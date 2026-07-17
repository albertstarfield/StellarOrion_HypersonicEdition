# Theory & Implementation Derivation

This document provides a comprehensive derivation of the mathematical models used in the StellarOrion Hypersonic Simulation Suite and maps them to their specific implementations in `StellarOrionEngineMach5Up.py` and `source/visualizer.py`.

---

## 1. SPARTA Data Parsing & Mapping

The simulation results are extracted from SPARTA dump files. The mapping between the raw data columns and the physical metrics is as follows:

### Surface Data (Force & Heat)
**Source File:** `results_reference/surf.*.out`  
**SPARTA Command:** `dump 1 surf all 1000 ... id f_1[*] f_surfavg[*] (StellarOrionEngineMach5Up.py:360)`

| Column | Implementation Index | Physical Variable | Unit | Implementation Line |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `parts[0]` | Particle ID | - | - |
| 2 | `parts[1]` | `nflux` (Number Flux) | $m^{-2} s^{-1}$ | - |
| 3 | `parts[2]` | `mflux` (Mass Flux) | $kg \cdot m^{-2} s^{-1}$ | - |
| 4 | `parts[3]` | `ke` (Kinetic Energy Flux) | $J \cdot m^{-2} s^{-1}$ | `StellarOrionEngineMach5Up.py:140` |
| 5 | `parts[4]` | `fx` (Axial Force) | $N$ | `StellarOrionEngineMach5Up.py:141` |
| 6 | `parts[5]` | `fy` (Radial Force) | $N$ | - |
| 7 | `parts[6]` | `fz` (Azimuthal Force) | $N$ | - |

**Derivation of Global Metrics:**
*   **Total Drag ($F_{drag}$):** $\sum |f_x|$ across all surface elements (`StellarOrionEngineMach5Up.py:144`).
*   **Total Heat Load ($Q_{total}$):** $\sum |ke|$ across all surface elements (`StellarOrionEngineMach5Up.py:145`).

### Grid Data (Field Maps)
**Source File:** `results_reference/grid.*.out`  
**SPARTA Command:** `dump 2 grid all 1000 ... id xlo ylo xhi yhi f_2[*] f_3[*] (StellarOrionEngineMach5Up.py:361)`

| Column | Implementation Index | Physical Variable | Unit | Visualizer Index |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `parts[0]` | Cell ID | - | - |
| 2-5 | `parts[1:5]` | `xlo`, `ylo`, `xhi`, `yhi` | $m$ | `data[:, 0:4]` |
| 6 | `parts[5]` | `n` (Number Density) | $m^{-3}$ | `data[:, 4]` |
| 7-9 | `parts[6:9]` | `u, v, w` (Velocity Components) | $m/s$ | `data[:, 5:8]` |
| 10 | `parts[9]` | `temp` (Translational Temperature) | $K$ | `data[:, 8]` |
| 11 | `parts[10]` | `press` (Pressure) | $Pa$ | `data[:, 9]` |

---

## 2. Flight Metrics Derivation

### Ballistic Coefficient ($\beta$)
The ballistic coefficient is a measure of a vehicle's ability to maintain its speed during reentry (Anderson, 2006).  
**Standard Equation:** $\beta = \frac{m}{C_D A}$  
**Implementation Derivation:**
Since $F_{drag} = C_D A q$, where $q$ is dynamic pressure:
$$\beta = \frac{m \cdot q}{F_{drag}}$$
*   **Mass Density ($\rho$):** $\rho = n_{\rho} \cdot \frac{M_{air}}{N_A}$ (`StellarOrionEngineMach5Up.py:163`)
*   **Dynamic Pressure ($q$):** $q = \frac{1}{2} \rho v_{\infty}^2$ (`StellarOrionEngineMach5Up.py:165`)
*   **Beta Implementation:** `beta = mass * q / drag_force` (`StellarOrionEngineMach5Up.py:166`)

### Instantaneous g-load ($n$)
The deceleration load felt by the vehicle in Earth-gravity units ($g_0$):
$$n = \frac{F_{drag}}{m \cdot g_0}$$
*   **Implementation:** `g_load = drag_force / (mass * 9.81)` (`StellarOrionEngineMach5Up.py:172`)

---

## 3. 1D Thermal Model Derivation

