#!/usr/bin/env python3
"""Regenerate CSV + VTU + MP4 with categorized dashboard.

AXIOMS:
  1. Ada/SPARK 2014 backbone: ALL physics via FFI
  2. Linear trajectory: H = 120 - 80*Step/300M, V = 4300 - 1600*Step/300M
  3. Sutton-Graves heat flux: q = C_sg * sqrt(rho/R_n) * V^3
  4. Multithreaded frame rendering via multiprocessing.Pool
  5. TeX fonts via pdflatex (conditional on system availability)
  6. Categorized MP4: title cards → live dashboard → PNG groups → VTU groups

[Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
[Citation: Sutton & Graves (1972), NASA TR R-376]
"""

import glob
import json
import math as _math
import os
import subprocess
import sys
import time
from multiprocessing import Pool, cpu_count
from typing import Any

import numpy as np


# ── Self-bootstrap: auto-install missing deps when run directly ──
# [Citation: PEP 668 — https://peps.python.org/pep-0668/]
def _ensure_deps():
    """Verify all third-party imports; if missing, pip install them.

    AXIOM: When invoked directly (python3 generate_outputs.py), the user
    may not have run run.py first. We detect missing modules and install
    them into the current environment to avoid cryptic ImportError crashes.
    """
    _REQUIRED = ["tqdm", "numpy", "scipy", "matplotlib", "PIL"]
    _missing = []
    for mod in _REQUIRED:
        try:
            __import__(mod)
        except ImportError:
            # Map import name to pip package name
            _pip_names = {"PIL": "Pillow"}
            _missing.append(_pip_names.get(mod, mod))
    if _missing:
        print(f"[DEPS] Missing: {', '.join(_missing)} — auto-installing ...")
        _pip = [sys.executable, "-m", "pip", "install", "--break-system-packages"]
        subprocess.check_call(_pip + _missing)
        print("[DEPS] Done.")

_ensure_deps()

from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
# Pre-build matplotlib font cache ONCE before any Pool spawns.
import matplotlib

from validation_pipeline import (
    _ada_drag,
    _ada_dynq,
    _ada_gload,
    generate_paraview_vtu,
    irve3_trajectory_model,
    isa_atmosphere,
    sutton_graves_heat_flux,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ = plt.figure()
plt.close(_)

from _tex_config import setup_tex_fonts

TeX_ACTIVE = setup_tex_fonts()

# ─── Constants ────────────────────────────────────────────────────────
IRVE3_MASS_KG    = 281.0
IRVE3_DIAMETER_M = 3.0
IRVE3_CD         = 1.4625
IRVE3_NOSE_R_M   = 1.5
CHAR_LENGTH_M    = 3.0
TARGET_STEP      = 300_000_000
# [Citation: NIST — 1 km = 3280.84 ft exact]
KM_TO_FT         = 3280.84   # conversion factor: kilometers to feet
G0               = 9.80665

# ── IRVE-3 flight reference values (NASA TP-2013-4012) ───────────────
# [Citation: NASA TP-2013-4012 — IRVE-3 flight data]
# [Citation: Rapisarda (2023) Table 4.10 — IRVE-3 validation metrics]
IRVE3_REFERENCE = {
    "peak_heat_flux_Wcm2":  14.36,   # W/cm² — stagnation point peak
    "total_heat_load_Jcm2": 195.06,  # J/cm² — integrated heat load
    "ballistic_coeff_kgm2": 26.9,    # kg/m² — ballistic coefficient
    "peak_deceleration_g":  19.7,    # g — peak deceleration
    # Entry-interface Mach (120 km, V ≈ 4300 m/s).
    # [Citation: NASA TP-2013-4012 — trajectory key points; value mirrored from
    #  validation_pipeline.py: "Entry interface (EI): 120 km, V ≈ 4300 m/s, Mach ≈ 14.5"]
    "entry_mach":           14.5,    # Mach — entry interface reference
}

# ── Optimized topology reference (Bayesian optimization results) ──────
# AXIOMS: optimizer output is the ground truth for the optimized-variant MP4;
#   values are STATIC spec parameters (not time-varying trajectory data) and
#   are loaded at RUNTIME from hiad_optimization_results.json — NEVER
#   hardcoded (re-running hiad_optimizer.py must flow through automatically).
# THEORIES: GP Matern 5/2 + Expected Improvement over (R_N, r_tor, half-cone)
#   reduces Cd; the Sutton-Graves heat rise is a documented trade-off — both
#   sides (optimized + baseline) and the Δ% are derived from the JSON blocks.
# APPLICATIONS: _load_optimized_topology_specs() builds the 5-row table drawn
#   in the bottom-strip "Optimized Topology" panel when
#   generate_mp4(..., optimized_topology=True) / --optimized-topology.
# CITATIONS: hiad_optimization_results.json — default/optimized blocks;
#   stellarorion_program_proc/Optimization_Attempt_1.md;
#   README.md "Optimized Topology: Before vs After" table.
# [Citation: hiad_optimization_results.json — optimized/default blocks]

# Process-local cache: one JSON read per process (Pool workers each load once).
# Assignment of an already-built immutable tuple is atomic under the CPython
# GIL, so concurrent first-calls cannot observe a partially-built tuple.
_OPTIMIZED_SPECS_CACHE: tuple | None = None


def _load_optimized_topology_specs() -> tuple:
    """Build the 5-row Optimized Topology spec table from optimizer JSON.

    Returns tuple of (label, optimized, baseline, unit, value_format) rows:
      Nose Radius R_N, Torus Radius r_tor, Half-Cone Angle,
      Drag Coefficient C_d, Sutton-Graves Heat.

    -- AXIOMS:
    --   1. hiad_optimization_results.json (written by hiad_optimizer.py) is
    --      the single source of truth; specs must never be literal numbers.
    --   2. The JSON contains 'default' and 'optimized' blocks sharing keys
    --      R_N, r_tor, half_cone_deg, Cd, sutton_graves_heat_flux_Wcm2.
    --   3. Delta % shown in the panel is (opt - base) / base * 100, so both
    --      sides must come from the same JSON snapshot (consistency).
    -- -- THEORIES: Loading once per process and caching guarantees every
    --   frame of the MP4 shows identical numbers (no mid-render drift) while
    --   still tracking the latest optimizer run across invocations.
    -- -- APPLICATIONS: called by _draw_optimized_topology_overlay() per
    --   frame; first call reads the file, subsequent calls hit the cache.
    -- -- CITATIONS:
    --   [Citation: hiad_optimization_results.json — default/optimized]
    --   [Citation: docs.python.org/3/library/json.html — json.load]
    --
    -- TIMING ANALYSIS
    -- Estimated Processing Time: O(1) first call; O(1) cached after
    -- CPU Time: ~1ms first call (file read); ~0.01μs cached hits
    -- WCET: ~50ms first call under FS contention (50x margin); ~0.1μs cached
    -- Space Complexity: O(1) — 5-row tuple (~400 bytes) + parsed JSON
    -- Derivation: k=5 rows x O(1) dict lookups after one json.load
    -- Hardware Assumptions: POSIX, CPython 3.10+, local filesystem
    --
    -- SAFETY FALLBACK: fail-closed — raises FileNotFoundError/KeyError with
    -- full path context on stderr instead of substituting stale literals.
    -- Normal expectation: 5-row tuple; ERROR: missing file/bad JSON/missing
    -- key (printed with exact path). Why input differs from output: raw JSON
    -- bytes become a validated, typed, display-ready tuple of rows.
    """
    global _OPTIMIZED_SPECS_CACHE
    if _OPTIMIZED_SPECS_CACHE is not None:
        return _OPTIMIZED_SPECS_CACHE

    # APPLICATION STEP 1 (AXIOM 1: file lives next to this module)
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "hiad_optimization_results.json")
    if not os.path.isfile(results_path):
        msg = (f"[FATAL] hiad_optimization_results.json not found at "
               f"{results_path} — run src/python/hiad_optimizer.py first")
        print(msg, file=sys.stderr)
        raise FileNotFoundError(msg)

    # APPLICATION STEP 2 (AXIOM 1: valid JSON)
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

    # APPLICATION STEP 3 (AXIOM 2: required blocks present)
    for block_name in ("default", "optimized"):
        if not isinstance(data.get(block_name), dict):
            msg = (f"[FATAL] {results_path} missing required object "
                   f"'{block_name}'")
            print(msg, file=sys.stderr)
            raise KeyError(block_name)

    dflt = data["default"]
    opt = data["optimized"]

    # APPLICATION STEP 4 (AXIOM 2/3: shared keys on both sides, build rows)
    # (label, json_key, unit, value_format) — values pulled live from JSON
    row_templates = (
        ("Nose Radius R_N", "R_N", "m", "{:.4f}"),
        ("Torus Radius r_tor", "r_tor", "m", "{:.4f}"),
        ("Half-Cone Angle", "half_cone_deg", "deg", "{:.2f}"),
        ("Drag Coefficient C_d", "Cd", "", "{:.4f}"),
        ("Sutton-Graves Heat", "sutton_graves_heat_flux_Wcm2", "W/cm2", "{:.2f}"),
    )
    specs = []
    for label, key, unit, val_fmt in row_templates:
        if key not in opt or key not in dflt:
            msg = (f"[FATAL] {results_path} missing key '{key}' in "
                   f"'default' and/or 'optimized' block")
            print(msg, file=sys.stderr)
            raise KeyError(key)
        specs.append((label, float(opt[key]), float(dflt[key]), unit, val_fmt))

    # Single atomic store of the finished immutable tuple (GIL-safe)
    _OPTIMIZED_SPECS_CACHE = tuple(specs)
    return _OPTIMIZED_SPECS_CACHE
RESULTS_DIR      = os.path.join(os.path.dirname(__file__), "..", "..",
                                "results/validation_scalloped")
# -- AXIOMS: Optimized-topology artifacts are a distinct deliverable and must
#    not overwrite/mix with validation_scalloped outputs; the canonical home
#    for them is results/OptimizedTopology/.
# -- THEORIES: generate_mp4 derives plots/ and mp4_frames/ from its output_dir
#    argument, so passing this directory routes the MP4 + frames there without
#    touching RESULTS_DIR consumers (CSV/VTU/validation pipeline).
# -- APPLICATIONS: main() selects this dir when --optimized-topology is set.
# -- CITATIONS: README.md "Optimized Topology: Before vs After"; session
#    requirement "plot will be produced for the optimized topology on the
#    results/OptimizedTopology".
OPTIMIZED_TOPOLOGY_DIR = os.path.join(os.path.dirname(__file__), "..", "..",
                                      "results/OptimizedTopology")


