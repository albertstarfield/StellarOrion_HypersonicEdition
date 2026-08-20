--  StellarOrion_HypersonicEdition — Aerothermodynamic Physics (Body)
--  Ada 2012 / SPARK 2014
--
--  All constants are imported from StellarOrion_Types.
--  Functions are pure and side-effect free.

package body StellarOrion_Physics is
   pragma SPARK_Mode (On);

   -- ==================================================================
   --  SPARK-safe square root (Newton-Raphson, 25 iterations)
   --  Required because Ada.Numerics.Elementary_Functions is not
   --  available in SPARK 2014 mode.
   --  Initial guess X/2 requires ~25 iterations to converge for
   --  Float values up to ~1e14 (used in Radiative_Eq_Temp where
   --  Sqrt(Sqrt(q/(sigma*eps))) needs accurate 4th root).
   -- ==================================================================
   function Sqrt (X : Float) return Float is
      Y     : Float;
      Y_New : Float;
   begin
      if X <= 0.0 then
         return 0.0;
      end if;
      Y := X / 2.0;  -- initial guess
      for I in 1 .. 25 loop
         pragma Unreferenced (I);
         Y_New := (Y + X / Y) / 2.0;
         Y     := Y_New;
      end loop;
      return Y;
   end Sqrt;

   -- ==================================================================
   --  Mean_Free_Path
   -- ==================================================================
   --  lambda = 1 / (sqrt(2) * pi * d^2 * n)
   --  Bird 1994, Eq. (1.32)
   function Mean_Free_Path
     (Number_Density : Float;
      Mol_Diameter   : Float) return Float
   is
      Sqrt_2 : constant Float := 1.4142135623730951;
      Pi     : constant Float := 3.141592653589793;
      Denom  : Float;
   begin
      --  Guard: avoid division by zero if number density or diameter is zero
      if Number_Density <= 0.0 or Mol_Diameter <= 0.0 then
         return Float'Last;
      end if;
      Denom := Sqrt_2 * Pi * (Mol_Diameter ** 2) * Number_Density;
      if Denom <= 0.0 then
         return Float'Last;
      end if;
      return 1.0 / Denom;
   end Mean_Free_Path;

   -- ==================================================================
   --  Knudsen_Number
   -- ==================================================================
   --  Kn = lambda / L    (Bird 1994, Sec. 1.4)
   function Knudsen_Number
     (MFP         : Float;
      Char_Length : Float) return Float
   is
   begin
      if Char_Length <= 0.0 then
         return Float'Last;
      end if;
      return MFP / Char_Length;
   end Knudsen_Number;

   -- ==================================================================
   --  Dynamic_Pressure
   -- ==================================================================
   --  q = 0.5 * rho * V^2
   function Dynamic_Pressure
     (Density  : Float;
      Velocity : Float) return Float
   is
   begin
      return 0.5 * Density * (Velocity ** 2);
   end Dynamic_Pressure;

   -- ==================================================================
   --  Ballistic_Coefficient
   -- ==================================================================
   --  beta = m * q / F_drag
   function Ballistic_Coefficient
     (Mass         : Float;
      Dyn_Pressure : Float;
      Drag_Force   : Float) return Float
   is
   begin
      if abs Drag_Force < 1.0e-30 then
         return Float'Last;
      end if;
      return (Mass * Dyn_Pressure) / Drag_Force;
   end Ballistic_Coefficient;

   -- ==================================================================
   --  Sutton_Graves_Heat
   -- ==================================================================
   --  q_stag = C_sg * sqrt(rho / R_n) * V^3
   --  Source: NASA TR R-376 (Sutton & Graves, 1972)
   function Sutton_Graves_Heat
     (Density     : Float;
      Nose_Radius : Float;
      Velocity    : Float) return Float
   is
   begin
      if Nose_Radius <= 0.0 or Density <= 0.0 then
         return 0.0;
      end if;
      return C_SG * Sqrt (Density / Nose_Radius) * (Velocity ** 3);
   end Sutton_Graves_Heat;

   -- ==================================================================
   --  Radiative_Eq_Temp
   -- ==================================================================
   --  T = (q / (sigma * epsilon))^(1/4)
   --  Source: Stefan-Boltzmann law
   function Radiative_Eq_Temp
     (Heat_Flux  : Float;
      Emissivity : Float) return Float
   is
      Denom : Float;
   begin
      Denom := SIGMA_BOLTZMANN * Emissivity;
      if Denom <= 0.0 or Heat_Flux < 0.0 then
         return 0.0;
      end if;
      return Sqrt (Sqrt (Heat_Flux / Denom));
   end Radiative_Eq_Temp;

   -- ==================================================================
   --  Backface_Temperature
   -- ==================================================================
   --  T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
   --  Source: Anderson 2006; Rapisarda 2023 Sec 5.5
   --  eta_lag is the thermal-lag efficiency factor (typically 0.15)
   function Backface_Temperature
     (Init_Temp     : Float;
      Heat_Flux     : Float;
      Duration      : Float;
      Thermal_Lag   : Float;
      TPS_Density   : Float;
      TPS_Cp        : Float;
      TPS_Thickness : Float) return Float
   is
      Thermal_Capacitance : Float;
   begin
      Thermal_Capacitance := TPS_Density * TPS_Cp * TPS_Thickness;
      if Thermal_Capacitance <= 0.0 then
         return Init_Temp;
      end if;
      return Init_Temp
        + (Heat_Flux * Duration * Thermal_Lag) / Thermal_Capacitance;
   end Backface_Temperature;

   -- ==================================================================
   --  Deceleration_G_Load
   -- ==================================================================
   --  n = F_drag / (m * g0)
   function Deceleration_G_Load
     (Drag_Force : Float;
      Mass       : Float) return Float
   is
   begin
      if Mass <= 0.0 then
         return 0.0;
      end if;
      return Drag_Force / (Mass * G0);
   end Deceleration_G_Load;

   -- ==================================================================
   --  Density_From_Number
   -- ==================================================================
   --  rho = n * M_air / N_A
   function Density_From_Number
     (N_Number : Float) return Float
   is
   begin
      return N_Number * M_AIR / N_AVOGADRO;
   end Density_From_Number;

   -- ==================================================================
   --  Is_Survivable
   -- ==================================================================
   --  True iff every metric is within material survivability limits.
   function Is_Survivable
     (Metrics : Flight_Metrics) return Boolean
   is
   begin
      return
        --  Surface temperature must stay below SiC limit
        Metrics.Surface_Temp_K <= SIC_MAX_TEMP
        --  Backface must stay below Kapton limit
        and Metrics.Backface_Temp_K <= KAPTON_MAX_TEMP
        --  Structural g-load must be within limits
        and Metrics.G_Load <= MAX_G_LOAD
        --  Deceleration g must be within limits
        and Metrics.Decel_G <= MAX_G_LOAD;
   end Is_Survivable;

   -- ==================================================================
   --  Calculate_Flight_Metrics
   -- ==================================================================
   --  Composite procedure: from raw SPARTA output + flight/geometry/TPS
   --  cards, compute all derived engineering metrics.
   procedure Calculate_Flight_Metrics
     (Results : Simulation_Results;
      Flight  : Flight_Parameters;
      Geo     : Geometry_Parameters;
      TPS     : TPS_Material;
      Metrics : out Flight_Metrics)
   is
      Dyn_Q      : Float;
      Number_Den : Float;
      MFP        : Float;
      Stag_Q     : Float;
   begin
      --  1. Dynamic pressure
      Dyn_Q := Dynamic_Pressure (Flight.Density_Kgm3, Flight.Velocity_Ms);

      --  2. Ballistic coefficient  beta = m * q / F_drag
      Metrics.Ballistic_Coeff :=
        Ballistic_Coefficient (Geo.Mass_Kg, Dyn_Q, Results.Drag_Force);

      --  3. Number density  n = rho * N_A / M_air
      Number_Den := Flight.Density_Kgm3 * N_AVOGADRO / M_AIR;

      --  4. Mean free path & Knudsen number
      MFP := Mean_Free_Path (Number_Den, MOL_DIAM);
      Metrics.Knudsen_Number := Knudsen_Number (MFP, Geo.Diameter_M);

      --  5. Stagnation heat flux  (Sutton-Graves correlation)
      --  Also accept SPARTA-reported value if non-zero
      Stag_Q := Results.Heat_Flux_Wm2;
      if Stag_Q <= 0.0 then
         Stag_Q := Sutton_Graves_Heat
           (Flight.Density_Kgm3, Geo.Nose_Radius_M, Flight.Velocity_Ms);
      end if;
      Metrics.Stag_Heat_Flux_Wm2 := Stag_Q;
      Metrics.Stag_Heat_Flux_Wcm2 := Stag_Q / 1.0e4;

      --  6. Radiative equilibrium surface temperature
      Metrics.Surface_Temp_K :=
        Radiative_Eq_Temp (Stag_Q, TPS.Emissivity);

      --  7. Backface temperature  (1-D transient estimate)
      --  Using a 60 s pulse as baseline reference trajectory duration
      Metrics.Backface_Temp_K := Backface_Temperature
        (Init_Temp     => 300.0,   -- ambient initial [K]
         Heat_Flux     => Stag_Q,
         Duration      => 60.0,    -- reference heat-pulse duration [s]
         Thermal_Lag   => 0.15,    -- typical lag efficiency
         TPS_Density   => TPS.Density,
         TPS_Cp        => TPS.Cp,
         TPS_Thickness => TPS.Thickness);

      --  8. Deceleration g-load
      Metrics.Decel_G :=
        Deceleration_G_Load (Results.Drag_Force, Geo.Mass_Kg);
      Metrics.G_Load := Metrics.Decel_G;  -- instantaneous = sustained here

      --  9. Survivability verdict
      Metrics.Survivable := Is_Survivable (Metrics);
   end Calculate_Flight_Metrics;

end StellarOrion_Physics;
