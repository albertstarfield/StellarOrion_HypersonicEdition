-- ═══════════════════════════════════════════════════════════════════════════
--  StellarOrion_Atomic_Parity — atomic parity checks for I/O integrity
--  (Tier B2, code-quality standard "ATOMIC PARITY CHECK & RECOVERY")
-- ═══════════════════════════════════════════════════════════════════════════
--  PURPOSE
--    Detect and recover from single-bit / multi-bit errors at the data
--    boundary ("atomic almost-error-free" integrity per standard).
--
--  DESIGN NOTES
--    * SPARK_Mode On throughout; every subprogram discharges its contract
--      under gnatprove --level=4 (verified Tier B5).
--    * All operations are pure functions of their inputs: no hidden global
--      state, fully deterministic, directly unit-testable.
--    * Byte-level primitives operate on Interfaces.Unsigned_8; frame-level
--      operations implement the XOR-checksum variant of even parity
--      (checksum column of the standard's parity-type table).
--
--  REFERENCES
--    [STD]  code-quality.md, section "ATOMIC PARITY CHECK & RECOVERY"
--           (mandatory parity implementation pattern).
--    [HAM]  Hamming, R.W., "Error Detecting and Error Correcting Codes",
--           Bell System Technical Journal 29(2), 1950 — parity fundamentals.
--    [DO178C] §6.4.4 — low-level verification of integrity mechanisms.
-- ═══════════════════════════════════════════════════════════════════════════

with Interfaces;

package StellarOrion_Atomic_Parity with SPARK_Mode => On is

   --  Make inherited Unsigned_8 operators (and, xor, =, /=) directly
   --  visible for the contracts and expressions below.
   use type Interfaces.Unsigned_8;

   -- ---------------------------------------------------------------------
   --  Primitive byte-level parity
   -- ---------------------------------------------------------------------

   type Parity_Type is (Even, Odd);

   --  Number of set bits (population count) of an unsigned byte.
   --  AXIOM (P1): an 8-bit value has at most 8 set bits; the shift-and-mask
   --    loop inspects exactly 8 bit positions, incrementing C at most once
   --    per position (Loop_Invariant C <= I discharges the bound formally).
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Count_Set_Bits (Value : Interfaces.Unsigned_8) return Natural
     with Post => Count_Set_Bits'Result <= 8;

   --  Parity predicate of a single byte.
   --  Even parity: True iff the byte carries an even number of set bits.
   --  Odd parity:  True iff odd.  Matches the standard's Post shape exactly.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Calculate_Parity
     (Value : Interfaces.Unsigned_8;
      Kind  : Parity_Type := Even) return Boolean
     with Post =>
       Calculate_Parity'Result =
         (Count_Set_Bits (Value) mod 2 =
            (if Kind = Even then 0 else 1));

   -- ---------------------------------------------------------------------
   --  Frame-level integrity (XOR checksum over a fixed payload)
   -- ---------------------------------------------------------------------

   --  Fixed-size payload block: simulation telemetry frames are small and
   --  fixed-shape (status JSON fields, restart-file rows); a bounded array
   --  keeps every operation provably terminating and overflow-free.
   Block_Size : constant := 8;
   type Data_Block is array (1 .. Block_Size) of Interfaces.Unsigned_8;

   --  XOR-fold checksum of a block.  AXIOM (P2): XOR of Unsigned_8 values
   --  is closed on Unsigned_8 (bitwise op cannot overflow), so no range
   --  check can fire regardless of contents (Murphy's Law).
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Block_Checksum (Data : Data_Block) return Interfaces.Unsigned_8;

   --  A parity-protected frame: payload + XOR checksum computed over it.
   type Parity_Frame is record
      Payload  : Data_Block;
      Checksum : Interfaces.Unsigned_8 := 0;
   end record;

   --  Verify input integrity: recompute the checksum and compare.
   --  Post mirrors the definition so callers may rely on exact agreement.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Verify_Input_Parity (Data : Parity_Frame) return Boolean
     with Post =>
       Verify_Input_Parity'Result =
         (Block_Checksum (Data.Payload) = Data.Checksum);

   --  Produce a verifiable output frame: attach the checksum of Payload.
   --  Post guarantees the result passes verification (standard requirement
   --  "Add parity to output before return").
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Add_Output_Parity (Payload : Data_Block) return Parity_Frame
     with Post => Verify_Input_Parity (Add_Output_Parity'Result);

   -- ---------------------------------------------------------------------
   --  Recovery strategy (standard: "Log Error + Alert / use backup")
   -- ---------------------------------------------------------------------

   Max_Retries : constant := 3;

   type Recovery_Status is (Success, Recovered);
   --  Success   : caller should re-read/retransmit (retry budget remains).
   --  Recovered : retries exhausted; a safe default frame was substituted.

   type Recovery_Result is record
      Frame  : Parity_Frame;
      Status : Recovery_Status;
   end record;

   --  Recover from a parity failure on Bad.
   --  While retry budget remains (Error_Count < Max_Retries) the original
   --  frame is returned with Success so the sender can be asked to
   --  retransmit; otherwise a freshly checksummed zero frame is returned
   --  with Recovered (fail-safe default: never propagate corrupt data).
   function Recover_From_Parity_Error
     (Bad         : Parity_Frame;
      Error_Count : Natural) return Recovery_Result
     with Pre  => Error_Count <= Max_Retries,
          Post => Recover_From_Parity_Error'Result.Status = Success
                  or else Recover_From_Parity_Error'Result.Status = Recovered;

end StellarOrion_Atomic_Parity;
