# StellarOrion Hypersonic Simulation: Self-Note on Parameters

This document serves as a reference for all parameters used in the `gui_backend.py` logic, specifically for **Hypersonic Payload Protection** (HIAD survivability) and **Hypersonic Transport** optimization.

---

## 1. Geometric Design Parameters (Payload Protection)
These parameters define the physical shape of the Hypersonic Inflatable Aerodynamic Decelerator (HIAD).

| Parameter | Default | Range | Purpose / Use Case |
| :--- | :--- | :--- | :--- |
| `diameter` | 3.0 m | 2.5 – 4.5 m | **Drag Area:** Controls $A_{ref}$. Larger diameters reduce $\beta$, allowing for higher-altitude deceleration. |
| `angle` (Cone Angle) | 60.0° | 10° – 85° | **Stability & Drag:** Steeper angles increase axial force ($f_x$) but may affect aerodynamic stability. |
| `nose_radius` | 0.191 m | 0.14 – 0.24 m | **Thermal Protection:** Controls shock standoff. A larger nose spreads the Kinetic Energy flux ($ke$). |
| `toroids` | 7 | 3 – 10+ | **Structural:** Inflatable rings. More toroids improve shape retention under high pressure. |
| `thickness` | 0.02 m | 0.01 – 0.03 m | **Insulation ($\delta_{TPS}$):** Crucial for preventing heat soak to the payload. |
| `scallop_pts` | 5 | 2 – 7 | **Fidelity:** Number of segments in the inflatable surface. Affects local flow turbulence. |
| `scallop_angle` | 90.0° | 75° – 105° | **Surface Aero:** Curvature of lobes. Affects heating concentrations. |
| `mass` | 281.0 kg | 231 – 331 kg | **Ballistic Loading:** Directly impacts $\beta$ and instantaneous g-load ($n$). |

---

## 2. Environmental & Transport Parameters
These define the flight regime and atmospheric conditions (Hypersonic/VLEO).

| Parameter | Value | Purpose / Impact |
| :--- | :--- | :--- |
| `env_vstream` | ~10,500 m/s | **Entry Velocity ($v_{\infty}$):** Determines intensity of the shock layer. |
| `env_nrho` | 3.9e20 /m³ | **Number Density ($n_{\rho}$):** Atmospheric density at altitude. |
| `env_duration` | 450.0 s | **Heat Pulse ($\Delta t$):** Exposure time to peak heating. |
| `env_chem_mode` | 5 / 11 sp. | **Gas Kinetics:** Neutral Air vs Ionized Plasma (for $ke$ calculation). |
| `env_thermal_lag` | 15.0% | **Heat Soak ($\eta_{lag}$):** Percentage of heat penetrating to backface. |
| `env_temp_inf` | 200.0 K | **Ambient Temp:** Baseline upper atmosphere temperature. |

---

## 3. Derived Metrics (Survivability Criteria)
Metrics used to determine if the payload is "protected."

*   **Ballistic Coefficient ($\beta$):** $\beta = \frac{m \cdot q}{F_{drag}}$ [$kg/m^2$]. Lower is safer for landing.
*   **Peak Stagnation Heat:** $\dot{q} = \frac{Q_{total}}{A_{ref}}$ [$W/m^2$]. Must stay below material limits.
*   **Backface Temperature:** $T_{back} = T_{init} + \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{TPS} \cdot C_{p,TPS} \cdot \delta_{TPS}}$. Target: $< 350K$.
*   **G-Load:** $n = \frac{F_{drag}}{m \cdot g_0}$. Deceleration load in units of Earth gravity.

---

## 5. Case-Specific Optimization & Adjustments

Depending on the mission profile, different parameters must be prioritized.

