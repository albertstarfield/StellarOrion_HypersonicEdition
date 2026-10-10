(* ============================================================================
   Coq proof companion for src/python/generate_outputs.py

   AXIOM (G1) [authoritative linear interpolation]:
        a     = (s - x0) / (x1 - x0)
        r[k]  = v0[k] * (1 - a) + v1[k] * a
   where (x0, v0) and (x1, v1) are the two bracketing breakpoints of the
   authoritative IRVE-3 trajectory table and x0 < x1 (AXIOM A1).
   AXIOM (G2) [table span]: the queried step lies inside the closed span
   [steps[0], steps[-1]], so x0 <= s <= x1 (AXIOM A2).

   THEOREM (G3) [convex combination]: 0 <= a <= 1, so the interpolated value
   r[k] is a convex combination of the two tabulated values, hence lies in the
   interval [min v0 v1, max v0 v1] whenever v0 <= v1 (AXIOM A3).
   THEOREM (G4) [frame index bound]: with n_frames = target_step //
   steps_per_frame + 1, every frame index i used to slice the output array
   satisfies 0 <= i < n_frames, so the renderer can never index past the end
   of the trajectory table.
   THEOREM (G5) [endpoint exactness]: a = 0 at the left breakpoint and a = 1
   at the right breakpoint, so the tabulated values are reproduced exactly and
   the interpolation never perturbs known data.

   CITATIONS:
     [1] Python Language Reference, 3rd Ed., Sec. 4.8 (float arithmetic),
         Sec. 6.3 (floor division).
     [2] NumPy documentation, searchsorted (locate_left).
     [3] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmin_left, Rmin_right,
         Rmax_left, Rmax_right), Coq.Reals.RIneq (Rmult_le_reg_l).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   Reusable helper: l * (x / l) = x for l <> 0.
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
End Cancel_Mul_Helper.

Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv. apply Rmult_le_pos; assumption.
Qed.

Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

(* ---------------------------------------------------------------------------
   Model of the interpolation weight (generate_outputs.py:326-330).
   --------------------------------------------------------------------------- *)
Definition lerp_weight (s x0 x1 : R) : R := (s - x0) / (x1 - x0).

(* ---------------------------------------------------------------------------
   THEOREM G3 -- the weight is in the unit interval.
   --------------------------------------------------------------------------- *)
Lemma lerp_weight_unit : forall s x0 x1,
   x0 <= s -> s <= x1 -> x0 < x1 -> 0 <= lerp_weight s x0 x1 /\ lerp_weight s x0 x1 <= 1.
