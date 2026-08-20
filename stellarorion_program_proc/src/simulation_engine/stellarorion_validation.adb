--  StellarOrion_HypersonicEdition — Geometry & Survivability Validation (Body)
--  Ada 2012 / SPARK 2014

with StellarOrion_Physics;  use StellarOrion_Physics;

package body StellarOrion_Validation is
   pragma SPARK_Mode (On);

   -- ==================================================================
   --  Validate_And_Dump
   -- ==================================================================
   --  Pre-simulation geometry QA.
   --  Checks:
   --    1. Diameter in [0.5, 15.0] m      (Rapisarda Table 5.4)
   --    2. Nose angle in [40, 80] deg
   --    3. Toroid count in [1, 12]
   --    4. Toroid radius > 0
   --    5. TPS density > 0
   --    6. TPS thickness > 0
   --    7. TPS emissivity in (0, 1]
   function Validate_And_Dump
     (Geo : Geometry_Parameters;
      TPS : TPS_Material) return Boolean
   is
      Valid_Geo : Boolean;
      Valid_TPS : Boolean;
   begin
      --  Geometry range checks
      Valid_Geo :=
        Geo.Diameter_M    >= 0.5
        and Geo.Diameter_M    <= 15.0
        and Geo.Angle_Deg     >= 40.0
        and Geo.Angle_Deg     <= 80.0
        and Geo.Toroid_Count  >= 1
        and Geo.Toroid_Count  <= 12
        and Geo.Toroid_Radius_M > 0.0
        and Geo.Nose_Radius_M   > 0.0
        and Geo.Mass_Kg         > 0.0;

      --  TPS material sanity
      Valid_TPS :=
        TPS.Density    > 0.0
        and TPS.Cp     > 0.0
        and TPS.Thickness > 0.0
        and TPS.Emissivity > 0.0
        and TPS.Emissivity <= 1.0;

      return Valid_Geo and Valid_TPS;
   end Validate_And_Dump;

   -- ==================================================================
   --  Check_Survivability
   -- ==================================================================
   --  Returns True iff all thermal/structural limits are satisfied.
   function Check_Survivability
     (Metrics : Flight_Metrics) return Boolean
   is
   begin
      return Is_Survivable (Metrics);
   end Check_Survivability;

end StellarOrion_Validation;
