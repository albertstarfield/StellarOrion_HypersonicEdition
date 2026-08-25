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
   --  Source: NASA TR R-376 (Sutton & Graves, 1972)
   --  C_SG = 1.7415e-4 (Earth, SI units; from StellarOrion_Types).
   --
   --  AXIOMS (physical envelope):
   --    AXIOM S1: rho in (0, 1e4] kg/m^3.
   --    AXIOM S2: R_n in [1e-4, 100] m (sounding probes ~1 cm to HIAD).
   --    AXIOM S3: V in [0, 1e5] m/s (as Dynamic_Pressure).
   --  OVERFLOW PROOF: rho/R_n <= 1e8; sqrt <= 1e4; C_sg*sqrt <= 1.75;
   --    V^3 <= 1e15 => q_stag <= 1.75e15 << Float'Last.
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
   function Backface_Temperature
     (Init_Temp    : Float;
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
   function Is_Survivable
     (Metrics : Flight_Metrics) return Boolean
     with Post => Is_Survivable'Result =
                    (Metrics.Surface_Temp_K <= SIC_MAX_TEMP
                     and Metrics.Backface_Temp_K <= KAPTON_MAX_TEMP
                     and Metrics.G_Load <= MAX_G_LOAD
                     and Metrics.Decel_G <= MAX_G_LOAD);

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
   procedure Calculate_Flight_Metrics
     (Results : Simulation_Results;
      Flight  : Flight_Parameters;
      Geo     : Geometry_Parameters;
      TPS     : TPS_Material;
      Metrics : out Flight_Metrics)
     with Pre => Results.Drag_Force >= 0.0
                   and Results.Drag_Force <= 1.0e18
                   and Results.Heat_Flux_Wm2 >= 0.0
                   and Results.Heat_Flux_Wm2 <= 2.0e15;

end StellarOrion_Physics;
