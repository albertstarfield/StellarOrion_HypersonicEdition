#!/usr/bin/env python3
"""Limit-validation harness for the Ada/SPARK composite F-TPS conduction solver.

WHAT THIS IS
    A VERIFICATION HARNESS, not an implementation. Every number it checks is
    produced by ``TPS_Conduction_C`` in Ada/SPARK through the ctypes wrapper
    ``ada_pinn_wrapper.tps_conduction``. This file re-derives only the ANALYTIC
    references the limits are defined against, and reports PASS/FAIL per limit.
    It is the Python-side mirror of the five limits the solver must satisfy.

WHY PYTHON IS LEGITIMATE HERE (project rule: Ada/SPARK primary, Python wrapper)
    The solver itself is Ada/SPARK. This harness is test code: it marshals
    inputs, calls the FFI, and compares against closed-form references. It
    contains no conduction physics used by the product path -- the reference
    formulas below are the textbook limits themselves, deliberately
    implemented independently of the Ada solver so the comparison is not
    circular.

AXIOMS THE SOLVER ENFORCES (stellarorion_physics.adb TPS_Surface_Balance)
    A1  Steady surface energy balance, with the cold face PINNED:
           q = (T_s - T_init)/R  +  eps*sigma*(T_s^4 - T_inf^4)
       (first term = conduction into the stack, second = net radiation).
    A2  T_back = T_init exactly: the solver imposes the Dirichlet condition at
       the cold face rather than a semi-infinite / insulated one.
    A3  The in-depth field is piecewise linear in RESISTANCE:
           T(z) = T_s - (T_s - T_init) * R(0..z) / R_total
       so a single homogeneous ply makes T(z) exactly LINEAR in z.
    A4  R_total depends only on the MULTISET of ply resistances
       (sum of delta_i/k_i), never on their order.

THEORIES CHECKED (one per limit)
    T1  R -> infinity removes the conduction term, so
           T_s -> (q/(eps*sigma) + T_inf^4)^(1/4)   [thin-insulator limit]
    T2  R -> infinity is also "thick": the pinned cold face never moves off
           T_init, and the profile's cold end stays at T_init.
    T3  A1 homogeneous ply under A2 has the closed-form solution
           T(z) = T_s + (T_init - T_s) * z/L.
    T4  R -> 0 forces T_s -> T_init: the slab goes isothermal, and the
           conductive share of the flux,
           (T_s - T_back)/(q*R), rises to 1 as radiation becomes negligible.
    T5  A4: permuting the ply stack leaves T_s, T_back and R_total invariant,
       and leaves the temperature-versus-resistance curve invariant (it does
       NOT leave temperature-versus-depth invariant -- that is reported, not
       asserted, because the ply interfaces physically move in z).

CITATIONS
    [1] Sutton, K. & Graves, A.G. (1972), NASA TR R-376, "A general
        stagnation-point convective heating equation for arbitrary gas
        mixtures" -- the Q_SG magnitude driving every case below.
    [2] Baumeister, P.K. (2006), Ch. 4 (composite-wall series resistance)
        and Ch. 11 (radiation boundary condition) -- A1, A3, T3.
    [3] Rapisarda 2023 Table 4.17 == NASA/TM-20110012051 Table 5 -- the F-TPS
        layup this file validates (two Nicalon SiC plies / two Pyrogel 3350
        plies / Kapton gas barrier, 7.131 mm total). Dillman et al., AIAA
        2014-4141 documents the OLD IRVE-3 flown layup this replaces (two
        Nextel BF-20 plies / two Pyrogel 3350 plies / aluminized-Kapton-Kevlar
        barrier, ~1/4 in total); https://ntrs.nasa.gov/citations/20140000147
    [4] IEEE 754-2019 -- T_Surface/T_Back cross the C ABI as Ada Float
        (binary32, 24-bit significand), so exactness assertions use a
        relative tolerance of ~1.2e-7 rather than 1e-9.
    [5] ctypes -- https://docs.python.org/3/library/ctypes.html
"""

