# StellarOrion HypersonicEdition

**Author:** Albert Starfield Wahyu Suryo Samudro

**Supervised by:**
1. Dr.-Ing. Mochammad Agoes Moelyadi, ST., MSc.
2. Yohanes Bimo Dwianto, S.T., M.T., Ph.D.

---

StellarOrion is a high-fidelity aerothermodynamic simulation and optimization suite for Hypersonic Inflatable Aerodynamic Decelerators (HIAD). It leverages the **SPARTA DSMC** solver for rarefied gas dynamics (Plimpton & Gallis, 2014) and a **PyTorch-based Metamodel Prognosis** for survivability optimization.

> **Note:** `main.py` is **deprecated** as of 2026-08-21. All functionality has been
> ported to the Ada/SPARK binary. Use `python3 stellarorion_program_proc/run.py` instead.

## 🚀 Quick Start

```bash
cd stellarorion_program_proc
python3 run.py --self-test        # Run 13 verification tests
python3 run.py --test sample      # Run single SPARTA sample with 11-metric comparison
python3 run.py --help             # Show all CLI flags
```

## 🏗️ Architecture

This project uses a hybrid architecture for running simulations:

- **Ada/SPARK Binary:** Primary simulation engine (`stellarorion_program_proc/`). Compiled with Alire, formally verified with GNATprove (889 checks, 75% proved, 0 new failures). Handles all 21 CLI modes including validation, optimization, calibration, and integration tests.
- **Docker:** Used exclusively for running the SPARTA DSMC simulation in a containerized Linux environment.
- **Python Sidecar:** Native OS Python environment for PINN refinement (DeepXDE), PyFluent/PyAnsys integration, and GUI launcher. Supports NVIDIA CUDA, AMD ROCm, Apple Metal (MPS), Intel OneAPI/OpenCL, and specialized accelerators.

---

## 🛠️ Requirements & Installation

- **Docker:** Required for SPARTA simulation.
- **Python 3.10+**: Recommended (for build pipeline and PINN sidecar).
- **Ada/Alire:** Required for the primary simulation binary.
- **Dependencies:** Auto-installed by `run.py` (hash-gated venv).

```bash
cd stellarorion_program_proc
python3 run.py --help          # Show all CLI flags
python3 run.py --self-test     # Run 13 verification tests
```

---

## 🧮 Theory & Derivation

For all mathematical models (DSMC rarefied gas dynamics, aerothermodynamics, Sutton-Graves, radiative equilibrium, 1D thermal model, optimization cost functions, PINN Navier-Stokes), see **[DERIVATION.md](DERIVATION.md)**.

---

## 📊 Grid Independency & Optimization
To ensure the simulation accuracy balances computational cost, a **Grid Independency Test** was performed. The `grid-factor` (mesh density multiplier) was evaluated against reference data from the **IRVE-3 MDAO (Multidisciplinary Design Analysis and Optimization)** paper.

*   **Test Range:** 0.3 to 1.0
*   **Optimal Result:** `0.7`
*   **Rationale:** At a factor of `0.7`, the simulation yields the least error compared to validated flight data and high-fidelity reference cases, while maintaining efficient execution times. Consequently, **0.7 is now the default grid factor** for all simulation runs.

Users can manually override this via:
```bash
cd stellarorion_program_proc && python3 run.py --grid-factor 1.0 --test sample
```

## 🛰️ HIAD Validation: Unified Comparison (IRVE-3 vs LOFTID vs Models vs StellarOrion)

StellarOrion is validated against **IRVE-3 flight data** (NASA TP-2013-4012) and **LOFTID flight data** (Deshmukh et al. AIAA 2024-1501, Hollis et al. AIAA 2024-1498), alongside analytical/CFD models (Sutton-Graves, Fay-Riddell). All sources are compared side-by-side below.

### Combined Validation Table

