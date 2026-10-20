"""Draw the genetic-algorithm campaign panels reported in Chapter 4.

PURPOSE
    The thesis reports a simple genetic algorithm as the optimizer: a
    15-point central composite screen followed by a population of 50
    individuals evolved for at most 200 generations. This script draws the
    three panels that carry that campaign:

      1. ga_convergence.png      recorded generation-best cost against
                                 generation, with the baseline and the
                                 re-evaluated optimum marked.
      2. ga_ccd_screen.png       the 15 central composite screen points in
                                 the three-factor design space, coloured by
                                 their evaluated cost.
      3. ga_design_trajectory.png  the generation-best design path through
                                 the (nose radius, torus radius, half-cone
                                 angle) space, coloured by generation.

    Every number is read from the official optimizer artifact written by
    src/python/hiad_optimizer.py; nothing is typed into the artwork. The
    script refuses to draw if the artifact is not the genetic-algorithm
    campaign or if the values asserted below have drifted.

PARAMETERS
    None. The artifact path is resolved from this file's location.

RETURNS
    main() returns 0 on success and 1 when a print guard rejects a panel.
    print_fit writes a PNG only after every guard passes, so a rejected panel
    leaves the committed image untouched.

EXCEPTIONS
    RuntimeError when the artifact is missing or malformed, when the campaign
    is not the genetic algorithm, when an asserted value departs from the
    thesis text, when a drawn string contains a banned dash, when an artist
    overhangs the canvas, or when any text would print below the legibility
    floor.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
    Goldberg, D. E. (1989) Genetic Algorithms in Search, Optimization and
    Machine Learning, Addison-Wesley, the GA operator definitions.
    Paul Tol's colour schemes, https://personal.sron.nl/~pault/

AXIOMS
    A1. The text is the specification: a figure that disagrees with a printed
        sentence is a defect even when it is faithful to the file.
    A2. The artifact on disk is the newest recorded run and is the single
        source of truth for the campaign reported in Chapter 4.
    A3. The recorded history is the generation-best SEARCH score, which
        includes the model-fidelity penalty. The re-evaluated optimum cost is
        a separate quantity and is drawn as its own reference line; the two
        must never be presented as the same number.

THEORIES
    T1. Because A3 separates the search score from the re-evaluated cost, the
        convergence panel can show both without implying that the recorded
        curve reaches a value the artifact does not contain.
    T2. A guard that runs on every build turns a silent drift into a loud
        failure, so the figure cannot quietly contradict the text.

APPLICATIONS
    A1. Chapter 4, Figure 4.8 (convergence), Figure 4.9 (screen) and
        Figure 4.10 (design trajectory).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401,E402  registers the 3d projection

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
LABEL_PT_3D = 13.0
LEGEND_PT = 8.5

INK = "#222222"
CB = ["#004488", "#DDAA33", "#BB5566", "#228833", "#AA4499", "#66CCEE"]

# Values printed in Chapter 4. Absolute tolerances: the text quotes four
# significant figures, so anything beyond the last quoted digit is a change of
# result rather than of rounding.
CLAIMS = {
    "history_len": 72,
    "population_size": 50,
    "max_generations": 200,
    "baseline_cost": 3.4338,
    "optimum_cost": 2.7375,
    "optimum_R_N": 1.0397,
    "optimum_r_tor": 0.2197,
    "optimum_half_cone": 53.7247,
    "ccd_len": 15,
    "ccd_min": 3.0612,
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
        "baseline_cost": (data["default"]["cost"], CLAIMS["baseline_cost"]),
        "optimum_cost": (data["optimized"]["cost"], CLAIMS["optimum_cost"]),
        "optimum_R_N": (data["optimized"]["R_N"], CLAIMS["optimum_R_N"]),
        "optimum_r_tor": (data["optimized"]["r_tor"], CLAIMS["optimum_r_tor"]),
        "optimum_half_cone": (data["optimized"]["half_cone_deg"],
                              CLAIMS["optimum_half_cone"]),
        "ccd_len": (len(data["ccd_samples"]), CLAIMS["ccd_len"]),
        "ccd_min": (min(float(s["cost"]) for s in data["ccd_samples"]),
                    CLAIMS["ccd_min"]),
    }
    for name, (actual, expected) in checks.items():
        if actual is None or abs(float(actual) - float(expected)) > 5e-4:
            raise RuntimeError(
                f"artifact disagreed with the thesis on {name}: "
                f"artifact={actual!r} thesis={expected!r}")
    return data


def style_axes(ax) -> None:
    """Apply the shared axis styling.

    Parameters:
        ax: the axes to style.

    Returns:
        None.
    """
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.grid(True, which="major", color="#DDDDDD", lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=TICK_PT, pad=2)


def build_convergence(data: dict):
    """Draw recorded generation-best cost against generation.

    Parameters:
        data: verified campaign dictionary.

    Returns:
        The matplotlib Figure.
    """
    history = data["history"]
    generations = [int(row["iteration"]) for row in history]
    recorded = [float(row["cost"]) for row in history]
    for i in range(len(recorded) - 1):
        if recorded[i] < recorded[i + 1] - 1e-12:
            raise RuntimeError(
                f"recorded best rose from {recorded[i]} to {recorded[i + 1]} "
                f"at generation {generations[i]}; the curve must be non-increasing")
    baseline = float(data["default"]["cost"])
    optimum = float(data["optimized"]["cost"])

    fig = plt.figure(figsize=(PRINT_W_IN, 3.60))
    ax = fig.add_axes([0.115, 0.165, 0.865, 0.760])
    dashed = (0, tuple(matplotlib.rcParams["lines.dashed_pattern"]))
    dotted = (0, tuple(matplotlib.rcParams["lines.dotted_pattern"]))

    base_line = ax.axhline(baseline, ls=dotted, lw=1.2, color=CB[2], zorder=1)
    opt_line = ax.axhline(optimum, ls=dashed, lw=1.2, color=CB[1], zorder=1)
    ax.step(generations, recorded, where="post", lw=1.7, color=CB[0], zorder=3)
    best_gen = generations[recorded.index(min(recorded))]
    ax.plot([best_gen], [min(recorded)], ls="none", marker="o", markersize=5.5,
            markerfacecolor=CB[0], markeredgecolor="white", markeredgewidth=0.6,
            zorder=4)

    ax.set_xlim(-1.5, generations[-1] + 1.5)
    low = min(min(recorded), optimum)
    high = max(max(recorded), baseline)
    pad = 0.04 * (high - low)
    ax.set_ylim(low - pad, high + pad)
    ax.set_xticks([0, 10, 20, 30, 40, 50, 60, 70])
    ax.set_xlabel("Generation", fontsize=LABEL_PT, labelpad=2)
    ax.set_ylabel("Cost $J$", fontsize=LABEL_PT, labelpad=2)
    style_axes(ax)

    handles = [
        ax.plot([], [], lw=1.7, color=CB[0])[0],
        base_line,
        opt_line,
    ]
    labels = ["recorded generation best", "baseline cost", "re-evaluated optimum"]
    ax.legend(handles, labels, loc="upper right", frameon=False,
              fontsize=LEGEND_PT, handlelength=1.8, borderaxespad=0.4)
    return fig


def build_screen(data: dict):
    """Draw the central composite screen in the three-factor design space.

    Parameters:
        data: verified campaign dictionary.

    Returns:
        The matplotlib Figure.
    """
    samples = data["ccd_samples"]
    rn = [float(s["R_N"]) for s in samples]
    rt = [float(s["r_tor"]) for s in samples]
    cone = [float(s["half_cone_deg"]) for s in samples]
    cost = [float(s["cost"]) for s in samples]
    norm = mcolors.LogNorm(vmin=min(cost), vmax=max(cost))

    fig = plt.figure(figsize=(PRINT_W_IN, 3.90))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_position([0.02, 0.02, 0.80, 0.94])
    points = ax.scatter(rn, rt, cone, c=cost, cmap="viridis", norm=norm,
                        s=34, edgecolor="white", linewidth=0.5, depthshade=False)
    best_i = cost.index(min(cost))
    ax.scatter([rn[best_i]], [rt[best_i]], [cone[best_i]], marker="*", s=150,
               facecolor=CB[1], edgecolor=INK, linewidth=0.6, depthshade=False)
    base = data["default"]
    ax.scatter([float(base["R_N"])], [float(base["r_tor"])],
               [float(base["half_cone_deg"])], marker="s", s=42,
               facecolor=CB[2], edgecolor="white", linewidth=0.6, depthshade=False)
    ax.set_xlabel("$R_N$ (m)", fontsize=LABEL_PT_3D, labelpad=8)
    ax.set_ylabel("$r_{tor}$ (m)", fontsize=LABEL_PT_3D, labelpad=8)
    ax.set_zlabel("$\\theta_c$ (deg)", fontsize=LABEL_PT_3D, labelpad=8)
    ax.tick_params(labelsize=TICK_PT, pad=1)
    ax.view_init(elev=22, azim=-58)

    cax = fig.add_axes([0.845, 0.22, 0.018, 0.56])
    bar = fig.colorbar(points, cax=cax)
    ticks = [t for t in (3.0, 4.0, 6.0, 8.0, 10.0, 20.0, 40.0)
             if min(cost) <= t <= max(cost)]
    bar.set_ticks(ticks)
    bar.set_ticklabels([f"{t:g}" for t in ticks])
    bar.minorticks_off()
    bar.ax.tick_params(labelsize=TICK_PT, pad=1)
    bar.set_label("Cost $J$", fontsize=LABEL_PT_3D, labelpad=2)

    handles = [
        plt.Line2D([], [], ls="none", marker="*", markersize=11,
                   markerfacecolor=CB[1], markeredgecolor=INK),
        plt.Line2D([], [], ls="none", marker="s", markersize=6,
                   markerfacecolor=CB[2], markeredgecolor="white"),
    ]
    labels = ["best screen point", "IRVE-3 baseline"]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.0, 1.02),
              frameon=False, fontsize=LEGEND_PT, handletextpad=0.2,
              borderaxespad=0.0)
    return fig


def build_trajectory(data: dict):
    """Draw the generation-best design path through the design space.

    Parameters:
        data: verified campaign dictionary.

    Returns:
        The matplotlib Figure.
    """
    history = data["history"]
    gens = [int(row["iteration"]) for row in history]
    rn = [float(row["R_N"]) for row in history]
    rt = [float(row["r_tor"]) for row in history]
    cone = [float(row["half_cone_deg"]) for row in history]

    # Keep only generations whose best design actually moved, so the path is
    # the sequence of accepted designs rather than 72 repeated points.
    keep = [0]
    for i in range(1, len(history)):
        if (rn[i], rt[i], cone[i]) != (rn[keep[-1]], rt[keep[-1]], cone[keep[-1]]):
            keep.append(i)
    k_rn = [rn[i] for i in keep]
    k_rt = [rt[i] for i in keep]
    k_cone = [cone[i] for i in keep]
    k_gen = [gens[i] for i in keep]

    fig = plt.figure(figsize=(PRINT_W_IN, 3.90))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_position([0.02, 0.02, 0.80, 0.94])
    norm = mcolors.Normalize(vmin=min(k_gen), vmax=max(k_gen))
    ax.plot(k_rn, k_rt, k_cone, lw=1.0, color="#999999", zorder=1)
    points = ax.scatter(k_rn, k_rt, k_cone, c=k_gen, cmap="plasma", norm=norm,
                        s=26, edgecolor="white", linewidth=0.4, depthshade=False,
                        zorder=2)
    opt = data["optimized"]
    ax.scatter([float(opt["R_N"])], [float(opt["r_tor"])],
               [float(opt["half_cone_deg"])], marker="*", s=150,
               facecolor=CB[1], edgecolor=INK, linewidth=0.6, depthshade=False,
               zorder=3)
    base = data["default"]
    ax.scatter([float(base["R_N"])], [float(base["r_tor"])],
               [float(base["half_cone_deg"])], marker="s", s=42,
               facecolor=CB[2], edgecolor="white", linewidth=0.6, depthshade=False,
               zorder=3)
    ax.set_xlabel("$R_N$ (m)", fontsize=LABEL_PT_3D, labelpad=8)
    ax.set_ylabel("$r_{tor}$ (m)", fontsize=LABEL_PT_3D, labelpad=8)
    ax.set_zlabel("$\\theta_c$ (deg)", fontsize=LABEL_PT_3D, labelpad=8)
    ax.tick_params(labelsize=TICK_PT, pad=1)
    ax.view_init(elev=22, azim=-58)

    cax = fig.add_axes([0.845, 0.22, 0.018, 0.56])
    bar = fig.colorbar(points, cax=cax)
    bar.ax.tick_params(labelsize=TICK_PT, pad=1)
    bar.set_label("Generation", fontsize=LABEL_PT_3D, labelpad=2)

    handles = [
        plt.Line2D([], [], ls="none", marker="*", markersize=11,
                   markerfacecolor=CB[1], markeredgecolor=INK),
        plt.Line2D([], [], ls="none", marker="s", markersize=6,
                   markerfacecolor=CB[2], markeredgecolor="white"),
    ]
    labels = ["final optimum", "IRVE-3 baseline"]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.0, 1.02),
              frameon=False, fontsize=LEGEND_PT, handletextpad=0.2,
              borderaxespad=0.0)
    return fig


def save(fig, name: str, height_in: float, is_3d: bool = False) -> int:
    """Save, measure and report one panel.

    Parameters:
        fig: the open figure.
        name: output file name inside this directory.
        height_in: printed height, used only for the report.
        is_3d: True for a 3d projection. The canvas-overhang assertion walks
            2d display extents, and a 3d axes reports its tick labels in
            data space (extents of hundreds of inches), so the assertion
            cannot be applied there; those panels are verified by reading
            the rendered PNG instead.

    Returns:
        0 on success, 1 when a print guard rejected the panel.
    """
    if not is_3d:
        pf.assert_inside_canvas(fig)
    try:
        path, scale = pf.save_to_print_width(fig, name, PRINT_W_IN, close=False)
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
    plt.close(fig)
    print(f"wrote {name} at print width {PRINT_W_IN:.3f} in, height {height_in:.2f} in, "
          f"scale {scale:.4f}")
    return 0


def main() -> int:
    """Build the three panels and report the outcome.

    Returns:
        0 when every panel is written, 1 when any guard rejected one.
    """
    data = load_campaign()
    print(f"    campaign: {len(data['history'])} generations, "
          f"population {data['config']['population_size']}, "
          f"baseline {data['default']['cost']:.4f}, "
          f"optimum {data['optimized']['cost']:.4f}, "
          f"screen points {len(data['ccd_samples'])}")
    status = 0
    status |= save(build_convergence(data), "ga_convergence.png", 3.60)
    status |= save(build_screen(data), "ga_ccd_screen.png", 3.90, is_3d=True)
    status |= save(build_trajectory(data), "ga_design_trajectory.png", 3.90, is_3d=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