from __future__ import annotations

import math
import os
import sys
from collections.abc import Callable, Sequence
from itertools import pairwise, permutations
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC_PY = os.path.normpath(os.path.join(_HERE, "..", "src", "python"))
if _SRC_PY not in sys.path:
    sys.path.insert(0, _SRC_PY)

import ada_pinn_wrapper as W  # imported after the sys.path insert above

# ----------------------------------------------------------------------------
# Physical constants and the flight condition that drives every case.
# SIGMA is duplicated here DELIBERATELY: the analytic references must not be
# imported from the solver, or the limits would validate the code against
# itself. It is checked against the Ada value at startup instead.
# ----------------------------------------------------------------------------
SIGMA_ST_SB = 5.670374419e-8   # Stefan-Boltzmann [W/(m^2*K^4)] [1]
EPS = 0.85                     # harness hot-face emissivity [dimensionless]
T_INIT = 293.15                # pinned cold-face temperature [K]
T_INF = 100.0                  # radiative ambient (cold stream) [K]

# Step-2200 flight condition: h = 51.8 km, V = 3378 m/s. Q_SG is obtained from
# the Ada FFI (Sutton_Graves_Heat_C) so Python never re-implements SG.
STEP2200_ALT_KM = 51.8
STEP2200_VEL_MS = 3378.0
# Rn = 1.5 m is the wrapper's documented nose-radius default; the ISA density
# at the altitude comes from the same Ada atmosphere entry point.
Q_SG = float(W.sutton_graves_heat_flux(
    STEP2200_ALT_KM, STEP2200_VEL_MS)["heat_flux_Wm2"])

# The F-TPS layup, hot face first [3].
#
# SINGLE-SOURCED from the Ada preset via the Python wrapper. This file used to
# hard-code `IRVE3_K = (0.25, 0.25, ...)`, i.e. the same stale Nextel k and the
# same superseded grade that the orphan `tps_step2200_layers.csv` carried: a
# layup change could be fully applied in the solver and still leave this
# validator checking a stack that no longer exists. A text literal in a
# validation script is exactly as authoritative as a column in a writer-less
# CSV -- which is to say, not at all.
# [3] Rapisarda 2023 Table 4.17 == NASA/TM-20110012051 Table 5;
#     stellarorion_types.ads TPS_Layup_IRVE3.
IRVE3_THICKNESS = tuple(W.IRVE3_FTPS_PLY_THICKNESS_M)
IRVE3_K = tuple(W.IRVE3_FTPS_PLY_THERMAL_K)
# Per-ply maximum continuous-use temperature [K] -- ply capability, NOT the
# 523.15 K structure limit. Rapisarda 2023 Table B.17.
IRVE3_PLY_TMAX_K = tuple(W.IRVE3_FTPS_PLY_TMAX_K)

# binary32 round-trip tolerance for values crossing the C ABI as Ada Float [4].
RTOL_F32 = 1.2e-7


# ----------------------------------------------------------------------------
# Thin helpers
# ----------------------------------------------------------------------------
def solve(
    thickness: Sequence[float],
    k: Sequence[float],
    *,
    q_sg: float = Q_SG,
    emissivity: float = EPS,
    t_init: float = T_INIT,
    t_inf: float = T_INF,
) -> dict[str, Any]:
    """Run one element solve through the Ada FFI wrapper.

    The Sutton-Graves reconstruction ratio Ke_Raw/Ke_Ref is set to exactly 1.0
    so the solver receives q = q_sg: every limit below is about the conduction
    and radiation response to a KNOWN flux, not about the reconstruction, which
    is exercised separately by the step-2200 driver.
    """
    return W.tps_conduction(
        q_sg_scale=q_sg,
        ke_raw=q_sg,
        ke_ref=q_sg,
        ply_thickness=thickness,
        ply_thermal_k=k,
        emissivity=emissivity,
        t_init=t_init,
        t_inf=t_inf,
    )


