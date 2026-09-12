#!/usr/bin/env python3
"""
StellarOrion Validation Post-Processing: DSMC vs Analytical Models
===================================================================

Produces:
  1. DSMC vs Sutton-Graves / Fay-Riddell comparison tables
  2. IRVE-3 flight data validation table
  3. Surface heating distribution analysis
  4. DSMC convergence / noise statistics
  5. Integrated heat load calculation

References:
  [1] Sutton & Graves (1971), NASA TR R-376 — SG correlation
  [2] Fay & Riddell (1958) — FR stagnation-point theory
  [3] Rapisarda (2023), MSc Thesis, TU Delft — Tables 4.9, 4.10
  [4] NASA TP-2013-4012 — IRVE-3 flight data
  [5] Bird (1994), "Molecular Gas Dynamics" — DSMC noise theory
"""

import glob
import math
import os
import sys

import numpy as np

# ============================================================================
# PHYSICAL CONSTANTS
# ============================================================================
# [Citation: Sutton & Graves 1971, NASA TR R-376, Table 1]
C_SG = 1.7415e-4  # Sutton-Graves constant [W/m^2 / (kg/m^3)^0.5 / m^1.5 / (m/s)^3]
# q_sg = C_SG * sqrt(rho / R_n) * V^3

# [Citation: Fay & Riddell 1958; Rapisarda 2023 Eq 3.82]
PRANDTL = 0.71   # Prandtl number for frozen air
GAMMA = 1.4      # Ratio of specific heats for air
R_GAS = 287.058   # Specific gas constant for air [J/(kg*K)]
MU_REF = 1.716e-5 # Reference viscosity at T_ref [Pa*s]
T_REF = 273.15    # Reference temperature [K]
SUTHERLAND_S = 110.56  # Sutherland constant for air [K]

# Stefan-Boltzmann constant [W/(m^2*K^4)]
SIGMA_SB = 5.670374419e-8

# [Citation: NASA TP-2013-4012; Discussion.md]
# IRVE-3 reference data
IRVE3 = {
    "diameter_m": 3.0,
    "mass_kg": 281.0,
    "nose_radius_m": 1.5,       # R_n = D/2
    "ref_area_m2": 7.0686,      # pi * (D/2)^2
    "peak_heat_flux_Wcm2": 14.36,
    "total_heat_load_Jcm2": 195.06,
    "peak_decel_g": 19.7,
    "ballistic_coeff_kgm2": 26.9,
}

# Rapisarda Table 4.10 reference values (IRVE-3)
RAPISARDA = {
    "FR_peak_heat_flux_Wcm2": 13.83,
    "FR_total_heat_load_Jcm2": 195.17,
    "SG_peak_heat_flux_Wcm2": 15.26,
    "SG_total_heat_load_Jcm2": 223.95,
}

# StellarOrion baseline simulation conditions
# [Citation: stellarorion_physics.adb line 1362]
SIM_CONDITIONS = {
    "density_kgm3": 6.9674e-4,  # ISA at ~52 km
    "velocity_ms": 2700.0,       # m/s
    "altitude_km": 51.82,
    "mach": 10.29,
    "wall_temp_K": 1500.0,       # Typical TPS surface temperature
}


# ============================================================================
# ANALYTICAL MODELS
# ============================================================================

def sutton_graves_heat(rho, R_n, V):
    """Sutton-Graves stagnation-point convective heat flux [W/m^2].

    q_sg = C_sg * sqrt(rho / R_n) * V^3

    [Citation: Sutton & Graves 1971, NASA TR R-376]
    Valid for: continuum, V < 12 km/s, Earth air.
    """
    return C_SG * math.sqrt(rho / R_n) * V**3


def sutherland_viscosity(T):
    """Sutherland's law for dynamic viscosity of air [Pa*s].

    mu = mu_ref * (T/T_ref)^1.5 * (T_ref + S) / (T + S)

    [Citation: Sutherland 1893; Anderson 2006, Sec 15.2]
    """
    return MU_REF * (T / T_REF)**1.5 * (T_REF + SUTHERLAND_S) / (T + SUTHERLAND_S)


