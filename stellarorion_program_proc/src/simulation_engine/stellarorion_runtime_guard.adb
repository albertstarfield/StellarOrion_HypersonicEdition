--  StellarOrion_HypersonicEdition — Runtime Guard Package (Body)
--  Ada 2012 / SPARK 2014
--  SPARK_Mode => Off : performs file I/O and subprocess dispatching.
--
--  Decomposition Stage 2: subprograms moved VERBATIM from
--  stellarorion_project.adb (Lock File Helpers, GPU Auto-Detection,
--  Pre-flight Docker Check, AmaryllisIdleAutomode Detection sections).
--  Behavior is bit-for-bit identical; see docs/PROJECT_DECOMPOSITION_PLAN.md.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with Ada.Text_IO;     use Ada.Text_IO;
with Ada.Directories; use Ada.Directories;
with GNAT.OS_Lib;     use GNAT.OS_Lib;

package body StellarOrion_Runtime_Guard is

   pragma SPARK_Mode (Off);
   --  extern: file I/O + GNAT.OS_Lib subprocess dispatch; outside SPARK subset

   -- ==================================================================
   --  Lock File Helpers  (matches Python check_and_acquire_lock)
   -- ==================================================================

   function Get_Lock_File_Path return String is
   begin
      return "main.lock";
   end Get_Lock_File_Path;

   --  Acquire main.lock for this process: break any existing (stale) lock
   --  file first, then create a fresh one.  Returns False when the stale
   --  lock cannot be removed.
   function Check_And_Acquire_Lock return Boolean is
      Lock_File : File_Type;
      Lock_Path : constant String := Get_Lock_File_Path;
      Success   : Boolean;
   begin
      if Exists (Lock_Path) then
         Put_Line ("[LOCK] Lock file exists: " & Lock_Path);
         Put_Line ("[LOCK] Attempting to break stale lock ...");
         Delete_File (Lock_Path, Success);
         if not Success then
            Put_Line ("[LOCK] WARNING: Could not remove stale lock file.");
            return False;
         end if;
      end if;

      --  Create lock file with timestamp marker
      Create (Lock_File, Out_File, Lock_Path);
      Put_Line (Lock_File, "locked_by_stellarorion_ada");
      Close (Lock_File);
      Put_Line ("[LOCK] Lock acquired: " & Lock_Path);
      return True;
   end Check_And_Acquire_Lock;

   --  Release main.lock by deleting it; a no-op when the lock is absent
   --  or the delete fails.
   procedure Release_Lock is
      Lock_Path : constant String := Get_Lock_File_Path;
      Success   : Boolean;
   begin
      if Exists (Lock_Path) then
         Delete_File (Lock_Path, Success);
         if Success then
            Put_Line ("[LOCK] Lock released: " & Lock_Path);
         end if;
      end if;
   end Release_Lock;

   -- ==================================================================
   --  GPU Auto-Detection  (matches Python has_nvidia_gpu)
   -- ==================================================================

   function Detect_Nvidia_GPU return Boolean is
      Success    : Boolean;
      --  Constant: zero-length argv for PATH probe (no arguments needed)
      Empty_Args : constant Argument_List (1 .. 0) := (others => null);
   begin
      Put_Line ("[GPU] Detecting NVIDIA GPU via nvidia-smi ...");
      Spawn ("nvidia-smi", Empty_Args, Success);
      if Success then
         Put_Line ("[GPU] NVIDIA GPU DETECTED.");
         return True;
      else
         Put_Line ("[GPU] No NVIDIA GPU detected (nvidia-smi not available).");
         return False;
      end if;
   exception
      when others =>
         Put_Line ("[GPU] GPU detection failed (exception).");
         return False;
   end Detect_Nvidia_GPU;

   -- ==================================================================
   --  Pre-flight Docker Check  (matches Python ensure_docker_colima)
   -- ==================================================================

   function Ensure_Docker_Running return Boolean is
      Success    : Boolean;
      --  Constant: zero-length argv for PATH probe (no arguments needed)
      Empty_Args : constant Argument_List (1 .. 0) := (others => null);
   begin
      Put_Line ("[DOCKER] Pre-flight Docker check ...");
      Spawn ("docker", Empty_Args, Success);
      if not Success then
         Put_Line ("[DOCKER] WARNING: Docker not available on PATH.");
         Put_Line ("[DOCKER] SPARTA simulation requires Docker.");
         return False;
      end if;

      --  Try 'docker info' to verify daemon is running
      Spawn ("docker", (1 => new String'("info")), Success);
      if Success then
         Put_Line ("[DOCKER] Docker daemon is running.");
         return True;
      end if;

      --  Docker binary exists but daemon not running; try colima
      Put_Line ("[DOCKER] Docker daemon not responding. Trying colima ...");
      Spawn ("colima", (1 => new String'("start")), Success);
      if Success then
         Put_Line ("[DOCKER] Colima started successfully.");
         return True;
      end if;

      Put_Line ("[DOCKER] WARNING: Could not start Docker/Colima.");
      Put_Line ("[DOCKER] SPARTA simulation will not be available.");
      return False;
   exception
      when others =>
         Put_Line ("[DOCKER] Docker check failed (exception).");
         return False;
   end Ensure_Docker_Running;

   -- ==================================================================
   --  AmaryllisIdleAutomode Detection  (matches Python headless idle logic)
   -- ==================================================================

   procedure Check_Amaryllis_Idle_Automode is
      Idle_Dir     : constant String := "/usr/local/AmaryllisIdleAutomode";
      Chmod_Success : Boolean;
   begin
      if not Exists (Idle_Dir) then
         return;
      end if;

      Put_Line ("[IDLE] AmaryllisIdleAutomode detected at " & Idle_Dir);
      Put_Line ("[IDLE] Creating idle-resume script ...");

      declare
         Script_Name : constant String :=
           "resumeDSMCResearch_ada_executeMeAtIdle.sh";
         Script_File : File_Type;
      begin
         Create (Script_File, Out_File, Script_Name);
         Put_Line (Script_File, "#!/bin/bash");
         Put_Line (Script_File, "# Auto-generated by StellarOrion Ada");
         Put_Line (Script_File, "# Runs after 600s idle period");
         Put_Line (Script_File, "sleep 600");
         Put_Line (Script_File, "cd " & Current_Directory);
         Put_Line (Script_File, "./bin/stellarorion_project --headless --validate");
         Close (Script_File);

          --  Make executable (chmod 0o755)
          GNAT.OS_Lib.Spawn
            ("chmod",
             (new String'("755"), new String'(Script_Name)),
             Chmod_Success);
         Put_Line ("[IDLE] Resume script: " & Script_Name);
      end;
   exception
      when others =>
         Put_Line ("[IDLE] Could not create idle-resume script.");
   end Check_Amaryllis_Idle_Automode;

end StellarOrion_Runtime_Guard;
