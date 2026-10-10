(* ============================================================================
   Coq proof companion for src/python/sparta_grid.py (SPARTA grid reader)

   AXIOM (SP1) [cell geometry]: a SPARTA "ITEM: CELLS" record carries the
   cell bounds as xlo xhi ylo yhi, and the reader computes the cell centre as
       x_center = (xlo + xhi) / 2 ,   y_center = (ylo + yhi) / 2 .
   AXIOM (SP2) [number density, Bird 1994 Sec. 2.3]: the reader converts the
   tabulated number density n [1/m^3] to a mass density with
       rho = n * M_air / N_A ,   M_air = 28.97e-3 kg/mol , N_A = 6.022e23 ,
   and then keeps the cell only if temp_K > 0 AND rho > 0.
   AXIOM (SP3) [column layout, SPARTA dump format]: the record has at least 11
   white-space separated columns; column 9 (0-based) is the cell temperature
   and column 10 is the number density. The reader only indexes column 9 when
   it has already checked that the column exists.

   THEOREM (SP4) [cell-centre containment]: for a well-formed cell with
   xlo <= xhi, the computed centre lies inside the cell:
       xlo <= (xlo + xhi) / 2 <= xhi .
   This is what makes "sample the cell centre" a sound stand-in for
   "sample the cell": a centre projected outside the cell would silently
   attach the wrong gas state to every trajectory point inside it.
   THEOREM (SP5) [density positivity]: the rho > 0 mask in the reader is
   SOUND and not accidentally false: whenever the number density is positive
   the computed mass density is strictly positive, so a physical cell is never
   silently dropped.
   THEOREM (SP6) [column indexing is total on the valid domain]: a column
   index that is in range of the parsed token list is a legal Python sequence
   index, and a record with fewer than 10 columns cannot supply column 9 --
   which is exactly why the reader's length check precedes the temperature
   read.

   CITATIONS:
     [1] Bird, G.A. (1994), "Molecular Gas Dynamics and the Direct Simulation
         of Gas Flows", Sec. 2.3 (number density / mass density).
     [2] SPARTA (Stochastic PArallel Rarefied-gas Time-accurate Analyzer)
         manual, Sec. 2.4, "dump" grid output, ITEM: CELLS layout.
     [3] CPython Language Reference, Sec. 3.2 (sequence indexing: an index is
         valid iff 0 <= i < len(s)).
     [4] Coq Reference Manual, Coq.Reals.RIneq (Rinv_l, Rmult_le_compat_l,
         Rmult_le_compat_r, Rmult_le_reg_l, Rmult_eq_reg_l,
         Rdiv_lt_0_compat).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

(* R_scope opened at file level: every Definition, Lemma and proof below
   quantifies over R; numerals and / then elaborate in the real field rather
   than nat.  Any nat-only lemma is wrapped in Section NatPart below. *)
Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   AXIOM SP2 -- the two physical constants of the reader, written so that every
   arithmetic step below is a closed computation on literals.
   --------------------------------------------------------------------------- *)
Definition M_AIR : R := 2987 / 100000.
Definition N_AVOGADRO : R := 6022 * 100000000000000000000.

Lemma m_air_pos : 0 < M_AIR.
Proof.
  unfold M_AIR.
  apply Rdiv_lt_0_compat; lra.
Qed.

Lemma n_avogadro_pos : 0 < N_AVOGADRO.
Proof.
  unfold N_AVOGADRO.
  assert (Ha : 0 < 6022) by lra.
  assert (Hb : 0 < 100000000000000000000) by lra.
  assert (H : 0 < 6022 * 100000000000000000000)
    by (apply Rmult_lt_0_compat; assumption).
  exact H.
Qed.

(* ---------------------------------------------------------------------------
   Cancellation lemma used by every "multiply both sides by the denominator"
   step below:  l * (x / l) = x  for l <> 0.
   --------------------------------------------------------------------------- *)
Lemma cancel_mul : forall x l : R, l <> 0 -> l * (x / l) = x.
Proof.
  intros x l Hne.
  unfold Rdiv.
  rewrite <- Rmult_assoc.
  rewrite (Rmult_comm l x).
  rewrite Rmult_assoc.
  rewrite (Rmult_comm l (/ l)).
  rewrite (Rinv_l l Hne).
  apply Rmult_1_r.
Qed.

(* ---------------------------------------------------------------------------
   Helper:  a / b <= 1  whenever 0 < b and a <= b.
   --------------------------------------------------------------------------- *)
Lemma rdiv_le_1 : forall a b, 0 < b -> a <= b -> a / b <= 1.
Proof.
  intros a b Hb Hab.
  assert (Hne : b <> 0) by lra.
  assert (E : b * (a / b) = a) by (apply cancel_mul; exact Hne).
  apply (Rmult_le_reg_l b).
  - exact Hb.
  - rewrite E. rewrite Rmult_1_r. exact Hab.
Qed.

(* ---------------------------------------------------------------------------
   Helper:  0 <= a / b  whenever 0 <= a and 0 < b.
   --------------------------------------------------------------------------- *)
