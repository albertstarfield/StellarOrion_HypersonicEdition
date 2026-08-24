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

package body StellarOrion_Sparta is
   pragma SPARK_Mode (Off);
   --  extern: writes SPARTA run scripts + Ada.Directories/Exceptions I/O (non-SPARK)

   -- ==================================================================
   --  Internal Helpers
   -- ==================================================================

   function Chem_To_String (C : Chemistry_Mode) return String is
   begin
      case C is
         when Five_Species   => return "5sp";
         when Eleven_Species => return "11sp";
         when Mars           => return "mars";
      end case;
   end Chem_To_String;

   function Nose_To_String (N : Nose_Type_Kind) return String is
   begin
      case N is
         when Smooth => return "smooth";
         when Pointy => return "pointy";
      end case;
   end Nose_To_String;

   function Img (V : Float) return String is
      S : constant String := Float'Image (V);
   begin
      if S'Length > 1 and then S (S'First) = ' ' then
         return S (S'First + 1 .. S'Last);
      end if;
      return S;
   end Img;

   function Img (V : Integer) return String is
      S : constant String := Integer'Image (V);
   begin
      if S'Length > 1 and then S (S'First) = ' ' then
         return S (S'First + 1 .. S'Last);
      end if;
      return S;
   end Img;

   function Sqrt (X : Float) return Float is
      Y, Y_New : Float;
   begin
      if X <= 0.0 then return 0.0; end if;
      Y := X / 2.0;
      for I in 1 .. 8 loop
         pragma Unreferenced (I);
         Y_New := (Y + X / Y) / 2.0;
         Y := Y_New;
      end loop;
      return Y;
   end Sqrt;

   function Abs_F (X : Float) return Float is
   begin
      if X < 0.0 then return -X; end if;
      return X;
   end Abs_F;

   procedure System (Cmd : String);
   pragma Import (C, System);

   -- ==================================================================
   --  Generate_Sparta_Script
   -- ==================================================================
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
         for I in reverse Restart_File'Range loop
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
            for I in Bname'Range loop
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
      Put_Line (File, "compute         temp_avg reduce ave " &
                "f_1[1] f_1[2] f_1[3]");
      Put_Line (File, "");

      -- Flow Field Data
      Put_Line (File, "compute         2 grid all " &
                To_String (Mixture_Name) & " n u v w");
      Put_Line (File, "fix             2 ave/grid all 1 1 1 c_2[*]");
      Put_Line (File, "");
      Put_Line (File, "compute         3 thermal/grid all " &
                To_String (Mixture_Name) & " temp");
      Put_Line (File, "fix             3 ave/grid all 1 1 1 c_3[*]");
      Put_Line (File, "");
      Put_Line (File, "compute         4 grid all " &
                To_String (Mixture_Name) & " nrho");
      Put_Line (File, "fix             4 ave/grid all 1 1 1 c_4[*]");
      Put_Line (File, "");
      Put_Line (File, "timestep        1e-6");
      Put_Line (File, "");
      Put_Line (File, "stats           " & Img (Stats_Interval));
      Put_Line (File, "stats_style     step cpu np c_drag c_lift " &
                "c_heat c_temp_avg[1] c_temp_avg[2] c_temp_avg[3]");
      Put_Line (File, "");
      Put_Line (File, "dump            1 surf all " &
                Img (Stats_Interval) & " " & Results_Dir &
                "/surf.*.out id f_1[*] f_surfavg[*]");
      Put_Line (File, "dump            2 grid all " &
                Img (Stats_Interval) & " " & Results_Dir &
                "/grid.*.out id xlo ylo xhi yhi f_2[*] f_3[*] f_4[*]");
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
   procedure Build_Sparta_Library is
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
   procedure Run_Sparta_Docker
     (Cwd       : String;
      Use_GPU   : Boolean;
      Num_Cores : Positive;
      Success   : out Boolean)
   is
      Graceful_Flag : constant String := Cwd & "/graceful_exit.flag";
      Exit_Flag     : constant String := Cwd & "/simulation_complete.flag";
      pragma Unreferenced (Exit_Flag);
   begin
      Success := False;
      Put_Line ("[SPARTA] Executing SPARTA via Docker...");
      System ("docker rm -f hiad-runner 2>/dev/null || true");

      if Exists (Graceful_Flag) then
         begin Delete_File (Graceful_Flag); exception when others => null; end;
      end if;

      --  Copy in.hiad from results_validation/ to project root for Docker mount
      begin
         if Exists (Cwd & "/results_validation/in.hiad") then
            Delete_File (Cwd & "/in.hiad");
            Copy_File (Cwd & "/results_validation/in.hiad", Cwd & "/in.hiad");
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
            Append (Cmd, "spa -in results_validation/in.hiad -pk kokkos newton on gpu 1 -sf kk");
         elsif Num_Cores > 1 then
            Append (Cmd, "mpirun --allow-run-as-root --oversubscribe -np " &
                    Img (Num_Cores) & " spa -in results_validation/in.hiad");
         else
            Append (Cmd, "spa -in results_validation/in.hiad");
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
             Start_Search (S, Cwd & "/results_validation", "surf.*.out");
            while More_Entries (S) loop
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
   function Compute_Surf_Y_Max (Output_Dir : String) return Float is
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

      while More_Entries (Search) loop
         Get_Next_Entry (Search, Dir_Ent);

         begin
            Open (File, In_File, Full_Name (Dir_Ent));
         exception
            when others =>
               goto Next_File;
         end;

         In_Data := False;
         while not End_Of_File (File) loop
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
               for I in 1 .. Last loop
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
   procedure Compute_Surf_Centroid
     (Output_Dir  : String;
      Centroid_X  : out Float;
      Centroid_Y  : out Float;
      Centroid_Z  : out Float)
   is
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

      while More_Entries (Search) loop
         Get_Next_Entry (Search, Dir_Ent);

         begin
            Open (File, In_File, Full_Name (Dir_Ent));
         exception
            when others =>
               goto Next_File_Centroid;
         end;

         while not End_Of_File (File) loop
            Get_Line (File, Line, Last);

            if Last > 1 and then (Line (1) = '#' or Line (1) = 'S') then
               null;
            elsif Last > 0 then
               --  Parse data line
               Col := 0;
               V_Len := 0;
               Col_Filled := (others => False);

               for I in 1 .. Last loop
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
   function Parse_Sparta_Results
     (Output_Dir : String;
      Flight     : Flight_Parameters;
      Geo        : Geometry_Parameters) return Simulation_Results
   is
      Max_Files : constant := 200;
      type Name_Arr is array (1 .. Max_Files) of Unbounded_String;
      Names     : Name_Arr;
      N_Files   : Natural := 0;
      Result    : Simulation_Results;
      All_Drag  : array (1 .. Max_Files) of Float := (others => 0.0);
       All_Heat  : array (1 .. Max_Files) of Float := (others => 0.0);
       pragma Unreferenced (All_Heat);
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
            while More_Entries (S) and N_Files < Max_Files loop
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

      -- Sort files by numeric index
      for I in 1 .. N_Files - 1 loop
         for J in I + 1 .. N_Files loop
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
         for Fidx in Start_I .. N_Files loop
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
                              while Pos <= L'Last and then L (Pos) = ' ' loop
                                 Pos := Pos + 1;
                              end loop;
                              exit when Pos > L'Last;
                              declare
                                 S : constant Natural := Pos;
                              begin
                                 while Pos <= L'Last and then L (Pos) /= ' ' loop
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
                               Drag_Sum := Drag_Sum + Abs_F (Cols (5));
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
            while More_Entries (G_S) loop
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
                                 while Pos <= GL'Last and then GL (Pos) = ' ' loop
                                    Pos := Pos + 1;
                                 end loop;
                                 exit when Pos > GL'Last;
                                 declare
                                    S : constant Natural := Pos;
                                 begin
                                    while Pos <= GL'Last and then
                                          GL (Pos) /= ' '
                                    loop
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

      -- Total heat load (integrated over 60s exposure)
      Result.Total_Heat_Load := Result.Heat_Flux_Wm2 * 60.0;

      Put_Line ("[SPARTA] Drag       = " & Img (Result.Drag_Force) &
                " N");
      Put_Line ("[SPARTA] Heat Flux  = " &
                Img (Result.Heat_Flux_Wm2) & " W/m^2");
      Put_Line ("[SPARTA] Total Load = " &
                Img (Result.Total_Heat_Load) & " J/m^2");

      return Result;
   end Parse_Sparta_Results;

end StellarOrion_Sparta;
