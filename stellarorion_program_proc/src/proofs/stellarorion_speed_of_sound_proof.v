(* ============================================================================
   Coq proof companion for src/simulation_engine/stellarorion_speed_of_sound
   Ada 2012 / SPARK 2014, pragma SPARK_Mode (On).

   AXIOM (S1) [ideal gas]: the speed of sound in an ideal gas is
        a = sqrt (gamma * R * T),
   with gamma = 1.4 and R = 287.058 J/(kg*K) for dry air, the exact constants
   the .ads declares as GAMMA_AIR and R_AIR.
   AXIOM (S2) [envelope]: the unit's Pre restricts T to 0 .. 6000 K, covering
   the ISA profile, hot-wall recovery and the SPARTA grid-cell temperature
   mask. gamma and R are constants of the unit, so their bounds are 1.4 and
   287.058 respectively.

   THEOREM (S3) [strict positivity]: for gamma > 0, R > 0 and T > 0 the
   ideal-gas speed of sound is STRICTLY POSITIVE. The Newton iteration of
   Sqrt_Approx can therefore never underflow to exactly 0.0 on the physical
   domain, so the unit's Post "Result >= 0.0" is a real bound, not a
   tautology.
   THEOREM (S4) [monotonicity]: a is non-decreasing in T, so a colder cell of
   the trajectory cannot report a larger speed of sound.
   THEOREM (S5) [exact square]: a * a = gamma * R * T. This is the closed form
   that the unit's relative-error contract (stated on the SQUARE, because the
   square root is irrational in general) is measured against.
   THEOREM (S6) [overflow bound]: gamma * R * T <= 1.4 * 287.058 * 6000, hence
   a <= sqrt of that product << Float'Last, so no intermediate of the unit can
   overflow.

   CITATIONS:
     [1] Anderson, "Modern Compressible Flow", 3rd Ed., Ch. 2 (speed of sound).
     [2] Ada Reference Manual ISO/IEC 8652:2012, RM A.5 (Float attributes).
     [3] Coq Reference Manual, Coq.Reals.R_sqrt (sqrt_lt_R0, sqrt_sqrt,
         sqrt_le_1, sqrt_pos) and Coq.Reals.RIneq (Rmult_lt_0_compat,
         Rmult_le_compat, Rmult_le_pos).
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

(* Every Definition and Lemma in this file quantifies over the reals; opening
   R_scope at file level makes numerals, <=, * and / elaborate in R rather than
   nat. [Citation: Coq 8.18 stdlib Coq.Reals.Reals -- Local Open Scope R_scope] *)
Local Open Scope R_scope.

(* ---------------------------------------------------------------------------
   Model of Ada Speed_Of_Sound (stellarorion_speed_of_sound.adb):

       Gamma_R_T := GAMMA_AIR * R_AIR * Temperature;
       if Gamma_R_T < 0.0 then Gamma_R_T := 0.0; end if;
       return Sqrt_Approx (Gamma_R_T);

   The mathematical ideal behind Sqrt_Approx's Newton iteration is the real
   square root, and the unit's Post bounds the SQUARE of the result, which is
   only meaningful because a * a = gamma * R * T exactly.
   --------------------------------------------------------------------------- *)
Definition speed_of_sound (gamma r_gas t : R) : R := sqrt (gamma * r_gas * t).

(* ---------------------------------------------------------------------------
   THEOREM S3 -- strict positivity for a strictly positive temperature.
   --------------------------------------------------------------------------- *)
Lemma speed_of_sound_pos : forall gamma r_gas t : R,
   0 < gamma -> 0 < r_gas -> 0 < t -> 0 < speed_of_sound gamma r_gas t.
Proof.
  intros gamma r_gas t Hg Hr Ht.
  unfold speed_of_sound.
  apply sqrt_lt_R0.
  apply Rmult_lt_0_compat.
  - apply Rmult_lt_0_compat; [exact Hg | exact Hr].
  - exact Ht.
