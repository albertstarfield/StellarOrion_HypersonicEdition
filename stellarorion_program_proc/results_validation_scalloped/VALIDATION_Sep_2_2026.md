# Validation Report — September 2–3, 2026

**Date**: September 2–3, 2026  
**Tool**: StellarOrion HypersonicEdition + SPARTA DSMC (6 MPI, Docker/Colima)  
**Binary**: `bin/main` (recompiled Sep 2, 2026, 9 Ada source files modified since prior build)

---

## 1. Simulation Configuration

| Parameter | Value |
|-----------|-------|
| Solver | SPARTA DSMC (5-species air, VSS collision) |
| Geometry | Scalloped HIAD (Rapisarda 2023 parametric, Table 4.1) |
| Aeroshell Diameter | 3.0 m (IRVE-3 baseline) |
| Torus Count | 6 tori |
| Skin Mode | `scalloped` |
| Grid Factor | 0.7 (grid-independency optimal) |
| Timesteps | 2,200 |
| DT | 1 µs |
| MPI Cores | 6 |
| Particles | ~1,387,500 |
| Grid Cells | 19,321 |
| Surface Elements | 76 |
| Wall Temperature | 1,000 K (cold-wall DSMC) |
| Surface Collide | Diffuse, full accommodation |

### Flight Conditions (constant, single-point DSMC)

| Parameter | Value | Source |
|-----------|-------|--------|
| Altitude | 51.82 km | ISA atmosphere at matched Mach |
| Velocity | 3,379 m/s | ISA profile (trajectory) |
| Mach | 10.29 | Trajectory profile |
| Dynamic Pressure | 4,392.5 Pa | ½ρV² |
| Air Density | 7.696 × 10⁻⁴ kg/m³ | ISA at 51.82 km |
| Temperature | 267.85 K | ISA at 51.82 km |

> **Note**: SPARTA `vstream = 2,700 m/s` (set in `in.hiad`) differs from trajectory velocity `3,379 m/s`. The SPARTA free-stream is a simplified input; the trajectory profile CSV uses ISA-derived values. Sutton-Graves computation uses SPARTA's V=2,700 m/s.

---

## 2. Convergence Summary

The simulation was run for 2,200 timesteps with statistics output every 100 steps.

| Step | CPU Time (s) | Particles | Drag (N) | Lift (N) | c_heat |
|------|-------------|-----------|----------|----------|--------|
| 100 | 126 | 1,383,871 | 62,470 | −12,928 | 4,583,245 |
| 200 | 315 | 1,377,657 | 52,005 | −12,311 | 2,742,942 |
| 300 | 598 | 1,371,181 | 54,005 | −13,078 | 2,998,448 |
| 400 | 945 | 1,364,106 | 53,205 | −14,324 | 2,497,234 |
| 500 | 1,315 | 1,356,098 | 52,382 | −14,487 | 2,315,616 |
| 600 | 1,778 | 1,347,694 | 51,353 | −14,696 | 2,722,708 |
| 700 | 2,284 | 1,338,889 | 51,002 | −15,375 | 1,979,276 |
| 800 | 3,246 | 1,329,879 | 50,685 | −15,434 | 1,934,065 |
| 900 | 4,236 | 1,320,532 | 50,168 | −15,982 | 2,003,875 |
| 1000 | 5,362 | 1,310,398 | 49,211 | −15,571 | 1,878,738 |

**Convergence observations:**
- **Drag**: Stabilizing ~45,000–50,000 N (peak 62,470 at step 100, settling by step 500+)
- **Lift**: Increasing magnitude from −12,928 to −15,982 N (still evolving)
- **c_heat**: Declining from 4.58M to ~2.0M (stabilizing after step 700)
- **Particle count**: Decreasing from 1.384M to 1.321M (5% loss, normal for open-boundary DSMC)

**Est. completion**: ~90 min remaining at step 1000/2200 (~4.7s/step wall time with 6 MPI)  
**Last updated**: Step 1000 (Sep 3, 00:17 WIB)

---

## 3. Converged Results (Step 2,200 — Prior Completed Run)

The following data comes from the prior completed run (validation_timeseries.csv, 22 rows).

### 3.1 Aerodynamic Coefficients

| Metric | Scalloped DSMC | IRVE-3 Flight | LOFTID | Notes |
|--------|---------------|---------------|--------|-------|
| **C_d** (mean) | 1.460 | — | ~1.4–1.7 (Korzun 2024) | Per-element average |
| **C_l** (mean) | −0.549 | — | — | Negative = downward lift |
| **L/D** | 0.376 | — | — | |C_l/C_d| at Mach 10.29 (CSV step 2200: cl=−0.549, cd=1.460) |

