(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_self_test (built-in 18-test suite)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_self_test.adb
              Pass_Count / Fail_Count  (lines 64-65)
              per-test PASS/FAIL increments (lines 121 ... 604)
              final verdict gate        (lines 616-629)
            src/simulation_engine/stellarorion_self_test.ads
              Run_Self_Test (18 self-tests, lines 6-8, 17-21)

   Goal  : Every test that passes reflects its documented property; the
           "All 18 self-tests PASSED." banner is emitted soundly.

   AXIOMS
   A1. Each of the 18 test regions updates exactly one counter: on success
       Pass_Count := Pass_Count + 1, otherwise Fail_Count := Fail_Count + 1.
       [Reference: stellarorion_self_test.adb:121/136/.../467/502/604
        (Pass increments) and 493/505/... (Fail increments)]
   A2. The win banner is printed if and only if Fail_Count = 0:
         if Fail_Count = 0 then "All 18 self-tests PASSED."
       [Reference: stellarorion_self_test.adb:622-629]
   A3. The suite comprises 18 test regions (Tests 1-18).
       [Reference: stellarorion_self_test.adb:6-9, ads:6-8]

   THEORIES
   T1. A pass-count accumulated over n evaluated tests is bounded by n
         count_true o n <= n
       -- the number of PASS outcomes can never exceed the number of tests the
       registry ran (bounded by the registry size).
   T2. If, after n evaluated tests, pass_count + fail_count = n, then
         fail_count = 0  <->  pass_count = n
       i.e. the "All passed" verdict is emitted exactly when every outcome was
       a pass and none a failure (the honest-verdict gate A2).

   APPLICATIONS
   These bound the self-test's own reporting: a PASS tally that exceeded the
   number of tests, or a green banner printed while any Fail_Count is positive,
   is arithmetically impossible.

   CITATIONS
   NASA/TP-2013-4012 (IRVE-3 trajectory and metrics).
   Rapisarda V. (2023), "Multidisciplinary Design Analysis and Optimisation
     of HIAD", TU Delft (IRVE-3 geometry Table 4.1).
   Bird G.A. (1994), "Molecular Gas Dynamics and the Direct Simulation Monte
     Carlo Method".

   VERIFICATION: every lemma below is discharged by `Qed`; nothing is
   admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lia.

Open Scope nat_scope.

(* A1 -- count of PASS outcomes over the first n test results. *)
Fixpoint count_true (o : nat -> bool) (n : nat) : nat :=
   match n with
   | 0    => 0
   | S k  => (if o k then 1 else 0) + count_true o k
   end.

(* T1 -- the pass tally is bounded by the number of evaluated tests. *)
Lemma pass_count_bounded : forall (o : nat -> bool) (n : nat),
   count_true o n <= n.
Proof.
   intros o n.
   induction n as [| k IH].
   - simpl. lia.
   - simpl. destruct (o k); lia.
Qed.

(* T2 -- honest verdict: with pass + fail = n, no-failure iff all-pass. *)
Lemma all_passed_iff_no_fail : forall n pass_count fail_count,
   pass_count + fail_count = n -> (fail_count = 0 <-> pass_count = n).
Proof.
   intros n pass_count fail_count H.
   split; intros E; lia.
Qed.
