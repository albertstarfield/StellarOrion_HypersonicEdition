# Unsteady Physics & Timestep Justification for DSMC Optimization

**Date:** July 2026
**Context:** Justification for the 1,100 timestep limit during the automated sampling/optimization phase vs. supervisor's concern for unsteady flow resolution.

## 1. Physical Timescales at Mach 5+ Conditions
*   **Velocity (`vstream`):** 2,700 m/s
*   **Time Step (`env_step`):** $1 \times 10^{-6}$ s (1 $\mu$s)
*   **Optimization Run Steps (`env_run`):** 1,100 steps
*   **Total Simulated Physical Time:** 1.1 ms (0.0011 seconds)

### Critical Timescales vs. 1.1ms Window

| Phenomenon | Timescale | Captured by 1,100 Steps (1.1 ms)? |
| :--- | :--- | :--- |
| **Bowshock establishment** | ~0.1–0.5 ms | ✅ **Yes** |
| **Particle transit (domain sweep)** | ~$L/v = 14 / 2700 \approx 5.2$ ms | ❌ **Only ~21% of one full sweep** |
| **Toroid valley recirculation (Unsteady)** | ~5–20 ms | ❌ **No** |
| **Thermal soak through TPS layers** | ~Seconds to minutes | ❌ **Far too short** |
| **DSMC statistical averaging window** | ~0.5–2.0 ms | ⚠️ **Marginal** |

---

## 2. The Verdict: Is 1,100 steps sufficient?

### Why 1,100 steps IS sufficient for the Optimization Phase (Sampling):
For the initial generation of the 2,500 sample matrix, 1,100 steps is practically defensible because:
1.  **Drag Coefficient ($C_d$) Stabilization:** The integrated drag force reaches a plateau early. By step 300, the gradients flatten out. Optimization relies on the **relative ranking** of $C_d$ and stagnation heat flux across different geometries, not absolute long-term accumulation.
2.  **Surrogate Smoothing:** The Physics-Informed Neural Network (PINN) interpolates between the 2,500 samples, which naturally smooths out short-time DSMC statistical noise.
3.  **Computational Feasibility:** Running thousands of geometry variants for the full unsteady timescale (e.g., 20+ ms requiring 20,000+ steps) would be computationally prohibitive for a single node.

### Why the Supervisor is Correct (Unsteady Flow Resolution):
The supervisor's concern is entirely valid regarding **scalloped toroid valleys**.
The 1.1 ms simulation window is not long enough to capture a full unsteady fluid recirculation cycle in the cavities between the inflatable toroids. This unsteady recirculation dictates the localized peaks in heat flux ("Thermal Accumulation") that threaten the 350K bondline limit.

---

## 3. Recommended Thesis Methodology
To satisfy both computational limits and rigorous physics validation, the thesis methodology should state:

1.  **Optimization Phase (MDAO / Surrogate Training):** Run 2,500 points at 1,100 steps using space-filling augmented CCD. This establishes the Pareto front efficiently using steady-state assumptions for bulk forces.
2.  **Final Validation Phase (Unsteady Physics):** Select the single final optimized geometry (or top 3 candidates) and perform a **long-duration unsteady DSMC simulation (5,000–10,000+ steps)**.
3.  **Reporting:** Use this long-run data to properly validate the unsteady recirculation and transient thermal accumulation in the toroid valleys. Acknowledge the 1,100-step runs as a known limitation of the search phase, resolved by the final high-fidelity validation.

---
*Note: The mathematical minimum sample size for a 4-variable Face-Centered Central Composite Design (CCD) is 25 samples. The 2,500 sample setup acts as a space-filling augmented design to train the PINN surrogate model over the entire domain.*
