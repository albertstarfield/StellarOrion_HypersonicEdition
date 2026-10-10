(* ============================================================================
   Coq proof companion for src/simulation_engine/stellarorion_postprocessing
   Ada 2012 / SPARK 2014.

   AXIOM (P1) [Sutherland's law]: Sutherland (1893) gives the dynamic
   viscosity of a gas as
        mu(T) = mu_ref * (T / T_ref)^1.5 * (T_ref + S) / (T + S)
   with mu_ref = 0.00001716 Pa.s, T_ref = 273.15 K and S = 110.4 K for air
   (the .ads constants MU_REF_AIR, T_REF_KELVIN and S_SUTHERLAND). Because
   x^1.5 = x * sqrt(x) for x >= 0, the 3/2 power is modelled here as
   x * sqrt(x), so every factor is checked with the standard square-root
   lemmas of the Coq standard library.

   THEOREM (P2) [strict positivity, the .ads Post "Result > 0.0"]: the three
   factors of mu are strictly positive for T > 0, hence mu > 0 for T > 0.
   Every consumer multiplies this result (Rho_W*Mu_W, Rho_S_Mu_S in
   Compute_Analytical_Predictions and the DKR/VD/Chapman bodies), so an
   unbounded Post would leave each product overflow check unprovable.
   THEOREM (P3) [the Sutherland factor is a proper fraction]: for T >= T_ref
   the term (T_ref + S)/(T + S) is positive and at most 1, so it can never
   amplify the reference viscosity.
   THEOREM (P4) [square-root magnitude floor, the .ads Sqrt_Float contract]:
   X >= 1 implies sqrt(X) >= 1, and 0 <= X <= 1 implies sqrt(X) <= 1. These are
   the two conjuncts that keep P_Stag / (R * T_Stag) provably non-zero.

   CITATIONS:
     [1] Sutherland, W. (1893), "The viscosity of gases and molecular force",
         Phil. Mag. S.5, 36:223, 507-531.
     [2] White, F.M., "Viscous Fluid Flow", 3rd Ed., Sec. 1.3 (Sutherland's
         law) -- the form quoted by the .ads.
     [3] Ada Reference Manual ISO/IEC 8652:2012, RM 4.5.1 (multiplicative
         operators).
     [4] Coq Reference Manual, Coq.Reals.R_sqrt (sqrt_pos, sqrt_lt_R0,
         sqrt_sqrt, sqrt_le_1) and Coq.Reals.RIneq (Rdiv_lt_0_compat,
         Rmult_le_compat, Rmult_le_compat_r, Rmult_le_pos,
         Rmult_lt_0_compat, Rmult_le_reg_l, Rinv_l, Rinv_r).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

(* R_scope opened at file level: every Definition and Lemma below quantifies
   over R; numerals and / then elaborate in the real field rather than nat.
   Any nat-only lemma is wrapped in Section NatPart below. *)
Local Open Scope R_scope.

(* AXIOM: for l <> 0 the product l * (x / l) is definitionally x, because
   Rdiv unfolds to x * (/ l) and (/ l) is a two-sided inverse of l.
   THEORY: this is the cancellation step that turns a division-involving
   hypothesis into a product form usable by Rmult_le_compat / lia.
   APPLICATION: used by rdiv_nonneg and sutherland_factor positivity below.
   [Citation: Coq 8.18 stdlib Coq.Reals.Reals (Rdiv, Rinv_l, Rmult_assoc)] *)
Lemma cancel_mul : forall x l : R, l <> 0 -> l * (x / l) = x.
Proof.
  intros x l Hne. unfold Rdiv.
  rewrite <- Rmult_assoc. rewrite (Rmult_comm l x).
  rewrite Rmult_assoc. rewrite (Rmult_comm l (/ l)).
  rewrite (Rinv_l l Hne). rewrite Rmult_1_r. reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   Air constants of the Ada body (stellarorion_postprocessing.adb).
   --------------------------------------------------------------------------- *)
Definition MU_REF_AIR : R := 0.00001716.
Definition T_REF_KELVIN : R := 273.15.
Definition S_SUTHERLAND : R := 110.4.

(* ---------------------------------------------------------------------------
   Model of Sutherland's law.  (T/T_ref)^1.5 is written as (T/T_ref)*sqrt(T/T).
   --------------------------------------------------------------------------- *)
Definition sutherland_half_power (t : R) : R :=
   (t / T_REF_KELVIN) * sqrt (t / T_REF_KELVIN).

Definition sutherland_factor (t : R) : R :=
   (T_REF_KELVIN + S_SUTHERLAND) / (t + S_SUTHERLAND).

Definition sutherland_viscosity (t : R) : R :=
   MU_REF_AIR * sutherland_half_power t * sutherland_factor t.

(* ---------------------------------------------------------------------------
   The three air constants are strictly positive, unfolded so that `lra` sees
   literal numerals rather than opaque atoms.
   --------------------------------------------------------------------------- *)
Lemma muref_pos : 0 < MU_REF_AIR.
Proof.
  unfold MU_REF_AIR.
  assert (Hshow : 0 < 1) by lra.
  assert (Hactual : 0 < 17 / 1000000000) by lra.
  lra.
Qed.

Lemma tref_pos : 0 < T_REF_KELVIN.
Proof.
  unfold T_REF_KELVIN.
  assert (Hshow : 0 < 1) by lra.
  assert (Hactual : 0 < 273) by lra.
  lra.
Qed.

Lemma suth_pos : 0 < S_SUTHERLAND.
Proof.
  unfold S_SUTHERLAND.
  assert (Hshow : 0 < 1) by lra.
  assert (Hactual : 0 < 110) by lra.
  lra.
Qed.

(* ---------------------------------------------------------------------------
   Helper: a / b <= 1 whenever 0 < b and a <= b.
   --------------------------------------------------------------------------- *)
Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

(* ---------------------------------------------------------------------------
   Helper: 0 <= a / b whenever 0 <= a and 0 < b.
   --------------------------------------------------------------------------- *)
Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv.
  apply Rmult_le_pos; [exact Ha | exact Hinv].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM P2 element 1 -- the (T/T_ref) half power is strictly positive.
   --------------------------------------------------------------------------- *)
