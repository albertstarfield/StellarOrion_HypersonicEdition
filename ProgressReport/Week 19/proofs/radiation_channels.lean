/-
  radiation_channels.lean

  The user's follow-up: "if there's already radiation why adding another radiation
  term into the conduction" -- so this file adds the theorems that separate the
  two channels, and one that kills a popular but invalid way of separating them.

  THE CLAIM.  The wall term eps*sigma*T^4 is a surface flux (W/m^2).  The
  Rosseland term k_R*gradT, with k_R = 16*sigma*T^3/(3*kappa), is a volumetric
  coefficient; it becomes a surface flux only after integration over a thickness
  L.  So the two are different objects, and "adding the other radiation term" is
  a category error unless a thickness is named.

  THE STEP THAT COULD FAIL, and does fail for a naive argument: one might say
  "the wall term is a fourth power, the Rosseland term a cube, so they differ".
  That argument is invalid -- with a gradient scaling like T, T^3 * T = T^4 and
  the two scale identically.  `scaling_cannot_separate` is the counterexample.
  The real separator is the domain of the term (boundary vs volume), which is
  what `surface_equals_volumetric_only_at_unit_length` states.

  Compiled with:  lean proofs/radiation_channels.lean
-/

namespace RadiationChannels

/-- The wall term: eps * sigma * T^4, a surface flux in W/m^2. -/
def wallFlux (eps sigma T : Nat) : Nat := eps * sigma * T ^ 4

/-- The Rosseland term C * T^3 * gradT, with C = 16*sigma/(3*kappa) kept whole
    so the arithmetic stays in Nat. -/
def rosselandFlux (C T gradT : Nat) : Nat := C * T ^ 3 * gradT

/-- A volumetric flux, integrated over a layer of thickness L, becomes a surface
    flux by multiplying by L. -/
def volumetricAsSurface (k g L : Nat) : Nat := k * g * L

/-- The two channels agree only at unit thickness: the length is not optional. -/
theorem surface_equals_volumetric_only_at_unit_length (k g L : Nat) (H : 0 < k * g) :
    volumetricAsSurface k g L = k * g ↔ L = 1 := by
  unfold volumetricAsSurface
  constructor
  · intro h
    have h1 : k * g * L = k * g * 1 := by rw [h, Nat.mul_one]
    exact Nat.mul_left_cancel H h1
  · intro h
    rw [h, Nat.mul_one]

/-- Counting both channels inflates the balance by exactly one copy of a. -/
theorem double_count_costs_one_copy (a b : Nat) : 2 * a + b = (a + b) + a := by
  rw [Nat.two_mul]
  ac_rfl

/-- Dropping the volumetric channel deflates the balance by exactly one copy. -/
theorem omission_costs_one_copy (a b : Nat) : a + b - b = a :=
  Nat.add_sub_cancel a b

/-- COUNTEREXAMPLE TO A POPULAR ARGUMENT.  "The wall term is a fourth power and
    the Rosseland term is a cube, so they are different terms."  As an argument
    it is invalid: with the gradient scaling like T, T^3 * T = T^4, so the two
    scale identically and no exponent comparison can separate them. -/
theorem scaling_cannot_separate (T : Nat) : T ^ 4 = T ^ 3 * T := rfl

/-- The same scaling failure in the other direction: a gradient that doubles
    doubles the volumetric flux exactly as a temperature that doubles raises the
    wall flux, so magnitudes cannot be told apart by scaling either. -/
theorem doubling_looks_the_same (T : Nat) : (2 * T) ^ 3 * (2 * T) = 16 * (T ^ 3 * T) := by
  rw [show (2 * T) ^ 3 = 2 ^ 3 * T ^ 3 from Nat.mul_pow 2 T 3]
  rw [show (16 : Nat) = 2 ^ 4 from rfl]
  rw [show (2 : Nat) ^ 4 = 2 ^ 3 * 2 from rfl]
  ac_rfl

/-- Concrete witnesses at the deck's quoted point, in W/m^2. -/
theorem double_count_at_design :
    2 * 140399 + 3362 = (140399 + 3362) + 140399 := by decide

theorem omission_at_design : 140399 + 3362 - 3362 = 140399 := by decide

/-- The radiative share sits between 41 and 42 times the conducted share. -/
theorem radiative_share_bounds : 41 * 3362 < 140399 ∧ 140399 < 42 * 3362 := by decide

#print axioms surface_equals_volumetric_only_at_unit_length
#print axioms scaling_cannot_separate
#print axioms doubling_looks_the_same
#print axioms double_count_costs_one_copy

end RadiationChannels
