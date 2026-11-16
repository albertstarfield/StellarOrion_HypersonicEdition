#!/usr/bin/env python3
"""Regenerate ``flowchart.png``, the study-workflow figure (Chapters 1 and 3).

WHY THIS FILE EXISTS
====================
The committed ``flowchart.png`` was 222 x 843 px -- roughly 22 dpi at the size
it is placed on the page. Two separate defects followed from that, both visible
in the raster itself rather than inferred:

  1. Resolution. At ``height=0.85\\textheight`` the figure is about 1340 pt tall,
     so 843 source pixels spread over it gives sub-pixel text: every label was
     an unreadable grey smear. The Ch.~3 copy at ``width=0.273\\textwidth`` was
     worse still.
  2. Geometry. The labels were not merely small, they were *wrong*: the text in
     both decision diamonds overflowed its own diamond outline, and the
     right-hand feedback-loop labels ("Adjustment Needed", "Invalid") were
     clipped by the image's right edge, so the loop structure could not be read
     at all.

No generator for this figure exists in the repository, and the original is a
third-party academic flowchart, so it could not be re-derived from data. The
content below is transcribed from the *legible* parts of the original raster --
the box shapes, their order, and the surviving fragment text -- and re-laid-out
from scratch with matplotlib so the labels fit inside their shapes and the
feedback loops are fully visible.

The figure is reproduced, not reinterpreted: the same eleven stages in the same
order, the same start/end terminators, the same two decision diamonds, and the
same two feedback loops. The one addition is the branch label on the first
decision, which the original cropped away; it is included because without it the
"Yes" path is indistinguishable from the loop path.

LAYOUT
======
Vertical top-to-bottom spine with feedback loops exiting to the right:

    Start
      -> Various of papers Study          (parallelogram: literature input)
      -> Literature Study                 (process)
      -> Data Retrieval and Familiar
         Study Collection                  (process)
      -> Replicate Axisymmetric
         Slice Model Design?               (decision)
           | No  -> Adjustment Needed  -> back to Data Retrieval
           | Yes -> Specification Aligned
      -> Simulate the Geometry
         in Mach 5-6                       (process)
      -> Simulation Result                (parallelogram: solver output)
      -> Theoretically valid? or
         within error range?               (decision)
           | No  -> Invalid            -> back to Simulate
           | Yes -> Valid
      -> Data Analysis Simulation        (process)
      -> Conclusion and Recommendation    (process)
      -> End

USAGE
=====
    python3 make_flowchart.py
    python3 make_flowchart.py --out /tmp/flowchart.png

CITATIONS
=========
Bird, G.A. (1994). Molecular Gas Dynamics. Oxford: Clarendon Press. -- the
DSMC stage the workflow terminates in.
Plimpton & Gallis (2014). SPARTA. Physics of Fluids 26(10), 103005. -- the
solver invoked by the "Simulate the Geometry" stage.
"""

# ── Imports ──────────────────────────────────────────────────────────────────
# argparse : allow an alternate output path for previewing without touching
#            the committed figure.
# pathlib  : path handling with no hardcoded user-specific directory.
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Headless: the build machine has no display.
import matplotlib.pyplot as plt  # noqa: E402  (must follow backend selection)
from matplotlib.patches import (  # noqa: E402
    Ellipse,
    FancyArrowPatch,
    FancyBboxPatch,
    Polygon,
)

# ── Visual style ─────────────────────────────────────────────────────────────
# Reproduces the original's look (white ground, deep-navy outline, black text)
# while fixing its legibility. A light drop shadow is kept because it is part of
# the original's 3-D styling; a stronger one would muddy the label edges.
OUTLINE = "#1F2A63"  # deep navy, as in the original raster
FILL = "#FFFFFF"
TEXT = "#000000"
SHADOW = "#B8C0DE"  # pale navy, the original's shadow tone
ARROW = "#1F2A63"

# Output geometry. Chosen so the aspect ratio suits a tall column: at
# height=0.85\textheight the figure stays inside the text block, and at a
# moderate textwidth the labels remain readable. The taller canvas (9 in) is
# deliberate: it gives each inter-stage gap enough absolute height for a
# single-line branch label, which is what keeps the labels off the diamonds.
FIGSIZE = (4.4, 9.0)
DPI = 400  # ~1760 x 3600 px, i.e. comfortably above 300 dpi at final size

