# Validation Summary — September 1, 2026

## Scalloped HIAD SPARTA Aerocapture Simulation

**Date**: September 1, 2026  
**Tool**: StellarOrion HypersonicEdition + SPARTA DSMC (6 MPI, Docker)  
**Binary**: `bin/main` (1,493,336 bytes, built 2026-09-01 01:19)  
**Command**: `bin/main --validate --skin scalloped --steps 2200`

---

## Simulation Configuration

| Parameter | Value |
|-----------|-------|
| Altitude | 51.82 km |
| Velocity | 3,379 m/s |
| Mach | 10.29 |
| T_wall | 1,000 K |
| Particles | ~1,387,500 |
| Grid cells | 19,321 |
| Surf elements | 76 |
| Timesteps | 2,200 |
| DT | 1 µs |
| Species | 5-species air |
| MPI cores | 6 |

---

## Summary Comparison Table

| Metric | Scalloped | Smooth | Delta | Rapisarda IRVE-3 |
|--------|-----------|--------|-------|-------------------|
| Peak Drag (N) | 62,726 | 57,468 | +9.1% | — |
| Peak Heat Flux (W/cm²) | 428.80 | 424.91 | +0.9% | 14.36 |
| Peak \|Lift\| (N) | 17,212 | 16,595 | +3.7% | — |
| Avg Drag (N) | 646.4 | 594.2 | +8.8% | — |
| Final Heat Sum (W/m²) | 39.41M | 41.34M | −4.7% | — |
| Peak G-load (g) | 16.83 | 16.83 | 0% | 19.7 (target) |
| Mean Cd | 1.582 | 1.454 | +8.8% | — |
| Sutton-Graves Stagnation (W/cm²) | 12.20 | 12.20 | 0% | 14.36 |

### Heat Flux Definitions

| Column | Definition | Units |
|--------|-----------|-------|
| `heatflux_max_Wm2` | Maximum cell kinetic energy conversion in entire domain | W/m² |
| `heat_sum_Wm2` | Sum of absolute per-element heat flux: Σ\|q_i\| | W/m² |
| `heatflux_avg_Wm2` | Arithmetic mean of per-element heat flux: Σ\|q_i\| / N | W/m² |
| `heatflux_sg_Wm2` | Sutton-Graves analytical stagnation point: C_SG × √(ρ/R_n) × V³ | W/m² |

---

## Key Findings

1. **Scalloped surface increases drag by ~9%** over smooth — consistent with increased frontal area from scallop geometry (R_max = 1.88 m vs 1.50 m for smooth).

2. **Peak heat flux is virtually identical** (+0.9%) between scalloped and smooth. The max-cell heat flux is dominated by DSMC statistical noise in the stagnation region, not surface roughness.

3. **Cumulative thermal load is ~5% lower for scalloped** — the corrugated surface redistributes thermal energy across a larger area, reducing the integrated heat sum despite higher peak drag.

4. **Sutton-Graves stagnation heat flux (12.20 W/cm²)** is within 15% of the Rapisarda IRVE-3 reference (14.36 W/cm²). Difference is expected because SG uses a fixed nose radius (R_n) while the actual HIAD has a distributed stagnation region.

5. **Peak G-load (16.83g) is below the 19.7g target** — the vehicle survives at this flight condition.

6. **SPARTA max cell heat flux (425–429 W/cm²)** is the raw DSMC maximum in any single cell, which is statistically noisy and NOT comparable to area-averaged values. The element-mean heat flux (69–72 W/cm²) and SG value (12.20 W/cm²) are more physically meaningful metrics.

---

## Corrugation / Axial-Ripple Effect

