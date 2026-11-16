#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the TPS material-presets table of appendix.tex (tab:tps) as a picture."""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"

OUT_TABLE = FIGURES / "thesis_tps_presets_table.png"

MIN_PICTURE_BYTES = 5000
DPI = 300

TABLE_W_IN = 7.70
TABLE_H_IN = 3.85

DRIVER = r"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image

TABLE_W_IN = 7.70
TABLE_H_IN = 3.85
OUT = Path(sys.argv[1])
MIN_BYTES = int(sys.argv[2])
DPI = int(sys.argv[3])

COLUMNS = ["Preset", "Material", "rho\n(kg/m3)", "c_p\n(J/kg K)",
           "k\n(W/m K)", "epsilon", "delta\n(m)"]

ROWS = [
    ("SiC", "Nicalon SiC", "1468", "1100", "0.20", "0.75", "0.0254"),
    ("PICAX", "Phenolic carbon", "320", "1500", "0.50", "0.85", "0.040"),
    ("LOFTID", "Nextel/Pyrogel", "300", "1200", "0.15", "0.80", "0.050"),
    ("Kapton", "Polyimide film", "1420", "1090", "0.12", "0.70", "0.005"),
    ("Pyrogel", "Aerogel insul.", "200", "1000", "0.02", "0.85", "0.025"),
    ("Multi", "Layer composite", "650", "1050", "0.10", "0.80", "0.040"),
]

WORK_ROW = 0

COL_WIDTHS = [0.11, 0.24, 0.10, 0.11, 0.10, 0.10, 0.24]
ROW_HEIGHTS = [0.15, 0.14, 0.14, 0.14, 0.14, 0.14, 0.15]

C_HEAD = "#123A63"
C_EDGE = "#8FA2BC"
C_ROW_ALT = "#EEF3FA"
C_WORK = "#E4F3E8"
C_WORK_TEXT = "#228833"

HEAD_PT = 9.5
CELL_PT = 9.5
WORK_PT = 9.5


def save(figure, out, what):
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


figure = plt.figure(figsize=(TABLE_W_IN, TABLE_H_IN))
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
table.set_fontsize(CELL_PT)
for (row, column), cell in table.get_celld().items():
    cell.set_edgecolor(C_EDGE)
    cell.set_linewidth(0.8)
    cell.set_height(ROW_HEIGHTS[row])
    if row == 0:
        cell.set_facecolor(C_HEAD)
        cell.set_text_props(color="white", weight="bold", fontsize=HEAD_PT)
        continue
    if row - 1 == WORK_ROW:
        cell.set_facecolor(C_WORK)
        cell.set_text_props(color=C_WORK_TEXT, weight="bold", fontsize=WORK_PT)
    else:
        cell.set_facecolor("white" if row % 2 else C_ROW_ALT)
        cell.set_text_props(color="#101820", fontsize=CELL_PT)

report = save(figure, OUT, "tps presets table")
plt.close(figure)
sys.stdout.write(report + "\n")
"""


def render() -> int:
    """Run the drawing program under the interpreter of the thesis.

    Returns:
        Zero when the picture was written, one otherwise.

    """
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(VENV_PYTHON), "-c", DRIVER, str(OUT_TABLE), str(MIN_PICTURE_BYTES), str(DPI)],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write("MISMATCH the tps presets table failed:\n" + completed.stderr[-2000:] + "\n")
        return 1
    return 0


def main() -> int:
    """Draw the tps presets table and report what was written.

    Returns:
        Zero when the picture was written, one otherwise.

    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write("MISMATCH the interpreter of the thesis is missing: " + str(VENV_PYTHON) + "\n")
        return 1
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
