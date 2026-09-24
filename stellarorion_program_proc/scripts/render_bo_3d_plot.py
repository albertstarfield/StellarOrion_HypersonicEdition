#!/usr/bin/env python3
"""
================================================================================
SCRIPT: render_bo_3d_plot.py — Bayesian Optimization 3D Diagnostic Figure
================================================================================

Generates bo_optimization_3d.png with three panels:

  A (top-left)  3D scatter of ALL evaluated geometries in
                (R_N, r_tor, half_cone_deg) space, colored by cost J:
                  CCD samples ....... open circles
                  LHD initial ....... filled triangles
                  BO iterations ..... filled circles
                  Optimum ........... red star
                  IRVE-3 default .... diamond
  B (bottom row) GP surrogate (Matern 5/2) refit on the 70-point history,
                shown as 2D slices at the optimized half-cone angle:
                  left  ... posterior mean mu(x)
                  right ... posterior std  sigma(x)  (epistemic uncertainty)
  C (top-right) Convergence: raw evaluated cost + best-so-far curve,
                with a marker at the LHD -> BO phase boundary.

DATA SOURCE:
  src/python/hiad_optimization_results.json — written by hiad_optimizer.py;
  the "history" key holds the full 70-point evaluation log (20 LHD + 50 BO).

AXIOMS:
  A1: The optimizer minimizes J(x); lower is better everywhere in this figure.
  A2: history contains exactly the points the GP+EI loop observed (n=70).
  A3: Bounds are the same _BOUNDS the optimizer used (ada_pinn_wrapper).
  A4: A 3D domain cannot be drawn as a surface — slices are the only honest
      way to visualize a 3D surrogate in 2D (fix one coordinate, vary two).

THEORIES:
  T1: From A1+A2: coloring by J with a log norm is valid because evaluated
      costs span ~1.44 (basin) to ~1367 (geometry-penalized corners),
      a span > 900x — a linear norm would crush the basin (see cost_norm A1).
  T2: From A4: fixing half_cone_deg = optimized value yields two informative
      2D slices (mu and sigma) that share the same projection as panel A.

APPLICATIONS:
  This script is the executable proof of T1/T2: every panel is derived from
  the persisted history, never re-running the optimizer.

CITATIONS:
  [1] Jones et al. (1998), Efficient Global Optimization — BO + EI
  [2] Rasmussen & Williams (2006), Gaussian Processes for Machine Learning
  [3] McKay et al. (1979), Technometrics 21(2) — Latin Hypercube
  [4] ada_pinn_wrapper.py run_bayesian_optimize — history contract
  [5] render_optimization_comparison.py — dark-theme / output-path precedent
  [6] matplotlib 3.11 docs — https://matplotlib.org/stable/api/

Author: Albert Starfield Wahyu Suryo Samudro
"""

import json
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & imports (headless-safe backend before pyplot)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent                      # stellarorion_program_proc
_SRC_PYTHON = _PROJECT_ROOT / "src" / "python"
_RESULTS_JSON = _SRC_PYTHON / "hiad_optimization_results.json"
_OUTPUT_PNG = _PROJECT_ROOT / "bo_optimization_3d.png"

import matplotlib

matplotlib.use("Agg")  # headless-safe: render off-screen, only savefig matters
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm, Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import MaxNLocator
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

# Dark theme — matches render_optimization_comparison.py precedent [5]
_BG = "#0a0a0f"
_PANEL = "#1a1a2e"
_TEXT = "#8892b0"
_ACCENT = "#e94560"
_DIM = "#555555"
_EDGE = "#0f3460"

# Fallback bounds mirroring ada_pinn_wrapper._BOUNDS (A3). Used ONLY if the
# Ada FFI import fails; a loud warning is printed whenever this path runs.
_FALLBACK_BOUNDS = [
    (0.5, 3.0),    # R_N — nose radius [m]
    (0.05, 0.5),   # r_tor — torus radius [m]
    (40.0, 80.0),  # half_cone_deg — half-cone angle [deg]
]

_REQUIRED_HISTORY_KEYS = ("iteration", "R_N", "r_tor", "half_cone_deg", "cost", "type")
_REQUIRED_TOP_KEYS = ("history", "ccd_samples", "default", "optimized")


