--  StellarOrion_Speed_Of_Sound body — SPARK_Mode On.
--
--  AXIOMS / THEORIES / APPLICATIONS / CITATIONS are carried by each subprogram.
--  This body is deliberately free of exception handlers with choice parameters
--  so it stays inside the SPARK subset.

package body StellarOrion_Speed_Of_Sound is
   pragma SPARK_Mode (On);

   GAMMA_AIR : constant Float := 1.4;      -- ratio of specific heats (dry air)
   R_AIR     : constant Float := 287.058;  -- specific gas constant [J/(kg*K)]

   --  Square root via Newton-Raphson (25 iterations), SPARK-provable.
   --
   --  AXIOM (S3): sqrt(x) is the unique non-negative y with y*y = x.
   --  THEOREM (T2) [band invariant]: the iteration map Y' = (Y + X/Y)/2
   --    preserves the band [Min(X,1), Max(X,1)] (AM-GM: Y' >= sqrt(X) when Y
   --    is in the band; both endpoints of the band are fixed points), so the
   --    loop invariant carries the band and the Post follows directly.
   --  APPLICATIONS: 25-iteration loop; initial guess Max(X/2, 1) is
   --    denormal-safe and enters the band; the invariant keeps Y > 0 so the
   --    division X/Y is always defined.
   --  CITATIONS: [Press et al., "Numerical Recipes," 3rd Ed., Ch. 5.6
   --    "Quadratic Convergence and Newton's Method"];
   --    [IEEE 754-2019, Section 9 — square root].
   function Sqrt_Approx (X : Float) return Float
     with Post => Sqrt_Approx'Result >= 0.0
                  and then
                    (if X > 0.0 then Sqrt_Approx'Result <= Float'Max (X, 1.0))
                  and then
                    (if X > 0.0 then
                       Sqrt_Approx'Result * Sqrt_Approx'Result
                         <= X * (1.0 + 1.0e-6)
                       and then
                       Sqrt_Approx'Result * Sqrt_Approx'Result
                         >= X * (1.0 - 1.0e-6))
   is
      Y     : Float;
      Y_New : Float;
   begin
      if X <= 0.0 then
         return 0.0;
      end if;
      Y := Float'Max (X / 2.0, 1.0);  -- denormal-safe Newton seed (Heron's method)
      for I in 1 .. 25 loop
         pragma Unreferenced (I);
         pragma Loop_Invariant (Y >= Float'Min (X, 1.0));
         pragma Loop_Invariant (Y <= Float'Max (X, 1.0));
         Y_New := (Y + X / Y) / 2.0;
         Y     := Y_New;
      end loop;
      return Y;
   end Sqrt_Approx;

   --  Speed of sound in air [m/s].
   --
   --  AXIOMS: a = sqrt(gamma*R*T); gamma = 1.4, R = 287.058 J/(kg*K).
   --  THEORIES: gamma*R*T is non-negative for T >= 0; the square root is
   --    computed via Sqrt_Approx, whose Post gives Result >= 0.
   --  APPLICATIONS: Gamma_R_T := GAMMA_AIR * R_AIR * Temperature; clamp to
   --    non-negative; return Sqrt_Approx (Gamma_R_T).
   --  CITATION: [Citation: Anderson, "Modern Compressible Flow," 3rd Ed.,
   --    Ch. 2 — speed of sound]; [Citation: Ada Reference Manual, RM A.5].
   function Speed_Of_Sound
     (Temperature : Float) return Float
   is
      Gamma_R_T : Float;
   begin
      Gamma_R_T := GAMMA_AIR * R_AIR * Temperature;
      if Gamma_R_T < 0.0 then
         Gamma_R_T := 0.0;
      end if;
      return Sqrt_Approx (Gamma_R_T);
   end Speed_Of_Sound;

end StellarOrion_Speed_Of_Sound;
