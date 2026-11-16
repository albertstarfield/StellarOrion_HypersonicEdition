#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the two validation pictures of the deck's methodology block.

WHY: the deck's methodology block ends with the seven DSMC channels, but
nothing in it showed this run compared against the published IRVE-3 flight
data. The thesis carries that comparison as the table tab:irve3_validation in
chapter 3, and the deck has no native table renderer, so the table has to
arrive as a picture. The companion slide needs a plot that says the same
thing: one grouped bar chart per scalar of the table, with the reference
trajectory record underneath it as the source of the flight column. The
orphaned rapisarda_scalar_comparison.png of the thesis was rejected on
purpose: its raw export numbers (390.29 W/cm2 peak heat flux and a peak drag
against a zero reference) contradict the table and would put three different
heat-flux values on one slide.

The drawing itself lives in DRIVER and runs under the interpreter of the
thesis, which is the interpreter that already holds matplotlib; the project
virtual environment must not be polluted. This file therefore imports no
plotting library, which is also what keeps the ruff and pyrefly gates of the
deck clean.

The script writes only into the figures folder of the deck.

Citations:
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.table.html
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.imshow.html
    Pillow 12, https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
THESIS_FIGURES = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"

#: The two pictures this script writes, in the naming convention of the deck.
OUT_TABLE = FIGURES / "thesis_irve3_validation_table.png"
OUT_PLOTS = FIGURES / "thesis_validation_comparison.png"

#: The reference trajectory record of the thesis, the source of the lower half
#: of the second picture. Its top band carries a title box that the thesis
#: export clipped, so that band is cropped away before the picture is drawn.
RECORD_SOURCE = THESIS_FIGURES / "heatRate_HIAD2015_IRVE3.png"
RECORD_TOP_CROP_PX = 31

#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 5000
#: Dots per inch of the raster, so a 7.70 in picture is 2310 px wide.
DPI = 300