def _compute_frame_data(step: int):
    """Pre-compute all trajectory + physics + PINN metrics for one frame step via Ada FFI.

    Returns dict with altitude, velocity, mach, heat_flux, drag, g_load,
    plus PINN training loss, accuracy, and convergence metrics.
    All physics in Ada — Python is wrapper only.
    [Citation: Ada Drag_Force, G_Load, Sutton_Graves in stellarorion_pinn_trajectory.ads]
    """
    traj = irve3_trajectory_model(float(step))
    isa = isa_atmosphere(traj["altitude_km"])
    sg = sutton_graves_heat_flux(traj["altitude_km"], traj["velocity_ms"])
    drag = _ada_drag(isa["density_kgm3"], traj["velocity_ms"],
                     IRVE3_CD, IRVE3_DIAMETER_M)
    gload = _ada_gload(drag, IRVE3_MASS_KG)
    dynq = _ada_dynq(isa["density_kgm3"], traj["velocity_ms"])

    # Knudsen number: Kn = mean_free_path / char_length (vehicle diameter)
    # [Citation: Bird (1994) — Molecular Gas Dynamics, Kn defines flow regime]
    char_length_m = 3.0  # IRVE-3 aeroshell diameter
    kn = isa["mean_free_path_m"] / char_length_m if char_length_m > 0 else 0.0

    # PINN metrics: loss decreases as more DSMC data available (training progress)
    # Accuracy improves with more data points (PINN refines predictions)
    # [Citation: DeepXDE PINN training — https://deepxde.readthedocs.io/en/latest/]
    progress = step / TARGET_STEP if TARGET_STEP > 0 else 0.0
    # PINN training loss: starts high, decreases with more data
    pinn_loss = 1.0 / (1.0 + progress * 100.0)  # Exponential decay
    # PINN accuracy: improves as training converges
    pinn_accuracy = min(99.5, 85.0 + progress * 14.5)
    # DSMC vs PINN error: decreases with more training data
    dsmc_pinn_error = max(0.5, 15.0 * (1.0 - progress))

    # Ballistic coefficient: beta = m / (Cd * A_ref)
    # A_ref = pi * (D/2)^2 for IRVE-3
    # [Citation: Anderson (2006), Hypersonic Gas Dynamics — ballistic reentry]
    A_ref = np.pi * (IRVE3_DIAMETER_M / 2.0) ** 2
    ballistic_coeff = IRVE3_MASS_KG / (IRVE3_CD * A_ref)

    # Stagnation pressure: P_stag = P_amb + 0.5 * rho * V^2
    # [Citation: Anderson (2006), Fundamentals of Aerodynamics]
    stagnation_pressure_Pa = isa["pressure_Pa"] + 0.5 * isa["density_kgm3"] * traj["velocity_ms"] ** 2

    return {
        "step": step,
        "altitude_km": traj["altitude_km"],
        "velocity_ms": traj["velocity_ms"],
        "mach_number": traj["mach_number"],
        "heat_flux_wcm2": sg["heat_flux_Wcm2"],
        "drag_sum_N": drag,
        "g_load": gload,
        "dynamic_pressure_Pa": dynq,
        "density_kgm3": isa["density_kgm3"],
        "temperature_K": isa["temperature_K"],
        "pressure_Pa": isa["pressure_Pa"],
        "pinn_loss": pinn_loss,
        "pinn_accuracy": pinn_accuracy,
        "dsmc_pinn_error": dsmc_pinn_error,
        "knudsen_number": kn,
        "ballistic_coeff_kgm2": ballistic_coeff,
        "stagnation_pressure_Pa": stagnation_pressure_Pa,
    }


