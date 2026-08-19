---
session: ses_078f
updated: 2026-08-13T15:18:23.792Z
---

# Session Summary

## Goal
Validate and fix the StellarOrion HIAD hypersonic simulation pipeline, run IRVE-3 headless validation, and compare results against reference flight/MDAO data to ensure accuracy.

## Constraints & Preferences
- Must use Docker for SPARTA DSMC simulation (`sparta-hysp` image)
- Dimension-2 axisymmetric simulation (`boundary o ao p`)
- Environment: Python 3.13, macOS, 10 MPI cores
- Reference: IRVE-3 flight data and MDAO model (Rapisarda 2023)
- Reference targets: Cd=1.47, heat=14.36 W/cm², total_heat=195.06 J/cm², decel=20.2 G, beta=26.9 kg/m², p_stag=12.4 kPa

## Progress
### Done
- [x] Created `validate_simulation_input.py` — checks .surf, .stl, SPARTA scripts, cross-validates bounds
- [x] Integrated validation at 3 points: main.py:1609, StellarOrionEngineMach5Up.py:2079, --validate-only CLI flag
- [x] **Bug Fix 1**: `env_nrho` 3.47e21 → 3.47e22 (main.py:1535) — was 10x too low
- [x] **Bug Fix 2**: 2D→3D axisymmetric Cd correction added (main.py:1669-1674)
- [x] Simulation completed: 1,109,048 particles, 1100 steps, 12 dump files generated
- [x] All validation checks pass (0 errors, 2 warnings)
- [x] ParaView output: 12 VTU files + 3D upscaled VTP + state file

### In Progress
- [ ] **CRITICAL: Axisymmetric correction formula is WRONG** — Cd=34.3 vs target 1.47 (23x error)
- [ ] Investigating correct interpretation of SPARTA `compute surf fx fy fz` force units
- [ ] Need to compare HIAD_custom.surf (used by SPARTA) vs HIAD_sample.surf (used by centroid code)

### Blocked
- Cd discrepancy is fundamental: none of the tested interpretations of SPARTA force units produce the correct Cd (V1=3.73, V2=34.3, V3=2.64, target=1.47)

## Key Decisions
- **env_nrho = 3.47e22**: Matches Rapisarda 2023 Table 4.5 at ~52km altitude
- **Sutton-Graves**: C_sg=1.7415e-4, nose_r=0.55m (standard NASA TR R-376)
- **Reference area**: π × (3.0/2)² = 7.069 m²

## Next Steps
1. **Read HIAD_custom.surf** (CADDesign/HIAD_custom.surf) and compare with HIAD_sample.surf — different geometry could explain force discrepancy
2. **Resolve axisymmetric correction formula**: Test if SPARTA `ao` boundary already applies axisymmetric weighting, or if forces need different scaling
3. **Fix the Cd computation** in main.py:1669-1674 and `_compute_surf_centroid()` at StellarOrionEngineMach5Up.py:579-668
4. **Re-run comparison** with corrected formula
5. **Update main.py** post-processing with correct axisymmetric conversion
6. **Present final comparison table** to user
7. **Update goal** with verified evidence of completion

## Critical Context
- **SPARTA surf dump columns**: `id f_1[1](nflux) f_1[2](mflux) f_1[3](ke) f_surfavg[1](fx) f_surfavg[2](fy) f_surfavg[3](fz)`
- **Raw drag data (sum f_surfavg[1])**: Steps 900-1100 average = 159,616 N
- **Tested interpretations**:
  - V1: F_3D = Σ|fx| (no correction) → Cd=3.74
  - V2: F_3D = Σ|fx|×2πy (force per unit z-depth) → Cd=34.3
  - V3: F_3D = Σ|fx|×2πy×Δl (force per unit area) → Cd=2.64
  - Target Cd=1.47 → F_3D should be ≈63,224 N
- **Key mismatch**: V1 (no correction) gives Cd=3.73, which is the SAME ratio to target regardless of density (both F_drag and q scale linearly with nrho)
- **SPARTA in.hiad reads HIAD_custom.surf**, but Python centroid code reads HIAD_sample.surf — these may differ
- **in.hiad fix definitions**:
  - `compute 1 surf hiad_surf air nflux mflux ke`
  - `compute surfF surf hiad_surf air fx fy fz`
  - `fix surfavg ave/surf hiad_surf 1 100 100 c_surfF[*]`
  - `compute drag reduce sum f_surfavg[1]`

## File Operations
### Read
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/HIAD_sample.surf`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/in.hiad`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/surf.1100.out`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/StellarOrionEngineMach5Up.py` (lines 579-668 centroid, 831-942 parse_sparta_results)
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/main.py` (lines 1655-1734 post-processing)
- All surf.*.out and grid.*.out in results_reference/

### Modified
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/main.py` (env_nrho fix at line 1535, Cd correction at lines 1669-1674)
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/validate_simulation_input.py` (new file)
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/StellarOrionEngineMach5Up.py` (pre-Docker validation at lines 2079-2098)
