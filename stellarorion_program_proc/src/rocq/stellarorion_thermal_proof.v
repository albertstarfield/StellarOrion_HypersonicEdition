(* ============================================================================
   StellarOrion HypersonicEdition -- 1D transient backface temperature and
   radiative-equilibrium temperature proofs.

   Every lemma below is machine-checked: none of them is an unfinished
   placeholder, and the file declares no unproven assumption.  Each obligation
   carries an AXIOM / THEORY / CITATION block so the statement under test, the
   reasoning that discharges it and the stdlib fact it rests on are all visible
   in place.

   AXIOM (B1) [lumped backface model]: the 1D transient backface temperature of
   the TPS wall is

       T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)

   with T_init the initial backface temperature [K], q the incident cold-wall
   heat flux [W/m^2], dt the time step [s], eta_lag the thermal-lag efficiency,
   rho_TPS the TPS density [kg/m^3], Cp the TPS specific heat [J/(kg*K)] and
   delta the TPS thickness [m].  Because the numerator is linear in q, the map
   q |-> T_back(q) is affine, which is what makes (B4) an equality rather than
   an inequality.

   AXIOM (R1) [Stefan-Boltzmann radiative equilibrium]: a surface at
   temperature T radiates sigma * epsilon * T^4, so the radiative-equilibrium
   temperature for an absorbed incident flux q is

       T_rad = (q / (sigma * epsilon))^(1/4)

   The fractional exponent cannot be written directly on R: the R_scope
   exponent of "^" is a nat (Coq 8.18, Coq.Reals.Rfunctions,
   Infix "^" := pow), so pow's second argument is a nat and (1/4) does not
   elaborate.  The fourth root is therefore MODELLED as sqrt (sqrt x), exactly
   the convention the Sutherland companion file uses for the 3/2 power
   (x * sqrt x).  For x >= 0 that is the real fourth root and it satisfies
   x = (sqrt (sqrt x))^4; for x < 0 Coq's sqrt is 0 by construction, so the
   fourth-power identity genuinely needs x >= 0 -- see the counterexample
   recorded at T_radFourth_proportional.

   THEOREM (B2) [backface non-negativity]: for non-negative T_init, q and dt
   and positive eta_lag, rho_TPS, Cp, delta, the backface temperature is
   non-negative.

   THEOREM (B3) [backface monotone in heat flux]: raising the incident heat
   flux raises the backface temperature.  The original statement assumed only
   dt >= 0, under which it is FALSE: with dt = 0 the whole flux term vanishes,
   T_back_with q1 = T_back_with q2 = T_init, and strict increase fails.  The
   missing physical hypothesis dt > 0 (a positive time step) is supplied here
   and the counterexample is recorded at the lemma.

   THEOREM (B4) [backface affinity in q]:
       T_back_with (q1 + q2) = T_back_with q1 + T_back_with q2 - T_init
   The "- T_init" shift is exactly what cancels the duplicated initial term, so
   this statement is TRUE as originally written; it is proved, not repaired.

   THEOREM (R2) [radiative temperature non-negative]: T_rad >= 0.
   THEOREM (R3) [fourth-power identity]: for q >= 0, sigma > 0 and
   epsilon > 0, T_rad^4 = q / (sigma * epsilon).

   CITATIONS:
     [1] Sutton & Graves (1972), NASA TR R-376 -- stagnation heat-flux
         correlation; q is an incident flux, hence non-negative.
     [2] Siegel & Howell, "Thermal Radiation Heat Transfer", 4th Ed. --
         Stefan-Boltzmann law sigma * epsilon * T^4.
     [3] Coq 8.18 standard library, Coq.Reals.Reals: Rdefinitions (Rdiv),
         Raxioms (Rmult_assoc, Rmult_comm, Rmult_plus_distr_l),
         Rpow_def (Fixpoint pow), RIneq (Rinv_0_lt_compat, Rlt_le, Rmult_1_r,
         Rmult_le_pos, Rmult_lt_0_compat, Rmult_lt_compat_r), Rfunctions (pow_add, Infix "^" := pow),
         Coq.Reals.R_sqrt (sqrt, sqrt_pos, sqrt_sqrt),
         Coq.micromega.Lra (lra -- unfolds Rdiv in the goal and in the context,
         then discharges the remaining linear problem over the abstracted
         atoms).

   Author: Albert Starfield Wahyu Suryo Samudro
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

