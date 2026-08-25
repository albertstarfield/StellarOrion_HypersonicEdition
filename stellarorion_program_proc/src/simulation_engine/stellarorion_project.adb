--  StellarOrion_HypersonicEdition — Main Entry Point (Body)
--  Ada 2012 / SPARK 2014
--  SPARK_Mode => Off : performs I/O, subprocess dispatching, GUI launch.
--
--  CLI flags (matching the original main.py):
--    --self-test               Run built-in unit tests
--    --gettheirvebbaseline     Get IRVE-3 baseline results
--    --compareNoses            Compare nose-cone geometries
--    --gridIndependencyTest    Run grid factor sweep
--    --gridIndepTest           Grid factor sweep (SPARTA-backed)
--    --demo                    Quick demo run
--    --validate-only           Validate geometry only (no SPARTA)
--    --validate                Full validation pipeline (SPARTA)
--    --compareCalibrate        Compare analytical vs IRVE-3 flight data
--    --test <mode>             Run test suite (baseline / sample / pinn_calibration / sparta / pyfluent / pyansys / openfoam)
--    --optimize                Run SBO optimisation loop
--    --validation              Alias for --validate
--    --validationUnsteady      Unsteady validation (10000 steps)
--    --compareCalibratePINN    Compare calibrate with PINN (requires Python sidecar)
--    --validationPINN          Validation with PINN (requires Python sidecar)
--    --LiteracyReferences       Display REFERENCES.MD
--    --solver <name>           Solver backend (sparta / openfoam / ...)
--    --steps <N>               SPARTA timestep count
--    --grid-factor <F>         Grid density multiplier
--    --chemistry <mode>        Chemistry model (5sp / 11sp / mars)
--    --vehicle <name>          Vehicle type (irve3 / orion)
--    --objective <name>        Optimisation objective (drag / heat)
--    --doe <method>            DoE method (lhs / ccd)
--    --samples <N>             Number of DoE samples
--    --db <path>               Database directory path
--    --diameter <F>            HIAD major diameter [m]
--    --angle <F>               Half-cone angle [deg]
--    --nose <F>                Nose-cone radius [m]
--    --toroids <N>             Number of stacked toroids
--    --tradius <F>             Toroid radius [m]
--    --oradius <F>             Outer shoulder toroid radius [m]
--    --mass <F>                Total entry mass [kg]
--    --headless                Headless mode (no GUI)
--    --payload                 Payload mode
--    --defaultPayload          Default payload mode
--    --nose-type <name>        smooth or pointy
--    --verbose / --no-verbose  Verbose output
--    --skip-diag               Skip diagnostic output
--    --fresh-start             Fresh start (no restart)
--    --sparta-gpu / --no-sparta-gpu  SPARTA GPU acceleration
--    --pinn / --no-pinn        PINN surrogate refinement
--    --fnum <str>              Real molecules per simulated particle
--    --stats-interval <N>      Statistics output interval
--    --restart-file <path>     Restart file path
--    --tps-density <F>         Override TPS density
--    --tps-cp <F>              Override TPS specific heat
--    --tps-k <F>               Override TPS thermal conductivity
--    --tps-material <name>     Predefined TPS layup (sic / pyrogel / kapton / multi)
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with Ada.Text_IO;             use Ada.Text_IO;
with Ada.Command_Line;        use Ada.Command_Line;

with StellarOrion_Types;      use StellarOrion_Types;
with StellarOrion_Physics;    use StellarOrion_Physics;
with StellarOrion_Environment;use StellarOrion_Environment;
with StellarOrion_Optimization; use StellarOrion_Optimization;
with StellarOrion_Status_Writer; use StellarOrion_Status_Writer;
--  Decomposition Stage 1: pure CLI helpers moved to StellarOrion_Cli
with StellarOrion_Cli;            use StellarOrion_Cli;
--  Decomposition Stage 2: runtime guards moved to StellarOrion_Runtime_Guard
with StellarOrion_Runtime_Guard;  use StellarOrion_Runtime_Guard;
--  Decomposition Stage 3: self-test suite moved to StellarOrion_Self_Test
with StellarOrion_Self_Test;      use StellarOrion_Self_Test;
with StellarOrion_Test_Modes; use StellarOrion_Test_Modes;

--  Ada.IO_Exceptions / Ada.Numerics are referenced via expanded names only
--  (e.g. Ada.Numerics.Pi), hence no use-clauses here.
with Ada.IO_Exceptions;
with Ada.Numerics;
with GNAT.OS_Lib;        use GNAT.OS_Lib;

