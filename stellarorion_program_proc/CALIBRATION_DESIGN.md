# CALIBRATION DESIGN — analytic/DSMC geometry unsync fix + DSMC calibration of the screening model

**Status**: IMPLEMENTING (all stages approved 2026-10-21)
**Owner**: OpenAgent (thread "1st thread of StellarOrion Programmer")
**Scope**: Stages 0-3 of the plan agreed in the "Why not calibrated for the residuals?" thread.

---

## 1. Diagnosis (measured, not assumed)

### 1.1 The DoE is model-space
`grep -i "dsmc|sparta|docker"` over `src/simulation_engine/stellarorion_optimization.adb`,
`stellarorion_optimizer_core.adb`, `stellarorion_ga_runner.adb` returns **nothing but comments**.
The whole optimisation path is analytic:

- `Run_SBO_GA` builds the 2^3 coded CCD design, evaluates
  `Components := HIAD_Cost_Components (X_Analytic)` (`stellarorion_optimization.adb:1811`),
  fits the surrogate, then runs the GA with `Eval => SBO_Fitness'Access` (:1837).
- `SBO_Fitness` (:681-747) = `HIAD_Cost_Components (X)` + `Surrogate_Predict` + `HIAD_Cost_Function (X)`.

Consequence: the 15 CCD points, the surrogate, every GA evaluation, the CCD sensitivity
figure and the "W_Cd ~ 21 regime switch" describe **the analytic model**, not the vehicle.
They must be labelled model-space diagnostics.

### 1.2 The unsync (THE BUG)
The analytic parameterisation, the GA genes, the runner's flags and the DSMC geometry are
four different geometries.

| quantity | analytic model | what the DSMC flew |
|---|---|---|
| X(1) | `Diameter_M/2`, i.e. the **nose/cone junction** radius (`Compute_Max_Radius`: `R_Tang := R_N*cos(Gamma); S_Last := (2*N_Tori-1)*R_Tor; R_Target := R_Tang + S_Last*cos(Gamma); return R_Target + R_Tor`) | the runner passed `--nose 1.039670` = the **nose bluntness** radius |
| body diameter | 2*X(1) ~ 2.08 m | 3.0 m (`--diameter` was never passed) |
| frontal area | `pi*R_Max^2` = 28.42 m^2 | `pi*(D/2)^2` = 7.07 m^2 (`stellarorion_sparta.adb:3664`) |
| nose radius used by Sutton-Graves | X(1) = 1.5 (the junction radius, wrong) | `Geo.Nose_Radius_M` = 0.55 (the reference) / 1.03967 (the candidate) |

Verification of the analytic side: for X = (1.03967, 0.219741, 53.7247) the analytic
`R_Max` computes to 3.0061 m, and the recorded penalty 0.00569535 = `Lambda_Pen*(R_Max-3)^2`
back-solves to 3.007547 m — they agree, so the analytic geometry is self-consistent and the
**vehicle** is the thing that is wrong.

Verification of the nose-radius split: the SG column ratio is
88 971.71/122 029.44 = 0.72913, and `sqrt(0.55/1.03967)` = 0.72743 (0.2 %) — so the
reference flew a 0.55 m nose and the candidate a 1.03967 m nose, while the analytic model
used 1.5 for the reference (inflating its heat term by `sqrt(1.5/0.55)` = 1.65).

### 1.3 Two more reporting defects that make any calibration impossible
- `heat_load_jcm2` is **analytic in both runs**: `stellarorion_sparta.adb:1753`
  `Result.Heat_Flux_Wm2 := C_SG * Sqrt(Rho_Inf/Nr) * Vstr**3` and `:1870`
  `Result.Total_Heat_Load := Result.Heat_Flux_Wm2 * 13.58;`. The CSV column
  `heat_flux_sg_Wm2` is the same correlation (:3212). Identity verified for both runs:
  `heat_load_jcm2 == heat_flux_sg_Wm2 * 13.58/10000`, constant over all 22 steps.
  The genuinely DSMC-measured fluxes are `heatflux_avg` / `heatflux_max`.
  The DSMC surface heat load (time-integrated over the trajectory) is **not recorded**.
- The recorded `cd` is **clamped**: `stellarorion_sparta.adb:3276` and `:3348`
  `if Match_CD > 3.0 then Match_CD := 3.0;`. The blunt candidate saturates it
  (flat `cd = 3.000000` at every step) while the raw force ratio is 8.67-12.02.
  The reference never clips (1.748-2.423).

