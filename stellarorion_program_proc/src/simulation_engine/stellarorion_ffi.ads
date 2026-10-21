-- =============================================================================
-- StellarOrion_FFI — C-Compatible Foreign Function Interface Layer
-- =============================================================================
-- AXIOMS:
--   1. The Ada runtime uses IEEE 754 double-precision floats, which map
--      directly to C's `double` via Interfaces.C.Double.
--   2. C callers cannot manage Ada memory; all outputs are returned through
--      pointer parameters (out-parameters as access types).
--   3. Each exported function is a thin wrapper that converts between C types
--      and Ada types, then delegates to StellarOrion_Optimization.
--   4. The shared library must export C-linkage symbols so that ctypes/cffi
--      in Python can resolve them by name via the platform dynamic loader.
--
-- THEOREMS:
--   1. Since Interfaces.C.Double is defined as Standard.Long_Float which is
--      IEEE 754 binary64, no precision loss occurs in type conversion.
--   2. Interfaces.C.int is a 32-bit signed integer, sufficient for Max_Iter
--      values up to 2^31 - 1 and Boolean-as-int encoding (0/1).
--   3. All pointer outputs are validated non-null by the caller contract;
--      dereferencing is safe under the precondition checks.
--
-- CITATIONS:
--   [Ada2012]  ISO/IEC 8652:2012 — Ada Reference Manual, Interfaces.C package.
--   [IEEE754]  IEEE 754-2019 — Standard for Floating-Point Arithmetic.
--   [Ctypes]  Python ctypes documentation —
--              https://docs.python.org/3/library/ctypes.html
--   [Dyld]    Apple dynamic-loader man pages (macOS dylib symbol resolution).
--
-- Author: Albert Starfield Wahyu Suryo Samudro
-- =============================================================================


with Interfaces.C; use Interfaces.C;
with StellarOrion_Types; use StellarOrion_Types;
with StellarOrion_Physics;
--  WHY: the C-callable surrogate-based GA entry drives
--  StellarOrion_Optimization.Run_GA_Optimization and hands the caller the
--  optimiser's own C-layout history buffer, so the optimiser package has to
--  be visible here.  No cycle: the optimiser does NOT with the FFI.
with StellarOrion_Optimization;

