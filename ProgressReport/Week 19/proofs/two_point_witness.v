(*  two_point_witness.v

    A different method from the previous turns: not a symbolic proof of an
    abstract lemma, but EXPLICIT WITNESSES plus a determinant, evaluated as exact
    rationals with `vm_compute`.  The point is to exhibit, at the deck's own
    numbers, two models that fit the single operating point identically and
    disagree about whether radiation is in the balance at all.

    Why this matters for "does that solve issue 3": the deck checks its closure at
    ONE point.  If that check is satisfied by a conduction-only model and by a
    model with a radiation term, then the check is not evidence for either --
    and here are the two models, with the arithmetic done by the kernel.

    Witness A:  K = 0,       c = q/T                      (no radiation at all)
    Witness B:  K = 1,       c = (q - T^4)/T              (radiation switched on)
    Both satisfy  K*T^4 + c*T = q  at  T = 1348 K,  q = 143760 W/m^2.

    Then: the ambiguity a single point leaves is T^3 = 2,449,456,192 W/(m^2 K) of
    conduction coefficient per unit of K -- a quantity no closure check can bound,
    because the check never sees it.

    Compiled with:  rocq compile proofs/two_point_witness.v
*)

From Stdlib Require Import QArith.
Open Scope Q_scope.

(* The deck's operating point. *)
Definition T1 : Q := (1348 # 1).
Definition q  : Q := (143760 # 1).
(* The thesis's closure temperature, 1430.25 K. *)
Definition T2 : Q := (5721 # 4).

(* --- witness A: pure conduction ------------------------------------------- *)
Definition KA : Q := (0 # 1).
Definition cA : Q := q / T1.

(* --- witness B: radiation present ----------------------------------------- *)
Definition KB : Q := (1 # 1).
Definition cB : Q := (q - T1 * T1 * T1 * T1) / T1.

Lemma witness_A_fits_the_deck_point :
  KA * (T1 * T1 * T1 * T1) + cA * T1 == q.
Proof. unfold KA, cA, T1, q. vm_compute. reflexivity. Qed.

Lemma witness_B_fits_the_same_point :
  KB * (T1 * T1 * T1 * T1) + cB * T1 == q.
Proof. unfold KB, cB, T1, q. vm_compute. reflexivity. Qed.

Lemma the_two_witnesses_are_different :
  KA == KB -> False.
Proof. unfold KA, KB. vm_compute. intros H. discriminate H. Qed.

(* The single-point check cannot choose between them. *)
Lemma one_point_admits_two_distinct_models :
  (KA == KB -> False) /\
  (KA * (T1 * T1 * T1 * T1) + cA * T1 == q) /\
  (KB * (T1 * T1 * T1 * T1) + cB * T1 == q).
Proof.
  split. exact the_two_witnesses_are_different.
  split. exact witness_A_fits_the_deck_point.
  exact witness_B_fits_the_same_point.
Qed.

(* --- and the same question at two points has exactly one answer ------------- *)
Definition determinant : Q := T1 * T1 * T1 * T1 * T2 - T2 * T2 * T2 * T2 * T1.

Lemma two_points_have_a_nonzero_determinant :
  determinant == (0 # 1) -> False.
Proof. unfold determinant, T1, T2. vm_compute. intros H. discriminate H. Qed.

(* --- the size of what a single point leaves undetermined -------------------- *)
Lemma ambiguity_per_unit_K_is_T_cubed :
  ((1348 * 1348 * 1348) # 1) == (2449456192 # 1).
Proof. vm_compute. reflexivity. Qed.

Lemma ambiguity_dwarfs_the_gas_conductivity :
  ((1 # 10) : Q) < ((1348 * 1348 * 1348) # 1).
Proof. vm_compute. reflexivity. Qed.

(* --- sanity: the bracket is not vacuous ------------------------------------ *)
Lemma the_two_temperatures_are_distinct : T1 == T2 -> False.
Proof. unfold T1, T2. vm_compute. intros H. discriminate H. Qed.