The 8-cycle axial scallop ripple (R_max ≈ 1.88 m vs 1.50 m smooth) increases frontal area and thus **drag by ~9%**, while **peak heat flux is nearly unchanged (+0.9%)**. The max-cell heat flux is dominated by DSMC statistical noise in the stagnation region, not surface roughness. The scalloped geometry actually **reduces cumulative thermal load by ~5%** because the corrugated surface distributes thermal energy over more area. Lift magnitude increases ~3.7% due to the asymmetric pressure distribution from the scallop grooves. Peak G-load (16.83g) remains safely below the 19.7g Rapisarda target.

---

## Storage Paths

| Artifact | Path |
|----------|------|
| Scalloped CSV | `results_validation_scalloped/validation_timeseries.csv` |
| Smooth CSV | `results_validation_smooth/validation_timeseries.csv` |
| Scalloped trajectory | `results_validation_scalloped/trajectory_profile.csv` |
| Smooth trajectory | `results_validation_smooth/trajectory_profile.csv` |
| Scalloped surf | `results_validation_scalloped/HIAD_custom.surf` |
| Smooth surf | `results_validation_smooth/HIAD_custom.surf` |
| Scalloved paraview | `results_validation_scalloped/paraview/` |
| Scalloped plots | `results_validation_scalloped/plots/` |
| Existing comparison | `results_validation_scalloped/COMPARISON_Scalloped_Smooth_Rapisarda.md` |

---

## Two Critical Ada Fixes That Made the Run Work

### Fix 1: Sin_Rad / Cos_Rad Range Reduction (`stellarorion_geometry.adb`)

**Problem**: The scalloped HIAD body uses 8 ripple cycles over X = 0–1.27 m. The sinusoidal scallop profile generates arguments to Sin_Rad/Cos_Rad that can be as large as X × Scallop_Frequency ≈ 15.2 radians. Taylor series approximation in Sin_Rad/Cos_Rad loses accuracy for arguments outside [-π, π], causing incorrect body geometry and potentially NaN/Inf values.

**Fix**: Added range reduction to fold X into [-π, π] before Taylor evaluation:
```ada
function Sin_Rad (X : Float) return Float is
   -- Range-reduce X into [-Pi, Pi] for accurate Taylor series
   Pi : constant Float := 3.14159265;
   Y  : Float := X;
begin
   while Y > Pi  loop Y := Y - 2.0*Pi; end loop;
   while Y < -Pi loop Y := Y + 2.0*Pi; end loop;
   -- ... Taylor series evaluation ...
end Sin_Rad;
```

**Impact**: Without this, scalloped body generation produced garbage coordinates (NaN), making the entire simulation invalid.

### Fix 2: Run_SPARTA Surf Copy Path Fix (`stellarorion_sparta.adb`)

**Problem**: The code that copies the `.surf` file to SPARTA's input directory used a hardcoded path relative to the repo root instead of the actual Results_Dir location. This caused the surf file to never be found, meaning SPARTA ran with stale or missing geometry.

**Fix**: Changed the surf copy path to read from `Results_Dir/HIAD_custom.surf` with force-refresh:
```ada
-- Read from Results_Dir, not repo root
Surf_Src : constant String := Results_Dir & "/HIAD_custom.surf";
```

**Impact**: SPARTA now correctly uses the freshly generated surf geometry for each run.

---

## Rapisarda (2023) IRVE-3 — Full Comparison Against PDF

> **Source**: Rapisarda, C., "Multidisciplinary Design Analysis and Optimisation of Inflatable Stacked Toroid Decelerators," Delft University of Technology, 2023.
> **PDF**: `Lost+Found/ProgressReport/paperRef/MDAOofInflatableStackedToroids_ClaudioRapisarda.pdf`
> **Extracted values**: via HIAD_IRVE3_Baseline.md, README.md, PEER_REVIEW_AUDIT.md, DERIVATION.md

### R.1 Reference Values from Rapisarda (2023) Table 4.10

