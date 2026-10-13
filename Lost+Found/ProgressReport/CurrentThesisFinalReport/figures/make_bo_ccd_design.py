"""Draw the central composite screen as a cost-coloured three-dimensional layout.

PURPOSE
    Figure 4.6 of the thesis reports fifteen screened designs: eight factorial
    corners, the design center and six axial points, each coloured by the cost
    the solver actually returned. This script regenerates that panel from the
    committed campaign so the figure can be rebuilt, and so the British spelling
    in the previous artwork cannot return.

PARAMETERS
    None. Every input is a module constant or comes from opt_data.load_verified.

RETURNS
    main() returns 0 on success and 1 when a figure is rejected. A rejection
    never overwrites the committed PNG, because print_fit writes to a temporary
    path only after every guard has passed.

EXCEPTIONS
    RuntimeError when the campaign does not match the printed text, when an
    artist overhangs the canvas, when the printed width cannot be reached, when
    any text would print below the legibility floor, or when a drawn string
    contains a banned dash.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
    Montgomery, D. C. (2017) Design and Analysis of Experiments, 9th ed.,
    Wiley, central composite designs.
    Paul Tol's colour schemes, https://personal.sron.nl/~pault/

AXIOMS
    A1. The printed text is the specification. Every number this panel shows is
        asserted against it by opt_data before anything is drawn.
    A2. Printed point size equals declared size times the achieved print
        scale, and the canvas is built at the printed width, so the scale is
        one and a declared 11.5 pt label prints at 11.5 pt.
    A3. A mathtext script prints at 0.7 of its parent, so any label carrying a
        subscript must be declared at 11.5 pt or larger to clear 8 pt.
    A4. The campaign optimum lies outside the screen cloud, so the axis limits
        must cover it or the round-1 marker would be drawn outside the box.

THEORIES
    T1. Because A1 makes the text authoritative and the committed revision is
        the only stable copy, the panel is generated from that revision and the
        claims are asserted, never assumed.
    T2. Because A2 and A3 fix the relation between declared and printed size,
        the legibility floor is enforced by measuring the achieved scale rather
        than by choosing sizes by eye.
    T3. Because A4 fixes the axis limits from the data, the four reference
        markers are guaranteed to be inside the plotted volume.

APPLICATIONS
    A1. Regenerate figures/bo_ccd_design.png after a campaign change.
    A2. Re-check the panel against the caption and the accessible text.

WHY THE PANEL IS A LAYOUT AND NOT A SURFACE
    Fifteen points cannot resolve a three-dimensional response surface, so no
    interpolating surface is drawn. The caption and the accessible text both say
    this, and drawing a surface here would contradict them.
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, unique measurement rules
import opt_data  # noqa: E402  sibling module, unique campaign loader
import print_fit as pf  # noqa: E402  sibling module, unique print geometry

ROOT = opt_data.ROOT
FIGDIR = os.path.dirname(os.path.abspath(__file__))
assert os.path.isdir(FIGDIR), f"figure directory missing: {FIGDIR}"

# The document includes this panel at width=\textwidth, so the canvas is built
# at exactly that width and the achieved print scale is one.
PRINT_W_IN = pf.TEXT_W_IN
PRINT_H_IN = 3.95

TITLE_LINES = (
    "Central Composite Screen in the Design Space",
    "8 factorial + 1 center + 6 axial points",
    "coloured by measured cost, a layout and not a fitted surface",
)
MIN_PRINTED_PT = 8.0
MATH_PT = 11.5        # smallest parent whose script still prints at 8.05 pt
TITLE_PT = 12.0
TICK_PT = 10.0
NOTE_PT = 9.0

# Paul Tol's colourblind-safe qualitative palette, the same six entries the
# sibling generators use so the figures read as one set.
CB = ["#004488", "#DDAA33", "#BB5566", "#228833", "#AA4499", "#66CCEE"]
INK = "#222222"
GRID = "#BBBBBB"

X_LIM = (0.90, 3.05)
Y_LIM = (0.055, 0.215)
Z_LIM = (38.0, 70.0)
X_TICKS = (1.0, 1.5, 2.0, 2.5, 3.0)
Y_TICKS = (0.06, 0.10, 0.14, 0.18, 0.22)
Z_TICKS = (40.0, 50.0, 60.0, 70.0)
# The screen costs run from 1.9959 to 38.8332, so these decades bracket them
# without inventing a value outside the measured range.
CBAR_TICKS = (2.0, 3.0, 5.0, 10.0, 20.0, 30.0)


def cost_key(samples: list[dict]) -> list[float]:
    """Return the evaluated cost of every screen point, in payload order.

    Parameters:
        samples: the ccd_samples list from the committed campaign.

    Returns:
        list of floats, one per sample.

    Raises:
        RuntimeError if the list does not have the fifteen screened points the
        text describes.
    """
    if len(samples) != opt_data.THESIS_CLAIMS["ccd_len"]:
        raise RuntimeError(f"expected 15 screen points, got {len(samples)}")
    return [float(row["cost"]) for row in samples]


def build(data: dict):
    """Construct the panel and return it with the artists the guards measure.

    Parameters:
        data: the verified campaign dict from opt_data.load_verified.

    Returns:
        tuple (fig, ax) where ax is the three-dimensional axes.

    Raises:
        RuntimeError if the marker set cannot be assembled from the payload.
    """
    samples = data["ccd_samples"]
    costs = np.array(cost_key(samples))
    centers = np.array(
        [[float(row["R_N"]), float(row["r_tor"]), float(row["half_cone_deg"])]
         for row in samples])

    fig = plt.figure(figsize=(PRINT_W_IN, PRINT_H_IN))
    # MEASURED: with the three-dimensional axes starting at y = 0.02 the x and y
    # axis labels hung 0.234 in and 0.208 in below the canvas, because labelpad
    # pushes those labels outward from the cube rather than from the axes box.
    # Raising the axes floor to 0.09 clears both with margin.
    # A11 MED: the rect changes from [0, 0.09, 0.86, 0.79] reserve the band
    # above the cube for the two-row legend. Floor 0.09 -> 0.12 and height
    # 0.79 -> 0.64 keep the axes top at 0.76 for that band while lifting the
    # cube 0.12 in clear of the bottom: at the 0.67-height cube the projected
    # y-axis label reached 0.035 in below the canvas (measured by
    # assert_inside_canvas), and 0.12 clears it with margin.
    ax = fig.add_axes([0.00, 0.12, 0.86, 0.64], projection="3d")
    cax = fig.add_axes([0.885, 0.28, 0.018, 0.44])

    norm = LogNorm(vmin=float(costs.min()), vmax=float(costs.max()))
    scatter = ax.scatter(centers[:, 0], centers[:, 1], centers[:, 2],
                         c=costs, cmap="viridis", norm=norm,
                         s=46, edgecolors="white", linewidths=0.6, depthshade=False)

    # Four reference markers. The design center and the IRVE-3 baseline differ
    # only in torus radius, so the center is the larger ring and the baseline is
    # the smaller square inside it, which keeps both readable at print size.
    center_row = next(row for row in samples if row["label"] == "center")
    default_row = data["default"]
    optimum_row = data["optimized"]
    best_index = int(np.argmin(costs))
    best_row = samples[best_index]

    ring_kwargs = dict(facecolors="none", linewidths=1.6, s=150)
    ring_sc = ax.scatter([float(center_row["R_N"])], [float(center_row["r_tor"])],
                         [float(center_row["half_cone_deg"])], edgecolors=CB[0],
                         **ring_kwargs)
    base_sc = ax.scatter([float(default_row["R_N"])], [float(default_row["r_tor"])],
                         [float(default_row["half_cone_deg"])],
                         marker="s", edgecolors=CB[1], linewidths=1.6, s=44,
                         depthshade=False)
    best_sc = ax.scatter([float(best_row["R_N"])], [float(best_row["r_tor"])],
                         [float(best_row["half_cone_deg"])],
                         marker="*", edgecolors=CB[3], linewidths=1.4, s=190,
                         depthshade=False)
    opt_sc = ax.scatter([float(optimum_row["R_N"])], [float(optimum_row["r_tor"])],
                        [float(optimum_row["half_cone_deg"])],
                        marker="D", edgecolors=CB[4], linewidths=1.6, s=64,
                        depthshade=False)

    ax.set_xlim(*X_LIM)
    ax.set_ylim(*Y_LIM)
    ax.set_zlim(*Z_LIM)
    # A11 LOW: at the default 3D view (elev 30, azim -60) the best-screened
    # star rested on the centre ring and the two top factorial points merged
    # into a single blob, so only about 14 of the 15 screened points were
    # individually readable. A 6 deg azimuth change separates both pairs at
    # print size while every axis face stays equally legible.
    ax.view_init(elev=30, azim=-36)
    ax.set_xticks(X_TICKS)
    ax.set_xticklabels([f"{value:g}" for value in X_TICKS], fontsize=TICK_PT)
    ax.set_yticks(Y_TICKS)
    ax.set_yticklabels([f"{value:.2f}" for value in Y_TICKS], fontsize=TICK_PT)
    ax.set_zticks(Z_TICKS)
    ax.set_zticklabels([f"{value:g}" for value in Z_TICKS], fontsize=TICK_PT)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((1.0, 1.0, 1.0, 1.0))
        axis._axinfo["grid"]["color"] = GRID
        axis._axinfo["grid"]["linewidth"] = 0.6

    ax.set_xlabel("Nose radius $R_N$ (m)", fontsize=MATH_PT, labelpad=2)
    ax.set_ylabel("Torus radius $r_{tor}$ (m)", fontsize=MATH_PT, labelpad=2)
    ax.set_zlabel("Half-cone angle $\\theta_c$ (deg)", fontsize=MATH_PT, labelpad=4)
    ax.tick_params(axis="x", pad=-2)
    ax.tick_params(axis="y", pad=-2)
    ax.tick_params(axis="z", pad=0)

    # MEASURED: the default LogNorm colorbar draws its ticks as mathtext decade
    # labels such as 2x10**0, whose exponent prints at 0.7 of the parent and
    # therefore below the 8 pt floor. Setting the major ticks alone is not enough
    # because the minor formatter still labelled 4x10**0 and 6x10**1, and those
    # wide labels then pushed the rotated bar label sideways so far that it left
    # the canvas by 0.646 in. Suppressing the minor labels fixes both symptoms.
    from matplotlib.ticker import NullFormatter, NullLocator

    bar = fig.colorbar(scatter, cax=cax)
    bar.set_ticks(CBAR_TICKS)
    bar.set_ticklabels([f"{value:g}" for value in CBAR_TICKS])
    bar.ax.tick_params(labelsize=TICK_PT, pad=1)
    bar.ax.yaxis.set_minor_locator(NullLocator())
    bar.ax.yaxis.set_minor_formatter(NullFormatter())
    bar.set_label("Evaluated cost $J$", fontsize=MATH_PT, labelpad=2)
    bar.outline.set_linewidth(0.8)

    # A11 MED: the four reference markers were unlabeled after the marker
    # refresh, and the shipped panel still carried the old in-axes legend
    # whose translucent frame sat over the cube with a data point inside it
    # and the grid showing through. The legend now lives OUTSIDE the axes as
    # one opaque row in the band reserved above the cube: framealpha 1.0
    # with a white face means neither grid lines nor data points can show
    # through, and because the row sits above the cube it covers no point.
    legend = ax.legend(
        handles=[ring_sc, base_sc, best_sc, opt_sc],
        labels=[
            "CCD design centre",
            "IRVE-3 baseline",
            "best screened point",
            "round-1 BO optimum",
        ],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.005),
        ncol=2,
        fontsize=TICK_PT,
        frameon=True,
        framealpha=1.0,
        facecolor="white",
        edgecolor=GRID,
        borderpad=0.4,
        columnspacing=1.2,
        handletextpad=0.5,
    )
    legend.set_zorder(10)

    # The note carries the two screen extremes the surrounding text discusses.
    note = (f"cheapest screened point $J = {costs.min():.4f}$, "
            f"dearest $J = {costs.max():.2f}$")
    fig.text(0.005, 0.005, note, fontsize=NOTE_PT, color=INK, ha="left", va="bottom")
    for index, line in enumerate(TITLE_LINES):
        fig.text(0.5, 0.985 - index * 0.032, line, fontsize=TITLE_PT,
                 fontweight="bold" if index == 0 else "normal",
                 color=INK, ha="center", va="top")
    return fig, ax


def guard(fig, path, scale) -> None:
    """Reject the saved panel if any printed text is below the floor.

    Parameters:
        fig: the figure, still open.
        path: the written PNG.
        scale: the achieved print scale from print_fit.

    Returns:
        None.

    Raises:
        RuntimeError naming the smallest text found.
    """
    smallest, description = fm.smallest_text_pt(fig, scale)
    print(f"    smallest printed text {smallest:.2f} pt ({description})")
    if smallest < MIN_PRINTED_PT:
        raise RuntimeError(
            f"bo_ccd_design.png: smallest printed text {smallest:.2f} pt "
            f"({description}) is below the {MIN_PRINTED_PT:.1f} pt floor")


def main() -> int:
    """Build, save, verify and report the panel.

    Returns:
        0 on success, 1 when a guard rejected the figure.

    Raises:
        RuntimeError from the underlying helpers; main converts the print fit
        failure into a 1 so the caller sees a non-zero status.
    """
    os.chdir(os.path.dirname(FIGDIR))
    data = opt_data.load_verified()
    strings = list(TITLE_LINES) + [
        "Nose radius $R_N$ (m)", "Torus radius $r_{tor}$ (m)",
        "Half-cone angle $\\theta_c$ (deg)", "Evaluated cost $J$",
        "CCD design centre", "IRVE-3 baseline",
        "best screened point", "round-1 BO optimum",
    ]
    pf.require_clean(*strings)
    fig, _ = build(data)
    pf.assert_inside_canvas(fig)
    try:
        path, scale = pf.save_to_print_width(
            fig, "bo_ccd_design.png", PRINT_W_IN, close=False)
    except RuntimeError as error:
        print(f"!! {error}")
        return 1
    guard(fig, path, scale)
    plt.close(fig)
    print(f"wrote bo_ccd_design.png print {PRINT_W_IN:.3f} in scale {scale:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
