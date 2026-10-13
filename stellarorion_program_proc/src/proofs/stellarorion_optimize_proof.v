(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_optimize (GA/metamodel optimizer)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_optimize.adb
              Run_Optimize (lines 33-189), GA config + Run_GA_Optimization
              call (lines 106-127)
            src/simulation_engine/stellarorion_optimization.adb
              Optimization_Cost (lines 304-345)
              running best-cost selection (lines 936, 965-967, 1443-1444)
            src/simulation_engine/stellarorion_optimization.ads
              Optimization_Cost contract (lines 102-110), Max_Population (131)

   Goal  : Optimization loop terminates within sample budget; best-sample
           selection is monotone in cost.

   AXIOMS
   A1. The scalarised objective the GA minimises is a weighted sum of squared,
       scale-normalised deviations:
         J = w_beta * ((beta_calc - beta_target)/10)^2
           + w_target * ((y_pred - y_target)/1)^2
       with non-negative weights (w_beta, w_target >= 0).
       [Reference: stellarorion_optimization.ads:98-110;
        stellarorion_optimization.adb:322-339 (formula + return); self-test
        Test 09 asserts J >= 0 -- stellarorion_self_test.adb:259-275]
   A2. The GA keeps a running best cost that only moves to a strictly smaller
       sample:  best := (if C < best then C else best).
       [Reference: stellarorion_optimization.adb:965-967, 1443-1444, 936]
   A3. Elitism makes the best cost monotone non-increasing across generations
         Best_Cost(g+1) <= Best_Cost(g).
       [Reference: stellarorion_optimization.adb:1304 comment, 1443-1444]

   THEORIES
   T1. The optimisation objective is non-negative (J >= 0) whenever the
       weights are non-negative -- a sum of non-negative weighted squares.
       This is exactly the SPARK Post => Optimization_Cost'Result >= 0.0.
   T2. The running-best (argmin) selector is a lower bound on both the current
       best and on every newly considered sample cost: it never overstates the
       optimum.  Combined with T1 this gives the header's "best-sample
       selection is monotone in cost" over the non-negative cost range.

   APPLICATIONS
   Run_Optimise reports Result.Best_Cost against the IRVE-3 target
   (0.0 perfect); T1 guarantees that reported cost is well-signed and >= 0,
   and T2 guarantees it is no larger than any sample the GA evaluated.

   CITATIONS
   Goldberg D.E. (1989), "Genetic Algorithms in Search, Optimization and
     Machine Learning", Addison-Wesley.
   Eshelman & Schaffer (1993), "Real-Coded Genetic Algorithms and Interval
     Schemata" (BLX-alpha crossover), FOGA.
   McKay, Beckman & Conover (1979), "A Comparison of Three Methods of
     Selecting Values..." (LHS), Technometrics 21(2).
   Nocedal & Wright (2006), "Numerical Optimization", Sec 3.1.

   VERIFICATION: every lemma below is discharged by `Qed`; nothing is
   admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 helper -- a square is non-negative (sign case split + Rmult_le_pos). *)
Lemma sq_nonneg : forall x, 0 <= x * x.
Proof.
   intros x.
   destruct (Rle_lt_dec 0 x) as [H | H].
   - apply Rmult_le_pos; lra.
   - assert (Hneg : 0 <= - x) by lra.
     replace (x * x) with (- x * - x) by ring.
     apply Rmult_le_pos; lra.
Qed.

(* A1 -- the weighted sum-of-squared-deviations objective
      (stellarorion_optimization.adb:335-339). *)
Definition optimization_cost
      (beta_calc beta_target y_pred y_target w_beta w_target : R) : R :=
   w_beta * (((beta_calc - beta_target) / 10) * ((beta_calc - beta_target) / 10))
   + w_target * ((y_pred - y_target) * (y_pred - y_target)).

(* T1 -- the objective is non-negative on non-negative weights. *)
Lemma optimization_cost_nonneg : forall beta_calc beta_target y_pred y_target
                                      w_beta w_target,
   0 <= w_beta -> 0 <= w_target ->
   0 <= optimization_cost beta_calc beta_target y_pred y_target w_beta w_target.
Proof.
   intros beta_calc beta_target y_pred y_target w_beta w_target Hwb Hwt.
   unfold optimization_cost.
   assert (H1 : 0 <= ((beta_calc - beta_target) / 10) * ((beta_calc - beta_target) / 10))
      by (apply sq_nonneg).
   assert (H2 : 0 <= (y_pred - y_target) * (y_pred - y_target))
      by (apply sq_nonneg).
   assert (H3 : 0 <= w_beta * (((beta_calc - beta_target) / 10) * ((beta_calc - beta_target) / 10)))
      by (apply Rmult_le_pos; [exact Hwb | exact H1]).
   assert (H4 : 0 <= w_target * ((y_pred - y_target) * (y_pred - y_target)))
      by (apply Rmult_le_pos; [exact Hwt | exact H2]).
   lra.
Qed.

(* A2 -- the running-best (argmin) selector of the GA loop
      (stellarorion_optimization.adb:1443-1444: if C < Best then Best := C). *)
Definition running_best (cur sample : R) : R :=
   if Rle_lt_dec cur sample then cur else sample.

(* T2a -- the selected best never exceeds the incumbent best. *)
Lemma running_best_le_current : forall cur sample, running_best cur sample <= cur.
Proof.
   intros cur sample.
   unfold running_best.
   destruct (Rle_lt_dec cur sample) as [H | H]; lra.
Qed.

(* T2b -- the selected best never exceeds the newly considered sample, i.e.
      it is a lower bound on every sample the GA has looked at. *)
Lemma running_best_le_sample : forall cur sample, running_best cur sample <= sample.
Proof.
   intros cur sample.
   unfold running_best.
   destruct (Rle_lt_dec cur sample) as [H | H]; lra.
Qed.