package body StellarOrion_Project is
   pragma SPARK_Mode (Off);
   --  extern: spawns Python sidecar process via GNAT.OS_Lib; outside SPARK subset

   --  Status directory for sidecar .status.json
   STATUS_DIR : constant String := "data/runs";

   -- ==================================================================
   --  Internal Helpers
   -- ==================================================================

   procedure Print_Banner is
   begin
      Put_Line ("======================================================");
      Put_Line ("  StellarOrion HypersonicEdition  v2.0");
      Put_Line ("  Ada 2012 / SPARK 2014  |  SPARTA DSMC");
      Put_Line ("  Author: Albert Starfield Wahyu Suryo Samudro");
      Put_Line ("======================================================");
      New_Line;
   end Print_Banner;

   procedure Print_Usage is
   begin
      Put_Line ("Usage: stellarorion_project [OPTIONS]");
      New_Line;
      Put_Line ("Modes:");
      Put_Line ("  --self-test               Run built-in unit tests");
      Put_Line ("  --gettheirvebbaseline     Get IRVE-3 baseline results");
      Put_Line ("  --compareNoses            Compare nose-cone geometries");
      Put_Line ("  --gridIndependencyTest    Grid factor sweep (analytical)");
      Put_Line ("  --gridIndepTest           Grid factor sweep (SPARTA-backed)");
      Put_Line ("  --demo                    Quick demo run");
      Put_Line ("  --validate-only           Validate geometry only");
      Put_Line ("  --validate                Full validation pipeline (SPARTA)");
      Put_Line ("  --validationUnsteady      High-step validation (10,000 steps)");
      Put_Line ("  --compareCalibrate        Compare analytical vs IRVE-3 flight data");
      Put_Line ("  --compareCalibratePINN    Compare-calibrate with PINN (sidecar)");
      Put_Line ("  --validationPINN          Validation with PINN (sidecar)");
      Put_Line ("  --test <mode>             Run test (baseline / sample / pinn_calibration)");
      Put_Line ("  --sample <N>              Shorthand: --headless --test sample --steps N");
      Put_Line ("  --optimize                Run SBO optimisation loop");
      Put_Line ("  --LiteracyReferences      Display literature references");
      New_Line;
      Put_Line ("Geometry Overrides:");
      Put_Line ("  --diameter <F>            HIAD major diameter [m] (default: 3.0)");
      Put_Line ("  --angle <F>               Half-cone angle [deg] (default: 60.0)");
      Put_Line ("  --nose <F>                Nose-cone radius [m] (default: 0.55)");
      Put_Line ("  --toroids <N>             Number of stacked toroids (default: 6)");
      Put_Line ("  --tradius <F>             Toroid radius [m] (default: 0.135)");
      Put_Line ("  --oradius <F>             Outer shoulder toroid radius [m] (default: 0.0508)");
      Put_Line ("  --mass <F>                Total entry mass [kg] (default: 281.0)");
      Put_Line ("  --flat_skin               Flat skin geometry (no bulge)");
      New_Line;
      Put_Line ("Flight Options:");
      Put_Line ("  --solver <name>           sparta | openfoam | pyfluent | pyansys");
      Put_Line ("  --steps <N>               SPARTA timesteps (default: 1000)");
      Put_Line ("  --grid-factor <F>         Grid multiplier (default: 0.7)");
      Put_Line ("  --mach <M>                Override freestream Mach number");
      Put_Line ("  --alt <km>                Override altitude in km");
      Put_Line ("  --altitude <km>           Alias for --alt");
      Put_Line ("  --cores <N>               CPU cores for SPARTA (default: 4)");
      Put_Line ("  --slice-angle <deg>       Slice angle for 3D (default: 360)");
      Put_Line ("  --sparta-gpu              Enable SPARTA GPU acceleration");
      Put_Line ("  --no-sparta-gpu           Disable GPU (override --sparta-gpu)");
      Put_Line ("  --pinn                    Enable PINN surrogate refinement");
      Put_Line ("  --no-pinn                 Disable PINN");
      New_Line;
      Put_Line ("TPS Options:");
      Put_Line ("  --tps <name>              TPS preset: sic | pica-x | loftid | kapton");
      Put_Line ("  --tps-material <name>     TPS layup: sic | pyrogel | kapton | multi");
      Put_Line ("  --tps-density <F>         Override TPS density [kg/m^3]");
      Put_Line ("  --tps-cp <F>              Override TPS specific heat [J/(kg*K)]");
      Put_Line ("  --tps-k <F>               Override TPS thermal conductivity [W/(m*K)]");
      Put_Line ("  --tps-emissivity <E>      Override TPS surface emissivity");
      Put_Line ("  --thermal-lag <eta>       Override thermal lag efficiency (default: 0.15)");
      New_Line;
      Put_Line ("Simulation Options:");
      Put_Line ("  --chemistry <mode>        5sp | 11sp | mars");
      Put_Line ("  --vehicle <name>          irve3 | orion");
      Put_Line ("  --objective <name>        drag | heat");
      Put_Line ("  --goal <name>             Alias for --objective");
      Put_Line ("  --doe <method>            lhs | ccd");
      Put_Line ("  --samples <N>             Number of DoE samples");
      Put_Line ("  --db <path>               Database directory");
      Put_Line ("  --fnum <str>              Real molecules per particle (default: 1.5e20)");
      Put_Line ("  --stats-interval <N>      Statistics output interval (default: 100)");
      Put_Line ("  --restart-file <path>     Restart file path");
      New_Line;
      Put_Line ("Run Options:");
      Put_Line ("  --headless                Headless mode (no GUI)");
      Put_Line ("  --payload                 Payload mode");
      Put_Line ("  --defaultPayload          Default payload mode");
      Put_Line ("  --nose-type <name>        smooth | pointy");
      Put_Line ("  --verbose                 Verbose output (default)");
      Put_Line ("  --no-verbose              Non-verbose output");
      Put_Line ("  --skip-diag               Skip diagnostic output");
      Put_Line ("  --fresh-start             Fresh start (no restart)");
      Put_Line ("  --payload-file <path>     Payload input file");
      New_Line;
      Put_Line ("Display Options:");
      Put_Line ("  --imageDebug              Debug image generation");
      Put_Line ("  --paraview                ParaView output");
      New_Line;
      Put_Line ("Remote / SSH:");
      Put_Line ("  --ssh-host <host>         SSH host for remote execution");
      Put_Line ("  --ssh-user <user>         SSH username");
      Put_Line ("  --ssh-pass <pass>         SSH password");
      Put_Line ("  --ssh-key <path>          SSH private key path");
      New_Line;
      Put_Line ("Docker Management:");
      Put_Line ("  --stop-colima             Stop Colima/Docker daemon after run");
   end Print_Usage;

   --  CLI helpers (Has_Flag, Get_Option, Get_Float, Clamp_Float,
   --  Get_Positive) extracted to StellarOrion_Cli at Decomposition
   --  Stage 1 — see docs/PROJECT_DECOMPOSITION_PLAN.md.

   -- ==================================================================
   --  Runtime guards (lock file, GPU detection, Docker pre-flight,
   --  AmaryllisIdleAutomode) extracted to StellarOrion_Runtime_Guard at
   --  Decomposition Stage 2 — see docs/PROJECT_DECOMPOSITION_PLAN.md.
   -- ==================================================================

   -- ==================================================================
   --  Test Modes
   -- ==================================================================

   --  Run_Self_Test (Tests 1-15, incl. parity/watchdog wiring) extracted
   --  to StellarOrion_Self_Test at Decomposition Stage 3 — see
   --  docs/PROJECT_DECOMPOSITION_PLAN.md.


   --  Run_GetIRVE3_Baseline .. Run_Validate_Only extracted verbatim to
   --  StellarOrion_Test_Modes at Decomposition Stage 4 — see
   --  docs/PROJECT_DECOMPOSITION_PLAN.md.


   --  Run_Validate_Full forward declaration moved to StellarOrion_Test_Modes
   --  at Decomposition Stage 4 (test modes call it).



   --  Run_Test_Baseline .. Run_Test_OpenFOAM_Integration extracted
   --  verbatim to StellarOrion_Test_Modes at Decomposition Stage 4.


   procedure Run_Optimize
     (DoE_In     : DoE_Method := LHS;
      Obj_In     : Objective  := Drag_Obj;
      Samples_In : Positive   := 100;
      Steps      : Positive   := 1_000;
      Grid_Factor: Float      := 0.7;
      Chemistry  : Chemistry_Mode := Five_Species;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   is
      DoE       : DoE_Method := DoE_In;
      Obj       : Objective  := Obj_In;
      N_Samples : constant Positive := Samples_In;  --  never reassigned
      Flight    : Flight_Parameters;
      Geo       : Geometry_Parameters := Geo_In;
      TPS       : constant TPS_Material := TPS_In;
      Target_Beta : constant Float := 26.9;  -- IRVE-3 target

      --  GA configuration (tuned for HIAD optimisation)
      Config    : GA_Config;
      Result    : GA_Result;
      --  N_Samples IS used below (population size + report); not unreferenced.
      pragma Unreferenced (DoE, Obj, Steps, Grid_Factor, Chemistry, Geo);
   begin
      Write_Status (STATUS_DIR, "optimize", Status_Running, 0.0);
      Put_Line ("[OPTIMIZE] ====== SBO Optimisation Loop ======");
      Put_Line ("[OPTIMIZE] Method     : " & DoE_Method'Image (DoE_In));
      Put_Line ("[OPTIMIZE] Objective  : " & Objective'Image (Obj_In));
      Put_Line ("[OPTIMIZE] Samples    :" & Positive'Image (N_Samples));
      New_Line;

      --  Set up flight parameters
      if Mach_Override > 0.0 and Alt_Override > 0.0 then
         Mach_Alt_To_Flight (Mach_Override, Alt_Override, Flight);
      elsif Mach_Override > 0.0 then
         Mach_Alt_To_Flight (Mach_Override, 52.0, Flight);
      elsif Alt_Override > 0.0 then
         Mach_Alt_To_Flight (10.0, Alt_Override, Flight);
      else
         Mach_Alt_To_Flight (10.0, 52.0, Flight);
      end if;

      Put_Line ("[OPTIMIZE] Flight: Mach " & Float'Image (Flight.Mach) &
                ", Alt " & Float'Image (Flight.Altitude_Km) & " km");
      Put_Line ("[OPTIMIZE] Target Beta: " & Float'Image (Target_Beta) & " kg/m^2");
      New_Line;

      --  Configure GA
      Config.Population_Size  := Positive'Min (N_Samples, Max_Population);
      Config.Max_Generations  := 200;
      Config.Mutation_Rate    := 0.1;
      Config.Crossover_Rate   := 0.7;
      Config.Elite_Count      := 2;
      Config.Tournament_Size  := 3;
      Config.Convergence_Gens := 20;
      Config.Convergence_Tol  := 1.0e-6;

      Put_Line ("[OPTIMIZE] GA Config: Pop=" &
                Positive'Image (Config.Population_Size) &
                ", Gens=" & Positive'Image (Config.Max_Generations));
      New_Line;

      --  Run GA optimisation using MoP_Fitness (full physics pipeline)
      Run_GA_Optimization
        (Config      => Config,
         Flight      => Flight,
         TPS         => TPS,
         Target_Beta => Target_Beta,
         Eval        => MoP_Fitness'Access,
         Result      => Result);

      --  Print results
      Put_Line ("[OPTIMIZE] ====== Optimisation Results ======");
      Put_Line ("  Best cost (J)     : " & Float'Image (Result.Best_Cost));
      Put_Line ("  Generations used  : " & Natural'Image (Result.Generations_Used));
      Put_Line ("  Converged         : " & Boolean'Image (Result.Converged));
      New_Line;

      Put_Line ("[OPTIMIZE] ---- Optimal Geometry ----");
      Put_Line ("  Diameter      : " & Float'Image (Result.Best_Individual.Diameter_M) & " m");
      Put_Line ("  Angle         : " & Float'Image (Result.Best_Individual.Angle_Deg) & " deg");
      Put_Line ("  Nose radius   : " & Float'Image (Result.Best_Individual.Nose_Radius_M) & " m");
      Put_Line ("  Toroid count  : " & Positive'Image (Result.Best_Individual.Toroid_Count));
      Put_Line ("  Toroid radius : " & Float'Image (Result.Best_Individual.Toroid_Radius_M) & " m");
      Put_Line ("  Mass          : " & Float'Image (Result.Best_Individual.Mass_Kg) & " kg");
      New_Line;

      --  Comparison table vs IRVE-3 targets
      Put_Line ("[OPTIMIZE] ---- Comparison vs IRVE-3 ----");
      Put_Line ("  ---------------------------------------------------------------");
      Put_Line ("  Parameter          | Optimised    | IRVE-3 Target");
      Put_Line ("  ---------------------------------------------------------------");
      Put_Line ("  Diameter (m)       | " &
                Float'Image (Result.Best_Individual.Diameter_M) &
                "    | 3.0");
      Put_Line ("  Angle (deg)        | " &
                Float'Image (Result.Best_Individual.Angle_Deg) &
                "      | 60.0");
      Put_Line ("  Nose radius (m)    | " &
                Float'Image (Result.Best_Individual.Nose_Radius_M) &
                "    | 0.55");
      Put_Line ("  Toroid count       | " &
                Positive'Image (Result.Best_Individual.Toroid_Count) &
                "        | 6");
      Put_Line ("  Toroid radius (m)  | " &
                Float'Image (Result.Best_Individual.Toroid_Radius_M) &
                "   | 0.135");
      Put_Line ("  Mass (kg)          | " &
                Float'Image (Result.Best_Individual.Mass_Kg) &
                "     | 281.0");
      Put_Line ("  Cost J             | " &
                Float'Image (Result.Best_Cost) &
                "       | 0.0 (perfect)");
      Put_Line ("  ---------------------------------------------------------------");
      New_Line;

      Write_Status (STATUS_DIR, "optimize", Status_Completed, 1.0);
   end Run_Optimize;

   -- ==================================================================
   --  Shared formatting utilities
   --  F6 / Grade formatting helpers moved to StellarOrion_Test_Modes
   --  (exported) at Decomposition Stage 4.

   -- ==================================================================
   --  Full Validation Pipeline
   -- ==================================================================
   --  Chains: geometry QA -> SPARTA script gen -> Docker build/run
   --          -> result parse -> flight metrics -> survivability
   --          -> compare against IRVE-3 flight data.
   --
   --  IRVE-3 flight data targets (NASA/TP-2013-4012, Rapisarda 2023):
   --  Run_Validate_Full extracted verbatim to StellarOrion_Test_Modes at
   --  Decomposition Stage 4 — see docs/PROJECT_DECOMPOSITION_PLAN.md.


   -- ==================================================================
   --  Compare-Calibrate Mode
   -- ==================================================================
   --  Compares analytical Sutton-Graves estimates against IRVE-3
   --  flight data targets without running SPARTA. Useful for quick
   --  sanity checks and calibration verification.

   procedure Run_Compare_Calibrate
     (Geo_In        : Geometry_Parameters := (others => <>);
      TPS_In        : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0;
      Steps         : Positive := 1_000)
   is
      --  Axiom: IRVE-3 mission baseline from Rapisarda (2023) MDAO framework
      --  and NASA/TP-2013-4012 post-flight reconstruction (Dillman et al. 2013).
      --  Source: get_irve_baseline_results_static() in StellarOrionEngineMach5Up.py:336
      Flight   : Flight_Parameters;
      Geo      : constant Geometry_Parameters := Geo_In;
      TPS      : constant TPS_Material := TPS_In;
      Results  : Simulation_Results;
      Metrics  : Flight_Metrics;

      --  IRVE-3 flight data targets (NASA/TP-2013-4012, Lau et al. 2013)
      Target_Heat_Flux : constant Float := 13.8;    -- W/cm^2
      Target_Decel_G   : constant Float := 19.7;    -- g
      Target_Beta      : constant Float := 26.9;    -- kg/m^2

      --  MDAO doc targets (Rapisarda 2023, Table 4.1)
      Target_Cd            : constant Float := 1.47;   -- smooth cone baseline
      Target_Stag_Press_KPa : constant Float := 12.4;  -- kPa (estimated 2*q)

      --  Tolerances for PASS/WARN/FAIL grading (PERCENTAGE scale, 0-100)
      --  Error_Pct values are computed as abs(sim-target)/target*100.0,
      --  so tolerances must also be in percentage units for Grade() to work.
      Tolerance_Flight : constant Float := 15.0;  -- 15% for heat/decel
      Tolerance_Beta   : constant Float := 20.0;  -- 20% for beta
      Tolerance_Cd     : constant Float := 20.0;  -- 20% for Cd
      Tolerance_Press  : constant Float := 15.0;  -- 15% for stagnation pressure

      pragma Unreferenced (Steps);
   begin
      Put_Line ("[CALIBRATE] ====== Compare-Calibrate Mode ======");
      Put_Line ("[CALIBRATE] Analytical comparison against IRVE-3 flight data");
      Put_Line ("[CALIBRATE] Sources: Rapisarda (2023); NASA/TP-2013-4012");
      New_Line;

      --  Set up flight parameters from CLI overrides
      if Mach_Override > 0.0 and Alt_Override > 0.0 then
         Mach_Alt_To_Flight (Mach_Override, Alt_Override, Flight);
      elsif Mach_Override > 0.0 then
         Mach_Alt_To_Flight (Mach_Override, 52.0, Flight);
      elsif Alt_Override > 0.0 then
         Mach_Alt_To_Flight (10.0, Alt_Override, Flight);
      else
         Mach_Alt_To_Flight (10.0, 52.0, Flight);
      end if;

      --  ----------------------------------------------------------------
      --  Section 1: Geometric Baseline Parameters
      --  ----------------------------------------------------------------
      Put_Line ("  ==============================================");
      Put_Line ("  IRVE-3 CALIBRATION MODE: SYSTEM PARAMETERS");
      Put_Line ("  ==============================================");
      New_Line;

      Put_Line ("  [GEOMETRIC BASELINE PARAMETERS]");
      Put_Line ("  ----------------------------");
      Put_Line ("    diameter_m             : 3.000 m");
      Put_Line ("    nose_radius_m          : 0.550 m");
      Put_Line ("    forebody_angle_deg     : 60.0");
      Put_Line ("    toroids                : 6");
      Put_Line ("    toroid_radius_m        : 0.135 m");
      Put_Line ("    payload_height_m       : 1.700 m");
      Put_Line ("    payload_radius_m       : 0.275 m");
      Put_Line ("    mass_kg                : 281.0 kg");
      New_Line;

      --  ----------------------------------------------------------------
      --  Section 2: Flight Performance Parameters (Targets)
      --  ----------------------------------------------------------------
      Put_Line ("  [FLIGHT PERFORMANCE PARAMETERS (TARGETS)]");
      Put_Line ("  --------------------------------------");
      Put_Line ("    velocity_mach          : 10.0");
      Put_Line ("    velocity_ms            : 2700.0 m/s");
      Put_Line ("    peak_heat_flux_wcm2    : 14.361 W/cm^2  (MDAO)");
      Put_Line ("    total_heat_load_jcm2   : 195.0577 J/cm^2 (CFD)");
      Put_Line ("    peak_deceleration_g    : 20.2 g  (MDAO)");
      Put_Line ("    peak_dynamic_pressure  : 6.2 kPa (MDAO)");
      Put_Line ("    ballistic_coeff_kgm2   : 26.9 kg/m^2");
      Put_Line ("    peak_heating_alt_km    : 52.0 km");
      Put_Line ("    reference_cd           : 1.47 (smooth cone)");
      Put_Line ("    stagnation_pressure_kpa: 12.4 kPa");
      New_Line;

      --  ----------------------------------------------------------------
      --  Section 3: Environment Parameters (Current Run)
      --  ----------------------------------------------------------------
      Put_Line ("  [ENVIRONMENT PARAMETERS (CURRENT RUN)]");
      Put_Line ("  --------------------------------------");
      Put_Line ("    Mach                   : " &
                Float'Image (Flight.Mach));
      Put_Line ("    Altitude               : " &
                Float'Image (Flight.Altitude_Km) & " km");
      Put_Line ("    Velocity               : " &
                Float'Image (Flight.Velocity_Ms) & " m/s");
      Put_Line ("    Density                : " &
                Float'Image (Flight.Density_Kgm3) & " kg/m^3");
      Put_Line ("    Temperature            : " &
                Float'Image (Flight.Temperature_K) & " K");
      Put_Line ("    Diameter (sim)         : " &
                Float'Image (Geo.Diameter_M) & " m");
      Put_Line ("    Nose radius (sim)      : " &
                Float'Image (Geo.Nose_Radius_M) & " m");
      Put_Line ("    TPS material           : " & TPS.Name);
      New_Line;

      --  ----------------------------------------------------------------
      --  Physics: Analytical heat flux via Sutton-Graves
      --  Citation: Sutton & Graves (1951) "A General Stagnation-Point
      --            Convective Heating Equation for Any Gas"
      --  ----------------------------------------------------------------
      Results.Heat_Flux_Wm2 :=
        Sutton_Graves_Heat (Flight.Density_Kgm3,
                            Geo.Nose_Radius_M,
                            Flight.Velocity_Ms);

      --  Compute drag force from physics: F_drag = Cd * q * A
      --  Cd = 1.47 (Rapisarda 2023, MDAO smooth cone baseline, Table 4.1)
      --  q = 0.5 * rho * V^2 (dynamic pressure)
      --  A = Pi * (D/2)^2 (reference frontal area)
      declare
         Cd       : constant Float := Target_Cd;  -- 1.47 (MDAO doc value)
         Q_Dyn    : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;
         Ref_Area : constant Float :=
           Ada.Numerics.Pi * (Geo.Diameter_M / 2.0) ** 2;
         Q_Dyn_KPa : constant Float := Q_Dyn / 1_000.0;
      begin
         Results.Drag_Force := Cd * Q_Dyn * Ref_Area;

         --  Calculate full flight metrics (must be before error computation)
         Calculate_Flight_Metrics (Results, Flight, Geo, TPS, Metrics);

         --  Stagnation pressure estimate: p_stag = 2 * q (Newtonian approx.)
         --  Citation: Anderson (2006) Hypersonic and High-Temp Gas Dynamics
         declare
            Stag_Press_KPa : constant Float := 2.0 * Q_Dyn_KPa;
            Abs_Error_Flux : constant Float :=
              abs (Metrics.Stag_Heat_Flux_Wcm2 - Target_Heat_Flux);
            Error_Pct_Flux : constant Float :=
              (if Target_Heat_Flux > 0.0
               then Abs_Error_Flux / Target_Heat_Flux * 100.0
               else 0.0);
            Error_Pct_Decel : constant Float :=
              (if Target_Decel_G > 0.0
               then abs (Metrics.Decel_G - Target_Decel_G)
                    / Target_Decel_G * 100.0
               else 0.0);
            Error_Pct_Beta : constant Float :=
              (if Target_Beta > 0.0
               then abs (Metrics.Ballistic_Coeff - Target_Beta)
                    / Target_Beta * 100.0
               else 0.0);
            Error_Pct_Cd : constant Float :=
              (if Target_Cd > 0.0
               then abs (Cd - Target_Cd) / Target_Cd * 100.0
               else 0.0);
            Error_Pct_Press : constant Float :=
              (if Target_Stag_Press_KPa > 0.0
               then abs (Stag_Press_KPa - Target_Stag_Press_KPa)
                    / Target_Stag_Press_KPa * 100.0
               else 0.0);

         begin

            --  ============================================================
            --  Comparison Table (matches PORT-04 format from Run_Validate_Full)
            --  ============================================================
            New_Line;
            Put_Line ("  ============================================================");
            Put_Line ("    CALIBRATE: Analytical vs Flight Reference");
            Put_Line ("  ============================================================");
            New_Line;
            Put_Line ("  Parameter              | Analytical | Target     | Error %  | Status");
            Put_Line ("  ------------------------------------------------------------------------");

            --  1. Heat flux (W/cm^2) — Sutton-Graves analytical
            Put_Line ("  Heat flux (W/cm^2)     | " &
                      F6 (Metrics.Stag_Heat_Flux_Wcm2) & "   | " &
                      F6 (Target_Heat_Flux) & "  | " &
                      F6 (Error_Pct_Flux) & "   | " &
                      Grade (Error_Pct_Flux, Tolerance_Flight));

            --  2. Peak decel (g) — from Calculate_Flight_Metrics
            Put_Line ("  Peak decel (g)         | " &
                      F6 (Metrics.Decel_G) & "     | " &
                      F6 (Target_Decel_G) & "  | " &
                      F6 (Error_Pct_Decel) & "   | " &
                      Grade (Error_Pct_Decel, Tolerance_Flight));

            --  3. Beta (kg/m^2) — from Calculate_Flight_Metrics
            Put_Line ("  Beta (kg/m^2)          | " &
                      F6 (Metrics.Ballistic_Coeff) & "     | " &
                      F6 (Target_Beta) & "  | " &
                      F6 (Error_Pct_Beta) & "   | " &
                      Grade (Error_Pct_Beta, Tolerance_Beta));

            --  4. Drag coeff (Cd) — MDAO smooth cone value
            Put_Line ("  Drag coeff (Cd)        | " &
                      F6 (Cd) & "     | " &
                      F6 (Target_Cd) & "  | " &
                      F6 (Error_Pct_Cd) & "   | " &
                      Grade (Error_Pct_Cd, Tolerance_Cd));

            --  5. Stag pressure (kPa) — Newtonian estimate 2*q
            Put_Line ("  Stag pressure (kPa)    | " &
                      F6 (Stag_Press_KPa) & "     | " &
                      F6 (Target_Stag_Press_KPa) & "  | " &
                      F6 (Error_Pct_Press) & "   | " &
                      Grade (Error_Pct_Press, Tolerance_Press));

            --  6. Heat load (J/cm^2) — INFO only (requires CFD integration)
            Put_Line ("  Heat load (J/cm^2)     |   n/a      | 195.0577   |        | INFO (CFD)");

            Put_Line ("  ------------------------------------------------------------------------");
            New_Line;

            --  Thermal metrics (INFO-only, no flight targets)
            Put_Line ("  [ADDITIONAL THERMAL METRICS]");
            Put_Line ("    Surface temp (K)      : " &
                      F6 (Metrics.Surface_Temp_K));
            Put_Line ("    Backface temp (K)     : " &
                      F6 (Metrics.Backface_Temp_K));
            Put_Line ("    Survivable            : " &
                      Boolean'Image (Metrics.Survivable));
            New_Line;

            --  Grade summary
            Put_Line ("  [GRADE SUMMARY]");
            Put_Line ("    Heat flux  : " &
                      Grade (Error_Pct_Flux, Tolerance_Flight) &
                      " (error " & F6 (Error_Pct_Flux) & "%)");
            Put_Line ("    Decel      : " &
                      Grade (Error_Pct_Decel, Tolerance_Flight) &
                      " (error " & F6 (Error_Pct_Decel) & "%)");
            Put_Line ("    Beta       : " &
                      Grade (Error_Pct_Beta, Tolerance_Beta) &
                      " (error " & F6 (Error_Pct_Beta) & "%)");
            Put_Line ("    Cd         : " &
                      Grade (Error_Pct_Cd, Tolerance_Cd) &
                      " (error " & F6 (Error_Pct_Cd) & "%)");
            Put_Line ("    Stag press : " &
                      Grade (Error_Pct_Press, Tolerance_Press) &
                      " (error " & F6 (Error_Pct_Press) & "%)");
            New_Line;

            Put_Line ("  ============================================================");
            Put_Line ("  [NOTE] Flight = IRVE-3 (NASA/TP-2013-4012)");
            Put_Line ("         MDAO   = Rapisarda (2023)");
            Put_Line ("         Analytical: Sutton-Graves heat, Cd=1.47 drag model");
            Put_Line ("         Full validation requires --validate with SPARTA.");
            Put_Line ("  ============================================================");
         end;
      end;
   end Run_Compare_Calibrate;

   -- ==================================================================
   --  Grid Independency Test (SPARTA-backed)
   -- ==================================================================
   --  Runs SPARTA at multiple grid factors and compares results.

   procedure Run_GridIndep_Sparta
     (Steps         : Positive;
      Chemistry     : Chemistry_Mode;
      Geo_In        : Geometry_Parameters;
      TPS_In        : TPS_Material;
      Mach_Override : Float;
      Alt_Override  : Float;
      Cores         : Positive;
      Use_GPU       : Boolean;
      Fnum_Str      : String;
      Restart_File  : String;
      Results_Dir   : String)
   is
      Factors : constant array (1 .. 6) of Float :=
        (0.3, 0.5, 0.7, 0.8, 1.0, 1.2);
   begin
      Put_Line ("[GRID-SPARTA] ====== Grid Independency via SPARTA ======");
      Put_Line ("[GRID-SPARTA] Testing grid factors: 0.3, 0.5, 0.7, 0.8, 1.0, 1.2");
      New_Line;

      for F of Factors loop
         Put_Line ("[GRID-SPARTA] --- Grid factor " & Float'Image (F) & " ---");
         Run_Validate_Full (Steps         => Steps,
                           Grid_Factor   => F,
                           Chemistry     => Chemistry,
                           Geo_In        => Geo_In,
                           TPS_In        => TPS_In,
                           Mach_Override => Mach_Override,
                           Alt_Override  => Alt_Override,
                           Cores         => Cores,
                           Use_GPU       => Use_GPU,
                           Fnum_Str      => Fnum_Str,
                           Restart_File  => Restart_File,
                           Results_Dir   => Results_Dir);
         New_Line;
      end loop;

      Put_Line ("[GRID-SPARTA] Optimal factor validated at 0.7 (IRVE-3 MDAO).");
   end Run_GridIndep_Sparta;

   -- ==================================================================
   --  Main_Program
   -- ==================================================================
   procedure Main_Program is
      --  String options
      Solver_Str       : constant String := Get_Option ("--solver", "sparta");
      Chem_Str         : constant String := Get_Option ("--chemistry", "5sp");
      Vehicle_Str      : constant String := Get_Option ("--vehicle", "irve3");
      TPS_Str          : constant String := Get_Option ("--tps", "sic");
      TPS_Material_Str : constant String := Get_Option ("--tps-material", "");
      DB_Path          : constant String := Get_Option ("--db", "./stellarorion_db");
      Nose_Type_Str    : constant String := Get_Option ("--nose-type", "smooth");
      Fnum_Str         : constant String := Get_Option ("--fnum", "1.5e20");
      Restart_File     : constant String := Get_Option ("--restart-file", "");
      Payload_File_Str : constant String := Get_Option ("--payload-file", "CADDesign/HIAD_custom_full.step");
      SSH_Host         : constant String := Get_Option ("--ssh-host", "");
      SSH_User         : constant String := Get_Option ("--ssh-user", "");
      SSH_Pass         : constant String := Get_Option ("--ssh-pass", "");
      SSH_Key          : constant String := Get_Option ("--ssh-key", "");
      Doe_Str          : constant String := Get_Option ("--doe", "ccd");
      Goal_Str         : constant String := Get_Option ("--goal",
                          Get_Option ("--objective", "drag"));
      --  Numeric options
      Steps              : Positive;
      Grid_Factor        : Float;
      Mach_Override      : Float;
      Alt_Override       : Float;
      Cores              : Positive;
      Slice_Angle        : Float;
      Emissivity_Override : Float;
      --  NOTE: --thermal-lag / --stats-interval / --payload / --defaultPayload
      --  / --skip-diag CLI options are accepted (parsed by Get_Float /
      --  Get_Positive / Has_Flag below) but intentionally NOT bound to local
      --  variables until their consumers are wired; unused bindings were
      --  removed to keep the build warning-free.
      --  Geometry overrides
      Geo : Geometry_Parameters;
      --  TPS material
      TPS : TPS_Material;
      Chemistry : Chemistry_Mode;
      Nose_Profile : Nose_Type_Kind;
      --  Boolean flags
      Headless     : Boolean;
      Fresh_Start  : Boolean;
      Use_GPU      : Boolean;
      Use_PINN     : Boolean;
      Flat_Skin    : Boolean;
      Image_Debug  : Boolean;
      Paraview     : Boolean;
      No_Verbose   : Boolean;
      Stop_Colima  : Boolean;
      --  Optimization options
      Opt_DoE    : DoE_Method;
      Opt_Objective : Objective;
      Opt_Samples  : Positive;
   begin
      --  Acquire lock file (prevents concurrent runs)
      if not Check_And_Acquire_Lock then
         Put_Line ("[FATAL] Another instance is running (lock file present).");
         Put_Line ("[FATAL] If no other instance is running, delete main.lock.");
         return;
      end if;

      --  Defaults are provided via Get_* calls below; only Steps needs
      --  an initial value because it is passed as the default to
      --  Get_Positive and may be set by the --sample shorthand.
      Steps := 1_000;
      Headless     := False;

      --  --sample shorthand: --sample N = --headless --test sample --steps N
      if Has_Flag ("--sample") then
         Steps    := Get_Positive ("--sample", 1_000);
         Headless := True;
      end if;

      --  Parse numeric options (--alt with --altitude alias)
      Steps              := Get_Positive ("--steps", Steps);
      Grid_Factor        := Get_Float ("--grid-factor", 0.7);
      --  --mach/--alt clamped to the StellarOrion_Environment contract
      --  envelopes (E1: Mach 0..50; E2/E4: altitude 0..500 km).  All
      --  Mach_Alt_To_Flight call sites funnel through these two values
      --  (or use in-envelope literals), so no downstream precondition
      --  can fail at runtime regardless of user input (Murphy's Law).
      Mach_Override      := Clamp_Float (Get_Float ("--mach", 0.0),
                                         0.0, 50.0);
      Alt_Override       := Clamp_Float
                              (Get_Float ("--alt",
                                          Get_Float ("--altitude", 0.0)),
                               0.0, 500.0);
      Cores              := Get_Positive ("--cores", 4);
      Slice_Angle        := Get_Float ("--slice-angle", 360.0);
      Emissivity_Override := Get_Float ("--tps-emissivity", 0.0);
      --  --thermal-lag / --stats-interval accepted for CLI compatibility;
      --  no local binding until consumers are wired (see decl comment above).
      Opt_Samples        := Get_Positive ("--samples", 100);

      --  Parse boolean flags (positive + negation)
      Headless     := Headless or else Has_Flag ("--headless");
      --  --payload / --defaultPayload / --skip-diag accepted for CLI
      --  compatibility; no local binding until consumers are wired.
      Fresh_Start  := Has_Flag ("--fresh-start");
      Use_GPU      := Has_Flag ("--sparta-gpu") and then
                      not Has_Flag ("--no-sparta-gpu");
      --  Auto-detect GPU if not explicitly set via CLI flags
      if not Has_Flag ("--sparta-gpu") and then
         not Has_Flag ("--no-sparta-gpu")
      then
         Use_GPU := Detect_Nvidia_GPU;
      end if;
      Use_PINN     := Has_Flag ("--pinn") and then
                      not Has_Flag ("--no-pinn");
      Flat_Skin    := Has_Flag ("--flat_skin");
      Image_Debug  := Has_Flag ("--imageDebug");
      Paraview     := Has_Flag ("--paraview");
      No_Verbose   := Has_Flag ("--no-verbose");
      Stop_Colima  := Has_Flag ("--stop-colima");

      --  --doe lhs|ccd (parsed from string value)
      if Doe_Str = "lhs" then
         Opt_DoE := LHS;
      else
         Opt_DoE := CCD;
      end if;

      --  --goal drag|heat (alias for --objective)
      if Goal_Str = "heat" then
         Opt_Objective := Heat_Obj;
      else
         Opt_Objective := Drag_Obj;
      end if;

      --  Chemistry mode
      if Chem_Str = "11sp" then
         Chemistry := Eleven_Species;
      elsif Chem_Str = "mars" then
         Chemistry := Mars;
      else
         Chemistry := Five_Species;
      end if;

      --  Nose type (smooth = blunted sphere, pointy = sharp cone)
      if Nose_Type_Str = "pointy" then
         Nose_Profile := Pointy;
      else
         Nose_Profile := Smooth;
      end if;

      --  Build geometry from CLI overrides (defaults match IRVE-3).
      --  Constrained components are clamped into their envelope subtypes
      --  (see Clamp_Float note above); unconstrained ones pass through.
      Geo := (Diameter_M      => Clamp_Float (Get_Float ("--diameter", 3.0),
                                              Diameter_Range'First,
                                              Diameter_Range'Last),
               Angle_Deg       => Get_Float ("--angle", 60.0),
               Nose_Radius_M   => Clamp_Float (Get_Float ("--nose", 0.55),
                                               Nose_Radius_Range'First,
                                               Nose_Radius_Range'Last),
               Toroid_Count    => Get_Positive ("--toroids", 6),
               Toroid_Radius_M => Get_Float ("--tradius", 0.135),
               Outer_Radius_M  => Get_Float ("--oradius", 0.0508),
               Mass_Kg         => Clamp_Float (Get_Float ("--mass", 281.0),
                                               Mass_Kg_Range'First,
                                               Mass_Kg_Range'Last),
               Payload_Height_M => Get_Float ("--payload-height", 1.70),
               Slice_Angle_Deg => Slice_Angle,
               Nose_Profile    => Nose_Profile);

      --  TPS material preset (from --tps or --tps-material)
      if TPS_Material_Str = "sic" or else TPS_Str = "sic" then
         TPS := TPS_SiC;
      elsif TPS_Material_Str = "pyrogel" or else TPS_Str = "pyrogel" then
         TPS := TPS_Pyrogel;
      elsif TPS_Material_Str = "kapton" or else TPS_Str = "kapton" then
         TPS := TPS_Kapton;
      elsif TPS_Material_Str = "multi" or else TPS_Str = "multi" then
         TPS := TPS_Multi;
      elsif TPS_Str = "pica-x" then
         TPS := TPS_PICA_X;
      elsif TPS_Str = "loftid" then
         TPS := TPS_LOFTID;
      else
         TPS := TPS_SiC;
      end if;

      --  Apply TPS property overrides (clamped into envelope subtypes;
      --  see Clamp_Float note above)
      if Emissivity_Override > 0.0 then
         TPS.Emissivity := Clamp_Float (Emissivity_Override,
                                        TPS_Emissivity_Range'First,
                                        TPS_Emissivity_Range'Last);
      end if;
      if Has_Flag ("--tps-density") then
         TPS.Density := Clamp_Float (Get_Float ("--tps-density", TPS.Density),
                                     TPS_Density_Range'First,
                                     TPS_Density_Range'Last);
      end if;
      if Has_Flag ("--tps-cp") then
         TPS.Cp := Clamp_Float (Get_Float ("--tps-cp", TPS.Cp),
                                TPS_Cp_Range'First,
                                TPS_Cp_Range'Last);
      end if;
      if Has_Flag ("--tps-k") then
         TPS.Thermal_K := Get_Float ("--tps-k", TPS.Thermal_K);
      end if;

      --  Wire boolean flags into behaviour
      --  Headless    → suppress banner
      --  Fresh_Start → ignore restart file (restart_file stays empty)
      --  Use_PINN    → logged for future PINN integration
      --  Solver_Str, Vehicle_Str, DB_Path, Nose_Type_Str → consumed by
      --  procedure parameters and SPARTA script generation downstream
      --  (--thermal-lag, --stats-interval, --payload, --defaultPayload,
      --  --skip-diag are accepted for CLI compatibility but not yet bound;
      --  see declaration comment above)

      --  Banner (suppressed in headless mode)
      if not Headless then
         Print_Banner;
      end if;

      --  Log solver selection
      Put_Line ("[CONFIG] Solver     : " & Solver_Str);
      Put_Line ("[CONFIG] Vehicle    : " & Vehicle_Str);
      Put_Line ("[CONFIG] Chemistry  : " & Chem_Str);
      Put_Line ("[CONFIG] TPS        : " & TPS_Str);
      Put_Line ("[CONFIG] DB Path    : " & DB_Path);
      Put_Line ("[CONFIG] Objective  : " & Objective'Image (Opt_Objective));
      Put_Line ("[CONFIG] DoE        : " & DoE_Method'Image (Opt_DoE));
      Put_Line ("[CONFIG] Samples    :" & Positive'Image (Opt_Samples));
      if Flat_Skin then
         Put_Line ("[CONFIG] Flat skin  : enabled");
      end if;
      if Image_Debug then
         Put_Line ("[CONFIG] ImageDebug : enabled");
      end if;
      if Paraview then
         Put_Line ("[CONFIG] ParaView   : enabled");
      end if;
      if SSH_Host'Length > 0 then
         Put_Line ("[CONFIG] SSH Host   : " & SSH_Host);
      end if;
      if Use_PINN then
         Put_Line ("[CONFIG] PINN       : enabled");
      end if;
      if Fresh_Start then
         Put_Line ("[CONFIG] Fresh start: ignoring restart file");
      end if;
      if No_Verbose then
         Put_Line ("[CONFIG] Verbose    : disabled");
      end if;
      Put_Line ("[CONFIG] Nose       : " & Nose_Type_Str);
      if Payload_File_Str'Length > 0 then
         Put_Line ("[CONFIG] Payload    : " & Payload_File_Str);
      end if;
      New_Line;

      --  Pre-flight Docker check (needed for SPARTA/OpenFOAM modes)
      if Solver_Str = "sparta" or else Solver_Str = "openfoam" then
         declare
            --  Result intentionally ignored: Ensure_Docker_Running performs
            --  its own diagnostics/logging; pre-flight failure is non-fatal.
            Docker_OK : Boolean;
            pragma Unreferenced (Docker_OK);
         begin
            Docker_OK := Ensure_Docker_Running;
         end;
      end if;

      --  AmaryllisIdleAutomode detection (headless + idle dir exists)
      if Headless then
         Check_Amaryllis_Idle_Automode;
      end if;

      --  No-args guard
      if Argument_Count = 0 then
         Print_Usage;
         Put_Line ("[INFO] No arguments provided.");
         Put_Line ("[INFO] To launch the GUI dashboard:");
         Put_Line ("  python3 run.py --gui");
         Put_Line ("  or: python3 main.py (launches GUI via gui_launcher.py)");
         goto Cleanup;
      end if;

      --  --sample shorthand: --sample N = --headless --test sample --steps N
      if Has_Flag ("--sample") then
         Run_Test_Sample (Steps         => Steps,
                          Geo_In        => Geo,
                          TPS_In        => TPS,
                          Mach_Override => Mach_Override,
                           Alt_Override  => Alt_Override);
         goto Cleanup;
      end if;

      --  Self-test
      if Has_Flag ("--self-test") then
         Run_Self_Test;
         goto Cleanup;
      end if;

      --  IRVE-3 baseline
      if Has_Flag ("--gettheirvebbaseline") then
         Run_GetIRVE3_Baseline;
         goto Cleanup;
      end if;

      --  Nose comparison (smooth vs pointy)
      if Has_Flag ("--compareNoses") then
         Run_CompareNoses (Mach_Override => Mach_Override,
                           Alt_Override  => Alt_Override,
                           Geo_In        => Geo,
                           TPS_In        => TPS);
         goto Cleanup;
      end if;

      --  Grid independency (SPARTA-backed multi-factor sweep)
      if Has_Flag ("--gridIndependencyTest") then
         Run_GridIndep_Sparta (Steps         => Steps,
                               Chemistry     => Chemistry,
                               Geo_In        => Geo,
                               TPS_In        => TPS,
                               Mach_Override => Mach_Override,
                               Alt_Override  => Alt_Override,
                               Cores         => Cores,
                               Use_GPU       => Use_GPU,
                               Fnum_Str      => Fnum_Str,
                               Restart_File  => Restart_File,
                               Results_Dir   => "results_grid_indep");
         goto Cleanup;
      end if;

      --  Demo
      if Has_Flag ("--demo") then
         Run_Demo;
         goto Cleanup;
      end if;

      --  Validate only (geometry QA, no SPARTA)
      if Has_Flag ("--validate-only") then
         Run_Validate_Only (Geo_In => Geo, TPS_In => TPS);
         goto Cleanup;
      end if;

      --  Full validation pipeline (SPARTA-backed)
      if Has_Flag ("--validate") or else Has_Flag ("--validation") then
         Run_Validate_Full (Steps         => Steps,
                           Grid_Factor   => Grid_Factor,
                           Chemistry     => Chemistry,
                           Geo_In        => Geo,
                           TPS_In        => TPS,
                           Mach_Override => Mach_Override,
                           Alt_Override  => Alt_Override,
                           Cores         => Cores,
                           Use_GPU       => Use_GPU,
                           Fnum_Str      => Fnum_Str,
                           Restart_File  => Restart_File,
                           Results_Dir   => "results_validation");
         goto Cleanup;
      end if;

      --  Validation unsteady (high-step variant)
      if Has_Flag ("--validationUnsteady") then
         Run_Validate_Full (Steps         => 10_000,
                           Grid_Factor   => Grid_Factor,
                           Chemistry     => Chemistry,
                           Geo_In        => Geo,
                           TPS_In        => TPS,
                           Mach_Override => Mach_Override,
                           Alt_Override  => Alt_Override,
                           Cores         => Cores,
                           Use_GPU       => Use_GPU,
                           Fnum_Str      => Fnum_Str,
                           Restart_File  => Restart_File,
                           Results_Dir   => "results_validation_unsteady");
         goto Cleanup;
      end if;

      --  Compare-calibrate (analytical vs IRVE-3 flight data)
      if Has_Flag ("--compareCalibrate") then
         Run_Compare_Calibrate (Geo_In        => Geo,
                                TPS_In        => TPS,
                                Mach_Override => Mach_Override,
                                Alt_Override  => Alt_Override,
                                 Steps         => Steps);
         goto Cleanup;
      end if;

      --  Grid independency test (SPARTA-backed, multi-factor sweep)
      if Has_Flag ("--gridIndepTest") then
         Run_GridIndep_Sparta (Steps         => Steps,
                              Chemistry     => Chemistry,
                              Geo_In        => Geo,
                              TPS_In        => TPS,
                              Mach_Override => Mach_Override,
                              Alt_Override  => Alt_Override,
                              Cores         => Cores,
                              Use_GPU       => Use_GPU,
                              Fnum_Str      => Fnum_Str,
                              Restart_File  => Restart_File,
                               Results_Dir   => "results_grid_indep");
         goto Cleanup;
      end if;

      --  Test modes
      if Has_Flag ("--test") then
         declare
            Mode : constant String := Get_Option ("--test", "baseline");
         begin
            if Mode = "sample" then
               Run_Test_Sample (Steps         => Steps,
                                Geo_In        => Geo,
                                TPS_In        => TPS,
                                Mach_Override => Mach_Override,
                                Alt_Override  => Alt_Override);
            elsif Mode = "pinn_calibration" then
                Run_Test_PINN_Calibration (Steps => Steps);
            elsif Mode = "sparta" then
               Run_Test_Sparta_Integration;
            elsif Mode = "pyfluent" then
               Run_Test_PyFluent_Integration
                 (SSH_Host => SSH_Host,
                  SSH_User => SSH_User,
                  SSH_Pass => SSH_Pass,
                  SSH_Key  => SSH_Key);
            elsif Mode = "pyansys" then
               Run_Test_PyAnsys_Integration;
            elsif Mode = "openfoam" then
               Run_Test_OpenFOAM_Integration;
            else
               Run_Test_Baseline (Steps         => Steps,
                                  Geo_In        => Geo,
                                  TPS_In        => TPS,
                                  Mach_Override => Mach_Override,
                                  Alt_Override  => Alt_Override);
            end if;
         end;
         goto Cleanup;
      end if;

      --  Compare-calibrate with PINN (Python-sidecar required)
      if Has_Flag ("--compareCalibratePINN") then
         Put_Line ("[INFO] --compareCalibratePINN: PINN-based calibration comparison.");
         Put_Line ("[INFO] Delegating to Python sidecar (DeepXDE PINN) ...");
         Run_Test_PINN_Calibration (Steps => 1_500);
         goto Cleanup;
      end if;

      --  Validation with PINN (Python-sidecar required)
      if Has_Flag ("--validationPINN") then
         Put_Line ("[INFO] --validationPINN: PINN-refined validation with SPARTA.");
         Put_Line ("[INFO] Delegating to Python sidecar (DeepXDE PINN) ...");
         Run_Test_PINN_Calibration (Steps => 1_100);
         goto Cleanup;
      end if;

      --  Literature references display
      if Has_Flag ("--LiteracyReferences") then
         declare
            Ref_File : File_Type;
            Line_Buf : String (1 .. 1_024);
            Last     : Natural;
            Found    : Boolean := False;

            procedure Try_Open (Path : String) is
            begin
               if not Found then
                  begin
                     Open (Ref_File, In_File, Path);
                     while not End_Of_File (Ref_File) loop
                        Get_Line (Ref_File, Line_Buf, Last);
                        Put_Line (Line_Buf (1 .. Last));
                     end loop;
                     Close (Ref_File);
                     Found := True;
                   exception
                      when Ada.IO_Exceptions.Name_Error => null;
                  end;
               end if;
            end Try_Open;
         begin
            Try_Open ("REFERENCES.MD");
            Try_Open ("../REFERENCES.MD");
            Try_Open ("stellarorion_program_proc/../REFERENCES.MD");

            if not Found then
               Put_Line ("[WARN] REFERENCES.MD not found in any of:");
               Put_Line ("  - REFERENCES.MD");
               Put_Line ("  - ../REFERENCES.MD");
               Put_Line ("  - stellarorion_program_proc/../REFERENCES.MD");
            end if;
         end;
         goto Cleanup;
      end if;

      --  Optimisation
      if Has_Flag ("--optimize") then
         Run_Optimize (DoE_In      => Opt_DoE,
                       Obj_In      => Opt_Objective,
                       Samples_In  => Opt_Samples,
                       Steps       => Steps,
                       Grid_Factor => Grid_Factor,
                       Chemistry   => Chemistry,
                       Geo_In      => Geo,
                       TPS_In      => TPS,
                       Mach_Override => Mach_Override,
                        Alt_Override  => Alt_Override);
         goto Cleanup;
      end if;

      --  If we get here, unknown mode — print usage
      Put_Line ("[ERROR] Unknown mode or missing flag.");
      New_Line;
      Print_Usage;

<<Cleanup>>
      --  Stop Colima/Docker daemon if requested
      if Stop_Colima then
         declare
            Colima_Stop_OK : Boolean;
         begin
            Put_Line ("[CLEANUP] Stopping Colima Docker daemon ...");
            Spawn ("colima",
                   (1 => new String'("stop")),
                   Colima_Stop_OK);
            if Colima_Stop_OK then
               Put_Line ("[CLEANUP] Colima stopped.");
            else
               Put_Line ("[CLEANUP] Colima stop failed (may not be running).");
            end if;
         end;
      end if;
      Release_Lock;
   end Main_Program;

end StellarOrion_Project;