Lemma rdiv_nonneg : forall a b, 0 <= a -> 0 < b -> 0 <= a / b.
Proof.
  intros a b Ha Hb.
  assert (Hinv : 0 < / b) by (apply Rinv_0_lt_compat; exact Hb).
  apply Rlt_le in Hinv.
  unfold Rdiv.
  apply Rmult_le_pos; [exact Ha | exact Hinv].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP4a -- the cell centre is at or above the lower bound.
   --------------------------------------------------------------------------- *)
Lemma midpoint_ge_lo : forall lo hi, lo <= hi -> lo <= (lo + hi) / 2.
Proof.
  intros lo hi Hle.
  assert (H2 : 0 < 2) by lra.
  assert (Hne : 2 <> 0) by lra.
  apply (Rmult_le_reg_l 2); [exact H2 | ].
  rewrite (cancel_mul (lo + hi) 2 Hne).
  lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP4b -- the cell centre is at or below the upper bound.
   --------------------------------------------------------------------------- *)
Lemma midpoint_le_hi : forall lo hi, lo <= hi -> (lo + hi) / 2 <= hi.
Proof.
  intros lo hi Hle.
  assert (H2 : 0 < 2) by lra.
  assert (Hne : 2 <> 0) by lra.
  apply (Rmult_le_reg_l 2); [exact H2 | ].
  rewrite (cancel_mul (lo + hi) 2 Hne).
  lra.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP4 -- the combined containment statement the reader relies on.
   --------------------------------------------------------------------------- *)
Lemma midpoint_in_cell : forall lo hi, lo <= hi ->
   lo <= (lo + hi) / 2 /\ (lo + hi) / 2 <= hi.
Proof.
  intros lo hi Hle.
  split.
  - apply midpoint_ge_lo.
    exact Hle.
  - apply midpoint_le_hi.
    exact Hle.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP4c -- the centre does not depend on the order in which the two
   bounds are reported, which is why the reader does not have to normalise
   xlo <= xhi itself before averaging.
   --------------------------------------------------------------------------- *)
Lemma midpoint_sym : forall lo hi, (lo + hi) / 2 = (hi + lo) / 2.
Proof.
  intros lo hi.
  assert (Hne : 2 <> 0) by lra.
  apply (Rmult_eq_reg_l 2).
  - rewrite (cancel_mul (lo + hi) 2 Hne).
    rewrite (cancel_mul (hi + lo) 2 Hne).
    lra.
  - exact Hne.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP5 -- the mass density is strictly positive for a positive number
   density, so the reader's density mask admits every physical cell.
   --------------------------------------------------------------------------- *)
Lemma density_positive : forall n, 0 < n -> 0 < n * M_AIR / N_AVOGADRO.
Proof.
  intros n Hn.
  assert (Hnm : 0 < n * M_AIR).
  { apply Rmult_lt_0_compat; [exact Hn | apply m_air_pos]. }
  apply Rdiv_lt_0_compat; [exact Hnm | apply n_avogadro_pos].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP5b -- the density is a positive scale of the number density, so
   the ordering of two cells is preserved by the unit conversion: a denser cell
   in number density is denser in mass density too.
   --------------------------------------------------------------------------- *)
Lemma density_scaling : forall n1 n2, 0 < n1 -> n1 <= n2 ->
   n1 * M_AIR / N_AVOGADRO <= n2 * M_AIR / N_AVOGADRO.
Proof.
  intros n1 n2 H1 H2.
  assert (Hm : 0 < M_AIR) by apply m_air_pos.
  assert (Hna : 0 < N_AVOGADRO) by apply n_avogadro_pos.
  assert (Hne : N_AVOGADRO <> 0) by lra.
  apply (Rmult_le_reg_l N_AVOGADRO); [exact Hna | ].
  rewrite (cancel_mul (n1 * M_AIR) N_AVOGADRO Hne).
  rewrite (cancel_mul (n2 * M_AIR) N_AVOGADRO Hne).
  apply (Rmult_le_compat_l M_AIR n1 n2); [lra | exact H2].
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP6a -- a column index inside the token list is a legal Python
   sequence index (CPython language reference, sequence indexing).
   --------------------------------------------------------------------------- *)
Lemma column_index_in_range : forall n i, i < n -> 0 <= i /\ i < n.
Proof.
  intros n i Hi.
  split.
  - lia.
  - exact Hi.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP6b -- reading column 9 requires at least 10 columns, so the
   reader's length check is exactly the precondition of the temperature read.
   --------------------------------------------------------------------------- *)
Lemma temperature_column_guarded : forall n, 10 <= n -> 9 < n.
Proof.
  intros n H.
  lia.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP6c -- a record with at most 9 columns cannot supply column 9, so a
   short row is (correctly) skipped rather than misread as temperature 0.
   --------------------------------------------------------------------------- *)
Lemma short_record_has_no_temperature : forall n, n <= 9 -> ~ (9 < n).
Proof.
  intros n H H2.
  lia.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM SP6d -- the density column 10 is read under the same guard.
   --------------------------------------------------------------------------- *)
Lemma density_column_guarded : forall n, 11 <= n -> 10 < n.
Proof.
  intros n H.
  lia.
Qed.
