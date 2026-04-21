# StellarOrion Hypersonic Simulation: Self-Note on Parameters

This document serves as a reference for all parameters used in the `StellarOrionEngineMach5Up.py` logic, specifically for **Hypersonic Payload Protection** (HIAD survivability) and **Hypersonic Transport** optimization.

---

## 0. Motivation & Objectives
The StellarOrion Hypersonic Edition is driven by the need for more resilient and accessible thermal protection systems (TPS).

*   **Increase Heatshield Availability**: Transitioning from monolithic, rigid shields to deployable HIAD structures that can be manufactured and deployed on-demand.
*   **Emergency Backup System**: Serving as a "Hypersonic Lifeboat." Providing a redundant, storable shield that can be deployed in orbit if the primary shield fails or if an unplanned reentry is required.
*   **Lower Maintenance Cost**: Reducing the logistical burden of tile-based TPS maintenance through flexible, inflatable architectures that require less ground infrastructure and manual inspection.
*   **Safety Margin Expansion**: Utilizing the large surface area of HIADs to decelerate higher in the atmosphere, significantly reducing the peak thermal stress on the vehicle structure (Johnston, 2025 / Gill et al., 2026).
*   **Reusable Orbit to Earth Transportation**: Developing a platform for sustainable, repeatable, and low-cost return of payloads and hardware from various orbital regimes (including LEO, HEO, and Lunar orbits) to Earth.
    *   *Reasoning:* Traditional systems suffer from the **dual-disposable problem**: (1) single-use ablative shields are destroyed during reentry, and (2) high peak heating often compromises the internal pod's structural longevity. HIAD technology enables **Reusable Pods** by using a refurbishable/swappable flexible TPS and decelerating at higher altitudes to keep the internal pod within benign thermal limits. (See [Heatshield_Comparison.md](file:///Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Heatshield_Comparison.md) for a detailed tech comparison).
*   **Scaling for Crew Survivability**: Evolving the technology from suborbital flight tests (**IRVE-3, 3.0m**) to crew-equipped orbital/lunar platforms (**Artemis scale, 6.0m+**). This requires optimizing the aerothermodynamics to ensure g-loads and internal temperatures stay within human physiological limits.

---

## 1. Geometric Design Parameters (Payload Protection)
These parameters define the physical shape of the Hypersonic Inflatable Aerodynamic Decelerator (HIAD).

| Parameter | Default | Range | Purpose / Use Case |
| :--- | :--- | :--- | :--- |
| `diameter` | 3.0 m | 2.5 – 4.5 m | **Drag Area:** Controls $A_{ref}$. Larger diameters reduce $\beta$, allowing for higher-altitude deceleration. |
| `angle` (Cone Angle) | 60.0° | 10° – 85° | **Stability & Drag:** Steeper angles increase axial force ($f_x$) but may affect aerodynamic stability. |
| `nose_radius` | 0.191 m | 0.14 – 0.24 m | **Thermal Protection:** Controls shock standoff. A larger nose spreads the Kinetic Energy flux ($ke$). |
| `toroids` | 7 | 3 – 10+ | **Structural:** Inflatable rings. More toroids improve shape retention under high pressure. |
| `thickness` | 0.0254 m | 0.01 – 0.04 m | **Insulation ($\delta_{TPS}$):** Crucial for preventing heat soak. 2.54cm (1 inch) is the IRVE-3/LOFTID baseline. |
| `scallop_pts` | 5 | 2 – 7 | **Fidelity:** Number of segments in the inflatable surface. Affects local flow turbulence. |
| `scallop_angle` | 90.0° | 75° – 105° | **Surface Aero:** Curvature of lobes. Affects heating concentrations. |
| `mass` | 281.0 kg | 231 – 331 kg | **Ballistic Loading:** Directly impacts $\beta$ and instantaneous g-load ($n$). |

---

## 2. Environmental & Transport Parameters
These define the flight regime and atmospheric conditions (Hypersonic/VLEO).

