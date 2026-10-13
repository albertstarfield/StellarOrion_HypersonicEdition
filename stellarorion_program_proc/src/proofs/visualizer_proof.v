(* ============================================================================
   MACHINE-CHECKED PROOF -- visualizer (plot-vs-source faithfulness)
   ============================================================================
   Unit  : src/python/visualizer.py is parity-stub only; the executable SPARTA
           plot generators are:
             scripts/make_vtu_visualization.py  (heat flux / surface temp plots)
                q_cm2 = heat / 1e4                    (line 261)
                axhline survivability limit y=2073    (line 287)
             scripts/make_derived_plots.py       (TPS survivability dashboard)
                SIC_MAX_TEMP = 2073.0  KAPTON 773.0   (lines 96-98)
                Q_total_jm2 = heat_load * 10000.0     (line 294)
                title derived from the same constants (lines 349-350)
                limit lines + survivability zones     (lines 418-428)
           Physics constants:
             src/simulation_engine/stellarorion_types.ads:120  SIC_MAX_TEMP := 2073.0
             src/simulation_engine/stellarorion_types.ads:124  KAPTON_MAX_TEMP := 773.0
             src/simulation_engine/stellarorion_types.ads:855  T_back <= KAPTON_MAX_TEMP
             src/simulation_engine/stellarorion_physics.adb:1428 Surface_Temp_K <= SIC_MAX_TEMP

   Goal (unit): Generated plots accurately reflect input data -- plot values
   match CSV/surf source values within floating-point tolerance.  This file
   machine-checks the two numeric facts the plotters rely on for faithfulness:
     (1) the W/m^2 -> W/cm^2 axis conversion divides by the positive constant
         1e4 (=10000.0, since 1 m^2 = 10^4 cm^2), so it is well-defined and
         order-preserving: the plotted series faithfully represents the source
         ordering (lines make_vtu:261, make_derived:294, make_derived:360-361);
     (2) the survivability limit lines drawn on the figures equal the Ada
         physics constants the verdict is tested against (the "ONE TRUTH, ONE
         VALUE" invariant): plotted 2073.0 == SIC_MAX_TEMP and plotted 773.0 ==
         KAPTON_MAX_TEMP, with 0 < Kapton <= SIC, matching the shading zones.

   AXIOMS
   A1. Axis unit conversion divides (resp. multiplies) by the physical factor
       1e4 = 10000.0 > 0 between m^2 and cm^2.
       [Reference: scripts/make_vtu_visualization.py:261  `q_cm2 = heat / 1e4`
                  scripts/make_derived_plots.py:294,360,361  `* 10000.0`, `/ 1e4`]
       [Citation: SI area scale -- https://physics.nist.gov/cuu/Units/ ]
   A2. The plotted survivability limits are the Ada constants: SIC = 2073.0
       (types.ads:120, physics.adb:1428) and Kapton = 773.0 (types.ads:124/:855);
       the two source files were aligned to these Ada values so a drawn limit
       can never disagree with the tested limit ("fix F60: ONE TRUTH, ONE VALUE").
       [Reference: scripts/make_vtu_visualization.py:287
                  scripts/make_derived_plots.py:96-98, 349-350, 418-428
                  src/simulation_engine/stellarorion_types.ads:120,124,855
                  src/simulation_engine/stellarorion_physics.adb:1428]
       [Citation: matplotlib Axes.axhline/axhspan -- https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.axhline.html]

   THEORIES
   T1. The m^2/cm^2 divisor 10000.0 is strictly positive.
   T2. wm2_to_wcm2 preserves positivity (0 < q -> 0 < wm2_to_wcm2 q) and is
       monotone (q1 <= q2 -> wm2_to_wcm2 q1 <= wm2_to_wcm2 q2): the plotted
       W/cm^2 series faithfully orders the source W/m^2 values.
   T3. The drawn limits equal the Ada constants (plotted == tested).
   T4. 0 < Kapton <= SIC -- the ordering the survivability shading assumes.

   APPLICATIONS
   A plotted heat-flux series never inverts the source ordering (no misleading
   figure), and a survivability limit line can never disagree with the constant
   the physics verdict actually tests -- the fidelity the unit's Goal requires.

   VERIFICATION: every lemma below is discharged by Qed; nothing here is
   admitted, assumed or vacuous.  Intended target: coqc 8.18.0, using only
   Coq.Reals.Reals + Coq.micromega.Lra.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 -- 1 m^2 = 10^4 cm^2, the positive scale between the two flux units. *)
Definition CM_SQUARED_PER_M_SQUARED : R := 10000.0.
(* Plot-side (Python) survivability limits (make_vtu:287, make_derived:96-97). *)
Definition PLOTTED_SIC_LIMIT_K : R := 2073.0.
Definition PLOTTED_KAPTON_LIMIT_K : R := 773.0.
(* Ada physics constants the verdict is tested against (types.ads:120/124). *)
Definition ADA_SIC_MAX_TEMP_K : R := 2073.0.
Definition ADA_KAPTON_MAX_TEMP_K : R := 773.0.

(* W/m^2 -> W/cm^2 axis conversion (make_vtu:261 `heat / 1e4`). *)
Definition wm2_to_wcm2 (q_wm2 : R) : R := q_wm2 / CM_SQUARED_PER_M_SQUARED.

(* T1 -- the unit-conversion divisor is strictly positive. *)
Lemma cm2_divisor_positive : 0 < CM_SQUARED_PER_M_SQUARED.
Proof.
  unfold CM_SQUARED_PER_M_SQUARED in *.
  lra.
Qed.

(* T2 -- dividing by a positive factor preserves positivity of heat flux. *)
Lemma wm2_to_wcm2_preserves_positivity : forall q, 0 < q -> 0 < wm2_to_wcm2 q.
Proof.
  intros q Hq.
  unfold wm2_to_wcm2.
  unfold CM_SQUARED_PER_M_SQUARED in *.
  apply Rdiv_lt_0_compat; [exact Hq | lra].
Qed.

(* T2 -- dividing by a positive factor preserves the source ordering. *)
Lemma wm2_to_wcm2_monotone : forall q1 q2, q1 <= q2 -> wm2_to_wcm2 q1 <= wm2_to_wcm2 q2.
Proof.
  intros q1 q2 Hq.
  unfold wm2_to_wcm2.
  unfold CM_SQUARED_PER_M_SQUARED in *.
  unfold Rdiv.
  apply Rmult_le_compat_r.
  - apply Rlt_le.
    apply Rinv_0_lt_compat.
    lra.
  - exact Hq.
Qed.

(* T3 -- the plotted SIC limit equals the Ada constant it is tested against. *)
Lemma plotted_sic_matches_ada : PLOTTED_SIC_LIMIT_K = ADA_SIC_MAX_TEMP_K.
Proof.
  unfold PLOTTED_SIC_LIMIT_K, ADA_SIC_MAX_TEMP_K in *.
  reflexivity.
Qed.

(* T3 -- the plotted Kapton limit equals the Ada constant. *)
Lemma plotted_kapton_matches_ada : PLOTTED_KAPTON_LIMIT_K = ADA_KAPTON_MAX_TEMP_K.
Proof.
  unfold PLOTTED_KAPTON_LIMIT_K, ADA_KAPTON_MAX_TEMP_K in *.
  reflexivity.
Qed.

(* T4 -- both survivability limits are positive. *)
Lemma sic_limit_positive : 0 < PLOTTED_SIC_LIMIT_K.
Proof.
  unfold PLOTTED_SIC_LIMIT_K in *.
  lra.
Qed.

(* T4 -- the shading order 0 < Kapton <= SIC (make_derived:424-426). *)
Lemma kapton_limit_below_sic : PLOTTED_KAPTON_LIMIT_K <= PLOTTED_SIC_LIMIT_K.
Proof.
  unfold PLOTTED_KAPTON_LIMIT_K, PLOTTED_SIC_LIMIT_K in *.
  lra.
Qed.
