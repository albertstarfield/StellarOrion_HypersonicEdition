--  StellarOrion_HypersonicEdition — Trajectory Output Frame Data (Spec)
--  Ada 2012 / SPARK 2014
--  Converts the computational math from generate_outputs.py._compute_frame_data
--  to Ada. The rendering stays in Python.
--
--  AXIOMS:
--    AXIOM F1: IRVE-3 trajectory is linear in step space:
--              H = 120.0 - 80.0 * Step / 300M (km),
--              V = 4300.0 - 1600.0 * Step / 300M (m/s).
--    AXIOM F2: Ballistic coefficient beta = m / (Cd * A_ref),
--              A_ref = pi * (D/2)^2.
--    AXIOM F3: Stagnation pressure P_stag = P_amb + 0.5 * rho * V^2.
--    AXIOM F4: PINN metrics model training convergence:
--              loss decays as 1/(1+100*progress),
--              accuracy improves toward 99.5%,
--              DSMC-PINN error decreases from 15% to 0.5%.
--    AXIOM F5: Knudsen number Kn = lambda / L_char, where lambda is the
--              mean free path from ISA atmosphere and L_char is vehicle
--              characteristic length (3.0 m for IRVE-3).
--
--  THEOREMS:
--    T1: All physics delegate to verified SPARK routines in
--        StellarOrion_PINN_Trajectory and StellarOrion_Physics.
--    T2: Frame_Data record captures every field from the Python
--        _compute_frame_data() output dict.
--
--  APPLICATIONS:
--    A1: Compute_Frame_Data is the Ada equivalent of Python's
--        _compute_frame_data() -- pure computation, no I/O.
--    A2: Python rendering reads Frame_Data fields via ctypes FFI.
--
--  CITATIONS:
--    [1] NASA TP-2013-4012 -- IRVE-3 flight trajectory
--    [2] Sutton & Graves (1972), NASA TR R-376
--    [3] Anderson (2006), Hypersonic Gas Dynamics
--    [4] Bird (1994), Molecular Gas Dynamics -- Knudsen number
--    [5] DeepXDE docs -- PINN training metrics
--
--  Author: Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Trajectory_Output is
   pragma SPARK_Mode (On);

   -- -----------------------------------------------------------------
   --  Constants
   -- -----------------------------------------------------------------
   --  TARGET_STEP: Total simulation steps (300M).
   --  [Citation: NASA TP-2013-4012 -- IRVE-3 trajectory]
   TARGET_STEP : constant Float := 3.0e8;

   --  CHAR_LENGTH_M: Vehicle characteristic length for Knudsen number [m].
   --  IRVE-3 aeroshell diameter.
   --  [Citation: NASA TP-2013-4012]
   CHAR_LENGTH_M : constant Float := 3.0;

   -- -----------------------------------------------------------------
   --  Trajectory_Point Record
   -- -----------------------------------------------------------------
   --  Trajectory-only data at a single simulation step.
   --  Subset of Frame_Data for callers that need only kinematics.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Step        : Simulation step index [dimensionless].
   --    Altitude_Km : Geodetic altitude [km] (120 -> 50).
   --    Velocity_Ms : True airspeed [m/s] (4300 -> 2700).
   --    Mach_Number : Ratio V / a (local speed of sound).
   --
   --  SOURCE: NASA TP-2013-4012; Rapisarda (2023) Table 4.1.
   type Trajectory_Point is record
      Step        : Float := 0.0;
      Altitude_Km : Float := 0.0;
      Velocity_Ms : Float := 0.0;
      Mach_Number : Float := 0.0;
   end record;

   -- -----------------------------------------------------------------
   --  Frame_Data Record
   -- -----------------------------------------------------------------
   --  All trajectory, physics, and PINN metrics for one simulation step.
   --  Mirrors the Python dict returned by _compute_frame_data().
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Step                  : Simulation step index [dimensionless].
   --    Altitude_Km           : Geodetic altitude [km] (120 -> 50).
   --    Velocity_Ms           : True airspeed [m/s] (4300 -> 2700).
   --    Mach_Number           : Ratio V / a (local speed of sound).
   --    Heat_Flux_Wcm2        : Sutton-Graves stagnation heat flux [W/cm^2].
   --    Drag_Force_N          : Aerodynamic drag [N].
   --    G_Load                : Deceleration in g's [g].
   --    Dynamic_Pressure_Pa   : Dynamic pressure q = 0.5*rho*V^2 [Pa].
   --    Density_Kgm3          : Ambient ISA density [kg/m^3].
   --    Temperature_K         : Ambient ISA temperature [K].
   --    Pressure_Pa           : Ambient ISA pressure [Pa].
   --    PINN_Loss             : Simulated PINN training loss [dimensionless].
   --    PINN_Accuracy         : Simulated PINN accuracy [%].
   --    DSMC_PINN_Error       : DSMC vs PINN discrepancy [%].
   --    Knudsen_Number        : Rarefaction parameter Kn = lambda/L [-].
   --    Ballistic_Coeff_Kgm2  : Ballistic coefficient beta [kg/m^2].
   --    Stagnation_Pressure_Pa: Stagnation pressure P_stag [Pa].
   --
   --  DEFAULTS: All fields initialized to 0.0 for safe construction.
   --
   --  SOURCE: Python generate_outputs.py _compute_frame_data().
   type Frame_Data is record
      Step                  : Float := 0.0;
      Altitude_Km           : Float := 0.0;
      Velocity_Ms           : Float := 0.0;
      Mach_Number           : Float := 0.0;
      Heat_Flux_Wcm2        : Float := 0.0;
      Drag_Force_N          : Float := 0.0;
      G_Load                : Float := 0.0;
      Dynamic_Pressure_Pa   : Float := 0.0;
      Density_Kgm3          : Float := 0.0;
      Temperature_K         : Float := 0.0;
      Pressure_Pa           : Float := 0.0;
      PINN_Loss             : Float := 0.0;
      PINN_Accuracy         : Float := 0.0;
      DSMC_PINN_Error       : Float := 0.0;
      Knudsen_Number        : Float := 0.0;
      Ballistic_Coeff_Kgm2  : Float := 0.0;
      Stagnation_Pressure_Pa: Float := 0.0;
   end record;

   -- -----------------------------------------------------------------
   --  Compute_Trajectory_Point
   -- -----------------------------------------------------------------
   --  Compute trajectory-only data (altitude, velocity, Mach) at a step.
   --  Lightweight alternative to Compute_Frame_Data for kinematic-only
   --  callers.
   --
   --  AXIOMS:
   --    TP1: Step >= 0.0 (start of simulation).
   --    TP2: TARGET_STEP > 0.0 (normalization divisor).
   --
   --  THEOREMS:
   --    T1: Altitude decreases monotonically: H(0) = 120, H(300M) = 40.
   --    T2: Velocity decreases monotonically: V(0) = 4300, V(300M) = 2700.
   --
   --  [Citation: NASA TP-2013-4012 -- IRVE-3 trajectory]
   function Compute_Trajectory_Point (Step : Float) return Trajectory_Point
      with Pre => Step >= 0.0;

   -- -----------------------------------------------------------------
   --  Compute_Frame_Data
   -- -----------------------------------------------------------------
   --  Compute all trajectory + physics + PINN metrics for one frame step.
   --  Ada equivalent of Python's _compute_frame_data(step) function.
   --
   --  AXIOMS:
   --    CF1: Step >= 0.0 (start of simulation).
   --    CF2: TARGET_STEP > 0.0 (normalization divisor).
   --    CF3: All physics delegate to SPARK-verified functions.
   --
   --  THEOREMS:
   --    T1: Altitude decreases monotonically: H(0) = 120 km, H(300M) = 40 km.
   --    T2: Velocity decreases monotonically: V(0) = 4300 m/s, V(300M) = 2700 m/s.
   --    T3: PINN loss is bounded in (0, 1.0].
   --    T4: PINN accuracy is bounded in [85.0, 99.5].
   --    T5: DSMC-PINN error is bounded in [0.5, 15.0].
   --
   --  [Citation: NASA TP-2013-4012 -- IRVE-3 trajectory]
   --  [Citation: Sutton & Graves (1972), NASA TR R-376]
   --  [Citation: Anderson (2006), Hypersonic Gas Dynamics]
   --  [Citation: Bird (1994), Molecular Gas Dynamics -- Knudsen]
   function Compute_Frame_Data (Step : Float) return Frame_Data
      with Pre  => Step >= 0.0,
           Post => Compute_Frame_Data'Result.PINN_Loss > 0.0
                    and Compute_Frame_Data'Result.PINN_Loss <= 1.0
                    and Compute_Frame_Data'Result.PINN_Accuracy >= 85.0
                    and Compute_Frame_Data'Result.PINN_Accuracy <= 99.5
                    and Compute_Frame_Data'Result.DSMC_PINN_Error >= 0.5
                    and Compute_Frame_Data'Result.DSMC_PINN_Error <= 15.0;

   -- -----------------------------------------------------------------
   --  Self-Test
   -- -----------------------------------------------------------------
   --  Verify Compute_Frame_Data at step=0 and step=TARGET_STEP.
   --  Asserts physical invariants: altitude, velocity, Mach, heat flux,
   --  PINN metrics are within expected ranges.
   --
   --  self-test registry: Register_Routine ("Test_Compute_Frame_Data")
   procedure Test_Compute_Frame_Data
      with Pre => True, Post => True;

end StellarOrion_Trajectory_Output;
