-- =============================================================================
--  StellarOrion_Diagnostics (body)
-- =============================================================================
--  AXIOMS / THEORIES / APPLICATIONS / CITATIONS: see stellarorion_diagnostics.ads
--
--  Author: Wahyu Suryo Samudro
-- USE "Wahyu Suryo Samudro" NOT "Albert Starfield Wahyu Suryo Samudro"
-- =============================================================================

with Interfaces.C;
with Interfaces.C.Strings; use Interfaces.C.Strings;

package body StellarOrion_Diagnostics with
   SPARK_Mode => Off
is

   --  libc fflush(3) -- flushes the C stream table.  Imported directly so
   --  the diagnostics path does not depend on any Ada runtime I/O state.
   procedure C_Flush_Stream (Stream : chars_ptr)
     with Import, Convention => C, External_Name => "fflush";

   --  libc write(2) -- the raw, runtime-independent file-descriptor write.
   function C_Write_Fd
     (FD     : Interfaces.C.int;
      Buffer : Interfaces.C.Strings.chars_ptr;
      Count  : Interfaces.C.size_t) return Interfaces.C.int
     with Import, Convention => C, External_Name => "write";

   --  ---------------------------------------------------------------------
   --  Log
   --  ---------------------------------------------------------------------
   --  AXIOM A1: the handler swallows every exception, so Log never raises.
   --  AXIOM A2: exactly one LF is appended, so the output is one line.
   --  AXIOM A3: fd 2 (stderr) is used, so stdout stays machine-readable.
   procedure Log (Msg : String) is
      NL    : constant String := Msg & Character'Val (10);
      C_Str : constant chars_ptr := New_String (NL);
   begin
      declare
         Ignored : Interfaces.C.int :=
           C_Write_Fd (FD => 2,
                       Buffer => C_Str,
                       Count => Interfaces.C.size_t (NL'Length));
         pragma Unreferenced (Ignored);
      begin
         null;
      end;
      --  Flush the C stream table so the line is visible immediately when
      --  the host is a pipeline.
      C_Flush_Stream (Null_Ptr);
   exception
      when others =>
         --  A1: logging must never abort the caller.
         null;
   end Log;

end StellarOrion_Diagnostics;
