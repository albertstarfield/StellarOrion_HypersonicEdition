# Parity protection: metadata/ada_pinn_wrapper.meta.json (RS+GC parity)
"""Python ctypes wrapper for Ada/SPARK PINN Trajectory Physics library.

All physics calculations (ISA atmosphere, Sutton-Graves heat flux, drag,
g-load, IRVE-3 trajectory) are performed in Ada/SPARK 2014.
Python calls these via ctypes; no Python logic performs physics.

AXIOMS:
  1. Ada library provides all aerothermodynamic calculations
  2. Python is a thin wrapper — no physics logic in Python
  3. ctypes FFI provides the interface between Python and Ada

CITATIONS:
  [1] NASA SP-7468 (1976) — ISA atmosphere
  [2] Sutton & Graves (1972), NASA TR R-376 — SG heat flux
  [3] NASA TP-2013-4012 — IRVE-3 flight data
  [4] Anderson (2006), Hypersonic Gas Dynamics

Author: Albert Starfield Wahyu Suryo Samudro
"""

import ctypes
import os

_LIB_NAME = "libstellarorion_pinn.dylib"
_LIB_SEARCH = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", _LIB_NAME),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", _LIB_NAME),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", _LIB_NAME),
]

_ada_lib = None
for _p in _LIB_SEARCH:
    _p = os.path.normpath(_p)
    if os.path.exists(_p):
        _ada_lib = ctypes.CDLL(_p)
        break

if _ada_lib is None:
    raise OSError(f"Ada PINN library '{_LIB_NAME}' not found.")


class ISA_Result(ctypes.Structure):
    _fields_ = [
        ("temperature_K", ctypes.c_float),
        ("pressure_Pa", ctypes.c_float),
        ("density_kgm3", ctypes.c_float),
        ("speed_of_sound_ms", ctypes.c_float),
        ("dynamic_viscosity_pas", ctypes.c_float),
    ]


class Trajectory_Result(ctypes.Structure):
    _fields_ = [
        ("altitude_km", ctypes.c_float),
        ("velocity_ms", ctypes.c_float),
        ("mach_number", ctypes.c_float),
        ("density_kgm3", ctypes.c_float),
        ("heat_flux_wm2", ctypes.c_float),
        ("drag_force_n", ctypes.c_float),
        ("g_load_value", ctypes.c_float),
        ("dynamic_pressure_pa", ctypes.c_float),
    ]


_ada_lib.stellarorion_pinn_trajectory__isa_atmosphere.restype = ISA_Result
_ada_lib.stellarorion_pinn_trajectory__isa_atmosphere.argtypes = [ctypes.c_float]

_ada_lib.stellarorion_pinn_trajectory__sutton_graves_heat_flux.restype = ctypes.c_float
_ada_lib.stellarorion_pinn_trajectory__sutton_graves_heat_flux.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]

_ada_lib.stellarorion_pinn_trajectory__dynamic_pressure.restype = ctypes.c_float
_ada_lib.stellarorion_pinn_trajectory__dynamic_pressure.argtypes = [ctypes.c_float, ctypes.c_float]

_ada_lib.stellarorion_pinn_trajectory__drag_force.restype = ctypes.c_float
_ada_lib.stellarorion_pinn_trajectory__drag_force.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]

_ada_lib.stellarorion_pinn_trajectory__g_load.restype = ctypes.c_float
_ada_lib.stellarorion_pinn_trajectory__g_load.argtypes = [ctypes.c_float, ctypes.c_float]

_ada_lib.stellarorion_pinn_trajectory__irve3_trajectory.restype = Trajectory_Result
_ada_lib.stellarorion_pinn_trajectory__irve3_trajectory.argtypes = [ctypes.c_float] * 8


def isa_atmosphere(altitude_km):
    r = _ada_lib.stellarorion_pinn_trajectory__isa_atmosphere(ctypes.c_float(altitude_km))
    return {
        "altitude_km": altitude_km,
        "temperature_K": r.temperature_K,
        "pressure_Pa": r.pressure_Pa,
        "density_kgm3": r.density_kgm3,
        "speed_of_sound_ms": r.speed_of_sound_ms,
        "dynamic_viscosity_pas": r.dynamic_viscosity_pas,
    }


def sutton_graves_heat_flux(altitude_km, velocity_ms, rn=None):
    atm = isa_atmosphere(altitude_km)
    if rn is None:
        rn = 1.5
    wm2 = _ada_lib.stellarorion_pinn_trajectory__sutton_graves_heat_flux(
        ctypes.c_float(atm["density_kgm3"]),
        ctypes.c_float(rn),
        ctypes.c_float(velocity_ms),
    )
    return {"heat_flux_Wm2": wm2, "heat_flux_Wcm2": wm2 / 10000.0,
            "density_kgm3": atm["density_kgm3"], "velocity_ms": velocity_ms}


def dynamic_pressure(density_kgm3, velocity_ms):
    """Compute dynamic pressure via Ada/SPARK FFI: q = 0.5 * rho * V^2.
    [Citation: Anderson (2006), Fundamentals of Aerodynamics]
    [Citation: Ada/SPARK Dynamic_Pressure in stellarorion_pinn_trajectory.ads]
    """
    return _ada_lib.stellarorion_pinn_trajectory__dynamic_pressure(
        ctypes.c_float(density_kgm3), ctypes.c_float(velocity_ms),
    )


def drag_force(density_kgm3, velocity_ms, cd, diameter_m):
    """Compute drag force via Ada/SPARK FFI: F = 0.5 * Cd * A * rho * V^2.
    A = pi * (D/2)^2.
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    [Citation: Ada/SPARK Drag_Force in stellarorion_pinn_trajectory.ads]
    """
    return _ada_lib.stellarorion_pinn_trajectory__drag_force(
        ctypes.c_float(density_kgm3), ctypes.c_float(velocity_ms),
        ctypes.c_float(cd), ctypes.c_float(diameter_m),
    )


