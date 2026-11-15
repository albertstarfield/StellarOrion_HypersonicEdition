/-
  conductivity_vs_source.lean

  The one step in the process answer that was still only argued in prose: "the
  Rosseland term is not a second radiation channel, because a conductivity is not
  a source."  Here it is as a theorem on a three-node layer.

  The discriminating property, stated so it can fail:

    * a conductive imbalance is k * (curvature of the profile).  On a FLAT
      profile it is zero -- for every coefficient, including a coefficient that
      depends on temperature, k = f(T).  A conductor with nothing to conduct
      moves nothing.
    * a source term adds S whatever the profile.  On a flat profile it survives
      untouched.

  So no coefficient, however strongly temperature-dependent, can turn a
  conductivity into a channel: on an isothermal layer one vanishes and the other
  does not.  That is the test the deck never runs, and it is the reason the T^3
  coefficient in front of a gradient is not "another radiation term".

  Consequence for the deck's "T^4 outside Fourier" slide: the quartic term at the
  wall (eps*sigma*T^4) is a surface balance -- it survives on an isothermal
  surface, because it radiates to the environment, not into the layer.  The
  volumetric term cannot.  Two different operators, two different tests.

  Compiled with:  lean proofs/conductivity_vs_source.lean
-/

namespace ConductivityVsSource

/-- Discrete conductive imbalance at the middle node of a three-node layer:
    what arrives from the inner face minus what leaves toward the outer face. -/
def conduction (k T0 T1 T2 : Int) : Int :=
  k * ((T2 - T1) - (T1 - T0))

/-- A conductor with nothing to conduct moves nothing: flat profile implies zero
    imbalance. -/
theorem conduction_vanishes_on_flat_profile (k T0 T1 T2 : Int)
    (h0 : T0 = T1) (h1 : T1 = T2) :
    conduction k T0 T1 T2 = 0 := by
  unfold conduction
  rw [h0, h1]
  simp

/-- The coefficient may be an arbitrary function of temperature -- the Rosseland
    k_R ~ T^3 is exactly this case -- and the flat-profile result is unchanged. -/
theorem temperature_dependent_coefficient_still_vanishes (f : Int → Int)
    (T0 T1 T2 : Int) (h0 : T0 = T1) (h1 : T1 = T2) :
    f T1 * ((T2 - T1) - (T1 - T0)) = 0 := by
  rw [h0, h1]
  simp

/-- A source of size S is not killed by a flat profile.  This is the property a
    conductivity does NOT have, so the two cannot be the same object. -/
theorem source_survives_on_flat_profile (S k T0 T1 T2 : Int)
    (hS : S ≠ 0) (h0 : T0 = T1) (h1 : T1 = T2) :
    S + conduction k T0 T1 T2 ≠ 0 := by
  unfold conduction
  rw [h0, h1]
  simpa using hS

/-- A conductivity is blind to the direction of the gradient; it sees only the
    curvature.  Reversing the profile leaves the imbalance unchanged. -/
theorem conductivity_sees_curvature_not_gradient_direction (k T0 T1 T2 : Int) :
    conduction k T2 T1 T0 = conduction k T0 T1 T2 := by
  unfold conduction
  have h : (T0 - T1) - (T1 - T2) = (T2 - T1) - (T1 - T0) := by omega
  rw [h]

/-- The negative result, in one place: there is no coefficient that makes a
    conductivity behave like a source on an isothermal layer. -/
theorem no_coefficient_turns_a_conductivity_into_a_source :
    (∀ (k T : Int), conduction k T T T = 0) ∧
    (∀ (S k T : Int), S ≠ 0 → S + conduction k T T T ≠ 0) := by
  constructor
  · intro k T
    exact conduction_vanishes_on_flat_profile k T T T rfl rfl
  · intro S k T hS
    exact source_survives_on_flat_profile S k T T T hS rfl rfl

/-- The Rosseland flux itself: no gradient, no flux -- at any temperature. -/
theorem radiative_flux_vanishes_without_a_gradient (kR T : Int) :
    kR * (T - T) = 0 := by
  simp

/-- And conversely: a nonzero gradient through a nonzero coefficient is a
    nonzero flux, so the term is tied to the gradient and not to the level. -/
theorem flux_is_nonzero_when_gradient_is (kR dT : Int)
    (hk : kR ≠ 0) (hd : dT ≠ 0) :
    kR * dT ≠ 0 := by
  intro h
  rcases Int.mul_eq_zero.mp h with h1 | h2
  · exact hk h1
  · exact hd h2

#print axioms conduction_vanishes_on_flat_profile
#print axioms temperature_dependent_coefficient_still_vanishes
#print axioms no_coefficient_turns_a_conductivity_into_a_source

end ConductivityVsSource
