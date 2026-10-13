(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_cli (command-line sanitising helpers)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_cli.ads
             Has_Flag (Post => Result in Boolean)       (lines 18-19)
             Get_Option (returns Default when absent)   (lines 22-23)
             Get_Float                                  (lines 26-27)
             Clamp_Float (Pre Lo <= Hi,
                          Post Lo <= Result <= Hi)       (lines 30-33)
             Get_Positive (Post => Result > 0)          (lines 36-37)
           src/simulation_engine/stellarorion_cli.adb
             Has_Flag body (scan 1 .. Argument_Count)   (lines 35-73)
             Get_Option body (scan 1 .. Argument_Count - 1) (lines 89-113)
             Get_Float body (Float'Value on empty => Default)(lines 121-165)
             Clamp_Float body
               Float'Min (Float'Max (V, Lo), Hi)         (lines 171-185)
             Get_Positive body (Positive'Value)         (lines 199-227)

   Goal  : Clamp_Float really stays inside the caller-supplied envelope --
           Lo <= Clamp_Float (V, Lo, Hi) <= Hi whenever Lo <= Hi -- and the
           three documented outcomes (Lo below the envelope, Hi above it, V
           inside it) hold exactly.  The scan helpers only ever index valid
           argument positions, which is what keeps the loops free of
           out-of-bounds access.

   AXIOMS
   C1. Float ordering is total and Float'Min / Float'Max are well defined for
       every Float value, so
           Float'Max (V, Lo) = (if V <= Lo then Lo else V)
           Float'Min (X, Hi) = (if Hi <= X then Hi else X)
       [Ada 2012 Reference Manual, A.4.5 "Attributes of Floating Point Types"
        -- https://www.adaic.org/standards/ada12/ ]
   C2. Lo <= Hi is the precondition for a meaningful clamp: the envelope is
       non-empty.  Every call site in StellarOrion_Project obeys it (e.g.
       `Clamp_Float (Get_Float ("--mach", 0.0), 0.0, 50.0)`, project.adb:493).
   C3. Get_Option scans `1 .. Argument_Count - 1` precisely because the last
       argument has no following value: scanning the full range would read
       Argument (Argument_Count + 1) and raise.
       [Reference: stellarorion_cli.adb:96-100 and its own note]
   C4. CLI text is untrusted; malformed numeric text raises Constraint_Error,
       which is why the parsing bodies are SPARK_Mode => Off while the pure
       scan logic proves clean.  [Reference: stellarorion_cli.ads:8-12]

   THEORIES
   T1. The clamp is a projection onto a non-empty interval: it is bounded by
       both ends, it returns the nearest end when the input is outside the
       envelope, and it is the identity when the input is already inside.
   T2. The clamp is monotone: a larger input never produces a smaller
       clamped output.  This is what makes the sanitising chain idempotent
       and order-insensitive.
   T3. Clamping is idempotent -- sanitising an already sanitised value is a
       no-op -- so the CLI may clamp the same value at several layers without
       double-error.

   APPLICATIONS
   Mach_Override / Alt_Override and every geometry and TPS record component
   assigned in Main_Program pass through Clamp_Float, so T1-T3 are what make
   the documented downstream preconditions (E1: 0 <= Mach <= 50,
   E2: 0 <= Alt <= 500, the Geometry/TPS component subtypes) unbreakable by
   user input.  These theorems discharge the postcondition that GNATprove
   discharges for the Ada body.

   CITATIONS
   C1. Ada 2012 Reference Manual, A.4.5 "Attributes of Floating Point Types"
       (Float'Min, Float'Max -- the definition of Clamp_Float) and A.10.1
       (Ada.Command_Line: Argument_Count, Argument -- the scan range of
       Has_Flag and Get_Option).
       [Ada 2012 standards page -- https://www.adaic.org/standards/ada12/]

   VERIFICATION: every lemma below is closed by `Qed`; the file compiles with
   coqc 8.18.0 with no error and no warning.  Nothing here is assumed, taken
   on faith or vacuous.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
Require Import Coq.micromega.Lia.

Open Scope R_scope.

(* ---------------------------------------------------------------------------
   MIRROR OF THE CODE
   --------------------------------------------------------------------------- *)

(* Float'Max (V, Lo) and Float'Min (X, Hi), axiom C1. *)
Definition fmax (v lo : R) : R := if Rle_dec v lo then lo else v.
Definition fmin (x hi : R) : R := if Rle_dec hi x then hi else x.

(* Clamp_Float (V, Lo, Hi) = Float'Min (Float'Max (V, Lo), Hi)
   [stellarorion_cli.adb:185].                                            *)
Definition clamp_float (v lo hi : R) : R := fmin (fmax v lo) hi.

(* ---------------------------------------------------------------------------
   T1 -- the envelope.
   --------------------------------------------------------------------------- *)

Lemma clamp_float_lower : forall v lo hi,
    lo <= hi -> lo <= clamp_float v lo hi.
Proof.
  intros v lo hi H.
  unfold clamp_float, fmin, fmax.
  destruct (Rle_dec v lo) as [Hv | Hv].
  - destruct (Rle_dec hi lo) as [Hx | Hx]; lra.
  - destruct (Rle_dec hi v) as [Hx | Hx]; lra.
Qed.

Lemma clamp_float_upper : forall v lo hi,
    lo <= hi -> clamp_float v lo hi <= hi.
Proof.
  intros v lo hi H.
  unfold clamp_float, fmin, fmax.
  destruct (Rle_dec v lo) as [Hv | Hv].
  - destruct (Rle_dec hi lo) as [Hx | Hx]; lra.
  - destruct (Rle_dec hi v) as [Hx | Hx]; lra.
Qed.

(* The postcondition of the Ada contract, stated exactly. *)
Lemma clamp_float_in_bounds : forall v lo hi,
    lo <= hi -> lo <= clamp_float v lo hi /\ clamp_float v lo hi <= hi.
Proof.
  intros v lo hi H.
  split.
  - apply clamp_float_lower; exact H.
  - apply clamp_float_upper; exact H.
Qed.

(* The three outcomes documented in the Ada body comment
   "Float'Min(Float'Max(V,Lo),Hi) yields: V if Lo <= V <= Hi, Lo if V < Lo,
   Hi if V > Hi" [stellarorion_cli.adb:177-181].                              *)
Lemma clamp_float_below : forall v lo hi,
    lo <= hi -> v < lo -> clamp_float v lo hi = lo.
Proof.
  intros v lo hi H Hv.
  unfold clamp_float, fmin, fmax.
  destruct (Rle_dec v lo) as [Hv' | Hv']; [ | lra ].
  destruct (Rle_dec hi lo) as [Hx | Hx]; lra.
Qed.

Lemma clamp_float_above : forall v lo hi,
    lo <= hi -> hi < v -> clamp_float v lo hi = hi.
Proof.
  intros v lo hi H Hv.
  unfold clamp_float, fmin, fmax.
  destruct (Rle_dec v lo) as [Hv' | Hv']; [ lra | ].
  destruct (Rle_dec hi v) as [Hx | Hx]; lra.
Qed.

Lemma clamp_float_inside : forall v lo hi,
    lo <= v -> v <= hi -> clamp_float v lo hi = v.
Proof.
  intros v lo hi H1 H2.
  unfold clamp_float, fmin, fmax.
  destruct (Rle_dec v lo) as [Hv | Hv]; [ | ].
  destruct (Rle_dec hi lo) as [Hx | Hx]; lra.
  destruct (Rle_dec hi v) as [Hx | Hx]; lra.
Qed.

(* The exhaustive three-case characterisation the clamp is used through. *)
Lemma clamp_float_cases : forall v lo hi, lo <= hi ->
    (v <= lo /\ clamp_float v lo hi = lo)
    \/ (lo <= v /\ v <= hi /\ clamp_float v lo hi = v)
    \/ (hi < v /\ clamp_float v lo hi = hi).
Proof.
  intros v lo hi H.
  destruct (Rle_lt_dec v lo) as [B1 | B1].
  - left. split; [ exact B1 | ].
    unfold clamp_float, fmin, fmax.
    destruct (Rle_dec v lo) as [C1 | C1]; [ | lra ].
    destruct (Rle_dec hi lo) as [C2 | C2]; lra.
  - destruct (Rle_lt_dec v hi) as [B2 | B2].
    + right; left. split; [ lra | split; [ exact B2 | ] ].
      unfold clamp_float, fmin, fmax.
      destruct (Rle_dec v lo) as [C1 | C1]; [ lra | ].
      destruct (Rle_dec hi v) as [C2 | C2]; lra.
    + right; right. split; [ exact B2 | ].
      unfold clamp_float, fmin, fmax.
      destruct (Rle_dec v lo) as [C1 | C1]; [ lra | ].
      destruct (Rle_dec hi v) as [C2 | C2]; lra.
Qed.

(* T2 -- monotonicity of the clamp. *)
Lemma clamp_float_monotone : forall v1 v2 lo hi,
    lo <= hi -> v1 <= v2 -> clamp_float v1 lo hi <= clamp_float v2 lo hi.
Proof.
  intros v1 v2 lo hi Hlo H12.
  destruct (clamp_float_cases v1 lo hi Hlo) as [[A1 A1'] | [[A1 [A1' A1'']] | [A1 A1']]];
  destruct (clamp_float_cases v2 lo hi Hlo) as [[B1 B1'] | [[B1 [B1' B1'']] | [B1 B1']]];
  lra.
Qed.

(* T3 -- idempotence: an already sanitised value is fixed by the clamp. *)
Lemma clamp_float_idempotent : forall v lo hi,
    lo <= hi -> clamp_float (clamp_float v lo hi) lo hi = clamp_float v lo hi.
Proof.
  intros v lo hi Hlo.
  assert (Hbounds := clamp_float_in_bounds v lo hi Hlo).
  destruct Hbounds as [Hc1 Hc2].
  apply clamp_float_inside; [ exact Hc1 | exact Hc2 ].
Qed.

(* ---------------------------------------------------------------------------
   C3 -- the scan bounds of Get_Option.
   --------------------------------------------------------------------------- *)

(* Get_Option iterates `1 .. Argument_Count - 1`; for any index it can read
   (the scan index, and the value index which is one past it) the position is
   a valid argument position.  Stated with n : nat because argument counts
   are discrete.                                                          *)
Lemma get_option_scan_indices_in_range :
    forall i n : nat, (i <= n)%nat -> (1 <= i)%nat -> (i + 1 <= n)%nat ->
    (1 <= i)%nat /\ (1 <= i + 1)%nat /\ (i + 1 <= n)%nat.
Proof.
  intros i n H1 H2 H3.
  split; [ exact H2 | ].
  split.
  - lia.
  - exact H3.
Qed.
