#!/usr/bin/env python3
# ===========================================================================
# SCRIPT: render_geometry_4views.py
# ===========================================================================
#
# AXIOMS:
#   A1  The HIAD geometry is fully determined by the triple
#       (R_N, r_tor, half_cone_deg) — no other shape parameter exists.
#   A2  A single 3/4 view hides half the body.  A report figure that claims
#       to show "the full 3D model" must show it from several camera
#       angles, otherwise the reader cannot see the whole surface.
#   A3  `hiad_geometry.generate_cross_section` is the SINGLE meridian
#       source, and `render_geometry_grid.revolve_profile` is the SINGLE
#       surface-of-revolution implementation.  This script imports both —
#       it never re-derives the 4-segment profile maths nor the
#       revolution broadcast (no copy-paste divergence, per the
#       no_copy_paste_divergence rule).
#   A4  Design data comes ONLY from `hiad_optimization_results.json`
#       (pure post-processing — this script NEVER re-runs the optimizer,
#       matching render_geometry_grid.py A4).
#   A5  The body is axisymmetric.  Therefore the SILHOUETTE is invariant
#       under azimuth and only the shading / feature orientation changes.
#       This is a physical fact, not a rendering bug — the figure states
#       it explicitly so nobody reads the four panels as four different
#       shapes.
#
# THEORIES:
#   T1  Revolving the shared meridian profile 360 deg about the axial axis
#       yields the axisymmetric HIAD body (same theorem as the grid).
#   T2  Four azimuths (0/90/180/270) at one fixed elevation form a
#       turntable that exposes the full surface: every point of the body
#       is visible in at least two of the four views.
#   T3  A missing or malformed results JSON must fail LOUDLY.  Inventing a
#       default geometry would silently publish a figure of the wrong
#       vehicle.
#   T4  Colour by axial position (not by cost) — the purpose of THIS
#       figure is shape legibility; cost colouring already exists in
#       `hiad_geometry_grid.png`.
#
# APPLICATIONS:
#   load designs -> generate_cross_section -> revolve_profile ->
#   4 x plot_surface (one per azimuth) -> savefig raster.
#
# CITATIONS:
#   [1] hiad_geometry.generate_cross_section (line 43) — Ada line-for-line
#       port of stellarorion_pinn_trajectory.adb::Get_HIAD_Cross_Section
#   [2] render_geometry_grid.revolve_profile (line 424) — shared revolution
#   [3] src/python/hiad_optimization_results.json — written by
#       hiad_optimizer.py (round-1 optimum on disk; `optimized_round2` is
#       absent as of 2026-10-08, handled as a loud warning not a crash)
#   [4] Rapisarda (2023) Sec. 3.7 — HIAD 4-segment flat-skin profile
#   [5] matplotlib mplot3d `plot_surface` + `view_init` documentation
#
# AUTHOR: Albert Starfield Wahyu Suryo Samudro
#
# TIMING ANALYSIS
#   Estimated Processing Time: 2 figures x 4 panels x O(N*M) surface emit,
#       N=57 meridian pts, M=48 azimuth samples
#   CPU Time: 15-60 ms per panel (Agg software raster)   WCET: 500 ms/panel
#   Space Complexity: O(N*M) per panel (~11 kB x 4 grids) + raster buffers
#   Hardware Assumptions: any CPU; Agg backend, no GPU required
# ===========================================================================

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")  # [5] headless-safe: must precede pyplot import
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize

# -- Paths -------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent              # stellarorion_program_proc/
_SRC_PYTHON = _PROJECT_ROOT / "src" / "python"
_RESULTS_JSON = _SRC_PYTHON / "hiad_optimization_results.json"

# -- Import the SHARED geometry + revolution code (A3 — no duplication) ------
sys.path.insert(0, str(_SRC_PYTHON))
sys.path.insert(0, str(_SCRIPT_DIR))

try:
    from hiad_geometry import generate_cross_section  # [1]
