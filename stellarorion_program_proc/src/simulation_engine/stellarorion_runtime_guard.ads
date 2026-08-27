--  StellarOrion_HypersonicEdition — Runtime Guard Package
--  Ada 2012 / SPARK 2014
--  SPARK_Mode => Off : performs file I/O and subprocess dispatching.
--
--  Decomposition Stage 2 (docs/PROJECT_DECOMPOSITION_PLAN.md):
--  runtime environment guards extracted verbatim from
--  stellarorion_project.adb so that all GNAT.OS_Lib subprocess
--  dispatch and lock-file side effects live in one place.
--
--  Contents:
--    Get_Lock_File_Path            - path of the single-instance lock file
--    Check_And_Acquire_Lock        - acquire lock, breaking stale locks
--    Release_Lock                  - remove the lock file if present
--    Detect_Nvidia_GPU             - probe nvidia-smi on PATH
--    Ensure_Docker_Running         - pre-flight Docker/Colima daemon check
--    Check_Amaryllis_Idle_Automode - create idle-resume hook when present
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Runtime_Guard is

   pragma SPARK_Mode (Off);
   --  extern: file I/O + GNAT.OS_Lib subprocess dispatch; outside SPARK subset

   --  Path of the single-instance lock file ("main.lock").
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Get_Lock_File_Path return String;

   --  Acquire the lock file; a pre-existing (stale) lock is broken.
   --  Returns True on success, False if the stale lock cannot be removed.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Check_And_Acquire_Lock return Boolean;

   --  Remove the lock file if present (idempotent).
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Release_Lock;

   --  True if nvidia-smi is available on PATH (NVIDIA GPU present).
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Detect_Nvidia_GPU return Boolean;

   --  Detect the number of performance (P) cores on Apple Silicon Macs.
   --  Uses: sysctl -n hw.perflevel0.physicalcpu (macOS P-core count)
   --  Falls back to: sysctl -n hw.ncpu (total cores) on non-Macs or
   --  if the perflevel query fails.  Returns 4 as last resort.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Detect_P_Cores return Positive;

   --  Pre-flight check: docker binary on PATH and daemon responding;
   --  attempts 'colima start' as fallback. True if SPARTA can run.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Ensure_Docker_Running return Boolean;

   --  If /usr/local/AmaryllisIdleAutomode exists, create the shell
   --  idle-resume script that re-launches validation after 600 s idle.
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Check_Amaryllis_Idle_Automode;

   procedure Test_Get_Lock_File_Path;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Check_And_Acquire_Lock;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Release_Lock;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Detect_Nvidia_GPU;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Ensure_Docker_Running;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Check_Amaryllis_Idle_Automode;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Check_Amaryllis_Idle_Automode", Test_Check_Amaryllis_Idle_Automode'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Check_And_Acquire_Lock", Test_Check_And_Acquire_Lock'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Detect_Nvidia_GPU", Test_Detect_Nvidia_GPU'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Ensure_Docker_Running", Test_Ensure_Docker_Running'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Get_Lock_File_Path", Test_Get_Lock_File_Path'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Release_Lock", Test_Release_Lock'Access);
end StellarOrion_Runtime_Guard;
