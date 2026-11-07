def get_slide_data() -> dict:
    return {
        'id': 'slide_val_grid',
        'title': 'Grid Dependency & Optimized Topology Mesh',
        'category': 'Validation',
        'content': r"""
# Grid Dependency & Optimized Topology Mesh

To ensure our DSMC results are independent of grid resolution and align with the Rapisarda baseline, we conducted a grid dependency study across adaptive octree refinement levels.

---

## 1. Dynamic Topology Refinement Animation (MP4)

<div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0;">
    <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(16, 185, 129, 0.5); border-radius: 12px; padding: 0.75rem; text-align: center;">
        <div style="font-size: 0.9rem; font-weight: 600; color: #10b981; margin-bottom: 0.4rem;">🕸️ Optimized Adaptive Mesh Topology MP4</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 8px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_grid_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/opt_validation_anim_grid_smooth.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(6, 182, 212, 0.5); border-radius: 12px; padding: 0.75rem; text-align: center;">
        <div style="font-size: 0.9rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.4rem;">📐 3D Mesh Topology Surface Grid</div>
        <img src="latestResult/opt_upscaled_3d_grid_smooth_M0_A0.png" alt="3D Mesh Topology" style="width: 100%; border-radius: 8px; aspect-ratio: 16/9; object-fit: cover;" />
    </div>
</div>

---

## 2. Mesh Independence Study

| Parameter | Value | Note |
|:---|:---|:---|
| **Mesh Type** | 3D Octree Adaptive Grid | Dynamic SPARTA Cell Refinement |
| **Tested Meshes** | 9 configurations | Range: 1,694 to 54,446 triangles |
| **Convergence Point** | 30,000 cells | $C_d$ stabilizes with < 1% variation |
| **Recommended Density** | $A_{\text{panel}} / A_{\text{total}} < 4 \times 10^{-4}$ | Normalised average panel area |
| **Grid Factor Selection** | **0.7 Multiplier** | Optimal balance of fidelity & speed |

**Conclusion:** Selecting a **Grid Factor multiplier of 0.7** yields approximately 30,000 cell convergence, providing the ideal trade-off between computational performance and physics resolution.
"""
    }