except ImportError as exc:  # pragma: no cover - import-time safety fallback
    raise SystemExit(
        f"[4views] FATAL: cannot import hiad_geometry from {_SRC_PYTHON}: {exc}"
    ) from exc

try:
    from render_geometry_grid import (  # [2]
        _ELEV,
        revolve_profile,
    )
except ImportError as exc:  # pragma: no cover - import-time safety fallback
    raise SystemExit(
        f"[4views] FATAL: cannot import revolve_profile from "
        f"{_SCRIPT_DIR}/render_geometry_grid.py: {exc}"
    ) from exc

# -- Presentation constants (dark theme, same palette as the grid figure) ----
_BG = "#0a0a0f"
_PANEL = "#1a1a2e"
_TEXT = "#8892b0"
_ACCENT = "#e94560"
_DIM = "#555555"

# -- Camera turntable (T2) ---------------------------------------------------
_AZIMUTHS = (0.0, 90.0, 180.0, 270.0)   # deg, four turntable stations
_AZIMUTH_LABELS = ("az = 0\u00b0", "az = 90\u00b0", "az = 180\u00b0", "az = 270\u00b0")

_FIGSIZE_IN = (9.0, 9.0)
_DPI = 200


# ===========================================================================
# FUNCTION: load_designs
# ===========================================================================
#
# AXIOMS:   A4 — data only from the results JSON.
# THEORIES: T3 — malformed input fails loudly, never invents a vehicle.
# APPLICATIONS: read -> validate keys -> return the two headline designs.
# CITATIONS: [3] hiad_optimization_results.json
#
# TIMING ANALYSIS
#   CPU Time: <5 ms (single small JSON read)   WCET: 50 ms
#   Space Complexity: O(1)
# ===========================================================================
def load_designs(json_path: Path = _RESULTS_JSON) -> list:
    """Load the IRVE-3 baseline and the optimized design from the results JSON.

    Parameters:
        json_path -- path to hiad_optimization_results.json

    Returns:
        list of dicts, each with keys:
            key        -- short identifier ("irve3", "optimized")
            label      -- human title for the figure
            R_N        -- nose radius [m]
            r_tor      -- torus radius [m]
            half_cone  -- half-cone angle [deg]
            cost       -- objective J (dimensionless)
            cd         -- drag coefficient
            heat_load  -- total heat load [J/cm^2]

    Raises:
        SystemExit -- if the file is missing, unreadable, not valid JSON, or
            lacks the required `default` / `optimized` entries (T3: loud).
    """
    if not json_path.exists():
        raise SystemExit(
            f"[4views] FATAL: results JSON not found at {json_path}. "
            f"Run hiad_optimizer.py first — refusing to invent a geometry (T3)."
        )
    try:
        with json_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"[4views] FATAL: cannot parse {json_path}: {exc}"
        ) from exc

    required = ("default", "optimized")
    missing = [k for k in required if k not in data]
    if missing:
        raise SystemExit(
            f"[4views] FATAL: {json_path} is missing key(s) {missing}. "
            f"Present keys: {sorted(data.keys())}"
        )

    designs = []
    for key, src in (("irve3", data["default"]), ("optimized", data["optimized"])):
        try:
            designs.append(
                {
                    "key": key,
                    "label": (
                        "IRVE-3 validation model (baseline)"
                        if key == "irve3"
                        else "Optimized topology (round-1 optimum)"
                    ),
                    "R_N": float(src["R_N"]),
                    "r_tor": float(src["r_tor"]),
                    "half_cone": float(src["half_cone_deg"]),
                    "cost": float(src["cost"]),
                    "cd": float(src.get("Cd", float("nan"))),
                    "heat_load": float(src.get("total_heat_load_Jcm2", float("nan"))),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(
                f"[4views] FATAL: malformed '{key}' entry in {json_path}: {exc}"
            ) from exc

    if "optimized_round2" in data:
        print("[4views] note: 'optimized_round2' present but not rendered here; "
              "the round-2 gate-corrected optimum is shown in hiad_geometry_grid.png.")
    else:
        print("[4views] note: no 'optimized_round2' in the JSON — the optimized "
              "figure uses the round-1 optimum (run --validate-round2 for R2).")

    return designs


# ===========================================================================
# FUNCTION: render_four_views
# ===========================================================================
#
# AXIOMS:   A2 — the full body must be visible; A3 — shared generator only.
# THEORIES: T1 (revolve -> axisymmetric body), T2 (turntable covers the
#           surface), T4 (axial-position colour = shape legibility).
# APPLICATIONS: generate -> revolve -> 4x plot_surface -> savefig.
# CITATIONS: [1] profile generator; [2] revolve_profile; [5] mplot3d.
#
# TIMING ANALYSIS
#   Estimated Processing Time: O(4*N*M) surface emit + 1 raster
#   CPU Time: ~0.5-2 s (Agg)   WCET: 8 s
#   Space Complexity: O(N*M) per panel
# ===========================================================================
def render_four_views(design: dict, out_path: Path) -> None:
    """Render one design as a 2x2 turntable of the full 3D body.

    Parameters:
        design   -- dict from load_designs
        out_path -- PNG destination

    Returns:
        None (writes the raster to out_path)

    Raises:
        ValueError -- if generate_cross_section rejects the parameters, or
            revolve_profile rejects the arrays (caller decides policy).
        OSError    -- if the raster cannot be written.
    """
    x, r = generate_cross_section(  # [1] single meridian source (A3)
        design["R_N"], design["r_tor"], design["half_cone"]
    )
    X, Y, Z = revolve_profile(x, r)  # [2] single revolution source (A3)

    # T4: colour by axial position so the silhouette reads as a shape.
    # The norm is shared by all four panels of THIS figure (comparability).
    axial_norm = Normalize(vmin=float(np.min(x)), vmax=float(np.max(x)))
    # [5] matplotlib >= 3.9 removed `matplotlib.cm.get_cmap`; the supported
    # public accessor is `matplotlib.pyplot.get_cmap` (verified on the
    # project venv: matplotlib 3.11.2).
    cmap = plt.get_cmap("turbo")

    # facecolors must match the (N, M) grid: broadcast the per-meridian
    # colour across all azimuth columns -> shape (N, M, 4).
    base = cmap(axial_norm(x))[:, None, :]                       # (N, 1, 4)
    facecolors = np.repeat(base, X.shape[1], axis=1)             # (N, M, 4)

    x_max = float(np.max(x))
    r_max = float(np.max(np.abs(r))) if np.any(r) else 1.0
    if not np.isfinite(x_max) or not np.isfinite(r_max) or r_max <= 0.0:
        raise ValueError(
            f"render_four_views: degenerate profile for {design['key']} "
            f"(x_max={x_max}, r_max={r_max}) — refusing to draw."
        )

    fig = plt.figure(figsize=_FIGSIZE_IN, dpi=_DPI, facecolor=_BG)
    #  WHY va="top" + y=0.98: the suptitle is TWO lines at fontsize 11, so its
    #  glyph block runs ~0.98 -> ~0.94 in figure coords.  The axisymmetry note
    #  below used to be placed at y=0.930 with the default va="baseline", which
    #  put its glyph body at ~0.930-0.945 and made "Body of revolution" collide
    #  with the "R_N = ..." line (defect measured 2026-10-08 by pixel
    #  inspection).  Anchoring the title from the top and moving the note to
    #  the BOTTOM margin removes the collision entirely.
    fig.suptitle(
        f"{design['label']}\n"
        f"R_N = {design['R_N']:.4f} m    r_tor = {design['r_tor']:.4f} m    "
        f"half-cone = {design['half_cone']:.3f}\u00b0    J = {design['cost']:.6f}",
        color=_TEXT, fontsize=11, y=0.98, va="top",
    )
    #  A5: the body is axisymmetric, so this note belongs in the figure
    #  margin, not in the header block where it collided with the title.
    fig.text(
        0.5, 0.012,
        "Body of revolution \u2014 axisymmetric, so the silhouette is invariant "
        "under azimuth; the four views differ in shading / feature orientation.",
        color=_DIM, fontsize=8, ha="center", va="bottom",
    )

    for idx, azim in enumerate(_AZIMUTHS):
        ax = fig.add_subplot(2, 2, idx + 1, projection="3d")
        ax.set_facecolor(_PANEL)
        ax.plot_surface(
            X, Y, Z,
            facecolors=facecolors,
            edgecolor="none", shade=True, linewidth=0, antialiased=False,
        )
        # Equal limits across every panel so shapes stay comparable (T1).
        ax.set_xlim(0.0, x_max * 1.05)
        ax.set_ylim(-r_max * 1.15, r_max * 1.15)
        ax.set_zlim(-r_max * 1.15, r_max * 1.15)
        ax.view_init(elev=_ELEV, azim=azim)  # [5] turntable station (T2)
        ax.set_box_aspect((1.0, 1.0, 1.0))
        ax.set_axis_off()
        ax.set_title(_AZIMUTH_LABELS[idx], color=_TEXT, fontsize=9, pad=0)

    # One shared colorbar describing the axial-position colouring (T4).
    mappable = cm.ScalarMappable(norm=axial_norm, cmap=cmap)
    cbar = fig.colorbar(mappable, ax=fig.axes, fraction=0.025, pad=0.02,
                        shrink=0.6)
    cbar.set_label("axial position [m]", color=_TEXT, fontsize=8)
    cbar.ax.tick_params(colors=_TEXT, labelsize=7)
    cbar.outline.set_edgecolor(_DIM)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=_DPI, facecolor=_BG, bbox_inches="tight")
    plt.close(fig)
    print(f"[4views] wrote {out_path} "
          f"({X.shape[0]}x{X.shape[1]} verts, 4 azimuths)")


# ===========================================================================
# FUNCTION: main
# ===========================================================================
#
# AXIOMS:   A2 — both headline models get a full 4-angle figure.
# THEORIES: each figure is independent; one failure must not abort the other
#           (safety_fallback rule) — but any failure sets a non-zero exit.
# APPLICATIONS: parse args -> load designs -> render 2 figures -> report.
# CITATIONS: [3] results JSON.
# ===========================================================================
def main() -> int:
    """Render the IRVE-3 and optimized 4-angle figures; return a process code.

    Parameters:
        (none — CLI only)

    Returns:
        0 if every figure was written, 1 if any figure failed.

    Raises:
        SystemExit -- from load_designs on missing/malformed results JSON.
    """
    parser = argparse.ArgumentParser(
        description="Render IRVE-3 and optimized HIAD bodies as 2x2 "
                    "four-camera-angle (turntable) 3D figures."
    )
    parser.add_argument(
        "--outdir", type=Path, default=_PROJECT_ROOT,
        help="Directory for the two PNGs (default: project root, matching "
             "render_geometry_grid.py).",
    )
    args = parser.parse_args()

    outdir = args.outdir if args.outdir.is_absolute() else (_PROJECT_ROOT / args.outdir)
    targets = {
        "irve3": outdir / "irve3_validation_3d_4views.png",
        "optimized": outdir / "optimized_topology_3d_4views.png",
    }

    designs = load_designs()
    failures = []
    for design in designs:
        out_path = targets[design["key"]]
        try:
            render_four_views(design, out_path)
        except (ValueError, OSError) as exc:
            # Safety fallback: report the exact failure, keep rendering the
            # remaining design, and surface a non-zero exit at the end.
            print(f"[4views] ERROR rendering {design['key']}: {exc}",
                  file=sys.stderr)
            failures.append((design["key"], str(exc)))

    if failures:
        print(f"[4views] FAILED: {failures}", file=sys.stderr)
        return 1
    print("[4views] OK: 2 figures written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
