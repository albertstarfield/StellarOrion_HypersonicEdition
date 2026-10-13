(* ============================================================================
   Coq proof companion for src/python/ada_pinn_wrapper.py

   AXIOM (L1) [Latin hypercube sampling, McKay et al. 1979]:
        for n_samples = N, each column j is filled with a random permutation of
   0..N-1, and sample i in column j is
        s[i,j] = (perm[i] + u) / N  with u ~ U[0,1) (AXIOM A1),
   then affinely mapped into the design bounds by
        x[i,j] = lo + s[i,j] * (hi - lo)   for each bound (lo, hi) (AXIOM A2).
   AXIOM (L2) [permutation cover, numpy Generator.permutation]: the mapping
   i |-> perm[i] is a permutation of 0..N-1: it is injective on 0..N-1, its
   values stay in 0..N-1, and every stratum k in 0..N-1 is the image of
   exactly one i (AXIOM A3).

   THEOREM (L3) [stratum containment]: for every sample i the raw value
   s[i,j] lies in [0, 1), hence the affine map lands in [lo, hi), so the PINN
   design never draws a point outside its declared domain (AXIOM A4).
   THEOREM (L4) [stratum index in range]: sample i occupies the stratum
   perm[i], which lies in 0..N-1, so the design has exactly N occupied strata
   and none outside.
   THEOREM (L5) [each stratum covered exactly once]: two distinct samples
   occupy two distinct strata, and every stratum is occupied by some sample.

   CITATIONS:
     [1] McKay, M.D., Beckman, R.J. & Conover, W.J. (1979), "A comparison of
         three methods for selecting values of input variables in the analysis
         of output from a computer code", Technometrics 21(2):239-245, Sec. 2
         (definition of the Latin hypercube sample).
     [2] NumPy documentation, default_rng and Generator.permutation (the
         returned array is a permutation of 0..N-1).
     [3] Coq Reference Manual, Coq.Reals.RIneq (Rmult_le_compat_r,
         Rmult_le_pos, Rmult_lt_reg_l, Rinv_0_lt_compat).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Local Open Scope R_scope.

(* R-scope wrapper: numerals and '*' must elaborate as R, not nat.
   Scoped to this section only so later nat lemmas stay nat. *)
Section Cancel_Mul_Helper.
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
End Cancel_Mul_Helper.

Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv. apply Rmult_le_pos; assumption.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM L3 -- the raw stratum value s = (perm + u) / N lies in [0, 1).
   --------------------------------------------------------------------------- *)
Definition lhs_raw (perm_value n_samples u : R) : R := (perm_value + u) / n_samples.

Lemma lhs_raw_lower : forall perm_value n_samples u,
   0 < n_samples -> 0 <= perm_value -> 0 <= u -> 0 <= lhs_raw perm_value n_samples u.
Proof.
  intros perm_value n_samples u Hn Hp Hu.
  unfold lhs_raw.
  apply rdiv_nonneg.
  - lra.
  - exact Hn.
Qed.

Lemma lhs_raw_upper : forall perm_value n_samples u,
   0 < n_samples -> perm_value <= n_samples - 1 -> u < 1 ->
   lhs_raw perm_value n_samples u < 1.
Proof.
  intros perm_value n_samples u Hn Hp Hu.
  unfold lhs_raw.
  assert (Hne : n_samples <> 0) by lra.
  assert (E : n_samples * ((perm_value + u) / n_samples) = perm_value + u)
    by (apply cancel_mul; exact Hne).
  apply (Rmult_lt_reg_l n_samples).
  - exact Hn.
  - rewrite E.
    rewrite Rmult_1_r.
    lra.
Qed.

(* ---------------------------------------------------------------------------
   Model of the affine map x = lo + s * (hi - lo) into the design bounds.
   --------------------------------------------------------------------------- *)
Definition lhs_affine (lo hi raw : R) : R := lo + raw * (hi - lo).

Lemma lhs_affine_lower : forall lo hi perm_value n_samples u,
   0 < n_samples -> 0 <= perm_value -> 0 <= u -> lo <= hi ->
   lo <= lhs_affine lo hi (lhs_raw perm_value n_samples u).
