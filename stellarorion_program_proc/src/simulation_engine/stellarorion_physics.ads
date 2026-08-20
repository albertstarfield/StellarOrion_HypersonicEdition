--  StellarOrion_HypersonicEdition — Aerothermodynamic Physics
--  Ada 2012 / SPARK 2014
--  Pure-math routines with no side effects.
--
--  Citations are given inline per function.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Physics is
   pragma SPARK_Mode (On);

   -- -----------------------------------------------------------------
   --  Rarefied Gas Dynamics
   -- -----------------------------------------------------------------

   --  Mean free path [m].
   --  lambda = 1 / (sqrt(2) * pi * d^2 * n)
   --  Source: Bird 1994, Eq. (1.32)
   --  Physical constraint: number density and molecular diameter must be
   --  positive for the formula to be meaningful (non-colliding gas at
   --  zero density has infinite mean free path).
   function Mean_Free_Path
     (Number_Density : Float;
      Mol_Diameter   : Float) return Float
     with Pre  => Number_Density > 0.0 and Mol_Diameter > 0.0,
          Post => Mean_Free_Path'Result >= 0.0;

   --  Knudsen number (dimensionless).
   --  Kn = lambda / L
   --  Source: Bird 1994, Sec. 1.4
   --  MFP is non-negative (physical mean free path); Char_Length must
   --  be positive (characteristic length of the body, e.g. diameter).
   function Knudsen_Number
     (MFP         : Float;
      Char_Length : Float) return Float
     with Pre  => MFP >= 0.0 and Char_Length > 0.0,
          Post => Knudsen_Number'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Aerodynamics
   -- -----------------------------------------------------------------

   --  Dynamic pressure [Pa].
   --  q = 0.5 * rho * V^2
   --  Density and velocity are non-negative physical quantities.
   function Dynamic_Pressure
     (Density  : Float;
      Velocity : Float) return Float
     with Pre  => Density >= 0.0 and Velocity >= 0.0,
          Post => Dynamic_Pressure'Result >= 0.0;

   --  Ballistic coefficient [kg/m^2].
   --  beta = m * q / F_drag
   --  Mass, dynamic pressure, and drag force must be positive for a
   --  physically meaningful ballistic coefficient (non-zero drag needed).
   function Ballistic_Coefficient
     (Mass       : Float;
      Dyn_Pressure : Float;
      Drag_Force : Float) return Float
     with Pre  => Mass > 0.0 and Dyn_Pressure >= 0.0 and Drag_Force > 0.0,
          Post => Ballistic_Coefficient'Result > 0.0;

   -- -----------------------------------------------------------------
   --  Aerothermodynamics
   -- -----------------------------------------------------------------

   --  Sutton-Graves stagnation-point convective heat flux [W/m^2].
   --  q_stag = C_sg * sqrt(rho / R_n) * V^3
   --  Source: NASA TR R-376 (Sutton & Graves, 1972)
   --  Density must be non-negative; nose radius and velocity positive
   --  for the square-root and cubic terms to be physically meaningful.
   function Sutton_Graves_Heat
     (Density    : Float;
      Nose_Radius : Float;
      Velocity   : Float) return Float
     with Pre  => Density >= 0.0 and Nose_Radius > 0.0 and Velocity >= 0.0,
          Post => Sutton_Graves_Heat'Result >= 0.0;

   --  Radiative equilibrium surface temperature [K].
   --  T = (q / (sigma * epsilon))^(1/4)
   --  Source: Stefan-Boltzmann law
   --  Heat flux must be non-negative; emissivity must be positive
   --  (zero emissivity is a black-body singularity).
   function Radiative_Eq_Temp
     (Heat_Flux  : Float;
      Emissivity : Float) return Float
     with Pre  => Heat_Flux >= 0.0 and Emissivity > 0.0,
          Post => Radiative_Eq_Temp'Result >= 0.0;

   --  1-D transient backface temperature [K].
   --  T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
   --  Source: Anderson 2006; Rapisarda 2023 Sec 5.5
   --  eta_lag (thermal lag efficiency) typically ~0.15
   --  All TPS properties must be positive; heat flux and duration
   --  non-negative for a physically meaningful backface estimate.
   function Backface_Temperature
     (Init_Temp    : Float;
      Heat_Flux    : Float;
      Duration     : Float;
      Thermal_Lag  : Float;
      TPS_Density  : Float;
      TPS_Cp       : Float;
      TPS_Thickness : Float) return Float
     with Pre  => Init_Temp >= 0.0
                  and Heat_Flux >= 0.0
                  and Duration >= 0.0
                  and Thermal_Lag > 0.0
                  and TPS_Density > 0.0
                  and TPS_Cp > 0.0
                  and TPS_Thickness > 0.0,
          Post => Backface_Temperature'Result >= 0.0;

   --  Deceleration in Earth g's.
   --  n = F_drag / (m * g0)
   --  Drag force is non-negative; mass must be positive to avoid
   --  division by zero and produce a meaningful g-load.
   function Deceleration_G_Load
     (Drag_Force : Float;
      Mass       : Float) return Float
     with Pre  => Drag_Force >= 0.0 and Mass > 0.0,
          Post => Deceleration_G_Load'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Density / Number-Density Conversion
   -- -----------------------------------------------------------------

   --  Mass density from number density [kg/m^3].
   --  rho = n * M_air / N_A
   --  Number density must be non-negative for a physical density.
   function Density_From_Number
     (N_Number : Float) return Float
     with Pre  => N_Number >= 0.0,
          Post => Density_From_Number'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Survivability
   -- -----------------------------------------------------------------

   --  Returns True iff every metric is within material limits.
   function Is_Survivable
     (Metrics : Flight_Metrics) return Boolean;

   -- -----------------------------------------------------------------
   --  Composite Calculation
   -- -----------------------------------------------------------------

   --  Compute all Flight_Metrics from raw simulation results,
   --  flight conditions, geometry, and TPS material card.
   --  The procedure aggregates all physics functions above into
   --  a single comprehensive metric calculation.
   procedure Calculate_Flight_Metrics
     (Results : Simulation_Results;
      Flight  : Flight_Parameters;
      Geo     : Geometry_Parameters;
      TPS     : TPS_Material;
      Metrics : out Flight_Metrics);

end StellarOrion_Physics;