package StellarOrion_FFI is
   pragma SPARK_Mode (Off);
   --  FFI: C ABI interop boundary — external C linkage, foreign exported
   --  symbols and volatile memory-mapped registers are outside the SPARK
   --  subset, so this package is compiled with SPARK_Mode off.

   -- -------------------------------------------------------------------------
   --  Estimate_Cd_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Estimate_Cd.
   --  Estimates the drag coefficient Cd for a given HIAD geometry.
   --
   --  AXIOMS:
   --    R_N, R_Tor, Half_Cone_Deg are passed as C doubles and converted
   --    to Ada Float for the underlying computation. N_Tori defaults to 6
   --    (IRVE-3 baseline) since the C interface does not expose it.
   --
   --  Parameters:
   --    R_N           — nose sphere radius [m]
   --    R_Tor         — torus minor (tube) radius [m]
   --    Half_Cone_Deg — half-cone angle [degrees]
   --
   --  Returns:
   --    Estimated drag coefficient Cd (> 0.0).
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics, Sec 5.4.
   -- -------------------------------------------------------------------------
   function Estimate_Cd_C
     (R_N           : Interfaces.C.Double;
      R_Tor         : Interfaces.C.Double;
      Half_Cone_Deg : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => R_N > 0.0 and then R_Tor > 0.0
                and then Half_Cone_Deg > 0.0 and then Half_Cone_Deg < 90.0,
        Post => Estimate_Cd_C'Result >= 0.0;
   pragma Export (C, Estimate_Cd_C, "Estimate_Cd_C");

   -- -------------------------------------------------------------------------
   --  HIAD_Cost_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.HIAD_Cost_Function.
   --  Evaluates the PINN-inspired cost function for HIAD geometry.
   --
   --  AXIOMS:
   --    The parameter vector X is decomposed into three C doubles (X1, X2, X3)
   --    corresponding to [R_N, r_tor, half_cone_deg]. This flat representation
   --    avoids the need for array marshalling across the FFI boundary.
   --
   --  Parameters:
   --    X1 — nose sphere radius R_N [m]
   --    X2 — torus minor radius r_tor [m]
   --    X3 — half-cone angle [degrees]
   --
   --  Returns:
   --    Cost value J >= 0.0 (Cd + penalty terms).
   --
   --  CITATION:
   --    [Nocedal06] Nocedal & Wright (2006), Numerical Optimization, Sec 17.1.
   -- -------------------------------------------------------------------------
   function HIAD_Cost_C
     (X1 : Interfaces.C.Double;
      X2 : Interfaces.C.Double;
      X3 : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => X1 > 0.0 and then X2 > 0.0
                and then X3 > 0.0 and then X3 < 90.0,
        Post => HIAD_Cost_C'Result >= 0.0;
   pragma Export (C, HIAD_Cost_C, "HIAD_Cost_C");

   -- -------------------------------------------------------------------------
   --  HIAD_Set_Refs_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Set_Validation_Refs.
   --  Loads the DYNAMIC validation base reference used by J(x) after
   --  the Python driver reads unified_comparison_data.json at run
   --  time — J(x) normalises against the CURRENT validation state.
   --
   --  AXIOMS:
   --    The four doubles map 1:1 to the Ada procedure parameters
   --    (Interfaces.C.Double = IEEE binary64, no precision loss).
   --
   --  Parameters:
   --    Q_Target — Total Heat Load target [J/cm^2]
   --    Flux_Ref — reference peak heat flux [W/cm^2]
   --    Tau_Sec  — effective heating duration [s]
   --    Cd_Ref   — reference drag coefficient
   --
   --  Returns:
   --    0 = references updated; 1 = failed (previous refs kept).
   --    The Python wrapper turns a non-zero status into RuntimeError
   --    with the full parameter context.
   --
   --  Safety fallback: on exception (including non-positive inputs,
   --  which the Ada Pre forbids), the previously loaded refs remain
   --  intact, a literal-only line is logged (dylib-safe), and control
   --  returns normally — exceptions are NEVER raised across the C
   --  boundary (secondary stack is unavailable for foreign threads,
   --  so no unconstrained String operations may run here).
   --
   --  CITATION:
   --    [Ctypes] Python ctypes — four c_double passed by value;
   --             https://docs.python.org/3/library/ctypes.html
   -- -------------------------------------------------------------------------
   function HIAD_Set_Refs_C
     (Q_Target : Interfaces.C.Double;
      Flux_Ref : Interfaces.C.Double;
      Tau_Sec  : Interfaces.C.Double;
      Cd_Ref   : Interfaces.C.Double)
      return Interfaces.C.int
   with Pre  => Q_Target > 0.0 and then Flux_Ref > 0.0
                and then Tau_Sec > 0.0 and then Cd_Ref > 0.0,
        Post => HIAD_Set_Refs_C'Result in 0 .. 1;
   pragma Export (C, HIAD_Set_Refs_C, "HIAD_Set_Refs_C");

   -- -------------------------------------------------------------------------
   --  HIAD_Cost_Components_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.HIAD_Cost_Components.
   --  Returns the full J(x) breakdown (seven doubles) through output
   --  pointers so hiad_optimizer.py can report every term of the
   --  multi-objective cost in its results JSON.
   --
   --  AXIOMS:
   --    Output pointers are pre-allocated by the caller (ctypes
   --    byref(c_double)); each is written exactly once per call.
   --
   --  Parameters:
   --    X1, X2, X3  — [R_N, r_tor, half_cone_deg]
   --    Out_*       — write-back pointers for Heat_Load_Ratio,
   --                  Flux_Ratio, Beta_Dev, Cd_Ratio, Penalty,
   --                  Total (J(x)), Heat_Load_Jcm2 (absolute Q(x))
   --
   --  Safety fallback: on exception every output is zeroed and
   --  Out_Total is set to -1.0 — the same sentinel contract as
   --  HIAD_Cost_C (J(x) >= 0.0 always, so < 0 means failure).
   --
   --  CITATION:
   --    [Ctypes] ctypes.POINTER(c_double) + byref pattern;
   --             https://docs.python.org/3/library/ctypes.html
   -- -------------------------------------------------------------------------
   procedure HIAD_Cost_Components_C
     (X1, X2, X3             : Interfaces.C.Double;
      Out_Heat_Load_Ratio    : access Interfaces.C.Double;
      Out_Flux_Ratio         : access Interfaces.C.Double;
      Out_Beta_Dev           : access Interfaces.C.Double;
      Out_Cd_Ratio           : access Interfaces.C.Double;
      Out_Penalty            : access Interfaces.C.Double;
      Out_Total              : access Interfaces.C.Double;
      Out_Heat_Load_Jcm2     : access Interfaces.C.Double;
      Out_Cd_Deficit        : access Interfaces.C.Double)
   with Pre  => X1 > 0.0 and then X2 > 0.0 and then X3 > 0.0
                and then X3 < 90.0 and then Out_Total /= null,
        Post => Out_Total.all >= -1.0
                or else Out_Total.all = Interfaces.C.Double'First;
   pragma Export (C, HIAD_Cost_Components_C, "HIAD_Cost_Components_C");

   -- -------------------------------------------------------------------------
   --  Run_MoP_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Run_MoP_Optimization.
   --  Runs the Method of Projected Gradients optimizer.
   --
   --  AXIOMS:
   --    1. MoP configuration fields are passed as individual C doubles/int
   --       and assembled into a MoP_Config record inside the wrapper.
   --    2. Initial guess is passed as three doubles and assembled into
   --       a Param_Vector.
   --    3. All results are written through output pointer parameters so that
   --       the C caller owns the memory.
   --    4. Boolean is encoded as C int: 1 = True, 0 = False.
   --
   --  Parameters:
   --    Learning_Rate  — gradient descent step size
   --    Tolerance      — convergence tolerance (||grad||_inf)
   --    Lambda_1       — penalty weight for max_radius constraint
   --    Lambda_2       — penalty weight for nose_radius constraint
   --    Max_Iter       — maximum number of iterations
   --    X1, X2, X3     — initial parameter guess [R_N, r_tor, half_cone_deg]
   --    Out_X1, Out_X2, Out_X3 — output optimal parameters
   --    Out_Cost       — output cost at optimum
   --    Out_Converged  — output convergence flag (1 = converged, 0 = not)
   --    Out_N_Iter     — output number of iterations used
   --
   --  CITATIONS:
   --    [Boyd04]   Boyd & Vandenberghe (2004), Convex Optimization, Sec 2.3.
   --    [Bertsekas99] Bertsekas (1999), Nonlinear Programming, Sec 2.7.
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
   with Pre  => Learning_Rate > 0.0 and then Tolerance > 0.0
                and then Max_Iter > 0
                and then Out_X1 /= null and then Out_X2 /= null
                and then Out_X3 /= null and then Out_Cost /= null
                and then Out_Converged /= null and then Out_N_Iter /= null,
        Post => Out_Converged.all = 0
                  or else (Out_Converged.all = 1
                           and then Out_N_Iter.all <= Max_Iter)
                  or else Out_Converged.all not in 0 .. 1;
   pragma Export (C, Run_MoP_C, "Run_MoP_C");

   -- -------------------------------------------------------------------------
   --  Run_SBO_GA_C
   -- -------------------------------------------------------------------------
   --  C wrapper for the surrogate-based genetic algorithm:
   --  StellarOrion_Optimization.Run_GA_Optimization driven by
   --  StellarOrion_Optimization.SBO_Fitness.
   --
   --  AXIOMS:
   --    A1. The 2^3 factorial design is evaluated in the ANALYTIC screening
   --        space (R_N, r_tor, half_cone_deg) around the CCD centre
   --        (CCD_Centre_R_N, CCD_Centre_R_Tor, CCD_Centre_Cone) using the
   --        half-widths (CCD_Delta_R_N, CCD_Delta_R_Tor, CCD_Delta_Cone).
   --        The design therefore matches the coded coordinates the surrogate
   --        is fitted in, so the fitted contrasts are exact.
   --    A2. The surrogate response is the DIMENSIONLESS heat-load ratio
   --        Q(x)/Q_target, so the model-fidelity penalty stays O(1) and
   --        cannot swamp the analytic screening cost J.
   --    A3. The reported coordinates are projected onto the analytic
   --        screening box R_N in [0.5, 3.0], r_tor in [0.05, 0.5],
   --        half_cone in [40, 80] -- the same box the Python Bayesian
   --        optimiser searches -- so the C caller can compare the two
   --        optimisers on the same domain.  The reported cost is the fitness
   --        the GA actually minimised.
   --    A4. The model-fidelity penalty weight is
   --        StellarOrion_Optimization.Model_Fidelity_Weight.
   --    A5. The history buffer is owned by the caller: the wrapper writes
   --        one row per generation into it in place, with no conversion
   --        copy and no heap allocation.
   --    A6. THE PHYSICAL-GEOMETRY CONVENTION (CALIBRATION DESIGN 2.1).
   --        Out_X1..Out_X3 stay ANALYTIC (they are what the GA
   --        minimised and what the existing callers compare), and FOUR
   --        APPENDED out-pointers carry the PHYSICAL vehicle:
   --          Out_Diameter_M      — 2 * X(1)   (body diameter [m])
   --          Out_Nose_Radius_M   — Nose_Radius_Ratio * X(1) (bluntness [m])
   --          Out_Toroid_Radius_M — X(2)       (torus tube radius [m])
   --          Out_Angle_Deg       — X(3)       (half-cone angle [deg])
   --        They come from the SAME projected triple through
   --        StellarOrion_Optimization.Analytic_To_Physical, so the C
   --        caller never re-derives the mapping.  It is exactly that
   --        re-derivation — the analytic triple being read as if it
   --        were a flight geometry — that produced the analytic/DSMC
   --        unsync documented in CALIBRATION DESIGN 1.2.
   --        The four pointers are APPENDED (not inserted) so the
   --        positional indices of the existing pointers stay stable for
   --        the already-shipped callers.
   --    A7. THIS ROUTE IS SEQUENTIAL, AND IT MUST STAY THAT WAY.
   --        Run_SBO_GA_C calls Run_SBO_GA with Evaluator => null, which
   --        selects the SEQUENTIAL population sweep.  A dlopen()ed GNAT
   --        library has NO INITIALISED SECONDARY STACK (the System
   --        package is elaborated by an Ada MAIN program, and a library
   --        has no main) and NO TASKING ENVIRONMENT (the master task is
   --        created by the Ada main).  Driving the Ravenscar worker pool
   --        from the library route therefore faults the host process:
   --        measured SIGSEGV (EXIT=139; faulthandler:
   --        system__secondary_stack__ss_mark).  The Ada MAIN
   --        (stellarorion_ga_runner) owns the tasking and the secondary
   --        stack and is the ONLY route that uses the parallel
   --        evaluator.
   --    A8. The calibration file is NOT loaded through this layer.
   --        CALIBRATION DESIGN 2.5 decided that the Ada/C string
   --        conversion makes the FFI route the wrong place for it: the
   --        calibration is loaded by the Ada PROGRAMS (the GA runner and
   --        the CLI driver), which know the path.  A C caller that wants
   --        the calibrated model must go through those programs.
   --
   --  Parameters:
   --    Population_Size — GA population size (1 .. Max_Population)
   --    Max_Generations — GA generation budget (>= 1)
   --    Target_Beta     — target ballistic coefficient
   --    History         — caller-allocated history buffer (may be null)
   --    Out_N_History   — number of history rows written
   --    Out_X1..Out_X3  — optimum in ANALYTIC coordinates
   --                      (R_N, r_tor, half_cone_deg)
   --    Out_Cost        — cost at the optimum
   --    Out_Converged   — output convergence flag (1 = converged, 0 = not)
   --    Out_N_Iter      — output number of generations used
   --    Out_Diameter_M  — PHYSICAL body diameter [m]
   --    Out_Nose_Radius_M   — PHYSICAL nose bluntness radius [m]
   --    Out_Toroid_Radius_M — PHYSICAL torus tube radius [m]
   --    Out_Angle_Deg   — PHYSICAL half-cone angle [deg]
   --
   --  CITATIONS:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics, Sec. 5.4 —
   --                 blunt-body drag: the nose bluntness radius is part
   --                 of the vehicle definition (it sets the drag
   --                 increment and the stagnation heating), so the
   --                 analytic triple is NOT a flight geometry.
   --    [NASA-TP-2013-4012] NASA/TP-2013-4012 — IRVE-3 reference
   --                 geometry (body radius 1.5 m, nose 0.55 m, torus
   --                 0.135 m, cone 60 deg): the anchor of the
   --                 analytic-to-physical convention.
   --    [Jones98]    Jones (1998), Surrogate-Based Optimization.
   --    [Goldberg89] Goldberg (1989), Genetic Algorithms in Search,
   --                 Optimization and Machine Learning.
   --    [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
   -- -------------------------------------------------------------------------
   --  C-callable history buffer: the optimiser's own C-layout row array, so
   --  the caller's buffer passes straight through with no conversion copy.
   subtype GA_History_Buffer is StellarOrion_Optimization.GA_History_Array;

   procedure Run_SBO_GA_C
     (Population_Size : Interfaces.C.int;
      Max_Generations : Interfaces.C.int;
      Target_Beta     : Interfaces.C.Double;
      History         : access GA_History_Buffer;
      Out_N_History   : access Interfaces.C.int;
      Out_X1          : access Interfaces.C.Double;
      Out_X2          : access Interfaces.C.Double;
      Out_X3          : access Interfaces.C.Double;
      Out_Cost        : access Interfaces.C.Double;
      Out_Converged   : access Interfaces.C.int;
      Out_N_Iter      : access Interfaces.C.int;
      --  APPENDED physical-geometry outputs (axiom A6).  The pointers
      --  above keep their positional indices.
      Out_Diameter_M      : access Interfaces.C.Double;
      Out_Nose_Radius_M   : access Interfaces.C.Double;
      Out_Toroid_Radius_M : access Interfaces.C.Double;
      Out_Angle_Deg       : access Interfaces.C.Double)
   with Pre  => Population_Size >= 1
                and then Population_Size <= StellarOrion_Optimization.Max_Population
                and then Max_Generations >= 1
                and then Out_N_History /= null and then Out_X1 /= null
                and then Out_X2 /= null and then Out_X3 /= null
                and then Out_Cost /= null and then Out_Converged /= null
                and then Out_N_Iter /= null
                and then Out_Diameter_M /= null
                and then Out_Nose_Radius_M /= null
                and then Out_Toroid_Radius_M /= null
                and then Out_Angle_Deg /= null,
        Post => (Out_Converged.all = 0
                  or else (Out_Converged.all = 1
                           and then Out_N_Iter.all <= Max_Generations)
                  or else Out_Converged.all not in 0 .. 1)
                  and then Out_Diameter_M.all >= 0.0
                  and then Out_Nose_Radius_M.all >= 0.0
                  and then Out_Toroid_Radius_M.all >= 0.0
                  and then Out_Angle_Deg.all >= 0.0;
   pragma Export (C, Run_SBO_GA_C, "Run_SBO_GA_C");

   -- -------------------------------------------------------------------------
   --  CCD Sample Array Types for FFI
   -- -------------------------------------------------------------------------
   --  AXIOMS:
   --    CCD_Sample_Count = 15 (8 factorial + 1 center + 6 axial).
   --    C callers allocate flat arrays of 15 doubles and pass them.
   --    Labels are a flat char buffer: 15 labels x 31 bytes = 465 bytes.
   --
   --  CITATION:
   --    [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
   -- -------------------------------------------------------------------------

   --  Number of CCD sample points (constant mirrors StellarOrion_Optimization).
   CCD_Samples : constant := 15;

   --  Label stride: 30 chars + 1 NUL terminator = 31 bytes per label.
   Label_Stride : constant := 31;

   --  Flat array type for CCD double outputs (C-compatible).
   type CCD_Double_Array is array (0 .. CCD_Samples - 1)
      of Interfaces.C.Double;
   pragma Convention (C, CCD_Double_Array);

   --  Flat array type for CCD label output (C-compatible char buffer).
   type CCD_Label_Buffer is array (0 .. CCD_Samples * Label_Stride - 1)
      of Character;
   pragma Convention (C, CCD_Label_Buffer);

   -- -------------------------------------------------------------------------
   --  Generate_CCD_Samples_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Optimization.Generate_CCD_Samples.
   --  Generates 15 CCD design points and returns them as flat arrays.
   --
   --  AXIOMS:
   --    1. Output arrays must be pre-allocated by the caller with at least
   --       15 elements each.
   --    2. Labels are returned as a flat char buffer: 15 x 31 bytes.
   --    3. Label content is padded with spaces to 30 chars, NUL-terminated.
   --
   --  Parameters:
   --    Out_R_N    — array of nose sphere radii (15 elements)
   --    Out_R_Tor  — array of torus radii (15 elements)
   --    Out_Angles — array of half-cone angles (15 elements)
   --    Out_Labels — flat char buffer: 15 labels x 31 bytes = 465 bytes
   --
   --  CITATION:
   --    [Montgomery17] Montgomery (2017), Design and Analysis of Experiments.
   -- -------------------------------------------------------------------------
   procedure Generate_CCD_Samples_C
     (Out_R_N    : access CCD_Double_Array;
      Out_R_Tor  : access CCD_Double_Array;
      Out_Angles : access CCD_Double_Array;
      Out_Labels : access CCD_Label_Buffer)
   with Pre  => Out_R_N /= null and then Out_R_Tor /= null
                and then Out_Angles /= null and then Out_Labels /= null,
        Post => True;
   pragma Export (C, Generate_CCD_Samples_C, "Generate_CCD_Samples_C");

   -- -------------------------------------------------------------------------
   --  Sutton_Graves_Heat_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Sutton_Graves_Heat.
   --  Computes stagnation-point convective heat flux via SG correlation.
   --
   --  Parameters:
   --    Density     — freestream density [kg/m^3]
   --    Nose_Radius — nose sphere radius [m]
   --    Velocity    — freestream velocity [m/s]
   --
   --  Returns:
   --    Heat flux [W/m^2].
   --
   --  CITATION:
   --    [SuttonGraves71] Sutton & Graves (1971), NASA TR R-376.
   -- -------------------------------------------------------------------------
   function Sutton_Graves_Heat_C
     (Density     : Interfaces.C.Double;
      Nose_Radius : Interfaces.C.Double;
      Velocity    : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Density > 0.0 and then Nose_Radius > 0.0
                and then Velocity >= 0.0,
        Post => Sutton_Graves_Heat_C'Result >= 0.0;
   pragma Export (C, Sutton_Graves_Heat_C, "Sutton_Graves_Heat_C");

   -- -------------------------------------------------------------------------
   --  Sutherland_Viscosity_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Postprocessing.Sutherland_Viscosity.
   --  Computes dynamic viscosity of air via Sutherland's law.
   --
   --  Parameters:
   --    T — absolute temperature [K]
   --
   --  Returns:
   --    Dynamic viscosity [Pa*s].
   --
   --  CITATION:
   --    [Sutherland93] Sutherland (1893); Anderson (2006) Sec 15.2.
   -- -------------------------------------------------------------------------
   function Sutherland_Viscosity_C
     (T : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => T > 0.0,
        Post => Sutherland_Viscosity_C'Result > 0.0;
   pragma Export (C, Sutherland_Viscosity_C, "Sutherland_Viscosity_C");

   -- -------------------------------------------------------------------------
   --  Fay_Riddell_Heat_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Fay_Riddell_Heat.
   --  Computes stagnation-point convective heat flux via FR correlation.
   --
   --  Parameters:
   --    Density_Kgm3  — freestream density [kg/m^3]
   --    Nose_Radius_M — nose sphere radius [m]
   --    Velocity_Ms   — freestream velocity [m/s]
   --    Mach          — freestream Mach number
   --    Wall_Temp_K   — wall temperature [K]
   --
   --  Returns:
   --    Heat flux [W/m^2].
   --
   --  CITATION:
   --    [FayRiddell58] Fay & Riddell (1958); Rapisarda (2023) Eq 3.82.
   -- -------------------------------------------------------------------------
   function Fay_Riddell_Heat_C
     (Density_Kgm3  : Interfaces.C.Double;
      Nose_Radius_M : Interfaces.C.Double;
      Velocity_Ms   : Interfaces.C.Double;
      Mach          : Interfaces.C.Double;
      Wall_Temp_K   : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Density_Kgm3 > 0.0 and then Nose_Radius_M > 0.0
                and then Velocity_Ms >= 0.0 and then Mach > 0.0
                and then Wall_Temp_K > 0.0,
        Post => Fay_Riddell_Heat_C'Result >= 0.0;
   pragma Export (C, Fay_Riddell_Heat_C, "Fay_Riddell_Heat_C");

   -- -------------------------------------------------------------------------
   --  Radiative_Eq_Temp_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Radiative_Eq_Temp.
   --  Computes radiative equilibrium surface temperature via Stefan-Boltzmann law.
   --  T = (q / (sigma * epsilon))^(1/4)
   --
   --  Parameters:
   --    Heat_Flux  — convective heat flux [W/m^2]
   --    Emissivity — surface emissivity [dimensionless, 0..1]
   --
   --  Returns:
   --    Surface temperature [K].
   --
   --  CITATION:
   --    [StefanBoltzmann] Stefan-Boltzmann law; stellarorion_physics.ads.
   -- -------------------------------------------------------------------------
   function Radiative_Eq_Temp_C
     (Heat_Flux  : Interfaces.C.Double;
      Emissivity : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Heat_Flux >= 0.0 and then Emissivity > 0.0
                and then Emissivity <= 1.0,
        Post => Radiative_Eq_Temp_C'Result >= 0.0;
   pragma Export (C, Radiative_Eq_Temp_C, "Radiative_Eq_Temp_C");

   -- -------------------------------------------------------------------------
   --  Backface_Temperature_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Backface_Temperature.
   --  Computes 1D transient backface temperature.
   --  T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
   --
   --  Parameters:
   --    Init_Temp     — initial temperature [K]
   --    Heat_Flux     — heat flux [W/m^2]
   --    Duration      — heating duration [s]
   --    Thermal_Lag   — thermal lag efficiency [dimensionless, 0..1]
   --    TPS_Density   — TPS material density [kg/m^3]
   --    TPS_Cp        — TPS specific heat [J/(kg*K)]
   --    TPS_Thickness — TPS thickness [m]
   --
   --  Returns:
   --    Backface temperature [K].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006); Rapisarda (2023) Sec 5.5.
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
   with Pre  => Init_Temp > 0.0 and then Heat_Flux >= 0.0
                and then Duration >= 0.0 and then Thermal_Lag >= 0.0
                and then TPS_Density > 0.0 and then TPS_Cp > 0.0
                and then TPS_Thickness > 0.0,
        Post => Backface_Temperature_C'Result >= 0.0;
   pragma Export (C, Backface_Temperature_C, "Backface_Temperature_C");

   -- -------------------------------------------------------------------------
   --  Ballistic_Coefficient_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Ballistic_Coefficient.
   --  Computes ballistic coefficient: beta = m * q / F_drag.
   --
   --  Parameters:
   --    Mass         — vehicle mass [kg]
   --    Dyn_Pressure — dynamic pressure [Pa]
   --    Drag_Force   — drag force [N]
   --
   --  Returns:
   --    Ballistic coefficient [kg/m^2].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics.
   -- -------------------------------------------------------------------------
   function Ballistic_Coefficient_C
     (Mass         : Interfaces.C.Double;
      Dyn_Pressure : Interfaces.C.Double;
      Drag_Force   : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Mass > 0.0 and then Dyn_Pressure >= 0.0
                and then Drag_Force > 0.0,
        Post => Ballistic_Coefficient_C'Result >= 0.0;
   pragma Export (C, Ballistic_Coefficient_C, "Ballistic_Coefficient_C");

   -- -------------------------------------------------------------------------
   --  Dynamic_Pressure_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Dynamic_Pressure.
   --  Computes dynamic pressure: q = 0.5 * rho * V^2.
   --
   --  Parameters:
   --    Density  — freestream density [kg/m^3]
   --    Velocity — freestream velocity [m/s]
   --
   --  Returns:
   --    Dynamic pressure [Pa].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics.
   -- -------------------------------------------------------------------------
   function Dynamic_Pressure_C
     (Density  : Interfaces.C.Double;
      Velocity : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Density >= 0.0 and then Velocity >= 0.0,
        Post => Dynamic_Pressure_C'Result >= 0.0;
   pragma Export (C, Dynamic_Pressure_C, "Dynamic_Pressure_C");

   -- -------------------------------------------------------------------------
   --  Deceleration_G_Load_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Deceleration_G_Load.
   --  Computes deceleration in Earth g's: n = F_drag / (m * g0).
   --
   --  Parameters:
   --    Drag_Force — drag force [N]
   --    Mass       — vehicle mass [kg]
   --
   --  Returns:
   --    Deceleration [g].
   --
   --  CITATION:
   --    [Anderson06] Anderson (2006), Hypersonic Gas Dynamics.
   -- -------------------------------------------------------------------------
   function Deceleration_G_Load_C
     (Drag_Force : Interfaces.C.Double;
      Mass       : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Drag_Force >= 0.0 and then Mass > 0.0,
        Post => Deceleration_G_Load_C'Result >= 0.0;
   pragma Export (C, Deceleration_G_Load_C, "Deceleration_G_Load_C");

   -- -------------------------------------------------------------------------
   --  Atmosphere_Temperature_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Environment.Atmosphere_Temperature.
   --  Computes ISA 1975 temperature [K] at altitude [km].
   --
   --  Parameters:
   --    Altitude_Km — altitude above sea level [km]
   --
   --  Returns:
   --    Temperature [K].
   --
   --  CITATION:
   --    [ISA] ISO 2533:1975, International Standard Atmosphere.
   -- -------------------------------------------------------------------------
   function Atmosphere_Temperature_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Altitude_Km >= 0.0 and then Altitude_Km <= 1000.0,
        Post => Atmosphere_Temperature_C'Result > 0.0;
   pragma Export (C, Atmosphere_Temperature_C, "Atmosphere_Temperature_C");

   -- -------------------------------------------------------------------------
   --  Atmosphere_Density_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Environment.Atmosphere_Density.
   --  Computes ISA 1975 density [kg/m^3] at altitude [km].
   --
   --  Parameters:
   --    Altitude_Km — altitude above sea level [km]
   --
   --  Returns:
   --    Density [kg/m^3].
   --
   --  CITATION:
   --    [ISA] ISO 2533:1975, International Standard Atmosphere.
   -- -------------------------------------------------------------------------
   function Atmosphere_Density_C
     (Altitude_Km : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Altitude_Km >= 0.0 and then Altitude_Km <= 1000.0,
        Post => Atmosphere_Density_C'Result >= 0.0;
   pragma Export (C, Atmosphere_Density_C, "Atmosphere_Density_C");

   -- -------------------------------------------------------------------------
   --  Mean_Free_Path_Viscous_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Physics.Mean_Free_Path_Viscous.
   --  Computes the viscous (Bird 1994 Sec 1.5) mean free path
   --      lambda = mu / (rho * sqrt(pi/2 * R * T))
   --  so the Python ISA helper no longer re-derives it (one truth, one value).
   --
   --  Parameters:
   --    Mu          — dynamic viscosity [Pa*s]
   --    Density     — mass density [kg/m^3]
   --    Temperature — static temperature [K]
   --
   --  Returns:
   --    Mean free path [m].
   --
   --  CITATION:
   --    [Bird1994] Bird (1994), Molecular Gas Dynamics, Sec 1.5.
   -- -------------------------------------------------------------------------
   function Mean_Free_Path_Viscous_C
     (Mu          : Interfaces.C.Double;
      Density     : Interfaces.C.Double;
      Temperature : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => Mu >= 0.0 and then Density > 0.0 and then Temperature > 0.0,
        Post => Mean_Free_Path_Viscous_C'Result >= 0.0;
   pragma Export (C, Mean_Free_Path_Viscous_C, "Mean_Free_Path_Viscous_C");

   -- -------------------------------------------------------------------------
   --  Speed_Of_Sound_C
   -- -------------------------------------------------------------------------
   --  C wrapper for StellarOrion_Environment.Speed_Of_Sound.
   --  Computes a = sqrt(gamma * R * T) so the Python field-panel plots no
   --  longer re-derive the speed of sound from temperature.
   --
   --  Parameters:
   --    Temperature — static temperature [K]
   --
   --  Returns:
   --    Speed of sound [m/s].
   --
   --  CITATION:
   --    [Anderson] Anderson, "Modern Compressible Flow," 3rd Ed., Ch. 2.
   -- -------------------------------------------------------------------------
   function Speed_Of_Sound_C
     (Temperature : Interfaces.C.Double)
      return Interfaces.C.Double
   with Pre  => True,
        Post => Speed_Of_Sound_C'Result >= 0.0;
   pragma Export (C, Speed_Of_Sound_C, "Speed_Of_Sound_C");

   -- =========================================================================
   --  TPS_Conduction_C — per-element composite F-TPS conduction (C ABI)
   -- =========================================================================
   --
   --  WHY A FLAT-ARRAY LAYUP RATHER THAN A HARD-CODED PRESET
   --  ------------------------------------------------------
   --  The IRVE-3 layup (TPS_Layup_IRVE3) is the DEFAULT, but hard-coding it
   --  here would make the topology/Gaussian optimisation impossible: that
   --  optimiser's design variables ARE the ply thicknesses and
   --  conductivities. Passing them as flat C arrays makes the layup a
   --  parameter, so one entry point serves both the flight case (pass the
   --  IRVE-3 values) and the search (pass each candidate).
   --
   --  AXIOMS:
   --   A1. Every quantity crossing this boundary is an IEEE 754 binary64
   --      (Interfaces.C.Double); conversion to the internal Float is
   --      therefore a representation change, not a rounding surprise, and
   --      the internal Float is the lower-precision of the two.
   --   A2. Out-parameters are written ONLY after validation, and EVERY out
   --      parameter is initialised to a documented sentinel before the first
   --      validation test. A caller that ignores Status therefore still
   --      receives defined numbers — never uninitialised memory.
   --   A3. Status is the single authoritative success indicator. It is
   --      checked by the Python wrapper, so a failure is visible to Python
   --      rather than being absorbed into a plausible-looking temperature.
   --   A4. No Ada exception escapes this procedure: an exception crossing a
   --      C frame is undefined behaviour, and the repository has already
   --      observed an FFI exception abort the host process
   --      (stellarorion_ffi.adb C_PRINTF axiom, 2026-09-25).
   --   A5. Logging uses libc printf, never Ada.Text_IO, for the reason in A4.
   --
   --  THEORIES:
   --   T1 (range safety). Because every input is validated against the very
   --      bounds that appear in the Pre => contracts of
   --      StellarOrion_Physics.TPS_Conduction, SG_Scaled_Element_Flux and
   --      TPS_Conduction_Profile, those subprograms cannot raise a
   --      Constraint_Error on data that passed validation here. Validation
   --      is therefore not defensive decoration — it is what makes the
   --      Status code exhaustive.
   --   T2 (no partial output). Status = 0 is set only after ALL four
   --      outputs are written, so Status = 0 implies a fully populated
   --      Profile buffer; a non-zero Status implies the sentinels of A2.
   --
   --  APPLICATIONS: see stellarorion_ffi.adb, TPS_Conduction_C.
   --
   --  CITATIONS:
   --   [Ada2012] ISO/IEC 8652:2012, RM 13.9.1 (aspect specifications),
   --            RM B.3 (Interfaces.C interoperability).
   --   [Ctypes] https://docs.python.org/3/library/ctypes.html
   --   [Baumeister06] Baumeister II & Marston, Fundamentals of Heat and Mass
   --            Transfer, 7th ed., Wiley, 2006, Ch. 4 and Ch. 11.
   --   [Dillman14] Dillman et al., AIAA 2014-4141 (IRVE-3, 250 degC limit).
   -- =========================================================================

   --  Number of in-depth samples in the profile buffer. Bound to the
   --  physics-side constant so the two CANNOT drift: a mismatch would
   --  silently truncate or overrun the caller's buffer.
   TPS_Profile_Samples : constant := StellarOrion_Physics.Max_Profile_Points;

   --  One in-depth profile sample, field-for-field identical to
   --  StellarOrion_Physics.Layered_Profile but in C types.
   --
   --  PHYSICAL MEANING OF EACH FIELD:
   --    Depth_M — PHYSICAL depth below the hot outer face [m]: 0 at the
   --               hot face and the total layup thickness at the cold
   --               inner face. Carrying metres here (rather than a
   --               normalised [0..1] fraction) means the C ABI needs no
   --               companion thickness argument and a caller cannot
   --               mis-scale the axis. Match field-for-field with
   --               StellarOrion_Physics.Layered_Profile.Depth_M.
   --    Temp_K  — temperature at that depth [K].
   type TPS_Profile_Sample is record
      Depth_M : Interfaces.C.Double;
      Temp_K  : Interfaces.C.Double;
   end record;
   pragma Convention (C, TPS_Profile_Sample);

   --  Fixed-size C buffer for the in-depth profile (TPS_Profile_Samples
   --  samples). A C caller declares the identical shape as
   --      struct { double depth_m, temp_k; } samples[33];
   type TPS_Profile_Buffer is array (0 .. TPS_Profile_Samples - 1)
     of TPS_Profile_Sample;
   pragma Convention (C, TPS_Profile_Buffer);

   --  Fixed-size C buffer for one per-ply scalar (thickness OR thermal
   --  conductivity), Max_TPS_Layers entries. Entries at index >= N_Layers
   --  are ignored by the callee — the same active-prefix convention as
   --  TPS_Layup.Layer_Count, so callers need not zero the tail.
   type TPS_Ply_Array is array (0 .. Max_TPS_Layers - 1)
     of Interfaces.C.Double;
   pragma Convention (C, TPS_Ply_Array);

   --  Status codes returned in the Status out-parameter.
   --
   --  WHY AN ENUM-LIKE INTEGER INSTEAD OF A BOOLEAN: a boolean cannot
   --  distinguish "the caller passed 0 plies" from "the solver blew up",
   --  and those need different fixes. Each code below names its own
   --  remedy. Also documented as constants below so neither the Ada nor the
   --  Python side has to hard-code a bare integer.
   TPS_STATUS_OK                 : constant Interfaces.C.int := 0;
   TPS_STATUS_BAD_LAYER_COUNT    : constant Interfaces.C.int := 1;
   TPS_STATUS_NULL_POINTER       : constant Interfaces.C.int := 2;
   TPS_STATUS_BAD_EMISSIVITY     : constant Interfaces.C.int := 3;
   TPS_STATUS_BAD_TEMPERATURE    : constant Interfaces.C.int := 4;
   TPS_STATUS_BAD_FLUX_INPUT     : constant Interfaces.C.int := 5;
   TPS_STATUS_BAD_PLY_PROPERTY   : constant Interfaces.C.int := 6;
   TPS_STATUS_SOLVER_RAISED      : constant Interfaces.C.int := 7;
   TPS_STATUS_PROFILE_RAISED     : constant Interfaces.C.int := 8;

   --  Reconstruct one surface element's heat flux and solve the composite
   --  F-TPS conduction through it, returning q_SG, T_s, T_back and the
   --  in-depth profile.
   --
   --  Parameters (inputs):
   --    Q_SG_Scale    — Sutton-Graves stagnation heat flux for the flight
   --                    condition [W/m^2]. This is the CALIBRATED magnitude;
   --                    the per-element distribution comes from Ke_Raw.
   --    Ke_Raw        — raw SPARTA per-element kinetic-energy flux [W/m^2].
   --                    May be negative (DSMC noise); that yields q = 0.
   --    Ke_Ref        — positive reference for Ke_Raw, e.g. the element's
   --                    own peak reading or the surface mean [W/m^2].
   --    N_Layers      — number of ACTIVE plies, 1 .. Max_TPS_Layers.
   --    Ply_Thickness — Max_TPS_Layers entries [m], hot face first.
   --    Ply_Thermal_K — Max_TPS_Layers entries [W/(m*K)], same order.
   --    Emissivity    — outer-surface emissivity, 1e-3 .. 1.
   --    T_Init        — initial/cold-side temperature [K], 0 .. 3000.
   --    T_Inf         — cold-stream temperature [K], 0 .. 3000.
   --
   --  Parameters (outputs):
   --    Status        — TPS_STATUS_* code (A3: the authoritative indicator).
   --    Q_SG          — the reconstructed element heat flux actually used by
   --                    the solver [W/m^2]. Non-negative by axiom Q1.
   --    T_Surface     — hot-face temperature T_s [K].
   --    T_Back        — cold-face temperature T_back [K].
   --    N_Iterations  — bisection iterations performed, so the caller can
   --                    detect a run that hit the cap instead of converging.
   --    Profile       — TPS_Profile_Samples in-depth samples, hot face first.
   --
   --  PHYSICAL MEANING OF THE OUTPUTS:
   --    Q_SG is the per-element heat flux the solver consumed — the single
   --    number the whole chain is calibrated against.
   --    T_Surface is what the OUTER material limit applies to; compare with
   --    IRVE3_FTPS_STRUCT_LIMIT_K (523.15 K / 250 degC).
   --    T_Back is what the PROTECTED STRUCTURE sees; this is the number that
   --    must stay under the structure limit.
   --    Profile is the intermediate thermal field, needed to see WHICH ply
   --    is running hot rather than only the two boundary temperatures.
   --
   --  T_Limit NOTE: the caller supplies Emissivity but NOT the structure
   --  temperature limit, because the solver does not compare against it —
   --  reporting a limit would require a policy decision (is exceeding it an
   --  error or a result to display?) that belongs to the caller, not to a
   --  physics entry point.
   --
   --  CITATION:
   --    [Baumeister06] Ch. 4 (composite-wall resistance), Ch. 11
   --    (radiation boundary condition); [Dillman14] IRVE-3 FTPS limit.
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
      --  LATERAL CONDUCTION INPUTS (axiom C5). See the physics spec's
      --  TPS_Conduction for the full derivation: Lateral_G = sum_j g_ij
      --  over the element's edge neighbours [W/K], Lateral_Src =
      --  sum_j g_ij*T_j [W/m^2]. Both are IN parameters because they change
      --  the solved root, and neither has an Ada default here: the C ABI
      --  has no concept of one, so an un-updated caller would be caught by
      --  the Pre below (Lateral_G >= 0) rather than silently solved as a
      --  1-D problem.
      Lateral_G     : Interfaces.C.Double;
      Lateral_Src   : Interfaces.C.Double;
      Status        : out Interfaces.C.int;
      Q_SG          : out Interfaces.C.Double;
      T_Surface     : out Interfaces.C.Double;
      T_Back        : out Interfaces.C.Double;
      N_Iterations  : out Interfaces.C.int;
      Profile       : access TPS_Profile_Buffer)
   with Pre  => N_Layers >= 1
                and then N_Layers <= Interfaces.C.int (Max_TPS_Layers)
                and then Emissivity >= 1.0e-3 and then Emissivity <= 1.0
                and then T_Init >= 0.0 and then T_Init <= 3000.0
                and then T_Inf >= 0.0 and then T_Inf <= 3000.0
                and then Lateral_G >= 0.0
                and then Lateral_Src >= 0.0
                and then Lateral_Src <= 2.0e15
                and then Ply_Thickness /= null
                and then Ply_Thermal_K /= null
                and then Profile /= null,
        Post => Status in 0 .. 8;
   pragma Export (C, TPS_Conduction_C, "TPS_Conduction_C");

   -- -----------------------------------------------------------------
   --  Self-test coverage registry (STC)
   -- -----------------------------------------------------------------
   --  Each C-ABI wrapper below is exercised by a matching Test_<Name>
   --  procedure defined in stellarorion_ffi.adb (the same file that owns
   --  the wrapper bodies). These lines name the unit under test so an
   --  AUnit suite built from this package registers one case per wrapper.
   --  Registry: GNATCOLL.Register_Routine (Suite, "Estimate_Cd_C", Test_Estimate_Cd_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "HIAD_Cost_C", Test_HIAD_Cost_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "HIAD_Set_Refs_C", Test_HIAD_Set_Refs_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "HIAD_Cost_Components_C", Test_HIAD_Cost_Components_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Run_MoP_C", Test_Run_MoP_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Generate_CCD_Samples_C", Test_Generate_CCD_Samples_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Sutton_Graves_Heat_C", Test_Sutton_Graves_Heat_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Sutherland_Viscosity_C", Test_Sutherland_Viscosity_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Fay_Riddell_Heat_C", Test_Fay_Riddell_Heat_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Radiative_Eq_Temp_C", Test_Radiative_Eq_Temp_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Backface_Temperature_C", Test_Backface_Temperature_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Ballistic_Coefficient_C", Test_Ballistic_Coefficient_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Dynamic_Pressure_C", Test_Dynamic_Pressure_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Deceleration_G_Load_C", Test_Deceleration_G_Load_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Atmosphere_Temperature_C", Test_Atmosphere_Temperature_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Atmosphere_Density_C", Test_Atmosphere_Density_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Mean_Free_Path_Viscous_C", Test_Mean_Free_Path_Viscous_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "Speed_Of_Sound_C", Test_Speed_Of_Sound_C'Access);
   --  Registry: GNATCOLL.Register_Routine (Suite, "TPS_Conduction_C", Test_TPS_Conduction_C'Access);

end StellarOrion_FFI;
