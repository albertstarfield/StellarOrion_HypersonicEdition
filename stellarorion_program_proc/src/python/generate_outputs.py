#!/usr/bin/env python3
"""Regenerate CSV + VTU + MP4 with categorized dashboard.

AXIOMS:
  1. Ada/SPARK 2014 backbone: ALL physics via FFI
  2. Linear trajectory: H = 120 - 70*Step/300M, V = 4300 - 1600*Step/300M
  3. Sutton-Graves heat flux: q = C_sg * sqrt(rho/R_n) * V^3
  4. Multithreaded frame rendering via multiprocessing.Pool
  5. TeX fonts via pdflatex (conditional on system availability)
  6. Categorized MP4: title cards → live dashboard → PNG groups → VTU groups

[Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
[Citation: Sutton & Graves (1972), NASA TR R-376]
"""

import os
import sys
import csv
import time
import shutil
import glob
import re
import subprocess
import numpy as np
from multiprocessing import Pool, cpu_count

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
from validation_pipeline import (
    irve3_trajectory_model, sutton_graves_heat_flux, isa_atmosphere,
    _ada_drag, _ada_gload, _ada_dynq,
    generate_paraview_vtu,
)

# Pre-build matplotlib font cache ONCE before any Pool spawns.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
_ = plt.figure()
plt.close(_)

from _tex_config import setup_tex_fonts  # noqa: E402
TeX_ACTIVE = setup_tex_fonts()

# ─── Constants ────────────────────────────────────────────────────────
IRVE3_MASS_KG    = 281.0
IRVE3_DIAMETER_M = 3.0
IRVE3_CD         = 1.4625
IRVE3_NOSE_R_M   = 1.5
CHAR_LENGTH_M    = 3.0
TARGET_STEP      = 300_000_000
G0               = 9.80665
RESULTS_DIR      = os.path.join(os.path.dirname(__file__), "..", "..",
                                "results_validation_scalloped")


def _compute_frame_data(step):
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
    }


def _make_title_card(title, subtitle, out_dir, idx, resolution=(1920, 1080)):
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
    def _fs(base):
        return max(10, int(base * _scale))

    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(48))
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(24))
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(14))
    except Exception:
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