def g_load(drag_force_n, mass_kg):
    """Compute deceleration in Earth g's via Ada/SPARK FFI: n = F_drag / (m * g0).
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    [Citation: Ada/SPARK G_Load in stellarorion_pinn_trajectory.ads]
    """
    return _ada_lib.stellarorion_pinn_trajectory__g_load(
        ctypes.c_float(drag_force_n), ctypes.c_float(mass_kg),
    )


def irve3_trajectory_model(step, target_step=3.0e8, h_entry=120.0, h_final=40.0,
                           v_entry=4300.0, v_final=2700.0, h_dsmc=51.8, v_dsmc=3378.0):
    r = _ada_lib.stellarorion_pinn_trajectory__irve3_trajectory(
        ctypes.c_float(float(step)), ctypes.c_float(target_step),
        ctypes.c_float(h_entry), ctypes.c_float(h_final),
        ctypes.c_float(v_entry), ctypes.c_float(v_final),
        ctypes.c_float(h_dsmc), ctypes.c_float(v_dsmc),
    )
    return {
        "altitude_km": r.altitude_km, "velocity_ms": r.velocity_ms,
        "mach_number": r.mach_number, "density_kgm3": r.density_kgm3,
        "heat_flux_Wm2": r.heat_flux_wm2, "drag_force_N": r.drag_force_n,
        "g_load": r.g_load_value, "dynamic_pressure_Pa": r.dynamic_pressure_pa,
    }


# -----------------------------------------------------------------
#  Get_HIAD_Cross_Section FFI binding
# -----------------------------------------------------------------
#  AXIOM: All geometry math is in Ada/SPARK. Python calls via ctypes.
#  Ada procedure uses `out Array_Float_200` parameters passed by
#  reference (pointer to 200-element float arrays).
#
#  [Citation: Rapisarda (2023) Sec 3.7 — HIAD flat-skin profile]
#  [Citation: Ada 2012 RM §6.2 — out parameter passing]
# -----------------------------------------------------------------
_MAX_CROSS_SECTION_PTS = 200
_Float_Array_200 = ctypes.c_float * _MAX_CROSS_SECTION_PTS

_ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section.restype = None
_ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section.argtypes = [
    ctypes.POINTER(_Float_Array_200),   # X_Arr (axial coords, by reference)
    ctypes.POINTER(_Float_Array_200),   # Y_Arr (radial coords, by reference)
    ctypes.POINTER(ctypes.c_int),       # N_Pts (access Integer — pointer)
]

#  Parameterized variant: same ABI plus three leading geometry params.
#  Ada Float is 32-bit, so every scalar crosses as c_float (matches the
#  working trajectory-package binds above — c_double would corrupt args).
#  [Citation: Ada RM §3.5.7 — Float is a 32-bit floating point type]
_ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section_params.restype = None
_ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section_params.argtypes = [
    ctypes.c_float,                     # R_N (nose sphere radius [m])
    ctypes.c_float,                     # R_Torus (torus minor radius [m])
    ctypes.c_float,                     # Half_Cone_Deg (cone half-angle [deg])
    ctypes.POINTER(_Float_Array_200),   # X_Arr (axial coords, by reference)
    ctypes.POINTER(_Float_Array_200),   # Y_Arr (radial coords, by reference)
    ctypes.POINTER(ctypes.c_int),       # N_Pts (access Integer — pointer)
]


def get_hiad_cross_section():
    """Return the 4-segment HIAD flat-skin cross-section from Ada/SPARK.

    Returns dict with:
      x : list[float]  — axial coordinates (nose points +X)
      y : list[float]  — radial coordinates (half-width)
      n : int          — actual number of valid points

    All geometry math is computed in Ada/SPARK; Python is a thin wrapper.
    [Citation: Rapisarda (2023) Sec 3.7, Appendix C.1]
    [Citation: stellarorion_pinn_trajectory.ads — Get_HIAD_Cross_Section]
    """
    x_arr = _Float_Array_200()
    y_arr = _Float_Array_200()
    n_pts = ctypes.c_int(0)
    #  Ada out params: X_Arr/Y_Arr passed by reference, N_Pts passed by copy.
    #  We pass all via byref() to ensure correct pointer semantics.
    _ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section(
        ctypes.byref(x_arr), ctypes.byref(y_arr), ctypes.byref(n_pts),
    )
    n = n_pts.value
    return {
        "x": [x_arr[i] for i in range(n)],
        "y": [y_arr[i] for i in range(n)],
        "n": n,
    }


def get_hiad_cross_section_params(r_n, r_torus, half_cone_deg):
    """Return the 4-segment HIAD flat-skin cross-section for ARBITRARY
    geometry parameters via Ada/SPARK FFI.

    Parameters:
      r_n           -- nose sphere radius [m]         (must be > 0)
      r_torus       -- torus minor (tube) radius [m]  (must be > 0)
      half_cone_deg -- windward cone half-angle [deg] (0 < angle < 90)

    Returns dict with:
      x : list[float]  — axial coordinates (nose points +X)
      y : list[float]  — radial coordinates (half-width)
      n : int          — actual number of valid points

    GIGO contract: this wrapper fail-closes on non-physical inputs before
    crossing the FFI boundary (the Ada library runs with assertions
    disabled, so it performs no runtime range checks itself).

    All geometry math is computed in Ada/SPARK (single source of truth);
    Python is a thin wrapper — used by render_optimization_comparison.py
    to draw the Bayesian-optimized profile.
    [Citation: Rapisarda (2023) Sec 3.7, Appendix C.1]
    [Citation: stellarorion_pinn_trajectory.ads — Get_HIAD_Cross_Section_Params]
    """
    if r_n <= 0.0:
        raise ValueError(f"r_n must be > 0 m, got {r_n!r}")
    if r_torus <= 0.0:
        raise ValueError(f"r_torus must be > 0 m, got {r_torus!r}")
    if not 0.0 < half_cone_deg < 90.0:
        raise ValueError(
            f"half_cone_deg must be in (0, 90) deg, got {half_cone_deg!r}",
        )
    x_arr = _Float_Array_200()
    y_arr = _Float_Array_200()
    n_pts = ctypes.c_int(0)
    #  Ada out params: X_Arr/Y_Arr passed by reference, N_Pts passed by
    #  copy of the access value — same pointer semantics as the default
    #  binding above.
    _ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section_params(
        ctypes.c_float(r_n), ctypes.c_float(r_torus),
        ctypes.c_float(half_cone_deg),
        ctypes.byref(x_arr), ctypes.byref(y_arr), ctypes.byref(n_pts),
    )
    n = n_pts.value
    return {
        "x": [x_arr[i] for i in range(n)],
        "y": [y_arr[i] for i in range(n)],
        "n": n,
    }


