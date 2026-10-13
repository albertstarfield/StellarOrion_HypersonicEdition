(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_test_modes (CLI test/demo modes)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_test_modes.adb
              F6   (float formatter, lines 45-105; DP clamp 73-75)
              Grade (tolerance grader, lines 116-147; bands 126-132)
            src/simulation_engine/stellarorion_test_modes.ads
              F6   (line 120)
              Grade (line 124)

   Goal  : Each mode reports PASS/FAIL honestly against IRVE-3 targets; F6
           formatting never overflows.

   AXIOMS
   A1. Grade partitions the non-negative comparison error into three bands
         Error <= Tol          -> PASS
         Error <= 2 * Tol      -> WARN
         otherwise             -> FAIL
       [Reference: test_modes.ads:124; test_modes.adb:116-132]
   A2. F6 formats |V| into an integer part and a two-digit decimal part DP that
       is explicitly clamped to the closed range 0 .. 99:
         (if Raw < 0 then 0 elsif Raw > 99 then 99 else Raw)
       [Reference: test_modes.adb:73-75]

   THEORIES
   T1. The grade rank is one of exactly three values {0, 1, 2} (range-bounded
       finite enumeration): a mode verdict is always a well-defined grade.
   T2. Grade is honest: the PASS verdict is selected if and only if
       Error <= Tol -- the strict first band boundary.
   T3. The F6 decimal digit, after clamping, is always within 0 .. 99: the
       formatter's integer digit pair can never overflow its two-digit field.

   APPLICATIONS
   Run_CompareNoses / Run_Test_Sample print PASS/WARN/FAIL verdicts against
   IRVE-3 tolerances and print metric values through F6; T2 guarantees the
   verdict matches the numeric error, T3 guarantees the printed decimal field
   stays in range.

   CITATIONS
   Montgomery D.C. (2017), "Design and Analysis of Experiments", 9th ed.
   Roache P.J. (1994), "Verification and Validation in Computational Science".
   NASA/TP-2013-4012 (IRVE-3 MDAO comparison methodology).
   Ada Reference Manual (2012), RM 4.10 (numeric formatting).

   VERIFICATION: every lemma below is discharged by `Qed`; nothing is
   admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Export Coq.micromega.Lia.
Require Export Coq.micromega.Lra.

Open Scope R_scope.

(* A1 -- the grade classifier as a rank; mirrors the if/elsif/else chain
      (test_modes.adb:126-132).  0 = PASS, 1 = WARN, 2 = FAIL. *)
Definition grade_rank (error tol : R) : nat :=
   if Rle_lt_dec error tol then 0
   else if Rle_lt_dec error (2 * tol) then 1 else 2.

(* T1 -- the grade is always one of three finite values. *)
Lemma grade_rank_bounded : forall error tol, (grade_rank error tol <= 2)%nat.
Proof.
   intros error tol.
   unfold grade_rank.
   destruct (Rle_lt_dec error tol) as [H | H].
   - clear H. lia.
   - destruct (Rle_lt_dec error (2 * tol)) as [H2 | H2].
     + clear H; clear H2. lia.
     + clear H; clear H2. lia.
Qed.

(* T2 -- the PASS verdict is emitted if and only if Error <= Tol. *)
(* `grade_rank` returns a nat, so the equality against 0 must be read in
   nat_scope -- the file is R_scope, where a bare `0` would elaborate as R. *)
Lemma grade_pass_sound : forall error tol, (grade_rank error tol = 0)%nat <-> error <= tol.
Proof.
   intros error tol.
   unfold grade_rank.
   destruct (Rle_lt_dec error tol) as [H | H].
   - split.
     + intros _. exact H.
     + intros _. reflexivity.
   - split.
     + intros Hg. exfalso.
       destruct (Rle_lt_dec error (2 * tol)) as [H2 | H2];
         clear H2; clear H; simpl in Hg; lia.
     + intros He. exfalso. lra.
Qed.

(* A2 -- the F6 decimal clamp (test_modes.adb:73-75). *)
Definition clamp_dp (raw : R) : R :=
   if Rle_lt_dec 0 raw then (if Rle_lt_dec raw 99 then raw else 99) else 0.

(* T3a -- the clamped decimal digit is non-negative. *)
Lemma clamp_dp_lower : forall raw, 0 <= clamp_dp raw.
Proof.
   intros raw.
   unfold clamp_dp.
   destruct (Rle_lt_dec 0 raw) as [H | H].
   - destruct (Rle_lt_dec raw 99) as [H2 | H2]; lra.
   - lra.
Qed.

(* T3b -- the clamped decimal digit never exceeds the two-digit field. *)
Lemma clamp_dp_upper : forall raw, clamp_dp raw <= 99.
Proof.
   intros raw.
   unfold clamp_dp.
   destruct (Rle_lt_dec 0 raw) as [H | H].
   - destruct (Rle_lt_dec raw 99) as [H2 | H2]; lra.
   - lra.
Qed.
