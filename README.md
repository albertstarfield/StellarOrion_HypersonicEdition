# StellarOrion HypersonicEdition

StellarOrion is a high-fidelity aerothermodynamic simulation and optimization suite for Hypersonic Inflatable Aerodynamic Decelerators (HIAD). It leverages the **SPARTA DSMC** solver for rarefied gas dynamics (Plimpton & Gallis, 2014) and a **PyTorch-based Metamodel Prognosis** for survivability optimization.

## 🚀 Architecture

This project uses a hybrid architecture for running simulations:

- **Docker:** Used exclusively for running the SPARTA simulation in a containerized Linux environment. This ensures reproducibility of the SPARTA build and execution.
- **Native OS:** The Python environment (including PyTorch) runs on the native OS to leverage global hardware acceleration. Supported platforms include **NVIDIA CUDA**, **AMD ROCm**, **Apple Metal (MPS)**, **Intel OneAPI/OpenCL**, and specialized accelerators from **Huawei (CANN)**, **Moore Threads (MUSA)**, **Biren (SUPA)**, and **Qualcomm (Snapdragon)**. This environment powers the **DeepXDE** PINN refinement and the MoP optimization loops.

---

## 🛠️ Requirements & Installation

- **Docker:** Required for SPARTA simulation.
- **Python 3.10+**: Recommended.
- **Dependencies:** `torch`, `numpy`, `matplotlib`, `pymsis`.
- **DeepXDE:** Required for PINN refinement (Auto-installed on first use if missing).

```bash
pip install torch numpy matplotlib pymsis
# DeepXDE is installed automatically when refinement is triggered
```

---

## 🧮 Mathematical Foundations

The following equations form the basis of the simulation engine and the performance metrics calculated in `StellarOrionEngineMach5Up.py`.

### 1. General DSMC & Rarefied Gas Dynamics
Direct Simulation Monte Carlo (DSMC) is used where the continuum assumption fails ($Kn > 0.01$) (Bird, 1994).

*   **Mean Free Path ($\lambda$):**
    $$\lambda = \frac{1}{\sqrt{2} \pi d^2 n}$$
    *Where $d$ is the molecular diameter and $n$ is the number density.*

*   **Knudsen Number ($Kn$):**
    $$Kn = \frac{\lambda}{L}$$
    *Where $L$ is the characteristic length (e.g., aeroshell diameter).*

*   **VSS (Variable Soft Sphere) Collision Model:**
    The cross-section $\sigma$ varies with relative velocity $g$:
    $$\sigma = \pi d_{ref}^2 \left( \frac{g_{ref}}{g} \right)^{2(\omega - 0.5)}$$

**Variables:**
*   $\lambda$: Mean free path $[m]$
*   $d$: Molecular diameter $[m]$
*   $n$: Number density $[m^{-3}]$
*   $Kn$: Knudsen number (dimensionless)
*   $L$: Characteristic length $[m]$
*   $\sigma$: Collision cross-section $[m^2]$
*   $g$: Relative velocity of colliding molecules $[m/s]$
*   $\omega$: Viscosity index (gas-specific)

### 2. Aerodynamics & Flight Metrics
Implemented in `calculate_flight_metrics` to derive performance from SPARTA surface results.

*   **Mass Density ($\rho$):**
    $$\rho = n_{rho} \cdot \frac{M_{air}}{N_A}$$
    *Where $M_{air} \approx 28.97 \text{ g/mol}$ and $N_A$ is Avogadro's constant.*

*   **Dynamic Pressure ($q$):**
    $$q = \frac{1}{2} \rho v_{\infty}^2$$

*   **Ballistic Coefficient ($\beta$):**
    $$\beta = \frac{m \cdot q}{F_{drag}}$$
    *A measure of the vehicle's ability to overcome air resistance.*

*   **Instantaneous g-load ($n$):**
    $$n = \frac{F_{drag}}{m \cdot g_0}$$