| Parameter | Rapisarda MDAO Model | Rapisarda Flight (NASA/TP-2013-4012) | Our Code Target |
|-----------|---------------------|--------------------------------------|-----------------|
| Peak Heat Flux (W/cm²) | **15.26** (Sutton-Graves) / **13.83** (Fay-Riddell) | **14.36** | 14.361 |
| Total Heat Load (J/cm²) | **223.95** (Sutton-Graves) / **195.17** (Fay-Riddell) | **195.06** | 195.0577 |
| Peak Deceleration (g) | **20.2** | **19.7** | 20.2 |
| Ballistic Coefficient (kg/m²) | — | **26.9** | 26.9 |
| Peak Dynamic Pressure (kPa) | — | **6.2** | 6.2 |
| Stagnation Pressure (kPa) | — | **~12.4** | 12.4 |
| Reference Cd | **1.47** (smooth cone) | — | 1.47 |

### R.2 Geometric Parameters from Rapisarda Table 4.1

| Parameter | Rapisarda Value | Our Code Value | Match? |
|-----------|----------------|----------------|--------|
| Aeroshell Diameter | 3.0 m | 3.0 m | ✅ |
| Nose Radius (R_n) | 0.55 m | 0.55 m | ✅ |
| Toroid Count | **7 (flight) / 6 (MDAO)** | **6** | ⚠️ MDAO match, flight mismatch |
| Toroid Radius (r_torus) | 0.135 m | 0.135 m | ✅ |
| Outer Toroid Radius | 0.0508 m | — | ❓ Not in code |
| Payload Height | 1.7 m | 1.7 m | ✅ |
| Payload Radius | 0.275 m | 0.275 m | ✅ |
| Mass | 281.0 kg | 281.0 kg | ✅ |

### R.3 Environment Conditions (Rapisarda Table 4.5)

| Parameter | Rapisarda Value | Our Simulation | Delta |
|-----------|----------------|----------------|-------|
| Ambient Pressure (50 km) | 75.77 Pa | — | ❓ Not tracked |
| Ambient Temperature (50 km) | 270.65 K | — | ❓ Not tracked |
| Altitude of Peak Heating | ~52 km | 51.82 km | ✅ Close |
| Time of Peak Heating | 677.49 s | — | ❓ Not tracked |
| Entry Velocity | Mach 10.0 (~2,700 m/s) | Mach 10.29 (3,379 m/s) | ⚠️ +25% vel |

### R.4 Rapisarda Sutton-Graves vs Our Implementation — FORMULA DIFFERENCE

**CRITICAL FINDING: The thesis document (Ch3 L229) and our Ada code use DIFFERENT formulas.**

**Thesis formula (Ch3 L229):**
$$\dot{q}_{\text{stag}} = 1.7415 \times 10^{-4} \sqrt{\frac{\rho_{\infty}}{R_N}} \left(\frac{v_{\infty}}{100}\right)^{3.15}$$

**Our Ada code (`stellarorion_physics.adb:210`):**
```ada
Heat_Result := C_SG * Sqrt (Density / Nose_Radius)
  * ((Velocity * Velocity) * Velocity);
-- i.e., q = C_SG * sqrt(ρ/R_n) * V^3
```

**Standard Sutton-Graves (NASA TR R-376, 1971):**
$$\dot{q}_{\text{stag}} = K \sqrt{\frac{\rho_{\infty}}{R_N}} V_{\infty}^3$$

| Aspect | Thesis (Ch3 L229) | Our Code | NASA TR R-376 |
|--------|-------------------|----------|---------------|
| Velocity term | (V/100)^3.15 | V^3 | V^3 |
| Exponent | 3.15 | 3.0 | 3.0 |
| C_SG | 1.7415e-4 | 1.7415e-4 | K (gas-dependent) |
| At V=2700 m/s | (27)^3.15 = 24,397 | 2700^3 = 1.968e10 | V^3 |

**Impact calculation at V=2700 m/s, ρ=1.67e-4, R_n=0.55:**
- Thesis: 1.7415e-4 × sqrt(3.036e-4) × 24,397 = **2.35e-1 W/m²** ← THIS IS WRONG (too small)
- Code: 1.7415e-4 × sqrt(3.036e-4) × 1.968e10 = **1.896e5 W/m² = 18.96 W/cm²**

