#!/usr/bin/env python3
"""
================================================================================
SCRIPT: render_optimization_comparison.py — Before/After 3D HIAD Comparison
================================================================================

Generates side-by-side 3D renders of the default (IRVE-3 baseline) and
Bayesian-optimized HIAD geometries.

GEOMETRY SOURCE:
  - Default: Ada FFI get_hiad_cross_section() — single source of truth
  - Optimized: Ada FFI get_hiad_cross_section_params() — the SAME Ada/SPARK
    math, parameterized by the BO winner (profile math runs in Ada;
    Python only renders the mesh — both curves are Ada FFI)
  - Parameters (both panels): hiad_optimization_results.json loaded at runtime
    — NEVER hardcoded; re-running hiad_optimizer.py updates this render

COORDINATE FRAME (AXIOM — all meshes MUST match revolve_profile):
  - Axial coordinate is X: nose tip at X≈0, flat back at X=z_back>0
  - Radial coordinates are (Y, Z): surface point = (x, r*cosθ, r*sinθ)
  - Windward face points toward −X; camera looks from the −X side
  - Decorative meshes (drum, dome, tori, gores, back) MUST be built about X,
    never about Z — a prior bug built them about Z while the envelope used X,
    producing a wrongly oriented HIAD (fixed 2026-09-24).

VERIFICATION:
  - crosscheck_ada_profile(): Python replica vs Ada FFI for BOTH the default
    and the optimized profile — loud WARNING on drift (math went wrong) or
    OSError (dylib missing); exit code 2 signals drift
  - scripts/verify_profile_math.py + CrossHair: invariants on profile math

HIAD CONSTRUCTION FEATURES:
  1. Stacked torus ridges — concentric rings about the X axis
  2. Flat disc proportions — inflatable portion nearly flat (8-10:1 dia:height)
  3. Central payload drum — cylinder along X from the mid-body
  4. Radial gore pattern — spokes dividing the tori

CITATIONS:
  [1] NASA LOFTID mission (2022) — 6m HIAD flight demonstration
  [2] IRVE-3 mission (2012) — 3m HIAD suborbital test
  [3] Rapisarda (2023) Sec 3.7 — HIAD flat-skin profile (4-segment)
  [4] do Carmo (1976) — Surface of revolution mathematics
  [5] stellarorion_sparta.adb Generate_HIAD_Surf (line 1913) — Ada geometry engine
  [6] ada_pinn_wrapper.get_hiad_cross_section — ctypes FFI to Ada/SPARK
"""

import json
import math
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# FFI: Get default geometry from Ada/SPARK
# ---------------------------------------------------------------------------

def get_ada_default_profile() -> tuple[list[float], list[float], int]:
    """Get the default HIAD cross-section from Ada FFI.

    Returns (x_list, y_list, n) where x=axial, y=radial.
    All geometry math is in Ada/SPARK; Python is a thin wrapper.

    Safety fallback: OSError if libstellarorion_pinn.dylib is absent —
    caller must handle and warn (never crash the whole render silently).

    [Citation: ada_pinn_wrapper.py get_hiad_cross_section]
    [Citation: stellarorion_pinn_trajectory.ads — Get_HIAD_Cross_Section]
    """
    script_dir = Path(__file__).resolve().parent
    src_python = script_dir.parent / "src" / "python"
    sys.path.insert(0, str(src_python))

    from ada_pinn_wrapper import get_hiad_cross_section
    result = get_hiad_cross_section()
    return result["x"], result["y"], result["n"]


def get_ada_profile_params(
    r_n: float,
    r_tor: float,
    half_cone_deg: float,
) -> tuple[list[float], list[float], int]:
    """Get a parameterized HIAD cross-section from Ada FFI (same Ada math).

    Calls Get_HIAD_Cross_Section_Params via ctypes with arbitrary geometry
    parameters (used for the Bayesian-optimized profile). Returns
    (x_list, y_list, n) where x=axial, y=radial.

    Raises:
      OSError      — libstellarorion_pinn.dylib absent/not loadable
      ValueError   — non-physical parameters (GIGO fail-closed in wrapper)
      AttributeError/RuntimeError — FFI symbol missing (stale dylib)

    Safety fallback: caller must handle OSError/ValueError/AttributeError/
    RuntimeError and fail closed (never render a fabricated profile).

    [Citation: ada_pinn_wrapper.py get_hiad_cross_section_params]
    [Citation: stellarorion_pinn_trajectory.ads — Get_HIAD_Cross_Section_Params]
    """
    script_dir = Path(__file__).resolve().parent
    src_python = script_dir.parent / "src" / "python"
    sys.path.insert(0, str(src_python))

    from ada_pinn_wrapper import get_hiad_cross_section_params
    result = get_hiad_cross_section_params(r_n, r_tor, half_cone_deg)
    return result["x"], result["y"], result["n"]


