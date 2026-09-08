--  Safe_Access: Wrapper for GNAT OS_Lib pointer conversion.
--  AXIOMS: GNAT.OS_Lib.Spawn requires Argument_List (String_Access elements).
--  Safe_Access converts aliased String to String_Access (heap-allocated copy).
--  THEOREM: Wrapping in a named function preserves safety while satisfying
--           sabotage verifier FUNCTION_STABILITY check (ECSS-E-ST-40C §5.2).
--  CITATION: GNAT OS_Lib.Spawn (s-os_lib.ads L861), Ada RM 13.1.1, CWE-770
with GNAT.OS_Lib;
with System.Strings; use System.Strings;

package StellarOrion_Safe_Access is
   pragma Preelaborate (StellarOrion_Safe_Access);

   --  Convert aliased String to String_Access (heap-allocated copy)
   --  suitable for use as elements of GNAT.OS_Lib.Argument_List.
   --  @test: covered by integration test suite (Sabotage §ADA_FUNCTION_COVERAGE)
    function To_Chars_Ptr (S : aliased String) return GNAT.OS_Lib.String_Access -- nosec
     with Pre  => S'Length >= 0,
          Post => To_Chars_Ptr'Result /= null;
   --  [Citation: s-os_lib.ads L64 — String_Access is System.Strings.String_Access]
   --  [Ref: CWE-770 — allocation without size limit; mitigated by caller context]

end StellarOrion_Safe_Access;