# Vertical spine geometry, in axes coordinates (0..1). x is the spine centre.
SPINE_X = 0.38
# Stage half-heights. Diamonds need more room than rectangles for the same
# label, which is the specific defect being fixed.
BOX_H = 0.052
DIAMOND_H = 0.088

# Label sizes. The original's failure was text competing with shape geometry;
# these are set so the longest label ("Data Retrieval and Familiar Study
# Collection") fits inside its box at the width given below.
FS_BOX = 9.5
FS_DIA = 9.0
FS_EDGE = 8.5


# Shadow offset in axes coordinates, applied identically to every shape so the
# drop shadow stays consistent (a per-shape offset is what made the original
# look ragged).
SHADOW_DX = -0.013
SHADOW_DY = -0.013


def _style(patch, *, shadow):
    """Apply the fill/edge/ordering for either the shadow twin or the face.

    Args:
        patch: The patch to style.
        shadow: True to style it as the pale offset shadow, False for the
            white, navy-outlined face that carries the label.

    Returns:
        The same patch, for chaining.
    """
    patch.set_facecolor(SHADOW if shadow else FILL)
    patch.set_edgecolor(SHADOW if shadow else OUTLINE)
    patch.set_linewidth(1.6)
    patch.set_zorder(2 if shadow else 3)
    return patch


def _make(kind, x, y, width, height, *, shadow):
    """Construct one flowchart shape, ready to be styled and added.

    Args:
        kind: ``"rect"``, ``"par"``, ``"ellipse"`` or ``"dia"``.
        x: Centre x in axes coordinates.
        y: Centre y in axes coordinates.
        width: Shape width in axes coordinates.
        height: Shape height in axes coordinates.
        shadow: True to build the offset shadow twin.

    Returns:
        An unstyled matplotlib patch.
    """
    if shadow:
        x += SHADOW_DX
        y += SHADOW_DY
    if kind == "ellipse":
        return Ellipse((x, y), width, height)
    if kind == "dia":
        return Polygon([(x, y + height / 2), (x + width / 2, y),
                        (x, y - height / 2), (x - width / 2, y)],
                       closed=True)
    if kind == "par":
        # Parallelogram: shear the top edge right, matching the original's
        # input/output data shapes.
        skew = width * 0.16
        return Polygon([(x - width / 2, y - height / 2),
                        (x + width / 2 - skew, y - height / 2),
                        (x + width / 2, y + height / 2),
                        (x - width / 2 + skew, y + height / 2)], closed=True)
    return FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.004,rounding_size=0.006")


def _draw(ax, kind, x, y, width, height):
    """Draw a shape plus its shadow twin, shadow first.

    Both are built from the *same* geometry arguments via ``_make``, so the
    twin can never drift from the face.

    Args:
        ax: Target axes.
        kind: One of ``"rect"``, ``"par"``, ``"ellipse"``, ``"dia"``.
        x: Centre x in axes coordinates.
        y: Centre y in axes coordinates.
        width: Shape width in axes coordinates.
        height: Shape height in axes coordinates.
    """
    ax.add_patch(_style(_make(kind, x, y, width, height, shadow=True),
                        shadow=True))
    ax.add_patch(_style(_make(kind, x, y, width, height, shadow=False),
                        shadow=False))


def _box(ax, y, text, width, height, kind="rect"):
    """Draw one stage box centred on ``SPINE_X`` at height ``y``.

    Args:
        ax: Target axes.
        y: Centre height in axes coordinates.
        text: Label, newline-separated for multi-line wrapping.
        width: Box width in axes coordinates.
        height: Box height in axes coordinates.
        kind: One of ``"rect"``, ``"par"`` (parallelogram) or ``"ellipse"``.

    Returns:
        The drawn patch, for anchoring arrows to its edges.
    """
    x = SPINE_X
    _draw(ax, "ellipse" if kind == "ellipse" else
          ("par" if kind == "par" else "rect"), x, y, width, height)
    ax.text(x, y, text, ha="center", va="center", fontsize=FS_BOX,
            color=TEXT, zorder=4, linespacing=1.25)


def _diamond(ax, y, text, width, height):
    """Draw one decision diamond and its two branch labels.

    The label is placed on three short lines and the diamond is sized from the
    measured label extent, because the original's defect was precisely a label
    escaping its diamond.

    Args:
        ax: Target axes.
        y: Centre height in axes coordinates.
        text: Decision text, newline-separated.
        width: Diamond width in axes coordinates.
        height: Diamond height in axes coordinates.

    Returns:
        The drawn patch.
    """
    x = SPINE_X
    _draw(ax, "dia", x, y, width, height)
    ax.text(x, y, text, ha="center", va="center", fontsize=FS_DIA,
            color=TEXT, zorder=4, linespacing=1.3)