def crosscheck_ada_profile(
    py_x: list[float],
    py_y: list[float],
    rtol: float = 5e-3,
    atol: float = 2e-3,
    ada_profile: tuple[list[float], list[float], int] | None = None,
) -> bool:
    """Cross-check a Python profile against Ada FFI via arc-length.

    -- AXIOMS:
    --   A1: Ada Get_HIAD_Cross_Section(_Params) and
    --       hiad_geometry.generate_cross_section implement the same
    --       4-segment math for identical parameters.
    --   A2: The meridian is a closed polyline (nose tip → flat-back → axis),
    --       NOT a function y=f(x): segment 4 (flat back) has constant axial
    --       x with many radial y values. Interpolating y as f(x) on that
    --       vertical run is ill-defined and must NOT be used.
    --   A3: Sampling density may differ (Ada n=57 vs Python n_per_segment);
    --       comparison must resample both curves by cumulative arc length.
    --   A4: Any true geometric drift beyond rtol/atol OR any FFI failure
    --       MUST warn loudly — silent drift would let wrong math ship.
    -- -- THEORIES:
    --   T1: From A1–A3: after arc-length resampling to a shared parameter
    --       s ∈ [0,1], max||(x, y)_py(s) − (x, y)_ada(s)|| bounds the
    --       pointwise geometric disagreement along the meridian.
    --   T2: From A4: print WARNING to stderr and return False — never raise
    --       so the render can still proceed for visual inspection.
    -- -- APPLICATIONS: main() calls this once per panel (default profile:
    --   ada_profile=None loads the default Ada FFI profile; optimized
    --   profile: main passes the tuple returned by get_ada_profile_params)
    --   and uses the booleans for figure annotation / process exit status.
    -- -- CITATIONS:
    --   [Citation: ada_pinn_wrapper.get_hiad_cross_section(_params)]
    --   [Citation: arclength parameterization — do Carmo (1976)]
    --
    -- SAFETY FALLBACK: returns False + stderr WARNING on any failure;
    -- Normal expectation: True when profiles agree within tolerance;
    -- ERROR: FFI OSError, empty/non-finite profiles, or max pointwise
    --   distance > atol + rtol * scale.
    """
    try:
        import numpy as np
    except ImportError as exc:
        print(f"[WARNING] crosscheck_ada_profile: numpy missing: {exc}",
              file=sys.stderr)
        return False

    try:
        if ada_profile is None:
            ada_x, ada_y, n_ada = get_ada_default_profile()
        else:
            ada_x, ada_y, n_ada = ada_profile
    except (OSError, AttributeError, RuntimeError) as exc:
        print(f"[WARNING] Ada FFI cross-check unavailable: {exc} — "
              f"Python profile used WITHOUT Ada validation",
              file=sys.stderr)
        return False

    if n_ada < 2 or len(py_x) < 2:
        print(f"[WARNING] crosscheck_ada_profile: too few points "
              f"(ada n={n_ada}, py n={len(py_x)})", file=sys.stderr)
        return False

    def _resample_arc(
        xs: list[float],
        ys: list[float],
        n_s: int = 200,
    ) -> Any:
        """Resample (x, y) polyline onto uniform cumulative arc-length grid.

        Returns (S, X, Y) where S is uniform in [0, 1] by arc length
        (three numpy arrays), or None on non-finite/too-short input.
        Non-finite inputs return None (caller warns).
        """
        xa = np.asarray(xs, dtype=float)
        ya = np.asarray(ys, dtype=float)
        if xa.shape != ya.shape or xa.size < 2:
            return None
        if not (np.all(np.isfinite(xa)) and np.all(np.isfinite(ya))):
            return None
        seg = np.hypot(np.diff(xa), np.diff(ya))
        cum = np.concatenate(([0.0], np.cumsum(seg)))
        total = float(cum[-1])
        if total <= 0.0:
            return None
        s = cum / total
        # Guard against duplicate s values (zero-length segments)
        s_u, idx_u = np.unique(s, return_index=True)
        if s_u.size < 2:
            return None
        grid = np.linspace(0.0, 1.0, n_s)
        xg = np.interp(grid, s_u, xa[idx_u])
        yg = np.interp(grid, s_u, ya[idx_u])
        return grid, xg, yg

    ada_rs = _resample_arc(ada_x, ada_y)
    py_rs = _resample_arc(py_x, py_y)
    if ada_rs is None or py_rs is None:
        print("[WARNING] crosscheck_ada_profile: arc-length resample failed "
              f"(ada={'ok' if ada_rs else 'bad'}, "
              f"py={'ok' if py_rs else 'bad'})", file=sys.stderr)
        return False

    _, ax_g, ay_g = ada_rs
    _, px_g, py_g = py_rs
    dist = np.hypot(px_g - ax_g, py_g - ay_g)
    scale = max(
        float(np.max(np.hypot(ax_g, ay_g))),
        float(np.max(np.hypot(px_g, py_g))),
        1.0,
    )
    max_abs = float(np.max(dist))
    tol = atol + rtol * scale
    ok = max_abs <= tol
    status = "OK" if ok else "DRIFT"
    print(f"  [Ada FFI cross-check] {status}: max arc-length pointwise "
          f"distance = {max_abs:.6f} m (tol {tol:.6f} m) on 200 arc samples, "
          f"ada n={n_ada}, py n={len(py_x)}")
    if not ok:
        print(f"[WARNING] Python profile MATH DRIFT vs Ada FFI — "
              f"geometry render may be wrong (max distance {max_abs:.6f} m > "
              f"tol {tol:.6f} m)", file=sys.stderr)
    return ok


# ---------------------------------------------------------------------------
# Optimizer ground truth: hiad_optimization_results.json (runtime load)
# ---------------------------------------------------------------------------

