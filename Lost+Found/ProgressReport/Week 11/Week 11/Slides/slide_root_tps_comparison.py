# slide_root_tps_comparison.py

def get_slide_data():
    return {
        "id": "slide_root_tps_comparison",
        "title": "Hypersonic Heatshield Technologies Trade-off & HIAD Selection",
        "category": "Architectural Design Selection",
        "content": r"""
# Hypersonic Heatshield Technology Trade-Off & Selection

*Industry Standard Comparison & Technology Justification from `Heatshield_Comparison.md`*

---

## 1. Comparative Analysis of Re-entry Thermal Protection Systems

| TPS Technology | Primary Materials | Key Advantages | Major Engineering Limitations |
| :--- | :--- | :--- | :--- |
| **Ablative TPS** | PICA, Avcoat, Carbon-Phenolic | Proven flight heritage (Apollo, Orion, Stardust); absorbs massive heat via chemical charring. | **Single-use only**; heavy structural mass penalty; non-reusable. |
| **Rigid Ceramic Tiles** | LI-900 (Shuttle), CMCs, UHTCs | High-temperature insulation ($> 2,000^\circ\text{C}$); fully reusable. | **High maintenance**; brittle; rigid payload fairing diameter bottleneck ($< 5.0\text{ m}$). |
| **Active Cooling** | Porous transpiration, Heat pipes | Handles extreme heat flux spots; zero material erosion. | **Extreme complexity**; high risk of pump/plumbing clogging failure. |
| **HIAD (Inflatable)** | Flexible TPS + Inflatable Silicone Toroids | **Deployable aeroshell ($> 6.0\text{ m}$)**; low ballistic coefficient ($\beta$); dramatic mass savings. | Flexible geometry requires high-fidelity kinetic DSMC modeling. |

---

## 2. Why HIAD is the Superior Choice for StellarOrion MDAO
1. **Unconstrained Aeroshell Diameter:** Stows inside standard launch fairings ($D_{\text{stowed}} = 1.2\text{ m}$) and inflates in orbit to $D = 3.0\text{ m} - 6.0\text{ m}$.
2. **Deceleration at High Altitude:** Large drag area ($A_{\text{ref}}$) decelerates spacecraft at $h > 70\text{ km}$, reducing peak convective heat flux by up to 50%.
3. **MDAO Mass Savings:** Achieves $> 35\%$ structural mass reduction compared to rigid ablative heatshields for Mars and Earth re-entry missions.
"""
    }
