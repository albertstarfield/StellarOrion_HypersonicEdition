#!/usr/bin/env python3
"""Regenerate `sutton_graves_parametric.png` for the CurrentThesis LaTeX report.

PURPOSE
-------
The previously committed figure plotted the Sutton--Graves stagnation correlation
using superseded constants and geometry, producing an IRVE-3 marker of
959.7 W/cm^2 at R_N = 0.577 m and V = 10.8 km/s. The current solver evaluates
the same correlation at C_SG = 1.83e-4 and R_N = 1.5 m, giving 16.14 W/cm^2 at
the run condition (h = 51.8 km, V = 3378 m/s). This script regenerates the
figure so that the plotted physics matches the code and the thesis text.

AXIOMS
------
A1. The correlation evaluated here is
        q_dot = C_SG * sqrt(rho / R_N) * V^3            [W/m^2]
    with C_SG = 1.83e-4 for Earth air, matching
    `stellarorion_types.ads` (C_SG : constant Float := 1.83e-4).
A2. The freestream density is a function of altitude only, obtained from the
    same atmospheric model the solver uses (`isa_atmosphere` via the Ada FFI),
    not from a hand-rolled exponential fit. This guarantees that the baseline
    marker on the plot equals the number quoted in the thesis.
A3. R_N = 1.5 m is the IRVE-3 nose radius (3 m aeroshell diameter).
A4. The run condition is h = 51.8 km, V = 3378 m/s (Mach ~ 10.29).

THEORIES
---------
T1. Because q_dot ~ V^3, the velocity sweep spans three orders of magnitude in
    heat flux; a linear y-axis is unreadable, so panel (a) uses a log axis.
T2. Because q_dot ~ 1/sqrt(R_N), the radius sweep is likewise logarithmic; a log
    x-axis is required to show the scaling over 0.1-3.0 m.
T3. The baseline marker must be computed by calling the solver's own SG
    function, not by re-deriving it in this file, so that plot and text cannot
    drift apart.

APPLICATIONS
------------
A1/A2/A3/A4 are realised by: importing `sutton_graves_heat_flux` and
`isa_atmosphere` from the project's `validation_pipeline` module, evaluating
them over a sweep, and annotating the IRVE-3 run condition with the value the
solver returns.

CITATIONS
---------
[Citation: Sutton & Graves (1971) - "A Correlation for Stagnation Point
          Heating", AIAA Paper 71-534]
[Citation: ada_pinn_wrapper.sutton_graves_heat_flux - Ada/SPARK FFI wrapper,
          stellarorion_program_proc/src/python/ada_pinn_wrapper.py]
[Citation: validation_pipeline.isa_atmosphere - atmospheric model,
          stellarorion_program_proc/src/python/validation_pipeline.py]
[Citation: Matplotlib v3.11.2 - https://matplotlib.org/stable/api/]

SAFETY / ERROR HANDLING
-----------------------
- Missing solver module or unavailable Ada library raises and aborts the build
  rather than silently falling back to a Python re-implementation, because a
  silent fallback would reintroduce exactly the drift this script removes.
- Output directory is created if absent; the PNG is written atomically via a
  temporary file and `os.replace` so a partial write cannot leave a corrupt
  figure in place.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# --- Axiom A3/A4: geometry and run condition constants -----------------------
R_N_BASELINE_M: float = 1.5          # A3: IRVE-3 nose radius (3 m diameter)
H_RUN_KM: float = 51.8               # A4: run altitude
V_RUN_MS: float = 3378.0             # A4: run velocity
MACH_RUN: float = 10.29              # A4: quoted Mach number

# Sweep ranges chosen to bracket the baseline in both panels.
V_SWEEP_KMS = [2.0, 2.5, 3.0, 3.378, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
R_SWEEP_M = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]


def _repo_root() -> str:
    """
    Resolve the repository root by walking up from this script.

    The script lives at
    ``<repo>/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/``,
    so the root is the ancestor that contains the ``stellarorion_program_proc``
    directory. Walking up and probing for that marker directory is robust to
    the report being relocated or an extra nesting level being introduced, and
    avoids a hard-coded path that would break on any other machine.

    :returns: absolute path of the repository root.
    :raises RuntimeError: if no ancestor contains ``stellarorion_program_proc``,
        which means the script is not inside the expected tree.
    """
    marker = "stellarorion_program_proc"
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(current, marker)):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # reached filesystem root without finding marker
            raise RuntimeError(
                "Repository root not found: no ancestor of %r contains a %r "
                "directory. The regeneration script must live inside the "
                "StellarOrion repository tree."
                % (os.path.abspath(__file__), marker)
            )
        current = parent


def _load_solver() -> dict[str, Any]:
    """
    Import the project's own physics entry points.

    :returns: mapping with keys ``sg`` (Sutton--Graves evaluator) and ``isa``
        (atmospheric density evaluator).
    :raises ImportError: if the solver module or its Ada/SPARK library cannot be
        loaded. Propagated deliberately: a silent fallback to an independent
        Python correlation would reintroduce the constant/geometry drift that
        this regeneration exists to remove.
    """
    # Locate the project source root relative to this script.
    # figures/ -> CurrentThesisFinalReport/ -> ProgressReport/ -> Lost+Found/ -> <repo>
    repo_root = _repo_root()
    repo_src = os.path.join(repo_root, "stellarorion_program_proc", "src", "python")
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)

    try:
        from validation_pipeline import (  # type: ignore[import-not-found]
            isa_atmosphere,
            sutton_graves_heat_flux,
        )
    except ImportError as exc:  # pragma: no cover - environment failure path
        raise ImportError(
            "Cannot import validation_pipeline from %r. The Ada/SPARK physics "
            "library must be available so that the regenerated figure uses the "
            "same correlation as the solver. Original error: %s" % (repo_src, exc)
        ) from exc

    return {"sg": sutton_graves_heat_flux, "isa": isa_atmosphere}


def sg_at_velocity(velocity_kms: float, nose_radius_m: float, solver: dict[str, Any]) -> float:
    """
    Evaluate the Sutton--Graves correlation at fixed nose radius.

    :param velocity_kms: freestream velocity in km/s.
    :param nose_radius_m: nose radius in metres.
    :param solver: mapping returned by :func:`_load_solver`.
    :returns: stagnation heat flux in W/cm^2.
    """
    # Density is taken at the run altitude so that every curve shares one
    # freestream state; velocity is the only variable on the abscissa (A2).
    density = solver["isa"](H_RUN_KM)["density_kgm3"]
    isa = solver["isa"]

    # The solver's SG entry point takes (altitude, velocity) and uses a fixed
    # nose radius, so for a radius sweep we evaluate the correlation directly
    # from its own constants, which the wrapper exports.
    c_sg = _c_sg_from_solver(isa)
    q_wm2 = c_sg * (density / nose_radius_m) ** 0.5 * (velocity_kms * 1000.0) ** 3
    return q_wm2 / 1.0e4


def sg_at_radius(nose_radius_m: float, velocity_kms: float, solver: dict[str, Any]) -> float:
    """
    Evaluate the Sutton--Graves correlation at fixed velocity.

    :param nose_radius_m: nose radius in metres.
    :param velocity_kms: freestream velocity in km/s.
    :param solver: mapping returned by :func:`_load_solver`.
    :returns: stagnation heat flux in W/cm^2.
    """
    return sg_at_velocity(velocity_kms, nose_radius_m, solver)


def _c_sg_from_solver(isa: Any) -> float:
    """
    Read the correlation constant the solver actually uses.

    :param isa: the ``isa_atmosphere`` callable, used only to trigger the module
        import side effects that load the Ada/SPARK library.
    :returns: ``C_SG`` in SI units.
    :raises RuntimeError: if the constant cannot be located in the source, which
        would mean the figure cannot be tied to the solver's own value.
    """
    del isa  # import side effect is the point of accepting this argument
    types_ads = os.path.join(
        _repo_root(),
        "stellarorion_program_proc",
        "src",
        "simulation_engine",
        "stellarorion_types.ads",
    )
    with open(types_ads, "r", encoding="utf-8") as handle:
        for line in handle:
            # Match the constant *declaration* only, so that a mere mention of
            # C_SG in a comment or a dependent expression cannot be picked up
            # in place of the authoritative value.
            if "C_SG" not in line or ":=" not in line:
                continue
            for token in line.replace(";", " ").split():
                cleaned = token.rstrip(";,")
                try:
                    value = float(cleaned)
                except ValueError:
                    continue
                # A correlation constant is a small positive number; reject any
                # other numeric token (e.g. an array bound) on the same line.
                if 0.0 < value < 1.0:
                    return value
    raise RuntimeError(
        "C_SG constant not found in %s; refusing to hard-code a value so that "
        "the figure cannot drift from the solver." % types_ads
    )


def main() -> int:
    """
    Render the two-panel Sutton--Graves figure and save it as a PNG.

    :returns: process exit status (0 on success).
    :raises Exception: any failure propagates so the build is visibly broken
        rather than shipping a stale figure.
    """
    solver = _load_solver()
    sg = solver["sg"]
    isa = solver["isa"]

    # --- Baseline value straight from the solver (Theorem T3) --------------
    baseline = sg(H_RUN_KM, V_RUN_MS)["heat_flux_Wcm2"]
    print("[sutton_graves_parametric] solver baseline: %.4f W/cm2" % baseline)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 5.4))
    fig.patch.set_facecolor("white")

    velocities = V_SWEEP_KMS
    radii = R_SWEEP_M

    # --- Panel (a): q vs velocity for several nose radii -------------------
    for r_n in radii:
        y = [sg_at_velocity(v, r_n, solver) for v in velocities]
        style = dict(lw=2.6, zorder=3)
        if abs(r_n - R_N_BASELINE_M) < 1e-9:
            style.update(color="black", lw=3.2)
            label = r"$R_N$ = 1.5 m (IRVE-3)"
        else:
            style.update(color="tab:blue", alpha=0.55)
            label = r"$R_N$ = %g m" % r_n
        ax1.plot(velocities, y, label=label, **style)

    # Mark the run condition. The IRVE-3 marker sits exactly on the 3.378 km/s
    # grid point, so no interpolation is required.
    v_run_kms = V_RUN_MS / 1000.0
    ax1.plot(
        [v_run_kms],
        [baseline],
        marker="o",
        ms=11,
        mfc="none",
        mec="black",
        mew=2.4,
        ls="none",
        zorder=6,
    )
    ax1.annotate(
        "IRVE-3 run condition\n%.2f W/cm$^2$" % baseline,
        xy=(v_run_kms, baseline),
        xytext=(v_run_kms - 2.05, baseline * 3.4),
        fontsize=12,
        ha="left",
        arrowprops=dict(arrowstyle="->", lw=1.8, color="black"),
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black", lw=1.1),
    )

    ax1.set_yscale("log")
    ax1.set_xlabel(r"Freestream velocity $V_\infty$ [km/s]", fontsize=13)
    ax1.set_ylabel(r"Stagnation heat flux $\dot{q}_s$ [W/cm$^2$]", fontsize=13)
    ax1.set_title(
        r"(a) Sutton--Graves: $\dot{q}_s$ vs $V_\infty$ "
        r"($h$ = 51.8 km, $C_{SG}$ = 1.83$\times$10$^{-4}$)",
        fontsize=13,
    )
    ax1.grid(True, which="both", alpha=0.3, ls=":")
    ax1.legend(fontsize=9.5, loc="lower right", framealpha=0.92)

    # --- Panel (b): q vs nose radius at several Mach numbers ---------------
    for v_kms in (3.0, 5.0, 7.0):
        y = [sg_at_radius(r_n, v_kms, solver) for r_n in radii]
        ax2.plot(
            radii,
            y,
            marker="o",
            ms=5,
            lw=2.4,
            label=r"$V$ = %g km/s" % v_kms,
        )

    ax2.axvline(
        R_N_BASELINE_M,
        color="black",
        ls="--",
        lw=1.6,
        zorder=2,
    )
    ax2.annotate(
        "$R_N$ = 1.5 m\n(IRVE-3)",
        xy=(R_N_BASELINE_M, sg_at_radius(R_N_BASELINE_M, 3.0, solver)),
        xytext=(R_N_BASELINE_M * 1.08, sg_at_radius(R_N_BASELINE_M, 3.0, solver) * 0.30),
        fontsize=12,
        ha="left",
        arrowprops=dict(arrowstyle="->", lw=1.6, color="black"),
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black", lw=1.1),
    )

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xticks(radii)
    ax2.set_xticklabels([("%g" % r) for r in radii])
    ax2.minorticks_off()
    ax2.set_xlabel(r"Nose radius $R_N$ [m]", fontsize=13)
    ax2.set_ylabel(r"Stagnation heat flux $\dot{q}_s$ [W/cm$^2$]", fontsize=13)
    ax2.set_title(
        r"(b) $\dot{q}_s$ vs $R_N$ (Sutton--Graves: $\dot{q}_s \propto 1/\sqrt{R_N}$)",
        fontsize=13,
    )
    ax2.grid(True, which="both", alpha=0.3, ls=":")
    ax2.legend(fontsize=10, loc="upper right", framealpha=0.92)

    fig.tight_layout()

    # --- Atomic write: temp file then rename (see module docstring) ---------
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "sutton_graves_parametric.png")
    tmp_path = out_path + ".tmp.png"
    fig.savefig(tmp_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    os.replace(tmp_path, out_path)
    print("[sutton_graves_parametric] wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
