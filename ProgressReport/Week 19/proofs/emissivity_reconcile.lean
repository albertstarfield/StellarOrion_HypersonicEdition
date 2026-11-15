-- emissivity_reconcile.lean
-- Asymmetric cross-check of the fourth_root_bracket.v claims, in Lean 4,
-- using native_decide on scaled integers (a different prover AND a different
-- mechanism from Rocq's vm_compute on Q).

-- (1) At eps = 0.85 the flux that yields 1348 K is between 159143 and 159144.
theorem q_for_1348_at_eps_85 :
    159143 * 2000000000000000000 < 96396365123 * 3301866946816 ∧
    96396365123 * 3301866946816 < 159144 * 2000000000000000000 := by
  native_decide

-- (2) At eps = 768/1000 the same temperature gives a flux between 143700 and 143800,
--     i.e. eps ≈ 0.7678329740938624 is what reconciles 143760 W/m^2 with 1348 K.
theorem q_for_1348_at_eps_768_per_1000 :
    143700 * 100000000000000000000 < 768 * 5670374419 * 3301866946816 ∧
    768 * 5670374419 * 3301866946816 < 143800 * 100000000000000000000 := by
  native_decide

-- (3) The split printed on the slide is off by one.
theorem deck_split_is_off_by_one :
    140399 + 3362 ≠ 143760 := by
  native_decide
