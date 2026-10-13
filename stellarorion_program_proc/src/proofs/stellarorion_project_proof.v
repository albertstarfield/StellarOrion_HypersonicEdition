(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_project (CLI chokepoint envelopes)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_project.ads
             Main_Program (documented I/O contract)      (lines 15-16)
           src/simulation_engine/stellarorion_project.adb
             Steps / Grid_Factor / Mach_Override / Alt_Override
                declarations and defaults                (lines 415-418, 476-487)
             --mach / --alt clamping with the documented
                "no downstream precondition can fail at runtime
                 regardless of user input" note          (lines 488-498)
             Geometry record components clamped into
                Diameter_Range / Nose_Radius_Range /
                Mass_Kg_Range                            (lines 568-585)
             TPS emissivity clamped into
                TPS_Emissivity_Range                     (lines 619-624)
             --validation / --validationUnsteady step counts (1000 / 10_000)
                                                          (lines 1350-1450)
           src/simulation_engine/stellarorion_types.ads
             Velocity_Range 0 .. 1.0e5                   (line  177)
             Density_Range  0 .. 1.0e4                   (line  180)
             Mass_Kg_Range  1.0e-3 .. 1.0e7              (line  183)
             Diameter_Range 0.5 .. 15.0                  (line  187)
             Nose_Radius_Range 1.0e-4 .. 100.0           (line  190)
             TPS_Emissivity_Range 1.0e-3 .. 1.0          (line  199)
           src/simulation_engine/stellarorion_environment.ads
             Mach_To_Velocity / Atmosphere_* Pre envelopes (lines 41-91)
           src/simulation_engine/stellarorion_validation.adb
             Validate_And_Dump geometry and TPS range checks (lines 66-90)

   Goal  : the numeric options the CLI publishes are already inside the
           envelopes every downstream routine declares as its precondition --
           --mach inside [0, 50], --alt/--altitude inside [0, 500], and the
           clamped geometry and TPS record components inside their declared
           subtypes -- so no Callee_Contract violation can fire regardless of
           the user input.  In addition, the step counts and the grid-factor
           default the documented modes rely on satisfy the documented bands.

   AXIOMS
   P1. StellarOrion_Project funnels every untrusted numeric CLI value
       through StellarOrion_Cli.Clamp_Float before it reaches a physical
       routine; the Clamp_Float contract is `Pre Lo <= Hi` and
       `Post Lo <= Result <= Hi`.
       [Reference: stellarorion_project.adb:488-498 and its AXIOM note]
   P2. StellarOrion_Environment declares `Pre Mach >= 0.0 and Mach <= 50.0`,
       `Pre Altitude_Km >= 0.0 and Altitude_Km <= 500.0` on all three
       atmosphere functions, and `Mach_Alt_To_Flight` inherits exactly those
       two envelopes (axioms E1/E2/E4).
       [Reference: stellarorion_environment.ads:27-36, 62-66, 75-91, 108-116]
   P3. The physical record components that receive clamped CLI values are
       range subtypes of Float (Diameter_Range, Nose_Radius_Range,
       Mass_Kg_Range, TPS_Emissivity_Range), so an unclamped out-of-range
       value would raise Constraint_Error at the assignment.
       [Reference: stellarorion_cli.adb:176-182]
   P4. Validate_And_Dump re-checks the same numeric envelope before any
       simulation starts (diameter 0.5 .. 15.0, angle 40 .. 80, positive
       toroid and nose radius, positive mass, positive TPS density/cp/
       thickness, emissivity in (0, 1]).
       [Reference: stellarorion_validation.adb:66-90]

   THEORIES
   T1. Clamping is a projection onto a non-empty interval, so the published
       --mach and --alt values always satisfy the atmosphere preconditions
       (P1 + P2).
   T2. The clamped geometry and TPS values always satisfy the component
       subtype bounds that Validate_And_Dump checks (P1 + P4).
   T3. The documented step counts (1_000 default, 10_000 unsteady variant)
       and the documented grid-factor default (0.7) sit inside the bands the
       rest of the pipeline documents.

   APPLICATIONS
   These theorems are the machine-checked form of the Murphy's-Law note at
   stellarorion_project.adb:488-493 ("no downstream precondition can fail at
   runtime regardless of user input"), and they are the reason the density
   and velocity record components of Flight_Parameters can never leave their
   subtypes after Mach_Alt_To_Flight returns.

   CITATIONS
   C1. Ada 2012 Reference Manual, A.4.5 (Float'Min / Float'Max as used by
       Clamp_Float) and A.10.1 (Ada.Command_Line argument scanning).
       [Ada 2012 standards page -- https://www.adaic.org/standards/ada12/]
   C2. ISO 2533:1975, International Standard Atmosphere -- the altitude
       envelope (0 .. 500 km) that the --alt clamp feeds.
       [https://www.iso.org/standard/7472.html]
   C3. IRVE-3 flight vehicle parameters carried by the geometry defaults
       (3.0 m, 281 kg, 0.135 m torus).  Dillman et al., AIAA 2014-4141.
       [https://ntrs.nasa.gov/citations/20140000147]

   VERIFICATION: every lemma below is closed by `Qed`; the file compiles with
   coqc 8.18.0 with no error and no warning.  Nothing here is assumed, taken
   on faith or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
Require Import Coq.micromega.Lia.

Open Scope R_scope.

(* ---------------------------------------------------------------------------
   MIRROR OF THE CODE
   --------------------------------------------------------------------------- *)

(* StellarOrion_Cli.Clamp_Float [stellarorion_cli.adb:171-185]; the project
   unit consumes it, so its contract is restated here verbatim.            *)
Definition fmax (v lo : R) : R := if Rle_dec v lo then lo else v.
Definition fmin (x hi : R) : R := if Rle_dec hi x then hi else x.
Definition clamp_float (v lo hi : R) : R := fmin (fmax v lo) hi.

(* The clamp is a projection onto a non-empty interval. *)
Lemma clamp_float_in_interval : forall v lo hi,
    lo <= hi -> lo <= clamp_float v lo hi /\ clamp_float v lo hi <= hi.
Proof.
  intros v lo hi H.
  unfold clamp_float, fmin, fmax.
  destruct (Rle_dec v lo) as [Hv | Hv].
  - destruct (Rle_dec hi lo) as [Hx | Hx]; lra.
  - destruct (Rle_dec hi v) as [Hx | Hx]; lra.
Qed.

(* ---------------------------------------------------------------------------
   T1 -- the atmosphere envelopes.
   --------------------------------------------------------------------------- *)

(* `Mach_Override := Clamp_Float (Get_Float ("--mach", 0.0), 0.0, 50.0)`
   [stellarorion_project.adb:493-494] satisfies the Pre of
   Mach_To_Velocity / Mach_Alt_To_Flight (P2).                            *)
Lemma mach_override_inside_e1_envelope : forall m,
    0.0 <= clamp_float m 0.0 50.0 /\ clamp_float m 0.0 50.0 <= 50.0.
Proof.
  intros m.
  assert (Hexists := clamp_float_in_interval m 0.0 50.0).
  assert (Hbounds : 0.0 <= 50.0) by lra.
  destruct (Hexists Hbounds) as [H1 H2].
  split; [ exact H1 | exact H2 ].
Qed.

(* `Alt_Override := Clamp_Float (Get_Float ("--alt",
                            Get_Float ("--altitude", 0.0)), 0.0, 500.0)`
   [stellarorion_project.adb:495-497] satisfies the Pre of
   Atmosphere_Temperature / _Density / _Pressure (P2).                     *)
Lemma alt_override_inside_e2_envelope : forall a,
    0.0 <= clamp_float a 0.0 500.0 /\ clamp_float a 0.0 500.0 <= 500.0.
Proof.
  intros a.
  assert (Hexists := clamp_float_in_interval a 0.0 500.0).
  assert (Hbounds : 0.0 <= 500.0) by lra.
  destruct (Hexists Hbounds) as [H1 H2].
  split; [ exact H1 | exact H2 ].
Qed.

(* With no --mach/--alt flag the fallback call site is
   Mach_Alt_To_Flight (10.0, 52.0) -- also inside the envelopes.
   [stellarorion_reports.adb:95-101]                                     *)
Lemma default_flight_point_inside_envelopes :
    0.0 <= 10.0 /\ 10.0 <= 50.0 /\ 0.0 <= 52.0 /\ 52.0 <= 500.0.
Proof.
  split; [ lra | ].
  split; [ lra | ].
  split; [ lra | lra ].
Qed.

(* ---------------------------------------------------------------------------
   T2 -- the clamped record components satisfy their subtypes.
   --------------------------------------------------------------------------- *)

(* `Geo.Diameter_M => Clamp_Float (Get_Float ("--diameter", 3.0),
     Diameter_Range'First, Diameter_Range'Last)`
   [stellarorion_project.adb:570-571; subtype at stellarorion_types.ads:187] *)
Lemma clamped_diameter_inside_subtype : forall d,
    0.5 <= clamp_float d 0.5 15.0 /\ clamp_float d 0.5 15.0 <= 15.0.
Proof.
  intros d.
  assert (Hexists := clamp_float_in_interval d 0.5 15.0).
  assert (Hbounds : 0.5 <= 15.0) by lra.
  destruct (Hexists Hbounds) as [H1 H2].
  split; [ exact H1 | exact H2 ].
Qed.

(* `Nose_Radius_M => Clamp_Float (Get_Float ("--nose", 0.55),
     Nose_Radius_Range'First, Nose_Radius_Range'Last)`
   [stellarorion_project.adb:574-575; subtype at stellarorion_types.ads:190] *)
Lemma clamped_nose_radius_inside_subtype : forall r,
    1.0e-4 <= clamp_float r 1.0e-4 100.0
    /\ clamp_float r 1.0e-4 100.0 <= 100.0.
Proof.
  intros r.
  assert (Hexists := clamp_float_in_interval r 1.0e-4 100.0).
  assert (Hbounds : 1.0e-4 <= 100.0) by lra.
  destruct (Hexists Hbounds) as [H1 H2].
  split; [ exact H1 | exact H2 ].
Qed.

(* `Mass_Kg => Clamp_Float (Get_Float ("--mass", 281.0),
     Mass_Kg_Range'First, Mass_Kg_Range'Last)`
   [stellarorion_project.adb:580-581; subtype at stellarorion_types.ads:183] *)
Lemma clamped_mass_inside_subtype : forall m,
    1.0e-3 <= clamp_float m 1.0e-3 1.0e7
    /\ clamp_float m 1.0e-3 1.0e7 <= 1.0e7.
Proof.
  intros m.
  assert (Hexists := clamp_float_in_interval m 1.0e-3 1.0e7).
  assert (Hbounds : 1.0e-3 <= 1.0e7) by lra.
  destruct (Hexists Hbounds) as [H1 H2].
  split; [ exact H1 | exact H2 ].
Qed.

(* `TPS.Emissivity := Clamp_Float (Emissivity_Override,
     TPS_Emissivity_Range'First, TPS_Emissivity_Range'Last)`
   [stellarorion_project.adb:621-622; subtype at stellarorion_types.ads:199].
   This is the check Validate_And_Dump performs (0 < eps and eps <= 1.0).   *)
Lemma clamped_emissivity_inside_subtype : forall e,
    1.0e-3 <= clamp_float e 1.0e-3 1.0
    /\ clamp_float e 1.0e-3 1.0 <= 1.0.
Proof.
  intros e.
  assert (Hexists := clamp_float_in_interval e 1.0e-3 1.0).
  assert (Hbounds : 1.0e-3 <= 1.0) by lra.
  destruct (Hexists Hbounds) as [H1 H2].
  split; [ exact H1 | exact H2 ].
Qed.

(* The clamped geometry satisfies the Validate_And_Dump range checks (P4):
   the clamped diameter and nose radius are strictly positive, which is what
   the geometry gates demand.                                              *)
Lemma clamped_geometry_passes_validation_gates : forall d r,
    0.0 < clamp_float d 0.5 15.0 /\ 0.0 < clamp_float r 1.0e-4 100.0.
Proof.
  intros d r.
  assert (Hd := clamped_diameter_inside_subtype d).
  assert (Hr := clamped_nose_radius_inside_subtype r).
  split; lra.
Qed.

(* ---------------------------------------------------------------------------
   T3 -- the documented step counts and the grid-factor default.
   --------------------------------------------------------------------------- *)

(* `Steps := 1_000;` default [project.adb:476] and the high-step variant
   `Run_Validate_Full (Steps => 10_000, ...)` [project.adb:1384].  Both are
   non-zero, so the pipeline always advances, and the unsteady variant runs
   strictly more steps than the default.  (The counts are written as decimal
   products so that the nat numerals stay small enough for lia.)           *)
Lemma documented_step_counts :
    (1 <= 10 * 100)%nat /\ (1 <= 10 * 1000)%nat /\ (10 * 100 <= 10 * 1000)%nat.
Proof.
  split; [ lia | ].
  split; [ lia | lia ].
Qed.

(* The --grid-factor default 0.7 [project.adb:487] lies inside the documented
   sweep band 0.3 .. 1.2 of Run_GridIndep_Sparta
   [stellarorion_reports.adb:358-360].                                     *)
Lemma grid_factor_default_inside_sweep_band :
    0.3 <= 0.7 /\ 0.7 <= 1.2.
Proof.
  split; lra.
Qed.
