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
ROW_TITLES = ["validation reference", "optimised topology"]


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
if len(bands) != 3:
    sys.stderr.write("MISMATCH expected three panel rows, measured "
                     + str(len(bands)) + "\n")
    raise SystemExit(1)

panels = []
for y_lo, y_hi in bands:
    groups = column_groups(image, y_lo, y_hi, int(0.6 * (y_hi - y_lo)), 200)
    for x_lo, x_hi in groups:
        panels.append(image.crop((x_lo, y_lo, x_hi, y_hi)))
if len(panels) != 6:
    sys.stderr.write("MISMATCH expected six panels, measured "
                     + str(len(panels)) + "\n")
    raise SystemExit(1)

figure = plt.figure(figsize=(W_IN, H_IN), facecolor="white")
left = 0.105
bottom = 0.02
top_band = 0.065
col_gap = 0.010
row_gap = 0.022
cols = 3
rows_n = 2
cw = (1.0 - left - col_gap * (cols - 1)) / cols
ch = (1.0 - top_band - row_gap * (rows_n - 1)) / rows_n
for index, panel in enumerate(panels):
    row, col = divmod(index, cols)
    axis = figure.add_axes(
        [left + col * (cw + col_gap),
         bottom + (rows_n - 1 - row) * (ch + row_gap), cw, ch],
    )
    _ = axis.imshow(panel)
    axis.set_axis_off()
    axis.set_aspect("equal")
for col, title in enumerate(COL_TITLES):
    figure.text(
        left + col * (cw + col_gap) + cw / 2.0, 0.985, title,
        ha="center", va="top", fontsize=10.0, weight="bold", color="#101820",
    )
for row, title in enumerate(ROW_TITLES):
    figure.text(
        0.030, bottom + (rows_n - 1 - row) * (ch + row_gap) + ch / 2.0, title,
        rotation=90, ha="center", va="center", fontsize=9.5,
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
