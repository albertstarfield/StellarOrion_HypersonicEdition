#!/usr/bin/env python3
"""
================================================================================
SCRIPT: render_optimization_comparison.py — Before/After 3D HIAD Comparison
================================================================================

Generates side-by-side 3D renders of the default (IRVE-3 baseline) and
Bayesian-optimized HIAD geometries.

GEOMETRY SOURCE:
  - Default: Ada FFI get_hiad_cross_section() — single source of truth
  - Optimized: 4-segment Rapisarda profile computed in Python (same math as Ada)

Both profiles are revolved around the axis to create 3D surfaces.

HIAD CONSTRUCTION FEATURES:
  1. Stacked torus ridges — concentric donut-shaped rings visible on surface
  2. Flat disc proportions — inflatable portion nearly flat (8-10:1 dia:height)
  3. Central payload drum — cylindrical section rising from disc center
  4. Radial gore pattern — spoke-like segments dividing the tori

CITATIONS:
  [1] NASA LOFTID mission (2022) — 6m HIAD flight demonstration
  [2] IRVE-3 mission (2012) — 3m HIAD suborbital test
  [3] Rapisarda (2023) Sec 3.7 — HIAD flat-skin profile (4-segment)
  [4] do Carmo (1976) — Surface of revolution mathematics
  [5] stellarorion_sparta.adb Generate_HIAD_Surf (line 1913) — Ada geometry engine
"""

import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# FFI: Get default geometry from Ada/SPARK
# ---------------------------------------------------------------------------

def get_ada_default_profile():
    """Get the default HIAD cross-section from Ada FFI.

    Returns (x_list, y_list) where x=axial, y=radial.
    All geometry math is in Ada/SPARK; Python is a thin wrapper.

    [Citation: ada_pinn_wrapper.py get_hiad_cross_section]
    [Citation: stellarorion_pinn_trajectory.ads — Get_HIAD_Cross_Section]
    """
    # Add parent src/python to path for import
    script_dir = Path(__file__).resolve().parent
    src_python = script_dir.parent / "src" / "python"
    sys.path.insert(0, str(src_python))

    from ada_pinn_wrapper import get_hiad_cross_section
    result = get_hiad_cross_section()
    return result["x"], result["y"], result["n"]


# ---------------------------------------------------------------------------
# Python 4-segment Rapisarda profile (same math as Ada Generate_HIAD_Surf)
# ---------------------------------------------------------------------------

