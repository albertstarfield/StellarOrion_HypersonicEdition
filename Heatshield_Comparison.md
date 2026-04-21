# Hypersonic Heatshield Technology: Comparison & Selection

This document summarizes the different types of Thermal Protection Systems (TPS) for hypersonic reentry and justifies the selection of **HIAD (Hypersonic Inflatable Aerodynamic Decelerator)** as the primary technology for the StellarOrion project.

## 1. Heatshield Types (Industry Standards)

Based on the initial progress report findings and NASA heritage, the following TPS types are commonly utilized:

| Type | Material / Mechanism | Characteristics | Limitations |
| :--- | :--- | :--- | :--- |
| **Ablative** | PICA, Avcoat, Carbon-Phenolic | Traditional; removes heat by melting/charring (chemical erosion). | **Single-use only.** High mass; requires total replacement after reentry. |
| **Rigid Ceramic (Tiles)** | LI-900 (Shuttle), CMCs, UHTCs | Reusable; high-temperature insulation (up to 2000°C). | **High Maintenance.** Brittle; prone to impact damage; restricted by fairing diameter. |
| **Active Cooling** | Transpiration (Porous skin), Heat Pipes | High-tech; pumps fluid or uses phase change to remove heat. | **Extreme Complexity.** High risk of failure; significant mass penalty for plumbing/pumps. |
| **HIAD (Inflatable)** | Flexible TPS (SiC/Alumina fabrics) + Inflatable Toroids | **Deployable.** Stows compactly; expands to large diameter for low-density deceleration. | Flexible geometry complicates local flow modeling (requires high-fidelity DSMC). |

---

## 2. Why HIAD? (The StellarOrion Choice)

The StellarOrion project selects **HIAD** over traditional rigid or active systems for the following technical reasons:

### A. Volumetric Efficiency & Scalability
Rigid shields are physically constrained by the width of the launch vehicle fairing (e.g., a 5m fairing can only fit a 4.5m rigid shield). HIADs bypass this limit; a system stowed in a 1m volume can deploy to a **6m to 15m diameter**, enabling the transport of massive payloads to Mars or Earth.

### B. Safety through Rarefaction (The Low-Beta Advantage)
Because a HIAD can deploy to a very large area, it has a significantly lower **Ballistic Coefficient ($\beta$)**. 
*   **Physics:** It starts decelerating much higher in the atmosphere (rarefied regime).
*   **Result:** Peak heating is lower because the vehicle slows down before hitting the denser, high-friction layers of the atmosphere.

### C. The "Hypersonic Lifeboat" (Emergency Backup)
Unlike rigid shields that must be part of the primary airframe, a HIAD can be stowed as an **emergency backup system**. If a primary shield (like the Orion Avcoat) shows damage in orbit (as seen in Artemis I), a HIAD "Pod" can be deployed as a redundant entry system, ensuring crew and payload survival.

### D. Lower Maintenance & Reusability
While rigid tiles (Space Shuttle) require thousands of manual inspections for cracks, the **Flexible TPS** of a HIAD is designed for modular refurbishment. The inflatable structure is protected by the F-TPS and can be reused, significantly lowering the "cost per return" compared to single-use ablative capsules.

### E. Human-Rated Scalability (Crew Evolution)
The project baseline originates from the **IRVE-3 (3.0m)** suborbital testbed. However, the ultimate objective of StellarOrion is to optimize this technology for **6.0m to 9.0m+** scales capable of carrying crew capsules (Artemis-class). Unlike rigid shields, which require a larger rocket to increase shield size, HIADs can scale the protected volume without requiring massive changes to the launch vehicle's aerodynamic fairing.

## References
1. *SummarizationLearning.md* - ProgressReport/Initial.
2. Johnston, C. O. (2025). Including Radiative Heating for the Design of the Orion Backshell for Artemis-1. *Journal of Spacecraft and Rockets*, *62*(1), 1-15.
3. Lippincott, J. J., et al. (2019). LOFTID Mission Overview. *AIAA 2019-3525*.
4. Gill, T. R., et al. (2026). The Test Like You Fly and Test What You Fly Approach for the Artemis Human Spaceflight Paradigm. *AIAA SciTech 2026 Forum*.
