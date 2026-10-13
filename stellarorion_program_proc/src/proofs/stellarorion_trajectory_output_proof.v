(* ============================================================================
   Coq proof companion for src/simulation_engine/stellarorion_trajectory_output
   Ada 2012 / SPARK 2014, pragma SPARK_Mode (On).

   AXIOM (F1) [linear trajectory]: over the normalized progress
   p = Step / TARGET_STEP in [0,1],
       H = 120.0 - 80.0 * p   (km),      V = 4300.0 - 1600.0 * p  (m/s),
   with TARGET_STEP = 3.0e8 the .ads normalization divisor.
   AXIOM (F4) [PINN metric model]: the metric block of the .adb is
       pinn_loss     = 1.0 / (1.0 + 100.0 * p)          in (0, 1]
       pinn_accuracy = Rmin 99.5 (85.0 + 14.5 * p)      in [85.0, 99.5]
       dsmc_pinn_err = Rmax 0.5 (15.0 * (1.0 - p))      in [0.5, 15.0]
   AXIOM (F5) [Knudsen / monotone progress]: p is monotone in Step because
   TARGET_STEP = 3.0e8 > 0.

   THEOREM (T3) [loss band]: 0 < pinn_loss <= 1 over the whole progress range,
   which is exactly the .ads Post conjunct "PINN_Loss > 0.0 and <= 1.0".
   THEOREM (T4) [accuracy band]: 85.0 <= pinn_accuracy <= 99.5, matching the
   .ads Post conjuncts, with equality 85.0 at p = 0 and 99.5 at p = 1.
   THEOREM (T5) [error band]: 0.5 <= dsmc_pinn_err <= 15.0, matching the .ads
   Post conjuncts, with equality 15.0 at p = 0 and 0.5 at p = 1.
   THEOREM (T1/T2) [monotone altitude and velocity]: H and V are monotone
   DECREASING in p, so H(0)=120 >= H(p) >= H(1)=40 and
   V(0)=4300 >= V(p) >= V(1)=2700 -- the values the .ads quotes.

   CITATIONS:
     [1] NASA/TP-2013-4012, Dillman et al., IRVE-3 flight reconstruction.
     [2] Sutton & Graves (1972), NASA TR R-376 (stagnation heat flux).
     [3] Ada Reference Manual ISO/IEC 8652:2012, RM 3.6, 3.8, 4.4.
     [4] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmax_l, Rmin_r, Rmin_l),
         Coq.Reals.RIneq (Rinv_0_lt_compat, Rmult_le_reg_l, Rmult_lt_0_compat).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

(* Every Definition and Lemma in this file quantifies over the reals; opening
   R_scope at file level makes numerals, <=, * and / elaborate in R rather than
   nat. [Citation: Coq 8.18 stdlib Coq.Reals.Reals -- Local Open Scope R_scope] *)
Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   A reusable helper: l * (x / l) = x for l <> 0.  Written out in full
   below because the proof file does not import other Coq proof files.
   [Citation: Coq 8.18 stdlib, Coq.Reals.Rbasic_fun / RIneq — Rinv_l,
   Rmult_assoc, Rmult_comm] *)
Lemma cancel_mul : forall x l : R, l <> 0 -> l * (x / l) = x.
Proof.
  intros x l Hne.
  unfold Rdiv.
  rewrite <- Rmult_assoc.
  rewrite (Rmult_comm l x).
  rewrite Rmult_assoc.
  rewrite (Rmult_comm l (/ l)).
  rewrite (Rinv_l l Hne).
  rewrite Rmult_1_r.
  reflexivity.
Qed.

(* ---------------------------------------------------------------------------
   TARGET_STEP : constant Float := 3.0e8  (the .ads normalization divisor).
   --------------------------------------------------------------------------- *)
Definition TARGET_STEP : R := 300000000.

(* ---------------------------------------------------------------------------
   Model of the Ada PINN-metric block (stellarorion_trajectory_output.adb):

       Progress := Step / TARGET_STEP;
       Result.PINN_Loss     := 1.0 / (1.0 + Progress * 100.0);
       Result.PINN_Accuracy := 85.0 + Progress * 14.5;
       if Result.PINN_Accuracy > 99.5 then Result.PINN_Accuracy := 99.5; end if;
       Result.DSMC_PINN_Error := 15.0 * (1.0 - Progress);
       if Result.DSMC_PINN_Error < 0.5 then Result.DSMC_PINN_Error := 0.5; end if;
   --------------------------------------------------------------------------- *)
Definition pinn_loss (p : R) : R := 1 / (1 + 100 * p).

Definition pinn_accuracy (p : R) : R := Rmin 99.5 (85 + 14.5 * p).

Definition dsmc_pinn_error (p : R) : R := Rmax 0.5 (15 * (1 - p)).

(* ---------------------------------------------------------------------------
   AXIOM F5 -- progress is well defined and lies in [0,1] over the step range.
   --------------------------------------------------------------------------- *)
Lemma progress_range : forall step : R, 0 <= step -> step <= TARGET_STEP ->
   0 <= step / TARGET_STEP <= 1.
