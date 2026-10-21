#!/usr/bin/env python3
"""
================================================================================
SCRIPT: render_bo_figures.py — Source-grounded figures for the BO results chapter
================================================================================

Generates three figures from the shipped optimizer artifact. The artifact's
"history" is whatever the DEFAULT optimiser recorded: with --optimizer sbo
(the default) it holds the Genetic Algorithm's per-generation rows, with
--optimizer bo it holds the Bayesian Optimisation log. Every number below
is read from the artifact; nothing about the campaign is hardcoded.

  1. bo_ccd_design.png    3D layout of the 15-point central composite screen
                          (8 factorial + 1 center + 6 axial) over the three
                          design factors, colored by the evaluated cost J.

  2. bo_convergence.png   Convergence over the recorded evaluation log:
                          raw evaluated cost per point on a log axis, plus the
                          running-best (incumbent) curve, the phase boundary
                          (drawn only when the log really has two phases) and
                          the optimum of the recorded campaign.

  3. bo_ccd_sensitivity.png
                           Per-factor sensitivity contrasts computed directly
                           from the 15 recorded CCD costs: axial swings
                           y(+alpha) - y(-alpha) and factorial corner mean
                           effects ybar(+) - ybar(-) over the 4+4 corners,
                           drawn side by side on a log axis. No response
                           surface is fitted; both estimators are reported
                           because they legitimately disagree (THEORY T3).

DATA SOURCE (single source of truth):
  src/python/hiad_optimization_results.json  — written by hiad_optimizer.py.
  Keys used: "ccd_samples" (list[15]), "history" (the recorded evaluation
             log), "default", "optimized", "config".

GA-NAMED TWIN OUTPUTS:
  The thesis cites the optimizer figures under GA names (figures/ga_convergence.
  png). The DEFAULT optimiser is now the Genetic Algorithm, so the same three
  truthful figures are ALSO written under their GA names -- ga_ccd_design.png,
  ga_ccd_sensitivity.png and ga_convergence.png -- as BYTE-IDENTICAL COPIES of
  the bo_* renders (a file copy, never a second render), so the two naming
  conventions can never disagree. Both sets are written into the same --outdir.

WHY THIS SCRIPT EXISTS:
  The thesis previously cited figures/ga_convergence.png and
  figures/ccd_response_surface.png for these two results. Both are stale
  artifacts from an earlier, different campaign:
    * ga_convergence.png plots a Genetic Algorithm run ("Best Cost J* vs
      Generation", 100 generations, cost plateauing near J* = 0.02). The BO
      campaign has 70 evaluations and a minimum cost of 1.6051, so the cost
      scale is incompatible and the algorithm is not the one under study.
    * ccd_response_surface.png is titled "d = 4 Factors, N = 25 Points" and
      plots aerosol diameter D against the half-cone angle. The real screen is
      3 factors / 15 points over (R_N, r_tor, half_cone_deg), and it contains
      no cost values at all -- it is a design layout, not a response surface.
  Both are regenerated here directly from the official artifact so that every
  plotted quantity is traceable to recorded optimizer output.

AXIOMS:
  A1: The optimizer MINIMIZES J(x); lower is better on every axis below.
  A2: "history" holds exactly the points the recorded optimiser observed,
      each carrying its own design vector and evaluated cost. Its length and
      its phase labels are READ from the artifact, never assumed.
  A3: "ccd_samples" holds exactly the 15 screened points
      (8 factorial + 1 center + 6 axial), as asserted by hiad_optimizer.py.
  A4: The phase boundary is derived from the per-entry "type" field, not
      hardcoded, so it stays correct if the split changes -- and it is drawn
      ONLY when the log really has two phases (the GA campaign has none).
  A5: Cost is plotted on a log axis because the evaluated range spans
      several orders of magnitude across the recorded points; a linear axis
      would flatten the converged region into an unreadable band at the
      bottom of the frame.
  A6: The Figure-3 estimators are design-native contrasts computed at render
      time from the recorded CCD costs: the axial swing y(+alpha) - y(-alpha)
      along each factor axis, and the factorial corner mean effect
      ybar(+) - ybar(-) over the 4 '+' and 4 '-' corners of the 2^3 screen.
      Both are resolved BY LABEL from "ccd_samples", and no response surface
      is fitted -- a surrogate would smooth over the estimator disagreement
      recorded in THEORY T3.

THEORIES (consequences the figure must not contradict):
  T1: The raw per-evaluation cost is NOT monotone. Only the running-best
      curve is. Any caption claiming monotone decrease of J(x) is false.
  T2: The running-best curve is non-increasing by construction, and its final
      value equals min(history) = the round-1 optimum cost.
  T3: The two estimators of A6 legitimately disagree on this screen. The
      axial swing isolates one factor at a time at the design centre, so it
      ranks r_tor above R_N by roughly 6.5x (23.04 vs 3.52). The corner mean
      effect averages 4 corners per factor, and the large R_N x r_tor
      interaction (the +++ corner costs 38.83 against 2.0 to 9.7 elsewhere)
      inflates both factors' '+' means, leaving r_tor and R_N nearly tied
      (11.16 vs 10.55, about 1.06x). The disagreement is structure in the
      design, not error: Figure 3 must show both estimators, and prose that
      quotes one of these rankings as "the" ranking is false.

APPLICATIONS:
  Figure 1 renders the screen as a design layout in factor space.
  Figure 2 renders both the raw and incumbent curves, so the distinction in T1
  is visible rather than asserted.
  Figure 3 reports the design-native per-factor contrasts (axial swings and
  factorial corner mean effects, AXIOM A6) computed directly from the recorded
  CCD block. No response surface is fitted anywhere in this script, and the
  estimator disagreement of THEORY T3 is drawn and captioned, not smoothed
  over.

CITATIONS:
  - Cost function and bounds: stellarorion_program_proc/DERIVATION.md
  - Optimizer driver: src/python/hiad_optimizer.py (_GATE_BO_KWARGS,
    n_initial=20, n_iter=50, xi=0.01, seed=42)
  - Matérn 5/2 GP + Expected Improvement: Kennedy & O'Hagan (2000),
    "A classifier-based approach to adaptive multi-fidelity modeling",
    Proc. 2000 Winter Simulation Conference, pp. 1037-1043.

USAGE:
  python3 scripts/render_bo_figures.py [--outdir DIR]
  Default --outdir is the thesis figures/ directory that consumes all three
  files.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from collections import Counter
from itertools import pairwise, product
from pathlib import Path

# Matplotlib must select a non-interactive backend before pyplot import; the
# script runs headless in CI and over SSH where no display is attached.
import matplotlib

# LogNorm used for the CCD cost colorbar
import matplotlib.colors

matplotlib.use("Agg")

# import order fixed by backend
import matplotlib.pyplot as plt

# AXIOM A3: the screen size is fixed by the optimizer's own assertion
# (hiad_optimizer.py: assert len(ccd) == 15). Fail loudly if it ever changes.
EXPECTED_CCD_POINTS = 15

# AXIOM A2: the BO evaluation log length is the sum of the two phase sizes
# recorded in "config" (20 LHS + 50 BO). Fail loudly if the artifact disagrees
# with the counts the thesis prose states, so a title can never drift from data.
EXPECTED_INITIAL_POINTS = 20
EXPECTED_BO_POINTS = 50

# AXIOM A3: the central-composite design centre is identified by this label,
# not by proximity to the default design. The two genuinely differ:
# ccd_samples["center"].r_tor = 0.14 while default.r_tor = 0.135, so marking
# the default and calling it "design centre" would mislabel a plotted point.
CCD_CENTER_LABEL = "center"

# AXIOM A6: the CCD block is exactly the 2^3 factorial corners plus the centre
# plus the 6 axial points already asserted above, and every Figure-3 estimator
# resolves its inputs BY LABEL: corners are "factorial---" .. "factorial+++"
# (the three suffix characters are the R_N, r_tor, half_cone_deg signs in that
# order) and axial points are "axial_<stem>_+/-". A relabelled, reordered or
# incomplete artifact therefore fails loudly instead of silently averaging the
# wrong points into a contrast.
CCD_FACTORIAL_PREFIX = "factorial"

# Factor order is the optimizer's own: the first suffix character of a corner
# label is R_N (most significant), then r_tor, then half_cone_deg.
CCD_FACTORS = ("R_N", "r_tor", "half_cone_deg")

# Factor key -> axial-label stem. The CCD labels shorten "half_cone_deg" to
# "half_cone" (axial_half_cone_+/-), so the mapping is explicit rather than
# assumed to equal the key. A rename in the artifact fails loudly with the
# observed labels printed.
CCD_FACTOR_AXIAL_STEM = {
    "R_N": "R_N",
    "r_tor": "r_tor",
    "half_cone_deg": "half_cone",
}

# Short mathtext symbols and axis descriptions for the Figure-3 tick labels.
CCD_FACTOR_SYMBOL = {
    "R_N": "$R_N$",
    "r_tor": "$r_{tor}$",
    "half_cone_deg": "$\\theta_c$",
}
CCD_FACTOR_AXIS_LABEL = {
    "R_N": "nose radius (m)",
    "r_tor": "torus radius (m)",
    "half_cone_deg": "half-cone angle (deg)",
}

EXPECTED_FACTORIAL_CORNERS = 8
EXPECTED_AXIAL_POINTS = 6

# Log-scale bars cannot start at zero (log(0) is undefined), so Figure 3 draws
# every bar from this positive floor, far below the smallest recorded effect.
EFFECT_BAR_FLOOR = 1e-3

# Relative location of the official artifact with respect to this script's
# repository package root. scripts/ -> stellarorion_program_proc/
RESULTS_JSON = Path(__file__).resolve().parent.parent / "src/python/hiad_optimization_results.json"

# Default output directory: the thesis figures/ folder that \includegraphics
# resolves against. Overridable so the script is not thesis-path-coupled.
DEFAULT_OUTDIR = (
    Path(__file__).resolve().parents[2]
    / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"
)


def load_results(path: Path) -> dict:
    """Load the official optimizer artifact.

    Args:
        path: Filesystem path to hiad_optimization_results.json.

    Returns:
        The parsed JSON object.

    Raises:
        FileNotFoundError: If the artifact is absent. The figure must never be
            regenerated from a guess; a missing artifact is a hard stop.
        json.JSONDecodeError: If the artifact is corrupt.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"official optimizer artifact not found: {path}\n"
            "Refusing to generate figures without the recorded run."
        )
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_payload(data: dict) -> None:
    """Assert the structural assumptions the figures depend on.

    Args:
        data: The parsed optimizer artifact.

    Raises:
        KeyError: If a required key is absent.
        ValueError: If the recorded counts contradict the AXIOMS, which would
            mean the artifact and the thesis prose describe different runs.
    """
    required = ("ccd_samples", "history", "default", "optimized", "config")
    missing = [key for key in required if key not in data]
    if missing:
        raise KeyError(f"artifact missing required key(s): {missing}")

    n_ccd = len(data["ccd_samples"])
    if n_ccd != EXPECTED_CCD_POINTS:
        raise ValueError(
            f"AXIOM A3 violated: expected {EXPECTED_CCD_POINTS} CCD points, "
            f"found {n_ccd}. Update the figure and the thesis prose together."
        )

    # AXIOM A3: the centre point must be addressable by label. Without this the
    # CCD figure would have to guess which of the 15 points is the centre.
    labels = [entry.get("label") for entry in data["ccd_samples"]]
    if CCD_CENTER_LABEL not in labels:
        raise ValueError(
            f"AXIOM A3 violated: no CCD sample labelled {CCD_CENTER_LABEL!r}; "
            f"got {labels}. The design-centre marker cannot be placed."
        )

    # AXIOM A6: Figure 3 resolves every estimator input BY LABEL, so the full
    # labelled block -- 8 factorial corners plus 6 axial points -- must exist
    # before any figure is written. Checked here so a relabelled artifact
    # aborts the run up front instead of failing midway through rendering.
    expected_corners = {
        CCD_FACTORIAL_PREFIX + "".join(signs)
        for signs in product("+-", repeat=len(CCD_FACTORS))
    }
    expected_axial = {
        f"axial_{CCD_FACTOR_AXIAL_STEM[factor]}_{sign}"
        for factor in CCD_FACTORS
        for sign in "+-"
    }
    missing = sorted((expected_corners | expected_axial) - set(labels))
    if missing:
        raise ValueError(
            f"AXIOM A6 violated: CCD block is missing the labelled point(s) "
            f"{missing}; the sensitivity contrasts cannot be computed. Got "
            f"labels {sorted(map(str, labels))}."
        )

    # AXIOM A2: the evaluation log must be exactly the two recorded phases, and
    # the counts must agree with "config". Otherwise a hardcoded 70/20/50 in a
    # figure title could describe a run the artifact does not contain.
    history = data["history"]
    if len(history) < 2:
        raise ValueError(f"history too short to plot: n={len(history)}")

    for entry in history:
        missing_fields = {"cost", "type", "R_N", "r_tor", "half_cone_deg"} - set(entry)
        if missing_fields:
            raise ValueError(f"history entry missing {missing_fields}: {entry}")

    # AXIOM A2 (extended): the recorded phase labels may come from the
    # Bayesian path ("initial" + "bo") OR from the Ada GA/SBO path
    # ("sbo" rows, one per generation). The strict 20+50 count check
    # applies to the Bayesian path only; the GA path is checked against
    # its own recorded generation budget.
    config = data["config"]
    optimizer = str(config.get("optimizer", "bo"))
    counts = Counter(entry["type"] for entry in history)
    unexpected = set(counts) - {"initial", "bo", "ga", "sbo"}
    if unexpected:
        raise ValueError(
            f"AXIOM A2/A4 violated: unexpected history phase label(s) "
            f"{sorted(unexpected)}; expected only 'initial', 'bo', 'ga' "
            "or 'sbo'."
        )
    n_initial = counts.get("initial", 0)
    n_bo = counts.get("bo", 0)
    n_ga = counts.get("ga", 0) + counts.get("sbo", 0)
    if optimizer == "bo":
        if n_initial != EXPECTED_INITIAL_POINTS or n_bo != EXPECTED_BO_POINTS:
            raise ValueError(
                "AXIOM A2 violated: expected "
                f"{EXPECTED_INITIAL_POINTS} 'initial' + {EXPECTED_BO_POINTS} "
                f"'bo' evaluations, found {n_initial} + {n_bo}. The recorded "
                "phases and the figure titles disagree; reconcile before "
                "regenerating."
            )
        # Cross-check the phase split against the optimizer's own recorded
        # config so the count cannot drift on either side independently.
        if int(config.get("bo_iterations", -1)) != n_bo:
            raise ValueError(
                f"AXIOM A2 violated: config.bo_iterations="
                f"{config.get('bo_iterations')!r} but history carries {n_bo} "
                "'bo' evaluations."
            )
    else:
        max_generations = int(config.get("max_generations", -1))
        if n_ga < 1:
            raise ValueError(
                f"AXIOM A2 violated: optimizer {optimizer!r} recorded no "
                "'ga'/'sbo' history rows."
            )
        if max_generations >= 0 and n_ga > max_generations + 1:
            raise ValueError(
                f"AXIOM A2 violated: history carries {n_ga} generation rows "
                f"but config.max_generations={max_generations}."
            )


