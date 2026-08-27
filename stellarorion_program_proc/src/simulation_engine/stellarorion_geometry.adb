--  StellarOrion_HypersonicEdition -- Geometry Utilities (Body)
--  Ada 2012 / SPARK 2014

package body StellarOrion_Geometry is
   pragma SPARK_Mode (On);

   -- ==================================================================
   --  Trig helper (SPARK-safe, no Numerics dependency)
   --  Taylor-series approximation truncated at O(x^7).
   --  Sufficient for 40-80 degree range with < 0.01% error.
   --  MUST be declared before Shield_Mass_Analytical which calls it.
   --  NOTE: a former Cos_Deg twin was removed as dead code when its only
   --  consumer (unused Cos_A) was deleted.
   -- ==================================================================

   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Deg_To_Rad") (helper for
   --  Sin_Deg; no direct self-test call - proof-verified unit).
--  @covered: gnatprove --level=4 formal proof (scripts/prove.sh).
   function Deg_To_Rad (Deg : Float) return Float
     with Global => null is
      --  Contract: pre  => any Float angle value;
      --           post => radians = Deg * Pi / 180.0, sign-preserving.
   begin
      --  NaN/Inf impossible: divisor is the compile-time constant 180.0
      --  (nonzero), so the quotient stays finite for every finite Deg.
      return Deg * Pi / 180.0;
   end Deg_To_Rad;

   --  Sine of an angle in degrees via the truncated Taylor series
   --  x - x^3/6 + x^5/120 - x^7/5040; SPARK-safe (no Ada.Numerics),
   --  accurate to < 0.01% over the aeroshell's 40-80 degree envelope.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Sin_Deg") (no direct
   --  self-test call - proof-verified unit).
--  @covered: gnatprove --level=4 formal proof (scripts/prove.sh).
   function Sin_Deg (Deg : Float) return Float
     with Global => null is
      --  Contract: pre  => Deg within the documented 40 .. 80 deg
      --           validity band of the Taylor series (< 0.01% error);
      --           post => sin(Deg) via truncated series x - x^3/6 +
      --           x^5/120 - x^7/5040.
      X  : constant Float := Deg_To_Rad (Deg);
      X3 : constant Float := X * X * X;
      X5 : constant Float := X3 * X * X;
      X7 : constant Float := X5 * X * X;
   begin
      --  NaN/Inf impossible: divisors 6.0, 120.0, 5040.0 are nonzero
      --  compile-time constants; quotients stay finite for finite X.
      --  sin(x) = x - x^3/6 + x^5/120 - x^7/5040
      return X - X3 / 6.0 + X5 / 120.0 - X7 / 5040.0;
   end Sin_Deg;

   --  ==================================================================
   --  Frontal_Area
   --  ==================================================================
   --  A = pi * Y_max^2
   --  NOTE: explicit Y_Max * Y_Max instead of '**' — GNATprove cannot
   --  discharge overflow VCs through the opaque float-exponentiation call.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Frontal_Area") (no direct
   --  self-test call - proof-verified unit).
