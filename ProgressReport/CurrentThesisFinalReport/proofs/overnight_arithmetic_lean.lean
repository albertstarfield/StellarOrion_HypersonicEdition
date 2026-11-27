-- Lean 4 core (no Mathlib available in this environment): rational arithmetic
-- checks for the numeric claims added to tab:analytic_validation on 2026-11-27.
-- Constants re-read this turn from chapter_03_methodology.tex eq:sutton_graves /
-- eq:heat_load and chapter_04_results.tex:196-208:
--   rho = 7.851e-4 kg/m^3, V = 3378 m/s, C_SG = 1.7415e-4,
--   R_n = 0.55 m, tau = 13.582459 s, flight q = 14.36 W/cm^2,
--   flight Q = 195.06 J/cm^2.
-- q_SG^2 (in W/cm^2 squared) = C^2 * rho/R_n * V^6 / 1e8.
-- Rat equality/order is computable, so native_decide is a kernel-checked proof.

example : (25362 / 1000 : Rat)^2 <=
    ((17415 / 100000000 : Rat)^2 * (7851 / 10000000 : Rat) /
     (55 / 100 : Rat) * (3378 : Rat)^6 / 100000000) := by native_decide

example :
    ((17415 / 100000000 : Rat)^2 * (7851 / 10000000 : Rat) /
     (55 / 100 : Rat) * (3378 : Rat)^6 / 100000000) <
    (25363 / 1000 : Rat)^2 := by native_decide

example :
    ((17415 / 100000000 : Rat)^2 * (7851 / 10000000 : Rat) /
     (55 / 100 : Rat) * (3378 : Rat)^6 / 100000000) <
    (2536201 / 100000 : Rat)^2 := by native_decide

-- Heat load: q*tau rounds to 344.48 J/cm^2, i.e. lies in [344.475, 344.485).
example : (344475 / 1000 : Rat) <=
    (25362 / 1000 : Rat) * (13582459 / 1000000 : Rat) := by native_decide

example :
    (2536201 / 100000 : Rat) * (13582459 / 1000000 : Rat) <
    (344485 / 1000 : Rat) := by native_decide

-- Both +76.6% entries: (analytic - flight)/flight in [0.766, 0.767).
example : (766 / 1000 : Rat) <=
    ((2536 / 100 : Rat) - 1436 / 100) / (1436 / 100) := by native_decide

example : ((2536 / 100 : Rat) - 1436 / 100) / (1436 / 100) <
    (767 / 1000 : Rat) := by native_decide

example : (766 / 1000 : Rat) <=
    ((34448 / 100 : Rat) - 19506 / 100) / (19506 / 100) := by native_decide

example : ((34448 / 100 : Rat) - 19506 / 100) / (19506 / 100) <
    (767 / 1000 : Rat) := by native_decide
