(* ============================================================================
   MACHINE-CHECKED PROOF -- gen_trajectory_profile (1-DOF ballistic entry profile)
   ============================================================================
   Unit : scripts/gen_trajectory_profile.py
            constants                 (lines 51-68)
            compute_trajectory        (lines 95-178)
            (Ada/SPARK parity: stellarorion_physics Compute_Trajectory_Profile)

   Goal : The scalar guards and bounds the integrator relies on:
          T1 the inverse-square gravity `g = G0 * (R_EARTH/(R_EARTH+alt))^2`
             (line 129) is strictly positive and bounded above by sea-level G0
             for 0 < G0, 0 < R_EARTH, 0 <= alt -- the physical domain in which
             the altitude/velocity/flight-path ODEs (lines 133-140) are stepped;
          T2 the altitude and velocity clamps `alt_new = max(alt_new, 0.0)` and
             `vel_new = max(vel_new, 0.0)` (lines 150, 153) keep the integrated
             altitude non-negative, so the loop's `alt_m <= 0.0` termination
             test (line 110) is on a well-ordered state;
          T3 the Mach number `mach = vel / a_sound` (line 156) is non-negative
             whenever velocity is non-negative and the speed of sound positive,
             so the plotted mach column never goes negative.

   AXIOMS
   A1. R_EARTH = 6371000.0 m, G0 = 9.80665 m/s^2 (lines 51-52); alt is clamped
       non-negative by line 150 and the loop guard keeps vel > 170 m/s (line 112,
       136). [Reference: scripts/gen_trajectory_profile.py:51-52, 110-112, 136, 150]
   A2. GRAVITY uses g(h) = G0 * (R/(R+h))^2 with the ODE dv/dt = -D/m - g*sin,
       dgamma, dh, ddr of the Chapman/Vinh 1-DOF model (lines 129-140).
       [Reference: scripts/gen_trajectory_profile.py:129-140]

   THEORIES
   T1. R/(R+h) in (0,1], so its square is in (0,1], so G0*square in (0, G0].
   T2. Rmax alt 0 >= 0 (and >= alt when alt >= 0).
   T3. vel/a >= 0 for vel >= 0 and a > 0.

   APPLICATIONS
   The returned profile (alt_km, vel_ms, mach, dyn_press_pa, g_load, ...) is
   only physical because gravity stays in (0, G0] and altitude stays >= 0 over
   the whole integration; these are the exact bounds the PDF/CDF comparison
   plots and the Rapisarda overlay then visualise.

   CITATIONS:
     [1] Chapman, D.R., "An Approximate Analytical Method for Studying Entry
         into Planetary Atmospheres", NASA TR R-37, 1959: https://ntrs.nasa.gov/
     [2] Vinh, N.X. et al., "Hypersonic and Planetary Entry Flight Mechanics",
         1980 (inverse-square gravity, 1-DOF equations): https://ntrs.nasa.gov/
     [3] Coq Reference Manual, Coq.Reals.RIneq (Rle_trans, Rmult_le_compat_l,
         Rmult_lt_0_compat, Rdiv_lt_0_compat, Rinv_l, Rmult_le_reg_l),
         Coq.Reals.Rbasic_fun (Rmax_l, Rmax_r): https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* ---------------------------------------------------------------------------
   Division helpers, each discharged from the stdlib.
   --------------------------------------------------------------------------- *)
Section Cancel_Mul_Helper.
  (* l*(x/l) = x for a nonzero divisor. *)
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

(* a/b <= 1 for a numerator bounded by a positive divisor. *)
Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

(* a/b is non-negative for a non-negative numerator over a positive divisor. *)
Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv.
  apply Rmult_le_pos; [exact Ha | exact Hinv].
Qed.

(* Square of a number in [0,1] stays in [0,1]; the left factor is common. *)
Lemma sq_le_1 : forall x, 0 <= x -> x <= 1 -> x * x <= 1.
Proof.
  intros x Hx Hx1.
  assert (Hle : x * x <= x * 1) by (apply Rmult_le_compat_l; [exact Hx | exact Hx1]).
  rewrite Rmult_1_r in Hle.
  apply Rle_trans with (r2 := x); [exact Hle | exact Hx1].