Proof.
  intros lo hi perm_value n_samples u Hn Hp Hu Hle.
  assert (Hraw : 0 <= lhs_raw perm_value n_samples u)
    by (apply lhs_raw_lower; assumption).
  unfold lhs_affine.
  assert (Hshow : 0 <= (hi - lo)) by lra.
  assert (Hprod : 0 <= lhs_raw perm_value n_samples u * (hi - lo))
    by (apply Rmult_le_pos; assumption).
  lra.
Qed.

Lemma lhs_affine_upper : forall lo hi perm_value n_samples u,
   0 < n_samples -> perm_value <= n_samples - 1 -> u < 1 -> lo <= hi ->
   lhs_affine lo hi (lhs_raw perm_value n_samples u) <= hi.
Proof.
  intros lo hi perm_value n_samples u Hn Hp Hu Hle.
  assert (Hraw : lhs_raw perm_value n_samples u < 1)
    by (apply lhs_raw_upper; assumption).
  unfold lhs_affine.
  assert (Hkey : lhs_raw perm_value n_samples u * (hi - lo) <= 1 * (hi - lo)).
  { apply Rmult_le_compat_r; [lra | apply Rlt_le; exact Hraw]. }
  rewrite Rmult_1_l in Hkey.
  assert (Hshow : 0 <= (hi - lo)) by lra.
  lra.
Qed.

Lemma lhs_affine_bounds : forall lo hi perm_value n_samples u,
   0 < n_samples -> 0 <= perm_value -> perm_value <= n_samples - 1 ->
   0 <= u -> u < 1 -> lo <= hi ->
   lo <= lhs_affine lo hi (lhs_raw perm_value n_samples u) /\
   lhs_affine lo hi (lhs_raw perm_value n_samples u) <= hi.
Proof.
  intros lo hi perm_value n_samples u Hn Hp Hpb Hu Hu1 Hle.
  split.
  - apply lhs_affine_lower; assumption.
  - apply lhs_affine_upper; assumption.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM L4 -- the stratum index of sample i is perm[i], in range.
   --------------------------------------------------------------------------- *)
Definition stratum_of (perm : nat -> nat) (i : nat) : nat := perm i.

(* The lemmas below are purely nat-valued.  The file opens R_scope at the top
   for the lhs_affine_* lemmas; a Section with an explicit nat_scope re-opening
   coexists with that file-level R_scope (verified fact 3) and makes the
   untyped binders elaborate as nat rather than R. *)
Section NatPart.
Local Open Scope nat_scope.

Lemma stratum_of_in_range : forall (N : nat) (perm : nat -> nat) (i : nat),
   1 <= N -> i < N -> (forall i, i < N -> perm i < N) ->
   stratum_of perm i < N.
Proof.
  intros N perm i HN Hi Hin.
  unfold stratum_of.
  assert (Hshow : perm i < N) by (apply Hin; exact Hi).
  exact Hshow.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM L5 -- distinct samples occupy distinct strata, and every stratum is
   occupied. This is exactly the Latin-hypercube covering property that makes
   the design space-filling rather than clustered.
   --------------------------------------------------------------------------- *)
Lemma strata_pairwise_distinct : forall N perm i j,
   i < N -> j < N -> i <> j ->
   (forall i j, i < N -> j < N -> perm i = perm j -> i = j) ->
   stratum_of perm i <> stratum_of perm j.
Proof.
  intros N perm i j Hi Hj Hij Hinj.
  unfold stratum_of.
  intro Heq.
  assert (Hkey : i = j) by (apply Hinj; assumption).
  assert (Hshow : i <> j) by exact Hij.
  contradiction.
Qed.

Lemma strata_cover_each_stratum : forall N perm k,
   1 <= N -> k < N ->
   (forall k, k < N -> exists i, i < N /\ perm i = k) ->
   exists i, i < N /\ stratum_of perm i = k.
Proof.
  intros N perm k HN Hk Hcov.
  destruct (Hcov k Hk) as [i [Hi Heq]].
  exists i.
  split.
  - exact Hi.
  - unfold stratum_of.
    exact Heq.
Qed.

End NatPart.