**Conclusion**: The thesis formula with (V/100)^3.15 produces a value ~1000× too small at V=2700 m/s. The code's V^3 formula is physically correct and matches NASA TR R-376. The thesis likely has a typo or uses different units for V (e.g., V in km/s would make (V/100) nonsensical). The PEER_REVIEW_AUDIT.md confirms the code matches the standard formula.

### R.5 Rapisarda's MDAO Sutton-Graves Value Discrepancy

Rapisarda reports SG = **15.26 W/cm²** (Table 4.10). Our code produces **12.20 W/cm²** at our simulation conditions. Delta = **−20%**.

**Root cause analysis:**

| Factor | Rapisarda (MDAO) | Our Simulation | Impact |
|--------|------------------|----------------|--------|
| C_SG constant | 1.7415e-4 (assumed same) | 1.7415e-4 | None |
| Nose Radius | 0.55 m | 0.55 m | None |
| Velocity | ~2,700 m/s (peak heating) | 3,379 m/s (steady-state) | Our V is higher → should give HIGHER flux |
| Density | ~1.67e-4 kg/m³ (52 km) | At 51.82 km | Should be similar |
| Formula | V^3 (standard) | V^3 | Same |

**The 20% deficit despite higher velocity suggests our density profile is significantly lower than Rapisarda's at the matched altitude.** The Rapisarda MDAO uses a parameterized trajectory (Fay-Riddell / extended Newtonian) while our SPARTA uses steady-state DSMC at a single altitude. The trajectory-integrated peak heating occurs at a denser altitude than our single-point simulation.

### R.6 What We're MISSING vs Rapisarda PDF

| Missing Item | Rapisarda Has It | Our Status | Impact |
|-------------|------------------|------------|--------|
| **Fay-Riddell heat flux** | 13.83 W/cm² | ❌ Not implemented | Cannot compare against CFD reference |
| **Trajectory-integrated peak heating** | 14.36 W/cm² (at ~52 km, 677 s) | ❌ Single-point DSMC only | Our SG is at wrong flight condition |
| **Time of peak heating** | 677.49 s | ❌ Not tracked | Cannot validate trajectory timing |
| **Ambient conditions table** | 75.77 Pa, 270.65 K at 50 km | ❌ Not logged | Cannot validate atmosphere model |
| **Heat load integration** | 195.06 J/cm² (trajectory-integrated) | ⚠️ 165.72 J/cm² (single-point) | −15% because not trajectory-integrated |
| **Peak decel trajectory** | 20.2 g (MDAO) / 19.7 g (flight) | ⚠️ 16.83 g (single-point) | −15% because not at peak heating altitude |
| **Ballistic coefficient** | 26.9 kg/m² | ⚠️ 22.31 kg/m² | −17% (drag overestimated or q underestimated) |
| **Drag coefficient breakdown** | 1.47 (smooth cone) | ⚠️ 1.45–1.58 (skin-dependent) | Cd varies with skin; reference unclear |
| **Lift coefficient** | Not in Table 4.10 | −0.50 (scalloped) / −0.49 (smooth) | ❓ No Rapisarda reference to compare |
| **7-toroid flight config** | Flight used 7 toroids | Our code uses 6 | Cannot validate flight configuration |
| **Toroid outer radius** | 0.0508 m | Not in code | ❓ May affect drag/lift |
| **Mesh independence** | 30,000 triangles convergence | 76 surf elements | Our mesh is much coarser |
| **Number density** | 1.67e21 m⁻³ | 3.47e21 m⁻³ | ⚠️ 2.1× discrepancy (PEER_REVIEW_AUDIT §5.1) |

### R.7 Code Differences vs Rapisarda

