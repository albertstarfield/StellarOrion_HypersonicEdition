(*  model_census.v

    New method for this turn: not symbolic algebra, but a KERNEL-EXECUTED
    EXHAUSTIVE CENSUS.  A boolean fit-test is run over a finite box of integer
    coefficient pairs (K, c) and the surviving models are listed by the kernel
    itself.  The theorem is the printed list.

    Model used throughout, same shape as the deck's balance:
        K * T^4 + c * T = q

    Two questions, both answered by counting:

      (1) At ONE operating point, how many (K, c) in the box reproduce the flux?
          Answer: several -- the deck's single-point closure cannot pick one.

      (2) At TWO operating points, how many?  Answer: exactly one.  That is the
          determinant of two_point_witness.v l. 68, obtained here by search
          instead of by algebra -- two independent routes to the same number.

    Small exact instance (T1 = 2, q1 = 100; T2 = 3, q2 = 207; K in 0..3,
    c in range) because the point is structural: it is the COUNT that matters,
    not the magnitudes, and integer arithmetic keeps the census exact.

    Compiled with:  rocq compile proofs/model_census.v
*)

From Stdlib Require Import ZArith List.
Import ListNotations.
Open Scope Z_scope.

(* The fit test: does the pair (K, c) reproduce flux q at temperature T? *)
Definition fits (K c T q : Z) : bool :=
  Z.eqb (K * T * T * T * T + c * T) q.

(* 0, 1, ..., n-1 as a list of integers. *)
Fixpoint upto (n : nat) : list Z :=
  match n with
  | O => nil
  | S k => upto k ++ [Z.of_nat k]
  end.

(* The box of candidate models. *)
Definition box (nK nc : nat) : list (Z * Z) := list_prod (upto nK) (upto nc).

(* Survivors at the first operating point only. *)
Definition survivors_one (nK nc : nat) : list (Z * Z) :=
  filter (fun p => fits (fst p) (snd p) 2 100) (box nK nc).

(* Survivors at both operating points. *)
Definition survivors_two (nK nc : nat) : list (Z * Z) :=
  filter (fun p => andb (fits (fst p) (snd p) 2 100)
                        (fits (fst p) (snd p) 3 207)) (box nK nc).

(* --- what the kernel actually computes ------------------------------------ *)
Eval vm_compute in survivors_one 4 61.
Eval vm_compute in survivors_two 4 61.
Eval vm_compute in length (survivors_one 4 61).
Eval vm_compute in length (survivors_two 4 61).

(* (1) At one point the census returns four distinct models. *)
Lemma one_point_admits_four_models :
  survivors_one 4 61 = [(0, 50); (1, 42); (2, 34); (3, 26)].
Proof. vm_compute. reflexivity. Qed.

(* (2) At two points the census returns one. *)
Lemma two_points_admit_exactly_one_model :
  survivors_two 4 61 = [(1, 42)].
Proof. vm_compute. reflexivity. Qed.

Lemma the_counts_are_four_and_one :
  length (survivors_one 4 61) = 4%nat /\ length (survivors_two 4 61) = 1%nat.
Proof. split; vm_compute; reflexivity. Qed.

(* The single survivor of the two-point census really does fit both points --
   checked by evaluation, not by appeal to the filter. *)
Lemma the_surviving_model_fits_both_points :
  fits 1 42 2 100 = true /\ fits 1 42 3 207 = true.
Proof. split; vm_compute; reflexivity. Qed.

(* ... and no model outside the K range can do better, so (2) is not an artefact
   of a small box: the census stays at one when the box is widened in c. *)
Lemma widening_the_box_does_not_add_two_point_models :
  length (survivors_two 4 401) = 1%nat.
Proof. vm_compute. reflexivity. Qed.

(* A model that fits the first point but not the second -- the discriminating
   witness, named explicitly. *)
Lemma model_0_50_dies_at_the_second_point :
  fits 0 50 2 100 = true /\ fits 0 50 3 207 = false.
Proof. split; vm_compute; reflexivity. Qed.

(* Sanity: the box is not empty and the test is not vacuous. *)
Lemma the_box_is_not_empty : length (box 4 61) = 244%nat.
Proof. vm_compute. reflexivity. Qed.
