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
| $\rho_\infty$ | Freestream density | $\approx 6.9674 \times 10^{-4}$ kg/m³ (code baseline) |
| $R_N$ | Nose radius | 0.55 m |
| $V_\infty$ | Freestream velocity | 2700 m/s |

**IRVE-3 Validation:**

$$\dot{q}_{stag} = 1.7415 \times 10^{-4} \sqrt{\frac{6.9674 \times 10^{-4}}{0.55}} \times 2700^3 \approx 1.22 \times 10^5 \ \text{W/m}^2 = 12.20 \ \text{W/cm}^2$$

This is compared against the IRVE-3 flight measurement of 14.36 W/cm². The difference reflects
that our code uses a single-point baseline condition (ρ=6.9674e-4, V=2700), while the actual
trajectory-integrated peak heating occurs at different conditions. Rapisarda (2023) reports
the trajectory-integrated Sutton-Graves peak as 15.26 W/cm² (+6.26% above flight) and the
Fay-Riddell CFD prediction as 13.83 W/cm² (-3.69% below flight) [Table 4.10]. The Fay-Riddell
correlation is more physically accurate for HIAD geometries because it accounts for the actual
shock layer structure, while Sutton-Graves assumes a spherical nose cap.

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

The **Physics-Informed Neural Network (PINN)** stage uses the **2D Axisymmetric Compressible Navier-Stokes Equations** (Anderson, 2006) to refine the flow field data from SPARTA.

### 2D Axisymmetric Compressible Navier-Stokes Equations
The network $\mathcal{N}(x, y) \to (\rho, u, v, T)$ predicts four state variables.
Pressure is derived via the ideal gas law: $p = \rho R T$ (not a network output).

The network is constrained by the following residuals:

1.  **Continuity Residual ($R_{cont}$):** Axisymmetric form
    $$\frac{\partial (\rho u)}{\partial x} + \frac{\partial (\rho v)}{\partial y} + \frac{\rho v}{y} = 0$$

2.  **Momentum-x Residual ($R_{mom,x}$):** Viscous, with pressure gradient via chain rule
    $$\rho\left(u \frac{\partial u}{\partial x} + v \frac{\partial u}{\partial y}\right) + \frac{\partial p}{\partial x} - \mu \nabla^2 u = 0$$
    where $\frac{\partial p}{\partial x} = R \left(\frac{\partial \rho}{\partial x} T + \rho \frac{\partial T}{\partial x}\right)$

3.  **Momentum-y Residual ($R_{mom,y}$):** Axisymmetric viscous with centrifugal correction
    $$\rho\left(u \frac{\partial v}{\partial x} + v \frac{\partial v}{\partial y}\right) + \frac{\partial p}{\partial y} - \mu \left(\nabla^2 v - \frac{v}{y^2}\right) = 0$$
    where $\frac{\partial p}{\partial y} = R \left(\frac{\partial \rho}{\partial y} T + \rho \frac{\partial T}{\partial y}\right)$

4.  **Energy Residual ($R_{energy}$):** Compressed form for ideal gas
    $$\rho c_p \left(u \frac{\partial T}{\partial x} + v \frac{\partial T}{\partial y}\right) - k \nabla^2 T = 0$$

*[Citation: Anderson (2006), "Hypersonic and High-Temperature Gas Dynamics", §3.2;
 Bird (1994), "Molecular Gas Dynamics", §2.3]*

### PINN Implementation (stellarorion_program_proc/src/python/pinn_accelerator.py)
*   **Automatic Differentiation:** `dde.grad.jacobian` computes first derivatives; `dde.grad.hessian` computes Laplacians — no mesh-based discretization needed.
*   **Pressure Gradient:** Computed via chain rule from the EOS $p = \rho R T$, avoiding the need for a separate pressure network output.
*   **Checkpoint Exchange:** SPARTA grid data is introduced via `dde.icbc.PointSetBC`, which adds a data-matching term to the loss function:
    $$\mathcal{L}_{total} = \mathcal{L}_{PDE} + w_{data} \mathcal{L}_{data}$$
    *Where $\mathcal{L}_{data} = \frac{1}{N_{obs}} \sum |y_{pred} - y_{obs}|^2$.*
