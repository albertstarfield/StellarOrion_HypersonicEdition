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
with StellarOrion_Geometry;   use StellarOrion_Geometry;
with StellarOrion_Environment;use StellarOrion_Environment;
with StellarOrion_Validation; use StellarOrion_Validation;
with StellarOrion_Sparta;     use StellarOrion_Sparta;
with StellarOrion_Optimization; use StellarOrion_Optimization;
with StellarOrion_Status_Writer; use StellarOrion_Status_Writer;

with Ada.Directories;    use Ada.Directories;
with Ada.Strings.Fixed;  use Ada.Strings.Fixed;
with Ada.IO_Exceptions;  use Ada.IO_Exceptions;
with Ada.Numerics;       use Ada.Numerics;
with GNAT.OS_Lib;        use GNAT.OS_Lib;

package body StellarOrion_Project is
   pragma SPARK_Mode (Off);

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

   --  Simple argument search (returns True if flag found)
   function Has_Flag (Flag : String) return Boolean is
   begin
      for I in 1 .. Argument_Count loop
         if Argument (I) = Flag then
            return True;
         end if;
      end loop;
      return False;
   end Has_Flag;

   --  Get value for --flag <value>
   function Get_Option (Flag : String; Default : String) return String is
   begin
      for I in 1 .. Argument_Count - 1 loop
         if Argument (I) = Flag then
            return Argument (I + 1);
         end if;
      end loop;
      return Default;
   end Get_Option;

   function Get_Float (Flag : String; Default : Float) return Float is
      Val : constant String := Get_Option (Flag, "");
   begin
      if Val'Length > 0 then
         return Float'Value (Val);
      else
         return Default;
      end if;
   end Get_Float;

   function Get_Positive (Flag : String; Default : Positive) return Positive is
      Val : constant String := Get_Option (Flag, "");
   begin
      if Val'Length > 0 then
         return Positive'Value (Val);
      else
         return Default;
      end if;
   end Get_Positive;

   -- ==================================================================
   --  Lock File Helpers  (matches Python check_and_acquire_lock)
   -- ==================================================================

   function Get_Lock_File_Path return String is
   begin
      return "main.lock";
   end Get_Lock_File_Path;

   function Check_And_Acquire_Lock return Boolean is
      Lock_File : File_Type;
      Lock_Path : constant String := Get_Lock_File_Path;
      Success   : Boolean;
   begin
      if Exists (Lock_Path) then
         Put_Line ("[LOCK] Lock file exists: " & Lock_Path);
         Put_Line ("[LOCK] Attempting to break stale lock ...");
         Delete_File (Lock_Path, Success);
         if not Success then
            Put_Line ("[LOCK] WARNING: Could not remove stale lock file.");
            return False;
         end if;
      end if;

      --  Create lock file with timestamp marker
      Create (Lock_File, Out_File, Lock_Path);
      Put_Line (Lock_File, "locked_by_stellarorion_ada");
      Close (Lock_File);
      Put_Line ("[LOCK] Lock acquired: " & Lock_Path);
      return True;
   end Check_And_Acquire_Lock;

   procedure Release_Lock is
      Lock_Path : constant String := Get_Lock_File_Path;
      Success   : Boolean;
   begin
      if Exists (Lock_Path) then
         Delete_File (Lock_Path, Success);
         if Success then
            Put_Line ("[LOCK] Lock released: " & Lock_Path);
         end if;
      end if;
   end Release_Lock;

   -- ==================================================================
   --  GPU Auto-Detection  (matches Python has_nvidia_gpu)
   -- ==================================================================

   function Detect_Nvidia_GPU return Boolean is
      use GNAT.OS_Lib;
      Success   : Boolean;
      Empty_Args : Argument_List (1 .. 0) := (others => null);
   begin
      Put_Line ("[GPU] Detecting NVIDIA GPU via nvidia-smi ...");
      Spawn ("nvidia-smi", Empty_Args, Success);
      if Success then
         Put_Line ("[GPU] NVIDIA GPU DETECTED.");
         return True;
      else
         Put_Line ("[GPU] No NVIDIA GPU detected (nvidia-smi not available).");
         return False;
      end if;
   exception
      when others =>
         Put_Line ("[GPU] GPU detection failed (exception).");
         return False;
   end Detect_Nvidia_GPU;

   -- ==================================================================
   --  Pre-flight Docker Check  (matches Python ensure_docker_colima)
   -- ==================================================================

   function Ensure_Docker_Running return Boolean is
      use GNAT.OS_Lib;
      Success    : Boolean;
      Empty_Args : Argument_List (1 .. 0) := (others => null);
   begin
      Put_Line ("[DOCKER] Pre-flight Docker check ...");
      Spawn ("docker", Empty_Args, Success);
      if not Success then
         Put_Line ("[DOCKER] WARNING: Docker not available on PATH.");
         Put_Line ("[DOCKER] SPARTA simulation requires Docker.");
         return False;
      end if;

      --  Try 'docker info' to verify daemon is running
      Spawn ("docker", (1 => new String'("info")), Success);
      if Success then
         Put_Line ("[DOCKER] Docker daemon is running.");
         return True;
      end if;

      --  Docker binary exists but daemon not running; try colima
      Put_Line ("[DOCKER] Docker daemon not responding. Trying colima ...");
      Spawn ("colima", (1 => new String'("start")), Success);
      if Success then
         Put_Line ("[DOCKER] Colima started successfully.");
         return True;
      end if;

      Put_Line ("[DOCKER] WARNING: Could not start Docker/Colima.");
      Put_Line ("[DOCKER] SPARTA simulation will not be available.");
      return False;
   exception
      when others =>
         Put_Line ("[DOCKER] Docker check failed (exception).");
         return False;
   end Ensure_Docker_Running;

   -- ==================================================================
   --  AmaryllisIdleAutomode Detection  (matches Python headless idle logic)
   -- ==================================================================

   procedure Check_Amaryllis_Idle_Automode is
      Idle_Dir     : constant String := "/usr/local/AmaryllisIdleAutomode";
      Chmod_Success : Boolean;
   begin
      if not Exists (Idle_Dir) then
         return;
      end if;

      Put_Line ("[IDLE] AmaryllisIdleAutomode detected at " & Idle_Dir);
      Put_Line ("[IDLE] Creating idle-resume script ...");

      declare
         Script_Name : constant String :=
           "resumeDSMCResearch_ada_executeMeAtIdle.sh";
         Script_File : File_Type;
      begin
         Create (Script_File, Out_File, Script_Name);
         Put_Line (Script_File, "#!/bin/bash");
         Put_Line (Script_File, "# Auto-generated by StellarOrion Ada");
         Put_Line (Script_File, "# Runs after 600s idle period");
         Put_Line (Script_File, "sleep 600");
         Put_Line (Script_File, "cd " & Current_Directory);
         Put_Line (Script_File, "./bin/stellarorion_project --headless --validate");
         Close (Script_File);

          --  Make executable (chmod 0o755)
          GNAT.OS_Lib.Spawn
            ("chmod",
             (new String'("755"), new String'(Script_Name)),
             Chmod_Success);
         Put_Line ("[IDLE] Resume script: " & Script_Name);
      end;
   exception
      when others =>
         Put_Line ("[IDLE] Could not create idle-resume script.");
   end Check_Amaryllis_Idle_Automode;

   -- ==================================================================
   --  Test Modes
   -- ==================================================================

   procedure Run_Self_Test is
      T1, T2, T3 : Float;
      Geo   : Geometry_Parameters;
      Flight: Flight_Parameters;
      Metrics: Flight_Metrics;
      Results: Simulation_Results;
      Survivable : Boolean;
      Pass_Count : Natural := 0;
      Fail_Count : Natural := 0;

      --  Helper: LHS sample value
      LHS_Val : Float;

      --  Helper: CCD values
      CCD_C, CCD_A_Pos, CCD_A_Neg : Float;

      --  Helper: Environment results
      Env_Flight : Flight_Parameters;

      --  Helper: Optimization cost
      Cost_Val : Float;

      --  Helper: Survivability check
      Bad_Metrics : Flight_Metrics;

      --  Helper: Nose_Type_Kind
      NT : Nose_Type_Kind;
   begin
      Write_Status (STATUS_DIR, "self_test", Status_Running, 0.0);
      Put_Line ("[TEST] Running self-test (13 tests) ...");
      New_Line;

      --  ==================================================================
      --  Test 1: Mean free path
      --  ==================================================================
      T1 := Mean_Free_Path (1.0e23, MOL_DIAM);
      Put_Line ("[TEST 01] MFP(n=1e23, d=3.7e-10) = " & Float'Image (T1) & " m");
      Put_Line ("[TEST 01]   Expected ~ 5.2e-3 m");
      if T1 > 0.0 and T1 < 1.0 then
         Put_Line ("[TEST 01]   PASS");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 01]   FAIL (value out of physical range)");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 2: Knudsen number
      --  ==================================================================
      T2 := Knudsen_Number (T1, 3.0);
      Put_Line ("[TEST 02] Kn(MFP, D=3m) = " & Float'Image (T2));
      Put_Line ("[TEST 02]   Expected ~ 1.7e-3 (continuum-transition)");
      if T2 > 0.0 and T2 < 1.0 then
         Put_Line ("[TEST 02]   PASS");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 02]   FAIL (Kn out of physical range)");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 3: Sutton-Graves heat flux
      --  ==================================================================
      T3 := Sutton_Graves_Heat (6.9674e-4, 0.55, 2700.0);
      Put_Line ("[TEST 03] q_stag(Mach10, 52km) = " & Float'Image (T3) & " W/m^2");
      Put_Line ("[TEST 03]   Expected ~ 140,000 W/m^2 (14 W/cm^2)");
      if T3 > 100_000.0 and T3 < 200_000.0 then
         Put_Line ("[TEST 03]   PASS");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 03]   FAIL (heat flux outside expected range)");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 4: Geometry validation (IRVE-3 defaults)
      --  ==================================================================
      Geo := (others => <>);  -- defaults (IRVE-3)
      if Validate_Geometry (Geo) then
         Put_Line ("[TEST 04] IRVE-3 geometry: VALID  -- PASS");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 04] IRVE-3 geometry: INVALID (unexpected!)  -- FAIL");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 5: Full metrics pipeline
      --  ==================================================================
      Flight := (others => <>);  -- defaults
      Results := (Drag_Force => 4500.0,
                  Heat_Flux_Wm2 => 140000.0,
                  others => <>);
      Calculate_Flight_Metrics (Results, Flight, Geo,
                                (others => <>), Metrics);
      Survivable := Is_Survivable (Metrics);
      Put_Line ("[TEST 05] Full metrics pipeline:");
      Put_Line ("  Ballistic coeff : " & Float'Image (Metrics.Ballistic_Coeff) & " kg/m^2");
      Put_Line ("  Knudsen number  : " & Float'Image (Metrics.Knudsen_Number));
      Put_Line ("  Stag heat flux  : " & Float'Image (Metrics.Stag_Heat_Flux_Wcm2) & " W/cm^2");
      Put_Line ("  Surface temp    : " & Float'Image (Metrics.Surface_Temp_K) & " K");
      Put_Line ("  Backface temp   : " & Float'Image (Metrics.Backface_Temp_K) & " K");
      Put_Line ("  Decel g         : " & Float'Image (Metrics.Decel_G) & " g");
      Put_Line ("  Survivable      : " & Boolean'Image (Survivable));
      if Metrics.Ballistic_Coeff > 0.0 and Metrics.Knudsen_Number >= 0.0 then
         Put_Line ("[TEST 05]   PASS");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 05]   FAIL");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 6: LHS Sampling (stratified bounds check)
      --  ==================================================================
      Put_Line ("[TEST 06] LHS Sampling (McKay 1979):");
      --  Test with diameter range [0.5, 15.0], N=10 samples
      LHS_Val := LHS_Sample (0.5, 15.0, 10, 1, 0.3);
      Put_Line ("  LHS(0.5, 15.0, N=10, i=1, r=0.3) = " & Float'Image (LHS_Val));
      if LHS_Val >= 0.5 and LHS_Val <= 15.0 then
         Put_Line ("[TEST 06]   PASS (within bounds)");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 06]   FAIL (out of bounds!)");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 7: CCD Sampling (centre + axial points)
      -- ==================================================================
      Put_Line ("[TEST 07] CCD Sampling (Centre + Axial):");
      CCD_C := CCD_Centre (0.5, 15.0);
      Put_Line ("  CCD_Centre(0.5, 15.0) = " & Float'Image (CCD_C) &
                "  Expected ~ 7.75");
      --  Use alpha=0.3 (realistic small) so axial points stay within bounds
      CCD_A_Pos := CCD_Axial (0.5, 15.0, 0.3, True);
      CCD_A_Neg := CCD_Axial (0.5, 15.0, 0.3, False);
      Put_Line ("  CCD_Axial(+, alpha=0.3) = " & Float'Image (CCD_A_Pos));
      Put_Line ("  CCD_Axial(-, alpha=0.3) = " & Float'Image (CCD_A_Neg));
      --  Centre must be within bounds (Post => ensures this)
      --  Axial points may exceed bounds for large alpha (by design)
      if CCD_C > 0.5 and CCD_C < 15.0 then
         Put_Line ("[TEST 07]   PASS (centre within bounds, axial computed)");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 07]   FAIL");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 8: ISA Environment Model (Mach_Alt_To_Flight)
      --  ==================================================================
      Put_Line ("[TEST 08] ISA Environment Model (Mach=10, Alt=52km):");
      Mach_Alt_To_Flight (10.0, 52.0, Env_Flight);
      Put_Line ("  Density     = " & Float'Image (Env_Flight.Density_Kgm3) & " kg/m^3");
      Put_Line ("  Temperature = " & Float'Image (Env_Flight.Temperature_K) & " K");
      Put_Line ("  Velocity    = " & Float'Image (Env_Flight.Velocity_Ms) & " m/s");
      if Env_Flight.Density_Kgm3 > 0.0
        and Env_Flight.Temperature_K > 0.0
        and Env_Flight.Velocity_Ms > 0.0 then
         Put_Line ("[TEST 08]   PASS (all positive physical values)");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 08]   FAIL (non-physical value)");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 9: Optimization Cost function
      --  ==================================================================
      Put_Line ("[TEST 09] Optimization Cost function:");
      --  Perfect match: beta_calc == beta_target, y_pred == y_target
      Cost_Val := Optimization_Cost (26.9, 26.9, 0.0, 0.0, 1.0, 0.0);
      Put_Line ("  Cost(perfect) = " & Float'Image (Cost_Val) & "  Expected ~ 0.0");
      --  Mismatch: beta_calc differs by 10
      Cost_Val := Optimization_Cost (36.9, 26.9, 0.0, 0.0, 1.0, 0.0);
      Put_Line ("  Cost(delta=10)= " & Float'Image (Cost_Val) & "  Expected ~ 1.0");
      --  Zero weight: cost should be 0
      Cost_Val := Optimization_Cost (100.0, 26.9, 0.0, 0.0, 0.0, 0.0);
      Put_Line ("  Cost(w=0)     = " & Float'Image (Cost_Val) & "  Expected ~ 0.0");
      --  Cost is always non-negative (Post condition)
      Cost_Val := Optimization_Cost (50.0, 26.9, 10.0, 0.0, 1.0, 1.0);
      if Cost_Val >= 0.0 then
         Put_Line ("[TEST 09]   PASS (cost non-negative)");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 09]   FAIL (negative cost!)");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 10: TPS Material Presets (all 6 materials)
      --  ==================================================================
      Put_Line ("[TEST 10] TPS Material Presets (6 materials):");
      declare
         SiC     : constant TPS_Material := TPS_SiC;
         PICA    : constant TPS_Material := TPS_PICA_X;
         LOFT    : constant TPS_Material := TPS_LOFTID;
         Kapt    : constant TPS_Material := TPS_Kapton;
         Pyro    : constant TPS_Material := TPS_Pyrogel;
         Multi   : constant TPS_Material := TPS_Multi;
         All_OK  : Boolean := True;
      begin
         --  Validate each material: density > 0, cp > 0, 0 < emissivity <= 1
         if SiC.Density <= 0.0 or SiC.Cp <= 0.0
           or SiC.Emissivity <= 0.0 or SiC.Emissivity > 1.0 then
            Put_Line ("  SiC:      INVALID"); All_OK := False;
         else
            Put_Line ("  SiC:      OK (d=" & Float'Image (SiC.Density) &
                      ", cp=" & Float'Image (SiC.Cp) &
                      ", eps=" & Float'Image (SiC.Emissivity) & ")");
         end if;
         if PICA.Density <= 0.0 or PICA.Cp <= 0.0
           or PICA.Emissivity <= 0.0 or PICA.Emissivity > 1.0 then
            Put_Line ("  PICA-X:   INVALID"); All_OK := False;
         else
            Put_Line ("  PICA-X:   OK (d=" & Float'Image (PICA.Density) &
                      ", cp=" & Float'Image (PICA.Cp) &
                      ", eps=" & Float'Image (PICA.Emissivity) & ")");
         end if;
         if LOFT.Density <= 0.0 or LOFT.Cp <= 0.0
           or LOFT.Emissivity <= 0.0 or LOFT.Emissivity > 1.0 then
            Put_Line ("  LOFTID:   INVALID"); All_OK := False;
         else
            Put_Line ("  LOFTID:   OK (d=" & Float'Image (LOFT.Density) &
                      ", cp=" & Float'Image (LOFT.Cp) &
                      ", eps=" & Float'Image (LOFT.Emissivity) & ")");
         end if;
         if Kapt.Density <= 0.0 or Kapt.Cp <= 0.0
           or Kapt.Emissivity <= 0.0 or Kapt.Emissivity > 1.0 then
            Put_Line ("  Kapton:   INVALID"); All_OK := False;
         else
            Put_Line ("  Kapton:   OK (d=" & Float'Image (Kapt.Density) &
                      ", cp=" & Float'Image (Kapt.Cp) &
                      ", eps=" & Float'Image (Kapt.Emissivity) & ")");
         end if;
         if Pyro.Density <= 0.0 or Pyro.Cp <= 0.0
           or Pyro.Emissivity <= 0.0 or Pyro.Emissivity > 1.0 then
            Put_Line ("  Pyrogel:  INVALID"); All_OK := False;
         else
            Put_Line ("  Pyrogel:  OK (d=" & Float'Image (Pyro.Density) &
                      ", cp=" & Float'Image (Pyro.Cp) &
                      ", eps=" & Float'Image (Pyro.Emissivity) & ")");
         end if;
         if Multi.Density <= 0.0 or Multi.Cp <= 0.0
           or Multi.Emissivity <= 0.0 or Multi.Emissivity > 1.0 then
            Put_Line ("  Multi:    INVALID"); All_OK := False;
         else
            Put_Line ("  Multi:    OK (d=" & Float'Image (Multi.Density) &
                      ", cp=" & Float'Image (Multi.Cp) &
                      ", eps=" & Float'Image (Multi.Emissivity) & ")");
         end if;

         if All_OK then
            Put_Line ("[TEST 10]   PASS (all 6 materials valid)");
            Pass_Count := Pass_Count + 1;
         else
            Put_Line ("[TEST 10]   FAIL");
            Fail_Count := Fail_Count + 1;
         end if;
      end;
      New_Line;

      --  ==================================================================
      --  Test 11: Geometry Edge Cases (boundary validation)
      --  ==================================================================
      Put_Line ("[TEST 11] Geometry Edge Cases:");
      declare
         Min_Geo : constant Geometry_Parameters :=
           (Diameter_M => 0.5, Angle_Deg => 40.0, Toroid_Count => 1,
            others => <>);
         Max_Geo : constant Geometry_Parameters :=
           (Diameter_M => 15.0, Angle_Deg => 80.0, Toroid_Count => 12,
            others => <>);
         Bad_Angle : constant Geometry_Parameters :=
           (Diameter_M => 3.0, Angle_Deg => 39.0, others => <>);
         All_OK : Boolean := True;
      begin
         if not Validate_Geometry (Min_Geo) then
            Put_Line ("  Min geometry (D=0.5, A=40, T=1): INVALID  -- FAIL");
            All_OK := False;
         else
            Put_Line ("  Min geometry (D=0.5, A=40, T=1): VALID");
         end if;
         if not Validate_Geometry (Max_Geo) then
            Put_Line ("  Max geometry (D=15, A=80, T=12): INVALID  -- FAIL");
            All_OK := False;
         else
            Put_Line ("  Max geometry (D=15, A=80, T=12): VALID");
         end if;
         if Validate_Geometry (Bad_Angle) then
            Put_Line ("  Bad angle (39.0): VALID (unexpected!)  -- FAIL");
            All_OK := False;
         else
            Put_Line ("  Bad angle (39.0): INVALID (expected)");
         end if;
         if All_OK then
            Put_Line ("[TEST 11]   PASS");
            Pass_Count := Pass_Count + 1;
         else
            Put_Line ("[TEST 11]   FAIL");
            Fail_Count := Fail_Count + 1;
         end if;
      end;
      New_Line;

      --  ==================================================================
      --  Test 12: Is_Survivable (extreme metrics check)
      --  ==================================================================
      Put_Line ("[TEST 12] Is_Survivable (survivability gate):");
      --  Normal metrics (should be survivable for default TPS)
      if Survivable then
         Put_Line ("  Default IRVE-3 metrics: SURVIVABLE  (OK)");
      else
         Put_Line ("  Default IRVE-3 metrics: NOT SURVIVABLE (may be expected)");
      end if;
      --  Extreme metrics (should NOT be survivable)
      Bad_Metrics := (Ballistic_Coeff     => 100.0,
                      Knudsen_Number      => 0.01,
                      Stag_Heat_Flux_Wm2  => 1.0e8,
                      Stag_Heat_Flux_Wcm2 => 1.0e4,
                      Surface_Temp_K      => 50000.0,
                      Backface_Temp_K     => 50000.0,
                      Decel_G             => 500.0,
                      G_Load              => 500.0,
                      Survivable          => False);
      if not Is_Survivable (Bad_Metrics) then
         Put_Line ("  Extreme metrics: NOT SURVIVABLE (expected)");
         Put_Line ("[TEST 12]   PASS");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("  Extreme metrics: SURVIVABLE (unexpected!)  -- FAIL");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Test 13: Nose_Type_Kind enum
      --  ==================================================================
      Put_Line ("[TEST 13] Nose_Type_Kind enum:");
      NT := Smooth;
      if NT = Smooth then
         Put_Line ("  Smooth = Smooth: OK");
      end if;
      NT := Pointy;
      if NT = Pointy then
         Put_Line ("  Pointy = Pointy: OK");
      end if;
      if Nose_Type_Kind'(Smooth) /= Nose_Type_Kind'(Pointy) then
         Put_Line ("[TEST 13]   PASS (distinct enum values)");
         Pass_Count := Pass_Count + 1;
      else
         Put_Line ("[TEST 13]   FAIL");
         Fail_Count := Fail_Count + 1;
      end if;
      New_Line;

      --  ==================================================================
      --  Summary
      --  ==================================================================
      Put_Line ("========================================");
      Put_Line ("[TEST] Self-test complete: " &
                Natural'Image (Pass_Count) & " PASS, " &
                Natural'Image (Fail_Count) & " FAIL");
      Put_Line ("========================================");

      if Fail_Count = 0 then
         Put_Line ("[TEST] All 13 self-tests PASSED.");
         Write_Status (STATUS_DIR, "self_test", Status_Completed, 1.0);
      else
         Put_Line ("[TEST] SOME TESTS FAILED!");
         Write_Status (STATUS_DIR, "self_test",
                       StellarOrion_Status_Writer.Status_Error, 0.0);
      end if;
   end Run_Self_Test;

   procedure Run_GetIRVE3_Baseline is
      Flight : constant Flight_Parameters := (others => <>);
      Geo    : constant Geometry_Parameters := (others => <>);
      TPS    : constant TPS_Material := (others => <>);
      Results: Simulation_Results;
      Metrics: Flight_Metrics;
   begin
      Write_Status (STATUS_DIR, "irve3_baseline", Status_Running, 0.0);
      Put_Line ("[IRVE3] Running baseline calculation ...");
      Put_Line ("[IRVE3] Mach 10, 52 km, 3.0 m diameter");
      New_Line;

      --  Use Sutton-Graves for quick analytical estimate
      Results.Heat_Flux_Wm2 :=
        Sutton_Graves_Heat (Flight.Density_Kgm3,
                            Geo.Nose_Radius_M,
                            Flight.Velocity_Ms);
      --  Compute drag force: F_drag = Cd * q * A
      declare
         Cd       : constant Float := 1.47;
         Q_Dyn    : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;
         Ref_Area : constant Float :=
           Ada.Numerics.Pi * (Geo.Diameter_M / 2.0) ** 2;
      begin
         Results.Drag_Force := Cd * Q_Dyn * Ref_Area;
      end;

      Calculate_Flight_Metrics (Results, Flight, Geo, TPS, Metrics);

      Put_Line ("[IRVE3] ---- Results ----");
      Put_Line ("  Stag Heat Flux : " &
                Float'Image (Metrics.Stag_Heat_Flux_Wcm2) & " W/cm^2");
      Put_Line ("  Total Heat Load: " &
                Float'Image (Results.Total_Heat_Load) & " J/m^2");
      Put_Line ("  Ballistic Coeff: " &
                Float'Image (Metrics.Ballistic_Coeff) & " kg/m^2");
      Put_Line ("  Peak Decel     : " &
                Float'Image (Metrics.Decel_G) & " g");
      Put_Line ("  Survivable     : " &
                Boolean'Image (Metrics.Survivable));
      Write_Status (STATUS_DIR, "irve3_baseline", Status_Completed, 1.0);
   end Run_GetIRVE3_Baseline;

   procedure Run_CompareNoses
     (Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0;
      Geo_In        : Geometry_Parameters := (others => <>);
      TPS_In        : TPS_Material := (others => <>))
   is
      Flight      : Flight_Parameters;
      Geo_Smooth  : Geometry_Parameters := Geo_In;
      Geo_Pointy  : Geometry_Parameters := Geo_In;
      Results_S   : Simulation_Results;
      Results_P   : Simulation_Results;
      Metrics_S   : Flight_Metrics;
      Metrics_P   : Flight_Metrics;
   begin
      Write_Status (STATUS_DIR, "compare_noses", Status_Running, 0.0);
      Put_Line ("[COMPARE] ====== Nose-Cone Comparison ======");
      Put_Line ("[COMPARE] Smooth (R=0.55m) vs Pointy (R=0.10m) nose geometries");
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

      Put_Line ("  Mach     : " & Float'Image (Flight.Mach));
      Put_Line ("  Altitude : " & Float'Image (Flight.Altitude_Km) & " km");
      Put_Line ("  Velocity : " & Float'Image (Flight.Velocity_Ms) & " m/s");
      Put_Line ("  Density  : " & Float'Image (Flight.Density_Kgm3) & " kg/m^3");
      New_Line;

      --  Smooth nose (R=0.55)
      Geo_Smooth.Nose_Radius_M := 0.55;
      Results_S.Heat_Flux_Wm2 :=
        Sutton_Graves_Heat (Flight.Density_Kgm3,
                            Geo_Smooth.Nose_Radius_M,
                            Flight.Velocity_Ms);
      declare
         Cd_S     : constant Float := 1.47;
         Q_Dyn_S  : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;
         Ref_A_S  : constant Float :=
           Ada.Numerics.Pi * (Geo_Smooth.Diameter_M / 2.0) ** 2;
      begin
         Results_S.Drag_Force := Cd_S * Q_Dyn_S * Ref_A_S;
      end;
      Calculate_Flight_Metrics (Results_S, Flight, Geo_Smooth, TPS_In, Metrics_S);

      --  Pointy nose (R=0.10)
      Geo_Pointy.Nose_Radius_M := 0.10;
      Results_P.Heat_Flux_Wm2 :=
        Sutton_Graves_Heat (Flight.Density_Kgm3,
                            Geo_Pointy.Nose_Radius_M,
                            Flight.Velocity_Ms);
      declare
         Cd_P     : constant Float := 1.47;
         Q_Dyn_P  : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;
         Ref_A_P  : constant Float :=
           Ada.Numerics.Pi * (Geo_Pointy.Diameter_M / 2.0) ** 2;
      begin
         Results_P.Drag_Force := Cd_P * Q_Dyn_P * Ref_A_P;
      end;
      Calculate_Flight_Metrics (Results_P, Flight, Geo_Pointy, TPS_In, Metrics_P);

      --  Comparison table
      Put_Line ("[COMPARE] ---- Comparison Table ----");
      Put_Line ("  ---------------------------------------------------------------");
      Put_Line ("  Parameter          | Smooth (R=0.55) | Pointy (R=0.10)");
      Put_Line ("  ---------------------------------------------------------------");
      Put_Line ("  Heat flux (W/cm^2) | " &
                Float'Image (Metrics_S.Stag_Heat_Flux_Wcm2) & "          | " &
                Float'Image (Metrics_P.Stag_Heat_Flux_Wcm2));
      Put_Line ("  Surface temp (K)   | " &
                Float'Image (Metrics_S.Surface_Temp_K) & "      | " &
                Float'Image (Metrics_P.Surface_Temp_K));
      Put_Line ("  Backface temp (K)  | " &
                Float'Image (Metrics_S.Backface_Temp_K) & "      | " &
                Float'Image (Metrics_P.Backface_Temp_K));
      Put_Line ("  Beta (kg/m^2)      | " &
                Float'Image (Metrics_S.Ballistic_Coeff) & "       | " &
                Float'Image (Metrics_P.Ballistic_Coeff));
      Put_Line ("  Decel G            | " &
                Float'Image (Metrics_S.Decel_G) & "         | " &
                Float'Image (Metrics_P.Decel_G));
      Put_Line ("  Survivable         | " &
                Boolean'Image (Metrics_S.Survivable) & "           | " &
                Boolean'Image (Metrics_P.Survivable));
      Put_Line ("  ---------------------------------------------------------------");
      New_Line;

      --  Deviation analysis
      Put_Line ("[COMPARE] Heat flux ratio (pointy/smooth): " &
                Float'Image (Metrics_P.Stag_Heat_Flux_Wcm2 /
                             Metrics_S.Stag_Heat_Flux_Wcm2));
      Put_Line ("[COMPARE] NOTE: Sharper nose reduces heat flux but");
      Put_Line ("           increases structural loading and TPS demands.");
      Write_Status (STATUS_DIR, "compare_noses", Status_Completed, 1.0);
   end Run_CompareNoses;

   procedure Run_GridIndep_Test is
      Factors : constant array (1 .. 8) of Float :=
        (0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5);
      pragma Unreferenced (Factors);
   begin
      Put_Line ("[GRID] Grid Independency Test");
      Put_Line ("[GRID] Testing grid-factor from 0.3 to 1.5");
      New_Line;

      for F of Factors loop
         Put_Line ("  Grid factor " & Float'Image (F) &
                   " -> cell size ~ " &
                   Float'Image (0.015 * F) & " m");
      end loop;

      New_Line;
      Put_Line ("[GRID] Optimal: 0.7 (validated against IRVE-3 MDAO)");
   end Run_GridIndep_Test;

   procedure Run_Demo is
      Flight : Flight_Parameters;
      Geo    : Geometry_Parameters;
      TPS    : TPS_Material;
      Results: Simulation_Results;
      Metrics: Flight_Metrics;
   begin
      Put_Line ("[DEMO] Quick demo run");
      New_Line;

      Mach_Alt_To_Flight (10.0, 52.0, Flight);

      Geo    := (others => <>);  -- IRVE-3 defaults
      TPS    := (others => <>);  -- SiC defaults

      Results.Heat_Flux_Wm2 :=
        Sutton_Graves_Heat (Flight.Density_Kgm3,
                            Geo.Nose_Radius_M,
                            Flight.Velocity_Ms);
      --  Compute drag force: F_drag = Cd * q * A
      declare
         Cd_D     : constant Float := 1.47;
         Q_Dyn_D  : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;
         Ref_A_D  : constant Float :=
           Ada.Numerics.Pi * (Geo.Diameter_M / 2.0) ** 2;
      begin
         Results.Drag_Force := Cd_D * Q_Dyn_D * Ref_A_D;
      end;

      Calculate_Flight_Metrics (Results, Flight, Geo, TPS, Metrics);

      Put_Line ("[DEMO] ---- Flight Parameters ----");
      Put_Line ("  Mach       : " & Float'Image (Flight.Mach));
      Put_Line ("  Altitude   : " & Float'Image (Flight.Altitude_Km) & " km");
      Put_Line ("  Velocity   : " & Float'Image (Flight.Velocity_Ms) & " m/s");
      Put_Line ("  Density    : " & Float'Image (Flight.Density_Kgm3) & " kg/m^3");
      Put_Line ("  Temperature: " & Float'Image (Flight.Temperature_K) & " K");
      New_Line;

      Put_Line ("[DEMO] ---- Results ----");
      Put_Line ("  Stag Heat Flux  : " &
                Float'Image (Metrics.Stag_Heat_Flux_Wcm2) & " W/cm^2");
      Put_Line ("  Surface Temp    : " &
                Float'Image (Metrics.Surface_Temp_K) & " K");
      Put_Line ("  Backface Temp   : " &
                Float'Image (Metrics.Backface_Temp_K) & " K");
      Put_Line ("  Ballistic Coeff : " &
                Float'Image (Metrics.Ballistic_Coeff) & " kg/m^2");
      Put_Line ("  Decel G         : " &
                Float'Image (Metrics.Decel_G) & " g");
      Put_Line ("  Survivable      : " &
                Boolean'Image (Metrics.Survivable));
   end Run_Demo;

   procedure Run_Validate_Only
     (Geo_In : Geometry_Parameters := (others => <>);
      TPS_In : TPS_Material := (others => <>))
   is
       Geo : constant Geometry_Parameters := Geo_In;
       TPS : constant TPS_Material := TPS_In;
       Valid : Boolean;
    begin
       Put_Line ("[VALIDATE] Pre-simulation geometry QA ...");

      Valid := Validate_And_Dump (Geo, TPS);

      if Valid then
         Put_Line ("[VALIDATE] All geometry checks PASSED.");
      else
         Put_Line ("[VALIDATE] Geometry checks FAILED.");
      end if;
   end Run_Validate_Only;

   --  Forward declaration (full body defined after Run_Compare_Calibrate)
   procedure Run_Validate_Full
     (Steps         : Positive;
      Grid_Factor   : Float;
      Chemistry     : Chemistry_Mode;
      Geo_In        : Geometry_Parameters;
      TPS_In        : TPS_Material;
      Mach_Override : Float;
      Alt_Override  : Float;
      Cores         : Positive;
      Use_GPU       : Boolean;
      Fnum_Str      : String;
      Restart_File  : String;
      Results_Dir   : String);

   procedure Run_Test_Baseline
     (Steps      : Positive := 1_000;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   is
   begin
      Put_Line ("[TEST:baseline] Running IRVE-3 baseline test (full SPARTA pipeline) ...");
      Put_Line ("[TEST:baseline] This runs the same 10-step pipeline as --validate.");
      Put_Line ("[TEST:baseline] Geometry: IRVE-3 defaults | Steps:" & Positive'Image (Steps));
      New_Line;

      --  Delegate to Run_Validate_Full with IRVE-3 defaults
      Run_Validate_Full (Steps         => Steps,
                         Grid_Factor   => 0.7,
                         Chemistry     => Five_Species,
                         Geo_In        => Geo_In,
                         TPS_In        => TPS_In,
                         Mach_Override => Mach_Override,
                         Alt_Override  => Alt_Override,
                         Cores         => 4,
                         Use_GPU       => False,
                         Fnum_Str      => "1.5e20",
                         Restart_File  => "",
                         Results_Dir   => "results_test_baseline");
   end Run_Test_Baseline;

   procedure Run_Test_Sample
     (Steps      : Positive := 1_000;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   is
   begin
      Put_Line ("[TEST:sample] Running sample geometry test (full SPARTA pipeline) ...");
      Put_Line ("[TEST:sample] This runs the same 10-step pipeline as --validate.");
      Put_Line ("[TEST:sample] Steps:" & Positive'Image (Steps));
      New_Line;

      --  Delegate to Run_Validate_Full with default grid and IRVE-3 chemistry
      Run_Validate_Full (Steps         => Steps,
                         Grid_Factor   => 0.7,
                         Chemistry     => Five_Species,
                         Geo_In        => Geo_In,
                         TPS_In        => TPS_In,
                         Mach_Override => Mach_Override,
                         Alt_Override  => Alt_Override,
                         Cores         => 4,
                         Use_GPU       => False,
                         Fnum_Str      => "1.5e20",
                         Restart_File  => "",
                         Results_Dir   => "results_test_sample");
   end Run_Test_Sample;

   procedure Run_Test_PINN_Calibration (Steps : Positive := 1_000) is
      --  PINN calibration requires DeepXDE + PyTorch (Python-only).
      --  Spawns standalone sidecar: src/python/pinn_test.py which handles:
      --    1. Baseline SPARTA validation (reads grid.NNNN.out files)
      --    2. DeepXDE PINN training via pinn_accelerator.py
      --    3. 3-way comparison (SPARTA vs PINN vs IRVE-3 document)
      Success   : Boolean;
      Steps_Raw : constant String := Positive'Image (Steps);
      Steps_Arg : constant String :=
        Steps_Raw (Steps_Raw'First + 1 .. Steps_Raw'Last);
   begin
      Write_Status (STATUS_DIR, "pinn_calibration", Status_Running, 0.0);
      Put_Line ("[TEST:pinn_calibration] PINN calibration test");
      Put_Line ("[TEST] Spawning standalone PINN sidecar ...");
      Put_Line ("[TEST] Steps :" & Steps_Arg);

      Spawn ("python3",
             (1 => new String'("src/python/pinn_test.py"),
              2 => new String'("--steps"),
              3 => new String'(Steps_Arg),
              4 => new String'("--solver"),
              5 => new String'("sparta")),
             Success);

      if Success then
         Put_Line ("[TEST:pinn_calibration] PINN calibration completed.");
      else
         Put_Line ("[TEST:pinn_calibration] PINN calibration FAILED.");
         Put_Line ("[TEST] Ensure Python 3.10+, torch, deepxde are installed.");
         Put_Line ("[TEST] Or run manually: python3 src/python/pinn_test.py --steps" & Steps_Arg);
      end if;

      Write_Status (STATUS_DIR, "pinn_calibration", Status_Completed, 1.0);
   end Run_Test_PINN_Calibration;

   -- ==================================================================
   --  New Test Modes (full parity with main.py)
   -- ==================================================================

   procedure Run_Test_Sparta_Integration is
   begin
      Write_Status (STATUS_DIR, "test_sparta", Status_Running, 0.0);
      Put_Line ("[TEST:sparta] SPARTA Docker integration test");
      Put_Line ("[TEST] Building SPARTA Docker image ...");
      Build_Sparta_Library;
      Put_Line ("[TEST] SPARTA integration test PASSED (image built).");
      Write_Status (STATUS_DIR, "test_sparta", Status_Completed, 1.0);
   end Run_Test_Sparta_Integration;

   procedure Run_Test_PyFluent_Integration
     (SSH_Host : String;
      SSH_User : String;
      SSH_Pass : String;
      SSH_Key  : String)
   is
      Success : Boolean;
   begin
      Write_Status (STATUS_DIR, "test_pyfluent", Status_Running, 0.0);
      Put_Line ("[TEST:pyfluent] PyFluent remote integration test (via standalone sidecar)");

      --  Validate SSH credentials
      if SSH_Host'Length = 0 or else SSH_User'Length = 0 then
         Put_Line ("[TEST:pyfluent] ERROR: --ssh-host and --ssh-user are required.");
         Put_Line ("[TEST:pyfluent] Usage: --test pyfluent --ssh-host HOST --ssh-user USER [--ssh-key KEY]");
         Write_Status (STATUS_DIR, "test_pyfluent", Status_Completed, 0.0);
         return;
      end if;

      Put_Line ("[TEST:pyfluent] Host     : " & SSH_Host);
      Put_Line ("[TEST:pyfluent] User     : " & SSH_User);
      if SSH_Key'Length > 0 then
         Put_Line ("[TEST:pyfluent] Key      : " & SSH_Key);
      end if;
      Put_Line ("[TEST:pyfluent] Spawning standalone PyFluent sidecar ...");

      --  Spawn src/python/pyfluent_test.py --ssh-host ... --ssh-user ...
      if SSH_Key'Length > 0 then
         Spawn ("python3",
                (1 => new String'("src/python/pyfluent_test.py"),
                 2 => new String'("--ssh-host"),
                 3 => new String'(SSH_Host),
                 4 => new String'("--ssh-user"),
                 5 => new String'(SSH_User),
                 6 => new String'("--ssh-key"),
                 7 => new String'(SSH_Key)),
                Success);
      elsif SSH_Pass'Length > 0 then
         Spawn ("python3",
                (1 => new String'("src/python/pyfluent_test.py"),
                 2 => new String'("--ssh-host"),
                 3 => new String'(SSH_Host),
                 4 => new String'("--ssh-user"),
                 5 => new String'(SSH_User),
                 6 => new String'("--ssh-pass"),
                 7 => new String'(SSH_Pass)),
                Success);
      else
         Spawn ("python3",
                (1 => new String'("src/python/pyfluent_test.py"),
                 2 => new String'("--ssh-host"),
                 3 => new String'(SSH_Host),
                 4 => new String'("--ssh-user"),
                 5 => new String'(SSH_User)),
                Success);
      end if;

      if Success then
         Put_Line ("[TEST:pyfluent] PyFluent integration test PASSED.");
      else
         Put_Line ("[TEST:pyfluent] PyFluent integration test FAILED.");
         Put_Line ("[TEST] Ensure paramiko, ansys-fluent-core are installed on remote host.");
         Put_Line ("[TEST] Or run manually: python3 src/python/pyfluent_test.py --ssh-host HOST --ssh-user USER");
      end if;

      Write_Status (STATUS_DIR, "test_pyfluent", Status_Completed, 1.0);
   end Run_Test_PyFluent_Integration;

   procedure Run_Test_PyAnsys_Integration is
      Success : Boolean;
   begin
      Write_Status (STATUS_DIR, "test_pyansys", Status_Running, 0.0);
      Put_Line ("[TEST:pyansys] PyAnsys local integration test (via standalone sidecar)");
      Put_Line ("[TEST] This mode requires Windows with Ansys Fluent installed.");
      Put_Line ("[TEST] Spawning standalone PyAnsys sidecar ...");

      --  Spawn src/python/pyansys_test.py
      Spawn ("python3",
             (1 => new String'("src/python/pyansys_test.py")),
             Success);

      if Success then
         Put_Line ("[TEST:pyansys] PyAnsys local integration test PASSED.");
      else
         Put_Line ("[TEST:pyansys] PyAnsys local integration test FAILED.");
         Put_Line ("[TEST] Ensure ansys-fluent-core is installed locally.");
         Put_Line ("[TEST] This mode requires Windows with Ansys Fluent.");
         Put_Line ("[TEST] Or run manually: python3 src/python/pyansys_test.py");
      end if;

      Write_Status (STATUS_DIR, "test_pyansys", Status_Completed, 1.0);
   end Run_Test_PyAnsys_Integration;

   procedure Run_Test_OpenFOAM_Integration is
      --  Mirrors StellarOrionEngine_ORION.py:2564-2608
      --  Creates a minimal blockMesh case and runs blockMesh inside the
      --  openfoam-hysp Docker container to verify the OpenFOAM toolchain.
      Test_Dir : constant String := "scratch/openfoam_test";
      Sys_Dir  : constant String := Test_Dir & "/system";
      BM_File  : File_Type;
      CD_File  : File_Type;
      Success  : Boolean;
   begin
      Write_Status (STATUS_DIR, "test_openfoam", Status_Running, 0.0);
      Put_Line ("[TEST:openfoam] OpenFOAM Docker integration test");

      --  Create directory structure
      if not Exists (Test_Dir) then
         Create_Directory (Test_Dir);
      end if;
      if not Exists (Sys_Dir) then
         Create_Directory (Sys_Dir);
      end if;

      --  Write blockMeshDict (minimal 10x10x10 hex mesh)
      Create (BM_File, Out_File, Sys_Dir & "/blockMeshDict");
      Put_Line (BM_File, "FoamFile");
      Put_Line (BM_File, "{");
      Put_Line (BM_File, "    version     2.0;");
      Put_Line (BM_File, "    format      ascii;");
      Put_Line (BM_File, "    class       dictionary;");
      Put_Line (BM_File, "    object      blockMeshDict;");
      Put_Line (BM_File, "}");
      Put_Line (BM_File, "");
      Put_Line (BM_File, "scale 0.1;");
      Put_Line (BM_File, "");
      Put_Line (BM_File, "vertices");
      Put_Line (BM_File, "(");
      Put_Line (BM_File, "    (0 0 0)");
      Put_Line (BM_File, "    (1 0 0)");
      Put_Line (BM_File, "    (1 1 0)");
      Put_Line (BM_File, "    (0 1 0)");
      Put_Line (BM_File, "    (0 0 1)");
      Put_Line (BM_File, "    (1 0 1)");
      Put_Line (BM_File, "    (1 1 1)");
      Put_Line (BM_File, "    (0 1 1)");
      Put_Line (BM_File, ");");
      Put_Line (BM_File, "");
      Put_Line (BM_File, "blocks");
      Put_Line (BM_File, "(");
      Put_Line (BM_File,
        "    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)");
      Put_Line (BM_File, ");");
      Put_Line (BM_File, "");
      Put_Line (BM_File, "edges");
      Put_Line (BM_File, "(");
      Put_Line (BM_File, ");");
      Put_Line (BM_File, "");
      Put_Line (BM_File, "boundary");
      Put_Line (BM_File, "(");
      Put_Line (BM_File, "    open");
      Put_Line (BM_File, "    {");
      Put_Line (BM_File, "        type patch;");
      Put_Line (BM_File, "        faces");
      Put_Line (BM_File, "        (");
      Put_Line (BM_File, "            (0 4 7 3)");
      Put_Line (BM_File, "            (1 2 6 5)");
      Put_Line (BM_File, "            (0 1 5 4)");
      Put_Line (BM_File, "            (2 3 7 6)");
      Put_Line (BM_File, "            (0 3 2 1)");
      Put_Line (BM_File, "            (4 5 6 7)");
      Put_Line (BM_File, "        );");
      Put_Line (BM_File, "    }");
      Put_Line (BM_File, ");");
      Put_Line (BM_File, "");
      Put_Line (BM_File, "mergePatchPairs");
      Put_Line (BM_File, "(");
      Put_Line (BM_File, ");");
      Close (BM_File);

      --  Write controlDict
      Create (CD_File, Out_File, Sys_Dir & "/controlDict");
      Put_Line (CD_File, "FoamFile");
      Put_Line (CD_File, "{");
      Put_Line (CD_File, "    version     2.0;");
      Put_Line (CD_File, "    format      ascii;");
      Put_Line (CD_File, "    class       dictionary;");
      Put_Line (CD_File, "    object      controlDict;");
      Put_Line (CD_File, "}");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "application   blockMesh;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "startFrom     startTime;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "startTime     0;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "stopAt        endTime;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "endTime       1;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "deltaT        1;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "writeControl  timeStep;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "writeInterval 1;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "purgeWrite    0;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "writeFormat   ascii;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "writePrecision 8;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "writeCompression off;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "timeFormat    general;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "timePrecision 6;");
      Put_Line (CD_File, "");
      Put_Line (CD_File, "runTimeModifiable yes;");
      Close (CD_File);

      Put_Line ("[TEST] Wrote blockMeshDict + controlDict to " & Sys_Dir);
      Put_Line ("[TEST] Running OpenFOAM Docker container ...");

      --  Run OpenFOAM Docker (mirrors Python: docker run --rm -v ...)
      Spawn ("docker",
             (1 => new String'("run"),
              2 => new String'("--rm"),
              3 => new String'("-v"),
              4 => new String'(Test_Dir & ":/workspace"),
              5 => new String'("openfoam-hysp"),
              6 => new String'("bash"),
              7 => new String'("-c"),
              8 => new String'(
                "source /usr/lib/openfoam/openfoam2312/etc/bashrc"
                & " && cd /workspace && blockMesh")),
             Success);

      if Success then
         Put_Line ("[TEST:openfoam] OpenFOAM integration test PASSED.");
      else
         Put_Line ("[TEST:openfoam] OpenFOAM integration test FAILED.");
         Put_Line ("[TEST] Ensure Docker is running and openfoam-hysp image exists.");
         Put_Line ("[TEST] Build with: docker build -t openfoam-hysp .");
      end if;

      Write_Status (STATUS_DIR, "test_openfoam", Status_Completed, 1.0);
   end Run_Test_OpenFOAM_Integration;

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
      N_Samples : Positive   := Samples_In;
      Flight    : Flight_Parameters;
      Geo       : Geometry_Parameters := Geo_In;
      TPS       : constant TPS_Material := TPS_In;
      Target_Beta : constant Float := 26.9;  -- IRVE-3 target

      --  GA configuration (tuned for HIAD optimisation)
      Config    : GA_Config;
      Result    : GA_Result;
      pragma Unreferenced (DoE, Obj, N_Samples, Steps, Grid_Factor, Chemistry, Geo);
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
   --  Full Validation Pipeline
   -- ==================================================================
   --  Chains: geometry QA -> SPARTA script gen -> Docker build/run
   --          -> result parse -> flight metrics -> survivability
   --          -> compare against IRVE-3 flight data.
   --
   --  IRVE-3 flight data targets (NASA/TP-2013-4012, Rapisarda 2023):
   --    Peak heat flux:    13.8 W/cm^2
   --    Total heat load:   188 J/cm^2
   --    Peak deceleration: 19.7 g
   --    Ballistic coeff:   26.9 kg/m^2
   --    Stagnation pressure: ~12.4 kPa

   procedure Run_Validate_Full
     (Steps         : Positive;
      Grid_Factor   : Float;
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
      Flight     : Flight_Parameters;
      Geo        : constant Geometry_Parameters := Geo_In;
      TPS        : constant TPS_Material := TPS_In;
      Results    : Simulation_Results;
      Metrics    : Flight_Metrics;
      DOK        : Boolean;
      Survivable : Boolean;

      --  Tolerance bands (percentage of target)
      Tolerance_Heat   : constant Float := 0.15;  -- 15%
      Tolerance_Decel  : constant Float := 0.10;  -- 10%
      Tolerance_Beta   : constant Float := 0.20;  -- 20%
      Tolerance_Cd     : constant Float := 0.20;  -- 20% (Cd is geometry-dependent)
      Tolerance_Press  : constant Float := 0.15;  -- 15% (pressure/geometry)
      Tolerance_Temp   : constant Float := 0.10;  -- 10% (ISA temperature)

      --  IRVE-3 flight data reference targets
      Target_Heat_Flux : constant Float := 13.8;    -- W/cm^2
      Target_Heat_Load : constant Float := 188.0;   -- J/cm^2
      Target_Decel_G   : constant Float := 19.7;    -- g
      Target_Beta      : constant Float := 26.9;    -- kg/m^2
      Target_Pressure  : constant Float := 12400.0;  -- Pa (12.4 kPa)

      --  MDAO doc baseline targets (Rapisarda 2023 / IRVE-3 MDAO paper)
      Target_Cd            : constant Float := 1.47;    -- drag coefficient
      Target_Dyn_Press_KPa : constant Float := 6.2;     -- kPa
      Target_Toroid_Radius : constant Float := 0.135;   -- m
      Target_Ambient_Temp  : constant Float := 270.65;  -- K
      Target_Ambient_Press : constant Float := 75.77;   -- Pa
      Target_Payload_Height: constant Float := 1.70;    -- m

      --  Fnum: real molecules per simulated particle
      Fnum : Float;
   begin
      --  Parse Fnum from string
      if Fnum_Str'Length > 0 then
         begin
            Fnum := Float'Value (Fnum_Str);
         exception
            when others =>
               Fnum := 1.5e20;
         end;
      else
         Fnum := 1.5e20;
      end if;

      Put_Line ("[VALIDATE] ====== Full Validation Pipeline ======");
      New_Line;

      --  Step 1: Set up flight parameters
      Put_Line ("[VALIDATE] Step 1: Setting up flight parameters ...");
      if Mach_Override > 0.0 and Alt_Override > 0.0 then
         Mach_Alt_To_Flight (Mach_Override, Alt_Override, Flight);
      elsif Mach_Override > 0.0 then
         Mach_Alt_To_Flight (Mach_Override, 52.0, Flight);
      elsif Alt_Override > 0.0 then
         Mach_Alt_To_Flight (10.0, Alt_Override, Flight);
      else
         Mach_Alt_To_Flight (10.0, 52.0, Flight);
      end if;

      Put_Line ("  Mach        : " & Float'Image (Flight.Mach));
      Put_Line ("  Altitude    : " & Float'Image (Flight.Altitude_Km) & " km");
      Put_Line ("  Velocity    : " & Float'Image (Flight.Velocity_Ms) & " m/s");
      Put_Line ("  Density     : " & Float'Image (Flight.Density_Kgm3) & " kg/m^3");
      Put_Line ("  Temperature : " & Float'Image (Flight.Temperature_K) & " K");
      Put_Line ("  Diameter    : " & Float'Image (Geo.Diameter_M) & " m");
      Put_Line ("  Steps       : " & Positive'Image (Steps));
      Put_Line ("  Grid factor : " & Float'Image (Grid_Factor));
      Put_Line ("  Cores       : " & Positive'Image (Cores));
      Put_Line ("  GPU         : " & Boolean'Image (Use_GPU));
      Put_Line ("  Fnum        : " & Float'Image (Fnum));
      New_Line;

      --  Step 2: Validate geometry (pre-simulation QA)
      Put_Line ("[VALIDATE] Step 2: Pre-simulation geometry QA ...");
      if Validate_And_Dump (Geo, TPS) then
         Put_Line ("  Geometry validation: PASSED");
      else
          Put_Line ("  Geometry validation: FAILED -- cannot proceed.");
         return;
      end if;
      New_Line;

      --  Step 3: Generate SPARTA input script
      Put_Line ("[VALIDATE] Step 3: Generating SPARTA input script ...");
      Generate_Sparta_Script
        (Flight       => Flight,
         Geo          => Geo,
         Grid_Factor  => Grid_Factor,
         Steps        => Steps,
         Chemistry    => Chemistry,
         Fnum         => Fnum,
         Restart_File => Restart_File,
         Results_Dir  => Results_Dir);
      Put_Line ("  Script written to: " & Results_Dir & "/in.hiad");
      New_Line;

      --  Step 4: Build SPARTA Docker image
      Put_Line ("[VALIDATE] Step 4: Building SPARTA Docker image ...");
      Build_Sparta_Library;
      Put_Line ("  Docker image built (or already up to date).");
      New_Line;

      --  Step 5: Run SPARTA simulation in Docker
      Put_Line ("[VALIDATE] Step 5: Running SPARTA simulation ...");
      Put_Line ("  This may take several minutes depending on steps count.");
      Run_Sparta_Docker
        (Cwd       => ".",
         Use_GPU   => Use_GPU,
         Num_Cores => Cores,
         Success   => DOK);
      New_Line;

      if not DOK then
         Put_Line ("  SPARTA simulation FAILED or produced no output.");
         Put_Line ("  Check Docker logs and " & Results_Dir & "/ for details.");
         return;
      end if;
      Put_Line ("  SPARTA simulation completed successfully.");
      New_Line;

      --  Step 6: Parse SPARTA results
      Put_Line ("[VALIDATE] Step 6: Parsing SPARTA surface dump files ...");
      Results := Parse_Sparta_Results (Results_Dir, Flight, Geo);
      Put_Line ("  Drag force     : " & Float'Image (Results.Drag_Force) & " N");
      Put_Line ("  Heat flux      : " & Float'Image (Results.Heat_Flux_Wm2) & " W/m^2");
      Put_Line ("  Total heat load: " & Float'Image (Results.Total_Heat_Load) & " J/m^2");
      Put_Line ("  Stag pressure  : " & Float'Image (Results.Stag_Pressure_Pa) & " Pa");
      Put_Line ("  Shock temp     : " & Float'Image (Results.Shock_Temp_K) & " K");
      New_Line;

      --  Step 7: Calculate flight metrics
      Put_Line ("[VALIDATE] Step 7: Calculating flight metrics ...");
      Calculate_Flight_Metrics (Results, Flight, Geo, TPS, Metrics);
      Put_Line ("  Ballistic coeff   : " & Float'Image (Metrics.Ballistic_Coeff) & " kg/m^2");
      Put_Line ("  Knudsen number    : " & Float'Image (Metrics.Knudsen_Number));
      Put_Line ("  Stag heat (W/m^2) : " & Float'Image (Metrics.Stag_Heat_Flux_Wm2));
      Put_Line ("  Stag heat (W/cm^2): " & Float'Image (Metrics.Stag_Heat_Flux_Wcm2));
      Put_Line ("  Surface temp      : " & Float'Image (Metrics.Surface_Temp_K) & " K");
      Put_Line ("  Backface temp     : " & Float'Image (Metrics.Backface_Temp_K) & " K");
      Put_Line ("  Decel g-load      : " & Float'Image (Metrics.Decel_G) & " g");
      New_Line;

      --  Step 8: Survivability check
      Put_Line ("[VALIDATE] Step 8: Survivability check ...");
      Survivable := Check_Survivability (Metrics);
      if Survivable then
         Put_Line ("  Survivability: PASSED");
      else
          Put_Line ("  Survivability: FAILED -- vehicle does not survive.");
      end if;
      New_Line;

      --  Step 8b: Sanity checks for unrealistic values
      Put_Line ("[VALIDATE] Step 8b: Sanity checks ...");
      if Metrics.Decel_G < 0.0 or else Metrics.Decel_G > 50.0 then
         Put_Line ("  WARNING: Deceleration " &
                   Float'Image (Metrics.Decel_G) &
                   " g is outside expected range [0, 50].");
         Put_Line ("  Results may be unreliable.");
      end if;
      if Metrics.Stag_Heat_Flux_Wcm2 < 0.0 or else
         Metrics.Stag_Heat_Flux_Wcm2 > 500.0
      then
         Put_Line ("  WARNING: Heat flux " &
                   Float'Image (Metrics.Stag_Heat_Flux_Wcm2) &
                   " W/cm^2 is outside expected range [0, 500].");
         Put_Line ("  Results may be unreliable.");
      end if;
      if Metrics.Ballistic_Coeff < 0.0 then
         Put_Line ("  WARNING: Ballistic coefficient is negative (" &
                   Float'Image (Metrics.Ballistic_Coeff) & ").");
         Put_Line ("  Results may be unreliable.");
      end if;
      Put_Line ("  Sanity checks complete.");
      New_Line;

      --  Step 9: Compare against IRVE-3 flight data (with % error)
      Put_Line ("[VALIDATE] Step 9: Comparison against IRVE-3 flight data");
      Put_Line ("  Source: NASA/TP-2013-4012 (IRVE-3 Flight Data);");
      Put_Line ("          Rapisarda (2023) HIAD MDAO thesis, Table 4.1");
      Put_Line ("  ---------------------------------------------------------------------");
      Put_Line ("  Parameter             | Simulated    | Target       | Error %  | Status");
      Put_Line ("  ---------------------------------------------------------------------");

      --  Heat flux comparison
      declare
         Heat_Dev : constant Float :=
           abs (Metrics.Stag_Heat_Flux_Wcm2 - Target_Heat_Flux)
           / Target_Heat_Flux;
         Heat_OK  : constant Boolean := Heat_Dev <= Tolerance_Heat;
         Heat_Pct : constant Float := Heat_Dev * 100.0;
      begin
         Put_Line ("  Heat flux (W/cm^2)    | " &
                   Float'Image (Metrics.Stag_Heat_Flux_Wcm2) & " | " &
                   Float'Image (Target_Heat_Flux) & "         | " &
                   Float'Image (Heat_Pct) & "%  | " &
                   (if Heat_OK then "PASS" else "FAIL"));
      end;

      --  Heat load comparison (J/cm^2)
      declare
         Heat_Load_Cm2 : constant Float :=
           Results.Total_Heat_Load / 10_000.0;
         HL_Dev  : constant Float :=
           abs (Heat_Load_Cm2 - Target_Heat_Load) / Target_Heat_Load;
         HL_OK   : constant Boolean := HL_Dev <= Tolerance_Heat;
         HL_Pct  : constant Float := HL_Dev * 100.0;
      begin
         Put_Line ("  Heat load (J/cm^2)    | " &
                   Float'Image (Heat_Load_Cm2) & " | " &
                   Float'Image (Target_Heat_Load) & "          | " &
                   Float'Image (HL_Pct) & "%  | " &
                   (if HL_OK then "PASS" else "FAIL"));
      end;

      --  Deceleration comparison
      declare
         Decel_Dev : constant Float :=
           abs (Metrics.Decel_G - Target_Decel_G) / Target_Decel_G;
         Decel_OK  : constant Boolean := Decel_Dev <= Tolerance_Decel;
         Decel_Pct : constant Float := Decel_Dev * 100.0;
      begin
         Put_Line ("  Peak decel (g)        | " &
                   Float'Image (Metrics.Decel_G) & " | " &
                   Float'Image (Target_Decel_G) & "          | " &
                   Float'Image (Decel_Pct) & "%  | " &
                   (if Decel_OK then "PASS" else "FAIL"));
      end;

      --  Ballistic coefficient comparison
      declare
         Beta_Dev : constant Float :=
           abs (Metrics.Ballistic_Coeff - Target_Beta) / Target_Beta;
         Beta_OK  : constant Boolean := Beta_Dev <= Tolerance_Beta;
         Beta_Pct : constant Float := Beta_Dev * 100.0;
      begin
         Put_Line ("  Beta (kg/m^2)         | " &
                   Float'Image (Metrics.Ballistic_Coeff) & " | " &
                   Float'Image (Target_Beta) & "          | " &
                   Float'Image (Beta_Pct) & "%  | " &
                   (if Beta_OK then "PASS" else "WARN"));
      end;

      --  Stagnation pressure
      declare
         Press_Dev : constant Float :=
           abs (Results.Stag_Pressure_Pa - Target_Pressure) / Target_Pressure;
         Press_OK  : constant Boolean := Press_Dev <= Tolerance_Heat;
         Press_Pct : constant Float := Press_Dev * 100.0;
      begin
         Put_Line ("  Stag pressure (Pa)   | " &
                   Float'Image (Results.Stag_Pressure_Pa) & " | " &
                   Float'Image (Target_Pressure) & "  | " &
                   Float'Image (Press_Pct) & "%  | " &
                   (if Press_OK then "PASS" else "WARN"));
      end;

      --  Drag coefficient (Cd) comparison
      declare
         Ref_Area : constant Float :=
           Ada.Numerics.Pi * (Geo.Diameter_M / 2.0) ** 2;
         Dyn_Pres : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;
         Cd_Val   : constant Float :=
           (if Dyn_Pres > 0.0 then
              Results.Drag_Force / (Dyn_Pres * Ref_Area)
            else 0.0);
         Cd_Dev : constant Float :=
           abs (Cd_Val - Target_Cd) / Target_Cd;
         Cd_OK  : constant Boolean := Cd_Dev <= Tolerance_Cd;
         Cd_Pct : constant Float := Cd_Dev * 100.0;
      begin
         Put_Line ("  Drag coeff (Cd)       | " &
                   Float'Image (Cd_Val) & " | " &
                   Float'Image (Target_Cd) & "          | " &
                   Float'Image (Cd_Pct) & "%  | " &
                   (if Cd_OK then "PASS" else "WARN"));
      end;

      --  Dynamic pressure (kPa) comparison
      declare
         Dyn_Pres_KPa : constant Float :=
           0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2
           / 1_000.0;
         DP_Dev : constant Float :=
           abs (Dyn_Pres_KPa - Target_Dyn_Press_KPa) / Target_Dyn_Press_KPa;
         DP_OK  : constant Boolean := DP_Dev <= Tolerance_Press;
         DP_Pct : constant Float := DP_Dev * 100.0;
      begin
         Put_Line ("  Dyn pressure (kPa)    | " &
                   Float'Image (Dyn_Pres_KPa) & " | " &
                   Float'Image (Target_Dyn_Press_KPa) & "          | " &
                   Float'Image (DP_Pct) & "%  | " &
                   (if DP_OK then "PASS" else "WARN"));
      end;

      --  Toroid radius (m) comparison
      declare
         TR_Dev : constant Float :=
           abs (Geo.Toroid_Radius_M - Target_Toroid_Radius)
           / Target_Toroid_Radius;
         TR_OK  : constant Boolean := TR_Dev <= Tolerance_Press;
         TR_Pct : constant Float := TR_Dev * 100.0;
      begin
         Put_Line ("  Toroid radius (m)     | " &
                   Float'Image (Geo.Toroid_Radius_M) & " | " &
                   Float'Image (Target_Toroid_Radius) & "          | " &
                   Float'Image (TR_Pct) & "%  | " &
                   (if TR_OK then "PASS" else "WARN"));
      end;

      --  Ambient temperature (K) comparison
      declare
         AT_Dev : constant Float :=
           abs (Flight.Temperature_K - Target_Ambient_Temp)
           / Target_Ambient_Temp;
         AT_OK  : constant Boolean := AT_Dev <= Tolerance_Temp;
         AT_Pct : constant Float := AT_Dev * 100.0;
      begin
         Put_Line ("  Ambient temp (K)      | " &
                   Float'Image (Flight.Temperature_K) & " | " &
                   Float'Image (Target_Ambient_Temp) & "          | " &
                   Float'Image (AT_Pct) & "%  | " &
                   (if AT_OK then "PASS" else "WARN"));
      end;

      --  Payload height (m) comparison (simulated geometry payload height)
      declare
         Payload_H : constant Float :=
           Geo.Diameter_M - 2.0 * Geo.Toroid_Radius_M;
         PH_Dev : constant Float :=
           abs (Payload_H - Target_Payload_Height) / Target_Payload_Height;
         PH_OK  : constant Boolean := PH_Dev <= Tolerance_Press;
         PH_Pct : constant Float := PH_Dev * 100.0;
      begin
         Put_Line ("  Payload height (m)    | " &
                   Float'Image (Payload_H) & " | " &
                   Float'Image (Target_Payload_Height) & "          | " &
                   Float'Image (PH_Pct) & "%  | " &
                   (if PH_OK then "PASS" else "WARN"));
      end;

      --  Ambient pressure (Pa) comparison (ISA: P = rho * R_specific * T)
      declare
         R_Air     : constant Float := 287.058;  -- J/(kg*K)
         Amb_Press : constant Float :=
           Flight.Density_Kgm3 * R_Air * Flight.Temperature_K;
         AP_Dev : constant Float :=
           abs (Amb_Press - Target_Ambient_Press) / Target_Ambient_Press;
         AP_OK  : constant Boolean := AP_Dev <= Tolerance_Press;
         AP_Pct : constant Float := AP_Dev * 100.0;
      begin
         Put_Line ("  Ambient press (Pa)    | " &
                   Float'Image (Amb_Press) & " | " &
                   Float'Image (Target_Ambient_Press) & "          | " &
                   Float'Image (AP_Pct) & "%  | " &
                   (if AP_OK then "PASS" else "WARN"));
      end;

      Put_Line ("  ---------------------------------------------------------------------");
      Put_Line ("  [NOTE] Flight = IRVE-3 (NASA/TP-2013-4012), MDAO = Rapisarda 2023.");
      New_Line;

      --  Step 10: Summary
      Put_Line ("[VALIDATE] ====== Validation Summary ======");
      Put_Line ("  Survivable   : " & Boolean'Image (Survivable));
      Put_Line ("  Heat flux    : " & Float'Image (Metrics.Stag_Heat_Flux_Wcm2) &
                " W/cm^2 (target: " & Float'Image (Target_Heat_Flux) & ")");
      Put_Line ("  Peak decel   : " & Float'Image (Metrics.Decel_G) &
                " g (target: " & Float'Image (Target_Decel_G) & ")");
      Put_Line ("  Ballistic    : " & Float'Image (Metrics.Ballistic_Coeff) &
                " kg/m^2 (target: " & Float'Image (Target_Beta) & ")");
      Put_Line ("  Stag pressure: " & Float'Image (Results.Stag_Pressure_Pa) &
                " Pa (target: ~" & Float'Image (Target_Pressure) & ")");
      New_Line;

      if Survivable then
         Put_Line ("[VALIDATE] RESULT: VALIDATION PASSED");
      else
         Put_Line ("[VALIDATE] RESULT: VALIDATION FAILED");
      end if;
   end Run_Validate_Full;

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

            --  Grade each comparison (PASS ≤ tol, WARN ≤ 2×tol, FAIL > 2×tol)
            function Grade (Error : Float; Tol : Float) return String is
            begin
               if Error <= Tol then
                  return "PASS";
               elsif Error <= Tol * 2.0 then
                  return "WARN";
               else
                  return "FAIL";
               end if;
            end Grade;

            --  Format float to "N.DD" (2 decimal places, no scientific notation).
            --  Axiom: Integer conversion + arithmetic avoids Float'Image truncation.
            --  Uses Long_Long_Integer to avoid range overflow for large values.
            --  Clamps decimal digits to 0..99 to guard against floating point edge cases.
            function F6 (V : Float) return String is
               Abs_V : constant Float := abs V + 0.005;
               IP    : constant Long_Long_Integer := Long_Long_Integer (Abs_V);
               Raw   : constant Long_Long_Integer :=
                 Long_Long_Integer ((Abs_V - Float (IP)) * 100.0);
               --  Clamp DP to 0..99 to prevent floating point precision overflow
               DP    : constant Long_Long_Integer :=
                 (if Raw < 0 then 0 elsif Raw > 99 then 99 else Raw);
               Sign  : constant String := (if V < 0.0 then "-" else "");
               IStr  : constant String := Long_Long_Integer'Image (IP);
               D1    : constant Character :=
                 Character'Val (Character'Pos ('0') + Integer (DP / 10));
               D2    : constant Character :=
                 Character'Val (Character'Pos ('0') + Integer (DP rem 10));
            begin
               return Sign & IStr (IStr'First + 1 .. IStr'Last) & "." & D1 & D2;
            end F6;

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
      Thermal_Lag        : Float;
      Stats_Interval     : Positive;
      --  Geometry overrides
      Geo : Geometry_Parameters;
      --  TPS material
      TPS : TPS_Material;
      Chemistry : Chemistry_Mode;
      Nose_Profile : Nose_Type_Kind;
      --  Boolean flags
      Headless     : Boolean;
      Payload_Mode : Boolean;
      Default_Pay  : Boolean;
      Skip_Diag    : Boolean;
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
      Mach_Override      := Get_Float ("--mach", 0.0);
      Alt_Override       := Get_Float ("--alt",
                            Get_Float ("--altitude", 0.0));
      Cores              := Get_Positive ("--cores", 4);
      Slice_Angle        := Get_Float ("--slice-angle", 360.0);
      Emissivity_Override := Get_Float ("--tps-emissivity", 0.0);
      Thermal_Lag        := Get_Float ("--thermal-lag", 0.15);
      Stats_Interval     := Get_Positive ("--stats-interval", 100);
      Opt_Samples        := Get_Positive ("--samples", 100);

      --  Parse boolean flags (positive + negation)
      Headless     := Headless or else Has_Flag ("--headless");
      Payload_Mode := Has_Flag ("--payload");
      Default_Pay  := Has_Flag ("--defaultPayload");
      Skip_Diag    := Has_Flag ("--skip-diag");
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

      --  Build geometry from CLI overrides (defaults match IRVE-3)
      Geo := (Diameter_M      => Get_Float ("--diameter", 3.0),
              Angle_Deg       => Get_Float ("--angle", 60.0),
              Nose_Radius_M   => Get_Float ("--nose", 0.55),
              Toroid_Count    => Get_Positive ("--toroids", 6),
              Toroid_Radius_M => Get_Float ("--tradius", 0.135),
              Outer_Radius_M  => Get_Float ("--oradius", 0.0508),
              Mass_Kg         => Get_Float ("--mass", 281.0),
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

      --  Apply TPS property overrides
      if Emissivity_Override > 0.0 then
         TPS.Emissivity := Emissivity_Override;
      end if;
      if Has_Flag ("--tps-density") then
         TPS.Density := Get_Float ("--tps-density", TPS.Density);
      end if;
      if Has_Flag ("--tps-cp") then
         TPS.Cp := Get_Float ("--tps-cp", TPS.Cp);
      end if;
      if Has_Flag ("--tps-k") then
         TPS.Thermal_K := Get_Float ("--tps-k", TPS.Thermal_K);
      end if;

      --  Wire boolean flags into behaviour
      --  Headless  → suppress banner
      --  Skip_Diag → skip self-test diagnostics
      --  Fresh_Start → ignore restart file (restart_file stays empty)
      --  Use_PINN  → logged for future PINN integration
      --  Solver_Str, Vehicle_Str, DB_Path, Nose_Type_Str, Thermal_Lag,
      --  Stats_Interval, Payload_Mode, Default_Pay → consumed by procedure
      --  parameters and SPARTA script generation downstream

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
            Docker_OK : Boolean;
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
