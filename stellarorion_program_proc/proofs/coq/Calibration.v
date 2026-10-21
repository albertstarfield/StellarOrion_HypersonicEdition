(* =====================================================================
   StellarOrion CALIBRATION — Coq/Rocq companion to the Lean 4 proofs.

   PURPOSE
       Prove, over the real numbers, the algebraic core of the Stage-1/2
       calibration of the StellarOrion screening model
       (CALIBRATION_DESIGN.md §2.6, §2.6.1, §2.7): the 7-term orthogonal
       residual model {1, x1, x2, x3, x1*x2, x1*x3, x2*x3} fitted over the
       coded 2^3 factorial layout is EXACT for every response that lies in
       the model span, and the orthogonality of the design is what makes the
       closed-form contrast fit the exact least-squares solution.

   AXIOMS
     A1  The coded 2^3 factorial design is the 8 sign vectors of {+1,-1}^3.
     A2  The three FACTOR columns are centred and orthogonal: a column sums
         to zero, the self-product of a column sums to 8, and the
         cross-product of two distinct columns sums to zero.
     A3  The seven MONOMIAL basis functions {1, x1, x2, x3, x1*x2, x1*x3,
         x2*x3} are mutually orthogonal on the design: the Gram matrix of the
         basis is 8*I.
     A4  The closed-form contrast fit is
           b0   = (1/8) * sum(y),
           b_k  = (1/8) * sum(x_k * y),
           b_ij = (1/8) * sum(x_k * x_j * y),
         and the evaluation is
           b0 + b1*x1 + b2*x2 + b3*x3 + b4*x1*x2 + b5*x1*x3 + b6*x2*x3.
     A5  The contrast fit reproduces EXACTLY every response in the model
         span, and a model response whose contrasts all vanish is the zero
         response.
     A6  The fit preserves the sample mean and every one of the seven
         contrasts.

   THEORIES
     T1  (Gauss 1809; Montgomery 2017 Ch. 6/7) A centred orthogonal design
         decouples the mean from the contrasts, so the closed-form contrast
         fit IS the exact least-squares solution.
     T2  (Kennedy & O'Hagan 2000, Biometrika 87(1)) An additive residual
         correction fitted on an orthogonal basis is exact for responses in
         the model span and vanishes identically when the model is right.

   CITATIONS
     - McKay, D. et al. (1979), "A comparison of three methods for selecting
       values of input variables", Technometrics 21(2), 239-248.
     - Montgomery, D.C. (2017), "Design and Analysis of Experiments", 9th ed.
     - Gauss, C.F. (1809), "Theoria Motus Corporum Coelestium".
     - Kennedy, M.C. & O'Hagan, A. (2000), "Bayesian calibration of computer
       models", Biometrika 87(1), 65-82.

   MODEL NOTE
       The Ada/SPARK implementation fits in Float; the statements below are
       the exact real-number versions of the same algebra.  The Lean 4
       companion (proofs/lean/StellarOrionProofs/Calibration.lean) proves
       the integer-scaled (norm 8) forms over Z.  This file is
       SELF-CONTAINED on purpose: it does not `Require` any sibling file, so
       `coqc Calibration.v` succeeds standalone and the repository proof
       gate (src/utils/coq_proof_gate.py) can compile it in any order.
   ===================================================================== *)

Require Import Reals.
Require Import Lra.
Require Import Psatz.
Require Import Field.
Require Import List.
Require Import Arith.
Require Import Lia.
Import ListNotations.
Open Scope R_scope.

(* =====================================================================
   1. The coded 2^3 factorial design
   ===================================================================== *)

(* The sign of FACTOR k (0 = x1, 1 = x2, 2 = x3) at coded design POINT i.
   The layout is the classical one: x1 flips at i = 4, x2 at i = 2 and x3
   at i = 1. *)
Definition xsign (i k : nat) : R :=
  match k, i with
  | 0, 0 => 1 | 0, 1 => 1 | 0, 2 => 1 | 0, 3 => 1
  | 0, 4 => -1 | 0, 5 => -1 | 0, 6 => -1 | 0, _ => -1
  | 1, 0 => 1 | 1, 1 => 1 | 1, 2 => -1 | 1, 3 => -1
  | 1, 4 => 1 | 1, 5 => 1 | 1, 6 => -1 | 1, _ => -1
  | 2, 0 => 1 | 2, 1 => -1 | 2, 2 => 1 | 2, 3 => -1
  | 2, 4 => 1 | 2, 5 => -1 | 2, 6 => 1 | 2, _ => -1
  | _, _ => 0
  end.

(* The sum of a function over the eight coded design points. *)
Definition sum8 (f : nat -> R) : R :=
  f 0%nat + f 1%nat + f 2%nat + f 3%nat + f 4%nat + f 5%nat + f 6%nat + f 7%nat.

(* =====================================================================
   2. The seven monomial basis functions
   ===================================================================== *)

(* The k-th monomial basis function of CALIBRATION_DESIGN §2.6:
     0 -> 1, 1 -> x1, 2 -> x2, 3 -> x3,
     4 -> x1*x2, 5 -> x1*x3, 6 -> x2*x3. *)
Definition mono (k i : nat) : R :=
  match k with
  | 0 => 1
  | 1 => xsign i 0
  | 2 => xsign i 1
  | 3 => xsign i 2
  | 4 => xsign i 0 * xsign i 1
  | 5 => xsign i 0 * xsign i 2
  | 6 => xsign i 1 * xsign i 2
  | _ => 0
  end.

(* The k-th fitted coefficient of the model, 0-based. *)
Definition coefficient (c0 c1 c2 c3 c4 c5 c6 : R) (k : nat) : R :=
  match k with
  | 0 => c0 | 1 => c1 | 2 => c2 | 3 => c3
  | 4 => c4 | 5 => c5 | 6 => c6
  | _ => 0
  end.

(* =====================================================================
   3. AXIOM A2 — the factor design is centred and orthogonal
   ===================================================================== *)

(* AXIOM A2: every factor column sums to zero (the design is centred). *)
Lemma design_centred : forall j : nat, Nat.le j 2 ->
  sum8 (fun i => xsign i j) = 0.
Proof.
  intros j Hj. destruct j as [|[|[|j]]]; try lia;
    unfold sum8, xsign; simpl; ring.
Qed.

(* AXIOM A2: the self-product of a factor column sums to 8
   (sum_i x_ik^2 = 8 for every k). *)
Lemma design_self : forall j : nat, Nat.le j 2 ->
  sum8 (fun i => xsign i j * xsign i j) = 8.
Proof.
  intros j Hj. destruct j as [|[|[|j]]]; try lia;
    unfold sum8, xsign; simpl; ring.
Qed.

(* AXIOM A2: the cross-product of two DISTINCT factor columns sums to zero
   (sum_i x_ik x_jl = 0 for k <> l). *)
Lemma design_cross : forall j k : nat, Nat.le j 2 -> Nat.le k 2 -> j <> k ->
  sum8 (fun i => xsign i j * xsign i k) = 0.
Proof.
  intros j k Hj Hk Hne.
  destruct j as [|[|[|j]]]; destruct k as [|[|[|k]]]; try lia;
    try (exfalso; apply Hne; reflexivity);
    unfold sum8, xsign; simpl; ring.
Qed.

(* =====================================================================
   4. AXIOM A3 — the seven monomial basis functions are orthogonal
   ===================================================================== *)

(* The Gram entry of the basis: 8 on the diagonal, 0 off it. *)
Lemma basis_gram_value : forall k l : nat, Nat.le k 6 -> Nat.le l 6 ->
  sum8 (fun i => mono k i * mono l i) = if Nat.eqb k l then 8 else 0.
Proof.
  intros k l Hk Hl.
  destruct k as [|[|[|[|[|[|[|k]]]]]]]; destruct l as [|[|[|[|[|[|[|l]]]]]]];
    try lia;
    unfold sum8, mono, xsign; simpl; ring.
Qed.

(* AXIOM A3, as an IFF so that the two directions can be used separately. *)
Lemma basis_gram_iff : forall k l : nat, Nat.le k 6 -> Nat.le l 6 ->
  (k <> l <-> sum8 (fun i => mono k i * mono l i) = 0).
Proof.
  intros k l Hk Hl. rewrite (basis_gram_value k l Hk Hl).
  destruct (Nat.eqb k l) eqn:E.
  - split.
    + intro Hne. exfalso. apply Hne.
      apply (proj1 (Nat.eqb_eq k l)). exact E.
    + intro H. exfalso. lra.
  - split.
    + intro Hne. reflexivity.
    + intro H. apply (proj1 (Nat.eqb_neq k l)). exact E.
Qed.

(* AXIOM A3, cross case: the cross-product of two DISTINCT basis functions
   sums to zero. *)
Lemma basis_cross_zero : forall k l : nat, Nat.le k 6 -> Nat.le l 6 -> k <> l ->
  sum8 (fun i => mono k i * mono l i) = 0.
Proof.
  intros k l Hk Hl Hne.
  apply (proj1 (basis_gram_iff k l Hk Hl)) in Hne.
  exact Hne.
Qed.

(* AXIOM A3, diagonal case: the squared norm of a basis function is 8. *)
Lemma basis_self_eight : forall k : nat, Nat.le k 6 ->
  sum8 (fun i => mono k i * mono k i) = 8.
Proof.
  intros k Hk.
  assert (H := basis_gram_value k k Hk Hk).
  rewrite Nat.eqb_refl in H.
  simpl in H. exact H.
Qed.

(* =====================================================================
   5. AXIOM A4 — the closed-form contrast fit
   ===================================================================== *)

(* The k-th contrast numerator: sum_i mono_k(i) * y_i. *)
Definition contrast (y : nat -> R) (k : nat) : R :=
  sum8 (fun i => mono k i * y i).

(* The k-th fitted coefficient, b_k = (1/8) * contrast_k.  The divisor is
   the squared norm of the design (8), never zero. *)
Definition bcoef (y : nat -> R) (k : nat) : R := contrast y k / 8.

(* The seven fitted coefficients. *)
Definition b0 (y : nat -> R) : R := bcoef y 0%nat.
Definition b1 (y : nat -> R) : R := bcoef y 1%nat.
Definition b2 (y : nat -> R) : R := bcoef y 2%nat.
Definition b3 (y : nat -> R) : R := bcoef y 3%nat.
Definition b4 (y : nat -> R) : R := bcoef y 4%nat.
Definition b5 (y : nat -> R) : R := bcoef y 5%nat.
Definition b6 (y : nat -> R) : R := bcoef y 6%nat.

(* The fitted response at a coded design point: the 7-term orthogonal
   model evaluated with the fitted coefficients. *)
Definition fit (y : nat -> R) (i : nat) : R :=
  bcoef y 0%nat * mono 0 i + bcoef y 1%nat * mono 1 i
  + bcoef y 2%nat * mono 2 i + bcoef y 3%nat * mono 3 i
  + bcoef y 4%nat * mono 4 i + bcoef y 5%nat * mono 5 i
  + bcoef y 6%nat * mono 6 i.

(* The 7-term model evaluated at a coded point, written out with the
   explicit monomials of CALIBRATION_DESIGN §2.6. *)
Definition evaluate (c0 c1 c2 c3 c4 c5 c6 : R) (i : nat) : R :=
  c0 + c1 * xsign i 0 + c2 * xsign i 1 + c3 * xsign i 2
  + c4 * (xsign i 0 * xsign i 1) + c5 * (xsign i 0 * xsign i 2)
  + c6 * (xsign i 1 * xsign i 2).

(* A response lying in the span of the seven basis monomials. *)
Definition model (c0 c1 c2 c3 c4 c5 c6 : R) (i : nat) : R :=
  evaluate c0 c1 c2 c3 c4 c5 c6 i.

(* AXIOM A4: the evaluation IS the 7-term expansion. *)
Lemma evaluate_expansion : forall c0 c1 c2 c3 c4 c5 c6 : R, forall i : nat,
  evaluate c0 c1 c2 c3 c4 c5 c6 i =
    c0 + c1 * xsign i 0 + c2 * xsign i 1 + c3 * xsign i 2
    + c4 * (xsign i 0 * xsign i 1) + c5 * (xsign i 0 * xsign i 2)
    + c6 * (xsign i 1 * xsign i 2).
Proof.
  reflexivity.
Qed.

(* AXIOM A4: the fitted grand-mean coefficient is (1/8)*sum(y). *)
Lemma b0_formula : forall y : nat -> R, b0 y = (sum8 y) / 8.
Proof.
  intros y. unfold b0, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* AXIOM A4: the fitted x1 coefficient is (1/8)*sum(x1*y). *)
