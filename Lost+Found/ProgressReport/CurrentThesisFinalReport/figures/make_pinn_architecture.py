#!/usr/bin/env python3
"""Redraw figures/pinn_architecture.png so its labels print at 8 pt or more.

PURPOSE
    The imported artwork measures about 3.0 pt of printed text, and it carries
    a literal double hyphen. This script rebuilds the same schematic from the
    thesis sources so every declared size can be checked, and it corrects two
    factual errors the old artwork contains.

PARAMETERS
    None. Output path is FIGDIR / "pinn_architecture.png".

RETURNS
    Process exit code 0 on success.

EXCEPTIONS
    RuntimeError if the print scale or the inside canvas check fails, if a drawn
    string contains a dash the thesis forbids, or if the smallest printed text
    falls below MIN_PRINTED_PT.

AXIOMS
    A1. Printed point size equals declared point size times the placement
        scale, so the scale must be measured from the written file, never
        assumed. (Source: print_fit.save_to_print_width.)
    A2. Matplotlib draws a mathtext sub or superscript at SHRINK_FACTOR of its
        parent, and SHRINK_FACTOR is 0.7. A declared 9.5 pt subscript therefore
        prints at 6.65 pt and fails the floor, so any string carrying a script
        is declared at MATH_PT or above. (Source: matplotlib/_mathtext.py.)
    A3. A string that is wider than the canvas makes the tight crop grow on
        every fit attempt, so the loop cannot converge and the artist must be
        rejected before the first save. (Source: print_fit axiom A3.)

THEORIES
    T1. With three top boxes the middle loss formula at MATH_PT measures about
        3.3 in, which cannot fit a 1.4 in third of the canvas. Laying the two
        residual sources side by side and giving the loss the full width makes
        every element fit, so the layout changes and no font has to shrink.
    T2. Printing the implemented loss instead of the advertised one keeps the
        figure honest: the artwork claimed a plain three term sum, while
        chapter_03 lines 620 to 634 define a two stage weighted loss.

APPLICATIONS
    A1. The rebuilt figure replaces the artwork in chapter_02 at 0.9 of the
        text width, so PRINT_W_IN must stay equal to that include width.
    A2. The same script pattern serves the remaining redraw queue.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
    S. Li, K. Xu, H. Zhang, et al, "PINNs: A deep learning framework for
    solving forward and inverse problems involving PDEs", Journal of
    Computational Physics, 378, 686-707, 2021.
    Lu et al, DeepXDE, https://github.com/lululxvi/deepxde

CORRECTIONS APPLIED TO THE OLD ARTWORK
    1. Hidden layers are three of 64 neurons and the output is
        (rho, v_x, v_y, T), which is what the code builds:
        dde.nn.FNN([2] + [64] * 3 + [n_output], "tanh", "Glorot normal")
        with n_output = 4, targets raw_data[:, [2, 4, 5, 3]]. The artwork
        claimed four hidden layers of 128 and five outputs.
    2. The loss box shows the two stage weighted loss of chapter_03 rather
        than the plain three term sum the artwork advertised.
    3. The stage box is placed below the network instead of overlapping the
        third hidden column, because an overlap is a collision waiting to
        happen and adds no information.
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  backend must be forced first
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, shared measurement
import print_fit as pf  # noqa: E402  sibling module, shared print geometry

FIGDIR = pf.FIGDIR
assert FIGDIR.is_dir(), "figures directory not found: %s" % FIGDIR

PRINT_W_IN = 0.9 * pf.TEXT_W_IN
H = 4.12

TITLE_PT = 13.0
BOX_PT = 10.0
STAGE_LABEL_PT = 9.5
STRATEGY_PT = 9.0
MATH_PT = 11.5
COLUMN_PT = 9.5
SUBSUB_PT = 9.0
BP_PT = 10.0
MIN_PRINTED_PT = 8.0

INK = "#1F2937"
NODE_EDGE = "#1D4ED8"
NODE_FILL = "#60A5FA"
LINK = "#D1D5DB"
ORANGE = "#F59E0B"
SRC_FILL = "#EFF6FF"
SRC_EDGE = "#3B82F6"
LOSS_FILL = "#F5F3FF"
LOSS_EDGE = "#8B5CF6"
RED = "#DC2626"

MARGIN = 0.10
ROW_A_TOP = H - 0.56
ROW_A_H = 0.52
ROW_B_TOP = H - 1.24
ROW_B_H = 0.82
NODES_TOP = H - 2.28
ROW_PITCH = 0.24
COL_X = [0.75, 1.60, 2.45, 3.30, 4.15]
NODE_RX = 0.13
NODE_RY = 0.075
BP_X = 4.52

COLUMNS = (
    ("Input", "2 features"),
    ("Hidden 1", "64 neurons"),
    ("Hidden 2", "64 neurons"),
    ("Hidden 3", "64 neurons"),
    ("Output", "4 outputs"),
)

SOURCES = (
    ("PDE Residual", "(Navier-Stokes)"),
    ("DSMC Data", "Anchor Points"),
)

STAGE_LINES = (
    ("Stage 1", r"$\mathcal{L}^{(1)} = \mathcal{L}_{data}$"),
    ("Stage 2", r"$\mathcal{L}^{(2)} = \lambda_{PDE}\,\mathcal{L}_{PDE} + \mathcal{L}_{data}$"),
)

STRATEGY = "Pre-train on data, then fine-tune with physics residuals"
MAPPING = r"maps $\mathbf{x} = (x, r)$ to $(\rho, v_x, v_y, T)$"
BACKPROP = "Backpropagation (AutoDiff)"
TITLE = "Physics-Informed Neural Network (PINN) Architecture"


def box(ax: object, x0: float, y0: float, w: float, h: float,
        fill: str, edge: str, lw: float = 1.4) -> None:
    """Draw a rounded rectangle patch.

    :param ax: the axes to draw on.
    :param x0: left edge in inches.
    :param y0: bottom edge in inches.
    :param w: width in inches.
    :param h: height in inches.
    :param fill: face colour.
    :param edge: edge colour.
    :param lw: edge line width in points.
    :returns: None.
    """
    patch = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0.0,rounding_size=0.06",
        linewidth=lw, edgecolor=edge, facecolor=fill, zorder=2,
    )
    ax.add_patch(patch)


def bar(ax: object, x0: float, y0: float, x1: float, y1: float) -> None:
    """Draw a thick plain connector with no arrowhead.

    :param ax: the axes to draw on.
    :param x0: start x in inches.
    :param y0: start y in inches.
    :param x1: end x in inches.
    :param y1: end y in inches.
    :returns: None.
    """
    ax.plot([x0, x1], [y0, y1], color=ORANGE, linewidth=3.0,
            solid_capstyle="butt", zorder=3)


def node_rows() -> list:
    """Return the y centre of every node row, top row first.

    :returns: five y values in inches.
    """
    return [NODES_TOP - (r + 0.5) * ROW_PITCH for r in range(5)]


def build() -> object:
    """Build the figure.

    :returns: the matplotlib figure, with the axes on it as its only axes.
    """
    fig = plt.figure(figsize=(PRINT_W_IN, H))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    ax.text(PRINT_W_IN / 2.0, H - 0.30, TITLE, ha="center", va="center",
            fontsize=TITLE_PT, fontweight="bold", color=INK)

    usable = PRINT_W_IN - 2.0 * MARGIN
    src_w = (usable - 0.46) / 2.0
    src_y = ROW_A_TOP - ROW_A_H
    centres = []
    for i, (head, sub) in enumerate(SOURCES):
        x0 = MARGIN + i * (src_w + 0.46)
        box(ax, x0, src_y, src_w, ROW_A_H, SRC_FILL, SRC_EDGE)
        mid = x0 + src_w / 2.0
        centres.append(mid)
        ax.text(mid, src_y + ROW_A_H * 0.66, head, ha="center", va="center",
                fontsize=BOX_PT, fontweight="bold", color=INK)
        ax.text(mid, src_y + ROW_A_H * 0.28, sub, ha="center", va="center",
                fontsize=BOX_PT, color=INK)
    bar(ax, centres[0] + src_w / 2.0, src_y + ROW_A_H / 2.0,
        centres[1] - src_w / 2.0, src_y + ROW_A_H / 2.0)

    loss_y = ROW_B_TOP - ROW_B_H
    box(ax, MARGIN, loss_y, usable, ROW_B_H, LOSS_FILL, LOSS_EDGE)
    for i, (label, formula) in enumerate(STAGE_LINES):
        y = loss_y + ROW_B_H - 0.22 - i * 0.22
        ax.text(MARGIN + 0.14, y, label, ha="left", va="center",
                fontsize=STAGE_LABEL_PT, fontweight="bold", color=INK)
        ax.text(MARGIN + 0.95, y, formula, ha="left", va="center",
                fontsize=MATH_PT, color=INK)
        bar(ax, centres[i], src_y, centres[i], loss_y + ROW_B_H)
    ax.text(PRINT_W_IN / 2.0, loss_y + 0.17, STRATEGY, ha="center", va="center",
            fontsize=STRATEGY_PT, fontstyle="italic", color=INK)

    ys = node_rows()
    for c in range(len(COL_X) - 1):
        for y0 in ys:
            for y1 in ys:
                ax.plot([COL_X[c] + NODE_RX, COL_X[c + 1] - NODE_RX],
                        [y0, y1], color=LINK, linewidth=0.6, zorder=1)
    for x in COL_X:
        for y in ys:
            ax.add_patch(Ellipse((x, y), 2.0 * NODE_RX, 2.0 * NODE_RY,
                                 facecolor=NODE_FILL, edgecolor=NODE_EDGE,
                                 linewidth=1.0, zorder=4))

    arrow = FancyArrowPatch(
        (BP_X, ys[-1] - 0.22), (BP_X, ys[0] + 0.22),
        arrowstyle="-|>", mutation_scale=11.0, linewidth=1.4,
        color=RED, linestyle=(0, (5, 3)), zorder=5,
    )
    ax.add_patch(arrow)
    ax.text(BP_X + 0.21, sum(ys) / len(ys), BACKPROP, ha="center",
            va="center", rotation=90, fontsize=BP_PT, fontweight="bold",
            color=RED, zorder=5)

    for x, (name, sub) in zip(COL_X, COLUMNS):
        ax.text(x, ys[-1] - 0.30, name, ha="center", va="center",
                fontsize=COLUMN_PT, fontweight="bold", color=INK)
        ax.text(x, ys[-1] - 0.50, sub, ha="center", va="center",
                fontsize=SUBSUB_PT, color=INK)

    ax.text(PRINT_W_IN / 2.0, 0.24, MAPPING, ha="center", va="center",
            fontsize=MATH_PT, color=INK)
    return fig


def verify(fig: object, scale: float) -> None:
    """Check the written figure against the readability floor.

    :param fig: the figure that was written, still open.
    :param scale: placement scale reported by the print fit.
    :returns: None.
    :raises RuntimeError: if the smallest printed text is under the floor.
    """
    printed, why = fm.smallest_text_pt(fig, scale)
    print("smallest printed text %.2f pt (%s); floor %.1f pt"
          % (printed, why, MIN_PRINTED_PT))
    if printed < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is under the %.1f pt floor from %s. "
            "A parent below %.2f pt cannot carry a mathtext script, so raise "
            "MATH_PT or drop the script."
            % (printed, MIN_PRINTED_PT, why, MIN_PRINTED_PT / fm.SHRINK_FACTOR)
        )


def main() -> int:
    """Write the figure and verify it.

    :returns: 0 on success.
    """
    strings = [TITLE, STRATEGY, MAPPING, BACKPROP, STRATEGY]
    for head, sub in SOURCES:
        strings.extend([head, sub])
    for name, sub in COLUMNS:
        strings.extend([name, sub])
    for label, formula in STAGE_LINES:
        strings.extend([label, formula])
    pf.require_clean(*strings)

    fig = build()
    out, scale = pf.save_to_print_width(fig, "pinn_architecture.png",
                                        PRINT_W_IN, close=False)
    pf.assert_inside_canvas(fig)
    verify(fig, scale)
    plt.close(fig)
    print("wrote %s at print width %.4f in" % (out.name, PRINT_W_IN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())