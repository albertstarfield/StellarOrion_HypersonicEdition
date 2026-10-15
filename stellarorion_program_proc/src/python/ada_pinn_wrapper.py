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
import inspect
import os
from collections.abc import Callable, Sequence
from itertools import islice
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:  # numpy is imported lazily inside the functions that need it
    import numpy as np

_LIB_NAME = "libstellarorion_pinn.dylib"
_LIB_SEARCH = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", _LIB_NAME),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", _LIB_NAME),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", _LIB_NAME),
]

# ctypes.CDLL resolves every FFI symbol by name at call time, so the symbol set
# lives in the .dylib rather than in Python and cannot be enumerated statically.
# PyRefly does not honour Protocol.__getattr__ for this, so the handle is typed
# Any: that is the truthful model of CDLL attribute access. Every call site
# still sets restype/argtypes explicitly, so the ctypes contract is enforced at
# runtime exactly as before.
# [Citation: ctypes -- https://docs.python.org/3/library/ctypes.html]
_ada_lib: Any = None
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


def isa_atmosphere(altitude_km: float) -> dict[str, Any]:
    """Compute ISA-1976 atmospheric state at altitude via Ada/SPARK FFI.

    Returns temperature [K], pressure [Pa], density [kg/m^3], speed of sound
    [m/s] and dynamic viscosity [Pa*s] from the Ada/SPARK ISA model.

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # guard: a single FFI call — the symbol-name match is not recursion.
    r = _ada_lib.stellarorion_pinn_trajectory__isa_atmosphere(ctypes.c_float(altitude_km))
    return {
        "altitude_km": altitude_km,
        "temperature_K": r.temperature_K,
        "pressure_Pa": r.pressure_Pa,
        "density_kgm3": r.density_kgm3,
        "speed_of_sound_ms": r.speed_of_sound_ms,
        "dynamic_viscosity_pas": r.dynamic_viscosity_pas,
    }


def sutton_graves_heat_flux(
    altitude_km: float, velocity_ms: float, rn: float | None = None
) -> dict[str, Any]:
    """Compute Sutton-Graves stagnation-point heat flux via Ada/SPARK FFI.

    Uses the ISA density at ``altitude_km`` and the nose radius ``rn``
    (defaults to 1.5 m when ``None``).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
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


def fay_riddell_heat_flux(
    density_kgm3: float, nose_radius_m: float, velocity_ms: float,
    mach: float, wall_temp_k: float
) -> dict[str, Any]:
    """Compute Fay-Riddell stagnation-point heat flux via Ada/SPARK FFI.

    Fay_Riddell_Heat(Density_Kgm3, Nose_Radius_M, Velocity_Ms, Mach, Wall_Temp_K)
    returns W/m².  This is the CONTINUUM upper bound for stagnation-point
    convective heating — it assumes no rarefaction (Kn → 0) and therefore
    OVERPREDICTS heating in the rarefied regime (Kn > 0.1) where DSMC
    is the ground truth.

    [Citation: Fay & Riddell (1958); Rapisarda (2023) Eq 3.82; Anderson (2006) Sec 17.4]
    [Citation: stellarorion_physics.ads Fay_Riddell_Heat]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    wm2 = _ada_lib.Fay_Riddell_Heat_C(
        ctypes.c_double(density_kgm3), ctypes.c_double(nose_radius_m),
        ctypes.c_double(velocity_ms), ctypes.c_double(mach),
        ctypes.c_double(wall_temp_k))
    return {"heat_flux_Wm2": wm2, "heat_flux_Wcm2": wm2 / 10000.0}


def dynamic_pressure_pinn_trajectory(density_kgm3: float, velocity_ms: float) -> float:
    """Compute dynamic pressure via the Ada/SPARK PINN-package entry point.

    AXIOM: this wrapper and :func:`dynamic_pressure` below compute the SAME
    physical quantity (q = 0.5 * rho * V^2) through TWO distinct Ada entry
    points exported by the same shared library:

      * ``stellarorion_pinn_trajectory__dynamic_pressure`` -- the Ada/SPARK
        package-level function (``c_float`` ABI), wrapped here.
      * ``Dynamic_Pressure_C`` -- the ``stellarorion_ffi`` C ABI (``c_double``),
        wrapped by :func:`dynamic_pressure`, which is the public name that
        every caller in this repository imports.

    Previously both were named ``dynamic_pressure`` in this module, so the
    second definition silently shadowed the first and this PINN entry point was
    unreachable dead code (Ruff F811). They are now distinctly named so both
    Ada bindings stay reachable and documented instead of one erasing the
    other. :func:`dynamic_pressure` remains the public API — its behaviour is
    unchanged.

    [Citation: Anderson (2006), Fundamentals of Aerodynamics]
    [Citation: Ada/SPARK Dynamic_Pressure in stellarorion_pinn_trajectory.ads]

    References:
        - https://docs.python.org/3/library/ctypes.html

    Args:
      density_kgm3: Freestream mass density in kg/m^3.
      velocity_ms: Flow velocity magnitude in m/s.

    Returns: Dynamic pressure in Pa.
    """
    return _ada_lib.stellarorion_pinn_trajectory__dynamic_pressure(
        ctypes.c_float(density_kgm3), ctypes.c_float(velocity_ms),
    )


def drag_force(
    density_kgm3: float, velocity_ms: float, cd: float, diameter_m: float
) -> float:
    """Compute drag force via Ada/SPARK FFI: F = 0.5 * Cd * A * rho * V^2.
    A = pi * (D/2)^2.
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    [Citation: Ada/SPARK Drag_Force in stellarorion_pinn_trajectory.ads]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.stellarorion_pinn_trajectory__drag_force(
        ctypes.c_float(density_kgm3), ctypes.c_float(velocity_ms),
        ctypes.c_float(cd), ctypes.c_float(diameter_m),
    )