**Variables:**
*   $\rho$: Mass density $[kg/m^3]$
*   $n_{rho}$: Number density $[m^{-3}]$
*   $M_{air}$: Molar mass of air $[kg/mol]$
*   $N_A$: Avogadro's constant ($6.022 \times 10^{23} mol^{-1}$)
*   $q$: Dynamic pressure $[Pa]$
*   $v_{\infty}$: Freestream velocity $[m/s]$
*   $\beta$: Ballistic coefficient $[kg/m^2]$
*   $m$: Vehicle mass $[kg]$
*   $F_{drag}$: Drag force $[N]$
*   $n$: Deceleration in Earth gravities $[g's]$
*   $g_0$: Standard gravity $[9.81 m/s^2]$

### 3. Aerothermodynamics & Thermal Protection (TPS)
Estimates for the flexible TPS (e.g., LOFTID/IRVE-3 F-TPS stack) (Lau et al., 2013 / Lippincott et al., 2019).

*   **Heat Flux Proxy ($\dot{q}$):**
    $$\dot{q} = \frac{Q_{total}}{A_{ref}}$$

*   **Radiative Equilibrium Surface Temperature ($T_{surface}$):**
    $$T_{surface} = \left( \frac{\dot{q}}{\sigma \epsilon} \right)^{1/4}$$
    *Where $\sigma$ is the Stefan-Boltzmann constant and $\epsilon$ is emissivity.*

*   **1D Transient Backface Temperature ($T_{back}$):**
    $$T_{back} = T_{init} + \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{TPS} \cdot C_{p,TPS} \cdot \delta_{TPS}}$$

**Variables:**
*   $\dot{q}$: Surface heat flux $[W/m^2]$
*   $Q_{total}$: Total heat rate $[W]$
*   $A_{ref}$: Reference area $[m^2]$
*   $T_{surface}$: Radiative equilibrium surface temperature $[K]$
*   $\sigma$: Stefan-Boltzmann constant ($5.67 \times 10^{-8} W/m^2K^4$)
*   $\epsilon$: Emissivity (dimensionless)
*   $T_{back}$: Payload/Backface temperature $[K]$
*   $\Delta t$: Heat pulse duration $[s]$
*   $\eta_{lag}$: Thermal lag efficiency (typically 0.15)
*   $\rho_{TPS}$: TPS density $[kg/m^3]$
*   $C_{p,TPS}$: TPS specific heat $[J/kg \cdot K]$
*   $\delta_{TPS}$: TPS thickness $[m]$

### 4. Survivability Optimization (SBO)
The Genetic Algorithm (GA) optimizes the HIAD geometry using a Metamodel Prognosis (MoP).

*   **Optimization Cost Function ($J$):**
    $$J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{target} \left( \frac{y_{pred} - y_{target}}{1} \right)^2$$

*   **LHS Sampling (Stratified):**
    $$x_i = x_{min} + (x_{max} - x_{min}) \cdot \frac{i + r}{N}$$ (McKay et al., 1979)

**Variables:**
*   $J$: Optimization cost value
*   $w_{\beta}, w_{target}$: Weight coefficients
*   $\beta_{calc}$: Derived ballistic coefficient
*   $y_{pred}$: Metamodel prediction
*   $x_i$: Sample value for parameter $x$
*   $r$: Random number $\in [0, 1)$
*   $N$: Total samples

For a deep dive into the specific derivations, SPARTA data column mappings, and code-level implementation details, see [DERIVATION.MD](file:///Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/DERIVATION.md).

---

## 🛰️ Calibration & Validation: IRVE-3 (Rapisarda 2024 Baseline)
StellarOrion is calibrated against the **IRVE-3 (Inflatable Reentry Vehicle Experiment 3)** flight data using the high-fidelity reconstruction parameters from **Rapisarda (2024)**.

### Key Validation Metrics (Peak Results)
| Parameter | Simulation Target | Source | Status |
| :--- | :--- | :--- | :--- |
| **Aeroshell Diameter** | 3.0 m | NASA Mission | ✅ Verified |
| **Toroid Radius ($r_{torus}$)** | 0.135 m | Rapisarda Table 4.1 | ✅ Geometry Sync |
| **Peak Heat Flux ($\dot{q}$)** | 14.36 W/cm² | Rapisarda Table 4.10 | ✅ Calibrated |
| **Total Heat Load ($Q$)** | 195.06 J/cm² | Rapisarda Table 4.10 | ✅ Calibrated |
| **Ballistic Coeff ($\beta$)** | 26.9 kg/m² | Rapisarda Table 4.10 | ✅ Base Meta |
| **Peak Deceleration** | 20.2 g | NASA Flight Data | ✅ Baseline |
| **Stagnation Pressure** | 12.4 kPa | Rapisarda Recon. | ✅ Verified |

Users can run the automated calibration suite using:
```bash
python3 main.py --compareCalibrate --solver sparta --steps 1000
```

## 📚 References
For detailed scientific citations and mission parameters (IRVE-3, LOFTID), see [REFERENCES.MD](file:///Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/REFERENCES.MD).
