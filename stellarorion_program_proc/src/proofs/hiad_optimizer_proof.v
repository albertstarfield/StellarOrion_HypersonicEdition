(* ============================================================================
   Coq proof companion for src/python/hiad_optimizer.py

   AXIOM (O1) [bounded multiplicative bias]:
        raw = q_hybrid / q_analytic,   c = clamp(raw, 0.5, 2.0),
   with 0.5 = _GATE_CORR_MIN and 2.0 = _GATE_CORR_MAX (AXIOM A5). The
   correction factor is the first-order discrepancy term of a two-level
   Kennedy & O'Hagan calibration, clamped so that one pathological
   simulation cannot make round 2 minimize nonsense.
   AXIOM (O2) [gate predicate, AXIOM A4]:
        passed <=> q_hybrid <= q_target  (the boundary counts as PASS).
   AXIOM (O3) [denominator sanity, AXIOM A3]:
        q_analytic is strictly positive, so the error percentage and the raw
        ratio are always well defined.

   THEOREM (O4) [clamp containment]: for positive inputs the correction factor
   satisfies 0.5 <= c <= 2.0, hence c - 1 is in [-0.5, 1] and the corrected
   cost J_round2 = J + (c-1)*ratio stays within a bounded distance of J: at
   c = 1 the correction is EXACTLY zero, which the module's own self-test
   asserts.
   THEOREM (O5) [verdict totality + correctness]: the gate verdict is a total
   boolean on positive finite inputs and is true exactly on the half-line
   q_hybrid <= q_target, so the gate never accepts a worse-than-target
   solution and never rejects the boundary.

   CITATIONS:
     [1] Kennedy, M.C. & O'Hagan, A. (2000), "Predicting the output from a
         complex computer code when fast approximations are available",
         Biometrika 87(1):1-13, Sec. 3 (first-order discrepancy).
     [2] Python Language Reference, 3rd Ed., Sec. 4.8 (min, max on floats).
     [3] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmax_left, Rmax_right,
         Rmin_left, Rmin_right), Coq.Reals.RIneq (Rmult_le_reg_l).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
(* Every constant and lemma below quantifies over the reals; opening R_scope
   at file level makes numerals and / elaborate in R rather than nat. *)
Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   Constants of the module (src/python/hiad_optimizer.py).
   --------------------------------------------------------------------------- *)
Definition GATE_CORR_MIN : R := 0.5.
Definition GATE_CORR_MAX : R := 2.0.

Lemma corr_min_pos : 0 < GATE_CORR_MIN.
Proof.
  unfold GATE_CORR_MIN.
  assert (Hshow : 0 < 1) by lra.
  assert (Hactual : 0 < 1 / 2) by lra.
  lra.
Qed.

Lemma corr_max_pos : 0 < GATE_CORR_MAX.
Proof.
  unfold GATE_CORR_MAX.
  assert (Hshow : 0 < 1) by lra.
  assert (Hactual : 0 < 2) by lra.
  lra.
Qed.

Lemma corr_max_gt : 0 < GATE_CORR_MAX - GATE_CORR_MIN.
Proof.
  unfold GATE_CORR_MIN, GATE_CORR_MAX.
  assert (Hshow : 0 < 2 - 1 / 2) by lra.
  lra.
Qed.

(* ---------------------------------------------------------------------------
   A reusable helper: l * (x / l) = x for l <> 0.  Written out in full in
   every file because these proof files do not import each other.
   --------------------------------------------------------------------------- *)
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

Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E.
    rewrite Rmult_1_r.
    exact Hab.
Qed.

(* ---------------------------------------------------------------------------
   Model of clamp(raw, GATE_CORR_MIN, GATE_CORR_MAX).
   --------------------------------------------------------------------------- *)
Definition correction_factor (q_hybrid q_analytic : R) : R :=
  Rmin GATE_CORR_MAX (Rmax GATE_CORR_MIN (q_hybrid / q_analytic)).

(* ---------------------------------------------------------------------------
   THEOREM O4 -- the clamped factor is contained in [0.5, 2.0].
   --------------------------------------------------------------------------- *)
Lemma correction_factor_lower : forall q_hybrid q_analytic,
   0 < q_hybrid -> 0 < q_analytic ->
   GATE_CORR_MIN <= correction_factor q_hybrid q_analytic.
Proof.
  intros q_hybrid q_analytic Hh Ha.
  unfold correction_factor.
  destruct (Rle_dec GATE_CORR_MAX (Rmax GATE_CORR_MIN (q_hybrid / q_analytic)))
    as [H | H].
  - rewrite Rmin_left by exact H.
    unfold GATE_CORR_MIN, GATE_CORR_MAX.
    lra.
  - apply Rnot_le_lt in H.
    apply Rlt_le in H.
    rewrite Rmin_right by exact H.
    apply Rmax_l.
Qed.

Lemma correction_factor_upper : forall q_hybrid q_analytic,
   0 < q_hybrid -> 0 < q_analytic ->
   correction_factor q_hybrid q_analytic <= GATE_CORR_MAX.
Proof.
  intros q_hybrid q_analytic Hh Ha.
  unfold correction_factor.
  destruct (Rle_dec GATE_CORR_MAX (Rmax GATE_CORR_MIN (q_hybrid / q_analytic)))
    as [H | H].
  - rewrite Rmin_left by exact H.
    apply Rle_refl.
  - apply Rnot_le_lt in H.
    apply Rlt_le in H.
    rewrite Rmin_right by exact H.
    exact H.