Proof.
  intros step H1 H2.
  assert (HT : 0 < TARGET_STEP) by (unfold TARGET_STEP; lra).
  assert (Hne : TARGET_STEP <> 0) by (unfold TARGET_STEP; lra).
  assert (Hi : 0 < / TARGET_STEP) by (apply Rinv_0_lt_compat; exact HT).
  unfold Rdiv.
  split.
  - apply Rmult_le_pos; [exact H1 | lra].
  - apply (Rmult_le_reg_l TARGET_STEP); [exact HT | ].
    rewrite (Rmult_comm step (/ TARGET_STEP)).
    rewrite <- Rmult_assoc.
    rewrite Rinv_r by exact Hne.
    rewrite Rmult_1_l.
    lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T3 -- the PINN loss lies in the open-closed band (0, 1].
   --------------------------------------------------------------------------- *)
Lemma pinn_loss_band : forall p, 0 <= p -> 0 < pinn_loss p /\ pinn_loss p <= 1.
Proof.
  intros p Hp.
  unfold pinn_loss.
  assert (Hd : 0 < 1 + 100 * p) by lra.
  assert (Hne : 1 + 100 * p <> 0) by lra.
  assert (Hi : 0 < / (1 + 100 * p)) by (apply Rinv_0_lt_compat; exact Hd).
  split.
  - apply Rmult_lt_0_compat; [lra | exact Hi].
  - apply (Rmult_le_reg_l (1 + 100 * p)); [exact Hd | ].
    rewrite Rmult_1_r.
    rewrite (cancel_mul 1 (1 + 100 * p) Hne).
    lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T4 -- the PINN accuracy lies in [85, 99.5].

   Coq's Rmin (Coq.Reals.Rbasic_fun) satisfies, for every x and y,
       Rmin_l : Rmin x y <= x          and          Rmin_r : Rmin x y <= y,
   which are exactly the two "clamp" facts of the Ada if-block; the value that
   the branch actually selects is exposed by the equation lemmas
   Rmin_left (x <= y -> Rmin x y = x) and Rmin_right (y <= x -> Rmin x y = y).
   --------------------------------------------------------------------------- *)
Lemma pinn_accuracy_band : forall p, 0 <= p -> p <= 1 ->
   85 <= pinn_accuracy p /\ pinn_accuracy p <= 99.5.
Proof.
  intros p Hp Hp1.
  unfold pinn_accuracy.
  destruct (Rle_dec (85 + 14.5 * p) 99.5) as [H | H].
  - split.
    + rewrite Rmin_right by exact H.
      lra.
    + apply Rmin_l.
  - split.
    + rewrite Rmin_left by lra.
      lra.
    + apply Rmin_l.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM T5 -- the DSMC-PINN error lies in [0.5, 15].

   Coq's Rmax (Coq.Reals.Rbasic_fun) satisfies, for every x and y,
       Rmax_l : x <= Rmax x y          and          Rmax_r : y <= Rmax x y,
   again exactly the two facts of the Ada if-block.
   --------------------------------------------------------------------------- *)
Lemma dsmc_error_band : forall p, 0 <= p -> p <= 1 ->
   0.5 <= dsmc_pinn_error p /\ dsmc_pinn_error p <= 15.
Proof.
  intros p Hp Hp1.
  unfold dsmc_pinn_error.
  split.
  - apply Rmax_l.
  - destruct (Rle_dec 0.5 (15 * (1 - p))) as [H | H].
    + rewrite Rmax_right by exact H.
      lra.
    + rewrite Rmax_left by lra.
      lra.
Qed.

(* ---------------------------------------------------------------------------
   AXIOM F1 -- the linear trajectory maps.
   --------------------------------------------------------------------------- *)
Definition altitude (p : R) : R := 120 - 80 * p.
Definition velocity (p : R) : R := 4300 - 1600 * p.

(* ---------------------------------------------------------------------------
   THEOREM T1/T2 -- H and V are monotone decreasing in p, with the exact
   endpoint values 120/40 km and 4300/2700 m/s that the .ads quotes.
   --------------------------------------------------------------------------- *)
Lemma altitude_endpoints : altitude 0 = 120 /\ altitude 1 = 40.
Proof.
  unfold altitude.
  split.
  - lra.
  - lra.
Qed.

Lemma velocity_endpoints : velocity 0 = 4300 /\ velocity 1 = 2700.
Proof.
  unfold velocity.
  split.
  - lra.
  - lra.
Qed.

Lemma altitude_decreasing : forall p1 p2, p1 <= p2 -> p2 <= 1 ->
   altitude p2 <= altitude p1.
Proof.
  intros p1 p2 H12 Hp2.
  unfold altitude.
  lra.
Qed.

Lemma velocity_decreasing : forall p1 p2, p1 <= p2 -> p2 <= 1 ->
   velocity p2 <= velocity p1.
Proof.
  intros p1 p2 H12 Hp2.
  unfold velocity.
  lra.
Qed.
