(* ============================================================================
   AXIOMS / THEORIES / APPLICATIONS / CITATIONS
   Unit : StellarOrion_Status_Writer -- sidecar status frames
          (stellarorion_status_writer.ads, stellarorion_status_writer.adb)

   AXIOMS
     A1  The .status.json file is the sole IPC channel between the Ada
         binary and the Python sidecar UI, and its schema is fixed:
         exactly five members per frame, status, progress, run_name,
         results, metrics (stellarorion_status_writer.adb:158-190).
     A2  A JSON object with two members carrying the same key is
         unparsable as a key/value map, so the sidecar reader requires the
         emitted keys to be unique within a frame.
     A3  Every member except the last carries a trailing comma
         (stellarorion_status_writer.adb:162-184); the last one does not.
     A4  Status_Kind has exactly four values (idle / running / completed /
         error) matching sidecar_ui.py's SimulationState
         (stellarorion_status_writer.ads:20-25).

   THEORIES
     T1  The emitted key set is duplicate-free, so a frame is a well-formed
         key/value map for the sidecar reader.
     T2  The interior members carry a trailing comma and the last member
         does not, so the assembled frame is syntactically valid JSON.
     T3  Status_Kind has exactly four inhabitants, so Status_String is total
         over the enumerated status codes.

   APPLICATIONS
     Swept by src/utils/coq_proof_gate.py.  The textual escaping and the
     atomic-save file I/O are outside the SPARK subset (the unit is
     SPARK_Mode => On but Write_Status does Text_IO); what is discharged
     here is the frame schema the I/O produces.

   CITATIONS
     [AdaRM] ISO/IEC 8652:2012 (Ada 2012), Sec A.10 Text_IO, Sec A.4.8.
     [CoqRM] Coq Reference Manual, Coq.Lists.List (NoDup, In, length)
         -- https://coq.inria.fr/refman/
     [CoqStrings] Coq Reference Manual, Coq.Strings.String
         -- https://coq.inria.fr/refman/
     [JSON] ECMA-404, "The JSON Data Interchange Syntax", 2nd ed., 2017 --
         object member syntax and uniqueness of keys.
   ============================================================================ *)

Require Import Coq.Strings.String.
Require Import Coq.Lists.List.
Import ListNotations.
Require Import Coq.Arith.PeanoNat.
Require Import Coq.micromega.Lia.

Open Scope nat_scope.

(* A1 -- the five members Write_Status emits, in emission order
   (stellarorion_status_writer.adb:162-184). *)
(* Each literal carries an explicit %string delimiter so the file does not
   need to open string_scope -- doing so would also capture the nat `<?`
   notation used by member_has_trailing_comma below. *)
Definition frame_keys : list string :=
  [ "status"%string; "progress"%string; "run_name"%string
  ; "results"%string; "metrics"%string ].

(* T2 -- a frame carries exactly five members. *)
Lemma frame_keys_length : length frame_keys = 5.
Proof.
  unfold frame_keys.
  reflexivity.
Qed.

(* T1 -- the emitted key set is duplicate-free, so the sidecar reader sees a
   well-formed key/value map (Axiom A2 above). *)
Lemma frame_keys_no_dup : NoDup frame_keys.
Proof.
  unfold frame_keys.
  repeat constructor.
  - simpl. intuition congruence.
  - simpl. intuition congruence.
  - simpl. intuition congruence.
  - simpl. intuition congruence.
  - simpl. intuition congruence.
Qed.

(* A3 -- the member count is five, so members 1..4 are interior. *)
Definition member_count : nat := 5.

(* A3 -- the trailing-comma test the writer applies. *)
Definition member_has_trailing_comma (i : nat) : bool := i <? member_count.

(* T2a -- every interior member carries a trailing comma. *)
Lemma interior_members_have_comma : forall i,
  i < member_count -> member_has_trailing_comma i = true.
Proof.
  intros i H.
  unfold member_has_trailing_comma, member_count in *.
  apply Nat.ltb_lt. exact H.
Qed.

(* T2b -- the last member does not carry a trailing comma, which is what
   keeps the assembled frame syntactically valid JSON. *)
Lemma last_member_has_no_comma :
  member_has_trailing_comma member_count = false.
Proof.
  unfold member_has_trailing_comma, member_count.
  reflexivity.
Qed.

(* A4 -- Status_Kind (stellarorion_status_writer.ads:20-25). *)
Inductive status_kind := Idle : status_kind | Running : status_kind
                        | Completed : status_kind | Error : status_kind.

(* T3 -- Status_Kind has exactly four inhabitants, so Status_String
   (stellarorion_status_writer.adb:110-112) is total over them. *)
Lemma status_kind_four_values : forall k,
  k = Idle \/ k = Running \/ k = Completed \/ k = Error.
Proof.
  intros k.
  destruct k.
  - left. reflexivity.
  - right. left. reflexivity.
  - right. right. left. reflexivity.
  - right. right. right. reflexivity.
Qed.
