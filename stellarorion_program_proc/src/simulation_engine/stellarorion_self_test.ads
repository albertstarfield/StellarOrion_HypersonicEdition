--  StellarOrion_HypersonicEdition — Self-Test Package
--  Ada 2012 / SPARK 2014
--
--  Decomposition Stage 3 (docs/PROJECT_DECOMPOSITION_PLAN.md):
--  built-in verification suite extracted from stellarorion_project.adb.
--  Runs the 15 self-tests covering physics, geometry, environment,
--  optimization, TPS materials, atomic parity and dual watchdog.
--
--  Author:  Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Self_Test is

   pragma SPARK_Mode (Off);
   --  extern: console I/O + status-file writes; outside SPARK subset

   --  Execute all 15 self-tests; prints [TEST nn] PASS/FAIL lines and
   --  the final "All 15 self-tests PASSED." banner. Exits via exception
   --  only on catastrophic internal error (never in normal operation).
   --  Contract: pre => True (no input constraints); post => normal termination; effects limited to documented outputs
   procedure Run_Self_Test;

end StellarOrion_Self_Test;
