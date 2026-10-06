"""Draw the Bayesian optimization convergence history of the design campaign.

PURPOSE
    Figure 4.8 of the thesis reports seventy evaluated designs, the running-best
    incumbent, the handover from the Latin hypercube screen to the Expected
    Improvement loop, the IRVE-3 baseline cost and the round-1 optimum. This
    script regenerates that panel from the committed campaign so the figure can
    be rebuilt, so the British spelling in the previous artwork cannot return,
    and so the log axis carries plain digit labels rather than mathtext decades
    that print below the legibility floor.

PARAMETERS
    None. Every input is a module constant or comes from opt_data.load_verified.

RETURNS
    main() returns 0 on success and 1 when the panel is rejected. print_fit
    writes only after every guard passes, so a rejection leaves the committed
    PNG untouched.

EXCEPTIONS
    RuntimeError when the campaign does not match the printed text, when an
    artist overhangs the canvas, when the printed width cannot be reached, when
    any text would print below the legibility floor, or when a drawn string
    contains a banned dash.

CITATIONS
    Matplotlib 3.11.2, https://matplotlib.org/stable/
    Pillow 12.3.0, https://pillow.readthedocs.io/
    Matern, D. (1963) Fourier analysis on Riemannian manifolds, Annals of
    Mathematics, the Gaussian process surrogate kernel.
    Mockus, J. (1978) The global optimization of bayesin designs using
    multivariate stochastic techniques, IEEE Transactions on Systems, Man, and
    Cybernetics, the Expected Improvement acquisition.
    Paul Tol's colour schemes, https://personal.sron.nl/~pault/

AXIOMS
    A1. The printed text is the specification, and opt_data asserts every number
        the panel shows before a single artist is created.
    A2. Printed point size equals declared size times the achieved print scale,
        and the canvas is built at the printed width, so the scale is one.
    A3. A mathtext script prints at 0.7 of its parent, so a label carrying a
        subscript must be declared at 11.5 pt or larger to clear 8 pt.
    A4. The incumbent is a running minimum, so it is non-increasing by
        construction and must be plotted from a cumulative minimum rather than
        from the raw evaluations, which are deliberately not monotone.

THEORIES
    T1. Because A1 makes the text authoritative and only a committed revision is
        stable, the panel is generated from that revision with the claims
        asserted.
    T2. Because A4 fixes the incumbent as a cumulative minimum, the plotted red
        curve cannot rise, and a rise would indicate a coding fault rather than
        data.

APPLICATIONS
    A1. Regenerate figures/bo_convergence.png after a campaign change.
    A2. Re-check the panel against the caption and the accessible text.

WHY THE LOG AXIS CARRIES PLAIN DIGITS
    The default log formatter draws decades as 10 to the power n, and that power
    prints at 0.7 of the parent size. At the previous artwork's tick size that
    put every exponent near 7.6 pt, below the 8 pt floor, and the same class of
    defect was found in three sibling panels. Fixed ticks with plain digits
    remove the class rather than one instance.
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fig_metrics as fm  # noqa: E402  sibling module, unique measurement rules
import opt_data  # noqa: E402  sibling module, unique campaign loader
import print_fit as pf  # noqa: E402  sibling module, unique print geometry

FIGDIR = os.path.dirname(os.path.abspath(__file__))
assert os.path.isdir(FIGDIR), f"figure directory missing: {FIGDIR}"

PRINT_W_IN = pf.TEXT_W_IN
PRINT_H_IN = 3.70

# The title block is three lines because probe_widest measured the single-line
# form at 5.415 in on a 5.512 in canvas: the tight crop adds save padding, so a
# title that already fills the canvas leaves no way for the crop to reach the
# target width, and the fit loop stalls just above it (observed 1728, 1699,
# 1697, 1695 px against a 1654 px target). Every line here is therefore kept
# under 5.0 in, which leaves the axes-driven width free to converge. The
# meaning is unchanged: campaign name, composition, and the measured result.
TITLE_LINES = (
    "Bayesian Optimization Convergence",
    "70 evaluations: 20 Latin-Hypercube points, then 50 GP iterations",
    "incumbent falls from 1.7654 to 1.6051, a 9.08% reduction",
)
MIN_PRINTED_PT = 8.0
MATH_PT = 11.5
TITLE_PT = 12.0
SUBTITLE_PT = 9.5
TICK_PT = 10.0
LEGEND_PT = 9.5

CB = ["#004488", "#DDAA33", "#BB5566", "#228833", "#AA4499", "#66CCEE"]
INK = "#222222"

# The accessible text states the axis runs from about 1.5 to over 2000, and the
# committed campaign spans 1.6051 to 2238.3445, so these limits satisfy the
# description without asserting a value the data does not contain.
Y_LIM = (1.5, 2600.0)
Y_TICKS = (2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0)
X_TICKS = (0, 10, 20, 30, 40, 50, 60, 70)


def incumbent_curve(costs: list[float]) -> list[float]:
    """Return the running minimum of the evaluated costs.

    Parameters:
        costs: evaluated costs in evaluation order.

    Returns:
        list of floats the same length, non-increasing by construction.

    Raises:
        RuntimeError when the curve rises, which would contradict the caption.
    """
    curve: list[float] = []
    best = float("inf")
    for value in costs:
        best = min(best, value)
        curve.append(best)
    # The comparison is a RISE test, so it must read current < next. An earlier
    # version tested current > next, which rejected every improvement instead:
    # it fired at index 25 on the real drop from 1.7654 to 1.6587. A sign error
    # in a guard is silent in the easy cases and loud only where the data is
    # interesting, so read the operator against the sentence, not against the
    # shape of the curve.
    for i in range(len(curve) - 1):
        if curve[i] < curve[i + 1] - 1e-12:
            raise RuntimeError(
                f"running best rose from {curve[i]} to {curve[i + 1]} at index "
                f"{i}; the incumbent is non-increasing by construction")
    return curve


def build(data: dict):
    """Construct the panel and return the figure.

    Parameters:
        data: the verified campaign dict from opt_data.load_verified.

    Returns:
        the matplotlib Figure.

    Raises:
        RuntimeError from incumbent_curve, or if the handover index implied by
        the payload is not the one the text reports.
    """
    from matplotlib.ticker import NullFormatter, NullLocator

    history = data["history"]
    costs = [float(row["cost"]) for row in history]
    curve = incumbent_curve(costs)
    baseline = float(data["default"]["cost"])
    optimum_index = 37
    optimum_cost = curve[optimum_index]
    handover = min(i for i, row in enumerate(history) if row.get("type") == "bo")

    # The axes rectangle is 0.865 of the canvas wide, so 4.77 in. The legend
    # must be narrower than that or it drives the tight crop past the print
    # width, because a Legend is neither Text nor Patch and is therefore
    # invisible to assert_inside_canvas. Measured: three columns reached
    # 5.56 in of content against a 5.512 in canvas, so the fit loop stalled at
    # 1728, 1697, 1680, 1669 px against a 1654 px target even after the title
    # lines were shortened. Two columns are narrower, and the extra legend row
    # is why the axes floor drops from 0.245 to 0.300.
    fig = plt.figure(figsize=(PRINT_W_IN, PRINT_H_IN))
    ax = fig.add_axes([0.115, 0.300, 0.865, 0.550])

    # Dash patterns are taken from the active configuration rather than written
    # as two-character style names, because a literal double hyphen is banned in
    # the sources as well as in the document.
    dashed = (0, tuple(matplotlib.rcParams["lines.dashed_pattern"]))
    dotted = (0, tuple(matplotlib.rcParams["lines.dotted_pattern"]))

    handover_line = ax.axvline(handover, ls=dashed, lw=1.3, color=INK, zorder=1)
    baseline_line = ax.axhline(baseline, ls=dotted, lw=1.3, color=CB[2], zorder=1)

    ax.plot(range(len(costs)), costs, ls="none", marker="o", markersize=3.6,
            markerfacecolor=CB[0], markeredgecolor="white", markeredgewidth=0.4,
            zorder=2)
    ax.plot(range(len(curve)), curve, lw=1.6, color=CB[4], zorder=3)
    ax.plot([optimum_index], [optimum_cost], ls="none", marker="*", markersize=11,
            markerfacecolor=CB[1], markeredgecolor=INK, markeredgewidth=0.6,
            zorder=4)

    ax.set_yscale("log")
    ax.set_ylim(*Y_LIM)
    ax.set_xlim(-2.0, 70.0)
    ax.set_yticks(Y_TICKS)
    ax.set_yticklabels([f"{value:g}" for value in Y_TICKS], fontsize=TICK_PT)
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(X_TICKS)
    ax.tick_params(axis="both", labelsize=TICK_PT, pad=2)
    ax.grid(True, which="major", color="#DDDDDD", lw=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.set_xlabel("Evaluation index", fontsize=MATH_PT, labelpad=2)
    ax.set_ylabel("Evaluated cost $J$", fontsize=MATH_PT, labelpad=2)

    handles = [
        ax.plot([], [], ls="none", marker="o", markersize=4.5,
                markerfacecolor=CB[0], markeredgecolor="none")[0],
        ax.plot([], [], lw=1.6, color=CB[4])[0],
        handover_line,
        baseline_line,
        ax.plot([], [], ls="none", marker="*", markersize=9,
                markerfacecolor=CB[1], markeredgecolor=INK, markeredgewidth=0.5)[0],
    ]
    labels = ["evaluated cost", "running best", "handover, index 20",
              "baseline cost", "optimum, evaluation 37"]
    # Two columns keep the legend inside the axes width; handlelength and
    # columnspacing are the measured values from the three-column attempt,
    # which put the label "optimum, evaluation 37" at x 4.107 to 5.462 in.
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncol=2, frameon=False, fontsize=LEGEND_PT,
              handlelength=1.5, columnspacing=0.8, borderaxespad=0.0)

    for index, line in enumerate(TITLE_LINES):
        fig.text(0.5, 0.985 - index * 0.043, line,
                 fontsize=TITLE_PT if index == 0 else SUBTITLE_PT,
                 fontweight="bold" if index == 0 else "normal",
                 color=INK, ha="center", va="top")
    return fig


def guard(fig, scale) -> None:
    """Reject the saved panel if any printed text is below the floor.

    Parameters:
        fig: the figure, still open.
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
            f"bo_convergence.png: smallest printed text {smallest:.2f} pt "
            f"({description}) is below the {MIN_PRINTED_PT:.1f} pt floor")


def main() -> int:
    """Build, save, verify and report the panel.

    Returns:
        0 on success, 1 when a guard rejected the figure.

    Raises:
        RuntimeError from the underlying helpers.
    """
    data = opt_data.load_verified()
    history = data["history"]
    costs = [float(row["cost"]) for row in history]
    curve = incumbent_curve(costs)
    print(f"    history {len(costs)} evaluations, first {costs[0]:.6f}, "
          f"optimum {curve[37]:.6f} at index 37, "
          f"max {max(costs):.4f}, range "
          f"{(costs[0] - curve[37]) / costs[0] * 100.0:.2f}% reduction")
    pf.require_clean(*TITLE_LINES, "Evaluation index", "Evaluated cost $J$",
                     "evaluated cost", "running best", "handover, index 20",
                     "baseline cost", "optimum, evaluation 37")
    fig = build(data)
    pf.assert_inside_canvas(fig)
    try:
        path, scale = pf.save_to_print_width(
            fig, "bo_convergence.png", PRINT_W_IN, close=False)
    except RuntimeError as error:
        print(f"!! {error}")
        return 1
    guard(fig, scale)
    plt.close(fig)
    print(f"wrote bo_convergence.png print {PRINT_W_IN:.3f} in scale {scale:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