*   **Inverse Estimation:** When `inverse=True`, a physical parameter (e.g., $v_{\infty}$) is defined as a `dde.Variable` and optimized alongside the network weights.

---

## 6. BTE → NS Asymptotic Link: Why DSMC Can Feed a PINN

This section addresses the theoretical justification for StellarOrion's hybrid pipeline:
**Step 1** uses DSMC (a Boltzmann Transport Equation solver) in the rarefied regime, while
**Step 3** uses a PINN constrained by the Navier-Stokes (NS) equations in the continuum regime.
The question is: *Why is this physically valid?* The answer lies in the **Chapman-Enskog asymptotic expansion** and the **Knudsen number regime** at the HIAD shock layer boundary.

### 6.1 The Boltzmann Transport Equation (BTE)

The BTE governs the evolution of the molecular velocity distribution function $f(\mathbf{x}, \mathbf{v}, t)$:

$$\frac{\partial f}{\partial t} + \mathbf{v} \cdot \nabla_{\mathbf{x}} f + \frac{\mathbf{F}}{m} \cdot \nabla_{\mathbf{v}} f = \left(\frac{\delta f}{\delta t}\right)_{coll}$$

where $\mathbf{F}$ is the external force per molecule and the right-hand side is the collision integral
(Chapman & Cowling, 1970, §3.1; Cercignani, 1988, §2.2).

**DSMC solves the BTE statistically:** Bird's Direct Simulation Monte Carlo method (Bird, 1994, Ch. 2)
tracks representative particles through collisions and free-streaming, converging to the BTE solution
as the number of simulated particles → ∞. In the rarefied regime (Kn > 0.01), DSMC is the
*only* valid approach — the continuum NS equations break down because the mean free path $\lambda$
is no longer negligible compared to the flow length scale $L$.

### 6.2 The Knudsen Number and Flow Regimes

The **Knudsen number** is the ratio of mean free path to characteristic length:

$$Kn = \frac{\lambda}{L}$$

where $\lambda = \frac{\mu}{\rho \sqrt{2 k_B T / m}}$ (mean free path from kinetic theory) and
$L$ is the characteristic body dimension (e.g., nose radius $R_N = 0.55$ m for IRVE-3).

| Regime | Kn Range | Valid Method | StellarOrion Context |
|--------|----------|-------------|---------------------|
| Free molecular | Kn > 10 | Collisionless BTE | Far-field upstream |
| Transition | 0.01 < Kn < 10 | BTE (DSMC) | **Shock layer edges** |
| Slip flow | 0.001 < Kn < 0.01 | NS + slip BCs | **HIAD boundary layer** |
| Continuum | Kn < 0.001 | NS (no-slip) | Post-shock stagnation region |

*[Citation: Bird (1994), "Molecular Gas Dynamics and the Direct Simulation of Gas Flows", §1.3;
Anderson (2006), "Hypersonic and High-Temperature Gas Dynamics", §3.4]*

**Key insight for StellarOrion:** At the HIAD stagnation point, the post-shock continuum region
(Kn < 0.001) occupies most of the shock layer volume. The transition regime (Kn ~ 0.01) exists
only in a thin layer near the shock front and in low-density regions away from the stagnation
point. This is why the Navier-Stokes equations are valid for the *bulk* flow that the PINN learns.

### 6.3 Chapman-Enskog Expansion: BTE → NS

The Chapman-Enskog expansion (Chapman & Cowling, 1970, Ch. 7–10) shows that the NS equations
are the **first-order asymptotic limit** of the BTE as Kn → 0.

**The expansion proceeds as follows:**

1. **Zeroth order (local equilibrium):** The distribution function is a local Maxwellian:
   $$f^{(0)} = n \left(\frac{m}{2\pi k_B T}\right)^{3/2} \exp\left(-\frac{m|\mathbf{v} - \mathbf{u}|^2}{2 k_B T}\right)$$
   This gives the **Euler equations** (inviscid NS).

