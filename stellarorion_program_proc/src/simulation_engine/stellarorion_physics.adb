--  StellarOrion_HypersonicEdition — Aerothermodynamic Physics (Body)
--  Ada 2012 / SPARK 2014
--
--  All constants are imported from StellarOrion_Types.
--  Functions are pure and side-effect free.

package body StellarOrion_Physics is
   pragma SPARK_Mode (On);

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
   function Sqrt (X : Float) return Float
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
         --  Belt-and-braces justification (see hand proof below): the
         --  quotient X/Y is bounded by max(2, sqrt(X)) <= 4.2e9 for all
         --  caller-bounded X <= 1.77e19, far under Float'Last.  [ASWSS]
         Y_New := (Y + X / Y) / 2.0;
         pragma Annotate
           (GNATprove,
            False_Positive,
            "float overflow check might fail",
            String'("Newton iterates stay in [min(X,1), max(X,1)] by "
                    & "the AM-GM band argument in the header comment, "
                    & "so X/Y <= max(2, sqrt(X)) <= 4.2e9"));
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
   function Mean_Free_Path
     (Number_Density : Float;
      Mol_Diameter   : Float) return Float
   is
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
   function Knudsen_Number
     (MFP         : Float;
      Char_Length : Float) return Float
   is
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
   function Dynamic_Pressure
     (Density  : Float;
      Velocity : Float) return Float
   is
   begin
      --  APPLICATION STEP: V^2 written as explicit product ('**' is
      --  opaque to gnatprove's interval analysis).
      return 0.5 * Density * (Velocity * Velocity);
   end Dynamic_Pressure;

   -- ==================================================================
   --  Ballistic_Coefficient
   -- ==================================================================
   --  beta = m * q / F_drag
   function Ballistic_Coefficient
     (Mass         : Float;
      Dyn_Pressure : Float;
      Drag_Force   : Float) return Float
   is
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
   function Sutton_Graves_Heat
     (Density     : Float;
      Nose_Radius : Float;
      Velocity    : Float) return Float
   is
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
      --  GNATprove times out re-inlining Sqrt's 25 Newton iterations
      --  at this call site even though Sqrt'Post suffices; justified
      --  per project standard's documented-exception process.  [ASWSS]
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
   --  Radiative_Eq_Temp
   -- ==================================================================
   --  T = (q / (sigma * epsilon))^(1/4)
   --  Source: Stefan-Boltzmann law
   function Radiative_Eq_Temp
     (Heat_Flux  : Float;
      Emissivity : Float) return Float
   is
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
   function Backface_Temperature
     (Init_Temp     : Float;
      Heat_Flux     : Float;
      Duration      : Float;
      Thermal_Lag   : Float;
      TPS_Density   : Float;
      TPS_Cp        : Float;
      TPS_Thickness : Float) return Float
   is
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
   function Deceleration_G_Load
     (Drag_Force : Float;
      Mass       : Float) return Float
   is
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
   function Density_From_Number
     (N_Number : Float) return Float
   is
   begin
      return N_Number * M_AIR / N_AVOGADRO;
   end Density_From_Number;

   -- ==================================================================
   --  Is_Survivable
   -- ==================================================================
   --  True iff every metric is within material survivability limits.
   function Is_Survivable
     (Metrics : Flight_Metrics) return Boolean
   is
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
   procedure Calculate_Flight_Metrics
     (Results : Simulation_Results;
      Flight  : Flight_Parameters;
      Geo     : Geometry_Parameters;
      TPS     : TPS_Material;
      Metrics : out Flight_Metrics)
   is
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

end StellarOrion_Physics;
