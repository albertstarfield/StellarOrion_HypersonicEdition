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
--  COMMAND LINE
--    --population <N>          GA population size        (default 50)
--    --generations <N>         GA generation budget      (default 200)
--    --target-beta <F>         target ballistic coefficient [kg/m^2]
--    --q-target <F>            reference heat load [J/cm^2]
--    --flux-ref <F>            reference peak heat flux [W/cm^2]
--    --tau <F>                 effective heating duration [s]
--    --cd-ref <F>              reference drag coefficient
--    --calibration <path>      calibration file to load BEFORE the run
--                               (CALIBRATION DESIGN 2.6.2; a missing or
--                               unreadable file DISABLES the calibration
--                               and is reported -- it never fails the run)
--    --print-geometry-flags    print, on stderr, the CLI flags that
--                               reproduce the optimum vehicle exactly
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
--    A5  THE PHYSICAL-GEOMETRY CONVENTION (CALIBRATION DESIGN 2.1).  The
--        JSON carries BOTH views of the same optimum:
--          * "x_opt"                    -- the ANALYTIC triple
--                                         (R_N, r_tor, half_cone_deg),
--                                         i.e. the coordinates the
--                                         screening model actually
--                                         scored and the GA minimised;
--          * "diameter_m",
--            "nose_radius_m",
--            "toroid_radius_m",
--            "angle_deg"                -- the PHYSICAL vehicle, obtained
--                                         from that SAME triple through
--                                         StellarOrion_Optimization.
--                                         Analytic_To_Physical.
--        The analytic triple is NOT a vehicle: X(1) is the BODY/JUNCTION
--        radius (the body diameter is 2*X(1)), while the nose bluntness
--        radius is Nose_Radius_Ratio*X(1).  Reporting only the analytic
--        triple is exactly what produced the analytic/DSMC unsync of
--        CALIBRATION DESIGN 1.2, in which the DSMC was flown with a
--        --nose value that the analytic model had never scored.
--    A6  The calibration file is loaded by THIS PROGRAM -- never through
--        the FFI (CALIBRATION DESIGN 2.5 decided the FFI route out: the
--        Ada <-> C string conversion, not an oversight) -- and it is
--        loaded BEFORE the optimisation starts, so the optimum is scored
--        with the model the DSMC will later be compared against.
--    A7  A missing, unreadable or malformed calibration file DEGRADES the
--        run to the uncalibrated (literature-constant) model and NEVER
--        fails it; the condition is reported on stderr.
--    A8  The physical geometry is reported with the SAME numeric type the
--        optimiser used (Standard.Float), so the vehicle handed to the
--        DSMC is the vehicle that was scored -- no rounding is applied
--        between the two views.
--
--  THEORIES
--    T1  A1 holds because the only Put_Line calls that write to stdout
--        build the JSON object; the diagnostics package writes to fd 2.
--    T2  A3 holds because Shut_Down_Workers is called on the normal path
--        AND in the exception handler.
--    T3  A5 holds because Analytic_To_Physical is the SINGLE mapping
--        between the analytic screening space and the flown geometry
--        (CALIBRATION DESIGN 2.1) and the runner applies it to exactly
--        the triple it reports as "x_opt"; the two views therefore cannot
--        drift apart.
--    T4  A7 holds because the loader's contract is "a missing file
--        disables the calibration and never raises" (L1 of the loader's
--        axioms) AND the call is additionally wrapped in a local
--        exception handler, so neither path can abort the run.
--
--  APPLICATIONS
--    1. src/python/ada_pinn_wrapper.run_sbo_ga -- spawns this program and
--       parses its JSON (the Python GA/SBO optimiser path).
--    2. The DSMC driver: "diameter_m"/"nose_radius_m"/"toroid_radius_m"/
--       "angle_deg" are the vehicle to fly, and --print-geometry-flags
--       prints them in the CLI form the project driver accepts.
--
--  CITATIONS
--    [Ada2012]  ISO/IEC 14882:2012, Ada 2012 Reference Manual.
--    [Goldberg89] D. E. Goldberg, Genetic Algorithms in Search, Optimization
--                 and Machine Learning, Addison-Wesley (1989).
--    [POSIX1]   IEEE Std 1003.1-2017, write(2).
--    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics, Sec. 5.4 --
--       blunt-body drag: the nose bluntness radius is part of the vehicle
--       definition (it sets the drag increment and the stagnation
--       heating), which is why the analytic triple cannot be handed to a
--       flight/DSMC driver as if it were a geometry.
--    [NASA-TP-2013-4012] NASA/TP-2013-4012 -- IRVE-3 reference geometry
--       (body radius 1.5 m, nose 0.55 m, torus 0.135 m, cone 60 deg):
--       the anchor of the analytic-to-physical convention.
--
--  Author: Wahyu Suryo Samudro
-- USE "Wahyu Suryo Samudro" NOT "Albert Starfield Wahyu Suryo Samudro"
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
   --
   --  WHY A WIDER 'Image (AXIOM A8): Float'Image renders only SIX
   --  significant digits, because the Ada Float is a 32-bit IEEE type.
   --  Six digits are NOT enough to reproduce the vehicle the optimiser
   --  scored: a consumer that recomputes the mapping from the REPORTED
   --  analytic triple (for example 2*X(1) for the diameter) and compares
   --  it with the reported physical value sees a relative disagreement of
   --  up to ~3E-6 -- the two views of the optimum would visibly drift,
   --  which is the very defect this calibration programme exists to
   --  remove (CALIBRATION DESIGN 1.2).
   --  Long_Long_Float'Image renders the EXACT value of the 32-bit Float
   --  (the widening is lossless), so the JSON round-trips the scored
   --  vehicle bit-for-bit and a downstream DSMC run is launched with
   --  exactly the geometry that was scored.  The rendered literal stays
   --  valid for both consumers: JSON accepts it, and Ada's Float'Value
   --  (the project CLI parser) rounds it straight back to the same Float.
   function J (X : Float) return String is
      Img : constant String := Long_Long_Float'Image (Long_Long_Float (X));
   begin
      if Img'Length > 0 and then Img (Img'First) = ' ' then
         return Img (Img'First + 1 .. Img'Last);
      else
         return Img;
      end if;
   end J;

   --  Maximum length of a calibration-file path accepted on the command
   --  line.  POSIX PATH_MAX is 1024 bytes on the supported targets; the
   --  buffer is sized so that a path can never be silently truncated --
   --  a truncated path would load a DIFFERENT calibration file (or none)
   --  without saying so, which is precisely the class of defect this
   --  calibration programme exists to remove.
   Max_Path_Len : constant := 1024;

   --  Copy a command-line argument into the fixed path buffer.
   --
   --  WHY A FIXED BUFFER AND NOT Ada.Strings.Unbounded: the path must
   --  survive until the calibration is loaded, and an unconstrained heap
   --  string would add an allocation to a program whose sibling route
   --  (the dlopen()ed library) is documented as unsafe with the secondary
   --  stack.  A bounded buffer also makes "path too long" a REPORTED
   --  event rather than a silent truncation.
   --
   --  Parameters:
   --    Src -- the argument to copy.
   --    Dst -- the destination buffer (not modified on failure).
   --  Returns:
   --    the number of characters copied; 0 means the argument was empty or
   --    longer than Dst, and the caller MUST reject it.
   function Copy_Path (Src : String; Dst : out String) return Natural is
   begin
      if Src'Length = 0 or else Src'Length > Dst'Length then
         return 0;
      end if;
      Dst (Dst'First .. Dst'First + Src'Length - 1) := Src;
      return Src'Length;
   end Copy_Path;

   --  TRUE when the argument looks like a FLAG (starts with "--") rather
   --  than a value.  Used to detect "--calibration" with no path, which
   --  must be reported rather than silently swallowed.
   function Looks_Like_Flag (S : String) return Boolean is
   begin
      return S'Length >= 2 and then S (S'First .. S'First + 1) = "--";
   end Looks_Like_Flag;

   --  Command-line state (AXIOM A2: every field has a default).
   Population   : Positive := 50;
   Generations  : Positive := 200;
   Target_Beta  : Float := 30.0;
   Q_Target     : Float := 0.0;
   Flux_Ref     : Float := 0.0;
   Tau_Sec      : Float := 0.0;
   Cd_Ref       : Float := 0.0;
   Have_Refs    : Boolean := False;

   --  Calibration state (CALIBRATION DESIGN 2.6.2 / AXIOM A6).
   Calibration_Path     : String (1 .. Max_Path_Len) := (others => ' ');
   Calibration_Len      : Natural := 0;
   Calibration_Seen     : Boolean := False;
   Calibration_Is_Active : Boolean := False;

   --  Print the CLI flags that reproduce the optimum (AXIOM A5).
   Print_Geometry_Flags : Boolean := False;

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

   --  The ANALYTIC triple the optimiser scored, and the PHYSICAL vehicle
   --  it denotes (AXIOM A5).
   X_Opt    : Param_Vector := (others => 0.0);
   Physical : StellarOrion_Types.Geometry_Parameters;
   --  Effective heat-load weight of J for THIS pass (the double pass GA's
   --  round-2 injection point: W_Heat_Load + (c - 1)).
   Heat_Load_Weight_Value : Float := 1.0;
   Heat_Load_Weight_Seen  : Boolean := False;

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
      elsif Argument (I) = "--calibration" then
         --  The path is the NEXT argument.  A missing value (or a value
         --  that is itself a flag) is REPORTED and ignored: the runner
         --  must not fail because of a malformed command line.
         Calibration_Seen := True;
         if I < Argument_Count
           and then not Looks_Like_Flag (Argument (I + 1))
         then
            Calibration_Len := Copy_Path (Argument (I + 1), Calibration_Path);
         else
            Calibration_Len := 0;
         end if;
      elsif Argument (I) = "--heat-load-weight" and then I < Argument_Count then
         Heat_Load_Weight_Value := Float'Value (Argument (I + 1));
         Heat_Load_Weight_Seen := True;
      elsif Argument (I) = "--print-geometry-flags" then
         Print_Geometry_Flags := True;
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

   --  The validation references make J(x) comparable with the DSMC+PINN_AUX
   --  references; the Python wrapper always supplies them.
   if Have_Refs then
      Set_Validation_Refs (Q_Target_Jcm2 => Q_Target,
                            Flux_Ref_Wcm2 => Flux_Ref,
                            Tau_Sec => Tau_Sec,
                            Cd_Ref => Cd_Ref);
   end if;

   --  ---- calibration (AXIOM A6, loaded BEFORE the optimisation) -------
   if Calibration_Seen then
      if Calibration_Len = 0 then
         --  T4: the run continues, uncalibrated.
         StellarOrion_Diagnostics.Log
           ("[GA_RUNNER] --calibration was given an empty path or a path"
            & " longer than " & Natural'Image (Max_Path_Len)
            & " characters - calibration NOT loaded (uncalibrated model)");
      else
         --  THE LOADER IS ALWAYS CALLED (the design gives it the job of
         --  disabling the calibration for a missing file); the handler
         --  below covers every OTHER failure mode (a malformed file, a
         --  permission error) so the runner ALWAYS produces its JSON.
         begin
            Load_Calibration (Calibration_Path (1 .. Calibration_Len));
         exception
            when E : others =>
               StellarOrion_Diagnostics.Log
                 ("[GA_RUNNER] calibration load raised "
                  & Exception_Name (E)
                  & " - continuing with the UNCALIBRATED model");
         end;

         --  The authoritative state is the loader's own query, NOT the
         --  return of the load call: the loader's contract is "a missing
         --  file disables the calibration and never raises", so a normal
         --  return does not prove that a calibration was applied.
         Calibration_Is_Active := Calibration_Active;

         if Calibration_Is_Active then
            StellarOrion_Diagnostics.Log
              ("[GA_RUNNER] calibration ACTIVE from "
               & Calibration_Path (1 .. Calibration_Len));
         else
            StellarOrion_Diagnostics.Log
              ("[GA_RUNNER] calibration NOT active ("
               & Calibration_Path (1 .. Calibration_Len)
               & " missing, unreadable or invalid) - the model keeps the"
               & " BUILT-IN literature constants");
         end if;
      end if;
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

   --  AXIOM (double pass GA): the effective heat-load weight of J.  The
   --  round-2 pass sets it to W_Heat_Load + (c - 1) (W_Heat_Load = 1.0),
   --  which is algebraically identical to J_round2 = J + (c-1)*heat_load_ratio
   --  -- the same genetic-algebra engine, the corrected cost.
   if Heat_Load_Weight_Seen then
      if Heat_Load_Weight_Value < 0.0 then
         StellarOrion_Diagnostics.Log
           ("[GA_RUNNER] negative heat-load weight "
            & Float'Image (Heat_Load_Weight_Value)
            & " - clamped to 0.0");
         Heat_Load_Weight_Value := 0.0;
      end if;
      StellarOrion_Optimization.Set_Heat_Load_Weight (Heat_Load_Weight_Value);
   end if;

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

   --  AXIOM A5: the ANALYTIC triple that was scored ...
   X_Opt (1) := Projected.Diameter_M / 2.0;
   X_Opt (2) := Projected.Toroid_Radius_M;
   X_Opt (3) := Projected.Angle_Deg;

   --  ... and the PHYSICAL vehicle it denotes (CALIBRATION DESIGN 2.1).
   --  POSITIONAL association on purpose: the design fixes the parameter
   --  names, but positional association also survives a rename in the
   --  (concurrently developed) mapping unit, so this runner cannot break
   --  on a cosmetic change to the mapping's specification.
   Analytic_To_Physical (X_Opt, Physical);

   --  AXIOM A1/A2: exactly one JSON object on stdout.  The new physical
   --  fields sit NEXT TO "x_opt" and BEFORE "history", because the host
   --  parser locates the end of the object with the LAST "]}" in the
   --  stream -- a field placed after the history array would hide it.
   Put_Line ("{""x_opt"": [" & J (X_Opt (1)) & ", "
             & J (X_Opt (2)) & ", "
             & J (X_Opt (3)) & "]"
             & ", ""diameter_m"": " & J (Physical.Diameter_M)
             & ", ""nose_radius_m"": " & J (Physical.Nose_Radius_M)
             & ", ""toroid_radius_m"": " & J (Physical.Toroid_Radius_M)
             & ", ""angle_deg"": " & J (Physical.Angle_Deg)
             & ", ""cost"": "
             & J (Result.Best_Cost) & ", ""converged"": "
             & (if Result.Converged then "true" else "false")
             & ", ""n_generations"": " & Natural'Image (Result.Generations_Used)
             & ", ""heat_load_weight"": " & J (Heat_Load_Weight_Value)
             & ", ""calibration_active"": "
             & (if Calibration_Is_Active then "true" else "false")
             & ", ""pipeline"": ""double pass GA"""
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

   --  AXIOM A1: the reproducible command line goes to STDERR, so stdout
   --  remains exactly one JSON object that the host can parse blindly.
   --  The flag names are the ones the project driver accepts
   --  (stellarorion_project.adb): --nose, --diameter, --tradius, --angle.
   if Print_Geometry_Flags then
      StellarOrion_Diagnostics.Log
        ("[GA_RUNNER] optimum vehicle -- reproduce it with:");
      StellarOrion_Diagnostics.Log
        ("--nose " & J (Physical.Nose_Radius_M)
         & " --diameter " & J (Physical.Diameter_M)
         & " --tradius " & J (Physical.Toroid_Radius_M)
         & " --angle " & J (Physical.Angle_Deg));
   end if;

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
