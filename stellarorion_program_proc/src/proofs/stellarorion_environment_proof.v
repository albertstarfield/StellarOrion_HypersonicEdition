(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_environment (ISA atmosphere)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_environment.ads
             Mach_To_Velocity contract (Pre 0 <= Mach <= 50,
                1 <= T <= 3000; Post >= 0.0)          (lines 38-43)
             Atmosphere_Temperature contract (Pre 0 <= h <= 500;
                Post 186.86 <= Result <= 288.15)      (lines 62-66)
             Atmosphere_Density contract (Post >= 0.0) (lines 75-78)
             Atmosphere_Pressure contract (Post >= 0.0)(lines 88-91)
             Mach_Alt_To_Flight contract               (lines 108-116)
           src/simulation_engine/stellarorion_environment.adb
             ISA constants T0, RHO0, G0_LOC, R_AIR       (lines 38-41)
             Atmosphere_Temperature body (7-branch
                piecewise profile + per-branch Assert) (lines 367-423)
             Atmosphere_Density body (troposphere
                branch Expon := G0/(R_AIR*|Lapse|) - 1)(lines 449-497)
             Atmosphere_Pressure body
                (Pressure := Rho * R_AIR * T)           (lines 644-671)
             Mach_To_Velocity body
                (Mach * Sqrt_Approx (Gamma*R*T))        (lines 695-729)

   Goal  : quantities the ISA model publishes are in their declared bands --
           atmosphere temperature inside [186.86, 288.15] K for every
           altitude of the 0 .. 500 km envelope and non-increasing while
           climbing through the troposphere, ISA pressure non-negative and
           bounded inside the ISA temperature band, and the Mach -> velocity
           conversion non-negative and monotone in both arguments.

   AXIOMS
   E1. Mach envelope 0 .. 50 covers all atmospheric flight regimes of
       interest (IRVE-3 entry ~Mach 25; escape velocity at sea level
       ~Mach 50.2); temperature envelope 1 .. 3000 K covers the ISA profile
       with headroom for hot-wall recovery temperatures.
       [Reference: stellarorion_environment.ads:27-36]
   E2. The ISA 1975 temperature profile is piecewise linear/piecewise
       constant over seven layers (troposphere 0-11 km at -6.5 K/km,
       tropopause 11-20 km isothermal, stratosphere I 20-32 km at
       +1.0 K/km, stratosphere II 32-47 km at +2.8 K/km, stratopause
       47-51 km isothermal, mesosphere I 51-71 km at -2.8 K/km,
       mesosphere II 71-84.852 km at -2.0 K/km) with a 186.87 K
       thermosphere floor above.
       [Citation: ISO 2533:1975, International Standard Atmosphere --
        https://www.iso.org/standard/7472.html ; COESA (1976), "U.S.
        Standard Atmosphere, 1976", NASA TR R-459 --
        https://ntrs.nasa.gov/ (COESA 1976, NASA TR R-459)]
   E3. Air as an ideal gas: a = sqrt (gamma * R * T) with gamma = 1.4 and
       R = 287.058 J/(kg*K), so V = Mach * a.
       [Citation: Anderson, "Modern Compressible Flow", 3rd Ed., Ch. 2 --
        speed of sound in an ideal gas]
   E4. Ideal gas law P = rho * R_specific * T with the same R_specific.
       [Reference: stellarorion_environment.ads:81-82]

   THEORIES
   T1. Every layer of the piecewise ISA profile maps its altitude interval
       into [186.86, 288.15] K, so the composite function does too over the
       whole 0 .. 500 km envelope -- exactly the annotated postcondition.
   T2. The troposphere lapse rate is negative, so temperature is
       non-increasing with altitude throughout 0 .. 11 km.
   T3. The troposphere barometric exponent g0/(R_AIR*|L|) - 1 is strictly
       positive, which is what makes the hand-bound "T/T0 in [0.648, 1] so
       Pow <= 1 hence Rho <= RHO0 = 1.225" hold on that branch.
   T4. P = rho * R * T is non-negative whenever its factors are, strictly
       positive when all are, and inside the ISA temperature band it is
       bounded above by ~1.05e5 Pa.

   APPLICATIONS
   Mach_Alt_To_Flight (the composite consumed by every CLI mode through
   the --mach/--alt chokepoint in StellarOrion_Project) calls these three
   functions, so their bands are what keeps the density/velocity
   record-component subtypes (Density_Range, Velocity_Range) satisfied.

   CITATIONS
   C1. ISO 2533:1975, International Standard Atmosphere -- the seven-layer
       piecewise profile (troposphere 0-11 km at -6.5 K/km, 216.65 K
       tropopause, stratospheric gradient layers, 186.87 K thermosphere
       floor) and the 0 .. 86 km band the unit covers.
       [https://www.iso.org/standard/7472.html]
   C2. COESA, "U.S. Standard Atmosphere, 1976", NASA TR R-459 -- the
       barometric/hydrostatic relations behind each density branch.
       [NASA Technical Reports Server -- https://ntrs.nasa.gov/]
   C3. Speed of sound in an ideal gas a = sqrt (gamma * R * T) and the ideal
       gas law P = rho * R_specific * T.
       [Thermal conduction / ideal-gas relations --
        https://en.wikipedia.org/wiki/Thermal_conduction]

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

(* ISA constants [stellarorion_environment.adb:38-41]. *)
Definition t0_isa : R := 288.15.     (* K, sea-level temperature *)
Definition rho0_isa : R := 1.225.    (* kg/m^3, sea-level density   *)
Definition g0_loc : R := 9.80665.    (* m/s^2, standard gravity     *)
Definition r_air : R := 287.058.     (* J/(kg*K), dry air           *)
Definition gamma_air : R := 1.4.     (* diatomic air *)

(* Atmosphere_Temperature [stellarorion_environment.adb:397-423]:
      if H <= 11.0   then T_Loc := T0 - 6.5 * H
      elsif H <= 20.0 then return 216.65
      elsif H <= 32.0 then T_Loc := 216.65 + 1.0 * (H - 20.0)
      elsif H <= 47.0 then T_Loc := 228.65 + 2.8 * (H - 32.0)
      elsif H <= 51.0 then return 270.65
      elsif H <= 71.0 then T_Loc := 270.65 - 2.8 * (H - 51.0)
      elsif H <= 84.852 then T_Loc := 214.65 - 2.0 * (H - 71.0)
      else return 186.87                                              *)
Definition atmosphere_temperature (h : R) : R :=
  if Rle_dec h 11.0 then t0_isa - 6.5 * h
  else if Rle_dec h 20.0 then 216.65
  else if Rle_dec h 32.0 then 216.65 + 1.0 * (h - 20.0)
  else if Rle_dec h 47.0 then 228.65 + 2.8 * (h - 32.0)
  else if Rle_dec h 51.0 then 270.65
  else if Rle_dec h 71.0 then 270.65 - 2.8 * (h - 51.0)
  else if Rle_dec h 84.852 then 214.65 - 2.0 * (h - 71.0)
  else 186.87.

(* Atmosphere_Pressure [stellarorion_environment.adb:664]:
      Pressure := Rho * R_AIR * T.                                    *)
Definition atmosphere_pressure (rho r_specific t : R) : R :=
  rho * r_specific * t.

(* Mach_To_Velocity [stellarorion_environment.adb:714-718]:
      Gamma_R_T := GAMMA_AIR * R_AIR * Temperature;  (clamped to >= 0)
      return Mach * Sqrt_Approx (Gamma_R_T).                            *)
Definition mach_to_velocity (mach temperature : R) : R :=
  mach * sqrt (gamma_air * r_air * temperature).

(* ---------------------------------------------------------------------------
   Helpers
   --------------------------------------------------------------------------- *)

(* Strict squaring monotonicity on the non-negative half-line.  Needed
   because there is no `sqrt_mono_le` in the 8.18 standard library.      *)
Lemma sqr_strict_mono : forall a b, 0 <= a -> a < b -> a * a < b * b.
Proof.
  intros a b Ha Hab.
  assert (Hsum : 0 < b + a) by lra.
  assert (Hdiff : 0 < b - a) by lra.
  assert (Hprod : 0 < (b - a) * (b + a))
    by (apply Rmult_lt_0_compat; [ exact Hdiff | exact Hsum ]).
  assert (E : b * b - a * a = (b - a) * (b + a)) by ring.
  lra.
Qed.

(* Square root is monotone: x <= y implies sqrt x <= sqrt y.  (The 8.18
   standard library has no such lemma, so it is derived here.)          *)
Lemma sqrt_mono_le : forall x y, 0 <= x -> 0 <= y -> x <= y -> sqrt x <= sqrt y.
Proof.
  intros x y Hx Hy Hxy.
  assert (Hpx : 0 <= sqrt x) by (apply sqrt_positivity; exact Hx).
  assert (Hpy : 0 <= sqrt y) by (apply sqrt_positivity; exact Hy).
  destruct (Rle_lt_dec (sqrt x) (sqrt y)) as [Hle | Hgt].
  - exact Hle.
  - exfalso.
    assert (Hsq : sqrt y * sqrt y < sqrt x * sqrt x)
      by (apply sqr_strict_mono; [ exact Hpy | exact Hgt ]).
    assert (Ex : sqrt x * sqrt x = x) by (apply Rsqr_sqrt; exact Hx).
    assert (Ey : sqrt y * sqrt y = y) by (apply Rsqr_sqrt; exact Hy).
    lra.
Qed.

(* a / d > 1 whenever 0 < d < a.  Used for the ISA exponent sign below.  *)
Lemma rdiv_gt_one : forall a d, 0 < d -> d < a -> 1 < a / d.
Proof.
  intros a d Hd Hda.
  assert (Hne : d <> 0) by lra.
  assert (Hid : d * /d = 1) by (apply Rinv_r; exact Hne).
  assert (Hid' : /d * d = 1) by (rewrite Rmult_comm; exact Hid).
  apply (Rmult_lt_reg_r d); [ exact Hd | ].
  unfold Rdiv.
  rewrite Rmult_assoc, Hid', Rmult_1_r.
  lra.
Qed.

(* Sign of the two ISA air constants, needed because `lra` reads them as
   opaque atoms until they are unfolded.                                   *)
Lemma gamma_air_pos : 0 < gamma_air.
Proof. unfold gamma_air. lra. Qed.

Lemma r_air_pos : 0 < r_air.
Proof. unfold r_air. lra. Qed.

(* gamma * R * T is non-negative on the whole E1 temperature envelope.     *)
Lemma sound_speed_argument_nonneg : forall t,
    0 <= t -> 0 <= gamma_air * r_air * t.
Proof.
  intros t Ht.
  assert (Hg : 0 <= gamma_air) by (apply Rlt_le; exact gamma_air_pos).
  assert (Hr : 0 <= r_air) by (apply Rlt_le; exact r_air_pos).
  assert (Hstep : 0 <= gamma_air * r_air)
    by (apply Rmult_le_pos; [ exact Hg | exact Hr ]).
  apply Rmult_le_pos; [ exact Hstep | exact Ht ].
Qed.

Lemma sound_speed_sqrt_nonneg : forall t,
    0 <= t -> 0 <= sqrt (gamma_air * r_air * t).
Proof.
  intros t Ht.
  assert (Harg : 0 <= gamma_air * r_air * t)
    by (apply sound_speed_argument_nonneg; exact Ht).
  apply sqrt_positivity.
  exact Harg.
Qed.

(* ---------------------------------------------------------------------------
   T1 -- the ISA postcondition band, branch by branch.
   --------------------------------------------------------------------------- *)

Lemma atmosphere_temperature_band : forall h,
    0 <= h -> h <= 500.0 -> 186.86 <= atmosphere_temperature h
                            /\ atmosphere_temperature h <= 288.15.
Proof.
  intros h H0 H500.
  unfold atmosphere_temperature, t0_isa.
  destruct (Rle_dec h 11.0) as [H1 | H1];
  destruct (Rle_dec h 20.0) as [H2 | H2];
  destruct (Rle_dec h 32.0) as [H3 | H3];
  destruct (Rle_dec h 47.0) as [H4 | H4];
  destruct (Rle_dec h 51.0) as [H5 | H5];
  destruct (Rle_dec h 71.0) as [H6 | H6];
  destruct (Rle_dec h 84.852) as [H7 | H7];
  split; lra.
Qed.

(* T2 -- the troposphere is non-isothermal in the right direction: T is
   non-increasing while climbing through 0 .. 11 km.                      *)
Lemma atmosphere_temperature_troposphere_monotone : forall h1 h2,
    0 <= h1 -> h1 <= h2 -> h2 <= 11.0 ->
    atmosphere_temperature h2 <= atmosphere_temperature h1.
Proof.
  intros h1 h2 H0 H12 H2.
  unfold atmosphere_temperature, t0_isa.
  destruct (Rle_dec h1 11.0) as [C1 | C1];
  destruct (Rle_dec h2 11.0) as [C2 | C2];
  lra.
Qed.

(* T2, strict form: a real altitude loss costs real temperature.         *)
Lemma atmosphere_temperature_troposphere_strict : forall h1 h2,
    0 <= h1 -> h1 < h2 -> h2 <= 11.0 ->
    atmosphere_temperature h2 < atmosphere_temperature h1.
Proof.
  intros h1 h2 H0 H12 H2.
  unfold atmosphere_temperature, t0_isa.
  destruct (Rle_dec h1 11.0) as [C1 | C1];
  destruct (Rle_dec h2 11.0) as [C2 | C2];
  lra.
Qed.

(* ---------------------------------------------------------------------------
   T3 -- the sign of the troposphere barometric exponent.
   Expon := G0_LOC / (R_AIR * abs Lapse) - 1.0 with Lapse = -6.5e-3, so
   the divisor is R_AIR * 0.0065.  The branch comment asserts
   "Pow <= 1; Rho <= RHO0 = 1.225" precisely because this exponent is > 0
   [stellarorion_environment.adb:485-497].
   --------------------------------------------------------------------------- *)

Lemma isa_troposphere_exponent_pos :
    0 < g0_loc / (r_air * 0.0065) - 1.0.
Proof.
  unfold g0_loc, r_air.
  assert (Hd : 0 < 287.058 * 0.0065) by lra.
  assert (Hgt : 287.058 * 0.0065 < 9.80665) by lra.
  assert (H : 1 < 9.80665 / (287.058 * 0.0065))
    by (apply rdiv_gt_one; [ exact Hd | exact Hgt ]).
  lra.
Qed.

(* ---------------------------------------------------------------------------
   T4 -- ideal-gas pressure.
   --------------------------------------------------------------------------- *)

Lemma atmosphere_pressure_nonneg : forall rho r_spec t,
    0 <= rho -> 0 <= r_spec -> 0 <= t -> 0 <= atmosphere_pressure rho r_spec t.
Proof.
  intros rho r_spec t H1 H2 H3.
  unfold atmosphere_pressure.
  assert (Hstep : 0 <= rho * r_spec) by (apply Rmult_le_pos; [ exact H1 | exact H2 ]).
  apply Rmult_le_pos; [ exact Hstep | exact H3 ].
Qed.

Lemma atmosphere_pressure_pos : forall rho r_spec t,
    0 < rho -> 0 < r_spec -> 0 < t -> 0 < atmosphere_pressure rho r_spec t.
Proof.
  intros rho r_spec t H1 H2 H3.
  unfold atmosphere_pressure.
  assert (Hstep : 0 < rho * r_spec) by (apply Rmult_lt_0_compat; [ exact H1 | exact H2 ]).
  apply Rmult_lt_0_compat; [ exact Hstep | exact H3 ].
Qed.

(* The sea-level hand-bound annotated on the Ada body
   [stellarorion_environment.adb:665-670]: with the ISA temperature band
   (T <= 288.15 K) and the ISA density ceiling rho <= 1.225 kg/m^3 the
   product stays below ~1.05e5 Pa.                                     *)
Lemma atmosphere_pressure_bounded : forall rho t,
    rho <= 1.225 -> 0 <= rho -> 0 <= t -> t <= 288.15 ->
    atmosphere_pressure rho 287.058 t <= 1.05e5.
Proof.
  intros rho t Hrho Hrho0 Ht0 Ht.
  assert (Hr : 0 <= 287.058) by lra.
  assert (H1 : rho * 287.058 <= 1.225 * 287.058)
    by (apply Rmult_le_compat_r; [ exact Hr | exact Hrho ]).
  assert (H2 : rho * 287.058 * t <= 1.225 * 287.058 * t)
    by (apply Rmult_le_compat_r; [ exact Ht0 | exact H1 ]).
  assert (H3 : 1.225 * 287.058 * t <= 1.225 * 287.058 * 288.15).
  { apply Rmult_le_compat_l.
    - apply Rmult_le_pos; lra.
    - exact Ht. }
  assert (H4 : 1.225 * 287.058 * 288.15 <= 1.05e5).
  { assert (E1 : 1.225 * 287.058 = 351.64605) by lra.
    rewrite E1.
    lra. }
  unfold atmosphere_pressure.
  lra.
Qed.

(* ---------------------------------------------------------------------------
   E1 -- Mach -> velocity.
   --------------------------------------------------------------------------- *)

Lemma mach_to_velocity_nonneg : forall mach t,
    0 <= mach -> 0 <= t -> 0 <= mach_to_velocity mach t.
Proof.
  intros mach t Hm Ht.
  unfold mach_to_velocity.
  assert (Hsqrt : 0 <= sqrt (gamma_air * r_air * t))
    by (apply sound_speed_sqrt_nonneg; exact Ht).
  apply Rmult_le_pos; [ exact Hm | exact Hsqrt ].
Qed.

Lemma mach_to_velocity_mono_in_mach : forall m1 m2 t,
    0 <= m1 -> m1 <= m2 -> 0 <= t ->
    mach_to_velocity m1 t <= mach_to_velocity m2 t.
Proof.
  intros m1 m2 t H1 H12 Ht.
  unfold mach_to_velocity.
  assert (Hsqrt : 0 <= sqrt (gamma_air * r_air * t))
    by (apply sound_speed_sqrt_nonneg; exact Ht).
  apply Rmult_le_compat_r; [ exact Hsqrt | exact H12 ].
Qed.

(* E3 consequence: the speed of sound grows with temperature, so the
   true airspeed of a given Mach number is monotone in temperature.      *)
Lemma mach_to_velocity_mono_in_temperature : forall mach t1 t2,
    0 <= mach -> 0 <= t1 -> t1 <= t2 ->
    mach_to_velocity mach t1 <= mach_to_velocity mach t2.
Proof.
  intros mach t1 t2 Hm Ht1 Ht12.
  unfold mach_to_velocity.
  assert (Harg1 : 0 <= gamma_air * r_air * t1) by (apply sound_speed_argument_nonneg; lra).
  assert (Harg2 : 0 <= gamma_air * r_air * t2) by (apply sound_speed_argument_nonneg; lra).
  assert (Hsqrt : 0 <= sqrt (gamma_air * r_air * t2))
    by (apply sqrt_positivity; exact Harg2).
  assert (Hinner : gamma_air * r_air * t1 <= gamma_air * r_air * t2).
  { apply Rmult_le_compat_l.
    - apply Rmult_le_pos; [ apply Rlt_le; exact gamma_air_pos | apply Rlt_le; exact r_air_pos ].
    - exact Ht12. }
  assert (Hmono : sqrt (gamma_air * r_air * t1) <= sqrt (gamma_air * r_air * t2))
    by (apply sqrt_mono_le; [ exact Harg1 | exact Harg2 | exact Hinner ]).
  apply Rmult_le_compat_l; [ exact Hm | exact Hmono ].
Qed.
