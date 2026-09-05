#!/usr/bin/env python3
"""
================================================================================
SCRIPT: make_derived_plots.py — Derived Aerothermodynamic Variable Plotter
================================================================================

AXIOMS:
  AXIOM 1: The Ada validation pipeline writes
           <results_dir>/validation_timeseries.csv with a header row
           followed by numeric data rows.
  AXIOM 2: The CSV contains columns: heatflux_avg_Wm2, heatflux_max_Wm2,
           drag_sum_N, dyn_press_pa, time_s, step.
  AXIOM 3: Derived variables (T_surface, T_back, beta) are computed from
           physics formulas in stellarorion_physics.ads.

THEORIES:
  THEOREM 1: T_surface = (q_avg / (sigma * epsilon))^0.25
             [Source: Stefan-Boltzmann law; stellarorion_physics.ads Radiative_Eq_Temp]
  THEOREM 2: T_back = T_init + (q_avg * dt_cumulative * eta_lag) / (rho_TPS * Cp * delta)
             [Source: 1D transient backface; stellarorion_physics.ads Backface_Temperature]
  THEOREM 3: beta = m * q_dyn / F_drag
             [Source: Ballistic coefficient; stellarorion_physics.ads Ballistic_Coefficient]

APPLICATIONS:
  - Read <results_dir>/validation_timeseries.csv
  - Compute T_surface, T_back, beta for each step
  - Plot derived variables vs step as PNG
  - Write PNGs into <results_dir>/plots/

CITATIONS:
  [StefanBoltzmann] Stefan-Boltzmann law: q = sigma * epsilon * T^4
  [Bird1994] Bird, G.A. "Molecular Gas Dynamics and the Direct Simulation
             of Gas Flows", 1994.
  [Rapisarda2023] Rapisarda, V. "Parametric Geometry and Trajectory
                   Optimization for HIAD", 2023.

TIMING ANALYSIS:
  Estimated Processing Time: O(N) where N = rows.
  WCET: < 1 s for typical validation runs (<= 100 rows).
================================================================================
"""
from __future__ import annotations

import math
import os
import sys

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # headless / non-interactive backend

# ---------------------------------------------------------------------------
# Physical constants and material properties
# [Source: stellarorion_physics.ads, README.md mathematical foundations]
# ---------------------------------------------------------------------------
SIGMA_SB = 5.670374419e-8  # Stefan-Boltzmann constant [W/(m^2 K^4)]
EMISSIVITY = 0.85          # SIC surface emissivity [dimensionless]
                            # [Source: Hollis et al. AIAA-2024-1498]
T_INIT = 300.0             # Initial temperature [K]
ETA_LAG = 0.15             # Thermal lag efficiency [dimensionless]
                            # [Source: Lau et al. 2013; Lippincott et al. 2019]
RHO_TPS = 2200.0           # SIC density [kg/m^3]
CP_TPS = 800.0             # SIC specific heat [J/(kg K)]
DELTA_TPS = 0.005          # TPS thickness [m] (5 mm)
MASS_IRVE3 = 281.0         # IRVE-3 vehicle mass [kg]
G0 = 9.80665               # Standard gravity [m/s^2]
A_REF = math.pi * (1.5 ** 2)  # Reference area for 3m diameter [m^2] = 7.0686

# Survivability limits [Source: Sep 2 Discussion.md Section 12.1]
SIC_MAX_TEMP = 1700.0      # SIC surface temperature limit [K]
KAPTON_MAX_TEMP = 673.0    # Kapton adhesive limit [K]
MAX_G_LOAD = 25.0          # Structural limit [g]


def _read_csv(path: str) -> tuple[list[int], dict[str, list[float]]]:
    """Read CSV header + data. Returns (steps, {col_name: values})."""
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    if not lines:
        return [], {}
    header = [h.strip() for h in lines[0].split(",")]
    data: dict[str, list[float]] = {h: [] for h in header}
    steps: list[int] = []
    for raw in lines[1:]:
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(",")
        if len(parts) < len(header):
            continue
        try:
            steps.append(int(float(parts[0])))
            for i, h in enumerate(header[1:], 1):
                data[h].append(float(parts[i]))
        except ValueError:
            continue
    return steps, data


def _compute_t_surface(q_avg_wm2: float) -> float:
    """Radiative equilibrium surface temperature [K].
    T = (q / (sigma * epsilon))^0.25
    [Source: Stefan-Boltzmann law; stellarorion_physics.ads Radiative_Eq_Temp]"""
    if q_avg_wm2 <= 0:
        return T_INIT
    return (q_avg_wm2 / (SIGMA_SB * EMISSIVITY)) ** 0.25