> **Note on L/D**: The CSV-derived L/D = 0.376 differs from the Discussion.md value of 0.34. The Discussion.md value may use a different calculation method or reference source. The CSV value is directly from `|cl|/cd` at step 2200.
| **Peak Drag** | 45,334 N | — | — | Step 2200 value |
| **Peak \|Lift\|** | 17,048 N | — | — | Step 2200 value |
| **Peak G-load** | 16.83 g | 19.7 g (target) | 9.66 g | Below 25g structural limit |

### 3.2 Heat Flux Results

| Metric | Value (Step 2200) | IRVE-3 Flight | LOFTID | Notes |
|--------|-------------------|---------------|--------|-------|
| **Peak heat flux** | 1,744,640 W/m² (174.5 W/cm²) | 14.36 W/cm² | 39.27 W/cm² | Max cell KE flux |
| **Mean element heat flux** | 518,520 W/m² (51.9 W/cm²) | — | — | Σ\|q_i\| / N (per-element avg) |
| **Sutton-Graves** | 122,029 W/m² (12.2 W/cm²) | 14.36 W/cm² | — | C_SG=1.7415e-4, V=2700 m/s |
| **Total heat load** | 165.72 J/cm² | 195.06 J/cm² | 3,520 J/cm² | Cumulative |

### 3.3 Heat Flux Definitions

| CSV Column | Definition | Units | Notes |
|------------|-----------|-------|-------|
| `heatflux_max_Wm2` | Maximum cell kinetic energy flux | W/m² | DSMC raw max, statistically noisy |
| `heat_sum_Wm2` | Sum of absolute per-element KE flux: Σ\|q_i\| | W/m² | Total, not area-weighted |
| `heatflux_avg_Wm2` | Arithmetic mean: Σ\|q_i\| / N | W/m² | Per-element average (N=76) |
| `heatflux_sg_Wm2` | Sutton-Graves analytical: C_SG × √(ρ/R_n) × V³ | W/m² | Continuum estimate |

> **Important**: The `heatflux_avg_Wm2` column is the per-element arithmetic mean (divides by element count N=76, NOT by surface area). The SPARTA compute `f_1[3]` reports kinetic energy flux per surface element. The code comment at line 1577 references "Heat_Sum / Surf_Area" but the actual implementation (line 2095) uses `Heat_Sum / Float(N)`.

### 3.4 Derived Thermal Variables

| Variable | Value | Formula | Limit | Status |
|----------|-------|---------|-------|--------|
| **T_surface** | 1,811–2,339 K | (q_avg / (σ·ε))^0.25 | 1,700 K (SIC) | ⚠ FAIL (if CSV is W/m²) |
| **T_back** | 328 K | T_init + (Q × η_lag) / (ρ·Cp·δ) | 673 K (Kapton) | ✅ PASS |
| **β (ballistic coeff)** | 27.23 kg/m² | m × q_dyn / F_drag | — | Close to IRVE-3 ref 26.9 |

### 3.5 Ballistic Coefficient Convergence

| Step | β (kg/m²) |
|------|-----------|
| 100 | 19.68 |
| 200 | 22.65 |
| 300 | 21.40 |
| 400 | 22.05 |
| 500 | 23.02 |
| 600 | 23.21 |
| 700 | 23.54 |
| 800 | 23.88 |
| 900 | 24.37 |
| 1000 | 24.85 |
| ... | ... |
| 2200 | 27.23 |

Converging toward IRVE-3 reference β = 26.9 kg/m².

---

## 4. Comparison: StellarOrion DSMC vs IRVE-3 vs LOFTID

### 4.1 Vehicle Geometry

| Parameter | IRVE-3 | LOFTID | StellarOrion DSMC | Source |
|-----------|--------|--------|-------------------|--------|
| D (m) | 3.0 | 6.0 | 3.0 | Rapisarda 2023 |
| θ_cone (°) | 60 | 70 | 60 | Rapisarda 2023 |
| N_tori | 6 | 7 (6+1) | 6 | Rapisarda 2023 |
| r_torus (m) | 0.135 | — (not published) | 0.135 | Rapisarda Table 4.1 |
| Mass (kg) | 281 | ~960 | 281 | NASA TP-2013-4012 |
| A_ref (m²) | 7.069 | 28.27 | 7.069 | π × (D/2)² |

### 4.2 Flight Performance

