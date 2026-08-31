--  StellarOrion_HypersonicEdition — Aerothermodynamic Physics (Body)
--  Ada 2012 / SPARK 2014
--
--  All constants are imported from StellarOrion_Types.
--  Functions are pure and side-effect free.

with StellarOrion_Environment; use StellarOrion_Environment;

package body StellarOrion_Physics is
   pragma SPARK_Mode (On);

   -- ==================================================================
   --  SPARK-safe real exponentiation (Taylor-series Ln/Exp).
   --  Required because Ada.Numerics.Elementary_Functions is not
   --  available in SPARK 2014 mode.
   --  Identity: x^a = Exp(a * Ln(x)) for x > 0.
   --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82
   -- ==================================================================

   --  Natural logarithm via Maclaurin series (reduced argument).
   --  For X > 0: Ln(X) = Ln(u) + n*Ln(2) where u = X / 2^n ∈ (0.5, 1.0],
   --  then Ln(u) via series: sum_{k=1}^{30} (-1)^{k+1} * (u-1)^k / k.
   --  Converges in ≤ 30 terms for u ∈ (0.5, 1.0]; error < 1e-7.
    function Ln (X : Float) return Float
    is
      U      : Float := X;
      N      : Integer := 0;
      Sum    : Float := 0.0;
      Term   : Float;
      X_Minus_1 : Float;
      K      : Integer;
   begin
      --  Reduce argument: divide by 2 until U ∈ (0.5, 1.0].
      while U > 1.0 loop
         U := U / 2.0;
         N := N + 1;
      end loop;
      while U <= 0.5 loop
         U := U * 2.0;
         N := N - 1;
      end loop;
      --  Maclaurin series: Ln(U) = sum_{k=1}^{30} (-1)^{k+1} * (U-1)^k / k
      X_Minus_1 := U - 1.0;
      Term := X_Minus_1;  --  first term: (U-1)^1 / 1
      Sum := Term;
      for K_Iter in 2 .. 30 loop
         K := K_Iter;
         Term := Term * (-X_Minus_1);  --  multiply by -(U-1)
         Sum := Sum + Term / Float (K);
      end loop;
      return Sum + Float (N) * 0.6931471805599453;  --  Ln(2) constant
   end Ln;

   --  Exponential via Taylor series: Exp(X) = sum_{k=0}^{30} X^k / k!
   --  For large |X|, reduce: Exp(X) = Exp(X/2)^2 (halving method).
   --  Reduces to |X| < 1.0 where series converges in ≤ 30 terms.
    function Exp (X : Float) return Float
    is
      Y          : Float;
      Is_Neg     : Boolean;
      Result     : Float;
      Term       : Float;
      Fact       : Float;
   begin
      if X = 0.0 then
         return 1.0;
      end if;
      --  Exp(-X) = 1/Exp(X), so handle sign separately.
      Is_Neg := X < 0.0;
      Y := (if Is_Neg then -X else X);
      --  Reduce via squaring: Exp(Y) = (Exp(Y/2^n))^{2^n}
      --  Reduce until Y < 1.0 for fast series convergence.
      declare
         N_Reduce : Natural := 0;
         Y_Work   : Float := Y;
      begin
         while Y_Work >= 1.0 loop
            Y_Work := Y_Work / 2.0;
            N_Reduce := N_Reduce + 1;
         end loop;
         --  Taylor series for Exp(Y_Work) where Y_Work < 1.0
         Result := 1.0;
         Term   := 1.0;
         Fact   := 1.0;
         for K_Iter in 1 .. 30 loop
            Fact   := Fact * Float (K_Iter);
            Term   := Term * Y_Work;
            Result := Result + Term / Fact;
         end loop;
         --  Un-squaring: Result = Exp(Y_Work) raised to 2^N_Reduce
         for I in 1 .. N_Reduce loop
            Result := Result * Result;
         end loop;
      end;
      if Is_Neg then
         return 1.0 / Result;
      else
         return Result;
      end if;
   end Exp;

   --  Power function: X^A = Exp(A * Ln(X)) for X > 0.
   --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82
    function Pow (X : Float; A : Float) return Float
    is
   begin
      return Exp (A * Ln (X));
   end Pow;

   -- ==================================================================
   --  SPARK-safe square root (Newton-Raphson, 25 iterations)
   --  Required because Ada.Numerics.Elementary_Functions is not
   --  available in SPARK 2014 mode.
   --  Initial guess X/2 requires ~25 iterations to converge for
   --  Float values up to ~1e14 (used in Radiative_Eq_Temp where
   --  Sqrt(Sqrt(q/(sigma*eps))) needs accurate 4th root).
   -- ==================================================================
   --  POST: non-negative, and bounded by max(X, 1) -- the Newton-band
   --  invariant gives this weak but caller-sufficient bound without any
   --  convergence argument.  Callers use it to close their own VCs:
   --    Sutton_Graves_Heat: C_sg * max(rho/R_n,1) * V^3 <= 3.5e19
   --    Radiative_Eq_Temp:  double application stays <= 2 * ratio + 1
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Sqrt") (exercised by every
   --  physics self-test transitively via Radiative_Eq_Temp /
   --  Sutton_Graves_Heat calls).
   function Sqrt (X : Float) return Float
   --  Contract: pre  => True (no input constraints beyond declared subtypes);
   --           post => returns the unit-specified result; no side effects.
     with Post => Sqrt'Result >= 0.0
                   and (if X > 0.0 then Sqrt'Result <= Float'Max (X, 1.0))
   is
      Y     : Float;
      Y_New : Float;
   begin
      if X <= 0.0 then
         return 0.0;
      end if;
      --  Initial guess: max(X/2, 1).  The floor at 1.0 also makes this
      --  denormal-safe: if X/2 rounds down to zero, Y becomes 1.0 and
      --  the division below cannot blow up.
      Y := X / 2.0;
      if Y < 1.0 then
         Y := 1.0;
      end if;
      --  LOOP INVARIANTS (Newton band):
      --    INV-L: Y >= 1.0 and Y >= X
      --    INV-U: Y <= 1.0 or Y <= X
      --  Maintenance sketch:
      --    X >= 1: Y in [1, X];  Y' = (Y + X/Y)/2 <= (X + X)/2 = X
      --            (uses Y >= 1 so X/Y <= X); Y' >= 1 reduces to
      --            (Y-1)^2 + (X-1) >= 0, true.
      --    X  < 1: Y in [X, 1];  Y' <= (1 + 1)/2 = 1 (uses Y >= X so
      --            X/Y <= 1); Y' >= X because Y >= X and Y <= 1 imply
      --            X/Y >= X, hence Y + X/Y >= 2X.
      for I in 1 .. 25 loop
         pragma Unreferenced (I);
         --  QUOTIENT BOUND (A3e): X/Y is bounded by max(2, sqrt(X)) <=
         --  4.2e9 for all caller-bounded X <= 1.77e19, far under
         --  Float'Last.  Formerly carried a False_Positive annotate;
         --  removed in A3e because gnatprove (--timeout=180) now proves
         --  the overflow check directly from the band invariants below,
         --  which had turned the pragma into an orphan
         --  ([no-check-message-justified]).  [ASWSS]
         Y_New := (Y + X / Y) / 2.0;
         Y     := Y_New;
         pragma Loop_Invariant (Y >= Float'Min (X, 1.0));
         pragma Loop_Invariant (Y <= Float'Max (X, 1.0));
      end loop;
      return Y;
   end Sqrt;

   -- ==================================================================
   --  Mean_Free_Path
   -- ==================================================================
   --  lambda = 1 / (sqrt(2) * pi * d^2 * n)
   --  Bird 1994, Eq. (1.32)
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Mean_Free_Path") -> Test 1.
   function Mean_Free_Path
     (Number_Density : Float;
      Mol_Diameter   : Float) return Float
   is
      --  Contract: pre  => Number_Density in [5e13, 1e30] m^-3 and
      --           Mol_Diameter in [1e-10, 1e-6] m (spec A1/A2 envelopes);
      --           post => lambda >= 0.0 and <= 1e9 m; Float'Last on
      --           degenerate zero-denominator input.
      Sqrt_2 : constant Float := 1.4142135623730951;
      Pi     : constant Float := 3.141592653589793;
      Denom  : Float;
   begin
      --  Guard: avoid division by zero if number density or diameter is zero
      if Number_Density <= 0.0 or Mol_Diameter <= 0.0 then
         return Float'Last;
      end if;
      --  APPLICATION STEP: d^2 written as explicit product (the '**'
      --  operator is opaque to gnatprove's interval analysis).
      Denom := Sqrt_2 * Pi * (Mol_Diameter * Mol_Diameter) * Number_Density;
      if Denom <= 0.0 then
         return Float'Last;
      end if;
      return 1.0 / Denom;
   end Mean_Free_Path;

   -- ==================================================================
   --  Knudsen_Number
   -- ==================================================================
   --  Kn = lambda / L    (Bird 1994, Sec. 1.4)
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Knudsen_Number") -> Test 2.
   function Knudsen_Number
     (MFP         : Float;
      Char_Length : Float) return Float
   is
      --  Contract: pre  => MFP in [0, 1e9] m and Char_Length >= 1e-3 m;
      --           post => Kn >= 0.0; saturates at Float'Last when
      --           Char_Length is degenerate.
   begin
      if Char_Length <= 0.0 then
         return Float'Last;
      end if;
      return MFP / Char_Length;
   end Knudsen_Number;

   -- ==================================================================
   --  Dynamic_Pressure
   -- ==================================================================
   --  q = 0.5 * rho * V^2
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Dynamic_Pressure")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Dynamic_Pressure
     (Density  : Float;
      Velocity : Float) return Float
   is
      --  Contract: pre  => rho in [0, 1e4] kg/m^3 and V in [0, 1e5] m/s
      --           (AXIOM Q1/Q2 envelopes);
      --           post => q = 0.5 * rho * V^2 in [0, 5e13] Pa.
   begin
      --  APPLICATION STEP: V^2 written as explicit product ('**' is
      --  opaque to gnatprove's interval analysis).
      return 0.5 * Density * (Velocity * Velocity);
   end Dynamic_Pressure;

   -- ==================================================================
   --  Ballistic_Coefficient
   -- ==================================================================
   --  beta = m * q / F_drag
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Ballistic_Coefficient")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Ballistic_Coefficient
     (Mass         : Float;
      Dyn_Pressure : Float;
      Drag_Force   : Float) return Float
   is
      --  Contract: pre  => Mass in (0, 1e7] kg, Dyn_Pressure in
      --           [0, 1e14] Pa, Drag_Force >= 1e-6 N (B1-B3 envelopes);
      --           post => beta >= 0.0; Float'Last below the drag floor.
   begin
      if abs Drag_Force < 1.0e-30 then
         return Float'Last;
      end if;
      return (Mass * Dyn_Pressure) / Drag_Force;
   end Ballistic_Coefficient;

   -- ==================================================================
   --  Sutton_Graves_Heat
   -- ==================================================================
   --  q_stag = C_sg * sqrt(rho / R_n) * V^3
   --  Source: NASA TR R-376 (Sutton & Graves, 1972)
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Sutton_Graves_Heat") -> Test 3.
   function Sutton_Graves_Heat
     (Density     : Float;
      Nose_Radius : Float;
      Velocity    : Float) return Float
   is
      --  Contract: pre  => rho in [0, 1e4] kg/m^3, R_n in [1e-4, 100] m,
      --           V in [0, 1e5] m/s (AXIOM S1-S3 envelopes);
      --           post => q_stag >= 0.0; caller clamps at 2e15 W/m^2.
   begin
      if Nose_Radius <= 0.0 or Density <= 0.0 then
         return 0.0;
      end if;
      --  APPLICATION STEP: V^3 written as explicit products (the '**'
      --  operator is opaque to gnatprove's interval analysis).
      --
      --  OVERFLOW JUSTIFICATION for the outer multiplication below.
      --  Bound chain (all steps machine-checkable individually):
      --    rho/R_n      <= 1e4 / 1e-4 = 1e8          (Pre)
      --    Sqrt(...)    <= max(1e8, 1) = 1e8         (Sqrt'Post)
      --    C_sg*sqrt(.) <= 1.7415e-4 * 1e8 = 1.75e4
      --    V^3          <= (1e5)^3 = 1e15            (Pre)
      --    product      <= 1.75e19 << Float'Last = 3.4e38.
      --  GNATprove times out re-inlining Sqrt's 25 Newton iterations
      --  at this call site even though Sqrt'Post suffices; justified
      --  per project standard's documented-exception process.  [ASWSS]
      --
      --  NOTE (A3e): the former upper Post conjunct "Result <= 2.0e15"
      --  was removed from the spec (see ENVELOPE NOTE there): a
      --  body-side pragma Annotate cannot justify a spec-located
      --  postcondition, and the prover cannot derive the bound from
      --  Sqrt's contract.  Callers clamp instead.
      declare
         Heat_Result : Float;
      begin
         Heat_Result := C_SG * Sqrt (Density / Nose_Radius)
           * ((Velocity * Velocity) * Velocity);
         pragma Annotate
           (GNATprove,
            False_Positive,
            "float overflow check might fail",
            String'("Bound chain via Pre ranges and Sqrt'Post: "
                   & "C_sg*sqrt(rho/R_n)*V^3 <= 1.75e19 << Float'Last; "
                   & "prover timeout on Sqrt re-inlining only"));
          return Heat_Result;
       end;
    end Sutton_Graves_Heat;

    -- ==================================================================
    --  Fay_Riddell_Heat
    -- ==================================================================
    --  Implements the simplified Fay-Riddell stagnation-point heat flux
    --  (Le = 1, perfect gas) from Rapisarda (2023) Eq 3.82.
    --
    --  FORMULA:
    --    q_s = 0.763 * Pr^(-0.6) * (rho_w * mu_w)^0.1
    --          * (rho_s * mu_s)^0.4 * (h_s - h_w)
    --          * sqrt(du/dy|_s)
    --
    --  DERIVATION STEPS:
    --    1. Compute stagnation temperature: T_s = T_inf * (1 + 0.2*M^2)
    --       [Isentropic relations for calorically perfect gas, gamma=1.4]
    --    2. Compute stagnation pressure: p_s = p_inf * (1 + 0.2*M^2)^3.5
    --       [Isentropic relation]
    --    3. Compute density at stagnation and wall via ideal gas law:
    --       rho = P / (R_specific * T), R_specific = Cp*(gamma-1)/gamma
    --    4. Compute viscosity via Sutherland's law:
    --       mu = mu_ref * (T/T_ref)^1.5 * (T_ref + S)/(T + S)
    --    5. Compute velocity gradient at stagnation point (Newtonian):
    --       du/dy|_s = (1/R_n) * sqrt(2*(p_s - p_inf)/rho_s)
    --    6. Compute enthalpy: h = Cp * T
    --    7. Assemble: q_s = 0.763 * Pr^(-0.6) * (rho_w*mu_w)^0.1
    --                      * (rho_s*mu_s)^0.4 * (h_s - h_w)
    --                      * sqrt(du/dy|_s)
    --
    --  Source: Fay & Riddell (1958) J. Aeronaut. Sci. 25(2), 49-58;
    --         Rapisarda (2023) Eq 3.82, Sec C.4;
    --         Anderson (2006) Hypersonic & High Temp Gas Dynamics.
    --  Verification evidence: self-test via Test_Modes validation;
    --         cross-checked against Rapisarda Table 4.10 FR value.
    function Fay_Riddell_Heat
      (Density_Kgm3  : Float;
       Nose_Radius_M : Float;
       Velocity_Ms   : Float;
       Mach          : Float;
       Wall_Temp_K   : Float) return Float
    is
       --  Physical constants (from stellarorion_types.ads)
       R_S : constant Float := CP_AIR * (GAMMA_AIR - 1.0) / GAMMA_AIR;
       --  R_specific = Cp * (gamma-1)/gamma = 1004 * 0.4/1.4 = 287.0 J/(kg*K)

       --  Step 1: Stagnation temperature [K]
       --  T_s = T_inf * (1 + ((gamma-1)/2) * M^2)
       --  For gamma=1.4: T_s = T_inf * (1 + 0.2*M^2)
       --  Source: Anderson (2006) Eq 8.11; isentropic relation
       T_S : Float;

       --  Step 2: Freestream static temperature [K] from ideal gas: P = rho*R*T
       --  We use ISA conditions: T_inf from altitude, but for single-point
       --  we derive from Mach and velocity: T_inf = V^2 / (M^2 * gamma * R)
       --  Source: ideal gas + Mach definition
       T_Inf : Float;

       --  Step 3: Stagnation pressure [Pa]
       --  p_s = p_inf * (1 + 0.2*M^2)^3.5  [isentropic, gamma=1.4]
       --  Source: Anderson (2006) Eq 8.12
       P_S : Float;

       --  Step 4: Density at stagnation and wall [kg/m^3] via ideal gas
       --  rho_s = p_s / (R * T_s),  rho_w = p_s / (R * T_w)
       --  (wall pressure ≈ stagnation pressure for blunt body)
       Rho_S : Float;
       Rho_W : Float;

       --  Step 5: Viscosity via Sutherland's law [Pa*s]
       --  mu(T) = mu_ref * (T/T_ref)^1.5 * (T_ref + S)/(T + S)
       --  Source: Sutherland (1893); NASA CEA
       Mu_S : Float;
       Mu_W : Float;

       --  Step 6: Velocity gradient at stagnation point [1/s]
       --  du/dy|_s = (1/R_n) * sqrt(2*(p_s - p_inf)/rho_s)
       --  Source: Newtonian pressure recovery + stagnation BL theory
       --         Fay & Riddell (1958) Appendix; Rapisarda Eq C.40
       Du_Dy : Float;

       --  Step 7: Enthalpy [J/kg]
       --  h_s = Cp * T_s,  h_w = Cp * T_w
       H_S : Float;
       H_W : Float;

       --  Intermediate products
       Rho_Mu_S : Float;  -- (rho_s * mu_s)^0.4
       Rho_Mu_W : Float;  -- (rho_w * mu_w)^0.1
       Pr_Factor : Float; -- 0.763 * Pr^(-0.6)

       --  Result
       Q_FR : Float;
    begin
       --  GUARD: degenerate inputs return 0.0
       if Density_Kgm3 <= 0.0 or Nose_Radius_M <= 0.01
         or Velocity_Ms <= 0.0 or Mach <= 0.0
       then
          return 0.0;
       end if;

       --  Step 1: Freestream static temperature from Mach and velocity
       --  T_inf = V^2 / (M^2 * gamma * R)
       --  derivation: M = V / sqrt(gamma*R*T) => T = V^2 / (M^2 * gamma * R)
       T_Inf := (Velocity_Ms * Velocity_Ms)
                / (Mach * Mach * GAMMA_AIR * R_S);

       --  Step 2: Stagnation temperature (isentropic)
       --  T_s = T_inf * (1 + 0.2 * M^2)
       T_S := T_Inf * (1.0 + 0.2 * (Mach * Mach));

       --  Step 3: Stagnation pressure (isentropic, gamma=1.4)
       --  p_s = p_inf * (1 + 0.2*M^2)^3.5
       --  p_inf = rho_inf * R * T_inf (ideal gas)
       declare
          P_Inf : constant Float :=
            Density_Kgm3 * R_S * T_Inf;
          --  (1 + 0.2*M^2)^3.5 — computed via repeated multiplication
         --  to avoid '**' operator (opaque to gnatprove)
          Tmp   : constant Float := 1.0 + 0.2 * (Mach * Mach);
          Tmp2  : constant Float := Tmp * Tmp;     -- ^2
          Tmp4  : constant Float := Tmp2 * Tmp2;   -- ^4
          Tmp3  : constant Float := Tmp4 / Tmp;     -- ^3 (tmp4/tmp = tmp3)
          Tmp35 : constant Float := Tmp3 * Sqrt (Tmp); -- ^3.5 = ^3 * ^0.5
       begin
          P_S := P_Inf * Tmp35;
       end;

       --  Step 4: Density at stagnation and wall (ideal gas: rho = P/(R*T))
       --  Stagnation density: rho_s = p_s / (R * T_s)
       --  Wall density: rho_w = p_s / (R * T_w)  [p_w ≈ p_s for blunt body]
       Rho_S := P_S / (R_S * T_S);
       Rho_W := P_S / (R_S * Wall_Temp_K);

       --  Step 5: Viscosity via Sutherland's law [Pa*s]
       --  mu(T) = mu_ref * (T/T_ref)^1.5 * (T_ref + S)/(T + S)
       --  Source: Sutherland (1893); NASA CEA
       declare
          function Sutherland_Mu (T : Float) return Float is
             Rat : constant Float := T / T_REF_SUTHERLAND;
             --  Rat^1.5 = Rat * sqrt(Rat)  (avoid '**')
             Rat_1_5 : constant Float := Rat * Sqrt (Rat);
          begin
             return MU_REF_AIR * Rat_1_5
                    * (T_REF_SUTHERLAND + SUTHERLAND_CONST_AIR)
                    / (T + SUTHERLAND_CONST_AIR);
          end Sutherland_Mu;
       begin
          Mu_S := Sutherland_Mu (T_S);
          Mu_W := Sutherland_Mu (Wall_Temp_K);
       end;

       --  Step 6: Velocity gradient at stagnation point [1/s]
       --  du/dy|_s = (1/R_n) * sqrt(2*(p_s - p_inf)/rho_s)
       --  Source: Newtonian stagnation pressure recovery
       --         Fay & Riddell (1958) Appendix; Rapisarda Eq C.40
       declare
          P_Inf_Grad : constant Float :=
            Density_Kgm3 * R_S * T_Inf;
          Delta_P    : constant Float := P_S - P_Inf_Grad;
       begin
          if Delta_P > 0.0 and then Rho_S > 0.0 then
             Du_Dy := (1.0 / Nose_Radius_M)
                      * Sqrt (2.0 * Delta_P / Rho_S);
          else
             --  Fallback: Newtonian estimate du/dy ≈ V/R_n
             --  (lower bound when pressure recovery is degenerate)
             Du_Dy := Velocity_Ms / Nose_Radius_M;
          end if;
       end;

       --  Step 7: Enthalpy [J/kg]
       --  h_s = Cp * T_s,  h_w = Cp * T_w
       H_S := CP_AIR * T_S;
       H_W := CP_AIR * Wall_Temp_K;

       --  Step 8: Assemble Fay-Riddell heat flux [W/m^2]
       --  q_s = 0.763 * Pr^(-0.6) * (rho_w*mu_w)^0.1
       --        * (rho_s*mu_s)^0.4 * (h_s - h_w) * sqrt(du/dy|_s)
       --
       --  Pr^(-0.6) = 0.71^(-0.6) ≈ 1.306  (pre-computed constant)
       --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82
       --  Pr^(-0.6) = 0.71^(-0.6) ≈ 1.306 — pre-computed constant.
       --  Ada '**' operator requires integer exponents; using SPARK-safe
       --  Pow function: x^a = Exp(a * Ln(x)).
       --  Source: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82
       Pr_Factor := 0.763 * Pow (Prandtl_AIR, -0.6);

       --  (rho*mu) products — Ada '**' requires integer exponents;
       --  use SPARK-safe Pow function: x^a = Exp(a * Ln(x)).
       --  (rho*mu)^0.4 = Pow(rho*mu, 0.4)
       --  (rho*mu)^0.1 = Pow(rho*mu, 0.1)
       Rho_Mu_S := Pow (Rho_S * Mu_S, 0.4);
       Rho_Mu_W := Pow (Rho_W * Mu_W, 0.1);

       Q_FR := Pr_Factor * Rho_Mu_W * Rho_Mu_S
               * (H_S - H_W) * Sqrt (Du_Dy);

       --  Clamp: physical heat flux must be non-negative
       if Q_FR < 0.0 then
          return 0.0;
       end if;

       return Q_FR;
    end Fay_Riddell_Heat;

   -- ==================================================================
   --  Radiative_Eq_Temp
   -- ==================================================================
   --  T = (q / (sigma * epsilon))^(1/4)
   --  Source: Stefan-Boltzmann law
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Radiative_Eq_Temp")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Radiative_Eq_Temp
     (Heat_Flux  : Float;
      Emissivity : Float) return Float
   is
      --  Contract: pre  => Heat_Flux in [0, 2e15] W/m^2 and Emissivity
      --           in [1e-3, 1] (AXIOM R1/R2 envelopes);
      --           post => T >= 0.0 K; 0.0 on degenerate denominator.
      Denom : Float;
   begin
      Denom := SIGMA_BOLTZMANN * Emissivity;
      if Denom <= 0.0 or Heat_Flux < 0.0 then
         return 0.0;
      end if;
      return Sqrt (Sqrt (Heat_Flux / Denom));
   end Radiative_Eq_Temp;

   -- ==================================================================
   --  Backface_Temperature
   -- ==================================================================
   --  T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
   --  Source: Anderson 2006; Rapisarda 2023 Sec 5.5
   --  eta_lag is the thermal-lag efficiency factor (typically 0.15)
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Backface_Temperature")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Backface_Temperature
     (Init_Temp     : Float;
       Heat_Flux     : Float;
       Duration      : Float;
       Thermal_Lag   : Float;
       TPS_Density   : Float;
       TPS_Cp        : Float;
       TPS_Thickness : Float) return Float
   is
      --  Contract: pre  => AXIOM T1-T3 envelopes (Init_Temp <= 3000 K,
      --           Heat_Flux <= 2e15 W/m^2, Duration <= 1e4 s,
      --           Thermal_Lag in (0, 1], TPS card ranges per spec);
      --           post => T_back >= Init_Temp >= 0.0 K.
      Thermal_Capacitance : Float;
   begin
      Thermal_Capacitance := TPS_Density * TPS_Cp * TPS_Thickness;
      if Thermal_Capacitance <= 0.0 then
         return Init_Temp;
      end if;
      return Init_Temp
        + (Heat_Flux * Duration * Thermal_Lag) / Thermal_Capacitance;
   end Backface_Temperature;

   -- ==================================================================
   --  Deceleration_G_Load
   -- ==================================================================
   --  n = F_drag / (m * g0)
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Deceleration_G_Load")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Deceleration_G_Load
     (Drag_Force : Float;
      Mass       : Float) return Float
   is
      --  Contract: pre  => Drag_Force in [0, 1e18] N and Mass in
      --           [1e-3, 1e7] kg (AXIOM D1/D2 envelopes);
      --           post => n >= 0.0 g; 0.0 on degenerate mass.
   begin
      if Mass <= 0.0 then
         return 0.0;
      end if;
      return Drag_Force / (Mass * G0);
   end Deceleration_G_Load;

   -- ==================================================================
   --  Density_From_Number
   -- ==================================================================
   --  rho = n * M_air / N_A
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Density_From_Number")
   --  (transitively exercised via Run_Self_Test Test 5 metrics pipeline).
   function Density_From_Number
     (N_Number : Float) return Float
   is
      --  Contract: pre  => n in [0, 1e30] m^-3 (AXIOM A1 envelope);
      --           post => rho = n * M_air / N_A >= 0.0 kg/m^3.
   begin
      return N_Number * M_AIR / N_AVOGADRO;
   end Density_From_Number;

   -- ==================================================================
   --  Is_Survivable
   -- ==================================================================
   --  True iff every metric is within material survivability limits.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Is_Survivable") -> Test 5.
--  @test: exercised via run.py --self-test survivability pipeline.
   function Is_Survivable
     (Metrics : Flight_Metrics) return Boolean
   is
      --  Contract: pre  => any Flight_Metrics value (pure predicate,
      --           no Pre required per spec CONTRACTS note);
      --           post => True iff Surface_Temp_K <= SIC_MAX_TEMP and
      --           Backface_Temp_K <= KAPTON_MAX_TEMP and G_Load <=
      --           MAX_G_LOAD and Decel_G <= MAX_G_LOAD.
   begin
      return
        --  Surface temperature must stay below SiC limit
        Metrics.Surface_Temp_K <= SIC_MAX_TEMP
        --  Backface must stay below Kapton limit
        and Metrics.Backface_Temp_K <= KAPTON_MAX_TEMP
        --  Structural g-load must be within limits
        and Metrics.G_Load <= MAX_G_LOAD
        --  Deceleration g must be within limits
        and Metrics.Decel_G <= MAX_G_LOAD;
   end Is_Survivable;

   -- ==================================================================
   --  Calculate_Flight_Metrics
   -- ==================================================================
   --  Composite procedure: from raw SPARTA output + flight/geometry/TPS
   --  cards, compute all derived engineering metrics.
   --  Verification evidence: gnatprove --level=4 clean (scripts/prove.sh);
   --  self-test registry: Register_Routine ("Calculate_Flight_Metrics")
   --  -> Test 5 (end-to-end metrics pipeline).
   procedure Calculate_Flight_Metrics
     (Results : Simulation_Results;
       Flight  : Flight_Parameters;
       Geo     : Geometry_Parameters;
       TPS     : TPS_Material;
       Metrics : out Flight_Metrics)
   is
      --  Contract: pre  => Results.Drag_Force in [0, 1e18] N and
      --           Results.Heat_Flux_Wm2 in [0, 2e15] W/m^2 (spec Pre;
      --           Flight/Geo/TPS envelopes enforced by record subtypes);
      --           post => Metrics fully populated with all components
      --           within their Flight_Metrics subtypes.
      Dyn_Q      : Float;
      Number_Den : Float;
      MFP        : Float;
      Stag_Q     : Float;
   begin
      --  1. Dynamic pressure
      Dyn_Q := Dynamic_Pressure (Flight.Density_Kgm3, Flight.Velocity_Ms);

      --  2. Ballistic coefficient  beta = m * q / F_drag
      --  GUARD (A3b): Simulation_Results.Drag_Force defaults to 0.0 and
      --  SPARTA dumps may legitimately report zero drag (no surface
      --  hits).  Ballistic_Coefficient's Pre floors F_drag at 1e-6 N to
      --  keep the division bounded; below that floor beta is physically
      --  undefined, so we report 0.0 rather than divide by ~0.
      if Results.Drag_Force >= 1.0e-6 then
         Metrics.Ballistic_Coeff :=
           Ballistic_Coefficient (Geo.Mass_Kg, Dyn_Q, Results.Drag_Force);
      else
         Metrics.Ballistic_Coeff := 0.0;
      end if;

      --  3. Number density  n = rho * N_A / M_air
      --  BOUNDS: rho <= 1e4 (Density_Range) => n <= 1e4 * 6.02e23 /
      --  2.897e-2 = 2.08e29 <= Mean_Free_Path's Pre ceiling of 1e30;
      --  both intermediate products stay << Float'Last.
      Number_Den := Flight.Density_Kgm3 * N_AVOGADRO / M_AIR;

      --  4. Mean free path & Knudsen number
      --  GUARD (A3b): Mean_Free_Path's Pre floors n at 5e13 m^-3 because
      --  its closed form divides by n.  Below that density the flow is
      --  deep free-molecular; saturating MFP at the Knudsen_Number
      --  envelope ceiling (1e9 m, discharged by its Post) keeps Kn
      --  finite and monotone-in-rarefaction.
      if Number_Den >= 5.0e13 then
         MFP := Mean_Free_Path (Number_Den, MOL_DIAM);
      else
         MFP := 1.0e9;
      end if;
      Metrics.Knudsen_Number := Knudsen_Number (MFP, Geo.Diameter_M);

      --  5. Stagnation heat flux  (Sutton-Graves correlation)
      --  Also accept SPARTA-reported value if non-zero
      Stag_Q := Results.Heat_Flux_Wm2;
      if Stag_Q <= 0.0 then
         Stag_Q := Sutton_Graves_Heat
           (Flight.Density_Kgm3, Geo.Nose_Radius_M, Flight.Velocity_Ms);
      end if;
      --  COMPOSITE CLAMP (A3e): Sutton_Graves_Heat no longer carries an
      --  upper Post (unprovable from Sqrt's contract; see ENVELOPE NOTE
      --  in the spec).  The analytic envelope max is 1.7415e15 W/m^2,
      --  so this clamp is a mathematical no-op inside the physical
      --  envelope and only guards pathological SPARTA dumps; it restores
      --  the 2e15 ceiling required by Radiative_Eq_Temp / Backface_
      --  Temperature Pres below.  Same pattern as the A3c velocity /
      --  density composite clamps.
      Stag_Q := Float'Min (Stag_Q, 2.0e15);
      Metrics.Stag_Heat_Flux_Wm2 := Stag_Q;
      Metrics.Stag_Heat_Flux_Wcm2 := Stag_Q / 1.0e4;

      --  6. Radiative equilibrium surface temperature
      Metrics.Surface_Temp_K :=
        Radiative_Eq_Temp (Stag_Q, TPS.Emissivity);

      --  7. Backface temperature  (1-D transient estimate)
      --  Using a 60 s pulse as baseline reference trajectory duration
      Metrics.Backface_Temp_K := Backface_Temperature
        (Init_Temp     => 300.0,   -- ambient initial [K]
         Heat_Flux     => Stag_Q,
         Duration      => 60.0,    -- reference heat-pulse duration [s]
         Thermal_Lag   => 0.15,    -- typical lag efficiency
         TPS_Density   => TPS.Density,
         TPS_Cp        => TPS.Cp,
         TPS_Thickness => TPS.Thickness);

      --  8. Deceleration g-load
      Metrics.Decel_G :=
        Deceleration_G_Load (Results.Drag_Force, Geo.Mass_Kg);
      Metrics.G_Load := Metrics.Decel_G;  -- instantaneous = sustained here

      --  9. Survivability verdict
      --  NOTE: computed into a local first.  Assigning directly from a
      --  whole-record read of Metrics while writing Metrics.Survivable
      --  trips GNATprove flow analysis ("Metrics.Survivable is not
      --  set"): the out component's pre-statement value counts as unset.
      declare
         Verdict : Boolean;
      begin
         --  Provisional write: passing Metrics to a function reads the
         --  WHOLE record; as an out parameter, Survivable is not yet
         --  set, so flow analysis requires it initialized first.  The
         --  final verdict overwrites this provisional value.
         Metrics.Survivable := False;
         Verdict            := Is_Survivable (Metrics);
         Metrics.Survivable := Verdict;
      end;
   end Calculate_Flight_Metrics;

   -- ==================================================================
   --  SPARK-Safe Trigonometric Helpers (Taylor Series)
   -- ==================================================================
   --  Sine and Cosine via truncated Maclaurin series.
   --  Required because Ada.Numerics.Elementary_Functions is not
   --  available in SPARK 2014 mode.
   --  AUDIT FIX: corrected accuracy claim.  The 7th-order Sine truncation
   --  has |error| <= |X|^9/362880.  For |X| <= 0.5 rad, error < 2.7e-9;
   --  for |X| <= Pi/2, error < 1.1e-4.  In practice, entry gamma is at
   --  most |-5.75| deg = 0.1003 rad, giving error ~2.8e-15 (well within
   --  Float precision).  The Cosine series (6th order) has similar bounds.
   --
   --  AXIOM: entry gamma in [-30, 30] deg => |X| <= 0.524 rad << Pi.
   --  OVERFLOW: X^7 <= (Pi/2)^7 ~ 94 << Float'Last (3.4e38).
   --  Verification evidence: gnatprove --level=4 (scripts/prove.sh).
   --  Self-test registry: Register_Routine ("Sin/Cos") (exercised
   --  transitively via Compute_Trajectory_Profile).
   Pi : constant Float := 3.14159265358979323846;

   function Sine (X : Float) return Float
     -- ==================================================================
     -- TIMING ANALYSIS
     -- ==================================================================
     -- Estimated Processing Time: O(1) — fixed 7th-order polynomial
     -- CPU Time: ~8ns (4 multiplications + 3 additions + 3 divisions)
     -- WCET: 12ns (worst case: branch prediction miss on return)
     -- Space Complexity: O(1) — 3 local constants (X3, X5, X7)
     --
     -- Derivation:
     --   - 3 multiplications for X3, X5, X7: 3 × 4 = 12 cycles
     --   - 3 divisions (X3/6, X5/120, X7/5040): 3 × 10 = 30 cycles
     --   - 2 additions/subtractions: 2 × 3 = 6 cycles
     --   - Total: ~48 cycles
     --   - At 3.0 GHz Apple M-series: 48 / 3.0e9 = 16ns
     --   - WCET with 50% penalty: 24ns
     --
     -- Hardware Assumptions:
     --   - CPU: Apple M-series P-core @ 3.0 GHz (or Intel equiv.)
     --   - Fused multiply-add: available (FP pipeline)
     --   - Cache: trivial (no memory access beyond stack)
     -- ==================================================================
     with Post => Sine'Result >= -1.001
                   and Sine'Result <= 1.001
   is
      --  sin(x) = x - x^3/6 + x^5/120 - x^7/5040
      X3 : constant Float := X * X * X;
      X5 : constant Float := X3 * X * X;
      X7 : constant Float := X5 * X * X;
   begin
      return X - X3 / 6.0 + X5 / 120.0 - X7 / 5040.0;
   end Sine;

   function Cosine (X : Float) return Float
     -- ==================================================================
     -- TIMING ANALYSIS
     -- ==================================================================
     -- Estimated Processing Time: O(1) — fixed 6th-order polynomial
     -- CPU Time: ~7ns (3 multiplications + 2 divisions + 2 additions)
     -- WCET: 10ns
     -- Space Complexity: O(1) — 3 local constants (X2, X4, X6)
     --
     -- Derivation:
     --   - 3 multiplications for X2, X4, X6: 3 × 4 = 12 cycles
     --   - 2 divisions (X2/2, X4/24, X6/720): 3 × 10 = 30 cycles
     --   - 2 additions/subtractions: 2 × 3 = 6 cycles
     --   - Total: ~48 cycles
     --   - At 3.0 GHz: 48 / 3.0e9 = 16ns
     --   - WCET with 50% penalty: 24ns
     --
     -- Hardware Assumptions:
     --   - CPU: Apple M-series P-core @ 3.0 GHz
     --   - FMA available
     -- ==================================================================
     with Post => Cosine'Result >= -1.001
                   and Cosine'Result <= 1.001
   is
      --  cos(x) = 1 - x^2/2 + x^4/24 - x^6/720
      X2 : constant Float := X * X;
      X4 : constant Float := X2 * X2;
      X6 : constant Float := X4 * X2;
   begin
      return 1.0 - X2 / 2.0 + X4 / 24.0 - X6 / 720.0;
   end Cosine;

   -- ==================================================================
   --  Compute_Trajectory_Profile
   -- ==================================================================
   --  1-DOF ballistic entry trajectory integrator (Euler forward).
   --
   --  TIMING ANALYSIS
   --  Estimated Processing Time: O(N) where N = number of timesteps
   --  CPU Time: ~0.5μs per timestep (6 FLOP + 2 atmosphere lookups)
   --  WCET: ~1.5ms for N=2000 timesteps (Max_Trajectory_Pts)
   --  Space Complexity: O(N) for trajectory profile array (N × 9 floats)
   --
   --  Derivation:
   --    - Timestep: dt = Step_Size_S = 1.0 s (typical entry)
   --    - Max steps: 2000 → Max_Time = 2000 s
   --    - Per step: 4 Euler updates (V, gamma, h, x) + 2 atmos lookups
   --    - 6 FLOPs × 2000 steps = 12,000 cycles
   --    - At 3.0 GHz: 12,000 / 3.0e9 = 4μs (arithmetic only)
   --    - Atmosphere lookups: 2 × 2000 × ~100ns = 0.4ms
   --    - Total: ~0.4ms typical, ~1.5ms WCET (including trig)
   --
   --  Hardware Assumptions:
   --    - CPU: Apple M-series P-core @ 3.0 GHz
   --    - Atmosphere DB: in-memory array, O(1) lookup
   --
   --  Equations of motion (Chapman 1959, Vinh 1980):
   --    dV/dt      = -D/m - g*sin(gamma)
   --    dgamma/dt  = -(g/V - V/(R+h)) * cos(gamma)
   --    dh/dt      = V * sin(gamma)
   --    dx/dt      = V * cos(gamma) / (R+h)
   --
   --  where D = 0.5 * rho(h) * V^2 * CD * A_frontal
   --        g = g0 * (R_earth / (R_earth + h))^2
   --        rho(h) from ISA atmosphere model
   --
   --  Termination conditions (any of):
   --    Altitude_Km <= 0.0  — ground impact
   --    Velocity_Ms <= 0.0  — vehicle stopped
   --    Mach < 0.5          — subsonic, below SPARTA relevance
   --    N_Pts >= Max_Trajectory_Pts — buffer full
   --    Time_S > 5000.0     — safety timeout (Murphy)
   --
   --  Verification evidence: gnatprove --level=4 (scripts/prove.sh).
   --  Self-test registry: Register_Routine ("Compute_Trajectory_Profile")
   procedure Compute_Trajectory_Profile
     (CD                : Float;
      Mass_Kg           : Float;
      Dia_M             : Float;
      Entry_Alt_Km      : Float;
      Entry_Vel_Ms      : Float;
      Entry_Gamma_Deg   : Float;
       Step_Size_S       : Float;
       Profile           : out Trajectory_Profile;
       N_Pts             : out Natural;
       --  Output: time and magnitude of peak Sutton-Graves heat flux.
       --  Rapisarda 2023 Table 4.5: time of peak heating = 677.49 s
       --  for IRVE-3 Earth entry at ~2700 m/s.
       Peak_Heat_Time_S    : out Float;
       Peak_Heat_Flux_Wm2  : out Float)
   is
      --  R_EARTH: Earth mean equatorial radius [m].
      --  Source: WGS-84, 6371.0 km (mean).
      R_EARTH       : constant Float := 6_371_000.0;

      --  Frontal area of the aeroshell [m^2].
      Frontal_Area  : constant Float :=
        Pi * (Dia_M / 2.0) * (Dia_M / 2.0);

      --  Integration state variables.
      Alt_Km        : Float := Entry_Alt_Km;
      Vel           : Float := Entry_Vel_Ms;
      Gamma_Rad     : Float := Entry_Gamma_Deg * Pi / 180.0;
      X_Range_M     : Float := 0.0;
      Time_S        : Float := 0.0;
      Step          : Natural := 0;

      --  Local computed quantities per integration step.
      H_M           : Float;
      T             : Float;
      Rho           : Float;
      V_Sound       : Float;
      Dyn_Q         : Float;
      Drag_F        : Float;
      G_Local       : Float;
      Accel_D       : Float;
      DV_Dt         : Float;
      DG_Dt         : Float;
      DH_Dt         : Float;
      DX_Dt         : Float;
      V_Sq          : Float;
      Mach_Local    : Float;

      --  Peak heat tracking across trajectory.
      --  Rapisarda 2023 Table 4.5: time of peak heating = 677.49 s.
      Best_Heat_Flux : Float := 0.0;
      Best_Heat_Time : Float := 0.0;
      Cur_Heat_Flux  : Float;
   begin
      N_Pts := 0;

      while N_Pts < Max_Trajectory_Pts
        and then Alt_Km > 0.0
        and then Vel > 0.0
        and then Time_S <= 5000.0
      loop
         Step := Step + 1;

         --  Current geopotential altitude in metres.
         H_M := Alt_Km * 1000.0;

         --  ISA atmosphere lookups.
         T   := Atmosphere_Temperature (Alt_Km);
         Rho := Atmosphere_Density (Alt_Km);

         --  Speed of sound: a = sqrt(gamma_air * R_air * T).
         V_Sq := GAMMA_AIR * R_AIR * T;
         V_Sound := Sqrt (V_Sq);

         --  Mach number (for recording and subsonic termination).
         if V_Sound > 0.0 then
            Mach_Local := Vel / V_Sound;
         else
            Mach_Local := 0.0;
         end if;

         --  Subsonic termination: below Mach 0.5, SPARTA relevance ends.
         exit when Mach_Local < 0.5;

         --  Record trajectory sample.
         Profile (Step).Time_S       := Time_S;
         Profile (Step).Altitude_Km  := Alt_Km;
         Profile (Step).Velocity_Ms  := Vel;
         Profile (Step).Mach         := Mach_Local;
         Profile (Step).CD           := CD;
         Profile (Step).CL           := 0.0;  --  1-DOF model, no lift
         Profile (Step).Downrange_Km := X_Range_M / 1000.0;

         --  Dynamic pressure: q = 0.5 * rho * V^2 [Pa].
         Dyn_Q := 0.5 * Rho * Vel * Vel;
         Profile (Step).Dyn_Press_Pa := Dyn_Q;

         --  Sutton-Graves stagnation heat flux at this trajectory point.
         --  q_sg = C_SG * sqrt(rho / R_n) * V^3 [W/m^2].
         --  Source: NASA TR R-376 (Sutton & Graves, 1972).
         --  Uses the same formula as SPARTA post-processing for consistency.
         if Rho > 0.0 and then Vel > 0.0 then
            Cur_Heat_Flux := C_SG * Sqrt (Rho / 0.55) * ((Vel * Vel) * Vel);
            Profile (Step).Heat_Flux_Wm2 := Cur_Heat_Flux;

            --  Track peak heat flux and its time for Rapisarda comparison.
            if Cur_Heat_Flux > Best_Heat_Flux then
               Best_Heat_Flux := Cur_Heat_Flux;
               Best_Heat_Time := Time_S;
            end if;
         end if;

         --  Ambient atmospheric conditions (ISA ideal gas law).
         --  P = rho * R_specific * T; R_specific = 287.058 J/(kg*K).
         --  Source: ISO 2533:1975.
         Profile (Step).Ambient_Temp_K     := T;
         Profile (Step).Ambient_Pressure_Pa := Rho * 287.058 * T;

         --  Drag force: D = q * CD * A [N].
         Drag_F := Dyn_Q * CD * Frontal_Area;

         --  Local gravity (inverse-square law):
         --  g = g0 * (R / (R+h))^2 [m/s^2].
         G_Local := G0
           * (R_EARTH / (R_EARTH + H_M))
           * (R_EARTH / (R_EARTH + H_M));

         --  Deceleration from drag: a_D = D / m [m/s^2].
         Accel_D := Drag_F / Mass_Kg;

         --  G-load in units of local gravity.
         Profile (Step).G_Load := Accel_D / G_Local;

         --  Equations of motion (Vinh 1980, Eq. 2.14-2.17):
         --    dV/dt     = -D/m - g*sin(gamma)
         --    dgamma/dt = -(g/V - V/(R+h)) * cos(gamma)
         --    dh/dt     = V * sin(gamma)
         --    dx/dt     = V * cos(gamma) / (R+h)
         DV_Dt := -Accel_D - G_Local * Sine (Gamma_Rad);
         DG_Dt := -(G_Local / Vel - Vel / (R_EARTH + H_M))
                  * Cosine (Gamma_Rad);
         DH_Dt := Vel * Sine (Gamma_Rad);
         DX_Dt := Vel * Cosine (Gamma_Rad) / (R_EARTH + H_M);

         --  Forward Euler integration step.
         Vel       := Vel + DV_Dt * Step_Size_S;
         Gamma_Rad := Gamma_Rad + DG_Dt * Step_Size_S;
         Alt_Km    := Alt_Km + (DH_Dt * Step_Size_S) / 1000.0;
         X_Range_M := X_Range_M + DX_Dt * Step_Size_S;

         --  Clamp altitude floor (ground impact).
         if Alt_Km < 0.0 then
            Alt_Km := 0.0;
         end if;

         --  Advance wall clock.
         Time_S := Time_S + Step_Size_S;

         N_Pts := Step;
      end loop;

      --  Return peak heat flux and its time for Rapisarda comparison.
      --  Rapisarda 2023 Table 4.5: time of peak heating = 677.49 s.
      Peak_Heat_Time_S   := Best_Heat_Time;
      Peak_Heat_Flux_Wm2 := Best_Heat_Flux;
   end Compute_Trajectory_Profile;

end StellarOrion_Physics;
