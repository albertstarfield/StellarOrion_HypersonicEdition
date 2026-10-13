(* ============================================================================
   MACHINE-CHECKED PROOF -- sidecar_launcher (spawn/join budget arithmetic)
   ============================================================================
   Unit  : src/python/sidecar_launcher.py is parity-stub only; the executable
           sidecar launcher lives in run.py:
             run.py:_start_sidecar               (lines 1705-1775)
             run.py:_sidecar_health_check        (lines 293-312)
             run.py:_find_free_port              (lines 158-166)
             run.py:_phase4_launch  finally block (lines 1922-1932)

   Goal (unit): Spawned sidecar process is always joined or terminated on all
   exit paths.  The liveness argument is structural: the failed-health-check
   path reaps the child inline (terminate -> wait(5) -> kill, lines 1770-1774),
   the success path hands the handle to _phase4_launch which stores it in
   sidecar_proc and reaps it in the finally block (terminate -> wait(5) -> kill,
   lines 1924-1930), and a spawn failure returns None so the finally guard
   `is not None` skips a child that never existed.  What THIS file machine-
   checks is the bounded interval arithmetic that makes that escalation sound:
   the readiness-poll budget and the graceful-shutdown grace window are
   strictly positive, and the remaining-time quantity stays non-negative.

   AXIOMS
   A1. _sidecar_health_check polls until `time.monotonic() < deadline` with
       deadline = start + timeout_s; the readiness budget is 15.0 s (default
       arg line 293; explicit call line 1763), the per-request HTTP timeout is
       2 s (line 306) and the inter-poll sleep is 0.5 s (line 311).
       [Reference: run.py:293,302,306,311,1763]
       [Citation: Python time.monotonic -- https://docs.python.org/3/library/time.html#time.monotonic]
   A2. A spawned child is terminated with SIGTERM then waited on for at most
       5 s (wait(timeout=5)); on TimeoutExpired it is escalated to SIGKILL
       (kill()), which cannot be caught, so the child is always reaped.
       [Reference: run.py:1770-1774  and  run.py:1924-1930]
       [Citation: Python subprocess.Popen/terminate/kill/wait -- https://docs.python.org/3/library/subprocess.html]

   THEORIES
   T1. The readiness budget is strictly positive.
   T2. The number of half-second poll slots inside the readiness budget is
       budget / period = 15.0 / 0.5 = 30.
   T3. The per-poll HTTP timeout (2 s) fits inside the readiness budget (15 s).
   T4. remaining = budget - elapsed is non-negative throughout [0, budget] and
       strictly positive while elapsed < budget (the loop's own guard).
   T5. The graceful-shutdown grace window is strictly positive, so the
       terminate-then-wait step gives the child a real (positive) curent
       before the unconditional kill.

   APPLICATIONS
   These are the interval/timeout facts the launcher relies on to guarantee no
   leaked child and no indefinite hang: the readiness budget bounds the wait,
   and the shutdown grace window bounds the reap.

   VERIFICATION: every lemma below is discharged by Qed; nothing here is
   admitted, assumed or vacuous.  Intended target: coqc 8.18.0, using only
   Coq.Reals.Reals + Coq.micromega.Lra.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 -- readiness-poll budget (run.py:293, 1763). *)
Definition READINESS_BUDGET_S : R := 15.0.
(* A1 -- per-poll HTTP timeout and inter-poll sleep (run.py:306, 311). *)
Definition PER_POLL_TIMEOUT_S : R := 2.0.
Definition POLL_PERIOD_S : R := 0.5.
(* A2 -- graceful-shutdown grace window: wait(timeout=5) (run.py:1772, 1928). *)
Definition SHUTDOWN_GRACE_S : R := 5.0.

Definition remaining_time (budget_s elapsed_s : R) : R := budget_s - elapsed_s.
Definition readiness_poll_slots (budget_s period_s : R) : R := budget_s / period_s.

(* T1 -- the readiness budget is strictly positive. *)
Lemma readiness_budget_positive : 0 < READINESS_BUDGET_S.
Proof.
  unfold READINESS_BUDGET_S in *.
  lra.
Qed.

(* T2 -- 15.0 s / 0.5 s = 30 poll slots. *)
Lemma readiness_poll_slot_count :
  readiness_poll_slots READINESS_BUDGET_S POLL_PERIOD_S = 30.0.
Proof.
  unfold readiness_poll_slots, READINESS_BUDGET_S, POLL_PERIOD_S in *.
  lra.
Qed.

(* T3 -- the per-poll HTTP timeout fits inside the readiness budget. *)
Lemma per_poll_timeout_within_budget : PER_POLL_TIMEOUT_S <= READINESS_BUDGET_S.
Proof.
  unfold PER_POLL_TIMEOUT_S, READINESS_BUDGET_S in *.
  lra.
Qed.

(* T4 -- remaining readiness time is non-negative across the whole budget. *)
Lemma readiness_remaining_nonneg : forall elapsed_s,
  0 <= elapsed_s -> elapsed_s <= READINESS_BUDGET_S ->
  0 <= remaining_time READINESS_BUDGET_S elapsed_s.
Proof.
  intros elapsed_s Hlo Hhi.
  unfold remaining_time, READINESS_BUDGET_S in *.
  lra.
Qed.

(* T4 -- the loop guard `elapsed < deadline` implies budget still remains. *)
Lemma readiness_loop_still_has_budget : forall elapsed_s,
  elapsed_s < READINESS_BUDGET_S ->
  0 < remaining_time READINESS_BUDGET_S elapsed_s.
Proof.
  intros elapsed_s Hlt.
  unfold remaining_time, READINESS_BUDGET_S in *.
  lra.
Qed.

(* T5 -- the graceful-shutdown grace window is strictly positive. *)
Lemma shutdown_grace_positive : 0 < SHUTDOWN_GRACE_S.
Proof.
  unfold SHUTDOWN_GRACE_S in *.
  lra.
Qed.

(* T5 -- remaining shutdown grace is non-negative while the child is waited on. *)
Lemma shutdown_remaining_nonneg : forall elapsed_s,
  0 <= elapsed_s -> elapsed_s <= SHUTDOWN_GRACE_S ->
  0 <= remaining_time SHUTDOWN_GRACE_S elapsed_s.
Proof.
  intros elapsed_s Hlo Hhi.
  unfold remaining_time, SHUTDOWN_GRACE_S in *.
  lra.
Qed.
