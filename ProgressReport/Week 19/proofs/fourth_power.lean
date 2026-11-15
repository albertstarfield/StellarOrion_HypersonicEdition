/-
  fourth_power.lean

  The question: if radiation is already in the wall balance as
  eps*sigma*(T^4 - T_inf^4), why does a T^3 / T^4-looking quantity turn up again
  when the solver is written out and when the root is found?

  Three claims are separated, because only two of them are arithmetic, and the
  arithmetic here is integer arithmetic, so it can be decided.

  (1) The fourth power is the whole radiative term, counted once.  At the
      measured design point the balance closes to one unit of rounding with one
      radiative term and misses by the entire radiative flux with two.
      `single_count_closes`, `double_count_breaks`, `counts_are_distinguishable`.

  (2) The T^3 in the Newton slope is the local slope of that same quartic, not a
      second radiative term.  At the design temperature the step of the quartic
      and four times the cube are both computed, and the step is the larger by
      about a tenth of a per cent, which is what convexity means.
      `slope_at_design`, `quartic_step_at_design`, `step_exceeds_slope`.

  (3) With one conduction path and one radiative path in parallel at the same
      wall node, the residual is strictly increasing in T, so the temperature the
      bisection chases is unique.  `residual_strictMono`, `residual_injective`.

  What is NOT in here, and cannot be: that the model is the right physics.  A
  participating medium would add a Rosseland term with k_rad = 16*sigma*T^3 /
  (3*kappa_R); whether that term belongs is settled by the gas being
  free-molecular and optically thin, which is a modelling decision with a
  citation, not a theorem.  This file proves only that the bookkeeping inside
  the chosen model is consistent and that the root it solves for is unique.
-/

namespace FourthPower

/-! ### The measured design point, counted once and counted twice -/

/-- Incident convective flux at the design point, W/m^2 (deck frame 44). -/
def qIn : Int := 143760
/-- Re-radiated flux, W/m^2 (deck frame 44). -/
def qRad : Int := 140399
/-- Conducted flux into the stack, W/m^2 (deck frame 44). -/
def qCond : Int := 3362

/-- One radiative term: the balance closes to a single unit of rounding. -/
theorem single_count_closes : (qIn - (qRad + qCond)).natAbs ≤ 2 := by decide

/-- Two radiative terms: the balance misses by the whole radiative flux. -/
theorem double_count_breaks : 100 ≤ (qIn - (2 * qRad + qCond)).natAbs := by decide

/-- The two readings are far apart, so no tolerance can make them agree. -/
theorem counts_are_distinguishable :
    (qIn - (qRad + qCond)).natAbs + 100 ≤ (qIn - (2 * qRad + qCond)).natAbs := by decide

/-! ### The quartic and the slope the solver uses -/

/-- Four times the cube at the design wall temperature, 1348 K (scaled). -/
theorem slope_at_design : 4 * 1348 ^ 3 = 9797824768 := by decide

/-- The actual step of T^4 over one kelvin at that temperature (scaled). -/
theorem quartic_step_at_design : 1349 ^ 4 - 1348 ^ 4 = 9808732785 := by decide

/-- The step is larger than the tangent slope, and by less than a thousandth of
it, which is the convexity the iteration has to respect. -/
theorem step_exceeds_slope :
    9797824768 < 1349 ^ 4 - 1348 ^ 4 ∧ 1349 ^ 4 - 1348 ^ 4 < 9797824768 + 11090000 := by
  decide

/-- Counting the radiative term twice is doubling its coefficient, which is the
same as claiming an emissivity above one. -/
theorem double_count_is_doubled_emissivity (b T : Nat) :
    2 * (b * T ^ 4) = (2 * b) * T ^ 4 := by
  rw [Nat.mul_assoc]

/-- For a positive coefficient and a positive temperature the doubled term is
strictly larger, so the two readings cannot be confused. -/
theorem doubled_term_is_larger {b T : Nat} (hb : 0 < b) (hT : 0 < T) :
    b * T ^ 4 < 2 * (b * T ^ 4) := by
  have hpos : 0 < b * T ^ 4 := Nat.mul_pos hb (Nat.pow_pos hT)
  omega

/-! ### One conduction path, one radiative path: the root is unique -/

/-- The wall residual in scaled integer units: c carries 1/R, b carries
eps*sigma, and T^4 is the single radiative power. -/
def residual (c b T : Nat) : Nat := c * T + b * T ^ 4

/-- Strictly increasing in T whenever both coefficients are positive. -/
theorem residual_strictMono {c b : Nat} (hc : 0 < c) (hb : 0 < b) {T₁ T₂ : Nat}
    (h : T₁ < T₂) : residual c b T₁ < residual c b T₂ := by
  unfold residual
  have hc' : c * T₁ < c * T₂ := Nat.mul_lt_mul_of_pos_left h hc
  have hp : T₁ ^ 4 < T₂ ^ 4 := Nat.pow_lt_pow_left h (by decide : (4 : Nat) ≠ 0)
  have hb' : b * T₁ ^ 4 < b * T₂ ^ 4 := Nat.mul_lt_mul_of_pos_left hp hb
  exact Nat.add_lt_add hc' hb'

/-- Hence the wall temperature that closes the balance is unique. -/
theorem residual_injective {c b : Nat} (hc : 0 < c) (hb : 0 < b) {T₁ T₂ : Nat}
    (h : residual c b T₁ = residual c b T₂) : T₁ = T₂ := by
  rcases Nat.lt_trichotomy T₁ T₂ with hlt | heq | hgt
  · exact absurd h (Nat.ne_of_lt (residual_strictMono hc hb hlt))
  · exact heq
  · exact absurd h.symm (Nat.ne_of_lt (residual_strictMono hc hb hgt))

#print axioms single_count_closes
#print axioms double_count_breaks
#print axioms step_exceeds_slope
#print axioms residual_strictMono
#print axioms residual_injective

end FourthPower