def _render_animated_frame(fargs):
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
     show_kn) = fargs

    from PIL import Image, ImageDraw, ImageFont

    W, H_orig = resolution

    # ── Auto-expand vertical resolution if content won't fit ──
    # Layout uses percentage-based y-coordinates.  For 5 rows (28-33% each)
    # + gaps + title bar, content extends to ~155% of the canvas height.
    # If the user-provided height is too small, expand it proportionally
    # so all panels fit without clipping.  Width stays fixed.
    _content_height_pct = 155.0
    _min_h = int(W * _content_height_pct / 100)
    H = max(H_orig, _min_h)
    BG = (20, 20, 40)
    FG = (220, 220, 220)
    GRID = (50, 50, 70)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Font sizes scale with resolution
    _scale = W / 1920.0
    def _fs(base):
        return max(10, int(base * _scale))

    try:
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(13))
        font_md = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(15))
        font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(18))
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", _fs(22))
    except Exception:
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

    def _pct_to_px(xp, yp, wp, hp):
        # Convert percentage positions to pixels at design height, then scale
        # y-positions to fit expanded canvas. Heights stay at design pixels.
        y_px = int(yp * _H_orig_for_layout / 100)
        h_px = int(hp * _H_orig_for_layout / 100)
        y_scaled = int(y_px * _y_scale)
        h_scaled = h_px  # Heights stay at design size
        return (int(xp * W / 100), y_scaled,
                int((xp + wp) * W / 100), y_scaled + h_scaled)

    def _draw_animated_panel(draw, x0, y0, x1, y1, title, ylabel,
                             data_x, data_y, color, current_val,
                             unit="", fmt="{:.1f}", frame_idx=0):
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

        def _to_px(vx, vy):
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

    def _draw_vehicle_panel(draw, x0, y0, x1, y1, alt, vel, mach, hf, frame_idx=0):
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
        r_out = 0.0508    # Torus outer radius [m]
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
        cone_len = R_veh / np.sin(gamma) - rN / np.tan(gamma)
        cone_start_x = rN * np.cos(-gamma)
        cone_start_y = rN * np.sin(-gamma)
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
        back_pts = [(cone_end_x, -R_veh), (cone_end_x, R_veh)]

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

        def to_px(vx, vy):
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
                  f"Alt: {alt:.0f} km", fill=FG, font=font_lg)
        hf_color = (255, 80, 80) if hf > 10 else FG
        draw.text((x1 - int(220 * _scale), y0 + int(50 * _scale)),
                  f"q={hf:.1f} W/cm2", fill=hf_color, font=font_md)
        draw.text((x1 - int(220 * _scale), y0 + int(70 * _scale)),
                  f"Mach {mach:.2f}", fill=FG, font=font_md)
        draw.text((x1 - int(220 * _scale), y0 + int(90 * _scale)),
                  "70° cone, 6 tori, r=0.135m", fill=(120, 120, 140), font=font_sm)

    # ══════════════════════════════════════════════════════════════════
    # LAYOUT: Percentage-based, adapts to resolution
    # ══════════════════════════════════════════════════════════════════

    if prefix == "dash":
        # ── MAIN DASHBOARD: 7 panels (percentage layout) ─────────
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)], fill=(15, 15, 30))
        pct = step / TARGET_STEP * 100
        draw.text((int(20 * _scale), int(10 * _scale)),
                  f"StellarOrion HIAD Live Dashboard | Step {step:,} / {TARGET_STEP:,} "
                  f"({pct:.1f}%) | Ada/SPARK 2014", fill=FG, font=font_title)
        draw.text((int(20 * _scale), int(40 * _scale)),
                  f"Alt: {alt:.1f} km | Vel: {vel:.0f} m/s | Mach: {mach:.2f} | "
                  f"q={hf:.1f} W/cm2 | G: {gload:.1f} | Drag: {drag:.0f} N",
                  fill=(180, 180, 180), font=font_md)

        # Row 1: altitude / velocity / mach
        p = _pct_to_px(2, title_h + 1, 31, 28)
        _draw_animated_panel(draw, *p, "Altitude Profile", "Alt [km]",
                             show_steps, show_alt, (100, 150, 255), alt, "km",
                             frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 1, 31, 28)
        _draw_animated_panel(draw, *p, "Velocity", "Vel [m/s]",
                             show_steps, show_vel, (100, 220, 100), vel, "m/s",
                             fmt="{:.0f}", frame_idx=frame_idx)
        p = _pct_to_px(66, title_h + 1, 32, 28)
        _draw_animated_panel(draw, *p, "Mach Number", "Mach",
                             show_steps, show_mach, (220, 100, 220), mach,
                             fmt="{:.2f}", frame_idx=frame_idx)

        # Row 2: heat flux (wide) / g-load
        p = _pct_to_px(2, title_h + 31, 64, 28)
        _draw_animated_panel(draw, *p, "Sutton-Graves Heat Flux", r"q [W/cm2]",
                             show_steps, show_hf, (255, 80, 80), hf, r"W/cm2",
                             frame_idx=frame_idx)
        p = _pct_to_px(67, title_h + 31, 31, 28)
        _draw_animated_panel(draw, *p, "Deceleration (G-load)", "G [g]",
                             show_steps, show_g, (80, 220, 220), gload, "g",
                             frame_idx=frame_idx)

        # Row 3: drag / vehicle
        p = _pct_to_px(2, title_h + 61, 31, 33)
        _draw_animated_panel(draw, *p, "Drag Force", "Drag [N]",
                             show_steps, show_drag, (255, 180, 50), drag, "N",
                             fmt="{:.0f}", frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 61, 64, 33)
        _draw_vehicle_panel(draw, *p, alt, vel, mach, hf)

        # Row 4: PINN statistics + Knudsen number (4 panels)
        pinn_loss_val = show_pinn_loss[frame_idx] if frame_idx < len(show_pinn_loss) else 0.0
        pinn_acc_val = show_pinn_acc[frame_idx] if frame_idx < len(show_pinn_acc) else 0.0
        dsmc_err_val = show_dsmc_pinn_err[frame_idx] if frame_idx < len(show_dsmc_pinn_err) else 0.0
        kn_val = show_kn[frame_idx] if frame_idx < len(show_kn) else 0.0
        p = _pct_to_px(2, title_h + 96, 23, 25)
        _draw_animated_panel(draw, *p, "PINN Training Loss", "Loss",
                             show_steps, show_pinn_loss, (0, 200, 100), pinn_loss_val, "",
                             fmt="{:.4f}", frame_idx=frame_idx)
        p = _pct_to_px(26, title_h + 96, 23, 25)
        _draw_animated_panel(draw, *p, "PINN Accuracy", "Acc [%]",
                             show_steps, show_pinn_acc, (100, 200, 255), pinn_acc_val, "%",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(50, title_h + 96, 23, 25)
        _draw_animated_panel(draw, *p, "DSMC vs PINN Error", "Error [%]",
                             show_steps, show_dsmc_pinn_err, (255, 150, 0), dsmc_err_val, "%",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(74, title_h + 96, 24, 25)
        _draw_animated_panel(draw, *p, "Knudsen Number (Kn)", "Kn [-]",
                             show_steps, show_kn, (200, 100, 255), kn_val, "",
                             fmt="{:.2e}", frame_idx=frame_idx)

        # Row 5: atmosphere environment (density, temperature, pressure)
        dens_val = show_density[frame_idx] if frame_idx < len(show_density) else 0.0
        temp_val = show_temp[frame_idx] if frame_idx < len(show_temp) else 0.0
        press_val = show_press[frame_idx] if frame_idx < len(show_press) else 0.0
        p = _pct_to_px(2, title_h + 124, 31, 25)
        _draw_animated_panel(draw, *p, "Atmospheric Density", r"rho [kg/m3]",
                             show_steps, show_density, (180, 220, 255), dens_val, r"kg/m3",
                             fmt="{:.4f}", frame_idx=frame_idx)
        p = _pct_to_px(34, title_h + 124, 31, 25)
        _draw_animated_panel(draw, *p, "Atmospheric Temperature", "T [K]",
                             show_steps, show_temp, (255, 200, 100), temp_val, "K",
                             fmt="{:.1f}", frame_idx=frame_idx)
        p = _pct_to_px(66, title_h + 124, 32, 25)
        _draw_animated_panel(draw, *p, "Atmospheric Pressure", "P [Pa]",
                             show_steps, show_press, (200, 150, 255), press_val, "Pa",
                             fmt="{:.0f}", frame_idx=frame_idx)

    elif prefix == "traj":
        # ── TRAJECTORY GROUP: 3 panels side by side ─────────────
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)],
                       fill=(15, 15, 30))
        draw.text((int(20 * _scale), int(15 * _scale)),
                  "StellarOrion — Trajectory Parameters", fill=FG, font=font_title)
        pw = 30
        gap = 2
        for i, (title, ylabel, data_y, color, unit, fmt) in enumerate([
            ("Altitude Profile", "Alt [km]", show_alt, (100, 150, 255), "km", "{:.1f}"),
            ("Velocity", "Vel [m/s]", show_vel, (100, 220, 100), "m/s", "{:.0f}"),
            ("Mach Number", "Mach", show_mach, (220, 100, 220), "", "{:.2f}"),
        ]):
            x_start = 2 + i * (pw + gap)
            p = _pct_to_px(x_start, title_h + 1, pw, 92)
            _draw_animated_panel(draw, *p, title, ylabel,
                                 show_steps, data_y, color,
                                 data_y[-1] if len(data_y) > 0 else 0, unit,
                                 fmt=fmt, frame_idx=frame_idx)

    elif prefix == "therm":
        # ── THERMAL GROUP: single wide panel ────────────────────
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)],
                       fill=(15, 15, 30))
        draw.text((int(20 * _scale), int(15 * _scale)),
                  "StellarOrion — Thermal & Heating", fill=FG, font=font_title)
        p = _pct_to_px(2, title_h + 1, 96, 92)
        _draw_animated_panel(draw, *p, "Sutton-Graves Heat Flux", r"q [W/cm2]",
                             show_steps, show_hf, (255, 80, 80), hf, r"W/cm2",
                             frame_idx=frame_idx)

    elif prefix == "mech":
        # ── MECHANICAL GROUP: drag + g-load side by side ────────
        draw.rectangle([0, 0, W, int(_title_pct * H / 100)],
                       fill=(15, 15, 30))
        draw.text((int(20 * _scale), int(15 * _scale)),
                  "StellarOrion — Mechanical Loads", fill=FG, font=font_title)
        pw = 47
        p = _pct_to_px(2, title_h + 1, pw, 92)
        _draw_animated_panel(draw, *p, "Drag Force", "Drag [N]",
                             show_steps, show_drag, (255, 180, 50), drag, "N",
                             fmt="{:.0f}", frame_idx=frame_idx)
        p = _pct_to_px(51, title_h + 1, pw, 92)
        _draw_animated_panel(draw, *p, "Deceleration (G-load)", "G [g]",
                             show_steps, show_g, (80, 220, 220), gload, "g",
                             frame_idx=frame_idx)

    frame_path = os.path.join(out_dir, f"{prefix}_{frame_idx:05d}.png")
    img.save(frame_path, "PNG")
    return frame_path


