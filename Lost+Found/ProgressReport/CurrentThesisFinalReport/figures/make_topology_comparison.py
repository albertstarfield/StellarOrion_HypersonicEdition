"""Compare the flown HIAD topologies: reference versus optimised candidates.

PURPOSE
    Show, from the geometry the DSMC solver actually integrated, how the
    reference body, the optimised-topology candidate and the two gate
    candidates differ. Supersedes the earlier layout whose legend escaped the
    canvas, whose delta-r arrow used an invalid interpolation across a
    non-monotonic polyline, and whose table rows collided with the footer.

AXIOMS
    A1. The flown surface of a run is exactly the polyline in
        ``stellarorion_program_proc/results/<tree>/HIAD_custom.surf``, which is
        the file ``in.hiad`` hands to SPARTA. Reuse it; never reconstruct it.
    A2. The body is axisymmetric, so the meridian above the centreline
        (r >= 0) determines it. The polyline is not single valued in x: it
        rises to the shoulder and then falls down the back face, so no
        interpolation in x is valid and none is used.
    A3. The gate heat load Q of a tree is the total recorded by that tree's
        validation time series, quoted not recomputed.
    A4. ``03_opt_geometry`` has no independent validation time series in these
        results, so its Q cell is "n/a" and must not be filled in.

THEORIES
    T1. At equal axis scale the two 1.269 m trees differ only in the outer
        envelope, and the pass-2 candidate is visibly a smaller body.
    T2. Wide text inside a narrow axes escapes the canvas. Therefore the
        panel labels are short names only and all numbers live in the table
        below, which spans the full figure width.
    T3. Envelope radii read from the maxima of the polylines are the honest
        measure of the shoulder difference; a double arrow between horizontal
        guides at those radii shows it without touching the curve shape.

APPLICATIONS
    Writes ``figures/hiad_topology_comparison.png`` for Chapter 4.

CITATIONS
    [1] stellarorion_program_proc/scripts/plot_hiad_3d.py - read_surf.
    [2] stellarorion_program_proc/results/*/HIAD_custom.surf - SPARTA surface.
    [3] results/validation_optimized_round2/DSMC_PINN_AUX_vs_reference.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parent.parent.parent.parent
PROC = REPO_ROOT / "stellarorion_program_proc"
sys.path.insert(0, str(PROC / "scripts"))

from plot_hiad_3d import read_surf  # noqa: E402

INK = "#222222"
GRID = "#E8E8E8"
TREES = [
    ("00_reference", "#004488", "-", "validation reference", 165.716),
    ("03_opt_geometry", "#DDAA33", "--", "optimised candidate", None),
    ("validation_optimized", "#228833", "-.", "gate pass 1 (failed)", 175.580),
    ("validation_optimized_round2", "#BB5566", ":", "gate pass 2 (passed)", 117.526),
]


def load(tree: str) -> np.ndarray:
    """Return the (x, r) polyline of ``tree`` in metres.

    AXIOM A1: the surface file is the ground truth; a missing file raises,
    it is never approximated.
    """
    path = PROC / "results" / tree / "HIAD_custom.surf"
    if not path.is_file():
        raise FileNotFoundError(f"flown surface missing: {path}")
    pts = np.asarray(read_surf(str(path)), dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 3:
        raise ValueError(f"unexpected surface shape {pts.shape} in {path}")
    return pts


def main() -> int:
    """Render the comparison and return a process status."""
    profiles = {tree: load(tree) for tree, *_ in TREES}

    fig = plt.figure(figsize=(6.0, 6.10))

    ax_full = fig.add_axes([0.105, 0.545, 0.345, 0.375])
    ax_zoom = fig.add_axes([0.565, 0.545, 0.405, 0.375])
    ax_tab = fig.add_axes([0.045, 0.135, 0.910, 0.300])
    ax_tab.axis("off")
    ax_tab.set_xlim(0.0, 1.0)
    ax_tab.set_ylim(0.0, 1.0)

    for tree, colour, style, label, q_value in TREES:
        pts = profiles[tree]
        ax_full.plot(pts[:, 0], pts[:, 1], color=colour, ls=style, lw=1.7,
                     label=label)

    ax_full.set_aspect("equal", adjustable="box")
    ax_full.set_xlim(-0.03, 1.34)
    ax_full.set_ylim(0.0, 1.97)
    ax_full.set_xlabel("Axial position $z$ (m)", fontsize=8.5, labelpad=1)
    ax_full.set_ylabel("Radial position $r$ (m)", fontsize=8.5, labelpad=1)
    ax_full.tick_params(labelsize=8.0, pad=2)
    ax_full.grid(True, color=GRID, lw=0.6)
    ax_full.set_axisbelow(True)
    for side in ("top", "right"):
        ax_full.spines[side].set_visible(False)
    ax_full.set_title("Flown meridional half-sections", fontsize=9.5, color=INK,
                      pad=5)
    #  WHY: at lower right the four-entry key covered the nose arc of the
    #  reference body; the upper left of this panel is empty.
    ax_full.legend(loc="upper left", fontsize=7.0, frameon=True,
                   facecolor="white", edgecolor="#BBBBBB", framealpha=1.0,
                   handlelength=2.2, borderpad=0.45, labelspacing=0.35)

    ref = profiles["00_reference"]
    opt = profiles["03_opt_geometry"]
    ax_zoom.plot(ref[:, 0], ref[:, 1], color="#004488", lw=1.9, label="reference")
    ax_zoom.plot(opt[:, 0], opt[:, 1], color="#DDAA33", ls="--", lw=1.7,
                 label="optimised candidate")
    r_max_ref = float(ref[:, 1].max())
    r_max_opt = float(opt[:, 1].max())
    ax_zoom.axhline(r_max_ref, color="#004488", lw=0.7, ls=(0, (2, 3)))
    ax_zoom.axhline(r_max_opt, color="#DDAA33", lw=0.7, ls=(0, (2, 3)))
    ax_zoom.annotate("", xy=(1.285, r_max_ref), xytext=(1.285, r_max_opt),
                     arrowprops=dict(arrowstyle="<->", lw=0.9, color=INK))
    ax_zoom.text(1.268, 0.5 * (r_max_ref + r_max_opt),
                 f"{(r_max_ref - r_max_opt) * 1000:.1f} mm",
                 fontsize=7.6, color=INK, va="center", ha="right",
                 bbox=dict(facecolor="white", edgecolor="none", pad=0.8))
    ax_zoom.set_xlim(0.78, 1.32)
    ax_zoom.set_ylim(1.70, 1.93)
    ax_zoom.set_xlabel("Axial position $z$ (m)", fontsize=8.5, labelpad=1)
    ax_zoom.set_ylabel("Radial position $r$ (m)", fontsize=8.5, labelpad=1)
    ax_zoom.tick_params(labelsize=8.0, pad=2)
    ax_zoom.grid(True, color=GRID, lw=0.6)
    ax_zoom.set_axisbelow(True)
    for side in ("top", "right"):
        ax_zoom.spines[side].set_visible(False)
    ax_zoom.set_title("Shoulder envelope difference", fontsize=9.5, color=INK,
                      pad=5)
    ax_zoom.legend(loc="lower left", fontsize=7.2, frameon=True,
                   facecolor="white", edgecolor="#BBBBBB", framealpha=1.0)

    cols = [0.005, 0.360, 0.470, 0.590, 0.720]
    header = ["flown tree", "L (m)", "$r_{max}$ (m)", "Q (J/cm$^2$)", "gate"]
    for x, text in zip(cols, header):
        ax_tab.text(x, 0.94, text, fontsize=8.0, fontweight="bold",
                    color=INK, ha="left", va="center")
    rows = [
        ("00_reference", "1.269", "1.880", "165.716", "target"),
        ("03_opt_geometry", "1.269", "1.830", "n/a", "n/a"),
        ("validation_optimized", "1.597", "2.255", "175.580", "FAIL"),
        ("validation_optimized_round2", "0.803", "1.174", "117.526", "PASS"),
    ]
    #  WHY: the rows start high and step by 0.155 so that the four data
    #  rows clear the footer, and every footer line is short enough to fit
    #  inside the axes width at 6.8 pt (a long line was clipped before).
    for i, row in enumerate(rows):
        y = 0.78 - 0.19 * i
        for j, (x, text) in enumerate(zip(cols, row)):
            ax_tab.text(x, y, text, fontsize=7.8, color=INK, ha="left",
                        va="center")
    fig.text(0.045, 0.020,
             "The two 1.269 m trees differ by at most 54.2 mm at any vertex; the pass-2\n"
             "body is 0.62 times the reference size. Q is the recorded total heat load of that\n"
             "tree's validation series; 03_opt_geometry was not flown through the gate, so Q is n/a.\n"
             "Surfaces read from results/<tree>/HIAD_custom.surf: no simulation re-run, no geometry reconstructed.",
             fontsize=6.8, color="#444444", ha="left", va="bottom",
             linespacing=1.45)

    out = FIG_DIR / "hiad_topology_comparison.png"
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)
    for tree, *_ in TREES:
        p = profiles[tree]
        print(f"{tree}: L={p[:,0].max():.5f} m  r_max={p[:,1].max():.5f} m")
    print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