(* Every Definition and Lemma below quantifies over R; opening R_scope at file
   level makes numerals, <=, <, * and / elaborate in the real field rather than
   nat.  This file contains no nat-only lemma, so no nat_scope section is
   needed. [Citation: Coq 8.18 stdlib Coq.Reals.Reals -- Local Open Scope
   R_scope] *)
Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   AXIOM: 0 <= a / b whenever 0 <= a and 0 < b.
   THEORY: Rdiv unfolds to a * (/ b), and / b is strictly positive when b is
   (Rinv_0_lt_compat), so the quotient of a non-negative numerator by a
   strictly positive denominator is non-negative.
   APPLICATION: the sign of the backface quotient
   (q * dt * eta_lag) / (rho_TPS * Cp * delta) and of the radiative ratio
   q / (sigma * epsilon).
   [Citation: Coq 8.18 stdlib, Coq.Reals.RIneq -- Rinv_0_lt_compat,
   Rlt_le, Rmult_le_pos, Coq.Reals.Rdefinitions -- Definition Rdiv]
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
   AXIOM: (a + b) * c = a * c + b * c for every real a, b, c.
   THEORY: Coq's field axiom Rmult_plus_distr_l is stated with the sum on the
   right of the product, so the left-distributive form used by the backface
   affinity proof is obtained by commuting the three factors.
   APPLICATION: splitting (q1 + q2) * dt * eta_lag across the backface
   quotient in T_back_linear_in_q.
   [Citation: Coq 8.18 stdlib, Coq.Reals.Raxioms -- Rmult_plus_distr_l,
   Rmult_comm]
   --------------------------------------------------------------------------- *)
Lemma rplus_mult_distr_l : forall a b c : R, (a + b) * c = a * c + b * c.
Proof.
  intros a b c.
  rewrite (Rmult_comm (a + b) c).
  rewrite (Rmult_comm a c).
  rewrite (Rmult_comm b c).
  apply Rmult_plus_distr_l.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM: (a + b) / c = a / c + b / c.
   THEORY: Rdiv unfolds to multiplication by the inverse Rinv, and
   Rmult_plus_distr_r distributes the product over the sum, so the split is a
   pure field identity that holds even at c = 0 (where /c is 0 on both sides).
   APPLICATION: splitting the backface quotient over the two heat fluxes in
   T_back_linear_in_q, which frees the remaining step for lra over pure atoms.
   [Citation: Coq 8.18 stdlib, Coq.Reals.RIneq -- Rmult_plus_distr_r,
   Coq.Reals.Rdefinitions -- Definition Rdiv] *)
Lemma rplus_div : forall a b c, (a + b) / c = a / c + b / c.
Proof.
  intros a b c.
  unfold Rdiv.
  apply Rmult_plus_distr_r.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM: t + (x + y) = t + x + (t + y) - t.
   THEORY: the duplicated initial temperature t on the right is exactly
   cancelled by the trailing subtraction, so both sides reduce to t + x + y.
   Stated over the abstract atoms t, x, y so that no division ever reaches the
   arithmetic tactic.
   APPLICATION: the last step of T_back_linear_in_q, after the flux quotient
   has been split over the two summands.
   [Citation: Coq 8.18 stdlib, Coq.Reals.RIneq -- Rminus, Rplus] *)
Lemma affine_shift_split : forall t x y : R,
  t + (x + y) = t + x + (t + y) - t.