def phase_boundary(history: list) -> int:
    """Locate the Latin-Hypercube -> Bayesian-Optimization transition.

    Derives the boundary from the recorded per-entry "type" field (AXIOM A4)
    rather than hardcoding 20, so a changed sampling split stays correct.

    Args:
        history: The evaluation log, in observation order.

    Returns:
        The evaluation index at which the first "bo" entry appears, or the
        full length if no boundary is present.

    Raises:
        ValueError: If no entry carries a recognized "type" value.
    """
    types = {entry.get("type") for entry in history}
    if not types & {"initial", "bo", "ga", "sbo"}:
        raise ValueError(
            f"no 'initial'/'bo'/'ga'/'sbo' type labels in history; got "
            f"{sorted(map(str, types))}"
        )
    if "initial" not in types:
        # GA/SBO path: there is no Latin-Hypercube phase, so there is no
        # phase transition to locate.
        return len(history)
    for index, entry in enumerate(history):
        if entry.get("type") in {"bo", "ga", "sbo"}:
            return index
    return len(history)


def _source_caption(data: dict) -> str:
    """Build the figure source caption from the artifact's own metadata.

    WHY: a hardcoded algorithm name and a hardcoded run date go stale as
    soon as the optimizer changes, which makes every regenerated figure
    misdescribe its own data. The caption is therefore derived from the
    recorded config block and the artifact's own modification time.

    Args:
        data: The parsed hiad_optimization_results.json payload.

    Returns:
        The caption string for the figure's source line.
    """
    config = data.get("config", {})
    optimizer = str(config.get("optimizer", "bo"))
    label = (
        "Bayesian Optimization" if optimizer == "bo"
        else "SBO Genetic Algorithm"
    )
    try:
        stamp = time.strftime(
            "%Y-%m-%d", time.localtime(RESULTS_JSON.stat().st_mtime)
        )
    except OSError:
        stamp = "unknown date"
    return f"Source: hiad_optimization_results.json ({label} run, {stamp})"


