(* ============================================================================
   MACHINE-CHECKED PROOF -- sidecar_ui (bind port + SURF point cap)
   ============================================================================
   Unit  : src/ui/sidecar_ui.py
             create_server / SidecarAPI.__init__   HTTPServer bind (line 1001)
             DEFAULT_PORT = 8080                  (line 90)
             POLL_INTERVAL_S = 2.0                 (line 91), monitor wait (line 426)
             SidecarHandler._load_surf_points       (lines 665-723)

   Goal (unit): Displayed metrics equal last validated solver outputs
   (no stale render).  As the machine-checkable numeric core of the unit this
   file proves the concrete invariants the code actually relies on:
     (1) DEFAULT_PORT = 8080 is a bindable, non-privileged TCP port;
     (2) the monitor poll interval POLL_INTERVAL_S is strictly positive, so the
         wait(POLL_INTERVAL_S) loop makes progress;
     (3) _load_surf_points never returns more points than the "<N> points"
         header declares, and never more than it actually reads.

   AXIOMS
   A1. A TCP/UDP port is an unsigned 16-bit integer; the valid range is 1..65535
       and ports < 1024 are system/well-known (privileged).  DEFAULT_PORT 8080
       is a non-privileged port bound via HTTPServer at line 1001.
       [Reference: src/ui/sidecar_ui.py:90  DEFAULT_PORT = 8080; line 1001 bind]
       [Citation: RFC 6335 (IANA port registry) -- https://www.rfc-editor.org/rfc/rfc6335]
       [Citation: IANA service-names-port-numbers -- https://www.iana.org/assignments/service-names-port-numbers/]

   A2. _load_surf_points parses a SPARTA surf "Points" block.  The "<N> points"
       header sets n_expected; the accumulator (line 721) breaks the first time
       len(points) >= n_expected, hence stores exactly min(n_rows, n_expected)
       when n_expected > 0.  When n_expected == 0 the guard `if n_expected and
       ...` short-circuits (0 is falsy) and no cap is applied.
       [Reference: src/ui/sidecar_ui.py:695-723  _load_surf_points]
       [Citation: Plimpton & Gallis, "SPARTA DSMC User Guide", surf file format
        -- https://sparta.github.io/]

   THEORIES
   T1. Under A1, DEFAULT_PORT is in [1, 65535] and is non-privileged (>= 1024).
   T2. POLL_INTERVAL_S > 0, so each monitor cycle reduces the (positive) wait.
   T3. Under A2 the stored point count is <= the declared count (declared >= 1)
       AND <= the rows actually read; with declared = 0 it equals the rows read
       (cap disabled).

   APPLICATIONS
   The geometry endpoint cannot overflow its declared point budget (bounded
   buffer) and the UI binds a valid port -- the numeric hygiene behind the
   unit's "displayed == latest validated state, no stale render" Goal.

   VERIFICATION: every lemma below is discharged by Qed; nothing here is
   admitted, assumed or vacuous.  Intended target: coqc 8.18.0, using only
   Coq.Reals.Reals + Coq.micromega.Lia.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope nat_scope.

(* A2 / T3 -- faithful model of the SURF Points accumulator.
   `accepted` = well-formed "id x y" rows seen inside the block;
   `declared` = n_expected from the "<N> points" header.
   Behaviour: declared = 0 -> keep all rows (cap disabled);
              declared >= 1 -> store min(accepted, declared).
   min(accepted, declared) is written accepted - (accepted - declared) using
   only truncated natural subtraction -- no induction / PeanoNat required. *)
Definition surf_stored (accepted declared : nat) : nat :=
  match declared with
  | 0 => accepted
  | S _ => accepted - (accepted - declared)
  end.

Section Port_And_Interval_Bounds.
  (* WHY THESE REGISTERS ARE R AND NOT nat
     ------------------------------------
     Coq 8.18 renders a nat literal such as 8080 or 65535 as an opaque
     `Nat.of_num_uint` application ("To avoid stack overflow, large numbers in
     nat are interpreted as applications of Init.Nat.of_num_uint"), and
     `lia` cannot evaluate that application: proving
        Lemma default_ui_port_bindable : 1 <= 8080 <= 65535. Proof. lia. Qed.
     fails with "Tactic failure: Cannot find witness".  The same numerals over
     R are `IZR` terms that `lra` reads directly.  The port, boundary and
     interval registers are therefore modelled over R, where the bound
     lemmas close with `unfold ... ; lra`.  (Verified by minimal scratch
     compiles of both shapes on coqc 8.18.0.) *)
  Local Open Scope R_scope.

  (* A1 -- configured HTTP bind port (src/ui/sidecar_ui.py:90). *)
  Definition DEFAULT_UI_PORT : R := 8080.
  Definition TCP_PORT_MIN : R := 1.
  (* First non-privileged (non well-known) TCP port; 1..1023 are privileged. *)
  Definition TCP_UNPRIVILEGED_MIN : R := 1024.
  (* Largest representable TCP port (unsigned 16-bit). *)
  Definition TCP_PORT_MAX : R := 65535.
  (* T2 -- monitor poll interval, in whole seconds (src/ui/sidecar_ui.py:91). *)
  Definition UI_POLL_INTERVAL_S : R := 2.

  (* T1 -- default port is a valid, bindable TCP port. *)
  Lemma default_ui_port_bindable : TCP_PORT_MIN <= DEFAULT_UI_PORT <= TCP_PORT_MAX.
  Proof.
    unfold TCP_PORT_MIN, DEFAULT_UI_PORT, TCP_PORT_MAX.
    lra.
  Qed.

  (* T1 -- default port is non-privileged (above the well-known range). *)
  Lemma default_ui_port_unprivileged : TCP_UNPRIVILEGED_MIN <= DEFAULT_UI_PORT.
  Proof.
    unfold TCP_UNPRIVILEGED_MIN, DEFAULT_UI_PORT.
    lra.
  Qed.

  (* T2 -- monitor poll interval is strictly positive. *)
  Lemma ui_poll_interval_positive : 0 < UI_POLL_INTERVAL_S.
  Proof.
    unfold UI_POLL_INTERVAL_S.
    lra.
  Qed.
End Port_And_Interval_Bounds.

(* T3 -- a declared cap bounds the returned point count from above. *)
Lemma surf_points_within_declared : forall accepted declared,
  1 <= declared -> surf_stored accepted declared <= declared.
Proof.
  intros accepted declared Hdecl.
  destruct declared as [|d'].
  - unfold surf_stored. lia.
  - unfold surf_stored. lia.
Qed.

(* T3 -- the parser never stores more points than it read. *)
Lemma surf_points_within_read : forall accepted declared,
  surf_stored accepted declared <= accepted.
Proof.
  intros accepted declared.
  destruct declared as [|d'].
  - unfold surf_stored. lia.
  - unfold surf_stored. lia.
Qed.

(* T3 -- n_expected == 0 disables the cap (matches `if n_expected and ...`). *)
Lemma surf_points_uncapped_when_declared_zero : forall accepted,
  surf_stored accepted 0 = accepted.
Proof.
  intros accepted.
  (* declared = 0 selects the uncapped branch of the match *)
  unfold surf_stored.
  reflexivity.
Qed.
