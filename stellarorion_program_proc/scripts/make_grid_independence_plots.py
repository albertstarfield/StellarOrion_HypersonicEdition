#!/usr/bin/env python3
"""Grid-independence figures for the StellarOrion DSMC study.

PURPOSE
    Turn the three per-level ``case.json`` records written by the grid
    refinement campaign (``results/grid_independence/level_{1,2,3}``) into the
    publication figure the results chapter cites: the stagnation-point peak
    heat flux and the integrated drag force against the grid resolution, with
    the level-to-level change annotated.

AXIOMS
    A1  The only authoritative source of a level's quantity of interest is its
        own ``case.json`` (written by the runner when that run completed).  The
        figure never re-derives a number from a solver log or from a dump the
        runner did not bless.
    A2  A level whose ``case.json`` is missing, or whose ``status`` is not
        ``ok``, is reported and skipped -- the figure never silently plots a
        partial campaign.  A gap in the plotted series is the honest rendering
        of a missing level.
    A3  Convergence is *shown*, not asserted: the level-to-level percentage
        change is printed and annotated, so the reader sees which quantity has
        settled and which is still moving.

THEOREMS
    T1  If every level shares the same geometry and the same flight condition
        (A1), the only remaining difference between the levels is the grid, so
        the spread across levels IS the discretisation error.
    T2  The convergence statement is falsifiable: a further level that moved
        the quantity by more than the last plotted step would contradict it,
        and the annotation would show the contradiction rather than hide it.

APPLICATIONS
    ``python3 scripts/make_grid_independence_plots.py`` from the repository
    root writes ``results/grid_independence/grid_independence_qoi.png`` and
    ``grid_independence_qoi.csv``; ``--campaign DIR`` points it at another
    campaign tree and ``--outdir DIR`` at another output directory.

CITATIONS
    [Roache1998] P. J. Roache, *Verification and Validation in Computational
        Science and Engineering*, Hermosa, 1998, ch. 5 (grid convergence and
        the observed order of accuracy).
    [Celik2008] I. B. Celik et al., "Procedure for estimation and reporting of
        uncertainty due to discretization in CFD applications",
        *J. Fluids Eng.* 130 (2008), doi:10.1115/1.2960953.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import pairwise
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LEVEL_DIRS = ("level_1", "level_2", "level_3")
DEFAULT_CAMPAIGN = Path("results") / "grid_independence"


def load_levels(campaign: Path) -> list[dict]:
    """Read every level record of the campaign.

    Parameters:
        campaign: the campaign directory holding ``level_*`` subdirectories.

    Returns:
        A list of dicts, one per readable level, each carrying ``level``,
        ``n_grid``, ``n_cells``, ``qoi_value`` (peak heat flux, W/m^2),
        ``drag`` (N) and ``wall_time_s``.

    Raises:
        FileNotFoundError: the campaign directory does not exist.
        RuntimeError: no level produced a usable record.
    """
    if not campaign.is_dir():
        raise FileNotFoundError(f"grid-independence campaign not found: {campaign}")
    rows: list[dict] = []
    for name in LEVEL_DIRS:
        record = campaign / name / "case.json"
        if not record.is_file():
            print(f"[grid] {name}: no case.json - level skipped", file=sys.stderr)
            continue
        try:
            data = json.loads(record.read_text())
        except (OSError, json.JSONDecodeError) as exc:  # Murphy law: corrupt record
            print(f"[grid] {name}: unreadable case.json ({exc}) - level skipped", file=sys.stderr)
            continue
        status = str(data.get("status", "")).lower()
        if status != "ok":
            print(f"[grid] {name}: status={status!r} - level skipped", file=sys.stderr)
            continue
        secondary = data.get("secondary", {}) or {}
        rows.append(
            {
                "level": int(data.get("level", len(rows) + 1)),
                "n_grid": int(data.get("n_grid", 0)),
                "n_cells": int(data.get("n_cells", 0)),
                "qoi_value": float(data.get("qoi_value", 0.0)),
                "drag": float(secondary.get("drag", 0.0)),
                "wall_time_s": float(data.get("wall_time_s", 0.0)),
            }
        )
    if not rows:
        raise RuntimeError(f"no usable level record under {campaign}")
    rows.sort(key=lambda row: row["level"])
    return rows


def level_deltas(values: list[float]) -> list[float]:
    """Relative level-to-level change, in per cent.

    Parameters:
        values: the per-level series, ordered from coarse to fine.

    Returns:
        A list one element shorter than ``values``; element ``i`` is
        ``(v[i+1] - v[i]) / v[i] * 100``.  A zero reference value yields
        ``float('nan')`` rather than an exception, so one bad level cannot
        kill the whole figure.
    """
    out: list[float] = []
    for coarse, fine in pairwise(values):
        out.append((fine - coarse) / coarse * 100.0 if coarse else float("nan"))
    return out


def render(rows: list[dict], out_png: Path, out_csv: Path) -> None:
    """Draw the two-panel grid-independence figure and write the CSV.

    Parameters:
        rows: the level records returned by :func:`load_levels`.
        out_png: destination of the rendered PNG.
        out_csv: destination of the machine-readable table.

    Raises:
        OSError: an output path cannot be written.
    """
    labels = [f"L{row['level']}\n{row['n_grid']}x{row['n_grid']}" for row in rows]
    q_mw = [row["qoi_value"] / 1.0e6 for row in rows]
    drag_kn = [row["drag"] / 1.0e3 for row in rows]
    q_delta = level_deltas(q_mw)
    drag_delta = level_deltas(drag_kn)

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), constrained_layout=True)
    for ax, series, deltas, title, unit, colour in (
        (axes[0], q_mw, q_delta, "Stagnation-point peak heat flux", "MW/m$^2$", "#c0392b"),
        (axes[1], drag_kn, drag_delta, "Integrated drag force", "kN", "#1f77b4"),
    ):
        ax.plot(range(len(series)), series, "o-", color=colour, linewidth=2.0, markersize=7)
        for idx, value in enumerate(series):
            ax.annotate(f"{value:.3f}", (idx, value), textcoords="offset points",
                        xytext=(0, 10), ha="center", fontsize=8.5)
            if idx < len(deltas):
                ax.annotate(
                    f"{deltas[idx]:+.2f}%",
                    (idx + 0.5, (value + series[idx + 1]) / 2.0),
                    textcoords="offset points", xytext=(0, 9),
                    ha="center", va="bottom", fontsize=8.0, color="#555555",
                )
        ax.set_xticks(range(len(series)))
        ax.set_xticklabels(labels)
        ax.set_xlabel("Refinement level and grid resolution")
        ax.set_ylabel(f"{title} ({unit})")
        ax.set_title(f"{title} vs. grid level")
        ax.grid(True, alpha=0.3)
        margin = 0.08 * (max(series) - min(series) or max(abs(v) for v in series) or 1.0)
        #  WHY: the value labels sit 10 pt above the markers, so the top pad has
        #  to be larger than the bottom pad or the first label is clipped by the
        #  axis frame (measured on the first render of this figure).
        ax.set_ylim(min(series) - margin, max(series) + 2.5 * margin)

    fig.suptitle(
        "Grid independence of the DSMC surface quantities "
        "(same geometry and flight condition at every level)",
        fontsize=11,
    )
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["level", "n_grid", "n_cells", "peak_heat_flux_Wm2", "drag_N", "wall_time_s"])
        for row in rows:
            writer.writerow([row["level"], row["n_grid"], row["n_cells"],
                             f"{row['qoi_value']:.6f}", f"{row['drag']:.6f}",
                             f"{row['wall_time_s']:.3f}"])

    print(f"[grid] peak heat flux (MW/m^2): {', '.join(f'{v:.3f}' for v in q_mw)}")
    print(f"[grid] level-to-level change: {', '.join(f'{d:+.2f}%' for d in q_delta)}")
    print(f"[grid] integrated drag (kN): {', '.join(f'{v:.3f}' for v in drag_kn)}")
    print(f"[grid] level-to-level change: {', '.join(f'{d:+.2f}%' for d in drag_delta)}")
    print(f"[grid] wrote {out_png}")
    print(f"[grid] wrote {out_csv}")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Parameters:
        argv: argument list (``None`` uses ``sys.argv[1:]``).

    Returns:
        ``0`` on success, ``2`` when the campaign cannot be read.

    Raises:
        SystemExit: argparse's own usage errors.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN,
                        help="campaign directory holding level_* subdirectories")
    parser.add_argument("--outdir", type=Path, default=None,
                        help="output directory (default: the campaign directory)")
    args = parser.parse_args(argv)
    outdir = args.outdir or args.campaign
    try:
        rows = load_levels(args.campaign)
        render(rows, outdir / "grid_independence_qoi.png",
               outdir / "grid_independence_qoi.csv")
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"[grid] FAILED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