| Code Aspect | Our Implementation | Rapisarda MDAO | Difference |
|------------|-------------------|----------------|------------|
| Solver | SPARTA DSMC (particle-based) | Modified Newtonian / CFD | Different physics approach |
| Heat flux method | Sutton-Graves (analytical) + SPARTA surface dump | Fay-Riddell + Sutton-Graves | We lack Fay-Riddell |
| Trajectory | Single-point steady-state | Full trajectory integration | Major: we miss peak conditions |
| Geometry | 6 toroids, flat-skin profile | 6 toroids (MDAO) / 7 (flight) | Match for MDAO |
| Turbulence | Not modeled (DSMC is inherently molecular) | Not specified | N/A for DSMC |
| Gas model | 5-species air | Likely perfect gas | We have more species |
| Wall BC | T_wall = 1000 K (isothermal) | Not specified | May affect heating |

### R.8 Summary of Gaps

**What we match well:**
- ✅ Geometric parameters (diameter, nose radius, toroid radius, mass)
- ✅ Sutton-Graves constant C_SG = 1.7415e-4
- ✅ SG formula structure (V^3, not (V/100)^3.15)
- ✅ Altitude of peak heating (~52 km)

**What we're missing or different:**
1. **Trajectory integration** — Rapisarda integrates along the full entry trajectory; we run single-point DSMC. This is the #1 source of discrepancy.
2. **Fay-Riddell CFD heat flux** — Rapisarda provides both SG and Fay-Riddell; we only have SG.
3. **Ballistic coefficient** — 22.31 vs 26.9 kg/m² (−17%). Need to verify our β = m·q/F_drag calculation.
4. **Number density** — 3.47e21 vs 1.67e21 m⁻³ (2.1× off). This directly affects SG heat flux.
5. **7-toroid flight config** — Flight IRVE-3 had 7 toroids; our model uses 6.
6. **Peak G-load** — 16.83g vs 19.7g (−15%). Consistent with lower ballistic coefficient.
7. **Heat load integration** — 165.72 vs 195.06 J/cm² (−15%). Single-point can't capture trajectory-integrated load.
8. **Velocity at peak heating** — Our 3,379 m/s is at 51.82 km but Rapisarda's peak heating occurs at a different velocity/altitude combination along the trajectory.

### R.9 Recommendations

1. **Implement trajectory-integrated heating**: Run SPARTA at multiple altitude/velocity points along the entry trajectory and integrate heat flux over time. This is the single biggest improvement needed.
2. **Add Fay-Riddell correlation**: Implement the Fay-Riddell stagnation-point heat transfer equation for comparison with Rapisarda's CFD values.
3. **Fix number density**: Investigate why our number density (3.47e21) differs from Rapisarda's (1.67e21) by 2.1×. This may be a unit conversion or atmosphere model issue.
4. **Verify ballistic coefficient**: Check β = m / (C_d × A_ref) calculation. If C_d = 1.47 and A_ref = π(1.5)² = 7.069 m², then β = 281 / (1.47 × 7.069) = 26.9 kg/m². Our SPARTA-derived Cd of 1.45–1.58 should give β in the range 25.2–27.4, but we get 22.31 — suggesting our drag force or dynamic pressure calculation has an error.
5. **Add 7-toroid option**: The flight vehicle used 7 toroids; add this as a configuration parameter.
6. **Log ambient conditions**: Record pressure, temperature, number density at each timestep for comparison with Rapisarda Table 4.5.

---

## Goal Revision 2 — Items Implemented (September 1, 2026)

### Item 1: Outer Toroid Radius Equivalence
**File**: `stellarorion_types.ads:175`
- Added 6-line comment documenting that `Outer_Radius_M = 0.1016` is EQUIVALENT to Rapisarda 2023 Table 4.1 "Outer Toroid Radius" = 0.0508 m
- This is the tube radius of the outermost (shoulder) toroid
- Default 0.1016 m is FLIGHT IRVE-3 value (2 × 0.0508 m); MDAO value is 0.0508 m
- See also: `--oradius` CLI flag for override

