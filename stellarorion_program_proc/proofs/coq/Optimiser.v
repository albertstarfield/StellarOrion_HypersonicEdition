(* =====================================================================
   StellarOrion optimiser — Coq/Rocq companion to the Lean 4 proofs.

   AXIOMS
     A1  The composite cost J is a sum of two non-negative weighted squares:
         J = w_beta * d_beta^2 + w_target * d_y^2 with w >= 0.
     A2  J vanishes exactly when both weighted terms vanish.
     A3  Elitism: the next generation carries the current best individual, so
         the best cost of an elitist run never increases.
     A4  The coded 2^3 factorial design is centred and orthogonal, hence the
         closed-form contrast fit is exact: it reproduces every response that
         is linear in the coded factors.
     A5  The 15-point central composite design is centrally symmetric.

   THEORIES
     T1  (Gauss 1809) A sum of non-negative terms is non-negative, and it
         vanishes only when every term vanishes.
     T2  (Goldberg 1989, Ch. 3) Elitism makes the best-cost sequence
         monotonically non-increasing.
     T3  (McKay et al. 1979; Montgomery 2017, Ch. 6) A centred orthogonal
         design decouples the mean from the contrasts, so the contrast fit
         reproduces a linear response exactly.

   CITATIONS
     - Gauss, C.F. (1809), "Theoria Motus Corporum Coelestium".
     - Goldberg, D.E. (1989), "Genetic Algorithms in Search, Optimization and
       Machine Learning", Addison-Wesley, Ch. 3.
     - McKay, D. et al. (1979), Technometrics 21(2), 239-248.
     - Montgomery, D.C. (2017), "Design and Analysis of Experiments", 9th ed.

   MODEL NOTE
     The Ada/SPARK implementation evaluates J on bounded Float values; the
     statements below are the exact real-number versions of the same algebra
     (the beta delta is scaled by 1/10 in the Ada code, which is a positive
     factor and therefore changes neither the sign nor the vanishing
     condition).
   ===================================================================== *)

Require Import Reals.
Require Import Lra.
Require Import Psatz.
Require Import Field.
Require Import List.
Require Import Arith.
Require Import Lia.
Import ListNotations.
Open Scope R_scope.

(* =====================================================================
   1. The composite cost
   ===================================================================== *)

Definition cost (wBeta wTarget dBeta dY : R) : R :=
  wBeta * (dBeta * dBeta) + wTarget * (dY * dY).

(* AXIOM A1: the cost is never negative. *)
Lemma cost_nonneg : forall wBeta wTarget dBeta dY : R,
  0 <= wBeta -> 0 <= wTarget -> 0 <= cost wBeta wTarget dBeta dY.
Proof.
  intros w1 w2 d1 d2 H1 H2. unfold cost.
  assert (A : 0 <= d1 * d1) by nra.
  assert (B : 0 <= d2 * d2) by nra.
  assert (C : 0 <= w1 * (d1 * d1)) by (apply (Rmult_le_pos w1 (d1 * d1)); assumption).
  assert (D : 0 <= w2 * (d2 * d2)) by (apply (Rmult_le_pos w2 (d2 * d2)); assumption).
  lra.
Qed.

(* AXIOM A2: the cost vanishes exactly when both weighted terms vanish. *)
Lemma cost_zero_iff : forall wBeta wTarget dBeta dY : R,
  0 <= wBeta -> 0 <= wTarget ->
  (cost wBeta wTarget dBeta dY = 0 <->
   (wBeta * (dBeta * dBeta) = 0 /\ wTarget * (dY * dY) = 0)).
Proof.
  intros w1 w2 d1 d2 H1 H2. unfold cost.
  assert (A : 0 <= d1 * d1) by nra.
  assert (B : 0 <= d2 * d2) by nra.
  assert (C : 0 <= w1 * (d1 * d1)) by (apply (Rmult_le_pos w1 (d1 * d1)); assumption).
  assert (D : 0 <= w2 * (d2 * d2)) by (apply (Rmult_le_pos w2 (d2 * d2)); assumption).
  split.
  - intro H. lra.
  - intros [H1' H2']. lra.
Qed.

(* A weighted square term vanishes only if its weight or its delta is zero. *)
Lemma cost_zero_weight_or_delta : forall wBeta wTarget dBeta dY : R,
  0 <= wBeta -> 0 <= wTarget -> cost wBeta wTarget dBeta dY = 0 ->
  (wBeta = 0 \/ dBeta = 0) /\ (wTarget = 0 \/ dY = 0).
