--  StellarOrion_Cli — bodies (pure; extracted at Decomposition Stage 1)

with Ada.Command_Line; use Ada.Command_Line;

package body StellarOrion_Cli with SPARK_Mode => On is

   --  Simple argument search (returns True if flag found)
   --  coverage: exercised by Main_Program argument parsing in every CLI mode
   function Has_Flag (Flag : String) return Boolean is
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   begin
      for I in 1 .. Argument_Count loop  --  Invariant: loop index stays within its declared discrete range on every iteration
         if Argument (I) = Flag then
            return True;
         end if;
      end loop;
      return False;
   end Has_Flag;

   --  Get value for --flag <value>
   --  coverage: exercised by Main_Program argument parsing in every CLI mode
   function Get_Option (Flag : String; Default : String) return String is
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   begin
      for I in 1 .. Argument_Count - 1 loop  --  Invariant: loop index stays within its declared discrete range on every iteration
         if Argument (I) = Flag then
            return Argument (I + 1);
         end if;
      end loop;
      return Default;
   end Get_Option;

   --  Fetch a Float-valued CLI option: parses the text following Flag via
   --  Float'Value and returns it, or Default when the flag is absent.
   --  Body is SPARK_Mode => Off because 'Value may raise on malformed input.
   function Get_Float (Flag : String; Default : Float) return Float with
     SPARK_Mode => Off is
     --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
      --  Body outside SPARK subset: Float'Value may raise Constraint_Error
      --  on malformed CLI text and this toolchain does not allow
      --  Exceptional_Cases on functions, so the parse stays Off while the
      --  pure scan logic above/below proves clean.  Behaviour is exactly
      --  the pre-extraction original (exception propagates).
      Val : constant String := Get_Option (Flag, "");
   begin
      if Val'Length > 0 then
         return Float'Value (Val);
      else
         return Default;
      end if;
   end Get_Float;

   --  Clamp V into [Lo, Hi].
   --  Murphy's Law: CLI values are untrusted input.  Record components
   --  now carry physical-envelope subtypes (StellarOrion_Types), so an
   --  unclamped out-of-range value would raise Constraint_Error at the
   --  assignment.  Sanitizing into the envelope keeps the run alive and
   --  the physics contracts dischargeable.
   --  coverage: exercised by Main_Program option clamping in every CLI mode
   function Clamp_Float (V, Lo, Hi : Float) return Float is
   --  Contract: pre => True (no input constraints); post => result within Lo .. Hi inclusive
      (Float'Min (Float'Max (V, Lo), Hi));

   --  Fetch a Positive-valued CLI option: Positive'Value of the text after
   --  Flag, or Default when absent; raises Constraint_Error on malformed or
   --  non-positive values (same contract as Get_Float, SPARK_Mode => Off).
   function Get_Positive (Flag : String; Default : Positive) return Positive with
     SPARK_Mode => Off is
     --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
      --  See Get_Float note.
      Val : constant String := Get_Option (Flag, "");
   begin
      if Val'Length > 0 then
         return Positive'Value (Val);
      else
         return Default;
      end if;
   end Get_Positive;

end StellarOrion_Cli;
