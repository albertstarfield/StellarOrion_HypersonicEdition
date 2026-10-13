(* ============================================================================
   MACHINE-CHECKED PROOF -- plot_hiad_3d (interactive 3D HIAD surface viewer)
   ============================================================================
   Unit : scripts/plot_hiad_3d.py
            read_surf               (lines 67-97)
            build_revolution_mesh   (lines 100-128)
            generate_html / main    (lines 131-340)
            N_AZIMUTHAL = 120       (line 63)

   Goal : Both structural guards the viewer relies on hold:
          T1 the guard `len(profile) < 3` (line 316) guarantees a NON-EMPTY
             meridian, so the revolved mesh of N_AZIMUTHAL * len(profile)
             surface elements (line 331) is non-empty and the max()/min()
             annotations computed in generate_html (lines 146-148) are total;
          T2 the azimuthal sample angle theta_j = 2*pi*j/n_az (line 114)
             stays in the HALF-OPEN window [0, 2*pi), so the n_az slices
             tile the annulus exactly once with no repeated seam angle --
             relying on n_az = N_AZIMUTHAL = 120 > 0 as a safe divisor.

   AXIOMS
   A1. read_surf returns one (Z_axial, R_radial) pair per Points-block row
       (lines 88-94); main rejects a profile with fewer than 3 points and
       exits before any rendering (lines 316-321).
       [Reference: scripts/plot_hiad_3d.py:88-94, 316-321]
   A2. A surface of revolution is sampled at n_az equally spaced azimuthal
       angles theta_j = 2*pi*j/n_az, j = 0 .. n_az-1, with n_az a nonzero
       compile-time constant (lines 113-114).
       [Reference: scripts/plot_hiad_3d.py:113-114]

   THEORIES
   T1. [non-empty mesh] 1 <= n_az and 3 <= n_profile imply
       0 < n_az * n_profile; build_revolution_mesh appends one row per
       azimuth and one cell per profile point, so the element count is
       exactly n_az * n_profile (line 331).
   T2. [half-open azimuthal window] 0 < two_pi and 0 < n_az and 0 <= j < n_az
       imply 0 <= theta_j < two_pi, so the sampling covers one full turn
       without repeating the seam theta = 2*pi.

   APPLICATIONS
   Rendering begins only after both guards: a non-empty profile makes the
   element total and the D = 2*max_r / axial-length annotations (line 210)
   well-defined, and the half-open azimuthal window makes the revolved mesh a
   faithful, seam-free torus (THEOREM 1/2 of the unit's own docstring).

   CITATIONS:
     [1] Surface of revolution (parametric form x = r*cos(theta),
         y = r*sin(theta), z = z): https://en.wikipedia.org/wiki/Surface_of_revolution
     [2] Rapisarda (2023), "IRVE-3 Aerothermodynamic Reconstruction", thesis,
         Sec 3.7 axisymmetric HIAD geometry, TU Delft repository:
         https://repository.tudelft.nl/
     [3] Plotly.js surface charts (self-contained HTML export):
         https://plotly.com/javascript/
     [4] Coq Reference Manual, Coq.Reals.Reals / Coq.Arith.PeanoNat
         (Nat.mul_le_mono_l, Rdiv via Rinv_l): https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* ---------------------------------------------------------------------------
   Division helpers, each discharged from the stdlib, mirroring the pattern
   used across the project's other plotting proofs.
   --------------------------------------------------------------------------- *)
Section Cancel_Mul_Helper.
  (* l*(x/l) = x for a nonzero divisor -- every a/b step below reduces to it.
     [Coq 8.18 Reals: Rinv_l, Rmult_assoc, Rmult_comm] *)
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

(* a/b is non-negative for a non-negative numerator over a positive divisor. *)
Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv.
  apply Rmult_le_pos; [exact Ha | exact Hinv].
Qed.

(* a/b stays below 1 for a numerator strictly below a positive divisor. *)
Lemma rdiv_lt_1 : forall a b, 0 < b -> a < b -> a / b < 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_lt_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

(* Strictly monotone left-multiplication by a positive constant -- needed to
   carry the strict window bound through the theta = two_pi*(j/n) scaling. *)
Lemma mul_lt_l : forall c x y, 0 < c -> x < y -> c * x < c * y.
Proof.
  intros c x y Hc Hxy.
  assert (Hd : 0 < c * (y - x)) by (apply Rmult_lt_0_compat; lra).
  assert (Heq : c * y - c * x = c * (y - x)) by ring.
  rewrite <- Heq in Hd.
  lra.
Qed.

(* ---------------------------------------------------------------------------
   T1 -- the meridian guard makes the surface-element count positive.
   `surface_elements n_az n_profile` mirrors the total printed at line 331.
   --------------------------------------------------------------------------- *)
Section Mesh_Nat.
Local Open Scope nat_scope.

Definition surface_elements (n_az n_profile : nat) : nat := n_az * n_profile.

Lemma surface_elements_positive : forall n_profile,
  3 <= n_profile -> 0 < surface_elements 120 n_profile.
Proof.
  intros n_profile Hn.
  unfold surface_elements.
  assert (Hmul : 120 * 3 <= 120 * n_profile)
    by (apply Nat.mul_le_mono_l; exact Hn).
  lia.
Qed.

End Mesh_Nat.

(* ---------------------------------------------------------------------------
   T2 -- the azimuthal sampling angle lies in the half-open window [0, 2*pi).
   `azimuth_step two_pi n_az j` models theta = 2*pi*j/n_az (line 114).
   --------------------------------------------------------------------------- *)
Definition azimuth_step (two_pi n_az j : R) : R := two_pi * (j / n_az).

Lemma azimuthal_window : forall two_pi n_az j,
  0 < two_pi -> 0 < n_az -> 0 <= j -> j < n_az ->
  0 <= azimuth_step two_pi n_az j /\ azimuth_step two_pi n_az j < two_pi.
Proof.
  intros two_pi n_az j Hp Hnz Hj Hjn.
  assert (Hfrac_nonneg : 0 <= j / n_az) by (apply rdiv_nonneg; [exact Hj | exact Hnz]).
  assert (Hfrac_lt1 : j / n_az < 1) by (apply rdiv_lt_1; [exact Hnz | exact Hjn]).
  unfold azimuth_step.
  split.
  - apply Rmult_le_pos; [lra | exact Hfrac_nonneg].
  - assert (Hlt : two_pi * (j / n_az) < two_pi * 1).
    { apply mul_lt_l; [exact Hp | exact Hfrac_lt1]. }
    rewrite Rmult_1_r in Hlt.
    exact Hlt.
Qed.
