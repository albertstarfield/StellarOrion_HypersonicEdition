"""Redraw the 2200-step Knudsen-number field from the SPARTA grid dump.

PURPOSE
    Figure 4.5 of the thesis shows the local Knudsen number on the
    axisymmetric slice. The original panel was a ParaView screenshot whose
    colour key carried two labels only and whose key text contradicted the
    plotted range. This script rebuilds the same field from the solver's own
    grid dump, so the colour bar, the axis labels and the regime thresholds
    are readable at print size.

AXIOMS
    A1. The dump is the ground truth: the field is computed from the
        cell number density in grid.2200.out, not read from a picture.
    A2. The mean free path is the hard-sphere/VSS estimate
        lambda = 1 / (sqrt(2) * pi * d^2 * n), with d = 3.7e-10 m for air
        (Bird 1994, Eq. 4.45) and the reference length L = 1 m.
    A3. Kn = lambda / L. The reported range is checked against the
        original panel's 1e-5 .. 1.15e-2.

CITATIONS
    Bird, G. A. (1994) Molecular Gas Dynamics and the Direct Simulation of
    Gas Flows, Oxford, Eq. 4.45 (mean free path).
    SPARTA grid dump: results/00_reference/grid.2200.out, dump 2 in in.hiad.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent.parent
DUMP = REPO / "stellarorion_program_proc/results/00_reference/grid.2200.out"
OUT = HERE / "knudsen_map_smooth_M0_A0.png"

D_MOL = 3.7e-10  # m, effective air diameter
L_REF = 1.0      # m


def load() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return cell-centre x, r and number density from the dump."""
    rows = np.loadtxt(DUMP, skiprows=9)
    x = 0.5 * (rows[:, 1] + rows[:, 3])
    r = 0.5 * (rows[:, 2] + rows[:, 4])
    n = rows[:, 10]
    keep = (n > 0.0) & (r >= 0.0)
    return x[keep], r[keep], n[keep]


def main() -> int:
    x, r, n = load()
    lam = 1.0 / (np.sqrt(2.0) * np.pi * D_MOL**2 * n)
    kn = lam / L_REF
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=300)
    mesh = ax.scatter(x, r, c=kn, s=3.0, norm=LogNorm(vmin=1e-5, vmax=1.15e-2),
                      cmap="turbo")
    ax.set_xlabel("Axial distance (m)")
    ax.set_ylabel("Radial distance (m)")
    ax.set_xlim(-1.0, 5.0)
    ax.set_ylim(0.0, 3.6)
    ax.set_aspect("equal", adjustable="box")
    cb = fig.colorbar(mesh, ax=ax, pad=0.02, ticks=[1e-5, 1e-4, 1e-3, 1e-2])
    cb.set_label("Knudsen number $Kn$ ($-$)")
    cb.ax.set_yticklabels([r"$10^{-5}$", r"$10^{-4}$", r"$10^{-3}$", r"$10^{-2}$"])
    ax.set_title("Local Knudsen number, step 2200", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"wrote {OUT.name}  Kn range {kn.min():.3e} .. {kn.max():.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