### A. Artemis (Lunar/Deep Space Return)
*   **Quest:** High-speed return of high-value samples or crew from Lunar orbit to Earth.
*   **Payload:** Crew Capsule / Lunar Regolith Samples.
*   **Target Regime:** High-energy Earth reentry (~11.0+ km/s).
*   **Key Adjustments:**
    *   `env_chem_mode`: Set to **11-species**. At lunar return speeds, atmospheric ionization is significant and affects heat flux.
    *   `thickness`: Increase to **max (0.03m)**. The total heat load from deep space is significantly higher than LEO.
    *   `nose_radius`: Increase to spread the heat.
*   **Reasoning:** The primary threat is **Thermal Failure**. Optimization must focus on minimizing `backface_temp` and `surface_temp`.

### B. Satellite Payload (VLEO / Deorbiting)
*   **Quest:** Maintain sustained orbit in the Very Low Earth Orbit (VLEO) regime or ensure clean deorbiting of spent satellites.
*   **Payload:** SmallSat Bus / Communication Satellite (e.g., Starlink-class).
*   **Target Regime:** High-altitude maintenance or end-of-life disposal.
*   **Key Adjustments:**
    *   `diameter`: Increase to **max (4.5m)** for deorbiting; minimize for maintenance.
    *   `env_nrho`: Set to low density (high altitude).
    *   `mass`: Usually lower than heavy entry vehicles.
*   **Reasoning:** For deorbiting, the goal is **Aerodynamic Braking** (maximize drag). For VLEO maintenance, the goal is **Drag Reduction** to save on-board propellant.

### C. Mars Entry (Interplanetary Transport)
*   **Quest:** Delivery of heavy scientific equipment or infrastructure to the surface of Mars.
*   **Payload:** Mars Rover / Pre-positioned Habitat / Power Plant.
*   **Target Regime:** Thin $CO_2$ atmosphere.
*   **Key Adjustments:**
    *   `env_preset`: Set to **Mars**.
    *   `diameter`: Set to **max (4.5m)**.
    *   `angle`: Use a shallower cone angle for higher lift-to-drag ($L/D$) ratios.
*   **Reasoning:** Mars has 1% of Earth's surface density. A very low **Ballistic Coefficient ($\beta$)** is required to decelerate enough for a safe landing before hitting the surface.

### D. Human Transport (Crewed Mission)
*   **Quest:** Safely return human occupants within specific biological g-load and thermal tolerances.
*   **Payload:** 4-6 Astronauts + Life Support Systems.
*   **Target Regime:** Low-g Earth reentry.
*   **Key Adjustments:**
    *   `angle`: Optimize for high drag to slow down early in the upper atmosphere.
    *   `mass`: Higher due to life support systems.
*   **Reasoning:** Human survivability is limited by **G-Load**. Optimization must ensure `g_load` stays below **10g** throughout the trajectory.

### E. Reusable Orbital Transport (Orbital Tug)
*   **Quest:** Multi-trip orbital ferry services for LEO-to-GEO transfers and refueling logistics.
*   **Payload:** Propellant Tanker / Satellite Servicing Robotic Arms.
*   **Target Regime:** Multi-pass aero-braking for orbit circularization and refueling logistics.
*   **Key Adjustments:**
    *   `diameter`: Deploy to **max** during aero-braking; retract or minimize during cruise to reduce unwanted drag.
    *   `thickness`: Optimized for **thermal cycling**. Multi-entry durability requires keeping the peak `surface_temp` below the ablation threshold.
    *   `nose_radius`: Large radius to maximize shock standoff and minimize peak heat flux.
*   **Reasoning:** The primary goal is **Delta-V Savings**. Using the HIAD for aero-capture or aero-braking reduces the required propellant mass for orbital changes.

### F. Emergency Reentry Retrofit ("Lifeboat" Mode)
*   **Quest:** Immediate evacuation and survivability during an unplanned orbital failure.
*   **Payload:** Critical Crew / Essential Flight Data / Seed Bank.
*   **Target Regime:** High-stress, unplanned reentry due to orbital failure or system malfunction.
*   **Key Adjustments:**
    *   `diameter`: Force to **absolute maximum** (4.5m+). This is the "parachute" of the hypersonic regime.
    *   `angle`: Optimize for **max drag coefficient ($C_D$)** rather than stability.
    *   `thickness`: Maximize for thermal insulation.