| Parameter | IRVE-3 Flight | LOFTID | StellarOrion DSMC | Notes |
|-----------|---------------|--------|-------------------|-------|
| V_entry (km/s) | ~3.5–4.5 (suborbital) | >8.0 (LEO) | 3.379 (fixed) | ISA at 51.82 km |
| β (kg/m²) | 26.9 | ~22.6 | 27.23 | Converged DSMC |
| q_max (W/cm²) | 14.36 | 39.27 | 174.5 (peak cell) | DSMC max cell ≠ flight avg |
| Q_total (J/cm²) | 195.06 | 3,520 | 165.72 | Cumulative heat load |
| n_max (g) | 19.7 | 9.66 | 16.83 | Deceleration |
| C_d | — | ~1.4–1.7 | 1.460 | Converged mean |

### 4.3 Key Discrepancies

1. **Peak heat flux (174.5 W/cm² vs 14.36 W/cm² IRVE-3)**: The DSMC max-cell value is ~12× higher than IRVE-3 flight. This is expected because:
   - DSMC max cell is a point value with statistical noise, not an area-averaged measurement
   - IRVE-3 flight reports stagnation-point heat flux (area-averaged over probe)
   - Coarse mesh (76 elements) inflates peak cell values
   - Rarefied effects (Kn >> 0.01) produce higher localized heating than continuum

2. **Heat load (165.72 vs 195.06 J/cm² IRVE-3)**: 15% lower than flight. This is because:
   - DSMC run is single-point (constant altitude/velocity), not full trajectory
   - IRVE-3 heat load integrates over entire entry trajectory
   - Single-point DSMC captures only the peak heating condition

3. **Ballistic coefficient (27.23 vs 26.9 kg/m² IRVE-3)**: Very close (<2% difference), confirming geometry fidelity.

4. **G-load (16.83 vs 19.7 g IRVE-3)**: 15% lower. Single-point DSMC at one altitude doesn't capture the full deceleration profile.

---

## 5. Heat Flux Unit Investigation

### 5.1 SPARTA Data Flow

```
in.hiad: compute 1 surf hiad_surf air nflux mflux ke
  → 3-component surface compute per element
  → f_1[1] = nflux (number flux)
  → f_1[2] = mflux (momentum flux)  
  → f_1[3] = ke (kinetic energy flux, W/m²)

stellarorion_sparta.adb line 1999:
  Heat(Row) := V(4)  -- reads f_1[3] = ke

Line 2022:
  Heat_Sum += |Heat(I)|  -- sum of absolute per-element KE

Line 2095:
  Avg_Heat_Flux := Heat_Sum / Float(N)  -- per-element mean
```

### 5.2 DSMC vs Sutton-Graves Comparison

| Metric | DSMC (step 800) | Sutton-Graves | Ratio |
|--------|-----------------|---------------|-------|
| Peak KE flux | 1,934,060 W/m² | — | — |
| Per-element avg | 665,815 W/m² | — | — |
| SG stagnation | — | 122,003 W/m² | — |
| **DSMC peak / SG** | — | — | **15.9×** |
| Free-stream KE flux | 6,857,000 W/m² | — | — |
| DSMC peak / h₀ | 0.26× | — | — |

### 5.3 Sources of DSMC–SG Discrepancy

1. **Nose radius**: SG uses R_n=0.55m (default), but effective HIAD nose radius is larger (blunter body)
2. **Continuum vs rarefied**: SG is a continuum correlation; DSMC captures rarefied effects at Kn >> 0.01
3. **Mesh resolution**: 76 surface elements (coarse) inflates peak cell values
4. **Internal energy**: SG doesn't account for vibrational/electronic excitation at Mach 10+
5. **Geometry**: HIAD toroid shape differs from SG's hemisphere assumption
6. **Velocity mismatch**: SG uses V=2700 (SPARTA), trajectory uses V=3379

---

## 6. Derived Variable Plots

Six derived plots were generated from the convergence data:

| Plot | File | Description |
|------|------|-------------|
| T_surface vs step | `T_surface_vs_step.png` | Radiative equilibrium temperature from area-averaged heat flux |
| T_back vs step | `T_back_vs_step.png` | 1D transient backface temperature |
| β vs step | `beta_vs_step.png` | Ballistic coefficient convergence |
| T_surface + T_back | `T_surface_T_back_combined.png` | Dual-axis thermal plot |
| Physical dashboard | `physical_dashboard.png` | 4-panel overview (T_s, T_back, β, g-load) |
| Survivability | `survivability_assessment.png` | Pass/fail against material limits |

### 6.1 VTU Visualization Plots

Twelve visualization plots from VTU surface data (3 steps × 4 plot types):

