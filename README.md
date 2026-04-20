# StellarOrion HypersonicEdition

StellarOrion is a high-fidelity aerothermodynamic simulation and optimization suite for Hypersonic Inflatable Aerodynamic Decelerators (HIAD). It leverages the **SPARTA DSMC** solver for rarefied gas dynamics and a **PyTorch-based Metamodel Prognosis** for survivability optimization.

## 🚀 Architecture

This project uses a hybrid architecture for running simulations:

- **Docker:** Used exclusively for running the SPARTA simulation in a containerized Linux environment. This ensures reproducibility of the SPARTA build and execution.
- **Native OS:** The Python environment (including PyTorch) runs on the native OS to leverage hardware acceleration (Apple Metal, NVIDIA CUDA, etc.) for pre- and post-processing.

---

## 🧮 Mathematical Foundations

The following equations form the basis of the simulation engine and the performance metrics calculated in `gui_backend.py`.

### 1. General DSMC & Rarefied Gas Dynamics
Direct Simulation Monte Carlo (DSMC) is used where the continuum assumption fails ($Kn > 0.01$).

*   **Mean Free Path ($\lambda$):**
    $$\lambda = \frac{1}{\sqrt{2} \pi d^2 n}$$
    *Where $d$ is the molecular diameter and $n$ is the number density.*

*   **Knudsen Number ($Kn$):**
    $$Kn = \frac{\lambda}{L}$$
    *Where $L$ is the characteristic length (e.g., aeroshell diameter).*

*   **VSS (Variable Soft Sphere) Collision Model:**
    The cross-section $\sigma$ varies with relative velocity $g$:
    $$\sigma = \pi d_{ref}^2 \left( \frac{g_{ref}}{g} \right)^{2(\omega - 0.5)}$$
    *Used to match the viscosity-temperature relationship of real gases.*

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

### 3. Aerothermodynamics & Thermal Protection (TPS)
Estimates for the flexible TPS (e.g., LOFTID/IRVE-3 F-TPS stack).

*   **Heat Flux Proxy ($\dot{q}$):**
    $$\dot{q} = \frac{Q_{total}}{A_{ref}}$$

*   **Radiative Equilibrium Surface Temperature ($T_{surface}$):**
    $$T_{surface} = \left( \frac{\dot{q}}{\sigma \epsilon} \right)^{1/4}$$
    *Where $\sigma$ is the Stefan-Boltzmann constant and $\epsilon$ is emissivity.*

*   **1D Transient Backface Temperature ($T_{back}$):**
    $$T_{back} = T_{init} + \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{TPS} \cdot C_{p,TPS} \cdot \delta_{TPS}}$$
    *Where $\eta_{lag}$ is the thermal lag factor, $\delta_{TPS}$ is thickness, and $C_p$ is specific heat.*

### 4. Survivability Optimization (SBO)
The Genetic Algorithm (GA) optimizes the HIAD geometry using a Metamodel Prognosis (MoP).

*   **Optimization Cost Function ($J$):**
    $$J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{target} \left( \frac{y_{pred} - y_{target}}{1} \right)^2$$

*   **LHS Sampling (Stratified):**
    $$x_i = x_{min} + (x_{max} - x_{min}) \cdot \frac{i + r}{N}$$
    *Ensures uniform coverage of the high-dimensional search space.*

For a deep dive into the specific derivations, SPARTA data column mappings, and code-level implementation details, see [DERIVATION.MD](file:///Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/DERIVATION.md).

## 📚 References
For detailed scientific citations and mission parameters (IRVE-3, LOFTID), see [REFERENCES.MD](file:///Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/REFERENCES.MD).