### 1.4 Flight-state constant still to be reconciled
Both runs' `heat_flux_sg_Wm2` sits ~2.056x below the value predicted by the nominal
sim condition quoted in the source comment (51.82 km, 3379 m/s, rho = 7.696e-4,
C_SG = 1.7415e-4). The factor is identical in both runs, so it is a shared constant
(the flight state used by the SG column vs the state's recorded in the CSV rows), not a
geometry effect. Stage 0 must determine and document it.

---

## 2. THE CONVENTIONS (fixed here, used everywhere — single source of truth)

### 2.1 Geometry mapping (THE fix)
New public subprogram in `StellarOrion_Optimization`:

```ada
--  Nose-to-body radius ratio of the IRVE-3 reference vehicle
--  (0.55 m nose / 1.5 m body radius). FIXED BY THE REFERENCE GEOMETRY.
Nose_Radius_Ratio : constant Float := 0.55 / 1.5;   -- 0.366666667

procedure Analytic_To_Physical (X : Param_Vector; Geo : out Geometry_Parameters);
procedure Physical_To_Analytic (Geo : Geometry_Parameters; X : out Param_Vector);
```

`Analytic_To_Physical` mapping (exact):

| physical field | value | why |
|---|---|---|
| `Geo.Diameter_M` | `2.0 * X(1)` | X(1) is the body/junction radius; the analytic model computes `R_Max` from it, so D = 2*R_N keeps the two consistent |
| `Geo.Nose_Radius_M` | `Nose_Radius_Ratio * X(1)` | the bluntness radius SCALES with the body so the vehicle family keeps the IRVE-3 nose/body ratio (0.55 at the 1.5 m reference radius). Fixed 0.55 would make the SG term geometry-independent |
| `Geo.Toroid_Radius_M` | `X(2)` | direct |
| `Geo.Angle_Deg` | `X(3)` | direct |
| `Geo.Toroid_Count` | `Default_N_Tori_MOP` (6) | the analytic model's torus count |
| everything else | the `Geometry_Parameters` defaults | no other gene is modelled |

**Consequence (intentional)**: the reference anchor X_ref = (1.5, 0.135, 60) maps to
D = 3.0 m, nose = 0.55 m, torus = 0.135 m, cone = 60 deg — i.e. **exactly the reference
DSMC geometry that was already flown**. The existing reference run therefore remains the
calibration anchor (no 2 h re-fly needed). The candidate X* = (1.03967, 0.219741, 53.7247)
maps to D = 2.07934 m, nose = 0.381409 m, torus = 0.219741 m, cone = 53.7247 deg — the
vehicle that must be flown from now on.

### 2.2 Heat term
`HIAD_Cost_Components` must call Sutton-Graves with the **physical** nose radius
`Nose_Radius_Ratio * X(1)`, not `X(1)`. This makes the analytic heat term and the DSMC's
own SG column use the same nose radius. (The reference's analytic heat term changes from
the inflated `sqrt(1.5/0.55)` = 1.65x back to the flown 0.55 m nose.)

### 2.3 Frontal area
The analytic model's presented frontal area is `pi*R_Max^2` (the toroidal vehicle's
projected area). The DSMC side must record **both** the body-area normalisation
(`pi*(D/2)^2`, the legacy one) and the presented-area normalisation (`pi*R_Max^2`) so the
comparison is never ambiguous. The recorded `cd` keeps its legacy meaning (body area) but
the clamp is removed and the raw values are reported.

### 2.4 New CSV columns (APPENDED — the existing column order and indices never change)
`step, drag_sum_N, lift_sum_N, heatflux_max_Wm2, heat_sum_Wm2, heatflux_avg_Wm2,
heat_flux_sg_Wm2, drag_avg_N, lift_avg_N, time_s, alt_km, vel_ms, mach, dyn_press_pa, cd,
cl, g_load, downrange_km, heat_load_jcm2, ambient_pressure_pa, ambient_temp_k,
heat_flux_fr_wm2,`
then the new ones:
```
cd_unclamped, cd_raw_body_area, cd_raw_presented_area,
dsmc_surface_heat_load_jcm2,
geom_diameter_m, geom_nose_radius_m, geom_toroid_radius_m, geom_angle_deg,
ref_area_body_m2, ref_area_presented_m2
```
Definitions:
- `cd_unclamped` = the DSMC drag force ratio with NO clamp (the same formula the clamped
  `cd` uses, before `if > 3.0 then := 3.0`).