def fay_riddell_heat(rho, R_n, V, Mach, T_wall):
    """Fay-Riddell stagnation-point convective heat flux [W/m^2].

    Simplified Le=1 form from Rapisarda (2023) Eq 3.82:
      q_s = 0.763 * Pr^(-0.6) * (rho_w * mu_w)^0.1
            * (rho_s * mu_s)^0.4 * (h_s - h_w)
            * sqrt(du/dy|_s)

    where:
      T_s = T_inf * (1 + 0.2 * M^2)  — stagnation temperature
      p_s = p_inf * (1 + 0.2 * M^2)^3.5 — stagnation pressure
      rho_s = p_s / (R * T_s) — stagnation density
      mu_s = Sutherland(T_s) — stagnation viscosity
      rho_w = rho * T_s / T_w — wall density (ideal gas)
      mu_w = Sutherland(T_w) — wall viscosity
      h_s = Cp * T_s — stagnation enthalpy
      h_w = Cp * T_w — wall enthalpy
      du/dy|_s = (1/R_n) * sqrt(2*(p_s - p_inf)/rho_s)

    [Citation: Fay & Riddell 1958; Rapisarda 2023 Eq 3.82]
    Valid for: continuum, laminar BL, M < 10.
    """
    Cp = GAMMA * R_GAS / (GAMMA - 1)  # Specific heat at constant pressure

    # Stagnation conditions (isentropic)
    T_s = T_wall  # Use T_s from freestream for now
    T_stag = SIM_CONDITIONS["temperature_K"] * (1 + 0.2 * Mach**2)
    p_inf = rho * R_GAS * SIM_CONDITIONS["temperature_K"]
    p_stag = p_inf * (1 + 0.2 * Mach**2)**3.5

    # Stagnation-point density and viscosity
    rho_s = p_stag / (R_GAS * T_stag)
    mu_s = sutherland_viscosity(T_stag)

    # Wall properties
    rho_w = rho * T_stag / T_wall
    mu_w = sutherland_viscosity(T_wall)

    # Stagnation enthalpy difference
    h_s = Cp * T_stag
    h_w = Cp * T_wall
    dh = h_s - h_w

    # Velocity gradient at stagnation point (Newtonian)
    du_dy = (1.0 / R_n) * math.sqrt(2.0 * (p_stag - p_inf) / rho_s)

    # Fay-Riddell (Le=1, Rapisarda Eq 3.82)
    q = 0.763 * PRANDTL**(-0.6) * (rho_w * mu_w)**0.1 * \
        (rho_s * mu_s)**0.4 * dh * math.sqrt(du_dy)

    return max(q, 0.0)


# ============================================================================
# SPARTA OUTPUT PARSERS
# ============================================================================

def parse_grid_file(filepath):
    """Parse SPARTA grid output file.

    Columns: id xlo ylo xhi yhi f_2[1] f_2[2] f_2[3] f_2[4] f_3[*] f_4[*]
      f_2[1] = particle count in cell
      f_2[2] = temperature [K]
      f_2[3] = velocity magnitude [m/s] or similar
      f_2[4] = ?
      f_3[*] = ?
      f_4[*] = number density [m^-3]

    Returns: dict with arrays for each column.
    """
    data = {"id": [], "x": [], "y": [], "temp": [], "density": [], "n_particles": []}
    with open(filepath) as f:
        in_cells = False
        for line in f:
            if line.startswith("ITEM: CELLS"):
                in_cells = True
                continue
            if line.startswith("ITEM:"):
                in_cells = False
                continue
            if in_cells:
                parts = line.split()
                if len(parts) >= 11:
                    data["id"].append(int(parts[0]))
                    xlo, xhi = float(parts[1]), float(parts[3])
                    ylo, yhi = float(parts[2]), float(parts[4])
                    data["x"].append((xlo + xhi) / 2.0)
                    data["y"].append((ylo + yhi) / 2.0)
                    data["n_particles"].append(float(parts[5]))
                    data["temp"].append(float(parts[6]))
                    data["density"].append(float(parts[10]))
    for k in data:
        data[k] = np.array(data[k])
    return data


