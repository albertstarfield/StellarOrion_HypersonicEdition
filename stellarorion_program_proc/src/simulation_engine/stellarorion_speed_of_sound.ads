--  StellarOrion_HypersonicEdition — Speed of Sound (dedicated SPARK_Mode On unit)
--  Ada 2012 / SPARK 2014
--
--  WHY A SEPARATE UNIT:
--    StellarOrion_Environment also models the atmosphere, but its body is
--    pragma SPARK_Mode (Off) because its exception handlers use the choice
--    parameter (when E : others =>), which the SPARK subset forbids, and
--    SPARK_Mode cannot be re-enabled from Off inside a body. Putting the
--    speed-of-sound physics in its own unit with pragma SPARK_Mode (On) keeps
--    it inside the formally verified subset without disturbing the atmosphere
--    package.
--
--  Author: Albert Starfield Wahyu Suryo Samudro

package StellarOrion_Speed_Of_Sound is
   pragma SPARK_Mode (On);

   --  Speed of sound in air [m/s] at a static temperature.
   --  a = sqrt(gamma * R * T); gamma = 1.4, R = 287.058 J/(kg*K).
   --
   --  AXIOM (S1) [ideal gas]: the speed of sound in an ideal gas is
   --    a = sqrt(gamma * R * T), with gamma = 1.4 and R = 287.058 J/(kg*K)
   --    for dry air.
   --  AXIOM (S2) [envelope]: temperature 0 .. 6000 K covers the ISA profile
   --    (186.87 .. 288.15 K), hot-wall recovery, and the SPARTA grid-cell
   --    mask (T_FLOOR .. T_CEIL = 50 .. 6000 K) used by the field-panel plots.
   --  THEOREM (T1) [overflow]: gamma*R*T <= 1.4*287.058*6000 = 2.4113e6;
   --    the Newton square root is <= Max(2.4113e6, 1); a <= 1553 m/s
   --    << Float'Last (~3.4e38). No intermediate can overflow.
   --  CITATION: [Anderson] Anderson, "Modern Compressible Flow," 3rd Ed.,
   --    Ch. 2 — speed of sound in an ideal gas.
   --  THEOREM (T2) [accuracy]: the result is the square root of
   --    gamma*R*Temperature to a relative error below 1.0e-6.  Because the
   --    square root is irrational in general, the accuracy is stated on the
   --    SQUARE of the result, which is a rational expression in the input:
   --      Result*Result in [ (gamma*R*T)*(1 - 1e-6), (gamma*R*T)*(1 + 1e-6) ].
   --    This is the formal counterpart of the measured worst-case relative
   --    error 6.3e-8 over the 50 .. 6000 K sweep.
   --  CITATION: [Citation: IEEE 754-2019, Section 9 — square root];
   --    [Citation: Anderson, "Modern Compressible Flow," 3rd Ed., Ch. 2].
   function Speed_Of_Sound
     (Temperature : Float) return Float
     with Pre  => Temperature >= 0.0 and Temperature <= 6000.0,
          Post => Speed_Of_Sound'Result >= 0.0
                  and then
                    Speed_Of_Sound'Result * Speed_Of_Sound'Result
                      <= 1.4 * 287.058 * Temperature * (1.0 + 1.0e-6)
                  and then
                    Speed_Of_Sound'Result * Speed_Of_Sound'Result
                      >= 1.4 * 287.058 * Temperature * (1.0 - 1.0e-6);

end StellarOrion_Speed_Of_Sound;
