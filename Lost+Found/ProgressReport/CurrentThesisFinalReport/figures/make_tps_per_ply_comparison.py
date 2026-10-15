"""Render the reference-vs-optimized per-ply TPS conduction comparison.

AXIOMS
------
A1. Each result tree carries its own step-2200 conduction solve, so the two
    trees are comparable only point by point, never as a single field:
    ``results/00_reference/tps_conduction/`` and
    ``results/03_opt_geometry/tps_conduction/``.
A2. ``tps_step2200_profiles.csv`` is a long table (element, sample, depth_m,
    temp_K) holding a 33-point through-thickness profile per element. The
    shallowest sample is the hot face and the deepest sample is the cold
    face; the deepest sample is NOT a prediction, because the solver pins
    the cold face to T_init by a steady-state Dirichlet condition
    (see ``run_tps_conduction_step2200.py``, "READING OF T_back").
A3. Surface temperature is a per-element field. Two trees may therefore
    put the peak on different elements while producing the same peak value.

THEORIES
--------
T1. Because A3 holds, a topology that does not change the heating field
    cannot change the peak surface temperature; it can only move which
    element carries it. The figure therefore overlays the through-thickness
    profile at each tree's own peak element, and plots the per-element
    surface-temperature field separately.
T2. The informative stress metric is the hot-face temperature, per A2. The
    cold-face column is reported only to show that it is pinned.

APPLICATIONS
------------
Renders ``tps_per_ply_comparison.png``: a two-panel figure with the
through-thickness profile at each tree's peak element on the left and the
per-element hot-face temperature field on the right.

CITATIONS
---------
    [Citation: Matplotlib v3.11.2 - https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html]
    [Based on: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subplots_demo.html]

Reads only; writes one PNG. Exits non-zero with a diagnostic if either
input tree is missing, so a silent half-figure is impossible.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / "stellarorion_program_proc" / "results"
OUT = Path(__file__).resolve().parent / "tps_per_ply_comparison.png"

TREES = {
    "Reference": RESULTS / "tps_conduction" / "00_reference" / "tps_step2200_profiles.csv",
    "Optimized": RESULTS / "tps_conduction" / "03_opt_geometry" / "tps_step2200_profiles.csv",
}
STRUCT_LIMIT_K = 523.15
KAPTON_LIMIT_K = 773.15


def read_profiles(path: Path) -> dict[int, list[tuple[float, float]]]:
    """Group the long profile table by element.

    Args:
        path: CSV with columns element, sample, depth_m, temp_K.

    Returns:
        Mapping of element id to a depth-sorted list of (depth_m, temp_K).

    Raises:
        FileNotFoundError: If the profile CSV does not exist.
        KeyError: If the header is missing an expected column.
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


def main() -> int:
    series = {}
    for label, path in TREES.items():
        try:
            series[label] = read_profiles(path)
        except (FileNotFoundError, KeyError, ValueError) as exc:
            print(f"ERROR cannot read {label}: {exc}", file=sys.stderr)
            return 1
        if not series[label]:
            print(f"ERROR {label} profile table is empty", file=sys.stderr)
            return 1

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), dpi=160)

    # Left: through-thickness profile at each tree's own hot-face peak.
    for label, style, colour in (
        ("Reference", "-", "tab:blue"),
        ("Optimized", "--", "tab:orange"),
    ):
        by_el = series[label]
        peak_el = max(by_el, key=lambda e: by_el[e][0][1])
        depths = [d for d, _ in by_el[peak_el]]
        temps = [t for _, t in by_el[peak_el]]
        axes[0].plot(
            [d * 1000.0 for d in depths], temps, style, color=colour, linewidth=2.0,
            label=f"{label} (element {peak_el})",
        )
    axes[0].axhline(KAPTON_LIMIT_K, color="firebrick", linestyle=":", linewidth=1.4)
    axes[0].axhline(STRUCT_LIMIT_K, color="gray", linestyle=":", linewidth=1.4)
    axes[0].text(
        0.015, KAPTON_LIMIT_K, f" Kapton limit {KAPTON_LIMIT_K:.0f} K",
        color="firebrick", fontsize=8, va="bottom", transform=axes[0].get_yaxis_transform(),
    )
    axes[0].text(
        0.015, STRUCT_LIMIT_K, f" structural limit {STRUCT_LIMIT_K:.2f} K",
        color="gray", fontsize=8, va="bottom", transform=axes[0].get_yaxis_transform(),
    )
    axes[0].set_xlabel("depth from hot face [mm]")
    axes[0].set_ylabel("temperature [K]")
    axes[0].set_title("Through-thickness profile at each tree's peak element", fontsize=11)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="lower left", fontsize=9)

    # Right: hot-face temperature field, which redistributes between trees.
    for label, colour in (("Reference", "tab:blue"), ("Optimized", "tab:orange")):
        by_el = series[label]
        els = sorted(by_el)
        axes[1].plot(els, [by_el[e][0][1] for e in els], ".", color=colour,
                     markersize=2.5, label=f"{label} hot face")
    axes[1].axhline(STRUCT_LIMIT_K, color="gray", linestyle=":", linewidth=1.4)
    axes[1].set_xlabel("surface element index")
    axes[1].set_ylabel("hot-face temperature [K]")
    axes[1].set_title("Hot-face temperature field over the surface", fontsize=11)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="lower left", fontsize=9)

    fig.suptitle(
        "Per-ply TPS conduction, reference versus optimized topology (step 2200)",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
