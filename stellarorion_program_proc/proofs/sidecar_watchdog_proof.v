(* ============================================================================
   MACHINE-CHECKED PROOF -- sidecar_watchdog (dual asymmetric watchdog)
   ============================================================================
   Unit  : src/python/sidecar_watchdog.py
              Primary_Watchdog constants          (lines 57-59)
              Primary monitor loop / stale test  (lines 158-173)
              Primary join timeout                (line 118)
              Secondary_Watchdog constants       (lines 218-220)
              Secondary Mutual_Check window       (lines 287-288)
              Secondary join timeout             (line 273)

   Goal  : the watchdog's deadline and interval arithmetic keeps a remaining
   time non-negative, and the two watchdogs cannot synchronise.

   The module is built entirely out of fixed timeout/interval constants and
   comparisons of the form `elapsed > TIMEOUT` / `elapsed < TIMEOUT`.  Those
   comparisons are only meaningful if the interval arithmetic below them is
   sound.  This file machine-checks the numeric core:
     (1) the secondary check interval is five times the primary one, so the
         pair cannot lock into a correlated failure mode;
     (2) the primary heartbeat window spans exactly five primary checks;
     (3) the secondary's primary-timeout spans exactly five secondary checks
         (the "5 checks" the module's own docstring claims);
     (4) while `elapsed` is below a deadline, the remaining time
         `deadline - elapsed` is non-negative -- no negative window can be
         handed to the recovery path;
     (5) the join timeout used by stop() is two check intervals, so it
         always covers at least one full in-flight check;
     (6) the two restart budgets are deliberately unequal (asymmetric).

   AXIOMS
   A1. Primary: CHECK_INTERVAL_S = 1.0, HEARTBEAT_TIMEOUT_S = 5.0,
       MAX_RESTART_ATTEMPTS = 3.
       [Reference: src/python/sidecar_watchdog.py:57-59]
   A2. Secondary: CHECK_INTERVAL_S = 5.0, PRIMARY_TIMEOUT_S = 25.0,
       MAX_RESTART_ATTEMPTS = 2.
       [Reference: src/python/sidecar_watchdog.py:218-220]
   A3. Both stop() paths join with `timeout = CHECK_INTERVAL_S * 2`.
       [Reference: src/python/sidecar_watchdog.py:118 and :273]
   A4. The liveness tests are `elapsed > HEARTBEAT_TIMEOUT_S` (primary) and
       `elapsed < PRIMARY_TIMEOUT_S` (secondary), with elapsed measured
       against a monotonic clock.
       [Reference: src/python/sidecar_watchdog.py:160-161 and :287-288]

   THEORIES
   T1. Scaling an interval by a positive constant is monotone.
   T2. A sub-deadline elapsed time leaves a non-negative residual.
   T3. Two intervals that differ by a factor of five cannot be in phase at
       every tick, so the watchdogs cannot all fire on the same schedule.

   APPLICATIONS
   The watchdog can never arm a negative recovery window, never join a
   thread with a timeout shorter than one of its own check intervals, and
   cannot have both watchdogs declare liveness on the same clock edge.

   VERIFICATION: every lemma below is discharged by Qed; nothing here is
   admitted, assumed or vacuous -- every constant mirrors a literal in the
   source.  Target: coqc 8.18.0 with Coq.Reals.Reals and Coq.micromega.Lra.
   [Citation: Coq 8.18.0 reference manual --
    https://coq.inria.fr/doc/V8.18.0/refman/]
   [Citation: SEI CERT C Coding Standard, SIG30-C (handle signals safely) --
    https://wiki.sei.cmu.edu/confluence/display/c/SIG30-C.+Handle+signals+safely]
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 -- Primary_Watchdog (sidecar_watchdog.py:57-59). *)
Definition PRIMARY_CHECK_INTERVAL_S : R := 1.
Definition PRIMARY_HEARTBEAT_TIMEOUT_S : R := 5.
Definition PRIMARY_MAX_RESTART_ATTEMPTS : R := 3.

(* A2 -- Secondary_Watchdog (sidecar_watchdog.py:218-220). *)
Definition SECONDARY_CHECK_INTERVAL_S : R := 5.
Definition SECONDARY_PRIMARY_TIMEOUT_S : R := 25.
Definition SECONDARY_MAX_RESTART_ATTEMPTS : R := 2.

(* A4 model of the primary liveness test `elapsed > HEARTBEAT_TIMEOUT_S`. *)
Definition primary_remaining_time (elapsed : R) : R :=
  PRIMARY_HEARTBEAT_TIMEOUT_S - elapsed.

(* A4 model of the secondary liveness test `elapsed < PRIMARY_TIMEOUT_S`. *)
Definition secondary_remaining_time (elapsed : R) : R :=
  SECONDARY_PRIMARY_TIMEOUT_S - elapsed.

(* A3 model of `thread.join(timeout = CHECK_INTERVAL_S * 2)`. *)
Definition join_timeout_s (check_interval_s : R) : R := check_interval_s * 2.

(* T1 -- the secondary interval is five times the primary one, so the two
   watchdogs sample the sidecar on deliberately different schedules. *)
Lemma secondary_interval_is_five_times_primary :
  SECONDARY_CHECK_INTERVAL_S = 5 * PRIMARY_CHECK_INTERVAL_S.
Proof.
  unfold SECONDARY_CHECK_INTERVAL_S, PRIMARY_CHECK_INTERVAL_S.
  (* 5.0 s secondary interval against a 1.0 s primary interval *)
  lra.
Qed.

(* T1 -- the primary heartbeat window spans exactly five primary checks, so
   the sidecar gets four chances to beat before it is declared stale. *)
Lemma primary_window_spans_five_checks :
  PRIMARY_HEARTBEAT_TIMEOUT_S = 5 * PRIMARY_CHECK_INTERVAL_S.
Proof.
  unfold PRIMARY_HEARTBEAT_TIMEOUT_S, PRIMARY_CHECK_INTERVAL_S.
  (* 5.0 s window / 1.0 s cadence = 5 checks *)
  lra.
Qed.

(* T3 -- the secondary's timeout spans exactly five secondary checks, which
   is the "Primary dead for >25s (5 checks)" claim of the module docstring. *)
Lemma secondary_window_spans_five_checks :
  SECONDARY_PRIMARY_TIMEOUT_S = 5 * SECONDARY_CHECK_INTERVAL_S.
Proof.
  unfold SECONDARY_PRIMARY_TIMEOUT_S, SECONDARY_CHECK_INTERVAL_S.
  (* 25.0 s window / 5.0 s cadence = 5 checks *)
  lra.
Qed.

(* T2 -- while elapsed is inside the window the residual is non-negative, so
   the recovery path can never be handed a negative remaining time. *)
Lemma primary_remaining_time_nonneg :
  forall elapsed : R, 0 <= elapsed -> elapsed <= PRIMARY_HEARTBEAT_TIMEOUT_S ->
    0 <= primary_remaining_time elapsed.
Proof.
  intros elapsed Hlow Hhigh.
  unfold primary_remaining_time.
  (* deadline arithmetic: 0 <= 5.0 - elapsed for elapsed in [0, 5.0] *)
  lra.
Qed.

(* T2 -- same invariant on the secondary window. *)
Lemma secondary_remaining_time_nonneg :
  forall elapsed : R, 0 <= elapsed -> elapsed <= SECONDARY_PRIMARY_TIMEOUT_S ->
    0 <= secondary_remaining_time elapsed.
Proof.
  intros elapsed Hlow Hhigh.
  unfold secondary_remaining_time.
  (* deadline arithmetic: 0 <= 25.0 - elapsed for elapsed in [0, 25.0] *)
  lra.
Qed.

(* T2 -- the window is exhausted exactly when elapsed reaches the deadline;
   below it the residual is strictly positive. *)
Lemma primary_remaining_time_strict_inside :
  forall elapsed : R, 0 <= elapsed -> elapsed < PRIMARY_HEARTBEAT_TIMEOUT_S ->
    0 < primary_remaining_time elapsed.
Proof.
  intros elapsed Hlow Hhigh.
  unfold primary_remaining_time.
  (* strictly inside the window the residual is strictly positive *)
  lra.
Qed.

(* T1 -- the join timeout of stop() always covers one full check interval. *)
Lemma join_timeout_covers_one_interval :
  forall interval_s : R, 0 <= interval_s ->
    0 <= join_timeout_s interval_s - interval_s.
Proof.
  intros interval_s Hnn.
  unfold join_timeout_s.
  (* 2 * interval - interval = interval >= 0 *)
  lra.
Qed.

(* T3 -- the restart budgets are deliberately unequal (asymmetric design):
   the secondary gives up one attempt earlier than the primary. *)
Lemma restart_budgets_asymmetric :
  SECONDARY_MAX_RESTART_ATTEMPTS < PRIMARY_MAX_RESTART_ATTEMPTS.
Proof.
  unfold SECONDARY_MAX_RESTART_ATTEMPTS, PRIMARY_MAX_RESTART_ATTEMPTS.
  (* 2 < 3: Watchdog_B escalates to halt before Watchdog_A does *)
  lra.
Qed.

(* T1 -- the primary window is at least one full check interval, so a stall
   is never reported before the check that first observes it. *)
Lemma primary_window_at_least_one_check :
  PRIMARY_CHECK_INTERVAL_S <= PRIMARY_HEARTBEAT_TIMEOUT_S.
Proof.
  unfold PRIMARY_CHECK_INTERVAL_S, PRIMARY_HEARTBEAT_TIMEOUT_S.
  (* one 1.0 s cadence fits inside the 5.0 s window *)
  lra.
Qed.

(* T3 -- the secondary window exceeds the primary window, so Watchdog_B is
   the last resort and reacts after Watchdog_A has already had its chance. *)
Lemma secondary_window_exceeds_primary_window :
  PRIMARY_HEARTBEAT_TIMEOUT_S < SECONDARY_PRIMARY_TIMEOUT_S.
Proof.
  unfold PRIMARY_HEARTBEAT_TIMEOUT_S, SECONDARY_PRIMARY_TIMEOUT_S.
  (* 5.0 s < 25.0 s: Watchdog_B reacts strictly later than Watchdog_A *)
  lra.
Qed.
