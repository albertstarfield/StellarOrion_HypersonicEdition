--  StellarOrion_HypersonicEdition — Optimiser Core (Pure, Provable) — Body
--  Ada 2012 / SPARK 2014
--
--  Author:  Wahyu Suryo Samudro
-- USE "Wahyu Suryo Samudro" NOT "Albert Starfield Wahyu Suryo Samudro"
--
--  AXIOMS
--     A1. This body contains no global state, no I/O and no randomness:
--         every subprogram is a pure function of its arguments, which is
--         what makes the package analysable by GNATprove.
--     A2. The helper Abs_Float replaces Ada.Numerics.Elementary_Functions
--         (not part of SPARK) and is proved non-negative.
--     A3. Every accumulator carries a loop invariant that pins its
--         partial-sum bound, so that the range check of the assignment
--         is discharged from that bound and not from the declared type
--         alone.
--
--  CITATIONS
--     [Gauss1809] Gauss, C. F. "Theoria Motus Corporum Coelestium", 1809.
--     [McKay79]   McKay, B. E., et al. Technometrics 21(2), 239-255, 1979.
--     [Montgomery17] Montgomery, D. C. "Design and Analysis of
--                 Experiments", 9th ed., Wiley, 2017.
--     [Goldberg89]  Goldberg, D. E. "Genetic Algorithms in Search,
--                 Optimization and Machine Learning", Addison-Wesley, 1989.
--     [Eshelman93]  Eshelman, L. J., Schaffer, J. D. Foundations of
--                 Genetic Algorithms 4, 155-199, 1993.
--     [Jones98]  Jones, D. R. J. Global Optimization 13, 455-483, 1998.

