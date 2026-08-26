--  StellarOrion_Reports — calibration-comparison & grid-independency reports
--  Extracted verbatim from StellarOrion_Project at Decomposition Stage 5 —
--  see docs/PROJECT_DECOMPOSITION_PLAN.md. Pure move: no behavior change.
--
--  extern: reporting modes orchestrate SPARTA runs via StellarOrion_Test_Modes;
--  outside SPARK subset.

with StellarOrion_Types;      use StellarOrion_Types;
package StellarOrion_Reports is

   pragma SPARK_Mode (Off);
   --  extern: orchestrates verified-off run modes; outside SPARK subset

   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Run_Compare_Calibrate
     (Geo_In        : Geometry_Parameters := (others => <>);
      TPS_In        : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0;
      Steps         : Positive := 1_000)
   ;

   --  Grid-independency sweep backed by real SPARTA runs: varies the grid
   --  factor over the tested range and compares derived metrics per point.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
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
   ;

   --  STC coverage wrapper.
   procedure Test_Run_Compare_Calibrate;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Run_GridIndep_Sparta;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Run_Compare_Calibrate", Test_Run_Compare_Calibrate'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Run_GridIndep_Sparta", Test_Run_GridIndep_Sparta'Access);
end StellarOrion_Reports;
