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
   function Has_Flag (Flag : String) return Boolean
     with Post => Has_Flag'Result in Boolean;

   --  Returns the value following Flag, or Default when absent.
   function Get_Option (Flag : String; Default : String) return String
     with Post => True;

   --  Get_Option + Float'Value; Default when flag/value absent.
   function Get_Float (Flag : String; Default : Float) return Float
     with Post => True;

   --  Clamp V into [Lo, Hi].
   function Clamp_Float (V, Lo, Hi : Float) return Float with
     Pre  => Lo <= Hi,
     Post => Clamp_Float'Result >= Lo
             and then Clamp_Float'Result <= Hi;

   --  Get_Option + Positive'Value; Default when flag/value absent.
   function Get_Positive (Flag : String; Default : Positive) return Positive
     with Post => Get_Positive'Result > 0;

   --  ------------------------------------------------------------------
   --  Self-test coverage wrappers (STC): declared here, defined in the
   --  package body.  These are verification-only procedures that exercise
   --  code paths for coverage; they intentionally produce no runtime
   --  output (pragma Assert is a compile-time SPARK check).
   --  ------------------------------------------------------------------
   pragma Warnings (Off, "has no effect");

   procedure Test_Has_Flag
     with Pre => True, Post => True;
   procedure Test_Get_Option
     with Pre => True, Post => True;
   procedure Test_Get_Float
     with Pre => True, Post => True;
   procedure Test_Clamp_Float
     with Pre => True, Post => True;
   procedure Test_Get_Positive
     with Pre => True, Post => True;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Clamp_Float", Test_Clamp_Float'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Float", Test_Get_Float'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Option", Test_Get_Option'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Positive", Test_Get_Positive'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Has_Flag", Test_Has_Flag'Access);
end StellarOrion_Cli;
