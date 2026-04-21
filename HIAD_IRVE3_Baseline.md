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
| **Toroid Count** | 7 | Structural inflatable rings |
| **Mass** | 281.0 kg | Nominal flight mass |

## 3. Flight Performance Parameters (Peak Results)
The following values are derived from the post-flight reconstruction (NASA/TP-2013-4012 / AIAA 2013-1386).

| Metric | Result | Note |
| :--- | :--- | :--- |
| **Entry Velocity** | Mach 10.0 | ~2,700 m/s |
| **Peak Heat Flux ($\dot{q}$)** | 14.4 W/cm² | Stagnation point (Theoretical) |
| **Peak Deceleration** | 20.2 g | Total aerodynamic load |
| **Peak Dynamic Pressure ($q$)** | 0.9 psia | ~6.2 kPa |
| **Peak Stagnation Pressure** | ~12.4 kPa | Estimated ($2 \times q$) |
| **Ballistic Coefficient ($\beta$)** | 26.9 kg/m² | NASA/TP-2013-4012 |
| **Altitude of Peak Heating** | ~52 km | Atmospheric interface layer |

## 4. Optimization Reference Points (Validation Check)
Use these values to calibrate the **Survivability Optimization (SBO)** targets in StellarOrion.

| Metric | IRVE-3 Baseline | Note |
| :--- | :--- | :--- |
| **Target $\beta$** | 26.9 kg/m² | Validates Mass/Drag ratio |
| **Target $\dot{q}_{max}$** | 14.4 W/cm² | Validates Aerothermal Model |
| **Target $g_{max}$** | 20.2 g | Validates Structural Load |
| **Target $q_{max}$** | 6.2 kPa | Validates Dynamic Pressure |
| **Reference $C_D$** | ~1.47 | Validates Forebody Drag |

## 5. Key Findings & Validation Metrics
*   **FTPS Performance**: The flexible TPS survived the peak heat flux without structural failure.
*   **Aerodynamic Stability**: The vehicle demonstrated stable flight throughout the hypersonic and supersonic regimes.
*   **Center-of-Gravity (CG) Offset**: Demonstrated the ability to generate lift for trajectory steering.

## References
1.  Cassell, G. J., et al., "Inflatable Re-entry Vehicle Experiment (IRVE-3) Flight Results," *AIAA 2013-1386*, 2013.
2.  Lau, K., Cheatwood, N., et al., "Inflatable Re-entry Vehicle Experiment 3 (IRVE-3) Post-Flight Aerothermal Reconstruction," *NASA/TP-2013-4012*.
3.  Dillman, R., "Inflatable Reentry Vehicle Experiment-3 (IRVE-3): Project Overview & Instrumentation," *NASA LaRC*, 2015.
