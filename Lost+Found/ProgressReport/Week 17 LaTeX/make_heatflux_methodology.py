#!/usr/bin/env python3
"""
Generate the heat-flux METHODOLOGY flowchart for the Week 16 progress deck.

AXIOMS (what is assumed true; every box cites the file it was read from):
  A1  Derived from code, not prose. Each box carries its source file:line so
      the slide cannot drift from `_proc`.
  A2  Two halves that are not interchangeable: SIMULATING (SPARTA DSMC solves
      the Boltzmann equation) and COUNTING (the accounting layer that bounds
      the solver's noisy internal quantity).
  A3  They meet at exactly one expression, Ada's SG_Scaled_Element_Flux:
      q_i = Q_SG * clamp(ke_i / Ke_Ref, 0, 1). DSMC supplies SHAPE, Sutton-
      Graves supplies SCALE.
  A4  Light themed: the deck palette is warm/muted and a dark figure clashes
      (the earlier #0a0a0f defect, already fixed).
  A5  LAYOUT: text must FIT INSIDE its box. Previous render overflowed every
      box, so this version keeps each body to <= 3 short lines at a small
      font, and main() ASSERTS on overflow before writing.

THEORY:  [DSMC] -> noisy per-element ke_i -> Ke_Ref = max(ke_raw)
         -> q_i = Q_SG*clamp(ke_i/Ke_Ref,0,1) -> integrate -> heat load.

APPLICATIONS: stellarorion_sparta.adb, stellarorion_physics.adb,
              scripts/run_tps_conduction_step2200.py

EXPECTED OUTPUT: figures/heatflux_methodology.png, light, no text crossing
its box.
RAISES: RuntimeError if the output dir is missing or a box overflows.

CITATIONS:
  [Citation: SPARTA surface compute - https://www.lammps.org/sparta/surf.html]
  [Citation: Bird 1994, Molecular Gas Dynamics, Sec 7 - DSMC statistical noise]
  [Citation: Sutton & Graves 1971, NASA TR R-376 - https://ntrs.nasa.gov/citations/19720003329]
  [Citation: Fay & Riddell 1958 - stagnation-point heat transfer]
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
from matplotlib import pyplot as plt

BAND = "#2F6B69"
INK = "#2F4F4D"
CREAM = "#F5EFE0"
MIST = "#E8EEE9"
SAND = "#EDE4CE"
ACC = "#5E918C"
BODY = "#33302B"

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "figures")
OUTPATH = os.path.join(OUTDIR, "heatflux_methodology.png")

# Body copy kept deliberately short: each entry must render inside its box.
# (title, [line, line, ...], face, edge, height)
BOXES = [
    # ── column 0: SIMULATING ──
    (0, 0, "SPARTA DSMC solver",
     ["Direct simulation of the", "Boltzmann equation", "(stellarorion_physics.ads:236)"],
     "white", BAND, 0.150),
    (0, 1, "Per-element energy flux",
     ["compute surf nflux mflux ke,", "then fix ave/surf (3648", "elements, sparta.adb:724)"],
     "white", BAND, 0.150),
    (0, 2, "Raw ke_i is a SHAPE ONLY",
     ["Negative excursions reach", "-10,570 W/m2 at step 2200.", "(stellarorion_physics.adb:2634)"],
     SAND, BAND, 0.150),
    # ── column 1: COUNTING ──
    (1, 0, "Ke_Ref = max(Ke_Raw)",
     ["Axiom A4: Ke_Ref > 0, else", "every flux is 0.", "(run_tps_conduction:402)"],
     "white", BAND, 0.150),
    (1, 1, "Ada: SG_Scaled_Element_Flux",
     ["q_i = Q_SG * clamp(ke_i/Ke_Ref, 0, 1)", "Result lies in [0, Q_SG];",
      "Q1 q>=0, Q2 q<=Q_SG, Q3 -> 0."],
     MIST, BAND, 0.170),
    (1, 2, "Scale: Sutton-Graves",
     ["Q_SG = C_SG*sqrt(rho/R_N)*V^3", "C_SG = 1.7415e-4 (TR R-376);", "types.ads:61, +6.26% vs flight."],
     SAND, BAND, 0.150),
]


def draw_box(ax, col, row, title, lines, fc, ec, h):
    """Draw one process box in a two-column, three-row grid.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    col : int  0 = SIMULATING column, 1 = COUNTING column
    row : int  0 (top) .. 2 (bottom)
    title : str  bold heading
    lines : list[str]  body lines, already short
    fc, ec : str  face and edge colour
    h : float  box height in axis units

    Returns
    -------
    tuple
        (x, y, w, h) rectangle of the drawn box, in axis coordinates.

    Raises
    ------
    RuntimeError
        If a body line is longer than the box can hold at the body font
        size (measured from the drawn text artist).
    """
    x = 0.030 if col == 0 else 0.535
    w = 0.435
    y = 0.700 - row * 0.185 - h + 0.150
    y = 0.640 - row * 0.190 - (h - 0.150)

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.005,rounding_size=0.010",
            linewidth=1.1, edgecolor=ec, facecolor=fc, zorder=2,
        )
    )
    ax.text(x + 0.012, y + h - 0.020, title, ha="left", va="top",
            fontsize=8.6, fontweight="bold", color=INK, zorder=3)
    t = ax.text(x + 0.012, y + h - 0.052, "\n".join(lines), ha="left",
                va="top", fontsize=7.0, color=BODY, linespacing=1.30, zorder=3)

    # ── overflow guard (AXIOM A5): measure the drawn artist, not the estimate ──
    bbox = t.get_window_extent(renderer=ax.figure.canvas.get_renderer())
    ax_bbox = ax.get_window_extent(renderer=ax.figure.canvas.get_renderer())
    ax_h_px = (y + h) - y
    box_bottom_px = y * ax_bbox.height
    box_top_px = (y + h) * ax_bbox.height
    if bbox.height <= 0:
        raise RuntimeError("text artist has zero height for %r" % title)
    text_top_px = bbox.y1
    text_bot_px = bbox.y0
    # Convert the box rectangle to figure pixel space using the axes bbox.
    if text_bot_px < ax_bbox.y0 + box_bottom_px + 2 or text_top_px > ax_bbox.y0 + box_top_px - 2:
        raise RuntimeError(
            "box overflow: %r text y=[%.0f,%.0f] outside box y=[%.0f,%.0f]"
            % (title, text_bot_px, text_top_px,
               ax_bbox.y0 + box_bottom_px, ax_bbox.y0 + box_top_px)
        )
    # Horizontal guard: text must not cross the right edge.
    if bbox.x1 > ax_bbox.x0 + (x + w) * ax_bbox.width - 4:
        raise RuntimeError(
            "box overflow right: %r text x1=%.0f > box x1=%.0f"
            % (title, bbox.x1, ax_bbox.x0 + (x + w) * ax_bbox.width)
        )
    ax_h_px = ax_h_px  # kept for clarity; vertical checks above are authoritative
    return (x, y, w, h)


def main():
    """Render the figure and verify no box overflows.

    Returns
    -------
    int
        0 on success.

    Raises
    ------
    RuntimeError
        If the output directory is missing or any box overflows.
    """
    if not os.path.isdir(OUTDIR):
        raise RuntimeError("output directory does not exist: %s" % OUTDIR)

    fig, ax = plt.subplots(figsize=(12.0, 6.75), dpi=200)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    fig.canvas.draw()  # build the renderer before any get_window_extent

    # Header band
    ax.add_patch(mpatches.Rectangle((0, 0.930), 1, 0.070, facecolor=BAND,
                                    edgecolor="none", zorder=1))
    ax.text(0.014, 0.965, "WHAT HEAT FLUX IS: CONVECTION + CONDUCTION + RERADIATION",
            ha="left", va="center", fontsize=13.0, fontweight="bold",
            color="white", zorder=3)
    ax.text(0.986, 0.965, "StellarOrion _proc", ha="right", va="center",
            fontsize=8.4, color=CREAM, zorder=3)

    # Column headers
    for cx, label, fc in (
        (0.2525, "1  SIMULATING   (DSMC physics)", SAND),
        (0.7525, "2  COUNTING   (accounting)", MIST),
    ):
        ax.add_patch(mpatches.Rectangle((cx - 0.2175, 0.845), 0.435, 0.050,
                                        facecolor=fc, edgecolor=ACC, lw=1.0, zorder=1))
        ax.text(cx, 0.870, label, ha="center", va="center", fontsize=9.6,
                fontweight="bold", color=INK, zorder=3)

    rects = {}
    for col, row, title, lines, fc, ec, h in BOXES:
        rects[(col, row)] = draw_box(ax, col, row, title, lines, fc, ec, h)

    # Vertical arrows within each column.
    for col in (0, 1):
        for row in (0, 1):
            x0, y0, w0, h0 = rects[(col, row)]
            x1, y1, w1, h1 = rects[(col, row + 1)]
            ax.annotate("", xy=(x1 + w1 / 2, y1 + h1 + 0.004),
                        xytext=(x0 + w0 / 2, y0 - 0.004),
                        arrowprops=dict(arrowstyle="-|>", color=BAND, lw=1.6,
                                        mutation_scale=13, shrinkA=0, shrinkB=0),
                        zorder=4)

    # ke_i: column 1 top -> column 2 top (the handoff).
    xa, ya, wa, ha = rects[(0, 0)]
    xb, yb, wb, hb = rects[(1, 0)]
    ax.annotate("", xy=(xb, yb + hb * 0.55), xytext=(xa + wa, ya + ha * 0.55),
                arrowprops=dict(arrowstyle="-|>", color=BAND, lw=2.0,
                                mutation_scale=15, shrinkA=0, shrinkB=0), zorder=4)
    ax.text((xa + wa + xb) / 2, ya + ha * 0.55 + 0.012, r"$ke_i$",
            ha="center", va="bottom", fontsize=8.4, fontweight="bold",
            color=BAND, zorder=5)

    # Bottom row of outputs.
    bottoms = [
        (0.030, 0.335, "Cross-check: Fay-Riddell",
         ["Stagnation-point theory,", "-3.69 % vs IRVE-3 flight:", "accurate, not conservative."],
         "white", ACC),
        (0.375, 0.330, "Integrate over trajectory",
         ["Q = integral(q dt),", "trapezoidal rule.", "(postprocessing.ads:363)"],
         "white", ACC),
        # Repurposed from "Delivered outputs". The terminal box is where the
        # reader expects to be told what the number IS, so it carries the
        # F84 surface energy balance -- the three terms this frame names.
        # Basis (corrected 2026-10-19): eps = 0.80 stack-level (Ada
        # TPS_Layup_IRVE3) and R_total = 0.305583 m^2*K/W, the sum of t/k over
        # the 7.131 mm 5-ply schedule. The earlier 261626.5 + 4882.8 /
        # T_s 1550.23 used the superseded 6.35 mm flown IRVE-3 stack's
        # R = 0.25605 (stellarorion_types.ads:760: 0.257250 -> 0.305583, +18.8%).
        # Decimal places are deliberate: integers do not add up on screen
        # (262416 + 4093 = 266509 is fine, but 261627 + 4883 = 266510 vs a true
        # 266509), one decimal does.
        # Body is capped at 3 lines because AXIOM A5's overflow guard refuses
        # a 4th: measured raise at h=0.145, "bottom box overflow".
        (0.725, 0.275, "Surface energy balance (F84)",
         ["q_conv = q_rad + q_cond",
          "266509.3 = 262415.9 + 4093.4 W/m2",
          "residual 0.0000 %, T_s 1550.86 K."],
         MIST, BAND),
    ]
    for x, w, title, lines, fc, ec in bottoms:
        y, h = 0.030, 0.145
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.005,rounding_size=0.010",
            linewidth=1.1, edgecolor=ec, facecolor=fc, zorder=2))
        ax.text(x + 0.010, y + h - 0.020, title, ha="left", va="top",
                fontsize=8.4, fontweight="bold", color=INK, zorder=3)
        t = ax.text(x + 0.010, y + h - 0.052, "\n".join(lines), ha="left",
                    va="top", fontsize=7.0, color=BODY, linespacing=1.30, zorder=3)
        bbox = t.get_window_extent(renderer=ax.figure.canvas.get_renderer())
        if bbox.y0 < ax.get_window_extent(
                renderer=ax.figure.canvas.get_renderer()).y0 + y * ax.get_window_extent(
                renderer=ax.figure.canvas.get_renderer()).height + 2:
            raise RuntimeError("bottom box overflow: %r" % title)
        if bbox.x1 > ax.get_window_extent(
                renderer=ax.figure.canvas.get_renderer()).x0 + (x + w) * ax.get_window_extent(
                renderer=ax.figure.canvas.get_renderer()).width - 4:
            raise RuntimeError("bottom box right overflow: %r" % title)

    # Arrows into the bottom row.
    x1, y1, w1, h1 = rects[(1, 2)]
    ax.annotate("", xy=(0.860, 0.179), xytext=(x1 + w1 / 2, y1 - 0.004),
                arrowprops=dict(arrowstyle="-|>", color=BAND, lw=1.6,
                                mutation_scale=13, shrinkA=0, shrinkB=0), zorder=4)
    ax.annotate("", xy=(0.725, 0.103), xytext=(0.708, 0.103),
                arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.6,
                                mutation_scale=13, shrinkA=0, shrinkB=0), zorder=4)
    ax.annotate("", xy=(0.375, 0.103), xytext=(0.368, 0.103),
                arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.6,
                                mutation_scale=13, shrinkA=0, shrinkB=0), zorder=4)
    # NOTE: a q_i arrow was drawn from the equation box into the bottom row.
    # It used connectionstyle="angle" and the resulting polyline cut straight
    # through the equation box's own body text. Removed on purpose: the
    # vertical column arrows already carry the flow, so the extra path was
    # decoration that cost legibility. Do not re-add a routed polyline here
    # without re-running the visual read-back.
    # y = -0.006, NOT +0.010: at +0.010 the footer landed 1 px below the
    # bottom-box border (measured: border rows 1031-1033, text rows 1034-1047),
    # which reads as a strike-through across the footer. bbox_inches="tight"
    # expands the canvas for text outside the axes, so a negative y is safe.
    ax.text(0.014, -0.006,
            "Every box cites the source it was read from. Sutton & Graves, "
            "NASA TR R-376 (1971); Bird (1994) Sec 7; balance: "
            "FAILURES_AND_FIXES.md F84.",
            ha="left", va="bottom", fontsize=6.6, color="#5A5A5A", zorder=3)

    fig.savefig(OUTPATH, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[heatflux_methodology] wrote %s" % OUTPATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
