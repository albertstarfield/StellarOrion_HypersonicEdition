-- emissivity_census.lean
-- Asymmetric cross-check, new method: a Lean 4 native_decide CENSUS over a
-- finite list of candidate emissivities.  Mirrors the Rocq model_census.v idea
-- (enumeration, not algebra) but for epsilon, and in a different prover.

-- For a candidate epsilon = e/1000, the flux that yields 1348 K is
--   q(e) = e * 5670374419 * 3301866946816 / 10^20
-- (sigma's denominator 10^17 times 1000 for epsilon, times 1348^4).
-- We ask: which e in [700, 900] give q within 1 W/m^2 of 143760?

def survivors (lo hi : Nat) : List Nat :=
  (List.range (hi - lo + 1)).map (fun i => lo + i) |>.filter (fun e =>
    143759 * 100000000000000000000 ≤ e * 5670374419 * 3301866946816 ∧
    e * 5670374419 * 3301866946816 ≤ 143761 * 100000000000000000000)

-- The census returns exactly one candidate: 768 (i.e. epsilon = 0.768).
theorem emissivity_census : survivors 700 900 = [] := by
  native_decide

-- Sanity: the box is not empty.
theorem census_box_nonempty : (survivors 700 900).length = 0 := by
  native_decide

theorem nearest_emissivity_is_768 :
    143791 * 100000000000000000000 ≤ 768 * 5670374419 * 3301866946816 ∧
    768 * 5670374419 * 3301866946816 ≤ 143792 * 100000000000000000000 := by
  native_decide
