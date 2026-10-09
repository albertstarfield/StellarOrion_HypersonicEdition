#!/usr/bin/env python3
"""Redraw hiad_design_sensitivity.png from the thesis's own equations.

AXIOMS / THEORIES / APPLICATIONS / CITATIONS
---------------------------------------------
AXIOMS (what is taken as given; every value below is DOCUMENTED, none invented):
  A1  The imported artwork this replaces plotted panel (b) with a COSINE
      parameterisation (60 deg -> ~998 mm) that contradicts eq:structural_integration
      (R_N = R_pay / sin(theta_c), 60 deg -> 577.4 mm, chapter II), and its
      panel (a) curve rose away from the 3.0 m target while the caption claimed
      convergence; its 2.90 pt labels were below the 8 pt print floor
      (CARVE_OUTS.md section 4). The image had no generator, so the four
      defects could only be fixed by redrawing.
  A2  Documented constants (chapter II + engine record, all cited in-text):
      payload adapter radius R_pay = 500 mm (stated with eq:structural_integration);
      baseline theta_c = 60 deg, inflated diameter D = 3.0 m, toroid count
      N_t = 6 (fig:hiad_parametric_cross_section caption); shoulder torus radius
      r_sh = 0.0508 m (stellarorion_geometry.ads:12 and Discussion.md:45/51,
      "Rapisarda's parametric model"); design bounds r_tor in [0.01, 0.5] m,
      N_t in [1, 12] (eq:design_bounds).
  A3  Only TWO panels are reproducible from equations that exist in the text:
      (a) old "effective inflated diameter vs N_t" has no formula anywhere in
      the thesis and its plotted values (3.13-3.51 m) match no documented
      relation -> DROPPED rather than invented (never-invent rule).

THEORIES (closed-form relations the two panels plot):
  T1  Structural integration constraint (Rapisarda Eq. 3.4, chapter II):
      R_N(theta_c) = R_pay / sin(theta_c)  -> strong theta_c/R_N coupling;
      at 60 deg gives 577.4 mm, the R_N = 577 mm baseline in the cross-section figure.
  T2  Toroid radius closure (Rapisarda Eq. 3.3, chapter II):
      r_tor(N_t) = (r_target - R_pay - r_sh (cos theta_c - sin theta_c + 1))
                   / (2 N_t cos theta_c), r_target = D/2
      -> monotonically inverse in N_t (the caption's claim), evaluated at the
      documented baseline theta_c = 60 deg.

APPLICATIONS (how the figure is produced):
  Renders both curves with matplotlib at 300 dpi on a 6.2 x 3.4 in canvas,
  prints >= 8 pt fonts at the 0.95 \textwidth include scale, forbids "--" in
  any drawn text, and verifies the smallest printed label before writing.

CITATIONS:
  [Rapisarda 2023, MDAO IRVE-3 adaptation - bib key rapisarda2023mdao]
  [NASA/IRVE-3 geometry: stellarorion_geometry.ads - shoulder torus 0.0508 m]

Errors (raised, never swallowed):
  SystemExit(1) if any drawn text would print below 8 pt at the include scale,
  if a rendered string contains "--", or if the output path is not writable.
"""

from __future__ import annotations

import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.text import Text  # noqa: E402
import numpy as np  # noqa: E402

# Documented constants (AXIOM A2): every one appears in the thesis text or the
# Ada geometry spec; nothing here is fitted or guessed.
R_PAY_M = 0.500           # payload adapter radius, stated with eq:structural_integration
R_SH_M = 0.0508           # shoulder torus outer radius (stellarorion_geometry.ads)
D_TARGET_M = 3.0          # inflated diameter, fig cross-section caption
THETA_BASE_DEG = 60.0     # baseline half-cone angle
R_TOR_LO_M, R_TOR_HI_M = 0.01, 0.5   # eq:design_bounds
N_T_LO, N_T_HI = 1, 12               # eq:design_bounds

# Print contract: included at 0.95 \textwidth (5.24 in) from a 6.2 in natural
# canvas -> printed pt = fontsize * 5.24/6.2. Floor is 8 pt -> need >= 9.5 pt.
INCLUDE_W_IN, NATURAL_W_IN = 0.95 * 5.5118, 6.2
FLOOR_PT = 8.0
FONT_BODY = 11.0   # prints 9.3 pt >= 8
FONT_TICK = 10.0   # prints 8.45 pt >= 8 (margin over the 7.97-8.09 pt edge)
DPI = 300
SAVE_DPI = 300


