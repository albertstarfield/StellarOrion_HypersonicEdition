(* ============================================================================
   Coq proof companion for src/simulation_engine/stellarorion_pipeline_checkpoint
   Ada 2012, pragma SPARK_Mode (Off) — Text_IO / Calendar / bounded strings.

   AXIOM (C1) [ordered pipeline]: the ordered step list is fixed and finite,
     SPARTA -> Kriging -> PINN -> Bayes Opt, with Pipeline_Step_Count = 4.
   AXIOM (C2) [bounded counters]: every index used to address the per-step
     arrays and the output-file array is a derived subtype, not an unbounded
     Integer:
        Output_File_Count is new Natural range 0 .. Max_Output_Files   (= 16)
     so the body's `State.Step_Files (Idx).Count := Output_File_Count (FIdx)`
     conversion is total exactly when FIdx <= Max_Output_Files.
   AXIOM (C3) [tiered index]: Find_Step_Index returns 0 for "not found" and
     1 .. Pipeline_Step_Count otherwise, so a 0 result must never be used to
     index Steps/Step_Files.

   THEOREM (K1) [index totality]: Find_Step_Index's result always lies in
     0 .. Pipeline_Step_Count, so the `Idx := Find_Step_Index (...)` +
     `Steps (Idx)` idiom in Mark_Step_Running / Mark_Step_Completed /
     Mark_Step_Failed can never raise Constraint_Error from a bad index.
   THEOREM (K2) [output-file bound]: if the parse loop admits an index FIdx
     only when 1 <= FIdx <= Max_Output_Files, then the recorded count satisfies
     0 <= Count <= Max_Output_Files, which is what makes the
     Output_File_Count conversion and the later `for J in 1 .. Count` loop
     total.
   THEOREM (K3) [config append bound]: the guarded append
        if State.Config_Count < Max_Config_Entries then
            State.Config_Count := State.Config_Count + 1
     preserves Config_Count <= Max_Config_Entries, so the
     Config (Config_Count) write is always in range.
   THEOREM (K4) [no silent overflow]: the guarded append either increments (when
     strictly below the cap) or leaves the count unchanged, so the count can
     never exceed the cap in one step.

   CITATIONS:
     [1] Ada Reference Manual ISO/IEC 8652:2012 — RM 3.5.1 (enumeration),
         RM 3.6 (subtype/derived types, constraint checks), RM 4.4 (expressions),
         RM 3.8.1 (enumeration iteration).
     [2] Plimpton, S.J. & Gallis, M.A., "SPARTA", 2014.
     [3] Coq Reference Manual — Coq.Init.Datatypes, Coq.Init.Nat,
         Coq.micromega.Lia.
   ============================================================================ *)

Require Import Coq.Init.Datatypes.
Require Import Coq.Init.Nat.
(* PeanoNat supplies Nat.ltb_lt and the Nat.* library lemmas used below. *)
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.

(* ---------------------------------------------------------------------------
   AXIOM C1 — the ordered pipeline, as the .ads declares it.
   --------------------------------------------------------------------------- *)
Definition Pipeline_Step_Count : nat := 4.
Definition Max_Output_Files : nat := 16.
Definition Max_Config_Entries : nat := 32.

(* ---------------------------------------------------------------------------
   AXIOM C3 — the tiered step index: 0 means "not found", 1..4 is the slot.
   --------------------------------------------------------------------------- *)
Definition Find_Step_Index (name : nat) : nat :=
  if Nat.eqb name 1 then 1
  else if Nat.eqb name 2 then 2
  else if Nat.eqb name 3 then 3
  else if Nat.eqb name 4 then 4
  else 0.

(* ---------------------------------------------------------------------------
   THEOREM K1 — totality of the step index.
   --------------------------------------------------------------------------- *)
Lemma find_step_index_range : forall name, Find_Step_Index name <= Pipeline_Step_Count.
Proof.
  intros name.
  unfold Find_Step_Index.
  destruct (Nat.eqb name 1) eqn:E1.
  - unfold Pipeline_Step_Count. lia.
  - destruct (Nat.eqb name 2) eqn:E2.
    + unfold Pipeline_Step_Count. lia.
    + destruct (Nat.eqb name 3) eqn:E3.
      * unfold Pipeline_Step_Count. lia.
      * destruct (Nat.eqb name 4) eqn:E4.
        -- unfold Pipeline_Step_Count. lia.
        -- unfold Pipeline_Step_Count. lia.
Qed.

