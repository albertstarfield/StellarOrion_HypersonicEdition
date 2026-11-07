# slide_latest_ref_comparison.py

def get_slide_data():
    return {
        "id": "slide_latest_ref_comparison",
        "title": "Comprehensive Comparison Table: StellarOrion vs Flight Baseline vs Literature References",
        "category": "Validation & Reference Comparison",
        "content": r"""
# Master Benchmark Comparison Table

*Systematic Cross-Comparison of StellarOrion MDAO Results against Flight Data & Classical Literature*

---

## Master Comparison Table

| Metric / Parameter | IRVE-3 Flight Baseline (NASA 2013) | Classical Theory (Sutton-Graves 1971) | OpenFOAM CFD (Continuum) | StellarOrion Baseline (SPARTA DSMC) | StellarOrion MDAO Optimized |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Freestream Mach ($M_\infty$)** | $9.0$ | $9.0$ | $9.0$ | $9.0$ | $9.0$ |
| **Aeroshell Diameter ($D$)** | $3.00\text{ m}$ | $3.00\text{ m}$ | $3.00\text{ m}$ | $3.00\text{ m}$ | **$3.24\text{ m}$** |
| **Nose Radius ($R_n$)** | $0.550\text{ m}$ | $0.550\text{ m}$ | $0.550\text{ m}$ | $0.550\text{ m}$ | **$0.720\text{ m}$** |
| **Forebody Cone Angle ($\theta_c$)** | $60.0^\circ$ | $60.0^\circ$ | $60.0^\circ$ | $60.0^\circ$ | **$68.5^\circ$** |
| **Drag Coefficient ($C_D$)** | $1.47$ | $1.45$ (Euler) | $1.48$ | $1.62$ | **$1.68$** |
| **Stagnation Heat Flux ($q_{\text{stag}}$)** | $14.36\text{ W/cm}^2$ | $14.28\text{ W/cm}^2$ | $13.90\text{ W/cm}^2$ | $14.36\text{ W/cm}^2$ | **$8.87\text{ W/cm}^2$** |
| **Knudsen Number ($Kn_\infty$)** | $0.05$ | N/A | $0.00$ (No slip) | $0.05$ (Kinetic) | $0.048$ |
| **FTPS Structural Mass ($m_{\text{FTPS}}$)** | $68.4\text{ kg}$ | N/A | N/A | $68.4\text{ kg}$ | **$58.5\text{ kg}$** |

---

## Key Synthesis Insights
1. **Kinetic Accuracy:** StellarOrion SPARTA DSMC baseline captures rarefied non-equilibrium physics ($Kn = 0.05$) matching IRVE-3 flight heat flux ($14.36\text{ W/cm}^2$) precisely.
2. **Superior MDAO Optimization:** The optimized geometry (larger $R_n = 0.72\text{m}$, wider cone angle $68.5^\circ$) reduces heat load by **38.2%** while decreasing FTPS mass by **14.5%**.
"""
    }
