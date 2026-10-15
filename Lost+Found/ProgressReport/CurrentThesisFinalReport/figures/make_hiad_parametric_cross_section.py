#!/usr/bin/env python3
"""
MODULE: make_hiad_parametric_cross_section.py — Parametric HIAD cross-section
=============================================================================

Redraws ``hiad_parametric_cross_section.png`` (thesis figure
``fig:hiad_parametric_cross_section``, chapter_02_literature_review.tex) after
the figure-recheck campaign flagged five defects in the shipped drawing.  The
shipped PNG was produced by an ad-hoc script that was never committed, so this
module is a fresh producer built from measurements of the shipped image plus
the parameters published in the thesis caption.  It deliberately keeps the
shipped drawing's visual language (dark panel, orange skin, cyan tori) and
repairs every flagged defect.

AXIOMS
  A1: The cross-section is symmetric about the axis r = 0 except for the
      shoulder torus T7, which the thesis alt-text (chapter_02 ActualText)
      places "at the end of the lower stack".  T7 is therefore drawn on the
      lower stack only, by specification, not by omission.
  A2: All coordinates are millimetres.  The caption publishes D = 3.0 m,
      theta_c = 60.0 deg, N_t = 6 and R_N = 577 mm; these four numbers are
      the only dimensional constants used.
  A3: The shipped image is the visual reference.  Element positions measured
      on it (torus centres, skin path, cone-line slope) are recorded below as
      MEASURED constants with the measurement date, and the drawing is
      reconstructed from those measurements.

THEORIES
  T1: From A3 + the defect list, the spurious "self-intersecting loops" were a
      point-ordering fault in the shoulder polyline (the shipped path zigzags
      between r = 652 mm and r = 939 mm over z = 740..940 mm, crossing its own
      trend).  Rebuilding the skin as ONE z-monotone polyline per side makes
      self-intersection impossible by construction; the script asserts
      monotonicity so the fault cannot silently return.
  T2: The theta_c label sat on the skin in the shipped figure because the
      label band overlapped the shoulder polyline.  Every label position in
      this module is chosen in a measured clear zone (recorded in comments).
  T3: The "D = 3.0 m" dimension arrow spanned r = [-1220, +1220] mm in the
      shipped figure, contradicting its own 3.0 m callout.  The rebuilt arrow
      spans exactly [-1500, +1500] mm and is placed aft of the geometry so it
      crosses no marker (the shipped arrow at z = 1455 mm crossed the T6/T7
      region).

APPLICATIONS
  Produces ``figures/hiad_parametric_cross_section.png`` at the print width
  used by the thesis include (width=0.85\\textwidth), with every text label at
  or above the 8 pt printed floor.

CITATIONS
  [1] Thesis caption + ActualText, chapter_02_literature_review.tex
      (fig:hiad_parametric_cross_section): D = 3.0 m, theta_c = 60 deg,
      N_t = 6, R_N = 577 mm, T1-T6 stacked, T7 shoulder torus on the lower
      stack end, scalloped skin, cone envelope, nose sphere guide.
  [2] MEASURED on the shipped PNG 2026-10-13 (1149x1180 px, axes frame
      x 198.5-950.5 px, y 102.5-1072.5 px): torus centres
      upper (734, 397) (873, 474) (1010, 549) (1148, 623) (1288, 698)
      (1422, 767); lower is the mirror; centre-line fit r = 0.538 z + 3 mm
      through the six centres (apex at the origin); skin row
      r = 0.538 z + 80 mm sampled at z = 996..1534 mm; nose arc
      r = 2.00 z^0.917 mm through (238, 302) (337, 480) (437, 589)
      (537, 670) (637, 745) (736, 905); shoulder defect band z = 740..940 mm.
  [3] Rapisarda (2023) Eqs. 3.4 and 3.3 — the baseline cited by the thesis
      figure chain (same source credit as hiad_design_sensitivity.png).
  [4] matplotlib 3.x — https://matplotlib.org/stable/api/

Author: Albert Starfield Wahyu Suryo Samudro
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")  # headless render; no display in CI or build shells

import matplotlib.pyplot as plt  # noqa: E402  (after backend selection)

FIGDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(FIGDIR))
import print_fit as pf  # noqa: E402  (shared fit-to-print-width helper)

# Print width of the thesis include, width=0.85\textwidth in
# chapter_02_literature_review.tex.  TEXT_W_IN is the same thesis text width
# the sibling sensitivity producers use.
TEXT_W_IN = 5.8019
PRINT_W_IN = 0.85 * TEXT_W_IN

# --- caption constants (A2) -------------------------------------------------
D_M = 3.0                 # overall diameter [m] (caption)
HALF_D_MM = D_M / 2.0 * 1000.0   # +/-1500 mm (T3)
THETA_C_DEG = 60.0        # half-cone angle [deg] (caption)
N_T = 6                   # toroid count (caption)
R_N_MM = 577.0            # nose sphere radius [mm] (caption)

# --- MEASURED reconstruction constants (A3, [2]) ----------------------------
# Torus centres (z, r) [mm]; upper stack, from the shipped PNG measurement.
TORI_UPPER_MM = [
    (734.0, 397.0),
    (873.0, 474.0),
    (1010.0, 549.0),
    (1148.0, 623.0),
    (1288.0, 698.0),
    (1422.0, 767.0),
]
TUBE_R_MM = 60.0          # drawn torus-tube radius [mm] (measured disc size)
ROW_SLOPE = 0.538         # d r / d z of the stack centre line [1]
ROW_OFFSET_MM = 80.0      # skin sits this far outside the centre line [mm]
NOSE_A = 2.00             # nose arc r = A * z^B [mm], measured fit
NOSE_B = 0.917
NOSE_END_Z = 740.0        # nose arc meets the shoulder here [mm]
NOSE_END_R = 905.0        # ... at this radius [mm] (measured)
SHOULDER_CTRL = (800.0, 620.0)   # quadratic Bezier control, measured smooth path
ROW_START_Z = 990.0       # shoulder ease lands on the row line here [mm]
ROW_END_Z = 1540.0        # row runs to here [mm] (measured end)
AFT_TIP_Z = 1645.0        # aft-outward skin tip [mm] (measured)
AFT_TIP_R = 1046.0
T7_Z, T7_R = 1560.0, -817.0   # shoulder torus: tangent continuation of the
                              # lower stack (pitch 151 mm from T6 lower at
                              # (1426, -748)), per alt-text "end of the lower
                              # stack" [1]
XLIM = (0.0, 2050.0)      # trimmed: shipped xlim 2500 left ~35 % empty
YLIM = (-1500.0, 1500.0)

# --- presentation (matches the shipped panel) -------------------------------
BG = "#001020"            # measured background
INK = "#F2F5F9"           # measured near-white text
SKIN = "#F09000"          # measured skin orange
TORUS_FILL = "#40C0F0"    # measured torus fill
TORUS_EDGE = "#40A0D0"
T7_FILL = "#A78BFA"       # shoulder torus purple
T7_EDGE = "#8B5CF6"
T7_INK = "#F5F3FF"        # bright lavender: fixes the low-contrast label
GUIDE = "#34D399"         # nose sphere guide green
CONE = "#94A3B8"          # cone envelope gray
FS_TITLE = 10.0
FS_SUB = 10.0
FS_LABEL = 10.5
FS_TICK = 9.0
FS_ANNOT = 9.5
MIN_DECLARED_PT = 9.0     # every text size is >= this (8 pt printed floor)


def skin_polyline(sign: float) -> tuple[np.ndarray, np.ndarray]:
    """Build one side of the aeroshell skin as a z-monotone polyline.

    The shipped figure's shoulder was a zigzag between r = 652 and r = 939 mm
    over z = 740..940 mm (the "self-intersecting loops").  This builder emits
    a strictly z-increasing polyline, so a vertical line can cross the skin at
    most once and self-intersection is impossible by construction (T1).

    Parameters
    ----------
    sign : float
        +1.0 for the upper stack, -1.0 for the lower stack.

    Returns
    -------
    (z, r) : tuple of ndarray
        Polyline coordinates in millimetres, both length 60.

    Raises
    ------
    ValueError
        If sign is not +1.0 or -1.0.
    """
    if sign not in (1.0, -1.0):
        raise ValueError(f"sign must be +1.0 or -1.0, got {sign}")
    z: list[float] = []
    r: list[float] = []
    # nose arc: r = A z^B, sampled 0..NOSE_END_Z (measured fit [2])
    for zz in np.linspace(0.0, NOSE_END_Z, 40)[:-1]:
        z.append(float(zz))
        r.append(sign * NOSE_A * (max(zz, 1e-9) ** NOSE_B))
    # shoulder ease: quadratic Bezier from the arc end with a measured control
    # point, landing on the row line at ROW_START_Z
    p0 = (NOSE_END_Z, sign * NOSE_END_R)
    p2 = (ROW_START_Z, sign * (ROW_SLOPE * ROW_START_Z + ROW_OFFSET_MM))
    p1 = (SHOULDER_CTRL[0], sign * SHOULDER_CTRL[1])  # z control is not mirrored
    for t in np.linspace(0.06, 1.0, 20)[:-1]:
        bx = (1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * p1[0] + t ** 2 * p2[0]
        by = (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * p1[1] + t ** 2 * p2[1]
        z.append(float(bx))
        r.append(float(by))
    # straight row to the measured aft end, then the short aft-outward tip
    for zz in np.linspace(ROW_START_Z, ROW_END_Z, 12)[1:]:
        z.append(float(zz))
        r.append(sign * (ROW_SLOPE * zz + ROW_OFFSET_MM))
    z.append(AFT_TIP_Z)
    r.append(sign * AFT_TIP_R)
    za = np.asarray(z)
    ra = np.asarray(r)
    # T1 guard: z must be strictly increasing, otherwise the shipped ordering
    # fault could creep back in; fail loudly instead of drawing a knot.
    if not np.all(np.diff(za) > 0):
        raise ValueError("skin polyline is not z-monotone; ordering fault")
    return za, ra


def draw() -> plt.Figure:
    """Build the cross-section figure.

    Returns
    -------
    matplotlib.figure.Figure
        The fully drawn figure (not yet saved).
    """
    # Native figsize is the thesis print width minus print_fit's tight-bbox
    # pad (0.1 in): with every artist inside the canvas the tight crop equals
    # canvas + pad, so the layout lands on the target.
    fig = plt.figure(figsize=(4.83, 2.72), facecolor=BG)
    ax = fig.add_axes((0.145, 0.145, 0.835, 0.72))
    ax.set_facecolor(BG)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    # explicit ticks: the auto locator emits a 2250 mm label past the trimmed
    # xlim, and an out-of-view Text still breaks the fit loop
    ax.set_xticks([0, 500, 1000, 1500, 2000])
    ax.set_yticks([-1500, -1000, -500, 0, 500, 1000, 1500])

    # faint grid + spines, matching the shipped panel tone
    ax.grid(True, color="#FFFFFF", alpha=0.07, linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#4A5568")
    ax.tick_params(colors=INK, labelsize=FS_TICK, length=3)
    ax.set_xlabel("Axial Distance z [mm]", color=INK, fontsize=FS_LABEL)
    ax.set_ylabel("Radial Distance r [mm]", color=INK, fontsize=FS_LABEL)

    # cone envelope: the measured stack centre line through the origin
    # (slope 0.538), drawn to just past the aft tip on both sides
    z_cone = np.linspace(0.0, 1800.0, 40)
    ax.plot(z_cone, ROW_SLOPE * z_cone, color=CONE, lw=1.0, ls=(0, (2, 3)),
            zorder=1, label="Cone Envelope")
    ax.plot(z_cone, -ROW_SLOPE * z_cone, color=CONE, lw=1.0, ls=(0, (2, 3)),
            zorder=1)

    # nose sphere guide: the published R_N circle centred at (R_N, 0)
    theta = np.linspace(0.0, np.pi, 60)
    ax.plot(R_N_MM + R_N_MM * np.cos(theta), R_N_MM * np.sin(theta),
            color=GUIDE, lw=1.1, ls=(0, (1, 2.5)), zorder=1,
            label="Nose Sphere Guide")

    # scalloped skin: one ordered polyline per side (T1)
    for sign in (1.0, -1.0):
        za, ra = skin_polyline(sign)
        ax.plot(za, ra, color=SKIN, lw=2.6, solid_joinstyle="round",
                zorder=4, label="Scalloped Skin" if sign > 0 else None)

    # toroidal bladders T1..T6, symmetric stacks (A1: T7 lower only)
    for i, (zc, rc) in enumerate(TORI_UPPER_MM, start=1):
        for sgn in (1.0, -1.0):
            ax.add_patch(plt.Circle((zc, sgn * rc), TUBE_R_MM,
                                    facecolor=TORUS_FILL,
                                    edgecolor=TORUS_EDGE, lw=1.2, zorder=5))
            ax.text(zc, sgn * rc, f"T{i}", ha="center", va="center",
                    fontsize=FS_ANNOT, fontweight="bold", color="#06283D",
                    zorder=6)
    # shoulder torus T7 at the end of the lower stack (alt-text [1]);
    # bright label ink fixes the shipped low-contrast purple text
    ax.add_patch(plt.Circle((T7_Z, T7_R), TUBE_R_MM, facecolor=T7_FILL,
                            edgecolor=T7_EDGE, lw=1.2, zorder=5))
    ax.text(T7_Z, T7_R, "T7", ha="center", va="center", fontsize=FS_ANNOT,
            fontweight="bold", color=T7_INK, zorder=6)
    # caption below the disc keeps the shoulder torus self-describing without
    # a legend entry (the shipped legend carried three entries only).  It sits
    # clear of the aft skin tip, whose lowest point is r = -1046 mm.
    ax.text(T7_Z, -1120.0, "Shoulder Torus T7", ha="center",
            va="top", fontsize=FS_TICK, color=T7_INK, zorder=6)

    # theta_c annotation: measured clear zone between the axis and the torus
    # row (the shipped label band crossed the skin; see T2).  The zone
    # z ~ 1150-1350, r ~ 250-350 mm is below the T4/T5 discs, above the axis
    # and well below the skin row.
    ax.text(1160.0, 300.0, r"$\theta_c$ = 60.0$^\circ$", color=INK,
            fontsize=FS_ANNOT, fontweight="bold", ha="left", va="center",
            zorder=6)

    # D dimension: exactly +/-1500 mm (T3), placed aft of every marker so it
    # crosses nothing (the shipped arrow at z = 1455 mm cut through the T6/T7
    # region and spanned only +/-1220 mm).  Label sits left of the arrow line
    # so it stays inside the canvas.
    d_z = 1750.0
    ax.annotate("", xy=(d_z, HALF_D_MM), xytext=(d_z, -HALF_D_MM),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.3,
                                shrinkA=0, shrinkB=0), zorder=6)
    ax.text(d_z - 25.0, 60.0, "D = 3.0 m", color=INK, fontsize=FS_ANNOT,
            fontweight="bold", ha="right", va="center", zorder=6)

    # R_N callout in the measured clear zone above the aft stack
    ax.text(1150.0, 1150.0, r"$R_N$ = 577 mm", color=INK, fontsize=FS_ANNOT,
            fontweight="bold", ha="left", va="center", zorder=6)

    # legend: upper-left clear zone (the shipped legend sat in the right band
    # that the xlim trim now removes)
    leg = ax.legend(loc="upper left", fontsize=FS_TICK, framealpha=0.25,
                    facecolor=BG, edgecolor="#4A5568", labelcolor=INK,
                    borderpad=0.6, handlelength=2.2)
    leg.set_zorder(7)

    # Title/subtitle are figure-centred, not axes-centred: the axes centre
    # sits right of the figure centre because of the y-label margin, and an
    # axes-centred 13 pt title overhangs the canvas and stalls the fit loop.
    fig.text(0.5, 0.925, "Parametric HIAD Cross-Section "
             "(Rapisarda MDAO Baseline)", ha="center", va="center",
             color=INK, fontsize=FS_TITLE, fontweight="bold")
    fig.text(0.5, 0.878,
             "D = 3.0 m, $N_t$ = 6, $\\theta_c$ = 60.0$^\\circ$",
             ha="center", va="center", color=INK, fontsize=FS_SUB)
    return fig


def main() -> int:
    """Render, floor-check and atomically write the figure.

    Returns
    -------
    int
        Process exit status: 0 on success, 1 on any verification failure.

    Raises
    ------
    SystemExit
        Never directly; the caller sees the return code.
    """
    fig = draw()
    # printed floor: declared sizes must clear 8 pt at the worst fit tolerance
    worst = MIN_DECLARED_PT * (1.0 - pf.FIT_TOL)
    if worst < 8.0:
        raise RuntimeError(
            f"declared floor {worst:.2f} pt below the 8.0 pt print floor"
        )
    path, scale = pf.save_to_print_width(
        fig, "hiad_parametric_cross_section.png", PRINT_W_IN
    )
    if MIN_DECLARED_PT * scale < 8.0:
        raise RuntimeError(
            f"text would print at {MIN_DECLARED_PT * scale:.2f} pt, below 8.0"
        )
    print(f"wrote {path} (scale {scale:.3f}, "
          f"min text {MIN_DECLARED_PT * scale:.2f} pt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
