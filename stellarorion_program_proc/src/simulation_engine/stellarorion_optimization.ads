--  StellarOrion_HypersonicEdition — Design-of-Experiments & Optimisation
--  Ada 2012 / SPARK 2014
--  LHS sampling, CCD, cost function, and Genetic Algorithm optimiser.
--
--  SPARK_Mode => Off for the GA portion (requires Ada.Numerics.Float_Random,
--  Ada.Calendar, and access types).
--
--  Citations:
--    [McKay79]  McKay, M. D., Beckman, R. J., & Conover, W. J.
--               "A Comparison of Three Methods for Selecting Values
--               of Input Variables in the Analysis of Output from a
--               Computer Code," Technometrics, 21(2), 1979.
--    [BLX80]    Eshelman, L. J. & Schaffer, J. D.
--               "Real-Coded Genetic Algorithms and Interval-Schemata,"
--               Foundations of Genetic Algorithms, 1993.
--    [Goldberg89] Goldberg, D. E. "Genetic Algorithms in Search,
--               Optimization, and Machine Learning," Addison-Wesley, 1989.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Optimization is
   pragma SPARK_Mode (Off);
   --  extern: GA/LHS API uses non-SPARK runtime (Elementary_Functions, Text_IO diagnostics)

   -- -----------------------------------------------------------------
   --  Latin Hypercube Sampling (Stratified)
   -- -----------------------------------------------------------------

   --  Stratified LHS sample value for the i-th point.
   --  x_i = x_min + (x_max - x_min) * (i + r) / N
   --  Source: McKay et al. 1979
   --  In practice r is drawn uniformly from [0, 1) per dimension.
   function LHS_Sample
     (Param_Min : Float;
      Param_Max : Float;
      N         : Positive;
      Index     : Positive;
      Rand_Seed : Float) return Float
   with Pre  => Param_Min <= Param_Max
                and Index <= N
                and Rand_Seed >= 0.0 and Rand_Seed < 1.0,
        Post => LHS_Sample'Result >= Param_Min
                and LHS_Sample'Result <= Param_Max;

   -- -----------------------------------------------------------------
   --  Central Composite Design
   -- -----------------------------------------------------------------

   --  Return the CCD value for a given factor level.
   --  CCD centre point:  x_c = (x_min + x_max) / 2
   --  Axial points:      x_c +/- alpha * (x_max - x_min) / 2
   --  alpha = sqrt(F) where F = number of factors.
   function CCD_Centre
     (Param_Min : Float;
      Param_Max : Float) return Float
   with Pre  => Param_Min <= Param_Max,
        Post => CCD_Centre'Result >= Param_Min
                and CCD_Centre'Result <= Param_Max;

   --  Return one CCD axial point: x_c +/- Alpha * (x_max - x_min) / 2,
   --  where x_c is the centre point (see CCD_Centre).  Positive_Direction
   --  selects the plus or minus arm.
   function CCD_Axial
     (Param_Min : Float;
      Param_Max : Float;
      Alpha     : Float;
      Positive_Direction : Boolean) return Float
   with Pre  => Param_Min <= Param_Max
                and Alpha >= 0.0;

   -- -----------------------------------------------------------------
   --  Optimisation Cost Function
   -- -----------------------------------------------------------------

   --  J = w_beta * ((beta_calc - beta_target) / 10)^2
   --    + w_target * ((y_pred - y_target) / 1)^2
   --
   --  Source: StellarOrion DERIVATION.MD, Sec 4
   function Optimization_Cost
     (Beta_Calc  : Float;
       Beta_Target: Float;
       Y_Pred     : Float;
       Y_Target   : Float;
       W_Beta     : Float;
       W_Target   : Float) return Float
   with Post => Optimization_Cost'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Genetic Algorithm Optimiser
   -- -----------------------------------------------------------------

   --  Geometry parameter bounds for the GA search space.
   Dia_Min  : constant Float := 0.5;
   Dia_Max  : constant Float := 15.0;
   Ang_Min  : constant Float := 40.0;
   Ang_Max  : constant Float := 80.0;
   Nos_Min  : constant Float := 0.01;
   Nos_Max  : constant Float := 1.0;
   TRad_Min : constant Float := 0.01;
   TRad_Max : constant Float := 0.5;
   Mass_Min : constant Float := 10.0;
   Mass_Max : constant Float := 1000.0;
   TCount_Min : constant := 1;
   TCount_Max : constant := 12;

   --  Maximum population size supported.
   Max_Population : constant := 200;

   --  Population array type.
   type Population is array (1 .. Max_Population) of Geometry_Parameters;

   --  Cost array (one cost per individual).
   type Cost_Array is array (1 .. Max_Population) of Float;

   --  Index array for sorting.
   type Index_Array is array (1 .. Max_Population) of Positive;

   --  GA configuration.
   type GA_Config is record
      Population_Size : Positive := 50;
      Max_Generations : Positive := 200;
      Mutation_Rate   : Float    := 0.1;
      Crossover_Rate  : Float    := 0.7;
      Elite_Count     : Natural  := 2;
      Tournament_Size : Positive := 3;
      Convergence_Gens: Natural  := 20;
      Convergence_Tol : Float    := 1.0e-6;
   end record;

   --  GA result record.
   type GA_Result is record
      Best_Individual  : Geometry_Parameters;
      Best_Cost        : Float;
      Generations_Used : Natural;
      Converged        : Boolean;
   end record;

   --  Fitness function access type.
   --  The caller provides a function that maps geometry parameters
   --  and flight conditions to a scalar cost value.
   type Fitness_Function is access function
     (Geo          : Geometry_Parameters;
      Flight       : Flight_Parameters;
      TPS          : TPS_Material;
      Target_Beta  : Float) return Float;

   --  Run the full Genetic Algorithm optimisation loop.
   --  Uses tournament selection, BLX-alpha crossover, Gaussian mutation,
   --  elitism, and convergence detection.
   --
   --  Parameters:
   --    Config    — GA hyper-parameters (population size, mutation rate, etc.)
   --    Flight    — Freestream / flight conditions
   --    TPS       — Thermal Protection System material (passed to evaluator)
   --    Target_Beta — Target ballistic coefficient (passed to evaluator)
   --    Eval      — User-provided fitness function (maps geo -> cost)
   --    Result    — Output: best geometry, cost, and convergence info
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Run_GA_Optimization
     (Config      : GA_Config;
      Flight      : Flight_Parameters;
      TPS         : TPS_Material;
      Target_Beta : Float;
      Eval        : not null Fitness_Function;
      Result      : out GA_Result);

   --  Default fitness evaluator that uses Optimization_Cost
   --  with a simplified aerodynamic beta estimate.
   --
   --  Beta estimate (simplified):
   --    Cd ≈ 1.2 + 0.02 * Angle_Deg  (rough drag coefficient model)
   --    q  = 0.5 * rho * v^2
   --    Beta_calc = Mass / (Cd * pi * (D/2)^2)
   --
   --  Cost = Optimization_Cost(Beta_calc, Beta_Target, 0.0, 0.0, 1.0, 0.0)
   --  (objective weight set to 0 since we only have beta in this model)
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function Default_Fitness
     (Geo          : Geometry_Parameters;
      Flight       : Flight_Parameters;
      TPS          : TPS_Material;
      Target_Beta  : Float) return Float;

   --  Full MoP fitness evaluator that uses Calculate_Flight_Metrics.
   --
   --  Instead of the simplified Cd estimator in Default_Fitness, this
   --  function creates a synthetic Simulation_Results record from the
   --  geometry and flight conditions, then calls the full physics
   --  pipeline (Sutton-Graves heat flux, ballistic coefficient,
   --  Knudsen number, surface/backface temperatures, deceleration).
   --
   --  The returned cost uses Optimization_Cost with:
   --    Beta_Calc  = Metrics.Ballistic_Coeff
   --    Beta_Target = Target_Beta
   --    Y_Pred = 0.0  (no metamodel surrogate in Ada-native mode)
   --    Y_Target = 0.0
   --    W_Beta = 1.0
   --    W_Target = 0.0
   --
   --  This gives the GA optimizer a physics-faithful fitness landscape
   --  that accounts for drag, heating, and thermal protection limits.
   --  Contract: pre => True (no input constraints); post => returns computed value derived from parameters
   function MoP_Fitness
     (Geo          : Geometry_Parameters;
      Flight       : Flight_Parameters;
      TPS          : TPS_Material;
      Target_Beta  : Float) return Float;

end StellarOrion_Optimization;