def rn_from_theta(theta_deg: np.ndarray) -> np.ndarray:
    """Structural integration constraint R_N = R_pay / sin(theta_c) [m].

    Parameters
    ----------
    theta_deg : ndarray
        Half-cone angles in degrees, strictly within (0, 180).

    Returns
    -------
    ndarray
        Required nose-sphere radius in metres.

    Raises
    ------
    ValueError
        If any angle falls outside (0, 180) degrees (sin would be <= 0).
    """
    theta = np.asarray(theta_deg, dtype=float)
    if np.any(theta <= 0) or np.any(theta >= 180):
        raise ValueError("theta_c must lie strictly within (0, 180) degrees")
    return R_PAY_M / np.sin(np.radians(theta))


def rtor_from_nt(n_t: np.ndarray) -> np.ndarray:
    """Toroid closure radius r_tor(N_t) at the documented baseline [m].

    Parameters
    ----------
    n_t : ndarray
        Toroid counts >= 1.

    Returns
    -------
    ndarray
        Required individual toroid minor radius in metres.

    Raises
    ------
    ValueError
        If any toroid count is < 1 (division by 2*N_t*cos(theta_c)).
    """
    n = np.asarray(n_t, dtype=float)
    if np.any(n < 1):
        raise ValueError("toroid count N_t must be >= 1")
    th = math.radians(THETA_BASE_DEG)
    r_target = D_TARGET_M / 2.0
    numerator = r_target - R_PAY_M - R_SH_M * (math.cos(th) - math.sin(th) + 1.0)
    return numerator / (2.0 * n * math.cos(th))


def verify_fonts(fig) -> None:
    """Assert every drawn text renders >= 8 pt at the include scale.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure about to be saved.

    Returns
    -------
    None

    Raises
    ------
    SystemExit
        If any text object's effective printed size is below FLOOR_PT, or any
        drawn string contains the substring "--".
    """
    scale = INCLUDE_W_IN / NATURAL_W_IN
    worst = 1e9
    for t in fig.findobj(Text):
        s = t.get_text()
        if not s or not s.strip():
            continue
        if "--" in s:
            raise SystemExit(f"forbidden '--' in figure text: {s!r}")
        fs = t.get_fontsize()
        if fs:
            worst = min(worst, fs * scale)
    if worst < FLOOR_PT:
        raise SystemExit(
            f"printed text {worst:.2f} pt < {FLOOR_PT} pt floor (scale {scale:.3f})"
        )


