(* ============================================================================
   MACHINE-CHECKED PROOF -- plot_rapisarda_comparison (MDAO comparison plots)
   ============================================================================
   Unit : scripts/plot_rapisarda_comparison.py
            RAPISARDA_REFS          (lines 51-66)
            _plot_comparison_bars   (lines 159-214)
            main (17-col branch)    (lines 246-487)

   Goal : The physical-unit rescalings the plotter applies to the raw DSMC
          columns are exact POSITIVE rescales, so they preserve sign and order:
          T1 the peak heat flux converted W/m^2 -> W/cm^2 by `q / 10000.0`
             (lines 402, 446) stays strictly positive and its ordering across
             steps is preserved, so the Rapisarda reference line at
             14.3610 W/cm^2 (line 53) is compared against a correctly scaled,
             correctly ranked series;
          T2 the Pa -> kPa rescaling by `q / 1000.0` (line 365) is likewise
             order-preserving.

   AXIOMS
   A1. `heatflux_max_Wm2` is a DSMC steady-state cell value in W/m^2; the plot
       divides by 10000.0 to express W/cm^2 exactly (1 W/m^2 = 1e-4 W/cm^2).
       [Reference: scripts/plot_rapisarda_comparison.py:402, 446]
   A2. The dynamic pressure column is in Pa; the plot divides by 1000.0 for kPa
       (1 kPa = 1000 Pa) so the 6.2 kPa target (line 61) is comparable.
       [Reference: scripts/plot_rapisarda_comparison.py:365]

   THEORIES
   T1. For c > 0 the map x |-> x/c is strictly positive on positive inputs
       (0 < q -> 0 < q/10000) and monotone (a <= b -> a/c <= b/c), so no peak
       becomes a trough and no positive flux becomes non-positive under the
       unit conversion.
   T2. The same holds for c = 1000 (Pa -> kPa).

   APPLICATIONS
   The scalar-comparison bar chart and the reference overlays are only
   meaningful because the divisor 10000.0 (resp. 1000.0) is a genuine positive
   scale: peak heat flux in W/cm^2 = max(W/m^2)/1e4 and it keeps the same rank
   and positivity as the underlying W/m^2 series.

   CITATIONS:
     [1] Rapisarda, "MDAO of Inflatable Stacked-Torus Aerodynamic Decelerators
         for Mars EDL", TU Delft, 2023 (Table 4.10 reference values):
         https://repository.tudelft.nl/
     [2] NASA Technical Paper 2013-4012, IRVE-3 Flight Data:
         https://ntrs.nasa.gov/
     [3] Hunter, J.D., "Matplotlib: A 2D Graphics Environment", 2007:
         https://matplotlib.org/
     [4] Coq Reference Manual, Coq.Reals.RIneq (Rinv_0_lt_compat, Rlt_le,
         Rmult_le_compat_r, Rdiv_lt_0_compat): https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* Division by a positive constant is monotone; proved directly from the
   reciprocal sign (Rinv_0_lt_compat) and Rmult_le_compat_r.
   [Coq 8.18 Reals: Rinv_0_lt_compat, Rlt_le, Rdiv, Rmult_le_compat_r] *)
Lemma rdiv_le_mono : forall a b c, 0 < c -> a <= b -> a / c <= b / c.
Proof.
  intros a b c Hc Hab.
  assert (Hinv : 0 <= / c) by (apply Rlt_le; apply Rinv_0_lt_compat; exact Hc).
  unfold Rdiv.
  apply Rmult_le_compat_r; [exact Hinv | exact Hab].
Qed.

(* W/m^2 -> W/cm^2 conversion used at line 402 (1 W/m^2 = 1e-4 W/cm^2). *)
Definition to_wcm2 (q : R) : R := q / 10000.

(* Pa -> kPa conversion used at line 365 (1 kPa = 1000 Pa). *)
Definition to_kpa (q : R) : R := q / 1000.

(* T1a -- a positive W/m^2 heat flux stays strictly positive in W/cm^2, so
   the plotted series and the 14.3610 reference keep the same sign. *)
Lemma to_wcm2_positive : forall q, 0 < q -> 0 < to_wcm2 q.
Proof.
  intros q Hq.
  assert (Hc : 0 < 10000) by lra.
  unfold to_wcm2.
  apply Rdiv_lt_0_compat; [exact Hq | exact Hc].
Qed.

(* T1b -- the W/m^2 -> W/cm^2 rescaling preserves order, so DSMC peak steps
   remain peak steps after conversion. *)
Lemma to_wcm2_monotone : forall a b, a <= b -> to_wcm2 a <= to_wcm2 b.
Proof.
  intros a b Hab.
  assert (Hc : 0 < 10000) by lra.
  unfold to_wcm2.
  apply rdiv_le_mono; [exact Hc | exact Hab].
Qed.

(* T2 -- the Pa -> kPa rescaling preserves order for the dynamic-pressure plot. *)
Lemma to_kpa_monotone : forall a b, a <= b -> to_kpa a <= to_kpa b.
Proof.
  intros a b Hab.
  assert (Hc : 0 < 1000) by lra.
  unfold to_kpa.
  apply rdiv_le_mono; [exact Hc | exact Hab].
Qed.
