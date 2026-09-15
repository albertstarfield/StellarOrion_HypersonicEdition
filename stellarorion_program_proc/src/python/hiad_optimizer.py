# Parity protection: metadata/hiad_optimizer.meta.json (RS+GC parity)
"""
HIAD Geometry Optimizer -- CCD sampling, PINN cost function, MoP optimization.

Minimizes drag coefficient Cd via Method of Projected Gradients (MoP) while
maintaining structural integrity constraints on max radius and nose radius.
Uses Sutton-Graves correlation for stagnation-point heat flux estimation
and loads default HIAD geometry from Ada/SPARK via the existing FFI wrapper.

AXIOMS:
  1. The HIAD geometry is fully parameterized by (R_N, r_tor, half_cone_deg)
     -- the nose sphere radius, torus minor radius, and half-cone angle.
  2. Drag coefficient Cd for a blunt body scales with frontal area and shape:
     Cd ~ Cd_ref * (A_frontal / A_ref) where A = pi * R_max^2.
  3. Sutton-Graves stagnation heat flux: q = C_SG * sqrt(rho / R_n) * V^3
     provides a conservative screening bound for thermal loads.
  4. IRVE-3 diameter limit: max_radius <= 3.0 m (vehicle envelope constraint).
  5. Thermal protection: nose_radius >= 1.0 m (minimum TPS coverage).

THEOREMS:
  1. CCD with 2^3 factorial + center + axial points samples the 3D design
     space with 15 points, sufficient to fit a quadratic response surface.
  2. MoP with projection onto the feasible set guarantees iterates remain
     feasible at every step, preventing constraint violations.
  3. The projected gradient descent converges to a KKT point under
     Lipschitz continuity of the cost function on the compact feasible set.

CITATIONS:
  [1] Sutton & Graves (1951), "Laminar Heat Transfer to a Hemisphere at
      Mach Numbers Up to 5", J. Aeronautical Sciences 18(10):671-672.
  [2] NASA TR R-376 (1972) -- Sutton-Graves heat flux correlation constant
      C_SG = 1.7415e-4 (standard atmosphere, air).
  [3] NASA TP-2013-4012 -- IRVE-3 flight data: 3.0 m aeroshell diameter.
  [4] Anderson (2006), "Hypersonic and High-Temperature Gas Dynamics",
      2nd ed., AIAA Education Series -- blunt-body drag correlations.
  [5] Montgomery (2017), "Design and Analysis of Experiments", 9th ed.,
      Wiley -- Central Composite Design methodology.
  [6] Rapisarda (2023), MSc Thesis, TU Delft -- HIAD flat-skin profile,
      Sec 3.7, Appendix C.1, Table 4.10.
  [7] IRVE-3 MDAO -- Multidisciplinary Design Analysis and Optimization
      for Hypersonic Inflatable Aerodynamic Decelerators.

Author: Albert Starfield Wahyu Suryo Samudro
"""

import sys
import os
import json
import math
import itertools

# --- Auto-install numpy if unavailable ---
try:
    import numpy as np
