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

matplotlib.use("Agg")
# Floor: chapter 04 places this PNG at \textwidth; with the shrunk
# canvas the natural width matches print width, so declared pt = printed
# pt. font.size pins tick labels at 8.5 pt (>= the 8 pt floor).
matplotlib.rcParams.update({"font.size": 8.5})
  # headless-safe: render off-screen, only savefig matters
import matplotlib.pyplot as plt
import numpy as np

#  F70: one shared implementation of "is this number measurable?".  The old
#  inline default float("nan") rendered the caption as "nan%" whenever the
#  key was missing, so a missing input looked like a measurement.
#  [Citation: scripts/figure_text.py AXIOMS A1-A3]
# improvement_pct import removed: its only use was the dropped suptitle
# line 2 (no_dead_code).
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LogNorm, Normalize
from matplotlib.ticker import LogFormatter, MaxNLocator
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

# Dark theme — matches render_optimization_comparison.py precedent [5]
# ---------------------------------------------------------------------------
# LIGHT THEME (p9 / DEFECT 1).
#
# WHY: this figure was authored dark (near-black _BG). The Beamer deck that
# consumes it has a WHITE body (rgb(255,255,255)) with a rgb(207,221,216)
# header band, so the exported figure rendered as a near-black rectangle:
# corner pixel rgb(10,10,15) with 85.9% dark pixels, driving that slide's
# ink fill to 54.83% against 5-15% for every other slide. Every colour below
# is the direct light-theme counterpart of the dark value it replaces, and the
# edges are keyed to the deck's own header band so the figure sits on the slide
# rather than fighting it.
#
# Measured after the swap (corner rgb(255,255,255), dark-pixel share back in
# the 3.9-31.5% band of the other seven figures).
#
# CITATION: [Deck body/header colours measured from
#            Lost+Found/ProgressReport/Week 16 LaTeX/main.pdf]
# ---------------------------------------------------------------------------
_BG = "#ffffff"        # was #0a0a0f -- figure + savefig facecolor
_PANEL = "#eef3f2"     # was #1a1a2e -- axes facecolor, label-box fill
_TEXT = "#2f3b43"      # was #8892b0 -- dark slate, legible on white
_ACCENT = "#c0392b"    # was #e94560 -- deeper red, same hue family, reads on white
_DIM = "#3a4a51"       # was #555555 -- tick labels + secondary marks
_EDGE = "#a8bfba"      # was #0f3460 -- keyed to the deck header band #cfddd8

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
    # WHY (crowding): parentheticals made the labels ~170 px wide and the
    # projection throws r_tor's label across the column gap onto panel C's
    # ylabel/ticks; the short forms match panels B1/B2 ('R_N [m]', 'r_tor
    # [m]') and the meanings live in the ch4 prose.
    # WHY (labelpad -4 -> 0, audit 1): the negative pad pulled each diagonal
    # label INTO the tick-number zone — 'R_N [m]' physically touched tick
    # '1' and overlapped tick '2' by 12.5x7.5 px, and 'r_tor [m]' crossed
    # tick '0.25'. 0 restores the default outward offset (~5.5 px) which
    # clears every tick; the short labels no longer risk reaching panel C.
    ax.set_xlabel("R_N [m]", color=_TEXT, fontsize=9, labelpad=0)
    ax.set_ylabel("r_tor [m]", color=_TEXT, fontsize=9, labelpad=0)
    # WHY (zlabel text + labelpad, take-6 final): 'half-cone [deg]' (18 px
    # band) could not clear BOTH the z-tick digits (~x302) and the
    # colorbar frame (x338) — every pad/padlabel combo left 0 px on one
    # side (audit 3 defects 3a/3b). The short form 'θc [deg]' (~12 px,
    # same θc symbol the thesis uses in tab:default_params) opens both:
    # at labelpad -4 audit 4 measured the tightest digit-gap at 1 px
    # (y186: digits end x304, label starts x306) — under the 2 px floor —
    # so -3 shifts the label right; right-side slack to the bar frame
    # (x338) is 18 px, both gaps re-probed after render.
    # Label rows y117-193 sit beside the bar rows but x-clear.
    ax.set_zlabel("θc [deg]", color=_TEXT, fontsize=9, labelpad=-3)
    ax.set_title(
        # WHY (width/floor): the old 51-char title overhung the 228 px cell
        # and spilled past the figure edge; the dropped '(color = cost J,
        # log scale)' lives on the colorbar label 'cost J (log)'. white was
        # a dark-theme leftover -> invisible on the light _PANEL/_BG.
        "A — Evaluated geometries",
        color=_TEXT, fontsize=11, fontweight="bold", pad=8,
    )
    ax.tick_params(colors=_DIM, labelsize=8.5)
    # Cap z-ticks: half-cone range 40-80 deg would otherwise crowd the
    # slot beside the shared colorbar (with pad 0.26 the slot runs
    # x303-337: ticks need x<=302, so 3 fit and 5 would overlap them).
    ax.zaxis.set_major_locator(MaxNLocator(nbins=3))
    ax.view_init(elev=22, azim=-55)
    ax.set_facecolor(_PANEL)
    # WHY (audit 1, D1-D4 + defects 5/6/7): the legend used to live HERE,
    # inside the 3-D axes — mplot3d's depth pass draws every scatter AFTER
    # ordinary axes children, so the markers painted straight over 4 of 5
    # legend rows, the shared colorbar struck rows 2-4, the 'Optimum J'
    # tail merged with colorbar tick '10¹', and the pale box hid the
    # z-tick numbers (45/60/75), the z label (then 'half-cone [deg]',
    # now the shorter 'θc [deg]') and the
    # '0.50' r_tor tick underneath it. No zorder value beats the depth
    # pass (same root cause as the comparison figure), so the legend is
    # now built at FIGURE level in main(), in the empty band between the
    # two grid rows — outside every axes, nothing to overpaint.
    # (labels stay on the scatter calls above; main() collects them.)

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
    # WHY (audit 4, defect 2 — root-caused by savefig introspection):
    # the previous axes-fraction 0.97/0.76 placed the text at dpi100
    # px y309-321, but the C legend (upper right, x352-502 y275-334)
    # is drawn AFTER the annotation and fully covered it — the pixel
    # probes found no text there and audit 4 called it 'absent'.
    # (0.97, 0.21) puts the text in the free slot BELOW the legend.
    # Take 0.28 measured the glyph band at final y193-205 and take
    # 0.24 at y200-211 — but the legend's bottom BORDER row is y199
    # (the savefig bbox mapping runs ~3 px optimistic), so 0.24 still
    # touched at 0-1 px. 0.21 drops another ~5 px to y~205-216,
    # giving a ~5 px gap below the y199 border; curve/axhline sit at
    # y>=236 so the bottom stays >=20 px clear. Verified by the
    # x750-785 column probe (annotation-only columns, legend ends x744).
    # The opaque _PANEL bbox keeps glyphs readable if a marker lands
    # underneath; the arrow points up-right from the final point.
    ax.annotate(
        f"final best = {optimized['cost']:.4f}",
        xy=(iters[-1], best[-1]),
        # audit-5: x 0.97 -> 0.90 -- red curve vertex (734,225) sat 8px under the
        # text right end (need >=10); text now spans x~552-719, all columns clear
        # of the x>=734 red by >=17px; y=0.21 keeps J=10 gridline y199 3px above
        # glyphs, C legend (bottom y183) 19px above, C y-ticks x468-509 43px left.
        xytext=(0.90, 0.251), textcoords="axes fraction",
        color=_TEXT, fontsize=8.5, ha="right", va="center",
        bbox={"facecolor": _PANEL, "edgecolor": "none", "alpha": 0.9, "pad": 1.5},
        arrowprops={"arrowstyle": "->", "color": _ACCENT, "lw": 0.8},
    )

    # Log y-scale: J spans ~1.44 to ~1367 (>900x) — linear crushes the basin
    # into the axis floor [module T1 / cost_norm A1].
    ax.set_yscale("log")
    # WHY plain decade formatter (audit 3, defect 7b): the default
    # LogFormatterSciNotation renders '10^3' with a mathtext superscript —
    # scripts are 0.70x the 8.5 pt parent, i.e. ~5.7 pt printed, under the
    # 8 pt figure-text floor. The plain base LogFormatter (no SciNotation
    # subclass) prints full-height digits ('1000') at the same 8.5 pt
    # (>= 8.0 pt after the print squeeze).
    ax.yaxis.set_major_formatter(LogFormatter(base=10.0))
    ax.set_xlabel("Evaluation index (0–69)", color=_TEXT, fontsize=9)
    # WHY labelpad 4 -> 2 (audit 3, rechecked take-5/6): with the A
    # colorbar pad at 0.26 the cax (bar + ticks + 'cost J (log)' label)
    # sits right of the z zone, closing in on C's ylabel; pulling C's
    # ylabel 2 pt left keeps >= 4 px to the colorbar label while staying
    # clear of C's own y-tick text (both gaps probed after render).
    ax.set_ylabel("Cost J  (minimize)", color=_TEXT, fontsize=9, labelpad=2)
    ax.set_title(
        # WHY: 47-char title overlapped the suptitle and C's own y-ticks;
        # the legend already names 'Evaluated J'/'best-so-far' series.
        # white -> _TEXT (invisible on light panel, see A title comment).
        "C — Convergence",
        color=_TEXT, fontsize=11, fontweight="bold", pad=8,
    )
    ax.tick_params(colors=_DIM, labelsize=8.5)
    ax.set_facecolor(_PANEL)
    ax.grid(True, color=_EDGE, linewidth=0.5, alpha=0.6)
    # WHY (audit 1, defect 5+6): framealpha 0.85 let the dashed LHD->BO
    # line and the grid show THROUGH the legend box (the line crossed the
    # red/dashed handles). _PANEL at alpha 1.0 is opaque — panel C is a
    # plain 2-D axes, so ordinary zorder applies and the legend paints over
    # the axvline (zorder 1) and grid (zorder 0) cleanly.
    leg = ax.legend(
        loc="upper right", fontsize=8.5, framealpha=1.0,
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
    # WHY clip_on (audit 1, defect 3): the optimum sits at R_N=2.989 of
    # the 0.5-3.0 bound — 0.5% from the right spine — so the s=220 star's
    # 27 px body straddled the spine and touched the mu colorbar. Explicit
    # clip_on=True cuts the marker hard at the axes edge instead.
    ax_mu.scatter(
        [optimized["R_N"]], [optimized["r_tor"]],
        marker="*", s=220, color=_ACCENT, edgecolors="white",
        linewidths=0.7, zorder=5, label="optimum", clip_on=True,
    )
    ax_mu.scatter(
        [default["R_N"]], [default["r_tor"]],
        marker="D", s=55, color=_TEXT, edgecolors="white",
        linewidths=0.7, zorder=5, label="default", clip_on=True,
    )
    ax_mu.set_title(
        # WHY: 40-char title collided with 'half-cone [deg]' zlabel and B2's
        # title; the slice angle stays in the ch4 prose. white -> _TEXT.
        "B1 — GP mean μ(x)",
        color=_TEXT, fontsize=11, fontweight="bold", pad=8,
    )
    _style_slice_axes(ax_mu)
    # WHY framealpha 1.0 (audit 1, defect 6): 0.85 let the mean map show
    # through the box ("legend covers the upper half of the map"). Opaque
    # _PANEL keeps the box readable; box stays upper right (15 px clear of
    # the '0.4' y tick there — B2 needed the nudge below).
    leg = ax_mu.legend(
        loc="upper right", fontsize=8.5, framealpha=1.0,
        facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
    )
    if leg is not None:
        leg.get_frame().set_edgecolor(_EDGE)
    cb1 = ax_mu.figure.colorbar(cf1, ax=ax_mu, shrink=0.85, pad=0.02)
    cb1.ax.tick_params(colors=_DIM, labelsize=8.5)  # floor: 7 pt -> 6.7 printed
    cb1.set_label("μ  [cost J]", color=_TEXT, fontsize=8.5)

    # --- Sigma panel ---
    cf2 = ax_sigma.contourf(gx_m, gy_m, sigma, levels=24, cmap="magma")
    ax_sigma.scatter(hx, hy, s=10, facecolors="none", edgecolors="white",
                     linewidths=0.5, alpha=0.7, label="observed (projected)")
    # clip_on=True — same boundary-optimum straddle as B1 (audit 1, defect 3).
    ax_sigma.scatter(
        [optimized["R_N"]], [optimized["r_tor"]],
        marker="*", s=220, color="white", edgecolors=_ACCENT,
        linewidths=0.8, zorder=5, label="optimum", clip_on=True,
    )
    ax_sigma.set_title(
        # WHY: 40-char title collided with B1's title; suffix parenthetical
        # is redundant with the σ colorbar label. white -> _TEXT.
        "B2 — GP std σ(x)",
        color=_TEXT, fontsize=11, fontweight="bold", pad=8,
    )
    _style_slice_axes(ax_sigma)
    # WHY bbox_to_anchor (audit 1, defect 4): the default (1,1) anchor
    # left the box's top-left corner flush against the '0.4' y-tick text
    # (tick ends x523, box starts x524 — 0 px). Dropping the box 5% of
    # the axes height clears the tick band vertically; framealpha 1.0 as
    # in B1. Audit 3 measured x1.00 → left border x527 = only 1 clear
    # column (x526) from the B2 spine (x524-525); 1.01 shifts the box
    # ~2 px right → ≥3 px from the spine's outer edge (x524) while the
    # right edge (x742) stays inside x749.
    # WHY the tight frame kwargs (take-3 measurement): at default
    # handlelength 2.0 the box measured x490-738 = 248 px — WIDER than
    # the 243 px axes, so its left edge overhung the spine (x748 right /
    # ~x505 left) and sat on top of the y-tick labels again. Compressed
    # frame reclaims ~33 px -> ~215 px, left edge lands ~x523, 20 px
    # clear of the tick text and inside the spine.
    leg2 = ax_sigma.legend(
        loc="upper right", bbox_to_anchor=(1.01, 0.95),
        fontsize=8.5, framealpha=1.0,
        facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
        handlelength=1.0, handletextpad=0.1, columnspacing=0.2,
        borderpad=0.2,
    )
    if leg2 is not None:
        leg2.get_frame().set_edgecolor(_EDGE)
    cb2 = ax_sigma.figure.colorbar(cf2, ax=ax_sigma, shrink=0.85, pad=0.02)
    cb2.ax.tick_params(colors=_DIM, labelsize=8.5)  # floor: 7 pt -> 6.7 printed
    cb2.set_label("σ  [cost J]", color=_TEXT, fontsize=8.5)


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
    ax.tick_params(colors=_DIM, labelsize=8.5)
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
        # WHY (layout + floor): height 3.60 -> 4.05 buys the two label bands
        # (xticks+xlabel below top row, panel titles above bottom row) that
        # spied 45 overlaps; width stays 5.77 so the include squeeze is
        # 0.955 (8.5 pt prints 8.12 pt). right 0.96 -> 0.88 keeps panel B2's
        # colorbar + tick labels inside the canvas (spied '0.75' 19 px
        # over at right=0.90); bottom 0.07 -> 0.11 holds the bottom-row
        # xtick+xlabel band; top 0.90 -> 0.84 puts top-row titles between
        # axes and suptitle; hspace 0.42 -> 0.80 separates C's xlabel band
        # from B2's title band; wspace 0.28 -> 0.45 keeps panel A's 3-D
        # labels from reaching panel C's ylabel/ticks across the gap.
        fig = plt.figure(figsize=(5.77, 4.05), facecolor=_BG)
        gs = fig.add_gridspec(
            2, 2, width_ratios=[1.15, 1.0], height_ratios=[1.0, 1.0],
            left=0.06, right=0.88, top=0.84, bottom=0.11,
            wspace=0.45, hspace=0.80,
        )
        # WHY: gs[:, 0] made panel A span BOTH rows while B1 (gs[1, 0]) drew
        # over A's lower half, burying A's xlabel/xticks under an opaque
        # axes (spied: 'R_N (nose radius) [m]' vs every B1 tick). Each panel
        # now owns exactly one cell.
        ax_a = fig.add_subplot(gs[0, 0], projection="3d")
        ax_c = fig.add_subplot(gs[0, 1])
        ax_mu = fig.add_subplot(gs[1, 0])
        ax_sg = fig.add_subplot(gs[1, 1])

        # Panel A
        try:
            sm = plot_scatter_3d(ax_a, history, ccd, default, optimized, norm)
            # WHY (pad 0.12 -> 0.175 -> 0.32 -> 0.26, audits 3 defects
            # 3a/3b + take-5/6 geometry): the colorbar bar sat on top of
            # the z label — the real defect (tick marks that follow the
            # bar were mistaken for the label in take-4/5 probes). With
            # the short 'θc [deg]' label (see plot_scatter_3d) ending at
            # x319, pad 0.26 puts the bar frame at x338: 18 px clear of
            # the label and 3+ px from the z-tick digits (x<=302).
            # pad pitch ~88 px per 1.0 (0.125 A/B test: bar 340->351).
            # Canvas stays legend-bound (ink 857 + 6 px pad) -> floor
            # 8.143 pt. C ylabel gap to cb label probed after render.
            cb = fig.colorbar(sm, ax=ax_a, shrink=0.68, pad=0.26)
            cb.ax.tick_params(colors=_DIM, labelsize=8.5)
            # WHY plain decade formatter (audit 3, defect 7b): LogNorm's
            # default SciNotation ticks '10³/10²/10¹' carry 0.70x mathtext
            # superscripts (~5.7 pt printed < 8 pt floor); the plain base
            # LogFormatter prints full-height '1000/100/10' at 8.5 pt so
            # every glyph stays >= 8 pt.
            cb.ax.yaxis.set_major_formatter(LogFormatter(base=10.0))
            cb.set_label("cost J (log)", color=_TEXT, fontsize=8.5)
            # WHY fig-level legend (audit 1, D1-D4): plot_scatter_3d no
            # longer draws an in-axes legend — mplot3d's depth pass paints
            # every scatter AFTER ordinary axes children, so markers,
            # the colorbar and the legend boxed each other in (defects
            # 1-3, 5-7). The empty band between the two grid rows (C's
            # xlabel band bottom ~310 px, B's title band top ~348 px) is
            # outside every axes: a figure-level legend drawn last can be
            # overpainted by nothing there. 8.5 pt keeps the printed size
            # at 8.5 x 0.955 = 8.12 pt (>= 8 pt floor).
            # WHY the tight spacings (take-1 measurement): the default
            # handlelength 2.0 / columnspacing 1.0 / handletextpad 0.5
            # produced a 965 px box — WIDER than the 865 px canvas, so
            # bbox_inches="tight" grew the figure to 994 px and the print
            # squeeze fell to 0.832 (8.5 pt -> 7.07 pt, under floor).
            # take-2 measured still 820 px (x55-875, canvas 890 px ->
            # 7.90 pt) so the spacings go to their minimums: reclaimed
            # ~45 px -> ~775 px box, right edge lands inside the canvas.
            # WHY anchor 0.4875: 0.465 put the box at y332-360, whose
            # bottom collided with the B-title band (rows start y355).
            # 0.4875 seats it at y318-343: 6 px under the top-row content
            # (ends y312) and 4 px above the titles (start y347).
            # WHY columnspacing 0.45 (audit 3, defect 1): at 0.1 the
            # Optimum-star handle (white edge x502) overpainted the ')' of
            # 'BO iteration (50)' (0 px) and 'Default J' sat 1 px from
            # 'Optimum J=1.560'. +0.35 em ≈ 6 px per boundary → ≥3 px at
            # both. Width budget: box ~802 px, right frame ~x866 → tight
            # canvas ≈ 874 px → nat 5.83 in → squeeze 0.946 → 8.04 pt ✓
            # (0.50 would push the canvas past 879 px = 8.0 pt floor).
            h_a, l_a = ax_a.get_legend_handles_labels()
            fig.legend(
                h_a, l_a, loc="upper center", bbox_to_anchor=(0.5, 0.4875),
                ncol=5, fontsize=8.5, framealpha=1.0,
                facecolor=_PANEL, edgecolor=_EDGE, labelcolor=_TEXT,
                borderpad=0.15, columnspacing=0.45, handletextpad=0.1,
                handlelength=1.0,
            )
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
        # WHY (crop + theme): line 2 (~90 chars at 13 pt = 10.3 in) spilled
        # 1.5 in past BOTH canvas edges and its facts (70 evals/20 LHD/50 BO,
        # best J, Cd improvement, Matern 5/2 + EI) all appear in the ch4
        # caption/prose. 1 line at 11 pt = 5.3 in fits the 5.77 in canvas.
        # white -> _TEXT: dark-theme leftover, invisible on white _BG.
        fig.suptitle(
            "StellarOrion HIAD — Bayesian Optimization Diagnostics",
            color=_TEXT, fontsize=11, fontweight="bold", y=0.975,
        )
        print(f"\n[5/5] Saving {_OUTPUT_PNG} ...")
        # WHY (pad_inches 0.04, take-5 floor): tight bbox without explicit
        # pad rendered an 881 px canvas -> nat 5.873 in -> 8.5 pt prints
        # 7.977 pt, under the 8.0 pt floor (max canvas 873 px). The default
        # margin alone cost ~15 px/side; pinning pad to 0.04 in (6 px)
        # targets ~869 px -> ~8.05 pt while keeping ink >= 6 px off the
        # canvas edge. 0.00 would clip glyph AA at the border.
        fig.savefig(
            str(_OUTPUT_PNG), dpi=150, facecolor=_BG, bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)
        if not _OUTPUT_PNG.is_file():
            raise RuntimeError(f"savefig reported success but file missing: "
                               f"{_OUTPUT_PNG}")
        size_kb = _OUTPUT_PNG.stat().st_size / 1024.0
        print(f"  Saved: {_OUTPUT_PNG} ({size_kb:.1f} kB)")

    except Exception as exc:  # noqa: BLE001 -- top-level safety net: a figure
        # that took minutes to render must still report its failure. Narrowing
        # this catch would crash the run and lose the diagnostic entirely.
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
