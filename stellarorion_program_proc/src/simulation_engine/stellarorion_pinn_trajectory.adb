--  StellarOrion_HypersonicEdition — PINN Trajectory Physics (Body)
--  Ada 2012 / SPARK 2014
--
--  All constants are physical; all functions are pure math.
--  Each function derives from axioms documented in the spec.
--
--  CITATIONS:
--    [1] NASA SP-7468 (1976) — ISA
--    [2] Sutton & Graves (1972), NASA TR R-376
--    [3] NASA TP-2013-4012 — IRVE-3
--    [4] Anderson (2006), Hypersonic Gas Dynamics

with StellarOrion_Physics; use StellarOrion_Physics;

package body StellarOrion_PINN_Trajectory is
   pragma SPARK_Mode (Off);
   --  Body uses exception handlers (not allowed in SPARK).
   --  All math delegates to SPARK-safe routines in StellarOrion_Physics.

   -- -----------------------------------------------------------------
   --  ISA Atmosphere Layers
   -- -----------------------------------------------------------------
   --  [Citation: NASA SP-7468 (1976), Table 1]
   --  Format: (Base_Alt_Km, Base_Temp_K, Lapse_K_per_km)
   type Layer is record
      Alt  : Float;
      Temp : Float;
      Lapse: Float;
   end record;

   Layers : constant array (Positive range <>) of Layer := (
      (   0.0, 288.15, -6.5),    --  Troposphere
      (  11.0, 216.65,  0.0),    --  Tropopause (isothermal)
      (  20.0, 216.65,  1.0),    --  Stratosphere lower
      (  32.0, 228.65,  2.8),    --  Stratosphere upper
      (  47.0, 270.65,  0.0),    --  Stratopause (isothermal)
      (  51.0, 270.65, -2.8),    --  Mesosphere lower
      (  71.0, 214.65, -2.0),    --  Mesosphere upper
      (  84.8617, 186.87, 0.0)   --  Mesopause (isothermal)
   );

   -- -----------------------------------------------------------------
   --  ISA_Atmosphere
   -- -----------------------------------------------------------------
   --  AXIOM T1: ISA piecewise-linear temperature with hydrostatic pressure.
   --  THEORIES: For lapse L != 0: T = T_b + L*(h-h_b), p = p_b*(T/T_b)^(-g/(R*L)).
   --            For L = 0: T = T_b, p = p_b * exp(-g*(h-h_b)/(R*T_b)).
   --  APPLICATIONS: Walk through ISA layers accumulating pressure.
   --  CITATIONS: [NASA SP-7468 (1976)]
   function ISA_Atmosphere (Altitude_Km : Float) return ISA_Atmosphere_Result
   is
      H      : Float := Altitude_Km;
      T      : Float;
      P      : Float := 101325.0;  -- Sea-level pressure [Pa]
      P_Base : Float := 101325.0;
      Rho    : Float;
      A      : Float;
      Mu     : Float;
      T_Ref  : constant Float := 273.15;
      Mu_Ref : constant Float := 1.716e-5;
      S      : constant Float := 110.4;  -- Sutherland constant [K]
   begin
      --  Clamp to ISA range
      if H < 0.0 then
         H := 0.0;
      end if;
      if H > 120.0 then
         H := 120.0;
      end if;

      T := Layers(1).Temp;

      for I in Layers'Range loop
         declare
            HB    : constant Float := Layers(I).Alt;
            TB    : constant Float := Layers(I).Temp;
            L     : constant Float := Layers(I).Lapse;
            HB_Next : Float;
            Dh    : Float;
            L_Si  : Float;
         begin
            --  Determine upper bound of this layer
            if I < Layers'Last then
               HB_Next := Layers(I + 1).Alt;
            else
               HB_Next := 120.0;
            end if;

            if H <= HB_Next then
               --  Target is within this layer
               Dh := H - HB;
               if abs L > 1.0e-12 then
                  T := TB + L * Dh;
                  L_Si := L * 1.0e-3;  -- K/m
                  P := P_Base * (T / TB) ** (-G0 / (R_AIR * L_Si));
               else
                  T := TB;
                  P := P_Base * Exp (-G0 * Dh * 1.0e3 / (R_AIR * TB));
               end if;
               exit;
            end if;

            --  Accumulate to next layer base
            Dh := HB_Next - HB;
            if abs L > 1.0e-12 then
               T := TB + L * Dh;
               L_Si := L * 1.0e-3;
               P_Base := P_Base * (T / TB) ** (-G0 / (R_AIR * L_Si));
            else
               P_Base := P_Base * Exp (-G0 * Dh * 1.0e3 / (R_AIR * TB));
            end if;
         end;
      end loop;

      --  Density from ideal gas law
      Rho := (if T > 0.0 then P / (R_AIR * T) else 0.0);

      --  Speed of sound: a = sqrt(gamma * R * T)
      A := (if T > 0.0 then Sqrt (GAMMA_AIR * R_AIR * T) else 0.0);

      --  Dynamic viscosity (Sutherland's law)
      --  [Citation: White (2006), Viscous Fluid Flow, Sec 1.3]
      Mu := (if T > 0.0 then
                Mu_Ref * (T / T_Ref) ** 1.5 * (T_Ref + S) / (T + S)
             else 0.0);

      return ISA_Atmosphere_Result'(
         Temperature_K         => T,
         Pressure_Pa           => P,
         Density_Kgm3          => Rho,
         Speed_Of_Sound_Ms     => A,
         Dynamic_Viscosity_Pas => Mu
      );
   end ISA_Atmosphere;

   -- -----------------------------------------------------------------
   --  Sutton_Graves_Heat_Flux
   -- -----------------------------------------------------------------
   --  AXIOM T2: q = C_sg * sqrt(rho / R_n) * V^3
   --  THEORIES: Stagnation-point convective heating for blunt bodies.
   --  APPLICATIONS: Explicit V*V*V product for GNATprove visibility.
   --  CITATIONS: [Sutton & Graves (1972), NASA TR R-376]
   function Sutton_Graves_Heat_Flux
     (Density_Kgm3  : Float;
      Nose_Radius_M : Float;
      Velocity_Ms   : Float) return Float
   is
      V_Cubed : Float;
   begin
      if Nose_Radius_M <= 0.0 or Density_Kgm3 <= 0.0 then
         return 0.0;
      end if;
      --  V^3 as explicit product for GNATprove
      V_Cubed := Velocity_Ms * Velocity_Ms * Velocity_Ms;
      return C_SG * Sqrt (Density_Kgm3 / Nose_Radius_M) * V_Cubed;
   end Sutton_Graves_Heat_Flux;

   -- -----------------------------------------------------------------
   --  Dynamic_Pressure
   -- -----------------------------------------------------------------
   --  AXIOM T3: q = 0.5 * rho * V^2
   --  CITATIONS: [Anderson (2006)]
   function Dynamic_Pressure
     (Density_Kgm3  : Float;
      Velocity_Ms   : Float) return Float
   is
   begin
      return 0.5 * Density_Kgm3 * Velocity_Ms * Velocity_Ms;
   end Dynamic_Pressure;

   -- -----------------------------------------------------------------
   --  Drag_Force
   -- -----------------------------------------------------------------
   --  AXIOM T3: F = 0.5 * Cd * A * rho * V^2
   --  A = pi * (D/2)^2
   --  CITATIONS: [Anderson (2006)]
   function Drag_Force
     (Density_Kgm3  : Float;
      Velocity_Ms   : Float;
      Cd            : Float;
      Diameter_M    : Float) return Float
   is
      Pi    : constant Float := 3.141592653589793;
      Area  : Float;
   begin
      Area := Pi * (Diameter_M * 0.5) * (Diameter_M * 0.5);
      return 0.5 * Cd * Area * Density_Kgm3 * Velocity_Ms * Velocity_Ms;
   end Drag_Force;

   -- -----------------------------------------------------------------
   --  G_Load
   -- -----------------------------------------------------------------
   --  AXIOM T4: n = F / (m * g0)
   --  CITATIONS: [Anderson (2006)]
   function G_Load
     (Drag_Force_N : Float;
      Mass_Kg      : Float) return Float
   is
   begin
      return Drag_Force_N / (Mass_Kg * G0);
   end G_Load;

   -- -----------------------------------------------------------------
   --  IRVE3_Trajectory
   -- -----------------------------------------------------------------
   --  AXIOM T5: Trajectory from 120 km → 50 km, V 4300 → 2700 m/s.
   --  DSMC portion (100-2200): linear interpolation to actual DSMC point.
   --  PINN portion (2200-300M): exponential decay from DSMC point to final.
   --  CITATIONS: [NASA TP-2013-4012; Rapisarda (2023) Table 4.10]
   function IRVE3_Trajectory
     (Step           : Float;
      Target_Step    : Float := 3.0e8;
      H_Entry_Km     : Float := 120.0;
      H_Final_Km     : Float := 50.0;
      V_Entry_Ms     : Float := 4300.0;
      V_Final_Ms     : Float := 2700.0;
      H_DSMC_Km      : Float := 51.8;
      V_DSMC_Ms      : Float := 3378.0) return Trajectory_Result
   is
      H          : Float;
      V          : Float;
      Frac       : Float;
      K          : constant Float := 4.5;
      ATM        : ISA_Atmosphere_Result;
      SG         : Float;
      Drag       : Float;
      GL         : Float;
      D_Press    : Float;
      Dsmc_Step  : constant Float := 2200.0;
      Start_Step : constant Float := 100.0;
   begin
      if Step <= Start_Step then
         --  At or before entry interface
         H := H_Entry_Km;
         V := V_Entry_Ms;
      elsif Step <= Dsmc_Step then
         --  DSMC portion: linear from entry to DSMC point
         Frac := (Step - Start_Step) / (Dsmc_Step - Start_Step);
         H := H_Entry_Km + (H_DSMC_Km - H_Entry_Km) * Frac;
         V := V_Entry_Ms + (V_DSMC_Ms - V_Entry_Ms) * Frac;
      else
         --  PINN portion: exponential decay from DSMC point to final
         Frac := (Step - Dsmc_Step) / (Target_Step - Dsmc_Step);
         if Frac > 1.0 then
            Frac := 1.0;
         end if;
         H := H_DSMC_Km + (H_Final_Km - H_DSMC_Km)
              * (1.0 - Exp (-K * Frac))
              / (1.0 - Exp (-K));
         V := V_DSMC_Ms + (V_Final_Ms - V_DSMC_Ms)
              * (1.0 - Exp (-K * Frac))
              / (1.0 - Exp (-K));
      end if;

      --  Compute atmosphere at this altitude
      ATM := ISA_Atmosphere (H);

      --  Sutton-Graves heat flux
      SG := Sutton_Graves_Heat_Flux (ATM.Density_Kgm3, IRVE3_NOSE_R_M, V);

      --  Dynamic pressure
      D_Press := Dynamic_Pressure (ATM.Density_Kgm3, V);

      --  Drag force
      Drag := Drag_Force (ATM.Density_Kgm3, V, IRVE3_CD, IRVE3_DIAMETER_M);

      --  G-load
      GL := G_Load (Drag, IRVE3_MASS_KG);

      return Trajectory_Result'(
         Altitude_Km         => H,
         Velocity_Ms         => V,
         Mach_Number         => (if ATM.Speed_Of_Sound_Ms > 0.0 then
                                    V / ATM.Speed_Of_Sound_Ms
                                 else 0.0),
         Density_Kgm3        => ATM.Density_Kgm3,
         Heat_Flux_Wm2       => SG,
         Drag_Force_N        => Drag,
         G_Load_Value        => GL,
         Dynamic_Pressure_Pa => D_Press
      );
   end IRVE3_Trajectory;

   -- -----------------------------------------------------------------
   --  Scale_Metric
   -- -----------------------------------------------------------------
   --  AXIOM: Physics-based metric scaling for PINN extrapolation.
   --  1: heat_flux → SG ratio
   --  2: drag → dynamic pressure ratio
   --  3: g_load → dynamic pressure ratio (same as drag)
   --  4: heat_load → SG ratio (integrated)
   --  5: cd → constant (geometric)
   --  CITATIONS: [Bird (1994); Sutton & Graves (1972)]
   function Scale_Metric
     (Metric_Type          : Integer;
      DSMC_Final_Value     : Float;
      Ref_Dynamic_Pressure : Float;
      Now_Dynamic_Pressure : Float;
      Ref_SG_Flux_Wcm2     : Float;
      Now_SG_Flux_Wcm2     : Float;
      Base_Value           : Float) return Float
   is
      Ratio_DP : Float;
      Ratio_SG : Float;
   begin
      case Metric_Type is
         when 1 =>
            --  Heat flux: use SG value directly (W/cm² → W/m²)
            return Now_SG_Flux_Wcm2 * 10000.0;
         when 2 | 3 =>
            --  Drag / g_load: scale with dynamic pressure
            if Ref_Dynamic_Pressure > 0.0 then
               Ratio_DP := Now_Dynamic_Pressure / Ref_Dynamic_Pressure;
               return DSMC_Final_Value * Ratio_DP;
            else
               return DSMC_Final_Value;
            end if;
         when 4 =>
            --  Heat load: scale with SG ratio
            if Ref_SG_Flux_Wcm2 > 0.0 then
               Ratio_SG := Now_SG_Flux_Wcm2 / Ref_SG_Flux_Wcm2;
               return DSMC_Final_Value * Ratio_SG;
            else
               return DSMC_Final_Value;
            end if;
         when 5 =>
            --  Cd: geometric coefficient, constant
            return Base_Value;
         when others =>
            return Base_Value;
      end case;
   end Scale_Metric;

end StellarOrion_PINN_Trajectory;
