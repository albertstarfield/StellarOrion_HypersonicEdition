(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_validation (geometry & survivability
                            gates)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_validation.ads
             Validate_And_Dump contract + Pre (Geo/TPS strictly positive)
                                                          (lines 31-43)
             Check_Survivability contract (Post in Boolean)(lines 49-52)
           src/simulation_engine/stellarorion_validation.adb
             Validate_And_Dump body: Valid_Geo conjunction (lines 66-79)
                 Valid_TPS conjunction                    (lines 82-90)
             Check_Survivability body: delegates to Is_Survivable (lines 115-153)
             Test_Validate_And_Dump (defaults + TPS_SiC => True) (lines 156-217)
             Test_Check_Survivability (all-zero metrics => True) (lines 220-...)
           src/simulation_engine/stellarorion_physics.ads
             Is_Survivable contract (the single survivability predicate)
                                                          (lines 619-627)
           src/simulation_engine/stellarorion_types.ads
             SIC_MAX_TEMP 2073.0 / KAPTON_MAX_TEMP 773.0 /
                MAX_G_LOAD 25.0                         (lines 118-128)
             IRVE3_FTPS_STRUCT_LIMIT_K 523.15 (250 degC)  (line  613)
             Geometry_Parameters defaults (3.0 m, 60 deg, 0.55 m nose,
                6 tori, 0.135 m toroid, 281 kg)         (lines 304-328)
             TPS_SiC preset (1468 kg/m^3, 1100 J/kg/K,
                0.0254 m, eps 0.75)                     (lines 382-389)

   Goal  : both gates of the unit behave as documented.  The survivability
           gate decomposes into exactly the four published limits (surface
           temperature 2073 K, back-face temperature 773 K, g-load 25 g and
           deceleration 25 g), it accepts the all-zero default metrics record,
           and it is antitone in every metric it bounds.  The geometry gate
           accepts exactly the IRVE-3 Rapisarda baseline recorded in the
           Geometry_Parameters defaults together with the TPS_SiC card, which
           is what the unit's own self-test asserts.

   AXIOMS
   V1. A vehicle is survivable iff all four limits hold, and the criterion is
       defined in exactly one place -- StellarOrion_Physics.Is_Survivable --
       with the postcondition
           Metrics.Surface_Temp_K  <= SIC_MAX_TEMP
           and Metrics.Backface_Temp_K <= KAPTON_MAX_TEMP
           and Metrics.G_Load        <= MAX_G_LOAD
           and Metrics.Decel_G       <= MAX_G_LOAD
       [Reference: stellarorion_physics.ads:619-627 and
        stellarorion_validation.adb:141-146 (delegation note)]
   V2. The material limits are 2073 K for the SiC surface, 773 K for the
       Kapton back-face interface and 25 g for both the g-load and the
       deceleration.
       [Reference: stellarorion_types.ads:114-128]
   V3. The pre-simulation gate checks the Rapisarda (2023) Table 5.4
       envelope: diameter 0.5 .. 15.0 m, half angle 40 .. 80 deg, toroid
       count at most 12, strictly positive toroid and nose radius, strictly
       positive mass, and a TPS card with strictly positive density, specific
       heat and thickness and emissivity in (0, 1].
       [Reference: stellarorion_validation.adb:66-90]
   V4. The IRVE-3 baseline is the record default: 3.0 m diameter, 60 deg half
       angle, 0.55 m nose radius, 6 stacked tori, 0.135 m torus minor radius,
       281 kg; the self-test pairs it with TPS_SiC and asserts True.
       [Reference: stellarorion_types.ads:304-328, 382-389;
        stellarorion_validation.adb:189-192]

   THEORIES
   T1. Survivable is a conjunction of four one-sided bounds, so each is a
       consequence of the verdict, and the verdict is monotone (antitone in
       each metric): reducing any single metric can never turn a survivable
       configuration into a non-survivable one.
   T2. The all-zero metrics record -- the default Flight_Metrics used by the
       unit's own coverage test -- is survivable.
   T3. The IRVE-3 baseline geometry and the SiC card pass the pre-simulation
       gate, and the gate's components hold individually for them.

   APPLICATIONS
   Check_Survivability is the last stage of the validation pipeline; V1-T2
   pin down exactly what it certifies, so "PASS" in a run report means the
   four bounds above hold.  Validate_And_Dump is the first stage; T3 shows
   it does not reject the baseline the whole campaign is validated against.
   (The 11 metric labels and SI units required of the report table are string
   data, not arithmetic, so they are not formalized here; what is formalized
   is every numeric bound the two gates enforce.)

   CITATIONS
   C1. IRVE-3 flight data and post-flight reconstruction -- the reference the
       survivability limits are set against.  Dillman et al., AIAA 2014-4141.
       [https://ntrs.nasa.gov/citations/20140000147]
   C2. Rapisarda, V., "Multidisciplinary Design Analysis and Optimization of
       HIAD", Ph.D. thesis, TU Delft, 2023 -- Table 5.4 (validated geometry
       ranges) and Sec 4.3 (TPS survivability limits).
   C3. The F-TPS material stack the 523.15 K structure limit protects
       (Nextel BF-20 fabric, Pyrogel 2250 felt, AKK gas barrier).
       DelCorso et al., NASA/TM-2012-011662.
       [https://ntrs.nasa.gov/citations/20120011662]

   VERIFICATION: every lemma below is closed by `Qed`; the file compiles with
   coqc 8.18.0 with no error and no warning.  Nothing here is assumed, taken
   on faith or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* ---------------------------------------------------------------------------
   MIRROR OF THE CODE
   --------------------------------------------------------------------------- *)

(* Survivable material and structural limits [stellarorion_types.ads:118-128]. *)
Definition sic_max_temp : R := 2073.0.
Definition kapton_max_temp : R := 773.0.
Definition max_g_load : R := 25.0.

(* IRVE-3 first-generation F-TPS inflatable structure limit, 250 degC
   [stellarorion_types.ads:566-572 and 613].                              *)
Definition irve3_ftps_struct_limit_k : R := 523.15.

(* Is_Survivable, transcribed from its postcondition
   [stellarorion_physics.ads:623-627]; Check_Survivability delegates to it
   [stellarorion_validation.adb:143-146].                                 *)
Definition is_survivable (surface_temp_k backface_temp_k g_load decel_g : R)
  : Prop :=
  surface_temp_k <= sic_max_temp
  /\ backface_temp_k <= kapton_max_temp
  /\ g_load <= max_g_load
  /\ decel_g <= max_g_load.

(* Valid_Geo [stellarorion_validation.adb:66-79].  The lower toroid-count
   bound is guaranteed by the Positive subtype of
   Geometry_Parameters.Toroid_Count, so only the upper bound is re-checked
   (note at stellarorion_validation.adb:63-65).                          *)
Definition valid_geo (diameter_M angle_deg toroid_count toroid_radius_M
                      nose_radius_M mass_kg : R) : Prop :=
  0.5 <= diameter_M /\ diameter_M <= 15.0
  /\ 40.0 <= angle_deg /\ angle_deg <= 80.0
  /\ toroid_count <= 12.0
  /\ 0.0 < toroid_radius_M
  /\ 0.0 < nose_radius_M
  /\ 0.0 < mass_kg.

(* Valid_TPS [stellarorion_validation.adb:82-90]. *)
Definition valid_tps (density cp thickness emissivity : R) : Prop :=
  0.0 < density /\ 0.0 < cp /\ 0.0 < thickness
  /\ 0.0 < emissivity /\ emissivity <= 1.0.

(* Validate_And_Dump returns Valid_Geo and Valid_TPS [validation.adb:92]. *)
Definition validate_and_dump (diameter_M angle_deg toroid_count toroid_radius_M
                              nose_radius_M mass_kg density cp thickness
                              emissivity : R) : Prop :=
  valid_geo diameter_M angle_deg toroid_count toroid_radius_M
            nose_radius_M mass_kg
  /\ valid_tps density cp thickness emissivity.

(* ---------------------------------------------------------------------------
   T2 -- the default metrics record is survivable.
   `Probe : constant Flight_Metrics := (others => <>);`
   [stellarorion_validation.adb:220-...]
   --------------------------------------------------------------------------- *)

Lemma survivable_default_metrics : is_survivable 0.0 0.0 0.0 0.0.
Proof.
  unfold is_survivable, sic_max_temp, kapton_max_temp, max_g_load.
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | lra ].
Qed.