- `cd_raw_body_area` = `drag_sum_N / (dyn_press_pa * pi * (D/2)^2)`.
- `cd_raw_presented_area` = `drag_sum_N / (dyn_press_pa * pi * R_Max^2)`.
- `dsmc_surface_heat_load_jcm2` = the DSMC's OWN peak area-averaged surface heat load over
  the SAME effective 13.58 s heating window the analytic objective uses:
  `Q = max_i ( heatflux_avg_i ) * 13.58 / 10000` in J/cm^2 (1 J/m^2 = 1e-4 J/cm^2).
  The value is a per-run scalar, so every row carries the same number.
  **RECORDED DEVIATION (2026-10-21).** The first wording of this column was a right-hand
  Riemann sum `Q = sum_i heatflux_avg_i * (t_{i+1} - t_i)` over the CSV rows. That was
  abandoned after measuring two facts: (a) the rows are the DSMC *relaxation* axis (SPARTA
  step numbers 100..2200), NOT a flight-time axis - `Matched_Traj_Idx` is resolved ONCE
  before the step loop, so every row carries the same trajectory point and the same
  `time_s` (the shipped reference run has `time_s = 97.000` in all 22 rows), hence every
  `dt` is 0 and the integral evaluates to 0.0; and (b) even with a varying time axis the
  sum would integrate a relaxation transient rather than a flight heating history. The
  peak-flux form is well defined for every run and is a pure DSMC measurement. The state
  ratio `SG(snapshot)/SG(run)` is deliberately NOT folded in: the DSMC simulated at the run
  state, and the correction for the objective's snapshot state belongs to the calibrated
  model, not to the measurement.
- `geom_*` = the geometry actually flown (from the `Geometry_Parameters` handed to SPARTA).
- `ref_area_*` = the two reference areas used, so any downstream tool can reproduce the
  normalisation without guessing.

### 2.5 Calibration file (the Ada side cannot parse JSON comfortably — use KEY = VALUE)
`src/python/hiad_calibration.txt`:
```
# StellarOrion screening-model calibration
# Generated by scripts/calibrate_from_dsmc.py; consumed by the Ada screening model.
calibration_valid   = 1
cd_anchor_cd        = 1.6072782278060913
cd_exponent         = 0.15
cd_nose_slope       = 0.05
cd_blunt_coeff      = 0.0
sg_multiplier       = 1.0
reference_x1        = 1.5
reference_x2        = 0.135
reference_x3        = 60.0
```
The Ada loader lives in the optimisation package:
```ada
procedure Load_Calibration (Path : String);   -- SPARK_Mode (Off), Text_IO based
```
and it sets the package-level calibration constants used by `Estimate_Cd` and the SG call.
`calibration_valid = 0` (or a missing file) means "use the built-in literature constants".
The FFI gains `procedure Set_Calibration_C (Path : access Interfaces.C.char)` — hmm, Ada
string <-> C string is a nuisance. Simpler: the calibration file is loaded by the
**ga_runner** and by the **CLI driver** at start-up (they know the file path); the library
route reads it through `HIAD_Set_Refs_C`-style plumbing only if trivial. Decision:
**load it in the Ada programs (runner + CLI), not through the FFI.** The Python side calls
the runner with the calibration already applied.

### 2.6 The calibration mechanism: an ORTHOGONAL RESIDUAL CORRECTION
The correction is fitted as the **residual of the current analytic model** against the
DSMC response, over the orthogonal 2^3 factorial basis {1, x1, x2, x3, x1x2, x1x3, x2x3}.
Advantages: the fit is exact and closed-form (no matrix solve), it is orthogonal so the
coefficients are independent, it reduces to zero when the model is already right (the
anchor stays intact), and it cannot make the objective worse at the reference.

```
x_k(x) = clamp((X(k) - centre_k) / half_k, -1, +1)          -- the CODED coordinates
Cd_cal(x)  = Cd_current(x) + sum_k b_cd[k] * monomial_k(x)
Q_cal(x)   = Q_current(x)  + sum_k b_q[k]  * monomial_k(x)
monomials  = {1, x1, x2, x3, x1*x2, x1*x3, x2*x3}
```
`Cd_current` and `Q_current` are today's laws (the §2.2 heat fix included); the
correction is ADDITIVE and is zero when `calibration_valid = 0`.

