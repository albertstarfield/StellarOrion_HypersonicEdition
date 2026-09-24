# Parity protection: metadata/hiad_optimizer.meta.json (RS+GC parity)
"""
HIAD Geometry Optimizer -- Thin FFI wrapper calling Ada/SPARK.

All computation (CCD sampling, cost function) is delegated to Ada/SPARK via FFI.
Bayesian Optimization (GP surrogate + Matern 5/2 + EI acquisition) runs in
Python using scikit-learn, calling Ada FFI for cost function evaluations.
MoP (Method of Projected Gradients) is available via Ada FFI for comparison.

AXIOMS:
  1. The HIAD geometry is fully parameterized by (R_N, r_tor, half_cone_deg).
  2. All physics and optimization logic lives in Ada/SPARK.
  3. Python provides only the CLI entry point, JSON output, and the
     post-run diagnostic render (scripts/render_geometry_grid.py).

CITATIONS:
  [1] stellarorion_ffi.ads — C-compatible FFI layer for optimization
  [2] stellarorion_optimization.ads — Core optimization algorithms
  [3] Ada 2012 Reference Manual, Interfaces.C package
  [4] scripts/render_geometry_grid.py — 87-panel geometry diagnostic

Author: Albert Starfield Wahyu Suryo Samudro
"""

import sys
import os
import json
import subprocess

# --- Import FFI wrappers from ada_pinn_wrapper ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ada_pinn_wrapper import (  # noqa: E402
    estimate_cd,
    hiad_cost_function,
    generate_ccd_samples,
    run_mop_optimize,
    run_bayesian_optimize,
    sutton_graves_heat_flux,
    get_hiad_cross_section,
)


# ======================================================================
#  Constants (matching Ada/SPARK defaults from stellarorion_optimization)
# ======================================================================

# [Citation: stellarorion_optimization.ads — Default_R_N, Default_R_Tor, etc.]
_DEFAULT_R_N = 1.5            # m -- nose sphere radius
_DEFAULT_R_TOR = 0.135        # m -- torus minor radius
_DEFAULT_HALF_CONE_DEG = 60.0  # degrees -- half-cone angle

# IRVE-3 flight conditions (Rapisarda 2023, Table 4.10)
_ALTITUDE_KM = 51.8           # km -- DSMC snapshot altitude
_VELOCITY_MS = 3378.0         # m/s -- velocity at snapshot

# Structural/thermal constraints (matching Ada constants)
_MAX_RADIUS_LIMIT = 3.0       # m -- IRVE-3 diameter limit
_NOSE_RADIUS_LIMIT = 1.0      # m -- minimum thermal protection


# ======================================================================
#  Main Entry Point (thin: calls Ada FFI for all computation)
# ======================================================================


