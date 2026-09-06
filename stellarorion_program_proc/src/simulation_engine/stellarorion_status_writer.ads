--  StellarOrion_HypersonicEdition — Sidecar Status Writer
--  Writes .status.json for the Python sidecar UI to poll.
--  Ada 2012 / SPARK 2014
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Status_Writer is
   pragma SPARK_Mode (On);

   --  Status codes matching sidecar_ui.py SimulationState
   type Status_Kind is
     (Status_Idle,
      Status_Running,
      Status_Completed,
      Status_Error);

   --  AXIOMS: Write a JSON status file that the sidecar monitor polls every 2 s.
   --    Dir_Path : directory where .status.json is written (e.g. "data/runs")
   --    Run_Name : human-readable run label
   --    Kind     : current status (idle/running/completed/error)
   --    Progress : 0.0 .. 1.0 fraction complete
   --    Results  : key-value pairs to embed in "results" object
   --    Metrics  : key-value pairs to embed in "metrics" object
   --  THEORIES: Normal termination writes .status.json to Dir_Path.
   --  APPLICATIONS: Ada.Text_IO file I/O with Ada.Directories path construction.
   --  CITATIONS: Ada 2012 RM A.4.8 (Text_IO), Ada 2012 RM D.4 (Direct_IO).
   procedure Write_Status
     (Dir_Path : String;
      Run_Name : String;
      Kind     : Status_Kind;
      Progress : Float;
      Results  : String := "";
      Metrics  : String := "")
     with Pre  => Dir_Path'Length > 0 and Run_Name'Length > 0,
          Post => True;

   --  AXIOMS: Remove the .status.json file (call on shutdown/cleanup).
   --  THEORIES: Normal termination deletes the status file if it exists.
   --  APPLICATIONS: Ada.Directories.Delete_File with exception handling.
   --  CITATIONS: Ada 2012 RM D.4 (Directories).
   procedure Clear_Status (Dir_Path : String)
     with Pre  => Dir_Path'Length > 0,
          Post => True;

   --  AXIOMS: Test stub for Write_Status — writes to a temp dir and verifies.
   procedure Test_Write_Status
     with Pre => True, Post => True;

   --  AXIOMS: Test stub for Clear_Status — creates and removes a temp file.
   --  STC coverage wrapper.
   procedure Test_Clear_Status
     with Pre => True, Post => True;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Clear_Status", Test_Clear_Status'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Write_Status", Test_Write_Status'Access);
end StellarOrion_Status_Writer;