# ===========================================================================
# FUNCTION: load_results
# ===========================================================================
#
# AXIOMS:
#   A1: hiad_optimizer.py writes a JSON object with the keys in
#       _REQUIRED_TOP_KEYS (contract since the history-persistence patch).
#   A2: Every history entry carries _REQUIRED_HISTORY_KEYS.
# THEORIES:
#   T1: From A1+A2: validating keys up front converts silent KeyError/NaN
#       plotting failures into one verbose, actionable error message.
# APPLICATIONS:
#   Explicit if/raise checks — no bare except, no sentinel None returns.
# CITATIONS:
#   [1] hiad_optimizer.py output dict — history + ccd_samples contract
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(H) key scan, H = history length (~70)
#   CPU Time: <1 ms for H=70 (pure dict traversal)
#   WCET: 5 ms including JSON decode of a ~50 kB file (10x margin)
#   Space Complexity: O(H) — the decoded history list
#   Hardware Assumptions: any CPU; file on local FS (no network)
# ===========================================================================
def load_results(json_path: Path) -> dict:
    """Load and validate hiad_optimization_results.json.

    Parameters:
        json_path -- path to the optimizer output JSON

    Returns:
        dict with at least keys: history, ccd_samples, default, optimized

    Raises:
        FileNotFoundError -- JSON does not exist (safety fallback: never
            proceed with missing data — Murphy: the file WILL be missing
            the first time someone runs this on a fresh clone)
        TypeError -- JSON top-level or history entry has the wrong type
            (TRY004: type mismatch, not a value problem)
        ValueError -- JSON malformed, or required keys/entry fields absent
    """
    if not json_path.is_file():
        raise FileNotFoundError(
            f"Optimizer results not found: {json_path}\n"
            f"  Cause: hiad_optimizer.py has not been run (or was run "
            f"elsewhere).\n"
            f"  Fix:   /opt/homebrew/bin/python3 { _SRC_PYTHON / 'hiad_optimizer.py' }"
        )
    try:
        with open(json_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Malformed JSON in {json_path}: {exc}\n"
            f"  Cause: truncated/partial write (optimizer killed mid-save?)\n"
            f"  Fix:   re-run hiad_optimizer.py"
        ) from exc

    if not isinstance(data, dict):
        raise TypeError(f"Expected top-level object in {json_path}, "
                        f"got {type(data).__name__}")

    missing = [k for k in _REQUIRED_TOP_KEYS if k not in data]
    if missing:
        raise ValueError(
            f"Missing required key(s) {missing} in {json_path}\n"
            f"  Present keys: {sorted(data.keys())}\n"
            f"  Cause: JSON written by an unpatched hiad_optimizer.py\n"
            f"  Fix:   re-run the patched hiad_optimizer.py"
        )

    history = data["history"]
    if not isinstance(history, list) or not history:
        raise ValueError(
            f"'history' must be a non-empty list, got "
            f"{type(history).__name__} len="
            f"{len(history) if isinstance(history, list) else 'n/a'}"
        )
    for i, entry in enumerate(history):
        if not isinstance(entry, dict):
            raise TypeError(f"history[{i}] is {type(entry).__name__}, not dict")
        lack = [k for k in _REQUIRED_HISTORY_KEYS if k not in entry]
        if lack:
            raise ValueError(
                f"history[{i}] missing keys {lack}; entry={entry}"
            )
    return data


# ===========================================================================
# FUNCTION: get_bounds
# ===========================================================================
#
# AXIOMS:
#   A1: The plot domain MUST equal the optimizer domain (else slices lie).
#   A2: ada_pinn_wrapper._BOUNDS is the single source of truth (A3 of module).
# THEORIES:
#   T1: From A1: importing _BOUNDS is preferred; hardcoding is a fallback
#       that must be flagged loudly so drift is never silent.
# APPLICATIONS:
#   try-import -> fallback constants + warning print (no silent degradation).
# CITATIONS:
#   [1] ada_pinn_wrapper.py:494-498 — _BOUNDS definition
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(1) after import (3 tuples)
#   CPU Time: ~5 ms first call (ctypes dylib load), ~0 after module cache
#   WCET: 500 ms if dylib cold-loads from disk
#   Space Complexity: O(1) — 3 bound pairs
#   Hardware Assumptions: macOS arm64, libstellarorion_pinn.dylib present
# ===========================================================================
def get_bounds() -> list:
    """Return the 3D parameter bounds used by the optimizer.

    Returns:
        list of 3 (lo, hi) tuples for (R_N, r_tor, half_cone_deg)

    Raises:
        nothing — falls back to _FALLBACK_BOUNDS with a printed warning if
        the Ada FFI module cannot be imported (safety fallback).
    """
    sys.path.insert(0, str(_SRC_PYTHON))
    try:
        from ada_pinn_wrapper import _BOUNDS  # single source of truth [1]
        bounds = list(_BOUNDS)
        print(f"  Bounds from Ada FFI wrapper: {bounds}")
        return bounds
    except OSError as exc:
        # dylib missing/unloadable — plot can still proceed with fallback,
        # but the operator MUST see this (verbose error reporting).
        print(
            f"WARNING: Ada FFI unavailable ({exc}).\n"
            f"  Cause: libstellarorion_pinn.dylib not found/loadable.\n"
            f"  Effect: using hardcoded _FALLBACK_BOUNDS — if Ada bounds\n"
            f"          ever change, this plot will silently drift.\n"
            f"  Fix:   alr exec -- gprbuild -P stellarorion_pinn_lib.gpr -f",
            file=sys.stderr,
        )
        return list(_FALLBACK_BOUNDS)


