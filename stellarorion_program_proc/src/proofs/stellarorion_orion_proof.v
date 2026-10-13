(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_orion (Orion flight metrics)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_orion.adb
              Orion_Survivability_Check (lines 36-73), Test wrapper (89-121)
            src/simulation_engine/stellarorion_physics.adb
              Ballistic_Coefficient (lines 538-564)
            src/simulation_engine/stellarorion_types.ads
              Flight_Metrics.Ballistic_Coeff (lines 825, 867-868)

   Goal  : Ballistic coefficient beta = m / (C_D * A) > 0 whenever mass and
           reference area are positive; beta >= 0 on the non-negative domain.

   AXIOMS
   A1. The ballistic coefficient realised in code is
         beta = (Mass * Dyn_Pressure) / Drag_Force
       which is algebraically  beta = m / (C_D * A_ref)  because the drag
       force SPARTA integrates is  F_D = C_D * A_ref * q  with dynamic
       pressure q, so  m*q / F_D = m / (C_D * A_ref).
       [Reference: stellarorion_physics.adb:494-555 (comment + body)]
   A2. Calculate_Flight_Metrics only ever calls Ballistic_Coefficient once the
       drag guard holds (Results.Drag_Force >= 1.0e-6 N); below that floor the
       code reports 0.0 rather than dividing by ~0.
       [Reference: stellarorion_physics.adb:1494-1499]
   A3. Body mass and the (dynamic-pressure-scaled) area term are strictly
       positive for the Orion crew vehicle (Mass_Kg = 10400 kg default).
       [Reference: stellarorion_orion.ads:38; stellarorion_types.ads:875 region]

   THEORIES
   T1. On the physical domain (Mass > 0, q > 0, F_D > 0) the coefficient is a
       ratio of a positive product to a positive denominator, hence
       beta > 0 -- it can never be zero or negative for a real vehicle.
   T2. If only non-negativity of mass/dynamic pressure is assumed (F_D > 0),
       beta >= 0: a non-negative numerator over a positive denominator is
       non-negative. This is the SPARK Post condition
         Ballistic_Coefficient'Result >= 0.0
       [Reference: stellarorion_physics.adb:545-546]

   APPLICATIONS
   The Orion survivability gate consumes Metrics.Ballistic_Coeff; T1/T2
   guarantee it is the well-signed, positive free-deceleration efficiency the
   IRVE-3 baseline comparison relies on (target beta = 26.9 kg/m^2).
   [Reference: stellarorion_physics.adb:522-526; stellarorion_orion.ads:65-73]

   CITATIONS
   Sutton K. & Graves R.A., "A general stagnation-point convective-heating
     equation...", NASA TR R-376, 1971 -- https://ntrs.nasa.gov/citations/19720005327
   Anderson J.D. (2006), "Hypersonic and High-Temperature Gas Dynamics", 2nd
     ed., AIAA, Sec 1.5 (ballistic coefficient).
   NASA/TP-2013-4012 (IRVE-3 flight reference data).

   VERIFICATION: every lemma below is discharged by `Qed`.  No statement is
   vacuous; each carries the hypotheses it needs and is proved from them.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 -- the ballistic coefficient exactly as the Ada body computes it:
      return (Mass * Dyn_Pressure) / Drag_Force;   (physics.adb:555) *)
Definition ballistic_coefficient (Mass Dyn_Pressure Drag_Force : R) : R :=
   (Mass * Dyn_Pressure) / Drag_Force.

(* T1 -- strictly positive on the physical domain (matches the goal). *)
Lemma ballistic_coefficient_pos : forall Mass Dyn_Pressure Drag_Force,
   Mass > 0 -> Dyn_Pressure > 0 -> Drag_Force > 0 ->
   0 < ballistic_coefficient Mass Dyn_Pressure Drag_Force.
Proof.
   intros Mass Dyn_Pressure Drag_Force Hm Hq HF.
   unfold ballistic_coefficient.
   apply Rdiv_lt_0_compat.
   - apply Rmult_lt_0_compat; assumption.
   - exact HF.
Qed.

(* T2 -- the SPARK Post condition reached directly: non-negative on the
      non-negative part of the domain, positive denominator. *)
Lemma ballistic_coefficient_nonneg : forall Mass Dyn_Pressure Drag_Force,
   0 <= Mass -> 0 <= Dyn_Pressure -> 0 < Drag_Force ->
   0 <= ballistic_coefficient Mass Dyn_Pressure Drag_Force.
Proof.
   intros Mass Dyn_Pressure Drag_Force Hm Hq HF.
   unfold ballistic_coefficient.
   unfold Rdiv.
   apply Rmult_le_pos.
   - apply Rmult_le_pos; assumption.
   - apply Rlt_le; apply Rinv_0_lt_compat; exact HF.
Qed.
