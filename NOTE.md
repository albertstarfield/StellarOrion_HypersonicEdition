# Calibration Note: HIAD IRVE-3 Reference

This project utilizes the **NASA IRVE-3 (Inflatable Reentry Vehicle Experiment 3)** as the primary baseline for default GUI parameters and simulation calibration.

## Default Parameter Mapping

| Parameter | GUI Default | IRVE-3 Value | Rationale |
| :--- | :--- | :--- | :--- |
| **Major Diameter** | 3.0 m | 3.0 m | Exact match to the IRVE-3 inflated outer diameter. |
| **Cone Angle** | 60.0° | 60.0° | Standard sphere-cone half-angle used in the flight test. |
| **Nose Radius** | 0.191 m | 0.191 m | Radius of the rigid centerbody (nose cap) used in IRVE-3. |
| **Toroid Count** | 7 | 7 | Typical stack count for a 3m HIAD to maintain structural lofting. |
| **Shield Mass** | 281 kg | 281 kg | Exact match to IRVE-3 entry mass. |
| **Ballistic Coeff (β)** | 27 kg/m² | ~27 kg/m² | Aligned with IRVE-3 flight data for sounding rocket reentry. |

## Why IRVE-3?
The IRVE-3 mission (launched July 23, 2012) is the most successful flight validation of HIAD technology to date. 
- **Thermal Calibration**: The default wall temperature (1000K) and stagnation heat targets are anchored in the IRVE-3 TPS performance data.
- **Structural Integrity**: The toroid geometry and scallop angles are derived from the braided Kevlar tori specifications of the IRVE-3 aeroshell.
- **DSMC Fidelity**: Freestream density (`nrho`) and temperature defaults are set to approximate the mesospheric conditions (80km altitude) where IRVE-3 began its primary data collection.

## Optimization Strategy
When using the "High-Fidelity SBO" mode, the optimization targets for heat flux and g-load are initially set to 1.5x IRVE-3 limits to allow the metamodel to explore "Survivability Envelopes" for future Mars-scale missions (e.g., LOFTID).
