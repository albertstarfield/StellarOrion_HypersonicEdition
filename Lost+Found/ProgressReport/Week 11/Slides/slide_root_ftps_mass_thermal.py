# slide_root_ftps_mass_thermal.py

def get_slide_data():
    return {
        "id": "slide_root_ftps_mass_thermal",
        "title": "Flexible TPS (FTPS) Multi-layer Mass & Heat Conduction Model",
        "category": "Thermal Protection System",
        "content": r"""
# Flexible Thermal Protection System (FTPS) Laminate Model

*Multilayer Thermal Insulation & Mass Methodology from `SHIELD_MASS_METHODOLOGY.md`*

---

## 1. Multi-Layer FTPS Laminate Stack Architecture

The HIAD Flexible Thermal Protection System (FTPS) comprises three functional layers:

1. **Outer Fabric Layer (Nextel 440 / Vectran Weave):**
   - Resists aerodynamic erosion, extreme shear stress, and direct shock radiation ($T_{\text{max}} \sim 1,400\text{ K}$).
2. **Insulation Core Layer (Pyrogel 2250 Aerogel Blankets):**
   - Ultra-low thermal conductivity ($k = 0.015\text{ W/m}\cdot\text{K}$), density $\rho = 130\text{ kg/m}^3$.
3. **Gas Barrier Layer (Kapton / Polyurethane Film):**
   - Prevents hot gas ingestion into structural inflatable toroids ($T_{\text{max}} \sim 500\text{ K}$).

---

## 2. 1D Transient Non-Linear Heat Conduction Equation
Thermal transport through the FTPS thickness ($z$) is governed by the 1D non-linear heat equation:

$$\rho(z) c_p(T) \frac{\partial T}{\partial t} = \frac{\partial}{\partial z} \left( k(T, p) \frac{\partial T}{\partial z} \right) + \dot{q}_{\text{rad}}$$

Boundary conditions:
- **Surface ($z = 0$):** Convective heating $q_{\text{conv}}$ balanced by surface re-radiation:
  $$-k \left. \frac{\partial T}{\partial z} \right|_{z=0} = q_{\text{stag}} - \epsilon \sigma T_{\text{surf}}^4$$
- **Toroid Interface ($z = \delta_{\text{FTPS}}$):** Insulation limit $T_{\text{inner}} \le 523\text{ K}$ ($250^\circ\text{C}$).

---

## 3. Mass vs Thermal Protection Optimization Trade-off
The optimization balances minimum total insulation mass against thermal safety margin:

$$\text{Minimize } m_{\text{FTPS}} = A_{\text{surf}} \cdot (\rho_{\text{outer}} \delta_{\text{outer}} + \rho_{\text{pyrogel}} \delta_{\text{pyrogel}} + \rho_{\text{barrier}} \delta_{\text{barrier}})$$
$$\text{Subject to } T_{\text{inner, max}} \le 523\text{ K}$$
"""
    }
