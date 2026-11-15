/-
  ledger_reconciliation.lean

  A different method again: not calculus and not the threshold, but exact
  integer bookkeeping of the two ledgers the deck and the thesis actually print,
  plus the identity that makes "a second radiation term" a countable object.

  THE CLAIM.  Adding k_R*gradT as if it were a second radiative channel changes
  the balance by exactly k_R*gradT -- not by a rounding, not by a fraction of
  itself.  So the deck cannot leave the choice implicit: the two ledgers differ
  by a named quantity.

  THE STEP THAT COULD FAIL.  The identity is arithmetic and holds for any
  positive coefficients; what it does NOT do is tell us whether k_R*gradT is
  present in this gas.  That is the measurement, and the last theorem turns the
  measurement into a decision procedure with two witnesses on opposite sides.

  Compiled with:  lean proofs/ledger_reconciliation.lean
-/

namespace LedgerReconciliation

/- ---------- the deck's ledger, as printed ---------- -/

def deckTotal : Nat := 143760
def deckRadiated : Nat := 140399
def deckConducted : Nat := 3362

theorem deck_ledger_overshoots : deckRadiated + deckConducted = deckTotal + 1 := by decide

/-- COUNTEREXAMPLE TO MY OWN PROSE: I had been saying the deck's residual is
    +1 W/m^2.  It is -1: the two shares sum to 143761 against a stated total of
    143760, so the ledger overshoots by one unit, it does not undershoot. -/
theorem deck_residual_is_minus_one : deckRadiated + deckConducted - deckTotal = 1 := by decide

/- ---------- the thesis's closure, as printed at appendix.tex:820 ---------- -/

def thesisImposed : Nat := 193154
def thesisRadiated : Nat := 189820
def thesisConducted : Nat := 3700

/-- The thesis overshoots its imposed flux by less than 0.19 %: the excess is
    366 W/m^2 on 193154, and 366 * 10000 = 3,660,000 < 3,669,926 = 193154 * 19. -/
theorem thesis_closure_within_019_percent :
    (thesisRadiated + thesisConducted - thesisImposed) * 10000 ≤ thesisImposed * 19 := by
  decide

/-- And the two ledgers are not the same case: the deck's total is strictly below
    the thesis's imposed flux. -/
theorem deck_and_thesis_disagree : deckTotal < thesisImposed := by decide

/- ---------- the identity that makes "a second term" countable ---------- -/

/-- Adding b*T^4 to a balance adds exactly b*T^4: distributivity, nothing else. -/
theorem adding_a_second_radiative_term_adds_exactly_itself
    (a b c T q : Nat) :
    (a + b) * T ^ 4 + c * T + q = (a * T ^ 4 + c * T + q) + b * T ^ 4 := by
  rw [Nat.add_mul]
  ac_rfl

/-- Therefore the difference between the two models is the term itself, not a
    fraction of it and not a rounding: no calibration of the conduction may
    absorb it silently, because the difference does not contain the conduction
    coefficient at all. -/
theorem the_difference_is_the_term_itself
    (a b c T q : Nat) :
    (a + b) * T ^ 4 + c * T + q - (a * T ^ 4 + c * T + q) = b * T ^ 4 := by
  rw [adding_a_second_radiative_term_adds_exactly_itself, Nat.add_sub_cancel_left]

/-- The twin errors: counting the term twice and dropping it are the same size
    and opposite sign, so neither can be dismissed as small. -/
theorem both_mistakes_have_the_same_size (a b : Nat) :
    a + b - b = a ∧ a + b + a - (a + b) = a := by
  constructor
  · exact Nat.add_sub_cancel a b
  · exact Nat.add_sub_cancel_left (a + b) a

/- ---------- the measurement as a decision procedure ---------- -/

/-- Legitimate means kappa strictly above the 7407 1/m floor of the threshold
    proved in omission_threshold.v (7,407.645 at T = 1348 K, k_gas = 0.1). -/
def omissionLegitimate (kappa : Nat) : Bool := Nat.blt 7407 kappa

/-- Two witnesses on opposite sides of the decision: 740 keeps the term, 74080
    drops it.  This is the whole empirical content, and it is one number. -/
theorem measurement_decides :
    omissionLegitimate 740 = false ∧ omissionLegitimate 74080 = true := by decide

/-- The decision is total: every kappa gets an answer, so "we don't know" is a
    statement about the measurement, never about the logic. -/
theorem measurement_is_total (kappa : Nat) :
    omissionLegitimate kappa = true ∨ omissionLegitimate kappa = false := by
  cases omissionLegitimate kappa <;> simp

#print axioms adding_a_second_radiative_term_adds_exactly_itself
#print axioms the_difference_is_the_term_itself
#print axioms measurement_decides

end LedgerReconciliation