def parse_surf_file(filepath):
    """Parse SPARTA surf output file.

    Columns: id f_1[1] f_1[2] f_1[3] f_surfavg[1] f_surfavg[2] f_surfavg[3]
      f_1[1] = force x [N]
      f_1[2] = force y [N]
      f_1[3] = heat flux [W/m^2] (kinetic energy flux to surface)
      f_surfavg[1] = surface-averaged heat flux
      f_surfavg[2] = surface-averaged ?
      f_surfavg[3] = surface-averaged ?

    Returns: dict with arrays.
    """
    data = {"id": [], "heat_flux": [], "surf_avg_flux": [], "force_x": [], "force_y": []}
    with open(filepath) as f:
        in_surfs = False
        for line in f:
            if line.startswith("ITEM: SURFS"):
                in_surfs = True
                continue
            if line.startswith("ITEM:"):
                in_surfs = False
                continue
            if in_surfs:
                parts = line.split()
                if len(parts) >= 7:
                    data["id"].append(int(parts[0]))
                    data["force_x"].append(float(parts[1]))
                    data["force_y"].append(float(parts[2]))
                    data["heat_flux"].append(float(parts[3]))
                    data["surf_avg_flux"].append(float(parts[4]))
    for k in data:
        data[k] = np.array(data[k])
    return data


# ============================================================================
# POST-PROCESSING FUNCTIONS
# ============================================================================

def compute_analytical_at_conditions():
    """Compute Sutton-Graves and Fay-Riddell at baseline conditions."""
    rho = SIM_CONDITIONS["density_kgm3"]
    V = SIM_CONDITIONS["velocity_ms"]
    R_n = IRVE3["nose_radius_m"]
    Mach = SIM_CONDITIONS["mach"]
    T_w = SIM_CONDITIONS["wall_temp_K"]

    q_sg = sutton_graves_heat(rho, R_n, V)
    q_fr = fay_riddell_heat(rho, R_n, V, Mach, T_w)

    # Convert to W/cm^2
    q_sg_Wcm2 = q_sg / 1e4
    q_fr_Wcm2 = q_fr / 1e4

    return q_sg, q_fr, q_sg_Wcm2, q_fr_Wcm2


def table1_dsmc_vs_analytical(surf_files):
    """Table 1: DSMC vs Analytical comparison at each timestep."""
    q_sg, q_fr, q_sg_Wcm2, q_fr_Wcm2 = compute_analytical_at_conditions()

    rows = []
    for sf in sorted(surf_files):
        step = int(sf.split(".")[-2].replace("out", ""))
        surf = parse_surf_file(sf)

        # DSMC metrics (exclude negative values as noise)
        positive_hf = surf["heat_flux"][surf["heat_flux"] > 0]
        if len(positive_hf) > 0:
            dsmc_peak = np.max(positive_hf)
            dsmc_mean = np.mean(positive_hf)
            dsmc_median = np.median(positive_hf)
            n_positive = len(positive_hf)
            n_negative = np.sum(surf["heat_flux"] <= 0)
        else:
            dsmc_peak = dsmc_mean = dsmc_median = 0.0
            n_positive = 0
            n_negative = len(surf["heat_flux"])

        rows.append({
            "step": step,
            "dsmc_peak_Wm2": dsmc_peak,
            "dsmc_peak_Wcm2": dsmc_peak / 1e4,
            "dsmc_mean_Wm2": dsmc_mean,
            "dsmc_mean_Wcm2": dsmc_mean / 1e4,
            "dsmc_median_Wm2": dsmc_median,
            "dsmc_median_Wcm2": dsmc_median / 1e4,
            "n_positive": n_positive,
            "n_negative": n_negative,
            "n_total": len(surf["heat_flux"]),
            "sg_Wcm2": q_sg_Wcm2,
            "fr_Wcm2": q_fr_Wcm2,
            "dsmc_sg_ratio": (dsmc_mean / 1e4) / q_sg_Wcm2 if q_sg_Wcm2 > 0 else 0,
            "dsmc_fr_ratio": (dsmc_mean / 1e4) / q_fr_Wcm2 if q_fr_Wcm2 > 0 else 0,
        })

    return rows, q_sg, q_fr, q_sg_Wcm2, q_fr_Wcm2


