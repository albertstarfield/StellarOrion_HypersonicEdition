(* StellarOrion HypersonicEdition -- Rocq Formal Proofs
   =====================================================
   Machine-checked proofs of the core physics properties of the
   hypersonic trajectory model:

     * Mean Free Path -- lambda = 1 / (sqrt2 * pi * d * d * n) is
       strictly positive for physical inputs and strictly decreasing
       in the number density n.
     * Knudsen Number -- Kn = lambda / L is non-negative whenever
       lambda >= 0 and L > 0.
     * Ballistic Coefficient -- beta = m * q / F is strictly positive
       for positive mass, positive dynamic pressure and positive drag
       force, and is exactly proportional to mass.
     * Sutton-Graves Heat Flux -- q_stag = Csg * sqrt(rho / Rn) * V^3
       is non-negative and scales with the cube of the velocity.
     * Survivability Envelope -- Is_Survivable implies the surface
       temperature, backface temperature and g-load limits hold.

   AXIOMS: every quantity below is a real number; each lemma states
   exactly which physical hypothesis it assumes (positive number
   density, positive molecular diameter, positive sqrt2 and pi,
   positive characteristic length, positive drag force, ...).

   THEORIES: every lemma is discharged by a complete Qed proof. No
   placeholder remains anywhere in this file; each statement that the
   previous placeholder version got wrong is repaired in place and the
   counterexample that proves the old one false is recorded next to it.

   APPLICATIONS: these proofs are the machine-checked obligation that
   the Ada/SPARK implementation computing the same quantities must
   satisfy.

   CITATIONS:
     [1] Coq Reference Manual, Coq.Reals.RIneq and Coq.Reals.Rbase
         (Rmult_lt_0_compat, Rdiv_lt_0_compat, Rinv_0_lt_compat,
         Rinv_lt_contravar, Rmult_le_pos, sqrt_positivity).
         https://coq.inria.fr/library/Coq.Reals.RIneq.html
     [2] Coq Reference Manual, Coq.Reals.Rbase ring normalisation of
         the real field, used for the velocity-cubed scaling identity.
         https://coq.inria.fr/library/Coq.Reals.Rbase.html

   Author: Albert Starfield Wahyu Suryo Samudro *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
(* Every arithmetic step below is real arithmetic driven by lra; no
   integer-level reasoning occurs, so Coq.micromega.Lia is not needed. *)
Local Open Scope R_scope.

(* ==========================================================================
   Helpers -- small, independently proved facts used by the sections below.
   Each carries its own AXIOM / THEORY / CITATION, and each is stated with
   the exact connective shape its callers need.
   ========================================================================== *)

(* --------------------------------------------------------------------------
   AXIOM (H1): a and b are strictly positive reals.
   THEORY: taking reciprocals reverses the order on the positive reals,
   which is what makes a denser gas have a shorter mean free path.
   CITATION: Coq 8.18, Rinv_lt_contravar in Coq.Reals.RIneq,
        Rinv_lt_contravar : 0 < r1 * r2 -> r1 < r2 -> / r2 < / r1
   -------------------------------------------------------------------------- *)
Lemma rdiv_reciprocal_antitone :
  forall a b : R, 0 < a -> 0 < b -> a < b -> 1 / a > 1 / b.
Proof.
  intros a b Ha Hb Hab.
  unfold Rdiv.
  rewrite !Rmult_1_l.
  assert (Hinv : / b < / a).
  { apply Rinv_lt_contravar.
    - apply Rmult_lt_0_compat; [exact Ha | exact Hb].
    - exact Hab. }
  exact Hinv.
Qed.

(* --------------------------------------------------------------------------
   AXIOM (H2): none -- unconditional arithmetic. When y = 0 both sides are
   0 because Coq defines x / y as x * / y and / 0 = 0.
   THEORY: scaling the numerator of a quotient scales the quotient.
   CITATION: Coq 8.18, Rmult_assoc in Coq.Reals.Rbase.
   -------------------------------------------------------------------------- *)
Lemma rdiv_scale_numerator :
  forall c x y : R, c * (x / y) = (c * x) / y.
Proof.
  intros c x y.
  unfold Rdiv.
  rewrite <- (Rmult_assoc c x (/ y)).
  reflexivity.
Qed.

(* --------------------------------------------------------------------------
   AXIOM (H3): none -- unconditional arithmetic over the reals.
   THEORY: doubling a halved quantity returns the original; this is the
   algebraic content of "doubling the mass doubles beta".
   CITATION: Coq 8.18, Rinv_r / Rmult_1_r in Coq.Reals.Rbase.
   -------------------------------------------------------------------------- *)
Lemma double_the_half :
  forall x : R, 2 * (x / 2) = x.
Proof.
  intros x.
  assert (Hne : 2 <> 0) by lra.
  unfold Rdiv.
  rewrite <- (Rmult_assoc 2 x (/ 2)).
  rewrite (Rmult_comm 2 x).
  rewrite (Rmult_assoc x 2 (/ 2)).
  rewrite (Rinv_r 2 Hne).
  rewrite (Rmult_1_r x).
  reflexivity.
Qed.

(* ---- Mean Free Path Properties ---- *)
(* lambda > 0 when n, d, sqrt2 and pi are all > 0 *)
(* lambda decreases monotonically with n for fixed d, sqrt2, pi *)

Section MeanFreePath.
  Variable n : R.       (* number density [m^-3] *)
  Variable d : R.       (* molecular diameter [m] *)
  Variable sqrt2 : R.   (* sqrt(2) *)
  Variable pi : R.      (* pi *)

  (* Mean free path lambda = 1 / (sqrt2 * pi * d^2 * n), parameterised
     over the four quantities of the kinetic-theory formula. *)
  Definition mfp (sqrt2 pi d n : R) : R := 1 / (sqrt2 * pi * d * d * n).

  (* mfp_with n is the mean free path of THIS gas at number density n:
     the definition mfp specialised to the section variables sqrt2, pi, d. *)
  Definition mfp_with (n : R) : R := mfp sqrt2 pi d n.

  (* ------------------------------------------------------------------
     AXIOM: the number density, the molecular diameter and the two
     geometric constants are all strictly positive (physical gas).
     THEORY: the reciprocal of a strictly positive quantity is strictly
     positive (Rdiv_lt_0_compat), and the denominator is a product of
     five strictly positive factors (Rmult_lt_0_compat).
     CITATION: https://coq.inria.fr/library/Coq.Reals.RIneq.html

     STATEMENT REPAIR -- the previous version of this statement was
         n > 0 -> d > 0 -> mfp > 0
     which is FALSE as soon as sqrt2 = 0 or pi = 0, because the
     denominator vanishes and the quotient 1 / 0 is 0 in Coq, not > 0.
     COUNTEREXAMPLE (sqrt2 = 0): n = 1, d = 1, pi = 1 gives
         mfp = 1 / (0 * 1 * 1 * 1 * 1) = 1 / 0 = 0 ,  so 0 > 0 is false.
     The repaired statement adds the two missing strict premises
     sqrt2 > 0 and pi > 0; the conclusion is unchanged.
     ------------------------------------------------------------------ *)
  Lemma mfp_positive :
    n > 0 -> d > 0 -> sqrt2 > 0 -> pi > 0 ->
    mfp_with n > 0.
  Proof.
    intros Hn Hd Hs Hp.
    assert (Hden : 0 < sqrt2 * pi * d * d * n).
    { apply Rmult_lt_0_compat.
      - apply Rmult_lt_0_compat.
        + apply Rmult_lt_0_compat.
          * apply Rmult_lt_0_compat; lra.
          * lra.
        + lra.
      - lra. }
    unfold mfp_with, mfp.
    assert (Hpos : 0 < 1 / (sqrt2 * pi * d * d * n)).
    { apply Rdiv_lt_0_compat; [lra | exact Hden]. }
    exact Hpos.
  Qed.

  (* ------------------------------------------------------------------
     AXIOM: n1 and n2 are strictly positive number densities with
     n1 < n2, and d, sqrt2, pi are strictly positive.
     THEORY: the density-independent factor sqrt2 * pi * d * d is
     strictly positive, so multiplying both densities by it preserves
     the strict order (Rmult_lt_compat_l); the reciprocal then reverses
     the order (rdiv_reciprocal_antitone), hence a denser gas has a
     shorter mean free path.
     CITATION: https://coq.inria.fr/library/Coq.Reals.RIneq.html

     STATEMENT REPAIR -- the previous version did not require
     sqrt2 > 0 and pi > 0, so it was FALSE when sqrt2 = 0: every mean
     free path is then 1 / 0 = 0 and mfp_with n1 > mfp_with n2 collapses
     to 0 > 0.
     COUNTEREXAMPLE: n1 = 1, n2 = 2, d = 1, sqrt2 = 0, pi = 1.
     ------------------------------------------------------------------ *)
  Lemma mfp_monotone_decreasing :
    forall n1 n2 : R,
      n1 > 0 -> n2 > 0 -> n1 < n2 ->
      d > 0 -> sqrt2 > 0 -> pi > 0 ->
      mfp_with n1 > mfp_with n2.
  Proof.
    intros n1 n2 H1 H2 Hlt Hd Hs Hp.
    assert (HA : 0 < sqrt2 * pi * d * d).
    { apply Rmult_lt_0_compat.
      - apply Rmult_lt_0_compat.
        + apply Rmult_lt_0_compat; lra.
        + lra.
      - lra. }
    assert (Hn1 : 0 < sqrt2 * pi * d * d * n1).
    { apply Rmult_lt_0_compat; [exact HA | lra]. }
    assert (Hn2 : 0 < sqrt2 * pi * d * d * n2).
    { apply Rmult_lt_0_compat; [exact HA | lra]. }
    assert (Hlt2 : sqrt2 * pi * d * d * n1 < sqrt2 * pi * d * d * n2).
    { apply (Rmult_lt_compat_l (sqrt2 * pi * d * d) n1 n2).
      - exact HA.
      - exact Hlt. }
    unfold mfp_with, mfp.
    apply rdiv_reciprocal_antitone.
    - exact Hn1.
    - exact Hn2.
    - exact Hlt2.
  Qed.
End MeanFreePath.

(* ---- Knudsen Number Properties ---- *)
(* Kn >= 0 when the mean free path is non-negative and L > 0 *)
(* Kn < 0.01 is only a premise here; no regime predicate is claimed *)

Section KnudsenNumber.
  Variable mfp : R.     (* mean free path [m] *)
  Variable L : R.       (* characteristic length [m] *)

  Definition kn := mfp / L.

  (* ------------------------------------------------------------------
     AXIOM: the mean free path is non-negative and the characteristic
     length is strictly positive.
     THEORY: / L is non-negative for L > 0 (Rinv_0_lt_compat weakened
     by Rlt_le), and a product of non-negative reals is non-negative
     (Rmult_le_pos), so mfp / L >= 0.
     CITATION: https://coq.inria.fr/library/Coq.Reals.RIneq.html
     ------------------------------------------------------------------ *)
  Lemma kn_nonneg :
    mfp >= 0 -> L > 0 -> kn >= 0.
  Proof.
    intros Hm HL.
    (* Coq 8.18 defines x >= y as (x > y \/ x = y), which is NOT the same
       term as y <= x (the equality disjunct flips), so the premise and the
       goal are first restated in the native <= shape by Rge_le / Rle_ge. *)
    apply Rge_le in Hm.
    apply Rle_ge.
    assert (Hinv : 0 < / L) by (apply Rinv_0_lt_compat; exact HL).
    assert (Hinv_le : 0 <= / L) by (apply Rlt_le; exact Hinv).
    unfold kn, Rdiv.
    apply Rmult_le_pos; [exact Hm | exact Hinv_le].
  Qed.

  (* ------------------------------------------------------------------
     AXIOM: none beyond the type of kn; the premise kn < 0.01 is simply
     not needed by the conclusion.
     THEORY: the conclusion is the inductive unit True, whose single
     constructor I proves it whatever the premise is. The implication
     is therefore trivially true.
     HONESTY NOTE: this is a vacuous truth, NOT a continuum-regime
     result. Deriving "kn < 0.01 implies continuum regime" needs the
     regime predicate in the statement; this statement has none, so no
     such content is asserted or invented.
     CITATION: Coq 8.18 standard inductive type True.
     ------------------------------------------------------------------ *)
  Lemma kn_regime_transition :
    kn < 0.01 -> (* continuum *)
    True.
  Proof.
    intros Hkn.
    (* Trivially true: True's sole constructor I proves the goal for
       any premise. No regime content can be derived from a bare
       kn < 0.01 premise, and none is claimed. *)
    exact I.
  Qed.
End KnudsenNumber.

(* ---- Ballistic Coefficient Properties ---- *)
(* beta > 0 when m > 0, q > 0 and F_drag > 0 *)
(* doubling mass doubles beta *)

Section BallisticCoeff.
  Variable m : R.       (* mass [kg] *)
  Variable q : R.       (* dynamic pressure [Pa] *)
  Variable F : R.       (* drag force [N] *)

  (* Ballistic coefficient beta = m * q / F, parameterised over the three
     per-call quantities. *)
  Definition beta (m q F : R) : R := m * q / F.

  (* ------------------------------------------------------------------
     AXIOM: mass, dynamic pressure and drag force are strictly positive.

     STATEMENT REPAIR -- the previous version of this statement was
         m > 0 -> q >= 0 -> F > 0 -> beta > 0
     which is FALSE at q = 0: beta = m * 0 / F = 0, and 0 is not > 0.
     COUNTEREXAMPLE: m = 1, q = 0, F = 1 gives beta = 0, so 0 > 0 fails.
     The repaired statement keeps the conclusion beta > 0 and tightens
     the premise from q >= 0 to q > 0; nothing else changes.

     THEORY: m * q is strictly positive (Rmult_lt_0_compat) and 1 / F is
     strictly positive (Rdiv_lt_0_compat), hence the quotient is strictly
     positive.
     CITATION: https://coq.inria.fr/library/Coq.Reals.RIneq.html
     ------------------------------------------------------------------ *)
  Lemma beta_positive :
    m > 0 -> q > 0 -> F > 0 -> beta m q F > 0.
  Proof.
    intros Hm Hq HF.
    assert (Hnum : 0 < m * q).
    { apply Rmult_lt_0_compat; [exact Hm | exact Hq]. }
    unfold beta.
    assert (Hpos : 0 < m * q / F).
    { apply Rdiv_lt_0_compat; [exact Hnum | exact HF]. }
    exact Hpos.
  Qed.

  (* ------------------------------------------------------------------
     AXIOM: none -- the identity holds for every m, q and F. When F = 0
     both sides are 0, since Coq defines x / 0 as x * / 0 = 0.
     THEORY: beta is linear in the mass: scaling the numerator of a
     quotient scales the quotient (rdiv_scale_numerator) and halving then
     doubling the mass is the identity (double_the_half).
     CITATION: helpers rdiv_scale_numerator / double_the_half above.
     ------------------------------------------------------------------ *)
  Lemma beta_proportional_to_mass :
    (* Doubling mass doubles beta (q, F fixed) *)
    beta m q F = 2 * beta (m / 2) q F.
  Proof.
    intros.
    assert (Hnum : 2 * ((m / 2) * q) = m * q).
    { rewrite <- (Rmult_assoc 2 (m / 2) q).
      rewrite (double_the_half m).
      reflexivity. }
    unfold beta.
    rewrite (rdiv_scale_numerator 2 ((m / 2) * q) F).
    rewrite Hnum.
    reflexivity.
  Qed.
End BallisticCoeff.

(* ---- Sutton-Graves Heat Flux Properties ---- *)
(* q_stag >= 0 for valid inputs: rho >= 0, Rn > 0, V >= 0, Csg > 0 *)
(* q_stag scales with the cube of the velocity *)

Section SuttonGraves.
  Variable rho : R.     (* density [kg/m^3] *)
  Variable Rn : R.      (* nose radius [m] *)
  Variable V : R.       (* velocity [m/s] *)
  Variable Csg : R.     (* Sutton-Graves constant *)

  (* Stagnation heat flux q_stag = Csg * sqrt(rho / Rn) * V^3, parameterised
     over the three per-call quantities rho, Rn and V; Csg is the section
     constant. *)
  Definition q_sg (rho Rn V : R) : R := Csg * sqrt (rho / Rn) * V * V * V.

  (* ------------------------------------------------------------------
     AXIOM: rho >= 0, Rn > 0, V >= 0 and Csg > 0 (physical re-entry).
     THEORY: rho / Rn >= 0 (non-negative over positive), so its square
     root is non-negative (sqrt_positivity); Csg > 0 times a non-negative
     factor is non-negative (Rmult_le_pos), and V^3 >= 0 is a product of
     three non-negative factors.
     CITATION: https://coq.inria.fr/library/Coq.Reals.RIneq.html
     ------------------------------------------------------------------ *)
  Lemma q_sg_nonneg :
    rho >= 0 -> Rn > 0 -> V >= 0 -> Csg > 0 -> q_sg rho Rn V >= 0.
  Proof.
    intros Hrho HRn HV HCsg.
    (* Coq 8.18 defines x >= y as (x > y \/ x = y), which is NOT the same
       term as y <= x (the equality disjunct flips), so both >= premises and
       the >= goal are restated in the native <= shape first. *)
    apply Rge_le in Hrho.
    apply Rge_le in HV.
    apply Rle_ge.
    assert (Hinv : 0 < / Rn) by (apply Rinv_0_lt_compat; exact HRn).
    assert (Hinv_le : 0 <= / Rn) by (apply Rlt_le; exact Hinv).
    assert (Hdiv : 0 <= rho / Rn).
    { unfold Rdiv. apply Rmult_le_pos; [exact Hrho | exact Hinv_le]. }
    assert (Hsq : 0 <= sqrt (rho / Rn)) by (apply sqrt_positivity; exact Hdiv).
    assert (HA : 0 <= Csg * sqrt (rho / Rn)).
    { apply Rmult_le_pos; [apply Rlt_le; exact HCsg | exact Hsq]. }
    unfold q_sg.
    apply Rmult_le_pos.
    - apply Rmult_le_pos.
      + apply Rmult_le_pos; [exact HA | exact HV].
      + exact HV.
    - exact HV.
  Qed.

  (* ------------------------------------------------------------------
     AXIOM: the velocity is rescaled by a strictly positive factor.
     THEORY: (k * V)^3 = k^3 * V^3 is a commutative-ring identity, so the
     Csg * sqrt(rho / Rn) prefactor is untouched and only the cubic power
     of the velocity absorbs the factor.
     CITATION: Coq 8.18 ring normalisation of the real closed field.
     ------------------------------------------------------------------ *)
  Lemma q_sg_velocity_cubic :
    forall k : R, k > 0 ->
      q_sg rho Rn (k * V) = k * k * k * q_sg rho Rn V.
  Proof.
    intros k Hk.
    unfold q_sg.
    ring.
  Qed.
End SuttonGraves.

(* ---- Survivability Envelope ---- *)
(* Is_Survivable implies all temps within limits *)

Section Survivability.
  Variable T_surface : R.
  Variable T_backface : R.
  Variable g_load : R.

  Variable SiC_max : R.     (* 2073 K *)
  Variable Kapton_max : R.  (* 773 K *)
  Variable g_max : R.       (* 25 g *)

  Definition survivable :=
    T_surface <= SiC_max /\
    T_backface <= Kapton_max /\
    g_load <= g_max.

  (* ------------------------------------------------------------------
     AXIOM: the three measured quantities and their three limits are
     reals; no physical inequality is assumed.
     THEORY: survivable is a conjunction of three bounds; the first two
     conjuncts are exactly the two temperature bounds, so destructing
     the conjunction discharges the goal.
     CITATION: not needed -- propositional reasoning only.
     ------------------------------------------------------------------ *)
  Lemma survivability_implies_temp_bounds :
    survivable ->
    T_surface <= SiC_max /\ T_backface <= Kapton_max.
  Proof.
    intros Hsur.
    unfold survivable in Hsur.
    destruct Hsur as [H1 [H2 H3]].
    split.
    - exact H1.
    - exact H2.
  Qed.

  (* ------------------------------------------------------------------
     AXIOM: as above.
     THEORY: the third conjunct of survivable is exactly g_load <= g_max,
     so destructing the conjunction yields it directly.
     CITATION: not needed -- propositional reasoning only.
     ------------------------------------------------------------------ *)
  Lemma survivability_implies_g_bound :
    survivable ->
    g_load <= g_max.
  Proof.
    intros Hsur.
    unfold survivable in Hsur.
    destruct Hsur as [H1 [H2 H3]].
    exact H3.
  Qed.
End Survivability.
