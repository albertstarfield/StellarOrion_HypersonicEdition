#!/usr/bin/env python3
"""
================================================================================
SCRIPT: make_validation_plots.py — Generic Validation Time-Series Plotter
================================================================================

AXIOMS:
  AXIOM 1: The Ada validation pipeline writes
           <results_dir>/validation_timeseries.csv with a header row
           followed by numeric data rows.
  AXIOM 2: The first column is always "step" (integer time index).
  AXIOM 3: All remaining columns are float metrics to plot vs step.
  AXIOM 4: matplotlib is importable in the host environment.

THEORIES:
  THEOREM 1: Any CSV column beyond "step" can be plotted generically by
             reading the header, parsing each column as float, and plotting
             column_name vs step.
  THEOREM 2: New CSV columns are auto-plotted without code changes.
  THEOREM 3: A missing/empty CSV is a non-fatal condition; print and exit 1.

APPLICATIONS:
  - Read <results_dir>/validation_timeseries.csv
  - Auto-detect all non-step columns from header
  - Plot each metric vs step as a separate PNG
  - Write PNGs into <results_dir>/plots/

CITATIONS:
  [Hunter2007] Hunter, J. D. "Matplotlib: A 2D Graphics Environment", 2007.

TIMING ANALYSIS:
  Estimated Processing Time: O(N * C) where N = rows, C = columns.
  WCET: < 1 s for typical validation runs (<= 100 rows, <= 10 columns).
================================================================================
"""
import csv
import os
import sys

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # headless / non-interactive backend


# Unit lookup for common column names (fallback: use raw column name)
# Handles both old 7-column and new 17-column CSV formats
_UNITS: dict[str, str] = {
    # Old format (7-col)
    "drag_sum_N": "Drag sum (N)",
    "lift_sum_N": "Lift sum (N)",
    "heatflux_max_Wm2": "Heat flux (W/m^2)",
    "heat_sum_Wm2": "Heat sum (W/m^2)",
    "drag_avg_N": "Avg drag (N)",
    "lift_avg_N": "Avg lift (N)",
    # New format (17-col) — Rapisarda MDAO trajectory variables
    "time_s": "Time (s)",
    "alt_km": "Altitude (km)",
    "vel_ms": "Velocity (m/s)",
    "mach": "Mach Number",
    "dyn_press_pa": "Dynamic Pressure (Pa)",
    "cd": "Drag Coefficient (CD)",
    "cl": "Lift Coefficient (CL)",
    "g_load": "G-Load (g)",
    "downrange_km": "Downrange (km)",
    "heat_load_jcm2": "Heat Load (J/cm^2)",
}


def _unit_for(col: str) -> str:
    """Return a human-readable Y-axis label for a column name."""
    return _UNITS.get(col, col.replace("_", " ").title())


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
                cols[c - 1].append(float(parts[c]))  # nosec: SMT_LOGIC_VERIFICATION — list length validated
        except ValueError:
            continue
    return steps, cols, header[1:]


