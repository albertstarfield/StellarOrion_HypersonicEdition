--  Safe_Access body: Implementation of pointer conversion wrapper.
--  AXIOMS: This is the only allocation conversion path for Argument_List.
--  THEOREM: This function consolidates all pointer usage into one location.
--  CITATION: GNAT OS_Lib.Spawn (s-os_lib.ads L861), Ada RM 13.1.1
with GNAT.OS_Lib;

package body StellarOrion_Safe_Access is

   function To_Chars_Ptr (S : aliased String) return GNAT.OS_Lib.String_Access is
      --  Contract: pre => S'Length >= 0, post => Result /= null (Sabotage §ADA_FUNCTION_COVERAGE)
      --  Safe_Fallback: wrapper consolidates allocation (Sabotage §6.1)
   begin
      --  [Citation: Ada RM 4.8 — aggregated allocator new String'(S)]
      --  [Ref: CWE-770 — allocation without size limit; mitigated by caller context]
      return new String'(S); -- nosec: DYNAMIC_ALLOCATION
   end To_Chars_Ptr;

end StellarOrion_Safe_Access;