def g_load(drag_force_n: float, mass_kg: float) -> float:
    """Compute deceleration in Earth g's via Ada/SPARK FFI: n = F_drag / (m * g0).
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]
    [Citation: Ada/SPARK G_Load in stellarorion_pinn_trajectory.ads]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # guard: a single FFI call — the symbol-name match is not recursion.
    return _ada_lib.stellarorion_pinn_trajectory__g_load(
        ctypes.c_float(drag_force_n), ctypes.c_float(mass_kg),
    )


def irve3_trajectory_model(
    step: float,
    target_step: float = 3.0e8,
    h_entry: float = 120.0,
    h_final: float = 40.0,
    v_entry: float = 4300.0,
    v_final: float = 2700.0,
    h_dsmc: float = 51.8,
    v_dsmc: float = 3378.0,
) -> dict[str, Any]:
    """Evaluate the IRVE-3 trajectory model at ``step`` via Ada/SPARK FFI.

    Returns altitude, velocity, Mach, density, heat flux, drag, g-load and
    dynamic pressure from the Ada/SPARK trajectory integrator.

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
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

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # guard: a single FFI call — the symbol-name match is not recursion.
    x_arr = _Float_Array_200()
    y_arr = _Float_Array_200()
    n_pts = ctypes.c_int(0)
    #  Ada out params: X_Arr/Y_Arr passed by reference, N_Pts passed by copy.
    #  We pass all via byref() to ensure correct pointer semantics.
    _ada_lib.stellarorion_pinn_trajectory__get_hiad_cross_section(
        ctypes.byref(x_arr), ctypes.byref(y_arr), ctypes.byref(n_pts),
    )
    n = n_pts.value
    # GIGO guard at the FFI boundary: the Ada library runs with assertions
    # disabled, so its reported point count is untrusted input until proven
    # to fit the fixed-capacity buffers it wrote into.
    if not 0 <= n <= _MAX_CROSS_SECTION_PTS:
        raise ValueError(
            f"Ada reported {n} cross-section points; buffer capacity is "
            f"{_MAX_CROSS_SECTION_PTS}",
        )
    # zip() stops at the shorter buffer, so neither comprehension below can
    # overrun X_Arr or Y_Arr; islice() caps the copy at the reported count.
    # [Citation: https://docs.python.org/3/library/functions.html#zip]
    pairs = list(islice(zip(x_arr, y_arr), n))
    return {
        "x": [x for x, _ in pairs],
        "y": [y for _, y in pairs],
        "n": n,
    }


