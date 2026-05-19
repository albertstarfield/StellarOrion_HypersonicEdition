# StellarOrion Hypersonic Pipeline: Architecture & Data Flow

This document outlines the end-to-end "Input-to-Adjustment" lifecycle of the StellarOrion hypersonic simulation and optimization pipeline.

---

## 0. Project Architecture (ASCII Tree)
The following tree illustrates the hierarchy of Python modules, file-based calls, and C library interfacing.

```text
StellarOrion_HypersonicEdition/
├── main.py (Host/Docker Entry Point)
│   ├── [Host Mode]
│   │   ├── gui_launcher.py (UI Layer)
│   │   │   └── StellarOrionEngineMach5Up.py (Logic Controller)
│   │   └── [Headless Mode]
│   │       └── StellarOrionEngineMach5Up.py (Logic Controller)
│   └── [Docker Mode]
│       ├── build_sparta() ──> [cmake/make] ──> libsparta.so (C++)
│       └── run_simulation()
│           └── ctypes.CDLL ──> libsparta.so (C Library Interface)
│
├── StellarOrionEngineMach5Up.py (The Orchestrator)
│   ├── subprocess.run ──> CADDesign/HIAD_GeometryEngine.py (CAD Kernel)
│   ├── subprocess.run ──> [Docker Engine] ──> sparta-hysp (Physics)
│   ├── from source import visualizer (Post-processing)
│   └── import torch (Metamodel / MoP Training)
│
├── source/
│   └── visualizer.py (Visualization Engine)
│       ├── generate_animation() ──> [OpenCV/FFmpeg] ──> .mp4
│       └── upscale_2d_to_3d() ──> [Matplotlib] ──> .png
│
└── sparta/ (Sandia National Labs - C++ Source)
    ├── src/ (C++ Kernels)
    └── python/ (Python C-API Wrappers)
```

---

## 1. Input Parameters (The Configuration Space)
The process begins with user-defined or preset parameters that define the mission profile.

*   **Geometric Design ($X_{geo}$):**
    *   `diameter`: Main drag area control.
    *   `angle`: Cone half-angle (stability vs. drag).
    *   `nose_radius`: Controls shock standoff distance.
    *   `toroids`: Number of inflatable rings (structural stiffness).
    *   `thickness`: Thermal Protection System (TPS) insulation depth.
    *   `mass`: Payload weight (impacts ballistic loading).
*   **Environmental Physics ($X_{env}$):**
    *   `vstream`: Entry velocity ($v_{\infty}$).
    *   `nrho`: Number density at altitude ($n_{\rho}$).
    *   `temp_inf`: Ambient atmospheric temperature ($T_{\infty}$).
    *   `chem_mode`: Gas kinetics (5-species neutral air vs. 11-species ionized plasma).

---

## 2. Into SPARTA (The Physics Engine)
These parameters are converted into a format suitable for the **Direct Simulation Monte Carlo (DSMC)** solver (Bird, 1994).

1.  **Geometry Kernel:** `HIAD_GeometryEngine.py` uses the geometric parameters to generate a 2D axisymmetric surface file (`.surf`).
2.  **Computational Grid:** Although DSMC is particle-based, it requires a grid to efficiently manage **Collision Pairing** (restricting checks to $O(N)$ within cells rather than $O(N^2)$ globally) and to provide "buckets" for **Macroscopic Property Sampling** (averaging particle data into density/temperature fields).
3.  **Script Generation:** `StellarOrionEngineMach5Up.py` generates the `in.hiad` control script:
    *   **Collision Model:** Variable Soft Sphere (VSS).
    *   **Reaction Model:** Total Collision Energy (TCE) for chemical dissociation/ionization.
    *   **Boundaries:** Freestream inflow (Emit), Vacuum outflow, and Diffuse surface reflection.
3.  **Execution:** The simulation runs within a **Docker container** (Linux-based SPARTA) to ensure environmental parity across platforms (Plimpton & Gallis, 2014).

---

## 3. SPARTA Output (The Raw Physics)
The solver generates binary/text logs that describe the particle-level interactions:

*   **`surf.*.out`**: Force ($F_x, F_y, F_z$) and energy flux ($KE_{flux}$) for every surface element.
*   **`grid.*.out`**: Macroscopic gas properties in the domain cells (Number density, Velocity, Translational Temperature, Pressure).

---

## 4. Derived Variables (The Survivability Metrics)
The raw output is parsed and processed to produce high-level engineering metrics:

