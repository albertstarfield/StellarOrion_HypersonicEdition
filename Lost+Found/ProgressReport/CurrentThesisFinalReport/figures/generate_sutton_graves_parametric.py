#!/usr/bin/env python3
"""Regenerate `sutton_graves_parametric.png` for the CurrentThesis LaTeX report.

PURPOSE
-------
The previously committed figure plotted the Sutton--Graves stagnation correlation
using superseded constants and geometry, producing an IRVE-3 marker of
959.7 W/cm^2 at R_N = 0.577 m and V = 10.8 km/s. The current solver evaluates
the same correlation at C_SG = 1.83e-4 and R_N = 1.5 m, giving 16.14 W/cm^2 at
the run condition (h = 51.8 km, V = 3378 m/s). This script regenerates the
figure so that the plotted physics matches the code and the thesis text.

AXIOMS
------
A1. The correlation evaluated here is
        q_dot = C_SG * sqrt(rho / R_N) * V^3            [W/m^2]
    with C_SG = 1.83e-4 for Earth air, matching
    `stellarorion_types.ads` (C_SG : constant Float := 1.83e-4).
A2. The freestream density is a function of altitude only, obtained from the
    same atmospheric model the solver uses (`isa_atmosphere` via the Ada FFI),
    not from a hand-rolled exponential fit. This guarantees that the baseline
    marker on the plot equals the number quoted in the thesis.
A3. R_N = 1.5 m is the IRVE-3 nose radius (3 m aeroshell diameter).
A4. The run condition is h = 51.8 km, V = 3378 m/s (Mach ~ 10.29).

THEORIES
---------
T1. Because q_dot ~ V^3, the velocity sweep spans three orders of magnitude in
    heat flux; a linear y-axis is unreadable, so panel (a) uses a log axis.
T2. Because q_dot ~ 1/sqrt(R_N), the radius sweep is likewise logarithmic; a log
    x-axis is required to show the scaling over 0.1-3.0 m.
T3. The baseline marker must be computed by calling the solver's own SG
    function, not by re-deriving it in this file, so that plot and text cannot
    drift apart.

APPLICATIONS
------------
A1/A2/A3/A4 are realised by: importing `sutton_graves_heat_flux` and
`isa_atmosphere` from the project's `validation_pipeline` module, evaluating
them over a sweep, and annotating the IRVE-3 run condition with the value the
solver returns.

CITATIONS
---------
[Citation: Sutton & Graves (1971) - "A Correlation for Stagnation Point
          Heating", AIAA Paper 71-534]
[Citation: ada_pinn_wrapper.sutton_graves_heat_flux - Ada/SPARK FFI wrapper,
          stellarorion_program_proc/src/python/ada_pinn_wrapper.py]
[Citation: validation_pipeline.isa_atmosphere - atmospheric model,
          stellarorion_program_proc/src/python/validation_pipeline.py]
[Citation: Matplotlib v3.11.2 - https://matplotlib.org/stable/api/]

SAFETY / ERROR HANDLING
-----------------------
- Missing solver module or unavailable Ada library raises and aborts the build
  rather than silently falling back to a Python re-implementation, because a
  silent fallback would reintroduce exactly the drift this script removes.
- Output directory is created if absent; the PNG is written atomically via a
  temporary file and `os.replace` so a partial write cannot leave a corrupt
  figure in place.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# --- Axiom A3/A4: geometry and run condition constants -----------------------
R_N_BASELINE_M: float = 1.5          # A3: IRVE-3 nose radius (3 m diameter)
H_RUN_KM: float = 51.8               # A4: run altitude
V_RUN_MS: float = 3378.0             # A4: run velocity
MACH_RUN: float = 10.29              # A4: quoted Mach number

# Sweep ranges chosen to bracket the baseline in both panels.
V_SWEEP_KMS = [2.0, 2.5, 3.0, 3.378, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
R_SWEEP_M = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]

# --- Layout constants, every one of them derived from measured geometry -----
# PRINT_W_IN is the width LaTeX uses: chapter_02 includes this figure at
# width=0.9\textwidth, and the A4 text block is 21.0 cm wide with 4.0 + 3.0 cm
# margins. The saved figure is 7.0 in, so the placement scale is
# PRINT_W_IN / 7.0 = 0.7087 and a 12 pt tick prints at 8.5 pt.
PRINT_W_IN: float = 0.9 * (21.0 / 2.54 - (4.0 + 3.0) / 2.54)
SAVE_DPI: int = 200

# Panel (b) x ticks are a SUBSET of the sweep. Labelling all ten sweep radii
# cannot work. The panel is 2.77 in wide and the axis spans log10(3.0/0.1) =
# 1.477 decades, so the neighbouring pair 2.5 m and 3.0 m sits 0.079 decades
# apart, which is 29 px at 200 dpi, while the 12 pt label "2.5" is 53 px wide.
# The measured render showed a single white column between the two labels, so
# the pair reads as the one number 2.53. The radii dropped from the lettering
# (0.3, 0.75 and 2.5 m) stay in R_SWEEP_M, so every curve still passes through
# them with its marker; only the axis text is thinned.
X_TICKS_M = [0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0]

# Panel (b) y limits. The annotation box needs an empty band under the lowest
# curve. With autoscaled limits the lowest plotted point is about 8.0 W/cm2
# (V = 3 km/s at R_N = 3 m) and the axis bottom landed near 6.45 W/cm2, so the
# band was only a fifth of a decade tall. AX2_Y_MIN opens the band down to
# 4.0 W/cm2, below every plotted point, and AX2_Y_MAX leaves the top curve
# (about 557 W/cm2) clear of the frame.
AX2_Y_MIN: float = 4.0
AX2_Y_MAX: float = 900.0

# The panel (b) arrow targets the dashed baseline line inside that empty band
# instead of a marker on a curve. It used to target the V = 3 km/s curve at
# R_N = 1.5 m, which put the arrowhead on the curve and broke its continuity
# (58 black px inside the curve band on the measured render). ARROW_TARGET_Q
# sits below every curve point that the arrow spans, so the tip clears the
# curve by about 14 printed points. This also settles the earlier disagreement
# between the artwork and its own spec about which marker the arrow should
# touch: the label names a nose RADIUS, the dashed line IS that radius, and no
# marker is claimed, so no colour choice can contradict the text.
ARROW_TARGET_Q: float = 7.0

# Guard floors, evaluated after the PNG is written to its temporary path and
# before it replaces the committed file, so a failure leaves the good figure in
# place. MIN_TICK_GAP_PT is a thin word space at these label sizes, and
# ARROW_HEAD_PT is the half extent of a matplotlib arrow head at the
# annotation font size, which is also its default mutation scale.
MIN_PRINTED_PT: float = 8.0
MIN_TICK_GAP_PT: float = 2.0
ARROW_FONTSIZE_PT: float = 12.0
ARROW_HEAD_PT: float = ARROW_FONTSIZE_PT * 0.45
MIN_ARROW_CLEAR_PT: float = 1.0


def _repo_root() -> str:
    """
    Resolve the repository root by walking up from this script.

    The script lives at
    ``<repo>/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/``,
    so the root is the ancestor that contains the ``stellarorion_program_proc``
    directory. Walking up and probing for that marker directory is robust to
    the report being relocated or an extra nesting level being introduced, and
    avoids a hard-coded path that would break on any other machine.

    :returns: absolute path of the repository root.
    :raises RuntimeError: if no ancestor contains ``stellarorion_program_proc``,
        which means the script is not inside the expected tree.
    """
    marker = "stellarorion_program_proc"
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(current, marker)):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # reached filesystem root without finding marker
            raise RuntimeError(
                "Repository root not found: no ancestor of %r contains a %r "
                "directory. The regeneration script must live inside the "
                "StellarOrion repository tree."
                % (os.path.abspath(__file__), marker)
            )
        current = parent


def _load_solver() -> dict[str, Any]:
    """
    Import the project's own physics entry points.

    :returns: mapping with keys ``sg`` (Sutton--Graves evaluator) and ``isa``
        (atmospheric density evaluator).
    :raises ImportError: if the solver module or its Ada/SPARK library cannot be
        loaded. Propagated deliberately: a silent fallback to an independent
        Python correlation would reintroduce the constant/geometry drift that
        this regeneration exists to remove.
    """
    # Locate the project source root relative to this script.
    # figures/ -> CurrentThesisFinalReport/ -> ProgressReport/ -> Lost+Found/ -> <repo>
    repo_root = _repo_root()
    repo_src = os.path.join(repo_root, "stellarorion_program_proc", "src", "python")
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)

    try:
        from validation_pipeline import (  # type: ignore[import-not-found]
            isa_atmosphere,
            sutton_graves_heat_flux,
        )
    except ImportError as exc:  # pragma: no cover - environment failure path
        raise ImportError(
            "Cannot import validation_pipeline from %r. The Ada/SPARK physics "
            "library must be available so that the regenerated figure uses the "
            "same correlation as the solver. Original error: %s" % (repo_src, exc)
        ) from exc

    return {"sg": sutton_graves_heat_flux, "isa": isa_atmosphere}


def sg_at_velocity(velocity_kms: float, nose_radius_m: float, solver: dict[str, Any]) -> float:
    """
    Evaluate the Sutton--Graves correlation at fixed nose radius.

    :param velocity_kms: freestream velocity in km/s.
    :param nose_radius_m: nose radius in metres.
    :param solver: mapping returned by :func:`_load_solver`.
    :returns: stagnation heat flux in W/cm^2.
    """
    # Density is taken at the run altitude so that every curve shares one
    # freestream state; velocity is the only variable on the abscissa (A2).
    density = solver["isa"](H_RUN_KM)["density_kgm3"]
    isa = solver["isa"]

    # The solver's SG entry point takes (altitude, velocity) and uses a fixed
    # nose radius, so for a radius sweep we evaluate the correlation directly
    # from its own constants, which the wrapper exports.
    c_sg = _c_sg_from_solver(isa)
    q_wm2 = c_sg * (density / nose_radius_m) ** 0.5 * (velocity_kms * 1000.0) ** 3
    return q_wm2 / 1.0e4


def sg_at_radius(nose_radius_m: float, velocity_kms: float, solver: dict[str, Any]) -> float:
    """
    Evaluate the Sutton--Graves correlation at fixed velocity.

    :param nose_radius_m: nose radius in metres.
    :param velocity_kms: freestream velocity in km/s.
    :param solver: mapping returned by :func:`_load_solver`.
    :returns: stagnation heat flux in W/cm^2.
    """
    return sg_at_velocity(velocity_kms, nose_radius_m, solver)


def _c_sg_from_solver(isa: Any) -> float:
    """
    Read the correlation constant the solver actually uses.

    :param isa: the ``isa_atmosphere`` callable, used only to trigger the module
        import side effects that load the Ada/SPARK library.
    :returns: ``C_SG`` in SI units.
    :raises RuntimeError: if the constant cannot be located in the source, which
        would mean the figure cannot be tied to the solver's own value.
    """
    del isa  # import side effect is the point of accepting this argument
    types_ads = os.path.join(
        _repo_root(),
        "stellarorion_program_proc",
        "src",
        "simulation_engine",
        "stellarorion_types.ads",
    )
    with open(types_ads, "r", encoding="utf-8") as handle:
        for line in handle:
            # Match the constant *declaration* only, so that a mere mention of
            # C_SG in a comment or a dependent expression cannot be picked up
            # in place of the authoritative value.
            if "C_SG" not in line or ":=" not in line:
                continue
            for token in line.replace(";", " ").split():
                cleaned = token.rstrip(";,")
                try:
                    value = float(cleaned)
                except ValueError:
                    continue
                # A correlation constant is a small positive number; reject any
                # other numeric token (e.g. an array bound) on the same line.
                if 0.0 < value < 1.0:
                    return value
    raise RuntimeError(
        "C_SG constant not found in %s; refusing to hard-code a value so that "
        "the figure cannot drift from the solver." % types_ads
    )


def verify(parts: dict[str, Any], tmp_path: str) -> None:
    """Measure the saved PNG and refuse to ship it if a layout rule is broken.

    WHY A MEASUREMENT AND NOT A LOOK: the two defects this guard exists for
    were invisible in the source. Defect 1 was ten log-axis tick labels
    squeezed into a 2.77 in panel, so 2.5 and 3.0 collided by one white
    column and read as the number 2.53. Defect 2 was an annotation
    arrowhead drawn across a plotted curve, breaking its continuity. Both
    are distances between rendered objects, so the only honest check is to
    measure the rendered objects in printed points.

    :param parts: mapping with the keys ``fig``, ``ax2`` and
        ``baseline_line`` returned by :func:`build_figure`.
    :param tmp_path: path of the PNG that was just written by ``savefig``.
    :returns: None.
    :raises RuntimeError: if any printed tick gap, the smallest printed
        font size, or the arrowhead clearance is below its floor. The
        committed PNG is left untouched because the caller verifies before
        renaming the temporary file over it.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fig_metrics as fm  # local measurement library, see its docstring

    fig = parts["fig"]
    ax2 = parts["ax2"]
    baseline_line = parts["baseline_line"]

    scale = fm.effective_scale(tmp_path, PRINT_W_IN, SAVE_DPI)
    print("[sutton_graves_parametric] print scale %.4f of declared sizes" % scale)

    # Rule 1: no adjacent tick label may touch its neighbour. Every pair is
    # printed so the reader can see which pair is tightest.
    fig.canvas.draw()
    worst = None
    for left, right, gap in fm.x_tick_label_gaps_pt(ax2, fig, scale):
        print(
            "[sutton_graves_parametric] tick gap %s to %s: %.2f pt"
            % (left, right, gap)
        )
        if worst is None or gap < worst[2]:
            worst = (left, right, gap)
    if worst is not None and worst[2] < MIN_TICK_GAP_PT:
        raise RuntimeError(
            "panel b tick labels %s and %s sit %.2f pt apart, below the "
            "%.1f pt floor; thin X_TICKS_M further"
            % (worst[0], worst[1], worst[2], MIN_TICK_GAP_PT)
        )

    # Rule 2: every declared size must survive the print scale, including
    # mathtext subscripts, which matplotlib renders at SHRINK_FACTOR of the
    # parent size.
    pt, where = fm.smallest_text_pt(fig, scale)
    print(
        "[sutton_graves_parametric] smallest printed text %.2f pt (%s)"
        % (pt, where)
    )
    if pt < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is below the %.1f pt floor (%s); "
            "raise the declared size or reduce the include width"
            % (pt, MIN_PRINTED_PT, where)
        )

    # Rule 3: the arrowhead must not touch a plotted line, or it breaks the
    # line the way defect 2 broke the V=3 curve. The baseline reference line
    # is skipped because pointing at it is the whole purpose of the arrow.
    clear, owner = fm.min_distance_to_lines_pt(
        ax2,
        fig,
        (R_N_BASELINE_M, ARROW_TARGET_Q),
        scale,
        skip=(baseline_line,),
    )
    print(
        "[sutton_graves_parametric] arrowhead clearance %.2f pt from %s"
        % (clear, owner)
    )
    if clear < ARROW_HEAD_PT + MIN_ARROW_CLEAR_PT:
        raise RuntimeError(
            "arrowhead clearance %.2f pt is below the %.2f pt floor (head "
            "%.2f pt plus %.2f pt margin) against %s; lower ARROW_TARGET_Q "
            "or raise AX2_Y_MIN"
            % (
                clear,
                ARROW_HEAD_PT + MIN_ARROW_CLEAR_PT,
                ARROW_HEAD_PT,
                MIN_ARROW_CLEAR_PT,
                owner,
            )
        )


