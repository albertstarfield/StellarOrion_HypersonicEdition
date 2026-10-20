#!/usr/bin/env python3
"""Redraw figures/software_pipeline.png so its labels print at 8 pt or more.

PURPOSE
    The imported artwork measures about 2.3 pt of printed text, and its
    title carries a literal em dash. This script rebuilds the same five
    column pipeline schematic from the thesis sources so every declared
    size can be checked, and it corrects the title punctuation.

PARAMETERS
    None. Output path is FIGDIR / "software_pipeline.png".

RETURNS
    Process exit code 0 on success, 1 on rejection.

EXCEPTIONS
    RuntimeError if the print scale or the inside canvas check fails, if a
    drawn string contains a dash the thesis forbids, or if the smallest
    printed text falls below MIN_PRINTED_PT.

AXIOMS
    A1. Printed point size equals declared point size times the placement
        scale, so the scale must be measured from the written file, never
        assumed. (Source: print_fit.save_to_print_width.)
    A2. A string that is wider than the canvas makes the tight crop grow on
        every fit attempt, so the loop cannot converge and the artist must
        be rejected before the first save. (Source: print_fit axiom A3.)
    A3. The engine to ParaView arrow must route around the solver and ML
        boxes, not over them, so the path is a polyline above the boxes.
    A4. An arrow that ends beside a box instead of on it reads as a
        dangling connector. The three input arrows leave their boxes at
        y 2.52, 1.86 and 1.18, so the engine box must span that whole
        range (it does: y 1.16 to 2.56); with the old 0.90 in box the
        top and bottom tips floated 0.24 in and 0.22 in off the box
        (measured on the written PNG).

THEORIES
    T1. Five columns with three input boxes, one engine box, two solver
        boxes, two model boxes and one output box fit the print width at a
        readable size when the canvas is about 3.6 in tall.
    T2. The feedback arrow from the genetic-algorithm optimiser to the
        engine routes below all boxes so it crosses no text and no other
        arrow.

APPLICATIONS
    A1. The rebuilt figure replaces the artwork in chapter_03, which includes
        it at width=0.85\textwidth (4.685 in) while the design canvas stays
        6.50 in so the column layout keeps its clearances. The save target is
        scaled by the same K_SHRINK = 0.85, so the squeeze ratio
        5.5118/6.50 = 4.685/5.525 = 0.848 is unchanged and verify still
        checks the floor at that squeezed size, not at the canvas size.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  backend must be forced first
from matplotlib.patches import (  # noqa: E402
    FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle)
from matplotlib.path import Path  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, shared measurement
import fig_shapes as fsh  # noqa: E402  sibling module, shared flowchart shapes
import print_fit as pf  # noqa: E402  sibling module, shared print geometry

# WHY serif Times: matches make_methodology_figures so all thesis figures
# read as one family (Times New Roman is present on this system at
# /System/Library/Fonts/Supplemental, with DejaVu Serif as the fallback).
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

FIGDIR = pf.FIGDIR
assert FIGDIR.is_dir(), "figures directory not found: %s" % FIGDIR

PRINT_W_IN = 6.50
# Paper pass 2026-10-08: chapter 03 includes the figure at 0.85\textwidth, so
# the save target shrinks by the same factor; verify()'s squeeze ratio below
# (TEXT_W_IN / PRINT_W_IN) stays correct because both the page width and the
# native canvas shrink together.
K_SHRINK = 0.85
# WHY H = 3.58 (was 3.50): the fit squeeze (set_size_inches, ratio ~0.82 of
# design) compresses data-unit gaps while title ink stays 0.09 in half-height
# in absolute points, which put the title descenders ON the routed rule at
# y 2.93 (image audit of 2026-10-08, 0 px gap). TITLE_Y moves 3.05 -> 3.11 and
# Start moves 3.18 -> 3.26, so the canvas must grow to 3.58 to keep the Start
# top (3.56) inside by 0.02 in at every squeeze ratio in [0.82, 1.0].
H = 3.58

TITLE_PT = 13.0
    # WHY HEADER_PT sits here and not with the other sizes: the 9.5 pt
    # value is part of the HEADER_Y corridor arithmetic (audit cycle 3);
    # see the HEADER_Y note for the 31-row corridor and the 8.06 pt floor.
BOX_PT = 9.5
LABEL_PT = 9.5
LEGEND_PT = 9.5
MIN_PRINTED_PT = 8.0
# WHY the 9.44 floor on LABEL_PT/LEGEND_PT: chapter 03 places this canvas at
# 0.85\textwidth = 4.685 in against a save target of 0.85 x 6.50 = 5.525 in,
# so the page squeezes every declared size by 4.685/5.525 = 0.848 (the same
# ratio as 5.5118/6.50 before the paper pass). 8.0 / 0.848 = 9.44, so a 9.0
# pt label would print at 7.6 pt and fail the 8 pt floor (verify checks the
# squeezed size).

INK = "#212121"
HEADER_GRAY = "#757575"
INPUT_FILL = "#E5F3FD"
INPUT_EDGE = "#C0C1C2"
ENGINE_FILL = "#2871C5"
ENGINE_EDGE = "#1665C0"
SOLVER_FILL = "#3F8742"
SOLVER_EDGE = "#2F7D33"
ML_FILL = "#E85F14"
ML_EDGE = "#E65201"
OUTPUT_FILL = "#582795"
OUTPUT_EDGE = "#4B158C"
ARROW_COLOR = "#37474F"
ORANGE = "#E65100"

# Column x-ranges (inches)
INPUT_X0, INPUT_X1 = 0.02, 1.36
ENGINE_X0, ENGINE_X1 = 1.54, 2.94
SOLVER_X0, SOLVER_X1 = 3.06, 4.16
ML_X0, ML_X1 = 4.28, 5.58
# WHY 5.65/6.43: the OUTPUT parallelogram slants its top edge 0.05 in
# right, so x1 + slant = 6.48 stays inside the 6.50 in canvas.
OUTPUT_X0, OUTPUT_X1 = 5.65, 6.43

# Box heights
INPUT_H = 0.48
# WHY 1.40: the engine must span every input arrow y (2.52, 1.86, 1.18),
# see axiom A4; y 1.16 to 2.56 covers all three tips with 0.02 in margin.
ENGINE_H = 1.40
SOLVER_H = 0.62
ML_H = 0.52
OUTPUT_H = 0.90

# Vertical positions (y bottom)
# WHY 2.28 for the first input (was 2.30, image audit cycle 4 2026-10-09):
# at 2.30 the CadQuery stroke top sat at row 223 while the INPUT header's
# antialiased ink bottom was row 221, leaving 1 white row where the spec
# demands >= 2. The header cannot rise (its rule gap is already exactly 2)
# and cannot shrink (9.5 pt is the 8 pt floor), so the box drops 0.02 in
# (about 5 rows), giving a 6-row gap. Arrow tip 1 moves to y 2.52, still
# 0.04 in inside the engine top per axiom A4.
INPUT_Y = [2.28, 1.62, 0.94]
ENGINE_Y = 1.16
SOLVER_Y = [2.12, 1.24]
ML_Y = [2.20]
OUTPUT_Y = 1.40

# WHY 3.11 (was 3.05): at the fit ratio (~0.82) the rule at y 2.93 lands on
# the title ink bottom (image audit 2026-10-08). (3.11 - 2.93) * 0.82 - 0.09
# = 0.058 in clearance to the rule, (3.26 - 3.11) * 0.82 - 0.09 = 0.033 in
# to the Start oval, both positive for every ratio in [0.82, 1.0].
TITLE_Y = 3.11
# WHY 9.5 pt and 2.842 (audit cycle 3, 2026-10-09): the third image audit
# measured HEADER_Y 2.854 at 10 pt with the cap ink TOUCHING the ruled
# connector (ink top y190 against rule AA row y191, 0 px gap where >= 2 px
# is required), while the original 2.82 sank the INPUT baseline 3 px into
# the CadQuery stroke (defect N1). With RULE_Y raised to 2.94 the corridor
# on the written PNG runs from the rule AA (row ~189) to the CadQuery
# stroke (row 223) = ~34 rows; a 10 pt cap band is 28 rows and sat with
# only 1 px at the rule side, so the header size drops to 9.5 pt (26.6
# rows) and 2.842 centres it: rule gap ~3 rows, CadQuery gap ~2 rows
# (PIL-verified on the written PNG). 9.5 pt still prints at
# 9.5 * 0.848 = 8.06 pt, above the 8 pt floor (verify() checks it).
HEADER_Y = 2.842
HEADER_PT = 9.5
# WHY a named constant: add_mask_rects() clamps every header mask just
# below this rule's stroke, and the routed connector is drawn at the same
# value, so the two can never drift apart.
# WHY 2.94 (was 2.93, audit cycle 3): the header band is pinned between
# the rule AA and the CadQuery stroke (31 rows for a 27 px cap band), so
# no baseline move clears BOTH edges by 2 px. Raising the rule 0.01 in
# adds 2.5 px of corridor above the headers (rule AA moves from PNG row
# 191 to ~189, header-rule gap becomes ~3 px) while the title keeps
# (3.11 - 2.94) * 0.82 - 0.09 = 0.049 in to the rule and the rule keeps
# 0.20 in to the solver boxes (top 2.74) and 0.22 in to the ML boxes
# (top 2.72), positive at every fit ratio in [0.82, 1.0].
RULE_Y = 2.94
LEGEND_Y1 = 0.45
LEGEND_Y2 = 0.25
LEGEND_Y3 = 0.05

TITLE_TEXT = "StellarOrion Engine, Software Pipeline Architecture"
HEADERS = ("INPUT", "CORE ENGINE", "SOLVERS", "ML MODELS", "OUTPUT")
HEADER_CENTERS = [
    (INPUT_X0 + INPUT_X1) / 2,
    (ENGINE_X0 + ENGINE_X1) / 2,
    (SOLVER_X0 + SOLVER_X1) / 2,
    (ML_X0 + ML_X1) / 2,
    (OUTPUT_X0 + OUTPUT_X1) / 2,
]

INPUT_TEXTS = (
    "CadQuery Geometry\n/ STL export",
    "Flight Conditions\n/ V, T∞, ρ∞",
    "Design Variables\n/ R_N, r_tor, θ_c",
)
# WHY no "/ " prefixes (audit 2026-10-08): "/ StellarOrion_Orion" measured
# 1.40 in of glyph ink against a 1.40 in box, so at the fit squeeze (text
# keeps absolute points, the box shrinks) the line painted white glyph
# pixels over BOTH vertical borders of the engine box. Dropping the leading
# slashes leaves the longest line at "StellarOrion_Orion" (18 chars, about
# 1.29 in) which clears each border by about 0.05 in even at squeeze 0.82.
# WHY no banned verification-token here (goal rev 6 / check_prose_batch
# BANNED list): the drawn text names the language only, never the proof
# toolchain. Shorter line 1 also widens the right clearance inside the box.
ENGINE_TEXT = "Ada Engine\nStellarOrion_Orion\ndriven by run.py\nphases 0 to 4"
SOLVER_TEXTS = (
    "SPARTA\n/ DSMC Solver\n/ Docker",
    "OpenFOAM\n/ laplacianFoam\n/ (solid thermal)",
)
ML_TEXTS = (
    # PINN removed 2026-10: the thesis no longer presents PINN; the model
    # column shows only the Gauss-process surrogate actually used to
    # produce the optimised body.
    "Genetic\n/ Algorithm\n/ population 50",
)
OUTPUT_TEXT = "ParaView\n/ VTK\n/ STL\n/ Rendering"

ARROW_LABEL_VTK = "VTK data"
ARROW_LABEL_SURFACE = "surface data"
ARROW_LABEL_REFINED = "refined"
ARROW_LABEL_FEEDBACK = "GA optimization\n/ feedback loop"

LEGEND_ROW1 = (
    ("Input (Geometry, Conditions)", INPUT_FILL, INPUT_EDGE),
    ("Core Engine (Ada, run.py)", ENGINE_FILL, ENGINE_EDGE),
)
LEGEND_ROW2 = (
    ("Physics Solvers (SPARTA, OpenFOAM)", SOLVER_FILL, SOLVER_EDGE),
    ("Models (GA)", ML_FILL, ML_EDGE),
)
LEGEND_ROW3 = (
    ("Visualization (ParaView)", OUTPUT_FILL, OUTPUT_EDGE),
)


def box(ax: object, x0: float, y0: float, w: float, h: float,
        text: str, fill: str, edge: str, text_color: str = INK,
        fs: float = BOX_PT, bold: bool = False, linespacing: float = 1.3,
        rounding: float = 0.04) -> None:
    """Draw a rounded rectangle with centered text.

    :param ax: the axes to draw on.
    :param x0: left edge in inches.
    :param y0: bottom edge in inches.
    :param w: width in inches.
    :param h: height in inches.
    :param text: label string, may contain newlines.
    :param fill: face colour.
    :param edge: edge colour.
    :param text_color: text colour.
    :param fs: declared font size in points.
    :param bold: use bold weight when True.
    :param linespacing: line spacing multiplier.
    :param rounding: corner radius in inches; pass h/2 (clamped to w/2) for
        oval flowchart terminators, keep the default for process boxes.
    :returns: None.
    """
    patch = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={rounding}",
        linewidth=1.2, edgecolor=edge, facecolor=fill, zorder=2,
    )
    ax.add_patch(patch)
    weight = "bold" if bold else "normal"
    ax.text(x0 + w / 2, y0 + h / 2, text, ha="center", va="center",
            fontsize=fs, color=text_color, fontweight=weight, zorder=3,
            linespacing=linespacing)


def arrow(ax: object, p0: tuple, p1: tuple, color: str = ARROW_COLOR,
          lw: float = 1.4, rad: float = 0.0) -> None:
    """Draw a straight arrow from p0 to p1.

    :param ax: the axes to draw on.
    :param p0: start point as (x, y) tuple in inches.
    :param p1: end point as (x, y) tuple in inches.
    :param color: arrow colour.
    :param lw: line width in points.
    :param rad: arc3 curvature radius.
    :returns: None.
    """
    patch = FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=11.0,
        linewidth=lw, color=color, connectionstyle=f"arc3,rad={rad}",
        zorder=4,
    )
    ax.add_patch(patch)


def routed_arrow(ax: object, points: list, color: str = ARROW_COLOR,
                 lw: float = 1.4) -> None:
    """Draw a multi-segment arrow through the given points.

    :param ax: the axes to draw on.
    :param points: list of (x, y) tuples in inches defining the path.
    :param color: arrow colour.
    :param lw: line width in points.
    :returns: None.
    """
    verts = list(points)
    codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 1)
    path = Path(verts, codes)
    patch = FancyArrowPatch(
        path=path, arrowstyle="-|>", mutation_scale=11.0,
        linewidth=lw, color=color, zorder=4,
    )
    ax.add_patch(patch)


def draw_legend_row(ax: object, items: tuple, y: float,
                    patch_w: float = 0.08, patch_h: float = 0.10,
                    gap: float = 0.10, fs: float = LEGEND_PT) -> None:
    """Draw one row of legend items centered on the canvas.

    :param ax: the axes to draw on.
    :param items: tuple of (label, fill, edge) tuples.
    :param y: bottom edge of the legend row in inches.
    :param patch_w: width of each colour patch in inches.
    :param patch_h: height of each colour patch in inches.
    :param gap: gap between items in inches (data units at design size).
    :param fs: font size in points.
    :returns: None.

    Label advances come from renderer-measured widths, not a per-character
    estimate. save_to_print_width shrinks the figure with set_size_inches
    while matplotlib text keeps its absolute point size, so a 0.55 em
    character estimate under-measured caps-heavy labels such as
    "Physics Solvers (SPARTA, OpenFOAM)" and the next colour patch landed
    on the previous label's tail (image audit of 2026-10-08).
    """
    fig = ax.figure
    renderer = (fig.canvas.get_renderer()
                if hasattr(fig.canvas, "get_renderer") else None)
    if renderer is None:
        # Murphy's Law: some backends expose no renderer until a draw.
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    advances = []
    for label, _, _ in items:
        probe = ax.text(-10.0, -10.0, label, fontsize=fs, alpha=0.0)
        width_in = probe.get_window_extent(renderer).width / fig.dpi
        probe.remove()
        # WHY divided by K_SHRINK: the saved canvas is squeezed to
        # PRINT_W_IN * K_SHRINK of design data inches while the glyphs keep
        # their absolute point size, so a label width_in wide on paper needs
        # width_in / K_SHRINK data units of room to clear its neighbour
        # after the squeeze. (Source: print_fit.save_to_print_width resizes
        # the figure with fig.set_size_inches, ratio loop.)
        advances.append(patch_w + 0.04 + width_in / K_SHRINK + gap)
    total_w = sum(advances) - gap
    if total_w > PRINT_W_IN:
        raise RuntimeError(
            "legend row is %.2f in of data, wider than the %.2f in canvas: %s"
            % (total_w, PRINT_W_IN, " | ".join(it[0] for it in items))
        )
    x = (PRINT_W_IN - total_w) / 2.0
    for (label, fill, edge), advance in zip(items, advances):
        ax.add_patch(Rectangle((x, y), patch_w, patch_h,
                               facecolor=fill, edgecolor=edge,
                               linewidth=0.8, zorder=2))
        ax.text(x + patch_w + 0.04, y + patch_h / 2, label,
                ha="left", va="center", fontsize=fs, color=INK, zorder=3)
        x += advance


def build() -> object:
    """Build the figure.

    :returns: the matplotlib figure, with the axes on it as its only axes.
    """
    fig = plt.figure(figsize=(PRINT_W_IN, H))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    ax.text(PRINT_W_IN / 2.0, TITLE_Y, TITLE_TEXT, ha="center", va="center",
            fontsize=TITLE_PT, fontweight="bold", color=INK)

    # WHY no bbox here, zorder 6, and add_mask_rects() after the fit pass:
    # a text bbox carries a pad that is a fraction of the FONT, so at the
    # fit squeeze (text keeps absolute points, boxes shrink) the padded
    # white box overpainted the borders of the CadQuery and SPARTA
    # boxes lying just beneath the header row (image audits 2026-10-08,
    # defects N1..N3). The replacement is an explicit white Rectangle in
    # DATA coordinates, computed by add_mask_rects() only after the save
    # loop has settled the figure at its final size, measured against the
    # real renderer extents and CLIPPED so it stops 2 px short of every
    # box border it approaches. zorder 6 keeps the glyphs above both the
    # mask (zorder 5) and the arrows (zorder 4) the mask interrupts;
    # zorder, not call order, is what makes the text paint last.
    for header, cx in zip(HEADERS, HEADER_CENTERS):
        ax.text(cx, HEADER_Y, header, ha="center", va="center",
                fontsize=HEADER_PT, fontweight="bold", color=HEADER_GRAY,
                zorder=6)

    # ISO 5807 data symbols: the three INPUT boxes carry data (geometry,
    # conditions, variables), so they are parallelograms, not terminators;
    # the single Start oval above the column owns the start-of-flow role.
    # The connector leaves the slanted right edge at box mid height, where
    # the edge sits at INPUT_X1 + slant/2 (see the arrow loop below).
    for y0, text in zip(INPUT_Y, INPUT_TEXTS):
        fsh.io_box(ax, INPUT_X0, y0, INPUT_X1 - INPUT_X0, INPUT_H,
                   text, INPUT_FILL, INPUT_EDGE)

    box(ax, ENGINE_X0, ENGINE_Y, ENGINE_X1 - ENGINE_X0, ENGINE_H,
        ENGINE_TEXT, ENGINE_FILL, ENGINE_EDGE, text_color="white", bold=True)

    # WHY: no separate VTK/STL label sits inside the SPARTA box. The box's
    # three centred lines already fill 0.59 of the 0.62 in height, so a fourth
    # label would collide with the top line (the failure that this redraw
    # fixed), and the OUTPUT box already carries the VTK/STL concept.
    box(ax, SOLVER_X0, SOLVER_Y[0], SOLVER_X1 - SOLVER_X0, SOLVER_H,
        SOLVER_TEXTS[0], SOLVER_FILL, SOLVER_EDGE, text_color="white",
        linespacing=1.1)
    box(ax, SOLVER_X0, SOLVER_Y[1], SOLVER_X1 - SOLVER_X0, SOLVER_H,
        SOLVER_TEXTS[1], SOLVER_FILL, SOLVER_EDGE, text_color="white")

    ml_cx = (ML_X0 + ML_X1) / 2
    for y0, text in zip(ML_Y, ML_TEXTS):
        box(ax, ML_X0, y0, ML_X1 - ML_X0, ML_H,
            text, ML_FILL, ML_EDGE, text_color="white")

    output_cx = (OUTPUT_X0 + OUTPUT_X1) / 2
    # ISO 5807 data symbol: the OUTPUT box is results (VTK/STL), so it is
    # a parallelogram like the inputs; x0 sits 0.05 in left so the slant
    # keeps the top edge inside the canvas (6.43 + 0.05 = 6.48 < 6.50).
    # The routed feed lands on the top edge and the Stop arrow leaves the
    # bottom edge, both at output_cx.
    fsh.io_box(ax, OUTPUT_X0, OUTPUT_Y, OUTPUT_X1 - OUTPUT_X0, OUTPUT_H,
               OUTPUT_TEXT, OUTPUT_FILL, OUTPUT_EDGE, text_color="white")

    # Start/Stop terminators: one Start above the INPUT column and one
    # Stop below the OUTPUT column close the flowchart. Start's arrow
    # lands on the first input's top edge (which spans x 0.07 to 1.41);
    # Stop's arrow leaves the output bottom edge at output_cx. The Start
    # oval bottom (3.26) stays 0.06 in above the title ink (top 3.20) at
    # design size; see the TITLE_Y note for the squeezed-size arithmetic.
    box(ax, 0.10, 3.26, 0.60, 0.30, "Start", "white", INK, rounding=0.15)
    # WHY computed, not literal (audit cycle 4): the target must follow the
    # first input's top edge after INPUT_Y[0] moved down, or the arrowhead
    # would sit 0.02 in inside the border instead of landing on it.
    arrow(ax, (0.40, 3.26), (0.40, INPUT_Y[0] + INPUT_H))
    box(ax, 5.765, 0.75, 0.55, 0.30, "Stop", "white", INK, rounding=0.15)
    arrow(ax, (output_cx, OUTPUT_Y), (output_cx, 1.05))

    engine_cx = (ENGINE_X0 + ENGINE_X1) / 2
    for y0 in INPUT_Y:
        yc = y0 + INPUT_H / 2.0
        # Start clear of the parallelogram's slanted right edge (at mid
        # height the edge sits at INPUT_X1 + 0.025), tip just inside the
        # engine box; the engine spans y 1.16 to 2.56 so every tip lands
        # on the box, none floats (axiom A4).
        arrow(ax, (INPUT_X1 + 0.04, yc), (ENGINE_X0 + 0.02, yc))

    sparta_yc = SOLVER_Y[0] + SOLVER_H / 2.0
    openfoam_yc = SOLVER_Y[1] + SOLVER_H / 2.0
    arrow(ax, (ENGINE_X1 - 0.02, sparta_yc - 0.1), (SOLVER_X0 + 0.02, sparta_yc))
    arrow(ax, (ENGINE_X1 - 0.02, openfoam_yc + 0.1), (SOLVER_X0 + 0.02, openfoam_yc))

    # WHY RULE_Y (2.94): the rule sits 0.049 in above the title ink bottom
    # (3.02 after the TITLE_Y move) at the fit ratio 0.82, and stays 0.20 in
    # above the solver boxes (top 2.74) and 0.22 in above the ML boxes
    # (top 2.72) as axiom A3 requires. Audit cycle 3 raised it 0.01 in over
    # the old 2.93 so the rule-to-header corridor reaches ~3 px on the
    # written PNG.
    routed_arrow(ax, [
        (engine_cx, ENGINE_Y + ENGINE_H),
        (engine_cx, RULE_Y),
        (output_cx, RULE_Y),
        (output_cx, OUTPUT_Y + OUTPUT_H),
    ])

    ml_yc = ML_Y[0] + ML_H / 2.0
    arrow(ax, (SOLVER_X1 - 0.02, sparta_yc), (ML_X0 + 0.02, ml_yc))

    routed_arrow(ax, [
        (ml_cx, ML_Y[0]),
        (ml_cx, 0.65),
        (engine_cx, 0.65),
        (engine_cx, ENGINE_Y),
    ], color=ORANGE)

    # WHY right-anchored at the solver box's left edge minus 0.04: the
    # engine-solver gap is only 0.12 in wide, so a centred label overran both
    # box texts (the reported 6.7x9.1 and 11.5x6.4 overlaps). Anchoring the
    # label's right end just left of the gap keeps it over background: the
    # 0.16 in lift puts the 9.5 pt label at y 2.59 to 2.72, above the grown
    # engine box (top 2.56) and below the header ink (bottom 2.75).
    ax.text(SOLVER_X0 - 0.04, sparta_yc + 0.16, ARROW_LABEL_VTK,
            ha="right", va="bottom", fontsize=LABEL_PT, fontstyle="italic",
            color=INK)
    # WHY no bbox, zorder 6 (same mechanism as the headers): the font-fraction
    # pad on the old white bbox bit into SPARTA's bottom border and corner
    # (image audit 2026-10-08, defect N4). add_mask_rects() supplies the
    # replacement mask, clipped against the solver boxes so it cannot touch
    # their edges; the arrow the label interrupts is the SPARTA->GA
    # diagonal crossing y406..423 inside this label's ink span.
    ax.text((SOLVER_X1 + ML_X0) / 2.0 + 0.02, (SOLVER_Y[1] + SOLVER_H + SOLVER_Y[0]) / 2.0,
            ARROW_LABEL_SURFACE, ha="center", va="center",
            fontsize=LABEL_PT, fontstyle="italic", color=INK,
            zorder=6)
    # WHY va=bottom at y 0.70 (was va=center at 0.75): the two-line label
    # centred at 0.75 straddled the orange horizontal at y 0.65 and the
    # second line "/ feedback loop" was struck through (image audit
    # 2026-10-08). Bottom-anchored, the block bottom is 0.05 data above the
    # line = 0.041 in at the fit ratio 0.82 (12 px), and the block top
    # clears the engine bottom (1.16) by 0.46 * 0.82 - 0.32 = 0.057 in.
    ax.text((ml_cx + engine_cx) / 2.0, 0.70, ARROW_LABEL_FEEDBACK,
            ha="center", va="bottom", fontsize=LABEL_PT, fontstyle="italic",
            color=ORANGE)

    draw_legend_row(ax, LEGEND_ROW1, LEGEND_Y1)
    # WHY gap 0.22: the measured advance left the orange patch touching the
    # tail of "OpenFOAM)" in the rendered PNG (image audit 2026-10-21); the
    # default 0.10 in is not enough clearance for this row.
    draw_legend_row(ax, LEGEND_ROW2, LEGEND_Y2, gap=0.22)
    draw_legend_row(ax, LEGEND_ROW3, LEGEND_Y3)

    return fig


def verify(fig: object, scale: float) -> None:
    """Check the written figure against the readability and collision floors.

    The check runs at the size the page will actually print, which is the
    fit scale times the chapter 03 \\textwidth squeeze described in A1.

    :param fig: the figure that was written, still open.
    :param scale: placement scale reported by the print fit.
    :returns: None.
    :raises RuntimeError: if the smallest printed text is under the floor, or
        two printed labels overlap by at least 3 pt in both directions
        (fm.text_overlaps_pt reports the offending pairs so the collision is
        diagnosable from the failure alone).
    """
    placed = scale * min(1.0, pf.TEXT_W_IN / PRINT_W_IN)
    printed, why = fm.smallest_text_pt(fig, placed)
    print("smallest printed text %.2f pt (%s); floor %.1f pt"
          % (printed, why, MIN_PRINTED_PT))
    if printed < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is under the %.1f pt floor from %s"
            % (printed, MIN_PRINTED_PT, why)
        )
    overlaps = fm.text_overlaps_pt(fig, placed)
    if overlaps:
        detail = "; ".join(
            "%.1fx%.1f pt %s <> %s" % (ox, oy, a, b)
            for a, b, ox, oy in overlaps[:8]
        )
        raise RuntimeError("printed labels overlap: %s" % detail)


def add_mask_rects(fig: object) -> int:
    """Interrupt arrows behind the header row and the surface-data label.

    PURPOSE
        The two routed-arrow verticals and the SPARTA->GA diagonal run
        straight through three text strings. Before this function existed
        the mask was a white bbox attached to each string, and because a
        bbox pad is a fraction of the font size, the fit squeeze (text
        keeps absolute points, every box shrinks with the canvas) grew the
        mask relative to the boxes until it painted white over the
        CadQuery, SPARTA and PINN border strokes (image audits 2026-10-08,
        defects N1..N4).

    PARAMETERS
        fig: the figure AFTER save_to_print_width has settled it at its
            final size, so renderer extents equal the geometry the audit
            measures. Adding the masks earlier computes them against the
            design canvas and they come out ~18% short after the squeeze.

    RETURNS
        The number of mask rectangles added (one per masked string).

    EXCEPTIONS
        RuntimeError is raised if the canvas exposes no renderer even
        after the draw-first fallback (Murphy's Law: some backends expose
        no renderer until a draw; if both paths fail the figure must not
        be shipped unmasked).

    AXIOMS
        A1. get_window_extent returns y-UP display coordinates: y0 is the
            BOTTOM edge, y1 is the TOP edge. Every clamp below is written
            in that convention; the first version of this function read
            them y-DOWN, which inverted the clamps, killed the INPUT and
            SOLVERS bands as degenerate, and dropped the CORE ENGINE mask
            across the ruled connector (caught on the probe run
            2026-10-08 before any audit).
        A2. A mask exists only where a line crosses ink. Rectangles are
            clipped 2 px short of any box border they approach and
            clamped below the ruled connector, so they can interrupt an
            arrow (which shares the text's band) but can never erase a
            border, a fill, or the rule.
        A3. Rectangles are placed in DATA coordinates from the settled
            canvas, so the second save's fit pass carries them with the
            artwork instead of stranding them in stale pixels.
    """
    ax = fig.axes[0]
    fig.canvas.draw()
    renderer = (fig.canvas.get_renderer()
                if hasattr(fig.canvas, "get_renderer") else None)
    if renderer is None:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        if renderer is None:
            raise RuntimeError("no renderer available for mask measurement")

    # Box borders that must never be painted: rounded process boxes
    # (FancyBboxPatch) and ISO 5807 data parallelograms (Polygon). Legend
    # swatches (Rectangle) sit far below every mask band and are skipped
    # on class, and FancyArrowPatch is deliberately absent because the
    # arrows are what the masks are FOR.
    clip_boxes = [p.get_window_extent(renderer) for p in ax.patches
                  if isinstance(p, (FancyBboxPatch, Polygon))]

    # The ruled connector is a routed arrow too, but its HORIZONTAL leg
    # must stay whole: every header mask is clamped 1 px below its stroke
    # (rule centre RULE_Y px, half-width 0.7 pt at the canvas dpi).
    rule_y_px = ax.transData.transform((0.0, RULE_Y))[1]
    rule_half_px = 0.7 * fig.dpi / 72.0

    px_per_data = abs(ax.transData.transform((1.0, 0.0))[0]
                      - ax.transData.transform((0.0, 0.0))[0])
    pad = 3.0
    gap_px = 2.0

    # WHY INPUT is excluded (audit cycle 4, check 10): no routed line ever
    # spans the INPUT column (the rule starts at engine_cx and the Start
    # arrow runs left of the glyph ink), so the INPUT mask crossed no
    # line and its only effect was erasing the right half of the Start
    # arrowhead at x129-140. A mask exists only where a line crosses ink
    # (axiom A2); with no crossing, there is nothing to mask.
    targets = [t for t in ax.texts
               if (t.get_text() in HEADERS and t.get_text() != "INPUT")
               or t.get_text() == ARROW_LABEL_SURFACE]
    inv = ax.transData.inverted()
    added = 0
    for text in targets:
        is_header = text.get_text() in HEADERS
        bb = text.get_window_extent(renderer)
        lo = bb.y0 - pad                      # y-UP: y0 is the bottom edge
        hi = bb.y1 + pad                      # y1 is the top edge
        left, right = bb.x0 - pad, bb.x1 + pad
        for b in clip_boxes:
            if b.x1 < left or b.x0 > right:
                continue                      # no horizontal overlap
            if b.y1 <= lo - gap_px:
                # Box lies wholly below the band: keep the mask above it.
                continue
            if b.y0 >= hi + gap_px:
                # Box lies wholly above the band: keep the mask below it.
                hi = min(hi, b.y0 - gap_px)
                continue
            # Box border intrudes into the band (or straddles it). Which
            # edge bounds the band depends on WHERE the box sits: a box
            # BELOW the text has its TOP edge (b.y1, y-UP display) under
            # the band, a box ABOVE has its BOTTOM edge (b.y0) over it.
            # The first version of this function swapped the two and
            # produced negative bands for SOLVERS, ML MODELS and surface
            # data (probe run 2026-10-08). A box containing the text
            # would kill the band, which is the honest failure (no such
            # box exists in this layout).
            box_mid = 0.5 * (b.y0 + b.y1)
            text_mid = 0.5 * (bb.y0 + bb.y1)
            if box_mid > text_mid:
                hi = min(hi, b.y0 - gap_px)   # box above: clip band top
            else:
                lo = max(lo, b.y1 + gap_px)   # box below: lift band base
        if is_header:
            # Butt the mask against the rule's stroke WITHOUT touching it.
            # Audit cycle 3: a 1.0 px standoff parked the mask top at PNG
            # row 195, four rows below the rule AA, so the leg stayed
            # visible inside the text band and overpainted ~9 px of the
            # first E of ENGINE. 0.25 px at dpi 100 lands the top ~1 px
            # under the AA: the leg is masked from the rule down to the
            # box while the rule keeps every pixel (PIL-verified).
            hi = min(hi, rule_y_px - rule_half_px - 0.25)
        if hi - lo < 2.0:
            print("mask skipped for %r (degenerate band %.1f px)"
                  % (text.get_text(), hi - lo))
            continue
        (dx_left, dy_lo) = inv.transform((left, lo))
        (dx_right, dy_hi) = inv.transform((right, hi))
        if dy_hi - dy_lo <= 0.0:
            raise RuntimeError(
                "mask for %r inverted in data space (%.4f..%.4f)"
                % (text.get_text(), dy_lo, dy_hi))
        ax.add_patch(Rectangle((dx_left, dy_lo),
                               dx_right - dx_left, dy_hi - dy_lo,
                               facecolor="white", edgecolor="none",
                               zorder=5))
        added += 1
        print("mask %-14r band %.1f..%.1f px (%.1f px)  data %.3f..%.3f"
              % (text.get_text(), lo, hi, hi - lo, dy_lo, dy_hi))
    print("mask rectangles added: %d" % added)
    if added == 0:
        raise RuntimeError("no mask rectangles were added; arrows would "
                           "still cross the header text")
    return added


def main() -> int:
    """Write the figure and verify it.

    :returns: 0 on success, 1 on rejection.
    """
    strings = [TITLE_TEXT] + list(HEADERS)
    strings.extend(INPUT_TEXTS)
    strings.append(ENGINE_TEXT)
    strings.extend(SOLVER_TEXTS)
    strings.extend(ML_TEXTS)
    strings.append(OUTPUT_TEXT)
    strings.extend([ARROW_LABEL_VTK, ARROW_LABEL_SURFACE,
                    ARROW_LABEL_REFINED, ARROW_LABEL_FEEDBACK])
    for item in LEGEND_ROW1 + LEGEND_ROW2 + LEGEND_ROW3:
        strings.append(item[0])
    strings.extend(["Start", "Stop"])
    pf.require_clean(*strings)

    fig = build()
    pf.assert_inside_canvas(fig)

    # Pass 1: run the fit loop so fig settles at the final squeezed size.
    # The masks must be measured against THAT geometry (text px are fixed,
    # box px shrink by ~0.848), so they are added only after this returns.
    tmp_path, scale = pf.save_to_print_width(
        fig, "software_pipeline_tmp.png", PRINT_W_IN * K_SHRINK, close=False)

    add_mask_rects(fig)

    # Pass 2: re-save with the masks in place. They live in data
    # coordinates inside existing text bands, so the tight-crop content
    # bbox is unchanged and the fit converges on the first attempt.
    tmp_path, scale = pf.save_to_print_width(
        fig, "software_pipeline_tmp.png", PRINT_W_IN * K_SHRINK, close=False)

    try:
        verify(fig, scale)
        final_path = FIGDIR / "software_pipeline.png"
        tmp_path.rename(final_path)
        print("wrote %s at print width %.4f in"
              % (final_path.name, PRINT_W_IN * K_SHRINK))
        return 0
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        print("software_pipeline FAILED: %s" % exc, file=sys.stderr)
        return 1
    finally:
        plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
