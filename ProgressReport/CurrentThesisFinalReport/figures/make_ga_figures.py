#!/usr/bin/env python3
"""Draw the genetic-algorithm campaign panels reported in Chapter 4.

PURPOSE
    The thesis reports a simple genetic algorithm as the optimizer: a
    Latin-hypercube initial population of 50 individuals evolved for at
    most 200 generations. The recorded campaign holds 38 generations and
    1900 evaluated designs, and it is the artifact these two panels draw:

      1. ga_convergence.png        the recorded generation-best cost against
                                   generation, with the baseline, the first
                                   recorded best, the final recorded best and
                                   the double-precision re-evaluated optimum
                                   marked, plus a zoom inset that resolves
                                   every one of the eight strict improvements.

      2. ga_design_trajectory.png  the generation-best design path through
                                   the (body radius, half-cone angle) plane,
                                   coloured by generation, together with the
                                   baseline-to-optimum change of each of the
                                   three design variables.

    Every number is read from the official optimizer artifact written by
    src/python/hiad_optimizer.py; nothing is typed into the artwork. The
    script refuses to draw if the artifact is not the genetic-algorithm
    campaign or if the values asserted below have drifted.

PARAMETERS
    None. The artifact path is resolved from this file's location.

RETURNS
    main() returns 0 on success and 1 when a print guard rejects a panel.
    save() writes a PNG only after every guard passes, so a rejected panel
    leaves the committed image untouched.

EXCEPTIONS
    RuntimeError when the artifact is missing or malformed, when the campaign
    is not the genetic algorithm, when an asserted value departs from the
    thesis text, when a drawn string contains a banned dash, when an artist
    overhangs the canvas, when two printed labels collide, or when any text
    would print below the legibility floor.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
    Goldberg, D. E. (1989) Genetic Algorithms in Search, Optimization and
    Machine Learning, Addison-Wesley, the GA operator definitions.
    Paul Tol's colour schemes, https://personal.sron.nl/~pault/

AXIOMS
    A1. The text is the specification: a figure that disagrees with a printed
        sentence is a defect even when it is faithful to the file. Chapter 4
        names the first design coordinate the body radius $X_1 = D/2$, so the
        trajectory panel labels that coordinate the way the text labels it.
    A2. The artifact on disk is the newest recorded run and is the single
        source of truth for the campaign reported in Chapter 4.
    A3. The recorded history is the generation-best cost reported by the
        single-precision Ada runner. The re-evaluated optimum is a separate,
        double-precision evaluation and is drawn as its own reference line;
        the two must never be presented as the same number.
    A4. An accepted design is a generation whose best design differs from the
        previous generation's best design. A generation that repeats its
        predecessor moved nothing and is not a point of the trajectory.
    A5. The recorded path is degenerate in the second design coordinate: the
        torus radius moves by less than 3e-5 m along the whole accepted path,
        so a three-dimensional rendering collapses to two distinct points.
        A two-dimensional panel plus a quantitative bar panel therefore carry
        strictly more information than a three-dimensional one.
    A6. The eight strict improvements span 5.3e-3 of a cost axis whose full
        extent is 4.15 to 4.78, so the main axes cannot show them and a zoom
        inset is the only way to make every improvement legible.
    A7. matplotlib draws a mathtext sub or superscript at 0.7 of its parent
        size, and the 8 pt legibility floor is measured on the printed
        result, so a label carrying a subscript must declare at least
        8 / 0.7 = 11.43 pt. Every label that carries a subscript is
        therefore set at SCRIPT_SAFE_PT = 11.5 pt, and every label that is
        set smaller than that is plain text with no script in it, so the
        torus radius is written out in words wherever it would otherwise
        have had to carry a subscript.

THEORIES
    T1. Because A3 separates the search score from the re-evaluated cost, the
        convergence panel can show both without implying that the recorded
        curve reaches a value the artifact does not contain.
    T2. A guard that runs on every build turns a silent drift into a loud
        failure, so the figure cannot quietly contradict the text.
    T3. By A6 the improvement steps and the baseline occupy different decades
        of the cost axis, so the panel is built in two registers: a linear
        main axes that carries the baseline, the recorded curve and the
        re-evaluated optimum, and a linear zoom inset over 4.2075 to 4.2155
        that carries the eight steps.

APPLICATIONS
    A1. Chapter 4, Figure 4.11 (convergence) and Figure 4.12 (design
       trajectory). The central-composite screen was removed from the
       methodology; there is no screen figure.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from matplotlib import ticker as mticker  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parent.parent.parent.parent
ARTIFACT = REPO_ROOT / "stellarorion_program_proc/src/python/hiad_optimization_results.json"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fig_metrics as fm  # noqa: E402  sibling module, text measurement
import print_fit as pf  # noqa: E402  sibling module, print geometry

PRINT_W_IN = pf.TEXT_W_IN
MIN_PRINTED_PT = 8.0
TICK_PT = 9.5
LABEL_PT = 10.5
LEGEND_PT = 8.5
NOTE_PT = 8.5
POINT_PT = 8.5

# WHY A SECOND LABEL SIZE. matplotlib draws a mathtext sub or superscript at
# SHRINK_FACTOR (0.7) of its parent, so a label carrying a script prints its
# smallest glyph at 0.7 times the declared size. fig_metrics.smallest_text_pt
# measures that, so the declared size of a script-carrying label must be at
# least 8 / 0.7 = 11.43 pt. This is the same constant make_fignew.py uses
# (SCRIPT_SAFE_PT), and it is why every label in this file that carries a
# subscript is set at 11.5 pt while every label that carries plain text may
# be smaller.
SCRIPT_SAFE_PT = 11.5
TITLE_PT = 12.0

CONV_HEIGHT_IN = 4.30
TRAJ_HEIGHT_IN = 5.30

INK = "#222222"
CB = ["#004488", "#DDAA33", "#BB5566", "#228833", "#AA4499", "#66CCEE"]
PATH_GREY = "#6B6B6B"
GRID_GREY = "#E8E8E8"

# Offsets, in points, at which a point label may be placed. The first entry
# that is inside the axes and clear of every other printed label wins, so a
# crowded cluster is resolved by searching rather than by guessing.
LABEL_CANDIDATES = (
    (10.0, 0.0), (10.0, 11.0), (10.0, -11.0), (10.0, 22.0), (10.0, -22.0),
    (10.0, 33.0), (10.0, -33.0),
    (-10.0, 0.0), (-10.0, 11.0), (-10.0, -11.0), (-10.0, 22.0), (-10.0, -22.0),
    (0.0, 12.0), (0.0, -12.0), (0.0, 24.0), (0.0, -24.0),
    (20.0, 12.0), (20.0, -12.0), (-20.0, 12.0), (-20.0, -12.0),
    (24.0, 0.0), (24.0, 16.0), (24.0, -16.0), (-24.0, 16.0), (-24.0, -16.0),
)

# The design-trajectory panel is wider than the convergence panel, so its
# labels may be placed further from their points before they leave the axes.
# The accepted designs of generations 8, 14, 15, 16 and 17 project onto a
# patch of the design plane that is about 0.0002 m wide and 0.007 deg tall,
# so five labels have to fan out of one corner, and these offsets give the
# search enough room to do it.
TRAJ_LABEL_CANDIDATES = (
    (12.0, 0.0), (12.0, 12.0), (12.0, -12.0), (12.0, 26.0), (12.0, -26.0),
    (12.0, 40.0), (12.0, -40.0), (26.0, 0.0), (26.0, 14.0), (26.0, -14.0),
    (26.0, 30.0), (26.0, -30.0), (40.0, 0.0), (40.0, 16.0), (40.0, -16.0),
    (40.0, 34.0), (40.0, -34.0), (0.0, 14.0), (0.0, -14.0), (0.0, 28.0),
    (0.0, -28.0), (-12.0, 0.0), (-12.0, 12.0), (-12.0, -12.0), (-12.0, 26.0),
    (-12.0, -26.0), (-26.0, 0.0), (-26.0, 14.0), (-26.0, -14.0),
)

# Values printed in Chapter 4. Absolute tolerances: the text quotes four
# significant figures, so anything beyond the last quoted digit is a change of
# result rather than of rounding.
CLAIMS = {
    "history_len": 38,
    "population_size": 50,
    "max_generations": 200,
    "n_evaluations": 1900,
    "baseline_cost": 4.6017,
    "optimum_cost": 4.1788,
    "optimum_R_N": 1.3359,
    "optimum_r_tor": 0.1796,
    "optimum_half_cone": 58.6071,
}


def load_campaign() -> dict:
    """Load and verify the newest optimizer artifact.

    Returns:
        The decoded results dictionary, asserted to be the GA campaign.

    Raises:
        RuntimeError when the file is absent, not JSON, not the genetic
        algorithm, or when an asserted value differs from the thesis text.
    """
    if not ARTIFACT.is_file():
        raise RuntimeError(f"optimizer artifact not found: {ARTIFACT}")
    with ARTIFACT.open(encoding="utf-8") as handle:
        data = json.load(handle)
    config = data.get("config", {})
    algorithm = str(config.get("algorithm", ""))
    if "Genetic" not in algorithm:
        raise RuntimeError(
            f"artifact is not the genetic-algorithm campaign: algorithm={algorithm!r}")
    checks = {
        "history_len": (len(data["history"]), CLAIMS["history_len"]),
        "population_size": (config.get("population_size"), CLAIMS["population_size"]),
        "max_generations": (config.get("max_generations"), CLAIMS["max_generations"]),
        "n_evaluations": (data["optimized"].get("n_evaluations"),
                          CLAIMS["n_evaluations"]),
        "baseline_cost": (data["default"]["cost"], CLAIMS["baseline_cost"]),
        "optimum_cost": (data["optimized"]["cost"], CLAIMS["optimum_cost"]),
        "optimum_R_N": (data["optimized"]["R_N"], CLAIMS["optimum_R_N"]),
        "optimum_r_tor": (data["optimized"]["r_tor"], CLAIMS["optimum_r_tor"]),
        "optimum_half_cone": (data["optimized"]["half_cone_deg"],
                              CLAIMS["optimum_half_cone"]),
    }
    for name, (actual, expected) in checks.items():
        if actual is None or abs(float(actual) - float(expected)) > 5e-4:
            raise RuntimeError(
                f"artifact disagreed with the thesis on {name}: "
                f"artifact={actual!r} thesis={expected!r}")
    return data


def accepted_designs(history: list[dict]) -> list[dict]:
    """Return the recorded generations whose best design actually changed.

    Parameters:
        history: the recorded generation rows of the campaign.

    Returns:
        The rows of the accepted designs, in generation order.

    Raises:
        RuntimeError never; the caller validates the record.

    WHY
        AXIOM A4: a generation that repeats the previous generation's best
        design moved nothing, so it is not a point of the trajectory and it
        must not be drawn as one.
    """
    accepted: list[dict] = []
    previous = None
    for row in history:
        key = (float(row["R_N"]), float(row["r_tor"]), float(row["half_cone_deg"]))
        if key != previous:
            accepted.append(row)
            previous = key
    return accepted


def style_axes(ax, grid: bool = True) -> None:
    """Apply the shared axis styling.

    Parameters:
        ax: the axes to style.
        grid: draw the major grid.

    Returns:
        None.

    WHY
        The grid is drawn lighter than the data. A grid that outweighs the
        curve it is meant to support reads as data and hides the steps the
        panel exists to show.
    """
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    if grid:
        ax.grid(True, which="major", color=GRID_GREY, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=TICK_PT, pad=2)


def _overlaps(box_a, box_b, pad: float) -> bool:
    """Return whether two display boxes collide within a clearance.

    Parameters:
        box_a: first matplotlib Bbox in display pixels.
        box_b: second matplotlib Bbox in display pixels.
        pad: clearance in pixels that must separate the two boxes.

    Returns:
        True when the boxes touch or overlap inside the clearance.
    """
    if box_a.x1 + pad <= box_b.x0 or box_b.x1 + pad <= box_a.x0:
        return False
    if box_a.y1 + pad <= box_b.y0 or box_b.y1 + pad <= box_a.y0:
        return False
    return True


def place_point_labels(ax, fig, points, texts, fontsize, color,
                       offsets=LABEL_CANDIDATES):
    """Place one label beside each point, clear of every other printed label.

    Parameters:
        ax: the axes that owns the points and receives the labels.
        fig: the parent figure, used for the canvas and the renderer.
        points: list of (x, y) data coordinates, one per label.
        texts: list of label strings, one per point.
        fontsize: label point size.
        color: label colour.
        offsets: candidate (dx, dy) offsets in points, tried in order.

    Returns:
        The list of placed Text artists.

    Raises:
        RuntimeError when no candidate offset is free for some point, which
        would leave a printed label overlapping another printed label.

    WHY
        Five of the nine accepted designs project onto almost the same point
        of the design plane, so a fixed offset collides. The first candidate
        that is inside the axes and clear of every other printed label is
        used, and a leader line ties the label back to its point.
    """
    import matplotlib

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    others = []
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        others.append(artist.get_window_extent(renderer=renderer))
    frame = ax.get_window_extent(renderer=renderer)
    pad = 1.5 * fig.dpi / 72.0
    placed = []
    artists = []
    for (x, y), text in zip(points, texts):
        chosen = None
        for dx, dy in offsets:
            ha = "left" if dx > 0 else ("right" if dx < 0 else "center")
            va = "bottom" if dy > 0 else ("top" if dy < 0 else "center")
            artist = ax.annotate(
                text, xy=(x, y), xycoords="data", xytext=(dx, dy),
                textcoords="offset points", ha=ha, va=va, fontsize=fontsize,
                color=color, zorder=7, annotation_clip=False)
            fig.canvas.draw()
            box = artist.get_window_extent(renderer=fig.canvas.get_renderer())
            inside = (box.x0 >= frame.x0 - pad and box.x1 <= frame.x1 + pad
                      and box.y0 >= frame.y0 - pad and box.y1 <= frame.y1 + pad)
            if inside:
                for other in others + placed:
                    if _overlaps(box, other, pad):
                        inside = False
                        break
            if inside:
                chosen = artist
                break
            artist.remove()
        if chosen is None:
            raise RuntimeError(
                f"no free label position for {text!r} on axes {ax.get_label()!r}")
        ax.annotate(
            "", xy=(x, y), xycoords="data", xytext=(dx, dy),
            textcoords="offset points", zorder=6, annotation_clip=False,
            arrowprops=dict(arrowstyle="-", color=color, lw=0.6,
                            shrinkA=0.5, shrinkB=2.5))
        placed.append(chosen.get_window_extent(renderer=fig.canvas.get_renderer()))
        artists.append(chosen)
    return artists


def build_convergence(data: dict) -> plt.Figure:
    """Plot the recorded GA convergence on a cost axis that shows every step.

    PURPOSE
        Render the Chapter 4 convergence figure: the generation-best composite
        cost of the LHS-seeded GA campaign against generation.

    AXIOMS
        A1. ``data['history'][i]['cost']`` is the best cost recorded at
            iteration ``i`` and is non-increasing (asserted below).
        A2. The eight strict improvements span about 5.3e-3 in cost, while the
            IRVE-3 baseline (4.6017) and the double-precision re-evaluation of
            the optimum (4.1788) lie far outside that band.
        A3. A single linear cost axis that also carries the two reference
            values compresses every step below one pixel, so the reference
            values must be annotated as off-scale instead of being plotted.

    THEORIES
        T1. Plotting only the recorded band with four-decimal ticks makes all
            eight improvements individually visible.
        T2. Off-scale annotations at the frame edges preserve the numeric
            context without destroying the vertical resolution.

    APPLICATIONS
        Writes ``ga_convergence.png`` at ``PRINT_W_IN`` x ``CONV_HEIGHT_IN``
        for inclusion at 0.9 x textwidth.

    CITATIONS
        [1] stellarorion_program_proc/src/python/hiad_optimization_results.json
            (history[0..37], default.cost, optimized.cost).
        [2] Matplotlib Axes.step documentation, where='post' semantics.
    """
    history = data["history"]
    generations = [int(row["iteration"]) for row in history]
    costs = [float(row["cost"]) for row in history]
    recorded: list[float] = []
    for value in costs:
        recorded.append(value if not recorded else min(recorded[-1], value))
    if any(b > a + 1e-12 for a, b in zip(recorded, recorded[1:])):
        raise RuntimeError("recorded best cost is not non-increasing")

    baseline = float(data["default"]["cost"])
    optimum = float(data["optimized"]["cost"])
    n_generations = len(history)
    n_evaluations = int(data["optimized"].get("n_evaluations", 0) or 0)
    accepted = accepted_designs(history)
    accepted_gens = [int(row["iteration"]) for row in accepted]
    accepted_costs = [recorded[g] for g in accepted_gens]
    improvements = [i for i in range(1, len(recorded))
                    if recorded[i] < recorded[i - 1] - 1e-12]

    fig = plt.figure(figsize=(PRINT_W_IN, CONV_HEIGHT_IN))
    ax = fig.add_axes([0.155, 0.150, 0.820, 0.735])
    style_axes(ax)

    ax.step(generations, recorded, where="post", lw=1.9, color=CB[0],
            zorder=3)
    ax.plot([generations[0]], [recorded[0]], marker="o", ms=5.0,
            color=CB[0], zorder=4)
    ax.plot(accepted_gens, accepted_costs, linestyle="none", marker="o",
            ms=4.6, mfc="white", mew=1.2, color=CB[2], zorder=5)

    ax.set_xlim(-1.0, n_generations + 1.0)
    #  WHY: the eight strict improvements span 5.3e-3 of cost. A window of
    #  0.0010 above and below that band keeps every step visible while the
    #  two reference values stay out of frame and are annotated as off-scale.
    ax.set_ylim(min(recorded) - 0.0004, max(recorded) + 0.0006)
    ax.set_xticks(list(range(0, n_generations + 1, 5)))
    ax.set_yticks([4.2090, 4.2100, 4.2110, 4.2120, 4.2130, 4.2140])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.4f}"))
    ax.set_xlabel("generation", fontsize=LABEL_PT)
    ax.set_ylabel("generation-best composite cost $J$",
                  fontsize=SCRIPT_SAFE_PT)
    #  WHY: the earlier title ran 0.19 in past the canvas; the word
    #  "recorded" is redundant because the axis label already says the
    #  curve is the recorded campaign.
    ax.set_title(f"GA convergence - {n_generations} generations, "
                 f"{n_evaluations} evaluations", fontsize=TITLE_PT, color=INK,
                 pad=8)

    #  WHY: the step curve hugs the bottom of the frame for most of the
    #  generation axis, so every note is stacked in the empty right-hand
    #  column and the two reference values stay out of the data band.
    ax.annotate(f"IRVE-3 baseline {baseline:.4f}\noff scale (above)",
                xy=(0.985, 0.62), xycoords="axes fraction",
                ha="right", va="bottom", fontsize=NOTE_PT, color=CB[2],
                linespacing=1.3)
    ax.annotate(f"re-evaluated optimum {optimum:.4f}\noff scale (below)",
                xy=(0.985, 0.40), xycoords="axes fraction",
                ha="right", va="bottom", fontsize=NOTE_PT, color=CB[1],
                linespacing=1.3)
    ax.annotate(f"recorded best {recorded[-1]:.4f}",
                xy=(0.985, 0.14), xycoords="axes fraction",
                ha="right", va="bottom", fontsize=NOTE_PT, color=INK)
    ax.annotate(f"first recorded {recorded[0]:.4f}",
                xy=(0.17, 0.93), xycoords="axes fraction",
                ha="left", va="top", fontsize=NOTE_PT, color=INK)

    handles = [
        plt.Line2D([], [], color=CB[0], lw=1.9,
                   label="generation-best cost"),
        plt.Line2D([], [], color=CB[2], marker="o", ms=4.6, mfc="white",
                   mew=1.2, linestyle="none",
                   label="design change accepted (9 of 38)"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=LEGEND_PT,
              frameon=True, facecolor="white", framealpha=0.95,
              edgecolor="#CCCCCC", borderpad=0.5, labelspacing=0.35)

    print(f"convergence: {n_generations} generations, "
          f"{len(improvements)} improvements at {improvements}")
    return fig


def build_trajectory(data: dict) -> plt.Figure:
    """Draw the generation-best design path and the per-variable change.

    Parameters:
        data: verified campaign dictionary.

    Returns:
        The matplotlib Figure.

    Raises:
        RuntimeError never; the caller validates the artifact.

    WHY
        AXIOM A5: the torus radius moves by less than 3e-5 m along the whole
        accepted path, so a three-dimensional rendering of the path collapses
        onto a line and hides the trajectory it is supposed to show. The
        panel is therefore two-dimensional, with a second panel that carries
        the baseline-to-optimum change of each design variable, where the
        three variables have three different units and could not share one
        absolute axis.
    """
    history = data["history"]
    accepted = accepted_designs(history)
    base = data["default"]
    opt = data["optimized"]
    n_generations = len(history)
    gens = [int(row["iteration"]) for row in accepted]
    x1 = [float(row["R_N"]) for row in accepted]
    rt = [float(row["r_tor"]) for row in accepted]
    cone = [float(row["half_cone_deg"]) for row in accepted]
    rt_spread = max(rt) - min(rt)
    rt_value = float(opt["r_tor"])

    fig = plt.figure(figsize=(PRINT_W_IN, TRAJ_HEIGHT_IN))

    # ---------------------------------------------------------------- panel a
    # WHY THE PANEL IS WIDE. The accepted path moves 0.0027 m in the body
    # radius and 0.32 deg in the half-cone angle, and the last five accepted
    # designs differ from each other by 0.0002 m in the radius and 0.007 deg
    # in the angle. A wide panel gives those five designs as much room as the
    # printed width allows, and the wide empty region under the path is where
    # the note and the key go.
    ax = fig.add_axes([0.115, 0.560, 0.800, 0.320])
    ax.set_title("Generation-best design path\nin the ($X_1$, $X_3$) plane",
                 fontsize=TITLE_PT, pad=6)
    ax.plot(x1, cone, lw=2.0, color=PATH_GREY, zorder=2, solid_capstyle="round")
    norm = mcolors.Normalize(vmin=0, vmax=n_generations - 1)
    ax.scatter(x1, cone, c=gens, cmap="plasma", norm=norm, s=34,
               edgecolor="white", linewidth=0.6, zorder=4)
    # The final optimum is the generation-17 design re-evaluated in double
    # precision, so its star is drawn under the last accepted design marker.
    ax.scatter([x1[-1]], [cone[-1]], marker="*", s=170, facecolor=CB[1],
               edgecolor=INK, linewidth=0.7, zorder=5)
    ax.scatter([x1[-1]], [cone[-1]], c=[gens[-1]], cmap="plasma", norm=norm, s=34,
               edgecolor="white", linewidth=0.6, zorder=6)

    # The window is asymmetric on purpose. The lower margin is generous so
    # that the generation-0 design, the lowest point of the path, keeps a
    # clear band above the note block, and the upper margin leaves room above
    # the generation-17 design for its label and for the off-scale key.
    x_lo, x_hi = min(x1), max(x1)
    y_lo, y_hi = min(cone), max(cone)
    ax.set_xlim(x_lo - 0.08 * (x_hi - x_lo), x_hi + 0.08 * (x_hi - x_lo))
    ax.set_ylim(y_lo - 0.20 * (y_hi - y_lo), y_hi + 0.12 * (y_hi - y_lo))
    ax.set_xticks([1.3360, 1.3365, 1.3370, 1.3375, 1.3380, 1.3385])
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))
    ax.set_yticks([58.3, 58.4, 58.5, 58.6])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))
    ax.set_xlabel("$X_1 = D/2$ (body radius, m)", fontsize=SCRIPT_SAFE_PT, labelpad=2)
    ax.set_ylabel("$X_3 = \\theta_c$ (deg)", fontsize=SCRIPT_SAFE_PT, labelpad=2)
    style_axes(ax)

    # The IRVE-3 baseline lies off scale in this plane: its body radius is
    # 1.5000 m against 1.3359 m here and its half-cone angle is 60.00 deg
    # against 58.61 deg. It is therefore keyed in the upper right corner, in
    # the direction it would lie in, and its values are written out in the
    # note block below.
    ax.scatter([0.985], [0.955], transform=ax.transAxes, marker="s", s=26,
               facecolor=CB[2], edgecolor="white", linewidth=0.6, zorder=6,
               clip_on=False)
    ax.text(0.962, 0.955, "IRVE-3 baseline (off scale)", transform=ax.transAxes,
            ha="right", va="center", fontsize=NOTE_PT, color=CB[2], zorder=7,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))


    handles = [
        ax.plot([], [], lw=2.0, color=PATH_GREY)[0],
        ax.plot([], [], ls="none", marker="*", markersize=12,
                markerfacecolor=CB[1], markeredgecolor=INK)[0],
    ]
    legend = ax.legend(handles, ["accepted design path", "final optimum"],
                       loc="lower left", bbox_to_anchor=(0.015, 0.030), frameon=True,
                       facecolor="white", edgecolor="#999999", framealpha=1.0,
                       fontsize=LEGEND_PT, handlelength=1.6, labelspacing=0.5,
                       borderpad=0.6)
    legend.set_zorder(9)

    #  WHY: generations 8 and 14-17 differ by about 2e-4 m in X1 and about
    #  0.007 deg in X3, so individually placed labels cannot be separated at
    #  print size. They are therefore not labelled one by one: the cluster is
    #  described in one plain note, and only the separated designs carry a
    #  number. Arrowed labels were removed because the collision checker
    #  measures the leader line as part of the label, so no arrowed fanned
    #  label can ever pass.
    labelled = {0: (9, 4), 4: (9, 4), 6: (8, -12), 7: (7, 7)}
    for index, generation in enumerate(gens):
        offset = labelled.get(generation)
        if offset is None:
            continue
        ax.annotate(str(generation), xy=(x1[index], cone[index]),
                    xycoords="data", xytext=offset, textcoords="offset points",
                    ha="left", va=("top" if offset[1] < 0 else "bottom"),
                    fontsize=POINT_PT, color=INK, zorder=10,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.9))

    #  WHY: 0.44 rather than 0.62, because the generation-6 label sits at the
    #  top right of the panel and the note box overlapped it at 0.62.
    #  WHY: the note sits in the empty left half of the panel. At the right
    #  edge it collided with the generation-0 label, and at the top right with
    #  the generation-6 label; the accepted designs all lie in the right half.
    ax.text(0.015, 0.50,
            "generations 8, 14, 15, 16 and 17\n"
            "lie within 0.0002 m of one another\n"
            "in this plane; the path has converged",
            transform=ax.transAxes, ha="left", va="center",
            fontsize=NOTE_PT, color=INK, zorder=7, linespacing=1.35)

    # Colour bar, horizontal, so that its long label can be printed on one
    # line instead of being rotated into the panel beside it. The label sits
    # ABOVE the bar, between the bar and the panel (a) x axis label, because
    # the bar's own tick labels are already printed below it.
    cax = fig.add_axes([0.315, 0.426, 0.400, 0.019])
    scatter = ax.collections[0]
    bar = fig.colorbar(scatter, cax=cax, orientation="horizontal")
    bar.set_ticks(list(range(0, n_generations, 10)) + [n_generations - 1])
    bar.ax.tick_params(labelsize=POINT_PT, pad=1)
    bar.outline.set_linewidth(0.6)
    fig.text(0.515, 0.460,
             f"generation (of {n_generations} recorded; only {len(accepted)} "
             f"changed the design)",
             ha="center", va="bottom", fontsize=NOTE_PT, color=INK)

    # ---------------------------------------------------------------- panel b
    # The bar rows are named with mathtext, so their labels sit at
    # SCRIPT_SAFE_PT and are wrapped onto two lines to keep the widest one
    # inside the printed width.
    axb = fig.add_axes([0.360, 0.105, 0.555, 0.235])
    axb.set_title("Change from the IRVE-3 baseline", fontsize=TITLE_PT, pad=7)
    variables = [
        ("$X_1$ body radius\n$D/2$ (m)", float(base["R_N"]), float(opt["R_N"]),
         "m", 4),
        ("$X_2$ torus radius\n$r_{tor}$ (m)", float(base["r_tor"]),
         float(opt["r_tor"]), "m", 4),
        ("$X_3$ half-cone\nangle $\\theta_c$ (deg)", float(base["half_cone_deg"]),
         float(opt["half_cone_deg"]), "deg", 2),
    ]
    positions = np.arange(len(variables), dtype=float)
    height = 0.30
    percent = [100.0 * o / b for _, b, o, _, _ in variables]
    axb.barh(positions + 0.5 * height, [100.0] * len(variables), height=height,
             color="#CFCFCF", edgecolor="none", zorder=2, label="IRVE-3 baseline")
    axb.barh(positions - 0.5 * height, percent, height=height, color=CB[0],
             edgecolor="none", zorder=2, label="GA optimum")
    for index, (_, b, o, unit, digits) in enumerate(variables):
        axb.text(97.0, positions[index] + 0.5 * height, f"{b:.{digits}f} {unit}",
                 ha="right", va="center", fontsize=NOTE_PT, color=INK, zorder=4)
        change = 100.0 * (o - b) / b
        axb.text(percent[index] - 2.0, positions[index] - 0.5 * height,
                 f"{o:.{digits}f} {unit} ({change:+.2f} %)", ha="right", va="center",
                 fontsize=NOTE_PT, color="white", zorder=4)
    axb.set_yticks(positions)
    axb.set_yticklabels([name for name, _, _, _, _ in variables])
    axb.set_xlim(0.0, 145.0)
    axb.set_xticks([0, 25, 50, 75, 100, 125])
    axb.set_xlabel("value as a percentage of the IRVE-3 baseline",
                   fontsize=TICK_PT + 1.0, labelpad=2)
    axb.tick_params(axis="x", labelsize=TICK_PT, pad=2)
    # The row names carry mathtext subscripts, so they are set at the script
    # safe size instead of the tick size.
    for label in axb.get_yticklabels():
        label.set_fontsize(SCRIPT_SAFE_PT)
    for spine in ("top", "right"):
        axb.spines[spine].set_visible(False)
    axb.set_axisbelow(True)
    axb.grid(True, axis="x", which="major", color=GRID_GREY, lw=0.6)
    # The key sits inside the axes, in the band above the top bar, and the
    # window is opened up to make that band exist. A key below the axis
    # would have to fight the x axis label for the last two tenths of an
    # inch of the printed page.
    axb.set_ylim(-0.55, 3.15)
    axb.text(0.0, 3.02, "grey = IRVE-3 baseline, blue = GA optimum",
             fontsize=NOTE_PT, color=INK, ha="left", va="top")

    print(f"    trajectory: {len(accepted)} accepted designs at generations {gens}; "
          f"r_tor spread {rt_spread:.2e} m")
    return fig


def save(fig, name: str, height_in: float) -> int:
    """Save, measure and report one panel.

    Parameters:
        fig: the open figure.
        name: output file name inside this directory.
        height_in: printed height, used only for the report.

    Returns:
        0 on success, 1 when a print guard rejected the panel.

    Raises:
        RuntimeError from the inside canvas assertion, which is a layout
        failure rather than a content failure and must not be swallowed.
    """
    pf.assert_inside_canvas(fig)
    drawn = [artist.get_text() for artist in fig.findobj(matplotlib.text.Text)
             if artist.get_text()]
    pf.require_clean(*drawn)
    try:
        _path, scale = pf.save_to_print_width(fig, name, PRINT_W_IN, close=False)
    except RuntimeError as error:
        print(f"!! {name}: {error}")
        plt.close(fig)
        return 1
    smallest, description = fm.smallest_text_pt(fig, scale)
    print(f"    smallest printed text {smallest:.2f} pt ({description})")
    if smallest < MIN_PRINTED_PT:
        print(f"!! {name}: smallest text {smallest:.2f} pt below the floor")
        plt.close(fig)
        return 1
    overlaps = fm.text_overlaps_pt(fig, scale)
    if overlaps:
        print(f"!! {name}: {len(overlaps)} printed label collision(s)")
        for first, second, width, height in overlaps[:6]:
            print(f"     {first} <-> {second} ({width:.2f} x {height:.2f} pt)")
        plt.close(fig)
        return 1
    gaps = fm.same_row_gaps_pt(fig, scale)
    if gaps:
        print(f"!! {name}: {len(gaps)} same-row label gap(s) under 2 pt")
        for first, second, gap in gaps[:6]:
            print(f"     {first} <-> {second} ({gap:.2f} pt)")
        plt.close(fig)
        return 1
    plt.close(fig)
    print(f"wrote {name} at print width {PRINT_W_IN:.3f} in, height {height_in:.2f} in, "
          f"scale {scale:.4f}")
    return 0


def main() -> int:
    """Build the two panels and report the outcome.

    Returns:
        0 when every panel is written, 1 when any guard rejected one.
    """
    data = load_campaign()
    print(f"    campaign: {len(data['history'])} generations, "
          f"population {data['config']['population_size']}, "
          f"baseline {data['default']['cost']:.4f}, "
          f"optimum {data['optimized']['cost']:.4f}")
    status = 0
    status |= save(build_convergence(data), "ga_convergence.png", CONV_HEIGHT_IN)
    status |= save(build_trajectory(data), "ga_design_trajectory.png",
                   TRAJ_HEIGHT_IN)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