# ===========================================================================
# FUNCTION: fit_gp_surrogate
# ===========================================================================
#
# AXIOMS:
#   A1: The optimizer's GP is ConstantKernel * Matern(nu=2.5), normalize_y,
#       alpha=1e-6, n_restarts_optimizer=5 (ada_pinn_wrapper L616-623).
#   A2: Refitting on the SAME 70 points with the SAME kernel reproduces the
#       surrogate family the acquisition function actually used.
# THEORIES:
#   T1: From A1+A2: any other kernel would visualize a surrogate the
#       optimizer never queried — a lie. So we mirror the config exactly.
#   T2: GP fit may emit ConvergenceWarnings (length-scale at bound); these
#       are informational, not fatal — fit result is still usable.
# APPLICATIONS:
#   try/except around fit: failure re-raises with full traceback context so
#   main() can annotate the figure instead of exiting blank (no silent fail).
# CITATIONS:
#   [1] Rasmussen & Williams (2006) — GP regression
#   [2] ada_pinn_wrapper.py:616-624 — kernel + GP constructor
#   [3] https://scikit-learn.org/stable/modules/gaussian_process.html
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(H^3) Cholesky, H=70 -> ~3.4e5 flops/rep
#   CPU Time: 50-300 ms typical (5 L-BFGS restarts x ~40 iters)
#   WCET: 3 s if every restart hits max_iter (does not abort the plot)
#   Space Complexity: O(H^2) kernel matrix = 70x70 doubles ≈ 39 kB
#   Hardware Assumptions: CPU-only sklearn (no GPU needed at H=70)
# ===========================================================================
def fit_gp_surrogate(history: list, bounds: list) -> GaussianProcessRegressor:
    """Refit the BO Gaussian Process on the persisted evaluation history.

    Parameters:
        history -- list of dicts with R_N, r_tor, half_cone_deg, cost
        bounds  -- list of (lo, hi) per dim (used only for validation)

    Returns:
        fitted GaussianProcessRegressor ready for predict(..., return_std=True)

    Raises:
        ValueError -- history empty or dimension mismatch vs bounds
        RuntimeError -- sklearn fit failed (full traceback attached)
    """
    if not history:
        raise ValueError("fit_gp_surrogate: history is empty — nothing to fit")
    n_dims = len(bounds)
    X = np.array(
        [[e["R_N"], e["r_tor"], e["half_cone_deg"]] for e in history],
        dtype=float,
    )
    y = np.array([e["cost"] for e in history], dtype=float)
    if X.shape[1] != n_dims:
        raise ValueError(
            f"Dimension mismatch: history has {X.shape[1]} columns, "
            f"bounds has {n_dims}"
        )
    if not np.all(np.isfinite(X)) or not np.all(np.isfinite(y)):
        bad_x = int(np.sum(~np.isfinite(X)))
        bad_y = int(np.sum(~np.isfinite(y)))
        raise ValueError(
            f"Non-finite values in history: {bad_x} in X, {bad_y} in y"
        )

    # Mirror optimizer kernel exactly (T1) [1][2][3]
    kernel = (
        ConstantKernel(1.0, constant_value_bounds=(1e-3, 1e3))
        * Matern(
            length_scale=[1.0] * n_dims,
            length_scale_bounds=[(1e-3, 1e3)] * n_dims,
            nu=2.5,
        )
    )
    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=5,
        normalize_y=True,
        alpha=1e-6,
    )
    try:
        gp.fit(X, y)
    except Exception as exc:
        raise RuntimeError(
            f"GP fit failed on {X.shape[0]} points: {exc!r}\n"
            f"  Kernel: {kernel}\n"
            f"  y range: [{y.min():.4f}, {y.max():.4f}]"
        ) from exc
    print(f"  GP fitted: {X.shape[0]} pts, kernel={gp.kernel_}")
    return gp


# ===========================================================================
# FUNCTION: cost_norm
# ===========================================================================
#
# AXIOMS:
#   A1: Observed costs span >900x (worst geometry-penalized corner ~1367
#       vs basin ~1.44; CCD-only tail reaches ~38).
# THEORIES:
#   T1: From A1: a linear norm crushes the basin into one color band;
#       LogNorm resolves both the basin and the exploration tail.
#   T2: If any cost <= 0 the log norm is undefined -> fall back to linear
#       and WARN (never emit NaN colormaps silently).
# APPLICATIONS:
#   explicit positivity check with printed warning + linear fallback.
# CITATIONS:
#   [1] https://matplotlib.org/stable/api/_as_gen/matplotlib.colors.LogNorm.html
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(N) min/max scan
#   CPU Time: <0.1 ms for N<=100
#   WCET: 1 ms
#   Space Complexity: O(1)
# ===========================================================================
def cost_norm(costs: np.ndarray) -> Normalize:
    """Build a color normalization for cost values (log when safe).

    Parameters:
        costs -- 1D array of positive cost values

    Returns:
        matplotlib Normalize instance (LogNorm if all costs > 0)
    """
    cmin, cmax = float(np.min(costs)), float(np.max(costs))
    if cmin > 0.0 and cmax > cmin:
        return LogNorm(vmin=cmin, vmax=cmax)
    print(
        f"WARNING: costs not strictly positive/finite-spread "
        f"(min={cmin}, max={cmax}) — using linear norm.",
        file=sys.stderr,
    )
    return Normalize(vmin=cmin, vmax=max(cmax, cmin + 1e-9))