# -----------------------------------------------------------------
#  Compute_Frame_Data FFI binding (from stellarorion_trajectory_output)
# -----------------------------------------------------------------
#  AXIOM: All trajectory/physics math is in Ada/SPARK. Python calls via ctypes.
#  Ada function returns a Frame_Data record (17 Float fields).
#
#  [Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
#  [Citation: Ada 2012 RM §6.2 — record type FFI passing]
# -----------------------------------------------------------------


class Frame_Data(ctypes.Structure):
    """ctypes mirror of Ada Frame_Data record (17 Float fields).

    [Citation: stellarorion_trajectory_output.ads — Frame_Data type]
    """
    _fields_ = [
        ("step", ctypes.c_float),
        ("altitude_km", ctypes.c_float),
        ("velocity_ms", ctypes.c_float),
        ("mach_number", ctypes.c_float),
        ("heat_flux_wcm2", ctypes.c_float),
        ("drag_force_n", ctypes.c_float),
        ("g_load", ctypes.c_float),
        ("dynamic_pressure_pa", ctypes.c_float),
        ("density_kgm3", ctypes.c_float),
        ("temperature_k", ctypes.c_float),
        ("pressure_pa", ctypes.c_float),
        ("pinn_loss", ctypes.c_float),
        ("pinn_accuracy", ctypes.c_float),
        ("dsmc_pinn_error", ctypes.c_float),
        ("knudsen_number", ctypes.c_float),
        ("ballistic_coeff_kgm2", ctypes.c_float),
        ("stagnation_pressure_pa", ctypes.c_float),
    ]


class Trajectory_Point(ctypes.Structure):
    """ctypes mirror of Ada Trajectory_Point record (4 Float fields).

    [Citation: stellarorion_trajectory_output.ads — Trajectory_Point type]
    """
    _fields_ = [
        ("step", ctypes.c_float),
        ("altitude_km", ctypes.c_float),
        ("velocity_ms", ctypes.c_float),
        ("mach_number", ctypes.c_float),
    ]


# Bind Ada Compute_Frame_Data(Step : Float) return Frame_Data
_ada_lib.stellarorion_trajectory_output__compute_frame_data.restype = Frame_Data
_ada_lib.stellarorion_trajectory_output__compute_frame_data.argtypes = [ctypes.c_float]

# Bind Ada Compute_Trajectory_Point(Step : Float) return Trajectory_Point
_ada_lib.stellarorion_trajectory_output__compute_trajectory_point.restype = Trajectory_Point
_ada_lib.stellarorion_trajectory_output__compute_trajectory_point.argtypes = [ctypes.c_float]


def compute_frame_data(step):
    """Compute all trajectory + physics + PINN metrics via Ada/SPARK FFI.

    Returns dict with altitude, velocity, mach, heat_flux, drag, g_load,
    plus PINN training loss, accuracy, and convergence metrics.
    All physics in Ada -- Python is wrapper only.

    [Citation: stellarorion_trajectory_output.ads — Compute_Frame_Data]
    [Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
    [Citation: Sutton & Graves (1972), NASA TR R-376]
    """
    r = _ada_lib.stellarorion_trajectory_output__compute_frame_data(ctypes.c_float(float(step)))
    return {
        "step": r.step,
        "altitude_km": r.altitude_km,
        "velocity_ms": r.velocity_ms,
        "mach_number": r.mach_number,
        "heat_flux_wcm2": r.heat_flux_wcm2,
        "drag_sum_N": r.drag_force_n,
        "g_load": r.g_load,
        "dynamic_pressure_Pa": r.dynamic_pressure_pa,
        "density_kgm3": r.density_kgm3,
        "temperature_K": r.temperature_k,
        "pressure_Pa": r.pressure_pa,
        "pinn_loss": r.pinn_loss,
        "pinn_accuracy": r.pinn_accuracy,
        "dsmc_pinn_error": r.dsmc_pinn_error,
        "knudsen_number": r.knudsen_number,
        "ballistic_coeff_kgm2": r.ballistic_coeff_kgm2,
        "stagnation_pressure_Pa": r.stagnation_pressure_pa,
    }


def compute_trajectory_point(step):
    """Compute trajectory-only data via Ada/SPARK FFI (lightweight).

    Returns dict with altitude, velocity, mach number only.

    [Citation: stellarorion_trajectory_output.ads — Compute_Trajectory_Point]
    [Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
    """
    r = _ada_lib.stellarorion_trajectory_output__compute_trajectory_point(ctypes.c_float(float(step)))
    return {
        "step": r.step,
        "altitude_km": r.altitude_km,
        "velocity_ms": r.velocity_ms,
        "mach_number": r.mach_number,
    }


# ──────────────────────────────────────────────────────────────────────
#  Optimization FFI bindings (from stellarorion_ffi)
# ──────────────────────────────────────────────────────────────────────

# Bind Ada Estimate_Cd_C(R_N, R_Tor, Half_Cone_Deg) return C.Double
_ada_lib.Estimate_Cd_C.restype = ctypes.c_double
_ada_lib.Estimate_Cd_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double]

