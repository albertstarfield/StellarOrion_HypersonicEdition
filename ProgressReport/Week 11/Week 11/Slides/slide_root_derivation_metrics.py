# slide_root_derivation_metrics.py

def get_slide_data():
    return {
        "id": "slide_root_derivation_metrics",
        "title": "Closed-Form Aerothermal & Drag Governing Equations",
        "category": "Theoretical Physics Derivations",
        "content": r"""
# Closed-Form Aerothermal & Drag Governing Equations

*Authoritative Formulation derived from `DERIVATION.md` for Hypersonic Inflatable Aerodynamic Decelerator (HIAD)*

---

## 1. Integrated Drag Force & Drag Coefficient
The total surface aerodynamic drag force ($F_{\text{drag}}$) is integrated across all DSMC surface elements:

$$F_{\text{drag}} = \sum_{i=1}^{N_{\text{elem}}} |f_{x,i}|$$

The non-dimensional Drag Coefficient ($C_D$) is defined as:

$$C_D = \frac{F_{\text{drag}}}{\frac{1}{2} \rho_\infty V_\infty^2 A_{\text{ref}}}$$

where $A_{\text{ref}} = \frac{\pi}{4} D_{\text{aeroshell}}^2 = 7.0686\text{ m}^2$ (for $D = 3.0\text{ m}$ IRVE-3 baseline).

---

## 2. Sutton-Graves Closed-Form Stagnation Heat Flux
Convective stagnation-point heat flux ($q_{\text{stag}}$) is modeled using the Sutton-Graves relation:

$$q_{\text{stag}} = C_s \sqrt{\frac{\rho_\infty}{R_n}} V_\infty^3$$

where:
- $C_s = 1.7415 \times 10^{-4} \text{ J}/(\text{m}^{1.5} \cdot \text{kg}^{0.5})$ (Earth atmospheric constant)
- $R_n = 0.550\text{ m}$ (Stagnation sphere-cone nose radius)
- Baseline flight condition ($M_\infty = 9.0, V_\infty = 2,700\text{ m/s}, \rho_\infty = 1.25 \times 10^{-4}\text{ kg/m}^3$) yields:

$$q_{\text{stag, baseline}} = 14.36 \text{ W/cm}^2$$

---

## 3. Ballistic Coefficient & Deceleration Dynamics
Vehicle entry deceleration dynamics are governed by the Ballistic Coefficient ($\beta$):

$$\beta = \frac{m}{C_D A_{\text{ref}}} \quad [\text{kg/m}^2]$$

- High $\beta \to$ Deeper atmospheric penetration, higher thermal peak ($q_{\text{stag}}$).
- Low $\beta \to$ Early high-altitude deceleration, reduced structural thermal load.

---

## 4. Flexible Thermal Protection System (FTPS) Mass Model
The total structural insulation mass ($m_{\text{FTPS}}$) is calculated by summing layer densities across total surface area ($A_{\text{surf}}$):

$$m_{\text{FTPS}} = A_{\text{surf}} \sum_{k=1}^{N_{\text{layers}}} \rho_k \cdot \delta_k$$

where $\delta_k$ is layer thickness and $\rho_k$ is layer material density (e.g. Pyrogel 2250 Aerogel $\rho = 130\text{ kg/m}^3$).
"""
    }
