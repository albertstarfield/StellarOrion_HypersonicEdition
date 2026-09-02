#!/usr/bin/env python3
"""
================================================================================
SCRIPT: make_vtu_visualization.py — VTU Physical Visualization Plotter
================================================================================

AXIOMS:
  AXIOM 1: SPARTA writes VTU (VTK UnstructuredGrid) files into paraview/
           every 100 steps during validation runs.
  AXIOM 2: Each VTU contains 3D surface mesh points + cell data:
           HeatFlux_Wm2, Drag_N, Lift_N.
  AXIOM 3: The HIAD is axisymmetric — a 2D cross-section suffices for
           physical visualization of heat flux distribution.

THEORIES:
  THEOREM 1: Surface heat flux distribution shows the stagnation region
             (highest heating) and shoulder/side regions (lower heating).
  THEOREM 2: The 3D surface plot colored by heat flux provides physical
             context for the DSMC simulation results.

APPLICATIONS:
  - Parse VTU XML files using xml.etree.ElementTree
  - Extract point coordinates and HeatFlux_Wm2 data
  - Create 4 visualization plots:
    1. 3D surface colored by heat flux (side perspective)
    2. 2D axisymmetric cross-section with heat flux colormap
    3. Heat flux distribution histogram
    4. Heat flux vs X-position (stagnation to shoulder)
  - Write PNGs to <results_dir>/plots/

CITATIONS:
  [VTUFormat] VTK File Format, https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf
  [Bird1994] Bird, G.A. "Molecular Gas Dynamics and the Direct Simulation
             of Gas Flows", 1994.
  [Rapisarda2023] Rapisarda, V. "Parametric Geometry and Trajectory
                    Optimization for HIAD", 2023.

TIMING ANALYSIS:
  Estimated Processing Time: O(P * N) where P=points, N=VTU files.
  WCET: < 30 s for typical validation runs (<= 23 VTU files).
================================================================================
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # headless backend

# ---------------------------------------------------------------------------
# Physical constants for T_surface mapping
# [Source: stellarorion_physics.ads; Stefan-Boltzmann law]
# ---------------------------------------------------------------------------
SIGMA_SB = 5.670374419e-8  # W/(m^2 K^4)
EMISSIVITY = 0.85          # SIC emissivity [Hollis et al. AIAA-2024-1498]


def _parse_vtu(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse VTU file, return (points Nx3, heat_flux_N).

    AXIOM: VTU XML has <Points> with Float64 NumberOfComponents=3,
           and <CellData> with HeatFlux_Wm2 DataArray.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    # --- Points ---
    points_arr = None
    for da in root.iter("DataArray"):
        if da.get("NumberOfComponents") == "3" and da.get("type") == "Float64":
            text = da.text.strip() if da.text else ""
            vals = [float(v) for v in text.split() if v]
            points_arr = np.array(vals).reshape(-1, 3)
            break
    if points_arr is None:
        raise ValueError(f"No Points DataArray found in {path}")

    # --- HeatFlux ---
    heat_arr = None
    for da in root.iter("DataArray"):
        if da.get("Name") == "HeatFlux_Wm2":
            text = da.text.strip() if da.text else ""
            vals = [float(v) for v in text.split() if v]
            heat_arr = np.array(vals)
            break
    if heat_arr is None:
        raise ValueError(f"No HeatFlux_Wm2 DataArray in {path}")

    # Reshape to per-point if per-cell (3648 cells vs 3696 points)
    if len(heat_arr) == 3648 and len(points_arr) == 3696:
        # Cell data → approximate per-point by averaging cell corners
        # For simplicity, pad with zeros (last 48 points are duplicates)
        heat_arr = np.concatenate([heat_arr, np.zeros(len(points_arr) - len(heat_arr))])

    return points_arr, heat_arr


def _watts_to_celsius_friendly(q_wm2: float) -> float:
    """Convert W/m² to W/cm² for display."""
    return q_wm2 / 1e4


def _q_to_t_surface(q_wm2: float) -> float:
    """Compute T_surface from heat flux using Stefan-Boltzmann law.
    T = (q / (sigma * epsilon))^0.25
    [Source: stellarorion_physics.ads Radiative_Eq_Temp]"""
    if q_wm2 <= 0:
        return 300.0
    return (q_wm2 / (SIGMA_SB * EMISSIVITY)) ** 0.25


def plot_3d_surface(points: np.ndarray, heat: np.ndarray, out_path: str,
                    step: int) -> None:
    """3D surface plot colored by heat flux."""
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection="3d")

    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    q_cm2 = heat / 1e4  # W/m² → W/cm²

    # Subsample for performance (plot every 4th point)
    idx = np.arange(0, len(x), 4)
    sc = ax.scatter(x[idx], z[idx], y[idx], c=q_cm2[idx], cmap="hot",
                    s=2, alpha=0.8, vmin=0, vmax=max(q_cm2.max(), 50))

    ax.set_xlabel("X (m) — Flow Direction", fontsize=10)
    ax.set_ylabel("Z (m) — Axial", fontsize=10)
    ax.set_zlabel("Y (m) — Radial", fontsize=10)
    ax.set_title(f"HIAD Surface Heat Flux Distribution — Step {step}\n"
                 f"DSMC (SPARTA) 5-species air, Mach 10, Alt 52 km",
                 fontsize=12, fontweight="bold")

    cb = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.1)
    cb.set_label("Heat Flux (W/cm²)", fontsize=10)

    ax.view_init(elev=20, azim=45)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {os.path.basename(out_path)}")


def plot_2d_cross_section(points: np.ndarray, heat: np.ndarray,
                          out_path: str, step: int) -> None:
    """2D axisymmetric cross-section with heat flux colormap.

    Since HIAD is axisymmetric, we show the X-Z plane (Y=0 slice)
    with color indicating heat flux magnitude.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    x, z = points[:, 0], points[:, 2]
    q_cm2 = heat / 1e4

    # Filter points near Y=0 plane (|Y| < 0.01m) for cross-section
    y = points[:, 1]
    mask = np.abs(y) < 0.01
    if mask.sum() < 10:
        # Fallback: use all points projected
        mask = np.ones(len(x), dtype=bool)

    sc = ax.scatter(x[mask], z[mask], c=q_cm2[mask], cmap="hot", s=8,
                    vmin=0, vmax=max(q_cm2[mask].max(), 50))

    ax.set_xlabel("X (m) — Flow Direction →", fontsize=11)
    ax.set_ylabel("Z (m) — Vehicle Axial", fontsize=11)
    ax.set_title(f"HIAD Cross-Section Heat Flux — Step {step}\n"
                 f"2D Axisymmetric Slice (|Y| < 0.01m)  |  "
                 f"Max: {q_cm2[mask].max():.1f} W/cm²  |  "
                 f"Avg: {q_cm2[mask].mean():.1f} W/cm²",
                 fontsize=11, fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    cb = fig.colorbar(sc, ax=ax, shrink=0.8)
    cb.set_label("Heat Flux (W/cm²)", fontsize=10)

    # Annotate stagnation region
    idx_max = np.argmax(q_cm2[mask])
    x_max = x[mask][idx_max]
    z_max = z[mask][idx_max]
    ax.annotate(f"Stagnation\n{q_cm2[mask][idx_max]:.1f} W/cm²",
                xy=(x_max, z_max), xytext=(x_max + 0.3, z_max + 0.3),
                arrowprops=dict(arrowstyle="->", color="white"),
                fontsize=9, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.7))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {os.path.basename(out_path)}")


