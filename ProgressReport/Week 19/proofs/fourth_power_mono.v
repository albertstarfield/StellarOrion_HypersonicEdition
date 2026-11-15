(* ==================================================================== *)
(*  fourth_power_mono.v -- Rocq scratch paper for fourth_power.lean      *)
(*                                                                       *)
(*  Claim under test (thesis appendix eq:app_tsurf):                     *)
(*      f(T) = k*T + b*T^4 - q,      k = 1/R > 0,  b = eps*sigma > 0     *)
(*  is STRICTLY INCREASING on T >= 0, so eps*sigma*T^4 = q_conv has at   *)
(*  most one root there, and the root of the full (k>0) balance is the   *)
(*  same.  Rocq is used here as an independent checker of the Lean       *)
(*  skeleton, on the reals rather than on Nat -- which is exactly the    *)
(*  place fourth_power.lean is weakest (it uses Nat, so T - T_back and   *)
(*  -q are unrepresentable).                                             *)
(*                                                                       *)
(*  Compiled with: rocq compile proofs/fourth_power_mono.v               *)
(* ==================================================================== *)

From Stdlib Require Import Reals.
From Stdlib Require Import Lra.
Open Scope R_scope.

(* -------------------------------------------------------------------- *)
(* The wall residual, same shape as the Ada expression at                *)
(* stellarorion_physics.adb:2613-2618 with the T-independent terms       *)
(* (T_back/R, b*T_inf^4, -q, -S) folded into the single constant -q.     *)
(* -------------------------------------------------------------------- *)
Definition residual (k b q T : R) : R := k * T + b * T ^ 4 - q.

(* -------------------------------------------------------------------- *)
(* Lemma 1: x^4 is strictly increasing on the non-negative reals.        *)
(* -------------------------------------------------------------------- *)
Lemma pow4_lt : forall x y : R, 0 <= x -> x < y -> x ^ 4 < y ^ 4.
Proof.
  intros x y hx hxy.
  assert (h2 : x ^ 2 < y ^ 2) by nra.
  assert (h4 : (x ^ 2) ^ 2 < (y ^ 2) ^ 2) by nra.
  nra.
Qed.