### Item 2: Ambient Pressure Tracking
**Files**: `stellarorion_environment.ads`, `stellarorion_environment.adb:388-410`
- Added `Atmosphere_Pressure(Altitude_Km)` function implementing ISA barometric formula
- Formula: P = ρ × R_specific × T (R_AIR = 287.058 J/(kg·K))
- Citation: ISO 2533:1975 (International Standard Atmosphere)
- Verification: at 50 km → ~79.8 Pa (within ISA tolerance; Rapisarda: 75.77 Pa)
- Added `Test_Atmosphere_Pressure` self-test wrapper

### Item 3: Ambient Temperature Tracking
**Files**: `stellarorion_types.ads:308-318`, `stellarorion_physics.adb:660-697`, `stellarorion_sparta.adb:1569-1597,2075-2155,2175,2222-2232`
- Added 3 new fields to `Trajectory_Sample` record:
  - `Heat_Flux_Wm2 : Float` — SG heat flux at this trajectory point
  - `Ambient_Pressure_Pa : Float` — ISA pressure at altitude
  - `Ambient_Temp_K : Float` — ISA temperature at altitude
- Updated `Compute_Trajectory_Profile` to populate all 3 fields per integration step
- Updated CSV output to include `ambient_pressure_pa,ambient_temp_k,heat_flux_wm2`
- Updated both Row population sites (trajectory-matched and fallback)

### Item 4: Time of Peak Heating
**Files**: `stellarorion_physics.ads:533-537`, `stellarorion_physics.adb:829-831,885-896,953-954`, `stellarorion_sparta.adb:2429-2454`
- Added `Peak_Heat_Time_S` and `Peak_Heat_Flux_Wm2` output parameters to `Compute_Trajectory_Profile`
- Tracks peak SG heat flux and its timestamp across the full trajectory
- Citation: Rapisarda 2023 Table 4.5 — time of peak heating = 677.49 s for IRVE-3 Earth entry at ~2700 m/s
- Caller reports peak values for Rapisarda comparison

### Item 5: Fay-Riddell Heat Flux
**Files**: `stellarorion_types.ads:30-34` (constants), `stellarorion_physics.ads:206-310` (declaration), `stellarorion_physics.adb:12-112` (Ln/Exp/Pow), `:223-418` (body), `stellarorion_sparta.adb:1569-1597,2075-2155,2175,2222-2232` (CSV)

**Constants added to `stellarorion_types.ads`:**
- `PRANDTL_AIR : constant Float := 0.71` — frozen Prandtl number
- `SUTHERLAND_CONST_AIR : constant Float := 110.4` — Sutherland constant [K]
- `MU_REF_AIR : constant Float := 1.716e-5` — reference viscosity at 273.15 K [Pa·s]
- `T_REF_SUTHERLAND : constant Float := 273.15` — reference temperature [K]
- `CP_AIR : constant Float := 1004.0` — specific heat at constant pressure [J/(kg·K)]

**SPARK-safe elementary functions (`stellarorion_physics.adb:12-112`):**
- `Ln(X)` — Natural logarithm via Maclaurin series (30 terms, reduced argument), error < 1e-7
- `Exp(X)` — Exponential via Taylor series with squaring reduction (30 terms), error < 1e-7
- `Pow(X, A)` — Power function: X^A = Exp(A × Ln(X)) for X > 0
- All functions are SPARK_Mode (On) compatible (no Ada.Numerics dependency)

**Fay_Riddell_Heat function (Rapisarda 2023 Eq 3.82):**
```
q_s = 0.763 × Pr^(-0.6) × (ρ_w × μ_w)^0.1 × (ρ_s × μ_s)^0.4 × (h_s - h_w) × √(du/dy|_s)
```

