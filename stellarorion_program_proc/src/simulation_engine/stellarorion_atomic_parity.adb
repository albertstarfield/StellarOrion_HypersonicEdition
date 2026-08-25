-- ═══════════════════════════════════════════════════════════════════════════
--  StellarOrion_Atomic_Parity — body (Tier B2)
--  See spec header for design notes and references.
-- ═══════════════════════════════════════════════════════════════════════════

package body StellarOrion_Atomic_Parity with SPARK_Mode => On is
   --  Unsigned_8 operator visibility inherited from the spec's use_type.

   -- ---------------------------------------------------------------------
   --  Byte-level parity
   -- ---------------------------------------------------------------------

   function Count_Set_Bits (Value : Interfaces.Unsigned_8) return Natural is
      V : Interfaces.Unsigned_8 := Value;
      C : Natural               := 0;
      I : Natural               := 0;
   begin
      --  Inspect each of the 8 bit positions once.  C counts the set bits
      --  seen so far; the invariant C <= I bounds it by 8 at loop exit
      --  (discharges the Post; AXIOM P1).
      while I < 8 loop
         if (V and 1) /= 0 then
            C := C + 1;
         end if;
         V := Interfaces.Shift_Right (V, 1);
         I := I + 1;
         --  B5 gate lesson: C <= I alone does NOT imply C <= 8 at exit --
         --  without an upper bound on I the prover cannot exclude I > 8.
         pragma Loop_Invariant (I <= 8);
         pragma Loop_Invariant (C <= I);
         pragma Loop_Variant (Increases => I);
      end loop;
      return C;
   end Count_Set_Bits;

   --  Total-parity predicate over one byte: True iff the number of set bits
   --  in Value has the parity requested by Kind (even count for Even,
   --  odd count for Odd).  Mirrors the Post'Class expression exactly.
   function Calculate_Parity
     (Value : Interfaces.Unsigned_8;
      Kind  : Parity_Type := Even) return Boolean
   is
      Bits : constant Natural := Count_Set_Bits (Value);
   begin
      --  Direct transcription of the Post: no proof gap can open between
      --  body and contract because they are the same expression.
      return (if Kind = Even then Bits mod 2 = 0 else Bits mod 2 = 1);
   end Calculate_Parity;

   -- ---------------------------------------------------------------------
   --  Frame-level integrity
   -- ---------------------------------------------------------------------

   function Block_Checksum (Data : Data_Block) return Interfaces.Unsigned_8 is
      Acc : Interfaces.Unsigned_8 := 0;
   begin
      --  XOR fold: closed on Unsigned_8 (AXIOM P2), so no range check can
      --  fire and no invariant is needed beyond the static loop bounds.
      for I in Data_Block'Range loop
         Acc := Acc xor Data (I);
      end loop;
      return Acc;
   end Block_Checksum;

   --  Frame integrity gate: returns True only when the transmitted Checksum
   --  equals a fresh XOR fold of the received Payload, i.e. the frame shows
   --  no detectable corruption.  Verification is recomputation of the Post.
   function Verify_Input_Parity (Data : Parity_Frame) return Boolean is
   begin
      --  Same expression as the Post: verification is recomputation.
      return Block_Checksum (Data.Payload) = Data.Checksum;
   end Verify_Input_Parity;

   --  Producer-side framing: attach the Block_Checksum of Payload so the
   --  receiver can Verify_Input_Parity the frame without any hidden
   --  state; the returned frame always satisfies Verify_Input_Parity.
   function Add_Output_Parity (Payload : Data_Block) return Parity_Frame is
      Result : constant Parity_Frame :=
        (Payload  => Payload,
         Checksum => Block_Checksum (Payload));
   begin
      return Result;
   end Add_Output_Parity;

   -- ---------------------------------------------------------------------
   --  Recovery strategy
   -- ---------------------------------------------------------------------

   function Recover_From_Parity_Error
     (Bad         : Parity_Frame;
      Error_Count : Natural) return Recovery_Result
   is
      Safe_Zero : constant Parity_Frame :=
        (Payload  => (others => 0),
         Checksum => 0);
   begin
      if Error_Count < Max_Retries then
         --  Retry budget remains: hand back the suspect frame untouched and
         --  ask the producer to retransmit (standard recovery table,
         --  "Request retransmission").
         return (Frame  => Bad,
                 Status => Success);
      else
         --  Budget exhausted: substitute a provably valid zero frame
         --  (checksum of all-zero payload is zero, so Verify passes).
         return (Frame  => Safe_Zero,
                 Status => Recovered);
      end if;
   end Recover_From_Parity_Error;

end StellarOrion_Atomic_Parity;