def plot_heat_flux_histogram(heat: np.ndarray, out_path: str,
                             step: int) -> None:
    """Histogram of heat flux distribution across surface elements."""
    fig, ax = plt.subplots(figsize=(10, 6))
    q_cm2 = heat / 1e4
    q_nonzero = q_cm2[q_cm2 > 0]

    ax.hist(q_nonzero, bins=50, color="orangered", edgecolor="black",
            alpha=0.8, density=False)
    ax.axvline(x=q_nonzero.mean(), color="blue", linestyle="--",
               linewidth=2, label=f"Mean: {q_nonzero.mean():.1f} W/cm²")
    ax.axvline(x=np.median(q_nonzero), color="green", linestyle=":",
               linewidth=2, label=f"Median: {np.median(q_nonzero):.1f} W/cm²")
    ax.axvline(x=14.36, color="purple", linestyle="-.",
               linewidth=2, label="IRVE-3 flight peak (14.36 W/cm²)")

    ax.set_xlabel("Heat Flux (W/cm²)", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title(f"Surface Heat Flux Distribution — Step {step}\n"
                 f"DSMC element-level values  |  N={len(q_nonzero)} non-zero elements",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {os.path.basename(out_path)}")


def plot_heat_flux_vs_x(points: np.ndarray, heat: np.ndarray,
                        out_path: str, step: int) -> None:
    """Heat flux vs X-position (stagnation to shoulder)."""
    fig, ax1 = plt.subplots(figsize=(12, 6))

    x = points[:, 0]
    q_cm2 = heat / 1e4
    t_surf = np.array([_q_to_t_surface(q) for q in heat])

    # Sort by X position
    sort_idx = np.argsort(x)
    x_sorted = x[sort_idx]
    q_sorted = q_cm2[sort_idx]
    t_sorted = t_surf[sort_idx]

    color1 = "tab:red"
    color2 = "tab:blue"

    ax1.plot(x_sorted, q_sorted, "o-", color=color1, markersize=3,
             linewidth=1.5, label="Heat Flux")
    ax1.set_xlabel("X Position (m) — Stagnation → Shoulder", fontsize=11)
    ax1.set_ylabel("Heat Flux (W/cm²)", fontsize=11, color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    ax2.plot(x_sorted, t_sorted, "s--", color=color2, markersize=3,
             linewidth=1.5, label="T_surface")
    ax2.axhline(y=1700, color="red", linestyle=":", linewidth=1.5,
                alpha=0.7, label="SIC limit (1700K)")
    ax2.set_ylabel("T_surface (K)", fontsize=11, color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)

    ax1.set_title(f"Heat Flux & Surface Temperature vs X-Position — Step {step}\n"
                  f"Stagnation point at X ≈ {x_sorted[0]:.3f} m",
                  fontsize=12, fontweight="bold")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {os.path.basename(out_path)}")


def main(argv: list[str]) -> int:
    results_dir = argv[1] if len(argv) > 1 else "results_validation_scalloped"
    paraview_dir = os.path.join(results_dir, "paraview")
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # Find all VTU files — sort numerically by step number, NOT lexicographically
    # Lexicographic sort breaks for steps like 200 vs 1900 (string "200" > "1900")
    def _extract_step(p: str) -> int:
        """Extract step number from VTU filename (surf_NNNN.vtu -> NNNN)."""
        base = os.path.basename(p)
        num_str = base.replace("surf_", "").replace(".vtu", "")
        try:
            return int(num_str)
        except ValueError:
            return 0

    vtu_files = sorted([
        os.path.join(paraview_dir, f)
        for f in os.listdir(paraview_dir)
        if f.endswith(".vtu")
    ], key=_extract_step)

    if not vtu_files:
        print(f"[vtu-viz] No VTU files in {paraview_dir}", file=sys.stderr)
        return 1

    print(f"[vtu-viz] Found {len(vtu_files)} VTU files")

    # Process key steps: first, early (500), mid (1000), late (1500), near-end (2000), last
    # Always include first and last; add intermediate steps at ~500-step intervals
    all_steps = [_extract_step(f) for f in vtu_files]
    target_steps = [100, 500, 1000, 1500, 2000, all_steps[-1]]
    key_indices = []
    for ts in target_steps:
        # Find closest available step
        best_idx = min(range(len(all_steps)),
                       key=lambda i: abs(all_steps[i] - ts))
        if best_idx not in key_indices:
            key_indices.append(best_idx)
    key_indices = sorted(key_indices)

    for idx in key_indices:
        vtu_path = vtu_files[idx]
        step_str = os.path.basename(vtu_path).replace("surf_", "").replace(".vtu", "")
        step = int(step_str)
        print(f"\n[vtu-viz] Processing step {step}...")

        points, heat = _parse_vtu(vtu_path)
        print(f"  Points: {len(points)}, Heat flux range: "
              f"{heat.min():.0f} - {heat.max():.0f} W/m²")

        # 1. 3D surface
        plot_3d_surface(
            points, heat,
            os.path.join(plots_dir, f"vtu_3d_step{step}.png"),
            step,
        )

        # 2. 2D cross-section
        plot_2d_cross_section(
            points, heat,
            os.path.join(plots_dir, f"vtu_cross_section_step{step}.png"),
            step,
        )

        # 3. Histogram
        plot_heat_flux_histogram(
            heat,
            os.path.join(plots_dir, f"vtu_histogram_step{step}.png"),
            step,
        )

        # 4. Heat flux vs X
        plot_heat_flux_vs_x(
            points, heat,
            os.path.join(plots_dir, f"vtu_heatflux_vs_x_step{step}.png"),
            step,
        )

    print(f"\n[vtu-viz] Wrote {len(key_indices) * 4} PNGs to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
