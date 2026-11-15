(*  rosseland_monotone.v

    Scratch paper for the claim the deck makes on "WHY T^4 SITS OUTSIDE FOURIER":
    with one conduction path and one radiative path at the same node, the wall
    residual

        f(T) = c*T + b*T^4            (c = 1/R + G > 0, b = eps*sigma > 0)

    is strictly increasing on T >= 0, hence injective, hence the temperature the
    bisection chases is unique.  The Lean file proofs/fourth_power.lean states the
    same thing over Nat (where no negatives exist); here it is over the reals,
    where b can actually be negative and the claim can fail -- which is what the
    last two theorems show.

    Compiled with:  rocq compile proofs/rosseland_monotone.v
*)

From Stdlib Require Import Reals.
From Stdlib Require Import ROrderedType.
From Stdlib.micromega Require Import Lra Psatz.

Open Scope R_scope.

Definition residual (c b T : R) : R := c * T + b * T ^ 4.

(* The positive-slope case: both coefficients positive, T >= 0, T1 < T2. *)
Theorem residual_strict_mono :
  forall c b T1 T2 : R,
    0 < c -> 0 < b -> 0 <= T1 -> T1 < T2 ->
    residual c b T1 < residual c b T2.
Proof.
  intros c b T1 T2 Hc Hb H0 Hlt.
  assert (Hid : T2 ^ 4 - T1 ^ 4 = (T2 - T1) * (T2 + T1) * (T2 ^ 2 + T1 ^ 2))
    by ring.
  assert (Hd : 0 < T2 - T1) by lra.
  assert (Hs : 0 < T2 + T1) by lra.
  assert (Hq : 0 < T2 ^ 2 + T1 ^ 2) by nra.
  assert (H4 : 0 < T2 ^ 4 - T1 ^ 4).
  { rewrite Hid.
    apply Rmult_lt_0_compat.
    - apply Rmult_lt_0_compat; assumption.
    - assumption. }
  unfold residual.
  nra.
Qed.

(* Strict monotonicity gives a unique root: equal values force equal arguments. *)
Theorem residual_injective :
  forall c b T1 T2 : R,
    0 < c -> 0 < b -> 0 <= T1 -> 0 <= T2 ->
    residual c b T1 = residual c b T2 -> T1 = T2.
Proof.
  intros c b T1 T2 Hc Hb H1 H2 Heq.
  destruct (Rcompare_spec T1 T2) as [Heqt | Hlt | Hgt].
  - exact Heqt.
  - exfalso. pose proof (residual_strict_mono c b T1 T2 Hc Hb H1 Hlt). lra.
  - exfalso. pose proof (residual_strict_mono c b T2 T1 Hc Hb H2 Hgt). lra.
Qed.

(* Counterexample 1: let b go negative -- an emissivity falling faster than T^3
   rises -- and the residual stops being monotone.  c = 1, b = -1 gives
   f(0) = f(1) = 0, so the root is not unique and bisection can land on either. *)
Theorem negative_b_breaks_monotonicity :
  exists c b T1 T2 : R,
    0 < c /\ T1 < T2 /\ residual c b T2 <= residual c b T1.
Proof.
  exists 1, (-1), 0, 1.
  split; [lra | split; [lra | unfold residual; ring_simplify; lra]].
Qed.

(* Counterexample 2: with no conduction and no radiation (c = b = 0) the residual
   is identically zero, so every T solves the balance -- monotonicity needs
   strict positivity of at least one coefficient. *)
Theorem degenerate_zero_residual :
  residual 0 0 0 = residual 0 0 1.
Proof.
  unfold residual. ring_simplify. lra.
Qed.

(* ------------------------------------------------------------------ *)
(* The possibility space around "drop the Rosseland term".             *)
(*                                                                     *)
(* H_drop:  the shock layer is optically thin, so q_rad = -k_R dT/dx   *)
(*          vanishes and the wall balance is conduction + surface      *)
(*          radiation only.                                            *)
(* H_keep:  k_R > 0 and the gradient is non-zero, so the term is       *)
(*          really there and omitting it changes the flux.             *)
(*                                                                     *)
(* The two are not a matter of taste: any non-zero k_R against a       *)
(* non-zero gradient gives a non-zero flux, so H_keep is falsifiable   *)
(* by a single measurement of k_R (i.e. of the optical depth).         *)
(* ------------------------------------------------------------------ *)

Theorem omission_changes_flux :
  forall k g : R, 0 < k -> g <> 0 -> k * g <> 0.
Proof.
  intros k g Hk Hg H.
  apply Rmult_integral in H.
  destruct H as [Hk0 | Hg0].
  - lra.
  - exact (Hg Hg0).
Qed.

(* The radiative share of the flux in the diffusion limit is
   (k_R * g) / (k_gas * g) = k_R / k_gas -- independent of the gradient.
   So "the gradient is steep here" argues neither for nor against keeping
   the term: only k_R (the optical depth) decides. *)
Theorem ratio_independent_of_gradient :
  forall a b g1 g2 : R, b <> 0 -> g1 <> 0 -> g2 <> 0 ->
    a * g1 / (b * g1) = a * g2 / (b * g2).
Proof.
  intros a b g1 g2 Hb Hg1 Hg2.
  field. all: auto with real.
Qed.
