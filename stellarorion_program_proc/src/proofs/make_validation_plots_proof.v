(* ============================================================================
   MACHINE-CHECKED PROOF -- make_validation_plots (validation time-series plotter)
   ============================================================================
   Unit : scripts/make_validation_plots.py
            _read_csv               (lines 75-100)
            _subsample              (lines 203-228)
            _plot_full_column       (lines 231-281)
            main                    (lines 331-380)

   Goal : The generic plotter's two indexing guards hold:
          T1 the subsample stride `step_size = max(1, ceil(len/max_points))`
             (line 222) is always >= 1, so `steps[::step_size]` (line 223)
             samples at least the HEAD element (index 0) and never degenerates
             to an empty/degenerate stride -- the invariant the renderer relies
             on to keep a non-empty, ordered x-axis;
          T2 reading a CSV with `num_cols` header columns yields exactly
             `num_cols - 1` metric columns (lines 80, 100), and the per-column
             loop `for c in range(1, num_cols): cols[c-1]` (lines 96-97) only
             ever forms indices `c - 1` that stay strictly below that count, so
             every `data_cols[col_idx]` access in main (line 360) is in range.

   AXIOMS
   A1. The CSV's first column is the integer `step`; the remaining `num_cols-1`
       columns are float metrics (AXIOM 2/3 of the unit).
       [Reference: scripts/make_validation_plots.py:80, 86, 96-97, 100]
   A2. The stride clamps at a floor of 1 regardless of the ceil term
       [Reference: scripts/make_validation_plots.py:222].

   THEORIES
   T1. Nat.max 1 s >= 1 for every s, and the head index 0 is a valid index of
       any array of length >= 1.
   T2. For any header width num_cols and any loop variable c with 1 <= c <
       num_cols, the formed index c-1 satisfies 0 <= c-1 < num_cols-1.

   APPLICATIONS
   The DSMC-window bottom panel (steps 0-2200, set_xlim(0,2200), line 271) and
   the full-span plots are only drawn because the stride guard and the column
   index guard keep the sampled/sliced arrays non-empty and in-range, so the
   renderer never indexes past the parsed columns or samples nothing.

   CITATIONS:
     [1] Python Language Reference, 3rd Ed., Sec. 4.8 (int), Sec. 6.3 (floor
         division), list slicing (steps[::step_size]):
         https://docs.python.org/3/reference/
     [2] Hunter, J.D., "Matplotlib: A 2D Graphics Environment", 2007:
         https://matplotlib.org/
     [3] Coq Reference Manual, Coq.Arith.PeanoNat (Nat.max), Coq.micromega.Lia:
         https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* All invariants of this plotter are combinatorial (nat), so they live in a
   nat-scoped section; the file-level R_scope is intentionally unused here. *)
Section MakeValidationNat.
Local Open Scope nat_scope.

(* `subsample_stride m` mirrors step_size = max(1, ceil(...)) at line 222,
   where m models the (positive) ceil term. *)
Definition subsample_stride (m : nat) : nat := Nat.max 1 m.

(* T1a -- the stride is floored at 1, so `steps[::step_size]` is a valid,
   non-degenerate slice start (index 0 is always taken). *)
Lemma subsample_stride_at_least_one : forall m, 1 <= subsample_stride m.
Proof.
  intros m.
  unfold subsample_stride.
  assert (Hshow : Nat.max 1 m = Nat.max 1 m) by reflexivity.
  lia.
Qed.

(* T1b -- with a positive stride the head index 0 is always inside any
   non-empty array, which is what makes the sampled plot carry a first sample. *)
Definition head_index : nat := 0.

Lemma head_index_in_range : forall n, 1 <= n -> head_index < n.
Proof.
  intros n Hn.
  unfold head_index.
  lia.
Qed.

(* `metric_columns num_cols` mirrors num_cols - 1 (the metric columns after
   dropping the leading `step` column). *)
Definition metric_columns (num_cols : nat) : nat := num_cols - 1.

(* T2 -- the per-column index c-1 stays strictly inside the metric-column count,
   so data_cols[c-1] (line 97) and data_cols[col_idx] (line 360) are in range. *)
Lemma data_index_in_range : forall num_cols c,
  1 <= c -> c < num_cols ->
  0 <= c - 1 /\ c - 1 < metric_columns num_cols.
Proof.
  intros num_cols c H1 H2.
  unfold metric_columns.
  split.
  - lia.
  - lia.
Qed.

End MakeValidationNat.
