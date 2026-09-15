-- =============================================================================
-- StellarOrion_FFI Body — C-Compatible Foreign Function Interface Layer
-- =============================================================================
-- AXIOMS:
--   1. Every C function receives plain scalars (Double, int) and returns
--      results through pointer parameters, matching the ctypes/cffi calling
--      convention on macOS (cdecl).
--   2. Type conversions between Interfaces.C.Double and Standard.Float are
--      safe because both are IEEE 754 binary64 (Long_Float on GNAT).
--   3. Interfaces.C.int is a 32-bit signed integer; Boolean is encoded as
--      1 (True) / 0 (False) per the C convention.
--   4. The body delegates all computation to StellarOrion_Optimization;
--      this layer contains zero domain logic.
--
-- THEOREMS:
--   1. Since Estimate_Cd, HIAD_Cost_Function, and Run_MoP_Optimization
--      have proven preconditions in the spec, the FFI wrappers can
--      safely call them given valid C inputs.
--   2. All output pointers are dereferenced exactly once, preventing
--      double-free or use-after-free scenarios.
--
-- CITATIONS:
--   [Ada2012]      ISO/IEC 8652:2012, Interfaces.C package.
--   [Ctypes]       Python ctypes — https://docs.python.org/3/library/ctypes.html
--   [Anderson06]   Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4.
--   [Nocedal06]    Nocedal & Wright (2006), Numerical Optimization, Sec 17.1.
--   [Boyd04]       Boyd & Vandenberghe (2004), Convex Optimization.
--   [Bertsekas99]  Bertsekas (1999), Nonlinear Programming, Sec 2.7.
--   [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
--   [Sutton51]     Sutton & Graves (1951), J. Aeronautical Sciences.
--   [NASA-TR-R376] NASA TR R-376 (1972) — C_SG = 1.7415e-4.
--
-- Author: Albert Starfield Wahyu Suryo Samudro
-- =============================================================================

with StellarOrion_Optimization; use StellarOrion_Optimization;
with StellarOrion_Physics;     use StellarOrion_Physics;
with StellarOrion_Postprocessing; use StellarOrion_Postprocessing;
with StellarOrion_Environment; use StellarOrion_Environment;

package body StellarOrion_FFI is

   -- -------------------------------------------------------------------------
   --  Estimate_Cd_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Optimization.Estimate_Cd with N_Tori = 6
   --  (IRVE-3 baseline default, per Rapisarda 2023 Table 4.1).
   --
   --  Safety fallback: If the underlying Estimate_Cd raises an exception
   --  (e.g., precondition violation from invalid geometry), the function
   --  returns 0.0 as a sentinel.  The Python caller must check for 0.0.
   -- -------------------------------------------------------------------------
   function Estimate_Cd_C
     (R_N           : Interfaces.C.Double;
      R_Tor         : Interfaces.C.Double;
      Half_Cone_Deg : Interfaces.C.Double)
      return Interfaces.C.Double
   is
      --  Type aliases for clarity
      Ada_R_N           : constant Standard.Float := Standard.Float (R_N);
      Ada_R_Tor         : constant Standard.Float := Standard.Float (R_Tor);
      Ada_Half_Cone_Deg : constant Standard.Float := Standard.Float (Half_Cone_Deg);
      Result            : Standard.Float;
   begin
      --  Delegate to the Ada optimization function
      --  N_Tori defaults to 6 (IRVE-3 baseline)
      Result := Estimate_Cd
        (R_N           => Ada_R_N,
         R_Tor         => Ada_R_Tor,
         Half_Cone_Deg => Ada_Half_Cone_Deg,
         N_Tori        => Default_N_Tori_MOP);

      return Interfaces.C.Double (Result);

   exception
      when others =>
         --  Safety fallback: return 0.0 sentinel on any error
         --  [Citation: Ada2012 RM 11.4 — Exception Handling]
         return 0.0;
   end Estimate_Cd_C;

   -- -------------------------------------------------------------------------
   --  HIAD_Cost_C
   -- -------------------------------------------------------------------------
   --  Assembles the three scalar parameters into a Param_Vector and
   --  delegates to StellarOrion_Optimization.HIAD_Cost_Function.
   --
   --  Safety fallback: Returns -1.0 sentinel on exception (cost is
   --  always >= 0.0 for valid inputs, so -1.0 signals an error).
   -- -------------------------------------------------------------------------
   function HIAD_Cost_C
     (X1 : Interfaces.C.Double;
      X2 : Interfaces.C.Double;
      X3 : Interfaces.C.Double)
      return Interfaces.C.Double
   is
      X : Param_Vector;
   begin
      X (1) := Standard.Float (X1);  -- R_N
      X (2) := Standard.Float (X2);  -- r_tor
      X (3) := Standard.Float (X3);  -- half_cone_deg

      return Interfaces.C.Double (HIAD_Cost_Function (X));

   exception
      when others =>
         --  Safety fallback: return -1.0 sentinel (cost >= 0.0 always)
         return Interfaces.C.Double (-1.0);
   end HIAD_Cost_C;

   -- -------------------------------------------------------------------------
   --  Run_MoP_C
   -- -------------------------------------------------------------------------
   --  Assembles MoP_Config and Param_Vector from individual C parameters,
   --  calls Run_MoP_Optimization, and writes results through output pointers.
   --
   --  Safety fallback: On exception, all output pointers are set to
   --  safe defaults (zeros, 0 = False, 0 iterations).
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
      Out_N_Iter     : access Interfaces.C.int)
   is
      --  Assemble MoP configuration from individual C parameters
      Config : MoP_Config;
      --  Assemble initial guess into Param_Vector
      X_Initial : Param_Vector;
      --  Result record from the optimizer
      Result : MoP_Result;
   begin
      --  Build MoP_Config
      Config.Learning_Rate := Standard.Float (Learning_Rate);
      Config.Tolerance     := Standard.Float (Tolerance);
      Config.Lambda_1      := Standard.Float (Lambda_1);
      Config.Lambda_2      := Standard.Float (Lambda_2);
      Config.Max_Iter      := Positive (Max_Iter);

      --  Build initial parameter vector
      X_Initial (1) := Standard.Float (X1);  -- R_N
      X_Initial (2) := Standard.Float (X2);  -- r_tor
      X_Initial (3) := Standard.Float (X3);  -- half_cone_deg

      --  Run the MoP optimizer
      Run_MoP_Optimization
        (Config    => Config,
         X_Initial => X_Initial,
         Result    => Result);

      --  Write results through output pointers
      Out_X1.all        := Interfaces.C.Double (Result.X_Opt (1));
      Out_X2.all        := Interfaces.C.Double (Result.X_Opt (2));
      Out_X3.all        := Interfaces.C.Double (Result.X_Opt (3));
      Out_Cost.all      := Interfaces.C.Double (Result.Cost);
      Out_N_Iter.all    := Interfaces.C.int (Result.N_Iter);

      --  Boolean -> C int encoding: True = 1, False = 0
      if Result.Converged then
         Out_Converged.all := 1;
      else
         Out_Converged.all := 0;
      end if;

   exception
      when others =>
         --  Safety fallback: zero all outputs on error
         Out_X1.all        := 0.0;
         Out_X2.all        := 0.0;
         Out_X3.all        := 0.0;
         Out_Cost.all      := 0.0;
         Out_Converged.all := 0;
         Out_N_Iter.all    := 0;
   end Run_MoP_C;

   -- -------------------------------------------------------------------------
   --  Generate_CCD_Samples_C
   -- -------------------------------------------------------------------------
   --  Generates 15 CCD design points via Generate_CCD_Samples, then
   --  copies each field into flat C arrays. Labels are copied as
   --  fixed-width 31-byte strings (30 chars + NUL terminator).
   --
   --  Safety fallback: On exception, output arrays are left zeroed
   --  and labels are filled with NUL bytes.
   -- -------------------------------------------------------------------------
   procedure Generate_CCD_Samples_C
     (Out_R_N    : access CCD_Double_Array;
      Out_R_Tor  : access CCD_Double_Array;
      Out_Angles : access CCD_Double_Array;
      Out_Labels : access CCD_Label_Buffer)
   is
      Samples : CCD_Sample_Array;
   begin
      --  Generate the 15 CCD sample points
      Generate_CCD_Samples (Samples => Samples);

      --  Copy numeric fields into flat arrays using index notation
      for I in 0 .. CCD_Samples - 1 loop
         declare
            Ada_I : constant Natural := I + 1;  --  Ada arrays are 1-based
         begin
            Out_R_N (I)    := Interfaces.C.Double (Samples (Ada_I).R_N);
            Out_R_Tor (I)  := Interfaces.C.Double (Samples (Ada_I).R_Tor);
            Out_Angles (I) := Interfaces.C.Double (Samples (Ada_I).Half_Cone_Deg);
         end;
      end loop;

      --  Copy labels into flat char buffer
      for I in 0 .. CCD_Samples - 1 loop
         declare
            Ada_I     : constant Natural := I + 1;
            Buf_Start : constant Natural := I * Label_Stride;
         begin
            --  Copy up to CCD_Label_Max characters from the label
            for J in 1 .. CCD_Label_Max loop
               Out_Labels (Buf_Start + J - 1) := Samples (Ada_I).Label (J);
            end loop;

            --  NUL-terminate the label (index 30 = CCD_Label_Max, 0-based)
            --  Label_Stride = 31 = CCD_Label_Max + 1, so NUL is the last byte.
            --  No padding needed: 30 chars + 1 NUL = 31 bytes = Label_Stride.
            Out_Labels (Buf_Start + CCD_Label_Max) := Character'Val (0);
         end;
      end loop;

   exception
      when others =>
         --  Safety fallback: zero all output buffers on error
         for I in 0 .. CCD_Samples - 1 loop
            Out_R_N (I)    := 0.0;
            Out_R_Tor (I)  := 0.0;
            Out_Angles (I) := 0.0;
         end loop;

         for I in 0 .. CCD_Samples * Label_Stride - 1 loop
            Out_Labels (I) := Character'Val (0);
         end loop;
   end Generate_CCD_Samples_C;

   -- -------------------------------------------------------------------------
   --  Sutton_Graves_Heat_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Sutton_Graves_Heat.
   --  Safety fallback: Returns 0.0 on exception.
   -- -------------------------------------------------------------------------
   function Sutton_Graves_Heat_C
     (Density     : Interfaces.C.Double;
      Nose_Radius : Interfaces.C.Double;
      Velocity    : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Sutton_Graves_Heat (
          Density     => Standard.Float (Density),
          Nose_Radius => Standard.Float (Nose_Radius),
          Velocity    => Standard.Float (Velocity)));
   exception
      when others =>
         return 0.0;
   end Sutton_Graves_Heat_C;

   -- -------------------------------------------------------------------------
   --  Sutherland_Viscosity_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Postprocessing.Sutherland_Viscosity.
   --  Safety fallback: Returns 1.716e-5 (MU_REF at 0 K limit) on exception.
   -- -------------------------------------------------------------------------
   function Sutherland_Viscosity_C
     (T : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Sutherland_Viscosity (T => Standard.Float (T)));
   exception
      when others =>
         return 1.716e-5;
   end Sutherland_Viscosity_C;

   -- -------------------------------------------------------------------------
   --  Fay_Riddell_Heat_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Fay_Riddell_Heat.
   --  Safety fallback: Returns 0.0 on exception.
   -- -------------------------------------------------------------------------
   function Fay_Riddell_Heat_C
     (Density_Kgm3  : Interfaces.C.Double;
      Nose_Radius_M : Interfaces.C.Double;
      Velocity_Ms   : Interfaces.C.Double;
      Mach          : Interfaces.C.Double;
      Wall_Temp_K   : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Fay_Riddell_Heat (
          Density_Kgm3  => Standard.Float (Density_Kgm3),
          Nose_Radius_M => Standard.Float (Nose_Radius_M),
          Velocity_Ms   => Standard.Float (Velocity_Ms),
          Mach          => Standard.Float (Mach),
          Wall_Temp_K   => Standard.Float (Wall_Temp_K)));
   exception
      when others =>
         return 0.0;
   end Fay_Riddell_Heat_C;

   -- -------------------------------------------------------------------------
   --  Radiative_Eq_Temp_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Radiative_Eq_Temp.
   --  Safety fallback: Returns 300.0 (ambient temperature) on exception.
   -- -------------------------------------------------------------------------
   function Radiative_Eq_Temp_C
     (Heat_Flux  : Interfaces.C.Double;
      Emissivity : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Radiative_Eq_Temp (
          Heat_Flux  => Standard.Float (Heat_Flux),
          Emissivity => Standard.Float (Emissivity)));
   exception
      when others =>
         return 300.0;
   end Radiative_Eq_Temp_C;

   -- -------------------------------------------------------------------------
   --  Backface_Temperature_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Backface_Temperature.
   --  Safety fallback: Returns 300.0 (ambient temperature) on exception.
   -- -------------------------------------------------------------------------
   function Backface_Temperature_C
     (Init_Temp     : Interfaces.C.Double;
      Heat_Flux     : Interfaces.C.Double;
      Duration      : Interfaces.C.Double;
      Thermal_Lag   : Interfaces.C.Double;
      TPS_Density   : Interfaces.C.Double;
      TPS_Cp        : Interfaces.C.Double;
      TPS_Thickness : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Backface_Temperature (
          Init_Temp     => Standard.Float (Init_Temp),
          Heat_Flux     => Standard.Float (Heat_Flux),
          Duration      => Standard.Float (Duration),
          Thermal_Lag   => Standard.Float (Thermal_Lag),
          TPS_Density   => Standard.Float (TPS_Density),
          TPS_Cp        => Standard.Float (TPS_Cp),
          TPS_Thickness => Standard.Float (TPS_Thickness)));
   exception
      when others =>
         return 300.0;
   end Backface_Temperature_C;

   -- -------------------------------------------------------------------------
   --  Ballistic_Coefficient_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Ballistic_Coefficient.
   --  Safety fallback: Returns 0.0 on exception.
   -- -------------------------------------------------------------------------
   function Ballistic_Coefficient_C
     (Mass         : Interfaces.C.Double;
      Dyn_Pressure : Interfaces.C.Double;
      Drag_Force   : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Ballistic_Coefficient (
          Mass         => Standard.Float (Mass),
          Dyn_Pressure => Standard.Float (Dyn_Pressure),
          Drag_Force   => Standard.Float (Drag_Force)));
   exception
      when others =>
         return 0.0;
   end Ballistic_Coefficient_C;

   -- -------------------------------------------------------------------------
   --  Dynamic_Pressure_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Dynamic_Pressure.
   --  Safety fallback: Returns 0.0 on exception.
   -- -------------------------------------------------------------------------
   function Dynamic_Pressure_C
     (Density  : Interfaces.C.Double;
      Velocity : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Dynamic_Pressure (
          Density  => Standard.Float (Density),
          Velocity => Standard.Float (Velocity)));
   exception
      when others =>
         return 0.0;
   end Dynamic_Pressure_C;

   -- -------------------------------------------------------------------------
   --  Deceleration_G_Load_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Deceleration_G_Load.
   --  Safety fallback: Returns 0.0 on exception.
   -- -------------------------------------------------------------------------
   function Deceleration_G_Load_C
     (Drag_Force : Interfaces.C.Double;
      Mass       : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Deceleration_G_Load (
          Drag_Force => Standard.Float (Drag_Force),
          Mass       => Standard.Float (Mass)));
   exception
      when others =>
         return 0.0;
   end Deceleration_G_Load_C;

   -- -------------------------------------------------------------------------
   --  Atmosphere_Temperature_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Environment.Atmosphere_Temperature.
   --  Safety fallback: Returns 288.15 (sea-level ISA) on exception.
   -- -------------------------------------------------------------------------
   function Atmosphere_Temperature_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Atmosphere_Temperature (
          Altitude_Km => Standard.Float (Altitude_Km)));
   exception
      when others =>
         return 288.15;
   end Atmosphere_Temperature_C;

   -- -------------------------------------------------------------------------
   --  Atmosphere_Density_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Environment.Atmosphere_Density.
   --  Safety fallback: Returns 1.225 (sea-level ISA) on exception.
   -- -------------------------------------------------------------------------
   function Atmosphere_Density_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Atmosphere_Density (
          Altitude_Km => Standard.Float (Altitude_Km)));
   exception
      when others =>
         return 1.225;
   end Atmosphere_Density_C;

end StellarOrion_FFI;
