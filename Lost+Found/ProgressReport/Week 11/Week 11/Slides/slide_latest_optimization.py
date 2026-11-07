# slide_latest_optimization.py

def get_slide_data():
    return {
        "id": "slide_latest_optimization",
        "title": "Latest Aerothermal MDAO Optimization & Pareto Trade-Off Results",
        "category": "Optimization & Results",
        "content": r"""
# Latest Aerothermal MDAO Optimization Results

*Extracted directly from `latestResult/OPTIMIZATION_LOG.md` & `latestResult/optimization_history.db`*

---

## 1. Optimal Configuration Multi-Field Flowfield Animation Grid (6-Card Showcase Grid)

<div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.8rem; margin: 1rem 0;">
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-anchor: center; text-align: center;">
        <div style="font-size: 0.82rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">🔥 Temperature Flowfield</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_temp_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_temp_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.82rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">💨 Mach Shock Front</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_mach_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_mach_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.82rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">⚡ Pressure Field</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_pressure_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_pressure_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.82rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">🌌 Knudsen Field</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_knudsen_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_knudsen_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(16, 185, 129, 0.5); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.82rem; font-weight: 600; color: #10b981; margin-bottom: 0.3rem;">🕸️ Optimized Mesh Topology Grid</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_grid_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/opt_validation_anim_grid_smooth.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(245, 158, 11, 0.5); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.82rem; font-weight: 600; color: #f59e0b; margin-bottom: 0.3rem;">🚀 3D Mesh Topology Silhouette</div>
        <img src="latestResult/opt_upscaled_3d_grid_smooth_M0_A0.png" alt="3D Mesh Topology" style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;" />
    </div>
</div>

- **Multi-Objective Trade-Off:** Minimizing structural insulation mass ($m_{\text{FTPS}}$) vs minimizing peak convective heat flux ($q_{\text{stag}}$) while maximizing aerodynamic drag coefficient ($C_D$).
- **Pareto Optimal Candidate (Variant #24):** Achieves **38.2% reduction in peak heat load** with a **14.5% structural mass savings**.

---


<div style="background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 16px; padding: 1.5rem; margin: 1.5rem 0; box-shadow: 0 12px 32px rgba(0,0,0,0.6);">
    <h3 style="color: #06b6d4; font-weight: 600; margin-top: 0; margin-bottom: 1.2rem; display: flex; align-items: center; gap: 0.5rem;">
        ⚡ MoP SBO Multi-Disciplinary Optimization Flowchart
    </h3>
    <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #06b6d4; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2);">
            <div>
                <div style="font-weight: 700; color: #38bdf8; font-size: 1rem;">1. SPARTA DSMC Ground Truth Sampling</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">25 CCD / LHS geometry variants × 1,100 SPARTA timesteps</div>
            </div>
            <span style="background: rgba(14, 165, 233, 0.2); border: 1px solid #38bdf8; color: #38bdf8; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">⏱️ ~20-24 Hours Wall-Clock</span>
        </div>
        <div style="text-align: center; color: #06b6d4; font-size: 1.2rem; margin: -0.4rem 0;">▼</div>
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #a855f7; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.2);">
            <div>
                <div style="font-weight: 700; color: #c084fc; font-size: 1rem;">2. Train MoP DeepXDE PINN Metamodel</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">Learns continuous response surface + enforces Navier-Stokes PDE loss (2,500 epoch steps)</div>
            </div>
            <span style="background: rgba(168, 85, 247, 0.2); border: 1px solid #c084fc; color: #c084fc; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">⏱️ ~11 Mins GPU/CPU</span>
        </div>
        <div style="text-align: center; color: #a855f7; font-size: 1.2rem; margin: -0.4rem 0;">▼</div>
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #f59e0b; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.2);">
            <div>
                <div style="font-weight: 700; color: #fbbf24; font-size: 1rem;">3. SBO Evolutionary Loop (NSGA-II Genetic Search)</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">Evaluates 10,000 to 20,000 candidate shapes using MoP surrogate ──► Extracts PARETO FRONTIER</div>
            </div>
            <span style="background: rgba(245, 158, 11, 0.2); border: 1px solid #fbbf24; color: #fbbf24; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">⏱️ ~5 ms / eval (&lt; 10s)</span>
        </div>
        <div style="text-align: center; color: #f59e0b; font-size: 1.2rem; margin: -0.4rem 0;">▼</div>
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #10b981; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);">
            <div>
                <div style="font-weight: 700; color: #34d399; font-size: 1rem;">4. Final Pareto Winner Verification</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">Selects Variant #24 (-38.2% peak heat flux) for 1 final extended (10,000+ step) DSMC run</div>
            </div>
            <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #34d399; color: #34d399; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">🎯 Final Verification</span>
        </div>
    </div>
</div>


## 2. Key Optimization Quantitative Metrics

| Metric / Objective | Baseline Flight (IRVE-3) | Optimized Candidate (MDAO SBO) | Improvement / Delta |
| :--- | :--- | :--- | :--- |
| **Peak Stagnation Heat Flux ($q_{\text{stag}}$)** | $14.36\text{ W/cm}^2$ | $8.87\text{ W/cm}^2$ | 🟢 **-38.2% Reduction** |
| **Drag Coefficient ($C_D$)** | $1.47$ | $1.68$ | 🟢 **+14.3% Braking Drag** |
| **FTPS Insulation Mass ($m_{\text{FTPS}}$)** | $68.4\text{ kg}$ | $58.5\text{ kg}$ | 🟢 **-14.5% Mass Savings** |
| **Toroid Recirculation Pocket Temp** | $1,150\text{ K}$ | $820\text{ K}$ | 🟢 **-28.7% Cooler Toroids** |
"""
    }
