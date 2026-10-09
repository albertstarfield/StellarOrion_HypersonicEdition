#!/usr/bin/env python3
"""Regenerate `sutton_graves_parametric.png` for the CurrentThesis LaTeX report.

PURPOSE
=======
The previously committed figure plotted the Sutton-Graves stagnation correlation
using superseded constants and geometry, producing an IRVE-3 marker of
959.7 W/cm^2 at R_N = 0.577 m and V = 10.8 km/s. This script evaluates the
same correlation at the constant the THESIS adopts, C_SG = 1.83e-4, and
R_N = 1.5 m, giving 16.14 W/cm^2 at the run condition (h = 51.8 km,
V = 3378 m/s): the value stated in the figure caption, in the AccSupp, and
in the official Optimization_Attempt_1 record (16.1379). The engine default
of 1.7415e-4 is disclosed in the thesis appendix and is deliberately not
plotted here, because this is a THESIS figure and must render its own
caption's constant.

AXIOMS
======
A1. The correlation evaluated here is
        q_dot = C_SG * sqrt(rho / R_N) * V^3            [W/m^2]
    with C_SG = 1.83e-4, the constant the thesis adopts for the 5-species
    reacting air model ("the value adopted here", chapter 2,
    \cite{sutton1971gravesh}); the appendix worked example derives
    16.14 W/cm^2 from it (1.83e-4 * sqrt(7.851e-4/1.5) * 3378^3).
    The engine default in `stellarorion_types.ads` is 1.7415e-4 and stays
    the disclosed contrast in the thesis; it is NOT the constant this
    figure plots, because the caption, the AccSupp and the official
    Optimization_Attempt_1 record all quote the 1.83e-4 scale (16.14 /
    16.1379 W/cm^2). An earlier revision of this script read the ads
    value and rendered 15.36 W/cm^2, contradicting its own caption.
    [Citation: NASA NTRS 20200002354, 2018, Eq. (2) = engine default.]
    [Citation: Sutton & Graves (1971) AIAA 71-534 = correlation form.]
A2. The freestream density is a function of altitude only, obtained from the
    same atmospheric model the solver uses (`isa_atmosphere` via the Ada FFI),
    not from a hand-rolled exponential fit. This guarantees that the baseline
    marker on the plot equals the number quoted in the thesis.
A3. R_N = 1.5 m is the IRVE-3 nose radius (3 m aeroshell diameter).
A4. The run condition is h = 51.8 km, V = 3378 m/s (Mach ~ 10.29).

THEORIES
=========
T1. Because q_dot ~ V^3, the velocity sweep spans three orders of magnitude in
    heat flux; a linear y-axis is unreadable, so panel (a) uses a log axis.
T2. Because q_dot ~ 1/sqrt(R_N), the radius sweep is likewise logarithmic; a log
    x-axis is required to show the scaling over 0.1-3.0 m.
T3. The baseline marker is computed by the SAME adopted-constant code path
    as the curves (sg_at_velocity in this file), so marker, curves and
    caption cannot drift apart. (This replaces an earlier T3 that called
    the solver FFI entry, which returned the engine-default 15.36 and
    drifted from the caption.)

APPLICATIONS
============
A1/A2/A3/A4 are realised by: importing `isa_atmosphere` from the project's
`validation_pipeline` module (through the Ada FFI) for the density,
evaluating the correlation with the thesis-adopted C_SG over the sweeps,
and annotating the IRVE-3 run condition with the resulting 16.14 W/cm^2.

CITATIONS
=========
[Citation: Sutton & Graves (1971) - "A Correlation for Stagnation Point
          Heating", AIAA Paper 71-534]
[Citation: validation_pipeline.isa_atmosphere - atmospheric model,
          stellarorion_program_proc/src/python/validation_pipeline.py]
[Citation: Matplotlib v3.11.2 - https://matplotlib.org/stable/api/]

SAFETY / ERROR HANDLING
=======================
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

# The print-fit loop, its tolerance, the achieved print scale and the
# inside-canvas check live in one sibling module. The path is added
# first so the import also works when a probe imports this file from
# another directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import print_fit as pf  # noqa: E402

# === Axiom A3/A4: geometry and run condition constants =======================
R_N_BASELINE_M: float = 1.5          # A3: IRVE-3 nose radius (3 m diameter)
H_RUN_KM: float = 51.8               # A4: run altitude
V_RUN_MS: float = 3378.0             # A4: run velocity
# === Axiom A1 (revised 2026-10-09): thesis-adopted correlation constant ======
# WHY not read from stellarorion_types.ads (which holds 1.7415e-4): the
# THESIS adopts 1.83e-4 for this figure ("the value adopted here", ch2,
# \cite{sutton1971gravesh}) and its caption/AccSupp/Optimization_Attempt_1
# all quote the resulting 16.14 W/cm^2. Reading the ads value rendered
# 15.36 W/cm^2 and contradicted the caption (batch-1 audit, 2026-10-09).
# The engine default stays disclosed in the thesis appendix; the ads file
# itself is never modified. Value = documented thesis constant, not an
# invention.
C_SG_THESIS: float = 1.83e-4
MACH_RUN: float = 10.29              # A4: quoted Mach number

# Sweep ranges chosen to bracket the baseline in both panels.
V_SWEEP_KMS = [2.0, 2.5, 3.0, 3.378, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
R_SWEEP_M = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]

# === Layout constants, every one of them derived from measured geometry =====
# PRINT_W_IN is the width LaTeX uses: chapter_02 includes this figure at
# width=0.9\textwidth, and the A4 text block is 21.0 cm wide with 4.0 + 3.0 cm
# The canvas is built at exactly the printed width, so the placement scale is
# 1.0 and a declared point size IS the printed point size. The save dpi is
# 300 because audit.py fails any figure whose effective dpi falls below 200,
# and a fit tolerance of 0.5 percent on a 200 dpi save lands at about 199.6.
PRINT_W_IN: float = 0.9 * pf.TEXT_W_IN
SAVE_DPI: int = pf.DPI

# Panel (b) x ticks are a SUBSET of the sweep. Labelling all ten sweep radii
# cannot work. The panel is 2.77 in wide and the axis spans log10(3.0/0.1) =
# 1.477 decades, so the neighbouring pair 2.5 m and 3.0 m sits 0.079 decades
# apart, which is 29 px at 200 dpi, while the 12 pt label "2.5" is 53 px wide.
# The measured render showed a single white column between the two labels, so
# the pair reads as the one number 2.53. The radii dropped from the lettering
# (0.3, 0.75 and 2.5 m) stay in R_SWEEP_M, so every curve still passes through
# them with its marker; only the axis text is thinned.
X_TICKS_M = [0.1, 0.2, 0.5, 1.0, 2.0, 3.0]
# Panel (a) x ticks in km/s. The sweep V_SWEEP_KMS spans 2 to 10, so the
# default ticker's 0, 5, 10, 15 lost two of its four labels to the axes clip
# and left the panel with a single x tick. Measured on the unsaved figure:
# 120.08 pt panel. The label at the 10 end of the sweep is deliberately NOT
# ticked, because an autoscale that ends at 10.4 puts that label on the right
# spine, where half of it sits in the 38.43 pt gutter and measured 4.69 pt of
# overlap with panel (b)'s y label. Four interior labels give a 40 pt pitch and
# keep every label clear of both spines and of the gutter.
A1_X_TICKS_KMS = [2.0, 4.0, 6.0, 8.0]

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
ARROW_TARGET_Q: float = 5.0

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

def _plain_tick(value: float, _pos: float) -> str:
    """Format a log-axis tick as a plain decimal number, not as a power.

    WHY: the default log formatter emits mathtext of the form ten to the
    power n, and matplotlib draws the exponent at SHRINK_FACTOR of the
    label size. Measured on the saved PNG at a print scale of 0.7082, a
    12 pt tick therefore printed its exponent at 0.7 x 12 x 0.7082 =
    5.95 pt, which is below the 8 pt floor the goal sets for figure text.
    The measured offending label was the zero exponent of the lowest
    decade. A plain decimal has no script at all, so it prints at the full
    declared size and cannot regress when the print scale changes.

    :param value: tick value in data units, always a positive decade
        multiple on a log axis.
    :param _pos: tick position, unused because log ticks are placed by
        value rather than by position.
    :returns: the tick label as a plain string, for example "100".
    """
    return "%g" % value


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

    :returns: mapping with keys ``sg`` (Sutton-Graves evaluator) and ``isa``
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
    Evaluate the Sutton-Graves correlation at fixed nose radius.

    :param velocity_kms: freestream velocity in km/s.
    :param nose_radius_m: nose radius in metres.
    :param solver: mapping returned by :func:`_load_solver`.
    :returns: stagnation heat flux in W/cm^2.
    """
    # Density is taken at the run altitude so that every curve shares one
    # freestream state; velocity is the only variable on the abscissa (A2).
    density = solver["isa"](H_RUN_KM)["density_kgm3"]

    # Thesis-adopted constant (A1): curves and the baseline marker share this
    # single value so the figure matches its own caption and the official
    # Optimization_Attempt_1 record.
    c_sg = C_SG_THESIS
    q_wm2 = c_sg * (density / nose_radius_m) ** 0.5 * (velocity_kms * 1000.0) ** 3
    return q_wm2 / 1.0e4


