#!/usr/bin/env python3
"""
================================================================================
MODULE: hiad_geometry.py — Shared HIAD Cross-Section Generator (Pure NumPy)
================================================================================

Single source of truth for the HIAD 4-segment cross-section profile in Python.
Moved out of generate_optimized_overlay.py so that scripts/ renderers can
import the geometry WITHOUT triggering ada_pinn_wrapper's module-level
ctypes.CDLL load of libstellarorion_pinn.dylib (which raises OSError when the
dylib is absent).

AXIOMS:
  A1: The HIAD profile is fully parameterized by (R_N, r_tor, half_cone_deg).
  A2: The Python formulas EXACTLY mirror Ada/SPARK Get_HIAD_Cross_Section
      in stellarorion_pinn_trajectory.adb (line-for-line).
  A3: This module must NEVER import ada_pinn_wrapper (no dylib dependency).

THEORIES:
  T1: From A1+A2: any consumer needing a cross-section should call this
      function rather than re-deriving the 4-segment math (no copy-paste).
  T2: From A3: a pure-numpy module is importable headless / CI / dylib-free.

APPLICATIONS:
  Consumed by generate_optimized_overlay.py (MP4 dashboard) and
  scripts/render_geometry_grid.py (87-panel BO geometry grid).

CITATIONS:
  [1] stellarorion_pinn_trajectory.adb lines 393-479 — Get_HIAD_Cross_Section
  [2] Rapisarda (2023) Sec 3.7 — HIAD 4-segment flat-skin profile
  [3] numpy 2.x docs — https://numpy.org/doc/stable/reference/

Author: Albert Starfield Wahyu Suryo Samudro
"""

import numpy as np

# Number of stacked tori in the IRVE-3 HIAD baseline.
# [Citation: stellarorion_pinn_trajectory.adb line 40 — N_Tori]
N_TORI = 6


def generate_cross_section(R_N, r_tor, half_cone_deg, n_per_segment=15):
    """Generate the HIAD meridian cross-section from geometry parameters.

    EXACT copy of Ada/SPARK stellarorion_pinn_trajectory.adb
    Get_HIAD_Cross_Section. All formulas match the Ada body line-for-line.

    Parameters:
        R_N            -- nose sphere radius [m] (> 0)
        r_tor          -- torus minor radius [m] (> 0)
        half_cone_deg  -- half-cone angle [degrees] (0, 90)
        n_per_segment  -- sample points per each of the 4 segments (>= 2)

    Returns:
        (x_pts, y_pts) -- numpy float arrays; x = axial (PZ), y = radial (PR)

    Raises:
        ValueError -- n_per_segment < 2 (segment sampling requires >= 2 pts)
        ValueError -- non-positive R_N / r_tor, or half_cone outside (0, 90)

    Safety fallback:
        Non-physical inputs raise loudly instead of emitting a silently
        degenerate profile (Murphy: bad bounds WILL occur in BO corners).
    """
    if n_per_segment < 2:
        raise ValueError(
            f"n_per_segment must be >= 2, got {n_per_segment}"
        )
    if R_N <= 0.0 or r_tor <= 0.0:
        raise ValueError(
            f"R_N and r_tor must be > 0, got R_N={R_N}, r_tor={r_tor}"
        )
    if not (0.0 < half_cone_deg < 90.0):
        raise ValueError(
            f"half_cone_deg must be in (0, 90), got {half_cone_deg}"
        )

    pi = np.pi
    # Ada uses Gamma_Rad = (90 - Half_Cone_Deg) * Pi / 180 (the complement
    # angle). [Citation: stellarorion_pinn_trajectory.adb line 393]
    gamma = np.radians(90.0 - half_cone_deg)
    tan_g = np.tan(gamma)

    # Tangency point (same as Ada: R_Tang = R_N * Cos_Rad(Gamma_Rad))
    # [Citation: stellarorion_pinn_trajectory.adb lines 397-398]
    R_tang = R_N * np.cos(gamma)
    Z_tang = R_N * (1.0 - np.sin(gamma))

    # Conical shell max axial length
    S_max = (2 * N_TORI - 1) * r_tor
    R_target = R_tang + S_max * np.cos(gamma)

    # Toroid outer center (same as Ada lines 393-394)
    R_C_out = R_target - r_tor * np.sin(gamma)
    Z_C_out = (Z_tang + S_max * np.sin(gamma)) + r_tor * np.cos(gamma)
    Z_back = Z_C_out + r_tor

    x_pts = []  # axial (PZ in Ada)
    y_pts = []  # radial (PR in Ada)

    # Segment 1: Nose Arc (theta: -Pi/2 to -gamma)
    # Ada: PR = R_N * Cos_Rad(Alpha), PZ = R_N + R_N * Sin_Rad(Alpha)
    # [Citation: stellarorion_pinn_trajectory.adb lines 429-440]
    for i in range(n_per_segment):
        t = i / (n_per_segment - 1)
        alpha = (-pi / 2.0) * (1.0 - t) + (-gamma) * t
        pr = R_N * np.cos(alpha)           # radial
        pz = R_N + R_N * np.sin(alpha)     # axial
        x_pts.append(max(0.0, pz))
        y_pts.append(max(0.0, pr))

    # Segment 2: Windward Straight (conical shell)
    # Ada: R = R_Tang + T * (R_Target - R_Tang), Z = Z_Tang + (R - R_Tang)*tan(gamma)
    # [Citation: stellarorion_pinn_trajectory.adb lines 444-453]
    for i in range(1, n_per_segment):
        t = i / (n_per_segment - 1)
        r = R_tang + t * (R_target - R_tang)
        z = Z_tang + (r - R_tang) * tan_g
        x_pts.append(z)
        y_pts.append(r)

    # Segment 3: Toroid Wrap (theta: -gamma to Pi/2)
    # Ada: PR = R_C_Out + r_tor * Cos_Rad(Theta), PZ = Z_C_Out + r_tor * Sin_Rad(Theta)
    # [Citation: stellarorion_pinn_trajectory.adb lines 457-468]
    for i in range(1, n_per_segment):
        t = i / (n_per_segment - 1)
        theta = (-gamma) * (1.0 - t) + (pi / 2.0) * t
        pr = R_C_out + r_tor * np.cos(theta)   # radial
        pz = Z_C_out + r_tor * np.sin(theta)   # axial
        x_pts.append(pz)
        y_pts.append(pr)

    # Segment 4: Flat Back (r from R_C_Out to 0, z = Z_Back)
    # Ada: R = R_C_Out * (1.0 - T), Z = Z_Back
    # [Citation: stellarorion_pinn_trajectory.adb lines 471-478]
    for i in range(1, n_per_segment):
        t = i / (n_per_segment - 1)
        r = R_C_out * (1.0 - t)
        z = Z_back
        x_pts.append(z)
        y_pts.append(r)

    return np.array(x_pts), np.array(y_pts)
