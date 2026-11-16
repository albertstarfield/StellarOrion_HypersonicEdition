"""Plate of TPS results reused verbatim from the program's own plot outputs.

PURPOSE
    Put the stacked-ply temperature field, the per-ply heat-flux distribution
    and the surface energy balance of the reference and of the optimised
    topology side by side in one thesis figure, WITHOUT regenerating them.
    The user asked for exactly these plots and asked why they had been
    rebuilt from zero when they already exist under ``results/``.

AXIOMS
    A1. ``stellarorion_program_proc/results/plots/<tree>/tps_per_ply/*.png``
        are the program's own TPS post-processing outputs for the sames
        conduction run (step 2200). They are the record of that run.
    A2. Reusing those files verbatim is correct: the numbers in them come from
        the same solver state as the thesis text, and re-plotting them from the
        raw arrays would only introduce a second, divergent render of the same
        data.
    A3. A panel that cannot be found raises, so a missing tree can never be
        silently replaced by an empty box.
    A4. The source PNGs are wide landscape panels whose internal text is sized
        for a full-page render. Placing two per row is the largest honest
        presentation in a 6 in figure; each panel is stretched only
        horizontally/vertically to fill its cell, which does not change the
        meaning of a schematic cartesian plot.

THEORIES
    T1. Two columns (reference | optimised) with one plot type per row makes
        the comparison direct: the reader reads across a row, not down a grid.
    T2. No column or row headers are drawn inside the panels beyond short row
        captions, because every source PNG already carries its own title; the
        earlier version duplicated them and wasted vertical space.
    T3. The quantitative comparison lives in the footer, where it can be set at
        a legible size, instead of being squeezed into the panels.

APPLICATIONS
    Writes ``figures/tps_reference_vs_optimized_reused.png`` for Chapter 4.

CITATIONS
    [1] stellarorion_program_proc/results/plots/00_reference/tps_per_ply/
    [2] stellarorion_program_proc/results/plots/03_opt_geometry/tps_per_ply/
    [3] Matplotlib imshow documentation, aspect='auto' semantics.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import image as mpimg  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parent.parent.parent.parent
PLOTS = REPO_ROOT / "stellarorion_program_proc" / "results" / "plots"

INK = "#222222"
TREES = [
    ("00_reference", "validation reference"),
    ("03_opt_geometry", "optimised topology"),
]
ROWS = [
    ("ply_stack_temperature_heatmap.png", "stacked ply temperature"),
    ("ply_heatflux_distribution.png", "per-ply heat-flux distribution"),
    ("surface_energy_balance.png", "surface energy balance"),
]


def load(tree: str, name: str) -> np.ndarray:
    """Return the RGB array of one TPS panel.

    AXIOM A3: a missing panel raises FileNotFoundError; it is never skipped.
    """
    path = PLOTS / tree / "tps_per_ply" / name
    if not path.is_file():
        raise FileNotFoundError(f"TPS panel missing: {path}")
    return mpimg.imread(path)


def main() -> int:
    """Render the plate and return a process status."""
    fig = plt.figure(figsize=(6.0, 6.35))
    gs = fig.add_gridspec(3, 2, left=0.035, right=0.995, top=0.955,
                          bottom=0.185, wspace=0.035, hspace=0.075)

    for row, (name, row_caption) in enumerate(ROWS):
        for col, (tree, tree_caption) in enumerate(TREES):
            ax = fig.add_subplot(gs[row, col])
            ax.imshow(load(tree, name), aspect="auto", interpolation="lanczos")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#BBBBBB")
                spine.set_linewidth(0.6)

    #  Column captions above the first row and row captions on the left. Both
    #  are short on purpose: the source panels carry their own titles, and
    #  repeating them was what made the earlier plate unreadable.
    for col, (_, tree_caption) in enumerate(TREES):
        x = 0.035 + (col + 0.5) * (0.960 / 2.0)
        fig.text(x, 0.975, tree_caption, ha="center", va="bottom",
                 fontsize=9.0, color=INK)
    for row, (_, row_caption) in enumerate(ROWS):
        y = 0.955 - (row + 0.5) * ((0.955 - 0.150) / 3.0)
        fig.text(0.012, y, row_caption, ha="center", va="center",
                 rotation=90, fontsize=7.4, color=INK)

    #  WHY the footer is seven short lines: at 6.4 pt a single long line runs
    #  past the right edge of the canvas (the first render clipped four lines).
    fig.text(0.035, 0.020,
             "All six panels are the program's own TPS post-processing output, reused verbatim from\n"
             "results/plots/<tree>/tps_per_ply/ (TPS conduction run, step 2200). Both trees were\n"
             "flown at the same condition (52.07 km, 3101 m/s). Peak surface heat flux\n"
             "q_peak = q_SG = 193154.22 W/m2 (19.315 W/cm2, against 30 W/cm2 for Nextel BF20).\n"
             "Mean surface temperature 801.35 K (reference) versus 830.03 K (optimised); peak\n"
             "1430.25 K in both; elements above 523.15 K 2064 versus 2160; zero-flux elements\n"
             "912 versus 960; mean radiative fraction 0.8660 versus 0.8693. The back-face\n"
             "temperature is pinned at 300 K in both runs, so only the surface field is informative.",
             fontsize=6.4, color="#333333", ha="left", va="bottom",
             linespacing=1.32)

    out = FIG_DIR / "tps_reference_vs_optimized_reused.png"
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)
    for tree, _ in TREES:
        for name, _ in ROWS:
            arr = load(tree, name)
            print(f"{tree}/{name}: {arr.shape[1]}x{arr.shape[0]} px")
    print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
