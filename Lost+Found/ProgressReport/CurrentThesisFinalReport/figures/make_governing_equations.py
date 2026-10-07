#!/usr/bin/env python3
"""Redraw figures/governing_equations.png so its labels print at 8 pt or more.

PURPOSE
    The imported artwork prints its smallest text (the axiom chips) at about
    2.9 pt, which fails the 8 pt floor. This script rebuilds the governing
    equations derivation chain from the thesis sources so every declared size
    can be checked, and it corrects two factual errors the old artwork
    contains: a duplicate A3 axiom chip and an A7 chip placed before A6.

PARAMETERS
    None. Output path is FIGDIR / "governing_equations.png".

RETURNS
    Process exit code 0 on success, 1 on rejection.

EXCEPTIONS
    RuntimeError if the print scale or the inside canvas check fails, if a
    drawn string contains a dash the thesis forbids, or if the smallest
    printed text falls below MIN_PRINTED_PT.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
    Bird, G. A. (1994), Molecular Gas Dynamics, Clarendon Press.
    The thesis is typeset on A4 with 4 cm left and 3 cm right margins, so the
    text width in inches is 21.0/2.54 less (4.0+3.0)/2.54.

AXIOMS
    A1. Printed point size equals declared point size times the placement
        scale, so the scale must be measured from the written file, never
        assumed. (Source: print_fit.save_to_print_width.)
    A2. Matplotlib draws a mathtext sub or superscript at SHRINK_FACTOR of
        its parent, and SHRINK_FACTOR is 0.7. A declared 11.5 pt parent
        therefore prints its scripts at 8.05 pt, clearing the 8 pt floor.
    A3. A string that is wider than the canvas makes the tight crop grow on
        every fit attempt, so the loop cannot converge and the artist must be
        rejected before the first save. (Source: print_fit axiom A3.)
    A4. The original artwork carries a duplicate A3 chip and places A7 before
        A6. The redraw must present exactly A1 through A7 in order.

THEORIES
    T1. Six main boxes with two-line titles at 9 pt need about 4.9 in of width,
        which fits the 5.35 in usable width with 0.074 in gaps, so the chain
        stays horizontal and no font has to shrink below 9 pt.
    T2. The Boltzmann equation at 11.5 pt mathtext measures about 1.9 in, which
        cannot fit a 0.83 in box on one line. The collision term is therefore
        abbreviated to its standard operator form Q(f,f) inside the cell, and
        the full integral is printed once as a full-width note under the cell
        row, where no neighbouring cell constrains its width.
    T3. Five transition chips at 9 pt need about 5.5 in of width for the
        widest single line, which exceeds the 5.35 in usable width. Splitting
        them into two rows of three and two leaves each chip centred on its
        gap with no overlap.
    T4. Two printed labels collide only when their bounding boxes overlap by
        at least 3 pt in both axes (fm.text_overlaps_pt). For cells on the
        same row the x overlap is (w1+w2)/2 minus the 0.904 in pitch, so every
        same-row pair must sum below 136.2 pt; for rows one step apart the
        y overlap is (e1+e2)/2 minus the line pitch, so a 0.335 in pitch keeps
        the worst pair (27.0 pt sqrt extent against 23.3 pt beta extent) at
        1.03 pt, under the floor.

APPLICATIONS
    A1. The rebuilt figure replaces the artwork in chapter_03_methodology.tex
        at width=\textwidth, so PRINT_W_IN must stay equal to the text width.
    A2. The same script pattern serves the remaining redraw queue.

CORRECTIONS APPLIED TO THE OLD ARTWORK
    1. The axiom chips are renumbered A1 through A7 with no duplicate A3 and
       no A7 before A6, matching the research axiom table.
    2. The sixth main box reads "Bayesian survivability
       optimization" to match the chapter 3 caption, which the
       old artwork shortened to "GA Optimization".
    3. The Boltzmann equation carries proper f' primes, which the old artwork
       rendered without visible primes.
    4. Every equation is split into short lines whose same-row widths sum
       below 136.2 pt, and the collision term prints as Q(f,f) with the
       integral expanded in a full-width note, so no two labels overlap by
       3 pt or more (verify rejects the drawing otherwise).
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  backend must be forced first
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, shared measurement
import print_fit as pf  # noqa: E402  sibling module, shared print geometry

FIGDIR = pf.FIGDIR
assert FIGDIR.is_dir(), "figures directory not found: %s" % FIGDIR

PRINT_W_IN = pf.TEXT_W_IN
H = 5.12

TITLE_PT = 13.0
BOX_TITLE_PT = 9.0
CHIP_PT = 9.0
EQ_PT = 11.5
AXIOM_PT = 9.0
FOOTER_PT = 9.0
MIN_PRINTED_PT = 8.0

INK = "#2C3E50"
BOX_FILLS = ("#316383", "#3D82AF", "#4392C7", "#2B9A84", "#BE9F23", "#9D4037")
BOX_BORDER = "#2C3E50"
CHIP_FILL = "#FEFAEB"
CHIP_BORDER = "#F2EA9F"
CHIP_TEXT = "#7F8C8D"
EQ_BORDER = "#C0C6C9"
AXIOM_FILL = "#F7F1F9"
AXIOM_BORDER = "#DAC1E4"
AXIOM_TEXT = "#6C3483"
FOOTER_TEXT = "#7F8C8C"
ARROW_COLOR = "#2C3E50"

MARGIN_X = 0.08
N_BOX = 6
GAP = 0.074
BOX_W = (PRINT_W_IN - 2.0 * MARGIN_X - (N_BOX - 1) * GAP) / N_BOX
EQ_W = 0.90

TITLE = ("Governing Equations: Derivation Chain",
          "from Kinetic Theory to Optimization")

BOX_TITLES = (
    ("Kinetic", "Theory"),
    ("DSMC", "Method"),
    ("Navier-", "Stokes", "Equations"),
    ("Sutton-", "Graves", "Correlation"),
    ("PINN", "Refinement"),
    ("Bayesian", "survivability", "optimization"),
)

TRANSITIONS = (
    ("Discretize", "(Bird, 1994)"),
    ("Continuum", "Limit (Kn->0)"),
    ("Regression", "Correlation"),
    ("Neural", "Approximation"),
    ("Global", "Search"),
)

EQUATIONS = (
    (r"$\partial f/\partial t$",
     r"$+ \mathbf{v}\cdot\nabla f$",
     r"$= Q(f\!,\!f)$"),
    (r"$\Delta x\leq\lambda/3$",
     r"$\Delta t\leq1/\nu$"),
    (r"$\partial \rho/\partial t$",
     r"$+\nabla\cdot(\rho$",
     r"$\mathbf{u})=0$"),
    (r"$\dot{q}_s=k$",
     r"$\sqrt{\rho_\infty/R_N}$",
     r"$V_\infty^3$"),
    (r"$\mathcal{L}=\lambda_d$",
     r"$\mathcal{L}_{data}$",
     r"$+\lambda_{pde}$",
     r"$\mathcal{L}_{PDE}$"),
    (r"$J^*=$",
     r"$\min(\beta$",
     r"$-\beta_{target})^2$",
     r"$+\lambda\sum$",
     r"$\max(0,g_i)$"),
)

Q_DEF = r"$Q(f,f) = \int (f' f_1' - f f_1)\, g\, \sigma\, d\Omega\, d\mathbf{v}_1$"

AXIOMS = (
    ("A1:", "Conservation"),
    ("A2:", "Molecular Chaos"),
    ("A3:", "Continuum Assumption"),
    ("A4:", "M-B Distribution"),
    ("A5:", "Empirical Heating"),
    ("A6:", "Convergence Guarantee"),
    ("A7:", "PINN Consistency"),
)

FOOTER = "Bottom: Axiom references (Table 3.1)    Top: Transition methodology"

TMP_NAME = "governing_equations_tmp.png"
FINAL_NAME = "governing_equations.png"


def box_left(i: int) -> float:
    """Return the left edge x of main box i in inches.

    :param i: zero based box index.
    :returns: x coordinate of the left edge.
    """
    return MARGIN_X + i * (BOX_W + GAP)


def box_center(i: int) -> float:
    """Return the centre x of main box i in inches.

    :param i: zero based box index.
    :returns: x coordinate of the centre.
    """
    return box_left(i) + BOX_W / 2.0


def gap_center(i: int) -> float:
    """Return the centre x of the gap after box i in inches.

    :param i: zero based box index, 0 to 4.
    :returns: x coordinate of the gap centre.
    """
    return box_left(i) + BOX_W + GAP / 2.0


def draw_main_box(ax: object, i: int) -> None:
    """Draw main box i with its title text.

    :param ax: the axes to draw on.
    :param i: zero based box index.
    :returns: None.
    """
    x0 = box_left(i)
    y0 = 3.24
    patch = FancyBboxPatch(
        (x0, y0), BOX_W, 0.70,
        boxstyle="round,pad=0.0,rounding_size=0.05",
        linewidth=1.5, edgecolor=BOX_BORDER, facecolor=BOX_FILLS[i], zorder=2,
    )
    ax.add_patch(patch)
    lines = BOX_TITLES[i]
    n = len(lines)
    for k, line in enumerate(lines):
        y = y0 + 0.70 - 0.16 - k * 0.18
        ax.text(box_center(i), y, line, ha="center", va="center",
                fontsize=BOX_TITLE_PT, fontweight="bold", color="white",
                family="DejaVu Serif", zorder=3)


def draw_arrows(ax: object) -> None:
    """Draw the five right-arrows between the main boxes.

    :param ax: the axes to draw on.
    :returns: None.
    """
    y = 3.24 + 0.35
    for i in range(N_BOX - 1):
        x_from = box_left(i) + BOX_W - 0.01
        x_to = box_left(i + 1) + 0.01
        arrow = FancyArrowPatch(
            (x_from, y), (x_to, y),
            arrowstyle="-|>", mutation_scale=12.0, linewidth=1.5,
            color=ARROW_COLOR, zorder=1,
        )
        ax.add_patch(arrow)


def draw_transition_chips(ax: object) -> None:
    """Draw the five transition chips in two rows over the gaps.

    :param ax: the axes to draw on.
    :returns: None.
    """
    top_indices = (0, 2, 4)
    bot_indices = (1, 3)
    for row, indices in enumerate((top_indices, bot_indices)):
        y = 4.39 - row * 0.30
        for i in indices:
            cx = gap_center(i)
            patch = FancyBboxPatch(
                (cx - 0.55, y - 0.13), 1.10, 0.26,
                boxstyle="round,pad=0.0,rounding_size=0.04",
                linewidth=1.0, edgecolor=CHIP_BORDER, facecolor=CHIP_FILL,
                zorder=2,
            )
            ax.add_patch(patch)
            lines = TRANSITIONS[i]
            for k, line in enumerate(lines):
                ly = y + 0.06 - k * 0.12
                ax.text(cx, ly, line, ha="center", va="center",
                        fontsize=CHIP_PT, fontstyle="italic",
                        color=CHIP_TEXT, zorder=3)


def draw_equation_boxes(ax: object) -> None:
    """Draw the six equation boxes under the main boxes.

    :param ax: the axes to draw on.
    :returns: None.
    """
    for i in range(N_BOX):
        x0 = box_left(i)
        y0 = 1.50
        patch = FancyBboxPatch(
            (x0, y0), EQ_W, 1.74,
            boxstyle="round,pad=0.0,rounding_size=0.03",
            linewidth=1.0, edgecolor=EQ_BORDER, facecolor="white", zorder=2,
        )
        ax.add_patch(patch)
        lines = EQUATIONS[i]
        for k, line in enumerate(lines):
            # WHY: one shared pad and pitch keep row k at the same y in every
            # cell, so the guard's same-row x test and adjacent-row y test
            # both stay under the 3 pt floor (header T4).
            y = y0 + 1.74 - 0.211 - k * 0.335
            ax.text(box_center(i), y, line, ha="center", va="center",
                    fontsize=EQ_PT, color=INK, zorder=3)


def draw_axiom_chips(ax: object) -> None:
    """Draw the seven axiom chips in two rows at the bottom.

    :param ax: the axes to draw on.
    :returns: None.
    """
    top_axioms = AXIOMS[:4]
    bot_axioms = AXIOMS[4:]
    for row, group in enumerate((top_axioms, bot_axioms)):
        y = 0.85 - row * 0.38
        n = len(group)
        if n == 4:
            spacing = (PRINT_W_IN - 2.0 * MARGIN_X) / n
        else:
            spacing = (PRINT_W_IN - 2.0 * MARGIN_X) / 4.0
        for k, (label, desc) in enumerate(group):
            cx = MARGIN_X + spacing * (k + 0.5)
            patch = FancyBboxPatch(
                (cx - 0.55, y - 0.13), 1.10, 0.26,
                boxstyle="round,pad=0.0,rounding_size=0.04",
                linewidth=1.0, edgecolor=AXIOM_BORDER, facecolor=AXIOM_FILL,
                zorder=2,
            )
            ax.add_patch(patch)
            ax.text(cx, y + 0.06, label, ha="center", va="center",
                    fontsize=AXIOM_PT, color=AXIOM_TEXT, zorder=3)
            ax.text(cx, y - 0.06, desc, ha="center", va="center",
                    fontsize=AXIOM_PT, color=AXIOM_TEXT, zorder=3)


def build() -> object:
    """Build the figure.

    :returns: the matplotlib figure, with the axes on it as its only axes.
    """
    fig = plt.figure(figsize=(PRINT_W_IN, H))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    if isinstance(TITLE, tuple):
        for k, line in enumerate(TITLE):
            ax.text(PRINT_W_IN / 2.0, H - 0.20 - k * 0.22, line, ha="center", va="center",
                    fontsize=TITLE_PT, fontweight="bold", color=INK)
    else:
        ax.text(PRINT_W_IN / 2.0, H - 0.25, TITLE, ha="center", va="center",
                fontsize=TITLE_PT, fontweight="bold", color=INK)

    draw_transition_chips(ax)
    for i in range(N_BOX):
        draw_main_box(ax, i)
    draw_arrows(ax)
    draw_equation_boxes(ax)
    draw_axiom_chips(ax)

    # Full-width note expanding box 0's Q(f,f): no horizontal neighbours on
    # this row, so its 232 pt width cannot collide with any cell label.
    ax.text(PRINT_W_IN / 2.0, 1.25, Q_DEF, ha="center", va="center",
            fontsize=EQ_PT, color=INK)
    ax.text(PRINT_W_IN / 2.0, 0.13, FOOTER, ha="center", va="center",
            fontsize=FOOTER_PT, fontstyle="italic", color=FOOTER_TEXT)
    return fig


def verify(fig: object, scale: float) -> None:
    """Check the written figure against the readability and collision floors.

    :param fig: the figure that was written, still open.
    :param scale: placement scale reported by the print fit.
    :returns: None.
    :raises RuntimeError: if the smallest printed text is under the floor, or
        two printed labels overlap by at least 3 pt in both directions
        (fm.text_overlaps_pt reports the offending pairs so the collision is
        diagnosable from the failure alone).
    """
    printed, why = fm.smallest_text_pt(fig, scale)
    print("smallest printed text %.2f pt (%s); floor %.1f pt"
          % (printed, why, MIN_PRINTED_PT))
    if printed < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is under the %.1f pt floor from %s. "
            "A parent below %.2f pt cannot carry a mathtext script, so raise "
            "EQ_PT or drop the script."
            % (printed, MIN_PRINTED_PT, why, MIN_PRINTED_PT / fm.SHRINK_FACTOR)
        )
    overlaps = fm.text_overlaps_pt(fig, scale)
    if overlaps:
        detail = "; ".join(
            "%.1fx%.1f pt %s <> %s" % (ox, oy, a, b)
            for a, b, ox, oy in overlaps[:8]
        )
        raise RuntimeError("printed labels overlap: %s" % detail)


def main() -> int:
    """Write the figure and verify it.

    :returns: 0 on success, 1 on rejection.
    """
    strings = [TITLE, FOOTER, Q_DEF]
    for lines in BOX_TITLES:
        strings.extend(lines)
    for lines in TRANSITIONS:
        strings.extend(lines)
    for lines in EQUATIONS:
        strings.extend(lines)
    for label, desc in AXIOMS:
        strings.extend([label, desc])
    pf.require_clean(*strings)

    fig = build()
    pf.assert_inside_canvas(fig)
    out, scale = pf.save_to_print_width(fig, TMP_NAME, PRINT_W_IN, close=False)
    try:
        verify(fig, scale)
    except RuntimeError as exc:
        print("%s FAILED: %s" % (FINAL_NAME, exc), file=sys.stderr)
        plt.close(fig)
        os.unlink(out)
        return 1
    plt.close(fig)
    os.rename(out, FIGDIR / FINAL_NAME)
    print("wrote %s at print width %.4f in" % (FINAL_NAME, PRINT_W_IN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
