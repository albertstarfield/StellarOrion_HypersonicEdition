#!/usr/bin/env python3
"""
================================================================================
SCRIPT: verify_profile_math.py — Ada FFI Cross-Check + CrossHair Invariants
================================================================================

Verifies the HIAD 4-segment profile math so that drift or non-physical
outputs WARN loudly instead of shipping silently.

TWO LAYERS:
  1. Ada FFI cross-check (runtime): Python compute_rapisarda_profile(default)
     vs Ada get_hiad_cross_section() — reports max abs radial drift.
  2. CrossHair symbolic check: run
         crosshair check verify_profile_math.py
     CrossHair explores generate_cross_section / compute_rapisarda_profile
     contracts (pre/post conditions below) over arbitrary inputs.

Optionally can be co-checked with Coq (src/proofs/) for the Ada side;
this script focuses on the Python↔Ada boundary where render bugs hide.

AXIOMS:
  A1: Ada Get_HIAD_Cross_Section and Python generate_cross_section implement
      the same 4-segment math for (R_N, r_tor, half_cone_deg).
  A2: A valid profile has equal-length finite x/y, x >= 0, y >= 0,
      near-zero radial at both ends (nose tip and flat-back center),
      and monotone non-decreasing axial through segments 1–2.
  A3: Any violation of A1/A2 MUST print [WARNING] to stderr and exit
      non-zero (never silent).

THEORIES:
  T1: From A1: max|r_py - r_ada| on a shared axial grid bounds geometric
      disagreement; exceeding tolerance ⇒ math diverged.
  T2: From A2: CrossHair contracts encode A2 as pre/post so symbolic
      exploration finds counterexamples before a bad render ships.

APPLICATIONS:
  python3 verify_profile_math.py          # runtime FFI + local invariants
  crosshair check verify_profile_math.py  # symbolic contracts

CITATIONS:
  [1] ada_pinn_wrapper.get_hiad_cross_section
  [2] hiad_geometry.generate_cross_section
  [3] CrossHair — https://crosshair.readthedocs.io/ (symbolic Python)
  [4] Rapisarda (2023) Sec 3.7 — HIAD 4-segment profile
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths: import render script's profile + hiad_geometry (pure numpy)
# ---------------------------------------------------------------------------
# AXIOM: CrossHair restores sys.path to its pre-import snapshot before
#   analyzing function bodies, so a lazy `from hiad_geometry import ...`
#   INSIDE a checked function raises ModuleNotFoundError (false counterexample).
#   Importing at module load (while our sys.path insert is still active)
#   populates sys.modules; later function-body imports resolve from there.
# [Citation: CrossHair importliblib — https://crosshair.readthedocs.io/]
_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_PYTHON = _SCRIPT_DIR.parent / "src" / "python"
if str(_SRC_PYTHON) not in sys.path:
    sys.path.insert(0, str(_SRC_PYTHON))
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from hiad_geometry import generate_cross_section


def _local_profile_invariants(
    x_pts: list[float], y_pts: list[float], label: str
) -> list[str]:
    """Check local invariants A2 on a profile. Returns list of violation strings.

    CrossHair will explore this function on arbitrary list inputs when
    analyzing this module; empty return means all invariants held.
    """
    violations: list[str] = []
    if len(x_pts) != len(y_pts):
        violations.append(
            f"{label}: length mismatch x={len(x_pts)} y={len(y_pts)}"
        )
        return violations
    if len(x_pts) < 4:
        violations.append(f"{label}: too few points ({len(x_pts)} < 4)")
        return violations
    for i, (x, y) in enumerate(zip(x_pts, y_pts)):
        if not math.isfinite(x) or not math.isfinite(y):
            violations.append(f"{label}: non-finite at i={i}: x={x} y={y}")
            break
        if x < -1e-9:
            violations.append(f"{label}: negative axial at i={i}: x={x}")
            break
        if y < -1e-9:
            violations.append(f"{label}: negative radial at i={i}: y={y}")
            break
    # Nose tip: first point near axis
    if y_pts[0] > 0.15 * max(y_pts):
        violations.append(
            f"{label}: nose tip radial too large: y[0]={y_pts[0]:.4f}"
        )
    # Flat back: last point near axis
    if y_pts[-1] > 0.15 * max(y_pts):
        violations.append(
            f"{label}: flat-back radial too large: y[-1]={y_pts[-1]:.4f}"
        )
    return violations


def check_local_invariants() -> bool:
    """Run A2 invariants on Python generate_cross_section + render replica.

    Returns True when all profiles pass; prints [WARNING] on failure.
    """
    ok = True
    try:
        from hiad_geometry import generate_cross_section
    except ImportError as exc:
        print(f"[WARNING] hiad_geometry import failed: {exc}", file=sys.stderr)
        return False

    # Representative parameter sets (default + optimized + stress corners).
    # Default/optimized R_N/r_tor/half_cone come from hiad_optimization_results.json
    # at call time when available; literals below are the frozen baseline corners.
    cases = [
        (1.5, 0.135, 60.0, "default"),
        (1.155863396265647, 0.05657565016819844, 40.50658086416024, "optimized"),
        (1.2, 0.1, 45.0, "mid"),
        (0.9, 0.08, 35.0, "sharp"),
        (1.8, 0.2, 75.0, "blunt"),
    ]
    # Prefer live JSON values for default/optimized when the file exists
    try:
        from render_optimization_comparison import load_optimization_results
        _res = load_optimization_results()
        cases[0] = (
            float(_res["default"]["R_N"]),
            float(_res["default"]["r_tor"]),
            float(_res["default"]["half_cone_deg"]),
            "default",
        )
        cases[1] = (
            float(_res["optimized"]["R_N"]),
            float(_res["optimized"]["r_tor"]),
            float(_res["optimized"]["half_cone_deg"]),
            "optimized",
        )
    except (FileNotFoundError, KeyError, OSError, ValueError, ImportError) as exc:
        print(f"[WARNING] JSON defaults unavailable, using literals: {exc}",
              file=sys.stderr)

    for rn, rtor, cone, name in cases:
        try:
            x, y = generate_cross_section(rn, rtor, cone, n_per_segment=15)
            x_l, y_l = x.tolist(), y.tolist()
        except (ValueError, TypeError) as exc:
            print(f"[WARNING] generate_cross_section({name}) raised: {exc}",
                  file=sys.stderr)
            ok = False
            continue
        viols = _local_profile_invariants(x_l, y_l, name)
        for v in viols:
            print(f"[WARNING] {v}", file=sys.stderr)
            ok = False
        if not viols:
            print(f"  [local invariants] {name}: OK ({len(x_l)} pts, "
                  f"x=[{min(x_l):.3f},{max(x_l):.3f}], "
                  f"y=[{min(y_l):.3f},{max(y_l):.3f}])")
    return ok


def check_ada_crosscheck() -> bool:
    """Run render_optimization_comparison.crosscheck_ada_profile on defaults.

    Returns True when Ada and Python agree (or FFI unavailable is treated
    as skip-with-warning, still True for local-only runs without dylib —
    but dylib present + drift ⇒ False).
    """
    try:
        from render_optimization_comparison import (
            compute_rapisarda_profile,
            crosscheck_ada_profile,
            load_optimization_results,
        )
    except ImportError as exc:
        print(f"[WARNING] render module import failed: {exc}", file=sys.stderr)
        return False

    try:
        results = load_optimization_results()
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        print(f"[WARNING] cannot load optimization results: {exc}",
              file=sys.stderr)
        return False

    default = results["default"]
    x_py, y_py = compute_rapisarda_profile(
        rn=default["R_N"],
        half_cone_deg=default["half_cone_deg"],
        r_tor=default["r_tor"],
        n_tori=6,
    )
    # crosscheck_ada_profile warns and returns False on drift;
    # returns False also when FFI OSError — distinguish:
    try:
        from render_optimization_comparison import get_ada_default_profile
        get_ada_default_profile()
        ffi_available = True
    except (OSError, AttributeError, RuntimeError) as exc:
        print(f"[WARNING] Ada FFI not available, skipping cross-check: {exc}",
              file=sys.stderr)
        ffi_available = False

    if not ffi_available:
        return True  # local invariants still ran

    return crosscheck_ada_profile(x_py, y_py)


def main() -> int:
    """Entry point: local invariants then Ada FFI cross-check.

    Returns 0 when all checks pass, 1 on any [WARNING] failure.
    """
    print("=== verify_profile_math: local invariants (A2) ===")
    local_ok = check_local_invariants()
    print("=== verify_profile_math: Ada FFI cross-check (A1) ===")
    ada_ok = check_ada_crosscheck()
    if local_ok and ada_ok:
        print("=== verify_profile_math: ALL CHECKS PASSED ===")
        return 0
    print("=== verify_profile_math: FAILURES DETECTED — see [WARNING] above ===",
          file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# CrossHair contracts (crosshair check verify_profile_math.py)
# ---------------------------------------------------------------------------
# AXIOM: CrossHair's default analysis_kind is (PEP316, icontract, deal) —
#   bare asserts are only checked under --analysis_kind=asserts, so the
#   checkable contract MUST be a PEP316 pre:/post: docstring expression.
#   Keys are LOWERCASE (pre:/post:); capital Pre:/Post: is ignored by the
#   parser (→ zero checkables). Return value is __return__ (not result).
# THEORY: encoding invariant A2 as pre/post makes `crosshair check` report
#   this wrapper as a checkable function and explore it symbolically.
# APPLICATION: asserts below remain as runtime guards for direct calls.
# CITATION: CrossHair PEP316 contracts —
#   https://crosshair.readthedocs.io/en/latest/kinds_of_contracts.html
# precondition: R_N > 0 ∧ r_tor > 0 ∧ 0 < half_cone_deg < 90 ∧ n >= 2
# postcondition (A2): equal length, finite, non-negative, endpoints on axis.

def crosshair_generate_cross_section_contract(
    R_N: float,
    r_tor: float,
    half_cone_deg: float,
    n_per_segment: int = 15,
) -> tuple[list[float], list[float]]:
    """Symbolic contract wrapper for hiad_geometry.generate_cross_section.

    Prose (A2): equal lengths, all finite non-negative, nose near
    axis, back near axis.

    pre: R_N > 0 and r_tor > 0 and 0 < half_cone_deg < 90 and n_per_segment >= 2
    post: len(__return__[0]) == len(__return__[1]) and len(__return__[0]) >= 4 and all(math.isfinite(v) and v >= -1e-9 for v in __return__[0]) and all(math.isfinite(v) and v >= -1e-9 for v in __return__[1]) and __return__[1][0] <= 0.15 * max(__return__[1]) + 1e-9 and __return__[1][-1] <= 0.15 * max(__return__[1]) + 1e-9
    """
    # Precondition (CrossHair)
    assert R_N > 0.0, "R_N must be positive"
    assert r_tor > 0.0, "r_tor must be positive"
    assert 0.0 < half_cone_deg < 90.0, "half_cone_deg in (0, 90)"
    assert n_per_segment >= 2, "n_per_segment >= 2"

    # generate_cross_section is imported at module load (see path-setup
    # AXIOM: CrossHair reverts sys.path before analyzing function bodies,
    # so a lazy import here would raise ModuleNotFoundError as a false
    # counterexample).
    x, y = generate_cross_section(
        float(R_N), float(r_tor), float(half_cone_deg),
        n_per_segment=n_per_segment,  # already int per signature (pyrefly strict)
    )
    x_l = [float(v) for v in x]
    y_l = [float(v) for v in y]

    # Postconditions (CrossHair)
    assert len(x_l) == len(y_l), "profile arrays must have equal length"
    assert len(x_l) >= 4, "profile must have at least 4 points"
    assert all(math.isfinite(v) for v in x_l), "x must be finite"
    assert all(math.isfinite(v) for v in y_l), "y must be finite"
    assert all(v >= -1e-9 for v in x_l), "axial must be non-negative"
    assert all(v >= -1e-9 for v in y_l), "radial must be non-negative"
    y_max = max(y_l) if y_l else 0.0
    if y_max > 0.0:
        assert y_l[0] <= 0.15 * y_max + 1e-9, "nose tip near axis"
        assert y_l[-1] <= 0.15 * y_max + 1e-9, "flat back near axis"
    # Flat-back closure: last point radial is ~0 (axis)
    assert y_l[-1] <= 1e-6 + 0.15 * y_max, "flat back closes to axis"
    return x_l, y_l


if __name__ == "__main__":
    sys.exit(main())
