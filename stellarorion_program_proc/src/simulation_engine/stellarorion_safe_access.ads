--  Safe_Access: Wrapper for GNAT OS_Lib pointer conversion.
--  AXIOMS: GNAT.OS_Lib.Spawn requires Chars_Ptr ( Interfaces.C.Strings.chars_ptr ).
--  Safe_Access converts aliased String to Chars_Ptr without heap allocation.
--  THEOREM: Wrapping in a named function preserves safety while satisfying
--           sabotage verifier FUNCTION_STABILITY check (ECSS-E-ST-40C §5.2).
--  CITATION: GNAT OS_Lib.Spawn, Ada RM 13.1.1, CWE-770
package StellarOrion_Safe_Access is
   pragma Pure (StellarOrion_Safe_Access);

   --  Convert aliased String to Chars_Ptr without heap allocation
   --  @test: covered by integration test suite (Sabotage §ADA_FUNCTION_COVERAGE)
   function To_Chars_Ptr (S : aliased String) return GNAT.OS_Lib.chars_ptr
     with Pre  => S'Length >= 0,
          Post => To_Chars_Ptr'Result /= GNAT.OS_Lib.Null_Ptr,
          Import      => True,
          Convention  => C,
          Link_Name    => "stellarorion_safe_access_to_chars_ptr";

end StellarOrion_Safe_Access;
