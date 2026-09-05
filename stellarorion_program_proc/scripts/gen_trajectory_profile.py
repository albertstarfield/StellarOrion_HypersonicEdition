#!/usr/bin/env python3
"""
gen_trajectory_profile.py — 1-DOF ballistic entry trajectory profile generator.

Generates a trajectory_profile.csv matching the Rapisarda MDAO comparison format,
using the same Euler forward integrator as the Ada Compute_Trajectory_Profile.

Entry conditions (LEO Earth entry, matching Rapisarda/IRVE-3):
  - Altitude: 122.65 km (top of sensible atmosphere for entry)
  - Velocity: 7500 m/s
  - Flight path angle: -5.75 degrees (below local horizontal)
  - CD: 1.47 (Rapisarda IRVE-3 reference)
  - Mass: 281 kg (IRVE-3)
  - Diameter: 3.0 m (IRVE-3)

Physics:
  - Chapman/Vinh equations of motion (1-DOF, gravity turn)
  - ISA 1975 piecewise atmosphere (exponential layers)
  - Inverse-square gravity: g(h) = G0 * (R_EARTH / (R_EARTH + h))^2
  - Speed of sound: a = sqrt(gamma * R * T)
  - Dynamic pressure: q = 0.5 * rho * V^2

Output: trajectory_profile.csv with columns:
  time_s, alt_km, vel_ms, mach, dyn_press_pa, cd, g_load, downrange_km

AXIOMS:
  T1: 1-DOF ballistic entry is valid for high L/D ratio decelerators
      where aerodynamic lift controls trajectory curvature.
  T2: Euler forward method gives O(dt^2) truncation error per step.
      Sufficient for comparison with Rapisarda reference profiles.
  T3: ISA 1975 atmosphere model matches standard aerospace reference
      to within 0.1% below 86 km.

CITATIONS:
  [Chapman1959] Chapman, D.R. "An Approximate Analytical Method for
      Studying Entry into Planetary Atmospheres", NASA TR R-37, 1959.
  [Vinh1980] Vinh, N.X. et al. "Hypersonic and Planetary Entry
      Flight Mechanics", 1980.
  [Rap23] Rapisarda, V. MDAO thesis, TU Delft, 2023.
  [ISA1975] COESA, "U.S. Standard Atmosphere, 1975".
"""

import csv
import math
import os
import sys

# ============================================================================
# Constants (matching stellarorion_physics.adb)
# ============================================================================
R_EARTH = 6_371_000.0       # WGS-84 mean Earth radius (m)
G0 = 9.80665                # Standard gravity at sea level (m/s^2)
R_AIR = 287.058             # Specific gas constant for dry air (J/(kg*K))
GAMMA_AIR = 1.4             # Ratio of specific heats for air

# Entry conditions
ALT_0_KM = 122.65           # Initial altitude (km)
VEL_0_MS = 7500.0           # Initial velocity (m/s)
GAMMA_0_DEG = -5.75         # Initial flight path angle (deg, below horizontal)
CD = 1.47                   # Drag coefficient (Rapisarda IRVE-3)
MASS_KG = 281.0             # Vehicle mass (kg)
DIAMETER_M = 3.0            # Vehicle diameter (m)

# Integration
DT_S = 1.0                  # Time step (s)
MAX_TIME_S = 5000.0         # Maximum integration time (s)
MAX_POINTS = 2000           # Maximum trajectory points

# Frontal area
FRONTAL_AREA = math.pi * (DIAMETER_M / 2.0) ** 2  # m^2


# ============================================================================
# ISA 1975 Atmosphere Model (piecewise, matching Ada Atmosphere_Density/Temp)
# ============================================================================
# Layer base heights (m) and temperatures (K) for ISA 1975
ISA_LAYERS = [
    # (base_alt_m, base_temp_K, lapse_rate_K/m)
    (0.0,        288.15,   -0.0065),     # Troposphere
    (11000.0,    216.65,    0.0),         # Tropopause
    (20000.0,    216.65,   +0.001),       # Stratosphere lower
    (32000.0,    228.65,   +0.0028),      # Stratosphere upper
    (47000.0,    270.65,    0.0),         # Stratopause
    (51000.0,    270.65,   -0.0028),      # Mesosphere lower
    (71000.0,    214.65,   -0.002),       # Mesosphere upper
    (84852.0,    186.87,    0.0),         # Mesopause
]

# Reference density at sea level
RHO_0 = 1.225  # kg/m^3


