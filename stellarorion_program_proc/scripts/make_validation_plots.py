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
from __future__ import annotations

import os
import sys

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # headless / non-interactive backend


# Unit lookup for common column names (fallback: use raw column name)
_UNITS: dict[str, str] = {
    "drag_sum_N": "Drag sum (N)",
    "lift_sum_N": "Lift sum (N)",
    "heatflux_max_Wm2": "Heat flux (W/m^2)",
    "heat_sum_Wm2": "Heat sum (W/m^2)",
    "drag_avg_N": "Avg drag (N)",
    "lift_avg_N": "Avg lift (N)",
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
                cols[c - 1].append(float(parts[c]))
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
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, marker="o", linestyle="-", color="tab:blue")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main(argv: list[str]) -> int:
    results_dir = argv[1] if len(argv) > 1 else "results_validation"
    csv_path = os.path.join(results_dir, "validation_timeseries.csv")
    plots_dir = os.path.join(results_dir, "plots")
    if not os.path.isfile(csv_path):
        print(f"[plots] CSV not found: {csv_path}", file=sys.stderr)
        return 1
    os.makedirs(plots_dir, exist_ok=True)
    steps, data_cols, col_names = _read_csv(csv_path)
    if not steps:
        print("[plots] No data rows in CSV.", file=sys.stderr)
        return 1
    count = 0
    for col_idx, col_name in enumerate(col_names):
        values = data_cols[col_idx]
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
    print(f"[plots] Wrote {count} PNGs to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
