# Layer-by-Layer TPS Heat-Flux Composition — Task List

Submission-ready task list for a simulation-builder agent.
Derived from a measured gap analysis of the IRVE-3 F-TPS conduction stack.

- **Repo root:** `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition`
- **Package under change:** `stellarorion_program_proc/` (referred to as `_proc`)
- **Date written:** 2026-10-07
- **Status:** plan only; nothing below is implemented yet.

## Standing rules for the agent

1. Every claim verified by running a tool, never inferred.
2. Every number traceable to a named source file.
3. No tolerance limit, physical constant, or reference set moved to manufacture a pass.
4. Anything that changes a published number is reported and approved, never silently applied.
5. Defects are filed in `FAILURES_AND_FIXES.md` (currently runs to **F83**; next free is **F84**).
6. Judge a LaTeX build from `main.log`, never the exit status. The verdict must include the
   pattern `^\./main\.tex:[0-9]+:` because `pdflatex -file-line-error` emits real errors as
   `./main.tex:NN: ...` which do NOT begin with `!`.

---

## PHASE 0 — Reconcile the three contradictory conduction statements

> **BLOCKING.** Every later phase depends on this. This phase changes published numbers, so
> each task that alters a reported temperature or flux must be recorded as an F-entry and
> approved before merge.

### T0.1 — Settle the authoritative conduction model

Three values disagree for the same physical quantity at the peak element:

| # | Where | Formula | Value | Material model |
| :-- | :-- | :-- | --: | :-- |
| A | Ada `TPS_Conduction` (`src/simulation_engine/stellarorion_physics.ads:1018`) | `q = (T_s − T_b)/Σ(δᵢ/kᵢ)` | **0.4883 W/cm²** | 5-ply F-TPS series resistance (correct) |
| B | `src/python/generate_outputs.py:297` | `q_cond = q_conv − q_rad` | **exactly 0.0** | none — degenerate |
| C | `src/python/validation_pipeline.py:4294` | `q = k_tps·ΔT/L` | SiC lumped | SiC at `k_tps = 120.0` (`:4272`), `thickness_tps = 0.005` (`:4275`) — wrong material |

**Deliverable:** one written decision naming the authoritative model and why, citing the physics,
and explicitly marking the other two as superseded.
**Acceptance:** one model; the other two named as superseded; no code path left ambiguous.

### T0.2 — Close the surface energy balance

The balance `q_conv = q_rad + q_cond` is not closed. Ada sets `T_surface` from `εσT_s⁴ = q_conv`
(which forces `q_rad = q_conv`, hence `q_cond = 0`) and *then* computes a profile with `T_back`
pinned (which forces `q_cond = 0.4883 W/cm²`). Both cannot hold simultaneously.

Solve jointly:

```
q_conv = εσT_s⁴ + (T_s − T_back) / R_total
```

Nonlinear in `T_s`. Use **bisection**, consistent with `TPS_Conduction`'s existing bisection
solver (documented reason: Newton needs a derivative).

**Deliverable:** one solve producing both `T_surface` and `q_cond` from the same equation.
**Acceptance:** energy-balance residual < 1 % at every element.

### T0.3 — Fix the degenerate `q_cond` in `generate_outputs.py`

`src/python/generate_outputs.py:293` sets `q_rad_wm2 = sg["heat_flux_Wm2"]`, so `:297`
`q_cond_wcm2 = max(0.0, sg["heat_flux_Wcm2"] − q_rad_wm2/10000.0)` evaluates to `max(0, X − X)`
= **0.0 for every element**. The in-file comment `ONE TRUTH, ONE VALUE (2026-10-06)` shows this is
deliberate, not a typo. The zero is shipped at `:348` (`"heat_flux_cond_wcm2"`).

**Acceptance:** `q_cond` is non-zero and equals the T0.2 value.

### T0.4 — Fix the wrong material in `validation_pipeline.py`

`src/python/validation_pipeline.py:4272` `k_tps = 120.0  # SIC at 1000K` and `:4275`
`thickness_tps = 0.005  # (5mm)`. The vehicle flies a 6.35 mm five-ply Nextel/Pyrogel/AKK stack
(effective k ≈ 0.025), not SiC. A second path uses the same constants: `:4291`
`T_backwall = T_surface − (q_conv * thickness_tps / k_tps)`, consumed at `:4312`, `:4333`,
`:4348`, `:4599` (`"conduction_heat_flux_Wm2"`), `:4615`.