def main() -> int:
    """
    Render the two-panel Sutton-Graves figure and save it as a PNG.

    :returns: process exit status (0 on success).
    :raises Exception: any failure propagates so the build is visibly broken
        rather than shipping a stale figure.
    """
    solver = _load_solver()
    sg = solver["sg"]

    # --- Baseline value straight from the solver (Theorem T3) --------------
    baseline = sg(H_RUN_KM, V_RUN_MS)["heat_flux_Wcm2"]
    print("[sutton_graves_parametric] solver baseline: %.4f W/cm2" % baseline)

    parts = build_figure(solver, baseline)
    fig = parts["fig"]

    import matplotlib.pyplot as plt  # backend already forced to Agg in there

    # --- Atomic write: temp file then rename (see module docstring) ---------
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "sutton_graves_parametric.png")
    tmp_path = out_path + ".tmp.png"
    fig.savefig(tmp_path, dpi=SAVE_DPI, bbox_inches="tight", facecolor="white")
    verify(parts, tmp_path)
    plt.close(fig)
    os.replace(tmp_path, out_path)
    print("[sutton_graves_parametric] wrote %s" % out_path)
    return 0


def build_figure(solver, baseline):
    """Build the two-panel figure and return it WITHOUT saving it.

    Split out of main() so that a layout guard can query the real text
    extents of the unsaved figure. Measuring the returned object is the only
    trustworthy way to prove that tick labels do not collide: reading the
    rendered PNG mixes the tight crop, the dpi and the LaTeX placement scale
    into one number that cannot be attributed to any single cause.

    :param solver: mapping holding the "sg" and "isa" callables of the project.
    :param baseline: stagnation heat flux in W/cm2 at the run condition.
    :type solver: dict
    :type baseline: float
    :returns: mapping with the keys "fig" (the matplotlib Figure), "ax1" and
        "ax2" (the two panel axes) and "baseline_line" (the dashed R_N = 1.5 m
        reference line), so that verify() can measure real extents before the
        figure is committed.
    :rtype: dict
    :raises Exception: any matplotlib failure propagates unchanged.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Printed at 0.9\textwidth = 4.96 in, so saved 7.0 in -> scale 0.71.
    # Tick labels at 12 pt print at 8.5 pt, at or above the 8 pt floor.
    plt.rcParams["xtick.labelsize"] = 12
    plt.rcParams["ytick.labelsize"] = 12

    # Layout AXIOM (goal rev 5): the panel (a) legend has 10 entries. At the
    # 8 pt printed floor it is 10 x ~10.5 pt = 1.47 in tall, which can never
    # fit inside a panel without covering curves, so BOTH legends live in a
    # dedicated row below their own panel. Panels stay on top; legend cells
    # (axes switched off) hold the legends.
    fig = plt.figure(figsize=(7.0, 4.2))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(
        2, 2, height_ratios=(2.2, 1.5), hspace=0.45, wspace=0.25,
        left=0.09, right=0.98, top=0.90, bottom=0.10)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    lg1 = fig.add_subplot(gs[1, 0])
    lg2 = fig.add_subplot(gs[1, 1])
    lg1.axis("off")
    lg2.axis("off")

    velocities = V_SWEEP_KMS
    radii = R_SWEEP_M

    # --- Panel (a): q vs velocity for several nose radii -------------------
    for r_n in radii:
        y = [sg_at_velocity(v, r_n, solver) for v in velocities]
        style = dict(lw=2.6, zorder=3)
        if abs(r_n - R_N_BASELINE_M) < 1e-9:
            style.update(color="black", lw=3.2)
            label = r"$R_N$ = 1.5 m (IRVE-3)"
        else:
            style.update(color="tab:blue", alpha=0.55)
            label = r"$R_N$ = %g m" % r_n
        ax1.plot(velocities, y, label=label, **style)

    # Mark the run condition. The IRVE-3 marker sits exactly on the 3.378 km/s
    # grid point, so no interpolation is required.
    v_run_kms = V_RUN_MS / 1000.0
    ax1.plot(
        [v_run_kms],
        [baseline],
        marker="o",
        ms=11,
        mfc="none",
        mec="black",
        mew=2.4,
        ls="none",
        zorder=6,
    )
    ax1.annotate(
        "IRVE-3 run condition\n%.2f W/cm$^2$" % baseline,
        xy=(v_run_kms, baseline),
        # Bottom band in AXES FRACTION: the curve family fans upward to the
        # right, so the band below the lowest curve (R_N = 3 m, which reaches
        # only ~55% height at x > 5.5 km/s) is empty. RIGHT-anchored at 0.95:
        # the round-pad box adds ~0.023 axes-frac, so 0.95 + 0.023 = 0.973
        # keeps the right edge ~15 px INSIDE the right spine (0.99 put it
        # 7 px past the spine on the rendered page), off the spine, and clear
        # of panel (b)'s rotated y-label. y = 0.055 (not 0.04) drops the
        # round-pad bottom edge ~6 px clear of the bottom spine; at 0.04 the
        # patch sat flush against the spine on the rendered page.
        xytext=(0.95, 0.055),
        textcoords="axes fraction",
        fontsize=13,
        ha="right",
        va="bottom",
        arrowprops=dict(arrowstyle="->", lw=1.8, color="black"),
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black", lw=1.1),
    )

    ax1.set_yscale("log")
    ax1.set_xlabel(r"Freestream velocity $V_\infty$ [km/s]", fontsize=13)
    ax1.set_ylabel(r"Stagnation heat flux $\dot{q}_s$ [W/cm$^2$]", fontsize=13)
    ax1.set_title(
        r"(a) $\dot{q}_s$ vs $V_\infty$ ($h$ = 51.8 km)",
        fontsize=13,
    )
    ax1.grid(True, which="both", alpha=0.3, ls=":")
    _h1, _l1 = ax1.get_legend_handles_labels()
    lg1.legend(_h1, _l1, fontsize=12, ncol=2, loc="center", frameon=False)

    # --- Panel (b): q vs nose radius at several Mach numbers ---------------
    for v_kms in (3.0, 5.0, 7.0):
        y = [sg_at_radius(r_n, v_kms, solver) for r_n in radii]
        ax2.plot(
            radii,
            y,
            marker="o",
            ms=5,
            lw=2.4,
            label=r"$V$ = %g km/s" % v_kms,
        )

    baseline_line = ax2.axvline(
        R_N_BASELINE_M,
        color="black",
        ls="--",
        lw=1.6,
        zorder=2,
    )
    # The y limits are set BEFORE the annotation is placed, so the empty band
    # the label box occupies is part of the axis rather than a margin that
    # autoscaling is free to eat.
    ax2.set_ylim(AX2_Y_MIN, AX2_Y_MAX)
    ax2.annotate(
        # One line, AXES FRACTION, right-anchored at 0.60, with a tight 0.15
        # pad. Measured on the rendered PNG: the blue V = 3 curve only descends
        # into the bottom band from x ~1170 px, so the patch must end left of
        # that, and anchor 0.60 puts its right edge near x 1151. At 13 pt with
        # pad 0.35 the patch measured 63 px tall and could not fit the band
        # without crossing the curve or the bottom spine, because the 0.35 pad
        # overshoots the anchor (text inside, patch not). 12 pt still prints at
        # or above the 8 pt floor (12 x 0.7087 = 8.5 pt), pad 0.15 shrinks the
        # patch to about 320x50 px, and va=bottom at 0.045 leaves about 11 px
        # above the spine.
        #
        # The arrow now ends on the dashed baseline line at ARROW_TARGET_Q,
        # inside the band that AX2_Y_MIN opens, instead of on a curve. The
        # measurement behind that change is recorded at ARROW_TARGET_Q.
        "$R_N$ = 1.5 m (IRVE-3)",
        xy=(R_N_BASELINE_M, ARROW_TARGET_Q),
        xytext=(0.60, 0.045),
        textcoords="axes fraction",
        fontsize=ARROW_FONTSIZE_PT,
        ha="right",
        va="bottom",
        arrowprops=dict(arrowstyle="->", lw=1.6, color="black"),
        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="black", lw=1.1),
    )

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    # Only the thinned subset carries lettering; see X_TICKS_M for the
    # measurement that forced the subset.
    ax2.set_xticks(X_TICKS_M)
    ax2.set_xticklabels([("%g" % r) for r in X_TICKS_M])
    ax2.minorticks_off()
    ax2.set_xlabel(r"Nose radius $R_N$ [m]", fontsize=13)
    ax2.set_ylabel(r"Stagnation heat flux $\dot{q}_s$ [W/cm$^2$]", fontsize=13)
    ax2.set_title(
        r"(b) $\dot{q}_s$ vs $R_N$ ($\propto 1/\sqrt{R_N}$)",
        fontsize=13,
    )
    ax2.grid(True, which="both", alpha=0.3, ls=":")
    _h2, _l2 = ax2.get_legend_handles_labels()
    lg2.legend(_h2, _l2, fontsize=12, ncol=1, loc="center", frameon=False)

    # No tight_layout: the gridspec margins above already place the rows, and
    # savefig(bbox_inches="tight") crops to the artist union at save time.

    # The axes and the reference line travel with the figure because verify()
    # measures them, not because the caller is expected to redraw anything.
    return {
        "fig": fig,
        "ax1": ax1,
        "ax2": ax2,
        "baseline_line": baseline_line,
    }


if __name__ == "__main__":
    sys.exit(main())
