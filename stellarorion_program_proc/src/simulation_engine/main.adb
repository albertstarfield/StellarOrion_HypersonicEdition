--  Standalone entry point for StellarOrion Program Proc.
--  GNAT requires a top-level parameterless procedure as a main program.
--  StellarOrion_Project.Main_Program is inside a package, so we wrap it here.

with StellarOrion_Project;

--  Executable entry point: delegates immediately to
--  StellarOrion_Project.Main_Program, which parses argv and dispatches to
--  the selected CLI mode.  This wrapper exists only because GNAT requires
--  a library-level parameterless procedure as the Ada main program.
--  @test: exercised by every CLI mode incl. --self-test (entry point Main)
procedure Main is
--  Contract: pre => True (no input constraints); post => dispatches exactly one CLI mode and terminates
begin
   StellarOrion_Project.Main_Program;
end Main;