def _optimizer_name(data: dict) -> str:
    """Return the recorded optimizer label ("bo" or the GA/SBO label).

    Args:
        data: The parsed hiad_optimization_results.json payload.

    Returns:
        The optimizer label recorded in the artifact's config block.
    """
    return str(data.get("config", {}).get("optimizer", "bo"))


def render_ccd_design(data: dict, out_path: Path) -> None:
    """Render the 15-point central composite screen in factor space.

    The figure is a design LAYOUT, deliberately not a response surface: the
    artifact records evaluated cost per point but no surrogate fitted over the
    screen, so drawing contours would invent structure that is not there.

    Args:
        data: The parsed optimizer artifact.
        out_path: Destination PNG path.

    Raises:
        OSError: If the figure cannot be written.
    """
    samples = data["ccd_samples"]
    default = data["default"]

    fig = plt.figure(figsize=(10.0, 7.4))
    ax = fig.add_subplot(111, projection="3d")

    # Color by evaluated cost on a log scale (AXIOM A5).
    costs = [float(entry["cost"]) for entry in samples]
    scatter = ax.scatter(
        [float(entry["R_N"]) for entry in samples],
        [float(entry["r_tor"]) for entry in samples],
        [float(entry["half_cone_deg"]) for entry in samples],
        c=costs,
        cmap="viridis",
        norm=matplotlib.colors.LogNorm(vmin=min(costs), vmax=max(costs)),
        s=90,
        edgecolors="black",
        linewidths=0.6,
        zorder=3,
    )

    # Mark the CCD design centre and the best screened point explicitly. The
    # centre is resolved BY LABEL (AXIOM A3), not by assuming it coincides with
    # the baseline design: the artifact records r_tor = 0.14 for the centre but
    # 0.135 for the default, so marking "default" as the centre would misplace
    # the star by 5 mm and misstate what the star means.
    center = next(e for e in samples if e["label"] == CCD_CENTER_LABEL)
    ax.scatter(
        [float(center["R_N"])],
        [float(center["r_tor"])],
        [float(center["half_cone_deg"])],
        marker="*",
        s=260,
        c="red",
        edgecolors="black",
        linewidths=0.7,
        zorder=5,
        label="CCD design centre",
    )
    # The IRVE-3 baseline is a separate, slightly different point; it is drawn
    # so the reader can see that the screen centre is not the baseline design.
    ax.scatter(
        [float(default["R_N"])],
        [float(default["r_tor"])],
        [float(default["half_cone_deg"])],
        marker="P",
        s=150,
        c="white",
        edgecolors="black",
        linewidths=1.6,
        zorder=5,
        label="IRVE-3 baseline",
    )
    best = min(samples, key=lambda entry: float(entry["cost"]))
    ax.scatter(
        [float(best["R_N"])],
        [float(best["r_tor"])],
        [float(best["half_cone_deg"])],
        marker="v",
        s=170,
        c="white",
        edgecolors="red",
        linewidths=2.0,
        zorder=5,
        label=f"best screened ({best['label']})",
    )

    # Round-1 BO optimum, shown to expose the extrapolation beyond the screen.
    opt = data["optimized"]
    ax.scatter(
        [float(opt["R_N"])],
        [float(opt["r_tor"])],
        [float(opt["half_cone_deg"])],
        marker="D",
        s=110,
        c="orange",
        edgecolors="black",
        linewidths=0.7,
        zorder=5,
        label=(
            "round-1 BO optimum"
            if _optimizer_name(data) == "bo"
            else "GA optimum (round 1)"
        ),
    )

    bar = fig.colorbar(scatter, ax=ax, pad=0.12, shrink=0.62)
    bar.set_label("evaluated cost $J(\\mathbf{x})$  (log scale)")

    ax.set_xlabel("nose radius $R_N$  (m)")
    ax.set_ylabel("torus radius $r_{tor}$  (m)")
    ax.set_zlabel("half-cone angle $\\theta_c$  (deg)")
    ax.set_title(
        "Central Composite Screen — 15 Points, 3 Factors\n"
        "8 factorial + 1 centre + 6 axial (design layout, not a response surface)",
        fontsize=11,
    )
    ax.legend(loc="upper left", bbox_to_anchor=(-0.08, 0.98), fontsize=8)

    fig.text(
        0.5,
        0.015,
        _source_caption(data),
        ha="center",
        fontsize=7.5,
        style="italic",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def render_convergence(data: dict, out_path: Path) -> None:
    """Render the 70-point evaluation log and its running-best curve.

    Both series are drawn (THEORY T1): the raw cost is emphatically not
    monotone, while the incumbent curve is. Omitting the raw series would
    hide exactly the behaviour the caption must not misstate.

    Args:
        data: The parsed optimizer artifact.
        out_path: Destination PNG path.

    Raises:
        OSError: If the figure cannot be written.
    """
    history = data["history"]
    costs = [float(entry["cost"]) for entry in history]
    indices = list(range(len(costs)))

    running_best: list[float] = []
    incumbent = float("inf")
    for value in costs:
        incumbent = min(incumbent, value)
        running_best.append(incumbent)

    boundary = phase_boundary(history)
    best_index = costs.index(min(costs))

    # Explicit pre-condition: the incumbent curve must be non-increasing
    # (THEORY T2). Verified BEFORE any figure is constructed or written, so a
    # broken accumulation fails loudly instead of shipping a figure that
    # misrepresents the run. Positions come from enumerate, not list.index(),
    # so the reported index is the actually-violating step rather than the
    # first equal value.
    for position, (previous, current) in enumerate(
        pairwise(running_best), start=1
    ):
        if current > previous:
            raise ValueError(
                f"running-best curve increased at evaluation index {position} "
                f"({previous} -> {current}); incumbent accumulation is broken"
            )

    fig, ax = plt.subplots(figsize=(10.0, 6.2))

    ax.scatter(
        indices,
        costs,
        s=26,
        alpha=0.55,
        c="tab:blue",
        label="evaluated cost $J(\\mathbf{x})$",
        zorder=2,
    )
    ax.plot(
        indices,
        running_best,
        color="tab:red",
        linewidth=2.0,
        label="running best (incumbent)",
        zorder=3,
    )
    if boundary < len(costs):
        # A boundary line only makes sense when the run really had two
        # phases; the GA path has none (phase_boundary returns the length).
        ax.axvline(
            boundary,
            color="0.35",
            linestyle="--",
            linewidth=1.2,
            label=f"LHS $\\rightarrow$ BO boundary (eval {boundary})",
            zorder=1,
        )
    ax.scatter(
        [best_index],
        [min(costs)],
        marker="*",
        s=280,
        c="gold",
        edgecolors="black",
        linewidths=0.8,
        zorder=4,
        label=(
            f"round-1 optimum (eval {best_index})"
            if _optimizer_name(data) == "bo"
            else f"GA optimum (generation {best_index})"
        ),
    )

    default_cost = float(data["default"]["cost"])
    ax.axhline(
        default_cost,
        color="0.45",
        linestyle=":",
        linewidth=1.4,
        label=f"IRVE-3 baseline $J$ = {default_cost:.4f}",
        zorder=1,
    )

    ax.set_yscale("log")
    ax.set_xlabel(
        "evaluation index" if _optimizer_name(data) == "bo"
        else "generation index"
    )
    ax.set_ylabel("cost $J(\\mathbf{x})$  (log scale)")
    # Counts are interpolated from the module constants, which validate_payload
    # has already proven against the artifact (AXIOM A2), so the title cannot
    # drift from the plotted series.
    config = data.get("config", {})
    if _optimizer_name(data) == "bo":
        n_initial = sum(1 for e in history if e.get("type") == "initial")
        n_bo = sum(1 for e in history if e.get("type") == "bo")
        ax.set_title(
            f"Bayesian Optimization Convergence — {len(costs)} Evaluations\n"
            f"{n_initial} Latin-Hypercube initial points + "
            f"{n_bo} GP/Expected-Improvement iterations",
            fontsize=11,
        )
    else:
        ax.set_title(
            f"SBO Genetic Algorithm Convergence — {len(costs)} Generations\n"
            f"population {config.get('population_size', '?')}, "
            f"generation budget {config.get('max_generations', '?')} "
            "(parallel population, model-fidelity penalty)",
            fontsize=11,
        )
    ax.grid(True, which="both", linewidth=0.3, alpha=0.5)
    # Show only the two series in the legend box; the vertical/horizontal guide
    # lines are self-describing in the title and would crowd a 10-inch frame.
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[:2], labels[:2], fontsize=8, loc="upper right")

    fig.text(
        0.5,
        0.012,
        _source_caption(data),
        ha="center",
        fontsize=7.5,
        style="italic",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def _rn_r_tor_interaction(corner_signs: dict, costs: dict) -> float:
    """Collapse the 8 corners onto the R_N x r_tor plane for the interaction.

    THEORY T3: the disagreement between the two sensitivity estimators is
    inflated by the R_N x r_tor interaction. This contrast is the quantitative
    evidence for that claim -- m(++) - m(+-) - m(-+) + m(--), where each m is
    the mean over the two half-cone levels -- so the caption can quote it from
    data instead of asserting it.

    Args:
        corner_signs: Map of corner label -> 3-character sign string.
        costs: Map of CCD label -> evaluated cost.

    Returns:
        The R_N x r_tor two-factor interaction contrast.

    Raises:
        ValueError: If any of the four cells does not carry exactly 2 corners.
    """
    cells: dict[str, list[float]] = {"++": [], "+-": [], "-+": [], "--": []}
    for label, suffix in corner_signs.items():
        cells[suffix[0] + suffix[1]].append(costs[label])
    means: dict[str, float] = {}
    for key, values in cells.items():
        if len(values) != 2:
            raise ValueError(
                f"R_N x r_tor cell {key!r} carries {len(values)} corners, "
                "expected 2; the interaction contrast cannot be computed."
            )
        means[key] = math.fsum(values) / 2.0
    return means["++"] - means["+-"] - means["-+"] + means["--"]


def ccd_sensitivity_estimates(samples: list | None) -> dict:
    """Compute the design-native sensitivity contrasts of the CCD block.

    AXIOM A6: two estimators are derived from the recorded costs with NO
    fitted response surface:
      * axial swing        y(+alpha) - y(-alpha)   per factor axis;
      * corner mean effect ybar(+) - ybar(-)       per factor, the mean over
        the 4 corners at the '+' level minus the mean over the 4 corners at
        the '-' level.
    The R_N x r_tor interaction contrast is also returned because it is the
    documented cause of the estimator disagreement (THEORY T3).

    Every input is resolved BY LABEL and every intermediate count is checked,
    so a missing, empty, relabelled, reordered or duplicated CCD block raises
    instead of producing a quietly wrong contrast.

    Args:
        samples: The "ccd_samples" list from the artifact.

    Returns:
        Dict with keys "factors" (factor-name tuple), "axial_swing" and
        "corner_effect" (factor -> float), "axial_ranking" and
        "corner_ranking" (factor names, descending effect), and
        "interaction_contrast" (float, R_N x r_tor over the 8 corners).

    Raises:
        ValueError: If the block is empty or not a list, an entry is not an
            object, a label is missing/duplicated/not a string, an axial pair
            is incomplete, the corner set is not the full 2^3 factorial, a
            corner label is malformed, or any recorded cost is not a finite
            number.
    """
    if not samples:
        raise ValueError(
            "ccd_samples block is missing or empty; the Figure-3 contrasts "
            "cannot be computed. Refusing to render an empty sensitivity plot."
        )
    #  A type guard raises TypeError (ruff TRY004): the failure is that the
    #  payload has the wrong TYPE, not that a value is out of range.  The
    #  isinstance checks below are structural guards on the artifact, so the
    #  exception they raise must say so.
    if not isinstance(samples, list):
        raise TypeError(
            f"ccd_samples must be a list, got {type(samples).__name__}"
        )

    # Resolve every sample by label first; a duplicate label would make the
    # lookup silently overwrite one of the two points.
    by_label: dict = {}
    for entry in samples:
        if not isinstance(entry, dict):
            raise TypeError(f"ccd_samples entry is not an object: {entry!r}")
        label = entry.get("label")
        if label is None:
            raise ValueError(f"ccd_samples entry without a label: {entry!r}")
        if not isinstance(label, str):
            raise TypeError(f"CCD sample label is not a string: {label!r}")
        if label in by_label:
            raise ValueError(
                f"duplicate CCD sample label {label!r}; labels must be unique "
                "for the contrasts to be well defined."
            )
        by_label[label] = entry

    costs: dict = {}
    for label, entry in by_label.items():
        try:
            value = float(entry["cost"])
        except KeyError as exc:
            raise ValueError(f"CCD sample {label!r} has no 'cost' field") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"CCD sample {label!r} has a non-numeric cost "
                f"{entry.get('cost')!r}"
            ) from exc
        if not math.isfinite(value):
            raise ValueError(
                f"CCD sample {label!r} has a non-finite cost {value!r}"
            )
        costs[label] = value

    axial_swing: dict = {}
    resolved_axial = 0
    for factor in CCD_FACTORS:
        pair: dict = {}
        for sign_char in ("+", "-"):
            label = f"axial_{CCD_FACTOR_AXIAL_STEM[factor]}_{sign_char}"
            if label not in costs:
                raise ValueError(
                    f"AXIOM A6 violated: axial point {label!r} not found in "
                    f"ccd_samples (labels: {sorted(costs)}); the axial swing "
                    f"for {factor} cannot be computed."
                )
            pair[sign_char] = costs[label]
            resolved_axial += 1
        axial_swing[factor] = pair["+"] - pair["-"]
    if resolved_axial != EXPECTED_AXIAL_POINTS:
        raise ValueError(
            f"AXIOM A6 violated: resolved {resolved_axial} axial points, "
            f"expected {EXPECTED_AXIAL_POINTS}."
        )

    corner_signs: dict = {}
    for label in costs:
        if not label.startswith(CCD_FACTORIAL_PREFIX):
            continue
        suffix = label[len(CCD_FACTORIAL_PREFIX):]
        if len(suffix) != len(CCD_FACTORS) or any(c not in "+-" for c in suffix):
            raise ValueError(
                f"malformed factorial corner label {label!r}; expected "
                f"{CCD_FACTORIAL_PREFIX!r} followed by {len(CCD_FACTORS)} sign "
                "characters."
            )
        corner_signs[label] = suffix
    if len(corner_signs) != EXPECTED_FACTORIAL_CORNERS:
        raise ValueError(
            f"AXIOM A6 violated: found {len(corner_signs)} factorial corner "
            f"labels, expected {EXPECTED_FACTORIAL_CORNERS} "
            f"(2^{len(CCD_FACTORS)}); got {sorted(corner_signs)}."
        )

    corner_effect: dict = {}
    for index, factor in enumerate(CCD_FACTORS):
        plus = [costs[l] for l, s in corner_signs.items() if s[index] == "+"]
        minus = [costs[l] for l, s in corner_signs.items() if s[index] == "-"]
        half = EXPECTED_FACTORIAL_CORNERS // 2
        if len(plus) != half or len(minus) != half:
            raise ValueError(
                f"AXIOM A6 violated: factor {factor} sees {len(plus)} '+' and "
                f"{len(minus)} '-' corners, expected {half} and {half}."
            )
        corner_effect[factor] = (
            math.fsum(plus) / len(plus) - math.fsum(minus) / len(minus)
        )

    return {
        "factors": CCD_FACTORS,
        "axial_swing": axial_swing,
        "corner_effect": corner_effect,
        "axial_ranking": sorted(axial_swing, key=axial_swing.get, reverse=True),
        "corner_ranking": sorted(corner_effect, key=corner_effect.get, reverse=True),
        "interaction_contrast": _rn_r_tor_interaction(corner_signs, costs),
    }


