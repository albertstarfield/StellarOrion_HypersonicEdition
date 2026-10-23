"""Redraw the step-2200 Knudsen-number field from the SPARTA grid dump.

PURPOSE
    Figure 4.5 of the thesis (figures/knudsen_map_smooth_M0_A0.png) shows the
    local Knudsen number in the meridional slice of the DSMC domain.  The
    panel that shipped with the thesis was a ParaView screenshot whose colour
    key contradicted the plotted range, and the first scripted redraw of it
    was mis-framed: the canvas was cropped with ``bbox_inches="tight"`` on
    top of a ``tight_layout`` pass, which clipped the top and the left axes
    (no y-spine, no y-tick labels, no y-label, no title), stretched the
    colour bar 151 px past the axes so the 10^-2 tick was cut off and the
    10^-5 label fell below the x-axis, and left 29 % of the canvas as
    transparent padding, so the panel rendered at roughly 70 % of the text
    width.  This script rebuilds the panel from the solver's own grid dump
    with a layout that fills the canvas, a cell-filled (not dotted) field,
    and the reference vehicle outline drawn on top of it.

AXIOMS
    A1.  The dump is the ground truth: the field is computed from the cell
        number density in grid.2200.out, never read off a picture.
    A2.  The mean free path is the hard-sphere estimate
        lambda = 1 / (sqrt(2) * pi * d^2 * n) with d = 3.7e-10 m for air
        (Bird 1994, Eq. 4.45) and the reference length L = 1 m.
    A3.  Kn = lambda / L.  The plotted range 1e-5 .. 1.15e-2 brackets the
        computed field (4.74e-6 .. 8.36e-3) and is kept from the original
        panel so the colour scale stays comparable with the thesis text.
    A4.  The run is the VALIDATION REFERENCE tree (results/00_reference),
        i.e. the un-optimised vehicle: Mach 7.53426, T_inf 267.85 K, 2200
        steps, 5sp chemistry, smooth nose, grid 139 x 139 x 1 over
        (-5, 0, -0.5) - (9, 3.9375, 0.5), i.e. 139 x 139 x 1 = 19321 child
        cells (the dump lists 19322 rows for 19321 distinct cell ids).
    A5.  The vehicle outline is the 77-point meridian profile in
        results/00_reference/HIAD_custom.surf (length 1.269 m, r_max
        1.880 m), read with the shared read_surf() helper that lives with
        the other program scripts.

THEORIES
    T1.  Cell-centred tiles drawn as filled rectangles reproduce the field
        without the gaps of a scatter plot, because the SPARTA cells tile
        the box exactly; the domain therefore reads as a continuous map
        rather than as a dotted picket fence.
    T2.  The canvas is laid out explicitly (the equivalent of an explicit
        subplots_adjust) instead of with constrained_layout, because
        constrained_layout gives the colour bar the full height of the
        layout cell while an equal-aspect axes is shrunk inside that cell.
        That mismatch is exactly the 151 px colour-bar/axes height error of
        the previous export, and no amount of canvas cropping removes it.
        Placing both boxes by hand and sizing the canvas from the measured
        text extents makes the colour bar exactly as tall as the axes and
        leaves no empty band: the canvas is the sum of the left margin, the
        axes, the gap, the colour bar and the right margin, and of the top
        margin, the axes and the bottom margin.
    T3.  V_inf follows from the frozen inflow of the reference deck:
        V_inf = M * sqrt(gamma * R * T_inf) = 7.53426 * sqrt(1.4 * 287 *
        267.85) = 2472 m/s.  It is a derived value, not a read-off.

APPLICATIONS
    - Read the SPARTA grid dump of the reference tree.
    - Draw the cell-filled Knudsen map, the reference vehicle outline and
        the run-condition box.
    - Export figures/knudsen_map_smooth_M0_A0.png for the thesis and
        verify the export for transparent padding, clipped text and
        colour-bar/axes height mismatch.

CITATIONS
    Bird, G. A. (1994) Molecular Gas Dynamics and the Direct Simulation of
    Gas Flows, Oxford University Press, Eq. 4.45 (mean free path).
    SPARTA grid dump: stellarorion_program_proc/results/00_reference/
    grid.2200.out (dump 2, step 2200).
    Vehicle profile: stellarorion_program_proc/results/00_reference/
    HIAD_custom.surf; reader read_surf() in stellarorion_program_proc/
    scripts/plot_hiad_3d.py.
    Run conditions: stellarorion_program_proc/results/00_reference/in.hiad.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROGRAM = REPO / "stellarorion_program_proc"
DUMP = PROGRAM / "results/00_reference/grid.2200.out"
SURF = PROGRAM / "results/00_reference/HIAD_custom.surf"
SCRIPTS = PROGRAM / "scripts"
OUT = HERE / "knudsen_map_smooth_M0_A0.png"

# The shared surface reader lives with the other program scripts
# (stellarorion_program_proc/scripts/plot_hiad_3d.py:67); import it instead of
# re-implementing the SPARTA .surf parser.  Byte-code writing is disabled so
# the import leaves no __pycache__ behind in the program tree.
sys.dont_write_bytecode = True
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from plot_hiad_3d import read_surf  # noqa: E402  (needs the sys.path set above)

D_MOL = 3.7e-10       # m, effective air diameter (Bird 1994, Eq. 4.45)
L_REF = 1.0           # m, reference length used to non-dimensionalise lambda
KN_MIN = 1e-5         # colour-scale floor, as published with the panel
KN_MAX = 1.15e-2      # colour-scale ceiling, as published with the panel
XLIM = (-1.0, 5.0)    # m, axial window of the published panel
YLIM = (0.0, 3.6)     # m, radial window of the published panel
DPI = 300
AX_HEIGHT_IN = 3.25   # drawn height of the axes, in inches
CBAR_RATIO = 15.0     # height/width of the colour bar
CBAR_GAP_IN = 0.12    # clear space between the axes and the colour bar
BODY_FACE = "0.86"    # neutral grey for the solid vehicle interior
BODY_EDGE = "black"   # solid outline of the reference vehicle
DATA_ASPECT = (XLIM[1] - XLIM[0]) / (YLIM[1] - YLIM[0])

# Run-condition box.  Every value is either read from the reference deck
# (in.hiad) or derived from it (T3); the panel states that this is the
# reference tree and not the optimised geometry.
CONDITION_TEXT = (
    "Validation REFERENCE tree 00_reference | step 2200 |\n"
    "Mach 7.53, T_inf 267.85 K (V_inf ~ 2472 m/s, derived) |\n"
    "19321 cells | smooth nose\n"
    "(reference geometry, not the optimised design)"
)


def load_field() -> tuple[np.ndarray, np.ndarray, int]:
    """Return solid-cell rectangles, their Knudsen numbers and the cell count.

    AXIOMS: A1 (the dump is the ground truth), A2 (mean free path),
    A3 (Kn = lambda / L).

    Empty cells (n = 0, i.e. the solid vehicle interior and the 72 cells of
    the evacuated near wake that hold no particles) carry no gas and
    therefore no Knudsen number; they are left blank instead of being
    coloured with a value the solver never reported.
    """
    rows = np.loadtxt(DUMP, skiprows=9)
    xlo, ylo = rows[:, 1], rows[:, 2]
    xhi, yhi = rows[:, 3], rows[:, 4]
    n_rho = rows[:, 10]
    solid = n_rho > 0.0
    kn = 1.0 / (np.sqrt(2.0) * np.pi * D_MOL**2 * n_rho[solid]) / L_REF
    verts = np.empty((int(solid.sum()), 4, 2))
    verts[:, 0, 0], verts[:, 0, 1] = xlo[solid], ylo[solid]
    verts[:, 1, 0], verts[:, 1, 1] = xhi[solid], ylo[solid]
    verts[:, 2, 0], verts[:, 2, 1] = xhi[solid], yhi[solid]
    verts[:, 3, 0], verts[:, 3, 1] = xlo[solid], yhi[solid]
    return verts, kn, len(np.unique(rows[:, 0]))


def load_profile() -> tuple[np.ndarray, np.ndarray]:
    """Return the reference vehicle meridian profile (axial, radial) in metres.

    AXIOM: A5.  The 77 points run from the nose tip, over the shoulder, down
    the flat aft face to the symmetry axis, so plotting them in order traces
    the closed outer surface of the vehicle.
    """
    points = read_surf(str(SURF))
    if len(points) < 3:
        raise RuntimeError(f"reference surface profile is empty or truncated: {SURF}")
    profile = np.asarray(points, dtype=float)
    return profile[:, 0], profile[:, 1]


def place_boxes(fig, ax, cax, ax_w, ax_h, cbar_w, gap, margins):
    """Put the axes and the colour bar on the canvas, in figure fractions.

    THEORY: T2.  The colour bar is given the same bottom and the same
    height as the axes, so the two boxes can never drift apart the way they
    do when a layout engine and an equal-aspect axes fight over the same
    cell.
    """
    width, height = fig.get_figwidth(), fig.get_figheight()
    ax.set_position([margins["left"] / width, margins["bottom"] / height,
                     ax_w / width, ax_h / height])
    cax.set_position([(margins["left"] + ax_w + gap) / width,
                      margins["bottom"] / height,
                      cbar_w / width, ax_h / height])


def measure_margins(fig, ax, cax, renderer):
    """Return the margins the decorations need, as a named dictionary.

    THEORY: T2.  The left margin is the room taken by the y-tick labels and
    the y-label, the bottom margin by the x-tick labels and the x-label, the
    top margin by the title, and the right margin by the colour-bar tick
    labels and the colour-bar label.  All four are measured from the drawn
    text, so the canvas can be sized to contain them exactly.
    """
    dpi = fig.dpi
    ax_pos = ax.get_position()
    ax_left = ax_pos.x0 * fig.get_figwidth()
    ax_right = (ax_pos.x0 + ax_pos.width) * fig.get_figwidth()
    ax_bottom = ax_pos.y0 * fig.get_figheight()
    ax_top = (ax_pos.y0 + ax_pos.height) * fig.get_figheight()
    cbar_right = cax.get_window_extent(renderer).x1 / dpi

    y_decor = [ax.yaxis.get_label().get_window_extent(renderer)]
    y_decor += [t.get_window_extent(renderer) for t in ax.get_yticklabels()]
    cbar_decor = [cax.yaxis.get_label().get_window_extent(renderer)]
    cbar_decor += [t.get_window_extent(renderer) for t in cax.get_yticklabels()]
    x_decor = [ax.xaxis.get_label().get_window_extent(renderer)]
    x_decor += [t.get_window_extent(renderer) for t in ax.get_xticklabels()]
    title = ax.title.get_window_extent(renderer)

    left_ink = min(e.x0 for e in y_decor) / dpi
    right_ink = max(e.x1 for e in cbar_decor) / dpi
    margin_l = ax_left - left_ink
    margin_r = right_ink - cbar_right
    margin_b = ax_bottom - min(e.y0 for e in x_decor) / dpi
    margin_t = title.y1 / dpi - ax_top
    # A title wider than the axes overhangs it symmetrically, so the canvas
    # has to reserve that overhang on both sides.
    overhang = max(0.0, (title.width / dpi - (ax_right - ax_left)) / 2.0)
    margin_l = max(margin_l, overhang)
    margin_r = max(margin_r, overhang)
    return {"left": margin_l, "right": margin_r,
            "top": margin_t, "bottom": margin_b}


def layout_figure(fig, ax, cax, data_aspect, ax_h, cbar_ratio, gap, iterations=6):
    """Size the canvas and place both boxes so the panel fills the canvas.

    THEORY: T2.  The canvas is the sum of the measured margins, the axes
    box, the gap and the colour bar, and the axes box carries the data
    aspect ratio exactly, so the equal-aspect axes is drawn at the size it
    was given and nothing is left blank inside the canvas.
    """
    ax_w = data_aspect * ax_h
    cbar_w = ax_h / cbar_ratio
    margins = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
    for _ in range(iterations):
        place_boxes(fig, ax, cax, ax_w, ax_h, cbar_w, gap, margins)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        margins = measure_margins(fig, ax, cax, renderer)
        fig.set_size_inches(
            margins["left"] + ax_w + gap + cbar_w + margins["right"],
            margins["top"] + ax_h + margins["bottom"])
    place_boxes(fig, ax, cax, ax_w, ax_h, cbar_w, gap, margins)
    fig.canvas.draw()


def text_outside_canvas(fig, renderer):
    """Return the text whose drawn extent leaves the canvas.

    A clipped tick label or axis label shows up here, which is the check the
    previous export failed: the y-spine, the y-tick labels, the y-label and
    the title of the old panel were all cropped away.
    """
    width = fig.get_figwidth() * fig.dpi
    height = fig.get_figheight() * fig.dpi
    outside = []
    for axes in fig.axes:
        texts = [axes.title, axes.xaxis.label, axes.yaxis.label]
        texts += list(axes.texts)
        texts += list(axes.get_xticklabels()) + list(axes.get_yticklabels())
        for text in texts:
            if not text.get_visible() or not text.get_text():
                continue
            box = text.get_window_extent(renderer)
            if (box.x0 < -0.5 or box.y0 < -0.5
                    or box.x1 > width + 0.5 or box.y1 > height + 0.5):
                outside.append((text.get_text()[:40],
                                round(box.x0, 1), round(box.y0, 1),
                                round(box.x1, 1), round(box.y1, 1)))
    return outside


def verify_export(path, ax_box, cbar_box, clipped):
    """Check the exported PNG for transparent padding and clipped content.

    A transparent border shows up as an alpha bounding box smaller than the
    canvas; a mis-sized colour bar shows up as a height difference against
    the axes; clipped text shows up in the `clipped` list.
    """
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        width, height = rgba.size
        alpha_bbox = rgba.getchannel("A").getbbox()
        pixels = np.asarray(rgba)
        ink = pixels[:, :, :3].min(axis=2) < 250
        ink_bbox = Image.fromarray((ink * 255).astype(np.uint8)).getbbox()
    return {
        "canvas_px": (width, height),
        "alpha_bbox": alpha_bbox,
        "alpha_covers_canvas": alpha_bbox == (0, 0, width, height),
        "ink_bbox": ink_bbox,
        "ink_fraction": float(ink.sum()) / float(width * height),
        "axes_px": (round(ax_box.width), round(ax_box.height)),
        "cbar_px": (round(cbar_box.width), round(cbar_box.height)),
        "cbar_matches_axes_height": abs(ax_box.height - cbar_box.height) <= 2.0,
        "clipped_text": clipped,
    }


def main() -> int:
    """Render the reference-tree Knudsen map and verify the export."""
    try:
        verts, kn, n_cells = load_field()
        body_x, body_r = load_profile()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: cannot build the Knudsen field: {exc}", file=sys.stderr)
        return 1

    fig = plt.figure(figsize=(7.0, 4.1), dpi=DPI)
    ax = fig.add_axes([0.10, 0.12, 0.70, 0.70])
    cax = fig.add_axes([0.85, 0.12, 0.02, 0.70])

    field = PolyCollection(verts, array=kn, cmap="turbo",
                           norm=LogNorm(vmin=KN_MIN, vmax=KN_MAX),
                           edgecolors="none", linewidths=0.0, antialiased=False,
                           zorder=1)
    ax.add_collection(field)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(np.arange(XLIM[0], XLIM[1] + 0.01, 1.0))
    ax.set_yticks(np.arange(YLIM[0], YLIM[1] + 0.01, 0.5))
    ax.set_xlabel("Axial distance (m)")
    ax.set_ylabel("Radial distance (m)")
    ax.set_title("Local Knudsen number, step 2200 (reference tree)", fontsize=11)

    # Reference vehicle: solid interior so the vehicle reads as an object,
    # solid outer surface so the boundary is explicit (AXIOM A5).
    ax.fill(body_x, body_r, facecolor=BODY_FACE, edgecolor="none", zorder=3)
    ax.plot(body_x, body_r, color=BODY_EDGE, linewidth=1.3, zorder=4,
            solid_capstyle="round", solid_joinstyle="round")

    ax.text(0.012, 0.988, CONDITION_TEXT, transform=ax.transAxes,
            ha="left", va="top", fontsize=7.0, linespacing=1.35, zorder=6,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="0.35", linewidth=0.6, alpha=0.95))

    cbar = fig.colorbar(field, cax=cax, ticks=[1e-5, 1e-4, 1e-3, 1e-2])
    cbar.set_label("Local Knudsen number $Kn$ ($-$)", fontsize=9)
    cbar.set_ticklabels([r"$10^{-5}$", r"$10^{-4}$", r"$10^{-3}$", r"$10^{-2}$"])
    cbar.minorticks_off()

    layout_figure(fig, ax, cax, DATA_ASPECT, AX_HEIGHT_IN, CBAR_RATIO,
                  CBAR_GAP_IN)
    renderer = fig.canvas.get_renderer()
    clipped = text_outside_canvas(fig, renderer)
    ax_box = ax.get_window_extent(renderer)
    cbar_box = cax.get_window_extent(renderer)
    fig.savefig(OUT, facecolor="white")
    plt.close(fig)

    report = verify_export(OUT, ax_box, cbar_box, clipped)
    print(f"wrote {OUT.name}")
    print(f"  cells in grid: {n_cells} | solid cells drawn: {len(kn)}")
    print(f"  Kn range: {kn.min():.4e} .. {kn.max():.4e} "
          f"(scale {KN_MIN:.0e} .. {KN_MAX:.2e})")
    print(f"  figure: {fig.get_figwidth():.2f} x {fig.get_figheight():.2f} in @ {DPI} dpi")
    print(f"  canvas px: {report['canvas_px']} | alpha bbox: {report['alpha_bbox']}")
    print(f"  alpha covers canvas: {report['alpha_covers_canvas']}")
    print(f"  ink bbox: {report['ink_bbox']} | ink fraction: {report['ink_fraction']:.3f}")
    print(f"  axes px: {report['axes_px']} | colourbar px: {report['cbar_px']}")
    print(f"  colourbar height matches axes: {report['cbar_matches_axes_height']}")
    print(f"  text outside canvas: {report['clipped_text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