# Bind Ada HIAD_Cost_C(X1, X2, X3) return C.Double
_ada_lib.HIAD_Cost_C.restype = ctypes.c_double
_ada_lib.HIAD_Cost_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double]

# Bind Ada HIAD_Set_Refs_C(Q_Target, Flux_Ref, Tau_Sec, Cd_Ref) -> int.
# Returns 0 = refs updated, 1 = Ada-side failure (previous refs kept).
# Loads the DYNAMIC validation base reference used by J(x) — values come
# from unified_comparison_data.json via hiad_optimizer._load_validation_refs.
# [Citation: stellarorion_ffi.ads — HIAD_Set_Refs_C]
_ada_lib.HIAD_Set_Refs_C.restype = ctypes.c_int
_ada_lib.HIAD_Set_Refs_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]

# Bind Ada HIAD_Cost_Components_C(X1, X2, X3, Out x7) procedure.
# Seven caller-allocated c_double write-backs (ffi.adb axiom block).
# [Citation: stellarorion_ffi.ads — HIAD_Cost_Components_C]
_ada_lib.HIAD_Cost_Components_C.restype = None
_ada_lib.HIAD_Cost_Components_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double,
    ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double)]


def estimate_cd(r_n: float, r_tor: float, half_cone_deg: float) -> float:
    """Estimate drag coefficient via Ada/SPARK FFI.

    Computes Cd for a HIAD geometry using blunt-body correlation.

    Parameters:
        r_n           -- nose sphere radius [m]
        r_tor         -- torus minor (tube) radius [m]
        half_cone_deg -- half-cone angle [degrees]

    Returns:
        Drag coefficient Cd (positive float)

    [Citation: stellarorion_ffi.ads — Estimate_Cd_C]
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    """
    return _ada_lib.Estimate_Cd_C(
        ctypes.c_double(r_n), ctypes.c_double(r_tor),
        ctypes.c_double(half_cone_deg))


def hiad_cost_function(x1: float, x2: float, x3: float) -> float:
    """Compute the multi-objective HIAD cost J(x) via Ada/SPARK FFI.

    J(x) = W_Heat_Load * Q(x)/Q_target        (primary: lowest Total Heat Load)
         + W_Flux      * q(x)/q_ref           (peak heat flux)
         + W_Beta      * (beta(x)/beta_ref - 1)^2   (ballistic coefficient)
         + W_Cd        * Cd(x)/Cd_ref         (drag coefficient)
         + Lambda_Pen  * [envelope + TPS + payload-size penalties]

    Q(x) = q_SG(x) * tau is the Sutton-Graves heat flux at the validated
    snapshot (h=51.8 km, V=3378 m/s) integrated over the validation-derived
    heating time.  ALL reference values (Q_target, q_ref, tau, Cd_ref) are
    loaded DYNAMICALLY from unified_comparison_data.json via
    set_validation_refs() — call that before the first evaluation.

    Parameters:
        x1 -- nose radius R_N [m]
        x2 -- torus radius r_tor [m]
        x3 -- half-cone angle [degrees]

    Returns:
        Cost value J(x) >= 0.0

    Raises:
        RuntimeError -- Ada returned the negative sentinel (only possible
            on an internal fault; J(x) >= 0.0 by contract).  Raised so a
            poisoned value can never win a minimisation silently.

    [Citation: stellarorion_ffi.ads — HIAD_Cost_C / HIAD_Cost_Function]
    [Citation: Nocedal & Wright (2006), Sec 3.1 weighted sums, Sec 17.1 penalties]
    [Citation: unified_comparison_data.json — dynamic reference values]
    """
    cost = float(_ada_lib.HIAD_Cost_C(
        ctypes.c_double(x1), ctypes.c_double(x2), ctypes.c_double(x3)))
    # Safety guard: the Ada side returns -1.0 sentinel on internal fault
    # (ffi.adb HIAD_Cost_C).  J(x) >= 0.0 always, so a negative value is
    # corruption — fail loudly instead of letting BO minimise on it.
    if cost < 0.0:
        raise RuntimeError(
            f"hiad_cost_function: negative sentinel {cost!r} for "
            f"X=({x1}, {x2}, {x3}) — Ada reported an internal fault "
            f"(check [VERBOSE_ERROR] output above)"
        )
    return cost


def set_validation_refs(
    q_target_jcm2: float,
    flux_ref_wcm2: float,
    tau_sec: float,
    cd_ref: float,
) -> None:
    """Load the dynamic validation base reference used by J(x) (FFI).

    Parameters:
        q_target_jcm2 -- Total Heat Load objective target [J/cm^2]
        flux_ref_wcm2 -- reference peak heat flux [W/cm^2]
        tau_sec       -- effective heating duration [s]
        cd_ref        -- reference drag coefficient

    Raises:
        ValueError  -- any input <= 0 (mirror of the Ada Pre condition;
            fails HERE rather than inside Ada so the caller gets a
            Python-level traceback with the bad value).
        RuntimeError -- Ada refused the update (previous refs kept; the
            Ada side logged [VERBOSE_ERROR] with full context).

    All values must come from _load_validation_refs() in hiad_optimizer.py
    (read from unified_comparison_data.json at run time).

    [Citation: stellarorion_ffi.ads — HIAD_Set_Refs_C]
    [Citation: stellarorion_optimization.ads — Set_Validation_Refs]
    """
    for name, val in (
        ("q_target_jcm2", q_target_jcm2),
        ("flux_ref_wcm2", flux_ref_wcm2),
        ("tau_sec", tau_sec),
        ("cd_ref", cd_ref),
    ):
        # Chained comparison also rejects NaN (all comparisons with NaN
        # are False -> `not False` fires) and +inf — mirrors the Ada
        # Pre (must be > 0) plus a finiteness requirement.
        if not (0.0 < val < float("inf")):
            raise ValueError(
                f"set_validation_refs: {name}={val!r} must be a "
                f"positive finite number (got <= 0, inf, or NaN)"
            )
    # Narrowing guard: module loader already raises OSError if the dylib
    # is missing; this keeps pyrefly's flow analysis happy AND fails loud
    # if the global were ever reset (Murphy's Law).
    if _ada_lib is None:
        raise RuntimeError("ada_pinn_wrapper: _ada_lib is None (library not loaded)")
    rc = int(_ada_lib.HIAD_Set_Refs_C(
        ctypes.c_double(q_target_jcm2), ctypes.c_double(flux_ref_wcm2),
        ctypes.c_double(tau_sec), ctypes.c_double(cd_ref)))
    # rc != 0: the Ada side refused the update (it logged a literal-only
    # line; dylib contexts cannot build exception strings — secondary
    # stack unavailable — so THIS wrapper is where full context lives).
    if rc != 0:
        raise RuntimeError(
            f"set_validation_refs: Ada rejected the update (rc={rc}); "
            f"previous validation refs kept. Values not applied: "
            f"q_target={q_target_jcm2!r}, flux_ref={flux_ref_wcm2!r}, "
            f"tau={tau_sec!r}, cd_ref={cd_ref!r}"
        )