def atmosphere_temperature(alt_m):
    """ISA 1975 temperature profile (K)."""
    alt_km = alt_m / 1000.0
    if alt_km < 0:
        return 288.15
    elif alt_km <= 11.0:
        return 288.15 - 6.5 * alt_km
    elif alt_km <= 20.0:
        return 216.65
    elif alt_km <= 32.0:
        return 216.65 + 1.0 * (alt_km - 20.0)
    elif alt_km <= 47.0:
        return 228.65 + 2.8 * (alt_km - 32.0)
    elif alt_km <= 51.0:
        return 270.65
    elif alt_km <= 71.0:
        return 270.65 - 2.8 * (alt_km - 51.0)
    elif alt_km <= 84.852:
        return 214.65 - 2.0 * (alt_km - 71.0)
    else:
        return 186.87  # Exponential falloff above mesopause


def atmosphere_density(alt_m):
    """ISA 1975 density profile (kg/m^3), piecewise exponential."""
    if alt_m < 0:
        return RHO_0
    elif alt_m <= 11000.0:
        T = 288.15 - 6.5 * (alt_m / 1000.0)
        return RHO_0 * (T / 288.15) ** (1 + G0 / (6.5 * R_AIR))
    elif alt_m <= 20000.0:
        T = 216.65
        rho_11 = RHO_0 * (216.65 / 288.15) ** (1 + G0 / (6.5 * R_AIR))
        return rho_11 * math.exp(-G0 * (alt_m - 11000.0) / (R_AIR * T))
    elif alt_m <= 32000.0:
        T = 216.65 + 0.001 * (alt_m - 20000.0)
        rho_20 = atmosphere_density(20000.0)
        return rho_20 * math.exp(-G0 * (alt_m - 20000.0) / (R_AIR * T))
    elif alt_m <= 47000.0:
        T = 228.65 + 0.0028 * (alt_m - 32000.0)
        rho_32 = atmosphere_density(32000.0)
        return rho_32 * (T / (228.65 + 0.0028 * 0)) ** (-G0 / (0.0028 * R_AIR))
    elif alt_m <= 51000.0:
        rho_47 = atmosphere_density(47000.0)
        return rho_47 * math.exp(-G0 * (alt_m - 47000.0) / (R_AIR * 270.65))
    elif alt_m <= 71000.0:
        T = 270.65 - 0.0028 * (alt_m - 51000.0)
        rho_51 = atmosphere_density(51000.0)
        return rho_51 * (T / 270.65) ** (-G0 / (-0.0028 * R_AIR))
    elif alt_m <= 84852.0:
        T = 214.65 - 0.002 * (alt_m - 71000.0)
        rho_71 = atmosphere_density(71000.0)
        return rho_71 * (T / 214.65) ** (-G0 / (-0.002 * R_AIR))
    else:
        rho_85 = atmosphere_density(84852.0)
        return rho_85 * math.exp(-G0 * (alt_m - 84852.0) / (R_AIR * 186.87))