Lemma b1_formula : forall y : nat -> R, b1 y = (sum8 (fun i => xsign i 0 * y i)) / 8.
Proof.
  intros y. unfold b1, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* AXIOM A4: the fitted x2 coefficient is (1/8)*sum(x2*y). *)
Lemma b2_formula : forall y : nat -> R, b2 y = (sum8 (fun i => xsign i 1 * y i)) / 8.
Proof.
  intros y. unfold b2, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* AXIOM A4: the fitted x3 coefficient is (1/8)*sum(x3*y). *)
Lemma b3_formula : forall y : nat -> R, b3 y = (sum8 (fun i => xsign i 2 * y i)) / 8.
Proof.
  intros y. unfold b3, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* AXIOM A4: the fitted x1*x2 interaction coefficient is
   (1/8)*sum(x1*x2*y). *)
Lemma b4_formula : forall y : nat -> R,
  b4 y = (sum8 (fun i => xsign i 0 * xsign i 1 * y i)) / 8.
Proof.
  intros y. unfold b4, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* AXIOM A4: the fitted x1*x3 interaction coefficient is
   (1/8)*sum(x1*x3*y). *)
Lemma b5_formula : forall y : nat -> R,
  b5 y = (sum8 (fun i => xsign i 0 * xsign i 2 * y i)) / 8.