def compute_rapisarda_profile(
    rn: float = 1.5,
    half_cone_deg: float = 60.0,
    r_tor: float = 0.135,
    n_tori: int = 6,
    n_seg: int = 20,
):
    """Compute the 4-segment HIAD flat-skin cross-section.

    Exact replica of Ada Generate_HIAD_Surf (stellarorion_sparta.adb line 1913).
    Used for optimized geometry where Ada globals can't be changed via FFI.

    AXIOMS (from Ada code lines 1947-1984):
      Gamma_Rad = (90 - angle) * Pi / 180
      R_Tang = R_N * Cos(Gamma)
      Z_Tang = R_N * (1 - Sin(Gamma))
      S_Last = (2*N - 1) * r_tor
      R_Target = R_Tang + S_Last * Cos(Gamma)
      Z_Out = Z_Tang + S_Last * Sin(Gamma)
      R_C_Out = R_Target - r_tor * Sin(Gamma)
      Z_C_Out = Z_Out + r_tor * Cos(Gamma)
      Z_Back = Z_C_Out + r_tor

    Segments:
      1. Nose arc: alpha [-Pi/2 -> -Gamma], R = R_N*cos(a), Z = R_N + R_N*sin(a)
      2. Windward straight: R [R_Tang -> R_Target], Z = Z_Tang + (R - R_Tang)*tan(G)
      3. Toroid wrap: theta [-Gamma -> Pi/2], R = R_C_Out + r_tor*cos(t), Z = Z_C_Out + r_tor*sin(t)
      4. Flat back: Z = Z_Back constant, R [R_C_Out+r_tor -> 0]

    [Citation: Rapisarda (2023) Sec 3.7, Appendix C.1]
    [Citation: stellarorion_sparta.adb Generate_HIAD_Surf lines 1913-2112]
    """
    # Derived geometric parameters (matching Ada exactly)
    gamma_rad = (90.0 - half_cone_deg) * math.pi / 180.0
    sin_g = math.sin(gamma_rad)
    cos_g = math.cos(gamma_rad)
    tan_g = sin_g / cos_g

    # Tangency point
    r_tang = rn * cos_g
    z_tang = rn * (1.0 - sin_g)

    # Outermost toroid reach
    s_last = float(2 * n_tori - 1) * r_tor
    r_target = r_tang + s_last * cos_g
    z_out = z_tang + s_last * sin_g

    # Center of outermost toroid
    r_c_out = r_target - r_tor * sin_g
    z_c_out = z_out + r_tor * cos_g
    z_back = z_c_out + r_tor

    # Segment 1: Nose arc (20 points)
    seg1_r, seg1_z = [], []
    for i in range(n_seg):
        t = i / (n_seg - 1)
        alpha = (-math.pi / 2.0) * (1.0 - t) + (-gamma_rad) * t
        seg1_r.append(rn * math.cos(alpha))
        seg1_z.append(rn + rn * math.sin(alpha))

    # Segment 2: Windward straight (19 points, skip first duplicate)
    seg2_r, seg2_z = [], []
    for i in range(1, n_seg):
        t = i / (n_seg - 1)
        r = r_tang + t * (r_target - r_tang)
        z = z_tang + (r - r_tang) * tan_g
        seg2_r.append(r)
        seg2_z.append(z)

    # Segment 3: Toroid wrap (19 points, skip first duplicate)
    seg3_r, seg3_z = [], []
    for i in range(1, n_seg):
        t = i / (n_seg - 1)
        theta = -gamma_rad + t * (math.pi / 2.0 - (-gamma_rad))
        seg3_r.append(r_c_out + r_tor * math.cos(theta))
        seg3_z.append(z_c_out + r_tor * math.sin(theta))

    # Segment 4: Flat back (19 points, skip first duplicate)
    # [Citation: stellarorion_sparta.adb line 2137: R := R_C_Out * (1.0 - T)]
    seg4_r, seg4_z = [], []
    r_start = r_c_out  # Ada uses R_C_Out, NOT R_C_Out + r_tor
    for i in range(1, n_seg):
        t = i / (n_seg - 1)
        seg4_r.append(r_start * (1.0 - t))
        seg4_z.append(z_back)

    # Concatenate all segments (R, Z) -> (x=Z, y=R) for FFI format
    r_all = seg1_r + seg2_r + seg3_r + seg4_r
    z_all = seg1_z + seg2_z + seg3_z + seg4_z

    # Return as (x=axial, y=radial) to match FFI format
    return z_all, r_all


# ---------------------------------------------------------------------------
# 3D mesh generation: revolve profile around axis
# ---------------------------------------------------------------------------

def revolve_profile(x_list, y_list, n_az=60):
    """Revolve a 2D (x, y) profile around the X-axis to create a 3D surface.

    The profile is in the (x, y) plane where x=axial, y=radial.
    Revolving around X-axis gives: for each (x_i, y_i),
      surface point at angle theta: (x_i, y_i*cos(theta), y_i*sin(theta))

    [Citation: do Carmo (1976) — Surface of revolution]
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
# HIAD visual features
# ---------------------------------------------------------------------------

def mesh_torus(cx, cy, cz, major_r, minor_r, n_major=60, n_minor=20):
    """Generate a torus mesh centered at (cx, cy, cz).

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
            X[i, j] = cx + r * cos_u
            Y[i, j] = cy + r * sin_u
            Z[i, j] = cz + minor_r * sin_v
    return X, Y, Z