def hiad_cost_components(x1: float, x2: float, x3: float) -> dict[str, float]:
    """Return the full J(x) term breakdown via Ada/SPARK FFI.

    Parameters:
        x1, x2, x3 -- [R_N (m), r_tor (m), half_cone_deg]

    Returns:
        dict with keys (all float):
            heat_load_ratio -- Q(x)/Q_target (primary term)
            flux_ratio      -- q(x)/q_ref
            beta_dev        -- (beta(x)/beta_ref - 1)^2
            cd_ratio        -- Cd(x)/Cd_ref
            penalty         -- envelope + TPS + payload penalties
            total           -- J(x); equals hiad_cost_function(x1,x2,x3)
            heat_load_jcm2  -- absolute predicted Total Heat Load [J/cm^2]

    Raises:
        RuntimeError -- Ada returned the negative sentinel (internal fault).

    [Citation: stellarorion_ffi.ads — HIAD_Cost_Components_C]
    [Citation: stellarorion_optimization.ads — Cost_Components record]
    """
    outs = [ctypes.c_double(0.0) for _ in range(7)]
    # Narrowing guard (same as set_validation_refs): keeps pyrefly's flow
    # analysis happy and fails loud if the dylib global were ever reset.
    if _ada_lib is None:
        raise RuntimeError("ada_pinn_wrapper: _ada_lib is None (library not loaded)")
    _ada_lib.HIAD_Cost_Components_C(
        ctypes.c_double(x1), ctypes.c_double(x2), ctypes.c_double(x3),
        ctypes.byref(outs[0]), ctypes.byref(outs[1]),
        ctypes.byref(outs[2]), ctypes.byref(outs[3]),
        ctypes.byref(outs[4]), ctypes.byref(outs[5]),
        ctypes.byref(outs[6]),
    )
    total = float(outs[5].value)
    # Same sentinel contract as hiad_cost_function (ffi.adb axiom block).
    if total < 0.0:
        raise RuntimeError(
            f"hiad_cost_components: negative sentinel {total!r} for "
            f"X=({x1}, {x2}, {x3}) — Ada reported an internal fault "
            f"(check [VERBOSE_ERROR] output above)"
        )
    return {
        "heat_load_ratio": float(outs[0].value),
        "flux_ratio": float(outs[1].value),
        "beta_dev": float(outs[2].value),
        "cd_ratio": float(outs[3].value),
        "penalty": float(outs[4].value),
        "total": total,
        "heat_load_jcm2": float(outs[6].value),
    }


# ---------------------------------------------------------------------------
#  Run_MoP_C — Method of Projected Gradients via Ada FFI
# ---------------------------------------------------------------------------

# CCD_Samples = 15 (8 factorial + 1 center + 6 axial) per stellarorion_ffi.ads
_CCD_COUNT = 15
_LABEL_STRIDE = 31  # 30 chars + NUL per label


def _bind_mop_and_ccd():
    """Bind Run_MoP_C and Generate_CCD_Samples_C symbols from the Ada dylib.

    -- AXIOMS: All output parameters are pre-allocated by the caller.
    -- CITATION: stellarorion_ffi.ads lines 96-197.
    """
    # Run_MoP_C: procedure with output pointers
    _ada_lib.Run_MoP_C.restype = None
    _ada_lib.Run_MoP_C.argtypes = [
        ctypes.c_double,   # Learning_Rate
        ctypes.c_double,   # Tolerance
        ctypes.c_double,   # Lambda_1
        ctypes.c_double,   # Lambda_2
        ctypes.c_int,      # Max_Iter
        ctypes.c_double,   # X1 (initial guess)
        ctypes.c_double,   # X2
        ctypes.c_double,   # X3
        ctypes.POINTER(ctypes.c_double),  # Out_X1
        ctypes.POINTER(ctypes.c_double),  # Out_X2
        ctypes.POINTER(ctypes.c_double),  # Out_X3
        ctypes.POINTER(ctypes.c_double),  # Out_Cost
        ctypes.POINTER(ctypes.c_int),     # Out_Converged
        ctypes.POINTER(ctypes.c_int),     # Out_N_Iter
    ]

    # Generate_CCD_Samples_C: procedure filling output arrays
    ccd_double_arr = ctypes.c_double * _CCD_COUNT
    ccd_label_buf = ctypes.c_char * (_CCD_COUNT * _LABEL_STRIDE)
    _ada_lib.Generate_CCD_Samples_C.restype = None
    _ada_lib.Generate_CCD_Samples_C.argtypes = [
        ctypes.POINTER(ccd_double_arr),  # Out_R_N
        ctypes.POINTER(ccd_double_arr),  # Out_R_Tor
        ctypes.POINTER(ccd_double_arr),  # Out_Angles
        ctypes.POINTER(ccd_label_buf),   # Out_Labels
    ]