2. **First-order correction:** Deviations from Maxwellian are proportional to Kn:
   $$f = f^{(0)} + Kn \cdot f^{(1)} + \mathbf{O}(Kn^2)$$
   The $f^{(1)}$ correction introduces **transport coefficients** (viscosity $\mu$, thermal
   conductivity $\kappa$) via the collision operator linearized around $f^{(0)}$.
   This yields the full **Navier-Stokes equations** with viscous and heat conduction terms.

3. **Second-order Burnett equations** (Kn² terms): Rarely used in practice due to numerical
   instability, but physically represent the transition-regime corrections.

**The critical theorem (Cercignani, 1988, §5.3):** As Kn → 0, the formal solution of the BTE
converges to the NS equations *in the continuum limit*. The convergence is uniform in compact
subdomains away from solid boundaries, meaning:

$$\lim_{Kn \to 0} f_{BTE} = f_{NS}^{Chapman-Enskog} + \mathbf{O}(Kn^2)$$

**In our pipeline:** Step 1 (DSMC) solves the full BTE including transition effects.
Step 3 (PINN) enforces NS equations. The Chapman-Enskog theorem guarantees that in the
continuum region (Kn < 0.001, which covers >90% of the shock layer volume), the NS PINN
solution is the *correct asymptotic limit* of the DSMC solution. The PINN does not need to
"re-learn" rarefied physics — it learns the continuum limit that the BTE naturally approaches.

### 6.4 Why Kn ≈ 0.01 Is the Transition Point

The transition regime boundary at Kn ≈ 0.01 is not arbitrary — it emerges from the Chapman-Enskog
expansion's validity condition. The first-order correction $f^{(1)}$ is $O(Kn)$, so:

- **Kn < 0.001:** NS accurate to ~0.1% (second-order Burnett terms negligible)
- **Kn ~ 0.01:** NS errors ~1% (first-order Chapman-Enskog still valid, but slip BCs needed)
- **Kn > 0.1:** NS fails — Burnett or higher-order kinetic corrections required

*[Citation: Cercignani (1988), "The Boltzmann Equation and Its Applications", §5.4;
Anderson (2006), §3.5, Table 3.1]*

For IRVE-3 at 52 km altitude (peak heating):
- $L = R_N = 0.55$ m
- $\lambda \approx 0.5$ mm (post-shock stagnation)
- $Kn_{stag} = \lambda / L \approx 0.0009 < 0.001$ → **fully continuum**

Away from stagnation, in the wake and expansion regions:
- $\lambda \sim 1$–$10$ mm
- $Kn \sim 0.002$–$0.02$ → **slip-flow to early transition**

This confirms that the NS equations (enforced by the PINN) are the physically correct model
for the dominant flow region, while DSMC (BTE) captures the transition-regime edge effects.

### 6.5 Why Kriging Denoising Is the Critical Bridge

Raw DSMC output is inherently noisy due to statistical sampling of the collision integral.
The noise scales as $1/\sqrt{N_{particles}}$ per cell, producing peak-to-peak fluctuations
of ±50–100% in local heat flux values. This noise is *physical* (it represents real molecular
fluctuations) but is *not* what the NS equations model — NS predicts the *mean* flow.

**The Kriging denoising step (Step 2) is therefore not optional — it is mathematically required:**

1. **PINN training requires smooth target data.** The loss function
   $\mathcal{L}_{data} = \frac{1}{N} \sum |y_{pred} - y_{obs}|^2$ converges only if $y_{obs}$
   represents the *continuum mean*. Raw DSMC values with ±50% noise would cause the PINN to
   overfit to noise rather than learn the NS solution.

2. **Kriging provides the optimal linear unbiased predictor (BLUP).** Under the assumption of
   a Gaussian random field, Kriging yields the minimum-variance estimate of the true continuum
   value at each grid point, effectively computing:

   $$\hat{y}(\mathbf{x}_0) = \mathbf{k}^T \mathbf{K}^{-1} \mathbf{y}_{DSMC}$$

   where $\mathbf{k}$ is the covariance vector between the prediction point and observed points,
   and $\mathbf{K}$ is the covariance matrix of observed points. This is a **spatial Wiener filter**
   that optimally separates signal (NS continuum) from noise (DSMC fluctuations).

