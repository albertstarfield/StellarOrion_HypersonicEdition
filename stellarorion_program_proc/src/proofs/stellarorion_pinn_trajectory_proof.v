(* ============================================================================
   Coq proof companion for src/simulation_engine/stellarorion_pinn_trajectory
   Ada 2012 / SPARK 2014, pragma SPARK_Mode (On).

   AXIOM (F1) [linear reentry map, NASA/TP-2013-4012]: the IRVE-3 trajectory
   is modelled as the affine map on the normalized progress
   p = Step / Target_Step (Pre: Target_Step > 0):
        H = H_Entry + (H_Final - H_Entry) * p     [km]
        V = V_Entry + (V_Final - V_Entry) * p     [m/s]
   with the .ads defaults H_Entry = 120.0 > H_Final = 40.0 and
   V_Entry = 4300.0 > V_Final = 2700.0.

   THEOREM (T1) [monotone descent]: because H_Final - H_Entry < 0, altitude is
   non-increasing in p; a later progress value never reports a larger
   altitude, which is exactly the property the descending DSMC handoff sweep
   of validation_pipeline.regime_gate relies on.
   THEOREM (T2) [endpoint exactness]: H(0) = H_Entry and H(1) = H_Final
   exactly, so the Pre conjunct H_Entry > H_Final forces a strict descent.
   THEOREM (T3) [window containment]: every point of the map stays inside the
   [H_Final, H_Entry] window the .ads documents, hence the map is a total
   function of p on [0,1] with values in the documented span.
   THEOREM (T4) [invertibility of the altitude map]: p = (H - H_Entry) /
   (H_Final - H_Entry) recovers H, which is the inversion the .ads header
   says the step axis uses.
   THEOREM (T5) [progress range]: p = Step / Target_Step lies in [0,1]
   whenever 0 <= Step <= Target_Step, so the normalized axis is closed.

   CITATIONS:
     [1] NASA/TP-2013-4012, Dillman et al., IRVE-3 flight reconstruction
         (the 120 km -> 40 km reentry corridor quoted by the .ads).
     [2] Anderson, "Modern Compressible Flow", 3rd Ed., Ch. 2 (ideal gas,
         speed of sound).
     [3] Ada Reference Manual ISO/IEC 8652:2012, RM 3.6 (real types) and
         RM 4.4 (expressions, multiplicative/additive operators).
     [4] Coq Reference Manual, Coq.Reals.RIneq (Rmult_le_compat_r,
         Rmult_le_pos, Rmult_eq_reg_l, Rinv_l, Rplus_le_compat_r).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

(* Every Definition and Lemma in this file quantifies over the reals; opening
   R_scope at file level makes numerals, <=, * and / elaborate in R rather than
   nat. [Citation: Coq 8.18 stdlib Coq.Reals.Reals -- Local Open Scope R_scope] *)
Local Open Scope R_scope.

(* AXIOM: a negative multiplier reverses order the same way it reverses
   subtraction. THEOREM: A < 0 and p1 <= p2 gives A * p2 <= A * p1.
   APPLICATION: monotonicity of a linear interpolation whose slope
   (h_final - h_entry) is negative.
   [Citation: Coq 8.18 Ropp_le_contravar / Rmult_le_compat_l] *)
Lemma mono_neg : forall A p1 p2 : R, A < 0 -> p1 <= p2 -> A * p2 <= A * p1.
Proof.
  intros A p1 p2 HA H12.
  replace (A * p2) with (- (- A * p2)) by ring.
  replace (A * p1) with (- (- A * p1)) by ring.
  apply Ropp_le_contravar.
  apply Rmult_le_compat_l; [lra | exact H12].
Qed.

(* ---------------------------------------------------------------------------
   The affine trajectory map of IRVE3_Trajectory (the .ads documentation).
   --------------------------------------------------------------------------- *)
Definition altitude_at (h_entry h_final p : R) : R :=
   h_entry + (h_final - h_entry) * p.

Definition velocity_at (v_entry v_final p : R) : R :=
   v_entry + (v_final - v_entry) * p.

(* ---------------------------------------------------------------------------
   Progress model inherited from the trajectory-output unit: p = Step/Target.
   --------------------------------------------------------------------------- *)
Definition progress (step target : R) : R := step / target.

(* ---------------------------------------------------------------------------
   THEOREM T5 -- progress is well defined and lies in [0,1] whenever
   0 <= Step <= Target and Target > 0.
   --------------------------------------------------------------------------- *)
Lemma progress_range : forall step target : R,
   0 <= step -> step <= target -> 0 < target ->
   0 <= progress step target /\ progress step target <= 1.
Proof.
  intros step target Hlo Hhi Htarget.
  assert (Hne : target <> 0) by lra.
  assert (Hinv : 0 < / target) by (apply Rinv_0_lt_compat; exact Htarget).
  unfold progress, Rdiv.
  split.
  - apply Rmult_le_pos; [exact Hlo | lra].
  - apply (Rmult_le_reg_l target); [exact Htarget | ].
    rewrite Rmult_1_r.
    rewrite <- Rmult_assoc.
    rewrite (Rmult_comm target step).
    rewrite Rmult_assoc.
    rewrite (Rmult_comm target (/ target)).
    rewrite (Rinv_l target Hne).
    rewrite Rmult_1_r.
    lra.
Qed.

(* ---------------------------------------------------------------------------
   Helper -- a bounded affine term: for a bounded slope interval and
   p in [0,1], the product (b - a) * p stays between (b - a) and 0.
   --------------------------------------------------------------------------- *)
Lemma affine_term_bounds : forall a b p,
   0 <= p -> p <= 1 -> b < a ->
   (a - b) * p <= a - b /\ 0 <= (a - b) * p.
Proof.
  intros a b p Hp1 Hp2 Hb.
  assert (Hnn : 0 <= (a - b) * p) by (apply Rmult_le_pos; lra).
  assert (Hup : (a - b) * p <= a - b).
  { rewrite (Rmult_comm (a - b) p).
    assert (H1 : p * (a - b) <= 1 * (a - b)).
    { apply (Rmult_le_compat_r (a - b) p 1); lra. }
    rewrite Rmult_1_l in H1.
    exact H1. }
  split; [exact Hup | exact Hnn].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T3 -- every point of the altitude map stays inside the window.
   --------------------------------------------------------------------------- *)
