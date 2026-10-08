#!/usr/bin/env python3
"""Generate Chapter 4's performance-comparison figure from the run CSVs.

AXIOM: A results chapter that compares two configurations numerically in prose
must show the curves the numbers come from. Chapter 4 listed drag coefficient,
lift coefficient, g-load and heat load between the smooth and scalloped series
in one sentence with no figure, while the only plotted comparison was heat
flux; the reader could not see convergence, crossing or scatter behind any of
the quoted values.

PARAMETERS
    None. Output path is FIGDIR / "results_performance_comparison.png".

RETURNS
    Process exit code 0 on success, 1 on rejection.

EXCEPTIONS
    RuntimeError if the print scale, the inside-canvas check, the tick-gap
    check or the smallest printed text check fails, or if a drawn string
    contains the dash character the thesis forbids.

AXIOMS
    A1. Every value plotted here is READ FROM A DATA FILE at run time; the
        script prints the values it plotted so they can be checked against
        Chapter 4. Nothing is hard-coded.
    A2. The two runs sit at different trajectory conditions, so every legend
        entry carries its own run's altitude and velocity; comparing them as
        a controlled pair is an error the figure must make visible.
    A3. The figure is built at the exact print width, so the guard's scale is
        1.0 and a 9 pt label prints at 9 pt on paper.

DATA SOURCES
    stellarorion_program_proc/results/validation_smooth/validation_timeseries.csv
    stellarorion_program_proc/results/validation_scalloped/validation_timeseries.csv

CITATION
    Matplotlib 3.11.2 (stellarorion_program_proc/venv_validation),
    https://matplotlib.org/stable/
    ColorBrewer colourblind-safe qualitative palette (Paul Tol),
    https://personal.sron.nl/~pault/
"""

from __future__ import annotations

import sys

sys.path.insert(0, str((__import__("pathlib").Path(__file__).resolve().parent)))
import make_fignew as mfn  # noqa: E402  (shared print-fit guard and style)

import matplotlib.pyplot as plt  # noqa: E402

# WHY the four panels: Chapter 4's prose quotes exactly these four series at
# the common final step (drag coefficient, lift coefficient, g-load, drag
# force) alongside the heat-flux pair that already has its own figure. Four
# panels in two rows at WIDTH_FULL keeps the whole comparison on one printed
# block instead of one figure per page (paper-saving directive).
PANELS = (
    ("Drag coefficient", "cd", "Coefficient $C_d$", False),
    ("Lift coefficient", "cl", "Coefficient $C_l$", False),
    ("Deceleration load", "g_load", "Deceleration load (g)", False),
    ("Axial drag force", "drag_sum_N", "Drag force (N)", True),
)


def fig_performance_comparison() -> None:
    """Render the 2x2 smooth-versus-scalloped performance comparison.

    PURPOSE
        Plot drag coefficient, lift coefficient, deceleration load and axial
        drag force for both skin runs against particle-time step, so the
        step-2200 values quoted in Chapter 4 have a visible series behind
        them.

    PARAMETERS
        None. Reads both validation_timeseries.csv files at run time.

    RETURNS
        None. Writes FIGDIR / "results_performance_comparison.png".

    EXCEPTIONS
        RuntimeError propagated from make_fignew.save if the print-scale,
        tick-gap or 8 pt floor guard rejects the rendered figure.
    """
    sm = mfn.read_csv(mfn.RESULTS / "validation_smooth" / "validation_timeseries.csv")
    sc = mfn.read_csv(mfn.RESULTS / "validation_scalloped" / "validation_timeseries.csv")

    def col(rows, key):
        return [float(r["step"]) for r in rows], [float(r[key]) for r in rows]

    # WHY a shared legend below BOTH rows: per-axis loc="best" legends have
    # repeatedly been measured occluding data or tick labels on the rendered
    # page in this figure family; a legend outside the data region cannot
    # occlude data by construction (same pattern as fignew_heatflux).
    fig, axes = plt.subplots(2, 2, figsize=(mfn.WIDTH_FULL, mfn.WIDTH_FULL * 0.82))
    handles = None
    for ax, (title, key, ylabel, xlabel_on) in zip(axes.flat, PANELS):
        x1, y1 = col(sm, key)
        x2, y2 = col(sc, key)
        ax.plot(x1, y1, "-o", ms=3, lw=1.3, color=mfn.CB[0],
                label=f"smooth  {float(sm[0]['alt_km']):.2f} km, "
                      f"{float(sm[0]['vel_ms']):.0f} m/s")
        ax.plot(x2, y2, "-s", ms=3, lw=1.3, color=mfn.CB[1],
                label=f"scalloped  {float(sc[0]['alt_km']):.2f} km, "
                      f"{float(sc[0]['vel_ms']):.0f} m/s")
        # Bottom row carries the shared x label; top row would repeat it.
        mfn.style(ax, title,
                  "Particle-time step" if xlabel_on else "",
                  ylabel)
        # WHY MaxNLocator(4): seven absolute-width four-digit tick labels
        # (100..2200) measured wider than the shrunken axes, so the tight
        # crop grew on every fit attempt and the loop oscillated 1523..1595 px
        # against a 1571 px target until it gave up (fit failure 2026-10-08).
        # Four ticks keep the labels inside the axes at every scale.
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        if not xlabel_on:
            # Top-row tick numbers repeat the bottom row's for no information.
            ax.tick_params(labelbottom=False)
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()

    # WHY y=0 in the drag-force panel: values run 45 kN and up with no
    # negative side; the guard measures tick gaps, and a bare autoscale
    # placed the top tick label into the panel title's pad.
    axes.flat[3].margins(y=0.12)
    axes.flat[3].set_ylim(bottom=0)

    # Anchor deeper than the one-row figures (-0.055): two axes rows push the
    # bottom xlabel plus tick labels roughly 0.45 in below the axes, and the
    # first legend row was measured rising into them at -0.055.
    fig.legend(handles, labels, fontsize=mfn.PLAIN_TEXT_PT, loc="lower center",
               ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.115))
    fig.tight_layout()
    mfn.save(fig, "results_performance_comparison.png", mfn.WIDTH_FULL)

    # Printed so every number in the Chapter 4 prose can be checked against
    # the same source the figure used.
    print("    conditions: "
          f"smooth {float(sm[0]['alt_km']):.4f} km {float(sm[0]['vel_ms']):.1f} m/s "
          f"Mach {float(sm[0]['mach']):.4f} | "
          f"scalloped {float(sc[0]['alt_km']):.4f} km {float(sc[0]['vel_ms']):.1f} m/s "
          f"Mach {float(sc[0]['mach']):.4f}")
    for key in ("cd", "cl", "g_load", "drag_sum_N", "heat_load_jcm2"):
        print(f"    {key:14s} step2200 scalloped {float(sc[-1][key]):.6g} "
              f"vs smooth {float(sm[-1][key]):.6g}")
    gs = [float(r["g_load"]) for r in sc]
    print(f"    scalloped g series: first {gs[0]:.4f} at step "
          f"{float(sc[0]['step']):.0f}, last {gs[-1]:.4f}")


def main() -> int:
    """Render every figure in this module.

    PARAMETERS
        None (argv unused).

    RETURNS
        0 on success. A guard rejection raises and exits non-zero.

    EXCEPTIONS
        RuntimeError from any figure guard.
    """
    fig_performance_comparison()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
