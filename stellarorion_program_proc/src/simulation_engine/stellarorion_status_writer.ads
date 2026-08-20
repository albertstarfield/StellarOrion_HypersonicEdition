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

   --  Write a JSON status file that the sidecar monitor polls every 2 s.
   --  Dir_Path : directory where .status.json is written (e.g. "data/runs")
   --  Run_Name : human-readable run label
   --  Kind     : current status (idle/running/completed/error)
   --  Progress : 0.0 .. 1.0 fraction complete
   --  Results  : key-value pairs to embed in "results" object
   --  Metrics  : key-value pairs to embed in "metrics" object
   procedure Write_Status
     (Dir_Path : String;
      Run_Name : String;
      Kind     : Status_Kind;
      Progress : Float;
      Results  : String := "";
      Metrics  : String := "");

   --  Remove the .status.json file (call on shutdown/cleanup)
   procedure Clear_Status (Dir_Path : String);

end StellarOrion_Status_Writer;
