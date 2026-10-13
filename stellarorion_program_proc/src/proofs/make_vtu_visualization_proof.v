(* ============================================================================
   MACHINE-CHECKED PROOF -- make_vtu_visualization (VTU physical visualization)
   ============================================================================
   Unit : scripts/make_vtu_visualization.py
            _watts_to_celsius_friendly (lines 114-116)
            _q_to_t_surface            (lines 119-126)
            plot_3d_surface            (lines 129-169)
            plot_2d_cross_section      (lines 172-222)

   Goal : The two scaling safeguards the visuals rely on:
          T1 the W/m^2 -> W/cm^2 conversion `q / 1e4` (lines 116, 136, 182, 229,
             261) is an exact POSITIVE rescale, so it preserves sign and order:
             a positive cell heat flux stays positive, and the hottest cell maps
             to the highest plotted value -- the ordering the "hot" colormap and
             the stagnation annotation (line 210) depend on;
          T2 the colormap upper bound `vmax = max(q_cm2.max(), 50)` (lines 141,
             192) is a VALID scale bound: it is at least the floor 50 W/cm^2 and
             at least the data maximum, so every cell value lies within the
             color range and the colorbar never under-spans the data;
          T3 the surface-temperature guard `_q_to_t_surface` returns the floor
             300.0 K for any non-positive heat flux (lines 124-125), so the
             per-point T_surface used in plot_heat_flux_vs_x never takes the
             radiative-equilibrium branch on a non-physical argument.

   AXIOMS
   A1. HeatFlux_Wm2 cell values are in W/m^2; 1 W/m^2 = 1e-4 W/cm^2 (the divisor
       1e4 is a nonzero compile-time constant, per the unit's nosec annotations).
       [Reference: scripts/make_vtu_visualization.py:116, 136, 229]
   A2. The colormap clamp floor is 50 W/cm^2 (lines 141, 192).
       [Reference: scripts/make_vtu_visualization.py:141, 192]
   A3. `_q_to_t_surface` delegates to radiative_eq_temp only for q > 0 and
       returns 300.0 otherwise (lines 124-126).
       [Reference: scripts/make_vtu_visualization.py:124-126]

   THEORIES
   T1. For c > 0, x |-> x/c is positive on positive input and monotone.
   T2. floor <= Rmax q floor and q <= Rmax q floor (Rmax_l / Rmax_r).
   T3. q <= 0 implies the guard branch is taken (_q_to_t_surface q t = 300).

   APPLICATIONS
   The 3D scatter, the 2D cross-section and the heat-flux-vs-X plot are only
   faithful because the rescaling keeps the data ordered and inside the (>=50)
   color range, and the T_surface series stays on its physical branch.

   CITATIONS:
     [1] VTK XML file format (VTU): https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf
     [2] Bird, G.A., "Molecular Gas Dynamics and the DSMC of Gas Flows", 1994:
         https://ntrs.nasa.gov/
     [3] Coq Reference Manual, Coq.Reals.Rbasic_fun (Rmax_l, Rmax_r),
         Coq.Reals.RIneq (Rdiv_lt_0_compat, Rinv_0_lt_compat, Rlt_le,
         Rmult_le_compat_r): https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* Division by a positive constant is monotone (used for the 1e4 rescaling). *)
Lemma rdiv_le_mono : forall a b c, 0 < c -> a <= b -> a / c <= b / c.
Proof.
  intros a b c Hc Hab.
  assert (Hinv : 0 <= / c) by (apply Rlt_le; apply Rinv_0_lt_compat; exact Hc).
  unfold Rdiv.
  apply Rmult_le_compat_r; [exact Hinv | exact Hab].
Qed.

(* `wm2_to_wcm2 q` mirrors _watts_to_celsius_friendly = q / 1e4 (line 116). *)
Definition wm2_to_wcm2 (q : R) : R := q / 10000.

(* T1a -- a positive W/m^2 cell heat flux stays strictly positive in W/cm^2,
   so the plotted series and the colormap see the same sign. *)
Lemma wm2_to_wcm2_positive : forall q, 0 < q -> 0 < wm2_to_wcm2 q.
Proof.
  intros q Hq.
  assert (Hc : 0 < 10000) by lra.
  unfold wm2_to_wcm2.
  apply Rdiv_lt_0_compat; [exact Hq | exact Hc].
Qed.

(* T1b -- the rescaling preserves order, so the hottest cell remains hottest. *)
Lemma wm2_to_wcm2_monotone : forall a b, a <= b -> wm2_to_wcm2 a <= wm2_to_wcm2 b.
Proof.
  intros a b Hab.
  assert (Hc : 0 < 10000) by lra.
  unfold wm2_to_wcm2.
  apply rdiv_le_mono; [exact Hc | exact Hab].
Qed.

(* `color_vmax q floor` mirrors vmax = max(q_cm2.max(), 50) (lines 141, 192). *)
Definition color_vmax (q floor : R) : R := Rmax q floor.

(* T2a -- the color scale is at least the floor 50 W/cm^2 even for tiny data. *)
Lemma color_vmax_ge_floor : forall q floor, floor <= color_vmax q floor.
Proof.
  intros q floor.
  unfold color_vmax.
  assert (Hshow : floor <= Rmax q floor) by apply Rmax_r.
  exact Hshow.
Qed.

(* T2b -- the color scale is at least the data maximum, so no cell over-spans. *)
Lemma color_vmax_ge_data : forall q floor, q <= color_vmax q floor.
Proof.
  intros q floor.
  unfold color_vmax.
  assert (Hshow : q <= Rmax q floor) by apply Rmax_l.
  exact Hshow.
Qed.

(* `q_to_t_surface q treg` mirrors _q_to_t_surface (lines 119-126): for q <= 0
   it returns the 300.0 K floor, otherwise the radiative-equilibrium value t. *)
Definition q_to_t_surface (q radiative_t : R) : R :=
  if Rle_dec q 0 then 300 else radiative_t.

(* T3 -- a non-positive heat flux takes the floor branch and yields 300.0 K. *)
Lemma q_to_t_floor : forall q radiative_t, q <= 0 -> q_to_t_surface q radiative_t = 300.
Proof.
  intros q radiative_t Hq.
  unfold q_to_t_surface.
  destruct (Rle_dec q 0) as [Hle | Hgt].
  - reflexivity.
  - exfalso.
    lra.
Qed.
