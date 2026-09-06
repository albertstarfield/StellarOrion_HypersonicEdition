--  StellarOrion_Optimize -- optimization driver mode (--optimize CLI path)
--  Extracted verbatim from StellarOrion_Project at Decomposition Stage 6 --
--  see docs/PROJECT_DECOMPOSITION_PLAN.md. Pure move: no behavior change.

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Optimize is

   pragma SPARK_Mode (Off);
   --  extern: orchestrates GA/metamodel runs writing run artifacts;
   --  outside SPARK subset

   --  AXIOMS: Optimization driver mode (--optimize CLI path).
   --  THEORIES: Runs GA/metamodel optimization loop with configurable parameters.
   --  APPLICATIONS: Orchestrates StellarOrion_Optimization and StellarOrion_Status_Writer.
   --  CITATIONS: Goldberg (1989) Genetic Algorithms in Search, Optimization, and Machine Learning.
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
     with Pre  => Samples_In > 0 and Steps > 0,
          Post => True;

   --  AXIOMS: Test stub for Run_Optimize — exercises optimization path.
   --  STC coverage wrapper.
   procedure Test_Run_Optimize
     with Pre => True, Post => True;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Run_Optimize", Test_Run_Optimize'Access);
end StellarOrion_Optimize;