(* A cube is non-negative on the non-negative reals: the 4*eps*sigma*T^3
   part of the Newton slope can never flip the sign of f'. *)
Lemma pow3_nonneg : forall T : R, 0 <= T -> 0 <= T ^ 3.
Proof.
  intros T hT. nra.
Qed.

(* -------------------------------------------------------------------- *)
(* Lemma 2 (the thesis sentence, done properly on R):                   *)
(* strictly increasing whenever both coefficients are strictly positive, *)
(* with no constraint that T - T_back be non-negative and no truncating  *)
(* subtraction anywhere.                                                 *)
(* -------------------------------------------------------------------- *)
Theorem residual_strict_mono :
  forall k b q T1 T2 : R,
    0 < k -> 0 < b -> 0 <= T1 -> T1 < T2 ->
    residual k b q T1 < residual k b q T2.
Proof.
  intros k b q T1 T2 hk hb h0 hlt.
  unfold residual.
  assert (hp : T1 ^ 4 < T2 ^ 4) by (apply pow4_lt; lra).
  nra.
Qed.

(* -------------------------------------------------------------------- *)
(* Lemma 3: the derivative  f'(T) = k + 4*b*T^3  is strictly positive.  *)
(* This is the "cubic" half of the cubic-plus-quartic story: the T^3 in  *)
(* the Newton slope is the derivative of the same single quartic, so it  *)
(* adds to the slope and cannot create a second branch.                  *)
(* -------------------------------------------------------------------- *)
Theorem slope_positive :
  forall k b T : R, 0 < k -> 0 < b -> 0 <= T -> 0 < k + 4 * b * T ^ 3.
Proof.
  intros k b T hk hb hT.
  assert (h3 : 0 <= T ^ 3) by (apply pow3_nonneg; lra).
  nra.
Qed.

(* -------------------------------------------------------------------- *)
(* Lemma 4: at most one root on [0, inf).  Injectivity is what a         *)
(* bisection needs; existence is supplied by the closed form            *)
(* T = (q/(eps*sigma))^(1/4), not by this theorem.                       *)
(* -------------------------------------------------------------------- *)
Theorem residual_root_unique :
  forall k b q T1 T2 : R,
    0 < k -> 0 < b -> 0 <= T1 -> 0 <= T2 ->
    residual k b q T1 = 0 -> residual k b q T2 = 0 -> T1 = T2.
Proof.
  intros k b q T1 T2 hk hb h1 h2 e1 e2.
  destruct (Rlt_le_dec T1 T2) as [h | h].
  - exfalso.
    assert (H := residual_strict_mono k b q T1 T2 hk hb h1 h).
    lra.
  - destruct (Rle_lt_or_eq_dec T2 T1 h) as [h' | h'].
    + exfalso.
      assert (H := residual_strict_mono k b q T2 T1 hk hb h2 h').
      lra.
    + symmetry. exact h'.
Qed.

(* -------------------------------------------------------------------- *)
(* Lemma 5: counting the radiative term twice is doubling its            *)
(* coefficient, i.e. asking for emissivity 2*eps -- which is what makes  *)
(* the double-count reading arithmetically distinguishable.              *)
(* -------------------------------------------------------------------- *)
Theorem double_count_is_doubled_emissivity :
  forall b T : R, 2 * (b * T ^ 4) = (2 * b) * T ^ 4.
Proof.
  intros b T. ring.
Qed.

(* -------------------------------------------------------------------- *)
(* Counterexample 1 (machine-checked): drop the hypothesis b > 0 and the *)
(* whole uniqueness argument dies.  With b = -1, k = 1, q = 0:           *)
(*     f(1) = 1 - 1 = 0,      f(2) = 2 - 16 = -14,                        *)
(* so f(1) > f(2) while 1 < 2: f is DECREASING, and a second root exists *)
(* in (1,2) because f(2) < 0 < f(1).  Positive slope is not decoration.  *)
(* -------------------------------------------------------------------- *)
Theorem negative_coefficient_breaks_it :
  ~ (forall k b q T1 T2 : R,
       0 < k -> 0 <= T1 -> T1 < T2 -> residual k b q T1 < residual k b q T2).
Proof.
  intro H.
  assert (h : residual 1 (-1) 0 1 < residual 1 (-1) 0 2).
  { apply H; lra. }
  unfold residual in h. lra.
Qed.

(* -------------------------------------------------------------------- *)
(* The bookkeeping claim, independently of Lean: one radiative term      *)
(* closes to one unit, two miss by the whole radiative flux.             *)
(* -------------------------------------------------------------------- *)
Theorem single_count_closes : Rabs (143760 - (140399 + 3362)) <= 2.
Proof. apply Rabs_le. lra. Qed.

Theorem double_count_breaks : 100 <= Rabs (143760 - (2 * 140399 + 3362)).
Proof.
  assert (H : Rabs (143760 - (2 * 140399 + 3362)) = 140400).
  { rewrite Rabs_left1 by lra. lra. }
  lra.
Qed.

(* And the two readings are 140399 apart, so no tolerance spans them. *)
Theorem counts_are_distinguishable :
  Rabs (143760 - (140399 + 3362)) + 100
    <= Rabs (143760 - (2 * 140399 + 3362)).
Proof.
  assert (H1 : Rabs (143760 - (140399 + 3362)) = 1).
  { rewrite Rabs_left1 by lra. lra. }
  assert (H2 : Rabs (143760 - (2 * 140399 + 3362)) = 140400).
  { rewrite Rabs_left1 by lra. lra. }
  lra.
Qed.

(* Sanity: the design point 1348 K is a root of the one-term balance to
   0.016 %, i.e. 22.2 W/m^2 out of 140399. *)
Theorem design_point_residual_small :
  Rabs (1404211640262531 / 10000000000 - 140399) <= 23.
Proof. apply Rabs_le. lra. Qed.

(* -------------------------------------------------------------------- *)
(* Counterexample 2 (machine-checked, exact rationals, no floats):       *)
(* the uniqueness theorem needs b to be a CONSTANT.  Let emissivity fall *)
(* faster than T^-4 above a threshold, which is what a coating that      *)
(* ablates or a semiconducting skin does: for T >= 1 take               *)
(*     eps(T)*sigma = b / T^8      (so eps ~ T^-8, steeper than T^-4),   *)
(* giving flux  g(T) = b / T^4  on that branch, continuous with the      *)
(* quartic branch b*T^4 at T = 1.  Then g(1/2) = b/16 and g(2) = b/16:   *)
(* the same flux at two different temperatures, so for q = b/16 the      *)
(* balance has TWO roots and "the" surface temperature is not unique.    *)
(* -------------------------------------------------------------------- *)
Theorem flux_not_injective :
  forall b : R, 0 < b ->
    exists T1 T2 : R, 0 < T1 /\ T1 < T2 /\ b * T1 ^ 4 = b / T2 ^ 4.
Proof.
  intros b hb.
  exists (1 / 2), 2.
  split; [lra | split; [lra | ]].
  replace ((1 / 2) ^ 4) with (1 / 16) by field.
  replace (2 ^ 4) with 16 by ring.
  field.
Qed.

Theorem two_roots_of_the_balance :
  forall b : R, 0 < b ->
    exists T1 T2 q : R,
      0 < T1 /\ T1 < T2 /\ b * T1 ^ 4 - q = 0 /\ b / T2 ^ 4 - q = 0.
Proof.
  intros b hb.
  destruct (flux_not_injective b hb) as [T1 [T2 [h1 [h2 heq]]]].
  exists T1, T2, (b * T1 ^ 4).
  split; [exact h1 | split; [exact h2 | split; [ring | ]]].
  rewrite <- heq. ring.
Qed.
