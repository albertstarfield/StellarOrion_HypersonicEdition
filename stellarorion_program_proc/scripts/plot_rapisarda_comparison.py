#!/usr/bin/env python3
"""
================================================================================
SCRIPT: plot_rapisarda_comparison.py — Rapisarda MDAO Comparison Plot Generator
================================================================================

AXIOMS:
  AXIOM 1: The Ada validation pipeline writes
           <results_dir>/validation_timeseries.csv with 17 columns including
           trajectory variables (time_s, alt_km, vel_ms, mach, dyn_press_pa,
           cd, cl, g_load, downrange_km, heat_load_jcm2).
  AXIOM 2: The first column is always "step" (integer time index).
  AXIOM 3: matplotlib is importable in the host environment.
  AXIOM 4: Rapisarda MDAO thesis (TU Delft, 2023) provides IRVE-3 reference
           values for stacked-toroid IAD decelerators at Mars EDL.

THEORIES:
  THEOREM 1: Trajectory variables can be plotted vs time or vs altitude
             to match Rapisarda Figures 4.6, 6.11, 6.13, 6.16, 6.18.
  THEOREM 2: Both old (7-col) and new (17-col) CSV formats are handled;
             old format plots basic SPARTA metrics only.
  THEOREM 3: Rapisarda reference values are overlaid as horizontal/vertical
             lines or markers for direct comparison.

CITATIONS:
  [Rapisarda2023] Rapisarda, C. "Multidisciplinary Design Analysis and
                  Optimization of Inflatable Stacked-Torus Aerodynamic
                  Decelerators for Mars EDL", TU Delft, 2023.
  [NASA_TP_2013_4012] NASA Technical Paper 2013-4012, IRVE-3 Flight Data.
  [Hunter2007] Hunter, J. D. "Matplotlib: A 2D Graphics Environment", 2007.

TIMING ANALYSIS:
  Estimated Processing Time: O(N * C) where N = rows, C = columns.
  WCET: < 5 s for typical validation runs (<= 200 rows, <= 17 columns).
================================================================================
"""
from __future__ import annotations

import os
import sys

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # headless / non-interactive backend


# ---------------------------------------------------------------------------
# Rapisarda IRVE-3 Reference Values (Table 4.10, Figures 4.6, 6.11-6.19)
# ---------------------------------------------------------------------------
RAPISARDA_REFS = {
    # Table 4.10 — Trajectory peak values
    "peak_heat_flux_Wcm2": 14.3610,
    "time_peak_heat_flux_s": 677.49,
    "total_heat_load_Jcm2": 195.0577,
    "peak_g_load": 19.7,
    "target_cd": 1.470,
    "target_cd_flight": 0.670,
    "target_beta_kgm2": 26.9,
    "target_stag_pressure_Pa": 12400.0,
    "target_dyn_press_kPa": 6.2,
    # Entry conditions (LEO Mars entry)
    "entry_alt_km": 122.65,
    "entry_vel_ms": 7500.0,
    "entry_gamma_deg": -5.75,
}


def _read_csv(
    path: str,
) -> tuple[list[int], list[list[float]], list[str]]:
    """Read CSV header + data. Returns (steps, columns, header_names)."""
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    if not lines:
        return [], [], []
    header = [h.strip() for h in lines[0].split(",")]
    num_cols = len(header)
    steps: list[int] = []
    cols: list[list[float]] = [[] for _ in range(num_cols - 1)]
    for raw in lines[1:]:
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(",")
        if len(parts) < num_cols:
            continue
        try:
            steps.append(int(float(parts[0])))
            for c in range(1, num_cols):
                cols[c - 1].append(float(parts[c]))
        except ValueError:
            continue
    return steps, cols, header[1:]


def _get_col(
    col_names: list[str], data_cols: list[list[float]], name: str
) -> list[float] | None:
    """Return data for a named column, or None if absent."""
    try:
        idx = col_names.index(name)
        return data_cols[idx]
    except ValueError:
        return None


