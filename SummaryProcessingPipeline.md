# Optimization Processing Pipeline

This document maps the StellarOrion HIAD geometry-optimization pipeline end to end: what
runs, in what order, which language owns each decision, and where every number in the
pipeline is defined in the source.

**Entry point:** `stellarorion_program_proc/src/python/hiad_optimizer.py`
**Physics/geometry/cost:** Ada/SPARK, reached only through the C ABI in
`stellarorion_ffi.ads` (`HIAD_Cost_C`, `HIAD_Cost_Components_C`).
**Run it:** `cd stellarorion_program_proc && python3 src/python/hiad_optimizer.py`

> Python's role is strictly orchestration: CLI, FFI marshalling, the Bayesian-optimization
> surrogate (scikit-learn), JSON output, and the post-run render. Every geometry formula,
> cost term, and penalty is evaluated in Ada.

> ### ⚠️ Read `FAILURES_AND_FIXES.md` F16–F52 before trusting any number below
>
> Independent audits of `_proc` on 2026-10-05 left **thirty-five findings open**: F16–F22
> from the DSMC/report-path pass, F24–F31 from a rescan of the PINN, checkpoint and status
> subsystems, F32–F36 from a pass over the Kriging, comparison and watchdog
> paths, and F37–F44 from a sweep of the atmosphere generator, the reporting scripts and
> the HTTP sidecar. F23 is a
> method finding already actioned.
>
> | ID | What it invalidates in this document |
> | :--- | :--- |
> | **F16** | `results/validation_smooth` (Sep 28) and `results/validation_optimized` (Sep 26) are **pre-F11 artefacts** — their `g_load` column is a single constant. Only `validation_scalloped` (Oct 5) carries the fix. |
> | **F17** | `cd` is clamped to 3.0 inline in `stellarorion_sparta.adb:3143` with no flag. **9 of 22 rows (41 %) of the optimized Cd series are pinned at `3.000000`**; the raw step-100 value was 4.15411. Any "Cd convergence" read off that series is partly an artefact. |
> | **F18** | The `51.8 km / 3378 m/s` "fixed flight condition" below is **not** the validated DSMC run's condition (`52.0326 km / 3094.2 m/s`). See the warning at the constants table. |
> | **F19** | `q_ref = 14.3610 W/cm²` is a **Rapisarda** value presented as IRVE-3 flight in two places below. IRVE-3 flight (NASA TP-2013-4012) is **13.80**. |
> | **F20** | `Decel_G` is reported as a tail mean of the last 15 dumps (17.09 g). The same run's `g_load` **peaks at 22.67 g (+15.07 % vs flight)**. `stellarorion_test_modes.adb:1196`'s `17.7276 g` "MEASURED" figure — the stated reason the decel band was widened 10 %→15 % — matches **no** estimator of the data. |
> | **F21** | The TPS-conduction leg normalises every element by a Sutton-Graves flux computed at the **CLI default** `51.8 km / 3378 m/s`, while the shape comes from a snapshot flown at `52.0326 km / 3094.2 m/s`. **Peak 26.65 W/cm² is really 20.21 W/cm² — a 31.90 % overstatement.** The default snapshot is the F16 stale artefact, and the limits gate validates a *third* load again (`Rn` 1.5 vs the run's 0.55, so `T_s` is understated by 182 K). |
> | **F22** | **This document's optimisation section is affected.** `J(x)` is graded against StellarOrion's **own** DSMC heat load (174.13736) and **own** measured `Cd` (1.75791) — a regression baseline, not validation. The Ada `Validation_Refs` V1 defaults are **5.08 % / 20.21 %** stale and are silently used by any FFI caller that omits `Set_Validation_Refs`. `Flux_Ref = 14.361` here is the value the JSON files under `irve3_flight`, which matches neither NASA (F, 13.80) nor the file's own `rapisarda_models.Sutton-Graves` (15.2595). |
> | **F24** | **The "PINN 5–30 min" leg below has never run.** `PINNAccelerator.train_from_checkpoint` calls `dde.icbc.IC(xy_norm, …)` where deepxde 1.15.0 requires a geometry, and raises `AttributeError: 'numpy.ndarray' object has no attribute 'on_initial'` **before the first iteration**. |
> | **F25** | Even if F24 were fixed, the PINN would be wrong: the DSMC targets parsed at `pinn_accelerator.py:627` are normalised into `_t_norm` at line 631 and **never read**, and `_ic_zero_values` returns `np.zeros(...)` — so every one of the 17 949 collocation points is supervised to output **0.0**. The 4-residual PDE and 9 boundary conditions exist only in self-tests. |
> | **F26** | The SPARTA grid parser averages `xlo` with `ylo` and `xhi` with `yhi` (a `[BUGFIX]` comment certifies the wrong field mapping), putting **4 093 of 17 949 cells (22.80 %)** at negative radial coordinate; max \|coordinate error\| **4.486 m**. The `T` column is unaffected. *(The 7.22 m error and "1 372 rows (7.10 %) dropped" figures were withdrawn in thread 3c — row-alignment artefact and empty cells, not losses.)* |
> | **F27** | `pinn_test.py:compute_pinn_metrics` reads column 4 of a 4-column result → guaranteed `IndexError`. Where it does not crash, the PINN reaches the reported physics only as `clip(ratio, 0.5, 2.0)` on two scalars, and `"Shock Temperature"` hardcodes both its reference and its error to `0.0`. |
> | **F28** | `stellarorion_test_modes.adb:728` writes `Write_Status(..., Status_Completed, 1.0)` **outside** the `if Success` block, and `GNAT.OS_Lib.Spawn`'s `Success` means "process created", not "exited 0" — so the calibration that provably always fails is recorded as **100 % complete**. 7 of the 8 `Write_Status` sites in that file share the flaw. |
> | **F29** | `pinn_test.py:28-51` `IRVE3_BASELINE` is a **fourth** copy of the F22 mis-provenanced 14.361 / 195.06 / 20.2 / 1.47 set, and feeds the "document" column of the three-way comparison. |
> | **F30** | The PINN sidecar's `.gpr` probe checks the repo root, always fails, and then `os.makedirs` **creates a wrong directory** rather than reporting the missing input — so the real grids at `results/validation/grid.*.out` are never found and the sidecar exits 1 on "No grid output files found". |
> | **F31** | `PipelineCheckpoint` — the mechanism behind the `sparta → kriging → pinn → mop` step sequence below — **discards a changed `config` on resume** and never checks that recorded `output_files` exist. Measured: resuming with a different `grid_file` still reports `sparta` complete and keeps the previous run's config. A corrupt checkpoint silently restarts the whole pipeline. |
> | **F32** | **The Kriging leg in the diagram above runs `kriging_denoise._parse_grid_file`, which carries the F26 axis-mixing bug byte-for-byte.** Both parsers return identical output, so an F26-only fix leaves the live path wrong. |
> | **F33** | Kriging's write→read round trip replaces **100 %** of cell densities with a hardcoded `1e20` default. Any second pass over the Kriging output reads a **constant** density field. |
> | **F34** | The `Surf → (x,y) cell centroid` step leaves **7 of 3 648 cells (0.19 %)** at the `(0,0)` origin sentinel, because the "point cloud fallback" the code announces is never implemented. |
> | **F35** | The "PINN Surrogate" arrow in the diagram is a `GaussianProcessRegressor` with **no PDE residual**, labelled PINN in nine places. A GP cannot encode the governing equations, so the surrogate is an interpolator, not a physics-informed model. |
> | **F36** | Any claim of a self-healing sidecar. `Secondary_Watchdog`'s timeout is reset by the very loop that tests it, so the primary is never declared dead and no resurrect ever fires. The watchdog is armed in name only. |
> | **F37** | Two modules counted in the visualisation inventory (`visualizer.py`, `sidecar_launcher.py`) contain no code at all. |
> | **F38** | **The atmosphere the trajectory is flown through is 1.48×–3.32× too dense from 5 to 84.852 km**, worst **+231.5 % at 47–51 km** — the exact band the runs are evaluated in. Every q, Mach and g-load in this document inherits it. |
> | **F39** | `postprocess_validation.py` sorts `surf.*.out` lexicographically, so its "final step" is step 900 when the real last step is 1700. |
> | **F40** | `verify_profile_math.py` returns **success** when the Ada FFI it exists to cross-check is unavailable. A green verifier run proves nothing. |
> | **F41** | The 14.36 / 195.06 mis-provenance appears in three more files, and one report prints an unconditional "in the right ballpark" verdict. |
> | **F42** | `pct_of_peak` is a hardcoded 100.0 on every row, and the heat-load integration hardcodes `dt = 1e-6 s` — ~3 300× below the reference, printed without warning. |
> | **F43** | **The `trajectory_profile.csv` in every run directory cannot be regenerated by the committed generator** (198 rows / 17.4213 g shipped vs 186 rows / 19.4773 g regenerated; `downrange_km` constant vs 186 distinct). The producer is not in the repository. |
> | **F44** | **The HTTP sidecar serving the dashboard has no auth and no origin check** — arbitrary file read over loopback and cross-origin forgery of the displayed validation state, with no server-side log. |
> | **F45** | **The atmosphere used for every q, drag, heating and `g_load` in this document is wrong by 1.5–3.3×.** Two ISA atmospheres ship here; the Ada/SPARK one is correct to 0.36 % and is live, the Python one that writes `trajectory_profile.csv` is 1.48–3.32× too dense. Temperature agrees exactly, so the error is invisible in the T column. |
> | **F46** | Any claim resting on run history, trajectory output or checkpointing rests on **5 459 lines of Ada with no caller**. There is no Ada-side run checkpoint, so nothing would ever contradict a wrong completion status. |
> | **F47** | The `gnatprove --level=4` claim does not cover the packages that matter most. `SPARK_Mode (Off)` in all five Ada bodies excludes them from proof, so every `Pre`/`Post` in those specs is unverified. |
> | **F48** | The atmosphere is implemented **three** times and the three disagree. The `alt_km` / `mach` / `dyn_press_pa` columns every stage above consumes are written by the Python model, which is **1.48–3.32× too dense**; the exported Ada model is correct to 0.36 %. |
> | **F49** | Any claim that the runtime guard — the process lock, the GPU probe, the container probe — is tested. Its seven `Test_*` wrappers assert on a hardcoded local literal and never call the routine they name, so the package contributes **0 real assertions**. |
> | **F50** | Any claim that the project's own rule set is satisfied. `sabotage_verifier.py` (917 KB) excludes `src/utils/` — itself — from every scan, and had never been run when this audit began. |
> | **F51** | Any claim that formal verification is "unsound because cvc5 is missing". cvc5 **1.0.9 is installed and working on PATH**; the gate probes the pip module, not the binary, in the same function that uses `shutil.which` for alt-ergo. |
> | **F52** | Any reading of a `TAINTED` verdict as a statement about the code. 2 of the 3 CRITICALs are a jupyter extension inside `venv_validation/`, which the walker does not prune. |
> | **F32** | The F26 axis-mixing parser is **duplicated byte-for-byte** at `kriging_denoise.py:103-104` — the module this document's Kriging stage actually runs. Both parsers return byte-identical output, so fixing F26 alone leaves the live path wrong. |
> | **F33** | The `kriging` stage's own write→read round trip replaces **100.00 % (17 949/17 949) of cell densities** with a hardcoded `1e20` default (writer emits 10 fields, reader needs `parts[10]`, real format has 11). Input `rho` spans `4.05e-05 … 4.63e-02 kg/m³`; output is the constant `4.810694e-06 kg/m³` (≈144× too small). Any multi-pass run reads a **constant** density field from pass 2 onward. The writer also reorders the axes relative to real SPARTA and omits `f_2[1]`. |

---

## 1. Pipeline at a glance

```
                    python3 src/python/hiad_optimizer.py
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        │  PHASE A — SELF-TESTS (always runs first, seconds)   │
        │  CCD 15 pts · validation refs · J(x_default)          │
        │  cost components · Cd · MoP 20 iters · BO 15 evals    │
        │  gate verdict PASS/edge/FAIL + error path + clamp     │
        └───────────────────────────┬───────────────────────────┘
                                    │  all must be OK
                                    ▼
   ╔═══════════════════════════════════════════════════════════════════╗
   ║  PHASE B — MAIN RUN        steps [0/7] … [7/7]                    ║
   ╚═══════════════════════════════════════════════════════════════════╝

 [0/7] Load validation references            ← dynamic, at run time
       Q_target 174.1374 J/cm²   (StellarOrion's OWN DSMC load — self-referential, see F22)
       q_ref      14.3610 W/cm²   (Rapisarda Tab. 4.10 — NOT IRVE-3 flight, see F19)
       q_flight    13.8000 W/cm²   (IRVE-3 flight, NASA TP-2013-4012)
       tau        13.5825 s       (= 195.0577/14.361 — the mis-filed irve3_flight
                                       pair, NOT 188.00/13.80 = 13.6232; see F22(a))
       Cd_ref      1.75791         (StellarOrion's OWN measured Cd — self-referential,
                                       Ada V1 default 1.462536 is 20.21 % stale; F22(b/c))
                              │
 [1/7] Load default HIAD geometry ──────────► Ada FFI  (57 cross-section pts)
       X [0.0002, 1.7444] m · Y [0.0000, 2.6522] m
                              │
 [2/7] Default parameters + cost ───────────► Ada FFI
       R_N 1.5 m · r_tor 0.135 m · cone 60° · Cd 1.607278 · J 2.162602
                              │
 [3/7] CCD sample points ───────────────────► Ada FFI
       15 pts = 8 factorial (2³) + 1 center + 6 axial
                              │
 [4/7] Evaluate J at those 15 ──────────────► Ada FFI  (15 calls)
       best CCD: factorial+-- J=1.995939
                              │
 [5/7] BAYESIAN OPTIMIZATION  ──────────────► Ada FFI (55 calls)
       ┌────────────────────────────────────────────────────────┐
       │  20 × Latin Hypercube      seed 42                     │
       │        ↓ evaluate J                                      │
       │  GP surrogate  = Matern(ν=5/2) × ConstantKernel         │
       │        ↓ fit                                             │
       │  50 × Expected Improvement,  xi = 0.01                  │
       │        ↓ pick x, evaluate J, refit                      │
       │  = 70 evaluations total                                 │
       └────────────────────────────────────────────────────────┘
       result: J 1.602195 · R_N 2.991054 · r_tor 0.074938 · cone 40.354047
                              │
 [6/7] Write hiad_optimization_results.json   (+ hiad_geometry_grid.png)
 [7/7] Render 87/88-panel 3D geometry grid
        (1 default + 15 CCD + 70 history + 1 R1 optimum + 0 R2)
```

```
   ╔═══════════════════════════════════════════════════════════════════╗
   ║  PHASE C — HYBRID VALIDATION GATE     --hybrid-validate           ║
   ║  (the multi-hour scale: DSMC ~2-3 h + PINN 5-30 min)              ║
   ╚═══════════════════════════════════════════════════════════════════╝

   winner geometry x*
          │
   ┌──────┴───────────────────────────────────────┐
   │ Stage 1/3  high-fidelity chain                │   ~2-3 h @2200 steps
   │   geometry QA → SPARTA DSMC → PINN            │   (--steps override)
   └──────┬───────────────────────────────────────┘   5-30 min PINN leg
          │
          ▼  q_hybrid   (fresh DSMC+PINN heat load)
   ┌────────────────────────────────────────────────────────────┐
   │ Stage 2/3  VERDICT:  PASS  ⟺  q_hybrid ≤ q_target           │
   │ correction c = clamp(q_hybrid / q_analytic, 0.5, 2.0)      │
   │           (multi-fidelity bias, Kennedy & O'Hagan 2000)    │
   └────────────────────────┬───────────────────────────────────┘
                            ▼
   Stage 3/3  ROUND-2 BO with corrected J
              same budget: 20 LHS + 50 EI, xi=0.01, seed 42
                            │
                            ▼
              hiad_optimization_results.json gains:
              "optimized_round2"  →  grid becomes 88 panels
              (optional --validate-round2: a 2nd DSMC run on x*_2)
```

> ⚠️ **The "PINN" in Stages 1/3 and 2/3 above is aspirational, not descriptive.** The
> `SPARTA DSMC → PINN` arrow does not currently fire: the trainer raises
> `AttributeError` before its first iteration (**F24**), the DSMC state it parses is
> discarded so the collocation points are supervised to output zero (**F25**), and the
> grid parser mis-places 22.80 % of cells across the axis of symmetry (**F26**). In
> practice the chain is **SPARTA DSMC → (PINN leg raises) → DSMC heat load**, and the
> verdict in Stage 2/3 is produced by the DSMC leg alone. That verdict is unaffected,
> because `q_hybrid` is a DSMC heat load — but the gate is "DSMC+PINN" in name only
> today, and the `clamp(…, 0.5, 2.0)` multi-fidelity correction has no PINN term to
> correct. See **F24–F27** and the ⁸/⁹ footnotes in `README.md`.

---

## 2. Phase A — self-tests

Run unconditionally before any optimization, so a broken toolchain fails in seconds
rather than after an hour of sampling. Covers the CCD generator, the validation-reference
loader, the default cost, the cost-component breakdown, `Estimate_Cd`, a 20-iteration MoP
run, a 15-evaluation BO run, and the gate's own verdict/clamp/error paths.

---

## 3. Phase B — the main run

Step markers are printed by `hiad_optimizer.py` at lines 1291, 1313, 1325, 1358, 1367,
1390, 1436, and 1530.

### 3.1 Step [0/7] — validation references (loaded, never hardcoded)

`J(x)` is only meaningful against a fixed reference set, and that set is read from
`unified_comparison_data.json` at run time (see `DERIVATION.md` §4):

| Symbol | Value | Meaning |
| :--- | --- | :--- |
| `Q_target` | 165.7160 (Ada V1 default) / **174.13736** (dynamic) | **Self-referential** — read from `comparison.stellarorion.raw_dsmc.total_heat_load_Jcm2`, StellarOrion's own DSMC heat load. The Ada default is **5.08 % stale**. See **F22(b)/(c)** |
| `Flux_Ref` (`q_ref`) | 14.3610 W/cm² | **Rapisarda** Table 4.10 — *not* IRVE-3 flight (which is 13.80). See `FAILURES_AND_FIXES.md` F12/F19 |
| `Tau_Sec` (`tau`) | 13.5825 s | Derived as `flight_q / flux_ref` — but both operands come from the mis-filed `irve3_flight` key (**195.0577 / 14.361**), not from the (F) pair. The genuine flight pair would give **188.00 / 13.80 = 13.6232 s**. See **F22(a)** |
| `Cd_Ref` | 1.462536 (Ada V1 default) / **1.75791** (dynamic) | **Self-referential** — read from `comparison.stellarorion.raw_dsmc.cd`, StellarOrion's own measured `Cd`, not a flight or literature value. The Ada default is **20.21 % stale**. See **F22(b)/(c)** |

**Consequence:** `J(x)` values are comparable only between runs that loaded the same
references. Changing the JSON changes the objective, and old `J` numbers stop being
comparable.

### 3.2 Steps [1/7]–[2/7] — default geometry and baseline cost

The default HIAD cross-section (57 points) and its cost come from Ada through the FFI.
The baseline for the 2026-10-04 run: `R_N = 1.5 m`, `r_tor = 0.135 m`,
`half_cone = 60°`, `C_d = 1.607278`, `J = 2.162602`, heat load 219.1041 J/cm².

### 3.3 Steps [3/7]–[4/7] — CCD sampling

`Generate_CCD_Samples` (`stellarorion_optimization.ads:554`) produces 15 points — an
8-point 2³ factorial, 1 centre point, and 6 axial points — giving local coverage before
the surrogate is fitted.

### 3.4 Step [5/7] — Bayesian optimization

`run_bayesian_optimize` (`ada_pinn_wrapper.py:836`):

| Parameter | Value | Note |
| :--- | :--- | :--- |
| `bounds` | `R_N` 0.5–3.0 m, `r_tor` 0.05–0.5 m, `half_cone` 40–80° | `_BOUNDS`, line 768 |
| `n_initial` | 20 | Latin Hypercube, `_latin_hypercube_sample` line 775 |
| `n_iter` | 50 | Expected Improvement |
| `xi` | 0.01 | exploration/exploitation trade-off |
| `seed` | 42 | reproducibility |
| **total** | **70 evaluations** | 20 LHD + 50 EI |

Surrogate: `GaussianProcessRegressor(Matern(ν=5/2) × ConstantKernel)` from scikit-learn.
Each iteration fits the GP to all observations, maximises Expected Improvement to pick the
next `x`, evaluates `J(x)` in Ada, and refits.

```
    20 × LHS  ──►  y = J(x) in Ada        (20 FFI calls)
                     │
                     ▼
              fit GP  Matern(ν=5/2) × Const
                     │
    ┌─── 50 × ────────┴──────────────────────────────────┐
    │  argmax_x  EI(x) = E[max(0, f_best − f(x) − xi)]   │
    │        │                                           │
    │        ▼                                           │
    │  y = J(x) in Ada        (1 FFI call)               │
    │        │                                           │
    └──► refit GP ───────────────────────────────────────┘
                     │
                     ▼
              x*, J*  +  full history (70 rows)
```

### 3.5 Steps [6/7]–[7/7] — output and render

Writes `src/python/hiad_optimization_results.json`, then renders the 3D geometry grid via
`scripts/render_geometry_grid.py`. Panel count is **87** for a round-1-only run
(1 default + 15 CCD + 70 history + 1 R1 optimum) and **88** once round 2 exists; the
renderer warns when it gets 87.

---

## 4. The objective function J(x)

All of this is Ada — `HIAD_Cost_Components` (`stellarorion_optimization.adb:1818`),
exported as `HIAD_Cost_Components_C`. Weights are constants at
`stellarorion_optimization.ads:358-362`.

```
        x = (R_N, r_tor, half_cone)
                         │
        ┌────────────────┴─────────────────┐
        │  Ada: Compute_Max_Radius → R_max │
        │  Ada: Compute_Frontal_Area → A   │
        └────────────────┬─────────────────┘
                         │
   Q̇ = Sutton_Graves_Heat( ρ(51.8 km), R_N, 3378 m/s ) / 1e4      [W/cm²]
                         │
        Q_load = Q̇ · tau          HL_R = Q_load / Q_target        w = 1.00 ◄ primary
                        Flux_R = Q̇ / q_ref                         w = 0.50
              β_R = (C_d,ref·A_ref)/(C_d(x)·A)   β_Dv = (β_R−1)²   w = 0.50
                                 C_d_R = C_d(x)/C_d_ref          w = 0.25
                         ┌───────────────────────────────────────┐
                         │  quadratic penalties (λ = 100)      │
                         │    R_max > 3.0 m      (envelope)     │
                         │    R_N < 1.0 m        (TPS coverage) │
                         │    R_N < 1.043 m      (payload fit)  │
                         └───────────────────────────────────────┘
                                    │
   J(x) = 1.00·HL_R + 0.50·Flux_R + 0.50·β_Dv + 0.25·C_d_R + Penalty      J ≥ 0
```

| Term | Weight | Constant | Meaning |
| :--- | ---: | :--- | :--- |
| `HL_R` | **1.00** | `W_Heat_Load`, line 358 | Heat load ÷ target — the **primary objective** |
| `Flux_R` | 0.50 | `W_Flux`, line 359 | Peak heat flux ÷ `q_ref` (**Rapisarda** 14.3610 — *not* IRVE-3 flight, F19) |
| `β_Dv` | 0.50 | `W_Beta`, line 360 | `(β_R − 1)²`, squared ballistic-coefficient deviation |
| `C_d_R` | 0.25 | `W_Cd`, line 361 | Drag coefficient ÷ reference |
| `Penalty` | λ = 100 | `Lambda_Pen`, line 362 | Quadratic; zero unless a constraint is violated |

Fixed flight condition: `Snapshot_Alt_Km = 51.8 km`, `Snapshot_Vel_Ms = 3378 m/s`
(lines 377–378).

> ⚠️ **This is NOT the condition of the validated DSMC run** (see `FAILURES_AND_FIXES.md`
> **F18**). Measured from `results/validation_scalloped/validation_timeseries.csv`, all 22
> rows sit at **h = 52.0326 km, V = 3094.193 m/s, Mach 9.4325**. The `51.8 / 3378` pair is
> the condition of `validation_smooth`. The two differ by **8.4 % in velocity and Mach**,
> so the optimizer is being driven at a different flight state than the run it is
> validated against. The same literal pair is also the default arguments
> `H_DSMC_Km` / `V_DSMC_Ms` in `stellarorion_pinn_trajectory.ads:191-192`, and appears as
> 31 hardcoded literals in `validation_pipeline.py` plus `hiad_optimizer.py:80-81` and
> `ada_pinn_wrapper.py:189-190`. Resolution: make `Flight.Altitude_Km` /
> `Flight.Velocity_Ms` the single source, delete the duplicates, and re-fly all three
> runs at one condition.

Penalty constraints:

| Constraint | Limit | Source | Rationale |
| :--- | :--- | :--- | :--- |
| `R_max ≤ 3.0 m` | envelope | `Max_Radius_Limit`, line 341 | IRVE-3 diameter limit |
| `R_N ≥ 1.0 m` | TPS coverage | `Nose_Radius_Limit`, line 342 | minimum nose coverage |
| `R_N ≥ 1.043 m` | payload fit | `Payload_Nose_Radius_Min` | `√(r_pay² + (h_pay/2)²) + standoff` = `√(0.275² + 0.85²) + 0.15` (`stellarorion_optimization.adb:1760`) |

`J(x) ≥ 0` by construction: every weight is positive and each ratio is non-negative. The
Ada body raises `Constraint_Error` if any denominator is non-positive or `Total < 0`,
rather than returning a silently corrupt cost.

**Why these weights matter.** `W_Heat_Load` exceeds every regulariser weight, so heat load
dominates the ordering of `J`. The penalty weight (100) only bites once a hard constraint
is actually violated. In the 2026-10-04 run this produced a 29.18% heat-load reduction
against a 3.46% C_d reduction — the objective behaving as documented.

---

## 5. Phase C — hybrid validation gate (`--hybrid-validate`)

Optional, and the only part that costs hours. It exists because Phase B optimises a *cheap
analytic surrogate*; the gate measures how wrong that surrogate is and feeds the error
back.

Constants: `_GATE_STEPS_DEFAULT = 2200` (line 255), `_GATE_SKIN = "scalloped"` (line 256),
`_GATE_PIPE_TIMEOUT_S = 90 × 60` (line 253), `_GATE_CORR_MIN = 0.5` / `_GATE_CORR_MAX = 2.0`
(lines 257–258).

| Stage | Action | Cost |
| :--- | :--- | :--- |
| 1/3 | `bin/main --validate-only` geometry QA → SPARTA DSMC re-simulation of `x*` → PINN pipeline | ~2–3 h + 5–30 min |
| 2/3 | Verdict + correction factor | seconds |
| 3/3 | Round-2 BO on the corrected objective | ~1 min |

> ⚠️ **Stage 1/3's "→ PINN pipeline" does not currently execute** — the trainer raises
> before its first iteration (**F24**), the parsed DSMC targets are discarded (**F25**),
> and the grid parser corrupts 22.80 % of cell positions (**F26**). Stage 2/3 therefore
> runs on the DSMC heat load alone, which is why the verdict still stands. See the
> warning after the Phase C diagram above and **F24–F31**.

**Verdict predicate** (`_gate_verdict`, line 705): `PASS ⟺ q_hybrid ≤ q_target`, with the
boundary counting as PASS (line 740).

**Correction factor:** `c = clamp(q_hybrid / q_analytic, 0.5, 2.0)` — a bounded
multiplicative fidelity correction. This is Kennedy & O'Hagan (2000), *Biometrika* 87(1)
1–13; the clamp stops one bad simulation leg from dragging the surrogate somewhere absurd.
Note that `c` is currently computed from DSMC-only quantities, so it is not yet a
multi-fidelity correction in the sense Kennedy & O'Hagan intend — the low-fidelity term it
is meant to reconcile against a PINN surrogate does not exist (**F24–F25**).

Round 2 reruns the identical budget — 20 LHS + 50 EI at `xi = 0.01`, seed 42 — against
`corrected_cost`, and its result is stored under `"optimized_round2"` in the results JSON.
`--validate-round2` additionally re-runs DSMC on the round-2 geometry (doubling simulation
time).

`--dry-run` performs the precondition checks and geometry-QA leg, prints the planned
DSMC/PINN commands, and stops — the safe way to inspect the gate without paying for it.

---

## 6. CLI reference

| Flag | Effect |
| :--- | :--- |
| *(none)* | Self-tests + full Phase B BO + grid render |
| `--hybrid-validate` | Run Phase C after BO; writes a pass/fail verdict, applies the correction, re-optimizes |
| `--dry-run` | With `--hybrid-validate`: check preconditions and print planned commands, then stop |
| `--allow-fail` | Exit 0 even when the gate verdict is FAIL (the verdict is still written) |
| `--validate-round2` | Also gate the round-2 geometry (a 2nd DSMC run) |
| `--force` | Delete a pre-existing non-empty `results/validation_optimized*` first (destructive) |
| `--steps N` | SPARTA timestep count for the gate DSMC leg (default 2200) |

Exit codes: `0` success / gate PASS / `--dry-run` / `--allow-fail`; `1` infrastructure or
child-process failure — never a fabricated verdict.

---

## 7. Latest recorded result

Official run **2026-10-04**, `src/python/hiad_optimization_results.json`:

| Parameter | Default (IRVE-3 baseline) | Optimized | Δ |
| :--- | :--- | :--- | :--- |
| Nose radius `R_N` | 1.5000 m | 2.9911 m | +99.40% |
| Torus radius `r_tor` | 0.1350 m | 0.0749 m | −44.49% |
| Half-cone angle | 60.00° | 40.35° | −32.74% |
| Drag coefficient `C_d` | 1.6073 | 1.5517 | −3.46% |
| Sutton-Graves heat flux | 16.14 W/cm² | 11.43 W/cm² | −29.18% |
| Total heat load `Q(x)` | 219.10 J/cm² | **155.16 J/cm²** | **−29.18 %** vs the 219.10 baseline |

> ⚠️ **F22(b) — "target" is the wrong word here.** The `Q(x)` objective is normalised by
> `Q_target = comparison.stellarorion.raw_dsmc.total_heat_load_Jcm2`, i.e. **StellarOrion's
> own DSMC heat load**, and `C_d` is penalised against StellarOrion's own measured `Cd`.
> `J(x)` is therefore asked to beat the geometry it was measured from: this is a
> **regression baseline, not a validation target**. Against the reference the code reads
> today (174.13736) the 155.16 result is **−10.898 %**, not the −6.37 % computed against
> the stale 165.715973 recorded in `hiad_optimization_results.json`; against NASA flight
> (188.00) it is **−17.468 %**, against Rapisarda (195.0577) **−20.454 %**.
| Cost `J(x)` | 2.1626 | 1.6022 | −25.91% |

70 evaluations, zero constraint violations, no penalty applied. Reproduce with
`python3 src/python/hiad_optimizer.py`.

---

## 8. Citations

1. Mockus, V. (1978), *Bayesian Approach to Global Optimization*, Springer — Bayesian
   optimization / expected improvement.
2. Jones, D.R., et al. (1998), "A Bayesian Optimization for Global Optimization," *JCGS*
   7(1) 45–59 — Efficient Global Optimization / EI acquisition.
3. Rasmussen, C.E. & Williams, C.K.I. (2006), *Gaussian Processes for Machine Learning*,
   MIT Press — GP surrogate.
4. Kennedy, M.C. & O'Hagan, A. (2000), "Predicting the output from a complex computer code
   when fast approximations are available," *Biometrika* 87(1) 1–13 — multi-fidelity
   bounded multiplicative bias correction (the gate's correction factor).
5. Nocedal, J. & Wright, S. (2006), *Numerical Optimization*, 2nd ed., §3.1 — weighted-sum
   scalarisation of a multi-objective problem (the `J(x)` weights).
6. Plimpton, S. & Gallis, P. (2014), "A.T. Sparta — a parallel unstructured DSMC code…,"
   *J. Comput. Phys.* 268, 400–412 — the DSMC leg of the gate.
7. Sutton, K. & Graves, A.G. (1972), NASA TR R-376 — the Sutton-Graves correlation inside
   `Q̇`.
8. Rapisarda, G. (2023), MSc Thesis, TU Delft, Table 4.10 — IRVE-3 reference values and
   the payload geometry behind `Payload_Nose_Radius_Min`.