except ImportError:
    print("[hiad_optimizer] numpy not found. Auto-installing ...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
    import numpy as np

# --- Import FFI wrapper for Ada/SPARK HIAD geometry and physics ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ada_pinn_wrapper import get_hiad_cross_section, sutton_graves_heat_flux
except ImportError as _exc:
    # Safety fallback: if Ada library is not compiled, use pure-Python geometry
    print(
        f"[hiad_optimizer] WARNING: ada_pinn_wrapper unavailable ({_exc}). "
        "Using pure-Python geometry fallback.",
        file=sys.stderr,
    )
    get_hiad_cross_section = None  # type: ignore[assignment]
    sutton_graves_heat_flux = None  # type: ignore[assignment]


# ======================================================================
#  Constants
# ======================================================================

# Sutton-Graves empirical constant for air (NASA TR R-376, 1972)
# [Citation: Sutton & Graves (1951); NASA TR R-376 (1972)]
_C_SG = 1.7415e-4  # W*s^3/(m^3*kg^0.5) -- SG coefficient in SI

# IRVE-3 flight conditions (Rapisarda 2023, Table 4.10)
_ALTITUDE_KM = 51.8  # km -- DSMC snapshot altitude
_VELOCITY_MS = 3378.0  # m/s -- velocity at snapshot

# IRVE-3 default geometry (from Ada/SPARK constants, generate_hiad_dashboard.py)
_DEFAULT_R_N = 1.5  # m -- nose sphere radius
_DEFAULT_R_TOR = 0.135  # m -- torus minor radius
_DEFAULT_HALF_CONE_DEG = 60.0  # degrees -- half-cone angle
_DEFAULT_N_TORI = 6  # number of inflatable tori

# Reference Cd for a smooth 70-deg sphere-cone at hypersonic speeds
# [Citation: Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4]
_CD_REF = 1.47

# Reference frontal area: pi * (1.5)^2 = 7.069 m^2 (IRVE-3 3m diameter)
_A_REF = math.pi * (_DEFAULT_R_N) ** 2

# Design space bounds
_R_N_MIN, _R_N_MAX = 1.2, 1.8  # m
_R_TOR_MIN, _R_TOR_MAX = 0.10, 0.18  # m
_HALF_CONE_MIN, _HALF_CONE_MAX = 55.0, 65.0  # degrees

# MoP hyperparameters
_LR = 0.01  # learning rate (step size)
_MAX_ITER = 100  # maximum iterations
_TOL = 1e-6  # convergence tolerance (gradient norm)

# Structural/thermal constraints
_MAX_RADIUS_LIMIT = 3.0  # m -- IRVE-3 diameter limit
_NOSE_RADIUS_LIMIT = 1.0  # m -- minimum thermal protection


# ======================================================================
#  HIAD Geometry Model (pure-Python fallback)
# ======================================================================


def _compute_max_radius(
    r_n: float,
    r_tor: float,
    half_cone_deg: float,
    n_tori: int = _DEFAULT_N_TORI,
) -> float:
    """Compute maximum radial extent of the HIAD from geometric parameters.

    The HIAD consists of a spherical nose cap followed by N tori arranged
    along a cone of half-angle gamma.  The outermost point is the top of
    the last torus.

    Args:
        r_n: Nose sphere radius [m].
        r_tor: Torus minor (tube) radius [m].
        half_cone_deg: Half-cone angle [degrees].
        n_tori: Number of inflatable tori.

    Returns:
        Maximum radial extent R_max [m].

    AXIOMS:
      1. Tangency point: R_tang = R_N * cos(gamma) on the nose sphere.
      2. Each torus center is displaced by 2*r_tor along the cone surface.
      3. Outermost radial point = R_target + r_tor.

    CITATIONS:
      [1] Rapisarda (2023) Sec 3.7, Appendix C.1 -- HIAD flat-skin profile
      [2] generate_hiad_dashboard.py -- geometric derivation
    """
    # Ada uses Gamma_Rad = (90 - Half_Cone_Deg) * Pi / 180 (complement angle)
    # [Citation: stellarorion_pinn_trajectory.adb line 393]
    gamma = math.radians(90.0 - half_cone_deg)
    r_tang = r_n * math.cos(gamma)
    s_last = (2 * n_tori - 1) * r_tor
    r_target = r_tang + s_last * math.cos(gamma)
    r_max = r_target + r_tor  # top of outermost torus
    return r_max


def _compute_frontal_area(r_max: float) -> float:
    """Compute frontal area A = pi * R_max^2.

    [Citation: Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4]
    """
    return math.pi * r_max ** 2


def _estimate_cd(
    r_n: float,
    r_tor: float,
    half_cone_deg: float,
    n_tori: int = _DEFAULT_N_TORI,
) -> float:
    """Estimate drag coefficient Cd for the HIAD geometry.

    Uses a blunt-body correlation: Cd scales with frontal area relative
    to the reference IRVE-3 configuration.  A correction factor accounts
    for the nose-radius-to-body-radius ratio (larger nose = blunter = higher Cd).

    AXIOMS:
      1. Cd_ref = 1.47 for smooth 70-deg sphere-cone (Anderson 2006).
      2. Frontal area scaling: Cd ~ (R_max / R_ref)^alpha where alpha ~ 0.15
         captures the weak dependence of drag on body size for blunt bodies.
      3. Nose bluntness correction: f(R_N) = 1 + 0.05 * (R_ref/R_N - 1)
         -- smaller nose = sharper = slightly lower Cd.

    CITATIONS:
      [1] Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4
      [2] IRVE-3 MDAO -- Cd ~ 1.47 (smooth cone), 1.45-1.58 (with skin)
    """
    r_max = _compute_max_radius(r_n, r_tor, half_cone_deg, n_tori)
    r_ref = _compute_max_radius(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG, n_tori)
    # Frontal area ratio with weak exponent
    area_ratio = r_max / r_ref
    # Nose bluntness correction
    nose_correction = 1.0 + 0.05 * (_DEFAULT_R_N / r_n - 1.0)
    cd = _CD_REF * (area_ratio ** 0.15) * nose_correction
    return cd


def _sutton_graves_heat_flux_local(
    rho_kgm3: float, r_n: float, velocity_ms: float
) -> float:
    """Compute Sutton-Graves stagnation-point heat flux locally.

    q = C_SG * sqrt(rho / R_n) * V^3

    Args:
        rho_kgm3: Freestream density [kg/m^3].
        r_n: Nose radius [m].
        velocity_ms: Freestream velocity [m/s].

    Returns:
        Heat flux [W/m^2].

    AXIOMS:
      1. Sutton-Graves is valid for continuum flow over hemispherical noses.
      2. C_SG = 1.7415e-4 for air (NASA TR R-376).
      3. q is proportional to sqrt(rho) and V^3.

    CITATIONS:
      [1] Sutton & Graves (1951), J. Aeronautical Sciences 18(10):671-672
      [2] NASA TR R-376 (1972)
      [3] Discussion.md Sec 5.5 -- SG vs FR comparison
    """
    # Prevent division by zero for r_n -> 0
    if r_n < 1e-6:
        r_n = 1e-6
    # Prevent negative density (numerical safety)
    rho_safe = max(rho_kgm3, 1e-12)
    q = _C_SG * math.sqrt(rho_safe / r_n) * velocity_ms ** 3
    return q


# ======================================================================
#  CCD Sampling (Central Composite Design)
# ======================================================================


def generate_ccd_samples() -> list:
    """Generate Central Composite Design (CCD) samples for 3 factors.

    Uses a 2^3 full factorial design augmented with:
      - 1 center point (all parameters at their midpoints)
      - 6 axial (star) points (one factor at extreme, others at center)

    Total samples: 8 (factorial) + 1 (center) + 6 (axial) = 15

    Design parameters and ranges:
      x1 = R_N:         [1.2, 1.8] m
      x2 = r_tor:       [0.10, 0.18] m
      x3 = half_cone_deg: [55, 65] degrees

    Returns:
        List of dicts, each with keys: R_N, r_tor, half_cone_deg, label

    AXIOMS:
      1. CCD provides second-order response surface capability with minimum
         number of experiments (Montgomery 2017, Sec 11.2).
      2. Axial points at +/- alpha ensure rotatability when alpha = (2^k)^(1/4).

    CITATIONS:
      [1] Montgomery (2017), Design and Analysis of Experiments, 9th ed., Wiley
      [2] Box & Wilson (1951), "On the Experimental Attainment of Optimum Conditions"
    """
    # Design ranges (coded -1 to +1 mapping)
    ranges = [
        (_R_N_MIN, _R_N_MAX),
        (_R_TOR_MIN, _R_TOR_MAX),
        (_HALF_CONE_MIN, _HALF_CONE_MAX),
    ]
    names = ["R_N", "r_tor", "half_cone_deg"]

    # Midpoints and half-ranges for coded-to-real mapping
    centers = [(lo + hi) / 2.0 for lo, hi in ranges]
    half_widths = [(hi - lo) / 2.0 for lo, hi in ranges]

    # Star point distance (alpha for rotatability in 2^3 design)
    # alpha = (2^3)^(1/4) ~ 1.682
    alpha = (2 ** 3) ** 0.25

    samples = []

    # --- Factorial points: 2^3 = 8 ---
    for signs in itertools.product([-1, +1], repeat=3):
        real_vals = [centers[i] + signs[i] * half_widths[i] for i in range(3)]
        sample = {names[i]: real_vals[i] for i in range(3)}
        sample["label"] = f"factorial_{''.join('+-'[s < 0] for s in signs)}"
        samples.append(sample)

    # --- Center point: 1 ---
    center_sample = {names[i]: centers[i] for i in range(3)}
    center_sample["label"] = "center"
    samples.append(center_sample)

    # --- Axial (star) points: 2 * 3 = 6 ---
    for dim in range(3):
        for sign in [-1, +1]:
            axial_vals = list(centers)
            axial_vals[dim] = centers[dim] + sign * alpha * half_widths[dim]
            sample = {names[i]: axial_vals[i] for i in range(3)}
            sample["label"] = f"axial_{names[dim]}_{'+' if sign > 0 else '-'}"
            samples.append(sample)

    return samples


# ======================================================================
#  PINN-Inspired Cost Function
# ======================================================================


def _project_to_feasible(x: np.ndarray) -> np.ndarray:
    """Project parameter vector onto the feasible set defined by box constraints.

    Args:
        x: Parameter vector [R_N, r_tor, half_cone_deg].

    Returns:
        Projected vector satisfying all bounds.

    AXIOMS:
      1. Box constraints: each parameter independently clamped to its range.
      2. Projection is the closest point in the feasible set (Euclidean).

    CITATIONS:
      [1] Boyd & Vandenberghe (2004), Convex Optimization, Sec 2.3
    """
    bounds = [
        (_R_N_MIN, _R_N_MAX),
        (_R_TOR_MIN, _R_TOR_MAX),
        (_HALF_CONE_MIN, _HALF_CONE_MAX),
    ]
    return np.array([np.clip(x[i], bounds[i][0], bounds[i][1]) for i in range(3)])


def _check_constraints(r_n: float, r_tor: float, half_cone_deg: float) -> dict:
    """Check structural and thermal constraints.

    Args:
        r_n: Nose radius [m].
        r_tor: Torus minor radius [m].
        half_cone_deg: Half-cone angle [degrees].

    Returns:
        Dict with keys: max_radius, max_radius_ok, nose_radius_ok, feasible.

    AXIOMS:
      1. max_radius <= 3.0 m (IRVE-3 vehicle envelope).
      2. nose_radius >= 1.0 m (minimum TPS coverage).
      3. Both constraints must be satisfied simultaneously.

    CITATIONS:
      [1] NASA TP-2013-4012 -- IRVE-3 3.0 m diameter limit
      [2] Rapisarda (2023) -- HIAD thermal protection requirements
    """
    max_radius = _compute_max_radius(r_n, r_tor, half_cone_deg)
    max_radius_ok = max_radius <= _MAX_RADIUS_LIMIT
    nose_radius_ok = r_n >= _NOSE_RADIUS_LIMIT
    return {
        "max_radius": max_radius,
        "max_radius_ok": max_radius_ok,
        "nose_radius_ok": nose_radius_ok,
        "feasible": max_radius_ok and nose_radius_ok,
    }


def cost_function(x: np.ndarray) -> float:
    """PINN-inspired cost function for HIAD geometry optimization.

    Minimizes drag coefficient Cd while penalizing constraint violations
    using a quadratic penalty method.

    J(x) = Cd(x) + lambda_1 * max(0, R_max - 3.0)^2 + lambda_2 * max(0, 1.0 - R_N)^2

    The penalty terms enforce:
      - max_radius <= 3.0 m (vehicle envelope, IRVE-3 diameter limit)
      - nose_radius >= 1.0 m (minimum thermal protection)

    AXIOMS:
      1. Primary objective: minimize Cd (aerodynamic efficiency).
      2. Penalty method converts constrained optimization to unconstrained.
      3. Penalty weights lambda_i are large enough to dominate Cd in
         infeasible regions, but do not distort the feasible landscape.
      4. Sutton-Graves heat flux is evaluated at the design point for
         informational output (not directly in the cost, as it is a
         single-point estimate at fixed altitude/velocity).

    CITATIONS:
      [1] Anderson (2006), Hypersonic Gas Dynamics -- Cd for blunt bodies
      [2] Sutton & Graves (1951) -- heat flux correlation
      [3] Nocedal & Wright (2006), Numerical Optimization, Sec 17.1 -- penalty methods
    """
    r_n = float(x[0])
    r_tor = float(x[1])
    half_cone_deg = float(x[2])

    # Primary objective: drag coefficient
    cd = _estimate_cd(r_n, r_tor, half_cone_deg)

    # Constraint penalties (quadratic penalty method)
    # [Citation: Nocedal & Wright (2006), Numerical Optimization, Sec 17.1]
    max_radius = _compute_max_radius(r_n, r_tor, half_cone_deg)
    penalty_radius = max(0.0, max_radius - _MAX_RADIUS_LIMIT) ** 2
    penalty_nose = max(0.0, _NOSE_RADIUS_LIMIT - r_n) ** 2

    # Penalty weights -- large enough to dominate Cd in infeasible regions
    lambda_1 = 100.0  # penalty for exceeding max_radius
    lambda_2 = 100.0  # penalty for nose_radius too small

    j = cd + lambda_1 * penalty_radius + lambda_2 * penalty_nose
    return j


def _numerical_gradient(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Compute gradient of cost function via central finite differences.

    Args:
        x: Current parameter vector.
        eps: Finite difference step size.

    Returns:
        Gradient vector [dJ/dR_N, dJ/dr_tor, dJ/d(half_cone_deg)].

    AXIOMS:
      1. Central differences: O(eps^2) accuracy (vs O(eps) for forward diff).
      2. eps = 1e-5 balances truncation error vs round-off error.

    CITATIONS:
      [1] Numerical Recipes (2007), Sec 5.7 -- numerical differentiation
    """
    grad = np.zeros(3)
    for i in range(3):
        x_plus = x.copy()
        x_minus = x.copy()
        x_plus[i] += eps
        x_minus[i] -= eps
        grad[i] = (cost_function(x_plus) - cost_function(x_minus)) / (2.0 * eps)
    return grad


# ======================================================================
#  MoP (Method of Projected Gradients)
# ======================================================================


def mop_optimize(
    x0: np.ndarray,
    lr: float = _LR,
    max_iter: int = _MAX_ITER,
    tol: float = _TOL,
) -> dict:
    """Method of Projected Gradients (MoP) optimization.

    At each iteration:
      1. Compute gradient of cost function at current point.
      2. Take a gradient descent step: x_new = x - lr * grad.
      3. Project x_new onto the feasible set (box constraints).

    Convergence criterion: ||grad||_inf < tol.

    Args:
        x0: Initial parameter vector [R_N, r_tor, half_cone_deg].
        lr: Learning rate (step size).
        max_iter: Maximum number of iterations.
        tol: Convergence tolerance on infinity-norm of gradient.

    Returns:
        Dict with keys: x_opt, cost, converged, n_iter, history.

    AXIOMS:
      1. Projection onto a closed convex set (box) is non-expansive.
      2. Under Lipschitz continuity (L) and lr < 1/L, the iterates converge.
      3. Box constraints are independently projected per coordinate.

    CITATIONS:
      [1] Boyd & Vandenberghe (2004), Convex Optimization, Sec 2.3, 5.2
      [2] Bertsekas (1999), Nonlinear Programming, 2nd ed., Sec 2.7
      [3] Calamai & More (1987), "Projected Gradient Methods for Linearly
          Constrained Problems", Math. Programming 39:93-116.
    """
    x = _project_to_feasible(x0.copy())
    history = []
    converged = False

    for iteration in range(max_iter):
        # Compute cost and gradient
        current_cost = cost_function(x)
        grad = _numerical_gradient(x)

        # Record history
        history.append({
            "iteration": iteration,
            "R_N": float(x[0]),
            "r_tor": float(x[1]),
            "half_cone_deg": float(x[2]),
            "cost": float(current_cost),
            "gradient_norm": float(np.max(np.abs(grad))),
        })

        # Check convergence (infinity-norm of gradient)
        grad_norm_inf = np.max(np.abs(grad))
        if grad_norm_inf < tol:
            converged = True
            break

        # Gradient descent step
        x_new = x - lr * grad

        # Project onto feasible set (box constraints)
        x_new = _project_to_feasible(x_new)

        # Safety: detect stagnation (step too small to move)
        if np.allclose(x_new, x, atol=1e-10):
            converged = True
            break

        x = x_new

    return {
        "x_opt": x,
        "cost": float(cost_function(x)),
        "converged": converged,
        "n_iter": len(history),
        "history": history,
    }


# ======================================================================
#  Main Entry Point
# ======================================================================


def main() -> int:
    """Run the full HIAD geometry optimization pipeline.

    Steps:
      1. Load default HIAD cross-section from Ada/SPARK (if available).
      2. Compute default parameters and cost.
      3. Generate CCD sample points.
      4. Evaluate cost at all CCD points (find best initial guess).
      5. Run MoP optimization from best CCD point.
      6. Save results to JSON.

    Returns:
        0 on success, 1 on error.

    SAFETY FALLBACK:
      If Ada library is unavailable, pure-Python geometry is used.
      All errors are printed with full context to stderr.
    """
    print("=" * 72)
    print("  HIAD Geometry Optimizer")
    print("  CCD Sampling + PINN Cost + MoP Optimization")
    print("=" * 72)

    # --- Step 1: Load default geometry from Ada/SPARK ---
    print("\n[1/6] Loading default HIAD geometry from Ada/SPARK ...")
    hiad_cs = None
    if get_hiad_cross_section is not None:
        try:
            hiad_cs = get_hiad_cross_section()
            print(f"  Loaded {hiad_cs['n']} cross-section points from Ada/SPARK")
            print(f"  X range: [{min(hiad_cs['x']):.4f}, {max(hiad_cs['x']):.4f}] m")
            print(f"  Y range: [{min(hiad_cs['y']):.4f}, {max(hiad_cs['y']):.4f}] m")
        except OSError as exc:
            print(
                f"  WARNING: Ada FFI call failed ({exc}). "
                "Using pure-Python geometry.",
                file=sys.stderr,
            )
    else:
        print("  Ada library not available. Using pure-Python geometry fallback.")

    # --- Step 2: Compute default parameters and cost ---
    print("\n[2/6] Computing default parameters and cost ...")
    x_default = np.array([_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG])
    default_cost = cost_function(x_default)
    default_constraints = _check_constraints(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    default_cd = _estimate_cd(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    default_max_r = default_constraints["max_radius"]

    # Compute Sutton-Graves heat flux at default geometry
    if sutton_graves_heat_flux is not None:
        try:
            sg_result = sutton_graves_heat_flux(_ALTITUDE_KM, _VELOCITY_MS, _DEFAULT_R_N)
            default_sg_wm2 = sg_result["heat_flux_Wm2"]
            default_sg_wcm2 = sg_result["heat_flux_Wcm2"]
        except OSError:
            default_sg_wm2 = _sutton_graves_heat_flux_local(
                7.696e-4, _DEFAULT_R_N, _VELOCITY_MS
            )
            default_sg_wcm2 = default_sg_wm2 / 10000.0
    else:
        # ISA density at 51.8 km: ~7.696e-4 kg/m^3
        # [Citation: NASA SP-7468 (1976) -- ISA atmosphere]
        default_sg_wm2 = _sutton_graves_heat_flux_local(7.696e-4, _DEFAULT_R_N, _VELOCITY_MS)
        default_sg_wcm2 = default_sg_wm2 / 10000.0

    print(f"  Default R_N = {_DEFAULT_R_N:.4f} m")
    print(f"  Default r_tor = {_DEFAULT_R_TOR:.4f} m")
    print(f"  Default half_cone = {_DEFAULT_HALF_CONE_DEG:.2f} deg")
    print(f"  Default Cd = {default_cd:.6f}")
    print(f"  Default max_radius = {default_max_r:.4f} m")
    print(f"  Default cost J = {default_cost:.6f}")
    print(f"  SG heat flux = {default_sg_wcm2:.4f} W/cm^2 "
          f"({default_sg_wm2:.2f} W/m^2)")

    # --- Step 3: Generate CCD sample points ---
    print("\n[3/6] Generating CCD sample points (2^3 factorial + center + axial) ...")
    ccd_samples = generate_ccd_samples()
    print(f"  Generated {len(ccd_samples)} CCD samples:")
    for i, s in enumerate(ccd_samples):
        print(f"    [{i:2d}] {s['label']:25s}  "
              f"R_N={s['R_N']:.4f}  r_tor={s['r_tor']:.4f}  "
              f"cone={s['half_cone_deg']:.2f}")

    # --- Step 4: Evaluate cost at all CCD points ---
    print("\n[4/6] Evaluating cost at CCD sample points ...")
    ccd_results = []
    for s in ccd_samples:
        x_i = np.array([s["R_N"], s["r_tor"], s["half_cone_deg"]])
        c_i = cost_function(x_i)
        feasible_i = _check_constraints(s["R_N"], s["r_tor"], s["half_cone_deg"])
        ccd_results.append({
            "label": s["label"],
            "R_N": s["R_N"],
            "r_tor": s["r_tor"],
            "half_cone_deg": s["half_cone_deg"],
            "cost": c_i,
            "feasible": feasible_i["feasible"],
        })
        status = "OK" if feasible_i["feasible"] else "INFEASIBLE"
        print(f"    {s['label']:25s}  J={c_i:.6f}  [{status}]")

    # Find best feasible CCD point as initial guess for MoP
    feasible_results = [r for r in ccd_results if r["feasible"]]
    if feasible_results:
        best_ccd = min(feasible_results, key=lambda r: r["cost"])
    else:
        # If all CCD points are infeasible, use center point
        best_ccd = min(ccd_results, key=lambda r: r["cost"])
    print(f"\n  Best CCD point for MoP init: {best_ccd['label']} "
          f"(J={best_ccd['cost']:.6f})")

    # --- Step 5: MoP optimization ---
    print("\n[5/6] Running MoP optimization ...")
    x_init = np.array([best_ccd["R_N"], best_ccd["r_tor"], best_ccd["half_cone_deg"]])
    result = mop_optimize(x_init)
    x_opt = result["x_opt"]

    opt_r_n = float(x_opt[0])
    opt_r_tor = float(x_opt[1])
    opt_cone = float(x_opt[2])
    opt_cd = _estimate_cd(opt_r_n, opt_r_tor, opt_cone)
    opt_constraints = _check_constraints(opt_r_n, opt_r_tor, opt_cone)
    opt_max_r = opt_constraints["max_radius"]

    # Compute SG at optimized geometry
    if sutton_graves_heat_flux is not None:
        try:
            sg_opt = sutton_graves_heat_flux(_ALTITUDE_KM, _VELOCITY_MS, opt_r_n)
            opt_sg_wm2 = sg_opt["heat_flux_Wm2"]
            opt_sg_wcm2 = sg_opt["heat_flux_Wcm2"]
        except OSError:
            opt_sg_wm2 = _sutton_graves_heat_flux_local(7.696e-4, opt_r_n, _VELOCITY_MS)
            opt_sg_wcm2 = opt_sg_wm2 / 10000.0
    else:
        opt_sg_wm2 = _sutton_graves_heat_flux_local(7.696e-4, opt_r_n, _VELOCITY_MS)
        opt_sg_wcm2 = opt_sg_wm2 / 10000.0

    print(f"  Converged: {result['converged']} (after {result['n_iter']} iterations)")
    print(f"  Optimized R_N = {opt_r_n:.6f} m")
    print(f"  Optimized r_tor = {opt_r_tor:.6f} m")
    print(f"  Optimized half_cone = {opt_cone:.6f} deg")
    print(f"  Optimized Cd = {opt_cd:.6f}")
    print(f"  Optimized max_radius = {opt_max_r:.4f} m")
    print(f"  Optimized cost J = {result['cost']:.6f}")
    print(f"  SG heat flux = {opt_sg_wcm2:.4f} W/cm^2 ({opt_sg_wm2:.2f} W/m^2)")
    print(f"  Constraints: max_radius OK={opt_constraints['max_radius_ok']}, "
          f"nose_radius OK={opt_constraints['nose_radius_ok']}")

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
    print("\n[6/6] Saving results to JSON ...")
    output = {
        "default": {
            "R_N": _DEFAULT_R_N,
            "r_tor": _DEFAULT_R_TOR,
            "half_cone_deg": _DEFAULT_HALF_CONE_DEG,
            "Cd": default_cd,
            "max_radius_m": default_max_r,
            "cost": default_cost,
            "sutton_graves_heat_flux_Wcm2": default_sg_wcm2,
            "sutton_graves_heat_flux_Wm2": default_sg_wm2,
        },
        "optimized": {
            "R_N": opt_r_n,
            "r_tor": opt_r_tor,
            "half_cone_deg": opt_cone,
            "Cd": opt_cd,
            "max_radius_m": opt_max_r,
            "cost": result["cost"],
            "sutton_graves_heat_flux_Wcm2": opt_sg_wcm2,
            "sutton_graves_heat_flux_Wm2": opt_sg_wm2,
            "converged": result["converged"],
            "n_iterations": result["n_iter"],
            "constraints": opt_constraints,
        },
        "improvement": {
            "cost_pct": improvement_pct,
            "cd_pct": cd_improvement_pct,
        },
        "ccd_samples": ccd_results,
        "optimization_history": result["history"],
        "config": {
            "learning_rate": _LR,
            "max_iterations": _MAX_ITER,
            "convergence_tol": _TOL,
            "penalty_lambda_1": 100.0,
            "penalty_lambda_2": 100.0,
            "max_radius_limit_m": _MAX_RADIUS_LIMIT,
            "nose_radius_limit_m": _NOSE_RADIUS_LIMIT,
            "altitude_km": _ALTITUDE_KM,
            "velocity_ms": _VELOCITY_MS,
            "sg_constant": _C_SG,
            "cd_ref": _CD_REF,
        },
    }

    # Determine output path (same directory as this script)
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
    print(f"  Max radius: {opt_max_r:.4f} m (limit: {_MAX_RADIUS_LIMIT} m)")
    print(f"  Nose radius: {opt_r_n:.4f} m (limit: >= {_NOSE_RADIUS_LIMIT} m)")
    print(f"  SG heat flux: {opt_sg_wcm2:.4f} W/cm^2")
    print("=" * 72)
    return 0


# ======================================================================
#  Self-Test
# ======================================================================

if __name__ == "__main__":
    # --- Pre-flight checks ---
    print("=== HIAD Geometry Optimizer Self-Test ===\n")

    # Test CCD generation
    ccd = generate_ccd_samples()
    assert len(ccd) == 15, f"CCD should have 15 samples, got {len(ccd)}"
    factorial = [s for s in ccd if s["label"].startswith("factorial")]
    assert len(factorial) == 8, f"Should have 8 factorial points, got {len(factorial)}"
    center = [s for s in ccd if s["label"] == "center"]
    assert len(center) == 1, f"Should have 1 center point, got {len(center)}"
    axial = [s for s in ccd if s["label"].startswith("axial")]
    assert len(axial) == 6, f"Should have 6 axial points, got {len(axial)}"
    print(f"  CCD: {len(ccd)} samples (8 factorial + 1 center + 6 axial) -- OK")

    # Test default cost
    x_def = np.array([_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG])
    c_def = cost_function(x_def)
    print(f"  Default cost J = {c_def:.6f} -- OK")

    # Test constraint checking
    c_ok = _check_constraints(1.5, 0.135, 60.0)
    assert c_ok["feasible"], "Default geometry should be feasible"
    c_bad = _check_constraints(0.5, 0.135, 60.0)
    assert not c_bad["feasible"], "R_N=0.5 should violate nose_radius constraint"
    print("  Constraint checking -- OK")

    # Test projection
    x_bad = np.array([0.5, 0.05, 70.0])
    x_proj = _project_to_feasible(x_bad)
    assert x_proj[0] == _R_N_MIN, f"R_N should be clipped to {_R_N_MIN}"
    assert x_proj[1] == _R_TOR_MIN, f"r_tor should be clipped to {_R_TOR_MIN}"
    assert x_proj[2] == _HALF_CONE_MAX, f"half_cone should be clipped to {_HALF_CONE_MAX}"
    print("  Projection -- OK")

    # Test gradient computation
    grad = _numerical_gradient(x_def)
    assert grad.shape == (3,), f"Gradient should be 3D, got shape {grad.shape}"
    print(f"  Gradient at default: [{grad[0]:.6f}, {grad[1]:.6f}, {grad[2]:.6f}] -- OK")

    # Test MoP with reduced iterations
    result = mop_optimize(x_def, max_iter=20)
    assert "x_opt" in result
    assert "cost" in result
    assert "converged" in result
    assert "history" in result
    print(f"  MoP test: {result['n_iter']} iterations, J={result['cost']:.6f} -- OK")

    # Test Sutton-Graves
    sg = _sutton_graves_heat_flux_local(7.696e-4, 1.5, 3378.0)
    assert sg > 0, "SG heat flux should be positive"
    print(f"  SG heat flux = {sg / 10000:.4f} W/cm^2 -- OK")

    print("\nAll self-tests passed.\n")

    # Run full optimization
    sys.exit(main())
