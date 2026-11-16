#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the reference-against-optimised differences table of the deck.

WHY: the deck compares the reference body and the optimised topology as
pictures (the flown topologies, the thermal response) but never states the two
sets of numbers side by side, so a reader cannot see how much of the geometry
moved and how much of the thermal answer moved with it. Both blocks belong to
the SAME pair of bodies: the reference flown by SPARTA and the optimised
topology, each 1.2694 m long, at the same run condition (52.07 km, 3101 m/s,
step 2200). The gate heat load row is carried deliberately: it is identical on
both sides because the gate column is the Sutton-Graves value at the matched
nose radius, not a solver quantity, and hiding that would let a reader mistake
it for a thermal result.

Every number is taken from Chapter 4 of the thesis:
    * geometry and measured surface load, chapter_04_results.tex, the caption of
      fig:topology_comparison and its alt text;
    * area-averaged and peak surface flux, the same caption;
    * surface temperatures, the caption of fig:tps_comparison;
    * gate heat load, tab:ga_two_pass and the same caption.
The deck has no table renderer, so the table arrives as a picture drawn here.

The drawing lives in DRIVER and runs under the interpreter of the thesis, which
is the interpreter that already holds matplotlib; the project virtual
environment must not be polluted, and keeping the import out of this module is
also what keeps the ruff and pyrefly gates of the deck clean.

Citations:
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.text.html
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.Rectangle.html
    Pillow 12, https://pillow.readthedocs.io/en/stable/reference/Image.html
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"

#: The picture this script writes, in the naming convention of the deck.
OUT_TABLE = FIGURES / "thesis_reference_vs_optimised_table.png"

#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 5000
#: Dots per inch of the raster, so a 7.70 in picture is 2310 px wide.
DPI = 300

#: The drawing program, run as a script by the interpreter of the thesis.
DRIVER = r"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image

OUT = Path(sys.argv[1])
MIN_BYTES = int(sys.argv[2])
DPI = int(sys.argv[3])

# The picture box of a side_points frame is 7.70 in wide and about 4.0 in tall,
# so the table is drawn at that shape and lands at scale 1.0.
W, H = 7.70, 3.85

C_HEAD = "#123A63"
C_BLOCK = "#DCE7F3"
C_ROW = "#FFFFFF"
C_ROW_ALT = "#EEF3FA"
C_EDGE = "#C9D3E1"
C_TEXT = "#101820"
C_OK = "#228833"
C_WATCH = "#B26B00"
C_WIDE = "#CC3311"
C_TINT_OK = "#E4F3E8"
C_TINT_WATCH = "#FDF3E0"
C_TINT_WIDE = "#FBE9E7"

PT_HEAD = 10.5
PT_BLOCK = 9.5
PT_ROW = 10.5
PT_DELTA = 10.5

# One tuple per row: block, quantity, reference value, optimised value, decimals.
# The two blocks are the two things the slide is about: how far the RADIUS
# moved, and how far the PERFORMANCE moved with it.
ROWS = [
    ("GEOMETRY", "Body length (m)", 1.2694, 1.2694, 4),
    ("GEOMETRY", "Nose radius (m)", 0.5500, 0.5500, 4),
    ("GEOMETRY", "Maximum radius (m)", 1.8802, 1.8298, 4),
    ("PERFORMANCE", "Surface heat load (J/cm2)", 1978.1, 1972.7, 1),
    ("PERFORMANCE", "Area-averaged flux (W/m2)", 565865.0, 575839.0, 0),
    ("PERFORMANCE", "Surface peak flux (W/m2)", 1824880.0, 1788250.0, 0),
    ("PERFORMANCE", "Mean surface temperature (K)", 801.35, 830.03, 2),
    ("PERFORMANCE", "Peak surface temperature (K)", 1430.25, 1430.25, 2),
    ("PERFORMANCE", "Gate heat load (J/cm2)", 165.716, 165.716, 3),
]

BLOCKS = ["GEOMETRY", "PERFORMANCE"]

# Column edges as fractions of the width. The quantity column is wide because
# it carries the units as well as the name; the delta column is wide enough for
# a signed percentage and, on the gate row, nothing more.
COLS = [0.0, 0.44, 0.62, 0.78, 1.0]


def number(value, decimals):
    # Format a value with thousands separators and no trailing noise.
    text = format(round(value, decimals), "." + str(decimals) + "f")
    whole, _, frac = text.partition(".")
    sign = ""
    if whole.startswith("-"):
        sign, whole = "-", whole[1:]
    grouped = format(int(whole), ",")
    return sign + grouped + ("." + frac if frac else "")


def delta_text(reference, optimised):
    # Percentage change from the reference body to the optimised body.
    if reference == 0.0:
        return "n/a"
    change = (optimised - reference) / abs(reference) * 100.0
    if abs(change) < 0.005:
        return "0.00%"
    return ("+" if change > 0.0 else "-") + format(abs(change), ".2f") + "%"


