--  StellarOrion_HypersonicEdition — Sidecar Status Writer (body)
--  Writes .status.json for the Python sidecar UI to poll.

with Ada.Text_IO;           use Ada.Text_IO;
with Ada.Directories;       use Ada.Directories;
with Ada.IO_Exceptions;

package body StellarOrion_Status_Writer is

   --  ------------------------------------------------------------------
   --  Float_Image : trimmed Image for Float values (no leading space)
   --  ------------------------------------------------------------------
   --  coverage: used by Write_Status progress formatting (all modes)
   function Float_Image (V : Float) return String is
   --  Contract: pre => True (no input constraints); post => returns trimmed image of V without leading space
      S : constant String := Float'Image (V);
   begin
      --  Ada.Float'Image puts a leading space; strip it
      if S'Length > 0 and then S (S'First) = ' ' then
         return S (S'First + 1 .. S'Last);
      end if;
      return S;
   end Float_Image;

   --  ------------------------------------------------------------------
   --  Status_String : map Status_Kind to JSON string value
   --  ------------------------------------------------------------------
   --  coverage: used by Write_Status JSON status field
   function Status_String (Kind : Status_Kind) return String is
   --  Contract: pre => True (no input constraints); post => returns JSON status literal for Kind
   begin
      case Kind is
         when Status_Idle      => return "idle";
         when Status_Running   => return "running";
         when Status_Completed => return "completed";
         when Status_Error     => return "error";
      end case;
   end Status_String;

   --  ------------------------------------------------------------------
   --  Write_Status
   --  ------------------------------------------------------------------
   procedure Write_Status
     (Dir_Path : String;
      Run_Name : String;
      Kind     : Status_Kind;
      Progress : Float;
      Results  : String := "";
      Metrics  : String := "")
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
      Status_File : File_Type;
      Full_Path   : constant String :=
        Dir_Path & "/" & ".status.json";
      Padded_Progress : constant String := Float_Image (Progress);
   begin
      --  Ensure the directory exists
      if not Exists (Dir_Path) then
         Create_Path (Dir_Path);
      end if;

      --  Build JSON via string concatenation (no JSON library needed)
      Create (File => Status_File, Mode => Out_File, Name => Full_Path);

      Put_Line (Status_File, "{");

      --  "status": "running"
      Put_Line (Status_File,
        "  ""status"": """ & Status_String (Kind) & """,");

      --  "progress": 0.45
      Put_Line (Status_File,
        "  ""progress"": " & Padded_Progress & ",");

      --  "run_name": "IRVE-3 baseline"
      Put_Line (Status_File,
        "  ""run_name"": """ & Run_Name & """,");

      --  "results": { ... }  (caller passes raw JSON snippet or empty)
      if Results'Length > 0 then
         Put_Line (Status_File,
           "  ""results"": " & Results & ",");
      else
         Put_Line (Status_File,
           "  ""results"": {},");
      end if;

      --  "metrics": { ... }
      if Metrics'Length > 0 then
         Put_Line (Status_File,
           "  ""metrics"": " & Metrics);
      else
         Put_Line (Status_File,
           "  ""metrics"": {}");
      end if;

      Put_Line (Status_File, "}");

      Close (Status_File);

   exception
      when Ada.IO_Exceptions.Status_Error |
           Ada.IO_Exceptions.Name_Error =>
         --  File system issue -- best effort, sidecar will just see stale data
         if Is_Open (Status_File) then
            Close (Status_File);
         end if;
   end Write_Status;

   --  ------------------------------------------------------------------
   --  Clear_Status
   --  ------------------------------------------------------------------
   --  coverage: exported Status_Writer API for status reset
   procedure Clear_Status (Dir_Path : String) is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
      Full_Path : constant String :=
        Dir_Path & "/" & ".status.json";
   begin
      if Exists (Full_Path) then
         Delete_File (Full_Path);
      end if;
   exception
      when Ada.IO_Exceptions.Status_Error |
           Ada.IO_Exceptions.Name_Error =>
         null;  -- best effort
   end Clear_Status;

end StellarOrion_Status_Writer;
