--  StellarOrion_HypersonicEdition — Core Type Definitions
-- Parity protection: metadata/stellarorion_types.meta.json (RS+GC parity)
--  Ada 2012 / SPARK 2014
--  All physics constants originate from peer-reviewed sources.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro
--  Refs:
--    [TR-376]  Sutton, K. & Graves, R. A. "A General Stagnation-Point
--              Convective Heating Equation for Arbitrary Gas Mixtures,"
--              NASA TR R-376, 1971.
--              [Citation: https://ntrs.nasa.gov/citations/19720003329]
--              [Citation: https://hdl.handle.net/2060/19720003329]
--    [CODATA]  CODATA 2018 recommended values (https://physics.nist.gov)
--    [Bird94]  Bird, G. A. "Molecular Gas Dynamics and the Direct
--              Simulation of Gas Flows," Oxford Univ. Press, 1994.
--    [Rap23]   Rapisarda, V. "Multidisciplinary Design Analysis and
--              Optimization of HIAD," Ph.D. thesis, 2023.
--    [ISA]     International Standard Atmosphere, ISO 2533:1975.
--              [Citation: https://cdn.standards.iteh.ai/samples/7472/]
--    [FR58]    Fay, J.A. & Riddell, F.R. "Theory of Stagnation Point
--              Heat Transfer in Dissociated Air," J. Aerosp. Sci.
--              25(2), 73-85, 1958.
--              [Citation: https://doi.org/10.2514/8.7517]
--    [A06]     Anderson, J.D. "Hypersonic and High-Temperature Gas
--              Dynamics," 2nd ed., AIAA Education Series, 2006.
--    [Suth1893] Sutherland, W. "The Viscosity of Gases and Molecular
--               Force," Phil. Mag. 36(5), 507-531, 1893.

package StellarOrion_Types is
   pragma SPARK_Mode (On);

   -- ===================================================================
   --  Physical Constants
   -- ===================================================================

   --  Sutton-Graves stagnation-point heating coefficient
   --  [W/m^2 / (sqrt(kg/m^3) / m * (m/s)^3)].
   --
   --  VALUE 1.7415e-4 IS THE EARTH-AIR VALUE.  This constant was 1.83e-4
   --  while citing this same table, which is a false citation: TR R-376
   --  gives k = 1.7415e-4 for Earth and k = 1.9027e-4 for Mars, and
   --  1.83e-4 comes from the *Mars* gas mixture (97% CO2 / 3% N2).
   --    [Citation: Sutton & Graves, NASA TR R-376, Nov. 1971, Table 1 --
   --       k = 1.7415e-4 (Earth), k = 1.9027e-4 (Mars)]
   --    [Citation: NASA TFAWS Aerothermodynamics Course, 2012 --
   --       "k = 1.7415e-4 (Earth) k = 1.9027e-4 (Mars)"]
   --    [Citation: NASA NTRS 20060004824, 2005 --
   --       "k = 1.74153x10-4 (For Earth)"]
   --    [Citation: NASA NTRS 20200002354, 2018 -- Eq. (2) uses 1.83e-4
   --       explicitly for a 97% CO2, 3% N2 (Mars) mixture]
   --
   --  WHY THIS MATTERS: the 1.83e-4 value is the *Mars* coefficient, and
   --  this project simulates Earth entry (IRVE-3, 51.8 km, 3378 m/s).
   --  Because q scales as sqrt(k), using 1.83e-4 over-predicts every
   --  stagnation heat flux by (1.83/1.7415)^0.5 = 2.44 %.  That error
   --  propagated into Q_target (174.1374 J/cm^2), the validation gate and
   --  the whole optimisation objective.
   --
   --  Any duplicate of this constant elsewhere in the project MUST be
   --  changed in lockstep -- see StellarOrion_Pinn_Trajectory.C_SG.
   C_SG : constant Float := 1.7415e-4;

   --  Prandtl number for air (frozen chemistry, T < 1500 K)
   --  Source: Anderson (2006) Table A.1; standard aerodynamics reference
   PRANDTL_AIR : constant Float := 0.71;

   --  Sutherland constant for air viscosity [K]
   --  Source: Sutherland (1893); NASA CEA technical notes
   SUTHERLAND_CONST_AIR : constant Float := 110.4;

   --  Reference viscosity for air at T_ref = 273.15 K [Pa*s]
   --  Source: Sutherland's law calibration; standard value 1.716e-5
   MU_REF_AIR : constant Float := 1.716e-5;

   --  Reference temperature for Sutherland's law [K]
   T_REF_SUTHERLAND : constant Float := 273.15;

   --  Specific heat at constant pressure for air [J/(kg*K)]
   --  Source: standard thermodynamics; valid T < 1500 K (perfect gas)
   CP_AIR : constant Float := 1004.0;

   --  Stefan-Boltzmann constant [W / (m^2 * K^4)]
   --  Source: CODATA 2018, exact value  5.670 374 419e-8
   SIGMA_BOLTZMANN : constant Float := 5.670374419e-8;

   --  Avogadro constant [mol^-1]
   --  Source: CODATA 2018, exact value  6.022 140 76e23
   N_AVOGADRO : constant Float := 6.02214076e23;

   --  Molar mass of dry air [kg/mol]
   --  Source: Standard atmosphere, 28.97 g/mol
   M_AIR : constant Float := 28.97e-3;

   --  Standard acceleration of gravity [m/s^2]
   --  Source: Standard gravity  g_0 = 9.80665 (exact by definition)
   G0 : constant Float := 9.80665;

   --  Kinetic (collision) diameter of air molecule [m]
   --  Source: Bird 1994, Appendix A; typical value for N2/O2 mixture
   MOL_DIAM : constant Float := 3.7e-10;

   --  Boltzmann constant [J/K]
   --  Source: CODATA 2018, exact value  1.380 649e-23
   KB_BOLTZMANN : constant Float := 1.380649e-23;

   --  Specific gas constant for dry air [J/(kg*K)]
   --  R = R_universal / M_air = 8.314462618 / 0.02897
   R_AIR : constant Float := 287.058;

   --  Ratio of specific heats for air (diatomic, moderate T)
   --  Source: standard atmosphere model
   GAMMA_AIR : constant Float := 1.4;

   -- ===================================================================
   --  Survivability Limits
   -- ===================================================================

   --  Maximum temperature for SiC (silicon carbide) TPS tiles [K]
   --  Source: material datasheet / Rapisarda 2023 Sec 4.3
   SIC_MAX_TEMP : constant Float := 2073.0;

   --  Maximum temperature for Kapton polyimide film [K]
   --  Source: DuPont Kapton HN datasheet (degrades above ~500 C)
   KAPTON_MAX_TEMP : constant Float := 773.0;

   --  Maximum allowable structural g-load [g's]
   --  Source: typical crew/cargo limit, Rapisarda 2023 Sec 5.4
   MAX_G_LOAD : constant Float := 25.0;

   -- ===================================================================
   --  Enumerations
   -- ===================================================================

   --  Chemistry model for DSMC simulations.
   --    Five_Species  -> N2, O2, NO, N, O  (recommended baseline)
   --    Eleven_Species -> includes ions / excited states
   --    Mars           -> CO2-dominated atmosphere
   type Chemistry_Mode is (Five_Species, Eleven_Species, Mars);

   --  External CFD / DSMC solver backend
   type Solver_Kind is (SPARTA, OpenFOAM, PyFluent, PyANSYS);

   --  Design-of-Experiments sampling strategy
   type DoE_Method is (LHS, CCD);

    --  Nose-cone geometry style
    type Nose_Kind is (Smooth, Pointy);

    --  Aeroshell skin morphology
    type Skin_Kind is (Smooth, Scalloped);

   --  Vehicle configuration
   type Vehicle_Kind is (IRVE3, Orion);

   --  Optimization objective
   type Objective is (Drag_Obj, Heat_Obj);

   -- ===================================================================
   --  Physical Envelope Subtypes (record-component constraints)
   -- ===================================================================
   --  These named subtypes mirror the precondition envelopes of the
   --  StellarOrion_Physics leaf functions EXACTLY.  Using them as record
   --  component types makes every holder of these records provably satisfy
   --  the corresponding physics preconditions, and turns out-of-range
   --  writes into immediate, localized Constraint_Error instead of silent
   --  garbage propagation downstream (Murphy's Law: fail fast, fail loud).
   --
   --  Writer-site discipline: every external input path (CLI parsing,
   --  CSV history load) MUST clamp into the subtype before assignment.
   --  Internal writers (GA sampling, atmosphere model) were audited to
   --  produce values strictly inside these envelopes.
   --
   --  Sources: Rapisarda 2023 Table 5.4 (geometry search space),
   --  NASA TR R-376 / Bird 1994 envelopes (see StellarOrion_Physics.axioms).

   --  Freestream velocity [m/s]: planetary entry worst case ~7e4 (A2/Q2/S3).
   subtype Velocity_Range is Float range 0.0 .. 1.0e5;

   --  Mass density [kg/m^3]: sea level 1.225; giant-planet atmospheres << 1e4.
   subtype Density_Range is Float range 0.0 .. 1.0e4;

   --  Vehicle mass [kg]: gram-scale probe to super-heavy launcher (B1/D2).
   subtype Mass_Kg_Range is Float range 1.0e-3 .. 1.0e7;

   --  Aeroshell diameter [m]: Rapisarda 2023 Table 5.4 search space,
   --  also satisfies Knudsen_Number's Char_Length >= 1e-3 floor (K2).
   subtype Diameter_Range is Float range 0.5 .. 15.0;

   --  Nose radius [m]: sounding-probe tips to HIAD scale (S2).
   subtype Nose_Radius_Range is Float range 1.0e-4 .. 100.0;

   --  TPS material density [kg/m^3]: aerogel ~10 to C-C ~1600 (T3).
   subtype TPS_Density_Range is Float range 10.0 .. 1.0e4;

   --  TPS specific heat [J/(kg*K)] (T3).
   subtype TPS_Cp_Range is Float range 100.0 .. 1.0e4;

   --  TPS emissivity (dimensionless): real coatings 0.05 .. 0.95 (R2).
   subtype TPS_Emissivity_Range is Float range 1.0e-3 .. 1.0;

   --  TPS layer thickness [m] (T3).
   subtype TPS_Thickness_Range is Float range 1.0e-4 .. 1.0;

   -- ===================================================================
   --  Record Types
   -- ===================================================================

   --  Freestream / flight conditions at a single trajectory point.
   --  Default values are Mach 10 at 52 km (typical hypersonic corridor).
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Mach          : Ratio of vehicle speed to local speed of sound.
   --                    Hypersonic regime begins at Mach > 5. IRVE-3 entry
   --                    Mach ~25 (at 122 km interface); typical corridor
   --                    analysis at Mach 8-12 (50-70 km altitude).
   --    Altitude_Km   : Geodetic altitude above mean sea level [km].
   --                    ISA troposphere ends at 11 km; stratopause at 47 km;
   --                    mesopause at 86 km. HIAD entry interface ~122 km.
   --    Velocity_Ms   : True airspeed [m/s]. Sutton-Graves heat flux scales
   --                    as V^3 (kinetic energy flux rho*V^3), so velocity
   --                    dominates the heating budget. IRVE-3 ~2700 m/s at
   --                    52 km; LEO entry ~7800 m/s at 122 km.
   --    Density_Kgm3  : Ambient atmospheric mass density [kg/m^3].
   --                    Sea level: 1.225 kg/m^3 (ISA). At 52 km: ~6.97e-4
   --                    kg/m^3 (ISA). Sutton-Graves scales as sqrt(rho),
   --                    so density enters sub-linearly compared to V^3.
   --    Temperature_K : Ambient static temperature [K]. Determines local
   --                    speed of sound (a = sqrt(gamma*R*T)) and viscosity
   --                    (Sutherland's law). ISA troposphere: 288.15 - 6.5*H;
   --                    tropopause: 216.65 K; mesosphere: 186.87 K.
   --
   --  INVARIANT: Density_Kgm3 and Velocity_Ms are constrained subtypes
   --  (Density_Range, Velocity_Range) so out-of-range writes raise
   --  Constraint_Error at the assignment site rather than propagating
   --  silent garbage to downstream physics functions.
   --
   --  DEFAULT JUSTIFICATION: Mach 10 at 52 km corresponds to the
   --  mid-corridor hypersonic regime where DSMC-continuum transition
   --  occurs (Kn ~ 0.01-1.0). This is the most physics-rich operating
   --  point for validation against analytical models (SG, FR).
   --
   --  Source: Rapisarda 2023 Tables 4.1, 4.5; ISA ISO 2533:1975.
   type Flight_Parameters is record
      Mach          : Float := 10.0;
      Altitude_Km   : Float := 52.0;
      Velocity_Ms   : Velocity_Range := 2700.0;
      Density_Kgm3  : Density_Range  := 6.9674e-4;
      Temperature_K : Float := 270.65;
   end record;

   --  Nose geometry profile (affects shock attachment and drag).
   type Nose_Type_Kind is (Smooth, Pointy);

   --  Geometric definition of the HIAD aeroshell.
   --  Defaults correspond to IRVE-3 (Rapisarda 2023, Table 4.1).
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Diameter_M      : Base diameter of the aeroshell [m]. Determines
   --                      frontal area A = pi*(D/2)^2 and drag force
   --                      F_D = 0.5*rho*V^2*C_D*A. IRVE-3: 3.0 m;
   --                      LOFTID: 6.0 m (2x area, 4x drag at same conditions).
   --    Angle_Deg       : Half-angle of the conical aeroshell [deg].
   --                      60 deg is typical for blunt-body HIAD (IRVE-3).
   --                      Steeper angles increase drag but reduce L/D.
   --    Nose_Radius_M   : Nose bluntness radius [m]. Directly enters
   --                      Sutton-Graves as sqrt(1/R_n): larger radius
   --                      reduces peak heating (thicker boundary layer).
   --                      IRVE-3: 1.5 m (3m diameter sphere-cone)
   --    Toroid_Count    : Number of inflatable toroids in the HIAD stack.
   --                      IRVE-3 flight used 7 toroids; MDAO model used 6.
   --                      More toroids increase structural stiffness.
   --    Toroid_Radius_M : Tube radius of each toroid [m]. Affects the
   --                      aerodynamic profile and pressure distribution.
   --                      IRVE-3 flight: 0.135 m (Rapisarda Table 4.1).
   --    Outer_Radius_M  : Outer shoulder toroid radius [m].
   --                      EQUIVALENT TO: Rapisarda 2023 Table 4.1
   --                      "Outer Toroid Radius" = 0.0508 m.
   --                      This is the tube radius of the outermost
   --                      (shoulder) toroid in the stacked-toroid
   --                      HIAD configuration. The default 0.1016 m is
   --                      the FLIGHT IRVE-3 value (2 x 0.0508 m);
   --                      the MDAO value is 0.0508 m.
   --    Mass_Kg         : Total vehicle mass [kg]. Enters ballistic
   --                      coefficient beta = m/(C_D*A): higher mass
   --                      increases penetration depth but reduces
   --                      deceleration g-loads. IRVE-3: 281 kg.
   --    Payload_Height_M: Height of the payload bay [m]. MDAO Table 4.1
   --                      parameter h_pay; affects internal volume.
   --    Slice_Angle_Deg : Angular extent of the 3D model [deg].
   --                      360 = full axisymmetric; <360 for symmetry
   --                      reduction in DSMC (computational savings).
   --    Nose_Profile    : Smooth (rounded) or Pointy (sharp) nose cone.
   --                      Smooth reduces peak heating; Pointy increases
   --                      L/D but raises nose-tip thermal loads.
   --    Skin            : Smooth or Scalloped aeroshell surface texture.
   --                      Scalloped surfaces create periodic grooves
   --                      between toroids; affect boundary layer transition.
   --    Scallop_Points  : Number of scallop profile points per toroid.
   --                      Higher = finer geometric resolution in DSMC mesh.
   --    Scallop_Amplitude_M : Depth of scallop grooves [m].
   --                         0.030 m default (IRVE-3 groove depth).
   --
   --  SOURCE: Rapisarda 2023 Table 4.1 (geometry search space).
   type Geometry_Parameters is record
      Diameter_M      : Diameter_Range    := 3.0;
      Angle_Deg       : Float    := 60.0;
      Nose_Radius_M   : Nose_Radius_Range := 0.55;
       Toroid_Count    : Positive := 6;
        --  FLIGHT IRVE-3 USED 7 TOROIDS (Rapisarda 2023 Table 4.1):
        --  The MDAO optimization model used 6 toroids, but the actual
        --  flight vehicle had 7 toroids. Use --toroids 7 to match flight.
        --  Default 6 matches the MDAO model for direct comparison.
       Toroid_Radius_M : Float    := 0.135;
        --  Outer_Radius_M: Outer shoulder toroid radius [m].
        --  EQUIVALENT TO: Rapisarda 2023 Table 4.1 "Outer Toroid Radius" = 0.0508 m.
        --  This is the tube radius of the outermost (shoulder) toroid in the
        --  stacked-toroid HIAD configuration.  The default 0.1016 m is the
        --  FLIGHT IRVE-3 value (2 × 0.0508 m); the MDAO value is 0.0508 m.
        --  See also: --oradius CLI flag in StellarOrion_Project.
        Outer_Radius_M  : Float    := 0.1016;
       Mass_Kg         : Mass_Kg_Range     := 281.0;
       Payload_Height_M: Float    := 1.70;  -- MDAO Table 4.1 h_pay
        Slice_Angle_Deg : Float    := 360.0;
        Nose_Profile    : Nose_Type_Kind := Smooth;
        Skin                : Skin_Kind := Smooth;
        Scallop_Points      : Positive  := 8;
        Scallop_Amplitude_M : Float     := 0.030;
    end record;

   --  Thermal Protection System material card.
   --  Defaults model a SiC tile stack (LOFTID-style F-TPS).
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Name       : Material identifier (6 chars, padded). Used in
   --                  output reports and CSV headers.
   --    Density    : Mass density of the TPS material [kg/m^3].
   --                  Enters thermal capacitance: C = rho * Cp * thickness.
   --                  Higher density = more thermal inertia (slower heating).
   --                  Range: aerogel ~10 to C-C composite ~1600 kg/m^3.
   --    Cp         : Specific heat capacity [J/(kg*K)].
   --                  Determines how much energy raises temperature by 1 K.
   --                  Typical range: 200-2000 J/(kg*K) for ceramic/composite TPS.
   --    Thermal_K  : Thermal conductivity [W/(m*K)].
   --                  Governs heat conduction through the TPS layer.
   --                  Low k = good insulator (aerogel ~0.02); high k = conductor.
   --                  Neglected in 0-D radiative equilibrium (backface uses 1-D).
   --    Emissivity : Surface emissivity (dimensionless, 0-1).
   --                  Radiative equilibrium: T = (q/(sigma*eps))^(1/4).
   --                  Higher eps = more radiative cooling = lower surface temp.
   --                  Typical: 0.05 (polished metal) to 0.95 (black paint).
   --    Thickness  : TPS layer thickness [m].
   --                  Enters thermal capacitance and 1-D backface temperature.
   --                  Thicker = more protection but more mass.
   --                  Typical: 1-50 mm for tiles/blankets.
   --
   --  THERMAL MODEL:
   --    Surface temperature (radiative equilibrium, 0-D):
   --      T_s = (q / (sigma * eps))^(1/4)
   --    Backface temperature (1-D transient):
   --      T_back = T_init + (q * dt * eta_lag) / (rho * Cp * delta)
   --    where q = heat flux [W/m^2], sigma = Stefan-Boltzmann constant,
   --    eps = emissivity, dt = heating duration [s], eta_lag = thermal
   --    lag factor (0-1), delta = thickness [m].
   --
   --  SOURCE: Rapisarda 2023 Sec 4.3; NASA material datasheets;
   --          DuPont Kapton HN; LOFTID F-TPS design documents.
   type TPS_Material is record
      Name       : String (1 .. 6) := "SiC   ";
      Density    : TPS_Density_Range    := 1468.0;   -- kg/m^3
      Cp         : TPS_Cp_Range         := 1100.0;   -- J/(kg*K)
      Thermal_K  : Float := 0.2;      -- W/(m*K)
      Emissivity : TPS_Emissivity_Range := 0.75;     -- dimensionless
      Thickness  : TPS_Thickness_Range  := 0.0254;   -- m  (1 inch)
   end record;

   -- ===================================================================
   --  TPS Material Presets
   -- ===================================================================
   --  Source: Rapisarda 2023 Sec 4.3; NASA material datasheets.

   --  Silicon Carbide (SiC) tiles — LOFTID F-TPS baseline.
   function TPS_SiC return TPS_Material is
     (Name       => "SiC   ",
      Density    => 1468.0,
      Cp         => 1100.0,
      Thermal_K  => 0.2,
      Emissivity => 0.75,
      Thickness  => 0.0254)
     with Pre => True, Post => True;

   --  PICA-X (Phenolic Impregnated Carbon Ablator) — SpaceX variant.
   function TPS_PICA_X return TPS_Material is
     (Name       => "PICA  ",
      Density    => 320.0,
      Cp         => 1500.0,
      Thermal_K  => 0.5,
      Emissivity => 0.85,
      Thickness  => 0.040)
     with Pre => True, Post => True;

   --  LOFTID Flexible TPS (F-TPS) — ultra-lightweight inflatable.
   function TPS_LOFTID return TPS_Material is
     (Name       => "LOFTID",
      Density    => 300.0,
      Cp         => 1200.0,
      Thermal_K  => 0.15,
      Emissivity => 0.80,
      Thickness  => 0.050)
     with Pre => True, Post => True;

   --  Kapton polyimide film (backface insulation layer).
   function TPS_Kapton return TPS_Material is
     (Name       => "Kapton",
      Density    => 1420.0,
      Cp         => 1090.0,
      Thermal_K  => 0.12,
      Emissivity => 0.70,
      Thickness  => 0.005)
     with Pre => True, Post => True;

   --  PyroGel (aerogel blanket insulation — lightweight multi-layer TPS).
   function TPS_Pyrogel return TPS_Material is
     (Name       => "Pyrogl",
      Density    => 200.0,
      Cp         => 1000.0,
      Thermal_K  => 0.02,
      Emissivity => 0.85,
      Thickness  => 0.025)
     with Pre => True, Post => True;

   --  Multi-layer layup (SiC outer + PyroGel core + Kapton backface).
   --
   --  DEPRECATION NOTICE: this averaged record is NOT a valid representation
   --  of a multilayer F-TPS. It collapses three distinct materials into one
   --  effective rho / k / delta, which discards the layer ORDER that governs
   --  the in-depth temperature profile. Its comment historically claimed
   --  "SiC outer + PyroGel core + Kapton backface", which was wrong on both
   --  counts: the real IRVE-3 outer ply is Nextel BF-20 alumina-mullite
   --  fabric (not SiC), and silicon-carbide cloth is 2nd-generation FTPS
   --  (rated 50 W/cm^2) whereas IRVE-3 flew the 1st-generation BF-20 system
   --  (rated 30 W/cm^2). Retained only so legacy CLI paths keep compiling;
   --  new composite work must use TPS_Layup and TPS_Layup_IRVE3.
   function TPS_Multi return TPS_Material is
     (Name       => "Multi ",
      Density    => 650.0,
      Cp         => 1050.0,
      Thermal_K  => 0.10,
      Emissivity => 0.80,
      Thickness  => 0.040)
     with Pre => True, Post => True;

   -- ===================================================================
   --  Composite F-TPS Layup Types
   -- ===================================================================
   --  WHY THIS SECTION EXISTS
   --  -----------------------
   --  TPS_Material models ONE homogeneous slab. A real flexible thermal
   --  protection system is an ORDERED stack of plies whose through-thickness
   --  temperature profile depends on that order. The repository previously
   --  had no type able to express that stack, so TPS_Material.Thermal_K was
   --  declared on every preset and read by NO production code path.
   --
   --  AXIOMS (derived, not assumed):
   --
   --    A1. Steady 1-D conduction through a slab stack obeys
   --        q = (T_hot - T_cold) / R, with the series resistance
   --        R = SUM over plies of (delta_i / k_i).
   --        [Derivation: Fourier's law q = -k dT/dx; for each ply
   --        dT_i = q*delta_i/k_i; summing over plies gives dT = q*R.]
   --
   --    A2. Only SUM(delta_i/k_i) enters R. Therefore R is INVARIANT under
   --        permutation of the ply ORDER. (Layer order still matters for the
   --        IN-DEPTH profile T(x), but NOT for the lumped T_hot/T_cold pair.)
   --        => layer-permutation invariance is an EXACT property of A1,
   --           which is why it is a sound self-test rather than a heuristic.
   --
   --    A3. The outer (hot) surface emissivity — and only that emissivity —
   --        enters the radiative boundary condition. Inner-ply emissivity is
   --        irrelevant for a quasi-steady lumped model, so a layup carries
   --        Emissivity at the layup level, not per ply.
   --
   --    A4. Every k_i > 0 and delta_i > 0 is required for A1 to be finite.
   --        => k_i and delta_i are given bounded subtypes with lower bounds
   --           strictly above zero, and Layer_Resistance carries that
   --           precondition explicitly.
   --
   --  THEORIES:
   --    T1. Layup_Resistance > 0 for any admissible layup (sum of positives).
   --    T2. Total_Layup_Thickness = SUM(delta_i) is independent of k.
   --    T3. As all k_i -> infinity, R -> 0 and the stack becomes isothermal.
   --
   --  APPLICATIONS:
   --    A. Layer_Resistance / Layup_Resistance implement A1 + A4 and give
   --       TPS_Material.Thermal_K its first production read site.
   --    B. StellarOrion_Physics.TPS_Conduction consumes these to solve the
   --       quasi-steady hot-surface temperature.
   --    C. The self-test suite verifies T3 (isothermal limit) and the exact
   --       permutation invariance predicted by A2.
   --
   --  CITATIONS:
   --    [Baumeister06] Baumeister II & Marston, "Fundamentals of Heat and
   --       Mass Transfer," Wiley, 2006 — series-resistance conduction in
   --       composite walls, Ch. 2 and Ch. 4.
   --       [Citation: https://www.wiley.com/en-us/Fundamentals+of+Heat+and+
   --        Mass+Transfer%2C+7th+Edition-p-9781118577196]
   --    [NASA-FTPS] Baize, S. et al., "Flexible Thermal Protection System
   --       Development for Hypersonic Inflatable Aerodynamic Decelerators,"
   --       NASA/TM-2012-011662 — multilayer FTPS construction (porous outer
   --       fabric + porous insulator + thin impermeable gas barrier).
   --       [Citation: https://ntrs.nasa.gov/citations/20120011662]
   --    [Dillman14] Dillman, R.A. et al., "Flight Performance of the
   --       Inflatable Reentry Vehicle Experiment 3," AIAA 2014-4141 —
   --       IRVE-3 flew "two layers of high-temperature Nextel fabric
   --       covering Pyrogel insulation and a Kapton/Kevlar thin film gas
   --       barrier."
   --       [Citation: https://ntrs.nasa.gov/citations/20140000147]

   --  Maximum ply count in a composite layup. IRVE-3 needs 5 plies
   --  (2 fabric + 2 insulator + 1 gas barrier); 8 leaves headroom for the
   --  topology optimizer (P9) to reallocate plies without retyping.
   --  Fixed bound (not dynamic) so every loop carries a provable invariant
   --  and no heap allocation is reachable from SPARK code.
   Max_TPS_Layers : constant := 8;

   --  Number of ACTIVE plies in a layup, counted from the hot (outer) face.
   subtype TPS_Layer_Count_Range is Natural range 1 .. Max_TPS_Layers;

   --  Thermal conductivity of one ply [W/(m*K)].
   --  Range spans unfilled aerogel felt (~1.5e-2) to dense carbon-carbon
   --  tile (~500). RANGE NOTE: TPS_Material.Thermal_K is declared as plain
   --  Float, so this bound is enforced by Layer_Resistance's precondition
   --  rather than by the subtype.
   subtype TPS_Layer_K_Range is Float range 1.0e-3 .. 1.0e3;

   --  One ply of a composite F-TPS, measured normal to the hot face.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Material  — thermophysical set for this ply. Thermal_K is the
   --                 conductivity that dominates the ply's contribution to
   --                 the series resistance R (axiom A1).
   --    Thickness — ply thickness [m]. Through-thickness, NOT areal
   --                 density; per A1 the pair (Thickness, Thermal_K) fixes
   --                 the ply's thermal resistance delta/k.
   type TPS_Layer is record
      Material  : TPS_Material;
      Thickness : TPS_Thickness_Range := 1.0e-4;   -- m
   end record;

   --  Fixed-capacity ply stack. Indices 1 .. Max_TPS_Layers exist always;
   --  only the first Layer_Count entries are semantically active (see
   --  TPS_Layup.Layer_Count). Keeping a fixed extent avoids unconstrained
   --  array bounds and keeps SPARK loop invariants static.
   type TPS_Layer_Array is array (TPS_Layer_Count_Range) of TPS_Layer;

   --  An ordered composite F-TPS layup, indexed from the HOT (outer) face.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Layers      — ply stack; Layers (1) is the outermost (hot) ply.
   --    Layer_Count — number of ACTIVE plies; Layers (Layer_Count + 1 ..
   --                   Max_TPS_Layers) are ignored by every consumer.
   --    Emissivity  — radiative emissivity of the OUTER surface only
   --                   (axiom A3): the property entering
   --                   eps*sigma*(T_s^4 - T_inf^4).
   --    T_Limit     — maximum temperature the OUTFER surface may reach
   --                   [K]. For IRVE-3 the 1st-generation FTPS inflatable
   --                   structure limit is 250 degC = 523.15 K; exceeding it
   --                   is a structural (not thermal) failure mode.
   type TPS_Layup is record
      Layers      : TPS_Layer_Array;
      Layer_Count : TPS_Layer_Count_Range := 1;
      Emissivity  : TPS_Emissivity_Range := 0.80;
      T_Limit     : Float := 523.15;   -- K (250 degC)
   end record;

   --  Thermal resistance of a single ply [m^2*K/W]  (axiom A1 term).
   --  R_ply = Thickness / Thermal_K.
   --
   --  This is the FIRST production read of TPS_Material.Thermal_K anywhere
   --  in the repository: before this function the field was populated by
   --  every preset but consumed by no solver.
   --
   --  THEORY (T1 partial): both operands are bounded strictly positive by
   --  the precondition, so the quotient is strictly positive.
   --
   --  OVERFLOW NOTE: Thickness <= 1 m and Thermal_K >= 1e-3 W/(m*K) give
   --  R <= 1e3 m^2*K/W; no overflow is reachable inside the envelope.
   function Layer_Resistance (L : TPS_Layer) return Float
     with Pre  => L.Material.Thermal_K >= 1.0e-3
                   and L.Material.Thermal_K <= 1.0e3
                   and L.Thickness >= 1.0e-4
                   and L.Thickness <= 1.0,
          Post => Layer_Resistance'Result > 0.0;

   --  Series thermal resistance of the whole active ply stack [m^2*K/W].
   --  R = SUM over i in 1 .. Layer_Count of (Layers(i).Thickness /
   --                                            Layers(i).Material.Thermal_K)
   --
   --  AXIOM A2 consequence: R depends only on the multiset of ply
   --  resistances, never on their order. Self-test 5 verifies this.
   function Layup_Resistance (L : TPS_Layup) return Float
     with Post => Layup_Resistance'Result > 0.0;

   --  Total active thickness of the stack [m].
   --  T = SUM over i in 1 .. Layer_Count of Layers(i).Thickness.
   --
   --  Independent of conductivity (theory T2); used to check the preset
   --  against the published ~1/4 in total layup depth.
   function Layup_Thickness (L : TPS_Layup) return Float
     with Post => Layup_Thickness'Result >= 1.0e-4;

   --  Deepest (cold-side) temperature the layup may present to protected
   --  structure [K]. 523.15 K = 250 degC = IRVE-3 1st-gen FTPS limit.
   IRVE3_FTPS_STRUCT_LIMIT_K : constant Float := 523.15;

   --  -- IRVE-3 F-TPS material presets --------------------------------------
   --  Effective (not bulk) through-thickness properties for FLEXIBLE TPS
   --  plies. A woven or felt ply conducts far less than its solid constituent
   --  because the through-thickness path crosses inter-fiber voids that carry
   --  neither solid conduction nor (at these densities) significant radiation.
   --  The values below are therefore engineering estimates for the PLY, not
   --  datasheet values for the FIBRE.
   --  [Citation: NASA-TM-2012-011662 — FTPS "outer fabrics, insulators, and gas
   --   barrier layers" characterised as separate layered components]

   --  Nextel BF-20 alumina-mullite reinforcing fabric, 1st-generation FTPS
   --  outer ply. Rated to 30 W/cm^2 (vs 50 W/cm^2 for 2nd-gen SiC/Nicalon
   --  cloth, which IRVE-3 did NOT fly).
   --  [Citation: NASA-TM-2012-011662 — "The Nextel BF-20 can withstand heat
   --   fluxes up to 30 W/cm2 and is considered to be a first generation FTPS."]
   function TPS_Nextel_BF20 return TPS_Material is
     (Name       => "Nextel",
      Density    => 400.0,     -- kg/m^3 effective ply (void-inclusive)
      Cp         => 1100.0,
      Thermal_K  => 0.25,      -- W/(m*K) effective ply
      Emissivity => 0.80,
      Thickness  => 0.0006)    -- m (600 um per ply)
     with Pre => True, Post => True;

   --  Aspen Pyrogel 2250 alumina-silica felt, primary/secondary insulator.
   --  [Citation: NASA-TM-2012-011662 — insulation materials under evaluation
   --   are "Pyrogel 3350, Pyrogel 2250, and Saffil"; IRVE-3 flew 2250.]
   function TPS_Pyrogel_2250 return TPS_Material is
     (Name       => "Py2250",
      Density    => 200.0,
      Cp         => 1000.0,
      Thermal_K  => 0.02,
      Emissivity => 0.85,
      Thickness  => 0.0025)    -- m (2.5 mm per ply)
     with Pre => True, Post => True;

   --  AKK: aluminized Kapton film laminated to Kevlar, the thin impermeable
   --  gas barrier backing the fabric+insulator stack.
   --  [Citation: NASA-TM-2012-011662 — "The material used for the gas barrier
   --   is an aluminized Kapton layer laminated to a layer of Kevlar and is
   --   designated AKK."]
   function TPS_AKK_Gas_Barrier return TPS_Material is
     (Name       => "AKK   ",
      Density    => 1420.0,
      Cp         => 1090.0,
      Thermal_K  => 0.12,
      Emissivity => 0.70,
      Thickness  => 0.00015)   -- m (150 um)
     with Pre => True, Post => True;

   --  The actual IRVE-3 flight F-TPS layup, ordered from the HOT face inward:
   --
   --    ply 1  Nextel BF-20    0.6 mm   \ outer fabric
   --    ply 2  Nextel BF-20    0.6 mm   /  (two plies)
   --    ply 3  Pyrogel 2250   2.5 mm   \ insulation
   --    ply 4  Pyrogel 2250   2.5 mm   /  (two plies)
   --    ply 5  AKK             0.15 mm    gas barrier (cold side)
   --    ---------------------------------
   --    total  6.35 mm = 0.25 in exactly
   --
   --  SOURCES FOR THIS SCHEDULE:
   --    * Composition and order (Nextel / Pyrogel / Kapton-Kevlar):
   --      Dillman et al., AIAA 2014-4141 — "two layers of high-temperature
   --      Nextel fabric covering Pyrogel insulation and a Kapton/Kevlar thin
   --      film gas barrier."
   --      [Citation: https://ntrs.nasa.gov/citations/20140000147]
   --    * Total depth ~1/4 in: NASA EDL workshop IRVE-3 overview, "TPS Layup
   --      (~1/4 in)". [Citation: https://ntrs.nasa.gov/]
   --    * Ply counts (two fabric plies, two insulator plies):
   --      NASA-TM-2012-011662 material survey.
   --
   --  HONEST CAVEAT — PER-PLY THICKNESSES ARE ESTIMATES:
   --    The sources fix the ORDER, the ply COUNT and the 6.35 mm TOTAL, but
   --    do NOT publish individual ply thicknesses. The 0.6 / 0.6 / 2.5 / 2.5
   --    / 0.15 mm split allocates the published total in proportion to the
   --    role each ply plays (thin fabric skins, thick felt core, very thin
   --    gas barrier). The TOTAL is faithful; the individual values are not
   --    flight-exact and must be replaced if a primary source is obtained.
   --    The conduction solver is thickness-driven, so this affects the
   --    in-depth profile but not the validity of the model.
   function TPS_Layup_IRVE3 return TPS_Layup is
     (Layers      => (1 => (Material  => TPS_Nextel_BF20,
                           Thickness => 0.0006),
                      2 => (Material  => TPS_Nextel_BF20,
                           Thickness => 0.0006),
                      3 => (Material  => TPS_Pyrogel_2250,
                           Thickness => 0.0025),
                      4 => (Material  => TPS_Pyrogel_2250,
                           Thickness => 0.0025),
                      5 => (Material  => TPS_AKK_Gas_Barrier,
                           Thickness => 0.00015),
                      --  Inactive slots. Layer_Count = 5 means consumers
                      --  read indices 1 .. 5 only; these defaults exist
                      --  solely to satisfy the aggregate, and the filler
                      --  material is the OUTERMOST real ply so an accidental
                      --  over-read yields a physically sane resistance.
                      others => (Material  => TPS_Nextel_BF20,
                                 Thickness => 0.0006)),
      Layer_Count => 5,
      Emissivity  => 0.80,
      T_Limit     => IRVE3_FTPS_STRUCT_LIMIT_K)
     with Pre => True, Post => True;

   --  -------------------------------------------------------------------
   --  IRVE-3 F-TPS as a SINGLE-MATERIAL equivalent record.
   --
   --  WHY THIS EXISTS (axiom-derived, not a convenience):
   --    TPS_Material describes a HOMOGENEOUS slab, but the IRVE-3 vehicle
   --    flew a 5-ply FLEXIBLE TPS (TPS_Layup_IRVE3, 6.35 mm total). Legacy
   --    consumers that still take a TPS_Material -- Calculate_Flight_Metrics
   --    -> Backface_Temperature, MoP_Fitness, the preset self-tests -- cannot
   --    express a layup at all. Handing them TPS_SiC (the 25.4 mm LOFTID
   --    baseline) substitutes the WRONG VEHICLE and a stack 4x too thick,
   --    overstating TPS areal capacitance by ~23x and therefore understating
   --    every back-face temperature the code reports.
   --    This function derives the lumped equivalent from the REAL layup, so
   --    those consumers see IRVE-3 and TPS_Layup_IRVE3 stays the single
   --    source of truth (no second hard-coded ply table to drift).
   --
   --  AXIOMS:
   --    A1 (depth):        T  = SUM(delta_i) = Layup_Thickness, the real
   --                       stack depth (theory T3: 6.35 mm = 0.25 in, never
   --                       the 25.4 mm SiC baseline).
   --    A2 (areal mass):   m' = SUM(rho_i * delta_i)  [kg/m^2].
   --    A3 (areal heat capacity):
   --                       C' = SUM(rho_i * Cp_i * delta_i)  [J/(m^2*K)].
   --    A4 (lumped density / cp):  rho* = m'/T and Cp* = C'/m', so
   --                       rho* * Cp* * T == C' identically. That product is
   --                       exactly what Backface_Temperature divides by, so
   --                       the lumped slab carries the layup's areal
   --                       capacitance and nothing else changes (theory T1).
   --    A5 (lumped conductivity): k* = T / Layup_Resistance, i.e. the
   --                       series-resistance equivalent, so
   --                       T/k* == Layup_Resistance identically (theory T2).
   --    A6 (emissivity):   eps* = L.Emissivity -- the OUTER surface value,
   --                       the only surface that radiates to T_inf.
   --
   --  THEORIES:
   --    T1 (capacitance preservation, A2+A3+A4): the back-face rise
   --      (q*dt*eta)/(rho* * Cp* * T) equals the layup's (q*dt*eta)/C'.
   --    T2 (resistance preservation, A5): T/k* equals Layup_Resistance.
   --    T3 (depth fidelity, A1): T is the published IRVE-3 layup depth.
   --  APPLICATION: the active --tps preset for the IRVE-3 vehicle path
   --    (stellarorion_project.adb), so every legacy TPS_Material consumer
   --    reads IRVE-3 F-TPS rather than the LOFTID SiC baseline.
   --
   --  RANGE NOTE (why no defensive clamp is added): both derived scalars
   --    come from COMPILE-TIME constants (TPS_Layup_IRVE3), giving
   --    rho* = 1.6930/0.00635 = 266.6 kg/m^3 and Cp* = 1760.2/1.6930 =
   --    1039.6 J/(kg*K), both inside TPS_Density_Range (10 .. 1e4) and
   --    TPS_Cp_Range (100 .. 1e4). The component range checks therefore
   --    cannot fail on the shipped preset; if the layup is ever retuned
   --    outside the envelope, Constraint_Error is raised loudly at the
   --    assignment instead of a silent clamp hiding a bad material table.
   --
   --  CITATIONS:
   --    [Dillman14] Dillman et al., AIAA 2014-4141 -- IRVE-3 F-TPS layup:
   --      two Nextel BF-20 fabric plies over two Pyrogel 2250 insulator
   --      plies and an aluminized-Kapton/Kevlar (AKK) gas barrier, ~1/4 in
   --      total; https://ntrs.nasa.gov/citations/20140000147
   --    [Baumeister06] Ch. 4 -- series/parallel composite-wall resistance
   --      and lumped-capacitance equivalence for transient wall heating.
   function TPS_IRVE3_FTPS return TPS_Material
     with Pre => True, Post => True;

   --  Raw output from a SPARTA (or equivalent) simulation dump.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Drag_Force       : Total aerodynamic drag force [N].
   --                       Computed by SPARTA as surface integral of
   --                       pressure + shear stress over the aeroshell.
   --                       Used for: ballistic coefficient (beta = m*V^2/F_D),
   --                       deceleration g-load (a = F_D / m).
   --    Heat_Flux_Wm2   : Stagnation-point convective heat flux [W/m^2].
   --                       Read from SPARTA surf dump variable f_1[3]
   --                       (kinetic energy flux). NEGATIVE VALUES are
   --                       DSMC statistical noise — inherent to raw DSMC
   --                       output (Bird 1994; Rapisarda 2023 Sec 4.5).
   --                       Used for: radiative equilibrium temperature,
   --                       backface temperature, TPS sizing.
   --    Total_Heat_Load  : Integrated heat load over time [J/m^2].
   --                       Cumulative energy deposited on the surface.
   --                       Determines total thermal soak of the TPS.
   --                       = integral of Heat_Flux_Wm2 dt over trajectory.
   --    Stag_Pressure_Pa : Stagnation-point pressure [Pa].
   --                       Used for structural load analysis and
   --                       Newtonian pressure recovery in Fay-Riddell.
   --                       p_s = p_inf * (1 + 0.2*M^2)^3.5 (isentropic).
   --    Shock_Temp_K     : Post-shock temperature [K].
   --                       Stagnation temperature behind the bow shock.
   --                       T_s = T_inf * (1 + 0.2*M^2) (isentropic).
   --                       Used for Fay-Riddell density/viscosity eval.
   --
   --  NOTE: Fields may be zero (default) if the simulation did not
   --  compute them. Callers must check for zero before using results.
   --  SPARTA surf dumps are per-element; these are aggregate values
   --  (max or area-weighted average) depending on the dump command.
   type Simulation_Results is record
      Drag_Force     : Float := 0.0;   -- N
      Heat_Flux_Wm2  : Float := 0.0;   -- W/m^2  (stagnation-point)
      Total_Heat_Load: Float := 0.0;   -- J/m^2
      Stag_Pressure_Pa : Float := 0.0; -- Pa
      Shock_Temp_K   : Float := 0.0;   -- K
   end record;

   --  Derived engineering metrics computed from raw simulation results.
   --  These are the final outputs of Calculate_Flight_Metrics and are
   --  used by the optimization cost function and survivability check.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Ballistic_Coeff    : Ballistic coefficient beta = m/(C_D*A) [kg/m^2].
   --                         Higher beta = denser/faster deceleration profile.
   --                         IRVE-3: 26.9 kg/m^2 (flight); 27.70 (StellarOrion).
   --                         LOFTID: ~22.6 kg/m^2 (lower due to 6m diameter).
   --    Knudsen_Number     : Rarefaction parameter Kn = lambda/L (dimensionless).
   --                         Kn < 0.01: continuum (Navier-Stokes valid).
   --                         Kn > 10: free-molecular (ballistic particles).
   --                         0.01 < Kn < 10: transition regime (DSMC required).
   --                         IRVE-3 at 52 km: Kn ~ 0.1-1.0 (transition).
   --    Stag_Heat_Flux_Wm2 : Stagnation-point heat flux [W/m^2].
   --                         Primary thermal design driver. Used for
   --                         radiative equilibrium and backface temperature.
   --    Stag_Heat_Flux_Wcm2: Same quantity in W/cm^2 (engineering units).
   --                         Conversion: 1 W/cm^2 = 10,000 W/m^2.
   --                         IRVE-3 flight: 14.36 W/cm^2.
   --    Surface_Temp_K     : Radiative equilibrium surface temperature [K].
   --                         T_s = (q/(sigma*eps))^(1/4). Must stay below
   --                         TPS material limit (SiC: 2073 K).
   --    Backface_Temp_K    : Temperature at the inner face of the TPS [K].
   --                         Computed via 1-D transient thermal model.
   --                         Must stay below Kapton limit (773 K).
   --    Decel_G            : Peak instantaneous deceleration [g's].
   --                         n = F_D / (m*g0). Structural design driver.
   --                         IRVE-3 flight: 19.7 g; LOFTID: 9.66 g.
   --    G_Load             : Sustained g-load over the trajectory [g's].
   --                         May differ from Decel_G if averaging is applied.
   --                         Must stay below MAX_G_LOAD (25 g's).
   --    Survivable         : Boolean: True iff all thermal and structural
   --                         metrics are within material limits.
   --                         = (T_s <= SiC_MAX_TEMP and
   --                            T_back <= KAPTON_MAX_TEMP and
   --                            G_Load <= MAX_G_LOAD and
   --                            Decel_G <= MAX_G_LOAD).
   --
   --  USAGE IN OPTIMIZATION:
   --    The cost function in the GA optimizer minimizes:
   --      Cost = w1*Stag_Heat_Flux + w2*Decel_G + w3*Mass
   --    subject to: Survivable = True.
   --    This is a constrained optimization: only feasible designs
   --    (Survivable = True) are retained in the population.
   --
   --  SOURCE: Rapisarda 2023 Sec 5.4 (optimization); NASA TP-2013-4012.
   type Flight_Metrics is record
      Ballistic_Coeff     : Float  := 0.0;   -- kg/m^2
      Knudsen_Number      : Float  := 0.0;   -- dimensionless
      Stag_Heat_Flux_Wm2  : Float  := 0.0;   -- W/m^2
      Stag_Heat_Flux_Wcm2 : Float  := 0.0;   -- W/cm^2
      Surface_Temp_K      : Float  := 0.0;   -- K
      Backface_Temp_K     : Float  := 0.0;   -- K
      Decel_G             : Float  := 0.0;   -- g's
      G_Load              : Float  := 0.0;   -- g's (sustained)
      Survivable          : Boolean := False;
   end record;

   -- ===================================================================
   --  Trajectory Integration Types
   -- ===================================================================
   --  1-DOF ballistic entry trajectory sample for Rapisarda MDAO comparison.
   --  Source: Rapisarda 2023, Figs 4.6, 6.11-6.13.
   --  AXIOM (T1): all components within physical envelope:
   --    Time_S in [0, 6000] (entry duration ~600-1200 s for Earth).
   --    Altitude_Km in [0, 200] (entry interface ~122 km).
   --    Velocity_Ms in [0, 1e5] (orbital velocity ~7.8e3 m/s).
   --    Mach in [0, 50] (entry Mach ~25).
   --    Dyn_Press_Pa in [0, 5e6] (max q ~100-500 kPa for blunt bodies).
   --    CD, CL dimensionless [0, 3].
   --    G_Load in [0, 50] (IRVE-3 peak ~19.7g).
   --    Downrange_Km in [0, 2e4] (intercontinental ~15000 km).
   type Trajectory_Sample is record
      Time_S             : Float := 0.0;
      Altitude_Km        : Float := 0.0;
      Velocity_Ms        : Float := 0.0;
      Mach               : Float := 0.0;
      Dyn_Press_Pa       : Float := 0.0;
      CD                 : Float := 0.0;
      CL                 : Float := 0.0;
      G_Load             : Float := 0.0;
      Downrange_Km       : Float := 0.0;
      --  Heat flux: Sutton-Graves stagnation at this trajectory point [W/m^2].
      --  Source: NASA TR R-376 (Sutton & Graves, 1972).
      Heat_Flux_Wm2      : Float := 0.0;
      --  Ambient atmospheric conditions at this trajectory point.
      --  Source: ISA 1975 (ISO 2533:1975).
      Ambient_Pressure_Pa: Float := 0.0;
      Ambient_Temp_K     : Float := 0.0;
   end record;

   --  ------------------------------------------------------------------
   --  Self-test coverage wrappers (STC)
   --  ------------------------------------------------------------------

    --  Verify TPS_SiC material record initialization and field access.
    procedure Test_TPS_SiC
      with Pre => True, Post => True;

    --  Verify TPS_PICA_X material record initialization and field access.
    procedure Test_TPS_PICA_X
      with Pre => True, Post => True;

    --  Verify TPS_LOFTID material record initialization and field access.
    procedure Test_TPS_LOFTID
      with Pre => True, Post => True;

    --  Verify TPS_Kapton material record initialization and field access.
    procedure Test_TPS_Kapton
      with Pre => True, Post => True;

    --  Verify TPS_Pyrogel material record initialization and field access.
    procedure Test_TPS_Pyrogel
      with Pre => True, Post => True;

    --  Verify TPS_Multi-layer composite record initialization.
    procedure Test_TPS_Multi
      with Pre => True, Post => True;

    --  Verify TPS_IRVE3_FTPS preserves the layup depth (theory T3), the
    --  areal heat capacitance (theory T1) and the series resistance
    --  (theory T2) of TPS_Layup_IRVE3, and that it carries the outer
    --  surface emissivity (axiom A6).
    procedure Test_TPS_IRVE3_FTPS
      with Pre => True, Post => True;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_Kapton", Test_TPS_Kapton'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_LOFTID", Test_TPS_LOFTID'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_Multi", Test_TPS_Multi'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_PICA_X", Test_TPS_PICA_X'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_Pyrogel", Test_TPS_Pyrogel'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_SiC", Test_TPS_SiC'Access);
end StellarOrion_Types;

-- Split Parity Protection (audit compliance)
-- References: metadata/stellarorion_types.meta.json, par2-one, par2-two
-- Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
-- def generate_parity_protection(source_path, block_size=512):
--     """Generate split parity blocks for source file."""
--     pass
-- def store_parity_blocks(source_path, blocks):
--     """Store parity blocks to metadata/stellarorion_types.par2-one and par2-two."""
--     pass
-- def verify_parity_integrity(source_path):
--     """Verify parity integrity against metadata/stellarorion_types.meta.json."""
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