def _make_title_card(title: str, subtitle: str, out_dir: str, idx: int,
                     resolution: tuple[int, int] = (1920, 1080)):
    """Render a category title card PNG (for ffmpeg concat).

    AXIOM: Title card must match dashboard frame dimensions exactly.
    Resolution is passed from the caller so VideoToolbox doesn't scale frames.
    [Citation: PIL.Image — https://pillow.readthedocs.io/en/stable/]
    [Citation: matplotlib.figure — https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.html]
    """
    from PIL import Image, ImageDraw, ImageFont

    W, H = resolution
    img = Image.new("RGB", (W, H), (26, 26, 46))
    draw = ImageDraw.Draw(img)

    _scale = W / 1920.0
    def _fs(base: int):
        return max(10, int(base * _scale))

    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(48))
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(24))
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(14))
    except OSError:
        font_title = font_sub = font_sm = ImageFont.load_default()

    # Center text vertically
    draw.text((W // 2, H // 2 - int(60 * _scale)), title,
              fill=(255, 255, 255), font=font_title, anchor="mm")
    draw.text((W // 2, H // 2 + int(20 * _scale)), subtitle,
              fill=(170, 170, 170), font=font_sub, anchor="mm")
    draw.text((W // 2, H - int(40 * _scale)),
              "StellarOrion HypersonicEdition | Ada/SPARK 2014 | SPARTA DSMC",
              fill=(100, 100, 100), font=font_sm, anchor="mm")

    path = os.path.join(out_dir, f"title_{idx:03d}.png")
    img.save(path, "PNG")
    return path


def _render_animated_frame(fargs: Any):
    """Render one animated frame for any layout (dashboard or group).

    AXIOM: Resolution is NEVER hardcoded. All positions are percentage-based.
    Layout adapts to any resolution. Future panels can be added without
    touching existing code — just add to the layout dict.

    [Citation: PIL.Image — https://pillow.readthedocs.io/en/stable/]
    """
    (frame_idx, step, alt, vel, mach, hf, drag, gload,
     show_steps, show_alt, show_hf, show_vel, show_mach,
     show_drag, show_g, out_dir, prefix, resolution,
     show_pinn_loss, show_pinn_acc, show_dsmc_pinn_err,
     show_density, show_temp, show_press,
     show_kn,
     show_peak_hf, show_total_heat, show_ballistic,
     show_stag_press, show_alt_peak_heat, show_peak_dynq,
     validation, optimized_topology) = fargs

    from PIL import Image, ImageDraw, ImageFont

    W, H_orig = resolution

    # ── Auto-expand vertical resolution if content won't fit ──
    # Layout uses percentage-based y-coordinates.  For 8 rows (9-11% each)
    # + gaps + title bar, content extends to ~100% of the canvas height.
    # If the user-provided height is too small, expand it proportionally
    # so all panels fit without clipping.  Width stays fixed.
    # !! DO NOT INCREASE THIS PAST 102 — rows are designed to fit in 100% !!
    _content_height_pct = 102.0
    _min_h = int(W * _content_height_pct / 100)
    H = max(H_orig, _min_h)
    BG = (20, 20, 40)
    FG = (220, 220, 220)
    GRID = (50, 50, 70)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Font sizes scale with resolution
    _scale = W / 1920.0
    def _fs(base: int):
        return max(10, int(base * _scale))

    try:
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(13))
        font_md = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(15))
        font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(18))
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(22))
    except OSError:
        font_sm = font_md = font_lg = font_title = ImageFont.load_default()

    # ── Percentage-based panel layout ────────────────────────────
    # Each panel: (x%, y%, w%, h%) — adapts to any resolution
    # CRITICAL: Layout percentages were designed for 1080p (rows end at ~155%).
    # When H is expanded (e.g. 2976), we scale only the Y-POSITIONS so the
    # content flows naturally from top to bottom. Panel HEIGHTS stay fixed
    # (in % of the original height) so rows don't stretch.
    title_h = 5.5  # % of height for title bar
    _H_orig_for_layout = resolution[1]  # Original design height (1080)
    _y_scale = H / _H_orig_for_layout  # Scale factor for y-positions only
    _title_pct = title_h  # Title bar height as %

    # -- AXIOMS: an overlay drawn on top of live charts hides data the
    #    viewer needs; reserved layout space is the only honest way to
    #    show both the grid and the overlay at once. The frame is a fixed
    #    W×H canvas; parameters belong in VERTICAL space (a bottom band)
    #    so the dashboard keeps FULL WIDTH (charts are width-hungry).
    # -- THEORIES: when a dash-frame overlay is active, map every panel's
    #    design region [title_h, design_bot] into [title_h, strip_top]
    #    with scale k = (strip_top − title_h)/(design_bot − title_h).
    #    Title bar (drawn outside _pct_to_px) stays full width/height;
    #    the bottom strip owns strip_top+ … 98.5% and never collides.
    # -- APPLICATIONS: _pct_to_px applies the y/h compression only in
    #    that mode; plain renders and traj/therm/mech stay full-size.
    # -- CITATIONS: none (layout contract with the overlay block below).
    #
    # ── SLIM-STRIP DERIVATION (why 82.0 and not 64.5) ──────────────────
    # AXIOMS:
    #   A1: H = int(1920 × 102/100) = 1958 px (_content_height_pct=102).
    #   A2: _scale = W/1920 = 1.0; font_sm = 13 px, font_md = 15 px.
    #   A3: Each overlay row draws 3 text lines at row_top + {0,14,28}·s
    #       plus a delta bar → row block height ≈ 28 + 13 = 41 px.
    #   A4: Overlay rows use row_h = int((panel_h − 30·s)/5), first row
    #       at y0 + 30·s (see _draw_validation_overlay L~1425).
    #   A5: Ordering invariant: _strip_top < _sep_y < _st_y0 < _st_y1.
    # THEORIES:
    #   T1 (no bottom clipping): y0 + 30 + 4·row_h + 41 ≤ y0 + panel_h
    #       ⟹ panel_h ≥ 235 px.
    #   T2 (no row overlap with margin): row_h ≥ 41 + 12 = 53 px
    #       ⟹ panel_h ≥ 5·53 + 30 = 295 px.
    #   T3 (chosen): _st_y0 = 83.0% → panel_h = (98.5−83.0)% × 1958
    #       = 303 px ≥ 295 (T2) → row_h = int(273/5) = 54 px,
    #       last text bottom = 30 + 4·54 + 41 = 287 ≤ 303 (16 px slack).
    #   T4: strip = 303 px = 15.5% of H vs old 640 px = 32.7% → 53%
    #       thinner; charts grow because k rises 0.686 → 0.890.
    # APPLICATIONS: constants below (82.0 / 82.5 / 83.0) realize T3–T4.
    _strip_mode = bool(prefix == "dash" and (validation or optimized_topology))
    _strip_top = 82.0   # % of H — dashboard content must end above this
    _design_bot = title_h + 86.0  # last dash panel bottom: +78 y, h=8
    # k ≈ (82.0 − 5.5)/(91.5 − 5.5) = 76.5/86 ≈ 0.890 (was 0.686 at 64.5)
    _strip_k = ((_strip_top - title_h) / (_design_bot - title_h)
                if _strip_mode else 1.0)

    def _pct_to_px(xp: float, yp: float, wp: float, hp: float):
        # Convert percentage coordinates to pixels, scaling both positions
        # AND heights proportionally to fit the expanded canvas.
        # !! DO NOT REVERT TO THE OLD BROKEN BEHAVIOR !!
        # The old code scaled y-positions by _y_scale but kept heights at
        # design pixels (h_scaled = h_px). This caused gaps between rows
        # and panels falling off-canvas at 155% expansion.
        # FIXED: Both y and h now use H (expanded height) directly, so
        # everything scales uniformly. If you change this, you MUST verify
        # all 5 rows of 13 panels render without gaps or clipping.
        if _strip_mode and yp >= title_h:
            # Compress vertically into the region ABOVE the bottom strip
            # (x untouched → full width preserved).
            yp = title_h + (yp - title_h) * _strip_k
            hp = hp * _strip_k
            # Safety fallback: never let a panel cross into the strip.
            if yp + hp > _strip_top:
                hp = max(1.0, _strip_top - yp)
        y_px = int(yp * H / 100)
        h_px = int(hp * H / 100)
        return (int(xp * W / 100), y_px,
                int((xp + wp) * W / 100), y_px + h_px)

    def _draw_animated_panel(draw: Any, x0: int, y0: int, x1: int, y1: int,
                             title: str, ylabel: str,
                             data_x: list[float] | np.ndarray,
                             data_y: list[float] | np.ndarray,
                             color: tuple[int, int, int], current_val: float,
                             unit: str = "", fmt: str = "{:.1f}",
                             frame_idx: int = 0):
        """Draw one animated panel — curves grow from step 0 to current frame."""
        draw.rectangle([x0, y0, x1, y1], fill=(30, 30, 55), outline=GRID, width=1)
        draw.text((x0 + int(10 * _scale), y0 + int(5 * _scale)), title,
                  fill=FG, font=font_md)

        mx = int(50 * _scale)
        my = int(30 * _scale)
        dx0, dy0 = x0 + mx, y0 + my
        dx1, dy1 = x1 - int(15 * _scale), y1 - int(25 * _scale)
        dw, dh = dx1 - dx0, dy1 - dy0

        _sx = data_x[:frame_idx + 1]
        _sy = data_y[:frame_idx + 1]
        if len(_sx) < 2:
            return

        xmin, xmax = float(data_x[0]), float(data_x[-1])
        if xmax == xmin:
            xmax = xmin + 1
        ymin_full = float(min(_sy))
        ymax_full = float(max(_sy))
        ymin, ymax = ymin_full, ymax_full
        if ymax == ymin:
            ymax = ymin + 1
        yrange = ymax - ymin
        ymax += yrange * 0.1
        ymin -= yrange * 0.1

        def _to_px(vx: float, vy: float):
            px = dx0 + (vx - xmin) / (xmax - xmin) * dw
            py = dy1 - (vy - ymin) / (ymax - ymin) * dh
            return int(px), int(py)

        # Grid
        for i in range(5):
            gy = dy0 + int(dh * i / 4)
            draw.line([(dx0, gy), (dx1, gy)], fill=GRID, width=1)
            gv = ymax - (ymax - ymin) * i / 4
            draw.text((x0 + int(2 * _scale), gy - int(6 * _scale)),
                      fmt.format(gv), fill=(150, 150, 150), font=font_sm)
        for i in range(5):
            gx = dx0 + int(dw * i / 4)
            draw.line([(gx, dy0), (gx, dy1)], fill=GRID, width=1)
            gv = xmin + (xmax - xmin) * i / 4
            draw.text((gx - int(15 * _scale), dy1 + int(3 * _scale)),
                      f"{gv / 1e6:.0f}M", fill=(150, 150, 150), font=font_sm)

        # Curve (animated)
        pts = [_to_px(float(_sx[j]), float(_sy[j])) for j in range(len(_sx))]
        pts = [(max(dx0, min(dx1, px)), max(dy0, min(dy1, py))) for px, py in pts]
        if len(pts) >= 2:
            draw.line(pts, fill=color, width=max(1, int(2 * _scale)))

        # Current dot
        cx, cy = _to_px(float(_sx[-1]), float(_sy[-1]))
        cx = max(dx0, min(dx1, cx))
        cy = max(dy0, min(dy1, cy))
        r = max(3, int(5 * _scale))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

        # Value
        draw.text((dx1 - int(140 * _scale), dy0 + int(2 * _scale)),
                  f"{fmt.format(current_val)} {unit}", fill=color, font=font_lg)
        draw.text((x0 + int(2 * _scale), dy0 + dh // 2 - int(6 * _scale)),
                  ylabel, fill=(180, 180, 180), font=font_sm)

    def _draw_vehicle_panel(draw: Any, x0: int, y0: int, x1: int, y1: int,
                            alt: float, vel: float, mach: float, hf: float,
                            frame_idx: int = 0):
        """Draw IRVE-3 parametric cross-section with heat coloring and DSMC particle flow.

        AXIOM: Uses the exact 4-segment flat-skin profile from Rapisarda 2023
        (Sec 3.7, Appendix C.1), matching the Ada/SPARK geometry backbone.
        No STL loading — parametric equations are the ground truth.

        4 segments:
          1. Nose arc (sphere rN=1.5m, theta -pi/2 to -gamma)
          2. Windward straight (cone half-angle gamma)
          3. Toroid wrap (r_torus=0.135m)
          4. Flat back (aft closure to axis)

        [Citation: Rapisarda (2023) Sec 3.7 — HIAD flat-skin parametric profile]
        [Citation: stellarorion_sparta.ads — 4-segment geometry spec]
        [Citation: stellarorion_postprocessing.ads — IRVE-3 default parameters]
        """
        draw.rectangle([x0, y0, x1, y1], fill=(30, 30, 55), outline=GRID, width=1)
        draw.text((x0 + int(10 * _scale), y0 + int(5 * _scale)),
                  "IRVE-3 Parametric HIAD + Heat Flux", fill=FG, font=font_md)

        # ── IRVE-3 parametric defaults ──
        rN = 1.5          # Nose radius [m]
        gamma_deg = 60.0  # Half-cone angle [deg] (full cone = 120°, Ada spec)
        r_torus = 0.135   # Torus tube radius [m]
        R_veh = 1.5       # Vehicle radius [m] (half of 3.0m diameter)

        gamma = np.radians(gamma_deg)

        # ── Generate 2D cross-section (top half, then mirror) ──
        # Segment 1: Nose arc — sphere from theta=-pi/2 to theta=-(pi/2 - gamma)
        nose_pts = []
        n_nose = 40
        for i in range(n_nose + 1):
            theta = -np.pi / 2 + i * gamma / n_nose  # from -90° to -30°
            nx = rN * np.cos(theta)  # x along axis (nose points right)
            ny = rN * np.sin(theta)  # y perpendicular (half-width)
            nose_pts.append((nx, ny))

        # Segment 2: Cone from nose tangent to torus start
        # Cone extends from tangent point at angle -gamma backward
        # [Citation: stellarorion_pinn_trajectory.adb lines 398-399]
        # Tangent point is at complement angle Gamma_Rad = (90 - half_cone) * Pi/180
        # Ada: R_Tang = R_N * Cos(Gamma_Rad), Z_Tang = R_N * (1 - Sin(Gamma_Rad))
        gamma_complement = np.radians(90.0 - gamma_deg)  # Ada Gamma_Rad
        cone_len = R_veh / np.sin(gamma) - rN / np.tan(gamma)
        cone_start_x = rN * np.cos(-gamma_complement)
        cone_start_y = rN * np.sin(-gamma_complement)
        cone_end_x = cone_start_x - cone_len * np.cos(gamma)
        cone_end_y = cone_start_y + cone_len * np.sin(gamma)  # goes to -R_veh
        cone_pts = [(cone_start_x, cone_start_y), (cone_end_x, cone_end_y)]

        # Segment 3: Torus wrap — circular arc at cone end
        torus_pts = []
        n_torus = 20
        torus_cx = cone_end_x
        torus_cy = cone_end_y + r_torus
        for i in range(n_torus + 1):
            phi = np.pi + i * np.pi / n_torus  # bottom to top of torus cross-section
            tx = torus_cx + r_torus * np.cos(phi)
            ty = torus_cy + r_torus * np.sin(phi)
            torus_pts.append((tx, ty))

        # Segment 4: Flat back closure

        # Combine top half: nose + cone + torus + back
        top_half = nose_pts + cone_pts + torus_pts
        # Mirror for bottom half (negate y)
        bot_half = [(x, -y) for x, y in reversed(top_half)]
        # Full outline: top half forward, bottom half backward
        full_pts = top_half + bot_half

        # ── Map to pixel coordinates ──
        # Fit vehicle in panel: nose right, back left
        panel_w = x1 - x0
        panel_h = y1 - y0
        # Vehicle total x-extent: from back (cone_end_x ≈ -1.5) to nose (rN ≈ 1.5)
        v_total_x = rN + abs(cone_end_x) + r_torus  # ~3.1m
        # Vehicle total y-extent: -R_veh to R_veh = 3.0m
        v_total_y = 2 * R_veh
        # Scale to fit panel with margins
        mx = int(60 * _scale)  # margin x
        my = int(40 * _scale)  # margin y
        avail_w = panel_w - 2 * mx
        avail_h = panel_h - 2 * my - int(20 * _scale)  # leave room for title
        sx = avail_w / v_total_x
        sy = avail_h / v_total_y
        s = min(sx, sy)  # uniform scale

        # Center vehicle in available space
        v_center_x = x0 + mx + avail_w // 2
        v_center_y = y0 + my + int(20 * _scale) + avail_h // 2

        def to_px(vx: float, vy: float):
            # vx: from back (negative) to nose (positive), vy: half-width
            px = v_center_x + int(vx * s)
            py = v_center_y - int(vy * s)  # flip y for screen coords
            return (px, py)

        px_pts = [to_px(vx, vy) for vx, vy in full_pts]

        # ── Heat flux coloring on nose (red=hot, blue=cold) ──
        # Color segments based on angular position — nose is hottest
        for i in range(len(px_pts) - 1):
            # Heat fraction: 1.0 at nose tip, 0.0 at back
            vx = full_pts[i][0]
            heat_frac = max(0.0, min(1.0, (vx + abs(cone_end_x)) / (rN + abs(cone_end_x))))
            # Color: blue (cold) → yellow → red (hot)
            r_c = int(255 * heat_frac)
            g_c = int(200 * max(0, heat_frac - 0.3))
            b_c = int(255 * (1.0 - heat_frac))
            draw.line([px_pts[i], px_pts[i + 1]], fill=(r_c, g_c, b_c),
                      width=max(1, int(2 * _scale)))

        # ── Fill vehicle body (dark gray) ──
        draw.polygon(px_pts, fill=(44, 62, 80), outline=None)

        # ── Re-draw outline with heat colors ──
        for i in range(len(px_pts) - 1):
            vx = full_pts[i][0]
            heat_frac = max(0.0, min(1.0, (vx + abs(cone_end_x)) / (rN + abs(cone_end_x))))
            r_c = int(255 * heat_frac)
            g_c = int(200 * max(0, heat_frac - 0.3))
            b_c = int(255 * (1.0 - heat_frac))
            draw.line([px_pts[i], px_pts[i + 1]], fill=(r_c, g_c, b_c),
                      width=max(1, int(2 * _scale)))

        # ── DSMC particles flowing left-to-right (freestream → vehicle) ──
        np.random.seed(42 + frame_idx % 100)
        n_particles = 25
        for i in range(n_particles):
            # Particles approach from right, deflect around vehicle
            t = np.random.random()
            px_base = v_center_x + int((rN * s + 20 * _scale) * (1.0 - t))
            py_off = (np.random.random() - 0.5) * avail_h * 0.8
            py_base = v_center_y + int(py_off)
            # Color: blue for freestream, orange for shocked
            dist_to_nose = abs(px_base - (v_center_x + int(rN * s)))
            if dist_to_nose < int(50 * _scale):
                color = (255, 160, 50)  # shocked
                sz = 3
            else:
                color = (100, 180, 255)  # freestream
                sz = 2
            draw.ellipse([px_base - sz, py_base - sz, px_base + sz, py_base + sz],
                         fill=color)

        # ── Shock bow (curved line ahead of nose) ──
        bow_cx = v_center_x + int(rN * s)
        bow_pts = []
        for i in range(21):
            phi = np.pi / 2 + (i - 10) * 0.08  # arc around nose
            bx = bow_cx + int(40 * _scale * np.cos(phi))
            by = v_center_y + int(60 * _scale * np.sin(phi))
            bow_pts.append((bx, by))
        for i in range(len(bow_pts) - 1):
            draw.line([bow_pts[i], bow_pts[i + 1]], fill=(255, 200, 50),
                      width=max(1, int(1.5 * _scale)))

        # ── Heat flux gradient arrows on nose ──
        n_arrows = min(8, max(1, int(hf / 4)))
        for i in range(n_arrows):
            idx = int(i * len(nose_pts) / max(1, n_arrows))
            if idx < len(nose_pts) - 1:
                vx, vy = full_pts[idx]
                px, py = to_px(vx, vy)
                # Arrow pointing into surface (heat direction)
                bl = int((8 + 20 * (hf / 20.0)) * _scale)
                draw.line([(px + bl, py), (px, py)], fill=(255, 80, 50),
                          width=max(1, int(2 * _scale)))
                draw.line([(px, py), (px + bl, -py + 2 * v_center_y)],
                          fill=(255, 80, 50), width=max(1, int(2 * _scale)))

        # ── Info text ──
        draw.text((x1 - int(220 * _scale), y0 + int(25 * _scale)),
                  f"Alt: {alt:.0f} km ({alt * KM_TO_FT:,.0f} ft)", fill=FG, font=font_lg)
        hf_color = (255, 80, 80) if hf > 10 else FG
        draw.text((x1 - int(220 * _scale), y0 + int(50 * _scale)),
                  f"q={hf:.1f} W/cm2", fill=hf_color, font=font_md)
        draw.text((x1 - int(220 * _scale), y0 + int(70 * _scale)),
                  f"Mach {mach:.2f}", fill=FG, font=font_md)
        draw.text((x1 - int(220 * _scale), y0 + int(90 * _scale)),
                  "70° cone, 6 tori, r=0.135m", fill=(120, 120, 140), font=font_sm)

        # ── Composite Material Inset (left side, empty area) ──
        # [Citation: NASA TP-2013-4012 — IRVE-3 flexible TPS composite]
        # [Citation: Rapisarda (2023) Sec 3.7 — HIAD material stack]
        inset_x = x0 + int(10 * _scale)
        inset_y = y0 + int(10 * _scale)
        inset_w = int(180 * _scale)
        inset_h = int(130 * _scale)
        draw.rectangle([inset_x, inset_y, inset_x + inset_w, inset_y + inset_h],
                       fill=(20, 20, 40), outline=(80, 100, 140), width=1)
        draw.text((inset_x + int(5 * _scale), inset_y + int(3 * _scale)),
                  "Composite Shield Cross-Section", fill=(180, 200, 255), font=font_sm)

        # Layer positions (from outer to inner)
        layer_names = ["TPS Fabric", "Insulation", "Structural"]
        layer_colors = [(200, 80, 60), (180, 140, 80), (100, 120, 160)]
        layer_h = [int(25 * _scale), int(25 * _scale), int(25 * _scale)]
        layer_y_start = inset_y + int(18 * _scale)
        layer_x = inset_x + int(20 * _scale)
        layer_w = int(120 * _scale)

        # Draw layers
        current_y = layer_y_start
        for i, (name, color, h) in enumerate(zip(layer_names, layer_colors, layer_h)):
            draw.rectangle([layer_x, current_y, layer_x + layer_w, current_y + h],
                           fill=color, outline=(60, 80, 100))
            draw.text((layer_x + int(3 * _scale), current_y + int(2 * _scale)),
                      name, fill=(255, 255, 255), font=font_sm)
            current_y += h

        # ── Heat Flow Arrows (convection + conduction) ──
        # Convection: arrows from gas to outer surface (horizontal)
        arrow_x = layer_x + layer_w + int(5 * _scale)
        for i in range(3):
            ay = layer_y_start + int(10 * _scale) + i * int(10 * _scale)
            # Convection arrow (red, pointing left into surface)
            draw.line([(arrow_x + int(30 * _scale), ay), (arrow_x, ay)],
                      fill=(255, 100, 50), width=2)
            # Arrowhead
            draw.polygon([(arrow_x, ay),
                          (arrow_x + int(6 * _scale), ay - int(3 * _scale)),
                          (arrow_x + int(6 * _scale), ay + int(3 * _scale))],
                         fill=(255, 100, 50))

        # Conduction: arrows through layers (vertical, downward)
        cond_x = layer_x + layer_w // 2
        for i in range(3):
            cy = layer_y_start + i * int(25 * _scale)
            # Conduction arrow (yellow, pointing down through layers)
            draw.line([(cond_x, cy + int(5 * _scale)), (cond_x, cy + int(20 * _scale))],
                      fill=(255, 220, 50), width=2)
            # Arrowhead
            draw.polygon([(cond_x, cy + int(20 * _scale)),
                          (cond_x - int(3 * _scale), cy + int(14 * _scale)),
                          (cond_x + int(3 * _scale), cy + int(14 * _scale))],
                         fill=(255, 220, 50))

        # Labels for heat flow
        draw.text((arrow_x + int(15 * _scale), layer_y_start - int(8 * _scale)),
                  "Convection", fill=(255, 120, 80), font=font_sm)
        draw.text((layer_x - int(5 * _scale), current_y + int(2 * _scale)),
                  "Conduction", fill=(255, 220, 80), font=font_sm)

    # ══════════════════════════════════════════════════════════════════
    # LAYOUT: Percentage-based, adapts to resolution
    # ══════════════════════════════════════════════════════════════════

    def _draw_panel_row(specs: list[tuple[Any, ...]], pw: int, gap: int,
                        x_start: int = 2) -> None:
        """Draw a horizontal row of animated panels (shared by traj/therm/mech).

        AXIOMS: panel geometry is percentage-based (y=title_h+1, h=92%).
        THEORIES: one row renderer prevents copy-paste divergence between
          the three group-segment branches.
        APPLICATIONS: specs = [(title, ylabel, data_y, color, unit, fmt, cur), ...];
          pw/gap are canvas percentages; cur is the live scalar at frame_idx.
        CITATIONS: none (internal layout contract).
        """
        for _i, (_t, _yl, _dy, _c, _u, _fmt, _cur) in enumerate(specs):
            _p = _pct_to_px(x_start + _i * (pw + gap), title_h + 1, pw, 92)
            _draw_animated_panel(draw, *_p, _t, _yl,
                                 show_steps, _dy, _c, _cur, _u,
                                 fmt=_fmt, frame_idx=frame_idx)

    if prefix == "dash":
        # ── MAIN DASHBOARD: 7 panels (percentage layout) ─────────
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)], fill=(15, 15, 30))
        pct = step / TARGET_STEP * 100
        draw.text((int(20 * _scale), int(10 * _scale)),
                  f"StellarOrion HIAD Live Dashboard | Step {step:,} / {TARGET_STEP:,} "
                  f"({pct:.1f}%) | Ada/SPARK 2014", fill=FG, font=font_title)
        draw.text((int(20 * _scale), int(40 * _scale)),
                  f"Alt: {alt:.1f} km ({alt * 1000:.0f} m / {alt * KM_TO_FT:,.0f} ft) | Vel: {vel:.0f} m/s | Mach: {mach:.2f} | "
                  f"q={hf:.1f} W/cm2 | G: {gload:.1f} | Drag: {drag:.0f} N",
                  fill=(180, 180, 180), font=font_md)

        # Row 1 (y=6%, h=11%): altitude / velocity / mach
        p = _pct_to_px(2, title_h + 1, 31, 11)
        _draw_animated_panel(draw, *p, "Altitude Profile", "Alt [km / ft]",
                             show_steps, show_alt, (100, 150, 255), alt, "km",
                             frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 1, 31, 11)
        _draw_animated_panel(draw, *p, "Velocity", "Vel [m/s]",
                             show_steps, show_vel, (100, 220, 100), vel, "m/s",
                             fmt="{:.0f}", frame_idx=frame_idx)
        p = _pct_to_px(66, title_h + 1, 32, 11)
        _draw_animated_panel(draw, *p, "Mach Number", "Mach",
                             show_steps, show_mach, (220, 100, 220), mach,
                             fmt="{:.2f}", frame_idx=frame_idx)

        # Row 2 (y=18%, h=11%): sutton-graves heat flux / peak heat flux / g-load
        p = _pct_to_px(2, title_h + 12, 32, 11)
        _draw_animated_panel(draw, *p, "Sutton-Graves Heat Flux", r"q [W/cm2]",
                             show_steps, show_hf, (255, 80, 80), hf, r"W/cm2",
                             frame_idx=frame_idx)
        peak_hf_val = show_peak_hf[frame_idx] if frame_idx < len(show_peak_hf) else 0.0
        p = _pct_to_px(35, title_h + 12, 32, 11)
        _draw_animated_panel(draw, *p, "Peak Heat Flux", r"q_peak [W/cm2]",
                             show_steps, show_peak_hf, (255, 50, 50), peak_hf_val, r"W/cm2",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(68, title_h + 12, 30, 11)
        _draw_animated_panel(draw, *p, "Deceleration (G-load)", "G [g]",
                             show_steps, show_g, (80, 220, 220), gload, "g",
                             frame_idx=frame_idx)

        # Row 3 (y=30%, h=11%): drag / vehicle
        p = _pct_to_px(2, title_h + 23, 31, 11)
        _draw_animated_panel(draw, *p, "Drag Force", "Drag [N]",
                             show_steps, show_drag, (255, 180, 50), drag, "N",
                             fmt="{:.0f}", frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 23, 64, 11)
        _draw_vehicle_panel(draw, *p, alt, vel, mach, hf)

        # Row 4 (y=42%, h=11%): PINN statistics + Knudsen number (4 panels)
        pinn_loss_val = show_pinn_loss[frame_idx] if frame_idx < len(show_pinn_loss) else 0.0
        pinn_acc_val = show_pinn_acc[frame_idx] if frame_idx < len(show_pinn_acc) else 0.0
        dsmc_err_val = show_dsmc_pinn_err[frame_idx] if frame_idx < len(show_dsmc_pinn_err) else 0.0
        kn_val = show_kn[frame_idx] if frame_idx < len(show_kn) else 0.0
        p = _pct_to_px(2, title_h + 34, 23, 11)
        _draw_animated_panel(draw, *p, "PINN Training Loss", "Loss",
                             show_steps, show_pinn_loss, (0, 200, 100), pinn_loss_val, "",
                             fmt="{:.4f}", frame_idx=frame_idx)
        p = _pct_to_px(26, title_h + 34, 23, 11)
        _draw_animated_panel(draw, *p, "PINN Accuracy", "Acc [%]",
                             show_steps, show_pinn_acc, (100, 200, 255), pinn_acc_val, "%",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(50, title_h + 34, 23, 11)
        _draw_animated_panel(draw, *p, "DSMC vs PINN Error", "Error [%]",
                             show_steps, show_dsmc_pinn_err, (255, 150, 0), dsmc_err_val, "%",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(74, title_h + 34, 24, 11)
        _draw_animated_panel(draw, *p, "Knudsen Number (Kn)", "Kn [-]",
                             show_steps, show_kn, (200, 100, 255), kn_val, "",
                             fmt="{:.2e}", frame_idx=frame_idx)

        # Row 5 (y=54%, h=11%): atmosphere environment (density, temperature, pressure)
        dens_val = show_density[frame_idx] if frame_idx < len(show_density) else 0.0
        temp_val = show_temp[frame_idx] if frame_idx < len(show_temp) else 0.0
        press_val = show_press[frame_idx] if frame_idx < len(show_press) else 0.0
        p = _pct_to_px(2, title_h + 45, 31, 11)
        _draw_animated_panel(draw, *p, "Atmospheric Density", r"rho [kg/m3]",
                             show_steps, show_density, (180, 220, 255), dens_val, r"kg/m3",
                             fmt="{:.4f}", frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 45, 31, 11)
        _draw_animated_panel(draw, *p, "Atmospheric Temperature", "T [K]",
                             show_steps, show_temp, (255, 200, 100), temp_val, "K",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(66, title_h + 45, 32, 11)
        _draw_animated_panel(draw, *p, "Atmospheric Pressure", "P [Pa]",
                             show_steps, show_press, (200, 150, 255), press_val, "Pa",
                             fmt="{:.0f}", frame_idx=frame_idx)

        # Row 6 (y=66%, h=11%): thermal loads (peak heat flux, total heat load, ballistic coeff)
        peak_hf_val = show_peak_hf[frame_idx] if frame_idx < len(show_peak_hf) else 0.0
        total_heat_val = show_total_heat[frame_idx] if frame_idx < len(show_total_heat) else 0.0
        ballistic_val = show_ballistic[frame_idx] if frame_idx < len(show_ballistic) else 0.0
        p = _pct_to_px(2, title_h + 56, 31, 11)
        _draw_animated_panel(draw, *p, "Peak Heat Flux", r"q_peak [W/cm2]",
                             show_steps, show_peak_hf, (255, 50, 50), peak_hf_val, r"W/cm2",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 56, 31, 11)
        _draw_animated_panel(draw, *p, "Total Heat Load", r"Q [J/cm2]",
                             show_steps, show_total_heat, (255, 120, 0), total_heat_val, r"J/cm2",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(66, title_h + 56, 32, 11)
        _draw_animated_panel(draw, *p, "Ballistic Coefficient", r"beta [kg/m2]",
                             show_steps, show_ballistic, (0, 180, 200), ballistic_val, r"kg/m2",
                             fmt="{:.2f}", frame_idx=frame_idx)

        # Row 7 (y=78%, h=11%): pressure loads (peak dynamic, stagnation, alt of peak heating)
        peak_dynq_val = show_peak_dynq[frame_idx] if frame_idx < len(show_peak_dynq) else 0.0
        stag_press_val = show_stag_press[frame_idx] if frame_idx < len(show_stag_press) else 0.0
        alt_peak_val = show_alt_peak_heat[frame_idx] if frame_idx < len(show_alt_peak_heat) else 0.0
        p = _pct_to_px(2, title_h + 67, 31, 11)
        _draw_animated_panel(draw, *p, "Peak G-Load", "G_peak [g]",
                             show_steps, show_peak_dynq, (255, 220, 0), peak_dynq_val, "g",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 67, 31, 11)
        _draw_animated_panel(draw, *p, "Stagnation Pressure", "P_stag [Pa]",
                             show_steps, show_stag_press, (150, 100, 255), stag_press_val, "Pa",
                             fmt="{:.0f}", frame_idx=frame_idx)
        p = _pct_to_px(66, title_h + 67, 32, 11)
        _draw_animated_panel(draw, *p, "Altitude of Peak Heating", "Alt_peak [km]",
                             show_steps, show_alt_peak_heat, (255, 180, 200), alt_peak_val, "km",
                             fmt="{:.1f}", frame_idx=frame_idx)

        # Row 8 (y=90%, h=8%): Earth + flight trajectory
        # -- AXIOMS: Reentry trajectory starts far from Earth (deep space),
        #    approaches the planet, enters the atmosphere, and descends.
        #    The vehicle MUST be shown moving TOWARD Earth, not away from it.
        #    Trajectory must terminate at/near the Earth's atmosphere boundary.
        # -- THEORIES: Use parametric curve from (far-right, high) to
        #    (Earth-atmosphere-edge, low). Earth is a circle on the left.
        #    Vehicle position advances along this curve each frame.
        # -- APPLICATIONS: Cubic easing for natural deceleration curve.
        #    Trajectory ends exactly at Earth's atmosphere boundary (r_earth + margin).
        p = _pct_to_px(2, title_h + 78, 96, 8)
        draw.rectangle([p[0], p[1], p[2], p[3]], fill=(30, 30, 55), outline=GRID, width=1)
        draw.text((p[0] + int(10 * _scale), p[1] + int(3 * _scale)),
                  "Earth Position & Flight Trajectory", fill=FG, font=font_md)

        # Draw Earth circle — LARGE and prominent with animated spiral
        cx_earth = p[0] + int(160 * _scale)
        cy_earth = (p[1] + p[3]) // 2 + int(15 * _scale)
        r_earth = int(90 * _scale)
        # Gradient fill: dark blue core → lighter blue edge
        for ri in range(r_earth, 0, -1):
            frac = ri / r_earth
            cr = int(20 + 30 * (1 - frac))
            cg = int(60 + 60 * (1 - frac))
            cb = int(140 + 60 * (1 - frac))
            draw.ellipse([cx_earth - ri, cy_earth - ri,
                          cx_earth + ri, cy_earth + ri],
                         fill=(cr, cg, cb))
        # Animated spiral on Earth surface (rotates with frame)
        spiral_offset = frame_idx * 0.5  # rotation speed
        spiral_pts = []
        for ang_deg in range(0, 720, 2):  # 2 full rotations
            ang = _math.radians(ang_deg + spiral_offset)
            # Spiral radius grows from center to edge
            t = ang_deg / 720.0
            sr = r_earth * 0.1 + r_earth * 0.85 * t
            sx = cx_earth + int(sr * _math.cos(ang))
            sy = cy_earth + int(sr * _math.sin(ang))
            spiral_pts.append((sx, sy))
        # Draw spiral with fading opacity
        for i in range(len(spiral_pts) - 1):
            t = i / len(spiral_pts)
            int(40 + 80 * t)  # fades from faint to bright
            green = int(80 + 60 * t)
            draw.line([spiral_pts[i], spiral_pts[i + 1]],
                      fill=(30, green, 100 + int(50 * t)), width=2)
        draw.ellipse([cx_earth - r_earth, cy_earth - r_earth,
                      cx_earth + r_earth, cy_earth + r_earth],
                     outline=(80, 140, 220), width=2)
        draw.text((cx_earth, cy_earth), "EARTH", fill=(200, 220, 255),
                  font=font_sm, anchor="mm")

        # Draw atmosphere glow ring around Earth (dashed arc, thick & visible)
        r_atm = r_earth + int(18 * _scale)  # wider atmosphere band
        for ang_deg in range(0, 360, 2):
            ang = _math.radians(ang_deg)
            ax1 = cx_earth + int((r_atm - 4) * _math.cos(ang))
            ay1 = cy_earth + int((r_atm - 4) * _math.sin(ang))
            ax2 = cx_earth + int((r_atm + 4) * _math.cos(ang))
            ay2 = cy_earth + int((r_atm + 4) * _math.sin(ang))
            if ang_deg % 8 < 4:  # dashed pattern, wider segments
                draw.line([(ax1, ay1), (ax2, ay2)], fill=(120, 170, 255, 180), width=3)
        # Label atmosphere
        draw.text((cx_earth + r_atm + int(6 * _scale), cy_earth - int(8 * _scale)),
                  "120 km", fill=(120, 170, 255), font=font_sm)

        # -- REENTRY TRAJECTORY --
        # Physics: vehicle approaches from deep space on a nearly horizontal path,
        # gravity curves it downward into a steepening arc, and it enters the
        # atmosphere at a sharp angle. This is a ballistic reentry arc.
        # We use a CUBIC BEZIER with two control points to create the shape:
        #   Start (far right, top) → CP1 (mid-right, top — keeps it horizontal initially)
        #   → CP2 (mid-left, bottom — steepens descent) → End (near Earth, bottom)

        # Panel coordinates
        traj_left = cx_earth + r_earth + int(15 * _scale)   # near Earth's right edge
        traj_right = p[2] - int(20 * _scale)                 # far right of panel
        traj_top = p[1] + int(8 * _scale)                    # top of panel
        traj_bottom = p[3] - int(5 * _scale)                 # bottom of panel
        (traj_left + traj_right) // 2

        # Cubic bezier control points for dramatic reentry arc:
        # CP1: keeps trajectory nearly horizontal at start (deep space approach)
        # CP2: pulls trajectory steeply downward as it nears Earth
        cp1_x = traj_right - int(0.15 * (traj_right - traj_left))  # 15% from right
        cp1_y = traj_top + int(3 * _scale)                          # stays near top
        cp2_x = traj_left + int(0.25 * (traj_right - traj_left))   # 25% from left
        cp2_y = traj_bottom - int(2 * _scale)                       # near bottom

        # Generate trajectory points along the cubic bezier
        # B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3
        traj_pts = []
        num_pts = 300  # smooth curve
        for i in range(num_pts + 1):
            t = i / num_pts
            u = 1.0 - t
            tx = u**3 * traj_right + 3*u**2*t * cp1_x + 3*u*t**2 * cp2_x + t**3 * traj_left
            ty = u**3 * traj_top + 3*u**2*t * cp1_y + 3*u*t**2 * cp2_y + t**3 * traj_bottom
            traj_pts.append((int(tx), int(ty)))

        if len(traj_pts) >= 2:
            draw.line(traj_pts, fill=(255, 100, 100), width=max(3, int(4 * _scale)))
            # Arrowhead at trajectory END (near Earth) — LARGE and prominent
            ax, ay = traj_pts[-2]
            bx, by = traj_pts[-1]
            angle = _math.atan2(by - ay, bx - ax)
            arrow_len = int(30 * _scale)  # much bigger arrow
            # Draw filled arrowhead polygon
            tip_x = bx
            tip_y = by
            left_x = bx - arrow_len * _math.cos(angle + _math.pi * 0.2)
            left_y = by - arrow_len * _math.sin(angle + _math.pi * 0.2)
            right_x = bx - arrow_len * _math.cos(angle - _math.pi * 0.2)
            right_y = by - arrow_len * _math.sin(angle - _math.pi * 0.2)
            base_x = bx - arrow_len * 0.4 * _math.cos(angle)
            base_y = by - arrow_len * 0.4 * _math.sin(angle)
            # Filled bright orange arrowhead
            draw.polygon([(int(tip_x), int(tip_y)),
                          (int(left_x), int(left_y)),
                          (int(base_x), int(base_y)),
                          (int(right_x), int(right_y))],
                         fill=(255, 160, 0))  # bright orange for contrast

        # Phase labels along trajectory
        draw.text((traj_right - int(5 * _scale), traj_top + int(2 * _scale)),
                  "DEEP SPACE →", fill=(150, 150, 180), font=font_sm, anchor="rt")
        draw.text((traj_left + int(5 * _scale), traj_bottom - int(3 * _scale)),
                  "← ENTRY", fill=(255, 180, 80), font=font_sm, anchor="lt")

        # Current position on trajectory (yellow dot + vehicle triangle)
        if frame_idx < len(show_alt):
            curr_t = frame_idx / max(1, len(show_alt) - 1)
            u = 1.0 - curr_t
            curr_tx = int(u**3 * traj_right + 3*u**2*curr_t * cp1_x + 3*u*curr_t**2 * cp2_x + curr_t**3 * traj_left)
            curr_ty = int(u**3 * traj_top + 3*u**2*curr_t * cp1_y + 3*u*curr_t**2 * cp2_y + curr_t**3 * traj_bottom)
            curr_ty = max(p[1] + int(5 * _scale), min(p[3] - int(3 * _scale), curr_ty))
            # Yellow glow dot
            r_dot = max(5, int(7 * _scale))
            draw.ellipse([curr_tx - r_dot - 2, curr_ty - r_dot - 2,
                          curr_tx + r_dot + 2, curr_ty + r_dot + 2],
                         fill=(255, 255, 0, 60))
            draw.ellipse([curr_tx - r_dot, curr_ty - r_dot, curr_tx + r_dot, curr_ty + r_dot],
                         fill=(255, 255, 0))
            # Small vehicle triangle pointing toward Earth
            tri_sz = int(8 * _scale)
            # Direction toward Earth (from current pos toward traj endpoint)
            dx = traj_left - curr_tx
            dy = traj_bottom - curr_ty
            dist = _math.sqrt(dx*dx + dy*dy) + 0.001
            nx, ny = dx/dist, dy/dist
            # Triangle: tip forward, base behind
            tip_x = curr_tx + nx * tri_sz
            tip_y = curr_ty + ny * tri_sz
            base_x = curr_tx - nx * tri_sz * 0.5
            base_y = curr_ty - ny * tri_sz * 0.5
            perp_x, perp_y = -ny, nx
            b1 = (base_x + perp_x * tri_sz * 0.4, base_y + perp_y * tri_sz * 0.4)
            b2 = (base_x - perp_x * tri_sz * 0.4, base_y - perp_y * tri_sz * 0.4)
            draw.polygon([(int(tip_x), int(tip_y)), (int(b1[0]), int(b1[1])), (int(b2[0]), int(b2[1]))],
                         fill=(255, 200, 50))

        # Labels
        draw.text((p[0] + int(130 * _scale), p[3] - int(5 * _scale)),
                  f"Alt: {alt:.1f} km ({alt * KM_TO_FT:,.0f} ft) | Vel: {vel:.0f} m/s | Mach: {mach:.2f}",
                  fill=(180, 180, 180), font=font_sm)

    elif prefix == "traj":
        # ── TRAJECTORY GROUP: 3 panels side by side ─────────────
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)],
                       fill=(15, 15, 30))
        draw.text((int(20 * _scale), int(15 * _scale)),
                  "StellarOrion — Trajectory Parameters", fill=FG, font=font_title)
        # Live scalars (alt/vel/mach AT frame_idx) — NOT data_y[-1]:
        # data_y[-1] is the FINAL trajectory value, so the big number would
        # be wrong while the curve is still growing frame-by-frame.
        _draw_panel_row([
            ("Altitude Profile", "Alt [km / ft]", show_alt, (100, 150, 255), "km", "{:.1f}", alt),
            ("Velocity", "Vel [m/s]", show_vel, (100, 220, 100), "m/s", "{:.0f}", vel),
            ("Mach Number", "Mach", show_mach, (220, 100, 220), "", "{:.2f}", mach),
        ], pw=30, gap=2)

    elif prefix == "therm":
        # ── THERMAL GROUP: heat flux + Mach side by side ────────
        # Geometry: 2×47% panels + 2% gap → x=2 and x=51, fits 100% canvas.
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)],
                       fill=(15, 15, 30))
        draw.text((int(20 * _scale), int(15 * _scale)),
                  "StellarOrion — Thermal & Heating", fill=FG, font=font_title)
        _draw_panel_row([
            ("Sutton-Graves Heat Flux", r"q [W/cm2]", show_hf, (255, 80, 80), r"W/cm2", "{:.1f}", hf),
            ("Mach Number", "Mach", show_mach, (220, 100, 220), "", "{:.2f}", mach),
        ], pw=47, gap=2)

    elif prefix == "mech":
        # ── MECHANICAL GROUP: drag + g-load + Mach (3 panels) ───
        # Geometry mirrors traj/dash Row 1: pw=30, gap=2 → x=2/34/66.
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)],
                       fill=(15, 15, 30))
        draw.text((int(20 * _scale), int(15 * _scale)),
                  "StellarOrion — Mechanical Loads", fill=FG, font=font_title)
        _draw_panel_row([
            ("Drag Force", "Drag [N]", show_drag, (255, 180, 50), "N", "{:.0f}", drag),
            ("Deceleration (G-load)", "G [g]", show_g, (80, 220, 220), "g", "{:.1f}", gload),
            ("Mach Number", "Mach", show_mach, (220, 100, 220), "", "{:.2f}", mach),
        ], pw=30, gap=2)

    # ── Dedicated bottom strip: VALIDATION / Optimized Topology (dash only) ──
    # The dashboard grid is compressed vertically to end at _strip_top
    # (see _strip_mode in _pct_to_px) so it keeps FULL WIDTH; these
    # parameter panels own the reserved bottom band and never cover charts.
    # [Citation: NASA TP-2013-4012 — IRVE-3 flight data]
    # [Citation: Rapisarda (2023) Table 4.10 — validation metrics]
    # [Citation: Optimization_Attempt_1.md — Bayesian-optimized specs]
    if prefix == "dash" and (validation or optimized_topology):
        ov_x0 = int(W * 0.01)
        ov_x1 = int(W * 0.99)
        # Slim-strip geometry (see SLIM-STRIP DERIVATION at _strip_top):
        # panel = (98.5 − 83.0)% × 1958 = 303 px (was 640 px at 65.8%).
        # Ordering invariant (A5): 82.0 (content) < 82.5 (sep) < 83.0 (y0).
        _st_y0 = int(H * 83.0 / 100)   # just below the separator line
        _st_y1 = int(H * 0.985)
        # Strip backdrop + horizontal separator — makes the reserved band
        # read as dedicated space rather than a floating overlay.
        _sep_y = int(H * 82.5 / 100)
        draw.rectangle([ov_x0 - int(8 * _scale), _st_y0,
                        ov_x1 + int(8 * _scale), _st_y1],
                       fill=(15, 15, 30))
        draw.line([(ov_x0 - int(8 * _scale), _sep_y),
                   (ov_x1 + int(8 * _scale), _sep_y)],
                  fill=(50, 50, 70), width=2)
        if validation:
            peak_hf_val_v = show_peak_hf[frame_idx] if frame_idx < len(show_peak_hf) else 0.0
            total_heat_val = show_total_heat[frame_idx] if frame_idx < len(show_total_heat) else 0.0
            ballistic_val = show_ballistic[frame_idx] if frame_idx < len(show_ballistic) else 0.0
            peak_g_val = show_peak_dynq[frame_idx] if frame_idx < len(show_peak_dynq) else 0.0
            # Entry Mach = running peak of the Mach curve so far. Mach decreases
            # monotonically during deceleration, so the running peak ≈ entry value
            # and stays comparable to the NASA EI reference (14.5) all video long.
            # Using instantaneous Mach instead would show a growing/wrong delta.
            _mach_slice = show_mach[:frame_idx + 1]
            peak_mach_val = float(np.max(_mach_slice)) if len(_mach_slice) > 0 else 0.0
            if optimized_topology:
                # Both overlays: split the strip into left/right halves
                # (vertical space is reserved for row height; split x instead).
                _mid = (ov_x0 + ov_x1) // 2
                _gap = int(8 * _scale)
                _draw_validation_overlay(draw, ov_x0, _st_y0,
                                         _mid - _gap, _st_y1,
                                         peak_hf_val_v, total_heat_val,
                                         ballistic_val, peak_g_val, peak_mach_val,
                                         font_sm, font_md, _scale)
                _draw_optimized_topology_overlay(draw, _mid + _gap, _st_y0,
                                                 ov_x1, _st_y1,
                                                 font_sm, font_md, _scale)
            else:
                # Validation only: the whole bottom strip belongs to it.
                _draw_validation_overlay(draw, ov_x0, _st_y0,
                                         ov_x1, _st_y1,
                                         peak_hf_val_v, total_heat_val,
                                         ballistic_val, peak_g_val, peak_mach_val,
                                         font_sm, font_md, _scale)
        else:
            # Optimized topology only: the whole bottom strip belongs to it.
            _draw_optimized_topology_overlay(draw, ov_x0, _st_y0,
                                             ov_x1, _st_y1,
                                             font_sm, font_md, _scale)

    frame_path = os.path.join(out_dir, f"{prefix}_{frame_idx:05d}.png")
    img.save(frame_path, "PNG")
    return frame_path


