(*  possibility_gate.v

    The gate asks for a usable possibility space.  A space in prose can always
    be waved through, so this file makes it a finite object: sixteen worlds,
    four hypotheses about why the "dropped here" sentence exists, and proofs
    that (a) our world satisfies all four, (b) a world exists that satisfies
    none -- the fully measured world -- and (c) the three exculpating
    hypotheses together do NOT rescue the universal claim.

    The one hypothesis under which the information is FALSE is H4.  Its
    falsification test is a decidable function of a single number, kappa_R,
    with the threshold 7408 1/m taken from possibility_space.v.

    Compiled with:  rocq compile proofs/possibility_gate.v
*)

From Stdlib Require Import Arith Bool Ring List.
Import ListNotations.
Open Scope bool_scope.
Open Scope nat_scope.

Record World : Type := mkWorld {
  kappaInCode         : bool;
  vendorUnconditional : bool;
  tauComputed         : bool;
  deckUniversal       : bool
}.

(* H1: the sentence restates a published derivation. *)
Definition H1 (w : World) : Prop := vendorUnconditional w = false.
(* H2: the omission was never measured (no optical depth computed). *)
Definition H2 (w : World) : Prop := tauComputed w = false.
(* H3: the term could not be implemented (no extinction coefficient in code). *)
Definition H3 (w : World) : Prop := kappaInCode w = false.
(* H4: the sentence is false at this condition. *)
Definition H4 (w : World) : Prop := deckUniversal w = true.

(* Our world, as measured: no kappa in the Ada, no unconditional vendor claim,
   no optical depth in the thesis, and a slide that reads as a blanket claim. *)
Definition w0 : World := mkWorld false false false true.

Definition allWorlds : list World :=
  [
    mkWorld true true true true;
    mkWorld true true true false;
    mkWorld true true false true;
    mkWorld true true false false;
    mkWorld true false true true;
    mkWorld true false true false;
    mkWorld true false false true;
    mkWorld true false false false;
    mkWorld false true true true;
    mkWorld false true true false;
    mkWorld false true false true;
    mkWorld false true false false;
    mkWorld false false true true;
    mkWorld false false true false;
    mkWorld false false false true;
    mkWorld false false false false
  ].

Lemma space_has_sixteen_worlds : length allWorlds = 16.
Proof. reflexivity. Qed.

(* (a) Our world carries all four hypotheses at once. *)
Lemma our_world_holds_all : H1 w0 /\ H2 w0 /\ H3 w0 /\ H4 w0.
Proof. repeat split; reflexivity. Qed.

(* (b) The fully measured world satisfies none of them: there is no unearned
   sentence there to explain.  This is the counterexample to "every world
   satisfies at least one hypothesis". *)
Lemma measured_world_needs_no_hypothesis :
  exists w, ~ H1 w /\ ~ H2 w /\ ~ H3 w /\ ~ H4 w.
Proof.
  exists (mkWorld true true true false).
  repeat split; intro H; discriminate H.
Qed.

(* (c) Silence plus scoping plus an unimplemented term do NOT rescue the
   universal claim: a world exists where H1, H2, H3 hold and H4 still does. *)
Lemma exculpations_do_not_rescue :
  exists w, H1 w /\ H2 w /\ H3 w /\ H4 w.
Proof. exists w0. repeat split; reflexivity. Qed.

(* H1 alone is compatible with the claim being true. *)
Lemma scoped_source_alone_is_not_enough :
  exists w, H1 w /\ ~ H4 w.
Proof.
  exists (mkWorld false false false false).
  split. { reflexivity. }
  intro H. discriminate H.
Qed.

(* H4 is exactly the blanket-slide flag, so it dies when the slide is scoped. *)
Lemma H4_dies_when_scoped : forall w, deckUniversal w = false -> ~ H4 w.
Proof. intros w H. unfold H4. intro HH. rewrite H in HH. discriminate HH. Qed.

(* ---- the falsification test for H4: one number, kappa_R ---- *)

Definition threshold : nat := 74 * 100 + 8.
Definition refuted_by (kappa : nat) : bool := Nat.ltb threshold kappa.

Lemma test_is_decidable : forall k, refuted_by k = true \/ refuted_by k = false.
Proof. intro k. destruct (refuted_by k). left; reflexivity. right; reflexivity. Qed.

Lemma far_above_threshold_refutes : refuted_by (threshold * 10) = true.
Proof. reflexivity. Qed.

Lemma far_below_threshold_does_not : refuted_by (threshold / 10) = false.
Proof. reflexivity. Qed.

Lemma at_threshold_does_not_refute : refuted_by threshold = false.
Proof. reflexivity. Qed.

(* ---- the counting half, in the same scratchpad ---- *)

Lemma double_count_costs_one_copy : forall a b : nat, 2 * a + b = (a + b) + a.
Proof. intros. ring. Qed.

Lemma omission_costs_one_copy : forall a b : nat, a + b - b = a.
Proof. intros. apply Nat.add_sub. Qed.

Print Assumptions our_world_holds_all.
Print Assumptions exculpations_do_not_rescue.
Print Assumptions measured_world_needs_no_hypothesis.
Print Assumptions far_above_threshold_refutes.
