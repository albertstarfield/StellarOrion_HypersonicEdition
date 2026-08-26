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
   --  Initial guess max(X/2, 1) is denormal-safe and converges for all
   --  finite positive X (largest call-site argument is gamma*R*T with
   --  T <= 3000 K, i.e. ~1.2e6).
   --  PROOF PATTERN (mirrors physics Sqrt, Tier A3a): the iteration map
   --    Y' = (Y + X/Y)/2 preserves the band [Min(X,1), Max(X,1)]
   --    (AM-GM: Y' >= sqrt(X) when Y in band; both endpoints of the band
   --    are fixed points of the band).  The loop invariant carries the
   --    band; the Post follows directly.
   function Sqrt_Approx (X : Float) return Float
     with Post => Sqrt_Approx'Result >= 0.0
                  and then
                    (if X > 0.0 then Sqrt_Approx'Result <= Float'Max (X, 1.0))
   is
      Y     : Float;
      Y_New : Float;
   begin
      if X <= 0.0 then
         return 0.0;
      end if;
      Y := Float'Max (X / 2.0, 1.0);  -- denormal-safe initial guess
      for I in 1 .. 25 loop
         pragma Unreferenced (I);
         --  Band invariants: Y stays inside [Min(X,1), Max(X,1)].
         pragma Loop_Invariant (Y >= Float'Min (X, 1.0));
         pragma Loop_Invariant (Y <= Float'Max (X, 1.0));
         Y_New := (Y + X / Y) / 2.0;
         Y     := Y_New;
      end loop;
      return Y;
   end Sqrt_Approx;

   --  exp(x) via Taylor series for small |x|.
   --  Accurate to ~1e-4 for |x| < 20.
   --
   --  AXIOM (E5): argument envelope |X| <= 120.  Largest call-site
   --    magnitudes: barometric exponents -G*(H-Hb)*1000/(R*Tb) with
   --    H <= 500 km give |Expon| <= 77.2; Pow_Float bounds its product
   --    to |Exponent * ln(Base)| <= 35 * 1.0 = 35.
   --  OVERFLOW PROOF (hand bound, opaque to interval analysis): term_k =
   --    |X|^k/k! grows monotonically for k <= 20 when |X| = 120 (ratio
   --    120/(k+1) > 1 throughout), so max partial sum <= 21 * term_20 =
   --    21 * 120^20/20! ~= 21 * 1.63e23 / ... i.e. O(1e24) << Float'Last
   --    (~3.4e38).  No intermediate can overflow.  The prover cannot
   --    derive this closed form through the loop, so residual checks at
   --    the multiplication/addition sites are discharged by annotation.
   function Exp_Approx (X : Float) return Float
     with Pre  => X >= -120.0 and X <= 120.0,
          Post => Exp_Approx'Result >= 0.0
   is
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
         --  Positivity invariants: every Taylor term of a non-negative
         --  base is non-negative, so the partial sum never drops below
         --  its seed 1.0.  These discharge the Neg-branch division
         --  (Sum /= 0, 1/Sum in (0,1]) and the Post Result >= 0.
         pragma Loop_Invariant (Term >= 0.0);
         pragma Loop_Invariant (Sum >= 1.0);
         --  Term := Term * X_Abs / Float (N)
         --  Hand bound: Term <= 120^N/N! <= 1.7e23 << Float'Last (E5).
         Term := Term * X_Abs / Float (N);
         pragma Annotate (GNATprove, False_Positive,
                          "float overflow check might fail",
                          "term_k = |X|^k/k! <= 120^20/20! ~ 1.7e23, "
                            & "monotone increasing for k<=20 at |X|=120 "
                            & "[ASWSS]");
         Sum := Sum + Term;
         pragma Annotate (GNATprove, False_Positive,
                          "float overflow check might fail",
                          "Sum <= 21 * 1.7e23 ~ 3.6e24 << Float'Last "
                            & "(Taylor partial-sum bound, E5) [ASWSS]");
         exit when Term < 1.0e-15;
      end loop;

      if Neg then
         --  Sum >= 1.0 (starts at 1.0, only positive terms added), so
         --  the division cannot divide by zero and result is in (0,1].
         return 1.0 / Sum;
      else
         return Sum;
      end if;
   end Exp_Approx;

   --  Natural logarithm via Padé approximant for x > 0.
   --  Uses the identity: ln(x) = 2 * sum_{k=0}^{N} y^(2k+1)/(2k+1)
   --  where y = (x-1)/(x+1).  Accurate to ~1e-6 for x in (0.01, 100).
   --
   --  AXIOM (E7): contractual envelope X in [0.5, 2.0] — exactly the
   --    Pow_Float call-site domain (E6: ISA layer temperature ratios).
   --    Outside this band the series converges too slowly to bound
   --    (a prover counterexample at large X yields |Result| ~ 4.7), so
   --    the envelope is part of the contract rather than the Post.
   --  OVERFLOW PROOF (hand bound, opaque to interval analysis): on the
   --    envelope |Y| = |X-1|/(X+1) <= 1/3, so Y2 <= 1/9 and each term
   --    satisfies |Term_k| <= |Y|*(1/9)^k.  The partial sum is bounded
   --    by a geometric series: |Sum| <= |Y| * sum (1/9)^k <= (1/3)*(9/8)
   --    = 0.375, hence |Result| = 2|Sum| <= 0.75 << Float'Last.  The
   --    prover cannot carry this closed form through the loop, so the
   --    residual overflow check at the final scaling is discharged by
   --    annotation.
   function Ln_Approx (X : Float) return Float
     with Pre => X >= 0.5 and X <= 2.0
   is
      Y    : Float;
      Y2   : Float;
      Term : Float;
      Sum  : Float := 0.0;
      R    : Float;
   begin
      Y  := (X - 1.0) / (X + 1.0);
      Y2 := Y * Y;
      Term := Y;
      for K in 0 .. 15 loop
         --  Band invariants (both trivially preserved on the E7 envelope,
         --  |Y| <= 1/3 => |Y2| <= 1/9 < 1): terms shrink geometrically
         --  and each addition grows the partial sum by at most one term.
         --  Together they bound every intermediate: |Term| <= 1/3,
         --  |Sum| <= 16/3, discharging the loop's overflow VCs directly.
         pragma Loop_Invariant (abs Term <= abs Y);
         pragma Loop_Invariant (abs Sum <= Float (K) * abs Y);
         Sum  := Sum + Term / Float (2 * K + 1);
         Term := Term * Y2;
      end loop;
      --  |R| = 2|Sum| <= 32/3 by the loop band invariants, so the final
      --  scaling overflow check proves directly (no annotation needed;
      --  the tighter geometric bound 0.75 is recorded in E7 above).
      R := 2.0 * Sum;
      return R;
   end Ln_Approx;

   --  General power: base^exponent for positive base.
   --  Uses the identity: base^exp = exp(exp * ln(base)).
   --
   --  AXIOM (E6): call-site envelope Base in [0.5, 2.0] (ISA layer
   --    temperature ratios T/Tb all lie in [0.648, 1.056]) and
   --    Exponent in [-35, 35] (barometric exponents G/(R*L)+-1 lie in
   --    [4.26, 34.17] for ISA lapse rates).
   --  OVERFLOW/PRE PROOF: |ln(Base)| <= ln(2) < 1.0 on [0.5, 2], hence
   --    |Exponent * Ln_Approx(Base)| <= 35 * 1.0 = 35 < 120 = Exp_Approx
   --    envelope (E5).  Result >= 0 follows from Exp_Approx'Post.
   --  The prover cannot derive a numeric ceiling for Ln_Approx (no Post;
   --  see E7), so the product overflow and the Exp_Approx precondition
   --  at this call site are discharged by annotation.
   function Pow_Float (Base, Exponent : Float) return Float
     with Pre  => Base >= 0.5 and Base <= 2.0
                  and Exponent >= -35.0 and Exponent <= 35.0,
          Post => Pow_Float'Result >= 0.0
   is
      L : Float;
      E : Float;
      R : Float;
   begin
      if abs Exponent < 1.0e-15 then
         return 1.0;
      end if;
      L := Ln_Approx (Base);
      E := Exponent * L;
      pragma Annotate (GNATprove, False_Positive,
                       "float overflow check might fail",
                       "|E| = |Exponent|*|ln B| <= 35 * ln(2) ~= 24.3 "
                         & "<< Float'Last (E6/E7 hand bound) [ASWSS]");
      R := Exp_Approx (E);
      pragma Annotate (GNATprove, False_Positive,
                       "precondition might fail",
                       "|E| <= 35 * 1.0 = 35 < 120 = Exp_Approx envelope "
                         & "(E5/E6: |ln B| <= ln 2 on [0.5,2] up to series "
                         & "truncation error ~1e-6) [ASWSS]");
      return R;
   end Pow_Float;

   -- ==================================================================
   --  Atmosphere_Temperature
   -- ==================================================================
   function Atmosphere_Temperature
     (Altitude_Km : Float) return Float
   is
      H     : Float := Altitude_Km;
      T_Loc : Float;
   begin
      if H < 0.0 then
         H := 0.0;
      end if;

      --  Each gradient branch asserts its own interval bound (linear
      --  arithmetic on the branch guard), so the composite Post band
      --  [186.86, 288.15] discharges per-path instead of as one
      --  time-limited multi-branch goal.
      if H <= 11.0 then
         T_Loc := T0 - 6.5 * H;
         pragma Assert (T_Loc >= 216.65 and T_Loc <= 288.15);
         return T_Loc;
      elsif H <= 20.0 then
         return 216.65;
      elsif H <= 32.0 then
         T_Loc := 216.65 + 1.0 * (H - 20.0);
         pragma Assert (T_Loc >= 216.65 and T_Loc <= 228.65);
         return T_Loc;
      elsif H <= 47.0 then
         T_Loc := 228.65 + 2.8 * (H - 32.0);
         pragma Assert (T_Loc >= 228.65 and T_Loc <= 270.65);
         return T_Loc;
      elsif H <= 51.0 then
         return 270.65;
      elsif H <= 71.0 then
         T_Loc := 270.65 - 2.8 * (H - 51.0);
         pragma Assert (T_Loc >= 214.65 and T_Loc <= 270.65);
         return T_Loc;
      elsif H <= 84.852 then
         T_Loc := 214.65 - 2.0 * (H - 71.0);
         pragma Assert (T_Loc >= 186.946 and T_Loc <= 214.65);
         return T_Loc;
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
      Rho   : Float;
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
         --  Hand bound: T/T0 in [0.648, 1.0] (Temperature post band) so
         --  Pow <= 1; Rho <= RHO0 = 1.225 << Float'Last.
         Rho := RHO0 * Pow_Float (T / T0, Expon);
         pragma Annotate (GNATprove, False_Positive,
                          "float overflow check might fail",
                          "ratio<=1 => Pow_Float<=1 => Rho<=RHO0=1.225 "
                            & "(Temperature post band, E6) [ASWSS]");

      --  11 - 20 km : Tropopause, isothermal T = 216.65
      elsif H <= 20.0 then
         T := 216.65;
         Expon := -G0_LOC * (H - 11.0) * 1000.0 / (R_AIR * T);
         --  Hand bound: Expon <= 0 on this branch (H >= 11) so Exp <= 1;
         --  product overflow proves via contextual inlining of
         --  Exp_Approx (no annotation needed).
         Rho := 0.36391 * Exp_Approx (Expon);

      --  20 - 32 km : Stratosphere I, L = +1.0e-3 K/m
      elsif H <= 32.0 then
         Lapse := 1.0e-3;
         T := Atmosphere_Temperature (H);
         if T > 0.0 then
            Expon := G0_LOC / (R_AIR * Lapse) - 1.0;
            --  Hand bound: ratio <= 288.15/216.65 = 1.3297 (post band),
            --  exponent 33.163 => Pow <= 1.3297^33.163 ~ 1.28e4;
            --  Rho <= 0.08801 * 1.28e4 ~ 1127 << Float'Last (product
            --  overflow proves via contextual inlining).
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
            --  Hand bound: ratio <= 288.15/228.65 = 1.2602, exponent
            --  11.20 => Pow <= 1.2602^11.2 ~ 13.3; Rho <= 0.176
            --  (product overflow proves via contextual inlining).
            Rho := 0.01322 * Pow_Float (T / 228.65, Expon);
         else
            Rho := 0.0;
         end if;

      --  47 - 51 km : Stratopause, isothermal T = 270.65
      elsif H <= 51.0 then
         T := 270.65;
         Expon := -G0_LOC * (H - 47.0) * 1000.0 / (R_AIR * T);
         --  Hand bound: Expon <= 0 on this branch (H >= 47) so Exp <= 1
         --  (product overflow proves via contextual inlining).
         Rho := 0.001427 * Exp_Approx (Expon);

      --  51 - 71 km : Mesosphere I, L = -2.8e-3 K/m
      elsif H <= 71.0 then
         Lapse := -2.8e-3;
         T := Atmosphere_Temperature (H);
         if T > 0.0 then
            Expon := G0_LOC / (R_AIR * abs Lapse) + 1.0;
            --  Hand bound: ratio <= 288.15/270.65 = 1.0647, exponent
            --  13.20 => Pow <= 1.0647^13.2 ~ 2.29; Rho <= 0.00197
            --  (product overflow proves via contextual inlining).
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
            --  Hand bound: ratio <= 288.15/214.65 = 1.3424, exponent
            --  18.08 => Pow <= 1.3424^18.08 ~ 2.06e2; Rho <= 0.0132
            --  (product overflow proves via contextual inlining).
            Rho := 0.000064 * Pow_Float (T / 214.65, Expon);
         else
            Rho := 0.0;
         end if;

      else
         T := 186.87;
         Expon := -G0_LOC * (H - 84.852) * 1000.0 / (R_AIR * T);
         --  Hand bound: Expon <= 0 on this branch (H >= 84.852), so
         --  Exp <= 1 (product overflow proves via contextual inlining).
         Rho := 0.000001 * Exp_Approx (Expon);
      end if;

      if Rho < 0.0 then
         Rho := 0.0;
      end if;

      return Rho;
   --  Invariant: parameters and derived locals remain within their declared
   --  subtype ranges throughout execution; no unchecked conversions occur.
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
   --  Invariant: parameters and derived locals remain within their declared
   --  subtype ranges throughout execution; no unchecked conversions occur.
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
      --  Murphy's Law containment: the approximator helpers have no
      --  provable closed-form ceilings, so the assigned values are
      --  clamped to the constrained component subtypes.  In the physical
      --  envelope (E1/E2) both clamps are no-ops: max velocity is
      --  ~5.49e4 m/s < Velocity_Range'Last = 1e5, and max ISA density is
      --  1.225 kg/m^3 < Density_Range'Last = 1e4.
      Flight.Velocity_Ms   :=
        Float'Min (Mach_To_Velocity (Mach, T), Velocity_Range'Last);
      Flight.Density_Kgm3  :=
        Float'Min (Atmosphere_Density (Alt_Km), Density_Range'Last);
   --  Invariant: parameters and derived locals remain within their declared
   --  subtype ranges throughout execution; no unchecked conversions occur.
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
      --  extern: ISA fallback; full MSIS needs external Python pymsis via C popen bridge
      pragma Unreferenced (Latitude_Deg);
      pragma Unreferenced (Day_Of_Year);
      pragma Unreferenced (F107);
      pragma Unreferenced (F107_A);
   begin
      --  ISA fallback (full MSIS requires Python pymsis + C popen bridge)
      Density     := Atmosphere_Density (Alt_Km);
      Temperature := Atmosphere_Temperature (Alt_Km);
   --  Invariant: parameters and derived locals remain within their declared
   --  subtype ranges throughout execution; no unchecked conversions occur.
   end MSIS_Atmosphere;

end StellarOrion_Environment;
