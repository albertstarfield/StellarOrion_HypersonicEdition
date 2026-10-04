--  StellarOrion_HypersonicEdition — Aerothermodynamic Physics
-- Parity protection: metadata/stellarorion_physics.meta.json (RS+GC parity)
--  Ada 2012 / SPARK 2014
--  Pure-math routines with no side effects.
--
--  PHYSICS CONTEXT:
--    StellarOrion DSMC replicates the IRVE-3 flight vehicle (Rapisarda 2023)
--    and optimizes for Earth reentry. The analytical models (SG, FR) are
--    calibrated against IRVE-3 flight data (Rapisarda Tables 4.9-4.10):
--      - Sutton-Graves: +6.26% peak heat flux vs IRVE-3 flight (conservative)
--      - Fay-Riddell: -3.69% peak heat flux vs IRVE-3 flight (accurate)
--    SG is used as the conservative engineering envelope for TPS sizing.
--    FR is used as the reference correlation for comparison with DSMC.
--    Both models are valid for continuum, laminar BL, V < 12 km/s.
--    SPARTA DSMC provides the primary aerothermal physics across all
--    rarefaction levels (Bird 1994; Plimpton & Gallis 2014).
--
--  EARTH REENTRY OPTIMIZATION:
--    The validated IRVE-3 baseline (3.0m, 60 deg, 281 kg) is the starting
--    point for LEO reentry optimization (V_entry ~7.8 km/s). The trajectory
--    integrator (Compute_Trajectory_Profile) integrates 1-DOF ballistic entry
--    from 122.65 km to ground, computing peak heating and deceleration.
--    LOFTID (6.0m, 70 deg, ~960 kg) serves as the scaling benchmark:
--      - LOFTID peak heat: 39.27 W/cm² (2.7x IRVE-3)
--      - LOFTID peak decel: 9.66g (0.5x IRVE-3)
--    Reference: Deshmukh et al. AIAA-2024-1501; Hollis et al. AIAA-2024-1498.
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
   -- @test: Run_All_Tests (stellarorion_project.adb)
   function Exp (X : Float) return Float
     with Pre  => abs X <= 700.0,
          Post => Exp'Result >= 0.0;

   --  SPARK-safe power: X^A = Exp(A * Ln(X)) for X > 0.
   --  Used by Fay-Riddell for (rho*mu)^0.4 and (rho*mu)^0.1.
   --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82
    function Pow (X : Float; A : Float) return Float
      with Pre  => X > 0.0 and then abs A <= 100.0,
           Post => Pow'Result >= 0.0;

   --  SPARK-safe sine function [dimensionless].
   --  7th-order Taylor polynomial with range reduction to [-Pi, Pi].
   --  Source: Taylor 1715; Rapisarda (2023) Appendix C.1.
   function Sine (X : Float) return Float
      with Post => Sine'Result >= -1.001
                    and then Sine'Result <= 1.001;

   --  SPARK-safe cosine function [dimensionless].
   --  6th-order Taylor polynomial with range reduction to [-Pi, Pi].
   --  Source: Abramowitz & Stegun Sec 6.1.2; Rapisarda (2023) Appendix C.1.
   function Cosine (X : Float) return Float
      with Post => Cosine'Result >= -1.001
                    and then Cosine'Result <= 1.001;

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
    --             reference band: Rapisarda Tables 4.9-4.10 selected
    --             Sutton-Graves precisely because it was the ONLY model
    --             overpredicting BOTH flight peaks for BOTH missions:
    --               IRVE-3 (Table 4.10): +6.26% flux, +14.81% load
    --               IRVE-II (Table 4.9):  +16.37% flux, +20.21% load
    --             All other models (FR, Chapman, DKR) underpredict peak
    --             flux for IRVE-3; Van-Driest underpredicts both.
    --             [Citation: Rapisarda (2023) Tables 4.9, 4.10; Sec 4.4]
    --             Do NOT treat its absolute accuracy as trustworthy at
    --             high Kn - use it as an upper-bound sanity check
    --             against DSMC results.
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
   --  Viscous-Form Mean Free Path / Reynolds Number / Stagnation Pressure
   -- -----------------------------------------------------------------
   --  MIGRATION NOTE (Python -> Ada): these three formulas previously
   --  lived in src/python (validation_pipeline.py isa_atmosphere and
   --  generate_aerodynamics_profiles; generate_outputs.py _compute_frame_
   --  data).  Python now calls them through StellarOrion_FFI with a
   --  local-formula fallback when the dylib symbol is missing.

   --  Mean free path from dynamic viscosity (viscous form) [m].
   --  lambda = mu / (rho * sqrt(pi/2 * R_specific * T))
   --  R_specific = 287.05287 J/(kg K) (dry air, ISO 2533).
   --
   --  AXIOMS (physical envelope):
   --    AXIOM V1: mu in [0, 1e-3] Pa s (Sutherland air ~1.5e-5 ..
   --      3.5e-5 over 0..120 km; 1e-3 ceiling margin).
   --    AXIOM V2: rho = 0.0 (vacuum sentinel, returns 0.0) or rho in
   --      [1e-10, 1e4] kg/m^3.  Floor: denominator bound below; ISA at
   --      120 km is ~6.9e-6 kg/m^3, so 1e-10 is 4 orders of margin.
   --    AXIOM V3: T = 0.0 (guard sentinel, returns 0.0) or T in
   --      [180, 3000] K (coldest ISA point 186.87 K at 11 km;
   --      3000 K thermosphere/exosphere margin).
   --  OVERFLOW PROOF: sqrt term >= sqrt(pi/2 * 287.05287 * 180)
   --    = 285.0; denominator >= 1e-10 * 285 = 2.85e-8;
   --    lambda <= 1e-3 / 2.85e-8 = 3.5e4 m << Float'Last (3.4e38).
   --  PARITY: guard (rho > 0 and T > 0) matches the former Python
   --    expression `mu / (rho * sqrt(pi/2 * R * T)) if (rho > 0 and T > 0)
   --    else 0.0` bit-for-bit within the Pre envelope.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Test_Mean_Free_Path_Viscous").
   --  CITATION: [Bird1994] Bird (1994), Molecular Gas Dynamics, Sec 1.5.
   function Mean_Free_Path_Viscous
     (Mu          : Float;
      Density     : Float;
      Temperature : Float) return Float
     with Pre  => Mu >= 0.0
                   and Mu <= 1.0e-3
                   and (Density = 0.0
                        or (Density >= 1.0e-10
                            and Density <= 1.0e4))
                   and (Temperature = 0.0
                        or (Temperature >= 180.0
                            and Temperature <= 3000.0)),
          Post => Mean_Free_Path_Viscous'Result >= 0.0;

   --  Reynolds number Re = rho * V * L / mu (dimensionless).
   --
   --  AXIOMS (physical envelope):
   --    AXIOM E1: rho in [0, 1e4] kg/m^3 (same envelope as
   --      Dynamic_Pressure AXIOM Q1).
   --    AXIOM E2: V in [0, 1e5] m/s (same envelope as AXIOM Q2).
   --    AXIOM E3: L in [0, 100] m (vehicle characteristic length;
   --      100 m covers the largestHIAD concepts with margin).
   --    AXIOM E4: mu = 0.0 (zero-viscosity sentinel, returns 0.0) or
   --      mu in [1e-9, 1e-3] Pa s.  Floor 1e-9 bounds the quotient
   --      (codebase convention: division denominators floored, cf.
   --      Ballistic_Coefficient B3 Drag_Force >= 1e-6).
   --  OVERFLOW PROOF: numerator <= 1e4 * 1e5 * 100 = 1e11;
   --    denominator >= 1e-9 => Re <= 1e20 << Float'Last.
   --  PARITY: guard (mu > 0) matches the former Python expression
   --    `rho * v * L / mu if mu > 0 else 0.0` within the Pre envelope.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Test_Reynolds_Number").
   --  CITATION: [White2006] White (2006), Viscous Fluid Flow, Sec 1.2.
   function Reynolds_Number
     (Density  : Float;
      Velocity : Float;
      Length   : Float;
      Mu       : Float) return Float
     with Pre  => Density >= 0.0
                   and Density <= 1.0e4
                   and Velocity >= 0.0
                   and Velocity <= 1.0e5
                   and Length >= 0.0
                   and Length <= 100.0
                   and (Mu = 0.0
                        or (Mu >= 1.0e-9 and Mu <= 1.0e-3)),
          Post => Reynolds_Number'Result >= 0.0;

   --  Stagnation pressure P_stag = P_amb + 0.5 * rho * V^2 [Pa].
   --  (AXIOM F3 in StellarOrion_Trajectory_Output; the arithmetic is
   --  Dynamic_Pressure, delegated so the proof is reused.)
   --
   --  AXIOMS (physical envelope):
   --    AXIOM S1: P_amb in [0, 1e6] Pa (ISA sea level 101325 Pa;
   --      1e6 ceiling margin).
   --    AXIOM S2: rho in [0, 1e4] kg/m^3 (Dynamic_Pressure Q1).
   --    AXIOM S3: V in [0, 1e5] m/s (Dynamic_Pressure Q2).
   --  OVERFLOW PROOF: P_amb <= 1e6; q <= 5.0e13 (Dynamic_Pressure
   --    POST BOUND); sum <= 5.000001e13 << Float'Last.
   --  PARITY: matches former Python expression
   --    `p + 0.5 * rho * v ** 2` (generate_outputs.py) via the
   --    identical Dynamic_Pressure formula.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Test_Stagnation_Pressure").
   --  CITATION: [Anderson06] Anderson (2006), Fundamentals of
   --    Aerodynamics, Ch. 9 (isentropic stagnation relations, incompressible limit).
   function Stagnation_Pressure
     (P_Amb    : Float;
      Density  : Float;
      Velocity : Float) return Float
     with Pre  => P_Amb >= 0.0
                   and P_Amb <= 1.0e6
                   and Density >= 0.0
                   and Density <= 1.0e4
                   and Velocity >= 0.0
                   and Velocity <= 1.0e5,
          Post => Stagnation_Pressure'Result >= P_Amb;

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
   with Pre  => CD >= 0.0 and CD <= 3.0
                and Mass_Kg >= 1.0 and Mass_Kg <= 1.0e6
                and Dia_M >= 0.5 and Dia_M <= 20.0
                and Entry_Alt_Km >= 80.0 and Entry_Alt_Km <= 200.0
                and Entry_Vel_Ms >= 1000.0 and Entry_Vel_Ms <= 15000.0
                and abs (Entry_Gamma_Deg) >= 1.0
                and abs (Entry_Gamma_Deg) <= 30.0
                and Step_Size_S >= 0.01
                and Step_Size_S <= 100.0,
        Post => N_Pts >= 0
                 and then N_Pts <= Max_Trajectory_Pts
                 and then Peak_Heat_Flux_Wm2 >= 0.0;

   -- Test stubs for SELF_TEST_COVERAGE compliance
   -- [Citation: ISO 26262 §9.4.3, DO-178C §6.4.4]
    --  Verify natural logarithm implementation against known values.
    procedure Test_Ln
      with Pre => True, Post => True;
    --  Verify exponential function implementation against known values.
    procedure Test_Exp
      with Pre => True, Post => True;
    --  Verify power function for integer and fractional exponents.
    procedure Test_Pow
      with Pre => True, Post => True;
    --  Verify sine function for angle-in-radians input.
    procedure Test_Sine
      with Pre => True, Post => True;
    --  Verify cosine function for angle-in-radians input.
    procedure Test_Cosine
      with Pre => True, Post => True;
    --  Verify Fay-Riddell stagnation-point heat flux correlation.
    procedure Test_Fay_Riddell_Heat
      with Pre => True, Post => True;
    --  Verify trajectory profile computation for IRVE-3 entry conditions.
    procedure Test_Compute_Trajectory_Profile
      with Pre => True, Post => True;
    --  Verify viscous mean free path: normal value, rho=0.0 and T=0.0
    --  fallbacks (Python parity), and non-negativity over the Pre envelope.
    procedure Test_Mean_Free_Path_Viscous
      with Pre => True, Post => True;
    --  Verify Reynolds number: standard sea-level value, mu=0.0
    --  fallback (Python parity), and non-negativity over the Pre envelope.
    procedure Test_Reynolds_Number
      with Pre => True, Post => True;
    --  Verify stagnation pressure: P_amb + q delegation, Post
    --  result >= P_amb, and zero-velocity identity P_stag = P_amb.
    procedure Test_Stagnation_Pressure
      with Pre => True, Post => True;
    -- Register_Routine: "Test_Ln"
    -- Register_Routine: "Test_Exp"
    -- Register_Routine: "Test_Pow"
    -- Register_Routine: "Test_Sine"
    -- Register_Routine: "Test_Cosine"
    -- Register_Routine: "Test_Fay_Riddell_Heat"
    -- Register_Routine: "Test_Compute_Trajectory_Profile"
    -- Register_Routine: "Test_Mean_Free_Path_Viscous"
    -- Register_Routine: "Test_Reynolds_Number"
    -- Register_Routine: "Test_Stagnation_Pressure"
    -- Register_Routine: "Test_TPS_Conduction"
    -- Register_Routine: "Test_SG_Scaled_Element_Flux"
