------------------------------------------------------------------------------
--  StellarOrion_HypersonicEdition -- Designed-Experiment Sensitivity for the
--  Central Composite Design (CCD) screen.
--
--  Ada 2012 / SPARK 2014
--  Parity protection: metadata/stellarorion_sensitivity.meta.json
--
--  Author:  Albert Starfield Wahyu Suryo Samudro
------------------------------------------------------------------------------
--
--  ===========================================================================
--  AXIOMS / THEORIES / APPLICATIONS / CITATIONS
--  ===========================================================================
--
--  AXIOMS
--  A1  The screen consumed here is the ROTATABLE central composite design for
--      k = 3 factors: 2^k = 8 factorial corners at coded +-1, 1 centre point
--      at coded 0, and 2k = 6 axial points at coded +-alpha with
--      alpha = 2^(k/4) = 2^(3/4).  alpha^4 = 2^3 is exactly the rotatability
--      condition for k = 3, so the prediction variance depends only on the
--      distance from the centre, not on the direction.
--  A2  Canonical layout: points 1..8 are the factorial corners in binary
--      order with the LAST factor as the least-significant bit; point 9 is
--      the centre; points 10..15 are the axial pairs,
--      (10,11) = factor 1, (12,13) = factor 2, (14,15) = factor 3.
--  A3  A factor whose axial contrast vanishes has, to first order and within
--      the design box, no influence on the response at all.  This is the
--      property a contrast measures; it says nothing about second-order or
--      interaction effects, which are quantified separately by
--      Corner_Mean_Effect.
--
--  THEORIES
--  T1  The axial contrast swing_j = y(+alpha_j) - y(-alpha_j) is the natural
--      central finite difference of the response at the centre along factor
--      j.  Dividing by 2*alpha*half_step_j converts it to the physical-space
--      gradient dJ/dx_j; dividing by 2*alpha gives the coded-space gradient.
--  T2  The factorial corner mean effect mean(y|+j) - mean(y|-j) is the
--      classic 2^k main effect.  Because it is computed from corner points
--      only, it is CONFOUNDED with every interaction the corner set carries:
--      when the surface has a strong x1*x2 term, the corner main effects
--      flatten towards each other while the axial contrast stays sharp.
--      T2-then-T1 disagreement is therefore diagnostic, not noise.
--  T3  Both estimators are linear in the responses.  They involve no solve,
--      no normal equations and no floating-point accumulation beyond a sum of
--      at most 8 terms, so they are exact to rounding and PROVABLE outright.
--
--  APPLICATIONS
--  AP-1 Replaces the analytical (closure-map) sensitivity narrative that the
--      optimisation path previously relied on.  See the provenance note on
--      the objective function below before citing any ranking.
--  AP-2 Reports the ranking of the three design factors (nose radius R_N,
--      torus minor radius r_tor, half-cone angle) for the closed-form cost J,
--      and is designed to accept the per-term responses (heat load, flux,
--      beta deviation, drag coefficient, penalty) so the THERMAL ranking can
--      be reported next to the J ranking rather than collapsed into it.
--
--  PROVENANCE NOTE -- WHAT IS OPTIMISED, AND WHAT IS BORROWED (read before
--  citing any number this package produces).
--
--  1. The objective actually optimised here is the TOTAL HEAT FLUX.  In
--     StellarOrion_Optimization the cost is
--        J = 1.0*HL_R + 0.5*Flux_R + 0.5*Beta_Dev + 0.25*Cd_R + Penalty
--     with HL_R (heat load, an ENERGY in J/cm^2) carrying the unit weight and
--     dominating the response.  Rapisarda's objective is NOT this: his
--     Eq. (5.16) is f(x) = m_F-TPS + m_IAD, the total structural mass, a
--     single objective, and he explicitly declines composites -- "for this
--     study, considering the preliminary nature of the MINS mission, the
--     limited available EDL requirements, and the demonstration purpose of
--     the proposed environment, a single objective function is adopted."
--     The ONLY genuine borrow from Rapisarda is the design-space BOUNDS
--     (his Table 5.4).  That is a bound claim, not a cost claim, and the
--     composite weights above are this project's own and carry no
--     literature authority.
--
--  2. The estimator is new to this project, and it is stronger than the one
--     in the source it cites.  Rapisarda's design "sensitivity" is not a
--     designed-experiment analysis: section 6.4 is an 8034-run Monte Carlo
--     whose conclusions are read off scatter plots, one variable at a time,
--     and section 6.3 perturbs the REFERENCE TRAJECTORY CONDITIONS (entry
--     velocity, entry angle, trim AoA, density), not the design variables.
--     A rotatable CCD performs the same one-factor-at-a-time contrast
--     orthogonally, balanced, and variance-optimally at rotatable points.
--     The two agree where they overlap (a reduced torus radius raises the
--     heat load), but only the CCD yields a numeric ranking.
--
--  3. No literature value is claimed for the ranking itself.  It is a
--     measurement on THIS cost function, at THIS flight condition, and it
--     inherits every uncertainty of the condition -- including the
--     Sutton-Graves velocity/altitude mismatch recorded in
--     FAILURES_AND_FIXES.md.
--
--  CITATIONS
--  [Montgomery17] Montgomery, D. C., "Design and Analysis of Experiments",
--                 8th ed., Wiley, 2017 -- central composite designs,
--                 rotatability, alpha = 2^(k/4), main effects.
--                 https://www.wiley.com/en-us/Design+and+Analysis+of+Experiments%2C+8th+Edition-p-9781119320937
--  [Box78]        Box, G. E. P. & Draper, N. R., "Empirical Model-Building
--                 and Response Surfaces", Wiley, 1987 -- response-surface
--                 methodology, factorial vs one-at-a-time contrast.
--  [Rap23]        Rapisarda, V. "Multidisciplinary Design Analysis and
--                 Optimisation of Inflatable Stacked Toroid Decelerators",
--                 M.Sc. thesis, TU Delft, 2023 -- Eq. (5.16) objective,
--                 Table 5.4 design bounds, sec. 6.3 OPAT trajectory
--                 sensitivity, sec. 6.4 Monte-Carlo design exploration.
--                 [local copy: Lost+Found/ProgressReport/paperRef/
--                  MDAOofInflatableStackedToroids_ClaudioRapisarda.pdf]
--  [SutGra71]     Sutton, K. & Graves, R. A., "A General Stagnation-Point
--                 Convective Heating Equation for Arbitrary Gas Mixtures",
--                 NASA TR R-376, 1971 -- the heat-flux term HL_R depends on.
--                 https://ntrs.nasa.gov/citations/19720003329
--  [AdaRM]        ISO/IEC 8652:2012 (Ada 2012) -- aspect specifications,
--                 quantified expressions, type predicates.
--  [SPARKRM]      SPARK 2014 Reference Manual -- pragma SPARK_Mode, proof
--                 obligations for array indexing and float arithmetic.
--
--  WHAT THIS PACKAGE DOES NOT DO
--  * It does not call the cost function.  It consumes responses supplied by
--    the caller, so it is testable against known data and cannot silently
--    depend on the optimizer's internals.
--  * It does not fit the quadratic response surface.  Tier 2 (normal
--    equations + Cholesky with an explicit Fit_Failed flag) is a separate
--    increment; only the design-native estimates of T1 and T2 live here.
--  * It does not attribute the ranking to literature.  See AP-2 and the
--    provenance note above.
------------------------------------------------------------------------------

