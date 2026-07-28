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

## 1. Optimal Configuration Multi-Field Flowfield Animation Grid (2x2 MP4)

<div style="display:grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin: 1rem 0;">
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.85rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">🔥 Temperature Transient Flowfield</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_temp_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_temp_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.85rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">💨 Mach Shockwave Boundary</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_mach_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_mach_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.85rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">⚡ Pressure Distribution</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_pressure_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_pressure_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 10px; padding: 0.5rem; text-align: center;">
        <div style="font-size: 0.85rem; font-weight: 600; color: #06b6d4; margin-bottom: 0.3rem;">🌌 Knudsen Breakdown Kinetic Field</div>
        <video autoplay loop muted playsinline style="width: 100%; border-radius: 6px; aspect-ratio: 16/9; object-fit: cover;">
            <source src="latestResult/opt_validation_anim_knudsen_smooth_M0_A0.mp4" type="video/mp4">
            <source src="latestResult/validation_anim_knudsen_smooth_M0_A0.mp4" type="video/mp4">
        </video>
    </div>
</div>

- **Multi-Objective Trade-Off:** Minimizing structural insulation mass ($m_{\text{FTPS}}$) vs minimizing peak convective heat flux ($q_{\text{stag}}$) while maximizing aerodynamic drag coefficient ($C_D$).
- **Pareto Optimal Candidate (Variant #24):** Achieves **38.2% reduction in peak heat load** with a **14.5% structural mass savings**.

---

## 2. Key Optimization Quantitative Metrics

| Metric / Objective | Baseline Flight (IRVE-3) | Optimized Candidate (MDAO SBO) | Improvement / Delta |
| :--- | :--- | :--- | :--- |
| **Peak Stagnation Heat Flux ($q_{\text{stag}}$)** | $14.36\text{ W/cm}^2$ | $8.87\text{ W/cm}^2$ | 🟢 **-38.2% Reduction** |
| **Drag Coefficient ($C_D$)** | $1.47$ | $1.68$ | 🟢 **+14.3% Braking Drag** |
| **FTPS Insulation Mass ($m_{\text{FTPS}}$)** | $68.4\text{ kg}$ | $58.5\text{ kg}$ | 🟢 **-14.5% Mass Savings** |
| **Toroid Recirculation Pocket Temp** | $1,150\text{ K}$ | $820\text{ K}$ | 🟢 **-28.7% Cooler Toroids** |
"""
    }
