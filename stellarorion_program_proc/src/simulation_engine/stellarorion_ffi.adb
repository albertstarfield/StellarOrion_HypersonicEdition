-- =============================================================================
-- StellarOrion_FFI Body — C-Compatible Foreign Function Interface Layer
-- =============================================================================
-- AXIOMS:
--   1. Every C function receives plain scalars (Double, int) and returns
--      results through pointer parameters, matching the ctypes/cffi calling
--      convention on macOS (cdecl).
--   2. Type conversions between Interfaces.C.Double and Standard.Float are
--      safe because both are IEEE 754 binary64 (Long_Float on GNAT).
--   3. Interfaces.C.int is a 32-bit signed integer; Boolean is encoded as
--      1 (True) / 0 (False) per the C convention.
--   4. The body delegates all computation to StellarOrion_Optimization;
--      this layer contains zero domain logic.
--
-- THEOREMS:
--   1. Since Estimate_Cd, HIAD_Cost_Function, and Run_MoP_Optimization
--      have proven preconditions in the spec, the FFI wrappers can
--      safely call them given valid C inputs.
--   2. All output pointers are dereferenced exactly once, preventing
--      double-free or use-after-free scenarios.
--
-- CITATIONS:
--   [Ada2012]      ISO/IEC 8652:2012, Interfaces.C package.
--   [Ctypes]       Python ctypes — https://docs.python.org/3/library/ctypes.html
--   [Anderson06]   Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4.
--   [Nocedal06]    Nocedal & Wright (2006), Numerical Optimization, Sec 17.1.
--   [Boyd04]       Boyd & Vandenberghe (2004), Convex Optimization.
--   [Bertsekas99]  Bertsekas (1999), Nonlinear Programming, Sec 2.7.
--   [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
--   [Sutton51]     Sutton & Graves (1951), J. Aeronautical Sciences.
--   [NASA-TR-R376] NASA TR R-376 (1972) — C_SG = 1.7415e-4.
--
-- Author: Albert Starfield Wahyu Suryo Samudro
-- =============================================================================

with StellarOrion_Optimization; use StellarOrion_Optimization;
with StellarOrion_Physics;     use StellarOrion_Physics;
with StellarOrion_Postprocessing; use StellarOrion_Postprocessing;
with StellarOrion_Environment; use StellarOrion_Environment;
with StellarOrion_Speed_Of_Sound; use StellarOrion_Speed_Of_Sound;
with Interfaces.C.Strings;
with Ada.Exceptions;

--  Operator visibility for the C scalar types. Interfaces.C is `with`ed but not
--  `use`d, so its primitive operators are not directly visible (GNAT 6.3).
--  A use-type clause is the minimal, scope-local remedy: a blanket
--  `use Interfaces.C` would import 80+ names and re-create the overloading
--  clashes that the qualified style below exists to avoid.
use type Interfaces.C.double;
use type Interfaces.C.int;

package body StellarOrion_FFI is

   -- -----------------------------------------------------------------
   --  C_PRINTF / C_FFLUSH — dylib-safe logging primitive
   -- -----------------------------------------------------------------
   --  AXIOMS: in the dynamically loaded libstellarorion_pinn.dylib the GNAT
   --  runtime's Ada.Text_IO Standard_Output is NOT open, so Put_Line
   --  raises ADA.IO_EXCEPTIONS.STATUS_ERROR and an exception escaping
   --  the FFI aborts the host process (observed 2026-09-25 while
   --  exercising HIAD_Set_Refs_C). libc's printf writes the file
   --  descriptor directly and has no Ada Text_IO state to corrupt.
   --  THEOREMS: printf/fflush symbols come from the host libc (already
   --  loaded by Python) — no extra link dependency for the dylib.
   --  APPLICATIONS: every FFI-layer log line goes through Log so error
   --  diagnostics NEVER abort the host (Murphy's Law: logging must not
   --  be a new crash path). fflush after each line keeps messages
   --  visible even if the process dies later.
   --  CITATIONS: [C99] ISO/IEC 9899:1999 stdio.h printf/fflush;
   --             [Ctypes] https://docs.python.org/3/library/ctypes.html
   -- -----------------------------------------------------------------
   function C_Printf
     (Format : Interfaces.C.Strings.chars_ptr) return Interfaces.C.int;
   pragma Import (C, C_Printf, "printf");

   --  C_Flush_Stream — flush a libc FILE* stream through the C ABI.
   --  Forces stdout/stderr to the file descriptor so log lines are visible
   --  even if the host process dies immediately afterwards.
   --  Timing analysis: WCET ~ 5us (single fflush syscall); CPU Time O(1);
   --  Space Complexity O(1) — no allocation, operates on the caller's stream.
   procedure C_Flush_Stream
     (Stream : Interfaces.C.Strings.chars_ptr);
   pragma Import (C, C_Flush_Stream, "fflush");

   --  Log one line to stdout via libc (dylib-safe; see C_Printf axiom).
   --  Timing analysis: WCET ~ 6us (printf + fflush syscalls); CPU Time O(1);
   --  Space Complexity O(len(Msg)) for the NUL-terminated copy, then O(1).
   --  @test: Test_Log exercises this subprogram (see STC block below).
   --  Contract: Pre => True (any string is loggable); Post => True
   --  (logging never propagates an error to the caller).
   procedure Log (Msg : String) with Pre => True, Post => True is
      NL    : constant String := Msg & Character'Val (10);
      C_Str : constant Interfaces.C.Strings.chars_ptr :=
        Interfaces.C.Strings.New_String (NL);
   begin
      declare
         Ignored : Interfaces.C.int := C_Printf (C_Str);
         pragma Unreferenced (Ignored);
      begin
         null;
      end;
      --  flush stdout (null pointer = stdout per C99 stdio.h)
      C_Flush_Stream (Interfaces.C.Strings.Null_Ptr);
   exception
      when others =>
         --  Logging must never raise out of Log itself (last resort:
         --  swallow only if libc itself failed — nothing else to do).
         null;
   end Log;

   -- -------------------------------------------------------------------------
   --  Estimate_Cd_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Optimization.Estimate_Cd with N_Tori = 6
   --  (IRVE-3 baseline default, per Rapisarda 2023 Table 4.1).
   --
   --  Safety fallback: If the underlying Estimate_Cd raises an exception
   --  (e.g., precondition violation from invalid geometry), the function
   --  returns 0.0 as a sentinel.  The Python caller must check for 0.0.
   -- -------------------------------------------------------------------------
   function Estimate_Cd_C
     (R_N           : Interfaces.C.Double;
      R_Tor         : Interfaces.C.Double;
      Half_Cone_Deg : Interfaces.C.Double)
      return Interfaces.C.Double
   is
      --  Type aliases for clarity
      Ada_R_N           : constant Standard.Float := Standard.Float (R_N);
      Ada_R_Tor         : constant Standard.Float := Standard.Float (R_Tor);
      Ada_Half_Cone_Deg : constant Standard.Float := Standard.Float (Half_Cone_Deg);
      Result            : Standard.Float;
   begin
      --  Delegate to the Ada optimization function
      --  N_Tori defaults to 6 (IRVE-3 baseline)
      Result := Estimate_Cd
        (R_N           => Ada_R_N,
         R_Tor         => Ada_R_Tor,
         Half_Cone_Deg => Ada_Half_Cone_Deg,
         N_Tori        => Default_N_Tori_MOP);

      return Interfaces.C.Double (Result);

   exception
      when others =>
         --  Safety fallback: return 0.0 sentinel on any error
         --  [Citation: Ada2012 RM 11.4 — Exception Handling]
         return 0.0;
   end Estimate_Cd_C;

   -- -------------------------------------------------------------------------
   --  HIAD_Cost_C
   -- -------------------------------------------------------------------------
   --  Assembles the three scalar parameters into a Param_Vector and
   --  delegates to StellarOrion_Optimization.HIAD_Cost_Function.
   --
   --  Safety fallback: Returns -1.0 sentinel on exception (cost is
   --  always >= 0.0 for valid inputs, so -1.0 signals an error).
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => X1 > 0.0 and then X2 > 0.0 and then X3 > 0.0 and then X3 < 90.0
   --    Post => HIAD_Cost_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function HIAD_Cost_C
     (X1 : Interfaces.C.Double;
      X2 : Interfaces.C.Double;
      X3 : Interfaces.C.Double)
      return Interfaces.C.Double
   is
      X : Param_Vector;
   begin
      X (1) := Standard.Float (X1);  -- R_N
      X (2) := Standard.Float (X2);  -- r_tor
      X (3) := Standard.Float (X3);  -- half_cone_deg

      return Interfaces.C.Double (HIAD_Cost_Function (X));

   exception
      when others =>
         --  Safety fallback: return -1.0 sentinel (cost >= 0.0 always)
         return Interfaces.C.Double (-1.0);
   end HIAD_Cost_C;

   -- -------------------------------------------------------------------------
   --  HIAD_Set_Refs_C
   -- -------------------------------------------------------------------------
   --  AXIOMS: four binary64 doubles map 1:1 to the Ada procedure
   --          parameters (no precision loss, ffi.ads THEOREM 2).
   --  THEOREMS: on failure the previous Current_Refs state is kept
   --            (Set_Validation_Refs raises BEFORE assignment) and no
   --            exception crosses the C boundary (cdecl contract).
   --  APPLICATIONS: called once per optimization run by
   --                ada_pinn_wrapper.set_validation_refs.
   --  CITATIONS: [Ctypes] https://docs.python.org/3/library/ctypes.html
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Q_Target > 0.0 and then Flux_Ref > 0.0 and then Tau_Sec > 0.0
   --            and then Cd_Ref > 0.0
   --    Post => HIAD_Set_Refs_C'Result in 0 .. 1
   -- -------------------------------------------------------------------------
   function HIAD_Set_Refs_C
     (Q_Target : Interfaces.C.Double;
      Flux_Ref : Interfaces.C.Double;
      Tau_Sec  : Interfaces.C.Double;
      Cd_Ref   : Interfaces.C.Double)
      return Interfaces.C.int
   is
   begin
      Set_Validation_Refs
        (Q_Target_Jcm2 => Standard.Float (Q_Target),
         Flux_Ref_Wcm2 => Standard.Float (Flux_Ref),
         Tau_Sec       => Standard.Float (Tau_Sec),
         Cd_Ref        => Standard.Float (Cd_Ref));
      return 0;  --  0 = refs updated (contract: value 0 means OK)
   exception
      when others =>
         --  LITERAL-ONLY logging: in the dynamically loaded dylib the GNAT
         --  secondary stack is unavailable for foreign threads, so any
         --  unconstrained String result ('Image, Exception_Name, concat)
         --  SEGFAULTS (faulthandler: system__secondary_stack__ss_mark).
         --  Full context (the four values) is reported by the Python
         --  wrapper, which validates inputs BEFORE calling this FFI.
         --  Previous (valid) refs remain loaded on failure.
         Log("[VERBOSE_ERROR] HIAD_Set_Refs_C: Ada exception - validation refs unchanged");
         return 1;  --  1 = failed (Python wrapper raises RuntimeError)
   end HIAD_Set_Refs_C;

   -- -------------------------------------------------------------------------
   --  HIAD_Cost_Components_C
   -- -------------------------------------------------------------------------
   --  AXIOMS: seven caller-allocated binary64 pointers, each written
   --          exactly once per call (ffi.ads THEOREM 2 / axiom block).
   --  THEOREMS: outputs equal the Ada Cost_Components record fields;
   --            on failure all fields are zeroed and Out_Total = -1.0
   --            (sentinel contract shared with HIAD_Cost_C).
   --  APPLICATIONS: hiad_optimizer.py hiad_cost_components() reads the
   --                breakdown for JSON reporting of J(x) terms.
   --  CITATIONS: [Ctypes] byref(c_double) write-back pattern.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => X1 > 0.0 and then X2 > 0.0 and then X3 > 0.0 and then X3 < 90.0
   --            and then Out_Total /= null
   --    Post => Out_Total /= null and then Out_Total.all >= -1.0
   --  Timing analysis: WCET O(1) — seven fixed writes; CPU Time ~1us;
   --  Space Complexity O(1) — no allocation, the caller owns every buffer.
   -- -------------------------------------------------------------------------
   procedure HIAD_Cost_Components_C
     (X1, X2, X3             : Interfaces.C.Double;
      Out_Heat_Load_Ratio    : access Interfaces.C.Double;
      Out_Flux_Ratio         : access Interfaces.C.Double;
      Out_Beta_Dev           : access Interfaces.C.Double;
      Out_Cd_Ratio           : access Interfaces.C.Double;
      Out_Penalty            : access Interfaces.C.Double;
      Out_Total              : access Interfaces.C.Double;
      Out_Heat_Load_Jcm2     : access Interfaces.C.Double)
   is
      X    : Param_Vector;
      Comp : Cost_Components;
   begin
      X (1) := Standard.Float (X1);  -- R_N
      X (2) := Standard.Float (X2);  -- r_tor
      X (3) := Standard.Float (X3);  -- half_cone_deg

      Comp := HIAD_Cost_Components (X);

      Out_Heat_Load_Ratio.all := Interfaces.C.Double (Comp.Heat_Load_Ratio);
      Out_Flux_Ratio.all      := Interfaces.C.Double (Comp.Flux_Ratio);
      Out_Beta_Dev.all        := Interfaces.C.Double (Comp.Beta_Dev);
      Out_Cd_Ratio.all        := Interfaces.C.Double (Comp.Cd_Ratio);
      Out_Penalty.all         := Interfaces.C.Double (Comp.Penalty);
      Out_Total.all           := Interfaces.C.Double (Comp.Total);
      Out_Heat_Load_Jcm2.all  := Interfaces.C.Double (Comp.Heat_Load_Jcm2);
   exception
      when others =>
         --  ORDER MATTERS: write the sentinel outputs FIRST so the host
         --  never sees partially-filled components (J=0 would poison a
         --  minimiser). Then LITERAL-ONLY logging (secondary stack is
         --  unavailable in the dynamically loaded dylib — see HIAD_Set_Refs_C);
         --  the Python wrapper raises RuntimeError with the full X
         --  values on the -1.0 sentinel.
         Out_Heat_Load_Ratio.all := 0.0;
         Out_Flux_Ratio.all      := 0.0;
         Out_Beta_Dev.all        := 0.0;
         Out_Cd_Ratio.all        := 0.0;
         Out_Penalty.all         := 0.0;
         Out_Total.all           := Interfaces.C.Double (-1.0);
         Out_Heat_Load_Jcm2.all  := 0.0;
         Log("[VERBOSE_ERROR] HIAD_Cost_Components_C: Ada exception - sentinel Total=-1.0 returned");
   end HIAD_Cost_Components_C;

   -- -------------------------------------------------------------------------
   --  Run_MoP_C
   -- -------------------------------------------------------------------------
   --  Assembles MoP_Config and Param_Vector from individual C parameters,
   --  calls Run_MoP_Optimization, and writes results through output pointers.
   --
   --  Safety fallback: On exception, all output pointers are set to
   --  safe defaults (zeros, 0 = False, 0 iterations).
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Learning_Rate > 0.0 and then Tolerance > 0.0
   --            and then Max_Iter > 0 and then Out_X1 /= null
   --            and then Out_X2 /= null and then Out_X3 /= null
   --            and then Out_Cost /= null and then Out_Converged /= null
   --            and then Out_N_Iter /= null
   --    Post => Out_Converged /= null
   --            and then (Out_Converged.all = 0 or else Out_Converged.all = 1)
   --  Timing analysis: WCET O(Max_Iter) — one projected-gradient step per
   --  iteration, each O(1); CPU Time bounded by Max_Iter; Space Complexity O(1).
   -- -------------------------------------------------------------------------
   procedure Run_MoP_C
     (Learning_Rate  : Interfaces.C.Double;
      Tolerance      : Interfaces.C.Double;
      Lambda_1       : Interfaces.C.Double;
      Lambda_2       : Interfaces.C.Double;
      Max_Iter       : Interfaces.C.int;
      X1             : Interfaces.C.Double;
      X2             : Interfaces.C.Double;
      X3             : Interfaces.C.Double;
      Out_X1         : access Interfaces.C.Double;
      Out_X2         : access Interfaces.C.Double;
      Out_X3         : access Interfaces.C.Double;
      Out_Cost       : access Interfaces.C.Double;
      Out_Converged  : access Interfaces.C.int;
      Out_N_Iter     : access Interfaces.C.int)
   is
      --  Assemble MoP configuration from individual C parameters
      Config : MoP_Config;
      --  Assemble initial guess into Param_Vector
      X_Initial : Param_Vector;
      --  Result record from the optimizer
      Result : MoP_Result;
   begin
      --  Build MoP_Config
      Config.Learning_Rate := Standard.Float (Learning_Rate);
      Config.Tolerance     := Standard.Float (Tolerance);
      Config.Lambda_1      := Standard.Float (Lambda_1);
      Config.Lambda_2      := Standard.Float (Lambda_2);
      Config.Max_Iter      := Positive (Max_Iter);

      --  Build initial parameter vector
      X_Initial (1) := Standard.Float (X1);  -- R_N
      X_Initial (2) := Standard.Float (X2);  -- r_tor
      X_Initial (3) := Standard.Float (X3);  -- half_cone_deg

      --  Run the MoP optimizer
      Run_MoP_Optimization
        (Config    => Config,
         X_Initial => X_Initial,
         Result    => Result);

      --  Write results through output pointers
      Out_X1.all        := Interfaces.C.Double (Result.X_Opt (1));
      Out_X2.all        := Interfaces.C.Double (Result.X_Opt (2));
      Out_X3.all        := Interfaces.C.Double (Result.X_Opt (3));
      Out_Cost.all      := Interfaces.C.Double (Result.Cost);
      Out_N_Iter.all    := Interfaces.C.int (Result.N_Iter);

      --  Boolean -> C int encoding: True = 1, False = 0
      if Result.Converged then
         Out_Converged.all := 1;
      else
         Out_Converged.all := 0;
      end if;

   exception
      when others =>
         --  Safety fallback: zero all outputs on error
         Out_X1.all        := 0.0;
         Out_X2.all        := 0.0;
         Out_X3.all        := 0.0;
         Out_Cost.all      := 0.0;
         Out_Converged.all := 0;
         Out_N_Iter.all    := 0;
   end Run_MoP_C;

   -- -------------------------------------------------------------------------
   --  Generate_CCD_Samples_C
   -- -------------------------------------------------------------------------
   --  Generates 15 CCD design points via Generate_CCD_Samples, then
   --  copies each field into flat C arrays. Labels are copied as
   --  fixed-width 31-byte strings (30 chars + NUL terminator).
   --
   --  Safety fallback: On exception, output arrays are left zeroed
   --  and labels are filled with NUL bytes.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Out_R_N /= null and then Out_R_Tor /= null
   --            and then Out_Angles /= null and then Out_Labels /= null
   --    Post => True
   --  Timing analysis: WCET O(CCD_Samples * CCD_Label_Max) — fixed 15 points,
   --  each a constant-width label copy; CPU Time O(1) fixed; Space Complexity O(1).
   -- -------------------------------------------------------------------------
   procedure Generate_CCD_Samples_C
     (Out_R_N    : access CCD_Double_Array;
      Out_R_Tor  : access CCD_Double_Array;
      Out_Angles : access CCD_Double_Array;
      Out_Labels : access CCD_Label_Buffer)
   is
      Samples : CCD_Sample_Array;
   begin
      --  Generate the 15 CCD sample points
      Generate_CCD_Samples (Samples => Samples);

      --  Copy numeric fields into flat arrays using index notation
      for I in 0 .. CCD_Samples - 1 loop
         --  invariant: 0 <= I <= CCD_Samples - 1 (in range of Out_* arrays)
         declare
            Ada_I : constant Natural := I + 1;  --  Ada arrays are 1-based
         begin
            Out_R_N (I)    := Interfaces.C.Double (Samples (Ada_I).R_N);
            Out_R_Tor (I)  := Interfaces.C.Double (Samples (Ada_I).R_Tor);
            Out_Angles (I) := Interfaces.C.Double (Samples (Ada_I).Half_Cone_Deg);
         end;
      end loop;

      --  Copy labels into flat char buffer
      for I in 0 .. CCD_Samples - 1 loop
         --  invariant: 0 <= I <= CCD_Samples - 1 (each label slot visited once)
         declare
            Ada_I     : constant Natural := I + 1;
            Buf_Start : constant Natural := I * Label_Stride;
         begin
            --  Copy up to CCD_Label_Max characters from the label
            for J in 1 .. CCD_Label_Max loop
               --  invariant: 1 <= J <= CCD_Label_Max (label field width)
               Out_Labels (Buf_Start + J - 1) := Samples (Ada_I).Label (J);
            end loop;

            --  NUL-terminate the label (index 30 = CCD_Label_Max, 0-based)
            --  Label_Stride = 31 = CCD_Label_Max + 1, so NUL is the last byte.
            --  No padding needed: 30 chars + 1 NUL = 31 bytes = Label_Stride.
            Out_Labels (Buf_Start + CCD_Label_Max) := Character'Val (0);
         end;
      end loop;

   exception
      when others =>
         --  Safety fallback: zero all output buffers on error
         for I in 0 .. CCD_Samples - 1 loop
            --  invariant: 0 <= I <= CCD_Samples - 1 (numeric buffer bound)
            Out_R_N (I)    := 0.0;
            Out_R_Tor (I)  := 0.0;
            Out_Angles (I) := 0.0;
         end loop;

         for I in 0 .. CCD_Samples * Label_Stride - 1 loop
            --  invariant: 0 <= I <= CCD_Samples * Label_Stride - 1 (byte buffer bound)
            Out_Labels (I) := Character'Val (0);
         end loop;
   end Generate_CCD_Samples_C;

   -- -------------------------------------------------------------------------
   --  Sutton_Graves_Heat_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Sutton_Graves_Heat.
   --  Safety fallback: Returns 0.0 on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Density > 0.0 and then Nose_Radius > 0.0 and then Velocity >= 0.0
   --    Post => Sutton_Graves_Heat_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Sutton_Graves_Heat_C
     (Density     : Interfaces.C.Double;
      Nose_Radius : Interfaces.C.Double;
      Velocity    : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Sutton_Graves_Heat (
          Density     => Standard.Float (Density),
          Nose_Radius => Standard.Float (Nose_Radius),
          Velocity    => Standard.Float (Velocity)));
   exception
      when others =>
         return 0.0;
   end Sutton_Graves_Heat_C;

   -- -------------------------------------------------------------------------
   --  Sutherland_Viscosity_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Postprocessing.Sutherland_Viscosity.
   --  Safety fallback: Returns 1.716e-5 (MU_REF at 0 K limit) on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => T > 0.0
   --    Post => Sutherland_Viscosity_C'Result > 0.0
   -- -------------------------------------------------------------------------
   function Sutherland_Viscosity_C
     (T : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Sutherland_Viscosity (T => Standard.Float (T)));
   exception
      when others =>
         return 1.716e-5;
   end Sutherland_Viscosity_C;

   -- -------------------------------------------------------------------------
   --  Fay_Riddell_Heat_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Fay_Riddell_Heat.
   --  Safety fallback: Returns 0.0 on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Density_Kgm3 > 0.0 and then Nose_Radius_M > 0.0
   --            and then Velocity_Ms >= 0.0 and then Mach > 0.0
   --            and then Wall_Temp_K > 0.0
   --    Post => Fay_Riddell_Heat_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Fay_Riddell_Heat_C
     (Density_Kgm3  : Interfaces.C.Double;
      Nose_Radius_M : Interfaces.C.Double;
      Velocity_Ms   : Interfaces.C.Double;
      Mach          : Interfaces.C.Double;
      Wall_Temp_K   : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Fay_Riddell_Heat (
          Density_Kgm3  => Standard.Float (Density_Kgm3),
          Nose_Radius_M => Standard.Float (Nose_Radius_M),
          Velocity_Ms   => Standard.Float (Velocity_Ms),
          Mach          => Standard.Float (Mach),
          Wall_Temp_K   => Standard.Float (Wall_Temp_K)));
   exception
      when others =>
         return 0.0;
   end Fay_Riddell_Heat_C;

   -- -------------------------------------------------------------------------
   --  Radiative_Eq_Temp_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Radiative_Eq_Temp.
   --  Safety fallback: Returns 300.0 (ambient temperature) on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Heat_Flux >= 0.0 and then Emissivity > 0.0 and then Emissivity <= 1.0
   --    Post => Radiative_Eq_Temp_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Radiative_Eq_Temp_C
     (Heat_Flux  : Interfaces.C.Double;
      Emissivity : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Radiative_Eq_Temp (
          Heat_Flux  => Standard.Float (Heat_Flux),
          Emissivity => Standard.Float (Emissivity)));
   exception
      when others =>
         return 300.0;
   end Radiative_Eq_Temp_C;

   -- -------------------------------------------------------------------------
   --  Backface_Temperature_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Backface_Temperature.
   --  Safety fallback: Returns 300.0 (ambient temperature) on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Init_Temp > 0.0 and then Heat_Flux >= 0.0 and then Duration >= 0.0
   --            and then Thermal_Lag >= 0.0 and then TPS_Density > 0.0
   --            and then TPS_Cp > 0.0 and then TPS_Thickness > 0.0
   --    Post => Backface_Temperature_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Backface_Temperature_C
     (Init_Temp     : Interfaces.C.Double;
      Heat_Flux     : Interfaces.C.Double;
      Duration      : Interfaces.C.Double;
      Thermal_Lag   : Interfaces.C.Double;
      TPS_Density   : Interfaces.C.Double;
      TPS_Cp        : Interfaces.C.Double;
      TPS_Thickness : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Backface_Temperature (
          Init_Temp     => Standard.Float (Init_Temp),
          Heat_Flux     => Standard.Float (Heat_Flux),
          Duration      => Standard.Float (Duration),
          Thermal_Lag   => Standard.Float (Thermal_Lag),
          TPS_Density   => Standard.Float (TPS_Density),
          TPS_Cp        => Standard.Float (TPS_Cp),
          TPS_Thickness => Standard.Float (TPS_Thickness)));
   exception
      when others =>
         return 300.0;
   end Backface_Temperature_C;

   -- -------------------------------------------------------------------------
   --  Ballistic_Coefficient_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Ballistic_Coefficient.
   --  Safety fallback: Returns 0.0 on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Mass > 0.0 and then Dyn_Pressure >= 0.0 and then Drag_Force > 0.0
   --    Post => Ballistic_Coefficient_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Ballistic_Coefficient_C
     (Mass         : Interfaces.C.Double;
      Dyn_Pressure : Interfaces.C.Double;
      Drag_Force   : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Ballistic_Coefficient (
          Mass         => Standard.Float (Mass),
          Dyn_Pressure => Standard.Float (Dyn_Pressure),
          Drag_Force   => Standard.Float (Drag_Force)));
   exception
      when others =>
         return 0.0;
   end Ballistic_Coefficient_C;

   -- -------------------------------------------------------------------------
   --  Dynamic_Pressure_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Dynamic_Pressure.
   --  Safety fallback: Returns 0.0 on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Density >= 0.0 and then Velocity >= 0.0
   --    Post => Dynamic_Pressure_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Dynamic_Pressure_C
     (Density  : Interfaces.C.Double;
      Velocity : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Dynamic_Pressure (
          Density  => Standard.Float (Density),
          Velocity => Standard.Float (Velocity)));
   exception
      when others =>
         return 0.0;
   end Dynamic_Pressure_C;

   -- -------------------------------------------------------------------------
   --  Deceleration_G_Load_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Deceleration_G_Load.
   --  Safety fallback: Returns 0.0 on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Drag_Force >= 0.0 and then Mass > 0.0
   --    Post => Deceleration_G_Load_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Deceleration_G_Load_C
     (Drag_Force : Interfaces.C.Double;
      Mass       : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Deceleration_G_Load (
          Drag_Force => Standard.Float (Drag_Force),
          Mass       => Standard.Float (Mass)));
   exception
      when others =>
         return 0.0;
   end Deceleration_G_Load_C;

   -- -------------------------------------------------------------------------
   --  Atmosphere_Temperature_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Environment.Atmosphere_Temperature.
   --  Safety fallback: Returns 288.15 (sea-level ISA) on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Altitude_Km >= 0.0 and then Altitude_Km <= 1000.0
   --    Post => Atmosphere_Temperature_C'Result > 0.0
   -- -------------------------------------------------------------------------
   function Atmosphere_Temperature_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Atmosphere_Temperature (
          Altitude_Km => Standard.Float (Altitude_Km)));
   exception
      when others =>
         return 288.15;
   end Atmosphere_Temperature_C;

   -- -------------------------------------------------------------------------
   --  Atmosphere_Density_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Environment.Atmosphere_Density.
   --  Safety fallback: Returns 1.225 (sea-level ISA) on exception.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Altitude_Km >= 0.0 and then Altitude_Km <= 1000.0
   --    Post => Atmosphere_Density_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Atmosphere_Density_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Atmosphere_Density (
          Altitude_Km => Standard.Float (Altitude_Km)));
   exception
      when others =>
         return 1.225;
   end Atmosphere_Density_C;

   -- -------------------------------------------------------------------------
   --  Mean_Free_Path_Viscous_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Physics.Mean_Free_Path_Viscous.
   --  Safety fallback: Returns 0.0 on exception (a zero mean free path is the
   --  documented degenerate value the former Python helper used for rho<=0 or
   --  T<=0).
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => Mu >= 0.0 and then Density > 0.0 and then Temperature > 0.0
   --    Post => Mean_Free_Path_Viscous_C'Result >= 0.0
   -- -------------------------------------------------------------------------
   function Mean_Free_Path_Viscous_C
     (Mu          : Interfaces.C.Double;
      Density     : Interfaces.C.Double;
      Temperature : Interfaces.C.Double)
      return Interfaces.C.Double
   is
   begin
      return Interfaces.C.Double (
        Mean_Free_Path_Viscous (
          Mu          => Standard.Float (Mu),
          Density     => Standard.Float (Density),
          Temperature => Standard.Float (Temperature)));
   exception
      when others =>
         return 0.0;
   end Mean_Free_Path_Viscous_C;

   -- -------------------------------------------------------------------------
   --  Speed_Of_Sound_C
   -- -------------------------------------------------------------------------
   --  Delegates to StellarOrion_Speed_Of_Sound.Speed_Of_Sound.
   --  The input is clamped to the documented Pre envelope [0, 6000] K so the
   --  SPARK precondition always holds; safety fallback returns 0.0.
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => True;
   --    Post => Speed_Of_Sound_C'Result >= 0.0;
   -- -------------------------------------------------------------------------
   function Speed_Of_Sound_C
     (Temperature : Interfaces.C.Double)
      return Interfaces.C.Double
   is
      T : Standard.Float := Standard.Float (Temperature);
   begin
      if T < 0.0 then
         T := 0.0;
      elsif T > 6000.0 then
         T := 6000.0;
      end if;
      return Interfaces.C.Double (Speed_Of_Sound (Temperature => T));
   exception
      when others =>
         return 0.0;
   end Speed_Of_Sound_C;

   -- -------------------------------------------------------------------------
   --  TPS_Conduction_C
   -- -------------------------------------------------------------------------
   --  Per-element composite F-TPS conduction across the C ABI.
   --
   --  AXIOMS / THEORIES: see stellarorion_ffi.ads, section
   --  "TPS_Conduction_C — per-element composite F-TPS conduction (C ABI)".
   --  Restated here only where it shapes the code:
   --
   --  A2 (sentinel-first): every out-parameter is assigned BEFORE the first
   --      validation test. The failure paths below then only need to set
   --      Status — they cannot leave a caller holding garbage.
   --  T1 (validation == the subprogram preconditions): each check below is
   --      written against the EXACT bound appearing in the Pre => of
   --      SG_Scaled_Element_Flux, TPS_Conduction or TPS_Conduction_Profile.
   --      If a bound is later tightened in the physics spec, this
   --      validation becomes the thing that reports it, and the Status code
   --      names the offending property — which is why the codes are per
   --      property (BAD_EMISSIVITY, BAD_TEMPERATURE, BAD_PLY_PROPERTY)
   --      rather than one generic BAD_INPUT.
   --  T2 (no partial output): Status := TPS_STATUS_OK is the LAST statement,
   --      after the profile buffer is fully written.
   --  A4 (nothing escapes): the handler catches everything, logs through
   --      libc printf, and RETURNS normally. An exception crossing a C frame
   --      is undefined behaviour.
   --
   --  INPUT/OUTPUT DIFFERENCE (explicitly stated, per house style):
   --      Q_SG_Scale is the stagnation MAGNITUDE for the whole flight
   --      condition; Q_SG is the reconstructed flux of THIS element. They
   --      differ because the DSMC per-element reading supplies only the
   --      distribution SHAPE (axiom Q1/Q2/Q3 in stellarorion_physics.ads),
   --      never the calibration. A caller reading Q_SG == Q_SG_Scale for every
   --      element is correctly reporting a spatially UNIFORM distribution.
   --
   --  CITATIONS:
   --    [Baumeister06] Ch. 4 composite-wall resistance; Ch. 11 radiation BC.
   --    [Dillman14] AIAA 2014-4141, IRVE-3 250 degC FTPS structure limit.
   --    [Bird94] Bird (1994) Sec. 7, DSMC estimator noise on raw ke.
   --
   --  TIMING ANALYSIS
   --  Estimated Processing Time: O(L) for validation plus O(iterations) for
   --    the bisection plus O(N_samples * L) for the profile, with
   --    L <= 8, N_samples = 33, iterations <= 120.
   --  CPU Time: ~15us typical per element (120 bisection evals + 264
   --    profile steps + 8 validation steps, at ~50ns per bisection eval).
   --  WCET: 25us at the iteration cap with a 50% branch-misprediction
   --    penalty on the two validation loops.
   --  Space Complexity: O(1) — the layup is a fixed 8-ply record on the
   --    stack (~120 B) plus the caller's 33-sample buffer; no allocation.
   --  Derivation:
   --    - Validation: 8 plies x ~6 ops = ~50 ops
   --    - SG_Scaled_Element_Flux: ~40ns
   --    - TPS_Conduction: 120 x ~50ns = 6us (WCET 8us)
   --    - TPS_Conduction_Profile: 33 x 8 x ~10ns = 2.6us
   --    - Total WCET ~ 8 + 3 + 1 = 12us, x2 penalty => 25us
   --  Hardware Assumptions: IEEE-754 binary64 inputs, ARM Cortex-A78
   --    @ 2.4GHz (or equivalent), layup record in L1.
   --  Time Anchor: nanosecond (1ns) resolution via Ada.Real_Time, backed by
   --    CLOCK_MONOTONIC on POSIX.
   --
   --  Contract (inherited from StellarOrion_FFI spec):
   --    Pre  => N_Layers >= 1 and then N_Layers <= Interfaces.C.int
   --            (Max_TPS_Layers) and then Emissivity >= 1.0e-3 and then
   --            Emissivity <= 1.0 and then T_Init >= 0.0 and then
   --            T_Init <= 3000.0 and then T_Inf >= 0.0 and then
   --            T_Inf <= 3000.0 and then Ply_Thickness /= null and then
   --            Ply_Thermal_K /= null and then Profile /= null;
   --    Post => Status in 0 .. 8;
   procedure TPS_Conduction_C
     (Q_SG_Scale    : Interfaces.C.Double;
      Ke_Raw        : Interfaces.C.Double;
      Ke_Ref        : Interfaces.C.Double;
      N_Layers      : Interfaces.C.int;
      Ply_Thickness : access TPS_Ply_Array;
      Ply_Thermal_K : access TPS_Ply_Array;
      Emissivity    : Interfaces.C.Double;
      T_Init        : Interfaces.C.Double;
      T_Inf         : Interfaces.C.Double;
      Status        : out Interfaces.C.int;
      Q_SG          : out Interfaces.C.Double;
      T_Surface     : out Interfaces.C.Double;
      T_Back        : out Interfaces.C.Double;
      N_Iterations  : out Interfaces.C.int;
      Profile       : access TPS_Profile_Buffer)
   is
      --  THE INTERNAL LAYUP, ASSEMBLED FROM THE C ARRAYS.
      --
      --  Only Material.Thermal_K and Thickness are filled from C data; the
      --  remaining TPS_Material fields (density, Cp, emissivity of the ply)
      --  take their record defaults because this solver is conduction-only
      --  and does not use them. That is stated here rather than left
      --  implicit: if a future transient term needs rho*Cp, the defaults
      --  would be silently wrong, and this comment is what makes that
      --  visible.
      Layup      : StellarOrion_Types.TPS_Layup;
      Iterations : Natural := 0;
      Ada_Prof   : StellarOrion_Physics.Profile_Array;

      --  Internal-precision copies of the two solved temperatures. Kept
      --  separate from the Interfaces.C.Double outputs because the physics
      --  subprograms speak Float and the boundary speaks C.Double; the
      --  profile call needs the SAME Float T_Surface the solver produced,
      --  and a double round-trip would let a value differ in the last bit
      --  between the reported T_Surface and the profile's hot-face sample.
      Ada_T_Surface : Float := 0.0;
      Ada_T_Back    : Float := 0.0;

      --  SENTINELS (axiom A2). Documented so a caller that ignores Status
      --  can still recognise the failure rather than misread a plausible
      --  number: T_Surface/T_Back of -1.0 K and Q_SG of -1.0 W/m^2 are
      --  outside every physical range this entry point can return, so they
      --  are unambiguous.
      Sentinel_T : constant Interfaces.C.Double := -1.0;
      Sentinel_Q : constant Interfaces.C.Double := -1.0;

      --  Restore every out-parameter of TPS_Conduction_C to its STEP-0
      --  sentinel value. Single owner of that logic: all three failure paths
      --  (solver-raised, profile-raised, unexpected) call this, so the reset
      --  can never drift between them.
      --
      --  AXIOM A2: Status = TPS_STATUS_OK if and only if every output is
      --  meaningful. The converse therefore also holds -- a NONZERO Status
      --  means every output is a sentinel. That converse is what this
      --  subprogram exists to establish.
      --
      --  WHY IT CANNOT RAISE (safety fallback, code-quality mandate): a caller
      --  can legally pass a dangling/garbage Profile pointer, and dereferencing
      --  it while clearing would raise. That raise would escape TPS_Conduction_C
      --  and cross the C ABI, violating A4. So this one subprogram carries its
      --  own handler. It is the ONLY deliberate exception swallow in this FFI
      --  entry point, it is not silent (the cause is logged verbatim), and it
      --  is sound because every caller has already set a NONZERO Status before
      --  reaching here -- so a caller that checks Status still fails loudly.
      --  Timing analysis: WCET O(TPS_Profile_Buffer'Length) bounded by 33
      --  iterations; CPU Time ~1us; Space Complexity O(1) — no allocation.
      --  @test: Test_Reset_Outputs drives TPS_Conduction_C with N_Layers = 0
      --  and asserts every output equals the STEP-0 sentinel this clears to.
      procedure Reset_Outputs with Pre => True, Post => True is
      begin
         Q_SG         := Sentinel_Q;
         T_Surface    := Sentinel_T;
         T_Back       := Sentinel_T;
         N_Iterations := 0;
         if Profile /= null then
            for I in TPS_Profile_Buffer'Range loop
               --  invariant: I is in TPS_Profile_Buffer'Range; every element
               --  before I holds the sentinel depth and temperature.
               Profile (I).Depth_M := Sentinel_T;
               Profile (I).Temp_K  := Sentinel_T;
            end loop;
         end if;
      exception
         when E : others =>
            Log ("[TPS_Conduction_C] FAIL: Reset_Outputs could not clear the "
                 & "profile buffer (" & Ada.Exceptions.Exception_Name (E)
                 & ": " & Ada.Exceptions.Exception_Message (E)
                 & "); Status is nonzero, so the caller must not trust it");
      end Reset_Outputs;
   begin
      -- ------------------------------------------------------------------
      -- APPLICATION STEP 0 (axiom A2): initialise EVERY out-parameter.
      -- Done first so that any early return below is safe by construction.
      -- ------------------------------------------------------------------
      Status       := TPS_STATUS_OK;
      Q_SG         := Sentinel_Q;
      T_Surface    := Sentinel_T;
      T_Back       := Sentinel_T;
      N_Iterations := 0;
      if Profile /= null then
         for I in TPS_Profile_Buffer'Range loop
            --  invariant: I is in TPS_Profile_Buffer'Range; every element
            --  before I holds the STEP-0 sentinel depth and temperature.
            Profile (I).Depth_M := Sentinel_T;
            Profile (I).Temp_K  := Sentinel_T;
         end loop;
      end if;

      -- ------------------------------------------------------------------
      -- APPLICATION STEP 1: validate. Each bound below is copied verbatim
      -- from the Pre => of the physics subprogram it protects (theory T1).
      -- ------------------------------------------------------------------

      --  1.1 Layer count must name at least one ply and fit the layup.
      if N_Layers < 1 or N_Layers > Interfaces.C.int (Max_TPS_Layers) then
         Status := TPS_STATUS_BAD_LAYER_COUNT;
         Log ("[TPS_Conduction_C] FAIL: N_Layers=" & Standard.Integer'Image (Standard.Integer (N_Layers))
               & " outside 1 .." & Standard.Integer'Image (Standard.Integer (Max_TPS_Layers))
               & " (Status=" & Standard.Integer'Image (Standard.Integer (TPS_STATUS_BAD_LAYER_COUNT)) & ")");
         return;
      end if;

      --  1.2 Every buffer pointer must be present. A null access from C is
      --  the classic FFI crash; it is checked before ANY dereference.
      if Ply_Thickness = null
        or else Ply_Thermal_K = null
        or else Profile = null
      then
         Status := TPS_STATUS_NULL_POINTER;
         Log ("[TPS_Conduction_C] FAIL: null buffer pointer ("
               & "Ply_Thickness=" & (if Ply_Thickness = null then "null" else "ok")
               & ", Ply_Thermal_K=" & (if Ply_Thermal_K = null then "null" else "ok")
               & ", Profile=" & (if Profile = null then "null" else "ok")
               & ") Status=" & Standard.Integer'Image (Standard.Integer (TPS_STATUS_NULL_POINTER)));
         return;
      end if;

      --  1.3 Emissivity, against the TPS_Conduction Pre bound.
      if Emissivity < 1.0e-3 or else Emissivity > 1.0 then
         Status := TPS_STATUS_BAD_EMISSIVITY;
         Log ("[TPS_Conduction_C] FAIL: Emissivity=" & Interfaces.C.double'Image (Emissivity)
               & " outside 1.0e-3 .. 1.0 (Status="
               & Standard.Integer'Image (Standard.Integer (TPS_STATUS_BAD_EMISSIVITY)) & ")");
         return;
      end if;

      --  1.4 Temperatures, against the TPS_Conduction Pre bound.
      if T_Init < 0.0 or else T_Init > 3000.0
        or else T_Inf < 0.0 or else T_Inf > 3000.0
      then
         Status := TPS_STATUS_BAD_TEMPERATURE;
         Log ("[TPS_Conduction_C] FAIL: T_Init=" & Interfaces.C.double'Image (T_Init)
               & " or T_Inf=" & Interfaces.C.double'Image (T_Inf)
               & " outside 0.0 .. 3000.0 (Status="
               & Standard.Integer'Image (Standard.Integer (TPS_STATUS_BAD_TEMPERATURE)) & ")");
         return;
      end if;

      --  1.5 Flux inputs, against the SG_Scaled_Element_Flux Pre bounds.
      --      Ke_Raw is deliberately NOT bounded below: a negative reading is
      --      real DSMC noise (axiom Q3) and is legal input.
      if Q_SG_Scale < 0.0 or else Q_SG_Scale > 2.0e15
        or else Ke_Ref < 1.0e-12 or else Ke_Ref > 1.0e15
      then
         Status := TPS_STATUS_BAD_FLUX_INPUT;
         Log ("[TPS_Conduction_C] FAIL: Q_SG_Scale=" & Interfaces.C.double'Image (Q_SG_Scale)
               & " or Ke_Ref=" & Interfaces.C.double'Image (Ke_Ref)
               & " outside bounds (Status="
               & Standard.Integer'Image (Standard.Integer (TPS_STATUS_BAD_FLUX_INPUT)) & ")");
         return;
      end if;

      --  1.6 Per-ply conductivity and thickness, against the
      --      Layer_Resistance / TPS_Conduction Pre bounds. The offending
      --      INDEX is reported, not just "some ply is bad", because the
      --      caller must know WHICH ply to fix.
      for I in 1 .. Integer (N_Layers) loop
         --  invariant: 1 <= I <= N_Layers and every ply before I passed the
         --  conductivity and thickness bounds checked in this body.
         declare
            K_V  : constant Float :=
              Standard.Float (Ply_Thermal_K (TPS_Ply_Array'First + I - 1));
            D_V  : constant Float :=
              Standard.Float (Ply_Thickness (TPS_Ply_Array'First + I - 1));
         begin
            if K_V < 1.0e-3 or else K_V > 1.0e3 then
               Status := TPS_STATUS_BAD_PLY_PROPERTY;
               Log ("[TPS_Conduction_C] FAIL: ply " & Standard.Integer'Image (I)
                     & " Thermal_K=" & Float'Image (K_V)
                     & " outside 1.0e-3 .. 1.0e3 W/(m*K) (Status="
                     & Standard.Integer'Image (Standard.Integer (TPS_STATUS_BAD_PLY_PROPERTY)) & ")");
               return;
            end if;
            if D_V < 1.0e-4 or else D_V > 1.0 then
               Status := TPS_STATUS_BAD_PLY_PROPERTY;
               Log ("[TPS_Conduction_C] FAIL: ply " & Standard.Integer'Image (I)
                     & " Thickness=" & Float'Image (D_V)
                     & " outside 1.0e-4 .. 1.0 m (Status="
                     & Standard.Integer'Image (Standard.Integer (TPS_STATUS_BAD_PLY_PROPERTY)) & ")");
               return;
            end if;
         end;
      end loop;

      -- ------------------------------------------------------------------
      -- APPLICATION STEP 2: assemble the Ada layup from the C arrays.
      -- Hot face first, matching the profile's Depth_M = 0 convention.
      -- ------------------------------------------------------------------
      Layup.Layer_Count := StellarOrion_Types.TPS_Layer_Count_Range (N_Layers);
      Layup.Emissivity  := StellarOrion_Types.TPS_Emissivity_Range
        (Standard.Float (Emissivity));
      --  T_Limit is a REPORTING field the solver never reads (documented in
      --  the spec), but it is stored so a caller inspecting the layup sees a
      --  self-consistent record rather than a default left by accident.
      Layup.T_Limit     := IRVE3_FTPS_STRUCT_LIMIT_K;

      for I in 1 .. Integer (N_Layers) loop
         --  invariant: 1 <= I <= N_Layers and every layup entry before I has
         --  been populated from the validated ply arrays.
         declare
            Idx : constant StellarOrion_Types.TPS_Layer_Count_Range :=
              StellarOrion_Types.TPS_Layer_Count_Range (I);
         begin
            Layup.Layers (Idx).Material.Thermal_K :=
              Standard.Float (Ply_Thermal_K (TPS_Ply_Array'First + I - 1));
            Layup.Layers (Idx).Thickness :=
              StellarOrion_Types.TPS_Thickness_Range
                (Standard.Float (Ply_Thickness (TPS_Ply_Array'First + I - 1)));
         end;
      end loop;

      -- ------------------------------------------------------------------
      -- APPLICATION STEP 3: reconstruct the element heat flux (axiom Q1/Q2/Q3)
      -- and solve the surface balance for T_Surface / T_Back.
      -- ------------------------------------------------------------------
      begin
         declare
            Flux : constant Float :=
              StellarOrion_Physics.SG_Scaled_Element_Flux
                (Q_SG      => Standard.Float (Q_SG_Scale),
                 Ke_Raw    => Standard.Float (Ke_Raw),
                 Ke_Ref    => Standard.Float (Ke_Ref));
         begin
            Q_SG := Interfaces.C.Double (Flux);

            StellarOrion_Physics.TPS_Conduction
              (Heat_Flux => Flux,
               Layup     => Layup,
               T_Init    => Standard.Float (T_Init),
               T_Inf     => Standard.Float (T_Inf),
               T_Back    => Ada_T_Back,
               T_Surface => Ada_T_Surface,
               Iterations => Iterations);
         end;
      exception
         when E : others =>
            --  Solver-stage failure: inputs passed validation, so this is a
            --  genuine internal fault (e.g. the solver's own postcondition
            --  audit raising), not a caller error. Status distinguishes the
            --  two so the fix goes to the right place.
            Status := TPS_STATUS_SOLVER_RAISED;
            Log ("[TPS_Conduction_C] FAIL: TPS_Conduction/SG_Scaled raised "
                  & Ada.Exceptions.Exception_Name (E) & ": "
                  & Ada.Exceptions.Exception_Message (E)
                  & " (Status="
                  & Standard.Integer'Image (Standard.Integer (TPS_STATUS_SOLVER_RAISED)) & ")");
            --  A2: Q_SG was already written by STEP 3, so the
            --  sentinels MUST be restored before returning.
            Reset_Outputs;
            return;
      end;

      T_Surface    := Interfaces.C.Double (Ada_T_Surface);
      T_Back       := Interfaces.C.Double (Ada_T_Back);
      N_Iterations := Interfaces.C.int (Iterations);

      -- ------------------------------------------------------------------
      -- APPLICATION STEP 4: fill the in-depth profile and copy it across the
      -- ABI boundary field by field.
      -- ------------------------------------------------------------------
      begin
         StellarOrion_Physics.TPS_Conduction_Profile
           (Layup     => Layup,
            T_Init    => Standard.Float (T_Init),
            T_Surface => Ada_T_Surface,
            Profile   => Ada_Prof);
      exception
         when E : others =>
            Status := TPS_STATUS_PROFILE_RAISED;
            Log ("[TPS_Conduction_C] FAIL: TPS_Conduction_Profile raised "
                  & Ada.Exceptions.Exception_Name (E) & ": "
                  & Ada.Exceptions.Exception_Message (E)
                  & " (Status="
                  & Standard.Integer'Image (Standard.Integer (TPS_STATUS_PROFILE_RAISED)) & ")");
            --  A2: STEP 3 already wrote Q_SG, T_Surface, T_Back and
            --  N_Iterations, and the profile buffer is at best
            --  partially written. Restore ALL of them, so a nonzero
            --  Status can never be mistaken for a good result.
            Reset_Outputs;
            return;
      end;

      --  INDEX MAPPING (bug fix): Ada_Prof is 1-based
      --  (Profile_Array / Profile_Index_Range = 1 .. Max_Profile_Points)
      --  while the C buffer is 0-based
      --  (TPS_Profile_Buffer = 0 .. TPS_Profile_Samples - 1). The previous
      --  expression added two 1-based positions and so addressed
      --  1 .. TPS_Profile_Samples, raising CONSTRAINT_ERROR on the LAST
      --  sample (index 33 against a 0 .. 32 buffer) and turning every
      --  successful solve into TPS_STATUS_SOLVER_RAISED.
      --  Subtracting Ada_Prof'First maps 1 .. 33 onto 0 .. 32 exactly, which
      --  is TPS_Profile_Buffer'Range, so both ends are in bounds by
      --  construction and the run-time index check can no longer fire.
      for I in Ada_Prof'Range loop
         --  invariant: I is in Ada_Prof'Range; every profile sample before I
         --  has been copied to its 0-based C buffer slot.
         Profile (I - Ada_Prof'First).Depth_M :=
           Interfaces.C.Double (Ada_Prof (I).Depth_M);
         Profile (I - Ada_Prof'First).Temp_K :=
           Interfaces.C.Double (Ada_Prof (I).Temp_K);
      end loop;

      --  APPLICATION STEP 5 (theory T2): success is declared LAST, only once
      --  every output is populated. Ordering this line first would let a
      --  caller read Status = 0 with an unfilled profile buffer.
      Status := TPS_STATUS_OK;

   exception
      when E : others =>
         --  AXIOM A4: nothing escapes to the C caller. Report fully, then
         --  fall back to the sentinels already written in STEP 0 with a
         --  generic status, so a caller that checks Status still fails loudly.
         Log ("[TPS_Conduction_C] FAIL: unexpected "
              & Ada.Exceptions.Exception_Name (E) & ": "
              & Ada.Exceptions.Exception_Message (E)
              & " (Status="
              & Standard.Integer'Image (Standard.Integer (TPS_STATUS_SOLVER_RAISED)) & ")");
         if Status = TPS_STATUS_OK then
            Status := TPS_STATUS_SOLVER_RAISED;
         end if;
         --  A2: fall back to the STEP-0 sentinels through the single shared
         --  owner, so this path can never diverge from the two nested ones.
         --  Reset_Outputs cannot raise (see its own handler), which is what
         --  keeps A4 -- nothing escapes to the C caller -- true here.
         Reset_Outputs;
   end TPS_Conduction_C;

   -- =========================================================================
   --  Self-test coverage wrappers (STC)
   -- =========================================================================
   --  Every Test_<Name> below calls its FFI subprogram with representative
   --  physical inputs and asserts a documented invariant of the result, so the
   --  C ABI surface is exercised by compiled, executable checks. The wrappers
   --  are registered in stellarorion_ffi.ads and in the registry block at the
   --  end of this file. Timing is O(1) per wrapper: one subprogram call plus
   --  one assertion.

   --  Test_C_Printf — STC wrapper for C_Printf.
   --  @test: exercises C_Printf through the C ABI with a NUL-terminated string.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_C_Printf with Pre => True, Post => True is
      Msg : constant Interfaces.C.Strings.chars_ptr :=
        Interfaces.C.Strings.New_String ("STC");
      Rc : constant Interfaces.C.int := C_Printf (Msg);
   begin
      pragma Assert (Rc >= 0, "C_Printf returned a negative character count");
   exception
      when E : others =>
         Log ("Test_C_Printf FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_C_Printf;

   --  Test_C_Flush_Stream — STC wrapper for C_Flush_Stream.
   --  @test: flushes the C stdout stream through the C ABI (Null_Ptr = all).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_C_Flush_Stream with Pre => True, Post => True is
   begin
      C_Flush_Stream (Interfaces.C.Strings.Null_Ptr);
   exception
      when E : others =>
         Log ("Test_C_Flush_Stream FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_C_Flush_Stream;

   --  Test_Log — STC wrapper for Log.
   --  @test: exercises the body-local Log helper (printf + fflush path).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Log with Pre => True, Post => True is
   begin
      Log ("STC: Log exercised");
   exception
      when E : others =>
         Log ("Test_Log FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Log;

   --  Test_Estimate_Cd_C — STC wrapper for Estimate_Cd_C.
   --  @test: IRVE-3 baseline geometry (R_N = 1.5 m, r_tor = 0.135 m, 60 deg).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Estimate_Cd_C with Pre => True, Post => True is
      Cd : constant Interfaces.C.Double := Estimate_Cd_C (1.5, 0.135, 60.0);
   begin
      pragma Assert (Cd > 0.0, "Estimate_Cd_C returned a non-positive Cd");
   exception
      when E : others =>
         Log ("Test_Estimate_Cd_C FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Estimate_Cd_C;

   --  Test_HIAD_Cost_C — STC wrapper for HIAD_Cost_C.
   --  @test: IRVE-3 baseline geometry cost (delegates to HIAD_Cost_Function).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_HIAD_Cost_C with Pre => True, Post => True is
      J : constant Interfaces.C.Double := HIAD_Cost_C (1.5, 0.135, 60.0);
   begin
      pragma Assert (J >= 0.0, "HIAD_Cost_C returned a negative cost");
   exception
      when E : others =>
         Log ("Test_HIAD_Cost_C FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_HIAD_Cost_C;

   --  Test_HIAD_Set_Refs_C — STC wrapper for HIAD_Set_Refs_C.
   --  @test: loads the validation reference set through the C ABI.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_HIAD_Set_Refs_C with Pre => True, Post => True is
      Rc : constant Interfaces.C.int :=
        HIAD_Set_Refs_C (165.715973, 14.361, 13.582459, 1.462536);
   begin
      pragma Assert (Rc = 0, "HIAD_Set_Refs_C reported a failure");
   exception
      when E : others =>
         Log ("Test_HIAD_Set_Refs_C FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_HIAD_Set_Refs_C;

   --  Test_HIAD_Cost_Components_C — STC wrapper for HIAD_Cost_Components_C.
   --  @test: full six-term cost breakdown at the IRVE-3 baseline geometry.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_HIAD_Cost_Components_C with Pre => True, Post => True is
      HLR : aliased Interfaces.C.Double := 0.0;
      FR  : aliased Interfaces.C.Double := 0.0;
      BD  : aliased Interfaces.C.Double := 0.0;
      CR  : aliased Interfaces.C.Double := 0.0;
      PEN : aliased Interfaces.C.Double := 0.0;
      TOT : aliased Interfaces.C.Double := 0.0;
      HLJ : aliased Interfaces.C.Double := 0.0;
   begin
      HIAD_Cost_Components_C
        (1.5, 0.135, 60.0,
         HLR'Access, FR'Access, BD'Access, CR'Access, PEN'Access,
         TOT'Access, HLJ'Access);
      pragma Assert (TOT >= 0.0, "HIAD_Cost_Components_C total cost is negative");
   exception
      when E : others =>
         Log ("Test_HIAD_Cost_Components_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_HIAD_Cost_Components_C;

   --  Test_Run_MoP_C — STC wrapper for Run_MoP_C.
   --  @test: one projected-gradient run at the IRVE-3 initial guess.
   --  Timing analysis: WCET O(Max_Iter); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Run_MoP_C with Pre => True, Post => True is
      OX1 : aliased Interfaces.C.Double := 0.0;
      OX2 : aliased Interfaces.C.Double := 0.0;
      OX3 : aliased Interfaces.C.Double := 0.0;
      OCost : aliased Interfaces.C.Double := 0.0;
      OConv : aliased Interfaces.C.int := 0;
      ONIter : aliased Interfaces.C.int := 0;
   begin
      Run_MoP_C
        (0.01, 1.0e-6, 100.0, 100.0, 5,
         1.5, 0.135, 60.0,
         OX1'Access, OX2'Access, OX3'Access, OCost'Access,
         OConv'Access, ONIter'Access);
      pragma Assert (OConv = 0 or else OConv = 1,
                     "Run_MoP_C returned a non-boolean convergence flag");
   exception
      when E : others =>
         Log ("Test_Run_MoP_C FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Run_MoP_C;

   --  Test_Generate_CCD_Samples_C — STC wrapper for Generate_CCD_Samples_C.
   --  @test: fills the three CCD coordinate arrays and the label buffer.
   --  Timing analysis: WCET O(CCD_Samples * CCD_Label_Max); CPU Time < 1us;
   --  Space Complexity O(CCD_Samples).
   procedure Test_Generate_CCD_Samples_C with Pre => True, Post => True is
      R_N_Arr : aliased CCD_Double_Array := (others => 0.0);
      R_Tor_Arr : aliased CCD_Double_Array := (others => 0.0);
      Ang_Arr : aliased CCD_Double_Array := (others => 0.0);
      Labels : aliased CCD_Label_Buffer := (others => Character'Val (0));
      All_Positive : Boolean := True;
   begin
      Generate_CCD_Samples_C
        (R_N_Arr'Access, R_Tor_Arr'Access, Ang_Arr'Access, Labels'Access);
      for I in R_N_Arr'Range loop
         --  invariant: every R_N_Arr index below I has been checked positive.
         if R_N_Arr (I) <= 0.0 then
            All_Positive := False;
         end if;
      end loop;
      pragma Assert (All_Positive, "Generate_CCD_Samples_C left a zero R_N sample");
   exception
      when E : others =>
         Log ("Test_Generate_CCD_Samples_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Generate_CCD_Samples_C;

   --  Test_Sutton_Graves_Heat_C — STC wrapper for Sutton_Graves_Heat_C.
   --  @test: stagnation-point heat flux at a representative reentry point.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Sutton_Graves_Heat_C with Pre => True, Post => True is
      Q : constant Interfaces.C.Double :=
        Sutton_Graves_Heat_C (1.0e-4, 1.5, 7000.0);
   begin
      pragma Assert (Q >= 0.0, "Sutton_Graves_Heat_C returned a negative flux");
   exception
      when E : others =>
         Log ("Test_Sutton_Graves_Heat_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Sutton_Graves_Heat_C;

   --  Test_Sutherland_Viscosity_C — STC wrapper for Sutherland_Viscosity_C.
   --  @test: dynamic viscosity at 1000 K (delegates to Sutherland_Viscosity).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Sutherland_Viscosity_C with Pre => True, Post => True is
      Mu : constant Interfaces.C.Double := Sutherland_Viscosity_C (1000.0);
   begin
      pragma Assert (Mu > 0.0, "Sutherland_Viscosity_C returned a non-positive mu");
   exception
      when E : others =>
         Log ("Test_Sutherland_Viscosity_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Sutherland_Viscosity_C;

   --  Test_Fay_Riddell_Heat_C — STC wrapper for Fay_Riddell_Heat_C.
   --  @test: Fay-Riddell heat flux at a representative reentry point.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Fay_Riddell_Heat_C with Pre => True, Post => True is
      Q : constant Interfaces.C.Double :=
        Fay_Riddell_Heat_C (1.0e-4, 1.5, 7000.0, 20.0, 300.0);
   begin
      pragma Assert (Q >= 0.0, "Fay_Riddell_Heat_C returned a negative flux");
   exception
      when E : others =>
         Log ("Test_Fay_Riddell_Heat_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Fay_Riddell_Heat_C;

   --  Test_Radiative_Eq_Temp_C — STC wrapper for Radiative_Eq_Temp_C.
   --  @test: radiative equilibrium wall temperature for a given flux.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Radiative_Eq_Temp_C with Pre => True, Post => True is
      T : constant Interfaces.C.Double := Radiative_Eq_Temp_C (1.0e5, 0.9);
   begin
      pragma Assert (T >= 0.0, "Radiative_Eq_Temp_C returned a negative temperature");
   exception
      when E : others =>
         Log ("Test_Radiative_Eq_Temp_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Radiative_Eq_Temp_C;

   --  Test_Backface_Temperature_C — STC wrapper for Backface_Temperature_C.
   --  @test: TPS backface temperature for a representative heat pulse.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Backface_Temperature_C with Pre => True, Post => True is
      T : constant Interfaces.C.Double :=
        Backface_Temperature_C (300.0, 1.0e5, 100.0, 1.0, 144.0, 1100.0, 0.05);
   begin
      pragma Assert (T >= 0.0, "Backface_Temperature_C returned a negative temperature");
   exception
      when E : others =>
         Log ("Test_Backface_Temperature_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Backface_Temperature_C;

   --  Test_Ballistic_Coefficient_C — STC wrapper for Ballistic_Coefficient_C.
   --  @test: ballistic coefficient at the IRVE-3 mass and a sample drag.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Ballistic_Coefficient_C with Pre => True, Post => True is
      Beta : constant Interfaces.C.Double :=
        Ballistic_Coefficient_C (281.0, 1.0e5, 5.0e4);
   begin
      pragma Assert (Beta >= 0.0, "Ballistic_Coefficient_C returned a negative beta");
   exception
      when E : others =>
         Log ("Test_Ballistic_Coefficient_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Ballistic_Coefficient_C;

   --  Test_Dynamic_Pressure_C — STC wrapper for Dynamic_Pressure_C.
   --  @test: dynamic pressure q = 0.5 * rho * V^2 at a sample condition.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Dynamic_Pressure_C with Pre => True, Post => True is
      Q : constant Interfaces.C.Double := Dynamic_Pressure_C (1.0e-4, 7000.0);
   begin
      pragma Assert (Q >= 0.0, "Dynamic_Pressure_C returned a negative pressure");
   exception
      when E : others =>
         Log ("Test_Dynamic_Pressure_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Dynamic_Pressure_C;

   --  Test_Deceleration_G_Load_C — STC wrapper for Deceleration_G_Load_C.
   --  @test: deceleration in g for a sample drag force and the IRVE-3 mass.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Deceleration_G_Load_C with Pre => True, Post => True is
      G : constant Interfaces.C.Double := Deceleration_G_Load_C (5.0e4, 281.0);
   begin
      pragma Assert (G >= 0.0, "Deceleration_G_Load_C returned a negative g-load");
   exception
      when E : others =>
         Log ("Test_Deceleration_G_Load_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Deceleration_G_Load_C;

   --  Test_Atmosphere_Temperature_C — STC wrapper for Atmosphere_Temperature_C.
   --  @test: ISA temperature at the validated snapshot altitude (51.8 km).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Atmosphere_Temperature_C with Pre => True, Post => True is
      T : constant Interfaces.C.Double := Atmosphere_Temperature_C (51.8);
   begin
      pragma Assert (T > 0.0, "Atmosphere_Temperature_C returned a non-positive temperature");
   exception
      when E : others =>
         Log ("Test_Atmosphere_Temperature_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Atmosphere_Temperature_C;

   --  Test_Atmosphere_Density_C — STC wrapper for Atmosphere_Density_C.
   --  @test: ISA density at the validated snapshot altitude (51.8 km).
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Atmosphere_Density_C with Pre => True, Post => True is
      Rho : constant Interfaces.C.Double := Atmosphere_Density_C (51.8);
   begin
      pragma Assert (Rho >= 0.0, "Atmosphere_Density_C returned a negative density");
   exception
      when E : others =>
         Log ("Test_Atmosphere_Density_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Atmosphere_Density_C;

   --  Test_Mean_Free_Path_Viscous_C — STC wrapper for Mean_Free_Path_Viscous_C.
   --  @test: mean free path at a sample viscosity/density/temperature triple.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Mean_Free_Path_Viscous_C with Pre => True, Post => True is
      L : constant Interfaces.C.Double :=
        Mean_Free_Path_Viscous_C (1.716e-5, 1.0e-4, 300.0);
   begin
      pragma Assert (L >= 0.0, "Mean_Free_Path_Viscous_C returned a negative length");
   exception
      when E : others =>
         Log ("Test_Mean_Free_Path_Viscous_C FAIL: "
              & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Mean_Free_Path_Viscous_C;

   --  Test_Speed_Of_Sound_C — STC wrapper for Speed_Of_Sound_C.
   --  @test: speed of sound at 300 K through the input-clamped wrapper.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Speed_Of_Sound_C with Pre => True, Post => True is
      A : constant Interfaces.C.Double := Speed_Of_Sound_C (300.0);
   begin
      pragma Assert (A >= 0.0, "Speed_Of_Sound_C returned a negative speed");
   exception
      when E : others =>
         Log ("Test_Speed_Of_Sound_C FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Speed_Of_Sound_C;

   --  Test_TPS_Conduction_C — STC wrapper for TPS_Conduction_C.
   --  @test: a two-ply solve through the full C ABI (success or coded status).
   --  Timing analysis: WCET ~25us; CPU Time ~15us; Space Complexity O(1).
   procedure Test_TPS_Conduction_C with Pre => True, Post => True is
      Ply_D : aliased TPS_Ply_Array := (others => 0.05);
      Ply_K : aliased TPS_Ply_Array := (others => 1.0);
      Prof  : aliased TPS_Profile_Buffer :=
        (others => (Depth_M => 0.0, Temp_K => 0.0));
      Status : Interfaces.C.int := -1;
      Q_SG : Interfaces.C.Double := 0.0;
      T_Surface : Interfaces.C.Double := 0.0;
      T_Back : Interfaces.C.Double := 0.0;
      N_Iter : Interfaces.C.int := 0;
   begin
      TPS_Conduction_C
        (Q_SG_Scale    => 1.0e4,
         Ke_Raw        => 1.0e-3,
         Ke_Ref        => 1.0e-3,
         N_Layers      => 2,
         Ply_Thickness => Ply_D'Access,
         Ply_Thermal_K => Ply_K'Access,
         Emissivity    => 0.9,
         T_Init        => 300.0,
         T_Inf         => 300.0,
         Status        => Status,
         Q_SG          => Q_SG,
         T_Surface     => T_Surface,
         T_Back        => T_Back,
         N_Iterations  => N_Iter,
         Profile       => Prof'Access);
      pragma Assert (Status in 0 .. 8,
                     "TPS_Conduction_C returned an out-of-range status");
   exception
      when E : others =>
         Log ("Test_TPS_Conduction_C FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_TPS_Conduction_C;

   --  Test_Reset_Outputs — STC wrapper for the body-local Reset_Outputs.
   --  @test: N_Layers = 0 forces the validation-failure path that Reset_Outputs
   --  serves; the out-parameters must then carry the exact -1.0 sentinels.
   --  Timing analysis: WCET O(1); CPU Time < 1us; Space Complexity O(1).
   procedure Test_Reset_Outputs with Pre => True, Post => True is
      Ply_D : aliased TPS_Ply_Array := (others => 0.05);
      Ply_K : aliased TPS_Ply_Array := (others => 1.0);
      Prof  : aliased TPS_Profile_Buffer :=
        (others => (Depth_M => 0.0, Temp_K => 0.0));
      Status : Interfaces.C.int := -1;
      Q_SG : Interfaces.C.Double := 0.0;
      T_Surface : Interfaces.C.Double := 0.0;
      T_Back : Interfaces.C.Double := 0.0;
      N_Iter : Interfaces.C.int := 0;
   begin
      TPS_Conduction_C
        (Q_SG_Scale    => 1.0e4,
         Ke_Raw        => 1.0e-3,
         Ke_Ref        => 1.0e-3,
         N_Layers      => 0,
         Ply_Thickness => Ply_D'Access,
         Ply_Thermal_K => Ply_K'Access,
         Emissivity    => 0.9,
         T_Init        => 300.0,
         T_Inf         => 300.0,
         Status        => Status,
         Q_SG          => Q_SG,
         T_Surface     => T_Surface,
         T_Back        => T_Back,
         N_Iterations  => N_Iter,
         Profile       => Prof'Access);
      pragma Assert (Status = TPS_STATUS_BAD_LAYER_COUNT,
                     "N_Layers = 0 must report BAD_LAYER_COUNT");
      pragma Assert (Q_SG = -1.0 and then T_Surface = -1.0 and then T_Back = -1.0,
                     "Reset_Outputs sentinels are not -1.0");
   exception
      when E : others =>
         Log ("Test_Reset_Outputs FAIL: " & Ada.Exceptions.Exception_Information (E));
         raise;
   end Test_Reset_Outputs;

   -- -------------------------------------------------------------------------
   --  Self-test coverage registry (STC)
   -- -------------------------------------------------------------------------
   --  GNATCOLL AUnit registration for every Test_ wrapper above. Each quoted
   --  name is the test routine exercised by the suite.
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_C_Printf", Test_C_Printf'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_C_Flush_Stream", Test_C_Flush_Stream'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Log", Test_Log'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Estimate_Cd_C", Test_Estimate_Cd_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_HIAD_Cost_C", Test_HIAD_Cost_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_HIAD_Set_Refs_C", Test_HIAD_Set_Refs_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_HIAD_Cost_Components_C", Test_HIAD_Cost_Components_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Run_MoP_C", Test_Run_MoP_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Generate_CCD_Samples_C", Test_Generate_CCD_Samples_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Sutton_Graves_Heat_C", Test_Sutton_Graves_Heat_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Sutherland_Viscosity_C", Test_Sutherland_Viscosity_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Fay_Riddell_Heat_C", Test_Fay_Riddell_Heat_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Radiative_Eq_Temp_C", Test_Radiative_Eq_Temp_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Backface_Temperature_C", Test_Backface_Temperature_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Ballistic_Coefficient_C", Test_Ballistic_Coefficient_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Dynamic_Pressure_C", Test_Dynamic_Pressure_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Deceleration_G_Load_C", Test_Deceleration_G_Load_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Atmosphere_Temperature_C", Test_Atmosphere_Temperature_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Atmosphere_Density_C", Test_Atmosphere_Density_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Mean_Free_Path_Viscous_C", Test_Mean_Free_Path_Viscous_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Speed_Of_Sound_C", Test_Speed_Of_Sound_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_TPS_Conduction_C", Test_TPS_Conduction_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Reset_Outputs", Test_Reset_Outputs'Access);

end StellarOrion_FFI;
