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
import print_fit as pf  # noqa: E402  sibling module, shared print geometry

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
        fs: float = 9.5, bold: bool = False, linespacing: float = 1.3) -> None:
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
    :returns: None.
    """
    patch = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0.0,rounding_size=0.04",
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
                    gap: float = 0.10, fs: float = 9.0) -> None:
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

    # Symmetry plane
    ax.plot([0.5, 6.0], [0.3, 0.3], color=INK, linewidth=1.5, zorder=1)

    # Cartesian mesh (coarse grid)
    for x in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]:
        ax.plot([x, x], [0.3, 3.5], color="#B0B0B0", linewidth=0.5, zorder=0)
    for y in [0.8, 1.3, 1.8, 2.3, 2.8, 3.3]:
        ax.plot([0.5, 6.0], [y, y], color="#B0B0B0", linewidth=0.5, zorder=0)

    # HIAD vehicle: nose (semicircle) + toroidal body
    import numpy as np
    theta = np.linspace(0, np.pi, 50)
    nose_r = 0.4
    nose_cx, nose_cy = 2.0, 0.3
    ax.fill(nose_cx + nose_r * np.cos(theta),
            nose_cy + nose_r * np.sin(theta),
            color=SOLVER_FILL, edgecolor=SOLVER_EDGE, linewidth=1.2, zorder=2)

    # Toroidal body (simplified as a rectangle with rounded top)
    body_x0, body_y0 = 2.4, 0.3
    body_w, body_h = 2.0, 0.6
    ax.add_patch(FancyBboxPatch(
        (body_x0, body_y0), body_w, body_h,
        boxstyle="round,pad=0.0,rounding_size=0.08",
        linewidth=1.2, edgecolor=SOLVER_EDGE, facecolor=SOLVER_FILL, zorder=2,
    ))

    # Bow shock (dashed curve)
    shock_x = np.linspace(1.0, 1.0, 2)
    shock_y = np.linspace(0.5, 3.3, 2)
    # Draw a curved bow shock using a parabola
    t = np.linspace(0, 1, 50)
    shock_x = 1.0 + 0.3 * np.sin(np.pi * t)
    shock_y = 0.5 + 2.8 * t
    ax.plot(shock_x, shock_y, linestyle="--", color=ORANGE,
            linewidth=1.5, zorder=1)

    # Labels
    ax.annotate("Farfield boundary", xy=(0.5, 3.5), xytext=(0.2, 3.7),
                fontsize=9.0, color=INK, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("Symmetry plane", xy=(4.0, 0.3), xytext=(4.5, 0.15),
                fontsize=9.0, color=INK, ha="center", va="bottom",
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("HIAD surface", xy=(2.0, 0.7), xytext=(1.2, 1.2),
                fontsize=9.0, color=INK, ha="center", va="bottom",
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("Bow shock", xy=(1.15, 2.0), xytext=(0.3, 2.5),
                fontsize=9.0, color=ORANGE, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.0))
    ax.annotate("Cartesian mesh\n(grid factor 0.7)", xy=(4.0, 2.0),
                xytext=(3.5, 2.8), fontsize=9.0, color=HEADER_GRAY,
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
    mop_x0, mop_y0, mop_w, mop_h = 2.2, 0.5, 1.4, 0.7
    ga_x0, ga_y0, ga_w, ga_h = 4.1, 0.5, 1.4, 0.7

    box(ax, sparta_x0, sparta_y0, sparta_w, sparta_h,
        "SPARTA\nDSMC Solver", SOLVER_FILL, SOLVER_EDGE, text_color="white")
    box(ax, openfoam_x0, openfoam_y0, openfoam_w, openfoam_h,
        "OpenFOAM\nSolid Thermal", SOLVER_FILL, SOLVER_EDGE, text_color="white")
    box(ax, surv_x0, surv_y0, surv_w, surv_h,
        "Survivability\nCheck", OUTPUT_FILL, OUTPUT_EDGE, text_color="white")
    box(ax, pinn_x0, pinn_y0, pinn_w, pinn_h,
        "PINN\nDeepXDE", ML_FILL, ML_EDGE, text_color="white")
    box(ax, mop_x0, mop_y0, mop_w, mop_h,
        "MoP Surrogate\nPyTorch", ML_FILL, ML_EDGE, text_color="white")
    box(ax, ga_x0, ga_y0, ga_w, ga_h,
        "GA\nOptimization", ENGINE_FILL, ENGINE_EDGE, text_color="white")

    # Arrows: top row
    arrow(ax, (sparta_x0 + sparta_w, sparta_y0 + sparta_h / 2),
          (openfoam_x0, openfoam_y0 + openfoam_h / 2))
    arrow(ax, (openfoam_x0 + openfoam_w, openfoam_y0 + openfoam_h / 2),
          (surv_x0, surv_y0 + surv_h / 2))

    # Arrows: bottom row
    arrow(ax, (pinn_x0 + pinn_w, pinn_y0 + pinn_h / 2),
          (mop_x0, mop_y0 + mop_h / 2))
    arrow(ax, (mop_x0 + mop_w, mop_y0 + mop_h / 2),
          (ga_x0, ga_y0 + ga_h / 2))

    # Vertical arrows: SPARTA to PINN, OpenFOAM to MoP
    arrow(ax, (sparta_x0 + sparta_w / 2, sparta_y0),
          (pinn_x0 + pinn_w / 2, pinn_y0 + pinn_h))
    arrow(ax, (openfoam_x0 + openfoam_w / 2, openfoam_y0),
          (mop_x0 + mop_w / 2, mop_y0 + mop_h))

    # Feedback loop: GA to SPARTA
    routed_arrow(ax, [
        (ga_x0 + ga_w / 2, ga_y0 + ga_h),
        (ga_x0 + ga_w / 2, 2.8),
        (sparta_x0 + sparta_w / 2, 2.8),
        (sparta_x0 + sparta_w / 2, sparta_y0 + sparta_h),
    ], color=ORANGE)

    # Arrow labels
    ax.text(1.55, 2.25, "surface heat flux", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)
    ax.text(3.05, 2.25, "backface temperature", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)
    ax.text(1.55, 0.95, "grid dump", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)
    ax.text(3.05, 0.95, "refined field", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)
    ax.text(5.35, 2.85, "new design", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=ORANGE)

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

    box(ax, dump_x0, dump_y0, dump_w, dump_h,
        "SPARTA\ndump surf", SOLVER_FILL, SOLVER_EDGE, text_color="white")
    box(ax, parse_x0, parse_y0, parse_w, parse_h,
        "Parse\nSurface Data", INPUT_FILL, INPUT_EDGE)
    box(ax, integrate_x0, integrate_y0, integrate_w, integrate_h,
        "Surface\nIntegration", ML_FILL, ML_EDGE, text_color="white")
    box(ax, metrics_x0, metrics_y0, metrics_w, metrics_h,
        "Flight Metrics\nq, Q, Cd", OUTPUT_FILL, OUTPUT_EDGE, text_color="white")

    # Arrows
    arrow(ax, (dump_x0 + dump_w, dump_y0 + dump_h / 2),
          (parse_x0, parse_y0 + parse_h / 2))
    arrow(ax, (parse_x0 + parse_w, parse_y0 + parse_h / 2),
          (integrate_x0, integrate_y0 + integrate_h / 2))
    arrow(ax, (integrate_x0 + integrate_w / 2, integrate_y0),
          (metrics_x0 + metrics_w / 2, metrics_y0 + metrics_h))

    # Arrow labels
    ax.text(1.55, 1.65, "raw data", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)
    ax.text(3.05, 1.65, "parsed", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)
    ax.text(5.35, 0.95, "integrated", ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", color=INK)

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
    """Check the written figure against the readability floor.

    :param fig: the figure that was written, still open.
    :param scale: placement scale reported by the print fit.
    :returns: None.
    :raises RuntimeError: if the smallest printed text is under the floor.
    """
    printed, why = fm.smallest_text_pt(fig, scale)
    print("smallest printed text %.2f pt (%s); floor %.1f pt"
          % (printed, why, MIN_PRINTED_PT))
    if printed < MIN_PRINTED_PT:
        raise RuntimeError(
            "smallest printed text %.2f pt is under the %.1f pt floor from %s"
            % (printed, MIN_PRINTED_PT, why)
        )


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
          "MoP Surrogate", "PyTorch", "GA", "Optimization",
          "surface heat flux", "backface temperature",
          "grid dump", "refined field", "new design",
          "DSMC Solver", "ML Model", "Optimization", "Output"]),
        ("result_extraction.png", build_result_extraction,
         ["Surface Data Extraction and Flight Metrics",
          "SPARTA", "dump surf", "Parse", "Surface Data",
          "Surface", "Integration", "Flight Metrics", "q, Q, Cd",
          "raw data", "parsed", "integrated",
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
