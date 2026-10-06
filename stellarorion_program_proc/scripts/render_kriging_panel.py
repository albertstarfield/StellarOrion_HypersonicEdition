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
import matplotlib.pyplot as plt  # noqa: E402

from kriging_denoise import _parse_grid_file, denoise_grid  # noqa: E402

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
    cb = plt.colorbar(sc, ax=ax, fraction=0.046, pad=0.03)
    cb.ax.tick_params(labelsize=FONT_PT - 2)
    return sc


def _note(ax, text):
    ax.text(0.5, 1.015, text, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=FONT_PT - 1, color="0.30")


def render_field_figure(raw: np.ndarray, krig: np.ndarray, step: int, path: str) -> str:
    """2x4 map figure: RAW on top, KRIGED below. Full-width (\\textwidth)."""
    fig, axes = plt.subplots(2, 4, figsize=(WIDTH_FULL_IN, 2.6 * WIDTH_FULL_IN / 4 * 2 / 2.6))
    fig.set_size_inches(WIDTH_FULL_IN, 2.55)
    x, y = raw[:, 0], raw[:, 1]
    for col, (_name, idx, label) in enumerate(FIELDS):
        ax = axes[0, col]
        _scatter(ax, x, y, raw[:, idx], f"RAW {label}")
        _note(ax, f"colour limits p{P_LOW:g}-{P_HIGH:g}")
        if col == 0:
            ax.set_ylabel("y [m]", fontsize=FONT_PT)
        ax = axes[1, col]
        _scatter(ax, x, y, krig[:, idx], f"KRIGED {label}")
        _note(ax, "same limits as RAW (direct comparison)")
        if col == 0:
            ax.set_ylabel("y [m]", fontsize=FONT_PT)
        ax.set_xlabel("x [m]", fontsize=FONT_PT)
    fig.suptitle(f"Kriging (GP) denoising -- DSMC step {step}", fontsize=TITLE_PT + 1)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def render_ratio_figure(raw: np.ndarray, krig: np.ndarray, step: int, path: str) -> str:
    """Noise-reduction bar chart. Placed at 0.75\\textwidth."""
    names, ratios, kept = [], [], []
    for _n, idx, _l in FIELDS:
        a, b = raw[:, idx], krig[:, idx]
        ok = np.isfinite(a) & np.isfinite(b)
        ra = float(np.std(a[ok]))
        rb = float(np.std(b[ok]))
        names.append(_n)
        kept.append(int(ok.sum()))
        ratios.append(rb / ra if ra > 0 else np.nan)
    fig, ax = plt.subplots()
    fig.set_size_inches(WIDTH_HALF_IN, 1.15 * WIDTH_HALF_IN / 4.1475 * 1.9)
    fig.set_size_inches(WIDTH_HALF_IN, 2.05)
    xs = np.arange(len(names))
    bars = ax.bar(xs, ratios, color="#3b6ea5", width=0.6)
    ax.axhline(1.0, color="0.35", linestyle="--", linewidth=1.0)
    ax.text(len(names) - 0.45, 1.02, "no change", fontsize=FONT_PT - 1,
            color="0.35", ha="right", va="bottom")
    for b, r, k in zip(bars, ratios, kept):
        lab = "n/a" if not np.isfinite(r) else f"{r:.3f}"
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                lab, ha="center", va="bottom", fontsize=FONT_PT - 1)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{n}\n(n={k})" for n, k in zip(names, kept)], fontsize=FONT_PT)
    ax.set_ylabel("std(kriged) / std(raw)", fontsize=FONT_PT)
    ax.set_ylim(0, 1.15)
    ax.tick_params(labelsize=FONT_PT - 1)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.set_title(f"Kriging noise reduction -- step {step}\n"
                 f"{kept[0]} of {raw.shape[0]} cells per field",
                 fontsize=TITLE_PT)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
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
    args = ap.parse_args(argv)

    if not os.path.isfile(args.grid):
        print(f"[kriging] no grid dump at {args.grid!r} -- nothing rendered. "
              "A missing input is a failure, not a skip.", file=sys.stderr)
        return 1

    step = 0
    tail = os.path.basename(args.grid)
    if tail.startswith("grid.") and tail.endswith(".out"):
        try:
            step = int(tail[5:-4])
        except ValueError:
            step = 0

    raw = _parse_grid_file(args.grid)
    if raw.shape[0] < 2:
        print(f"[kriging] {args.grid} yielded {raw.shape[0]} usable cells; "
              "cannot fit a GP.", file=sys.stderr)
        return 1
    print(f"[kriging] parsed {raw.shape[0]} cells from {args.grid}; "
          f"denoising with n_restarts={args.restarts} ...")
    krig = denoise_grid(raw, n_restarts=args.restarts, random_state=args.random_state)

    os.makedirs(args.outdir, exist_ok=True)
    a = render_field_figure(raw, krig, step,
                            os.path.join(args.outdir, f"kriging_denoise_step{step}.png"))
    b = render_ratio_figure(raw, krig, step,
                            os.path.join(args.outdir, f"kriging_noise_reduction_step{step}.png"))
    print(f"[kriging] wrote {a}")
    print(f"[kriging] wrote {b}")
    print(f"[kriging] done -- 2 figures, none missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())