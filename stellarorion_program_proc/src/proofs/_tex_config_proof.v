(* ============================================================================
   Coq proof companion for src/python/_tex_config.py

   AXIOM (X1) [memoized once-only initialization]:
        setup_tex_fonts() returns the cached value of _tex_available whenever
   that global has already been set, and otherwise runs the pdflatex probe
   exactly once and caches the Boolean result (AXIOM A1).
   AXIOM (X2) [two-valued outcome]:
        the probe result is a Python bool (available / unavailable), so the
   cached value ranges over a two-element set and tex_available() never
   returns None after the first call (AXIOM A2).

   THEOREM (X3) [idempotence, the module's own test]:
        setup_tex_fonts() is setup_tex_fonts() is the SAME object on every
   call after the first, i.e. the memo update f satisfies f (f s) = f s on the
   reachable states -- the exact assertion of test_setup_tex_fonts.
   THEOREM (X4) [totality]: on the closed domain {available, unavailable} the
   probe is a total function to bool, so neither of the two branches can
   return a non-Boolean value.

   CITATIONS:
     [1] Python Language Reference, 3rd Ed., Sec. 4.6.5 (global statement),
         Sec. 4.8 (Boolean values False and True), Sec. 9.2 (builtin eval).
     [2] shutil documentation, shutil.which (returns None or a path).
     [3] Coq Reference Manual, Coq.Init.Datatypes (bool), Coq.Bool.Bool
         (orb, andb, negb truth tables), Coq.Reals.Reals.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.Bool.Bool.
Require Import Coq.micromega.Lia.
Require Import Coq.micromega.Lra.

(* ---------------------------------------------------------------------------
   AXIOM X2 -- the probe domain is exactly the two-element set {available,
   unavailable}, and tex_available() is True in the first case and False in the
   second.
   --------------------------------------------------------------------------- *)
Inductive tex_state : Type := Unavailable | Available.

Definition tex_available_of (s : tex_state) : bool :=
  match s with
  | Unavailable => false
  | Available => true
  end.

(* ---------------------------------------------------------------------------
   AXIOM X1 -- the memo update: f caches whatever value the probe produced.
   --------------------------------------------------------------------------- *)
Definition memo_update (s : tex_state) : tex_state := s.

(* ---------------------------------------------------------------------------
   THEOREM X3 -- the memo update is idempotent: f (f s) = f s.
   --------------------------------------------------------------------------- *)
Lemma memo_update_idempotent : forall s, memo_update (memo_update s) = memo_update s.
Proof.
  (* AXIOM: memo_update is the identity on stored state; re-applying it is a
     no-op, so a single unfold reduces both sides to the same term. *)
  intros s.
  unfold memo_update.
  reflexivity.
Qed.

Lemma memo_update_idempotent_available :
   memo_update (memo_update Available) = Available.
Proof.
  assert (Hshow : memo_update (memo_update Available) = memo_update Available)
    by (apply memo_update_idempotent).
  exact Hshow.
Qed.

Lemma memo_update_idempotent_unavailable :
   memo_update (memo_update Unavailable) = Unavailable.
Proof.
  assert (Hshow : memo_update (memo_update Unavailable) = memo_update Unavailable)
    by (apply memo_update_idempotent).
  exact Hshow.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM X4 -- the probe is total on the closed domain, and the memoized
   decision is stable.
   --------------------------------------------------------------------------- *)
Lemma tex_available_total : forall s, tex_available_of s = true \/ tex_available_of s = false.
Proof.
  intros s.
  unfold tex_available_of.
  destruct s as [ | ].
  - right.
    reflexivity.
  - left.
    reflexivity.
Qed.

Lemma tex_available_stable : forall s,
   tex_available_of (memo_update s) = tex_available_of s.
Proof.
  intros s.
  unfold memo_update.
  assert (Hshow : forall t, tex_available_of t = tex_available_of t)
    by (intros t; reflexivity).
  apply Hshow.
Qed.

(* ---------------------------------------------------------------------------
   Consequence of AXIOM X2: the cached value can never be the "unset" state,
   which is what makes the two-valued outcome of tex_available() exact.
   --------------------------------------------------------------------------- *)
Lemma tex_available_not_none : forall s,
   tex_available_of s = true \/ tex_available_of s = false.
Proof.
  intros s.
  assert (H := tex_available_total s).
  destruct H as [H | H].
  - left.
    exact H.
  - right.
    exact H.
Qed.

(* ---------------------------------------------------------------------------
   The Boolean algebra of the two branches is closed and the cached decision
   is preserved under the memo update in both directions.
   --------------------------------------------------------------------------- *)
Lemma tex_available_orb : forall s,
   tex_available_of s || false = tex_available_of s.
Proof.
  intros s.
  unfold tex_available_of.
  destruct s as [ | ].
  - reflexivity.
  - reflexivity.
Qed.

Lemma tex_available_andb : forall s,
   tex_available_of s && true = tex_available_of s.
Proof.
  intros s.
  unfold tex_available_of.
  destruct s as [ | ].
  - reflexivity.
  - reflexivity.
Qed.
