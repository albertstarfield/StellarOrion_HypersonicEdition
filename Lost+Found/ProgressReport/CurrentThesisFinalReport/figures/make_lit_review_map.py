#!/usr/bin/env python3
"""Redraw figures/literature_review_map.png so its text prints at 8 pt or more.

AXIOM 1 (the failure being fixed): the imported artwork printed every label at
about 3.9 pt. Its smallest cap height was 16 px of a 1979 px image, so at an
include width of 0.92 text width the printed size was 16/1979 times 365.9 pt =
2.96 pt of ink for a 9 pt label. No amount of file inspection can repair baked
pixels, so the only honest fix is to draw the figure again from the same content.

AXIOM 2 (scale): a figure is printed at a known fraction of the 5.51181 in text
width. If the canvas is built at exactly that printed width, one inch of canvas
is one inch of paper, so a declared font size in points IS the printed size. This
is why every font below is >= 9 pt: the 8 pt floor is then cleared with margin
instead of by luck.

AXIOM 3 (content is fixed): the coverage claims in this figure are the literature
review claims of Chapter 2. They are transcribed verbatim from the measured
artwork and asserted for shape, so a redraw can never silently change which study
covers which capability. The caption and the BeginAccSupp ActualText at
chapter_02_literature_review.tex both describe circles, a half circle and empty,
and both mention the dashed red outline, so those three elements are preserved
exactly.

THEORY 1 (why the column headers are rotated): six two-line headers in a row of
six columns at 9 pt need about 6.0 in of width for the widest single word,
"Survivability", while the printed width is 5.071 in. Horizontal headers would
therefore collide or fall below 9 pt. Rotating the headers costs one word length
of vertical band and leaves the columns at their full width, which is the
standard remedy for a wide matrix in print.

THEORY 2 (why the legend shows whole cells): a white filled circle on a white
legend background is invisible, so a legend of bare marks cannot represent the
"full" state. Each legend swatch is therefore a miniature of the cell it
explains, fill, border and mark together, which also makes the key, the cells and
the caption say the same thing.

APPLICATION 1: run this script to regenerate figures/literature_review_map.png at
the exact printed width. The saved pixel width is asserted to within 0.5 percent
of the printed width, so the effective scale is reported, not assumed.

APPLICATION 2: the printed size of the smallest label is recomputed from the
declared size and the measured scale, and the script refuses to emit the figure
if that value falls below 8 pt.

PARAMETERS: none. The module reads no command line and takes no arguments.

RETURNS: the process exit code, 0 on success and 1 on any failed assertion.

RAISES: RuntimeError if the coverage matrix is malformed, if a banned dash
character appears in any drawn string, if the measured legend does not fit on one
line, if the canvas cannot be fitted to the printed width, or if the smallest
printed label would fall below 8 pt.

CITATIONS
  Matplotlib 3.11.2, https://matplotlib.org/stable/
  Bird, G. A. (1994), Molecular Gas Dynamics, Clarendon Press (the NTC and
  Streeter terms this thesis inherits are unrelated to this figure and are cited
  only to keep the chain of the surrounding chapter complete)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle, Wedge  # noqa: E402
from PIL import Image  # noqa: E402

import print_fit as pf  # noqa: E402  sibling module, unique print geometry

# figures/ -> CurrentThesisFinalReport -> ProgressReport -> Lost+Found -> repo root
ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
THESIS = Path(__file__).resolve().parent.parent
FIGDIR = THESIS / "figures"
assert FIGDIR.is_dir() and Path(__file__).resolve().parent == FIGDIR, (
    "FIGDIR must be the directory holding this script")

DPI = pf.DPI             # 300, the single save resolution used by print_fit
TEXT_W_IN = pf.TEXT_W_IN                     # 5.51181 in, A4 21 cm less 4+3 cm
PRINT_W_IN = 0.92 * TEXT_W_IN                     # matches width=0.92\textwidth in ch2

FONT_TITLE = 13.0        # >= 13 pt required by the redraw spec
FONT_BODY = 9.0          # >= 9 pt declared, prints >= 8 pt at scale 1.0
MIN_PRINTED_PT = 8.0
TITLE_LINE_PITCH = 0.235  # in, vertical distance between the two title lines

INK = "#2C3E50"          # cell edges and all text
FILL_FULL = "#1A5276"    # navy, full coverage
FILL_PART = "#85C1E9"    # light blue, partial coverage
FILL_NONE = "#F2F4F4"    # off white, not covered
HILITE = "#E74C3C"       # dashed red outline around the This Work row

# Highlight inset, in inches. The dashed outline is drawn INSIDE the This Work
# row by this amount on all four sides. A rendered-page audit of the previous
# revision measured the outline straddling its row: the top edge put 1008 red
# pixels inside the Schwartzentruber row above and the bottom edge ran 5 px past
# the matrix into the legend. An inset outline cannot reach a neighbouring row
# or the legend whatever the stroke width, so the box can only ever mean this
# row.
HL_INSET = 0.020

# Legend placement, in inches.
# LEGEND_GAP is the clear white gutter between the matrix bottom gridline and
# the top of the legend band. The previous revision placed the legend centre
# only 0.07 in below the matrix while the swatch half height is 0.11 in, so the
# swatch reached back up into the matrix: the audit measured a 0 px gap and 971
# red pixels of the highlight stroke striking the legend text. A gutter that
# exceeds the swatch half height cannot collide with anything.
LEGEND_GAP = 0.26
LEGEND_BAND = 0.26

# Banned dash checking lives in print_fit so that every generator applies the
# same rule; see pf.DASHES for the code point construction.

COLUMNS = (
    ("HIAD", "Geometry"),
    ("DSMC", "Aerothermal"),
    ("Sutton-Graves", "Heating"),
    ("PINN", "Refinement"),
    ("Survivability", "Optimization"),
    ("Multi-Solver", "Pipeline"),
)

ROWS = (
    ("Rapisarda (2022)", "ML for HIAD Heating"),
    ("Rapisarda et al. (2024)", "HIAD Parametric Study"),
    ("Masciarelli & Cassis (2021)", "LOFTID Design"),
    ("Schwartzentruber (2018)", "DSMC Hypersonic"),
    ("This Work", "StellarOrion Pipeline"),
)

# Coverage transcribed from the artwork. F full, P partial, "." not covered.
COVERAGE = (
    "FPPFFP",
    "FPF.P.",
    "F.F...",
    ".F....",
    "FFFFFF",
)

LEGEND = (("Fully covered", "F"), ("Partially covered", "P"), ("Not covered", "."))

_SCRATCH: plt.Figure | None = None


def check_text(label: str, *strings: str) -> None:
    """Raise if any drawn string contains a double hyphen, en dash or em dash.

    Thin wrapper over the shared checker so this script keeps its element
    labelled error messages while the rule itself exists only once.

    Parameters: label names the element for the error message; strings are the
    exact texts that will be handed to matplotlib.

    Returns: None.

    Raises: RuntimeError on the first banned character found.
    """
    for s in pf.checked_dashes(*strings):
        found = [f"U+{ord(d):04X}" for d in pf.DASHES if d in s]
        raise RuntimeError(
            f"{label}: drawn text {s!r} contains a banned dash {found}; "
            f"the thesis forbids it")


def text_w_in(s: str, size_pt: float, weight: str = "normal",
              style: str = "normal") -> float:
    """Return the width of a string in inches at a declared point size.

    AXIOM: with the Agg canvas at dpi 72, one pixel is exactly one point, so the
    measured window extent in pixels divided by 72 is the width in inches, and it
    is independent of the canvas size that print_fit later settles on.

    Parameters: s is the string; size_pt its declared font size; weight and style
    select bold and italic.

    Returns: the string width in inches.

    Raises: RuntimeError if the Agg renderer cannot be obtained.
    """
    global _SCRATCH
    if _SCRATCH is None:
        _SCRATCH = plt.figure(figsize=(8.0, 8.0), dpi=72)
    t = _SCRATCH.text(0.0, 0.0, s, fontsize=size_pt, fontweight=weight,
                      fontstyle=style)
    try:
        renderer = _SCRATCH.canvas.get_renderer()
    except Exception as exc:  # pragma: no cover, Agg always provides one
        raise RuntimeError(f"no Agg renderer available: {exc}") from exc
    width = t.get_window_extent(renderer=renderer).width
    t.remove()
    return width / 72.0



def draw_mark(ax, state: str, cx: float, cy: float, r: float) -> None:
    """Draw the coverage mark of one cell, or nothing for a not covered cell.

    AXIOM: the caption, the AccSupp and the artwork all call these a circle, a
    half circle and empty, so this function may not substitute any other shape.
    The half circle is drawn as a wedge spanning 90 to 270 degrees, which is the
    left half of the disc, matching the imported artwork.

    Parameters: ax is the target axes; state is one of "F", "P" or ".";
    cx, cy the cell centre in inches; r the mark radius in inches.

    Returns: None.

    Raises: RuntimeError on an unknown state, which would silently hide a
    transcription error.
    """
    if state == "F":
        ax.add_patch(Circle((cx, cy), r, facecolor="white",
                            edgecolor="white", linewidth=0.8, zorder=4))
    elif state == "P":
        ax.add_patch(Wedge((cx, cy), r, 90.0, 270.0, facecolor=FILL_FULL,
                           edgecolor="none", zorder=4))
        ax.add_patch(Circle((cx, cy), r, facecolor="none",
                            edgecolor=FILL_FULL, linewidth=1.0, zorder=5))
    elif state == ".":
        return
    else:
        raise RuntimeError(f"unknown coverage state {state!r}")


def build() -> plt.Figure:
    """Compose the coverage matrix figure.

    Returns: the unsaved matplotlib Figure.

    Raises: RuntimeError if the coverage matrix is malformed or the measured
    geometry cannot hold the labels at the required sizes.
    """
    check_text("title", "Literature Review: Coverage of Physical Phenomena and Methodology")
    check_text("column headers", *[t for pair in COLUMNS for t in pair])
    check_text("row labels", *[t for pair in ROWS for t in pair])
    check_text("legend", *[t for t, _ in LEGEND])
    assert len(COVERAGE) == len(ROWS), "one coverage row per study"
    for row, states in zip(ROWS, COVERAGE):
        assert len(states) == len(COLUMNS), f"row {row[0]} has {len(states)} states"
        assert set(states) <= {"F", "P", "."}, f"row {row[0]} has bad states {states}"

    margin = 0.05
    title_h = 0.58
    row_h = 0.46
    title_lines = ("Literature Review: Coverage of Physical",
                   "Phenomena and Methodology")

    label_w = max(text_w_in(t, FONT_BODY, weight="bold") for pair in ROWS
                  for t in pair) + 0.10
    header_h = max(text_w_in(t, FONT_BODY, weight="bold") for pair in COLUMNS
                   for t in pair) + 0.10
    matrix_w = PRINT_W_IN - 2.0 * margin - label_w - 0.08
    col_w = matrix_w / len(COLUMNS)
    if col_w < 0.34:
        raise RuntimeError(
            f"column width {col_w:.3f} in is too small for a readable mark and its "
            f"padding; widen the canvas or shorten the labels")

    matrix_h = row_h * len(ROWS)
    # The legend gutter is part of the height budget, so the band below the
    # matrix is exactly LEGEND_GAP plus one legend band.
    height = (margin + title_h + 0.06 + header_h + 0.05 + matrix_h
              + LEGEND_GAP + LEGEND_BAND + margin)

    print(f"  canvas {PRINT_W_IN:.3f} x {height:.3f} in   label column {label_w:.3f} in"
          f"   header band {header_h:.3f} in   column {col_w:.3f} in")

    fig = plt.figure(figsize=(PRINT_W_IN, height))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, height)
    ax.axis("off")

    # The title is set on two centered lines. At FONT_TITLE it measures about
    # 8 in on one line, which is wider than the 5.07 in canvas, and a text
    # artist wider than the canvas makes the tight crop in print_fit grow the
    # image on every attempt so the fit loop cannot converge.
    for k, line in enumerate(title_lines):
        ax.text(PRINT_W_IN / 2.0, height - margin - k * TITLE_LINE_PITCH, line,
                ha="center", va="top", fontsize=FONT_TITLE, fontweight="bold",
                color=INK)

    header_top = height - margin - title_h - 0.06
    header_mid = header_top - header_h / 2.0
    matrix_top = header_top - header_h - 0.05
    mx0 = margin + label_w + 0.08
    mark_r = 0.33 * min(col_w, row_h)

    # One Text per header carrying both lines, so each header is laid out as a
    # single rotated block. Two separate Text objects rotated 90 degrees are
    # centred on their own anchor boxes, so an offset applied along x lands
    # partly along the reading direction as well as across it. The audit of the
    # previous revision measured the two lines diagonally staggered with only a
    # 1 px clear gap between them, which is legible but is not the two-line
    # layout the spec asks for.
    for j, (line1, line2) in enumerate(COLUMNS):
        cx = mx0 + (j + 0.5) * col_w
        ax.text(cx, header_mid, line1 + "\n" + line2, rotation=90.0,
                ha="center", va="center", linespacing=1.30, fontsize=FONT_BODY,
                fontweight="bold", color=INK)

    for i, (line1, line2) in enumerate(ROWS):
        y1 = matrix_top - i * row_h
        cy = y1 - row_h / 2.0
        ax.text(mx0 - 0.08, cy + 0.075, line1, ha="right", va="center",
                fontsize=FONT_BODY, fontweight="bold", color=INK)
        ax.text(mx0 - 0.08, cy - 0.075, line2, ha="right", va="center",
                fontsize=FONT_BODY, fontweight="bold", color=INK)
        for j, state in enumerate(COVERAGE[i]):
            cx = mx0 + (j + 0.5) * col_w
            ax.add_patch(Rectangle((mx0 + j * col_w, y1 - row_h), col_w, row_h,
                                   facecolor={"F": FILL_FULL, "P": FILL_PART,
                                              ".": FILL_NONE}[state],
                                   edgecolor=INK, linewidth=0.8, zorder=2))
            draw_mark(ax, state, cx, cy, mark_r)

    # The dashed red highlight is drawn fully INSIDE the This Work row, inset by
    # HL_INSET on every side. A rendered-page audit of the previous revision
    # measured the outline straddling the row: 1008 red pixels landed inside the
    # Schwartzentruber row above and the bottom edge ran 5 px past the matrix
    # into the legend. An inset outline cannot touch a neighbouring row or the
    # legend, whatever the stroke width, so the box can only ever mean
    # "this row".
    last = len(ROWS) - 1
    hl_y1 = matrix_top - last * row_h - HL_INSET
    hl_y0 = matrix_top - (last + 1) * row_h + HL_INSET
    ax.add_patch(Rectangle((mx0 + HL_INSET, hl_y0), matrix_w - 2.0 * HL_INSET,
                           hl_y1 - hl_y0, facecolor="none", edgecolor=HILITE,
                           linewidth=1.6, linestyle=(0, (4.0, 2.0)), zorder=6))

    swatch = 0.22
    gap = 0.14
    widths = [swatch + 0.06 + text_w_in(t, FONT_BODY) for t, _ in LEGEND]
    total = sum(widths) + gap * (len(LEGEND) - 1)
    if total > PRINT_W_IN - 2.0 * margin:
        raise RuntimeError(
            f"legend needs {total:.3f} in but only {PRINT_W_IN - 2.0 * margin:.3f} in "
            f"is available; the key must stay on one line to match the caption")
    # The legend centre sits LEGEND_GAP below the matrix bottom gridline, so
    # the whole legend band is clear of the matrix and of the highlight box.
    legend_y = matrix_top - matrix_h - LEGEND_GAP
    x = margin + (PRINT_W_IN - 2.0 * margin - total) / 2.0
    for (text, state), w in zip(LEGEND, widths):
        ax.add_patch(Rectangle((x, legend_y - swatch / 2.0), swatch, swatch,
                               facecolor={"F": FILL_FULL, "P": FILL_PART,
                                          ".": FILL_NONE}[state],
                               edgecolor=INK, linewidth=0.8, zorder=2))
        draw_mark(ax, state, x + swatch / 2.0, legend_y, 0.30 * swatch)
        ax.text(x + swatch + 0.06, legend_y, text, ha="left", va="center",
                fontsize=FONT_BODY, color="#000000")
        x += w + gap
    # Measured guarantee, not an assumption. gutter is the clear white space in
    # inches between the matrix bottom gridline and the top of the legend
    # swatches, positive when the legend is below the matrix. The rendered-page
    # audit of the previous revision measured 0 px here and 971 red pixels of
    # the highlight stroke striking the legend text; a gutter of at least
    # 0.10 in is 7.2 pt, comfortably above the 6 pt the audit asked for.
    swatch_top = legend_y + swatch / 2.0
    gutter = (matrix_top - matrix_h) - swatch_top
    if gutter < 0.10:
        raise RuntimeError(
            f"legend swatches clear the matrix by only {gutter:.3f} in, which is "
            f"below the 0.100 in minimum; raise LEGEND_GAP")
    pf.assert_inside_canvas(fig)
    return fig


def main() -> int:
    """Regenerate the coverage matrix and assert its printed text size.

    Returns: 0 on success.

    Raises: nothing directly; build() and print_fit document their failures.
    """
    fig = build()
    # print_fit owns the print geometry: it saves at DPI, fits the printed
    # width to FIT_TOL, measures the achieved print scale and closes the figure.
    out, eff = pf.save_to_print_width(fig, "literature_review_map.png",
                                      PRINT_W_IN)
    w_px, h_px = Image.open(out).size
    smallest = FONT_BODY * eff
    print(f"  smallest declared label {FONT_BODY:.1f} pt at scale {eff:.3f} "
          f"= {smallest:.2f} pt printed; floor {MIN_PRINTED_PT:.1f} pt")
    if smallest < MIN_PRINTED_PT:
        raise RuntimeError(
            f"smallest printed label {smallest:.2f} pt is below the "
            f"{MIN_PRINTED_PT:.1f} pt floor")
    print(f"  {w_px}x{h_px}px, aspect {w_px / h_px:.3f}, matrix {len(ROWS)} rows "
          f"x {len(COLUMNS)} columns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