def delta_colour(reference, optimised):
    # Colour a delta by how far it moved, not by whether up is good.
    change = abs((optimised - reference) / abs(reference) * 100.0) if reference else 0.0
    if change <= 1.0:
        return C_OK, C_TINT_OK
    if change <= 5.0:
        return C_WATCH, C_TINT_WATCH
    return C_WIDE, C_TINT_WIDE


def draw():
    # Draw the table and return the report line of what was written.
    # Two block labels and one header share the row list, so the table height is
    # counted from all three rather than from the data rows alone.
    total_rows = 1 + len(BLOCKS) + len(ROWS)
    figure = plt.figure(figsize=(W, H))
    axes = figure.add_axes([0.0, 0.0, 1.0, 1.0])
    axes.set_xlim(0.0, 1.0)
    axes.set_ylim(0.0, float(total_rows))
    axes.set_axis_off()

    def band(y_bottom, height, colour):
        axes.add_patch(Rectangle((0.0, y_bottom), 1.0, height,
                                 facecolor=colour, edgecolor="none", zorder=0))

    def text(x, y, label, size, colour=C_TEXT, weight="normal", align="left"):
        axes.text(x, y, label, fontsize=size, color=colour, weight=weight,
                  ha=align, va="center", zorder=3)

    cursor = float(total_rows)

    # Header band.
    cursor -= 1.0
    band(cursor, 1.0, C_HEAD)
    text(0.02, cursor + 0.5, "Quantity", PT_HEAD, "white", "bold")
    text((COLS[1] + COLS[2]) / 2.0, cursor + 0.5, "Reference", PT_HEAD, "white", "bold", "center")
    text((COLS[2] + COLS[3]) / 2.0, cursor + 0.5, "Optimised", PT_HEAD, "white", "bold", "center")
    text((COLS[3] + COLS[4]) / 2.0, cursor + 0.5, "Change", PT_HEAD, "white", "bold", "center")

    row_index = 0
    for block in BLOCKS:
        # Block label row: it names what the rows under it are about, so the
        # radius rows can never be read as a performance claim.
        cursor -= 1.0
        band(cursor, 1.0, C_BLOCK)
        text(0.02, cursor + 0.5, block, PT_BLOCK, C_HEAD, "bold")
        for block_row in [row for row in ROWS if row[0] == block]:
            _, quantity, reference, optimised, decimals = block_row
            cursor -= 1.0
            colour, tint = delta_colour(reference, optimised)
            band(cursor, 1.0, C_ROW if row_index % 2 == 0 else C_ROW_ALT)
            # The delta cell is tinted over its own row band so the colour is a
            # property of the cell and cannot run into the quantity column.
            axes.add_patch(Rectangle((COLS[3], cursor), COLS[4] - COLS[3], 1.0,
                                     facecolor=tint, edgecolor="none", zorder=1))
            text(0.02, cursor + 0.5, quantity, PT_ROW)
            text((COLS[1] + COLS[2]) / 2.0, cursor + 0.5, number(reference, decimals),
                 PT_ROW, C_TEXT, "normal", "center")
            text((COLS[2] + COLS[3]) / 2.0, cursor + 0.5, number(optimised, decimals),
                 PT_ROW, C_TEXT, "normal", "center")
            text((COLS[3] + COLS[4]) / 2.0, cursor + 0.5, delta_text(reference, optimised),
                 PT_DELTA, colour, "bold", "center")
            row_index += 1

    # Rules: one under the header, one under every row, and vertical dividers
    # only where a column really starts, so the table reads as a grid of cells.
    axes.axhline(float(total_rows) - 1.0, color=C_EDGE, linewidth=1.1, zorder=4)
    for step in range(1, total_rows):
        axes.axhline(float(step), color=C_EDGE, linewidth=0.6, zorder=4)
    for edge in COLS[1:-1]:
        axes.axvline(edge, color=C_EDGE, linewidth=0.6, zorder=4)
    axes.add_patch(Rectangle((0.0, 0.0), 1.0, float(total_rows),
                             facecolor="none", edgecolor=C_EDGE, linewidth=1.2, zorder=5))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUT, dpi=DPI, facecolor="white")
    plt.close(figure)
    size = OUT.stat().st_size if OUT.is_file() else 0
    if size < MIN_BYTES:
        sys.stderr.write("MISMATCH the table was not written: " + str(size)
                         + " bytes in " + str(OUT) + "\n")
        raise SystemExit(1)
    with Image.open(OUT) as image:
        width, height = image.size
    return "[ok] reference vs optimised table: " + str(width) + "x" + str(height) + "px, " + str(size) + " bytes"


sys.stdout.write(draw() + "\n")
"""


def render() -> int:
    """Run the drawing program under the interpreter of the thesis.

    Returns:
        The exit code of the drawing program.
    """
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(VENV_PYTHON), "-c", DRIVER, str(OUT_TABLE), str(MIN_PICTURE_BYTES), str(DPI)],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(f"MISMATCH the differences table failed:\n{completed.stderr[-2000:]}\n")
        return 1
    return 0


def main() -> int:
    """Draw the differences table and report what was written.

    Returns:
        Zero when the picture was written, one when the interpreter or the
        render failed.
    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the interpreter of the thesis is missing: {VENV_PYTHON}\n")
        return 1
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