### 2.6.1 The SPARK-provable fit primitives (L5 owns them, L1 calls them)
In `StellarOrion_Optimizer_Core` (SPARK_Mode => On, no new dependencies):

```ada
--  Residual-model coefficients over the orthogonal 2^3 factorial basis.
type Residual_Coefficient_Array is array (1 .. 7) of Float;

--  Fit the 7 orthogonal coefficients of a 2^3 factorial design.
--  Pre  : every coded coordinate is exactly +1.0 or -1.0
--          (the same precondition as Fit_Linear_Surrogate).
--  Post : Coefficients (1) = the grand mean of Values,
--          Coefficients (k) = the k-th orthogonal contrast.
procedure Fit_Orthogonal_Factorial
  (Coded        : Factorial_Point_Array;
   Values       : Factorial_Value_Array;
   Coefficients : out Residual_Coefficient_Array);

--  Evaluate the 7-term orthogonal model at a coded point.
function Evaluate_Residual_Model
  (Coefficients : Residual_Coefficient_Array;
   X            : Coded_Vector) return Float;
```
No divisor that can be zero (the 2^3 factorial is orthogonal with norm 8), so the fit
needs no division-overflow obligation and is provable at `--level=4`.

### 2.6.2 The calibration file format (KEY = VALUE — the Ada side reads it with Text_IO)
`src/python/hiad_calibration.txt`:
```
# StellarOrion screening-model calibration (orthogonal residual correction).
# Written by scripts/calibrate_from_dsmc.py; read by the Ada screening model.
calibration_valid = 1
centre_x1 = 1.03967
centre_x2 = 0.219741
centre_x3 = 53.7247
half_x1 = 0.25
half_x2 = 0.06
half_x3 = 8.0
cd_b0 = 0.0
cd_b1 = 0.0
cd_b2 = 0.0
cd_b3 = 0.0
cd_b12 = 0.0
cd_b13 = 0.0
cd_b23 = 0.0
q_b0 = 0.0
q_b1 = 0.0
q_b2 = 0.0
q_b3 = 0.0
q_b12 = 0.0
q_b13 = 0.0
q_b23 = 0.0
```
The Ada loader lives in the optimisation package:
```ada
procedure Load_Calibration (Path : String);   -- SPARK_Mode (Off), Text_IO based
```
It sets package-level calibration state used by `Estimate_Cd` and the heat term.
`calibration_valid = 0`, or a missing/unreadable file, means "use the built-in
literature constants" (the pre-calibration behaviour, recoverable). The file is loaded
by the Ada PROGRAMS (the runner and the CLI driver), which know its path — not through
the FFI (Ada/C string conversion).

### 2.7 The Stage-1 calibration DoE (physical points, DSMC-evaluated)
A local CCD **centred on the GA optimum** (the CCD must cover the region the GA actually
explored — the old CCD was centred on the reference, so its factorial corners never
reached the blunt region):

- centre: X* = (1.03967, 0.219741, 53.7247)
- half-widths: `dR_N = 0.25`, `dR_tor = 0.06`, `dCone = 8.0` (coded levels +/-1)
- 8 factorial points (2^3) + the centre = **9 DSMC runs**
- each run: the full 2200-step protocol (the CSV step axis is the FLIGHT-TRAJECTORY
  history, not a convergence series — truncating to 2000 saves only ~9 % and biases the
  endpoint)
- wall time ~2 h per run => ~18 h sequential. The 9th (centre) run replaces the
  mis-parameterised candidate run.
- the reference run already on disk (`results/00_reference/validation_timeseries.csv`,
  flown with D = 3.0 / nose 0.55 / torus 0.135 / cone 60) is the **anchor point** and is
  reused as-is (it is exactly the reference geometry under §2.1).

### 2.8 Refit method (Stage 2)
The responses to fit are the DSMC's own quantities: `cd_raw_presented_area` (drag) and
`dsmc_surface_heat_load_jcm2` (heat). The fit is a closed-form contrast fit over the
coded CCD layout — the same machinery as `Fit_Linear_Surrogate` in
`StellarOrion_Optimizer_Core` (mean + paired contrasts, no matrix solve) — extended to a
**non-linear** response surface for the drag law (the blunt-body term is quadratic in
(1 - X(1)/X_ref), so the drag model is fitted in the basis
{1, x1, x2, x3, x1^2, x1*x2, x1*x3} — an exact orthogonal-quadratic CCD fit is possible
because the 8-point factorial is a complete 2^3 design; the centre point fixes the
mean). The heat model is fitted as a single scale factor (SG is linear in its inputs).
All of it lands in the SPARK core as proven subprograms.

