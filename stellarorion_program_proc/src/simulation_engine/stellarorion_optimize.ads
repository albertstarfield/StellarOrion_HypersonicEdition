--  StellarOrion_Optimize -- optimization driver mode (--optimize CLI path)
--  Extracted verbatim from StellarOrion_Project at Decomposition Stage 6 --
--  see docs/PROJECT_DECOMPOSITION_PLAN.md. Pure move: no behavior change.

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Optimize is

   pragma SPARK_Mode (Off);
   --  extern: orchestrates GA/metamodel runs writing run artifacts;
   --  outside SPARK subset

   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
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
   ;

end StellarOrion_Optimize;