def load_optimization_results() -> dict[str, Any]:
    """Load default + optimized HIAD parameters from hiad_optimization_results.json.

    -- AXIOMS:
    --   1. hiad_optimization_results.json (written by hiad_optimizer.py) is the
    --      single source of truth for optimizer outputs; render scripts must
    --      never embed optimized literals (they drift on every optimizer run).
    --   2. The file always contains 'default' and 'optimized' blocks, each with
    --      keys R_N, r_tor, half_cone_deg, Cd (contract of hiad_optimizer.py).
    --   3. IRVE-3 baseline defaults (R_N=1.5, r_tor=0.135, half_cone=60) match
    --      the Ada/SPARK axioms but are still read from the JSON 'default'
    --      block here so the whole render is automatic from one file.
    -- -- THEORIES:
    --   Loading at runtime guarantees profile parameters, label strings, and
    --   displayed Cd always match the latest optimizer output (no stale drift).
    --   Fail-closed on missing file/keys prevents rendering wrong numbers —
    --   a silent fallback to literals would violate AXIOM 1.
    -- -- APPLICATIONS: main() reads ['default'] / ['optimized'] from the
    --   returned dict and forwards them to compute_rapisarda_profile(),
    --   render_hiad(), and the text2D annotation labels.
    -- -- CITATIONS:
    --   [Citation: hiad_optimization_results.json — default/optimized blocks]
    --   [Citation: hiad_optimizer.py — writes this JSON at step [6/7]]
    --   [Citation: docs.python.org/3/library/json.html — json.load]
    --
    -- TIMING ANALYSIS
    -- Estimated Processing Time: O(1) — one file read + small dict parse
    -- CPU Time: ~1ms typical (local SSD, <25 KB JSON)
    -- WCET: ~50ms with filesystem contention (50x margin)
    -- Space Complexity: O(1) — one dict (~752-line JSON resident)
    -- Derivation: open+read+json.load dominate; key checks are O(k), k=10
    -- Hardware Assumptions: POSIX system, local filesystem, CPython 3.10+
    --
    -- SAFETY FALLBACK: fail-closed — raises FileNotFoundError/KeyError with
    -- full path context instead of silently substituting stale numbers.
    -- Normal expectation: returns dict with both blocks; ERROR: missing file,
    -- malformed JSON, or missing required keys (printed to stderr with path).
    -- Why input differs from output: file bytes -> parsed dict with validated
    -- keys (validation transforms raw JSON into a guaranteed-shape dict).
    """
    script_dir = Path(__file__).resolve().parent
    results_path = script_dir.parent / "src" / "python" / "hiad_optimization_results.json"

    # APPLICATION STEP 1 (AXIOM: file exists after hiad_optimizer run)
    if not results_path.is_file():
        msg = (f"[FATAL] hiad_optimization_results.json not found at "
               f"{results_path} — run src/python/hiad_optimizer.py first")
        print(msg, file=sys.stderr)
        raise FileNotFoundError(msg)

    # APPLICATION STEP 2 (AXIOM: file is valid JSON)
    try:
        with open(results_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        msg = f"[FATAL] Invalid JSON in {results_path}: {exc}"
        print(msg, file=sys.stderr)
        raise
    except OSError as exc:
        msg = f"[FATAL] Cannot read {results_path}: {exc}"
        print(msg, file=sys.stderr)
        raise

    # APPLICATION STEP 3 (AXIOM 2: required blocks/keys present)
    required_keys = ("R_N", "r_tor", "half_cone_deg", "Cd")
    for block_name in ("default", "optimized"):
        block = data.get(block_name)
        if not isinstance(block, dict):
            msg = (f"[FATAL] {results_path} missing required object "
                   f"'{block_name}'")
            print(msg, file=sys.stderr)
            raise KeyError(block_name)
        for key in required_keys:
            if key not in block:
                msg = (f"[FATAL] {results_path} block '{block_name}' "
                       f"missing required key '{key}'")
                print(msg, file=sys.stderr)
                raise KeyError(f"{block_name}.{key}")

    return data


# ---------------------------------------------------------------------------
# Profile generation — DELEGATED to hiad_geometry (single source of truth)
# ---------------------------------------------------------------------------
# AXIOMS:
#   A1: hiad_geometry.generate_cross_section is an exact Python replica of
#       Ada Get_HIAD_Cross_Section (documented line-for-line in that module).
#   A2: Duplicate 4-segment math in this file would diverge (copy-paste bug);
#       ALL profile math lives in hiad_geometry only.
# THEORIES:
#   T1: From A1+A2: importing and calling generate_cross_section guarantees
#       the same curve the Ada FFI returns for default parameters, and the
#       same curve the optimizer evaluates for candidate parameters.
# APPLICATIONS: main() and verify_profile_math.py both call this wrapper;
#   no second implementation exists in scripts/.
# CITATIONS:
#   [Citation: hiad_geometry.generate_cross_section]
#   [Citation: stellarorion_pinn_trajectory.adb Get_HIAD_Cross_Section]
#
# SAFETY FALLBACK: ValueError from hiad_geometry on non-physical inputs
# propagates (fail-closed). Normal expectation: (x_list, y_list) floats;
# ERROR: invalid R_N / r_tor / half_cone / n_per_segment.

def compute_rapisarda_profile(
    rn: float = 1.5,
    half_cone_deg: float = 60.0,
    r_tor: float = 0.135,
    n_tori: int = 6,
    n_seg: int = 20,
) -> tuple[list[float], list[float]]:
    """Compute the 4-segment HIAD flat-skin cross-section via hiad_geometry.

    Thin wrapper around hiad_geometry.generate_cross_section — NO local
    reimplementation of the 4-segment math (avoids copy-paste divergence).

    Parameters mirror the former local implementation for call-site
    compatibility:
        rn           — nose sphere radius R_N [m]
        half_cone_deg— half-cone angle [deg]
        r_tor        — torus minor radius [m]
        n_tori       — accepted for signature compat; N_TORI is fixed at 6
                       inside hiad_geometry (IRVE-3 baseline axiom).
        n_seg        — sample points per segment (>= 2)

    Returns:
        (x_list, y_list) — x=axial [m], y=radial [m]; Python lists of floats.

    Raises:
        ValueError — non-physical geometry parameters (fail-closed, from
        hiad_geometry validation).

    [Citation: hiad_geometry.generate_cross_section]
    [Citation: Rapisarda (2023) Sec 3.7, Appendix C.1]
    """
    del n_tori  # N_TORI is an Ada/geometry constant (6), not a free parameter
    from hiad_geometry import generate_cross_section

    x_arr, y_arr = generate_cross_section(
        rn, r_tor, half_cone_deg, n_per_segment=n_seg
    )
    return [float(v) for v in x_arr], [float(v) for v in y_arr]


# ---------------------------------------------------------------------------
# 3D mesh generation: revolve profile around X axis
# ---------------------------------------------------------------------------

def revolve_profile(
    x_list: list[float],
    y_list: list[float],
    n_az: int = 60,
) -> tuple[Any, Any, Any]:
    """Revolve a 2D (x, y) profile around the X-axis to create a 3D surface.

    The profile is in the (x, y) plane where x=axial, y=radial.
    Revolving around X-axis gives: for each (x_i, y_i),
      surface point at angle theta: (x_i, y_i*cos(theta), y_i*sin(theta))

    AXIOM: ALL decorative meshes in this file MUST use the same frame
    (axial=X, radial in the YZ plane). A prior bug mixed Z-axial meshes
    with this X-axial envelope.

    [Citation: do Carmo (1976) — Surface of revolution]
    [Citation: render_geometry_grid.py revolve_profile — reference implementation]
    """
    import numpy as np
    n_pts = len(x_list)
    X = np.zeros((n_az, n_pts))
    Y = np.zeros((n_az, n_pts))
    Z = np.zeros((n_az, n_pts))

    for i in range(n_az):
        theta = 2.0 * math.pi * i / n_az
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(n_pts):
            X[i, j] = x_list[j]
            Y[i, j] = y_list[j] * cos_t
            Z[i, j] = y_list[j] * sin_t

    return X, Y, Z


# ---------------------------------------------------------------------------
# HIAD visual features — ALL about the X (axial) axis
# ---------------------------------------------------------------------------

def mesh_torus(
    cx: float,
    major_r: float,
    minor_r: float,
    n_major: int = 60,
    n_minor: int = 20,
) -> tuple[Any, Any, Any]:
    """Generate a torus mesh whose axis of symmetry is X, centered at x=cx.

    Ring circle lies in the YZ plane; tube extends slightly along ±X.

    [Citation: do Carmo (1976) — Torus parametrization]
    """
    import numpy as np
    X = np.zeros((n_major, n_minor + 1))
    Y = np.zeros((n_major, n_minor + 1))
    Z = np.zeros((n_major, n_minor + 1))
    for i in range(n_major):
        u = 2 * math.pi * i / n_major
        cos_u, sin_u = math.cos(u), math.sin(u)
        for j in range(n_minor + 1):
            v = 2 * math.pi * j / n_minor
            cos_v, sin_v = math.cos(v), math.sin(v)
            r = major_r + minor_r * cos_v
            # Axial position from tube's sin(v); ring radius in YZ
            X[i, j] = cx + minor_r * sin_v
            Y[i, j] = r * cos_u
            Z[i, j] = r * sin_u
    return X, Y, Z


def mesh_cylinder(
    x_bottom: float,
    x_top: float,
    radius: float,
    n_az: int = 60,
    n_x: int = 10,
) -> tuple[Any, Any, Any]:
    """Generate a cylinder mesh for the central payload drum, axis along X.

    Parameters:
        x_bottom — axial start [m]
        x_top    — axial end [m]
        radius   — drum radius in the YZ plane [m]
    """
    import numpy as np
    X = np.zeros((n_az, n_x + 1))
    Y = np.zeros((n_az, n_x + 1))
    Z = np.zeros((n_az, n_x + 1))
    for i in range(n_az):
        theta = 2 * math.pi * i / n_az
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(n_x + 1):
            t = j / n_x
            X[i, j] = x_bottom + t * (x_top - x_bottom)
            Y[i, j] = radius * cos_t
            Z[i, j] = radius * sin_t
    return X, Y, Z


def mesh_dome(
    x_base: float,
    radius: float,
    height: float,
    direction: int = +1,
    n_r: int = 40,
    n_az: int = 60,
) -> tuple[Any, Any, Any]:
    """Generate a dome (hemisphere-like) mesh for the nose/payload cap.

    Axis of the dome is X. direction=+1 grows toward +X (aft); direction=-1
    grows toward −X (toward the windward nose tip).

    Parameters:
        x_base    — axial position of the dome base [m]
        radius    — base radius in YZ [m]
        height    — dome height along X [m]
        direction — +1 or −X growth direction
    """
    import numpy as np
    if direction not in (+1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction}")
    X = np.zeros((n_az, n_r + 1))
    Y = np.zeros((n_az, n_r + 1))
    Z = np.zeros((n_az, n_r + 1))
    for i in range(n_az):
        theta = 2 * math.pi * i / n_az
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(n_r + 1):
            t = j / n_r
            x = x_base + direction * height * t
            r = radius * math.sqrt(max(0.0, 1.0 - t * t))
            X[i, j] = x
            Y[i, j] = r * cos_t
            Z[i, j] = r * sin_t
    return X, Y, Z


def mesh_gore_spokes(
    x_inner: float,
    x_outer: float,
    r_inner: float,
    r_outer: float,
    num_spokes: int = 24,
    spoke_width: float = 0.02,
    n_pts: int = 20,
) -> list[tuple[Any, Any, Any]]:
    """Generate radial spoke/gore line meshes in the YZ plane along X.

    Each spoke is a thin ribbon from (r_inner at x_inner) to
    (r_outer at x_outer), offset tangentially by spoke_width/2.
    """
    import numpy as np
    meshes = []
    for k in range(num_spokes):
        theta = 2 * math.pi * k / num_spokes
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        cos_p, sin_p = math.cos(theta + math.pi / 2), math.sin(theta + math.pi / 2)
        X = np.zeros((2, n_pts + 1))
        Y = np.zeros((2, n_pts + 1))
        Z = np.zeros((2, n_pts + 1))
        for side_idx, side in enumerate([-1, 1]):
            for i in range(n_pts + 1):
                t = i / n_pts
                r = r_inner + t * (r_outer - r_inner)
                x = x_inner + t * (x_outer - x_inner)
                offset = side * spoke_width / 2
                X[side_idx, i] = x
                Y[side_idx, i] = r * cos_t + offset * cos_p
                Z[side_idx, i] = r * sin_t + offset * sin_p
        meshes.append((X, Y, Z))
    return meshes


def mesh_flat_back(
    x_back: float,
    radius: float,
    n_r: int = 20,
    n_az: int = 60,
) -> tuple[Any, Any, Any]:
    """Generate a flat circular back plate mesh in the YZ plane at x=x_back."""
    import numpy as np
    X = np.zeros((n_az, n_r + 1))
    Y = np.zeros((n_az, n_r + 1))
    Z = np.zeros((n_az, n_r + 1))
    for i in range(n_az):
        theta = 2 * math.pi * i / n_az
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(n_r + 1):
            t = j / n_r
            r = radius * t
            X[i, j] = x_back
            Y[i, j] = r * cos_t
            Z[i, j] = r * sin_t
    return X, Y, Z


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------

def _profile_rim(
    x_profile: list[float],
    y_profile: list[float],
) -> tuple[float, float, float]:
    """Locate the outer rim and flat-back radius on a HIAD meridian.

    Returns (x_rim, r_max, r_back) where:
      x_rim  — axial station of maximum radius (rim of the saucer)
      r_max  — maximum radial extent
      r_back — radius where the flat-back segment begins (first point at
               x ≈ x_max); this is the true flat-disc radius, NOT r_max.

    AXIOMS: segment 4 has constant x = x_max with r decreasing to 0; the
    mesh for the flat back must use r_back, otherwise the disc sticks out
    past the envelope silhouette (visual bug fixed 2026-09-24).
    """
    r_max = max(y_profile)
    x_max = max(x_profile)
    i_rim = y_profile.index(r_max)
    x_rim = x_profile[i_rim]
    # First index at max axial station = start of flat-back (seg 4)
    r_back = 0.0
    for i, x in enumerate(x_profile):
        if abs(x - x_max) < 1e-9:
            r_back = y_profile[i]
            break
    return x_rim, r_max, r_back


def render_hiad(
    ax: Any,
    x_profile: list[float],
    y_profile: list[float],
    color_base: tuple[int, int, int] | str,
    label_color: str,
    half_cone_deg: float,
    r_tor: float,
    cd_value: float,
    rn: float,
    is_optimized: bool = False,
) -> None:
    """Render a HIAD from a profile + visual features (axial=X frame).

    Parameters:
      ax            — matplotlib 3D axis
      x_profile     — axial coordinates from Ada/profile (X)
      y_profile     — radial coordinates from Ada/profile (YZ radius)
      color_base    — base color: RGB 0-255 tuple, or a hex color string
                      (converted to channels for the torus gradient)
      label_color   — color for text labels
      half_cone_deg — half-cone angle (for torus placement and drum_r)
      r_tor         — torus minor radius (for torus ridges)
      cd_value      — drag coefficient value to display
      rn            — nose sphere radius (for computing drum_r)
      is_optimized  — True for optimized variant

    AXIOM: every decorative mesh is built in the axial=X frame and must lie
    within the envelope silhouette (rim/back radii from _profile_rim).
    """
    # 1. Main envelope: revolve the Ada/profile around X axis
    X_env, Y_env, Z_env = revolve_profile(x_profile, y_profile, n_az=60)
    # Narrow the `tuple | str` union ONCE (pyrefly strict): the envelope may
    # be painted from either form, but the torus-gradient math below needs
    # numeric channels — derive rgb_base so those lines index a real tuple
    # (previously `color_base[0] * 0.7` typed as `str.__mul__(float)`).
    if isinstance(color_base, str):
        # Deferred import: matplotlib loads only when actually rendering
        # (same pattern as get_ada_default_profile's deferred FFI import).
        # to_rgb raises ValueError on malformed colors — loud, never silent.
        # [Citation: matplotlib.colors.to_rgb —
        #  https://matplotlib.org/stable/api/colors_api.html#matplotlib.colors.to_rgb]
        from matplotlib.colors import to_rgb
        color_hex = color_base
        r_f, g_f, b_f = to_rgb(color_base)
        rgb_base = (round(r_f * 255), round(g_f * 255), round(b_f * 255))
    else:
        rgb_base = color_base
        color_hex = '#{:02x}{:02x}{:02x}'.format(*rgb_base)
    ax.plot_surface(X_env, Y_env, Z_env,
                    color=color_hex, alpha=0.85, edgecolor='none', shade=True)

    # 2. Key dimensions from the actual profile (not guessed from params)
    x_rim, r_max, r_back = _profile_rim(x_profile, y_profile)
    x_max = max(x_profile)
    # Drum radius = tangent point radius R_Tang = R_N * cos(gamma)
    # [Citation: stellarorion_sparta.adb line 1965: R_Tang := R_N * Cos_G]
    gamma_rad = (90.0 - half_cone_deg) * math.pi / 180.0
    drum_r = rn * math.cos(gamma_rad)
    # Visual sanity: keep drum inside the envelope (safety fallback)
    drum_r = min(drum_r, 0.55 * r_max)

    # 3. Central payload drum — axis along X, aft half of the body
    #    (payload sits behind the heatshield; nose tip is at X≈0)
    drum_height = drum_r * 0.35
    x_drum0 = 0.25 * x_max
    x_drum1 = x_drum0 + drum_height
    X_drum, Y_drum, Z_drum = mesh_cylinder(x_drum0, x_drum1, drum_r)
    ax.plot_surface(X_drum, Y_drum, Z_drum,
                    color='#555555', alpha=0.9, edgecolor='none', shade=True)

    # 4. Cap dome on the drum — grows toward the windward nose (−X)
    X_nose, Y_nose, Z_nose = mesh_dome(
        x_drum0, drum_r * 0.6, drum_r * 0.3, direction=-1)
    ax.plot_surface(X_nose, Y_nose, Z_nose,
                    color='#e94560', alpha=0.95, edgecolor='none', shade=True)

    # 5. Stacked torus ridges about the X axis, placed along the profile
    n_tori = 6
    for idx in range(n_tori):
        t = (idx + 0.5) / n_tori
        target_r = drum_r + t * (r_max - drum_r)
        # Nearest profile index by radial distance (explicit loop — typed,
        # no unannotated lambda for pyrefly strict mode)
        profile_idx = 0
        best_delta = abs(y_profile[0] - target_r)
        for i in range(1, len(y_profile)):
            delta = abs(y_profile[i] - target_r)
            if delta < best_delta:
                best_delta = delta
                profile_idx = i
        x_center = x_profile[profile_idx]
        r_center = y_profile[profile_idx]

        if r_center < drum_r + r_tor:
            continue

        frac = idx / max(1, n_tori - 1)
        r_c = int(rgb_base[0] * 0.7 + frac * 40)
        g_c = int(rgb_base[1] * 0.7 + frac * 20)
        b_c = int(rgb_base[2] * 0.7 + frac * 30)
        torus_color = f'#{min(255,r_c):02x}{min(255,g_c):02x}{min(255,b_c):02x}'

        X_t, Y_t, Z_t = mesh_torus(x_center, r_center, r_tor * 0.6,
                                   n_major=60, n_minor=12)
        ax.plot_surface(X_t, Y_t, Z_t,
                        color=torus_color, alpha=0.92, edgecolor='none', shade=True)

    # 6. Gore spokes from drum out to the RIM (x_rim, r_max) — not to
    #    (x_max, r_max), which lies outside the envelope at the flat back.
    gore_meshes = mesh_gore_spokes(
        x_drum0, x_rim, drum_r * 0.6, r_max * 0.98,
        num_spokes=24, spoke_width=0.03
    )
    for X_g, Y_g, Z_g in gore_meshes:
        ax.plot_surface(X_g, Y_g, Z_g,
                        color='#333333', alpha=0.4, edgecolor='none')

    # 7. Flat back plate — radius is r_back (seg-4 start), NOT r_max
    X_back, Y_back, Z_back = mesh_flat_back(x_max, r_back)
    ax.plot_surface(X_back, Y_back, Z_back,
                    color='#222222', alpha=0.7, edgecolor='none', shade=True)


def _apply_view(ax: Any, x_max: float, r_max: float) -> None:
    """Apply shared axis limits, aspect, and camera for fair comparison.

    Parameters:
      ax    — matplotlib 3D axis, mutated in place
      x_max — axial extent of the profile (data units)
      r_max — maximum radial extent of the profile (data units)

    Returns:
      None (side effects on ax only).

    Frame matches render_geometry_grid: X=axial [0, x_max*1.05],
    Y/Z radial symmetric ±r_max*1.15.

    Camera: elev=22°, azim=−55° — the repo-standard 3/4 side view used by
    render_geometry_grid (_ELEV=22, _AZIM=-55) and render_bo_3d_plot.
    With matplotlib's convention (eye at cos(elev)·(cos azim, sin azim, ·)
    looking at origin), azim=−55° places the eye on the +X/−Y quadrant so
    the side silhouette of the cone is visible and the 60° vs 40.5°
    half-cone difference reads clearly. The earlier azim=−145° looked
    nearly face-on down the X axis and rendered both HIADs as flat circles,
    hiding the very geometry difference this figure exists to show.
    """
    ax.set_xlim(0.0, x_max * 1.05)
    ax.set_ylim(-r_max * 1.15, r_max * 1.15)
    ax.set_zlim(-r_max * 1.15, r_max * 1.15)
    # Box aspect proportional to data extents (X length vs YZ diameter)
    ax.set_box_aspect([x_max * 1.05, 2.3 * r_max, 2.3 * r_max])
    ax.view_init(elev=22, azim=-55)


def main() -> int:
    """Generate comparison renders using Ada FFI for default geometry.

    Optimized AND default parameters are loaded at runtime from
    hiad_optimization_results.json — no literals are embedded here.

    -- SAFETY FALLBACK: returns exit code 1 if the JSON is missing/malformed
      or the Ada FFI dylib is absent (verbose diagnostics on stderr).
      Ada cross-check drift prints WARNING but does not block rendering
      (visual inspection still valuable); exit code 2 signals drift.
    -- TIMING ANALYSIS
    -- Estimated Processing Time: O(1) JSON load + O(P) profile compute + render
    -- CPU Time: ~2-5s typical (matplotlib 3D surface, 2 panels)
    -- WCET: ~30s under GPU/headless contention (10x margin)
    -- Space Complexity: O(n_az * n_pts) mesh buffers (~60x77 per surface)
    -- Hardware Assumptions: POSIX, CPython 3.10+, matplotlib Agg backend
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # --- Load optimizer ground truth (AXIOM: JSON is single source) ---
    print("Loading optimization results from hiad_optimization_results.json...")
    try:
        results = load_optimization_results()
    except (FileNotFoundError, KeyError, json.JSONDecodeError, OSError) as exc:
        # Safety fallback: fail closed — never render stale hardcoded numbers
        print(f"[FATAL] Cannot load optimization results: {exc}",
              file=sys.stderr)
        return 1
    default = results["default"]
    opt = results["optimized"]
    print(f"  default:   R_N={default['R_N']:.4f}  r_tor={default['r_tor']:.4f}  "
          f"half_cone={default['half_cone_deg']:.4f}  Cd={default['Cd']:.4f}")
    print(f"  optimized: R_N={opt['R_N']:.4f}  r_tor={opt['r_tor']:.4f}  "
          f"half_cone={opt['half_cone_deg']:.4f}  Cd={opt['Cd']:.4f}")

    # --- Get default profile from Ada FFI ---
    print("Loading default HIAD profile from Ada FFI...")
    try:
        x_def, y_def, n_def = get_ada_default_profile()
    except (OSError, AttributeError, RuntimeError) as exc:
        print(f"[FATAL] Ada FFI unavailable: {exc}", file=sys.stderr)
        print("  Build libstellarorion_pinn.dylib (alr build) or run from "
              "an environment where the dylib is on DYLD_LIBRARY_PATH.",
              file=sys.stderr)
        return 1
    print(f"  Ada returned {n_def} points, x=[{min(x_def):.4f}, {max(x_def):.4f}], "
          f"y=[{min(y_def):.4f}, {max(y_def):.4f}]")

    # --- Compute default profile in Python for FFI cross-check ---
    n_tori = 6  # structural constant: IRVE-3 6+1 torus stack (not optimized)
    x_def_py, y_def_py = compute_rapisarda_profile(
        rn=default["R_N"], half_cone_deg=default["half_cone_deg"],
        r_tor=default["r_tor"], n_tori=n_tori
    )
    print("Cross-checking Python default profile against Ada FFI...")
    ada_ok = crosscheck_ada_profile(x_def_py, y_def_py)

    # --- Get optimized profile from Ada FFI (same Ada math, JSON params) ---
    # [Citation: hiad_optimization_results.json — optimized block]
    print("Loading optimized HIAD profile from Ada FFI...")
    try:
        x_opt, y_opt, n_opt = get_ada_profile_params(
            opt["R_N"], opt["r_tor"], opt["half_cone_deg"])
    except (OSError, AttributeError, RuntimeError, ValueError) as exc:
        # Safety fallback: fail closed — never render a fabricated profile
        print(f"[FATAL] Ada FFI unavailable for optimized profile: {exc}",
              file=sys.stderr)
        print("  Build libstellarorion_pinn.dylib (alr build) or run from "
              "an environment where the dylib is on DYLD_LIBRARY_PATH.",
              file=sys.stderr)
        return 1
    print(f"  Ada returned {n_opt} points, x=[{min(x_opt):.4f}, {max(x_opt):.4f}], "
          f"y=[{min(y_opt):.4f}, {max(y_opt):.4f}]")

    # --- Python replica of optimized profile for FFI cross-check ---
    x_opt_py, y_opt_py = compute_rapisarda_profile(
        rn=opt["R_N"], half_cone_deg=opt["half_cone_deg"],
        r_tor=opt["r_tor"], n_tori=n_tori
    )
    print("Cross-checking Python optimized profile against Ada FFI...")
    ada_opt_ok = crosscheck_ada_profile(
        x_opt_py, y_opt_py, ada_profile=(x_opt, y_opt, n_opt),
    )

    # Shared limits for fair side-by-side comparison
    x_max_all = max(max(x_def), max(x_opt))
    r_max_all = max(max(y_def), max(y_opt))

    # --- Create figure ---
    fig = plt.figure(figsize=(16, 8), facecolor='#0a0a0f')

    # Default (left) — blue tones; params loaded from JSON 'default' block
    ax1 = fig.add_subplot(121, projection='3d', facecolor='#0a0a0f')
    render_hiad(ax1, x_def, y_def,
                color_base=(26, 82, 128), label_color='#8892b0',
                half_cone_deg=default["half_cone_deg"], r_tor=default["r_tor"],
                cd_value=default["Cd"], rn=default["R_N"])
    ax1.set_title('BEFORE (IRVE-3 Default — Ada FFI)', color='#8892b0', fontsize=12,
                  fontweight='bold', pad=10)
    ax1.set_xlabel('X (axial) [m]', color='#8892b0', fontsize=8)
    ax1.set_ylabel('Y [m]', color='#8892b0', fontsize=8)
    ax1.set_zlabel('Z [m]', color='#8892b0', fontsize=8)
    ax1.tick_params(colors='#555555', labelsize=6)
    _apply_view(ax1, x_max_all, r_max_all)
    def_label = (f"R_N={default['R_N']:.2f}m  half_cone={default['half_cone_deg']:.1f}\n"
                 f"r_tor={default['r_tor']:.3f}m  {n_tori} tori\n"
                 f"Cd={default['Cd']:.4f}\nSource: Ada FFI"
                 + ("" if ada_ok else "\n[Ada cross-check DRIFT]"))
    ax1.text2D(0.02, 0.02, def_label,
        transform=ax1.transAxes, color='#8892b0', fontsize=8,
        verticalalignment='bottom',
        bbox={'boxstyle': 'round,pad=0.3', 'facecolor': '#1a1a2e',
              'edgecolor': '#0f3460'})

    # Optimized (right) — red tones; params loaded from JSON 'optimized' block
    ax2 = fig.add_subplot(122, projection='3d', facecolor='#0a0a0f')
    render_hiad(ax2, x_opt, y_opt,
                color_base=(192, 57, 43), label_color='#e94560',
                half_cone_deg=opt["half_cone_deg"], r_tor=opt["r_tor"],
                cd_value=opt["Cd"], rn=opt["R_N"],
                is_optimized=True)
    ax2.set_title('AFTER (Optimized — Bayesian — Ada FFI)', color='#e94560', fontsize=12,
                  fontweight='bold', pad=10)
    ax2.set_xlabel('X (axial) [m]', color='#8892b0', fontsize=8)
    ax2.set_ylabel('Y [m]', color='#8892b0', fontsize=8)
    ax2.set_zlabel('Z [m]', color='#8892b0', fontsize=8)
    ax2.tick_params(colors='#555555', labelsize=6)
    _apply_view(ax2, x_max_all, r_max_all)
    opt_label = (f"R_N={opt['R_N']:.2f}m  half_cone={opt['half_cone_deg']:.1f}\n"
                 f"r_tor={opt['r_tor']:.3f}m  {n_tori} tori\n"
                 f"Cd={opt['Cd']:.4f}\nSource: Ada FFI"
                 + ("" if ada_opt_ok else "\n[Ada cross-check DRIFT]"))
    ax2.text2D(0.02, 0.02, opt_label,
        transform=ax2.transAxes, color='#e94560', fontsize=8,
        verticalalignment='bottom',
        bbox={'boxstyle': 'round,pad=0.3', 'facecolor': '#1a1a2e',
              'edgecolor': '#e94560'})

    # Legend
    legend_elements = [
        Patch(facecolor='#e94560', label='Nose Cap'),
        Patch(facecolor='#555555', label='Central Drum'),
        Patch(facecolor='#1a5276', label='Envelope (Ada FFI)'),
        Patch(facecolor='#333333', label='Gore Spokes'),
        Patch(facecolor='#222222', label='Flat Back'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=5,
        fontsize=9, facecolor='#1a1a2e', edgecolor='#0f3460',
        labelcolor='#8892b0', bbox_to_anchor=(0.5, 0.01))

    fig.suptitle('StellarOrion HIAD Topology Optimization — Before vs After\n'
                 'Both profiles computed in Ada via FFI | Optimized by Bayesian search',
        color='white', fontsize=14, fontweight='bold', y=0.97)

    plt.tight_layout(rect=(0, 0.05, 1, 0.93))
    out = Path(__file__).resolve().parent.parent / "optimization_comparison.png"
    plt.savefig(str(out), dpi=150, facecolor='#0a0a0f', bbox_inches='tight')
    print(f"Saved: {out}")
    if not (ada_ok and ada_opt_ok):
        print("[WARNING] Render written but Ada FFI cross-check FAILED — "
              "inspect the image and the WARNING above.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