Proof.
  intros y. unfold b5, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* AXIOM A4: the fitted x2*x3 interaction coefficient is
   (1/8)*sum(x2*x3*y). *)
Lemma b6_formula : forall y : nat -> R,
  b6 y = (sum8 (fun i => xsign i 1 * xsign i 2 * y i)) / 8.
Proof.
  intros y. unfold b6, bcoef, contrast, mono, sum8. simpl. field; lra.
Qed.

(* =====================================================================
   6. AXIOM A5 — the contrast fit is exact on the model span
   ===================================================================== *)

(* The k-th contrast of a MODEL response is 8 times the k-th coefficient:
   this is the orthogonality (AXIOM A3) acting on the model span. *)
Lemma contrast_of_model : forall c0 c1 c2 c3 c4 c5 c6 : R, forall k : nat, Nat.le k 6 ->
  contrast (model c0 c1 c2 c3 c4 c5 c6) k
    = 8 * coefficient c0 c1 c2 c3 c4 c5 c6 k.
Proof.
  intros c0 c1 c2 c3 c4 c5 c6 k Hk.
  destruct k as [|[|[|[|[|[|[|k]]]]]]]; try lia;
    unfold contrast, sum8, mono, xsign, model, evaluate, coefficient;
    simpl; ring.
Qed.

