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
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
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

   --  STC coverage wrapper for Orion_Survivability_Check.
   --  Pure predicate exercised on the all-defaults Flight_Metrics record;
   --  zero g-loads sit inside the crew-rated envelope, so a positive
   --  generic verdict must yield a positive Orion verdict.
   procedure Test_Orion_Survivability_Check is
   --  @test: Test_Orion_Survivability_Check unit smoke coverage (STC registry).
   --  Contract covers pre => True (no inputs); post => completes without raising.
      Probe   : constant Flight_Metrics := (others => <>);
      Verdict : constant Boolean := Orion_Survivability_Check (Probe);
   begin
      pragma Assert (Probe.Decel_G <= ORION_MAX_G);
      pragma Assert (Probe.G_Load <= ORION_MAX_G);
      pragma Assert (if Is_Survivable (Probe) then Verdict);
   end Test_Orion_Survivability_Check;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Orion_Survivability_Check", Test_Orion_Survivability_Check'Access);
end StellarOrion_Orion;
