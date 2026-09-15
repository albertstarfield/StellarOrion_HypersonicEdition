--  StellarOrion_HypersonicEdition — Pipeline Checkpoint (Spec)
-- Parity protection: metadata/stellarorion_pipeline_checkpoint.meta.json (RS+GC parity)
--  Ada 2012
--  Save/Resume tracker for the 4-step StellarOrion pipeline:
--    Step 1: SPARTA   — DSMC simulation (Docker/colima)
--    Step 2: Kriging  — Spatial denoising of SPARTA grid output
--    Step 3: PINN     — Physics-informed neural network training
--    Step 4: MoP      — Metamodel Prognosis (virtual sample generation)
--
--  If the pipeline is interrupted (crash, power loss, timeout), the checkpoint
--  file allows resume from the last completed step without re-running prior steps.
--
--  CHECKPOINT FILE FORMAT (line-based, not JSON):
--    VERSION=1
--    PIPELINE_ID=run-20260903
--    CREATED_AT=2026-09-03T12:00:00Z
--    UPDATED_AT=2026-09-03T12:05:00Z
--    STEP_SPARTA=completed
--    STEP_SPARTA_COMPLETED=2026-09-03T12:03:00Z
--    STEP_SPARTA_FILES=grid.2200.out,grid.2200_denoised.out
--    STEP_KRIGING=pending
--    STEP_PINN=pending
--    STEP_MOP=pending
--    CONFIG_grid_file=grid.2200.out
--    CONFIG_iterations=2000
--
--  SPARK_Mode => Off (requires Ada.Text_IO, Ada.Calendar, and bounded strings).
--
--  Citations:
--    [Python310]  Python 3.10 documentation — json module, datetime module.
--                 https://docs.python.org/3/library/json.html
--                 https://docs.python.org/3/library/datetime.html
--    [ISO8601]    ISO 8601:2019 — Date and time format representation.
--    [Ada2012]    ISO/IEC 8652:2012 — Ada Reference Manual, RM 9.4 (protected types),
--                 RM 14 (exceptions), RM A.10 (Text_IO).
--    [Plimpton14] Plimpton, S.J. & Gallis, M.A. "SPARTA — Stochastic PArallel
--                 Rarefied- gas Time-accurate Analyser," 2014.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Pipeline_Checkpoint is
   pragma SPARK_Mode (Off);
   --  extern: Ada.Text_IO and Ada.Calendar are non-SPARK runtime libraries

   -- ==================================================================
   --  Pipeline Step Definitions
   -- ==================================================================
   --  The ordered pipeline steps; resume starts from the first non-completed step.
   --  AXIOM: Pipeline order is fixed: SPARTA → Kriging → PINN → MoP.

   subtype Step_Name is String (1 .. 8);
   --  Maximum step name length; all four steps fit in 8 characters.

   Step_Sparta  : constant Step_Name := "sparta  ";
   Step_Kriging : constant Step_Name := "kriging ";
   Step_PINN    : constant Step_Name := "pinn    ";
   Step_MoP     : constant Step_Name := "mop     ";

   --  Number of pipeline steps.
   Pipeline_Step_Count : constant Positive := 4;

   --  Ordered step names (index 1..4).
   type Pipeline_Step_Array is array (1 .. Pipeline_Step_Count) of Step_Name;

   --  The canonical ordered steps.
   Pipeline_Steps : constant Pipeline_Step_Array :=
     (Step_Sparta, Step_Kriging, Step_PINN, Step_MoP);

   -- ==================================================================
   --  Step Status Enumeration
   -- ==================================================================
   --  AXIOM: A step is in exactly one of four states: PENDING, RUNNING,
   --         COMPLETED, or FAILED.
   --  THEORIES: State transitions are: PENDING→RUNNING→COMPLETED or
   --            PENDING→RUNNING→FAILED.  RESET sets all steps to PENDING.

   type Step_Status is (Pending, Running, Completed, Failed);

   -- ==================================================================
   --  Checkpoint State Record
   -- ==================================================================
   --  Holds all mutable state for a single pipeline checkpoint.
   --  AXIOM: A checkpoint record is valid only after a successful Start call.

   Max_Pipeline_ID_Length : constant Positive := 128;
   Max_Timestamp_Length   : constant Positive := 32;
   Max_File_Path_Length   : constant Positive := 256;
   Max_Config_Key_Length  : constant Positive := 64;
   Max_Config_Val_Length  : constant Positive := 256;
   Max_Error_Length       : constant Positive := 256;
   Max_Output_Files       : constant Positive := 16;
   Max_File_Name_Length   : constant Positive := 128;
   Max_Config_Entries     : constant Positive := 32;

   subtype Pipeline_ID_String  is String (1 .. Max_Pipeline_ID_Length);
   subtype Timestamp_String    is String (1 .. Max_Timestamp_Length);
   subtype File_Path_String    is String (1 .. Max_File_Path_Length);
   subtype Config_Key_String   is String (1 .. Max_Config_Key_Length);
   subtype Config_Val_String   is String (1 .. Max_Config_Val_Length);
   subtype Error_String        is String (1 .. Max_Error_Length);
   subtype File_Name_String    is String (1 .. Max_File_Name_Length);

   --  Per-step data record.
   type Step_Data is record
      Status       : Step_Status := Pending;
      Completed_At : Timestamp_String := (others => ' ');
      Has_Completed_At : Boolean := False;
      Error        : Error_String := (others => ' ');
      Has_Error    : Boolean := False;
   end record;

   --  Output files for a step (fixed-size array with count).
   type Output_File_Array is array (1 .. Max_Output_Files) of File_Name_String;
   type Output_File_Count is new Natural range 0 .. Max_Output_Files;

   --  Step output files bundle.
   type Step_Output_Files is record
      Files : Output_File_Array := (others => (others => ' '));
      Count : Output_File_Count := 0;
   end record;

   --  Configuration key-value pair.
   type Config_Entry is record
      Key   : Config_Key_String := (others => ' ');
      Value : Config_Val_String := (others => ' ');
   end record;

   type Config_Entry_Array is array (1 .. Max_Config_Entries) of Config_Entry;

   --  Full checkpoint state.
   type Step_Data_Array is array (1 .. Pipeline_Step_Count) of Step_Data;
   type Step_Output_Files_Array is array (1 .. Pipeline_Step_Count) of Step_Output_Files;

   type Checkpoint_State is record
      --  Metadata
      Is_Initialized : Boolean := False;
      Pipeline_ID    : Pipeline_ID_String := (others => ' ');
      Pipeline_ID_Len : Natural := 0;
      Created_At     : Timestamp_String := (others => ' ');
      Updated_At     : Timestamp_String := (others => ' ');

      --  Per-step status and output files
      Steps       : Step_Data_Array;
      Step_Files  : Step_Output_Files_Array;

      --  Configuration (key-value pairs)
      Config       : Config_Entry_Array;
      Config_Count : Natural := 0;
   end record;

   -- ==================================================================
   --  Public Subprograms
   -- ==================================================================

   procedure Start
     (State       : in out Checkpoint_State;
      File_Path   : String;
      Pipeline_ID : String := "";
      Config      : String := "")
   with
     Post => State.Is_Initialized;
   --  Initialize a new pipeline run or resume an existing one.
   --  If the checkpoint file exists and has a prior run, it is preserved
   --  (resume mode). If not, a fresh checkpoint is created.
   --
   --  AXIOMS:
   --    Axiom 1: If File_Path does not exist, a fresh checkpoint is created.
   --    Axiom 2: If File_Path exists and contains valid step data, resume mode.
   --    Axiom 3: Pipeline_ID is auto-generated if empty.
   --  THEORIES:
   --    Theory 1: After Start, State.Is_Initialized = True.
   --  APPLICATIONS:
   --    Implementation: attempt file load; on success use existing state,
   --    otherwise create new state and save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.10 (Text_IO for file operations).
   --  TIMING ANALYSIS:
   --    WCET: ~1ms for file I/O + timestamp generation.

   function Is_Step_Completed
     (State     : Checkpoint_State;
      Step_Name : String) return Boolean
   with Pre => State.Is_Initialized;
   --  Check if a specific step has been completed.
   --
   --  AXIOMS:
   --    Axiom 1: A step is completed iff its status = Completed.
   --  THEORIES:
   --    Theory 1: Returns True if and only if the named step status is Completed.
   --  APPLICATIONS:
   --    Implementation: linear scan of Pipeline_Steps to find index, then
   --    compare status.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8 (Boolean type).
   --  TIMING ANALYSIS:
   --    WCET: ~100ns (linear scan, 4 steps max).

   function Get_Next_Step
     (State : Checkpoint_State) return Step_Name
   with Pre => State.Is_Initialized;
   --  Return the first step that is not yet completed, or the last step name
   --  if all are completed (caller must check Is_All_Completed separately).
   --
   --  AXIOMS:
   --    Axiom 1: Pipeline_Steps is ordered SPARTA→KRIGING→PINN→MOP.
   --    Axiom 2: Get_Next_Step returns the first step with status != Completed.
   --  THEORIES:
   --    Theory 1: If all steps are Completed, returns Step_Mop (caller checks
   --              Is_All_Completed to distinguish).
   --  APPLICATIONS:
   --    Implementation: iterate Pipeline_Steps, return first non-Completed.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8.1 (enumeration type iteration).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns (loop over 4 steps, string comparison).

   function Is_All_Completed
     (State : Checkpoint_State) return Boolean
   with Pre => State.Is_Initialized;
   --  Return True if every pipeline step is completed.
   --
   --  AXIOMS:
   --    Axiom 1: All steps completed iff every Steps(i).Status = Completed.
   --  THEORIES:
   --    Theory 1: Is_All_Completed = (Get_Next_Step returns a completed step)
   --              but is implemented directly for clarity.
   --  APPLICATIONS:
   --    Implementation: loop over all steps, return False on first non-Completed.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8 (Boolean type).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns.

   procedure Mark_Step_Running
     (State     : in out Checkpoint_State;
      File_Path : String;
      Step_Name : String)
   with Pre => State.Is_Initialized;
   --  Mark a step as currently running. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Mark_Step_Running sets Steps(i).Status := Running.
   --    Axiom 2: Save is called immediately after mutation.
   --  THEORIES:
   --    Theory 1: After Mark_Step_Running, Get_Step_Status returns Running.
   --  APPLICATIONS:
   --    Implementation: find step index, set status, call Save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 9.4 (protected types for thread safety — future work).
   --  TIMING ANALYSIS:
   --    WCET: ~2ms (mutation + file save).

   procedure Mark_Step_Completed
     (State       : in out Checkpoint_State;
      File_Path   : String;
      Step_Name   : String;
      Output_Files : String := "")
   with Pre => State.Is_Initialized;
   --  Mark a step as completed with optional output file list. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Mark_Step_Completed sets status := Completed and records timestamp.
   --    Axiom 2: Output_Files is a comma-separated list of file names.
   --  THEORIES:
   --    Theory 1: After Mark_Step_Completed, Is_Step_Completed returns True.
   --  APPLICATIONS:
   --    Implementation: find step index, set status + timestamp, parse files, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.10 (Text_IO for file output).
   --  TIMING ANALYSIS:
   --    WCET: ~2ms (mutation + timestamp + file save).

   procedure Mark_Step_Failed
     (State     : in out Checkpoint_State;
      File_Path : String;
      Step_Name : String;
      Error_Msg : String := "")
   with Pre => State.Is_Initialized;
   --  Mark a step as failed. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Mark_Step_Failed sets status := Failed.
   --    Axiom 2: Error_Msg is recorded if non-empty.
   --  THEORIES:
   --    Theory 1: After Mark_Step_Failed, Is_Step_Completed returns False.
   --  APPLICATIONS:
   --    Implementation: find step index, set status + error, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 11.4.1 (raise statement).
   --  TIMING ANALYSIS:
   --    WCET: ~2ms.

   procedure Reset
     (State     : in out Checkpoint_State;
      File_Path : String)
   with Pre => State.Is_Initialized;
   --  Reset all steps to pending (keep config). Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Reset sets all Steps(i).Status := Pending.
   --    Axiom 2: Config entries are preserved across Reset.
   --  THEORIES:
   --    Theory 1: After Reset, Get_Next_Step returns the first step.
   --  APPLICATIONS:
   --    Implementation: loop over steps, reset each, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8.1 (loop over enumeration).
   --  TIMING ANALYSIS:
   --    WCET: ~2ms.

   function Summary
     (State : Checkpoint_State) return String
   with Pre => State.Is_Initialized;
   --  Return a human-readable summary of the pipeline state.
   --
   --  AXIOMS:
   --    Axiom 1: Summary includes pipeline ID and each step's status.
   --  THEORIES:
   --    Theory 1: Output format matches Python pipeline_checkpoint.py summary().
   --  APPLICATIONS:
   --    Implementation: build string with status icons per step.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (String concatenation).
   --  TIMING ANALYSIS:
   --    WCET: ~500ns (string building).

   function Get_Config
     (State : Checkpoint_State) return String
   with Pre => State.Is_Initialized;
   --  Return the pipeline configuration as a formatted string.
   --
   --  AXIOMS:
   --    Axiom 1: Get_Config returns key=value pairs, one per line.
   --  THEORIES:
   --    Theory 1: Output matches the CONFIG_* lines in the checkpoint file.
   --  APPLICATIONS:
   --    Implementation: iterate Config entries, format as KEY=VALUE.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (String).
   --  TIMING ANALYSIS:
   --    WCET: ~500ns.

   procedure Update_Config
     (State     : in out Checkpoint_State;
      File_Path : String;
      Key       : String;
      Value     : String)
   with Pre => State.Is_Initialized;
   --  Add or update a configuration key-value pair. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: If Key exists, its Value is overwritten.
   --    Axiom 2: If Key does not exist, a new entry is appended.
   --  THEORIES:
   --    Theory 1: After Update_Config, Get_Config contains the new key=value.
   --  APPLICATIONS:
   --    Implementation: linear scan for existing key, update or append, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8.1 (loop).
   --  TIMING ANALYSIS:
   --    WCET: ~2ms (scan + mutation + save).

   function Get_Output_Files
     (State     : Checkpoint_State;
      Step_Name : String) return String
   with Pre => State.Is_Initialized;
   --  Return the output files recorded for a step as a comma-separated string.
   --
   --  AXIOMS:
   --    Axiom 1: Returns comma-separated file names, or empty string if none.
   --  THEORIES:
   --    Theory 1: Output matches the STEP_*_FILES lines in checkpoint file.
   --  APPLICATIONS:
   --    Implementation: find step index, concatenate file names.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (String).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns.

   function Get_Step_Status
     (State     : Checkpoint_State;
      Step_Name : String) return Step_Status
   with Pre => State.Is_Initialized;
   --  Return the status of a named step.
   --
   --  AXIOMS:
   --    Axiom 1: Get_Step_Status returns the Status field of the named step.
   --  THEORIES:
   --    Theory 1: Result is one of Pending, Running, Completed, Failed.
   --  APPLICATIONS:
   --    Implementation: find step index, return Status.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.5.1 (enumeration type).
   --  TIMING ANALYSIS:
   --    WCET: ~100ns.

   procedure Test_Pipeline_Checkpoint;
   --  Self-test procedure: exercises all public subprograms.
   --
   --  AXIOMS:
   --    Axiom 1: Test_Pipeline_Checkpoint raises no exceptions on success.
   --  THEORIES:
   --    Theory 1: All tests pass if the checkpoint roundtrip is consistent.
   --  APPLICATIONS:
   --    Implementation: create temp file, exercise Start, Mark_*, Query_*, Reset.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 11.4 (exceptions for assertion).
   --  TIMING ANALYSIS:
   --    WCET: ~50ms (file I/O + multiple mutations).

   --  Exception for uninitialized checkpoint access.
   Uninitialized_Checkpoint : exception;
   --  AXIOM: Raised when a subprogram requiring initialization is called
   --         before Start.

end StellarOrion_Pipeline_Checkpoint;
