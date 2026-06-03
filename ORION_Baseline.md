# ORION Baseline Flight Results

This document establishes the official flight test baseline for the **Orion Crew Module**, which serves as a rigid-body validation case for the StellarOrion Hypersonic Simulation Suite.

## 1. Mission Overview
*   **Mission Name**: Orion EFT-1 / Artemis I
*   **Launch Vehicle**: Delta IV Heavy / SLS
*   **Primary Objective**: Demonstrate survivability of the Orion aeroshell and Avcoat thermal protection system at lunar-return or high-energy entry velocities.

## 2. Geometric Baseline
| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Aeroshell Diameter** | 5.02 m | Maximum diameter |
| **Nose Radius ($R_n$)** | ~0.3 m | Stagnation point curvature (spherical segment) |
| **Forebody Shape** | Spherical Segment | Apollo-style capsule geometry |
| **Mass** | ~10,400 kg | Nominal flight mass |

## 3. Flight Performance Parameters (Peak Results)
The following values are derived from EFT-1 and post-flight reconstructions.

| Metric | Result | Note |
| :--- | :--- | :--- |
| **Entry Velocity** | Mach ~32 | ~8,900 m/s (EFT-1) to 11,000 m/s (Artemis I) |
| **Peak Heat Flux ($\dot{q}$)** | ~1,000 W/cm² | Stagnation point heating |
| **Peak Deceleration** | ~8-9 g | Total aerodynamic load |
| **Ballistic Coefficient ($\beta$)** | ~400 kg/m² | High ballistic coefficient (Rigid capsule) |
| **Time of Peak Heating** | ~T+XXX s | Re-entry timeline |

## 4. Optimization Reference Points (Validation Check)
Use these values to calibrate the **Survivability Optimization (SBO)** targets in StellarOrion.

| Metric | ORION Baseline | Note |
| :--- | :--- | :--- |
| **Target $\beta$** | ~400 kg/m² | Validates Mass/Drag ratio |
| **Target $\dot{q}_{max}$** | 1000 W/cm² | Validates Aerothermal Model |
| **Reference $C_D$** | ~1.2 - 1.3 | Validates Forebody Drag for blunt body |

## 5. Key Findings & Validation Metrics
*   **TPS Performance**: The Avcoat ablative heat shield performed nominally during the peak heating phase.
*   **Aerodynamic Stability**: The capsule maintained a stable trim angle of attack to generate required lift.
*   **Center-of-Gravity (CG) Offset**: Used to generate an L/D ratio of ~0.27 for skip-entry and precision landing.

## 6. DSMC Simulation Enhancements (SPARTA)
To ensure absolute mathematical stability and robustness during the Direct Simulation Monte Carlo (DSMC) runs, **Adaptive Mesh Refinement (AMR)** has been completely disabled in our framework for the ORION baseline. 

*   **Zero-Volume Cut-Cell Exception**: When utilizing `fix adapt_grid` on complex, curved CAD models (like the Orion capsule), the dynamic mesh refinement inevitably produces microscopic "sliver" cut-cells with near-zero fluid volumes at the exact intersection vertices between the Cartesian grid and the curved boundary. When high-energy particles enter these slivers, it triggers an unrecoverable divide-by-zero crash (`Collision cell volume is zero`) within the SPARTA collision kernel.
*   **Static Grid Stabilization**: To mitigate this, we rely on a statically scaled, high-resolution uniform grid (e.g., 279x279 odd-numbered bounds) explicitly shifted by several millimeters to completely decouple the CAD surface from the grid cell corners.
*   **Orchestrator Conflict Mitigation**: By disabling AMR, we also prevent the multi-instance Python orchestrator from losing synchronization during restart states (where SPARTA `read_restart` inherently fails to seamlessly preserve dynamic `group` assignments and surface collision models).
*   **Dynamic Load Balancing (`fix balance_grid`)**: While AMR is disabled, Recursive Coordinate Bisection (RCB) load balancing is still actively used to continuously redistribute particle and static grid memory structures evenly across all parallel CPU cores.
*   **Domain Boundary Optimization (X-Span)**: The highly restricted geometric domain bounds (specifically tightening the X-axis span to unusual dimensions like `[-1.69m, 2.00m]` instead of a standard large control volume) are deliberately employed to combat limited computational resources and strict development timelines. By aggressively clipping the empty vacuum of the free-stream and the expansive aft wake region, we massively reduce the total required grid cell and active particle count, enabling significantly faster simulation throughput.