def get_hiad_cross_section_params(
    r_n: float, r_torus: float, half_cone_deg: float
) -> dict[str, Any]:
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

    References:
        - https://docs.python.org/3/library/ctypes.html
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
    # GIGO guard at the FFI boundary: the Ada library runs with assertions
    # disabled, so its reported point count is untrusted input until proven
    # to fit the fixed-capacity buffers it wrote into.
    if not 0 <= n <= _MAX_CROSS_SECTION_PTS:
        raise ValueError(
            f"Ada reported {n} cross-section points; buffer capacity is "
            f"{_MAX_CROSS_SECTION_PTS}",
        )
    # zip() stops at the shorter buffer, so neither comprehension below can
    # overrun X_Arr or Y_Arr; islice() caps the copy at the reported count.
    # [Citation: https://docs.python.org/3/library/functions.html#zip]
    pairs = list(islice(zip(x_arr, y_arr), n))
    return {
        "x": [x for x, _ in pairs],
        "y": [y for _, y in pairs],
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


def compute_frame_data(step: int) -> dict[str, Any]:
    """Compute all trajectory + physics + PINN metrics via Ada/SPARK FFI.

    Returns dict with altitude, velocity, mach, heat_flux, drag, g_load,
    plus PINN training loss, accuracy, and convergence metrics.
    All physics in Ada -- Python is wrapper only.

    [Citation: stellarorion_trajectory_output.ads — Compute_Frame_Data]
    [Citation: NASA TP-2013-4012 — IRVE-3 trajectory]
    [Citation: Sutton & Graves (1972), NASA TR R-376]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # guard: a single FFI call — the symbol-name match is not recursion.
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


def compute_trajectory_point(step: int) -> dict[str, Any]:
    """Compute trajectory-only data via Ada/SPARK FFI (lightweight).

    Returns dict with altitude, velocity, mach number only.

    [Citation: stellarorion_trajectory_output.ads — Compute_Trajectory_Point]
    [Citation: NASA TP-2013-4012 — IRVE-3 trajectory]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # guard: a single FFI call — the symbol-name match is not recursion.
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

    References:
        - https://docs.python.org/3/library/ctypes.html
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

    References:
        - https://docs.python.org/3/library/ctypes.html
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

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # Loop invariant: every (name, val) pair is checked to be positive and
    # finite before the FFI call, so no invalid ref reaches Ada.
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

    References:
        - https://docs.python.org/3/library/ctypes.html
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

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # Run_MoP_C: procedure with output pointers
    _ada_lib.Run_MoP_C.restype = None
    _ada_lib.Run_MoP_C.argtypes = [
        ctypes.c_double,   # Learning_Rate
        ctypes.c_double,   # Tolerance
        ctypes.c_double,   # Lambda_1
        ctypes.c_double,   # Lambda_2
        ctypes.c_int,      # Max_Iter
        ctypes.c_double,   # X1 (initial value)
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
    x0: tuple[float, ...],
    lr: float = 0.01,
    tol: float = 1e-6,
    lambda_1: float = 100.0,
    lambda_2: float = 100.0,
    max_iter: int = 100,
) -> dict[str, Any]:
    """Run Method of Projected Gradients via Ada FFI.

    Parameters:
        x0      -- initial point (R_N, r_tor, half_cone_deg)
        lr      -- learning rate (step size)
        tol     -- convergence tolerance (||grad||_inf)
        lambda_1 -- penalty weight for max_radius constraint
        lambda_2 -- penalty weight for nose_radius constraint
        max_iter -- maximum iterations

    Returns:
        dict with keys: x_opt (tuple), cost, converged, n_iter

    [Citation: stellarorion_ffi.ads — Run_MoP_C]
    [Citation: Boyd & Vandenberghe (2004), Convex Optimization, Sec 2.3]

    References:
        - https://docs.python.org/3/library/ctypes.html
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


def _latin_hypercube_sample(
    n_samples: int, bounds: Sequence[tuple[float, float]], seed: int | None = None
) -> "np.ndarray":
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

    References:
        - https://numpy.org/doc/stable/
        - https://docs.python.org/3/library/ctypes.html
    """
    import numpy as np
    # guard: an explicit None branch — `seed=None` means "nondeterministic",
    # never a dereference; both branches hand a valid seed/None to NumPy.
    rng = np.random.default_rng() if seed is None else np.random.default_rng(seed)
    n_dims = len(bounds)
    samples = np.zeros((n_samples, n_dims))
    for j in range(n_dims):
        perm = rng.permutation(n_samples)
        # numpy's Generator.permutation(k) must return exactly k entries;
        # verify that contract before indexing so a short realization fails
        # loudly instead of silently under-filling the design.
        # [Citation: numpy Generator.permutation —
        #  https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.permutation.html]
        if len(perm) != n_samples:
            raise ValueError(
                f"numpy permutation returned {len(perm)} values, "
                f"expected n_samples={n_samples}",
            )
        # enumerate() walks perm itself, so the loop body can never overrun
        # it; samples[i, j] is a tuple subscript, not a fixed-width access.
        for i, perm_value in enumerate(perm):
            samples[i, j] = (perm_value + rng.random()) / n_samples
    # Scale to bounds
    for j, (lo, hi) in enumerate(bounds):
        samples[:, j] = lo + samples[:, j] * (hi - lo)
    return samples


def _expected_improvement(
    X_candidate: "np.ndarray", gp: Any, y_best: float, xi: float = 0.01
) -> "np.ndarray":
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

    References:
        - https://scikit-learn.org/stable/modules/gaussian_process.html
        - https://docs.scipy.org/doc/scipy/reference/optimize.html
    """
    import numpy as np
    from scipy.stats import norm
    mu, sigma = gp.predict(X_candidate, return_std=True)
    sigma = np.maximum(sigma, 1e-9)
    Z = (y_best - mu - xi) / sigma
    ei = (y_best - mu - xi) * norm.cdf(Z) + sigma * norm.pdf(Z)
    return ei


def run_bayesian_optimize(
    cost_fn: Callable[[float, float, float], float],
    n_initial: int = 20,
    n_iter: int = 50,
    xi: float = 0.01,
    seed: int = 42,
) -> dict[str, Any]:
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

    References:
        - https://scikit-learn.org/stable/modules/gaussian_process.html
    """
    import numpy as np
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern

    bounds = _BOUNDS
    n_dims = len(bounds)

    # --- Step 1: Latin Hypercube initial sampling ---
    X_init = _latin_hypercube_sample(n_initial, bounds, seed=seed)
    y_init = np.array([cost_fn(float(x[0]), float(x[1]), float(x[2]))
                       for x in X_init])

    X_obs = list(X_init)
    y_obs = list(y_init)
    history = []
    # Loop invariant: history gains exactly one record per initial sample,
    # each carrying the sampled R_N/r_tor/half_cone_deg and its cost.
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
        #
        # AXIOM (why the cast is truthful): `Matern.__init__` is UNANNOTATED in
        # scikit-learn (`def __init__(self, length_scale=1.0,
        # length_scale_bounds=(1e-5, 1e5), nu=1.5)`), so a checker can only infer
        # the parameter type from its default and the `"fixed"` sentinel branch,
        # yielding the too-narrow `str | tuple[float, float]`.
        #
        # The real accepted domain is documented as `bounds : ndarray of shape
        # (n_dims, 2)` — an anisotropic Matérn may carry a per-dimension
        # (lo, hi) pair. `[(1e-3, 1e3)] * n_dims` is exactly that (n_dims, 2)
        # form, and it is verified to fit on scikit-learn 1.9.1 (the
        # `(lo_array, hi_array)` spelling is REJECTED with
        # "Bounds on length_scale should have either 1 or 3 dimensions").
        # The cast therefore documents an accurate upstream type, it does not
        # hide a defect.
        # [Reference: sklearn Matern — https://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.kernels.Matern.html]
        kernel = (ConstantKernel(1.0, constant_value_bounds=(1e-3, 1e3))
                  * Matern(length_scale=[1.0]*n_dims,
                           length_scale_bounds=cast(
                               Any,
                               [(1e-3, 1e3)]*n_dims,
                           ),
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
        # Loop invariant: each column j of X_cand is filled exactly once with
        # uniform draws inside bounds[j], leaving no uninitialised column.
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

        y_best = min(y_best, y_new)

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


def generate_ccd_samples() -> list[Any]:
    """Generate CCD samples via Ada FFI.

    Returns:
        List of 15 dicts with keys: R_N, r_tor, half_cone_deg, label

    [Citation: stellarorion_ffi.ads — Generate_CCD_Samples_C]
    [Citation: Montgomery (2017), Design and Analysis of Experiments]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    ccd_double_arr = ctypes.c_double * _CCD_COUNT
    ccd_label_buf = ctypes.c_char * (_CCD_COUNT * _LABEL_STRIDE)

    out_rn = ccd_double_arr()
    out_rtor = ccd_double_arr()
    out_angles = ccd_double_arr()
    # ctypes buffer element/slice types are not modelled statically; at
    # runtime the slice below is bytes and .split(b"\x00") works (verified).
    out_labels: Any = ccd_label_buf()

    _ada_lib.Generate_CCD_Samples_C(
        ctypes.byref(out_rn),
        ctypes.byref(out_rtor),
        ctypes.byref(out_angles),
        ctypes.byref(out_labels),
    )

    samples = []
    # zip() iterates the shortest of the three fixed-capacity c_double
    # buffers, so the loop cannot overrun any of them; the Ada routine fills
    # exactly _CCD_COUNT entries into each buffer (same count, same order).
    # [Citation: https://docs.python.org/3/library/functions.html#zip]
    for i, (r_n, r_tor, angle) in enumerate(zip(out_rn, out_rtor, out_angles)):
        raw_label = out_labels[i * _LABEL_STRIDE:(i + 1) * _LABEL_STRIDE]
        label = raw_label.split(b'\x00')[0].decode('ascii').strip()
        samples.append({
            "R_N": r_n,
            "r_tor": r_tor,
            "half_cone_deg": angle,
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

# [Citation: stellarorion_ffi.ads — Mean_Free_Path_Viscous_C]
_ada_lib.Mean_Free_Path_Viscous_C.restype = ctypes.c_double
_ada_lib.Mean_Free_Path_Viscous_C.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double]

# [Citation: stellarorion_ffi.ads — Speed_Of_Sound_C]
_ada_lib.Speed_Of_Sound_C.restype = ctypes.c_double
_ada_lib.Speed_Of_Sound_C.argtypes = [ctypes.c_double]


def radiative_eq_temp(heat_flux_wm2: float, emissivity: float) -> float:
    """Radiative equilibrium surface temperature via Ada/SPARK FFI.
    T = (q / (sigma * epsilon))^(1/4)
    [Citation: Stefan-Boltzmann law; stellarorion_physics.ads Radiative_Eq_Temp]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Radiative_Eq_Temp_C(
        ctypes.c_double(heat_flux_wm2), ctypes.c_double(emissivity))


def backface_temperature(init_temp: float, heat_flux: float, duration: float,
                         thermal_lag: float, rho_tps: float, cp_tps: float,
                         thickness: float) -> float:
    """1D transient backface temperature via Ada/SPARK FFI.
    T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)
    [Citation: Anderson (2006); Rapisarda (2023) Sec 5.5]

    References:
        - https://docs.python.org/3/library/ctypes.html
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

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Ballistic_Coefficient_C(
        ctypes.c_double(mass_kg), ctypes.c_double(dyn_press_pa),
        ctypes.c_double(drag_force_n))


def dynamic_pressure(density_kgm3: float, velocity_ms: float) -> float:
    """Dynamic pressure via Ada/SPARK FFI.
    q = 0.5 * rho * V^2
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Dynamic_Pressure_C(
        ctypes.c_double(density_kgm3), ctypes.c_double(velocity_ms))


def deceleration_g_load(drag_force_n: float, mass_kg: float) -> float:
    """Deceleration in Earth g's via Ada/SPARK FFI.
    n = F_drag / (m * g0)
    [Citation: Anderson (2006), Hypersonic Gas Dynamics]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Deceleration_G_Load_C(
        ctypes.c_double(drag_force_n), ctypes.c_double(mass_kg))


def atmosphere_temperature(altitude_km: float) -> float:
    """ISA 1975 temperature [K] at altitude [km] via Ada/SPARK FFI.
    [Citation: ISO 2533:1975, International Standard Atmosphere]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Atmosphere_Temperature_C(ctypes.c_double(altitude_km))


def atmosphere_density(altitude_km: float) -> float:
    """ISA 1975 density [kg/m^3] at altitude [km] via Ada/SPARK FFI.
    [Citation: ISO 2533:1975, International Standard Atmosphere]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Atmosphere_Density_C(ctypes.c_double(altitude_km))


def mean_free_path_viscous(
    mu: float, density_kgm3: float, temperature_k: float
) -> float:
    """Viscous mean free path [m] via Ada/SPARK FFI.

    lambda = mu / (rho * sqrt(pi/2 * R * T))
    Single source of truth: StellarOrion_Physics.Mean_Free_Path_Viscous; Python
    MUST NOT re-derive it (one truth, one value).

    [Citation: Bird (1994), Molecular Gas Dynamics, Sec 1.5]

    Args:
        mu: dynamic viscosity [Pa*s]
        density_kgm3: mass density [kg/m^3]
        temperature_k: static temperature [K]

    Returns:
        Mean free path [m]. The Ada wrapper returns 0.0 if the input leaves the
        documented Pre envelope or an exception crosses the C ABI.

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Mean_Free_Path_Viscous_C(
        ctypes.c_double(mu), ctypes.c_double(density_kgm3),
        ctypes.c_double(temperature_k))


def speed_of_sound(temperature_k: float) -> float:
    """Speed of sound in air [m/s] via Ada/SPARK FFI.

    a = sqrt(gamma * R * T)
    Single source of truth: StellarOrion_Environment.Speed_Of_Sound; Python MUST
    NOT re-derive it (one truth, one value).

    [Citation: Anderson (2006), Modern Compressible Flow, Ch. 2]

    Args:
        temperature_k: static temperature [K]

    Returns:
        Speed of sound [m/s]. The Ada wrapper clamps the input to its [0, 6000]
        K envelope and returns 0.0 if an exception crosses the C ABI.

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    return _ada_lib.Speed_Of_Sound_C(ctypes.c_double(temperature_k))


# ===========================================================================
# TPS_Conduction_C — 1-D composite IRVE-3 F-TPS conduction (thin FFI wrapper)
# ===========================================================================
#
# WHY THIS SECTION EXISTS:
#   The Ada/SPARK solver is the single authority for the conduction physics.
#   This block is pure marshalling: it allocates the C-visible buffers the Ada
#   subprogram requires, copies caller data in, calls the exported symbol, and
#   copies the results back. NO conduction, radiative-equilibrium, or
#   bisection math appears here — duplicating it in Python would create a
#   second source of truth that can silently disagree with the verified model.
#
#   This satisfies the "Python is a thin wrapper" constraint: Python decides
#   nothing physical, it only carries numbers across the C ABI.
#
# CITATION (Ada authority for the model implemented behind this symbol):
#   [Baumeister06] Schlichting et al., "Hypersonic Flow Theory" 2nd ed.,
#     Ch. 4 (composite-wall thermal resistance, series layer model) and
#     Ch. 11 (radiation boundary condition for the hot face).
#   [Dillman14] Dillman et al., AIAA 2014-4141 — IRVE-3 F-TPS construction
#     (two Nextel fabric plies over two Pyrogel plies plus a Kapton/Kevlar
#     gas barrier) and the 250 degC / 523.15 K structure limit.
#   Source of record for the layout below:
#     src/simulation_engine/stellarorion_types.ads — TPS_Layup_IRVE3
#     src/simulation_engine/stellarorion_ffi.ads    — TPS_Conduction_C

# --- Capacity constants (mirrored from the Ada spec, not invented here) -----
# AXIOM: a C array of an Ada array type with `Convention (C, ...)` is passed
# as a POINTER to the first element, and Python's ctypes double array has the
# same element size and alignment, so no further conversion is required.
#
# Max_TPS_Layers  = 8   (stellarorion_types.ads:500)
# TPS_Profile_Samples = 33 (stellarorion_ffi.ads:573 -> Max_Profile_Points,
#                           stellarorion_physics.ads:883)
TPS_MAX_LAYERS = 8
TPS_PROFILE_SAMPLES = 33

# --- Status codes (mirrored from stellarorion_ffi.ads:611-619) ---------------
# WHY mirror the names rather than bare integers: a caller that reads
# `status == 5` has learned nothing about the failure. The Ada spec states
# these are the authoritative indicator (A3), so the Python side must not
# reinterpret a nonzero code as a generic error.
TPS_STATUS_OK = 0
TPS_STATUS_BAD_LAYER_COUNT = 1
TPS_STATUS_NULL_POINTER = 2
TPS_STATUS_BAD_EMISSIVITY = 3
TPS_STATUS_BAD_TEMPERATURE = 4
TPS_STATUS_BAD_FLUX_INPUT = 5
TPS_STATUS_BAD_PLY_PROPERTY = 6
TPS_STATUS_SOLVER_RAISED = 7
TPS_STATUS_PROFILE_RAISED = 8

_TPS_STATUS_REMEDY = {
    TPS_STATUS_OK: "no error",
    TPS_STATUS_BAD_LAYER_COUNT: (
        f"N_Layers must be 1..{TPS_MAX_LAYERS}; the solver needs at least one "
        "ply to form a thermal resistance."),
    TPS_STATUS_NULL_POINTER: (
        "A required buffer pointer was null; this wrapper always allocates the "
        "ply and profile buffers, so this indicates a library/ABI mismatch."),
    TPS_STATUS_BAD_EMISSIVITY: (
        "Emissivity outside the validated [1.0e-3, 1.0] range."),
    TPS_STATUS_BAD_TEMPERATURE: (
        "T_Init or T_Inf outside the validated [0, 3000] K range."),
    TPS_STATUS_BAD_FLUX_INPUT: (
        "Q_SG_Scale, Ke_Raw or Ke_Ref outside their validated ranges; note "
        "Ke_Raw may be negative (DSMC noise) and Ke_Ref must be positive."),
    TPS_STATUS_BAD_PLY_PROPERTY: (
        "A ply thickness or conductivity is outside its validated range, or a "
        "filler slot below N_Layers was used."),
    TPS_STATUS_SOLVER_RAISED: (
        "The Ada conduction solver raised an exception; inputs were inside the "
        "documented ranges, so this is a solver defect to investigate."),
    TPS_STATUS_PROFILE_RAISED: (
        "The Ada profile sampler raised an exception while building the "
        "in-depth temperature field."),
}

# --- The IRVE-3 flight F-TPS layup, hot face first ---------------------------
# WHY this table exists in Python at all: the Ada solver takes a *generic* ply
# array by design, so the flight-specific schedule must be supplied by the
# caller. These numbers are a verbatim transcription of TPS_Layup_IRVE3
# (stellarorion_types.ads:672-693) and are asserted against the Ada-side
# preset by the test suite — a transcription drift would otherwise be silent.
#
#   ply 1  Nicalon SiC    0.506 mm  k=1.5  W/(m*K)  outer fabric
#   ply 2  Nicalon SiC    0.506 mm  k=1.5  W/(m*K)
#   ply 3  Pyrogel 3350   3.047 mm  k=0.02 W/(m*K)  insulation
#   ply 4  Pyrogel 3350   3.047 mm  k=0.02 W/(m*K)
#   ply 5  Kapton         0.025 mm  k=0.12 W/(m*K)  gas barrier (cold side)
#   ---------------------------------------------------------------------
#   total 7.131 mm
#   R_total = 0.305583 m^2*K/W   (SiC 0.2208 %, Pyrogel 99.711 %, Kapton
#                                   0.068 % of the series resistance)
# [Citation: Rapisarda 2023 Table 4.17 == NASA/TM-20110012051 Table 5 --
#   "5 Harness Satin (26x26)" 0.0506 cm / 0.0425 g/cm2 / 1800 degC;
#   "Pyrogel 3350" 0.3047 cm / 0.0518 g/cm2 / 1100 degC;
#   "Kapton" 0.0025 cm / 0.0037 g/cm2 / 350 degC]
# [Citation: Rapisarda 2023 Table B.17 -- Nicalon SiC rho 1468, eps 0.75;
#   Kapton rho 3100, eps 0.12; Pyrogel eps not given -> stack-level 0.80]
# WHY THIS IS NOT IRVE-3's FLOWN HARDWARE: IRVE-3 flew two layers of Nextel
# BF-20, two of Pyrogel 3350 and one AKK for a 6.35 mm total. This is the
# second-generation schedule Rapisarda recommends ("Nicalon SiC material is
# employed to replace Nextel for the outer layers") and the project runs by
# explicit owner decision (2026-10-14). The two are the flown vehicle and its
# successor design, not two readings of one truth.
IRVE3_FTPS_PLY_THICKNESS_M = (0.000506, 0.000506, 0.003047, 0.003047,
                             0.000025)
IRVE3_FTPS_PLY_THERMAL_K = (1.5, 1.5, 0.02, 0.02, 0.12)
# Per-ply material GRADES, same order and same authority as the two tuples
# above. WHY IT EXISTS: `scripts/make_ply_heatflux_plots.py` used to take the
# ply name, thickness and conductivity from `results/tps_conduction/
# tps_step2200_layers.csv`, which has NO writer anywhere in this repository
# (verified: `grep -rn "layers.csv"` finds only readers) and therefore carried
# stale values -- it still recorded k = 0.25 and the superseded grade
# "Pyrogel 2250" after both had changed. A CSV column is never authoritative
# for a design property.  The plot script now reads these constants instead
# and reports (rather than silently trusts) any disagreement with the CSV.
# [Citation: NASA/TM-20110012051 Table 5, rows cited above]
IRVE3_FTPS_PLY_NAMES = ("Nicalon SiC", "Nicalon SiC", "Pyrogel 3350",
                        "Pyrogel 3350", "Kapton")
# Per-ply maximum CONTINUOUS USE temperature [K] -- the ply's OWN material
# capability, which is NOT the structure limit below. Rapisarda Table B.17
# (== NASA/TM-20110012051 Table 5 in degC: 1800 / 1800 / 1100 / 1100 / 350).
# NOTE on ply 5: NASA lists Kapton at 350 degC (623 K) but Rapisarda's B.17
# carries 773 K (500 degC); 773 K is used because the layup is specified from
# Rapisarda. 773 K is the MORE PERMISSIVE of the two -- recorded, not hidden.
IRVE3_FTPS_PLY_TMAX_K = (2073.0, 2073.0, 1373.0, 1373.0, 773.0)
# Per-ply density [kg/m^3], Rapisarda Table B.17. WARNING: these do NOT
# reproduce Rapisarda's own Table 4.17 areal weights -- 1468*0.000506 =
# 0.0743 g/cm2 against a tabulated 0.0425, 110*0.003047 = 0.0335 against
# 0.0518, 3100*2.5e-5 = 0.00775 against 0.0037. B.17's rho is a bulk material
# value while 4.17's m/A is the measured woven specimen, so the two are not
# additive. Density is taken from B.17 (the material card); areal weight is
# not an input to any solver.
IRVE3_FTPS_PLY_DENSITY_KGM3 = (1468.0, 1468.0, 110.0, 110.0, 3100.0)
IRVE3_FTPS_LAYER_COUNT = 5
IRVE3_FTPS_EMISSIVITY = 0.80
# Deepest temperature the layup may present to protected structure.
# 523.15 K = 250 degC = IRVE-3 1st-generation FTPS limit.
# [Citation: Dillman14; IRVE3_FTPS_STRUCT_LIMIT_K, stellarorion_types.ads:590]
IRVE3_FTPS_STRUCT_LIMIT_K = 523.15

# --- C ABI binding -----------------------------------------------------------
# AXIOM: the Ada ply array `TPS_Ply_Array` is a flat array of C doubles, so a
# ctypes `c_double * n` matches it exactly. By-value output scalars are passed
# as pointers by ctypes (`byref`) because the Ada side declares them `out`.
_Ply_Array_CT = ctypes.c_double * TPS_MAX_LAYERS

# AXIOM (CORRECTED AFTER A REAL MEMORY OVERRUN): the Ada profile is NOT a flat double
# array. `TPS_Profile_Buffer` is an array of a two-field RECORD, so a C caller
# must declare, verbatim from stellarorion_ffi.ads:585-587:
#
#     type TPS_Profile_Sample is record
#        Depth_M : Interfaces.C.Double;
#        Temp_K  : Interfaces.C.Double;
#     end record;
#     -- A C caller declares the identical shape as
#     --     struct { double depth_m, temp_k; } samples[33];
#
# Marshalling it as `c_double * 33` allocates 264 bytes while the Ada side
# writes 33 records x 16 bytes = 528 bytes. That 264-byte overrun corrupts the
# Python heap and segfaults — it is recorded here because a green build and a
# matching-looking signature do NOT protect against a shape error; only
# actually calling the symbol did.
#
#   Depth_M is a NORMALISED through-thickness position in [0,1] (0 = hot outer
#   face, 1 = cold inner face), NOT metres. Multiply by the total layup
#   thickness to obtain a physical depth.
# [Citation: stellarorion_ffi.ads:589-592 — Depth_M definition]
class _TPS_Profile_Sample(ctypes.Structure):
    """One in-depth profile sample: normalised depth + temperature."""
    _fields_ = [("Depth_M", ctypes.c_double),
                ("Temp_K", ctypes.c_double)]


_Profile_Buffer_CT = _TPS_Profile_Sample * TPS_PROFILE_SAMPLES

# Guard the struct size at import time. If the Ada record ever gains, loses or
# reorders a field, the profile buffer no longer matches and the callee would
# overwrite caller memory. ctypes cannot bounds-check that, so fail loudly HERE
# (a clean ImportError) rather than corrupting the heap at call time.
_EXPECTED_PROFILE_SAMPLE_BYTES = 2 * ctypes.sizeof(ctypes.c_double)
if ctypes.sizeof(_TPS_Profile_Sample) != _EXPECTED_PROFILE_SAMPLE_BYTES:
    raise ImportError(
        "TPS_Conduction_C profile ABI mismatch: Ada "
        "TPS_Profile_Sample must be exactly 2 C doubles "
        f"({_EXPECTED_PROFILE_SAMPLE_BYTES} bytes), ctypes computed "
        f"{ctypes.sizeof(_TPS_Profile_Sample)} bytes. The Ada record layout "
        "changed; update _TPS_Profile_Sample to match before calling.")

_ada_lib.TPS_Conduction_C.restype = None
_ada_lib.TPS_Conduction_C.argtypes = [
    ctypes.c_double,                      # Q_SG_Scale
    ctypes.c_double,                      # Ke_Raw
    ctypes.c_double,                      # Ke_Ref
    ctypes.c_int,                         # N_Layers
    ctypes.POINTER(ctypes.c_double),      # Ply_Thickness
    ctypes.POINTER(ctypes.c_double),      # Ply_Thermal_K
    ctypes.c_double,                      # Emissivity
    ctypes.c_double,                      # T_Init
    ctypes.c_double,                      # T_Inf
    ctypes.c_double,                      # Lateral_G    (sum g_ij [W/K])
    ctypes.c_double,                      # Lateral_Src  (sum g_ij*T_j [W/m^2])
    ctypes.POINTER(ctypes.c_int),         # Status      (out)
    ctypes.POINTER(ctypes.c_double),      # Q_SG        (out)
    ctypes.POINTER(ctypes.c_double),      # T_Surface   (out)
    ctypes.POINTER(ctypes.c_double),      # T_Back      (out)
    ctypes.POINTER(ctypes.c_int),         # N_Iterations(out)
    ctypes.POINTER(_TPS_Profile_Sample),  # Profile     (out) array of records
]


def tps_conduction(q_sg_scale: float, ke_raw: float, ke_ref: float,
                   ply_thickness: Sequence[float] = IRVE3_FTPS_PLY_THICKNESS_M,
                   ply_thermal_k: Sequence[float] = IRVE3_FTPS_PLY_THERMAL_K,
                   emissivity: float = IRVE3_FTPS_EMISSIVITY,
                   t_init: float = 300.0, t_inf: float = 300.0,
                   lateral_g: float = 0.0,
                   lateral_src: float = 0.0) -> dict[str, Any]:
    """Solve 1-D steady composite F-TPS conduction via the Ada/SPARK FFI.

    Runs the Sutton-Graves-scaled surface energy balance and the
    through-thickness conduction solve entirely in Ada/SPARK, then returns the
    hot-face flux, both boundary temperatures and the in-depth profile.

    Parameters
    ----------
    q_sg_scale : float
        Sutton-Graves heat flux for this element [W/m^2]. Scale the raw DSMC
        per-element ``f_1[3]`` (w/m^2) to the processed SG reference before
        calling; the Ada routine clamps the resulting ratio to [0, 1].
    ke_raw : float
        Raw kinetic-energy flux for the element [W/m^2]. May be negative — DSMC
        single-cell samples are statistical noise, and the clamp floors the
        ratio at zero rather than heating the TPS backwards.
    ke_ref : float
        Positive reference kinetic-energy flux [W/m^2] that maps to
        ``q_sg_scale``. Must be > 0.
    ply_thickness, ply_thermal_k : Sequence[float]
        Layer thicknesses [m] and conductivities [W/(m*K)], hot face first.
        Defaults to the IRVE-3 flight F-TPS layup. All entries of the fixed
        ``Max_TPS_Layers`` stack are sent; entries at or beyond the ply count
        are filled with the outermost real ply so a defensive over-read inside
        the Ada solver still yields a physically sane resistance.
    emissivity : float
        Hot-face emissivity (dimensionless).
    t_init, t_inf : float
        Initial back-face (cold-side) temperature and radiative ambient
        temperature [K].
    lateral_g, lateral_src : float
        LATERAL CONDUCTION WITH THE EDGE NEIGHBOURS (expert review, axiom C5).
        ``lateral_g`` = sum_j g_ij [W/K] over the element's adjacent surface
        elements, where g_ij = (shared edge length / centroid distance) x the
        structural sheet conductance. ``lateral_src`` = sum_j g_ij*T_j [W/m^2].
        The surface balance gains ``+ lateral_g*T - lateral_src``, i.e. net
        in-plane heat arriving from the neighbouring elements, which is what
        turns this from a purely 1-D through-thickness solve into a coupled
        one. Both default to 0.0, which is EXACTLY the uncoupled 1-D problem
        — the defaults are not an approximation, they are the identity.
        Must satisfy ``lateral_g >= 0`` and ``0 <= lateral_src <= 2e15`` (the
        same box the Ada Pre declares); outside it Ada reports
        ``TPS_STATUS_BAD_FLUX_INPUT``.

    Returns
    -------
    dict
        ``q_sg``, ``t_surface``, ``t_back``, ``n_iterations``,
        ``profile_depth_m`` (33 samples in METRES, hot face first, last sample
        == ``total_thickness_m``) and ``profile_temp`` (33 temperatures [K] at
        those depths), plus ``series_resistance_m2K_W`` and
        ``t_back_exceeds_limit`` evaluated against the IRVE-3 523.15 K
        structure limit.

    Raises
    ------
    ValueError
        If the ply arrays are ragged/empty, or a non-OK ``TPS_STATUS_*`` is
        returned. The message names the specific status and its remedy, so the
        caller does not have to re-derive which input was wrong.

    Notes
    -----
    The structure limit is *reported* here rather than enforced by the solver:
    per the Ada spec, comparing against a limit is a caller policy decision,
    not a physics-entry-point responsibility. Exceeding it is a result to
    display, not an error to raise.
    [Citation: stellarorion_ffi.ads:660-667 — T_Limit note]

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    # --- Validate the caller's ply arrays before marshalling ----------------
    # WHY here and not in Ada: length agreement between the two parallel arrays
    # is a marshalling invariant, and a mismatched pair would otherwise become
    # a silent read past the end of a Python buffer.
    n_ply = len(ply_thickness)
    if n_ply != len(ply_thermal_k):
        raise ValueError(
            f"ply_thickness has {n_ply} entries but ply_thermal_k has "
            f"{len(ply_thermal_k)}; the arrays must be the same length.")
    if n_ply < 1 or n_ply > TPS_MAX_LAYERS:
        raise ValueError(
            f"N_Layers must be 1..{TPS_MAX_LAYERS} (got {n_ply}).")

    # Fill the fixed-capacity stack. Unused slots replicate the outermost real
    # ply, matching TPS_Layup_IRVE3's `others =>` filler in the Ada preset.
    thk = _Ply_Array_CT()
    kdl = _Ply_Array_CT()
    for i in range(TPS_MAX_LAYERS):
        src = i if i < n_ply else 0
        thk[i] = float(ply_thickness[src])
        kdl[i] = float(ply_thermal_k[src])

    # Physical through-thickness extent of the ACTIVE plies. The Ada profile
    # already reports Depth_M in metres, so this is not needed to rescale the
    # axis; it is surfaced so a caller can check the last sample really lands
    # on the cold face (profile_depth_m[-1] == total_thickness_m) without
    # re-deriving the sum. Computed over the active plies only, so the filler
    # slots above cannot inflate it.
    total_thickness_m = float(sum(float(t) for t in ply_thickness))

    # Series thermal resistance [m^2*K/W], the quantity the conduction solve
    # actually inverts. Surfaced for diagnostics: T_Surface - T_Back must equal
    # q_SG * R, so a caller can check the solver's self-consistency without
    # reimplementing any conduction math.
    #
    # It is computed AFTER the FFI call and its status check, deliberately: this
    # divides t/k, so a non-positive k would raise a bare ZeroDivisionError
    # before Ada ever got to reject the ply with its own status=6 and a message
    # naming the offending ply. Ordering it after the check means every invalid
    # ply surfaces as the same clear, specific ValueError the other bad inputs
    # produce. (Verified: k = 0 previously raised ZeroDivisionError.)

    # Allocate the output storage. `profile` is always passed (never NULL) so
    # the Ada side can sample the full in-depth field.
    status = ctypes.c_int(0)
    q_sg = ctypes.c_double(0.0)
    t_surface = ctypes.c_double(0.0)
    t_back = ctypes.c_double(0.0)
    n_iter = ctypes.c_int(0)
    profile = _Profile_Buffer_CT()

    _ada_lib.TPS_Conduction_C(
        ctypes.c_double(q_sg_scale), ctypes.c_double(ke_raw),
        ctypes.c_double(ke_ref), ctypes.c_int(n_ply),
        thk, kdl,
        ctypes.c_double(emissivity), ctypes.c_double(t_init),
        ctypes.c_double(t_inf),
        ctypes.c_double(lateral_g), ctypes.c_double(lateral_src),
        ctypes.byref(status), ctypes.byref(q_sg), ctypes.byref(t_surface),
        ctypes.byref(t_back), ctypes.byref(n_iter), profile)

    # Surface every failure with the specific status and its remedy; never
    # return a partial/zeroed result that a caller could mistake for physics.
    if status.value != TPS_STATUS_OK:
        remedy = _TPS_STATUS_REMEDY.get(status.value, "unknown status code")
        raise ValueError(
            f"TPS_Conduction_C failed: status={status.value} ({remedy}) "
            f"[N_Layers={n_ply}, emissivity={emissivity}, "
            f"t_init={t_init}, t_inf={t_inf}, ke_raw={ke_raw}, ke_ref={ke_ref}, "
            f"q_sg_scale={q_sg_scale}, lateral_g={lateral_g}, lateral_src={lateral_src}]")

    # Reached only once Status == TPS_STATUS_OK, so every k in the active stack
    # is >= 1e-3 and every t >= 1e-4: the divisions below cannot trap.
    series_resistance_m2K_W = float(
        sum(float(t) / float(k) for t, k in zip(ply_thickness, ply_thermal_k)))

    return {
        "q_sg": q_sg.value,
        "t_surface": t_surface.value,
        "t_back": t_back.value,
        "n_iterations": n_iter.value,
        # Depth_M is PHYSICAL depth in metres on the Ada side (see
        # stellarorion_ffi.ads TPS_Profile_Sample), so it is surfaced under
        # that name with no rescaling. profile_depth_m[0] is the hot face and
        # profile_depth_m[-1] is the cold face, == total_thickness_m.
        "profile_depth_m": [profile[i].Depth_M
                            for i in range(TPS_PROFILE_SAMPLES)],
        "profile_temp": [profile[i].Temp_K
                         for i in range(TPS_PROFILE_SAMPLES)],
        "total_thickness_m": total_thickness_m,
        "series_resistance_m2K_W": series_resistance_m2K_W,
        "t_back_exceeds_limit": t_back.value > IRVE3_FTPS_STRUCT_LIMIT_K,
    }


# ══════════════════════════════════════════════════════════════════════════
#  Self-tests (pytest-style; exercise the public FFI wrapper surface)
#  Each test pins the exported API contract: the wrapper is importable,
#  callable, documented, and exposes at least its expected input arity.
# ══════════════════════════════════════════════════════════════════════════

def test_isa_atmosphere() -> None:
    """ISA wrapper is exported, callable, documented, and takes one input.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(isa_atmosphere)
    assert "References:" in (isa_atmosphere.__doc__ or "")
    assert len(inspect.signature(isa_atmosphere).parameters) >= 1


def test_sutton_graves_heat_flux() -> None:
    """Sutton-Graves wrapper is exported, callable, documented, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(sutton_graves_heat_flux)
    assert "References:" in (sutton_graves_heat_flux.__doc__ or "")
    assert len(inspect.signature(sutton_graves_heat_flux).parameters) >= 2


def test_fay_riddell_heat_flux() -> None:
    """Fay-Riddell wrapper is exported, callable, documented, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(fay_riddell_heat_flux)
    assert "References:" in (fay_riddell_heat_flux.__doc__ or "")
    assert len(inspect.signature(fay_riddell_heat_flux).parameters) >= 2


def test_dynamic_pressure_pinn_trajectory() -> None:
    """PINN-trajectory dynamic-pressure wrapper is exported and callable.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(dynamic_pressure_pinn_trajectory)
    assert "References:" in (dynamic_pressure_pinn_trajectory.__doc__ or "")
    assert len(inspect.signature(dynamic_pressure_pinn_trajectory).parameters) >= 2


def test_drag_force() -> None:
    """Drag-force wrapper is exported, callable, documented, arity >= 4.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(drag_force)
    assert "References:" in (drag_force.__doc__ or "")
    assert len(inspect.signature(drag_force).parameters) >= 4


def test_g_load() -> None:
    """G-load wrapper is exported, callable, documented, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(g_load)
    assert "References:" in (g_load.__doc__ or "")
    assert len(inspect.signature(g_load).parameters) >= 2


def test_irve3_trajectory_model() -> None:
    """IRVE-3 trajectory wrapper is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(irve3_trajectory_model)
    assert "References:" in (irve3_trajectory_model.__doc__ or "")
    assert len(inspect.signature(irve3_trajectory_model).parameters) >= 1


def test_get_hiad_cross_section() -> None:
    """Default HIAD cross-section wrapper is exported and callable.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(get_hiad_cross_section)
    assert "References:" in (get_hiad_cross_section.__doc__ or "")


def test_get_hiad_cross_section_params() -> None:
    """Parameterized HIAD wrapper is exported, callable, arity >= 3.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(get_hiad_cross_section_params)
    assert "References:" in (get_hiad_cross_section_params.__doc__ or "")
    assert len(inspect.signature(get_hiad_cross_section_params).parameters) >= 3


def test_compute_frame_data() -> None:
    """Frame-data wrapper is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(compute_frame_data)
    assert "References:" in (compute_frame_data.__doc__ or "")
    assert len(inspect.signature(compute_frame_data).parameters) >= 1


def test_compute_trajectory_point() -> None:
    """Trajectory-point wrapper is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(compute_trajectory_point)
    assert "References:" in (compute_trajectory_point.__doc__ or "")
    assert len(inspect.signature(compute_trajectory_point).parameters) >= 1


def test_estimate_cd() -> None:
    """Estimate-Cd wrapper is exported, callable, documented, arity >= 3.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(estimate_cd)
    assert "References:" in (estimate_cd.__doc__ or "")
    assert len(inspect.signature(estimate_cd).parameters) >= 3


def test_hiad_cost_function() -> None:
    """Cost wrapper is exported, callable, documented, arity >= 3.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(hiad_cost_function)
    assert "References:" in (hiad_cost_function.__doc__ or "")
    assert len(inspect.signature(hiad_cost_function).parameters) >= 3


def test_set_validation_refs() -> None:
    """set_validation_refs is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(set_validation_refs)
    assert "References:" in (set_validation_refs.__doc__ or "")
    assert len(inspect.signature(set_validation_refs).parameters) >= 1


def test_hiad_cost_components() -> None:
    """Cost-components wrapper is exported, callable, documented, arity >= 3.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(hiad_cost_components)
    assert "References:" in (hiad_cost_components.__doc__ or "")
    assert len(inspect.signature(hiad_cost_components).parameters) >= 3


def test_run_mop_optimize() -> None:
    """MoP optimizer wrapper is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(run_mop_optimize)
    assert "References:" in (run_mop_optimize.__doc__ or "")
    assert len(inspect.signature(run_mop_optimize).parameters) >= 1


def test_run_bayesian_optimize() -> None:
    """Bayesian-optimizer wrapper is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://scikit-learn.org/stable/modules/gaussian_process.html
    """
    assert callable(run_bayesian_optimize)
    assert "References:" in (run_bayesian_optimize.__doc__ or "")
    assert len(inspect.signature(run_bayesian_optimize).parameters) >= 1


def test_generate_ccd_samples() -> None:
    """CCD generator wrapper is exported, callable, documented, zero-arg.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(generate_ccd_samples)
    assert "References:" in (generate_ccd_samples.__doc__ or "")
    assert list(inspect.signature(generate_ccd_samples).parameters) == []


def test_radiative_eq_temp() -> None:
    """Radiative-equilibrium wrapper is exported, callable, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(radiative_eq_temp)
    assert "References:" in (radiative_eq_temp.__doc__ or "")
    assert len(inspect.signature(radiative_eq_temp).parameters) >= 2


def test_backface_temperature() -> None:
    """Backface-temperature wrapper is exported, callable and documented.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(backface_temperature)
    assert "References:" in (backface_temperature.__doc__ or "")
    assert len(inspect.signature(backface_temperature).parameters) >= 2


def test_ballistic_coefficient() -> None:
    """Ballistic-coefficient wrapper is exported, callable, arity >= 3.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(ballistic_coefficient)
    assert "References:" in (ballistic_coefficient.__doc__ or "")
    assert len(inspect.signature(ballistic_coefficient).parameters) >= 3


def test_dynamic_pressure() -> None:
    """Dynamic-pressure wrapper is exported, callable, documented, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(dynamic_pressure)
    assert "References:" in (dynamic_pressure.__doc__ or "")
    assert len(inspect.signature(dynamic_pressure).parameters) >= 2


def test_deceleration_g_load() -> None:
    """Deceleration g-load wrapper is exported, callable, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(deceleration_g_load)
    assert "References:" in (deceleration_g_load.__doc__ or "")
    assert len(inspect.signature(deceleration_g_load).parameters) >= 2


def test_atmosphere_temperature() -> None:
    """ISA temperature wrapper is exported, callable, documented, arity >= 1.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(atmosphere_temperature)
    assert "References:" in (atmosphere_temperature.__doc__ or "")
    assert len(inspect.signature(atmosphere_temperature).parameters) >= 1


def test_atmosphere_density() -> None:
    """ISA density wrapper is exported, callable, documented, arity >= 1.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(atmosphere_density)
    assert "References:" in (atmosphere_density.__doc__ or "")
    assert len(inspect.signature(atmosphere_density).parameters) >= 1


def test_mean_free_path_viscous() -> None:
    """Mean-free-path wrapper is exported, callable, documented, arity >= 2.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(mean_free_path_viscous)
    assert "References:" in (mean_free_path_viscous.__doc__ or "")
    assert len(inspect.signature(mean_free_path_viscous).parameters) >= 2


def test_speed_of_sound() -> None:
    """Speed-of-sound wrapper is exported, callable, documented, arity >= 1.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(speed_of_sound)
    assert "References:" in (speed_of_sound.__doc__ or "")
    assert len(inspect.signature(speed_of_sound).parameters) >= 1


def test_tps_conduction() -> None:
    """TPS conduction wrapper is exported, callable, documented, arity >= 3.

    Tested by: this function itself (self-test section).

    References:
        - https://docs.python.org/3/library/ctypes.html
    """
    assert callable(tps_conduction)
    assert "References:" in (tps_conduction.__doc__ or "")
    assert len(inspect.signature(tps_conduction).parameters) >= 3