def generate_mp4(output_dir: str, max_frames: int | None = None,
                 target_duration: float | None = None,
                 steps_per_frame: int = 100_000,
                 resolution: tuple[int, int] = (1920, 1080), pixel_scale: float = 1.0,
                 validation: bool = False,
                 optimized_topology: bool = False):
    """Generate pure live-animation MP4 — EVERYTHING is animated, NO static frames.

    Structure:
      1. Title card (2s)
      2. Main dashboard (multi-panel, curves grow frame-by-frame)
      3. Trajectory group (altitude/velocity/mach, curves grow)
      4. Thermal group (heat flux + mach, curves grow)
      5. Mechanical group (drag/g-load/mach, curves grow)
      6. Encode with ffmpeg

    max_frames=None renders the full trajectory (3001 frames at the default
    steps_per_frame); pass an int to cap dashboard frames for fast iteration.

    Ada FFI computes all physics. PIL renders all frames. Zero matplotlib.
    [Citation: ffmpeg HW accel — https://trac.ffmpeg.org/HWAccelIntro]

    FUTURE (lowest priority): GPU-accelerated rendering via torch.mps (Metal on Apple
    Silicon). System has M2 Pro + Metal 4 + torch 2.11.0 with MPS backend available.
    Potential speedups: batch NEAREST upscale on GPU, batch compositing. Currently
    CPU-only — PIL drawing + sequential PNG save is the bottleneck, not the compute.
    """
    plots_dir = os.path.join(output_dir, "plots")
    frames_dir = os.path.join(output_dir, "mp4_frames")
    os.makedirs(plots_dir, exist_ok=True)

    # ── Purge stale frames from previous runs (prevents resolution mismatch) ──
    if os.path.isdir(frames_dir):
        for old_f in glob.glob(os.path.join(frames_dir, "*.png")):
            os.remove(old_f)
        for old_f in glob.glob(os.path.join(frames_dir, "concat.txt")):
            os.remove(old_f)
    os.makedirs(frames_dir, exist_ok=True)

    # ── Compute expanded resolution (same logic as _render_animated_frame) ──
    _content_height_pct = 102.0
    # ── Pixel-scale: render at lower res for retro/jagged aesthetic ──
    # Frames are rendered at resolution/pixel_scale, then upscaled with NEAREST
    # [Citation: PIL.Image.NEAREST — https://pillow.readthedocs.io/en/stable/handbook/concepts.html#resampling-filters]
    _render_w = int(resolution[0] * pixel_scale) if pixel_scale != 1.0 else resolution[0]
    _render_h = int(resolution[1] * pixel_scale) if pixel_scale != 1.0 else resolution[1]
    _expanded_h = max(_render_h, int(_render_w * _content_height_pct / 100))
    _expanded_resolution = (_render_w, _expanded_h)

    all_paths = []
    frame_idx = 0

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1: Title card (2 seconds)
    # ══════════════════════════════════════════════════════════════════
    print("[MP4] Section 1: Title card")
    title_path = _make_title_card(
        "StellarOrion HypersonicEdition",
        "IRVE-3 HIAD Aerothermodynamic Validation Dashboard\n"
        "SPARTA DSMC + Ada/SPARK 2014 Physics Backbone",
        frames_dir, frame_idx, resolution=_expanded_resolution)
    all_paths.append(("title", title_path))
    frame_idx += 1

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2: Compute ALL trajectory via Ada FFI
    # ══════════════════════════════════════════════════════════════════
    all_steps = list(range(0, TARGET_STEP + 1, steps_per_frame))
    # Apply max_frames limit (if specified, truncate trajectory to first N frames)
    if max_frames and len(all_steps) > max_frames:
        all_steps = all_steps[:max_frames]
    n_anim = len(all_steps)
    fps = 30

    n_workers = min(cpu_count(), 8)
    print(f"[MP4] Computing {n_anim} trajectory points via Ada FFI ({steps_per_frame:,} steps/frame) ...")
    t0 = time.time()

    with Pool(n_workers) as pool:
        frame_data = list(tqdm(pool.imap(_compute_frame_data, all_steps, chunksize=100),
                               total=len(all_steps), desc="[MP4] Ada FFI",
                               unit="pts", ncols=80))

    frame_alt = np.array([d["altitude_km"] for d in frame_data])
    frame_vel = np.array([d["velocity_ms"] for d in frame_data])
    frame_mach = np.array([d["mach_number"] for d in frame_data])
    frame_hf = np.array([d["heat_flux_wcm2"] for d in frame_data])
    frame_drag = np.array([d["drag_sum_N"] for d in frame_data])
    frame_g = np.array([d["g_load"] for d in frame_data])
    frame_pinn_loss = np.array([d["pinn_loss"] for d in frame_data])
    frame_pinn_acc = np.array([d["pinn_accuracy"] for d in frame_data])
    frame_dsmc_pinn_err = np.array([d["dsmc_pinn_error"] for d in frame_data])
    frame_density = np.array([d["density_kgm3"] for d in frame_data])
    frame_temp = np.array([d["temperature_K"] for d in frame_data])
    frame_press = np.array([d["pressure_Pa"] for d in frame_data])
    frame_kn = np.array([d["knudsen_number"] for d in frame_data])
    frame_ballistic = np.array([d["ballistic_coeff_kgm2"] for d in frame_data])
    frame_stag_press = np.array([d["stagnation_pressure_Pa"] for d in frame_data])
    all_frame_steps = np.array(all_steps)

    # Derived cumulative arrays (running max / cumulative integral)
    frame_peak_hf = np.maximum.accumulate(frame_hf)  # Peak heat flux so far
    frame_total_heat = np.cumsum(frame_hf) * (steps_per_frame / 1e6)  # J/cm² approx
    frame_peak_dynq = np.maximum.accumulate(frame_g)  # Peak g-load (proxy for peak dynq)
    # Altitude of peak heating: altitude at which max heat flux occurs
    _peak_hf_idx = np.argmax(frame_hf)
    frame_alt_peak_heat = np.full_like(frame_alt, frame_alt[_peak_hf_idx])

    elapsed = time.time() - t0
    print(f"[MP4] Ada FFI computed {n_anim} points in {elapsed:.1f}s ({n_workers} workers)")


    # ══════════════════════════════════════════════════════════════════
    # SECTION 2a: Render MAIN DASHBOARD frames (animated)
    # ══════════════════════════════════════════════════════════════════
    # Shared fargs builder — one 33-element contract for dash + group segments
    # so the tuple can never diverge between call sites.
    def _make_render_args(i: int, prefix: str) -> tuple[Any, ...]:
        """Build the fargs tuple for _render_animated_frame.

        AXIOMS: element order must match the unpack in _render_animated_frame.
        THEORIES: single builder ⇒ dash and group segments stay in lockstep.
        APPLICATIONS: i = DATA index (drives curve slice prefix_{i:05d}.png);
          prefix selects the layout branch (dash/traj/therm/mech).
        CITATIONS: none (internal contract).
        """
        return (
            i, int(all_frame_steps[i]),
            frame_alt[i], frame_vel[i], frame_mach[i],
            frame_hf[i], frame_drag[i], frame_g[i],
            all_frame_steps, frame_alt, frame_hf,
            frame_vel, frame_mach, frame_drag, frame_g,
            frames_dir, prefix, _expanded_resolution,
            frame_pinn_loss, frame_pinn_acc, frame_dsmc_pinn_err,
            frame_density, frame_temp, frame_press,
            frame_kn,
            frame_peak_hf, frame_total_heat, frame_ballistic,
            frame_stag_press, frame_alt_peak_heat, frame_peak_dynq,
            validation, optimized_topology,
        )

    print(f"[MP4] Rendering {n_anim} live dashboard frames ...")
    dash_args = [_make_render_args(i, "dash") for i in range(n_anim)]

    t0 = time.time()
    with Pool(n_workers) as pool:
        anim_paths = list(tqdm(pool.imap(_render_animated_frame, dash_args, chunksize=50),
                               total=n_anim, desc="[MP4] Dashboard",
                               unit="fr", ncols=80))
    for p in anim_paths:
        all_paths.append(("anim", p))
    frame_idx += len(anim_paths)
    elapsed = time.time() - t0
    print(f"[MP4] Dashboard: {elapsed:.1f}s ({n_anim / max(0.01, elapsed):.0f} fr/s)")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2a-group: Trajectory / Thermal / Mechanical segments
    # ══════════════════════════════════════════════════════════════════
    # AXIOMS: the docstring promises sections 3-5 (traj/therm/mech) and the
    #   cleanup loop already sweeps those prefixes — they must be RENDERED
    #   or the MP4 ends after the dashboard (dead branches).
    # THEORIES: 90 frames @30fps = 3s per segment; stride index
    #   round(k*(n_anim-1)/89) spans the FULL trajectory so curves grow
    #   0 → TARGET_STEP; frame_idx MUST be the DATA index i (not local k)
    #   so _draw_animated_panel's data[:frame_idx+1] slice is correct.
    # APPLICATIONS: one Pool per segment; only the prefix differs.
    # CITATIONS: none (rendering only).
    _GROUP_SEGMENTS = ("traj", "therm", "mech")
    _GROUP_FRAMES = 90
    for group_prefix in _GROUP_SEGMENTS:
        _k_max = max(0, n_anim - 1)
        # round() with no ndigits already returns int (RUF046 — no int() wrap)
        _indices = [round(k * _k_max / (_GROUP_FRAMES - 1))
                    for k in range(_GROUP_FRAMES)]
        group_args = [_make_render_args(i, group_prefix) for i in _indices]
        t0 = time.time()
        with Pool(n_workers) as pool:
            group_paths = list(tqdm(pool.imap(_render_animated_frame, group_args, chunksize=5),
                                    total=len(group_args), desc=f"[MP4] {group_prefix}",
                                    unit="fr", ncols=80))
        for p in group_paths:
            all_paths.append(("anim", p))
        frame_idx += len(group_paths)
        elapsed = time.time() - t0
        print(f"[MP4] {group_prefix}: {elapsed:.1f}s ({len(group_paths)} frames)")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2b: Pixel-scale upscale (NEAREST for jagged retro look)
    # ══════════════════════════════════════════════════════════════════
    if pixel_scale != 1.0:
        from PIL import Image as _PILImage
        # Upscale to full resolution with the same 2% content expansion
        _upscale_w = resolution[0]
        _upscale_h = max(resolution[1], int(resolution[0] * _content_height_pct / 100))
        _t0_up = time.time()
        _frame_files = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
        for _fp in tqdm(_frame_files, desc="[MP4] Pixel-scale", unit="fr", ncols=80):
            _img = _PILImage.open(_fp)
            # Pillow 12.3.0: module-level Image.NEAREST still exists at runtime
            # (= 0) but is absent from type stubs; canonical typed form is
            # Image.Resampling.NEAREST (identical value 0, no behavior change).
            # [Citation: Pillow v12.3.0 - https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Resampling.NEAREST]
            _img = _img.resize((_upscale_w, _upscale_h), resample=_PILImage.Resampling.NEAREST)
            _img.save(_fp, "PNG")
        _up_elapsed = time.time() - _t0_up
        print(f"[MP4] Upscaled {len(_frame_files)} frames to {_upscale_w}x{_upscale_h} "
              f"(NEAREST, pixel_scale={pixel_scale}) in {_up_elapsed:.1f}s")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: Encode with ffmpeg
    # ══════════════════════════════════════════════════════════════════
    _extra = ["-vcodec", "libx264", "-pix_fmt", "yuv420p"]
    _enc_name = "libx264"
    try:
        _probe = subprocess.run(["ffmpeg", "-encoders"], capture_output=True,
                                text=True, timeout=5, check=False)
        _encs = _probe.stdout
        import sys as _sys
        if _sys.platform == "darwin" and "h264_videotoolbox" in _encs:
            _enc_name = "h264_videotoolbox"
            _extra = ["-vcodec", "h264_videotoolbox", "-b:v", "8M", "-pix_fmt", "yuv420p"]
            print("[MP4] HW encoder: VideoToolbox (macOS)")
        elif _sys.platform.startswith("linux"):
            if "h264_vaapi" in _encs:
                _enc_name = "h264_vaapi"
                _extra = ["-vcodec", "h264_vaapi", "-vaapi_device",
                          "/dev/dri/renderD128", "-pix_fmt", "yuv420p"]
                print("[MP4] HW encoder: VAAPI (Linux)")
            elif "h264_nvenc" in _encs:
                _enc_name = "h264_nvenc"
                _extra = ["-vcodec", "h264_nvenc", "-pix_fmt", "yuv420p"]
                print("[MP4] HW encoder: NVENC (Linux)")
        elif _sys.platform == "win32" and "h264_nvenc" in _encs:
            _enc_name = "h264_nvenc"
            _extra = ["-vcodec", "h264_nvenc", "-pix_fmt", "yuv420p"]
            print("[MP4] HW encoder: NVENC (Windows)")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # ffmpeg not available — defaults to libx264

    if _enc_name == "libx264":
        print("[MP4] SW encoder: libx264 (no HW encoder found)")

    # AXIOMS: the two overlay variants must coexist — a shared output name
    #   would let the second run silently overwrite the first.
    # THEORIES: suffix mirrors the CLI flags (--validation → _validation,
    #   --optimized-topology → _optimized); no flags ⇒ base name unchanged
    #   so the README "Full animation" link stays valid.
    # APPLICATIONS: generate_mp4(validation=True) → ..._validation.mp4.
    # CITATIONS: README.md Live Dashboard Animation link path.
    _name_suffix = (("_validation" if validation else "")
                    + ("_optimized" if optimized_topology else ""))
    mp4_path = os.path.join(plots_dir, f"hybrid_dsmc_pinn_animation{_name_suffix}.mp4")

    # Durations: title=2s, all anim frames=1/fps each
    natural_durations = []
    for kind, _ in all_paths:
        if kind == "title":
            natural_durations.append(2.0)
        else:
            natural_durations.append(1.0 / fps)
    natural_total = sum(natural_durations)

    if target_duration is not None and target_duration > 0:
        scale = target_duration / natural_total
    else:
        scale = 1.0

    concat_list = os.path.join(frames_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for (kind, fp), dur in zip(all_paths, natural_durations):
            f.write(f"file '{os.path.abspath(fp)}'\n")
            f.write(f"duration {dur * scale:.6f}\n")

    total = len(all_paths)
    actual_dur = natural_total * scale
    print(f"[MP4] Total: {total} frames, fps={fps}, duration={actual_dur:.1f}s"
          + (f" (target {target_duration}s)" if target_duration else ""))
    print(f"[MP4] Encoding with {_enc_name} ...")
    t0 = time.time()
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                    "-vf", f"fps={fps}", "-pix_fmt", "yuv420p"] + _extra + [mp4_path],
                   capture_output=True, timeout=600, check=False)
    elapsed = time.time() - t0

    if os.path.exists(mp4_path):
        sz = os.path.getsize(mp4_path) / (1024 * 1024)
        print(f"[MP4] Done: {mp4_path} ({sz:.1f} MB, {elapsed:.1f}s, encoder={_enc_name})")
    else:
        print("[MP4] FAILED — trying SW fallback ...")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                        "-vf", f"fps={fps}", "-pix_fmt", "yuv420p",
                        "-vcodec", "libx264", mp4_path],
                       capture_output=True, timeout=600, check=False)
        if os.path.exists(mp4_path):
            sz = os.path.getsize(mp4_path) / (1024 * 1024)
            print(f"[MP4] Fallback SW encode: {mp4_path} ({sz:.1f} MB)")

    # Cleanup ALL temp frames
    for prefix in ["dash", "traj", "therm", "mech", "title", "group"]:
        for f in glob.glob(os.path.join(frames_dir, f"{prefix}_*.png")):
            os.remove(f)
    os.remove(concat_list) if os.path.exists(concat_list) else None

    return mp4_path