Proof.
  intros w1 w2 d1 d2 H1 H2 Hc.
  apply (proj1 (cost_zero_iff w1 w2 d1 d2 H1 H2)) in Hc.
  destruct Hc as [Hc1 Hc2].
  split.
  - apply Rmult_integral in Hc1.
    destruct Hc1 as [Hc1 | Hc1].
    + left; exact Hc1.
    + apply Rmult_integral in Hc1.
      destruct Hc1 as [Hc1 | Hc1].
      * right; exact Hc1.
      * right; exact Hc1.
  - apply Rmult_integral in Hc2.
    destruct Hc2 as [Hc2 | Hc2].
    + left; exact Hc2.
    + apply Rmult_integral in Hc2.
      destruct Hc2 as [Hc2 | Hc2].
      * right; exact Hc2.
      * right; exact Hc2.
Qed.

(* The converse: both deltas vanishing makes the cost vanish. *)
Lemma cost_zero_of_zero_deltas : forall wBeta wTarget dBeta dY : R,
  dBeta = 0 -> dY = 0 -> cost wBeta wTarget dBeta dY = 0.
Proof.
  intros w1 w2 d1 d2 H1 H2. unfold cost. subst. ring.
Qed.

(* =====================================================================
   2. Elitism
   ===================================================================== *)

(* The nat comparison, explicit: the real scope is open for the cost
   lemmas above, so the bare <= notation would resolve to Rle. *)
Notation "x <=nat y" := (Nat.le x y) (at level 70).

Fixpoint listMin (l : list nat) (acc : nat) : nat :=
  match l with
  | [] => acc
  | a :: t => listMin t (Nat.min acc a)
  end.

Lemma listMin_ge : forall (l : list nat) (acc : nat),
  (forall c, In c l -> acc <=nat c) -> acc <=nat listMin l acc.
Proof.
  intros l. induction l as [|a t IH]; intros acc H; simpl.
  - apply Nat.le_refl.
  - assert (Ha : acc <=nat a) by (apply H; left; reflexivity).
    assert (Ht : forall c, In c t -> acc <=nat c)
      by (intros c Hc; apply H; right; exact Hc).
    rewrite (Nat.min_l acc a Ha). apply IH. exact Ht.
Qed.

Lemma listMin_eq_of_ge : forall (l : list nat) (best : nat),
  (forall c, In c l -> best <=nat c) -> listMin l best = best.
Proof.
  intros l. induction l as [|a t IH]; intros best H; simpl.
  - reflexivity.
  - assert (Ha : best <=nat a) by (apply H; left; reflexivity).
    assert (Ht : forall c, In c t -> best <=nat c)
      by (intros c Hc; apply H; right; exact Hc).
    rewrite (Nat.min_l best a Ha). apply IH. exact Ht.
Qed.

(* AXIOM A3 / THEORY T2: elitism.  The next generation starts with the
   current best individual and no individual is cheaper than the current
   best, so the best cost cannot increase. *)
Lemma elitism_preserves_best : forall (best : nat) (costs : list nat),
  hd_error costs = Some best ->
  (forall c, In c (tl costs) -> best <=nat c) ->
  listMin costs best = best.
Proof.
  intros best costs Hhd Htl.
  destruct costs as [|a rest]; simpl in Hhd.
  - discriminate.
  - injection Hhd as Hhd; subst a.
    assert (Hrest : forall c, In c rest -> best <=nat c).
    { intros c Hc. apply Htl. simpl. exact Hc. }
    simpl. rewrite (Nat.min_l best best (Nat.le_refl best)).
    apply listMin_eq_of_ge. exact Hrest.
Qed.

(* The best-cost sequence of an elitist run is non-increasing. *)
Lemma elitism_best_nonincreasing : forall (best : nat) (costs : list nat),
  hd_error costs = Some best ->
  (forall c, In c (tl costs) -> best <=nat c) ->
  listMin costs best <=nat best.
Proof.
  intros best costs H1 H2.
  rewrite (elitism_preserves_best best costs H1 H2).
  apply Nat.le_refl.
Qed.

(* =====================================================================
   3. The coded design and the contrast fit
   ===================================================================== *)

(* The coded 2^3 factorial design: the sign of factor k at point i. *)
Definition xsign (i k : nat) : R :=
  match k, i with
  | 0, 0 => 1 | 0, 1 => 1 | 0, 2 => 1 | 0, 3 => 1
  | 0, 4 => -1 | 0, 5 => -1 | 0, 6 => -1 | 0, _ => -1
  | 1, 0 => 1 | 1, 1 => 1 | 1, 2 => -1 | 1, 3 => -1
  | 1, 4 => 1 | 1, 5 => 1 | 1, 6 => -1 | 1, _ => -1
  | 2, 0 => 1 | 2, 1 => -1 | 2, 2 => 1 | 2, 3 => -1
  | 2, 4 => 1 | 2, 5 => -1 | 2, 6 => 1 | 2, _ => -1
  | _, _ => 0
  end.

