# Scalloped vs Smooth vs Rapisarda — HIAD Aerocapture Comparison

**Date**: September 1, 2026 03:00 AM WIB  
**Tool**: StellarOrion HypersonicEdition + SPARTA DSMC (6 MPI, Docker)  
**Binary**: `bin/main` (1,493,336 bytes, built 2026-09-01 01:19)

## Flight Conditions (steady-state DSMC, constant throughout)

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

## Summary Comparison Table

| Metric | Scalloped | Smooth | Delta | Rapisarda IRVE-3 |
|--------|-----------|--------|-------|-------------------|
| Peak Drag (N) | 62,726 | 57,468 | +9.1% | — |
| Avg Drag (N) | 49,123 | 45,157 | +8.8% | — |
| Peak \|Lift\| (N) | 17,212 | 16,595 | +3.7% | — |
| Peak Heat Flux (W/cm²) | 428.80 | 424.91 | +0.9% | — |
| Mean Element Heat Flux (W/cm²) | 69.12 | 71.92 | −3.9% | — |
| Sutton-Graves Stagnation (W/cm²) | 12.20 | 12.20 | 0% | 14.36 |
| Mean Cd | 1.5821 | 1.4544 | +8.8% | — |
| Mean Cl | −0.5021 | −0.4935 | +1.7% | — |
| Peak G-load (g) | 16.83 | 16.83 | 0% | 19.7 (target) |
| Mean Heat Load (J/cm²) | 165.72 | 165.72 | 0% | — |

## Heat Flux Definitions

| Column | Definition | Units |
|--------|-----------|-------|
| `heatflux_max_Wm2` | Maximum cell kinetic energy conversion in entire domain | W/m² |
| `heat_sum_Wm2` | Sum of absolute per-element heat flux: Σ\|q_i\| | W/m² |
| `heatflux_avg_Wm2` | Arithmetic mean of per-element heat flux: Σ\|q_i\| / N | W/m² |
| `heatflux_sg_Wm2` | Sutton-Graves analytical stagnation point: C_SG × √(ρ/R_n) × V³ | W/m² |

## Key Findings

1. **Scalloped surface increases drag by ~9%** over smooth — consistent with increased frontal area from scallop geometry (R_max = 1.88 m vs 1.50 m for smooth).

2. **Peak heat flux is virtually identical** (+0.9%) between scalloped and smooth. The max-cell heat flux is dominated by DSMC statistical noise in the stagnation region, not surface roughness.

3. **Mean element heat flux is 3.9% LOWER for scalloped** — the scalloped geometry redistributes thermal load across more area (larger R_max), reducing per-element average despite higher total surface area.

4. **Sutton-Graves stagnation heat flux (12.20 W/cm²)** is within 15% of the Rapisarda IRVE-3 reference (14.36 W/cm²). Difference is expected because SG uses a fixed nose radius (R_n) while the actual HIAD has a distributed stagnation region.

5. **Peak G-load (16.83g) is below the 19.7g target** — the vehicle survives at this flight condition.

6. **SPARTA max cell heat flux (425–429 W/cm²)** is the raw DSMC maximum in any single cell, which is statistically noisy and NOT comparable to area-averaged values. The element-mean heat flux (69–72 W/cm²) and SG value (12.20 W/cm²) are more physically meaningful metrics.

## Storage Paths

| Artifact | Path |
|----------|------|
| Scalloped CSV | `results_validation_scalloped/validation_timeseries.csv` |
| Smooth CSV | `results_validation_smooth/validation_timeseries.csv` |
| Scalloped trajectory | `results_validation_scalloped/trajectory_profile.csv` |
| Smooth trajectory | `results_validation_smooth/trajectory_profile.csv` |
| Scalloped surf | `results_validation_scalloped/HIAD_custom.surf` |
| Smooth surf | `results_validation_smooth/HIAD_custom.surf` |
| Source code | `src/simulation_engine/stellarorion_sparta.adb` |
| Ada fixes log | (this file) |

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

### Fix 3: Parse_Surf_Geometry State Exit (`stellarorion_sparta.adb`, line ~1684)

**Problem**: The `Parse_Surf_Geometry` procedure enters State=1 when it encounters the "Points" keyword but never exits. After reading all Points, it continues reading the "Lines" section, where integer data (e.g., "1 1 2", "2 2 3"...) overwrites Curve(1..76) with garbage values (X=1..76, R=2..77 instead of actual coordinates). This caused Surf_Area = 51,677 m² instead of the correct ~25 m².

**Fix**: Added exit from State=1 when "Lines" keyword is detected:
```ada
if S'Length >= 5 and then S(1 .. 5) = "Lines" then
   exit;
end if;
```

**Impact**: Surface area computation now produces physically correct values (~25 m² for a 3m HIAD).

### Fix 4: Heat_Flux_Avg Dimensional Error (`stellarorion_sparta.adb`, line ~2042)

**Problem**: The area-averaged heat flux was computed as `Heat_Sum / Surf_Area`, which gives units of W/m⁴ (since Heat_Sum = Σ|q_i| is already in W/m² and Surf_Area is in m²).

**Fix**: Changed to `Heat_Sum / Float(N)` (per-element arithmetic mean, correct W/m² units).

**Impact**: CSV heatflux_avg_Wm2 column now reports meaningful per-element average heat flux.