#: The drawing program. It is run as a script by the interpreter of the
#: thesis, because that is where matplotlib lives.
DRIVER = r'''
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image

TABLE_OUT = Path(sys.argv[1])
PLOTS_OUT = Path(sys.argv[2])
RECORD = Path(sys.argv[3])
MIN_BYTES = int(sys.argv[4])
DPI = int(sys.argv[5])
TOP_CROP = int(sys.argv[6])

# Both pictures are drawn at the shape of the picture box of a side_points
# frame: SIDE_POINTS_PICTURE_WIDTH_IN wide and about 4.0 in tall once the
# caption has been taken from the 4.46 in of panel, so each lands at scale 1.0.
TABLE_W, TABLE_H = 7.70, 3.85
PLOTS_W, PLOTS_H = 7.70, 3.98
RECORD_WIDTH = 6.20

TABLE_HEAD_PT = 11.0
TABLE_CELL_PT = 11.0
TABLE_SMALL_PT = 9.0
METRIC_PT = 10.5
BAR_LABEL_PT = 9.5
# The category labels are set smaller than the rest: once the charts were
# inset from the left edge, "IRVE-3 flight" and "this work" met in the middle
# at 9.5 pt, and two labels touching under a pair of bars reads as one word.
X_TICK_PT = 8.5
DELTA_PT = 10.5

C_FLIGHT = "#0077BB"
C_WORK = "#EE7733"
C_OK = "#228833"
C_WIDE = "#CC3311"
C_GRID = "#C9D3E1"
C_EDGE = "#8FA2BC"
C_HEAD = "#123A63"
C_ROW_ALT = "#EEF3FA"

COLUMNS = [
    "Parameter",
    "IRVE-3\nflight",
    "MDAO\n(Fay-Riddell)",
    "StellarOrion\n(this work)",
    "SO error\n(%)",
]

# One tuple per row of tab:irve3_validation of chapter 3, in the order of the
# thesis: parameter, flight, MDAO reference, this work, error.
ROWS = [
    ("Peak heat flux\nq (SG)", "14.36 W/cm2", "13.83 W/cm2",
     "15.36 W/cm2", "+6.9%,\nnot like-for-like"),
    ("Total heat load\nQ", "195.06 J/cm2", "195.17 J/cm2",
     "165.72 J/cm2", "-15.0"),
    ("Peak deceleration", "19.7 g", "-", "22.72 g", "+15.3"),
    ("Ballistic coefficient\nbeta", "26.9 kg/m2", "-", "27.70 kg/m2", "+3.0"),
    ("Drag coefficient\nCd", "-", "-", "1.4625", "-"),
]

# Column widths as fractions of the picture width; they sum to one. The first
# and last are the widest because they carry the row labels and the two-line
# error note.
COL_WIDTHS = [0.27, 0.17, 0.19, 0.20, 0.17]
# Row heights as fractions of the picture height; the header and the first
# body row are taller because they carry two lines each.
ROW_HEIGHTS = [0.17, 0.19, 0.15, 0.15, 0.17, 0.17]

# The scalars of the table that both sides report, as
# (axis label, this work, flight, delta label, inside the 10 percent margin).
# The drag coefficient has no flight value and the heat flux is a correlation,
# so neither is charted here; both stay in the table above.
# Printed form of the values that the table prints differently from str():
# the ballistic coefficient of this work is 27.70 in tab:irve3_validation,
# and a chart that said 27.7 beside a table that said 27.70 would be a
# needless discrepancy on a validation slide.
VALUE_TEXT = {27.70: "27.70"}

METRICS = [
    ("Total heat load\n(J/cm2)", 165.72, 195.06, "delta -15.0%", False),
    ("Peak deceleration\n(g)", 22.72, 19.70, "delta +15.3%", False),
    ("Ballistic coefficient\n(kg/m2)", 27.70, 26.90, "delta +3.0%", True),
]


def save(figure, out, what):
    """Write a figure and fail loudly when the picture is not a real one."""
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=DPI, facecolor="white")
    size = out.stat().st_size if out.is_file() else 0
    if size < MIN_BYTES:
        sys.stderr.write("MISMATCH " + what + " was not written: "
                         + str(size) + " bytes in " + str(out) + "\n")
        raise SystemExit(1)
    with Image.open(out) as image:
        width, height = image.size
    return "[ok] " + what + ": " + str(width) + "x" + str(height) + "px, " + str(size) + " bytes"


def draw_table():
    """Draw tab:irve3_validation as a picture of its own."""
    figure = plt.figure(figsize=(TABLE_W, TABLE_H))
    axis = figure.add_axes([0.0, 0.0, 1.0, 1.0])
    axis.set_axis_off()
    table = axis.table(
        cellText=[list(row) for row in ROWS],
        colLabels=COLUMNS,
        colWidths=COL_WIDTHS,
        loc="center",
        cellLoc="center",
        bbox=[0.0, 0.0, 1.0, 1.0],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(TABLE_CELL_PT)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor(C_EDGE)
        cell.set_linewidth(0.8)
        cell.set_height(ROW_HEIGHTS[row])
        if row == 0:
            cell.set_facecolor(C_HEAD)
            cell.set_text_props(color="white", weight="bold", fontsize=TABLE_HEAD_PT)
            continue
        cell.set_facecolor("white" if row % 2 else C_ROW_ALT)
        cell.set_text_props(color="#101820")
        if column == 4:
            note = ROWS[row - 1][4]
            if note.startswith("+3.0"):
                # Inside the plus or minus 10 percent margin: the row the
                # thesis argument closes on, so it reads as a pass.
                cell.set_facecolor("#E4F3E8")
                cell.set_text_props(color=C_OK, weight="bold", fontsize=TABLE_SMALL_PT)
            elif note.startswith("-"):
                cell.set_text_props(color="#101820", fontsize=TABLE_CELL_PT)
            else:
                # Outside the margin, and flagged as not like-for-like, so
                # the note is set smaller and in the warning colour.
                cell.set_facecolor("#FBE9E7")
                cell.set_text_props(color=C_WIDE, fontsize=TABLE_SMALL_PT)
    report = save(figure, TABLE_OUT, "validation table")
    plt.close(figure)
    return report


def draw_comparison():
    """Draw the bar chart of the table above the reference record."""
    if not RECORD.is_file():
        sys.stderr.write("MISMATCH the flight record is missing: " + str(RECORD) + "\n")
        raise SystemExit(1)
    record = Image.open(RECORD).convert("RGB")
    record = record.crop((0, TOP_CROP, record.width, record.height))
    aspect = record.width / record.height

    figure = plt.figure(figsize=(PLOTS_W, PLOTS_H))

    # The record keeps its own aspect, so its axes height follows from the
    # width it is given: the picture must not stretch a published plot.
    width_fraction = RECORD_WIDTH / PLOTS_W
    height_fraction = (RECORD_WIDTH / aspect) / PLOTS_H
    record_bottom = 0.02
    record_axis = figure.add_axes(
        [(1.0 - width_fraction) / 2.0, record_bottom, width_fraction, height_fraction],
    )
    _ = record_axis.imshow(record)
    record_axis.set_axis_off()

    # The band of bars is placed from the top of the record, not at a fixed
    # height, so a record of a different aspect can never be overprinted by
    # the tick labels of the charts. The title of the record is left to the
    # caption of the slide, which already names it.
    band_bottom = record_bottom + height_fraction + 0.09
    band_top = 0.97
    slot = 1.0 / len(METRICS)
    for index, (label, work, flight, delta, inside) in enumerate(METRICS):
        axis = figure.add_axes(
            [index * slot + 0.075, band_bottom, slot - 0.115, band_top - band_bottom],
        )
        _ = axis.bar(
            [0.0, 1.0], [flight, work], width=0.62,
            color=[C_FLIGHT, C_WORK], edgecolor=C_EDGE, linewidth=0.7,
        )
        axis.set_xticks([0.0, 1.0], ["IRVE-3 flight", "this work"], fontsize=X_TICK_PT)
        # A tight range keeps the two categories close to the middle of the
        # axes, which buys the two labels the gap they need.
        axis.set_xlim(-0.5, 1.5)
        # Head room of 100 percent: the bars stop halfway up the axes, which
        # leaves the value labels, the delta and the two title lines their own
        # band above them without any of the four touching.
        axis.set_ylim(0.0, max(flight, work) * 2.00)
        axis.tick_params(axis="y", labelsize=BAR_LABEL_PT)
        axis.grid(axis="y", color=C_GRID, linewidth=0.6)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        for x_value, value in ((0.0, flight), (1.0, work)):
            axis.text(
                x_value, value, VALUE_TEXT.get(value, str(value)),
                ha="center", va="bottom",
                fontsize=BAR_LABEL_PT, color="#101820",
            )
        # The metric name, its unit and the delta each take a line INSIDE the
        # axes: above the axes the title was clipped by the edge of the
        # picture, and centred on one line the name overran the axes on both
        # sides and sat on the tick labels.
        name, unit = label.split("\n")
        axis.text(
            0.5, 0.99, name, transform=axis.transAxes,
            ha="center", va="top", fontsize=METRIC_PT, weight="bold",
            color="#101820",
        )
        axis.text(
            0.5, 0.88, unit, transform=axis.transAxes,
            ha="center", va="top", fontsize=METRIC_PT, color="#101820",
        )
        axis.text(
            0.5, 0.74, delta, transform=axis.transAxes, ha="center", va="top",
            fontsize=DELTA_PT, weight="bold", color=C_OK if inside else C_WIDE,
        )

    report = save(figure, PLOTS_OUT, "validation comparison")
    plt.close(figure)
    return report


sys.stdout.write(draw_table() + "\n")
sys.stdout.write(draw_comparison() + "\n")
'''


def render() -> int:
    """Run the drawing program under the interpreter of the thesis.

    Returns:
        The exit code of the drawing program.
    """
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(VENV_PYTHON),
            "-c",
            DRIVER,
            str(OUT_TABLE),
            str(OUT_PLOTS),
            str(RECORD_SOURCE),
            str(MIN_PICTURE_BYTES),
            str(DPI),
            str(RECORD_TOP_CROP_PX),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(f"MISMATCH the validation pictures failed:\n{completed.stderr[-2000:]}\n")
        return 1
    return 0


def main() -> int:
    """Draw both validation pictures and report what was written.

    Returns:
        Zero when both pictures were written, one when the interpreter of the
        thesis or a source picture was missing.
    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the interpreter of the thesis is missing: {VENV_PYTHON}\n")
        return 1
    if not RECORD_SOURCE.is_file():
        _ = sys.stdout.write(f"MISMATCH the source record is missing: {RECORD_SOURCE}\n")
        return 1
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