def mesh_cylinder(cx, cy, z_bottom, z_top, radius, n_az=60, n_z=10):
    """Generate a cylinder mesh for the central payload drum."""
    import numpy as np
    X = np.zeros((n_az, n_z + 1))
    Y = np.zeros((n_az, n_z + 1))
    Z = np.zeros((n_az, n_z + 1))
    for i in range(n_az):
        theta = 2 * math.pi * i / n_az
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(n_z + 1):
            t = j / n_z
            X[i, j] = cx + radius * cos_t
            Y[i, j] = cy + radius * sin_t
            Z[i, j] = z_bottom + t * (z_top - z_bottom)
    return X, Y, Z


def mesh_dome(cx, cy, cz, radius, height, n_r=40, n_az=60):
    """Generate a dome (hemisphere-like) mesh for the nose cap."""
    import numpy as np
    X = np.zeros((n_az, n_r + 1))
    Y = np.zeros((n_az, n_r + 1))
    Z = np.zeros((n_az, n_r + 1))
    for i in range(n_az):
        theta = 2 * math.pi * i / n_az
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(n_r + 1):
            t = j / n_r
            z = cz + height * t
            r = radius * math.sqrt(max(0, 1 - t * t))
            X[i, j] = cx + r * cos_t
            Y[i, j] = cy + r * sin_t
            Z[i, j] = z
    return X, Y, Z


def mesh_gore_spokes(cx, cy, cz, r_inner, r_outer, z_inner, z_outer,
                     num_spokes=24, spoke_width=0.02, n_pts=20):
    """Generate radial spoke/gore line meshes for visual effect."""
    import numpy as np
    meshes = []
    for k in range(num_spokes):
        theta = 2 * math.pi * k / num_spokes
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        cos_p, sin_p = math.cos(theta + math.pi/2), math.sin(theta + math.pi/2)
        X = np.zeros((2, n_pts + 1))
        Y = np.zeros((2, n_pts + 1))
        Z = np.zeros((2, n_pts + 1))
        for side_idx, side in enumerate([-1, 1]):
            for i in range(n_pts + 1):
                t = i / n_pts
                r = r_inner + t * (r_outer - r_inner)
                z = z_inner + t * (z_outer - z_inner)
                offset = side * spoke_width / 2
                X[side_idx, i] = cx + r * cos_t + offset * cos_p
                Y[side_idx, i] = cy + r * sin_t + offset * sin_p
                Z[side_idx, i] = z
        meshes.append((X, Y, Z))
    return meshes


def mesh_flat_back(cx, cy, z_back, radius, n_r=20, n_az=60):
    """Generate a flat circular back plate mesh."""
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
            X[i, j] = cx + r * cos_t
            Y[i, j] = cy + r * sin_t
            Z[i, j] = z_back
    return X, Y, Z


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------

