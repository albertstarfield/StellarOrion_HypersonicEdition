# HIAD Shield Mass Calculation Methodology

## 1. Overview

This document describes the analytical methodology used to calculate the total mass of the Hypersonic Inflatable Aerodynamic Decelerator (HIAD) shield system in the StellarOrion HIAD Designer Tool. The shield mass is computed from geometry parameters, TPS material properties, and structural assumptions.

**Reference**: IRVE-3 Mission (NASA/TP-2013-4012, Rapisarda 2023)

---

## 2. Geometry Assumptions

### 2.1 IRVE-3 Baseline Configuration

| Parameter | Symbol | Value | Source |
|-----------|--------|-------|--------|
| Aeroshell Diameter | D | 3.0 m | IRVE-3 flight hardware |
| Half-cone Angle | θ | 60° | IRVE-3 design specification |
| Nose Radius | R_n | 0.55 m | Sphere-cone tangency geometry |
| Toroid Count | N | 6 | Rapisarda (2023) MDAO baseline |
| Toroid Radius | r_t | 0.135 m | Rapisarda Table 4.1 |
| Outer Toroid Radius | r_o | 0.0508 m | Rapisarda Table 4.1 |
| Payload Height | h_pay | 1.7 m | Rapisarda Table 4.1 |
| Payload Radius | r_pay | 0.275 m | Rapisarda Table 4.1 |
| Total Vehicle Mass | m_total | 281.0 kg | NASA/TP-2013-4012 |

### 2.2 Sphere-Cone Geometry

The HIAD forebody is a **sphere-cone** shape defined by:

- **Nose sphere**: Hemisphere with radius R_n = 0.55 m
- **Cone section**: Half-angle θ = 60° from tangency point to outer edge
- **Tangency point**: Where nose sphere meets cone envelope

```
Tangency coordinates:
  r_tangency = R_n × cos(θ) = 0.55 × cos(60°) = 0.275 m
  z_tangency = R_n × (1 - sin(θ)) = 0.55 × (1 - 0.866) = 0.074 m
```

---

## 3. TPS Material Properties

### 3.1 Multi-Layer F-TPS Construction

The IRVE-3 used a **Flexible Thermal Protection System (F-TPS)** consisting of three primary layers:

| Layer | Material | Thickness (mm) | Density (kg/m³) | Function |
|-------|----------|----------------|-----------------|----------|
| Outer | Nicalon SiC | 0.506 | 1468 | Thermal protection, oxidation resistance |
| Middle | Pyrogel | 3.047 | 110 | Primary insulation |
| Inner | Kapton | 0.025 | 3100 | Structural integrity, gas barrier |
| **Total** | — | **3.578** | ~1468 (effective) | — |

### 3.2 Material Specifications (MDAO Reference Table B.17)

| Material | Emissivity (ε) | Density (ρ) | Max Temp (K) | Specific Heat (Cp) |
|----------|----------------|-------------|--------------|---------------------|
| SiC (Nicalon) | 0.75 | 1468 kg/m³ | 2073 K | 1100 J/kg·K |
| Pyrogel | 0.90 | 110 kg/m³ | 1373 K | 1000 J/kg·K |
| Kapton | 0.12 | 3100 kg/m³ | 773 K | 1090 J/kg·K |

### 3.3 Effective Density Calculation

For mass calculation purposes, an **effective density** is used:

```
ρ_eff = (t_SiC × ρ_SiC + t_Pyrogel × ρ_Pyrogel + t_Kapton × ρ_Kapton) / t_total
      = (0.506×1468 + 3.047×110 + 0.025×3100) / 3.578
      = (742.8 + 335.2 + 77.5) / 3.578
      = 1155.5 / 3.578
      ≈ 323 kg/m³ (actual effective)
```

**Note**: The current implementation uses ρ_eff = 1468 kg/m³ (SiC density) as a conservative upper bound.

---

## 4. Analytical Formulas

### 4.1 Nose Sphere Cap Area

