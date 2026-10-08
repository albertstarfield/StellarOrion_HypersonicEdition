#!/usr/bin/env python3
"""Generate Chapter 4's performance-comparison figure from the run CSVs.

AXIOM: A results chapter that compares two configurations numerically in prose
must show the curves the numbers come from. Chapter 4 listed drag coefficient,
lift coefficient, g-load and heat load between the smooth and scalloped series
in one sentence with no figure, while the only plotted comparison was heat
flux; the reader could not see convergence, crossing or scatter behind any of
the quoted values.

PARAMETERS
    None. Output paths are FIGDIR / "results_performance_comparison.png"
    and FIGDIR / "results_tps_backface.png".

RETURNS
    Process exit code 0 on success, 1 on rejection.

EXCEPTIONS
    RuntimeError if the print scale, the inside-canvas check, the tick-gap
    check or the smallest printed text check fails, or if a drawn string
    contains the dash character the thesis forbids.

AXIOMS
    A1. The performance series are READ FROM A DATA FILE at run time and
        the script prints every value it plotted so Chapter 4 can be
        checked against the same source. The backface figure's constants
        are not derivable from any CSV: they are measured values recorded
        once in the validation-gate record of the repository README and in
        the Ada types, and each carries its PROVENANCE in the function
        docstring. Nothing in this module is estimated or fitted.
    A2. The two runs sit at different trajectory conditions, so every legend
        entry carries its own run's altitude and velocity; comparing them as
        a controlled pair is an error the figure must make visible.
    A3. The figure is built at the exact print width, so the guard's scale is
        1.0 and a 9 pt label prints at 9 pt on paper.

DATA SOURCES
    stellarorion_program_proc/results/validation_smooth/validation_timeseries.csv
    stellarorion_program_proc/results/validation_scalloped/validation_timeseries.csv
    repository README.md validation-gate record (backface figure: gate line
        "Backface temp : 9.55662E+02 K" and the SiC/IRVE-3 areal
        capacitance table)
    stellarorion_types.ads (limits: KAPTON_MAX_TEMP 773.0,
        IRVE3_FTPS_STRUCT_LIMIT_K 523.15)

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
    # WHY True (image audit 2026-10-08): this is a bottom-row panel, and the
    # False flag both blanked its shared x-axis label and hid its tick
    # numbers, so the rendered panel showed bare ticks with no numbers at
    # all while its neighbour printed both. Bottom row carries the x axis;
    # only the top row suppresses it.
    ("Deceleration load", "g_load", "Deceleration load (g)", True),
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


def fig_tps_backface() -> None:
    """Render the active-TPS backface violation against both material limits.

    PURPOSE
        Chapter 4's Thermal Constraint Violation paragraph quotes 955.66 K
        against the 773 K Kapton limit and the 523.15 K IRVE-3 structural
        limit, and contrasts the active 6.35 mm layup with the superseded
        25.4 mm silicon-carbide slab, with no figure behind any of those
        numbers.

    PARAMETERS
        None. The two temperatures and the two areal capacitances are
        measured constants recorded in the validation-gate record (see
        PROVENANCE); they are not fitted, interpolated or re-derived here.

    RETURNS
        None. Writes FIGDIR / "results_tps_backface.png".

    EXCEPTIONS
        RuntimeError propagated from make_fignew.save if the print-scale,
        tick-gap or 8 pt floor guard rejects the rendered figure.

    PROVENANCE
        955.66 K and 328.1 K: validation-gate record in the repository
        README, gate line "Backface temp : 9.55662E+02 K" and its
        areal-capacitance table (SiC 25.4 mm, rho c_p delta 41 016
        J m^-2 K^-1, 328.1 K PASS; IRVE-3 6.35 mm, 1 760, 955.7 K FAIL;
        recorded as "Reproduced analytically to 3 decimals against the
        solver's own 955.662 K"). The four-way predicate itself is
        Is_Survivable in stellarorion_physics.adb.
        773 K: KAPTON_MAX_TEMP, stellarorion_types.ads.
        523.15 K: IRVE3_FTPS_STRUCT_LIMIT_K, stellarorion_types.ads;
        Chapter 4 cites old2013irve3postflight for it.
        The printed deltas cross-check the Chapter 4 prose values 182.7 K
        and 432.5 K.
    """
    # WHY constants declared here: these values live in prose artefacts
    # (the README gate record and Ada source constants), not in a CSV, so
    # they carry their source in PROVENANCE instead of being parsed at run
    # time; the printed deltas are the mechanical check against the text.
    temps = (328.1, 955.66)
    caps = (41016.0, 1760.0)
    # WHY these short three-line forms: at the print width the two-line
    # long forms sat -7.97 pt apart (tick centres are fixed at 1.53 in by
    # the x positions; guard failure 2026-10-09), and the areal-capacity
    # strings above the bars collided with the upper-left legend by
    # 36.78 pt. Moving the capacity into the third tick line attaches it
    # to the stack it describes, keeps the upper zone to value labels
    # only, and the widest lines (1.20 in + 1.11 in) leave ~27 pt between
    # the blocks. The full descriptions live in the caption.
    labels = ("LOFTID baseline\nSiC, 25.4 mm\n$\\rho c_p\\delta$ = 41 016",
              "IRVE-3 F-TPS\n5-ply, 6.35 mm\n$\\rho c_p\\delta$ = 1 760")
    kapton_limit = 773.0
    struct_limit = 523.15

    # WHY a narrow single panel at WIDTH_NARROW: the paper-saving directive
    # (native width 0.80 textwidth, printed at scale 1.0) and one stack
    # comparison needs no more area than this.
    fig, ax = plt.subplots(figsize=(mfn.WIDTH_NARROW, mfn.WIDTH_NARROW * 0.62))
    bars = ax.bar((0, 1), temps, width=0.5, color=(mfn.CB[0], mfn.CB[2]),
                  zorder=3)
    # WHY zorder 4 (image audit 2026-10-09): at zorder 2 the lines sat
    # UNDER the bars (bar patches paint at 3), so both limits vanished
    # across the red bar's 237 px width and the figure read as if the
    # limits stopped at the data. A limit line must cross the bars it
    # judges, so it paints above them; the value labels below are clamped
    # clear of the 773 K line for the same reason.
    ax.axhline(kapton_limit, color="#212121", ls="--", lw=1.2, zorder=4,
               label="Kapton adhesive limit, 773 K")
    ax.axhline(struct_limit, color="#757575", ls=":", lw=1.4, zorder=4,
               label="IRVE-3 structural limit, 523.15 K")
    # WHY this title length: at 12 pt the previous "…the two candidate
    # stacks" measured 4.256 in of ink against a 4.409 in canvas, so the
    # unshrinkable text drove the fit loop to its asymptote (4.493 in)
    # and the save failed (probe 2026-10-09). "…of the two stacks" is
    # 3.38 in, leaving the tight crop inside the print width.
    mfn.style(ax, "Backface temperature of the two stacks",
              "", "Backface temperature (K)")
    # WHY 1400 (was 1240, image audit 2026-10-09): at 1240 the red bar
    # top reached y=214 px while the legend's second row ended at y=230,
    # so 346 dark glyph pixels of "…523.15 K" sat ON the red fill. The
    # legend is anchored to the axes box, so only the scale moves: at
    # 1400 the red top falls to y=253, 23 px below the legend, and the
    # upper zone still belongs to legend plus value labels alone. The
    # tight crop must not grow past the print width (same failure mode
    # as the performance figure's 4-digit ticks, 2026-10-08).
    ax.set_ylim(0.0, 1400.0)
    # WHY exactly these five ticks (image audit 2026-10-09, defect: only
    # 0/500/1000 rendered): the default MultipleLocator(250) inside a
    # 0..1400 window would also emit 1250 and 1400, whose labels crowd the
    # legend zone; the spec is five labels at 0/250/500/750/1000, so the
    # locator is replaced with an explicit list rather than a step.
    ax.set_yticks([0.0, 250.0, 500.0, 750.0, 1000.0])
    ax.set_xlim(-0.62, 1.62)
    ax.set_xticks((0, 1))
    # WHY SCRIPT_SAFE_PT, not TICK_PT: the third tick line carries mathtext
    # scripts (rho c_p delta) that print at SHRINK_FACTOR 0.7, so the
    # parent must be >= 11.43 pt for the 8 pt floor.
    ax.set_xticklabels(labels, fontsize=mfn.SCRIPT_SAFE_PT)

    # WHY value labels inside the bars: above-bar labels collided with the
    # upper-left legend by 8.70 x 3.13 pt, and at temp - 16 the legend's
    # second row still reached them (22.83 x 5.85 pt; guard failures
    # 2026-10-09). The legend measures down to ~895 in axis units, so the
    # labels sit at temp - 180 (white bold, PLAIN_TEXT_PT) as long as
    # that stays below the limit lines. WHY the min() clamp (image audit
    # 2026-10-09): with the lines raised above the bars the 773 K dashes
    # (y=314 px) would have struck the top edge of "955.66 K" (its label
    # top measured on the line itself at temp - 180); capping the top at
    # kapton_limit - 45 puts the digits ~15 px below the dashes while
    # leaving the short 328.1 K bar untouched (min selects temp - 180).
    for bar, temp in zip(bars, temps):
        cx = bar.get_x() + bar.get_width() / 2.0
        ax.text(cx, min(temp - 180.0, kapton_limit - 45.0), f"{temp:g} K",
                ha="center", va="top", fontsize=mfn.PLAIN_TEXT_PT,
                fontweight="bold", color="white", zorder=5)

    # WHY upper left: the tall bar and its two annotation lines occupy the
    # upper right, and the short bar leaves the upper left free; a legend
    # there cannot occlude data by construction (measured 2026-10-09).
    ax.legend(loc="upper left", fontsize=mfn.PLAIN_TEXT_PT, frameon=False)
    fig.tight_layout()
    mfn.save(fig, "results_tps_backface.png", mfn.WIDTH_NARROW)

    # Printed so the Chapter 4 prose can be checked against the same
    # source the figure used.
    print(f"    tps_backface: SiC 25.4 mm {temps[0]:g} K "
          f"(rho c_p delta {caps[0]:.0f}) | IRVE-3 6.35 mm "
          f"{temps[1]:g} K ({caps[1]:.0f})")
    print(f"    {temps[1]:.2f} - {kapton_limit:.0f} = "
          f"{temps[1] - kapton_limit:.2f} K (prose 182.7) | "
          f"{temps[1]:.2f} - {struct_limit} = "
          f"{temps[1] - struct_limit:.2f} K (prose 432.5)")


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
    fig_tps_backface()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