Definition sum8 (f : nat -> R) : R :=
  f 0%nat + f 1%nat + f 2%nat + f 3%nat + f 4%nat + f 5%nat + f 6%nat + f 7%nat.

(* A response that is exactly linear in the coded factors. *)
Definition ylist (c0 c1 c2 c3 : R) (i : nat) : R :=
  c0 + c1 * xsign i 0%nat + c2 * xsign i 1%nat + c3 * xsign i 2%nat.

(* The closed-form contrast fit of the proved Ada/SPARK core:
   b0 = sum(y)/8, bk = sum(x_k * y)/8. *)
Definition s0 (c0 c1 c2 c3 : R) : R := sum8 (ylist c0 c1 c2 c3).
Definition sk (k : nat) (c0 c1 c2 c3 : R) : R :=
  sum8 (fun i => xsign i k * ylist c0 c1 c2 c3 i).
Definition yhat (c0 c1 c2 c3 : R) (i : nat) : R :=
  (s0 c0 c1 c2 c3
   + sk 0%nat c0 c1 c2 c3 * xsign i 0%nat
   + sk 1%nat c0 c1 c2 c3 * xsign i 1%nat
   + sk 2%nat c0 c1 c2 c3 * xsign i 2%nat) / 8.

(* AXIOM A4 / THEORY T3: the contrast fit reproduces a linear response
   exactly, at every design point. *)
Lemma fit_exact : forall c0 c1 c2 c3 i,
  yhat c0 c1 c2 c3 i = ylist c0 c1 c2 c3 i.
Proof.
  intros c0 c1 c2 c3 i.
  destruct i as [|[|[|[|[|[|[|i]]]]]]];
    unfold yhat, s0, sk, ylist, sum8; simpl; field; ring.
Qed.

(* The fit preserves the grand mean. *)
Lemma fit_preserves_mean : forall c0 c1 c2 c3,
  sum8 (yhat c0 c1 c2 c3) = sum8 (ylist c0 c1 c2 c3).
Proof.
  intros c0 c1 c2 c3. unfold sum8.
  rewrite (fit_exact c0 c1 c2 c3 0), (fit_exact c0 c1 c2 c3 1),
          (fit_exact c0 c1 c2 c3 2), (fit_exact c0 c1 c2 c3 3),
          (fit_exact c0 c1 c2 c3 4), (fit_exact c0 c1 c2 c3 5),
          (fit_exact c0 c1 c2 c3 6), (fit_exact c0 c1 c2 c3 7).
  reflexivity.
Qed.

(* The fit preserves every paired contrast. *)
Lemma fit_preserves_contrast : forall c0 c1 c2 c3 k,
  sum8 (fun i => xsign i k * yhat c0 c1 c2 c3 i) =
  sum8 (fun i => xsign i k * ylist c0 c1 c2 c3 i).
Proof.
  intros c0 c1 c2 c3 k. unfold sum8.
  rewrite (fit_exact c0 c1 c2 c3 0), (fit_exact c0 c1 c2 c3 1),
          (fit_exact c0 c1 c2 c3 2), (fit_exact c0 c1 c2 c3 3),
          (fit_exact c0 c1 c2 c3 4), (fit_exact c0 c1 c2 c3 5),
          (fit_exact c0 c1 c2 c3 6), (fit_exact c0 c1 c2 c3 7).
  reflexivity.
Qed.

(* AXIOM A4: the coded design is centred. *)
Lemma design_centred : forall j : nat, Nat.le j 2 ->
  sum8 (fun i => xsign i j) = 0.
Proof.
  intros j Hj. destruct j as [|[|[|j]]]; try lia;
    unfold sum8, xsign; simpl; ring.
Qed.

(* AXIOM A4: the coded design is orthogonal (8 on the diagonal, 0 off it). *)
Lemma design_self : forall j : nat, Nat.le j 2 ->
  sum8 (fun i => xsign i j * xsign i j) = 8.
Proof.
  intros j Hj. destruct j as [|[|[|j]]]; try lia;
    unfold sum8, xsign; simpl; ring.
Qed.

Lemma design_cross : forall j k : nat, Nat.le j 2 -> Nat.le k 2 -> j <> k ->
  sum8 (fun i => xsign i j * xsign i k) = 0.
Proof.
  intros j k Hj Hk Hne.
  destruct j as [|[|[|j]]]; destruct k as [|[|[|k]]]; try lia;
    try (exfalso; apply Hne; reflexivity);
    unfold sum8, xsign; simpl; ring.
Qed.

(* =====================================================================
   4. Central composite design

   The 15-point central composite design is centrally symmetric; that
   property is proved in the Lean 4 companion (`StellarOrionProofs/Design.lean`,
   theorem `ccd_central_symmetry`), where the design is a concrete list and
   the check is a kernel decision.
   ===================================================================== *)
