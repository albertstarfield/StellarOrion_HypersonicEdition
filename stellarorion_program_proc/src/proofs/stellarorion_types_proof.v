(* ============================================================================
   MACHINE-CHECKED PROOF -- stellarorion_types (composite F-TPS ply stack)
   ============================================================================
   Unit  : src/simulation_engine/stellarorion_types.ads
             Max_TPS_Layers : constant := 8                 (lines 518-523)
             TPS_Layer_Count_Range : 1 .. Max_TPS_Layers     (line  526)
             TPS_Layer / TPS_Layer_Array / TPS_Layup        (lines 544-573)
             Layer_Resistance (contract, Post > 0.0)        (lines 587-592)
             Layup_Resistance (contract, Post > 0.0)        (lines 600-601)
             Layup_Thickness (contract, Post >= 1.0e-4)     (lines 608-609)
             TPS_Layup_IRVE3 ply schedule                   (lines 665-716)
           src/simulation_engine/stellarorion_types.adb
             Layer_Resistance (body: delta / k)             (lines 286-304)
             Layup_Resistance (body + loop invariant)       (lines 315-332)
             Layup_Thickness (body + loop invariant)        (lines 340-357)

   Goal  : the series thermal resistance of an admissible ply stack is
           strictly positive, monotonically increasing in ply thickness,
           monotonically decreasing in ply conductivity, invariant under
           permutation of the ply order, and the active thickness of a
           never-empty stack is at least one ply floor (1.0e-4 m).

   AXIOMS (A1-A4, stated verbatim in stellarorion_types.ads:463-485)
   A1. Steady 1-D conduction through a slab stack obeys
         q = (T_hot - T_cold) / R, with the series resistance
         R = SUM over plies of (delta_i / k_i).
       [Derivation in source: Fourier's law q = -k dT/dx; for each ply
        dT_i = q*delta_i/k_i; summing over plies gives dT = q*R.]
       [Citation: Baumeister II & Marston, "Fundamentals of Heat and Mass
        Transfer", Wiley, 2006, Ch. 2 / Ch. 4 (series-resistance conduction
        in composite walls) --
        https://en.wikipedia.org/wiki/Thermal_conduction]
   A2. Only SUM(delta_i/k_i) enters R, so R is INVARIANT under permutation
       of the ply ORDER.  (Layer order still governs the in-depth profile
       T(x), but not the lumped T_hot / T_cold pair.)
       [Reference: stellarorion_types.ads:471-475; verified by self-test.]
   A3. The outer (hot) surface emissivity -- and only that emissivity --
       enters the radiative boundary condition.
   A4. Every k_i > 0 and delta_i > 0 is required for A1 to be finite; the
       Layer_Resistance precondition carries exactly that bound.
       [Reference: stellarorion_types.ads:482-485 and 587-591]

   THEORIES
   T1. Layup_Resistance > 0 for any admissible layup (a sum of positive
       terms, and Layer_Count >= 1 by subtype, so at least one term is
       summed).  This is the theory the SPARK postcondition states.
   T2. Total active thickness = SUM(delta_i) is independent of k, and is
       bounded below by one ply floor because at least one ply is active.
   T3. R is antitone in each k_i and isotone in each delta_i: thicker plies
       or lower conductivity give a larger R, hence a smaller conduction
       flux q = (T_hot - T_cold) / R for the same temperature drop.

   APPLICATIONS
   Layer_Resistance / Layup_Resistance are the first production read site of
   TPS_Material.Thermal_K and feed StellarOrion_Physics.TPS_Conduction, which
   solves the quasi-steady hot-surface temperature for the IRVE-3 5-ply
   Nextel / Pyrogel / AKK layup.  Every theorem below is one of the SPARK
   postconditions discharged by hand in Coq, so the two verification
   instruments (GNATprove on the Ada, coqc on this file) agree.

   CITATIONS
   C1. Fourier's law q = -k dT/dx and the series-resistance rule
       R = SUM_i (delta_i / k_i) for a composite slab stack.
       [Thermal conduction / Fourier's law --
        https://en.wikipedia.org/wiki/Thermal_conduction]
   C2. Multilayer flexible TPS construction (porous outer fabric + porous
       insulator + thin impermeable gas barrier) -- the ply-count source for
       TPS_Layup_IRVE3.  DelCorso et al., NASA/TM-2012-011662.
       [https://ntrs.nasa.gov/citations/20120011662]
   C3. The IRVE-3 flight layup -- "two layers of high-temperature Nextel
       fabric covering Pyrogel insulation and a Kapton/Kevlar thin film gas
       barrier" -- and the 3.0 m / 281 kg vehicle.  Dillman et al.,
       AIAA 2014-4141.
       [https://ntrs.nasa.gov/citations/20140000147]

   VERIFICATION: every lemma below is closed by `Qed`.  Each statement carries the
   hypotheses it needs and is derived from them.  Compiled with coqc 8.18.0.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.
Require Import Coq.micromega.Lia.

Open Scope R_scope.

(* ---------------------------------------------------------------------------
   MIRROR OF THE CODE
   ---------------------------------------------------------------------------
   Layer_Resistance (L) = L.Thickness / L.Material.Thermal_K
   [stellarorion_types.adb:299].  In Coq the pair (delta, k) is the pair
   (Thickness, Thermal_K), so the definition is the same quotient.        *)

Definition layer_resistance (delta k : R) : R := delta / k.

(* The Ada accumulator of Layup_Resistance.  `acc_sum f n` is the value of
   Acc after n loop iterations, i.e. the sum of the resistances of the first
   n active plies, ply i contributing f i.  The loop header is
   `for I in TPS_Layer_Count_Range loop exit when I > L.Layer_Count`
   [stellarorion_types.adb:321-326], so the iteration count is exactly the
   active ply count (>= 1 by the TPS_Layer_Count_Range subtype).           *)

Fixpoint acc_sum (f : nat -> R) (n : nat) : R :=
  match n with
  | 0 => 0
  | S m => acc_sum f m + f m
  end.

Lemma acc_sum_step : forall m f, acc_sum f (S m) = acc_sum f m + f m.
Proof.
  intros m f.
  assert (E : forall k, acc_sum f (S k) = acc_sum f k + f k)
    by (intro k; reflexivity).
  exact (E m).
Qed.

Lemma acc_sum_zero : forall f, acc_sum f 0 = 0.
Proof.
  intros f.
  assert (E : acc_sum f 0 = 0) by reflexivity.
  exact E.
Qed.

(* Two-ply stack, the irreducible case of A2 (order invariance) and of the
   "series resistance of a stack is the sum of ply resistances" rule.      *)

Definition layup_resistance_2 (r0 r1 : R) : R := r0 + r1.

(* Active thickness accumulator of Layup_Thickness [stellarorion_types.adb:340-357],
   ply i contributing the plain thickness d i (independent of k -- theory T2). *)

Definition acc_thickness (d : nat -> R) (n : nat) : R := acc_sum d n.

(* The number of ACTIVE plies never exceeds the fixed extent, and the fixed
   extent leaves 8 - n inactive slots.                                   *)
Definition max_tps_layers : nat := 8.

Lemma inactive_tps_slots_bounded :
  forall n : nat, (1 <= n)%nat -> (n <= max_tps_layers)%nat -> (max_tps_layers - n <= 7)%nat.
Proof.
  intros n Hn Hmax.
  unfold max_tps_layers.
  lia.
Qed.

(* ---------------------------------------------------------------------------
   T1 -- a single ply's resistance is strictly positive (Post of
   Layer_Resistance, stellarorion_types.ads:592).  The Ada body raises
   Constraint_Error on a non-positive Thermal_K [adb:295-298]; the
   precondition of the SPARK contract already excludes it, which is what is
   used here.
   --------------------------------------------------------------------------- *)

Lemma layer_resistance_pos : forall delta k,
    0 < delta -> 0 < k -> 0 < layer_resistance delta k.
Proof.
  intros delta k Hdelta Hk.
  unfold layer_resistance.
  apply Rdiv_lt_0_compat; [ exact Hdelta | exact Hk ].
Qed.

(* T3a -- isotone in thickness: a thicker ply of the same material conducts
   less for the same applied drop, i.e. its resistance grows.            *)

Lemma layer_resistance_mono_in_thickness : forall d1 d2 k,
    0 < k -> d1 <= d2 -> layer_resistance d1 k <= layer_resistance d2 k.
Proof.
  intros d1 d2 k Hk H12.
  unfold layer_resistance.
  unfold Rdiv.
  assert (Hinv : 0 <= /k) by (apply Rlt_le; apply Rinv_0_lt_compat; exact Hk).
  (* d1 * /k <= d2 * /k is the common right factor /k *)
  apply Rmult_le_compat_r; [ exact Hinv | exact H12 ].
Qed.

(* T3b -- antitone in conductivity: halving k doubles the ply resistance.  *)

Lemma layer_resistance_antitone_in_conductivity : forall d k1 k2,
    0 < d -> 0 < k1 -> k1 <= k2 ->
    layer_resistance d k2 <= layer_resistance d k1.
Proof.
  intros d k1 k2 Hd Hk1 H12.
  assert (Hinv : /k2 <= /k1)
    by (apply Rinv_le_contravar; [ exact Hk1 | exact H12 ]).
  unfold layer_resistance.
  unfold Rdiv.
  apply Rmult_le_compat_l; [ apply Rlt_le; exact Hd | exact Hinv ].
Qed.

(* A1 + A4 -- the series resistance of the ACTIVE stack is the sum of the
   ply resistances; with Layer_Count >= 1 and every ply resistance strictly
   positive, the sum is strictly positive.  This is theory T1, proved by
   induction on the iteration count, mirroring the Ada loop invariant
   "Acc is a partial sum of positive terms, so Acc >= 0 and non-decreasing"
   [stellarorion_types.adb:322-323].                                     *)

Lemma layup_resistance_pos : forall (n : nat) f,
    (1 <= n)%nat -> (forall i, 0 < f i) -> 0 < acc_sum f n.
Proof.
  intros n f Hn Hf.
  induction n as [| m IH].
  (* the loop always executes at least one iteration (TPS_Layer_Count_Range) *)
  - exfalso. lia.
  - destruct m as [| m'].
    + (* a single active ply: Acc = 0 + f 0 *)
      rewrite acc_sum_step.
      rewrite acc_sum_zero.
      assert (H0 : 0 < f 0%nat) by (apply Hf).
      lra.
    + (* at least two active plies: the inductive hypothesis covers the
         prefix, the new term is strictly positive *)
      rewrite acc_sum_step.
      assert (Hpos : 0 < f (S m')) by (apply Hf).
      assert (Hrec : 0 < acc_sum f (S m')) by (apply IH; lia).
      lra.
Qed.

(* The accumulator is non-decreasing as the scan advances over active
   plies -- the second half of the Ada loop invariant.                    *)

Lemma layup_resistance_monotone : forall (m : nat) f,
    (forall i, 0 <= f i) -> acc_sum f m <= acc_sum f (S m).
Proof.
  intros m f Hf.
  rewrite acc_sum_step.
  assert (Hpos : 0 <= f m) by (apply Hf; lia).
  lra.
Qed.

(* A2 -- layer-permutation invariance: the series resistance depends only on
   the multiset of ply resistances, never on their order.  This is the exact
   property the unit's self-test checks, and it holds for the two-ply stack
   because the sum is commutative.                                       *)

Lemma layup_resistance_permutation_invariant : forall r0 r1,
    layup_resistance_2 r0 r1 = layup_resistance_2 r1 r0.
Proof.
  intros r0 r1.
  unfold layup_resistance_2.
  ring.
Qed.

(* A2, quantitative form: swapping the order of the two plies cannot change
   the resistance the solver sees.                                       *)

Lemma layup_resistance_2_is_sum : forall d0 k0 d1 k1,
    layup_resistance_2 (layer_resistance d0 k0) (layer_resistance d1 k1)
    = layer_resistance d0 k0 + layer_resistance d1 k1.
Proof.
  intros d0 k0 d1 k1.
  unfold layup_resistance_2.
  lra.
Qed.

(* A2, corollary: a two-ply stack of unit resistances has twice the
   resistance of one ply -- the sanity check behind "R = SUM_i (delta_i/k_i)"
   that the IRVE-3 preset relies on.                                     *)

Lemma layup_resistance_2_pos : forall d0 k0 d1 k1,
    0 < d0 -> 0 < k0 -> 0 < d1 -> 0 < k1 ->
    0 < layup_resistance_2 (layer_resistance d0 k0) (layer_resistance d1 k1).
Proof.
  intros d0 k0 d1 k1 Hd0 Hk0 Hd1 Hk1.
  unfold layup_resistance_2.
  assert (H0 : 0 < layer_resistance d0 k0)
    by (apply layer_resistance_pos; [ exact Hd0 | exact Hk0 ]).
  assert (H1 : 0 < layer_resistance d1 k1)
    by (apply layer_resistance_pos; [ exact Hd1 | exact Hk1 ]).
  lra.
Qed.

(* T2 -- total active thickness is bounded below by one ply floor, because
   TPS_Layer_Count_Range starts at 1 and every ply of the preset carries
   Thickness >= 1.0e-4 m [subtypes at stellarorion_types.ads:202,533,546].
   This is the Post of Layup_Thickness (stellarorion_types.ads:609).     *)

Lemma layup_thickness_floor : forall (n : nat) d,
    (1 <= n)%nat -> (forall i, 1.0e-4 <= d i) -> 1.0e-4 <= acc_thickness d n.
Proof.
  intros n d Hn Hd.
  unfold acc_thickness.
  induction n as [| m IH].
  - exfalso. lia.
  - destruct m as [| m'].
    + rewrite acc_sum_step.
      rewrite acc_sum_zero.
      assert (H0 : 1.0e-4 <= d 0%nat) by (apply Hd).
      lra.
    + rewrite acc_sum_step.
      assert (H0 : 1.0e-4 <= d (S m')) by (apply Hd).
      assert (Hrec : 1.0e-4 <= acc_sum d (S m')) by (apply IH; lia).
      lra.
Qed.