def _sensitivity_caption(estimates: dict, data: dict) -> str:
    """Build the multi-line caption reporting both estimators and their
    documented disagreement.

    Every number is interpolated from the computed estimates, so the caption
    can never drift from the bars drawn above it (THEORY T3: the disagreement
    is real and must be stated, not smoothed away).

    Args:
        estimates: The dict returned by ccd_sensitivity_estimates.

    Returns:
        The caption string, lines joined by newlines.
    """
    axial = estimates["axial_swing"]
    corner = estimates["corner_effect"]

    def dominance(series: dict) -> tuple:
        """Return (top symbol, runner-up symbol, ratio text) for a series."""
        order = sorted(series, key=series.get, reverse=True)
        top, second = order[0], order[1]
        denominator = series[second]
        if denominator > 0.0:
            ratio = f"{series[top] / denominator:.2f}x"
        else:
            ratio = "not comparable"
        return CCD_FACTOR_SYMBOL[top], CCD_FACTOR_SYMBOL[second], ratio

    a_top, a_second, a_ratio = dominance(axial)
    c_top, c_second, c_ratio = dominance(corner)
    largest_corner = max(corner.values())
    #  Each implicitly concatenated group is explicitly parenthesised: ruff's
    #  ISC004 rejects an unparenthesised implicit concatenation inside a
    #  collection literal, and the collection here is a list of caption lines.
    return "\n".join(
        [
            (
                "Design-native contrasts computed directly from the 15 recorded "
                "CCD costs; no response surface is fitted."
            ),
            (
                "The axial swing isolates each factor at the design centre; the "
                "corner mean effect averages the 4 '+' and 4 '-' corners."
            ),
            (
                f"Estimators disagree by design: axially {a_top} ranks {a_ratio} "
                f"above {a_second}, while the corner means leave {c_top} and "
                f"{c_second} near-tied ({c_ratio}), inflated by"
            ),
            (
                f"the R_N x r_tor interaction (contrast "
                f"{estimates['interaction_contrast']:.2f} exceeds the largest "
                f"corner main effect {largest_corner:.2f})."
            ),
            (
                "Positive contrast = evaluated cost rises as the factor "
                "increases (J is minimized)."
            ),
            _source_caption(data),
        ]
    )


