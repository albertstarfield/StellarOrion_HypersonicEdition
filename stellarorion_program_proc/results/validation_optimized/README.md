# results/validation_optimized — DSMC+PINN_AUX validation of the optimised topology

**Run window:** 2026-10-20 22:02 → 2026-10-21 00:01 (local time, 7155 s = 1 h 59 m wall).

**Geometry:** the committed GA optimum — nose radius `R_N = 1.039670 m`,
torus radius `r_tor = 0.219741 m`, half-cone `53.724700 deg`, skin `scalloped`.
Body maximum radius `R_Max = 3.007547 m` (the reference geometry's is
`3.000000 m`): **the same body size with a much blunter nose.**

**Command**

```sh
bin/main --validate --headless \
  --nose 1.039670 --tradius 0.219741 --angle 53.724700 --skin scalloped \
  --steps 2200 --results-dir results/validation_optimized
```

The in-process PINN_AUX leg (Step 13) then ran on the produced time series
(`--target-step 300000000 --iterations 4000`) and produced the comparison
tables and plots under `validation_pipeline_output/`.

## Artefact provenance

| Artefact | Origin |
|:---|:---|
| `validation_timeseries.csv` | **THIS RUN** — DSMC, 2200 steps, 22 recorded steps (100 … 2200) |
| `trajectory_profile.csv` | **THIS RUN** |
| `in.hiad`, `HIAD_custom.surf` | **THIS RUN** — SPARTA input deck and surface export |
| `validation_pipeline_output/unified_comparison_data.json` | **THIS RUN** — PINN_AUX leg |
| `validation_pipeline_output/unified_comparison_table.{csv,md}` | **THIS RUN** — PINN_AUX leg |
| `validation_pipeline_output/convergence_audit.csv` | **THIS RUN** — PINN_AUX leg |
| `validation_pipeline_output/pinn_trajectory_per_step.csv` | **THIS RUN** — PINN_AUX leg |
| `validation_pipeline_output/pipeline_results.json` | **THIS RUN** — PINN_AUX leg |
| `validation_pipeline_output/dsmc_pinn_switch_section.md` | **THIS RUN** — PINN_AUX leg |
| `validation_pipeline_output/plots/` (10 files) | **THIS RUN** — includes `hybrid_dsmc_pinn_animation.mp4` |
| `validation_pipeline_output/interactive/` (5 files) | **THIS RUN** |
| `paraview/` | **MIXED** — `surf_*.vtu` and `surf_pinn_300000000.vtu` rewritten by this run; the older `surf_*.vtu` entries predate it |
| `plots/` (21 files) | **STALE** — timestamped 2026-10-18 18:00, i.e. the earlier `03_opt_geometry` run. **Not** from this run; regenerate before citing |

## Headline result (see `DSMC_PINN_AUX_vs_reference.md` for the full table)

| Quantity | Reference (R_N 1.5) | Optimised (R_N 1.03967) | Delta |
|:---|---:|---:|---:|
| Total heat load [J/cm^2] | 165.716 | **120.824** | −27.1 % |
| Final peak heat flux [W/cm^2] | 192.02 | 139.40 | −27.4 % |
| Fay–Riddell heat flux [W/cm^2] | 161.55 | 117.50 | −27.3 % |
| Drag force [N] | 45 613 | 108 248 | **+137.3 %** |
| Drag coefficient (reference-area normalised, `cd_raw`) | 1.7655 | **8.7214** | +394 % |
| Drag coefficient (body-area normalised, `cd_body`) | 0.4414 | **1.0422** | +136 % |
| Peak deceleration load [g] | 22.72 | 54.16 | **+138.4 %** |

**Validation gate: PASS** — the DSMC+PINN_AUX heat load (120.82 J/cm^2) is
below the 165.716 J/cm^2 target.

## Two findings that must not be lost

1. **The recorded drag coefficient is clamped, not measured.**
   `src/simulation_engine/stellarorion_sparta.adb:3348` clamps `cd` to
   `[0, 3]` (`if FB_CD > 3.0 then FB_CD := 3.0;`). The blunt optimised geometry
   saturates that clamp, so the CSV reports a flat `3.000000` at every step
   while the raw force ratio is 8.67 … 12.02. Any figure, table or
   convergence audit that reads the `cd` column of this run (including
   `validation_pipeline_output/convergence_audit.csv`, which therefore reports
   a 104 % "error" against the MDAO reference) is reading a saturated number.
   Use `scripts/compare_dsmc_runs.py`, which reconstructs the value from the
   raw drag force and states the saturation explicitly.

2. **The analytic screening objective is mis-calibrated for this geometry.**
   The Ada screening model predicted a heat load of 250.45 J/cm^2 and a drag
   coefficient of 1.6677 for the optimum; the DSMC+PINN_AUX run measured
   120.82 J/cm^2 (ratio 0.48 — the analytic model is 2.07× pessimistic on the
   heat load) and 8.72 (ratio 5.2× — the analytic model under-predicts the
   drag by a factor of five on a blunt body of the same maximum radius). The
   optimiser therefore optimised against a cost function whose two dominant
   terms are wrong in opposite directions for this topology. The
   "heat load rises by 20 %" trade-off predicted by the analytic sweep does
   **not** occur in the DSMC: the real heat load falls by 27 %.