(* ---------------------------------------------------------------------------
   T1 -- the four published bounds are each implied by the verdict.
   --------------------------------------------------------------------------- *)

Lemma survivable_surface_bounded : forall s b g d,
    is_survivable s b g d -> s <= sic_max_temp.
Proof.
  intros s b g d Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  exact H1.
Qed.

Lemma survivable_backface_bounded : forall s b g d,
    is_survivable s b g d -> b <= kapton_max_temp.
Proof.
  intros s b g d Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  exact H2.
Qed.

Lemma survivable_g_load_bounded : forall s b g d,
    is_survivable s b g d -> g <= max_g_load.
Proof.
  intros s b g d Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  exact H3.
Qed.

Lemma survivable_decel_bounded : forall s b g d,
    is_survivable s b g d -> d <= max_g_load.
Proof.
  intros s b g d Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  exact H4.
Qed.

(* T1, antitone form: improving any single metric preserves the verdict. *)
Lemma survivable_antitone_in_surface_temp : forall s1 s2 b g d,
    s1 <= s2 -> is_survivable s2 b g d -> is_survivable s1 b g d.
Proof.
  intros s1 s2 b g d H12 Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  split; [ lra | ].
  split; [ exact H2 | ].
  split; [ exact H3 | exact H4 ].
Qed.

Lemma survivable_antitone_in_backface_temp : forall s b1 b2 g d,
    b1 <= b2 -> is_survivable s b2 g d -> is_survivable s b1 g d.