| Parameter | IRVE-3 Flight | LOFTID Flight | Rapisarda Models | StellarOrion DSMC | Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Aeroshell Diameter** | 3.0 m | 6.0 m | — | — | NASA TP-2013-4012; Deshmukh AIAA 2024-1501 |
| **Peak Heat Flux ($\dot{q}$)** | **14.36 W/cm²** | **39.27 W/cm²** | 13.83 W/cm² (FR) / 15.26 W/cm² (SG) | 182.5 W/cm² (single cell, noisy) / **56.6 W/cm²** (per-element avg) | Rapisarda Table 4.10; Deshmukh AIAA 2024-1501; StellarOrion |
| **Total Heat Load ($Q$)** | **195.06 J/cm²** | **3,520 J/cm²** | 195.17 J/cm² (FR) / 223.95 J/cm² (SG) | **165.72 J/cm²** | Rapisarda Table 4.10; Deshmukh AIAA 2024-1501; StellarOrion |
| **Ballistic Coeff ($\beta$)** | 26.9 kg/m² | ~22.6 kg/m² (est.) | — | **27.70 kg/m²** | NASA TP-2013-4012; Discussion.md; StellarOrion |
| **Peak Deceleration** | **19.7 g** | **9.66 g** | — | **16.83 g** | NASA TP-2013-4012; Deshmukh AIAA 2024-1501; StellarOrion |
| **C_d** | — | — | — | **1.4625** | StellarOrion (within LOFTID range 1.4–1.7) |
| **L/D** | — | — | — | **0.3802** | StellarOrion |
| **Entry Velocity** | ~3.5–4.5 km/s | >8.0 km/s | — | — | Discussion.md (Sutton-Graves V³ scaling) |

**Column key:**
- **IRVE-3 Flight** — NASA TP-2013-4012 (suborbital, Wallops Island, Black Brant XI)
- **LOFTID Flight** — Deshmukh et al. AIAA 2024-1501 / Hollis et al. AIAA 2024-1498 (LEO, 6 m, >8 km/s)
- **Rapisarda Models** — Rapisarda (2023, MSc Thesis, TU Delft) Table 4.10: Fay-Riddell (FR) CFD and Sutton-Graves (SG) correlation applied to IRVE-3 trajectory
- **StellarOrion DSMC** — Our SPARTA DSMC simulation (Sep 2, 2026, scalloped geometry, step 2200, 6 MPI ranks)

### Simulation Environment Conditions

Each source uses different atmosphere models, geometry, and solvers — this directly affects comparability.

| Condition | IRVE-3 Flight | LOFTID Flight | Rapisarda Models | StellarOrion DSMC |
| :--- | :--- | :--- | :--- | :--- |
| **Atmosphere Model** | Actual atmosphere | Actual atmosphere | MCD v6.1 (~56% higher density than ISA at 52 km) | ISA |
| **Gas Composition** | Real air | Real air | Earth air (MCD v6.1 for density/temp profiles only) | Five_Species: N₂, O₂, NO, N, O |
| **Geometry** | IRVE-3 inflatable (3.0 m) | LOFTID inflatable (6.0 m, 70° sphere-cone, 6+1 tori) | Smooth toroid ($r_{torus}$ = 0.135 m) | **Scalloped** (grooved-torus), 3.0 m |
| **Solver Method** | Flight instrumentation | Flight instrumentation | Fay-Riddell CFD / SG correlation | SPARTA DSMC (VSS, grid 0.7) |
| **Trajectory** | Full reentry (Black Brant XI, suborbital) | Full reentry (LEO, >8 km/s) | Full trajectory integration | **Single point** (step 2200) |
| **Noise Filtering** | Hardware averaging | Hardware averaging | 6th-order polynomial + Wilmoth | Raw per-element `f_1[3]` |

**Why this matters:** The −15% delta in heat load and g-load is expected — StellarOrion runs a single trajectory point while flight data and Rapisarda's models integrate over the full trajectory. The density difference between MCD v6.1 and ISA (56% at 52 km) explains part of the gap between our single-point SG (12.2 W/cm²) and Rapisarda's trajectory-integrated SG (15.26 W/cm²), since $\dot{q}_{SG} \propto \sqrt{\rho}$.

**Notes on DSMC peak heat flux:** The 182.5 W/cm² single-cell value is raw DSMC `f_1[3]` noise (one noisy point-sample). The per-element average (56.6 W/cm²) is the physically meaningful metric — it sits between Sutton-Graves (conservative, 12.2 W/cm² at single-point) and Fay-Riddell (aggressive, 161.6 W/cm²). See DSMC Noise Methodology section below.

