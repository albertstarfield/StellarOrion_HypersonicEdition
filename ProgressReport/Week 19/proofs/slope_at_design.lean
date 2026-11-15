-- slope_at_design.lean
-- Asymmetric cross-check, new method: Lean 4 native_decide on the deck's p.46
-- claim "the slope 1/R + 4*eps*sigma*T^3 + G is positive, so the root is unique".
-- We check the finite difference of f(T) = T + eps*sigma*T^4 (R=1, G=0) at the
-- design point T = 1348: f(1348) - f(1347) > 0 and f(1349) - f(1348) > 0.
-- Scaled by the denominator of eps*sigma (2*10^18): the difference is
--   1 * 2*10^18 + 96396365123 * (T2^4 - T1^4)   (all integers).

theorem finite_difference_positive_left :
    0 < 1 * 2000000000000000000 + 96396365123 * (1348^4 - 1347^4) := by
  native_decide

theorem finite_difference_positive_right :
    0 < 1 * 2000000000000000000 + 96396365123 * (1349^4 - 1348^4) := by
  native_decide
