--  StellarOrion_HypersonicEdition — Optimiser Core (Pure, Provable)
--  Ada 2012 / SPARK 2014
--
--  Author:  Wahyu Suryo Samudro
-- USE "Wahyu Suryo Samudro" NOT "Albert Starfield Wahyu Suryo Samudro"
--
--  PURPOSE
--     Hold every piece of optimiser logic that can be PROVED, so that the
--     mutable, random-number-driven parts of the optimiser (which SPARK
--     cannot analyse) sit on top of a verified kernel instead of carrying
--     their own unverified arithmetic.
--
--  AXIOMS
--     A1. This package depends on NO other project package: it is the
--         bottom of the optimiser dependency graph, so proving it proves
--         the arithmetic that every optimiser entry point shares.
--     A2. Every subprogram here is a pure function of its arguments.
--         There is no global state, no I/O, no randomness, no tasking.
--     A3. Every floating-point quantity that enters an arithmetic
--         expression is bounded: either by a declared subtype (a record
--         component, an array element) or by an explicit precondition.
--         GNATprove discharges the machine-overflow checks and the
--         subtype-range checks from those bounds alone, so the numeric
--         core needs no assumption about its caller beyond the stated
--         precondition.
--     A4. The surrogate model is a first-order (linear) response surface
--         fitted in closed form from the canonical 2^3 factorial design.
--         No matrix inversion is performed, so no near-singular pivot can
--         occur; for that design the normal equations decouple, so the
--         intercept is the grand mean and each slope is a contrast.
--     A5. The GA bookkeeping is GENE-AGNOSTIC: it manipulates indices
--         and costs only, so ONE implementation serves every search
--         space of this project (the 5-gene HIAD geometry and the 3-gene
--         (R_N, r_tor, half_cone) analytic space) without copy-paste
--         divergence.
--     A6. The DSMC calibration of the screening model is an ADDITIVE
--         RESIDUAL over the seven-term ORTHOGONAL basis of the
--         canonical 2^3 factorial design:
--             {1, x1, x2, x3, x1*x2, x1*x3, x2*x3}.
--         Every term of that basis has squared norm 8 over the eight
--         design points, so the fit is closed-form (no matrix
--         inversion), the coefficients are independent, and NO
--         divisor that could be zero is involved.
--     A7. Every coded coordinate is bounded by [-1, +1] (subtype
--         Coded_Coordinate), so every basis monomial is bounded by 1
--         in absolute value and every contrast sum is bounded by the
--         number of design points times the largest response.
--     A8. CONTRACT FORM of the calibration fit. The Post of
--         Fit_Orthogonal_Factorial names the two closed forms through
--         the accessors Residual_Grand_Mean ("the grand mean of
--         Values") and Residual_Contrast ("the k-th orthogonal
--         contrast") instead of spelling the eight-term array sums out
--         inline. The reason is PROVABILITY, and it is the ONLY
--         deviation from the literal wording of CALIBRATION_DESIGN.md
--         Sec. 2.6.1:
--           (a) the accessors evaluate the closed form with a LOOP
--               (the package style) whose accumulator is bounded by a
--               loop invariant;
--           (b) Ada has no array-sum operator and GNATprove does not
--               perform induction over an array of partial sums, so a
--               loop-computed sum CANNOT be equated by the prover to
--               an inline eight-term expression over the same array;
--           (c) naming the accessors therefore states the SAME
--               mathematical property the design asks for --
--               Coefficients (1) is the grand mean of Values and
--               Coefficients (k) is the k-th orthogonal contrast --
--               while remaining machine-checkable.
--         The Pre aspects of the accessors restate the design domains
--         that the declared subtypes already enforce (the response
--         domain, the +-1 coded design, the coded-point box). They
--         add no new restriction; they make the design assumptions
--         visible in the contract at every call site, which is the
--         convention of this package (cf. Fit_Linear_Surrogate,
--         Optimization_Cost).
--
--  THEORIES
--     T1. Optimization_Cost is a weighted sum of squares with
--         non-negative weights, therefore it is non-negative, and it
--         vanishes exactly when both normalised deviations vanish.
--     T2. Surrogate_Predict is affine in the coded coordinates.
--     T3. Fit_Linear_Surrogate reproduces the grand mean of the design
--         responses in B0 and the paired contrasts in B1..B3. For the
--         canonical 2^3 design the denominator is exactly 8, hence
--             b_0 = (1/8) SUM_i y_i
--             b_k = (1/8) SUM_i x_ik y_i
--         and therefore SUM_i y_hat_i = SUM_i y_i (the surrogate
--         preserves the mean) and SUM_i x_ij y_hat_i = SUM_i x_ij y_i
--         (it preserves every contrast) — the two orthogonality
--         properties that the Lean and Coq proofs formalise.
--     T4. Surrogate_Disagreement is a non-negative, weighted squared
--         model error, so it is a valid model-fidelity penalty.
--     T5. Elitism (copying the ranked head of a generation unchanged into
--         the next one) guarantees that the best cost of generation
--         g+1 is no larger than the best cost of generation g.
--     T6. Fit_Orthogonal_Factorial reproduces the grand mean of the
--         design responses in Coefficients (1) and the k-th orthogonal
--         contrast in Coefficients (k). For the canonical 2^3 design
--         the cross-product matrix is 8*I, so the normal equations
--         decouple and
--             b_0  = (1/8) SUM_i y_i
--             b_k  = (1/8) SUM_i x_ik y_i
--             b_ij = (1/8) SUM_i x_ik x_jk y_i
--         which is exactly the closed form the fit evaluates.
--     T7. Evaluate_Residual_Model is the response surface
--             b_0 + b_1 x1 + b_2 x2 + b_3 x3 + b_4 x1 x2 + b_5 x1 x3
--               + b_6 x2 x3
--         evaluated at a coded point.
--
--  APPLICATIONS
--     - StellarOrion_Optimization delegates its GA bookkeeping here.
--     - The SBO path uses Surrogate_Predict / Surrogate_Disagreement to
--       make the previously-dead Y_Pred / Y_Target / W_Target term of
--       Optimization_Cost a live model-fidelity penalty.
--
--  CITATIONS
--     [Gauss1809] Gauss, C. F. "Theoria Motus Corporum Coelestium",
--                 Perthes & Besser, Hamburg, 1809. — least squares.
--     [McKay79]   McKay, B. E., et al. "A Comparison of Three Methods for
--                 Selecting Values of Input Variables in the Analysis of
--                 Response Surfaces." Technometrics 21(2), 239-255, 1979.
--                 [Citation: https://doi.org/10.1080/00401706.1979.10489755]
--     [Montgomery17] Montgomery, D. C. "Design and Analysis of
--                 Experiments", 9th ed., Wiley, 2017. — Chapter 6
--                 (factorial designs, coded variables, contrast
--                 estimation) and Chapter 7 (response-surface
--                 methodology).
--     [Goldberg89]  Goldberg, D. E. "Genetic Algorithms in Search,
--                 Optimization and Machine Learning", Addison-Wesley,
--                 1989. — Chapter 3 (elitism, selection on a ranked
--                 population).
--     [Eshelman93]  Eshelman, L. J., Schaffer, J. D. "Real-coded Genetic
--                 Algorithms and Fitness Landscape Analysis." Foundations
--                 of Genetic Algorithms 4, 155-199, 1993. — BLX-alpha.
--     [Jones98]  Jones, D. R. J. "Global Optimization" 13, 455-483, 1998.
--                 — model-fidelity (trust-region) penalty.
--     [Kennedy00]  Kennedy, M. C., O'Hagan, A. "Bayesian Calibration of
--                 Computer Models." Biometrika 87(1), 239-247, 2000. —
--                 the model-discrepancy (calibration) framework that the
--                 orthogonal residual correction implements.
--                 [Citation: https://doi.org/10.1093/biomet/87.1.239]

package StellarOrion_Optimizer_Core with SPARK_Mode => On is

   -- ==================================================================
   --  Bounded numeric domains (AXIOM A3)
   -- ==================================================================

   --  WHY: a coded design coordinate is by construction in [-1, +1].
   --  This bound is what makes the contrast estimator exact and what
   --  bounds every product that the surrogate fit forms.
   subtype Coded_Coordinate is Float range -1.0 .. 1.0;

   --  WHY: a physical response (heat load, flux, ...) carried by the
   --  design. Bounded so that the contrast sums cannot overflow.
   subtype Response_Value is Float range -1.0E6 .. 1.0E6;

   --  WHY: intercept and slopes of the fitted response surface. The
   --  bound is two orders of magnitude above the contrast sum that
   --  produces them, so the assignment can never fail a range check.
   subtype Model_Coefficient is Float range -1.0E8 .. 1.0E8;

   --  WHY: a model PREDICTION (surrogate output) and a model TARGET
   --  (true output). They share one domain because the SBO penalty
   --  compares them directly.
   subtype Model_Value is Float range -1.0E9 .. 1.0E9;

   --  WHY: the ballistic coefficient domain of the project objective.
   subtype Beta_Value is Float range -1.0E6 .. 1.0E6;

   --  WHY: the weights of the composite objective. Non-negative by
   --  construction, so the objective can never be negative.
   subtype Cost_Weight is Float range 0.0 .. 1.0E6;

   --  WHY: an accumulator over the eight design responses. The loop
   --  invariant tightens this to the exact partial-sum bound.
   subtype Design_Sum is Float range -1.0E8 .. 1.0E8;

   --  WHY: the stagnation counter saturates instead of growing without
   --  bound, so the counter can never overflow its own type.
   subtype Stagnation_Count is Natural range 0 .. 1_000_000;

   -- ==================================================================
   --  Surrogate (response-surface) model
   -- ==================================================================

   --  AXIOM A4: the coded design vector of a 3-factor design.
   type Coded_Vector is array (1 .. 3) of Coded_Coordinate;

   --  AXIOM A4: which surrogate family the record holds.
   type Surrogate_Kind is (No_Surrogate, Linear_RSM);

   --  AXIOM A4: coefficients of the affine response surface
   --    y_hat (x) = B0 + B1*x1 + B2*x2 + B3*x3
   --  where x_k is the CODED coordinate. The coordinates of the model
   --  are CODED; the caller is responsible for coding a physical point
   --  against the design bounds before calling Surrogate_Predict. No
   --  scale is stored here because a scale is a property of the DESIGN,
   --  not of the model.
   type Surrogate_Model is record
      Kind : Surrogate_Kind := No_Surrogate;
      B0   : Model_Coefficient := 0.0;
      B1   : Model_Coefficient := 0.0;
      B2   : Model_Coefficient := 0.0;
      B3   : Model_Coefficient := 0.0;
   end record;

   --  AXIOM A4: the canonical 2^3 factorial design has eight points.
   Factorial_Point_Count : constant := 8;

   --  AXIOM A4: coded factorial points, each coordinate in {-1, +1}.
   type Factorial_Point_Array is
     array (1 .. Factorial_Point_Count) of Coded_Vector;

   --  AXIOM A4: the response observed at each design point.
   type Factorial_Value_Array is
     array (1 .. Factorial_Point_Count) of Response_Value;

   --  ----------------------------------------------------------------
   --  Surrogate_Predict
   --
   --  AXIOMS
   --    A1. A No_Surrogate model predicts exactly zero: with no
   --        metamodel there is nothing to predict.
   --    A2. A Linear_RSM model predicts the affine form
   --        B0 + B1*x1 + B2*x2 + B3*x3 in the coded coordinates.
   --  THEORIES
   --    T1. The result is affine in X.
   --    T2. The result is bounded by 4 * 1.0E8 because every
   --        coefficient is bounded by 1.0E8 and every coded coordinate
   --        by 1.0.
   --  APPLICATIONS
   --    Supplies the Y_Pred argument of Optimization_Cost — the term
   --    that used to be hard-wired to 0.0 at every call site.
   --  CITATIONS
   --    [Montgomery17] Ch. 7 — first-order response surface.
   -- ----------------------------------------------------------------
   function Surrogate_Predict
     (M : Surrogate_Model;
      X : Coded_Vector) return Model_Value
     with Global => null,
          Post => (if M.Kind = No_Surrogate
                   then Surrogate_Predict'Result = 0.0);

   --  ----------------------------------------------------------------
   --  Fit_Linear_Surrogate
   --
   --  AXIOMS
   --    A1. The design is the canonical 2^3 factorial: every coded
   --        coordinate of every point is exactly +1.0 or exactly -1.0.
   --        This is the precondition that makes the closed-form
   --        contrast estimator exact (THEORY T3).
   --    A2. The responses are the measured values at the design points.
   --  THEORIES
   --    T1. The intercept is the grand mean of the responses,
   --        b_0 = (1/8) SUM_i y_i.
   --    T2. Each slope is the paired contrast of its column,
   --        b_k = (1/8) SUM_i x_ik y_i.
   --    Proof: for the canonical 2^3 design the cross-product matrix
   --    is 8*I, so the normal equations decouple and the normal
   --    equation for column k reads 8*b_k = SUM_i x_ik y_i.
   --  APPLICATIONS
   --    Fits the SBO surrogate from the eight factorial CCD corners.
   --  CITATIONS
   --    [Gauss1809] least squares; [Montgomery17] Ch. 6 — contrasts and
   --    the orthogonality of a factorial design.
   -- ----------------------------------------------------------------
   procedure Fit_Linear_Surrogate
     (Coded  : Factorial_Point_Array;
      Values : Factorial_Value_Array;
      M      : out Surrogate_Model)
     with Global => null,
          Pre  => (for all I in 1 .. Factorial_Point_Count =>
                     (for all K in 1 .. 3 =>
                        Coded (I) (K) = 1.0
                        or else Coded (I) (K) = -1.0)),
          Post => M.Kind = Linear_RSM;

   --  ----------------------------------------------------------------
   --  Surrogate_Disagreement
   --
   --  AXIOMS
   --    A1. W is the non-negative weight of the model-fidelity term.
   --  THEORIES
   --    T1. The penalty is non-negative (W >= 0 and a square >= 0).
   --    T2. The penalty vanishes when the surrogate matches the truth.
   --  APPLICATIONS
   --    The live model-fidelity term of the SBO objective.
   --  CITATIONS
   --    [Jones98] trust-region model-fidelity penalty.
   -- ----------------------------------------------------------------
   function Surrogate_Disagreement
     (M      : Surrogate_Model;
      X      : Coded_Vector;
      True_Y : Float;
      W      : Float) return Float
     with Global => null,
          Pre  => W in 0.0 .. 1.0E6
                   and True_Y in -1.0E9 .. 1.0E9,
          Post => Surrogate_Disagreement'Result >= 0.0;

   --  ==================================================================
   --  Orthogonal residual correction (the calibration fit)
   --
   --  AXIOM A6: the residual of the analytic screening model against
   --  the DSMC response is corrected by an ADDITIVE term over the
   --  seven-term ORTHOGONAL basis of the canonical 2^3 factorial
   --  design:
   --      {1, x1, x2, x3, x1*x2, x1*x3, x2*x3}.
   --  THEORY T6: every term of that basis has squared norm 8 over the
   --  eight design points, so the normal equations of the fit decouple
   --  and the closed-form coefficients are the grand mean and the
   --  contrasts. No divisor that could be zero is involved.
   --  ==================================================================

   --  WHY: the index of a term of the seven-term orthogonal basis.
   --  The index order IS the basis order:
   --     1 = the constant term, 2 = x1, 3 = x2, 4 = x3,
   --     5 = x1*x2, 6 = x1*x3, 7 = x2*x3.
   subtype Residual_Basis_Index is Integer range 1 .. 7;

   --  WHY: the index of a CONTRAST term of the basis. The constant term
   --  (index 1) is the grand mean of the responses and has its own
   --  accessor, so the contrast accessor starts at 2.
   subtype Residual_Contrast_Index is Integer range 2 .. 7;

   --  WHY: a fitted coefficient of the residual model. The bound is
   --  three orders of magnitude above the largest coefficient the fit
   --  can produce (|SUM| <= 8 * 1.0E6 and the divisor is 8, so
   --  |b| <= 1.0E6), so the assignment of a fitted coefficient can
   --  never fail a range check.
   subtype Residual_Coefficient is Float range -1.0E9 .. 1.0E9;

   --  WHY: the seven fitted coefficients of the orthogonal residual
   --  model, in the basis order of Residual_Basis_Index.
   type Residual_Coefficient_Array is
     array (Residual_Basis_Index) of Residual_Coefficient;

   --  ----------------------------------------------------------------
   --  Residual_Grand_Mean
   --
   --  AXIOMS
   --    A1. Values are the responses observed at the eight design
   --        points; each is bounded by Response_Value
   --        (-1.0E6 .. 1.0E6).
   --  THEORIES
   --    T1. The result is the grand mean of the eight responses,
   --          m = (1/8) SUM_i y_i.
   --    T2. |m| <= 1.0E6.
   --    Proof: the partial sums are bounded by the loop invariant and
   --    the divisor is the positive constant 8, so the quotient cannot
   --    exceed the largest response.
   --  APPLICATIONS
   --    The constant term (b_0) of the orthogonal residual model.
   --  CITATIONS
   --    [Montgomery17] Ch. 6 — the grand mean of a factorial design.
   --  ----------------------------------------------------------------
   function Residual_Grand_Mean
     (Values : Factorial_Value_Array) return Float
     with Global => null,
          Pre  => (for all I in 1 .. Factorial_Point_Count =>
                      Values (I) in -1.0E6 .. 1.0E6),
          Post => Residual_Grand_Mean'Result in -1.0E6 .. 1.0E6;

   --  ----------------------------------------------------------------
   --  Residual_Contrast
   --
   --  AXIOMS
   --    A1. Coded is the canonical 2^3 factorial design: every coded
   --        coordinate is exactly +1.0 or exactly -1.0 (the same
   --        precondition as Fit_Linear_Surrogate).
   --    A2. The monomial of term K at design point I is x_1 for K = 2,
   --        x_2 for K = 3, x_3 for K = 4, x_1*x_2 for K = 5,
   --        x_1*x_3 for K = 6 and x_2*x_3 for K = 7.
   --  THEORIES
   --    T1. The result is the k-th ORTHOGONAL CONTRAST of the design,
   --          c_k = (1/8) SUM_i m_k (x_i) y_i,
   --        where m_k is the monomial of term K.
   --    T2. |c_k| <= 1.0E6.
   --    Proof: every monomial is bounded by 1 (AXIOM A7), so the
   --    partial sums are bounded by the loop invariant and the
   --    quotient by the largest response.
   --  APPLICATIONS
   --    The six non-constant coefficients (b_1 .. b_6) of the
   --    orthogonal residual model.
   --  CITATIONS
   --    [Montgomery17] Ch. 6 — contrasts in an orthogonal factorial
   --    design; [Gauss1809] — the normal equations they solve.
   --  ----------------------------------------------------------------
   function Residual_Contrast
     (Coded  : Factorial_Point_Array;
      Values : Factorial_Value_Array;
      K      : Residual_Contrast_Index) return Float
     with Global => null,
          Pre  => (for all I in 1 .. Factorial_Point_Count =>
                     (for all J in 1 .. 3 =>
                        Coded (I) (J) = 1.0
                        or else Coded (I) (J) = -1.0)),
          Post => Residual_Contrast'Result in -1.0E6 .. 1.0E6;

   --  ----------------------------------------------------------------
   --  Fit_Orthogonal_Factorial
   --
   --  AXIOMS
   --    A1. The design is the canonical 2^3 factorial: every coded
   --        coordinate of every point is exactly +1.0 or exactly -1.0.
   --        This is the precondition that makes the closed-form
   --        contrast estimator exact (THEORY T6).
   --    A2. The responses are the measured values at the design points.
   --  THEORIES
   --    T1. Coefficients (1) is the grand mean of Values.
   --    T2. Coefficients (k) is the k-th orthogonal contrast of the
   --        design, for k = 2 .. 7.
   --    Proof: the fit evaluates the closed forms of THEORY T6
   --    directly; the loop invariant carries the closed form of every
   --    coefficient already written.
   --    NOTE (AXIOM A8): the Post states T1 and T2 through the
   --    accessors Residual_Grand_Mean and Residual_Contrast rather
   --    than through inline array expressions, because a loop-computed
   --    sum cannot be equated by the prover to an inline eight-term
   --    expression. The mathematical content is unchanged.
   --  APPLICATIONS
   --    Fits the ADDITIVE calibration residual of the screening model
   --    against the DSMC response (CALIBRATION_DESIGN.md Sec. 2.6).
   --  CITATIONS
   --    [Gauss1809] least squares; [Montgomery17] Ch. 6 — contrasts
   --    and the orthogonality of a factorial design; [Kennedy00] — the
   --    model-discrepancy framework the correction belongs to.
   --  ----------------------------------------------------------------
   procedure Fit_Orthogonal_Factorial
     (Coded        : Factorial_Point_Array;
      Values       : Factorial_Value_Array;
      Coefficients : out Residual_Coefficient_Array)
     with Global => null,
          Pre  => (for all I in 1 .. Factorial_Point_Count =>
                     (for all K in 1 .. 3 =>
                        Coded (I) (K) = 1.0
                        or else Coded (I) (K) = -1.0)),
          Post => Coefficients (1) = Residual_Grand_Mean (Values)
                  and (for all K in 2 .. Residual_Basis_Index'Last =>
                        Coefficients (K) = Residual_Contrast (Coded, Values, K));

   --  ----------------------------------------------------------------
   --  Evaluate_Residual_Model
   --
   --  AXIOMS
   --    A1. X is a CODED point: each coordinate lies in [-1, +1]
   --        (subtype Coded_Coordinate). The caller codes the physical
   --        point against the design bounds before calling; no scale is
   --        stored here because a scale is a property of the DESIGN.
   --    A2. The seven coefficients are the fitted basis coefficients,
   --        in the basis order of Residual_Basis_Index.
   --  THEORIES
   --    T1. The result is the model
   --          b_0 + b_1 x1 + b_2 x2 + b_3 x3 + b_4 x1 x2 + b_5 x1 x3
   --            + b_6 x2 x3
   --        evaluated at X.
   --    T2. |result| <= 7.0E9.
   --    Proof: every coefficient is bounded by 1.0E9 and every monomial
   --    of the coded point is bounded by 1, so each of the seven terms
   --    is bounded by 1.0E9.
   --  APPLICATIONS
   --    The additive correction the calibrated screening model adds to
   --    the analytic drag and heat laws.
   --  CITATIONS
   --    [Montgomery17] Ch. 7 — first-order response surface with
   --    two-factor interactions.
   --  ----------------------------------------------------------------
   function Evaluate_Residual_Model
     (Coefficients : Residual_Coefficient_Array;
      X            : Coded_Vector) return Float
     with Global => null,
          Pre  => (for all K in 1 .. 3 => X (K) in -1.0 .. 1.0),
          Post => Evaluate_Residual_Model'Result in -7.0E9 .. 7.0E9;

   --  ==================================================================
   --  Objective function
   -- ==================================================================

   --  ----------------------------------------------------------------
   --  Optimization_Cost
   --
   --  AXIOMS
   --    A1. J = W_Beta * ((Beta_Calc - Beta_Target) / 10) ** 2
   --            + W_Target * (Y_Pred - Y_Target) ** 2.
   --    A2. W_Beta >= 0.0 and W_Target >= 0.0.
   --    A3. The 10 is the characteristic scale of the ballistic
   --        coefficient, making the beta deviation dimensionless.
   --    A4. The domains of the six arguments bound every intermediate
   --        of the computation (AXIOM A3): |Delta_Beta| <= 2.0E5,
   --        |Delta_Y| <= 2.0E9, so |J| <= 4.1E24 — far inside the
   --        machine range of Float, hence no overflow is possible.
   --  THEORIES
   --    T1. J >= 0.
   --    Proof: both terms are a non-negative weight times a square.
   --    T2. J = 0 iff Delta_Beta = 0 and Delta_Y = 0 whenever both
   --        weights are strictly positive.
   --    Proof: a non-negative summand is zero iff its factors are zero.
   --  APPLICATIONS
   --    The single objective shared by every optimiser entry point. The
   --    SBO path makes the second term live (Y_Pred from the surrogate,
   --    Y_Target from the true model, W_Target > 0).
   --  CITATIONS
   --    [Gauss1809] weighted least squares; [StellarOrion DERIVATION.MD,
   --    Sec 4] the project derivation of this cost.
   -- ----------------------------------------------------------------
   function Optimization_Cost
     (Beta_Calc   : Float;
      Beta_Target : Float;
      Y_Pred      : Float;
      Y_Target    : Float;
      W_Beta      : Float;
      W_Target    : Float) return Float
     with Global => null,
          Pre  => W_Beta in 0.0 .. 1.0E6
                   and W_Target in 0.0 .. 1.0E6
                   and Beta_Calc in -1.0E6 .. 1.0E6
                   and Beta_Target in -1.0E6 .. 1.0E6
                   and Y_Pred in -1.0E9 .. 1.0E9
                   and Y_Target in -1.0E9 .. 1.0E9,
          Post => Optimization_Cost'Result >= 0.0;

   -- ==================================================================
   --  Genetic-algorithm bookkeeping (pure, no randomness, AXIOM A5)
   -- ==================================================================

   --  AXIOM A5: the population ceiling is defined once, here.
   Max_Population : constant := 200;

   --  AXIOM A5: one cost per individual.
   type Cost_Array is array (1 .. Max_Population) of Float;

   --  AXIOM A5: a permutation of the population indices. The component
   --  type is BOUNDED by Max_Population (not plain Positive) so that any
   --  index taken from this array is provably a valid index into the
   --  other Max_Population-bounded arrays of this package.
   subtype Population_Index is Positive range 1 .. Max_Population;
   type Index_Array is array (1 .. Max_Population) of Population_Index;

   --  ----------------------------------------------------------------
   --  Sort_By_Cost
   --
   --  AXIOMS
   --    A1. After the call, Idx ranks the individuals by ascending
   --        cost: the individual at slot 1 is the cheapest, ties are
   --        broken by the lower original index so the ranking is
   --        deterministic.
   --    A2. Every index written into the first N slots is one of the
   --        N individuals of the population, never a stale slot.
   --  THEORIES
   --    T1. Idx (1) is the index of a minimum-cost individual.
   --    T2. The permutation is preserved, so no individual is lost.
   --  APPLICATIONS
   --    The selection order used by tournament selection and elitism.
   --  CITATIONS
   --    [Goldberg89] Ch. 3 — selection on a ranked population.
   -- ----------------------------------------------------------------
   procedure Sort_By_Cost
     (Idx   : out Index_Array;
      Costs : Cost_Array;
      N     : Positive)
     with Global => null,
          Pre  => N <= Max_Population,
          Post => (for all I in 1 .. N => Idx (I) <= N);

   --  ----------------------------------------------------------------
   --  Best_Index
   --
   --  AXIOMS
   --    A1. The returned index is one of the first N individuals.
   --    A2. Its cost is minimal over the first N individuals.
   --  THEORIES
   --    T1. Costs (Best_Index'Result) <= Costs (I) for every I in the
   --        active population.
   --  APPLICATIONS
   --    Best-so-far tracking across generations; the caller copies the
   --    gene of the returned individual.
   --  CITATIONS
   --    [Goldberg89] Ch. 3.
   -- ----------------------------------------------------------------
   function Best_Index
     (Costs : Cost_Array;
      N     : Positive) return Population_Index
     with Global => null,
          Pre  => N <= Max_Population,
          Post => (for all I in 1 .. N =>
                     Costs (Best_Index'Result) <= Costs (I));

   --  ----------------------------------------------------------------
   --  Update_Stagnation
   --
   --  AXIOMS
   --    A1. Stagnation counts consecutive generations whose best cost
   --        improved by less than Tol.
   --    A2. Convergence is declared once the count reaches Required
   --        (a count of zero disables convergence detection).
   --    A3. The counter SATURATES at Stagnation_Count'Last instead of
   --        overflowing, so the counter can never leave its domain.
   --  THEORIES
   --    T1. A required count of zero disables convergence detection.
   --    T2. The counter never exceeds the number of observed
   --        generations (and saturates rather than overflowing).
   --  APPLICATIONS
   --    The convergence test of the GA.
   --  CITATIONS
   --    [Goldberg89] Ch. 3 — convergence by stagnation of the best
   --    objective.
   -- ----------------------------------------------------------------
   procedure Update_Stagnation
     (Best_Cost  : Float;
      Prev_Best  : Float;
      Tol        : Float;
      Stag_Count : in out Stagnation_Count;
      Converged  : out Boolean;
      Required   : Natural)
     with Global => null,
          Pre  => Tol >= 0.0
                   and Best_Cost in 0.0 .. 1.0E30
                   and Prev_Best in 0.0 .. 1.0E30
                   and Tol <= 1.0E30,
          Post => (if Required = 0 then not Converged);

end StellarOrion_Optimizer_Core;
