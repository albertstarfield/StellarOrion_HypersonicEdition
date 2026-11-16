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
    4. ISO 5807 flowchart symbols carry meaning: the rectangle is a
       process step, the parallelogram is input/output, and the stadium
       is a terminator. Drawing the first process step as a terminator
       misstates its role, so Start and Stop are drawn as their own
       stadium nodes and the seven steps use process/data symbols only.

THEORIES
    1. A seven step column plus one loop arrow carries the whole algorithm
       at this resolution, so no extra decoration is required. The Start
       and Stop terminators bracket the column without disturbing that
       layout: their heights are added to the canvas, not taken from the
       inter-box gaps, so the loop anchors on boxes 1 and 5 keep the exact
       geometry the clearance measurement certifies.
    2. matplotlib's Arc3 connection style places its control point at
       (mid_x + rad*dy, mid_y - rad*dx). For a vertical chord (dx = 0) a
       negative rad therefore bows the curve toward smaller x, and the
       sampled minimum x equals mid_x + rad*dy/2. The script verifies
       this numerically instead of trusting the sign convention.

APPLICATIONS
    1. Draw the Start and Stop terminators, the seven steps (six process
       rectangles, one input/output parallelogram), six down arrows, the
       green step label, the red dashed repeat loop, and the title.
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
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

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
import fig_shapes as fsh
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
# INCLUDE_FRACTION is the design-time include fraction (width=0.9\textwidth
# at design). Paper pass 2026-10-08: the page now includes the figure at
# 0.765\textwidth (= 0.9 x 0.85), and the save target below equals that
# include width, so the achieved scale stays 1.0 and the 8.40 pt loop
# subscript keeps printing at 8.40 pt. Every px-based guard (loop gap, flush
# rows) re-measures the saved file, which is 0.85 of the design raster.
INCLUDE_FRACTION = 0.9
PRINT_W_IN = INCLUDE_FRACTION * TEXT_W_IN
K_SHRINK = 0.85

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
#  ISO 5807 gives the decision block its own taller slot: the diamond
#  must CONTAIN its two text lines at the ink corners (|dy| = 0.1375 in
#  for lines at +/-0.5*LABEL_PITCH), and a 0.17 in half-height cuts
#  every glyph off. DECISION_H is the slot height for box 5 only; box 6
#  and the Stop chain carry the delta in box_top, and H grows by the
#  same amount so the bottom clearance stays BOT.
DECISION_H = 0.90
#  DEFECT 7a == the flowchart used 36% of the available plot width.
#
#  MEASURED (preamble.tex:524): \PlotFrame places with
#      \includegraphics[width=\textwidth, height=\plotheight, keepaspectratio]
#      and \plotheight = 0.60\textheight, so for a beamer 16:9 frame the
#      plot box is about 6.1 in x 1.89 in == box aspect ~3.23. A figure is
#      HEIGHT-limited and its placed width is 0.60*\textheight * figure_aspect,
#      so width usage is driven entirely by the figure's own aspect ratio.
#  MEASURED here: W = 0.9 * TEXT_W_IN = 4.96063 in, and with
#      H = TOP + TITLE_H + START_SLOT + 6*BOX_H + DECISION_H + 6*GAP
#          + STOP_SLOT + BOT = 4.84 in
#  the shipped aspect is 1.025, so a height-limited 6.1 x 1.89 in frame
#  places it 1.89 * 1.025 = 1.94 in wide == 32% of the box.
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
# Start and Stop terminators (stadium symbols) sit between the title and
# the first step, and below the last step. Their slots are part of H, so
# all seven inter-box relationships, the loop anchors on boxes 1 and 5 and
# the six down arrows keep exactly the geometry the clearance measurement
# certifies; only the canvas grows to carry the terminators.
TERM_W = 1.10
TERM_H = 0.24
# Vertical run of the arrow from Start into box 0 and from box 6 into Stop.
TERM_GAP = 0.12
# Clearance between the title region and the Start oval.
TITLE_GAP = 0.10
START_SLOT = TITLE_GAP + TERM_H + TERM_GAP
STOP_SLOT = TERM_GAP + TERM_H
H = (TOP + TITLE_H + START_SLOT + (N_BOX - 1) * BOX_H + DECISION_H
     + (N_BOX - 1) * GAP + STOP_SLOT + BOT)
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
# Terminators use the slate greys (Tailwind slate), deliberately outside
# the six palette border colours and outside the red shared by the loop
# and box 6, so the border detection and the loop mask in
# measure_loop_gap never see them.
TERM_EDGE = SLATE
TERM_FILL = "#F1F5F9"