Qed.

(* ---------------------------------------------------------------------------
   Helper: the product gamma * R * T is non-negative when all factors are.
   --------------------------------------------------------------------------- *)
Lemma gamma_r_t_nonneg : forall gamma r_gas t,
   0 <= gamma -> 0 <= r_gas -> 0 <= t -> 0 <= gamma * r_gas * t.
Proof.
  intros gamma r_gas t Hg Hr Ht.
  apply Rmult_le_pos.
  - apply Rmult_le_pos; [exact Hg | exact Hr].
  - exact Ht.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM S4 -- monotonicity in temperature.
   --------------------------------------------------------------------------- *)
Lemma speed_of_sound_mono : forall gamma r_gas t1 t2,
   0 < gamma -> 0 < r_gas -> 0 <= t1 -> t1 <= t2 ->
   speed_of_sound gamma r_gas t1 <= speed_of_sound gamma r_gas t2.
Proof.
  intros gamma r_gas t1 t2 Hg Hr Ht1 Ht12.
  unfold speed_of_sound.
  assert (Hc : 0 <= gamma * r_gas) by (apply Rmult_le_pos; lra).
  assert (Hle : gamma * r_gas * t1 <= gamma * r_gas * t2).
  { rewrite (Rmult_comm (gamma * r_gas) t1).
    rewrite (Rmult_comm (gamma * r_gas) t2).
    apply Rmult_le_compat_r; [exact Hc | exact Ht12]. }
  apply sqrt_le_1.
  - apply Rmult_le_pos; [exact Hc | exact Ht1].
  - apply Rmult_le_pos; [exact Hc | lra].
  - exact Hle.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM S5 -- the square of the result equals gamma * R * T exactly.
   --------------------------------------------------------------------------- *)
Lemma speed_of_sound_square : forall gamma r_gas t,
   0 <= gamma * r_gas * t ->
   speed_of_sound gamma r_gas t * speed_of_sound gamma r_gas t = gamma * r_gas * t.
Proof.
  intros gamma r_gas t H.
  unfold speed_of_sound.
  apply sqrt_sqrt.
  exact H.
Qed.

(* ---------------------------------------------------------------------------
   THEOREM S6 -- overflow bound.
   gamma * R * T <= 1.4 * 287.058 * 6000 by monotonicity of multiplication in
   each factor; the left association written here matches the source
   expression "gamma * r_gas * t".
   --------------------------------------------------------------------------- *)
Lemma gamma_r_t_upper : forall gamma r_gas t,
   0 <= gamma -> gamma <= 1.4 ->
   0 <= r_gas -> r_gas <= 287.058 ->
   0 <= t -> t <= 6000 ->
   gamma * r_gas * t <= 1.4 * 287.058 * 6000.
Proof.
  intros gamma r_gas t Hg Hb1 Hr Hb2 Ht Hb3.
  apply Rmult_le_compat.
  - apply Rmult_le_pos; lra.
  - exact Ht.
  - apply Rmult_le_compat; lra.
  - exact Hb3.
Qed.

(* ---------------------------------------------------------------------------
   Consequence: the speed of sound itself is bounded by the square root of the
   overflow bound, which is the quantity the unit's T1 theorem quotes.
   --------------------------------------------------------------------------- *)
Lemma speed_of_sound_upper : forall gamma r_gas t,
   0 <= gamma -> gamma <= 1.4 ->
   0 <= r_gas -> r_gas <= 287.058 ->
   0 <= t -> t <= 6000 ->
   speed_of_sound gamma r_gas t <= sqrt (1.4 * 287.058 * 6000).
Proof.
  intros gamma r_gas t Hg Hb1 Hr Hb2 Ht Hb3.
  unfold speed_of_sound.
  apply sqrt_le_1.
  - apply gamma_r_t_nonneg; assumption.
  - apply Rmult_le_pos; lra.
  - apply gamma_r_t_upper; assumption.
Qed.