Proof.
  intros t x y.
  lra.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM: x ^ 2 = x * x.
   THEORY: the R_scope "^" is pow on nat.  The exponent is rebuilt as an
   explicit nat sum 1 + 1 (conversion, no reliance on the shape of the
   Fixpoint body, which lives in a file that does not open R_scope), then
   pow_add splits the exponent additively and pow_1 clears each unit factor,
   leaving a pure product identity.
   APPLICATION: rewriting the squared fourth-root in T_radFourth_proportional.
   [Citation: Coq 8.18 stdlib, Coq.Reals.Rfunctions -- pow_add
   (x^(n+m) = x^n * x^m), pow_1 (x^1 = x)]
   --------------------------------------------------------------------------- *)
Lemma pow_two_expand : forall x : R, x ^ 2 = x * x.
Proof.
  intros x.
  (* (1+1)%nat: inside R_scope a bare numeral pair "1 + 1" would be read by
     R_scope's Rplus, so the nat scope must be forced explicitly (this is why
     the stdlib itself writes (n + 1)%nat in Rfunctions.v). *)
  assert (E : x ^ 2 = x ^ (1 + 1)%nat) by reflexivity.
  rewrite E.
  rewrite (pow_add x 1 1).
  rewrite (pow_1 x).
  (* pow_1 rewrites every occurrence of the instance x^1 at once. *)
  reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM: x ^ 4 = x ^ 2 * x ^ 2.
   THEORY: the R_scope "^" is pow on nat.  The exponent 4 is rebuilt as the
   explicit nat sum 2 + 2 by conversion, so no assumption is made about the
   shape of the Fixpoint body (Rpow_def.v does not open R_scope).  pow_add then
   splits 2 + 2 into two second powers, and the rest is literally reflexivity.
   APPLICATION: exposing (sqrt (sqrt x)) * (sqrt (sqrt x)) * ... in
   T_radFourth_proportional so that sqrt_sqrt applies twice.
   [Citation: Coq 8.18 stdlib, Coq.Reals.Rfunctions -- pow_add
   (x^(n+m) = x^n * x^m)]
   --------------------------------------------------------------------------- *)
Lemma pow_four_expand : forall x : R, x ^ 4 = x ^ 2 * x ^ 2.
Proof.
  intros x.
  assert (E : x ^ 4 = x ^ (2 + 2)%nat) by reflexivity.
  rewrite E.
  rewrite (pow_add x 2 2).
  reflexivity.
Qed.

(* ---- Backface Temperature ---- *)
(* T_back(q) = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta) *)

