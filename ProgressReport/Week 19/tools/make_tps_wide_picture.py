#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Re-lay the six TPS panels of Chapter 4 into one landscape plate.

WHY: the thesis prints the reference and the optimised topology as two tall
columns of three panels each, which is the right shape for a page but the
wrong shape for the deck: placed as it is, the picture is height-capped in
the slide box and half of the horizontal space is left empty. The same six
panels, laid three plot types across and two trees down, fill the box, and
nothing inside a panel is touched: every panel is cropped out of the thesis
plate as published and pasted back verbatim, with only the row and column
labels redrawn, because those labels belong to the layout and the layout is
what changed. The paragraph the thesis bakes under the plates is dropped
here on purpose, because the slide caption and the source block carry the
same statement.

The script writes only into the figures folder of the deck. It re-runs
itself under the interpreter of the thesis, which is the interpreter that
already holds matplotlib; the project virtual environment must not be
polluted. The module therefore imports no plotting library, which is also
what keeps the ruff and pyrefly gates of the deck clean.

Citations:
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.imshow.html
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

#: The plate as the thesis prints it, and the landscape plate this writes.
SOURCE = FIGURES / "thesis_tps_reference_vs_optimized.png"
OUT_WIDE = FIGURES / "thesis_tps_reference_vs_optimized_wide.png"

#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 20000
#: Dots per inch of the raster, so a 7.70 in picture is 2310 px wide.
DPI = 300

