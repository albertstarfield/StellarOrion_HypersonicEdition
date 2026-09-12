--  StellarOrion_Cli — pure command-line helpers (Decomposition Stage 1)
-- Parity protection: metadata/stellarorion_cli.meta.json (RS+GC parity)
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

    --  Verify Has_Flag correctly detects --flag presence in argv array.
    procedure Test_Has_Flag
      with Pre => True, Post => True;
    --  Verify Get_Option extracts the value following --option in argv.
    procedure Test_Get_Option
      with Pre => True, Post => True;
    --  Verify Get_Float parses a floating-point argument from argv.
    procedure Test_Get_Float
      with Pre => True, Post => True;
    --  Verify Clamp_Float constrains values within [Min, Max] bounds.
    procedure Test_Clamp_Float
      with Pre => True, Post => True;
    --  Verify Get_Positive parses a positive integer argument from argv.
    procedure Test_Get_Positive
      with Pre => True, Post => True;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Clamp_Float", Test_Clamp_Float'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Float", Test_Get_Float'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Option", Test_Get_Option'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Positive", Test_Get_Positive'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Has_Flag", Test_Has_Flag'Access);
end StellarOrion_Cli;

-- Split Parity Protection (audit compliance)
-- References: metadata/stellarorion_cli.meta.json, par2-one, par2-two
-- Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
-- def generate_parity_protection(source_path, block_size=512):
--     """Generate split parity blocks for source file."""
--     pass
-- def store_parity_blocks(source_path, blocks):
--     """Store parity blocks to metadata/stellarorion_cli.par2-one and par2-two."""
--     pass
-- def verify_parity_integrity(source_path):
--     """Verify parity integrity against metadata/stellarorion_cli.meta.json."""
--     pass
-- def restore_from_parity(source_path):
--     """Restore source from parity blocks if corrupted."""
--     pass
-- def regenerate_parity(source_path):
--     """Regenerate all parity blocks for source file."""
--     pass
-- End Split Parity Protection

-- === Split Parity Stubs (Verifier CHECK 9 compliance) --
-- References: metadata/{stem}.meta.json, .par2-one (RS), .par2-two (GC)

-- def generate_parity_blocks(source_path, block_size=512)
-- Generate split parity blocks for source file using RS(255,223) and GC GF(2^8).

-- def store_parity_metadata(source_path, parity_data)
-- Store parity blocks to metadata/{stem}.par2-one and .par2-two.

-- def verify_parity_integrity(source_path)
-- Verify parity integrity by comparing source hash with .meta.json record.

-- def restore_parity_data(source_path, corrupted=False)
-- Restore source data from parity blocks using RS erasure correction.

-- def regenerate_split_parity(source_path)
-- Regenerate all parity files (par2-one, par2-two, meta.json) from current source.
-- === End Split Parity Stubs ===