def sg_at_radius(nose_radius_m: float, velocity_kms: float, solver: dict[str, Any]) -> float:
    """
    Evaluate the Sutton-Graves correlation at fixed velocity.

    :param nose_radius_m: nose radius in metres.
    :param velocity_kms: freestream velocity in km/s.
    :param solver: mapping returned by :func:`_load_solver`.
    :returns: stagnation heat flux in W/cm^2.
    """
    return sg_at_velocity(velocity_kms, nose_radius_m, solver)


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

    # Rule 4: no two printed labels may overlap. The three checks above are
    # blind to this class: they test tick spacing along one row, one font
    # size, and one arrowhead. A rendered audit then found four labels that
    # broke every one of those rules while overlapping anyway, namely the
    # legend title struck through panel (a)'s x label, the panel (a) title
    # overprinted on its own last word, an annotation box printed across
    # panel (b)'s left spine, and a gutter x tick label touching panel (b)'s
    # y label. The guard lives in fig_metrics so every generator gets it.
    for left, right, width_pt, height_pt in fm.text_overlaps_pt(fig, scale):
        raise RuntimeError(
            "printed labels overlap by %.2f x %.2f pt: %r against %r; "
            "shorten or reposition one of them"
            % (width_pt, height_pt, left, right)
        )

    # Rule 5: a framed annotation placed in axes fraction is positioned by
    # its anchor, not by its width, so a long label anchored well inside can
    # still stick out of a spine and print across the neighbouring panel.
    for axes, name in ((parts["ax1"], "ax1"), (ax2, "ax2")):
        for text, leaks in fm.annotation_boxes_inside_axes_pt(axes, fig, scale):
            detail = ", ".join("%s %.2f pt" % (side, amount)
                               for side, amount in sorted(leaks.items()))
            raise RuntimeError(
                "annotation box on %s leaves its axes (%s): %r; move its "
                "xytext or shorten its text" % (name, detail, text)
            )

    # Rule 6: nothing, of any kind, may leave the canvas. print_fit scans Text,
    # Patch and Legend, and the Legend arm exists because a legend is neither a
    # Text nor a Patch, so both this guard and the overlap guard used to skip
    # it. The container for a legend placed with bbox_to_anchor is the CANVAS,
    # not the cell axes it belongs to, which is why the check is the shared
    # canvas assertion rather than legend_boxes_inside_axes_pt.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import print_fit as pf  # local print geometry library

    pf.assert_inside_canvas(fig)
    print("[sutton_graves_parametric] no label overlaps, no box leaves its "
          "axes, and nothing leaves the canvas")


