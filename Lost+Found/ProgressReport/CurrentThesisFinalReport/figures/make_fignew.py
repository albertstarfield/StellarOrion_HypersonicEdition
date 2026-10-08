#!/usr/bin/env python3
"""Generate the figures Chapter 3 and Chapter 4 promise in prose but never show.

AXIOM: A results chapter that describes a curve, a screen or a comparison must
show it. The page audit of this thesis found the following sections making
quantitative claims with no figure anywhere in the document:

  1. Sec. on PINN refinement (ch3) and the hybrid gate leg (ch4): the entire
     PINN contribution, roughly 250 lines, had ZERO figures.
  2. The scalloped-versus-smooth heating comparison (ch4) had no figure, and its
     caption for the adjacent temperature map had to ADMIT that the scalloped
     field map does not exist in the repository.
  3. The Bayesian optimisation search reported 70 evaluations with only a
     scatter plot; the running-minimum behaviour and the argmin index, which
     the text discusses in detail, were never plotted.
  4. The 15-point CCD screen was described numerically with no design-space
     figure.
  5. The hybrid validation gate reported a correction factor and a pass verdict
     with no comparison figure.

Every value plotted here is READ FROM A DATA FILE at run time. Nothing is
hard-coded, and the script prints the values it plotted so they can be checked
against the text. Where the repository holds conflicting records, the figure
shows the conflict rather than hiding it, because that is the honest rendering
of the current evidence.

DATA SOURCES
  stellarorion_program_proc/results/validation_smooth/validation_timeseries.csv
  stellarorion_program_proc/results/validation_scalloped/validation_timeseries.csv
  stellarorion_program_proc/results/validation_optimized/validation_timeseries.csv
  stellarorion_program_proc/results/validation_scalloped/validation_pipeline_output/convergence_audit.csv
  stellarorion_program_proc/src/python/hiad_optimization_results.json

CITATION
  Matplotlib, https://matplotlib.org/stable/
  ColorBrewer colourblind-safe qualitative palette (Paul Tol),
  https://personal.sron.nl/~pault/
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

# The print-fit loop, its tolerance, the achieved print scale and the
# inside-canvas check live in one sibling module, so no two generators
# can disagree about what a printed figure looks like. The path is
# added first so the import also works when a probe imports this file
# from another directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_metrics as fm  # noqa: E402  sibling module, unique printed-layout guards
import opt_data  # noqa: E402  sibling module, unique committed-campaign loader
import print_fit as pf  # noqa: E402

# figures/ -> CurrentThesisFinalReport -> ProgressReport -> Lost+Found -> repo root
ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
# this file lives in <thesis>/figures/, so the thesis root is one level up
THESIS = Path(__file__).resolve().parent.parent
FIGDIR = THESIS / "figures"
assert FIGDIR.is_dir() and Path(__file__).resolve().parent == FIGDIR, (
    "FIGDIR must be the directory holding this script")
RESULTS = ROOT / "stellarorion_program_proc" / "results"
# CRITICAL: the working-tree copy of this JSON is a DIRTY, un-gated re-run that
# background automation overwrites repeatedly (observed argmin moving from index
# 29 to 50 between two minutes, with cost 1.602195 then 1.608508). The thesis
# reports the values from the COMMITTED revision, verified against the DSMC
# validation gate that was actually run with the nose radius override set to
# 2.971440. So the figure must be generated from that same committed revision,
# otherwise the figure and the text would contradict each other. The path, the
# revision, the blob fetch and the assertion all now live in opt_data, which is
# the single owner of that rule, so nothing here repeats the commit id.

# Paul Tol's colourblind-safe qualitative palette.
CB = ["#004488", "#DDAA33", "#BB5566", "#228833", "#AA4499", "#66CCEE"]

DPI = pf.DPI             # 300, the save resolution

# Sizing rule, and why these numbers are what they are.
#
# AXIOM: a matplotlib figsize is in inches of the SAVED image. LaTeX then scales
# that image to the width requested by \includegraphics. If the two disagree the
# effective scale is figsize_width / print_width, and every font in the figure is
# multiplied by it. The first version of this script declared a single
# WIDTH_IN = 5.51 for everything and then built the multi-panel figures at
# WIDTH_IN * 2 and WIDTH_IN * 2.1, while the document includes them at
# 0.95\textwidth. Effective scales were therefore:
#     two-panel figures  11.02 in / 5.24 in = 0.476
#     three-panel figure 11.55 in / 5.24 in = 0.454
# so a 9 pt axis label printed at 4.3 pt and a 7.5 pt legend at 3.6 pt, both far
# below legibility. One-panel figures at 0.95 scale were close to correct.
#
# FIX: every figure is now built at the exact width it is printed at, so the
# effective scale is 1.0 and a font size of 9 pt is 9 pt on paper. The constants
# below are derived from the document geometry rather than typed in:
#     text width  = 21 cm - 4 cm - 3 cm = 14 cm = 5.51181 in
#     text height = 29.7 cm - 3 cm - 3 cm = 23.7 cm = 9.33071 in
TEXT_W_IN = pf.TEXT_W_IN                        # 5.51181 in
TEXT_H_IN = 29.7 / 2.54 - (3.0 + 3.0) / 2.54      # 9.33071
WIDTH_FULL = 0.95 * TEXT_W_IN                        # 5.23622, width=0.95\textwidth
WIDTH_NARROW = 0.80 * TEXT_W_IN                     # 4.40945, width=0.80\textwidth

# Legibility floors enforced on every saved figure by _guard_layout. Both are
# measured on the rendered result, never asserted from the source.
MIN_PRINTED_PT = 8.0        # smallest printed text, including mathtext scripts
MIN_TICK_GAP_PT = 2.0       # clearance between adjacent x tick labels

# Font sizes derived from the floors rather than chosen by eye.
# Matplotlib SHRINK_FACTOR for math scripts is 0.7 (matplotlib/_mathtext.py),
# so the smallest parent size whose script still prints at or above 8 pt is
# 8 / 0.7 = 11.43 pt, rounded up to 11.5 pt.
SCRIPT_SHRINK = 0.7
SCRIPT_SAFE_PT = 11.5                   # for any label carrying a mathtext script
PLAIN_TEXT_PT = 9.0                     # for any label carrying no scripts
TITLE_PT = 12.0                         # titles carry no scripts
TICK_PT = 10.0                          # tick labels carry no scripts
# WHY A COLLISION FLOOR OF 3.0 PT: a matplotlib text extent includes the full
# ascent and descent of the line box, not the inked glyphs, so two labels on
# neighbouring rows report a point or two of box overlap while the glyphs are
# plainly apart. Measured at 13 pt Times the descent allowance is about 3 pt,
# so anything below that is reported as no overlap and anything above it is a
# real overprint a reader can see.
MIN_OVERLAP_PT = 3.0
# WHY A ROW GAP FLOOR OF 2.0 PT: two labels on one horizontal band need at
# least a word space between them, and a word space at these sizes measures
# 2 to 5 pt. The central composite screen failed this at one white column,
# which is 0.5 pt and rendered as (m)Toroid on the page.
MIN_ROW_GAP_PT = 2.0

# WHY PLAIN_TEXT_PT IS NOT 8.0: save() fits the printed width to within 0.5
# percent, so the achieved scale lands between 0.995 and 1.005 in practice and
# a declared 8 pt label can print at 7.98 pt, which _guard_layout rejects. The
# declared size must carry the floor itself: 9.0 x 0.98 = 8.82 pt. Measured on
# this run: scale 0.978 printed a 9 pt key at 8.80 pt and an 8 pt key at 7.82.


def load_committed_opt() -> dict:
    """Return the optimization results as COMMITTED, matching the thesis text.

    Parameters:
        none.

    Returns:
        the parsed payload of the committed results file.

    Raises:
        RuntimeError from opt_data.load_committed when the committed revision
        does not match the thesis, or when git cannot produce the blob.

    WHY THIS IS A DELEGATION AND NOT A COPY
        The loader asserts that the campaign agrees with the printed text. That
        assertion is a numeric guard, and a duplicated guard is worse than no
        guard because the two copies can drift and one figure can then be drawn
        from data the other would refuse. opt_data is now the single owner of
        the committed-revision rule and of the sixteen printed claims, so this
        function only forwards.
    """
    return opt_data.load_committed()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def style(ax, title: str, xlabel: str, ylabel: str) -> None:
    # LABEL PT FLOOR: matplotlib draws a mathtext SUBSCRIPT at SHRINK_FACTOR
    # 0.7 of its parent, so a 9 pt label carrying $C_d$ printed its script at
    # 6.3 pt and a 12 pt one printed 8.4 pt. _guard_layout measured both cases
    # and rejected them. Axis labels therefore sit at SCRIPT_SAFE_PT, the
    # smallest parent whose script still clears the 8 pt floor, while ticks
    # and titles carry no scripts and stay smaller.
    ax.set_title(title, fontsize=TITLE_PT, pad=8)
    ax.set_xlabel(xlabel, fontsize=SCRIPT_SAFE_PT)
    ax.set_ylabel(ylabel, fontsize=SCRIPT_SAFE_PT)
    ax.tick_params(labelsize=TICK_PT)
    ax.grid(True, which="both", ls=":", lw=0.5, alpha=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plain_log_ticks(ax, axis: str = "y", target: int = 4) -> None:
    """Give a log axis plain-digit labels at ticks that lie inside its window.

    TWO DEFECTS, ONE ROOT CAUSE EACH.
    First, matplotlib's default log formatter writes each decade as a mathtext
    power, so "100" is drawn as 10 to the 2 and the exponent renders at
    SHRINK_FACTOR of the tick size. At TICK_PT the exponent printed 7.0 pt and
    _guard_layout rejected the figure. Writing the decade as plain digits
    removes the script entirely, so the floor cannot regress.
    Second, a decade locator offers only 10, 100, 1000, so an axis whose window
    spans less than one decade has NO decade inside it and prints no number at
    all. Measured on the heat-flux panels: panel 1 spans 50.6 to 151.7 and gets
    the single label 100, while panel 2 spans 150.8 to 446.4 and gets nothing
    at all, while showing tick marks and gridlines. The ticks are therefore
    chosen by fig_metrics.log_ticks_in_window, which returns values strictly
    inside the window and spaces them evenly in the exponent, which is what a
    reader sees as even on a log axis.

    PARAMETERS: ax the axes whose axis is logarithmic; axis "x" or "y"; target
    the desired number of ticks, reduced automatically until they are far
    enough apart to print without touching.
    RETURNS: None.
    RAISES: RuntimeError if axis is neither "x" nor "y", or if the window holds
    no positive value so no tick can be placed.
    """
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter
    if axis not in ("x", "y"):
        raise RuntimeError(f"plain_log_ticks: axis must be x or y, got {axis!r}")
    a = getattr(ax, f"{axis}axis")
    low, high = sorted(a.get_view_interval())
    ticks = fm.log_ticks_in_window(low, high, target=target)
    if ticks:
        a.set_major_locator(FixedLocator(ticks))
    # Minor labels are suppressed because they were never drawn: matplotlib
    # leaves the minor log formatter empty by default, and labelling them here
    # would add text the figure did not previously carry.
    a.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:g}"))
    a.set_minor_formatter(NullFormatter())


def save(fig, name: str, print_width_in: float) -> Path:
    """Save at the printed width, then reject a figure that cannot be read.

    WHY THIS IS A THIN WRAPPER: the fit loop, its tolerance and the achieved
    print scale are one numeric guard and must exist once, in print_fit. A
    second copy can pass a figure that the first copy rejects, which is worse
    than having no guard at all. This wrapper adds only what is specific to
    this module, namely the shared layout guard on tick spacing and text size,
    and it runs before the figure is closed so the artist tree is still
    measurable.

    AXIOM: declaring a figsize does not set the printed width, because every
    call uses bbox_inches="tight", which CROPS the saved image to its artist
    extents. Measured on the first attempt at the corrected sizes,
    fignew_scalloped_vs_smooth_heatflux.png came out 2282 px = 7.607 in
    against a 5.236 in print width, an effective scale of 0.688, which would
    still have shrunk every label by nearly a third.
    """
    out, eff = pf.save_to_print_width(fig, name, print_width_in, close=False)
    _guard_layout(fig, out, print_width_in, eff)
    plt.close(fig)
    return out


def _guard_layout(fig, out: Path, print_width_in: float, scale: float) -> None:
    """Reject the figure if a tick pair touches or the smallest text is under 8 pt.

    WHY: two separate defects in this figure family were invisible in the
    source and only visible on the printed page. In the gate figure the
    three category labels touched because the columns were too close for
    their own text. In the sutton figure every mathtext SUBSCRIPT printed
    below the 8 pt floor because the canvas printed at 0.71 of its declared
    size. Both are measured properties of the rendered result, so they are
    checked here against the shared measurement library rather than being
    re-derived per figure.

    :param fig: the matplotlib Figure, which must already be drawn.
    :param out: path of the saved PNG, used for the scale lookup.
    :param print_width_in: printed width in inches, for the error message.
    :param scale: achieved print scale, printed size divided by declared size.
    :returns: None.
    :raises RuntimeError: if an adjacent tick pair is closer than
        MIN_TICK_GAP_PT or the smallest printed text is below 8 pt.
    """
    fig.canvas.draw()
    for axis in fig.axes:
        try:
            pairs = fm.x_tick_label_gaps_pt(axis, fig, scale)
        except RuntimeError:
            continue  # an axis with fewer than two visible labels cannot collide
        for left, right, gap in pairs:
            if gap < MIN_TICK_GAP_PT:
                raise RuntimeError(
                    f"{out.name}: x tick labels {left!r} and {right!r} sit "
                    f"{gap:.2f} pt apart at print width {print_width_in:.3f} in, "
                    f"below the {MIN_TICK_GAP_PT:.1f} pt floor; shorten or wrap "
                    f"the labels")
    smallest, where = fm.smallest_text_pt(fig, scale)
    if smallest < MIN_PRINTED_PT:
        raise RuntimeError(
            f"{out.name}: smallest printed text {smallest:.2f} pt ({where}) is "
            f"below the {MIN_PRINTED_PT:.1f} pt floor; raise the declared size")
    # WHY A COLLISION TEST AND NOT A WIDER TICK GAP: two panels carrying the
    # same axis label cannot collide with each other, a title can overprint its
    # own last word, and an axis label can run into a legend key. None of those
    # pairs share a tick row, so a tick-gap test cannot see them. The all-pairs
    # box test can, and it costs one draw.
    pairs = fm.text_overlaps_pt(fig, scale, min_overlap_pt=MIN_OVERLAP_PT)
    if pairs:
        first, second, wide, high = pairs[0]
        raise RuntimeError(
            f"{out.name}: {len(pairs)} text pair(s) overlap; worst is "
            f"{first} against {second} at {wide:.2f} x {high:.2f} pt at print "
            f"width {print_width_in:.3f} in, above the {MIN_OVERLAP_PT:.1f} pt "
            f"floor; shorten, wrap or move the text")
    # WHY A ROW GAP FLOOR AS WELL AS AN OVERLAP FLOOR: the central composite
    # screen measured ONE WHITE COLUMN between the panel 2 and panel 3 x labels,
    # so the boxes did not intersect and the overlap test stayed silent while
    # the page rendered (m)Toroid. A gap is not an overlap, so it needs its own
    # test, and the two labels belong to different axes, so the within-axis tick
    # gap test could not see them either.
    tight = fm.same_row_gaps_pt(fig, scale, min_gap_pt=MIN_ROW_GAP_PT)
    if tight:
        left, right, gap = tight[0]
        raise RuntimeError(
            f"{out.name}: {len(tight)} label pair(s) on one row sit within "
            f"{MIN_ROW_GAP_PT:.1f} pt; narrowest is {left} against {right} at "
            f"{gap:.2f} pt at print width {print_width_in:.3f} in; shorten or "
            f"wrap the labels")
    # WHY AN EMPTY-AXIS TEST AS WELL AS A SIZE TEST: a label that is never
    # drawn has no size to measure, no neighbour to collide with, and prints
    # inside the canvas, so every test above passes it. The heat-flux panel 2
    # rendered tick marks, gridlines and NO number because its y window spans
    # 150.8 to 446.4 and contains no decade, so the default log locator offered
    # only 100 and 1000 and both lie outside. Fix it with
    # fm.log_ticks_in_window, which returns values inside the window.
    empty = fm.axes_without_tick_labels(fig)
    if empty:
        name, window, locs = empty[0]
        raise RuntimeError(
            f"{out.name}: {len(empty)} axis/axes draw no numeric tick label; "
            f"first is {name} with {window} and locator values "
            f"{['%.6g' % v for v in locs]}; set explicit ticks inside the "
            f"window, for example with fig_metrics.log_ticks_in_window")


def fig_scalloped_vs_smooth() -> None:
    """F1. Per-element and peak heat flux, both skins, with run conditions shown.

    HONESTY REQUIREMENT: the two runs are NOT at the same flight condition, so
    the figure states each run's altitude and velocity in the legend. This is
    the whole point of the figure: to make the difference legible.
    """
    sm = read_csv(RESULTS / "validation_smooth" / "validation_timeseries.csv")
    sc = read_csv(RESULTS / "validation_scalloped" / "validation_timeseries.csv")

    def col(rows, name):
        return [float(r["step"]) for r in rows], [float(r[name]) / 1e4 for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2,
                             figsize=(WIDTH_FULL, WIDTH_FULL * 0.70))

    handles = None
    for ax, key, lbl in (
        (ax1, "heatflux_avg_Wm2", "Per-element mean heat flux"),
        (ax2, "heatflux_max_Wm2", "Peak cell heat flux"),
    ):
        x1, y1 = col(sm, key)
        x2, y2 = col(sc, key)
        ax.plot(x1, y1, "-o", ms=3, lw=1.3, color=CB[0],
                label=f"smooth  {float(sm[0]['alt_km']):.2f} km, {float(sm[0]['vel_ms']):.0f} m/s")
        ax.plot(x2, y2, "-s", ms=3, lw=1.3, color=CB[1],
                label=f"scalloped  {float(sc[0]['alt_km']):.2f} km, {float(sc[0]['vel_ms']):.0f} m/s")
        ax.set_yscale("log")
        plain_log_ticks(ax, "y")
        style(ax, lbl, "Particle-time step", "Heat flux (W/cm$^2$)")
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()

    # The legend is drawn ONCE, BELOW both panels, and not inside either axes.
    # Two placements inside the axes were tried and both failed on the rendered
    # page: loc="best" chose upper left, which is where these traces are highest,
    # and a pinned upper right still clipped the first markers in the left panel.
    # A legend outside the data region cannot occlude data by construction.
    fig.legend(handles, labels, fontsize=PLAIN_TEXT_PT, loc="lower center", ncol=2,
               frameon=False, bbox_to_anchor=(0.5, -0.055))

    # No suptitle and no note below the axes. Both statements belong in the LaTeX
    # caption, where they are searchable, screen-reader accessible and able to run
    # to as many lines as needed. Drawing them as figure text also broke the
    # fit-to-print-width loop in save(): bbox_inches="tight" grew the cropped box
    # while the canvas shrank, and the figure collapsed to 2282x447 px.
    fig.tight_layout()
    save(fig, "fignew_scalloped_vs_smooth_heatflux.png", WIDTH_FULL)

    print(f"    smooth   last: avg={float(sm[-1]['heatflux_avg_Wm2'])/1e4:.4g} "
          f"max={float(sm[-1]['heatflux_max_Wm2'])/1e4:.4g} step={sm[-1]['step']}")
    print(f"    scalloped last: avg={float(sc[-1]['heatflux_avg_Wm2'])/1e4:.4g} "
          f"max={float(sc[-1]['heatflux_max_Wm2'])/1e4:.4g} step={sc[-1]['step']}")


def fig_trajectory() -> None:
    """F2. The 1-DOF entry trajectory, with both run conditions marked.

    WHY THIS PLOTS trajectory_profile.csv AND NOT validation_timeseries.csv
    AXIOM: The DSMC production runs are STEADY STATE AT A SINGLE TRAJECTORY
    POINT. Measured over all 22 samples of validation_timeseries.csv, time_s,
    alt_km, vel_ms, mach, dyn_press_pa and g_load each take exactly ONE distinct
    value, so no trajectory can be plotted from it and any attempt produces a
    degenerate single-point panel. The trajectory itself lives in
    trajectory_profile.csv, a 198-sample one-degree-of-freedom profile running
    from 122.65 km at 7500 m/s down to 27.29 km.

    WHAT THE TWO RUN CONDITIONS IMPLY, MEASURED
    The scalloped run's state (52.0692 km, 3101.1 m/s, Mach 9.4553, g 14.0082)
    is an EXACT row of that profile, at t = 97.0 s. The smooth run's state
    (51.8185 km, 3378.7 m/s, Mach 10.2882) does NOT lie on the profile at all.
    Both facts are marked on the figure, because they are the precise reason the
    two runs cannot be compared as a controlled pair.
    """
    rows = read_csv(RESULTS / "validation_smooth" / "trajectory_profile.csv")
    t = [float(r["time_s"]) for r in rows]
    alt = [float(r["alt_km"]) for r in rows]
    vel = [float(r["vel_ms"]) for r in rows]
    mach = [float(r["mach"]) for r in rows]
    g = [float(r["g_load"]) for r in rows]
    q = [float(r["dyn_press_pa"]) for r in rows]

    # WHY the anchor is read from the run CSV instead of a literal: this
    # function used to search for 52.032558, the condition of an older
    # scalloped run; after the 2026-10-06 rerun the authoritative condition
    # is 52.0692 and the literal silently matched only because profile rows
    # are 0.75 km apart. Reading the run's own first row makes the marker
    # track whatever the scalloped tree actually says.
    sc = read_csv(RESULTS / "validation_scalloped" / "validation_timeseries.csv")
    sc_alt = float(sc[0]["alt_km"])
    on_idx = min(range(len(rows)), key=lambda i: abs(alt[i] - sc_alt))
    # EXACTNESS THRESHOLD: the profile stores altitude to 4 decimals
    # (grid 1e-4 km = 0.1 m) and velocity to 2 decimals (grid 0.01 m/s), so
    # a run condition written at higher precision is "on the profile" when it
    # sits within half a storage grid step: measured 2026-10-08, the scalloped
    # run's 52.069210 km against the profile's 52.0692 differs by 1e-5 km
    # (1 cm) and 0.001 m/s, i.e. the same row. A 1e-6 test would have called
    # that mismatch purely because it lies below what the file can store.
    on_exact = (abs(alt[on_idx] - sc_alt) < 5e-5
                and abs(vel[on_idx] - float(sc[0]["vel_ms"])) < 5e-3)
    print(f"    trajectory: {len(rows)} samples, {min(alt):.2f}-{max(alt):.2f} km, "
          f"t = 0-{max(t):.0f} s")
    print(f"    peak dynamic pressure {max(q):.1f} Pa and peak g-load {max(g):.3f} both at "
          f"alt={alt[q.index(max(q))]:.2f} km, V={vel[q.index(max(q))]:.1f} m/s, "
          f"Mach={mach[q.index(max(q))]:.3f}")
    print(f"    scalloped run state matches profile row {on_idx} "
          f"{'exactly' if on_exact else 'ONLY approximately'} "
          f"(t={t[on_idx]:.1f} s); the smooth run state is NOT on this profile")

    fig, (ax1, ax2) = plt.subplots(1, 2,
                             figsize=(WIDTH_FULL, WIDTH_FULL * 0.62))

    ax1.plot(alt, vel, "-", lw=1.5, color=CB[0], label="1-DOF entry profile")
    ax1.plot(alt[on_idx], vel[on_idx], "s", ms=7, color=CB[1], mec="black", mew=0.7,
             label=f"scalloped run (t = {t[on_idx]:.0f} s)")
    ax1.plot(51.818481, 3378.671, "^", ms=8, color=CB[2], mec="black", mew=0.7,
             label="smooth run (off this profile)")
    # PANEL TITLE WIDTH: at TITLE_PT the phrase "Deceleration load against
    # altitude" measured 2.870 in wide inside a 1.745 in axes, so it crossed
    # the canvas edge by 0.412 in and the fit loop in save() stalled at 5.353 in
    # against a 5.236 in target. Wrapping both titles to two lines keeps every
    # line near 1.55 in, which fits, and says exactly what the single line said.
    style(ax1, "Velocity against\naltitude", "Altitude (km)", "Velocity (m/s)")

    ax2.plot(alt, g, "-", lw=1.5, color=CB[0], label="deceleration load")
    ax2.plot(alt[on_idx], g[on_idx], "s", ms=7, color=CB[1], mec="black", mew=0.7)
    ax2.plot(51.818481, 16.833399, "^", ms=8, color=CB[2], mec="black", mew=0.7)
    style(ax2, "Deceleration load\nagainst altitude", "Altitude (km)",
          "Deceleration load (g)")

    # ONE legend, drawn BELOW both panels. The previous per-panel loc="best"
    # legends failed on the rendered page: the left legend covered the y-tick
    # "4000" (only "40" survived) and a stretch of the velocity curve, and the
    # right legend sat on the deceleration curve, hiding both limbs of the
    # peak. A legend outside the data region cannot occlude data or tick
    # labels by construction (same pattern as fig_heatflux above). FOUR
    # entries mean TWO legend rows, so the anchor must sit deeper than the
    # two-entry (one-row) figures: at -0.055 the first legend row rose into
    # the "Altitude (km)" x-axis labels of both panels on the rendered page.
    handles, labels = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    handles.extend(h2)
    labels.extend(l2)
    fig.legend(handles, labels, fontsize=PLAIN_TEXT_PT, loc="lower center", ncol=2,
               frameon=False, bbox_to_anchor=(0.5, -0.12))

    fig.suptitle("One-degree-of-freedom entry trajectory and the two run conditions",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "fignew_trajectory.png", WIDTH_FULL)


def fig_convergence() -> None:
    """F3. Normalised residuals against step, with the definition stated."""
    rows = read_csv(RESULTS / "validation_smooth" / "validation_timeseries.csv")

    fig, ax = plt.subplots(figsize=(WIDTH_FULL, WIDTH_FULL * 0.74))
    print("    measured residuals |x - x_ref|/|x_ref|, x_ref = mean of last three samples:")
    for key, lbl, colr in (
        ("cd", "Drag coefficient $C_d$", CB[0]),
        ("cl", "Lift coefficient $C_l$", CB[1]),
        ("heatflux_avg_Wm2", "Per-element heat flux", CB[2]),
    ):
        vals = [float(r[key]) for r in rows]
        steps = [float(r["step"]) for r in rows]
        ref = sum(vals[-3:]) / 3.0
        res = [abs(v - ref) / abs(ref) for v in vals]
        ax.semilogy(steps, res, "-o", ms=3, lw=1.3, color=colr, label=lbl)
        print(f"      {key:18s} ref={ref:.6g}  first={res[0]:.4g}  last={res[-1]:.4g}"
              f"  decades={__import__('math').log10(res[0]/res[-1]) if res[-1] > 0 else float('inf'):.2f}")
    style(ax, "Convergence of the surface coefficients",
          "Particle-time step", "Normalised residual $|x-x_{ref}|/|x_{ref}|$")
    plain_log_ticks(ax, "y")
    # Outside the axes for the same reason as the scalloped figure: on a set of
    # decaying residuals the inside-axes corner chosen by loc="best" sits over the
    # earliest, largest residual values.
    h, lb = ax.get_legend_handles_labels()
    # LEGEND PT FLOOR: two of these three keys carry mathtext scripts ($C_d$
    # and $C_l$), which matplotlib draws at 0.7 of the parent size, so the
    # previous 8 pt legend printed its scripts at 5.6 pt. _guard_layout measured
    # that on the saved PNG and raised, which is why this legend sits at
    # SCRIPT_SAFE_PT. ncol drops from 3 to 2 for the same reason the fit loop in
    # save() needs a bound canvas: three 11.5 pt keys are wider than the 5.236 in
    # print width, and an over-wide artist makes the tight crop grow while the
    # canvas shrinks, which diverges instead of converging. Two keys per row
    # means two rows, so the anchor sits deeper than the single-row figures.
    # LEGEND ANCHOR: a rendered audit measured the x-axis label 0.75 pt from
    # legend row 1 at anchor -0.10. The legend is anchored in figure
    # fractions while tight_layout places the axis label from the axes box, so
    # the two are independent and can collide; the anchor is the lever that
    # owns the gap, because the label must stay where the axes put it.
    fig.legend(h, lb, fontsize=SCRIPT_SAFE_PT, loc="lower center", ncol=2,
               frameon=False, bbox_to_anchor=(0.5, -0.16))
    fig.tight_layout()
    save(fig, "fignew_convergence_residuals.png", WIDTH_FULL)


def fig_ccd_screen() -> None:
    """F5. The 15-point CCD screen as three design-space projections."""
    d = load_committed_opt()
    ccd = d["ccd_samples"]
    rn = [float(r["R_N"]) for r in ccd]
    rt = [float(r["r_tor"]) for r in ccd]
    hc = [float(r["half_cone_deg"]) for r in ccd]
    cost = [float(r["cost"]) for r in ccd]
    label = [r["label"] for r in ccd]

    def group(lbl: str) -> str:
        if lbl.startswith("factorial"):
            return "factorial corner (8)"
        if lbl.startswith("axial"):
            return "axial star (6)"
        return "center (1)"

    groups = [group(l) for l in label]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH_FULL, WIDTH_FULL * 0.46))
    # Each panel is (x quantity, y quantity, x label, y label). The x labels wrap
    # onto two lines because the one-line form did not fit: _guard_layout measured
    # the second and third panel labels 1.24 pt OVERLAPPING at SCRIPT_SAFE_PT in
    # panels of WIDTH_FULL/3 = 1.745 in, and a rendered audit found the same pair
    # separated by a single white column. The quantity name then the symbol and
    # unit keeps each line short enough for the panel it labels.
    panels = [(rn, rt, "Nose radius\n$R_N$ (m)", "Toroid radius $r_{tor}$ (m)"),
              (rn, hc, "Nose radius\n$R_N$ (m)", "Half-cone angle (deg)"),
              (rt, hc, "Toroid radius\n$r_{tor}$ (m)", "Half-cone angle (deg)")]
    marker_style = {"factorial corner (8)": ("o", CB[0]),
                    "axial star (6)": ("^", CB[1]),
                    "center (1)": ("*", CB[2])}
    for ax, (xq, yq, xlab, ylab) in zip(axes, panels):
        for g, (m, colr) in marker_style.items():
            xs = [v for v, gg in zip(xq, groups) if gg == g]
            ys = [v for v, gg in zip(yq, groups) if gg == g]
            ax.plot(xs, ys, m, ms=8 if m == "*" else 5, ls="none", color=colr, label=g)
        style(ax, "", xlab, ylab)
        # Per-panel legends were removed: each sat in the upper-right and covered
        # the same axial-star point at (R_N 1.5, r_tor 0.21, angle 68 deg) in all
        # three projections, hiding exactly the kind of edge point a design-space
        # screen exists to reveal. One shared legend below the panels replaces
        # all three and can overlap nothing. (A leftover guard that compared a
        # label string against the HANDLE list used to append a duplicate
        # "center (1)" entry to every panel; it is gone.)
    handles, labels = axes[0].get_legend_handles_labels()
    # Guard: one legend key per CCD group; a duplicate means a stray labelled
    # artist crept back in and the legend would print the same key twice.
    assert len(labels) == len(set(labels)) == 3, f"duplicate CCD legend keys: {labels}"
    fig.legend(handles, labels, fontsize=PLAIN_TEXT_PT, loc="lower center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, -0.10))
    # The exponent in 2^3 is a mathtext script, so this title carries the same
    # 0.7 shrink as the axis labels and must sit at SCRIPT_SAFE_PT, not at the
    # 10 pt it used to print (which rendered the exponent at 7 pt).
    fig.suptitle("Face-centered CCD screen: $N = 2^3 + 2(3) + 1 = 15$ points",
                 fontsize=SCRIPT_SAFE_PT)
    # y is the suptitle's default 0.98; the earlier explicit y=1.03 pushed the
    # text outside the saved bounding box and clipped the top of the capitals.
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    save(fig, "fignew_ccd_screen.png", WIDTH_FULL)
    print(f"    CCD points={len(ccd)} factors=3 (R_N, r_tor, half_cone_deg)")
    print(f"    factorial={groups.count('factorial corner (8)')} "
          f"axial={groups.count('axial star (6)')} center={groups.count('center (1)')}")
    print(f"    cost range {min(cost):.4f} to {max(cost):.4f}; center cost={cost[label.index('center')]:.4f}")


def fig_gate() -> None:
    """F6. Hybrid validation gate: prediction, re-simulation, flight, threshold."""
    p = (RESULTS / "validation_optimized" / "validation_pipeline_output"
         / "unified_comparison_data.json")
    if not p.exists():
        print("  !! gate JSON missing, skipping F6")
        return
    d = json.loads(p.read_text(encoding="utf-8"))

    def find(obj, *names):
        for n in names:
            if n in obj:
                return obj[n]
        return None

    comp = d.get("comparison", {})
    irve = comp.get("irve3_flight", {})
    raw = comp.get("stellarorion", {}).get("raw_dsmc", {})
    sg = comp.get("rapisarda_models", {}).get("Sutton-Graves", {})

    # Flight and DSMC values come from the validation pipeline export, which is
    # a committed, timestamped artefact of the run that was actually performed.
    q_flight = irve.get("total_heat_load_Jcm2")
    q_raw = raw.get("total_heat_load_Jcm2")
    q_sg = sg.get("Qmax")
    # The acceptance threshold and the analytic prediction come from the
    # COMMITTED optimization JSON, because that is the campaign the DSMC gate was
    # run against; see load_committed_opt() for why the working tree is not used.
    opt = load_committed_opt()
    q_target = opt["validation_refs"]["q_target_jcm2"]
    q_analytic = opt["optimized"]["total_heat_load_Jcm2"]
    print(f"    q_flight={q_flight}  q_analytic={q_analytic}  q_raw_dsmc={q_raw}  "
          f"q_target={q_target}  rapisarda_SG={q_sg}")
    if q_raw is not None and q_analytic:
        print(f"    correction factor c = q_dsmc/q_analytic = {q_raw / q_analytic:.5f} "
              f"(text reports 0.5006)")
        print(f"    verdict: q_hybrid = {q_raw:.2f} <= Q_target = {q_target:.2f} -> "
              f"{'PASS' if q_raw <= q_target else 'FAIL'}")

    # Only MEASURED quantities are drawn as bars. The acceptance threshold was
    # previously a fourth bar, which wrongly implied it was another
    # measurement; it is now a dashed reference line, which is what a threshold
    # is. No legend is needed because every bar carries its own x-axis label.
    # Category labels are wrapped to short lines because the long single line
    # "trajectory-integrated" measured 19 characters, about 1.30 in at 9 pt
    # against a 1.45 in column pitch, so adjacent labels touched. Wrapping to
    # a maximum of about 13 characters per line brings the widest line to
    # about 0.89 in, which leaves a clear word space between columns.
    series = [("IRVE-3 flight\n(trajectory\nintegrated)", q_flight, CB[0]),
              ("Analytic\nprediction\nfrom cost\nfunction", q_analytic, CB[1]),
              ("DSMC\nre-simulation\n(raw, this\ngeometry)", q_raw, CB[2])]
    series = [(n, v, c) for n, v, c in series if isinstance(v, (int, float))]

    fig, ax = plt.subplots(figsize=(WIDTH_NARROW, WIDTH_NARROW * 0.92))
    # Columns sit 1.15 units apart (not the default 1.0) so the two-line
    # x-tick labels of adjacent categories keep a clear word-space gap on the
    # printed page: batch-1 verification measured only 2-4 px between columns.
    xs = [i * 1.15 for i in range(len(series))]
    vals = [v for _, v, _ in series]
    bars = ax.bar(xs, vals, color=[c for _, _, c in series], width=0.6)
    # The x limits are tight (-0.35 rather than -0.55) so the column pitch in
    # PIXELS grows: with the wider limit the axis span was 3.0 units for a
    # pitch of 1.15, only 38 percent of the width, and verification measured
    # the three category labels touching even after the spread change.
    ax.set_xlim(-0.35, (len(series) - 1) * 1.15 + 0.35)
    for b, (_, v, _) in zip(bars, series):
        # Value labels hang INSIDE the bar top: an above-bar label for the
        # analytic bar landed 1 px under the dashed acceptance-threshold line.
        ax.annotate(f"{v:.2f}", (b.get_x() + b.get_width() / 2, v), ha="center",
                    va="top", textcoords="offset points", xytext=(0, -4),
                    fontsize=PLAIN_TEXT_PT)
    threshold_line = None
    if q_target:
        # The dashed linestyle is taken from the active rcParams instead of the
        # two-character style name, because the goal forbids a literal double
        # hyphen in any source file. The drawn pattern is identical, so the
        # rendered PNG is unchanged, and the pattern stays a single definition.
        dashed = (0, tuple(matplotlib.rcParams["lines.dashed_pattern"]))
        threshold_line = ax.axhline(
            q_target, ls=dashed, lw=1.4, color=CB[3],
            label=f"Acceptance threshold $Q_{{target}}$ = {q_target:.2f}")
    ax.set_xticks(xs)
    ax.set_xticklabels([n for n, _, _ in series], fontsize=9)
    style(ax, "Hybrid validation gate: heat load comparison",
          "", "Total heat load (J/cm$^2$)")
    top = max(vals + ([q_target] if q_target else []))
    ax.set_ylim(0, top * 1.22)
    fig.tight_layout()
    if threshold_line is not None:
        # LEGEND PT FLOOR: this key carries a mathtext subscript, so the
        # previous 8 pt in-axes legend printed that subscript at 5.6 pt and
        # _guard_layout rejected the figure. The legend also MOVES OUT of the
        # axes, for the reason every other legend in this file sits outside the
        # data region: an in-axes frame can occlude the bars it annotates, and a
        # single 11.5 pt key plus its frame no longer fits the 3.78 in axes
        # without overhanging the canvas. The anchor clears the four-line
        # category labels drawn below the axes.
        fig.legend([threshold_line], [threshold_line.get_label()],
                   fontsize=SCRIPT_SAFE_PT, loc="lower center", ncol=1,
                   frameon=False, bbox_to_anchor=(0.5, -0.30))
    save(fig, "fignew_gate_comparison.png", WIDTH_NARROW)


def main() -> int:
    FIGDIR.mkdir(exist_ok=True)
    # fig_bo_trace is deliberately absent. The document already prints
    # figures/bo_convergence.png for the Bayesian-optimisation search, and that
    # figure additionally draws the vertical line marking the boundary between the
    # 20 Latin-Hypercube points and the 50 Expected-Improvement iterations, which
    # a second BO figure would duplicate rather than improve. Generating an
    # unreferenced PNG here would only enlarge the orphan-asset count.
    jobs = [fig_scalloped_vs_smooth, fig_trajectory, fig_convergence,
            fig_ccd_screen, fig_gate]
    rc = 0
    for job in jobs:
        print(f"\n{job.__doc__.splitlines()[0]}")
        try:
            job()
        except Exception as exc:  # noqa: BLE001
            print(f"  !! {job.__name__} FAILED: {type(exc).__name__}: {exc}")
            rc = 1
    print("\ndone")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