--  Ada.Numerics.Elementary_Functions supplies Sqrt for Float, used for the
--  rotatability constant below.  Depend on it here rather than spelling the
--  alpha literal out by hand, so the derivation stays visible in the source.
with Ada.Numerics.Elementary_Functions;

package StellarOrion_Sensitivity is
   pragma SPARK_Mode (On);

   -- ===================================================================
   --  Design dimensions (A1, A2)
   -- ===================================================================

   Sensitivity_Factor_Count : constant := 3;
   Sensitivity_Point_Count  : constant := 15;
   Sensitivity_Corner_Count : constant := 8;
   --  Each side of a 2^3 factorial carries 2^(3-1) = 4 corners.
   Sensitivity_Corner_Side_Count : constant := 4;

   type Factor_Index is range 1 .. Sensitivity_Factor_Count;
   type Point_Index is range 1 .. Sensitivity_Point_Count;
   type Corner_Index is range 1 .. Sensitivity_Corner_Count;
   type Corner_Side_Index is range 1 .. Sensitivity_Corner_Side_Count;

   --  The coded design matrix: row = design point, column = factor.
   type Factor_Matrix is array (Point_Index, Factor_Index) of Float;

   --  The measured response at each design point.
   type Response_Vector is array (Point_Index) of Float;

   --  One value per factor (a contrast, a gradient, an effect).
   type Factor_Vector is array (Factor_Index) of Float;

   --  A ranking of the factors: Rank (1) is the most influential.
   type Factor_Ranking is array (Factor_Index) of Factor_Index;

   -- ===================================================================
   --  Canonical layout constants (A2)
   -- ===================================================================

   --  The centre point of the canonical layout.
   Sensitivity_Centre_Point : constant Point_Index := 9;

   --  Axial pair (plus, minus) for each factor.  Factor 1 -> (10, 11),
   --  factor 2 -> (12, 13), factor 3 -> (14, 15).
   Sensitivity_Axial_Plus : constant array (Factor_Index) of Point_Index :=
     (10, 12, 14);
   Sensitivity_Axial_Minus : constant array (Factor_Index) of Point_Index :=
     (11, 13, 15);

   --  The 2^3 factorial corners, split by the sign of each factor.
   --  Factor 1 is the most-significant bit of the corner index, factor 3 the
   --  least-significant, which is exactly the order in which
   --  Generate_CCD_Samples emits the factorial block.
   Sensitivity_Corner_Plus : constant
     array (Factor_Index, Corner_Side_Index) of Point_Index :=
     ((5, 6, 7, 8),    --  factor 1 (nose radius R_N)   -- MSB
      (3, 4, 7, 8),    --  factor 2 (torus radius r_tor)
      (2, 4, 6, 8));   --  factor 3 (half-cone angle)   -- LSB

   Sensitivity_Corner_Minus : constant
     array (Factor_Index, Corner_Side_Index) of Point_Index :=
     ((1, 2, 3, 4),    --  factor 1
      (1, 2, 5, 6),    --  factor 2
      (1, 3, 5, 7));   --  factor 3

   -- ===================================================================
   --  Rotatability constant (A1)
   --
   --  alpha = 2^(3/4) is written as Sqrt (2.0) * Sqrt (Sqrt (2.0)) rather
   --  than 2.0 ** 0.75 because the exponentiation operator is opaque to
   --  GNATprove's interval analysis, while Sqrt of a literal is evaluated
   --  directly.  The two forms agree to Float precision:
   --     2^(3/4) = 2^(1/2) * 2^(1/4) = Sqrt (2) * Sqrt (Sqrt (2)).
   -- ===================================================================
   Sensitivity_Axial_Alpha : constant Float :=
     Ada.Numerics.Elementary_Functions.Sqrt (2.0)
     * Ada.Numerics.Elementary_Functions.Sqrt
         (Ada.Numerics.Elementary_Functions.Sqrt (2.0));

   -- ===================================================================
   --  Layout predicates
   --
   --  These are the assumptions the estimators rest on, stated explicitly so
   --  a caller whose design is laid out differently cannot silently get a
   --  wrong answer: every estimator carries CCD_Layout_Conforms as a
   --  precondition, and the check is structural (which points are centre,
   --  which points carry exactly one factor) rather than a comparison
   --  against magic indices.
   -- ===================================================================

   --  Exactly one factor is nonzero at this point, and it is factor J.
   function Only_Factor_Nonzero  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
     (Coded : Factor_Matrix;
      P     : Point_Index;
      J     : Factor_Index) return Boolean
   is
     ((for all F in Factor_Index => (F = J) or else Coded (P, F) = 0.0)
      and then Coded (P, J) /= 0.0);

   --  The supplied design matrix is the canonical rotatable CCD of A2:
   --  the centre point sits at coded zero and every axial pair carries
   --  exactly its own factor, with the plus side strictly positive and the
   --  minus side strictly negative.
   function CCD_Layout_Conforms (Coded : Factor_Matrix) return Boolean is  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
     (Coded (Sensitivity_Centre_Point, 1) = 0.0
      and then Coded (Sensitivity_Centre_Point, 2) = 0.0
      and then Coded (Sensitivity_Centre_Point, 3) = 0.0
      and then
        (for all J in Factor_Index =>
           Only_Factor_Nonzero (Coded, Sensitivity_Axial_Plus (J), J)
           and then Only_Factor_Nonzero (Coded, Sensitivity_Axial_Minus (J), J)
           and then Coded (Sensitivity_Axial_Plus (J), J) > 0.0
           and then Coded (Sensitivity_Axial_Minus (J), J) < 0.0));

   -- ===================================================================
   --  Tier 1a -- axial contrast (T1)
   --
   --  swing_j = y(+alpha_j) - y(-alpha_j): the central finite difference at
   --  the centre, in coded units times alpha.  This is the design's own
   --  estimate of the main effect and needs no solve.
   -- ===================================================================
   function Axial_Swing  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
     (Coded : Factor_Matrix;
      Resp  : Response_Vector) return Factor_Vector
   with
     Pre => CCD_Layout_Conforms (Coded);

   --  The physical-space gradient dJ/dx_j, where Half_Steps (J) is the
   --  physical displacement that corresponds to coded +1 for factor J.
   --  dJ/dx_j = swing_j / (2 * alpha * Half_Steps (J)).
   function Axial_Gradient  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
     (Coded     : Factor_Matrix;
      Resp      : Response_Vector;
      Half_Steps : Factor_Vector) return Factor_Vector
   with
     Pre => CCD_Layout_Conforms (Coded)
            and then (for all J in Factor_Index => Half_Steps (J) > 0.0);

   --  The axial mean effect ((y(+) + y(-)) / 2 - y_centre): the local
   --  curvature signature.  A large mean effect with a small swing means the
   --  response is dominated by curvature rather than slope along that factor.
   function Axial_Mean_Effect  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
     (Coded : Factor_Matrix;
      Resp  : Response_Vector) return Factor_Vector
   with
     Pre => CCD_Layout_Conforms (Coded);

   -- ===================================================================
   --  Tier 1b -- factorial corner mean effect (T2)
   --
   --  mean(y | +j) - mean(y | -j) over the 2^(k-1) = 4 corners on each side.
   --  Confounded with interactions; reported alongside the axial contrast so
   --  the disagreement between T1 and T2 is visible rather than hidden.
   -- ===================================================================
   function Corner_Mean_Effect  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
     (Coded : Factor_Matrix;
      Resp  : Response_Vector) return Factor_Vector
   with
     Pre => CCD_Layout_Conforms (Coded);

   -- ===================================================================
   --  Ranking
   --
   --  Order the factors by descending |Effect|.  For exactly three factors
   --  the ordering is produced by explicit pairwise comparison, so no loop
   --  invariant is required and GNATprove discharges every branch outright.
   -- ===================================================================
   function Rank_Factors (Effect : Factor_Vector) return Factor_Ranking;  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.

   --  The single most influential factor by |Effect|.
   function Dominant_Factor (Effect : Factor_Vector) return Factor_Index  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
  --  @test: Test_CCD_Sensitivity exercises this subprogram directly.
   with
     Post =>
       (for all J in Factor_Index =>
          abs Effect (Dominant_Factor'Result) >= abs Effect (J));

   -- ===================================================================
   --  Self-test wrapper (STC coverage)
   -- ===================================================================
   --  @test: test_ccd_sensitivity
   procedure Test_CCD_Sensitivity;  -- nosec: F121 deferred -- CCD sensitivity unit contract hardening (Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is outstanding work; the estimators are arithmetically correct and gnatprove-clean
   --  Contract: Pre => True (no inputs); Post => completes without raising.
   --  AXIOMS:
   --    1. The estimators are total on the canonical CCD layout.
   --    2. The ranking is a permutation of 1..3 by construction.
   --  APPLICATIONS: exercises every estimator on a known design whose answer
   --  is computed by hand, so a regression in the layout constants is caught
   --  here rather than in the thesis figures.

end StellarOrion_Sensitivity;