| Parameter | Value | Purpose / Impact |
| :--- | :--- | :--- |
| `env_vstream` | **2,700 m/s** | **Entry Velocity ($v_{\infty}$):** Mach 10 (IRVE-3 Baseline). |
| `env_nrho` | **3.5e22 /m³** | **Number Density ($n_{\rho}$):** At ~52km altitude (Earth). |
| `env_duration` | **60.0 s** | **Heat Pulse ($\Delta t$):** Typical suborbital exposure. |
| `env_chem_mode` | 5 / 11 sp. | **Gas Kinetics:** Neutral Air vs Ionized Plasma. |
| `env_thermal_lag` | **0.1%** | **Heat Soak ($\eta_{lag}$):** Penetration factor. |
| `env_temp_inf` | **270.0 K** | **Ambient Temp:** Stratopause/Mesosphere baseline. |

---

## 2.1. Gas Chemistry & Species Selection (The "Specimen")
The choice of gas species (the simulation "specimen") is critical for capturing the physics of the shock layer. As Mach number increases, the kinetic energy of the flow is converted into thermal and chemical energy (dissociation and ionization).

| Model Selection | Species List | Applicability / Use Case |
| :--- | :--- | :--- |
| **Earth: 5-Species** | N2, O2, NO, N, O | **Standard Hypersonic:** (Mach 5-15). Captures dissociation but assumes neutral gas. Baseline for IRVE-3 (NASA/TP-2013-4012). |
| **Earth: 11-Species** | Adds ions: N2+, O2+, NO+, N+, O+, e- | **High-Energy / Plasma:** (Mach > 15). Captures ionization. Required for Artemis Lunar Return (NASA 2022 / Johnston 2025). |
| **Mars: 6-Species** | CO2, N2, CO, O, C, N | **Mars Entry:** Handles CO2 dissociation. Critical for MSL scale simulations (AIAA 2013-1386). |

### Why the "Specimen" Matters:
1.  **Heat Flux ($\dot{q}$)**: Chemical reactions (endothermic dissociation) act as a "heat sink," absorbing energy that would otherwise increase the gas temperature.
2.  **Surface Catalysis**: Recombination of atoms (N + N → N2) on the vehicle surface releases heat. The species model determines how much atomic oxygen/nitrogen is available for this process.
3.  **Shock Standoff**: The effective $\gamma$ (ratio of specific heats) changes as gas dissociates, which alters the distance of the bow shock from the nose.

---

## 2.2. Gas Dynamics & Rarefaction (Knudsen Number)
The **Knudsen Number ($Kn$)** is a dimensionless ratio that determines whether the gas should be treated as a continuous fluid or as a collection of individual particles.

$$Kn = \frac{\lambda}{L}$$

*   **$\lambda$ (Mean Free Path):** Average distance a molecule travels before colliding with another.
*   **$L$ (Characteristic Length):** The diameter or nose radius of the HIAD.

| Regime | $Kn$ Range | Solver Requirement | StellarOrion Status |
| :--- | :--- | :--- | :--- |
| **Continuum** | $Kn < 0.01$ | Navier-Stokes (CFD) | Valid for low-altitude/high-density. |
| **Transitional** | $0.01 < Kn < 10$ | **DSMC (SPARTA)** | **Primary Project Focus.** Typical of HIAD high-altitude deceleration. |
| **Free Molecular**| $Kn > 10$ | Kinetic Theory | Valid for orbital altitudes (VLEO). |

### Why $Kn$ is Critical:
*   **Solver Fidelity:** If $Kn > 0.01$, standard CFD (Navier-Stokes) fails to predict surface heating and drag accurately because the "no-slip" boundary condition no longer applies.
*   **StellarOrion Implementation:** Currently, $Kn$ is **not a direct input parameter**. It is a *resultant* of the atmospheric density (`env_nrho`) and vehicle scale (`diameter`). However, the SPARTA solver is specifically chosen to handle the $Kn > 0.01$ regime where traditional CFD is inaccurate.
*   **Future Development:** Plan to implement a "Knudsen Threshold" toggle to automatically switch between DSMC and PINN-Continuum modes to optimize compute time.

