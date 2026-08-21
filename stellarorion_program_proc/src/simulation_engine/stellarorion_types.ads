--  StellarOrion_HypersonicEdition — Core Type Definitions
--  Ada 2012 / SPARK 2014
--  All physics constants originate from peer-reviewed sources.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro
--  Refs:
--    [TR-376]  Sutton, K. & Graves, R. A. "A General Stagnation-Point
--              Convective Heating Equation for Arbitrary Gas Mixtures,"
--              NASA TR R-376, 1972.
--    [CODATA]  CODATA 2018 recommended values (https://physics.nist.gov)
--    [Bird94]  Bird, G. A. "Molecular Gas Dynamics and the Direct
--              Simulation of Gas Flows," Oxford Univ. Press, 1994.
--    [Rap23]   Rapisarda, V. "Multidisciplinary Design Analysis and
--              Optimization of HIAD," Ph.D. thesis, 2023.
--    [ISA]     International Standard Atmosphere, ISO 2533:1975.

package StellarOrion_Types is
   pragma SPARK_Mode (On);

   -- ===================================================================
   --  Physical Constants
   -- ===================================================================

   --  Sutton-Graves stagnation-point heating coefficient [W/m^2 / (sqrt(kg/m^3)/m * (m/s)^3)]
   --  Source: NASA TR R-376, Table 1  (Sutton & Graves, 1972)
   C_SG : constant Float := 1.7415e-4;

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

   --  Vehicle configuration
   type Vehicle_Kind is (IRVE3, Orion);

   --  Optimization objective
   type Objective is (Drag_Obj, Heat_Obj);

   -- ===================================================================
   --  Record Types
   -- ===================================================================

   --  Freestream / flight conditions at a single trajectory point.
   --  Default values are Mach 10 at 52 km (typical hypersonic corridor).
   type Flight_Parameters is record
      Mach          : Float := 10.0;
      Altitude_Km   : Float := 52.0;
      Velocity_Ms   : Float := 2700.0;
      Density_Kgm3  : Float := 6.9674e-4;
      Temperature_K : Float := 270.65;
   end record;

   --  Nose geometry profile (affects shock attachment and drag).
   type Nose_Type_Kind is (Smooth, Pointy);

   --  Geometric definition of the HIAD aeroshell.
   --  Defaults correspond to IRVE-3 (Rapisarda 2023, Table 4.1).
   type Geometry_Parameters is record
      Diameter_M      : Float    := 3.0;
      Angle_Deg       : Float    := 60.0;
      Nose_Radius_M   : Float    := 0.55;
      Toroid_Count    : Positive := 6;
      Toroid_Radius_M : Float    := 0.135;
      Outer_Radius_M  : Float    := 0.0508;
      Mass_Kg         : Float    := 281.0;
      Slice_Angle_Deg : Float    := 360.0;
      Nose_Profile    : Nose_Type_Kind := Smooth;
   end record;

   --  Thermal Protection System material card.
   --  Defaults model a SiC tile stack (LOFTID-style F-TPS).
   type TPS_Material is record
      Name       : String (1 .. 6) := "SiC   ";
      Density    : Float := 1468.0;   -- kg/m^3
      Cp         : Float := 1100.0;   -- J/(kg*K)
      Thermal_K  : Float := 0.2;      -- W/(m*K)
      Emissivity : Float := 0.75;     -- dimensionless
      Thickness  : Float := 0.0254;   -- m  (1 inch)
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
      Thickness  => 0.0254);

   --  PICA-X (Phenolic Impregnated Carbon Ablator) — SpaceX variant.
   --  Source: NASA Ames RC; Tran et al. 2014.
   function TPS_PICA_X return TPS_Material is
     (Name       => "PICA  ",
      Density    => 320.0,
      Cp         => 1500.0,
      Thermal_K  => 0.5,
      Emissivity => 0.85,
      Thickness  => 0.040);

   --  LOFTID Flexible TPS (F-TPS) — ultra-lightweight inflatable.
   --  Source: Lau et al. 2013; NASA/TP-2013-4012.
   function TPS_LOFTID return TPS_Material is
     (Name       => "LOFTID",
      Density    => 300.0,
      Cp         => 1200.0,
      Thermal_K  => 0.15,
      Emissivity => 0.80,
      Thickness  => 0.050);

   --  Kapton polyimide film (backface insulation layer).
   --  Source: DuPont Kapton HN datasheet.
   function TPS_Kapton return TPS_Material is
     (Name       => "Kapton",
      Density    => 1420.0,
      Cp         => 1090.0,
      Thermal_K  => 0.12,
      Emissivity => 0.70,
      Thickness  => 0.005);

   --  PyroGel (aerogel blanket insulation — lightweight multi-layer TPS).
   --  Source: Aspen Aerogels PyroGel data sheets.
   function TPS_Pyrogel return TPS_Material is
     (Name       => "Pyrogl",
      Density    => 200.0,
      Cp         => 1000.0,
      Thermal_K  => 0.02,
      Emissivity => 0.85,
      Thickness  => 0.025);

   --  Multi-layer layup (SiC outer + PyroGel core + Kapton backface).
   --  Source: NASA IRVE-3 TPS stack description.
   function TPS_Multi return TPS_Material is
     (Name       => "Multi ",
      Density    => 650.0,
      Cp         => 1050.0,
      Thermal_K  => 0.10,
      Emissivity => 0.80,
      Thickness  => 0.040);

   --  Raw output from a SPARTA (or equivalent) simulation dump.
   type Simulation_Results is record
      Drag_Force     : Float := 0.0;   -- N
      Heat_Flux_Wm2  : Float := 0.0;   -- W/m^2  (stagnation-point)
      Total_Heat_Load: Float := 0.0;   -- J/m^2
      Stag_Pressure_Pa : Float := 0.0; -- Pa
      Shock_Temp_K   : Float := 0.0;   -- K
   end record;

   --  Derived engineering metrics computed from raw simulation results.
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

end StellarOrion_Types;