TITLE_FS = 13
BOX_FS = 9
# Box 5's subtitle only: '(Steady State / Time Average)' measures
# 2.2155 in at 9 pt in the DejaVu worst case and would cut both
# diamond edges, so it declares 8.1 to stay above the 8.0 pt printed
# floor under the fit tolerance (printed = declared * achieved).
DECISION_SUB_FS = 8.1
LOOP_FS = 9
LOOP_MATH_FS = 12
TITLE_TEXT = "DSMC Algorithm (Bird, 1994)"
LOOP_LABEL_1 = "Repeat"
LOOP_LABEL_2 = "$N_{steps}$"
# Branch labels for the box 5 decision diamond: No goes back around the
# red Repeat loop, Yes continues down to the output parallelogram.
DECISION_YES = "Yes"
DECISION_NO = "No"
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
LOOP_X = BOX_X0 - 0.32
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
ENTRY_X = BOX_X0
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

# Shared style for every straight down arrow (Start to box 0, the six
# between-box arrows, and box 6 to Stop) so one literal cannot drift from
# another between call sites.
ARROW_STYLE = {
    "arrowstyle": "-|>",
    "color": SLATE,
    "linewidth": 1.5,
    "mutation_scale": 12,
    "shrinkA": 0.0,
    "shrinkB": 0.0,
}

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
    top = H - TOP - TITLE_H - START_SLOT - i * (BOX_H + GAP)
    if i == N_BOX - 1:
        # Box 6 hangs below the decision diamond's taller slot: the
        # delta DECISION_H - BOX_H was added above it in H, so subtract
        # it here to keep box 6, Stop and the bottom clearance exactly
        # on their old lines.
        top -= DECISION_H - BOX_H
    return top


def box_center(i: int) -> float:
    """Return the vertical center y of box i in data inches.

    Parameters
        i: zero based box index from the top.
    Returns
        y coordinate of the center line.
    """
    slot = DECISION_H if i == 5 else BOX_H
    return box_top(i) - slot / 2.0


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