def _compute_t_back(q_total_jm2: float) -> float:
    """1D transient backface temperature [K].
    T_back = T_init + (Q_total * eta_lag) / (rho_TPS * Cp * delta)
    [Source: stellarorion_physics.ads Backface_Temperature]
    Uses cumulative heat load (J/m²) directly, NOT time-based formula.
    Q_total is the area-integrated heat load from the DSMC simulation."""
    capacitance = RHO_TPS * CP_TPS * DELTA_TPS  # [J/(m^2 K)] = 8800
    return T_INIT + (q_total_jm2 * ETA_LAG) / capacitance


def _compute_beta(dyn_press_pa: float, drag_sum_n: float) -> float:
    """Ballistic coefficient [kg/m^2].
    beta = m * q / F_drag
    [Source: stellarorion_physics.ads Ballistic_Coefficient]"""
    if drag_sum_n <= 0:
        return float('inf')
    return MASS_IRVE3 * dyn_press_pa / drag_sum_n


def _plot_derived(
    steps: list[int],
    values: list[float],
    out_path: str,
    title: str,
    ylabel: str,
    limit_lines: list[tuple[float, str]] | None = None,
) -> None:
    """Plot derived variable vs step with optional horizontal limit lines."""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(steps, values, marker="o", linestyle="-", color="tab:blue",
            markersize=4, linewidth=1.5)
    if limit_lines:
        for limit_val, label in limit_lines:
            ax.axhline(y=limit_val, color="tab:red", linestyle="--",
                       linewidth=1.5, label=f"{label} ({limit_val:.0f} K)" if "K" in label
                       else f"{label} ({limit_val:.0f})")
        ax.legend(loc="best", fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("SPARTA Step", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [OK] {os.path.basename(out_path)}")


def _plot_multi_axis(
    steps: list[int],
    values_a: list[float],
    values_b: list[float],
    out_path: str,
    title: str,
    ylabel_a: str,
    ylabel_b: str,
    label_a: str,
    label_b: str,
) -> None:
    """Plot two derived variables on dual Y-axes vs step."""
    fig, ax1 = plt.subplots(figsize=(10, 6))
    color_a = "tab:blue"
    color_b = "tab:orange"

    ax1.plot(steps, values_a, marker="o", linestyle="-", color=color_a,
             markersize=4, linewidth=1.5, label=label_a)
    ax1.set_xlabel("SPARTA Step", fontsize=11)
    ax1.set_ylabel(ylabel_a, fontsize=11, color=color_a)
    ax1.tick_params(axis="y", labelcolor=color_a)

    ax2 = ax1.twinx()
    ax2.plot(steps, values_b, marker="s", linestyle="--", color=color_b,
             markersize=4, linewidth=1.5, label=label_b)
    ax2.set_ylabel(ylabel_b, fontsize=11, color=color_b)
    ax2.tick_params(axis="y", labelcolor=color_b)

    ax1.set_title(title, fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [OK] {os.path.basename(out_path)}")


def main(argv: list[str]) -> int:
    results_dir = argv[1] if len(argv) > 1 else "results_validation_scalloped"
    csv_path = os.path.join(results_dir, "validation_timeseries.csv")
    plots_dir = os.path.join(results_dir, "plots")
    if not os.path.isfile(csv_path):
        print(f"[derived-plots] CSV not found: {csv_path}", file=sys.stderr)
        return 1
    os.makedirs(plots_dir, exist_ok=True)

    steps, data = _read_csv(csv_path)
    if not steps:
        print("[derived-plots] No data rows in CSV.", file=sys.stderr)
        return 1

    print(f"[derived-plots] Computing derived variables for {len(steps)} steps...")

    # Extract required columns
    q_avg = data.get("heatflux_avg_Wm2", [])
    q_max = data.get("heatflux_max_Wm2", [])
    drag_sum = data.get("drag_sum_N", [])
    dyn_press = data.get("dyn_press_pa", [])
    heat_load = data.get("heat_load_jcm2", [])
    g_load = data.get("g_load", [])
    _time_s = data.get("time_s", [])  # reserved for future time-based analysis

    n = len(steps)
    if not all(len(v) == n for v in [q_avg, drag_sum, dyn_press]):
        print("[derived-plots] Missing required columns in CSV.", file=sys.stderr)
        return 1

    # Compute derived variables
    # NOTE: heatflux_max_Wm2 = max DSMC cell value (stagnation point peak)
    #       heatflux_avg_Wm2 = area-averaged over vehicle surface
    #       IRVE-3 flight q_max = 14.36 W/cm² is area-averaged (not max cell)
    #       For fair comparison with flight, use avg; for TPS peak design, use max.
    t_surface_avg = [_compute_t_surface(q) for q in q_avg]  # area-averaged (compare w/ flight)
    t_surface_max = [_compute_t_surface(q) for q in q_max]  # max cell (peak TPS design)
    t_surface = t_surface_avg  # primary plot uses area-averaged for flight comparison
    # For T_back, use cumulative time: step_number * time_per_step
    # time_s column is the simulation time per step; approximate cumulative dt
    # Using step number as proxy (each step ~ same dt)
    # More accurate: use time_s * step / 100 (since first data point is step 100)
    # T_back uses cumulative heat load (J/m²) directly, NOT time-based formula.
    # The heat_load_jcm2 column is already the integrated heat load at each step.
    # Correct formula: T_back = T_init + (Q_total * eta_lag) / (rho_TPS * Cp * delta)
    # [Source: stellarorion_physics.ads Backface_Temperature; Rapisarda 2023 Sec 5.5]
    capacitance = RHO_TPS * CP_TPS * DELTA_TPS  # [J/(m^2 K)] = 2200*800*0.005 = 8800
    t_back = []
    for i in range(n):
        Q_total_jm2 = heat_load[i] * 10000.0  # Convert J/cm² to J/m²
        t_back.append(T_INIT + (Q_total_jm2 * ETA_LAG) / capacitance)

    beta = [_compute_beta(dyn_press[i], drag_sum[i]) for i in range(n)]

    # Limit lines for survivability checks
    t_surface_limits = [
        (SIC_MAX_TEMP, "SIC max temp"),
    ]
    t_back_limits = [
        (KAPTON_MAX_TEMP, "Kapton adhesive limit"),
    ]
    _g_load_limits = [
        (MAX_G_LOAD, "Structural limit"),
    ]  # reserved for future survivability overlay

    print("[derived-plots] Generating plots...")

    # 1. T_surface vs Step (area-averaged, comparable with IRVE-3 flight)
    _plot_derived(
        steps, t_surface,
        os.path.join(plots_dir, "T_surface_vs_step.png"),
        "Radiative Equilibrium Surface Temperature vs Step\n"
        "T = (q_avg / (σ·ε))^0.25  |  σ=5.67e-8, ε=0.85 (SIC)\n"
        "Using area-averaged heat flux (comparable with IRVE-3 flight)",
        "Surface Temperature (K)",
        limit_lines=t_surface_limits,
    )

    # 2. T_back vs Step
    _plot_derived(
        steps, t_back,
        os.path.join(plots_dir, "T_back_vs_step.png"),
        "1D Transient Backface Temperature vs Step\n"
        "T_back = T_init + (q·dt·η_lag)/(ρ·Cp·δ)  |  η_lag=0.15, ρ=2200, Cp=800, δ=5mm",
        "Backface Temperature (K)",
        limit_lines=t_back_limits,
    )

    # 3. Beta (ballistic coefficient) vs Step
    _plot_derived(
        steps, beta,
        os.path.join(plots_dir, "beta_vs_step.png"),
        "Ballistic Coefficient vs Step\n"
        "β = m·q_dyn / F_drag  |  m=281 kg (IRVE-3)",
        "Ballistic Coefficient (kg/m²)",
    )

    # 4. T_surface and T_back combined dual-axis
    _plot_multi_axis(
        steps, t_surface, t_back,
        os.path.join(plots_dir, "T_surface_T_back_combined.png"),
        "Surface & Backface Temperature vs Step\n"
        "TPS Survivability Check: T_surface < 1700K (SIC), T_back < 673K (Kapton)",
        "T_surface (K)", "T_back (K)",
        "T_surface (SIC)", "T_back (Kapton)",
    )

    # 5. Heat flux with physical context (stagnation region visualization)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 5a: Heat flux distribution (max vs avg)
    ax = axes[0, 0]
    ax.plot(steps, [q / 1e4 for q in q_max], "r-o", markersize=3, label="Max (cell)")
    ax.plot(steps, [q / 1e4 for q in q_avg], "b-s", markersize=3, label="Avg (surface)")
    ax.axhline(y=14.36, color="green", linestyle="--", label="IRVE-3 flight peak")
    ax.set_title("Heat Flux Comparison", fontweight="bold")
    ax.set_ylabel("Heat Flux (W/cm²)")
    ax.set_xlabel("SPARTA Step")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 5b: Drag coefficient convergence
    ax = axes[0, 1]
    cd = data.get("cd", [])
    if cd:
        ax.plot(steps, cd, "g-o", markersize=3)
        ax.axhline(y=1.58, color="red", linestyle="--", label="DSMC converged (~1.58)")
        ax.set_title("Drag Coefficient Convergence", fontweight="bold")
        ax.set_ylabel("C_D")
        ax.set_xlabel("SPARTA Step")
        ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 5c: G-load with limit
    ax = axes[1, 0]
    if g_load:
        ax.plot(steps, g_load, "m-o", markersize=3)
        ax.axhline(y=19.7, color="green", linestyle="--", label="IRVE-3 flight (19.7g)")
        ax.axhline(y=25, color="red", linestyle="--", label="Structural limit (25g)")
        ax.set_title("Deceleration G-Load", fontweight="bold")
        ax.set_ylabel("G-Load (g)")
        ax.set_xlabel("SPARTA Step")
        ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 5d: Ballistic coefficient with reference
    ax = axes[1, 1]
    ax.plot(steps, beta, "c-o", markersize=3)
    ax.axhline(y=26.9, color="red", linestyle="--", label="IRVE-3 reference (26.9)")
    ax.set_title("Ballistic Coefficient", fontweight="bold")
    ax.set_ylabel("β (kg/m²)")
    ax.set_xlabel("SPARTA Step")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle("StellarOrion DSMC Validation — Physical Variable Dashboard",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "physical_dashboard.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] physical_dashboard.png")

    # 6. Survivability summary plot
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(steps, t_surface_avg, "r-o", markersize=4,
            label=f"T_surface avg (max={max(t_surface_avg):.0f}K)")
    ax.plot(steps, t_surface_max, "r--^", markersize=3, alpha=0.6,
            label=f"T_surface max-cell (max={max(t_surface_max):.0f}K)")
    ax.plot(steps, t_back, "b-s", markersize=4, label=f"T_back (max={max(t_back):.0f}K)")
    ax.axhline(y=SIC_MAX_TEMP, color="red", linestyle="--", alpha=0.7,
               label=f"SIC limit ({SIC_MAX_TEMP:.0f}K)")
    ax.axhline(y=KAPTON_MAX_TEMP, color="blue", linestyle="--", alpha=0.7,
               label=f"Kapton limit ({KAPTON_MAX_TEMP:.0f}K)")

    # Shade survivability zones
    ax.axhspan(0, KAPTON_MAX_TEMP, alpha=0.05, color="green", label="Kapton safe zone")
    ax.axhspan(KAPTON_MAX_TEMP, SIC_MAX_TEMP, alpha=0.05, color="yellow",
               label="Kapton exceed / SIC safe")
    ax.axhspan(SIC_MAX_TEMP, max(max(t_surface), SIC_MAX_TEMP) * 1.1,
               alpha=0.05, color="red", label="SIC exceed zone")

    ax.set_title("HIAD TPS Survivability Assessment\n"
                 "StellarOrion DSMC Validation (IRVE-3 geometry, Rapisarda 2023)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("SPARTA Step", fontsize=11)
    ax.set_ylabel("Temperature (K)", fontsize=11)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "survivability_assessment.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] survivability_assessment.png")

    # Print summary
    print("\n[derived-plots] Summary:")
    print(f"  T_surface range: {min(t_surface):.0f} - {max(t_surface):.0f} K")
    print(f"  T_back range:    {min(t_back):.0f} - {max(t_back):.0f} K")
    print(f"  Beta range:      {min(beta):.2f} - {max(beta):.2f} kg/m²")
    print(f"  IRVE-3 ref beta: {MASS_IRVE3 * data['dyn_press_pa'][-1] / drag_sum[-1]:.2f} kg/m² (step {steps[-1]})")

    # Survivability check
    t_surv = max(t_surface) <= SIC_MAX_TEMP
    t_back_surv = max(t_back) <= KAPTON_MAX_TEMP
    print("\n  Survivability:")
    print(f"    T_surface < {SIC_MAX_TEMP}K (SIC): {'PASS' if t_surv else 'FAIL'} (max={max(t_surface):.0f}K)")
    print(f"    T_back < {KAPTON_MAX_TEMP}K (Kapton): {'PASS' if t_back_surv else 'FAIL'} (max={max(t_back):.0f}K)")

    print(f"\n[derived-plots] Wrote 6 PNGs to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