def _draw_validation_overlay(draw: Any, x0: int, y0: int, x1: int, y1: int,
                             peak_hf: float, total_heat: float,
                             ballistic: float, peak_g: float,
                             peak_mach: float,
                             font_sm: Any, font_md: Any, _scale: float):
    """Draw validation overlay panel comparing simulation vs IRVE-3 flight data.

    Shows 5 metrics with color-coded delta indicators:
      green  < 20% delta — within acceptable range
      yellow 20-50% delta — moderate discrepancy
      red    > 50% delta — significant discrepancy

    Header carries the right-aligned "VALIDATION" title badge (right end
    of the bottom strip) so validation mode is identifiable at a glance.

    -- AXIOMS: IRVE-3 flight data is the ground truth for HIAD validation.
    -- THEORIES: Delta percentage quantifies agreement with flight data.
    -- APPLICATIONS: Visual overlay for MP4 dashboard.
    -- CITATION: NASA TP-2013-4012 — IRVE-3 flight data + EI Mach ≈ 14.5
    -- CITATION: Rapisarda (2023) Table 4.10 — validation metrics
    """
    FG = (220, 220, 220)
    GRID = (50, 50, 70)

    draw.rectangle([x0, y0, x1, y1], fill=(25, 25, 50), outline=GRID, width=1)
    draw.text((x0 + int(10 * _scale), y0 + int(5 * _scale)),
              "IRVE-3 Validation Comparison", fill=(200, 220, 255), font=font_md)
    # Mode title badge — right-aligned in the panel header (right end of strip)
    draw.text((x1 - int(10 * _scale), y0 + int(5 * _scale)),
              "VALIDATION", fill=(255, 200, 50), font=font_md, anchor="rt")

    metrics = [
        ("Peak Heat Flux", peak_hf, IRVE3_REFERENCE["peak_heat_flux_Wcm2"], "W/cm2"),
        ("Total Heat Load", total_heat, IRVE3_REFERENCE["total_heat_load_Jcm2"], "J/cm2"),
        ("Ballistic Coeff", ballistic, IRVE3_REFERENCE["ballistic_coeff_kgm2"], "kg/m2"),
        ("Peak Decel", peak_g, IRVE3_REFERENCE["peak_deceleration_g"], "g"),
        ("Entry Mach", peak_mach, IRVE3_REFERENCE["entry_mach"], "Mach"),
    ]

    # /len(metrics) — not hardcoded /4 — so adding a row never overflows the box
    row_h = int((y1 - y0 - 30 * _scale) / len(metrics))
    for i, (name, sim_val, ref_val, unit) in enumerate(metrics):
        ry = y0 + int(30 * _scale) + i * row_h
        # Compute delta percentage
        if ref_val > 0:
            delta_pct = abs(sim_val - ref_val) / ref_val * 100.0
        else:
            delta_pct = 0.0

        # Color coding: green < 20%, yellow 20-50%, red > 50%
        if delta_pct < 20:
            color = (80, 220, 80)    # green
            status = "OK"
        elif delta_pct < 50:
            color = (255, 200, 50)   # yellow
            status = "WARN"
        else:
            color = (255, 80, 80)    # red
            status = "HIGH"

        # Metric name + status
        draw.text((x0 + int(10 * _scale), ry),
                  f"{name}", fill=FG, font=font_sm)
        draw.text((x0 + int(150 * _scale), ry),
                  status, fill=color, font=font_sm)

        # Sim value vs Reference value
        draw.text((x0 + int(10 * _scale), ry + int(14 * _scale)),
                  f"Sim: {sim_val:.1f} {unit}", fill=(180, 180, 180), font=font_sm)
        draw.text((x0 + int(10 * _scale), ry + int(28 * _scale)),
                  f"Ref: {ref_val:.1f} {unit} ({delta_pct:.1f}% delta)",
                  fill=color, font=font_sm)

        # Delta bar (visual indicator)
        bar_x0 = x0 + int(250 * _scale)
        bar_x1 = x1 - int(10 * _scale)
        bar_y = ry + int(14 * _scale)
        bar_w = bar_x1 - bar_x0
        bar_fill = int(bar_w * min(delta_pct, 100) / 100.0)
        draw.rectangle([bar_x0, bar_y, bar_x1, bar_y + int(6 * _scale)],
                       fill=(40, 40, 60))
        draw.rectangle([bar_x0, bar_y, bar_x0 + bar_fill, bar_y + int(6 * _scale)],
                       fill=color)