try:
    _bind_mop_and_ccd()
except (OSError, AttributeError):
    pass  # FFI symbols unavailable — fallback will raise at call time


def run_mop_optimize(
    x0: tuple,
    lr: float = 0.01,
    tol: float = 1e-6,
    lambda_1: float = 100.0,
    lambda_2: float = 100.0,
    max_iter: int = 100,
) -> dict:
    """Run Method of Projected Gradients via Ada FFI.

    Parameters:
        x0      -- initial guess (R_N, r_tor, half_cone_deg)
        lr      -- learning rate (step size)
        tol     -- convergence tolerance (||grad||_inf)
        lambda_1 -- penalty weight for max_radius constraint
        lambda_2 -- penalty weight for nose_radius constraint
        max_iter -- maximum iterations

    Returns:
        dict with keys: x_opt (tuple), cost, converged, n_iter

    [Citation: stellarorion_ffi.ads — Run_MoP_C]
    [Citation: Boyd & Vandenberghe (2004), Convex Optimization, Sec 2.3]
    """
    out_x1 = ctypes.c_double()
    out_x2 = ctypes.c_double()
    out_x3 = ctypes.c_double()
    out_cost = ctypes.c_double()
    out_converged = ctypes.c_int()
    out_n_iter = ctypes.c_int()

    _ada_lib.Run_MoP_C(
        ctypes.c_double(lr),
        ctypes.c_double(tol),
        ctypes.c_double(lambda_1),
        ctypes.c_double(lambda_2),
        ctypes.c_int(max_iter),
        ctypes.c_double(x0[0]),
        ctypes.c_double(x0[1]),
        ctypes.c_double(x0[2]),
        ctypes.byref(out_x1),
        ctypes.byref(out_x2),
        ctypes.byref(out_x3),
        ctypes.byref(out_cost),
        ctypes.byref(out_converged),
        ctypes.byref(out_n_iter),
    )

    return {
        "x_opt": (out_x1.value, out_x2.value, out_x3.value),
        "cost": out_cost.value,
        "converged": out_converged.value == 1,
        "n_iter": out_n_iter.value,
    }


# ---------------------------------------------------------------------------
#  Bayesian Optimization — Global optimization via GP surrogate
# ---------------------------------------------------------------------------

# [Citation: Mockus (1978), "Bayesian Approach to Global Optimization"]
# [Citation: Jones et al. (1998), "Efficient Global Optimization of Expensive
#  Black-Box Functions", J. Global Optimization 13, 455-492]
# [Citation: Scikit-learn: https://scikit-learn.org/stable/modules/gaussian_process.html]

# Parameter bounds for HIAD geometry optimization
# [Citation: stellarorion_optimization.ads — Constraints]
# R_N: nose sphere radius (m), r_tor: torus minor radius (m),
# half_cone_deg: half-cone angle (degrees)
_BOUNDS = [
    (0.5, 3.0),    # R_N — nose radius: 0.5m to 3.0m
    (0.05, 0.5),   # r_tor — torus radius: 0.05m to 0.5m
    (40.0, 80.0),  # half_cone_deg — half-cone angle: 40° to 80°
]


