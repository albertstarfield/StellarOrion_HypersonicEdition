--  StellarOrion_HypersonicEdition — Orion Crew Vehicle Defaults (Body)
--  Ada 2012 / SPARK 2014

with StellarOrion_Physics; use StellarOrion_Physics;

package body StellarOrion_Orion is
   pragma SPARK_Mode (On);

   --  Orion crew-rated g-load limit (higher than cargo: 25 g max)
   --  Source: NASA Orion design loads, public documentation
   ORION_MAX_G : constant Float := 25.0;

   -- ==================================================================
   --  Orion_Survivability_Check
   -- ==================================================================
   --  Checks that the Orion vehicle would survive the given conditions.
   --  Uses the standard Is_Survivable plus Orion-specific g-limit.
   function Orion_Survivability_Check
     (Metrics : Flight_Metrics) return Boolean
   is
   begin
      --  Must pass generic survivability (material limits)
      if not Is_Survivable (Metrics) then
         return False;
      end if;

      --  Orion-specific: crew-rated g-limit
      return Metrics.Decel_G <= ORION_MAX_G
        and Metrics.G_Load <= ORION_MAX_G;
   --  Invariant: parameters and derived locals remain within their declared
   --  subtype ranges throughout execution; no unchecked conversions occur.
   end Orion_Survivability_Check;

end StellarOrion_Orion;