*   **Reasoning:** In a failure scenario (e.g., failed propulsion), the vehicle may enter at a steep flight-path angle. The only way to prevent burn-up is to **decelerate as high as possible**. Optimization focuses on minimizing the **Ballistic Coefficient ($\beta$)** to its physical limit.

### G. Mission Atlas (Heavy Cargo / Mega-Scale Delivery)
*   **Quest:** Primary heavy-lift delivery of massive infrastructure modules for planetary colonization.
*   **Payload:** 20-ton Industrial Equipment / Modular Base Sections / Large Fuel Reservoirs.
*   **Target Regime:** Maximum-load planetary entry (Earth or Mars).
*   **Key Adjustments:**
    *   `diameter`: Extreme scale (15m - 20m+).
    *   `toroids`: Significantly increased ring count (12+) for maximum structural stiffness.
    *   `mass`: 20,000kg - 50,000kg.
*   **Reasoning:** Scalability is the unique advantage of the HIAD for **heavy lift**. Optimization focuses on **Structural Stiffness** to prevent torus buckling under the extreme dynamic pressure generated by such a massive payload.

### H. Commercial Space Tourism (Mature Technology Phase)
*   **Quest:** Provide a premium, ultra-safe, and high-comfort reentry experience for civilian passengers.
*   **Payload:** 6-8 Space Tourists + Luxury Cabin + Life Support.
*   **Target Regime:** Ultra-low-g orbital or suborbital Earth return.
*   **Key Adjustments:**
    *   `angle`: Optimized for a **shallow, gradual deceleration profile** to minimize peak physiological stress.
    *   `nose_radius`: Maximized to reduce peak stagnation heating and acoustic vibration.
    *   `thickness`: Increased for massive safety margins and redundancy in backface thermal protection.
*   **Reasoning:** For non-professional passengers, the priority is **Human Comfort (G-Limit)**. Optimization must ensure that the peak `g_load` remains below **3g - 4g**, providing a "soft" landing experience similar to a commercial aircraft descent rather than a traditional ballistic reentry.

---

## 6. Strategy: DSMC MoP-SBO vs. Continuum CFD (Ansys / OpenFOAM)
A common question is why this pipeline uses **DSMC + MoP-SBO** instead of a standard **Ansys Fluent** or **OpenFOAM** optimization loop.

| Feature | DSMC MoP-SBO (StellarOrion) | Continuum Solvers (Fluent / OpenFOAM) |
| :--- | :--- | :--- |
| **Flow Physics** | **Rarefied & Transitional:** Accurate for high-altitude/VLEO where $Kn > 0.01$. | **Continuum:** Accuracy drops as density decreases (Navier-Stokes fails). |
| **Optimization Speed** | **Near-Instant:** MoP surrogate allows 1,000+ iterations in seconds after training. | **Slow:** Each iteration requires a new 30-60 min CFD convergence. |
| **Non-equilibrium** | Handles thermochemical non-equilibrium at the particle level naturally. | Requires complex, semi-empirical tuning of reaction constants. |
| **Dimensionality** | **2D Axisymmetric:** Optimized for HIAD symmetry; 100x faster than 3D. | **2D/3D Available:** Even in 2D, full CFD convergence is orders of magnitude slower than MoP. |
| **Hardware / Acceleration** | **Hybrid Logic:** **Docker Linux** (SPARTA Physics) + GPU/NPU (MPS, CUDA, ROCm, OneAPI) for SBO. | **Standard:** Primarily CPU-bound; GPU acceleration is often limited or requires high-end solver licenses. |
| **Pros** | High fidelity in rarefied flow; Extreme optimization speed; Zero license costs; Hardware-agnostic acceleration. | High fidelity in dense atmosphere; Industry-standard for subsonic/supersonic; Extensive GUI tools. |
| **Cons** | Requires initial "training" samples; Less accurate in dense, low-altitude subsonic regimes. | Prohibitively slow for large-scale optimization; Expensive licenses (Fluent); High complexity (OpenFOAM). |

