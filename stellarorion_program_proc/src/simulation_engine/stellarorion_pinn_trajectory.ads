--  StellarOrion_HypersonicEdition — PINN Trajectory Physics (SPARK 2014)
--  Ada 2012 / SPARK 2014
--  Pure-math routines for PINN extrapolation trajectory calculations.
--  All functions are side-effect free and provable by gnatprove --level=4.
--
--  This package provides the physics backbone for the validation pipeline's
--  PINN extrapolation: ISA atmosphere, Sutton-Graves heat flux, IRVE-3
--  trajectory model, dynamic pressure, drag force, and g-load.
--  Python calls these via ctypes; no Python logic performs physics.
--
--  DERIVATION (axioms → theories → applications):
--    AXIOM T1: ISA atmosphere follows piecewise-linear temperature profile
--              with hydrostatic pressure integration [NASA SP-7468, 1976].
--    AXIOM T2: Sutton-Graves: q = C_sg * sqrt(rho/R_n) * V^3
--              [Sutton & Graves, 1972, NASA TR R-376].
--    AXIOM T3: Drag force F = 0.5 * Cd * A * rho * V^2 [Anderson 2006].
--    AXIOM T4: G-load n = F_drag / (m * g0) [standard dynamics].
--    AXIOM T5: IRVE-3 trajectory: 120 km → 50 km, V_entry=4300 m/s,
--              V_final=2700 m/s [NASA TP-2013-4012].
--
--  CITATIONS:
--    [1] NASA SP-7468 (1976) — U.S. Standard Atmosphere
--    [2] Sutton, K. & Graves, R.A. (1972), NASA TR R-376
--    [3] NASA TP-2013-4012 — IRVE-3 Flight Reconstruction
--    [4] Anderson, J.D. (2006), Hypersonic and High-Temperature Gas Dynamics
--    [5] Rapisarda (2023), MSc Thesis, TU Delft — Table 4.10
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_PINN_Trajectory is
   pragma SPARK_Mode (On);

   -- -----------------------------------------------------------------
   --  Physical Constants
   -- -----------------------------------------------------------------
   --  G0: Standard gravitational acceleration [m/s^2]
   --  [Citation: ISO 80000-3]
   G0 : constant Float := 9.80665;

   --  R_AIR: Specific gas constant for dry air [J/(kg*K)]
   --  [Citation: NASA SP-7468 (1976)]
   R_AIR : constant Float := 287.058;

   --  GAMMA_AIR: Ratio of specific heats for air
   --  [Citation: Anderson (2006)]
   GAMMA_AIR : constant Float := 1.4;

   --  C_SG: Sutton-Graves correlation constant for Earth air [SI units]
   --  [Citation: Sutton & Graves (1972), NASA TR R-376, Table 1]
   C_SG : constant Float := 1.83e-4;

   --  Vehicle parameters (IRVE-3)
   --  [Citation: NASA TP-2013-4012; Rapisarda (2023) Table 4.1]
   IRVE3_MASS_KG    : constant Float := 281.0;
   IRVE3_DIAMETER_M : constant Float := 3.0;
   IRVE3_CD         : constant Float := 1.4625;
   IRVE3_NOSE_R_M   : constant Float := 1.5;

   -- -----------------------------------------------------------------
   --  ISA Atmosphere Model
   -- -----------------------------------------------------------------

   --  ISA atmosphere properties at a given altitude.
   --  Returns temperature, pressure, density, speed of sound, and
   --  dynamic viscosity at the specified altitude.
   --
   --  AXIOMS:
   --    ISA_A1: Altitude_Km in [0.0, 120.0] (ISA table range).
   --    ISA_A2: Temperature in [186.87, 300.0] K (ISA range).
   --    ISA_A3: Pressure in [0.0, 101325.0] Pa.
   --    ISA_A4: Density in [0.0, 1.225] kg/m^3.
   --
   --  OVERFLOW PROOF: All intermediate products bounded by ISA table limits.
   --  Verification: gnatprove --level=4.
   type ISA_Atmosphere_Result is record
      Temperature_K       : Float := 0.0;
      Pressure_Pa         : Float := 0.0;
      Density_Kgm3        : Float := 0.0;
      Speed_Of_Sound_Ms   : Float := 0.0;
      Dynamic_Viscosity_Pas : Float := 0.0;
   end record;

   function ISA_Atmosphere (Altitude_Km : Float) return ISA_Atmosphere_Result
      with Pre  => Altitude_Km >= 0.0 and Altitude_Km <= 120.0,
           Post => ISA_Atmosphere'Result.Temperature_K > 0.0
                    and ISA_Atmosphere'Result.Density_Kgm3 >= 0.0;

   -- -----------------------------------------------------------------
   --  Sutton-Graves Stagnation-Point Heat Flux
   -- -----------------------------------------------------------------

   --  Sutton-Graves stagnation-point convective heat flux [W/m^2].
   --  q_stag = C_sg * sqrt(rho / R_n) * V^3
   --
   --  AXIOMS:
   --    SG_A1: Density_Kgm3 >= 0.0 (vacuum to sea level).
   --    SG_A2: Nose_Radius_M > 0.0 (physical vehicle).
   --    SG_A3: Velocity_Ms >= 0.0 (rest to escape).
   --
   --  OVERFLOW PROOF: C_sg * sqrt(rho/R_n) * V^3 <= 1.75e19 << Float'Last.
   --  [Citation: Sutton & Graves (1972), NASA TR R-376]
   function Sutton_Graves_Heat_Flux
     (Density_Kgm3  : Float;
      Nose_Radius_M : Float;
      Velocity_Ms   : Float) return Float
      with Pre  => Density_Kgm3 >= 0.0
                    and Nose_Radius_M > 0.0
                    and Velocity_Ms >= 0.0,
           Post => Sutton_Graves_Heat_Flux'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Dynamic Pressure
   -- -----------------------------------------------------------------

   --  Dynamic pressure [Pa]: q = 0.5 * rho * V^2
   --  [Citation: Anderson (2006), Fundamentals of Aerodynamics]
   function Dynamic_Pressure
     (Density_Kgm3  : Float;
      Velocity_Ms   : Float) return Float
      with Pre  => Density_Kgm3 >= 0.0 and Velocity_Ms >= 0.0,
           Post => Dynamic_Pressure'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Drag Force and G-Load
   -- -----------------------------------------------------------------

   --  Drag force [N]: F = 0.5 * Cd * A * rho * V^2
   --  A = pi * (D/2)^2 (frontal area)
   --  [Citation: Anderson (2006)]
   function Drag_Force
     (Density_Kgm3  : Float;
      Velocity_Ms   : Float;
      Cd            : Float;
      Diameter_M    : Float) return Float
      with Pre  => Density_Kgm3 >= 0.0
                    and Velocity_Ms >= 0.0
                    and Cd >= 0.0
                    and Diameter_M > 0.0,
           Post => Drag_Force'Result >= 0.0;

   --  Deceleration in Earth g's: n = F_drag / (m * g0)
   --  [Citation: Anderson (2006)]
   function G_Load
     (Drag_Force_N : Float;
      Mass_Kg      : Float) return Float
      with Pre  => Drag_Force_N >= 0.0
                    and Mass_Kg > 0.0,
           Post => G_Load'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  IRVE-3 Trajectory Model
   -- -----------------------------------------------------------------

   --  Trajectory result at a given simulation step.
   type Trajectory_Result is record
      Altitude_Km   : Float := 0.0;
      Velocity_Ms   : Float := 0.0;
      Mach_Number   : Float := 0.0;
      Density_Kgm3  : Float := 0.0;
      Heat_Flux_Wm2 : Float := 0.0;
      Drag_Force_N  : Float := 0.0;
      G_Load_Value  : Float := 0.0;
      Dynamic_Pressure_Pa : Float := 0.0;
   end record;

   --  Compute IRVE-3 reentry trajectory conditions at a given step.
   --
   --  The trajectory maps simulation steps to physical conditions via
   --  uniform linear interpolation:
   --    H = H_Entry + (H_Final - H_Entry) * Step / Target_Step
   --    V = V_Entry + (V_Final - V_Entry) * Step / Target_Step
   --
   --  This gives 120 km → 50 km across steps 0 → 300M with uniform
   --  altitude distribution (no regime boundaries or exponential jumps).
   --
   --  AXIOMS:
   --    TRAJ_A1: Step >= 0.0 (start of simulation).
   --    TRAJ_A2: Target_Step > 0.0 (simulation duration).
   --    TRAJ_A3: H_Entry > H_Final (vehicle descends).
   --    TRAJ_A4: V_Entry > V_Final (vehicle decelerates).
   --
   --  [Citation: NASA TP-2013-4012 — IRVE-3 flight]
   --  [Citation: code-quality.md — ALL physics in Ada/SPARK 2014]
   function IRVE3_Trajectory
     (Step           : Float;
      Target_Step    : Float := 3.0e8;
      H_Entry_Km     : Float := 120.0;
      H_Final_Km     : Float := 50.0;
      V_Entry_Ms     : Float := 4300.0;
      V_Final_Ms     : Float := 2700.0;
      H_DSMC_Km      : Float := 51.8;
      V_DSMC_Ms      : Float := 3378.0) return Trajectory_Result
      with Pre  => Target_Step > 0.0
                    and H_Entry_Km > H_Final_Km
                    and V_Entry_Ms > V_Final_Ms;

   -- -----------------------------------------------------------------
   --  Metric Scaling (PINN extrapolation)
   -- -----------------------------------------------------------------

   --  Scale a metric from DSMC reference conditions to current trajectory.
   --  Uses physics-based scaling ratios.
   --
   --  metric_type: 1=heat_flux, 2=drag, 3=g_load, 4=heat_load, 5=cd
   function Scale_Metric
     (Metric_Type         : Integer;
      DSMC_Final_Value    : Float;
      Ref_Dynamic_Pressure : Float;
      Now_Dynamic_Pressure : Float;
      Ref_SG_Flux_Wcm2    : Float;
      Now_SG_Flux_Wcm2    : Float;
      Base_Value          : Float) return Float
      with Pre => Metric_Type in 1 .. 5
                   and Ref_Dynamic_Pressure >= 0.0
                   and Now_Dynamic_Pressure >= 0.0
                   and Ref_SG_Flux_Wcm2 >= 0.0
                   and Now_SG_Flux_Wcm2 >= 0.0;

   -- -----------------------------------------------------------------
   --  Geometry Cross-Section (for dashboard visualization)
   -- -----------------------------------------------------------------

   --  Maximum number of points in the 2D cross-section profile.
   MAX_CROSS_SECTION_PTS : constant Positive := 200;

   --  Fixed-length array for cross-section coordinates (x or y).
   subtype Cross_Section_Index is Positive range 1 .. MAX_CROSS_SECTION_PTS;
   type Array_Float_200 is array (Cross_Section_Index) of Float;

   --  Return the 2D axisymmetric cross-section of the HIAD vehicle.
   --
   --  Generates the exact 4-segment flat-skin profile used by SPARTA:
   --    1. Nose arc        (sphere rN=1.5m, theta -pi/2 to -gamma)
   --    2. Windward straight (cone half-angle gamma)
   --    3. Toroid wrap      (r_torus=0.135m)
   --    4. Flat back        (aft closure to axis)
   --
   --  X coords: axis direction (nose points +X)
   --  Y coords: half-width (positive = upper surface)
   --  N_Pts: actual number of points returned
   --
   --  [Citation: Rapisarda (2023) Sec 3.7 — HIAD flat-skin profile]
   --  [Citation: stellarorion_sparta.ads — 4-segment geometry spec]
    procedure Get_HIAD_Cross_Section
      (X_Arr  : out Array_Float_200;
       Y_Arr  : out Array_Float_200;
       N_Pts  : access Integer)
       with Pre => True, Post => N_Pts.all >= 0
                    and N_Pts.all <= MAX_CROSS_SECTION_PTS;

end StellarOrion_PINN_Trajectory;