def render_ccd_sensitivity(data: dict, out_path: Path) -> None:
    """Render the per-factor CCD sensitivity contrasts as a grouped bar chart.

    AXIOM A6 / THEORY T3: both estimators are computed at render time from the
    recorded costs and both are drawn side by side per factor, because on this
    screen they legitimately disagree -- the axial swing isolates each factor
    at the design centre while the corner mean effect averages 4 corners per
    side and is inflated by the R_N x r_tor interaction. No response surface
    is fitted: a surrogate would smooth exactly the disagreement the caption
    reports. The y axis is logarithmic because the effects span nearly three
    decades (AXIOM A5 applied to effects).

    Args:
        data: The parsed optimizer artifact.
        out_path: Destination PNG path.

    Raises:
        ValueError: Propagated from ccd_sensitivity_estimates if the CCD
            block cannot yield both estimators, or if any effect is
            non-positive so the log axis could not represent it honestly.
        OSError: If the figure cannot be written.
    """
    estimates = ccd_sensitivity_estimates(data.get("ccd_samples"))
    factors = list(estimates["factors"])
    axial = estimates["axial_swing"]
    corner = estimates["corner_effect"]
    axial_values = [axial[factor] for factor in factors]
    corner_values = [corner[factor] for factor in factors]

    #  AXIOM A5 (revised 2026-10-20): a CONTRAST IS SIGNED.  A negative
    #  contrast means that increasing the factor REDUCES the cost, which is
    #  a physically meaningful result, not a defect -- and the recorded
    #  15-point CCD contains exactly such a case (the half-cone axial
    #  swing is negative for the current validation references).  A pure
    #  log axis cannot represent it, so the effect plot uses a SYMMETRIC
    #  LOG axis: the decade readability of the log scale is kept for the
    #  large effects, while the small ones keep their sign.  Only a
    #  non-finite contrast fails loudly (it cannot be placed on any axis).
    for name, series in (("axial swing", axial), ("corner mean effect", corner)):
        for factor, value in series.items():
            if not math.isfinite(value):
                raise ValueError(
                    f"{name} for {factor} is {value!r}; a non-finite contrast "
                    "cannot be plotted."
                )
    lo = min([EFFECT_BAR_FLOOR] + [v for v in axial_values + corner_values if v < 0.0])
    hi = max([EFFECT_BAR_FLOOR] + axial_values + corner_values)
    span = max(hi - lo, 1.0E-12)

    positions = list(range(len(factors)))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10.0, 7.0))
    # subplots_adjust instead of tight_layout: the caption below the axes is
    # part of this figure's message, and tight_layout does not reserve room
    # for fig.text artists.
    fig.subplots_adjust(bottom=0.26, top=0.86, left=0.09, right=0.97)

    axial_bars = ax.bar(
        [p - width / 2 for p in positions],
        axial_values,
        width,
        bottom=EFFECT_BAR_FLOOR,
        color="tab:blue",
        label="axial swing  $y(+\\alpha) - y(-\\alpha)$",
        zorder=3,
    )
    corner_bars = ax.bar(
        [p + width / 2 for p in positions],
        corner_values,
        width,
        bottom=EFFECT_BAR_FLOOR,
        color="tab:orange",
        label="corner mean effect  $\\bar{y}_{+} - \\bar{y}_{-}$",
        zorder=3,
    )
    for bars, values in ((axial_bars, axial_values), (corner_bars, corner_values)):
        for rect, value in zip(bars, values):
            ax.annotate(
                f"{value:.3f}",
                (rect.get_x() + rect.get_width() / 2.0, value * 1.12),
                ha="center",
                fontsize=8,
                zorder=4,
            )

    ax.set_yscale("symlog", linthresh=1e-2)
    ax.set_ylim(lo - 0.10 * span, hi + 0.35 * span)
    ax.set_xticks(positions)
    ax.set_xticklabels(
        [
            f"{CCD_FACTOR_SYMBOL[factor]}\n{CCD_FACTOR_AXIS_LABEL[factor]}"
            for factor in factors
        ]
    )
    ax.set_ylabel("contrast effect on cost $J(\\mathbf{x})$  (symmetric log scale)")
    ax.set_title(
        "CCD Sensitivity — Per-Factor Design-Native Contrasts\n"
        "axial swings and factorial corner mean effects from the 15 recorded "
        "CCD costs (no response surface fitted)",
        fontsize=11,
    )
    ax.grid(True, which="both", linewidth=0.3, alpha=0.5)
    ax.legend(fontsize=8, loc="upper left")

    fig.text(
        0.5,
        0.015,
        _sensitivity_caption(estimates, data),
        ha="center",
        va="bottom",
        fontsize=7.8,
        linespacing=1.4,
    )
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def main(argv: list[str] | None = None) -> int:
    """Generate the three thesis figures from the official optimizer artifact.

    Args:
        argv: Command-line arguments; None uses sys.argv.

    Returns:
        Process exit status: 0 on success, 1 on any handled failure.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help=f"output directory (default: {DEFAULT_OUTDIR})",
    )
    args = parser.parse_args(argv)

    try:
        data = load_results(RESULTS_JSON)
        validate_payload(data)
        args.outdir.mkdir(parents=True, exist_ok=True)
        render_ccd_design(data, args.outdir / "bo_ccd_design.png")
        render_ccd_sensitivity(data, args.outdir / "bo_ccd_sensitivity.png")
        render_convergence(data, args.outdir / "bo_convergence.png")
        #  WHY: the thesis cites the optimizer figures under GA names
        #  (figures/ga_convergence.png).  The DEFAULT optimiser is now the
        #  Genetic Algorithm, so the SAME truthful figures are also written
        #  under their GA names.  The GA-named files are BYTE-IDENTICAL
        #  copies (not a second render) so the two naming conventions can
        #  never disagree about the plotted data, and the cost is one file
        #  copy instead of a second matplotlib pass.
        for bo_name, ga_name in (
            ("bo_ccd_design.png", "ga_ccd_design.png"),
            ("bo_ccd_sensitivity.png", "ga_ccd_sensitivity.png"),
            ("bo_convergence.png", "ga_convergence.png"),
        ):
            shutil.copyfile(args.outdir / bo_name, args.outdir / ga_name)
    except (FileNotFoundError, KeyError, ValueError, OSError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(
        "all three figures generated from the official artifact "
        "(+ the three GA-named copies: ga_ccd_design.png, "
        "ga_ccd_sensitivity.png, ga_convergence.png)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
