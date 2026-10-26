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

#  WHY a discovery function and not a fixed three-name tuple: the GCI needs at
#  least three levels, but a fourth is exactly how a series whose successive
#  differences GROW is resolved (review item #2).  A hard-coded tuple silently
#  ignored level_4 and would have reported the same non-monotone verdict after
#  the fourth solve had already been paid for.
LEVEL_PREFIX = "level_"


def level_dirs(campaign: Path) -> list[str]:
    """List the level directory names of a campaign, coarsest to finest.

    Parameters:
        campaign: the campaign directory holding ``level_*`` subdirectories.

    Returns:
        The directory names sorted by their numeric suffix, so ``level_10``
        sorts after ``level_9`` (a plain string sort would not).

    Raises:
        FileNotFoundError: the campaign directory does not exist.

    AXIOMS:
        A1  The level index in the directory name is the refinement order:
            level_1 is the coarsest grid and the highest index is the finest.
        A2  A campaign may hold any number of levels >= 1; the caller decides
            how many it needs (Richardson needs at least three).

    THEOREMS:
        T1  Sorting by ``int(name[len(LEVEL_PREFIX):])`` is monotone in the
            level index for every name this producer writes, and tolerates a
            two-digit index that a lexicographic sort would misplace.
    """
    if not campaign.is_dir():
        raise FileNotFoundError(f"grid-independence campaign not found: {campaign}")
    names = [
        entry.name
        for entry in campaign.iterdir()
        if entry.is_dir() and entry.name.startswith(LEVEL_PREFIX)
    ]
    return sorted(names, key=lambda n: int(n[len(LEVEL_PREFIX):]))

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
    rows: list[dict] = []
    for name in level_dirs(campaign):
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


