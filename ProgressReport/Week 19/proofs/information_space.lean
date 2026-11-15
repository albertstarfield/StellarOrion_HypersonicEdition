/-
  information_space.lean

  The gate asks a different question from the last file: not "which regime are
  we in", but "why does this sentence exist at all, and under which reading is
  it false".  So this file formalises the two readings of the deck's sentence

      "the Rosseland term is dropped here"

  as propositions over the extinction kappa, with A = 7408 1/m the threshold at
  T = 1348 K and k_gas = 0.1 W/(m K):

      scoped       : forall kappa, A < kappa -> hDrop kappa     (a conditional)
      universal    : forall kappa, hDrop kappa                  (a blanket claim)

  The first is what the vendor pages actually say, and it is provable.  The
  second is what the slide reads as, and it is FALSE: kappa = 740 refutes it.
  That is the hypothesis under which the information is false, and it is
  decided here rather than argued.

  Compiled with:  lean proofs/information_space.lean
-/

namespace InformationSpace

/-- Threshold extinction in 1/m at the illustrative design point. -/
def A : Nat := 7408

/-- The deck's sentence, read as a proposition about the extinction. -/
def hDrop (kappa : Nat) : Prop := A < kappa

/-- The falsifier: radiative conduction is not negligible. -/
def hKeep (kappa : Nat) : Prop := kappa < A

instance hDropDecidable (kappa : Nat) : Decidable (hDrop kappa) := Nat.decLt A kappa
instance hKeepDecidable (kappa : Nat) : Decidable (hKeep kappa) := Nat.decLt kappa A

/-- Reading 1, the scoped one the vendors license: true by construction. -/
theorem scoped_reading_holds : ∀ kappa : Nat, A < kappa → hDrop kappa :=
  fun _ h => h

/-- Reading 2, the blanket one the slide sounds like: false, with a witness. -/
theorem unconditional_reading_is_false : ¬ (∀ kappa : Nat, hDrop kappa) := by
  intro h
  have h740 : hDrop 740 := h 740
  exact absurd h740 (by decide)

/-- The two readings disagree at one concrete extinction, so they are not the
    same claim wearing different words. -/
theorem readings_disagree_at_740 : hKeep 740 ∧ ¬ hDrop 740 := by
  constructor
  · decide
  · decide

/-- No extinction makes both readings true, so the space has no overlap. -/
theorem no_kappa_satisfies_both (kappa : Nat) : ¬ (hDrop kappa ∧ hKeep kappa) :=
  fun h => Nat.lt_asymm h.1 h.2

#print axioms scoped_reading_holds
#print axioms unconditional_reading_is_false
#print axioms readings_disagree_at_740

end InformationSpace
