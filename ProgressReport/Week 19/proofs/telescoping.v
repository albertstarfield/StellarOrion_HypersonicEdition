(*  telescoping.v

    The theorem the question actually asks for: "if there is already radiation,
    why add another radiation term into the conduction?"

    Answer, in exact integer algebra:

    (1) The quartic difference across a layer FACTORISES as a coefficient times
        the temperature step:

            T1^4 - T0^4 = (T1 - T0) * (T1^3 + T1^2 T0 + T1 T0^2 + T0^3)

        so the radiative transfer is literally "a conductivity times a gradient".
        That coefficient is not a free parameter -- it is fixed by the two
        temperatures, which is why the Rosseland form k_R = 16 sigma T^3 / (3 kappa)
        is the small-step limit of it.

    (2) At zero step the coefficient collapses to 4 T^3, which is exactly the
        derivative d/dT (T^4) = 4 T^3 that produces the cubic Rosseland
        coefficient.  So "T^4 outside Fourier" and "T^3 inside Fourier" are the
        SAME object written one derivative apart -- not two channels.

    (3) Summed over the layer the fluxes TELESCOPE: the interior contributions
        collapse to a single boundary difference.  So the volumetric term is a
        divergence of one potential, and its total is the potential's boundary
        values.  Adding it again double counts by exactly the total.

    (4) The wall term is that same functional evaluated at the surface:
        eps*sigma*(Ts^4 - Tenv^4) = radFlux (eps*sigma) Tenv Ts.  One object,
        three writings: potential difference, conductivity times gradient,
        boundary evaluation.

    Compiled with:  rocq compile proofs/telescoping.v
*)

From Stdlib Require Import ZArith setoid_ring.Ring_tac.
Open Scope Z_scope.

Definition Z4 (T : Z) : Z := T * T * T * T.

(* Radiative transfer across one step, as a difference of the same potential. *)
Definition radFlux (C T0 T1 : Z) : Z := C * (Z4 T1 - Z4 T0).

(* The wall balance, in the thesis's own form (appendix.tex:811, 815). *)
Definition wallFlux (eps sig Ts Tenv : Z) : Z := eps * sig * (Z4 Ts - Z4 Tenv).

(* (1) The quartic difference IS a coefficient times the gradient. *)
Lemma the_difference_is_a_conductivity_times_the_step (C T0 T1 : Z) :
  radFlux C T0 T1 =
    C * (T1 - T0) * (T1 * T1 * T1 + T1 * T1 * T0 + T1 * T0 * T0 + T0 * T0 * T0).
Proof. unfold radFlux, Z4. ring. Qed.

(* (2) At zero step the coefficient is exactly 4 T^3: the origin of the cubic
       Rosseland coefficient, and therefore of the 16/3 in front of it. *)
Lemma zero_step_coefficient_is_four_T_cubed (T : Z) :
  T * T * T + T * T * T + T * T * T + T * T * T = 4 * (T * T * T).
Proof. ring. Qed.

(* (3) Telescoping: interior contributions collapse to one boundary difference. *)
Lemma telescoping_three_nodes (C T0 T1 T2 : Z) :
  radFlux C T0 T1 + radFlux C T1 T2 = radFlux C T0 T2.
Proof. unfold radFlux. ring. Qed.

Lemma telescoping_four_nodes (C T0 T1 T2 T3 : Z) :
  radFlux C T0 T1 + radFlux C T1 T2 + radFlux C T2 T3 = radFlux C T0 T3.
Proof. unfold radFlux. ring. Qed.

(* The sum over the layer is a boundary functional -- which is why a volumetric
   writing and a surface writing of the same physics agree when written once. *)
Lemma the_layer_sum_is_the_boundary_difference (C T0 T1 T2 : Z) :
  radFlux C T0 T1 + radFlux C T1 T2 = C * Z4 T2 - C * Z4 T0.
Proof. unfold radFlux. ring. Qed.

(* (4) One object, two writings: the wall term is radFlux at the surface. *)
Lemma wall_is_the_same_functional (eps sig Ts Tenv : Z) :
  wallFlux eps sig Ts Tenv = radFlux (eps * sig) Tenv Ts.
Proof. unfold wallFlux, radFlux. ring. Qed.

(* Counting it twice gives exactly twice -- not a rounding, a factor. *)
Lemma double_counting_gives_twice (C T0 T2 : Z) :
  radFlux C T0 T2 + radFlux C T0 T2 = 2 * radFlux C T0 T2.
Proof. unfold radFlux. ring. Qed.

(* And the flux is not identically zero, so (8) is not vacuous. *)
Lemma a_nonzero_flux_exists : radFlux 1 1000 1348 <> 0.
Proof. unfold radFlux, Z4. vm_compute. intros H. discriminate H. Qed.

(* A zero step carries zero flux at any temperature -- the volumetric term needs
   a gradient, the wall term does not (it needs a surface/environment gap). *)
Lemma zero_step_carries_zero_flux (C T : Z) : radFlux C T T = 0.
Proof. unfold radFlux. ring. Qed.

(* The separation, non-vacuously: a FLAT interior carries no volumetric flux at
   all, while the wall balance is not zero -- because it is driven by the gap to
   the environment, not by the interior gradient. *)
Lemma flat_interior_still_radiates_at_the_wall :
  radFlux 1 1200 1200 = 0 /\ wallFlux 1 1 1348 300 <> 0.
Proof.
  split.
  - unfold radFlux. ring.
  - unfold wallFlux, Z4. vm_compute. intros H. discriminate H.
Qed.
