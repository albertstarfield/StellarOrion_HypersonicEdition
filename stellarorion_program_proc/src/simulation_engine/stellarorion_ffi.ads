-- =============================================================================
-- StellarOrion_FFI — C-Compatible Foreign Function Interface Layer
-- =============================================================================
-- AXIOMS:
--   1. The Ada runtime uses IEEE 754 double-precision floats, which map
--      directly to C's `double` via Interfaces.C.Double.
--   2. C callers cannot manage Ada memory; all outputs are returned through
--      pointer parameters (out-parameters as access types).
--   3. Each exported function is a thin wrapper that converts between C types
--      and Ada types, then delegates to StellarOrion_Optimization.
--   4. The shared library must export C-linkage symbols so that ctypes/cffi
--      in Python can resolve them by name via dlsym/dlopen.
--
-- THEOREMS:
--   1. Since Interfaces.C.Double is defined as Standard.Long_Float which is
--      IEEE 754 binary64, no precision loss occurs in type conversion.
--   2. Interfaces.C.int is a 32-bit signed integer, sufficient for Max_Iter
--      values up to 2^31 - 1 and Boolean-as-int encoding (0/1).
--   3. All pointer outputs are validated non-null by the caller contract;
--      dereferencing is safe under the precondition checks.
--
-- CITATIONS:
--   [Ada2012]  ISO/IEC 8652:2012 — Ada Reference Manual, Interfaces.C package.
--   [IEEE754]  IEEE 754-2019 — Standard for Floating-Point Arithmetic.
--   [Ctypes]  Python ctypes documentation —
--              https://docs.python.org/3/library/ctypes.html
--   [dlsym]   Apple dlopen/dlsym man pages (macOS dylib symbol resolution).
--
-- Author: Albert Starfield Wahyu Suryo Samudro
-- =============================================================================

with Interfaces.C;

