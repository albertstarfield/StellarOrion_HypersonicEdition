#!/usr/bin/env python3
"""
StellarOrion ParaView Pipeline Demo
====================================
Demonstrates the full visualization pipeline with STUB simulation data.

Pipeline:
  1. Generate synthetic SPARTA grid dumps (mock DSMC at 52km, Mach 10)
  2. Export to VTU (2D unstructured grid) and VTP (3D revolved surface)
  3. Generate ParaView state script with HIAD STL geometry
  4. Launch ParaView with the complete pipeline

Axioms:
  - SPARTA grid dump format: ITEM: CELLS header + [id xlo ylo xhi yhi n u v w temp nrho ...]
  - DSMC cell-averaged storage (Bird, 1994)
  - Freestream conditions: 52km altitude, V=2700 m/s, T=270K, n=3.47e21 /m³
  - Sutton-Graves stagnation heating: q ∝ ρ^0.5 * V^3 (Sutton & Graves, 1971)

Usage:
  python3 demo_paraview_pipeline.py
"""

import os
import sys
import numpy as np
import shutil

# ── Configuration ──────────────────────────────────────────────────────────
DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_paraview_output")
STL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HIAD_custom.stl")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "source"))

# Freestream conditions (52km altitude, US Standard Atmosphere)
V_INF = 2700.0       # m/s (Mach ~10 at 52km)
T_INF = 270.0        # K (freestream temperature)
N_RHO = 3.47e21      # /m³ (number density)
T_STAGNATION = 5580.0  # K (stagnation temperature from energy balance)

# Grid dimensions (axisymmetric: z = axial, r = radial)
N_Z = 60             # axial cells
N_R = 30             # radial cells
Z_MIN, Z_MAX = -2.0, 2.0   # meters (axial extent)
R_MIN, R_MAX = 0.0, 1.8    # meters (radial extent, symmetric about r=0)


def generate_synthetic_grid_dump(output_path, timestep=1):
    """Generate a synthetic SPARTA grid dump with physically realistic stub data.

    Creates a 2D axisymmetric grid representing the shock layer around a HIAD
    at 52km altitude, Mach 10. Temperature peaks at the stagnation point
    (leading edge) and decays downstream, consistent with hypersonic bow shock
    physics (Anderson, 2006).

    Parameters
    ----------
    output_path : str
        Path to write the grid.X.out file.
    timestep : int
        Timestep number for the filename.

    Returns
    -------
    str
        Path to the written file.
    """
    dz = (Z_MAX - Z_MIN) / N_Z
    dr = (R_MAX - R_MIN) / N_R

    lines = [
        f"ITEM: TIMESTEP\n{timestep}",
        f"ITEM: NUMBER OF CELLS\n{N_Z * N_R}",
        f"ITEM: CELLS\n"
    ]

    cell_id = 0
    for iz in range(N_Z):
        for ir in range(N_R):
            cell_id += 1
            zlo = Z_MIN + iz * dz
            zhi = zlo + dz
            rlo = R_MIN + ir * dr
            rhi = rlo + dr
            r_mid = (rlo + rhi) / 2.0
            z_mid = (zlo + zhi) / 2.0

            # ── Physics-based stub data ──
            # Stagnation point is at z ≈ -1.5 (nose of HIAD), r ≈ 0
            # Shock layer: high T near stagnation, decays downstream
            z_stag = -1.5  # stagnation point location
            r_nose = 0.55  # nose radius

            # Distance from stagnation point (normalized)
            dist = np.sqrt((z_mid - z_stag)**2 + r_mid**2)
            dist_norm = dist / 2.0  # normalize to ~1.0

            # Temperature: stagnation peak + decay + radial variation
            # Bow shock structure: T peaks in shock layer, drops in wake
            if z_mid < z_stag:
                # Upstream (freestream approaching)
                T_cell = T_INF + (T_STAGNATION - T_INF) * np.exp(-3.0 * dist_norm)
            else:
                # Downstream (wake region)
                T_cell = T_INF + (T_STAGNATION - T_INF) * 0.3 * np.exp(-2.0 * dist_norm)

            # Add some DSMC noise (1/sqrt(N) statistical fluctuation)
            T_cell *= (1.0 + 0.05 * np.random.randn())
            T_cell = max(T_INF, min(T_STAGNATION * 1.1, T_cell))

            # Velocity: freestream in z-direction, decelerated in shock layer
            # Rankine-Hugoniot: V drops across shock
            v_shock = V_INF * max(0.05, 1.0 - 0.8 * np.exp(-2.0 * dist_norm))
            u_cell = v_shock * (1.0 + 0.02 * np.random.randn())  # z-velocity
            v_cell = 0.05 * V_INF * np.sin(r_mid * 2.0) * np.exp(-dist_norm)  # r-velocity (radial expansion)
            w_cell = 0.0  # azimuthal (axisymmetric)

            # Number density: compressed in shock layer
            n_ratio = 1.0 + 3.0 * np.exp(-2.5 * dist_norm)  # up to 4x compression
            n_cell = N_RHO * n_ratio * (1.0 + 0.03 * np.random.randn())
            n_cell = max(N_RHO * 0.5, n_cell)

            # Number of simulated particles per cell (for SPARTA weighting)
            n_particles = max(1, int(n_cell / 1e20))

            # Extra columns (species, etc.) — pad to match expected format
            extra = " ".join(["0.0"] * 3)

            line = f"{cell_id} {zlo:.6f} {rlo:.6f} {zhi:.6f} {rhi:.6f} {n_particles} {u_cell:.4f} {v_cell:.4f} {w_cell:.4f} {T_cell:.2f} {n_cell:.4e} {extra}"
            lines.append(line)

    with open(output_path, 'w') as f:
        f.write("\n".join(lines) + "\n")

    print(f"[DEMO] Generated synthetic grid dump: {output_path}")
    print(f"       {N_Z * N_R} cells, {timestep} timestep(s)")
    print(f"       T range: {T_INF:.0f}K - {T_STAGNATION:.0f}K (stagnation)")
    print(f"       V_inf: {V_INF:.0f} m/s, n_inf: {N_RHO:.2e} /m³")
    return output_path


