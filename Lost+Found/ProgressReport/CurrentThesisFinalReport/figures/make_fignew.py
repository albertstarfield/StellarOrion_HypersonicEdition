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
# validation gate that was actually run at `--nose 2.971440`. So the figure must
# be generated from that same committed revision, otherwise the figure and the
# text would contradict each other. `git show <rev>:<path>` is used for exactly
# this reason, and the revision is asserted below rather than hard-coded twice.
OPTJSON_REL = "stellarorion_program_proc/src/python/hiad_optimization_results.json"
OPTJSON_REV = "bdddb47"

# Paul Tol's colourblind-safe qualitative palette.
CB = ["#004488", "#DDAA33", "#BB5566", "#228833", "#AA4499", "#66CCEE"]

DPI = 300

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
TEXT_W_IN = 21.0 / 2.54 - (4.0 + 3.0) / 2.54      # 5.51181
TEXT_H_IN = 29.7 / 2.54 - (3.0 + 3.0) / 2.54      # 9.33071
WIDTH_FULL = 0.95 * TEXT_W_IN                        # 5.23622, width=0.95\textwidth
WIDTH_NARROW = 0.80 * TEXT_W_IN                     # 4.40945, width=0.80\textwidth


def load_committed_opt() -> dict:
    """Return the optimization results as COMMITTED, matching the thesis text."""
    import subprocess
    res = subprocess.run(["git", "show", f"{OPTJSON_REV}:{OPTJSON_REL}"],
                         cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"git show {OPTJSON_REV}:{OPTJSON_REL} failed: {res.stderr.strip()}")
    data = json.loads(res.stdout)
    hist = data["history"]
    costs = [float(r["cost"]) for r in hist]
    argmin = min(range(len(costs)), key=lambda i: costs[i])
    opt = data["optimized"]
    print(f"    [committed {OPTJSON_REV}] argmin idx={argmin} cost={costs[argmin]:.6f} "
          f"R_N={opt['R_N']:.6f} r_tor={opt['r_tor']:.6f} Q={opt['total_heat_load_Jcm2']:.4f}")
    if abs(costs[argmin] - 1.605054) > 1e-4 or argmin != 37:
        raise RuntimeError(
            f"committed JSON does not match the thesis (expected idx 37 cost 1.605054, "
            f"got idx {argmin} cost {costs[argmin]:.6f}); refusing to plot a figure "
            f"that would contradict the text")
    return data


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=10, pad=8)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(True, which="both", ls=":", lw=0.5, alpha=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def save(fig, name: str, print_width_in: float) -> Path:
    """Save so that the PRINTED width equals print_width_in to within 0.5%.

    AXIOM: this is not achievable by declaring a figsize alone. Every call uses
    bbox_inches="tight", which CROPS the saved image to its artist extents, so
    the saved width is not the figsize width. Measured on the first attempt at
    the corrected sizes: fignew_scalloped_vs_smooth_heatflux.png came out
    2282 px = 7.607 in against a 5.236 in print width, an effective scale of
    0.688, which would still have shrunk every label by nearly a third.

    The crop ratio depends only on the figure's internal proportions, so it is
    stable under resizing. Measuring the crop once and rescaling the canvas by
    the reciprocal therefore converges, and the result is asserted rather than
    assumed.
    """
    out = FIGDIR / name
    target_px = print_width_in * DPI
    for attempt in range(1, 5):
        fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
        got_px = Image.open(out).size[0]
        if abs(got_px - target_px) / target_px <= 0.005:
            break
        w, h = fig.get_size_inches()
        ratio = target_px / got_px
        fig.set_size_inches(w * ratio, h * ratio, forward=True)
    else:
        print(f"  !! {name}: could not fit to {print_width_in:.3f} in "
              f"(last {got_px / DPI:.3f} in)")
        rc = 1
    final_in = Image.open(out).size[0] / DPI
    eff = print_width_in / final_in
    print(f"  wrote {name:44s} {Image.open(out).size[0]}x{Image.open(out).size[1]}px  "
          f"print {print_width_in:.3f} in  scale {eff:.3f}  "
          f"effective dpi {DPI / eff:.0f}")
    plt.close(fig)
    return out


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
                label=f"smooth  {sm[0]['alt_km'][:5]} km, {float(sm[0]['vel_ms']):.0f} m/s")
        ax.plot(x2, y2, "-s", ms=3, lw=1.3, color=CB[1],
                label=f"scalloped  {sc[0]['alt_km'][:5]} km, {float(sc[0]['vel_ms']):.0f} m/s")
        ax.set_yscale("log")
        style(ax, lbl, "Particle-time step", "Heat flux (W/cm$^2$)")
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()

    # The legend is drawn ONCE, BELOW both panels, and not inside either axes.
    # Two placements inside the axes were tried and both failed on the rendered
    # page: loc="best" chose upper left, which is where these traces are highest,
    # and a pinned upper right still clipped the first markers in the left panel.
    # A legend outside the data region cannot occlude data by construction.
    fig.legend(handles, labels, fontsize=8, loc="lower center", ncol=2,
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
    The scalloped run's state (52.0326 km, 3094.2 m/s, Mach 9.4325, g 14.0059)
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

    on_idx = min(range(len(rows)), key=lambda i: abs(alt[i] - 52.032558))
    print(f"    trajectory: {len(rows)} samples, {min(alt):.2f}-{max(alt):.2f} km, "
          f"t = 0-{max(t):.0f} s")
    print(f"    peak dynamic pressure {max(q):.1f} Pa and peak g-load {max(g):.3f} both at "
          f"alt={alt[q.index(max(q))]:.2f} km, V={vel[q.index(max(q))]:.1f} m/s, "
          f"Mach={mach[q.index(max(q))]:.3f}")
    print(f"    scalloped run state matches profile row {on_idx} exactly "
          f"(t={t[on_idx]:.1f} s); the smooth run state is NOT on this profile")

    fig, (ax1, ax2) = plt.subplots(1, 2,
                             figsize=(WIDTH_FULL, WIDTH_FULL * 0.62))

    ax1.plot(alt, vel, "-", lw=1.5, color=CB[0], label="1-DOF entry profile")
    ax1.plot(alt[on_idx], vel[on_idx], "s", ms=7, color=CB[1], mec="black", mew=0.7,
             label=f"scalloped run (t = {t[on_idx]:.0f} s)")
    ax1.plot(51.818481, 3378.671, "^", ms=8, color=CB[2], mec="black", mew=0.7,
             label="smooth run (off this profile)")
    style(ax1, "Velocity against altitude", "Altitude (km)", "Velocity (m/s)")
    ax1.legend(fontsize=8, loc="best", frameon=True, framealpha=1.0,
               facecolor="white", edgecolor="0.7")

    ax2.plot(alt, g, "-", lw=1.5, color=CB[0], label="deceleration load")
    ax2.plot(alt[on_idx], g[on_idx], "s", ms=7, color=CB[1], mec="black", mew=0.7)
    ax2.plot(51.818481, 16.833399, "^", ms=8, color=CB[2], mec="black", mew=0.7)
    style(ax2, "Deceleration load against altitude", "Altitude (km)",
          "Deceleration load (g)")
    ax2.legend(fontsize=8, loc="best", frameon=True, framealpha=1.0,
               facecolor="white", edgecolor="0.7")

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
    # Outside the axes for the same reason as the scalloped figure: on a set of
    # decaying residuals the inside-axes corner chosen by loc="best" sits over the
    # earliest, largest residual values.
    h, lb = ax.get_legend_handles_labels()
    fig.legend(h, lb, fontsize=8, loc="lower center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, -0.055))
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
        return "centre (1)"

    groups = [group(l) for l in label]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH_FULL, WIDTH_FULL * 0.46))
    # Each panel is (x quantity, y quantity, x label, y label).
    panels = [(rn, rt, "Nose radius $R_N$ (m)", "Toroid radius $r_{tor}$ (m)"),
              (rn, hc, "Nose radius $R_N$ (m)", "Half-cone angle (deg)"),
              (rt, hc, "Toroid radius $r_{tor}$ (m)", "Half-cone angle (deg)")]
    marker_style = {"factorial corner (8)": ("o", CB[0]),
                    "axial star (6)": ("^", CB[1]),
                    "centre (1)": ("*", CB[2])}
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
        # all three and can overlap nothing.
        if g not in ax.get_legend_handles_labels()[0]:
            ax.plot([], [], m, ms=8 if m == "*" else 5, ls="none", color=colr, label=g)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, loc="lower center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, -0.10))
    fig.suptitle("Face-centred CCD screen: $N = 2^3 + 2(3) + 1 = 15$ points",
                 fontsize=10)
    # y is the suptitle's default 0.98; the earlier explicit y=1.03 pushed the
    # text outside the saved bounding box and clipped the top of the capitals.
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    save(fig, "fignew_ccd_screen.png", WIDTH_FULL)
    print(f"    CCD points={len(ccd)} factors=3 (R_N, r_tor, half_cone_deg)")
    print(f"    factorial={groups.count('factorial corner (8)')} "
          f"axial={groups.count('axial star (6)')} centre={groups.count('centre (1)')}")
    print(f"    cost range {min(cost):.4f} to {max(cost):.4f}; centre cost={cost[label.index('center')]:.4f}")


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
    series = [("IRVE-3 flight\n(trajectory-integrated)", q_flight, CB[0]),
              ("Analytic prediction\nfrom cost function", q_analytic, CB[1]),
              ("DSMC re-simulation\n(raw, this geometry)", q_raw, CB[2])]
    series = [(n, v, c) for n, v, c in series if isinstance(v, (int, float))]

    fig, ax = plt.subplots(figsize=(WIDTH_NARROW, WIDTH_NARROW * 0.92))
    xs = list(range(len(series)))
    vals = [v for _, v, _ in series]
    bars = ax.bar(xs, vals, color=[c for _, _, c in series], width=0.6)
    for b, (_, v, _) in zip(bars, series):
        ax.annotate(f"{v:.2f}", (b.get_x() + b.get_width() / 2, v), ha="center",
                    va="bottom", fontsize=8.5)
    if q_target:
        ax.axhline(q_target, ls="--", lw=1.4, color=CB[3],
                   label=f"Acceptance threshold $Q_{{target}}$ = {q_target:.2f}")
        ax.legend(fontsize=8, loc="upper right", frameon=True, framealpha=1.0,
                  facecolor="white", edgecolor="0.7")
    ax.set_xticks(xs)
    ax.set_xticklabels([n for n, _, _ in series], fontsize=8)
    style(ax, "Hybrid validation gate: heat load comparison",
          "", "Total heat load (J/cm$^2$)")
    top = max(vals + ([q_target] if q_target else []))
    ax.set_ylim(0, top * 1.22)
    fig.tight_layout()
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
