--  Standalone entry point for StellarOrion Program Proc.
--  GNAT requires a top-level parameterless procedure as a main program.
--  StellarOrion_Project.Main_Program is inside a package, so we wrap it here.

with StellarOrion_Project;

--  Executable entry point: delegates immediately to
--  StellarOrion_Project.Main_Program, which parses argv and dispatches to
--  the selected CLI mode.  This wrapper exists only because GNAT requires
--  a library-level parameterless procedure as the Ada main program.
procedure Main is
begin
   StellarOrion_Project.Main_Program;
end Main;
