#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the five stages of the research workflow as one landscape plate.

WHY: the deck's methodology slide describes the work as five numbered stages,
while the plate it used to carry, `thesis_software_pipeline.png`, is an
architecture diagram whose columns are INPUT, CORE ENGINE, SOLVERS, MODELS and
OUTPUT. It never shows a numbered stage anywhere, so the cards invented a
process the picture did not have, and a reader had to reconcile two different
vocabularies for the same programme. This plate is drawn in the deck, from the
same facts and in the same palette family as the thesis figure, but its columns
are the five stages the narration names, in the order the narration names them:
geometry, DSMC setup, simulation, validation and optimisation. Validation is a
box of its own because the thesis figure has no such block and because the
comparison the deck makes is only trustworthy if the validation step is visible.

The feedback arc is drawn, not implied: the optimiser writes the next geometry
back to stage one, which is why the five stages are a loop and not a list.

The script writes only into the figures folder of the deck. It re-runs itself
under the interpreter of the thesis, which is the interpreter that already
holds matplotlib; the project virtual environment must not be polluted. The
module therefore imports no plotting library, which is also what keeps the ruff
and pyrefly gates of the deck clean.

AXIOMS
    A1 A stage exists in this plate only if the narration names it, so the
       picture and the cards cannot drift apart again.
    A2 The order is the order of the work, not the order of the file system.
    A3 The palette is the palette of the thesis figure, so the deck still reads
       as one document.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.annotate.html
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.FancyBboxPatch.html
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"

#: The plate this writes.
OUT = FIGURES / "thesis_stage_pipeline.png"

#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 20000
#: Dots per inch of the raster, so a 7.70 in picture is 2310 px wide.
DPI = 300

#: The drawing program. It is run as a script by the interpreter of the
#: thesis, because that is where matplotlib lives. Colours are the colours of
#: the thesis software pipeline figure, so the two pictures belong together.
DRIVER = r'''
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

OUT = Path(sys.argv[1])
MIN_BYTES = int(sys.argv[2])
DPI = int(sys.argv[3])

W_IN, H_IN = 7.70, 4.01
INK = "#212121"
ARROW = "#37474F"
ORANGE = "#E65100"

TITLE = "StellarOrion Research Workflow, Five Stages"

# Each stage carries its own name and the facts the narration states, one
# phrase per line so the wrap is decided here and not by the renderer.
STAGES = (
    ("1", "GEOMETRY", "#2871C5", "#1665C0",
     ("CadQuery CAD", "scalloped and", "smooth skins", "STL export")),
    ("2", "DSMC SETUP", "#3F8742", "#2F7D33",
     ("SPARTA case", "5-species air", "VSS collisions",
      "grid finer than", "the mean free path")),
    ("3", "SIMULATION", "#3F8742", "#2F7D33",
     ("millions of", "particles", "advection and",
      "surface collisions", "VTK output")),
    ("4", "VALIDATION", "#582795", "#4B158C",
     ("grid independence", "Sutton-Graves", "IRVE-3 flight data",
      "heat load gate")),
    ("5", "OPTIMISATION", "#E85F14", "#E65201",
     ("GA, population 50", "tournament,", "crossover, mutation",
      "writes the next", "geometry back")),
)

LEFT = 0.14
COLS = len(STAGES)
GAP = 0.30
CW = (W_IN - 2.0 * LEFT - GAP * (COLS - 1)) / COLS
HEAD_H = 0.235
HEAD_BOTTOM = 3.315
BODY_TOP = 3.255
BODY_BOTTOM = 1.155
LOOP_Y = 0.620
LABEL_Y = 0.330
LINE_STEP = 0.250

figure = plt.figure(figsize=(W_IN, H_IN), facecolor="white")
axis = figure.add_axes((0.0, 0.0, 1.0, 1.0))
axis.set_xlim(0.0, W_IN)
axis.set_ylim(0.0, H_IN)
axis.set_axis_off()

axis.text(W_IN / 2.0, 3.845, TITLE, ha="center", va="center",
            fontsize=12.5, weight="bold", color=INK, family="serif")

for index, (number, name, fill, edge, lines) in enumerate(STAGES):
    x0 = LEFT + index * (CW + GAP)
    axis.add_patch(Rectangle((x0, BODY_BOTTOM), CW, BODY_TOP - BODY_BOTTOM,
                             facecolor="white", edgecolor=edge,
                             linewidth=1.6, zorder=2))
    axis.add_patch(Rectangle((x0, HEAD_BOTTOM), CW, HEAD_H,
                             facecolor=fill, edgecolor=edge,
                             linewidth=1.6, zorder=3))
    axis.text(x0 + CW / 2.0, HEAD_BOTTOM + HEAD_H / 2.0,
                number + "  " + name, ha="center", va="center",
                fontsize=9.2, weight="bold", color="white", family="serif",
                zorder=4)
    middle = (BODY_TOP + BODY_BOTTOM) / 2.0
    start = middle + (len(lines) - 1) * LINE_STEP / 2.0
    for row, line in enumerate(lines):
        axis.text(x0 + CW / 2.0, start - row * LINE_STEP, line,
                    ha="center", va="center", fontsize=8.8, color=INK,
                    family="serif", zorder=4)
    if index:
        axis.add_patch(FancyArrowPatch(
            (x0 - GAP + 0.030, middle), (x0 - 0.020, middle),
            arrowstyle="-|>", mutation_scale=13.0, color=ARROW,
            linewidth=1.5, zorder=5,
        ))

first = LEFT + CW / 2.0
last = LEFT + (COLS - 1) * (CW + GAP) + CW / 2.0
axis.plot([last, last], [BODY_BOTTOM, LOOP_Y], color=ORANGE, linewidth=1.6,
          solid_capstyle="butt", zorder=5)
axis.plot([last, first], [LOOP_Y, LOOP_Y], color=ORANGE, linewidth=1.6,
          solid_capstyle="butt", zorder=5)
axis.add_patch(FancyArrowPatch(
    (first, LOOP_Y), (first, BODY_BOTTOM - 0.015),
    arrowstyle="-|>", mutation_scale=13.0, color=ORANGE, linewidth=1.6,
    zorder=5,
))
axis.text((first + last) / 2.0, LABEL_Y,
            "the GA writes the winning geometry back to stage 1",
            ha="center", va="center", fontsize=8.8, style="italic",
            color=ORANGE, family="serif")

OUT.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(OUT, dpi=DPI, facecolor="white")
plt.close(figure)
size = OUT.stat().st_size if OUT.is_file() else 0
if size < MIN_BYTES:
    sys.stderr.write("MISMATCH the stage pipeline plate was not written: "
                     + str(size) + " bytes\n")
    raise SystemExit(1)
sys.stdout.write("[ok] stage pipeline plate: " + str(W_IN) + "x" + str(H_IN)
                 + " in, " + str(size) + " bytes, " + str(COLS) + " stages\n")
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
            str(OUT),
            str(MIN_PICTURE_BYTES),
            str(DPI),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(
            "MISMATCH the stage pipeline plate failed:\n"
            + completed.stderr[-2000:]
            + "\n",
        )
        return 1
    return 0


def main() -> int:
    """Draw the five stage pipeline plate and report what was written.

    Returns:
        Zero when the plate was written, one when the interpreter of the
        thesis is missing.
    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(
            "MISMATCH the interpreter of the thesis is missing: "
            + str(VENV_PYTHON)
            + "\n",
        )
        return 1
    FIGURES.mkdir(parents=True, exist_ok=True)
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
