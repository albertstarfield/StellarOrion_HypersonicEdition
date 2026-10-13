(* ============================================================================
   AXIOMS / THEORIES / APPLICATIONS / CITATIONS
   Unit : StellarOrion_Sparta -- SPARTA DSMC solver bridge
          (stellarorion_sparta.ads, stellarorion_sparta.adb)

   AXIOMS
     A1  The dump cadence written into the generated deck is the single
         source of truth DUMP_STATS_INTERVAL (= 100 ticks,
         stellarorion_sparta.ads:31).  It lives in the package spec so the
         deck writer and the completeness check cannot disagree.
     A2  The deck generator clamps the effective interval N to Steps
         (stellarorion_sparta.adb:948-951), so a run shorter than the
         cadence still emits the step-0 dump plus one full interval.
     A3  SPARTA writes dump files at steps 0, N, 2N, ... up to the last
         multiple not exceeding Steps, so the file count is Steps / N + 1
         (stellarorion_sparta.adb:954).

   THEORIES
     T1  The Post aspect declared on Expected_Dump_Count
         (stellarorion_sparta.ads:166) requires 1 <= Result <= Steps + 1.
         Both bounds are discharged below, and the safety-critical fact is
         that the lower bound never collapses to zero (a count of 0 would
         make the completeness verdict vacuous).
     T2  The unit's own self-test Test_Expected_Dump_Count
         (stellarorion_sparta.adb:4637-4647) pins the concrete rule values
         (2 for Steps below the cadence).  The below-cadence case is proved
         here as a theorem rather than asserted inside a test stub.

   APPLICATIONS
     This file is swept by src/utils/coq_proof_gate.py together with every
     other .v in proofs/, src/proofs/ and src/rocq/; run.py phase 3 aborts
     on any non-zero coqc exit, so a regression in the cadence rule fails
     the build before it can reach the validation gate.

   CITATIONS
     [CoqRM] Coq Reference Manual, Coq.Arith.PeanoNat (Nat.div_le_upper_bound,
             Nat.ltb_lt, Nat.ltb_ge, Nat.mul_le_mono_r, Nat.mul_1_l,
             Nat.div_same) -- https://coq.inria.fr/refman/
     [CoqMicromega] Coq Reference Manual, micromega plugin (Lia) --
             https://coq.inria.fr/refman/addendum/micromega.html
     [Plimpton2014] Plimpton, S. & Gallis, M., "SPARTA: Stochastic Particle
             Automatic Real-Time Application", 2014 -- dump command,
             "dump ... every N".
     [DO178C] DO-178C Sec 6.4.4 -- verification of derived constants.
   ============================================================================ *)

Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.

Open Scope nat_scope.

(* A1 -- the dump cadence constant, mirrored from stellarorion_sparta.ads:31. *)
Definition dump_stats_interval : nat := 100.

(* A2 -- the deck generator's clamp: when the fixed cadence exceeds the run
   length the effective interval is the run itself
   (stellarorion_sparta.adb:948-951). *)
Definition dump_cadence (steps : nat) : nat :=
  if dump_stats_interval <? steps then dump_stats_interval else steps.

(* A3 -- the documented dump-file count: the multiples of N inside the run
   plus the step-0 file (stellarorion_sparta.adb:954). *)
Definition expected_dump_count (steps : nat) : nat :=
  steps / dump_cadence steps + 1.

(* T1a -- the cadence is a positive tick count, so dividing by it is defined. *)
Lemma dump_stats_interval_positive : 1 <= dump_stats_interval.
Proof. unfold dump_stats_interval. lia. Qed.

(* T1b -- a run of at least one step always has a positive effective cadence,
   which is what keeps the division in expected_dump_count meaningful. *)
Lemma dump_cadence_positive : forall steps,
  1 <= steps -> 1 <= dump_cadence steps.
Proof.
  intros steps Hs.
  unfold dump_cadence, dump_stats_interval.
  destruct (100 <? steps) eqn:E.
  - apply Nat.ltb_lt in E. simpl. lia.
  - apply Nat.ltb_ge in E. simpl. lia.
Qed.

(* T1c -- the effective cadence never exceeds the fixed interval. *)
Lemma dump_cadence_clamped : forall steps,
  dump_cadence steps <= dump_stats_interval.
Proof.
  intros steps.
  unfold dump_cadence, dump_stats_interval.
  destruct (100 <? steps) eqn:E.
  - apply Nat.ltb_lt in E. simpl. lia.
  - apply Nat.ltb_ge in E. simpl. exact E.
Qed.

(* T1 -- the declared Post aspect of Expected_Dump_Count: the count is at
   least 1 and at most Steps + 1 (stellarorion_sparta.ads:166).

   Proof idea: the upper bound needs steps / cadence <= steps.  Because the
   cadence is at least 1, Nat.div_le_upper_bound with q := steps reduces it
   to steps <= cadence * steps, which follows from 1 <= cadence by
   monotonicity of multiplication. *)
Lemma expected_dump_count_bounds : forall steps, 1 <= steps ->
  1 <= expected_dump_count steps /\ expected_dump_count steps <= steps + 1.
Proof.
  intros steps Hs.
  assert (Hn : 1 <= dump_cadence steps) by (apply dump_cadence_positive; exact Hs).
  assert (Hdiv : steps / dump_cadence steps <= steps).
  { apply Nat.div_le_upper_bound.
    - intro H0. lia.
    - assert (Hm : 1 * steps <= dump_cadence steps * steps).
      { apply Nat.mul_le_mono_r. exact Hn. }
      rewrite Nat.mul_1_l in Hm. exact Hm. }
  unfold expected_dump_count. split; lia.
Qed.

(* T2 -- the self-test's below-cadence case: exactly one full interval plus
   the step-0 dump, i.e. 2 files (stellarorion_sparta.adb:4637-4647). *)
Lemma dump_count_below_cadence : forall steps,
  1 <= steps -> steps <= dump_stats_interval ->
  expected_dump_count steps = 2.
Proof.
  intros steps Hs Hle.
  unfold dump_stats_interval in Hle.
  assert (Hc : dump_cadence steps = steps).
  { unfold dump_cadence, dump_stats_interval.
    destruct (100 <? steps) eqn:E.
    - apply Nat.ltb_lt in E. simpl. lia.
    - reflexivity. }
  assert (Hne : steps <> 0) by (intro H0; lia).
  unfold expected_dump_count. rewrite Hc.
  rewrite (Nat.div_same steps Hne).
  unfold dump_stats_interval. lia.
Qed.
