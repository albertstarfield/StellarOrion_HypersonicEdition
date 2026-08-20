-- StellarOrion HypersonicEdition — Ada Unit Tests
-- Tests for core physics, geometry, and validation packages.

with AUnit; use AUnit;
with AUnit.Test_Suites; use AUnit.Test_Suites;
with AUnit.Test_Cases; use AUnit.Test_Cases;
with AUnit.Assertions; use AUnit.Assertions;

with StellarOrion_Types; use StellarOrion_Types;
with StellarOrion_Physics; use StellarOrion_Physics;
with StellarOrion_Geometry; use StellarOrion_Geometry;
with StellarOrion_Validation; use StellarOrion_Validation;

package body Test_Physics is

   procedure Test_Mean_Free_Path (T : in out Test_Cases.Test_Case'Class) is
      MFP : Float;
   begin
      -- MFP at n=1e23, d=3.7e-10 should be ~5.2e-3 m
      MFP := Mean_Free_Path (1.0e23, 3.7e-10);
      Assert (MFP > 0.0, "MFP must be positive");
      Assert (MFP > 1.0e-3 and MFP < 1.0e-1,
              "MFP out of expected range for standard air");
   end Test_Mean_Free_Path;

   procedure Test_Knudsen_Number (T : in out Test_Cases.Test_Case'Class) is
      Kn : Float;
   begin
      -- Kn at MFP~5e-3, L=3.0m should be ~1.7e-3
      Kn := Knudsen_Number (5.2e-3, 3.0);
      Assert (Kn >= 0.0, "Knudsen number must be non-negative");
      Assert (Kn < 0.01, "Kn should be in continuum-transition regime");
   end Test_Knudsen_Number;

   procedure Test_Sutton_Graves (T : in out Test_Cases.Test_Case'Class) is
      Q : Float;
   begin
      -- At Mach 10, 52km: rho=6.9674e-4, Rn=0.55, V=2700
      Q := Sutton_Graves_Heat (6.9674e-4, 0.55, 2700.0);
      Assert (Q > 0.0, "Sutton-Graves heat flux must be positive");
      Assert (Q > 1.0e4 and Q < 1.0e6,
              "Heat flux out of expected range for Mach 10");
   end Test_Sutton_Graves;

   procedure Test_Dynamic_Pressure (T : in out Test_Cases.Test_Case'Class) is
      Q_Pa : Float;
   begin
      Q_Pa := Dynamic_Pressure (1.225, 100.0);
      Assert (Q_Pa = 0.5 * 1.225 * 100.0 * 100.0,
              "Dynamic pressure calculation incorrect");
   end Test_Dynamic_Pressure;

   procedure Test_Ballistic_Coefficient (T : in out Test_Cases.Test_Case'Class) is
      Beta : Float;
   begin
      Beta := Ballistic_Coefficient (281.0, 2.54e6, 4500.0);
      Assert (Beta > 0.0, "Ballistic coefficient must be positive");
   end Test_Ballistic_Coefficient;

   procedure Test_Geometry_Validation (T : in out Test_Cases.Test_Case'Class) is
      Geo : Geometry_Parameters := (others => <>);
   begin
      Assert (Validate_Geometry (Geo),
              "Default IRVE-3 geometry should be valid");
   end Test_Geometry_Validation;

   procedure Test_Radiative_Eq_Temp (T : in out Test_Cases.Test_Case'Class) is
      T_rad : Float;
   begin
      T_rad := Radiative_Eq_Temp (1.4e5, 0.75);
      Assert (T_rad > 0.0, "Radiative equilibrium temp must be positive");
      Assert (T_rad > 200.0 and T_rad < 5000.0,
              "Radiative temp out of expected range");
   end Test_Radiative_Eq_Temp;

   procedure Test_Backface_Temperature (T : in out Test_Cases.Test_Case'Class) is
      T_back : Float;
   begin
      T_back := Backface_Temperature
        (300.0, 1.4e5, 100.0, 0.15, 1468.0, 1100.0, 0.0254);
      Assert (T_back > 300.0,
              "Backface temp must be higher than initial (heating)");
      Assert (T_back < 2000.0,
              "Backface temp unreasonably high");
   end Test_Backface_Temperature;

   procedure Test_Deceleration_G (T : in out Test_Cases.Test_Case'Class) is
      G : Float;
   begin
      G := Deceleration_G_Load (4500.0, 281.0);
      Assert (G > 0.0, "Decel G must be positive");
      Assert (G < 100.0, "Decel G unreasonably high");
   end Test_Deceleration_G;

   procedure Test_Is_Survivable (T : in out Test_Cases.Test_Case'Class) is
      Metrics : Flight_Metrics := (
         Ballistic_Coeff     => 26.9,
         Knudsen_Number      => 0.001,
         Stag_Heat_Flux_Wm2  => 1.4e5,
         Stag_Heat_Flux_Wcm2 => 14.0,
         Surface_Temp_K      => 1200.0,
         Backface_Temp_K     => 400.0,
         Decel_G             => 19.0,
         G_Load              => 19.0,
         Survivable          => True);
   begin
      Assert (Is_Survivable (Metrics),
              "IRVE-3-like metrics should be survivable");
   end Test_Is_Survivable;

   procedure Test_Density_From_Number (T : in out Test_Cases.Test_Case'Class) is
      Rho : Float;
   begin
      Rho := Density_From_Number (1.0e23);
      Assert (Rho > 0.0, "Density must be positive");
      -- rho = 1e23 * 28.97e-3 / 6.022e23 ~ 0.00481 kg/m^3
      Assert (Rho > 1.0e-3 and Rho < 1.0e-1,
              "Density out of expected range");
   end Test_Density_From_Number;

end Test_Physics;