# ===========================================================================
# FUNCTION: plot_scatter_3d  (PANEL A)
# ===========================================================================
#
# AXIOMS:
#   A1: Each history entry is one point in the 3D design space (A2 module).
#   A2: CCD samples live in the same 3D space (same units/bounds).
#   A3: Default and optimum are specific points in that space.
# THEORIES:
#   T1: Marker shape encodes PHASE (CCD/LHD/BO); color encodes COST —
#       two orthogonal channels, so both are readable at once.
# APPLICATIONS:
#   three scatter calls + two singleton markers + shared LogNorm colorbar.
# CITATIONS:
#   [1] render_optimization_comparison.py — 3D styling precedent
#   [2] matplotlib mplot3d — https://matplotlib.org/stable/api/
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(N) marker emission, N<=85
#   CPU Time: 20-80 ms (Agg rasterizer)
#   WCET: 400 ms on a cold font cache
#   Space Complexity: O(N)
#   Hardware Assumptions: Agg software rendering (no GPU required)
# ===========================================================================
def plot_scatter_3d(
    ax,
    history: list,
    ccd: list,
    default: dict,
    optimized: dict,
    norm: Normalize,
) -> ScalarMappable:
    """Draw panel A: 3D scatter of CCD + LHD + BO evaluations.

    Parameters:
        ax        -- matplotlib 3D axes
        history   -- 70-entry evaluation log (dicts with type in LHD/BO)
        ccd       -- CCD sample list (dicts with label + cost)
        default   -- IRVE-3 baseline dict (R_N, r_tor, half_cone_deg)
        optimized -- optimum dict (R_N, r_tor, half_cone_deg, cost)
        norm      -- shared color normalization for cost

    Returns:
        ScalarMappable for the figure-level colorbar

    Raises:
        ValueError -- empty history (safety fallback: refuse blank panel)
    """
    if not history:
        raise ValueError("plot_scatter_3d: history empty — refusing blank panel")

    cmap = plt.get_cmap("turbo")

    # --- CCD design points: open circles, edge color = cost (T1) ---
    if ccd:
        cx = [s["R_N"] for s in ccd]
        cy = [s["r_tor"] for s in ccd]
        cz = [s["half_cone_deg"] for s in ccd]
        cc = [s["cost"] for s in ccd]
        ax.scatter(
            cx, cy, cz, c=cc, cmap=cmap, norm=norm,
            marker="o", s=48, linewidths=1.2, depthshade=True,
            edgecolors=cmap(norm(np.array(cc))),  # colored rim
            facecolors="none", label=f"CCD ({len(ccd)})",
        )
    else:
        print("WARNING: no CCD samples in JSON — panel A omits CCD layer.",
              file=sys.stderr)

    # --- LHD initial design: filled triangles ---
    lhd = [e for e in history if e["type"] == "initial"]
    bo = [e for e in history if e["type"] == "bo"]
    if not lhd and not bo:
        raise ValueError(
            f"history has neither 'initial' nor 'bo' entries; "
            f"types seen: {sorted({e['type'] for e in history})}"
        )

    if lhd:
        ax.scatter(
            [e["R_N"] for e in lhd],
            [e["r_tor"] for e in lhd],
            [e["half_cone_deg"] for e in lhd],
            c=[e["cost"] for e in lhd], cmap=cmap, norm=norm,
            marker="^", s=55, depthshade=True,
            label=f"LHD initial ({len(lhd)})",
        )

    # --- BO proposals: filled circles ---
    if bo:
        ax.scatter(
            [e["R_N"] for e in bo],
            [e["r_tor"] for e in bo],
            [e["half_cone_deg"] for e in bo],
            c=[e["cost"] for e in bo], cmap=cmap, norm=norm,
            marker="o", s=36, depthshade=True, linewidths=0.4,
            edgecolors="black",
            label=f"BO iteration ({len(bo)})",
        )

    # --- Optimum (red star) & default (diamond) ---
    ax.scatter(
        [optimized["R_N"]], [optimized["r_tor"]], [optimized["half_cone_deg"]],
        marker="*", s=260, color=_ACCENT, edgecolors="white",
        linewidths=0.8, depthshade=False,
        label=f"Optimum J={optimized['cost']:.3f}", zorder=5,
    )
    ax.scatter(
        [default["R_N"]], [default["r_tor"]], [default["half_cone_deg"]],
        marker="D", s=70, color=_TEXT, edgecolors="white",
        linewidths=0.8, depthshade=False,
        label=f"Default J={default['cost']:.3f}", zorder=5,
    )

    # --- Axes styling (precedent [1]) ---
    ax.set_xlabel("R_N (nose radius) [m]", color=_TEXT, fontsize=9)
    ax.set_ylabel("r_tor (torus radius) [m]", color=_TEXT, fontsize=9)
    ax.set_zlabel("half-cone [deg]", color=_TEXT, fontsize=9)
    ax.set_title(
        "A — Evaluated geometries (color = cost J, log scale)",
        color="white", fontsize=11, fontweight="bold", pad=8,
    )
    ax.tick_params(colors=_DIM, labelsize=7)
    # Cap z-ticks: half-cone range 40–80 deg would otherwise crowd labels
    ax.zaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.view_init(elev=22, azim=-55)
    ax.set_facecolor(_PANEL)
    leg = ax.legend(
        loc="upper left", fontsize=7, framealpha=0.85,
        facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
    )
    if leg is not None:
        leg.get_frame().set_edgecolor(_EDGE)

    # Return whichever mappable exists for the shared colorbar
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    return sm


