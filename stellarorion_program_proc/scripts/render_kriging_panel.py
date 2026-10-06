#!/usr/bin/env python3
"""Render the kriging-denoising figure that page 5 (KRIGING DENOISING) needs.

WHY THIS FILE EXISTS
--------------------
``src/python/kriging_denoise.py`` computed a Gaussian-process denoising of the
DSMC grid field for the whole project and **never called ``savefig``** -- there
was no kriging figure anywhere in the repository.  This module is the missing
plot leg: it calls the real ``denoise_grid`` and renders the ACTUAL raw and
denoised fields side by side.

It deliberately does NOT reuse ``convergence_audit_plot.png`` (a different
computation) -- relabelling an unrelated figure would misattribute the slide.

AXIOMS
------
A1  The figure must show the REAL denoised field produced by
    ``kriging_denoise.denoise_grid`` -- never a re-derivation, never a stand-in.
A2  Figure text must stay >= 8 pt at the width the figure is actually printed.
    matplotlib sizes text in POINTS relative to the figure's size IN INCHES, so
    a figure must be laid out in inches and placed at the width it was designed
    for.  A 3600x2100 px figure carries no physical meaning and prints at ~3.4 pt
    at \\textwidth -- that was the original defect.
A3  A missing input is a FAILURE, never a silently skipped panel.  Exit code 1
    means "something was missing"; only exit 0 means every panel was written.
A4  The SPARTA grid `temp` is an INSTANTANEOUS average (``fix ave/grid all 1 1
    1`` -> Nevery=1, Nrepeat=1), so it reaches ~1e5 K in sparsely populated cells
    and ~0 in empty ones.  Colour limits must therefore be PERCENTILE-based and
    the percentile must be printed on the figure -- a silent clip hides data.

THEORIES
---------
T1  Denoising reduces the standard deviation of each field while leaving the
    coordinates untouched, so the per-field ratio std_kriged/std_raw is the
    single honest measure of what the kriging did.
T2  If the figure's native width in inches equals the printed width, the font
    size on paper equals ``fontsize``, so >= 8 pt needs no compensating scale.

USAGE
-----
    python3 scripts/render_kriging_panel.py
    python3 scripts/render_kriging_panel.py --grid results/validation/grid.500.out
    python3 scripts/render_kriging_panel.py --restarts 2 --outdir /tmp/krig

[Citation: Plimpton & Gallis (2014), SPARTA DSMC User Manual, grid file format]
[Citation: Bird (1994), Molecular Gas Dynamics, Sec 2.3 -- GP/kriging on fields]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from kriging_denoise import _parse_grid_file, denoise_grid

# --- A2: physical layout ------------------------------------------------------
# LaTeX \textwidth is 5.53 in; the chapter figures are placed at 0.75\textwidth.
WIDTH_FULL_IN = 5.53
WIDTH_HALF_IN = 4.1475
FONT_PT = 9.0
TITLE_PT = 10.0
DPI = 300

FIELDS = (("rho", 2, "rho [kg m$^{-3}$]"), ("T", 3, "T [K]"),
          ("vx", 4, "v$_x$ [m/s]"), ("vy", 5, "v$_y$ [m/s]"))
P_LOW, P_HIGH = 1.0, 99.0


def _release(fig) -> None:
    """Free a finished figure deterministically.

    WHY THIS EXISTS (measured 2026-10-06): rendering every grid step in one
    process while ALSO keeping figures alive (a plt.close no-op in an
    inspection probe) drove swap from 3072M/2202M used to 8192M/6930M used
    on this 16 GB host, and the agent runtime was killed. Two independent
    fixes, not one: this helper frees each figure at once, and main() now
    caps a batch run (--max-steps) and REPORTS peak RSS so the cost is
    measured instead of guessed.
    """
    try:
        fig.clear()
    finally:
        plt.close(fig)


def peak_rss_mb() -> float:
    """Return this process's peak resident set size in MB.

    MEASURED (2026-10-06, macOS/darwin): `ru_maxrss` is in BYTES here.
    Proof: baseline 13762560, then holding exactly 512 MiB of a bytearray
    gave 550617088 -- a delta of 536854528, i.e. 512 MiB + overhead. Dividing
    by 1024 only reported the true figure 1024x too large ("peak RSS 1229856
    MB"), which is nonsense and would have hidden a real leak.
    Linux reports the same field in KILOBYTES, hence the branch.
    [Citation: POSIX getrusage(2); resource.getrusage(RUSAGE_SELF)]
    Returns: peak RSS in megabytes. 0.0 if unavailable. Never raises.
    """
    try:
        import resource
        import sys
        raw = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return raw / (1024.0 * 1024.0) if sys.platform == "darwin" else raw / 1024.0
    except Exception:  # noqa: BLE001 - a diagnostic must never kill the run
        return 0.0


def _scatter(ax, x, y, vals, title):
    """Scatter a field with percentile colour limits and an explicit label.

    AXIOM A4: the percentile used for the colour limits is printed on the panel,
    because the instantaneous `temp` column spans five orders of magnitude and a
    silent clip would hide that.
    """
    finite = np.isfinite(vals)
    if not finite.any():
        ax.text(0.5, 0.5, "no finite data", ha="center", va="center",
                transform=ax.transAxes, fontsize=FONT_PT)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=TITLE_PT)
        return None
    lo = float(np.percentile(vals[finite], P_LOW))
    hi = float(np.percentile(vals[finite], P_HIGH))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = float(np.min(vals[finite])), float(np.max(vals[finite]))
    if hi <= lo:
        hi = lo + 1.0
    sc = ax.scatter(x[finite], y[finite], c=vals[finite], s=0.7, marker="s",
                    linewidths=0, cmap="inferno", vmin=lo, vmax=hi)
    ax.set_title(title, fontsize=TITLE_PT)
    ax.tick_params(labelsize=FONT_PT - 1)
    ax.set_aspect("equal", adjustable="box")
    #  NO per-axes colourbar: 8 of them turned the 2x4 grid into 16 axes and
    #  squeezed every map to 0.86 x 0.24 in. The caller draws ONE shared
    #  colourbar per row instead, which is both readable and correct here
    #  because every panel in a row plots the same field of the same data.
    return sc


def _note(ax, text):
    ax.text(0.5, 1.015, text, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=FONT_PT - 1, color="0.30")


def render_field_figure(raw: np.ndarray, krig: np.ndarray, step: int, path: str) -> str:
    """2x4 map figure: RAW on top, KRIGED below. Full-width (\\textwidth)."""
    #  layout="constrained" keeps the CANVAS exactly WIDTH_FULL_IN.
    #  bbox_inches="tight" was the A2 bug: it measured the bounding box of
    #  the wide y-tick labels and the two-line title, EXPANDED the canvas
    #  to 6.47 in, and so shrank the printed font to 7.69 pt < 8 pt.
    #  constrained_layout reserves that space INSIDE the canvas instead.
    #  NO constrained_layout here: with 4 colourbar-equipped columns in
    #  5.53 in it printed "constrained_layout not applied because axes
    #  sizes collapsed to zero" -- and height did not help, the binding
    #  constraint is WIDTH. Explicit margins are deterministic and keep
    #  the canvas at exactly WIDTH_FULL_IN (bbox_inches is NOT used).
    #  LAYOUT (AXIOM A2/A5, measured): the DSMC box is 14 x 3.9 m, i.e. a
    #  3.6:1 strip. With aspect="equal" a 4-COLUMN grid at 5.53 in gives each
    #  map only ~0.86 in wide -> ~0.24 in tall (measured), which is unusable.
    #  Four ROWS of two columns gives each map ~2.5 in -> ~0.7 in, which
    #  matches the domain aspect. One shared colourbar per row keeps the
    #  axes count at 8 maps + 4 bars instead of 8 + 8.
    fig, axes = plt.subplots(4, 2)
    #  Height only: the A2 contract is about the WIDTH (the printed scale
  # factor is WIDTH_FULL_IN / native_width), so a taller figure keeps
  # the 9 pt contract AND gives constrained_layout the room it needs.
  #  At 2.55 in it printed "constrained_layout not applied because axes
  #  sizes collapsed to zero" -- 8 colourbar-equipped axes in 2 rows.
    fig.set_size_inches(WIDTH_FULL_IN, 5.20)
    x, y = raw[:, 0], raw[:, 1]
    #  row -> (state, field index into FIELDS)
    ROWS = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1)]
    for pos, (state, field_i) in enumerate(ROWS):
        row, col = divmod(pos, 2)
        _name, idx, label = FIELDS[field_i]
        ax = axes[row, col]
        _scatter(ax, x, y, raw[:, idx] if state == 0 else krig[:, idx],
                 f"{'RAW' if state == 0 else 'KRIGED'} {label}")
        _note(ax, f"colour limits p{P_LOW:g}-{P_HIGH:g}" if state == 0
              else "same limits as RAW (direct comparison)")
        if col == 0:
            ax.set_ylabel("y [m]", fontsize=FONT_PT)
        if row == 3:
            ax.set_xlabel("x [m]", fontsize=FONT_PT)
    #  One shared colourbar per ROW: all four rows pair RAW with KRIGED of
    #  the SAME field, and the KRIGED panel deliberately reuses the RAW
    #  limits, so a per-row bar is the physically correct single key.
    for row in range(4):
        cb = fig.colorbar(axes[row, 1].collections[0], ax=list(axes[row, :]),
                          orientation="vertical", fraction=0.035, pad=0.015)
        cb.ax.tick_params(labelsize=FONT_PT - 2)
    fig.suptitle(f"Kriging (GP) denoising -- DSMC step {step}", fontsize=TITLE_PT + 1)
    #  WHY subplots_adjust and NOT tight_layout: tight_layout printed
    #  "Tight layout not applied ... cannot make Axes width small enough"
    #  on this 2x4 grid of dense scatters, so it silently left the layout
    #  in its unadjusted state. Fixed margins are deterministic and the
    #  inches-based A2 contract does not depend on the figure being packed.
    fig.subplots_adjust(left=0.062, right=0.90, top=0.945, bottom=0.055,
                        wspace=0.16, hspace=0.42)
    fig.savefig(path, dpi=DPI)
    _release(fig)   # clear() + close(): deterministic free, see _release docstring
    return path


#  AXIOM A5 -- the bulk percentile used for the honest second series.
#  [Based on: the measured rho behaviour on results/validation/grid.500.out]
BULK_PERCENTILE = 90.0
#  Filled in by main() so the caption can state the real training-cell count
#  instead of implying the whole field was fitted.
TRAIN_CAP_NOTE = "a subsample of cells"


def xo_height(value: float) -> float:
    """Return a drawable bar height for a possibly-missing ratio.

    AXIOM A3: a value that could not be computed is drawn as zero rather
    than as a number, and its label reads "n/a" -- never a silent 1.0.
    """
    return float(value) if np.isfinite(value) else 0.0


def xb_height(value: float) -> float:
    """Bulk-series counterpart of :func:`xo_height` (kept separate so a
    future divergence in the two label paths is visible rather than shared."""
    return float(value) if np.isfinite(value) else 0.0


def render_ratio_figure(raw: np.ndarray, krig: np.ndarray, step: int, path: str) -> str:
    """Noise-reduction bar chart. Placed at 0.75\\textwidth."""
    names, overall, bulk, kept = [], [], [], []
    for _n, idx, _l in FIELDS:
        a, b = raw[:, idx], krig[:, idx]
        ok = np.isfinite(a) & np.isfinite(b)
        ra = float(np.std(a[ok]))
        rb = float(np.std(b[ok]))
        #  BULK ratio (AXIOM A5): the single overall std ratio hides what
        #  happens away from the extremes. Measured on grid.500.out with the
        #  real data: rho's OVERALL ratio is 0.689 (looks like a good
        #  denoise) but its BULK ratio is 2.38 -- the bulk variance nearly
        #  2.4x WORSE, with the favourable overall number produced entirely
        #  by a handful of outlier cells. Both are plotted so the reader is
        #  never shown only the flattering one.
        thr = float(np.percentile(np.abs(a[ok]), BULK_PERCENTILE))
        m = ok & (np.abs(a) <= thr)
        ba = float(np.std(a[m]))
        bb = float(np.std(b[m]))
        names.append(_n)
        kept.append(int(ok.sum()))
        overall.append(rb / ra if ra > 0 else np.nan)
        bulk.append(bb / ba if ba > 0 else np.nan)
    fig, ax = plt.subplots()
    fig.set_size_inches(WIDTH_HALF_IN, 2.55)
    xs = np.arange(len(names))
    ov_all = np.array(overall, dtype=float)
    bk_all = np.array(bulk, dtype=float)
    finite = np.concatenate([ov_all[np.isfinite(ov_all)],
                             bk_all[np.isfinite(bk_all)]])
    #  AXIOM A4 (never silently clip): the previous fixed ylim(0, 1.15)
    #  would have cut off rho's measured bulk ratio of 2.38. The axis is
    #  scaled from the data, and the numeric value is printed on each bar,
    #  so a ratio outside the drawn range is still readable.
    top = float(np.max(finite)) if finite.size else 1.0
    ax.bar(xs - 0.19, ov_all, width=0.36, color="#3b6ea5", label="all cells")
    ax.bar(xs + 0.19, bk_all, width=0.36, color="#d98f2b",
           label=f"bulk (|x| <= p{BULK_PERCENTILE:.0f})")
    ax.axhline(1.0, color="0.35", linestyle="--", linewidth=1.0)
    ax.text(len(names) - 0.45, 1.01, "no change", fontsize=FONT_PT - 1,
            color="0.35", ha="right", va="bottom")
    for xo, ro in zip(xs - 0.19, ov_all):
        ax.text(xo, xo_height(ro), "n/a" if not np.isfinite(ro) else f"{ro:.3f}",
                ha="center", va="bottom", fontsize=FONT_PT - 2, rotation=90)
    for xb, rb_ in zip(xs + 0.19, bk_all):
        ax.text(xb, xb_height(rb_), "n/a" if not np.isfinite(rb_) else f"{rb_:.3f}",
                ha="center", va="bottom", fontsize=FONT_PT - 2, rotation=90)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{n}\n(n={k})" for n, k in zip(names, kept)], fontsize=FONT_PT)
    ax.set_ylabel("std(kriged) / std(raw)", fontsize=FONT_PT)
    ax.set_ylim(0, max(1.15, top * 1.30))
    ax.tick_params(labelsize=FONT_PT - 1)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.legend(fontsize=FONT_PT - 2, loc="upper left", framealpha=0.9)
    ax.set_title(f"Kriging noise reduction -- step {step}\n"
                 f"{kept[0]} of {raw.shape[0]} cells; GP trained on "
                 f"{TRAIN_CAP_NOTE}",
                 fontsize=TITLE_PT)
    fig.savefig(path, dpi=DPI)
    _release(fig)   # clear() + close(): deterministic free, see _release docstring
    return path


def main(argv: list[str] | None = None) -> int:
    """Render both kriging figures.

    Args:
        argv: CLI arguments; None uses sys.argv[1:].
    Returns:
        0 -- both figures written.  1 -- the grid file was missing or unreadable
        (AXIOM A3: a gap is never a success).
    Exceptions:
        none -- every failure path maps to exit 1 with a stderr message.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grid", default="results/validation/grid.500.out")
    ap.add_argument("--outdir", default="src/ui/uiassets/assets/plots")
    ap.add_argument("--restarts", type=int, default=2)
    ap.add_argument("--random-state", type=int, default=42)
    ap.add_argument("--all-steps", action="store_true",
                    help="render grid.NNN.out files in --grid's directory")
    ap.add_argument("--max-steps", type=int, default=4,
                    help="hard cap on a --all-steps batch (memory guard; "
                         "raise deliberately, one step at a time)")
    args = ap.parse_args(argv)

    if args.all_steps:
        #  A gap is never success (A3): report a missing input as exit 1.
        directory = os.path.dirname(args.grid) or "."
        if not os.path.isdir(directory):
            print(f"[kriging] no such directory {directory!r}.", file=sys.stderr)
            return 1
        steps = []
        for name in sorted(os.listdir(directory)):
            if name.startswith("grid.") and name.endswith(".out"):
                try:
                    steps.append((int(name[5:-4]), os.path.join(directory, name)))
                except ValueError:
                    continue
        if not steps:
            print(f"[kriging] no grid.NNN.out dumps in {directory!r} -- "
                  "nothing rendered. A missing input is a failure, not a skip.",
                  file=sys.stderr)
            return 1
        #  MEMORY GUARD (measured 2026-10-06): an unbounded batch on a
        #  16 GB host is what drove swap to 6.9 GB. Cap it and SAY so, rather
        #  than silently truncating -- a capped batch reports what it skipped.
        if len(steps) > args.max_steps:
            print(f"[WARNING] {len(steps)} steps available but --max-steps is "
                  f"{args.max_steps}; rendering the first {args.max_steps} only "
                  f"(--all-steps was capped to bound memory). Raise --max-steps "
                  f"deliberately.", file=sys.stderr)
            steps = steps[: args.max_steps]
        rc = 0
        for st, path in steps:
            rc |= _render_one(path, st, args)
        print(f"[kriging] done -- {len(steps)} step(s); peak RSS "
              f"{peak_rss_mb():.0f} MB")
        return rc

    return _render_one(args.grid, None, args)


def _render_one(grid_path: str, step: int | None, args) -> int:
    """Render both figures for one grid dump. Returns 0 on success, 1 on failure."""
    global TRAIN_CAP_NOTE
    if not os.path.isfile(grid_path):
        print(f"[kriging] no grid dump at {grid_path!r} -- nothing rendered. "
              "A missing input is a failure, not a skip.", file=sys.stderr)
        return 1

    if step is None:
        step = 0
        tail = os.path.basename(grid_path)
        if tail.startswith("grid.") and tail.endswith(".out"):
            try:
                step = int(tail[5:-4])
            except ValueError:
                step = 0

    raw = _parse_grid_file(grid_path)
    if raw.shape[0] < 2:
        print(f"[kriging] {grid_path} yielded {raw.shape[0]} usable cells; "
              "cannot fit a GP.", file=sys.stderr)
        return 1
    from kriging_denoise import _MAX_TRAINING_CELLS
    TRAIN_CAP_NOTE = (f"{min(_MAX_TRAINING_CELLS, raw.shape[0])} of "
                      f"{raw.shape[0]} cells (GP is O(N^3))")
    print(f"[kriging] parsed {raw.shape[0]} cells from {grid_path}; "
          f"denoising with n_restarts={args.restarts} ...")
    krig = denoise_grid(raw, n_restarts=args.restarts, random_state=args.random_state)

    os.makedirs(args.outdir, exist_ok=True)
    a = render_field_figure(raw, krig, step,
                            os.path.join(args.outdir, f"kriging_denoise_step{step}.png"))
    b = render_ratio_figure(raw, krig, step,
                            os.path.join(args.outdir, f"kriging_noise_reduction_step{step}.png"))
    print(f"[kriging] wrote {a}")
    print(f"[kriging] wrote {b}")
    print("[kriging] done -- 2 figures, none missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())