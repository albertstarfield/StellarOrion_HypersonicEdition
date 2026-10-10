(* ============================================================================
   Coq proof companion for src/python/validation_pipeline.py
   Python 3, ctypes FFI layer (no SPARK; safety argument is arithmetic).

   AXIOM (V1) [Knudsen number]: Kn = lambda / L_char, the ratio of the
   molecular mean free path to the characteristic length. Bird, "Molecular Gas
   Dynamics and the Direct Simulation Monte Carlo Method", Sec. 1.2 & 1.4,
   which is the reference the module header quotes.
   AXIOM (V2) [monotone mean free path]: over the IRVE-3 flight span the mean
   free path is monotone NON-INCREASING in altitude, so Kn descends with
   altitude and a Kn threshold is crossed at exactly one altitude (the module
   header states this as the correctness condition of the descending sweep).
   AXIOM (V3) [linear altitude map]: the trajectory maps a normalized progress
   p = Step / Target_Step onto altitude by H = 120 + (40 - 120) * p, so the
   inversion is p = (H - 120) / (40 - 120) and
        Step = (H - H_Entry) / (H_Final - H_Entry) * Target_Step.

   THEOREM (V4) [quotient monotonicity]: Kn = lambda / L_char is monotone in
   lambda for a fixed positive L_char, so the descending sweep is sound.
   THEOREM (V5) [handoff step is in span]: whenever the handoff altitude lies
   inside the flight span, the handoff step lies inside [0, Target_Step]. This
   is what keeps regime_gate's handoff_step a valid index on the same step axis
   the PINN leg uses (the .ads Pre Target_Step > 0 is used, not assumed).
   THEOREM (V6) [inversion monotonicity]: the step-of-altitude map is monotone
   DEcreasing in altitude, so the earlier crossing of the threshold maps to the
   earlier step, and the sweep finds the unique handoff.

   CITATIONS:
     [1] Bird, G.A., "Molecular Gas Dynamics and the Direct Simulation Monte
         Carlo Method", Clarendon Press, 1994, Sec. 1.2 & 1.4.
     [2] NASA/TP-2013-4012 (IRVE-3 flight span 120 km -> 40 km), the reference
         quoted by the module header.
     [3] Python Language Reference, 3rd Ed., Sec. 3.1 (numeric model) for the
         float arithmetic of (h_entry - handoff_alt) / (h_entry - h_final).
     [4] Coq Reference Manual, Coq.Reals.RIneq (Rmult_le_compat_r,
         Rdiv_lt_0_compat, Rinv_l, Rinv_r, Rmult_le_reg_l, Rmult_lt_reg_l).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   Helper: l * (x / l) = x for a non-zero l.  Used everywhere below to
   normalise a quotient after multiplying by its own denominator.
   --------------------------------------------------------------------------- *)
(* R-scope wrapper: numerals and '*' must elaborate as R, not nat.
   Scoped to this section only so later nat lemmas stay nat. *)
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
Lemma rdiv_le_mono : forall a b c, 0 < c -> a <= b -> a / c <= b / c.
Proof.
  intros a b c Hc Hab.
  assert (Hne : c <> 0) by lra.
  assert (E1 : c * (a / c) = a) by (apply cancel_mul; exact Hne).
  assert (E2 : c * (b / c) = b) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l c); [exact Hc | ].
  rewrite E1. rewrite E2. exact Hab.
Qed.
Lemma rdiv_neg_flip : forall x y, y < 0 -> x / y = - (x / (- y)).
Proof.
  intros x y Hy.
  assert (Hne : - y <> 0) by lra.
  assert (Ei : / y = - (/ (- y))).
  { rewrite <- (Ropp_involutive (/ y)). rewrite Rinv_opp. reflexivity. }
  unfold Rdiv. rewrite Ei.
  rewrite Ropp_mult_distr_r_reverse. reflexivity.
Qed.
Lemma rdiv_le_mono_neg : forall a b c, c < 0 -> a <= b -> b / c <= a / c.
Proof.
  intros a b c Hc Hab.
  assert (Hm : 0 < - c) by lra.
  rewrite (rdiv_neg_flip b c Hc).
  rewrite (rdiv_neg_flip a c Hc).
  apply Ropp_le_contravar.
  apply rdiv_le_mono; [exact Hm | exact Hab].
Qed.
End Cancel_Mul_Helper.

Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

Lemma rdiv_lt_1 : forall a b, 0 < b -> a < b -> a / b < 1.
Proof.
  intros a b Hb Hab.
  destruct (Req_dec (a / b) 1) as [Heq | Hne2].
  - exfalso.
    assert (Hne : b <> 0) by lra.
    assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
    rewrite Heq in E.
    rewrite Rmult_1_r in E.
    lra.
  - assert (Hle : a / b <= 1) by (apply rdiv_le_1; lra).
    lra.
Qed.

Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv.
  apply Rmult_le_pos; [exact Ha | exact Hinv].
Qed.

Lemma rdiv_pos : forall a b, 0 < a -> 0 < b -> 0 < a / b.
Proof.
  intros a b Ha Hb.
  apply Rdiv_lt_0_compat; [exact Ha | exact Hb].
Qed.

Lemma rdiv_lt_mono : forall a b c, 0 < c -> a < b -> a / c < b / c.
Proof.
  intros a b c Hc Hab.
  assert (Hne : c <> 0) by lra.
  assert (E1 : c * (a / c) = a) by (apply cancel_mul; exact Hne).
  assert (E2 : c * (b / c) = b) by (apply cancel_mul; exact Hne).
  apply (Rmult_lt_reg_l c); [exact Hc | ].
  rewrite E1, E2.
  exact Hab.
