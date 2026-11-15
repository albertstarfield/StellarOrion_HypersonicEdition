(*  split_family.v

    New method for this turn: a decision procedure for rational field
    identities (Qfield), used to prove a SYMBOLIC ONE-PARAMETER FAMILY rather
    than a single identity.  The result is stronger than "one point is not
    enough": for EVERY share r of the flux, there is an exact model of the deck's
    operating point that puts precisely r W/m^2 into the radiative channel.

      K(r) = r / T^4          (radiative coefficient, W m^-2 K^-4)
      c(r) = (q - r) / T      (conduction coefficient, W m^-2 K^-1)

    Every r fits.  So the deck's single-point closure is satisfied by a
    continuum of models, indexed by the very quantity in dispute -- and the
    deficit shows up only if the term is counted twice, where the surplus is
    exactly r.

    Why this answers "why add another radiation term into the conduction":
    because a conductivity is a coefficient multiplying a gradient, the split
    between "conduction" and "radiation" is a relabelling at a single point.
    What fixes r is not the point; it is a second point (two_point_witness.v
    l. 68: determinant != 0) or a measured extinction coefficient
    (design_point_exact.v l. 49/53: kappa* between 7407 and 7408 1/m).

    Compiled with:  rocq compile proofs/split_family.v
*)

From Stdlib Require Import QArith setoid_ring.Field_tac.
Open Scope Q_scope.

Definition T1 : Q := (1348 # 1).
Definition q  : Q := (143760 # 1).
Definition T4 : Q := T1 * T1 * T1 * T1.

Definition Kof (r : Q) : Q := r / T4.
Definition cof (r : Q) : Q := (q - r) / T1.

(* The family: every split reproduces the deck's total flux exactly. *)
Lemma family_fits_every_split (r : Q) :
  Kof r * T4 + cof r * T1 == q.
Proof. unfold Kof, cof, T4, T1, q. field. Qed.

(* r = 0 is the pure-conduction model the deck implicitly assumes. *)
Lemma zero_share_is_pure_conduction :
  Kof (0 # 1) == (0 # 1) /\ cof (0 # 1) == q / T1.
Proof.
  split.
  - unfold Kof, T4, T1. vm_compute. reflexivity.
  - unfold cof. vm_compute. reflexivity.
Qed.

(* r = 14376 (ten per cent of the deck's flux) is a different model. *)
Lemma ten_percent_share_is_a_different_model :
  Kof (14376 # 1) == (14376 # 1) / ((1348 * 1348 * 1348 * 1348) # 1).
Proof. unfold Kof, T4, T1. vm_compute. reflexivity. Qed.

(* The two models cannot be the same model. *)
Lemma the_two_models_differ :
  Kof (0 # 1) == Kof (14376 # 1) -> False.
Proof. unfold Kof, T4, T1. vm_compute. intros H. discriminate H. Qed.

(* Conduction must FALL as the radiative share rises: the family is not a
   relabelling of one model but a trade-off. *)
Lemma conduction_falls_as_radiation_rises :
  cof (14376 # 1) < cof (0 # 1).
Proof. unfold cof, T1, q. vm_compute. reflexivity. Qed.

(* And the diagnostics: count the radiative term twice and the surplus is
   exactly the share r, not a rounding. *)
Lemma double_counting_surplus_is_exactly_the_share (r : Q) :
  (Kof r * T4 + cof r * T1) + Kof r * T4 == q + r.
Proof. unfold Kof, cof, T4, T1, q. field. Qed.

Lemma surplus_at_ten_percent_is_14376 :
  (q + (14376 # 1)) - q == (14376 # 1).
Proof. unfold q. vm_compute. reflexivity. Qed.

(* Sanity: the family is not degenerate -- T4 is not zero, so K(r) is defined. *)
Lemma T4_is_not_zero : T4 == (0 # 1) -> False.
Proof. unfold T4, T1. vm_compute. intros H. discriminate H. Qed.
