--  StellarOrion_HypersonicEdition — Atmospheric Environment Model
--  Ada 2012 / SPARK 2014
--  International Standard Atmosphere (ISA) 1975 piecewise profile.
--
--  Citations:
--    [ISA]   ISO 2533:1975, International Standard Atmosphere.
--    [US76]  U.S. Standard Atmosphere, 1976.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Environment is
   pragma SPARK_Mode (On);

   Pi : constant Float := 3.141592653589793;

   -- -----------------------------------------------------------------
   --  Mach <-> Velocity Conversion
   -- -----------------------------------------------------------------

   --  Convert Mach number to true airspeed [m/s].
   --  V = Mach * sqrt(gamma * R * T)
   --  gamma = 1.4 (air), R = 287.058 J/(kg*K)
   --  Mach must be non-negative; temperature must be positive for the
   --  square root of gamma*R*T to be real and meaningful.
   function Mach_To_Velocity
     (Mach        : Float;
      Temperature : Float) return Float
     with Pre  => Mach >= 0.0 and Temperature > 0.0,
          Post => Mach_To_Velocity'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  ISA Atmosphere Model
   -- -----------------------------------------------------------------

   --  Standard atmosphere temperature [K] at altitude [km].
   --  Piecewise linear profile from ISO 2533:1975.
   --  Altitude must be non-negative (below sea level is clamped).
   --  ISA guarantees positive temperature throughout the modelled
   --  atmosphere (minimum ~187 K in the thermosphere).
   function Atmosphere_Temperature
     (Altitude_Km : Float) return Float
     with Pre  => Altitude_Km >= 0.0,
          Post => Atmosphere_Temperature'Result >= 0.0;

   --  Standard atmosphere density [kg/m^3] at altitude [km].
   --  Piecewise exponential/linear model from ISO 2533:1975.
   --  Altitude must be non-negative; density is always non-negative
   --  (approaches zero at very high altitudes).
   function Atmosphere_Density
     (Altitude_Km : Float) return Float
     with Pre  => Altitude_Km >= 0.0,
          Post => Atmosphere_Density'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Composite: Mach + Altitude  ->  Flight_Parameters
   -- -----------------------------------------------------------------

   --  Given a Mach number and altitude, populate a Flight_Parameters
   --  record with density, temperature, and velocity.
   --  Mach and altitude must be non-negative for meaningful results.
   procedure Mach_Alt_To_Flight
     (Mach    : Float;
      Alt_Km  : Float;
      Flight  : out Flight_Parameters)
      with Pre => Mach >= 0.0 and Alt_Km >= 0.0;

   -- -----------------------------------------------------------------
   --  NRLMSIS 2.1 Atmosphere Model (Python pymsis wrapper)
   -- -----------------------------------------------------------------

   --  Query the NRLMSIS 2.1 atmosphere model via the Python pymsis
   --  library.  If pymsis is unavailable, falls back to ISA.
   --
   --  Inputs:
   --    Alt_Km       : Geodetic altitude [km]
   --    Latitude_Deg : Geographic latitude [deg], default 0.0
   --    Day_Of_Year  : Day of year (1..365), default 1
   --    F107         : 10.7 cm solar flux [SFU], default 150.0
   --    F107_A       : 81-day avg F107 [SFU], default 150.0
   --  Outputs:
   --    Density      : Total mass density [kg/m^3]
   --    Temperature  : Exospheric temperature [K]
   procedure MSIS_Atmosphere
     (Alt_Km       : Float;
      Latitude_Deg : Float;
      Day_Of_Year  : Positive;
      F107         : Float;
      F107_A       : Float;
      Density      : out Float;
      Temperature  : out Float)
      with SPARK_Mode => Off,
           Pre => Alt_Km >= 0.0;

end StellarOrion_Environment;
