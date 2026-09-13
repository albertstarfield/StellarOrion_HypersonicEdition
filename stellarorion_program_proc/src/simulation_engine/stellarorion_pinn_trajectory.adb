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
   --  Body uses exception handlers and Ada.Text_IO (not allowed in SPARK).
   --  All math delegates to SPARK-safe routines in StellarOrion_Physics.

   -- -----------------------------------------------------------------
   --  Local Sqrt (Newton-Raphson, 25 iterations)
   --  [Citation: Newton 1671, Method of Fluxions]
   -- -----------------------------------------------------------------
   function Local_Sqrt (X : Float) return Float is
      Y     : Float;
      Y_New : Float;
   begin
      if X <= 0.0 then
         return 0.0;
      end if;
      Y := X / 2.0;
      if Y < 1.0 then
         Y := 1.0;
      end if;
      for I in 1 .. 25 loop
         pragma Unreferenced (I);
         Y_New := (Y + X / Y) / 2.0;
         Y     := Y_New;
      end loop;
      return Y;
   end Local_Sqrt;

   -- -----------------------------------------------------------------
   --  ISA Atmosphere Layers
   -- -----------------------------------------------------------------
   --  [Citation: NASA SP-7468 (1976), Table 1]
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
   --  THEORIES: For lapse L /= 0: T = T_b + L*(h-h_b), p = p_b*(T/T_b)^(-g/(R*L)).
   --            For L = 0: T = T_b, p = p_b * exp(-g*(h-h_b)/(R*T_b)).
   --  NOTE: (T/T_b)**X is implemented as Exp(X * Ln(T/T_b)) because
   --        Ada's ** operator requires Integer exponent.
   --  CITATIONS: [NASA SP-7468 (1976)]
   function ISA_Atmosphere (Altitude_Km : Float) return ISA_Atmosphere_Result
   is
      H      : Float := Altitude_Km;
      T      : Float;
      P      : Float := 101325.0;
      P_Base : Float := 101325.0;
      Rho    : Float;
      A      : Float;
      Mu     : Float;
      T_Ref  : constant Float := 273.15;
      Mu_Ref : constant Float := 1.716e-5;
      S      : constant Float := 110.4;
   begin
      if H < 0.0 then
         H := 0.0;
      end if;
      if H > 120.0 then
         H := 120.0;
      end if;

      T := Layers(1).Temp;

      for I in Layers'Range loop
         declare
            HB      : constant Float := Layers(I).Alt;
            TB      : constant Float := Layers(I).Temp;
            L       : constant Float := Layers(I).Lapse;
            HB_Next : Float;
            Dh      : Float;
            L_Si    : Float;
            Exponent: Float;
         begin
            if I < Layers'Last then
               HB_Next := Layers(I + 1).Alt;
            else
               HB_Next := 120.0;
            end if;

            if H <= HB_Next then
               Dh := H - HB;
               if abs L > 1.0e-12 then
                  T := TB + L * Dh;
                  L_Si := L * 1.0e-3;
                  --  (T/TB)**(-G0/(R*L_Si)) = Exp(-G0/(R*L_Si) * Ln(T/TB))
                  Exponent := -G0 / (R_AIR * L_Si);
                  P := P_Base * Exp (Exponent * Ln (T / TB));
               else
                  T := TB;
                  P := P_Base * Exp (-G0 * Dh * 1.0e3 / (R_AIR * TB));
               end if;
               exit;
            end if;

            Dh := HB_Next - HB;
            if abs L > 1.0e-12 then
               T := TB + L * Dh;
               L_Si := L * 1.0e-3;
               Exponent := -G0 / (R_AIR * L_Si);
               P_Base := P_Base * Exp (Exponent * Ln (T / TB));
            else
               P_Base := P_Base * Exp (-G0 * Dh * 1.0e3 / (R_AIR * TB));
            end if;
         end;
      end loop;

      --  Density from ideal gas law
      if T > 0.0 then
         Rho := P / (R_AIR * T);
      else
         Rho := 0.0;
      end if;

      --  Speed of sound: a = sqrt(gamma * R * T)
      if T > 0.0 then
         A := Local_Sqrt (GAMMA_AIR * R_AIR * T);
      else
         A := 0.0;
      end if;

      --  Dynamic viscosity (Sutherland's law)
      --  [Citation: White (2006), Viscous Fluid Flow, Sec 1.3]
      --  mu = mu_ref * (T/T_ref)**1.5 * (T_ref+S)/(T+S)
      --  (T/T_ref)**1.5 = Exp(1.5 * Ln(T/T_ref))
      if T > 0.0 then
         Mu := Mu_Ref * Exp (1.5 * Ln (T / T_Ref)) * (T_Ref + S) / (T + S);
      else
         Mu := 0.0;
      end if;

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
      V_Cubed := Velocity_Ms * Velocity_Ms * Velocity_Ms;
      return C_SG * Local_Sqrt (Density_Kgm3 / Nose_Radius_M) * V_Cubed;
   end Sutton_Graves_Heat_Flux;

   -- -----------------------------------------------------------------
   --  Dynamic_Pressure
   -- -----------------------------------------------------------------
   --  AXIOM T3: q = 0.5 * rho * V^2
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
   function Drag_Force
     (Density_Kgm3  : Float;
      Velocity_Ms   : Float;
      Cd            : Float;
      Diameter_M    : Float) return Float
   is
      Pi   : constant Float := 3.141592653589793;
      Area : Float;
   begin
      Area := Pi * (Diameter_M * 0.5) * (Diameter_M * 0.5);
      return 0.5 * Cd * Area * Density_Kgm3 * Velocity_Ms * Velocity_Ms;
   end Drag_Force;

   -- -----------------------------------------------------------------
   --  G_Load
   -- -----------------------------------------------------------------
   --  AXIOM T4: n = F / (m * g0)
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
   --  AXIOM T5: Trajectory from 120 km to 50 km, V 4300 to 2700 m/s.
   --  DSMC portion (100-2200): linear to actual DSMC point (51.8 km).
   --  PINN portion (2200-300M): exponential decay to final altitude.
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
      Exp_Neg_K  : Float;
      Exp_Neg_KF : Float;
      ATM        : ISA_Atmosphere_Result;
      SG         : Float;
      Drag       : Float;
      GL         : Float;
      D_Press    : Float;
      Dsmc_Step  : constant Float := 2200.0;
      Start_Step : constant Float := 100.0;
      Mach_Val   : Float;
   begin
      if Step <= Start_Step then
         H := H_Entry_Km;
         V := V_Entry_Ms;
      elsif Step <= Dsmc_Step then
         Frac := (Step - Start_Step) / (Dsmc_Step - Start_Step);
         H := H_Entry_Km + (H_DSMC_Km - H_Entry_Km) * Frac;
         V := V_Entry_Ms + (V_DSMC_Ms - V_Entry_Ms) * Frac;
      else
         Frac := (Step - Dsmc_Step) / (Target_Step - Dsmc_Step);
         if Frac > 1.0 then
            Frac := 1.0;
         end if;
         --  Pre-compute exponentials to avoid repeated calls
         Exp_Neg_K := Exp (-K);
         Exp_Neg_KF := Exp (-K * Frac);
         H := H_DSMC_Km + (H_Final_Km - H_DSMC_Km)
              * (1.0 - Exp_Neg_KF) / (1.0 - Exp_Neg_K);
         V := V_DSMC_Ms + (V_Final_Ms - V_DSMC_Ms)
              * (1.0 - Exp_Neg_KF) / (1.0 - Exp_Neg_K);
      end if;

      ATM := ISA_Atmosphere (H);
      SG := Sutton_Graves_Heat_Flux (ATM.Density_Kgm3, IRVE3_NOSE_R_M, V);
      D_Press := Dynamic_Pressure (ATM.Density_Kgm3, V);
      Drag := Drag_Force (ATM.Density_Kgm3, V, IRVE3_CD, IRVE3_DIAMETER_M);
      GL := G_Load (Drag, IRVE3_MASS_KG);

      if ATM.Speed_Of_Sound_Ms > 0.0 then
         Mach_Val := V / ATM.Speed_Of_Sound_Ms;
      else
         Mach_Val := 0.0;
      end if;

      return Trajectory_Result'(
         Altitude_Km         => H,
         Velocity_Ms         => V,
         Mach_Number         => Mach_Val,
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
            return Now_SG_Flux_Wcm2 * 10000.0;
         when 2 | 3 =>
            if Ref_Dynamic_Pressure > 0.0 then
               Ratio_DP := Now_Dynamic_Pressure / Ref_Dynamic_Pressure;
               return DSMC_Final_Value * Ratio_DP;
            else
               return DSMC_Final_Value;
            end if;
         when 4 =>
            if Ref_SG_Flux_Wcm2 > 0.0 then
               Ratio_SG := Now_SG_Flux_Wcm2 / Ref_SG_Flux_Wcm2;
               return DSMC_Final_Value * Ratio_SG;
            else
               return DSMC_Final_Value;
            end if;
         when 5 =>
            return Base_Value;
         when others =>
            return Base_Value;
      end case;
   end Scale_Metric;

end StellarOrion_PINN_Trajectory;
