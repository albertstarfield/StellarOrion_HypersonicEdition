--  StellarOrion_HypersonicEdition — Run History / Database Bridge
--  Ada 2012 / SPARK 2014
--  SPARK_Mode => Off : performs file I/O and SQLite bridging.
--
--  CSV-based portable storage with file locking for concurrent access.
--  File layout:
--    <db_dir>/runs.csv          — one row per simulation run
--    <db_dir>/samples.csv       — one row per DoE sample
--    <db_dir>/.lock             — PID/timestamp lock file
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;
with Ada.Strings.Unbounded; use Ada.Strings.Unbounded;

package StellarOrion_History is
   pragma SPARK_Mode (Off);
   --  extern: run-history API backed by non-SPARK runtime libs (Unbounded_String, Directories)

   -- -----------------------------------------------------------------
   --  Run Record (in-memory representation of a CSV row)
   -- -----------------------------------------------------------------

   type Run_Record is record
      Name      : Unbounded_String := Null_Unbounded_String;
      Status    : Unbounded_String := To_Unbounded_String ("completed");
      Progress  : Float            := 1.0;
      Flight    : Flight_Parameters;
      Geo       : Geometry_Parameters;
      Results   : Simulation_Results;
      Metrics   : Flight_Metrics;
      Solver    : Solver_Kind      := SPARTA;
      Chemistry : Chemistry_Mode   := Five_Species;
   end record;

   Max_Run_Count : constant := 1000;
   type Run_Array is array (1 .. Max_Run_Count) of Run_Record;

   type Run_Set is record
      Data  : Run_Array;
      Count : Natural := 0;
   end record;

   -- -----------------------------------------------------------------
   --  Database Lifecycle
   -- -----------------------------------------------------------------

   --  Initialise (or open) the CSV database at Database_Path.
   --  Creates directory and header rows if they don't exist.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Init_DB (Database_Path : String);

   -- -----------------------------------------------------------------
   --  Persistence: Full Runs
   -- -----------------------------------------------------------------

   --  Save a complete simulation run to the CSV database.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Save_Run
     (Name      : String;
      Flight    : Flight_Parameters;
      Geo       : Geometry_Parameters;
      TPS       : TPS_Material;
      Results   : Simulation_Results;
      Metrics   : Flight_Metrics;
      Solver    : Solver_Kind;
      Chemistry : Chemistry_Mode);

   --  Load a run by name.  Returns False if not found.
   --  Populates all out parameters on success.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Load_Run
     (Name      : String;
      Flight    : out Flight_Parameters;
      Geo       : out Geometry_Parameters;
      TPS       : out TPS_Material;
      Results   : out Simulation_Results;
      Metrics   : out Flight_Metrics;
      Solver    : out Solver_Kind;
      Chemistry : out Chemistry_Mode) return Boolean;

   --  Delete a run by name.  Returns True if the run was found and removed.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Delete_Run (Name : String) return Boolean;

   --  Return all saved runs (up to Max_Run_Count).
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Get_All_Runs return Run_Set;

   --  Update the progress field of a named run (0.0 .. 1.0).
   --  Also optionally sets the status string.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Update_Run_Progress
     (Name     : String;
      Progress : Float;
      Status   : String := "");

   --  Insert or update a draft run.  If a draft with the same name
   --  exists, it is overwritten; otherwise a new draft row is appended.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Upsert_Draft
     (Name     : String;
      Flight   : Flight_Parameters;
      Geo      : Geometry_Parameters;
      TPS      : TPS_Material;
      Results  : Simulation_Results;
      Metrics  : Flight_Metrics;
      Solver   : Solver_Kind;
      Chem     : Chemistry_Mode;
      Progress : Float);

   -- -----------------------------------------------------------------
   --  Persistence: Design-of-Experiments Samples
   -- -----------------------------------------------------------------

   --  Save a single DoE sample point.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Save_Sample
     (Sample_Index : Positive;
      Geo          : Geometry_Parameters;
      Results      : Simulation_Results;
      Metrics      : Flight_Metrics);

   -- -----------------------------------------------------------------
   --  Queries
   -- -----------------------------------------------------------------

   --  Return the total number of saved runs.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Run_Count return Natural;

   --  Return the total number of saved DoE samples.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Sample_Count return Natural;

end StellarOrion_History;
