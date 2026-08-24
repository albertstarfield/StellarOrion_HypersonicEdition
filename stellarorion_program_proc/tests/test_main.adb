-- StellarOrion HypersonicEdition -- Unit Test Harness
-- =====================================================
--
--  Standalone unit-test runner for the SPARK simulation-engine
--  packages (physics, geometry, validation, environment).
--
--  DESIGN NOTE (Tier A9): this harness replaces the earlier
--  tests/test_physics.adb + tests/test_suite.adb AUnit stubs, which
--  were never compilable (package bodies without specs, suite body
--  malformed, directory absent from every GPR, no aunit crate
--  dependency).  Rather than introduce a new external dependency,
--  the valuable assertions of those stubs were ported here into a
--  zero-dependency AAA-style runner with corrected expected values
--  (the stub's Mean_Free_Path expectation was arithmetically wrong:
--  1/(sqrt(2)*pi*d^2*n) at n=1e23, d=3.7e-10 is ~1.64e-5 m, not
--  ~5.2e-3 m).
--
--  All call arguments respect the AXIOM envelope contracts introduced
--  in Tier A3 (commits 525ab7e..072c263); several tests deliberately
--  sit ON contract boundaries as regression guards.
--
--  Tier B additions: deep unit tests for StellarOrion_Atomic_Parity
--  (popcount, parity predicate, XOR checksum, corruption detection,
--  recovery strategy) and StellarOrion_Dual_Watchdog (grace ladder,
--  cross-monitoring recovery, emergency latch) beyond the smoke-level
--  self-test coverage embedded in the production binary.
--
--  Build & run (from stellarorion_program_proc/):
--    alr exec -- gprbuild -P tests/stellarorion_tests.gpr -j0
--    ./bin/test_main
--
--  Exit status: 0 iff every check passes.

with Ada.Text_IO;             use Ada.Text_IO;
with Ada.Command_Line;
with Interfaces;

with StellarOrion_Types;       use StellarOrion_Types;
with StellarOrion_Physics;     use StellarOrion_Physics;
with StellarOrion_Geometry;    use StellarOrion_Geometry;
with StellarOrion_Environment; use StellarOrion_Environment;
with StellarOrion_Atomic_Parity;
with StellarOrion_Dual_Watchdog;

procedure Test_Main is

   Tests_Run : Natural := 0;
   Failures  : Natural := 0;

   ---------------------------------------------------------------
   --  Minimal assertion reporter (AAA: the caller Arranges and Acts
   --  locally, then Asserts here).  One Check per behaviour.
   ---------------------------------------------------------------
   procedure Check (Name : String; Condition : Boolean; Detail : String := "") is
   begin
      Tests_Run := Tests_Run + 1;
      if Condition then
         Put_Line ("PASS: " & Name);
      else
         Failures := Failures + 1;
         Put_Line ("FAIL: " & Name &
                   (if Detail = "" then "" else "  --  " & Detail));
      end if;
   end Check;