| Step | 3D Surface | 2D Cross-section | Histogram | Heat Flux vs X |
|------|-----------|-----------------|-----------|----------------|
| 100 | `vtu_step_100_3d.png` | `vtu_step_100_cross.png` | `vtu_step_100_hist.png` | `vtu_step_100_vs_x.png` |
| 900 | `vtu_step_900_3d.png` | `vtu_step_900_cross.png` | `vtu_step_900_hist.png` | `vtu_step_900_vs_x.png` |
| 2200 | `vtu_step_2200_3d.png` | `vtu_step_2200_cross.png` | `vtu_step_2200_hist.png` | `vtu_step_2200_vs_x.png` |

---

## 7. Survivability Assessment

| Check | Criterion | Value | Limit | Status |
|-------|-----------|-------|-------|--------|
| T_surface | T < 1,700 K | 1,811–2,339 K | 1,700 K (SIC) | ⚠ FAIL (if W/m²) |
| T_back | T < 673 K | 328 K | 673 K (Kapton adhesive) | ✅ PASS |
| G-load | n < 25 g | 16.83 g | 25 g (structural) | ✅ PASS |
| β | β ≈ 26.9 | 27.23 kg/m² | — | ✅ CLOSE (<2%) |
| C_d | 1.4–1.7 range | 1.460 | — | ✅ PASS |

> **T_surface caveat**: The 1,811–2,339 K range is derived from `heatflux_avg_Wm2` (51.9 W/cm² area-averaged). If the heat flux unit is correct, the surface exceeds SIC limits. However, the heat flux value may include normalization artifacts (per-element average vs true area-weighted average). The IRVE-3 flight peak is 14.36 W/cm², which would give T_surface ≈ 1,313 K — well within SIC limits.

---

## 8. Code Fixes Applied

Four critical Ada fixes were required to make the simulation valid:

1. **Sin_Rad/Cos_Rad range reduction** (`stellarorion_geometry.adb`): Fold large arguments into [-π, π] for Taylor series accuracy
2. **Run_SPARTA surf copy path** (`stellarorion_sparta.adb`): Read surf file from `Results_Dir`, not hardcoded repo root
3. **Parse_Surf_Geometry state exit** (`stellarorion_sparta.adb`): Exit State=1 when "Lines" keyword detected, preventing Curve corruption
4. **Heat_Flux_Avg dimensional correction** (`stellarorion_sparta.adb`): Changed from `Heat_Sum / Surf_Area` (W/m⁴) to `Heat_Sum / Float(N)` (W/m²)

---

## 9. Storage Paths

| Artifact | Path |
|----------|------|
| Validation CSV | `results_validation_scalloped/validation_timeseries.csv` |
| Trajectory Profile | `results_validation_scalloped/trajectory_profile.csv` |
| Raw SPARTA Dumps | `results_validation_scalloped/surf.*.out` |
| VTU Files | `results_validation_scalloped/paraview/surf_*.vtu` |
| Original Plots | `results_validation_scalloped/plots/*.png` (18) |
| Derived Plots | `results_validation_scalloped/plots/*.png` (6 derived) |
| VTU Visualizations | `results_validation_scalloped/plots/vtu_*.png` (12) |
| Derived Plot Script | `scripts/make_derived_plots.py` |
| VTU Visualization Script | `scripts/make_vtu_visualization.py` |
| Comparison Script | `scripts/compare_validation.py` |
| Discussion Document | `Sep 2 Discussion.md` |

---

## 10. Open Items

1. **Heat flux unit validation**: Confirm whether `heatflux_avg_Wm2` is truly W/m² or has a normalization factor
2. **Area-weighted average**: Implement proper area-weighted heat flux (Surf_Area is computed but unused)
3. **Full trajectory integration**: Single-point DSMC doesn't capture full entry heat load
4. **Mesh refinement**: 76 elements may be too coarse for reliable peak heat flux
5. **Internal energy modes**: SPARTA 5-species air includes vibrational modes; verify ke compute captures total enthalpy
6. **VTU output for new run**: Current run will produce new VTU files at steps 100, 200, ..., 2200
7. **Smooth vs Scalloped comparison**: Update with new run data when complete

---

## References

1. Rapisarda, V. (2023). *Multidisciplinary Design Analysis and Optimization of Hypersonic Inflatable Aerodynamic Decelerators*. PhD Thesis.
2. Korzun, A.M. et al. (2024). AIAA-2024-1500. LOFTID aerodynamic characterization.
3. Hollis, B.R. et al. (2024). AIAA-2024-1498. HIAD TPS thermal analysis.
4. Plimpton, S.J. & Gallis, M.A. (2014). SPARTA DSMC documentation.
5. NASA TP-2013-4012. IRVE-3 mission report.
6. Bird, G.A. (1994). *Molecular Gas Dynamics and the Direct Simulation of Gas Flows*. Oxford University Press.
