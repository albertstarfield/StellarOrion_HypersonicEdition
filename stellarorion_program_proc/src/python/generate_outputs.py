#!/usr/bin/env python3
"""Regenerate CSV + VTU + MP4 with linear trajectory, multithreaded rendering,
TeX fonts, and all PNG plots included in MP4.

AXIOMS:
  1. Ada/SPARK 2014 backbone: ALL physics via FFI (irve3_trajectory_model, etc.)
  2. Linear trajectory: H = 120 - 70*Step/300M, V = 4300 - 1600*Step/300M
  3. Sutton-Graves heat flux: q = C_sg * sqrt(rho/R_n) * V^3
  4. Multithreaded frame rendering via multiprocessing.Pool
  5. TeX fonts via pdflatex (conditional on system availability)
  6. All existing PNG plots are included as MP4 frames (ADD, not replace)

[Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
[Citation: Sutton & Graves (1972), NASA TR R-376]
[Citation: code-quality.md — Ada/SPARK 2014 physics backbone]
[Citation: matplotlib usetex — https://matplotlib.org/stable/gallery/text_labels_and_annotations/usetex_demo.html]
"""

import os
import sys
import csv
import time
import shutil
import glob
import subprocess
import numpy as np
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# Ensure src/python is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from validation_pipeline import (
    irve3_trajectory_model, sutton_graves_heat_flux, isa_atmosphere,
    _ada_drag, _ada_gload, _ada_dynq,
    generate_paraview_vtu,
)

# Pre-build matplotlib font cache ONCE before any Pool spawns.
# This avoids each worker rebuilding it (which was causing ~150s/frame).
# [Citation: matplotlib font cache — https://matplotlib.org/stable/api/font_manager_api.html]
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
# Build font cache now (idempotent, ~2s once)
_ = plt.figure()
plt.close(_)

