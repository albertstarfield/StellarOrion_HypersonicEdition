(* ============================================================================
   Coq proof companion for src/python/generate_optimized_overlay.py

   AXIOM (O1) [frame loop, AXIOM A1]:
        progress = frame / (fps * duration),   frame = 0 .. fps*duration - 1,
   with fps >= 1 and duration >= 1 (AXIOM A2).
   AXIOM (O2) [two-phase reveal, AXIOM A3]:
        phase1 = progress * 2                when progress < 0.5
        phase2 = (progress - 0.5) * 2        otherwise
   and n_show = max(1, int(len(x) * phase)); x[:n_show] is then drawn with the
   converged trajectory overlaid on the baseline.

   THEOREM (O3) [progress containment]: 0 <= progress < 1 for every frame the
   loop visits, so no phase function is ever called with an out-of-range
   argument (AXIOM A4).
   THEOREM (O4) [phase containment]: 0 <= phase1 <= 1 and 0 <= phase2 <= 1, so
   n_show only ever reveals a prefix of the trajectory (AXIOM A5).
   THEOREM (O5) [never-empty slice]: n_show >= 1 whenever the underlying point
   array is non-empty, so the overlay never draws a blank frame before the end
   of the animation (AXIOM A6).

   CITATIONS:
     [1] Python Language Reference, 3rd Ed., Sec. 4.8 (int truncation toward
         zero), Sec. 6.3 (floor division), Sec. 9.1 (built-in max).
     [2] Matplotlib documentation, FuncAnimation (frames argument).
     [3] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmax_l, Rmax_left,
         Rmax_right, Rmax_lub), Coq.Reals.RIneq (Rmult_le_compat_l,
         Rinv_0_lt_compat, Rmult_lt_0_compat).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
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
   Model of the frame-loop progress.
   --------------------------------------------------------------------------- *)
Definition frame_progress (frame fps duration : R) : R := frame / (fps * duration).

(* ---------------------------------------------------------------------------
   THEOREM O3 -- progress is contained in [0, 1).
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

(* ---------------------------------------------------------------------------
   Model of the two reveal phases.
   --------------------------------------------------------------------------- *)
Definition phase_one (progress : R) : R := progress * 2.

Definition phase_two (progress : R) : R := (progress - 1 / 2) * 2.

(* ---------------------------------------------------------------------------
   THEOREM O4 -- each phase maps its half of [0,1) onto [0,1].
   --------------------------------------------------------------------------- *)
Lemma phase_one_bounds : forall progress,
   0 <= progress -> progress < 1 / 2 ->
   0 <= phase_one progress /\ phase_one progress < 1.
Proof.
  intros progress H1 H2.
  unfold phase_one.
  split; lra.
Qed.

Lemma phase_two_bounds : forall progress,
   1 / 2 <= progress -> progress < 1 ->
   0 <= phase_two progress /\ phase_two progress < 1.
Proof.
  intros progress H1 H2.
  unfold phase_two.
  split; lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM O5 -- the revealed-prefix length is at least one, where the model
   of max(1, int(len(x) * phase)) is the real max of 1 with the (non-negative)
   projected length len * phase.
   --------------------------------------------------------------------------- *)
Definition n_show (len : nat) (phase : R) : R := Rmax 1 (INR len * phase).

Lemma n_show_at_least_one : forall len phase, 1 <= n_show len phase.
Proof.
  intros len phase.
  unfold n_show.
  apply Rmax_l.
Qed.

Lemma inr_len_nonneg : forall len, 0 <= INR len.
Proof.
  intros len.
  apply pos_INR.
Qed.

Lemma n_show_le_length : forall len phase,
   0 <= phase -> phase <= 1 -> n_show len phase <= Rmax 1 (INR len).
Proof.
  intros len phase Hp1 Hp2.
  assert (Hlen : 0 <= INR len) by apply inr_len_nonneg.
  (* Rmult_le_compat_l cannot unify its conclusion "r * r1 <= r * r2" against
     a goal whose right-hand side is the bare atom INR len (Coq does not
     normalise INR len * 1 to INR len during unification), so the product
     bound is established against the explicit factor 1 and then folded back
     with Rmult_1_r. *)
  assert (Hg : INR len * phase <= INR len * 1)
    by (apply Rmult_le_compat_l; [exact Hlen | exact Hp2]).
  rewrite Rmult_1_r in Hg.
  unfold n_show.
  destruct (Rle_dec 1 (INR len * phase)) as [H | H].
  - rewrite (Rmax_right 1 (INR len * phase) H).
    apply Rle_trans with (r2 := INR len).
    + exact Hg.
    + apply Rmax_r.
  - (* ~ (1 <= INR len * phase) is a negation; convert it to the strict
       inequality Rmax_left expects, then to the non-strict one. *)
    apply Rnot_le_lt in H.
    apply Rlt_le in H.
    rewrite (Rmax_left 1 (INR len * phase) H).
    apply Rmax_l.
Qed.

Lemma n_show_monotone : forall len phase1 phase2,
   phase1 <= phase2 -> 0 <= phase1 ->
   n_show len phase1 <= n_show len phase2.
Proof.
  intros len phase1 phase2 Hp12 Hp1.
  assert (Hlen : 0 <= INR len) by apply inr_len_nonneg.
  assert (Hkey : INR len * phase1 <= INR len * phase2)
    by (apply Rmult_le_compat_l; [exact Hlen | exact Hp12]).
  unfold n_show.
  destruct (Rle_dec 1 (INR len * phase2)) as [H | H].
  - rewrite (Rmax_right 1 (INR len * phase2) H).
    destruct (Rle_dec 1 (INR len * phase1)) as [H' | H'].
    + rewrite (Rmax_right 1 (INR len * phase1) H').
      exact Hkey.
    + (* ~ (1 <= INR len * phase1) is a negation; convert it to the strict
         inequality Rmax_left expects, then to the non-strict one. *)
      apply Rnot_le_lt in H'.
      apply Rlt_le in H'.
      rewrite (Rmax_left 1 (INR len * phase1) H').
      exact H.
  - (* ~ (1 <= INR len * phase2) is a negation; convert it to the strict
       inequality, but KEEP it strict: the B1 contradiction below needs
       INR len * phase2 < 1, whereas the non-strict form alone is satisfiable
       (1 <= L*p1 <= L*p2 <= 1 holds with L*p1 = L*p2 = 1). *)
    apply Rnot_le_lt in H.
    assert (Hle : INR len * phase2 <= 1) by (apply Rlt_le; exact H).
    rewrite (Rmax_left 1 (INR len * phase2) Hle).
    (* Goal: Rmax 1 (INR len * phase1) <= 1. *)
    destruct (Rle_dec 1 (INR len * phase1)) as [H' | H'].
    + exfalso.
      (* H' : 1 <= INR len * phase1 with phase1 <= phase2 gives
         1 <= INR len * phase2 < 1 -- a genuine contradiction.
         Hkey (established above the destruct) links the two nonlinear
         product atoms, and lra treats each atom as an opaque variable, so
         the chain 1 <= L*p1 <= L*p2 < 1 closes the goal arithmetically. *)
      lra.
    + (* ~ (1 <= INR len * phase1): both maxima collapse to 1. *)
      apply Rnot_le_lt in H'.
      apply Rlt_le in H'.
      rewrite (Rmax_left 1 (INR len * phase1) H').
      apply Rle_refl.
Qed.