## 7. HIAD Geometry Integration & Auto-Scaling
To ensure mathematical and physical validity during SBO (Surrogate-Based Optimization) integration, the HIAD generator enforces strict geometric constraints relative to the payload object being protected:
*   **Minimum Diameter Multiplier (1.5x Rule)**: The inflatable heat shield must expand to a minimum diameter of exactly $1.5\times$ the target object's base diameter. For the 5.0m Orion capsule, the absolute minimum allowable HIAD diameter is **7.5 meters**. This strict lower bound guarantees that the trailing hypersonic boundary layer and expanding plasma wake do not physically overlap or incinerate the aft edges of the capsule.
*   **Flush Nose Tangency**: The spherical nose curvature of the HIAD is dynamically auto-calculated to ensure its outer tangency coordinates bridge onto the geometric rim of the Orion capsule, merging the capsule's blunt heatshield and the HIAD toroids into a single continuous aerodynamic surface without clipping or gaps.
## 8. Aerodynamic Rationale for HIAD Integration
Even though the Orion capsule possesses a highly capable rigid ablative heat shield (AVCOAT) at its stagnation point, integrating a Hypersonic Inflatable Aerodynamic Decelerator (HIAD) provides critical mission capabilities:

1.  **The Ballistic Coefficient ($\beta$)**: The primary job of a HIAD is not actually to block heat at the nose—it's to act as a hypersonic parachute. By expanding the diameter from 5.0m to 8.5m, we almost triple the surface area ($A$) of the vehicle without adding much mass ($m$). This drastically lowers the vehicle's ballistic coefficient ($\beta = m / (C_D \cdot A)$).
2.  **High-Altitude Braking**: Because the vehicle is essentially a giant aerodynamic feather, it hits the "wall" of the atmosphere much higher up where the air is extremely thin. It bleeds off all of its orbital velocity in the upper stratosphere.
3.  **Saving the Rigid Heat Shield**: If an Orion capsule returns from a Mars or deep-space trajectory, it hits the atmosphere at 11 to 13 km/s. If it used its stock 5.0m heat shield, it would plunge deep into the thick, dense lower atmosphere while still moving at Mach 30. The friction and plasma density would instantly incinerate the AVCOAT ablator. By deploying the HIAD, the vehicle slows down in the thin upper atmosphere. By the time it reaches the thicker air, it has already lost its dangerous kinetic energy. The stagnation point is still on the Orion (or the HIAD's aerodynamic center), but the peak temperature and heat flux it experiences are slashed by orders of magnitude.
4.  **Plasma Wake Protection**: The 8.5m skirt pushes the massive, superheated plasma wake far away from the aft conical body of the capsule. The trailing boundary layer is pushed out so wide that the crew module docking ports and aft walls never touch the searing hypersonic wake.

Ultimately, the HIAD is not deployed to replace the Orion's heat shield; it is deployed to **brake the vehicle before the Orion's heat shield melts**.

## References
1.  Johnston, C. O., et al., "EFT-1 Heatshield Aerothermal Environment Reconstruction," *NASA/AIAA Thermophysics Conference*.
2.  Bose, D., et al., "Exploration Flight Test 1 Afterbody Aerothermal Environment Reconstruction," *AIAA*.
3.  Prabhu, D. K., et al., "Orion Launch Abort System Performance on Exploration Flight Test–1," *NASA/AIAA*.
4.  Subramanian, V., et al., "Orion Exploration Flight Test-1 Post-Flight Navigation Performance Assessment Relative to the Best Estimated Trajectory," *AAS 16-143*.
