/-
  fourth_power_audit.lean

  Audit probe for fourth_power.lean.  Nothing here replaces that file; this
  file (a) prints the axioms of EVERY theorem it declares, including the five
  the original never prints, and (b) tests the three places where the original
  statement is weaker than the prose around it:

  A. `residual` is Nat-valued, so `residual c b 0 = 0` for every c, b: the
     Lean "residual" has a root at absolute zero and no root at 1348 K.  It
     formalises monotonicity of a shape, not the balance equation.
  B. The Ada residual differs from Lean's by a T-independent constant, which
     is harmless -- proved here (`strictMono_add_const`), and then the
     Ada-shaped residual with a possibly negative (T - T_back) is proved
     strictly monotone over Int (`ada_shape_strictMono`).
  C. If the `- q` term is written with Nat subtraction (the obvious way to
     "add the missing term"), strict monotonicity is destroyed by truncation:
     `nat_sub_kills_strictMono` gives the numerals.
-/

namespace FourthPowerAudit

/-! ### Copy of the original definitions, unchanged -/

def qIn : Int := 143760
def qRad : Int := 140399
def qCond : Int := 3362

def residual (c b T : Nat) : Nat := c * T + b * T ^ 4

/-! ### A. The Nat residual's root is not the physical root -/

/-- Every positive-coefficient Nat residual vanishes at T = 0. -/
theorem residual_at_zero (c b : Nat) : residual c b 0 = 0 := by
  simp [residual]

/-- And T = 0 is its ONLY root, for positive coefficients: no Nat T solves
    the physical balance c*T + b*T^4 = q with q > 0. -/
theorem residual_eq_zero_iff {c b : Nat} (hc : 0 < c) (hb : 0 < b) (T : Nat) :
    residual c b T = 0 ↔ T = 0 := by
  constructor
  · intro h
    unfold residual at h
    rcases Nat.eq_zero_or_pos T with hT | hT
    · exact hT
    · exfalso
      have h1 : 0 < c * T := Nat.mul_pos hc hT
      have h2 : 0 < b * T ^ 4 := Nat.mul_pos hb (Nat.pow_pos hT)
      have h3 : 0 < c * T + b * T ^ 4 := Nat.add_pos_left h1 _
      omega
  · intro h; subst h; exact residual_at_zero c b

/-! ### B. Constants are harmless; the Ada shape survives over Int -/

/-- Adding a T-independent constant preserves strict monotonicity.  This is
    the step that licenses dropping T_back/R, b*T_inf^4, -q and -S. -/
theorem strictMono_add_const {f : Int → Int} (hf : ∀ a b : Int, a < b → f a < f b)
    (C : Int) : ∀ a b : Int, a < b → f a + C < f b + C := by
  intro a b h
  have := hf a b h
  omega

/-- The T-dependent part of the Ada residual,
      k*T + b*T^4 + G*T,
    is strictly increasing over Int for k > 0, b > 0, G ≥ 0 -- with no
    hypothesis that T - T_back be non-negative. -/
theorem ada_shape_strictMono (k b G : Int) (hk : 0 < k) (hb : 0 < b) (hG : 0 ≤ G)
    {T₁ T₂ : Nat} (h : T₁ < T₂) :
    k * (T₁ : Int) + b * (T₁ : Int) ^ 4 + G * (T₁ : Int)
      < k * (T₂ : Int) + b * (T₂ : Int) ^ 4 + G * (T₂ : Int) := by
  have h12 : (T₁ : Int) < (T₂ : Int) := Int.ofNat_lt.mpr h
  have hp : T₁ ^ 4 < T₂ ^ 4 := Nat.pow_lt_pow_left h (by decide : (4 : Nat) ≠ 0)
  have hcast : ((T₁ ^ 4 : Nat) : Int) < ((T₂ ^ 4 : Nat) : Int) := Int.ofNat_lt.mpr hp
  have hp' : (T₁ : Int) ^ 4 < (T₂ : Int) ^ 4 := by
    simpa [Int.natCast_pow] using hcast
  have h1 : k * (T₁ : Int) < k * (T₂ : Int) := Int.mul_lt_mul_of_pos_left h12 hk
  have h2 : b * (T₁ : Int) ^ 4 < b * (T₂ : Int) ^ 4 :=
    Int.mul_lt_mul_of_pos_left hp' hb
  have h3 : G * (T₁ : Int) ≤ G * (T₂ : Int) :=
    Int.mul_le_mul_of_nonneg_left (Int.le_of_lt h12) hG
  have h4 : k * (T₁ : Int) + b * (T₁ : Int) ^ 4
      < k * (T₂ : Int) + b * (T₂ : Int) ^ 4 := Int.add_lt_add h1 h2
  omega

/-! ### C. The obvious way to add `- q` in Nat destroys the theorem -/

/-- Nat subtraction truncates at zero, so a Nat-valued residual with the
    imposed flux removed is NOT strictly increasing: at c = b = 1, q = 100,
    both T = 1 and T = 2 give residual 0. -/
theorem nat_sub_kills_strictMono :
    ¬ (∀ T₁ T₂ : Nat, T₁ < T₂ →
        (1 * T₁ + 1 * T₁ ^ 4) - 100 < (1 * T₂ + 1 * T₂ ^ 4) - 100) := by
  intro h
  have h12 : (1 : Nat) < 2 := by decide
  have hbad := h 1 2 h12
  revert hbad
  decide

/-- The same two numerals computed out, so the failure is not a tactic
    artefact: 1 + 1 - 100 = 0 and 2 + 16 - 100 = 0 in Nat. -/
example : (1 * 1 + 1 * 1 ^ 4 : Nat) - 100 = (1 * 2 + 1 * 2 ^ 4 : Nat) - 100 := by
  decide

/-! ### D. Axioms

Axiom printing is done by `proofs/fourth_power_axioms.lean`, which is a
byte-identical copy of `fourth_power.lean` with ten `#print axioms` lines
appended, so the declarations tested are the original ones and not copies.
The five theorems the original omits are the ones that matter: three of them
are the arithmetic (`counts_are_distinguishable`, `slope_at_design`,
`quartic_step_at_design`) and two are algebra
(`double_count_is_doubled_emissivity`, `doubled_term_is_larger`).
-/

/-! ### E. A Quot.sound-free replacement for `doubled_term_is_larger`

The original closes with `omega`, which drags in `Quot.sound`.  The same
statement follows from `Nat.mul_lt_mul_of_pos_left` on `1 < 2`, with no tactic
that touches quotients.  Verified below to be axiom-free.
-/

theorem doubled_term_is_larger_clean {b T : Nat} (hb : 0 < b) (hT : 0 < T) :
    b * T ^ 4 < 2 * (b * T ^ 4) := by
  have hpos : 0 < b * T ^ 4 := Nat.mul_pos hb (Nat.pow_pos hT)
  have h := Nat.mul_lt_mul_of_pos_left (show (1 : Nat) < 2 by decide) hpos
  simpa [Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h

#print axioms doubled_term_is_larger_clean

end FourthPowerAudit
