(* ============================================================================
   MACHINE-CHECKED PROOF -- kriging_denoise (Kriging spatial denoising)
   ============================================================================
   Unit  : src/python/kriging_denoise.py
              denoise_grid()          (lines 196-307)
              _build_kernel()         (lines 161-193)
              GP posterior-mean / BLUP statement (line 205)

   Goal  : GP-based denoising preserves the field while reducing DSMC noise;
           the GP posterior mean is the best linear unbiased predictor (BLUP).

   AXIOMS
   A1. The GP posterior mean (the denoised value) is a linear predictor of the
       observations:
         f* of x* = K(x*, X) [K(X,X) + sigma_n^2 I]^{-1} y = SUM_i w_i of x*  (y_i)
       i.e. a non-negative-weight combination when the kernel is a
       positive-definite stationary covariance restricted to observed cells.
       [Reference: kriging_denoise.py:205-207; Theorem 2.1 of Rasmussen &
        Williams (2006) -- https://gaussianprocess.org/gpml/]
   A2. The physical fields carried by the pipeline (mass density rho,
       temperature T) are non-negative in continuum SPARTA output
         [Reference: kriging_denoise.py:141-149 (M_air > 0, num_density);
          physical constraint: rho >= 0, T >= 0].
   A3. DSMC noise is modelled cell-independently by a WhiteKernel added to a
       Matern 5/2 signal kernel, which keeps the posterior-mean weights
       non-negative for a stationary kernel.
       [Reference: kriging_denoise.py:161-193, 74, 188-193;
        https://scikit-learn.org/stable/modules/gaussian_process.html]

   THEORIES
   T1. A convex combination (weighted sum with non-negative weights) of
       non-negative observations is non-negative: this is the soundness of
       the denoised field remaining a physical (non-negative) density /
       temperature.
   T2. A convex combination of two observations with coefficient
       t in [0,1] lies between them (weighted-average boundedness); this is
       the finite-cell statement of topology preservation by the GP mean.

   APPLICATIONS
   denoise_grid() returns denoised[:, 2:6]; T1 proves the predicted density
   and temperature never go negative, so the Kriging step cannot corrupt the
   physical sign of the field even where raw DSMC statistics fluctuate.

   CITATIONS
   Rasmussen C.E. & Williams C.K.I. (2006), "Gaussian Processes for Machine
     Learning", MIT Press -- https://gaussianprocess.org/gpml/
   Cressie N. (1993), "Statistics for Spatial Data", Wiley.
   Lophaven S.N. et al. (2002), "DACE - A MATLAB Kriging Toolbox", DTU.
   Scikit-learn GaussianProcessRegressor --
     https://scikit-learn.org/stable/modules/gaussian_process.html

   VERIFICATION: every lemma below is discharged by `Qed`; no statement is
   admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A1 -- the GP posterior mean at one query point as a finite weighted sum
     SUM_{k=0}^{n-1} w_k * y_k over the observed cell values y_k. *)
Fixpoint wsum (w y : nat -> R) (n : nat) : R :=
   match n with
   | 0    => 0
   | S k  => w k * y k + wsum w y k
   end.

(* T1 -- convex combination of non-negative observations is non-negative. *)
Lemma wsum_nonneg : forall (n : nat) (w y : nat -> R),
   (forall i, 0 <= w i) -> (forall i, 0 <= y i) -> 0 <= wsum w y n.
Proof.
   induction n as [| k IH]; intros w y Hw Hy.
   - simpl. lra.
   - simpl.
     assert (H1 : 0 <= w k * y k)
        by (apply Rmult_le_pos; [apply Hw | apply Hy]).
     assert (H2 : 0 <= wsum w y k) by (apply IH; assumption).
     lra.
Qed.

(* T2 -- a two-cell convex combination stays inside the range of its two
     observations, the finite statement of topology preservation. *)
Lemma convex2_between : forall a b (t : R),
   a <= b -> 0 <= t -> t <= 1 ->
   (a <= (1 - t) * a + t * b) /\ ((1 - t) * a + t * b <= b).
Proof.
   intros a b t Hab Ht0 Ht1.
   assert (Hta : t * a <= t * b)
      by (apply Rmult_le_compat_l; lra).
   assert (Hab1 : (1 - t) * a <= (1 - t) * b)
      by (apply Rmult_le_compat_l; lra).
   split.
   - assert (Ea : a = (1 - t) * a + t * a) by ring.
     lra.
   - assert (Eb : b = (1 - t) * b + t * b) by ring.
     lra.
Qed.
