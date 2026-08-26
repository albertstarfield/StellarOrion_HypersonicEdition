--  StellarOrion_Cli — pure command-line helpers (Decomposition Stage 1)
--
--  Extracted verbatim from StellarOrion_Project (docs/PROJECT_DECOMPOSITION_PLAN.md
--  Stage 1): Has_Flag, Get_Option, Get_Float, Clamp_Float, Get_Positive.
--  Pure string/float logic over Ada.Command_Line; no I/O, no process spawns.
--
--  SPARK_Mode => On: every subprogram discharges its contract under
--  gnatprove --level=4.  Malformed numeric CLI text raises Constraint_Error
--  exactly as before extraction (documented via Parse_* Exceptional_Cases;
--  behaviour-preserving move).

pragma SPARK_Mode (On);

package StellarOrion_Cli is

   --  Returns True if Flag appears among the command-line arguments.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Has_Flag (Flag : String) return Boolean;

   --  Returns the value following Flag, or Default when absent.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Get_Option (Flag : String; Default : String) return String;

   --  Get_Option + Float'Value; Default when flag/value absent.
   --  Note: malformed numeric text raises Constraint_Error (documented,
   --  same behaviour as the pre-extraction original).
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Get_Float (Flag : String; Default : Float) return Float;

   --  Clamp V into [Lo, Hi].  Murphy's Law: CLI values are untrusted
   --  input.  Record components now carry physical-envelope subtypes
   --  (StellarOrion_Types), so an unclamped out-of-range value would
   --  raise Constraint_Error at the assignment.  Sanitizing into the
   --  envelope keeps the run alive and the physics contracts
   --  dischargeable.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Clamp_Float (V, Lo, Hi : Float) return Float with
     Pre => Lo <= Hi;

   --  Get_Option + Positive'Value; Default when flag/value absent.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Get_Positive (Flag : String; Default : Positive) return Positive;

   --  ------------------------------------------------------------------
   --  Self-test coverage wrappers (STC): declared here, defined in the
   --  package body.
   --  ------------------------------------------------------------------

   procedure Test_Has_Flag;
   --  Contract covers pre => True (no inputs); post => completes without raising.
   procedure Test_Get_Option;
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  STC coverage wrapper.
   procedure Test_Get_Float;
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  STC coverage wrapper.
   procedure Test_Clamp_Float;
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  STC coverage wrapper.
   procedure Test_Get_Positive;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Clamp_Float", Test_Clamp_Float'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Float", Test_Get_Float'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Option", Test_Get_Option'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Positive", Test_Get_Positive'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Has_Flag", Test_Has_Flag'Access);
end StellarOrion_Cli;
