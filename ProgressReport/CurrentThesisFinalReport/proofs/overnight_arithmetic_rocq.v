(* Rocq 9.3 core-arithmetic check of the numeric claims added to
   tab:analytic_validation on 2026-11-27.  Constants re-read this turn from
   chapter_03_methodology.tex eq:sutton_graves/eq:heat_load and
   chapter_04_results.tex:196-208.  Integer-scaled forms avoid floats; numbers
   are written as small literal products so no large-nat warning is emitted. *)

From Stdlib Require Import Bool.

(* Sutton-Graves flux: 25.3620035 W/cm^2, i.e. scaled by 1000 it is
   25*1000+362 = 25362, strictly between 25360 (25.36) and 25370 (25.37). *)
Goal Nat.ltb (25 * 1000 + 360) (25 * 1000 + 362) = true.
Proof. vm_compute. reflexivity. Qed.
Goal Nat.ltb (25 * 1000 + 362) (25 * 1000 + 370) = true.
Proof. vm_compute. reflexivity. Qed.

(* Heat load rounds to 344.48 J/cm^2: scaled by 100 it is 344*100+48,
   strictly between 34447 and 34449. *)
Goal Nat.ltb (344 * 100 + 47) (344 * 100 + 48) = true.
Proof. vm_compute. reflexivity. Qed.
Goal Nat.ltb (344 * 100 + 48) (344 * 100 + 49) = true.
Proof. vm_compute. reflexivity. Qed.

(* Both +76.6% entries: ((2536-1436)*1000)/1436 and
   ((34448-19506)*1000)/19506, integer division giving 766 per mille. *)
Goal Nat.div (11 * 100 * 1000) (14 * 100 + 36) = 7 * 100 + 66.
Proof. vm_compute. reflexivity. Qed.
Goal Nat.div (149 * 100 * 1000 + 42 * 1000) (195 * 100 + 6) = 7 * 100 + 66.
Proof. vm_compute. reflexivity. Qed.
