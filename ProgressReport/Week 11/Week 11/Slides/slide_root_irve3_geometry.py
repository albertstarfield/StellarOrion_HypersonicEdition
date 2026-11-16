# slide_root_irve3_geometry.py

def get_slide_data():
    return {
        "id": "slide_root_irve3_geometry",
        "title": "HIAD IRVE-3 Flight Geometry & Peak Trajectory Calibration",
        "category": "Flight Calibration Baseline",
        "content": r"""
# HIAD IRVE-3 Flight Test Baseline Calibration

*Flight Test Calibration Data from `HIAD_IRVE3_Baseline.md` (NASA TM-2014-218525 / AIAA 2013-3162)*

---

## 1. Mission Overview
- **Mission:** NASA IRVE-3 (Inflatable Re-entry Vehicle Experiment 3)
- **Flight Date:** July 23, 2012 (Wallops Flight Facility)
- **Launch Vehicle:** Black Brant XI Sounding Rocket (Apogee $469\text{ km}$)
- **Primary Mission Goal:** Demonstrate hypersonic survivability of a $3.0\text{m}$ inflatable aeroshell under peak heat flux $> 12\text{ W/cm}^2$.

---

## 2. Definitive Geometric Parameters

| Geometric Parameter | Flight Nominal Value | MDAO Model Parameter |
| :--- | :--- | :--- |
| **Aeroshell Outer Diameter ($D$)** | $3.00\text{ m}$ | Baseline $D = 3.0\text{ m}$ |
| **Nose Radius ($R_n$)** | $0.550\text{ m}$ | Sphere-Cone Curvature $R_n$ |
| **Forebody Cone Half-Angle ($\theta_c$)** | $60.0^\circ$ | Cone Half-Angle $\theta_c$ |
| **Toroid Stack Count** | 6 Toroids | Toroid Stack $N_{\text{toroid}} = 6$ |
| **Major Toroid Radius ($r_{\text{torus}}$)** | $0.1350\text{ m}$ | Rapisarda Baseline $r_{\text{torus}}$ |
| **Outer Edge Toroid Radius** | $0.0508\text{ m}$ | Outer Lip Radius |
| **Payload Structure Mass ($m_0$)** | $281.0\text{ kg}$ | Total Entry Mass |

---

## 3. Flight Calibration Peak Results vs SPARTA DSMC

| Trajectory Parameter | IRVE-3 Flight Reconstruction | SPARTA DSMC Baseline Model |
| :--- | :--- | :--- |
| **Mach Number ($M_\infty$)** | $9.0$ | $9.0$ |
| **Freestream Velocity ($V_\infty$)** | $2,700\text{ m/s}$ | $2,700\text{ m/s}$ |
| **Peak Dynamic Pressure ($q_\infty$)** | $8.4\text{ kPa}$ | $8.4\text{ kPa}$ |
| **Peak Stagnation Heat Flux ($q_{\text{stag}}$)** | $14.36\text{ W/cm}^2$ | $14.36\text{ W/cm}^2$ |
| **Drag Coefficient ($C_D$)** | $1.47$ (Continuum) | $1.62$ (Rarefied Kinetic DSMC) |
"""
    }