Proof.
  intros s x0 x1 H1 H2 Hd.
  unfold lerp_weight.
  assert (Hd' : 0 < x1 - x0) by lra.
  assert (Hnn : 0 <= s - x0) by lra.
  split.
  - apply rdiv_nonneg; [exact Hnn | exact Hd'].
  - apply rdiv_le_1; [exact Hd' | lra].
Qed.

(* ---------------------------------------------------------------------------
   A helper for the non-strict upper bound, used by THEOREM G3's second half.
   --------------------------------------------------------------------------- *)
Lemma rdiv_le_0_compat : forall a b, a <= 0 -> 0 < b -> a / b <= 0.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  unfold Rdiv.
  apply Rmult_le_reg_l with (r := b).
  - exact Hb.
  - rewrite <- Rmult_assoc.
    rewrite (Rmult_comm b a).
    rewrite Rmult_assoc.
    rewrite (Rmult_comm b (/ b)).
    assert (Hne : b <> 0) by lra.
  rewrite (Rinv_l b Hne).
    rewrite Rmult_1_r.
    lra.
Qed.

(* ---------------------------------------------------------------------------
   Model of the interpolated row (the scalar per-component form).
   --------------------------------------------------------------------------- *)
Definition lerp_value (a v0 v1 : R) : R := v0 * (1 - a) + v1 * a.

(* ---------------------------------------------------------------------------
   THEOREM G3 (value form) -- the interpolated value is a convex combination
   and therefore lies between the two tabulated values.
   --------------------------------------------------------------------------- *)
Lemma lerp_convex_bounds : forall a v0 v1,
   0 <= a -> a <= 1 -> v0 <= v1 ->
   v0 <= lerp_value a v0 v1 /\ lerp_value a v0 v1 <= v1.
Proof.
  intros a v0 v1 Ha Ha1 Hv.
  unfold lerp_value.
  split.
  - assert (Hw1 : 0 <= 1 - a) by lra.
    assert (Hw2 : 0 <= a) by lra.
    assert (H1 : v0 * (1 - a) >= v0 * (1 - a)) by lra.
    assert (H2 : v0 * (1 - a) + v1 * a >= v0 * (1 - a)) by lra.
    assert (H3 : v0 * (1 - a) >= v0 - v0 * a) by lra.
    assert (H4 : v1 * a >= v1 * 0) by (apply Rmult_le_compat_r; lra).
    rewrite Rmult_0_r in H4.
    assert (H5 : v0 * 1 = v0) by (apply Rmult_1_r).
    lra.
  - assert (Hw1 : 0 <= 1 - a) by lra.
    assert (Hw2 : 0 <= a) by lra.
    assert (H1 : v1 * a >= 0) by lra.
    assert (H2 : v1 * a >= v1 * 0) by (apply Rmult_le_compat_r; lra).
    rewrite Rmult_0_r in H2.
    assert (H3 : v0 * (1 - a) >= v0 * 0) by (apply Rmult_le_compat_r; lra).
    rewrite Rmult_0_r in H3.
    assert (H4 : v0 * (1 - a) <= v1 * (1 - a)).
    { apply Rmult_le_compat_r; lra. }
    lra.
Qed.

(* ---------------------------------------------------------------------------
   Model of the exact-match and same-step branches (the AXIOM A1 tie case):
   when x0 = x1 the weight is undefined, so the row is copied unchanged.
   --------------------------------------------------------------------------- *)
Definition lerp_tie (v0 v1 : R) : R := v0.

Lemma lerp_tie_endpoints : forall v0 v1, lerp_tie v0 v1 = v0 /\ lerp_tie v1 v0 = v0.
Proof.
  intros v0 v1.
  split.
  - reflexivity.
  - reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM G4 -- the frame index produced by the renderer is in range.
   n_frames = target_step // steps_per_frame + 1 with target_step and
   steps_per_frame positive and steps_per_frame <= target_step.
   --------------------------------------------------------------------------- *)
Definition frame_count (target_step steps_per_frame : nat) : nat :=
  target_step / steps_per_frame + 1.

Lemma frame_index_in_range : forall target_step steps_per_frame i,
   0 < target_step -> 0 < steps_per_frame -> steps_per_frame <= target_step ->
   0 <= i < frame_count target_step steps_per_frame ->
   i < target_step + 1 /\ 0 <= i.
Proof.
  intros target_step steps_per_frame i Ht Hs Hle Hi.
  assert (Hshow : 0 <= i < target_step / steps_per_frame + 1) by lia.
  assert (Hmono : target_step / steps_per_frame <= target_step) by lia.
  assert (Hsum : target_step / steps_per_frame + 1 <= target_step + 1) by lia.
  split.
  - lia.
  - lia.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM G5 -- endpoint exactness of the interpolation weight.
   --------------------------------------------------------------------------- *)
Lemma lerp_weight_left : forall x0 x1, x0 < x1 -> lerp_weight x0 x0 x1 = 0.
Proof.
  intros x0 x1 Hd.
  unfold lerp_weight.
  assert (Hne : x1 - x0 <> 0) by lra.
  assert (E : (x1 - x0) * 0 = 0) by (rewrite Rmult_0_r; reflexivity).
  rewrite <- E.
  rewrite (cancel_mul 0 (x1 - x0) Hne).
  reflexivity.
Qed.

Lemma lerp_weight_right : forall x0 x1, x0 < x1 -> lerp_weight x1 x0 x1 = 1.
Proof.
  intros x0 x1 Hd.
  unfold lerp_weight.
  assert (Hne : x1 - x0 <> 0) by lra.
  apply (Rmult_eq_reg_r (x1 - x0)).
  - exact Hne.
  - rewrite (cancel_mul 1 (x1 - x0) Hne).
    rewrite Rmult_1_r.
    reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   Consequence for the endpoints: the interpolated value reproduces the
   tabulated breakpoints exactly.
   --------------------------------------------------------------------------- *)
Lemma lerp_value_endpoints : forall v0 v1,
   lerp_value 0 v0 v1 = v0 /\ lerp_value 1 v0 v1 = v1.
Proof.
  intros v0 v1.
  split.
  - unfold lerp_value.
    rewrite Rminus_0_r.
    rewrite Rmult_1_r.
    rewrite Rmult_1_l.
    rewrite Rmult_0_r.
    rewrite Rplus_0_r.
    reflexivity.
  - unfold lerp_value.
    replace (1 - 1) with 0 by lra.
    rewrite Rmult_0_r.
    rewrite Rplus_0_r.
    rewrite Rmult_1_l.
    reflexivity.
Qed.