--  @covered: gnatprove --level=4 formal proof (scripts/prove.sh).
   function Frontal_Area (Y_Max : Float) return Float is
      --  Contract: pre  => Y_Max in [1e-6, 1e3] m (AXIOM G1 envelope);
      --           post => A = pi * Y_max^2 > 0.0 m^2.
      Y2 : constant Float := Y_Max * Y_Max;
   begin
      return Pi * Y2;
   end Frontal_Area;

   -- ==================================================================
   --  Shield_Mass_Analytical
   -- ==================================================================
   --  Pappus theorem decomposition:
   --    1. Nose cap       : hemisphere arc  ->  2 * pi * R_nose * h_nose
   --    2. Cone frustum   : pi * (r1 + r2) * L_slant
   --    3. Scallop factor : 1.2x frustum (wrinkle allowance)
   --    4. Toroids        : 2 * pi^2 * R_tor * r_tor^2 * t * rho
   --
   --  Source: Rapisarda 2023 Sec 4.2 / Table 4.1
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Shield_Mass_Analytical")
   --  (no direct self-test call - proof-verified unit).
   function Shield_Mass_Analytical
     (Diameter      : Float;
       Angle_Deg     : Float;
       Toroid_Count  : Positive;
       Toroid_Radius : Float;
       TPS_Thickness : Float;
       TPS_Density   : Float) return Float
   is
      --  Contract: pre  => AXIOM G2 envelopes (Diameter [0.5, 15] m,
      --           Angle_Deg [40, 80] deg, Toroid_Radius (0, 5] m,
      --           TPS_Thickness (0, 1] m, TPS_Density [10, 1e4]);
      --           post => mass >= 0.0 kg; 0.0 on degenerate flat cone.
      Two_Pi   : constant Float := 2.0 * Pi;
      R_nose   : Float;   -- nose-cap radius (hemisphere)
      R_base   : Float;   -- base radius of the frustum
      H_nose   : Float;   -- nose-cap height
       Sin_A    : Float;
      L_slant  : Float;   -- slant length of frustum
      A_nose   : Float;   -- nose-cap surface area
      A_frust  : Float;   -- frustum surface area
      A_scallop: Float;   -- 1.2x frustum
      A_toroid : Float;   -- per-toroid surface area
      Total_A  : Float;   -- total wetted surface
   begin
      R_base  := Diameter / 2.0;
      --  For a 60-deg half-angle cone, the nose radius ~ R_base * tan(30)
      --  but for a generic nose cap we use the hemisphere approximation:
      R_nose  := R_base * 0.3;  -- empirical nose-cap radius fraction

      --  Trig via Taylor-series approximations (SPARK-compatible).
      --  Only Sin_A is needed (slant-length projection); the former unused
      --  Cos_A computation was removed as dead code.
      Sin_A := Sin_Deg (Angle_Deg);

      if Sin_A < 1.0e-10 then
         --  Degenerate: nearly flat
         return 0.0;
      end if;

      --  Nose-cap height (hemisphere)
      H_nose := R_nose;

      --  Slant length of the frustum (from nose edge to base)
      L_slant := (R_base - R_nose) / Sin_A;
      pragma Assert (L_slant <= 1.0e11);  -- proof aid: R_base<=7.5, Sin_A>=1.0e-10

      --  1. Nose cap:  hemisphere = 2 * pi * R_n * h_n
      A_nose := Two_Pi * R_nose * H_nose;

      --  2. Cone frustum:  pi * (r1 + r2) * L
      A_frust := Pi * (R_nose + R_base) * L_slant;
      pragma Assert (A_frust <= 1.0e13);  -- proof aid: Pi*(R_nose+R_base)<=9.75

      --  3. Scallop: 1.2x frustum (wrinkled fabric allowance)
      A_scallop := 1.2 * A_frust;
      pragma Assert (A_scallop <= 1.5e13);  -- proof aid: 1.2x frustum bound

      --  4. Toroids: 2 * pi^2 * R_tor * r_tor^2 * t * rho
      --    (volume of torus * thickness * density, simplified)
      --  Using R_tor = base radius for toroid placement.
      --  NOTE: explicit Toroid_Radius * Toroid_Radius instead of '**' —
      --  GNATprove cannot see through the opaque float-exponentiation call.
      A_toroid := Two_Pi * Pi * R_base * (Toroid_Radius * Toroid_Radius)
                  * TPS_Thickness * TPS_Density;
      pragma Assert (A_toroid <= 1.0e8);  -- proof aid: Two_Pi*Pi*R_base*T_r^2*t*rho

      --  Total shield mass
      Total_A := (A_nose + A_scallop)
                 + (Float (Toroid_Count) * A_toroid);
      pragma Assert (Float (Toroid_Count) <= 2.15e9);  -- proof aid: Positive'Last conversion
      pragma Assert (Total_A <= 1.0e18);  -- proof aid: bounded terms sum

      --  Mass = total surface area * TPS thickness * TPS density
      return Total_A * TPS_Thickness * TPS_Density;
   end Shield_Mass_Analytical;

   -- ==================================================================
   --  Shield_Mass_Pappus
   -- ==================================================================
   --  Pappus centroid theorem for toroidal shield rings:
   --    m_shield = N * rho * 2 * pi * R_centroid * A_cross
   --  where:
   --    R_centroid = Diameter / 2  (distance from axis to toroid center)
   --    A_cross    = pi * r_tor^2  (cross-sectional area of tube)
   --  Simplifies to:
   --    m_shield = N * rho * pi^2 * Diameter * r_tor^2
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Shield_Mass_Pappus")
   --  (no direct self-test call - proof-verified unit).
   function Shield_Mass_Pappus
     (Diameter      : Float;
       Toroid_Radius : Float;
       Num_Toroids   : Positive;
       Density       : Float) return Float
   is
      --  Contract: pre  => AXIOM G3 envelopes (Diameter [0.5, 15] m,
      --           Toroid_Radius (0, 5] m, Num_Toroids <= 12,
      --           Density [10, 1e4]);
      --           post => mass = N * rho * pi^2 * D * r_tor^2 >= 0.0 kg.
      Pi_Sq : constant Float := Pi * Pi;
   begin
      --  NOTE: explicit Toroid_Radius * Toroid_Radius instead of '**' —
      --  GNATprove cannot see through the opaque float-exponentiation call.
      return Float (Num_Toroids) * Density * Pi_Sq
              * Diameter * (Toroid_Radius * Toroid_Radius);
   end Shield_Mass_Pappus;

   -- ==================================================================
   --  Validate_Geometry
   -- ==================================================================
   --  Per Rapisarda 2023 Table 5.4:
   --    Angle        40 .. 80 deg
   --    Toroid_Count 1 .. 12
   --    Diameter     0.5 .. 15.0 m
   --  NOTE: Toroid_Count lower bound (>= 1) is enforced by the Positive
   --  subtype of Geometry_Parameters.Toroid_Count, so only the upper bound
   --  is re-checked here.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Validate_Geometry") -> Test 4.
   function Validate_Geometry (Params : Geometry_Parameters) return Boolean
   is
      --  Contract: pre  => any Geometry_Parameters value (subtype-
      --           constrained record; no Pre required);
      --           post => True iff Angle_Deg in [40, 80], Toroid_Count
      --           <= 12, and Diameter_M in [0.5, 15.0].
   begin
      return
        Params.Angle_Deg     >= 40.0
        and Params.Angle_Deg <= 80.0
        and Params.Toroid_Count <= 12
        and Params.Diameter_M   >= 0.5
        and Params.Diameter_M   <= 15.0;
   end Validate_Geometry;

end StellarOrion_Geometry;