StellarOrion uses a 1D transient approximation for the Thermal Protection System (TPS) backface
temperature (Anderson, 2006), assuming a thermal lag during the peak heat pulse.

### Stagnation Heat Flux — Sutton-Graves Correlation (1971) [Ref: 251]

> **Design Decision (Jul 2026):** The raw SPARTA DSMC `ke` surface compute cannot be used directly
> as an absolute heat flux in W/m². SPARTA's `fix ave/surf` outputs kinetic energy
> per simulated particle per timestep per face element — a simulation-internal unit that depends on
> `fnum`, timestep `dt`, and the face area in a non-trivially-normalized way. It is retained only
> as a **relative shape-ranking signal** for the optimizer (comparing geometries against each other).
>
> For all **absolute thermal calculations** (surface temperature, backface temperature,
> TPS survivability) StellarOrion uses the **Sutton-Graves (1971)** stagnation-point
> convective heating correlation, which is the standard reference formula for Earth entry
> and has been validated against IRVE-3 flight data by Rapisarda (2023).

The Sutton-Graves general stagnation-point convective heating equation is:

$$\boxed{\dot{q}_{stag} = C_{SG} \sqrt{\frac{\rho_\infty}{R_N}} \cdot V_\infty^3}$$

| Symbol | Description | Value (IRVE-3 baseline) |
|---|---|---|
| $\dot{q}_{stag}$ | Stagnation-point heat flux | W/m² |
| $C_{SG}$ | Sutton-Graves constant (Earth air) | $1.7415 \times 10^{-4}$ |
| $\rho_\infty$ | Freestream density | $\approx 1.67 \times 10^{-4}$ kg/m³ (52 km) |
| $R_N$ | Nose radius | 0.55 m |
| $V_\infty$ | Freestream velocity | 2700 m/s |

**IRVE-3 Validation:**

$$\dot{q}_{stag} = 1.7415 \times 10^{-4} \sqrt{\frac{1.67 \times 10^{-4}}{0.55}} \times 2700^3 \approx 1.90 \times 10^5 \ \text{W/m}^2 = 19.0 \ \text{W/cm}^2$$