def render_hiad(ax, x_profile, y_profile, color_base, label_color,
                half_cone_deg, r_tor, cd_value, rn, is_optimized=False):
    """Render a HIAD from an Ada-generated profile + visual features.

    Parameters:
      ax            — matplotlib 3D axis
      x_profile     — axial coordinates from Ada/profile
      y_profile     — radial coordinates from Ada/profile
      color_base    — base color for tori gradient
      label_color   — color for text labels
      half_cone_deg — half-cone angle (for torus placement and drum_r)
      r_tor         — torus minor radius (for torus ridges)
      cd_value      — drag coefficient value to display
      rn            — nose sphere radius (for computing drum_r)
      is_optimized  — True for optimized variant
    """
    import numpy as np

    # 1. Main envelope: revolve the Ada/profile around axis
    X_env, Y_env, Z_env = revolve_profile(x_profile, y_profile, n_az=60)
    # Convert int tuple (0-255) to matplotlib hex color
    if isinstance(color_base, tuple) and len(color_base) == 3:
        color_hex = '#{:02x}{:02x}{:02x}'.format(*color_base)
    else:
        color_hex = color_base
    ax.plot_surface(X_env, Y_env, Z_env,
                    color=color_hex, alpha=0.85, edgecolor='none', shade=True)

    # 2. Extract key dimensions from profile
    r_max = max(y_profile)
    x_max = max(x_profile)
    # Drum radius = tangent point radius R_Tang = R_N * cos(gamma)
    # [Citation: stellarorion_sparta.adb line 1965: R_Tang := R_N * Cos_G]
    gamma_rad = (90.0 - half_cone_deg) * math.pi / 180.0
    drum_r = rn * math.cos(gamma_rad)

    # 3. Central payload drum
    drum_height = drum_r * 0.35  # Short cylinder per IRVE-3 proportions
    X_drum, Y_drum, Z_drum = mesh_cylinder(0, 0, 0, drum_height, drum_r)
    ax.plot_surface(X_drum, Y_drum, Z_drum,
                    color='#555555', alpha=0.9, edgecolor='none', shade=True)

    # 4. Nose cap dome (hemisphere on top of drum)
    X_nose, Y_nose, Z_nose = mesh_dome(0, 0, drum_height, drum_r * 0.6, drum_r * 0.3)
    ax.plot_surface(X_nose, Y_nose, Z_nose,
                    color='#e94560', alpha=0.95, edgecolor='none', shade=True)

    # 5. Stacked torus ridges (visual indicator of inflatable structure)
    # Place tori at evenly spaced radial positions along the profile
    n_tori = 6
    for idx in range(n_tori):
        t = (idx + 0.5) / n_tori
        # Find the profile point closest to this radial position
        target_r = drum_r + t * (r_max - drum_r)
        # Find corresponding x from profile
        profile_idx = min(range(len(y_profile)), key=lambda i: abs(y_profile[i] - target_r))
        z_center = x_profile[profile_idx]
        r_center = y_profile[profile_idx]

        if r_center < drum_r + r_tor:
            continue

        # Color gradient
        frac = idx / max(1, n_tori - 1)
        r_c = int(color_base[0] * 0.7 + frac * 40)
        g_c = int(color_base[1] * 0.7 + frac * 20)
        b_c = int(color_base[2] * 0.7 + frac * 30)
        torus_color = f'#{min(255,r_c):02x}{min(255,g_c):02x}{min(255,b_c):02x}'

        X_t, Y_t, Z_t = mesh_torus(0, 0, z_center, r_center, r_tor * 0.6,
                                     n_major=60, n_minor=12)
        ax.plot_surface(X_t, Y_t, Z_t,
                        color=torus_color, alpha=0.92, edgecolor='none', shade=True)

    # 6. Gore spokes (radial lines from drum to outer edge)
    z_outer = x_profile[-1] if x_profile[-1] > x_profile[-2] else x_max
    gore_meshes = mesh_gore_spokes(
        0, 0, 0, drum_r * 0.6, r_max, drum_height, z_outer,
        num_spokes=24, spoke_width=0.03
    )
    for X_g, Y_g, Z_g in gore_meshes:
        ax.plot_surface(X_g, Y_g, Z_g,
                        color='#333333', alpha=0.4, edgecolor='none')

    # 7. Flat back plate
    X_back, Y_back, Z_back = mesh_flat_back(0, 0, z_outer, r_max)
    ax.plot_surface(X_back, Y_back, Z_back,
                    color='#222222', alpha=0.7, edgecolor='none', shade=True)