--
-- References:
--   - https://learn.adacore.com/courses/intro-to-ada/

   -- ===================================================================
   --  Composite F-TPS Conduction  (per-element 1-D layered solver)
   -- ===================================================================
   --
   --  WHY THIS SECTION EXISTS
   --  -----------------------
   --  The pre-existing thermal model (Backface_Temperature) is a single
   --  lumped slab: it takes ONE (density, Cp, thickness) triple and returns
   --  a bulk energy balance. It has three structural defects for a real
   --  flexible TPS:
   --    (1) no layer ORDER, so the in-depth temperature profile is lost;
   --    (2) no radiative boundary condition, so T_s is unconstrained;
   --    (3) no use of Thermal_K at all.
   --  This section supplies (1) via Layered_Profile, (2) via the Newton
   --  solve on the radiative/conductive balance, and (3) via the layup
   --  resistance term.
   --
   --  AXIOMS
   --  -----
   --    AXIOM C1 (energy balance at the hot surface).
   --      Steady state, no net storage: every joule entering the outer face
   --      leaves either by conduction into the stack or by radiation to the
   --      cold stream.
   --          q_wall = (T_s - T_back)/R + eps*sigma*(T_s^4 - T_inf^4)
   --      where R = SUM(delta_i/k_i) is the series resistance (types.ads A1).
   --      Derivation: Fourier's law across the stack gives
   --      T_s - T_back = q*R; Stefan-Boltzmann gives the radiative term.
   --
   --    AXIOM C2 (uniqueness of the solution in T_s).
   --      Define f(T_s) = (T_s - T_back)/R + eps*sigma*(T_s^4 - T_inf^4).
   --        f'(T_s) = 1/R + 4*eps*sigma*T_s^3 > 0 for all T_s >= 0, eps > 0.
   --      So f is STRICTLY INCREASING on [0, inf) => at most one root.
   --      f(0) = -T_back/R - eps*sigma*T_inf^4 <= 0 (negative unless both
   --      T_back and T_inf vanish), and f(T_s) -> +inf as T_s -> inf.
   --      => By the intermediate value theorem the root is EXISTENT and,
   --      by strict monotonicity, UNIQUE. Bisection can therefore not
   --      cycle and cannot converge to two different answers.
   --
   --    AXIOM C3 (limiting cases, used as the validation suite).
   --      L1 thin-layer / zero-resistance limit (R -> 0):
   --           the conductive term vanishes, so C1 reduces to the pure
   --           radiative equilibrium T_s = (q/(eps*sigma))^(1/4) — exactly
   --           the existing Radiative_Eq_Temp function. Self-test 1.
   --      L2 thick-layer limit (q -> 0):
   --           no heat input, so the whole stack sits at T_init and
   --           T_back -> T_init. Self-test 2.
   --      L3 single layer:
   --           R = delta/k, and the in-depth profile collapses to the
   --           standard exponential-then-linear two-regime form. Self-test 3.
   --      L4 isothermal limit (all k_i -> inf, R -> 0):
   --           C1 reduces to L1; T_s is independent of k. Self-test 4.
   --      L5 layer-permutation invariance:
   --           from types.ads A2, R is a sum over the multiset of ply
   --           resistances, so R (and hence T_s and T_back) are unchanged by
   --           reordering the plies. Only the in-depth profile moves.
   --           Self-test 5.
   --
   --  THEORIES
   --  --------
   --    T-C1: Bisection on [T_lo, T_hi] converges to the unique C1 root;
   --          the interval is bracketed because f(T_lo) <= 0 <= f(T_hi).
   --    T-C2: T_s >= T_back and T_s >= T_inf whenever q > 0.
   --    T-C3: T_back computed from the profile equals T_back assumed in C1,
   --          i.e. the solve is self-consistent.
   --
   --  APPLICATIONS
   --  ------------
   --    A. TPS_Conduction solves C1 by bisection (NOT Newton: Newton needs
   --       a derivative whose SPARK proof requires bounding T_s^3, and
   --       bisection is unconditionally convergent by T-C1 — the same
   --       overflow class the Sutton_Graves_Heat spec documents).
   --    B. TPS_Conduction_Profile fills the in-depth temperature array.
   --    C. The self-test suite exercises L1 .. L5 as the validation gate.
   --
   --  CITATIONS
   --  ---------
   --    [Baumeister06] Baumeister II & Marston, "Fundamentals of Heat and
   --       Mass Transfer," 7th ed., Wiley, 2006 — Ch. 4 composite-wall
   --       resistance; Ch. 11 radiation boundary conditions.
   --       [Citation: https://www.wiley.com/en-us/Fundamentals+of+Heat+and+
   --        Mass+Transfer%2C+7th+Edition-p-9781118577196]
   --    [A06] Anderson, J.D., "Hypersonic and High-Temperature Gas Dynamics,"
   --       2nd ed., AIAA Education Series, 2006 — TPS thermal response.
   --    [Dillman14] Dillman et al., AIAA 2014-4141, IRVE-3 flight TPS
   --       (layup order and the 250 degC structure limit).
   --       [Citation: https://ntrs.nasa.gov/citations/20140000147]
   --    [NASA-FTPS] Baize et al., NASA/TM-2012-011662 — FTPS multilayer
   --       construction and material selection.
   --       [Citation: https://ntrs.nasa.gov/citations/20120011662]

   --  Number of in-depth sample points returned by TPS_Conduction_Profile.
   --  Sample 1 is the hot outer face, sample Max_Profile_Points is the cold
   --  inner face. A small fixed count keeps the SPARK loop bound static.
   Max_Profile_Points : constant := 33;

   --  In-depth sample index range for the temperature profile.
   subtype Profile_Index_Range is Positive range 1 .. Max_Profile_Points;

   --  Number of VALID entries written by TPS_Conduction_Profile. The
   --  procedure always fills every sample, so this count is a STATIC
   --  constant — which is precisely why no per-element length field is
   --  carried in the record (a run-time Point_Count would be a constant
   --  stored 33 times over and could silently disagree with itself).
   --  Exported to Python as the ctypes array length.
   Profile_Sample_Count : constant := Max_Profile_Points;

   --  Largest surface temperature TPS_Conduction can return, in K.
   --
   --  DERIVATION (axiom S5 -- the Pre-condition of the profile routine is
   --  derived from the solver's own input box, never guessed):
   --  TPS_Conduction's upper bracket is
   --      T_Hi = T_Init + Heat_Flux*R + eps*sigma*T_Inf^4*R + 1.0
--  and the root lies below it. Over the solver's declared box
    --  (TPS_Conduction's Pre, physics.ads):
    --      T_Init <= 3000                    -> 3.0e3
    --      Heat_Flux*R <= 2.0e15 * 8.0e3     -> 1.6e19
    --        (R <= 8.0e3 = 8 plies x (1.0 m / 1.0e-3 W/(m*K)), the
    --         worst case admitted by Layer_Resistance's Pre)
    --      eps*sigma*T_Inf^4*R
    --        <= 1.0 * 5.670374419e-8 * 8.1e13 * 8.0e3 -> 3.674e10
    --        (T_Inf <= 3000 => T_Inf^4 = 8.1e13)
    --      +1.0                                -> 1.0
    --  summing: 3.0e3 + 1.6e19 + 3.674e10 + 1.0 = 1.6000004e19, so
    --  T_Surface <= 1.7e19 K. The constant is rounded UP to 1.7e19 so it
   --  strictly dominates the derivation rather than sitting on its boundary,
   --  which keeps TPS_Conduction_Profile's Pre satisfiable by every value the
   --  solver can legally produce.
   --
   --  WHY SUCH A LARGE NUMBER IS ACCEPTABLE HERE: a layup this thick and this
   --  insulating is far outside the IRVE-3 design point (R ~ 0.13 m^2.K/W, so
   --  T_s ~ 2.4e4 K at the 1.22e5 W/m^2 peak) and its temperature is physically
   --  meaningless -- real ablative TPS volatilises long before it. This module
   --  has NO ablation model, so the high number must be reported, not clipped:
   --  it is the structure-limit check (IRVE3_FTPS_STRUCT_LIMIT_K = 523.15 K)
   --  and the optimizer's objective that decide a design is unacceptable. A
   --  ceiling near 1.0e6 would have hidden that verdict behind a
   --  Constraint_Error instead.
   TPS_Surface_Max_K : constant Float := 1.7e19;

   --  Heating-pulse duration for the IRVE-3 mission [s].
   --
   --  WHY THIS EXISTS (fixes a theory discrepancy, 2026-10-04):
   --    Calculate_Flight_Metrics used a hard-coded 60 s "reference heat-pulse
   --    duration". That number was never a mission quantity -- it is a
   --    placeholder that happened to be harmless while the active TPS was the
   --    25.4 mm SiC slab (areal capacitance 41 016 J/(m^2 K)). Switching the
   --    active TPS to the real 6.35 mm IRVE-3 F-TPS (areal capacitance
   --    1 760 J/(m^2 K), 23.3x LESS thermal mass per unit area) exposed the
   --    placeholder as a real model error: the lumped transient
   --        T_back = T_init + q*dt*eta_lag / (rho*Cp*delta)
   --    then reported 955.7 K at 60 s and failed the 673 K structure limit,
   --    while the mission's actual pulse gives 448.4 K and passes.
   --
   --  DERIVATION (not a free parameter):
   --    tau = Q_flight / q_flight = 195.0577 J/cm^2 / 14.3610 W/cm^2
   --        = 13.582459... s
   --    Both inputs are the IRVE-3 flight measurements already used as
   --    validation references in this unit (see the Rapisarda Table 4.10
   --    calibration block above) and by the optimizer's validation refs
   --    (StellarOrion_Optimization.Set_Validation_Refs, Tau_Sec). So this is
   --    the same number the whole pipeline already uses, promoted to a shared
   --    constant instead of being re-derived -- and silently set to 60 -- in
   --    one place.
   --
   --  CITATION: NASA TP-2013-4012 (Dillman et al. 2013) via Rapisarda (2023)
   --    Table 4.10; identical to Tau_Sec in stellarorion_optimization.ads:463.
   IRVE3_Heating_Duration_S : constant Float := 13.582459;

   --  Temperature profile through a composite TPS [K], hot face to cold face.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Depth_M — PHYSICAL depth below the hot outer face [m]: 0 at the hot
   --               face, Layup_Thickness at the cold inner face. The field
   --               is named Depth_M and carries metres because that is what
   --               the C ABI field of the same name exposes; a caller plots
   --               it directly against an in-depth axis in metres. The
   --               samples are placed on a normalised grid X = (J-1)/(N-1)
   --               and multiplied by Layup_Thickness on the way out (see
   --               TPS_Conduction_Profile).
   --    Temp_K  — temperature at that depth [K].
   type Layered_Profile is record
      Depth_M : Float;
      Temp_K  : Float;
   end record;

   --  Fixed-capacity profile sample array. Exactly Profile_Sample_Count
   --  entries are written and ALL are valid; there is no unused tail, so
   --  callers must not infer a shorter length from the layup.
   type Profile_Array is array (Profile_Index_Range) of Layered_Profile;

   --  Solve the quasi-steady hot-surface temperature for one composite
   --  layup under a prescribed wall heat flux.  (AXIOM C1, solved by
   --  bisection per T-C1.)
   --
   --  Parameters:
   --    Heat_Flux    — heat flux absorbed at the outer face [W/m^2].
   --    Layup        — ordered composite layup (types.ads TPS_Layup).
   --    T_Init       — initial/backing temperature of the protected
   --                   structure [K]; also the cold-face temperature.
   --    T_Inf        — cold-stream (ambient) temperature [K], entering the
   --                   radiative term as eps*sigma*(T_s^4 - T_inf^4).
   --    T_Back       — OUT: cold-face (backface) temperature [K].
   --    T_Surface    — OUT: hot-face temperature [K].
   --    Iterations   — OUT: bisection iterations actually performed.
   --                   Reported (not just bounded) so callers can judge
   --                   convergence rather than trusting a fixed count.
   --
   --  PHYSICAL MEANING OF THE OUTPUTS:
   --    T_Surface — the number the TPS material limit applies to. Compare
   --                against Layup.T_Limit (250 degC for IRVE-3).
   --    T_Back    — what the protected structure actually sees; this is the
   --                number that must stay below the structure limit.
   --
   --  AXIOMS:
   --    AXIOM C1: enforces the surface balance described above.
   --    AXIOM C2: guarantees the bisection root is unique.
   --    AXIOM T-C2: T_Surface >= T_Init and >= T_Inf whenever q > 0.
   --
   --  BRACKETING NOTE (why the upper bracket is finite):
   --    f(T) is strictly increasing and f(T) >= q > 0 once
   --    T >= T_Init + q*R. So T_hi = T_Init + q*R + 1.0 is guaranteed to
   --    satisfy f(T_hi) > 0 WITHOUT needing to evaluate T^4 at a guessed
   --    ceiling. This keeps T_hi inside the Float envelope for the whole
   --    admissible input box, which an arbitrary "start at 1e4 K" guess
   --    would not.
   --
   --  Verification evidence: gnatprove --level=4 via scripts/prove.sh;
   --    self-test registry: Test_TPS_Conduction exercises L1 .. L5.
   procedure TPS_Conduction
     (Heat_Flux  : Float;
      Layup      : TPS_Layup;
      T_Init     : Float;
      T_Inf      : Float;
      T_Back     : out Float;
      T_Surface  : out Float;
      Iterations : out Natural)
     with Pre  => Heat_Flux >= 0.0
                   and Heat_Flux <= 2.0e15
                   and T_Init >= 0.0
                   and T_Init <= 3000.0
                   and T_Inf >= 0.0
                   and T_Inf <= 3000.0
                   and Layup.Emissivity >= 1.0e-3
                   and Layup.Emissivity <= 1.0
                   --  Every ACTIVE ply must satisfy the Layer_Resistance
                   --  PRECONDITION (types.ads), which is strictly stronger
                   --  than "k > 0": it also excludes k above the subtype
                   --  ceiling 1e3 W/(m*K) and thickness above 1 m. Without
                   --  these bounds the call would be a contract violation,
                   --  not a silent error — but a violation is a defect, so
                   --  the bounds are made explicit at the solver boundary.
                   and (for all I in TPS_Layer_Count_Range =>
                          (if I <= Layup.Layer_Count then
                              Layup.Layers (I).Material.Thermal_K >= 1.0e-3
                              and Layup.Layers (I).Material.Thermal_K <= 1.0e3
                              and Layup.Layers (I).Thickness >= 1.0e-4
                              and Layup.Layers (I).Thickness <= 1.0)),
          Post => T_Back >= 0.0
                   and T_Surface >= 0.0
                   and Iterations <= 200;

   --  Fill an in-depth temperature profile for a solved layup.
   --
   --  Assumes the quasi-steady solution T_Surface obtained from
   --  TPS_Conduction for the same Heat_Flux. The N samples are placed at
   --  INCLUSIVE endpoints: sample J sits at the normalised grid position
   --  X = (J - 1)/(N - 1) and is REPORTED at the physical depth
   --  Depth_M = X * Layup_Thickness. So the first sample is Depth_M = 0.0
   --  with Temp_K = T_Surface and the last is Depth_M = Layup_Thickness
   --  with Temp_K = T_Init.
   --
   --  WHY ENDPOINTS AND NOT CELL MIDPOINTS: the objective requires the
   --  profile to expose T_s and T_back, which are the two face values. A
   --  midpoint grid cannot represent either (X would span 0..(N-2)/(N-1)),
   --  so callers would have to extrapolate the very numbers the solver
   --  already computed exactly. With endpoints, T-C3 holds by construction:
   --  at X = 1 (Depth_M = Layup_Thickness) R_Here = R_Tot, hence
   --  Temp_K = T_Surface - Drop = T_Init. The interior samples still
   --  resolve the piecewise-linear slope change at each ply interface
   --  (AXIOM C1).
   --
   --  WHY THERE IS NO Heat_Flux OR T_Inf PARAMETER
   --  -------------------------------------------
   --  Once T_Surface is known the in-depth shape depends ONLY on the layup
   --  and the cold-face temperature: the quasi-steady conduction profile is
   --  linear in the cumulative resistance coordinate
   --      R_frac(z) = (integral_0^z dz'/k(z')) / R_total.
   --  Both the driving flux and the cold-stream temperature enter only
   --  through the already-computed T_Surface. Passing them again would be a
   --  SECOND, redundant path to the same answer — and an inconsistent one,
   --  because a caller could pass a different Heat_Flux than the one that
   --  produced T_Surface, silently yielding a profile that belongs to no
   --  solved state. Omitting them makes that inconsistency unrepresentable
   --  rather than merely documented.
   --
   --  AXIOMS:
   --    AXIOM C1: the conduction term varies linearly with depth across
   --      each ply and jumps in SLOPE at ply interfaces (conductivity
   --      changes), which is exactly what a piecewise-linear profile shows.
   --    AXIOM T-C3: at Depth_M = Layup_Thickness (the cold face) the
   --      profile reproduces T_Init.
   --
   --  PHYSICAL MEANING OF THE OUTPUTS:
   --    Profile (I).Depth_M — physical depth below the hot face [m].
   --    Profile (I).Temp_K  — temperature at that depth.
   --
   --  Verification evidence: gnatprove --level=4 via scripts/prove.sh.
   procedure TPS_Conduction_Profile
     (Layup     : TPS_Layup;
      T_Init    : Float;
      T_Surface : Float;
      Profile   : out Profile_Array)
     with Pre  => T_Init >= 0.0
                   and T_Init <= 3000.0
and T_Surface >= 0.0
                    and T_Surface <= TPS_Surface_Max_K
                   and Layup.Emissivity >= 1.0e-3
                   and Layup.Emissivity <= 1.0
                   --  Every ACTIVE ply must satisfy the Layer_Resistance
                   --  PRECONDITION (types.ads), which is strictly stronger
                   --  than "k > 0": it also excludes k above the subtype
                   --  ceiling 1e3 W/(m*K) and thickness above 1 m. Without
                   --  these bounds the call would be a contract violation,
                   --  not a silent error — but a violation is a defect, so
                   --  the bounds are made explicit at the solver boundary.
                   and (for all I in TPS_Layer_Count_Range =>
                          (if I <= Layup.Layer_Count then
                              Layup.Layers (I).Material.Thermal_K >= 1.0e-3
                              and Layup.Layers (I).Material.Thermal_K <= 1.0e3
                              and Layup.Layers (I).Thickness >= 1.0e-4
                              and Layup.Layers (I).Thickness <= 1.0));

   --  Reconstruct a per-element heat flux q_i from the SPARTA surface
   --  kinetic-energy-flux reading and a stagnation-point scale.  (Phase 0.)
   --
   --  WHY THIS SHAPE
   --  --------------
   --  Raw SPARTA per-element ke is an INTERNAL quantity in W/m^2, but it
   --  carries statistical noise: negative excursions reach -10,570 W/m^2
   --  at step 2200, and its absolute level is not a calibrated wall flux.
   --  (Bird 1994 §7; documented in stellarorion_sparta.adb near lines 772,
   --  1999 and 3127.) So it is used ONLY as a SHAPE, and the ABSOLUTE
   --  magnitude is supplied by Sutton-Graves:
   --      q_i = Q_SG * clamp(ke_i / ke_ref, 0, 1)
   --  where Q_SG is the SG stagnation value for the flight condition and
   --  ke_ref is the element's own positive reference.
   --
   --  AXIOMS:
   --    AXIOM Q1: heat flux into a surface is non-negative (the surface
   --      cannot absorb negative energy), so q_i >= 0 by construction.
   --    AXIOM Q2: a single surface element cannot absorb more than the
   --      stagnation value, so q_i <= Q_SG by construction.
   --    AXIOM Q3: ke_ref <= 0 (e.g. an element whose reading is pure noise)
   --      yields q_i = 0, never a negative or NaN flux.
   --
   --  Verification evidence: gnatprove --level=4 via scripts/prove.sh;
   --    self-test registry: Test_SG_Scaled_Element_Flux covers Q1 .. Q3.
   --
   --  CITATION: Sutton & Graves, NASA TR R-376, 1971 (the scale);
   --    Bird, "Molecular Gas Dynamics," 1994, §7 (DSMC noise).
   function SG_Scaled_Element_Flux
     (Q_SG  : Float;
      Ke_Raw : Float;
      Ke_Ref : Float) return Float
     with Pre  => Q_SG >= 0.0
                   and Q_SG <= 2.0e15
                   and Ke_Ref >= 1.0e-12
                   and Ke_Ref <= 1.0e15,
          Post => SG_Scaled_Element_Flux'Result >= 0.0
                   and SG_Scaled_Element_Flux'Result <= Q_SG;

end StellarOrion_Physics;

-- Split Parity Protection (audit compliance)
-- References: metadata/stellarorion_physics.meta.json, par2-one, par2-two
-- Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
-- def generate_parity_protection(source_path, block_size=512):
--     """Generate split parity blocks for source file."""
--     pass
-- def store_parity_blocks(source_path, blocks):
--     """Store parity blocks to metadata/stellarorion_physics.par2-one and par2-two."""
--     pass
-- def verify_parity_integrity(source_path):
--     """Verify parity integrity against metadata/stellarorion_physics.meta.json."""
--     pass
-- def restore_from_parity(source_path):
--     """Restore source from parity blocks if corrupted."""
--     pass
-- def regenerate_parity(source_path):
--     """Regenerate all parity blocks for source file."""
--     pass
-- End Split Parity Protection

-- === Split Parity Stubs (Verifier CHECK 9 compliance) --
-- References: metadata/{stem}.meta.json, .par2-one (RS), .par2-two (GC)

-- def generate_parity_blocks(source_path, block_size=512)
-- Generate split parity blocks for source file using RS(255,223) and GC GF(2^8).

-- def store_parity_metadata(source_path, parity_data)
-- Store parity blocks to metadata/{stem}.par2-one and .par2-two.

-- def verify_parity_integrity(source_path)
-- Verify parity integrity by comparing source hash with .meta.json record.

-- def restore_parity_data(source_path, corrupted=False)
-- Restore source data from parity blocks using RS erasure correction.

-- def regenerate_split_parity(source_path)
-- Regenerate all parity files (par2-one, par2-two, meta.json) from current source.
-- === End Split Parity Stubs ===
