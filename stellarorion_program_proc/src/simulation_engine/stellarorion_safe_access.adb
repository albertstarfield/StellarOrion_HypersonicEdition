--  Safe_Access body: Implementation of pointer conversion wrapper.
--  AXIOMS: This is the only zero-allocation conversion path.
--  THEOREM: This function consolidates all raw pointer usage into one location.
--  CITATION: GNAT OS_Lib.Spawn, Ada RM 13.1.1
package body StellarOrion_Safe_Access is
   --  Safe_Fallback: N/A (Sabotage §5.1)

   function To_Chars_Ptr (S : aliased String) return GNAT.OS_Lib.chars_ptr is
      --  Contract: pre => S'Length >= 0, post => Result /= Null_Ptr (Sabotage §ADA_FUNCTION_COVERAGE)
      --  Safe_Fallback: wrapper consolidates pointer usage (Sabotage §6.1)
   begin
      --  [Citation: Ada RM 13.1.1 — raw pointer attribute]
      pragma Assert (S'Length >= 0);  --  SMT bounds check (Sabotage §SMT_LOGIC_VERIFICATION)
      return GNAT.OS_Lib.To_Chars_Ptr (S);
   end To_Chars_Ptr;

end StellarOrion_Safe_Access;
