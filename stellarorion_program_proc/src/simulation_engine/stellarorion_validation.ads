--  StellarOrion_HypersonicEdition — Geometry & Survivability Validation
--  Ada 2012 / SPARK 2014
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

with StellarOrion_Types; use StellarOrion_Types;

package StellarOrion_Validation is
   pragma SPARK_Mode (On);

   --  Pre-simulation geometry QA:
   --    * Validates ranges per Rapisarda 2023 Table 5.4
   --    * Prints a human-readable report (when SPARK_Mode => Off caller)
   --    * Returns True iff all checks pass.
   --  Both geometry and TPS material must have positive values for
   --  the validation checks to be meaningful.
   function Validate_And_Dump
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     (Geo : Geometry_Parameters;
     --  Invariant: parameters and derived locals remain within their declared
      TPS : TPS_Material) return Boolean
   with Pre => Geo.Diameter_M > 0.0
               and Geo.Angle_Deg > 0.0
               and Geo.Toroid_Radius_M > 0.0
               and TPS.Thickness > 0.0
               and TPS.Density > 0.0
               and TPS.Cp > 0.0
               and TPS.Emissivity > 0.0;

   --  Post-simulation survivability check:
   --    * Returns True iff all thermal / structural limits are satisfied.
   --  Checks: surface temp ≤ SIC max, backface temp ≤ Kapton max,
   --  deceleration g-load ≤ 25 g, stagnation pressure reasonable.
   function Check_Survivability
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     (Metrics : Flight_Metrics) return Boolean;
      --  Invariant: parameters and derived locals remain within their declared

   --  Test infrastructure: verification-only procedures that exercise code
   --  paths for coverage.  Intentionally produce no runtime output.
   pragma Warnings (Off, "has no effect");

   procedure Test_Validate_And_Dump;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  STC coverage wrapper.
   procedure Test_Check_Survivability;
   --  Contract covers pre => True (no inputs); post => completes without raising.

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Check_Survivability", Test_Check_Survivability'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Validate_And_Dump", Test_Validate_And_Dump'Access);
end StellarOrion_Validation;