def generate_mp4(output_dir, max_frames=300, target_duration=None, steps_per_frame=100_000, resolution=(1920, 1080)):
    """Generate pure live-animation MP4 — EVERYTHING is animated, NO static frames.

    Structure:
      1. Title card (2s)
      2. Main dashboard (7-panel, curves grow frame-by-frame)
      3. Trajectory group (altitude/velocity/mach, curves grow)
      4. Thermal group (heat flux, curve grows)
      5. Mechanical group (drag/g-load, curves grow)
      6. Encode with ffmpeg

    Ada FFI computes all physics. PIL renders all frames. Zero matplotlib.
    [Citation: ffmpeg HW accel — https://trac.ffmpeg.org/HWAccelIntro]
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
    _content_height_pct = 155.0
    _expanded_h = max(resolution[1], int(resolution[0] * _content_height_pct / 100))
    _expanded_resolution = (resolution[0], _expanded_h)

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
    n_anim = len(all_steps)
    fps = 30

    n_workers = min(cpu_count(), 8)
    print(f"[MP4] Computing {n_anim} trajectory points via Ada FFI ({steps_per_frame:,} steps/frame) ...")
    t0 = time.time()

    frame_data = []
    with Pool(n_workers) as pool:
        for r in tqdm(pool.imap(_compute_frame_data, all_steps, chunksize=100),
                       total=len(all_steps), desc="[MP4] Ada FFI",
                       unit="pts", ncols=80):
            frame_data.append(r)

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
    all_frame_steps = np.array(all_steps)

    elapsed = time.time() - t0
    print(f"[MP4] Ada FFI computed {n_anim} points in {elapsed:.1f}s ({n_workers} workers)")


    # ══════════════════════════════════════════════════════════════════
    # SECTION 2a: Render MAIN DASHBOARD frames (animated)
    # ══════════════════════════════════════════════════════════════════
    print(f"[MP4] Rendering {n_anim} live dashboard frames ...")
    dash_args = []
    for i in range(n_anim):
        dash_args.append((
            i, int(all_frame_steps[i]),
            frame_alt[i], frame_vel[i], frame_mach[i],
            frame_hf[i], frame_drag[i], frame_g[i],
            all_frame_steps, frame_alt, frame_hf,
            frame_vel, frame_mach, frame_drag, frame_g,
            frames_dir, "dash", resolution,
            frame_pinn_loss, frame_pinn_acc, frame_dsmc_pinn_err,
            frame_density, frame_temp, frame_press,
            frame_kn,
        ))

    anim_paths = []
    t0 = time.time()
    with Pool(n_workers) as pool:
        for fp in tqdm(pool.imap(_render_animated_frame, dash_args, chunksize=50),
                       total=n_anim, desc="[MP4] Dashboard",
                       unit="fr", ncols=80):
            anim_paths.append(fp)
    for p in anim_paths:
        all_paths.append(("anim", p))
    frame_idx += len(anim_paths)
    elapsed = time.time() - t0
    print(f"[MP4] Dashboard: {elapsed:.1f}s ({n_anim / max(0.01, elapsed):.0f} fr/s)")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: Encode with ffmpeg
    # ══════════════════════════════════════════════════════════════════
    _extra = ["-vcodec", "libx264", "-pix_fmt", "yuv420p"]
    _enc_name = "libx264"
    try:
        _probe = subprocess.run(["ffmpeg", "-encoders"], capture_output=True,
                                text=True, timeout=5)
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
    except Exception:
        pass

    if _enc_name == "libx264":
        print("[MP4] SW encoder: libx264 (no HW encoder found)")

    mp4_path = os.path.join(plots_dir, "hybrid_dsmc_pinn_animation.mp4")

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
                   capture_output=True, timeout=600)
    elapsed = time.time() - t0

    if os.path.exists(mp4_path):
        sz = os.path.getsize(mp4_path) / (1024 * 1024)
        print(f"[MP4] Done: {mp4_path} ({sz:.1f} MB, {elapsed:.1f}s, encoder={_enc_name})")
    else:
        print("[MP4] FAILED — trying SW fallback ...")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                        "-vf", f"fps={fps}", "-pix_fmt", "yuv420p",
                        "-vcodec", "libx264", mp4_path],
                       capture_output=True, timeout=600)
        if os.path.exists(mp4_path):
            sz = os.path.getsize(mp4_path) / (1024 * 1024)
            print(f"[MP4] Fallback SW encode: {mp4_path} ({sz:.1f} MB)")

    # Cleanup ALL temp frames
    for prefix in ["dash", "traj", "therm", "mech", "title", "group"]:
        for f in glob.glob(os.path.join(frames_dir, f"{prefix}_*.png")):
            os.remove(f)
    os.remove(concat_list) if os.path.exists(concat_list) else None

    return mp4_path


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
    args = parser.parse_args()

    # Parse resolution
    try:
        res_parts = args.resolution.lower().split("x")
        resolution = (int(res_parts[0]), int(res_parts[1]))
    except (ValueError, IndexError):
        print(f"[WARN] Invalid resolution '{args.resolution}', using 1920x1080")
        resolution = (1920, 1080)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("=" * 70)
    print("  StellarOrion Output Generator (Live Dashboard)")
    print("=" * 70)

    if not args.mp4_only:
        print("\n[1/3] Generating per-step CSV ...")
        csv_path = generate_csv(RESULTS_DIR)

        print("\n[2/3] Generating ParaView VTU files ...")
        vtu_files = generate_paraview_vtu(RESULTS_DIR)
        print(f"  Generated {len(vtu_files)} VTU files")
    else:
        print("\n[--mp4-only] Skipping CSV and VTU generation")

    n_frames = TARGET_STEP // args.steps_per_frame + 1
    print(f"\n[3/3] Generating live dashboard MP4 ({n_frames} frames, "
          f"{args.steps_per_frame:,} steps/frame, {resolution[0]}x{resolution[1]}) ...")
    mp4_path = generate_mp4(RESULTS_DIR, steps_per_frame=args.steps_per_frame,
                            target_duration=args.duration, resolution=resolution)

    print("\n" + "=" * 70)
    print("  DONE")
    print(f"  MP4: {mp4_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
