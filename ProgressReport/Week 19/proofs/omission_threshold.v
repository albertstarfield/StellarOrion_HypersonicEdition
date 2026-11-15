(*  omission_threshold.v

    The process answer's logic in one line: dropping the Rosseland term is
    legitimate exactly when the extinction coefficient is at least a threshold,
    so the deck's unconditional "the term is dropped here" is false exactly
    below that threshold.  That is an algebraic equivalence, not an opinion, and
    this file proves it over the reals.

    WHAT COULD FAIL.  The equivalence turns a physical question (is the gas
    optically thick?) into one arithmetic comparison, and that is only as good
    as the coefficient formula.  The formula is cited, not proved here --
    Fluent 5.3.4 and CHAM Eqn 7.1.  What IS proved: the equivalence, the
    tightness of the boundary, and a non-empty region where the omission is not
    legitimate.

    Compiled with:  rocq compile proofs/omission_threshold.v
*)

From Stdlib Require Import Reals RIneq.
From Stdlib.micromega Require Import Lra Psatz.

Open Scope R_scope.

(* Helper, proved by hand because this stdlib build does not export
   Rdiv_le_iff: for a positive denominator, division by it is
   cross-multiplication. *)
Lemma le_div_iff : forall a b c : R, 0 < c -> (a / c <= b <-> a <= b * c).
Proof.
  intros a b c Hc.
  assert (Hc' : c <> 0) by nra.
  split.
  - intro H.
    assert (Hle : a / c * c <= b * c) by (apply Rmult_le_compat_r; lra).
    unfold Rdiv in Hle.
    rewrite Rmult_assoc in Hle.
    rewrite Rinv_l in Hle; [| exact Hc'].
    rewrite Rmult_1_r in Hle.
    exact Hle.
  - intro H.
    assert (Hinv : 0 < / c) by (apply Rinv_0_lt_compat; lra).
    assert (H2 : a * / c <= b * c * / c) by (apply Rmult_le_compat_r; lra).
    rewrite Rmult_assoc in H2.
    rewrite Rinv_r in H2; [| exact Hc'].
    rewrite Rmult_1_r in H2.
    unfold Rdiv.
    exact H2.
Qed.

(* Rosseland volumetric conductivity, W/(m*K). *)
Definition k_rosseland (sigma kappa T : R) : R := 16 * sigma * T ^ 3 / (3 * kappa).

(* The extinction coefficient at which the term equals the gas conductivity. *)
Definition threshold (sigma T kgas : R) : R := 16 * sigma * T ^ 3 / (3 * kgas).

(* THE CORE EQUIVALENCE.  The omission is legitimate iff kappa is at least the
   threshold: both sides cross-multiply to 16*sigma*T^3 <= 3*kappa*k_gas. *)
Theorem omission_is_legitimate_iff :
  forall sigma T kappa kgas : R,
    0 < sigma -> 0 < T -> 0 < kappa -> 0 < kgas ->
    (k_rosseland sigma kappa T <= kgas <-> threshold sigma T kgas <= kappa).
Proof.
  intros sigma T kappa kgas Hs HT Hk Hg.
  unfold k_rosseland, threshold.
  assert (H3k : 0 < 3 * kappa) by nra.
  assert (H3g : 0 < 3 * kgas) by nra.
  rewrite (le_div_iff (16 * sigma * T ^ 3) kgas (3 * kappa) H3k).
  rewrite (le_div_iff (16 * sigma * T ^ 3) kappa (3 * kgas) H3g).
  split; intro H; nra.
Qed.

(* THE REFUTATION REGION IS NON-EMPTY.  Below the threshold the omission is not
   legitimate -- that is exactly where the deck's blanket sentence is false. *)
Theorem omission_false_below_threshold :
  forall sigma T kappa kgas : R,
    0 < sigma -> 0 < T -> 0 < kappa -> 0 < kgas ->
    kappa < threshold sigma T kgas -> kgas < k_rosseland sigma kappa T.
Proof.
  intros sigma T kappa kgas Hs HT Hk Hg Hlt.
  assert (Hnle : ~ (k_rosseland sigma kappa T <= kgas)).
  - intro Hle.
    pose proof (proj1 (omission_is_legitimate_iff sigma T kappa kgas Hs HT Hk Hg) Hle) as Hth.
    lra.
  - lra.
Qed.

(* At the threshold itself the omission is exactly legitimate: the boundary is
   tight, so no gap hides between "dropped" and "kept". *)
Theorem omission_legitimate_at_threshold :
  forall sigma T kgas : R,
    0 < sigma -> 0 < T -> 0 < kgas ->
    k_rosseland sigma (threshold sigma T kgas) T = kgas.
Proof.
  intros sigma T kgas Hs HT Hg.
  unfold k_rosseland, threshold.
  assert (H3g : 3 * kgas <> 0) by nra.
  field. nra.
Qed.

(* Numerical witness at the deck's own quoted temperature: with
   sigma = 5.670374419e-8 and k_gas = 0.1, the threshold exceeds 700 1/m, so
   740 and 74080 land on opposite sides of the refutation region. *)
Theorem small_kappa_keeps_the_term :
  threshold (5670374419 / 10 ^ 17) 1348 (1 / 10) > 700.
Proof. unfold threshold. lra. Qed.