def main() -> int:
    """Generate comparison renders using Ada FFI for default geometry."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # --- Get default profile from Ada FFI ---
    print("Loading default HIAD profile from Ada FFI...")
    x_def, y_def, n_def = get_ada_default_profile()
    print(f"  Ada returned {n_def} points, x=[{min(x_def):.4f}, {max(x_def):.4f}], "
          f"y=[{min(y_def):.4f}, {max(y_def):.4f}]")

    # --- Compute optimized profile (same math as Ada, different params) ---
    # Optimized params from Bayesian optimization: R_N=1.1146, r_tor=0.0539, half_cone=44.58
    print("Computing optimized HIAD profile...")
    x_opt, y_opt = compute_rapisarda_profile(
        rn=1.1146, half_cone_deg=44.58, r_tor=0.0539, n_tori=6
    )
    print(f"  Computed {len(x_opt)} points, x=[{min(x_opt):.4f}, {max(x_opt):.4f}], "
          f"y=[{min(y_opt):.4f}, {max(y_opt):.4f}]")

    # --- Create figure ---
    fig = plt.figure(figsize=(16, 8), facecolor='#0a0a0f')

    # Default (left) — blue tones
    ax1 = fig.add_subplot(121, projection='3d', facecolor='#0a0a0f')
    render_hiad(ax1, x_def, y_def,
                color_base=(26, 82, 128), label_color='#8892b0',
                half_cone_deg=60.0, r_tor=0.135, cd_value=1.6073, rn=1.5)
    ax1.set_title('BEFORE (IRVE-3 Default — Ada FFI)', color='#8892b0', fontsize=12,
                  fontweight='bold', pad=10)
    ax1.set_xlabel('X (axial) [m]', color='#8892b0', fontsize=8)
    ax1.set_ylabel('Y [m]', color='#8892b0', fontsize=8)
    ax1.set_zlabel('Z [m]', color='#8892b0', fontsize=8)
    ax1.tick_params(colors='#555555', labelsize=6)
    ax1.view_init(elev=25, azim=45)
    ax1.set_box_aspect([1, 1, 0.3])
    ax1.text2D(0.02, 0.02,
        'R_N=1.50m  half_cone=60.0\nr_tor=0.135m  6 tori\nCd=1.6073\nSource: Ada FFI',
        transform=ax1.transAxes, color='#8892b0', fontsize=8,
        verticalalignment='bottom',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#0f3460'))

    # Optimized (right) — red tones
    ax2 = fig.add_subplot(122, projection='3d', facecolor='#0a0a0f')
    render_hiad(ax2, x_opt, y_opt,
                color_base=(192, 57, 43), label_color='#e94560',
                half_cone_deg=44.58, r_tor=0.054, cd_value=1.4554, rn=1.1146,
                is_optimized=True)
    ax2.set_title('AFTER (Optimized — Bayesian)', color='#e94560', fontsize=12,
                  fontweight='bold', pad=10)
    ax2.set_xlabel('X (axial) [m]', color='#8892b0', fontsize=8)
    ax2.set_ylabel('Y [m]', color='#8892b0', fontsize=8)
    ax2.set_zlabel('Z [m]', color='#8892b0', fontsize=8)
    ax2.tick_params(colors='#555555', labelsize=6)
    ax2.view_init(elev=25, azim=45)
    ax2.set_box_aspect([1, 1, 0.3])
    ax2.text2D(0.02, 0.02,
        'R_N=1.11m  half_cone=44.6\nr_tor=0.054m  6 tori\nCd=1.4554\nSource: Python profile',
        transform=ax2.transAxes, color='#e94560', fontsize=8,
        verticalalignment='bottom',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#e94560'))

    # Same axis limits for fair comparison
    lim = 1.8
    for ax in [ax1, ax2]:
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_zlim(0, 1.5)

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
                 'Default geometry from Ada FFI | Optimized from Bayesian search',
        color='white', fontsize=14, fontweight='bold', y=0.97)

    plt.tight_layout(rect=[0, 0.05, 1, 0.93])
    out = Path(__file__).resolve().parent.parent / "optimization_comparison.png"
    plt.savefig(str(out), dpi=150, facecolor='#0a0a0f', bbox_inches='tight')
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
