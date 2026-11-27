(* Narrative scope rule for the Rev_Nov27_2026.md decision. *)
Inductive topic :=
  | KnudsenRegime
  | ViscousEntropy
  | FrameworkChain
  | GnatproveTables
  | LeanRocqIdentities
  | PanelProvenance.

Definition in_appendix (t : topic) : bool :=
  match t with
  | GnatproveTables => true
  | LeanRocqIdentities => true
  | PanelProvenance => true
  | _ => false
  end.

Definition described_in_chapter (t : topic) : bool :=
  match t with
  | KnudsenRegime => true
  | ViscousEntropy => true
  | FrameworkChain => true
  | GnatproveTables => true
  | LeanRocqIdentities => true
  | PanelProvenance => true
  end.

Lemma scope_rule_holds : forall t, in_appendix t = true -> described_in_chapter t = true.
Proof.
  intros t H.
  destruct t; simpl in H; try discriminate; simpl; reflexivity.
Qed.