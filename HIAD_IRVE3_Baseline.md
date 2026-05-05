# HIAD IRVE-3 Baseline Flight Results

This document establishes the official flight test baseline for the **Inflatable Re-entry Vehicle Experiment 3 (IRVE-3)**, which serves as the primary validation case for the StellarOrion Hypersonic Simulation Suite.

## 1. Mission Overview
*   **Mission Name**: IRVE-3 (Inflatable Re-entry Vehicle Experiment 3)
*   **Flight Date**: July 23, 2012
*   **Launch Vehicle**: Black Brant XI (Sounding Rocket)
*   **Apogee**: 469 km
*   **Primary Objective**: Demonstrate survivability of a 3.0m HIAD aeroshell and Flexible Thermal Protection System (FTPS) at heat fluxes > 12 W/cm².

## 2. Geometric Baseline
| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Aeroshell Diameter** | 3.0 m | Fully inflated diameter |
| **Nose Radius ($R_n$)** | 0.191 m | Stagnation point curvature |
| **Forebody Shape** | 60° Sphere-Cone | 60-degree half-angle |
| **Toroid Count** | 7 (or 6*) | Baseline: 7; Rapisarda: 6 |
| **Toroid Radius ($r_{torus}$)** | 0.1350 m | Rapisarda (2024) Table 4.1 |
| **Outer Toroid Radius** | 0.0508 m | Rapisarda (2024) Table 4.1 |
| **Payload Height ($h_{pay}$)** | 1.7 m | Rapisarda (2024) Table 4.1 |
| **Payload Radius ($r_{pay}$)** | 0.275 m | Rapisarda (2024) Table 4.1 |
| **Mass** | 281.0 kg | Nominal flight mass |

## 3. Flight Performance Parameters (Peak Results)
The following values are derived from the post-flight reconstruction (NASA/TP-2013-4012 / AIAA 2013-1386) and high-fidelity modeling by Rapisarda (2024).

| Metric | Result | Note |
| :--- | :--- | :--- |
| **Entry Velocity** | Mach 10.0 | ~2,700 m/s |
| **Peak Heat Flux ($\dot{q}$)** | 14.36 W/cm² | Rapisarda Table 4.10 |
| **Total Heat Load ($Q_{max}$)** | 195.06 J/cm² | Rapisarda Table 4.10 |
| **Peak Deceleration** | 20.2 g | Total aerodynamic load |
| **Peak Dynamic Pressure ($q$)** | 6.2 kPa | ~0.9 psia |
| **Stagnation Pressure** | ~12.4 kPa | Estimated ($2 \times q$) |
| **Ambient Pressure (50km)** | 75.77 Pa | Rapisarda Table 4.5 |
| **Ambient Temp (50km)** | 270.65 K | Rapisarda Table 4.5 |
| **Ballistic Coefficient ($\beta$)** | 26.9 kg/m² | NASA/TP-2013-4012 |
| **Altitude of Peak Heating** | ~52 km | Atmospheric interface layer |
| **Time of Peak Heating** | 677.49 s | Rapisarda Table 4.10 |

## 4. Optimization Reference Points (Validation Check)
Use these values to calibrate the **Survivability Optimization (SBO)** targets in StellarOrion.

| Metric | IRVE-3 Baseline | Note |
| :--- | :--- | :--- |
| **Target $\beta$** | 26.9 kg/m² | Validates Mass/Drag ratio |
| **Target $\dot{q}_{max}$** | 14.36 W/cm² | Validates Aerothermal Model |
| **Target $g_{max}$** | 20.2 g | Validates Structural Load |
| **Target $q_{max}$** | 6.2 kPa | Validates Dynamic Pressure |
| **Reference $C_D$** | ~1.47 | Validates Forebody Drag |

## 5. Key Findings & Validation Metrics
*   **FTPS Performance**: The flexible TPS survived the peak heat flux without structural failure.
*   **Aerodynamic Stability**: The vehicle demonstrated stable flight throughout the hypersonic and supersonic regimes.
*   **Center-of-Gravity (CG) Offset**: Demonstrated the ability to generate lift for trajectory steering.

## 6. MDAO Reference (Rapisarda 2024) - Mesh Independence
The following parameters establish the mesh fidelity requirements used in the Rapisarda MDAO framework for Inflatable Stacked Toroids.

| Parameter | Value | Note |
| :--- | :--- | :--- |
| **Mesh Type** | 3D Surface Mesh | Delaunay Triangulation (Triangular Panels) |
| **Tested Meshes** | 9 configurations | Range: 1,694 to 54,446 triangles |
| **Convergence Point** | 30,000 triangles | $C_d$ stabilizes with < 1% variation |
| **Recommended Density** | $A_{panel} / A_{total} < 4 \times 10^{-4}$ | Normalised average panel area |
| **Simulation Speed** | < 0.6s per run | On standard research workstation |

*   **Key Finding**: $C_d$ is Mach-independent in the continuum regime (Modified Newtonian method), but highly sensitive to the shading algorithm and panel density on rounded features (nose/shoulder).

## References
1.  Cassell, G. J., et al., "Inflatable Re-entry Vehicle Experiment (IRVE-3) Flight Results," *AIAA 2013-1386*, 2013.
2.  Lau, K., Cheatwood, N., et al., "Inflatable Re-entry Vehicle Experiment 3 (IRVE-3) Post-Flight Aerothermal Reconstruction," *NASA/TP-2013-4012*.
3.  Rapisarda, C., "MDAO of Inflatable Stacked Toroids for Atmospheric Entry," *University of Strathclyde*, 2024.
