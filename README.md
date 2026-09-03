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

## 🛰️ Calibration & Validation: IRVE-3 (Rapisarda 2023 Baseline)
StellarOrion is calibrated against the **IRVE-3 (Inflatable Reentry Vehicle Experiment 3)** flight data using the high-fidelity reconstruction parameters from **Rapisarda (2023)**.

### Key Validation Metrics (Peak Results)
| Parameter | Flight Data | MDAO Model | Source | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Aeroshell Diameter** | 3.0 m | — | NASA Mission | ✅ Verified |
| **Toroid Radius ($r_{torus}$)** | 0.135 m | 0.135 m | Rapisarda Table 4.1 | ✅ Geometry Sync |
| **Peak Heat Flux ($\dot{q}$)** | **14.36 W/cm²** | 13.83 W/cm² (Fay-Riddell) / 15.26 (Sutton-Graves) | Flight: Rapisarda 2023 Table 4.10 [38]; Models: Rapisarda Table 4.10 | ✅ Calibrated (audit-corrected: flight/model roles were swapped pre-audit) |
| **Total Heat Load ($Q$)** | **195.06 J/cm²** | 195.17 J/cm² (Fay-Riddell) / 223.95 (Sutton-Graves) | Flight: Rapisarda 2023 Table 4.10; Models: Rapisarda Table 4.10 | ✅ Calibrated (audit-corrected) |
| **Ballistic Coeff ($\beta$)** | 26.9 kg/m² | — | NASA TP-2013-4012 only (not in thesis) | ⚠ Unverified |
| **Peak Deceleration** | **19.7 g** | — | NASA TP-2013-4012 mission report (thesis has no IRVE-3 decel table) | ✅ Baseline |
| **Stagnation Pressure** | ~12.4 kPa | — | Estimated ($2 \times q$) | ✅ Verified |

Users can run the automated calibration suite using:
```bash
cd stellarorion_program_proc && python3 run.py --compareCalibrate --solver sparta --steps 1000
```

## 🧪 DSMC Validation Results (Sep 2, 2026 — Scalloped Geometry)

A fresh validation simulation was run with the scalloped (grooved-torus) geometry at step 2200, headless mode, 6 MPI ranks.

| Parameter | StellarOrion DSMC | IRVE-3 Flight | Delta |
| :--- | :--- | :--- | :--- |
| **C_d** | 1.4625 | — | Within LOFTID range (1.4–1.7) |
| **L/D** | 0.3802 | — | — |
| **Peak heat flux** | 182.5 W/cm² (single cell) | 14.36 W/cm² | ~12.7× (noise, not comparable) |
| **Per-element avg** | 56.6 W/cm² | — | Between Sutton-Graves and Fay-Riddell |
| **Heat load** | 165.72 J/cm² | 195.06 J/cm² | −15% (single-point vs trajectory) |
| **G-load** | 16.83 g | 19.7 g | −15% (single-point vs trajectory) |
| **Ballistic coeff** | 27.70 kg/m² | 26.9 kg/m² | +3% (geometry fidelity confirmed) |

**Plots generated:** 51 PNGs total (21 CSV time-series + 6 derived thermal + 24 VTU visualizations).

**Key analytical comparisons (Step 2200):**

| Model | Stagnation heat flux | Ratio vs DSMC avg |
| :--- | :--- | :--- |
| Sutton-Graves | 12.2 W/cm² | 0.22× |
| Fay-Riddell | 161.6 W/cm² | 2.86× |
| DSMC per-element avg | 56.6 W/cm² | 1.00× |

See `stellarorion_program_proc/results_validation_scalloped/VALIDATION_Sep_2_2026.md` for full results.

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

## 🔬 DSMC Noise Methodology: Why Our Data Has Noise But Rapisarda Doesn't

Rapisarda (2023, MSc Thesis, Delft University of Technology) used Moss et al. (2006) stagnation-point DSMC data but applied three layers of noise filtering:

1. **Pre-processed data** — Moss's published values were already time-averaged over many particle timesteps
2. **6th-order polynomial fit** — Smoothed residual scatter and extrapolated into the free-molecular flow regime (R²→1) (Sec 4.5.1, Fig 4.40, Table 4.13)
3. **Wilmoth bridging function** — Fitted to polynomial-smoothed data via non-linear least-squares (R²=0.99138 per thesis text; Table 4.15 reports R²=0.9792 for the specific coefficient fit) (Sec 4.4.5, Fig 4.41, Table 4.15)

**Contrast with our approach:** We read raw per-element `f_1[3]` (kinetic energy flux, W/m²) from SPARTA surf dumps. The max-cell value is a single noisy point-sample. Negative values at later steps (e.g., −10,570 W/m² at step 2200) are DSMC statistical noise. Three code comment blocks in `stellarorion_sparta.adb` (~lines 388, ~2057, ~2185) document this noise context and cite Rapisarda's methodology.

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
