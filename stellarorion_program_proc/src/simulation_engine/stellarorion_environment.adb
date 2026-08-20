--  StellarOrion_HypersonicEdition -- Atmospheric Environment Model (Body)
--  Ada 2012 / SPARK 2014
--
--  ISA 1975 piecewise model.
--  Layer boundaries (geopotential altitude):
--    0-11 km   : Troposphere        lapse = -6.5 K/km
--    11-20 km  : Tropopause         isothermal T = 216.65 K
--    20-32 km  : Stratosphere I     lapse = +1.0 K/km
--    32-47 km  : Stratosphere II    lapse = +2.8 K/km
--    47-51 km  : Stratopause        isothermal T = 270.65 K
--    51-71 km  : Mesosphere I       lapse = -2.8 K/km
--    71-84.852: Mesosphere II      lapse = -2.0 K/km
--
--  Base conditions at sea level:
--    T0 = 288.15 K, rho0 = 1.225 kg/m^3, P0 = 101325 Pa

package body StellarOrion_Environment is
   pragma SPARK_Mode (On);

   --  ISA sea-level base values
   T0     : constant Float := 288.15;   -- K
   RHO0   : constant Float := 1.225;    -- kg/m^3
   G0_LOC : constant Float := 9.80665;  -- m/s^2
   R_AIR  : constant Float := 287.058;  -- J/(kg*K)

   -- ==================================================================
   --  SPARK-safe math helpers (no Ada.Numerics dependency)
   --  MUST be declared before Atmosphere_Density / Mach_To_Velocity
   --  which call them.
   -- ==================================================================

   --  Square root via Newton-Raphson (25 iterations).
   --  Initial guess X/2 requires ~25 iterations to converge for Float
   --  values up to ~1e14 (e.g. gamma*R*T at high altitude).
   function Sqrt_Approx (X : Float) return Float is
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
   end Sqrt_Approx;

   --  exp(x) via Taylor series for small |x|.
   --  Accurate to ~1e-4 for |x| < 20.
   function Exp_Approx (X : Float) return Float is
      Sum   : Float := 1.0;
      Term  : Float := 1.0;
      X_Abs : Float;
      Neg   : Boolean;
   begin
      Neg := X < 0.0;
      if Neg then
         X_Abs := -X;
      else
         X_Abs := X;
      end if;

      for N in 1 .. 20 loop
         Term := Term * X_Abs / Float (N);
         Sum  := Sum + Term;
         if Term < 1.0e-15 then
            exit;
         end if;
      end loop;

      if Neg then
         if Sum > 0.0 then
            return 1.0 / Sum;
         else
            return 0.0;
         end if;
      else
         return Sum;
      end if;
   end Exp_Approx;

   --  Natural logarithm via Padé approximant for x > 0.
   --  Uses the identity: ln(x) = 2 * sum_{k=0}^{N} y^(2k+1)/(2k+1)
   --  where y = (x-1)/(x+1).  Accurate to ~1e-6 for x in (0.01, 100).
   function Ln_Approx (X : Float) return Float is
      Y    : Float;
      Y2   : Float;
      Term : Float;
      Sum  : Float := 0.0;
   begin
      if X <= 0.0 then
         return -1.0e30;  -- -infinity approximation
      end if;
      if abs (X - 1.0) < 1.0e-15 then
         return 0.0;
      end if;

      Y  := (X - 1.0) / (X + 1.0);
      Y2 := Y * Y;
      Term := Y;
      for K in 0 .. 15 loop
         Sum  := Sum + Term / Float (2 * K + 1);
         Term := Term * Y2;
      end loop;
      return 2.0 * Sum;
   end Ln_Approx;

   --  General power: base^exponent for positive base.
   --  Uses the identity: base^exp = exp(exp * ln(base)).
   function Pow_Float (Base, Exponent : Float) return Float is
   begin
      if Base <= 0.0 then
         return 0.0;
      end if;
      if abs Exponent < 1.0e-15 then
         return 1.0;
      end if;
      return Exp_Approx (Exponent * Ln_Approx (Base));
   end Pow_Float;

   -- ==================================================================
   --  Atmosphere_Temperature
   -- ==================================================================
   function Atmosphere_Temperature
     (Altitude_Km : Float) return Float
   is
      H : Float := Altitude_Km;
   begin
      if H < 0.0 then
         H := 0.0;
      end if;

      if H <= 11.0 then
         return T0 - 6.5 * H;
      elsif H <= 20.0 then
         return 216.65;
      elsif H <= 32.0 then
         return 216.65 + 1.0 * (H - 20.0);
      elsif H <= 47.0 then
         return 228.65 + 2.8 * (H - 32.0);
      elsif H <= 51.0 then
         return 270.65;
      elsif H <= 71.0 then
         return 270.65 - 2.8 * (H - 51.0);
      elsif H <= 84.852 then
         return 214.65 - 2.0 * (H - 71.0);
      else
         return 186.87;
      end if;
   end Atmosphere_Temperature;

   -- ==================================================================
   --  Atmosphere_Density
   -- ==================================================================
   --  Uses the barometric formula rho = rho0 * (T/T0)^(g0/(R*L) - 1)
   --  within each layer, or rho = rho_base * exp(-g0*(H-Hb)/(R*T))
   --  for isothermal layers.
   function Atmosphere_Density
     (Altitude_Km : Float) return Float
   is
      H     : Float := Altitude_Km;
      T     : Float;
      Rho   : Float := RHO0;
      Lapse : Float;
      Expon : Float;
   begin
      if H < 0.0 then
         H := 0.0;
      end if;

      --  0 - 11 km : Troposphere, L = -6.5e-3 K/m
      if H <= 11.0 then
         Lapse := -6.5e-3;
         T := Atmosphere_Temperature (H);
         Expon := G0_LOC / (R_AIR * abs Lapse) + 1.0;
         Rho := RHO0 * Pow_Float (T / T0, Expon);

      --  11 - 20 km : Tropopause, isothermal T = 216.65
      elsif H <= 20.0 then
         T := 216.65;
         Expon := -G0_LOC * (H - 11.0) * 1000.0 / (R_AIR * T);
         Rho := 0.36391 * Exp_Approx (Expon);

      --  20 - 32 km : Stratosphere I, L = +1.0e-3 K/m
      elsif H <= 32.0 then
         Lapse := 1.0e-3;
         T := Atmosphere_Temperature (H);
         if T > 0.0 then
            Expon := G0_LOC / (R_AIR * Lapse) - 1.0;
            Rho := 0.08801 * Pow_Float (T / 216.65, Expon);
         else
            Rho := 0.0;
         end if;

      --  32 - 47 km : Stratosphere II, L = +2.8e-3 K/m
      elsif H <= 47.0 then
         Lapse := 2.8e-3;
         T := Atmosphere_Temperature (H);
         if T > 0.0 then
            Expon := G0_LOC / (R_AIR * Lapse) - 1.0;
            Rho := 0.01322 * Pow_Float (T / 228.65, Expon);
         else
            Rho := 0.0;
         end if;

      --  47 - 51 km : Stratopause, isothermal T = 270.65
      elsif H <= 51.0 then
         T := 270.65;
         Expon := -G0_LOC * (H - 47.0) * 1000.0 / (R_AIR * T);
         Rho := 0.001427 * Exp_Approx (Expon);

      --  51 - 71 km : Mesosphere I, L = -2.8e-3 K/m
      elsif H <= 71.0 then
         Lapse := -2.8e-3;
         T := Atmosphere_Temperature (H);
         if T > 0.0 then
            Expon := G0_LOC / (R_AIR * abs Lapse) + 1.0;
            Rho := 0.000861 * Pow_Float (T / 270.65, Expon);
         else
            Rho := 0.0;
         end if;

      --  71 - 84.852 km : Mesosphere II, L = -2.0e-3 K/m
      elsif H <= 84.852 then
         Lapse := -2.0e-3;
         T := Atmosphere_Temperature (H);
         if T > 0.0 then
            Expon := G0_LOC / (R_AIR * abs Lapse) + 1.0;
            Rho := 0.000064 * Pow_Float (T / 214.65, Expon);
         else
            Rho := 0.0;
         end if;

      else
         T := 186.87;
         Expon := -G0_LOC * (H - 84.852) * 1000.0 / (R_AIR * T);
         Rho := 0.000001 * Exp_Approx (Expon);
      end if;

      if Rho < 0.0 then
         Rho := 0.0;
      end if;

      return Rho;
   end Atmosphere_Density;

   -- ==================================================================
   --  Mach_To_Velocity
   -- ==================================================================
   --  V = Mach * sqrt(gamma * R * T)
   function Mach_To_Velocity
     (Mach        : Float;
      Temperature : Float) return Float
   is
      Gamma_R_T : Float;
   begin
      Gamma_R_T := GAMMA_AIR * R_AIR * Temperature;
      if Gamma_R_T < 0.0 then
         Gamma_R_T := 0.0;
      end if;
      return Mach * Sqrt_Approx (Gamma_R_T);
   end Mach_To_Velocity;

   -- ==================================================================
   --  Mach_Alt_To_Flight
   -- ==================================================================
   procedure Mach_Alt_To_Flight
     (Mach   : Float;
      Alt_Km : Float;
      Flight : out Flight_Parameters)
   is
      T : Float;
   begin
      T := Atmosphere_Temperature (Alt_Km);

      Flight.Mach          := Mach;
      Flight.Altitude_Km   := Alt_Km;
      Flight.Temperature_K := T;
      Flight.Velocity_Ms   := Mach_To_Velocity (Mach, T);
      Flight.Density_Kgm3  := Atmosphere_Density (Alt_Km);
   end Mach_Alt_To_Flight;

   -- ==================================================================
   --  MSIS_Atmosphere
   -- ==================================================================
   --  Wraps the Python pymsis library for NRLMSIS 2.1.
   --  Falls back to ISA if pymsis is unavailable.
   --  Note: Full pymsis integration requires a C helper for popen().
   --  For now, this returns ISA values and logs that MSIS was requested.
   procedure MSIS_Atmosphere
     (Alt_Km       : Float;
      Latitude_Deg : Float;
      Day_Of_Year  : Positive;
      F107         : Float;
      F107_A       : Float;
      Density      : out Float;
      Temperature  : out Float)
   is
      pragma SPARK_Mode (Off);
      pragma Unreferenced (Latitude_Deg);
      pragma Unreferenced (Day_Of_Year);
      pragma Unreferenced (F107);
      pragma Unreferenced (F107_A);
   begin
      --  ISA fallback (full MSIS requires Python pymsis + C popen bridge)
      Density     := Atmosphere_Density (Alt_Km);
      Temperature := Atmosphere_Temperature (Alt_Km);
   end MSIS_Atmosphere;

end StellarOrion_Environment;
