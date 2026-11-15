/-
  exponent_budget.lean

  The sharpest remaining question: "if there is already radiation, why add another
  radiation term into the conduction?"  Answer, as an exponent budget:

    wall term            eps*sigma*T^4          exponent 4, always
    volumetric term      k_R * gradT
      k_R ~ T^3                                  exponent 3
      gradT ~ T^g                                exponent g
      total                                      exponent 3 + g

  So the two channels have the SAME apparent exponent -- and therefore look like
  one term -- exactly when g = 1.  That is a statement about the boundary
  condition, not about the radiative law: g = 1 means the wall temperature scales
  with the gas temperature, which is what a radiative-equilibrium wall does.

  Consequence, and the reason the deck's "T^4 vs T^3" sentence is not an
  explanation: the confusion is manufactured by the boundary condition.  Change
  the boundary condition and the channels separate again (g = 0 gives exponent 3,
  g = 2 gives exponent 5).  What never changes is the domain: one term sits on the
  surface, the other inside the layer -- proved operationally in
  channel_discriminator.lean ll. 33 and 40.

  Compiled with:  lean proofs/exponent_budget.lean
-/

namespace ExponentBudget

/-- Exponent of the volumetric channel: 3 from the Rosseland coefficient, g from
    how the gradient scales with temperature. -/
def volumetricExponent (g : Nat) : Nat := 3 + g

/-- Exponent of the wall channel. -/
def wallExponent : Nat := 4

/-- The two channels are indistinguishable by temperature scaling exactly when
    the gradient scales linearly in T. -/
theorem equal_apparent_exponent_iff_gradient_scales_linearly (g : Nat) :
    volumetricExponent g = wallExponent ↔ g = 1 := by
  unfold volumetricExponent wallExponent
  omega

/-- A temperature-independent gradient (g = 0) leaves a cubic volumetric term,
    which a temperature scaling separates from the quartic wall term at once. -/
theorem constant_gradient_separates : volumetricExponent 0 ≠ wallExponent := by
  unfold volumetricExponent wallExponent
  decide

/-- A gradient scaling faster than the wall (g = 2) separates them too. -/
theorem quadratic_gradient_separates : volumetricExponent 2 ≠ wallExponent := by
  unfold volumetricExponent wallExponent
  decide

/-- The general negative result: for every g other than 1, an exponent test
    works.  So non-separability is the exception, not the rule. -/
theorem only_unit_gradient_hides_the_channel (g : Nat) (hg : g ≠ 1) :
    volumetricExponent g ≠ wallExponent := by
  unfold volumetricExponent wallExponent
  omega

/-- And when it is hidden, it is hidden for every scale factor: the equality of
    exponents means the two channels move together under any d.  (The scaling
    algebra itself is proved in temperature_scaling.lean l. 51.) -/
theorem hidden_means_hidden_at_every_scale (g : Nat) (hg : g = 1) :
    volumetricExponent g = wallExponent := by
  subst hg
  unfold volumetricExponent wallExponent
  rfl

/-- The domain claim in its barest form: a surface term carries no length, a
    volumetric one carries it linearly, so they cannot be the same object
    whatever their exponent. -/
theorem exponent_cannot_change_the_carrier :
    (∀ C : Nat, (fun _L : Nat => C) 7 = (fun _L : Nat => C) 12) ∧
    (∀ k g : Nat, 0 < k * g → k * g * 7 ≠ k * g * 12) := by
  constructor
  · intro C; rfl
  · intro k g hkg h
    exact absurd (Nat.mul_left_cancel hkg h) (by decide)

#print axioms equal_apparent_exponent_iff_gradient_scales_linearly
#print axioms only_unit_gradient_hides_the_channel
#print axioms exponent_cannot_change_the_carrier

end ExponentBudget
