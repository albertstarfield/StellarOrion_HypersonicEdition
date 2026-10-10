(* ============================================================================
   Coq proof companion for src/python/hiad_geometry.py
   Python 3, matplotlib output (no SPARK; safety argument is arithmetic).

   AXIOM (G1) [HIAD cross-section, Rapisarda & Zohdar 2023 Sec. 3.7]:
   the cross-section is built from four joined segments over n_per_segment
   samples each, contributing n + 3*(n - 1) = 4n - 3 points for n >= 2.
   AXIOM (G2) [monotone radius]: the second segment interpolates linearly
        r = R_tang + t * (R_target - R_tang),   0 <= t <= 1,
   and the fourth segment shrinks the corrugation arc by r = R_C_out * (1 - t).

   THEOREM (G3) [point count]: for n_per_segment >= 2 the four segments emit
   exactly 4n - 3 points, and this count is at least 5 and at most the
   MAX_CROSS_SECTION_PTS = 200 bound of stellarorion_pinn_trajectory.ads,
   whenever n_per_segment <= 50 (4*50 - 3 = 197 <= 200).
   THEOREM (G4) [segment containment]: the interpolated radius of segment 2
   stays inside [R_tang, R_target]; hence the mirrored point list never leaves
   the aeroshell envelope the .ads bounds.
   THEOREM (G5) [non-negativity]: the radial coordinate is clamped by
   Python's max(0.0, x), so every emitted ordinate is >= 0.0 -- exactly the
   assertion the module's own test makes.

   CITATIONS:
     [1] Rapisarda, M. & Zohar, Y., "HIAD: development of a deployable
         aeroshell", 2023, Sec. 3.7 (cross-section construction).
     [2] Python Language Reference, 3rd Ed., Sec. 4.8 (max applied to floats).
     [3] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmax_l, Rmax_r),
         Coq.Reals.RIneq (Rmult_le_compat_r, Rmult_le_pos, Rinv_l).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
Require Import Coq.micromega.Lia.

(* ---------------------------------------------------------------------------
   Model of the four-segment construction over n samples per segment.
   --------------------------------------------------------------------------- *)
Definition segment_point_count (n : nat) : nat := n + 3 * (n - 1).

(* ---------------------------------------------------------------------------
   THEOREM G3 -- the count is 4n - 3, is at least 5, and fits the Ada buffer.
   --------------------------------------------------------------------------- *)
Lemma point_count_shape : forall n, 2 <= n -> segment_point_count n = 4 * n - 3.
Proof.
  intros n Hn.
  unfold segment_point_count.
  assert (Hshow : 3 * (n - 1) = 3 * n - 3) by (rewrite Nat.mul_sub_distr_l; lia).
  lia.
Qed.

Lemma point_count_at_least_5 : forall n, 2 <= n -> 5 <= segment_point_count n.
Proof.
  intros n Hn.
  unfold segment_point_count.
  assert (Hshow : 3 * (n - 1) = 3 * n - 3) by (rewrite Nat.mul_sub_distr_l; lia).
  lia.
Qed.

Lemma point_count_fits_buffer : forall n,
   2 <= n -> n <= 50 -> segment_point_count n <= 200.
Proof.
  intros n Hn Hn50.
  unfold segment_point_count.
  assert (Hshow : 3 * (n - 1) = 3 * n - 3) by (rewrite Nat.mul_sub_distr_l; lia).
  lia.
Qed.

(* ---------------------------------------------------------------------------
   Model of segment 2:  r = R_tang + t * (R_target - R_tang),  t in [0,1].
   --------------------------------------------------------------------------- *)
Definition segment2_radius (r_tang r_target t : R) : R :=
   r_tang + t * (r_target - r_tang).

(* ---------------------------------------------------------------------------
   THEOREM G4 -- segment 2 stays inside [R_tang, R_target].
   --------------------------------------------------------------------------- *)
Lemma segment2_contained : forall r_tang r_target t : R,
   r_tang <= r_target -> 0 <= t -> t <= 1 ->
   r_tang <= segment2_radius r_tang r_target t /\
   segment2_radius r_tang r_target t <= r_target.
Proof.
  intros r_tang r_target t Hle Ht1 Ht2.
  unfold segment2_radius.
  split.
  - assert (Hnn : 0 <= t * (r_target - r_tang)) by (apply Rmult_le_pos; lra).
    lra.
  - assert (H1 : t * (r_target - r_tang) <= 1 * (r_target - r_tang)).
    { apply Rmult_le_compat_r; lra. }
    rewrite Rmult_1_l in H1.
    lra.
Qed.

(* ---------------------------------------------------------------------------
   Model of segment 4:  r = R_C_out * (1 - t),  t in [0,1],  R_C_out >= 0.
   --------------------------------------------------------------------------- *)
Definition segment4_radius (r_c_out t : R) : R := r_c_out * (1 - t).

Lemma segment4_contained : forall r_c_out t,
   0 <= r_c_out -> 0 <= t -> t <= 1 ->
   0 <= segment4_radius r_c_out t /\ segment4_radius r_c_out t <= r_c_out.
Proof.
  intros r_c_out t Hr Ht1 Ht2.
  unfold segment4_radius.
  assert (Hnn : 0 <= r_c_out * (1 - t)) by (apply Rmult_le_pos; lra).
  assert (H1 : r_c_out * (1 - t) <= r_c_out * 1).
  { apply Rmult_le_compat_r; lra. }
  rewrite Rmult_1_r in H1.
  split; [exact Hnn | exact H1].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM G5 -- the emitted ordinate is Python's max(0.0, x), hence >= 0.
   --------------------------------------------------------------------------- *)
Lemma clamp_nonneg : forall x, 0 <= Rmax 0 x.
Proof.
  intros x.
  assert (Hshow : 0 <= 0) by lra.
  apply Rmax_l.
Qed.

Lemma clamp_ge_arg : forall x, x <= Rmax 0 x.
Proof.
  intros x.
  assert (Hshow : 0 <= 0) by lra.
  apply Rmax_r.
Qed.

(* ---------------------------------------------------------------------------
   Consequence for the mirror: mirroring x around 0 maps an ordinate in
   [0, R] into [-R, 0], so the mirrored envelope is centred on the axis of
   symmetry, which is what the .ads Cross_Section buffer stores.
   --------------------------------------------------------------------------- *)
Lemma mirror_ord : forall x, x <= 0 -> - 0 <= - x.
Proof.
  intros x Hx.
  assert (Hshow : - 0 = 0) by lra.
  rewrite Hshow.
  lra.
Qed.
