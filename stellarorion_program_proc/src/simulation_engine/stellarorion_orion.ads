--  StellarOrion_HypersonicEdition — Orion Crew Vehicle Defaults
--  Ada 2012 / SPARK 2014
--
--  Orion parameters based on NASA Orion Multi-Purpose Crew Vehicle
--  specifications and publicly available MDAO data.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Orion is
   pragma SPARK_Mode (On);

   -- ==================================================================
   --  Orion Default Parameters
   -- ==================================================================

   --  Flight conditions at a representative hypersonic trajectory point
   --  (Mach 30, ~75 km altitude, peak heating corridor).
   ORION_FLIGHT_DEFAULTS : constant Flight_Parameters :=
     (Mach          => 30.0,
      Altitude_Km   => 75.0,
      Velocity_Ms   => 9500.0,
      Density_Kgm3  => 3.846e-5,   -- ISA at 75 km
      Temperature_K => 206.87);    -- ISA at 75 km

   --  Geometry: Orion aeroshell (5.02 m diameter, 32.5-deg half-angle,
   --  no toroids — rigid PICA-X style).
   --  Source: NASA Orion spacecraft technical reports
    ORION_GEOMETRY_DEFAULTS : constant Geometry_Parameters :=
      (Diameter_M            => 5.02,
       Angle_Deg             => 32.5,
       Nose_Radius_M         => 1.5,
       Toroid_Count          => 1,   --  minimum 1 for the record constraint
       Toroid_Radius_M       => 0.0,
       Outer_Radius_M        => 0.0,
       Mass_Kg               => 10400.0,
       Payload_Height_M      => 1.70,
       Slice_Angle_Deg       => 360.0,
       Nose_Profile          => Smooth,
       Skin                  => Smooth,
       Scallop_Points        => 8,
       Scallop_Amplitude_M   => 0.030);

   --  TPS material: PICA-X (Phenolic Impregnated Carbon Ablator)
   --  Source: NASA Ames / SpaceX PICA-X data
   ORION_TPS_DEFAULTS : constant TPS_Material :=
     (Name       => "PICA-X",
      Density    => 320.0,    -- kg/m^3  (low-density ablator)
      Cp         => 1200.0,   -- J/(kg*K)
      Thermal_K  => 0.5,      -- W/(m*K)
      Emissivity => 0.85,
      Thickness  => 0.050);   -- m  (50 mm)

   -- ==================================================================
   --  Survivability Check
   -- ==================================================================

   --  Orion-specific survivability check.
   --  Uses the same material limits as the generic check but
   --  applies Orion-specific tolerances (higher g-load allowance
   --  for crew-rated vehicle).
   function Orion_Survivability_Check
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     (Metrics : Flight_Metrics) return Boolean;
      --  Invariant: parameters and derived locals remain within their declared

   procedure Test_Orion_Survivability_Check;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Orion_Survivability_Check", Test_Orion_Survivability_Check'Access);
end StellarOrion_Orion;