def radiative_equilibrium(q_sg: float, eps: float, t_inf: float) -> float:
    """T_s when the conduction term vanishes: (q/(eps*sigma) + T_inf^4)^(1/4)."""
    return (q_sg / (eps * SIGMA_ST_SB) + t_inf ** 4) ** 0.25


def series_r(thickness: Sequence[float], k: Sequence[float]) -> float:
    """Series thermal resistance of a ply stack [m^2*K/W] (axiom A4)."""
    return sum(t / kk for t, kk in zip(thickness, k))


class Report:
    """Collects per-check outcomes and prints a final verdict."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, label: str, ok: bool, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {label}" + (f"  --  {detail}" if detail else ""))
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        return ok


# ----------------------------------------------------------------------------
# Limit 1 -- thin-insulator / radiative-equilibrium limit  (theory T1)
# ----------------------------------------------------------------------------
def limit_1(r: Report) -> None:
    """T_s -> (q/(eps*sigma) + T_inf^4)^(1/4) as the stack's resistance grows.

    A thin, very low-conductivity ply is the physical realisation: the stack
    conducts so little that the hot face sits at radiative equilibrium. R is
    swept over three decades by moving k (the thickness stays at the 1 m
    envelope maximum) so the conduction term eps-free sweeps from significant
    to negligible while staying inside the FFI envelope (k >= 1e-3 W/(m*K)).
    """
    print("LIMIT 1  thin-insulator / radiative equilibrium")
    t_ref = radiative_equilibrium(Q_SG, EPS, T_INF)
    print(f"  reference T_rad = (q/(eps*sigma) + T_inf^4)^(1/4) = {t_ref:.4f} K")
    print(f"  driven by       q_SG = {Q_SG:.1f} W/m^2 "
          f"(Sutton-Graves at h={STEP2200_ALT_KM} km, V={STEP2200_VEL_MS} m/s)")

    dev: list[float] = []
    temps: list[float] = []
    iters: list[int] = []
    for k_val in (1.0, 1.0e-1, 1.0e-2, 1.0e-3):
        res = solve((1.0,), (k_val,))
        r_tot = series_r((1.0,), (k_val,))
        t_s = res["t_surface"]
        rel = abs(t_s - t_ref) / t_ref
        dev.append(rel)
        temps.append(t_s)
        iters.append(res["n_iterations"])
        print(f"    R = {r_tot:9.1f} m^2*K/W (k = {k_val:.0e})  "
              f"T_s = {t_s:9.3f} K  rel.dev = {rel:.3e}  "
              f"iters = {res['n_iterations']}")

    r.check("T_s rises monotonically toward T_rad as R grows",
            all(b > a for a, b in pairwise(temps)),
            " / ".join(f"{t:.2f}" for t in temps))
    r.check("relative deviation shrinks monotonically as R grows",
            all(b < a for a, b in pairwise(dev)),
            " / ".join(f"{d:.2e}" for d in dev))
    r.check("at R = 1000 m^2*K/W, T_s matches T_rad to < 1e-5 relative",
            dev[-1] < 1.0e-5, f"rel.dev = {dev[-1]:.3e}")
    r.check("bisection converged in every case (below the 120-iteration cap)",
            all(0 < n < 120 for n in iters),
            "iterations = " + " / ".join(str(n) for n in iters))


# ----------------------------------------------------------------------------
# Limit 2 -- thick-layer limit: the cold face stays at T_init  (theory T2)
# ----------------------------------------------------------------------------
def limit_2(r: Report) -> None:
    """T_back -> T_init, and stays there as the stack gets thicker.

    The model pins the cold face (axiom A2), so T_back is T_init for EVERY
    stack; what thickness changes is whether the deep interior has already
    collapsed onto T_init. Scaling the IRVE-3 plies by 1x .. 100x keeps every
    ply inside the envelope (thickest ply 0.25 m <= 1 m) and shows the cold end
    of the profile pinned while the hot end stays at T_s.
    """
    print("LIMIT 2  thick layer: T_back -> T_init")
    for factor in (1, 10, 100):
        thick = tuple(t * factor for t in IRVE3_THICKNESS)
        res = solve(thick, IRVE3_K)
        back = res["t_back"]
        prof_back = res["profile_temp"][-1]
        depth_last = res["profile_depth_m"][-1]
        total = res["total_thickness_m"]
        print(f"    x{factor:<4d} thickness = {total:.5f} m  T_back = {back:.6f} K  "
              f"profile[last] = {prof_back:.6f} K  (depth {depth_last:.5f} m)")
        r.check(f"x{factor}: T_back == T_init within binary32 tolerance",
                abs(back - T_INIT) <= RTOL_F32 * T_INIT,
                f"|dT| = {abs(back - T_INIT):.3e} K")
        r.check(f"x{factor}: profile's cold-face sample == T_init",
                abs(prof_back - T_INIT) <= RTOL_F32 * T_INIT,
                f"|dT| = {abs(prof_back - T_INIT):.3e} K")
        r.check(f"x{factor}: last sample sits on the cold face in metres",
                abs(depth_last - total) <= RTOL_F32 * total,
                f"depth = {depth_last:.6f} m vs total = {total:.6f} m")
        r.check(f"x{factor}: profile axis spans 0 .. total thickness",
                abs(res["profile_depth_m"][0]) <= RTOL_F32 * total,
                f"first depth = {res['profile_depth_m'][0]:.3e} m")


# ----------------------------------------------------------------------------
# Limit 3 -- single-layer closed form  (theory T3)
# ----------------------------------------------------------------------------
def limit_3(r: Report) -> None:
    """One homogeneous ply under the pinned cold face is exactly LINEAR in z.

    This is the model's own closed-form solution (axiom A3 with constant k), so
    it is asserted to near-exactness. The semi-infinite exponential is a
    DIFFERENT boundary condition -- insulated/semi-infinite cold side instead
    of the pinned T_init -- so its deviation is reported for information and is
    deliberately NOT asserted: asserting it would be testing a model the
    solver does not claim to implement.
    """
    print("LIMIT 3  single-layer closed form")
    thickness, k_val = 0.01, 0.05     # R = 0.2 m^2*K/W: a real, resolvable drop
    res = solve((thickness,), (k_val,))
    t_s, t_back = res["t_surface"], res["t_back"]
    depth, temp = res["profile_depth_m"], res["profile_temp"]
    r_tot = series_r((thickness,), (k_val,))

    print(f"    single ply: L = {thickness} m, k = {k_val} W/(m*K), "
          f"R = {r_tot} m^2*K/W")
    print(f"    T_s = {t_s:.4f} K, T_back = {t_back:.4f} K, "
          f"q*R = {Q_SG * r_tot:.1f} K (conduction drop)")

    max_dev = 0.0
    for z, t in zip(depth, temp):
        t_exact = t_s + (t_back - t_s) * (z / thickness)
        max_dev = max(max_dev, abs(t - t_exact))
    r.check("profile matches the closed-form linear solution to < 1e-3 K",
            max_dev < 1.0e-3, f"max |deviation| = {max_dev:.3e} K")

    # Reported, not asserted: the semi-infinite exponential belongs to a
    # different (unpinned) cold-side boundary condition. ell = L is stated
    # explicitly so the number is reproducible and not mistaken for a
    # fitted length scale.
    rms_exp = math.sqrt(sum(
        (t - (t_back + (t_s - t_back) * math.exp(-z / thickness))) ** 2
        for z, t in zip(depth, temp)) / len(depth))
    print(f"    INFO (not asserted): RMS deviation from the semi-infinite "
          f"exp(-z/L) form = {rms_exp:.2f} K. That form solves a DIFFERENT")
    print( "           boundary condition (insulated / semi-infinite cold")
    print( "           side). This model pins T(L) = T_init by axiom A2, so")
    print( "           a large deviation here is expected and is not a defect.")

    t_rad = radiative_equilibrium(Q_SG, EPS, T_INF)
    # Conduction carries part of the flux INTO the stack, so less is left to
    # radiate and the hot face must sit BELOW the pure-radiative temperature.
    # (The naive "T_s - T_back < T_rad - T_s" comparison is meaningless: the
    # two drops live in different energy channels, not on one temperature
    # ladder. The balance-closure check in abi_checks is the sharp test.)
    r.check("T_s sits below the pure-radiative temperature (conduction removes "
            "part of the flux from the surface)",
            t_s < t_rad,
            f"T_s = {t_s:.3f} K < T_rad = {t_rad:.3f} K "
            f"(deficit {t_rad - t_s:.3f} K)")


# ----------------------------------------------------------------------------
# Limit 4 -- isothermal limit, k -> infinity  (theory T4)
# ----------------------------------------------------------------------------
def limit_4(r: Report) -> None:
    """R -> 0 forces T_s -> T_init: the slab becomes isothermal.

    Sweeping k over three decades at fixed thickness drives R from 1e-2 down to
    1e-5 m^2*K/W. The envelope caps k at 1e3 W/(m*K), so the sweep stops there
    and the residual spread is reported rather than extrapolated -- the limit is
    approached, never reached, and saying so is part of the result.
    """
    print("LIMIT 4  isothermal limit (k -> infinity, R -> 0)")
    thickness = 0.01
    spreads: list[float] = []
    ratios: list[float] = []
    temps: list[float] = []
    for k_val in (1.0, 10.0, 100.0, 1000.0):
        res = solve((thickness,), (k_val,))
        r_tot = series_r((thickness,), (k_val,))
        temp = res["profile_temp"]
        spread = max(temp) - min(temp)
        ratio = (res["t_surface"] - res["t_back"]) / (Q_SG * r_tot)
        spreads.append(spread)
        ratios.append(ratio)
        temps.append(res["t_surface"])
        print(f"    k = {k_val:7.1f} W/(m*K)  R = {r_tot:.1e} m^2*K/W  "
              f"T_s = {res['t_surface']:8.3f} K  profile spread = {spread:8.3f} K  "
              f"(T_s-T_back)/(q*R) = {ratio:.6f}")

    r.check("profile spread shrinks monotonically as k grows",
            all(b < a for a, b in pairwise(spreads)),
            " / ".join(f"{s:.2f}" for s in spreads))
    r.check("T_s falls monotonically toward T_init as k grows",
            all(b < a for a, b in pairwise(temps)),
            " / ".join(f"{t:.2f}" for t in temps))
    r.check("conductive share of the flux rises toward 1 and never exceeds it",
            all(b >= a for a, b in pairwise(ratios))
            and max(ratios) <= 1.0 + 1.0e-6,
            " / ".join(f"{x:.6f}" for x in ratios))
    r.check("at k = 1000 W/(m*K) the slab is near-isothermal (spread < 5 K)",
            spreads[-1] < 5.0, f"spread = {spreads[-1]:.3f} K")
    print("    NOTE: the FFI envelope caps k at 1e3 W/(m*K), so this is an")
    print( "          approach to the limit, not a limit that is reached.")


# ----------------------------------------------------------------------------
# Limit 5 -- layer-permutation invariance  (theory T5)
# ----------------------------------------------------------------------------
def _analytic_at_depths(
    thickness: Sequence[float],
    k: Sequence[float],
    t_s: float,
    t_back: float,
    depths: Sequence[float],
) -> list[float]:
    """Exact piecewise-linear profile of a serial ply stack, at given depths.

    Implements axiom A3 directly -- temperature is linear in ACCUMULATED
    THERMAL RESISTANCE, not in depth -- and returns
    ``T(z) = T_s - (T_s - T_Back) * R(0..z)/R_total``. This is the closed-form
    solution of the model; it contains no fitting, no interpolation between
    solver samples and no assumption about where the solver chose to sample.
    """
    resistances = [t / kk for t, kk in zip(thickness, k)]
    total = sum(resistances)
    # Cumulative DEPTH boundaries locate the ply that owns a sample...
    depth_edges = [0.0]
    for t_i in thickness:
        depth_edges.append(depth_edges[-1] + t_i)
    # ...while cumulative RESISTANCE is the abscissa the profile is linear in.
    res_edges = [0.0]
    for r_i in resistances:
        res_edges.append(res_edges[-1] + r_i)
    out: list[float] = []
    for z in depths:
        idx = len(thickness) - 1
        for i, t_i in enumerate(thickness):
            if z <= depth_edges[i + 1]:
                idx = i
                break
        local = min(max(z - depth_edges[idx], 0.0), thickness[idx])
        # Within a ply, resistance grows linearly with depth at rate 1/k, so
        # R(0..z) = R_prefix + local / k_idx.
        acc = res_edges[idx] + local / k[idx]
        out.append(t_s - (t_s - t_back) * (acc / total))
    return out


def limit_5(r: Report) -> None:
    """All 120 orderings of the 5-ply IRVE-3 stack give the same physics.

    R_total is a sum of ply resistances (axiom A4), so T_s and T_back cannot
    depend on order. The temperature-vs-resistance curve is likewise invariant.
    The temperature-vs-DEPTH curve is NOT, and is reported -- the ply
    interfaces physically sit at different depths when the stack is reordered,
    which is a real effect rather than a solver artefact.
    """
    print("LIMIT 5  layer-permutation invariance (5 plies -> 120 orderings)")
    base = solve(IRVE3_THICKNESS, IRVE3_K)
    r_ref = base["series_resistance_m2K_W"]

    worst_ts = worst_tb = worst_r = worst_curve = 0.0
    worst_depth_profile = 0.0
    count = 0
    for perm in permutations(range(len(IRVE3_THICKNESS))):
        count += 1
        thick = tuple(IRVE3_THICKNESS[i] for i in perm)
        kk = tuple(IRVE3_K[i] for i in perm)
        res = solve(thick, kk)
        worst_ts = max(worst_ts, abs(res["t_surface"] - base["t_surface"]))
        worst_tb = max(worst_tb, abs(res["t_back"] - base["t_back"]))
        worst_r = max(worst_r, abs(res["series_resistance_m2K_W"] - r_ref))
        # The solver's profile is compared against the model's exact
        # closed form AT THE SOLVER'S OWN SAMPLE DEPTHS. That keeps the test a
        # test of the solver rather than of an interpolator: re-sampling onto
        # a common abscissa would fold in the 33-sample grid's own error
        # (the IRVE-3 interfaces at 0.6/1.2/3.7/6.2 mm do not land on the
        # 0.198 mm grid), which is a sampling artefact, not a physics one.
        exact = _analytic_at_depths(thick, kk, res["t_surface"],
                                    res["t_back"], res["profile_depth_m"])
        worst_curve = max(worst_curve, max(
            abs(a - b) for a, b in zip(res["profile_temp"], exact)))
        worst_depth_profile = max(
            worst_depth_profile,
            max(abs(a - b) for a, b in zip(res["profile_temp"],
                                           base["profile_temp"])))
    print(f"    orderings tested: {count}   R_total = {r_ref:.9f} m^2*K/W")
    print(f"    worst |dT_s| = {worst_ts:.3e} K   worst |dT_back| = {worst_tb:.3e} K")
    print(f"    worst |dR| = {worst_r:.3e} m^2*K/W")
    print(f"    worst |deviation from the model's closed form, over ALL "
          f"orderings and all 33 samples = {worst_curve:.3e} K")
    print(f"    worst |dT| between reordered DEPTH profiles = "
          f"{worst_depth_profile:.3e} K (expected non-zero: the ply")
    print( "          interfaces physically move in z when the stack is")
    print( "          reordered, so only the resistance-parametrised curve,")
    print( "          not the depth-parametrised one, can be invariant)")

    r.check("T_s is permutation-invariant over all 120 orderings",
            worst_ts <= RTOL_F32 * max(1.0, base["t_surface"]),
            f"worst |dT_s| = {worst_ts:.3e} K")
    r.check("T_back is permutation-invariant over all 120 orderings",
            worst_tb <= RTOL_F32 * T_INIT,
            f"worst |dT_back| = {worst_tb:.3e} K")
    r.check("R_total is permutation-invariant over all 120 orderings",
            worst_r <= RTOL_F32 * r_ref,
            f"worst |dR| = {worst_r:.3e} m^2*K/W")
    r.check("every ordering's profile matches the order-independent closed "
            "form in resistance (hence the curve is permutation-invariant)",
            worst_curve <= 1.0e-3,
            f"worst |deviation| = {worst_curve:.3e} K")


# ----------------------------------------------------------------------------
# Cross-cutting consistency checks on the exposed ABI
# ----------------------------------------------------------------------------
def abi_checks(r: Report) -> None:
    """The FFI must expose q_SG, T_s, T_back and the 33-point profile."""
    res = solve(IRVE3_THICKNESS, IRVE3_K)
    r_tot = res["series_resistance_m2K_W"]
    print("ABI exposure (TPS_Conduction_C outputs)")
    print(f"    q_SG = {res['q_sg']:.1f} W/m^2   T_s = {res['t_surface']:.3f} K   "
          f"T_back = {res['t_back']:.3f} K")
    print(f"    profile samples = {len(res['profile_temp'])}  "
          f"depth span = {res['profile_depth_m'][0]:.3e} .. "
          f"{res['profile_depth_m'][-1]:.6f} m  "
          f"total_thickness = {res['total_thickness_m']:.6f} m")

    r.check("q_SG is returned and equals the calibrated input flux",
            abs(res["q_sg"] - Q_SG) <= RTOL_F32 * Q_SG,
            f"q_SG = {res['q_sg']:.4f} vs {Q_SG:.4f} W/m^2")
    r.check("profile carries exactly Max_Profile_Points = 33 samples",
            len(res["profile_temp"]) == W.TPS_PROFILE_SAMPLES == 33
            and len(res["profile_depth_m"]) == 33,
            f"{len(res['profile_temp'])} samples")
    r.check("T_s > T_back (heat flows inward)",
            res["t_surface"] > res["t_back"],
            f"{res['t_surface']:.2f} K > {res['t_back']:.2f} K")
    r.check("T_s - T_back never exceeds the pure-conduction bound q*R",
            (res["t_surface"] - res["t_back"]) <= Q_SG * r_tot * (1.0 + 1.0e-6),
            f"{res['t_surface'] - res['t_back']:.2f} K <= "
            f"{Q_SG * r_tot:.2f} K")
    r.check("the profile decreases monotonically from hot face to cold face",
            all(b <= a + 1.0e-4 for a, b in zip(res["profile_temp"],
                                                res["profile_temp"][1:])),
            "no interior temperature rise")
    r.check("IRVE-3 layup total thickness is 6.35 mm = 1/4 in",
            abs(res["total_thickness_m"] - 0.00635) <= 1.0e-9,
            f"{res['total_thickness_m']:.8f} m")
    r.check("bisection converged below the 120-iteration cap",
            0 < res["n_iterations"] < 120,
            f"n_iterations = {res['n_iterations']}")

    # Sharpest single test of the whole model: the solver's answer must close
    # axiom A1's energy balance to the precision of binary32 arithmetic.
    # TOLERANCE DERIVATION (not a fudge factor). T_Surface and T_Back cross
    # the C ABI as Ada Float (binary32) [4], so each carries a relative error
    # of order RTOL_F32. The radiative term inherits ~4*RTOL_F32 through
    # T^4; the conductive term inherits RTOL_F32/|1 - T_back/T_surface|, which
    # BLOWS UP as the slab becomes isothermal -- at k = 1000 W/(m*K) the
    # conductive drop is q*R = 1.61 K expressed as a difference of two
    # ~294 K binary32 values, i.e. ~3e-5 K of absolute rounding on a 1.6 K
    # span, ~2e-5 relative. The achievable bound is therefore computed
    # per case, and the check demands the residual actually stay under it.
    balance_ok = True
    cases = [
        ("IRVE-3 5-ply", IRVE3_THICKNESS, IRVE3_K),
        ("single ply R=0.2", (0.01,), (0.05,)),
        ("insulator R=1000", (1.0,), (1.0e-3,)),
        ("near-isothermal", (0.01,), (1000.0,)),
    ]
    for label, thick, kk in cases:
        case = solve(thick, kk)
        rr = case["series_resistance_m2K_W"]
        ts, tb = case["t_surface"], case["t_back"]
        conductive = (ts - tb) / rr
        radiated = EPS * SIGMA_ST_SB * (ts ** 4 - T_INF ** 4)
        residual = abs(conductive + radiated - Q_SG) / Q_SG
        drop = max(abs(ts - tb), 1.0e-30)
        bound = max(1.0e-6,
                    8.0 * RTOL_F32,
                    8.0 * RTOL_F32 * max(ts, tb) / drop)
        print(f"    {label:<20s} R = {rr:10.5f} m^2*K/W  "
              f"conductive = {conductive:11.2f}  radiated = {radiated:11.2f}  "
              f"residual = {residual:.2e}  binary32 bound = {bound:.2e}")
        # Per case, against ITS OWN derived bound: pairing the worst residual
        # with the smallest bound would compare numbers from different cases.
        balance_ok = balance_ok and residual <= bound
    r.check("steady surface balance closes within each case's binary32-derived "
            "bound (q = (T_s-T_back)/R + eps*sigma*(T_s^4 - T_inf^4))",
            balance_ok,
            "residuals and bounds printed above, case by case")


# ----------------------------------------------------------------------------
def main() -> int:
    print("=" * 78)
    print("Composite F-TPS conduction solver -- limit validation")
    print("  solver   : StellarOrion_Physics.TPS_Conduction_C (Ada/SPARK)")
    print("  wrapper  : src/python/ada_pinn_wrapper.py::tps_conduction")
    print("  layup    : F-TPS (Nicalon SiC x2 / Pyrogel 3350 x2 / Kapton), "
          "Rapisarda 2023 Table 4.17 == NASA/TM-20110012051 Table 5")
    print(f"  library  : {W._LIB_NAME}")
    print("=" * 78)
    print(f"Stefan-Boltzmann used for the analytic references: "
          f"{SIGMA_ST_SB:.9e} W/(m^2*K^4)")

    limits: list[Callable[[Report], None]] = [
        limit_1, limit_2, limit_3, limit_4, limit_5,
    ]
    report = Report()
    for fn in limits:
        fn(report)
        print()
    abi_checks(report)
    print()
    print("=" * 78)
    print(f"TOTAL: {report.passed} checks passed, {report.failed} failed")
    if report.failed == 0:
        print("VERDICT: ALL 5 LIMITS PASS (plus the ABI exposure checks)")
        print("=" * 78)
        return 0
    print("VERDICT: FAILURE -- at least one limit did not hold")
    print("=" * 78)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
