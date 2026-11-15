(*  identifiability.v

    The question behind "why add another radiation term into the conduction"
    is not rhetorical: it is whether one operating point can tell the two
    models apart.  This file answers it in both directions.

    1. ONE POINT CANNOT.  For any radiation coefficient b there is a conduction
       coefficient c' = c + b*T^3 that reproduces the same residual at T.  So a
       single-point closure check -- which is exactly what check 3 on the slide
       is -- is *no evidence at all* about whether the term belongs there.

    2. TWO POINTS CAN.  If the same (c, q) fits two distinct temperatures under
       both coefficients, then the coefficients are equal.  The balance is
       over-determined as soon as you have two operating points, so the term is
       measurable rather than a matter of taste.

    3. WHAT HIDING IT COSTS.  At the deck's own 1348 K, absorbing a 10 % share
       forces the conduction coefficient to be wrong by 14376/1348 =
       10.665 W/(m^2 K) -- more than a hundredfold the illustrative
       0.1 W/(m K) gas conductivity.

    THE STEP THAT COULD FAIL is (2): it assumes c and q are the same in both
    models, i.e. that the conduction coefficient is a property of the gas and
    not a fit parameter.  If c is free per model, only (1) holds and the term is
    formally unidentifiable from any number of points -- which is precisely why
    the deck must state which coefficients are fixed.

    Compiled with:  rocq compile proofs/identifiability.v
*)

From Stdlib Require Import Reals RIneq.
From Stdlib.micromega Require Import Lra Psatz.

Open Scope R_scope.

(* The wall balance: radiative coefficient K on T^4, conduction c on T, flux q. *)
Definition wallBalance (K c q T : R) : R := K * T ^ 4 + c * T - q.

(* (1) A single point never separates the models: the omission can always be
   laundered through the conduction coefficient. *)
Theorem single_point_cannot_separate :
  forall K b c q T : R, 0 < T ->
    wallBalance K (c + b * T ^ 3) q T = wallBalance (K + b) c q T.
Proof.
  intros K b c q T HT.
  unfold wallBalance.
  ring.
Qed.

(* (1') The compensating error is explicit: it is exactly b*T^3. *)
Theorem compensating_conduction_error :
  forall K b c c' q T : R, 0 < T ->
    wallBalance (K + b) c q T = 0 ->
    wallBalance K c' q T = 0 ->
    c' = c + b * T ^ 3.
Proof.
  intros K b c c' q T HT H1 H2.
  unfold wallBalance in *.
  assert (H : b * T ^ 4 + c * T - c' * T = 0) by nra.
  assert (Hfac : b * T ^ 4 = b * T ^ 3 * T) by ring.
  rewrite Hfac in H.
  assert (HT' : T <> 0) by lra.
  assert (H3 : (b * T ^ 3 + c - c') * T = 0) by nra.
  destruct (Rmult_integral _ _ H3) as [Hz | Hz].
  - lra.
  - contradiction.
Qed.

(* (2) Two distinct temperatures do separate them, provided c and q are shared. *)
Theorem two_points_identify_the_radiation_coefficient :
  forall K1 K2 c q T1 T2 : R,
    0 < T1 -> 0 < T2 ->
    wallBalance K1 c q T1 = 0 -> wallBalance K1 c q T2 = 0 ->
    wallBalance K2 c q T1 = 0 -> wallBalance K2 c q T2 = 0 ->
    T1 <> T2 -> K1 = K2.
Proof.
  intros K1 K2 c q T1 T2 H1pos H2pos A1 A2 B1 B2 Hne.
  unfold wallBalance in *.
  assert (H : (K1 - K2) * T1 ^ 4 = 0) by nra.
  assert (HT : T1 ^ 4 <> 0) by (apply pow_nonzero; lra).
  destruct (Rmult_integral _ _ H) as [Hd | Hz].
  - lra.
  - contradiction.
Qed.

(* (3) What it costs to hide a 10 % share at the deck's 1348 K: the conduction
   coefficient must move by 14376/1348 W/(m^2 K), which is more than 100x the
   illustrative 0.1 W/(m K).  Cross-multiplied so no division is needed. *)
Theorem hiding_ten_percent_costs_more_than_a_hundredfold :
  14376 > 100 * (1348 * (1 / 10)).
Proof. lra. Qed.

(* The same statement at 1 %: still more than a tenfold error. *)
Theorem hiding_one_percent_costs_more_than_tenfold :
  1437 > 10 * (1348 * (1 / 10)).
Proof. lra. Qed.
