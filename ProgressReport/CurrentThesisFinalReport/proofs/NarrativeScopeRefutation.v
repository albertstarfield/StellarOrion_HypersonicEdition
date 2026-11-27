(* PROVE REFUTATION: concrete counterexample to "every appendix section is
   described in Chapter 2 first". *)
Inductive section :=
  | Ch2Knudsen
  | AppB3GnatproveDischarge.

Definition InAppendix (s : section) : Prop :=
  match s with
  | AppB3GnatproveDischarge => True
  | _ => False
  end.

Definition DescribedInCh2 (s : section) : Prop :=
  match s with
  | Ch2Knudsen => True
  | AppB3GnatproveDischarge => False
  end.

Definition AllAppendixDescribed : Prop :=
  forall s : section, InAppendix s -> DescribedInCh2 s.

Definition witness : section := AppB3GnatproveDischarge.

Lemma witness_in_appendix : InAppendix witness.
Proof. simpl. trivial. Qed.

Lemma witness_not_described : ~ DescribedInCh2 witness.
Proof. simpl. intro H. exact H. Qed.

Lemma refutation : ~ AllAppendixDescribed.
Proof.
  intro H.
  apply witness_not_described.
  apply H.
  apply witness_in_appendix.
Qed.