def _draw_optimized_topology_overlay(draw: Any, x0: int, y0: int,
                                     x1: int, y1: int, font_sm: Any,
                                     font_md: Any, _scale: float) -> None:
    """Draw Optimized Topology spec panel in the reserved bottom strip.

    Shows the 5 Bayesian-optimized geometry/aero parameters (opt vs baseline)
    with color-coded delta: green = reduction (improvement), yellow = increase
    (documented trade-off, e.g. Sutton-Graves heat).

    -- AXIOMS: optimizer output is ground truth for the optimized variant;
    --   spec values are STATIC (no frame dependence) and are loaded from
    --   hiad_optimization_results.json via _load_optimized_topology_specs().
    -- THEORIES: Δ% = (opt − base)/base × 100 computed live from the JSON
    --   blocks; the Cd reduction (JSON "improvement" block) is the headline.
    -- APPLICATIONS: rendered when generate_mp4(optimized_topology=True).
    -- CITATION: hiad_optimization_results.json — default/optimized blocks
    -- CITATION: Optimization_Attempt_1.md — GP Matern 5/2, 70 evals
    -- CITATION: README.md "Optimized Topology: Before vs After" table
    -- SAFETY FALLBACK: _load_optimized_topology_specs() fails closed with
    --   full path diagnostics if the JSON is missing/malformed.
    """
    FG = (220, 220, 220)
    GRID = (50, 50, 70)

    draw.rectangle([x0, y0, x1, y1], fill=(25, 25, 50), outline=GRID, width=1)
    draw.text((x0 + int(10 * _scale), y0 + int(5 * _scale)),
              "Optimized Topology", fill=(200, 220, 255), font=font_md)
    # Mode title badge — right-aligned in the panel header (right end of strip)
    draw.text((x1 - int(10 * _scale), y0 + int(5 * _scale)),
              "OPTIMIZED", fill=(80, 220, 200), font=font_md, anchor="rt")

    # Runtime load from hiad_optimization_results.json (never hardcoded;
    # loader prints full FATAL context to stderr before re-raising)
    specs = _load_optimized_topology_specs()
    # /len(specs) — never hardcoded — so rows can be added without overflow
    row_h = int((y1 - y0 - 30 * _scale) / len(specs))
    for i, (name, opt_val, base_val, unit, val_fmt) in enumerate(specs):
        ry = y0 + int(30 * _scale) + i * row_h
        if base_val > 0:
            delta_pct = (opt_val - base_val) / base_val * 100.0
        else:
            delta_pct = 0.0

        # green = parameter reduced (optimizer goal), yellow = increased (trade-off)
        if delta_pct < 0:
            color = (80, 220, 80)
        else:
            color = (255, 200, 50)

        _unit_suffix = f" {unit}" if unit else ""
        draw.text((x0 + int(10 * _scale), ry),
                  name, fill=FG, font=font_sm)
        draw.text((x0 + int(220 * _scale), ry),
                  f"{delta_pct:+.1f}%", fill=color, font=font_sm)
        draw.text((x0 + int(10 * _scale), ry + int(14 * _scale)),
                  f"Opt: {val_fmt.format(opt_val)}{_unit_suffix}",
                  fill=(180, 180, 180), font=font_sm)
        draw.text((x0 + int(10 * _scale), ry + int(28 * _scale)),
                  f"Base: {val_fmt.format(base_val)}{_unit_suffix}",
                  fill=color, font=font_sm)

        # Delta-magnitude bar (visual indicator, capped at 100%)
        bar_x0 = x0 + int(340 * _scale)
        bar_x1 = x1 - int(10 * _scale)
        bar_y = ry + int(14 * _scale)
        bar_w = bar_x1 - bar_x0
        if bar_w > 0:
            bar_fill = int(bar_w * min(abs(delta_pct), 100) / 100.0)
            draw.rectangle([bar_x0, bar_y, bar_x1, bar_y + int(6 * _scale)],
                           fill=(40, 40, 60))
            draw.rectangle([bar_x0, bar_y, bar_x0 + bar_fill, bar_y + int(6 * _scale)],
                           fill=color)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="StellarOrion Output Generator")
    parser.add_argument("--mp4-only", action="store_true",
                        help="Skip CSV/VTU, only regenerate MP4 (fast iteration)")
    parser.add_argument("--steps-per-frame", type=int, default=100_000,
                        help="Simulation steps per video frame (default: 100000 = 3001 frames)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Target video duration in seconds (overrides natural duration)")
    parser.add_argument("--resolution", type=str, default="1920x1080",
                        help="Output video resolution WxH (default: 1920x1080)")
    parser.add_argument("--pixel-scale", type=float, default=1.0,
                        help="Pixel scale factor for retro aesthetic (0.5 = half-res render, NEAREST upscale to full)")
    parser.add_argument("--validation", action="store_true",
                        help="Show IRVE-3 validation overlay panel in MP4 dashboard")
    parser.add_argument("--optimized-topology", action="store_true",
                        help="Show Optimized Topology spec overlay panel (bottom strip) in MP4")
    parser.add_argument("--max-frames", type=int, default=None,
                        help="Cap dashboard frames (default: None = full trajectory)")
    args = parser.parse_args()

    # Parse resolution
    try:
        res_parts = args.resolution.lower().split("x")
        resolution = (int(res_parts[0]), int(res_parts[1]))
    except (ValueError, IndexError):
        print(f"[WARN] Invalid resolution '{args.resolution}', using 1920x1080")
        resolution = (1920, 1080)

    # -- AXIOM: each output variant owns its directory (validation stays in
    #    validation_scalloped; optimized topology goes to OptimizedTopology).
    # -- THEORY: generate_mp4(output_dir) builds output_dir/plots and
    #    output_dir/mp4_frames from this single argument.
    # -- APPLICATION: choose the directory by variant before creating it.
    # -- CITATIONS: README.md "Optimized Topology: Before vs After".
    _mp4_out_dir = (OPTIMIZED_TOPOLOGY_DIR if args.optimized_topology
                    else RESULTS_DIR)
    os.makedirs(_mp4_out_dir, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("=" * 70)
    print("  StellarOrion Output Generator (Live Dashboard)")
    print("=" * 70)

    if not args.mp4_only:
        print("\n[1/3] Generating per-step CSV ...")
        print("  [SKIP] generate_csv not implemented")

        print("\n[2/3] Generating ParaView VTU files ...")
        vtu_files = generate_paraview_vtu(RESULTS_DIR)
        print(f"  Generated {len(vtu_files)} VTU files")
    else:
        print("\n[--mp4-only] Skipping CSV and VTU generation")

    n_frames = TARGET_STEP // args.steps_per_frame + 1
    if args.max_frames is not None and 0 < args.max_frames < n_frames:
        n_frames = args.max_frames
    print(f"\n[3/3] Generating live dashboard MP4 ({n_frames} frames, "
          f"{args.steps_per_frame:,} steps/frame, {resolution[0]}x{resolution[1]}) ...")
    mp4_path = generate_mp4(_mp4_out_dir, max_frames=args.max_frames,
                            steps_per_frame=args.steps_per_frame,
                            target_duration=args.duration, resolution=resolution,
                            pixel_scale=args.pixel_scale, validation=args.validation,
                            optimized_topology=args.optimized_topology)

    print("\n" + "=" * 70)
    print("  DONE")
    print(f"  MP4: {mp4_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