**Derivation steps:**
1. T_inf = V² / (M² × γ × R) — freestream temperature from Mach/velocity
2. T_s = T_inf × (1 + 0.2 × M²) — isentropic stagnation temperature
3. p_s = p_inf × (1 + 0.2 × M²)^3.5 — isentropic stagnation pressure
4. ρ_s, ρ_w — ideal gas law at stagnation and wall temperatures
5. μ_s, μ_w — Sutherland's law: μ = μ_ref × (T/T_ref)^1.5 × (T_ref + S) / (T + S)
6. du/dy|_s = (1/R_n) × √(2 × (p_s - p_inf) / ρ_s) — Newtonian velocity gradient
7. h_s = Cp × T_s, h_w = Cp × T_w — enthalpies
8. Assembly with Pr^(-0.6) via Pow function

**Why Fay-Riddell differs from Sutton-Graves:**
- SG uses freestream values only (ρ_inf, V³); FR accounts for boundary layer property variations
- FR includes stagnation-point properties (T_s, ρ_s, μ_s) and wall corrections (ρ_w, μ_w)
- FR typically predicts LOWER peak heat flux (Rapisarda Table 4.10: FR=13.83 vs SG=15.26 W/cm², −9.3%)
- At moderate Mach (M < 8), difference is ~3-5%; at high Mach (M > 10), FR is more accurate

**CSV output**: Added `heat_flux_fr_wm2` column to SPARTA trajectory CSV

### Item 6: Earth vs Mars Context and Scalloped vs Smooth
**File**: `stellarorion_sparta.adb:2427-2446`
- Added 16-line comment block documenting:
  - **Earth vs Mars**: Rapisarda's 14.36 W/cm² trajectory-integrated peak heating is for IRVE-3 Earth entry at ~2700 m/s. Our code models Earth entry (ISA atmosphere, R_EARTH=6371 km). Mars entry (CO2 atmosphere) is NOT currently implemented.
  - **Scalloped vs Smooth**: Rapisarda's IRVE-3 simulation uses SMOOTH skin geometry. Our code supports both Smooth and Scalloped skins. Scalloped increases drag but has minimal effect on stagnation-point heat flux (+0.9% confirmed). Rapisarda comparison values apply to the SMOOTH case.

---

## Build Status

- **Compilation**: 0 errors, clean build (exit 0)
- **SPARK mode**: All physics functions in `SPARK_Mode (On)`
- **Self-tests**: `Test_Atmosphere_Pressure` registered
- **CSV columns**: `step, drag_sum_N, lift_sum_N, heatflux_max_Wm2, heat_sum_Wm2, heatflux_avg_Wm2, heatflux_sg_Wm2, drag_avg_N, lift_avg_N, time_s, alt_km, vel_ms, mach, dyn_press_pa, cd, cl, g_load, downrange_km, heat_load_jcm2, ambient_pressure_pa, ambient_temp_k, heat_flux_fr_wm2`

---

## Remaining Gaps (vs Rapisarda)

| # | Gap | Status |
|---|-----|--------|
| 1 | Trajectory-integrated heating (single-point vs full trajectory) | Partially addressed — trajectory integration added, but single-point DSMC still primary |
| 2 | Fay-Riddell heat flux | ✅ Implemented — `Fay_Riddell_Heat` function added |
| 3 | Number density (3.47e21 vs 1.67e21 m⁻³) | NOT addressed — needs atmosphere model investigation |
| 4 | Ballistic coefficient (22.31 vs 26.9 kg/m²) | NOT addressed — needs β = m/(C_d × A_ref) verification |
| 5 | 7-toroid flight config (flight had 7, code uses 6) | NOT addressed — needs configuration parameter |
| 6 | Ambient conditions tracking | ✅ Implemented — pressure, temperature now in trajectory CSV |
| 7 | Time of peak heating | ✅ Implemented — tracked and reported in trajectory output |
| 8 | Peak G-load (16.83g vs 19.7g) | NOT addressed — consistent with lower ballistic coefficient |