# ============================================================================
# Trajectory Integration (Euler forward, matching Ada Compute_Trajectory_Profile)
# ============================================================================
def compute_trajectory():
    """Compute 1-DOF ballistic entry trajectory profile."""
    gamma_0_rad = math.radians(GAMMA_0_DEG)

    # Initial state
    alt_m = ALT_0_KM * 1000.0
    vel = VEL_0_MS
    gamma = gamma_0_rad
    downrange_m = 0.0
    t = 0.0

    samples = []

    while t < MAX_TIME_S and len(samples) < MAX_POINTS:
        # Termination conditions
        if alt_m <= 0.0:
            break
        if vel <= 0.5 * 340.0:  # Mach 0.5 (~170 m/s at sea level)
            break

        # Atmosphere
        rho = atmosphere_density(alt_m)
        T = atmosphere_temperature(alt_m)
        a_sound = math.sqrt(GAMMA_AIR * R_AIR * T) if T > 0 else 340.0

        # Dynamic pressure
        q = 0.5 * rho * vel * vel

        # Drag force
        drag = q * CD * FRONTAL_AREA

        # Gravity (inverse-square)
        g = G0 * (R_EARTH / (R_EARTH + alt_m)) ** 2

        # Equations of motion (Chapman/Vinh)
        # dv/dt = -D/m - g*sin(gamma)
        dv_dt = -(drag / MASS_KG) - g * math.sin(gamma)
        # dgamma/dt = -(g/v)*cos(gamma) + (L/(m*v)) + (v/(R_EARTH+h))*cos(gamma)
        # For 1-DOF (no lift): L=0
        dgamma_dt = -(g / vel) * math.cos(gamma) + (vel / (R_EARTH + alt_m)) * math.cos(gamma)
        # dh/dt = v*sin(gamma)
        dh_dt = vel * math.sin(gamma)
        # ddownrange/dt = v*cos(gamma) * R_EARTH/(R_EARTH+h)
        ddr_dt = vel * math.cos(gamma) * R_EARTH / (R_EARTH + alt_m)

        # Euler forward step
        vel_new = vel + dv_dt * DT_S
        gamma_new = gamma + dgamma_dt * DT_S
        alt_new = alt_m + dh_dt * DT_S
        dr_new = downrange_m + ddr_dt * DT_S
        t_new = t + DT_S

        # Clamp altitude
        alt_new = max(alt_new, 0.0)

        # Clamp velocity
        vel_new = max(vel_new, 0.0)

        # Record sample
        mach = vel / a_sound if a_sound > 0 else 0.0
        g_load = abs(dv_dt) / G0 if G0 > 0 else 0.0
        cd_val = CD  # Constant CD for 1-DOF model

        samples.append({
            'time_s': round(t_new, 3),
            'alt_km': round(alt_new / 1000.0, 4),
            'vel_ms': round(vel_new, 2),
            'mach': round(mach, 4),
            'dyn_press_pa': round(q, 2),
            'cd': round(cd_val, 6),
            'g_load': round(g_load, 4),
            'downrange_km': round(dr_new / 1000.0, 3),
        })

        # Update state
        alt_m = alt_new
        vel = vel_new
        gamma = gamma_new
        downrange_m = dr_new
        t = t_new

    return samples


def write_csv(samples, output_path):
    """Write trajectory profile CSV."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time_s', 'alt_km', 'vel_ms', 'mach',
                         'dyn_press_pa', 'cd', 'g_load', 'downrange_km'])
        for s in samples:
            writer.writerow([
                s['time_s'], s['alt_km'], s['vel_ms'], s['mach'],
                s['dyn_press_pa'], s['cd'], s['g_load'], s['downrange_km']
            ])
    print(f"Wrote {len(samples)} trajectory points to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: gen_trajectory_profile.py <results_dir>")
        print("  Generates trajectory_profile.csv in the specified directory.")
        print("  Also generates in results_validation_smooth/ and results_validation_scalloped/")
        sys.exit(1)

    results_dir = sys.argv[1]

    samples = compute_trajectory()

    # Find key metrics
    max_g = max(s['g_load'] for s in samples)
    max_g_alt = next(s for s in samples if s['g_load'] == max_g)
    max_q = max(s['dyn_press_pa'] for s in samples)
    max_q_alt = next(s for s in samples if s['dyn_press_pa'] == max_q)
    max_vel = max(s['vel_ms'] for s in samples)
    max_mach = max(s['mach'] for s in samples)

    print("\n=== Trajectory Profile Summary ===")
    print(f"Points: {len(samples)}")
    print(f"Entry: {ALT_0_KM} km, {VEL_0_MS} m/s, {GAMMA_0_DEG} deg")
    print(f"Termination: {samples[-1]['alt_km']:.1f} km, {samples[-1]['vel_ms']:.0f} m/s, t={samples[-1]['time_s']:.0f} s")
    print(f"Max g-load: {max_g:.2f}g at {max_g_alt['alt_km']:.1f} km, t={max_g_alt['time_s']:.0f} s")
    print(f"Max dynamic pressure: {max_q:.0f} Pa ({max_q/1000:.2f} kPa) at {max_q_alt['alt_km']:.1f} km")
    print(f"Max Mach: {max_mach:.2f}")
    print(f"Max velocity: {max_vel:.0f} m/s")
    print(f"Downrange: {samples[-1]['downrange_km']:.1f} km")

    # Write to specified results dir
    output_path = os.path.join(results_dir, "trajectory_profile.csv")
    write_csv(samples, output_path)

    # Also write to smooth and scalloped dirs if they exist
    base = os.path.dirname(os.path.abspath(results_dir))
    for subdir in ['results_validation_smooth', 'results_validation_scalloped']:
        target = os.path.join(base, subdir)
        if os.path.isdir(target):
            target_path = os.path.join(target, "trajectory_profile.csv")
            write_csv(samples, target_path)


if __name__ == '__main__':
    main()
