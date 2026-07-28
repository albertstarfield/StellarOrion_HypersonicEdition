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

## 1. MDAO Pareto Frontier Trade-Off Analysis

<div style="display:flex; gap:1rem; align-items:center; justify-content:center; margin:1rem 0;">
    <img src="latestResult/thermal_map_opt.png" style="width:48%; border-radius:12px; border:1px solid rgba(255,255,255,0.2);" alt="Optimized Thermal Contour">
    <img src="latestResult/pressure_map_opt.png" style="width:48%; border-radius:12px; border:1px solid rgba(255,255,255,0.2);" alt="Optimized Pressure Contour">
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