Lemma altitude_window : forall h_entry h_final p,
   h_final < h_entry -> 0 <= p -> p <= 1 ->
   h_final <= altitude_at h_entry h_final p /\ altitude_at h_entry h_final p <= h_entry.
Proof.
  intros h_entry h_final p Hdesc Hp1 Hp2.
  assert (Hb := affine_term_bounds h_entry h_final p Hp1 Hp2 Hdesc).
  assert (Hkey : (h_final - h_entry) * p = - ((h_entry - h_final) * p)).
  { replace (h_final - h_entry) with (- (h_entry - h_final)) by lra.
    rewrite <- (Ropp_mult_distr_l (h_entry - h_final) p).
    reflexivity. }
  unfold altitude_at.
  rewrite Hkey.
  split.
  - lra.
  - lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T3 (velocity) -- the same containment for the velocity map.
   --------------------------------------------------------------------------- *)
Lemma velocity_window : forall v_entry v_final p,
   v_final < v_entry -> 0 <= p -> p <= 1 ->
   v_final <= velocity_at v_entry v_final p /\ velocity_at v_entry v_final p <= v_entry.
Proof.
  intros v_entry v_final p Hdesc Hp1 Hp2.
  assert (Hb := affine_term_bounds v_entry v_final p Hp1 Hp2 Hdesc).
  assert (Hkey : (v_final - v_entry) * p = - ((v_entry - v_final) * p)).
  { replace (v_final - v_entry) with (- (v_entry - v_final)) by lra.
    rewrite <- (Ropp_mult_distr_l (v_entry - v_final) p).
    reflexivity. }
  unfold velocity_at.
  rewrite Hkey.
  split.
  - lra.
  - lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T1 -- altitude is non-increasing in progress.
   --------------------------------------------------------------------------- *)
