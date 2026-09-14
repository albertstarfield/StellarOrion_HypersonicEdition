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


def irve3_trajectory_model(step, target_step=3.0e8, h_entry=120.0, h_final=50.0,
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


if __name__ == "__main__":
    print("=== Ada/SPARK PINN Trajectory Wrapper Self-Test ===")
    atm = isa_atmosphere(50.0)
    print(f"ISA at 50 km: T={atm['temperature_K']:.1f}K, rho={atm['density_kgm3']:.4e}kg/m3")
    sg = sutton_graves_heat_flux(51.8, 3378.0)
    print(f"SG at 51.8km: {sg['heat_flux_Wcm2']:.3f} W/cm2 (expected ~25.4)")
    sg50 = sutton_graves_heat_flux(50.0, 2700.0)
    print(f"SG at 50km: {sg50['heat_flux_Wcm2']:.3f} W/cm2 (expected ~14.5)")
    t2200 = irve3_trajectory_model(2200)
    print(f"Step 2200: alt={t2200['altitude_km']:.1f}km, g={t2200['g_load']:.2f}")
    t300 = irve3_trajectory_model(300000000)
    print(f"Step 300M: alt={t300['altitude_km']:.1f}km, g={t300['g_load']:.2f}")
    print("Self-test complete.")
