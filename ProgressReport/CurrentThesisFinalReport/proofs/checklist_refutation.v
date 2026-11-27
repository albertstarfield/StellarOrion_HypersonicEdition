From Stdlib Require Import Arith Lia.
Definition checklist_items : nat := 43.
Definition checked_items : nat := 43.
Theorem all_checked : checklist_items = checked_items.
Proof. reflexivity. Qed.
Example not_all_checked (h : checked_items < checklist_items) : False.
Proof. unfold checked_items, checklist_items in h. lia. Qed.