Qed.

(* `sq x` packages x*x so the gravity term is written without the ambiguous
   `a/b * c/d` association. *)
Definition sq (x : R) : R := x * x.

(* `gravity_ratio radius altitude` models R/(R+alt); `gravity_accel g0 r a`
   models g = G0 * (R/(R+h))^2 at line 129. *)
Definition gravity_ratio (radius altitude : R) : R := radius / (radius + altitude).
Definition gravity_accel (g0 radius altitude : R) : R :=
  g0 * sq (gravity_ratio radius altitude).

(* T1 -- gravity stays in (0, G0]: R/(R+h) in (0,1] implies its square is in
   (0,1], and multiplying by the positive G0 lands in (0, G0]. *)
Lemma gravity_bounds : forall g0 radius altitude,
  0 < g0 -> 0 < radius -> 0 <= altitude ->
  0 < gravity_accel g0 radius altitude /\ gravity_accel g0 radius altitude <= g0.
Proof.
  intros g0 radius altitude H0 HR Ha.
  assert (Hsum : 0 < radius + altitude) by lra.
  assert (Hle : radius <= radius + altitude) by lra.
  assert (Hrr1 : gravity_ratio radius altitude <= 1).
  { unfold gravity_ratio. apply rdiv_le_1; [exact Hsum | exact Hle]. }
  assert (Hrrp : 0 < gravity_ratio radius altitude).
  { unfold gravity_ratio. apply Rdiv_lt_0_compat; [exact HR | exact Hsum]. }
  assert (Hrr0 : 0 <= gravity_ratio radius altitude) by (apply Rlt_le; exact Hrrp).
  assert (Hsqp : 0 < sq (gravity_ratio radius altitude)).
  { unfold sq. apply Rmult_lt_0_compat; [exact Hrrp | exact Hrrp]. }
  assert (Hsql : sq (gravity_ratio radius altitude) <= 1).
  { unfold sq. apply sq_le_1; [exact Hrr0 | exact Hrr1]. }
  unfold gravity_accel.
  split.
  - apply Rmult_lt_0_compat; [exact H0 | exact Hsqp].
  - apply Rle_trans with (r2 := g0 * 1).
    + apply Rmult_le_compat_l; [lra | exact Hsql].
    + rewrite Rmult_1_r. apply Rle_refl.
Qed.

(* `altitude_clamp alt` mirrors alt_new = max(alt_new, 0.0) at line 150. *)
Definition altitude_clamp (altitude : R) : R := Rmax altitude 0.

(* T2a -- the clamped altitude is non-negative, so the termination test on
   alt_m <= 0.0 (line 110) sees a well-ordered state. *)
Lemma altitude_clamp_nonneg : forall altitude, 0 <= altitude_clamp altitude.
Proof.
  intros altitude.
  unfold altitude_clamp.
  apply Rmax_r.
Qed.

(* T2b -- the clamp never lowers a non-negative altitude. *)
Lemma altitude_clamp_ge_input : forall altitude, altitude <= altitude_clamp altitude.
Proof.
  intros altitude.
  unfold altitude_clamp.
  apply Rmax_l.
Qed.

(* `mach_ratio vel a` mirrors mach = vel / a_sound at line 156. *)
Definition mach_ratio (velocity speed_of_sound : R) : R := velocity / speed_of_sound.

(* T3 -- the Mach number is non-negative for non-negative velocity over a
   positive speed of sound, so the plotted mach column never goes negative. *)
Lemma mach_ratio_nonneg : forall velocity speed_of_sound,
  0 <= velocity -> 0 < speed_of_sound ->
  0 <= mach_ratio velocity speed_of_sound.
Proof.
  intros velocity speed_of_sound Hv Ha.
  unfold mach_ratio.
  apply rdiv_nonneg; [exact Hv | exact Ha].
Qed.
