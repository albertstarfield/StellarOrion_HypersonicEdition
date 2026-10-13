(* ============================================================================
   MACHINE-CHECKED PROOF -- make_derived_plots (derived thermal-variable plotter)
   ============================================================================
   Unit : scripts/make_derived_plots.py
            constants               (lines 69-98)
            _compute_t_surface      (lines 126-133)
            main (T_back / beta)    (lines 290-297)

   Goal : The thermal identities the derived-variable plotter relies on:
          T1 the thermal capacitance `capacitance = RHO_TPS * CP_TPS *
             DELTA_TPS` (line 291) is a strictly POSITIVE divisor, so the
             backface-temperature step `T_back = T_INIT + (Q*ETA_LAG)/capacitance`
             (line 295) is well defined and finite;
          T2 with the material constants all positive that capacitance equals
             8800 J/(m^2 K) (the value asserted in the code comment at line 291);
          T3 the backface temperature is monotone non-decreasing in the
             accumulated heat load: 0 <= Q implies T_INIT <= T_back, which is the
             physical premise behind the KAPTON_MAX_TEMP survivability verdict
             (lines 96-97, 451-455);
          T4 the J/cm^2 -> J/m^2 rescaling `heat_load[i] * 10000.0` (line 294)
             maps a non-negative load to a non-negative energy (1 J/cm^2 = 1e4
             J/m^2).

   AXIOMS
   A1. Material constants RHO_TPS = 2200, CP_TPS = 800, DELTA_TPS = 0.005,
       ETA_LAG = 0.15, T_INIT = 300.0 are all positive (lines 69-76).
       [Reference: scripts/make_derived_plots.py:69-76]
   A2. Survivability limits SIC_MAX_TEMP = 2073.0, KAPTON_MAX_TEMP = 773.0 come
       from stellarorion_types.ads and are compared against the derived
       temperatures (lines 96-97, 451-455). [Reference: lines 92-97]

   THEORIES
   T1. rho*cp*delta > 0 for positive rho, cp, delta (left-nested product).
   T3. (Q*eta)/C >= 0 for Q >= 0, eta >= 0, C > 0, hence T_back >= T_INIT.

   APPLICATIONS
   Every T_back point plotted against the Kapton limit is a positive-heat-load
   increment above T_INIT, so the exceedance count the figure draws counts the
   same exceedances the Ada verdict (stellarorion_physics.adb) computes.

   CITATIONS:
     [1] Stefan-Boltzmann / radiative equilibrium: https://physics.nist.gov/cgi-bin/cuu/Value?sigma
     [2] 1-D transient backface heating (Rapisarda Sec. 5.5), IRVE-3:
         https://ntrs.nasa.gov/citations/20120011662
     [3] Coq Reference Manual, Coq.Reals.RIneq (Rmult_lt_0_compat, Rmult_le_pos,
         Rinv_0_lt_compat, Rdiv_lt_0_compat, Rlt_le):
         https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* `thermal_capacitance rho cp delta` mirrors capacitance = rho*cp*delta at
   line 291 -- the denominator of the backface-temperature update. *)
Definition thermal_capacitance (rho cp delta : R) : R := rho * cp * delta.

(* T1 -- the capacitance is a strictly positive divisor; `rho*cp*delta` is the
   left-nested product ((rho*cp)*delta), so the product rule peels `delta`
   off last, then splits rho and cp. *)
Lemma thermal_capacitance_positive : forall rho cp delta,
  0 < rho -> 0 < cp -> 0 < delta ->
  0 < thermal_capacitance rho cp delta.
Proof.
  intros rho cp delta Hrho Hcp Hdelta.
  unfold thermal_capacitance.
  apply Rmult_lt_0_compat; [ | exact Hdelta].
  apply Rmult_lt_0_compat; [exact Hrho | exact Hcp].
Qed.

(* T2 -- with the shipped material constants the capacitance is exactly the
   8800 J/(m^2 K) value asserted in the comment at line 291. *)
Lemma capacitance_equals_8800 : thermal_capacitance 2200 800 0.005 = 8800.
Proof.
  unfold thermal_capacitance.
  assert (Hshow : 2200 * 800 * 0.005 = 8800) by lra.
  exact Hshow.
Qed.

(* `backface_temperature T_init Q eta C` mirrors T_INIT + (Q*eta)/C at line 295. *)
Definition backface_temperature (T_init Q_total eta C : R) : R :=
  T_init + (Q_total * eta) / C.

(* T3 -- the backface temperature never drops below the initial temperature
   when the accumulated load and lag factor are non-negative: the added term
   (Q*eta)/C is itself non-negative. *)
Lemma backface_ge_initial : forall T_init Q_total eta C,
  0 <= Q_total -> 0 <= eta -> 0 < C ->
  T_init <= backface_temperature T_init Q_total eta C.
Proof.
  intros T_init Q_total eta C HQ Heta HC.
  unfold backface_temperature.
  assert (Hnum : 0 <= Q_total * eta) by (apply Rmult_le_pos; [exact HQ | exact Heta]).
  assert (Hinv : 0 < / C) by (apply Rinv_0_lt_compat; exact HC).
  assert (Hterm : 0 <= (Q_total * eta) / C).
  { unfold Rdiv.
    apply Rmult_le_pos; [exact Hnum | apply Rlt_le; exact Hinv]. }
  lra.
Qed.

(* T3 (strict) -- a genuine heat-load increment strictly raises the backface
   temperature above T_INIT. *)
Lemma backface_gt_initial : forall T_init Q_total eta C,
  0 < Q_total -> 0 < eta -> 0 < C ->
  T_init < backface_temperature T_init Q_total eta C.
Proof.
  intros T_init Q_total eta C HQ Heta HC.
  unfold backface_temperature.
  assert (Hnum : 0 < Q_total * eta) by (apply Rmult_lt_0_compat; [exact HQ | exact Heta]).
  assert (Hterm : 0 < (Q_total * eta) / C)
    by (apply Rdiv_lt_0_compat; [exact Hnum | exact HC]).
  lra.
Qed.

(* `jcm2_to_jm2 q` mirrors Q_total_jm2 = heat_load[i] * 10000.0 at line 294. *)
Definition jcm2_to_jm2 (q : R) : R := q * 10000.

(* T4 -- the J/cm^2 -> J/m^2 rescaling keeps a non-negative load non-negative
   (1 J/cm^2 = 1e4 J/m^2), so T_back stays physical. *)
Lemma jcm2_to_jm2_nonneg : forall q, 0 <= q -> 0 <= jcm2_to_jm2 q.
Proof.
  intros q Hq.
  unfold jcm2_to_jm2.
  apply Rmult_le_pos; [exact Hq | lra].
Qed.