begin
   Put_Line ("=== StellarOrion HypersonicEdition :: Unit Tests ===");

   -------------------------------------------------------------
   --  Physics: rarefied gas dynamics
   -------------------------------------------------------------
   declare
      --  Arrange: n = 1e23 m^-3, d = 3.7e-10 m (air molecule).
      --  Act: lambda = 1/(sqrt(2) pi d^2 n) ~= 1.644e-5 m.
      Lambda : constant Float := Mean_Free_Path (1.0e23, 3.7e-10);
   begin
      Check ("Mean_Free_Path standard-air order of magnitude",
             Lambda > 1.0e-5 and Lambda < 1.0e-4,
             "lambda = " & Float'Image (Lambda));
   end;

   declare
      --  Kn = lambda/L with L = 3.0 m aeroshell diameter:
      --  continuum regime requires Kn < 0.01 (Bird 1994).
      Kn : constant Float := Knudsen_Number (5.2e-3, 3.0);
   begin
      Check ("Knudsen_Number continuum regime",
             Kn > 1.0e-4 and Kn < 0.01,
             "Kn = " & Float'Image (Kn));
   end;

   declare
      --  rho = 1e23 * 28.97e-3 / 6.02214076e23 ~= 4.811e-3 kg/m^3.
      Rho : constant Float := Density_From_Number (1.0e23);
   begin
      Check ("Density_From_Number trace-atmosphere value",
             Rho > 4.5e-3 and Rho < 5.1e-3,
             "rho = " & Float'Image (Rho));
   end;

   -------------------------------------------------------------
   --  Physics: aerodynamic / aerothermodynamic metrics
   -------------------------------------------------------------
   declare
      --  Exact analytic identity: q = 0.5 * rho * V^2.
      Q_Pa : constant Float := Dynamic_Pressure (1.225, 100.0);
   begin
      Check ("Dynamic_Pressure analytic value at sea-level dynamic case",
             abs (Q_Pa - 6125.0) < 0.01,
             "q = " & Float'Image (Q_Pa));
   end;

   declare
      --  beta = m*q/F_drag = 281*2.54e6/4500 ~= 1.5861e5 kg/m^2 for
      --  the stub's stress-case inputs (IRVE-3-like magnitudes are
      --  covered by Run_Self_Test in the production binary).
      Beta : constant Float := Ballistic_Coefficient (281.0, 2.54e6, 4500.0);
   begin
      Check ("Ballistic_Coefficient matches m*q/F",
             Beta > 1.585e5 and Beta < 1.587e5,
             "beta = " & Float'Image (Beta));
   end;

   declare
      --  Sutton-Graves: q_dot = C_sg*sqrt(rho/R_n)*V^3
      --  = 1.7415e-4 * sqrt(6.9674e-4/0.55) * 2700^3 ~= 1.220e5 W/m^2
      --  (Mach 10 @ 52 km reference trajectory).
      Q_Dot : constant Float := Sutton_Graves_Heat (6.9674e-4, 0.55, 2700.0);
   begin
      Check ("Sutton_Graves_Heat Mach-10 reference flux",
             Q_Dot > 1.15e5 and Q_Dot < 1.30e5,
             "q_dot = " & Float'Image (Q_Dot));
   end;

   declare
      --  T_surf = (q_dot/(sigma*eps))^(1/4) ~= 1347 K at the IRVE-3
      --  peak heat-flux proxy 1.4e5 W/m^2 with eps = 0.75.
      T_Surf : constant Float := Radiative_Eq_Temp (1.4e5, 0.75);
   begin
      Check ("Radiative_Eq_Temp Stefan-Boltzmann balance",
             T_Surf > 1330.0 and T_Surf < 1365.0,
             "T = " & Float'Image (T_Surf));
   end;

   declare
      --  1-D transient conduction proxy: T_back = 300 +
      --  q*dt*eta/(rho*Cp*delta) = 300 + 2.1e6/41015.92 ~= 351.2 K.
      T_Back : constant Float :=
        Backface_Temperature (300.0, 1.4e5, 100.0, 0.15, 1468.0, 1100.0, 0.0254);
   begin
      Check ("Backface_Temperature heats above initial",
             T_Back > 340.0 and T_Back < 365.0,
             "T_back = " & Float'Image (T_Back));
   end;

   declare
      --  n_z = F/(m*g0) = 4500/(281*9.80665) ~= 1.633 g.
      G_Load : constant Float := Deceleration_G_Load (4500.0, 281.0);
   begin
      Check ("Deceleration_G_Load analytic value",
             G_Load > 1.55 and G_Load < 1.72,
             "g = " & Float'Image (G_Load));
   end;

   -------------------------------------------------------------
   --  Survivability verdict
   -------------------------------------------------------------
   declare
      Metrics : constant Flight_Metrics :=
        (Ballistic_Coeff     => 26.9,
         Knudsen_Number      => 0.001,
         Stag_Heat_Flux_Wm2  => 1.4e5,
         Stag_Heat_Flux_Wcm2 => 14.0,
         Surface_Temp_K      => 1200.0,
         Backface_Temp_K     => 400.0,
         Decel_G             => 19.0,
         G_Load              => 19.0,
         Survivable          => True);
   begin
      Check ("Is_Survivable accepts IRVE-3-like metrics",
             Is_Survivable (Metrics),
             "verdict was False");
   end;

   -------------------------------------------------------------
   --  Geometry validation
   -------------------------------------------------------------
   declare
      Geo : constant Geometry_Parameters := (others => <>);
   begin
      Check ("Validate_Geometry accepts default IRVE-3 geometry",
             Validate_Geometry (Geo),
             "default record rejected");
   end;

   declare
      --  39 deg sits below the Rapisarda 2023 Table 5.4 cone-angle
      --  floor (40..80); rejection path must stay armed even though
      --  Angle_Deg is intentionally unconstrained at the type level.
      Bad : constant Geometry_Parameters := (Angle_Deg => 39.0, others => <>);
   begin
      Check ("Validate_Geometry rejects sub-table cone angle",
             not Validate_Geometry (Bad),
             "39 deg accepted");
   end;

   -------------------------------------------------------------
   --  Environment: ISA atmosphere (AXIOMs E1/E2 envelopes)
   -------------------------------------------------------------
   declare
      --  Sea level: 288.15 K is the Post-band ceiling (E2).
      T0 : constant Float := Atmosphere_Temperature (0.0);
   begin
      Check ("Atmosphere_Temperature sea level == 288.15",
             abs (T0 - 288.15) < 0.02,
             "T = " & Float'Image (T0));
   end;

   declare
      --  US76 strato-II gradient (+2.8 K/km from 228.65 K at 32 km):
      --  T(46 km) = 228.65 + 14*2.8 = 267.85 K.
      T46 : constant Float := Atmosphere_Temperature (46.0);
   begin
      Check ("Atmosphere_Temperature stratosphere gradient",
             T46 > 267.3 and T46 < 268.4,
             "T = " & Float'Image (T46));
   end;

   declare
      D0  : constant Float := Atmosphere_Density (0.0);
      D10 : constant Float := Atmosphere_Density (10.0);
      D20 : constant Float := Atmosphere_Density (20.0);
   begin
      Check ("Atmosphere_Density decreases monotonically",
             D0 > D10 and D10 > D20 and D20 > 0.0
             and D0 > 1.2 and D0 < 1.25,
             "rho(0)=" & Float'Image (D0) &
             " rho(10)=" & Float'Image (D10) &
             " rho(20)=" & Float'Image (D20));
   end;

   declare
      --  E1 envelope corner: V = 50*sqrt(gamma*R*T_max) ~= 5.49e4 m/s,
      --  comfortably inside Velocity_Range (regression guard for the
      --  composite clamp introduced in A3c).
      V_Max : constant Float := Mach_To_Velocity (50.0, 3000.0);
   begin
      Check ("Mach_To_Velocity max-envelope stays inside subtype",
             V_Max > 5.47e4 and V_Max < 5.52e4
             and V_Max < Velocity_Range'Last,
             "V = " & Float'Image (V_Max));
   end;

   -------------------------------------------------------------
   --  Atomic parity (Tier B2): byte + frame integrity, recovery
   -------------------------------------------------------------
   declare
   begin
      Check ("Count_Set_Bits boundaries (0x00, 0xFF, 0xA5)",
             StellarOrion_Atomic_Parity.Count_Set_Bits (16#00#) = 0
             and then StellarOrion_Atomic_Parity.Count_Set_Bits (16#FF#) = 8
             and then StellarOrion_Atomic_Parity.Count_Set_Bits (16#A5#) = 4,
             "popcounts wrong");
   end;

   declare
      --  16#03# carries two set bits -> even parity True, odd False;
      --  16#01# carries one set bit -> the reverse.
   begin
      Check ("Calculate_Parity even/odd semantics",
             StellarOrion_Atomic_Parity.Calculate_Parity (16#03#, StellarOrion_Atomic_Parity.Even)
               and then not StellarOrion_Atomic_Parity.Calculate_Parity (16#03#, StellarOrion_Atomic_Parity.Odd)
             and then not StellarOrion_Atomic_Parity.Calculate_Parity (16#01#, StellarOrion_Atomic_Parity.Even)
               and then StellarOrion_Atomic_Parity.Calculate_Parity (16#01#, StellarOrion_Atomic_Parity.Odd),
             "parity predicate wrong");
   end;

   declare
      use type Interfaces.Unsigned_8;
      Block : constant StellarOrion_Atomic_Parity.Data_Block :=
        (1 => 16#01#, 2 => 16#02#, 3 => 16#04#, 4 => 16#08#, others => 16#00#);
      --  XOR fold: 1 xor 2 xor 4 xor 8 = 15 = 16#0F#.
   begin
      Check ("Block_Checksum XOR-fold identity",
             StellarOrion_Atomic_Parity.Block_Checksum
               ((others => 16#00#)) = 16#00#
             and then StellarOrion_Atomic_Parity.Block_Checksum (Block) = 16#0F#,
             "checksum wrong");
   end;

   declare
      use type Interfaces.Unsigned_8;
      Frame : constant StellarOrion_Atomic_Parity.Parity_Frame :=
        StellarOrion_Atomic_Parity.Add_Output_Parity
          ((1 => 16#AA#, others => 16#00#));
      Corrupt : StellarOrion_Atomic_Parity.Parity_Frame := Frame;
   begin
      Corrupt.Payload (3) := Corrupt.Payload (3) xor 16#01#;  --  flip one bit
      Check ("Frame roundtrip verifies; single-bit corruption detected",
             StellarOrion_Atomic_Parity.Verify_Input_Parity (Frame)
             and then not StellarOrion_Atomic_Parity.Verify_Input_Parity (Corrupt),
             "detection failed");
   end;

   declare
      use type StellarOrion_Atomic_Parity.Recovery_Status;
      use type StellarOrion_Atomic_Parity.Parity_Frame;
      Bad     : constant StellarOrion_Atomic_Parity.Parity_Frame :=
        StellarOrion_Atomic_Parity.Add_Output_Parity ((others => 16#5A#));
      Retry   : constant StellarOrion_Atomic_Parity.Recovery_Result :=
        StellarOrion_Atomic_Parity.Recover_From_Parity_Error
          (Bad, StellarOrion_Atomic_Parity.Max_Retries - 1);
      Exhaust : constant StellarOrion_Atomic_Parity.Recovery_Result :=
        StellarOrion_Atomic_Parity.Recover_From_Parity_Error
          (Bad, StellarOrion_Atomic_Parity.Max_Retries);
   begin
      Check ("Recovery: retry budget returns Success w/ original; exhausted substitutes safe frame",
             Retry.Status = StellarOrion_Atomic_Parity.Success
             and then Retry.Frame = Bad
             and then Exhaust.Status = StellarOrion_Atomic_Parity.Recovered
             and then StellarOrion_Atomic_Parity.Verify_Input_Parity (Exhaust.Frame),
             "recovery strategy wrong");
   end;

   -------------------------------------------------------------
   --  Dual watchdog (Tier B3): grace ladder, cross-recovery, emergency
   -------------------------------------------------------------
   declare
      use type StellarOrion_Dual_Watchdog.Health_Status;
      use all type StellarOrion_Dual_Watchdog.Watchdog_ID;
      S : StellarOrion_Dual_Watchdog.System_State;
   begin
      --  Scenario 1: single-watchdog starvation and peer recovery.
      --  Timeout 5 ticks; A is fed, B is starved from tick 0.
      StellarOrion_Dual_Watchdog.Initialize (S, Timeout_Ticks => 5);
      Check ("Watchdog Initialize brings both up Healthy",
             S.A.Status = StellarOrion_Dual_Watchdog.Healthy
             and then S.B.Status = StellarOrion_Dual_Watchdog.Healthy
             and then not S.Emergency_Latched);

      StellarOrion_Dual_Watchdog.Update_Heartbeat (S, Watchdog_A, Now => 20);
      Check ("Heartbeat refresh records tick",
             S.A.Last_Heartbeat = 20
             and then S.A.Status = StellarOrion_Dual_Watchdog.Healthy);

      StellarOrion_Dual_Watchdog.Evaluate (S, Now => 21);
      --  A age 1 <= 5 stays Healthy; B age 21 > 5 degrades (grace step).
      Check ("Grace ladder: first overdue evaluation degrades only",
             S.A.Status = StellarOrion_Dual_Watchdog.Healthy
             and then S.B.Status = StellarOrion_Dual_Watchdog.Degraded
             and then S.B.Failure_Count = 0);

      StellarOrion_Dual_Watchdog.Evaluate (S, Now => 22);
      --  Second consecutive stale evaluation fails B; counter increments.
      Check ("Grace ladder: second overdue evaluation fails + counts",
             S.A.Status = StellarOrion_Dual_Watchdog.Healthy
             and then S.B.Status = StellarOrion_Dual_Watchdog.Failed
             and then S.B.Failure_Count = 1);

      StellarOrion_Dual_Watchdog.Cross_Check (S);
      Check ("Cross-monitoring: live A starts recovery of failed B",
             S.B.Status = StellarOrion_Dual_Watchdog.Recovering);

      StellarOrion_Dual_Watchdog.Advance_Recovery (S, Watchdog_B, Now => 23);
      Check ("Advance_Recovery restores B Healthy with fresh heartbeat",
             S.B.Status = StellarOrion_Dual_Watchdog.Healthy
             and then S.B.Last_Heartbeat = 23);
   end;

   declare
      use type StellarOrion_Dual_Watchdog.Health_Status;
      S : StellarOrion_Dual_Watchdog.System_State;
   begin
      --  Scenario 2: both watchdogs starve -> emergency safe state.
      StellarOrion_Dual_Watchdog.Initialize (S, Timeout_Ticks => 5);
      StellarOrion_Dual_Watchdog.Evaluate (S, Now => 11);   --  both degrade
      StellarOrion_Dual_Watchdog.Evaluate (S, Now => 12);   --  both fail
      Check ("Both-starve detected as emergency condition",
             StellarOrion_Dual_Watchdog.Needs_Emergency (S));

      StellarOrion_Dual_Watchdog.Emergency_Safe_State (S);
      Check ("Emergency safe state: both Dead, latch sticky",
             S.A.Status = StellarOrion_Dual_Watchdog.Dead
             and then S.B.Status = StellarOrion_Dual_Watchdog.Dead
             and then S.Emergency_Latched);
   end;

   -------------------------------------------------------------
   --  Summary
   -------------------------------------------------------------
   Put_Line ("-----------------------------------------------");
   Put_Line ("Tests run:" & Natural'Image (Tests_Run) &
             "  Failed:" & Natural'Image (Failures));
   if Failures = 0 then
      Put_Line ("ALL TESTS PASSED");
   else
      Put_Line ("TEST FAILURES PRESENT");
   end if;

   Ada.Command_Line.Set_Exit_Status
     (if Failures = 0
      then Ada.Command_Line.Success
      else Ada.Command_Line.Failure);

end Test_Main;
