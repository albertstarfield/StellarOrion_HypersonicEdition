#!/usr/bin/env python3
"""Compute optimization-history statistics from hiad_optimization_results.json.

Purpose: derive the exact convergence facts (first cost, running-best
trajectory, final incumbent and its index, counts above baseline, cost span,
CCD sample costs) directly from the results file so the thesis narrative can be
written to the code's own numbers.

Axioms: the JSON file is the authoritative record of the official run.
Theories: running-best is the cumulative minimum of the cost history.
Applications: print the statistics consumed by chapter_04_results.tex.

Inputs: none (path fixed below).
Outputs: key statistics printed to stdout.
Errors: raises on missing file or malformed JSON (no silent fallback).
"""
import json
import pathlib

PATH = pathlib.Path(
    "stellarorion_program_proc/src/python/hiad_optimization_results.json"
)


def main() -> None:
    data = json.loads(PATH.read_text())
    hist = data["history"]
    base = data["default"]["cost"]
    costs = [h["cost"] for h in hist]
    rn = [h.get("R_N") for h in hist]

    running = []
    best = float("inf")
    for c in costs:
        best = min(best, c)
        running.append(best)

    last_improve = max(i for i in range(len(running)) if running[i] < running[i - 1]) \
        if any(running[i] < running[i - 1] for i in range(1, len(running))) else 0

    above = [i for i, c in enumerate(costs) if c > base]
    above_rn = [rn[i] for i in above]
    n_above_nose = sum(1 for r in above_rn if r is not None and r > 1.5)
    n_below_nose = sum(1 for r in above_rn if r is not None and r <= 1.5)

    print(f"n_history          = {len(hist)}")
    print(f"baseline cost      = {base!r}")
    print(f"first eval cost    = {costs[0]!r}")
    print(f"min cost           = {min(costs)!r} at index {costs.index(min(costs))}")
    print(f"max cost           = {max(costs)!r}")
    print(f"running[0]         = {running[0]!r}")
    print(f"running[19] (LHS->BO handover) = {running[19]!r}")
    print(f"running[37]        = {running[37]!r}")
    print(f"running[-1]        = {running[-1]!r} at index {len(running)-1}")
    print(f"last improvement   = index {last_improve} (running {running[last_improve]!r})")
    print(f"n above baseline   = {len(above)} of {len(costs)}")
    print(f"  of those, R_N>1.5 = {n_above_nose}; R_N<=1.5 = {n_below_nose}")
    if min(costs) > 0:
        import math
        print(f"decades span       = {math.log10(max(costs)/min(costs)):.2f}")
    ccd = data.get("ccd_samples", [])
    print(f"n ccd_samples      = {len(ccd)}")
    for s in ccd[:20]:
        print("   ccd", s)


if __name__ == "__main__":
    main()
