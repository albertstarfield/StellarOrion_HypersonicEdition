--  StellarOrion_HypersonicEdition — Root Project Package
--  Ada 2012 / SPARK 2014
--  This is the root package visible to all child units.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Project is
   pragma SPARK_Mode (On);

   --  The Main_Procedure itself must be SPARK_Mode => Off because it
   --  performs I/O, subprocess dispatching, and GUI launching.
   --  It is declared here but its body is in the .adb.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Main_Program
     with SPARK_Mode => Off;

   --  STC coverage wrapper.
   procedure Test_Main_Program;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Main_Program", Test_Main_Program'Access);
end StellarOrion_Project;
