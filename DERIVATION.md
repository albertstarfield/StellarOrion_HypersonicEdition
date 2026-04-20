# Theory & Implementation Derivation

This document provides a comprehensive derivation of the mathematical models used in the StellarOrion Hypersonic Simulation Suite and maps them to their specific implementations in `gui_backend.py` and `source/visualizer.py`.

---

## 1. SPARTA Data Parsing & Mapping

The simulation results are extracted from SPARTA dump files. The mapping between the raw data columns and the physical metrics is as follows:

### Surface Data (Force & Heat)
**Source File:** `results_reference/surf.*.out`  
**SPARTA Command:** `dump 1 surf all 1000 ... id f_1[*] f_surfavg[*] (gui_backend.py:360)`

| Column | Implementation Index | Physical Variable | Unit | Implementation Line |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `parts[0]` | Particle ID | - | - |
| 2 | `parts[1]` | `nflux` (Number Flux) | $m^{-2} s^{-1}$ | - |
| 3 | `parts[2]` | `mflux` (Mass Flux) | $kg \cdot m^{-2} s^{-1}$ | - |
| 4 | `parts[3]` | `ke` (Kinetic Energy Flux) | $J \cdot m^{-2} s^{-1}$ | `gui_backend.py:140` |
| 5 | `parts[4]` | `fx` (Axial Force) | $N$ | `gui_backend.py:141` |
| 6 | `parts[5]` | `fy` (Radial Force) | $N$ | - |
| 7 | `parts[6]` | `fz` (Azimuthal Force) | $N$ | - |

**Derivation of Global Metrics:**
*   **Total Drag ($F_{drag}$):** $\sum |f_x|$ across all surface elements (`gui_backend.py:144`).
*   **Total Heat Load ($Q_{total}$):** $\sum |ke|$ across all surface elements (`gui_backend.py:145`).

### Grid Data (Field Maps)
**Source File:** `results_reference/grid.*.out`  
**SPARTA Command:** `dump 2 grid all 1000 ... id xlo ylo xhi yhi f_2[*] f_3[*] (gui_backend.py:361)`

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
The ballistic coefficient is a measure of a vehicle's ability to maintain its speed during reentry.  
**Standard Equation:** $\beta = \frac{m}{C_D A}$  
**Implementation Derivation:**
Since $F_{drag} = C_D A q$, where $q$ is dynamic pressure:
$$\beta = \frac{m \cdot q}{F_{drag}}$$
*   **Mass Density ($\rho$):** $\rho = n_{\rho} \cdot \frac{M_{air}}{N_A}$ (`gui_backend.py:163`)
*   **Dynamic Pressure ($q$):** $q = \frac{1}{2} \rho v_{\infty}^2$ (`gui_backend.py:165`)
*   **Beta Implementation:** `beta = mass * q / drag_force` (`gui_backend.py:166`)

### Instantaneous g-load ($n$)
The deceleration load felt by the vehicle in Earth-gravity units ($g_0$):
$$n = \frac{F_{drag}}{m \cdot g_0}$$
*   **Implementation:** `g_load = drag_force / (mass * 9.81)` (`gui_backend.py:172`)

---

## 3. 1D Thermal Model Derivation

StellarOrion uses a 1D transient approximation for the Thermal Protection System (TPS) backface temperature, assuming a thermal lag during the peak heat pulse.

### Stagnation Heat Flux Proxy ($\dot{q}$)
$$\dot{q} = \frac{Q_{total}}{A_{ref}}$$
*   **Implementation:** `stag_heat = heat_flux / area` (`gui_backend.py:169`)

### Adiabatic Backface Temperature ($T_{back}$)
Assuming the heat pulse $\dot{q}$ lasts for duration $\Delta t$, and a fraction $\eta_{lag}$ of that energy penetrates the insulation to reach the backface:
$$E_{total} = \dot{q} \cdot \Delta t \cdot \eta_{lag}$$
The temperature rise $\Delta T$ is given by:
$$\Delta T = \frac{E_{total}}{\text{Mass}_{TPS} \cdot C_{p,TPS}} = \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{(\rho_{TPS} \cdot \delta_{TPS}) \cdot C_{p,TPS}}$$
*   **Implementation:** `t_rise = (heat_load * thermal_lag_factor) / (rho_tps * cp_tps * tps_thickness)` (`gui_backend.py:191`)
*   **Final Temperature:** `t_backface = t_initial + t_rise` (`gui_backend.py:193`)

---

## 4. Survivability Optimization (SBO)

### Latin Hypercube Sampling (LHS)
To ensure the high-dimensional search space (Diameter, Angle, Mass, etc.) is explored uniformly with minimal samples, StellarOrion implements **Stratified LHS**:
$$x_{i,j} = \min(x_j) + \text{range}(x_j) \cdot \frac{i + r}{N}$$
*Where $i$ is the sample index, $j$ is the parameter dimension, $N$ is total samples, and $r \sim \mathcal{U}(0,1)$.*
*   **Implementation:** `val = p_info['min'] + (p_info['max'] - p_info['min']) * (i + np.random.random()) / samples_n` (`gui_backend.py:530`)

### Metamodel Training (PyTorch)
The "Metamodel Prognosis" (MoP) is a Multi-Layer Perceptron (MLP) that maps design parameters to performance metrics.
*   **Architecture:** 3-layer MLP (`Linear(N, 64) -> ReLU -> Linear(64, 64) -> ReLU -> Linear(64, 1)`).
*   **Implementation:** `model = nn.Sequential(...)` (`gui_backend.py:613`)
*   **Loss Function:** Mean Squared Error (MSE).
*   **Implementation:** `loss = nn.MSELoss()(model(X_tensor), Y_tensor)` (`gui_backend.py:617`)

### Genetic Algorithm (GA) Cost Function
The GA steers the search towards configurations that minimize a weighted cost $J$ relative to user-defined targets.
$$J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{metric} \left( \frac{y_{pred} - y_{target}}{1} \right)^2$$
*   **Implementation:** Lines 642-644 in `gui_backend.py`.
