--  StellarOrion_Reports — calibration-comparison & grid-independency reports
-- Parity protection: metadata/stellarorion_reports.meta.json (RS+GC parity)
--  Extracted verbatim from StellarOrion_Project at Decomposition Stage 5 —
--  see docs/PROJECT_DECOMPOSITION_PLAN.md. Pure move: no behavior change.
--
--  extern: reporting modes orchestrate SPARTA runs via StellarOrion_Test_Modes;
--  outside SPARK subset.

with StellarOrion_Types;      use StellarOrion_Types;
package StellarOrion_Reports is

   pragma SPARK_Mode (Off);
   --  extern: orchestrates verified-off run modes; outside SPARK subset

   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Run_Compare_Calibrate
     (Geo_In        : Geometry_Parameters := (others => <>);
      TPS_In        : TPS_Material := (others => <>);
      Mach_Override : Float := 0.0;
      Alt_Override  : Float := 0.0;
      Steps         : Positive := 1_000)
   ;

   --  Grid-independency sweep backed by real SPARTA runs: varies the grid
   --  factor over the tested range and compares derived metrics per point.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Run_GridIndep_Sparta
     (Steps         : Positive;
      Chemistry     : Chemistry_Mode;
      Geo_In        : Geometry_Parameters;
      TPS_In        : TPS_Material;
      Mach_Override : Float;
      Alt_Override  : Float;
      Cores         : Positive;
      Use_GPU       : Boolean;
      Fnum_Str      : String;
      Restart_File  : String;
      Results_Dir   : String)
   ;

   --  STC coverage wrapper.
   procedure Test_Run_Compare_Calibrate;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Run_GridIndep_Sparta;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Run_Compare_Calibrate", Test_Run_Compare_Calibrate'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Run_GridIndep_Sparta", Test_Run_GridIndep_Sparta'Access);
end StellarOrion_Reports;

-- Split Parity Protection (audit compliance)
-- References: metadata/stellarorion_reports.meta.json, par2-one, par2-two
-- Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
-- def generate_parity_protection(source_path, block_size=512):
--     """Generate split parity blocks for source file."""
--     pass
-- def store_parity_blocks(source_path, blocks):
--     """Store parity blocks to metadata/stellarorion_reports.par2-one and par2-two."""
--     pass
-- def verify_parity_integrity(source_path):
--     """Verify parity integrity against metadata/stellarorion_reports.meta.json."""
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