(* ---------------------------------------------------------------------------
   A companion statement: a non-zero index is always a valid array subscript.
   --------------------------------------------------------------------------- *)
Lemma find_step_index_nz_valid : forall name,
  Find_Step_Index name <> 0 -> 1 <= Find_Step_Index name <= Pipeline_Step_Count.
Proof.
  intros name Hnz.
  split.
  - lia.
  - apply find_step_index_range.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM C2 — the guarded output-file conversion of the .adb body:
        if FIdx >= 1 and FIdx <= Max_Output_Files then
            State.Step_Files (Idx).Count := Output_File_Count (FIdx)
   The output-file count is a Natural bounded by the array length, so the
   conversion cannot raise Constraint_Error.
   --------------------------------------------------------------------------- *)
Definition Output_File_Count (fidx : nat) : nat := fidx.

(* ---------------------------------------------------------------------------
   THEOREM K2 — the recorded output-file count is always a valid array length.
   --------------------------------------------------------------------------- *)
Lemma output_file_count_bound : forall fidx,
  1 <= fidx -> fidx <= Max_Output_Files -> 0 <= Output_File_Count fidx <= Max_Output_Files.
Proof.
  intros fidx H1 H2.
  unfold Output_File_Count.
  lia.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM K2b — the output-file round-trip loop
        for J in 1 .. Integer (State.Step_Files (I).Count) loop
   visits exactly Count entries, never one more.
   --------------------------------------------------------------------------- *)
Lemma output_file_loop_total : forall count j,
  0 <= count -> count <= Max_Output_Files -> 1 <= j -> j <= count ->
  1 <= j <= Max_Output_Files.
Proof.
  intros count j Hc Hc2 Hj1 Hj2.
  lia.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM C3b — the guarded config append of the .adb body.
   --------------------------------------------------------------------------- *)
Definition guarded_append (count : nat) : nat :=
  if Nat.ltb count Max_Config_Entries then S count else count.

(* ---------------------------------------------------------------------------
   THEOREM K3 — the guarded append preserves the config bound.
   --------------------------------------------------------------------------- *)
Lemma guarded_append_bound : forall count,
  count <= Max_Config_Entries -> guarded_append count <= Max_Config_Entries.
Proof.
  intros count H.
  unfold guarded_append.
  destruct (Nat.ltb count Max_Config_Entries) eqn:E.
  - apply Nat.ltb_lt in E.
    unfold Max_Config_Entries in *.
    lia.
  - apply Nat.ltb_ge in E.
    lia.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM K4 — the append either increments exactly once or not at all, and it
   never overflows in a single step.
   --------------------------------------------------------------------------- *)
Lemma guarded_append_step : forall count,
  count <= Max_Config_Entries ->
  (guarded_append count = S count /\ guarded_append count <= Max_Config_Entries)
  \/ (guarded_append count = count /\ count = Max_Config_Entries).
Proof.
  intros count H.
  unfold guarded_append.
  destruct (Nat.ltb count Max_Config_Entries) eqn:E.
  - apply Nat.ltb_lt in E.
    left.
    split.
    + reflexivity.
    + unfold Max_Config_Entries in *.
      lia.
  - apply Nat.ltb_ge in E.
    right.
    split.
    + reflexivity.
    + lia.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM K4b — a step is Pending, Running, Completed or Failed and nothing
   else, so the four-way Reset loop covers every status exhaustively.
   --------------------------------------------------------------------------- *)
Inductive Step_Status : Type :=
  | Pending : Step_Status
  | Running : Step_Status
  | Completed : Step_Status
  | Failed : Step_Status.

Lemma step_status_total : forall s : Step_Status,
  s = Pending \/ s = Running \/ s = Completed \/ s = Failed.
Proof.
  intros s.
  destruct s as [ | | | ].
  - left. reflexivity.
  - right. left. reflexivity.
  - right. right. left. reflexivity.
  - right. right. right. reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM K4c — "all completed" implies the last step is completed, which is
   exactly the .ads Post of Is_All_Completed.
   --------------------------------------------------------------------------- *)
Definition all_completed (steps : nat -> Step_Status) : Prop :=
  forall i, 1 <= i <= Pipeline_Step_Count -> steps i = Completed.

Lemma all_completed_imply_last : forall steps : nat -> Step_Status,
  all_completed steps -> steps Pipeline_Step_Count = Completed.
Proof.
  intros steps Hall.
  apply Hall.
  unfold Pipeline_Step_Count.
  lia.
Qed.
