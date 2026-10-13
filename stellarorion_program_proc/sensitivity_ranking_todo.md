# Sensitivity ranking with PINN? — design note and TODO

> Source: thesis Q&A analysis, 2026-10-13. Reviewed against
> `chapter_02_literature_review.tex` (Ch2), `chapter_03_methodology.tex` (Ch3),
> `chapter_04_results.tex` (Ch4), `chapter_05_conclusion.tex` (Ch5).
> Purpose: park the item-4 redesign ("PINN for sensitivity ranking / CCD
> sampling") as a tracked decision on the program side. The thesis text is
> NOT changed by this file.

## What the thesis actually does

- PINN never touches the ranking in the implemented pipeline. Sensitivity is
  established analytically (closure maps + Sutton–Graves `q ∝ 1/sqrt(R_N)`)
  and the search is scored by the closed-form cost (Ch3 L773: "the recorded
  campaign … scores each design with the closed-form cost … and never calls
  the solver during the search"). There is no PINN sensitivity ranking to lose
  the shock in.
- PINN is a post-processor on DSMC output (the kriging→PINN chain), and the
  Limitation sentence added to Ch2 states the consequence honestly: the
  network attenuates sharp gradients such as the bow shock. That's real — a
  fully connected tanh network cannot resolve the shock's mm-scale jump.
- The thesis therefore never lets PINN be the truth on the shock. The Ch2
  Limitation sentence says it explicitly ("the DSMC particle statistics remain
  the reference"), the validation gate runs DSMC directly on the winner
  (Ch4: q = 77.93 J/cm² from DSMC vs 155.67 J/cm² analytic), and the gate
  bypasses PINN entirely (Ch4 L477: "Enforced DSMC re-simulation gate
  (PINN bypassed)"). Even the kriging→PINN claim in Ch3 is scoped to
  "preserving the shock structure" at the denoising stage, and Ch5's PINN
  validation is still open work ("its accuracy across the continuum and
  slip-flow bands needs quantification").

Conclusion: no claim in the thesis currently depends on PINN resolving the
bow shock.

## The real implication for the item-4 redesign

If sensitivity ranking is later switched to a PINN-surrogate-scored CCD, this
is exactly the hazard to design around, and it is not a small one:

- The heat load is the dominant cost term (the gate's correction factor
  0.5006 exists because the analytic q over-predicted it by ~2x: 155.67 vs
  77.93 J/cm²).
- The heat load is generated at the shock — stagnation heating is a
  shock-layer quantity.
- A network that attenuates the shock would systematically under-rank the
  parameters whose action is through the shock — nose radius above all
  (shock stand-off and stagnation flux). The ranking could come out "flat"
  precisely where the physics is sharpest.

## TODO (owner decision)

- [x] Decide scope: does the ranking change apply to the closed-form CCD
      screening stage, the GP surrogate stage, or the gate?
      ANSWERED -- it applies to the closed-form CCD screening stage ONLY.
      The GP surrogate stage already has uncertainty-guided sampling:
      the BO loop is a Matern 5/2 GP + Expected Improvement over 20 LHS
      + 50 BO evaluations, and Expected Improvement IS
      uncertainty-guided sampling -- it was just never recorded as such.
      The gate is unchanged (DSMC re-simulation of the round-1 winner,
      PINN bypassed).
- [x] If PINN scores candidates: solve the supervisor problem — a PINN can
      only be trained on DSMC fields, so every scored candidate needs a DSMC
      run first (the speed win of the closed-form scoring is gone), or a
      pre-trained network is frozen before the sweep (then it carries its own
      spectral-bias floor into the ranking).
      NOT APPLICABLE -- the PINN cannot be used in the CCD loop. Evidence:
      `pinn_accelerator.py` `train_from_checkpoint(self, grid_file: str,
      ...)` takes a MANDATORY SPARTA `grid.NNNN.out` file (its own
      self-test `test_train_from_checkpoint_missing_file` asserts
      FileNotFoundError when it is missing) -- it is a physics-REGULARISED
      surrogate, not a no-data solver. Each CCD sample is a different
      geometry, hence a different domain, hence a separate training run;
      the gate budgets `_GATE_PIPE_TIMEOUT_S = 90*60` seconds for ONE
      4000-iteration training. It also has no uncertainty estimate at all
      (no ensemble, no MC-dropout; the only np.std uses are
      data-normalisation scalers).
- [x] If the change is made anyway, guard the shock-sensitive term: either
      keep DSMC in the ranking loop for the heat-load term, validate the
      surrogate specifically at the shock boundary before trusting any
      ranking, or restrict the ranking to shock-insensitive metrics.
      ANSWERED -- and it is the important one: the guard turned out to be
      a REPORTING requirement, not a modelling one. The per-term rankings
      INVERT each other. On the composite cost J, r_tor dominates (axial
      swing 23.041132). But on the heat term ALONE only the nose radius
      matters: R_N -0.456, with r_tor and half_cone arithmetically ZERO
      (verified: two CCD points sharing R_N = 1.5 but with r_tor 0.14 vs
      0.207 give byte-identical heat flux 15.35128 W/cm2 and heat load
      208.50807 J/cm2). So the worry above about under-ranking the nose
      radius IS correct -- for the THERMAL question, not for J. The fix is
      to report BOTH rankings rather than collapse them into one number.
- [x] Recorded-campaign note: the shipped 70-entry history, the corrected
      rerun (R_N = 2.9979 m, J = 1.1415) and the gate numbers were produced
      by the closed-form-scoring architecture; any pipeline change requires a
      campaign rerun before thesis numbers are re-stated.
      MEASURED RESOLUTION -- the sensitivity change itself needs NO
      rerun, because it only reads the already-recorded `ccd_samples` and
      changes no physics, no CCD generation, no cost function, and no FFI
      signature. The ranking was measured invariant across all six
      {3378, 2741.14, 2700 m/s} x {tau 14.565899, 13.582459 s}
      combinations; r_tor's swing is literally unchanged (penalty-driven,
      no V/tau dependence). A rerun is still REQUIRED before restating
      absolute thesis figures (J values, optimized geometry, gate
      numbers), but that is a separate piece of work.

## What was built

The item-4 redesign is now built on the screening side: a
central-composite-design (CCD) sensitivity estimator in Ada 2012 /
SPARK 2014 (`pragma SPARK_Mode (On)` in the spec).

- New files `src/simulation_engine/stellarorion_sensitivity.ads` /
  `.adb`. The estimator consumes the 15 coded factor vectors plus the
  recorded responses and never calls the cost function -- the same
  discipline the search itself already follows (Ch3 L773).
- Layout: rotatable CCD, 15 points = 8 factorial corners (coded +-1) +
  1 centre + 6 axial points (coded +-alpha, alpha = 2^(3/4) =
  1.681793). Factors: R_N (1.5 m / 0.3 half-step), r_tor (0.14 / 0.04),
  half_cone_deg (60 / 5).
- Two estimators are computed side by side:
  - Tier 1a axial contrast swing_j = y(+alpha_j) - y(-alpha_j):
    R_N 3.520005, r_tor 23.041132, half_cone_deg 0.034212.
  - Tier 1b factorial corner mean effect mean(y|+j) - mean(y|-j):
    R_N 10.5453, r_tor 11.1575, half_cone_deg 7.3370.
- Both estimators give the same ordering, r_tor > R_N > half_cone_deg,
  but the axial contrast separates them 6.54x while the corner means are
  nearly tied (1.06x): the corners are confounded with the dominant
  R_N x r_tor interaction. That is why the axial contrast is the
  reporting number and the corner means are reported alongside it.
- The ranking is INVARIANT across all six combinations of {3378,
  2741.14, 2700 m/s} x {tau 14.565899, 13.582459 s}; r_tor's swing is
  literally unchanged (penalty-driven, no V/tau dependence).

### Provenance: the objective actually optimised (owner-requested note)

The objective actually optimised here is the TOTAL HEAT FLUX:

    J = 1.0*HL_R + 0.5*Flux_R + 0.5*Beta_Dev + 0.25*Cd_R + Pen

with HL_R an energy in J/cm2 carried at unit weight. The cited source's
objective, its Eq. (5.16), is f(x) = m_F-TPS + m_IAD -- total mass --
and it explicitly declines composite objectives. The only genuine
borrow from that source is the design-space BOUNDS (its Table 5.4);
that is a bound claim, not a cost claim, and the cost function above is
this project's own.

### Literature position

The cited source's "sensitivity analysis" is not a designed experiment.
Its section 6.4 is an 8034-run Monte Carlo read off scatter plots one
variable at a time, and its section 6.3 perturbs the reference
TRAJECTORY CONDITIONS (entry velocity, entry angle, trim AoA, density),
not the design variables. A rotatable CCD performs the same
one-factor-at-a-time contrast orthogonally, balanced and
variance-optimally, so it is strictly stronger than the source it cites.

## Reference anchors (thesis text)

- Ch2 Limitation paragraph (Applications in Hypersonic Aerothermodynamics):
  spectral bias, shock attenuation, trend-level survivability bound.
- Ch2 "Why physics replaces data." paragraph: PDE residual + boundary
  conditions as the supervisor (why a PINN can work without a large dataset).
- Ch3 L773: closed-form scoring during the search, solver never called.
- Ch4 hybrid gate: DSMC re-simulation of the round-1 winner, PINN bypassed.
- Ch5 conclusion: DSMC validates baseline then optimized design; PINN
  refinement bounded to the survivability comparison.