def table2_irve3_validation(rows):
    """Table 2: IRVE-3 flight validation comparison."""
    # Use the final timestep (step 1000) as representative
    final = rows[-1]

    return {
        "Parameter": ["Peak Heat Flux (W/cm²)", "Total Heat Load (J/cm²)",
                       "Peak Deceleration (g)", "Ballistic Coeff (kg/m²)"],
        "IRVE-3 Flight": [IRVE3["peak_heat_flux_Wcm2"], IRVE3["total_heat_load_Jcm2"],
                          IRVE3["peak_decel_g"], IRVE3["ballistic_coeff_kgm2"]],
        "Rapisarda FR": [RAPISARDA["FR_peak_heat_flux_Wcm2"], RAPISARDA["FR_total_heat_load_Jcm2"],
                         "—", "—"],
        "Rapisarda SG": [RAPISARDA["SG_peak_heat_flux_Wcm2"], RAPISARDA["SG_total_heat_load_Jcm2"],
                         "—", "—"],
        "StellarOrion DSMC": [final["dsmc_mean_Wcm2"], "—",
                              "—", "—"],
        "Delta vs Flight (%)": [
            f"{((final['dsmc_mean_Wcm2'] / IRVE3['peak_heat_flux_Wcm2']) - 1) * 100:+.1f}%",
            "—", "—", "—"
        ],
    }


def table3_surface_distribution(surf_files):
    """Table 3: Surface heating distribution — peak heating by surface element."""
    final_surf = parse_surf_file(surf_files[-1])

    # Get positive heat flux elements only
    mask = final_surf["heat_flux"] > 0
    ids = final_surf["id"][mask]
    hf = final_surf["heat_flux"][mask]

    if len(hf) == 0:
        return []

    # Sort by heat flux descending
    sorted_idx = np.argsort(hf)[::-1]

    rows = []
    for i, idx in enumerate(sorted_idx[:15]):  # Top 15 elements
        rows.append({
            "rank": i + 1,
            "surf_id": int(ids[idx]),
            "heat_flux_Wm2": float(hf[idx]),
            "heat_flux_Wcm2": float(hf[idx]) / 1e4,
            "pct_of_peak": 100.0,
            "pct_of_mean": float(hf[idx]) / float(np.mean(hf)) * 100,
        })

    return rows, np.mean(hf), np.std(hf), np.median(hf)


def table4_convergence_stats(surf_files):
    """Table 4: DSMC convergence / noise statistics across timesteps."""
    rows = []
    all_peak_hf = []

    for sf in sorted(surf_files):
        step = int(sf.split(".")[-2].replace("out", ""))
        surf = parse_surf_file(sf)
        positive_hf = surf["heat_flux"][surf["heat_flux"] > 0]

        if len(positive_hf) > 0:
            peak = np.max(positive_hf)
            mean = np.mean(positive_hf)
            std = np.std(positive_hf)
            cv = std / mean * 100  # Coefficient of variation (%)
            n_neg = int(np.sum(surf["heat_flux"] <= 0))
            all_peak_hf.append(peak)
        else:
            peak = mean = std = cv = 0.0
            n_neg = len(surf["heat_flux"])

        rows.append({
            "step": step,
            "peak_Wcm2": peak / 1e4,
            "mean_Wcm2": mean / 1e4,
            "std_Wcm2": std / 1e4,
            "CV_%": cv,
            "n_elements": len(surf["heat_flux"]),
            "n_negative": n_neg,
        })

    # Overall convergence stats
    if all_peak_hf:
        all_peaks = np.array(all_peak_hf)
        convergence_cv = np.std(all_peaks) / np.mean(all_peaks) * 100
    else:
        convergence_cv = 0.0

    return rows, convergence_cv


