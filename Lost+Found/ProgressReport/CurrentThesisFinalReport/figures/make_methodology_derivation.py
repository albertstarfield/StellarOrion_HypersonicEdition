#!/usr/bin/env python3
"""Redraw figures/methodology_derivation.png as a legible thesis schematic.

PURPOSE
    Regenerate the methodology derivation chain diagram (chapter 3, included
    at 0.90\textwidth) so every printed label clears the 8 pt floor and no drawn
    string carries a banned dash. The imported original prints its smallest
    text at about 2.8 pt (the red data-flow labels), which fails the floor,
    so the whole schematic is rebuilt from the thesis sources at the print
    width with declared fonts of 9 pt or more (the 0.90 include fraction is
    the 2026-10-08 floor fix; see PRINT_TARGET_IN below).

PARAMETERS
    None. The script writes exactly one file, FIGDIR/methodology_derivation.png,
    and takes no input. A temporary file is written first and renamed only
    after every guard passes.

RETURNS
    Process exit code 0 on success, 1 on rejection.

EXCEPTIONS
    RuntimeError if a drawn string contains a banned dash, if an artist
    overhangs the canvas, if the smallest printed text falls below 8 pt, if
    two printed labels collide, or if the print width cannot be matched.

CITATIONS
    [Citation: Matplotlib 3.11.2 - https://matplotlib.org/stable/]
    [Citation: Pillow 12.3.0 - https://pillow.readthedocs.io/]
    [Reference: REDRAW_SPECS.md section 1 - verbatim text and layout]
    [Reference: chapter_03_methodology.tex line 15 - caption]
    [Reference: print_fit.py - save_to_print_width, assert_inside_canvas,
     require_clean]
    [Reference: fig_metrics.py - smallest_text_pt, text_overlaps_pt]

AXIOMS
    A1. Printed point size equals declared point size times the placement
        scale, so the scale is measured from the written file, never assumed.
        (Source: print_fit.save_to_print_width.)
    A2. A mathtext sub or superscript prints at SHRINK_FACTOR (0.7) of its
        parent, so this redraw uses plain Unicode text at 9 pt instead of
        mathtext: no script shrinks below the declared size, and a declared
        9 pt line prints at 9 x 0.8967 = 8.07 pt at the include scale the
        reader sees (see T1).
    A3. "IMPLEMENTATION" at 9 pt bold italic caps is about 1.19 in wide, so a
        dedicated left label column would force the four box columns below
        the width that "Stosszahlansatz" (0.90 in at 9 pt; the 10 pt attempt
        measured 1.331 in against a 1.200 in box and was rejected) and the
        other verbatim
        strings need. The layer labels are therefore drawn above each row,
        left aligned, which keeps them on the left side of the figure and
        gives the boxes the full text width.
    A4. A single unbreakable word wider than its box cannot be wrapped, so
        every logical line is pre-broken to fit and a width-table wrapper
        is the safety net that breaks anything still too wide.

THEORIES
    T1. The save scale is about 1.0 because the figure is built at the print
        width (5.532 in), but the READER's scale is the include width over
        the native width: 0.90 x 5.5118 / 5.532 = 0.8967. A declared font
        must therefore clear 8 / 0.8967 = 8.92 pt to satisfy the floor, so
        the 9.0 pt labels clear it at 8.07 pt with the 0.90 include. At the
        old 0.85 include the scale was 0.8478 and the true floor was 7.62 pt,
        a violation the design-scale check could not see.
    T2. Giving row 3 a wider column gap (0.28 in instead of 0.12 in) lets the
        red data-flow labels sit in the gaps without overlapping the box
        text, because a label centred on a gap extends into a box by half
        its width minus half the gap.
    T3. Centring row 3's narrower boxes in the same total width as the other
        rows keeps every column centre aligned, so the twelve vertical
        derivation arrows stay vertical.

APPLICATIONS
    A1. The rebuilt figure replaces the artwork in chapter 3 at
        0.90\textwidth (floor fix 2026-10-08); verify() is handed
        scale * INCLUDE_SCALE so its floor and collision checks run at the
        size the reader sees.
    A2. The same script pattern serves the remaining redraw queue.

DEVIATIONS FROM THE ORIGINAL ARTWORK
    1. Layer labels sit above each row rather than in a left column
       (AXIOM A3).
    2. Equations are set as plain Unicode text, not mathtext (AXIOM A2).
    3. Row 3 uses a wider column gap so the red labels clear the box text
       (THEORY T2).
    4. Row 3 columns 3-4 and row 4 columns 3-4 replace the retired MoP and
       Python-engine labels with the current pipeline terms (Gaussian
       Cost Function, Genetic Algorithm, Ada GA runner, Ada core
       driven by run.py), matching chapter_03_methodology.tex sections
       sec:axioms and sec:software_pipeline.
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, shared measurement
import print_fit as pf  # noqa: E402  sibling module, shared print geometry

FIGDIR = pf.FIGDIR
assert FIGDIR.is_dir(), "figures directory not found: %s" % FIGDIR

# The thesis text width in inches. REDRAW_SPECS.md section 1 fixed the
# conversion at 5.532 in = 398.3 pt for a figure included at textwidth.
PRINT_W_IN = 5.532
# Floor fix 2026-10-08. chapter_03 used to include this figure at
# 0.85\textwidth, which against the 5.532 in design canvas prints every
# label at 4.685/5.532 = 0.8478 of its declared size, so the 9.0 pt labels
# really printed at 7.62 pt - below the 8 pt rule, invisible to a check that
# only measures the design print width. Three fixes were evaluated:
# (1) shrink the save target to the include width - impossible, print_fit
# fits with a tight crop and the tight crop cannot go below the longest
# fixed-point text run, measured at 4.787 in; (2) raise TEXT_PT to 10 -
# rejected by assert_boxes_fit, "(Stosszahlansatz)" measured 1.331 in
# against a 1.200 in box inner width; (3) widen the include fraction to
# 0.90, which gives a reader scale of 0.90 x 5.5118 / 5.532 = 0.8967 and a
# true floor of 9.0 x 0.8967 = 8.07 pt. Fix (3) is applied. PRINT_TARGET_IN
# stays at the design width, and main() hands verify() the reader's include
# scale so every guard judges the size the reader actually sees.
PRINT_TARGET_IN = PRINT_W_IN

# Declared font sizes. Every drawn string is 9 pt or more (AXIOM A2), the
# title is 13 pt, so the smallest printed text is 9 x 0.8967 = 8.07 pt at
# the include scale (AXIOM A1 / THEORY T1).
TITLE_PT = 13.0
TEXT_PT = 9.0
MIN_PRINTED_PT = 8.0
# The reader's placement scale: include width (0.90 x text width) over the
# native width of the saved file (PRINT_TARGET_IN).
INCLUDE_SCALE = 0.90 * pf.TEXT_W_IN / PRINT_TARGET_IN

# Colours from REDRAW_SPECS.md section 1.
INK = "#212121"
LAYER = "#757575"
ROW_COLORS = ("#37A0F4", "#FFA219", "#5EB761", "#A63CB7")
BOX_TEXT = "#FFFFFF"
ARROW = "#607D8B"
RED = "#F44336"
LEGEND_PATCH = ("#2196F3", "#FF9800", "#4CAF50", "#9C27B0")

# Horizontal geometry (inches). Four equal columns for rows 1, 2 and 4; row 3
# uses a wider gap so the red data-flow labels clear the box text (THEORY T2).
PITCH = 1.38          # column pitch: box width + gap
BOX_W = 1.26          # box width for rows 1, 2, 4
GAP = PITCH - BOX_W   # 0.12 in column gap for rows 1, 2, 4
ROW3_GAP = 0.28       # wider gap for row 3
ROW3_BOX_W = PITCH - ROW3_GAP  # 1.16 in box width for row 3
ROW3_OFFSET = 0.5 * (BOX_W - ROW3_BOX_W)  # centres row 3, aligns centres
BOX_AREA_LEFT = 0.5 * (PRINT_W_IN - (4 * BOX_W + 3 * GAP))  # 0.066 in
BOX_AREA_RIGHT = BOX_AREA_LEFT + (4 * BOX_W + 3 * GAP)      # 5.466 in
COL_CENTERS = [BOX_AREA_LEFT + c * PITCH + 0.5 * BOX_W for c in range(4)]

# Vertical geometry (inches).
LINE_PITCH = 0.15     # line pitch inside a box
PAD_Y = 0.05          # top/bottom padding inside a box
LABEL_PITCH = 0.12    # line pitch of a two-line layer label
LABEL_GAP = 0.08      # gap between a layer label and its row of boxes
ROW_GAP = 0.18        # vertical gap between rows (holds the arrows)
TITLE_H = 0.50        # space reserved at the top for the title
BOTTOM_MARGIN = 0.08

# DejaVu Sans advance widths in em units, rounded up so the wrap test is
# conservative. Covers every character the figure draws, including the
# Greek and mathematical Unicode used in the equation boxes.
_EM = {
    " ": 0.35, "!": 0.35, '"': 0.42, "#": 0.75, "$": 0.62, "%": 0.95,
    "&": 0.75, "'": 0.25, "(": 0.35, ")": 0.35, "*": 0.55, "+": 0.75,
    ",": 0.35, "-": 0.35, ".": 0.35, "/": 0.35, ":": 0.35, ";": 0.35,
    "<": 0.75, "=": 0.75, ">": 0.75, "?": 0.55, "@": 0.95, "[": 0.35,
    "\\": 0.35, "]": 0.35, "^": 0.55, "_": 0.55, "`": 0.35, "{": 0.55,
    "|": 0.35, "}": 0.55, "~": 0.75,
    "a": 0.62, "b": 0.62, "c": 0.55, "d": 0.62, "e": 0.62, "f": 0.42,
    "g": 0.62, "h": 0.62, "i": 0.35, "j": 0.35, "k": 0.55, "l": 0.35,
    "m": 0.95, "n": 0.62, "o": 0.62, "p": 0.62, "q": 0.62, "r": 0.42,
    "s": 0.55, "t": 0.42, "u": 0.62, "v": 0.62, "w": 0.85, "x": 0.62,
    "y": 0.62, "z": 0.55,
    "A": 0.72, "B": 0.72, "C": 0.72, "D": 0.72, "E": 0.62, "F": 0.62,
    "G": 0.75, "H": 0.75, "I": 0.35, "J": 0.55, "K": 0.68, "L": 0.55,
    "M": 0.95, "N": 0.75, "O": 0.78, "P": 0.68, "Q": 0.78, "R": 0.72,
    "S": 0.68, "T": 0.68, "U": 0.72, "V": 0.72, "W": 1.00, "X": 0.72,
    "Y": 0.68, "Z": 0.68,
    "0": 0.62, "1": 0.62, "2": 0.62, "3": 0.62, "4": 0.62, "5": 0.62,
    "6": 0.62, "7": 0.62, "8": 0.62, "9": 0.62,
    "ρ": 0.62, "τ": 0.62, "∇": 0.95, "∞": 0.75, "·": 0.35, "³": 0.55,
    "ₙ": 0.62, "√": 0.75, "Δ": 0.75, "λ": 0.62, "β": 0.62,
}

# Safety factor on the width estimate. The table is already rounded up; this
# adds a further margin so a wrapped line is guaranteed to fit its box.
WIDTH_SAFETY = 1.06

TITLE = "Methodology Derivation from First Principles"

# The four rows. Each box holds a list of logical lines taken verbatim from
# REDRAW_SPECS.md section 1, pre-broken so that no logical line is wider
# than its box (AXIOM A4). The wrapper below is the safety net.
ROWS = (
    {
        "label": ("LAYER 1 /", "AXIOMS"),
        "color": ROW_COLORS[0],
        "boxes": (
            ("A1: Conservation", "(Mass,", "Momentum,", "Energy)"),
            ("A2: Molecular", "Chaos", "(Stosszahlansatz)"),
            ("A3: Continuum", "Hypothesis", "(valid for", "Kn<0.01)"),
            ("A4: Equilibrium", "Distribution", "(MB", "statistics)"),
        ),
    },
    {
        "label": ("LAYER 2 /", "EQUATIONS"),
        "color": ROW_COLORS[1],
        "boxes": (
            ("Boltzmann Eq.", "d f/dt + v·∇f", "= Q(f,f)"),
            ("Navier-Stokes", "ρ(du/dt + u·∇u)", "= -∇p + div τ"),
            ("Sutton-Graves", "q = k sqrt(ρ∞/Rₙ)", "V∞³"),
            ("Conservation", "Laws (Mass,", "Momentum,", "Energy)"),
        ),
    },
    {
        "label": ("LAYER 3 /", "METHODS"),
        "color": ROW_COLORS[2],
        "cols": (0, 2, 3),
        "boxes": (
            ("DSMC (Bird", "Algorithm)", "SPARTA"),
            ("Cost", "Function", "Evaluation"),
            ("Genetic", "Algorithm", "(selection,", "crossover,", "mutation)"),
        ),
    },
    {
        "label": ("LAYER 4 /", "IMPLEMENTATION"),
        "color": ROW_COLORS[3],
        "cols": (0, 2, 3),
        "boxes": (
            ("SPARTA Docker", "Container", "5-species air"),
            ("Ada/SPARK", "GA runner", "Ravenscar pool"),
            ("StellarOrion", "Ada core", "run.py", "orchestrator"),
        ),
    },
)

# Red data-flow arrows in row 3: (source column, target column, label).
RED_ARROWS = ((0, 2, "data"), (2, 3, "$J$"))
# WHY "$J$": the gap between the cost box and the GA box is too narrow
# for the word "eval"; the glyph clipped on the GA border (image audit
# 2026-10-21). The scalar passed along the arrow is the cost J.

# Bottom legend: (label, patch colour).
LEGEND = (
    ("Axioms (First Principles)", LEGEND_PATCH[0]),
    ("Governing Equations", LEGEND_PATCH[1]),
    ("Numerical Methods", LEGEND_PATCH[2]),
    ("Software Implementation", LEGEND_PATCH[3]),
)

TMP_NAME = "methodology_derivation_tmp.png"
FINAL_NAME = "methodology_derivation.png"


def text_width_in(text: str, fontsize_pt: float) -> float:
    """Return the conservative printed width of a string in inches.

    :param text: the string to measure.
    :param fontsize_pt: declared font size in points.
    :returns: width in inches, using the DejaVu Sans em table times
        WIDTH_SAFETY.
    """
    em = sum(_EM.get(ch, 0.62) for ch in text)
    return em * fontsize_pt / 72.0 * WIDTH_SAFETY


def wrap_line(text: str, fontsize_pt: float, max_width_in: float) -> list:
    """Wrap one logical line to fit max_width_in, breaking on spaces.

    A single word wider than max_width_in cannot be broken and is returned on
    its own line; the caller's pre-save width assertion is the guard that
    rejects such a word (AXIOM A4).

    :param text: the logical line to wrap.
    :param fontsize_pt: declared font size in points.
    :param max_width_in: widest allowed line in inches.
    :returns: the list of wrapped lines.
    """
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if not current or text_width_in(trial, fontsize_pt) <= max_width_in:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def wrap_box(lines: tuple, fontsize_pt: float, max_width_in: float) -> list:
    """Wrap every logical line of a box and flatten the result.

    :param lines: the logical lines of the box.
    :param fontsize_pt: declared font size in points.
    :param max_width_in: widest allowed line in inches.
    :returns: the flattened list of wrapped lines.
    """
    out: list[str] = []
    for line in lines:
        out.extend(wrap_line(line, fontsize_pt, max_width_in))
    return out


def compute_layout() -> dict:
    """Compute the wrapped line counts, box heights and figure height.

    :returns: a dictionary with the per-row wrapped boxes, the box height of
        each row, and the total figure height in inches.
    """
    inner_w = BOX_W - 2.0 * 0.03
    inner_w3 = ROW3_BOX_W - 2.0 * 0.03
    wrapped_rows = []
    box_heights = []
    for r, row in enumerate(ROWS):
        width = inner_w3 if r == 2 else inner_w
        wrapped = [wrap_box(box, TEXT_PT, width) for box in row["boxes"]]
        wrapped_rows.append(wrapped)
        n_lines = max(len(b) for b in wrapped)
        box_heights.append(n_lines * LINE_PITCH + 2.0 * PAD_Y)
    label_block = 2.0 * LABEL_PITCH + LABEL_GAP
    legend_h = 0.40
    content = sum(label_block + bh + ROW_GAP for bh in box_heights)
    height = TITLE_H + content + 0.12 + legend_h + BOTTOM_MARGIN
    return {
        "wrapped": wrapped_rows,
        "box_heights": box_heights,
        "height": height,
        "label_block": label_block,
        "legend_h": legend_h,
    }


def row_box_left(row_index: int, col_index: int) -> float:
    """Return the left edge of one box in inches.

    :param row_index: zero based row index.
    :param col_index: zero based column index.
    :returns: the x coordinate of the box left edge.
    """
    if row_index == 2:
        return BOX_AREA_LEFT + ROW3_OFFSET + col_index * PITCH
    return BOX_AREA_LEFT + col_index * PITCH


def row_box_width(row_index: int) -> float:
    """Return the box width of one row in inches.

    :param row_index: zero based row index.
    :returns: the box width in inches.
    """
    return ROW3_BOX_W if row_index == 2 else BOX_W


def assert_boxes_fit() -> None:
    """Reject any wrapped box line that is wider than its box.

    The wrapper breaks on spaces, so a single unbreakable word can still be
    wider than its box. This is the guard AXIOM A4 promises: it names the
    offending line and its box before anything is written.

    :returns: None.
    :raises RuntimeError: if any wrapped line exceeds its box inner width.
    """
    inner_w = BOX_W - 2.0 * 0.03
    inner_w3 = ROW3_BOX_W - 2.0 * 0.03
    layout = compute_layout()
    for r, row in enumerate(ROWS):
        width = inner_w3 if r == 2 else inner_w
        for c, box in enumerate(layout["wrapped"][r]):
            for line in box:
                if text_width_in(line, TEXT_PT) > width + 0.005:
                    raise RuntimeError(
                        "line %r in row %d box %d is %.3f in wide, "
                        "box inner width is %.3f in"
                        % (line, r + 1, c + 1,
                           text_width_in(line, TEXT_PT), width))


def draw() -> plt.Figure:
    """Build the figure.

    :returns: the matplotlib figure with the axes on it as its only axes.
    """
    layout = compute_layout()
    height = layout["height"]
    fig = plt.figure(figsize=(PRINT_W_IN, height))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, height)
    ax.axis("off")

    ax.text(PRINT_W_IN / 2.0, height - 0.24, TITLE, ha="center", va="center",
            fontsize=TITLE_PT, fontweight="bold", color=INK)

    # Vertical cursor: the top of the current row's layer label.
    y = height - TITLE_H
    row_centers = []
    for r, row in enumerate(ROWS):
        label_top = y
        # White backing so the derivation arrows crossing the label band
        # cannot strike through the words (image audit 2026-10-21).
        ax.text(BOX_AREA_LEFT, label_top - LABEL_PITCH, row["label"][0],
                ha="left", va="center", fontsize=TEXT_PT, fontweight="bold",
                fontstyle="italic", color=LAYER, zorder=6,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8})
        ax.text(BOX_AREA_LEFT, label_top - 2.0 * LABEL_PITCH, row["label"][1],
                ha="left", va="center", fontsize=TEXT_PT, fontweight="bold",
                fontstyle="italic", color=LAYER, zorder=6,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8})
        box_top = label_top - 2.0 * LABEL_PITCH - LABEL_GAP
        box_h = layout["box_heights"][r]
        box_w = row_box_width(r)
        for c, lines in zip(row.get("cols", range(4)), layout["wrapped"][r]):
            x0 = row_box_left(r, c)
            ax.add_patch(FancyBboxPatch(
                (x0, box_top - box_h), box_w, box_h,
                boxstyle="round,pad=0.0,rounding_size=0.04",
                linewidth=0.0, facecolor=row["color"], zorder=2))
            n = len(lines)
            for k, line in enumerate(lines):
                ly = box_top - 0.5 * box_h + (n / 2.0 - k - 0.5) * LINE_PITCH
                ax.text(COL_CENTERS[c], ly, line, ha="center", va="center",
                        fontsize=TEXT_PT, color=BOX_TEXT, zorder=3)
        row_centers.append(box_top - 0.5 * box_h)
        y = box_top - box_h - ROW_GAP

    # Derivation arrows, source centre bottom to target centre top, one per
    # lane that exists in both adjacent rows (the PINN lane is absent from
    # the METHODS and IMPLEMENTATION rows, so no arrow enters the gap).
    for r in range(3):
        shared = sorted(set(ROWS[r].get("cols", range(4))) &
                        set(ROWS[r + 1].get("cols", range(4))))
        for c in shared:
            cx = COL_CENTERS[c]
            y_from = row_centers[r] - 0.5 * layout["box_heights"][r]
            y_to = row_centers[r + 1] + 0.5 * layout["box_heights"][r + 1]
            ax.annotate(
                "", xy=(cx, y_to + 0.02), xytext=(cx, y_from - 0.02),
                arrowprops={"arrowstyle": "-|>", "color": ARROW,
                            "linewidth": 1.4, "mutation_scale": 11,
                            "shrinkA": 0.0, "shrinkB": 0.0},
                zorder=1)

    # Three red dashed data-flow arrows in row 3, in the wider gaps, with
    # italic labels above them (THEORY T2).
    cy3 = row_centers[2]
    for src, dst, label in RED_ARROWS:
        x_from = row_box_left(2, src) + ROW3_BOX_W
        x_to = row_box_left(2, dst)
        ax.annotate(
            "", xy=(x_to - 0.015, cy3), xytext=(x_from + 0.015, cy3),
            arrowprops={"arrowstyle": "-|>", "color": RED, "linewidth": 1.4,
                        "mutation_scale": 10, "linestyle": (0, (5, 3)),
                        "shrinkA": 0.0, "shrinkB": 0.0},
            zorder=3)
        ax.text(0.5 * (x_from + x_to), cy3 + 0.14, label, ha="center",
                va="center", fontsize=TEXT_PT, fontstyle="italic", color=RED,
                zorder=6,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6})

    # Bottom legend: a 2 by 2 grid of colour patches with labels.
    legend_top = y - 0.12
    patch_w, patch_h = 0.16, 0.11
    entry_gap = 0.30
    for i, (text, color) in enumerate(LEGEND):
        row_i, col_i = divmod(i, 2)
        label_w = text_width_in(text, TEXT_PT)
        row_entries = [LEGEND[2 * row_i], LEGEND[2 * row_i + 1]]
        row_w = sum(patch_w + 0.08 + text_width_in(e[0], TEXT_PT)
                    for e in row_entries) + entry_gap
        x = 0.5 * (PRINT_W_IN - row_w) + (
            0.0 if col_i == 0 else
            patch_w + 0.08 + text_width_in(row_entries[0][0], TEXT_PT)
            + entry_gap)
        ey = legend_top - row_i * 0.20
        ax.add_patch(Rectangle((x, ey), patch_w, patch_h, facecolor=color,
                               edgecolor=color, linewidth=0.0, zorder=2))
        ax.text(x + patch_w + 0.08, ey + 0.5 * patch_h, text, ha="left",
                va="center", fontsize=TEXT_PT, color=INK, zorder=3)
    return fig


def all_drawn_strings() -> list:
    """Return every string the figure will draw.

    :returns: the list of all title, label, box, arrow-label and legend
        strings.
    """
    strings = [TITLE]
    for row in ROWS:
        strings.extend(row["label"])
        for box in row["boxes"]:
            strings.extend(box)
    for _, _, label in RED_ARROWS:
        strings.append(label)
    for text, _ in LEGEND:
        strings.append(text)
    return strings


def verify(fig: plt.Figure, scale: float) -> None:
    """Check the written figure against the readability floor.

    :param fig: the figure that was written, still open.
    :param scale: placement scale reported by the print fit.
    :returns: None.
    :raises RuntimeError: if the smallest printed text is under the floor or
        if two printed labels collide.
    """
    printed, why = fm.smallest_text_pt(fig, scale)
    print("smallest printed text %.2f pt (%s); floor %.1f pt"
          % (printed, why, MIN_PRINTED_PT))
    if printed < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is under the %.1f pt floor from %s"
            % (printed, MIN_PRINTED_PT, why))
    overlaps = fm.text_overlaps_pt(fig, scale)
    if overlaps:
        detail = "; ".join("%s vs %s (%.2f pt)" % (a, b, min(w, h))
                           for a, b, w, h in overlaps[:4])
        raise RuntimeError("printed labels collide: %s" % detail)


def main() -> int:
    """Write the figure and verify it.

    :returns: 0 on success, 1 on rejection.
    """
    pf.require_clean(*all_drawn_strings())
    assert_boxes_fit()
    fig = None
    tmp = FIGDIR / TMP_NAME
    try:
        fig = draw()
        pf.assert_inside_canvas(fig)
        _, scale = pf.save_to_print_width(fig, TMP_NAME, PRINT_TARGET_IN,
                                          close=False)
        # The save scale is relative to PRINT_TARGET_IN, but the reader sees
        # the file at 0.90\textwidth; multiply so verify() judges floor and
        # collisions at the printed size, not at the design size.
        verify(fig, scale * INCLUDE_SCALE)
        plt.close(fig)
        fig = None
        final = FIGDIR / FINAL_NAME
        os.replace(tmp, final)
        print("wrote %s at print width %.4f in" % (final.name, PRINT_TARGET_IN))
        return 0
    except RuntimeError as exc:
        print("methodology_derivation FAILED: %s" % exc, file=sys.stderr)
        if fig is not None:
            plt.close(fig)
        if tmp.exists():
            tmp.unlink()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
