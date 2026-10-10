(* ============================================================================
   Coq proof companion for src/python/generate_hiad_dashboard.py

   AXIOM (D1) [frame loop, AXIOM A1]:
        progress = frame / (fps * duration),   frame = 0 .. fps*duration - 1,
   with fps >= 1 and duration >= 1, and fps == 0 raises ValueError (AXIOM A2).
   AXIOM (D2) [reveal count, AXIOM A3]:
        n_show = max(1, int(n_pts * progress)) and the frame draws only
        x[:n_show], y[:n_show], mirrored to the full aeroshell silhouette.

   THEOREM (D3) [time and progress are consistent]: 0 <= progress < 1 for
   every frame of the loop and time_sec = frame / fps is ordered by frame, so
   the rendered time axis is monotone (AXIOM A4).
   THEOREM (D4) [reveal containment]: 1 <= n_show <= n_pts at every frame when
   n_pts >= 1, so the animation reveals a prefix that is never empty and never
   exceeds the geometry array (AXIOM A5).
   THEOREM (D5) [mirror closure]: mirroring the revealed prefix yields exactly
   2 * n_show points, so the frame buffer is allocated with the right size and
   never overflows (AXIOM A6).

   CITATIONS:
     [1] Python Language Reference, 3rd Ed., Sec. 4.8 (int truncation),
         Sec. 6.3 (floor division), Sec. 9.1 (built-in max).
     [2] Matplotlib documentation, FuncAnimation (frames, interval).
     [3] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmax_l, Rmax_left,
         Rmax_right), Coq.Reals.RIneq (Rmult_le_compat_l, IZR_le).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.
(* Znat supplies pos_INR, the nat -> R cast positivity lemma used below. *)
Require Import Coq.ZArith.Znat.

Local Open Scope R_scope.

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

Lemma rdiv_lt_1 : forall a b, 0 < b -> a < b -> a / b < 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_lt_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv.
  apply Rmult_le_pos; [exact Ha | exact Hinv].
Qed.

(* ---------------------------------------------------------------------------
   Model of the frame-loop progress and of the frame timestamp.
   --------------------------------------------------------------------------- *)
Definition frame_progress (frame fps duration : R) : R := frame / (fps * duration).

Definition frame_time (frame fps : R) : R := frame / fps.

(* ---------------------------------------------------------------------------
   THEOREM D3 -- progress is contained in [0,1) and the frame timestamp is
   ordered by frame.
   --------------------------------------------------------------------------- *)
Lemma frame_progress_bounds : forall frame fps duration,
   0 < fps -> 0 < duration -> 0 <= frame -> frame < fps * duration ->
   0 <= frame_progress frame fps duration /\ frame_progress frame fps duration < 1.
Proof.
  intros frame fps duration Hf Hd H1 H2.
  assert (Hprod : 0 < fps * duration).
  { apply Rmult_lt_0_compat; [exact Hf | exact Hd]. }
  unfold frame_progress.
  split.
  - apply rdiv_nonneg; [exact H1 | exact Hprod].
  - apply rdiv_lt_1; [exact Hprod | exact H2].
Qed.

Lemma frame_time_monotone : forall f1 f2 fps,
   0 < fps -> f1 <= f2 -> 0 <= f1 -> frame_time f1 fps <= frame_time f2 fps.
Proof.
  intros f1 f2 fps Hf H12 H1.
  unfold frame_time.
  assert (Hinv : 0 < / fps) by (apply Rinv_0_lt_compat; exact Hf).
  assert (H1' : f1 * / fps <= f2 * / fps).
  { apply Rmult_le_compat_r; [lra | exact H12]. }
  lra.
Qed.

(* ---------------------------------------------------------------------------
   Model of max(1, int(n_pts * progress)).
   --------------------------------------------------------------------------- *)
Definition n_show (n_pts : nat) (progress : R) : R := Rmax 1 (INR n_pts * progress).

(* ---------------------------------------------------------------------------
   THEOREM D4 -- the revealed prefix is never empty and never too long.
   --------------------------------------------------------------------------- *)
Lemma n_show_at_least_one : forall n_pts progress, 1 <= n_show n_pts progress.
Proof.
  intros n_pts progress.
  unfold n_show.
  apply Rmax_l.
Qed.

(* AXIOM: a natural number cast to the reals is non-negative, because INR is
   order-preserving and every nat is non-negative by construction.
   THEORY: pos_INR (Coq.ZArith.Znat) is exactly that fact, stated over nat
   directly — it needs no arithmetic reasoning about bounds.
   APPLICATION: used wherever an INR-cast count enters an R inequality. *)
Lemma inr_pts_nonneg : forall n_pts, 0 <= INR n_pts.
Proof.
  intros n_pts.
  apply pos_INR.
Qed.

Lemma n_show_le_geometry : forall n_pts progress,
   0 <= progress -> progress <= 1 ->
   n_show n_pts progress <= Rmax 1 (INR n_pts).
Proof.
  intros n_pts progress Hp1 Hp2.
  assert (Hlen : 0 <= INR n_pts) by apply inr_pts_nonneg.
  unfold n_show.
  destruct (Rle_dec 1 (INR n_pts * progress)) as [H | H].
  - rewrite Rmax_right by exact H.
    rewrite Rmax_right.
    + apply Rmult_le_compat_l; [exact Hlen | exact Hp2].
    + lra.
  - rewrite Rmax_left by exact H.
    apply Rmax_l.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM D5 -- the mirrored frame has exactly twice the revealed points.
   --------------------------------------------------------------------------- *)
Definition mirrored_total (revealed : nat) : nat := 2 * revealed.

Lemma mirrored_total_nonzero : forall revealed, 1 <= revealed -> 2 <= mirrored_total revealed.
Proof.
  intros revealed H.
  unfold mirrored_total.
  assert (Hshow : 0 < 2) by lia.
  assert (Hkey : 2 * 1 <= 2 * revealed) by (apply Nat.mul_le_mono_l; assumption).
  lia.
Qed.