def table5_integrated_heat_load(surf_files, dt_between_steps=100):
    """Table 5: Integrated heat load over the trajectory.

    Heat load Q = integral(q_dot * dt) over trajectory.
    For single-point DSMC, we approximate by averaging across surface elements.
    """
    rows = []
    cumulative_heat_load = 0.0

    for i, sf in enumerate(sorted(surf_files)):
        step = int(sf.split(".")[-2].replace("out", ""))
        surf = parse_surf_file(sf)

        # Mean heat flux across all surface elements (positive only)
        positive_hf = surf["heat_flux"][surf["heat_flux"] > 0]
        if len(positive_hf) > 0:
            mean_hf = np.mean(positive_hf)  # W/m^2
        else:
            mean_hf = 0.0

        # Approximate dt between steps (SPARTA timestep * dump interval)
        # For DSMC, each step represents a physical time increment
        # We use a rough estimate: dt ~ 1e-6 s per step (typical DSMC timestep)
        dt = 1e-6  # seconds per step (approximate)

        # Incremental heat load [J/m^2]
        dq = mean_hf * dt
        cumulative_heat_load += dq

        rows.append({
            "step": step,
            "mean_flux_Wm2": mean_hf,
            "mean_flux_Wcm2": mean_hf / 1e4,
            "incremental_load_Jm2": dq,
            "cumulative_load_Jm2": cumulative_heat_load,
            "cumulative_load_Jcm2": cumulative_heat_load / 1e4,
        })

    return rows


