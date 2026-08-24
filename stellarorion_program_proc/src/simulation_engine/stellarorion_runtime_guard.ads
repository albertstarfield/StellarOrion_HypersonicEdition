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
   function Get_Lock_File_Path return String;

   --  Acquire the lock file; a pre-existing (stale) lock is broken.
   --  Returns True on success, False if the stale lock cannot be removed.
   function Check_And_Acquire_Lock return Boolean;

   --  Remove the lock file if present (idempotent).
   procedure Release_Lock;

   --  True if nvidia-smi is available on PATH (NVIDIA GPU present).
   function Detect_Nvidia_GPU return Boolean;

   --  Pre-flight check: docker binary on PATH and daemon responding;
   --  attempts 'colima start' as fallback. True if SPARTA can run.
   function Ensure_Docker_Running return Boolean;

   --  If /usr/local/AmaryllisIdleAutomode exists, create the shell
   --  idle-resume script that re-launches validation after 600 s idle.
   procedure Check_Amaryllis_Idle_Automode;

end StellarOrion_Runtime_Guard;
