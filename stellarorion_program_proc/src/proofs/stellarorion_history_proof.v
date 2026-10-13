(* ============================================================================
   AXIOMS / THEORIES / APPLICATIONS / CITATIONS
   Unit : StellarOrion_History -- run history / database bridge
          (stellarorion_history.ads, stellarorion_history.adb)

   AXIOMS
     A1  Recorded samples carry a simulated-time stamp drawn from a monotonic
         logical clock (the package clock source is Ada.Real_Time backed by
         CLOCK_MONOTONIC, documented at stellarorion_history.ads:57).
     A2  A new sample row is appended only when its time stamp is strictly
         later than the last recorded one, so the stored series in
         samples.csv never regresses.
     A3  The run set is a bounded array of Max_Run_Count = 1000 rows with an
         explicit Count (stellarorion_history.ads:37-43), so the capacity is
         a fixed positive constant rather than a computed bound.

   THEORIES
     T1  With every successive simulated step advancing the clock, any
         earlier sample's time is strictly before any later sample's time.
         This is the ordering the resume and "resume from checkpoint" paths
         rely on when they replay samples.csv.
     T2  The writer's append guard preserves that ordering: storing one more
         sample strictly later than the previous last one keeps the whole
         series strictly increasing.
     T3  The run capacity is positive, so the bounded array can always hold
         the header row plus at least one run.

   APPLICATIONS
     Swept by src/utils/coq_proof_gate.py.  The file-I/O and SQLite-bridge
     behaviour itself is outside the SPARK subset (the unit is declared
     SPARK_Mode => Off) and is covered by the self-test harness; what is
     discharged here is the ordering invariant that behaviour depends on.

   CITATIONS
     [AdaRM] ISO/IEC 8652:2012 (Ada 2012), Sec 9.8 Ada.Real_Time
         -- monotonic logical time.
     [CoqRM] Coq Reference Manual, Coq.Reals and the micromega plugin (Lra)
         -- https://coq.inria.fr/refman/
     [CoqMicromega] Coq Reference Manual, micromega plugin (Lra)
         -- https://coq.inria.fr/refman/addendum/micromega.html
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.

Open Scope R_scope.

(* A3 -- the run-history capacity is a nat count, so it lives in its own nat
   section; the series lemmas below stay in R_scope. *)
Section History_Nat.
  Local Open Scope nat_scope.

  Definition max_run_count : nat := 1000.

  (* T3 -- the bounded array can always hold the header row plus one run. *)
  Lemma max_run_count_positive : 0 < max_run_count.
  Proof. unfold max_run_count. lia. Qed.

End History_Nat.

(* A1 -- the time stamp of the i-th recorded sample. *)
Definition sample_time (t : nat -> R) (i : nat) : R := t i.

(* T1 -- the recorded series is strictly increasing in simulated time.

   Proof idea: induction on the later index j.  The base case forces i = 0
   because i <= 0 and i is a nat, so the goal is the single first step of
   the clock.  The step case splits on whether i has already reached j or is
   still one step behind it; the first branch chains the induction
   hypothesis with the clock step, the second is the clock step itself. *)
Lemma recorded_series_strictly_increasing : forall (t : nat -> R) i j,
  (forall k, sample_time t k < sample_time t (S k)) ->
  (i <= j)%nat ->
  sample_time t i < sample_time t (S j).
Proof.
  intros t i j Hstep.
  unfold sample_time in *.
  induction j as [|j' IH]; intros Hle.
  - assert (Hi0 : (i = 0)%nat) by lia.
    rewrite Hi0. apply Hstep.
  - destruct (Nat.le_gt_cases i j') as [Hc|Hc].
    + assert (IH' := IH Hc).
      assert (Ha := Hstep j').
      assert (Hb := Hstep (S j')).
      lra.
    + assert (Hij : (i = S j')%nat) by lia.
      rewrite Hij. apply Hstep.
Qed.

(* T2 -- the writer's append guard preserves the recorded order: storing one
   more sample strictly later than the previous last one keeps every earlier
   sample strictly before it. *)
Lemma append_guard_preserves_order : forall (t : nat -> R) i j,
  sample_time t i < sample_time t j ->
  sample_time t j < sample_time t (S j) ->
  sample_time t i < sample_time t (S j).
Proof.
  intros t i j Hij Hjk.
  unfold sample_time in *.
  lra.
Qed.
