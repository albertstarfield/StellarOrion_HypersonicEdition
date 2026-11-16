#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the optimization flowchart with the genetic algorithm spelled out.

WHY: the owner asked for the flowchart to show how the genetic algorithm
works and how the double pass is organised. The thesis figure only carries a
box named Bayesian optimization, which the thesis itself has removed, so this
generator redraws the picture for the deck: the twelve stage pipeline on top,
the optimization loop in the middle, and the inside of the genetic algorithm
with its four operators, its stopping rule and the two passes at the bottom.

The numbers are taken from chapter 3 of the thesis: population 50, at most
200 generations, tournament size 3, uniform crossover 0.7, Gaussian mutation
0.1 with sigma 10 percent of the range, elitism of 2, stagnation at 1e-6 over
20 generations, the correction factor clamped between 0.5 and 2.0.

The script writes only into the deck folder, backs up any picture it
replaces, and refuses to write a file that carries an em dash.
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
TARGET = PROJECT / "figures" / "thesis_optimization_flowchart.png"
BACKUP = Path(__file__).resolve().parent / "backups" / "thesis_optimization_flowchart_before_ga_band.png"
THESIS_PYTHON = (
    PROJECT.parent
    / "CurrentThesisFinalReport"
    / ".venv-pdf"
    / "bin"
    / "python"
)
EM_DASH = "\u2014"
MIN_BYTES = 20000

WIDTH_IN = 13.6
HEIGHT_IN = 7.0
#: The field separator that carries a list through one command line argument.
SEP = chr(30)
LABEL_PT = 17.0
SMALL_PT = 14.0

STAGES = [
    "Flight\nparameters",
    "Geometry\nquality",
    "Generate\nHIAD surface",
    "Write solver\nscript",
    "Build solver\ncontainer",
    "Run DSMC\nsimulation",
    "Parse\nsurface dumps",
    "Compute\nflight metrics",
    "Survivability\ncheck",
    "Sanity\nchecks",
    "Compare with\nIRVE-3 flight",
    "Export fields\nand plots",
]

LOOP = [
    "Design space\n(Latin hypercube)",
    "Genetic\nalgorithm",
    "Cost function\nJ(x)",
    "DSMC\nre-simulation",
    "Accept if\nq <= Q_target",
]

GA_STEPS = [
    "Evaluate J(x)\nclosed form",
    "Tournament\nselection, k = 3",
    "Uniform\ncrossover 0.7",
    "Gaussian\nmutation 0.1",
    "Elitism\nbest 2 kept",
]