Lemma sutherland_half_power_pos : forall t, 0 < t -> 0 < sutherland_half_power t.
Proof.
  intros t Ht.
  unfold sutherland_half_power.
  assert (Ha : 0 < t / T_REF_KELVIN).
  { apply Rdiv_lt_0_compat; [exact Ht | exact tref_pos]. }
  apply Rmult_lt_0_compat.
  - exact Ha.
  - apply sqrt_lt_R0.
    exact Ha.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM P2 element 2 -- the Sutherland factor is strictly positive.
   --------------------------------------------------------------------------- *)
Lemma sutherland_factor_pos : forall t, 0 < t -> 0 < sutherland_factor t.
Proof.
  intros t Ht.
  unfold sutherland_factor.
  apply Rdiv_lt_0_compat.
  - assert (Hl : 0 < T_REF_KELVIN + S_SUTHERLAND).
    { assert (H1 : 0 < T_REF_KELVIN) by exact tref_pos.
      assert (H2 : 0 < S_SUTHERLAND) by exact suth_pos.
      lra. }
    exact Hl.
  - assert (Hr : 0 < t + S_SUTHERLAND).
    { assert (H2 : 0 < S_SUTHERLAND) by exact suth_pos.
      lra. }
    exact Hr.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM P2 -- Sutherland viscosity is strictly positive for T > 0.
   --------------------------------------------------------------------------- *)
Lemma sutherland_viscosity_pos : forall t, 0 < t -> 0 < sutherland_viscosity t.
Proof.
  intros t Ht.
  unfold sutherland_viscosity.
  assert (H1 : 0 < sutherland_half_power t)
    by (apply sutherland_half_power_pos; exact Ht).
  assert (H2 : 0 < sutherland_factor t)
    by (apply sutherland_factor_pos; exact Ht).
  assert (H0 : 0 < MU_REF_AIR) by exact muref_pos.
  apply Rmult_lt_0_compat.
  - apply Rmult_lt_0_compat; [exact H0 | exact H1].
  - exact H2.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM P3 -- for T >= T_ref the factor is a proper fraction in (0, 1].
   --------------------------------------------------------------------------- *)
Lemma sutherland_factor_bounds : forall t,
   T_REF_KELVIN <= t -> 0 < sutherland_factor t /\ sutherland_factor t <= 1.
Proof.
  intros t Ht.
  assert (Htpos : 0 < t).
  { assert (H1 : 0 < T_REF_KELVIN) by exact tref_pos. lra. }
  split.
  - apply sutherland_factor_pos.
    exact Htpos.
  - unfold sutherland_factor.
    apply rdiv_le_1.
    + assert (H2 : 0 < S_SUTHERLAND) by exact suth_pos.
      lra.
    + assert (H1 : 0 < T_REF_KELVIN) by exact tref_pos.
      assert (H2 : 0 < S_SUTHERLAND) by exact suth_pos.
      lra.
Qed.

(* ---------------------------------------------------------------------------
   Helper: mu(T) is non-negative for every T >= 0 (the .ads weaker Post).
   --------------------------------------------------------------------------- *)
