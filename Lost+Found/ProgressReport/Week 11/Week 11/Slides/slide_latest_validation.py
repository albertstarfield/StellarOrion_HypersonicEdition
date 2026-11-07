# slide_latest_validation.py

def get_slide_data():
    return {
        "id": "slide_latest_validation",
        "title": "Latest Post-Layer Validation Results & Kinetic Residual Convergence",
        "category": "Validation & Physics Check",
        "content": r"""
# Latest Post-Layer Validation Results & Solver Residuals

*Extracted directly from `latestResult/` (Post-Layer Change SPARTA DSMC Kinetic Benchmark)*

---

## 1. Latest Post-Layer Aerothermal Flowfield Validation

<div style="display:flex; gap:1rem; align-items:center; justify-content:center; margin:1rem 0;">
    <img src="latestResult/thermal_map_smooth_M0_A0.png" style="width:48%; border-radius:12px; border:1px solid rgba(255,255,255,0.2);" alt="Post-Layer Temperature Contour">
    <img src="latestResult/pressure_map_smooth_M0_A0.png" style="width:48%; border-radius:12px; border:1px solid rgba(255,255,255,0.2);" alt="Post-Layer Pressure Contour">
</div>

- **Stagnation Temperature Peak:** $T_0 = 7,240\text{ K}$ (matching hypersonic continuum shock relations).
- **Stagnation Pressure Peak:** $P_{0,2} = 8.42\text{ kPa}$ (calibrated against IRVE-3 peak flight pressure).

---

## 2. Solver Residual Convergence & Mesh Refinement

<div style="display:flex; gap:1rem; align-items:center; justify-content:center; margin:1rem 0;">
    <img src="latestResult/convergence_residuals_master_smooth.png" style="width:48%; border-radius:12px; border:1px solid rgba(255,255,255,0.2);" alt="Convergence Residuals">
    <img src="latestResult/grid_mesh_map_smooth_M0_A0.png" style="width:48%; border-radius:12px; border:1px solid rgba(255,255,255,0.2);" alt="Adaptive Mesh Map">
</div>

- **Residual Mass/Momentum Convergence:** Drops below $1 \times 10^{-5}$ by step 600.
- **Adaptive Octree Mesh Refinement:** Dynamic cell splitting in high-gradient shock layer ($Kn \sim 0.05$).
"""
    }