def run_pipeline():
    """Execute the full ParaView visualization pipeline with stub data."""
    print("=" * 70)
    print("StellarOrion ParaView Pipeline Demo")
    print("=" * 70)

    # ── Step 0: Verify STL geometry exists ──
    if not os.path.isfile(STL_FILE):
        print(f"[ERROR] HIAD STL geometry not found: {STL_FILE}")
        print("        Ensure HIAD_custom.stl is in the project root.")
        return False
    print(f"[OK] HIAD STL geometry: {STL_FILE}")

    # ── Step 1: Generate synthetic grid dumps ──
    print("\n--- Step 1: Generating synthetic SPARTA grid dumps ---")
    os.makedirs(DEMO_DIR, exist_ok=True)

    grid_files = []
    for t in range(1, 4):  # 3 timesteps to demonstrate time series
        grid_path = os.path.join(DEMO_DIR, f"grid.{t}.out")
        generate_synthetic_grid_dump(grid_path, timestep=t * 100)
        grid_files.append(grid_path)

    # ── Step 2: Export to VTU (2D) and VTP (3D) ──
    print("\n--- Step 2: Exporting to VTK format ---")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "source"))

    from visualizer import export_sparta_vtk, export_sparta_vtk_3d

    # 2D unstructured grid (VTU)
    vtu_files = export_sparta_vtk(
        grid_files,
        os.path.join(DEMO_DIR, "vtu_output"),
        ref_params={'nose_radius': 0.55, 'env_preset': 'earth'}
    )
    if vtu_files:
        print(f"[OK] VTU export: {len(vtu_files)} file(s)")
        for f in vtu_files:
            print(f"     {f}")
    else:
        print("[ERROR] VTU export failed")
        return False

    # 3D revolved surface (VTP)
    vtp_files = export_sparta_vtk_3d(
        grid_files,
        os.path.join(DEMO_DIR, "vtp_output"),
        ref_params={'nose_radius': 0.55, 'env_preset': 'earth'}
    )
    if vtp_files:
        print(f"[OK] VTP export: {len(vtp_files)} file(s)")
        for f in vtp_files:
            print(f"     {f}")
    else:
        print("[WARN] VTP export failed (non-critical)")

    # ── Step 3: Generate ParaView state script ──
    print("\n--- Step 3: Generating ParaView state script ---")
    from visualizer import launch_paraview_for_sparta

    script_path = launch_paraview_for_sparta(
        vtk_file=vtu_files,
        output_dir=DEMO_DIR,
        vtk_3d_file=vtp_files,
        geometry_stl=STL_FILE
    )
    print(f"[OK] ParaView state script: {script_path}")

    # ── Step 4: Launch ParaView ──
    print("\n--- Step 4: Launching ParaView ---")
    paraview_bin = None
    for candidate in ["paraview", "/Applications/ParaView.app/Contents/MacOS/paraview"]:
        found = shutil.which(candidate)
        if found:
            paraview_bin = found
            break
        if os.path.isfile(candidate):
            paraview_bin = candidate
            break

    if paraview_bin:
        import subprocess
        try:
            proc = subprocess.Popen(
                [paraview_bin, "--script", script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[OK] ParaView launched (PID: {proc.pid})")
            print(f"     Script: {script_path}")
        except Exception as e:
            print(f"[WARN] Could not auto-launch ParaView: {e}")
            print(f"       Run manually: paraview --script={script_path}")
    else:
        print("[INFO] ParaView not found on PATH")
        print(f"       Run manually: paraview --script={script_path}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("Pipeline Summary")
    print("=" * 70)
    print(f"  Output directory:  {DEMO_DIR}")
    print(f"  Grid dumps:        {len(grid_files)} file(s)")
    print(f"  VTU (2D):          {len(vtu_files) if vtu_files else 0} file(s)")
    print(f"  VTP (3D):          {len(vtp_files) if vtp_files else 0} file(s)")
    print(f"  STL geometry:      {STL_FILE}")
    print(f"  ParaView script:   {script_path}")
    print()
    print("  ParaView will show:")
    print("    1. 2D temperature field (Black-Body Radiation colormap)")
    print("    2. 3D revolved surface (Jet colormap, 60% opacity)")
    print("    3. HIAD STL geometry (light grey, 85% opacity)")
    print()
    print("  Use VCR controls to animate through timesteps.")
    print("  Switch arrays in Properties panel for Pressure/Mach/Knudsen.")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