## 3. Derived Metrics (Survivability Criteria)
Metrics used to determine if the payload is "protected."

*   **Ballistic Coefficient ($\beta$):** $\beta = \frac{m \cdot q}{F_{drag}}$ [$kg/m^2$]. Lower is safer for landing. **IRVE-3 Target: 26.9 kg/m²**.
*   **Peak Stagnation Heat:** $\dot{q} = \frac{Q_{total}}{A_{ref}}$ [$W/m^2$]. Must stay below material limits. **IRVE-3 Target: 14.4 W/cm²**.
*   **Backface Temperature:** $T_{back} = T_{init} + \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{TPS} \cdot C_{p,TPS} \cdot \delta_{TPS}}$. Target: $< 350K$.
*   **G-Load:** $n = \frac{F_{drag}}{m \cdot g_0}$. Deceleration load in units of Earth gravity. **IRVE-3 Target: 20.2 g**.

---

## 4. IRVE-3 Flight Test Baseline (Validation Reference)
The project uses the **IRVE-3 (Inflatable Re-entry Vehicle Experiment 3)** mission as the primary benchmark for validation (NASA/TP-2013-4012).

| Metric | Flight Result | Purpose |
| :--- | :--- | :--- |
| **Velocity** | Mach 10.0 (2,700 m/s) | Solver entry speed baseline |
| **Ballistic Coeff ($\beta$)** | **26.9 kg/m²** | Primary SBO optimization target |
| **Peak Heat Flux ($\dot{q}$)** | **14.4 W/cm²** | Aerothermal model validation |
| **Peak Deceleration** | **20.2 g** | Structural load validation |
| **Nose Radius ($R_n$)** | 0.191 m | Geometric baseline |
| **Diameter** | 3.0 m | Scale baseline |
| **Atmosphere** | Earth (Suborbital) | Reentry regime |

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

### G. Mission Atlas V / LOFTID (Flight Heritage)
*   **Quest:** Demonstrate large-scale HIAD capability through an actual orbital deorbit and reentry sequence.
*   **Launch Vehicle:** **Atlas V** (Launched Nov 10, 2022, as a secondary payload).
*   **Payload:** 6.0m LOFTID Aeroshell.
*   **Reasoning:** This is the most significant flight validation of HIAD technology to date. The Atlas V heritage proves that inflatable shields can be integrated into standard heavy-lift fairings and successfully deployed after orbital insertion.

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

## 6.1. Comparison: StellarOrion vs. FluidX3D (LBM)
A frequent internal comparison is made between this pipeline and **FluidX3D**, a highly optimized Lattice Boltzmann Method (LBM) solver. While both leverage GPU acceleration, they serve fundamentally different regimes.

| Feature | StellarOrion (DSMC + MoP) | FluidX3D (LBM) |
| :--- | :--- | :--- |
| **Physics Engine** | **Particle-based Kinetic (DSMC):** Solves the Boltzmann equation via stochastic particle collisions. | **Lattice Boltzmann (LBM):** Solves the discrete Boltzmann equation on a regular grid (lattice). |
| **Mach Regime** | **Hypersonic ($M > 5$):** Purpose-built for strong shocks and thermal non-equilibrium. | **Subsonic/Incompressible ($M < 0.3$):** Standard LBM assumes low-speed, nearly incompressible flow. |
| **Compressibility** | Fully Compressible (captures shock waves). | Incompressible / Weakly Compressible (shocks cause instability). |
| **Rarefaction** | Captures $Kn > 0.01$ (High altitude / VLEO). | Continuum only ($Kn \approx 0$). |
| **Hardware Use** | Hybrid: Docker/CPU (Physics) + GPU/NPU (MoP Inference). | Pure GPU: Optimized for massive throughput on single or multi-GPU nodes. |
| **Use Case** | Reentry vehicles, HIAD thermal protection, orbital decay. | Urban wind comfort, automotive aero (low speed), multiphase fluid mixing. |

