# Thesis Defense Q&A (generated audit)

## Q1. What is the IRVE-3 flight peak heat flux and how does the DSMC result compare?
A. Flight peak 14.36 W/cm² (Lau 2013). This work's Sutton–Graves correlation at the DSMC run condition gives 15.36 W/cm² (+6.9%). The solver-resolved DSMC surface data give 192.0 W/cm² max single-cell and 55.2 W/cm² per-element average, but these are noisy and not used as the headline. Source: Ch. IV §4.1, Table 4.1.

## Q2. Why are the field panels at Mach 7.53 / V≈2472 m/s while the scalar validation uses V=3378 m/s?
A. The panels are renders of the step-2200 grid dump of the reference run (results/00_reference/grid.2200.out), whose recorded condition is M∞=7.534, T∞=267.85 K. The scalar metrics use the 3378 m/s trajectory point. The thesis states this explicitly and treats the panels as qualitative only. Source: Ch. IV §4.1 provenance paragraph.

## Q3. What is the validation gate and what are its outcomes?
A. Pass-1 candidate fails at 175.580 J/cm² vs target 165.716 J/cm²; correction factor clamped to 2.0; pass-2 passes at 117.526 J/cm². Source: Ch. IV §4.10 (chapter_04_gate.tex).

## Q4. What is the Knudsen number range in the reference flow field?
A. 10⁻⁵ to 1.15×10⁻² (transitional to near-continuum, never free-molecular). Source: Fig. 4.4 caption.

## Q5. What grid resolution and particle count were used?
A. 139×139×1 Cartesian grid, 19321 child cells; ~1.39×10⁶ particles initially, ~1.19×10⁶ at final step; time step 1×10⁻⁶ s for 2200 steps. Source: Ch. I scope item 5 + run.sparta.log.

## Q6. How many GA generations and evaluations?
A. 38 generations, 1900 individual evaluations, population 50, LHS-seeded. Source: Ch. IV §4.9.

## Q7. What is the optimized geometry?
A. Pass-2: D=6.0 m, Rn=1.1 m, r_tor=0.05 m, half-cone 45.97°, 6 toroids. Source: Table 4.10.

## Q8. What is the peak deceleration of the pass-2 candidate?
A. 8.357 g (vs 22.720 g reference). Source: Ch. IV §4.10.

## Q9. Is the PINN part of the final pipeline?
A. No. PINN is removed from the main pipeline; the optimizer is a simple GA on a closed-form cost. Source: Ch. I PINN-HIDDEN comments and Ch. I §1.4.d.

## Q10. What validation data is NOT available?
A. LOFTID flight data is not validated (only IRVE-3). Full 3D off-axis simulations are not reported. Particle-count/time-step now documented (added this pass). Backface-temperature flight data not compared.