Lemma sutherland_viscosity_nonneg : forall t, 0 <= t -> 0 <= sutherland_viscosity t.
Proof.
  intros t Ht.
  assert (H1 : 0 <= sutherland_half_power t).
  { unfold sutherland_half_power.
    apply Rmult_le_pos.
    - apply rdiv_nonneg; [exact Ht | exact tref_pos].
    - apply sqrt_pos. }
  assert (H2 : 0 <= sutherland_factor t).
  { unfold sutherland_factor.
    assert (Ha : 0 <= T_REF_KELVIN + S_SUTHERLAND).
    { assert (Htr : 0 < T_REF_KELVIN) by exact tref_pos.
      assert (Hsu : 0 < S_SUTHERLAND) by exact suth_pos.
      lra. }
    apply rdiv_nonneg.
    + exact Ha.
    + assert (Hsu : 0 < S_SUTHERLAND) by exact suth_pos.
      assert (Hr : 0 < t + S_SUTHERLAND) by lra.
      exact Hr.
  }
  unfold sutherland_viscosity.
  assert (H0 : 0 <= MU_REF_AIR) by (apply Rlt_le; exact muref_pos).
  apply Rmult_le_pos.
  - apply Rmult_le_pos; [exact H0 | exact H1].
  - exact H2.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM P4a -- X >= 1 implies sqrt(X) >= 1 (the .ads magnitude floor).
   --------------------------------------------------------------------------- *)
Lemma sqrt_ge_1 : forall x, 1 <= x -> 1 <= sqrt x.
Proof.
  intros x Hx.
  destruct (Rle_dec 1 (sqrt x)) as [H | H].
  - exact H.
  - exfalso.
    assert (Hpos : 0 <= x) by lra.
    assert (Hsq : sqrt x * sqrt x = x) by (apply sqrt_sqrt; exact Hpos).
    assert (Hlt : sqrt x < 1) by lra.
    assert (Hns : 0 <= sqrt x) by (apply sqrt_pos).
    (* Since 0 <= sqrt x <= 1, the product sqrt x * sqrt x is bounded
       above by sqrt x * 1 = sqrt x, and sqrt x < 1 contradicts 1 <= x. *)
    assert (Hmon : sqrt x * sqrt x <= sqrt x * 1).
    { apply Rmult_le_compat.
      - exact Hns.
      - exact Hns.
      - apply Rle_refl.
      - apply Rlt_le. exact Hlt. }
    lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM P4b -- 0 <= X <= 1 implies sqrt(X) <= 1.
   --------------------------------------------------------------------------- *)
Lemma sqrt_le_1_of_le_1 : forall x, 0 <= x -> x <= 1 -> sqrt x <= 1.
Proof.
  intros x Hx1 Hx2.
  (* The stdlib name sqrt_le_1 has type
       forall x y : R, 0 <= x -> 0 <= y -> x <= y -> sqrt x <= sqrt y
     (Coq 8.18, Coq.Reals.R_sqrt), so it cannot be applied directly to this
     goal: the conclusion would be "sqrt x <= sqrt 1", not "sqrt x <= 1", and
     sqrt is opaque to lra.  The monotone case is therefore established by the
     same case split used for sqrt_ge_1 above. *)
  destruct (Rle_dec (sqrt x) 1) as [H | H].
  - exact H.
  - exfalso.
    assert (Hpos : 0 <= x) by exact Hx1.
    assert (Hsq : sqrt x * sqrt x = x) by (apply sqrt_sqrt; exact Hpos).
    assert (Hlt : 1 < sqrt x) by lra.
    assert (Hns : 0 <= sqrt x) by (apply sqrt_pos; exact Hpos).
    (* Since 1 <= sqrt x, the product sqrt x * sqrt x is bounded below by
       1 * sqrt x = sqrt x, and 1 < sqrt x contradicts x <= 1. *)
    assert (Hmon : 1 * sqrt x <= sqrt x * sqrt x).
    { apply Rmult_le_compat.
      - lra.
      - exact Hns.
      - apply Rlt_le. exact Hlt.
      - apply Rle_refl. }
    lra.
Qed.

(* ---------------------------------------------------------------------------
   Consequence used by the body's loop invariant: for X >= 1 the exact square
   root never exceeds its argument, which is why Sqrt_Float's Post bound
   "Result <= Float'Max (X, 1)" is tight and not merely defensive.
   --------------------------------------------------------------------------- *)
Lemma sqrt_le_self : forall x, 1 <= x -> sqrt x <= x.
Proof.
  intros x Hx.
  assert (Hs : sqrt x * sqrt x = x) by (apply sqrt_sqrt; lra).
  assert (Hpos : 0 <= sqrt x) by apply sqrt_pos.
  assert (Hone : 1 <= sqrt x) by (apply sqrt_ge_1; exact Hx).
  assert (Hm : 1 * sqrt x <= sqrt x * sqrt x).
  { apply Rmult_le_compat_r; [exact Hpos | exact Hone]. }
  rewrite Rmult_1_l in Hm.
  rewrite Hs in Hm.
  exact Hm.
Qed.

(* ---------------------------------------------------------------------------
   Consequence for the Newton seed: X / 2 <= X for X >= 0, so the body's seed
   Float'Max (X / 2.0, 1.0) can never exceed Float'Max (X, 1.0).
   --------------------------------------------------------------------------- *)
Lemma newton_seed_half_le : forall x, 0 <= x -> x / 2 <= x.
Proof.
  intros x Hx.
  assert (Htwo : 0 < 2) by lra.
  assert (H := rdiv_le_1 x 2 Htwo).
  lra.
Qed.
