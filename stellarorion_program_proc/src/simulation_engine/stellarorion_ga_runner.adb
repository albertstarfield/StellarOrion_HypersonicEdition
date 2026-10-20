-- =============================================================================
--  StellarOrion_GA_Runner
-- =============================================================================
--  Stand-alone Ada main that runs the surrogate-based genetic algorithm
--  with the RAVENSCAR-PARALLEL population evaluation and prints the
--  result as JSON on stdout.
--
--  WHY AN ADA MAIN (and not the ctypes FFI entry)
--    The GNAT SECONDARY STACK is never initialised in a shared library that
--    a foreign host (ctypes/Python) dlopen()s: the System package is
--    elaborated by an Ada MAIN program and a library has no main. A
--    library call that materialises a large aggregate therefore faults the
--    host process (measured: EXIT=139). Ada TASKING is affected too: the
--    master task is created by the Ada main. This program therefore owns
--    both the runtime and the worker tasks, and the Python side talks to
--    it as a SUBPROCESS (not as a dlopen()ed library).
--
--  AXIOMS
--    A1  stdout carries EXACTLY ONE JSON object; every diagnostic goes to
--        stderr (StellarOrion_Diagnostics.Log) so the host can parse
--        stdout without filtering.
--    A2  The JSON object always contains "x_opt", "cost", "converged",
--        "n_generations" and "history" (the history may be empty).
--    A3  The worker pool is ALWAYS shut down before the program returns:
--        the workers are library-level tasks that block on their gate, so
--        leaving them alive would hang the partition at exit.
--    A4  The reported geometry is projected onto the analytic screening
--        box (Project_To_Analytic_Box) so the coordinates and the cost
--        refer to the same screening problem.
--
--  THEORIES
--    T1  A1 holds because the only Put_Line calls that write to stdout
--        build the JSON object; the diagnostics package writes to fd 2.
--    T2  A3 holds because Shut_Down_Workers is called on the normal path
--        AND in the exception handler.
--
--  APPLICATIONS
--    1. src/python/ada_pinn_wrapper.run_sbo_ga -- spawns this program and
--       parses its JSON (the Python GA/SBO optimiser path).
--
--  CITATIONS
--    [Ada2012]  ISO/IEC 14882:2012, Ada 2012 Reference Manual.
--    [Goldberg89] D. E. Goldberg, Genetic Algorithms in Search, Optimization
--                 and Machine Learning, Addison-Wesley (1989).
--    [POSIX1]   IEEE Std 1003.1-2017, write(2).
--
--  Author: Albert Starfield Wahyu Suryo Samudro
-- =============================================================================

with Ada.Command_Line;      use Ada.Command_Line;
with Ada.Exceptions;        use Ada.Exceptions;
with Ada.Text_IO;           use Ada.Text_IO;
with StellarOrion_Diagnostics;
with StellarOrion_Types;
with StellarOrion_Optimization;  use StellarOrion_Optimization;
with StellarOrion_GA_Parallel;

procedure StellarOrion_GA_Runner is

   --  JSON number rendering: Ada's Float'Image carries a LEADING SPACE for
   --  positive values, which JSON does not allow.
   function J (X : Float) return String is
      Img : constant String := Float'Image (X);
   begin
      if Img'Length > 0 and then Img (Img'First) = ' ' then
         return Img (Img'First + 1 .. Img'Last);
      else
         return Img;
      end if;
   end J;

   --  Command-line state (AXIOM A2: every field has a default).
   Population   : Positive := 50;
   Generations  : Positive := 200;
   Target_Beta  : Float := 30.0;
   Q_Target     : Float := 0.0;
   Flux_Ref     : Float := 0.0;
   Tau_Sec      : Float := 0.0;
   Cd_Ref       : Float := 0.0;
   Have_Refs    : Boolean := False;

   Config : GA_Config;
   Result : GA_Result;
   Count  : Natural := 0;

   --  The history buffer is allocated EXPLICITLY on the heap: the
   --  Ravenscar restriction set of the parallel unit forbids IMPLICIT heap
   --  allocation, and a 4096-row local array would live on the secondary
   --  stack (which is fine in an Ada main, but the explicit allocation is
   --  clearer and keeps the frame small).
   type History_Access is access GA_History_Array;
   History_Buffer : constant History_Access := new GA_History_Array;

   Projected : StellarOrion_Types.Geometry_Parameters;