def _plot_with_ref(
    x: list[float],
    y: list[float],
    out_path: str,
    title: str,
    xlabel: str,
    ylabel: str,
    ref_lines: list[tuple[float, str, str]] | None = None,
    ref_markers: list[tuple[float, float, str, str]] | None = None,
    twin_ylabel: str | None = None,
    twin_y: list[float] | None = None,
) -> None:
    """Plot with optional reference horizontal lines and markers."""
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color_main = "tab:blue"
    ax1.plot(x, y, marker="o", linestyle="-", color=color_main,
             markersize=4, linewidth=1.5, label="StellarOrion")
    ax1.set_title(title, fontsize=13, fontweight="bold")
    ax1.set_xlabel(xlabel, fontsize=11)
    ax1.set_ylabel(ylabel, fontsize=11, color=color_main)
    ax1.tick_params(axis="y", labelcolor=color_main)
    ax1.grid(True, alpha=0.3)

    # Reference horizontal lines (e.g., peak values)
    if ref_lines:
        for val, label, color in ref_lines:
            ax1.axhline(y=val, color=color, linestyle="--", linewidth=1.2,
                        alpha=0.8, label=f"{label} = {val:.2f}")

    # Reference markers (e.g., specific x,y points from Rapisarda)
    if ref_markers:
        for mx, my, label, color in ref_markers:
            ax1.plot(mx, my, marker="*", markersize=12, color=color,
                     zorder=5, label=f"{label}")

    # Optional twin Y-axis
    if twin_ylabel and twin_y and len(twin_y) == len(x):
        ax2 = ax1.twinx()
        color_twin = "tab:red"
        ax2.plot(x, twin_y, marker="s", linestyle=":", color=color_twin,
                 markersize=3, linewidth=1.0, alpha=0.7, label=twin_ylabel)
        ax2.set_ylabel(twin_ylabel, fontsize=11, color=color_twin)
        ax2.tick_params(axis="y", labelcolor=color_twin)

    ax1.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_comparison_bars(
    out_path: str,
    metrics: list[tuple[str, float, float, str]],
) -> None:
    """Bar chart comparing StellarOrion vs Rapisarda for scalar metrics.
    metrics: list of (label, our_value, rapisarda_value, unit)
    """
    fig, axes = plt.subplots(1, len(metrics), figsize=(4 * len(metrics), 5))
    if len(metrics) == 1:
        axes = [axes]

    colors_so = "tab:blue"
    colors_ref = "tab:orange"

    for ax, (label, ours, ref, unit) in zip(axes, metrics):
        bars = ax.bar(
            ["StellarOrion", "Rapisarda"],
            [ours, ref],
            color=[colors_so, colors_ref],
            edgecolor="black",
            linewidth=0.5,
        )
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.set_ylabel(unit, fontsize=10)
        for bar, val in zip(bars, [ours, ref]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        # Percentage error
        if ref != 0:
            err = (ours - ref) / abs(ref) * 100.0
            ax.text(
                0.5, 0.95,
                f"Δ = {err:+.1f}%",
                ha="center",
                va="top",
                transform=ax.transAxes,
                fontsize=9,
                color="red" if abs(err) > 20 else "green",
                fontweight="bold",
            )

    fig.suptitle(
        "StellarOrion vs Rapisarda MDAO — Scalar Metrics Comparison",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str]) -> int:
    # Support multiple result directories for side-by-side comparison
    result_dirs = argv[1:] if len(argv) > 1 else ["results_validation"]

    all_data = {}
    for rdir in result_dirs:
        csv_path = os.path.join(rdir, "validation_timeseries.csv")
        if not os.path.isfile(csv_path):
            print(f"[rapisarda] CSV not found: {csv_path}", file=sys.stderr)
            continue
        steps, data_cols, col_names = _read_csv(csv_path)
        if not steps:
            print(f"[rapisarda] No data in: {csv_path}", file=sys.stderr)
            continue
        all_data[rdir] = (steps, data_cols, col_names)

    if not all_data:
        print("[rapisarda] No valid CSVs found.", file=sys.stderr)
        return 1

    total_plots = 0

    for rdir, (steps, data_cols, col_names) in all_data.items():
        plots_dir = os.path.join(rdir, "plots_rapisarda")
        os.makedirs(plots_dir, exist_ok=True)

        # Detect format (old 7-col vs new 17-col)
        has_trajectory = "time_s" in col_names

        if has_trajectory:
            # === NEW 17-COLUMN FORMAT: Full Rapisarda comparison ===
            #
            # IMPORTANT: SPARTA runs steady-state DSMC at a single freestream
            # condition (Mach 10, 52 km). The validation_timeseries.csv has
            # CONSTANT trajectory variables for all rows. For time-series plots,
            # we load the trajectory_profile.csv which contains the 1-DOF
            # ballistic entry profile (122 km → ground) with varying altitude,
            # velocity, Mach, g-load, dynamic pressure, etc.

            # --- Load trajectory profile CSV (1-DOF ballistic entry) ---
            traj_path = os.path.join(rdir, "trajectory_profile.csv")
            traj_time = traj_alt = traj_vel = traj_mach = None
            traj_dp = traj_cd_t = traj_g = traj_dr = None
            if os.path.isfile(traj_path):
                _traj_steps, _traj_cols, _traj_names = _read_csv(traj_path)
                # trajectory CSV uses "time_s" as first col (no step col)
                # Re-read as generic CSV
                with open(traj_path, "r", encoding="utf-8") as fh:
                    tlines = fh.read().splitlines()
                if tlines:
                    theader = [h.strip() for h in tlines[0].split(",")]
                    tdata = [[] for _ in range(len(theader))]
                    for traw in tlines[1:]:
                        traw = traw.strip()
                        if not traw:
                            continue
                        tparts = traw.split(",")
                        if len(tparts) < len(theader):
                            continue
                        try:
                            for tc in range(len(theader)):
                                tdata[tc].append(float(tparts[tc]))
                        except ValueError:
                            continue
                    # Map column names
                    tname_map = {n: i for i, n in enumerate(theader)}
                    traj_time = tdata[tname_map["time_s"]] if "time_s" in tname_map else None
                    traj_alt = tdata[tname_map["alt_km"]] if "alt_km" in tname_map else None
                    traj_vel = tdata[tname_map["vel_ms"]] if "vel_ms" in tname_map else None
                    traj_mach = tdata[tname_map["mach"]] if "mach" in tname_map else None
                    traj_dp = tdata[tname_map["dyn_press_pa"]] if "dyn_press_pa" in tname_map else None
                    traj_cd_t = tdata[tname_map["cd"]] if "cd" in tname_map else None
                    traj_g = tdata[tname_map["g_load"]] if "g_load" in tname_map else None
                    traj_dr = tdata[tname_map["downrange_km"]] if "downrange_km" in tname_map else None
                print(f"[rapisarda] Loaded trajectory profile: {len(traj_time or [])} points from {traj_path}")
            else:
                print(f"[rapisarda] WARNING: No trajectory_profile.csv in {rdir}; "
                      "using constant SPARTA values for time-series plots.")

            # --- SPARTA data (force/heat vs step) ---
            drag_sum = _get_col(col_names, data_cols, "drag_sum_N")
            lift_sum = _get_col(col_names, data_cols, "lift_sum_N")
            heat_max = _get_col(col_names, data_cols, "heatflux_max_Wm2")
            heat_load = _get_col(col_names, data_cols, "heat_load_jcm2")
            sparta_steps = steps  # integer step indices

            # --- Use trajectory profile for time-series Rapisarda plots ---
            t_time = traj_time if traj_time else _get_col(col_names, data_cols, "time_s")
            t_alt = traj_alt if traj_alt else _get_col(col_names, data_cols, "alt_km")
            t_vel = traj_vel if traj_vel else _get_col(col_names, data_cols, "vel_ms")
            t_mach = traj_mach if traj_mach else _get_col(col_names, data_cols, "mach")
            t_dp = traj_dp if traj_dp else _get_col(col_names, data_cols, "dyn_press_pa")
            t_cd = traj_cd_t if traj_cd_t else _get_col(col_names, data_cols, "cd")
            t_g = traj_g if traj_g else _get_col(col_names, data_cols, "g_load")
            t_dr = traj_dr if traj_dr else _get_col(col_names, data_cols, "downrange_km")

            # --- Figure 6.11 style: Altitude vs Time ---
            if t_time and t_alt:
                _plot_with_ref(
                    t_time, t_alt,
                    os.path.join(plots_dir, "01_altitude_vs_time.png"),
                    "Altitude vs Time (Rapisarda Fig 6.11)",
                    "Time (s)", "Altitude (km)",
                    ref_lines=[
                        (RAPISARDA_REFS["entry_alt_km"], "Entry Alt", "red"),
                    ],
                )
                total_plots += 1

            # --- Figure 6.11 style: Velocity vs Time ---
            if t_time and t_vel:
                _plot_with_ref(
                    t_time, t_vel,
                    os.path.join(plots_dir, "02_velocity_vs_time.png"),
                    "Velocity vs Time (Rapisarda Fig 6.11)",
                    "Time (s)", "Velocity (m/s)",
                    ref_lines=[
                        (RAPISARDA_REFS["entry_vel_ms"], "Entry Vel", "red"),
                    ],
                )
                total_plots += 1

            # --- Figure 4.6a: Mach vs Altitude ---
            if t_alt and t_mach:
                _plot_with_ref(
                    t_alt, t_mach,
                    os.path.join(plots_dir, "03_mach_vs_altitude.png"),
                    "Mach Number vs Altitude (Rapisarda Fig 4.6a)",
                    "Altitude (km)", "Mach Number",
                )
                total_plots += 1

            # --- Figure 4.6b: G-load vs Altitude ---
            if t_alt and t_g:
                _plot_with_ref(
                    t_alt, t_g,
                    os.path.join(plots_dir, "04_gload_vs_altitude.png"),
                    "G-Load vs Altitude (Rapisarda Fig 4.6b)",
                    "Altitude (km)", "G-Load (g)",
                    ref_lines=[
                        (RAPISARDA_REFS["peak_g_load"], "Rapisarda Peak", "red"),
                    ],
                )
                total_plots += 1

            # --- Figure 4.6c: Dynamic Pressure vs Altitude ---
            if t_alt and t_dp:
                _plot_with_ref(
                    t_alt, [q / 1000.0 for q in t_dp],
                    os.path.join(plots_dir, "05_dynpress_vs_altitude.png"),
                    "Dynamic Pressure vs Altitude (Rapisarda Fig 4.6c)",
                    "Altitude (km)", "Dynamic Pressure (kPa)",
                    ref_lines=[
                        (RAPISARDA_REFS["target_dyn_press_kPa"],
                         "Rapisarda Target", "red"),
                    ],
                )
                total_plots += 1

            # --- Figure 4.6d: Downrange vs Time ---
            if t_time and t_dr:
                _plot_with_ref(
                    t_time, t_dr,
                    os.path.join(plots_dir, "06_downrange_vs_time.png"),
                    "Downrange Distance vs Time (Rapisarda Fig 4.6d)",
                    "Time (s)", "Downrange (km)",
                )
                total_plots += 1

            # --- Figure 6.13: CD vs Time ---
            if t_time and t_cd:
                _plot_with_ref(
                    t_time, t_cd,
                    os.path.join(plots_dir, "07_cd_vs_time.png"),
                    "Drag Coefficient CD vs Time (Rapisarda Fig 6.13)",
                    "Time (s)", "CD",
                    ref_lines=[
                        (RAPISARDA_REFS["target_cd"], "Rapisarda Smooth", "orange"),
                        (RAPISARDA_REFS["target_cd_flight"], "IRVE-3 Flight", "green"),
                    ],
                )
                total_plots += 1

            # --- Figure 6.18: Heat Flux vs Step (SPARTA steady-state) ---
            if sparta_steps and heat_max:
                heat_max_Wcm2 = [q / 10000.0 for q in heat_max]
                _plot_with_ref(
                    sparta_steps, heat_max_Wcm2,
                    os.path.join(plots_dir, "08_heatflux_vs_step.png"),
                    "Peak Heat Flux vs SPARTA Step (Steady-State)",
                    "Step", "Heat Flux (W/cm²)",
                    ref_lines=[
                        (RAPISARDA_REFS["peak_heat_flux_Wcm2"],
                         "Rapisarda Peak", "red"),
                    ],
                )
                total_plots += 1

            # --- Heat Load from SPARTA (scalar comparison) ---
            if heat_load:
                _plot_with_ref(
                    sparta_steps, heat_load,
                    os.path.join(plots_dir, "09_heatload_vs_step.png"),
                    "Heat Load vs SPARTA Step",
                    "Step", "Heat Load (J/cm²)",
                    ref_lines=[
                        (RAPISARDA_REFS["total_heat_load_Jcm2"],
                         "Rapisarda Total", "red"),
                    ],
                )
                total_plots += 1

            # --- Drag Force vs SPARTA Step ---
            if sparta_steps and drag_sum:
                _plot_with_ref(
                    sparta_steps, drag_sum,
                    os.path.join(plots_dir, "10_drag_vs_step.png"),
                    "Drag Force vs SPARTA Step (Steady-State)",
                    "Step", "Drag Force (N)",
                )
                total_plots += 1

            # --- Scalar Comparison Bar Chart ---
            scalar_metrics = []
            if drag_sum:
                scalar_metrics.append(
                    ("Peak Drag", max(drag_sum), 0.0, "N (no Rapisarda ref)")
                )
            if heat_max:
                peak_hf = max(heat_max) / 10000.0
                scalar_metrics.append(
                    ("Peak Heat Flux", peak_hf,
                     RAPISARDA_REFS["peak_heat_flux_Wcm2"], "W/cm²")
                )
            if heat_load:
                scalar_metrics.append(
                    ("Total Heat Load", max(heat_load),
                     RAPISARDA_REFS["total_heat_load_Jcm2"], "J/cm²")
                )
            if t_g:
                scalar_metrics.append(
                    ("Peak G-Load", max(t_g),
                     RAPISARDA_REFS["peak_g_load"], "g")
                )
            if scalar_metrics:
                _plot_comparison_bars(
                    os.path.join(plots_dir, "11_scalar_comparison.png"),
                    scalar_metrics,
                )
                total_plots += 1

            # --- Trajectory Profile: Altitude vs Velocity ---
            if t_alt and t_vel:
                fig, ax = plt.subplots(figsize=(8, 6))
                sc = ax.scatter(t_vel, t_alt, c=t_time if t_time else range(len(t_alt)),
                                cmap="viridis", s=20, zorder=5)
                ax.plot(t_vel, t_alt, color="tab:blue", linewidth=1.0, alpha=0.5)
                cbar = fig.colorbar(sc, ax=ax)
                cbar.set_label("Time (s)")
                ax.set_xlabel("Velocity (m/s)", fontsize=11)
                ax.set_ylabel("Altitude (km)", fontsize=11)
                ax.set_title("Trajectory Profile — Altitude vs Velocity",
                             fontsize=13, fontweight="bold")
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(
                    os.path.join(plots_dir, "12_trajectory_alt_vs_vel.png"),
                    dpi=150, bbox_inches="tight",
                )
                plt.close(fig)
                total_plots += 1

        else:
            # === OLD 7-COLUMN FORMAT: Basic SPARTA metrics only ===
            drag_sum = _get_col(col_names, data_cols, "drag_sum_N")
            lift_sum = _get_col(col_names, data_cols, "lift_sum_N")
            heat_max = _get_col(col_names, data_cols, "heatflux_max_Wm2")
            heat_sum = _get_col(col_names, data_cols, "heat_sum_Wm2")

            if drag_sum:
                _plot_with_ref(
                    steps, drag_sum,
                    os.path.join(plots_dir, "drag_vs_step.png"),
                    "Drag Force vs SPARTA Step", "Step", "Drag (N)",
                )
                total_plots += 1

            if lift_sum:
                _plot_with_ref(
                    steps, [abs(l) for l in lift_sum],
                    os.path.join(plots_dir, "lift_vs_step.png"),
                    "|Lift| vs SPARTA Step", "Step", "|Lift| (N)",
                )
                total_plots += 1

            if heat_max:
                _plot_with_ref(
                    steps, [h / 10000.0 for h in heat_max],
                    os.path.join(plots_dir, "heatflux_vs_step.png"),
                    "Peak Heat Flux vs SPARTA Step", "Step",
                    "Heat Flux (W/cm²)",
                    ref_lines=[
                        (RAPISARDA_REFS["peak_heat_flux_Wcm2"],
                         "Rapisarda Peak", "red"),
                    ],
                )
                total_plots += 1

            if heat_sum:
                _plot_with_ref(
                    steps, heat_sum,
                    os.path.join(plots_dir, "heatsum_vs_step.png"),
                    "Heat Sum vs SPARTA Step", "Step", "Heat Sum (W/m²)",
                )
                total_plots += 1

            # Note about missing trajectory data
            print(
                f"[rapisarda] WARNING: Old CSV format in {rdir} — "
                f"no trajectory data. Re-run with updated Ada code to get "
                f"altitude/velocity/Mach/CD/g-load comparison plots.",
                file=sys.stderr,
            )

    print(f"[rapisarda] Wrote {total_plots} comparison plots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
