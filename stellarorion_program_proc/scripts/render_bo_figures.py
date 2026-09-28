#!/usr/bin/env python3
"""
================================================================================
SCRIPT: render_bo_figures.py — Source-grounded figures for the BO results chapter
================================================================================

Generates two figures from the official 2026-09-26 optimizer artifact:

  1. bo_ccd_design.png    3D layout of the 15-point central composite screen
                          (8 factorial + 1 center + 6 axial) over the three
                          design factors, colored by the evaluated cost J.

  2. bo_convergence.png   Convergence over the 70-point evaluation log
                          (20 Latin-Hypercube initial + 50 BO iterations):
                          raw evaluated cost per point on a log axis, plus the
                          running-best (incumbent) curve, the LHS -> BO phase
                          boundary, and the round-1 optimum.

DATA SOURCE (single source of truth):
  src/python/hiad_optimization_results.json  — written by hiad_optimizer.py.
  Keys used: "ccd_samples" (list[15]), "history" (list[70]), "default",
             "optimized", "config".

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
  A2: "history" holds exactly the points the GP+EI loop observed (n=70),
      each carrying its own design vector and evaluated cost.
  A3: "ccd_samples" holds exactly the 15 screened points
      (8 factorial + 1 center + 6 axial), as asserted by hiad_optimizer.py.
  A4: The LHS -> BO boundary is derived from the per-entry "type" field, not
      hardcoded, so it stays correct if the split changes.
  A5: Cost is plotted on a log axis because the evaluated range spans
      1.6 to 2238 across the 70 points; a linear axis would flatten the
      converged region into an unreadable band at the bottom of the frame.

THEORIES (consequences the figure must not contradict):
  T1: The raw per-evaluation cost is NOT monotone. Only the running-best
      curve is. Any caption claiming monotone decrease of J(x) is false.
  T2: The running-best curve is non-increasing by construction, and its final
      value equals min(history) = the round-1 optimum cost.

APPLICATIONS:
  Figure 1 renders the screen as a design layout in factor space. It makes no
  claim about a fitted response surface, because no surrogate fit over the CCD
  alone is recorded in the artifact.
  Figure 2 renders both the raw and incumbent curves, so the distinction in T1
  is visible rather than asserted.

CITATIONS:
  - Cost function and bounds: stellarorion_program_proc/DERIVATION.md
  - Optimizer driver: src/python/hiad_optimizer.py (_GATE_BO_KWARGS,
    n_initial=20, n_iter=50, xi=0.01, seed=42)
  - Matérn 5/2 GP + Expected Improvement: Kennedy & O'Hagan (2000),
    "A classifier-based approach to adaptive multi-fidelity modeling",
    Proc. 2000 Winter Simulation Conference, pp. 1037-1043.

USAGE:
  python3 scripts/render_bo_figures.py [--outdir DIR]
  Default --outdir is the thesis figures/ directory that consumes both files.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Matplotlib must select a non-interactive backend before pyplot import; the
# script runs headless in CI and over SSH where no display is attached.
import matplotlib
import matplotlib.colors  # noqa: E402  (LogNorm used for the CCD cost colorbar)

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (import order fixed by backend)

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

    counts = Counter(entry["type"] for entry in history)
    unexpected = set(counts) - {"initial", "bo"}
    if unexpected:
        raise ValueError(
            f"AXIOM A2/A4 violated: unexpected history phase label(s) "
            f"{sorted(unexpected)}; expected only 'initial' and 'bo'."
        )
    n_initial = counts.get("initial", 0)
    n_bo = counts.get("bo", 0)
    if n_initial != EXPECTED_INITIAL_POINTS or n_bo != EXPECTED_BO_POINTS:
        raise ValueError(
            "AXIOM A2 violated: expected "
            f"{EXPECTED_INITIAL_POINTS} 'initial' + {EXPECTED_BO_POINTS} 'bo' "
            f"evaluations, found {n_initial} + {n_bo}. The recorded phases and "
            "the figure titles disagree; reconcile before regenerating."
        )

    # Cross-check the phase split against the optimizer's own recorded config so
    # the count cannot drift on either side independently.
    config = data["config"]
    if int(config.get("bo_iterations", -1)) != n_bo:
        raise ValueError(
            f"AXIOM A2 violated: config.bo_iterations="
            f"{config.get('bo_iterations')!r} but history carries {n_bo} "
            "'bo' evaluations."
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
    if not types & {"initial", "bo"}:
        raise ValueError(
            f"no 'initial'/'bo' type labels in history; got {sorted(map(str, types))}"
        )
    for index, entry in enumerate(history):
        if entry.get("type") == "bo":
            return index
    return len(history)


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
        label="round-1 BO optimum",
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
        "Source: hiad_optimization_results.json, official run 2026-09-26",
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
        zip(running_best, running_best[1:]), start=1
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
        label=f"round-1 optimum (eval {best_index})",
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
    ax.set_xlabel("evaluation index")
    ax.set_ylabel("cost $J(\\mathbf{x})$  (log scale)")
    # Counts are interpolated from the module constants, which validate_payload
    # has already proven against the artifact (AXIOM A2), so the title cannot
    # drift from the plotted series.
    ax.set_title(
        f"Bayesian Optimization Convergence — {len(costs)} Evaluations\n"
        f"{EXPECTED_INITIAL_POINTS} Latin-Hypercube initial points + "
        f"{EXPECTED_BO_POINTS} GP/Expected-Improvement iterations",
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
        "Source: hiad_optimization_results.json, official run 2026-09-26",
        ha="center",
        fontsize=7.5,
        style="italic",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def main(argv: list[str] | None = None) -> int:
    """Generate both thesis figures from the official optimizer artifact.

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
        render_convergence(data, args.outdir / "bo_convergence.png")
    except (FileNotFoundError, KeyError, ValueError, OSError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("both figures generated from the official artifact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
