-- StellarOrion HypersonicEdition — Test Suite Runner
-- Entry point for Ada unit tests using AUnit.

with AUnit.Test_Suites; use AUnit.Test_Suites;
with Test_Physics; use Test_Physics;

package Test_Suite_Body is

   function Suite return AUnit.Test_Suites.Test_Suite is
      S : AUnit.Test_Suites.Test_Suite;
   begin
      Add_Test (S, new Test_Physics);
      return S;
   end Suite;

end Test_Suite_Body;