**Acceptance:** uses the layup's own `R_total`; no hard-coded single material.

### T0.5 — Reconcile the emissivity constant

`generate_outputs.py` uses `_emissivity = 0.85`; Ada `TPS_Layup_IRVE3` uses `0.80`.

**Acceptance:** one value, cited; the other removed.

---

## PHASE 1 — Export the per-ply breakdown (depends on Phase 0)

### T1.1 — Compute per-ply quantities per element

The inputs are **already exported** in `results/tps_conduction/tps_step2200_summary.json` →
`layup.ply_thickness_m` and `layup.ply_thermal_k` (and in `ada_pinn_wrapper.py:1320-1321`), so this
is Python-only; no new FFI is strictly required.

Compute `R_i = δ_i/k_i`, `share_i = R_i/R_total`, `ΔT_i = q_cond·R_i`, and `T_in`/`T_out` per ply.

**Acceptance:** `ΣR_i == Layup_Resistance` and `ΣΔT_i == T_surface − T_back` to 1e-6.

### T1.2 — Emit `results/tps_conduction/tps_step2200_layers.csv`

Columns: `element, ply, delta_m, k, R_i, R_share, dT_K, T_in_K, T_out_K`.

**Acceptance:** 3648 elements × 5 plies = 18240 rows; per-element sums close.

### T1.3 — (optional, cleaner) Add FFI bindings

`Layer_Resistance`, `Layup_Resistance` and `Layup_Thickness` exist in Ada
(`src/simulation_engine/stellarorion_types.ads`) but are referenced only in comments in
`stellarorion_ffi.adb` / `.ads`. `TPS_Conduction_Profile` is called at `stellarorion_ffi.adb:1004`
inside the `TPS_Conduction_C` wrapper but has no standalone C binding.

**Acceptance:** if added, the Python values equal the Ada values exactly (no re-derivation drift).

---

## PHASE 2 — Per-ply limit checking (depends on Phase 1)

### T2.1 — One limits table in code

Limits currently exist only as prose or scattered constants:

| Ply | Limit | Currently at |
| :-- | :-- | :-- |
| Nextel BF-20 | 30.0 W/cm² (flux) | `scripts/run_tps_conduction_step2200.py:87` (`NEXTEL_BF20_RATING_WCM2`) |
| Kapton gas barrier | 773 K | `stellarorion_types.ads:124` (`KAPTON_MAX_TEMP`); `uiassets/main.ts:313` |
| Structural / bondline | 523.15 K | `stellarorion_types.ads` (`IRVE3_FTPS_STRUCT_LIMIT_K`) |
| Pyrogel 2250 | **1000 K vs 1373 K — CONFLICT** | thesis `chapter_03_methodology.tex:455` vs `uiassets/main.ts:312` |

**Acceptance:** a single table; no duplicated literal.

### T2.2 — Resolve the Pyrogel conflict

1000 K (thesis `chapter_03_methodology.tex:455`) vs 1373 K (`src/ui/uiassets/main.ts:312`).
Determine the correct rating and fix the other site.

**Acceptance:** documented decision; both sites agree.

### T2.3 — Per-element exceedance flags

Flag each element whose any ply exceeds **that ply's** limit.

**Acceptance:** the flag names the ply and the limit. Expected to fire: the model implies ply 3
spans 1526.8 → 916.5 K against a 1000 K Pyrogel rating — confirm or refute against the T0.2 solve.

---

## PHASE 3 — Interface-aligned profile and figure (depends on Phase 1)

### T3.1 — Sample the profile at ply boundaries

The exported profile is a uniform 33-point grid (`Max_Profile_Points := 33`,
`stellarorion_physics.ads:883`) whose spacing (0.198 mm) does **not** land on the
0.60 / 1.20 / 3.70 / 6.20 mm interfaces.

**Acceptance:** interface temperatures present and equal to the T1.1 `T_in`/`T_out`.

### T3.2 — Layer-by-layer figure