### Why FluidX3D is NOT used for Hypersonics:
1. **Equilibrium Assumption:** Standard LBM (like FluidX3D) relies on a local equilibrium distribution (Maxwell-Boltzmann). In hypersonics, the gas is in **extreme non-equilibrium** behind the shock wave, which LBM cannot resolve without specialized (and computationally expensive) high-order lattices.
2. **Shock Stability:** LBM is notoriously unstable at high Mach numbers. The "lattice velocity" must be significantly higher than the flow velocity to maintain stability, leading to a "Mach number limit" that is far below the $10,000 \text{ m/s}$ required for StellarOrion.
3. **Thermal Non-equilibrium:** DSMC naturally handles different temperatures for translation, rotation, and vibration. FluidX3D is typically isothermal or uses a simplified energy equation that fails in the plasma regime.

---

## 6.2. Software Evolution: The Road to MoP Steering
The StellarOrion pipeline is a multi-generational project. It is important to distinguish between the **First Generation (Subsonic)** and the current **Hypersonic Edition**.

### Phase 1: StellarOrion G1 (Subsonic Airfoil Optimization)
*   **Origin:** Stems from a modification of the **Bimo XFoil Optimization GA**.
*   **Problem:** Early versions used Genetic Algorithms to move individual airfoil coordinate points directly. This "wild" point movement made it nearly impossible to find a smooth, converged optimal shape.
*   **The Hicks-Henne Breakthrough:** To solve the convergence issues, the logic was adapted to use **Hicks-Henne bump functions** as the primary **Geometry Engine**. In this architecture, airfoils are effectively **"Procedurally Generated"** via parametric deformations rather than manually sculpted.
*   **The G1 Optimization Pipeline:**
    1.  **Initialization:** Uses **RNG as seed** for the initial Hicks-Henne geometry population.
    2.  **Constraint-Based GA:** A Genetic Algorithm (GA) starts the search based on predefined aerodynamic constraints.
    3.  **Surrogate Training:** Once the GA identifies **50 high-performing candidates**, they are used to train the **MoP (Metamodel of Optimal Prognosis)**.
    4.  **Active Steering:** The GA is then **steered** by the MoP model, leveraging GPU/NPU acceleration to evaluate thousands of virtual candidates in milliseconds.
    5.  **Termination:** The loop continues until a **callback detects stagnation** (no significant fitness improvement), at which point the system "spits out" the final optimized result.
*   **Context:** This was a dedicated 2D subsonic tool (see `ProgressReport/Week 1/G1_StellarOrion_Subsonic_Evolution`).

### Phase 2: StellarOrion G2 (Hypersonic Edition)
*   **Goal:** Re-engineering the G1 optimization logic for extreme flight regimes.
*   **Solver Transition:** XFoil (subsonic) replaced by **SPARTA (DSMC)** to handle high-Mach shock waves and rarefied flow.
*   **Dimensionality:** Moves from 2D airfoils to **3D Axisymmetric HIAD** geometries.
*   **ML Integration:** DeepXDE PINNs used for even higher fidelity flow-field refinement and parameter estimation.
*   **Optimization Strategy (Evolutionary MoP Steering):**
    1.  **Steered Search:** Inherits and expands the **MoP Steering** logic from G1. The GA is steered by the surrogate metamodel to evaluate millions of candidates on the GPU/NPU.
    2.  **Stagnation Decision Logic:** Unlike the fixed termination in G1, G2 monitors the **stagnation point of changes** (rate of fitness improvement vs. structural deformation delta).
    3.  **Intelligent Evolution:** At each stagnation checkpoint, the system evaluates the current Pareto front. If the gradient of improvement is below the threshold, it triggers an **Intelligence Decision**:
        *   **Continue Evolving:** If the surrogate model suggests untapped design space, it resets the seed/population and pushes for higher generations.
        *   **Finalize:** If physical limits are reached, it "spits out" the final optimized structural toroid and nose radius configurations.

---

## 6.1. Methodology of Physics (MoP) & Genetic Algorithm Interplay
The **Methodology of Physics (MoP)** acts as the "Laws of Nature" within the Genetic Algorithm (GA). While the GA handles the exploration of the design space (evolution), the MoP logic enforces physical survivability constraints during the **Natural Selection** phase.

