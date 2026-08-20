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
   procedure Main_Program
     with SPARK_Mode => Off;

end StellarOrion_Project;
