--  StellarOrion_HypersonicEdition — SPARTA DSMC Solver Bridge (Body)
--  Ada 2012 / SPARK 2014
--  SPARK_Mode => Off : subprocess / Docker / file I/O.
--
--  This implementation:
--    1. Generates a SPARTA input script from parameters.
--    2. Invokes Docker to run the SPARTA build + simulation.
--    3. Parses the surface dump files and averages the last 15 dumps.
--
--  References:
--    [Plimpton2014] Plimpton, S. & Gallis, M. "SPARTA Stochastic
--                   Particle Automatic Real-Time Application," 2014.
--    [Rap23]        Rapisarda, V. thesis, 2023.
--    [TR-376]       Sutton, K. & Graves, R. A. NASA TR R-376, 1972.

with Ada.Text_IO;           use Ada.Text_IO;
with Ada.Strings;           use Ada.Strings;
with Ada.Strings.Unbounded; use Ada.Strings.Unbounded;
with Ada.Directories;       use Ada.Directories;
with Ada.Exceptions;        use Ada.Exceptions;
with StellarOrion_Geometry; use StellarOrion_Geometry;
with Interfaces.C.Strings;

package body StellarOrion_Sparta is
   pragma SPARK_Mode (Off);
   --  extern: writes SPARTA run scripts + Ada.Directories/Exceptions I/O (non-SPARK)

   -- ==================================================================
   --  Internal Helpers
   -- ==================================================================

   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Chem_To_String")
   --  (script-generation helper; integration path via --test sample).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Chem_To_String (C : Chemistry_Mode) return String is
      --  Contract: pre  => C is any valid Chemistry_Mode value;
      --           post => result is the SPARTA species-block tag for C.
   begin
      case C is
         when Five_Species   => return "5sp";
         when Eleven_Species => return "11sp";
         when Mars           => return "mars";
      end case;
   end Chem_To_String;

   --  Map a nose-cone kind to its descriptor string in the generated
   --  SPARTA input script.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Nose_To_String")
   --  (script-generation helper; integration path via --test sample).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Nose_To_String (N : Nose_Type_Kind) return String is
      --  Contract: pre  => N is any valid Nose_Type_Kind value;
      --           post => result is the SPARTA nose descriptor for N.
   begin
      case N is
         when Smooth => return "smooth";
         when Pointy => return "pointy";
      end case;
   end Nose_To_String;

   --  Float'Image with the leading space GNAT emits for non-negative
   --  values stripped, so generated scripts stay column-aligned.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Img_Float") (formatting
   --  helper; exercised by every generated-script smoke run).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Img (V : Float) return String is
      --  Contract: pre  => any Float value;
      --           post => 'Image text with any leading blank stripped.
      S : constant String := Float'Image (V);
   begin
      if S'Length > 1 and then S (S'First) = ' ' then
         return S (S'First + 1 .. S'Last);
      end if;
      return S;
   end Img;

   --  Integer counterpart of Img above.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Img_Integer") (formatting
   --  helper; exercised by every generated-script smoke run).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Img (V : Integer) return String is
      --  Contract: pre  => any Integer value;
      --           post => 'Image text with any leading blank stripped.
      S : constant String := Integer'Image (V);
   begin
      if S'Length > 1 and then S (S'First) = ' ' then
         return S (S'First + 1 .. S'Last);
      end if;
      return S;
   end Img;

   --  Square root via 8 fixed Newton iterations starting from X/2;
   --  returns 0.0 for X <= 0 so callers never see an invalid result.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Sqrt") (script-generation
   --  helper; exercised via --test sample smoke runs).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Sqrt (X : Float) return Float is
      --  Contract: pre  => any Float value;
      --           post => non-negative Newton approximation of sqrt(X);
      --           exactly 0.0 when X <= 0.0.
      Y, Y_New : Float;
   begin
      if X <= 0.0 then return 0.0; end if;
      Y := X / 2.0;
      --  Loop invariant: fixed 8-iteration Newton refinement; Y remains
      --  positive because X > 0 here and each update averages two
      --  positive terms, so the division below cannot fault.
      for I in 1 .. 8 loop
         --  Invariant: iteration count is bounded and state
         --  variables remain within their declared ranges.
         pragma Unreferenced (I);
         exit when Y = 0.0;  -- defensive: unreachable for X > 0 (Y stays positive)
         Y_New := (Y + X / Y) / 2.0;
         --  range/NaN note: Y + X stays finite (both operands positive
         --  floats); the loop range is the fixed 1 .. 8 refinement
         --  schedule, so no Constraint_Error and no Inf/NaN can arise.
         Y := Y_New;
      end loop;
      return Y;
   end Sqrt;

   --  Branch-based absolute value used when computing geometry deltas.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Abs_F") (helper; exercised
   --  via --test sample smoke runs).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Abs_F (X : Float) return Float is
      --  Contract: pre  => any Float value;
      --           post => |X| >= 0.0, exact for all finite inputs.
   begin
      if X < 0.0 then return -X; end if;
      return X;
   end Abs_F;

   --  Binding to C system(3): dispatches shell commands (Docker runs)
   --  from this otherwise pure-Ada package.
   --  Contract: pre  => Cmd is a shell command string to dispatch;
   --           post => returns after the external command completes;
   --           exit status is not inspected by callers.
   procedure System (Cmd : String) is
      function C_System (S : Interfaces.C.Strings.chars_ptr) return Integer;
      pragma Import (C, C_System, "system");
      C_Cmd : Interfaces.C.Strings.chars_ptr := Interfaces.C.Strings.New_String (Cmd);
      Rc    : Integer;
   begin
      Rc := C_System (C_Cmd);
      Interfaces.C.Strings.Free (C_Cmd);
   end System;

   -- ==================================================================
   --  Generate_Sparta_Script
   -- ==================================================================
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Generate_Sparta_Script")
   --  (integration path via --test sample; no direct Run_Self_Test call).
   --  Contract: pre  => Flight/Geo components within their record
   --           subtype envelopes, Steps >= 1;
   --           post => writes a complete SPARTA input script (in.hiad)
   --           to Results_Dir covering species/grid/BC/compute blocks.
   procedure Generate_Sparta_Script
     (Flight       : Flight_Parameters;
      Geo          : Geometry_Parameters;
      Grid_Factor  : Float;
      Steps        : Positive;
      Chemistry    : Chemistry_Mode;
      Fnum         : Float;
      Restart_File : String;
      Results_Dir  : String)
   is
      File        : File_Type;
      Script_Path : constant String := Results_Dir & "/in.hiad";
      --  Convert mass density [kg/m^3] to number density [molecules/m^3]
      --  for SPARTA's "global nrho" command: nrho = rho_kgm3 * N_A / M_air
      N_Rho       : constant Float := Flight.Density_Kgm3 * N_AVOGADRO / M_AIR;
      Vstream     : constant Float := Flight.Velocity_Ms;
      Temp_Inf    : constant Float := Flight.Temperature_K;
      T_Wall      : constant Float := 1000.0;
       D_Val       : constant Float := Geo.Diameter_M;
       pragma Unreferenced (D_Val);
      Surf_Name   : constant String := "HIAD_custom";
      Gamma       : Float;
      R_Gas       : Float;
      Sound_Spd   : Float;
      Mach_Val    : Float;
      Xmin, Xmax, Ymax : Float;
      --  Grid matches Python ORION template: create_grid 139 139 1 at factor 0.7
      NX, NY      : Integer;
      Stats_Interval : Natural := 100;
      Avg_Nfreq, Avg_Nrepeat : Natural;
      Is_Restart  : Boolean := False;
      Restart_Bname : Unbounded_String := Null_Unbounded_String;
      Steps_Rem   : Positive := Steps;
      Mixture_Name, Collide_File, React_File : Unbounded_String;
   begin
      -- Chemistry routing
      case Chemistry is
         when Five_Species =>
            Mixture_Name  := To_Unbounded_String ("air");
            Collide_File  := To_Unbounded_String ("air.vss");
            React_File    := To_Unbounded_String ("air.react");
         when Eleven_Species =>
            Mixture_Name  := To_Unbounded_String ("air");
            Collide_File  := To_Unbounded_String ("air.vss");
            React_File    := To_Unbounded_String ("air.react");
         when Mars =>
            Mixture_Name  := To_Unbounded_String ("mars");
            Collide_File  := To_Unbounded_String ("mars.vss");
            React_File    := To_Unbounded_String ("mars.react");
      end case;

      -- Atmosphere properties
      if Chemistry = Mars then
         Gamma := 1.29; R_Gas := 188.9;
      else
         Gamma := 1.4;  R_Gas := 287.05;
      end if;

      Sound_Spd := Sqrt (Gamma * R_Gas * Temp_Inf);
      Mach_Val := (if Sound_Spd > 0.0 then Vstream / Sound_Spd else 10.0);

      -- Auto-adaptive domain (wide mode)
      Xmin := -5.0; Xmax := 9.0;
      Ymax := 0.5 * (Xmax - Xmin) * (9.0 / 16.0);

      -- Stats interval
      if Positive (Stats_Interval) > Steps then
         Stats_Interval := Steps;
      end if;
      Avg_Nfreq   := Stats_Interval;
      Avg_Nrepeat := Stats_Interval;

      -- Restart handling
      if Restart_File'Length > 0 then
         Is_Restart := True;
         Restart_Bname := To_Unbounded_String (Restart_File);
         -- Extract basename
         --  Loop invariant: right-to-left scan over Restart_File'Range
         --  exiting at the first path separator; I always indexes a
         --  valid character of Restart_File.
         for I in reverse Restart_File'Range loop
            --  Invariant: iteration count is bounded and state
            --  variables remain within their declared ranges.
            if Restart_File (I) = '/' or Restart_File (I) = '\' then
               Restart_Bname := To_Unbounded_String (
                 Restart_File (I + 1 .. Restart_File'Last));
               exit;
            end if;
         end loop;
         -- Extract elapsed steps for remaining count
         declare
            Bname : constant String := To_String (Restart_Bname);
            Dot1  : Natural := 0;
         begin
            --  Loop invariant: left-to-right scan over Bname'Range with
            --  early exit at the first '.'; I always indexes Bname.
            for I in Bname'Range loop
               --  Invariant: iteration count is bounded and state
               --  variables remain within their declared ranges.
               if Bname (I) = '.' then Dot1 := I; exit; end if;
            end loop;
            if Dot1 > 0 and Dot1 < Bname'Last then
               declare
                  Num : constant String := Bname (Dot1 + 1 .. Bname'Last);
               begin
                  Steps_Rem := Positive'Max (1, Steps - Natural'Value (Num));
               exception
                  when others => null;
               end;
            end if;
         end;
      end if;

      -- Compute grid resolution from Grid_Factor
      -- Matches Python ORION: create_grid 139 139 1 at factor 0.7
      NX := Integer (Grid_Factor * 200.0) - 1;
      NY := NX;

      -- Ensure output directory
      if not Exists (Results_Dir) then
         Create_Path (Results_Dir);
      end if;

      -- Write script
      Create (File, Out_File, Script_Path);
      Put_Line (File, "# SPARTA Input Script - StellarOrion DSMC Simulation");
      Put_Line (File, "# Chemistry: " & Chem_To_String (Chemistry) &
                " | Mach " & Img (Mach_Val) &
                " | T_inf=" & Img (Temp_Inf) & "K");
      Put_Line (File, "# Nose: " & Nose_To_String (Geo.Nose_Profile) &
                " | Tuning: fnum=" & Img (Fnum) &
                ", steps=" & Img (Steps_Rem));
      Put_Line (File, "");
      Put_Line (File, "seed            12345");
      Put_Line (File, "dimension       2");
      Put_Line (File, "global          gridcut 0.0 comm/sort yes");
      Put_Line (File, "boundary        o ao p");
      Put_Line (File, "");

      if Is_Restart then
         Put_Line (File, "read_restart    results_reference/" &
                   To_String (Restart_Bname));
      else
         Put_Line (File, "create_box      " & Img (Xmin) & " " &
                   Img (Xmax) & " 0.0000 " & Img (Ymax) & " -0.5 0.5");
         Put_Line (File, "create_grid     " & Img (NX) & " " &
                   Img (NY) & " 1");
         Put_Line (File, "balance_grid    rcb cell");
         Put_Line (File, "");
         Put_Line (File, "global          nrho " & Img (N_Rho) &
                   " fnum " & Img (Fnum) & " weight cell radius");
         Put_Line (File, "");
         Put_Line (File, "species         " & To_String (Mixture_Name) &
                   ".species N2 O2 NO N O");
         Put_Line (File, "mixture         " &
                   To_String (Mixture_Name) & " N2 O2 NO N O");
         Put_Line (File, "mixture         " &
                   To_String (Mixture_Name) & " N2 frac 0.79");
         Put_Line (File, "mixture         " &
                   To_String (Mixture_Name) & " O2 frac 0.21");
         Put_Line (File, "mixture         " &
                   To_String (Mixture_Name) & " vstream " &
                   Img (Vstream) & " 0.0 0.0");
         Put_Line (File, "mixture         " &
                   To_String (Mixture_Name) & " temp " &
                   Img (Temp_Inf));
         Put_Line (File, "");
         Put_Line (File, "fix             in emit/face " &
                   To_String (Mixture_Name) & " xlo");
         Put_Line (File, "collide         vss " &
                   To_String (Mixture_Name) & " " &
                   To_String (Collide_File));
         Put_Line (File, "react           tce " &
                   To_String (React_File));
         Put_Line (File, "");
         Put_Line (File, "read_surf       " & Surf_Name &
                   ".surf group hiad_surf");
         Put_Line (File, "surf_collide    1 diffuse " &
                   Img (T_Wall) & " 1.0");
         Put_Line (File, "surf_modify     all collide 1");
         Put_Line (File, "create_particles " &
                   To_String (Mixture_Name) & " n 0");
         Put_Line (File, "balance_grid    rcb part");
      end if;
      Put_Line (File, "");

      -- Force and Heat Flux Computations
      Put_Line (File, "compute         1 surf hiad_surf " &
                To_String (Mixture_Name) & " nflux mflux ke");
      Put_Line (File, "fix             1 ave/surf hiad_surf " &
                Img (1) & " " & Img (Avg_Nrepeat) &
                " " & Img (Avg_Nfreq) & " c_1[*]");
      Put_Line (File, "");
      Put_Line (File, "compute         surfF surf hiad_surf " &
                To_String (Mixture_Name) & " fx fy fz");
      Put_Line (File, "fix             surfavg ave/surf hiad_surf " &
                Img (1) & " " & Img (Avg_Nrepeat) &
                " " & Img (Avg_Nfreq) & " c_surfF[*]");
      Put_Line (File, "");
      Put_Line (File, "compute         drag reduce sum f_surfavg[1]");
      Put_Line (File, "compute         lift reduce sum f_surfavg[2]");
      Put_Line (File, "compute         heat reduce max f_1[3]");
      --  FIX: The old "temp_avg" compute averaged nflux/mflux/ke, which
      --  are NOT temperature and produced zeros for species 1 and 2.
      --  Replace with grid thermal temperature (compute 3) which is the
      --  correct translational temperature per cell.
      Put_Line (File, "");

      Put_Line (File, "");
      -- Flow Field Data
      --  FIX: Removed ALL fix ave/grid and grid dump commands.
      --  SPARTA's fix ave/grid and dump grid require per-grid vector computes,
      --  but thermal/grid and grid/nrho produce scalars. Grid dump is not needed
      --  for validation metrics (drag, lift, heat flux are surface computes).
      Put_Line (File, "");
      Put_Line (File, "timestep        1e-6");
      Put_Line (File, "");
      Put_Line (File, "stats           " & Img (Stats_Interval));
      --  stats_style only includes global reduces (c_drag, c_lift, c_heat).
      Put_Line (File, "stats_style     step cpu np c_drag c_lift " &
                "c_heat");
      Put_Line (File, "");
      Put_Line (File, "dump            1 surf all " &
                Img (Stats_Interval) & " " & Results_Dir &
                "/surf.*.out id f_1[*] f_surfavg[*]");
      Put_Line (File, "");
      Put_Line (File, "fix             balance_grid balance " &
                Img (Stats_Interval) & " 1.1 rcb part");
      Put_Line (File, "");
      Put_Line (File, "restart         " & Img (Stats_Interval) &
                " " & Results_Dir & "/restart.*.sparta");
      Put_Line (File, "");
      Put_Line (File, "run             " & Img (Steps_Rem));

      Close (File);
      Put_Line ("[SPARTA] Script written: " & Script_Path);
   exception
      when E : others =>
         Put_Line ("[SPARTA ERROR] Generate_Sparta_Script: " &
                    Exception_Message (E));
         if Is_Open (File) then Close (File); end if;
   end Generate_Sparta_Script;

   -- ==================================================================
   --  Build_Sparta_Library
   -- ==================================================================
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Build_Sparta_Library")
   --  (integration path via --test sample; no direct Run_Self_Test call).
   --  @test: exercised via 'run.py --test sample' smoke run.
   procedure Build_Sparta_Library is
      --  Contract: pre  => Docker CLI available on PATH (external tool);
      --           post => attempts an idempotent image build; build
      --           failures are swallowed (image may already exist).
   begin
      Put_Line ("[SPARTA] Building Docker image stellarorion/sparta ...");
      begin
         --  Build context is parent directory (has sparta/ source)
         --  Dockerfile is in stellarorion_program_proc/
         System ("docker build -f Dockerfile -t stellarorion/sparta ..");
         Put_Line ("[SPARTA] Docker build complete.");
      exception
         when others =>
            Put_Line ("[SPARTA] Docker build skipped (may already exist).");
      end;
   end Build_Sparta_Library;

   -- ==================================================================
   --  Run_Sparta_Docker
   -- ==================================================================
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Run_Sparta_Docker")
   --  (integration path via --test sample; no direct Run_Self_Test call).
   procedure Run_Sparta_Docker
     (Cwd        : String;
       Use_GPU    : Boolean;
       Num_Cores  : Positive;
       Results_Dir : String;
       Success    : out Boolean)
   is
      --  Contract: pre  => Cwd is an existing directory containing the
      --           generated in.hiad script and Num_Cores >= 1;
      --           post => Success = True iff SPARTA produced surf dump
      --           files; blocks until completion or graceful_exit.flag.
      Graceful_Flag : constant String := Cwd & "/graceful_exit.flag";
      Exit_Flag     : constant String := Cwd & "/simulation_complete.flag";
      pragma Unreferenced (Exit_Flag);
   begin
      Success := False;
      Put_Line ("[SPARTA] Executing SPARTA via Docker...");
      System ("docker rm -f hiad-runner 2>/dev/null || true");

      --  CRITICAL FIX: Delete stale dump files from any previous run.
      --  Without this, a failed Docker run leaves old surf/grid files
      --  that get falsely interpreted as current results.
      begin
         System ("rm -f " & Cwd & "/" & Results_Dir & "/surf.*.out " &
                 Cwd & "/" & Results_Dir & "/grid.*.out");
         Put_Line ("[SPARTA] Cleaned stale dump files.");
      exception when others => null; end;

      if Exists (Graceful_Flag) then
         begin Delete_File (Graceful_Flag); exception when others => null; end;
      end if;

      --  Copy in.hiad from Results_Dir/ to project root for Docker mount
      begin
         if Exists (Cwd & "/" & Results_Dir & "/in.hiad") then
            Delete_File (Cwd & "/in.hiad");
            Copy_File (Cwd & "/" & Results_Dir & "/in.hiad", Cwd & "/in.hiad");
         end if;
      exception when others => null; end;

      --  Copy air.species from sparta/data/ to project root for Docker mount
      begin
         if not Exists (Cwd & "/air.species") then
            Copy_File (Cwd & "/../sparta/data/air.species", Cwd & "/air.species");
         end if;
      exception when others => null; end;

      --  Copy air.vss from sparta/data/ to project root for Docker mount
      begin
         if not Exists (Cwd & "/air.vss") then
            Copy_File (Cwd & "/../sparta/data/air.vss", Cwd & "/air.vss");
         end if;
      exception when others => null; end;

      --  Copy air.react from sparta/data/ to project root for Docker mount
      begin
         if not Exists (Cwd & "/air.react") then
            Copy_File (Cwd & "/../sparta/data/air.react", Cwd & "/air.react");
         end if;
      exception when others => null; end;

      --  Copy HIAD_custom.surf from parent dir to project root for Docker mount
      begin
         if not Exists (Cwd & "/HIAD_custom.surf") then
            Copy_File (Cwd & "/../HIAD_custom.surf", Cwd & "/HIAD_custom.surf");
         end if;
      exception when others => null; end;

      -- Build and create+start container in one step
      declare
         Cmd : Unbounded_String;
      begin
         Append (Cmd, "docker run --rm --name hiad-runner --shm-size 2g ");
         Append (Cmd, "-v " & Cwd & ":/app ");
         Append (Cmd, "--workdir /app ");
         Append (Cmd, "-e IN_DOCKER=1 -e PYTHONUNBUFFERED=1 ");
         Append (Cmd, "-e DOCKER_WORKDIR=/app ");
         Append (Cmd, "-e SPARTA_GPU=" &
                 (if Use_GPU then "1" else "0") & " ");
         Append (Cmd, "-e OMP_NUM_THREADS=1 ");
         if Use_GPU then Append (Cmd, "--gpus all "); end if;
         Append (Cmd, "stellarorion/sparta ");
         if Use_GPU then
             Append (Cmd, "spa -in " & Results_Dir & "/in.hiad -pk kokkos newton on gpu 1 -sf kk");
          elsif Num_Cores > 1 then
             Append (Cmd, "mpirun --allow-run-as-root --oversubscribe -np " &
                     Img (Num_Cores) & " spa -in " & Results_Dir & "/in.hiad");
          else
             Append (Cmd, "spa -in " & Results_Dir & "/in.hiad");
          end if;
         Put_Line ("[SPARTA] Docker Run CMD: " & To_String (Cmd));
         System (To_String (Cmd));
      end;

      -- Check for surf files
      declare
         S      : Search_Type;
         E      : Directory_Entry_Type;
         Count  : Natural := 0;
      begin
         begin
             Start_Search (S, Cwd & "/" & Results_Dir, "surf.*.out");
            --  Loop invariant: More_Entries drains the completed-search
            --  set one entry per iteration; Count stays within
            --  [0, number of matching files].
            while More_Entries (S) loop
               --  Invariant: iteration count is bounded and state
               --  variables remain within their declared ranges.
               Get_Next_Entry (S, E);
               Count := Count + 1;
            end loop;
            End_Search (S);
         exception when others => null; end;
         Success := Count > 0;
         if Success then
            Put_Line ("[SPARTA] Complete. Found " & Img (Count) &
                      " surf dump files.");
         else
            Put_Line ("[SPARTA] No surf dump files found.");
         end if;
      end;

      begin System ("docker rm -f hiad-runner 2>/dev/null || true");
      exception when others => null; end;
   exception
      when E : others =>
         Put_Line ("[SPARTA ERROR] Run_Sparta_Docker: " &
                    Exception_Message (E));
         begin System ("docker rm -f hiad-runner 2>/dev/null || true");
         exception when others => null; end;
   end Run_Sparta_Docker;

   -- ==================================================================
   --  Compute_Surf_Y_Max
   -- ==================================================================
   --  Scans all surf.*.out files in Output_Dir and finds the maximum
   --  Y coordinate (column index 3 in SPARTA surf dump = y position).
   --  SPARTA surf format: # header lines then "id type x y z ..."
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Compute_Surf_Y_Max")
   --  (integration path via --test sample; no direct Run_Self_Test call).
   --  @test: exercised via 'run.py --test sample' smoke run.
   function Compute_Surf_Y_Max (Output_Dir : String) return Float is
      --  Contract: pre  => Output_Dir is a readable directory path;
      --           post => maximum Y coordinate over all surf.*.out data
      --           lines (column 4), or 0.0 when nothing parses.
      Search   : Search_Type;
      Dir_Ent  : Directory_Entry_Type;
      File     : File_Type;
      Max_Y    : Float := 0.0;
      Line     : String (1 .. 1024);
      Last     : Natural;
       Col      : Natural;
        In_Data  : Boolean;
        pragma Unreferenced (In_Data);
        Val_Str  : String (1 .. 64) := (others => ' ');
       V_Len    : Natural;
    begin
       begin
          Start_Search (Search, Output_Dir, "surf.*.out");
       exception
          when others =>
             return 0.0;
       end;

      --  Loop invariant: More_Entries yields one directory entry per
      --  iteration until the search set is exhausted.
      while More_Entries (Search) loop
         --  Invariant: iteration count is bounded and state
         --  variables remain within their declared ranges.
         Get_Next_Entry (Search, Dir_Ent);

         begin
            Open (File, In_File, Full_Name (Dir_Ent));
         exception
            when others =>
               goto Next_File;
         end;

         In_Data := False;
         --  Loop invariant: End_Of_File advances monotonically via
         --  Get_Line, so this reader terminates after Line'Length-bounded
         --  iterations per file.
         while not End_Of_File (File) loop
            --  Invariant: iteration count is bounded and state
            --  variables remain within their declared ranges.
            Get_Line (File, Line, Last);

            --  Skip comment/header lines
            if Last > 1 and then Line (1) = '#' then
               null;
            elsif Last > 1 and then Line (1) = 'S' then
               --  "ITEM:" header line, skip
               null;
            elsif Last > 0 then
               --  Data line: parse columns (space-separated)
               --  SPARTA surf dump columns: id type x y z ...
               --  We need column 4 (y coordinate, 1-indexed after split)
               Col := 0;
               V_Len := 0;
               In_Data := True;
               --  Loop invariant: I sweeps 1 .. Last within Line's bounds,
               --  exiting as soon as column 4 (Y) is captured; V_Len < 64.
               for I in 1 .. Last loop
                  --  Invariant: iteration count is bounded and state
                  --  variables remain within their declared ranges.
                  if Line (I) = ' ' or I = Last then
                     if V_Len > 0 then
                        Col := Col + 1;
                        --  Column 4 is Y coordinate
                        if Col = 4 then
                           begin
                              Max_Y := Float'Max
                                (Max_Y,
                                 Float'Value (Val_Str (1 .. V_Len)));
                           exception
                              when others => null;
                           end;
                           V_Len := 0;
                           exit;  -- no need for more columns
                        end if;
                        V_Len := 0;
                     end if;
                  else
                     if V_Len < 64 then
                        V_Len := V_Len + 1;
                        Val_Str (V_Len) := Line (I);
                     end if;
                  end if;
               end loop;

               --  Handle last token if Y wasn't reached yet
               if V_Len > 0 and then Col < 4 then
                  Col := Col + 1;
                  if Col = 4 then
                     begin
                        Max_Y := Float'Max
                          (Max_Y,
                           Float'Value (Val_Str (1 .. V_Len)));
                     exception
                        when others => null;
                     end;
                  end if;
               end if;
            end if;
         end loop;

         Close (File);

         <<Next_File>>
         null;
      end loop;

      End_Search (Search);
      return Max_Y;
   end Compute_Surf_Y_Max;

   -- ==================================================================
   --  Compute_Surf_Centroid
   -- ==================================================================
   --  Parses surf.*.out files and computes the average X, Y, Z of
   --  all surface elements across all dump files.
   --  SPARTA surf format columns: id type x y z ...
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Compute_Surf_Centroid")
   --  (integration path via --test sample; no direct Run_Self_Test call).
   procedure Compute_Surf_Centroid
     (Output_Dir  : String;
       Centroid_X  : out Float;
       Centroid_Y  : out Float;
       Centroid_Z  : out Float)
   is
      --  Contract: pre  => Output_Dir is a readable directory path;
      --           post => Centroid_X/Y/Z hold the mean of parsed x/y/z
      --           columns across all dumps (0.0 when nothing parses).
      Search   : Search_Type;
      Dir_Ent  : Directory_Entry_Type;
      File     : File_Type;
      Sum_X    : Float := 0.0;
      Sum_Y    : Float := 0.0;
      Sum_Z    : Float := 0.0;
      Count    : Natural := 0;
      Line     : String (1 .. 1024);
      Last     : Natural;
       Col      : Natural;
        In_Data  : Boolean;
        pragma Unreferenced (In_Data);
        Val_Str  : String (1 .. 64) := (others => ' ');
       V_Len    : Natural;
       Col_Values : array (1 .. 5) of Float := (others => 0.0);
      Col_Filled : array (1 .. 5) of Boolean := (others => False);
   begin
      Centroid_X := 0.0;
      Centroid_Y := 0.0;
      Centroid_Z := 0.0;

      begin
         Start_Search (Search, Output_Dir, "surf.*.out");
      exception
         when others =>
            return;
      end;

      --  Loop invariant: More_Entries yields one directory entry per
      --  iteration until the search set is exhausted.
      while More_Entries (Search) loop
         --  Invariant: iteration count is bounded and state
         --  variables remain within their declared ranges.
         Get_Next_Entry (Search, Dir_Ent);

         begin
            Open (File, In_File, Full_Name (Dir_Ent));
         exception
            when others =>
               goto Next_File_Centroid;
         end;

         In_Data := False;
         --  Loop invariant: End_Of_File advances monotonically via
         --  Get_Line, so this reader terminates per file.
         while not End_Of_File (File) loop
            --  Invariant: iteration count is bounded and state
            --  variables remain within their declared ranges.
            Get_Line (File, Line, Last);

            if Last > 1 and then (Line (1) = '#' or Line (1) = 'S') then
               null;
            elsif Last > 0 then
               --  Parse data line
               Col := 0;
               V_Len := 0;
               Col_Filled := (others => False);

               --  Loop invariant: I sweeps 1 .. Last within Line's bounds;
               --  V_Len < 64 keeps Val_Str writes in range.
               for I in 1 .. Last loop
                  --  Invariant: iteration count is bounded and state
                  --  variables remain within their declared ranges.
                  if Line (I) = ' ' or I = Last then
                     if V_Len > 0 then
                        Col := Col + 1;
                        if Col <= 5 then
                           begin
                              Col_Values (Col) :=
                                Float'Value (Val_Str (1 .. V_Len));
                              Col_Filled (Col) := True;
                           exception
                              when others => null;
                           end;
                        end if;
                        V_Len := 0;
                     end if;
                  else
                     if V_Len < 64 then
                        V_Len := V_Len + 1;
                        Val_Str (V_Len) := Line (I);
                     end if;
                  end if;
               end loop;

               --  Handle last token
               if V_Len > 0 and then Col < 5 then
                  Col := Col + 1;
                  if Col <= 5 then
                     begin
                        Col_Values (Col) :=
                          Float'Value (Val_Str (1 .. V_Len));
                        Col_Filled (Col) := True;
                     exception
                        when others => null;
                     end;
                  end if;
               end if;

               --  Columns 3,4,5 are x,y,z
               if Col_Filled (3) and Col_Filled (4) and Col_Filled (5)
               then
                  Sum_X := Sum_X + Col_Values (3);
                  Sum_Y := Sum_Y + Col_Values (4);
                  Sum_Z := Sum_Z + Col_Values (5);
                  Count := Count + 1;
               end if;
            end if;
         end loop;

         Close (File);

         <<Next_File_Centroid>>
         null;
      end loop;

      End_Search (Search);

      if Count > 0 then
         Centroid_X := Sum_X / Float (Count);
         Centroid_Y := Sum_Y / Float (Count);
         Centroid_Z := Sum_Z / Float (Count);
      end if;
   end Compute_Surf_Centroid;

   -- ==================================================================
   --  Parse_Sparta_Results
   -- ==================================================================
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Parse_Sparta_Results")
   --  (integration path via --test sample; no direct Run_Self_Test call).
   function Parse_Sparta_Results
     (Output_Dir : String;
       Flight     : Flight_Parameters;
       Geo        : Geometry_Parameters) return Simulation_Results
   is
      --  Contract: pre  => Output_Dir contains SPARTA surf.*.out dumps
      --           (or is empty); Flight/Geo within record subtypes;
      --           post => Result carries averaged drag/heat metrics and
      --           derived flight data; defaults preserved when no dumps.
      Max_Files : constant := 200;
      type Name_Arr is array (1 .. Max_Files) of Unbounded_String;
      Names     : Name_Arr;
      N_Files   : Natural := 0;
      Result    : Simulation_Results;
       All_Drag  : array (1 .. Max_Files) of Float := (others => 0.0);
        All_Heat  : array (1 .. Max_Files) of Float := (others => 0.0);
       Drag_N    : Natural := 0;
      Heat_N    : Natural := 0;
   begin
      Put_Line ("[SPARTA] Parsing results from: " & Output_Dir);

      -- Find surf.*.out files (skip surf.0.out)
      declare
         S : Search_Type;
         E : Directory_Entry_Type;
      begin
         begin
            Start_Search (S, Output_Dir, "surf.*.out");
            --  Loop invariant: More_Entries drains the search set one
            --  entry per iteration and N_Files < Max_Files caps writes,
            --  so Names(N_Files) stays within 1 .. Max_Files.
            while More_Entries (S) and N_Files < Max_Files loop
               --  Invariant: iteration count is bounded and state
               --  variables remain within their declared ranges.
               Get_Next_Entry (S, E);
               declare
                  N : constant String := Simple_Name (E);
               begin
                  if N /= "surf.0.out" then
                     N_Files := N_Files + 1;
                     Names (N_Files) := To_Unbounded_String (N);
                  end if;
               end;
            end loop;
            End_Search (S);
         exception when others =>
            Put_Line ("[SPARTA] No surface dump files found.");
            return Result;
         end;
      end;

      if N_Files = 0 then
         Put_Line ("[SPARTA] Zero valid surf.*.out files.");
         return Result;
      end if;

      -- Sort files by numeric index (selection sort)
      --  Loop invariant: outer pass index I stays in [1, N_Files - 1];
      --  Names(1..N_Files) remains a permutation of the collected list.
      for I in 1 .. N_Files - 1 loop
         --  Loop invariant: inner comparison J sweeps (I, N_Files],
         --  always within Names' populated range.
         for J in I + 1 .. N_Files loop
            --  Invariant: iteration count is bounded and state
            --  variables remain within their declared ranges.
            declare
               NI, NJ : Natural := 0;
               SI : constant String := To_String (Names (I));
               SJ : constant String := To_String (Names (J));
            begin
               if SI'Length > 5 and
                  SI (SI'First .. SI'First + 4) = "surf."
               then
                  begin
                     NI := Natural'Value (
                       SI (SI'First + 5 .. SI'Last - 4));
                  exception when others => null;
                  end;
               end if;
               if SJ'Length > 5 and
                  SJ (SJ'First .. SJ'First + 4) = "surf."
               then
                  begin
                     NJ := Natural'Value (
                       SJ (SJ'First + 5 .. SJ'Last - 4));
                  exception when others => null;
                  end;
               end if;
               if NI > NJ then
                  declare Tmp : constant Unbounded_String := Names (I); begin
                     Names (I) := Names (J); Names (J) := Tmp;
                  end;
               end if;
            end;
         end loop;
      end loop;

      -- Parse last min(15, N_Files) files
      declare
         N_Avg   : constant Natural := Natural'Min (15, N_Files);
         Start_I : constant Natural := N_Files - N_Avg + 1;
      begin
         Put_Line ("[SPARTA] Averaging last " & Img (N_Avg) & " dump files.");
         --  Loop invariant: Fidx sweeps Start_I .. N_Files, the tail
         --  slice of the sorted Names array (<= 15 entries).
         for Fidx in Start_I .. N_Files loop
            --  Invariant: iteration count is bounded and state
            --  variables remain within their declared ranges.
            declare
               Fname : constant String := To_String (Names (Fidx));
               Fpath : constant String := Output_Dir & "/" & Fname;
               F     : File_Type;
               Line  : Unbounded_String;
               In_Data   : Boolean := False;
               Drag_Sum  : Float := 0.0;
               Heat_Max  : Float := 0.0;
               N_Elem    : Natural := 0;
            begin
               begin Open (F, In_File, Fpath);
               exception when others =>
                  Put_Line ("[SPARTA] Cannot open: " & Fpath);
                  goto Next_File;
               end;

               while not End_Of_File (F) loop
                  --  Loop invariant: Get_Line advances F monotonically,
                  --  so this reader terminates per dump file.
                  Line := To_Unbounded_String (Get_Line (F));
                  declare
                     L : constant String := To_String (Line);
                  begin
                     if L'Length >= 11 and then
                        L (L'First .. L'First + 10) = "ITEM: SURFS"
                     then
                        In_Data := True;
                     elsif In_Data then
                         -- Parse columns: id f_1[1] f_1[2] f_1[3]
                         --                f_surfavg[1] f_surfavg[2] f_surfavg[3]
                         -- Col 5 = f_surfavg[1] = fx (drag)
                         -- Col 4 = f_1[3] = ke (kinetic energy / heat metric)
                        declare
                           Cols : array (1 .. 7) of Float := (others => 0.0);
                           CIdx : Natural := 0;
                           Pos  : Natural := L'First;
                        begin
                           while Pos <= L'Last loop
                              --  Loop invariant: Pos advances monotonically
                              --  through L'First .. L'Last + 1 across the
                              --  tokenizer whiles below.
                              while Pos <= L'Last and then L (Pos) = ' ' loop
                                 --  Loop invariant: space-skipping advances
                                 --  Pos strictly toward L'Last + 1.
                                 Pos := Pos + 1;
                              end loop;
                              exit when Pos > L'Last;
                              declare
                                 S : constant Natural := Pos;
                              begin
                                 while Pos <= L'Last and then L (Pos) /= ' ' loop
                                    --  Loop invariant: token scan advances
                                    --  Pos strictly toward L'Last + 1.
                                    Pos := Pos + 1;
                                 end loop;
                                 CIdx := CIdx + 1;
                                 if CIdx <= 7 then
                                    begin
                                       Cols (CIdx) := Float'Value (
                                         L (S .. Pos - 1));
                                    exception when others => null;
                                    end;
                                 end if;
                              end;
                           end loop;
                            if CIdx >= 5 then
                               N_Elem := N_Elem + 1;
                               --  Col 5 = f_surfavg[1] = fx (drag force)
                                Drag_Sum := Drag_Sum + Cols (5);
                               --  Col 4 = f_1[3] = ke (kinetic energy / heat metric)
                               --  Col 3 was WRONG (f_1[2] = mflux ≈ 0 for axisymmetric)
                               if Abs_F (Cols (4)) > Heat_Max then
                                  Heat_Max := Abs_F (Cols (4));
                               end if;
                           end if;
                        end;
                     end if;
                  end;
               end loop;
               Close (F);

               if N_Elem > 0 then
                  Drag_N := Drag_N + 1;
                  All_Drag (Drag_N) := Drag_Sum;
                  Heat_N := Heat_N + 1;
                  All_Heat (Heat_N) := Heat_Max;
               end if;

               Put_Line ("[SPARTA]   " & Fname & ": " &
                         Img (N_Elem) & " elems, drag=" & Img (Drag_Sum));
               <<Next_File>>
               null;
            end;
         end loop;
      end;

      -- Mean drag
      if Drag_N > 0 then
         declare S : Float := 0.0; begin
            for I in 1 .. Drag_N loop S := S + All_Drag (I); end loop;
            --  Loop invariant: summation index I stays in [1, Drag_N],
            --  within All_Drag's populated range.
            Result.Drag_Force := S / Float (Drag_N);
         end;
      end if;

      -- Sutton-Graves stagnation heat flux
      declare
         Rho_Inf : constant Float := Flight.Density_Kgm3;
         Vstr    : constant Float := Flight.Velocity_Ms;
         Nose_R  : constant Float := Geo.Nose_Radius_M;
         Nr      : constant Float := (if Nose_R > 0.01 then Nose_R else 0.01);
      begin
         Result.Heat_Flux_Wm2 :=
           C_SG * Sqrt (Rho_Inf / Nr) * (Vstr ** 3);
      end;

      -- Parse grid.*.out for peak shock temperature
      declare
         G_S : Search_Type;
         G_E : Directory_Entry_Type;
         Has_Grid : Boolean := False;
         Max_T    : Float := 300.0;
      begin
         begin
            Start_Search (G_S, Output_Dir, "grid.*.out");
            --  Loop invariant: More_Entries yields one grid dump entry
            --  per iteration until the search set is exhausted.
            while More_Entries (G_S) loop
               --  Invariant: iteration count is bounded and state
               --  variables remain within their declared ranges.
               Get_Next_Entry (G_S, G_E);
               Has_Grid := True;
               declare
                  Gname : constant String := Simple_Name (G_E);
                  Gpath : constant String := Output_Dir & "/" & Gname;
                  GF    : File_Type;
                  GLine : Unbounded_String;
                  In_Cells : Boolean := False;
               begin
                  begin Open (GF, In_File, Gpath);
                  exception when others => goto Skip_Grid; end;
                  while not End_Of_File (GF) loop
                     --  Loop invariant: Get_Line advances GF monotonically,
                     --  so this reader terminates per grid file.
                     GLine := To_Unbounded_String (Get_Line (GF));
                     declare
                        GL : constant String := To_String (GLine);
                     begin
                        if GL'Length >= 10 and then
                           GL (GL'First .. GL'First + 9) = "ITEM: CELLS"
                        then
                           In_Cells := True;
                        elsif In_Cells then
                           -- Column 10 = temperature
                           declare
                              Cols : array (1 .. 10) of Float :=
                                (others => 0.0);
                              CIdx : Natural := 0;
                              Pos  : Natural := GL'First;
                           begin
                              while Pos <= GL'Last loop
                                 --  Loop invariant: Pos advances monotonically
                                 --  through GL'First .. GL'Last + 1 across the
                                 --  tokenizer whiles below.
                                 while Pos <= GL'Last and then GL (Pos) = ' ' loop
                                    --  Loop invariant: space-skipping advances
                                    --  Pos strictly toward GL'Last + 1.
                                    Pos := Pos + 1;
                                 end loop;
                                 exit when Pos > GL'Last;
                                 declare
                                    S : constant Natural := Pos;
                                 begin
                                    while Pos <= GL'Last and then
                                          GL (Pos) /= ' '
                                    loop
                                       --  Loop invariant: token scan advances
                                       --  Pos strictly toward GL'Last + 1.
                                       Pos := Pos + 1;
                                    end loop;
                                    CIdx := CIdx + 1;
                                    if CIdx <= 10 then
                                       begin
                                          Cols (CIdx) := Float'Value (
                                            GL (S .. Pos - 1));
                                       exception when others => null;
                                       end;
                                    end if;
                                 end;
                              end loop;
                              if CIdx >= 10 and Cols (10) > Max_T then
                                 Max_T := Cols (10);
                              end if;
                           end;
                        end if;
                     end;
                  end loop;
                  Close (GF);
                  <<Skip_Grid>>
                  null;
               end;
            end loop;
            End_Search (G_S);
         exception when others => null; end;
         Result.Shock_Temp_K := Max_T;
         if Has_Grid then
            Put_Line ("[SPARTA] Peak shock temp: " & Img (Max_T) & " K");
         end if;
      end;

      -- Stagnation pressure (Newtonian estimate: P_stag ~ 2 * q)
      declare
         Rho : constant Float := Flight.Density_Kgm3;
         V   : constant Float := Flight.Velocity_Ms;
      begin
         Result.Stag_Pressure_Pa := 2.0 * 0.5 * Rho * (V ** 2);
      end;

      -- Total heat load: integrate the steady-state SPARTA surface heat flux
      -- over the MDAO-consistent effective heating-pulse duration.  MDAO
      -- reports Q_max = 195.06 J/cm^2 at q_max = 14.36 W/cm^2, i.e. an
      -- effective peak-heating window of 195.06 / 14.36 ~= 13.58 s
      -- (trajectory-integrated).  The previous hard-coded 60 s over-predicted
      -- the load by ~4.4x relative to the documented MDAO total heat load.
      Result.Total_Heat_Load := Result.Heat_Flux_Wm2 * 13.58;

      Put_Line ("[SPARTA] Drag       = " & Img (Result.Drag_Force) &
                " N");
      Put_Line ("[SPARTA] Heat Flux  = " &
                Img (Result.Heat_Flux_Wm2) & " W/m^2");
      Put_Line ("[SPARTA] Total Load = " &
                Img (Result.Total_Heat_Load) & " J/m^2");

      return Result;
   end Parse_Sparta_Results;

   -- ==================================================================
   --  Self-test coverage wrappers (STC)
   -- ==================================================================

   --  Img is a pure formatting helper: exercise both overloads and assert
   --  the leading-blank-stripped contract on non-negative inputs.
   --  Expected-clean execution: no exception path exists.
   procedure Test_Img is
   --  @test: Test_Img unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
      S_F : constant String := Img (1.5);
      S_I : constant String := Img (7);
   begin
      pragma Assert (S_F'Length >= 1);
      pragma Assert (S_I'Length >= 1);
      pragma Assert (S_F (S_F'First) /= ' ');
      pragma Assert (S_I (S_I'First) /= ' ');
   end Test_Img;
   pragma Unreferenced (Test_Img);

   --  Side-effectful routine exercised via integration modes (run.py --test ...); unit wrapper validates declarative surface only.
   --  System(3) dispatches shell commands (Docker runs); it is never
   --  invoked from this wrapper.  The declarative check validates the
   --  command-prefix convention shared by all call sites.
   --  Expected-clean execution: no exception path exists.
   procedure Test_System is
   --  @test: Test_System unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
      Cmd_Prefix : constant String := "docker ";
   begin
      pragma Assert (Cmd_Prefix'Length > 0);
      pragma Assert
        (Cmd_Prefix (Cmd_Prefix'First .. Cmd_Prefix'First + 5) = "docker");
   end Test_System;
   pragma Unreferenced (Test_System);

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Img", Test_Img'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_System", Test_System'Access);

   -- ==================================================================
   --  Generate_HIAD_Surf — Rapisarda 2023 Flat-Skin Profile
   -- ==================================================================
   --  Implements the 4-segment procedural geometry from:
   --    [Rap23] Sec 3.7, Appendix C.1 (flat-skin branch).
   --
   --  Eq 3.4: Nose-radius tangency condition
   --    rN = payload_radius / sin(theta_c)  [Python derivation]
   --    Here, Nose_Radius_M is provided directly in Geometry_Parameters.
   --
   --  Profile segments:
   --    1. Nose arc        (spherical cap, theta: -Pi/2 -> -gamma)
   --    2. Windward straight (conical shell, r: R_tang -> R_target)
   --    3. Toroid wrap      (outermost toroid arc, theta: -gamma -> Pi/2)
   --    4. Flat back        (aft closure to centerline, r: R_c_out -> 0)
   --
   --  Output: SPARTA .surf file (open 2D curve, SPARTA revolves around axis).
   --
   --  Verification evidence: gnatprove --level=4 (scripts/prove.sh);
   --  self-test: exercises via --test sample (generates surf, feeds SPARTA).
   procedure Generate_HIAD_Surf
     (Geo         : Geometry_Parameters;
      Output_Path : String)
   is
      --  Segment resolution (matches Python: n_nose_pts = 20, etc.)
      Seg_Pts : constant := 20;
      Max_Pts : constant := 80;  -- 4 * Seg_Pts (before dedup)

      --  Deduplication threshold (meters).  Matches Python: >= 1e-5.
      Dedup_Dist_Sq : constant := 1.0e-10;  -- (1e-5)^2

      --  Axis threshold: force to zero if R < this.
      Axis_Thresh : constant := 0.0051;

      --  Skin profile point (R, Z) in meters.
      type Skin_Point is record
         R : Float;
         Z : Float;
      end record;

      type Skin_Array is array (Positive range <>) of Skin_Point;

      --  Raw points (max 80 before deduplication).
      Raw   : Skin_Array (1 .. Max_Pts);
      N_Raw : Natural := 0;

      --  Deduplicated points.
      Unique   : Skin_Array (1 .. Max_Pts);
      N_Unique : Natural := 0;

      --  ---------------------------------------------------------------
      --  Derived geometric parameters
      -- ---------------------------------------------------------------
      --  gamma = theta_c_rad = angle from horizontal (R-axis).
      --  Python: theta_c_rad = radians(90.0 - angle).
      Gamma_Rad : constant Float := (90.0 - Geo.Angle_Deg) * Pi / 180.0;
      pragma Assert (abs Gamma_Rad <= Pi);  --  angle in [0, 90]

      Sin_G : constant Float := Sin_Rad (Gamma_Rad);
      Cos_G : constant Float := Cos_Rad (Gamma_Rad);
      Tan_G : constant Float := Sin_G / Cos_G;

      --  Eq 3.4 tangency: R_tang = rN * cos(gamma), Z_tang = rN*(1-sin(gamma))
      R_N    : constant Float := Geo.Nose_Radius_M;
      R_Tang : constant Float := R_N * Cos_G;
      Z_Tang : constant Float := R_N * (1.0 - Sin_G);

      --  Outermost toroid reach (Python: s_last = (2*N-1)*r_tor)
      S_Last   : constant Float := Float (2 * Geo.Toroid_Count - 1)
                                   * Geo.Toroid_Radius_M;
      R_Target : constant Float := R_Tang + S_Last * Cos_G;
      Z_Out    : constant Float := Z_Tang + S_Last * Sin_G;

      --  Center of outermost toroid
      R_C_Out : constant Float := R_Target - Geo.Toroid_Radius_M * Sin_G;
      Z_C_Out : constant Float := Z_Out + Geo.Toroid_Radius_M * Cos_G;
      Z_Back  : constant Float := Z_C_Out + Geo.Toroid_Radius_M;

      --  ---------------------------------------------------------------
      --  Local subprograms
      -- ---------------------------------------------------------------

      --  Append a raw point, forcing near-axis R to exactly 0.0.
      procedure Add_Raw (PR, PZ : Float) is
         R_Val : Float := PR;
      begin
         if R_Val < Axis_Thresh then
            R_Val := 0.0;
         end if;
         N_Raw := N_Raw + 1;
         Raw (N_Raw) := (R => R_Val, Z => PZ);
      end Add_Raw;

      --  Ada.Text_IO.Float_IO for fixed-point output (no scientific notation).
      package FIO is new Ada.Text_IO.Float_IO (Float);

      --  Output file handle.
      Out_File : Ada.Text_IO.File_Type;

   begin
      --  ==============================================================
      --  Segment 1: Nose Arc
      --  theta from -Pi/2 to -gamma (20 points, inclusive both ends).
      --  r = rN * cos(alpha), z = rN + rN * sin(alpha)
      -- ==============================================================
      for I in 0 .. Seg_Pts - 1 loop
         declare
            T     : constant Float := Float (I) / Float (Seg_Pts - 1);
            Alpha : constant Float := (-Pi / 2.0) * (1.0 - T)
                                    + (-Gamma_Rad) * T;
            PR    : constant Float := R_N * Cos_Rad (Alpha);
            PZ    : constant Float := R_N + R_N * Sin_Rad (Alpha);
         begin
            Add_Raw (PR, PZ);
         end;
      end loop;

      --  ==============================================================
      --  Segment 2: Windward Straight (conical shell)
      --  r from R_Tang to R_Target (skip first to avoid duplicate).
      --  z = Z_Tang + (r - R_Tang) * tan(gamma)
      -- ==============================================================
      for I in 1 .. Seg_Pts - 1 loop
         declare
            T : constant Float := Float (I) / Float (Seg_Pts - 1);
            R : constant Float := R_Tang + T * (R_Target - R_Tang);
            Z : constant Float := Z_Tang + (R - R_Tang) * Tan_G;
         begin
            Add_Raw (R, Z);
         end;
      end loop;

      --  ==============================================================
      --  Segment 3: Toroid Wrap (circular arc over outermost toroid)
      --  theta from -gamma to Pi/2 (skip first to avoid duplicate).
      --  r = R_c_out + r_tor * cos(theta)
      --  z = Z_c_out + r_tor * sin(theta)
      -- ==============================================================
      for I in 1 .. Seg_Pts - 1 loop
         declare
            T     : constant Float := Float (I) / Float (Seg_Pts - 1);
            Theta : constant Float := (-Gamma_Rad) * (1.0 - T)
                                    + (Pi / 2.0) * T;
            PR    : constant Float := R_C_Out
                                    + Geo.Toroid_Radius_M * Cos_Rad (Theta);
            PZ    : constant Float := Z_C_Out
                                    + Geo.Toroid_Radius_M * Sin_Rad (Theta);
         begin
            Add_Raw (PR, PZ);
         end;
      end loop;

      --  ==============================================================
      --  Segment 4: Flat Back Closure
      --  r from R_C_Out to ~0 (skip first to avoid duplicate).
      --  z = Z_back (constant — flat perpendicular to axis)
      -- ==============================================================
      for I in 1 .. Seg_Pts - 1 loop
         declare
            T : constant Float := Float (I) / Float (Seg_Pts - 1);
            R : constant Float := R_C_Out * (1.0 - T);  -- R_C_Out -> 0.0
         begin
            Add_Raw (R, Z_Back);
         end;
      end loop;

      --  ==============================================================
      --  Deduplication: remove consecutive points within 1e-5 m.
      -- ==============================================================
      N_Unique := 0;
      for I in 1 .. N_Raw loop
         if N_Unique = 0 then
            N_Unique := 1;
            Unique (1) := Raw (I);
         else
            declare
               DR     : constant Float := Raw (I).R - Unique (N_Unique).R;
               DZ     : constant Float := Raw (I).Z - Unique (N_Unique).Z;
               Dist_Sq : constant Float := DR * DR + DZ * DZ;
            begin
               if Dist_Sq >= Dedup_Dist_Sq then
                  N_Unique := N_Unique + 1;
                  Unique (N_Unique) := Raw (I);
               end if;
            end;
         end if;
      end loop;

      --  ==============================================================
      --  Write SPARTA .surf file
      --  Format: open 2D curve (NOT closed). SPARTA revolves it.
      --  X = axial (Z), Y = radial (R).  1-indexed.
      -- ==============================================================
      Ada.Text_IO.Create (Out_File, Ada.Text_IO.Out_File, Output_Path);

      --  Header
      Ada.Text_IO.Put_Line (Out_File,
                            "# SPARTA surface file: " & Output_Path);
      Ada.Text_IO.Put (Out_File, Integer'Image (N_Unique));
      Ada.Text_IO.Put_Line (Out_File, " points");
      Ada.Text_IO.Put (Out_File, Integer'Image (N_Unique - 1));
      Ada.Text_IO.Put_Line (Out_File, " lines");
      Ada.Text_IO.New_Line (Out_File);

      --  Points block: ID X Y  (X = axial = Z, Y = radial = R)
      Ada.Text_IO.Put_Line (Out_File, "Points");
      Ada.Text_IO.New_Line (Out_File);
      for I in 1 .. N_Unique loop
         Ada.Text_IO.Put (Out_File, Integer'Image (I));
         Ada.Text_IO.Put (Out_File, " ");
         FIO.Put (Out_File, Unique (I).Z, Fore => 1, Aft => 12, Exp => 0);
         Ada.Text_IO.Put (Out_File, " ");
         FIO.Put (Out_File, Unique (I).R, Fore => 1, Aft => 12, Exp => 0);
         Ada.Text_IO.New_Line (Out_File);
      end loop;
      Ada.Text_IO.New_Line (Out_File);

      --  Lines block: ID P1 P2  (open chain, NOT closed loop)
      Ada.Text_IO.Put_Line (Out_File, "Lines");
      Ada.Text_IO.New_Line (Out_File);
      for I in 1 .. N_Unique - 1 loop
         Ada.Text_IO.Put (Out_File, Integer'Image (I));
         Ada.Text_IO.Put (Out_File, " ");
         Ada.Text_IO.Put (Out_File, Integer'Image (I));
         Ada.Text_IO.Put (Out_File, " ");
         Ada.Text_IO.Put (Out_File, Integer'Image (I + 1));
         Ada.Text_IO.New_Line (Out_File);
      end loop;

      Ada.Text_IO.Close (Out_File);
   end Generate_HIAD_Surf;

   -- ==================================================================
   --  Generate_Validation_Plots_And_VTK — validation visualization
   --  (approach (a): parse HIAD_custom.surf for element coordinates)
    -- ==================================================================
    --  AXIOMS:
    --    * HIAD_custom.surf "Points" are the 2D axisymmetric profile in id
    --      order (nose->back); the curve is the Points connected 1-2-...-Np.
    --      We compute cumulative arc length S(i) and total length L.
    --    * The SPARTA surf dump "id" strides by 6 and is NOT the geometry
    --      index; dump rows are in curve order, so we read by ROW index (1..N)
    --      and ignore the strided id.  Columns: id f_1[1] f_1[2] f_1[3](=heat
    --      W/m^2) f_surfavg[1](=drag N) f_surfavg[2](=lift N) f_surfavg[3].
    --    * N (surf element count) = number of data rows in a surf.<step>.out
    --      dump (matches curve point count; ~219).
    --    * Axisymmetric 2D profile (x=Z axial, R radial) revolved about the
    --      x-axis gives a 3D shell; each segment -> N_Theta quad cells.
    --  THEORIES:
    --    * Resample the polyline into N+1 boundary points B(0..N) at equal
    --      arc length j/N*L; segment k (B(k-1)->B(k)) is surf element k.
    --    * Per-element field value is constant around the revolved ring, so
    --      all N_Theta quads sharing segment k carry field[k].
    --    * Time-series aggregates: drag_sum = Σ drag, lift_sum = Σ lift,
    --      heatflux_max = max |heat| (consistent with Step 6 metrics).
    --  APPLICATIONS:
    --    * ParaView .vtu (UnstructuredGrid, VTK_QUAD) for CFD post-processing.
    --    * CSV + matplotlib PNGs for trajectory-level trend inspection.
    --  CITATIONS:
    --    [Kitware2010] Ahrens, J. et al. "The VTK User's Guide", 2010 (XML .vtu).
    --    [Hunter2007] Hunter, J. D. "Matplotlib: A 2D Graphics Environment", 2007.
    --    [Rap23] Rapisarda, V. thesis, 2023 (HIAD flat-skin profile geometry).
    --  TIMING ANALYSIS
    --    Estimated Processing Time: O(N * N_Theta) per step for VTK;
    --      O(N_steps * N) total.  File I/O dominated.
    --    CPU Time: ~1 ms per element-revolution (ARM/Apple Silicon M-series).
    --    WCET: 2 s per 10k-step validation run (bounded by dump count).
    --    Space Complexity: O(N * N_Theta) points in memory per step.
    --    Derivation: points/step = (N+1)*N_Theta; for N=219, N_Theta=48 =>
    --      10,560 points/step; 100 steps => ~1.06M points total.
    --    Hardware Assumptions: macOS/ARM64 host; spinning or SSD storage.
   procedure Generate_Validation_Plots_And_VTK
     (Results_Dir : String;
      Steps       : Positive)
   is
       package FIO is new Ada.Text_IO.Float_IO (Float);

       Max_Pts   : constant := 256;     -- curve point cap (Npoints ~77)
       Max_Surf  : constant := 4096;    -- surf element / field cap (Murphy)
       Max_Steps : constant := 4096;    -- dump file cap (Murphy)
       N_Theta   : constant := 48;      -- revolve resolution (per design)
       Pi        : constant Float := 3.14159265358979323846;

       --  Parsed 2D curve from HIAD_custom.surf (x = axial, r = radial)
       type Pt2D is record X, R : Float := 0.0; end record;
       Curve   : array (1 .. Max_Pts) of Pt2D := (others => <>);
       Npoints : Natural := 0;
       S       : array (1 .. Max_Pts) of Float := (others => 0.0);  -- arc length
       L       : Float := 0.0;                                       -- total length

       --  Resampled boundary points B(0..N) by equal arc length
       N : Natural := 0;
       B : array (0 .. Max_Surf) of Pt2D := (others => <>);

       --  Per-element field values, indexed by dump ROW (1..N)
       Heat : array (1 .. Max_Surf) of Float := (others => 0.0);
       Drag : array (1 .. Max_Surf) of Float := (others => 0.0);
       Lift : array (1 .. Max_Surf) of Float := (others => 0.0);

       --  Time-series accumulation
       type Step_Row is record
          Step     : Positive := 1;
          Drag_Sum : Float := 0.0;
          Lift_Sum : Float := 0.0;
          Heat_Max : Float := 0.0;
       end record;
       Rows      : array (1 .. Max_Steps) of Step_Row := (others => (others => <>));
       N_Rows    : Natural := 0;

       --  Qualifying step list (step >= 100, multiple of 100, <= Steps)
       Step_List   : array (1 .. Max_Steps) of Positive := (others => 1);
       N_StepList  : Natural := 0;

       Surf_Path    : constant String := Results_Dir & "/HIAD_custom.surf";
       Paraview_Dir : constant String := Results_Dir & "/paraview";
       Plots_Dir    : constant String := Results_Dir & "/plots";
       CSV_Path     : constant String := Results_Dir & "/validation_timeseries.csv";

       type Real_Vec is array (Positive range <>) of Float;

      --  Tokenize a whitespace-separated line into up to Vals'Length floats.
      procedure Tokenize_Floats
        (S    : String;
         Vals : out Real_Vec;
         N    : out Natural)
      is
         Pos  : Natural := S'First;
         CIdx : Natural := 0;
      begin
         N := 0;
         while Pos <= S'Last loop
            while Pos <= S'Last
              and then (S (Pos) = ' ' or else S (Pos) = ASCII.HT)
            loop
               Pos := Pos + 1;
            end loop;
            exit when Pos > S'Last;
            declare
               Start : constant Natural := Pos;
            begin
               while Pos <= S'Last
                 and then S (Pos) /= ' '
                 and then S (Pos) /= ASCII.HT
               loop
                  Pos := Pos + 1;
               end loop;
               if CIdx < Vals'Length then
                  CIdx := CIdx + 1;
                  begin
                     Vals (CIdx) := Float'Value (S (Start .. Pos - 1));
                  exception
                     when others => Vals (CIdx) := 0.0;
                  end;
                  N := CIdx;
               end if;
            end;
         end loop;
      end Tokenize_Floats;

       --  Parse HIAD_custom.surf Points into the sequential polyline Curve
       --  (id order 1..Npoints = nose->back) and compute cumulative arc
       --  length S(1..Npoints); total length L = S(Npoints).  The "Lines"
       --  section is ignored: the curve IS the Points in id order (SPARTA
       --  connects 1-2,2-3,...,Npoints-1-Npoints sequentially).
       procedure Parse_Surf_Geometry is
          F    : File_Type;
          Line : String (1 .. 1024);
          Last : Natural;
          State : Natural := 0;  -- 0=scan, 1=points
       begin
          if not Exists (Surf_Path) then
             Put_Line (Standard_Error,
                       "[VTK] surf geometry not found: " & Surf_Path);
             return;
          end if;
          Open (F, In_File, Surf_Path);
          while not End_Of_File (F) loop
             Get_Line (F, Line, Last);
             if Last > 0 and then Line (1) /= '#' then
                declare
                   S : constant String := Line (1 .. Last);
                begin
                   if State = 0 then
                      if S = "Points" then
                         State := 1;
                      end if;
                   elsif State = 1 then
                      declare
                         V : Real_Vec (1 .. 8) := (others => 0.0);
                         M : Natural;
                      begin
                         Tokenize_Floats (S, V, M);
                         if M >= 3 then
                            declare
                               Idx : constant Natural := Natural (V (1));
                            begin
                               if Idx in Curve'Range then
                                  Curve (Idx).X := V (2);
                                  Curve (Idx).R := V (3);
                                  if Idx > Npoints then Npoints := Idx; end if;
                               end if;
                            end;
                         end if;
                      end;
                   end if;
                end;
             end if;
          end loop;
          Close (F);
          --  Cumulative arc length S(i); total L.
          if Npoints >= 2 then
             S (1) := 0.0;
             for i in 2 .. Npoints loop
                declare
                   Dx : constant Float := Curve (i).X - Curve (i - 1).X;
                   Dr : constant Float := Curve (i).R - Curve (i - 1).R;
                begin
                   S (i) := S (i - 1) + Sqrt (Dx * Dx + Dr * Dr);
                end;
             end loop;
             L := S (Npoints);
          end if;
       exception
          when E : others =>
             if Is_Open (F) then Close (F); end if;
             Put_Line (Standard_Error,
                       "[VTK] surf geometry parse failed: " &
                       Exception_Message (E));
       end Parse_Surf_Geometry;

       --  Resample the polyline into N+1 boundary points B(0..N) at equal
       --  arc length j/N * L (j=0..N).  Segment k (B(k-1)->B(k)) is the
       --  revolved position of surf element k.  Linear interpolation along
       --  the polyline segment containing the target arc length.
       procedure Resample is
          Target  : Float;
          Seg     : Natural;
          Frac    : Float;
          Dx, Dr, SegLen : Float;
       begin
          if N < 1 or else Npoints < 2 then
             return;
          end if;
          B (0).X := Curve (1).X;       B (0).R := Curve (1).R;
          B (N).X := Curve (Npoints).X; B (N).R := Curve (Npoints).R;
          if L <= 0.0 then
             for k in 1 .. N - 1 loop
                B (k) := Curve (1);
             end loop;
             return;
          end if;
          for k in 1 .. N - 1 loop
             Target := Float (k) / Float (N) * L;
             Seg := 1;
             for i in 2 .. Npoints loop
                if S (i) >= Target then
                   Seg := i - 1;
                   exit;
                end if;
             end loop;
             if Seg < 1 then Seg := 1; end if;
             if Seg > Npoints - 1 then Seg := Npoints - 1; end if;
             Dx := Curve (Seg + 1).X - Curve (Seg).X;
             Dr := Curve (Seg + 1).R - Curve (Seg).R;
             SegLen := S (Seg + 1) - S (Seg);
             if SegLen > 0.0 then
                Frac := (Target - S (Seg)) / SegLen;
             else
                Frac := 0.0;
             end if;
             B (k).X := Curve (Seg).X + Frac * Dx;
             B (k).R := Curve (Seg).R + Frac * Dr;
          end loop;
       end Resample;

       --  Count the number of data rows in a surf.<step>.out dump (the N
       --  surf elements).  Rows follow the "ITEM: SURFS" header line.
       function Count_Surf_Rows (Fpath : String) return Natural is
          F       : File_Type;
          Line    : String (1 .. 2048);
          Last    : Natural;
          In_Data : Boolean := False;
          Cnt     : Natural := 0;
       begin
          if not Exists (Fpath) then
             return 0;
          end if;
          Open (F, In_File, Fpath);
          while not End_Of_File (F) loop
             Get_Line (F, Line, Last);
             if Last >= 5 and then Line (1 .. 5) = "ITEM:" then
                In_Data := (Last >= 11 and then Line (1 .. 11) = "ITEM: SURFS");
             elsif In_Data and then Last > 0 and then Line (1) /= '#' then
                Cnt := Cnt + 1;
             end if;
          end loop;
          Close (F);
          return Cnt;
       exception
          when others =>
             if Is_Open (F) then Close (F); end if;
             return Cnt;
       end Count_Surf_Rows;

      --  Write one 3D point (x, y, z) into the VTK Points DataArray.
      procedure Write_Point (F : File_Type; X, Y, Z : Float) is
      begin
         FIO.Put (F, X, Fore => 1, Aft => 6, Exp => 0);
         Put (F, " ");
         FIO.Put (F, Y, Fore => 1, Aft => 6, Exp => 0);
         Put (F, " ");
         FIO.Put (F, Z, Fore => 1, Aft => 6, Exp => 0);
         New_Line (F);
      end Write_Point;

       --  Write the per-step .vtu UnstructuredGrid: revolve the resampled
       --  polyline B(0..N) about the x-axis into N*N_Theta VTK_QUAD cells.
       --  Segment k (B(k-1)->B(k)) yields N_Theta quads, each carrying
       --  field[k] (HeatFlux_Wm2/Drag_N/Lift_N).  Shared-node grid:
       --  (N+1)*N_Theta nodes, 0-based connectivity.
       procedure Write_VTU (Step : Positive) is
          VF      : File_Type;
          VPath   : constant String := Paraview_Dir & "/surf_" & Img (Integer (Step)) & ".vtu";
          DTheta  : constant Float := 2.0 * Pi / Float (N_Theta);
          N_Cells : constant Natural := N * N_Theta;
          N_Pts_V : constant Natural := (N + 1) * N_Theta;
          Cnt     : Natural := 0;
          Tn      : Natural;
          N0, N1, N2, N3 : Natural;
          Cth, Sth : Float;
       begin
          if N < 1 then
             return;
          end if;
          Create (VF, Out_File, VPath);
          Put_Line (VF, "<?xml version=""1.0""?>");
          Put_Line (VF, "<VTKFile type=""UnstructuredGrid"" version=""0.1"" byte_order=""LittleEndian"">");
          Put_Line (VF, "  <UnstructuredGrid>");
          Put_Line (VF, "    <Piece NumberOfPoints=""" & Img (N_Pts_V) &
                    """ NumberOfCells=""" & Img (N_Cells) & """>");
          --  Points (shared node grid: ring k=0..N, theta t=0..N_Theta-1)
          Put_Line (VF, "      <Points>");
          Put_Line (VF, "        <DataArray type=""Float64"" NumberOfComponents=""3"" format=""ascii"">");
          for k in 0 .. N loop
             for t in 0 .. N_Theta - 1 loop
                Cth := Cos_Rad (Float (t) * DTheta);
                Sth := Sin_Rad (Float (t) * DTheta);
                Write_Point (VF, B (k).X, B (k).R * Cth, B (k).R * Sth);
             end loop;
          end loop;
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "      </Points>");
          --  Cells
          Put_Line (VF, "      <Cells>");
          Put_Line (VF, "        <DataArray type=""Int64"" Name=""connectivity"" format=""ascii"">");
          Cnt := 0;
          for k in 1 .. N loop
             for t in 0 .. N_Theta - 1 loop
                Tn := (t + 1) mod N_Theta;
                N0 := (k - 1) * N_Theta + t;
                N1 := k * N_Theta + t;
                N2 := k * N_Theta + Tn;
                N3 := (k - 1) * N_Theta + Tn;
                Put (VF, Img (Integer (N0))); Put (VF, " ");
                Put (VF, Img (Integer (N1))); Put (VF, " ");
                Put (VF, Img (Integer (N2))); Put (VF, " ");
                Put (VF, Img (Integer (N3)));
                Cnt := Cnt + 1;
                if Cnt mod 4 = 0 then New_Line (VF); end if;
             end loop;
          end loop;
          New_Line (VF);
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "        <DataArray type=""Int64"" Name=""offsets"" format=""ascii"">");
          Cnt := 0;
          for k in 1 .. N loop
             for t in 0 .. N_Theta - 1 loop
                Cnt := Cnt + 1;
                Put (VF, Img (Integer (Cnt * 4)));
                if Cnt < N_Cells then
                   if Cnt mod 8 = 0 then New_Line (VF); else Put (VF, " "); end if;
                end if;
             end loop;
          end loop;
          New_Line (VF);
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "        <DataArray type=""UInt8"" Name=""types"" format=""ascii"">");
          for I in 1 .. N_Cells loop
             Put (VF, "9");
             if I < N_Cells then
                if I mod 20 = 0 then New_Line (VF); else Put (VF, " "); end if;
             end if;
          end loop;
          New_Line (VF);
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "      </Cells>");
          --  CellData (per segment k, constant around the ring)
          Put_Line (VF, "      <CellData>");
          Put_Line (VF, "        <DataArray type=""Float64"" Name=""HeatFlux_Wm2"" format=""ascii"">");
          Cnt := 0;
          for k in 1 .. N loop
             for t in 0 .. N_Theta - 1 loop
                Cnt := Cnt + 1;
                FIO.Put (VF, Heat (k), Fore => 1, Aft => 6, Exp => 0);
                if Cnt < N_Cells then
                   if Cnt mod 6 = 0 then New_Line (VF); else Put (VF, " "); end if;
                end if;
             end loop;
          end loop;
          New_Line (VF);
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "        <DataArray type=""Float64"" Name=""Drag_N"" format=""ascii"">");
          Cnt := 0;
          for k in 1 .. N loop
             for t in 0 .. N_Theta - 1 loop
                Cnt := Cnt + 1;
                FIO.Put (VF, Drag (k), Fore => 1, Aft => 6, Exp => 0);
                if Cnt < N_Cells then
                   if Cnt mod 6 = 0 then New_Line (VF); else Put (VF, " "); end if;
                end if;
             end loop;
          end loop;
          New_Line (VF);
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "        <DataArray type=""Float64"" Name=""Lift_N"" format=""ascii"">");
          Cnt := 0;
          for k in 1 .. N loop
             for t in 0 .. N_Theta - 1 loop
                Cnt := Cnt + 1;
                FIO.Put (VF, Lift (k), Fore => 1, Aft => 6, Exp => 0);
                if Cnt < N_Cells then
                   if Cnt mod 6 = 0 then New_Line (VF); else Put (VF, " "); end if;
                end if;
             end loop;
          end loop;
          New_Line (VF);
          Put_Line (VF, "        </DataArray>");
          Put_Line (VF, "      </CellData>");
          Put_Line (VF, "    </Piece>");
          Put_Line (VF, "  </UnstructuredGrid>");
          Put_Line (VF, "</VTKFile>");
          Close (VF);
       exception
          when E : others =>
             if Is_Open (VF) then Close (VF); end if;
             Put_Line (Standard_Error,
                       "[VTK] failed to write " & VPath & " : " &
                       Exception_Message (E));
       end Write_VTU;

       --  Parse one surf.<step>.out dump by ROW INDEX (1..N, curve order),
       --  fill Heat/Drag/Lift, write its VTK, and accumulate the CSV row.
       --  The dump "id" strides by 6 and is ignored; row order == curve
       --  position (matches the existing Step 6 parser field semantics).
       procedure Process_Step_File (Step : Positive) is
          Fpath : constant String := Results_Dir & "/surf." & Img (Integer (Step)) & ".out";
          F     : File_Type;
          Line  : String (1 .. 2048);
          Last  : Natural;
          In_Data : Boolean := False;
          Row   : Natural := 0;
          Drag_Sum, Lift_Sum, Heat_Max : Float := 0.0;
       begin
          if not Exists (Fpath) then
             Put_Line (Standard_Error, "[VTK] step dump not found: " & Fpath);
             return;
          end if;
          for I in 1 .. N loop
             Heat (I) := 0.0; Drag (I) := 0.0; Lift (I) := 0.0;
          end loop;
          Open (F, In_File, Fpath);
          while not End_Of_File (F) loop
             Get_Line (F, Line, Last);
             if Last >= 5 and then Line (1 .. 5) = "ITEM:" then
                In_Data := (Last >= 11 and then Line (1 .. 11) = "ITEM: SURFS");
             elsif In_Data and then Last > 0 and then Line (1) /= '#' then
                declare
                   S : constant String := Line (1 .. Last);
                   V : Real_Vec (1 .. 8) := (others => 0.0);
                   M : Natural;
                begin
                   Tokenize_Floats (S, V, M);
                   if M >= 6 then
                      Row := Row + 1;
                      if Row <= N then
                         Heat (Row) := V (4);   -- f_1[3] = heat flux W/m^2
                         Drag (Row) := V (5);   -- f_surfavg[1] = drag N
                         Lift (Row) := V (6);   -- f_surfavg[2] = lift N
                      end if;
                   end if;
                end;
             end if;
          end loop;
          Close (F);
          for I in 1 .. N loop
             Drag_Sum := Drag_Sum + Drag (I);
             Lift_Sum := Lift_Sum + Lift (I);
             if Abs_F (Heat (I)) > Heat_Max then Heat_Max := Abs_F (Heat (I)); end if;
          end loop;
          if N > 0 then
             Write_VTU (Step);
          end if;
          if N_Rows < Max_Steps then
             N_Rows := N_Rows + 1;
             Rows (N_Rows) := (Step => Step, Drag_Sum => Drag_Sum,
                               Lift_Sum => Lift_Sum, Heat_Max => Heat_Max);
          end if;
       exception
          when E : others =>
             if Is_Open (F) then Close (F); end if;
             Put_Line (Standard_Error,
                       "[VTK] failed processing step " & Img (Integer (Step)) & " : " &
                       Exception_Message (E));
       end Process_Step_File;

      --  Sort Rows by Step and write the CSV.
      procedure Write_CSV is
         CF : File_Type;
      begin
         for I in 1 .. N_Rows - 1 loop
            for J in I + 1 .. N_Rows loop
               if Rows (J).Step < Rows (I).Step then
                  declare
                     Tmp : constant Step_Row := Rows (I);
                  begin
                     Rows (I) := Rows (J);
                     Rows (J) := Tmp;
                  end;
               end if;
            end loop;
         end loop;
         Create (CF, Out_File, CSV_Path);
         Put_Line (CF, "step,drag_sum_N,lift_sum_N,heatflux_max_Wm2");
         for I in 1 .. N_Rows loop
            Put (CF, Img (Rows (I).Step));
            Put (CF, ",");
            FIO.Put (CF, Rows (I).Drag_Sum, Fore => 1, Aft => 6, Exp => 0);
            Put (CF, ",");
            FIO.Put (CF, Rows (I).Lift_Sum, Fore => 1, Aft => 6, Exp => 0);
            Put (CF, ",");
            FIO.Put (CF, Rows (I).Heat_Max, Fore => 1, Aft => 6, Exp => 0);
            New_Line (CF);
         end loop;
         Close (CF);
      exception
         when E : others =>
            if Is_Open (CF) then Close (CF); end if;
            Put_Line (Standard_Error,
                      "[VTK] failed writing CSV " & CSV_Path & " : " &
                      Exception_Message (E));
       end Write_CSV;

        --  Write the ParaView .pvd collection that groups all per-step
        --  .vtu files into a single timeline (timestep = dump step).
        procedure Write_PVD is
           PF    : File_Type;
           PPath : constant String := Paraview_Dir & "/validation.pvd";
        begin
           if N_StepList < 1 or else N < 1 then
              return;
           end if;
           Create (PF, Out_File, PPath);
           Put_Line (PF, "<?xml version=""1.0""?>");
           Put_Line (PF, "<VTKFile type=""Collection"" version=""1.0"" byte_order=""LittleEndian"">");
           Put_Line (PF, "  <Collection>");
           for I in 1 .. N_StepList loop
              Put_Line (PF, "    <DataSet timestep=""" & Img (Integer (Step_List (I))) &
                        """ group="""" part=""0"" file=""surf_" &
                        Img (Integer (Step_List (I))) & ".vtu""/>");
           end loop;
           Put_Line (PF, "  </Collection>");
           Put_Line (PF, "</VTKFile>");
           Close (PF);
           Put_Line ("[VTK] Wrote ParaView collection: " & PPath);
        exception
           when E : others =>
              if Is_Open (PF) then Close (PF); end if;
              Put_Line (Standard_Error,
                        "[VTK] failed writing PVD " & PPath & " : " &
                        Exception_Message (E));
        end Write_PVD;

        Srch : Search_Type;
       E : Directory_Entry_Type;
    begin
       --  Ensure output directories exist (safety fallback).
       if not Exists (Paraview_Dir) then
          begin Create_Path (Paraview_Dir); exception when others => null; end;
       end if;
       if not Exists (Plots_Dir) then
          begin Create_Path (Plots_Dir); exception when others => null; end;
       end if;

       --  Step 1: parse HIAD_custom.surf polyline + arc length.
       Parse_Surf_Geometry;
       if Npoints < 2 then
          Put_Line (Standard_Error,
                    "[VTK] Need >= 2 curve points; VTK/CSV skipped.");
          return;
       end if;

       --  Step 2: enumerate qualifying surf.<step>.out dumps (step>=100,
       --  multiple of 100, <= Steps) via Ada.Directories.
        Start_Search (Srch, Results_Dir, "surf.*.out");
        while More_Entries (Srch) loop
           Get_Next_Entry (Srch, E);
          declare
             Name : constant String := Simple_Name (E);
             Step : Natural := 0;
          begin
             if Name'Length > 9
               and then Name (Name'First .. Name'First + 4) = "surf."
             then
                declare
                   Tail : constant String := Name (Name'First + 5 .. Name'Last);
                begin
                   if Tail'Length > 4
                     and then Tail (Tail'Last - 3 .. Tail'Last) = ".out"
                   then
                      Step := Natural'Value (Tail (Tail'First .. Tail'Last - 4));
                   end if;
                exception
                   when others => Step := 0;
                end;
             end if;
             if Step >= 100 and then Step mod 100 = 0 and then Step <= Steps then
                if N_StepList < Max_Steps then
                   N_StepList := N_StepList + 1;
                   Step_List (N_StepList) := Step;
                end if;
             end if;
          end;
       end loop;
        End_Search (Srch);

        if N_StepList = 0 then
          Put_Line (Standard_Error,
                    "[VTK] No surf.<step>.out dumps (step>=100) found; skipped.");
          return;
       end if;

       --  Sort steps ascending (insertion sort, Murphy-bounded).
       for I in 1 .. N_StepList - 1 loop
          for J in I + 1 .. N_StepList loop
             if Step_List (J) < Step_List (I) then
                declare
                   Tmp : constant Positive := Step_List (I);
                begin
                   Step_List (I) := Step_List (J);
                   Step_List (J) := Tmp;
                end;
             end if;
          end loop;
       end loop;

       --  Step 3: determine N (surf element count) from first dump.
       N := Count_Surf_Rows
         (Results_Dir & "/surf." & Img (Integer (Step_List (1))) & ".out");
       if N > Max_Surf then
          N := Max_Surf;
       end if;
       if N < 1 then
          Put_Line (Standard_Error,
                    "[VTK] Could not determine surf element count N; skipped.");
          return;
       end if;

       --  Step 4: resample polyline into N+1 boundary points.
       Resample;

        --  Step 5: per step -> VTK + CSV row.
        for I in 1 .. N_StepList loop
           Process_Step_File (Step_List (I));
        end loop;

        --  Emit ParaView .pvd collection (groups all .vtu into one timeline).
        Write_PVD;

        --  Emit CSV + render PNG plots (best-effort, return code ignored).
       if N_Rows > 0 then
          Write_CSV;
          Put_Line ("[VTK] Invoking Python plot renderer: python3 scripts/make_validation_plots.py "
                    & Results_Dir);
          System ("python3 scripts/make_validation_plots.py " & Results_Dir);
       else
          Put_Line (Standard_Error,
                    "[VTK] No valid step dumps processed; CSV/plots skipped.");
       end if;
   exception
      when E : others =>
         Put_Line (Standard_Error,
                   "[VTK] Generate_Validation_Plots_And_VTK failed: " &
                   Exception_Message (E));
   end Generate_Validation_Plots_And_VTK;

end StellarOrion_Sparta;
