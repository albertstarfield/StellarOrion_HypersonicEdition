(* ============================================================================
   StellarOrion_HypersonicEdition -- Coq proof of the CCD sensitivity layer.

   Proved properties of StellarOrion_Sensitivity
   (src/simulation_engine/stellarorion_sensitivity.ads / .adb).

   AXIOMS
   A1 The screen is the rotatable central composite design for k = 3 factors:
      2^k = 8 factorial corners at coded +-1, 1 centre, 2k = 6 axial points at
      coded +-alpha with alpha = 2^(k/4) = 2^(3/4), which is exactly the
      rotatability condition (alpha^4 = 2^k).  The estimators do not depend on
      the VALUE of alpha beyond its positivity, so alpha is a parameter here.
   A2 Canonical layout (stellarorion_sensitivity.ads): points 1..8 are the
      factorial corners in binary order with the LAST factor least
      significant; point 9 is the centre; points 10..15 are the axial pairs
      (10,11), (12,13), (14,15).  Factor 1's + set is {5,6,7,8} and its - set
      {1,2,3,4}; factor 2: + {3,4,7,8}, - {1,2,5,6}; factor 3: + {2,4,6,8},
      - {1,3,5,7}.
   A3 A factor whose axial contrast vanishes has, to first order and inside
      the design box, no influence on the response.  A contrast says nothing
      about interactions, which is why the corner estimator is proved
      alongside rather than merged.

   THEORIES
   T1 The estimators are LINEAR in the 15 responses, hence additive
      (swing_additive, corner_additive) and exactly calibrated by a
      discontinuation argument (corner_magnitude).
   T2 A CONSTANT response must produce a zero contrast for every estimator;
      that is the unbiasedness condition (corner_constant).  The magnitude
      theorem is the one that actually pins the scale down, because
      corner_constant alone is satisfied by ANY halved or doubled estimator.
   T3 The corner set's order is irrelevant (corner_comm), so the factorial
      main effect does not depend on how the generator orders its corners.
   T4 Dominance: the argmax of the absolute effects really dominates every
      factor (dom_covers), which is the Ada Dominant_Factor postcondition.

   APPLICATIONS
   AP-1 This is the machine-checked part of the sensitivity ranking
      reported for the closed-form cost J.  See sensitivity_ranking_todo.md
      for the provenance boundary: the objective actually optimised is the
      TOTAL HEAT FLUX, and the cited source's objective (its Eq. 5.16) is
      total mass with composite objectives explicitly declined -- only its
      design-space bounds are borrowed.
   AP-2 The ranking the Ada unit produced on the recorded screen is
      r_tor > R_N > half_cone_deg on both estimators (axial swings
      3.520005 / 23.041132 / 0.034212; corner mean effects
      10.5453 / 11.1575 / 7.3370), invariant across every candidate flight
      condition.  Those numbers are a MEASUREMENT on the closed form; the
      theorems here prove the ESTIMATOR's properties, not those values.

   WHAT IS NOT PROVED HERE
   * Rank_Factors returning a permutation of 1..3 is discharged in Ada by
      construction (its postcondition states it and GNATprove verifies it
      against the unrolled pairwise comparison).  It is not re-proved in Coq.
   * The quadratic response surface, Cholesky factorisation and its Fit_Failed
      flag are NOT in this file: that is Tier 2 and is not yet built in Ada
      either.  Only the design-native estimates exist.

   CITATIONS
   [Montgomery17] Montgomery, D. C., "Design and Analysis of Experiments",
                  8th ed., Wiley, 2017 -- CCD, rotatability, main effects.
                  https://www.wiley.com/en-us/Design+and+Analysis+of+Experiments%2C+8th+Edition-p-9781119320937
   [AdaRM]        ISO/IEC 8652:2012 -- the Ada unit whose contracts this file
                  mirrors.
   [SPARKRM]      SPARK 2014 Reference Manual -- pragma SPARK_Mode,
                  pre/post obligations verified by GNATprove --level=4.
   [Rap23]        Rapisarda, V., TU Delft 2023 -- Eq. (5.16) objective and
                  Table 5.4 bounds, cited only for the boundary in AP-1.
                  local copy: Lost+Found/ProgressReport/paperRef/
                  MDAOofInflatableStackedToroids_ClaudioRapisarda.pdf

   NOTE ON SCOPE: R scope is open for the whole file.  Every response, sum
   and estimator is a real; the design-point indices stay nat because their
   expected type is nat wherever they appear.  A bare list literal needs no
   annotation, but a nat-bound comparison inside an R-scoped statement does.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
Require Import Coq.Lists.List.
Import ListNotations.
Local Open Scope R_scope.

Fixpoint csum (y : nat -> R) (l : list nat) : R :=
  match l with nil => 0 | p :: ps => y p + csum y ps end.

Definition corner_effect (y : nat -> R) (plus minus : list nat) : R :=
  csum y plus / 4 - csum y minus / 4.
Definition axial_swing (y : nat -> R) (p q : nat) : R := y p - y q.
Definition axial_grad (y : nat -> R) (p q : nat) (a h : R) : R :=
  (y p - y q) / (2 * a * h).

Definition pickset := (5 :: 6 :: 7 :: 8 :: nil)%nat.
Definition minset  := (1 :: 2 :: 3 :: 4 :: nil)%nat.

Lemma csum_app : forall y a b, csum y (a ++ b) = csum y a + csum y b.
Proof. induction a as [|x a IH]; simpl; intros; [lra | rewrite IH; lra]. Qed.

Lemma csum_add : forall y1 y2 l,
  csum (fun n => y1 n + y2 n) l = csum y1 l + csum y2 l.
Proof. induction l as [|p ps IH]; simpl; [lra | rewrite IH; lra]. Qed.

Lemma swing_additive : forall y1 y2 p q,
  axial_swing (fun n => y1 n + y2 n) p q
  = axial_swing y1 p q + axial_swing y2 p q.
Proof. intros. unfold axial_swing. lra. Qed.

Lemma swing_antisym : forall y p q, axial_swing y q p = - axial_swing y p q.
Proof. intros. unfold axial_swing. lra. Qed.

Lemma corner_additive : forall y1 y2 plus minus,
  corner_effect (fun n => y1 n + y2 n) plus minus
  = corner_effect y1 plus minus + corner_effect y2 plus minus.
Proof.
  intros. unfold corner_effect.
  rewrite (csum_add y1 y2 plus), (csum_add y1 y2 minus). lra.
Qed.

Lemma corner_comm : forall y a b,
  corner_effect y (a ++ b) nil - corner_effect y (b ++ a) nil = 0.
Proof.
  intros. unfold corner_effect. simpl.
  rewrite !csum_app. lra.
Qed.

Lemma corner_constant : forall c,
  corner_effect (fun _ => c) pickset minset = 0.
Proof. intros. unfold corner_effect, csum. simpl. lra. Qed.

Lemma corner_magnitude :
  corner_effect (fun n => match n with 5 => 4 | 6 => 4 | 7 => 4 | 8 => 4
                                  | _ => 0 end) pickset minset = 4.
Proof. intros. unfold corner_effect, csum. simpl. lra. Qed.

Lemma gradient_pos : forall y p q a h,
  0 < a -> 0 < h -> 0 < axial_swing y p q ->
  0 < axial_grad y p q a h.
Proof.
  intros y p q a h Ha Hh Hs. unfold axial_grad, axial_swing in *.
  assert (Hden : 0 < 2 * a * h).
  { apply Rmult_lt_0_compat; lra. }
  apply Rdiv_lt_0_compat; [exact Hs | exact Hden].
Qed.

(* pick the i-th of three, 1-based; anything else falls through to the third *)
Definition pick3 (i : nat) (a b c : R) : R :=
  match i with 1 => a | 2 => b | _ => c end.

(* unrolled argmax over three reals -- mirrors the Ada Dominant_Factor *)
Definition dom3 (a b c : R) : nat :=
  if Rlt_dec a b then (if Rlt_dec b c then 3 else 2)
  else if Rlt_dec a c then 3 else 1.

Definition abspick (i : nat) (e1 e2 e3 : R) : R :=
  Rabs (pick3 i (Rabs e1) (Rabs e2) (Rabs e3)).

Lemma covers_1 : forall e1 e2 e3 : R,
  Rabs e1 <= abspick (dom3 (Rabs e1) (Rabs e2) (Rabs e3)) e1 e2 e3.
Proof.
  intros e1 e2 e3.
  assert (H1 : 0 <= Rabs e1) by apply Rabs_pos.
  assert (H2 : 0 <= Rabs e2) by apply Rabs_pos.
  assert (H3 : 0 <= Rabs e3) by apply Rabs_pos.
  unfold abspick, dom3, pick3.
  destruct (Rlt_dec (Rabs e1) (Rabs e2)) as [H12|H12].
  - destruct (Rlt_dec (Rabs e2) (Rabs e3)) as [H23|H23].
    + rewrite (Rabs_pos_eq (Rabs e3) H3). lra.
    + rewrite (Rabs_pos_eq (Rabs e2) H2). lra.
  - destruct (Rlt_dec (Rabs e1) (Rabs e3)) as [H13|H13].
    + rewrite (Rabs_pos_eq (Rabs e3) H3). lra.
    + rewrite (Rabs_pos_eq (Rabs e1) H1). apply Rle_refl.
Qed.

Lemma covers_2 : forall e1 e2 e3 : R,
  Rabs e2 <= abspick (dom3 (Rabs e1) (Rabs e2) (Rabs e3)) e1 e2 e3.
Proof.
  intros e1 e2 e3.
  assert (H1 : 0 <= Rabs e1) by apply Rabs_pos.
  assert (H2 : 0 <= Rabs e2) by apply Rabs_pos.
  assert (H3 : 0 <= Rabs e3) by apply Rabs_pos.
  unfold abspick, dom3, pick3.
  destruct (Rlt_dec (Rabs e1) (Rabs e2)) as [H12|H12].
  - destruct (Rlt_dec (Rabs e2) (Rabs e3)) as [H23|H23].
    + rewrite (Rabs_pos_eq (Rabs e3) H3). lra.
    + rewrite (Rabs_pos_eq (Rabs e2) H2). apply Rle_refl.
  - destruct (Rlt_dec (Rabs e1) (Rabs e3)) as [H13|H13].
    + rewrite (Rabs_pos_eq (Rabs e3) H3). lra.
    + assert (Hn : Rabs e2 <= Rabs e1) by lra.
      rewrite (Rabs_pos_eq (Rabs e1) H1). exact Hn.
Qed.

Lemma covers_3 : forall e1 e2 e3 : R,
  Rabs e3 <= abspick (dom3 (Rabs e1) (Rabs e2) (Rabs e3)) e1 e2 e3.
Proof.
  intros e1 e2 e3.
  assert (H1 : 0 <= Rabs e1) by apply Rabs_pos.
  assert (H2 : 0 <= Rabs e2) by apply Rabs_pos.
  assert (H3 : 0 <= Rabs e3) by apply Rabs_pos.
  unfold abspick, dom3, pick3.
  destruct (Rlt_dec (Rabs e1) (Rabs e2)) as [H12|H12].
  - destruct (Rlt_dec (Rabs e2) (Rabs e3)) as [H23|H23].
    + rewrite (Rabs_pos_eq (Rabs e3) H3). apply Rle_refl.
    + assert (Hn : Rabs e3 <= Rabs e2) by lra.
      rewrite (Rabs_pos_eq (Rabs e2) H2). exact Hn.
  - destruct (Rlt_dec (Rabs e1) (Rabs e3)) as [H13|H13].
    + rewrite (Rabs_pos_eq (Rabs e3) H3). apply Rle_refl.
    + assert (Hn : Rabs e3 <= Rabs e1) by lra.
      rewrite (Rabs_pos_eq (Rabs e1) H1). exact Hn.
Qed.

Lemma dom_covers : forall e1 e2 e3 : R,
  Rabs e1
    <= abspick (dom3 (Rabs e1) (Rabs e2) (Rabs e3)) e1 e2 e3
  /\ Rabs e2
    <= abspick (dom3 (Rabs e1) (Rabs e2) (Rabs e3)) e1 e2 e3
  /\ Rabs e3
    <= abspick (dom3 (Rabs e1) (Rabs e2) (Rabs e3)) e1 e2 e3.
Proof.
  intros e1 e2 e3.
  split; [exact (covers_1 e1 e2 e3) |].
  split; [exact (covers_2 e1 e2 e3) | exact (covers_3 e1 e2 e3)].
Qed.
