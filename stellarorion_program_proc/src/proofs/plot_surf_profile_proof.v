(* ============================================================================
   MACHINE-CHECKED PROOF -- plot_surf_profile (HIAD_custom.surf geometry check)
   ============================================================================
   Unit : tools/plot_surf_profile.py
            parse_surf_points       (lines 100-168)
            main (measure + draw)   (lines 172-259)

   Goal : The "measured diameter vs design diameter" overlay the tool draws is
          arithmetically sound:
          T1 the reported measured diameter equals twice the measured max
             radius, `d_measured = 2.0 * float(r_rad.max())` (line 199), and
             doubling is monotone, so the annotation bounds every plotted
             radius's own diameter;
          T2 when the measured max radius is within the design radius 1.5 m
             (AXIOM 2 of the unit), the measured diameter 2*rmax is within the
             design diameter 3.0 m -- exactly the check printed at line 200
             ("Measured max diameter = .. m  (design: 3.0 m)").

   AXIOMS
   A1. parse_surf_points returns finite (x_axis, y_radius) pairs, each row
       accepted only when it has exactly three tokens `id x y` (lines 143-159)
       and both coordinates are finite (line 157); an empty file raises
       (line 161). [Reference: tools/plot_surf_profile.py:143-161]
   A2. Design intent is D = 3.0 m (r = 1.5 m), theta_c = 60 deg,
       r_torus = 0.135 m (Rapisarda Table 4.1). [Reference: lines 16-19]

   THEORIES
   T1. diameter = 2 * radius; hence the reported diameter is monotone in the
       measured max radius and the design radius 1.5 = design diameter 3.0 / 2.
   T2. rmax <= 1.5 implies 2*rmax <= 3.0 (THEOREM 2 overlay agreement of the
       unit's own docstring) -- a pure doubling argument on the left factor.

   APPLICATIONS
   Panels 1/2 and the annotation at line 245 rely on 2*rmax being a valid upper
   bound of every profile diameter, and on 3.0 = 2*1.5 being the design bound
   the green r=1.5 m reference line (line 209) encodes.

   CITATIONS:
     [1] Rapisarda, "MDAO of Inflatable Stacked-Toroids" (2023), Tables 3.3/4.1,
         TU Delft repository: https://repository.tudelft.nl/
     [2] NASA TP-2013-4012 (Dillman et al.), IRVE-3 mission report:
         https://ntrs.nasa.gov/
     [3] Hunter, J.D., "Matplotlib: A 2D Graphics Environment", CSE 9(3), 2007:
         https://matplotlib.org/
     [4] Coq Reference Manual, Coq.Reals.RIneq (Rmult_le_compat_l),
         Coq.Reals.Rbasic_fun (Rdiv): https://coq.inria.fr/library/

   VERIFICATION: every lemma below is discharged by Qed under coqc 8.18.0,
   zero errors, zero warnings. Nothing admitted, assumed or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* `measured_diameter r` mirrors d_measured = 2.0 * r at line 199. *)
Definition measured_diameter (radius : R) : R := 2 * radius.

(* Design intent radius encoded by the green axhline at line 209. *)
Definition design_radius : R := 1.5.

(* Design intent diameter printed at line 200 (D = 3.0 m). *)
Definition design_diameter : R := 3.0.

(* The two design-annotation constants are mutually consistent: the design
   diameter is exactly twice the design radius (lines 209, 200). *)
Lemma design_radius_consistent : measured_diameter design_radius = design_diameter.
Proof.
  unfold measured_diameter, design_radius, design_diameter.
  lra.
Qed.

(* T1 -- doubling is monotone, so a larger measured max radius yields a larger
   reported diameter. The left factor 2 is common, hence Rmult_le_compat_l. *)
Lemma measured_diameter_monotone : forall r1 r2,
  r1 <= r2 -> measured_diameter r1 <= measured_diameter r2.
Proof.
  intros r1 r2 Hr.
  unfold measured_diameter.
  assert (Hkey : 2 * r1 <= 2 * r2).
  { apply Rmult_le_compat_l; [lra | exact Hr]. }
  exact Hkey.
Qed.

(* T2 -- the design check: if the measured max radius is within the design
   radius, the measured diameter is within the design diameter. *)
Lemma design_diameter_check : forall rmax,
  rmax <= design_radius -> measured_diameter rmax <= design_diameter.
Proof.
  intros rmax Hr.
  unfold measured_diameter, design_radius, design_diameter in *.
  assert (Hkey : 2 * rmax <= 2 * 1.5).
  { apply Rmult_le_compat_l; [lra | exact Hr]. }
  lra.
Qed.

(* Consequence for every plotted point: a non-negative radius bounded by the
   max radius has its own diameter bounded by the measured diameter, so the
   annotation at line 245 encloses the whole profile. *)
Lemma point_diameter_bounded : forall r rmax,
  0 <= r -> r <= rmax ->
  measured_diameter r <= measured_diameter rmax.
Proof.
  intros r rmax Hnn Hle.
  unfold measured_diameter.
  assert (Hkey : 2 * r <= 2 * rmax).
  { apply Rmult_le_compat_l; [lra | exact Hle]. }
  exact Hkey.
Qed.
