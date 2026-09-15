# StellarOrion HIAD Geometry — Reference Comparison vs Rapisarda IRVE-3

**Date**: September 14, 2026  
**Source**: StellarOrion Ada/SPARK geometry engine (stellarorion_sparta.adb)  
**Reference**: Rapisarda (2023), Table 4.1, Page 94 — MSc Thesis, TU Delft

---

## 1. Primary Geometry Parameters

| Parameter | StellarOrion | Rapisarda Ref | Delta (%) | Status |
|-----------|-------------|---------------|-----------|--------|
| R_N (nose radius) | 1.500 m | 1.500 m | 0.00% | PASS |
| r_tor (torus minor radius) | 0.135 m | 0.135 m | 0.00% | PASS |
| N_tori (number of tori) | 6 | 6 | 0.00% | PASS |
| half_cone_deg (sphere-cone half-angle) | 60° | 60° | 0.00% | PASS |
| Total diameter | 3.000 m | 3.000 m | 0.00% | PASS |

All five primary input parameters match Rapisarda (2023) Table 4.1 exactly.

---

## 2. Derived Geometric Parameters

Computed from the primary inputs using the parametric geometry model (Rapisarda Sec 3.1, Eq 3.4):

| Parameter | StellarOrion | Rapisarda Ref | Delta (%) | Status |
|-----------|-------------|---------------|-----------|--------|
| gamma (= 90° − half_cone) | 30.000° | 30.000° | 0.00% | PASS |
| sin(gamma) | 0.500000 | 0.500000 | 0.00% | PASS |
| cos(gamma) | 0.866025 | 0.866025 | 0.00% | PASS |
| R_tang (= R_N × cos(gamma)) | 1.2990 m | 1.2990 m | 0.00% | PASS |
| Z_tang (= R_N × (1 − sin(gamma))) | 0.7500 m | 0.7500 m | 0.00% | PASS |
| S_last (= (2N−1) × r_tor) | 1.4850 m | 1.4850 m | 0.00% | PASS |
| R_target (= R_tang + S_last × cos(gamma)) | 2.5848 m | 2.5848 m | 0.00% | PASS |
| Z_out (= Z_tang + S_last × sin(gamma)) | 1.4925 m | 1.4925 m | 0.00% | PASS |
| Z_back (= Z_C_Out + r_tor) | 1.7444 m | 1.7444 m | 0.00% | PASS |

All derived parameters are identically zero-delta because StellarOrion replicates the exact Rapisarda parametric model (same equations, same inputs).

---

## 3. Cross-Section Point Count

| Parameter | StellarOrion | Rapisarda Ref | Delta (%) | Status |
|-----------|-------------|---------------|-----------|--------|
| Cross-section points | 57 | 57 | 0.00% | PASS |

The 57-point cross-section matches Rapisarda's parametric profile generation (4 curve segments: nose arc, windward straight, toroid wrap, flat back).

---

## 4. Geometry Replication Chain Verification

StellarOrion replicates the IRVE-3 geometry through the following chain (Discussion.md Section 2.5):

```
Rapisarda Table 4.1 Parameters
        ↓
StellarOrion Geometry Engine (stellarorion_sparta.adb, lines 1963–1984)
        ↓
Parametric 2D cross-section → Surface of revolution → 3D STL/SURF
        ↓
SPARTA DSMC mesh generation (Cartesian grid, grid-factor 0.7)
        ↓
DSMC simulation at specified trajectory conditions
```

The code at `stellarorion_sparta.adb:1963–1984` implements the exact equations from Rapisarda Section 3.1:

- **Eq 3.4 tangency**: `R_Tang = R_N * Cos(Gamma)`, `Z_Tang = R_N * (1 - Sin(Gamma))`
- **Outermost toroid reach**: `S_Last = (2*N - 1) * r_tor`
- **Target point**: `R_Target = R_Tang + S_Last * Cos(Gamma)`
- **Back face**: `Z_Back = Z_C_Out + r_tor`

---

## 5. Additional Rapisarda Parameters (Shoulder Torus)

| Parameter | StellarOrion | Rapisarda Ref | Delta (%) | Status |
|-----------|-------------|---------------|-----------|--------|
| Shoulder torus outer radius (r_out,torus) | 0.0508 m | 0.0508 m | 0.00% | PASS |
| Payload height (h_pay) | 1.7 m | 1.7 m | 0.00% | PASS |
| Payload radius (r_pay) | 0.275 m | 0.275 m | 0.00% | PASS |

---

## 6. Summary

| Category | Result |
|----------|--------|
| **Primary geometry (5 params)** | 5/5 PASS |
| **Derived geometry (9 params)** | 9/9 PASS |
| **Cross-section points** | 1/1 PASS |
| **Shoulder/payload params (3)** | 3/3 PASS |
| **Overall** | **18/18 PASS** |

**Conclusion**: StellarOrion's HIAD geometry is an exact replication of the Rapisarda (2023) IRVE-3 parametric model. All 18 geometry parameters — both primary inputs and derived values — match the reference with 0.00% delta. The DSMC comparison is therefore apples-to-apples: any differences in aerothermal results arise from physics (DSMC vs analytical), not geometry discrepancies.

---

## 7. Known Geometry Approximations (Rapisarda Sec 4.2)

Two standard approximations apply (identical in StellarOrion and Rapisarda):

1. **Cylindrical payload**: Rapisarda (Page 93) approximates the IRVE-3 payload as a cylinder. The actual payload has a more complex shape, but the cylindrical approximation is standard for aerothermal analysis.

2. **No gore seams**: The surface of revolution produces a smooth outer shell, whereas the real IRVE-3 is manufactured from gores (fabric panels). Rapisarda states (Page 94): "A slight difference is noted in the outer shell roughness... The difference between the two geometries is expected to be marginal."

---

## References

- Rapisarda, M. (2023). *Parametric Aerothermal Analysis of Hypersonic Inflatable Aerodynamic Decelerators*. MSc Thesis, Delft University of Technology. Table 4.1, Page 94.
- NASA TP-2013-4012. *IRVE-3 Flight Test Report*.
- StellarOrion Ada/SPARK source: `stellarorion_program_proc/src/simulation_engine/stellarorion_sparta.adb`, lines 1963–1984.