### Rationale for Selection:
1. **Survival Envelope:** HIADs start decelerating at altitudes where the air is too thin for the continuum assumptions used in Fluent or OpenFOAM. DSMC (SPARTA) captures the true kinetic behavior of the gas.
2. **Hardware-Agnostic Hybrid Support:** StellarOrion is built for modern cross-platform development. It leverages a **Hybrid CPU+GPU Architecture**:
    *   **Physics (CPU):** SPARTA runs on **Docker Linux** to ensure a high-performance, reproducible environment regardless of the host OS (macOS/Windows/Linux).
    *   **Optimization (GPU/NPU):** The MoP-SBO loop uses PyTorch with support for **Apple Metal (MPS)**, **NVIDIA CUDA**, **Intel OneAPI**, and **AMD ROCm**. This ensures high-speed optimization on everything from a MacBook Pro to a data center cluster.
3. **SPARTA vs. OpenFOAM (dsmcFoam+):** While OpenFOAM has a DSMC solver, **SPARTA (Sandia National Labs)** is purpose-built for high-performance DSMC. It offers significantly better parallel scaling and a more robust implementation of the VSS/VHS collision models and surface chemistry required for hypersonics.
4. **MoP/SBO Efficiency:** To find the *optimal* cone angle or nose radius, we need to test thousands of variations. While Fluent and OpenFOAM *can* run in 2D to save time, a full CFD convergence still takes minutes. The **Metamodel of Optimal Prognosis (MoP)** allows us to "learn" the physics and then run 10,000+ virtual "tests" in milliseconds.
5. **Axisymmetric Optimization:** Since the HIAD is a body of revolution, 2D axisymmetry is the "gold standard" for early-stage design. The StellarOrion pipeline leverages this to generate the massive datasets needed for high-fidelity surrogate models that would be computationally prohibitive with traditional CFD.

---

## 7. Technology Review: Pros & Cons of Inflatable HIAD
The **Hypersonic Inflatable Aerodynamic Decelerator (HIAD)** is a paradigm shift from traditional rigid aeroshells.

### Pros
*   **Volumetric Efficiency:** Can be stowed in a compact volume (e.g., a 0.5m fairing) and deployed to a 3m-15m+ diameter. This bypasses the physical limits of rocket fairing sizes.
*   **Low Ballistic Coefficient ($\beta$):** The large surface area allows the vehicle to decelerate in the **upper atmosphere** (thinner air). This significantly reduces peak heat flux and total heat load.
*   **Mass Savings:** Inflatable structures and Flexible TPS (F-TPS) are orders of magnitude lighter than monolithic rigid ceramic or metallic heat shields.
*   **Mission Versatility:** Ideal for thin atmospheres (Mars), high-energy returns (Artemis), and orbital maintenance (VLEO) where mass and drag control are critical.

### Cons
*   **Structural Fidelity:** The "scalloped" nature of the inflatable toroids can cause local heating concentrations and flow turbulence that are harder to model than smooth rigid surfaces.
*   **System Complexity:** Requires high-reliability inflation systems, gas generators, and structural tendons. A single puncture or valve failure can lead to loss of mission.
*   **Thermal Limits:** Flexible materials have lower absolute temperature limits compared to advanced rigid carbon-carbon or ablative materials.
    *   *Example:* **Silicon Carbide (SiC) fabrics** used in F-TPS are limited to **~1,470 K - 1,870 K**. In contrast, rigid ablators like **PICA (Phenolic Impregnated Carbon Ablator)** can survive **2,770 K+** during high-energy interplanetary returns.
*   **Dynamic Stability:** Inflatable structures can exhibit "breathing" or aero-elastic fluttering under high dynamic pressure, which complicates the aerodynamic stability derivatives.
