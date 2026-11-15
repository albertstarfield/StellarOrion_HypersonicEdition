-- recovery_inconsistent.lean
-- New theorem, new file, new method: Lean 4 native_decide on the deck p.50
-- claim "1,348 K recovered from (q_rad/(eps*sigma))^(1/4)".
-- With q = 143760 W/m^2 and eps*sigma = 96396365123 / 2*10^18,
-- the flux that yields exactly 1348 K is 159143.985... != 143760.

theorem flux_for_1348_not_deck_total :
    96396365123 * 1348 ^ 4 ≠ 143760 * 2000000000000000000 := by
  native_decide

theorem flux_for_1348_exceeds_deck_total :
    96396365123 * 1348 ^ 4 > 143760 * 2000000000000000000 := by
  native_decide

theorem deck_split_off_by_one :
    140399 + 3362 ≠ 143760 := by
  native_decide

theorem deck_split_actual :
    140399 + 3362 = 143761 := by
  native_decide