#: The drawing program. It is run as a script by the interpreter of the
#: thesis, because that is where matplotlib lives. The six panels are found
#: by measuring the dark rectangles of the source plate rather than by
#: hard-coded coordinates, so a plate redrawn at another size still composes.
DRIVER = r'''
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image

SOURCE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
MIN_BYTES = int(sys.argv[3])
DPI = int(sys.argv[4])

W_IN, H_IN = 7.70, 3.98
COL_TITLES = ["stacked ply temperature", "per-ply heat-flux distribution",
              "surface energy balance"]
ROW_TITLES = ["reference", "optimised"]


def is_dark(pixel):
    """Return True when a pixel belongs to a panel background."""
    red, green, blue = pixel
    return 0.299 * red + 0.587 * green + 0.114 * blue < 100.0


def row_bands(image, x_lo, x_hi, min_dark, min_height):
    """Return the vertical bands whose rows are dominated by panel pixels."""
    px = image.load()
    bands = []
    start = None
    for y in range(image.height):
        count = 0
        for x in range(x_lo, min(x_hi, image.width)):
            if is_dark(px[x, y]):
                count += 1
        if count > min_dark and start is None:
            start = y
        elif count <= min_dark and start is not None:
            if y - start >= min_height:
                bands.append((start, y))
            start = None
    if start is not None and image.height - start >= min_height:
        bands.append((start, image.height))
    return bands


def column_groups(image, y_lo, y_hi, min_dark, min_width):
    """Return the horizontal groups whose columns are dominated by panels."""
    px = image.load()
    groups = []
    start = None
    span = y_hi - y_lo
    for x in range(image.width):
        count = 0
        for y in range(y_lo, y_hi):
            if is_dark(px[x, y]):
                count += 1
        if count > min_dark and start is None:
            start = x
        elif count <= min_dark and start is not None:
            if x - start >= min_width:
                groups.append((start, x))
            start = None
    if start is not None and image.width - start >= min_width:
        groups.append((start, image.width))
    assert len(groups) >= 2, "expected two panel columns, measured " + str(span)
    return groups[:2]


if not SOURCE.is_file():
    sys.stderr.write("MISMATCH the TPS plate is missing: " + str(SOURCE) + "\n")
    raise SystemExit(1)

image = Image.open(SOURCE).convert("RGB")
bands = row_bands(image, 60, min(1790, image.width), 300, 120)

# WHY: a panel of the source plate is not always one solid dark band. The
# stacked-ply heatmap of the first row carries a bright table strip across its
# lower part, so the scan breaks that one panel into two bands, one of them
# far shorter than the others. A band less than 60 percent of the median band
# height is therefore a bridge inside a panel, not a panel row, and is folded
# into the band above it. Measured on the 1800 by 1905 plate: the four raw
# bands are 286, 139, 463 and 463 px, so only the 139 px strip is absorbed and
# the three panel rows come out at 462, 463 and 463 px.
if bands:
    heights = sorted(band[1] - band[0] for band in bands)
    median = heights[len(heights) // 2]
    merged = []
    for band in bands:
        if merged and (band[1] - band[0]) < 0.6 * median:
            merged[-1] = (merged[-1][0], band[1])
        else:
            merged.append(band)
    bands = merged

if len(bands) != 3:
    sys.stderr.write("MISMATCH expected three panel rows, measured "
                     + str(len(bands)) + "\n")
    raise SystemExit(1)

# WHY: the six panels sit on one shared column grid, so the two columns are
# measured once, on the first row, where both panels are a solid dark field
# with no bright artwork across them. Measuring them again per row is not
# only redundant but wrong: on the bar-chart row the bright bars and their
# error whiskers leave a column only partly dark, so a per-row scan there
# returns narrow strips (221 and 204 px instead of 846). The one measured
# grid is then applied to every row.
groups = column_groups(image, bands[0][0], bands[0][1],
                       int(0.6 * (bands[0][1] - bands[0][0])), 200)

panels = []
for y_lo, y_hi in bands:
    for x_lo, x_hi in groups:
        panels.append(image.crop((x_lo, y_lo, x_hi, y_hi)))
if len(panels) != 6:
    sys.stderr.write("MISMATCH expected six panels, measured "
                     + str(len(panels)) + "\n")
    raise SystemExit(1)

figure = plt.figure(figsize=(W_IN, H_IN), facecolor="white")
left = 0.045
col_gap = 0.008
cols = 3
rows_n = 2
# The panels of the source plate are 2 columns by 3 rows; the slide wants the
# opposite reading, 3 columns (temperature, heat flux, energy balance) by 2
# rows (reference, optimised). So panel index 2 * column + row is the one that
# belongs in that cell, and the number of the row inside the source plate is
# also the number of the column on the slide.
cw = (1.0 - left - 0.008 - col_gap * (cols - 1)) / cols
# The raster of a panel fixes its height for a given width, so the axes box is
# cut to that shape and imshow fills it exactly with no letterboxing.
ch = cw * (W_IN / H_IN) / (panels[0].width / panels[0].height)
# The block of two rows is centred vertically, so the empty margin is shared
# above and below rather than all sitting in the middle of the picture.
row_gap = 0.050
block = rows_n * ch + row_gap
top_limit = 0.930
bottom = 0.020 + ((top_limit - 0.020) - block) / 2.0
for col in range(cols):
    for row in range(rows_n):
        axis = figure.add_axes(
            [left + col * (cw + col_gap),
             bottom + (rows_n - 1 - row) * (ch + row_gap), cw, ch],
        )
        _ = axis.imshow(panels[2 * col + row])
        axis.set_axis_off()
        axis.set_aspect("equal")
for col, title in enumerate(COL_TITLES):
    figure.text(
        left + col * (cw + col_gap) + cw / 2.0, 0.985, title,
        ha="center", va="top", fontsize=10.0, weight="bold", color="#101820",
    )
for row, title in enumerate(ROW_TITLES):
    figure.text(
        0.020, bottom + (rows_n - 1 - row) * (ch + row_gap) + ch / 2.0, title,
        rotation=90, ha="center", va="center", fontsize=9.0,
        weight="bold", color="#101820",
    )
OUT.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(OUT, dpi=DPI, facecolor="white")
size = OUT.stat().st_size if OUT.is_file() else 0
if size < MIN_BYTES:
    sys.stderr.write("MISMATCH the wide TPS plate was not written: "
                     + str(size) + " bytes\n")
    raise SystemExit(1)
with Image.open(OUT) as written:
    width, height = written.size
sys.stdout.write("[ok] wide TPS plate: " + str(width) + "x" + str(height)
                 + "px, " + str(size) + " bytes, panels "
                 + ", ".join(str(p.width) + "x" + str(p.height) for p in panels)
                 + "\n")
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
            str(SOURCE),
            str(OUT_WIDE),
            str(MIN_PICTURE_BYTES),
            str(DPI),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(f"MISMATCH the wide TPS plate failed:\n{completed.stderr[-2000:]}\n")
        return 1
    return 0


def main() -> int:
    """Compose the landscape TPS plate and report what was written.

    Returns:
        Zero when the plate was written, one when the interpreter or the
        source plate was missing.
    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the interpreter of the thesis is missing: {VENV_PYTHON}\n")
        return 1
    if not SOURCE.is_file():
        _ = sys.stdout.write(f"MISMATCH the source plate is missing: {SOURCE}\n")
        return 1
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