def main() -> int:
    """Run the full HIAD geometry optimization pipeline.

    All computation is delegated to Ada/SPARK via FFI.
    This function only handles CLI output, JSON serialization, and the
    step-7 diagnostic render (subprocess -> render_geometry_grid.py).

    Returns:
        0 on success (JSON written AND grid rendered), 1 on any failure
        (never 0 on error -- verbose errors go to stderr).
    """
    print("=" * 72)
    print("  HIAD Geometry Optimizer (Bayesian Optimization)")
    print("  CCD Sampling + PINN Cost + GP Surrogate + EI Acquisition")
    print("=" * 72)

    # --- Step 1: Load default geometry from Ada/SPARK ---
    print("\n[1/7] Loading default HIAD geometry from Ada/SPARK ...")
    try:
        hiad_cs = get_hiad_cross_section()
        print(f"  Loaded {hiad_cs['n']} cross-section points from Ada/SPARK")
        print(f"  X range: [{min(hiad_cs['x']):.4f}, {max(hiad_cs['x']):.4f}] m")
        print(f"  Y range: [{min(hiad_cs['y']):.4f}, {max(hiad_cs['y']):.4f}] m")
    except OSError as exc:
        print(f"  WARNING: Ada FFI call failed ({exc}).", file=sys.stderr)

    # --- Step 2: Compute default parameters and cost via Ada FFI ---
    print("\n[2/7] Computing default parameters and cost (via Ada FFI) ...")
    default_cd = estimate_cd(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    default_cost = hiad_cost_function(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)

    # Compute SG heat flux at default geometry
    try:
        sg_result = sutton_graves_heat_flux(_ALTITUDE_KM, _VELOCITY_MS, _DEFAULT_R_N)
        default_sg_wm2 = sg_result["heat_flux_Wm2"]
        default_sg_wcm2 = sg_result["heat_flux_Wcm2"]
    except OSError:
        # Fallback: local SG computation not available via Ada
        default_sg_wm2 = 0.0
        default_sg_wcm2 = 0.0

    print(f"  Default R_N = {_DEFAULT_R_N:.4f} m")
    print(f"  Default r_tor = {_DEFAULT_R_TOR:.4f} m")
    print(f"  Default half_cone = {_DEFAULT_HALF_CONE_DEG:.2f} deg")
    print(f"  Default Cd = {default_cd:.6f}")
    print(f"  Default cost J = {default_cost:.6f}")
    print(f"  SG heat flux = {default_sg_wcm2:.4f} W/cm^2 "
          f"({default_sg_wm2:.2f} W/m^2)")

    # --- Step 3: Generate CCD sample points via Ada FFI ---
    print("\n[3/7] Generating CCD sample points (via Ada FFI) ...")
    ccd_samples = generate_ccd_samples()
    print(f"  Generated {len(ccd_samples)} CCD samples:")
    for i, s in enumerate(ccd_samples):
        print(f"    [{i:2d}] {s['label']:25s}  "
              f"R_N={s['R_N']:.4f}  r_tor={s['r_tor']:.4f}  "
              f"cone={s['half_cone_deg']:.2f}")

    # --- Step 4: Evaluate cost at all CCD points via Ada FFI ---
    print("\n[4/7] Evaluating cost at CCD sample points (via Ada FFI) ...")
    ccd_results = []
    for s in ccd_samples:
        c_i = hiad_cost_function(s["R_N"], s["r_tor"], s["half_cone_deg"])
        ccd_results.append({
            "label": s["label"],
            "R_N": s["R_N"],
            "r_tor": s["r_tor"],
            "half_cone_deg": s["half_cone_deg"],
            "cost": c_i,
        })
        print(f"    {s['label']:25s}  J={c_i:.6f}")

    # Find best CCD point as initial guess for BO
    best_ccd = min(ccd_results, key=lambda r: r["cost"])
    print(f"\n  Best CCD point: {best_ccd['label']} (J={best_ccd['cost']:.6f})")

    # --- Step 5: Bayesian Optimization via GP surrogate ---
    print("\n[5/7] Running Bayesian Optimization (GP surrogate + EI) ...")
    result = run_bayesian_optimize(
        hiad_cost_function, n_initial=20, n_iter=50, xi=0.01, seed=42,
    )
    opt_r_n, opt_r_tor, opt_cone = result["x_opt"]
    opt_cd = estimate_cd(opt_r_n, opt_r_tor, opt_cone)

    # Compute SG at optimized geometry
    try:
        sg_opt = sutton_graves_heat_flux(_ALTITUDE_KM, _VELOCITY_MS, opt_r_n)
        opt_sg_wm2 = sg_opt["heat_flux_Wm2"]
        opt_sg_wcm2 = sg_opt["heat_flux_Wcm2"]
    except OSError:
        opt_sg_wm2 = 0.0
        opt_sg_wcm2 = 0.0

    print(f"  Best cost: {result['cost']:.6f} (after {result['n_evals']} evaluations)")
    print(f"  Optimized R_N = {opt_r_n:.6f} m")
    print(f"  Optimized r_tor = {opt_r_tor:.6f} m")
    print(f"  Optimized half_cone = {opt_cone:.6f} deg")
    print(f"  Optimized Cd = {opt_cd:.6f}")
    print(f"  Optimized cost J = {result['cost']:.6f}")
    print(f"  SG heat flux = {opt_sg_wcm2:.4f} W/cm^2 ({opt_sg_wm2:.2f} W/m^2)")

    # Improvement percentage
    if default_cost > 0:
        improvement_pct = ((default_cost - result["cost"]) / default_cost) * 100.0
    else:
        improvement_pct = 0.0
    print(f"\n  Cost improvement: {improvement_pct:+.4f}%")
    if default_cd > 0:
        cd_improvement_pct = ((default_cd - opt_cd) / default_cd) * 100.0
    else:
        cd_improvement_pct = 0.0
    print(f"  Cd improvement: {cd_improvement_pct:+.4f}%")

    # --- Step 6: Save results to JSON ---
    print("\n[6/7] Saving results to JSON ...")
    output = {
        "default": {
            "R_N": _DEFAULT_R_N,
            "r_tor": _DEFAULT_R_TOR,
            "half_cone_deg": _DEFAULT_HALF_CONE_DEG,
            "Cd": default_cd,
            "cost": default_cost,
            "sutton_graves_heat_flux_Wcm2": default_sg_wcm2,
            "sutton_graves_heat_flux_Wm2": default_sg_wm2,
        },
        "optimized": {
            "R_N": opt_r_n,
            "r_tor": opt_r_tor,
            "half_cone_deg": opt_cone,
            "Cd": opt_cd,
            "cost": result["cost"],
            "sutton_graves_heat_flux_Wcm2": opt_sg_wcm2,
            "sutton_graves_heat_flux_Wm2": opt_sg_wm2,
            "n_evaluations": result["n_evals"],
        },
        "improvement": {
            "cost_pct": improvement_pct,
            "cd_pct": cd_improvement_pct,
        },
        "ccd_samples": ccd_results,
        # AXIOMS: run_bayesian_optimize() contract returns "history" -- the full
        # evaluation log (20 Latin-Hypercube initial + 50 BO iterations = 70 pts).
        # THEORIES: persisting it lets render_bo_3d_plot.py rebuild the 3D scatter,
        # GP surrogate slices, and convergence curve without re-running the optimizer.
        # APPLICATIONS: direct key access (not .get) so a broken contract raises
        # loudly instead of silently writing an empty history (no silent failure).
        # [Citation: ada_pinn_wrapper.py run_bayesian_optimize — returns history]
        "history": result["history"],
        "config": {
            "source": "Bayesian Optimization (GP surrogate + EI acquisition)",
            "algorithm": "Bayesian Optimization",
            "surrogate": "Gaussian Process (Matern 5/2 kernel)",
            "acquisition": "Expected Improvement (xi=0.01)",
            "initial_sampling": "Latin Hypercube (n=20)",
            "bo_iterations": 50,
        },
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "hiad_optimization_results.json")
    # nosec: S305 -- JSON serialization of computed optimization data
    with open(output_path, "w") as fh:  # nosec: S305
        json.dump(output, fh, indent=2)
    print(f"  Results saved to: {output_path}")

    # --- Summary ---
    print("\n" + "=" * 72)
    print("  OPTIMIZATION SUMMARY")
    print("=" * 72)
    print(f"  Default  Cd = {default_cd:.6f}  J = {default_cost:.6f}")
    print(f"  Optimized Cd = {opt_cd:.6f}  J = {result['cost']:.6f}")
    print(f"  Improvement: {improvement_pct:+.4f}% (cost), {cd_improvement_pct:+.4f}% (Cd)")
    print(f"  Evaluations: {result['n_evals']} (20 initial LHD + 50 BO iterations)")
    print(f"  SG heat flux: {opt_sg_wcm2:.4f} W/cm^2")
    print("=" * 72)

    # --- Step 7: Render the 87-panel geometry grid (diagnostic figure) ---
    # AXIOMS: the grid is pure post-processing of the JSON just written --
    # it must never re-run the optimizer (render_geometry_grid A4).
    # THEORIES: a missing/broken renderer is a broken checkout, not a soft
    # skip -- fail loudly with full child stderr (no silent degradation).
    # APPLICATIONS: subprocess with timeout; echo child output; return 1 on
    # any non-zero child exit or launch failure.
    # [Citation: scripts/render_geometry_grid.py main() exit-code contract]
    print("\n[7/7] Rendering 87-panel HIAD geometry grid ...")
    # Path: src/python/hiad_optimizer.py -> ../../scripts/render_geometry_grid.py
    grid_script = os.path.abspath(os.path.join(
        script_dir, os.pardir, os.pardir, "scripts",
        "render_geometry_grid.py",
    ))
    if not os.path.isfile(grid_script):
        print(
            f"ERROR: grid renderer not found: {grid_script}\n"
            f"  Cause: scripts/render_geometry_grid.py missing from checkout.\n"
            f"  Fix:   restore the file from version control.",
            file=sys.stderr,
        )
        return 1
    try:
        proc = subprocess.run(
            [sys.executable, grid_script],
            capture_output=True, text=True, timeout=600, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"ERROR: failed to launch grid renderer: {exc!r}\n"
            f"  Script: {grid_script}",
            file=sys.stderr,
        )
        return 1
    # Echo child output so the operator sees every renderer message.
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        print(
            f"ERROR: render_geometry_grid.py exited with code "
            f"{proc.returncode}\n"
            f"  JSON results were still saved to: {output_path}",
            file=sys.stderr,
        )
        return 1
    print("  Geometry grid rendered successfully.")
    return 0


# ======================================================================
#  Self-Test
# ======================================================================

if __name__ == "__main__":
    print("=== HIAD Geometry Optimizer Self-Test (Ada/SPARK FFI) ===\n")

    # Test CCD generation via Ada FFI
    ccd = generate_ccd_samples()
    assert len(ccd) == 15, f"CCD should have 15 samples, got {len(ccd)}"
    factorial = [s for s in ccd if s["label"].startswith("factorial")]
    assert len(factorial) == 8, f"Should have 8 factorial points, got {len(factorial)}"
    center = [s for s in ccd if s["label"] == "center"]
    assert len(center) == 1, f"Should have 1 center point, got {len(center)}"
    axial = [s for s in ccd if s["label"].startswith("axial")]
    assert len(axial) == 6, f"Should have 6 axial points, got {len(axial)}"
    print(f"  CCD: {len(ccd)} samples (8 factorial + 1 center + 6 axial) -- OK")

    # Test default cost via Ada FFI
    c_def = hiad_cost_function(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    print(f"  Default cost J = {c_def:.6f} -- OK")

    # Test estimate_cd via Ada FFI
    cd_val = estimate_cd(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    assert cd_val > 0, "Cd should be positive"
    print(f"  Default Cd = {cd_val:.6f} -- OK")

    # Test MoP optimization via Ada FFI (still available for comparison)
    result = run_mop_optimize((_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG),
                               max_iter=20)
    assert "x_opt" in result
    assert "cost" in result
    assert "converged" in result
    print(f"  MoP test: {result['n_iter']} iterations, J={result['cost']:.6f} -- OK")

    # Test Bayesian Optimization (small run for self-test)
    bo_result = run_bayesian_optimize(hiad_cost_function, n_initial=10, n_iter=5, seed=0)
    assert "x_opt" in bo_result
    assert "cost" in bo_result
    assert "n_evals" in bo_result
    print(f"  BO test: {bo_result['n_evals']} evals, J={bo_result['cost']:.6f} -- OK")

    print("\nAll self-tests passed.\n")

    # Run full optimization
    sys.exit(main())
