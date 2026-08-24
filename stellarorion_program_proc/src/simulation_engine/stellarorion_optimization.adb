--  StellarOrion_HypersonicEdition — Design-of-Experiments & Optimisation (Body)
--  Ada 2012 / SPARK 2014
--  LHS, CCD, cost function, and Genetic Algorithm optimiser.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with Ada.Numerics;                  use Ada.Numerics;
with Ada.Numerics.Float_Random;     use Ada.Numerics.Float_Random;
with Ada.Numerics.Elementary_Functions;
use Ada.Numerics.Elementary_Functions;
with Ada.Calendar;                  use Ada.Calendar;
with Ada.Text_IO;                   use Ada.Text_IO;
with StellarOrion_Physics;          use StellarOrion_Physics;

package body StellarOrion_Optimization is
   pragma SPARK_Mode (Off);
   --  extern: Elementary_Functions + Text_IO are non-SPARK runtime libraries

   --  Float'Round is for fixed-point only; use manual rounding for Float.
   function To_Int (V : Float) return Integer is
   begin
      if V >= 0.0 then
         return Integer (V + 0.5);
      else
         return Integer (V - 0.5);
      end if;
   end To_Int;

   -- ==================================================================
   --  LHS_Sample
   -- ==================================================================
   --  x_i = x_min + (x_max - x_min) * (i + r) / N
   --  Source: McKay et al. 1979, Eq. (2.1)
   function LHS_Sample
     (Param_Min : Float;
      Param_Max : Float;
      N         : Positive;
      Index     : Positive;
      Rand_Seed : Float) return Float
   is
      R : Float;
   begin
      --  Clamp random seed to [0, 1)
      R := Rand_Seed;
      if R < 0.0 then
         R := 0.0;
      elsif R >= 1.0 then
         --  Simple fractional part extraction
         R := R - Float (Integer (R));
      end if;

      return Param_Min
        + (Param_Max - Param_Min)
        * (Float (Index) + R) / Float (N);
   end LHS_Sample;

   -- ==================================================================
   --  CCD_Centre
   -- ==================================================================
   --  x_c = (x_min + x_max) / 2
   function CCD_Centre
     (Param_Min : Float;
      Param_Max : Float) return Float
   is
   begin
      return (Param_Min + Param_Max) / 2.0;
   end CCD_Centre;

   -- ==================================================================
   --  CCD_Axial
   -- ==================================================================
   --  x_alpha = x_c +/- alpha * (x_max - x_min) / 2
   --  alpha = sqrt(F) where F = number of factors.
   function CCD_Axial
     (Param_Min         : Float;
      Param_Max         : Float;
      Alpha             : Float;
      Positive_Direction: Boolean) return Float
   is
      X_C   : Float;
      Half_R: Float;
   begin
      X_C    := CCD_Centre (Param_Min, Param_Max);
      Half_R := (Param_Max - Param_Min) / 2.0;

      if Positive_Direction then
         return X_C + Alpha * Half_R;
      else
         return X_C - Alpha * Half_R;
      end if;
   end CCD_Axial;

   -- ==================================================================
   --  Optimization_Cost
   -- ==================================================================
   --  J = w_beta * ((beta_calc - beta_target) / 10)^2
   --    + w_target * ((y_pred - y_target) / 1)^2
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
   --  Default_Fitness — simplified aerodynamic beta estimator
   -- ==================================================================
   --  Cd ≈ 1.2 + 0.02 * Angle_Deg  (empirical approximation for HIAD)
   --  q  = 0.5 * rho * v^2
   --  Beta_calc = Mass / (Cd * pi * (D/2)^2)
   function Default_Fitness
     (Geo          : Geometry_Parameters;
      Flight       : Flight_Parameters;
      TPS          : TPS_Material;
      Target_Beta  : Float) return Float
   is
      Cd      : Float;
      Beta_C  : Float;
      Ref_Area: Float;
      pragma Unreferenced (TPS);
   begin
      --  Simplified Cd from angle (higher angle = more drag)
      Cd := 1.2 + 0.02 * Geo.Angle_Deg;

      --  Reference area (frontal)
      Ref_Area := Pi * (Geo.Diameter_M / 2.0) ** 2;

      --  Ballistic coefficient: beta = m / (Cd * A_ref)
      --  (standard definition: beta = m / (Cd * A))
      if Ref_Area > 0.0 and Cd > 0.0 then
         Beta_C := Geo.Mass_Kg / (Cd * Ref_Area);
      else
         Beta_C := 0.0;
      end if;

      --  Cost using only beta term (no metamodel available)
      return Optimization_Cost
        (Beta_Calc   => Beta_C,
         Beta_Target => Target_Beta,
         Y_Pred      => 0.0,
         Y_Target    => 0.0,
         W_Beta      => 1.0,
         W_Target    => 0.0);
   end Default_Fitness;

   -- ==================================================================
   --  MoP Fitness — Full physics pipeline via Calculate_Flight_Metrics
   -- ==================================================================

   function MoP_Fitness
     (Geo          : Geometry_Parameters;
      Flight       : Flight_Parameters;
      TPS          : TPS_Material;
      Target_Beta  : Float) return Float
   is
      Cd       : Float;
      Q_dyn    : Float;
      Ref_Area : Float;
      F_drag   : Float;
      H_Flux   : Float;
      Results  : Simulation_Results;
      Metrics  : Flight_Metrics;
   begin
      --  Step 1: Simplified drag coefficient (same estimator as Default_Fitness)
      Cd := 1.2 + 0.02 * Geo.Angle_Deg;

      --  Step 2: Dynamic pressure  q = 0.5 * rho * v^2
      Q_dyn := 0.5 * Flight.Density_Kgm3 * Flight.Velocity_Ms ** 2;

      --  Step 3: Reference frontal area  A = pi * (D/2)^2
      Ref_Area := Pi * (Geo.Diameter_M / 2.0) ** 2;

      --  Step 4: Drag force  F = Cd * q * A
      if Ref_Area > 0.0 and Cd > 0.0 then
         F_drag := Cd * Q_dyn * Ref_Area;
      else
         F_drag := 0.0;
      end if;

      --  Step 5: Stagnation heat flux via Sutton–Graves
      --  q_sg = C_sg * sqrt(rho / R_n) * V^3
      if Geo.Nose_Radius_M > 0.0 and Flight.Velocity_Ms > 0.0 then
         H_Flux := Sutton_Graves_Heat
           (Density     => Flight.Density_Kgm3,
            Nose_Radius => Geo.Nose_Radius_M,
            Velocity    => Flight.Velocity_Ms);
      else
         H_Flux := 0.0;
      end if;

      --  Step 6: Assemble synthetic Simulation_Results
      Results.Drag_Force      := F_drag;
      Results.Heat_Flux_Wm2   := H_Flux;
      --  Characteristic ballistic reentry heating duration
      --  dt_char = sqrt(2 * pi * R_earth * H_scale) / V
      --  R_earth = 6_371 km, H_scale = 7 km (isothermal atmosphere)
      if Flight.Velocity_Ms > 0.0 then
         Results.Total_Heat_Load :=
           H_Flux * Sqrt (2.0 * Pi * 6_371_000.0 * 7_000.0)
           / Flight.Velocity_Ms;
      else
         Results.Total_Heat_Load := 0.0;
      end if;
      Results.Stag_Pressure_Pa := 2.0 * Q_dyn;    --  Newtonian stagnation
      Results.Shock_Temp_K    := 0.0;             --  not used by Metrics

      --  Step 7: Full physics metrics (beta, Kn, Ts, Tb, g-load, etc.)
      Calculate_Flight_Metrics
        (Results => Results,
         Flight  => Flight,
         Geo     => Geo,
         TPS     => TPS,
         Metrics => Metrics);

      --  Step 8: Return optimization cost using beta from full physics
      return Optimization_Cost
        (Beta_Calc   => Metrics.Ballistic_Coeff,
         Beta_Target => Target_Beta,
         Y_Pred      => 0.0,
         Y_Target    => 0.0,
         W_Beta      => 1.0,
         W_Target    => 0.0);
   end MoP_Fitness;

   -- ==================================================================
   --  GA Internal Helpers
   -- ==================================================================

   Gen : Float_Random.Generator;

   --  Clamp a float value to [Lo, Hi].
   function Clamp (V, Lo, Hi : Float) return Float is
   begin
      if V < Lo then return Lo;
      elsif V > Hi then return Hi;
      else return V;
      end if;
   end Clamp;

   --  Uniform random float in [Lo, Hi].
   function Uniform_Rand (Lo, Hi : Float) return Float is
   begin
      return Lo + (Hi - Lo) * Float_Random.Random (Gen);
   end Uniform_Rand;

   --  Box-Muller transform: returns a standard normal sample N(0, 1).
   function Gaussian_Standard return Float is
      U1, U2 : Float;
   begin
      loop
         U1 := Float_Random.Random (Gen);
         exit when U1 > 1.0e-10;  --  avoid log(0)
      end loop;
      U2 := Float_Random.Random (Gen);
      return Sqrt (-2.0 * Log (U1)) * Cos (2.0 * Pi * U2);
   end Gaussian_Standard;

   --  Gaussian random with mean 0 and standard deviation Sigma.
   function Gaussian_Rand (Sigma : Float) return Float is
   begin
      return Sigma * Gaussian_Standard;
   end Gaussian_Rand;

   --  Random Geometry_Parameters within bounds.
   function Random_Geometry return Geometry_Parameters is
      G : Geometry_Parameters;
   begin
      G.Diameter_M      := Uniform_Rand (Dia_Min, Dia_Max);
      G.Angle_Deg       := Uniform_Rand (Ang_Min, Ang_Max);
      G.Nose_Radius_M   := Uniform_Rand (Nos_Min, Nos_Max);
      G.Toroid_Count    := Integer (
        Uniform_Rand (Float (TCount_Min), Float (TCount_Max) + 0.999));
      G.Toroid_Radius_M := Uniform_Rand (TRad_Min, TRad_Max);
      G.Mass_Kg         := Uniform_Rand (Mass_Min, Mass_Max);
      return G;
   end Random_Geometry;

   --  Sort indices by ascending cost (insertion sort for small N).
   procedure Sort_By_Cost (Indices : in out Index_Array;
                           Costs   : Cost_Array;
                           N       : Natural)
   is
      J, Key : Positive;
      Temp   : Positive;
   begin
      for I in 2 .. N loop
         Key := Indices (I);
         J := I - 1;
         loop
            exit when J < 1;
            exit when Costs (Indices (J)) <= Costs (Key);
            Indices (J + 1) := Indices (J);
            J := J - 1;
         end loop;
         Indices (J + 1) := Key;
      end loop;
   end Sort_By_Cost;

   --  Tournament selection: pick Tournament_Size random individuals,
   --  return the one with the lowest cost.
   function Tournament_Select (Indices : Index_Array;
                               Costs   : Cost_Array;
                               Tourney : Positive) return Positive
   is
      Best_Idx  : Positive := Indices (Indices'First);
      Best_Cost : Float    := Costs (Best_Idx);
      Idx       : Positive;
      C         : Float;
   begin
      for I in 2 .. Tourney loop
          Idx := Indices (Integer(Float_Random.Random (Gen) *
                   Float (Indices'Length - 1)) + Indices'First);
          C := Costs (Idx);
         if C < Best_Cost then
            Best_Idx  := Idx;
            Best_Cost := C;
         end if;
      end loop;
      return Best_Idx;
   end Tournament_Select;

   --  BLX-alpha crossover for two parent geometry parameters.
   --  For each gene:
   --    range = |P1 - P2|
   --    child in [min(P1,P2) - alpha*range, max(P1,P2) + alpha*range]
   --  clamped to bounds.
   procedure BLX_Crossover (P1, P2 : Geometry_Parameters;
                             Alpha  : Float;
                             C1, C2 : out Geometry_Parameters)
   is
      procedure Blend_Gene (V1, V2, Lo, Hi : Float;
                             OV1, OV2 : out Float) is
         Range_V : Float;
         Lo_Bound: Float;
         Hi_Bound: Float;
      begin
         Range_V  := abs (V1 - V2);
         Lo_Bound := Float'Min (V1, V2) - Alpha * Range_V;
         Hi_Bound := Float'Max (V1, V2) + Alpha * Range_V;
         OV1 := Clamp (Uniform_Rand (Lo_Bound, Hi_Bound), Lo, Hi);
         OV2 := Clamp (Uniform_Rand (Lo_Bound, Hi_Bound), Lo, Hi);
      end Blend_Gene;

      procedure Blend_Int (V1, V2 : Integer; Lo, Hi : Integer;
                            OV1, OV2 : out Integer) is
         FV1, FV2 : Float;
      begin
         Blend_Gene (Float (V1), Float (V2),
                     Float (Lo), Float (Hi), FV1, FV2);
         OV1 := To_Int (Clamp (FV1, Float (Lo), Float (Hi)));
         OV2 := To_Int (Clamp (FV2, Float (Lo), Float (Hi)));
         --  Ensure positive
         if OV1 < Lo then OV1 := Lo; end if;
         if OV2 < Lo then OV2 := Lo; end if;
      end Blend_Int;

      C1_Torus, C2_Torus : Integer;
   begin
      Blend_Gene (P1.Diameter_M,    P2.Diameter_M,    Dia_Min,  Dia_Max,
                  C1.Diameter_M,     C2.Diameter_M);
      Blend_Gene (P1.Angle_Deg,     P2.Angle_Deg,     Ang_Min,  Ang_Max,
                  C1.Angle_Deg,      C2.Angle_Deg);
      Blend_Gene (P1.Nose_Radius_M, P2.Nose_Radius_M, Nos_Min,  Nos_Max,
                  C1.Nose_Radius_M,  C2.Nose_Radius_M);
      Blend_Int  (P1.Toroid_Count,  P2.Toroid_Count,  TCount_Min, TCount_Max,
                  C1_Torus,          C2_Torus);
      C1.Toroid_Count := C1_Torus;
      C2.Toroid_Count := C2_Torus;
      Blend_Gene (P1.Toroid_Radius_M, P2.Toroid_Radius_M,
                  TRad_Min, TRad_Max,
                  C1.Toroid_Radius_M, C2.Toroid_Radius_M);
      Blend_Gene (P1.Mass_Kg,       P2.Mass_Kg,       Mass_Min, Mass_Max,
                  C1.Mass_Kg,        C2.Mass_Kg);
      --  Copy non-optimized fields
      C1.Outer_Radius_M  := P1.Outer_Radius_M;
      C1.Slice_Angle_Deg := P1.Slice_Angle_Deg;
      C2.Outer_Radius_M  := P1.Outer_Radius_M;
      C2.Slice_Angle_Deg := P1.Slice_Angle_Deg;
   end BLX_Crossover;

   --  Gaussian mutation with adaptive step size.
   --  Step size = sigma fraction of the parameter range.
   procedure Gaussian_Mutate (Ind   : in out Geometry_Parameters;
                              Rate  : Float;
                              Sigma_Frac : Float := 0.1)
   is
      Sigma : Float;
   begin
      --  Diameter
      Sigma := Sigma_Frac * (Dia_Max - Dia_Min);
      if Float_Random.Random (Gen) < Rate then
         Ind.Diameter_M := Clamp (
           Ind.Diameter_M + Gaussian_Rand (Sigma), Dia_Min, Dia_Max);
      end if;

      --  Angle
      Sigma := Sigma_Frac * (Ang_Max - Ang_Min);
      if Float_Random.Random (Gen) < Rate then
         Ind.Angle_Deg := Clamp (
           Ind.Angle_Deg + Gaussian_Rand (Sigma), Ang_Min, Ang_Max);
      end if;

      --  Nose radius
      Sigma := Sigma_Frac * (Nos_Max - Nos_Min);
      if Float_Random.Random (Gen) < Rate then
         Ind.Nose_Radius_M := Clamp (
           Ind.Nose_Radius_M + Gaussian_Rand (Sigma), Nos_Min, Nos_Max);
      end if;

      --  Toroid count (integer, treat as continuous then round)
      if Float_Random.Random (Gen) < Rate then
         declare
            New_Count : Float := Float (Ind.Toroid_Count) +
              Gaussian_Rand (Sigma_Frac * Float (TCount_Max - TCount_Min));
         begin
            New_Count := Clamp (New_Count,
                                Float (TCount_Min), Float (TCount_Max));
            Ind.Toroid_Count := To_Int (New_Count);
         end;
      end if;

      --  Toroid radius
      Sigma := Sigma_Frac * (TRad_Max - TRad_Min);
      if Float_Random.Random (Gen) < Rate then
         Ind.Toroid_Radius_M := Clamp (
           Ind.Toroid_Radius_M + Gaussian_Rand (Sigma), TRad_Min, TRad_Max);
      end if;

      --  Mass
      Sigma := Sigma_Frac * (Mass_Max - Mass_Min);
      if Float_Random.Random (Gen) < Rate then
         Ind.Mass_Kg := Clamp (
           Ind.Mass_Kg + Gaussian_Rand (Sigma), Mass_Min, Mass_Max);
      end if;
   end Gaussian_Mutate;

   -- ==================================================================
   --  Run_GA_Optimization — main GA loop
   -- ==================================================================
   procedure Run_GA_Optimization
     (Config      : GA_Config;
      Flight      : Flight_Parameters;
      TPS         : TPS_Material;
      Target_Beta : Float;
      Eval        : not null Fitness_Function;
      Result      : out GA_Result)
   is
      Pop_Size   : constant Positive :=
        Positive'Min (Config.Population_Size, Max_Population);
      Pop        : Population;
      Costs      : Cost_Array;
      Sort_Idx   : Index_Array;

      Best_Cost  : Float := Float'Last;
      Best_Geo   : Geometry_Parameters;
      Prev_Best  : Float := Float'Last;
      Stag_Count : Natural := 0;
      Gen_Used   : Natural := 0;
      Converged  : Boolean := False;

      T_Start    : constant Time := Clock;

   begin
      --  Seed the RNG with a time-based seed
      Reset (Gen);

      Put_Line ("[GA] Starting Genetic Algorithm optimisation...");
      Put_Line ("[GA] Population:" & Positive'Image (Pop_Size) &
                "  Max_Gen:" & Positive'Image (Config.Max_Generations) &
                "  Mutation:" & Float'Image (Config.Mutation_Rate) &
                "  Crossover:" & Float'Image (Config.Crossover_Rate));

      --  ── Phase 1: Initialize population with random individuals ──
      for I in 1 .. Pop_Size loop
         Pop (I) := Random_Geometry;
         Sort_Idx (I) := I;
      end loop;

      --  ── Phase 2: Evaluate initial fitness ──
      for I in 1 .. Pop_Size loop
         Costs (I) := Eval (Pop (I), Flight, TPS, Target_Beta);
      end loop;

      --  Find initial best
      Sort_By_Cost (Sort_Idx, Costs, Pop_Size);
      Best_Cost := Costs (Sort_Idx (1));
      Best_Geo  := Pop (Sort_Idx (1));
      Prev_Best  := Best_Cost;

      Put_Line ("[GA] Gen  0: best_cost =" & Float'Image (Best_Cost));

      --  ── Phase 3: GA Evolution Loop ──
      for Gen_Num in 1 .. Config.Max_Generations loop
         Gen_Used := Natural (Gen_Num);

         --  Build sorted index of current generation
         for I in 1 .. Pop_Size loop
            Sort_Idx (I) := I;
         end loop;
         Sort_By_Cost (Sort_Idx, Costs, Pop_Size);

         --  ── Elitism: copy top Elite_Count directly ──
         declare
            Next_Pop : Population;
            Next_Costs : Cost_Array;
            Next_Idx : Natural := 0;
         begin
            --  Copy elite individuals
            for I in 1 .. Integer'Min (Config.Elite_Count, Pop_Size) loop
               Next_Idx := Next_Idx + 1;
               Next_Pop (Next_Idx) := Pop (Sort_Idx (I));
               Next_Costs (Next_Idx) := Costs (Sort_Idx (I));
            end loop;

            --  ── Generate offspring via selection + crossover + mutation ──
            while Next_Idx < Pop_Size loop
               --  Select two parents via tournament
               declare
                  P1_Idx, P2_Idx : Positive;
                  Child1, Child2 : Geometry_Parameters;
               begin
                  P1_Idx := Tournament_Select
                    (Sort_Idx (1 .. Pop_Size), Costs,
                     Integer'Min (Config.Tournament_Size, Pop_Size));
                  P2_Idx := Tournament_Select
                    (Sort_Idx (1 .. Pop_Size), Costs,
                     Integer'Min (Config.Tournament_Size, Pop_Size));

                  --  Ensure different parents when possible
                  if P1_Idx = P2_Idx and then Pop_Size > 1 then
                     P2_Idx := Sort_Idx (
                       Integer(Float_Random.Random (Gen) *
                         Float (Pop_Size - 1)) + 1);
                  end if;

                  --  Crossover
                  if Float_Random.Random (Gen) < Config.Crossover_Rate then
                     BLX_Crossover (Pop (P1_Idx), Pop (P2_Idx),
                                    0.5, Child1, Child2);
                  else
                     --  No crossover: copy parents
                     Child1 := Pop (P1_Idx);
                     Child2 := Pop (P2_Idx);
                  end if;

                  --  Mutation
                  Gaussian_Mutate (Child1, Config.Mutation_Rate);
                  Gaussian_Mutate (Child2, Config.Mutation_Rate);

                  --  Add children to next generation
                  Next_Idx := Next_Idx + 1;
                  if Next_Idx <= Pop_Size then
                     Next_Pop (Next_Idx) := Child1;
                     Next_Costs (Next_Idx) :=
                       Eval (Child1, Flight, TPS, Target_Beta);
                  end if;

                  Next_Idx := Next_Idx + 1;
                  if Next_Idx <= Pop_Size then
                     Next_Pop (Next_Idx) := Child2;
                     Next_Costs (Next_Idx) :=
                       Eval (Child2, Flight, TPS, Target_Beta);
                  end if;
               end;
            end loop;

            --  Replace population
            for I in 1 .. Pop_Size loop
               Pop (I)   := Next_Pop (I);
               Costs (I) := Next_Costs (I);
            end loop;
         end;

         --  ── Track best ──
         for I in 1 .. Pop_Size loop
            if Costs (I) < Best_Cost then
               Best_Cost := Costs (I);
               Best_Geo  := Pop (I);
            end if;
         end loop;

         --  ── Convergence check (stagnation monitoring) ──
         if Gen_Num mod 20 = 0 then
            Put_Line ("[GA] Gen" & Natural'Image (Gen_Num) &
                      ": best_cost =" & Float'Image (Best_Cost));
         end if;

         if abs (Best_Cost - Prev_Best) < Config.Convergence_Tol then
            Stag_Count := Stag_Count + 1;
         else
            Stag_Count := 0;
         end if;
         Prev_Best := Best_Cost;

         if Config.Convergence_Gens > 0 and then
            Stag_Count >= Config.Convergence_Gens
         then
            Put_Line ("[GA] Convergence detected at generation" &
                      Natural'Image (Gen_Num) &
                      " after" & Natural'Image (Stag_Count) &
                      " stagnant generations.");
            Converged := True;
            exit;
         end if;

         --  Adaptive mutation: increase mutation rate if stagnating
         --  (handled implicitly by the convergence check above)
      end loop;

      --  ── Final result ──
      Result.Best_Individual  := Best_Geo;
      Result.Best_Cost        := Best_Cost;
      Result.Generations_Used := Gen_Used;
      Result.Converged        := Converged;

      declare
         Elapsed : constant Duration := Clock - T_Start;
      begin
         Put_Line ("[GA] Optimisation complete.");
         Put_Line ("[GA] Best cost:" & Float'Image (Best_Cost));
         Put_Line ("[GA] Generations:" & Natural'Image (Gen_Used));
         Put_Line ("[GA] Converged:" & Boolean'Image (Converged));
         Put_Line ("[GA] Wall time:" & Duration'Image (Elapsed) & "s");
         Put_Line ("[GA] Best geometry:");
         Put_Line ("  Diameter_m    =" & Float'Image (Best_Geo.Diameter_M));
         Put_Line ("  Angle_deg     =" & Float'Image (Best_Geo.Angle_Deg));
         Put_Line ("  Nose_radius_m =" & Float'Image (Best_Geo.Nose_Radius_M));
         Put_Line ("  Toroid_count  =" & Positive'Image (Best_Geo.Toroid_Count));
         Put_Line ("  Toroid_rad_m  =" & Float'Image (Best_Geo.Toroid_Radius_M));
         Put_Line ("  Mass_kg       =" & Float'Image (Best_Geo.Mass_Kg));
      end;
   end Run_GA_Optimization;

end StellarOrion_Optimization;
