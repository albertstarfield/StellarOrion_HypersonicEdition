# slide_root_timestep_justification.py

def get_slide_data():
    return {
        "id": "slide_root_timestep_justification",
        "title": "DSMC Unsteady Physical Timescale & Timestep Justification",
        "category": "Numerical Kinetics & Validation",
        "content": r"""
# Unsteady Physics & Timestep Justification for DSMC Optimization

*Formal Thesis Defense & Numerical Justification from `THESIS_TIMESTEP_JUSTIFICATION.md`*

---

## 1. Physical Timescales at Hypersonic Conditions ($M_\infty = 9.0$)
- **Freestream Velocity ($V_\infty$):** $2,700\text{ m/s}$
- **DSMC Time Step ($\Delta t$):** $1 \times 10^{-6}\text{ s}$ ($1.0\text{ }\mu\text{s}$)
- **Optimization Sample Limit:** $1,100\text{ timesteps}$
- **Total Simulated Physical Window:** $1.1\text{ ms}$ ($0.0011\text{ s}$)

---

## 2. Multi-Physics Timescale Hierarchy Matrix

| Physical Phenomenon | Timescale | Captured by 1,100 Steps ($1.1\text{ ms}$)? | Justification & Impact |
| :--- | :--- | :--- | :--- |
| **Bow Shock Wave Establishment** | $\sim 0.1 - 0.5\text{ ms}$ | ✅ **Fully Captured** | Primary shock layer heating $T_0 > 7,000\text{ K}$ settles early. |
| **Particle Transit Across Domain** | $\sim L/V \approx 5.2\text{ ms}$ | ⚠️ **21% Sweep** | Sufficient for relative ranking across LHS variants. |
| **Toroid Valley Recirculation** | $\sim 5 - 20\text{ ms}$ | ❌ **Unsteady Limit** | Recirculation vortices require full unsteady transient runs. |
| **Thermal Soak through FTPS** | $\sim \text{Seconds}$ | ❌ **Decoupled** | Handled via 1D transient heat conduction solver. |
| **Statistical DSMC Averaging** | $\sim 0.5 - 2.0\text{ ms}$ | ✅ **Acceptable** | Drag ($C_D$) plateaus by step 300; gradients flatten. |

---

## 3. Defense Strategy for Surrogate-Based Optimization (SBO)
1. **$C_D$ & $q_{\text{stag}}$ Stabilization:** $C_D$ integrated drag force stabilizes by step 300. Sampling 1,100 steps preserves exact relative ranking across 2,500 LHS design variants.
2. **Computational Cost:** 1,100 steps requires $\sim 45\text{s}$ per design variant vs $\sim 15\text{ mins}$ for 20,000 steps (saving 95% CPU compute time).
3. **Verification Stage:** Top Pareto optimal candidates undergo extended 15,000+ step full DSMC transient verification.
"""
    }
