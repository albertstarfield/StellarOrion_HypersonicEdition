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
   procedure Run_GridIndep_Test ;
   procedure Run_Demo ;
   procedure Run_Validate_Only
     (Geo_In : Geometry_Parameters := (others => <>);
      TPS_In : TPS_Material := (others => <>))
   ;

   procedure Run_Test_Baseline
     (Steps      : Positive := 1_000;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   ;
   procedure Run_Test_Sample
     (Steps      : Positive := 1_000;
      Geo_In     : Geometry_Parameters := (others => <>);
      TPS_In     : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0)
   ;
   procedure Run_Test_PINN_Calibration (Steps : Positive := 1_000) ;
   procedure Run_Test_Sparta_Integration ;
   procedure Run_Test_PyFluent_Integration
     (SSH_Host : String;
      SSH_User : String;
      SSH_Pass : String;
      SSH_Key  : String)
   ;
   procedure Run_Test_PyAnsys_Integration ;
   procedure Run_Test_OpenFOAM_Integration ;

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
