(*  possibility_space.v

    The deck's claim -- "the Rosseland term is dropped here" -- lives inside a
    space of four hypotheses.  Rhetoric cannot separate them; a parameter can.

    In the diffusion limit the radiative share of the flux is

        q_rad / q_cond  =  (k_R * g) / (k_gas * g)  =  k_R / k_gas  =  A / kappa

    with A := 16*sigma*T^3 / (3*k_gas) and kappa := k_R the Rosseland extinction.
    So the two hypotheses

        H_drop : the term is negligible   <->  A / kappa < 1
        H_keep : the term matters         <->  1 < A / kappa

    occupy disjoint halves of the kappa axis, split at kappa* = A.  Everything
    below is proved, not asserted: the boundary is sharp, the regimes are
    separable, and H_drop is falsified by any measured kappa below kappa*.

    The numeric instance uses the deck's wall temperature (T = 1348 K) and an
    illustrative gas conductivity of 0.1 W/(m*K), which gives A = 7408 1/m.
    That number is illustrative only -- the theorems below hold for any A > 0.

    Compiled with:  rocq compile proofs/possibility_space.v
*)

From Stdlib Require Import Reals.
From Stdlib.micromega Require Import Lra Psatz.

Open Scope R_scope.

Definition q_ratio (A kappa : R) : R := A / kappa.

(* The split at kappa* = A is exact, in both directions. *)
Theorem ratio_lt_one :
  forall A kappa : R, 0 < kappa -> (q_ratio A kappa < 1 <-> A < kappa).
Proof.
  intros A kappa Hk. unfold q_ratio.
  assert (Hid : (A / kappa) * kappa = A) by (field; lra).
  split; intro H.
  - pose proof (Rmult_lt_compat_r kappa _ _ Hk H) as Hm.
    rewrite Hid in Hm. lra.
  - apply (Rmult_lt_reg_r kappa (A / kappa) 1 Hk).
    rewrite Hid. lra.
Qed.

Theorem ratio_gt_one :
  forall A kappa : R, 0 < kappa -> (1 < q_ratio A kappa <-> kappa < A).
Proof.
  intros A kappa Hk. unfold q_ratio.
  assert (Hid : (A / kappa) * kappa = A) by (field; lra).
  split; intro H.
  - pose proof (Rmult_lt_compat_r kappa _ _ Hk H) as Hm.
    rewrite Hid in Hm. lra.
  - apply (Rmult_lt_reg_r kappa 1 (A / kappa) Hk).
    rewrite Hid. lra.
Qed.

(* H_drop holds on one side of kappa* ... *)
Theorem drop_is_justified :
  forall A kappa : R, 0 < kappa -> A < kappa -> q_ratio A kappa < 1.
Proof.
  intros A kappa Hk HA. apply ratio_lt_one; assumption.
Qed.

(* ... and is false on the other.  This is the hypothesis under which the
   deck's present wording would be wrong. *)
Theorem drop_is_falsified :
  forall A kappa : R, 0 < kappa -> kappa < A -> 1 < q_ratio A kappa.
Proof.
  intros A kappa Hk HA. apply ratio_gt_one; assumption.
Qed.

(* The space is not vacuous: both regimes are inhabited for every A > 0. *)
Theorem regimes_are_separable :
  forall A : R, 0 < A ->
    exists k_lo k_hi : R,
      0 < k_lo /\ 0 < k_hi /\ k_lo < A /\ A < k_hi.
Proof.
  intros A HA.
  exists (A / 2), (2 * A).
  split; [nra | split; [nra | split; nra]].
Qed.

(* The concrete slice the deck sits on: T = 1348 K, k_gas = 0.1 W/(m*K)
   -> A = 7408 1/m (computed in Python from sigma = 5.670374419e-8).
   Dropping the term is right for kappa = 74080 (ratio 0.1) and wrong for
   kappa = 740 (ratio 10.01). *)
Definition A_design : R := 7408.

Theorem design_point_regimes :
  q_ratio A_design 74080 < 1 /\ 1 < q_ratio A_design 740.
Proof.
  unfold A_design.
  split.
  - apply drop_is_justified; lra.
  - apply drop_is_falsified; lra.
Qed.
