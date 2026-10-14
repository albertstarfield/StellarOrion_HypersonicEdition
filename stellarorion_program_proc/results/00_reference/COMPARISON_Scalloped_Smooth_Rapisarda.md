# Validation Comparison: Scalloped vs Smooth vs IRVE-3 vs LOFTID

- Scalloped CSV: `results/validation_scalloped/validation_timeseries.csv`  — **AVAILABLE**
- Smooth CSV:    `results/validation_smooth/validation_timeseries.csv`  — **AVAILABLE**
- Reference: Rapisarda (2023) IRVE-3 baseline, Table 4.10 / NASA TP-2013-4012; LOFTID: Deshmukh et al. AIAA-2024-1501 / Hollis et al. AIAA-2024-1498

## Peak Aerothermodynamic Metrics

| Metric | Scalloped | Smooth | IRVE-3 Ref | LOFTID Ref | Scalloped/Smooth |
|---|---|---|---|---|---|
| Peak Drag Force (N) | 62,469.8 | 57,468.1 | — | — | 1.087 |
| Peak |Lift| Force (N) | 17,262.8 | 16,595.4 | — | — | 1.040 |
| Peak Heat Flux (W/cm^2, literal col /1e4) | 458.32 | 424.91 | 14.36 | 39.27 | 1.079 |
| Peak Deceleration (g) | 22.67 | 20.85 | 19.7 | 9.66 | 1.087 |
| Peak Total Heat Rate (W, heat_sum col) | 1.107e+08 | 1.097e+08 | — | — | 1.010 |
| Vehicle Diameter (m) | 3.0 | 3.0 | 3.0 | 6.0 | — |

## Reference Targets

### IRVE-3 (Rapisarda 2023 / NASA TP-2013-4012)
- Peak heat flux  q_max = **14.36 W/cm^2** (143,600 W/m^2)
- Total heat load Q     = **195.06 J/cm^2** (1,950,600 J/m^2)
- Peak deceleration     = **19.7 g** (flight) / 20.2 g (MDAO)
- Ballistic coeff  beta = **26.9 kg/m^2**
- Diameter              = **3.0 m**
- Decel conversion: decel_g = drag_sum_N / 2755.67 (m=281.0 kg)

### LOFTID (Deshmukh et al. AIAA-2024-1501 / Hollis et al. AIAA-2024-1498)
- Peak heat flux  q_max = **39.27 W/cm^2** (2.7x IRVE-3)
- Total heat load Q     = **3.52 kJ/cm^2** (~18x IRVE-3)
- Peak deceleration     = **9.66 g** (0.49x IRVE-3)
- Diameter              = **6.0 m** (2x IRVE-3)
- Entry velocity        = **~8.0 km/s** (LEO, vs IRVE-3 ~3.5–4.5 km/s suborbital)

## Notes & Data-Quality Flags

- **Heat-flux magnitude check:** Smooth peak heat flux = 424.9 W/cm^2 (literal `heatflux_max_Wm2`/1e4). Rapisarda reference = 14.36 W/cm^2. Ratio = 29.6x.
  - ⚠ LARGE DISCREPANCY. The `heatflux_max_Wm2` column is labeled W/m^2 but its magnitude is much higher than IRVE-3 flight peak. Two possibilities:
    1. The column is actually **total heat power (W)**, not per-area flux; dividing by the vehicle reference area (~7.07 m^2 for 3 m diameter IRVE-3) normalizes it to physically plausible W/cm^2 values.
    2. There is a unit/scaling bug in the heat-flux reporting. RECOMMEND verifying the column semantics (per-area vs total) before trusting absolute heat-flux numbers.
- **Deceleration check:** Smooth peak decel = 20.9 g vs Rapisarda 19.7 g (+6% relative). Drag-based deceleration is in the right ballpark.
- Corrugation effect on drag: Scalloped is +8.7% vs Smooth.
- Corrugation effect on heat flux: Scalloped is +7.9% vs Smooth.
- Corrugation effect on deceleration: Scalloped is +8.7% vs Smooth.
- Corrugation effect on lift: Scalloped is +4.0% vs Smooth.

## Storage Locations

- Scalloped surf : `stellarorion_program_proc/results/validation_scalloped/HIAD_custom.surf`
- Scalloped CSV  : `stellarorion_program_proc/results/validation_scalloped/validation_timeseries.csv`
- Smooth surf   : `stellarorion_program_proc/results/validation_smooth/HIAD_custom.surf`
- Smooth CSV    : `stellarorion_program_proc/results/validation_smooth/validation_timeseries.csv`
- This report    : `stellarorion_program_proc/results/validation_scalloped/COMPARISON_Scalloped_Smooth_Rapisarda.md`