def richardson(rows: list[dict], key: str) -> dict:
    """Estimate the grid-converged value of one quantity by Richardson extrapolation.

    Parameters:
        rows: the level records returned by :func:`load_levels`, coarse to fine.
        key: the quantity to extrapolate (``qoi_value`` or ``drag``).

    Returns:
        A dict with ``coarse``, ``medium``, ``fine`` (the FINEST three levels,
        i.e. the ones the order was fitted on), ``p`` (observed order of
        accuracy), ``exact`` (the extrapolated value), ``gci_pct`` (the fine-grid
        Grid Convergence Index, factor of safety 1.25), ``monotone`` (whether the
        three values converge monotonically) and ``n`` (how many levels were used).

    Raises:
        Nothing: a series with fewer than three levels, or one whose differences
        have opposite signs, falls back to the assumed first order and reports
        ``monotone = False`` rather than fabricating an order.

    AXIOMS:
        A1  The levels used share one geometry and one flight condition, so the
            only difference between them is the grid spacing.
        A2  The spacing scales as h ~ 1 / n_grid; the absolute factor cancels in
            every ratio below, so no cell size has to be measured.

    THEOREMS:
        T1  For a series that converges as f(h) = f_exact + C h^p, the observed
            order follows from the ratio of successive differences,
            (f1 - f2) / (f2 - f3) = (h1^p - h2^p) / (h2^p - h3^p); the right-hand
            side is strictly increasing in p, so the order is found by bisection
            and no assumption about the refinement ratio being constant is needed.
        T2  With p known, f_exact = f1 - C h1^p and C = (f1 - f2) / (h1^p - h2^p).

    CITATIONS:
        [Roache1998] Roache, Verification and Validation in Computational Science
            and Engineering, Hermosa, 1998 (the Grid Convergence Index).
        [Celik2008] Celik et al., J. Fluids Eng. 130(7) 078001, 2008,
            doi:10.1115/1.2960953 (the ASME V&V 20 procedure: observed order,
            extrapolated value, GCI with a factor of safety of 1.25 on three grids).

    WHY: the three-level campaign shows the peak heat flux is not converged; an
    extrapolated value and its GCI let the thesis state how far the production
    grid is from the limit instead of reporting only the two raw deltas.
    """
    values = [float(row[key]) for row in rows]
    h = [1.0 / float(row["n_grid"]) for row in rows if row["n_grid"]]
    #  WHY the triple is taken from the FINEST three: the observed order is a
    #  property of the last refinement step, so coarse/medium/fine must name the
    #  three values the fit actually used.  Reporting values[0] and values[1] in a
    #  four-level campaign labelled a fit that never touched them (measured: the
    #  CSV read coarse/medium = levels 1 and 2 while the order came from 2, 3, 4).
    out = {"coarse": values[-3] if len(values) >= 3 else values[0],
           "medium": values[-2] if len(values) >= 2 else values[0],
           "fine": values[-1], "p": 1.0, "exact": values[-1], "gci_pct": float("nan"),
           "monotone": False, "n": len(values)}
    if len(values) < 3 or len(h) < 3:
        return out
    h1, h2, h3 = h[-3], h[-2], h[-1]
    f1, f2, f3 = values[-3], values[-2], values[-1]
    d12, d23 = f1 - f2, f2 - f3
    if d12 == 0.0 or d23 == 0.0 or d12 * d23 <= 0.0:
        #  Non-monotone or already identical: no observed order can be extracted.
        return out
    target = d12 / d23

    def ratio(p: float) -> float:
        return (h1 ** p - h2 ** p) / (h2 ** p - h3 ** p)

    lo, hi = 0.05, 8.0
    if ratio(lo) > target or ratio(hi) < target:
        #  WHY: for f = f_exact + C h^p the ratio of successive differences is
        #  always > 1 (h1 > h2 > h3, p > 0).  A target at or below that bound means
        #  the differences do not shrink with refinement at all, so no observed
        #  order exists and NO extrapolated value may be claimed -- reporting one
        #  would be a fabricated number.  monotone stays False.
        return out
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if ratio(mid) < target:
            lo = mid
        else:
            hi = mid
    p_obs = 0.5 * (lo + hi)
    c = d12 / (h1 ** p_obs - h2 ** p_obs)
    exact = f1 - c * h1 ** p_obs
    out.update({"p": p_obs, "exact": exact, "monotone": True})
    if exact:
        out["gci_pct"] = 1.25 * abs(f1 - exact) / abs(exact) * 100.0
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

    #  WHY: the observed order and the GCI come from the same three levels as the
    #  plotted series; the extrapolated value is drawn as a dashed asymptote so the
    #  reader sees how far the finest grid still sits from the limit.
    rich_q = richardson(rows, "qoi_value")
    rich_d = richardson(rows, "drag")
    rich_q["exact_plot"] = rich_q["exact"] / 1.0e6
    rich_d["exact_plot"] = rich_d["exact"] / 1.0e3

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), constrained_layout=True)
    for ax, series, deltas, title, unit, colour, extrap in (
        (axes[0], q_mw, q_delta, "Stagnation-point peak heat flux", "MW/m$^2$", "#c0392b", rich_q),
        (axes[1], drag_kn, drag_delta, "Integrated drag force", "kN", "#1f77b4", rich_d),
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
        if extrap["monotone"]:
            ax.axhline(extrap["exact_plot"], color=colour, linestyle="--", linewidth=1.2,
                       alpha=0.75, label="Richardson limit")
            ax.annotate(
                f"Richardson: p = {extrap['p']:.2f}\n"
                f"limit = {extrap['exact_plot']:.3f} {unit}\n"
                f"GCI = {extrap['gci_pct']:.1f}% of the limit",
                xy=(0.02, 0.03), xycoords="axes fraction", ha="left", va="bottom",
                fontsize=8.0, color="#333333",
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "white",
                      "edgecolor": colour, "alpha": 0.85},
            )
        else:
            ax.annotate("Richardson limit not available\n(non-monotone series)",
                        xy=(0.02, 0.03), xycoords="axes fraction", ha="left", va="bottom",
                        fontsize=8.0, color="#777777")
        span = max(series + [extrap["exact_plot"]]) - min(series + [extrap["exact_plot"]])
        margin = 0.08 * (span or max(abs(v) for v in series) or 1.0)
        #  WHY: the value labels sit 10 pt above the markers, so the top pad has
        #  to be larger than the bottom pad or the first label is clipped by the
        #  axis frame (measured on the first render of this figure).
        low = min(min(series), extrap["exact_plot"]) - margin
        high = max(max(series), extrap["exact_plot"]) + 2.5 * margin
        ax.set_ylim(low, high)

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

    rich_csv = out_csv.with_name("grid_independence_richardson.csv")
    with rich_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["quantity", "unit", "coarse", "medium", "fine", "observed_order",
                         "extrapolated", "gci_pct_of_limit", "monotone", "levels_used"])
        for name, unit, extrap in (("peak_heat_flux", "W/m2", rich_q), ("drag", "N", rich_d)):
            writer.writerow([name, unit,
                             f"{extrap['coarse']:.6f}", f"{extrap['medium']:.6f}",
                             f"{extrap['fine']:.6f}",
                             f"{extrap['p']:.4f}" if extrap["monotone"] else "",
                             f"{extrap['exact']:.6f}" if extrap["monotone"] else "",
                             f"{extrap['gci_pct']:.4f}" if extrap["monotone"] else "",
                             str(extrap["monotone"]).lower(), extrap["n"]])

    print(f"[grid] peak heat flux (MW/m^2): {', '.join(f'{v:.3f}' for v in q_mw)}")
    print(f"[grid] level-to-level change: {', '.join(f'{d:+.2f}%' for d in q_delta)}")
    print(f"[grid] integrated drag (kN): {', '.join(f'{v:.3f}' for v in drag_kn)}")
    print(f"[grid] level-to-level change: {', '.join(f'{d:+.2f}%' for d in drag_delta)}")
    for name, unit, extrap in (("peak heat flux", "MW/m^2", rich_q), ("drag", "kN", rich_d)):
        if extrap["monotone"]:
            print(f"[grid] Richardson {name}: p = {extrap['p']:.2f}, limit = "
                  f"{extrap['exact_plot'] if name.startswith('peak') else extrap['exact'] / 1.0e3:.3f} "
                  f"{unit}, GCI = {extrap['gci_pct']:.1f}% of the limit")
        else:
            print(f"[grid] Richardson {name}: not available (non-monotone series)")
    print(f"[grid] wrote {out_png}")
    print(f"[grid] wrote {out_csv}")
    print(f"[grid] wrote {rich_csv}")


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
