(*  design_point_exact.v

    A different method from the last four turns: no symbolic algebra, no
    `decide` on Nat, no `nra`.  This file evaluates the actual design-point
    numbers as exact rationals with `vm_compute`, so the claims about 140399,
    3362, 143760, 193154 and the 7,407 1/m threshold are checked by machine
    arithmetic on the exact decimals -- not by floating point, and not by my
    transcription.

    Why it matters: every number in the deck has so far been checked by Python
    floats.  A float cannot tell 143,761 from 143,760 once it has been rounded
    into a slide, and it cannot certify that the threshold lies between 7407 and
    7408.  Exact rationals can.

    Compiled with:  rocq compile proofs/design_point_exact.v
*)

From Stdlib Require Import QArith Qpower.
Open Scope Q_scope.

(* Stefan-Boltzmann as the thesis derives it (appendix.tex:811), to ten digits. *)
Definition sigma : Q := (5670374419 # 100000000000000000).

(* The Rosseland threshold: k_R(T) = k_gas  =>  kappa = 16*sigma*T^3/(3*k_gas). *)
Definition kstar (T kgas : Q) : Q := 16 * sigma * (T * T * T) / (3 * kgas).

(* 1. The deck's two shares sum to one more than the total it prints: the
      residual is -1 W/m^2, not +1. *)
Lemma deck_overshoots_exactly :
  140399 + 3362 = 143760 + 1.
Proof. vm_compute. reflexivity. Qed.

(* 2. The thesis's closure at appendix.tex:820 is inside 0.19 %:
      193520 <= 193154 * 1.0019. *)
Lemma thesis_closure_inside_019_percent :
  (193520 # 1) <= (193154 # 1) * (10019 # 10000).
Proof. vm_compute. intro H. discriminate H. Qed.

(* 3. The deck's case and the thesis's case are different operating points:
      143760/75 < 193154/80, and q/eps fixes T^4. *)
Lemma deck_case_is_cooler_than_thesis_case :
  (143760 # 1) / (75 # 1) < (193154 # 1) / (80 # 1).
Proof. vm_compute. reflexivity. Qed.

(* 4. THE THRESHOLD IS EXACTLY BRACKETED: at T = 1348 K and k_gas = 0.1 W/(m K),
      the extinction coefficient that makes the Rosseland term equal the gas
      conductivity lies strictly between 7407 and 7408 1/m.  So 740 is below it
      (the term dominates by an order of magnitude) and 74080 is above it. *)
Lemma kstar_above_7407 :
  (7407 # 1) < kstar (1348 # 1) (1 # 10).
Proof. unfold kstar, sigma. vm_compute. reflexivity. Qed.

Lemma kstar_below_7408 :
  kstar (1348 # 1) (1 # 10) < (7408 # 1).
Proof. unfold kstar, sigma. vm_compute. reflexivity. Qed.

(* 5. What hiding the term costs, exactly: a share dq = 14376 W/m^2 at 1348 K
      is reproduced by raising the conduction coefficient by dq/T = 14376/1348,
      because (dq/T^4)*T^3 = dq/T.  Exact, not approximate. *)
Lemma compensating_error_is_exactly_dq_over_T :
  (14376 # 1) / ((1348 * 1348 * 1348 * 1348) # 1) * ((1348 * 1348 * 1348) # 1)
    == (14376 # 1) / (1348 # 1).
Proof. vm_compute. reflexivity. Qed.

(* 6. And that compensating error is more than a hundredfold the illustrative
      0.1 W/(m K) gas conductivity: 14376/1348 > 100 * 0.1. *)
Lemma compensating_error_exceeds_hundredfold :
  (14376 # 1) / (1348 # 1) > (100 # 1) * (1 # 10).
Proof. vm_compute. reflexivity. Qed.

(* 7. Sanity: the bracket in (4) is not vacuous -- 7407 < 7408. *)
Lemma bracket_is_nonempty : (7407 # 1) < (7408 # 1).
Proof. vm_compute. reflexivity. Qed.
