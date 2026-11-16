"""Draw the HIAD bladder layout as a meridional half-section.

PURPOSE
    Replace the earlier measured reconstruction, whose fitted skin line
    self-intersected and produced the "sharp mushroom" outline. This script
    draws the nose shell returned by the repo geometry API and the six
    toroidal bladders at their computed centres, as a line schematic.

AXIOMS
    A1. `hiad_geometry.generate_cross_section` (an exact copy of the
        Ada/SPARK Get_HIAD_Cross_Section) supplies the nose shell.
    A2. Torus i is centred at s_i = (2i+1) r_tor along the cone:
        z_i = Z_tang + s_i sin(gamma), r_i = R_tang + s_i cos(gamma),
        gamma = 90 deg - half_cone, R_tang = R_N cos(gamma),
        Z_tang = R_N (1 - sin(gamma)).
    A3. The body is axisymmetric, so the half-section above the centreline
        fully defines it; the centreline is the symmetry axis.
    A4. The aft aerodynamic skin is a straight generator through the torus
        centres plus a shoulder wrap and a flat back. Drawing it as a filled
        solid hides the bladders and reads as a mushroom, so only the row
        centreline is drawn; the skin is stated to be omitted.

THEORIES
    T1. Nose arc + six circles on the generator + the generator line is a
        faithful, self-intersection-free depiction of the bladder stack.
    T2. Axis-equal scaling preserves the half-cone angle and the torus
        proportions read from the panel.
    T3. A half-section halves the panel height relative to the mirrored
        drawing, so the figure fits a text page without a sparse full page.

APPLICATIONS
    Writes `figures/hiad_parametric_cross_section.png` for Chapter 2,
    `fig:hiad_parametric_cross_section`, at 0.85\\textwidth.

CITATIONS
    [1] hiad_geometry.py - generate_cross_section, N_TORI = 6.
    [2] stellarorion_pinn_trajectory.adb - Get_HIAD_Cross_Section.
    [3] Rapisarda (2023), MSc Thesis TU Delft, Sec. 3.7 and App. C.1.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO = FIG_DIR.parent.parent.parent.parent
sys.path.insert(0, str(REPO / "stellarorion_program_proc" / "src" / "python"))

from hiad_geometry import generate_cross_section  # noqa: E402

R_N = 0.55          # m, nose-sphere radius
R_TOR = 0.135       # m, torus tube radius
HALF_CONE = 60.0    # deg
N_TORI = 6

SKIN = "#DDAA33"
TORUS = "#66CCEE"
TORUS_EDGE = "#004488"
INK = "#222222"


def main() -> int:
    """Render the half-section and return a process status."""
    x, y = generate_cross_section(R_N, R_TOR, HALF_CONE)
    gamma = math.radians(90.0 - HALF_CONE)
    r_tang = R_N * math.cos(gamma)
    z_tang = R_N * (1.0 - math.sin(gamma))
    r_max = r_tang + (2 * N_TORI - 1) * R_TOR * math.cos(gamma) + R_TOR

    centres = []
    for i in range(N_TORI):
        s = (2 * i + 1) * R_TOR
        centres.append((z_tang + s * math.sin(gamma),
                        r_tang + s * math.cos(gamma)))

    fig, ax = plt.subplots(figsize=(5.525, 4.55))
    #  WHY: the data box is 1.32 m by 2.04 m (aspect 0.65). Equal aspect
    #  therefore leaves a wide right margin; the parameter panel is placed
    #  there instead of below the plot, which keeps the figure short.
    fig.subplots_adjust(left=0.125, right=0.575, bottom=0.125, top=0.895)

    nose = x <= z_tang + 1e-12
    ax.plot(x[nose], y[nose], color=SKIN, lw=1.8, zorder=2)

    ax.plot([centres[0][0], centres[-1][0]],
            [centres[0][1], centres[-1][1]],
            color="#777777", lw=0.9, ls=(0, (5, 3)), zorder=1)

    for i, (zc, rc) in enumerate(centres, start=1):
        ax.add_patch(Circle((zc, rc), R_TOR, facecolor=TORUS,
                            edgecolor=TORUS_EDGE, lw=0.9, alpha=0.60,
                            zorder=3))
        ax.text(zc, rc, f"$T_{i}$", ha="center", va="center", fontsize=7.2,
                color=TORUS_EDGE, fontweight="bold", zorder=4)

    ax.axhline(0.0, color="#777777", lw=1.0, ls=":")

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(0.0, 1.32)
    ax.set_ylim(0.0, r_max + 0.14)
    ax.set_xlabel("Axial coordinate $z$ (m)", fontsize=8.5)
    ax.set_ylabel("Radial coordinate $r$ (m)", fontsize=8.5)
    ax.tick_params(labelsize=8.0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    info = (f"$R_N$ = {R_N:.2f} m\n"
            f"$r_{{\\mathrm{{tor}}}}$ = {R_TOR:.3f} m\n"
            f"$\\theta_c$ = {HALF_CONE:.0f}$^\\circ$\n"
            f"$N_t$ = {N_TORI}\n"
            f"$R_{{\\max}}$ = {r_max:.2f} m\n"
            f"$L_{{\\mathrm{{body}}}}$ = {x.max():.3f} m")
    fig.text(0.605, 0.50, info, va="center", ha="left", fontsize=8.6,
             color=INK, linespacing=1.55,
             bbox=dict(boxstyle="round,pad=0.55", facecolor="white",
                       edgecolor="#BBBBBB", alpha=0.96))

    #  WHY: the note is wrapped to three short lines, because a single long
    #  line overruns the right edge of the canvas and is clipped in the PNG.
    fig.text(0.605, 0.315,
             "Skin aft of the nose tangent\nomitted so that the bladder\n"
             "stack remains visible.",
             va="top", ha="left", fontsize=7.4, color="#555555",
             linespacing=1.45)

    fig.text(0.125, 0.955, "HIAD meridional half-section: bladder layout",
             fontsize=9.4, color=INK, ha="left", va="top")

    out = FIG_DIR / "hiad_parametric_cross_section.png"
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)
    print(f"wrote {out.name}: R_max={r_max:.4f} m, length={x.max():.4f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