Section BackfaceTemperature.
  Variable T_init : R.      (* initial temperature [K] *)
  Variable q : R.           (* heat flux [W/m^2] *)
  Variable dt : R.          (* time step [s] *)
  Variable eta_lag : R.     (* thermal lag efficiency *)
  Variable rho_TPS : R.     (* TPS density [kg/m^3] *)
  Variable Cp : R.          (* TPS specific heat [J/(kg*K)] *)
  Variable delta : R.       (* TPS thickness [m] *)

  (* AXIOM: the backface temperature for an arbitrary incident heat flux.
     THEORY: this is the flux-parameterised form of the (B1) model, so the
     monotonicity and affinity lemmas can quantify over the flux they need
     instead of being pinned to the section Variable q.
     APPLICATION: the three BackfaceTemperature lemmas below.
     [Citation: Coq 8.18 stdlib, Coq.Reals.Rdefinitions -- Rdiv] *)
  Definition T_back_with (q' : R) : R :=
    T_init + (q' * dt * eta_lag) / (rho_TPS * Cp * delta).

  (* The nullary T_back of the (B1) formula is the special case q' = q; it is
     kept so T_back_nonneg certifies the literal header formula. *)
  Definition T_back := T_back_with q.

  (* -------------------------------------------------------------------------
     THEOREM (B2) -- the backface temperature is non-negative on the physical
     domain (T_init, q, dt >= 0 and eta_lag, rho_TPS, Cp, delta > 0).
     AXIOM: a product of non-negative reals is non-negative and a quotient
     with a strictly positive denominator stays non-negative, so the flux term
     of (B1) cannot be negative.
     THEORY: q * dt >= 0 by two applications of Rmult_le_pos, the whole
     numerator q * dt * eta_lag >= 0, the denominator rho_TPS * Cp * delta > 0
     by two applications of Rmult_lt_0_compat, hence the quotient >= 0 by
     rdiv_nonneg, and adding it to T_init >= 0 keeps the sum non-negative.
     APPLICATION: the .ads lower bound on Backface_Temperature_K.
     [Citation: Coq 8.18 stdlib, Coq.Reals.RIneq -- Rmult_le_pos,
     Rmult_lt_0_compat, and rdiv_nonneg + lra above]
     ------------------------------------------------------------------------- *)
  Lemma T_back_nonneg :
    0 <= T_init -> 0 <= q -> 0 <= dt -> 0 < eta_lag ->
    0 < rho_TPS -> 0 < Cp -> 0 < delta ->
    0 <= T_back.
  Proof.
    intros HT HQ Hdt Heta Hrho HCp Hdelta.
    unfold T_back.
    unfold T_back_with.
    assert (Hqdt : 0 <= q * dt)
      by (apply Rmult_le_pos; [exact HQ | exact Hdt]).
    assert (Hnum : 0 <= q * dt * eta_lag).
    { apply Rmult_le_pos; [exact Hqdt | ].
      apply Rlt_le; exact Heta. }
    assert (HrhoCp : 0 < rho_TPS * Cp)
      by (apply Rmult_lt_0_compat; [exact Hrho | exact HCp]).
    assert (Hden : 0 < rho_TPS * Cp * delta)
      by (apply Rmult_lt_0_compat; [exact HrhoCp | exact Hdelta]).
    assert (Hquot : 0 <= (q * dt * eta_lag) / (rho_TPS * Cp * delta))
      by (apply rdiv_nonneg; [exact Hnum | exact Hden]).
    (* The quotient is non-negative and T_init is non-negative; lra cannot see
       the / term, so the sum is closed with the two-premise stdlib lemma. *)
    apply Rplus_le_le_0_compat.
    - exact HT.
    - exact Hquot.
  Qed.

  (* -------------------------------------------------------------------------
     THEOREM (B3) -- the backface temperature is strictly increasing in the
     incident heat flux.

     REPAIR NOTE (the original statement was FALSE).  It read
         q1 >= 0 -> q2 > q1 -> eta_lag > 0 -> dt >= 0 -> ... ->
         T_back_with q2 > T_back_with q1
     The hypothesis dt >= 0 admits dt = 0, and then every T_back_with is just
     T_init, so the conclusion T_back_with q2 > T_back_with q1 is violated.
     Counterexample: dt = 0 (any T_init, q1, q2 with q1 < q2) gives
         T_back_with q1 = T_init + (q1 * 0 * eta_lag)/(rho_TPS*Cp*delta)
                        = T_init = T_back_with q2.
     The physically correct hypothesis -- a strictly positive time step -- is
     supplied instead; nothing has been weakened to reach a proof.

     AXIOM: (T_back_with q2) - (T_back_with q1) equals
     ((q2 - q1) * dt * eta_lag) / (rho_TPS * Cp * delta), so raising q raises
     the backface temperature by exactly the flux increment times the
     non-negative thermal coupling.
     THEORY: rho_TPS * Cp * delta > 0 (two Rmult_lt_0_compat), dt * eta_lag > 0
     (Rmult_lt_0_compat), so Rmult_lt_compat_r gives
     q1 * (dt * eta_lag) < q2 * (dt * eta_lag) from q1 < q2; re-associating
     with Rmult_assoc keeps the numerator ordered, and division by the positive
     denominator reverses nothing (Rmult_lt_compat_r against Rinv_0_lt_compat).
     The two quotients differ strictly, and adding the common T_init preserves
     the strict order.
     APPLICATION: the .ads monotonicity Post on the backface temperature.
     NOTE: the hypotheses 0 <= q1 and 0 <= T_init are the physical domain and
     are retained for statement fidelity; the proof only needs q1 < q2, because
     the difference of the two quotients is already positive and adding the
     common T_init cannot change its sign.
     [Citation: Coq 8.18 stdlib, Coq.Reals.RIneq -- Rmult_lt_compat_r,
     Rmult_lt_0_compat, Rmult_assoc, Rinv_0_lt_compat, Rdiv]
     ------------------------------------------------------------------------- *)
  Lemma T_back_increases_with_heat :
    forall q1 q2 : R,
      0 <= q1 -> q1 < q2 -> 0 < eta_lag -> 0 < dt ->
      0 < rho_TPS -> 0 < Cp -> 0 < delta ->
      0 <= T_init ->
      T_back_with q1 < T_back_with q2.
  Proof.
    intros q1 q2 Hq1 Hlt Heta Hdt Hrho HCp Hdelta HT.
    assert (HrhoCp : 0 < rho_TPS * Cp)
      by (apply Rmult_lt_0_compat; [exact Hrho | exact HCp]).
    assert (Hden : 0 < rho_TPS * Cp * delta)
      by (apply Rmult_lt_0_compat; [exact HrhoCp | exact Hdelta]).
    assert (Hdte : 0 < dt * eta_lag)
      by (apply Rmult_lt_0_compat; [exact Hdt | exact Heta]).
    (* re-associate the numerator as q' * (dt * eta_lag) so the ordered factor
       dt * eta_lag can be used as the multiplier of Rmult_lt_compat_r *)
    assert (E1 : q1 * dt * eta_lag = q1 * (dt * eta_lag))
      by exact (Rmult_assoc q1 dt eta_lag).
    assert (E2 : q2 * dt * eta_lag = q2 * (dt * eta_lag))
      by exact (Rmult_assoc q2 dt eta_lag).
    assert (Hnum : q1 * (dt * eta_lag) < q2 * (dt * eta_lag))
      by (apply Rmult_lt_compat_r; [exact Hdte | exact Hlt]).
    assert (Hnum2 : q1 * dt * eta_lag < q2 * dt * eta_lag)
      by (rewrite E1, E2; exact Hnum).
    assert (Hquot : q1 * dt * eta_lag / (rho_TPS * Cp * delta)
                   < q2 * dt * eta_lag / (rho_TPS * Cp * delta)).
    { unfold Rdiv.
      apply Rmult_lt_compat_r; [ | exact Hnum2].
      apply Rinv_0_lt_compat; exact Hden. }
    unfold T_back_with.
    (* Strictness is preserved by adding the same T_init on both sides; lra is
       not used because it must never see the / term. *)
    apply Rplus_lt_compat_l.
    exact Hquot.
  Qed.

  (* -------------------------------------------------------------------------
     THEOREM (B4) -- the backface temperature is affine in the heat flux:
         T_back_with (q1 + q2) = T_back_with q1 + T_back_with q2 - T_init

     VERIFICATION OF THE STATEMENT (it is TRUE as originally written).  Let
     d = rho_TPS * Cp * delta.  Then
         T_back_with (q1 + q2) - T_init = ((q1 + q2) * dt * eta_lag) / d
         T_back_with q1 + T_back_with q2 - T_init - T_init
           = (q1 * dt * eta_lag) / d + (q2 * dt * eta_lag) / d
           = ((q1 + q2) * dt * eta_lag) / d,
     so the "- T_init" on the right is exactly the term that removes the
     duplicated initial temperature and nothing has to be weakened.

     AXIOM: the model is additive because the numerator is a product of the
     flux with constants.
     THEORY: (q1 + q2) * dt * eta_lag is first re-associated to
     (q1 + q2) * (dt * eta_lag), then split by rplus_mult_distr_l and
     re-associated back; the quotient of the sum is then split with
     Rmult_plus_distr_l applied to the common factor / d.  Everything that is
     left is a linear identity over the two quotient atoms, which lra closes.
     APPLICATION: the .ads additivity Post used to superpose two heating
     intervals.
     [Citation: Coq 8.18 stdlib, Coq.Reals.Raxioms -- Rmult_assoc,
     Rmult_plus_distr_l, Rmult_comm; rplus_mult_distr_l above]
     ------------------------------------------------------------------------- *)
  Lemma T_back_linear_in_q :
    forall q1 q2 : R,
      T_back_with (q1 + q2) = T_back_with q1 + T_back_with q2 - T_init.
  Proof.
    intros q1 q2.
    unfold T_back_with.
    assert (Enum : (q1 + q2) * dt * eta_lag
                  = q1 * dt * eta_lag + q2 * dt * eta_lag).
    { rewrite (Rmult_assoc (q1 + q2) dt eta_lag).
      rewrite (rplus_mult_distr_l q1 q2 (dt * eta_lag)).
      rewrite (Rmult_assoc q1 dt eta_lag).
      rewrite (Rmult_assoc q2 dt eta_lag).
      reflexivity. }
    assert (Equot : (q1 * dt * eta_lag + q2 * dt * eta_lag)
                     / (rho_TPS * Cp * delta)
                   = q1 * dt * eta_lag / (rho_TPS * Cp * delta)
                     + q2 * dt * eta_lag / (rho_TPS * Cp * delta))
      by exact (rplus_div (q1 * dt * eta_lag) (q2 * dt * eta_lag)
                         (rho_TPS * Cp * delta)).
    rewrite Enum.
    rewrite Equot.
    (* Both quotients are now split over the two summands, so the goal is
       literally the abstract identity proved in affine_shift_split; the /
       terms are never handed to lra. *)
    exact (affine_shift_split T_init
             (q1 * dt * eta_lag / (rho_TPS * Cp * delta))
             (q2 * dt * eta_lag / (rho_TPS * Cp * delta))).
  Qed.
End BackfaceTemperature.

(* ---- Radiative Equilibrium Temperature ---- *)
(* T_rad = (q / (sigma * epsilon))^(1/4), modelled as sqrt (sqrt (q/(sigma*epsilon))) *)

Section RadiativeEquilibrium.
  Variable q : R.           (* heat flux [W/m^2] *)
  Variable sigma : R.       (* Stefan-Boltzmann constant *)
  Variable epsilon : R.     (* total hemispherical emissivity *)

  (* AXIOM: the radiative-equilibrium temperature is the fourth root of the
     absorbed flux ratio q / (sigma * epsilon).
     THEORY: the R_scope exponent of "^" is a nat, so (1/4) does not elaborate;
     the fourth root is therefore realised as sqrt (sqrt x).  sqrt is
     non-negative for every argument and squares back to its input whenever
     the input is non-negative, so sqrt (sqrt x) is the real fourth root on
     the physically meaningful domain x >= 0.
     APPLICATION: T_rad_nonneg and T_radFourth_proportional below.
     [Citation: Coq 8.18 stdlib, Coq.Reals.R_sqrt -- Definition sqrt,
     sqrt_pos, sqrt_sqrt; Coq.Reals.Rfunctions -- Infix "^" := pow] *)
  Definition T_rad := sqrt (sqrt (q / (sigma * epsilon))).

  (* -------------------------------------------------------------------------
     THEOREM (R2) -- the radiative-equilibrium temperature is non-negative.
     AXIOM: sqrt returns a non-negative value for every real argument, so no
     positivity hypothesis is needed; the hypotheses below are the physical
     domain and are kept for statement fidelity.
     THEORY: sqrt_pos is unconditional in Coq 8.18 (it holds by the case
     analysis of Rcase_abs inside the definition of sqrt).
     APPLICATION: the .ads lower bound on Radiative_Equilibrium_Temperature.
     [Citation: Coq 8.18 stdlib, Coq.Reals.R_sqrt -- sqrt_pos]
     ------------------------------------------------------------------------- *)
  Lemma T_rad_nonneg :
    0 <= q -> 0 < sigma -> 0 < epsilon ->
    0 <= T_rad.
  Proof.
    intros Hq Hsigma Hepsilon.
    unfold T_rad.
    apply sqrt_pos.
  Qed.

  (* -------------------------------------------------------------------------
     THEOREM (R3) -- T^4 is proportional to q:
         T_rad ^ 4 = q / (sigma * epsilon)

     REPAIR NOTE (the original statement was FALSE without hypotheses).  It
     read T_rad^4 = q / (sigma * epsilon) outright.  With T_rad modelled as
     sqrt (sqrt x), Coq's sqrt is 0 for x < 0, so the identity fails in
     exactly the negative-flux corner.
     Counterexample: q = -1, sigma = 1, epsilon = 1 gives
     x = q / (sigma * epsilon) = -1, sqrt x = 0 (R_sqrt case on Rcase_abs),
     T_rad = sqrt (sqrt (-1)) = sqrt 0 = 0, and T_rad^4 = 0 whereas
     q / (sigma * epsilon) = -1.
     The physical hypotheses 0 <= q, 0 < sigma, 0 < epsilon are supplied; the
     conclusion itself is unchanged.

     AXIOM: for a non-negative x the fourth root squares back twice, so
     (sqrt (sqrt x))^4 = x.
     THEORY: pow_four_expand turns a^4 into a^2 * a^2 and pow_two_expand
     turns a^2 into a * a; sqrt_sqrt then gives
     sqrt (sqrt x) * sqrt (sqrt x) = sqrt x (needs 0 <= sqrt x, which is
     sqrt_pos) and sqrt x * sqrt x = x (needs 0 <= x, which is
     rdiv_nonneg applied to q / (sigma * epsilon)).
     APPLICATION: the .ads Post
         Radiative_Equilibrium_Temperature ^ 4 = Absorbed_Flux / (sigma * e)
     that closes the Stefan-Boltzmann balance.
     [Citation: Coq 8.18 stdlib, Coq.Reals.R_sqrt -- sqrt_pos, sqrt_sqrt;
     Coq.Reals.Rfunctions -- pow_add; rdiv_nonneg, pow_two_expand,
     pow_four_expand above]
     ------------------------------------------------------------------------- *)
  Lemma T_radFourth_proportional :
    0 <= q -> 0 < sigma -> 0 < epsilon ->
    T_rad ^ 4 = q / (sigma * epsilon).
  Proof.
    intros Hq Hsigma Hepsilon.
    assert (Hse : 0 < sigma * epsilon)
      by (apply Rmult_lt_0_compat; [exact Hsigma | exact Hepsilon]).
    assert (Hx : 0 <= q / (sigma * epsilon))
      by (apply rdiv_nonneg; [exact Hq | exact Hse]).
    unfold T_rad.
    assert (Hinner : 0 <= sqrt (q / (sigma * epsilon))) by apply sqrt_pos.
    assert (Hsq1 : sqrt (sqrt (q / (sigma * epsilon)))
                  * sqrt (sqrt (q / (sigma * epsilon)))
                  = sqrt (q / (sigma * epsilon)))
      by (apply sqrt_sqrt; exact Hinner).
    assert (Hsq2 : sqrt (q / (sigma * epsilon)) * sqrt (q / (sigma * epsilon))
                  = q / (sigma * epsilon))
      by (apply sqrt_sqrt; exact Hx).
    rewrite (pow_four_expand (sqrt (sqrt (q / (sigma * epsilon))))).
    rewrite (pow_two_expand (sqrt (sqrt (q / (sigma * epsilon))))).
    rewrite Hsq1.
    exact Hsq2.
  Qed.
End RadiativeEquilibrium.
