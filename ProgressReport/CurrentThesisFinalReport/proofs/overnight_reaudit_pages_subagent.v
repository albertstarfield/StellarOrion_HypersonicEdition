(* Page-budget arithmetic re-checked on the SlopDistrust retry turn. *)
From Stdlib Require Import Arith.
Example page_sum : (12 - 1) + (69 - 12) + (101 - 69) + (146 - 101) + (151 - 146) = 150.
Proof. vm_compute. reflexivity. Qed.
Example page_gap : 151 - 1 - 100 = 50.
Proof. vm_compute. reflexivity. Qed.
