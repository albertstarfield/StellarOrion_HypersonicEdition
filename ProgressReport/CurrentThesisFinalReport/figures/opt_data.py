"""Load the optimization campaign results that the thesis text reports.

PURPOSE
    Three figure generators must draw the same campaign: the CCD screen panel,
    the Bayesian convergence panel, and the validation gate panel. Each of them
    needs the identical set of numbers, and each of them must refuse to draw if
    those numbers have drifted away from the values printed in the thesis. This
    module owns that one loader and that one set of assertions so a figure can
    never contradict the text and so the rule exists once.

WHY THE COMMITTED REVISION AND NOT THE FILE ON DISK
    The working tree copy of the results JSON is a dirty, un-gated re-run that
    background automation overwrites repeatedly. The argmin of the history was
    observed to move from index 29 to index 50 within two minutes, with the cost
    changing from 1.602195 to 1.608508. The thesis reports the campaign that the
    DSMC validation gate was actually run against, which is the committed
    revision. Reading the file on disk would therefore make the figures
    contradict the text, and two of the numbers would differ in the first three
    significant figures. The revision is read through git for exactly this
    reason, and it is asserted rather than trusted.

PARAMETERS
    None. The revision and the relative path are module constants.

RETURNS
    load_committed() returns the decoded results dict.
    assert_thesis_claims(data) returns None.

EXCEPTIONS
    RuntimeError if git is unavailable, if the revision does not contain the
    path, if the payload does not decode, if the history does not have 70
    entries, or if any asserted value departs from the thesis. The function
    raises instead of returning a partial result because a partially verified
    campaign would draw a partially verified figure.

CITATIONS
    subprocess.run, Python standard library, https://docs.python.org/3/library/subprocess.html
    git show, Git documentation, https://git-scm.com/docs/git-show

AXIOMS
    A1. The text is the specification. A figure that disagrees with a printed
        sentence is a defect even when the figure is faithful to a file.
    A2. A file that background automation rewrites is a moving target, so the
        only stable reference is a committed revision.
    A3. An assertion that is never run is a comment. The claims below are
        therefore executed on every load.

THEORIES
    T1. Because A1 makes the text authoritative and A2 makes only a commit
        stable, the committed payload plus a claim-by-claim assertion is the
        unique data source that can satisfy both.
    T2. If a claim fails, the correct response is to stop, not to redraw the
        figure from the drifted file, because that would silently move the
        reported result.

APPLICATIONS
    A1. figures/make_bo_ccd_design.py draws the 15-point screen.
    A2. figures/make_bo_convergence.py draws the 70-evaluation history.
    A3. figures/make_fignew.py draws the gate comparison and inherits this
        loader, so all three panels cannot disagree.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# Repository root: this file lives at <thesis>/figures/opt_data.py, so the root
# is five levels up from the figures directory.
ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
OPTJSON_REL = "stellarorion_program_proc/src/python/hiad_optimization_results.json"
OPTJSON_REV = "bdddb47"

# Values printed in chapter 4 of the thesis. Each is asserted below, so a drift
# in the campaign stops the figure instead of silently changing the reported
# result. The tolerances are absolute and tight: the text quotes four
# significant figures, so anything beyond the last quoted digit is a change of
# result, not of rounding.
THESIS_CLAIMS = {
    "q_target": 165.716,          # Table, total heat load target
    "baseline_cost": 2.1626,      # IRVE-3 aggregate cost J
    "optimum_cost": 1.6051,       # round-1 Bayesian optimum
    "optimum_R_N": 2.9714,        # round-1 nose radius, m
    "optimum_r_tor": 0.0885,      # round-1 torus radius, m
    "optimum_half_cone": 40.15,   # round-1 half-cone angle, degrees
    "optimum_Q": 155.67,          # round-1 total heat load, J/cm2
    "optimum_Cd": 1.5597,         # round-1 drag coefficient
    "screen_min": 1.9959,         # lowest central composite screen cost
    "screen_center": 2.1674,      # cost at the design center
    "screen_max": 38.8332,        # most expensive factorial corner
    "first_eval": 1.7654,         # cost at evaluation zero
    "improvement_pct": 9.08,      # incumbent reduction, percent
    "above_baseline": 46,         # evaluations costing more than the baseline
    "history_len": 70,            # evaluated designs
    "ccd_len": 15,                # screened designs
}


def load_committed() -> dict:
    """Return the campaign results exactly as committed, verified against the text.

    Parameters: none.

    Returns:
        dict with the keys validation_refs, default, optimized, improvement,
        ccd_samples, history and config.

    Raises:
        RuntimeError when git fails, the path is absent at that revision, the
        payload is not JSON, the history is not the expected length, or the
        minimum of the history is not the value the thesis reports.
    """
    result = subprocess.run(
        ["git", "show", f"{OPTJSON_REV}:{OPTJSON_REL}"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git show {OPTJSON_REV}:{OPTJSON_REL} failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    history = data["history"]
    costs = [float(row["cost"]) for row in history]
    argmin = min(range(len(costs)), key=lambda i: costs[i])
    optimized = data["optimized"]
    print(f"    [committed {OPTJSON_REV}] argmin idx={argmin} cost={costs[argmin]:.6f} "
          f"R_N={optimized['R_N']:.6f} r_tor={optimized['r_tor']:.6f} "
          f"Q={optimized['total_heat_load_Jcm2']:.4f}")
    if argmin != 37 or abs(costs[argmin] - THESIS_CLAIMS["optimum_cost"]) > 1e-4:
        raise RuntimeError(
            f"committed campaign does not match the thesis: expected the optimum at "
            f"index 37 with cost {THESIS_CLAIMS['optimum_cost']}, got index {argmin} "
            f"with cost {costs[argmin]:.6f}")
    return data


def assert_thesis_claims(data: dict) -> None:
    """Check every campaign number the thesis prints against the payload.

    Parameters:
        data: the dict returned by load_committed.

    Returns:
        None. The function exists for its side effect.

    Raises:
        RuntimeError naming the first claim that fails, with the text value and
        the payload value.
    """
    history = data["history"]
    costs = [float(row["cost"]) for row in history]
    samples = data["ccd_samples"]
    screen = [float(row["cost"]) for row in samples]
    incumbent: list[float] = []
    best = float("inf")
    for value in costs:
        best = min(best, value)
        incumbent.append(best)
    baseline = float(data["default"]["cost"])
    improved_steps = [i for i in range(len(costs) - 1) if incumbent[i] > incumbent[i + 1] + 1e-15]
    above = [i for i, value in enumerate(costs) if value > baseline]
    above_radius = [float(history[i]["R_N"]) for i in above]

    def check(name: str, got: float, expected: float, tol: float) -> None:
        if abs(got - expected) > tol:
            raise RuntimeError(
                f"thesis claim {name} disagrees with the committed campaign: text "
                f"{expected}, payload {got}; refusing to draw a figure that would "
                f"contradict the text")

    check("q_target", float(data["validation_refs"]["q_target_jcm2"]),
          THESIS_CLAIMS["q_target"], 5e-4)
    check("baseline_cost", baseline, THESIS_CLAIMS["baseline_cost"], 5e-5)
    check("optimum_cost", float(data["optimized"]["cost"]),
          THESIS_CLAIMS["optimum_cost"], 5e-5)
    check("optimum_R_N", float(data["optimized"]["R_N"]),
          THESIS_CLAIMS["optimum_R_N"], 5e-5)
    check("optimum_r_tor", float(data["optimized"]["r_tor"]),
          THESIS_CLAIMS["optimum_r_tor"], 5e-5)
    check("optimum_half_cone", float(data["optimized"]["half_cone_deg"]),
          THESIS_CLAIMS["optimum_half_cone"], 5e-3)
    check("optimum_Q", float(data["optimized"]["total_heat_load_Jcm2"]),
          THESIS_CLAIMS["optimum_Q"], 5e-3)
    check("optimum_Cd", float(data["optimized"]["Cd"]),
          THESIS_CLAIMS["optimum_Cd"], 5e-5)
    check("screen_min", min(screen), THESIS_CLAIMS["screen_min"], 5e-5)
    check("screen_center", float(samples[8]["cost"]),
          THESIS_CLAIMS["screen_center"], 5e-5)
    check("screen_max", max(screen), THESIS_CLAIMS["screen_max"], 5e-4)
    check("first_eval", costs[0], THESIS_CLAIMS["first_eval"], 5e-5)
    check("improvement_pct", (incumbent[0] - incumbent[-1]) / incumbent[0] * 100.0,
          THESIS_CLAIMS["improvement_pct"], 5e-3)
    check("above_baseline", len(above), THESIS_CLAIMS["above_baseline"], 0.0)
    check("history_len", len(history), THESIS_CLAIMS["history_len"], 0.0)
    check("ccd_len", len(samples), THESIS_CLAIMS["ccd_len"], 0.0)

    # The two-stage structure the text describes: twenty Latin hypercube points,
    # then fifty Expected Improvement steps, with the handover between indices
    # 19 and 20. The convergence panel draws a line there, so the boundary is
    # asserted rather than assumed.
    initial = [i for i, row in enumerate(history) if row.get("type") == "initial"]
    bayesian = [i for i, row in enumerate(history) if row.get("type") == "bo"]
    if len(initial) != 20 or len(bayesian) != 50 or max(initial) + 1 != min(bayesian):
        raise RuntimeError(
            f"campaign is not 20 Latin hypercube then 50 Bayesian steps: got "
            f"{len(initial)} initial ending at {max(initial) if initial else None} "
            f"and {len(bayesian)} Bayesian starting at {min(bayesian) if bayesian else None}")

    # The text states the incumbent is flat after the optimum, so the last
    # improvement must land on the optimum itself.
    if max(improved_steps) + 1 != 37:
        raise RuntimeError(
            f"incumbent last improves at index {max(improved_steps) + 1}, but the "
            f"text reports the optimum at index 37")

    # The text splits the expensive proposals by the baseline nose radius.
    high = sum(1 for value in above_radius if value > 1.5)
    low = sum(1 for value in above_radius if value < 1.5)
    if (high, low) != (17, 29):
        raise RuntimeError(
            f"expensive proposals split {high}/{low} about the baseline nose "
            f"radius, but the text reports 17/29")


def load_verified() -> dict:
    """Return the committed campaign after every thesis claim has been checked.

    Parameters: none.

    Returns:
        dict, the same object load_committed returns.

    Raises:
        RuntimeError from either underlying function.
    """
    data = load_committed()
    assert_thesis_claims(data)
    print(f"    [verified] {len(THESIS_CLAIMS)} printed claims agree with "
          f"{OPTJSON_REV}")
    return data


if __name__ == "__main__":
    """Run the loader and the claim checks, then report the exit status."""
    try:
        load_verified()
    except RuntimeError as error:
        print(f"FAIL {error}")
        raise SystemExit(1)
    print("SELFCHECK PASS")
