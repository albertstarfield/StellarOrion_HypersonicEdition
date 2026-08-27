def get_slide_data() -> dict:
    return {
        'title': 'Week 11 MDAO Optimization: IRVE-3 Reference vs. AI Optimums',
        'content': r'''
# Week 11 MDAO Optimization: NASA IRVE-3 Reference vs. AI Optimums

Comprehensive aerothermal performance comparison between the NASA IRVE-3 flight test baseline and the StellarOrion AI-optimized configurations:

| Parameter / Metric | IRVE-3 Reference (Rapisarda 2023) | Optimum A: Max Drag (Sample 9 / 11) | Optimum B: Thermal Stability (Sample 7) | Delta (Opt A vs Ref) |
| :--- | :--- | :--- | :--- | :--- |
| **Major Outer Diameter ($D$)** | $3.00\\text{ m}$ | **$4.86\\text{ m}$** (Expanded Scale) | $2.92\\text{ m}$ (Standard Scale) | **$+62.0\\%$** |
| **Cone Half-Angle ($\\theta$)** | $60.0^\\circ$ | **$45.0^\\circ$** | $75.0^\\circ$ | $-15.0^\\circ$ |
| **Toroid Stack Count ($N$)** | $6$ | **$7$** (Locked $202.5\\text{mm}$ toroid) | $6$ | $+1$ toroid |
| **Nose Radius ($R_n$)** | $0.55\\text{ m}$ | **$0.60\\text{ m}$** | $0.60\\text{ m}$ | $+0.05\\text{ m}$ |
| **Aerodynamic Drag ($F_D$)** | $62.72\\text{ kN}$ | **$194.84\\text{ kN}$** | $92.84\\text{ kN}$ | **$+210.6\\%$** |
| **Drag Coefficient ($C_D$)** | $\\approx 1.47$ | **$1.49$** (Scalloped geometry) | $1.48$ | $+1.36\\%$ |
| **Ballistic Coeff ($\\beta$)** | $26.90\\text{ kg/m}^2$ | **$8.85\\text{ kg/m}^2$** (Ultra-fast decel) | $18.58\\text{ kg/m}^2$ | **$-67.10\\%$** |
| **Stagnation Heat Flux ($\\dot{q}_{\\text{stag}}$)** | $14.36\\text{ W/cm}^2$ ($143.6\\text{ kW/m}^2$) | **$18.16\\text{ W/cm}^2$** ($181.6\\text{ kW/m}^2$) | **$18.16\\text{ W/cm}^2$** ($181.6\\text{ kW/m}^2$) | $+3.80\\text{ W/cm}^2$ |
| **Shock Layer Temp ($T_{\\text{shock}}$)** | $12,362\\text{ K}$ | **$3,991.3\\text{ K}$** | $9,492.8\\text{ K}$ | **$-67.7\\%$** |
| **Radiative Surf Temp ($T_{\\text{surf}}$)** | $1,453\\text{ K}$ | **$1,675\\text{ K}$** | $1,453\\text{ K}$ | $+222\\text{ K}$ |
| **Backside Payload Temp ($T_{\\text{back}}$)** | $\\le 350\\text{ K}$ | **$338.5\\text{ K}$** | $341.2\\text{ K}$ | PASS ($\\le 350\\text{ K}$ limit) |
| **Generated CAD \\& Mesh Artifacts** | `HIAD_custom_full.step` | `geometry.step` | `geometry.step` | 3D STEP \\& STL Produced |

<div style="margin-top: 1.5rem; display:flex; gap:1rem; flex-wrap:wrap; justify-content:flex-end;">
    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(24)">View Genetic Search Dynamics &rarr;</a>
</div>
'''
    }
