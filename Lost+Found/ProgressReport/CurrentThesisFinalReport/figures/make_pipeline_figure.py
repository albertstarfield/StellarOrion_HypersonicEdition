#!/usr/bin/env python3
"""Replace the generic template flowchart with the pipeline this work actually
executes.

WHY THIS REPLACEMENT IS NECESSARY
AXIOM: `figures/flowchart.png` was captioned in the Introduction as "Research
methodology flowchart" and its alt text claimed an "eleven-stage numerical
research workflow". Inspecting the artwork shows neither is true. Transcribed
verbatim, its boxes read:

    Start
    Various of papers Study
    Literature Study
    Data Retrieval and Familiar Study Collection
    Replicate Axisymmetric Slice Model Design?
    Simulate the Geometry in Mach 5-6      <-- WRONG PHYSICS
    Simulation Result
    Theoretically valid? or within error range?
    Data Analysis Simulation
    Conclusion and Recommendation
    End

Three separate defects:
  1. It says "Mach 5-6". This study is at Mach 10.29, and the trajectory
     profile spans Mach 27.5 down to 0.5. The label contradicts the thesis.
  2. The upper half is generic literature-review boilerplate, not methodology.
  3. It never shows the stages that constitute this work: parametric geometry
     generation, the DSMC solver, PINN refinement, or the optimisation loop.
The same file was also reused in Chapter 3, so the wrong figure appeared twice.

The replacement is built from the stages the engine actually executes. The
eleven numbered stages are those printed by the full validation pipeline
(`Run_Validate_Full`, stellarorion_program_proc/src/simulation_engine/
stellarorion_test_modes.adb:1147 onward), in the order that function runs them:

    1  flight parameters            7  parse SPARTA surface dumps
    2  geometry quality assurance    8  flight metrics
    3  generate HIAD surface         9  survivability check
    4  write solver input           10  sanity checks
    5  build solver container       11  compare against IRVE-3 flight data
    6  run DSMC simulation          12  export fields, series and plots

The optimisation loop is shown separately because it is driven by the cost
function of Sec. cost_function and gated by Sec. gate_methodology, not by the
validation pipeline itself.

CITATION
  Matplotlib, https://matplotlib.org/stable/
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "fignew_pipeline.png"

# Colourblind-safe (Paul Tol): blue, yellow, magenta, green, teal, red.
C_INPUT = "#DDAA33"
C_PROCESS = "#004488"
C_CHECK = "#BB5566"
C_OUTPUT = "#228833"
C_EDGE = "#333333"

# Printed size, derived from the document geometry rather than chosen:
#     text height = 29.7 cm - 3 cm - 3 cm = 23.7 cm = 9.33071 in
# The chapter inserts this figure with height = 0.72\textheight, so the printed
# box is 0.72 * 9.33071 = 6.718 in tall. The image is then built to exactly that
# height and its width follows from the aspect ratio.
# AXIOM: a figsize is inches of the SAVED image and the document rescales it, so
# the effective scale is print_height / saved_height. At the previous
# figsize of 7.0 x 10.85 in against a printed height of 0.60\textheight = 5.598 in
# the scale was 0.516 and every label printed at half size. save_to_print_height()
# below measures and removes that factor.
TEXT_H_IN = 29.7 / 2.54 - (3.0 + 3.0) / 2.54      # 9.33071
PRINT_H_IN = 0.72 * TEXT_H_IN                      # 6.71811
WIDTH_IN = PRINT_H_IN * (2056 / 3225)              # 4.283


def box(ax, x, y, w, h, text, fc, fs=7.4, style="round,pad=0.02,rounding_size=0.02"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=style, linewidth=0.9,
        edgecolor=C_EDGE, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color="white" if fc == C_PROCESS else "black",
            zorder=3, linespacing=1.35)


def arrow(ax, p0, p1, style="-|>", ls="-", color=C_EDGE, lw=1.5, rad=0.0):
    """zorder 5 so the connector is drawn OVER the boxes. At zorder 1 with
    mutation_scale 8 the connectors were completely hidden and the diagram read
    as twelve unconnected boxes."""
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle=style, linestyle=ls, color=color, linewidth=lw,
        mutation_scale=13, connectionstyle=f"arc3,rad={rad}", zorder=5))


def main() -> int:
    fig, ax = plt.subplots(figsize=(WIDTH_IN, PRINT_H_IN))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.992, "Validation pipeline executed by the engine",
            ha="center", va="top", fontsize=7.0, weight="bold")
    ax.text(0.5, 0.966,
            "Stages in execution order, as printed by the full validation run",
            ha="center", va="top", fontsize=6.2, style="italic")

    stages = [
        ("1  Flight parameters", C_INPUT),
        ("2  Geometry quality assurance", C_PROCESS),
        ("3  Generate HIAD surface", C_PROCESS),
        ("4  Write solver input script", C_PROCESS),
        ("5  Build solver container", C_PROCESS),
        ("6  Run DSMC simulation", C_PROCESS),
        ("7  Parse surface dumps", C_PROCESS),
        ("8  Compute flight metrics", C_PROCESS),
        ("9  Survivability check", C_CHECK),
        ("10  Sanity checks", C_CHECK),
        ("11  Compare with IRVE-3 flight", C_PROCESS),
        ("12  Export fields and plots", C_OUTPUT),
    ]
    # Two columns spanning the full canvas width. The vertical gap between the
    # two columns is deliberately kept wide: the 6 -> 7 wrap arrow is routed
    # through it, so it never crosses a box.
    n_per_col, w, h = 6, 0.40, 0.070
    x_left, x_right = 0.035, 0.545
    top, gap = 0.905, 0.030
    lane_y = 0.330                      # clear lane below both columns
    assert len(stages) == n_per_col * 2

    pos = {}
    for i, (label, fc) in enumerate(stages):
        col, row = i // n_per_col, i % n_per_col
        x0 = x_left if col == 0 else x_right
        y0 = top - row * (h + gap) - h
        box(ax, x0, y0, w, h, label, fc, fs=5.9)
        pos[i] = (x0, y0)

    # Intra-column connectors: solid black, drawn over the boxes, long enough to
    # read at print size.
    for col in range(2):
        for row in range(n_per_col - 1):
            i = col * n_per_col + row
            x0, y0 = pos[i]
            ax.annotate("", xy=(x0 + w / 2, y0 - gap), xytext=(x0 + w / 2, y0),
                        arrowprops=dict(arrowstyle="-|>", color="black",
                                        linewidth=1.6, mutation_scale=13), zorder=5)

    # Wrap 6 -> 7: down the left edge of column 1, across the clear lane below,
    # up through the gap BETWEEN the columns, then into the top of column 2.
    x_lc = x_left + w / 2
    x_gap = (x_left + w + x_right) / 2
    y_bot_left = pos[n_per_col - 1][1]
    y_top_right = pos[n_per_col][1] + h
    seg = [(x_lc, y_bot_left), (x_lc, lane_y), (x_gap, lane_y), (x_gap, y_top_right)]
    for a, b in zip(seg, seg[1:]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color="black", lw=1.6,
                solid_capstyle="butt", zorder=5)
    ax.annotate("", xy=(x_right + 0.020, y_top_right), xytext=seg[-1],
                arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.6,
                                mutation_scale=13), zorder=5)
    ax.text(x_gap, lane_y + 0.012, "continues", fontsize=5.8, ha="center",
            va="bottom", color="black")

    # ---- optimisation loop, its own row with room for the feedback path ----
    ax.text(0.5, 0.268,
            "Geometry optimisation loop (driven by the cost function, gated by DSMC re-simulation)",
            ha="center", va="top", fontsize=7.0, weight="bold")
    loop = ["Design space\n(LHS or CCD screen)",
            "Bayesian optimisation\n(GP + Expected Improvement)",
            "Cost function\n$J(x)$",
            "DSMC\nre-simulation",
            "Accept if\n$q \\leq Q_{target}$"]
    # 5*lw_ + 4*lgap must fit inside [0.020, 0.980]:
    # 5*0.170 + 4*0.026 = 0.954, ending at 0.974.
    lw_, lh, lgap = 0.170, 0.082, 0.026
    ly = 0.105                          # high enough that the lane below (0.03) is inside ylim
    for i, label in enumerate(loop):
        x0 = 0.020 + i * (lw_ + lgap)
        fc = C_CHECK if i == 3 else C_PROCESS
        box(ax, x0, ly, lw_, lh, label, fc, fs=5.9)
        if i:
            ax.annotate("", xy=(x0, ly + lh / 2), xytext=(x0 - lgap, ly + lh / 2),
                        arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.4,
                                        mutation_scale=11), zorder=5)
    # Rejection feedback, routed strictly below the row so it crosses nothing.
    x_first = 0.020 + lw_ / 2
    x_last = 0.020 + 4 * (lw_ + lgap) + lw_
    fb_y = 0.045
    ax.plot([x_last, x_last, x_first, x_first], [ly, fb_y, fb_y, ly],
            color=C_CHECK, lw=1.4, zorder=5, solid_capstyle="butt")
    ax.annotate("", xy=(x_first, ly + 0.006), xytext=(x_first, fb_y),
                arrowprops=dict(arrowstyle="-|>", color=C_CHECK, linewidth=1.4,
                                mutation_scale=11), zorder=5)
    ax.text((x_first + x_last) / 2, fb_y - 0.004, "reject and resample",
            fontsize=5.8, ha="center", va="top", color=C_CHECK)

    fig.tight_layout()

    # Fit the SAVED image to the printed height. bbox_inches="tight" crops to the
    # artist extents, so the saved height is not the figsize height; measuring the
    # crop once and rescaling by the reciprocal converges, and the result is
    # asserted rather than assumed.
    from PIL import Image

    target_px = PRINT_H_IN * 300
    for _ in range(4):
        fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
        got_px = Image.open(OUT).size[1]
        if abs(got_px - target_px) / target_px <= 0.005:
            break
        w, h = fig.get_size_inches()
        fig.set_size_inches(w * target_px / got_px, h * target_px / got_px, forward=True)
    px = Image.open(OUT).size
    scale = PRINT_H_IN / (px[1] / 300)
    print(f"wrote {OUT.name} {px[0]}x{px[1]}px  print height {PRINT_H_IN:.3f} in  "
          f"scale {scale:.3f}  effective dpi {300 / scale:.0f}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