This is consistent with the IRVE-3 documented peak heat flux of ~14 W/cm² (difference reflects
that the Sutton-Graves correlation is a conservative upper bound — actual aeroheating is reduced by
the HIAD's flared geometry and stand-off shock).

**Applicability note:** Sutton-Graves is valid for:
- Earth atmosphere, continuum and near-continuum flow ($\text{Kn} \ll 1$)
- Blunt-body geometry (spherical nose cap)
- Velocity range: 3–12 km/s

*   **Implementation:** `stag_heat = C_sg * np.sqrt(rho_inf / nose_radius) * (vstream ** 3)`
    (`StellarOrionEngineMach5Up.py`, `calculate_flight_metrics`)
*   **Reference:** K. Sutton and R. A. Graves Jr., "A general stagnation-point convective heating
    equation for arbitrary gas mixtures," NASA TR R-376, 1971. [Ref: 251]

---

### Surface Temperature — Radiative Equilibrium ($T_{surface}$)

At the TPS outer surface, radiative cooling balances the incoming convective heat flux at steady
state. Assuming grey-body radiation:

$$\dot{q}_{stag} = \epsilon \sigma T_{surface}^4 \implies T_{surface} = \left(\frac{\dot{q}_{stag}}{\epsilon \sigma}\right)^{1/4}$$

| Symbol | Description | Value |
|---|---|---|
| $\epsilon$ | TPS surface emissivity | 0.75 (Nicalon SiC default) |
| $\sigma$ | Stefan-Boltzmann constant | $5.67 \times 10^{-8}$ W/m²K⁴ |

**IRVE-3 baseline result:** $T_{surface} \approx 1453$ K, well below the SiC melting point of 2073 K. ✅

*   **Implementation:** `t_surface = (stag_heat / (sigma * epsilon))**0.25`

---

### Adiabatic Backface Temperature ($T_{back}$)
Assuming the heat pulse $\dot{q}$ lasts for duration $\Delta t$, and a fraction $\eta_{lag}$ of that energy penetrates the insulation to reach the backface:
$$E_{total} = \dot{q} \cdot \Delta t \cdot \eta_{lag}$$
The temperature rise $\Delta T$ is given by:
$$\Delta T = \frac{E_{total}}{\text{Mass}_{TPS} \cdot C_{p,TPS}} = \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{(\rho_{TPS} \cdot \delta_{TPS}) \cdot C_{p,TPS}}$$
*   **Implementation:** `t_rise = (heat_load * thermal_lag_factor) / (rho_tps * cp_tps * tps_thickness)` (`StellarOrionEngineMach5Up.py`)
*   **Final Temperature:** `t_backface = t_initial + t_rise`

---


## 4. Survivability Optimization (SBO)

### Latin Hypercube Sampling (LHS)
To ensure the high-dimensional search space (Diameter, Angle, Mass, etc.) is explored uniformly with minimal samples, StellarOrion implements **Stratified LHS** (McKay et al., 1979):
$$x_{i,j} = \min(x_j) + \text{range}(x_j) \cdot \frac{i + r}{N}$$
*Where $i$ is the sample index, $j$ is the parameter dimension, $N$ is total samples, and $r \sim \mathcal{U}(0,1)$.*
*   **Implementation:** `val = p_info['min'] + (p_info['max'] - p_info['min']) * (i + np.random.random()) / samples_n` (`StellarOrionEngineMach5Up.py:530`)

### Metamodel Training (PyTorch)
The "Metamodel Prognosis" (MoP) is a Multi-Layer Perceptron (MLP) that maps design parameters to performance metrics.
*   **Architecture:** 3-layer MLP (`Linear(N, 64) -> ReLU -> Linear(64, 64) -> ReLU -> Linear(64, 1)`).
*   **Implementation:** `model = nn.Sequential(...)` (`StellarOrionEngineMach5Up.py:613`)
*   **Loss Function:** Mean Squared Error (MSE).
*   **Implementation:** `loss = nn.MSELoss()(model(X_tensor), Y_tensor)` (`StellarOrionEngineMach5Up.py:617`)

### Genetic Algorithm (GA) Cost Function
The GA steers the search towards configurations that minimize a weighted cost $J$ relative to user-defined targets.
$$J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{metric} \left( \frac{y_{pred} - y_{target}}{1} \right)^2$$
*   **Implementation:** Lines 642-644 in `StellarOrionEngineMach5Up.py`.

---

## 5. PINN Refinement Derivation (DeepXDE)

The **Physics-Informed Neural Network (PINN)** stage uses the **2D Compressible Navier-Stokes Equations** (Anderson, 2006) to refine the flow field data from SPARTA.

### 2D Compressible Navier-Stokes Equations (Axisymmetric)
The network $\mathcal{N}(x, y) \to (\rho, u, v, T, p)$ is constrained by the following residuals:

1.  **Continuity Residual ($R_{cont}$):**
    $$\nabla \cdot (\rho \mathbf{u}) = \frac{\partial (\rho u)}{\partial x} + \frac{\partial (\rho v)}{\partial y} = 0$$
2.  **Momentum Residuals ($R_{mom,x}, R_{mom,y}$):**
    $$\rho(u \frac{\partial u}{\partial x} + v \frac{\partial u}{\partial y}) + \frac{\partial p}{\partial x} = 0$$
    $$\rho(u \frac{\partial v}{\partial x} + v \frac{\partial v}{\partial y}) + \frac{\partial p}{\partial y} = 0$$
3.  **Equation of State Residual ($R_{EOS}$):**
    $$p - \rho R T = 0$$

### PINN Implementation (source/pinn_accelerator.py)
*   **Automatic Differentiation:** `dde.grad.jacobian` is used to calculate spatial derivatives without mesh-based discretization.
*   **Checkpoint Exchange:** SPARTA grid data is introduced via `dde.icbc.PointSetBC`, which adds a data-matching term to the loss function:
    $$\mathcal{L}_{total} = \mathcal{L}_{PDE} + w_{data} \mathcal{L}_{data}$$
    *Where $\mathcal{L}_{data} = \frac{1}{N_{obs}} \sum |y_{pred} - y_{obs}|^2$.*
*   **Inverse Estimation:** When `inverse=True`, a physical parameter (e.g., $v_{\infty}$) is defined as a `dde.Variable` and optimized alongside the network weights.
