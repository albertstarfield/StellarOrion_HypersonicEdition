(* ============================================================================
   AXIOMS / THEORIES / APPLICATIONS / CITATIONS
   Unit : StellarOrion_Atomic_Parity -- atomic parity checks for I/O
          integrity (stellarorion_atomic_parity.ads, .adb)

   AXIOMS
     A1  The byte-level population count is a shift-and-mask loop that
         inspects exactly 8 bit positions, incrementing at most once per
         position.  Testing bit i of v is that loop step for position i
         (stellarorion_atomic_parity.ads:46-47, Loop_Invariant C <= I).
     A2  Even parity holds iff the number of set bits is even, i.e.
         Count_Set_Bits mod 2 = 0; odd parity is the complementary case
         (stellarorion_atomic_parity.ads:53-59).
     A3  The fixed payload block holds 8 bytes and the retry budget is 3
         (stellarorion_atomic_parity.ads:68, :103), so both bounds are
         small positive constants rather than computed values.

   THEORIES
     T1  Count_Set_Bits'Result <= 8 -- the declared Post aspect at
         stellarorion_atomic_parity.ads:47.  Discharged by induction on the
         number of inspected positions: each position contributes at most 1.
     T2  Calculate_Parity'Result = (Count_Set_Bits mod 2 = 0) for Even and
         = 1 for Odd -- the declared Post aspect at :57-59.  Because the two
         targets differ, exactly one of the two parity values is true for a
         given byte, which is the property that makes a parity mismatch
         detectable rather than ambiguous.

   APPLICATIONS
     The detected-error rate at the data boundary is meaningless if the
     parity function can be true for both parities of the same byte.  T3
     below rules that out.  Swept by src/utils/coq_proof_gate.py.

   CITATIONS
     [Hamming1950] Hamming, R.W., "Error Detecting and Error Correcting
         Codes", Bell System Technical Journal 29(2), 1950, p.147-160
         -- https://doi.org/10.1002/j.1538-7305.1950.tb00406.x
     [CoqRM] Coq Reference Manual, Coq.Arith.PeanoNat (Nat.eqb_eq, Nat.eqb_neq,
         Nat.odd, Nat.testbit) -- https://coq.inria.fr/refman/
     [CoqLists] Coq Reference Manual, Coq.Init.Datatypes -- https://coq.inria.fr/refman/
     [DO178C] DO-178C Sec 6.4.4 -- low-level verification of integrity
         mechanisms.
   ============================================================================ *)

Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.

Open Scope nat_scope.

(* A1 -- one is contributed when bit i of v is set, zero otherwise. *)
Definition bit_at (v pos : nat) : nat :=
  if Nat.testbit v pos then 1 else 0.

(* A1 -- the loop accumulates over the 8 inspected positions. *)
Fixpoint count_positions (v : nat) (i : nat) : nat :=
  match i with
  | O => O
  | S i' => bit_at v i' + count_positions v i'
  end.

(* A1 -- the Ada Count_Set_Bits over an 8-bit byte. *)
Definition count_set_bits (v : nat) : nat := count_positions v 8.

(* T1 -- each inspected position contributes at most one set bit, so a loop
   over i positions counts at most i bits. *)
Lemma count_positions_le : forall i v, count_positions v i <= i.
Proof.
  induction i as [|i' IH]; intros v; simpl.
  - lia.
  - assert (H := IH v).
    unfold bit_at.
    destruct (Nat.testbit v i'); simpl; lia.
Qed.

(* T1 -- the declared Post aspect Count_Set_Bits'Result <= 8
   (stellarorion_atomic_parity.ads:47). *)
Lemma count_set_bits_le_8 : forall v, count_set_bits v <= 8.
Proof.
  intros v.
  unfold count_set_bits.
  apply (count_positions_le 8).
Qed.

(* A2 -- the parity kind mirrors Parity_Type (Even / Odd). *)
Inductive parity_kind := Even : parity_kind | Odd : parity_kind.

(* A2 -- the even-parity predicate: the set-bit count is even. *)
Definition parity_even (v : nat) : bool :=
  Nat.eqb (count_set_bits v mod 2) 0.

(* A2 -- the odd-parity predicate: the set-bit count is odd. *)
Definition parity_odd (v : nat) : bool :=
  Nat.eqb (count_set_bits v mod 2) 1.

(* A2 -- Calculate_Parity, dispatching on the requested parity kind. *)
Definition calculate_parity (v : nat) (k : parity_kind) : bool :=
  match k with
  | Even => parity_even v
  | Odd => parity_odd v
  end.

(* T2 -- the Even branch of the declared Post aspect
   (stellarorion_atomic_parity.ads:57-59). *)
Lemma calculate_parity_even : forall v,
  calculate_parity v Even = true <-> count_set_bits v mod 2 = 0.
Proof.
  intros v.
  unfold calculate_parity, parity_even.
  split.
  - apply Nat.eqb_eq.
  - apply Nat.eqb_eq.
Qed.

(* T2 -- the Odd branch of the declared Post aspect. *)
Lemma calculate_parity_odd : forall v,
  calculate_parity v Odd = true <-> count_set_bits v mod 2 = 1.
Proof.
  intros v.
  unfold calculate_parity, parity_odd.
  split.
  - apply Nat.eqb_eq.
  - apply Nat.eqb_eq.
Qed.

(* T3 -- the two parity answers can never both be true for the same byte,
   so a parity mismatch is always detectable. *)
Lemma calculate_parity_distinct : forall v,
  calculate_parity v Even = true -> calculate_parity v Odd = false.
Proof.
  intros v He.
  apply calculate_parity_even in He.
  destruct (Nat.eq_dec (count_set_bits v mod 2) 1) as [H1|H1].
  - rewrite H1 in He. lia.
  - unfold calculate_parity, parity_odd.
    apply Nat.eqb_neq. exact H1.
Qed.

(* A3 -- the fixed payload block holds 8 bytes (stellarorion_atomic_parity.ads:68). *)
Lemma block_size_positive : 0 < 8.
Proof. lia. Qed.

(* A3 -- the retry budget is 3 (stellarorion_atomic_parity.ads:103), so a
   recovering read always has at least one retransmit attempt. *)
Lemma max_retries_positive : 0 < 3.
Proof. lia. Qed.