# ===========================================================================
# FUNCTION: plot_convergence  (PANEL C)
# ===========================================================================
#
# AXIOMS:
#   A1: History is ordered by iteration 0..69 (append order in optimizer).
#   A2: best-so-far(i) = min(cost[0..i]) is non-increasing (monotone).
# THEORIES:
#   T1: From A1+A2: np.minimum.accumulate gives the exact incumbent curve;
#       a vertical rule at the LHD/BO boundary explains the phase change.
# APPLICATIONS:
#   line plot of accumulate() + scatter of raw costs + axvline boundary.
# CITATIONS:
#   [1] Jones et al. (1998) — EGO convergence plots
#   [2] numpy.minimum.accumulate docs
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(N) accumulate, N=70
#   CPU Time: <1 ms compute; 15-40 ms render
#   WCET: 200 ms
#   Space Complexity: O(N)
# ===========================================================================
def plot_convergence(ax, history: list, optimized: dict) -> None:
    """Draw panel C: raw costs + best-so-far convergence curve.

    Parameters:
        ax         -- matplotlib 2D axes
        history    -- 70-entry evaluation log
        optimized  -- optimum dict (used for the floor annotation)

    Raises:
        ValueError -- empty history (safety fallback)
    """
    if not history:
        raise ValueError("plot_convergence: history empty")
    ordered = sorted(history, key=lambda e: e["iteration"])
    iters = np.array([e["iteration"] for e in ordered], dtype=float)
    costs = np.array([e["cost"] for e in ordered], dtype=float)
    best = np.minimum.accumulate(costs)

    n_lhd = sum(1 for e in ordered if e["type"] == "initial")

    ax.scatter(iters, costs, s=14, color=_TEXT, alpha=0.55,
               label="Evaluated J", zorder=2)
    ax.plot(iters, best, color=_ACCENT, linewidth=2.0,
            label="Best so far", zorder=3)
    if n_lhd > 0:
        ax.axvline(n_lhd - 0.5, color=_DIM, linestyle="--", linewidth=1.0,
                   label=f"LHD → BO (n={n_lhd})", zorder=1)
    ax.axhline(optimized["cost"], color=_ACCENT, linestyle=":",
               linewidth=1.0, alpha=0.7, zorder=1)
    ax.annotate(
        f"final best = {optimized['cost']:.4f}",
        xy=(iters[-1], best[-1]),
        xytext=(-10, 10), textcoords="offset points",
        color="white", fontsize=8, ha="right",
        arrowprops={"arrowstyle": "->", "color": _ACCENT, "lw": 0.8},
    )

    # Log y-scale: J spans ~1.44 to ~1367 (>900x) — linear crushes the basin
    # into the axis floor [module T1 / cost_norm A1].
    ax.set_yscale("log")
    ax.set_xlabel("Evaluation index (0–69)", color=_TEXT, fontsize=9)
    ax.set_ylabel("Cost J  (minimize)", color=_TEXT, fontsize=9)
    ax.set_title(
        "C — Convergence (best-so-far vs raw evaluations)",
        color="white", fontsize=11, fontweight="bold", pad=8,
    )
    ax.tick_params(colors=_DIM, labelsize=8)
    ax.set_facecolor(_PANEL)
    ax.grid(True, color=_EDGE, linewidth=0.5, alpha=0.6)
    leg = ax.legend(
        loc="upper right", fontsize=7, framealpha=0.85,
        facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
    )
    if leg is not None:
        leg.get_frame().set_edgecolor(_EDGE)


