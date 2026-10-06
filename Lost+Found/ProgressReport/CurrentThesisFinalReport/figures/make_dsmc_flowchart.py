"""Redraw of the Bird (1994) NTC DSMC algorithm flowchart at legible print size.

PURPOSE
    Regenerate `figures/dsmc_algorithm_flowchart.png` as a thesis-side
    matplotlib schematic. The imported original has baked text of about
    3.6 pt when printed (subscript `steps`), which fails the 8 pt floor.
    This script rebuilds the same seven step schematic at the printed
    width so every declared point size is also the printed point size.

PARAMETERS
    None. The script writes exactly one file and takes no input.

RETURN VALUE
    None. On success the PNG exists at the printed width within 0.5 percent.

EXCEPTIONS
    RuntimeError: raised when the saved width cannot be fitted to the
        print width, when a banned dash character reaches a drawn string,
        when the loop curve would cross a box, or when the smallest drawn
        text would print below 8 pt.

AXIOMS
    1. Printed size, not canvas size, governs legibility: a figure built at
       exactly the printed width has effective scale 1.0, so a declared
       9 pt font prints as 9 pt.
    2. Text is drawn in absolute points by the text engine, while the
       axes is rescaled during the width fit. Fonts therefore keep their
       point size across fit iterations, and only geometry scales.
    3. Mathtext subscripts print at roughly 0.7 of the parent point size,
       so a parent of 12 pt is needed for an 8.4 pt subscript.

THEORIES
    1. A seven step column plus one loop arrow carries the whole algorithm
       at this resolution, so no extra decoration is required.
    2. matplotlib's Arc3 connection style places its control point at
       (mid_x + rad*dy, mid_y - rad*dx). For a vertical chord (dx = 0) a
       negative rad therefore bows the curve toward smaller x, and the
       sampled minimum x equals mid_x + rad*dy/2. The script verifies
       this numerically instead of trusting the sign convention.

APPLICATIONS
    1. Draw the seven boxes, six down arrows, the green step label, the
       red dashed repeat loop, and the title.
    2. Fit the saved width to 0.9 of the text width, then assert the
       legibility floor and the dash-free rule.

CITATIONS
    - matplotlib 3.11.2, https://matplotlib.org/stable/
    - Bird, G. A. (1994), Molecular Gas Dynamics, Clarendon Press.
    - Tailwind CSS color palette, https://tailwindcss.com/docs/colors
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

# The rendered-ink measurement lives in its own module so that the
# generator's guard and the standalone audit tool are the same code. The
# clearance floor and the contact bound are imported from it rather than
# restated, because a second copy of a threshold is a second chance to
# disagree about the same image.
sys.path.insert(0, str(Path(__file__).resolve().parent))
# The print-fit loop, its tolerance, the achieved print scale and the
# inside-canvas check live in one sibling module so that no two
# generators can disagree about what a printed figure looks like.
import print_fit as pf
from measure_loop_gap import (
    MAX_TOUCH_ROWS,
    MIN_SEP_GAP_PX,
    measure,
)

DPI = pf.DPI             # 300, the save resolution
ROOT = Path(__file__).resolve().parent.parent
THESIS = ROOT
FIGDIR = THESIS / "figures"
assert FIGDIR.is_dir(), f"missing figure directory: {FIGDIR}"

# Text width from the main document geometry: A4 text width 210 mm minus
# 40 mm left and 30 mm right margin, converted to inches. print_fit
# owns that arithmetic, because a wrong text width silently scales
# every declared font size.
TEXT_W_IN = pf.TEXT_W_IN
INCLUDE_FRACTION = 0.9
PRINT_W_IN = INCLUDE_FRACTION * TEXT_W_IN

# Design canvas in inches. Data coordinates run 0..W by 0..H.
W = PRINT_W_IN
TOP = 0.10
TITLE_H = 0.30
BOT = 0.08
BOX_W = 3.20
# BOX H: the DEFECT 7a block below shrinks this figure so a beamer frame
# receives it at a usable aspect. The shrink went too far once it was
# measured rather than estimated: two 9 pt lines need more height than the
# 0.28 in it was given, and probe_box_text_fit.py measured the subtitle
# crossing the bottom border of all seven boxes by 1.81 pt. A 9 pt DejaVu
# line measures a half extent of 0.065 in, so two lines at LABEL_PITCH
# apart span 2*(LABEL_PITCH/2 + 0.065) = 0.26 in, and MIN_BOX_CLEAR_PT of
# 2 pt on each side adds 0.056 in. 0.34 in clears both conditions with a
# visible white channel, which is the same floor measure_loop_gap already
# uses for the loop.
BOX_H = 0.34
#  DEFECT 7a == the flowchart used 36% of the available plot width.
#
#  MEASURED (preamble.tex:524): \PlotFrame places with
#      \includegraphics[width=\textwidth, height=\plotheight, keepaspectratio]
#      and \plotheight = 0.60\textheight, so for a beamer 16:9 frame the
#      plot box is about 6.1 in x 1.89 in == box aspect ~3.23. A figure is
#      HEIGHT-limited and its placed width is 0.60*\textheight * figure_aspect,
#      so width usage is driven entirely by the figure's own aspect ratio.
#  MEASURED here: W = 0.9 * TEXT_W_IN = 4.96063 in, and with
#      H = TOP + TITLE_H + 7*BOX_H + 6*GAP + BOT = 4.24 in
#  the shipped aspect was 1.170 -> placed width ~1.49 in of ~6.1 in = 24%.
#
#  WHY A 2-COLUMN SNAKE WAS REJECTED (measured, not assumed):
#      LOOP_X = BOX_X1 + 0.32 is anchored to the box column's RIGHT edge.
#      In a 2-column layout BOX_X1 becomes the canvas edge, so the width
#      guard at the end of draw() == which requires
#      W - (LOOP_X + 0.40 + math_fs/2) >= 0.02 == fails by -0.75 in for
#      every column gap tried (0.25 / 0.35 / 0.45). The loop can only live
#      beside a column that is NOT the rightmost one. Separately,
#      measure_loop_gap() detects a single box_right_x, so with two boxes
#      side by side the post-save clearance gate would measure the wrong
#      border == i.e. the layout fix would require editing the measurement
#      utility that certifies the figure.
#
#  THE FIX APPLIED HERE: keep one column and the loop exactly where they are
#  (so both the inline bow guard and measured_loop_clearance keep testing
#  what they tested before), and cut the mandatory vertical stack == the
#  7 stacked boxes are the only thing making H large. Reducing BOX_H and
#  GAP leaves BOX_W, BOX_X0, BOX_X1, CX and therefore the whole loop
#  geometry byte-identical, and removes the two text-offset pairs' only
#  pressure by widening their separation to match the shorter box.
#  [Citation: matplotlib == figure height in inches vs data-unit extents]
#  [Reference: FAILURES_AND_FIXES.md == DEFECT 7]

GAP = 0.10
N_BOX = 7
# Vertical distance between the two label lines inside a box. Declared here
# rather than typed into the two draw calls so that BOX_H and the offsets
# cannot drift apart, which is exactly what happened when the offsets were
# literals and BOX_H changed underneath them. The lines are placed
# symmetrically at plus and minus half of this value about the box centre.
LABEL_PITCH = 0.15
H = TOP + TITLE_H + N_BOX * BOX_H + (N_BOX - 1) * GAP + BOT
BOX_X0 = (W - BOX_W) / 2.0
BOX_X1 = BOX_X0 + BOX_W
CX = W / 2.0

BOX_TITLES = [
    "Initialize Particles",
    "Move Particles Ballistically",
    "Index Particles into Cells",
    "Sample Collisions within Cells",
    "Accumulate Macroscopic Properties",
    "Check Convergence",
    "Output Surface Data",
]
BOX_SUBS = [
    "(Maxwell-Boltzmann Distribution)",
    "(Free Flight for $\\Delta t$)",
    "(Grid-Based Spatial Sorting)",
    "(NTC Method: Pair Selection)",
    "$\\rho$, T, u, p per Cell",
    "(Steady State / Time Average)",
    "(Heat Flux, Pressure, Shear)",
]
# Border, fill and text color per box, in reading order.
PALETTE = [
    ("#3B82F6", "#DBEAFE"),
    ("#22C55E", "#DCFCE7"),
    ("#F59E0B", "#FEF3C7"),
    ("#EC4899", "#FCE7F3"),
    ("#6366F1", "#E0E7FF"),
    ("#A855F7", "#F3E8FF"),
    ("#EF4444", "#FEE2E2"),
]
RED = "#EF4444"
SLATE = "#475569"

TITLE_FS = 13
BOX_FS = 9
LOOP_FS = 9
LOOP_MATH_FS = 12
TITLE_TEXT = "DSMC Algorithm (Bird, 1994)"
LOOP_LABEL_1 = "Repeat"
LOOP_LABEL_2 = "$N_{steps}$"
# Mathtext shrinks subscripts by this factor. It is read from matplotlib
# itself instead of being restated, because the legibility floor below is
# only as trustworthy as this number.
try:
    from matplotlib._mathtext import SHRINK_FACTOR as SUBSCRIPT_SCALE
except ImportError:  # pragma: no cover - private module moved
    SUBSCRIPT_SCALE = 0.7
MIN_PRINTED_PT = 8.0
# The fit tolerance is print_fit's, so the pre-save floor check below
# and the fit loop itself can never use different numbers.
FIT_TOL = pf.FIT_TOL
BOX_LW = 1.5
LOOP_LW = 1.4
# Loop geometry: a vertical chord to the right of the boxes bowing left, a
# horizontal tail that starts on the border of the box the loop leaves, and
# a short entry segment whose arrowhead lands on the box the loop reenters.
# The bow depth is calibrated against measured ink on the saved PNG, because
# the connection style is applied in display space and cannot be predicted
# from the data-space curvature. At this value the measured clearance sits
# above the eight pixel floor with margin.
LOOP_X = BOX_X1 + 0.32
# Bow depth, that is how far the curve's leftmost point sits left of the
# chord. A quadratic Bezier reaches exactly half of the control point
# offset, so the apex lands at LOOP_X - LOOP_BOW / 2 and the clearance to
# the box edge is (LOOP_X - BOX_X1) - LOOP_BOW / 2 = 0.32 - LOOP_BOW / 2.
# At 0.20 in that is 0.22 in of clearance, which measured 36 px of white
# space on the rendered PNG against the eight pixel floor.
LOOP_BOW = 0.20
# Smallest analytic clearance between the bow apex and the box edge, in
# inches. Zero point one five is about 0.4 mm, so the curve never runs
# close enough to the boxes to read as touching them.
BOW_CLEAR_MIN = 0.15
LOOP_SAMPLES = 241
# Arrowhead: length along the column and half width at the base.
LOOP_HEAD_LEN = 0.13
HEAD_HALF_RATIO = 0.62
ENTRY_X = BOX_X1
# Both connectors stop a hair INSIDE the border rather than exactly on it.
# WHY: the box border is a 1.5 pt stroke centred on BOX_X1, so a connector
# that ends at BOX_X1 leaves a sliver of white between its own ink and the
# border ink, which reads as a gap and is what the measured guard caught on
# the first run. Overlapping by 0.015 in (4.4 px at the rendered scale,
# under half a millimetre printed) closes that sliver, so the connectors
# meet the boxes the way a drawn connector is expected to, and it gives the
# contact metric in measure_loop_gap the two intended contact bands it needs
# to tell a real connection from a bow running along the border.
CONNECTOR_OVERLAP = 0.015

BANNED = (
    chr(45) + chr(45),
    chr(0x2013),
    chr(0x2014),
)


def box_top(i: int) -> float:
    """Return the top edge y of box i in data inches.

    Parameters
        i: zero based box index from the top.
    Returns
        y coordinate of the top edge.
    """
    return H - TOP - TITLE_H - i * (BOX_H + GAP)


def box_center(i: int) -> float:
    """Return the vertical center y of box i in data inches.

    Parameters
        i: zero based box index from the top.
    Returns
        y coordinate of the center line.
    """
    return box_top(i) - BOX_H / 2.0


def check_text(name: str, value: str) -> None:
    """Assert that a drawn string carries no banned dash character.

    Parameters
        name: label used in the error message.
        value: the string that will be drawn.
    Returns
        None.
    Exceptions
        RuntimeError: if value contains a double hyphen or an en or em
            dash.
    """
    for bad in BANNED:
        if bad in value:
            raise RuntimeError(f"banned dash {bad!r} in {name}")


def measured_loop_clearance(path: Path) -> dict[str, int]:
    """Measure the loop clearance on a saved PNG and enforce both bounds.

    Parameters
        path: the saved PNG to measure.
    Returns
        the measurement dictionary from measure_loop_gap.measure, whose
        keys are box_right_x, loop_left_x, gap_px, contact_rows and
        contact_run, all in pixels.
    Exceptions
        RuntimeError: if the measured white gap is below the eight pixel
            floor, which means the loop bow merges with the box border, or
            if the loop touches the border along more rows than two
            connectors can account for, which means it is running along
            the border instead of clearing it.
        SystemExit: propagated from the measurement when the image does not
            look like this flowchart at all.
    """
    result = measure(path)
    if result["sep_gap_px"] < MIN_SEP_GAP_PX:
        raise RuntimeError(
            f"loop median clearance from the box border is only "
            f"{result['sep_gap_px']} px, need {MIN_SEP_GAP_PX} px; reduce "
            f"the bow (LOOP_BOW is {LOOP_BOW})"
        )
    if result["touch_rows"] > MAX_TOUCH_ROWS:
        raise RuntimeError(
            f"loop runs flush against the box border on {result['touch_rows']} "
            f"rows, longest run {result['touch_run']} px, bound "
            f"{MAX_TOUCH_ROWS}; two connectors cannot account for that"
        )
    return result


def draw() -> None:
    """Build and save the DSMC flowchart figure.

    Returns
        None.
    Exceptions
        RuntimeError: propagates any check failure from check_text or
            save.
    """
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    for i in range(N_BOX):
        check_text(f"box title {i}", BOX_TITLES[i])
        check_text(f"box subtitle {i}", BOX_SUBS[i])
    check_text("title", TITLE_TEXT)
    check_text("loop label 1", LOOP_LABEL_1)
    check_text("loop label 2", LOOP_LABEL_2)

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0.0, W)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    ax.text(
        CX,
        H - TOP - TITLE_H / 2.0,
        TITLE_TEXT,
        ha="center",
        va="center",
        fontsize=TITLE_FS,
        fontweight="bold",
        color="#0F172A",
    )

    for i in range(N_BOX):
        border, fill = PALETTE[i]
        top = box_top(i)
        ax.add_patch(
            Rectangle(
                (BOX_X0, top - BOX_H),
                BOX_W,
                BOX_H,
                facecolor=fill,
                edgecolor=border,
                linewidth=1.5,
                zorder=2,
            )
        )
        ax.text(
            CX,
            top - BOX_H / 2.0 + 0.5 * LABEL_PITCH,
            BOX_TITLES[i],
            ha="center",
            va="center",
            fontsize=BOX_FS,
            fontweight="bold",
            color="#0F172A",
            zorder=3,
        )
        ax.text(
            CX,
            top - BOX_H / 2.0 - 0.5 * LABEL_PITCH,
            BOX_SUBS[i],
            ha="center",
            va="center",
            fontsize=BOX_FS,
            fontweight="bold",
            color="#0F172A",
            zorder=3,
        )

    for i in range(N_BOX - 1):
        y_from = box_top(i) - BOX_H
        y_to = box_top(i + 1) - 0.01
        ax.annotate(
            "",
            xy=(CX, y_to),
            xytext=(CX, y_from),
            arrowprops={
                "arrowstyle": "-|>",
                "color": SLATE,
                "linewidth": 1.5,
                "mutation_scale": 12,
                "shrinkA": 0.0,
                "shrinkB": 0.0,
            },
            zorder=1,
        )

    # The green Delta t that used to sit beside box 2 was removed on purpose.
    # A rendered-page audit found it floating six points clear of the box with
    # no leader line, and box 2 already names the step length in its own second
    # line as "Free Flight for Delta t", so the label was pure duplication.

    y_loop_from = box_center(5)
    y_loop_to = box_center(1)
    # The loop is drawn as explicit data coordinate geometry: a quadratic
    # Bezier sampled to a polyline, a straight dashed tail, and a polygon
    # arrowhead. WHY NOT AN ANNOTATED CURVE: matplotlib applies an arc3
    # connection style in DISPLAY space, and the rendered result was
    # measured to depart from the data coordinates in two separate ways.
    # The drawn bow was far deeper than the data space curvature (rad
    # -0.21 gave a drawn bow of about 0.31 in against an analytic 0.09 in),
    # and the arrow endpoint landed about ten pixels to the right of the
    # data position. Both were measured on the saved PNG, not assumed.
    # With the curve spelled out here the bow depth is a stated length, the
    # analytic clearance below is true of the drawn curve, and the pixel
    # guard in measure_loop_gap still confirms the rendered result.
    mid_y = 0.5 * (y_loop_from + y_loop_to)
    control = (LOOP_X - LOOP_BOW, mid_y)
    ts = np.linspace(0.0, 1.0, LOOP_SAMPLES)
    bx = (1.0 - ts) ** 2 * LOOP_X + 2.0 * (1.0 - ts) * ts * control[0] + ts**2 * LOOP_X
    by = (1.0 - ts) ** 2 * y_loop_from + 2.0 * (1.0 - ts) * ts * mid_y + ts**2 * y_loop_to
    # The apex of a quadratic Bezier is at half of the control point offset,
    # so the curve's leftmost point is what has to clear the box edge. Testing
    # the control point instead would demand twice the clearance and reject a
    # curve that is in fact well clear.
    apex_x = float(bx.min())
    if apex_x - BOX_X1 < BOW_CLEAR_MIN:
        raise RuntimeError(
            f"loop apex reaches x {apex_x:.4f}, which clears the box edge "
            f"{BOX_X1:.4f} by only {apex_x - BOX_X1:.4f} in, need "
            f"{BOW_CLEAR_MIN:.4f} in"
        )
    ax.plot(
        bx,
        by,
        color=RED,
        linewidth=LOOP_LW,
        linestyle=(0, (6, 2.5)),
        solid_capstyle="butt",
        zorder=1,
    )
    # The chord stands off the box column, so a horizontal tail carries
    # the dashed path from the border of the box the loop leaves out to
    # the chord. Without it the loop appears to start in empty space.
    ax.plot(
        [BOX_X1 - CONNECTOR_OVERLAP, LOOP_X],
        [y_loop_from, y_loop_from],
        color=RED,
        linewidth=LOOP_LW,
        linestyle=(0, (6, 2.5)),
        solid_capstyle="butt",
        zorder=1,
    )
    # Arrowhead as a data coordinate triangle whose tip lands on the border
    # of the box the loop reenters. The tip must sit INSIDE the border STROKE
    # so the connector meets the box with no white sliver, but it must NOT
    # reach the box FILL, or a dark triangle overprints the light interior.
    # The stroke spans BOX_LW/2 about the border centreline, so the window
    # that satisfies both conditions is that half width; 40 percent of it
    # lands 0.0042 in inside the centreline and 0.0062 in clear of the fill.
    # A rendered audit measured 0.015 in of tip inside the box before this
    # was measured, which is why the overlap is derived from the stroke
    # width rather than typed as a literal.
    stroke_half = 0.5 * BOX_LW / 72.0
    tip_x = ENTRY_X - 0.4 * stroke_half
    head_len = LOOP_HEAD_LEN
    head_half = 0.5 * head_len * HEAD_HALF_RATIO
    ax.add_patch(
        Polygon(
            [(tip_x, y_loop_to), (tip_x + head_len, y_loop_to + head_half),
             (tip_x + head_len, y_loop_to - head_half)],
            closed=True,
            facecolor=RED,
            edgecolor=RED,
            linewidth=LOOP_LW,
            zorder=2,
        )
    )

    ax.text(
        LOOP_X + 0.18,
        2.0,
        LOOP_LABEL_1,
        rotation=90,
        ha="center",
        va="center",
        fontsize=LOOP_FS,
        fontweight="bold",
        color=RED,
        zorder=3,
    )
    ax.text(
        LOOP_X + 0.40,
        2.0,
        LOOP_LABEL_2,
        rotation=90,
        ha="center",
        va="center",
        fontsize=LOOP_MATH_FS,
        color=RED,
        zorder=3,
    )
    if LOOP_MATH_FS * SUBSCRIPT_SCALE < MIN_PRINTED_PT:
        raise RuntimeError(
            f"loop subscript prints at {LOOP_MATH_FS * SUBSCRIPT_SCALE:.1f} pt"
        )
    if W - (LOOP_X + 0.40 + LOOP_MATH_FS / 72.0 / 2.0) < 0.02:
        raise RuntimeError("rotated loop labels overflow the canvas")

    # Pre-save floor check uses the worst magnification the fit can
    # produce, so nothing below 8 pt is ever written. The post-save check
    # repeats it with the magnification that was actually achieved.
    floor_pt = LOOP_MATH_FS * SUBSCRIPT_SCALE * (1.0 - FIT_TOL)
    if floor_pt < MIN_PRINTED_PT:
        raise RuntimeError(
            f"loop subscript would print at {floor_pt:.2f} pt at worst "
            f"case fit, below the {MIN_PRINTED_PT:.1f} pt floor"
        )
    print(
        f"loop subscript declared {LOOP_MATH_FS * SUBSCRIPT_SCALE:.2f} pt, "
        f"floor {floor_pt:.2f} pt"
    )
    # print_fit saves, fits, measures the achieved print scale and closes
    # the figure, so this script never repeats the loop.
    achieved = pf.save_to_print_width(
        fig, "dsmc_algorithm_flowchart.png", PRINT_W_IN)[1]
    printed_pt = LOOP_MATH_FS * SUBSCRIPT_SCALE * achieved
    if printed_pt < MIN_PRINTED_PT:
        raise RuntimeError(
            f"loop subscript printed at {printed_pt:.2f} pt, below the "
            f"{MIN_PRINTED_PT:.1f} pt floor"
        )
    # Measured guard on the written file. measure_loop_gap is the single
    # implementation of this measurement, so the generator and the
    # standalone audit tool can never disagree about the same image.
    gap = measured_loop_clearance(FIGDIR / "dsmc_algorithm_flowchart.png")
    print(
        f"loop measured on the saved PNG: median gap {gap['sep_gap_px']}px "
        f"floor {MIN_SEP_GAP_PX}px, flush rows {gap['touch_rows']} longest "
        f"run {gap['touch_run']} bound {MAX_TOUCH_ROWS}"
    )


if __name__ == "__main__":
    try:
        draw()
    except RuntimeError as exc:
        print(f"dsmc flowchart FAILED: {exc}", file=sys.stderr)
        raise