package body StellarOrion_Optimizer_Core with SPARK_Mode => On is

   -- ==================================================================
   --  Local helper
   -- ==================================================================
   --  AXIOM A2: absolute value, proved non-negative.
   --  THEORIES
   --    T1. Abs_Float (X) >= 0.
   --    Proof: the negative branch negates a value known to be < 0.
   --  APPLICATIONS
   --    Replaces the non-SPARK Ada.Numerics.Elementary_Functions."abs".
   --  CITATIONS
   --    [Ada 2012 RM 4.5.2] predefined operators on floating point.
   -- ==================================================================
   function Abs_Float (X : Float) return Float
     with Global => null,
          Post => Abs_Float'Result >= 0.0;

   function Abs_Float (X : Float) return Float is
   begin
      if X < 0.0 then
         return -X;
      else
         return X;
      end if;
   end Abs_Float;

   -- ==================================================================
   --  Surrogate model
   -- ==================================================================

   --  AXIOM A4/T2: No_Surrogate predicts exactly zero; Linear_RSM
   --  predicts the affine form.
   --  THEORIES
   --    T1. The result is affine in X.
   --  APPLICATIONS
   --    Supplies the Y_Pred argument of Optimization_Cost.
   --  CITATIONS
   --    [Montgomery17] Ch. 7 — first-order response surface.
   -- ==================================================================
   function Surrogate_Predict
     (M : Surrogate_Model;
      X : Coded_Vector) return Model_Value
   is
   begin
      if M.Kind = No_Surrogate then
         return 0.0;
      else
         return M.B0 + M.B1 * X (1) + M.B2 * X (2) + M.B3 * X (3);
      end if;
   end Surrogate_Predict;

   --  AXIOM A4: closed-form least-squares fit in coded coordinates.
   --  THEORIES
   --    T1. B0 is the grand mean of the responses.
   --    T2. Bk is the contrast sum of column k divided by 8.
   --    Proof: for the canonical 2^3 design the cross-product matrix is
   --    8*I, so the normal equations decouple and each coefficient
   --    depends on one column only.
   --  APPLICATIONS
   --    Fits the SBO surrogate from the eight factorial CCD corners.
   --  CITATIONS
   --    [Gauss1809] least squares; [Montgomery17] Ch. 6 — contrasts.
   -- ==================================================================
   procedure Fit_Linear_Surrogate
     (Coded  : Factorial_Point_Array;
      Values : Factorial_Value_Array;
      M      : out Surrogate_Model)
   is
      Sum_V : Design_Sum := 0.0;
      --  WHY: no initial value on Num -- it is assigned inside the K loop
      --  before every read, so a declaration default would be a dead
      --  initialisation (GNATprove reports it as a warning).
      Num   : Design_Sum;
   begin
      M := (Kind => Linear_RSM, B0 => 0.0, B1 => 0.0, B2 => 0.0, B3 => 0.0);

      --  WHY: the denominator of the closed-form fit is 8 for the
      --  canonical 2^3 design (the cross-product matrix is 8*I), so no
      --  divisor that could be zero and no division overflow exists.
      for I in 1 .. Factorial_Point_Count loop
         --  AXIOM A3: after I terms the sum is bounded by I responses.
         pragma Loop_Invariant
           (Sum_V in -(Float (I) * 1.0E6) .. (Float (I) * 1.0E6));
         Sum_V := Sum_V + Values (I);
      end loop;
      M.B0 := Sum_V / Float (Factorial_Point_Count);

      for K in 1 .. 3 loop
         pragma Loop_Invariant (True);
         Num := 0.0;
         for I in 1 .. Factorial_Point_Count loop
            --  AXIOM A3: after I terms the contrast sum is bounded by
            --  I responses (the coded coordinate is +-1 by AXIOM A1).
            pragma Loop_Invariant
              (Num in -(Float (I) * 1.0E6) .. (Float (I) * 1.0E6));
            Num := Num + Coded (I) (K) * Values (I);
         end loop;

         case K is
            when 1 =>
               M.B1 := Num / Float (Factorial_Point_Count);
            when 2 =>
               M.B2 := Num / Float (Factorial_Point_Count);
            when 3 =>
               M.B3 := Num / Float (Factorial_Point_Count);
         end case;
      end loop;
   end Fit_Linear_Surrogate;

   --  AXIOM A4/T4: weighted squared model error.
   --  THEORIES
   --    T1. The penalty is non-negative (W >= 0 and a square >= 0).
   --    T2. The penalty vanishes when the surrogate matches the truth.
   --  APPLICATIONS
   --    The live model-fidelity term of the SBO objective.
   --  CITATIONS
   --    [Jones98] trust-region model-fidelity penalty.
   -- ==================================================================
   function Surrogate_Disagreement
     (M      : Surrogate_Model;
      X      : Coded_Vector;
      True_Y : Float;
      W      : Float) return Float
   is
      Diff : Float;
   begin
      Diff := Surrogate_Predict (M, X) - True_Y;
      return W * (Diff ** 2);
   end Surrogate_Disagreement;

   -- ==================================================================
   --  Orthogonal residual correction (the calibration fit)
   -- ==================================================================

   --  WHY: the value of one basis monomial at one design point. Every
   --  monomial of the basis {1, x1, x2, x3, x1*x2, x1*x3, x2*x3} is
   --  bounded by 1 in absolute value (the coded coordinates are), and
   --  that bound is what keeps the contrast accumulator inside its
   --  declared range.
   subtype Basis_Monomial_Value is Float range -1.0 .. 1.0;

   --  AXIOM A6/T6: the grand mean of the eight design responses.
   --  THEORIES
   --    T1. The result is (1/8) SUM_i y_i.
   --    T2. |result| <= 1.0E6.
   --    Proof: the partial sums are bounded by the loop invariant and
   --    the divisor is the positive constant 8.
   --  APPLICATIONS
   --    The constant term (b_0) of the orthogonal residual model.
   --  CITATIONS
   --    [Montgomery17] Ch. 6 — the grand mean of a factorial design.
   -- ==================================================================
   function Residual_Grand_Mean (Values : Factorial_Value_Array) return Float
   is
      Sum_V : Design_Sum := 0.0;
   begin
      for I in 1 .. Factorial_Point_Count loop
         --  AXIOM A3: after I-1 terms the sum is bounded by I-1
         --  responses (each in -1.0E6 .. 1.0E6).
         pragma Loop_Invariant
           (Sum_V in -(Float (I - 1) * 1.0E6) .. (Float (I - 1) * 1.0E6));
         Sum_V := Sum_V + Values (I);
      end loop;

      --  WHY: the divisor is the constant 8 — the squared norm of the
      --  canonical 2^3 factorial — so it can never be zero and the
      --  division can never overflow.
      return Sum_V / Float (Factorial_Point_Count);
   end Residual_Grand_Mean;

   --  AXIOM A6/T6: the k-th orthogonal contrast of the design.
   --  THEORIES
   --    T1. The result is (1/8) SUM_i m_k (x_i) y_i, where m_k is the
   --        monomial of basis term K.
   --    T2. |result| <= 1.0E6.
   --    Proof: every monomial is bounded by 1 (AXIOM A7), so the
   --    partial sums are bounded by the loop invariant and the
   --    quotient by the largest response.
   --  APPLICATIONS
   --    The six non-constant coefficients (b_1 .. b_6) of the
   --    orthogonal residual model.
   --  CITATIONS
   --    [Montgomery17] Ch. 6 — contrasts in an orthogonal factorial
   --    design; [Gauss1809] — the normal equations they solve.
   -- ==================================================================
   function Residual_Contrast
     (Coded  : Factorial_Point_Array;
      Values : Factorial_Value_Array;
      K      : Residual_Contrast_Index) return Float
   is
      Num  : Design_Sum := 0.0;
      --  WHY: no initial value on Term -- it is assigned inside the
      --  loop before every read, so a declaration default would be a
      --  dead initialisation (GNATprove reports it as a warning).
      Term : Basis_Monomial_Value;
   begin
      for I in 1 .. Factorial_Point_Count loop
         --  AXIOM A3/A7: after I-1 terms the contrast sum is bounded
         --  by I-1 responses (every basis monomial is bounded by 1).
         pragma Loop_Invariant
           (Num in -(Float (I - 1) * 1.0E6) .. (Float (I - 1) * 1.0E6));

         --  WHY: the monomial of basis term K at design point I. The
         --  main effects take one coded coordinate; the two-factor
         --  terms take the product of the two coordinates they couple.
         Term := (case K is
                    when 2      => Coded (I) (1),
                    when 3      => Coded (I) (2),
                    when 4      => Coded (I) (3),
                    when 5      => Coded (I) (1) * Coded (I) (2),
                    when 6      => Coded (I) (1) * Coded (I) (3),
                    when 7      => Coded (I) (2) * Coded (I) (3));
         Num := Num + Term * Values (I);
      end loop;

      --  WHY: the divisor is the constant 8 — the squared norm of the
      --  canonical 2^3 factorial — so it can never be zero and the
      --  division can never overflow.
      return Num / Float (Factorial_Point_Count);
   end Residual_Contrast;

   --  AXIOM A6/T6: the closed-form fit of the seven orthogonal
   --  coefficients of the residual model.
   --  THEORIES
   --    T1. Coefficients (1) is the grand mean of Values.
   --    T2. Coefficients (k) is the k-th orthogonal contrast of the
   --        design, for k = 2 .. 7.
   --    Proof: the fit evaluates the closed forms of THEORY T6
   --    directly; the loop invariant carries the closed form of every
   --    coefficient already written.
   --  APPLICATIONS
   --    The ADDITIVE calibration residual of the screening model
   --    against the DSMC response (CALIBRATION_DESIGN.md Sec. 2.6).
   --  CITATIONS
   --    [Montgomery17] Ch. 6 — contrasts and the orthogonality of a
   --    factorial design; [Kennedy00] — model discrepancy.
   -- ==================================================================
   procedure Fit_Orthogonal_Factorial
     (Coded        : Factorial_Point_Array;
      Values       : Factorial_Value_Array;
      Coefficients : out Residual_Coefficient_Array)
   is
   begin
      --  WHY: an OUT array parameter must be fully defined on return;
      --  the aggregate assignment defines every element before any
      --  read.
      Coefficients := (others => 0.0);

      --  THEORY T1: the constant basis term is the grand mean.
      Coefficients (1) := Residual_Grand_Mean (Values);

      for K in 2 .. Residual_Basis_Index'Last loop
         --  THEORY T2: every coefficient already written is the
         --  closed-form contrast of its column.
         pragma Loop_Invariant
           (Coefficients (1) = Residual_Grand_Mean (Values)
            and (for all J in 2 .. Residual_Basis_Index'Last =>
                   (if J < K then
                      Coefficients (J) = Residual_Contrast (Coded, Values, J))));
         Coefficients (K) := Residual_Contrast (Coded, Values, K);
      end loop;
   end Fit_Orthogonal_Factorial;

   --  AXIOM A6/T7: the 7-term orthogonal model at a coded point.
   --  THEORIES
   --    T1. The result is
   --          b_0 + b_1 x1 + b_2 x2 + b_3 x3 + b_4 x1 x2 + b_5 x1 x3
   --            + b_6 x2 x3.
   --    T2. |result| <= 7.0E9.
   --    Proof: every coefficient is bounded by 1.0E9 and every monomial
   --    of the coded point is bounded by 1 (AXIOM A7), so each of the
   --    seven terms is bounded by 1.0E9.
   --  APPLICATIONS
   --    The additive calibration correction the screening model adds to
   --    the analytic drag and heat laws.
   --  CITATIONS
   --    [Montgomery17] Ch. 7 — response surface with two-factor
   --    interactions.
   -- ==================================================================
   function Evaluate_Residual_Model
     (Coefficients : Residual_Coefficient_Array;
      X            : Coded_Vector) return Float
   is
      Total : Float;
   begin
      Total := Coefficients (1)
        + Coefficients (2) * X (1)
        + Coefficients (3) * X (2)
        + Coefficients (4) * X (3)
        + Coefficients (5) * X (1) * X (2)
        + Coefficients (6) * X (1) * X (3)
        + Coefficients (7) * X (2) * X (3);
      return Total;
   end Evaluate_Residual_Model;

   -- ==================================================================
   --  Objective function
   -- ==================================================================
   --  AXIOM A1/T1: weighted sum of squares, weights non-negative.
   --  THEORIES
   --    T1. The result is non-negative.
   --    Proof: each term is a non-negative weight times a square.
   --  APPLICATIONS
   --    The single objective shared by all optimiser entry points.
   --  CITATIONS
   --    [Gauss1809] weighted least squares; StellarOrion DERIVATION.MD
   --    Sec 4 for the project-specific normalisation by 10.
   -- ==================================================================
   function Optimization_Cost
     (Beta_Calc   : Float;
      Beta_Target : Float;
      Y_Pred      : Float;
      Y_Target    : Float;
      W_Beta      : Float;
      W_Target    : Float) return Float
   is
      Delta_Beta : Float;
      Delta_Y    : Float;
   begin
      Delta_Beta := (Beta_Calc - Beta_Target) / 10.0;
      Delta_Y    := Y_Pred - Y_Target;

      return W_Beta * (Delta_Beta ** 2)
           + W_Target * (Delta_Y ** 2);
   end Optimization_Cost;

   -- ==================================================================
   --  GA bookkeeping
   -- ==================================================================

   --  AXIOM A5: ascending sort by cost, ties broken by the original
   --  index so the outcome is deterministic.
   --  THEORIES
   --    T1. Idx is a permutation of 1 .. N with non-decreasing costs.
   --    T2. Idx (1) indexes a minimum-cost individual.
   --  APPLICATIONS
   --    Selection order for tournament selection and elitism.
   --  CITATIONS
   --    [Goldberg89] Ch. 3 — selection on a ranked population.
   -- ==================================================================
   procedure Sort_By_Cost
     (Idx   : out Index_Array;
      Costs : Cost_Array;
      N     : Positive)
   is
      Best : Population_Index;
      Tmp  : Population_Index;
   begin
      --  WHY: an OUT array parameter must be fully defined on return.
      --  The identity permutation is the starting point of the
      --  selection sort. Slots outside 1 .. N keep the value 1, which
      --  is a valid population index (AXIOM A2 of the spec).
      Idx := (others => 1);

      for I in 1 .. N loop
         pragma Loop_Invariant (for all J in 1 .. N => Idx (J) <= N);
         Idx (I) := I;
      end loop;

      for I in 1 .. N - 1 loop
         pragma Loop_Invariant (for all J in 1 .. N => Idx (J) <= N);
         Best := I;
         for J in I + 1 .. N loop
            pragma Loop_Invariant (for all K in 1 .. N => Idx (K) <= N);
            pragma Loop_Invariant (Best in I .. N);
            if Costs (Idx (J)) < Costs (Idx (Best))
              or else
                (Costs (Idx (J)) = Costs (Idx (Best))
                 and then Idx (J) < Idx (Best))
            then
               Best := J;
            end if;
         end loop;

         --  WHY: the swap is unconditional. A conditional swap would
         --  need the prover to reason about two branches with the same
         --  array-update reasoning; the unconditional swap keeps the
         --  "every written value is <= N" argument uniform.
         Tmp := Idx (I);
         Idx (I) := Idx (Best);
         Idx (Best) := Tmp;
      end loop;
   end Sort_By_Cost;

   --  AXIOM A5: index of the cheapest individual of the active
   --  population.
   --  THEORIES
   --    T1. Costs (Best) <= Costs (K) for every K in 1 .. N.
   --    Proof: the scan keeps the cheapest individual seen so far.
   --  APPLICATIONS
   --    Best-so-far tracking across generations; the caller copies the
   --    gene of the returned individual.
   --  CITATIONS
   --    [Goldberg89] Ch. 3.
   -- ==================================================================
   function Best_Index
     (Costs : Cost_Array;
      N     : Positive) return Population_Index
   is
      Best : Population_Index := 1;
   begin
      for I in 2 .. N loop
         --  AXIOM A3: the cheapest individual seen so far.
         pragma Loop_Invariant
           (for all K in 1 .. I - 1 => Costs (Best) <= Costs (K));
         pragma Loop_Invariant (Best in 1 .. N);
         if Costs (I) < Costs (Best) then
            Best := I;
         end if;
      end loop;
      return Best;
   end Best_Index;

   --  AXIOM A5: stagnation counting and convergence detection.
   --  THEORIES
   --    T1. A required count of zero disables convergence detection.
   --    T2. The counter saturates rather than overflowing.
   --  APPLICATIONS
   --    The GA convergence test.
   --  CITATIONS
   --    [Goldberg89] Ch. 3 — convergence by stagnation.
   -- ==================================================================
   procedure Update_Stagnation
     (Best_Cost  : Float;
      Prev_Best  : Float;
      Tol        : Float;
      Stag_Count : in out Stagnation_Count;
      Converged  : out Boolean;
      Required   : Natural)
   is
   begin
      if Abs_Float (Best_Cost - Prev_Best) < Tol then
         --  WHY: saturate instead of overflowing. The counter is a
         --  Natural with a finite domain; incrementing it past the
         --  domain would raise Constraint_Error at run time.
         if Stag_Count < Stagnation_Count'Last then
            Stag_Count := Stag_Count + 1;
         end if;
      else
         Stag_Count := 0;
      end if;

      Converged := (Required > 0) and then (Stag_Count >= Required);
   end Update_Stagnation;

end StellarOrion_Optimizer_Core;