Stacked temperature profile with ply bands plus per-ply ΔT bars; ITB house style.

**Acceptance:** figure values match the CSV to 1e-6; visual read-back before delivery.

---

## PHASE 4 — Deck frame (depends on Phase 3)

### T4.1 — Add the frame

Add `4c. LAYER-BY-LAYER HEAT FLUX COMPOSITION` to
`Lost+Found/ProgressReport/Week 16 LaTeX/main.tex` using the existing
`\PlotFrame{title}{caption, 1-2 lines}{image}` macro. The caption must cite its source file; the
1-2 line budget is enforced by `\MaxTextLines`.

**Acceptance:** 14-page clean build; log verdict includes `^\./main\.tex:[0-9]+:`; 0 pages
"MISSING PLOT"; figure read back visually.

---

## PHASE 5 — Verification and record

- **T5.1** Energy-balance residual < 1 % at every element, shipped as a check.
- **T5.2** Interface temperatures cross-checked between CSV, profile and figure.
- **T5.3** File every genuine defect found as **F84+** in `FAILURES_AND_FIXES.md` (runs to F83),
  with `## F84 — …` + `*Class: …*` + Evidence / Fix / Reproducer, and a `| F84 | … |` Summary row.
- **T5.4** Fix the dashboard's "Composite Material Inset" (`generate_outputs.py:779-795`) which
  draws **3** layers where the model has **5**.

---

## Prerequisites the agent cannot decide alone

1. **Phase 0.1 physics decision.** Which conduction model is authoritative. T0.2 proposes the
   closed-balance solve, but it *lowers* the reported `T_surface` from 1550.2 K, so it changes
   published numbers and needs sign-off.
2. **Steady vs transient.** In steady 1-D the flux is *identical* through every ply, so
   "per-layer flux" is really per-layer **ΔT / resistance share**. A genuinely per-layer **flux**
   needs the transient storage term `ρᵢc_{p,i}δᵢ·dT/dt`. Which does the agent build?

---

## Reference — the current per-ply breakdown (computed, indicative only)

Inputs: `δ = [0.6, 0.6, 2.5, 2.5, 0.15] mm`, `k = [0.25, 0.25, 0.02, 0.02, 0.12] W/m·K`,
`T_s = 1550.2345 K`, `T_b = 300.0 K` (Dirichlet-pinned to `T_init`).

| Ply | δ (mm) | k | Rᵢ (m²K/W) | share | ΔTᵢ (K) | T in → out (K) |
| :-- | --: | --: | --: | --: | --: | :-- |
| 1 Nextel BF-20 | 0.60 | 0.25 | 0.002400 | 0.94 % | 11.72 | 1550.2 → 1538.5 |
| 2 Nextel BF-20 | 0.60 | 0.25 | 0.002400 | 0.94 % | 11.72 | 1538.5 → 1526.8 |
| 3 Pyrogel 2250 | 2.50 | 0.02 | 0.125000 | 48.82 % | 610.35 | 1526.8 → 916.5 |
| 4 Pyrogel 2250 | 2.50 | 0.02 | 0.125000 | 48.82 % | 610.35 | 916.5 → 306.1 |
| 5 AKK gas barrier | 0.15 | 0.12 | 0.001250 | 0.49 % | 6.10 | 306.1 → 300.0 |

`R_total = 0.256050 m²K/W`; `q_cond = 4882.77 W/m² = 0.488277 W/cm²`; `ΣΔT = 1250.23 K`
(= `T_s − T_b`, closes exactly); ratio `q_SG / q_cond = 54.6×`.

Two consequences no code currently states:

1. The two Pyrogel plies carry **97.6 %** of the total resistance; the Nextel and AKK plies are
   structurally incidental to the gradient.
2. Ply 3 spans 1526.8 → 916.5 K against a 1000 K Pyrogel rating, so the outer ~80 % of that ply is
   above its material rating and nothing flags it.

**Caveat that must travel with any use of these numbers:** `T_back` is Dirichlet-pinned to
`T_init = 300 K`, which the driver itself says "restates the boundary condition rather than
predicting a transient back-face temperature." So `q_cond` is *implied by the pin*, not predicted.
These values are indicative, not validated transient physics.