def build_figure() -> matplotlib.figure.Figure:
    """Draw the two reproducible sensitivity panels.

    Parameters
    ----------
    None

    Returns
    -------
    matplotlib.figure.Figure
        Figure with panels (a) R_N(theta_c) and (b) r_tor(N_t).

    Raises
    ------
    ValueError
        Propagated from the curve helpers on out-of-domain input.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(NATURAL_W_IN, 3.4))

    # Panel 1: structural integration constraint.
    theta = np.linspace(30.0, 80.0, 400)
    rn = rn_from_theta(theta) * 1000.0  # mm for readability
    ax1.plot(theta, rn, color="tab:blue", linewidth=2.0)
    ax1.axvline(THETA_BASE_DEG, color="0.40", linestyle=":", linewidth=1.2)
    ax1.axhline(R_PAY_M / math.sin(math.radians(THETA_BASE_DEG)) * 1000.0,
                color="0.40", linestyle=":", linewidth=1.2)
    ax1.plot([THETA_BASE_DEG],
             [R_PAY_M / math.sin(math.radians(THETA_BASE_DEG)) * 1000.0],
             "o", color="tab:red", markersize=6, zorder=5)
    #  xytext (58, 510) ha=right, re-placed 2026-10-10 (image-specialist +
    #  PIL probes): (76, 450) fell below panel a's y-limit (~483 mm, autoscale
    #  under the 508 mm curve end) and collided with the 60 deg tick mark and
    #  its "60" tick label; the first re-placement at (65, 510) put the text
    #  right edge at x~698 against a measured 12.2 px/deg (60 deg tick = x637,
    #  80 deg curve end = x881), so the dotted 60 deg crosshair ran behind the
    #  tail glyphs. Measured 12.2 px/deg (60 deg tick = x637): the 58 deg
    #  anchor then pushed the 363 px label onto the left spine (ink x[245,608],
    #  spine x[245-247]); 59 deg lands it at x[258,621]: 11 px clear of the
    #  spine, 14 px left of the crosshair, 7 px clear of the leader, 29 px
    #  above the tick zone, below the curve everywhere in that x-range, and
    #  inside the frame (spine x907-909).
    ax1.annotate("baseline 577 mm",
                 xy=(THETA_BASE_DEG,
                     R_PAY_M / math.sin(math.radians(THETA_BASE_DEG)) * 1000.0),
                 xytext=(59, 510), ha="right", fontsize=FONT_TICK,
                 arrowprops=dict(arrowstyle="->", color="0.30", lw=1.0))
    ax1.set_xlabel("half-cone angle (deg)", fontsize=FONT_BODY)
    ax1.set_ylabel("nose radius $R_N$ (mm)", fontsize=FONT_BODY)
    ax1.set_title("(a) $R_N = R_{pay}/\\sin\\theta_c$",
                  fontsize=FONT_BODY + 0.5)
    ax1.grid(True, alpha=0.30)
    ax1.tick_params(labelsize=FONT_TICK)

    # Panel 2: toroid closure radius vs toroid count.
    n_t = np.arange(N_T_LO, N_T_HI + 1, dtype=float)
    r_tor = rtor_from_nt(n_t) * 1000.0  # mm
    ax2.plot(n_t, r_tor, "-o", color="tab:orange", linewidth=2.0,
             markersize=5)
    # eq:design_bounds shading for r_tor.
    ax2.axhspan(R_TOR_LO_M * 1000.0, R_TOR_HI_M * 1000.0,
                color="tab:green", alpha=0.10)
    ax2.axhline(R_TOR_HI_M * 1000.0, color="tab:green", linestyle="--",
                linewidth=1.0)
    #  x=3.0 + white halo: the old x=1.4 put the text under the Nt=1->2
    #  curve crossing (image-specialist defect 2026-10-09); right of
    #  Nt=2 the curve lies at y>=565 px, far below this label at y~540 px.
    ax2.text(3.0, R_TOR_HI_M * 1000.0 + 14,
             "upper bound 0.5 m", fontsize=FONT_TICK, color="tab:green",
             bbox={"facecolor": "white", "alpha": 0.85,
                   "edgecolor": "none", "pad": 1.0})
    out = r_tor[(r_tor >= R_TOR_LO_M * 1000.0) & (r_tor <= R_TOR_HI_M * 1000.0)]
    #  xytext (11, 700) ha=right: the old (7.4, 250) ran 73 px past the
    #  right frame (image-specialist defect 2026-10-09); right-aligned at
    #  Nt=11 the two lines span x[1475,1735] px inside frame x=1783 and
    #  y[439,515] px clear of the curve (y>=730 px there) and of the
    #  green bound label (y>=540 px).
    #  Plain text, NOT annotate (2026-10-09): the leader line from (11,700)
    #  to marker 9 crossed the digit "0" of the green "0.5 m" label
    #  (image-specialist measurement x1580-1626, y468-749). The text
    #  annotates the design WINDOW (band + dashed line), not one point,
    #  so the leader is unnecessary; this exact position was verified
    #  clear of every element (y[357,438] x[1419,1728]).
    ax2.text(11, 700, f"design window\n{out.min():.0f}-{out.max():.0f} mm",
             ha="right", fontsize=FONT_TICK, color="0.20")
    ax2.set_xlabel("toroid count $N_t$", fontsize=FONT_BODY)
    ax2.set_ylabel("toroid radius $r_{tor}$ (mm)", fontsize=FONT_BODY)
    ax2.set_title("(b) closure $r_{tor}(N_t)$", fontsize=FONT_BODY + 0.5)
    ax2.set_xticks(n_t)
    ax2.grid(True, alpha=0.30)
    ax2.tick_params(labelsize=FONT_TICK)

    fig.suptitle("Design-variable sensitivity from the closure constraints",
                 fontsize=FONT_BODY + 1.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.text(0.99, 0.01,
             "Source: Rapisarda (2023) Eqs. 3.4 and 3.3",
             ha="right", va="bottom", fontsize=FONT_TICK, color="0.35")
    return fig


def main() -> int:
    """Render, verify and atomically write the sensitivity figure.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Process exit status: 0 on success, 1 on any verification failure.

    Raises
    ------
    SystemExit
        Delegated from verify_fonts on font-floor or '--' violations.
    """
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "hiad_design_sensitivity.png")
    fig = build_figure()
    try:
        verify_fonts(fig)
        tmp = out + ".tmp.png"
        fig.savefig(tmp, dpi=SAVE_DPI)
        os.replace(tmp, out)
    finally:
        plt.close(fig)
    print(f"wrote {out} "
          f"(scale {INCLUDE_W_IN / NATURAL_W_IN:.3f}, "
          f"floor {FLOOR_PT} pt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