def main() -> int:
    """
    Render the two-panel Sutton-Graves figure and save it as a PNG.

    :returns: process exit status (0 on success).
    :raises Exception: any failure propagates so the build is visibly broken
        rather than shipping a stale figure.
    """
    solver = _load_solver()

    # === Baseline via the SAME adopted-constant path as the curves (T3) ====
    # The solver FFI entry (engine-default C_SG) returned 15.36 W/cm^2 and
    # contradicted the caption's 16.14; one code path now serves the marker,
    # the curves and the annotation.
    baseline = sg_at_velocity(V_RUN_MS / 1000.0, R_N_BASELINE_M, solver)
    print("[sutton_graves_parametric] adopted-constant baseline: %.4f W/cm2"
          % baseline)

    parts = build_figure(solver, baseline)
    fig = parts["fig"]

    import matplotlib.pyplot as plt  # backend already forced to Agg in there

    # === Atomic write: temp file then rename (see module docstring) =========
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "sutton_graves_parametric.png")
    tmp_path = out_path + ".tmp.png"
    # print_fit owns the fit loop and the print scale. close=False keeps
    # the artist tree alive for verify(), which measures the written
    # file and the axes that produced it.
    pf.save_to_print_width(
        fig, os.path.basename(tmp_path), PRINT_W_IN, dpi=SAVE_DPI,
        label="sutton", close=False)
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
    from matplotlib.ticker import FuncFormatter, NullFormatter

    # SIZE AXIOM (goal rev 5): the canvas is built at exactly the width it
    # prints at (0.9\textwidth = 4.96 in) and the save loop in main() holds it
    # there, so the print scale is 1.0 and a declared point size IS the
    # printed point size. The previous 7.0 in canvas printed at scale 0.7082,
    # which silently shrank every mathtext SUBSCRIPT to 0.7 x 12 x 0.7082 =
    # 5.95 pt, well under the 8 pt floor; verify() measured and rejected it.
    # At scale 1.0 the 12 pt label prints a 12 x 0.7 = 8.4 pt subscript,
    # which clears the floor.
    plt.rcParams["xtick.labelsize"] = 12
    plt.rcParams["ytick.labelsize"] = 12

    # Layout AXIOM (goal rev 5): the panel (a) legend has 10 entries. At the
    # 8 pt printed floor it is 10 x ~10.5 pt = 1.47 in tall, which can never
    # fit inside a panel without covering curves, so BOTH legends live in a
    # dedicated row below their own panel. Panels stay on top; legend cells
    # (axes switched off) hold the legends.
    # The height follows the printed width so that the aspect ratio of the
    # committed artwork is preserved: 4.2 in at 7.0 in wide is 0.6, so
    # 0.6 x PRINT_W_IN keeps the same shape at scale 1.0.
    #  HEIGHT IS THE CLEARANCE LEVER (2026-10-06).
    #
    #  WHY: save_to_print_width pins the PRINTED WIDTH to PRINT_W_IN, so the
    #  print scale == and therefore every declared font size in points == is
    #  fixed by the width alone and cannot be traded for clearance. The only
    #  remaining freedom is the figure HEIGHT, and printed clearance in points
    #  scales with it at fixed width and fixed gridspec fractions.
    #
    #  WHY NOT THE TWO REMEDIES verify() NAMES. Lowering ARROW_TARGET_Q would
    #  move the arrow tip off the dashed baseline it exists to point at: the tip
    #  is placed AT the baseline and the baseline is the one line excluded from
    #  the clearance test (skip=(baseline_line,)). Raising AX2_Y_MIN would
    #  squeeze the empty band that the annotation box needs == the band below
    #  the lowest plotted point (about 8.0 W/cm^2) is the deliberate design
    #  documented at AX2_Y_MIN. Shrinking the data range fixes the arrow by
    #  cropping the artwork.
    #
    #  MEASURED: at 0.78 the arrowhead cleared the V = 3 km/s curve by only
    #  5.78 pt against a 6.40 pt floor (head 5.40 pt plus 1.00 pt margin) and
    #  verify() raised. 0.78 -> 0.88 multiplies the vertical scale by 1.128,
    #  predicting about 6.52 pt of clearance. Everything else is unaffected or
    #  better: the width-driven print scale and all font sizes are unchanged
    #  (so the 8.41 pt smallest-text floor still holds), the tick gaps grow,
    #  and the empty annotation band gains height rather than losing it.
    #
    #  CITATION: matplotlib figure sizing is in inches and is independent of
    #  the raster dpi (https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.html).
    fig = plt.figure(figsize=(PRINT_W_IN, 0.88 * PRINT_W_IN))
    fig.patch.set_facecolor("white")
    # Margins widened from left 0.09 / right 0.98 / top 0.90 / bottom 0.10
    # because probe_overhang.py measured the panel y-labels and the 10000 tick
    # hanging 0.221 in and 0.057 in off the canvas at the native printed
    # width. Fonts are absolute in points, so shrinking the canvas does not
    # shrink them and the overhang persisted; the margin must absorb it.
    # The legend row is taller and the row gap larger than the measured
    # (2.2, 1.5) / hspace 0.62. probe_sutton_geom.py measured panel (a)'s x
    # label and the panel (a) legend title on the same rows, merging into one
    # 136 px = 17.00 pt ink band with the two baselines 6.25 pt apart, because
    # the legend is anchored at loc="center" in a row that sat directly under
    # a 120 pt wide panel. A taller legend row plus a larger hspace moves the
    # centred legend text down and away from the panel x labels. Both legends
    # are still centred, so the change is symmetric across the two columns.
    gs = fig.add_gridspec(
        2, 2, height_ratios=(2.2, 1.9), hspace=1.15, wspace=0.32,
        left=0.17, right=0.95, top=0.80, bottom=0.13)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    lg1 = fig.add_subplot(gs[1, 0])
    lg2 = fig.add_subplot(gs[1, 1])
    lg1.axis("off")
    lg2.axis("off")

    velocities = V_SWEEP_KMS
    radii = R_SWEEP_M

    # === Panel (a): q vs velocity for several nose radii ===================
    for r_n in radii:
        y = [sg_at_velocity(v, r_n, solver) for v in velocities]
        style = dict(lw=2.6, zorder=3)
        # Legend entries carry the radius VALUE only. Measured on the
        # unsaved figure: repeating the variable name in every entry made the
        # ten-entry block about 3.4 in wide inside a 2.2 in panel, and the
        # block hung 0.47 in off the left edge of the canvas, which is why
        # the print fit loop could not converge. The variable name now sits
        # once in the legend title, and the caption and AccSupp already name
        # both the variable and its 0.1 to 3.0 m range, so no information is
        # lost.
        if abs(r_n - R_N_BASELINE_M) < 1e-9:
            style.update(color="black", lw=3.2)
            label = "%g (baseline)" % r_n
        else:
            style.update(color="tab:blue", alpha=0.55)
            label = "%g" % r_n
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
        # Three short lines. Measured: the two-line form was 130.33 pt wide
        # inside a 120.08 pt panel, so its framed box hung 20.80 pt LEFT of
        # panel (a)'s left spine and reached the y-axis label and the '10' tick.
        # Splitting the words so the longest line is "16.14 W/cm$^2$" keeps the
        # patch inside the panel.
        "IRVE-3 run\ncondition\n%.2f W/cm$^2$" % baseline,
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
        xytext=(0.95, 0.075),
        textcoords="axes fraction",
        fontsize=13,
        ha="right",
        va="bottom",
        arrowprops=dict(arrowstyle="->", lw=1.8, color="black"),
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black", lw=1.1),
    )

    ax1.set_yscale("log")
    # Plain decimal ticks: see _plain_tick for the measured 5.95 pt
    # exponent that the default mathtext log formatter produced.
    ax1.yaxis.set_major_formatter(FuncFormatter(_plain_tick))
    # The minor log ticks KEEP their tick marks but carry NO lettering.
    # Measured on the rendered page at 8 px per point: labelling every minor
    # tick put 18 tick centres on a 667 px = 83.38 pt ink band at a pitch down
    # to 11 px = 1.38 pt, which is a solid black smear rather than numbers.
    # NullFormatter is used rather than minorticks_off() because minorticks_off()
    # would also remove the minor tick marks, and ax1.grid(True, which="both")
    # needs them to keep its minor gridlines. ax2 already does this at the
    # ax2.minorticks_off() call below.
    ax1.yaxis.set_minor_formatter(NullFormatter())
    # Two lines, because probe_sutton_geom.py measured this label 195.84 pt
    # wide inside a 120.08 pt panel, so it hung 37.9 pt past the LEFT canvas
    # edge and 37.9 pt into the 38.43 pt gutter between the panels. Each half
    # of the split measures 60 to 110 pt and fits the panel.
    ax1.set_xlabel(
        "Freestream velocity\n$V_\\infty$ [km/s]",
        fontsize=13,
    )
    # Explicit ticks with plain digits. Measured: the sweep runs from 2 to
    # 10 km/s, so the default ticker chose 0, 5, 10 and 15. The axes clipped
    # 0 and 15 away and panel (a) was left carrying exactly ONE x tick label,
    # and that one was drawn as $\mathdefault{10}$, the mathtext form that
    # prints its digits at the parent's size but is inconsistent with the
    # plain-digit y ticks beside it. Five labels over the 2 to 10 span give a
    # 30 pt pitch inside a 120.08 pt panel, and every one is inside the window
    # so none is clipped.
    ax1.set_xticks(A1_X_TICKS_KMS)
    ax1.set_xticklabels(["%g" % v for v in A1_X_TICKS_KMS], fontsize=13)
    # Rotated, so its box width is the line height (15.84 pt) and its box
    # height is the string length. At 13 pt the string measures about 200 pt,
    # which is longer than the 70.28 pt panel, so the box overhangs the panel
    # vertically. That is harmless here because the overhang runs into the
    # 55.73 pt of canvas above the panel and the 117.59 pt below it, both of
    # which are free of other ink; assert_inside_canvas proves it.
    ax1.set_ylabel(r"Stagnation heat flux $\dot{q}_s$ [W/cm$^2$]", fontsize=13)
    # Two lines, because panel (a) measures 120.08 pt wide and the single line
    # measured about 140 pt, so its last word overprinted itself at the right
    # end. Each half of the split measures 60 to 90 pt and fits.
    ax1.set_title(
        "(a) $\\dot{q}_s$ vs $V_\\infty$\n($h$ = 51.8 km)",
        fontsize=13,
    )
    ax1.grid(True, which="both", alpha=0.3, ls=":")
    _h1, _l1 = ax1.get_legend_handles_labels()
    legend_a = lg1.legend(
        _h1, _l1,
        fontsize=12,
        ncol=2,
        loc="center",
        frameon=False,
        title="Nose radius [m]",
        title_fontsize=12,
    )
    legend_a.get_title().set_fontweight("bold")

    # === Panel (b): q vs nose radius at several Mach numbers ===============
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
        ls=(0, (6, 4)),
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
        # Shortened from "$R_N$ = 1.5 m (IRVE-3)". The measured panel (b) is
        # 120.08 pt wide and the longer label measured about 118 pt, so
        # right-anchored at 0.60 axes fraction the patch hung 42.38 pt LEFT of
        # panel (b)'s left spine and reached 3.50 pt inside panel (a). Nothing
        # is lost by dropping "(IRVE-3)": the caption states "The IRVE-3 run
        # condition ($R_N$ = 1.5~m, $V_{\infty}$ = 3.378~km/s) is marked", the
        # panel (a) legend carries the black entry "1.5 (baseline)", and the
        # dashed line this arrow names IS the baseline radius.
        "$R_N$ = 1.5 m",
        xy=(R_N_BASELINE_M, ARROW_TARGET_Q),
        # LEFT anchored at 0.05 axes fraction, inside the left spine. The
        # dashed baseline sits at 0.796 of the log axis, so an arrow running
        # right from this anchor crosses no curve: the V = 3 curve only
        # descends into the empty band at the far right of the panel.
        xytext=(0.05, 0.045),
        textcoords="axes fraction",
        fontsize=ARROW_FONTSIZE_PT,
        ha="left",
        va="bottom",
        # shrinkB=0 makes the tip land exactly on the dashed line. matplotlib
        # shrinks a FancyArrowPatch by 2 points at each end by default, which
        # left the tip 2.38 pt short of the line on the rendered page; the
        # 1.6 pt stroke of the dashed line then absorbs the tip.
        arrowprops=dict(
            arrowstyle="->", lw=1.6, color="black",
            shrinkA=0, shrinkB=0,
        ),
        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="black", lw=1.1),
    )

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.yaxis.set_major_formatter(FuncFormatter(_plain_tick))
    ax2.yaxis.set_minor_formatter(NullFormatter())
    # Only the thinned subset carries lettering; see X_TICKS_M for the
    # measurement that forced the subset.
    ax2.set_xticks(X_TICKS_M)
    ax2.set_xticklabels([("%g" % r) for r in X_TICKS_M])
    ax2.minorticks_off()
    ax2.set_xlabel(r"Nose radius $R_N$ [m]", fontsize=13)
    ax2.set_ylabel(r"Stagnation heat flux $\dot{q}_s$ [W/cm$^2$]", fontsize=13)
    ax2.set_title(
        # Two lines, because panel (b) measures 120.08 pt wide and the single
        # line measured about 140 pt, so its tail overprinted itself. Each half
        # of the split measures 60 to 90 pt and fits.
        "(b) $\\dot{q}_s$ vs $R_N$\n($\\propto 1/\\sqrt{R_N}$)",
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
        # The legend cells travel with the figure because verify() measures
        # their boxes against their own axes.
        "lg1": lg1,
        "lg2": lg2,
        "baseline_line": baseline_line,
    }


if __name__ == "__main__":
    sys.exit(main())