def _latin_hypercube_sample(n_samples, bounds, seed=None):
    """Generate Latin Hypercube Design of Experiments.

    Parameters:
        n_samples -- number of sample points
        bounds    -- list of (min, max) tuples for each dimension
        seed      -- random seed for reproducibility

    Returns:
        numpy array of shape (n_samples, n_dims)

    [Citation: McKay et al. (1979), "A Comparison of Three Methods for
     Selecting Values of Input Variables in the Analysis of Output from
     a Computer Code", Technometrics 21(2), 239-245]
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    n_dims = len(bounds)
    samples = np.zeros((n_samples, n_dims))
    for j in range(n_dims):
        perm = rng.permutation(n_samples)
        for i in range(n_samples):
            samples[i, j] = (perm[i] + rng.random()) / n_samples
    # Scale to bounds
    for j, (lo, hi) in enumerate(bounds):
        samples[:, j] = lo + samples[:, j] * (hi - lo)
    return samples


def _expected_improvement(X_candidate, gp, y_best, xi=0.01):
    """Compute Expected Improvement acquisition function.

    EI(x) = E[max(0, f_best - f(x) - xi)]
          = (f_best - mu(x) - xi) * Phi(Z) + sigma(x) * phi(Z)
    where Z = (f_best - mu(x) - xi) / sigma(x)

    Parameters:
        X_candidate -- candidate points (n, d)
        gp          -- fitted GaussianProcessRegressor
        y_best      -- best observed cost value (minimum)
        xi          -- exploration-exploitation tradeoff (default 0.01)

    Returns:
        EI values (n,)

    [Citation: Jones et al. (1998), Eq. (2)]
    [Citation: https://scikit-learn.org/stable/modules/gaussian_process.html]
    """
    from scipy.stats import norm
    import numpy as np
    mu, sigma = gp.predict(X_candidate, return_std=True)
    sigma = np.maximum(sigma, 1e-9)
    Z = (y_best - mu - xi) / sigma
    ei = (y_best - mu - xi) * norm.cdf(Z) + sigma * norm.pdf(Z)
    return ei


def run_bayesian_optimize(
    cost_fn,
    n_initial: int = 20,
    n_iter: int = 50,
    xi: float = 0.01,
    seed: int = 42,
) -> dict:
    """Run Bayesian Optimization for HIAD geometry parameters.

    Uses Gaussian Process surrogate with Expected Improvement acquisition
    to find global optimum of the cost function.

    Parameters:
        cost_fn   -- callable(R_N, r_tor, half_cone_deg) -> float
        n_initial -- initial Latin Hypercube sample count (default 20)
        n_iter    -- BO iterations after initial sampling (default 50)
        xi        -- exploration-exploitation tradeoff (default 0.01)
        seed      -- random seed for reproducibility

    Returns:
        dict with keys: x_opt (tuple), cost, n_evals, history (list of dicts)

    [Citation: Mockus (1978), Bayesian Approach to Global Optimization]
    [Citation: Jones et al. (1998), Efficient Global Optimization]
    """
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, ConstantKernel
    import numpy as np

    bounds = _BOUNDS
    n_dims = len(bounds)

    # --- Step 1: Latin Hypercube initial sampling ---
    X_init = _latin_hypercube_sample(n_initial, bounds, seed=seed)
    y_init = np.array([cost_fn(float(x[0]), float(x[1]), float(x[2]))
                       for x in X_init])

    X_obs = list(X_init)
    y_obs = list(y_init)
    history = []
    for i, (x, y) in enumerate(zip(X_init, y_init)):
        history.append({
            "iteration": i,
            "R_N": float(x[0]),
            "r_tor": float(x[1]),
            "half_cone_deg": float(x[2]),
            "cost": float(y),
            "type": "initial",
        })

    y_best = float(min(y_obs))

    # --- Step 2: Bayesian Optimization loop ---
    for i in range(n_iter):
        X_arr = np.array(X_obs)
        y_arr = np.array(y_obs)

        # Fit GP surrogate
        kernel = (ConstantKernel(1.0, constant_value_bounds=(1e-3, 1e3))
                  * Matern(length_scale=[1.0]*n_dims,
                           length_scale_bounds=[(1e-3, 1e3)]*n_dims,
                           nu=2.5))
        gp = GaussianProcessRegressor(
            kernel=kernel, n_restarts_optimizer=5, normalize_y=True,
            alpha=1e-6,
        )
        gp.fit(X_arr, y_arr)

        # Generate candidates via random search in bounds
        n_candidates = 5000
        X_cand = np.zeros((n_candidates, n_dims))
        rng = np.random.default_rng(seed + i)
        for j, (lo, hi) in enumerate(bounds):
            X_cand[:, j] = rng.uniform(lo, hi, n_candidates)

        # Compute Expected Improvement
        ei = _expected_improvement(X_cand, gp, y_best, xi=xi)
        best_idx = int(np.argmax(ei))

        # Evaluate cost at best candidate
        x_new = X_cand[best_idx]
        y_new = cost_fn(float(x_new[0]), float(x_new[1]), float(x_new[2]))

        X_obs.append(x_new)
        y_obs.append(y_new)

        if y_new < y_best:
            y_best = y_new

        history.append({
            "iteration": n_initial + i,
            "R_N": float(x_new[0]),
            "r_tor": float(x_new[1]),
            "half_cone_deg": float(x_new[2]),
            "cost": float(y_new),
            "type": "bo",
            "ei_max": float(ei[best_idx]),
        })

    # --- Step 3: Return best result ---
    best_idx = int(np.argmin(y_obs))
    x_opt = X_obs[best_idx]
    y_opt = y_obs[best_idx]

    return {
        "x_opt": (float(x_opt[0]), float(x_opt[1]), float(x_opt[2])),
        "cost": float(y_opt),
        "n_evals": len(X_obs),
        "history": history,
    }


def generate_ccd_samples() -> list:
    """Generate CCD samples via Ada FFI.

    Returns:
        List of 15 dicts with keys: R_N, r_tor, half_cone_deg, label

    [Citation: stellarorion_ffi.ads — Generate_CCD_Samples_C]
    [Citation: Montgomery (2017), Design and Analysis of Experiments]
    """
    ccd_double_arr = ctypes.c_double * _CCD_COUNT
    ccd_label_buf = ctypes.c_char * (_CCD_COUNT * _LABEL_STRIDE)

    out_rn = ccd_double_arr()
    out_rtor = ccd_double_arr()
    out_angles = ccd_double_arr()
    out_labels = ccd_label_buf()

    _ada_lib.Generate_CCD_Samples_C(
        ctypes.byref(out_rn),
        ctypes.byref(out_rtor),
        ctypes.byref(out_angles),
        ctypes.byref(out_labels),
    )

    samples = []
    for i in range(_CCD_COUNT):
        raw_label = out_labels[i * _LABEL_STRIDE:(i + 1) * _LABEL_STRIDE]
        label = raw_label.split(b'\x00')[0].decode('ascii').strip()
        samples.append({
            "R_N": out_rn[i],
            "r_tor": out_rtor[i],
            "half_cone_deg": out_angles[i],
            "label": label,
        })
    return samples


if __name__ == "__main__":
    print("=== Ada/SPARK PINN Trajectory Wrapper Self-Test ===")
    atm = isa_atmosphere(40.0)
    print(f"ISA at 40 km: T={atm['temperature_K']:.1f}K, rho={atm['density_kgm3']:.4e}kg/m3")
    sg = sutton_graves_heat_flux(51.8, 3378.0)
    print(f"SG at 51.8km: {sg['heat_flux_Wcm2']:.3f} W/cm2 (expected ~25.4)")
    sg40 = sutton_graves_heat_flux(40.0, 2700.0)
    print(f"SG at 40km: {sg40['heat_flux_Wcm2']:.3f} W/cm2 (expected ~14.5)")
    t2200 = irve3_trajectory_model(2200)
    print(f"Step 2200: alt={t2200['altitude_km']:.1f}km, g={t2200['g_load']:.2f}")
    t300 = irve3_trajectory_model(300000000)
    print(f"Step 300M: alt={t300['altitude_km']:.1f}km, g={t300['g_load']:.2f}")

    # --- HIAD Cross-Section self-test ---
    print("\n--- HIAD Cross-Section Test ---")
    cs = get_hiad_cross_section()
    print(f"Points returned: {cs['n']} (expected 56 = 4 segments * 15 pts - 3 overlap)")
    print(f"X range: [{min(cs['x']):.4f}, {max(cs['x']):.4f}] m")
    print(f"Y range: [{min(cs['y']):.4f}, {max(cs['y']):.4f}] m")
    print(f"Nose tip (first pt): X={cs['x'][0]:.4f}, Y={cs['y'][0]:.4f}")
    print(f"Back plane (last pt): X={cs['x'][-1]:.4f}, Y={cs['y'][-1]:.4f}")
    # Verify max radial extent - IRVE-3 with 6 tori extends beyond nose radius
    max_r = max(cs['y'])
    print(f"Max radial extent: {max_r:.4f} m (IRVE-3 nose=1.5m, toroid extends to ~2.65m)")
    # For IRVE-3 with 6 tori, max radius is around 2.65m (nose + toroid wrap)
    if cs['n'] > 0 and 2.5 < max_r < 2.7:
        print("PASS: Cross-section geometry matches IRVE-3 toroid parameters")
    else:
        print("WARN: Cross-section geometry outside expected range (2.5-2.7m)")
    print("\nSelf-test complete.")


# ──────────────────────────────────────────────────────────────────────
#  Post-Processing FFI bindings (from stellarorion_ffi)
# ──────────────────────────────────────────────────────────────────────

# [Citation: stellarorion_ffi.ads — Sutton_Graves_Heat_C]
_ada_lib.Sutton_Graves_Heat_C.restype = ctypes.c_double
_ada_lib.Sutton_Graves_Heat_C.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Sutherland_Viscosity_C]
_ada_lib.Sutherland_Viscosity_C.restype = ctypes.c_double
_ada_lib.Sutherland_Viscosity_C.argtypes = [ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Fay_Riddell_Heat_C]
_ada_lib.Fay_Riddell_Heat_C.restype = ctypes.c_double
_ada_lib.Fay_Riddell_Heat_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double,
    ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Radiative_Eq_Temp_C]
_ada_lib.Radiative_Eq_Temp_C.restype = ctypes.c_double
_ada_lib.Radiative_Eq_Temp_C.argtypes = [ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Backface_Temperature_C]
_ada_lib.Backface_Temperature_C.restype = ctypes.c_double
_ada_lib.Backface_Temperature_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double,
    ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Ballistic_Coefficient_C]
_ada_lib.Ballistic_Coefficient_C.restype = ctypes.c_double
_ada_lib.Ballistic_Coefficient_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Dynamic_Pressure_C]
_ada_lib.Dynamic_Pressure_C.restype = ctypes.c_double
_ada_lib.Dynamic_Pressure_C.argtypes = [ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Deceleration_G_Load_C]
_ada_lib.Deceleration_G_Load_C.restype = ctypes.c_double
_ada_lib.Deceleration_G_Load_C.argtypes = [ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Atmosphere_Temperature_C]
_ada_lib.Atmosphere_Temperature_C.restype = ctypes.c_double
_ada_lib.Atmosphere_Temperature_C.argtypes = [ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Atmosphere_Density_C]
_ada_lib.Atmosphere_Density_C.restype = ctypes.c_double
_ada_lib.Atmosphere_Density_C.argtypes = [ctypes.c_double]


def radiative_eq_temp(heat_flux_wm2: float, emissivity: float) -> float:
    """Radiative equilibrium surface temperature via Ada/SPARK FFI.
    T = (q / (sigma * epsilon))^(1/4)
    [Citation: Stefan-Boltzmann law; stellarorion_physics.ads Radiative_Eq_Temp]
    """
    return _ada_lib.Radiative_Eq_Temp_C(
        ctypes.c_double(heat_flux_wm2), ctypes.c_double(emissivity))


def backface_temperature(init_temp: float, heat_flux: float, duration: float,
                         thermal_lag: float, rho_tps: float, cp_tps: float,
                         thickness: float) -> float:
    """1D transient backface temperature via Ada/SPARK FFI.
    T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
    [Citation: Anderson (2006); Rapisarda (2023) Sec 5.5]
    """
    return _ada_lib.Backface_Temperature_C(
        ctypes.c_double(init_temp), ctypes.c_double(heat_flux),
        ctypes.c_double(duration), ctypes.c_double(thermal_lag),
        ctypes.c_double(rho_tps), ctypes.c_double(cp_tps),
        ctypes.c_double(thickness))


def ballistic_coefficient(mass_kg: float, dyn_press_pa: float, drag_force_n: float) -> float:
    """Ballistic coefficient via Ada/SPARK FFI.
    beta = m * q / F_drag
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    """
    return _ada_lib.Ballistic_Coefficient_C(
        ctypes.c_double(mass_kg), ctypes.c_double(dyn_press_pa),
        ctypes.c_double(drag_force_n))


def dynamic_pressure(density_kgm3: float, velocity_ms: float) -> float:
    """Dynamic pressure via Ada/SPARK FFI.
    q = 0.5 * rho * V^2
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    """
    return _ada_lib.Dynamic_Pressure_C(
        ctypes.c_double(density_kgm3), ctypes.c_double(velocity_ms))


def deceleration_g_load(drag_force_n: float, mass_kg: float) -> float:
    """Deceleration in Earth g's via Ada/SPARK FFI.
    n = F_drag / (m * g0)
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    """
    return _ada_lib.Deceleration_G_Load_C(
        ctypes.c_double(drag_force_n), ctypes.c_double(mass_kg))


def atmosphere_temperature(altitude_km: float) -> float:
    """ISA 1975 temperature [K] at altitude [km] via Ada/SPARK FFI.
    [Citation: ISO 2533:1975, International Standard Atmosphere]
    """
    return _ada_lib.Atmosphere_Temperature_C(ctypes.c_double(altitude_km))


def atmosphere_density(altitude_km: float) -> float:
    """ISA 1975 density [kg/m^3] at altitude [km] via Ada/SPARK FFI.
    [Citation: ISO 2533:1975, International Standard Atmosphere]
    """
    return _ada_lib.Atmosphere_Density_C(ctypes.c_double(altitude_km))