The nose is a spherical cap formed by the sphere-cone tangency:

```
A_nose = 2π × R_n × h_cap

where:
  h_cap = R_n × (1 - sin(θ))     [cap height]
  R_n = nose radius               [0.55 m]
  θ = half-cone angle             [60°]

Calculation:
  h_cap = 0.55 × (1 - sin(60°)) = 0.55 × 0.134 = 0.0737 m
  A_nose = 2π × 0.55 × 0.0737 = 0.255 m²
```

### 4.2 Cone Frustum Area

The cone section is a frustum (truncated cone) from tangency to outer edge:

```
A_cone = π × (r_tangency + r_target) × L_slant

where:
  r_tangency = R_n × cos(θ) = 0.275 m
  r_target = D/2 = 1.5 m
  L_slant = (r_target - r_tangency) / sin(θ) = (1.5 - 0.275) / sin(60°) = 1.414 m

Calculation:
  A_cone = π × (0.275 + 1.5) × 1.414 = 7.888 m²
```

### 4.3 Scallop Factor

The toroid wrapping creates a scalloped surface that increases the effective area:

```
Scallop Factor = 1.2   [empirical for stacked toroids]
                 1.0   [flat skin mode]

Total Area = (A_nose + A_cone) × Scallop Factor
           = (0.255 + 7.888) × 1.2
           = 9.771 m²
```

### 4.4 Shield Volume

Using the thin-shell approximation:

```
V_shield = A_total × t_tps

where:
  A_total = 9.771 m²
  t_tps = 0.003578 m (3.578 mm)

Calculation:
  V_shield = 9.771 × 0.003578 = 0.03496 m³
```

### 4.5 Shield Skin Mass

```
m_shield = V_shield × ρ_eff

Calculation:
  m_shield = 0.03496 × 1468 = 51.32 kg
```

### 4.6 Toroid Structure Mass

Each toroid is modeled as a torus with 10% density factor (inflatable structure):

```
V_torus = 2π² × R_center × r_t²

where:
  R_center = r_target × 0.7 = 1.05 m  [approximate center radius]
  r_t = toroid radius = 0.135 m

Calculation:
  V_torus_each = 2π² × 1.05 × 0.135² = 0.378 m³
  V_torus_total = 0.378 × 6 = 2.268 m³
  m_torus = 2.268 × 1468 × 0.1 = 332.71 kg
```

**Note**: The 10% density factor is a **conservative assumption**. Actual inflatable toroids use woven fabric at ~5-15% of solid material density.

---

## 5. Mass Breakdown

### 5.1 Calculated Mass Components

| Component | Formula | Mass (kg) | Notes |
|-----------|---------|-----------|-------|
| Nose sphere cap | A_nose × t × ρ | ~0.13 kg | Thin shell |
| Cone frustum | A_cone × t × ρ | ~40.19 kg | Primary structure |
| Scallop wrapping | (A_total - A_flat) × t × ρ | ~11.00 kg | Toroid wrap |
| **Shield Skin Total** | — | **51.32 kg** | F-TPS layers |
| Toroid structure | V_torus × ρ × 0.1 | 332.71 kg | Inflatable (conservative) |
| **Total Shield Mass** | — | **384.03 kg** | |

### 5.2 Comparison with Flight Data

| Source | Shield Mass | Notes |
|--------|-------------|-------|
| **Calculated (this method)** | 384.03 kg | Conservative toroid assumption |
| **NASA/TP-2013-4012 estimate** | ~30-50 kg | F-TPS only, no toroids |
| **Rapisarda (2023) estimate** | ~40-60 kg | F-TPS + attachment |
| **Actual IRVE-3 total** | 281.0 kg | Entire vehicle |

### 5.3 Mass Fraction Analysis

```
Shield Mass Fraction = m_shield / m_total × 100%
                     = 384.03 / 281.0 × 100%
                     = 136.7%  [⚠️ Overestimation]
```

**Expected**: Shield mass should be 15-25% of total vehicle mass for HIAD systems.