**Delta analysis:**
- **Heat load:** StellarOrion (165.72 J/cm²) is −15% vs flight (195.06) — single trajectory point vs full integrated trajectory
- **G-load:** StellarOrion (16.83 g) is −15% vs flight (19.7 g) — same single-point vs trajectory explanation
- **Ballistic coeff:** StellarOrion (27.70 kg/m²) is +3% vs flight (26.9) — confirms geometry fidelity of the scalloped model

**Plots generated:** 51 PNGs total (21 CSV time-series + 6 derived thermal + 24 VTU visualizations).

See `stellarorion_program_proc/results_validation_scalloped/VALIDATION_Sep_2_2026.md` for full results.

Users can run the automated calibration suite using:
```bash
cd stellarorion_program_proc && python3 run.py --compareCalibrate --solver sparta --steps 1000
```

### IRVE-3 Rapisarda Testing Variant: Mars Chemistry Mode

StellarOrion supports a `--chemistry mars` mode using a CO2-dominated atmosphere model (`mars.vss`, `mars.react`). This is relevant because Rapisarda (2023) used the **Mars Climate Database v6.1 (MCD v6.1)** as a cross-validation technique — applying Mars-derived atmosphere data to Earth re-entry validation.

**Key distinction (from source code comments in `stellarorion_sparta.adb` ~line 2601):**
- IRVE-3 is an **Earth re-entry** mission (Wallops Island VA, Black Brant XI)
- Our code uses ISA (International Standard Atmosphere) — correct for Earth
- Rapisarda's MCD v6.1 gives ~56% higher density than ISA at 52 km
- Since SG ∝ √ρ, this density ratio (1.564) produces a 25% higher SG heat flux
- This explains part of the gap between our single-point SG (12.2 W/cm²) and Rapisarda's trajectory-integrated SG (15.26 W/cm²)

**Usage:**
```bash
cd stellarorion_program_proc && python3 run.py --chemistry mars --test sample --steps 1000
```

## 🔬 DSMC Noise Methodology: Raw DSMC vs Post-Processed DSMC

Both StellarOrion and Rapisarda (2023) use DSMC — it is the standard method for rarefied gas dynamics (Bird, 1994). The difference is in how the raw DSMC output is processed:

Rapisarda (2023, MSc Thesis, Delft University of Technology) used Moss et al. (2006) stagnation-point DSMC data and applied three layers of noise filtering:

1. **Pre-processed data** — Moss's published values were already time-averaged over many particle timesteps
2. **6th-order polynomial fit** — Smoothed residual scatter and extrapolated into the free-molecular flow regime (R²→1) (Sec 4.5.1, Fig 4.40, Table 4.13)
3. **Wilmoth bridging function** — Fitted to polynomial-smoothed data via non-linear least-squares (R²=0.99138 per thesis text; Table 4.15 reports R²=0.9792 for the specific coefficient fit) (Sec 4.4.5, Fig 4.41, Table 4.15)

**Contrast with our approach:** Both StellarOrion and Rapisarda use DSMC — it is the standard method for rarefied hypersonic flow (Bird, 1994). The difference is post-processing. We read raw per-element `f_1[3]` (kinetic energy flux, W/m²) from SPARTA surf dumps and apply no smoothing. The max-cell value is a single noisy point-sample. Negative values at later steps (e.g., −10,570 W/m² at step 2200) are DSMC statistical noise — inherent to any raw DSMC output. Rapisarda's 3-layer filtering (polynomial fit + Wilmoth bridging) removes this noise at the cost of introducing model-dependent smoothing. Three code comment blocks in `stellarorion_sparta.adb` (~lines 388, ~2057, ~2185) document this noise context and cite Rapisarda's methodology.

See `stellarorion_program_proc/results_validation_scalloped/VALIDATION_Sep_2_2026.md` Section 9 for full comparison.

## 📝 Code Updates (Ada/SPARK)

### Ada Fixes Applied