# ===========================================================================
# FUNCTION: plot_gp_slices  (PANEL B — mean + sigma)
# ===========================================================================
#
# AXIOMS:
#   A1: A 3D GP cannot be drawn as a surface; slices at fixed coordinate
#       are the standard visualization (module A4 / theory T2).
#   A2: gp.predict(X, return_std=True) yields (mu, sigma) [sklearn API].
# THEORIES:
#   T1: Fixing half_cone = optimized value shows the surrogate exactly in
#       the plane where the optimum lives — most decision-relevant slice.
#   T2: sigma panel exposes where the GP is unsure (few observations);
#       high-sigma regions = exploration debt, not "bad design".
# APPLICATIONS:
#   60x60 grid over (R_N, r_tor) at fixed half_cone; contourf(mu),
#   contourf(sigma); observed points over-projected for ground truth.
# CITATIONS:
#   [1] Rasmussen & Williams (2006) Ch. 2 — GP mean/variance
#   [2] sklearn GaussianProcessRegressor.predict return_std
#   [3] https://scikit-learn.org/stable/modules/gaussian_process.html
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(G*H) predict, G=3600 grid x H=70 -> 2.5e5
#   CPU Time: 30-150 ms per panel (two predicts: mean+std together)
#   WCET: 1 s including contourf triangulation
#   Space Complexity: O(G) = 3600 doubles per field (~29 kB x2)
#   Hardware Assumptions: CPU-only; Agg contour rasterizer
# ===========================================================================
def plot_gp_slices(
    ax_mu,
    ax_sigma,
    gp: GaussianProcessRegressor,
    history: list,
    bounds: list,
    optimized: dict,
    default: dict,
    grid_n: int = 60,
) -> None:
    """Draw panel B: GP posterior mean and std slices at optimized half-cone.

    Parameters:
        ax_mu      -- axes for posterior mean contour
        ax_sigma   -- axes for posterior std contour
        gp         -- fitted surrogate (fit_gp_surrogate output)
        history    -- observation log (for over-projected markers)
        bounds     -- (lo, hi) per dimension [R_N, r_tor, half_cone]
        optimized  -- optimum dict (fixes the slice + star marker)
        default    -- default dict (diamond marker)
        grid_n     -- grid resolution per axis (default 60 -> 3600 pts)

    Raises:
        ValueError -- grid_n < 2 or bounds malformed (safety fallback)
        RuntimeError -- gp.predict failed (full context attached)
    """
    if grid_n < 2:
        raise ValueError(f"grid_n must be >= 2, got {grid_n}")
    if len(bounds) != 3:
        raise ValueError(f"Expected 3 bound pairs, got {len(bounds)}: {bounds}")

    (lo0, hi0), (lo1, hi1), (lo2, hi2) = bounds
    half_cone_fix = float(optimized["half_cone_deg"])
    # Murphy: if the optimizer somehow wrote an out-of-bounds optimum,
    # clamp into the slice range and SAY SO (never plot off-domain silently).
    if not (lo2 <= half_cone_fix <= hi2):
        print(
            f"WARNING: optimized half_cone {half_cone_fix} outside bounds "
            f"[{lo2}, {hi2}] — clamping for slice.",
            file=sys.stderr,
        )
        half_cone_fix = min(max(half_cone_fix, lo2), hi2)

    gx = np.linspace(lo0, hi0, grid_n)
    gy = np.linspace(lo1, hi1, grid_n)
    gx_m, gy_m = np.meshgrid(gx, gy)
    X_grid = np.column_stack(
        [gx_m.ravel(), gy_m.ravel(), np.full(gx_m.size, half_cone_fix)]
    )
    try:
        mu, sigma = gp.predict(X_grid, return_std=True)
    except Exception as exc:
        raise RuntimeError(
            f"gp.predict failed on {X_grid.shape[0]} grid points: {exc!r}"
        ) from exc
    mu = mu.reshape(gx_m.shape)
    sigma = sigma.reshape(gx_m.shape)

    # --- Mean panel ---
    cf1 = ax_mu.contourf(gx_m, gy_m, mu, levels=24, cmap="turbo", alpha=0.92)
    ax_mu.contour(
        gx_m, gy_m, mu,
        levels=[float(optimized["cost"])],
        colors="white", linewidths=1.4,
    )
    # Over-project ALL observations onto this slice (visual ground truth)
    hx = [e["R_N"] for e in history]
    hy = [e["r_tor"] for e in history]
    ax_mu.scatter(hx, hy, s=10, facecolors="none", edgecolors="white",
                  linewidths=0.5, alpha=0.7, label="observed (projected)")
    ax_mu.scatter(
        [optimized["R_N"]], [optimized["r_tor"]],
        marker="*", s=220, color=_ACCENT, edgecolors="white",
        linewidths=0.7, zorder=5, label="optimum",
    )
    ax_mu.scatter(
        [default["R_N"]], [default["r_tor"]],
        marker="D", s=55, color=_TEXT, edgecolors="white",
        linewidths=0.7, zorder=5, label="default",
    )
    ax_mu.set_title(
        f"B1 — GP mean μ(x) at half-cone = {half_cone_fix:.2f}°",
        color="white", fontsize=11, fontweight="bold", pad=8,
    )
    _style_slice_axes(ax_mu)
    leg = ax_mu.legend(
        loc="upper right", fontsize=7, framealpha=0.85,
        facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
    )
    if leg is not None:
        leg.get_frame().set_edgecolor(_EDGE)
    cb1 = ax_mu.figure.colorbar(cf1, ax=ax_mu, shrink=0.85, pad=0.02)
    cb1.ax.tick_params(colors=_DIM, labelsize=7)
    cb1.set_label("μ  [cost J]", color=_TEXT, fontsize=8)

    # --- Sigma panel ---
    cf2 = ax_sigma.contourf(gx_m, gy_m, sigma, levels=24, cmap="magma")
    ax_sigma.scatter(hx, hy, s=10, facecolors="none", edgecolors="white",
                     linewidths=0.5, alpha=0.7, label="observed (projected)")
    ax_sigma.scatter(
        [optimized["R_N"]], [optimized["r_tor"]],
        marker="*", s=220, color="white", edgecolors=_ACCENT,
        linewidths=0.8, zorder=5, label="optimum",
    )
    ax_sigma.set_title(
        "B2 — GP std σ(x)  (epistemic uncertainty)",
        color="white", fontsize=11, fontweight="bold", pad=8,
    )
    _style_slice_axes(ax_sigma)
    leg2 = ax_sigma.legend(
        loc="upper right", fontsize=7, framealpha=0.85,
        facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
    )
    if leg2 is not None:
        leg2.get_frame().set_edgecolor(_EDGE)
    cb2 = ax_sigma.figure.colorbar(cf2, ax=ax_sigma, shrink=0.85, pad=0.02)
    cb2.ax.tick_params(colors=_DIM, labelsize=7)
    cb2.set_label("σ  [cost J]", color=_TEXT, fontsize=8)


