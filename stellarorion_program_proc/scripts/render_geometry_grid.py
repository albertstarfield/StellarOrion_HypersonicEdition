#!/usr/bin/env python3
"""
================================================================================
SCRIPT: render_geometry_grid.py — 87-Panel 3D HIAD Geometry Grid
================================================================================

Renders hiad_geometry_grid.png — a 10x9 grid of 3D vehicle panels, one per
geometry evaluated (or referenced) during Bayesian optimization, each colored
by its cost J on a single shared logarithmic colormap.

Panel composition (87 = 1 + 15 + 70 + 1):
  [1]     IRVE-3 default baseline          (explicit reference)
  [15]    CCD design points                 (ccd_samples in JSON)
  [70]    BO evaluation history             (20 LHD initial + 50 BO)
  [1]     Optimized optimum                 (explicit, highlighted)

AXIOMS:
  A1: A geometry is fully determined by (R_N, r_tor, half_cone_deg).
  A2: Evaluated costs span >900x (~1.44 basin to ~1367 penalized corner);
      a linear color norm would crush the basin (same fact as
      render_bo_3d_plot.py cost_norm A1).
  A3: hiad_geometry.generate_cross_section is the single profile source —
      no local re-derivation of the 4-segment math (no copy-paste drift).
  A4: Panel data comes ONLY from hiad_optimization_results.json — the grid
      never re-runs the optimizer (pure post-processing).

THEORIES:
  T1: From A1+A3: revolving the shared meridian profile 360 deg about the
      axial axis produces the axisymmetric HIAD body; every panel uses the
      same revolution code path, so shapes are geometrically comparable.
  T2: From A2: ONE LogNorm shared by all 87 panels makes panel colors
      directly comparable; per-panel norms would encode nothing.
  T3: From A4: if the JSON is missing/malformed the script fails loudly
      (FileNotFoundError/ValueError with fix instructions), never invents
      data and never exits 0 on missing input.

APPLICATIONS:
  load_results -> build_panel_list (87) -> per-panel plot_surface under a
  shared view/norm/limits -> single colorbar -> savefig (Agg backend).

CITATIONS:
  [1] hiad_geometry.py — generate_cross_section (Ada line-for-line port)
  [2] stellarorion_pinn_trajectory.adb lines 393-479 — Ada source of truth
  [3] hiad_optimization_results.json — written by hiad_optimizer.py
  [4] render_bo_3d_plot.py — dark theme, LogNorm, validation precedent
  [5] Jones et al. (1998) — BO evaluation log (EGO)
  [6] matplotlib LogNorm —
      https://matplotlib.org/stable/api/_as_gen/matplotlib.colors.LogNorm.html

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
_OUTPUT_PNG = _PROJECT_ROOT / "hiad_geometry_grid.png"

import matplotlib

matplotlib.use("Agg")  # headless-safe: render off-screen, only savefig matters
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LogNorm, Normalize

# Pure-NumPy geometry module — MUST NOT import ada_pinn_wrapper (A3): the
# grid has to render even when libstellarorion_pinn.dylib is absent.
sys.path.insert(0, str(_SRC_PYTHON))
from hiad_geometry import generate_cross_section  # noqa: E402

# Dark theme — matches render_bo_3d_plot.py [4]
_BG = "#0a0a0f"
_PANEL = "#1a1a2e"
_TEXT = "#8892b0"
_ACCENT = "#e94560"
_DIM = "#555555"
_EDGE = "#0f3460"

# Panel-grid geometry: 10 rows x 9 cols = 90 slots, first 87 filled.
_EXPECTED_PANELS = 87
_COLS = 9
_ROWS = 10
_N_EMPTY_SLOTS = _ROWS * _COLS - _EXPECTED_PANELS  # = 3 trailing blanks

# Revolution resolution: 48 azimuthal steps x 57 profile pts ≈ 2.7k verts.
# [Citation: hiad_geometry.generate_cross_section default n_per_segment=15
#  -> 15 + 14 + 14 + 14 = 57 meridian points]
_N_AZIMUTH = 48

# Shared 3D camera for every panel (T1: identical projection => comparable).
_ELEV = 22
_AZIM = -55

_REQUIRED_TOP_KEYS = ("history", "ccd_samples", "default", "optimized")
_REQUIRED_HISTORY_KEYS = (
    "iteration", "R_N", "r_tor", "half_cone_deg", "cost", "type",
)
_REQUIRED_POINT_KEYS = ("R_N", "r_tor", "half_cone_deg", "cost")


# ===========================================================================
# FUNCTION: load_results
# ===========================================================================
#
# AXIOMS:
#   A4: JSON is the only data source; validating keys up front converts
#       silent KeyError/NaN rendering failures into one actionable error.
# THEORIES:
#   T3: missing file -> FileNotFoundError with fix command; malformed JSON
#       -> ValueError with cause; wrong shape -> TypeError/ValueError.
# APPLICATIONS:
#   explicit if/raise checks — no bare except, no sentinel None returns.
# CITATIONS:
#   [3] hiad_optimizer.py output dict — history + ccd_samples contract
#   [4] render_bo_3d_plot.py load_results — validation precedent
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
        FileNotFoundError -- JSON does not exist (Murphy: the file WILL be
            missing on a fresh clone — print the exact fix command)
        TypeError -- JSON top-level or history entry has the wrong type
        ValueError -- JSON malformed, or required keys/entry fields absent
    """
    if not json_path.is_file():
        raise FileNotFoundError(
            f"Optimizer results not found: {json_path}\n"
            f"  Cause: hiad_optimizer.py has not been run (or was run "
            f"elsewhere).\n"
            f"  Fix:   python3 { _SRC_PYTHON / 'hiad_optimizer.py' }"
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
        raise TypeError(
            f"Expected top-level object in {json_path}, "
            f"got {type(data).__name__}"
        )

    missing = [k for k in _REQUIRED_TOP_KEYS if k not in data]
    if missing:
        raise ValueError(
            f"Missing required key(s) {missing} in {json_path}\n"
            f"  Present keys: {sorted(data.keys())}\n"
            f"  Fix:   re-run hiad_optimizer.py"
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
            raise TypeError(
                f"history[{i}] is {type(entry).__name__}, not dict"
            )
        lack = [k for k in _REQUIRED_HISTORY_KEYS if k not in entry]
        if lack:
            raise ValueError(
                f"history[{i}] missing keys {lack}; entry={entry}"
            )
    return data


# ===========================================================================
# FUNCTION: _point_panel
# ===========================================================================
#
# AXIOMS:   A1 — one dict per geometry, fixed key set.
# THEORIES: normalization here means downstream code sees ONE shape (T1).
# APPLICATIONS: called by build_panels for all four panel kinds.
# CITATIONS: [3] JSON schema; [4] validation style.
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(1)   CPU Time: <1 us
#   WCET: 10 us   Space Complexity: O(1)
# ===========================================================================
def _point_panel(label: str, kind: str, src: dict) -> dict:
    """Build one validated panel record from a JSON point dict.

    Parameters:
        label -- human-readable panel title
        kind  -- one of: default, ccd, initial, bo, optimum
        src   -- dict carrying R_N, r_tor, half_cone_deg, cost

    Returns:
        dict with keys: label, kind, R_N, r_tor, half_cone_deg, cost

    Raises:
        KeyError/TypeError -- required field absent or non-numeric
            (safety fallback: refuse to build a NaN panel silently)
    """
    lack = [k for k in _REQUIRED_POINT_KEYS if k not in src]
    if lack:
        raise ValueError(
            f"panel '{label}' source missing keys {lack}; src={src}"
        )
    rec = {
        "label": label,
        "kind": kind,
        "R_N": float(src["R_N"]),
        "r_tor": float(src["r_tor"]),
        "half_cone_deg": float(src["half_cone_deg"]),
        "cost": float(src["cost"]),
    }
    for key in _REQUIRED_POINT_KEYS:
        if not np.isfinite(rec[key]):
            raise ValueError(
                f"panel '{label}' has non-finite {key}={rec[key]!r}"
            )
    return rec


# ===========================================================================
# FUNCTION: build_panels
# ===========================================================================
#
# AXIOMS:
#   A4: every field is read from the validated `data` dict (load_results).
#   Panel order = default, CCD(15), history(70 by iteration), optimum.
# THEORIES:
#   T1: fixed order makes the figure reproducible (same JSON -> same grid).
#   If len != 87 the doc contract drifted — WARN loudly, still render
#   (a changed optimizer config is not a reason to withhold diagnostics).
# APPLICATIONS:
#   list comprehension over ccd + sorted history + two pinned references.
# CITATIONS:
#   [3] ccd_samples / history / default / optimized keys
#   [5] history iteration ordering (LHD 0..19, BO 20..69)
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(H log H) sort, H=70
#   CPU Time: <1 ms    WCET: 5 ms    Space Complexity: O(P), P=87 panels
# ===========================================================================
def build_panels(data: dict) -> list:
    """Assemble the ordered panel list (default + CCD + history + optimum).

    Parameters:
        data -- validated optimizer JSON (load_results output)

    Returns:
        list of panel dicts (label, kind, R_N, r_tor, half_cone_deg, cost)

    Raises:
        ValueError -- default/optimized/ccd_samples malformed (propagates
            from _point_panel; safety fallback: no half-built grid)
    """
    panels: list = [
        _point_panel("default (IRVE-3)", "default", data["default"]),
    ]
    for i, s in enumerate(data["ccd_samples"]):
        tag = s.get("label", f"#{i}")
        panels.append(_point_panel(f"CCD {i + 1}: {tag}", "ccd", s))
    for e in sorted(data["history"], key=lambda h: h["iteration"]):
        phase = "LHD" if e["type"] == "initial" else "BO"
        panels.append(
            _point_panel(f"{phase} #{e['iteration']}", e["type"], e)
        )
    panels.append(_point_panel("OPTIMUM", "optimum", data["optimized"]))

    n_ccd = sum(1 for p in panels if p["kind"] == "ccd")
    n_hist = sum(1 for p in panels if p["kind"] in ("initial", "bo"))
    print(
        f"  Panels built: {len(panels)} "
        f"(1 default + {n_ccd} CCD + {n_hist} history + 1 optimum)"
    )
    if len(panels) != _EXPECTED_PANELS:
        print(
            f"WARNING: expected {_EXPECTED_PANELS} panels (doc contract), "
            f"got {len(panels)}.\n"
            f"  Cause: optimizer config changed (n_initial/n_iter/ccd).\n"
            f"  Effect: grid renders anyway; row/col layout unchanged.",
            file=sys.stderr,
        )
    return panels


# ===========================================================================
# FUNCTION: cost_norm
# ===========================================================================
#
# AXIOMS:   A2 — costs span >900x; log norm required when all costs > 0.
# THEORIES: T2 — same Norm instance reused for EVERY panel color.
#           non-positive costs -> linear fallback + printed warning
#           (never emit NaN colormaps silently).
# APPLICATIONS: positivity check with warning, then LogNorm/Normalize.
# CITATIONS: [6] matplotlib LogNorm; [4] render_bo_3d_plot.cost_norm
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(P) min/max scan, P=87
#   CPU Time: <0.1 ms    WCET: 1 ms    Space Complexity: O(1)
# ===========================================================================
def cost_norm(costs: np.ndarray) -> Normalize:
    """Build a color normalization for cost values (log when safe).

    Parameters:
        costs -- 1D array of positive cost values

    Returns:
        matplotlib Normalize (LogNorm if all costs > 0 and spread > 0)
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
# FUNCTION: revolve_profile
# ===========================================================================
#
# AXIOMS:
#   A1: profile (x_i, r_i) is the meridian of an axisymmetric body.
#   A3: profile comes from hiad_geometry.generate_cross_section.
# THEORIES:
#   T1: the surface of revolution is
#         X(phi,i) = x_i
#         Y(phi,i) = r_i * cos(phi)
#         Z(phi,i) = r_i * sin(phi)
#       for phi in [0, 2pi); at r_i = 0 all columns collapse to the axis
#       (degenerate but valid — the flat-back center point).
# APPLICATIONS:
#   broadcast the meridian across _N_AZIMUTH azimuthal samples.
# CITATIONS:
#   [1] hiad_geometry.generate_cross_section
#   [2] stellarorion_pinn_trajectory.adb Get_HIAD_Cross_Section
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(N*M) grid build, N=57 pts, M=48 phi
#   CPU Time: ~0.2 ms per panel (vectorized numpy)  WCET: 2 ms
#   Space Complexity: O(N*M) ≈ 11 kB per panel (3 float64 grids)
#   Hardware Assumptions: any CPU; numpy broadcast (no GPU)
# ===========================================================================
def revolve_profile(x: np.ndarray, r: np.ndarray) -> tuple:
    """Revolve a meridian profile 360 deg about the axial (x) axis.

    Parameters:
        x -- axial coordinates [m], shape (N,)
        r -- radial coordinates [m], shape (N,), r >= 0

    Returns:
        (X, Y, Z) meshgrids of shape (N, _N_AZIMUTH)

    Raises:
        ValueError -- shape mismatch or non-finite entries
    """
    if x.shape != r.shape or x.ndim != 1:
        raise ValueError(
            f"revolve_profile expects 1D equal-length arrays, got "
            f"x{x.shape} r{r.shape}"
        )
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(r))):
        raise ValueError("revolve_profile: non-finite profile coordinates")
    phi = np.linspace(0.0, 2.0 * np.pi, _N_AZIMUTH, endpoint=False)
    cos_p = np.cos(phi)
    sin_p = np.sin(phi)
    X = x[:, None] * np.ones((1, _N_AZIMUTH))
    R = r[:, None]
    Y = R * cos_p[None, :]
    Z = R * sin_p[None, :]
    return X, Y, Z


# ===========================================================================
# FUNCTION: draw_panel
# ===========================================================================
#
# AXIOMS:   A1+A3 — geometry from shared generator; A2 — color from norm.
# THEORIES: T1 — identical view/limits across panels; T2 — shared LogNorm.
# APPLICATIONS: generate -> revolve -> plot_surface -> styled title.
# CITATIONS: [1] hiad_geometry; [6] LogNorm; [4] dark-theme colors.
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(N*M) surface emit, N=57, M=48
#   CPU Time: 15-60 ms per panel (Agg software raster)  WCET: 400 ms
#   Space Complexity: O(N*M) surface buffers
#   Hardware Assumptions: Agg backend (no GPU required)
# ===========================================================================
def draw_panel(ax, panel: dict, norm: Normalize, cmap, x_max: float, r_max: float) -> None:
    """Draw one 3D geometry panel colored by its cost.

    Parameters:
        ax     -- matplotlib 3D axes (already created by caller)
        panel  -- panel dict from build_panels
        norm   -- SHARED cost normalization (T2 — never per-panel)
        cmap   -- shared colormap (turbo, same as render_bo_3d_plot)
        x_max  -- global axial extent for equal x-limits
        r_max  -- global radial extent for equal y/z-limits

    Raises:
        ValueError -- generate_cross_section / revolve_profile rejected the
            parameters (safety fallback: caller catches and marks FAILED)
    """
    x, r = generate_cross_section(
        panel["R_N"], panel["r_tor"], panel["half_cone_deg"]
    )
    X, Y, Z = revolve_profile(x, r)
    face = cmap(norm(np.array([panel["cost"]])))[0]
    ax.plot_surface(
        X, Y, Z, facecolors=None, color=face,
        edgecolor="none", shade=True, linewidth=0, antialiased=False,
    )
    # Equal limits => shapes comparable across all 87 panels (T1)
    ax.set_xlim(0.0, x_max * 1.05)
    ax.set_ylim(-r_max * 1.15, r_max * 1.15)
    ax.set_zlim(-r_max * 1.15, r_max * 1.15)
    ax.view_init(elev=_ELEV, azim=_AZIM)
    ax.set_axis_off()
    title_color = _ACCENT if panel["kind"] == "optimum" else _TEXT
    weight = "bold" if panel["kind"] in ("optimum", "default") else "normal"
    ax.set_title(
        f"{panel['label']}\nJ={panel['cost']:.4g}",
        color=title_color, fontsize=5.5, fontweight=weight, pad=1,
    )


# ===========================================================================
# FUNCTION: compute_global_limits
# ===========================================================================
#
# AXIOMS:   limits must cover EVERY panel (else shapes clip differently).
# THEORIES: max over all profiles -> one shared box (comparability, T1).
# APPLICATIONS: first pass over generated profiles; failures skipped here
#               and reported per-panel during draw (isolation).
# CITATIONS: [1] profile generator.
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(P*N) scan   CPU Time: <1 ms (P=87, N=57)
#   WCET: 5 ms    Space Complexity: O(1)
# ===========================================================================
def compute_global_limits(panels: list) -> tuple:
    """Compute shared x/r limits across every renderable panel.

    Parameters:
        panels -- panel dicts from build_panels

    Returns:
        (x_max, r_max) floats strictly > 0

    Raises:
        ValueError -- no panel produced a valid profile (safety fallback:
            refuse to draw a grid with degenerate/zero limits)
    """
    x_max = 0.0
    r_max = 0.0
    n_ok = 0
    for p in panels:
        try:
            x, r = generate_cross_section(
                p["R_N"], p["r_tor"], p["half_cone_deg"]
            )
        except ValueError as exc:
            print(
                f"WARNING: limits pass skipped panel '{p['label']}': {exc}",
                file=sys.stderr,
            )
            continue
        x_max = max(x_max, float(np.max(x)))
        r_max = max(r_max, float(np.max(r)))
        n_ok += 1
    if n_ok == 0 or x_max <= 0.0 or r_max <= 0.0:
        raise ValueError(
            f"compute_global_limits: no valid profiles "
            f"(n_ok={n_ok}, x_max={x_max}, r_max={r_max})"
        )
    print(f"  Global limits: x<= {x_max:.4f} m, r<= {r_max:.4f} m "
          f"({n_ok}/{len(panels)} profiles OK)")
    return x_max, r_max


# ===========================================================================
# FUNCTION: main
# ===========================================================================
#
# AXIOMS:
#   A4: one JSON load feeds every panel (single source of truth).
#   A figure with any failed panel is still SAVED for debugging and the
#   process exits NON-ZERO (no silent partial success).
# THEORIES:
#   T3: missing/bad JSON -> top-level except -> return 1, never exit 0.
# APPLICATIONS:
#   load -> panels -> limits -> draw loop -> colorbar -> savefig.
# CITATIONS:
#   [4] render_bo_3d_plot.main — structure/exit-code precedent
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(P*N*M) draw dominates; P=87, N=57, M=48
#   CPU Time: 8-30 s typical (87 Agg 3D surfaces at dpi=100)
#   WCET: 120 s on a cold font cache / slow laptop
#   Space Complexity: O(P*N*M) ≈ 1 MB surface buffers + figure raster
#   Hardware Assumptions: macOS arm64, Agg software rendering (no GPU)
#   Derivation: draw(87) x plot_surface(57*48 verts) + savefig raster
# ===========================================================================
def main() -> int:
    """Render hiad_geometry_grid.png (87 3D panels + colorbar).

    Returns:
        0 on full success, 1 on any data/panel/save failure (never 0 on
        error).
    """
    print("=" * 72)
    print("  Rendering 87-panel HIAD 3D geometry grid")
    print("=" * 72)
    panel_errors: list = []

    try:
        # --- Step 1: load + validate (A4 / T3) ---
        print(f"\n[1/4] Loading {_RESULTS_JSON} ...")
        data = load_results(_RESULTS_JSON)
        panels = build_panels(data)

        # --- Step 2: shared norm + limits (A2 / T1) ---
        print("\n[2/4] Computing shared color norm and axis limits ...")
        costs = np.asarray([p["cost"] for p in panels], dtype=float)
        norm = cost_norm(costs)
        cmap = plt.get_cmap("turbo")
        x_max, r_max = compute_global_limits(panels)

        # --- Step 3: draw ---
        print(f"\n[3/4] Drawing {len(panels)} 3D panels "
              f"({_ROWS}x{_COLS} grid) ...")
        fig = plt.figure(figsize=(18, 24), facecolor=_BG)
        gs = fig.add_gridspec(
            _ROWS, _COLS,
            left=0.03, right=0.93, top=0.93, bottom=0.04,
            wspace=0.08, hspace=0.28,
        )
        axes_list = []
        for i, panel in enumerate(panels):
            ax = fig.add_subplot(gs[i // _COLS, i % _COLS], projection="3d")
            axes_list.append(ax)
            try:
                draw_panel(ax, panel, norm, cmap, x_max, r_max)
            except Exception as exc:  # noqa: BLE001 — panel isolation is deliberate: one bad geometry must not kill the other 86
                panel_errors.append(panel["label"])
                print(f"ERROR panel '{panel['label']}': {exc}",
                      file=sys.stderr)
                traceback.print_exc()
                ax.set_title(f"{panel['label']}\nFAILED",
                             color=_ACCENT, fontsize=5.5, fontweight="bold")
            if (i + 1) % 15 == 0:
                print(f"  ... {i + 1}/{len(panels)} panels drawn")

        # Trailing empty slots (90 - 87 = 3) — blank, no axes clutter
        for slot in range(len(panels), _ROWS * _COLS):
            ax = fig.add_subplot(
                gs[slot // _COLS, slot % _COLS], projection="3d"
            )
            ax.set_axis_off()

        # --- Shared colorbar (T2) via fixed fig axes (robust w/ 87 axes) ---
        cax = fig.add_axes([0.945, 0.15, 0.012, 0.70])
        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])
        cb = fig.colorbar(sm, cax=cax)
        cb.ax.tick_params(colors=_DIM, labelsize=8)
        cb.set_label("cost J  (log scale)", color=_TEXT, fontsize=10)

        imp = data.get("improvement", {})
        opt = data["optimized"]
        fig.suptitle(
            "StellarOrion HIAD — 87-Panel Geometry Grid "
            "(color = cost J, log scale)\n"
            f"1 default + 15 CCD + 70 history (20 LHD + 50 BO) + optimum · "
            f"best J = {opt['cost']:.4f} · "
            f"Cd improvement = {imp.get('cd_pct', float('nan')):.2f}% · "
            f"view elev={_ELEV} azim={_AZIM}",
            color="white", fontsize=14, fontweight="bold", y=0.965,
        )

        # --- Step 4: save + verify (A2 of module: no silent partial) ---
        print(f"\n[4/4] Saving {_OUTPUT_PNG} ...")
        fig.savefig(
            str(_OUTPUT_PNG), dpi=100, facecolor=_BG, bbox_inches="tight",
        )
        plt.close(fig)
        if not _OUTPUT_PNG.is_file():
            raise RuntimeError(
                f"savefig reported success but file missing: {_OUTPUT_PNG}"
            )
        size_kb = _OUTPUT_PNG.stat().st_size / 1024.0
        print(f"  Saved: {_OUTPUT_PNG} ({size_kb:.1f} kB)")

    except Exception as exc:
        # Top-level safety net: never exit silently (verbose error reporting)
        print(f"\nFATAL: {exc!r}", file=sys.stderr)
        traceback.print_exc()
        return 1

    if panel_errors:
        print(
            f"\nFAILED panels ({len(panel_errors)}): {panel_errors}\n"
            f"  Figure saved for debugging, but this run is NOT a success.",
            file=sys.stderr,
        )
        return 1

    print("\nAll panels rendered successfully.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
