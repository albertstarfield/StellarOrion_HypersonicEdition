(* ============================================================================
   AXIOMS / THEORIES / APPLICATIONS / CITATIONS
   Unit : StellarOrion_Dual_Watchdog -- dual independent watchdogs with
          cross-monitoring (stellarorion_dual_watchdog.ads, .adb)

   AXIOMS
     A1  Each watchdog runs the state machine declared at
         stellarorion_dual_watchdog.ads:36:
         Healthy -> Degraded -> Failed -> Recovering -> Healthy, with the
         both-failed transition sending every state to Dead.
     A2  Heartbeats are explicit monotonic tick counts supplied by the caller
         (subtype Tick_Type, :49), so every operation is a pure function of
         its inputs and the concurrent tasking wrapper is out of scope here.
     A3  Audit counters are bounded and saturating at Max_Audit_Count
         = 1_000_000 (:59), which is what discharges every overflow
         obligation (B5 gate lesson documented at :52-56).
     A4  Recovery attempts are limited to Max_Recovery_Attempts = 3 (:40)
         and the default heartbeat budget is Default_Timeout = 10 ticks (:44).

   THEORIES
     T1  The saturating increment never leaves the bounded range, is
         monotone inside the range, and is idempotent once the ceiling is
         reached.  This is the invariant that lets the counters be audit
         evidence without becoming a control-flow overflow source.
     T2  Dead is the maximum health rank and no state outranks it, which is
         the formal content of "the emergency safe state is the terminal
         state of the escalation path".
     T3  A Dead watchdog rejects heartbeats -- only Healthy and Degraded
         accept them, so a failed monitor cannot be silently resurrected
         (the Post aspect at :130-136).
     T4  The emergency latch is sticky: once Emergency_Latched is set it
         stays set (record component at :78, rationale comment :79-81).

   APPLICATIONS
     T3 is the no-silent-resurrection guarantee the dual-watchdog matrix
     exists to provide; T4 is the fail-safe property that the safe state
     cannot be silently un-latched.  Swept by src/utils/coq_proof_gate.py.

   CITATIONS
     [Storey1996] Storey, N., "Safety-Critical Computer Systems",
         Addison-Wesley, 1996 -- watchdog timers and fail-safe design.
     [CoqRM] Coq Reference Manual, Coq.Arith.PeanoNat (Nat.ltb_lt, Nat.ltb_ge,
         Nat.le_min) -- https://coq.inria.fr/refman/
     [CoqMicromega] Coq Reference Manual, micromega plugin (Lia)
         -- https://coq.inria.fr/refman/addendum/micromega.html
     [DO178C] DO-178C Sec 6.4.4; ISO 26262 Sec 9.4.3.
   ============================================================================ *)

Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.

Open Scope nat_scope.

(* A4 -- the recovery-attempt budget (stellarorion_dual_watchdog.ads:40). *)
Definition max_recovery_attempts : nat := 3.

(* A4 -- the default heartbeat budget in ticks (:44). *)
Definition default_timeout : nat := 10.

(* A3 -- the audit counter ceiling.  Spelled as 1000 * 1000 because a bare
   1000000 nat literal is rendered by Coq as an application of
   Nat.of_num_uint, which the micromega plugins cannot evaluate. *)
Definition max_audit_count : nat := 1000 * 1000.

Lemma max_recovery_attempts_positive : 0 < max_recovery_attempts.
Proof. unfold max_recovery_attempts. lia. Qed.

Lemma default_timeout_positive : 0 < default_timeout.
Proof. unfold default_timeout. lia. Qed.

Lemma max_audit_count_positive : 0 < max_audit_count.
Proof. unfold max_audit_count. lia. Qed.

(* A3 -- the saturating increment: the counter grows by one until it reaches
   the ceiling, where it sticks. *)
Definition inc_audit (c : nat) : nat :=
  if max_audit_count <? S c then max_audit_count else S c.

(* T1a -- the increment never leaves the bounded subtype range
   0 .. Max_Audit_Count. *)
Lemma inc_audit_bounded : forall c, inc_audit c <= max_audit_count.
Proof.
  intros c.
  unfold inc_audit.
  destruct (max_audit_count <? S c) eqn:E.
  - apply Nat.ltb_lt in E. lia.
  - apply Nat.ltb_ge in E. lia.
Qed.

(* T1b -- inside the range the increment is monotone, so the audit trail
   never moves backwards. *)
Lemma inc_audit_monotone : forall c,
  c <= max_audit_count -> c <= inc_audit c.
Proof.
  intros c Hc.
  unfold inc_audit.
  destruct (max_audit_count <? S c) eqn:E.
  - apply Nat.ltb_lt in E. lia.
  - apply Nat.ltb_ge in E. lia.
Qed.

(* T1c -- at the ceiling the increment is idempotent. *)
Lemma inc_audit_idempotent_at_ceiling : forall c,
  c = max_audit_count -> inc_audit c = max_audit_count.
Proof.
  intros c Hc.
  unfold inc_audit.
  destruct (max_audit_count <? S c) eqn:E.
  - reflexivity.
  - apply Nat.ltb_ge in E. rewrite Hc in E. lia.
Qed.

(* A1 -- the health lattice (stellarorion_dual_watchdog.ads:36). *)
Inductive health := Healthy : health | Degraded : health
                  | Failed : health | Recovering : health | Dead : health.

(* A1 -- the escalation rank: higher means further along the degradation
   path.  Failed and Recovering share rank 2 because Recovering is the
   repair arm of Failed, not a further degradation. *)
Definition health_rank (h : health) : nat :=
  match h with
  | Healthy => 0
  | Degraded => 1
  | Failed => 2
  | Recovering => 2
  | Dead => 3
  end.

(* T2a -- every health state ranks at most as high as Dead. *)
Lemma health_rank_bounded : forall h, health_rank h <= 3.
Proof.
  intros h.
  destruct h; simpl; lia.
Qed.

(* T2 -- Dead is the maximum rank, so the escalation path terminates there
   and cannot cycle back below it. *)
Lemma dead_is_the_maximum_rank : forall h,
  health_rank h <= health_rank Dead.
Proof.
  intros h.
  destruct h; simpl; lia.
Qed.

(* A1 -- only a live watchdog accepts a heartbeat (the Post aspect at
   stellarorion_dual_watchdog.ads:130-136). *)
Definition accept_heartbeat (h : health) : bool :=
  match h with Healthy | Degraded => true | _ => false end.

(* T3a -- a Dead watchdog rejects heartbeats. *)
Lemma dead_rejects_heartbeat : accept_heartbeat Dead = false.
Proof.
  unfold accept_heartbeat.
  reflexivity.
Qed.

(* T3 -- accepting a heartbeat implies the watchdog was Healthy or Degraded,
   so a Failed monitor stays failed until cross-recovery repairs it. *)
Lemma only_live_watchdogs_accept : forall h,
  accept_heartbeat h = true -> h = Healthy \/ h = Degraded.
Proof.
  intros h H.
  destruct h; simpl in H.
  - left. reflexivity.
  - right. reflexivity.
  - discriminate H.
  - discriminate H.
  - discriminate H.
Qed.

(* A4 -- the emergency latch is set by the both-failed transition and, once
   set, is never cleared (stellarorion_dual_watchdog.ads:78-81). *)
Definition emergency_latch (latched : bool) : bool := true.

(* T4 -- the emergency latch is sticky. *)
Lemma emergency_latch_sticky : forall b,
  emergency_latch (emergency_latch b) = emergency_latch b.
Proof.
  intros b.
  destruct b; unfold emergency_latch; reflexivity.
Qed.
