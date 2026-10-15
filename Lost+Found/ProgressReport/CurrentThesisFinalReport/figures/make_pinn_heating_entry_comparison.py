"""Render the reference-vs-optimized PINN heating and entry overview.

Uses the step-aligned, 570-row full-trajectory overview files that exist for
both trees: results/00_reference/validation_pipeline_output/
pinn_trajectory_per_step.csv and results/03_opt_geometry/
validation_pipeline_output/pinn_trajectory_per_step.csv.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / "stellarorion_program_proc" / "results"
OUT = Path(__file__).resolve().parent / "pinn_heating_entry_comparison.png"

FILES = {
    "Reference": RESULTS / "00_reference" / "validation_pipeline_output" / "pinn_trajectory_per_step.csv",
    "Optimized": RESULTS / "03_opt_geometry" / "validation_pipeline_output" / "pinn_trajectory_per_step.csv",
}


def read(path: Path) -> dict[str, list[float]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        "step": [float(r["step"]) for r in rows],
        "heat_flux": [float(r["heat_flux_max_Wm2"]) for r in rows],
        "velocity": [float(r["velocity_ms"]) for r in rows],
        "altitude": [float(r["altitude_km"]) for r in rows],
    }


def main() -> int:
    data = {label: read(path) for label, path in FILES.items()}
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.4), dpi=160)

    for label, style in (("Reference", "-"), ("Optimized", "--")):
        d = data[label]
        axes[0].plot(d["step"], d["heat_flux"], style, linewidth=2.0, label=label)
        axes[1].plot(d["step"], d["velocity"], style, linewidth=2.0, label=label)

    axes[0].axvline(2200, color="firebrick", linestyle=":", linewidth=1.5)
    axes[0].axvspan(0, 2200, color="gray", alpha=0.12)
    axes[0].set_yscale("log")
    axes[0].set_title("PINN overview: peak heat flux")
    axes[0].set_xlabel("Step (0=launch offset; 2200=DSMC-to-PINN boundary)")
    axes[0].set_ylabel("Peak heat flux (W/m^2)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="lower right", fontsize=9)

    axes[1].axvline(2200, color="firebrick", linestyle=":", linewidth=1.5)
    axes[1].axvspan(0, 2200, color="gray", alpha=0.12)
    axes[1].set_title("PINN overview: entry velocity")
    axes[1].set_xlabel("Step (0=launch offset; 2200=DSMC-to-PINN boundary)")
    axes[1].set_ylabel("Velocity (m/s)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right", fontsize=9)

    note = "Curves for the reference and optimized trees coincide for the heating and entry columns; only the force coefficients differ."
    fig.suptitle("Step-aligned PINN overview, reference versus optimized topology", fontsize=13)
    axes[1].text(0.5, -0.18, note, ha="center", va="top", transform=axes[1].transAxes,
                 fontsize=9, wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    fig.savefig(OUT, bbox_inches="tight", dpi=160)
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