---

## 6. Known Limitations

### 6.1 Overestimation Sources

| Issue | Impact | Correction Factor |
|-------|--------|-------------------|
| Toroid density too high | +332 kg | Use 5-15% of solid density |
| Scallop factor conservative | +20% area | Depends on geometry |
| No fastener/adhesive mass | -5 kg | Add 5-10 kg for joints |
| No payload interface mass | -10 kg | Add backshell hardware |
| Effective density assumption | +200 kg | Use actual 323 kg/m³ |

### 6.2 Underestimation Sources

| Issue | Impact | Correction |
|-------|--------|------------|
| No wiring/harness mass | -2 kg | Add electrical systems |
| No separation hardware | -3 kg | Add pyro bolts, springs |
| No thermal blankets | -1 kg | Add MLI layers |

---

## 7. Recommendations for Accurate Mass Estimation

### 7.1 Use Layer-Specific Calculation

```python
# Recommended: Calculate each layer separately
m_SiC = A_total × t_SiC × ρ_SiC = 9.771 × 0.000506 × 1468 = 7.24 kg
m_Pyrogel = A_total × t_Pyrogel × ρ_Pyrogel = 9.771 × 0.003047 × 110 = 3.26 kg
m_Kapton = A_total × t_Kapton × ρ_Kapton = 9.771 × 0.000025 × 3100 = 0.76 kg
m_FTPS_total = 7.24 + 3.26 + 0.76 = 11.26 kg
```

### 7.2 Correct Toroid Density

```python
# Use actual inflatable structure density
ρ_inflatable = 15-50 kg/m³  [woven fabric + gas]
m_torus = V_torus × ρ_inflatable = 2.268 × 30 = 68.04 kg
```

### 7.3 Complete Mass Budget

| Component | Mass (kg) | Percentage |
|-----------|-----------|------------|
| F-TPS shield skin | 11.26 | 4.0% |
| Toroid structure | 68.04 | 24.2% |
| Attachment hardware | 8.0 | 2.8% |
| Payload/instruments | 160.0 | 56.9% |
| Backshell/structure | 33.7 | 12.0% |
| **Total** | **281.0** | **100%** |

---

## 8. Implementation Notes

### 8.1 Code Location

- **Analytical method**: `StellarOrionEngineMach5Up.py:222` — `calculate_shield_mass_analytical()`
- **Geometry-based method**: `StellarOrionEngineMach5Up.py:163` — `calculate_shield_mass()`
- **Flight metrics integration**: `StellarOrionEngineMach5Up.py:843` — `calculate_flight_metrics()`

### 8.2 Usage Examples

```python
from StellarOrionEngineMach5Up import Api

# IRVE-3 baseline
baseline = Api.get_irve_baseline_results_static()
shield_mass = baseline['shield_mass_analysis']
print(f"Shield mass: {shield_mass['total_shield_mass_kg']:.2f} kg")

# Custom geometry
custom = Api.calculate_shield_mass_analytical(
    diameter_m=5.0,
    angle_deg=60.0,
    toroid_count=10,
    toroid_radius_m=0.135,
    tps_thickness=0.003578,
    tps_density=1468.0
)
print(f"Custom shield mass: {custom['total_shield_mass_kg']:.2f} kg")
```

---

## 9. References

1. **NASA/TP-2013-4012**: Lau, K., et al. (2013). "IRVE-3 Post-Flight Aerothermal Reconstruction."
2. **AIAA-2013-1390**: Dillman, R. A., et al. (2013). "Flight Performance of the Inflatable Reentry Vehicle Experiment 3."
3. **Rapisarda (2023)**: "Multidisciplinary Design Analysis and Optimisation of Inflatable Stacked Toroid Decelerators." Delft University of Technology.
4. **MDAO Validation Ref**: Table B.17 — TPS Material Specifications.

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-09 | StellarOrion Team | Initial documentation |

---

*This document is part of the StellarOrion HIAD Designer Tool documentation suite.*