| Fix | File | Description |
| :--- | :--- | :--- |
| **Sin_Rad/Cos_Rad range reduction** | `stellarorion_geometry.adb` | Fold large arguments into [-π, π] for Taylor series accuracy |
| **Run_SPARTA surf copy path** | `stellarorion_sparta.adb` | Read surf file from `Results_Dir`, not hardcoded repo root |
| **Parse_Surf_Geometry state exit** | `stellarorion_sparta.adb` | Exit State=1 when "Lines" keyword detected, preventing Curve corruption |
| **Heat_Flux_Avg dimensional correction** | `stellarorion_sparta.adb` | Changed from `Heat_Sum / Surf_Area` (W/m⁴) to `Heat_Sum / Float(N)` (W/m²) |
| **VTU connectivity spacing** | `stellarorion_sparta.adb` | Fixed missing space after N3 in quad connectivity (VTK XML parse error) |

### DSMC Noise Documentation (Code Comments)

Three comment blocks added to `stellarorion_sparta.adb` documenting:

1. **~line 388**: DSMC noise context near surf compute/fix commands — why SPARTA "reduce max" on `f_1[3]` produces noise, Rapisarda's 3-layer strategy, future work options
2. **~line 2057**: Per-element heat flux parsing near `Heat(Row) := V(4)` — noise source, negative values, Rapisarda's polynomial smoothing
3. **~line 2185**: Per-element average vs Rapisarda's polynomial near `Avg_Heat_Flux := Heat_Sum / Float(N)` — 3 types of data (flight area-weighted, Rapisarda polynomial-smoothed, our raw per-element)

### GNATprove Level 4 Validation

- 889 checks total, 666 proved (75%), 35 justified (4%), 54 unproved (6%)
- All 54 unproved checks are pre-existing in other units (not in `stellarorion_sparta.adb`)
- 0 new failures introduced by code changes

## 📄 Documentation

| Document | Path | Content |
| :--- | :--- | :--- |
| **Discussion** | `stellarorion_program_proc/Discussion.md` | 12 numbered sections (1–10, 12–13) + Appendix: vehicle comparison, IRVE-3/LOFTID data, DSMC results, delta comparison, SG vs FR analysis, physics verification, optimization chain |
| **Validation** | `stellarorion_program_proc/results_validation_scalloped/VALIDATION_Sep_2_2026.md` | 11 numbered sections (1–11) + References: simulation config, convergence, results, comparison, heat flux investigation, 51 plots, survivability, code fixes, DSMC noise methodology, storage paths, open items |

### Discussion.md Sections (12 + Appendix)

1. Executive Summary
2. Vehicle Comparison (Rapisarda Table 4.1)
3. IRVE-3 Validation Data (Rapisarda Table 4.10, NASA TP-2013-4012)
4. LOFTID Flight Data (Deshmukh AIAA 2024-1501, Hollis AIAA 2024-1498)
5. StellarOrion DSMC Validation Results — includes:
   - 5.4 Delta Comparison: StellarOrion vs Rapisarda IRVE-3 vs Flight
   - 5.5 Sutton-Graves vs Fay-Riddell: When Each Is Good, When Each Fails
   - 5.6 Mathematical Derivation: Why Our DSMC, Fay-Riddell, and Sutton-Graves Give Different Answers
6. Cross-Mission Comparison Table
7. Rapisarda Model Performance Across Missions
8. StellarOrion Physics Verification (GNATprove)
9. Key Findings and Next Steps
10. IRVE-3 Rapisarda Baseline → Earth Reentry Optimization Chain
12. Key Success Variables: What Determines Mission Success?
13. References
- Appendix A: Raw StellarOrion DSMC Data

## 📦 Split Archive Files

Large weekly report archives (>50 MB) are split into 25 MB chunks for GitHub compliance:

```bash
# Reassemble split archives locally
cd Lost+Found/ProgressReport && bash reassemble.sh
```

Original `.tar.zst` files are excluded from git tracking (see `.gitignore`). Split parts are tracked.

## 📚 References
For detailed scientific citations and mission parameters (IRVE-3, LOFTID), see [REFERENCES.MD](REFERENCES.MD).