Qed.

Lemma correction_factor_band : forall q_hybrid q_analytic,
   0 < q_hybrid -> 0 < q_analytic ->
   GATE_CORR_MIN <= correction_factor q_hybrid q_analytic /\
   correction_factor q_hybrid q_analytic <= GATE_CORR_MAX.
Proof.
  intros q_hybrid q_analytic Hh Ha.
  split.
  - apply correction_factor_lower; assumption.
  - apply correction_factor_upper; assumption.
Qed.

(* ---------------------------------------------------------------------------
   Consequence for the round-2 cost: the correcting term (c - 1) is bounded,
   and vanishes exactly at c = 1.
   --------------------------------------------------------------------------- *)
Lemma correction_offset_bounds : forall q_hybrid q_analytic,
   0 < q_hybrid -> 0 < q_analytic ->
   GATE_CORR_MIN - 1 <= correction_factor q_hybrid q_analytic - 1 /\
   correction_factor q_hybrid q_analytic - 1 <= GATE_CORR_MAX - 1.
Proof.
  intros q_hybrid q_analytic Hh Ha.
  assert (H := correction_factor_band q_hybrid q_analytic Hh Ha).
  split; lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM O4 (identity case) -- at q_hybrid = q_analytic the correction is
   exactly the neutral element 1, so J_round2 = J as the self-test asserts.
   --------------------------------------------------------------------------- *)
Lemma correction_factor_neutral : forall q_analytic,
   0 < q_analytic -> correction_factor q_analytic q_analytic = 1.
Proof.
  intros q_analytic Ha.
  assert (Hne : q_analytic <> 0) by lra.
  assert (E1 : q_analytic / q_analytic = 1).
  { unfold Rdiv. apply Rinv_r. exact Hne. }
  unfold correction_factor.
  rewrite E1.
  assert (Hrmax : GATE_CORR_MIN <= 1).
  { unfold GATE_CORR_MIN. lra. }
  rewrite Rmax_right by exact Hrmax.
  assert (Hmin1 : 1 <= GATE_CORR_MAX).
  { unfold GATE_CORR_MAX. lra. }
  rewrite Rmin_right by exact Hmin1.
  reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM O5 -- the gate verdict is decided by a strict/non-strict
   comparison and is therefore total and boundary-inclusive.
   --------------------------------------------------------------------------- *)
Definition gate_verdict (q_hybrid q_target : R) : bool :=
  if Rle_dec q_hybrid q_target then true else false.

Lemma gate_verdict_true : forall q_hybrid q_target,
   q_hybrid <= q_target -> gate_verdict q_hybrid q_target = true.
Proof.
  intros q_hybrid q_target Hle.
  unfold gate_verdict.
  destruct (Rle_dec q_hybrid q_target) as [H | H].
  - reflexivity.
  - exfalso.
    assert (Hshow : q_hybrid <= q_target) by lra.
    contradiction.
Qed.

Lemma gate_verdict_false : forall q_hybrid q_target,
   q_target < q_hybrid -> gate_verdict q_hybrid q_target = false.
Proof.
  intros q_hybrid q_target Hlt.
  unfold gate_verdict.
  destruct (Rle_dec q_hybrid q_target) as [H | H].
  - exfalso.
    assert (Hshow : q_hybrid <= q_target) by lra.
    lra.
  - reflexivity.
Qed.

Lemma gate_verdict_total : forall q_hybrid q_target,
   gate_verdict q_hybrid q_target = true \/ gate_verdict q_hybrid q_target = false.
Proof.
  intros q_hybrid q_target.
  unfold gate_verdict.
  destruct (Rle_dec q_hybrid q_target) as [H | H].
  - left.
    reflexivity.
  - right.
    reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   Consequence: the prediction error is measured against a strictly positive
   denominator, so its sign carries information.
   --------------------------------------------------------------------------- *)
Definition prediction_error_pct (q_hybrid q_analytic : R) : R :=
  (q_hybrid - q_analytic) / q_analytic * 100.

Lemma prediction_error_pos : forall q_hybrid q_analytic,
   q_analytic < q_hybrid -> 0 < q_analytic ->
   0 < prediction_error_pct q_hybrid q_analytic.
Proof.
  intros q_hybrid q_analytic Hlt Ha.
  unfold prediction_error_pct.
  assert (Hd : 0 < q_hybrid - q_analytic) by lra.
  apply Rmult_lt_0_compat.
  - apply Rdiv_lt_0_compat; lra.
  - assert (Hshow : 0 < 100) by lra.
    lra.
Qed.

Lemma prediction_error_nonpos : forall q_hybrid q_analytic,
   q_hybrid <= q_analytic -> 0 < q_analytic ->
   prediction_error_pct q_hybrid q_analytic <= 0.
Proof.
  intros q_hybrid q_analytic Hle Ha.
  assert (Hne : q_analytic <> 0) by lra.
  assert (Hx : q_hybrid - q_analytic <= 0) by lra.
  assert (Hd : (q_hybrid - q_analytic) / q_analytic <= 0).
  { apply (Rmult_le_reg_l q_analytic); [exact Ha | ].
    rewrite (cancel_mul (q_hybrid - q_analytic) q_analytic Hne).
    rewrite Rmult_0_r.
    exact Hx. }
  unfold prediction_error_pct.
  apply Rle_trans with (0 * 100).
  - apply Rmult_le_compat_r; [lra | exact Hd].
  - rewrite Rmult_0_l.
    apply Rle_refl.
Qed.
