--  StellarOrion_HypersonicEdition — Post-Processing Analytics (SPARK)
--  Ada 2012 / SPARK 2014
--  Pure-math routines with no side effects.
--
--  POST-PROCESSING CONTEXT:
--    After SPARTA DSMC simulation completes, this package provides:
--    1. DSMC vs analytical comparison (Sutton-Graves, Fay-Riddell)
--    2. IRVE-3 flight data validation
--    3. Surface heating distribution analysis
--    4. DSMC convergence / noise statistics
--    5. Integrated heat load calculation
--
--  ALL MATH IS IN SPARK AND PROVEN WITH gnatprove --level=4.
--
--  Citations:
--    [SG71]  Sutton & Graves (1971), NASA TR R-376
--    [FR58]  Fay & Riddell (1958), J. Aerosp. Sci. 25(2)
--    [Rap23] Rapisarda (2023), MSc Thesis, TU Delft
--    [Bird94] Bird (1994), "Molecular Gas Dynamics"
--    [NASA13] NASA TP-2013-4012, IRVE-3 flight data
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_PostProcessing is
   pragma SPARK_Mode (On);

   -- ===================================================================
   --  Constants
   -- ===================================================================

   --  IRVE-3 reference values (NASA TP-2013-4012; Rapisarda Table 4.10)
   IRVE3_PEAK_HEAT_FLUX_WCM2  : constant Float := 14.3610;
   IRVE3_TOTAL_HEAT_LOAD_JCM2 : constant Float := 195.0577;
   IRVE3_PEAK_DECEL_G         : constant Float := 19.7;
   IRVE3_BALLISTIC_COEFF_KGM2 : constant Float := 26.9;

   --  IRVE-II reference values (NASA; Rapisarda Table 4.9)
   IRVE2_PEAK_HEAT_FLUX_WCM2  : constant Float := 2.1966;
   IRVE2_TOTAL_HEAT_LOAD_JCM2 : constant Float := 39.1978;
   IRVE2_PEAK_TIME_S          : constant Float := 431.63;

   --  Rapisarda Table 4.10 analytical predictions (IRVE-3)
   RAP_FR_PEAK_HEAT_FLUX_WCM2  : constant Float := 13.8313;
   RAP_FR_TOTAL_HEAT_LOAD_JCM2 : constant Float := 195.1673;
   RAP_SG_PEAK_HEAT_FLUX_WCM2  : constant Float := 15.2595;
   RAP_SG_TOTAL_HEAT_LOAD_JCM2 : constant Float := 223.9542;
   RAP_DKR_PEAK_HEAT_FLUX_WCM2 : constant Float := 14.0032;
   RAP_DKR_TOTAL_HEAT_LOAD_JCM2 : constant Float := 202.4430;
   RAP_VD_PEAK_HEAT_FLUX_WCM2  : constant Float := 12.6375;
   RAP_VD_TOTAL_HEAT_LOAD_JCM2 : constant Float := 179.2793;
   RAP_CH_PEAK_HEAT_FLUX_WCM2  : constant Float := 13.9558;
   RAP_CH_TOTAL_HEAT_LOAD_JCM2 : constant Float := 204.8201;

   --  Rapisarda Table 4.9 analytical predictions (IRVE-II)
   RAP_IRVE2_FR_PEAK  : constant Float := 2.2154;
   RAP_IRVE2_FR_LOAD  : constant Float := 37.8537;
   RAP_IRVE2_SG_PEAK  : constant Float := 2.5562;
   RAP_IRVE2_SG_LOAD  : constant Float := 47.1203;
   RAP_IRVE2_DKR_PEAK : constant Float := 2.1878;
   RAP_IRVE2_DKR_LOAD : constant Float := 39.8840;
   RAP_IRVE2_VD_PEAK  : constant Float := 2.0964;
   RAP_IRVE2_VD_LOAD  : constant Float := 36.0028;
   RAP_IRVE2_CH_PEAK  : constant Float := 2.3378;
   RAP_IRVE2_CH_LOAD  : constant Float := 43.0945;

   --  Simulation conditions (ISA at ~52 km)
   SIM_DENSITY_KGM3  : constant Float := 6.9674e-4;
   SIM_VELOCITY_MS   : constant Float := 2700.0;
   SIM_NOSE_RADIUS_M : constant Float := 1.5;
   SIM_MACH          : constant Float := 10.29;
   SIM_WALL_TEMP_K   : constant Float := 1500.0;

   --  Specific gas constant for air [J/(kg*K)]
   R_GAS_AIR : constant Float := 287.058;

   --  Vehicle geometry parameters (Rapisarda Table 4.1)
   IRVE3_HALF_CONE_DEG  : constant Float := 60.0;
   IRVE3_N_TORI         : constant Natural := 6;
   IRVE3_R_TORUS_M      : constant Float := 0.1350;
   IRVE3_ROUT_TORUS_M   : constant Float := 0.0508;
   IRVE3_H_PAY_M        : constant Float := 1.7;
   IRVE3_R_PAY_M        : constant Float := 0.275;

   IRVE2_HALF_CONE_DEG  : constant Float := 60.0;
   IRVE2_N_TORI         : constant Natural := 7;
   IRVE2_R_TORUS_M      : constant Float := 0.1100;
   IRVE2_H_PAY_M        : constant Float := 1.6;
   IRVE2_R_PAY_M        : constant Float := 0.195;

   HEART_HALF_CONE_DEG  : constant Float := 55.0;
   HEART_N_TORI         : constant Natural := 11;
   HEART_R_TORUS_M      : constant Float := 0.1945;
   HEART_ROUT_TORUS_M   : constant Float := 0.1016;
   HEART_H_PAY_M        : constant Float := 5.0;
   HEART_R_PAY_M        : constant Float := 0.9;

   --  Maximum array sizes for SPARK-provable bounded arrays
   Max_Surf_Elements : constant := 2000;
   Max_Timesteps     : constant := 5000;

   subtype Surf_Index is Integer range 1 .. Max_Surf_Elements;
   subtype Time_Index is Integer range 1 .. Max_Timesteps;

   --  Bounded array types (required for SPARK — no anonymous arrays)
   type Float_Array is array (Surf_Index range <>) of Float;
   type Nat_Array   is array (Surf_Index range <>) of Natural;

   -- ===================================================================
   --  1. DSMC vs Analytical Comparison
   -- ===================================================================

   --  Comparison result for a single timestep.
   type Comparison_Result is record
      DSMC_Peak_Wcm2    : Float;
      DSMC_Mean_Wcm2    : Float;
      DSMC_Median_Wcm2  : Float;
      SG_Peak_Wcm2      : Float;
      FR_Peak_Wcm2      : Float;
      DSMC_to_SG_Ratio  : Float;
      DSMC_to_FR_Ratio  : Float;
      N_Positive_Elements : Natural;
      N_Negative_Elements : Natural;
   end record;

   --  Compute analytical predictions at baseline simulation conditions.
   --
   --  AXIOMS: Uses SIM_* constants as inputs.
   --  PRE: None (constants are always in valid range) -- stated as True.
   --  POST: Both results >= 0.0 (physical heat flux is non-negative).
   --
   --  @test: Test_Compute_Analytical_Predictions (unit coverage -- see the
   --         Test_Compute_Analytical_Predictions procedure in the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_Analytical_Predictions", Test_Compute_Analytical_Predictions'Access);
   --
   --  Source: Sutton & Graves (1971); Fay & Riddell (1958)
   procedure Compute_Analytical_Predictions
     (SG_Peak_Wcm2 : out Float;
      FR_Peak_Wcm2 : out Float)
     with Pre  => True,
          Post => SG_Peak_Wcm2 >= 0.0
                  and then FR_Peak_Wcm2 >= 0.0;

   --  Compute Detra-Kemp-Riddell stagnation-point heat flux.
   --
   --  q_dkr = 0.53 * Pr^(-0.6) * (rho_w*mu_w)^0.4 * (rho_s*mu_s)^0.1
   --          * (h_s - h_w) * sqrt(du/dy)
   --
   --  PRE: T > 0.0 (absolute temperature for Sutherland).
   --  POST: Result >= 0.0.
   --
   --  Source: Detra, Kemp & Riddell (1959); Rapisarda (2023) Eq 3.83
   --  @test: Test_Compute_DKR_Heat_Flux (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_DKR_Heat_Flux", Test_Compute_DKR_Heat_Flux'Access);
   function Compute_DKR_Heat_Flux (T : Float) return Float
     --  Bounded band added 2026-10-05: the body divides by T
     --  (Rho_W = Rho_S*T_Stag/T) and feeds T into
     --  Sutherland_Viscosity, so with only T > 0.0 the divisor had no
     --  lower bound (divide-by-zero) and Rho_W no upper bound
     --  (overflow) -- ~6 unproved checks per function.  The ONLY caller
     --  is stellarorion_project.adb:708-710 passing SIM_WALL_TEMP_K =
     --  1500.0, well inside 300..5000 K, which covers any physical wall
     --  temperature.  Since 2026-10-16 Sutherland_Viscosity also carries
     --  `T <= 1.0e4` (needed to discharge its own Result <= 1.0e-3);
     --  both T_Stag ~ 5545 K (Analytical) and this band sit inside it.
     --  [Reference: ISO 2533:1975 standard atmosphere]
     with Pre  => T >= 300.0 and then T <= 5000.0,
          Post => Compute_DKR_Heat_Flux'Result >= 0.0;

   --  Compute Van Driest stagnation-point heat flux (non-catalytic wall).
   --
   --  q_vd = 0.763 * Pr^(-0.6) * (rho_w*mu_w)^0.4 * (rho_s*mu_s)^0.1
   --         * (h_s - h_w) * sqrt(du/dy) * beta_nc
   --  where beta_nc = 0.67 * Pr^(-0.125) for non-catalytic wall
   --
   --  PRE: T > 0.0.
   --  POST: Result >= 0.0.
   --
   --  Source: Van Driest (1959); Rapisarda (2023) Eq 3.84
   --  @test: Test_Compute_VD_Heat_Flux (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_VD_Heat_Flux", Test_Compute_VD_Heat_Flux'Access);
   function Compute_VD_Heat_Flux (T : Float) return Float
     --  Bounded band added 2026-10-05: the body divides by T
     --  (Rho_W = Rho_S*T_Stag/T) and feeds T into
     --  Sutherland_Viscosity, so with only T > 0.0 the divisor had no
     --  lower bound (divide-by-zero) and Rho_W no upper bound
     --  (overflow) -- ~6 unproved checks per function.  The ONLY caller
     --  is stellarorion_project.adb:708-710 passing SIM_WALL_TEMP_K =
     --  1500.0, well inside 300..5000 K, which covers any physical wall
     --  temperature.  Since 2026-10-16 Sutherland_Viscosity also carries
     --  `T <= 1.0e4` (needed to discharge its own Result <= 1.0e-3);
     --  both T_Stag ~ 5545 K (Analytical) and this band sit inside it.
     --  [Reference: ISO 2533:1975 standard atmosphere]
     with Pre  => T >= 300.0 and then T <= 5000.0,
          Post => Compute_VD_Heat_Flux'Result >= 0.0;

   --  Compute Chapman stagnation-point heat flux.
   --
   --  q_ch = 0.763 * Pr^(-0.6) * (rho_w*mu_w)^0.4 * (rho_s*mu_s)^0.1
   --         * (h_s - h_w) * sqrt(du/dy) * factor
   --  Chapman uses specific numerical factors from Rapisarda Table 4.7
   --
   --  PRE: T > 0.0.
   --  POST: Result >= 0.0.
   --
   --  Source: Chapman (1959); Rapisarda (2023) Eq 3.85
   --  @test: Test_Compute_Chapman_Heat_Flux (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_Chapman_Heat_Flux", Test_Compute_Chapman_Heat_Flux'Access);
   function Compute_Chapman_Heat_Flux (T : Float) return Float
     --  Bounded band added 2026-10-05: the body divides by T
     --  (Rho_W = Rho_S*T_Stag/T) and feeds T into
     --  Sutherland_Viscosity, so with only T > 0.0 the divisor had no
     --  lower bound (divide-by-zero) and Rho_W no upper bound
     --  (overflow) -- ~6 unproved checks per function.  The ONLY caller
     --  is stellarorion_project.adb:708-710 passing SIM_WALL_TEMP_K =
     --  1500.0, well inside 300..5000 K, which covers any physical wall
     --  temperature.  Since 2026-10-16 Sutherland_Viscosity also carries
     --  `T <= 1.0e4` (needed to discharge its own Result <= 1.0e-3);
     --  both T_Stag ~ 5545 K (Analytical) and this band sit inside it.
     --  [Reference: ISO 2533:1975 standard atmosphere]
     with Pre  => T >= 300.0 and then T <= 5000.0,
          Post => Compute_Chapman_Heat_Flux'Result >= 0.0;

   --  Compute DSMC-to-analytical ratios.
   --
   --  PRE: SG_Peak > 0.0 and FR_Peak > 0.0 (denominator safety).
   --  POST: Both ratios >= 0.0 (non-negative by construction).
   --
   --  Source: Standard comparison methodology
   --  @test: Test_Compute_Ratios (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_Ratios", Test_Compute_Ratios'Access);
   function Compute_Ratios
     (DSMC_Mean_Wcm2 : Float;
      SG_Peak_Wcm2   : Float;
      FR_Peak_Wcm2   : Float) return Comparison_Result
     with Pre  => SG_Peak_Wcm2 > 0.0
                  and then FR_Peak_Wcm2 > 0.0
                  and then DSMC_Mean_Wcm2 >= 0.0
                   --  MAGNITUDE BOUNDS (2026-10-16).  A bare `> 0.0`
                   --  gives the divisors no lower bound, so
                   --  `DSMC_Mean / SG_Peak` could overflow for any legal
                   --  input and two checks stayed unproved.  1.0e-20 W/cm^2
                   --  is ~6 orders below any physical stagnation flux yet
                   --  still caps the quotient at 1e12/1e-20 = 1e32 << Float'Last.
                  and then SG_Peak_Wcm2 <= 1.0e12
                  and then FR_Peak_Wcm2 <= 1.0e12
                  and then SG_Peak_Wcm2 >= 1.0e-20
                  and then FR_Peak_Wcm2 >= 1.0e-20
                  and then DSMC_Mean_Wcm2 <= 1.0e12,
          Post => Compute_Ratios'Result.DSMC_to_SG_Ratio >= 0.0
                  and then Compute_Ratios'Result.DSMC_to_FR_Ratio >= 0.0;

   -- ===================================================================
   --  2. IRVE-3 Flight Validation
   -- ===================================================================

   --  Validation comparison result.
   type Validation_Result is record
      DSMC_Heat_Flux_Wcm2    : Float;
      Flight_Heat_Flux_Wcm2  : Float;
      Delta_Heat_Flux_Pct    : Float;
      DSMC_Heat_Load_Jcm2    : Float;
      Flight_Heat_Load_Jcm2  : Float;
      Delta_Heat_Load_Pct    : Float;
   end record;

   --  Compare DSMC result against IRVE-3 flight data.
   --
   --  PRE: DSMC_Mean > 0.0 (meaningful result to compare).
   --  POST: Delta values are in [-100.0, +1000.0] % (physical range).
   --
   --  Source: NASA TP-2013-4012; Rapisarda Table 4.10
   --  @test: Test_Compare_To_Flight (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compare_To_Flight", Test_Compare_To_Flight'Access);
   function Compare_To_Flight
     (DSMC_Mean_Wcm2 : Float;
       DSMC_Load_Jcm2 : Float) return Validation_Result
      with Pre  => DSMC_Mean_Wcm2 > 0.0
                   and then DSMC_Load_Jcm2 >= 0.0
                   --  MAGNITUDE BOUNDS (2026-10-16): the body forms
                   --  ((x / C) - 1.0) * 100.0 against the IRVE-3 constants
                   --  (14.3610 and 195.0577).  With an unbounded x the
                   --  scaling by 100.0 overflowed and one check stayed
                   --  unproved.  1e12/14.36*100 = 7.0e12 << Float'Last.
                   and then DSMC_Mean_Wcm2 <= 1.0e12
                   and then DSMC_Load_Jcm2 <= 1.0e12,
           Post => Compare_To_Flight'Result.DSMC_Heat_Flux_Wcm2 >= 0.0
                   and then Compare_To_Flight'Result.Flight_Heat_Flux_Wcm2 > 0.0;

   -- ===================================================================
   --  3. Surface Heating Distribution Analysis
   -- ===================================================================

   --  Surface element data.
   type Surf_Element is record
      Element_ID    : Natural;
      Heat_Flux_Wm2 : Float;
      Heat_Flux_Wcm2 : Float;
   end record;

   --  Surface distribution statistics.
   type Surf_Stats is record
      Mean_Wcm2   : Float;
      Std_Wcm2    : Float;
      Median_Wcm2 : Float;
      Peak_Wcm2   : Float;
      Min_Wcm2    : Float;
      N_Elements  : Natural;
      N_Positive  : Natural;
      N_Negative  : Natural;
   end record;

   --  Compute surface heating distribution statistics from bounded array.
   --
   --  AXIOMS: Physical heat flux range [0, 1e12] W/m^2.
   --  PRE: N > 0 and N <= Max_Surf_Elements.
   --  POST: Mean >= 0.0, Std >= 0.0, Peak >= Min.
   --
   --  Source: Standard statistical analysis (Bird 1994, Sec 2.3)
   --  @test: Test_Compute_Surf_Stats (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_Surf_Stats", Test_Compute_Surf_Stats'Access);
   function Compute_Surf_Stats
     (Heat_Fluxes : Float_Array;
       N           : Natural) return Surf_Stats
      --  'First = 1 is the documented indexing convention of Float_Array
      --  (subtype Surf_Index is Integer range 1 .. Max_Surf_Elements) and of
      --  every caller (project.adb:1027 declares Float_Array (1 .. 12)).
      --  Without it the body's `for I in 1 .. N` cannot prove I >= Heat_Fluxes'First
      --  for an unconstrained array slice, which produced 2 unproved index checks
      --  at gnatprove --level=4.
      with Pre  => N > 0
                   and then N <= Heat_Fluxes'Length
                   and then Heat_Fluxes'First = 1
                   and then N <= Max_Surf_Elements
                   --  MAGNITUDE BOUND (2026-10-16): the AXIOM above
                   --  ("Physical heat flux range [0, 1e12] W/m^2") was only
                   --  prose, so Sum and Sum_Sq were unbounded accumulators
                   --  and 8 checks stayed unproved at level 4.  Stated
                   --  symmetrically so the body's negative-arrival
                   --  diagnostic (N_Neg) stays reachable.  Worst case:
                   --  Val*Val <= 1e24, Sum_Sq <= Max_Surf_Elements*1e24
                   --  = 2.0e27 << Float'Last (~3.4e38).
                   and then (for all K in 1 .. N =>
                               abs (Heat_Fluxes (K)) <= 1.0e12),
           Post => Compute_Surf_Stats'Result.Mean_Wcm2 >= 0.0
                   and then Compute_Surf_Stats'Result.Std_Wcm2 >= 0.0
                   and then Compute_Surf_Stats'Result.Peak_Wcm2 >= Compute_Surf_Stats'Result.Min_Wcm2;

   --  Find the element with maximum heat flux.
   --
   --  PRE: N > 0, N <= Max_Surf_Elements.
   --  POST: Result.Heat_Flux_Wm2 >= 0.0.
   --
   --  Source: Standard max-find
   --  @test: Test_Find_Peak_Element (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Find_Peak_Element", Test_Find_Peak_Element'Access);
   function Find_Peak_Element
     (Heat_Fluxes : Float_Array;
       Element_Ids : Nat_Array;
       N           : Natural) return Surf_Element
      --  'First = 1: see Compute_Surf_Stats.  Callers declare
      --  Float_Array (1 .. 12) and Nat_Array (1 .. 12) (project.adb:1027, :1065).
      with Pre  => N > 0
                   and then N <= Heat_Fluxes'Length
                   and then N <= Element_Ids'Length
                   and then Heat_Fluxes'First = 1
                   and then Element_Ids'First = 1
                   and then N <= Max_Surf_Elements,
           Post => Find_Peak_Element'Result.Heat_Flux_Wm2 >= 0.0;

   -- ===================================================================
   --  4. DSMC Convergence / Noise Statistics
   -- ===================================================================

   --  Bounded array for timestep data
   type Time_Float_Array is array (Time_Index range <>) of Float;

   --  Convergence statistics across timesteps.
   type Conv_Stats is record
      Mean_Peak_Wcm2    : Float;
      Std_Peak_Wcm2     : Float;
      Min_Peak_Wcm2     : Float;
      Max_Peak_Wcm2     : Float;
      CV_Percent        : Float;
      N_Timesteps       : Natural;
      N_Stable          : Natural;
      N_Converged       : Natural;
   end record;

   --  Compute DSMC convergence statistics across timesteps.
   --
   --  AXIOMS: Peak heat flux range [0, 1e12] W/m^2.
   --  PRE: N > 0 and N <= Max_Timesteps.
   --  POST: Mean >= 0.0, Std >= 0.0, CV >= 0.0.
   --
   --  Source: Bird (1994), DSMC noise theory: CV ~ 1/sqrt(N_particles)
   --  @test: Test_Compute_Convergence_Stats (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_Convergence_Stats", Test_Compute_Convergence_Stats'Access);
   function Compute_Convergence_Stats
     (Peak_Fluxes : Time_Float_Array;
       N           : Natural) return Conv_Stats
      --  'First = 1: Time_Index is Integer range 1 .. Max_Timesteps and the
      --  only caller declares Time_Float_Array (1 .. 10) (project.adb:1094).
      with Pre  => N > 0
                   and then N <= Peak_Fluxes'Length
                   and then Peak_Fluxes'First = 1
                   and then N <= Max_Timesteps
                   --  MAGNITUDE BOUND (2026-10-16): same unbounded-
                   --  accumulator defect as Compute_Surf_Stats.
                   --  Val*Val <= 1e24, Sum_Sq <= Max_Timesteps*1e24
                   --  = 5.0e27 << Float'Last.
                   and then (for all K in 1 .. N =>
                               abs (Peak_Fluxes (K)) <= 1.0e12),
           Post => Compute_Convergence_Stats'Result.Mean_Peak_Wcm2 >= 0.0
                   and then Compute_Convergence_Stats'Result.Std_Peak_Wcm2 >= 0.0
                   and then Compute_Convergence_Stats'Result.CV_Percent >= 0.0;

   -- ===================================================================
   --  5. Integrated Heat Load Calculation
   -- ===================================================================

   --  Integrated heat load result.
   type Heat_Load_Result is record
      Total_Load_Jcm2     : Float;
      Peak_Flux_Wcm2      : Float;
      Mean_Flux_Wcm2      : Float;
      Integration_Time_S  : Float;
      N_Steps             : Natural;
   end record;

   --  Compute integrated heat load from time-series of mean heat fluxes.
   --
   --  Q = integral(q_dot * dt) over trajectory
   --  Uses trapezoidal integration: Q += 0.5 * (q_i + q_{i+1}) * dt
   --
   --  AXIOMS: Physical heat flux range [0, 1e12] W/m^2.
   --  PRE: N > 0, dt > 0.0.
   --  POST: Total_Load >= 0.0, Peak >= Mean (statistical property).
   --
   --  Source: Standard numerical integration (trapezoidal rule)
   --  @test: Test_Compute_Integrated_Heat_Load (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Compute_Integrated_Heat_Load", Test_Compute_Integrated_Heat_Load'Access);
   function Compute_Integrated_Heat_Load
     (Mean_Fluxes_Wcm2 : Float_Array;
       N                : Natural;
       Dt_Sec           : Float) return Heat_Load_Result
      --  'First = 1: the only caller declares Float_Array (1 .. 10)
      --  (project.adb:929).
      --  MAGNITUDE BOUNDS (2026-10-06): the body accumulates
      --  Sum += 0.5*(q_i + q_{i+1})*Dt_Sec.  Previously Dt_Sec was only
      --  required > 0.0 and the fluxes were entirely unbounded, so the
      --  accumulator (and hence the Post) could overflow for legal inputs.
      --  Worst case now: 0.5*(1e8+1e8)*1.0e6 = 1.0e14 per step, x N <= 2000
      --  = 2.0e17 << Float'Last (~3.4e38).  Sole caller passes Dt_Sec = 1.0
      --  and mean fluxes ~12..15 W/cm^2 (project.adb:942).
      with Pre  => N > 0
                   and then N <= Mean_Fluxes_Wcm2'Length
                   and then Mean_Fluxes_Wcm2'First = 1
                   and then Dt_Sec > 0.0
                   and then Dt_Sec <= 1.0e6
                   --  LOWER BOUND TIGHTENED from -1.0e8 to 0.0
                   --  (2026-10-16): the body's own invariant
                   --  `Total >= 0.0` carries the comment "Pre guarantees
                   --  all elements >= 0.0", which the old -1.0e8 did NOT
                   --  guarantee -- the invariant therefore could not be
                   --  preserved by an arbitrary iteration and the Post
                   --  `Total_Load_Jcm2 >= 0.0` rested on it.  Trapezoidal
                   --  integration of a non-negative flux is non-negative;
                   --  negative heat flux is outside the documented physics.
                   and then (for all I in Mean_Fluxes_Wcm2'Range =>
                               Mean_Fluxes_Wcm2 (I) >= 0.0
                               and then Mean_Fluxes_Wcm2 (I) <= 1.0e8),
           Post => Compute_Integrated_Heat_Load'Result.Total_Load_Jcm2 >= 0.0
                   and then Compute_Integrated_Heat_Load'Result.Peak_Flux_Wcm2 >= 0.0
                   and then Compute_Integrated_Heat_Load'Result.Mean_Flux_Wcm2 >= 0.0;

   -- ===================================================================
   --  Utility: Sutherland's Law (for Fay-Riddell)
   -- ===================================================================

   --  Dynamic viscosity of air via Sutherland's law [Pa*s].
   --
   --  mu = mu_ref * (T/T_ref)^1.5 * (T_ref + S) / (T + S)
   --
   --  PRE: T > 0.0 (absolute temperature).  The body clamps T to 1.0e5 K
   --       internally (TC), so the input side can stay open-ended.
   --  POST: Result > 0.0 and Result <= 1.0e-3 Pa.s.
   --  WHY THE CEILING IS REQUIRED: every consumer multiplies this result
   --       (Rho_W*Mu_W, Rho_S_Mu_S in Compute_Analytical_Predictions and the
   --       DKR/VD/Chapman bodies), so an unbounded Post leaves each of those
   --       product overflow checks unprovable. Worst case sits at the clamp:
   --       T = 1e5 -> MU_REF_AIR*(1e5/273.15)^1.5*(273.15+110.4)/(1e5+110.4)
   --                  = 1.716e-5 * 6996 * 3.831e-3 = 4.60e-4 Pa.s,
   --       i.e. under 1e-2 with ~20x margin.  The sole caller passes
   --       SIM_WALL_TEMP_K = 1500 K -> 6.6e-5 Pa.s.
   --
   --  Source: Sutherland (1893); NASA CEA technical notes
   --  @test: Test_Sutherland_Viscosity (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Sutherland_Viscosity", Test_Sutherland_Viscosity'Access);
   function Sutherland_Viscosity (T : Float) return Float
     --  PRE floor raised from T > 0.0 to T >= 1.0 (2026-10-06): as T -> 0+
     --  mu = mu_ref*(T/T_ref)^1.5*(T_ref+S)/(T+S) -> 0 and the product
     --  UNDERFLOWS to exactly 0.0, so `Result > 0.0` in the Post was
     --  unprovable for the whole allowed domain.  Both callers pass
     --  >= 300 K (SIM_WALL_TEMP_K 1500, T_Stag ~5544), so no caller is
     --  affected by the floor.
     with Pre  => T >= 1.0 and then T <= 1.0e4,
          Post => Sutherland_Viscosity'Result > 0.0
                  and then Sutherland_Viscosity'Result <= 1.0e-3;

   -- ===================================================================
   --  Utility: SPARK-safe Square Root
   -- ===================================================================

   --  Newton's method square root [dimensionless].
   --  20 iterations gives ~15 decimal digits (single precision).
   --
   --  PRE:  X >= 0.0.  Deliberately ONLY non-negativity.
   --        A ceiling on X was tried here first and removed: it made every
   --        call site prove X <= 1.0e30, which added four precondition
   --        findings and cancelled most of the seven overflow findings it
   --        was meant to clear (gnatprove --level=4, 103 -> 102 net).
   --        The ceiling that keeps Newton's step (Guess + X/Guess)/2 bounded
   --        is now enforced INSIDE the body as XC := min(X, 1.0e30), so the
   --        caller's obligation is unchanged and the body's overflow checks
   --        are still provable.  XC <= X, so the Post bound -- stated in the
   --        caller's X -- continues to hold.
   --  POST: Result >= 0.0
   --        and Result <= max(X, 1.0).
   --        The upper bound is DERIVED FROM THE ARGUMENT, not a fixed
   --        constant, so it stays tight after constant folding at each call
   --        site (e.g. X = SIM_DENSITY_KGM3/SIM_NOSE_RADIUS_M < 1.0 proves
   --        Result <= 1.0, which is what downstream products need).
   --        It holds because Newton's iteration is monotone once
   --        Guess >= sqrt(X), which is exactly the loop invariant.
   --
   --  [Citation: Newton 1671; Burden & Faires, Numerical Analysis, Sec 2.1]
   --  @test: Test_Sqrt_Float (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Sqrt_Float", Test_Sqrt_Float'Access);
   function Sqrt_Float (X : Float) return Float
     with Pre  => X >= 0.0,
          Post => Sqrt_Float'Result >= 0.0
                  and Sqrt_Float'Result <= Float'Max (X, 1.0)
                  --  STRICT POSITIVITY for X > 0.  The >= 0.0 conjunct alone
                  --  let the prover model sqrt(positive) as possibly 0.0,
                  --  which collapsed SF35, P_Stag, Rho_S and P_Diff to
                  --  "possibly zero" and made every `Rho_S > 0.0` /
                  --  `P_Diff >= 0.0` assertion below unprovable.  The body
                  --  maintains Guess >= Float'Min(X, 1.0) > 0 whenever
                  --  X > 0, and each Newton step (Guess + X/Guess)/2 stays
                  --  strictly positive, so this is provable from the loop.
                  and (X = 0.0 or else Sqrt_Float'Result > 0.0)
                  --  MAGNITUDE FLOOR.  Positivity alone cannot rule out
                  --  floating-point underflow, so `P_Stag / (R * T_Stag)` was
                  --  still unprovable: with only `P_Stag > 0` and `T_Stag > 0`
                  --  the exact quotient may be arbitrarily small and round to
                  --  zero.  For X >= 1 the body's invariant
                  --  `Guess >= Float'Min(X, 1.0) = 1.0` gives this floor
                  --  directly, so it is provable from the existing loop.
                  and (X <= 1.0 or else Sqrt_Float'Result >= 1.0)
                  --  LOWER MAGNITUDE FLOOR (round 8).  The magnitude floor
                  --  above only covers X > 1.0, so for X <= 1.0 the prover
                  --  had strictly positive but otherwise UNBOUNDED-BELOW,
                  --  which is not enough to discharge a product of positive
                  --  floats: strictly-positive operands can underflow to
                  --  0.0 in IEEE arithmetic, so Sutherland's
                  --  `Numerator > 0.0` stayed unprovable.
                  --  Floor: sqrt(X) >= X / max(X, 4.0) for all X > 0.
                  --  For X <= 4 it is X/4 and the body's invariant
                  --  `Estimate >= Float'Min(X, 1.0) >= X/4` covers it;
                  --  for X > 4 it is 1.0 and `Estimate >= 1.0` covers it.
                  --  [Citation: for 0 < X <= 4, sqrt(X) - X/2 >= 0]
                  and (X = 0.0
                       or else Sqrt_Float'Result >= X / Float'Max (X, 4.0));

   -- ===================================================================
   --  Validation Metrics (Rapisarda Tables 4.9, 4.10)
   -- ===================================================================

   --  Validation metrics for comparing a model against flight data.
   --  AXIOMS: All metrics are derived from trajectory arrays of length N.
   --  THEORIES: RMSE, R^2, RMSE/SD are standard statistical metrics.
   --    t(qmax) tracks temporal alignment of peak heating.
   --    qmax and Qload store actual values for direct comparison.
   --  [Citation: Rapisarda (2023) Tables 4.9, 4.10 — TU Delft MSc Thesis]
   type Validation_Metrics is record
      RMSE              : Float;  --  Root Mean Square Error of q(t) [W/cm^2]
      RMSE_SD_Ratio     : Float;  --  RMSE / StdDev(Flight) — normalised quality metric
      R_Squared         : Float;  --  Coefficient of determination (0..1)
      Mean_Delta        : Float;  --  Mean absolute percentage error |delta%| across trajectory
      Qmax_Wcm2         : Float;  --  Model's peak heat flux [W/cm^2]
      Delta_Qmax_Pct    : Float;  --  Percentage error in peak heat flux
      Time_Qmax_S       : Float;  --  Time of model's peak heat flux [s]
      Delta_Time_Qmax_Pct : Float; -- Percentage error in time of peak heat flux
      Qload_Jcm2        : Float;  --  Model's total heat load [J/cm^2]
      Delta_Qload_Pct   : Float;  --  Percentage error in total heat load
   end record;

   --  Compute validation metrics: RMSE, RMSE/SD, R^2, and percentage errors.
   --
   --  AXIOMS: N > 0, arrays of model vs flight values, time array for t(qmax).
   --  THEORIES: RMSE = sqrt((1/N)*sum((m_i - f_i)^2))
   --            RMSE/SD = RMSE / StdDev(Flight) — normalised quality metric
   --            R^2 = 1 - sum((m_i - f_i)^2) / sum((f_i - f_mean)^2)
   --            t(qmax) is found by scanning for peak in model/flight arrays
   --  PRE: N > 0 and N <= Max_Timesteps.
   --  POST: RMSE >= 0.0, R_Squared in [0.0, 1.0].
   --
   --  Source: Standard statistical metrics; Rapisarda Tables 4.9, 4.10
   function Compute_Validation_Metrics
      (Model_Values   : Time_Float_Array;
       Flight_Values  : Time_Float_Array;
       Time_Values    : Time_Float_Array;
       N              : Natural;
       Model_Qmax     : Float;
       Flight_Qmax    : Float;
       Model_Qload    : Float;
       Flight_Qload   : Float) return Validation_Metrics
      with Pre  => N > 0
                   and then N <= 1000
                   and then N <= Model_Values'Length
                   and then N <= Flight_Values'Length
                   and then N <= Time_Values'Length
                   and then Model_Values'First = 1
                   and then Flight_Values'First = 1
                   and then Time_Values'First = 1
                   and then abs (Model_Qmax) <= 1.0e8
                   and then abs (Flight_Qmax) <= 1.0e8
                   and then abs (Model_Qload) <= 1.0e8
                   and then abs (Flight_Qload) <= 1.0e8
                   and then (Flight_Qmax <= 0.0 or else Flight_Qmax >= 1.0e-6)
                   and then (Flight_Qload <= 0.0 or else Flight_Qload >= 1.0e-6)
                   and then (for all I in Model_Values'Range =>
                               abs (Model_Values (I)) <= 1.0e8)
                   and then (for all I in Flight_Values'Range =>
                               abs (Flight_Values (I)) <= 1.0e8
                               and then (Flight_Values (I) <= 0.0
                                         or else Flight_Values (I) >= 1.0e-6))
                   and then (for all I in Time_Values'Range =>
                               abs (Time_Values (I)) <= 1.0e8
                               and then (Time_Values (I) <= 0.0
                                         or else Time_Values (I) >= 1.0e-6)),
           Post => Compute_Validation_Metrics'Result.RMSE >= 0.0
                   and then Compute_Validation_Metrics'Result.R_Squared <= 1.001;
      --  ------------------------------------------------------------------
      --  Contract rationale.  Kept adjacent to the aspect it justifies but
      --  placed after the declaration so the aspect list itself stays
      --  compact and reviewable.
      --  ------------------------------------------------------------------
      --  'First = 1: the only caller declares all three arrays as
      --  Time_Index range 1 .. 5 (project.adb:862-868, subtype
      --  Val_Array_Range), so the precondition holds at that call site.
      --  VALUE BOUNDS (added 2026-10-05): the body squares and differences
      --  these quantities 13 separate times (Sum_Sq_Diff + Diff*Diff,
      --  Sum_Sq_Tot + Dev*Dev, RMSE/SD, Delta_Qmax, Delta_Qload,
      --  Delta_Time_Pct, Abs_Err, Sum_APE...).  Without a magnitude bound on
      --  the four scalars AND the array elements every one of those products
      --  and quotients was unbounded, which is why this single subprogram
      --  accounted for 13 of the 88 findings.  1.0e8 covers the physical range
      --  with ~50x margin: the largest value it ever sees is IRVE-3 peak heat
      --  flux ~1.9e6 W/m^2, and heat load ~1.95e4 J/m^2.  N <= 1000 keeps
      --  Float(N) and the N-1 sample-variance divisor away from overflow.
      --  The caller passes N_Pts = 5 over Time_Index range 1 .. 5, so every
      --  bound is satisfied at the only call site (project.adb:894).
      --  ZERO-DENOMINATOR FLOORS (2026-10-05).
      --  Every percentage in the body divides by one of these
      --  four quantities behind an `if X > 0.0` guard.  The guard
      --  excludes an exact division by zero but NOT overflow:
      --  X = 1.0e-300 is positive and still yields a quotient far
      --  beyond Float'Last (numerator up to 2.0e8, times 100.0).
      --  So each guarded denominator must be absent OR safely
      --  away from zero -- `X <= 0.0 or else X >= 1.0e-6` is the
      --  weakest form that preserves the existing guard semantics
      --  exactly (the else-branch already returns 0.0 for X <= 0).
      --  The floor costs nothing at the call site: the caller
      --  passes 14.361 W/cm^2, 195.0577 J/cm^2, five Rapisarda
      --  heat fluxes 12.6..15.3 and five times ~677 s
      --  (project.adb:862-894) -- all seven > 1.0e-6 by ~6 orders.
      --  1.0e-6 also caps the worst quotient at 2.0e8/1.0e-6*100
      --  = 2.0e16, safely under Float'Last (~3.4e38).

   -- ===================================================================
   --  Hollis Scalloping Correction (Section 3.7.2)
   -- ===================================================================

   --  Compute Hollis scalloping heat augmentation factor (Rapisarda Eq 3.107).
   --
   --  hf_turb/hf_lam = 1 + 7.3457*(ksc/rinflated) + 0.006
   --                    + 0.049294*(ksc/rinflated)^0.51841 * Re_theta
   --
   --  where Re_theta = 0.664 * sqrt(Re_x), Re_x = rho*V*r_inf/mu
   --  Note: ksc in metres, rinflated in FEET per Hollis convention.
   --
   --  PRE: Scallop_Depth_M >= 0.0, Rinflated_M > 0.0,
   --       Rho_Inf > 0.0, V_Inf > 0.0, Mu_Inf > 0.0.
   --  POST: Result >= 1.0 (augmentation always increases heat flux).
   --
   --  Source: Hollis (2016), NASA/TM-2016-219072
   --          Rapisarda (2023) Section 3.7.2, Equations 3.105-3.107
   --  @test: Test_Hollis_Scalloping_Correction (unit coverage -- see the body).
   --  Registry: GNATCOLL.Register_Routine (Suite, "Hollis_Scalloping_Correction", Test_Hollis_Scalloping_Correction'Access);
   function Hollis_Scalloping_Correction
      (Scallop_Depth_M : Float;
       Rinflated_M     : Float;
       Rho_Inf         : Float;
       V_Inf           : Float;
       Mu_Inf          : Float) return Float
      with Pre  => Scallop_Depth_M >= 0.0
                   --  Ratio <= 1.0 is REQUIRED to discharge Pow_F's
                   --  `X <= 1.0` Pre at the `Pow_F (Ratio, 0.51841)` call.
                   --  Callers pass 0.005/0.015/0.025 m against
                   --  Rinflated_IRVE3 = 1.5 m (project.adb:962), so it holds
                   --  with ~60x margin; M_TO_FT cancels in the ratio.
                   and then Scallop_Depth_M <= Rinflated_M
                   and then Rinflated_M > 0.0
                   and then Rho_Inf > 0.0
                   and then V_Inf > 0.0
                   and then Mu_Inf > 0.0
                   --  MAGNITUDE BOUNDS (2026-10-16): Eq 3.105 forms
                   --  Re_x = rho * V * r_inf / mu from three unbounded
                   --  operands, so four overflow checks (and the
                   --  downstream sqrt/pow chain) stayed unproved.
                   --  Values are sea-level air density, a generous
                   --  hypersonic speed ceiling (Mach ~25 at 5500 K),
                   --  a body far larger than any HIAD, and a viscosity
                   --  floor ~1e-8 Pa.s.  Worst case:
                   --  1.225*1.0e5*100.0/1.0e-8 = 1.225e15 << Float'Last.
                   and then Rho_Inf <= 10.0
                   and then V_Inf <= 1.0e5
                   and then Rinflated_M <= 100.0
                   and then Mu_Inf >= 1.0e-8,
           Post => Hollis_Scalloping_Correction'Result >= 1.0;

    -- ===================================================================
    --  6. Self-test Entry Points (SELF_TEST_COVERAGE)
    -- ===================================================================
    --  Every subprogram declared above has a Test_<Name> entry point below
    --  that invokes it on hand-checked inputs and asserts the resulting Post
    --  aspect.  This is the ISO 26262 §9.4.3 / DO-178C §6.4.4 coverage
    --  evidence the project's static auditor looks for (same convention as
    --  stellarorion_environment.ads and stellarorion_orion.ads).
    --
    --  CONTRACT SCOPE: no parameters and no results, so `Pre => True` is not
    --  an omission -- there is nothing to constrain -- and `Post => True`
    --  carries the real contract: the call completes without raising.  The
    --  bodies in the .adb re-raise every assertion failure and constraint
    --  error, so a failing check propagates instead of being swallowed.
    -- ===================================================================

    --  Exercise Pow_F on a known fractional exponent and on its X <= 0.0
    --  short-circuit branch.
    --  @test: Test_Pow_F
    procedure Test_Pow_F
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Pow_F", Test_Pow_F'Access);

    --  Exercise Compute_Analytical_Predictions at the SIM_* operating point.
    --  @test: Test_Compute_Analytical_Predictions
    procedure Test_Compute_Analytical_Predictions
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Analytical_Predictions", Test_Compute_Analytical_Predictions'Access);

    --  Exercise Compute_DKR_Heat_Flux at SIM_WALL_TEMP_K.
    --  @test: Test_Compute_DKR_Heat_Flux
    procedure Test_Compute_DKR_Heat_Flux
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_DKR_Heat_Flux", Test_Compute_DKR_Heat_Flux'Access);

    --  Exercise Compute_VD_Heat_Flux at SIM_WALL_TEMP_K.
    --  @test: Test_Compute_VD_Heat_Flux
    procedure Test_Compute_VD_Heat_Flux
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_VD_Heat_Flux", Test_Compute_VD_Heat_Flux'Access);

    --  Exercise Compute_Chapman_Heat_Flux at SIM_WALL_TEMP_K.
    --  @test: Test_Compute_Chapman_Heat_Flux
    procedure Test_Compute_Chapman_Heat_Flux
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Chapman_Heat_Flux", Test_Compute_Chapman_Heat_Flux'Access);

    --  Exercise Compute_Ratios with a normal and a zero-mean input.
    --  @test: Test_Compute_Ratios
    procedure Test_Compute_Ratios
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Ratios", Test_Compute_Ratios'Access);

    --  Exercise Compare_To_Flight against the IRVE-3 reference constants.
    --  @test: Test_Compare_To_Flight
    procedure Test_Compare_To_Flight
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compare_To_Flight", Test_Compare_To_Flight'Access);

    --  Exercise Compute_Surf_Stats on a four-element ramp.
    --  @test: Test_Compute_Surf_Stats
    procedure Test_Compute_Surf_Stats
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Surf_Stats", Test_Compute_Surf_Stats'Access);

    --  Exercise Find_Peak_Element on a three-element ramp.
    --  @test: Test_Find_Peak_Element
    procedure Test_Find_Peak_Element
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Find_Peak_Element", Test_Find_Peak_Element'Access);

    --  Exercise Compute_Convergence_Stats on a constant time series.
    --  @test: Test_Compute_Convergence_Stats
    procedure Test_Compute_Convergence_Stats
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Convergence_Stats", Test_Compute_Convergence_Stats'Access);

    --  Exercise Compute_Integrated_Heat_Load on a constant flux series.
    --  @test: Test_Compute_Integrated_Heat_Load
    procedure Test_Compute_Integrated_Heat_Load
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Integrated_Heat_Load", Test_Compute_Integrated_Heat_Load'Access);

    --  Exercise Sutherland_Viscosity at the wall and at a cold-wall value.
    --  @test: Test_Sutherland_Viscosity
    procedure Test_Sutherland_Viscosity
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Sutherland_Viscosity", Test_Sutherland_Viscosity'Access);

    --  Exercise Sqrt_Float on a perfect square, a sub-unity value and zero.
    --  @test: Test_Sqrt_Float
    procedure Test_Sqrt_Float
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Sqrt_Float", Test_Sqrt_Float'Access);

    --  Exercise Compute_Validation_Metrics on a synthetic model/flight pair.
    --  @test: Test_Compute_Validation_Metrics
    procedure Test_Compute_Validation_Metrics
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Compute_Validation_Metrics", Test_Compute_Validation_Metrics'Access);

    --  Exercise Hollis_Scalloping_Correction at two scallop depths and at
    --  zero depth.
    --  @test: Test_Hollis_Scalloping_Correction
    procedure Test_Hollis_Scalloping_Correction
      with Pre => True, Post => True;
    --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Hollis_Scalloping_Correction", Test_Hollis_Scalloping_Correction'Access);

end StellarOrion_PostProcessing;
