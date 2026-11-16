#!/usr/bin/env python3
"""Replace the generic template flowchart with the pipeline this work actually
executes.

WHY THIS REPLACEMENT IS NECESSARY
AXIOM: `figures/flowchart.png` (since removed from the repository as dead
artwork) was captioned in the Introduction as "Research
methodology flowchart" and its alt text claimed an "eleven-stage numerical
research workflow". Inspecting the artwork shows neither is true. Transcribed
verbatim, its boxes read:

    Start
    Various of papers Study
    Literature Study
    Data Retrieval and Familiar Study Collection
    Replicate Axisymmetric Slice Model Design?
    Simulate the Geometry in Mach 5-6      [flag] WRONG PHYSICS
    Simulation Result
    Theoretically valid? or within error range?
    Data Analysis Simulation
    Conclusion and Recommendation
    End

Three separate defects:
  1. It says "Mach 5-6". This study is at Mach 10.29, and the trajectory
     profile spans Mach 27.5 down to 0.5. The label contradicts the thesis.
  2. The upper half is generic literature-review boilerplate, not methodology.
  3. It never shows the stages that constitute this work: parametric geometry
     generation, the DSMC solver, PINN refinement, or the optimisation loop.
The same file was also reused in Chapter 3, so the wrong figure appeared twice.

WHY THIS FILE KEEPS ITS OWN FIT LOOP INSTEAD OF CALLING print_fit
print_fit.save_to_print_width fits the saved width to a target printed WIDTH.
This figure is included as width=\textwidth together with
height=0.72\textheight and keepaspectratio, so its printed size is limited by
the printed HEIGHT and its aspect (0.78) is deliberately smaller than the
height-to-width ratio of the page area (0.8205). Fitting to width would
therefore optimise the dimension that does not constrain the result. The loop
below fits to PRINT_H_IN and the floor check uses the height-limited scale.

The replacement is built from the stages the engine actually executes. The
eleven numbered stages are those printed by the full validation pipeline
(`Run_Validate_Full`, stellarorion_program_proc/src/simulation_engine/
stellarorion_test_modes.adb:1147 onward), in the order that function runs them:

    1  flight parameters            7  parse SPARTA surface dumps
    2  geometry quality assurance    8  flight metrics
    3  generate HIAD surface         9  survivability check
    4  write solver input           10  sanity checks
    5  build solver container       11  compare against IRVE-3 flight data
    6  run DSMC simulation          12  export fields, series and plots

The optimisation loop is shown separately because it is driven by the cost
function of Sec. cost_function and gated by Sec. gate_methodology, not by the
validation pipeline itself.

PRINT-SCALE AXIOMS (goal rev 5: all figure text >= 8 pt printed)
  AXIOM: printed point size = declared point size x (print box / saved image).
  THEORIES: the chapter includes this PNG with width<=textwidth and
    height<=0.72\textheight (keepaspectratio), so the print box is
    5.51181 in x 6.71811 in. If the saved aspect stays under
    5.51181/6.71811 = 0.8205 the figure is height-capped and the scale is 1.0,
    so declared pt == printed pt. Width-inflation of the tight crop (a title
    wider than the canvas) previously broke that equality and shrank every
    label; the fit checks below fail the build instead.
  APPLICATIONS: every label is declared at LABEL_FS = 8.4 pt, titles are
    asserted to fit the canvas, box labels are asserted to fit their boxes,
    and the final scale is asserted >= 8/8.4 so nothing prints under 8 pt.
  ERRORS: SystemExit with the offending string on any fit or scale failure.

CITATION
  Matplotlib, https://matplotlib.org/stable/
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402  (arc sampling in terminator())
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

# Typography: the thesis body is set in Times, and matplotlib's default
# DejaVu Sans reads as generic Arial beside it. The figure inherits Times
# New Roman (present on this system; resolved via findfont) with STIX
# mathtext so inline math (J(x), q <= Q_target) matches the same serif.
# [Reference: matplotlib font family configuration -
#  https://matplotlib.org/stable/users/explain/text/font_family.html]
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

OUT = Path(__file__).resolve().parent / "fignew_pipeline.png"

# Colourblind-safe (Paul Tol): blue, yellow, magenta, green, teal, red.
C_INPUT = "#DDAA33"
C_PROCESS = "#004488"
C_CHECK = "#BB5566"
C_OUTPUT = "#228833"
C_EDGE = "#333333"

# Printed size, derived from the document geometry rather than chosen:
#     text height = 29.7 cm - 3 cm - 3 cm = 23.7 cm = 9.33071 in
# The chapter inserts this figure with height = 0.72\textheight, so the printed
# box is 0.72 * 9.33071 = 6.718 in tall and at most \textwidth = 5.51181 in
# wide. AXIOM: a figsize is inches of the SAVED image and the document rescales
# it, so the effective scale is min(print_w / saved_w, print_h / saved_h).
# Aspect 0.78 < 0.8205 keeps the figure height-capped at scale 1.0, which is
# what makes LABEL_FS print at 8.4 pt.
#
# WHY THE CANVAS IS THIS TALL AND NOT SHORTER.  Every box below is positioned
# in axes FRACTIONS, so a box's printed height is (its fraction) x PRINT_H_IN
# while its type stays an absolute point size.  Cutting PRINT_H_IN therefore
# shrinks the boxes and leaves the labels where they are.  Measured on
# 2026-10-06 with figures/probe_text_in_boxes.py: at PRINT_H_IN = 3.307 in the
# five two-line loop labels measured a 22.68 pt layout extent inside a
# 17.50 pt box interior, an overflow of 2.58 pt above and below, and the
# generator's own check_fits passed because that check compares WIDTH only.
# At PRINT_H_IN = 6.718 in the same boxes are 37.4 pt tall and clear.
#
# A shorter landscape canvas was tried on 2026-10-06 to suit the 16:9 beamer
# deck in Week 16 LaTeX, whose \PlotFrame height-caps every figure at
# 0.60\textheight.  That deck is outside the scope of this thesis, and the
# resize traded a correct thesis figure for a broken one, so it is reverted
# here.  Anyone redoing it must re-author the layout fractions AND add the
# vertical fit check, not just change one constant.
TEXT_H_IN = 29.7 / 2.54 - (3.0 + 3.0) / 2.54      # 9.33071
PRINT_H_IN = 0.72 * TEXT_H_IN                      # 6.71811
PRINT_W_IN = 5.51181
WIDTH_IN = PRINT_H_IN * 0.78                       # 5.240

# Declared point size of every label. 8.4 gives headroom above the 8 pt floor.
LABEL_FS = 8.4
# A box label must be at least this much narrower than its box (inches).
FIT_MARGIN_IN = 0.04


def box(ax, x, y, w, h, text, fc, fs=LABEL_FS, style="round,pad=0,rounding_size=0.02"):
    """Draw one rounded stage box with a centred label.

    Parameters:
        ax: matplotlib Axes in figure fraction coordinates (position 0..1).
        x, y, w, h: box rectangle in axes fraction coordinates.
        text: label string (may contain newlines).
        fc: face colour; white label text when fc is the dark process blue.
        fs: declared point size (default LABEL_FS = 8.4).
        boxstyle: FancyBboxPatch style string; pad is 0 so the drawn border
            sits exactly on (x, y, w, h) and the fit check is exact.

    Returns:
        (box_width_fraction, text_artist) for the fit-check pass.

    Raises: none; overflow is detected later by check_fits().
    """
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=style, linewidth=0.9,
        edgecolor=C_EDGE, facecolor=fc, zorder=2))
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color="white" if fc == C_PROCESS else "black",
                zorder=3, linespacing=1.35)
    return w, t


def io_box(ax, x, y, w, h, text, fc, fs=LABEL_FS, slant_in=0.05):
    """Draw one input/output parallelogram with a centred label.

    ISO 5807 data symbol: a right-leaning parallelogram, distinct from the
    rectangular process boxes so the diagram reads by shape alone.

    Parameters:
        ax: matplotlib Axes in figure fraction coordinates (position 0..1).
        x, y, w, h: box rectangle in axes fraction coordinates (bottom edge).
        text: label string (may contain newlines).
        fc: face colour; white label text when fc is the dark process blue.
        fs: declared point size (default LABEL_FS = 8.4).
        slant_in: horizontal offset of the top edge in INCHES, converted to
            axes fraction here because x fractions map to WIDTH_IN inches.

    Returns:
        (box_width_fraction, text_artist) for the fit-check pass; the text
        sits on the vertical mid line where the shape is still w wide.

    Raises: none; overflow is detected later by check_fits().
    """
    s = slant_in / WIDTH_IN
    ax.add_patch(Polygon([(x, y), (x + w, y), (x + w + s, y + h), (x + s, y + h)],
                         closed=True, linewidth=0.9, edgecolor=C_EDGE,
                         facecolor=fc, zorder=2))
    t = ax.text(x + w / 2 + s / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color="white" if fc == C_PROCESS else "black",
                zorder=3, linespacing=1.35)
    return w, t


def terminator(ax, x, y, w, h, text, fs=LABEL_FS):
    """Draw one dedicated Start/Stop terminal as an EXACT stadium.

    WHY A POLYGON AND NOT FancyBboxPatch: this figure's axes are fraction
    coordinates whose x and y scales differ (WIDTH_IN vs PRINT_H_IN inches),
    so FancyBboxPatch's rounding_size draws anisotropic elliptical corners
    (measured cap depth 14 px vs the 27 px a stadium requires; audit-1
    FAIL). Building the outline in PHYSICAL inches -- semicircular caps of
    radius h/2 at both ends -- and converting back to fractions gives true
    stadium geometry at any canvas aspect.

    Parameters:
        ax: matplotlib Axes in figure fraction coordinates (position 0..1).
        x, y, w, h: terminal rectangle in axes fraction coordinates.
        text: "Start" or "Stop".
        fs: declared point size (default LABEL_FS = 8.4).

    Returns:
        (box_width_fraction, text_artist) for the fit-check pass.

    Raises: none; overflow is detected later by check_fits().
    """
    # Physical-inch rectangle and cap radius.
    xi, yi = x * WIDTH_IN, y * PRINT_H_IN
    wi, hi = w * WIDTH_IN, h * PRINT_H_IN
    r = hi / 2.0
    cx0, cx1 = xi + r, xi + wi - r          # cap centres
    cyc = yi + r                             # centre line
    n = 48                                   # points per semicircle
    pts_in = []
    for k in range(n + 1):                   # right cap: bottom -> top
        a = -np.pi / 2 + np.pi * k / n
        pts_in.append((cx1 + r * np.cos(a), cyc + r * np.sin(a)))
    for k in range(n + 1):                   # left cap: top -> bottom
        a = np.pi / 2 + np.pi * k / n
        pts_in.append((cx0 + r * np.cos(a), cyc + r * np.sin(a)))
    verts = [(px / WIDTH_IN, py / PRINT_H_IN) for px, py in pts_in]
    ax.add_patch(Polygon(verts, closed=True, linewidth=0.9,
                         edgecolor=C_EDGE, facecolor="white", zorder=2))
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color="black", zorder=3, linespacing=1.35)
    return w, t


def arrow(ax, p0, p1, style="-|>", ls="-", color=C_EDGE, lw=1.5, rad=0.0):
    """Draw one connector.

    zorder 5 so the connector is drawn OVER the boxes. At zorder 1 with
    mutation_scale 8 the connectors were completely hidden and the diagram read
    as twelve unconnected boxes.

    Parameters:
        ax: matplotlib Axes; p0, p1: endpoints in axes fraction coordinates.
        style, ls, color, lw, rad: FancyArrowPatch appearance (arc3 curvature).

    Returns: None. Raises: none.
    """
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle=style, linestyle=ls, color=color, linewidth=lw,
        mutation_scale=13, connectionstyle=f"arc3,rad={rad}", zorder=5))


def check_fits(fig, checks, what):
    """Assert drawn text extents fit their allowed width.

    Parameters:
        fig: the Figure (Agg canvas; drawn before calling).
        checks: list of (Text artist, allowed width in inches, context string).
        what: label used in the error message ("box" or "canvas").

    Returns: None. Prints one line per label.
    Raises: SystemExit listing every overflowing label.
    """
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    bad = []
    for t, allow_in, ctx in checks:
        tw_in = t.get_window_extent(renderer=rend).width / fig.dpi
        ok = tw_in <= allow_in - FIT_MARGIN_IN if what == "box" \
            else tw_in <= allow_in
        tag = "ok" if ok else "OVERFLOW"
        print(f"  [{tag}] {ctx}: {t.get_text()!r} text {tw_in:.2f} in"
              f" / allowed {allow_in:.2f} in")
        if not ok:
            bad.append(t.get_text())
    if bad:
        raise SystemExit(f"fit check ({what}) failed for: {bad}")


def main() -> int:
    """Build fignew_pipeline.png.

    Returns: 0 on success.
    Raises: SystemExit when a label overflows its box, a title overflows the
        canvas, or the final print scale would put labels below 8 pt.
    """
    fig, ax = plt.subplots(figsize=(WIDTH_IN, PRINT_H_IN))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # Full-canvas axes: every fraction below is a fraction of the figure, so
    # box widths map 1:1 onto inches and the fit math stays exact. tight_layout
    # is deliberately NOT called: it would re-shrink the axes position.
    ax.set_position([0, 0, 1, 1])

    fits_box = []    # (text artist, box width in inches, context)
    fits_canvas = []  # (text artist, canvas width in inches, context)

    title = ax.text(0.5, 0.992, "Validation pipeline executed by the engine",
                    ha="center", va="top", fontsize=LABEL_FS, weight="bold")
    fits_canvas.append((title, WIDTH_IN, "title"))
    sub = ax.text(0.5, 0.966,
                  "Stages in execution order, as printed by the full validation run",
                  ha="center", va="top", fontsize=LABEL_FS, style="italic")
    fits_canvas.append((sub, WIDTH_IN, "subtitle"))

    stages = [
        ("1  Flight parameters", C_INPUT),
        ("2  Geometry quality assurance", C_PROCESS),
        ("3  Generate HIAD surface", C_PROCESS),
        ("4  Write solver input script", C_PROCESS),
        ("5  Build solver container", C_PROCESS),
        ("6  Run DSMC simulation", C_PROCESS),
        ("7  Parse surface dumps", C_PROCESS),
        ("8  Compute flight metrics", C_PROCESS),
        ("9  Survivability check", C_CHECK),
        ("10  Sanity checks", C_CHECK),
        ("11  Compare with IRVE-3 flight", C_PROCESS),
        ("12  Export fields and plots", C_OUTPUT),
    ]
    # Two columns spanning the full canvas. The vertical gap between the
    # two columns is deliberately kept wide: the 6 -> 7 wrap arrow is routed
    # through it, so it never crosses a box. top/gap were re-solved when the
    # dedicated Start terminator was added above stage 1: top dropped 0.905 ->
    # 0.885 and gap 0.030 -> 0.026 so the column BOTTOM stays at 0.335,
    # preserving the wrap-lane clearance below both columns.
    n_per_col, w, h = 6, 0.46, 0.070
    x_left, x_right = 0.010, 0.530
    top, gap = 0.885, 0.026
    lane_y = 0.330                      # clear lane below both columns
    assert len(stages) == n_per_col * 2

    pos = {}
    for i, (label, fc) in enumerate(stages):
        col, row = i // n_per_col, i % n_per_col
        x0 = x_left if col == 0 else x_right
        y0 = top - row * (h + gap) - h
        # ISO 5807 symbol set: stage 1 (Flight parameters) is the data ENTRY
        # and stage 12 (Export fields and plots) the data EXIT, so those two
        # are input/output parallelograms; every other stage is a process and
        # keeps the rectangle. The dedicated labeled Start/Stop terminals are
        # separate nodes below — the first/last stages are real steps, not
        # terminators, so rounding them would conflate process and terminal.
        if i in (0, len(stages) - 1):
            bw, t = io_box(ax, x0, y0, w, h, label, fc)
        else:
            bw, t = box(ax, x0, y0, w, h, label, fc)
        fits_box.append((t, bw * WIDTH_IN, f"stage {i + 1}"))
        pos[i] = (x0, y0)

    # Dedicated terminals: ONE labeled "Start" oval above stage 1 and ONE
    # labeled "Stop" oval below stage 12 (the flow's true end after the
    # wrap). Exact stadium geometry via terminator() -- see its docstring.
    term_w, term_h = 0.12, 0.026
    sx_c = x_left + w / 2
    bw, t = terminator(ax, sx_c - term_w / 2, 0.900, term_w, term_h, "Start")
    fits_box.append((t, bw * WIDTH_IN, "Start terminator"))
    ax.annotate("", xy=(sx_c, 0.885), xytext=(sx_c, 0.900),
                arrowprops=dict(arrowstyle="-|>", color="black",
                                linewidth=1.6, mutation_scale=13), zorder=5)
    ex_c = x_right + w / 2
    bw, t = terminator(ax, ex_c - term_w / 2, 0.290, term_w, term_h, "Stop")
    fits_box.append((t, bw * WIDTH_IN, "Stop terminator"))
    ax.annotate("", xy=(ex_c, 0.316), xytext=(ex_c, 0.335),
                arrowprops=dict(arrowstyle="-|>", color="black",
                                linewidth=1.6, mutation_scale=13), zorder=5)

    # Intra-column connectors: solid black, drawn over the boxes, long enough to
    # read at print size.
    for col in range(2):
        for row in range(n_per_col - 1):
            i = col * n_per_col + row
            x0, y0 = pos[i]
            ax.annotate("", xy=(x0 + w / 2, y0 - gap), xytext=(x0 + w / 2, y0),
                        arrowprops=dict(arrowstyle="-|>", color="black",
                                        linewidth=1.6, mutation_scale=13), zorder=5)

    # Wrap 6 -> 7: down the left edge of column 1, across the clear lane below,
    # up through the gap BETWEEN the columns, then into the top of column 2.
    x_lc = x_left + w / 2
    x_gap = (x_left + w + x_right) / 2
    y_bot_left = pos[n_per_col - 1][1]
    y_top_right = pos[n_per_col][1] + h
    seg = [(x_lc, y_bot_left), (x_lc, lane_y), (x_gap, lane_y), (x_gap, y_top_right)]
    for a, b in zip(seg, seg[1:]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color="black", lw=1.6,
                solid_capstyle="butt", zorder=5)
    ax.annotate("", xy=(x_right + 0.020, y_top_right), xytext=seg[-1],
                arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.6,
                                mutation_scale=13), zorder=5)
    # The label sits BELOW the lane line, in the clear band between the column
    # bottoms (y 0.335) and the loop title, so it crosses neither boxes nor the
    # wrap connector's vertical run.
    cont = ax.text(x_gap, lane_y - 0.016, "continues", fontsize=LABEL_FS,
                   ha="center", va="top", color="black")
    fits_canvas.append((cont, WIDTH_IN, "continues"))

    #  optimisation loop, its own row with room for the feedback path 
    loop_head = ax.text(0.5, 0.268, "Geometry optimization loop",
                        ha="center", va="top", fontsize=LABEL_FS, weight="bold")
    fits_canvas.append((loop_head, WIDTH_IN, "loop heading"))
    loop_sub = ax.text(0.5, 0.246,
                       "(driven by the cost function, gated by DSMC re-simulation)",
                       ha="center", va="top", fontsize=LABEL_FS, style="italic")
    fits_canvas.append((loop_sub, WIDTH_IN, "loop subheading"))
    loop = ["Design space\n(LHS or CCD)",
            "Bayesian\noptimization",
            "Cost function\n$J(x)$",
            "DSMC\nre-simulation",
            "Accept if\n$q \\leq Q_{target}$"]
    # 5*lw_ + 4*lgap must fit inside [0.020, 0.980]:
    # 5*0.182 + 4*0.012 = 0.958, ending at 0.978.
    lw_, lh, lgap = 0.182, 0.082, 0.012
    ly = 0.105                          # high enough that the lane below (0.03) is inside ylim
    for i, label in enumerate(loop):
        x0 = 0.020 + i * (lw_ + lgap)
        fc = C_CHECK if i == 3 else C_PROCESS
        # Symbol set: "Design space (LHS or CCD)" is the loop's data entry
        # (the candidate design set), so it is an input parallelogram; the
        # remaining loop boxes are processing steps and stay rectangles.
        if i == 0:
            bw, t = io_box(ax, x0, ly, lw_, lh, label, fc)
        else:
            bw, t = box(ax, x0, ly, lw_, lh, label, fc)
        fits_box.append((t, bw * WIDTH_IN, f"loop {i + 1}"))
        if i:
            ax.annotate("", xy=(x0, ly + lh / 2), xytext=(x0 - lgap, ly + lh / 2),
                        arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.4,
                                        mutation_scale=11), zorder=5)
    # Rejection feedback, routed strictly below the row so it crosses nothing.
    x_first = 0.020 + lw_ / 2
    x_last = 0.020 + 4 * (lw_ + lgap) + lw_
    fb_y = 0.045
    ax.plot([x_last, x_last, x_first, x_first], [ly, fb_y, fb_y, ly],
            color=C_CHECK, lw=1.4, zorder=5, solid_capstyle="butt")
    ax.annotate("", xy=(x_first, ly + 0.006), xytext=(x_first, fb_y),
                arrowprops=dict(arrowstyle="-|>", color=C_CHECK, linewidth=1.4,
                                mutation_scale=11), zorder=5)
    reject = ax.text((x_first + x_last) / 2, fb_y - 0.004, "reject and resample",
                     fontsize=LABEL_FS, ha="center", va="top", color=C_CHECK)
    fits_canvas.append((reject, WIDTH_IN, "feedback label"))

    # Every label must fit where it lives BEFORE anything is saved.
    check_fits(fig, fits_box, "box")
    check_fits(fig, fits_canvas, "canvas")

    # Fit the SAVED image to the printed height. bbox_inches="tight" crops to the
    # artist extents, so the saved height is not the figsize height; measuring the
    # crop once and rescaling by the reciprocal converges, and the result is
    # asserted rather than assumed.
    from PIL import Image

    target_px = PRINT_H_IN * 300
    for _ in range(4):
        fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
        got_px = Image.open(OUT).size[1]
        if abs(got_px - target_px) / target_px <= 0.005:
            break
        fw, fh = fig.get_size_inches()
        fig.set_size_inches(fw * target_px / got_px, fh * target_px / got_px,
                            forward=True)
    px = Image.open(OUT).size
    scale = PRINT_H_IN / (px[1] / 300)
    effective_pt = LABEL_FS * scale
    print(f"wrote {OUT.name} {px[0]}x{px[1]}px  print height {PRINT_H_IN:.3f} in  "
          f"scale {scale:.3f}  effective dpi {300 / scale:.0f}  "
          f"label {effective_pt:.2f} pt")
    if effective_pt < 8.0:
        raise SystemExit(
            f"effective label size {effective_pt:.2f} pt below 8 pt "
            f"(scale {scale:.3f}; saved aspect {px[0] / px[1]:.3f} exceeds the "
            f"height-capped limit {PRINT_W_IN / PRINT_H_IN:.3f})")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
