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
     (Geo : Geometry_Parameters;
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
     (Metrics : Flight_Metrics) return Boolean;

end StellarOrion_Validation;
