# Technical References & Theoretical Foundations

This document outlines the scientific theories, papers, and books that form the foundation of the StellarOrion Hypersonic Simulation Suite, as implemented in the `gui_backend.py` and the broader simulation pipeline.

## 1. Rarefied Gas Dynamics & DSMC
The simulation core utilizes the **Direct Simulation Monte Carlo (DSMC)** method to model high-altitude, rarefied hypersonic flows where the continuum assumption (Navier-Stokes) breaks down.

*   **Primary Text**: G. A. Bird, *Molecular Gas Dynamics and the Direct Simulation of Gas Flows*, Clarendon Press, Oxford, 1994.
*   **Solver (SPARTA)**: S. J. Plimpton, S. G. Moore, A. Borner, A. K. Stagg, T. P. Koehler, J. R. Torczynski, and M. A. Gallis, "Direct simulation Monte Carlo on petaflop supercomputers and beyond," *Physics of Fluids*, 31, 086101, 2019. [DOI: 10.1063/1.5108534](https://doi.org/10.1063/1.5108534)
*   **Software**: SPARTA DSMC Simulator ([http://sparta.github.io](http://sparta.github.io))

## 2. Mathematical Models & Equations

### Aerodynamics & Flight Metrics
The following equations are implemented in `gui_backend.py` to derive vehicle performance from DSMC results:

*   **Dynamic Pressure ($q$):**
    $$q = \frac{1}{2} \rho v_{\infty}^2$$
*   **Ballistic Coefficient ($\beta$):**
    $$\beta = \frac{m \cdot q}{F_{drag}}$$
*   **Instantaneous g-load ($n$):**
    $$n = \frac{F_{drag}}{m \cdot g_0}$$
*   **Heat Flux Proxy ($\dot{q}$):**
    $$\dot{q} = \frac{Q_{total}}{A_{ref}}, \quad A_{ref} = \pi \left(\frac{D}{2}\right)^2$$

### Thermal Protection System (TPS)
A 1D transient approximation is used to estimate backface heating for the flexible TPS:

*   **Radiative Equilibrium Surface Temperature ($T_s$):**
    $$T_s = \left( \frac{\dot{q}}{\sigma \epsilon} \right)^{1/4}$$
*   **Adiabatic Backface Temperature Rise ($\Delta T_{back}$):**
    $$\Delta T_{back} = \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{tps} \cdot C_{p,tps} \cdot \delta_{tps}}$$
    *Where $\eta_{lag}$ is the thermal lag factor (default 15%) and $\delta_{tps}$ is the thickness.*

### Survivability Optimization (SBO/GA)
The optimization loop uses a Metamodel Prognosis (MoP) trained via MSE loss:

*   **Objective Function (GA Cost):**
    $$J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{y} \left( \frac{y_{pred} - y_{target}}{1} \right)^2$$
*   **Metamodel Training Loss:**
    $$\mathcal{L} = \frac{1}{N} \sum_{i=1}^{N} (y_i - \hat{y}_i)^2$$

### Stochastic Sampling
*   **Stratified LHS Sampling:**
    $$x_i = x_{min} + (x_{max} - x_{min}) \cdot \frac{i + r}{N}$$
    *Where $i \in [0, N-1]$ is the sample index, $r \sim \mathcal{U}(0,1)$, and $N$ is the total number of samples.*

## 3. Hypersonic Aerothermodynamics
The calculations for heat flux, stagnation point proxies, and radiative equilibrium temperatures are based on established hypersonic theory.

*   **Reference Book**: J. D. Anderson, *Hypersonic and High-Temperature Gas Dynamics*, AIAA Education Series, 2nd Edition, 2006.
*   **Physics Implemented**: 
    *   Radiative equilibrium surface temperature ($\sigma \epsilon T^4$).
    *   Ballistic Coefficient ($\beta = m / (C_D A)$) for reentry trajectory analysis.

## 3. Atmospheric Modeling
The environment presets (Artemis/Earth) use the **NRLMSIS 2.1** empirical model for neutral atmosphere temperature and density.

*   **Primary Paper**: J. T. Emmert et al., "NRLMSIS 2.1: An empirical model of nitric oxide incorporated into MSIS," *Journal of Geophysical Research: Space Physics*, 127, e2022JA030896, 2022. [DOI: 10.1029/2022JA030896](https://doi.org/10.1029/2022JA030896)

## 4. Surrogate-Based Optimization (SBO)
The survivability optimization uses a metamodeling approach to reduce the computational cost of expensive DSMC simulations.

*   **Metamodel of Optimal Prognosis (MoP)**: T. Most and J. Will, "Meta-model of Optimal Prognosis—An automatic approach for variable reduction and optimal meta-model selection," *27th CADFEM Users’ Meeting*, Leipzig, Germany, 2009.
*   **Latin Hypercube Sampling (LHS)**: M. D. McKay, R. J. Beckman, and W. J. Conover, "A Comparison of Three Methods for Selecting Values of Input Variables in the Analysis of Output from a Computer Code," *Technometrics*, 21(2), 239-245, 1979.
*   **Machine Learning**: The metamodel is implemented via a multi-layer perceptron (PyTorch) using the MoP philosophy for steering Genetic Algorithms (GA).

## 5. HIAD Design & IRVE-3 Mission
The default geometry and simulation parameters are based on NASA's Hypersonic Inflatable Aerodynamic Decelerator (HIAD) project, specifically the IRVE-3 mission.

### IRVE-3 Default Parameters (Baseline)
| Parameter | Value | Reference |
| :--- | :--- | :--- |
| **Aeroshell Diameter** | 3.0 meters | NASA IRVE-3 Mission Specs |
| **Sphere-Cone Angle** | 60° (Half-Angle) | AIAA 2013-1386 |
| **Nose Radius** | 0.191 meters | NASA HIAD Geometry Baseline |
| **Toroid Count** | 7 Inflatable Rings | IRVE-3 Inflatable Structure |
| **Stowed Diameter** | 0.47 meters | Black Brant XI Payload Envelope |
| **Nominal Mass** | 281.0 kg | IRVE-3 Flight Hardware |

### Default Simulation Environment (Artemis/Lunar Return)
The default simulation settings in `main.py` and `gui_backend.py` are calibrated for a high-energy lunar return reentry, reflecting conditions similar to NASA's Artemis mission profile rather than the suborbital IRVE-3 test.

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| **Entry Velocity** | 10,500 m/s | Lunar-to-Earth return speed |
| **Stream Density ($n_{\rho}$)** | $3.9 \times 10^{20} \text{ m}^{-3}$ | Approx. 80km altitude (Earth) |
| **Stream Temperature** | 200.0 K | Standard Mesosphere temperature |
| **Heat Pulse Duration** | 450.0 s | Typical high-energy peak heating duration |
| **Surface Emissivity** | 0.88 | Silicon Carbide (SiC) fabric TPS |

### Mission References
*   Cassell et al., "Inflatable Re-entry Vehicle Experiment (IRVE-3) Flight Results," *AIAA 2013-1386*, 2013.
*   Lippincott et al., "Low-Earth Orbit Flight Test of an Inflatable Decelerator (LOFTID) Mission Overview," *AIAA 2019-3386*.
*   NASA's LOFTID (Low-Earth Orbit Flight Test of an Inflatable Decelerator) technical summaries.

## 6. Physics-Informed Neural Networks (PINNs)
The pipeline integrates a PINN refinement stage via DeepXDE to "fill the gaps" in noisy DSMC data and perform inverse parameter estimation.

*   **Software (DeepXDE)**: Lu, L., Meng, X., Mao, Z., and Karniadakis, G. E., "DeepXDE: A deep learning library for solving differential equations," *SIAM Review*, 63(1), 208-228, 2021. [DOI: 10.1137/19M1274067](https://doi.org/10.1137/19M1274067)
*   **Methodology**: G. E. Karniadakis, I. G. Kevrekidis, L. Lu, C. H. Pang, and M. Perdikaris, "Physics-informed machine learning," *Nature Reviews Physics*, 3, 422–440, 2021.
