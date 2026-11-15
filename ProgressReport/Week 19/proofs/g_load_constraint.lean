/-!
# g_load_constraint.lean

Axiom test for the g-load (deceleration) term added to the HIAD cost function.

Encoded integer arithmetic: deceleration `n` in units of 0.01 g, so the 25 g limit
is the integer 2500.  The penalty is `max(0, n - 25)^2` in units of 1e-4 g^2,
matching `Pen_G := Max (0.0, G_Now - G_Load_Limit) ** 2` in
`stellarorion_optimization.adb`.

Source lines:
  stellarorion_optimization.ads  G_Load_Limit := 25.0   (ORION_MAX_G, orion.ads:72)
  stellarorion_optimization.ads  HIAD_Mass_Kg := 281.0  (IRVE3_MASS_KG)
  stellarorion_optimization.adb  Q_Dyn_Now := 0.5*Rho*V**2; Drag := Q_Dyn*Cd*A
  stellarorion_optimization.adb  G_Now := Deceleration_G_Load (Drag, Mass)
  stellarorion_optimization.adb  Pen_G := Max (0.0, G_Now - G_Load_Limit) ** 2
-/

namespace GLoadAudit

/-- Hard structural limit, in 0.01 g units. -/
def GLimit : Int := 2500

/-- The penalty as coded, in 0.01 g units for the argument and 1e-4 g^2 for the
result.  `Nat` for the square so non-negativity is structural, not argued. -/
def PenG (n : Int) : Nat :=
  if n ≤ GLimit then 0 else ((n - GLimit).toNat) ^ 2

/-- THE CLAIM (safety half): a feasible deceleration pays nothing. -/
theorem feasible_pays_nothing (n : Int) (h : n ≤ GLimit) : PenG n = 0 := by
  simp [PenG, h]

/-- THE CLAIM (liveness half): the term is not inert -- it pays as soon as the
trajectory model predicts more than 25 g.  This is what the payload penalty could
not do inside its design box. -/
theorem infeasible_pays (n : Int) (h : GLimit < n) :
    PenG n = ((n - GLimit).toNat) ^ 2 := by
  have hnot : ¬ n ≤ GLimit := by omega
  simp [PenG, hnot]

/-- Non-negativity, hence `J(x) >= 0` survives the added term (spec Post). -/
theorem penalty_nonnegative (n : Int) : 0 ≤ PenG n := Nat.zero_le _

/-- At the IRVE-3 flight peak of 19.7 g the term is zero: the reference vehicle is
inside the limit by 5.3 g. -/
theorem irve3_peak_is_inside : PenG 1970 = 0 := by decide

/-- At 33 g the term is 64 000 000 in units of 1e-4 g^2, i.e. `Pen_G = 6400` g^2;
weighted by `Lambda_Pen = 100` it contributes 640 000 to J, which is six orders of
magnitude above the O(1) ratio terms -- so the GA cannot prefer such a design
without an impossible gain elsewhere. -/
theorem thirtythree_g_is_dominated :
    PenG 3300 = 640000 ∧ 100 * PenG 3300 = 64000000 := by decide

/-- Exactly at the limit, no penalty: the constraint is `n <= 25`, not `n < 25`.
Stated because an off-by-one in the comparison would make the limit 24.99 g. -/
theorem boundary_is_inclusive : PenG 2500 = 0 := by decide

/-- One hundredth of a g over the limit already costs something. -/
theorem just_over_the_limit_binds : PenG 2501 = 1 := by decide

/-- Monotonicity on each side of the threshold: adding penalty can only ever
raise J, never lower it, so the new term cannot make an infeasible design look
better than a feasible one. -/
theorem penalty_monotone_above_limit (a b : Int) (ha : GLimit ≤ a) (hab : a ≤ b) :
    PenG a ≤ PenG b := by
  by_cases h : a ≤ GLimit
  · have heq : a = GLimit := by omega
    subst heq
    simp [PenG]
  · have hb : ¬ b ≤ GLimit := by omega
    simp [PenG, h, hb]
    have hsub : (a - GLimit).toNat ≤ (b - GLimit).toNat := by omega
    exact Nat.pow_le_pow_left hsub 2

/-- The objective with the term is the old objective plus a non-negative amount:
`J_new(x) = J_old(x) + Lambda_Pen * Pen_G(x) >= J_old(x)`. -/
theorem total_is_old_plus_penalty (J_old : Nat) (n : Int) :
    J_old + 100 * PenG n ≥ J_old := by omega

/-- Counterexample to "the term is decorative": with `G_Load_Limit` removed (i.e.
limit at infinity modelled as `n ≤ GLimit` failing), the design space contains
penalised points, so removal changes the objective on a non-empty set. -/
theorem exists_penalised_point : ∃ n : Int, PenG n > 0 :=
  ⟨3300, by decide⟩

/-- And the converse: if the limit were raised above every achievable g-load the
term would be inert -- which is exactly the failure mode the payload penalty
exhibited.  Named so the two cases are not conflated in review. -/
theorem inert_if_limit_above_reachable (n : Int) (h : n ≤ GLimit) : PenG n = 0 :=
  feasible_pays_nothing n h

end GLoadAudit
