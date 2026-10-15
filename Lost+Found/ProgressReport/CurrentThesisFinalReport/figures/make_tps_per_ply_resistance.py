"""Render the per-ply through-flux and series-resistance budget at the peak element.

AXIOMS
------
A1. A one-dimensional series stack at steady state carries the same
    through-flux through every ply, because no ply generates or stores
    heat in the steady model. Per-ply flux therefore cannot differ between
    plies; what differs between plies is the temperature drop.
A2. The ply schedule is shared by both trees (Table tps_layup of the
    thesis): Nicalon SiC 0.506 mm x2, Pyrogel 3350 3.047 mm x2, Kapton
    0.025 mm x1, conductivities 1.5, 1.5, 0.02, 0.02, 0.12 W/(m K).
A3. The series resistance of a ply is R_i = t_i / k_i, and the total
    series resistance is the sum of the ply resistances.

THEORIES
--------
T1. From A1 and A3 the temperature drop across ply i is
    q * R_i, so the resistance budget, not the flux, decides which ply
    drops the temperature. The two Pyrogel plies must therefore dominate.
T2. From A3 the total series resistance must equal the value the thesis
    quotes for the stack, 0.305583 m^2 K/W. The figure prints the
    decomposed budget so that identity is visible rather than asserted.

APPLICATIONS
------------
Renders ``tps_per_ply_resistance.png``: per-ply through-flux at each
tree's own peak element on the left and the per-ply series-resistance
budget on the right.

CITATIONS
---------
    [Citation: Matplotlib v3.11.2 - https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html]
    [Reference: ASTM C518 - Standard Test Method for Steady-State Thermal Transmission Properties]

Reads the two profile tables and the two per-element tables; writes one PNG.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / "stellarorion_program_proc" / "results"
OUT = Path(__file__).resolve().parent / "tps_per_ply_resistance.png"

PROFILES = {
    "Reference": RESULTS / "tps_conduction" / "00_reference" / "tps_step2200_profiles.csv",
    "Optimized": RESULTS / "tps_conduction" / "03_opt_geometry" / "tps_step2200_profiles.csv",
}
ELEMENTS = {
    "Reference": RESULTS / "tps_conduction" / "00_reference" / "tps_step2200_elements.csv",
    "Optimized": RESULTS / "tps_conduction" / "03_opt_geometry" / "tps_step2200_elements.csv",
}
PLY_LABELS = ["Nicalon\nR=3.37e-4", "Nicalon\nR=3.37e-4",
              "Pyrogel\nR=0.1524", "Pyrogel\nR=0.1524", "Kapton\nR=2.08e-4"]


def read_profiles(path: Path) -> dict[int, list[tuple[float, float]]]:
    """Group the long profile table by element, depth-sorted.

    Args:
        path: CSV with columns element, sample, depth_m, temp_K.

    Returns:
        Element id to depth-sorted [(depth_m, temp_K), ...].

    Raises:
        FileNotFoundError: If the profile CSV is absent.
        KeyError: If an expected column is missing.
    """
    if not path.is_file():
        raise FileNotFoundError(f"missing profile CSV: {path}")
    by_el: dict[int, list[tuple[float, float]]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_el.setdefault(int(row["element"]), []).append(
                (float(row["depth_m"]), float(row["temp_K"]))
            )
    for el in by_el:
        by_el[el].sort()
    return by_el


def read_elements(path: Path) -> dict[int, dict[str, str]]:
    """Read the per-element exposure table.

    Args:
        path: CSV with columns element, q_sg_Wm2, t_surface_K, ...

    Returns:
        Element id to its raw row.

    Raises:
        FileNotFoundError: If the per-element CSV is absent.
        KeyError: If an expected column is missing.
    """
    if not path.is_file():
        raise FileNotFoundError(f"missing elements CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return {int(r["element"]): r for r in csv.DictReader(f)}


def main() -> int:
    profiles, elements = {}, {}
    for label in PROFILES:
        try:
            profiles[label] = read_profiles(PROFILES[label])
            elements[label] = read_elements(ELEMENTS[label])
        except (FileNotFoundError, KeyError, ValueError) as exc:
            print(f"ERROR cannot read {label}: {exc}", file=sys.stderr)
            return 1

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), dpi=160)
    width = 0.38
    xpos = list(range(5))

    # Left: per-ply through-flux at each tree's own peak element.
    for offset, (label, colour) in enumerate(
        (("Reference", "tab:blue"), ("Optimized", "tab:orange"))
    ):
        by_el = profiles[label]
        peak_el = max(by_el, key=lambda e: by_el[e][0][1])
        # Through-flux is constant across the stack (axiom A1), so the
        # per-ply value is the peak-element value reported by the solver.
        q = float(elements[label][peak_el]["q_sg_Wm2"])
        axes[0].bar(
            [p + (offset - 0.5) * width for p in xpos],
            [q] * 5, width, color=colour, alpha=0.85, label=f"{label} (element {peak_el})",
        )
    axes[0].set_xticks(xpos)
    axes[0].set_xticklabels(PLY_LABELS, fontsize=8)
    axes[0].set_xlabel("ply (hot face to cold face)")
    axes[0].set_ylabel("through-flux q [W/m$^2$]")
    axes[0].set_title("Per-ply through-flux at the peak element", fontsize=11)
    axes[0].grid(True, axis="y", alpha=0.3)
    axes[0].legend(loc="upper right", fontsize=9)

    # Right: series-resistance budget, identical for both trees (shared layup).
    thick = [0.000506, 0.000506, 0.003047, 0.003047, 2.5e-05]
    cond = [1.5, 1.5, 0.02, 0.02, 0.12]
    resist = [t / k for t, k in zip(thick, cond)]
    axes[1].bar(xpos, resist, 0.6, color="tab:green", alpha=0.85)
    axes[1].set_yscale("log")
    axes[1].set_xticks(xpos)
    axes[1].set_xticklabels(
        ["Nicalon\n0.337e-3", "Nicalon\n0.337e-3", "Pyrogel\n0.1524",
         "Pyrogel\n0.1524", "Kapton\n0.208e-3"], fontsize=8,
    )
    axes[1].set_xlabel("ply (hot face to cold face)")
    axes[1].set_ylabel("series resistance $R_i$ [m$^2$ K/W], log scale")
    axes[1].set_title(
        f"Per-ply resistance budget (total {sum(resist):.6f} m$^2$ K/W)", fontsize=11
    )
    axes[1].grid(True, axis="y", alpha=0.3)

    fig.suptitle(
        "Per-ply heat flux and resistance budget, step 2200 (shared five-ply schedule)",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT} (total R = {sum(resist):.6f} m^2 K/W)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
