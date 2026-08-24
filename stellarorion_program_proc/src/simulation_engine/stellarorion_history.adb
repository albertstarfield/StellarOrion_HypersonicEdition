--  StellarOrion_HypersonicEdition — Run History / Database Bridge (Body)
--  Ada 2012 / SPARK 2014
--  SPARK_Mode => Off : file I/O, file locking, CSV parsing.
--
--  This implementation uses flat-file CSV storage as a portable
--  fallback when SQLite is unavailable.  The interface is designed
--  so that a future GNATColl or SQLite binding can replace the
--  internals without changing the spec.
--
--  File layout:
--    <db_dir>/runs.csv          — one row per simulation run
--    <db_dir>/samples.csv       — one row per DoE sample
--    <db_dir>/.lock             — lock file for concurrent access
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with Ada.Text_IO;              use Ada.Text_IO;
with Ada.Strings;              use Ada.Strings;
with Ada.Strings.Fixed;        use Ada.Strings.Fixed;
with Ada.Directories;          use Ada.Directories;
with Ada.Exceptions;           use Ada.Exceptions;
with Ada.Calendar;             use Ada.Calendar;
with Ada.Characters.Handling;  use Ada.Characters.Handling;

package body StellarOrion_History is
   pragma SPARK_Mode (Off);
   --  extern: Ada.Directories/Ada.Exceptions file persistence for run history (non-SPARK libs)

   --  Internal state
   DB_Directory   : Unbounded_String;
   DB_Initialised : Boolean := False;

   Runs_File    : constant String := "runs.csv";
   Samples_File : constant String := "samples.csv";
   Lock_File    : constant String := ".lock";

   --  Maximum seconds to wait for a stale lock before force-removing it.
   Lock_Timeout : constant Duration := 30.0;

   -- ==================================================================
   --  CSV Helpers
   -- ==================================================================

   Max_Fields : constant := 40;
   type Field_Array is array (1 .. Max_Fields) of Unbounded_String;

   --  Split a CSV line on commas.  Returns the number of fields found.
   --  Handles quoted fields containing commas.
   function Parse_CSV_Line (Line : String;
                            Fields : out Field_Array) return Natural
   is
      In_Quote : Boolean := False;
      Idx      : Positive := 1;
      Fld      : Natural := 0;
   begin
      if Line'Length = 0 then
         return 0;
      end if;

      for I in Line'Range loop
         if Line(I) = '"' then
            In_Quote := not In_Quote;
         elsif Line(I) = ',' and then not In_Quote then
            Fld := Fld + 1;
            if Fld <= Max_Fields then
               Fields(Fld) := To_Unbounded_String(Line(Idx .. I - 1));
            end if;
            Idx := I + 1;
         end if;
      end loop;

      --  Capture the last field (after the final comma or the only field)
      Fld := Fld + 1;
      if Fld <= Max_Fields then
         Fields(Fld) := To_Unbounded_String(Line(Idx .. Line'Last));
      end if;

      return Fld;
   end Parse_CSV_Line;

   --  Unescape a CSV field: strip surrounding double-quotes if present.
   function CSV_Unescape (S : String) return String is
   begin
      if S'Length >= 2 and then
         S(S'First) = '"' and then S(S'Last) = '"'
      then
         return S(S'First + 1 .. S'Last - 1);
      else
         return S;
      end if;
   end CSV_Unescape;

   --  Escape a CSV field: wrap in double-quotes if it contains a comma.
   function CSV_Escape (S : String) return String is
   begin
      for I in S'Range loop
         if S(I) = ',' then
            return """" & S & """";
         end if;
      end loop;
      return S;
   end CSV_Escape;

   --  String to Float (trims whitespace)
   function S2F (S : String) return Float is
   begin
      return Float'Value (Trim (CSV_Unescape (S), Both));
   exception
      when others => return 0.0;
   end S2F;

   --  String to Integer (trims whitespace)
   function S2I (S : String) return Integer is
   begin
      return Integer'Value (Trim (CSV_Unescape (S), Both));
   exception
      when others => return 0;
   end S2I;

   --  String to Boolean
   function S2B (S : String) return Boolean is
      LS : constant String := To_Lower (Trim (CSV_Unescape (S), Both));
   begin
      return LS = "true" or LS = "yes" or LS = "1";
   end S2B;

   --  Float to String (trimmed)
   function F2S (V : Float) return String is
   begin
      return Trim (Float'Image (V), Both);
   end F2S;

   --  Boolean to String
   function B2S (V : Boolean) return String is
   begin
      if V then return "true"; else return "false"; end if;
   end B2S;

   --  Solver_Kind <-> String conversions
   function Solver_To_Str (S : Solver_Kind) return String is
   begin
      case S is
         when SPARTA   => return "sparta";
         when OpenFOAM => return "openfoam";
         when PyFluent => return "pyfluent";
         when PyANSYS  => return "pyansys";
      end case;
   end Solver_To_Str;

   function Str_To_Solver (S : String) return Solver_Kind is
      LS : constant String := To_Lower (Trim (S, Both));
   begin
      if LS = "openfoam" then return OpenFOAM;
      elsif LS = "pyfluent" then return PyFluent;
      elsif LS = "pyansys" then return PyANSYS;
      else return SPARTA;
      end if;
   end Str_To_Solver;

   --  Chemistry_Mode <-> String conversions
   function Chem_To_Str (C : Chemistry_Mode) return String is
   begin
      case C is
         when Five_Species   => return "5sp";
         when Eleven_Species => return "11sp";
         when Mars           => return "mars";
      end case;
   end Chem_To_Str;

   function Str_To_Chem (S : String) return Chemistry_Mode is
      LS : constant String := To_Lower (Trim (S, Both));
   begin
      if LS = "11sp" then return Eleven_Species;
      elsif LS = "mars" then return Mars;
      else return Five_Species;
      end if;
   end Str_To_Chem;

   -- ==================================================================
   --  File Locking (timestamp-based)
   -- ==================================================================

   --  Acquire a lock on the database directory.
   --  If the lock file exists and is fresh (< Lock_Timeout), wait and retry.
   --  If the lock file is stale, remove it and proceed.
   procedure Acquire_Lock is
      Lock_Path : constant String :=
        Compose (To_String (DB_Directory), Lock_File);
      Attempts  : Natural := 0;
   begin
      loop
         if not Exists (Lock_Path) then
            --  Create lock file with timestamp
            declare
               F : File_Type;
            begin
               Create (F, Out_File, Lock_Path);
               Put_Line (F, "locked");
               Close (F);
            end;
            return;
         end if;

         --  Lock exists; check staleness via modification time
         declare
            Stamp : constant Time := Modification_Time (Lock_Path);
            Now   : constant Time := Clock;
            Age   : constant Duration := Now - Stamp;
         begin
            if Age > Lock_Timeout then
               --  Stale lock — force remove
               Delete_File (Lock_Path);
               Put_Line ("[HISTORY] Removed stale lock file.");
            else
               --  Wait briefly and retry
               delay 0.1;
               Attempts := Attempts + 1;
               if Attempts > 300 then  -- 30 seconds of retries
                  Put_Line ("[HISTORY WARNING] Lock timeout. Proceeding anyway.");
                  begin
                     Delete_File (Lock_Path);
                  exception
                     when others => null;
                  end;
                  return;
               end if;
            end if;
         end;
      end loop;
   exception
      when E : others =>
         Put_Line ("[HISTORY WARNING] Acquire_Lock: " &
                    Exception_Message (E));
   end Acquire_Lock;

   --  Release the lock file.
   procedure Release_Lock is
      Lock_Path : constant String :=
        Compose (To_String (DB_Directory), Lock_File);
   begin
      if Exists (Lock_Path) then
         Delete_File (Lock_Path);
      end if;
   exception
      when others => null;
   end Release_Lock;

   -- ==================================================================
   --  Init_DB
   -- ==================================================================
   procedure Init_DB (Database_Path : String) is
   begin
      DB_Directory := To_Unbounded_String (Database_Path);

      --  Create directory if it doesn't exist
      if not Exists (Database_Path) then
         Create_Directory (Database_Path);
      end if;

      --  Create header rows if files don't exist
      if not Exists (Compose (Database_Path, Runs_File)) then
         declare
            F : File_Type;
         begin
            Create (F, Out_File, Compose (Database_Path, Runs_File));
            Put_Line (F,
              "name,mach,alt_km,vel_ms,rho,density_temp_k," &
              "diameter,angle,nose_r,toroid_n,toroid_r," &
              "mass,drag_force,heat_flux,total_load," &
              "stag_pressure,shock_temp," &
              "ballistic_coeff,knudsen,stag_hf_wm2," &
              "stag_hf_wcm2,surf_temp,backface_temp," &
              "decel_g,g_load,survivable,solver,chemistry," &
              "status,progress");
            Close (F);
         end;
      end if;

      if not Exists (Compose (Database_Path, Samples_File)) then
         declare
            F : File_Type;
         begin
            Create (F, Out_File, Compose (Database_Path, Samples_File));
            Put_Line (F,
              "sample_idx,diameter,angle,nose_r,toroid_n," &
              "toroid_r,mass," &
              "drag_force,heat_flux,total_load," &
              "ballistic_coeff,decel_g,survivable");
            Close (F);
         end;
      end if;

      DB_Initialised := True;
      Put_Line ("[HISTORY] Database initialised at: " & Database_Path);
   exception
      when E : others =>
         Put_Line ("[HISTORY ERROR] Init_DB: " &
                    Exception_Message (E));
   end Init_DB;

   -- ==================================================================
   --  Populate a Run_Record from parsed CSV fields.
   --  Fields array is 1-indexed.  Field 1 = name, fields 2..30 = data.
   --  Missing fields (index > Field_Count) are filled with defaults.
   -- ==================================================================
   procedure Populate_Run_Record (Fields      : Field_Array;
                                  Field_Count : Natural;
                                  Rec         : out Run_Record)
   is
      function F (Idx : Positive) return Float is
      begin
         if Idx <= Field_Count then
            return S2F (To_String (Fields (Idx)));
         else
            return 0.0;
         end if;
      end F;

      function I (Idx : Positive) return Integer is
      begin
         if Idx <= Field_Count then
            return S2I (To_String (Fields (Idx)));
         else
            return 0;
         end if;
      end I;

      function B (Idx : Positive) return Boolean is
      begin
         if Idx <= Field_Count then
            return S2B (To_String (Fields (Idx)));
         else
            return False;
         end if;
      end B;

      function S (Idx : Positive) return String is
      begin
         if Idx <= Field_Count then
            return CSV_Unescape (To_String (Fields (Idx)));
         else
            return "";
         end if;
      end S;

   begin
      --  Field  1: name
      if Field_Count >= 1 then
         Rec.Name := Fields (1);
      end if;

      --  Fields  2-6: Flight_Parameters
      --  Constrained components are clamped into their envelope subtypes
      --  (Murphy's Law: a corrupt/hostile CSV row must not crash the
      --  history load with Constraint_Error at the range check; values
      --  are sanitized to the nearest legal bound instead).
      Rec.Flight.Mach          := F (2);
      Rec.Flight.Altitude_Km   := F (3);
      Rec.Flight.Velocity_Ms   :=
        Float'Min (Float'Max (F (4), Velocity_Range'First),
                   Velocity_Range'Last);
      Rec.Flight.Density_Kgm3  :=
        Float'Min (Float'Max (F (5), Density_Range'First),
                   Density_Range'Last);
      Rec.Flight.Temperature_K := F (6);

      --  Fields  7-12: Geometry_Parameters
      Rec.Geo.Diameter_M      :=
        Float'Min (Float'Max (F (7), Diameter_Range'First),
                   Diameter_Range'Last);
      Rec.Geo.Angle_Deg       := F (8);
      Rec.Geo.Nose_Radius_M   :=
        Float'Min (Float'Max (F (9), Nose_Radius_Range'First),
                   Nose_Radius_Range'Last);
      Rec.Geo.Toroid_Count    := Integer'Max (1, I (10));
      Rec.Geo.Toroid_Radius_M := F (11);
      Rec.Geo.Mass_Kg         :=
        Float'Min (Float'Max (F (12), Mass_Kg_Range'First),
                   Mass_Kg_Range'Last);

      --  Fields 13-17: Simulation_Results
      Rec.Results.Drag_Force      := F (13);
      Rec.Results.Heat_Flux_Wm2   := F (14);
      Rec.Results.Total_Heat_Load := F (15);
      Rec.Results.Stag_Pressure_Pa := F (16);
      Rec.Results.Shock_Temp_K    := F (17);

      --  Fields 18-25: Flight_Metrics
      Rec.Metrics.Ballistic_Coeff     := F (18);
      Rec.Metrics.Knudsen_Number      := F (19);
      Rec.Metrics.Stag_Heat_Flux_Wm2  := F (20);
      Rec.Metrics.Stag_Heat_Flux_Wcm2 := F (21);
      Rec.Metrics.Surface_Temp_K      := F (22);
      Rec.Metrics.Backface_Temp_K     := F (23);
      Rec.Metrics.Decel_G             := F (24);
      Rec.Metrics.G_Load              := F (25);
      Rec.Metrics.Survivable          := B (26);

      --  Fields 27-28: Solver, Chemistry
      Rec.Solver    := Str_To_Solver (S (27));
      Rec.Chemistry := Str_To_Chem    (S (28));

      --  Fields 29-30: Status, Progress (optional, backward-compatible)
      if Field_Count >= 29 then
         Rec.Status := To_Unbounded_String (CSV_Unescape (To_String (Fields (29))));
      else
         Rec.Status := To_Unbounded_String ("completed");
      end if;

      if Field_Count >= 30 then
         Rec.Progress := F (30);
      else
         Rec.Progress := 1.0;
      end if;
   end Populate_Run_Record;

   -- ==================================================================
   --  Save_Run
   -- ==================================================================
   procedure Save_Run
     (Name      : String;
      Flight    : Flight_Parameters;
      Geo       : Geometry_Parameters;
      TPS       : TPS_Material;
      Results   : Simulation_Results;
      Metrics   : Flight_Metrics;
      Solver    : Solver_Kind;
      Chemistry : Chemistry_Mode)
   is
      F    : File_Type;
      Path : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      Line : Unbounded_String;
      pragma Unreferenced (TPS);
   begin
      if not DB_Initialised then
         Put_Line ("[HISTORY ERROR] Database not initialised.");
         return;
      end if;

      Acquire_Lock;
      begin
         --  Build CSV line
         Line := To_Unbounded_String (CSV_Escape (Name) & ",");
         Append (Line, F2S (Flight.Mach) & ",");
         Append (Line, F2S (Flight.Altitude_Km) & ",");
         Append (Line, F2S (Flight.Velocity_Ms) & ",");
         Append (Line, F2S (Flight.Density_Kgm3) & ",");
         Append (Line, F2S (Flight.Temperature_K) & ",");
         Append (Line, F2S (Geo.Diameter_M) & ",");
         Append (Line, F2S (Geo.Angle_Deg) & ",");
         Append (Line, F2S (Geo.Nose_Radius_M) & ",");
         Append (Line, Trim (Positive'Image (Geo.Toroid_Count), Both) & ",");
         Append (Line, F2S (Geo.Toroid_Radius_M) & ",");
         Append (Line, F2S (Geo.Mass_Kg) & ",");
         Append (Line, F2S (Results.Drag_Force) & ",");
         Append (Line, F2S (Results.Heat_Flux_Wm2) & ",");
         Append (Line, F2S (Results.Total_Heat_Load) & ",");
         Append (Line, F2S (Results.Stag_Pressure_Pa) & ",");
         Append (Line, F2S (Results.Shock_Temp_K) & ",");
         Append (Line, F2S (Metrics.Ballistic_Coeff) & ",");
         Append (Line, F2S (Metrics.Knudsen_Number) & ",");
         Append (Line, F2S (Metrics.Stag_Heat_Flux_Wm2) & ",");
         Append (Line, F2S (Metrics.Stag_Heat_Flux_Wcm2) & ",");
         Append (Line, F2S (Metrics.Surface_Temp_K) & ",");
         Append (Line, F2S (Metrics.Backface_Temp_K) & ",");
         Append (Line, F2S (Metrics.Decel_G) & ",");
         Append (Line, F2S (Metrics.G_Load) & ",");
         Append (Line, B2S (Metrics.Survivable) & ",");
         Append (Line, Solver_To_Str (Solver) & ",");
         Append (Line, Chem_To_Str (Chemistry) & ",");
         Append (Line, "completed,");
         Append (Line, "1.0");

         Open (F, Append_File, Path);
         Put_Line (F, To_String (Line));
         Close (F);

         Put_Line ("[HISTORY] Run saved: " & Name);
      exception
         when E : others =>
            Put_Line ("[HISTORY ERROR] Save_Run: " &
                       Exception_Message (E));
            if Is_Open (F) then
               Close (F);
            end if;
      end;
      Release_Lock;
   end Save_Run;

   -- ==================================================================
   --  Load_Run — Parse CSV line by line, populate out parameters.
   -- ==================================================================
   function Load_Run
     (Name      : String;
      Flight    : out Flight_Parameters;
      Geo       : out Geometry_Parameters;
      TPS       : out TPS_Material;
      Results   : out Simulation_Results;
      Metrics   : out Flight_Metrics;
      Solver    : out Solver_Kind;
      Chemistry : out Chemistry_Mode) return Boolean
   is
      F           : File_Type;
      Path        : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      Raw_Line    : String (1 .. 2048);
      Last        : Natural;
      Found       : Boolean := False;
      Fields      : Field_Array;
      Field_Count : Natural;
      Rec         : Run_Record;
      pragma Unreferenced (TPS);
   begin
      if not DB_Initialised or not Exists (Path) then
         return False;
      end if;

      Open (F, In_File, Path);

      --  Skip header line
      if not End_Of_File (F) then
         Skip_Line (F);
      end if;

      --  Search for matching name
      while not End_Of_File (F) loop
         Get_Line (F, Raw_Line, Last);

         if Last > 0 then
            Field_Count := Parse_CSV_Line (Raw_Line (1 .. Last), Fields);

            --  Check if field 1 (name) matches
            if Field_Count >= 1 then
               declare
                  Field_Name : constant String :=
                    CSV_Unescape (To_String (Fields (1)));
               begin
                  if Field_Name'Length = Name'Length and then
                     Field_Name = Name
                  then
                     Found := True;
                     Populate_Run_Record (Fields, Field_Count, Rec);
                     exit;
                  end if;
               end;
            end if;
         end if;
      end loop;

      Close (F);

      if Found then
         Flight    := Rec.Flight;
         Geo       := Rec.Geo;
         --  TPS is not stored in CSV; caller gets default TPS.
         --  This matches the flat-file design where TPS is a
         --  simulation-time parameter, not a persisted one.
         Results   := Rec.Results;
         Metrics   := Rec.Metrics;
         Solver    := Rec.Solver;
         Chemistry := Rec.Chemistry;
      end if;

      return Found;

   exception
      when E : others =>
         Put_Line ("[HISTORY ERROR] Load_Run: " &
                    Exception_Message (E));
         if Is_Open (F) then
            Close (F);
         end if;
         return False;
   end Load_Run;

   -- ==================================================================
   --  Delete_Run — Rewrite CSV excluding the named run.
   -- ==================================================================
   function Delete_Run (Name : String) return Boolean is
      F           : File_Type;
      Tmp         : File_Type;
      Path        : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      Tmp_Path    : constant String := Path & ".tmp";
      Raw_Line    : String (1 .. 2048);
      Last        : Natural;
      Found       : Boolean := False;
      Fields      : Field_Array;
      Field_Count : Natural;
      Header      : Unbounded_String;
   begin
      if not DB_Initialised or not Exists (Path) then
         return False;
      end if;

      Acquire_Lock;
      begin
         --  Read header
         Open (F, In_File, Path);
         if not End_Of_File (F) then
            Get_Line (F, Raw_Line, Last);
            Header := To_Unbounded_String (Raw_Line (1 .. Last));
         end if;

         --  Copy all non-matching lines to temp file
         Create (Tmp, Out_File, Tmp_Path);
         Put_Line (Tmp, To_String (Header));

         while not End_Of_File (F) loop
            Get_Line (F, Raw_Line, Last);
            if Last > 0 then
               Field_Count := Parse_CSV_Line (Raw_Line (1 .. Last), Fields);
               if Field_Count >= 1 then
                  declare
                     Field_Name : constant String :=
                       CSV_Unescape (To_String (Fields (1)));
                  begin
                     if Field_Name'Length = Name'Length and then
                        Field_Name = Name
                     then
                        Found := True;  --  skip this line
                     else
                        Put_Line (Tmp, Raw_Line (1 .. Last));
                     end if;
                  end;
               else
                  Put_Line (Tmp, Raw_Line (1 .. Last));
               end if;
            end if;
         end loop;

         Close (F);
         Close (Tmp);

         --  Replace original with temp
         Delete_File (Path);
         Rename (Tmp_Path, Path);

         if Found then
            Put_Line ("[HISTORY] Run deleted: " & Name);
         end if;

      exception
         when E : others =>
            Put_Line ("[HISTORY ERROR] Delete_Run: " &
                       Exception_Message (E));
            if Is_Open (F) then Close (F); end if;
            if Is_Open (Tmp) then Close (Tmp); end if;
            if Exists (Tmp_Path) then
               begin Delete_File (Tmp_Path); exception
                  when others => null;
               end;
            end if;
      end;
      Release_Lock;

      return Found;
   end Delete_Run;

   -- ==================================================================
   --  Get_All_Runs — Read all rows into a Run_Set.
   -- ==================================================================
   function Get_All_Runs return Run_Set is
      F           : File_Type;
      Path        : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      Raw_Line    : String (1 .. 2048);
      Last        : Natural;
      Fields      : Field_Array;
      Field_Count : Natural;
      Result      : Run_Set;
   begin
      if not DB_Initialised or not Exists (Path) then
         return Result;
      end if;

      Open (F, In_File, Path);

      --  Skip header
      if not End_Of_File (F) then
         Skip_Line (F);
      end if;

      while not End_Of_File (F) loop
         Get_Line (F, Raw_Line, Last);

         if Last > 0 and then Result.Count < Max_Run_Count then
            Field_Count := Parse_CSV_Line (Raw_Line (1 .. Last), Fields);
            if Field_Count >= 1 then
               Result.Count := Result.Count + 1;
               Populate_Run_Record (Fields, Field_Count,
                                    Result.Data (Result.Count));
            end if;
         end if;
      end loop;

      Close (F);
      return Result;

   exception
      when E : others =>
         Put_Line ("[HISTORY ERROR] Get_All_Runs: " &
                    Exception_Message (E));
         if Is_Open (F) then
            Close (F);
         end if;
         return Result;
   end Get_All_Runs;

   -- ==================================================================
   --  Update_Run_Progress — Find the run and rewrite with new progress.
   -- ==================================================================
   procedure Update_Run_Progress
     (Name     : String;
      Progress : Float;
      Status   : String := "")
   is
      F           : File_Type;
      Tmp         : File_Type;
      Path        : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      Tmp_Path    : constant String := Path & ".tmp";
      Raw_Line    : String (1 .. 2048);
      Last        : Natural;
      Found       : Boolean := False;
      Fields      : Field_Array;
      Field_Count : Natural;
      Header      : Unbounded_String;
      New_Status  : Unbounded_String;
   begin
      if not DB_Initialised or not Exists (Path) then
         return;
      end if;

      New_Status := To_Unbounded_String (Status);

      Acquire_Lock;
      begin
         --  Read header
         Open (F, In_File, Path);
         if not End_Of_File (F) then
            Get_Line (F, Raw_Line, Last);
            Header := To_Unbounded_String (Raw_Line (1 .. Last));
         end if;

         --  Rewrite file with updated progress
         Create (Tmp, Out_File, Tmp_Path);
         Put_Line (Tmp, To_String (Header));

         while not End_Of_File (F) loop
            Get_Line (F, Raw_Line, Last);
            if Last > 0 then
               Field_Count := Parse_CSV_Line (Raw_Line (1 .. Last), Fields);
               if Field_Count >= 1 then
                  declare
                     Field_Name : constant String :=
                       CSV_Unescape (To_String (Fields (1)));
                  begin
                     if Field_Name'Length = Name'Length and then
                        Field_Name = Name
                     then
                        Found := True;
                        --  Rebuild the line with updated status/progress
                        --  Write the base fields (1..28) unchanged
                        declare
                           New_Line : Unbounded_String;
                        begin
                           New_Line := To_Unbounded_String (Raw_Line (1 .. Last));

                           --  Ensure we have at least 28 fields + comma
                           --  Append or replace status/progress
                           if Field_Count < 28 then
                              --  Pad with commas
                              for I in Field_Count + 1 .. 28 loop
                                 Append (New_Line, ",");
                              end loop;
                           end if;

                           --  Remove trailing status/progress fields if present
                           --  by truncating at field 28 boundary
                           declare
                              Comma_Pos : Natural := 0;
                              Cnt       : Natural := 0;
                           begin
                              for I in Raw_Line (1 .. Last)'Range loop
                                 if Raw_Line (I) = ',' then
                                    Cnt := Cnt + 1;
                                    if Cnt = 28 then
                                       Comma_Pos := I;
                                       exit;
                                    end if;
                                 end if;
                              end loop;
                              if Comma_Pos > 0 then
                                 New_Line := To_Unbounded_String (
                                   Raw_Line (1 .. Comma_Pos - 1));
                              end if;
                           end;

                           --  Append new status and progress
                           Append (New_Line, ",");
                           if Length (New_Status) > 0 then
                              Append (New_Line,
                                CSV_Escape (To_String (New_Status)));
                           else
                              Append (New_Line, "completed");
                           end if;
                           Append (New_Line, ",");
                           Append (New_Line, F2S (Progress));

                           Put_Line (Tmp, To_String (New_Line));
                        end;
                     else
                        --  Keep original line
                        Put_Line (Tmp, Raw_Line (1 .. Last));
                     end if;
                  end;
               else
                  Put_Line (Tmp, Raw_Line (1 .. Last));
               end if;
            end if;
         end loop;

         Close (F);
         Close (Tmp);

         --  Replace original with temp
         Delete_File (Path);
         Rename (Tmp_Path, Path);

         if Found then
            Put_Line ("[HISTORY] Progress updated for: " & Name);
         end if;

      exception
         when E : others =>
            Put_Line ("[HISTORY ERROR] Update_Run_Progress: " &
                       Exception_Message (E));
            if Is_Open (F) then Close (F); end if;
            if Is_Open (Tmp) then Close (Tmp); end if;
            if Exists (Tmp_Path) then
               begin Delete_File (Tmp_Path); exception
                  when others => null;
               end;
            end if;
      end;
      Release_Lock;
   end Update_Run_Progress;

   -- ==================================================================
   --  Upsert_Draft — Insert or update a draft run row.
   -- ==================================================================
   procedure Upsert_Draft
     (Name     : String;
      Flight   : Flight_Parameters;
      Geo      : Geometry_Parameters;
      TPS      : TPS_Material;
      Results  : Simulation_Results;
      Metrics  : Flight_Metrics;
      Solver   : Solver_Kind;
      Chem     : Chemistry_Mode;
      Progress : Float)
   is
      F           : File_Type;
      Tmp         : File_Type;
      Path        : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      Tmp_Path    : constant String := Path & ".tmp";
      Raw_Line    : String (1 .. 2048);
      Last        : Natural;
      Found       : Boolean := False;
      pragma Unreferenced (TPS);
      Fields      : Field_Array;
      Field_Count : Natural;
      Header      : Unbounded_String;

      --  Build a CSV line for the draft row
      function Build_Draft_Line return String is
         Line : Unbounded_String;
      begin
         Line := To_Unbounded_String (CSV_Escape (Name) & ",");
         Append (Line, F2S (Flight.Mach) & ",");
         Append (Line, F2S (Flight.Altitude_Km) & ",");
         Append (Line, F2S (Flight.Velocity_Ms) & ",");
         Append (Line, F2S (Flight.Density_Kgm3) & ",");
         Append (Line, F2S (Flight.Temperature_K) & ",");
         Append (Line, F2S (Geo.Diameter_M) & ",");
         Append (Line, F2S (Geo.Angle_Deg) & ",");
         Append (Line, F2S (Geo.Nose_Radius_M) & ",");
         Append (Line, Trim (Positive'Image (Geo.Toroid_Count), Both) & ",");
         Append (Line, F2S (Geo.Toroid_Radius_M) & ",");
         Append (Line, F2S (Geo.Mass_Kg) & ",");
         Append (Line, F2S (Results.Drag_Force) & ",");
         Append (Line, F2S (Results.Heat_Flux_Wm2) & ",");
         Append (Line, F2S (Results.Total_Heat_Load) & ",");
         Append (Line, F2S (Results.Stag_Pressure_Pa) & ",");
         Append (Line, F2S (Results.Shock_Temp_K) & ",");
         Append (Line, F2S (Metrics.Ballistic_Coeff) & ",");
         Append (Line, F2S (Metrics.Knudsen_Number) & ",");
         Append (Line, F2S (Metrics.Stag_Heat_Flux_Wm2) & ",");
         Append (Line, F2S (Metrics.Stag_Heat_Flux_Wcm2) & ",");
         Append (Line, F2S (Metrics.Surface_Temp_K) & ",");
         Append (Line, F2S (Metrics.Backface_Temp_K) & ",");
         Append (Line, F2S (Metrics.Decel_G) & ",");
         Append (Line, F2S (Metrics.G_Load) & ",");
         Append (Line, B2S (Metrics.Survivable) & ",");
         Append (Line, Solver_To_Str (Solver) & ",");
         Append (Line, Chem_To_Str (Chem) & ",");
         Append (Line, "draft,");
         Append (Line, F2S (Progress));
         return To_String (Line);
      end Build_Draft_Line;

   begin
      if not DB_Initialised then
         Put_Line ("[HISTORY ERROR] Database not initialised.");
         return;
      end if;

      Acquire_Lock;
      begin
         --  Read header and search for existing draft with same name
         if Exists (Path) then
            Open (F, In_File, Path);
            if not End_Of_File (F) then
               Get_Line (F, Raw_Line, Last);
               Header := To_Unbounded_String (Raw_Line (1 .. Last));
            end if;

            Create (Tmp, Out_File, Tmp_Path);
            Put_Line (Tmp, To_String (Header));

            while not End_Of_File (F) loop
               Get_Line (F, Raw_Line, Last);
               if Last > 0 then
                  Field_Count := Parse_CSV_Line (Raw_Line (1 .. Last), Fields);
                  if Field_Count >= 1 then
                     declare
                        Field_Name : constant String :=
                          CSV_Unescape (To_String (Fields (1)));
                        Field_Status : constant String :=
                          (if Field_Count >= 29
                           then CSV_Unescape (To_String (Fields (29)))
                           else "completed");
                     begin
                        if Field_Name'Length = Name'Length and then
                           Field_Name = Name and then
                           Field_Status = "draft"
                        then
                           --  Replace this line with the updated draft
                           Found := True;
                           Put_Line (Tmp, Build_Draft_Line);
                        else
                           Put_Line (Tmp, Raw_Line (1 .. Last));
                        end if;
                     end;
                  else
                     Put_Line (Tmp, Raw_Line (1 .. Last));
                  end if;
               end if;
            end loop;

            Close (F);
         else
            --  File doesn't exist yet; create it
            Create (Tmp, Out_File, Tmp_Path);
            Put_Line (Tmp,
              "name,mach,alt_km,vel_ms,rho,density_temp_k," &
              "diameter,angle,nose_r,toroid_n,toroid_r," &
              "mass,drag_force,heat_flux,total_load," &
              "stag_pressure,shock_temp," &
              "ballistic_coeff,knudsen,stag_hf_wm2," &
              "stag_hf_wcm2,surf_temp,backface_temp," &
              "decel_g,g_load,survivable,solver,chemistry," &
              "status,progress");
         end if;

         --  If no existing draft was found, append the new one
         if not Found then
            Put_Line (Tmp, Build_Draft_Line);
         end if;

         Close (Tmp);

         --  Replace original with temp
         if Exists (Path) then
            Delete_File (Path);
         end if;
         Rename (Tmp_Path, Path);

         if Found then
            Put_Line ("[HISTORY] Draft updated: " & Name);
         else
            Put_Line ("[HISTORY] Draft created: " & Name);
         end if;

      exception
         when E : others =>
            Put_Line ("[HISTORY ERROR] Upsert_Draft: " &
                       Exception_Message (E));
            if Is_Open (F) then Close (F); end if;
            if Is_Open (Tmp) then Close (Tmp); end if;
            if Exists (Tmp_Path) then
               begin Delete_File (Tmp_Path); exception
                  when others => null;
               end;
            end if;
      end;
      Release_Lock;
   end Upsert_Draft;

   -- ==================================================================
   --  Save_Sample
   -- ==================================================================
   procedure Save_Sample
     (Sample_Index : Positive;
      Geo          : Geometry_Parameters;
      Results      : Simulation_Results;
      Metrics      : Flight_Metrics)
   is
      F    : File_Type;
      Path : constant String :=
        Compose (To_String (DB_Directory), Samples_File);
      Line : Unbounded_String;
   begin
      if not DB_Initialised then
         Put_Line ("[HISTORY ERROR] Database not initialised.");
         return;
      end if;

      Acquire_Lock;
      begin
         Line := To_Unbounded_String (
           Trim (Positive'Image (Sample_Index), Both) & ",");
         Append (Line, F2S (Geo.Diameter_M) & ",");
         Append (Line, F2S (Geo.Angle_Deg) & ",");
         Append (Line, F2S (Geo.Nose_Radius_M) & ",");
         Append (Line, Trim (Positive'Image (Geo.Toroid_Count), Both) & ",");
         Append (Line, F2S (Geo.Toroid_Radius_M) & ",");
         Append (Line, F2S (Geo.Mass_Kg) & ",");
         Append (Line, F2S (Results.Drag_Force) & ",");
         Append (Line, F2S (Results.Heat_Flux_Wm2) & ",");
         Append (Line, F2S (Results.Total_Heat_Load) & ",");
         Append (Line, F2S (Metrics.Ballistic_Coeff) & ",");
         Append (Line, F2S (Metrics.Decel_G) & ",");
         Append (Line, B2S (Metrics.Survivable));

         Open (F, Append_File, Path);
         Put_Line (F, To_String (Line));
         Close (F);

         Put_Line ("[HISTORY] Sample " &
                   Trim (Positive'Image (Sample_Index), Both) & " saved.");
      exception
         when E : others =>
            Put_Line ("[HISTORY ERROR] Save_Sample: " &
                       Exception_Message (E));
            if Is_Open (F) then
               Close (F);
            end if;
      end;
      Release_Lock;
   end Save_Sample;

   -- ==================================================================
   --  Run_Count / Sample_Count
   -- ==================================================================
   function Run_Count return Natural is
      F    : File_Type;
      Path : constant String :=
        Compose (To_String (DB_Directory), Runs_File);
      N    : Natural := 0;
   begin
      if not DB_Initialised or not Exists (Path) then
         return 0;
      end if;

      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         Skip_Line (F);
         N := N + 1;
      end loop;
      Close (F);

      if N > 0 then
         N := N - 1;
      end if;
      return N;
   exception
      when others =>
         if Is_Open (F) then
            Close (F);
         end if;
         return 0;
   end Run_Count;

   function Sample_Count return Natural is
      F    : File_Type;
      Path : constant String :=
        Compose (To_String (DB_Directory), Samples_File);
      N    : Natural := 0;
   begin
      if not DB_Initialised or not Exists (Path) then
         return 0;
      end if;

      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         Skip_Line (F);
         N := N + 1;
      end loop;
      Close (F);

      if N > 0 then
         N := N - 1;
      end if;
      return N;
   exception
      when others =>
         if Is_Open (F) then
            Close (F);
         end if;
         return 0;
   end Sample_Count;

end StellarOrion_History;