(* AXIOM A5 / THEORY T1: the closed-form contrast fit reproduces EXACTLY
   every response that lies in the span of the seven basis monomials. *)
Lemma fit_reproduces_model : forall c0 c1 c2 c3 c4 c5 c6 : R, forall i : nat,
  fit (model c0 c1 c2 c3 c4 c5 c6) i = model c0 c1 c2 c3 c4 c5 c6 i.
Proof.
  intros c0 c1 c2 c3 c4 c5 c6 i.
  unfold fit, bcoef.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 0%nat) by lia.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 1%nat) by lia.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 2%nat) by lia.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 3%nat) by lia.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 4%nat) by lia.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 5%nat) by lia.
  rewrite (contrast_of_model c0 c1 c2 c3 c4 c5 c6 6%nat) by lia.
  unfold model, evaluate, mono, xsign, coefficient. simpl. field; lra.
Qed.

(* AXIOM A5 (converse half): a model response whose contrasts all vanish
   has all seven coefficients zero.  The product-zero direction is
   `Rmult_integral`. *)
Lemma model_zero_of_zero_contrast : forall c0 c1 c2 c3 c4 c5 c6 : R, forall k : nat,
  Nat.le k 6 ->
  (forall j : nat, Nat.le j 6 ->
     contrast (model c0 c1 c2 c3 c4 c5 c6) j = 0) ->
  coefficient c0 c1 c2 c3 c4 c5 c6 k = 0.
Proof.
  intros c0 c1 c2 c3 c4 c5 c6 k Hk H.
  assert (Hz : 8 * coefficient c0 c1 c2 c3 c4 c5 c6 k = 0).
  { rewrite <- (contrast_of_model c0 c1 c2 c3 c4 c5 c6 k Hk).
    apply (H k Hk). }
  apply Rmult_integral in Hz.
  destruct Hz as [Hz | Hz]; [lra | exact Hz].
Qed.

(* =====================================================================
   7. AXIOM A6 — the fit preserves the mean and the contrasts
   ===================================================================== *)

(* AXIOM A6 / THEORY T3: the fit preserves the sample mean — the sum of
   the fitted responses equals the sum of the responses. *)
Lemma fit_preserves_mean : forall y : nat -> R,
  sum8 (fun i => fit y i) = sum8 y.
Proof.
  intros y. unfold fit, bcoef, contrast, sum8, mono, xsign. simpl. field; lra.
Qed.

(* AXIOM A6 / THEORY T3: the fit preserves every one of the seven
   contrasts. *)
Lemma fit_preserves_contrast : forall y : nat -> R, forall k : nat, Nat.le k 6 ->
  sum8 (fun i => mono k i * fit y i) = sum8 (fun i => mono k i * y i).
Proof.
  intros y k Hk.
  destruct k as [|[|[|[|[|[|[|k]]]]]]]; try lia;
    unfold fit, bcoef, contrast, sum8, mono, xsign; simpl; field; lra.
Qed.