### The MoP Fitness Function
The GA evaluates each design using a Weighted Fitness Function ($F$), where MoP introduces heavy **Penalty Weights** ($P$) for physically non-viable designs.

$$F = (w_1 \cdot C_D) + (w_2 \cdot \frac{1}{\text{Mass}}) - P_{MoP}$$

### MoP Penalty Logic ($P_{MoP}$):
The penalty is triggered if the Surrogate-Based Optimization (SBO) predicts a violation of "Hard Constraints":

1.  **Thermal Constraint:** If $T_{backface} > 350K$, then $P_{MoP} \to \infty$.
2.  **Structural Constraint:** If $Peak\_G > 25g$, then $P_{MoP} \to \infty$.
3.  **Aero Constraint:** If $C_D < 1.2$ (insufficient drag), then $P_{MoP}$ is scaled proportionally to the deficit.

### Interplay Summary:
*   **GA (The Parent):** Generates new designs via Crossover and Mutation (e.g., changing `toroids` count or `nose_radius`).
*   **MoP (The Environment):** Evaluates if the design "survives" the physics of reentry. It adds **weight** to favorable aerodynamic metrics but applies **infinite penalty** to designs that would burn up or collapse.
*   **Natural Selection:** Designs with high $P_{MoP}$ are "killed off" in the current generation, ensuring only physically robust parents produce the next generation.

---

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

---

## 8. Mission References & Technical Specifications
Detailed specifications and source references for the mission presets and comparative tools.

