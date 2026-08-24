-- ═══════════════════════════════════════════════════════════════════════════
--  StellarOrion_Dual_Watchdog — dual independent watchdogs w/ cross-monitoring
--  (Tier B3, code-quality standard "DUAL WATCHDOG SYSTEM (MANDATORY)")
-- ═══════════════════════════════════════════════════════════════════════════
--  PURPOSE
--    Two independent watchdog monitors (A primary, B secondary) watch each
--    other and the supervised tasks.  No single point of failure: if A
--    fails, B recovers it and vice versa; if both fail, the system enters
--    an emergency safe state.
--
--  DESIGN NOTES
--    * SPARK_Mode On; every subprogram discharges its contract under
--      gnatprove --level=4 (verified Tier B5).
--    * TIME MODEL: heartbeats are explicit monotonic tick counts supplied
--      by the caller instead of Ada.Real_Time.Time.  This keeps every
--      operation a pure function of its inputs -> deterministic, provable,
--      unit-testable without real-time scheduling.  The concurrent tasking
--      wrapper that feeds ticks is Tier C2 scope (project.adb
--      decomposition); this package is the verified core.
--    * STATE MACHINE (per watchdog):
--        Healthy --(heartbeat overdue)--> Failed --(peer cross-check)-->
--        Recovering --(restart ok)--> Healthy
--        Healthy/Degraded/Failed/Recovering --(both failed)--> Dead
--
--  REFERENCES
--    [STD]   code-quality.md, sections "FAULT TOLERANCE & WATCHDOG RECOVERY"
--            and "DUAL WATCHDOG SYSTEM" (mandatory dual-watchdog matrix).
--    [STORE] Storey, N., "Safety-Critical Computer Systems", 1996 --
--            watchdog timers and fail-safe design.
-- ═══════════════════════════════════════════════════════════════════════════

package StellarOrion_Dual_Watchdog with SPARK_Mode => On is

   type Watchdog_ID is (Watchdog_A, Watchdog_B);
   type Health_Status is (Healthy, Degraded, Failed, Recovering, Dead);

   --  Recovery attempts allowed before a recovering watchdog is declared
   --  beyond automatic repair (standard recovery matrix: escalation path).
   Max_Recovery_Attempts : constant := 3;

   --  Default heartbeat budget in ticks before a watchdog is judged stale.
   --  Callers override via Initialize for slower/fast supervision cadence.
   Default_Timeout : constant := 10;

   subtype Tick_Type is Natural;
   --  Monotonic logical time.  AXIOM (W1): callers pass non-decreasing Now
   --  values across calls on the same state; every subprogram tolerates
   --  equal or smaller values gracefully (no subtraction can go negative:
   --  all age computations are guarded by Now >= Last_Heartbeat checks,
   --  Murphy's Law).

   --  Audit counters are bounded and saturating.  B5 gate lesson: an
   --  unbounded Natural counter incremented per failure/recovery has no
   --  provable overflow ceiling, because nothing bounds how often Evaluate
   --  or Cross_Check may run.  Saturation at Max_Audit_Count discharges
   --  every overflow VC trivially while losing no safety property: the
   --  counters are audit evidence, not control flow.
   Max_Audit_Count : constant := 1_000_000;

   subtype Audit_Count_Type is Natural range 0 .. Max_Audit_Count;

   -- ---------------------------------------------------------------------
   --  State (visible by design: tests assert on it directly)
   -- ---------------------------------------------------------------------

   type Watchdog_State is record
      Last_Heartbeat    : Tick_Type       := 0;
      Timeout           : Natural         := Default_Timeout;
      Status            : Health_Status   := Healthy;
      Failure_Count     : Audit_Count_Type := 0;
      Recovery_Attempts : Audit_Count_Type := 0;
   end record;

   type System_State is record
      A : Watchdog_State;
      B : Watchdog_State;
      Emergency_Latched : Boolean := False;
      --  True once Emergency_Safe_State has run; latching makes the safe
      --  state sticky (fail-safe: cannot be silently un-latched).
   end record;

   -- ---------------------------------------------------------------------
   --  Lifecycle
   -- ---------------------------------------------------------------------

   --  Bring both watchdogs up Healthy with the given heartbeat timeout.
   procedure Initialize
     (S : out System_State; Timeout_Ticks : Natural := Default_Timeout)
     with Post => S.A.Status = Healthy
                  and then S.B.Status = Healthy
                  and then not S.Emergency_Latched;

   --  Supervised component reports liveness to its watchdog.
   --  Only a live watchdog accepts heartbeats: Failed/Dead monitors stay
   --  Failed until cross-recovery repairs them (no silent resurrection).
   procedure Update_Heartbeat
     (S   : in out System_State;
      W   : Watchdog_ID;
      Now : Tick_Type)
     with Pre  => not S.Emergency_Latched,
          Post => (if W = Watchdog_A
                     and then S.A.Status'Old in Healthy | Degraded
                   then S.A.Status = Healthy
                          and then S.A.Last_Heartbeat = Now)
                  and then
                  (if W = Watchdog_B
                     and then S.B.Status'Old in Healthy | Degraded
                   then S.B.Status = Healthy
                          and then S.B.Last_Heartbeat = Now);

   -- ---------------------------------------------------------------------
   --  Monitoring
   -- ---------------------------------------------------------------------

   --  Re-evaluate both watchdogs against logical time Now.  A watchdog
   --  whose heartbeat age exceeds its timeout degrades first (one grace
   --  evaluation) then fails; failure counters increment monotonically.
   procedure Evaluate
     (S   : in out System_State;
      Now : Tick_Type)
     with Post => S.A.Failure_Count >= S.A.Failure_Count'Old
                  and then S.B.Failure_Count >= S.B.Failure_Count'Old;

   --  Cross-monitoring (the "no single point of failure" rule):
   --  a live watchdog starts recovery of its Failed peer.
   procedure Cross_Check
     (S : in out System_State)
     with Post => (if S.B.Status'Old = Failed
                     and then S.A.Status'Old in Healthy | Degraded
                   then S.B.Status = Recovering);

   --  One step of the restart sequence for a Recovering watchdog.
   --  Success model: each call completes the restart and returns the
   --  watchdog to Healthy with its heartbeat refreshed to Now (documented
   --  simplification; retry counting escalates via Max_Recovery_Attempts
   --  in the C2 tasking wrapper if restarts themselves fail).
   procedure Advance_Recovery
     (S   : in out System_State;
      W   : Watchdog_ID;
      Now : Tick_Type)
     with Pre  => not S.Emergency_Latched,
          Post => (if W = Watchdog_A
                     and then S.A.Status'Old = Recovering
                   then S.A.Status = Healthy
                          and then S.A.Last_Heartbeat = Now)
                  and then
                  (if W = Watchdog_B
                     and then S.B.Status'Old = Recovering
                   then S.B.Status = Healthy
                          and then S.B.Last_Heartbeat = Now);

   --  Both watchdogs failed: enter the emergency safe state (latched).
   --  Standard recovery matrix row "Both fail -> Emergency shutdown".
   procedure Emergency_Safe_State
     (S : in out System_State)
     with Pre  => S.A.Status = Failed and then S.B.Status = Failed,
          Post => S.A.Status = Dead
                  and then S.B.Status = Dead
                  and then S.Emergency_Latched;

   --  Predicate: system requires the emergency path right now.
   function Needs_Emergency (S : System_State) return Boolean
     with Post => Needs_Emergency'Result =
                    (S.A.Status = Failed and then S.B.Status = Failed);

end StellarOrion_Dual_Watchdog;
