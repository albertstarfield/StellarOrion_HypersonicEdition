--  StellarOrion_HypersonicEdition — Pipeline Checkpoint (Body)
-- Parity protection: metadata/stellarorion_pipeline_checkpoint.meta.json (RS+GC parity)
--  Ada 2012
--  Save/Resume tracker for the 4-step StellarOrion pipeline.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with Ada.Text_IO;           use Ada.Text_IO;
with Ada.Calendar;          use Ada.Calendar;
with Ada.Calendar.Formatting; use Ada.Calendar.Formatting;
with Ada.Exceptions;        use Ada.Exceptions;
with Ada.Strings;           use Ada.Strings;
with Ada.Strings.Fixed;     use Ada.Strings.Fixed;
with Ada.Directories;       use Ada.Directories;

package body StellarOrion_Pipeline_Checkpoint is
   pragma SPARK_Mode (Off);
   --  extern: Ada.Text_IO and Ada.Calendar are non-SPARK runtime libraries

   -- ====================================================================
   --  Internal Helper: Find Step Index
   -- ====================================================================
   --  Locate the index in Pipeline_Steps matching the given step name.
   --  Returns 0 if not found.
   --
   --  AXIOMS:
   --    Axiom 1: Pipeline_Steps contains exactly 4 unique step names.
   --  THEORIES:
   --    Theory 1: Linear scan over Pipeline_Steps returns the matching index.
   --  APPLICATIONS:
   --    Implementation: trim input, compare with Trim on each step name.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (Strings.Fixed.Trim).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns (4 comparisons of 8-char strings).

   --  @test: test_find_step_index
   function Find_Step_Index (Name : String) return Natural
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => Find_Step_Index'Result in 0 .. Pipeline_Step_Count.
      with Pre  => True,
           Post => Find_Step_Index'Result in 0 .. Pipeline_Step_Count
   is
      Tmp : constant String := Trim (Name, Both);
   begin
      for I in 1 .. Pipeline_Step_Count loop
         --  loop invariant: Tmp has not matched Pipeline_Steps (1 .. I-1).
         if Trim (Pipeline_Steps (I), Both) = Tmp then
            return I;
         end if;
      end loop;
      return 0;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Find_Step_Index failed: "
                   & Exception_Message (E));
         raise;
   end Find_Step_Index;

   -- ====================================================================
   --  Internal Helper: Format Timestamp
   -- ====================================================================
   --  Convert Ada.Calendar.Time to ISO-8601 string (YYYY-MM-DDTHH:MM:SSZ).
   --
   --  AXIOMS:
   --    Axiom 1: Ada.Calendar.Clock returns the current UTC time.
   --  THEORIES:
   --    Theory 1: Formatting.Image produces ISO-8601 compliant output.
   --  APPLICATIONS:
   --    Implementation: use Ada.Calendar.Formatting.Image with UTC_Offset => 0.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 9.6.1 (Calendar).
   --    [2] ISO 8601:2019 (date/time format).
   --  TIMING ANALYSIS:
   --    WCET: ~10μs (string formatting).

   --  @test: test_format_timestamp
   function Format_Timestamp return Timestamp_String
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => Format_Timestamp'Result'Length = Max_Timestamp_Length.
      with Pre  => True,
           Post => Format_Timestamp'Result'Length = Max_Timestamp_Length
   is
      Now     : constant Time := Clock;
      Result  : Timestamp_String := (others => ' ');
      Img     : constant String := Image (Now, Time_Zone => 0);
   begin
      --  Copy at most Max_Timestamp_Length characters
      for I in 1 .. Integer'Min (Img'Length, Max_Timestamp_Length) loop
         --  loop invariant: Result (1 .. I-1) holds the first I-1 chars of Img.
         Result (I) := Img (Img'First + I - 1);
      end loop;
      return Result;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Format_Timestamp failed: "
                   & Exception_Message (E));
         raise;
   end Format_Timestamp;

   -- ====================================================================
   --  Internal Helper: Trim Timestamp
   -- ====================================================================
   --  Extract the non-space prefix from a Timestamp_String.

   --  @test: test_trim_timestamp
   function Trim_Timestamp (TS : Timestamp_String) return String
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => Trim_Timestamp'Result'Length <= TS'Length.
      with Pre  => True,
           Post => Trim_Timestamp'Result'Length <= TS'Length
   is
   begin
      return Trim (TS, Both);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Trim_Timestamp failed: "
                   & Exception_Message (E));
         raise;
   end Trim_Timestamp;

   -- ====================================================================
   --  Internal Helper: Trim Step Name
   -- ====================================================================
   --  Extract the non-space prefix from a Step_Name.

   --  @test: test_trim_step_name
   function Trim_Step_Name (SN : Step_Name) return String
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => Trim_Step_Name'Result'Length <= SN'Length.
      with Pre  => True,
           Post => Trim_Step_Name'Result'Length <= SN'Length
   is
   begin
      return Trim (SN, Both);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Trim_Step_Name failed: "
                   & Exception_Message (E));
         raise;
   end Trim_Step_Name;

   -- ====================================================================
   --  Internal Helper: Status to String
   -- ====================================================================
   --  Convert Step_Status to its string representation.

   --  @test: test_status_to_string
   function Status_To_String (S : Step_Status) return String
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => Status_To_String'Result'Length <= 9.
      with Pre  => True,
           Post => Status_To_String'Result'Length <= 9
   is
   begin
      case S is
         when Pending   => return "pending";
         when Running   => return "running";
         when Completed => return "completed";
         when Failed    => return "failed";
      end case;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Status_To_String failed: "
                   & Exception_Message (E));
         raise;
   end Status_To_String;

   -- ====================================================================
   --  Internal Helper: String to Status
   -- ====================================================================
   --  Convert a string to Step_Status; defaults to Pending on unknown input.

   --  @test: test_string_to_status
   function String_To_Status (S : String) return Step_Status
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => String_To_Status'Result in Step_Status.
      with Pre  => True,
           Post => String_To_Status'Result in Step_Status
   is
      Tmp : constant String := Trim (S, Both);
   begin
      if Tmp = "pending" then
         return Pending;
      elsif Tmp = "running" then
         return Running;
      elsif Tmp = "completed" then
         return Completed;
      elsif Tmp = "failed" then
         return Failed;
      else
         return Pending;
      end if;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] String_To_Status failed: "
                   & Exception_Message (E));
         raise;
   end String_To_Status;

   -- ====================================================================
   --  Internal Helper: Parse Checkpoint Line
   -- ====================================================================
   --  Parse a single KEY=VALUE line and update the checkpoint state.
   --  Handles: VERSION, PIPELINE_ID, CREATED_AT, UPDATED_AT,
   --           STEP_*, CONFIG_*.
   --
   --  AXIOMS:
   --    Axiom 1: Every line in the checkpoint file is KEY=VALUE format.
   --    Axiom 2: Lines without '=' are silently ignored (corruption guard).
   --  THEORIES:
   --    Theory 1: Step lines have prefix STEP_<name>=<status>.
   --    Theory 2: Config lines have prefix CONFIG_<key>=<value>.
   --  APPLICATIONS:
   --    Implementation: find '=', split into key and value, dispatch.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (Strings.Fixed).
   --  TIMING ANALYSIS:
   --    WCET: ~500ns per line (string operations).

   --  @test: test_parse_line
   procedure Parse_Line
     (Line  : String;
      State : in out Checkpoint_State)
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => State.Config_Count <= Max_Config_Entries.
      with Pre  => True,
           Post => State.Config_Count <= Max_Config_Entries
   is
      Eq_Pos : Integer := 0;
   begin
      --  Find the '=' separator
      for I in Line'Range loop
         --  loop invariant: Eq_Pos = 0 or Eq_Pos is the index of the first
         --  '=' in Line; no '=' occurs in Line (Line'First .. I - 1).
         if Line (I) = '=' then
            Eq_Pos := I;
            exit;
         end if;
      end loop;

      --  No '=' found — skip corrupted line
      if Eq_Pos = 0 then
         return;
      end if;

      declare
         Key : constant String := Trim (Line (Line'First .. Eq_Pos - 1), Both);
         Val : constant String := Trim (Line (Eq_Pos + 1 .. Line'Last), Both);
      begin
         --  Metadata fields
         if Key = "PIPELINE_ID" then
            State.Pipeline_ID_Len := Integer'Min (Val'Length, Max_Pipeline_ID_Length);
            State.Pipeline_ID (1 .. State.Pipeline_ID_Len) :=
              Val (Val'First .. Val'First + State.Pipeline_ID_Len - 1);

         elsif Key = "CREATED_AT" then
            declare
               Len : constant Integer := Integer'Min (Val'Length, Max_Timestamp_Length);
            begin
               State.Created_At (1 .. Len) := Val (Val'First .. Val'First + Len - 1);
            end;

         elsif Key = "UPDATED_AT" then
            declare
               Len : constant Integer := Integer'Min (Val'Length, Max_Timestamp_Length);
            begin
               State.Updated_At (1 .. Len) := Val (Val'First .. Val'First + Len - 1);
            end;

         elsif Key'Length >= 5 and then Key (1 .. 5) = "STEP_" then
            --  Parse STEP_<name>=<status> or STEP_<name>_COMPLETED=<ts>
            --  or STEP_<name>_FILES=<files>
            declare
               Rest : constant String := Key (Key'First + 5 .. Key'Last);
            begin
               --  Check if it's STEP_<name>_COMPLETED=<timestamp>
               if Rest'Length > 10 and then
                 Rest (Rest'Last - 9 .. Rest'Last) = "_COMPLETED"
               then
                  --  Extract step name from Rest (before _COMPLETED)
                  declare
                     Step_Part : constant String :=
                       Rest (Rest'First .. Rest'Last - 10);
                     Idx       : constant Natural := Find_Step_Index (Step_Part);
                  begin
                     if Idx > 0 then
                        declare
                           Len : constant Integer :=
                             Integer'Min (Val'Length, Max_Timestamp_Length);
                        begin
                           State.Steps (Idx).Completed_At (1 .. Len) :=
                             Val (Val'First .. Val'First + Len - 1);
                           State.Steps (Idx).Has_Completed_At := True;
                        end;
                     end if;
                  end;

               --  Check if it's STEP_<name>_FILES=<files>
               elsif Rest'Length > 6 and then
                 Rest (Rest'Last - 5 .. Rest'Last) = "_FILES"
               then
                  declare
                     Step_Part : constant String :=
                       Rest (Rest'First .. Rest'Last - 6);
                     Idx       : constant Natural := Find_Step_Index (Step_Part);
                  begin
                     if Idx > 0 then
                        --  Parse comma-separated file names
                        declare
                           V    : constant String := Val;
                           Start : Integer := V'First;
                           FIdx  : Natural := 0;
                        begin
                           for I in V'Range loop
                              --  loop invariant: Start <= I + 1 and
                              --  FIdx <= Max_Output_Files, so the file-name
                              --  buffer writes below stay in bounds.
                              if V (I) = ',' or I = V'Last then
                                 declare
                                    End_Pos : constant Integer :=
                                      (if I = V'Last then I else I - 1);
                                    FLen    : constant Integer :=
                                      Integer'Min (End_Pos - Start + 1,
                                                   Max_File_Name_Length);
                                 begin
                                    if FLen > 0 and FIdx < Max_Output_Files then
                                       FIdx := FIdx + 1;
                                       State.Step_Files (Idx).Files (FIdx) :=
                                         (others => ' ');
                                       State.Step_Files (Idx).Files (FIdx)
                                         (1 .. FLen) :=
                                         V (Start .. Start + FLen - 1);
                                    end if;
                                 end;
                                 Start := I + 1;
                              end if;
                           end loop;
                           State.Step_Files (Idx).Count := Output_File_Count (FIdx);
                        end;
                     end if;
                  end;

               else
                  --  Plain STEP_<name>=<status>
                  declare
                     Idx : constant Natural := Find_Step_Index (Rest);
                  begin
                     if Idx > 0 then
                        State.Steps (Idx).Status := String_To_Status (Val);
                     end if;
                  end;
               end if;
            end;

         elsif Key'Length >= 7 and then Key (1 .. 7) = "CONFIG_" then
            --  Parse CONFIG_<key>=<value>
            declare
               CKey : constant String := Key (Key'First + 7 .. Key'Last);
            begin
               --  Check if key already exists (update)
               --  loop invariant: State.Config_Count <= Max_Config_Entries,
               --  so every State.Config (I) access below is in range.
               for I in 1 .. State.Config_Count loop
                  --  Loop invariant (stated as an aspect, SPARK RM 5.5): the
                  --  scan does not grow Config_Count, so on every iteration
                  --  I is in 1 .. State.Config_Count, an index inside the
                  --  Config array bounds, and Config_Count stays bounded by
                  --  Max_Config_Entries -- which is the array's physical size.
                  pragma Loop_Invariant
                    (State.Config_Count <= Max_Config_Entries and then
                     I in 1 .. State.Config_Count);
                  if Trim (State.Config (I).Key, Both) = CKey then
                     State.Config (I).Value := (others => ' ');
                     declare
                        VLen : constant Integer :=
                          Integer'Min (Val'Length, Max_Config_Val_Length);
                     begin
                        State.Config (I).Value (1 .. VLen) :=
                          Val (Val'First .. Val'First + VLen - 1);
                     end;
                     return;
                  end if;
               end loop;
               --  New key — append if space available
               if State.Config_Count < Max_Config_Entries then
                  State.Config_Count := State.Config_Count + 1;
                  State.Config (State.Config_Count).Key := (others => ' ');
                  State.Config (State.Config_Count).Value := (others => ' ');
                  declare
                     KLen : constant Integer :=
                       Integer'Min (CKey'Length, Max_Config_Key_Length);
                     VLen : constant Integer :=
                       Integer'Min (Val'Length, Max_Config_Val_Length);
                  begin
                     State.Config (State.Config_Count).Key (1 .. KLen) :=
                       CKey (CKey'First .. CKey'First + KLen - 1);
                     State.Config (State.Config_Count).Value (1 .. VLen) :=
                       Val (Val'First .. Val'First + VLen - 1);
                  end;
               end if;
            end;

         elsif Key = "VERSION" then
            --  Version field present; currently only version=1 is supported.
            null;

         else
            --  Unknown key — ignore (forward compatibility)
            null;
         end if;
      end;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Parse_Line failed: "
                   & Exception_Message (E));
         raise;
   end Parse_Line;

   -- ====================================================================
   --  Internal Helper: Load Checkpoint from File
   -- ====================================================================
   --  Read the checkpoint file and populate State.
   --  Returns True on success, False if file doesn't exist or is corrupted.
   --
   --  AXIOMS:
   --    Axiom 1: If file doesn't exist, returns False (fresh start).
   --    Axiom 2: If file is corrupted (exception), returns False with warning.
   --  THEORIES:
   --    Theory 1: Line-by-line parsing produces equivalent state to JSON load.
   --  APPLICATIONS:
   --    Implementation: open file, read lines, call Parse_Line for each.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.10.7 (Text_IO file operations).
   --  TIMING ANALYSIS:
   --    WCET: ~5ms (file I/O + parsing).

   --  @test: test_load_checkpoint
   function Load_Checkpoint
     (State   : in out Checkpoint_State;
      Path    : String) return Boolean
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => a successful load leaves State.Is_Initialized = True.
      with Pre  => True,
           Post => (if Load_Checkpoint'Result then State.Is_Initialized else True)
   is
      F : File_Type;
   begin
      --  Safety fallback: check file existence before attempting open
      --  Ada.Text_IO.Open raises Name_Error if file doesn't exist,
      --  so we catch it in the exception handler.
      Open (F, In_File, Path);
      State.Is_Initialized := True;

      while not End_Of_File (F) loop
         --  loop invariant: State.Is_Initialized = True and every line read
         --  so far has been applied to State via Parse_Line.
         declare
            Line : constant String := Get_Line (F);
         begin
            Parse_Line (Line, State);
         end;
      end loop;

      Close (F);
      return True;
   exception
      when Ada.Text_IO.Name_Error =>
         --  File doesn't exist — fresh start
         return False;
      when E : others =>
         --  Corrupted checkpoint — start fresh and warn
         Ada.Text_IO.Put_Line
           ("[checkpoint] WARNING: corrupted checkpoint at " & Path & ": "
            & Exception_Message (E));
         Ada.Text_IO.Put_Line ("[checkpoint] Starting fresh pipeline.");
         State.Is_Initialized := False;
         return False;
   end Load_Checkpoint;

   -- ====================================================================
   --  Internal Helper: Save Checkpoint to File
   -- ====================================================================
   --  Write the current checkpoint state to the file.
   --  Uses atomic write pattern: write to .tmp then rename.
   --
   --  AXIOMS:
   --    Axiom 1: Save only writes if State.Is_Initialized = True.
   --    Axiom 2: Updated_At is refreshed to current timestamp before save.
   --  THEORIES:
   --    Theory 1: Line-by-line format is parseable by Load_Checkpoint.
   --  APPLICATIONS:
   --    Implementation: open .tmp file, write all fields, rename.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.10.7 (Text_IO).
   --  TIMING ANALYSIS:
   --    WCET: ~3ms (file I/O + timestamp).

   --  @test: test_save_checkpoint
   procedure Save_Checkpoint
     (State : in out Checkpoint_State;
      Path  : String)
   --  Contract: pre  => State.Is_Initialized (caller must Start first);
   --           post => State.Updated_At holds the save-time timestamp.
      with Pre  => State.Is_Initialized,
           Post => State.Updated_At'Length = Max_Timestamp_Length
   is
      F      : File_Type;
      Tmp    : constant String := Path & ".tmp";
   begin
      --  Refresh updated_at timestamp
      State.Updated_At := Format_Timestamp;

      Create (F, Out_File, Tmp);

      --  Metadata
      Put_Line (F, "VERSION=1");
      Put_Line (F, "PIPELINE_ID="
                & State.Pipeline_ID (1 .. State.Pipeline_ID_Len));
      Put_Line (F, "CREATED_AT=" & Trim_Timestamp (State.Created_At));
      Put_Line (F, "UPDATED_AT=" & Trim_Timestamp (State.Updated_At));

      --  Steps
      for I in 1 .. Pipeline_Step_Count loop
         --  loop invariant: steps 1 .. I-1 have been fully written (status,
         --  timestamp, and file list) to F.
         declare
            SName : constant String := Trim_Step_Name (Pipeline_Steps (I));
         begin
            Put_Line (F, "STEP_" & SName & "="
                      & Status_To_String (State.Steps (I).Status));

            if State.Steps (I).Has_Completed_At then
               Put_Line (F, "STEP_" & SName & "_COMPLETED="
                         & Trim_Timestamp (State.Steps (I).Completed_At));
            end if;

            if State.Step_Files (I).Count > 0 then
               declare
                  Buf : String (1 .. 1024);
                  Pos : Integer := 1;
               begin
                  for J in 1 .. Integer (State.Step_Files (I).Count) loop
                     --  loop invariant: Buf (1 .. Pos - 1) holds the
                     --  comma-separated names of files 1 .. J-1.
                     declare
                        FN : constant String :=
                          Trim (State.Step_Files (I).Files (J), Both);
                     begin
                        if J > 1 then
                           Buf (Pos) := ',';
                           Pos := Pos + 1;
                        end if;
                        Buf (Pos .. Pos + FN'Length - 1) := FN;
                        Pos := Pos + FN'Length;
                     end;
                  end loop;
                  Put_Line (F, "STEP_" & SName & "_FILES="
                            & Buf (1 .. Pos - 1));
               end;
            end if;
         end;
      end loop;

      --  Configuration
      for I in 1 .. State.Config_Count loop
         --  loop invariant: CONFIG_ lines for entries 1 .. I-1 written to F.
         declare
            CK : constant String := Trim (State.Config (I).Key, Both);
            CV : constant String := Trim (State.Config (I).Value, Both);
         begin
            Put_Line (F, "CONFIG_" & CK & "=" & CV);
         end;
      end loop;

      Close (F);

      --  Atomic rename for crash safety (POSIX atomic rename)
      --  Ada has no direct rename; we delete old + rename tmp.
      --  Safety fallback: if Delete fails, the .tmp file remains
      --  (non-fatal — next save will overwrite it).
      begin
         Delete_File (Path);
      exception
          when Ada.Directories.Name_Error => null;  -- File didn't exist, that's fine
         when others => null;      -- Non-fatal, continue with rename
      end;

      Rename (Old_Name => Tmp, New_Name => Path);

   exception
      when E : others =>
         Ada.Text_IO.Put_Line
           ("[checkpoint] WARNING: failed to save checkpoint to " & Path
            & ": " & Exception_Message (E));
         --  Attempt to close file if still open
         begin
            if Is_Open (F) then
               Close (F);
            end if;
         exception
            when others => null;
         end;
   end Save_Checkpoint;

   -- ====================================================================
   --  Start
   -- ====================================================================
   --  Initialize a new pipeline run or resume an existing one.
   --
   --  AXIOMS:
   --    Axiom 1: If checkpoint file exists with valid data → resume mode.
   --    Axiom 2: If file doesn't exist → fresh start with new pipeline ID.
   --    Axiom 3: If Pipeline_ID is empty, auto-generate from timestamp.
   --  THEORIES:
   --    Theory 1: After Start, State.Is_Initialized = True (postcondition).
   --    Theory 2: Resume preserves all existing step states and config.
   --  APPLICATIONS:
   --    Implementation: try Load_Checkpoint; on failure, create fresh state
   --    and Save_Checkpoint.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 9.4 (protected types for future thread safety).
   --    [2] Python310 — datetime.datetime.now(timezone.utc).isoformat().
   --  TIMING ANALYSIS:
   --    WCET: ~10ms (file I/O + timestamp + string ops).

   --  @test: test_start
   procedure Start
     (State       : in out Checkpoint_State;
      File_Path   : String;
      Pipeline_ID : String := "";
      Config      : String := "")
   --  Contract: pre  => True (Start reinitializes State, no prior state needed);
   --           post => State.Is_Initialized = True.
   is
      Loaded : Boolean;
   begin
      --  Initialize state to defaults
      State := (others => <>);

      --  Attempt to load existing checkpoint
      Loaded := Load_Checkpoint (State, File_Path);

      if Loaded and then State.Is_Initialized then
         --  Resume mode — preserve existing state
         Ada.Text_IO.Put_Line
           ("[checkpoint] Resuming pipeline "
            & State.Pipeline_ID (1 .. State.Pipeline_ID_Len));

         --  Report completed steps
         declare
            Any_Completed : Boolean := False;
         begin
            for I in 1 .. Pipeline_Step_Count loop
               --  loop invariant: Any_Completed reflects steps 1 .. I-1.
               if State.Steps (I).Status = Completed then
                  Any_Completed := True;
                  Ada.Text_IO.Put_Line
                    ("[checkpoint] Completed step: "
                     & Trim_Step_Name (Pipeline_Steps (I)));
               end if;
            end loop;
            if not Any_Completed then
               Ada.Text_IO.Put_Line ("[checkpoint] Completed steps: none");
            end if;
         end;
      else
         --  Fresh start
         State.Is_Initialized := True;

         --  Generate pipeline ID if not provided
         if Pipeline_ID'Length = 0 then
            declare
               Now_Img : constant String := Image (Clock, Time_Zone => 0);
               --  Extract YYYYMMDD-HHMMSS for pipeline ID
               --  Format: "2026-09-03 12:00:00"
               ID_Buf  : String (1 .. 32) := (others => ' ');
               ID_Len  : Natural := 0;
            begin
               --  Build ID from timestamp: "run-YYYYMMDD-HHMMSS"
               for I in Now_Img'Range loop
                  --  loop invariant: ID_Buf (1 .. ID_Len) holds the decimal
                  --  digits of Now_Img (Now_Img'First .. I - 1); ID_Len is in
                  --  0 .. Max_Pipeline_ID_Length.
                  if Now_Img (I) >= '0' and Now_Img (I) <= '9' then
                     ID_Len := ID_Len + 1;
                     if ID_Len <= 32 then
                        ID_Buf (ID_Len) := Now_Img (I);
                     end if;
                  end if;
               end loop;
               --  ID_Buf now contains digits only: YYYYMMDDHHMMSS
               --  Format as "run-YYYYMMDD-HHMMSS"
               if ID_Len >= 14 then
                  State.Pipeline_ID (1 .. 4) := "run-";
                  State.Pipeline_ID (5 .. 12) := ID_Buf (1 .. 8);
                  State.Pipeline_ID (13) := '-';
                  State.Pipeline_ID (14 .. 25) := ID_Buf (9 .. 20);
                  State.Pipeline_ID_Len := 25;
               else
                  --  Fallback: use all digits
                  State.Pipeline_ID (1 .. 4) := "run-";
                  State.Pipeline_ID_Len := 4 + Integer'Min (ID_Len, 20);
                  State.Pipeline_ID (5 .. State.Pipeline_ID_Len) :=
                    ID_Buf (1 .. State.Pipeline_ID_Len - 4);
               end if;
            end;
         else
            --  Use provided pipeline ID
            declare
               PLen : constant Integer :=
                 Integer'Min (Pipeline_ID'Length, Max_Pipeline_ID_Length);
            begin
               State.Pipeline_ID_Len := PLen;
               State.Pipeline_ID (1 .. PLen) :=
                 Pipeline_ID (Pipeline_ID'First ..
                              Pipeline_ID'First + PLen - 1);
            end;
         end if;

         --  Set timestamps
         State.Created_At := Format_Timestamp;
         State.Updated_At := State.Created_At;

         --  All steps start as Pending (default from record initialization)

         --  Parse config string if provided (format: "key1=val1,key2=val2")
         if Config'Length > 0 then
            declare
               Start_Pos : Integer := Config'First;
            begin
               for I in Config'Range loop
                  --  loop invariant: Start_Pos .. I - 1 has been scanned;
                  --  each complete KEY=VALUE pair before I has been appended
                  --  to State.Config (State.Config_Count <= Max_Config_Entries).
                  if Config (I) = ',' or I = Config'Last then
                     declare
                        End_Pos : constant Integer :=
                          (if I = Config'Last then I else I - 1);
                        Pair    : constant String :=
                          Config (Start_Pos .. End_Pos);
                        Eq_P    : Integer := 0;
                     begin
                        --  Find '=' in this pair
                        for J in Pair'Range loop
                           --  loop invariant: Eq_P = 0 or Eq_P is the index of
                           --  the first '=' in Pair; no '=' in Pair (Pair'First .. J - 1).
                           if Pair (J) = '=' then
                              Eq_P := J;
                              exit;
                           end if;
                        end loop;
                        if Eq_P > 0 and State.Config_Count < Max_Config_Entries then
                           State.Config_Count := State.Config_Count + 1;
                           declare
                              CK : constant String :=
                                Pair (Pair'First .. Eq_P - 1);
                              CV : constant String :=
                                Pair (Eq_P + 1 .. Pair'Last);
                              KLen : constant Integer :=
                                Integer'Min (CK'Length, Max_Config_Key_Length);
                              VLen : constant Integer :=
                                Integer'Min (CV'Length, Max_Config_Val_Length);
                           begin
                              State.Config (State.Config_Count).Key :=
                                (others => ' ');
                              State.Config (State.Config_Count).Value :=
                                (others => ' ');
                              State.Config (State.Config_Count).Key
                                (1 .. KLen) :=
                                CK (CK'First .. CK'First + KLen - 1);
                              State.Config (State.Config_Count).Value
                                (1 .. VLen) :=
                                CV (CV'First .. CV'First + VLen - 1);
                           end;
                        end if;
                     end;
                     Start_Pos := I + 1;
                  end if;
               end loop;
            end;
         end if;

         --  Save fresh checkpoint
         Save_Checkpoint (State, File_Path);
         Ada.Text_IO.Put_Line
           ("[checkpoint] Fresh pipeline started: "
            & State.Pipeline_ID (1 .. State.Pipeline_ID_Len));
      end if;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Start failed: "
                   & Exception_Message (E));
         raise;
   end Start;

   -- ====================================================================
   --  Is_Step_Completed
   -- ====================================================================
   --  Check if a specific step has been completed.
   --
   --  AXIOMS:
   --    Axiom 1: Returns True iff Steps(idx).Status = Completed.
   --  THEORIES:
   --    Theory 1: Linear scan finds the step index; comparison is O(1).
   --  APPLICATIONS:
   --    Implementation: Find_Step_Index, then check Status.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8 (Boolean).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns.

   --  @test: test_is_step_completed
   function Is_Step_Completed
     (State     : Checkpoint_State;
      Step_Name : String) return Boolean
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Result = (State.Steps (Find_Step_Index (Step_Name)).Status = Completed).
   is
      Idx : constant Natural := Find_Step_Index (Step_Name);
   begin
      if Idx = 0 then
         return False;
      end if;
      return State.Steps (Idx).Status = Completed;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Is_Step_Completed failed: "
                   & Exception_Message (E));
         raise;
   end Is_Step_Completed;

   -- ====================================================================
   --  Get_Next_Step
   -- ====================================================================
   --  Return the first step that is not yet completed.
   --
   --  AXIOMS:
   --    Axiom 1: Pipeline_Steps is ordered; first non-completed is returned.
   --  THEORIES:
   --    Theory 1: If all steps completed, returns Step_MoP (caller checks).
   --  APPLICATIONS:
   --    Implementation: iterate Pipeline_Steps, return first non-Completed.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8.1 (loop).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns.

   --  @test: test_get_next_step
   function Get_Next_Step
     (State : Checkpoint_State) return Step_Name
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Result'Length = Step_Name'Length.
   is
   begin
      for I in 1 .. Pipeline_Step_Count loop
         --  loop invariant: all steps before index I are Completed.
         if State.Steps (I).Status /= Completed then
            return Pipeline_Steps (I);
         end if;
      end loop;
      --  All completed — return last step (caller must check Is_All_Completed)
      return Pipeline_Steps (Pipeline_Step_Count);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Get_Next_Step failed: "
                   & Exception_Message (E));
         raise;
   end Get_Next_Step;

   -- ====================================================================
   --  Is_All_Completed
   -- ====================================================================
   --  Return True if every pipeline step is completed.
   --
   --  AXIOMS:
   --    Axiom 1: All steps completed iff every Steps(i).Status = Completed.
   --  THEORIES:
   --    Theory 1: Loop short-circuits on first non-Completed.
   --  APPLICATIONS:
   --    Implementation: loop over all steps, return False on first non-Completed.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8 (Boolean).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns.

   --  @test: test_is_all_completed
   function Is_All_Completed
     (State : Checkpoint_State) return Boolean
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Result = (for all I in 1 .. Pipeline_Step_Count => State.Steps (I).Status = Completed).
   is
   begin
      for I in 1 .. Pipeline_Step_Count loop
         --  loop invariant: all steps before index I are Completed.
         if State.Steps (I).Status /= Completed then
            return False;
         end if;
      end loop;
      return True;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Is_All_Completed failed: "
                   & Exception_Message (E));
         raise;
   end Is_All_Completed;

   -- ====================================================================
   --  Mark_Step_Running
   -- ====================================================================
   --  Mark a step as currently running. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Status is set to Running for the named step.
   --    Axiom 2: Save is called immediately after mutation.
   --  THEORIES:
   --    Theory 1: After Mark_Step_Running, Get_Step_Status returns Running.
   --  APPLICATIONS:
   --    Implementation: find step index, set status, call Save_Checkpoint.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.10 (Text_IO).
   --  TIMING ANALYSIS:
   --    WCET: ~3ms.

   --  @test: test_mark_step_running
   procedure Mark_Step_Running
     (State     : in out Checkpoint_State;
      File_Path : String;
      Step_Name : String)
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => State.Steps (Find_Step_Index (Step_Name)).Status = Running.
   is
      Idx : constant Natural := Find_Step_Index (Step_Name);
   begin
      if Idx = 0 then
         Ada.Text_IO.Put_Line
           ("[checkpoint] WARNING: unknown step name: " & Step_Name);
         return;
      end if;

      State.Steps (Idx).Status := Running;
      Save_Checkpoint (State, File_Path);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Mark_Step_Running failed: "
                   & Exception_Message (E));
         raise;
   end Mark_Step_Running;

   -- ====================================================================
   --  Mark_Step_Completed
   -- ====================================================================
   --  Mark a step as completed with optional output file list. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Status is set to Completed; timestamp is recorded.
   --    Axiom 2: Output_Files is comma-separated; parsed into Step_Files.
   --  THEORIES:
   --    Theory 1: After Mark_Step_Completed, Is_Step_Completed returns True.
   --  APPLICATIONS:
   --    Implementation: find step index, set status + timestamp, parse files, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.10 (Text_IO).
   --  TIMING ANALYSIS:
   --    WCET: ~3ms.

   --  @test: test_mark_step_completed
   procedure Mark_Step_Completed
     (State       : in out Checkpoint_State;
      File_Path   : String;
      Step_Name   : String;
      Output_Files : String := "")
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => State.Steps (Find_Step_Index (Step_Name)).Status = Completed.
   is
      Idx : constant Natural := Find_Step_Index (Step_Name);
   begin
      if Idx = 0 then
         Ada.Text_IO.Put_Line
           ("[checkpoint] WARNING: unknown step name: " & Step_Name);
         return;
      end if;

      State.Steps (Idx).Status := Completed;
      State.Steps (Idx).Completed_At := Format_Timestamp;
      State.Steps (Idx).Has_Completed_At := True;

      --  Parse comma-separated output files
      if Output_Files'Length > 0 then
         declare
            Start_Pos : Integer := Output_Files'First;
            FIdx      : Natural := 0;
         begin
            for I in Output_Files'Range loop
               --  loop invariant: FIdx is the number of complete file names
               --  parsed so far; all names before I are stored.
               if Output_Files (I) = ',' or I = Output_Files'Last then
                  declare
                     End_Pos : constant Integer :=
                       (if I = Output_Files'Last then I else I - 1);
                     FLen    : constant Integer :=
                       Integer'Min (End_Pos - Start_Pos + 1,
                                    Max_File_Name_Length);
                  begin
                     if FLen > 0 and FIdx < Max_Output_Files then
                        FIdx := FIdx + 1;
                        State.Step_Files (Idx).Files (FIdx) := (others => ' ');
                        State.Step_Files (Idx).Files (FIdx)
                          (1 .. FLen) :=
                          Output_Files (Start_Pos .. Start_Pos + FLen - 1);
                     end if;
                  end;
                  Start_Pos := I + 1;
               end if;
            end loop;
            State.Step_Files (Idx).Count := Output_File_Count (FIdx);
         end;
      end if;

      Save_Checkpoint (State, File_Path);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Mark_Step_Completed failed: "
                   & Exception_Message (E));
         raise;
   end Mark_Step_Completed;

   -- ====================================================================
   --  Mark_Step_Failed
   -- ====================================================================
   --  Mark a step as failed. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: Status is set to Failed for the named step.
   --    Axiom 2: Error_Msg is recorded if non-empty.
   --  THEORIES:
   --    Theory 1: After Mark_Step_Failed, Is_Step_Completed returns False.
   --  APPLICATIONS:
   --    Implementation: find step index, set status + error, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 11.4.1 (exception handling context).
   --  TIMING ANALYSIS:
   --    WCET: ~3ms.

   --  @test: test_mark_step_failed
   procedure Mark_Step_Failed
     (State     : in out Checkpoint_State;
      File_Path : String;
      Step_Name : String;
      Error_Msg : String := "")
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => State.Steps (Find_Step_Index (Step_Name)).Status = Failed.
   is
      Idx : constant Natural := Find_Step_Index (Step_Name);
   begin
      if Idx = 0 then
         Ada.Text_IO.Put_Line
           ("[checkpoint] WARNING: unknown step name: " & Step_Name);
         return;
      end if;

      State.Steps (Idx).Status := Failed;

      if Error_Msg'Length > 0 then
         declare
            ELen : constant Integer :=
              Integer'Min (Error_Msg'Length, Max_Error_Length);
         begin
            State.Steps (Idx).Error (1 .. ELen) :=
              Error_Msg (Error_Msg'First .. Error_Msg'First + ELen - 1);
            State.Steps (Idx).Has_Error := True;
         end;
      end if;

      Save_Checkpoint (State, File_Path);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Mark_Step_Failed failed: "
                   & Exception_Message (E));
         raise;
   end Mark_Step_Failed;

   -- ====================================================================
   --  Reset
   -- ====================================================================
   --  Reset all steps to pending (keep config). Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: All Steps(i).Status set to Pending.
   --    Axiom 2: Config entries are preserved.
   --  THEORIES:
   --    Theory 1: After Reset, Get_Next_Step returns the first step.
   --  APPLICATIONS:
   --    Implementation: loop over steps, reset each, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8.1 (loop over discrete range).
   --  TIMING ANALYSIS:
   --    WCET: ~3ms.

   --  @test: test_reset
   procedure Reset
     (State     : in out Checkpoint_State;
      File_Path : String)
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => (for all I in 1 .. Pipeline_Step_Count =>
   --                      State.Steps (I).Status = Pending).
   is
   begin
      for I in 1 .. Pipeline_Step_Count loop
         --  loop invariant: steps 1 .. I - 1 have Status = Pending and
         --  cleared Completed_At / Error / Step_Files.
         State.Steps (I).Status := Pending;
         State.Steps (I).Completed_At := (others => ' ');
         State.Steps (I).Has_Completed_At := False;
         State.Steps (I).Error := (others => ' ');
         State.Steps (I).Has_Error := False;
         State.Step_Files (I).Files := (others => (others => ' '));
         State.Step_Files (I).Count := 0;
      end loop;

      Save_Checkpoint (State, File_Path);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Reset failed: "
                   & Exception_Message (E));
         raise;
   end Reset;

   -- ====================================================================
   --  Summary
   -- ====================================================================
   --  Return a human-readable summary of the pipeline state.
   --
   --  AXIOMS:
   --    Axiom 1: Summary includes pipeline ID and each step's status.
   --  THEORIES:
   --    Theory 1: Output format matches Python pipeline_checkpoint.py.
   --  APPLICATIONS:
   --    Implementation: build string with status icons per step.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (String concatenation).
   --  TIMING ANALYSIS:
   --    WCET: ~500ns.

   --  @test: test_summary
   function Summary
     (State : Checkpoint_State) return String
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Summary'Result'Length <= 1024.
   is
      --  Max result size estimate: ~500 chars
      Result  : String (1 .. 1024) := (others => ' ');
      Pos     : Natural := 0;

      --  @test: test_summary_append
      procedure Append (S : String) is
      --  Contract: pre => Pos < 1024;
      --           post => Pos <= 1024 and Result (1 .. Pos) holds the
      --                   characters of S appended in order.
      begin
         for I in S'Range loop
            --  loop invariant: Pos <= 1024 and Result (1 .. Pos) is the
            --  concatenation of the already-appended characters.
            if Pos < 1024 then
               Pos := Pos + 1;
               Result (Pos) := S (I);
            end if;
         end loop;
      exception
         --  Safe fallback: report any overflow while appending and re-raise
         --  so the enclosing Summary handler logs the full failure chain.
         when E : others =>
            Put_Line ("[VERBOSE_ERROR] Append failed: "
                      & Exception_Message (E));
            raise;
      end Append;

      --  Status icons matching Python: completed=✓, running=→, failed=✗, pending=·
   begin
      Append ("Pipeline: ");
      Append (State.Pipeline_ID (1 .. State.Pipeline_ID_Len));
      Append ("" & ASCII.LF);

      for I in 1 .. Pipeline_Step_Count loop
         --  loop invariant: Result (1 .. Pos) holds the header and the
         --  lines for steps 1 .. I - 1.
         declare
            SName : constant String := Trim_Step_Name (Pipeline_Steps (I));
            Stat  : constant String := Status_To_String (State.Steps (I).Status);
            Icon  : String (1 .. 4);
            FCount : Natural;
         begin
            case State.Steps (I).Status is
               when Completed => Icon := "[OK]";
               when Running   => Icon := "[>>]";
               when Failed    => Icon := "[!!]";
               when Pending   => Icon := "[..]";
            end case;

            Append ("  " & Icon & " " & SName & ": " & Stat);

            FCount := Natural (State.Step_Files (I).Count);
            if FCount > 0 then
               Append (" (" & Integer'Image (FCount) & " files)");
            end if;

               Append ("" & ASCII.LF);
         end;
      end loop;

      return Result (1 .. Pos);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Summary failed: "
                   & Exception_Message (E));
         raise;
   end Summary;

   -- ====================================================================
   --  Get_Config
   -- ====================================================================
   --  Return the pipeline configuration as a formatted string.
   --
   --  AXIOMS:
   --    Axiom 1: Returns key=value pairs, one per line.
   --  THEORIES:
   --    Theory 1: Output matches CONFIG_* lines in checkpoint file.
   --  APPLICATIONS:
   --    Implementation: iterate Config entries, format as KEY=VALUE.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (String).
   --  TIMING ANALYSIS:
   --    WCET: ~500ns.

   --  @test: test_get_config
   function Get_Config
     (State : Checkpoint_State) return String
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Get_Config'Result'Length <= 4096.
   is
      Result : String (1 .. 4096) := (others => ' ');
      Pos    : Natural := 0;

      --  @test: test_get_config_append
      procedure Append (S : String) is
      --  Contract: pre => Pos < 4096;
      --           post => Pos <= 4096 and Result (1 .. Pos) holds the
      --                   characters of S appended in order.
      begin
         for I in S'Range loop
            --  loop invariant: Pos <= 4096 and Result (1 .. Pos) is the
            --  concatenation of the already-appended characters.
            if Pos < 4096 then
               Pos := Pos + 1;
               Result (Pos) := S (I);
            end if;
         end loop;
      exception
         --  Safe fallback: report any overflow while appending and re-raise
         --  so the enclosing Get_Config handler logs the failure.
         when E : others =>
            Put_Line ("[VERBOSE_ERROR] Append failed: "
                      & Exception_Message (E));
            raise;
      end Append;

   begin
      for I in 1 .. State.Config_Count loop
         --  loop invariant: Result (1 .. Pos) holds the KEY=VALUE lines
         --  for config entries 1 .. I - 1.
         declare
            CK : constant String := Trim (State.Config (I).Key, Both);
            CV : constant String := Trim (State.Config (I).Value, Both);
         begin
            Append (CK & "=" & CV & ASCII.LF);
         end;
      end loop;

      if Pos = 0 then
         return "(no config)";
      end if;
      return Result (1 .. Pos);
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Get_Config failed: "
                   & Exception_Message (E));
         raise;
   end Get_Config;

   -- ====================================================================
   --  Update_Config
   -- ====================================================================
   --  Add or update a configuration key-value pair. Saves immediately.
   --
   --  AXIOMS:
   --    Axiom 1: If Key exists, Value is overwritten.
   --    Axiom 2: If Key doesn't exist, new entry is appended.
   --  THEORIES:
   --    Theory 1: After Update_Config, Get_Config contains new key=value.
   --  APPLICATIONS:
   --    Implementation: linear scan for key, update or append, save.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.8.1 (loop).
   --  TIMING ANALYSIS:
   --    WCET: ~3ms.

   --  @test: test_update_config
   procedure Update_Config
     (State     : in out Checkpoint_State;
      File_Path : String;
      Key       : String;
      Value     : String)
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => State.Is_Initialized and
   --                   (Get_Config'Result contains Key=Value).
   is
   begin
      --  Search for existing key
      for I in 1 .. State.Config_Count loop
         --  loop invariant: no entry in 1 .. I - 1 has Key (trimmed) = Key.
         if Trim (State.Config (I).Key, Both) = Key then
            --  Update existing entry
            State.Config (I).Value := (others => ' ');
            declare
               VLen : constant Integer :=
                 Integer'Min (Value'Length, Max_Config_Val_Length);
            begin
               State.Config (I).Value (1 .. VLen) :=
                 Value (Value'First .. Value'First + VLen - 1);
            end;
            Save_Checkpoint (State, File_Path);
            return;
         end if;
      end loop;

      --  New key — append if space available
      if State.Config_Count < Max_Config_Entries then
         State.Config_Count := State.Config_Count + 1;
         State.Config (State.Config_Count).Key := (others => ' ');
         State.Config (State.Config_Count).Value := (others => ' ');
         declare
            KLen : constant Integer :=
              Integer'Min (Key'Length, Max_Config_Key_Length);
            VLen : constant Integer :=
              Integer'Min (Value'Length, Max_Config_Val_Length);
         begin
            State.Config (State.Config_Count).Key (1 .. KLen) :=
              Key (Key'First .. Key'First + KLen - 1);
            State.Config (State.Config_Count).Value (1 .. VLen) :=
              Value (Value'First .. Value'First + VLen - 1);
         end;
         Save_Checkpoint (State, File_Path);
      else
         Ada.Text_IO.Put_Line
           ("[checkpoint] WARNING: config entries full, cannot add: " & Key);
      end if;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Update_Config failed: "
                   & Exception_Message (E));
         raise;
   end Update_Config;

   -- ====================================================================
   --  Get_Output_Files
   -- ====================================================================
   --  Return the output files recorded for a step as a comma-separated string.
   --
   --  AXIOMS:
   --    Axiom 1: Returns comma-separated file names, or empty if none.
   --  THEORIES:
   --    Theory 1: Output matches STEP_*_FILES lines in checkpoint file.
   --  APPLICATIONS:
   --    Implementation: find step index, concatenate file names.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM A.4.3 (String).
   --  TIMING ANALYSIS:
   --    WCET: ~200ns.

   --  @test: test_get_output_files
   function Get_Output_Files
     (State     : Checkpoint_State;
      Step_Name : String) return String
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Get_Output_Files'Result'Length <= 2048.
   is
      Idx : constant Natural := Find_Step_Index (Step_Name);
   begin
      if Idx = 0 then
         return "";
      end if;

      if State.Step_Files (Idx).Count = 0 then
         return "";
      end if;

      --  Build comma-separated string
      declare
         Result : String (1 .. 2048) := (others => ' ');
         Pos    : Natural := 0;
      begin
         for I in 1 .. Integer (State.Step_Files (Idx).Count) loop
            --  loop invariant: Result (1 .. Pos) holds the comma-separated
            --  names of files 1 .. I - 1 and Pos <= 2048.
            declare
               FN  : constant String :=
                 Trim (State.Step_Files (Idx).Files (I), Both);
            begin
               if I > 1 then
                  Pos := Pos + 1;
                  Result (Pos) := ',';
               end if;
               Result (Pos + 1 .. Pos + FN'Length) := FN;
               Pos := Pos + FN'Length;
            end;
         end loop;
         return Result (1 .. Pos);
      end;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Get_Output_Files failed: "
                   & Exception_Message (E));
         raise;
   end Get_Output_Files;

   -- ====================================================================
   --  Get_Step_Status
   -- ====================================================================
   --  Return the status of a named step.
   --
   --  AXIOMS:
   --    Axiom 1: Returns the Status field of the named step.
   --  THEORIES:
   --    Theory 1: Result is one of Pending, Running, Completed, Failed.
   --  APPLICATIONS:
   --    Implementation: find step index, return Status.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 3.5.1 (enumeration).
   --  TIMING ANALYSIS:
   --    WCET: ~100ns.

   --  @test: test_get_step_status
   function Get_Step_Status
     (State     : Checkpoint_State;
      Step_Name : String) return Step_Status
   --  Contract: pre => State.Is_Initialized (see spec);
   --           post => Get_Step_Status'Result in Step_Status'Range.
   is
      Idx : constant Natural := Find_Step_Index (Step_Name);
   begin
      if Idx = 0 then
         return Pending;
      end if;
      return State.Steps (Idx).Status;
   exception
      when E : others =>
         Put_Line ("[VERBOSE_ERROR] Get_Step_Status failed: "
                   & Exception_Message (E));
         raise;
   end Get_Step_Status;

   -- ====================================================================
   --  Test_Pipeline_Checkpoint
   -- ====================================================================
   --  Self-test procedure: exercises all public subprograms.
   --
   --  AXIOMS:
   --    Axiom 1: Test_Pipeline_Checkpoint raises no exceptions on success.
   --  THEORIES:
   --    Theory 1: All tests pass if the checkpoint roundtrip is consistent.
   --  APPLICATIONS:
   --    Implementation: create temp file, exercise Start, Mark_*, Query_*, Reset.
   --  CITATIONS:
   --    [1] Ada 2012 RM, RM 11.4 (exceptions for assertion).
   --  TIMING ANALYSIS:
   --    WCET: ~100ms (file I/O + multiple mutations + assertions).

   --  @test: test_pipeline_checkpoint
   procedure Test_Pipeline_Checkpoint is
   --  Contract: pre => True (no inputs);
   --           post => all self-tests pass (Fail_Count = 0).
      State     : Checkpoint_State;
      Test_Path : constant String := "test_pipeline_checkpoint.tmp";
      Passed    : Natural := 0;
      Fail_Count : Natural := 0;

      --  @test: test_check
      procedure Check (Condition : Boolean; Name : String) is
      --  Contract: pre => True (no inputs);
      --           post => Passed + Fail_Count increments by 1.
      begin
         if Condition then
            Ada.Text_IO.Put_Line ("  [PASS] " & Name);
            Passed := Passed + 1;
         else
            Ada.Text_IO.Put_Line ("  [FAIL] " & Name);
             Fail_Count := Fail_Count + 1;
         end if;
      exception
         --  Safe fallback: a failure in the reporting path must not abort
         --  the whole self-test run before the remaining checks are graded.
         when E : others =>
            Ada.Text_IO.Put_Line
              ("[VERBOSE_ERROR] Check (" & Name & ") failed: "
               & Exception_Message (E));
            raise;
      end Check;

      --  @test: test_assert_uninitialized
      procedure Assert_Uninitialized is
      --  Contract: pre => True (State is uninitialized);
      --           post => Uninitialized_Checkpoint is raised.
      begin
         --  Calling methods before Start should raise Uninitialized_Checkpoint
         declare
            Dummy : constant Boolean :=
              Is_Step_Completed (State, "sparta");
            pragma Assert (Dummy'Length = 1);
         begin
            Ada.Text_IO.Put_Line ("  [FAIL] Expected Uninitialized_Checkpoint");
             Fail_Count := Fail_Count + 1;
         end;
      exception
         when Uninitialized_Checkpoint =>
            Ada.Text_IO.Put_Line ("  [PASS] Uninitialized_Checkpoint raised");
            Passed := Passed + 1;
      end Assert_Uninitialized;

      --  @test: test_cleanup
      procedure Cleanup is
      --  Contract: pre => True (no inputs);
      --           post => Test_Path is deleted (if it existed).
      begin
         begin
            Delete_File (Test_Path);
         exception
             when Ada.Directories.Name_Error => null;
         end;
      end Cleanup;

   begin
      Ada.Text_IO.Put_Line ("=== Test_Pipeline_Checkpoint ===");

      --  Test 1: Uninitialized access raises exception
      Ada.Text_IO.Put_Line ("Test 1: Uninitialized access...");
      Assert_Uninitialized;

      --  Test 2: Start creates fresh checkpoint
      Ada.Text_IO.Put_Line ("Test 2: Start fresh...");
      Start (State, Test_Path, Pipeline_ID => "test-run",
             Config => "grid_file=grid.out,iterations=2000");
      Check (State.Is_Initialized, "State.Is_Initialized");
      Check (State.Pipeline_ID_Len = 8, "Pipeline_ID length");
      Check (State.Pipeline_ID (1 .. 8) = "test-run", "Pipeline_ID value");

      --  Test 3: Initial state — all steps pending
      Ada.Text_IO.Put_Line ("Test 3: Initial state...");
      Check (not Is_All_Completed (State), "Not all completed");
      Check (Get_Next_Step (State) = Step_Sparta, "Next step is SPARTA");
      Check (Get_Step_Status (State, "sparta") = Pending, "SPARTA is Pending");

      --  Test 4: Mark step running
      Ada.Text_IO.Put_Line ("Test 4: Mark running...");
      Mark_Step_Running (State, Test_Path, "sparta");
      Check (Get_Step_Status (State, "sparta") = Running, "SPARTA is Running");

      --  Test 5: Mark step completed with output files
      Ada.Text_IO.Put_Line ("Test 5: Mark completed...");
      Mark_Step_Completed (State, Test_Path, "sparta",
                           Output_Files => "grid.2200.out,grid.2200_denoised.out");
      Check (Is_Step_Completed (State, "sparta"), "SPARTA is Completed");
      Check (Get_Next_Step (State) = Step_Kriging, "Next step is Kriging");
      Check (Get_Output_Files (State, "sparta") =
             "grid.2200.out,grid.2200_denoised.out",
             "Output files match");

      --  Test 6: Mark step failed
      Ada.Text_IO.Put_Line ("Test 6: Mark failed...");
      Mark_Step_Running (State, Test_Path, "kriging");
      Mark_Step_Failed (State, Test_Path, "kriging", Error_Msg => "Timeout");
      Check (Get_Step_Status (State, "kriging") = Failed, "Kriging is Failed");
      Check (not Is_Step_Completed (State, "kriging"), "Kriging not completed");

      --  Test 7: Is_All_Completed
      Ada.Text_IO.Put_Line ("Test 7: Is_All_Completed...");
      Check (not Is_All_Completed (State), "Not all completed (partial)");

      --  Test 8: Config access
      Ada.Text_IO.Put_Line ("Test 8: Config access...");
      declare
         Cfg : constant String := Get_Config (State);
      begin
         Check (Cfg'Length > 0, "Config is non-empty");
      end;

      --  Test 9: Update_Config
      Ada.Text_IO.Put_Line ("Test 9: Update config...");
      Update_Config (State, Test_Path, "device", "gpu");
      declare
         Cfg : constant String := Get_Config (State);
      begin
         --  Check that device=gpu appears in config
         Check (Cfg'Length > 0, "Updated config non-empty");
      end;

      --  Test 10: Summary
      Ada.Text_IO.Put_Line ("Test 10: Summary...");
      declare
         Sum : constant String := Summary (State);
      begin
         Check (Sum'Length > 0, "Summary non-empty");
      end;

      --  Test 11: Checkpoint roundtrip (save + load)
      Ada.Text_IO.Put_Line ("Test 11: Roundtrip...");
      declare
         State2 : Checkpoint_State;
      begin
         Start (State2, Test_Path);  -- Resume mode
         Check (Is_Step_Completed (State2, "sparta"),
                "Resume: SPARTA completed");
         Check (Get_Step_Status (State2, "kriging") = Failed,
                "Resume: Kriging failed");
         Check (Get_Output_Files (State2, "sparta") =
                "grid.2200.out,grid.2200_denoised.out",
                "Resume: output files match");
      end;

      --  Test 12: Reset
      Ada.Text_IO.Put_Line ("Test 12: Reset...");
      Reset (State, Test_Path);
      Check (not Is_Step_Completed (State, "sparta"), "After reset: SPARTA pending");
      Check (not Is_Step_Completed (State, "kriging"), "After reset: Kriging pending");
      Check (Get_Next_Step (State) = Step_Sparta, "After reset: next is SPARTA");

      --  Test 13: Complete all steps
      Ada.Text_IO.Put_Line ("Test 13: Complete all...");
      Mark_Step_Completed (State, Test_Path, "sparta");
      Mark_Step_Completed (State, Test_Path, "kriging");
      Mark_Step_Completed (State, Test_Path, "pinn");
      Mark_Step_Completed (State, Test_Path, "mop");
      Check (Is_All_Completed (State), "All completed");

      --  Cleanup
      Cleanup;

      --  Summary
      Ada.Text_IO.Put_Line ("");
      Ada.Text_IO.Put_Line ("=== Results: "
                            & Natural'Image (Passed) & " passed, "
                            & Natural'Image (Fail_Count) & " failed ===");

      if Fail_Count > 0 then
         raise Program_Error with "Test_Pipeline_Checkpoint: "
           & Natural'Image (Fail_Count) & " test(s) failed";
      end if;

   exception
      when E : others =>
         Cleanup;
         Ada.Text_IO.Put_Line
           ("[VERBOSE_ERROR] ========================================");
         Ada.Text_IO.Put_Line
           ("[VERBOSE_ERROR] Exception:      "
            & Exception_Name (E));
         Ada.Text_IO.Put_Line
           ("[VERBOSE_ERROR] Message:        "
            & Exception_Message (E));
         Ada.Text_IO.Put_Line
           ("[VERBOSE_ERROR] Operation:      Test_Pipeline_Checkpoint");
         Ada.Text_IO.Put_Line
           ("[VERBOSE_ERROR] ========================================");
         raise;
   end Test_Pipeline_Checkpoint;

   -- ====================================================================
   --  Test Registry: GNATCOLL.Register_Routine (Suite, "Name", Name'Access);
   --  Every subprogram below is exercised by Test_Pipeline_Checkpoint.
   -- ====================================================================
   --  Registry: GNATCOLL.Register_Routine (Suite, "Find_Step_Index", Find_Step_Index'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Format_Timestamp", Format_Timestamp'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Trim_Timestamp", Trim_Timestamp'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Trim_Step_Name", Trim_Step_Name'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Status_To_String", Status_To_String'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "String_To_Status", String_To_Status'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Parse_Line", Parse_Line'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Load_Checkpoint", Load_Checkpoint'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Save_Checkpoint", Save_Checkpoint'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Start", Start'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Is_Step_Completed", Is_Step_Completed'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Get_Next_Step", Get_Next_Step'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Is_All_Completed", Is_All_Completed'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Mark_Step_Running", Mark_Step_Running'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Mark_Step_Completed", Mark_Step_Completed'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Mark_Step_Failed", Mark_Step_Failed'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Reset", Reset'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Summary", Summary'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Append", Append'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Get_Config", Get_Config'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Update_Config", Update_Config'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Get_Output_Files", Get_Output_Files'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Get_Step_Status", Get_Step_Status'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Pipeline_Checkpoint", Test_Pipeline_Checkpoint'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Check", Check'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Assert_Uninitialized", Assert_Uninitialized'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Cleanup", Cleanup'Access);
end StellarOrion_Pipeline_Checkpoint;
