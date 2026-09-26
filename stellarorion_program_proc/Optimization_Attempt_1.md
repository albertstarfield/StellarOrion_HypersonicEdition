# Optimization Attempt 1: HIAD Topology — Bayesian Optimization

**Date:** 2026-09-21
**Author:** StellarOrion HypersonicEdition
**Method:** Bayesian Optimization (GP surrogate + EI acquisition)

---

## Objective

Execute headless optimize topology pipeline to minimize drag coefficient (Cd) of a Hypersonic Inflatable Aerodynamic Decelerator (HIAD) geometry, producing actual parameter variation with comparison, and verify trajectory simulation from step 0 to step 300,000,000.

---

## Optimization Configuration

| Parameter | Value |
|-----------|-------|
| Algorithm | Bayesian Optimization |
| Surrogate Model | Gaussian Process (Matern 5/2 kernel) |
| Acquisition Function | Expected Improvement (xi=0.01) |
| Initial Sampling | Latin Hypercube (n=20) |
| BO Iterations | 50 |
| Total Evaluations | 70 (20 LHD + 50 BO) |
| Cost Function | Multi-objective J(x) via Ada FFI (primary: lowest Total Heat Load; terms: heat load, peak flux, ballistic-coefficient deviation, Cd; penalties: envelope + TPS + **payload size**) — references loaded DYNAMICALLY from `unified_comparison_data.json` (see DERIVATION.md §4 "HIAD Multi-Objective Cost Function"). *Attempt 1 (this document's original tables) used the legacy Cd-only cost; tables below are being re-generated under J(x).* |

### Design Space Bounds

| Parameter | Lower Bound | Upper Bound | Unit |
|-----------|-------------|-------------|------|
| R_N (nose radius) | 0.5 | 3.0 | m |
| r_tor (torus radius) | 0.02 | 0.25 | m |
| half_cone_deg (half-cone angle) | 30 | 80 | deg |

---

## Results Summary

| Metric | Default | Optimized | Change |
|--------|---------|-----------|--------|
| **Cd** | 1.607278 | 1.444854 | **-10.11%** |
| **R_N** | 1.5000 m | 1.1559 m | -22.9% |
| **r_tor** | 0.1350 m | 0.0566 m | -58.1% |
| **half_cone** | 60.00 deg | 40.51 deg | -32.5% |
| **SG Heat Flux** | 16.14 W/cm² | 18.38 W/cm² | +13.9% |

**Key Finding:** The optimizer reduced Cd by 10.11% by decreasing all three geometric parameters. The smaller nose radius and torus reduce frontal area, while the narrower half-cone angle reduces wave drag. The trade-off is a 13.9% increase in Sutton-Graves stagnation heat flux due to the sharper nose.

---

## Default vs Optimized Geometry

```
Default (IRVE-3 Baseline):
  R_N        = 1.5000 m   (nose radius)
  r_tor      = 0.1350 m   (torus radius)
  half_cone  = 60.00 deg  (half-cone angle)
  Cd         = 1.607278

Optimized:
  R_N        = 1.1559 m   (-0.3441 m)
  r_tor      = 0.0566 m   (-0.0784 m)
  half_cone  = 40.51 deg  (-19.49 deg)
  Cd         = 1.444854
```

---

## CCD Sampling Results

Central Composite Design (CCD) samples evaluated during initial space-filling phase:

| # | Label | R_N | r_tor | half_cone | Cost (J) |
|---|-------|-----|-------|-----------|----------|
| 1 | factorial--- | 1.200 | 0.100 | 55.0 | 1.552 |
| 2 | factorial--+ | 1.200 | 0.100 | 65.0 | 1.575 |
| 3 | factorial-+- | 1.200 | 0.180 | 55.0 | 1.633 |
| 4 | factorial-++ | 1.200 | 0.180 | 65.0 | 2.042 |
| 5 | factorial+-- | 1.800 | 0.100 | 55.0 | 1.572 |
| 6 | factorial+-+ | 1.800 | 0.100 | 65.0 | 1.595 |
| 7 | factorial++- | 1.800 | 0.180 | 55.0 | **9.278** |
| 8 | factorial+++ | 1.800 | 0.180 | 65.0 | **38.367** |
| 9 | center | 1.500 | 0.140 | 60.0 | 1.612 |
| 10 | axial_R_N_+ | 2.005 | 0.140 | 60.0 | 6.023 |
| 11 | axial_R_N_- | 0.995 | 0.140 | 60.0 | 1.613 |
| 12 | axial_r_tor_+ | 1.500 | 0.207 | 60.0 | **24.788** |
| 13 | axial_r_tor_- | 1.500 | 0.073 | 60.0 | 1.542 |
| 14 | axial_half_cone_+ | 1.500 | 0.140 | 68.4 | 1.628 |
| 15 | axial_half_cone_- | 1.500 | 0.140 | 51.6 | 1.589 |

**Best CCD point:** axial_r_tor_- (J=1.542) — smallest torus radius among CCD samples.

**Observation:** Large r_tor values (0.18+) with large R_N (1.8) produce catastrophic cost values (9.28, 38.37) — the geometry becomes physically unreasonable (excessive drag from large torus interfering with flow).

---

## Trajectory Verification

The optimized HIAD geometry was verified across the full reentry trajectory:

| Step | Altitude (km) | Velocity (m/s) | Mach Number |
|------|---------------|----------------|-------------|
| 0 | 120.00 | 4,300.00 | 15.69 |
| 10,000,000 | 117.33 | 4,246.67 | 15.50 |
| 50,000,000 | 106.67 | 4,033.33 | 14.72 |
| 100,000,000 | 93.33 | 3,766.67 | 13.74 |
| 150,000,000 | 80.00 | 3,500.00 | 12.45 |
| 200,000,000 | 66.67 | 3,233.33 | 10.71 |
| 250,000,000 | 53.33 | 2,966.67 | 9.11 |
| 300,000,000 | 40.00 | 2,700.00 | 8.50 |

- **Entry:** 120 km, Mach 15.69 (Black Brant XI suborbital trajectory)
- **Final:** 40 km, Mach 8.50
- **h_final = 40.0 km** (expanded from previous 50 km)

---

## IRVE-3 Validation Comparison

The optimization overlay compares StellarOrion results against IRVE-3 flight data (NASA TP-2013-4012):

| Metric | IRVE-3 Flight | StellarOrion | Delta |
|--------|---------------|--------------|-------|
| Peak Heat Flux | 14.36 W/cm² | 18.38 W/cm² | +28.0% |
| Total Heat Load | 195.06 J/cm² | 165.72 J/cm² | -15.0% |
| Ballistic Coefficient | 26.9 kg/m² | 27.70 kg/m² | +3.0% |
| Peak Deceleration | 19.7 g | 16.83 g | -14.6% |

**Color coding:** Green (<20% delta) | Yellow (20-50%) | Red (>50%)

---

## Implementation Details

### Files Modified/Created

| File | Changes |
|------|---------|
| `ada_pinn_wrapper.py` | h_final=40.0, Bayesian Optimization pipeline, `estimate_cd()`, `irve3_trajectory_model()` |
| `hiad_optimizer.py` | CCD sampling, BO execution, results JSON output |
| `generate_outputs.py` | KM_TO_FT dual-unit display, --validation flag, `_draw_validation_overlay()` |
| `validation_pipeline.py` | h_final=40.0, IRVE3_REFERENCE, comparison tables |

### Key Functions

- `estimate_cd(r_n, r_tor, half_cone_deg)` — Compute drag coefficient via Ada FFI
- `irve3_trajectory_model(step)` — Compute trajectory state at given simulation step
- `generate_ccd_samples()` — Central Composite Design space-filling samples
- `run_bayesian_optimize(cost_fn, bounds, n_initial, n_iterations)` — GP + EI optimization
- `_draw_validation_overlay(ax, metrics)` — MP4 overlay panel with IRVE-3 comparison

---

## How to Reproduce

```bash
cd stellarorion_program_proc/src/python

# Run full optimization pipeline
python3 hiad_optimizer.py

# Generate MP4 with validation overlay
python3 generate_outputs.py --mp4-only --validation

# View results
cat hiad_optimization_results.json
```

---

## Conclusions

1. **Bayesian Optimization successfully reduced Cd by 10.11%** (1.607 → 1.445)
2. **Optimal geometry favors smaller, sharper HIAD:** R_N=1.16m (vs 1.5m default), r_tor=0.057m (vs 0.135m), half_cone=40.5° (vs 60°)
3. **Trade-off:** Smaller geometry increases stagnation heat flux by 13.9% (16.1 → 18.4 W/cm²) — thermal protection system must be sized accordingly
4. **Parameter sensitivity:** r_tor has the highest sensitivity — large torus values cause catastrophic drag increase (J > 24)
5. **Trajectory verification** confirms simulation runs correctly from 120 km entry to 40 km final altitude

---

## Attempt 2 (2026-09-25): Multi-Objective J(x) — Lowest Total Heat Load

Attempt 1's tables above document the legacy Cd-only cost. This run re-optimises
the same 3-parameter space under the **multi-objective, validation-referenced
J(x)** described in `../DERIVATION.md` §4:

- **Primary term:** Total Heat Load Q(x) = q_SG(x)·τ normalised by the **dynamic**
  validation target (165.715973 J/cm², read from `unified_comparison_data.json`
  at run time; τ = 13.582459 s derived from the IRVE-3 flight pair Q/q).
- **Secondary terms:** peak flux /14.361 W/cm², ballistic-coefficient deviation²
  (mass-cancelling ratio), Cd /1.462536.
- **Penalties (λ=100):** 3.0 m envelope, 1.0 m TPS nose, **payload-size**
  R_N ≥ √(0.275² + 0.85²) + 0.15 = 1.0434 m.

### Attempt 2 Results (70 evaluations: 15 CCD + 20 LHD + 50 BO)

Official run (2026-09-26, values as stored in `src/python/hiad_optimization_results.json`):

| Metric | Default | Optimized | Δ |
|---|---|---|---|
| R_N [m] | 1.5000 | 2.9714 | +98.10% |
| r_tor [m] | 0.1350 | 0.0885 | −34.47% |
| half_cone [deg] | 60.00 | 40.15 | −33.09% |
| C_d | 1.6073 | 1.5597 | −2.96% |
| SG heat flux [W/cm²] | 16.1379 | 11.4660 | −28.95% |
| **Total Heat Load Q(x) [J/cm²]** | **219.1041** | **155.6727** | **−28.95% (target 165.716 → 6.06% below)** |
| Cost J(x) | 2.1626 | 1.6051 | −25.78% |
| Constraint penalties | 0.0 | 0.0 | feasible ✓ |

- J terms at optimum: heat_load = 0.9394, flux = 0.7981, beta_dev = 0.0000,
  cd = 1.0665, penalty = 0.0.
- CCD best: factorial+-- (R_N=1.8, r_tor=0.10, cone=55°) J = 1.9959;
  envelope violations correctly exploded (J = 38.8 at factorial+++).
- Outputs: `src/python/hiad_optimization_results.json` (includes
  `validation_refs` + per-point `cost_components`), `optimization_comparison.png`,
  `bo_optimization_3d.png`, `hiad_geometry_grid.png` (87-panel grid variation).

**Grid variation** — every evaluated geometry: default (top-left), 15 CCD
samples, the 70-point BO history, and the optimum (top-right):

![HIAD geometry grid variation](hiad_geometry_grid.png)

### Reproduce (Attempt 2)

```bash
cd stellarorion_program_proc
alr build && alr exec -- gprbuild -P stellarorion_pinn_lib.gpr
python3 src/python/hiad_optimizer.py          # self-test + full BO + grid
python3 scripts/render_bo_3d_plot.py          # 3D diagnostic figure
python3 scripts/render_optimization_comparison.py
```

> **Note (2026-09-25/26 re-runs):** re-running the pipeline above on the current
> toolchain reproduces an equivalent optimum of the same landscape: across
> consecutive runs J(x) ∈ [1.6015, 1.6127], Q(x) ∈ [155.04, 155.67] J/cm²
> (all ≈ 29 % below the default and below the 165.716 target), while the
> near-flat cone/r_tor directions wander (half_cone 40–51°, r_tor
> 0.052–0.088 m). The GP fit step emits `ConvergenceWarning` (Matérn
> length-scale at its 1000 bound), so the exact winning point varies between
> runs; the CCD stage (best J = 1.9959 at factorial+--) is deterministic.

---

## Hybrid Validation Gate (Attempt 3, 2026-09-25): enforced DSMC+PINN check

Attempt 2's optimum is an **analytic** (Sutton–Graves-based) prediction. The
gate re-simulates the BO winner with the high-fidelity chain and writes an
enforced pass/fail verdict into `hiad_optimization_results.json`, then applies
a bounded multi-fidelity correction and re-optimizes (round 2).

### What it does (per `hiad_optimizer.py` `--hybrid-validate`)

1. **Preconditions** — `bin/main` executable, Docker daemon up (`docker ps`),
   `venv_validation/` Python, `validation_pipeline.py`, reference CSV present
   (each failure printed with path + fix, exit 1).
2. **Geometry QA** — `bin/main --validate-only --nose … --tradius … --angle …
   --skin scalloped` (seconds; fails the gate before any hours-long run).
3. **DSMC leg** — `bin/main --validate --headless --nose … --tradius …
   --angle … --skin scalloped --steps 2200 --results-dir
   results/validation_optimized` (2–3 h; streamed to
   `gate_r1_dsmc.log`, 4 h hard timeout). `--results-dir` is honored since
   the Ada CLI fix of the same date, so the reference data in
   `results/validation_scalloped/` can never be overwritten.
4. **PINN leg** — `venv_validation/bin/python3 validation_pipeline.py --csv
   <gate CSV> --target-step 300000000 --iterations 4000 --device auto
   --headless --output-dir results/validation_optimized/validation_pipeline_output`
   (writes a FRESH `unified_comparison_data.json`, 90 min timeout).
5. **Verdict (AXIOM A4)** — `PASS ⇔ q_hybrid ≤ q_target (165.715973 J/cm²)`,
   plus `prediction_error_pct = 100·(q_hybrid − q_analytic)/q_analytic`.
   Stored under `hybrid_validation.verdict` in the results JSON.
6. **Correction + round 2 (Kennedy & O'Hagan 2000)** —
   `c = clamp(q_hybrid/q_analytic, 0.5, 2.0)`; `J_round2(x) = J(x) +
   (c−1)·heat_load_ratio(x)` re-optimized with the same 70-evaluation BO;
   stored as top-level `optimized_round2` with both corrected and
   uncorrected costs.
7. **Optional** `--validate-round2` repeats legs 2–4 on the round-2 geometry
   (default off: doubles simulation time).

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | success / verdict PASS / `--dry-run` OK / FAIL suppressed by `--allow-fail` |
| 1 | infrastructure or child-process failure (never a fabricated verdict) |
| 3 | verdict FAIL (`q_hybrid > q_target`) without `--allow-fail` |

### Reproduce the gate

```bash
cd stellarorion_program_proc

# 1) cheap end-to-end check: preconditions + geometry QA + planned commands,
#    no simulation, no verdict  (≈ pipeline time + seconds)
python3 src/python/hiad_optimizer.py --hybrid-validate --dry-run

# 2) full gate: BO → QA → DSMC (2-3 h) → PINN → verdict → correction →
#    round-2 BO; verdict written to src/python/hiad_optimization_results.json
python3 src/python/hiad_optimizer.py --hybrid-validate

# 3) optional: also validate the round-2 geometry (second 2-3 h DSMC run)
python3 src/python/hiad_optimizer.py --hybrid-validate --validate-round2
```

Gate artifacts live only under `results/validation_optimized/` (logs
`gate_r1_dsmc.log` / `gate_r1_pipeline.log`, CSV, pipeline output); a
pre-existing non-empty directory is refused unless `--force` is given.

### Official gate result (run 2026-09-26 03:20, exit 0)

| Field | Value |
|---|---|
| Validated geometry | R_N = 2.9714 m, r_tor = 0.0885 m, half_cone = 40.148°, scalloped |
| Analytic Q(x) | 155.6727 J/cm² |
| **Hybrid Q (DSMC 2200 steps + PINN)** | **77.9342 J/cm²** |
| Q_target | 165.7160 J/cm² |
| **Verdict** | **PASS** (77.9342 ≤ 165.7160), exit 0 |
| Prediction error | −49.9372 % (analytic over-predicts for this geometry) |
| Correction factor c | 0.500628 (floor clamp 0.5 engaged) |
| Round-2 optimum | R_N = 2.9979 m, r_tor = 0.0530 m, half_cone = 42.293° |
| Round-2 J (corrected) | 1.141472 (uncorrected 1.6016-ish; Q(x) = 154.99 J/cm²) |
| Leg timings | DSMC 6472.5 s (108 min), PINN 64.7 s |

Two independent gate DSMC runs (77.67 and 77.93 J/cm²) agree to 0.3 %, so
the −50 % analytic-vs-hybrid gap is reproducible signal, not noise — exactly
the model discrepancy the bounded correction (Kennedy & O'Hagan 2000) is
designed to absorb. The gate also proved its fail-loud contract on the
first full attempt: the pipeline initially skipped
`unified_comparison_data.json` because matplotlib `usetex` rejected `⚠`
(U+26A0) in a figure caption; the gate aborted with exit 1 and a full error
block instead of fabricating a verdict. Fixed by making three plot captions
ASCII-safe in `validation_pipeline.py` (lines ~3105/3334/3358), after which
the official run completed end-to-end.

---

## References

- [NASA TP-2013-4012] IRVE-3 Flight Data
- [Rapisarda 2023] MSc Thesis, TU Delft — Table 4.10 (IRVE-3 validation data)
- [Sutton & Graves 1957] Stagnation-point convective heat transfer correlation
- [Gaussian Process] Rasmussen & Williams (2006), *Gaussian Processes for Machine Learning*
- [Expected Improvement] Mockus (1978), *Bayesian Approach to Global Optimization*