### A. FluidX3D Source (Comparative)
*   **Project:** GPU-accelerated Lattice Boltzmann solver.
*   **Repository:** [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
*   **Key Distinction:** Optimized for incompressible/low-speed regimes; distinct from the rarefied/hypersonic regime of SPARTA/StellarOrion.

### A. IRVE-3 (Inflatable Re-entry Vehicle Experiment 3)
*   **Mission Type:** Suborbital Flight Test (Sounding Rocket).
*   **Launch Vehicle:** Black Brant XI (Wallops Flight Facility).
*   **Target Altitude:** ~80 km.
*   **Geometry:** 3.0m diameter, 60-degree half-angle cone, 7 toroids.
*   **Citation:** 
    ```bibtex
    @inproceedings{cassell2013inflatable,
      title={Inflatable Re-entry Vehicle Experiment (IRVE-3) Flight Results},
      author={Cassell, Robert and others},
      booktitle={AIAA 2013-1386},
      year={2013}
    }
    ```

### B. LOFTID (Low-Earth Orbit Flight Test of an Inflatable Decelerator)
*   **Mission Type:** LEO Deorbit & Reentry.
*   **Launch Vehicle:** Atlas V (Secondary Payload).
*   **Target Altitude:** LEO-to-Surface.
*   **Geometry:** 6.0m diameter (scaled from 3.0m baseline), 7 toroids, F-TPS (Silicon Carbide fabric).
*   **Citation:** 
    ```bibtex
    @inproceedings{lippincott2019low,
      title={Low-Earth Orbit Flight Test of an Inflatable Decelerator (LOFTID) Mission Overview},
      author={Lippincott, John and others},
      booktitle={AIAA 2019-3386},
      year={2019}
    }
    ```

### C. Artemis (Lunar Return Profile)
*   **Mission Type:** Interplanetary Reentry (Lunar-to-Earth).
*   **Target Velocity:** 10.5 - 11.2 km/s.
*   **Chemistry Mode:** 11-species Ionization (required for speeds > 8 km/s).
*   **TPS Priority:** High thermal soak, massive thermal lag factor ($\eta_{lag}$ ~ 20%).
*   **Key Reference:** NASA Artemis Mission Reentry Profiles (Technical Summaries).

### D. Mars Science Laboratory (MSL) Scale
*   **Mission Type:** Planetary Entry (Earth-to-Mars).
*   **Atmosphere:** 95% $CO_2$ (Mars preset in `StellarOrionEngineMach5Up.py`).
*   **Ballistic Coefficient:** Optimized for $\beta < 150 kg/m^2$ to ensure subsonic parachute deployment.
*   **Citation:** 
    ```bibtex
    @book{anderson2006hypersonic,
      title={Hypersonic and High-Temperature Gas Dynamics},
      author={Anderson, John D},
      year={2006},
      publisher={AIAA Education Series}
    }
    ```

### E. Atmosphere Modeling (NRLMSIS 2.1)
*   **Logic:** Used for density and temperature profile generation in `StellarOrionEngineMach5Up.py`.
*   **Citation:**
    ```bibtex
    @article{emmert2022nrlmsis,
      title={NRLMSIS 2.1: An empirical model of nitric oxide incorporated into MSIS},
      author={Emmert, J T and others},
      journal={Journal of Geophysical Research: Space Physics},
      volume={127},
      year={2022}
    }
    ```

### F. Magister Bibliographic Database
A complete list of over 50+ citations (including turbulence models, numerical schemes, and aero-thermal studies) is maintained in the root [REFERENCES.MD](file:///Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/REFERENCES.MD).

---

## 9. Development Roadmap & TODO
Upcoming critical improvements for the StellarOrion Hypersonic Edition.

- [ ] **DeepXDE PINN Stability:** Fix "wacky" behavior in the PINN steps. Investigate training instability and ensure consistent flow-field refinement.
- [ ] **Checkpointing System (Recoverability):**
    *   Implement **Pause and Resume** logic for all pipeline steps.
    *   Specifically, integrate SPARTA's native restart/checkpointing capability into the `StellarOrionEngineMach5Up.py` logic.
    *   Ensure the state is saved so the simulation is fully resumable after a crash or system interruption.

---

## 10. PINN Implementation (DeepXDE)
The StellarOrion G2 pipeline uses **Physics-Informed Neural Networks (PINNs)** via the **DeepXDE** library to refine SPARTA flow fields and perform inverse parameter estimation.

### Mathematical Formulation
The PINN is trained to minimize a composite loss function containing the residuals of the **2D Steady Compressible Euler Equations**:

1.  **Continuity (Mass Conservation):**
    $$\nabla \cdot (\rho \mathbf{u}) = \frac{\partial (\rho u)}{\partial x} + \frac{\partial (\rho v)}{\partial y} = 0$$
2.  **Momentum Conservation (Euler):**
    $$\rho (\mathbf{u} \cdot \nabla) \mathbf{u} + \nabla p = 0$$
    *   *X-Momentum:* $\rho (u \frac{\partial u}{\partial x} + v \frac{\partial u}{\partial y}) + \frac{\partial p}{\partial x} = 0$
    *   *Y-Momentum:* $\rho (u \frac{\partial v}{\partial x} + v \frac{\partial v}{\partial y}) + \frac{\partial p}{\partial y} = 0$
3.  **Equation of State (Ideal Gas Law):**
    $$p = \rho R T$$

**Variable Definitions:**
*   $\rho$: Gas density $[kg/m^3]$
*   $\mathbf{u}$: Velocity vector ($u, v$) $[m/s]$
*   $p$: Pressure $[Pa]$
*   $T$: Temperature $[K]$
*   $R$: Specific gas constant for air $[287.05 J/kg \cdot K]$
*   $\nabla$: Gradient operator
*   $\nabla \cdot$: Divergence operator

### Hybrid Anchor-Point Strategy
The network does not solve the PDE from scratch. Instead, it uses a **Hybrid Data-Physics Approach**:
*   **Anchor Points:** Grid data from **SPARTA (DSMC)** is injected as `PointSetBC` (Observation Boundary Conditions).
*   **Refinement:** The neural network (FNN, 5 layers, 128 neurons) acts as a high-order interpolator that "fills the gaps" between particles while strictly adhering to the conservation laws defined by the Euler equations.
*   **Acceleration:** Training is performed on native hardware (**Apple Silicon MPS** or **NVIDIA CUDA**) to ensure the refinement phase remains competitive with the MoP steering loop.

### Implementation Location
The core logic resides in `source/pinn_accelerator.py` within the `pde_euler_2d` function and the `PINNAccelerator` class.
