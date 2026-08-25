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
--  Decomposition Stage 1: pure CLI helpers moved to StellarOrion_Cli
with StellarOrion_Cli;            use StellarOrion_Cli;
--  Decomposition Stage 2: runtime guards moved to StellarOrion_Runtime_Guard
with StellarOrion_Runtime_Guard;  use StellarOrion_Runtime_Guard;
--  Decomposition Stage 3: self-test suite moved to StellarOrion_Self_Test
with StellarOrion_Self_Test;      use StellarOrion_Self_Test;
with StellarOrion_Test_Modes; use StellarOrion_Test_Modes;
with StellarOrion_Reports; use StellarOrion_Reports;
with StellarOrion_Optimize;      use StellarOrion_Optimize;

--  Ada.IO_Exceptions / Ada.Numerics are referenced via expanded names only
--  (e.g. Ada.Numerics.Pi), hence no use-clauses here.
with Ada.IO_Exceptions;
with GNAT.OS_Lib;        use GNAT.OS_Lib;

package body StellarOrion_Project is
   pragma SPARK_Mode (Off);
   --  extern: spawns Python sidecar process via GNAT.OS_Lib; outside SPARK subset

   --  Status directory for sidecar .status.json

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


   --  Run_Optimize extracted verbatim to StellarOrion_Optimize at
   --  Decomposition Stage 6 -- see docs/PROJECT_DECOMPOSITION_PLAN.md.


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
   --  Run_Compare_Calibrate / Run_GridIndep_Sparta extracted verbatim to
   --  StellarOrion_Reports at Decomposition Stage 5 — see
   --  docs/PROJECT_DECOMPOSITION_PLAN.md.


   -- ==================================================================
   --  Grid Independency Test (SPARTA-backed)

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