package StellarOrion_FFI is
   pragma SPARK_Mode (Off);

   -- -------------------------------------------------------------------------
   --  Estimate_Cd_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Estimate_Cd.
   --  Estimates the drag coefficient Cd for a given HIAD geometry.
   --
   --  AXIOMS:
   --    R_N, R_Tor, Half_Cone_Deg are passed as C doubles and converted
   --    to Ada Float for the underlying computation. N_Tori defaults to 6
   --    (IRVE-3 baseline) since the C interface does not expose it.
   --
   --  Parameters:
   --    R_N           — nose sphere radius [m]
   --    R_Tor         — torus minor (tube) radius [m]
   --    Half_Cone_Deg — half-cone angle [degrees]
   --
   --  Returns:
   --    Estimated drag coefficient Cd (> 0.0).
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4.
   -- -------------------------------------------------------------------------
   function Estimate_Cd_C
     (R_N           : Interfaces.C.Double;
      R_Tor         : Interfaces.C.Double;
      Half_Cone_Deg : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Estimate_Cd_C, "Estimate_Cd_C");

   -- -------------------------------------------------------------------------
   --  HIAD_Cost_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.HIAD_Cost_Function.
   --  Evaluates the PINN-inspired cost function for HIAD geometry.
   --
   --  AXIOMS:
   --    The parameter vector X is decomposed into three C doubles (X1, X2, X3)
   --    corresponding to [R_N, r_tor, half_cone_deg]. This flat representation
   --    avoids the need for array marshalling across the FFI boundary.
   --
   --  Parameters:
   --    X1 — nose sphere radius R_N [m]
   --    X2 — torus minor radius r_tor [m]
   --    X3 — half-cone angle [degrees]
   --
   --  Returns:
   --    Cost value J >= 0.0 (Cd + penalty terms).
   --
   --  CITATION:
   --    [Nocedal06] Nocedal & Wright (2006), Numerical Optimization, Sec 17.1.
   -- -------------------------------------------------------------------------
   function HIAD_Cost_C
     (X1 : Interfaces.C.Double;
      X2 : Interfaces.C.Double;
      X3 : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, HIAD_Cost_C, "HIAD_Cost_C");

   -- -------------------------------------------------------------------------
   --  Run_MoP_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Run_MoP_Optimization.
   --  Runs the Method of Projected Gradients optimizer.
   --
   --  AXIOMS:
   --    1. MoP configuration fields are passed as individual C doubles/int
   --       and assembled into a MoP_Config record inside the wrapper.
   --    2. Initial guess is passed as three doubles and assembled into
   --       a Param_Vector.
   --    3. All results are written through output pointer parameters so that
   --       the C caller owns the memory.
   --    4. Boolean is encoded as C int: 1 = True, 0 = False.
   --
   --  Parameters:
   --    Learning_Rate  — gradient descent step size
   --    Tolerance      — convergence tolerance (||grad||_inf)
   --    Lambda_1       — penalty weight for max_radius constraint
   --    Lambda_2       — penalty weight for nose_radius constraint
   --    Max_Iter       — maximum number of iterations
   --    X1, X2, X3     — initial parameter guess [R_N, r_tor, half_cone_deg]
   --    Out_X1, Out_X2, Out_X3 — output optimal parameters
   --    Out_Cost       — output cost at optimum
   --    Out_Converged  — output convergence flag (1 = converged, 0 = not)
   --    Out_N_Iter     — output number of iterations used
   --
   --  CITATIONS:
   --    [Boyd04]   Boyd & Vandenberghe (2004), Convex Optimization, Sec 2.3.
   --    [Bertsekas99] Bertsekas (1999), Nonlinear Programming, Sec 2.7.
   -- -------------------------------------------------------------------------
   procedure Run_MoP_C
     (Learning_Rate  : Interfaces.C.Double;
      Tolerance      : Interfaces.C.Double;
      Lambda_1       : Interfaces.C.Double;
      Lambda_2       : Interfaces.C.Double;
      Max_Iter       : Interfaces.C.int;
      X1             : Interfaces.C.Double;
      X2             : Interfaces.C.Double;
      X3             : Interfaces.C.Double;
      Out_X1         : access Interfaces.C.Double;
      Out_X2         : access Interfaces.C.Double;
      Out_X3         : access Interfaces.C.Double;
      Out_Cost       : access Interfaces.C.Double;
      Out_Converged  : access Interfaces.C.int;
      Out_N_Iter     : access Interfaces.C.int);
   pragma Export (C, Run_MoP_C, "Run_MoP_C");

   -- -------------------------------------------------------------------------
   --  CCD Sample Array Types for FFI
   -- -------------------------------------------------------------------------
   --  AXIOMS:
   --    CCD_Sample_Count = 15 (8 factorial + 1 center + 6 axial).
   --    C callers allocate flat arrays of 15 doubles and pass them.
   --    Labels are a flat char buffer: 15 labels x 31 bytes = 465 bytes.
   --
   --  CITATION:
   --    [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
   -- -------------------------------------------------------------------------

   --  Number of CCD sample points (constant mirrors StellarOrion_Optimization).
   CCD_Samples : constant := 15;

   --  Label stride: 30 chars + 1 NUL terminator = 31 bytes per label.
   Label_Stride : constant := 31;

   --  Flat array type for CCD double outputs (C-compatible).
   type CCD_Double_Array is array (0 .. CCD_Samples - 1)
      of Interfaces.C.Double;
   pragma Convention (C, CCD_Double_Array);

   --  Flat array type for CCD label output (C-compatible char buffer).
   type CCD_Label_Buffer is array (0 .. CCD_Samples * Label_Stride - 1)
      of Character;
   pragma Convention (C, CCD_Label_Buffer);

   -- -------------------------------------------------------------------------
   --  Generate_CCD_Samples_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Generate_CCD_Samples.
   --  Generates 15 CCD design points and returns them as flat arrays.
   --
   --  AXIOMS:
   --    1. Output arrays must be pre-allocated by the caller with at least
   --       15 elements each.
   --    2. Labels are returned as a flat char buffer: 15 x 31 bytes.
   --    3. Label content is padded with spaces to 30 chars, NUL-terminated.
   --
   --  Parameters:
   --    Out_R_N    — array of nose sphere radii (15 elements)
   --    Out_R_Tor  — array of torus radii (15 elements)
   --    Out_Angles — array of half-cone angles (15 elements)
   --    Out_Labels — flat char buffer: 15 labels x 31 bytes = 465 bytes
   --
   --  CITATION:
   --    [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
   -- -------------------------------------------------------------------------
   procedure Generate_CCD_Samples_C
     (Out_R_N    : access CCD_Double_Array;
      Out_R_Tor  : access CCD_Double_Array;
      Out_Angles : access CCD_Double_Array;
      Out_Labels : access CCD_Label_Buffer);
   pragma Export (C, Generate_CCD_Samples_C, "Generate_CCD_Samples_C");

   -- -------------------------------------------------------------------------
   --  Sutton_Graves_Heat_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Sutton_Graves_Heat.
   --  Computes stagnation-point convective heat flux via SG correlation.
   --
   --  Parameters:
   --    Density     — freestream density [kg/m^3]
   --    Nose_Radius — nose sphere radius [m]
   --    Velocity    — freestream velocity [m/s]
   --
   --  Returns:
   --    Heat flux [W/m^2].
   --
   --  CITATION:
   --    [SuttonGraves71] Sutton & Graves (1971), NASA TR R-376.
   -- -------------------------------------------------------------------------
   function Sutton_Graves_Heat_C
     (Density     : Interfaces.C.Double;
      Nose_Radius : Interfaces.C.Double;
      Velocity    : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Sutton_Graves_Heat_C, "Sutton_Graves_Heat_C");

   -- -------------------------------------------------------------------------
   --  Sutherland_Viscosity_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Postprocessing.Sutherland_Viscosity.
   --  Computes dynamic viscosity of air via Sutherland's law.
   --
   --  Parameters:
   --    T — absolute temperature [K]
   --
   --  Returns:
   --    Dynamic viscosity [Pa*s].
   --
   --  CITATION:
   --    [Sutherland93] Sutherland (1893); Anderson (2006) Sec 15.2.
   -- -------------------------------------------------------------------------
   function Sutherland_Viscosity_C
     (T : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Sutherland_Viscosity_C, "Sutherland_Viscosity_C");

   -- -------------------------------------------------------------------------
   --  Fay_Riddell_Heat_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Fay_Riddell_Heat.
   --  Computes stagnation-point convective heat flux via FR correlation.
   --
   --  Parameters:
   --    Density_Kgm3  — freestream density [kg/m^3]
   --    Nose_Radius_M — nose sphere radius [m]
   --    Velocity_Ms   — freestream velocity [m/s]
   --    Mach          — freestream Mach number
   --    Wall_Temp_K   — wall temperature [K]
   --
   --  Returns:
   --    Heat flux [W/m^2].
   --
   --  CITATION:
   --    [FayRiddell58] Fay & Riddell (1958); Rapisarda (2023) Eq 3.82.
   -- -------------------------------------------------------------------------
   function Fay_Riddell_Heat_C
     (Density_Kgm3  : Interfaces.C.Double;
      Nose_Radius_M : Interfaces.C.Double;
      Velocity_Ms   : Interfaces.C.Double;
      Mach          : Interfaces.C.Double;
      Wall_Temp_K   : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Fay_Riddell_Heat_C, "Fay_Riddell_Heat_C");

   -- -------------------------------------------------------------------------
   --  Radiative_Eq_Temp_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Radiative_Eq_Temp.
   --  Computes radiative equilibrium surface temperature via Stefan-Boltzmann law.
   --  T = (q / (sigma * epsilon))^(1/4)
   --
   --  Parameters:
   --    Heat_Flux  — convective heat flux [W/m^2]
   --    Emissivity — surface emissivity [dimensionless, 0..1]
   --
   --  Returns:
   --    Surface temperature [K].
   --
   --  CITATION:
   --    [StefanBoltzmann] Stefan-Boltzmann law; stellarorion_physics.ads.
   -- -------------------------------------------------------------------------
   function Radiative_Eq_Temp_C
     (Heat_Flux  : Interfaces.C.Double;
      Emissivity : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Radiative_Eq_Temp_C, "Radiative_Eq_Temp_C");

   -- -------------------------------------------------------------------------
   --  Backface_Temperature_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Backface_Temperature.
   --  Computes 1D transient backface temperature.
   --  T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
   --
   --  Parameters:
   --    Init_Temp     — initial temperature [K]
   --    Heat_Flux     — heat flux [W/m^2]
   --    Duration      — heating duration [s]
   --    Thermal_Lag   — thermal lag efficiency [dimensionless, 0..1]
   --    TPS_Density   — TPS material density [kg/m^3]
   --    TPS_Cp        — TPS specific heat [J/(kg*K)]
   --    TPS_Thickness — TPS thickness [m]
   --
   --  Returns:
   --    Backface temperature [K].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006); Rapisarda (2023) Sec 5.5.
   -- -------------------------------------------------------------------------
   function Backface_Temperature_C
     (Init_Temp     : Interfaces.C.Double;
      Heat_Flux     : Interfaces.C.Double;
      Duration      : Interfaces.C.Double;
      Thermal_Lag   : Interfaces.C.Double;
      TPS_Density   : Interfaces.C.Double;
      TPS_Cp        : Interfaces.C.Double;
      TPS_Thickness : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Backface_Temperature_C, "Backface_Temperature_C");

   -- -------------------------------------------------------------------------
   --  Ballistic_Coefficient_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Ballistic_Coefficient.
   --  Computes ballistic coefficient: beta = m * q / F_drag.
   --
   --  Parameters:
   --    Mass         — vehicle mass [kg]
   --    Dyn_Pressure — dynamic pressure [Pa]
   --    Drag_Force   — drag force [N]
   --
   --  Returns:
   --    Ballistic coefficient [kg/m^2].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics.
   -- -------------------------------------------------------------------------
   function Ballistic_Coefficient_C
     (Mass         : Interfaces.C.Double;
      Dyn_Pressure : Interfaces.C.Double;
      Drag_Force   : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Ballistic_Coefficient_C, "Ballistic_Coefficient_C");

   -- -------------------------------------------------------------------------
   --  Dynamic_Pressure_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Dynamic_Pressure.
   --  Computes dynamic pressure: q = 0.5 * rho * V^2.
   --
   --  Parameters:
   --    Density  — freestream density [kg/m^3]
   --    Velocity — freestream velocity [m/s]
   --
   --  Returns:
   --    Dynamic pressure [Pa].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics.
   -- -------------------------------------------------------------------------
   function Dynamic_Pressure_C
     (Density  : Interfaces.C.Double;
      Velocity : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Dynamic_Pressure_C, "Dynamic_Pressure_C");

   -- -------------------------------------------------------------------------
   --  Deceleration_G_Load_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Deceleration_G_Load.
   --  Computes deceleration in Earth g's: n = F_drag / (m * g0).
   --
   --  Parameters:
   --    Drag_Force — drag force [N]
   --    Mass       — vehicle mass [kg]
   --
   --  Returns:
   --    Deceleration [g].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics.
   -- -------------------------------------------------------------------------
   function Deceleration_G_Load_C
     (Drag_Force : Interfaces.C.Double;
      Mass       : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Deceleration_G_Load_C, "Deceleration_G_Load_C");

   -- -------------------------------------------------------------------------
   --  Atmosphere_Temperature_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Environment.Atmosphere_Temperature.
   --  Computes ISA 1975 temperature [K] at altitude [km].
   --
   --  Parameters:
   --    Altitude_Km — altitude above sea level [km]
   --
   --  Returns:
   --    Temperature [K].
   --
   --  CITATION:
   --    [ISA] ISO 2533:1975, International Standard Atmosphere.
   -- -------------------------------------------------------------------------
   function Atmosphere_Temperature_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Atmosphere_Temperature_C, "Atmosphere_Temperature_C");

   -- -------------------------------------------------------------------------
   --  Atmosphere_Density_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Environment.Atmosphere_Density.
   --  Computes ISA 1975 density [kg/m^3] at altitude [km].
   --
   --  Parameters:
   --    Altitude_Km — altitude above sea level [km]
   --
   --  Returns:
   --    Density [kg/m^3].
   --
   --  CITATION:
   --    [ISA] ISO 2533:1975, International Standard Atmosphere.
   -- -------------------------------------------------------------------------
   function Atmosphere_Density_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double;
   pragma Export (C, Atmosphere_Density_C, "Atmosphere_Density_C");

end StellarOrion_FFI;
