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
    --
    --  AXIOM G1 (radius envelope [1e-6, 1e3] m):
    --    * Lower bound: below Y_max ~ 2.3e-23 the square Y_max^2 underflows
    --      Float to exactly 0.0, breaking Post (Result > 0). A floor of 1e-6 m
    --      (micrometre scale) keeps Y_max^2 >= 1e-12, far above Float'Model_Small
    --      (~1.18e-38), so the product is strictly positive and normal.
    --    * Upper bound: largest HIAD flown/planned is LOFTID at ~6 m radius;
   --      1e3 m gives >100x headroom. Overflow bound: Pi * (1e3)^2 = 3.14e6,
   --      negligible vs Float'Last (~3.4e38).
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Frontal_Area") (no direct
   --  self-test call; proof-verified unit).
   function Frontal_Area (Y_Max : Float) return Float
      with Pre  => Y_Max >= 1.0e-6
                   and Y_Max <= 1.0e3,
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
    --
    --  AXIOM G2 (physical envelopes, Rapisarda 2023 Table 5.4 mirrors):
    --    * Diameter     [0.5, 15.0] m  : Rap23 Tab 5.4; matches
    --      Geometry_Parameters.Diameter_M subtype (Diameter_Range).
    --    * Angle_Deg    [40.0, 80.0]   : Rap23 Tab 5.4 cone half-angle band;
    --      ALSO the documented validity range of the Taylor-series trig
    --      helpers below (< 0.01% error). The former [0,180] Pre admitted
    --      angles where those series degrade silently.
    --    * Toroid_Radius (0, 5] m      : GA bound [0.01, 0.5]; IRVE-3 uses
    --      0.135 m (Rap23 Tab 4.1); 10x headroom above GA max.
    --    * TPS_Thickness (0, 1] m      : mirrors TPS_Thickness_Range subtype.
    --    * TPS_Density  [10, 1e4] kg/m3: mirrors TPS_Density_Range subtype.
   --  Overflow proof: worst-case chain Total_A ~ 4.5e8 m^2, mass <=
   --  Total_A * t * rho <= 4.5e8 * 1 * 1e4 = 4.5e12 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Shield_Mass_Analytical")
   --  (no direct self-test call; proof-verified unit).
   function Shield_Mass_Analytical
      (Diameter      : Float;
       Angle_Deg     : Float;
       Toroid_Count  : Positive;
       Toroid_Radius : Float;
       TPS_Thickness : Float;
       TPS_Density   : Float) return Float
      with Pre  => Diameter >= 0.5
                   and Diameter <= 15.0
                   and Angle_Deg >= 40.0
                   and Angle_Deg <= 80.0
                   and Toroid_Radius > 0.0
                   and Toroid_Radius <= 5.0
                   and TPS_Thickness > 0.0
                   and TPS_Thickness <= 1.0
                   and TPS_Density >= 10.0
                   and TPS_Density <= 1.0e4,
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
    --
    --  AXIOM G3 (physical envelopes, mirrors AXIOM G2):
    --    * Diameter     [0.5, 15.0] m   : Rap23 Tab 5.4.
    --    * Toroid_Radius (0, 5] m       : GA bound 10x headroom.
    --    * Num_Toroids  <= 12           : Rap23 Tab 5.4 upper bound
    --      (lower bound is the Positive subtype).
    --    * Density      [10, 1e4] kg/m3 : TPS_Density_Range mirror.
   --  Overflow proof: N * rho * pi^2 * D * r^2 <=
   --  12 * 1e4 * 9.87 * 15 * 25 = 4.4e8 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Shield_Mass_Pappus")
   --  (no direct self-test call; proof-verified unit).
   function Shield_Mass_Pappus
      (Diameter      : Float;
       Toroid_Radius : Float;
       Num_Toroids   : Positive;
       Density       : Float) return Float
      with Pre  => Diameter >= 0.5
                   and Diameter <= 15.0
                   and Toroid_Radius > 0.0
                   and Toroid_Radius <= 5.0
                   and Num_Toroids <= 12
                   and Density >= 10.0
                   and Density <= 1.0e4,
           Post => Shield_Mass_Pappus'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Geometry Validation
   -- -----------------------------------------------------------------

   --  Pre-simulation sanity check per Rapisarda 2023 Table 5.4:
   --    Angle       : 40 .. 80 deg
   --    Toroid_Count: 1 .. 12
   --    Diameter    : 0.5 .. 15.0 m
   --  Returns True iff all geometry parameters are within valid bounds.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Validate_Geometry") -> Test 4.
   function Validate_Geometry (Params : Geometry_Parameters) return Boolean;

end StellarOrion_Geometry;