Lemma altitude_nonincreasing : forall h_entry h_final p1 p2,
   h_final < h_entry -> p1 <= p2 ->
   altitude_at h_entry h_final p2 <= altitude_at h_entry h_final p1.
Proof.
  intros h_entry h_final p1 p2 Hdesc Hp12.
  unfold altitude_at.
  unfold altitude_at.
  assert (H2 : (h_final - h_entry) * p2 <= (h_final - h_entry) * p1)
    by (apply mono_neg; [lra | exact Hp12]).
  lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T1 (velocity) -- velocity is non-increasing in progress.
   --------------------------------------------------------------------------- *)
Lemma velocity_nonincreasing : forall v_entry v_final p1 p2,
   v_final < v_entry -> p1 <= p2 ->
   velocity_at v_entry v_final p2 <= velocity_at v_entry v_final p1.
Proof.
  intros v_entry v_final p1 p2 Hdesc Hp12.
  unfold velocity_at.
  unfold velocity_at.
  assert (H2 : (v_final - v_entry) * p2 <= (v_final - v_entry) * p1)
    by (apply mono_neg; [lra | exact Hp12]).
  lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T2 -- the map hits the documented endpoints exactly.
   --------------------------------------------------------------------------- *)
Lemma altitude_endpoints : forall h_entry h_final,
   altitude_at h_entry h_final 0 = h_entry /\
   altitude_at h_entry h_final 1 = h_final.
Proof.
  intros h_entry h_final.
  unfold altitude_at.
  split.
  - lra.
  - lra.
Qed.

Lemma velocity_endpoints : forall v_entry v_final,
   velocity_at v_entry v_final 0 = v_entry /\
   velocity_at v_entry v_final 1 = v_final.
Proof.
  intros v_entry v_final.
  unfold velocity_at.
  split.
  - lra.
  - lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T2 (strictness) -- with a strictly positive descent the endpoint
   inequality of the Pre is strict, so the trajectory never stalls.
   --------------------------------------------------------------------------- *)
Lemma altitude_descends : forall h_entry h_final,
   h_final < h_entry ->
   altitude_at h_entry h_final 1 < altitude_at h_entry h_final 0.
Proof.
  intros h_entry h_final Hdesc.
  unfold altitude_at.
  lra.
Qed.

Lemma velocity_descends : forall v_entry v_final,
   v_final < v_entry ->
   velocity_at v_entry v_final 1 < velocity_at v_entry v_final 0.
Proof.
  intros v_entry v_final Hdesc.
  unfold velocity_at.
  lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T4 -- the altitude map is invertible on any strictly descending
   span: p = (H - H_Entry) / (H_Final - H_Entry) recovers H exactly. This is
   the inversion the .ads header says the step axis performs.
   --------------------------------------------------------------------------- *)
Lemma altitude_inverse : forall h_entry h_final h,
   h_entry <> h_final ->
   altitude_at h_entry h_final ((h - h_entry) / (h_final - h_entry)) = h.
Proof.
  intros h_entry h_final h Hne.
  assert (Hd : h_final - h_entry <> 0) by lra.
  assert (E : (h_final - h_entry) * ((h - h_entry) / (h_final - h_entry)) = h - h_entry).
  { unfold Rdiv.
    rewrite <- Rmult_assoc.
    rewrite (Rmult_comm (h_final - h_entry) (h - h_entry)).
    rewrite Rmult_assoc.
    rewrite (Rmult_comm (h_final - h_entry) (/ (h_final - h_entry))).
    rewrite (Rinv_l (h_final - h_entry) Hd).
    rewrite Rmult_1_r.
    reflexivity. }
  unfold altitude_at.
  rewrite E.
  lra.
Qed.
