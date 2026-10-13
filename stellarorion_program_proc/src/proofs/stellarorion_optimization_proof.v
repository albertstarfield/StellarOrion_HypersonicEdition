(* ============================================================================
   AXIOMS / THEORIES / APPLICATIONS / CITATIONS
   Unit : StellarOrion_Optimization -- DoE and SBO objective
          (stellarorion_optimization.ads, stellarorion_optimization.adb)

   AXIOMS
     A1  The SBO objective is the weighted sum of two squared deviations,
         J = w_beta * Delta_Beta^2 + w_target * Delta_Y^2, where
         Delta_Beta = (Beta_Calc - Beta_Target) / 10.0 and
         Delta_Y = Y_Pred - Y_Target (stellarorion_optimization.adb:335-339).
     A2  The weights are declared non-negative by the Pre aspect
         (stellarorion_optimization.ads:109-110), which is the only
         hypothesis the objective's non-negativity requires.
     A3  The CCD centre point is the interval midpoint
         (stellarorion_optimization.ads:72-76).
     A4  The LHS stratum offset r is clamped into [0,1) by the body
         (stellarorion_optimization.adb:121-165), and the design space is
         partitioned into N equal strata of which one sample is drawn
         (Axiom 1 documented at stellarorion_optimization.adb:139-142).

   THEORIES
     T1  Optimization_Cost'Result >= 0.0 -- the declared Post aspect at
         stellarorion_optimization.ads:110.  A square is non-negative and
         the weights are non-negative, so both terms are non-negative and
         their sum is too.  This is the correctness anchor of the whole SBO
         loop: a cost that could go negative would make the running-minimum
         tracking meaningless.
     T2  CCD_Centre'Result lies inside [Param_Min, Param_Max] -- the
         declared Post aspect at :77-78.
     T3  LHS_Sample'Result lies inside the design space -- the declared Post
         aspect at :61-62.

   HONEST BOUNDARY
     The Ada header comment at stellarorion_optimization.adb:145-147 proves
     Theory 2 with "since 0 <= i + r < N", i.e. a ZERO-BASED stratum index,
     while the package signature declares Index : Positive (1 .. N).  Under
     the 1-based reading a sample at Index = N with r > 0 overshoots the
     interval, so T3 below is stated with the hypothesis the body actually
     relies on, (i + 1 <= N), and the spec/base mismatch is recorded here
     rather than hidden.  Resolving the 1-based Positive index against the
     0-based theory is a source change, not a proof change.

   APPLICATIONS
     Swept by src/utils/coq_proof_gate.py; a regression in the cost sign or
     the sampling bounds fails the build.

   CITATIONS
     [McKay1979] McKay, M.D., Beckman, R.J. & Conover, W.J., "A Comparison
         of Three Methods for Selecting Values of the Input Variables from
         a Computer Code", Technometrics 21(2), 1979, Eq. (2.1)
         -- https://doi.org/10.1080/00401706.1979.10490761
     [Goldberg1989] Goldberg, D.E., "Genetic Algorithms in Search,
         Optimization and Machine Learning", Addison-Wesley, 1989.
     [CoqRM] Coq Reference Manual, Coq.Reals.RIneq (Rmult_le_pos,
         Rmult_le_compat_l, Rmult_le_reg_l, Rinv_l, Rinv_0_lt_compat)
         -- https://coq.inria.fr/refman/
     [CoqMicromega] Coq Reference Manual, micromega plugin (Lra)
         -- https://coq.inria.fr/refman/addendum/micromega.html
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 helper -- a square is non-negative.  Sign case split: Rmult_le_pos
   needs both factors non-negative, and when x < 0 the product x * x equals
   the product of two non-negatives minus x. *)
Lemma sq_nonneg : forall x, 0 <= x * x.
Proof.
  intros x.
  destruct (Rle_lt_dec 0 x) as [H | H].
  - apply Rmult_le_pos; lra.
  - assert (Hneg : 0 <= - x) by lra.
    replace (x * x) with (- x * - x) by ring.
    apply Rmult_le_pos; lra.
Qed.

(* A1 helper -- cancel_mul: for a non-zero denominator, multiplying the
   quotient back recovers the numerator. *)
Section Cancel_Mul_Helper.
  Lemma cancel_mul : forall x l : R, l <> 0 -> l * (x / l) = x.
  Proof.
  intros x l Hne.
  unfold Rdiv.
  rewrite <- Rmult_assoc.
  rewrite (Rmult_comm l x).
  rewrite Rmult_assoc.
  rewrite (Rmult_comm l (/ l)).
  rewrite (Rinv_l l Hne).
  rewrite Rmult_1_r.
  reflexivity.
  Qed.
