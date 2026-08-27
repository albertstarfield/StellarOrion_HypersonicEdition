#!/usr/bin/env python3
"""
================================================================================
SCRIPT: make_validation_plots.py — Validation Time-Series Plotter (Library Bridge)
================================================================================

AXIOMS:
  AXIOM 1: The Ada validation pipeline writes
           <results_dir>/validation_timeseries.csv with columns:
           step, drag_sum_N, lift_sum_N, heatflux_max_Wm2.
  AXIOM 2: Each row is one SPARTA surf dump (every 100 steps) of the trajectory.
  AXIOM 3: matplotlib is importable in the host environment.

THEORIES:
  THEOREM 1: Plotting drag_sum_N, lift_sum_N, heatflux_max_Wm2 versus step yields
             trajectory-level trend plots for survivability inspection.
  THEOREM 2: A missing/empty CSV is a non-fatal condition; print and exit 1.

APPLICATIONS:
  - Read <results_dir>/validation_timeseries.csv
  - Render heatflux_max vs step, drag_sum vs step, lift_sum vs step as PNGs
  - Write PNGs into <results_dir>/plots/

CITATIONS:
  [Hunter2007] Hunter, J. D. "Matplotlib: A 2D Graphics Environment", 2007.

TIMING ANALYSIS:
  Estimated Processing Time: O(N) where N = number of CSV rows.
  WCET: < 1 s for typical validation runs (<= 100 rows).
================================================================================
"""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")  # headless / non-interactive backend
import matplotlib.pyplot as plt


def _read_csv(path: str) -> tuple[list[int], list[float], list[float], list[float]]:
    steps: list[int] = []
    drag: list[float] = []
    lift: list[float] = []
    heat: list[float] = []
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for raw in lines[1:]:
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(",")
        if len(parts) < 4:
            continue
        try:
            steps.append(int(float(parts[0])))
            drag.append(float(parts[1]))
            lift.append(float(parts[2]))
            heat.append(float(parts[3]))
        except ValueError:
            continue
    return steps, drag, lift, heat


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
    steps, drag, lift, heat = _read_csv(csv_path)
    if not steps:
        print("[plots] No data rows in CSV.", file=sys.stderr)
        return 1
    _plot(
        steps,
        heat,
        os.path.join(plots_dir, "heatflux_max_vs_step.png"),
        "Max Heat Flux vs Step",
        "Step",
        "Heat flux (W/m^2)",
    )
    _plot(
        steps,
        drag,
        os.path.join(plots_dir, "drag_sum_vs_step.png"),
        "Total Drag vs Step",
        "Step",
        "Drag sum (N)",
    )
    _plot(
        steps,
        lift,
        os.path.join(plots_dir, "lift_sum_vs_step.png"),
        "Total Lift vs Step",
        "Step",
        "Lift sum (N)",
    )
    print(f"[plots] Wrote 3 PNGs to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