# ===========================================================================
# FUNCTION: _style_slice_axes  (shared helper for panel B)
# ===========================================================================
#
# AXIOMS:   slice panels share identical styling requirements (consistency).
# THEORIES: one helper => zero style drift between B1 and B2 (no copy-paste).
# APPLICATIONS: called by plot_gp_slices for both axes.
# CITATIONS: render_optimization_comparison.py tick/color precedent.
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(1) attribute sets
#   CPU Time: <1 ms    WCET: 5 ms    Space Complexity: O(1)
# ===========================================================================
def _style_slice_axes(ax) -> None:
    """Apply the shared dark-theme styling to a panel-B axes.

    Parameters:
        ax -- matplotlib 2D axes to style in place
    """
    ax.set_xlabel("R_N [m]", color=_TEXT, fontsize=9)
    ax.set_ylabel("r_tor [m]", color=_TEXT, fontsize=9)
    ax.tick_params(colors=_DIM, labelsize=8)
    ax.set_facecolor(_PANEL)


# ===========================================================================
# FUNCTION: main
# ===========================================================================
#
# AXIOMS:
#   A1: All three panels derive from ONE JSON load (single source of truth).
#   A2: A figure with any failed panel must still be SAVED for debugging and
#       the process must exit NON-ZERO (no silent partial success).
# THEORIES:
#   T1: From A1: reloading data per panel would risk intra-figure drift.
#   T2: From A2: annotate-the-error + save + exit(1) beats a blank crash.
# APPLICATIONS:
#   load -> norm -> three panel calls inside one try/except -> savefig.
# CITATIONS:
#   [1] code-quality.md — verbose errors, safety fallback, execute-before-done
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(H^3) GP fit dominates; total 1-5 s typical
#   CPU Time: ~2 s (GP 0.3 s + contours 0.5 s + raster 1 s)
#   WCET: 15 s (cold sklearn import + GP restarts at max_iter)
#   Space Complexity: O(H^2 + G) ≈ 1 MB working set
#   Hardware Assumptions: macOS arm64, /opt/homebrew python3.14 + sklearn 1.9
#   Derivation: fit(O(H^3)) + predict(O(GH)) + render(O(G)); H=70, G=3600
# ===========================================================================
def main() -> int:
    """Render bo_optimization_3d.png (panels A, B, C).

    Returns:
        0 on full success, 1 on any panel/data failure (never 0 on error).
    """
    print("=" * 72)
    print("  Rendering BO 3D diagnostic figure (panels A + B + C)")
    print("=" * 72)
    panel_errors: list = []

    try:
        # --- Step 1: load + validate data (A1) ---
        print(f"\n[1/5] Loading {_RESULTS_JSON} ...")
        data = load_results(_RESULTS_JSON)
        history = data["history"]
        ccd = data["ccd_samples"]
        default = data["default"]
        optimized = data["optimized"]
        print(f"  history={len(history)}  ccd={len(ccd)}  "
              f"opt J={optimized['cost']:.6f}")

        # --- Step 2: bounds (A3) ---
        print("\n[2/5] Resolving parameter bounds ...")
        bounds = get_bounds()

        # --- Step 3: shared color norm from ALL plotted costs ---
        all_costs = [e["cost"] for e in history] + [s["cost"] for s in ccd]
        cost_arr = np.asarray(all_costs, dtype=float)
        norm = cost_norm(cost_arr)
        print(f"  cost range: [{cost_arr.min():.4f}, {cost_arr.max():.4f}]")

        # --- Step 4: fit GP surrogate (panel B prerequisite) ---
        print("\n[3/5] Fitting GP surrogate on history ...")
        try:
            gp = fit_gp_surrogate(history, bounds)
        except (ValueError, RuntimeError) as exc:
            # Safety fallback: still render A + C, mark B as failed,
            # exit non-zero at the end (A2 / T2).
            print(f"ERROR: GP fit failed:\n{exc}", file=sys.stderr)
            traceback.print_exc()
            gp = None
            panel_errors.append("GP fit")

        # --- Step 5: build figure ---
        print("\n[4/5] Drawing panels ...")
        fig = plt.figure(figsize=(16, 10), facecolor=_BG)
        gs = fig.add_gridspec(
            2, 2, width_ratios=[1.15, 1.0], height_ratios=[1.0, 1.0],
            left=0.06, right=0.96, top=0.90, bottom=0.07,
            wspace=0.28, hspace=0.42,
        )
        ax_a = fig.add_subplot(gs[:, 0], projection="3d")
        ax_c = fig.add_subplot(gs[0, 1])
        ax_mu = fig.add_subplot(gs[1, 0])
        ax_sg = fig.add_subplot(gs[1, 1])

        # Panel A
        try:
            sm = plot_scatter_3d(ax_a, history, ccd, default, optimized, norm)
            cb = fig.colorbar(sm, ax=ax_a, shrink=0.68, pad=0.10)
            cb.ax.tick_params(colors=_DIM, labelsize=7)
            cb.set_label("cost J (log)", color=_TEXT, fontsize=8)
            print("  panel A (3D scatter): OK")
        except Exception as exc:  # noqa: BLE001 — panel isolation is deliberate (module A2): one panel failing must not kill the figure
            panel_errors.append("A")
            print(f"ERROR panel A: {exc}", file=sys.stderr)
            traceback.print_exc()
            ax_a.set_title("A — FAILED (see stderr)", color=_ACCENT,
                           fontsize=11, fontweight="bold")

        # Panel C
        try:
            plot_convergence(ax_c, history, optimized)
            print("  panel C (convergence): OK")
        except Exception as exc:  # noqa: BLE001 — panel isolation is deliberate (module A2)
            panel_errors.append("C")
            print(f"ERROR panel C: {exc}", file=sys.stderr)
            traceback.print_exc()
            ax_c.set_title("C — FAILED (see stderr)", color=_ACCENT,
                           fontsize=11, fontweight="bold")

        # Panel B (both sub-panels)
        if gp is not None:
            try:
                plot_gp_slices(ax_mu, ax_sg, gp, history, bounds,
                               optimized, default)
                print("  panel B (GP mean + sigma): OK")
            except Exception as exc:  # noqa: BLE001 — panel isolation is deliberate (module A2)
                panel_errors.append("B")
                print(f"ERROR panel B: {exc}", file=sys.stderr)
                traceback.print_exc()
                ax_mu.set_title("B1 — FAILED (see stderr)", color=_ACCENT,
                                fontsize=11, fontweight="bold")
                ax_sg.set_title("B2 — FAILED (see stderr)", color=_ACCENT,
                                fontsize=11, fontweight="bold")
        else:
            panel_errors.append("B")
            for ax, name in ((ax_mu, "B1"), (ax_sg, "B2")):
                ax.set_facecolor(_PANEL)
                ax.text(
                    0.5, 0.5, f"{name}: GP FIT FAILED\n(see stderr)",
                    transform=ax.transAxes, ha="center", va="center",
                    color=_ACCENT, fontsize=12, fontweight="bold",
                )

        # --- Suptitle + save ---
        imp = data.get("improvement", {})
        fig.suptitle(
            "StellarOrion HIAD — Bayesian Optimization Diagnostics\n"
            f"70 evals (20 LHD + 50 BO) · best J = {optimized['cost']:.4f} "
            f"· Cd improvement = {imp.get('cd_pct', float('nan')):.2f}% "
            f"· GP Matern 5/2 + EI (ξ=0.01)",
            color="white", fontsize=13, fontweight="bold", y=0.975,
        )
        print(f"\n[5/5] Saving {_OUTPUT_PNG} ...")
        fig.savefig(
            str(_OUTPUT_PNG), dpi=150, facecolor=_BG, bbox_inches="tight",
        )
        plt.close(fig)
        if not _OUTPUT_PNG.is_file():
            raise RuntimeError(f"savefig reported success but file missing: "
                               f"{_OUTPUT_PNG}")
        size_kb = _OUTPUT_PNG.stat().st_size / 1024.0
        print(f"  Saved: {_OUTPUT_PNG} ({size_kb:.1f} kB)")

    except Exception as exc:
        # Top-level safety net: never exit silently (verbose error reporting)
        print(f"\nFATAL: {exc!r}", file=sys.stderr)
        traceback.print_exc()
        return 1

    if panel_errors:
        print(
            f"\nFAILED panels: {panel_errors}\n"
            f"  Figure saved for debugging, but this run is NOT a success.",
            file=sys.stderr,
        )
        return 1

    print("\nAll panels rendered successfully.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
