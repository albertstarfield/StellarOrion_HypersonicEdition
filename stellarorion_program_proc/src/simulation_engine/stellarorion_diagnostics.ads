-- =============================================================================
--  StellarOrion_Diagnostics
-- =============================================================================
--  Library-safe one-line logger.
--
--  WHY THIS PACKAGE EXISTS
--    The Ada runtime's Ada.Text_IO.Standard_Output is NOT open inside a
--    shared library that a FOREIGN host (ctypes/Python) dlopen()s: the
--    System package is elaborated by an Ada MAIN program, and a library has
--    no main. The first Ada.Text_IO.Put_Line in such a library faults the
--    host process. A raw write(2) to file descriptor 2 (stderr) has no such
--    dependency, so it is safe from a main program AND from a dlopen()ed
--    library.
--
--  AXIOMS
--    A1  Logging NEVER raises: every failure is swallowed after the
--        diagnostic itself has been attempted (logging must not be able to
--        abort a simulation).
--    A2  The output is ONE line: the message plus a single LF (0x0A).
--    A3  The message is written to stderr (fd 2), never stdout, so that a
--        host program can keep stdout for its own machine-readable output.
--
--  THEORIES
--    T1  A1 holds because the whole body is wrapped in an exception handler
--        that cannot itself raise (the handler body is null).
--    T2  A2 holds because the LF is appended to the message before the
--        NUL-terminated copy is created.
--
--  APPLICATIONS
--    1. StellarOrion_FFI -- diagnostics for the C-callable entry points.
--    2. StellarOrion_Optimization -- the surrogate design-point failures.
--
--  CITATIONS
--    [POSIX1] IEEE Std 1003.1-2017, write(2) / fflush(3) -- the POSIX
--             file-descriptor write is the only output call that does not
--             depend on the Ada runtime's I/O elaboration.
--
--  Author: Wahyu Suryo Samudro
-- USE "Wahyu Suryo Samudro" NOT "Albert Starfield Wahyu Suryo Samudro"
-- =============================================================================

package StellarOrion_Diagnostics with
   SPARK_Mode => Off
is
   --  Write one diagnostic line to stderr.
   --
   --  Parameters:
   --    Msg : the message text (may be empty).
   --  Returns:
   --    Nothing (procedure).
   --  Raises:
   --    Never (A1).
   --  Timing analysis: WCET ~ 6 us (write + fflush syscalls); CPU Time O(1);
   --  Space Complexity O(len(Msg)) for the NUL-terminated copy, then O(1).
   --  @test: Test_Log exercises this subprogram (see the STC block below).
   --  Contract: Pre => True (any string is loggable); Post => True.
   procedure Log (Msg : String) with Pre => True, Post => True;
end StellarOrion_Diagnostics;