DRIVER = r'''
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon

OUT = sys.argv[1]
SEP = chr(30)
width, height, label_pt, small_pt = (float(v) for v in sys.argv[2:6])
stages = sys.argv[6].split(SEP)
loop = sys.argv[7].split(SEP)
ga_steps = sys.argv[8].split(SEP)
stop_line = sys.argv[9]
pass_line = sys.argv[10]
title_line = sys.argv[11]

C_IN = "#E8C97A"
C_PROCESS = "#2F6FB0"
C_CHECK = "#C25B4C"
C_EDGE = "#333333"
C_GA = "#7B4FA8"
C_BAND = "#0B1A33"

fig, ax = plt.subplots(figsize=(width, height), dpi=200)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.axis("off")


def box(x, y, w, h, text, face, size):
    """Draw one rounded box and return it."""
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0,rounding_size=0.012",
        linewidth=1.4, edgecolor=C_EDGE, facecolor=face, zorder=3,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=size, color="white", zorder=4, linespacing=1.15)
    return patch


def link(x0, y0, x1, y1, color=C_EDGE, style="-|>"):
    """Draw one connector."""
    arrow = FancyArrowPatch(
        (x0, y0), (x1, y1), arrowstyle=style, color=color,
        linewidth=1.5, mutation_scale=13, zorder=5,
        shrinkA=0, shrinkB=0,
    )
    ax.add_patch(arrow)


# Band 1: the twelve stage pipeline, two rows of six.
ax.text(0.5, 0.985, title_line, ha="center", va="top", fontsize=21,
        fontweight="bold", color="#0A132C")
sw, sh, sgap = 0.148, 0.082, 0.018
sx0, sy_top = 0.020, 0.845
for index, label in enumerate(stages):
    row, col = divmod(index, 6)
    x = sx0 + col * (sw + sgap)
    y = sy_top - row * (sh + 0.030)
    box(x, y, sw, sh, label, C_PROCESS, small_pt)
    if col < 5:
        link(x + sw, y + sh / 2, x + sw + sgap, y + sh / 2)
# the lane from stage 6 down to stage 7
link(sx0 + 5 * (sw + sgap) + sw / 2, sy_top - sh, sx0 + 5 * (sw + sgap) + sw / 2, sy_top - sh - 0.030)
link(sx0 + 5 * (sw + sgap) + sw / 2, sy_top - sh - 0.030, sx0 + sw / 2, sy_top - sh - 0.030)
link(sx0 + sw / 2, sy_top - sh - 0.030, sx0 + sw / 2, sy_top - sh - 0.030 - 0.030)

# Band 2: the optimization loop.
ax.text(0.5, 0.635, "Geometry optimization loop", ha="center", va="top",
        fontsize=19, fontweight="bold", color="#0A132C")
ax.text(0.5, 0.605, "driven by the cost function, gated by the DSMC re-simulation",
        ha="center", va="top", fontsize=15, color="#333333")
lw_, lh, lgap = 0.170, 0.078, 0.022
lx0, ly = 0.020, 0.487
for index, label in enumerate(loop):
    x = lx0 + index * (lw_ + lgap)
    face = C_IN if index == 0 else (C_GA if index == 1 else C_PROCESS)
    if index == 3:
        face = C_CHECK
    box(x, ly, lw_, lh, label, face, small_pt)
    if index < len(loop) - 1:
        link(x + lw_, ly + lh / 2, x + lw_ + lgap, ly + lh / 2)
# reject feedback under the loop
fb_y = 0.432
link(lx0 + lw_, ly, lx0 + lw_, fb_y, C_CHECK, "-")
link(lx0 + lw_, fb_y, lx0, fb_y, C_CHECK, "-")
link(lx0, fb_y, lx0, ly + 0.004, C_CHECK)
ax.text((lx0 + lx0 + lw_) / 2 - lw_ / 2, fb_y, " reject and resample",
        ha="left", va="top", fontsize=small_pt, color=C_CHECK)

# Band 3: how the genetic algorithm works.
ax.text(0.5, 0.393, "Inside the genetic algorithm: one generation",
        ha="center", va="top", fontsize=19, fontweight="bold", color="#0A132C")
gw, gh, ggap = 0.170, 0.078, 0.026
gx0, gy = 0.020, 0.268
for index, label in enumerate(ga_steps):
    x = gx0 + index * (gw + ggap)
    box(x, gy, gw, gh, label, C_GA, small_pt)
    if index < len(ga_steps) - 1:
        link(x + gw, gy + gh / 2, x + gw + ggap, gy + gh / 2)
# the loop back from elitism to the evaluation
back_y = 0.214
link(gx0 + 4 * (gw + ggap) + gw / 2, gy, gx0 + 4 * (gw + ggap) + gw / 2, back_y, C_GA, "-")
link(gx0 + 4 * (gw + ggap) + gw / 2, back_y, gx0 + gw / 2, back_y, C_GA, "-")
link(gx0 + gw / 2, back_y, gx0 + gw / 2, gy + 0.004, C_GA)
ax.text(gx0 + 2 * (gw + ggap), back_y - 0.004, "next generation",
        ha="center", va="top", fontsize=small_pt, color=C_GA)
ax.text(0.985, back_y - 0.004, stop_line, ha="right", va="top",
        fontsize=small_pt, color="#0A132C")

# Band 4: the two passes.
band = FancyBboxPatch(
    (0.012, 0.030), 0.976, 0.125,
    boxstyle="round,pad=0,rounding_size=0.010",
    linewidth=1.4, edgecolor=C_EDGE, facecolor="#EEF3FA", zorder=2,
)
ax.add_patch(band)
ax.text(0.5, 0.138, "Double pass of the same algorithm",
        ha="center", va="top", fontsize=17, fontweight="bold", color="#0A132C")
ax.text(0.5, 0.078, pass_line, ha="center", va="top", fontsize=small_pt,
        color="#0A132C", linespacing=1.3)

fig.savefig(OUT, dpi=200, facecolor="white", bbox_inches="tight")
plt.close(fig)
print("wrote", OUT)
'''


def main() -> int:
    """Draw the picture and install it in the deck folder.

    Returns:
        Zero when the picture was drawn and installed, one otherwise.
    """
    if not THESIS_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the thesis interpreter is missing: {THESIS_PYTHON}\n")
        return 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.is_file():
        _ = BACKUP.parent.mkdir(parents=True, exist_ok=True)
        _ = BACKUP.write_bytes(TARGET.read_bytes())
    out = Path(__file__).resolve().parent / "ga_flowchart_deck.png"
    payload = DRIVER
    if EM_DASH in payload:
        _ = sys.stdout.write("MISMATCH the drawing would carry an em dash\n")
        return 1
    completed = subprocess.run(
        [  # ruff: ignore[subprocess-without-shell-equals-true]
            str(THESIS_PYTHON),
            "-c",
            payload,
            str(out),
            str(WIDTH_IN),
            str(HEIGHT_IN),
            str(LABEL_PT),
            str(SMALL_PT),
            SEP.join(STAGES),
            SEP.join(LOOP),
            SEP.join(GA_STEPS),
            "stop: 200 generations, or no gain of 1e-6 over 20 generations",
            "Pass 1 searches in closed form:  LHS 50  ->  GA  ->  winner x1  ->  "
            "DSMC 2200 steps  ->  c = clamp(q_DSMC / q_SG, 0.5, 2.0)  ->  "
            "Pass 2 runs the same GA with the heat-load term weighted by c  ->  "
            "validate the winner x2",
            "Optimization pipeline: how the genetic algorithm works",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        _ = sys.stdout.write(f"MISMATCH the drawing failed:\n{completed.stderr[-1200:]}\n")
        return 1
    if not out.is_file() or out.stat().st_size < MIN_BYTES:
        _ = sys.stdout.write("MISMATCH the drawing is missing or too small\n")
        return 1
    _ = out.replace(TARGET)
    _ = sys.stdout.write(
        f"wrote {TARGET.name} {TARGET.stat().st_size} bytes\n{completed.stdout.strip()}\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
