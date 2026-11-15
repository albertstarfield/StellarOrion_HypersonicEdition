(*  core_inference.v

    The question the answer has to carry: "if there is already radiation, why
    add another radiation term into the conduction?"  The prose answer says the
    second T^4 is not a second radiative channel -- it is a volumetric diffusion
    coefficient whose SI home is W/(m*K), while the wall term eps*sigma*T^4 is a
    surface flux in W/m^2.  That distinction is the load-bearing step, so it is
    the step this file proves or refutes.

    THE CLAIM.  Let a = the radiative power per unit area that crosses the wall,
    b = the conducted power per unit area, and let a volumetric Rosseland term
    be converted to a surface flux by multiplying by a layer thickness L (that
    is what an integral over depth does).  Then:

      (C1) the volumetric term converts to the same surface flux only when the
           length scale is exactly 1 -- so "adding the other radiation term"
           is a category error unless a thickness is named;
      (C2) counting both channels inflates the balance by exactly one copy of a,
           while dropping the volumetric channel deflates it by exactly one copy
           of a: the two mistakes are equal in magnitude and opposite in sign.

    THE STEP THAT COULD FAIL.  C1 and C2 are algebra, but they say nothing about
    whether a is large.  Whether the volumetric channel exists at all in this
    gas is an empirical question -- it needs the Rosseland extinction kappa_R --
    and that step is NOT formalized here; the answer states the measurement that
    replaces it (kappa_R against the 7408 1/m split from possibility_space.v).

    Compiled with:  rocq compile proofs/core_inference.v
*)

From Stdlib Require Import Reals.
From Stdlib.micromega Require Import Lra Psatz.

Open Scope R_scope.

(* Wall term: eps * sigma * T^4, a surface flux in W/m^2. *)
Definition q_wall (eps sigma T : R) : R := eps * sigma * T ^ 4.

(* Rosseland volumetric conductivity: 16 sigma T^3 / (3 kappa), W/(m*K). *)
Definition k_rosseland (sigma kappa T : R) : R := 16 * sigma * T ^ 3 / (3 * kappa).

(* The same coefficient written as the derivative of the potential
   Phi = (4 sigma / (3 kappa)) T^4, i.e. dPhi/dT = 4 * (4 sigma / (3 kappa)) T^3.
   This is why a T^4-shaped object reappears inside a conduction term. *)
Theorem coefficient_is_potential_derivative :
  forall sigma kappa T : R, kappa <> 0 ->
    k_rosseland sigma kappa T = 4 * ((4 * sigma) / (3 * kappa)) * T ^ 3.
Proof.
  intros sigma kappa T Hk.
  unfold k_rosseland.
  field. nra.
Qed.

(* A volumetric flux becomes a surface flux only after integration over depth. *)
Definition q_volumetric_as_surface (k g L : R) : R := k * g * L.

(* C1: the two are interchangeable only at unit length.  Any other thickness
   gives a different number, so the terms are not the same object. *)
Theorem surface_equals_volumetric_only_at_unit_length :
  forall k g L : R, k * g <> 0 ->
    (q_volumetric_as_surface k g L = k * g <-> L = 1).
Proof.
  intros k g L Hkg. unfold q_volumetric_as_surface.
  split; intro H.
  - assert (Hd : k * g * L - k * g = 0) by lra.
    assert (Hf : k * g * (L - 1) = 0) by (rewrite <- Hd; ring).
    apply Rmult_integral in Hf.
    destruct Hf as [H0 | H1].
    + contradiction.
    + lra.
  - rewrite H. ring.
Qed.

(* C2: counting both channels inflates the balance by exactly one copy of a. *)
Theorem double_count_costs_one_copy :
  forall a b : R, 2 * a + b - (a + b) = a.
Proof. intros. ring. Qed.

(* ... while dropping the volumetric channel deflates it by exactly one copy. *)
Theorem omission_costs_one_copy :
  forall a b : R, (a + b) - (0 + b) = a.
Proof. intros. ring. Qed.

(* The two mistakes are twins: same size, opposite sign.  Neither is a rounding
   question, so the choice between the models is empirical, not verbal. *)
Theorem errors_are_twins :
  forall a b : R,
    (2 * a + b) - (a + b) = a /\ (a + b) - (0 + b) = a.
Proof. intros. split; ring. Qed.

(* The design point, in W/m^2, as the deck quotes it. *)
Definition wall_power : R := 140399.
Definition cond_power : R := 3362.

Theorem design_point_errors :
  ((2 * wall_power + cond_power) - (wall_power + cond_power) = wall_power) /\
  ((wall_power + cond_power) - (0 + cond_power) = wall_power).
Proof. split; unfold wall_power, cond_power; ring. Qed.

(* The radiative share is 41.7 < 42 times the conducted share at that point,
   so neither error can hide inside the other. *)
Theorem radiative_share_dominates :
  41 < wall_power / cond_power < 42.
Proof. unfold wall_power, cond_power. split; nra. Qed.
