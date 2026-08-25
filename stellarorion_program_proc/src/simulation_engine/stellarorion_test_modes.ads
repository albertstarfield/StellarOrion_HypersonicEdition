--  StellarOrion_Test_Modes — CLI test/demo mode procedures
--  Extracted verbatim from StellarOrion_Project at Decomposition Stage 4 —
--  see docs/PROJECT_DECOMPOSITION_PLAN.md. Pure move: no behavior change.
--
--  extern: spawns standalone Python/Docker sidecars per
--  docs/PYTHON_SIDECAR_EXCEPTIONS.md section 2; outside SPARK subset.

with StellarOrion_Types;      use StellarOrion_Types;

package StellarOrion_Test_Modes is

   pragma SPARK_Mode (Off);
   --  extern: sidecar interop; outside SPARK subset

   procedure Run_GetIRVE3_Baseline ;
   procedure Run_CompareNoses
     (Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0;
      Geo_In        : Geometry_Parameters := (others => <>);
      TPS_In        : TPS_Material := (others => <>))
   ;
   --  Analytical grid-factor sweep; prints the validated optimum (0.7)
   --  without launching any SPARTA runs.
   procedure Run_GridIndep_Test ;
   --  Quick demo: Mach 10 / 52 km flight with IRVE-3 defaults and
   --  analytically derived flight metrics.
   procedure Run_Demo ;
   --  Pre-simulation geometry/TPS QA gates only; no solver is invoked.
   procedure Run_Validate_Only
     (Geo_In : Geometry_Parameters := (others => <>);
      TPS_In : TPS_Material := (others => <>))
   ;

   --  Baseline SPARTA run reproducing the IRVE-3 reference case.
   procedure Run_Test_Baseline
     (Steps      : Positive := 1_000;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   ;
   --  Single SPARTA sample run with the full 11-metric comparison report.
   procedure Run_Test_Sample
     (Steps      : Positive := 1_000;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   ;
   --  Compare-calibrate delegated to the Python DeepXDE PINN sidecar.
   procedure Run_Test_PINN_Calibration (Steps : Positive := 1_000) ;
   --  End-to-end SPARTA pipeline integration check.
   procedure Run_Test_Sparta_Integration ;
   --  PyFluent sidecar integration over SSH using the supplied host,
   --  user, password, and key path.
   procedure Run_Test_PyFluent_Integration
     (SSH_Host : String;
      SSH_User : String;
      SSH_Pass : String;
      SSH_Key  : String)
   ;
   --  PyAnsys sidecar integration check.
   procedure Run_Test_PyAnsys_Integration ;
   --  OpenFOAM solver-path integration check.
   procedure Run_Test_OpenFOAM_Integration ;

   --  Full validation pipeline: SPARTA run with explicit grid factor,
   --  chemistry model, core count/GPU toggle, and output locations.
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

   --  Format float to "N.DD" (2 decimal places, no scientific notation).
   function F6 (V : Float) return String;

   --  Grade each comparison (PASS <= tol, WARN <= 2*tol, FAIL > 2*tol).
   function Grade (Error : Float; Tol : Float) return String;

end StellarOrion_Test_Modes;
