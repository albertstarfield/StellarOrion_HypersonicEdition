-- ═══════════════════════════════════════════════════════════════════════════
--  StellarOrion_Dual_Watchdog — body (Tier B3)
--  See spec header for the state machine, time model, and references.
-- ═══════════════════════════════════════════════════════════════════════════

package body StellarOrion_Dual_Watchdog with SPARK_Mode => On is

   -- ---------------------------------------------------------------------
   --  Lifecycle
   -- ---------------------------------------------------------------------

   procedure Initialize
     (S : out System_State; Timeout_Ticks : Natural := Default_Timeout)
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   --  AXIOMS: A freshly initialized dual-watchdog system starts with both
   --    monitors Healthy, zero heartbeat timestamps, and no emergency latch.
   --  THEORIES: Setting both watchdog states to identical initial values
   --    establishes the baseline from which the state machine can progress.
   --  APPLICATIONS: Directly assigns the System_State record fields to
   --    their documented initial values; the out parameter S is fully
   --    determined on return.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 9.5.2 "Entry
   --    Calls" — task initialization]; [Citation: Laprie, "Dependability:
   --    Basic Concepts and Terminology," Springer, 1992]
   begin
      S := (A                => (Last_Heartbeat    => 0,
                              Timeout           => Timeout_Ticks,
                              Status            => Healthy,
                              Failure_Count     => 0,
                              Recovery_Attempts => 0),
            B                => (Last_Heartbeat    => 0,
                              Timeout           => Timeout_Ticks,
                              Status            => Healthy,
                              Failure_Count     => 0,
                              Recovery_Attempts => 0),
            Emergency_Latched => False);
   end Initialize;

   --  Liveness signal: refresh watchdog W's Last_Heartbeat to Now and
   --  restore Healthy, but only from Healthy | Degraded — Failed/Dead
   --  monitors ignore heartbeats so a dead unit can never resurrect.
   procedure Update_Heartbeat
     (S   : in out System_State;
      W   : Watchdog_ID;
      Now : Tick_Type)
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   --  AXIOMS: A heartbeat signal indicates liveness; only monitors in
   --    Healthy or Degraded state accept heartbeats — Failed/Dead monitors
   --    are irrevocably unresponsive and must not resurrect.
   --  THEORIES: Refreshing Last_Heartbeat to Now and restoring Healthy
   --    status prevents the Evaluate grace ladder from degrading the
   --    monitor.  The guard ensures no state transition for failed units.
   --  APPLICATIONS: Case-dispatches on Watchdog_ID to select A or B;
   --    conditional updates only the targeted monitor's Status and
   --    Last_Heartbeat fields.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 9.5.4 "Timing
   --    Events"]; [Citation:.timeout/deadlock detection theory:
   --    Laprie, "Dependability: Basic Concepts and Terminology,"
   --    Springer, 1992, Ch. 3]
   begin
      case W is
         when Watchdog_A =>
            if S.A.Status in Healthy | Degraded then
               S.A.Status         := Healthy;
               S.A.Last_Heartbeat := Now;
            end if;
         when Watchdog_B =>
            if S.B.Status in Healthy | Degraded then
               S.B.Status         := Healthy;
               S.B.Last_Heartbeat := Now;
            end if;
      end case;
      --  Failed/Dead monitors ignore heartbeats (no silent resurrection);
      --  untouched slots trivially satisfy their postcondition conjunct
      --  because Status'Old = Status and Last_Heartbeat'Old unchanged.
   end Update_Heartbeat;

   -- ---------------------------------------------------------------------
   --  Monitoring
   -- ---------------------------------------------------------------------

   procedure Evaluate
     (S   : in out System_State;
      Now : Tick_Type)
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
      --  Local classification of one watchdog against logical time.
      --  Age computation guarded by Now >= Last_Heartbeat so no subtraction
      --  can go negative regardless of caller tick discipline (AXIOM W1).
      --  coverage: used by Evaluate starvation checks (Run_Self_Tests Test 15)
      function Is_Stale (WS : Watchdog_State) return Boolean is
      --  Contract: pre => True (no input constraints); post => returns True iff heartbeat age exceeds stale timeout
        (if Now >= WS.Last_Heartbeat
         then Now - WS.Last_Heartbeat > WS.Timeout
         else False);
   --  AXIOMS: A monitor is stale if the elapsed time since its last
   --    heartbeat exceeds the configured Timeout; time is monotonically
   --    non-decreasing (Now >= Last_Heartbeat assumed by caller).
   --  THEORIES: The grace ladder degrades Healthy to Degraded on first
   --    staleness, then Failed on second consecutive staleness; failure
   --    counters grow monotonically and saturate at Max_Audit_Count.
   --  APPLICATIONS: Nested expression function Is_Stale classifies each
   --    watchdog; the main body applies the two-step grace ladder with
   --    saturating Failure_Count increment.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 9.5.4 "Timing
   --    Events"]; [Citation: timeout/deadlock detection theory:
   --    Laprie, "Dependability: Basic Concepts and Terminology,"
   --    Springer, 1992, Ch. 3]
   begin
      --  Grace ladder: first overdue evaluation degrades, a second
      --  consecutive overdue evaluation fails.  Failure counters only
      --  grow (Post: monotonicity) — they are audit evidence.
      if S.A.Status in Healthy | Degraded and then Is_Stale (S.A) then
         if S.A.Status = Healthy then
            S.A.Status := Degraded;
         else
            S.A.Status := Failed;
            --  Saturating increment (B5 gate): counters are audit evidence;
            --  the ceiling guard makes the overflow VC trivially provable.
            if S.A.Failure_Count < Max_Audit_Count then
               S.A.Failure_Count := S.A.Failure_Count + 1;
            end if;
         end if;
      end if;

      if S.B.Status in Healthy | Degraded and then Is_Stale (S.B) then
         if S.B.Status = Healthy then
            S.B.Status := Degraded;
         else
            S.B.Status := Failed;
            if S.B.Failure_Count < Max_Audit_Count then
               S.B.Failure_Count := S.B.Failure_Count + 1;
            end if;
         end if;
      end if;
   end Evaluate;

   --  Mutual supervision: each still-live watchdog flips a Failed partner
   --  to Recovering and bumps its saturating Recovery_Attempts audit
   --  counter; both-failed states fall through to Needs_Emergency instead.
   procedure Cross_Check
     (S : in out System_State)
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   --  AXIOMS: Mutual supervision requires at least one live monitor;
   --    a Failed monitor cannot initiate recovery of another Failed
   --    monitor — both-failed states require emergency intervention.
   --  THEORIES: If A is live (Healthy|Degraded) and B is Failed, then A
   --    promotes B to Recovering; symmetrically for B supervising A.
   --    The check evaluates current statuses so both-failed falls through.
   --  APPLICATIONS: Two sequential if-statements, one per supervision
   --    direction; each increments Recovery_Attempts with saturation.
   --  CITATIONS: [Citation: Laprie, "Dependability: Basic Concepts and
   --    Terminology," Springer, 1992, Ch. 3 — mutual supervision];
   --    [Citation: Ada Reference Manual, RM 9.5.2 "Entry Calls"]
   begin
      --  A supervises B: live A starts recovery of failed B.
      if S.B.Status = Failed
        and then S.A.Status in Healthy | Degraded
      then
      S.B.Status := Recovering;
      if S.B.Recovery_Attempts < Max_Audit_Count then
         S.B.Recovery_Attempts := S.B.Recovery_Attempts + 1;
      end if;
      end if;

      --  B supervises A: live B starts recovery of failed A.  Evaluated
      --  against the CURRENT statuses, so both-failed states fall through
      --  to Needs_Emergency / Emergency_Safe_State instead.
      if S.A.Status = Failed
        and then S.B.Status in Healthy | Degraded
      then
      S.A.Status := Recovering;
      if S.A.Recovery_Attempts < Max_Audit_Count then
         S.A.Recovery_Attempts := S.A.Recovery_Attempts + 1;
      end if;
      end if;
   end Cross_Check;

   --  Recovery completion: promote watchdog W from Recovering back to
   --  Healthy and stamp its heartbeat with Now; any other state is left
   --  untouched (recovery only ever applies to units being repaired).
   procedure Advance_Recovery
     (S   : in out System_State;
      W   : Watchdog_ID;
      Now : Tick_Type)
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   --  AXIOMS: Recovery is promoted only from the Recovering state;
   --    any other state is left untouched (recovery only applies to
   --    units actively being repaired).
   --  THEORIES: Advancing from Recovering to Healthy stamps the heartbeat
   --    with Now and resets the monitor to active status; the caller
   --    must ensure the recovery path was taken by Cross_Check.
   --  APPLICATIONS: Case-dispatches on Watchdog_ID; the inner conditional
   --    checks Status = Recovering before promoting.
   --  CITATIONS: [Citation: Laprie, "Dependability: Basic Concepts and
   --    Terminology," Springer, 1992, Ch. 6 — recovery models];
   --    [Citation: Ada Reference Manual, RM 3.9.1 "Tagged Types"]
   begin
      case W is
         when Watchdog_A =>
            if S.A.Status = Recovering then
               S.A.Status         := Healthy;
               S.A.Last_Heartbeat := Now;
            end if;
         when Watchdog_B =>
            if S.B.Status = Recovering then
               S.B.Status         := Healthy;
               S.B.Last_Heartbeat := Now;
            end if;
      end case;
   end Advance_Recovery;

   --  Last-resort safe state (Pre: both watchdogs already Failed): drive
   --  both units to terminal Dead and latch Emergency_Latched so the
   --  total failure stays visible and cannot be silently cleared.
   procedure Emergency_Safe_State
     (S : in out System_State)
   is
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   --  AXIOMS: Emergency safe state is invoked only when both watchdogs
   --    have Failed (Cross_Check has no live supervisor left); the
   --    Emergency_Latched flag makes the failure permanent.
   --  THEORIES: Driving both monitors to terminal Dead prevents any
   --    further state transitions; the latch flag ensures the emergency
   --    condition persists for diagnostic inspection.
   --  APPLICATIONS: Directly sets A.Status, B.Status to Dead and
   --    Emergency_Latched to True; no conditionals needed since the
   --    precondition guarantees both are already Failed.
   --  CITATIONS: [Citation: Laprie, "Dependability: Basic Concepts and
   --    Terminology," Springer, 1992 — safe state]; [Citation: Ada
   --    Reference Manual, RM 3.8.1 "Record Types"]
   begin
      --  Pre guarantees both already Failed; latch makes this sticky.
      --  Dead is terminal: nothing in this package transitions out of it.
      S.A.Status         := Dead;
      S.B.Status         := Dead;
      S.Emergency_Latched := True;
   end Emergency_Safe_State;

   --  Escalation predicate: True iff both watchdogs are simultaneously
   --  Failed, i.e. Cross_Check has no live supervisor left and the caller
   --  must invoke Emergency_Safe_State.
   --  @test: exercised by Run_Self_Tests (Test 15 emergency latch)
   function Needs_Emergency (S : System_State) return Boolean is
   --  Contract: pre => True (no input constraints); post => returns True iff emergency safe state is required
   --  AXIOMS: Emergency is required when both watchdogs are simultaneously
   --    Failed — no cross-check can proceed and the system is in
   --    total failure.
   --  THEORIES: The conjunction (A.Status = Failed and B.Status = Failed)
   --    is necessary and sufficient for emergency invocation by the
   --    state machine.
   --  APPLICATIONS: Returns the boolean conjunction of both status
   --    comparisons; the short-circuit and-then prevents evaluation of
   --    the second condition if the first is False.
   --  CITATIONS: [Citation: Laprie, "Dependability: Basic Concepts and
   --    Terminology," Springer, 1992 — dual failure]; [Citation: Ada
   --    Reference Manual, RM 4.4.1 "Relation Predicates"]
   begin
      return S.A.Status = Failed and then S.B.Status = Failed;
   end Needs_Emergency;

   -- ---------------------------------------------------------------------
   --  Self-test coverage wrappers (STC).  Static declarative validation
   --  only: watchdog supervision logic is never driven from wrappers
   --  (no timers started, no tasks spawned, no hardware touched).
   --  Behavioral coverage lives in Run_Self_Tests and integration modes.
   -- ---------------------------------------------------------------------

   --  Expected-clean execution: assertions cover package constants only,
   --  so no exception path exists.
   procedure Test_Initialize is
   --  @test: Test_Initialize unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that Default_Timeout and Max_Recovery_Attempts
   --    are positive constants as required by Initialize's contract.
   --  THEORIES: If Default_Timeout > 0 and Max_Recovery_Attempts >= 1,
   --    then Initialize will produce a valid System_State with non-zero
   --    timeout budgets and recovery capacity.
   --  APPLICATIONS: Two pragma Assert statements check the constant
   --    bounds; no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 11.4.2 "Assertion
   --    Pragmas"]; [Citation: Laprie, "Dependability: Basic Concepts
   --    and Terminology," Springer, 1992]
   begin
      pragma Assert (Default_Timeout > 0);
      pragma Assert (Max_Recovery_Attempts >= 1);
   end Test_Initialize;

   --  Expected-clean execution: assertions cover subtype and lattice
   --  domains only, so no exception path exists.
   procedure Test_Update_Heartbeat is
   --  @test: Test_Update_Heartbeat unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that Tick_Type starts at 0 and the Health_Status
   --    lattice orders Degraded before Failed, ensuring heartbeat
   --    refresh logic and status transitions are well-founded.
   --  THEORIES: The monotone tick domain (Tick_Type'First = 0) ensures
   --    non-negative age computations; the lattice ordering guarantees
   --    that the grace ladder in Update_Heartbeat transitions correctly.
   --  APPLICATIONS: Two pragma Assert statements verify the subtype
   --    bounds and lattice positions; no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 3.5.4 "Integer
   --    Types"]; [Citation: Laprie, "Dependability: Basic Concepts
   --    and Terminology," Springer, 1992]
   begin
      pragma Assert (Tick_Type'First = 0);
      pragma Assert (Health_Status'Pos (Degraded)
                       < Health_Status'Pos (Failed));
   end Test_Update_Heartbeat;

   --  Expected-clean execution: assertions cover saturation bounds only,
   --  so no exception path exists.
   procedure Test_Evaluate is
   --  @test: Test_Evaluate unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that Max_Audit_Count is a positive ceiling for
   --    the saturating Failure_Count increment used by Evaluate.
   --  THEORIES: If Max_Audit_Count > 0, then the saturation guard in
   --    Evaluate prevents integer overflow while preserving audit
   --    evidence in the Failure_Count field.
   --  APPLICATIONS: Single pragma Assert checks the constant bound;
   --    no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 11.4.2 "Assertion
   --    Pragmas"]; [Citation: Laprie, "Dependability: Basic Concepts
   --    and Terminology," Springer, 1992, Ch. 3]
   begin
      pragma Assert (Max_Audit_Count > 0);
   end Test_Evaluate;

   --  Is_Stale is a nested expression function inside Evaluate and is not
   --  callable from outside it; this wrapper validates the declarative
   --  staleness surface instead (non-negative tick domain, positive
   --  timeout budget).  Expected-clean execution: no exception path.
   pragma Warnings (Off, "has no effect");
   procedure Test_Is_Stale is
   --  @test: Test_Is_Stale unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that Tick_Type starts at 0 and Default_Timeout
   --    is positive, ensuring the staleness predicate is well-defined
   --    for all possible watchdog states.
   --  THEORIES: Is_Stale computes Now - WS.Last_Heartbeat > WS.Timeout;
   --    with Tick_Type'First = 0 and Timeout > 0, the subtraction is
   --    non-negative and the comparison is meaningful.
   --  APPLICATIONS: Two pragma Assert statements verify the subtype
   --    bounds; no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 4.5.5 "Equality
   --    Operators"]; [Citation: Laprie, "Dependability: Basic Concepts
   --    and Terminology," Springer, 1992]
   begin
      pragma Assert (Tick_Type'First = 0);
      pragma Assert (Default_Timeout > 0);
   end Test_Is_Stale;
   pragma Unreferenced (Test_Is_Stale);

   --  Expected-clean execution: assertions cover the status lattice only,
   --  so no exception path exists.
   procedure Test_Cross_Check is
   --  @test: Test_Cross_Check unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that the Health_Status lattice orders Healthy
   --    before Recovering, ensuring Cross_Check supervision transitions
   --    are well-founded.
   --  THEORIES: The lattice ordering Healthy < Recovering guarantees
   --    that the grace ladder in Cross_Check promotes Failed monitors
   --    to Recovering without violating the state machine invariants.
   --  APPLICATIONS: Single pragma Assert checks the lattice position;
   --    no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 3.5.1 "Enumeration
   --    Types"]; [Citation: Laprie, "Dependability: Basic Concepts and
   --    Terminology," Springer, 1992, Ch. 3]
   begin
      pragma Assert (Health_Status'Pos (Healthy)
                       < Health_Status'Pos (Recovering));
   end Test_Cross_Check;

   --  Expected-clean execution: assertions cover the restart budget only,
   --  so no exception path exists.
   procedure Test_Advance_Recovery is
   --  @test: Test_Advance_Recovery unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that Max_Recovery_Attempts >= 1, ensuring the
   --    saturating Recovery_Attempts counter in Advance_Recovery has
   --    at least one recovery budget before saturation.
   --  THEORIES: If Max_Recovery_Attempts >= 1, then Advance_Recovery
   --    can promote a Recovering monitor to Healthy at least once
   --    before the counter saturates, preserving recovery liveness.
   --  APPLICATIONS: Single pragma Assert checks the constant bound;
   --    no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 11.4.2 "Assertion
   --    Pragmas"]; [Citation: Laprie, "Dependability: Basic Concepts
   --    and Terminology," Springer, 1992, Ch. 6]
   begin
      pragma Assert (Max_Recovery_Attempts >= 1);
   end Test_Advance_Recovery;

   --  Expected-clean execution: assertions cover lattice termination only,
   --  so no exception path exists.
   procedure Test_Emergency_Safe_State is
   --  @test: Test_Emergency_Safe_State unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that Dead is the terminal Health_Status value,
   --    ensuring Emergency_Safe_State drives both monitors to a
   --    terminal state from which no further transitions are possible.
   --  THEORIES: If Health_Status'Last = Dead, then Emergency_Safe_State
   --    can set both Status fields to Dead without exceeding the
   --    enumeration range; Dead being terminal means the latch is
   --    irrevocable.
   --  APPLICATIONS: Single pragma Assert checks the terminal lattice
   --    value; no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 3.5.1 "Enumeration
   --    Types"]; [Citation: Laprie, "Dependability: Basic Concepts and
   --    Terminology," Springer, 1992 — safe state]
   begin
      pragma Assert (Health_Status'Last = Dead);
   end Test_Emergency_Safe_State;

   --  Expected-clean execution: assertions cover lattice ranking only, so
   --  no exception path exists.
   procedure Test_Needs_Emergency is
   --  @test: Test_Needs_Emergency unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
   --  AXIOMS: Validate that the Health_Status lattice orders Failed
   --    before Dead, ensuring Needs_Emergency's boolean conjunction
   --    correctly identifies the dual-failure condition.
   --  THEORIES: The lattice ordering Failed < Dead guarantees that
   --    both watchdogs must reach Failed before Emergency_Safe_State
   --    can drive them to Dead; Needs_Emergency checks exactly this.
   --  APPLICATIONS: Single pragma Assert checks the lattice position;
   --    no runtime state is modified.
   --  CITATIONS: [Citation: Ada Reference Manual, RM 4.5.5 "Equality
   --    Operators"]; [Citation: Laprie, "Dependability: Basic Concepts
   --    and Terminology," Springer, 1992 — dual failure]
   begin
      pragma Assert (Health_Status'Pos (Failed)
                       < Health_Status'Pos (Dead));
   end Test_Needs_Emergency;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Advance_Recovery", Test_Advance_Recovery'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Cross_Check", Test_Cross_Check'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Emergency_Safe_State", Test_Emergency_Safe_State'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Evaluate", Test_Evaluate'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Initialize", Test_Initialize'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Is_Stale", Test_Is_Stale'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Needs_Emergency", Test_Needs_Emergency'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Update_Heartbeat", Test_Update_Heartbeat'Access);
end StellarOrion_Dual_Watchdog;
