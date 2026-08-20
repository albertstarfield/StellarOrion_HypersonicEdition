--  Standalone entry point for StellarOrion Program Proc.
--  GNAT requires a top-level parameterless procedure as a main program.
--  StellarOrion_Project.Main_Program is inside a package, so we wrap it here.

with StellarOrion_Project;

procedure Main is
begin
   StellarOrion_Project.Main_Program;
end Main;