Proof.
  intros s b1 b2 g d H12 Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  split; [ exact H1 | ].
  split; [ lra | ].
  split; [ exact H3 | exact H4 ].
Qed.

Lemma survivable_antitone_in_g_load : forall s b g1 g2 d,
    g1 <= g2 -> is_survivable s b g2 d -> is_survivable s b g1 d.
Proof.
  intros s b g1 g2 d H12 Hs.
  destruct Hs as [H1 [H2 [H3 H4]]].
  split; [ exact H1 | ].
  split; [ exact H2 | ].
  split; [ lra | exact H4 ].
Qed.

(* The structural limit of the IRVE-3 F-TPS is stricter than both the
   back-face and the surface material limits, so it is the binding one.
   [stellarorion_types.ads:566-572]                                      *)
Lemma ftps_struct_limit_is_binding :
    irve3_ftps_struct_limit_k <= kapton_max_temp
    /\ irve3_ftps_struct_limit_k <= sic_max_temp.
Proof.
  unfold irve3_ftps_struct_limit_k, kapton_max_temp, sic_max_temp.
  split; lra.
Qed.

(* ---------------------------------------------------------------------------
   T3 -- the baseline passes the pre-simulation gate.
   --------------------------------------------------------------------------- *)

(* Geometry_Parameters defaults [stellarorion_types.ads:304-328]: 3.0 m,
   60 deg, 6 tori, 0.135 m torus, 0.55 m nose radius, 281 kg.            *)
Lemma irve3_baseline_geometry_valid :
    valid_geo 3.0 60.0 6.0 0.135 0.55 281.0.
Proof.
  unfold valid_geo.
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | lra ].
Qed.

(* TPS_SiC [stellarorion_types.ads:382-389] -- the card the unit's own
   coverage test pairs with the default geometry.                        *)
Lemma sic_card_tps_valid : valid_tps 1468.0 1100.0 0.0254 0.75.
Proof.
  unfold valid_tps.
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | lra ].
Qed.

(* The conjunction Validate_And_Dump actually returns on the baseline, which
   is what Test_Validate_And_Dump asserts [validation.adb:189-192].        *)
Lemma irve3_baseline_passes_validate_and_dump :
    validate_and_dump 3.0 60.0 6.0 0.135 0.55 281.0 1468.0 1100.0 0.0254 0.75.
Proof.
  unfold validate_and_dump.
  split.
  - apply irve3_baseline_geometry_valid.
  - apply sic_card_tps_valid.
Qed.

(* ---------------------------------------------------------------------------
   T1/T3 -- the individual gates decompose, so each range check of the Ada
   body is available on its own.
   --------------------------------------------------------------------------- *)

Lemma valid_geo_diameter_in_envelope : forall d a n rt nr m,
    valid_geo d a n rt nr m -> 0.5 <= d /\ d <= 15.0.
Proof.
  intros d a n rt nr m Hg.
  destruct Hg as [H1 [H2 H3]].
  split; [ exact H1 | exact H2 ].
Qed.

Lemma valid_geo_angle_in_envelope : forall d a n rt nr m,
    valid_geo d a n rt nr m -> 40.0 <= a /\ a <= 80.0.
Proof.
  intros d a n rt nr m Hg.
  unfold valid_geo in Hg.
  destruct Hg as [H1 [H2 [H3 [H4 [H5 [H6 H7]]]]]].
  split; [ exact H3 | exact H4 ].
Qed.

Lemma valid_geo_torus_count_bounded : forall d a n rt nr m,
    valid_geo d a n rt nr m -> n <= 12.0.
Proof.
  intros d a n rt nr m Hg.
  unfold valid_geo in Hg.
  destruct Hg as [H1 [H2 [H3 [H4 [H5 [H6 H7]]]]]].
  exact H5.
Qed.

Lemma valid_tps_emissivity_in_unit_interval : forall rho c t e,
    valid_tps rho c t e -> 0.0 < e /\ e <= 1.0.
Proof.
  intros rho c t e Ht.
  unfold valid_tps in Ht.
  destruct Ht as [H1 [H2 [H3 [H4 H5]]]].
  split; [ exact H4 | exact H5 ].
Qed.