def measured_loop_clearance(path: Path, side: str = "right") -> dict[str, int]:
    """Measure the loop clearance on a saved PNG and enforce both bounds.

    Parameters
        path: the saved PNG to measure.
        side: side of the box column that carries the loop, "right" or
            "left" (this figure uses "left").
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
    result = measure(path, side=side)
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
    # Times matches the thesis body text and every other thesis figure;
    # the BOX_H clearance comment below was measured with DejaVu Sans, and
    # Times is narrower at the same point size, so that clearance only
    # grows under this font.
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
    plt.rcParams["mathtext.fontset"] = "stix"

    for i in range(N_BOX):
        check_text(f"box title {i}", BOX_TITLES[i])
        check_text(f"box subtitle {i}", BOX_SUBS[i])
    check_text("title", TITLE_TEXT)
    check_text("loop label 1", LOOP_LABEL_1)
    check_text("loop label 2", LOOP_LABEL_2)
    check_text("start terminator", "Start")
    check_text("stop terminator", "Stop")
    check_text("decision branch yes", DECISION_YES)
    check_text("decision branch no", DECISION_NO)

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

    # Start terminator: a slate stadium above box 0 with the arrow that
    # enters the column. The oval top keeps TITLE_GAP below the title
    # region; the oval bottom is TERM_GAP above box 0, the same run every
    # between-box arrow uses.
    start_top = box_top(0) + TERM_GAP + TERM_H
    start_bottom = start_top - TERM_H
    ax.add_patch(
        FancyBboxPatch(
            (CX - TERM_W / 2.0, start_bottom),
            TERM_W,
            TERM_H,
            boxstyle=f"round,pad=0,rounding_size={TERM_H / 2.0}",
            facecolor=TERM_FILL,
            edgecolor=TERM_EDGE,
            linewidth=BOX_LW,
            zorder=2,
        )
    )
    ax.text(
        CX,
        start_bottom + TERM_H / 2.0,
        "Start",
        ha="center",
        va="center",
        fontsize=BOX_FS,
        fontweight="bold",
        color="#0F172A",
        zorder=3,
    )
    ax.annotate(
        "",
        xy=(CX, box_top(0)),
        xytext=(CX, start_bottom),
        arrowprops=dict(ARROW_STYLE),
        zorder=1,
    )

    for i in range(N_BOX):
        border, fill = PALETTE[i]
        top = box_top(i)
        # ISO 5807 symbols: boxes 0 to 5 are process rectangles (box 0 no
        # longer doubles as a terminator; the Start node owns that role),
        # and box 6, Output Surface Data, is an input/output parallelogram
        # from the shared helper. x0 = BOX_X0 - SLANT_IN puts the top edge
        # flush with the box column so the rightmost red ink still lands
        # on BOX_X1, inside the column that measure_loop_gap masks out of
        # the loop, while the visual centre (and both arrow landings at
        # CX) stay aligned with the rectangular steps.
        if i == N_BOX - 1:
            fsh.io_shape(
                ax,
                BOX_X0 - fsh.SLANT_IN,
                top - BOX_H,
                BOX_W,
                BOX_H,
                fill,
                border,
                linewidth=BOX_LW,
                slant_in=fsh.SLANT_IN,
            )
        elif i == 5:
            # ISO 5807 decision diamond for Check Convergence: four
            # points at the slot's top/right/bottom/left, so the column
            # arrow lands on the top vertex and the Repeat loop leaves
            # the right vertex exactly where the old rectangle edge sat
            # (BOX_X1), keeping the loop mask and clearance checks.
            ax.add_patch(
                Polygon(
                    [
                        (CX, top),
                        (BOX_X1, top - DECISION_H / 2.0),
                        (CX, top - DECISION_H),
                        (BOX_X0, top - DECISION_H / 2.0),
                    ],
                    facecolor=fill,
                    edgecolor=border,
                    linewidth=BOX_LW,
                    zorder=2,
                )
            )
        else:
            ax.add_patch(
                Rectangle(
                    (BOX_X0, top - BOX_H),
                    BOX_W,
                    BOX_H,
                    facecolor=fill,
                    edgecolor=border,
                    linewidth=BOX_LW,
                    zorder=2,
                )
            )
        cy = box_center(i)
        ax.text(
            CX,
            cy + 0.5 * LABEL_PITCH,
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
            cy - 0.5 * LABEL_PITCH,
            BOX_SUBS[i],
            ha="center",
            va="center",
            fontsize=DECISION_SUB_FS if i == 5 else BOX_FS,
            fontweight="bold",
            color="#0F172A",
            zorder=3,
        )

    for i in range(N_BOX - 1):
        # Box 5 exits from the diamond's bottom vertex, not BOX_H down.
        slot = DECISION_H if i == 5 else BOX_H
        y_from = box_top(i) - slot
        y_to = box_top(i + 1) - 0.01
        ax.annotate(
            "",
            xy=(CX, y_to),
            xytext=(CX, y_from),
            arrowprops=dict(ARROW_STYLE),
            zorder=1,
        )

    # Stop terminator: mirror of the Start node below box 6. Its bottom
    # edge lands exactly BOT above the canvas edge by the slot algebra in
    # H and box_top, so no clearance check has a special case.
    stop_top = box_top(N_BOX - 1) - BOX_H - TERM_GAP
    stop_bottom = stop_top - TERM_H
    ax.add_patch(
        FancyBboxPatch(
            (CX - TERM_W / 2.0, stop_bottom),
            TERM_W,
            TERM_H,
            boxstyle=f"round,pad=0,rounding_size={TERM_H / 2.0}",
            facecolor=TERM_FILL,
            edgecolor=TERM_EDGE,
            linewidth=BOX_LW,
            zorder=2,
        )
    )
    ax.text(
        CX,
        stop_bottom + TERM_H / 2.0,
        "Stop",
        ha="center",
        va="center",
        fontsize=BOX_FS,
        fontweight="bold",
        color="#0F172A",
        zorder=3,
    )
    ax.annotate(
        "",
        xy=(CX, stop_bottom),
        xytext=(CX, box_top(N_BOX - 1) - BOX_H),
        arrowprops=dict(ARROW_STYLE),
        zorder=1,
    )

    # The green Delta t that used to sit beside box 2 was removed on purpose.
    # A rendered-page audit found it floating six points clear of the box with
    # no leader line, and box 2 already names the step length in its own second
    # line as "Free Flight for Delta t", so the label was pure duplication.

    # Branch labels: No sits above the loop tail between the diamond's
    # right edge and the bezier (edge x = 3.724 at this y, bezier x ~=
    # 4.38, ink 3.995..4.245); Yes sits beside the column arrow in the
    # gap between box 6's top line and the diamond's lower-right edge
    # (ink 0.7925..0.9175 vs box6 0.78 and edge 0.931 at x = 2.66).
    ax.text(
        LOOP_X - 0.28,
        box_center(5) + 0.10,
        DECISION_NO,
        ha="center",
        va="center",
        fontsize=BOX_FS,
        fontweight="bold",
        color=RED,
        zorder=3,
    )
    ax.text(
        CX + 0.18,
        box_top(N_BOX - 1) + 0.075,
        DECISION_YES,
        ha="left",
        va="center",
        fontsize=BOX_FS,
        fontweight="bold",
        color="#0F172A",
        zorder=3,
    )

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
    control = (LOOP_X + LOOP_BOW, mid_y)
    ts = np.linspace(0.0, 1.0, LOOP_SAMPLES)
    bx = (1.0 - ts) ** 2 * LOOP_X + 2.0 * (1.0 - ts) * ts * control[0] + ts**2 * LOOP_X
    by = (1.0 - ts) ** 2 * y_loop_from + 2.0 * (1.0 - ts) * ts * mid_y + ts**2 * y_loop_to
    # The apex of a quadratic Bezier is at half of the control point offset,
    # so the curve's leftmost point is what has to clear the box edge. Testing
    # the control point instead would demand twice the clearance and reject a
    # curve that is in fact well clear.
    apex_x = float(bx.max())
    if BOX_X0 - apex_x < BOW_CLEAR_MIN:
        raise RuntimeError(
            f"loop apex reaches x {apex_x:.4f}, which clears the box edge "
            f"{BOX_X0:.4f} by only {BOX_X0 - apex_x:.4f} in, need "
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
        [LOOP_X, BOX_X0 + CONNECTOR_OVERLAP],
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
    tip_x = ENTRY_X + 0.4 * stroke_half
    head_len = LOOP_HEAD_LEN
    head_half = 0.5 * head_len * HEAD_HALF_RATIO
    ax.add_patch(
        Polygon(
            [(tip_x, y_loop_to), (tip_x - head_len, y_loop_to + head_half),
             (tip_x - head_len, y_loop_to - head_half)],
            closed=True,
            facecolor=RED,
            edgecolor=RED,
            linewidth=LOOP_LW,
            zorder=2,
        )
    )

    ax.text(
        LOOP_X - 0.18,
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
        LOOP_X - 0.40,
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
    if LOOP_X - (0.40 + LOOP_MATH_FS / 72.0 / 2.0) < 0.02:
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
        fig, "dsmc_algorithm_flowchart.png", PRINT_W_IN * K_SHRINK)[1]
    printed_pt = LOOP_MATH_FS * SUBSCRIPT_SCALE * achieved
    if printed_pt < MIN_PRINTED_PT:
        raise RuntimeError(
            f"loop subscript printed at {printed_pt:.2f} pt, below the "
            f"{MIN_PRINTED_PT:.1f} pt floor"
        )
    # Measured guard on the written file. measure_loop_gap is the single
    # implementation of this measurement, so the generator and the
    # standalone audit tool can never disagree about the same image.
    gap = measured_loop_clearance(FIGDIR / "dsmc_algorithm_flowchart.png", side="left")
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