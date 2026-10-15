# SOP compliance audit — missing data & plots

**Scope.** `Standard Operating Procedure of CFD.md` (688 lines) is a *status-quo
reference*: A1 states it "does not yet describe this repository", and line 686
states adaptation for StellarOrion "has not been performed". This audit performs
that deferred adaptation: it maps every SOP-required output onto what the
repository actually emits, and lists what is missing.

**Method.** Every claim below is measured, not assumed. Plot inventory = 684 PNGs
enumerated by `find` and deduplicated by name pattern. Generator inventory =
`scripts/*.py` + `src/python/*.py`. "Missing" means **zero artefacts AND zero
generators** — a plot that exists is counted even if its generator name differs.

Date: 2026-10-15.

---

## 1. Verdict summary

| SOP requirement | Chapter | Status | Evidence |
|---|---|---|---|
| Contours on surfaces/planes | 10 | **PRESENT** | `thermal_map`, `pressure_map`, `mach_map`, `knudsen_map`, `vtu_cross_section` (42 ea.) |
| Vectors | 10 | **PRESENT** | `velocity_vectors_smooth_step_*.png` (34) |
| Surface integrals / fluxes | 10 | **PRESENT** | `heat_load_jcm2_vs_step`, `heat_sum_Wm2_vs_step` (8 ea.) |
| Force / moment reports (C_L, C_D) | 10 | **PRESENT** | `cd_vs_step.png`, `cl_vs_step.png` (8 ea.) |
| XY plots (profiles, history) | 10 | **PRESENT** | `*_vs_step` series (~20 kinds), `vtu_heatflux_vs_x_stepN` (42) |
| Section planes | 10 | **PRESENT** | `vtu_cross_section_stepN.png` (42) |
| Exports (.csv/.dat) | 10 | **PRESENT** | per-tree CSVs; `validation_timeseries.csv` |
| **Pathlines / streamlines** | 10 | **MISSING** | 0 artefacts; 0 generators (`stream` matches were data-stream words) |
| **Isosurfaces** | 10 | **MISSING** | 0 artefacts; 0 generators |
| Convergence evidence (residuals+monitors) | 12#6 | **PRESENT** | `convergence_residuals_master_smooth.png`, `convergence_audit_plot.png`, `convergence_multi_metric_dual_axis.png` |
| Mesh quality record (min/mean) | 12#3 | **PRESENT** | `mesh_statistics_smooth_step_*.png` (34) |
| **Mesh independence result (3-level)** | 12#4, 15 | **MISSING** | 0 artefacts; grep for `refinement level`/`three-level` = **0 hits** |
| **Setup sheet** | 12#5, 15 | **MISSING** | 0 artefacts named `setup_sheet` |
| **Uncertainty / tolerance on comparisons** | 12#7, 14 | **MISSING** | 0 artefacts; 0 generators |
| **Inlet/outlet (mass) balance closed** | 15 | **MISSING** | 0 artefacts; 0 generators |
| Validation comparison vs reference | 12#9 | **PRESENT** | `*_full_*_dsmc_pinn.png` (4 ea.), `survivability_assessment.png` |
| Field visualisations | 12#8 | **PRESENT** | as contours above |

**SOP gaps: 6 missing outputs.** Ranked by review risk (Ch. 14: "Result cannot be
explained in review → Missing evidence from Chapter 12"):

1. **Mesh independence (3-level)** — Ch. 12 #4 calls it *the* thing without which
   "the numbers are mesh-dependent"; Ch. 15 requires "Three-level mesh independence
   completed and recorded". No generator exists at all.
2. **Setup sheet** — Ch. 12 #5; its absence also fails Ch. 11 #6 (record software
   release, mesh level, models, BCs, schemes, iteration count, criterion).
3. **Uncertainty / tolerance** — Ch. 12 #7 and #12.3 demand every comparison claim
   carry a range; Ch. 14 lists "A single number with no range" as insufficient.
4. **Mass/balance closure** — Ch. 15 "Inlet/outlet balance closed".
5. **Streamlines / pathlines** — Ch. 10. (For DSMC a particle-track view is the
   analogue; low risk, but genuinely absent.)
6. **Isosurfaces** — Ch. 10. Same.

---

## 2. ParaView-side gaps (measured with the real VTK reader)

`scripts/audit_vtu.py --root results` — 1551 files.

### 2.1 FIXED tonight

**Corrupt connectivity in all 66 `surf_*.vtu`.** `stellarorion_sparta.adb`
Write_VTU emitted a separator inside each cell but *not between cells*, so
cell N's last index concatenated onto cell N+1's first:

```
expected 14592 indices -> 11856 tokens   (14592 - 2736 glues = 11856)
2709 tokens outside [0,3696): '1010', '36473647'
vtk error 20008: "the connectivity array is not long enough" -> 0 points, 0 cells
```

That is the reported *"array thingy when I click visibility"*: the grid never
loaded, so every array appeared broken. Fixed in the Ada writer (commit
`bc1e8027`), and the 68 existing files repaired with proof (§ P0.4 of the
overnight plan). **0 unreadable files remain.**

### 2.2 Still open

| # | Gap | Measured | Impact |
|---|---|---|---|
| G1 | `surf_*.vtu` carries **no PointData** at all | point_arrays = `[]` for all 66 | ParaView can only colour by *cell* (flat/faceted) values; smooth interpolated surface colouring is impossible |
| G2 | `surf_*.vtu` has 3 cell arrays vs `surf_pinn_*`'s 8 | missing `step`, `G_Load`, `HeatLoad_Jcm2`, `HeatFlux_Max_Wm2`, `drag_coefficient` | Production snapshots lack the derived quantities the PINN export already writes |
| G3 | `optimisation_output/optimised_geometry.vtu` is **empty** | `NumberOfPoints="0" NumberOfCells="0"` | No geometry to display for the optimisation result |
| G4 | 1482 `irve*_alt*_km_step*.vtu` are **1-point / 1-cell** | 1 point at `(0,0,altitude)`, 1 tuple per array | They are time-series scalar records dressed as geometry — nothing to see in a 3-D view; they belong in an XY/Time-plot, not a mesh |
| G5 | No `FieldData` anywhere | `field_arrays = []` across all 1551 | No embedded provenance (time, case id, units) — Ch. 11 "record for every run" is not satisfied inside the artefact |

Array inventory actually present across the tree:

- **Point arrays (11):** `altitude_km, density_kgm3, drag_force_N, dynamic_pressure_Pa, g_load, heat_flux_Wcm2, heat_flux_Wm2, mach_number, pressure_Pa, temperature_K, velocity_ms`
- **Cell arrays (14):** `angle_deg, diameter_m, mass_kg, nose_radius_m, step, toroid_count, toroid_radius_m, Drag_N, G_Load, HeatFlux_Max_Wm2, HeatFlux_Wm2, HeatLoad_Jcm2, Lift_N, drag_coefficient`

---

## 3. Recommended order

1. Mesh independence study (3 grid levels, same case) — closes the single
   highest-risk SOP gap and is a real measurement, not a document.
2. Setup sheet generator wired into `run.py` — cheap, satisfies Ch. 11 #6 + 12 #5.
3. PointData + missing cell arrays on `surf_*.vtu` — closes G1/G2.
4. Uncertainty bands on the validation comparison plots — closes #7 / #12.3.

*Streamlines and isosurfaces (5 and 6) are recorded as accepted limitations for a
particle-based DSMC solver unless the owner asks for them.*
