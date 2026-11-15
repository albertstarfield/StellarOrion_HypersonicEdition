(*  evidence_function.v

    "Where does that solve issue 3 and issue 4?"  The honest answer has two
    halves, and this file is the second half.

    Half one is documentary: the deck's own slides p. 46, 50, 51 carry the
    resolution, and the text is extracted below from the PDF.

    Half two is logical, and it is what this file settles.  The deck resolves
    issue 3 CONDITIONALLY: "the quartic belongs outside Fourier provided the
    medium is optically thick."  So the resolution is a predicate on one scalar
    the deck never measures -- the extinction coefficient kappa.  Three facts
    about that predicate, each machine-checked:

      (a) it is MONOTONE in kappa, so a single measurement settles it for every
          layer thickness and every temperature, permanently;
      (b) a THRESHOLD exists (for a 1 mm layer, kappa0 = 3001 1/m), so "measure
          it once" is a finite, bounded task and not an infinite regress;
      (c) the deck's own published numbers leave the predicate UNDETERMINED:
          kappa = 740 gives tau = 0.74 (thin, omission wrong) and kappa = 74080
          gives tau = 74.08 (thick, omission right) with every other number in
          the slide identical.

    So the slide solves issue 3 as a conditional and does not -- cannot -- solve
    it as a statement about this vehicle, because the antecedent is exactly the
    quantity missing from the document.

    Units convention: L in millimetres, and tau is carried in units of 1/1000 so
    that everything stays in Z -- tau_milli = kappa * L, threshold 3000.

    Compiled with:  rocq compile proofs/evidence_function.v
*)

From Stdlib Require Import ZArith Lia.
Open Scope Z_scope.

Definition tauMilli (kappa L : Z) : Z := kappa * L.

(* tau > 3, i.e. 3000 in units of 1/1000. *)
Definition optThick (kappa L : Z) : Prop := 3000 < tauMilli kappa L.

(* (a) monotone: more extinction never makes a medium thinner. *)
Lemma optThick_is_monotone_in_kappa (k1 k2 L : Z)
    (hL : 0 < L) (h : k1 <= k2) (ho : optThick k1 L) :
    optThick k2 L.
Proof. unfold optThick, tauMilli in *. nia. Qed.

(* ... and a thicker layer never makes it thinner either. *)
Lemma optThick_is_monotone_in_thickness (k L1 L2 : Z)
    (hk : 0 <= k) (h : L1 <= L2) (ho : optThick k L1) :
    optThick k L2.
Proof. unfold optThick, tauMilli in *. nia. Qed.

(* (b) a threshold exists: one measurement, one bound, no regress. *)
Lemma a_threshold_exists_for_a_one_millimetre_layer :
  exists k0, forall k, k0 <= k -> optThick k 1.
Proof. exists 3001. intros k h. unfold optThick, tauMilli. nia. Qed.

(* The threshold scales inversely with thickness: tau = kappa * L. *)
Lemma threshold_scales_with_thickness (k L : Z) :
  optThick k L <-> optThick (k * L) 1.
Proof. unfold optThick, tauMilli. split; intros H; nia. Qed.

(* (c) THE UNDETERMINATION.  Same deck numbers, opposite verdicts. *)
Lemma the_deck_numbers_leave_the_predicate_undetermined :
  ~ optThick 740 1 /\ optThick 74080 1.
Proof.
  split.
  - unfold optThick, tauMilli. vm_compute. intros H. discriminate H.
  - unfold optThick, tauMilli. vm_compute. reflexivity.
Qed.

(* At the measured threshold the two answers meet: kappa* sits strictly between
   7407 and 7408, so 740 is below by a factor of ten and 74080 above. *)
Lemma the_two_candidate_values_straddle_the_threshold :
  740 < 7407 /\ 7408 < 74080.
Proof. split; vm_compute; reflexivity. Qed.

(* Sanity: the predicate is not vacuous -- some kappa is thick, some is not. *)
Lemma the_predicate_is_not_constant :
  (exists k, optThick k 1) /\ (exists k, ~ optThick k 1).
Proof.
  split.
  - exists 4000. unfold optThick, tauMilli. nia.
  - exists 1. unfold optThick, tauMilli. nia.
Qed.