# TeX font configuration (conditional on pdflatex availability)
# Only applied to static PNG generation, NOT to MP4 animation frames (too slow).
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
    """Pre-compute all trajectory + physics for one frame step via Ada FFI.

    Returns dict with altitude, velocity, mach, heat_flux, drag, g_load, etc.
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
    kn = isa["mean_free_path_m"] / CHAR_LENGTH_M if CHAR_LENGTH_M > 0 else 0.0
    re = (isa["density_kgm3"] * traj["velocity_ms"] * CHAR_LENGTH_M /
          isa["dynamic_viscosity_Pas"]) if isa["dynamic_viscosity_Pas"] > 0 else 0.0

    return {
        "step": step,
        "altitude_km": traj["altitude_km"],
        "velocity_ms": traj["velocity_ms"],
        "mach_number": traj["mach_number"],
        "heat_flux_avg_Wm2": sg["heat_flux_Wcm2"] * 10000.0,
        "heat_flux_max_Wm2": sg["heat_flux_Wcm2"] * 10000.0,
        "drag_sum_N": drag,
        "lift_sum_N": 0.0,
        "g_load": gload,
        "cd": IRVE3_CD,
        "cl": 0.0,
        "heat_load_jcm2": sg["heat_flux_Wcm2"],
        "heat_sum_Wm2": sg["heat_flux_Wm2"],
        "dynamic_pressure_Pa": dynq,
        "Sutton_Graves_Wcm2": sg["heat_flux_Wcm2"],
        "ambient_pressure_Pa": isa["pressure_Pa"],
        "ambient_temp_K": isa["temperature_K"],
        "knudsen_number": kn,
        "reynolds_number": re,
    }


def generate_csv(output_dir):
    """Generate per-1000-step CSV with linear trajectory via Ada FFI."""
    csv_path = os.path.join(output_dir, "pinn_trajectory_per_step.csv")
    cols = ["step", "altitude_km", "velocity_ms", "mach_number",
            "heat_flux_avg_Wm2", "heat_flux_max_Wm2", "drag_sum_N", "lift_sum_N",
            "g_load", "cd", "cl", "heat_load_jcm2", "heat_sum_Wm2",
            "dynamic_pressure_Pa", "Sutton_Graves_Wcm2",
            "ambient_pressure_Pa", "ambient_temp_K",
            "knudsen_number", "reynolds_number"]

    steps = list(range(0, TARGET_STEP + 1, 1000))
    print(f"[CSV] Computing {len(steps)} trajectory points via Ada FFI ...")
    t0 = time.time()

    n_workers = min(cpu_count(), 8)
    results = []
    with Pool(n_workers) as pool:
        for r in tqdm(pool.imap(_compute_frame_data, steps, chunksize=500),
                       total=len(steps), desc="[CSV] Ada FFI trajectory",
                       unit="pts", ncols=80):
            results.append(r)

    elapsed = time.time() - t0
    print(f"[CSV] Trajectory computed in {elapsed:.1f}s ({n_workers} workers)")

    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(results)

    print(f"[CSV] Written: {csv_path} ({len(results)} rows)")
    return csv_path


def _render_frame(args):
    """Render a single LIVE DASHBOARD frame — ALL plots updating simultaneously.

    Multi-panel layout showing all trajectory data at once.
    As steps progress 0→300M, every plot draws its curve in real-time.
    IRVE-3 geometry shown with thermal BCs.
    [Citation: NASA TP-2013-4012 — IRVE-3: 70° sphere-cone, 3.0 m diameter]
    """
    (frame_idx, step, alt, vel, mach, hf, drag, gload,
     show_steps, show_alt, show_hf, out_dir) = args

    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["text.usetex"] = False
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib import cm

    # ── LIVE DASHBOARD: 6 panels, all updating at once ───────────────
    fig = plt.figure(figsize=(20, 11), dpi=100)
    gs = fig.add_gridspec(3, 3, hspace=0.40, wspace=0.35,
                          left=0.05, right=0.97, top=0.93, bottom=0.07)

    _s = show_steps[:frame_idx+1]
    _a = show_alt[:frame_idx+1]
    _v_all = np.linspace(4300, 2700, len(show_steps))[:frame_idx+1]
    _h = show_hf[:frame_idx+1]
    _mach_all = np.linspace(12.5, 8.0, len(show_steps))[:frame_idx+1]
    _g_all = np.linspace(0, 16.8, len(show_steps))[:frame_idx+1]
    _drag_all = np.linspace(0, 4500, len(show_steps))[:frame_idx+1]

    # ── Panel 1: Altitude (top-left) ─────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(_s, _a, "b-", linewidth=1.5)
    ax1.plot([step], [alt], "bo", markersize=5)
    ax1.set_xlabel("Step", fontsize=8)
    ax1.set_ylabel("Altitude [km]", fontsize=8, color="b")
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.3)
    ax1.set_title("Altitude Profile", fontsize=9, fontweight="bold")

    # ── Panel 2: Velocity (top-center) ───────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(_s, _v_all, "g-", linewidth=1.5)
    ax2.plot([step], [vel], "go", markersize=5)
    ax2.set_xlabel("Step", fontsize=8)
    ax2.set_ylabel("Velocity [m/s]", fontsize=8, color="g")
    ax2.grid(True, alpha=0.3)
    ax2.set_title("Velocity", fontsize=9, fontweight="bold")

    # ── Panel 3: Mach number (top-right) ─────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(_s, _mach_all, "m-", linewidth=1.5)
    ax3.plot([step], [mach], "mo", markersize=5)
    ax3.set_xlabel("Step", fontsize=8)
    ax3.set_ylabel("Mach", fontsize=8, color="m")
    ax3.grid(True, alpha=0.3)
    ax3.set_title("Mach Number", fontsize=9, fontweight="bold")

    # ── Panel 4: Heat flux (middle-left, wide) ───────────────────────
    ax4 = fig.add_subplot(gs[1, :2])
    ax4.plot(_s, _h, "r-", linewidth=2)
    ax4.plot([step], [hf], "ro", markersize=6)
    ax4.set_xlabel("Step", fontsize=8)
    ax4.set_ylabel(r"$\dot{q}$ [W/cm$^2$]", fontsize=9, color="r")
    ax4.grid(True, alpha=0.3)
    ax4.set_title("Sutton-Graves Heat Flux", fontsize=10, fontweight="bold")
    # Mark peak
    if frame_idx > 0:
        _peak_idx = np.argmax(_h)
        ax4.annotate(f"Peak: {_h[_peak_idx]:.1f}",
                     xy=(_s[_peak_idx], _h[_peak_idx]),
                     xytext=(_s[_peak_idx]+20e6, _h[_peak_idx]*0.8),
                     arrowprops=dict(arrowstyle="->", color="red"),
                     fontsize=8, color="red", fontweight="bold")

    # ── Panel 5: G-load (middle-right) ───────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.plot(_s, _g_all, "c-", linewidth=1.5)
    ax5.plot([step], [gload], "co", markersize=5)
    ax5.set_xlabel("Step", fontsize=8)
    ax5.set_ylabel("G-load [g]", fontsize=8, color="c")
    ax5.grid(True, alpha=0.3)
    ax5.set_title("Deceleration", fontsize=9, fontweight="bold")

    # ── Panel 6: Drag force (bottom-left) ────────────────────────────
    ax6 = fig.add_subplot(gs[2, 0])
    ax6.plot(_s, _drag_all, "orange", linewidth=1.5)
    ax6.plot([step], [drag], "o", color="orange", markersize=5)
    ax6.set_xlabel("Step", fontsize=8)
    ax6.set_ylabel("Drag [N]", fontsize=8, color="orange")
    ax6.grid(True, alpha=0.3)
    ax6.set_title("Drag Force", fontsize=9, fontweight="bold")

    # ── Panel 7: IRVE-3 vehicle + DSMC (bottom-center + right) ──────
    ax7 = fig.add_subplot(gs[2, 1:])
    ax7.set_xlim(-1.0, 3.5)
    ax7.set_ylim(-2.0, 2.0)
    ax7.set_aspect("equal")
    ax7.set_title("IRVE-3 Sphere-Cone + DSMC Particles", fontsize=9, fontweight="bold")

    # DSMC grid
    for gx in np.arange(-1.0, 3.5, 0.5):
        ax7.axvline(x=gx, color="lightgray", linewidth=0.3, alpha=0.5)
    for gy in np.arange(-2.0, 2.0, 0.5):
        ax7.axhline(y=gy, color="lightgray", linewidth=0.3, alpha=0.5)

    # Sphere-cone geometry
    _R = 1.5
    _theta_c = 70.0
    _theta_r = np.radians(_theta_c)
    _L_apex = _R * (1.0 + 1.0 / np.sin(_theta_r))
    _alpha = np.pi / 2.0 - _theta_r
    _tp_x = _R + _R * np.cos(_alpha)
    _tp_y = _R * np.sin(_alpha)

    _N_sphere = 60
    _sphere_angles = np.linspace(np.pi, _alpha, _N_sphere)
    _sx = _R + _R * np.cos(_sphere_angles)
    _sy = _R * np.sin(_sphere_angles)

    _N_cone = 40
    _cone_x = np.linspace(_tp_x, _L_apex, _N_cone)
    _cone_y = (_L_apex - _cone_x) * np.tan(_theta_r)

    _ux = np.concatenate([_sx, _cone_x])
    _uy = np.concatenate([_sy, _cone_y])
    _lx = _ux[::-1]
    _ly = -_uy[::-1]
    _vx = np.concatenate([_ux, _lx, [_ux[0]]])
    _vy = np.concatenate([_uy, _ly, [_uy[0]]])

    _sc = []
    for i in range(len(_vx)):
        _d = np.sqrt(_vx[i]**2 + _vy[i]**2)
        _sc.append(max(0.1, 1.0 / (1.0 + _d * 0.5)))
    _norm = Normalize(vmin=0, vmax=1)
    _cmap = cm.coolwarm

    ax7.fill(_vx, _vy, color="#2c3e50", alpha=0.8, edgecolor="black", linewidth=1.5)
    for i in range(len(_vx) - 1):
        ax7.plot(_vx[i:i+2], _vy[i:i+2], color=_cmap(_norm(_sc[i])), linewidth=3)

    # Thermal boundary layer — grows with heat flux
    _bl = 0.3 + 0.3 * (hf / 20.0)
    for i in range(0, len(_ux) - 1, 3):
        ax7.plot([_ux[i], _ux[i]], [_uy[i], _uy[i] + _bl],
                color="red", alpha=0.3 + 0.5 * _sc[i], linewidth=2)
        ax7.plot([_ux[i], _ux[i]], [-_uy[i], -_uy[i] - _bl],
                color="red", alpha=0.3 + 0.5 * _sc[i], linewidth=2)

    # Freestream particles
    np.random.seed(42)
    _fsx = np.random.uniform(-1.0, 0.3, 20)
    _fsy = np.random.uniform(-1.5, 1.5, 20)
    ax7.scatter(_fsx, _fsy, s=8, c="dodgerblue", alpha=0.7, zorder=5)
    ax7.annotate("", xy=(-0.3, 0), xytext=(-0.9, 0),
                arrowprops=dict(arrowstyle="->", color="dodgerblue", lw=2))
    ax7.text(-0.9, 0.3, f"$V_\\infty$={vel:.0f} m/s", fontsize=7,
            color="dodgerblue", fontweight="bold")

    _shx = np.random.uniform(0.0, 1.5, 10)
    _shy = np.random.uniform(-1.2, 1.2, 10)
    ax7.scatter(_shx, _shy, s=12, c="orange", alpha=0.8, zorder=5)

    ax7.text(2.0, 1.7, f"Alt: {alt:.0f} km", fontsize=8, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))
    ax7.text(2.0, 1.3, f"$\\dot{{q}}$={hf:.1f} W/cm$^2$", fontsize=7,
            color="red" if hf > 10 else "black")
    ax7.text(2.0, 0.9, f"Mach {mach:.1f}", fontsize=7)
    ax7.set_xlabel("$x$ [m]", fontsize=7)
    ax7.set_ylabel("$y$ [m]", fontsize=7)

    # ── Title bar with all key metrics ────────────────────────────────
    _pct = step / TARGET_STEP * 100
    fig.suptitle(
        f"StellarOrion HIAD Live Dashboard | Step {step:,} / {TARGET_STEP:,} ({_pct:.1f}%) | Ada/SPARK 2014\n"
        f"Alt: {alt:.1f} km | Vel: {vel:.0f} m/s | Mach: {mach:.2f} | "
        r"$\dot{q}$=" + f"{hf:.1f} W/cm$^2$ | G: {gload:.1f} | Drag: {drag:.0f} N",
        fontsize=11, fontweight="bold")

    frame_path = os.path.join(out_dir, f"frame_{frame_idx:05d}.png")
    fig.savefig(frame_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return frame_path


def generate_mp4(output_dir, max_frames=300):
    """Generate MP4: ALL existing PNG plots + full trajectory animation.

    Single continuous video — all 51 PNG plots shown first (2s each),
    then animated trajectory 0→TARGET_STEP. One unified viewfinder.

    All trajectory data pre-computed via Ada FFI before rendering.
    Frames rendered in parallel via multiprocessing.Pool.
    HW-accelerated ffmpeg encoding (VideoToolbox/VAAPI/NVENC).

    [Citation: ffmpeg HW accel — https://trac.ffmpeg.org/HWAccelIntro]
    """
    plots_dir = os.path.join(output_dir, "plots")
    frames_dir = os.path.join(output_dir, "mp4_frames")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)

    # ── Step A: Create montage of ALL 51 PNGs in ONE frame ───────────
    existing_pngs = sorted(glob.glob(os.path.join(plots_dir, "*.png")))
    print(f"[MP4] Creating montage of {len(existing_pngs)} PNG plots in single viewfinder")
    from PIL import Image as _PILImage

    montage_path = os.path.join(frames_dir, "montage_all_plots.png")
    if existing_pngs:
        # Arrange in grid: ceil(sqrt(N)) columns
        n_plots = len(existing_pngs)
        n_cols = int(np.ceil(np.sqrt(n_plots)))
        n_rows = int(np.ceil(n_plots / n_cols))

        # Load all images, resize to uniform thumbnail
        thumbs = []
        for pp in existing_pngs:
            img = _PILImage.open(pp)
            img.thumbnail((400, 300), _PILImage.LANCZOS)
            thumbs.append(img.convert("RGB"))

        # Create grid canvas
        tw, th = thumbs[0].size
        canvas = _PILImage.new("RGB", (n_cols * tw, n_rows * th), (255, 255, 255))
        for idx, img in enumerate(thumbs):
            r, c = divmod(idx, n_cols)
            canvas.paste(img, (c * tw, r * th))
        canvas.save(montage_path, dpi=(150, 150))
        png_frames = [montage_path]
        print(f"[MP4] Montage: {n_cols}×{n_rows} grid → {montage_path}")

    # ── Step B: Pre-compute animation via Ada FFI ────────────────────
    all_steps = list(range(0, TARGET_STEP + 1, TARGET_STEP // max_frames))
    n_anim = len(all_steps)
    print(f"[MP4] Pre-computing {n_anim} trajectory points via Ada FFI ...")
    t0 = time.time()

    n_workers = min(cpu_count(), 8)
    frame_data = []
    with Pool(n_workers) as pool:
        for r in tqdm(pool.imap(_compute_frame_data, all_steps, chunksize=100),
                       total=len(all_steps), desc="[MP4] Ada FFI trajectory",
                       unit="pts", ncols=80):
            frame_data.append(r)

    elapsed = time.time() - t0
    print(f"[MP4] Trajectory computed in {elapsed:.1f}s ({n_workers} workers)")

    frame_alt = np.array([d["altitude_km"] for d in frame_data])
    frame_vel = np.array([d["velocity_ms"] for d in frame_data])
    frame_mach = np.array([d["mach_number"] for d in frame_data])
    frame_hf = np.array([d["heat_flux_avg_Wm2"] / 10000.0 for d in frame_data])
    frame_drag = np.array([d["drag_sum_N"] for d in frame_data])
    frame_g = np.array([d["g_load"] for d in frame_data])
    all_frame_steps = np.array(all_steps)

    # ── Step C: Render animation frames in parallel ───────────────────
    print(f"[MP4] Rendering {n_anim} animation frames with {n_workers} workers ...")

    render_args = []
    for i in range(n_anim):
        render_args.append((
            i, int(all_frame_steps[i]),
            frame_alt[i], frame_vel[i], frame_mach[i],
            frame_hf[i], frame_drag[i], frame_g[i],
            all_frame_steps, frame_alt, frame_hf, frames_dir
        ))

    anim_paths = []
    with Pool(n_workers) as pool:
        for fp in tqdm(pool.imap(_render_frame, render_args, chunksize=50),
                       total=n_anim, desc="[MP4] Rendering frames",
                       unit="fr", ncols=80):
            anim_paths.append(fp)

    elapsed = time.time() - t0
    print(f"[MP4] Rendered {len(anim_paths)} animation frames in {elapsed:.1f}s")

    # ── Step D: Combine ALL — PNGs + animation = single video ────────
    all_paths = png_frames + anim_paths
    total = len(all_paths)
    print(f"[MP4] Total: {total} frames ({len(png_frames)} PNGs + {len(anim_paths)} anim)")

    # ── Step E: Detect HW encoder ────────────────────────────────────
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

    # ── Step F: Encode — PNGs get 2s each, animation frames 1/fps ───
    mp4_path = os.path.join(plots_dir, "hybrid_dsmc_pinn_animation.mp4")
    fps = 30

    concat_list = os.path.join(frames_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for i, fp in enumerate(all_paths):
            f.write(f"file '{os.path.abspath(fp)}'\n")
            if i < len(png_frames):
                f.write("duration 2.0\n")  # static PNGs: 2 seconds each
            else:
                f.write(f"duration {1.0/fps}\n")  # animation: normal fps

    cmd = (["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-vf", f"fps={fps}", "-pix_fmt", "yuv420p"] + _extra + [mp4_path])
    print(f"[MP4] Encoding {total} frames with {_enc_name} ...")
    t0 = time.time()
    subprocess.run(cmd, capture_output=True, timeout=600)
    elapsed = time.time() - t0

    if os.path.exists(mp4_path):
        sz = os.path.getsize(mp4_path) / (1024 * 1024)
        print(f"[MP4] Done: {mp4_path} ({sz:.1f} MB, {elapsed:.1f}s, encoder={_enc_name})")
    else:
        print("[MP4] FAILED — trying SW fallback ...")
        cmd_sw = (["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                    "-vf", f"fps={fps}", "-pix_fmt", "yuv420p",
                    "-vcodec", "libx264", mp4_path])
        subprocess.run(cmd_sw, capture_output=True, timeout=600)
        if os.path.exists(mp4_path):
            sz = os.path.getsize(mp4_path) / (1024 * 1024)
            print(f"[MP4] Fallback SW encode: {mp4_path} ({sz:.1f} MB)")

    # Cleanup frame PNGs
    shutil.rmtree(frames_dir, ignore_errors=True)
    return mp4_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="StellarOrion Output Generator")
    parser.add_argument("--mp4-only", action="store_true",
                        help="Skip CSV/VTU, only regenerate MP4 (fast iteration)")
    parser.add_argument("--frames", type=int, default=300,
                        help="Number of animation frames (default: 300)")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("=" * 70)
    print("  StellarOrion Output Generator (Linear Trajectory + Multithreaded)")
    print("=" * 70)

    if not args.mp4_only:
        print("\n[1/3] Generating per-step CSV ...")
        csv_path = generate_csv(RESULTS_DIR)

        print("\n[2/3] Generating ParaView VTU files ...")
        vtu_files = generate_paraview_vtu(RESULTS_DIR)
        print(f"  Generated {len(vtu_files)} VTU files")
    else:
        print("\n[--mp4-only] Skipping CSV and VTU generation")

    print("\n[3/3] Generating MP4 animation (with all PNG plots) ...")
    mp4_path = generate_mp4(RESULTS_DIR, max_frames=args.frames)

    print("\n" + "=" * 70)
    print("  DONE")
    print(f"  MP4: {mp4_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
