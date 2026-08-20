--  StellarOrion_HypersonicEdition — Geometry Utilities
--  Ada 2012 / SPARK 2014
--  Pure-math aeroshell geometry calculations.
--
--  Citations:
--    [Rap23]  Rapisarda, V. "Multidisciplinary Design Analysis and
--              Optimization of HIAD," Ph.D. thesis, 2023.
--    [Pappus] Pappus's centroid theorem for surfaces of revolution.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Geometry is
   pragma SPARK_Mode (On);

   --  Pi (Ada 2012 has no Standard.Math.Pi constant in SPARK; define here)
   Pi : constant Float := 3.141592653589793;

   -- -----------------------------------------------------------------
   --  Frontal / Reference Area
   -- -----------------------------------------------------------------

   --  Circular frontal (projected) area [m^2].
   --  A = pi * Y_max^2
   --  Y_max is the maximum radius; must be positive for a meaningful area.
   function Frontal_Area (Y_Max : Float) return Float
     with Pre  => Y_Max > 0.0,
          Post => Frontal_Area'Result > 0.0;

   -- -----------------------------------------------------------------
   --  Shield Mass  (Analytical Pappus-based estimate)
   -- -----------------------------------------------------------------

   --  Mass of the flexible TPS shield [kg].
   --  Decomposition (Rapisarda 2023):
   --    * Nose cap      : 2 * pi * R * h   (hemisphere arc)
   --    * Cone frustum  : pi * (r1 + r2) * L
   --    * Scallop       : 1.2x cone frustum (wrinkle factor)
   --    * Toroids       : 2 * pi^2 * R_tor * r_tor^2 * 0.1 * density
   --  where h = nose height, L = slant length of frustum.
   --  Diameter, angle, toroid radius, TPS thickness, and TPS density
   --  must all be positive for a meaningful mass estimate.
   function Shield_Mass_Analytical
     (Diameter      : Float;
      Angle_Deg     : Float;
      Toroid_Count  : Positive;
      Toroid_Radius : Float;
      TPS_Thickness : Float;
      TPS_Density   : Float) return Float
     with Pre  => Diameter > 0.0
                  and Angle_Deg >= 0.0
                  and Angle_Deg <= 180.0
                  and Toroid_Radius > 0.0
                  and TPS_Thickness > 0.0
                  and TPS_Density > 0.0,
          Post => Shield_Mass_Analytical'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Shield Mass  (Pappus Theorem for Toroidal Shield)
   -- -----------------------------------------------------------------

   --  Mass of the toroidal shield rings using Pappus centroid theorem:
   --    m_shield = rho * 2 * pi * R_centroid * A_cross
   --  where R_centroid is distance from axis to toroid centroid,
   --  A_cross is the cross-sectional area of a single toroid.
   --  For a circular toroid cross-section: A_cross = pi * r_tor^2
   --  and R_centroid = R_base (center of toroid tube from axis).
   --
   --  Parameters:
   --    Diameter     : HIAD major diameter [m]
   --    Toroid_Radius: Minor radius of toroid tube [m]
   --    Num_Toroids  : Number of stacked toroid rings
   --    Density      : Shield material density [kg/m^3]
   function Shield_Mass_Pappus
     (Diameter      : Float;
      Toroid_Radius : Float;
      Num_Toroids   : Positive;
      Density       : Float) return Float
     with Pre  => Diameter > 0.0
                  and Toroid_Radius > 0.0
                  and Density > 0.0,
          Post => Shield_Mass_Pappus'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Geometry Validation
   -- -----------------------------------------------------------------

   --  Pre-simulation sanity check per Rapisarda 2023 Table 5.4:
   --    Angle       : 40 .. 80 deg
   --    Toroid_Count: 1 .. 12
   --    Diameter    : 0.5 .. 15.0 m
   --  Returns True iff all geometry parameters are within valid bounds.
   function Validate_Geometry (Params : Geometry_Parameters) return Boolean;

end StellarOrion_Geometry;