begin
   --  ---- command line -------------------------------------------------
   for I in 1 .. Argument_Count loop
      if Argument (I) = "--population" and then I < Argument_Count then
         Population := Positive'Value (Argument (I + 1));
      elsif Argument (I) = "--generations" and then I < Argument_Count then
         Generations := Positive'Value (Argument (I + 1));
      elsif Argument (I) = "--target-beta" and then I < Argument_Count then
         Target_Beta := Float'Value (Argument (I + 1));
      elsif Argument (I) = "--q-target" and then I < Argument_Count then
         Q_Target := Float'Value (Argument (I + 1));
         Have_Refs := True;
      elsif Argument (I) = "--flux-ref" and then I < Argument_Count then
         Flux_Ref := Float'Value (Argument (I + 1));
      elsif Argument (I) = "--tau" and then I < Argument_Count then
         Tau_Sec := Float'Value (Argument (I + 1));
      elsif Argument (I) = "--cd-ref" and then I < Argument_Count then
         Cd_Ref := Float'Value (Argument (I + 1));
      end if;
   end loop;

   --  Validation (Murphy law: a bad argument must not reach the solver).
   if Population > Max_Population then
      StellarOrion_Diagnostics.Log
        ("[GA_RUNNER] population " & Positive'Image (Population)
         & " exceeds the maximum " & Positive'Image (Max_Population)
         & " - clamped");
      Population := Max_Population;
   end if;

   --  The validation references make J(x) comparable with the DSMC/PINN
   --  references; the Python wrapper always supplies them.
   if Have_Refs then
      Set_Validation_Refs (Q_Target_Jcm2 => Q_Target,
                            Flux_Ref_Wcm2 => Flux_Ref,
                            Tau_Sec => Tau_Sec,
                            Cd_Ref => Cd_Ref);
   end if;

   Config.Population_Size := Population;
   Config.Max_Generations := Generations;
   Config.Mutation_Rate := 0.1;
   Config.Crossover_Rate := 0.7;
   Config.Elite_Count := 2;
   Config.Tournament_Size := 3;
   Config.Convergence_Gens := 20;
   Config.Convergence_Tol := 1.0E-6;
   --  AXIOM A1: stdout carries EXACTLY ONE JSON object, so the GA's
   --  progress log is switched OFF (the history rows carry the trace).
   Config.Verbose := False;

   --  The parallel route: the population is evaluated CONCURRENTLY by the
   --  four Ravenscar worker tasks.
   Run_SBO_GA (Config        => Config,
               Target_Beta   => Target_Beta,
               Evaluator     => StellarOrion_GA_Parallel.Parallel_Batch_Evaluator'Access,
               History       => History_Buffer,
               History_Count => Count,
               Result        => Result);

   --  AXIOM A3: release the worker pool (the tasks block on their gate).
   StellarOrion_GA_Parallel.Shut_Down_Workers;

   --  AXIOM A4: project the optimum onto the analytic screening box.
   Projected := Project_To_Analytic_Box (Result.Best_Individual);

   --  AXIOM A1/A2: exactly one JSON object on stdout.
   Put_Line ("{""x_opt"": [" & J (Projected.Diameter_M / 2.0) & ", "
             & J (Projected.Toroid_Radius_M) & ", "
             & J (Projected.Angle_Deg) & "], ""cost"": "
             & J (Result.Best_Cost) & ", ""converged"": "
             & (if Result.Converged then "true" else "false")
             & ", ""n_generations"": " & Natural'Image (Result.Generations_Used)
             & ", ""history"": [");
   if Count > 0 then
      for R in 0 .. Count - 1 loop
         Put_Line ("  {""iteration"": " & Integer'Image (Integer (History_Buffer (R).Generation))
                   & ", ""R_N"": " & J (Float (History_Buffer (R).R_N))
                   & ", ""r_tor"": " & J (Float (History_Buffer (R).R_Tor))
                   & ", ""half_cone_deg"": " & J (Float (History_Buffer (R).Half_Cone))
                   & ", ""cost"": " & J (Float (History_Buffer (R).Cost))
                   & "}" & (if R < Count - 1 then "," else ""));
      end loop;
   end if;
   Put_Line ("]}");

exception
   when E : others =>
      StellarOrion_Diagnostics.Log
        ("[GA_RUNNER] fatal: " & Exception_Name (E) & " - "
         & Exception_Information (E));
      --  AXIOM A3: the pool must be released even on the failure path.
      begin
         StellarOrion_GA_Parallel.Shut_Down_Workers;
      exception
         when others =>
            null;
      end;
      Set_Exit_Status (Failure);
end StellarOrion_GA_Runner;
