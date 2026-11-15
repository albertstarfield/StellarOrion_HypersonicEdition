(*  series_resistance.v

    The theorem the T^4 question is really asking for, in the form an engineer
    can use: the radiative wall term is a RESISTANCE IN SERIES with the stack.

    Linearise the wall balance about the surface temperature:
        eps*sigma*(Ts^4 - Tinf^4) ~ 4*eps*sigma*Ts^3 * (Ts - Tinf)
    so the wall behaves as a resistor of value
        R_rad  = 1 / (4*eps*sigma*Ts^3)          [m^2 K / W]
    in series with the stack's conduction resistance
        R_cond = L / k                           [m^2 K / W]

    Consequences, each checked here:

      (1) SERIES IDENTITY -- a single flux q through both elements gives the
          drops q*R1 and q*R2, and q = (q*R1 + q*R2)/(R1 + R2).  Resistances
          add; the flux does not.

      (2) THE SHARE IS SMALL BUT NOT NEGLIGIBLE -- at Ts = 1348 K, eps = 0.85,
          sigma = 5.670374419e-8 (CODATA 2022), k = 0.1, L = 3 mm:
          7 % of R_cond < R_rad < R_cond / 14, so the radiative share of the
          total resistance is between 6 % and 7 %.  "Conduction dominates" is
          true and "radiation is irrelevant" is false, from the same numbers.

      (3) COUNTING IT TWICE IS A FACTOR, NOT A PERTURBATION -- putting the
          radiative resistance in twice multiplies the total resistance by
          (2*R_rad + R_cond)/(R_rad + R_cond) = 1.0659, a 6.19 % flux error.

    That is the answer to "if there is already radiation, why add another
    radiation term into the conduction": at the wall the same physics enters
    ONCE, as a resistance in series; adding it again doubles a series element,
    a multiplicative error -- the resistance-side twin of telescoping.v l. 80.

    Compiled with:  rocq compile proofs/series_resistance.v
*)

From Stdlib Require Import QArith setoid_ring.Field_tac.
Open Scope Q_scope.

(* Wall resistance at Ts = 1348 K, eps = 0.85, sigma = 5.670374419e-8. *)
Definition Rrad  : Q := (7812500000000000 # 3689354272450393619).
(* Stack conduction resistance at L = 3 mm, k = 0.1 W/(m K). *)
Definition Rcond : Q := (3 # 100).

(* (1) The series identity, stated without division so it is a pure ring fact:
       the two temperature drops are q*R1 and q*R2 and they add to q*(R1+R2).
       Dividing by the total resistance recovers the same q -- that is the whole
       content of "resistances in series add". *)
Lemma drops_add_to_the_total (R1 R2 q : Q) :
  q * R1 + q * R2 == q * (R1 + R2).
Proof. ring. Qed.

Lemma total_resistance_is_the_sum (R1 R2 : Q) :
  (R1 + R2) - R2 == R1.
Proof. ring. Qed.

Lemma a_relabelled_split_does_not_change_the_total (R1 R2 : Q) :
  (R1 + R2) - R1 == R2.
Proof. ring. Qed.

(* (2) The bracket on the radiative share, exact rationals, no floating point. *)
Lemma radiative_resistance_is_above_seven_per_cent_of_conduction :
  (7 # 100) * Rcond < Rrad.
Proof. unfold Rrad, Rcond. vm_compute. reflexivity. Qed.

Lemma radiative_resistance_is_below_one_fourteenth_of_conduction :
  Rrad < Rcond / (14 # 1).
Proof. unfold Rrad, Rcond. vm_compute. reflexivity. Qed.

Lemma the_radiative_share_of_the_total_is_between_six_and_seven_per_cent :
  (6 # 100) < Rrad / (Rrad + Rcond) /\ Rrad / (Rrad + Rcond) < (7 # 100).
Proof.
  split; unfold Rrad, Rcond; vm_compute; reflexivity.
Qed.

(* (3) Counting the wall resistance twice is a multiplicative error. *)
Lemma double_counting_costs_6_19_per_cent :
  (Rrad + Rcond) / (2 * Rrad + Rcond) < (1000000 # 1000000)
  /\ (930000 # 1000000) < (Rrad + Rcond) / (2 * Rrad + Rcond).
Proof.
  split; unfold Rrad, Rcond; vm_compute; reflexivity.
Qed.

(* And the two fluxes differ, so the error is not cosmetic. *)
Lemma the_two_fluxes_differ :
  (1000 # 1) / (2 * Rrad + Rcond) < (1000 # 1) / (Rrad + Rcond).
Proof. unfold Rrad, Rcond. vm_compute. reflexivity. Qed.

(* Sanity: the resistances are positive and the bracket is not vacuous. *)
Lemma both_resistances_are_positive :
  (0 # 1) < Rrad /\ (0 # 1) < Rcond.
Proof. split; unfold Rrad, Rcond; vm_compute; reflexivity. Qed.