def _plot(
    x: list[float],
    y: list[float],
    out_path: str,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    """Render a single validation plot and save to disk.

    AXIOM: x and y are equal-length lists of numeric data.
    THEOREM: Matplotlib produces publication-quality output at 120 DPI.
    APPLICATION: Writes PNG file to out_path.

    Args:
        x: Independent variable values (e.g., simulation steps).
        y: Dependent variable values (e.g., heat flux).
        out_path: Output file path for the PNG.
        title: Plot title.
        xlabel: X-axis label.
        ylabel: Y-axis label.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, marker="o", linestyle="-", color="tab:blue")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# Candidate columns for the full 0–300M DSMC+PINN_AUX trajectory.
# These names match `pinn_trajectory_per_step.csv`.
_FULL_COLUMNS: tuple[str, ...] = (
    "altitude_km",
    "velocity_ms",
    "mach_number",
    "heat_flux_avg_Wm2",
    "heat_flux_max_Wm2",
    "drag_sum_N",
    "lift_sum_N",
    "g_load",
    "cd",
    "cl",
    "heat_load_jcm2",
    "heat_sum_Wm2",
    "dynamic_pressure_Pa",
    "Sutton_Graves_Wcm2",
    "ambient_pressure_Pa",
    "ambient_temp_K",
    "knudsen_number",
    "reynolds_number",
)


def _read_full_trajectory(
    path: str,
) -> tuple[list[int], dict[str, list[float]]]:
    """Read `pinn_trajectory_per_step.csv` and return (steps, column data).

    AXIOM: The CSV has a `step` column and numeric metric columns.
    THEOREM: Only requested/available metric columns are parsed.
    APPLICATION: Enables full-span 0–300M DSMC+PINN_AUX plots.

    Args:
        path: Path to `pinn_trajectory_per_step.csv`.

    Returns:
        Tuple of (step list, {column_name: values}).
    """
    steps: list[int] = []
    columns: dict[str, list[float]] = {name: [] for name in _FULL_COLUMNS}
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                step = int(float(row.get("step", "")))
            except ValueError:
                continue
            steps.append(step)
            for name in _FULL_COLUMNS:
                raw = (row.get(name) or "").strip()
                if not raw:
                    columns[name].append(float("nan"))
                    continue
                try:
                    columns[name].append(float(raw))
                except ValueError:
                    columns[name].append(float("nan"))
    # Drop columns that are missing or entirely NaN.
    clean_columns = {
        name: values
        for name, values in columns.items()
        if values and any(value == value for value in values)  # noqa: PLR0124  # deliberate NaN test (x == x is False for NaN)
    }
    return steps, clean_columns


def _subsample(steps: list[int], values: list[float], max_points: int = 2000) -> tuple[list[int], list[float]]:
    """Evenly downsample paired x/y arrays for rendering speed.

    AXIOM: Inputs are equal-length numeric arrays.
    THEOREM: Output preserves endpoints and is deterministic.
    APPLICATION: Keeps 300k-row PINN trajectories renderable in <1s.

    Args:
        steps: X values.
        values: Y values.
        max_points: Maximum number of points to keep.

    Returns:
        Downsampled (steps, values).
    """
    if len(steps) <= max_points:
        return steps, values
    import math

    step_size = max(1, math.ceil(len(steps) / max_points))
    sampled_steps = steps[::step_size]
    sampled_values = values[::step_size]
    if sampled_steps[-1] != steps[-1]:
        sampled_steps.append(steps[-1])
        sampled_values.append(values[-1])
    return sampled_steps, sampled_values


def _plot_full_column(
    steps: list[int],
    values: list[float],
    out_path: str,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    """Render one full-span 0–300M DSMC+PINN_AUX plot and save it.

    AXIOM: `steps` covers the full trajectory, including DSMC and PINN.
    THEOREM: A vertical marker at step 2200 labels the DSMC+PINN_AUX boundary.
    APPLICATION: Writes a PNG that explicitly covers 0–300M steps.

    Args:
        steps: Full step axis.
        values: Metric values.
        out_path: Output PNG path.
        title: Plot title.
        xlabel: X-axis label (should state full coverage).
        ylabel: Y-axis label.
    """
    sampled_steps, sampled_values = _subsample(steps, values)
    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [2.0, 1.0]}
    )
    ax_top.plot(sampled_steps, sampled_values, linestyle="-", linewidth=1.1, color="tab:blue")
    ax_top.axvline(2200, color="tab:red", linestyle="--", linewidth=1.5, label="DSMC→PINN_AUX boundary (step 2200)")
    ax_top.axvspan(0, 2200, alpha=0.10, color="gray", label="DSMC window")
    ax_top.set_title(title)
    ax_top.set_xlabel(xlabel)
    ax_top.set_ylabel(ylabel)
    ax_top.grid(True, alpha=0.3)
    ax_top.legend(fontsize=8)

    dsmc_pairs = [(s, v) for s, v in zip(steps, values) if s <= 2200]
    if dsmc_pairs:
        dsmc_steps, dsmc_values = zip(*dsmc_pairs)
        ax_bottom.plot(dsmc_steps, dsmc_values, linestyle="-", linewidth=1.2, marker=".", markersize=2, color="tab:green")
        ax_bottom.axvline(2200, color="tab:red", linestyle="--", linewidth=1.2)
        ax_bottom.set_xlim(0, 2200)
        ax_bottom.set_title("DSMC-window jitter view (steps 0–2200, all available samples)")
        ax_bottom.set_xlabel("Step")
        ax_bottom.set_ylabel(ylabel)
        ax_bottom.grid(True, alpha=0.3)
    else:
        ax_bottom.axis("off")

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def make_full_pinn_plots(results_dir: str, plots_dir: str) -> int:
    """Write explicit 0–300M DSMC+PINN_AUX PNGs for the validation tree.

    AXIOM: `results_dir` may contain `pinn_trajectory_per_step.csv`.
    THEOREM: When present, it can render full-span DSMC+PINN_AUX metrics.
    APPLICATION: Adds explicit full-trajectory plots to the generic plot path.

    Args:
        results_dir: Validation result directory.
        plots_dir: Output plots directory.

    Returns:
        Number of full-span PNGs written.
    """
    full_csv = os.path.join(results_dir, "pinn_trajectory_per_step.csv")
    if not os.path.isfile(full_csv):
        nested = os.path.join(results_dir, "validation_pipeline_output", "pinn_trajectory_per_step.csv")
        if os.path.isfile(nested):
            full_csv = nested
        else:
            print(f"[plots] Full 300M trajectory CSV not found under {results_dir}")
            return 0
    steps, columns = _read_full_trajectory(full_csv)
    if not steps:
        print(f"[plots] No rows in {full_csv}", file=sys.stderr)
        return 0
    os.makedirs(plots_dir, exist_ok=True)
    count = 0
    for name, values in columns.items():
        if len(values) != len(steps):
            print(f"[plots] Full column '{name}' has {len(values)} values for {len(steps)} steps — skipped.")
            continue
        pretty = name.replace("_", " ").title()
        fname = f"{name}_vs_step_full_0_300M_dsmc_pinn.png"
        _plot_full_column(
            steps,
            values,
            os.path.join(plots_dir, fname),
            f"{pretty} vs Step — Full 0–300M DSMC+PINN_AUX",
            "Step (0=launch offset; 2200=DSMC→PINN_AUX boundary)",
            _unit_for(name),
        )
        count += 1
    print(f"[plots] Wrote {count} full 0–300M DSMC+PINN_AUX PNGs to {plots_dir}")
    return count


def main(argv: list[str]) -> int:
    """Generate per-column validation plots from time-series CSV.

    Reads all numeric columns from validation_timeseries.csv and produces
    one PNG plot per column using the _plot() helper.

    AXIOM: CSV file exists at results_dir/validation_timeseries.csv.
    THEOREM: Each column represents a distinct aerothermodynamic quantity.
    APPLICATION: Produces publication-quality per-metric plots.

    Args:
        argv: Command-line args. argv[1] is optional results directory.

    Returns:
        0 on success, 1 if CSV missing or empty.
    """
    results_dir = argv[1] if len(argv) > 1 else "results/validation"
    csv_path = os.path.join(results_dir, "validation_timeseries.csv")
    plots_dir = os.path.join(results_dir, "plots")
    if not os.path.isfile(csv_path):
        print(f"[plots] CSV not found: {csv_path}", file=sys.stderr)
        return 1
    os.makedirs(plots_dir, exist_ok=True)  # nosec: EXTERNAL_CALL_UNHANDLED — utility script, errors propagate to caller
    steps, data_cols, col_names = _read_csv(csv_path)
    if not steps:
        print("[plots] No data rows in CSV.", file=sys.stderr)
        return 1
    count = 0
    for col_idx, col_name in enumerate(col_names):
        values = data_cols[col_idx]  # nosec: SMT_LOGIC_VERIFICATION — bounds-safe via enumerate
        if len(values) != len(steps):
            print(
                f"[plots] Column '{col_name}' has {len(values)} values "
                f"but {len(steps)} steps — skipped.",
                file=sys.stderr,
            )
            continue
        fname = f"{col_name}_vs_step.png"
        _plot(
            steps,
            values,
            os.path.join(plots_dir, fname),
            f"{col_name.replace('_', ' ').title()} vs Step",
            "Step",
            _unit_for(col_name),
        )
        count += 1
    make_full_pinn_plots(results_dir, plots_dir)
    print(f"[plots] Wrote {count} PNGs to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
