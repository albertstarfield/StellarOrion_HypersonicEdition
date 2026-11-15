/-
  possibility_space.lean

  A second, independent check of the same possibility space that
  proofs/possibility_space.v states over the reals.  Here everything is integer
  arithmetic, so every claim about the regime split is decidable: no analysis,
  no axioms, just `decide`.

  The model: in the diffusion limit the radiative share of the flux is
  k_R / k_gas = A / kappa, with

      A = 16 * sigma * T^3 / (3 * k_gas)   evaluated at T = 1348 K,
                                           k_gas = 0.1 W/(m K)  ->  A = 7408 1/m

  So the two hypotheses about the deck's "the term is dropped here"

      H_drop : the term is negligible       <->  A < kappa
      H_keep : the term matters             <->  kappa < A

  are the two open halves of the kappa axis, and kappa = A belongs to neither.
  The theorems below prove that the halves are inhabited, that they never
  overlap, and that together with the boundary they exhaust the axis -- which is
  exactly what makes H_keep a live falsifier of the deck rather than decoration.

  Compiled with:  lean proofs/possibility_space.lean
-/

namespace PossibilitySpace

/-- Threshold extinction in 1/m at the illustrative design point. -/
def A : Nat := 7408

/-- The deck's claim: radiation conduction is below gas conduction. -/
def hDrop (kappa : Nat) : Prop := A < kappa

/-- The falsifier: radiation conduction equals or exceeds gas conduction. -/
def hKeep (kappa : Nat) : Prop := kappa < A

instance hDropDecidable (kappa : Nat) : Decidable (hDrop kappa) := Nat.decLt A kappa
instance hKeepDecidable (kappa : Nat) : Decidable (hKeep kappa) := Nat.decLt kappa A

/-- H_drop is inhabited: a strongly absorbing medium makes the term negligible. -/
theorem hDrop_at_74080 : hDrop 74080 := by decide

/-- H_keep is inhabited: a weakly absorbing medium makes the term dominant. -/
theorem hKeep_at_740 : hKeep 740 := by decide

/-- The two hypotheses can never both hold at the same extinction. -/
theorem regimes_never_overlap (kappa : Nat) : ¬ (hDrop kappa ∧ hKeep kappa) :=
  fun h => Nat.lt_asymm h.1 h.2

/-- Both regimes exist, so the space is not vacuous. -/
theorem regimes_inhabited : ∃ klo khi : Nat, hKeep klo ∧ hDrop khi :=
  ⟨740, 74080, by decide, by decide⟩

/-- The split is sharp: every extinction is drop, keep, or exactly the threshold. -/
theorem threshold_exhausts_axis (kappa : Nat) : hDrop kappa ∨ hKeep kappa ∨ kappa = A := by
  rcases Nat.lt_trichotomy kappa A with h | h | h
  · exact Or.inr (Or.inl h)
  · exact Or.inr (Or.inr h)
  · exact Or.inl h

/-- A measurement decides the question: H_drop is refutable by one number. -/
theorem hDrop_is_refutable (kappa : Nat) : hKeep kappa → ¬ hDrop kappa :=
  fun hk hd => Nat.lt_asymm hd hk

#print axioms regimes_inhabited
#print axioms regimes_never_overlap
#print axioms threshold_exhausts_axis

end PossibilitySpace
