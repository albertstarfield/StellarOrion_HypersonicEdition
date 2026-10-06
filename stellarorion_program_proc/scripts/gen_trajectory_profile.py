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
# ISA 1975 Atmosphere Model -- Ada/SPARK FFI (single source of truth)
# ============================================================================
#  ONE TRUTH, ONE VALUE (2026-10-06): the ISA layer table, the per-layer density
#  power law, and the sqrt(gamma*R*T) speed of sound that used to live here were
#  a SECOND implementation of the atmosphere model. They were aligned to the
#  Ada/SPARK value by hand (F45, worst 0.347% vs Ada) and could drift again the
#  moment either side changed. They have been deleted; density, temperature, and
#  the speed of sound now come from the Ada/SPARK library through
#  ada_pinn_wrapper, so this profile is the same model the rest of the pipeline
#  uses.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "python"))
from ada_pinn_wrapper import (  # sys.path set just above
    dynamic_pressure as _ada_dynamic_pressure,
)
from ada_pinn_wrapper import (
    isa_atmosphere as _ada_isa_atmosphere,
)


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

        # Atmosphere -- one Ada/SPARK call returns density and the speed of
        # sound (Atmosphere_Density_C / speed_of_sound). No Python ISA table and
        # no sqrt(gamma*R*T): one truth, one value.
        atm = _ada_isa_atmosphere(alt_m / 1000.0)
        rho = atm["density_kgm3"]
        a_sound = atm["speed_of_sound_ms"]

        # Dynamic pressure via Ada/SPARK (Dynamic_Pressure_C).
        q = _ada_dynamic_pressure(rho, vel)

        # Drag force
        drag = q * CD * FRONTAL_AREA

        # Gravity (inverse-square)
        g = G0 * (R_EARTH / (R_EARTH + alt_m)) ** 2

        # Equations of motion (Chapman/Vinh)
        # dv/dt = -D/m - g*sin(gamma)
        dv_dt = -(drag / MASS_KG) - g * math.sin(gamma)  # nosec: SMT_LOGIC_VERIFICATION — MASS_KG=281.0 kg, always nonzero; standard aerodynamic drag equation (Chapman/Vinh)
        # dgamma/dt = -(g/v)*cos(gamma) + (L/(m*v)) + (v/(R_EARTH+h))*cos(gamma)
        # For 1-DOF (no lift): L=0
        dgamma_dt = -(g / vel) * math.cos(gamma) + (vel / (R_EARTH + alt_m)) * math.cos(gamma)  # nosec: SMT_LOGIC_VERIFICATION — loop guard ensures vel > 170 m/s; flight path angle ODE (Chapman/Vinh)
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
    with open(output_path, 'w', newline='') as f:  # nosec: EXTERNAL_CALL_UNHANDLED — utility script, errors propagate to caller; file path from argparse, not user-injected
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
    """Entry point: parse args, run trajectory, write CSV."""
    if len(sys.argv) < 2:
        print("Usage: gen_trajectory_profile.py <results_dir>")
        print("  Generates trajectory_profile.csv in the specified directory.")
        print("  Also generates in results/validation_smooth/ and results/validation_scalloped/")
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

    # Also write to smooth and scalloped dirs if they exist.
    # base = dirname(results_dir); when results_dir = results/<variant>, base = results/,
    # so the sibling variants are plain names relative to base.
    base = os.path.dirname(os.path.abspath(results_dir))
    for subdir in ['validation_smooth', 'validation_scalloped']:
        target = os.path.join(base, subdir)
        if os.path.isdir(target):
            target_path = os.path.join(target, "trajectory_profile.csv")
            write_csv(samples, target_path)


if __name__ == '__main__':
    main()
