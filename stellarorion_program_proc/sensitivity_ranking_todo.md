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

- [ ] Decide scope: does the ranking change apply to the closed-form CCD
      screening stage, the GP surrogate stage, or the gate?
- [ ] If PINN scores candidates: solve the supervisor problem — a PINN can
      only be trained on DSMC fields, so every scored candidate needs a DSMC
      run first (the speed win of the closed-form scoring is gone), or a
      pre-trained network is frozen before the sweep (then it carries its own
      spectral-bias floor into the ranking).
- [ ] If the change is made anyway, guard the shock-sensitive term: either
      keep DSMC in the ranking loop for the heat-load term, validate the
      surrogate specifically at the shock boundary before trusting any
      ranking, or restrict the ranking to shock-insensitive metrics.
- [ ] Recorded-campaign note: the shipped 70-entry history, the corrected
      rerun (R_N = 2.9979 m, J = 1.1415) and the gate numbers were produced
      by the closed-form-scoring architecture; any pipeline change requires a
      campaign rerun before thesis numbers are re-stated.

## Reference anchors (thesis text)

- Ch2 Limitation paragraph (Applications in Hypersonic Aerothermodynamics):
  spectral bias, shock attenuation, trend-level survivability bound.
- Ch2 "Why physics replaces data." paragraph: PDE residual + boundary
  conditions as the supervisor (why a PINN can work without a large dataset).
- Ch3 L773: closed-form scoring during the search, solver never called.
- Ch4 hybrid gate: DSMC re-simulation of the round-1 winner, PINN bypassed.
- Ch5 conclusion: DSMC validates baseline then optimized design; PINN
  refinement bounded to the survivability comparison.
