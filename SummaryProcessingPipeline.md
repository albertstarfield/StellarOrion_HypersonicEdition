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
       Q_target 165.7160 J/cm²   (StellarOrion validated)
       q_ref      14.3610 W/cm²   (IRVE-3 flight)
       tau        13.5825 s       (= Q_flight / q_flight)
       Cd_ref      1.462536
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
| `Q_target` | 165.7160 J/cm² | StellarOrion validated heat load |
| `Flux_Ref` (`q_ref`) | 14.3610 W/cm² | IRVE-3 flight peak heat flux |
| `Tau_Sec` (`tau`) | 13.5825 s | dynamic heating duration = Q_flight / q_flight |
| `Cd_Ref` | 1.462536 | StellarOrion validated drag coefficient |

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
| `Flux_R` | 0.50 | `W_Flux`, line 359 | Peak heat flux ÷ IRVE-3 flight |
| `β_Dv` | 0.50 | `W_Beta`, line 360 | `(β_R − 1)²`, squared ballistic-coefficient deviation |
| `C_d_R` | 0.25 | `W_Cd`, line 361 | Drag coefficient ÷ reference |
| `Penalty` | λ = 100 | `Lambda_Pen`, line 362 | Quadratic; zero unless a constraint is violated |

Fixed flight condition: `Snapshot_Alt_Km = 51.8 km`, `Snapshot_Vel_Ms = 3378 m/s`
(lines 377–378) — the same single-point condition as the validated DSMC run.

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

**Verdict predicate** (`_gate_verdict`, line 705): `PASS ⟺ q_hybrid ≤ q_target`, with the
boundary counting as PASS (line 740).

**Correction factor:** `c = clamp(q_hybrid / q_analytic, 0.5, 2.0)` — a bounded
multiplicative fidelity correction. This is Kennedy & O'Hagan (2000), *Biometrika* 87(1)
1–13; the clamp stops one bad simulation leg from dragging the surrogate somewhere absurd.

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
| Total heat load `Q(x)` | 219.10 J/cm² | **155.16 J/cm²** (target 165.72) | **−29.18%** |
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