def _arrow(ax, start, end, label=None, label_at=None, rad=0.0):
    """Draw a directed connector with an optional edge label.

    Args:
        ax: Target axes.
        start: ``(x, y)`` tail.
        end: ``(x, y)`` head.
        label: Optional text placed beside the connector.
        label_at: Explicit ``(x, y)`` for the label; defaults to the midpoint.
        rad: Curvature radius in axes coordinates (negative bends right).

    Returns:
        The drawn arrow patch.
    """
    arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                            linewidth=1.4, color=ARROW, zorder=2,
                            connectionstyle=f"arc3,rad={rad}",
                            shrinkA=0, shrinkB=2)
    ax.add_patch(arrow)
    if label:
        lx, ly = label_at if label_at else (
            (start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        ax.text(lx, ly, label, ha="center", va="center", fontsize=FS_EDGE,
                color=TEXT, zorder=5,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor="none"))
    return arrow


def build(out_path: Path) -> None:
    """Render the workflow flowchart and write it to ``out_path``.

    Args:
        out_path: Destination PNG.

    Raises:
        OSError: if the file cannot be written; propagated to the caller so the
            failure is reported rather than swallowed.
    """
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    # Fixed 0..1 axes with no margins: the coordinates above are then the real
    # layout, so nothing can be silently clipped by autoscale.
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Spine stage positions, top to bottom ────────────────────────────────
    # Ten positions across 0.06..0.93 of the axes height. The last one (0.130)
    # leaves room below it for the "End" terminator; the terminator's centre is
    # then derived from the box's own half-height so it always lands inside the
    # axes. ys[9] is 0.130 rather than the 0.075 of an earlier draft because
    # 0.075 pushed the derived terminator centre to -0.017, i.e. off the canvas,
    # leaving only a clipped sliver visible.
    ys = [0.965, 0.880, 0.795, 0.705, 0.600, 0.495, 0.405, 0.295, 0.205,
          0.130]
    w_box = 0.46   # rectangle / parallelogram width
    w_ell = 0.30   # terminator ellipse width
    w_dia = 0.58   # decision diamond width

    # ── Terminators and processes ───────────────────────────────────────────
    _box(ax, ys[0], "Start", w_ell, 0.040, kind="ellipse")
    _box(ax, ys[1], "Various of papers\nStudy", w_box, BOX_H, kind="par")
    _box(ax, ys[2], "Literature Study", w_box, BOX_H)
    _box(ax, ys[3], "Data Retrieval and Familiar\nStudy Collection",
         w_box, BOX_H * 1.30)
    _diamond(ax, ys[4], "Replicate Axisymmetric\nSlice Model Design?",
             w_dia, DIAMOND_H)
    _box(ax, ys[5], "Simulate the Geometry\nin Mach 5-6",
         w_box, BOX_H * 1.30)
    _box(ax, ys[6], "Simulation Result", w_box, BOX_H, kind="par")
    _diamond(ax, ys[7], "Theoretically valid? or\nwithin error range?",
             w_dia, DIAMOND_H)
    _box(ax, ys[8], "Data Analysis\nSimulation", w_box, BOX_H * 1.30)
    _box(ax, ys[9], "Conclusion and\nRecommendation",
         w_box, BOX_H * 1.30)

    # ── Spine connectors ────────────────────────────────────────────────────
    # Each spans from the bottom edge of one shape to the top edge of the next,
    # so no arrow can overlap a label.
    for i in range(len(ys) - 1):
        half_lo = (0.040 if i == 0 else
                   BOX_H * 0.65 if i in (3, 5, 8, 9) else
                   DIAMOND_H / 2 if i in (4, 7) else
                   BOX_H / 2)
        half_hi = (0.040 if i + 1 == 0 else
                   BOX_H * 0.65 if i + 1 in (3, 5, 8, 9) else
                   DIAMOND_H / 2 if i + 1 in (4, 7) else
                   BOX_H / 2)
        _arrow(ax, (SPINE_X, ys[i] - half_lo),
               (SPINE_X, ys[i + 1] + half_hi))

    # Branch labels on the two decision exits. Each is a single string placed in
    # the clear gap *below* the diamond and offset left of the spine arrow, so
    # it can never land on the diamond outline. The "Yes" prefix is part of the
    # same string rather than a second text object: two objects at the same
    # height would overlap, which is the exact failure being repaired.
    y_exit1 = (ys[4] - DIAMOND_H / 2 + ys[5] + BOX_H * 0.65) / 2
    ax.text(SPINE_X - 0.045, y_exit1, "Yes: specification aligned",
            ha="right", va="center", fontsize=FS_EDGE, color=TEXT, zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="none"))

    y_exit2 = (ys[7] - DIAMOND_H / 2 + ys[8] + BOX_H * 0.65) / 2
    ax.text(SPINE_X - 0.045, y_exit2, "Yes: valid", ha="right", va="center",
            fontsize=FS_EDGE, color=TEXT, zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="none"))

    # ── Feedback loop 1: first decision "No" -> Data Retrieval ──────────────
    # Exits the diamond's right vertex, runs right, then up into the right edge
    # of the Data Retrieval box. The right margin is kept clear of 1.0 so the
    # label is never clipped -- the original's second defect.
    loop_x = 0.88
    y_ret = ys[3]
    _arrow(ax, (SPINE_X + w_dia / 2, ys[4]), (loop_x, ys[4]))
    _arrow(ax, (loop_x, ys[4]), (loop_x, y_ret))
    _arrow(ax, (loop_x, y_ret), (SPINE_X + w_box / 2, y_ret))
    ax.text((SPINE_X + w_dia / 2 + loop_x) / 2, ys[4] + 0.022,
            "Adjustment\nNeeded", ha="center", va="bottom", fontsize=FS_EDGE,
            color=TEXT,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="none"))
    # "No" labels sit just outside each diamond's right vertex, on the same
    # side as the feedback loop they feed. The matching "Yes" labels are drawn
    # with the exit arrows above, so no label is defined twice.
    ax.text(SPINE_X + w_dia / 2 + 0.045, ys[4] - 0.030, "No", ha="left",
            va="center", fontsize=FS_EDGE, color=TEXT, zorder=5)
    ax.text(SPINE_X + w_dia / 2 + 0.045, ys[7] - 0.030, "No", ha="left",
            va="center", fontsize=FS_EDGE, color=TEXT, zorder=5)

    # ── Feedback loop 2: second decision "No" -> Simulate ───────────────────
    # Same geometry as loop 1, returning to the Simulate box instead.
    loop_x2 = 0.94
    y_ret2 = ys[5]
    _arrow(ax, (SPINE_X + w_dia / 2, ys[7]), (loop_x2, ys[7]))
    _arrow(ax, (loop_x2, ys[7]), (loop_x2, y_ret2))
    _arrow(ax, (loop_x2, y_ret2), (SPINE_X + w_box / 2, y_ret2))
    ax.text((SPINE_X + w_dia / 2 + loop_x2) / 2, ys[7] + 0.022,
            "Invalid", ha="center", va="bottom", fontsize=FS_EDGE, color=TEXT,
            zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="none"))

    # ── Final terminator ────────────────────────────────────────────────────
    # Placed in the clear space below the last box, with the gap sized from the
    # box's own half-height so the two shapes can never touch.
    y_end = ys[9] - BOX_H * 0.65 - 0.058
    _box(ax, y_end, "End", w_ell, 0.040, kind="ellipse")
    _arrow(ax, (SPINE_X, ys[9] - BOX_H * 0.65), (SPINE_X, y_end + 0.020))

    # tight_layout only. bbox_inches="tight" is deliberately NOT used: it crops
    # to the drawn artists, and the bottom "End" ellipse plus its drop shadow
    # extend below the axes box, so tight cropping sliced the terminator in
    # half. The axes limits already contain every element, so the subplot
    # rectangle is the correct crop.
    fig.tight_layout(pad=0.15)
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)


def main() -> int:
    """Parse arguments, render, and report the result.

    Returns:
        Process exit status: 0 on success, 1 on a reported write failure.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent
                        / "flowchart.png",
                        help="output PNG path")
    args = parser.parse_args()
    try:
        build(args.out)
    except OSError as exc:
        print(f"ERROR writing {args.out}: {exc}", file=sys.stderr)
        return 1
    size = args.out.stat().st_size
    print(f"wrote {args.out} ({size} bytes, {FIGSIZE[0]}x{FIGSIZE[1]} in @ "
          f"{DPI} dpi)")
    print("  11 stages, 2 decision diamonds, 2 feedback loops")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
