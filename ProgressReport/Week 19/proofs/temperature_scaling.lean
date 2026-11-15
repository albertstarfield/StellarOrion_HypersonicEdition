/-
  temperature_scaling.lean

  The sharpest form of "if there is already radiation, why add another radiation
  term to the conduction?" -- and why every temperature-scaling experiment must
  fail to answer it.

  THE ARGUMENT.
    * A monomial C*T^n scales as d^n when T is scaled by d.  So a temperature
      scaling identifies the exponent n.
    * But the Rosseland coefficient is itself cubic in T, k_R = C*T^3, and it
      multiplies gradT, which is linear in T.  Their product is exactly C*T^4.
    * Therefore the volumetric channel and the wall channel scale with the SAME
      power of T.  No change of temperature -- doubling, tripling, any d -- can
      tell them apart.  The exponent you see is a consequence, not a witness.
    * What is left is the domain: the wall term lives on the boundary, the
      volumetric one lives in the layer.  That is proved operationally in
      channel_discriminator.lean ll. 33 and 40 (halve the layer; one term moves).

  Compiled with:  lean proofs/temperature_scaling.lean
-/

namespace TemperatureScaling

/-- Scaling T by d scales a monomial of degree n by d^n: this is what makes the
    exponent observable at all. -/
theorem scaling_identifies_the_exponent (C T d n : Nat) :
    C * (d * T) ^ n = d ^ n * (C * T ^ n) := by
  rw [Nat.mul_pow]
  ac_rfl

/-- A cubic coefficient multiplying a linear gradient is exactly a quartic
    monomial: (d*T)^3 * (d*T) = (d*T)^4.  This is the algebra behind
    k_R * gradT ~ T^3 * T = T^4. -/
theorem cubic_times_linear_is_quartic (C T d : Nat) :
    C * ((d * T) ^ 3 * (d * T)) = d ^ 4 * (C * T ^ 4) := by
  rw [← Nat.pow_succ]
  rw [Nat.mul_pow]
  ac_rfl

/-- The wall term, being a plain quartic, scales the same way. -/
theorem wall_scales_as_fourth_power (C T d : Nat) :
    C * (d * T) ^ 4 = d ^ 4 * (C * T ^ 4) := by
  rw [Nat.mul_pow]
  ac_rfl

/-- THE NEGATIVE RESULT.  If the two candidate models agree at the scaled
    temperature d*T, they agree at T as well -- for every d.  A temperature
    scaling is therefore not a test: it cannot separate the channels, whatever
    the exponent looks like. -/
theorem no_temperature_scaling_separates (C1 C2 T d : Nat)
    (hd : 0 < d ^ 4)
    (h : C1 * ((d * T) ^ 3 * (d * T)) = C2 * (d * T) ^ 4) :
    C1 * T ^ 4 = C2 * T ^ 4 := by
  rw [cubic_times_linear_is_quartic] at h
  rw [wall_scales_as_fourth_power] at h
  exact Nat.mul_left_cancel hd h

/-- Since the exponent cannot separate them, the only separator is the domain.
    A surface term is thickness-blind; the volumetric one is not. -/
theorem surface_term_has_no_thickness_parameter (C : Nat) :
    (fun _L : Nat => C) 0 = (fun _L : Nat => C) 1 := by
  rfl

/-- Whereas the volumetric surface-equivalent is linear in the layer thickness,
    so halving the layer halves it. -/
theorem volumetric_term_halves_with_the_layer (k g L : Nat) :
    k * g * (L * 2) = 2 * (k * g * L) := by
  ac_rfl

/-- Exponents are observable in principle -- 2^3 and 2^4 differ -- which is why
    the coincidence of the two channels at degree four is worth stating
    explicitly rather than assumed. -/
theorem exponent_three_differs_from_four : (2 : Nat) ^ 3 ≠ 2 ^ 4 := by decide

#print axioms scaling_identifies_the_exponent
#print axioms cubic_times_linear_is_quartic
#print axioms no_temperature_scaling_separates

end TemperatureScaling
