#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the five-ply TPS layup that the thermal run actually solved.

WHY: the deck's TPS material slide used to carry the six generic presets of the
appendix table, which are the options the solver offers rather than the stack
that was modelled. The owner asked for the five plies that were simulated, with
their thickness, their share of the stack, their conductivity, their thermal
resistance and their temperature limit, because that is the stack the reported
surface temperature and heat load belong to.

The values come from the solved run, not from a preset list:
`stellarorion_program_proc/results/tps_conduction/00_reference/tps_step2200_layers.csv`
gives every ply with its start position, thickness and conductivity, and the
resistance of each ply is its thickness over its conductivity. The five
resistances sum to 0.3056 m2K/W, which is exactly the R the thesis states for
the five-ply layup in the thermal balance of chapter 3, so the table and the
equation that uses it cannot disagree.

The drawing lives in DRIVER and runs under the interpreter of the thesis, which
is the one that holds matplotlib; the deck virtual environment must not be
polluted. This file therefore imports no plotting library, which is also what
keeps the ruff and pyrefly gates of the deck clean.

Citations:
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.table.html
    Pillow 12, https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
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
OUT_TABLE = FIGURES / "thesis_tps_layup_table.png"

#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 5000

#: Dots per inch of the raster, so a 7.70 in picture is 2310 px wide.
DPI = 300

#: The drawing program. It is run as a script by the interpreter of the thesis.
DRIVER = r'''
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image

OUT = Path(sys.argv[1])
MIN_BYTES = int(sys.argv[2])
DPI = int(sys.argv[3])
W_IN = float(sys.argv[4])
H_IN = float(sys.argv[5])

# The five plies of the solved stack, from the layer export of the reference
# thermal run: ply number, material, thickness in mm, conductivity in W/m K,
# resistance in m2K/W (thickness over conductivity) and the service limit.
PLIES = [
    (1, "Nicalon SiC", 0.506, 1.5, 0.00034, 2073),
    (2, "Nicalon SiC", 0.506, 1.5, 0.00034, 2073),
    (3, "Pyrogel 3350", 3.047, 0.02, 0.15235, 1373),
    (4, "Pyrogel 3350", 3.047, 0.02, 0.15235, 1373),
    (5, "Kapton", 0.025, 0.12, 0.00021, 773),
]

COLUMNS = [
    "Ply",
    "Material",
    "Thickness (mm)",
    "Share (%)",
    "k (W/m K)",
    "R (m2K/W)",
    "T max (K)",
]
COL_WIDTHS = [0.07, 0.23, 0.15, 0.13, 0.13, 0.15, 0.14]

C_HEAD = "#123A63"
C_EDGE = "#8FA2BC"
C_ROW_ALT = "#EEF3FA"
C_TOTAL = "#DCE7F3"
C_INSUL = "#FFF1DC"
C_TEXT = "#101820"
C_NOTE = "#404A57"

PT_HEAD = 10.5
PT_CELL = 10.5
PT_NOTE = 8.6


def build_rows():
    """Return the cell text of the header, the five plies and the total row."""
    total_thickness = sum(ply[2] for ply in PLIES)
    total_resistance = sum(ply[4] for ply in PLIES)
    body = []
    for ply, material, thickness, conductivity, resistance, limit in PLIES:
        share = 100.0 * thickness / total_thickness
        body.append([
            str(ply),
            material,
            f"{thickness:.3f}",
            f"{share:.2f}",
            f"{conductivity:.2f}",
            f"{resistance:.5f}",
            f"{limit:,}",
        ])
    total = [
        "",
        "Five-ply stack",
        f"{total_thickness:.3f}",
        "100.0",
        "",
        f"{total_resistance:.4f}",
        f"{max(ply[5] for ply in PLIES):,}",
    ]
    return body, total


def draw():
    """Draw the layup table and report what was written."""
    body, total = build_rows()
    figure = plt.figure(figsize=(W_IN, H_IN))
    axis = figure.add_axes([0.0, 0.0, 1.0, 1.0])
    axis.set_axis_off()
    table = axis.table(
        cellText=body + [total],
        colLabels=COLUMNS,
        colWidths=COL_WIDTHS,
        loc="center",
        cellLoc="center",
        bbox=[0.0, 0.085, 1.0, 0.895],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(PT_CELL)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor(C_EDGE)
        cell.set_linewidth(0.8)
        if row == 0:
            cell.set_facecolor(C_HEAD)
            cell.set_text_props(color="white", weight="bold", fontsize=PT_HEAD)
            continue
        if row == len(body) + 1:
            # The total row carries the two numbers the argument turns on: the
            # stack thickness and the resistance the thermal balance divides by.
            cell.set_facecolor(C_TOTAL)
            cell.set_text_props(color=C_TEXT, weight="bold")
            continue
        cell.set_facecolor("white" if row % 2 else C_ROW_ALT)
        cell.set_text_props(color=C_TEXT)
        if column == 1:
            cell.set_text_props(color=C_TEXT, ha="left")
        if column == 5 and row in (3, 4):
            # The two Pyrogel plies hold nearly all of the resistance, so the
            # column is tinted on those two rows rather than the whole column.
            cell.set_facecolor(C_INSUL)
            cell.set_text_props(color=C_TEXT, weight="bold")
    figure.text(
        0.012,
        0.030,
        "R = thickness / conductivity, summed over the stack. The two Pyrogel plies "
        "hold 99.7 percent of the 0.3056 m2K/W.",
        fontsize=PT_NOTE,
        color=C_NOTE,
        ha="left",
        va="bottom",
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUT, dpi=DPI, facecolor="white")
    plt.close(figure)
    size = OUT.stat().st_size if OUT.is_file() else 0
    if size < MIN_BYTES:
        sys.stderr.write("MISMATCH the layup table was not written: "
                         + str(size) + " bytes in " + str(OUT) + "\n")
        raise SystemExit(1)
    with Image.open(OUT) as image:
        width, height = image.size
    sys.stdout.write("[ok] tps layup table: " + str(width) + "x" + str(height)
                     + "px, " + str(size) + " bytes\n")


draw()
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
            str(MIN_PICTURE_BYTES),
            str(DPI),
            "7.70",
            "3.85",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # WHY: writing an empty string is a no-op, so no truth test is needed,
    # and a truth test on a string is exactly what pyrefly forbids.
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(f"MISMATCH the layup table failed:\n{completed.stderr[-2000:]}\n")
        return 1
    return 0


def main() -> int:
    """Draw the five-ply layup table.

    Returns:
        Zero when the picture was written, one when the interpreter of the
        thesis is missing or the drawing failed.
    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the interpreter of the thesis is missing: {VENV_PYTHON}\n")
        return 1
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