def print_table(title, headers, rows, col_width=14):
    """Pretty-print a table."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

    # Header
    header_str = "".join(h.ljust(col_width) for h in headers)
    print(f"  {header_str}")
    print(f"  {'-' * len(header_str)}")

    # Rows
    for row in rows:
        if isinstance(row, dict):
            row_str = "".join(str(row.get(h, "—")).ljust(col_width) for h in headers)
        else:
            row_str = "".join(str(v).ljust(col_width) for v in row)
        print(f"  {row_str}")
    print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base_dir, "results_validation")

    print("=" * 80)
    print("  StellarOrion Validation Post-Processing")
    print("  DSMC vs Analytical Models (Sutton-Graves, Fay-Riddell)")
    print("=" * 80)

    # Find all output files
    grid_files = sorted(glob.glob(os.path.join(results_dir, "grid.*.out")))
    surf_files = sorted(glob.glob(os.path.join(results_dir, "surf.*.out")))

    print(f"\n  Grid files: {len(grid_files)}")
    print(f"  Surf files: {len(surf_files)}")
    print(f"  Simulation conditions:")
    print(f"    Density: {SIM_CONDITIONS['density_kgm3']:.4e} kg/m³ (ISA at ~52 km)")
    print(f"    Velocity: {SIM_CONDITIONS['velocity_ms']:.0f} m/s")
    print(f"    Mach: {SIM_CONDITIONS['mach']:.2f}")
    print(f"    Nose radius: {IRVE3['nose_radius_m']:.1f} m")
    print(f"    Wall temp: {SIM_CONDITIONS['wall_temp_K']:.0f} K")

    # ============================================================================
    # TABLE 1: DSMC vs Analytical
    # ============================================================================
    rows1, q_sg, q_fr, q_sg_Wcm2, q_fr_Wcm2 = table1_dsmc_vs_analytical(surf_files)

    headers1 = ["step", "dsmc_peak_Wcm2", "dsmc_mean_Wcm2", "dsmc_median_Wcm2",
                 "sg_Wcm2", "fr_Wcm2", "dsmc/sg", "dsmc/fr", "n_pos", "n_neg"]
    rows1_fmt = []
    for r in rows1:
        rows1_fmt.append([
            r["step"],
            f"{r['dsmc_peak_Wcm2']:.2f}",
            f"{r['dsmc_mean_Wcm2']:.2f}",
            f"{r['dsmc_median_Wcm2']:.2f}",
            f"{r['sg_Wcm2']:.2f}",
            f"{r['fr_Wcm2']:.2f}",
            f"{r['dsmc_sg_ratio']:.2f}",
            f"{r['dsmc_fr_ratio']:.2f}",
            r["n_positive"],
            r["n_negative"],
        ])
    print_table("TABLE 1: DSMC vs Sutton-Graves vs Fay-Riddell", headers1, rows1_fmt)

    # ============================================================================
    # TABLE 2: IRVE-3 Validation
    # ============================================================================
    t2 = table2_irve3_validation(rows1)
    headers2 = ["Parameter", "IRVE-3 Flight", "Rapisarda FR", "Rapisarda SG", "StellarOrion DSMC", "Delta vs Flight"]
    rows2_fmt = []
    for i, param in enumerate(t2["Parameter"]):
        rows2_fmt.append([
            param,
            t2["IRVE-3 Flight"][i],
            t2["Rapisarda FR"][i],
            t2["Rapisarda SG"][i],
            t2["StellarOrion DSMC"][i],
            t2["Delta vs Flight (%)"][i],
        ])
    print_table("TABLE 2: IRVE-3 Flight Validation", headers2, rows2_fmt, col_width=20)

    # ============================================================================
    # TABLE 3: Surface Distribution
    # ============================================================================
    t3_result = table3_surface_distribution(surf_files)
    if len(t3_result) == 2:
        rows3, surf_mean, surf_std, surf_median = t3_result
        headers3 = ["rank", "surf_id", "heat_flux_Wcm2", "pct_of_peak", "pct_of_mean"]
        rows3_fmt = []
        for r in rows3:
            rows3_fmt.append([
                r["rank"],
                r["surf_id"],
                f"{r['heat_flux_Wcm2']:.2f}",
                f"{r['pct_of_peak']:.1f}",
                f"{r['pct_of_mean']:.1f}",
            ])
        print_table("TABLE 3: Surface Heating Distribution (Top 15 Elements)", headers3, rows3_fmt)
        print(f"  Surface statistics (positive elements only):")
        print(f"    Mean:   {surf_mean/1e4:.2f} W/cm²")
        print(f"    Std:    {surf_std/1e4:.2f} W/cm²")
        print(f"    Median: {surf_median/1e4:.2f} W/cm²")

    # ============================================================================
    # TABLE 4: Convergence Stats
    # ============================================================================
    rows4, conv_cv = table4_convergence_stats(surf_files)
    headers4 = ["step", "peak_Wcm2", "mean_Wcm2", "std_Wcm2", "CV_%", "n_neg"]
    rows4_fmt = []
    for r in rows4:
        rows4_fmt.append([
            r["step"],
            f"{r['peak_Wcm2']:.2f}",
            f"{r['mean_Wcm2']:.2f}",
            f"{r['std_Wcm2']:.2f}",
            f"{r['CV_%']:.1f}",
            r["n_negative"],
        ])
    print_table("TABLE 4: DSMC Convergence & Noise Statistics", headers4, rows4_fmt)
    print(f"  Overall convergence CV (peak flux across timesteps): {conv_cv:.1f}%")

    # ============================================================================
    # TABLE 5: Integrated Heat Load
    # ============================================================================
    rows5 = table5_integrated_heat_load(surf_files)
    headers5 = ["step", "mean_flux_Wcm2", "cumul_load_Jcm2"]
    rows5_fmt = []
    for r in rows5:
        rows5_fmt.append([
            r["step"],
            f"{r['mean_flux_Wcm2']:.2f}",
            f"{r['cumulative_load_Jcm2']:.4f}",
        ])
    print_table("TABLE 5: Integrated Heat Load", headers5, rows5_fmt)

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"  Analytical predictions at baseline conditions:")
    print(f"    Sutton-Graves: {q_sg_Wcm2:.2f} W/cm²")
    print(f"    Fay-Riddell:   {q_fr_Wcm2:.2f} W/cm²")
    print(f"    SG/FR ratio:   {q_sg_Wcm2/q_fr_Wcm2:.2f}")
    print()
    print(f"  IRVE-3 reference (Rapisarda Table 4.10):")
    print(f"    Flight:        {IRVE3['peak_heat_flux_Wcm2']:.2f} W/cm²")
    print(f"    FR model:      {RAPISARDA['FR_peak_heat_flux_Wcm2']:.2f} W/cm²")
    print(f"    SG model:      {RAPISARDA['SG_peak_heat_flux_Wcm2']:.2f} W/cm²")
    print()
    print(f"  StellarOrion DSMC (final step):")
    final = rows1[-1]
    print(f"    Peak (raw):    {final['dsmc_peak_Wcm2']:.2f} W/cm²")
    print(f"    Mean:          {final['dsmc_mean_Wcm2']:.2f} W/cm²")
    print(f"    Median:        {final['dsmc_median_Wcm2']:.2f} W/cm²")
    print(f"    DSMC/SG:       {final['dsmc_sg_ratio']:.2f}")
    print(f"    DSMC/FR:       {final['dsmc_fr_ratio']:.2f}")
    print()
    print(f"  DSMC noise: {conv_cv:.1f}% CV across timesteps")
    print(f"  Negative elements (noise): {final['n_negative']}/{final['n_total']}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