*   **Ballistic Coefficient ($\beta$):** $\beta = \frac{m \cdot q}{F_{drag}}$. Determines how well the vehicle sheds velocity.
*   **Peak Stagnation Heat:** The maximum $KE_{flux}$ recorded on the nose or toroids.
*   **Shock Layer Temperature:** The peak translational gas temperature in the shock wave.
*   **Radiative Surface Temp:** Surface temperature based on radiative equilibrium ($T_{surf} \propto \sqrt[4]{q}$).
*   **Backface Temperature:** Estimated internal payload temperature using a 1D transient thermal rise model.
*   **G-Load:** Deceleration intensity ($n = \frac{F_{drag}}{m \cdot g_0}$).

---

## 5. Optimization & MoP Role (The Intelligence)
The pipeline does not just run one simulation; it uses a **Surrogate-Based Optimization (SBO)** approach.

1.  **Sampling (LHS):** **Latin Hypercube Sampling** (McKay et al., 1979) generates a series of diverse input parameter sets (e.g., 5-20 samples) to explore the search space efficiently.
2.  **Training the Metamodel (MoP):** 
    *   **MoP** stands for **Metamodel Prognosis**. 
    *   A PyTorch-based neural network is trained on the results of the LHS samples.
    *   **Role:** The MoP learns the complex, non-linear mapping between geometry and physics (e.g., "how does changing the cone angle affect the backface temperature?").
3.  **Steering (Genetic Algorithm):**
    *   A Genetic Algorithm (GA) or random search "flies" through the MoP's predicted space.
    *   It tests 10,000+ virtual configurations per second to find the one that minimizes the cost function (e.g., Lowest Heat while keeping $\beta < 150$).

---

## 6. Back to Input with Adjustment (Closing the Loop)
Once the MoP and GA identify the **Optimal Configuration**:

1.  **Adjustment:** The original input parameters are "adjusted" to the optimal values found by the GA.
2.  **Validation:** The pipeline automatically triggers a **final SPARTA simulation** using these optimal parameters to verify that the MoP's prediction was accurate.
3.  **Result:** The final geometry, 3D upscaled visualizer, and flight metrics are presented to the user.

```mermaid
graph TD
    A[Input Parameters] --> B[HIAD_GeometryEngine.py / in.hiad]
    B --> C[SPARTA Solver]
    C --> D[Raw Out: surf/grid]
    D --> E[Derived Metrics: beta, heat, g-load]
    E --> F{Optimization Loop?}
    F -- Yes --> G[LHS Sampling]
    G --> B
    E --> H[MoP Training - PyTorch]
    H --> I[GA Steering / Selection]
    I --> J[Adjusted Best Parameters]
    J --> B
    F -- No --> K[Final Validation Result]

---

## 7. DeepXDE PINN Refinement (The Checkpoint Exchange)
To further accelerate and refine the simulation results, a **Physics-Informed Neural Network (PINN)** stage is integrated via **DeepXDE** (Lu et al., 2021).

1.  **Checkpoint Exchange:** The final "stable" flow field from SPARTA (DSMC) is used as a sparse point-cloud "anchor" for the PINN.
2.  **Physical Constraints:** Unlike the pure data-driven MoP, the PINN is constrained by the **2D Compressible Navier-Stokes Equations** (Anderson, 2006):
    *   Continuity ($\nabla \cdot (\rho \mathbf{u}) = 0$)
    *   Momentum ($\rho(\mathbf{u} \cdot \nabla)\mathbf{u} + \nabla p = 0$)
    *   Equation of State ($p = \rho R T$)
3.  **Gap Filling & Inverse Estimation:**
    *   **Gap Filling:** The PINN interpolates and "smooths" the noisy particle data from DSMC onto a high-resolution grid.
    *   **Inverse Parameter Estimation:** The model can be used to estimate unknown physical parameters (e.g., freestream conditions or reaction rates) by minimizing the residual between the PDE and the sparse DSMC observations.
4.  **Hardware Acceleration:** Training is accelerated using a wide range of global hardware platforms, providing near-real-time flow field refinement:
    *   **Tier 1:** NVIDIA CUDA, AMD ROCm, Apple Silicon (MPS).
    *   **Tier 2 (Intel/Mobile):** Intel OneAPI, OpenCL, Snapdragon/ARM GPU.
    *   **Specialized (Non-Western):** Huawei CANN (Ascend), Moore Threads MUSA, Biren SUPA, Innosilicon Fenghua, and Denglin GPU+.
```