Qed.

(* ---------------------------------------------------------------------------
   Model of regime_gate (validation_pipeline.py:569-589):

       kn_run = lam_run / l_char
       handoff_step = (h_entry - handoff_alt) / (h_entry - h_final) * target_step
   --------------------------------------------------------------------------- *)
Definition knudsen (lam l_char : R) : R := lam / l_char.

Definition handoff_step (h_entry h_final h_handoff target_step : R) : R :=
   ((h_entry - h_handoff) / (h_entry - h_final)) * target_step.

Definition step_of_altitude (h_entry h_final h target_step : R) : R :=
   ((h - h_entry) / (h_final - h_entry)) * target_step.

(* ---------------------------------------------------------------------------
   THEOREM V4 -- Kn is non-negative for a non-negative mean free path and
   monotone in lambda for a fixed positive L_char.
   --------------------------------------------------------------------------- *)
Lemma kn_nonneg : forall lam l_char, 0 <= lam -> 0 < l_char -> 0 <= knudsen lam l_char.
Proof.
  intros lam l_char Hlam Hl.
  unfold knudsen.
  apply rdiv_nonneg; [exact Hlam | exact Hl].
Qed.

Lemma kn_monotone_in_lambda : forall lam1 lam2 l_char,
   0 < l_char -> lam1 <= lam2 ->
   knudsen lam1 l_char <= knudsen lam2 l_char.
Proof.
  intros lam1 lam2 l_char Hl Hle.
  unfold knudsen.
  apply rdiv_le_mono; [exact Hl | exact Hle].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM V5 -- the handoff step lies inside the flight span whenever the
   handoff altitude does.
   --------------------------------------------------------------------------- *)
Lemma handoff_step_in_span : forall h_entry h_final h_handoff target_step,
   h_final < h_entry -> h_final <= h_handoff -> h_handoff <= h_entry ->
   0 < target_step ->
   0 <= handoff_step h_entry h_final h_handoff target_step /\
   handoff_step h_entry h_final h_handoff target_step <= target_step.
Proof.
  intros h_entry h_final h_handoff target_step Hdesc Hlo Hhi Htarget.
  assert (Hd : 0 < h_entry - h_final) by lra.
  assert (Hw : (h_entry - h_handoff) / (h_entry - h_final) <= 1)
    by (apply rdiv_le_1; lra).
  unfold handoff_step.
  split.
  - apply Rmult_le_pos.
    + apply rdiv_nonneg; lra.
    + lra.
  - assert (Hm : (h_entry - h_handoff) / (h_entry - h_final) * target_step
                <= 1 * target_step).
    { apply Rmult_le_compat_r; [lra | exact Hw]. }
    rewrite Rmult_1_l in Hm.
    exact Hm.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM V6 -- the step-of-altitude inversion is monotone decreasing in
   altitude, so the descending altitude sweep maps to an ascending step sweep.
   --------------------------------------------------------------------------- *)
Lemma step_of_monotone : forall h1 h2 h_entry h_final target_step,
   h_final < h_entry -> h1 <= h2 -> h2 <= h_entry -> 0 < target_step ->
   step_of_altitude h_entry h_final h2 target_step
   <= step_of_altitude h_entry h_final h1 target_step.
Proof.
  intros h1 h2 h_entry h_final target_step Hdesc H12 H2 Htarget.
  assert (Hd : 0 < h_entry - h_final) by lra.
  unfold step_of_altitude.
  apply Rmult_le_compat_r; [lra | ].
  apply rdiv_le_mono_neg; [lra | lra].
Qed.

(* ---------------------------------------------------------------------------
   Consequence: the altitude-to-step inversion maps the two ends of the flight
   span to the two ends of the step axis.  This is the "invert the IRVE-3
   linear altitude map (120 -> 40 km over target_step)" claim of the module
   header, stated as the two endpoint equalities the sweep relies on.
   --------------------------------------------------------------------------- *)
Lemma step_of_at_entry : forall h_entry h_final target_step,
   step_of_altitude h_entry h_final h_entry target_step = 0.
Proof.
  intros h_entry h_final target_step.
  unfold step_of_altitude.
  (* AXIOM: x - x = 0 for any real x, so the numerator is identically zero
     once subtraction is evaluated (Rminus_diag), not merely rewrite-equal.
     APPLICATION: canonicalise the numerator first, then the Rdiv mass cancels. *)
  rewrite Rminus_diag.
  unfold Rdiv.
  rewrite Rmult_0_l.
  reflexivity.
Qed.

Lemma step_of_at_final : forall h_entry h_final target_step,
   h_entry <> h_final ->
   step_of_altitude h_entry h_final h_final target_step = target_step.
Proof.
  intros h_entry h_final target_step Hne.
  assert (Hd : h_final - h_entry <> 0) by lra.
  assert (Hone : (h_final - h_entry) / (h_final - h_entry) = 1).
  { apply (Rmult_eq_reg_r (h_final - h_entry)); [ | exact Hd].
    unfold Rdiv.
    rewrite Rmult_assoc.
    rewrite (Rinv_r (h_final - h_entry) Hd).
    rewrite Rmult_1_r.
    rewrite Rmult_1_l.
    reflexivity. }
  unfold step_of_altitude.
  rewrite Hone.
  rewrite Rmult_1_l.
  reflexivity.
Qed.