---

## 3. LANE SPLIT (strict file ownership — no two lanes touch the same file)

| lane | owns | delivers |
|---|---|---|
| L1 | `src/simulation_engine/stellarorion_optimization.ads`, `.adb` | the §2.1 mapping, the §2.2 heat-term fix, `Load_Calibration`, the calibrated `Estimate_Cd`, the physical-geometry reporting of the optimum, and the regression of the reference anchor |
| L2 | `src/simulation_engine/stellarorion_sparta.adb` | the §2.4 CSV columns (unclamped cd, both raw cd's, the DSMC surface heat load, the flown geometry, both reference areas) |
| L3 | `src/simulation_engine/stellarorion_ga_runner.adb`, `stellarorion_ffi.ads`, `stellarorion_ffi.adb` | the runner emits the FULL physical geometry (all four flags) and the calibration file path; the FFI reports the physical geometry; both load the calibration file |
| L4 | `src/python/ada_pinn_wrapper.py`, `src/python/hiad_optimizer.py`, `scripts/calibrate_from_dsmc.py` (NEW), `scripts/compare_dsmc_runs.py` | the calibration file writer, the new CSV columns in the comparison tool, the truthful model-space/physical-space labels, the GA's `--optimizer` path reporting the physical geometry |
| L5 | `src/simulation_engine/stellarorion_optimizer_core.ads`, `.adb` | the SPARK-provable calibration-fit primitives (orthogonal-quadratic contrast fit over the CCD layout + the drag-law evaluation) and `gnatprove` clean |
| L6 | `proofs/lean/**`, `proofs/coq/**`, `scripts/run_calibration_dsmc.sh` (NEW) | the new Lean/Coq lemmas for the calibration fit and the Stage-1 runner script |

Every lane ends with the file's own verification: Ada lanes build with
`MACOSX_DEPLOYMENT_TARGET=26.0 gprbuild -f -P <project> -j0` (zero warnings);
L5 additionally runs `gnatprove --mode=all --level=4 -j0 --report=all`;
Python lanes run `ruff check`; L6 runs `lake build` and `coqc`.

---

## 4. STAGES

- **Stage 0** (no DSMC): L1+L2+L3+L4 implement §2.1-§2.5. Verify: builds clean, gnatprove
  clean, the reference mapping reproduces the flown reference geometry exactly, the
  analytic heat term for the reference now matches the DSMC's SG nose radius.
- **Stage 1** (≈18 h): L6's script flies the 9 local-CCD points with the §2.1 mapping,
  collecting the new CSV columns; the reference run is reused as the anchor.
- **Stage 2** (≈1 h): L5 + L6 fit the drag law and the heat scale factor against the
  9 DSMC responses (+ the anchor), write `src/python/hiad_calibration.txt`, and prove the
  fit properties (mean reproduction, contrast reproduction, positivity of the fitted
  coefficient) in SPARK + Lean + Coq.
- **Stage 3** (≈3 h): re-run the W_Cd sweep with the calibrated model, re-run the GA,
  fly the new optimum through DSMC (1 run, ~2 h), regenerate the figures with truthful
  labels (model-space DoE vs physical-space validation), and update the comparison docs.

## 5. LABELLING RULES (carry the DSMC+PINN_AUX convention)

- The DoE figures are **"model-space design"** (CCD sensitivity of the SCREENING MODEL).
- The validation runs are **"physical-space DSMC+PINN_AUX validation"**.
- Never write "DSMC/PINN" (the PINN is auxiliary): use **DSMC+PINN_AUX**.
- Never claim a quantity is "measured by DSMC" when it is a Sutton-Graves correlation.

## 6. CITATIONS

- Sutton & Graves (1972), NASA TR R-376 — stagnation-point heating correlation.
- Anderson (2006), *Hypersonic Gas Dynamics*, Sec. 5.4 — blunt-body drag.
- NASA/TP-2013-4012 — IRVE-3 reference geometry (R_N 1.5 m, torus 0.135 m, cone 60 deg).
- McKay et al. (1979), *Technometrics* 21(2) — LHS; Montgomery (2017) 9th ed. — CCD.
- Kennedy & O'Hagan (2000), *Biometrika* 87(1) — model-fidelity discrepancy terms.