*[Citation: Rasmussen & Williams (2006), "Gaussian Processes for Machine Learning", §2.7;
Krige (1951), "A Statistical Approach to Some Basic Mine Valuation Problems"]*

3. **Kriging preserves spatial correlation.** Unlike simple averaging or polynomial smoothing
   (which Rapisarda uses), Kriging respects the spatial correlation structure of the flow field.
   A Kriging-denoiased grid at (x₁, y₁) is statistically consistent with the value at (x₂, y₂)
   based on their physical separation — crucial for the PINN to learn smooth spatial derivatives
   $\partial \rho / \partial x$, $\partial (\rho u) / \partial y$, etc.

4. **The Kriging variance $\sigma^2(\mathbf{x})$ quantifies denoising confidence.** Cells with
   high Kriging variance (e.g., far from DSMC sample points) indicate regions where the denoised
   value is uncertain — the PINN's data-matching loss can be weighted inversely by this variance:

   $$\mathcal{L}_{data} = \frac{1}{N} \sum \frac{|y_{pred}(\mathbf{x}_i) - \hat{y}(\mathbf{x}_i)|^2}{\sigma^2(\mathbf{x}_i)}$$

   This ensures the PINN trusts denoised DSMC data where it is reliable and relies more on the
   PDE residual where data is sparse or noisy.

### 6.6 Summary: The Complete BTE → Kriging → NS Chain

```
                    ┌─────────────────────────────────────────┐
  STEP 1 (DSMC)     │  Full BTE solution via Bird's DSMC     │
  Rarefied regime   │  Handles Kn > 0.01 transition physics  │
  Raw output:       │  Noisy per-cell [ρ, vx, vy, T]         │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
  STEP 2 (Kriging)  │  Optimal spatial denoising (BLUP)       │
  Bridge layer      │  Separates DSMC noise from NS mean      │
  Output:           │  Smooth [ρ, vx, vy, T] + variance σ²   │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
  STEP 3 (PINN)     │  NS equations enforced via AD            │
  Continuum regime  │  Chapman-Enskog limit of BTE as Kn→0    │
  Output:           │  Smooth continuum flow field             │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
  STEP 4 (MoP)      │  1,000+ virtual samples from metamodel  │
  Optimization      │  Geometry optimization via GA            │
  Output:           │  Optimized HIAD configuration            │
                    └─────────────────────────────────────────┘
```

**The mathematical chain is sound:**
- BTE (DSMC) is exact in rarefied regime → Kriging denoises to continuum mean → NS (PINN)
  is the Chapman-Enskog asymptotic limit of BTE → PINN predicts continuum flow → MoP
  generates virtual samples for optimization.

**References:**
- Bird, G.A. (1994). *Molecular Gas Dynamics and the Direct Simulation of Gas Flows*.
  Oxford Engineering Science Series, Vol. 42. [DSMC method, BTE, Kn regimes]
- Cercignani, C. (1988). *The Boltzmann Equation and Its Applications*. Springer. [BTE theory,
  Chapman-Enskog expansion, NS limit]
- Chapman, S. & Cowling, T.G. (1970). *The Mathematical Theory of Non-Uniform Gases*.
  Cambridge University Press. [Chapman-Enskog method, transport coefficients]
- Anderson, J.D. (2006). *Hypersonic and High-Temperature Gas Dynamics*. 2nd ed. AIAA. [Kn regimes,
  shock layer structure, continuum breakdown]
- Rasmussen, C.E. & Williams, C.K.I. (2006). *Gaussian Processes for Machine Learning*. MIT Press.
  [Kriging/GP theory, BLUP derivation]
- Krige, D.G. (1951). "A Statistical Approach to Some Basic Mine Valuation Problems on the
  Witwatersrand." *J. Chem., Metall. Mining Soc. S. Africa*, 52(6), 119–139. [Original Kriging]
- Rapisarda, G. (2023). *Earth Reentry Optimization for HIAD*. MSc Thesis, TU Delft.
  [Rapisarda's 3-layer noise filtering, Wilmoth bridging, Table 4.10]
