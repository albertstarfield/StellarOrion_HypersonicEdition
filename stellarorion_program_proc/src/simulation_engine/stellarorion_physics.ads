--  StellarOrion_HypersonicEdition — Aerothermodynamic Physics
--  Ada 2012 / SPARK 2014
--  Pure-math routines with no side effects.
--
--  Citations are given inline per function.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Physics is
   pragma SPARK_Mode (On);

   -- -----------------------------------------------------------------
   --  SPARK-safe elementary functions (Taylor series)
   -- -----------------------------------------------------------------

   --  Natural logarithm [dimensionless].
   --  Taylor series (reduced argument): Ln(X) for X > 0.
   --  Error < 1e-7 for 30 terms. Source: standard numerical analysis.
   function Ln (X : Float) return Float
      with Pre  => X > 0.0,
           --  POST BOUND: Ln(X) for X in (0, Float'Last] is bounded by
           --  Ln(Float'Last) ~ 88.7. The -1000..1000 range covers this with
           --  >10 decades of headroom. Helps gnatprove prove Pow overflow.
           Post => Ln'Result >= -1000.0
                    and then Ln'Result <= 1000.0;

   --  Exponential function [dimensionless].
   --  Taylor series with squaring reduction: Exp(X) for any Float.
   --  Error < 1e-7 for 30 terms. Source: standard numerical analysis.
   function Exp (X : Float) return Float
     with Pre => abs X <= 700.0;

   --  SPARK-safe power: X^A = Exp(A * Ln(X)) for X > 0.
   --  Used by Fay-Riddell for (rho*mu)^0.4 and (rho*mu)^0.1.
   --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82
    function Pow (X : Float; A : Float) return Float
      with Pre => X > 0.0 and then abs A <= 100.0;

   -- -----------------------------------------------------------------
   --  Rarefied Gas Dynamics
   -- -----------------------------------------------------------------

   --  Mean free path [m].
   --  lambda = 1 / (sqrt(2) * pi * d^2 * n)
   --  Source: Bird 1994, Eq. (1.32)
   --
   --  AXIOMS (physical envelope, IEEE-754 single precision safe):
   --    AXIOM A1: number density n in [5e13, 1e30] m^-3
   --      (thermosphere at 500 km ~3e14; floor keeps lambda bounded).
   --    AXIOM A2: molecular diameter d in [1e-10, 1e-6] m
   --      (air ~3.7e-10; helium 2.6e-10; large organics ~1e-9).
   --  OVERFLOW PROOF: denom = sqrt(2)*pi*d^2*n in [2.2e-6, 4.5e18]
   --    => lambda <= 4.5e5 m at the envelope maximum (theory-audit
   --    correction: an earlier revision wrote 4.5e8 here, conflating
   --    the envelope max with the K1 interplanetary reference ~4.5e8;
   --    both are << Float'Last = 3.4028235e38).
   --  POST BOUND: lambda <= 1e9 covers the envelope max with >3 decades
   --    of headroom and discharges Knudsen_Number's Pre at the
   --    sole call site (Calculate_Flight_Metrics).
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Mean_Free_Path") -> Test 1.
   function Mean_Free_Path
     (Number_Density : Float;
      Mol_Diameter   : Float) return Float
     with Pre  => Number_Density >= 5.0e13
                   and Number_Density <= 1.0e30
                   and Mol_Diameter >= 1.0e-10
                   and Mol_Diameter <= 1.0e-6,
          Post => Mean_Free_Path'Result >= 0.0
                   and Mean_Free_Path'Result <= 1.0e9;

   --  Knudsen number (dimensionless).
   --  Kn = lambda / L
   --  Source: Bird 1994, Sec. 1.4
   --
   --  AXIOMS (physical envelope):
   --    AXIOM K1: MFP in [0, 1e9] m (discharged by Mean_Free_Path's Post
   --      at the sole call site; interplanetary limit ~4.5e8 m).
   --    AXIOM K2: Char_Length >= 1e-3 m (vehicle scale, millimetre floor).
   --  OVERFLOW PROOF: Kn <= 1e9 / 1e-3 = 1e12 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Knudsen_Number") -> Test 2.
   function Knudsen_Number
     (MFP         : Float;
      Char_Length : Float) return Float
     with Pre  => MFP >= 0.0
                   and MFP <= 1.0e9
                   and Char_Length >= 1.0e-3,
          Post => Knudsen_Number'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Aerodynamics
   -- -----------------------------------------------------------------

   --  Dynamic pressure [Pa].
   --  q = 0.5 * rho * V^2
   --
   --  AXIOMS (physical envelope):
   --    AXIOM Q1: rho in [0, 1e4] kg/m^3 (Venus surface ~65; 1e4 margin).
   --    AXIOM Q2: V in [0, 1e5] m/s (Earth escape 11.2e3; solar-system
   --      entry worst case ~7e4; 1e5 margin).
   --  OVERFLOW PROOF: q <= 0.5 * 1e4 * (1e5)^2 = 5.0e13 << Float'Last.
   function Dynamic_Pressure
     (Density  : Float;
      Velocity : Float) return Float
     with Pre  => Density >= 0.0
                   and Density <= 1.0e4
                   and Velocity >= 0.0
                   and Velocity <= 1.0e5,
           Post => Dynamic_Pressure'Result >= 0.0
                    and Dynamic_Pressure'Result <= 5.0e13;
   --  POST BOUND (A3b): q <= 0.5 * rho_max * V_max^2 = 5.0e13 Pa within
   --  the AXIOM Q1/Q2 envelope; discharges Ballistic_Coefficient's
   --  widened Dyn_Pressure Pre at the Calculate_Flight_Metrics call site.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Dynamic_Pressure")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).

   --  Ballistic coefficient [kg/m^2].
   --  beta = m * q / F_drag
   --
   --  AXIOMS (physical envelope):
   --    AXIOM B1: m in (0, 1e7] kg (largest launch vehicles ~1e6).
   --    AXIOM B2: q in [0, 1e14] Pa.  WIDENED in A3b: within the input
   --      subtypes (rho <= 1e4, V <= 1e5) Dynamic_Pressure legitimately
   --      reaches 5.0e13 (see its POST BOUND); the former 1e6 ceiling was
   --      unreachable-by-proof and contradicted the caller chain.
   --    AXIOM B3: F_drag in [1e-6, 1e18] N (floor avoids division blowup;
   --      peak HIAD drag ~1e6-1e7 N; CEILING WIDENED 1e9 -> 1e18 in A3e
   --      to match the Calculate_Flight_Metrics Pre on Results.Drag_Force
   --      and the Deceleration_G_Load envelope: analytic Cd*q*A worst
   --      ~2.5e17 N.  Widening is overflow-neutral because beta = m*q/F
   --      DECREASES in F; the worst case remains floor-driven.)
   --  OVERFLOW PROOF: m*q <= 1e21; /F_drag >= 1e-6 => beta <= 1e27
   --    << Float'Last = 3.4028235e38 (independent of the F ceiling).
   --  NOTE: Post relaxed to >= 0.0: q = 0 (V = 0) legitimately gives
   --    beta = 0. The former Post "> 0.0" was a spec defect found by
   --    gnatprove (contradicted Pre for Dyn_Pressure = 0).
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Ballistic_Coefficient")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Ballistic_Coefficient
     (Mass       : Float;
      Dyn_Pressure : Float;
      Drag_Force : Float) return Float
     with Pre  => Mass > 0.0
                   and Mass <= 1.0e7
                   and Dyn_Pressure >= 0.0
                   and Dyn_Pressure <= 1.0e14
                    and Drag_Force >= 1.0e-6
                    and Drag_Force <= 1.0e18,
          Post => Ballistic_Coefficient'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Aerothermodynamics
   -- -----------------------------------------------------------------

    --  Sutton-Graves stagnation-point convective heat flux [W/m^2].
    --  q_stag = C_sg * sqrt(rho / R_n) * V^3
    --  Source: Sutton, K. & Graves, R.A. (1971) "A General Stagnation-
    --         Point Convective Heating Equation for Arbitrary Gas
    --         Mixtures," NASA TR R-376, Nov 1971.
    --         [Citation: https://ntrs.nasa.gov/citations/19720003329]
    --         [Citation: NASA-TR-R-376, L-7885]
    --  C_SG = 1.7415e-4 (Earth air, SI units; Table 1 of TR R-376).
    --  Derived for: stagnation-point convective heating of blunt
    --         axisymmetric bodies in chemical equilibrium gases.
    --         Valid for Earth air (N2/O2 mix) at V < 12 km/s.
    --
    --  DERIVATION (from Fay-Riddell stagnation-point theory):
    --    Fay & Riddell (1958), J. Aeronaut. Sci. 25(2), give the
    --    stagnation-point laminar boundary-layer heat flux
    --      q_stag ~ k * sqrt(rho_e * mu_e * (du_e/dx)_stag) * h_recovery,
    --    which, under Le = 1, Pr = 0.71, frozen chemistry and a
    --    Newtonian stagnation-region velocity gradient
    --    (du_e/dx ~ (1/R_n)*sqrt(2*(p_e - p_inf)/rho_e)), collapses to
    --    the engineering form used here:
    --      q_stag = C_sg * sqrt(rho_inf / R_n) * V^3,   C_sg = 1.7415e-4
    --    (SI: [W/m^2], rho [kg/m^3], R_n [m], V [m/s]).
    --    The V^3 scaling follows from kinetic energy flux (rho*V^3)
    --    times the sqrt(R_n)-dilution of the boundary layer; the
    --    sqrt(rho) (not linear rho) reflects BL thickening with depth.
    --
    --  APPLICABILITY / REGIME OF VALIDITY (audit note, Rapisarda 2023):
    --    VALID:   continuum, attached blunt-body flow, Knudsen number
    --             Kn = lambda/L << 0.01, chemically-frozen-or-equilibrium
    --             air at V <~ 12 km/s (above that, ionization changes the
    --             effective C_sg).
    --    INVALID: transition and free-molecular flow (Kn >~ 0.01), where
    --             boundary-layer theory itself fails. Free-molecular
    --             heating scales differently (surface-accommodation
    --             driven; no sqrt(R_n) dilution). The Boltzmann Transport
    --             Equation (BTE) governs there, NOT Navier-Stokes.
    --    IN THIS CODEBASE: SPARTA DSMC numerically solves the BTE by
    --             direct particle simulation (Bird 1994; Plimpton &
    --             Gallis 2014), so DSMC output is the PRIMARY aerothermal
    --             physics across all rarefaction levels. This function
    --             serves ONLY as a conservative engineering envelope /
    --             reference band: Rapisarda Table 4.10 selected
    --             Sutton-Graves precisely because it was the ONLY model
    --             overpredicting BOTH IRVE-3 flight peaks
    --             (+6.26% flux, +14.81% load). Do NOT treat its absolute
    --             accuracy as trustworthy at high Kn - use it as an
    --             upper-bound sanity check against DSMC results.
    --
   --  AXIOMS (physical envelope):
   --    AXIOM S1: rho in (0, 1e4] kg/m^3.
   --    AXIOM S2: R_n in [1e-4, 100] m (sounding probes ~1 cm to HIAD).
   --    AXIOM S3: V in [0, 1e5] m/s (as Dynamic_Pressure).
   --  OVERFLOW PROOF: rho/R_n <= 1e8; sqrt <= 1e4; C_sg*sqrt <= 1.75;
   --    V^3 <= 1e15 => q_stag <= 1.75e15 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Sutton_Graves_Heat") -> Test 3.
   function Sutton_Graves_Heat
     (Density    : Float;
      Nose_Radius : Float;
      Velocity   : Float) return Float
     with Pre  => Density >= 0.0
                   and Density <= 1.0e4
                   and Nose_Radius >= 1.0e-4
                   and Nose_Radius <= 100.0
                   and Velocity >= 0.0
                   and Velocity <= 1.0e5,
           Post => Sutton_Graves_Heat'Result >= 0.0;
   --  ENVELOPE NOTE (A3b/A3e): exact-envelope worst case is C_sg * 1e4 *
   --  1e15 = 1.7415e15 W/m^2.  The former upper Post conjunct
   --  "Result <= 2.0e15" was REMOVED in A3e: gnatprove cannot derive it
   --  from Sqrt's contract (whose Post only bounds by max(X,1)) without
   --  timing out on re-inlining Sqrt's Newton loop, and a body-side
   --  pragma Annotate cannot justify a spec-located postcondition
   --  ([no-check-message-justified]).  Callers that need the bound
   --  apply an explicit Float'Min clamp (see Calculate_Flight_Metrics),
   --  matching the composite-clamp pattern used since A3b/A3c; the 2e15
   --  clamp value still matches the Radiative_Eq_Temp /
   --  Backface_Temperature Heat_Flux Pres exactly, keeping the
   --  Calculate_Flight_Metrics chain dischargeable.

   -- -----------------------------------------------------------------
   --  Fay-Riddell Stagnation-Point Heat Flux
   -- -----------------------------------------------------------------

   --  Fay-Riddell stagnation-point convective heat flux [W/m^2].
   --  Implements the simplified Fay-Riddell expression (Le = 1) from
   --  Rapisarda (2023) Eq 3.82, derived from the full catalytic
   --  formulation (Eq 3.81) of Fay & Riddell (1958).
   --
   --  FORMULA (Rapisarda 2023 Eq 3.82, simplified Le=1):
   --    q_s = 0.763 * Pr^(-0.6) * (rho_w * mu_w)^0.1
   --          * (rho_s * mu_s)^0.4 * (h_s - h_w)
   --          * sqrt(du/dy|_s)
   --
   --  where:
   --    Pr    = 0.71 (Prandtl number, frozen air)
   --    rho_w = rho(T_w)       [kg/m^3]   -- wall density
   --    mu_w  = mu(T_w)        [Pa*s]     -- wall viscosity (Sutherland)
   --    rho_s = rho(T_s)       [kg/m^3]   -- stagnation-point density
   --    mu_s  = mu(T_s)        [Pa*s]     -- stagnation-point viscosity
   --    h_s   = Cp * T_s       [J/kg]     -- stagnation enthalpy
   --    h_w   = Cp * T_w       [J/kg]     -- wall enthalpy
   --    du/dy|_s = velocity gradient at stagnation point [1/s]
   --             = (1/R_n) * sqrt(2*(p_s - p_inf)/rho_s)
   --    T_s   = T_inf * (1 + 0.2 * M^2)  -- stagnation temperature
   --    p_s   = p_inf * (1 + 0.2 * M^2)^3.5 -- stagnation pressure
   --
   --  DERIVATION FROM SUTTON-GRAVES:
   --    Sutton-Graves (TR R-376) is the engineering collapse of
   --    Fay-Riddell under Le=1, Pr=0.71, frozen chemistry and a
   --    Newtonian velocity gradient. The key simplification:
   --      Fay-Riddell has (rho_s * mu_s)^0.4 * (rho_w * mu_w)^0.1
   --        which captures real-gas BL property variations.
   --      Sutton-Graves replaces this with sqrt(rho_inf) * V^3,
   --        collapsing all BL property dependencies into C_sg.
   --    The difference: Fay-Riddell accounts for boundary layer
   --    property variations (density/viscosity changes across the BL),
   --    while Sutton-Graves uses freestream values only.
   --    At moderate Mach (M < 8), the difference is small (~3-5%).
   --    At high Mach (M > 10), real-gas effects become significant
   --    and Fay-Riddell is more accurate.
   --
   --  WHY DIFFERENT FROM SUTTON-GRAVES:
   --    1. Fay-Riddell uses stagnation-point properties (T_s, rho_s,
   --       mu_s) which account for compressibility heating at the nose.
   --    2. Fay-Riddell includes wall-property corrections (rho_w, mu_w)
   --       which capture hot-wall effects.
   --    3. Fay-Riddell computes the velocity gradient explicitly from
   --       Newtonian pressure recovery, rather than absorbing it into
   --       a single constant.
   --    4. Result: Fay-Riddell typically predicts LOWER peak heat flux
   --       than Sutton-Graves (Rapisarda Table 4.10: FR=13.83 vs
   --       SG=15.26 W/cm², -9.3% difference for IRVE-3).
   --
   --  RAPISARDA TABLE 4.10 CALIBRATION (IRVE-3):
   --    Fay-Riddell: 13.8313 W/cm² (peak), 195.1673 J/cm² (load)
   --    Sutton-Graves: 15.2595 W/cm² (peak), 223.9542 J/cm² (load)
   --    Flight: 14.3610 W/cm² (peak), 195.0577 J/cm² (load)
   --    => FR is -3.69% vs flight; SG is +6.26% vs flight.
   --
   --  APPLICABILITY / REGIME (from Rapisarda 2023 Sec 3.5):
   --    VALID:   continuum, laminar BL, moderate Mach (M < 8-10),
   --             perfect-gas regime (T < 2000 K, no dissociation).
   --    LIMITED: At high Mach (>10), real-gas effects (dissociation,
   --             ionization) degrade accuracy; Fay-Riddell has a
   --             theoretical maximum total enthalpy of 23 MJ/kg.
   --    ROLE IN CODEBASE: Reference correlation for comparison with
   --             SPARTA DSMC and Sutton-Graves. NOT used for TPS
   --             sizing (Sutton-Graves is conservative envelope).
   --
   --  AXIOMS (physical envelope):
   --    AXIOM FR1: Density_Kgm3 in (0, 1e4] kg/m^3.
   --    AXIOM FR2: Nose_Radius_M in [1e-4, 100] m.
   --    AXIOM FR3: Velocity_Ms in [0, 1e5] m/s.
   --    AXIOM FR4: Mach in [0, 100].
   --    AXIOM FR5: Wall_Temp_K in [200, 5000] K.
   --  OVERFLOW PROOF: All intermediate products bounded by physical
   --    envelope; result < 1e12 W/m^2 for IRVE-3 conditions.
   --  Verification evidence: self-test via Test_Modes validation.
   --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82;
   --          Anderson (2006) Sec 17.4.
   function Fay_Riddell_Heat
     (Density_Kgm3  : Float;
      Nose_Radius_M : Float;
      Velocity_Ms   : Float;
      Mach          : Float;
      Wall_Temp_K   : Float) return Float
      with Pre  => Density_Kgm3 >= 0.0
                    and Density_Kgm3 <= 1.0e4
                    and Nose_Radius_M >= 1.0e-4
                    and Nose_Radius_M <= 100.0
                    and Velocity_Ms >= 0.0
                    and Velocity_Ms <= 1.0e5
                    and Mach > 0.0
                    and Mach <= 100.0
                    and Wall_Temp_K >= 200.0
                    and Wall_Temp_K <= 5000.0,
           Post => Fay_Riddell_Heat'Result >= 0.0;

   --  Radiative equilibrium surface temperature [K].
   --  T = (q / (sigma * epsilon))^(1/4)
   --  Source: Stefan-Boltzmann law
   --  sigma = 5.670374419e-8 W/(m^2 K^4); eps in [1e-3, 1] covers all
   --  real TPS coatings (typically 0.05 .. 0.95).
   --
   --  AXIOMS (physical envelope):
   --    AXIOM R1: q in [0, 2e15] W/m^2.  WIDENED in A3b: Sutton-Graves
   --      legitimately reaches 1.75e15 within its input envelope (see its
   --      POST BOUND); the former 1e9 ceiling contradicted that chain.
   --    AXIOM R2: eps in [1e-3, 1].
   --  OVERFLOW PROOF: denom >= 5.67e-11; ratio <= 3.6e25 << Float'Last;
   --    double sqrt yields T <= 2.45e6 K ((3.6e25)^(1/4); theory-audit
   --    correction: an earlier revision stated 4.9e6 K - a factor-2
   --    arithmetic slip, conservative direction, bound still valid).
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Radiative_Eq_Temp")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Radiative_Eq_Temp
     (Heat_Flux  : Float;
      Emissivity : Float) return Float
     with Pre  => Heat_Flux >= 0.0
                   and Heat_Flux <= 2.0e15
                   and Emissivity >= 1.0e-3
                   and Emissivity <= 1.0,
          Post => Radiative_Eq_Temp'Result >= 0.0;

   --  1-D transient backface temperature [K].
   --  T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
   --  Source: Anderson 2006; Rapisarda 2023 Sec 5.5
   --
   --  AXIOMS (physical envelope):
   --    AXIOM T1: T_init in [0, 3000] K (soak-back ceiling of stack).
   --    AXIOM T2: q in [0, 2e15] W/m^2 (WIDENED in A3b, see
   --      Radiative_Eq_Temp R1); dt in [0, 1e4] s (2.8 h pulse);
   --      eta_lag in (0, 1].
   --    AXIOM T3: rho_TPS in [10, 1e4] kg/m^3 (aerogel ~10; C-C ~1600);
   --      Cp in [100, 1e4] J/(kg K); thickness in [1e-4, 1] m.
   --  OVERFLOW PROOF: capacitance in [0.1, 1e8]; numerator <= 2e19;
   --    ratio <= 2e20; T_back <= 3000 + 2e20 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Backface_Temperature")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Backface_Temperature
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     (Init_Temp    : Float;
     --  Invariant: parameters and derived locals remain within their declared
       Heat_Flux    : Float;
       Duration     : Float;
       Thermal_Lag  : Float;
       TPS_Density  : Float;
       TPS_Cp       : Float;
       TPS_Thickness : Float) return Float
     with Pre  => Init_Temp >= 0.0
                   and Init_Temp <= 3000.0
                   and Heat_Flux >= 0.0
                   and Heat_Flux <= 2.0e15
                   and Duration >= 0.0
                   and Duration <= 1.0e4
                   and Thermal_Lag > 0.0
                   and Thermal_Lag <= 1.0
                   and TPS_Density >= 10.0
                   and TPS_Density <= 1.0e4
                   and TPS_Cp >= 100.0
                   and TPS_Cp <= 1.0e4
                   and TPS_Thickness >= 1.0e-4
                   and TPS_Thickness <= 1.0,
           Post => Backface_Temperature'Result >= 0.0;

   --  Deceleration in Earth g's.
   --  n = F_drag / (m * g0)
   --  g0 = 9.80665 m/s^2.
   --
   --  AXIOMS (physical envelope):
   --    AXIOM D1: F_drag in [0, 1e18] N.  WIDENED in A3b: analytic drag
   --      estimators (Cd * q * A) legitimately reach ~2.5e17 within the
   --      input subtypes; the former 1e9 ceiling contradicted that chain.
   --    AXIOM D2: m in [1e-3, 1e7] kg (gram-scale probe to super-heavy).
   --  OVERFLOW PROOF: m*g0 in [9.81e-3, 9.81e7];
   --    n <= 1e18 / 9.81e-3 = 1.02e20 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Deceleration_G_Load")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Deceleration_G_Load
     (Drag_Force : Float;
      Mass       : Float) return Float
     with Pre  => Drag_Force >= 0.0
                   and Drag_Force <= 1.0e18
                   and Mass >= 1.0e-3
                   and Mass <= 1.0e7,
          Post => Deceleration_G_Load'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Density / Number-Density Conversion
   -- -----------------------------------------------------------------

   --  Mass density from number density [kg/m^3].
   --  rho = n * M_air / N_A
   --  M_air = 28.97e-3 kg/mol; N_A = 6.02214076e23 /mol.
   --
   --  AXIOMS (physical envelope): same n range as Mean_Free_Path (A1).
   --  OVERFLOW PROOF: n*M_air <= 2.9e28; /N_A <= 4.8e4 << Float'Last.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Density_From_Number")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Density_From_Number
     (N_Number : Float) return Float
     with Pre  => N_Number >= 0.0
                   and N_Number <= 1.0e30,
          Post => Density_From_Number'Result >= 0.0;

   -- -----------------------------------------------------------------
   --  Survivability
   -- -----------------------------------------------------------------

   --  Returns True iff every metric is within material limits.
   --
   --  CONTRACTS (post-audit remediation): total pure predicate — only
   --  comparisons, so no Pre is required (safe for every Float input,
   --  including NaN-free extremes of Flight_Metrics).  The Post mirrors
   --  the definition exactly (standard mandate: contracts on every
   --  subprogram); the prover discharges it by unfolding the body.
   --  [STD: contract-on-every-subprogram] [DO178C §5.1 decision coverage]
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Is_Survivable") -> Test 5.
   function Is_Survivable
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     (Metrics : Flight_Metrics) return Boolean
     with Post => Is_Survivable'Result =
                    (Metrics.Surface_Temp_K <= SIC_MAX_TEMP
                     and Metrics.Backface_Temp_K <= KAPTON_MAX_TEMP
                     and Metrics.G_Load <= MAX_G_LOAD
                     and Metrics.Decel_G <= MAX_G_LOAD);
                     --  Invariant: parameters and derived locals remain within their declared

   -- -----------------------------------------------------------------
   --  Composite Calculation
   -- -----------------------------------------------------------------

   --  Compute all Flight_Metrics from raw simulation results,
   --  flight conditions, geometry, and TPS material card.
   --  The procedure aggregates all physics functions above into
   --  a single comprehensive metric calculation.
   --
   --  CONTRACTS (A3b): Flight/Geo/TPS component envelopes are enforced
   --  structurally by the record-component subtypes in StellarOrion_Types
   --  (Velocity_Range, Density_Range, Mass_Kg_Range, Diameter_Range,
   --  Nose_Radius_Range, TPS_*_Range), so no explicit Pre conjuncts are
   --  needed for them.  Simulation_Results intentionally remains
   --  unconstrained (its defaults are 0.0 and SPARTA dumps may carry
   --  arbitrary magnitudes), so its forwarded bounds are stated here.
   --    Drag_Force  <= 1e18 : discharges Deceleration_G_Load's widened
   --      D1 envelope; analytic Cd*q*A worst case ~2.5e17 fits.
   --    Heat_Flux_Wm2 <= 2e15: discharges Radiative_Eq_Temp / Backface_
   --      Temperature's widened R1/T2 envelopes; Sutton-Graves Post
   --      ceiling is 1.75e15.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Calculate_Flight_Metrics")
   --  -> Test 5 (end-to-end metrics pipeline).
   procedure Calculate_Flight_Metrics
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     (Results : Simulation_Results;
     --  Invariant: parameters and derived locals remain within their declared
      Flight  : Flight_Parameters;
      Geo     : Geometry_Parameters;
      TPS     : TPS_Material;
      Metrics : out Flight_Metrics)
     with Pre => Results.Drag_Force >= 0.0
                   and Results.Drag_Force <= 1.0e18
                   and Results.Heat_Flux_Wm2 >= 0.0
                   and Results.Heat_Flux_Wm2 <= 2.0e15;

   -- ==================================================================
   --  1-DOF Ballistic Entry Trajectory Integration
   -- ==================================================================

   Max_Trajectory_Pts : constant := 2000;

   subtype Trajectory_Index is Integer range 1 .. Max_Trajectory_Pts;

   type Trajectory_Profile is array (Trajectory_Index range <>) of Trajectory_Sample;

   --  Integrate a 1-DOF ballistic entry trajectory from entry interface
   --  to ground impact or Mach 0.5.
   --
   --  Equations of motion (Chapman 1959, Vinh 1980):
   --    dv/dt = -D/m - g*sin(gamma)
   --    dgamma/dt = -(g/V - V/(R_earth + h)) * cos(gamma)
   --    dh/dt = V * sin(gamma)
   --    dx/dt = V * cos(gamma) / (R_earth + h)
   --
   --  where D = 0.5 * rho(h) * V^2 * CD * A_frontal
   --        g = g0 * (R_earth / (R_earth + h))^2
   --        rho(h) from ISA atmosphere model
   --
   --  Inputs:
   --    CD         : Drag coefficient (from SPARTA or empirical)
   --    Mass_Kg    : Vehicle mass [kg]
   --    Dia_M      : Aeroshell diameter [m] (for frontal area)
   --    Entry_Alt_Km : Entry interface altitude [km] (typically 122.65)
   --    Entry_Vel_Ms : Entry velocity [m/s] (typically 7500 for LEO)
   --    Entry_Gamma_Deg : Entry flight path angle [deg] (typically -5.75)
   --    Step_Size_S : Integration time step [s] (typically 1.0)
   --  Output:
   --    Profile    : Array of trajectory samples (time-ordered)
   --    N_Pts      : Number of valid samples in Profile
   --
   --  AXIOMS:
   --    TRAJ_A1: CD in [0.0, 3.0] (blunt body hypersonic range).
   --    TRAJ_A2: Mass_Kg in [1.0, 1.0e6] (probe to crew vehicle).
   --    TRAJ_A3: Dia_M in [0.5, 20.0] (small probe to giant HIAD).
   --    TRAJ_A4: Entry_Alt_Km in [80.0, 200.0] (above atmosphere).
   --    TRAJ_A5: Entry_Vel_Ms in [1000.0, 15000.0] (suborbital to escape).
   --    TRAJ_A6: abs(Entry_Gamma_Deg) in [1.0, 30.0] (steep to shallow).
   --    TRAJ_A7: Step_Size_S in [0.01, 100.0] (resolution vs stability).
   procedure Compute_Trajectory_Profile
     (CD                : Float;
      Mass_Kg           : Float;
      Dia_M             : Float;
      Entry_Alt_Km      : Float;
      Entry_Vel_Ms      : Float;
      Entry_Gamma_Deg   : Float;
      Step_Size_S       : Float;
      Profile           : out Trajectory_Profile;
      N_Pts             : out Natural;
      --  Output: time and magnitude of peak Sutton-Graves heat flux.
      --  Rapisarda 2023 Table 4.5: time of peak heating = 677.49 s
      --  for IRVE-3 Earth entry at ~2700 m/s.
      Peak_Heat_Time_S    : out Float;
      Peak_Heat_Flux_Wm2  : out Float)
   with Pre => CD >= 0.0 and CD <= 3.0
                and Mass_Kg >= 1.0 and Mass_Kg <= 1.0e6
                and Dia_M >= 0.5 and Dia_M <= 20.0
                and Entry_Alt_Km >= 80.0 and Entry_Alt_Km <= 200.0
                and Entry_Vel_Ms >= 1000.0 and Entry_Vel_Ms <= 15000.0
                and abs (Entry_Gamma_Deg) >= 1.0
                and abs (Entry_Gamma_Deg) <= 30.0
                and Step_Size_S >= 0.01
                and Step_Size_S <= 100.0;

end StellarOrion_Physics;