End Cancel_Mul_Helper.

(* A1 helper -- a quotient by a positive denominator is at most one when the
   numerator is at most the denominator. *)
Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

(* A1 -- the objective, mirroring the body at stellarorion_optimization.adb:335-339. *)
Definition optimization_cost
  (beta_calc beta_target y_pred y_target w_beta w_target : R) : R :=
  w_beta * (((beta_calc - beta_target) / 10) * ((beta_calc - beta_target) / 10))
  + w_target * ((y_pred - y_target) * (y_pred - y_target)).

(* T1 -- the declared Post aspect Optimization_Cost'Result >= 0.0
   (stellarorion_optimization.ads:110). *)
Lemma optimization_cost_nonneg :
  forall beta_calc beta_target y_pred y_target w_beta w_target,
  0 <= w_beta -> 0 <= w_target ->
  0 <= optimization_cost beta_calc beta_target y_pred y_target w_beta w_target.
Proof.
  intros b bt yp yt wb wt Hwb Hwt.
  unfold optimization_cost.
  assert (H1 : 0 <= wb * (((b - bt) / 10) * ((b - bt) / 10))).
  { apply Rmult_le_pos; [exact Hwb | apply sq_nonneg]. }
  assert (H2 : 0 <= wt * ((yp - yt) * (yp - yt))).
  { apply Rmult_le_pos; [exact Hwt | apply sq_nonneg]. }
  lra.
Qed.

(* A3 -- the CCD centre point is the interval midpoint
   (stellarorion_optimization.ads:72-76). *)
Definition ccd_centre (pmin pmax : R) : R := (pmin + pmax) / 2.

(* T2 -- the declared Post aspect CCD_Centre'Result in [Param_Min, Param_Max]
   (stellarorion_optimization.ads:77-78). *)
Lemma ccd_centre_in_range : forall pmin pmax, pmin <= pmax ->
  pmin <= ccd_centre pmin pmax /\ ccd_centre pmin pmax <= pmax.
Proof.
  intros pmin pmax H.
  unfold ccd_centre.
  split; lra.
Qed.

(* A4 -- the stratified LHS sample, mirroring the return expression at
   stellarorion_optimization.adb:163-164. *)
Definition lhs_sample (pmin pmax N i r : R) : R :=
  pmin + (pmax - pmin) * (i + r) / N.

(* T3a -- the sample never falls below the lower bound of the design space. *)
Lemma lhs_sample_lower : forall pmin pmax N i r,
  0 <= pmax - pmin -> 0 < N -> 0 <= i -> 0 <= r ->
  pmin <= lhs_sample pmin pmax N i r.
Proof.
  intros pmin pmax N i r Hpm HN Hi Hr.
  assert (Hinv : 0 < / N) by (apply Rinv_0_lt_compat; exact HN).
  apply Rlt_le in Hinv.
  assert (Hf : 0 <= (i + r) / N).
  { unfold Rdiv. apply Rmult_le_pos; [lra | exact Hinv]. }
  assert (Hm : 0 <= (pmax - pmin) * ((i + r) / N)).
  { apply Rmult_le_pos; [exact Hpm | exact Hf]. }
  unfold lhs_sample. lra.
Qed.

(* T3b -- the sample never exceeds the upper bound of the design space.  The
   stratum offset is strictly below one and the stratum index is the last
   one, so the whole design space is covered exactly once. *)
Lemma lhs_sample_upper : forall pmin pmax N i r,
  pmin <= pmax -> 0 < N -> 0 <= i -> i + 1 <= N -> 0 <= r -> r < 1 ->
  lhs_sample pmin pmax N i r <= pmax.
Proof.
  intros pmin pmax N i r Hpm HN Hi Hin Hr Hr1.
  assert (Hf : (i + r) / N <= 1).
  { apply rdiv_le_1; [lra | lra]. }
  assert (Hpm' : 0 <= pmax - pmin) by lra.
  assert (Hm : (pmax - pmin) * ((i + r) / N) <= (pmax - pmin) * 1).
  { apply Rmult_le_compat_l; [exact Hpm' | exact Hf]. }
  rewrite Rmult_1_r in Hm.
  unfold lhs_sample. lra.
Qed.
