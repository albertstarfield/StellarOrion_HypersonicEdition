#!/usr/bin/env python3
"""Generate three methodology-chapter figures for the thesis.

PURPOSE
    Add three figures to Chapter 3 (Methodology) to match the standard
    layout's figure richness: a computational domain/mesh schematic, a
    multi-solver coupling diagram, and a result-extraction pipeline.

PARAMETERS
    None. Output paths are FIGDIR / "domain_mesh.png", FIGDIR /
    "solver_coupling.png", FIGDIR / "result_extraction.png".

RETURNS
    Process exit code 0 on success, 1 on rejection.

EXCEPTIONS
    RuntimeError if the print scale or the inside canvas check fails, if a
    drawn string contains a dash the thesis forbids, or if the smallest
    printed text falls below MIN_PRINTED_PT.

AXIOMS
    A1. Printed point size equals declared point size times the placement
        scale, so the scale must be measured from the written file, never
        assumed. (Source: print_fit.save_to_print_width.)
    A2. A string that is wider than the canvas makes the tight crop grow on
        every fit attempt, so the loop cannot converge and the artist must
        be rejected before the first save. (Source: print_fit axiom A3.)
    A3. The three figures share a visual style (box colors, arrow style,
        font sizes) so they read as a set.

THEORIES
    T1. A 2-D axisymmetric schematic with a coarse Cartesian mesh overlay
        communicates the SPARTA domain better than a photograph.
    T2. A box-and-arrow diagram with labeled data flows communicates the
        multi-solver coupling better than prose alone.
    T3. A linear pipeline diagram communicates the result-extraction
        workflow better than a table.

APPLICATIONS
    A1. The three figures replace the missing methodology-chapter figures
        in chapter_03 at the full text width.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  backend must be forced first
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.path import Path  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, shared measurement
import fig_shapes as fsh  # noqa: E402  sibling module, shared flowchart shapes
import print_fit as pf  # noqa: E402  sibling module, shared print geometry

# Typography: the thesis body is set in Times, and matplotlib's default
# DejaVu Sans reads as generic Arial beside it. These figures inherit Times
# New Roman (present on this system; resolved via findfont) with STIX
# mathtext so any inline math matches the same serif. The sibling generator
# make_pipeline_figure.py sets the identical triple, so every flowchart in
# the thesis reads as one type family.
# [Reference: matplotlib font family configuration -
#  https://matplotlib.org/stable/users/explain/text/font_family.html]
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

FIGDIR = pf.FIGDIR
assert FIGDIR.is_dir(), "figures directory not found: %s" % FIGDIR

PRINT_W_IN = 6.50
MIN_PRINTED_PT = 8.0

INK = "#212121"
HEADER_GRAY = "#757575"
INPUT_FILL = "#E5F3FD"
INPUT_EDGE = "#C0C1C2"
ENGINE_FILL = "#2871C5"
ENGINE_EDGE = "#1665C0"
SOLVER_FILL = "#3F8742"
SOLVER_EDGE = "#2F7D33"
ML_FILL = "#E85F14"
ML_EDGE = "#E65201"
OUTPUT_FILL = "#582795"
OUTPUT_EDGE = "#4B158C"
ARROW_COLOR = "#37474F"
ORANGE = "#E65100"


def box(ax: object, x0: float, y0: float, w: float, h: float,
        text: str, fill: str, edge: str, text_color: str = INK,
        fs: float = 9.5, bold: bool = False, linespacing: float = 1.3,
        rounding: float = 0.04) -> None:
    """Draw a rounded rectangle with centered text.

    :param ax: the axes to draw on.
    :param x0: left edge in inches.
    :param y0: bottom edge in inches.
    :param w: width in inches.
    :param h: height in inches.
    :param text: label string, may contain newlines.
    :param fill: face colour.
    :param edge: edge colour.
    :param text_color: text colour.
    :param fs: declared font size in points.
    :param bold: use bold weight when True.
    :param linespacing: line spacing multiplier.
    :param rounding: corner radius in inches; pass h/2 for oval flowchart
        start/end terminators, keep the default for process boxes.
    :returns: None.
    """
    patch = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={rounding}",
        linewidth=1.2, edgecolor=edge, facecolor=fill, zorder=2,
    )
    ax.add_patch(patch)
    weight = "bold" if bold else "normal"
    ax.text(x0 + w / 2, y0 + h / 2, text, ha="center", va="center",
            fontsize=fs, color=text_color, fontweight=weight, zorder=3,
            linespacing=linespacing)


def arrow(ax: object, p0: tuple, p1: tuple, color: str = ARROW_COLOR,
          lw: float = 1.4, rad: float = 0.0) -> None:
    """Draw a straight arrow from p0 to p1.

    :param ax: the axes to draw on.
    :param p0: start point as (x, y) tuple in inches.
    :param p1: end point as (x, y) tuple in inches.
    :param color: arrow colour.
    :param lw: line width in points.
    :param rad: arc3 curvature radius.
    :returns: None.
    """
    patch = FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=11.0,
        linewidth=lw, color=color, connectionstyle=f"arc3,rad={rad}",
        zorder=4,
    )
    ax.add_patch(patch)


def routed_arrow(ax: object, points: list, color: str = ARROW_COLOR,
                 lw: float = 1.4) -> None:
    """Draw a multi-segment arrow through the given points.

    :param ax: the axes to draw on.
    :param points: list of (x, y) tuples in inches defining the path.
    :param color: arrow colour.
    :param lw: line width in points.
    :returns: None.
    """
    verts = list(points)
    codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 1)
    path = Path(verts, codes)
    patch = FancyArrowPatch(
        path=path, arrowstyle="-|>", mutation_scale=11.0,
        linewidth=lw, color=color, zorder=4,
    )
    ax.add_patch(patch)


def draw_legend_row(ax: object, items: tuple, y: float,
                    patch_w: float = 0.08, patch_h: float = 0.10,
                    gap: float = 0.10, fs: float = 9.5) -> None:
    """Draw one row of legend items centered on the canvas.

    :param ax: the axes to draw on.
    :param items: tuple of (label, fill, edge) tuples.
    :param y: bottom edge of the legend row in inches.
    :param patch_w: width of each colour patch in inches.
    :param patch_h: height of each colour patch in inches.
    :param gap: gap between items in inches.
    :param fs: font size in points.
    :returns: None.
    """
    char_w = 0.55 * fs / 72.0
    total_w = 0.0
    for label, _, _ in items:
        total_w += patch_w + 0.04 + len(label) * char_w + gap
    total_w -= gap
    x = (PRINT_W_IN - total_w) / 2.0
    for label, fill, edge in items:
        ax.add_patch(Rectangle((x, y), patch_w, patch_h,
                               facecolor=fill, edgecolor=edge,
                               linewidth=0.8, zorder=2))
        ax.text(x + patch_w + 0.04, y + patch_h / 2, label,
                ha="left", va="center", fontsize=fs, color=INK, zorder=3)
        x += patch_w + 0.04 + len(label) * char_w + gap


def build_domain_mesh() -> object:
    """Build the computational domain and mesh schematic.

    :returns: the matplotlib figure, with the axes on it as its only axes.
    """
    H = 4.0
    fig = plt.figure(figsize=(PRINT_W_IN, H))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    title = "SPARTA Computational Domain and Cartesian Mesh"
    ax.text(PRINT_W_IN / 2.0, 3.85, title, ha="center", va="center",
            fontsize=13.0, fontweight="bold", color=INK)

    # Domain boundary (dashed)
    ax.plot([0.5, 0.5], [0.3, 3.5], linestyle="--", color=HEADER_GRAY,
            linewidth=1.0, zorder=1)
    ax.plot([0.5, 6.0], [3.5, 3.5], linestyle="--", color=HEADER_GRAY,
            linewidth=1.0, zorder=1)
    ax.plot([6.0, 6.0], [0.3, 3.5], linestyle="--", color=HEADER_GRAY,
            linewidth=1.0, zorder=1)

    # Symmetry plane (centerline style: alternating long and short dashes)
    ax.plot([0.5, 6.0], [0.3, 0.3], color=INK, linewidth=1.0,
            linestyle=(0, (8, 2, 2, 2)), zorder=1)

    # Cartesian mesh (coarse grid)
    for x in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]:
        ax.plot([x, x], [0.3, 3.5], color="#B0B0B0", linewidth=0.5, zorder=0)
    for y in [0.8, 1.3, 1.8, 2.3, 2.8, 3.3]:
        ax.plot([0.5, 6.0], [y, y], color="#B0B0B0", linewidth=0.5, zorder=0)

    # HIAD vehicle: smooth body-of-revolution cross-section (nose + toroidal body)
    import numpy as np
    from matplotlib.path import Path

    # Silhouette: tangent-ogive nose blending into a toroidal (inflatable) body.
    # Built as one closed path so the surface reads as a single aeroshell.
    nose_cx, nose_cy = 2.0, 0.3
    nose_r = 0.4

    # Nose: upper half of a circle (sitting on the symmetry plane)
    theta = np.linspace(0, np.pi, 40)
    nose_x = nose_cx + nose_r * np.cos(theta)      # 2.4 -> 1.6
    nose_y = nose_cy + nose_r * np.sin(theta)      # 0.3 -> 0.7

    # Body: torus-like cross-section extending aft (tangent to the nose top)
    body_x0 = nose_cx + nose_r                       # 2.4
    body_top = 0.75
    body_bot = 0.3
    body_x1 = 4.2

    # Upper contour of the body (smooth step from nose top to body top)
    tb = np.linspace(0, 1, 40)
    upper_x = body_x0 + (body_x1 - body_x0) * tb
    # Smoothstep blending the nose top (0.7) into the body top (0.75)
    blend = 3 * tb**2 - 2 * tb**3
    upper_y = nose_y[-1] + (body_top - nose_y[-1]) * blend

    # Lower contour (sits on the symmetry plane)
    lower_x = np.linspace(body_x1, body_x0, 40)
    lower_y = np.full_like(lower_x, body_bot)

    # Assemble the closed silhouette: nose (right-to-left) + upper body + lower body (left-to-right)
    sil_x = np.concatenate([nose_x, upper_x, lower_x])
    sil_y = np.concatenate([nose_y, upper_y, lower_y])

    verts = list(zip(sil_x, sil_y)) + [(sil_x[0], sil_y[0])]
    codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
    path = Path(verts, codes)
    from matplotlib.patches import PathPatch
    ax.add_patch(PathPatch(path, facecolor=SOLVER_FILL,
                           edgecolor=SOLVER_EDGE, linewidth=1.2, zorder=2))

    # Bow shock: convex upstream (left), detached ahead of the nose
    t = np.linspace(0, 1, 60)
    shock_y = 0.5 + 2.8 * t
    # Hyperbola-like curve: closest at the centreline (bottom), curving upstream
    shock_x = 1.0 - 0.35 * (1.0 - (1.0 - t)**2)     # 1.0 (bottom) -> 0.65 (top)
    ax.plot(shock_x, shock_y, linestyle="--", color=ORANGE,
            linewidth=1.5, zorder=1)

    # Labels
    ax.annotate("Farfield boundary", xy=(0.5, 3.5), xytext=(0.2, 3.55),
                fontsize=9.5, color=INK, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("Symmetry plane", xy=(4.0, 0.3), xytext=(4.5, 0.15),
                fontsize=9.5, color=INK, ha="center", va="bottom",
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("HIAD surface", xy=(2.0, 0.7), xytext=(1.2, 1.2),
                fontsize=9.5, color=INK, ha="center", va="bottom",
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("Bow shock", xy=(1.15, 2.0), xytext=(0.3, 2.5),
                fontsize=9.5, color=ORANGE, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.0))
    ax.annotate("Cartesian mesh\n(grid factor 0.7)", xy=(4.0, 2.0),
                xytext=(3.5, 2.8), fontsize=9.5, color=HEADER_GRAY,
                ha="center", va="bottom",
                arrowprops=dict(arrowstyle="->", color=HEADER_GRAY, lw=1.0))

    return fig


def build_solver_coupling() -> object:
    """Build the multi-solver coupling and data exchange diagram.

    :returns: the matplotlib figure, with the axes on it as its only axes.
    """
    H = 3.5
    fig = plt.figure(figsize=(PRINT_W_IN, H))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    title = "Multi-Solver Coupling and Data Exchange"
    ax.text(PRINT_W_IN / 2.0, 3.35, title, ha="center", va="center",
            fontsize=13.0, fontweight="bold", color=INK)

    # Box positions
    sparta_x0, sparta_y0, sparta_w, sparta_h = 0.3, 1.8, 1.4, 0.7
    openfoam_x0, openfoam_y0, openfoam_w, openfoam_h = 2.2, 1.8, 1.4, 0.7
    surv_x0, surv_y0, surv_w, surv_h = 4.1, 1.8, 1.4, 0.7
    pinn_x0, pinn_y0, pinn_w, pinn_h = 0.3, 0.5, 1.4, 0.7
    sur_x0, sur_y0, sur_w, sur_h = 2.2, 0.5, 1.4, 0.7
    ei_x0, ei_y0, ei_w, ei_h = 4.1, 0.5, 1.4, 0.7

    # Flowchart symbology: SPARTA, OpenFOAM, Survivability Check, PINN,
    # the GP surrogate and EI are all processing steps, so all six are
    # rectangles; the oval symbol (rounding = h/2) is reserved for the
    # dedicated Start/Stop terminators drawn below. The previous revision
    # rounded SPARTA and Survivability as pseudo-terminals, which
    # conflated process and terminal under the symbology directive.
    box(ax, sparta_x0, sparta_y0, sparta_w, sparta_h,
        "SPARTA\nDSMC Solver", SOLVER_FILL, SOLVER_EDGE, text_color="white")
    box(ax, openfoam_x0, openfoam_y0, openfoam_w, openfoam_h,
        "OpenFOAM\nSolid Thermal", SOLVER_FILL, SOLVER_EDGE, text_color="white")
    box(ax, surv_x0, surv_y0, surv_w, surv_h,
        "Survivability\nCheck", OUTPUT_FILL, OUTPUT_EDGE, text_color="white")
    box(ax, pinn_x0, pinn_y0, pinn_w, pinn_h,
        "PINN\nDeepXDE", ML_FILL, ML_EDGE, text_color="white")
    box(ax, sur_x0, sur_y0, sur_w, sur_h,
        "Bayes Opt Surrogate\nGP Matern 5/2", ML_FILL, ML_EDGE,
        text_color="white")
    box(ax, ei_x0, ei_y0, ei_w, ei_h,
        "EI Acquisition\nNext Design", ENGINE_FILL, ENGINE_EDGE,
        text_color="white")

    # Arrows: top row
    arrow(ax, (sparta_x0 + sparta_w, sparta_y0 + sparta_h / 2),
          (openfoam_x0, openfoam_y0 + openfoam_h / 2))
    arrow(ax, (openfoam_x0 + openfoam_w, openfoam_y0 + openfoam_h / 2),
          (surv_x0, surv_y0 + surv_h / 2))

    # Arrows: bottom row
    arrow(ax, (pinn_x0 + pinn_w, pinn_y0 + pinn_h / 2),
          (sur_x0, sur_y0 + sur_h / 2))
    arrow(ax, (sur_x0 + sur_w, sur_y0 + sur_h / 2),
          (ei_x0, ei_y0 + ei_h / 2))

    # Vertical arrows: SPARTA to PINN, OpenFOAM to the GP surrogate
    arrow(ax, (sparta_x0 + sparta_w / 2, sparta_y0),
          (pinn_x0 + pinn_w / 2, pinn_y0 + pinn_h))
    arrow(ax, (openfoam_x0 + openfoam_w / 2, openfoam_y0),
          (sur_x0 + sur_w / 2, sur_y0 + sur_h))

    # Feedback loop: EI back to SPARTA, carrying the new design. WHY the
    # right-margin route: the old path rose from EI's top centre (x=4.8)
    # straight through the Survivability Check box body, because both
    # columns share x=4.8 (pixel probe of the committed render found 615
    # orange #E65100 pixels inside x[4.1,5.5] y[1.8,2.5]). Exiting EI's
    # right edge, running up the right margin at x=6.4 (clear of the
    # Survivability right edge 5.5 and of the Stop terminal 6.25) and
    # entering SPARTA's top at x=1.0 touches no box body. The x=1.0
    # descent clears the 'surface heat flux' label only because that
    # label sits at x=1.62 (audit finding: at x=1.55 the shaft clipped
    # the leading 's', ink starting x~0.99 in).
    routed_arrow(ax, [
        (ei_x0 + ei_w, ei_y0 + ei_h / 2),
        (6.4, ei_y0 + ei_h / 2),
        (6.4, 2.8),
        (sparta_x0 + sparta_w / 2, 2.8),
        (sparta_x0 + sparta_w / 2, sparta_y0 + sparta_h),
    ], color=ORANGE)

    # Dedicated labeled terminals (ISO 5807 ovals): Start feeds SPARTA,
    # the coupling cycle's entry, from above at x=0.7 -- 0.3 in left of
    # the feedback entry at x=1.0, and clear of the y=2.8 feedback run
    # which starts at x=1.0. Stop follows Survivability Check, the flow's
    # dead end. This file's axes are inches on both axes (data unit = 1 in
    # of a (6.5 x H) canvas), so FancyBboxPatch rounding = h/2 draws a
    # TRUE stadium here; no polygon reconstruction is needed (unlike
    # make_pipeline_figure.py, whose axes are anisotropic fractions).
    box(ax, 0.4, 2.9, 0.6, 0.3, "Start", "white", INK, rounding=0.15)
    arrow(ax, (0.7, 2.9), (0.7, sparta_y0 + sparta_h))
    box(ax, 5.75, 2.0, 0.5, 0.3, "Stop", "white", INK, rounding=0.15)
    arrow(ax, (surv_x0 + surv_w, surv_y0 + surv_h / 2), (5.75, 2.15))

    # Arrow labels. WHY they sit above/below their rows rather than on the
    # arrow line itself: at y=2.25/0.95 the labels shared the boxes' text rows
    # (box labels nearly fill their boxes), and fm.text_overlaps_pt flagged
    # four pre-existing collisions once that guard existed -- 6.2/26/47/54.8 pt
    # wide x 4.5 pt tall against 'PINN DeepXDE', 'SPARTA DSMC Solver',
    # 'Bayes Opt Surrogate GP Matern 5/2' and 'OpenFOAM Solid Thermal'
    # (the committed solver_coupling.png still carries them: HEAD fails the
    # same verify). Top-row labels now sit just above the top boxes
    # (y=2.55, under the y=2.8 feedback line by 0.12 in); bottom-row labels
    # sit in the inter-row gap above the bottom boxes (y=1.22). 'refined
    # field' also shifts right to x=3.35 so it clears the vertical arrow line
    # at x=2.9 by 0.12 in. No Text pair overlaps remain at these spots. The
    # 'surface heat flux' centre moved 1.55 -> 1.62: the feedback descent at
    # x=1.0 clipped its leading 's' in the committed render (audit, pixel
    # probe); at 1.62 the ink starts ~1.15 in, 0.14 in clear of the shaft,
    # and the gap to 'backface temperature' stays > 0.4 in.
    ax.text(1.62, 2.55, "surface heat flux", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)
    ax.text(3.05, 2.55, "backface temperature", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)
    ax.text(1.55, 1.22, "grid dump", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)
    ax.text(3.35, 1.22, "refined field", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)
    ax.text(5.35, 2.85, "new design", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=ORANGE)

    # Legend
    legend_row1 = (
        ("DSMC Solver", SOLVER_FILL, SOLVER_EDGE),
        ("ML Model", ML_FILL, ML_EDGE),
    )
    legend_row2 = (
        ("Optimization", ENGINE_FILL, ENGINE_EDGE),
        ("Output", OUTPUT_FILL, OUTPUT_EDGE),
    )
    draw_legend_row(ax, legend_row1, 0.25)
    draw_legend_row(ax, legend_row2, 0.10)

    return fig


def build_result_extraction() -> object:
    """Build the surface data extraction and flight metrics pipeline.

    :returns: the matplotlib figure, with the axes on it as its only axes.
    """
    H = 3.0
    fig = plt.figure(figsize=(PRINT_W_IN, H))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, PRINT_W_IN)
    ax.set_ylim(0.0, H)
    ax.axis("off")

    title = "Surface Data Extraction and Flight Metrics"
    ax.text(PRINT_W_IN / 2.0, 2.85, title, ha="center", va="center",
            fontsize=13.0, fontweight="bold", color=INK)

    # Box positions
    dump_x0, dump_y0, dump_w, dump_h = 0.3, 1.2, 1.4, 0.7
    parse_x0, parse_y0, parse_w, parse_h = 2.2, 1.2, 1.4, 0.7
    integrate_x0, integrate_y0, integrate_w, integrate_h = 4.1, 1.2, 1.4, 0.7
    metrics_x0, metrics_y0, metrics_w, metrics_h = 4.1, 0.2, 1.4, 0.7

    # Flowchart symbology: 'SPARTA dump surf' is the INPUT data entering
    # this extraction pipeline and 'Flight Metrics q, Q, Cd' is its
    # OUTPUT, so both are ISO 5807 parallelograms; 'Parse' and 'Surface
    # Integration' are processing steps and stay rectangles. The oval
    # symbol is reserved for the dedicated Start/Stop terminals below
    # (the previous revision rounded dump/metrics as pseudo-terminals).
    fsh.io_box(ax, dump_x0, dump_y0, dump_w, dump_h,
           "SPARTA\ndump surf", SOLVER_FILL, SOLVER_EDGE, text_color="white")
    box(ax, parse_x0, parse_y0, parse_w, parse_h,
        "Parse\nSurface Data", INPUT_FILL, INPUT_EDGE)
    box(ax, integrate_x0, integrate_y0, integrate_w, integrate_h,
        "Surface\nIntegration", ML_FILL, ML_EDGE, text_color="white")
    fsh.io_box(ax, metrics_x0, metrics_y0, metrics_w, metrics_h,
           "Flight Metrics\nq, Q, Cd", OUTPUT_FILL, OUTPUT_EDGE,
           text_color="white")

    # Arrows. The dump connector starts on the parallelogram's right edge
    # at mid-height (x0 + w + slant/2), not at the bottom-right corner, so
    # the shaft meets the outline instead of starting inside the fill.
    arrow(ax, (dump_x0 + dump_w + 0.025, dump_y0 + dump_h / 2),
          (parse_x0, parse_y0 + parse_h / 2))
    arrow(ax, (parse_x0 + parse_w, parse_y0 + parse_h / 2),
          (integrate_x0, integrate_y0 + integrate_h / 2))
    arrow(ax, (integrate_x0 + integrate_w / 2, integrate_y0),
          (metrics_x0 + metrics_w / 2, metrics_y0 + metrics_h))

    # Dedicated labeled terminals (ISO 5807 ovals): Start feeds the dump
    # step from above at x=0.85 (clear of the 'raw data' label at
    # x~1.25-1.85 and of the title, whose centred span starts ~x=1.35);
    # Stop follows the metrics output. Axes are inches on both axes, so
    # rounding = h/2 draws a true stadium (see build_solver_coupling).
    box(ax, 0.55, 2.3, 0.6, 0.3, "Start", "white", INK, rounding=0.15)
    arrow(ax, (0.85, 2.3), (0.85, dump_y0 + dump_h))
    box(ax, 5.75, 0.4, 0.5, 0.3, "Stop", "white", INK, rounding=0.15)
    arrow(ax, (metrics_x0 + metrics_w + 0.025, metrics_y0 + metrics_h / 2),
          (5.75, 0.55))

    # Arrow labels. WHY above the row: box labels nearly fill their boxes, so
    # labels on the arrow line (y=1.65) collided with 'SPARTA dump surf' and
    # 'Parse Surface Data' (5.0/26.8 pt wide x 4.5 pt tall per
    # fm.text_overlaps_pt -- the committed result_extraction.png carries the
    # same latent collisions). The two horizontal-arrow labels now sit above
    # the box row (y=1.95, clear of the title); 'integrated' stays beside its
    # vertical arrow, which never collided.
    ax.text(1.55, 1.95, "raw data", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)
    ax.text(3.05, 1.95, "parsed", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)
    ax.text(5.35, 0.95, "integrated", ha="center", va="bottom",
            fontsize=9.5, fontstyle="italic", color=INK)

    # Legend
    legend_row1 = (
        ("DSMC Output", SOLVER_FILL, SOLVER_EDGE),
        ("Processing", INPUT_FILL, INPUT_EDGE),
    )
    legend_row2 = (
        ("Integration", ML_FILL, ML_EDGE),
        ("Metrics", OUTPUT_FILL, OUTPUT_EDGE),
    )
    draw_legend_row(ax, legend_row1, 0.25)
    draw_legend_row(ax, legend_row2, 0.10)

    return fig


def verify(fig: object, scale: float) -> None:
    """Check the written figure against the readability and collision floors.

    The check runs at the size the page will actually print: the fit scale
    times the chapter 03 \\textwidth squeeze (canvas 6.50 in placed at
    5.5118 in), because these figures are included with width=\\textwidth.

    :param fig: the figure that was written, still open.
    :param scale: placement scale reported by the print fit.
    :returns: None.
    :raises RuntimeError: if the smallest printed text is under the floor, or
        two printed labels overlap by at least 3 pt in both directions.
    """
    placed = scale * min(1.0, pf.TEXT_W_IN / PRINT_W_IN)
    printed, why = fm.smallest_text_pt(fig, placed)
    print("smallest printed text %.2f pt (%s); floor %.1f pt"
          % (printed, why, MIN_PRINTED_PT))
    if printed < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is under the %.1f pt floor from %s"
            % (printed, MIN_PRINTED_PT, why)
        )
    overlaps = fm.text_overlaps_pt(fig, placed)
    if overlaps:
        detail = "; ".join(
            "%.1fx%.1f pt %s <> %s" % (ox, oy, a, b)
            for a, b, ox, oy in overlaps[:8]
        )
        raise RuntimeError("printed labels overlap: %s" % detail)


def main() -> int:
    """Write the three figures and verify them.

    :returns: 0 on success, 1 on rejection.
    """
    figures = [
        ("domain_mesh.png", build_domain_mesh,
         ["SPARTA Computational Domain and Cartesian Mesh",
          "Farfield boundary", "Symmetry plane", "HIAD surface",
          "Bow shock", "Cartesian mesh", "grid factor 0.7"]),
        ("solver_coupling.png", build_solver_coupling,
         ["Multi-Solver Coupling and Data Exchange",
          "SPARTA", "DSMC Solver", "OpenFOAM", "Solid Thermal",
          "Survivability", "Check", "PINN", "DeepXDE",
          "Bayes Opt Surrogate", "GP Matern 5/2",
          "EI Acquisition", "Next Design",
          "surface heat flux", "backface temperature",
          "grid dump", "refined field", "new design",
          "Start", "Stop",
          "DSMC Solver", "ML Model", "Optimization", "Output"]),
        ("result_extraction.png", build_result_extraction,
         ["Surface Data Extraction and Flight Metrics",
          "SPARTA", "dump surf", "Parse", "Surface Data",
          "Surface", "Integration", "Flight Metrics", "q, Q, Cd",
          "raw data", "parsed", "integrated",
          "Start", "Stop",
          "DSMC Output", "Processing", "Integration", "Metrics"]),
    ]

    for name, build_fn, strings in figures:
        pf.require_clean(*strings)
        fig = build_fn()
        pf.assert_inside_canvas(fig)
        tmp_path, scale = pf.save_to_print_width(
            fig, name.replace(".png", "_tmp.png"), PRINT_W_IN, close=False)
        try:
            verify(fig, scale)
            final_path = FIGDIR / name
            tmp_path.rename(final_path)
            print("wrote %s at print width %.4f in" % (final_path.name, PRINT_W_IN))
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            print("%s FAILED: %s" % (name, exc), file=sys.stderr)
            plt.close(fig)
            return 1
        finally:
            plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
