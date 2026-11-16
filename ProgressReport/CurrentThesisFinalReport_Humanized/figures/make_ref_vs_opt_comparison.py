"""Draw the reference-versus-optimized DSMC comparison panel for Chapter 4.

PURPOSE
    Chapter 4 reports three DSMC runs of the same solver on the same flight
    condition: the IRVE-3 reference geometry (results/00_reference), the
    pass-1 GA winner (results/validation_optimized) and the pass-2
    gate-corrected winner (results/validation_optimized_round2).  The
    thesis needs one figure that shows the four quantities the gate and the
    cost function actually use -- total heat load, peak surface heat flux,
    drag force and peak deceleration -- against the particle-time step for
    all three runs, so the reader can see the effect of the geometry change
    rather than a single end-of-run number.

    The panel is a pure function of the three `validation_timeseries.csv`
    files written by the solver; no number is typed into the artwork.

CITATIONS
    [1] Bird, G.A. (1994) Molecular Gas Dynamics, Oxford University Press --
        the DSMC method whose time series the panel plots.
    [2] Sutton & Graves (1972) NASA TR R-376 -- the Sutton-Graves
        correlation the heat-load target is expressed in.

AXIOMS
    A1. The three CSVs are the run records; a value in the figure is
        readable in the CSV, and the CSV is the audit trail.
    A2. The heat-load target line (165.716 J/cm^2) is the gate criterion
        from the validation reference set, so the panel shows the same
        threshold the gate applies.

THEORIES
    T1. Because every panel shares the step axis and the legend, the three
        geometries are directly comparable without a second figure.
    T2. A missing column or an empty CSV is a loud failure, not a blank
        panel: the script raises before drawing anything.

APPLICATIONS
    Chapter 4, Section 4.14 (Reference versus Optimized DSMC comparison).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parent.parent.parent.parent
RESULTS = REPO_ROOT / "stellarorion_program_proc/results"

RUNS = (
    ("IRVE-3 reference", RESULTS / "00_reference/validation_timeseries.csv", "#004488"),
    ("pass-1 GA winner", RESULTS / "validation_optimized/validation_timeseries.csv", "#BB5566"),
    ("pass-2 gate winner", RESULTS / "validation_optimized_round2/validation_timeseries.csv", "#228833"),
)

Q_TARGET = 165.715973  # [J/cm^2] validation reference, the gate threshold

PANELS = (
    ("heat_load_jcm2", "Total heat load $Q$  [J/cm$^2$]", "Total heat load [J/cm2]"),
    ("heatflux_max_Wm2", "Peak surface heat flux  [W/cm$^2$]", "Peak surface heat flux [W/cm2]"),
    ("drag_sum_N", "Drag force  [N]", "Drag force [N]"),
    ("g_load", "Peak deceleration  [$g$]", "Peak deceleration [g]"),
)

SCALE = 1.0e-4  # W/m^2 -> W/cm^2 for the flux panel


def read_series(path: Path) -> list[dict[str, float]]:
    """Read one solver time series.

    Parameters:
        path: the `validation_timeseries.csv` of the run.

    Returns:
        A list of row dictionaries with float values.

    Raises:
        FileNotFoundError: the CSV does not exist.
        RuntimeError: the CSV has no data rows.
    """
    if not path.is_file():
        raise FileNotFoundError(f"missing run record: {path}")
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"empty run record: {path}")
    out: list[dict[str, float]] = []
    for row in rows:
        out.append({k: float(v) for k, v in row.items() if v not in (None, "")})
    return out


def main() -> int:
    """Draw the comparison panel; return a process code.

    Returns:
        0 when the figure is written, 1 when a run record is unusable.
    """
    data: list[tuple[str, list[dict[str, float]], str]] = []
    for label, path, colour in RUNS:
        try:
            rows = read_series(path)
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"[ref_vs_opt] ERROR: {exc}", file=sys.stderr)
            return 1
        for column, _, _ in PANELS:
            if column not in rows[-1]:
                print(f"[ref_vs_opt] ERROR: {path.name} has no column "
                      f"{column!r}", file=sys.stderr)
                return 1
        data.append((label, rows, colour))
        print(f"[ref_vs_opt] {label}: {len(rows)} rows from {path.name}")

    fig, axes = plt.subplots(2, 2, figsize=(6.05, 4.70), dpi=300)
    for ax, (column, _ylabel, title) in zip(axes.ravel(), PANELS):
        for label, rows, colour in data:
            steps = [r["step"] for r in rows]
            values = [r[column] * (SCALE if column == "heatflux_max_Wm2" else 1.0)
                      for r in rows]
            ax.plot(steps, values, lw=1.6, color=colour, label=label)
        if column == "heat_load_jcm2":
            ax.axhline(Q_TARGET, ls=(0, (1, 2)), lw=1.2, color="#333333",
                       zorder=1)
            ax.annotate(f"heat-load target {Q_TARGET:.1f} J/cm$^2$",
                        xy=(0.03, 0.93), xycoords="axes fraction",
                        fontsize=8.5, color="#333333", va="top")
        ax.set_xlabel("Particle-time step", fontsize=9.5, labelpad=2)
        ax.set_title(title, fontsize=10.0, pad=4)
        ax.grid(True, which="major", color="#DDDDDD", lw=0.6)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="both", labelsize=9.0, pad=2)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               fontsize=9.0, bbox_to_anchor=(0.5, 0.005))
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    out = FIG_DIR / "ref_vs_opt_dsmc_comparison.png"
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[ref_vs_opt] wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
