(*  fourth_root_bracket.v

    New method for this turn: KERNEL-EXECUTED NUMERIC ENCLOSURE.  No ring, no
    decision procedure over a grid -- the kernel evaluates exact rationals and
    the theorem is an integer bracket on a fourth root.

    Why: the deck's p. 50 verdict is not just prose, it is a numerical claim --
    "1,348 K recovered from (q_rad/(eps*sigma))^(1/4)".  That sentence can be
    checked, and it does not check out against the split printed on the same
    slide.  With sigma = 5.670374419e-8 (NIST CODATA, exact decimal) and
    eps = 0.85:

        q needed for 1348 K  = eps*sigma*1348^4 = 159143.9858964... W/m^2
        the slide's own split = 140399 + 3362 = 143761 W/m^2  (+1 residual)
        q = 143760 W/m^2      -> T in (1314, 1315) K,  not 1348 K
        q = 140399 W/m^2      -> T in (1306, 1307) K
        q =   3362 W/m^2      -> T in ( 513,  514) K

    So three of the slide's numbers cannot all be right at once.  To reconcile
    q = 143760 with T = 1348 K you would need an environment temperature in
    (751, 752) K -- checked below -- which is not the 300 K the report uses
    elsewhere.

    None of this touches the *structure* proved in telescoping.v and
    series_resistance.v: one radiative term at the surface, counted once.  It
    touches the arithmetic of the verification sentence itself.

    Compiled with:  rocq compile proofs/fourth_root_bracket.v
*)

From Stdlib Require Import QArith setoid_ring.Field_tac.
Open Scope Q_scope.

(* eps*sigma with sigma = 5670374419/10^17 (NIST, exact) and eps = 17/20. *)
Definition es : Q := (96396365123 # 2000000000000000000).

(* The flux whose fourth root is exactly 1348 K. *)
Definition Q1348 : Q := (1243312389815782649603 # 7812500000000000).

Lemma es_times_1348_to_the_fourth_is_Q1348 :
  es * (1348 * 1348 * 1348 * 1348) == Q1348.
Proof. unfold es, Q1348. vm_compute. reflexivity. Qed.

(* 1348 K sits at a flux of 159,143.98... W/m^2, not 143,760. *)
Lemma the_flux_that_yields_1348_is_between_159143_and_159144 :
  (159143 # 1) < Q1348 /\ Q1348 < (159144 # 1).
Proof. split; unfold Q1348; vm_compute; reflexivity. Qed.

(* The deck's total flux recovers a different temperature. *)
Lemma the_deck_total_flux_recovers_between_1314_and_1315 :
  (1314 * 1314 * 1314 * 1314 # 1) < (143760 # 1) / es
  /\ (143760 # 1) / es < (1315 * 1315 * 1315 * 1315 # 1).
Proof. split; unfold es; vm_compute; reflexivity. Qed.

(* The conduction share recovers its own temperature. *)
Lemma the_conduction_share_recovers_between_1306_and_1307 :
  (1306 * 1306 * 1306 * 1306 # 1) < (140399 # 1) / es
  /\ (140399 # 1) / es < (1307 * 1307 * 1307 * 1307 # 1).
Proof. split; unfold es; vm_compute; reflexivity. Qed.

(* And so does the radiation share the slide quotes. *)
Lemma the_radiation_share_recovers_between_513_and_514 :
  (513 * 513 * 513 * 513 # 1) < (3362 # 1) / es
  /\ (3362 # 1) / es < (514 * 514 * 514 * 514 # 1).
Proof. split; unfold es; vm_compute; reflexivity. Qed.

(* The only environment temperature that reconciles q = 143760 with T = 1348. *)
Lemma reconciling_environment_temperature_is_between_751_and_752 :
  (751 * 751 * 751 * 751 # 1) < (Q1348 - (143760 # 1)) / es
  /\ (Q1348 - (143760 # 1)) / es < (752 * 752 * 752 * 752 # 1).
Proof. split; unfold Q1348, es; vm_compute; reflexivity. Qed.

(* So the two numbers on the slide are not the same number. *)
Lemma the_flux_for_1348_is_not_the_deck_total :
  Q1348 == (143760 # 1) -> False.
Proof. unfold Q1348. vm_compute. intros H. discriminate H. Qed.

(* And the split printed as an identity is off by exactly one. *)
Lemma the_split_is_off_by_one :
  (140399 + 3362)%Z = (143760 + 1)%Z.
Proof. vm_compute. reflexivity. Qed.

(* Sanity: es is positive, so every division above is defined. *)
Lemma es_is_positive : (0 # 1) < es.
Proof. unfold es. vm_compute. reflexivity. Qed.
