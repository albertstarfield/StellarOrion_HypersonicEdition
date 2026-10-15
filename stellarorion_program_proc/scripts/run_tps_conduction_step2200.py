#!/usr/bin/env python3
"""Per-element IRVE-3 F-TPS conduction solve over the step-2200 SPARTA snapshot.

WHAT THIS IS
    The driver the goal asks for: it walks every surface element of the
    step-2200 SPARTA snapshot, reconstructs that element's Sutton-Graves-scaled
    heat flux q_i, and calls the Ada/SPARK composite conduction solver once per
    element, reporting q_SG, T_s, T_back and the 33-point in-depth profile.

    Python is a WRAPPER here and nothing more (project rule: Ada/SPARK primary):
      * it reads the VTU file and marshals arrays,
      * it asks Ada for the Sutton-Graves magnitude and the atmosphere
        (``isa_atmosphere`` / ``sutton_graves_heat_flux`` -> Ada FFI),
      * it calls ``TPS_Conduction_C`` once per element through
        ``ada_pinn_wrapper.tps_conduction``,
      * it aggregates and prints. No conduction, radiation or scaling physics
        is implemented below: the q_i reconstruction itself lives in Ada
        (``StellarOrion_Physics.SG_Scaled_Element_Flux``), which is what the
        ``ke_raw`` / ``ke_ref`` arguments of the FFI entry select.

AXIOMS (all enforced in Ada; restated here as the driver's contract)
    A1  q_i = Q_SG * clamp(Ke_Raw_i / Ke_Ref, 0, 1)
        -- StellarOrion_Physics.SG_Scaled_Element_Flux. A negative Ke_Raw_i
        (DSMC single-cell noise; the snapshot contains real negative values)
        floors the ratio at 0 and yields q_i = 0 rather than heating the TPS
        backwards.
    A2  The layup is the F-TPS schedule the project runs (Rapisarda 2023
        Table 4.17 == NASA/TM-20110012051 Table 5), single-sourced from the
        Ada preset through the wrapper: two Nicalon SiC plies (0.506 mm),
        two Pyrogel 3350 plies (3.047 mm), one Kapton gas barrier (0.025 mm);
        total 7.131 mm; outer emissivity 0.80; structure limit
        523.15 K / 250 degC.
        NOT IRVE-3's flown hardware: IRVE-3 flew two Nextel BF-20 plies, two
        Pyrogel 3350 plies and an AKK barrier for a 6.35 mm total. This is the
        second-generation schedule Rapisarda recommends ("Nicalon SiC material
        is employed to replace Nextel for the outer layers") and the project
        runs by explicit owner decision (2026-10-14).
    A3  Only the step-2200 snapshot is admissible. Any other step is refused
        before a single solve runs.
    A4  Ke_Ref must be strictly positive: it is the divisor that maps the
        snapshot's hottest reading onto Q_SG. Zero would divide by zero, so
        the driver refuses rather than letting the FFI guess.

FLIGHT CONDITION
    The snapshot is the DESIGNATED VALIDATED REFERENCE, not the optimization
    gate's output.  `results/00_reference/` is the reference dataset
    every objective is measured against (hiad_optimizer.py axiom A2: "The
    reference data in results/00_reference/ is the source of every J(x)
    reference"), and `validation_timeseries.csv` records its own step-2200
    state directly:

        step 2200 : alt = 52.069210 km, V = 3101.079 m/s, M = 9.455298,
                    q_max = 1,920,170 W/m^2, q_avg = 552,002 W/m^2,
                    q_SG = 122,029 W/m^2, heat load = 165.716 J/cm^2

    Those two numbers are the CLI defaults below, taken FROM that file rather
    than asserted.  Corrected on 2026-10-14: the defaults previously read
    h = 51.8 km / V = 3378 m/s, which is the pair
    `Snapshot_Alt_Km`/`Snapshot_Vel_Ms` declare in
    stellarorion_optimization.ads:404-405 -- and which the reference DSMC run
    does NOT use.  Three different velocities have circulated for 51.8-52 km:
    3378 m/s (the Ada constants), 3101.079 m/s (the reference run's own
    step-2200 value, used here) and 2700 m/s (the scalloped DSMC deck).  The
    flight-condition question is OPEN; this driver now follows the reference
    dataset it actually reads, and says so, rather than quoting a constant
    from a different run.  Both remain CLI-overridable, so a change is a
    visible flag change and never a silent drift.

READING OF T_back (stated up front, because it is a model property)
    The solver imposes a steady-state Dirichlet condition on the cold face
    (T(L) = T_init, axiom A2 of the solver spec), so T_back equals T_init by
    construction. Its structure-limit check is therefore a restatement of the
    boundary condition, NOT an independent prediction. The physically
    informative number for the outer ply is T_s; both are reported, and the
    summary says which one carries information.

CITATIONS
    [1] Sutton, K. & Graves, A.G. (1972), NASA TR R-376 -- Q_SG magnitude.
    [2] NASA-TM-2012-011662 -- Nextel BF-20 rated to 30 W/cm^2 and Nicalon SiC
        to 50 W/cm^2; the 30 W/cm^2 1st-generation figure is still the reference
        the computed peak flux is compared against, so the comparison is
        deliberately conservative against the 2nd-generation cloth actually
        installed. Nicalon SiC conductivity 1.5 W/(m*K): cg-Nicalon fibre,
        UCLA/PNNL "Thermophysical and Mechanical Properties of SiC/SiC
        Composites" Table 1.
    [3] Dillman et al., AIAA 2014-4141 -- IRVE-3 F-TPS layup composition;
        https://ntrs.nasa.gov/citations/20140000147
    [4] VTK File Format Specification (XML DataArray / Piece attributes).
    [5] ctypes -- https://docs.python.org/3/library/ctypes.html
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import statistics
import sys
from collections.abc import Sequence
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC_PY = os.path.normpath(os.path.join(_HERE, "..", "src", "python"))
if _SRC_PY not in sys.path:
    sys.path.insert(0, _SRC_PY)

import ada_pinn_wrapper as W  # imported after the sys.path insert above

REQUIRED_STEP = 2200
#  The DESIGNATED VALIDATED REFERENCE snapshot, not the optimization gate's.
#  Corrected 2026-10-14: this previously pointed at
#  `results/validation_optimized/`, whose gate run's own log reads
#  "[VALIDATE] RESULT: VALIDATION FAILED / Survivability: FAILED -- vehicle
#  does not survive" (heat flux 58.42 % error, heat load 59.00 %, peak decel
#  31.00 %).  Every per-ply figure built on it inherited that provenance
#  without saying so.  `results/00_reference/` is the reference dataset
#  the optimizer measures every objective against (hiad_optimizer.py A2) and is
#  also fresh: step-2200 dump 2026-10-06 12:35 against 2026-09-26 for the gate
#  run.  Shape-compatible (3696 points / 3648 cells / 3648 heat-flux values),
#  verified before the switch.
DEFAULT_VTU = os.path.join(
    _HERE, "..", "results", "00_reference", "paraview",
    f"surf_{REQUIRED_STEP}.vtu")

#: Step-2200 state of the reference run, read verbatim from
#: `results/00_reference/validation_timeseries.csv` row step=2200.
#: Kept as named constants so the CLI defaults, the summary JSON and the
#: docstring above cannot disagree with each other.
REF_STEP2200_ALT_KM = 52.069210
REF_STEP2200_VEL_MS = 3101.079

#: The trees run.py Phase 2c emits a per-ply set for, and what each snapshot's
#: provenance IS.  This is the single table that makes the per-ply sets
#: automatable and non-interchangeable at the same time: the loop in run.py
#: reads it, so a tree cannot be added without also writing down what its
#: numbers mean.
#:
#: `alt_km` / `vel_ms` are each tree's OWN step-2200 values read from its own
#: `validation_timeseries.csv`.  They are deliberately NOT shared: measured
#: 2026-10-14, the four trees span 51.818 .. 52.069 km and 3094 .. 3379 m/s,
#: and the Ada `Snapshot_Vel_Ms = 3378` constant matches
#: `01_smooth` (3378.671) rather than the reference tree it was once
#: applied to.  A per-ply set built on one tree's snapshot and another tree's
#: altitude/velocity is a fabricated condition.
#:
#: `validation` is deliberately ABSENT: its DSMC window is 0..1000, so it has
#: no step-2200 row and no step-2200 surface dump to solve against.  It is not
#: silently skipped -- run.py states the reason when it builds the others.
#  Only the validated reference dataset is permitted to drive a per-ply
#  set.  The round-1 \"optimized\" gate run (heat flux 58.42 %% / heat load
#  59.00 %% / peak decel 31.00 %% error) is no longer kept on disk.
PER_PLY_TREES: dict[str, dict[str, object]] = {
    "00_reference": {
        "alt_km": REF_STEP2200_ALT_KM,
        "vel_ms": REF_STEP2200_VEL_MS,
        "role": "validation reference",
        "verdict": (
            "Validated reference: this is the dataset hiad_optimizer.py "
            "measures every objective against (A2) and the freshest "
            "step-2200 dump on disk (2026-10-06 12:35)."
        ),
    },
    "03_opt_geometry": {
        "alt_km": REF_STEP2200_ALT_KM,
        "vel_ms": REF_STEP2200_VEL_MS,
        "role": "optimized-topology candidate",
        "verdict": (
            "Per-ply TPS generated from that topology's own step-2200 "
            "surf VTU (2026-10-14). Its step-2200 row reads the same "
            "altitude and velocity as the validated reference."
        ),
    },
}

#: Nextel BF-20 outer-fabric heat-flux rating [W/cm^2] [2]. Used only for
#: reporting context, never to alter a solve.
NEXTEL_BF20_RATING_WCM2 = 30.0


# ---------------------------------------------------------------------------
# Snapshot parsing
# ---------------------------------------------------------------------------
def parse_vtu_cell_array(path: str, array_name: str) -> tuple[int, int, list[float]]:
    """Return ``(n_points, n_cells, values)`` for one CellData array.

    Parses the legacy VTK XML ``<Piece NumberOfPoints=.. NumberOfCells=..>``
    header and the named ``<DataArray>`` inside ``<CellData>`` [4]. Only the
    header and the CellData block are read, so a multi-megabyte Points block
    is never materialised.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the Piece header, the CellData block or the array is missing, or if
        the array length disagrees with NumberOfCells. A truncated dump is a
        hard failure here rather than a silently short element list.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"snapshot not found: {path}")
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    piece = re.search(
        r'<Piece\s+NumberOfPoints="(\d+)"\s+NumberOfCells="(\d+)"', text)
    if piece is None:
        raise ValueError(f"{path}: no <Piece> header found")
    n_points, n_cells = int(piece.group(1)), int(piece.group(2))

    cell_start = text.find("<CellData")
    cell_end = text.find("</CellData>")
    if cell_start < 0 or cell_end < 0:
        raise ValueError(f"{path}: no <CellData> block found")
    block = text[cell_start:cell_end]

    match = re.search(
        r'<DataArray[^>]*Name="' + re.escape(array_name) +
        r'"[^>]*>(.*?)</DataArray>',
        block, re.DOTALL)
    if match is None:
        raise ValueError(
            f"{path}: CellData has no array named {array_name!r}; "
            f"available: {re.findall(r'Name=\"([^\"]+)\"', block)}")
    values = [float(tok) for tok in match.group(1).split()]
    if len(values) != n_cells:
        raise ValueError(
            f"{path}: {array_name} has {len(values)} entries but the Piece "
            f"declares NumberOfCells={n_cells}; refusing to solve a partial "
            f"snapshot")
    return n_points, n_cells, values


def guard_step_identity(path: str, step: int) -> None:
    """Axiom A3: refuse anything that is not the step-2200 snapshot.

    Two independent guards, because either alone is defeatable: the requested
    step must be 2200, and the FILENAME must independently encode 2200. A
    caller that passes ``--step 2200`` while pointing at ``surf_1000.vtu``
    would otherwise silently solve the wrong flight state.
    """
    if step != REQUIRED_STEP:
        raise SystemExit(
            f"[GUARD] this driver only accepts the step-{REQUIRED_STEP} "
            f"snapshot; got step={step}. Refusing to run.")
    name = os.path.basename(path)
    # Compare as ints: re.findall yields strings, and REQUIRED_STEP is an int,
    # so a str/int comparison here would reject every legitimate filename.
    found = {int(tok) for tok in re.findall(r"\d+", name)}
    if REQUIRED_STEP not in found:
        raise SystemExit(
            f"[GUARD] filename {name!r} does not encode step {REQUIRED_STEP}; "
            f"refusing to assume which snapshot it is.")


def guard_tree_provenance(path: str, tree: str | None) -> None:
    """Refuse a snapshot whose results tree disagrees with ``--tree``.

    WHY THIS EXISTS (measured, 2026-10-15): ``--vtu`` used to default to a
    fixed path while ``--tree`` only set the provenance LABEL, so running
    ``--tree 03_opt_geometry`` without an explicit ``--vtu`` solved the
    00_reference snapshot and then wrote it into the 03 tree's outputs.  The
    numbers came back byte-identical to the reference run, which is how it was
    caught.  run.py has always passed ``--vtu`` explicitly and was never
    affected; the hole was in the standalone CLI.

    The check is a path-segment test rather than a content hash because the
    contract is about WHICH tree the caller claims, and the tree segment is
    exactly where that claim is made.

    Raises:
        SystemExit: if ``tree`` is set and ``path`` does not contain
            ``results/<tree>/`` as a path segment.
    """
    if tree is None:
        return
    parts = os.path.normpath(path).split(os.sep)
    # Adjacency test on SEGMENTS: "results" must be immediately followed by
    # the tree name. Comparing a joined "results/<tree>" string against single
    # segments can never match, which is the bug this replaced.
    under_tree = any(
        parts[i] == "results" and parts[i + 1] == tree
        for i in range(len(parts) - 1)
    )
    if not under_tree:
        raise SystemExit(
            f"[GUARD] --tree {tree} but --vtu is {os.path.normpath(path)!r}, "
            f"which is not under results/{tree}/. Solving one tree's snapshot "
            f"while labelling the results with another tree's provenance "
            f"would make the summary JSON a lie. Pass a matching --vtu.")


def verify_snapshot_shape(n_points: int, n_cells: int) -> dict[str, int]:
    """Check the snapshot against the Ada VTU writer's documented capacity.

    ``stellarorion_sparta.adb:2290-2291`` revolves each of N axial segments
    into N_Theta = 48 quads, so cells = N * 48 and points = (N + 1) * 48.
    Checking the snapshot against those writer caps proves the 3648-element
    surface is one the pipeline legitimately produced, instead of leaving the
    relationship as an assumption.

    Note on the 2000-element cap: ``Max_Surf_Elements = 2000``
    (``stellarorion_postprocessing.ads:98``) bounds arrays in the
    post-processing unit, NOT this path. The driver holds no fixed-size
    element array -- it iterates whatever the file declares -- and each solve
    is a single-element call into Ada, so no Ada array ever holds 3648
    elements. That is why the snapshot size is not a capacity problem here.
    """
    max_surf_segments = 4096      # stellarorion_sparta.adb:2290 (Max_Surf)
    n_theta = 48                 # stellarorion_sparta.adb:2291 (N_Theta)
    if n_cells % n_theta != 0:
        raise SystemExit(
            f"[GUARD] {n_cells} cells is not a multiple of N_Theta={n_theta}; "
            f"this snapshot was not written by the expected revolve writer.")
    segments = n_cells // n_theta
    if segments > max_surf_segments:
        raise SystemExit(
            f"[GUARD] {segments} axial segments exceeds the writer's "
            f"Max_Surf={max_surf_segments} cap; the snapshot is not the "
            f"file this pipeline produces.")
    expected_points = (segments + 1) * n_theta
    if n_points != expected_points:
        raise SystemExit(
            f"[GUARD] {n_points} points is inconsistent with "
            f"{segments} segments x N_Theta={n_theta} "
            f"(expected {expected_points}).")
    return {"axial_segments": segments, "n_theta": n_theta,
            "points_per_revolution": n_theta}


# ---------------------------------------------------------------------------
# Per-element solve
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Surface energy balance -- re-radiation vs conduction
# ---------------------------------------------------------------------------
# CODATA 2018 / SI-2019 exact value, used ONLY as an independent cross-check of
# the sigma recovered from Ada below; it is never the value the physics uses.
# [Citation: CODATA 2018, sigma = 5.670374419e-8 W m^-2 K^-4 (exact since 2019
#  SI redefinition); https://physics.nist.gov/cgi-bin/cuu/Value?sigma]
SIGMA_CODATA_WM2K4 = 5.670374419e-8

# Relative agreement required between the probes and CODATA before the
# recovered constant may be trusted.  1e-5 is ~20x the observed float64
# round-trip noise (measured 1.7e-8) yet far tighter than any physical change.
SIGMA_TOLERANCE = 1.0e-5

_sigma_cache: list[float] = []


def stefan_boltzmann_sigma() -> float:
    """Stefan-Boltzmann constant [W m^-2 K^-4], recovered from the Ada FFI.

    WHY NOT A LITERAL: the constant exists exactly once in this project, as
    ``SIGMA_BOLTZMANN`` in ``stellarorion_physics``.  ``TPS_Surface_Balance``
    uses that copy in its radiative term, so writing a second copy here would
    give the residual below two different sigmas to disagree about -- it would
    then be measuring my transcription, not the solver.  Deriving it keeps the
    value single-sourced in Ada.

    IDENTITIES
        ``Radiative_Eq_Temp(q, eps) = (q / (sigma * eps))**(1/4)``  [Ada]
        =>  ``sigma = q / (eps * T**4)``

    Three (q, eps) probes are evaluated and must agree; the first is taken as
    canonical.  The recovered value is then compared against the CODATA exact
    constant, which here acts as a GUARD on Ada's identity rather than as the
    source of the value.

    Returns:
        sigma [W m^-2 K^-4].

    Raises:
        ValueError: if any probe returns a non-positive temperature, the
            probes disagree by more than ``SIGMA_TOLERANCE``, or the result is
            non-positive or disagrees with CODATA by more than
            ``SIGMA_TOLERANCE``.  Each means the Ada identity changed shape,
            and silently continuing would corrupt every balance residual.
    """
    if _sigma_cache:
        return _sigma_cache[0]

    probes = ((1.0, 1.0), (1.0e6, 0.8), (3.0, 1.0))
    recovered: list[float] = []
    for heat_flux, emissivity in probes:
        temperature = float(W.radiative_eq_temp(heat_flux, emissivity))
        if temperature <= 0.0:
            raise ValueError(
                "radiative_eq_temp"
                f"({heat_flux}, {emissivity}) returned {temperature} K; "
                "cannot invert for sigma")
        recovered.append(heat_flux / (emissivity * temperature ** 4))

    spread = max(recovered) - min(recovered)
    scale = max(recovered)
    if scale <= 0.0 or spread / scale > SIGMA_TOLERANCE:
        raise ValueError(
            f"sigma probes disagree: {recovered} (relative spread "
            f"{spread / scale if scale else float('inf'):.3e} > "
            f"{SIGMA_TOLERANCE:.1e}); the Ada radiative identity changed")

    sigma = recovered[0]
    drift = abs(sigma - SIGMA_CODATA_WM2K4) / SIGMA_CODATA_WM2K4
    if drift > SIGMA_TOLERANCE:
        raise ValueError(
            f"sigma recovered from Ada {sigma:.10e} drifts {drift:.3e} "
            f"relative from CODATA {SIGMA_CODATA_WM2K4:.10e}")

    _sigma_cache.append(sigma)
    return sigma


def surface_flux_terms(t_surface_K: float, t_back_K: float,
                       q_conv: float, series_resistance: float,
                       emissivity: float, t_inf: float,
                       sigma: float,
                       lateral_g: float = 0.0,
                       lateral_src: float = 0.0
                       ) -> tuple[float, float, float, float, float]:
    """Split an element's wall flux into its balanced parts [W/m^2].

    The Ada surface balance solves, for the root ``T_s``::

        q_conv + q_lateral = q_cond + q_rad

    with ``q_lateral = lateral_src - lateral_g*T_s`` the net in-plane heat
    arriving from the neighbours, ``(T_s - T_back)/R`` the through-thickness
    conduction and ``eps*sigma*(T_s**4 - T_inf**4)`` the re-radiation.  With
    both lateral terms at their default of zero this collapses exactly to the
    uncoupled form ``q_conv = q_cond + q_rad``.

    Reporting ``q_lateral`` explicitly is not decoration: omitting it makes
    the residual look like a solver failure when it is simply the lateral
    term the coupled model added.  Measured on the step-2200 snapshot, the
    omitted-term residual peaked at 7.5 W/m^2 while the full balance closes
    to 0.062 W/m^2 -- a 120x difference that decides whether the solver
    looks trustworthy.

    Parameters:
        t_surface_K: hot-face temperature the solver returned [K].
        t_back_K: cold-face temperature the solver returned [K].
        q_conv: imposed convective wall flux the solver consumed [W/m^2].
        series_resistance: total series resistance of the layup [m^2K/W],
            as returned by the Ada FFI (NOT recomputed here).
        emissivity: hot-face emissivity [-].
        t_inf: radiative ambient temperature [K].
        sigma: Stefan-Boltzmann constant [W/m^2/K^4].
        lateral_g: sum_j g_ij for this element [W/K].
        lateral_src: sum_j g_ij*T_j for this element [W/m^2].

    Returns:
        ``(q_conv, q_cond, q_rad, q_lateral, residual)`` in W/m^2, where
        ``residual = q_conv + q_lateral - q_cond - q_rad`` and is zero to
        solver tolerance.

    Raises:
        ValueError: if ``series_resistance`` is not strictly positive (the
            conduction term would divide by zero) or any input is non-finite.
            These are contract violations from the solver, not data noise.
    """
    values = (t_surface_K, t_back_K, q_conv, series_resistance,
              emissivity, t_inf, sigma, lateral_g, lateral_src)
    if not all(math.isfinite(v) for v in values):
        raise ValueError(f"non-finite input to surface_flux_terms: {values}")
    if series_resistance <= 0.0:
        raise ValueError(
            f"series resistance must be > 0, got {series_resistance}")

    q_cond = (t_surface_K - t_back_K) / series_resistance
    q_rad = emissivity * sigma * (t_surface_K ** 4 - t_inf ** 4)
    #  Net in-plane heat DELIVERED to this element. Positive when the
    #  neighbours are hotter than this element, negative when it is shedding
    #  heat into them -- which is the usual case at the hot flank.
    q_lateral = lateral_src - lateral_g * t_surface_K
    return q_conv, q_cond, q_rad, q_lateral, q_conv + q_lateral - q_cond - q_rad


# ---------------------------------------------------------------------------
#  Lateral (in-plane) conduction -- expert-review item 2
# ---------------------------------------------------------------------------
#  WHY THIS EXISTS: the Ada solve is 1-D through-thickness and treats every
#  surface element as thermally islanded. The expert review asked for heat to
#  also travel INTO the neighbouring composite. This block supplies the two
#  quantities that term needs -- how strongly each pair of neighbours is
#  coupled, and how much heat each one is currently delivering -- and a
#  Gauss-Seidel loop that converges the whole surface at once.
#
#  GOVERNING EQUATION, per element i (steady state):
#      q_conv,i + sum_j g_ij (T_j - T_i) = q_rad,i(T_i) + (T_i - T_Back)/R_i
#  which the driver hands to Ada in the algebraically identical form
#      Lateral_G   = sum_j g_ij          [W/K]
#      Lateral_Src = sum_j g_ij * T_j    [W/m^2]
#  (see stellarorion_physics.ads, TPS_Conduction).
# ---------------------------------------------------------------------------

#  MATERIAL RULE. "Structural-layers-only" was the owner's decision: heat
#  travelling in-plane is carried by the continuous load-bearing plies, not by
#  the aerogel insulation, whose in-plane conductivity is 75x lower and which
#  is deliberately excluded. Names come from W.IRVE3_FTPS_PLY_NAMES, so a
#  layup change is picked up automatically -- but an UNRECOGNISED name is a
#  hard failure rather than a silent drop, because quietly classifying a new
#  ply as "not structural" would change the physics without anyone noticing.
STRUCTURAL_PLY_NAMES: frozenset[str] = frozenset({"Nicalon SiC"})

#  Convergence of the coupled surface: stop when no element's surface
#  temperature moves by more than LATERAL_TOL_K between sweeps. 1 mK against
#  surfaces of order 1e3 K is a relative 1e-6, far below the 0.1 % closure
#  tolerance the balance figure already enforces.
LATERAL_TOL_K: float = 1.0e-3

#  Hard cap on sweeps (softlock guard). Each sweep is 3648 short FFI calls;
#  the T^4 radiation term makes the map strongly contractive, so convergence
#  is reached in a handful of sweeps and this bound is never the binding one.
LATERAL_MAX_SWEEPS: int = 400

#  Sanity ceiling on the sheet conductance S [W/K]. The real IRVE-3 value is
#  1.518e-3; anything at or above this means a unit/typo bug upstream, and
#  silently feeding it in would produce confident nonsense.
LATERAL_SHEET_CAP_W_K: float = 1.0e2

#  Throughput below which an element is excluded from the RELATIVE closure
#  statistic only (the absolute residual is always reported). See the
#  summary block for why.
RESIDUAL_REL_FLOOR_WM2: float = 1.0


def parse_vtu_geometry(path: str) -> tuple[list[tuple[float, float, float]],
                                           list[tuple[int, ...]]]:
    """Read the point coordinates and cell connectivity from an ASCII VTU.

    Deliberately a small, guarded reader rather than a VTK import: the
    pipeline venv (`venv/python`) has no `vtk`, and adding one just to get
    3696 points would be a new failure mode in a stage that has to run by
    default. Only the header, `<Points>` and `<Cells>` are touched; the
    multi-megabyte CellData blocks are never materialised.

    Parameters
    ----------
    path : str
        Path to an ASCII ``.vtu`` file.

    Returns
    -------
    tuple
        ``(points, cells)`` where ``points`` is a list of N ``(x, y, z)``
        triples in metres and ``cells`` is a list of index tuples, one per
        cell, read via the ``offsets`` array so triangles and quads are both
        handled.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the header, the Points block, the connectivity or the offsets are
        missing, or if any length disagrees with the declared counts. A
        malformed mesh is a hard failure: adjacency built from a partial
        index list would silently invent or drop neighbour pairs.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"snapshot not found: {path}")
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    piece = re.search(
        r'<Piece\s+NumberOfPoints="(\d+)"\s+NumberOfCells="(\d+)"', text)
    if piece is None:
        raise ValueError(f"{path}: no <Piece> header found")
    n_points, n_cells = int(piece.group(1)), int(piece.group(2))

    # -- Points ------------------------------------------------------------
    p_start, p_end = text.find("<Points>"), text.find("</Points>")
    if p_start < 0 or p_end < 0:
        raise ValueError(f"{path}: no <Points> block found")
    p_array = re.search(
        r'<DataArray[^>]*NumberOfComponents="3"[^>]*>(.*?)</DataArray>',
        text[p_start:p_end], re.DOTALL)
    if p_array is None:
        raise ValueError(f"{path}: no 3-component Points DataArray found")
    coords = p_array.group(1).split()
    if len(coords) != 3 * n_points:
        raise ValueError(
            f"{path}: Points DataArray has {len(coords)} values, "
            f"expected {3 * n_points}")
    points = [
        (float(coords[3 * i]), float(coords[3 * i + 1]),
         float(coords[3 * i + 2]))
        for i in range(n_points)
    ]

    # -- Cells: connectivity + offsets -------------------------------------
    c_start, c_end = text.find("<Cells>"), text.find("</Cells>")
    if c_start < 0 or c_end < 0:
        raise ValueError(f"{path}: no <Cells> block found")
    block = text[c_start:c_end]

    conn_m = re.search(
        r'<DataArray[^>]*Name="connectivity"[^>]*>(.*?)</DataArray>',
        block, re.DOTALL)
    off_m = re.search(
        r'<DataArray[^>]*Name="offsets"[^>]*>(.*?)</DataArray>', block, re.DOTALL)
    if conn_m is None or off_m is None:
        raise ValueError(f"{path}: connectivity/offsets DataArray not found")

    conn = [int(v) for v in conn_m.group(1).split()]
    offsets = [int(v) for v in off_m.group(1).split()]
    if len(offsets) != n_cells:
        raise ValueError(
            f"{path}: offsets has {len(offsets)} entries, "
            f"expected {n_cells} cells")
    if not offsets or offsets[-1] != len(conn):
        raise ValueError(
            f"{path}: offsets end at {offsets[-1] if offsets else 0} but "
            f"connectivity holds {len(conn)} indices")

    cells: list[tuple[int, ...]] = []
    start = 0
    for stop in offsets:
        cell = tuple(conn[start:stop])
        if not cell:
            raise ValueError(f"{path}: zero-length cell in connectivity")
        for idx in cell:
            if idx < 0 or idx >= n_points:
                raise ValueError(
                    f"{path}: connectivity index {idx} outside "
                    f"[0, {n_points})")
        cells.append(cell)
        start = stop
    if len(cells) != n_cells:
        raise ValueError(
            f"{path}: derived {len(cells)} cells, header declares {n_cells}")
    return points, cells


def build_adjacency(points: list[tuple[float, float, float]],
                    cells: list[tuple[int, ...]]) -> tuple[
                        list[list[tuple[int, float, float]]], dict[str, int]]:
    """Pair up cells that share an edge and measure the coupling geometry.

    Neighbourhood is derived from the MESH, not from a guessed structured
    index: two cells are neighbours when they own the same pair of point
    indices, which is exactly a shared edge. That works for any topology and
    cannot be wrong in the way an assumed ``(k, t)`` indexing could.

    For each pair the returned conductance coefficient is
    ``ell / d`` -- shared-edge length over centroid distance -- which the
    caller multiplies by the sheet conductance. Both are measured in metres
    on the real 3-D surface, so an axisymmetric body of revolution is handled
    without any special-casing.

    Parameters
    ----------
    points : list of (x, y, z)
        Cell-corner coordinates [m].
    cells : list of index tuples
        Connectivity, as returned by :func:`parse_vtu_geometry`.

    Returns
    -------
    tuple
        ``(adj, stats)``. ``adj[i]`` is a list of ``(j, ell_over_d)`` for
        every cell ``j`` sharing an edge with cell ``i``; ``ell_over_d`` is
        dimensionless. ``stats`` counts edges, neighbour pairs and the
        anomalies encountered, so a caller can assert the mesh was sane.

    Raises
    ------
    ValueError
        If a shared edge has zero length, two centroids coincide (which would
        divide by zero), or an edge is claimed by more than two cells
        (non-manifold -- the coupling would be double-counted).
    """
    if not cells:
        raise ValueError("mesh has no cells; cannot build adjacency")

    edge_owner: dict[tuple[int, int], list[int]] = {}
    for cell_index, cell in enumerate(cells):
        n = len(cell)
        for e in range(n):
            a, b = cell[e], cell[(e + 1) % n]
            key = (a, b) if a < b else (b, a)
            edge_owner.setdefault(key, []).append(cell_index)

    #  Cell centroid: the anchor the separation d is measured between.
    centroids: list[tuple[float, float, float]] = []
    for cell in cells:
        n = len(cell)
        centroids.append((
            sum(points[i][0] for i in cell) / n,
            sum(points[i][1] for i in cell) / n,
            sum(points[i][2] for i in cell) / n,
        ))

    adj: list[list[tuple[int, float, float]]] = [[] for _ in cells]
    boundary_edges = 0
    non_manifold = 0
    for (a, b), owners in edge_owner.items():
        if len(owners) == 1:
            #  A free edge on the outer rim: nothing to conduct to, which is
            #  the correct behaviour, not a defect.
            boundary_edges += 1
            continue
        if len(owners) > 2:
            non_manifold += 1
            raise ValueError(
                f"edge ({a}, {b}) is shared by {len(owners)} cells; "
                f"the mesh is non-manifold and lateral coupling would "
                f"double-count heat")
        pa, pb = points[a], points[b]
        ell = math.sqrt((pa[0] - pb[0]) ** 2
                        + (pa[1] - pb[1]) ** 2
                        + (pa[2] - pb[2]) ** 2)
        if not (ell > 0.0) or not math.isfinite(ell):
            raise ValueError(f"shared edge ({a}, {b}) has length {ell}; "
                             f"the coupling coefficient would be NaN/inf")

        i, j = owners
        ca, cb = centroids[i], centroids[j]
        d = math.sqrt((ca[0] - cb[0]) ** 2
                      + (ca[1] - cb[1]) ** 2
                      + (ca[2] - cb[2]) ** 2)
        if not (d > 0.0) or not math.isfinite(d):
            raise ValueError(
                f"cells {i} and {j} share an edge but their centroids are "
                f"{d} apart; cannot form a separation distance")

        ratio = ell / d
        adj[i].append((j, ratio))
        adj[j].append((i, ratio))

    stats = {
        "cells": len(cells),
        "edges": len(edge_owner),
        "boundary_edges": boundary_edges,
        "neighbour_pairs": sum(len(v) for v in adj) // 2,
        "isolated_cells": sum(1 for v in adj if not v),
        "non_manifold_edges": non_manifold,
    }
    return adj, stats


def structural_sheet_conductance() -> dict[str, float]:
    """Sum ``k * thickness`` over the structural plies only [W/K].

    The sheet conductance is the right object for in-plane flow: a layer of
    thickness ``t`` and conductivity ``k`` spanning a planar distance ``d``
    across a width ``ell`` conducts ``k * (ell * t) / d``, so the whole layup
    collapses to ``(ell/d) * sum(k * t)`` and ``sum(k * t)`` is this value.

    Returns
    -------
    dict
        ``sheet_structural_W_K`` (the value actually used), ``sheet_total_W_K``
        (all five plies, reported so a reader can see what the
        structural-only decision costs), ``excluded_names`` and ``unknown``.

    Raises
    ------
    ValueError
        If a ply name is not in the structural set AND not recognised as a
        known non-structural ply, or if any ``k * t`` is non-positive.
    """
    names = W.IRVE3_FTPS_PLY_NAMES
    thickness = W.IRVE3_FTPS_PLY_THICKNESS_M
    conductivity = W.IRVE3_FTPS_PLY_THERMAL_K
    if not (len(names) == len(thickness) == len(conductivity)):
        raise ValueError(
            f"layup name/thickness/k arrays are ragged: "
            f"{len(names)}/{len(thickness)}/{len(conductivity)}")

    #  Names that are deliberately NOT structural. Listed rather than
    #  inferred from k so that adding a ply forces an explicit classification
    #  instead of being classified by whatever its conductivity happens to be.
    known_non_structural = {"Pyrogel 3350", "Kapton"}
    unknown = [n for n in names
               if n not in STRUCTURAL_PLY_NAMES and n not in known_non_structural]
    if unknown:
        raise ValueError(
            f"unclassified ply name(s) {sorted(set(unknown))}: add them to "
            f"STRUCTURAL_PLY_NAMES or to the known non-structural set in "
            f"structural_sheet_conductance(); guessing would silently "
            f"change the lateral conductance")

    structural = 0.0
    total = 0.0
    for name, t, k in zip(names, thickness, conductivity, strict=True):
        if not (t > 0.0) or not (k > 0.0):
            raise ValueError(f"ply {name!r} has t={t}, k={k}; "
                             f"both must be positive")
        contribution = float(k) * float(t)
        total += contribution
        if name in STRUCTURAL_PLY_NAMES:
            structural += contribution

    if not (structural > 0.0):
        raise ValueError(
            f"structural sheet conductance is {structural}; no ply was "
            f"classified as structural")
    if structural >= LATERAL_SHEET_CAP_W_K:
        raise ValueError(
            f"structural sheet conductance {structural} W/K reaches the "
            f"{LATERAL_SHEET_CAP_W_K} sanity ceiling; the layup arrays are "
            f"almost certainly mis-scaled")

    return {
        "sheet_structural_W_K": structural,
        "sheet_total_W_K": total,
        "structural_ply_count": float(sum(
            1 for n in names if n in STRUCTURAL_PLY_NAMES)),
        "excluded_names": 0.0,
        "unknown_count": float(len(unknown)),
    }


def _lateral_coefficients(
    adj: list[list[tuple[int, float, float]]],
    sheet_wk: float,
) -> list[list[tuple[int, float]]]:
    """Turn adjacency ratios into per-pair conductances ``g_ij`` [W/K].

    ``g_ij = (ell_ij / d_ij) * S`` -- the shared-edge geometry scaled by the
    structural sheet conductance. Computed once, since neither factor changes
    between sweeps.
    """
    return [
        [(neighbour, ratio * sheet_wk) for neighbour, ratio in pairs]
        for pairs in adj
    ]

def solve_all_elements(
    ke_raw: list[float],
    q_sg: float,
    ke_ref: float,
    write_profiles: bool,
    t_init: float,
    t_inf: float,
    adjacency: list[list[tuple[int, float]]] | None = None,
    sheet_wk: float = 0.0,
) -> list[dict[str, Any]]:
    """Solve every surface element, optionally coupled laterally.

    The IRVE-3 layup arguments are left at their ``tps_conduction`` defaults,
    which ARE the IRVE-3 F-TPS schedule (axiom A2). They are not restated
    here, so there is exactly one copy of the ply table in the codebase.

    Parameters
    ----------
    ke_raw : list of float
        Per-element raw kinetic-energy flux [W/m^2].
    q_sg, ke_ref : float
        Sutton-Graves reference flux and its positive divisor.
    write_profiles : bool
        Emit the 33-sample in-depth profile for each element.
    t_init, t_inf : float
        Pinned cold-face and radiative ambient temperatures [K].
    adjacency : list of list of (neighbour, g_ij), optional
        Pre-computed lateral conductances [W/K] from
        :func:`_lateral_coefficients`. ``None`` runs the pure 1-D solve.
    sheet_wk : float
        The sheet conductance already folded into ``g_ij``; kept as a
        parameter only so the caller can report what was used.

    Returns
    -------
    list of dict
        One row per element, including the surface-balance split and the
        lateral terms that produced it.

    Raises
    ------
    SystemExit
        If ``ke_ref`` is not positive, if Ada violates the q_SG clamp, if the
        adjacency does not cover exactly the element list, or if the coupled
        solve fails to converge within ``LATERAL_MAX_SWEEPS`` sweeps. An
        unconverged field is never written out: a table that looks solved but
        is not is worse than no table.

    Notes
    -----
    Solve order (one code path, so the 1-D and coupled cases cannot drift):
    1. a seed pass with both lateral terms at zero -- the exact legacy 1-D
       result, which is also the whole answer when ``adjacency is None``;
    2. Gauss-Seidel sweeps, each element seeing its neighbours' CURRENT
       temperature, until no element moves by more than ``LATERAL_TOL_K``;
    3. one materialising pass that rebuilds every reported field from the
       converged temperatures and fills the profiles.

    Step 3 is a separate pass rather than a flag threaded through step 2
    precisely so the profile and the reported T_surface can never come from
    different sweeps.
    """
    if not (ke_ref > 0.0):
        raise SystemExit(
            f"[GUARD] Ke_Ref = {ke_ref} is not positive; it is the divisor "
            f"that maps the hottest snapshot reading onto Q_SG (axiom A4).")

    sigma = stefan_boltzmann_sigma()
    emissivity = W.IRVE3_FTPS_EMISSIVITY
    print(f"[BALANCE] sigma recovered from Ada FFI = {sigma:.10e} W/m^2/K^4 "
          f"(CODATA {SIGMA_CODATA_WM2K4:.10e}, relative drift "
          f"{abs(sigma - SIGMA_CODATA_WM2K4) / SIGMA_CODATA_WM2K4:.2e}); "
          f"eps = {emissivity}; the surface split below is the solver's own, "
          f"not a re-implementation")

    n_elements = len(ke_raw)
    #  Scale the raw ell/d geometry ratios into conductances HERE. Passing
    #  adjacency through untouched would treat a dimensionless ratio as a
    #  conductance and over-couple the surface by 1/S (659x for this layup)
    #  -- caught by comparing the resulting G against A/R from the mesh.
    lateral_pairs: list[list[tuple[int, float]]] | None = (
        _lateral_coefficients(adjacency, sheet_wk)
        if adjacency is not None else None)
    if lateral_pairs is not None:
        if len(lateral_pairs) != n_elements:
            raise SystemExit(
                f"[GUARD] adjacency describes {len(lateral_pairs)} cells but "
                f"the snapshot carries {n_elements} elements; pairing them "
                f"would attach every g_ij to the wrong element.")
        if not (sheet_wk > 0.0):
            raise SystemExit(
                f"[GUARD] lateral coupling requested with sheet conductance "
                f"{sheet_wk}; it must be strictly positive.")

    def _one(index: int, raw: float, lateral_g: float,
             lateral_src: float) -> dict[str, Any]:
        """Run the Ada solve for one element and apply the q_SG clamp guard."""
        result = W.tps_conduction(
            q_sg_scale=q_sg, ke_raw=raw, ke_ref=ke_ref,
            t_init=t_init, t_inf=t_inf,
            lateral_g=lateral_g, lateral_src=lateral_src)
        if not (0.0 <= result["q_sg"] <= q_sg * (1.0 + 1.0e-6)):
            raise SystemExit(
                f"[GUARD] element {index}: Ada returned q_SG="
                f"{result['q_sg']} outside [0, Q_SG={q_sg}]; the clamp in "
                f"axiom A1 was not honoured.")
        return result

    def _terms(index: int) -> tuple[float, float]:
        """(Lateral_G, Lateral_Src) for element i at the current temperatures."""
        if lateral_pairs is None:
            return 0.0, 0.0
        g_i = 0.0
        src_i = 0.0
        for neighbour, g_ij in lateral_pairs[index]:
            g_i += g_ij
            src_i += g_ij * results[neighbour]["t_surface"]
        return g_i, src_i

    # -- 1. Seed pass: both lateral terms zero == the legacy 1-D solve ------
    results = [_one(index, raw, 0.0, 0.0)
               for index, raw in enumerate(ke_raw)]

    sweeps = 0
    delta = LATERAL_TOL_K
    if lateral_pairs is not None:
        # -- 2. Gauss-Seidel over the surface ------------------------------
        for sweep in range(1, LATERAL_MAX_SWEEPS + 1):
            sweeps = sweep
            delta = 0.0
            for index, raw in enumerate(ke_raw):
                g_i, src_i = _terms(index)
                updated = _one(index, raw, g_i, src_i)
                drift = abs(updated["t_surface"]
                             - results[index]["t_surface"])
                delta = max(delta, drift)
                results[index] = updated
            if delta <= LATERAL_TOL_K:
                break
        else:
            raise SystemExit(
                f"[GUARD] lateral coupling is still moving {delta} K after "
                f"{LATERAL_MAX_SWEEPS} sweeps (tolerance {LATERAL_TOL_K} K). "
                f"Refusing to emit a table from an unconverged field.")
        print(f"[LATERAL] coupled solve: {sweeps} sweeps, max |dT_s| = "
              f"{delta:.3e} K, sheet S = {sheet_wk:.6e} W/K, "
              f"neighbours/cell = "
              f"{sum(len(v) for v in lateral_pairs) / max(1, n_elements):.2f}")

    # -- 3. Materialise every reported field from the converged field ------
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(ke_raw):
        g_i, src_i = _terms(index)
        result = _one(index, raw, g_i, src_i)
        results[index] = result
        q_conv, q_cond, q_rad, q_lateral, residual = surface_flux_terms(
            t_surface_K=result["t_surface"],
            t_back_K=result["t_back"],
            q_conv=result["q_sg"],
            series_resistance=result["series_resistance_m2K_W"],
            emissivity=emissivity,
            t_inf=t_inf,
            sigma=sigma,
            lateral_g=g_i,
            lateral_src=src_i,
        )
        rows.append({
            "element": index,
            "ke_raw_Wm2": raw,
            "q_sg_Wm2": result["q_sg"],
            "t_surface_K": result["t_surface"],
            "t_back_K": result["t_back"],
            "n_iterations": result["n_iterations"],
            "t_surface_exceeds_struct_limit":
                result["t_surface"] > W.IRVE3_FTPS_STRUCT_LIMIT_K,
            "t_back_exceeds_struct_limit": result["t_back_exceeds_limit"],
            # Surface energy balance: q_conv = q_cond + q_rad [+ residual].
            "series_resistance_m2K_W": result["series_resistance_m2K_W"],
            "q_conv_Wm2": q_conv,
            "q_cond_Wm2": q_cond,
            "q_rad_Wm2": q_rad,
            "q_lateral_Wm2": q_lateral,
            "balance_residual_Wm2": residual,
            # Lateral terms actually handed to Ada for this element.
            "lateral_g_WK": g_i,
            "lateral_src_Wm2": src_i,
            "profile_depth_m": result["profile_depth_m"] if write_profiles else None,
            "profile_temp_K": result["profile_temp"] if write_profiles else None,
        })
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_element_csv(path: str, rows: list[dict[str, Any]]) -> None:
    """Per-element table: the q_SG / T_s / T_back exposure the goal requires."""
    fields = ["element", "ke_raw_Wm2", "q_sg_Wm2", "t_surface_K", "t_back_K",
              "n_iterations", "t_surface_exceeds_struct_limit",
              "t_back_exceeds_struct_limit",
              # Surface energy balance: q_conv = q_cond + q_rad (+ residual).
              # Emitted so a reader can re-check closure without re-running
              # the solver, and so the balance plot has its data on disk.
              "series_resistance_m2K_W", "q_conv_Wm2", "q_cond_Wm2",
              "q_rad_Wm2", "q_lateral_Wm2", "balance_residual_Wm2",
              # Lateral (in-plane) terms the coupled solve actually used for
              # this element. Emitted so a reader can re-derive the neighbour
              # sum -- and see the zero row that means "uncoupled" -- without
              # rebuilding the mesh.
              "lateral_g_WK", "lateral_src_Wm2"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_profile_csv(path: str, rows: list[dict[str, Any]]) -> int:
    """Flat per-element x per-sample profile table (33 samples per element)."""
    written = 0
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["element", "sample", "depth_m", "temp_K"])
        for row in rows:
            depth = row["profile_depth_m"]
            temp = row["profile_temp_K"]
            if depth is None or temp is None:
                continue
            for sample, (d, t) in enumerate(zip(depth, temp)):
                writer.writerow([row["element"], sample, f"{d:.9g}", f"{t:.9g}"])
                written += 1
    return written


def _series_node_temp(t_surface_K: float, t_back_K: float,
                      ply_thickness: Sequence[float],
                      ply_thermal_k: Sequence[float],
                      target_depth_m: float) -> float:
    """Exact node temperature at ``target_depth_m`` from the series solution [K].

    WHY NOT INTERPOLATE THE PROFILE (this replaces an interpolating version):
    the solver's 33 profile samples are UNIFORMLY spaced (0 .. total_depth/32,
    i.e. 2.22844e-4 m), so they do not land on ply hot faces.  A boundary at
    0.001012 m falls between samples at 0.000891 and 0.001114.  But the
    profile is only PIECEWISE linear -- dT/dx = -q/k changes at every
    interface -- so a straight line between two samples that straddle an
    interface lies across a kink and mis-states the boundary temperature.
    Measured on the peak element, that error was 10.1 K at the ply-3 face and
    3.4 K at the ply-5 face, and it turned into per-ply fluxes of
    3 698.7 / 33 627.7 / 3 632.4 / 3 676.2 / 20 117.5 W/m2 where steady-state
    series conduction requires ONE value.

    THE EXACT ROUTE. In steady 1-D series conduction the through-flux is
    constant, so with R_total = SUM(t_i/k_i):

        q     = (T_surface - T_back) / R_total          [W/m2]
        T(x)  = T_surface - q * R(x)                    [K]
        R(x)  = SUM_{plies fully above x} t_i/k_i
                + (x - x_i)/k_i                         [m2K/W]

    This is evaluated directly from the layup and the two boundary
    temperatures the solver returns, so it is exact to floating-point
    summation and does not depend on the sample grid at all.  Verified: it
    reproduces the solver's own 33 samples to 3e-4 K (mean) / 1e-3 K (max)
    on the peak element, and it puts the node at the ply-3 face at 1427.75 K
    where interpolation gave 1417.66 K.

    Parameters:
        t_surface_K: hot-face temperature the solver returned [K].
        t_back_K: cold-face temperature the solver returned [K].
        ply_thickness, ply_thermal_k: the layup actually solved, hot face first.
        target_depth_m: depth from the hot face at which to evaluate [m].

    Returns:
        The node temperature [K].

    Raises:
        ValueError: the layup is empty, or a thickness or conductivity is not
            strictly positive (R would be undefined), or the depth is outside
            the stack.  All three are caller bugs, not data noise, so they are
            raised rather than clamped.
    """
    n_ply = len(ply_thickness)
    if n_ply == 0:
        raise ValueError("layup is empty")
    if len(ply_thickness) != len(ply_thermal_k):
        raise ValueError("ply_thickness and ply_thermal_k differ in length")
    total = 0.0
    r_total = 0.0
    for thickness, k in zip(ply_thickness, ply_thermal_k):
        t_i = float(thickness)
        k_i = float(k)
        if t_i <= 0.0 or k_i <= 0.0:
            raise ValueError(
                f"non-positive ply property: thickness={t_i} k={k_i}")
        total += t_i
        r_total += t_i / k_i
    if r_total <= 0.0:
        raise ValueError(f"total series resistance is non-positive: {r_total}")
    if not 0.0 <= target_depth_m <= total + 1.0e-15:
        raise ValueError(
            f"target depth {target_depth_m} m outside the stack "
            f"0 .. {total} m")

    flux = (float(t_surface_K) - float(t_back_K)) / r_total
    acc_depth = 0.0
    acc_resistance = 0.0
    for thickness, k in zip(ply_thickness, ply_thermal_k):
        t_i = float(thickness)
        k_i = float(k)
        if acc_depth + t_i >= target_depth_m - 1.0e-15:
            return (float(t_surface_K)
                    - flux * (acc_resistance + (target_depth_m - acc_depth) / k_i))
        acc_depth += t_i
        acc_resistance += t_i / k_i
    # target_depth_m == total (the cold face), within the epsilon above.
    return float(t_surface_K) - flux * acc_resistance


def series_flux(t_surface_K: float, t_back_K: float,
                ply_thickness: Sequence[float],
                ply_thermal_k: Sequence[float]) -> float:
    """The ONE through-flux of a series stack [W/m2].

    Steady 1-D series conduction carries a single flux, so reporting five
    per-ply fluxes is reporting five estimates of one number.  This returns
    the exact value; the per-ply quantities that ARE independent are the node
    temperature at each face and the ply's share of the total resistance.

    Raises:
        ValueError: empty layup, non-positive property, or non-positive total
            resistance -- the same guards as ``_series_node_temp``.
    """
    n_ply = len(ply_thickness)
    if n_ply == 0:
        raise ValueError("layup is empty")
    if len(ply_thickness) != len(ply_thermal_k):
        raise ValueError("ply_thickness and ply_thermal_k differ in length")
    r_total = 0.0
    for thickness, k in zip(ply_thickness, ply_thermal_k):
        t_i = float(thickness)
        k_i = float(k)
        if t_i <= 0.0 or k_i <= 0.0:
            raise ValueError(
                f"non-positive ply property: thickness={t_i} k={k_i}")
        r_total += t_i / k_i
    if r_total <= 0.0:
        raise ValueError(f"total series resistance is non-positive: {r_total}")
    return (float(t_surface_K) - float(t_back_K)) / r_total


def write_layers_csv(path: str, rows: list[dict[str, Any]],
                     ply_thickness: Sequence[float],
                     ply_thermal_k: Sequence[float],
                     ply_names: Sequence[str]) -> int:
    """Per-element x per-ply table, written by THIS driver.

    WHY THIS WRITER EXISTS (F123/F124 -- read before deleting it):
    `tps_step2200_layers.csv` had NO writer anywhere in the repository, so it
    went stale silently.  It still recorded `k = 0.25` and the superseded grade
    "Pyrogel 2250" after both had changed, and `make_ply_heatflux_plots.py`
    read the ply name, thickness and conductivity from it -- meaning a layup
    change could be fully applied in the solver and absent from every per-ply
    figure.  The plot script was moved onto the authoritative preset, and the
    preset-override warning remains as a tripwire, but a table that no program
    writes is a table that will drift again.  This closes the hole at the
    source: the values come from the Ada solver's own layup, so the file is
    regenerated whenever the solve is.

    AXIOMS:
        A1. Ply geometry and material are the solver's, never a re-derivation:
            the same tuples that parameterise the Ada FFI call are written out.
        A2. ``depth_m`` is the ply's HOT-FACE depth (ply 1 at 0.0), so the
            column is what ``per_ply_flux`` and
            ``plot_temperature_profile`` assume.  It is NOT the cold face:
            an earlier revision wrote cumulative cold-face depths
            (0.000506, 0.001012, ...), which shifted every gradient by one
            ply and produced a nonsensical q2 = 1.645e6 W/m^2 on the peak
            element.  ``per_ply_flux`` forms ``(T_i - T_{i+1}) / R_i`` and
            ``plot_temperature_profile`` closes the axis with
            ``depths[-1] + thickness[-1]``; both read hot face first.
        A3. ``temp_K`` is the EXACT node temperature from the series
            solution, not an interpolation of the uniform sample grid --
            see ``_series_node_temp`` for why interpolation is wrong at a
            material interface (measured: 10.1 K at the ply-3 face).

    Parameters:
        rows: per-element results, carrying ``t_surface_K`` and
            ``t_back_K`` from the Ada solver.  ``profile_depth_m`` /
            ``profile_temp_K`` are NOT used: the node temperatures come from
            the layup and the two boundary temperatures, so they do not
            depend on the 33-point sample grid.
        ply_thickness, ply_thermal_k, ply_names: the layup actually solved,
            hot face first, same length.

    Returns:
        The number of data rows written (elements x plies).

    Raises:
        ValueError: propagated from ``_series_node_temp`` if the layup is
            malformed.  A malformed layup is a caller bug and must abort the
            write rather than emit a table of wrong depths.
    """
    n_ply = len(ply_thickness)
    if n_ply == 0:
        raise ValueError("layup is empty")
    if len(ply_thickness) != len(ply_thermal_k):
        raise ValueError("ply_thickness and ply_thermal_k differ in length")
    #  HOT-FACE depth of each ply [m] = the cumulative thickness of every ply
    #  ABOVE it, so ply 1 sits at 0.0.  This is the convention the table has
    #  always used and every reader depends on -- see axiom A2 above.
    hot_face: list[float] = []
    acc = 0.0
    for thickness in ply_thickness:
        hot_face.append(acc)
        acc += float(thickness)

    written = 0
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["element", "ply", "ply_name", "depth_m", "temp_K",
                         "ply_thickness_m", "ply_k_WmK"])
        for row in rows:
            element = row["element"]
            t_surface = float(row["t_surface_K"])
            t_back = float(row["t_back_K"])
            for ply in range(n_ply):
                name = ply_names[ply] if ply < len(ply_names) else f"ply{ply + 1}"
                thickness = float(ply_thickness[ply])
                k = float(ply_thermal_k[ply]) if ply < len(ply_thermal_k) else float("nan")
                node = _series_node_temp(t_surface, t_back,
                                         ply_thickness, ply_thermal_k,
                                         hot_face[ply])
                writer.writerow([
                    element, ply + 1, name,
                    f"{hot_face[ply]:.9g}",
                    f"{node:.9g}",
                    f"{thickness:.9g}", f"{k:.9g}",
                ])
                written += 1
    return written


def _flux_of(row: dict[str, Any]) -> float:
    """Sort key: the Sutton-Graves flux this element received [W/m^2]."""
    return float(row["q_sg_Wm2"])


def _safe_mean(values: Sequence[float]) -> float:
    """Arithmetic mean of ``values``, or 0.0 when ``values`` is empty.

    An empty sequence is legitimate here: if every element received zero flux
    there is no radiative FRACTION to average (0/0 is undefined).  0.0 is
    returned as an explicit sentinel for "no heated elements to average", NOT
    as a claim that the radiative share is zero -- the caller must read
    ``elements_at_zero_flux`` next to it to tell those two apart.

    Raises:
        ValueError: if any value is non-finite (a NaN would otherwise
            silently poison the mean).
    """
    if not values:
        return 0.0
    if not all(math.isfinite(v) for v in values):
        raise ValueError("non-finite value in mean")
    return float(statistics.fmean(values))


def summarise(rows: list[dict[str, Any]], q_sg: float, shape: dict[str, int],
              snapshot: str, *,
              tree: str | None = None,
              altitude_km: float | None = None,
              velocity_ms: float | None = None) -> dict[str, Any]:
    """Aggregate statistics plus the two caveats a reader must not miss."""
    _spec = PER_PLY_TREES.get(tree, {}) if tree else {}
    _known = tree if tree else "unnamed"
    q_values = [r["q_sg_Wm2"] for r in rows]
    t_s = [r["t_surface_K"] for r in rows]
    t_b = [r["t_back_K"] for r in rows]
    peak = max(rows, key=_flux_of)
    zero_flux = sum(1 for v in q_values if v == 0.0)
    negative_raw = sum(1 for r in rows if r["ke_raw_Wm2"] < 0.0)
    return {
        "snapshot": os.path.basename(snapshot),
        "provenance": {
            "tree": _known,
            "role": _spec.get("role", "not stated by the caller"),
            "verdict": _spec.get(
                "verdict",
                "No --tree was given, so no role or verdict is claimed. "
                "The snapshot path is the only provenance this run carries."),
            "altitude_km_used": altitude_km,
            "velocity_ms_used": velocity_ms,
            "tree_step2200_alt_km": _spec.get("alt_km"),
            "tree_step2200_vel_ms": _spec.get("vel_ms"),
            "condition_matches_tree": (
                None if not _spec or altitude_km is None or velocity_ms is None
                else (abs(float(_spec["alt_km"]) - altitude_km) < 1.0e-9
                      and abs(float(_spec["vel_ms"]) - velocity_ms) < 1.0e-9)
            ),
        },
        "elements": len(rows),        "snapshot_shape": shape,
        "q_sg_Wm2": q_sg,
        "q_peak_Wm2": max(q_values),
        "q_peak_Wcm2": max(q_values) / 1.0e4,
        "nextel_bf20_rating_Wcm2": NEXTEL_BF20_RATING_WCM2,
        "peak_within_nextel_rating": (max(q_values) / 1.0e4)
                                    <= NEXTEL_BF20_RATING_WCM2,
        "t_surface_K": {"min": min(t_s), "max": max(t_s),
                        "mean": statistics.fmean(t_s)},
        "t_back_K": {"min": min(t_b), "max": max(t_b),
                     "mean": statistics.fmean(t_b)},
        "elements_at_zero_flux": zero_flux,
        "elements_with_negative_raw_flux": negative_raw,
        "elements_t_surface_over_struct_limit":
            sum(1 for r in rows if r["t_surface_exceeds_struct_limit"]),
        "elements_t_back_over_struct_limit":
            sum(1 for r in rows if r["t_back_exceeds_struct_limit"]),
        "struct_limit_K": W.IRVE3_FTPS_STRUCT_LIMIT_K,
        "peak_element": {"element": peak["element"],
                         "q_sg_Wm2": peak["q_sg_Wm2"],
                         "t_surface_K": peak["t_surface_K"],
                         "t_back_K": peak["t_back_K"]},
        "layup": {
            "ply_thickness_m": list(W.IRVE3_FTPS_PLY_THICKNESS_M),
            "ply_thermal_k": list(W.IRVE3_FTPS_PLY_THERMAL_K),
            "total_thickness_m": sum(W.IRVE3_FTPS_PLY_THICKNESS_M),
            "emissivity": W.IRVE3_FTPS_EMISSIVITY,
            "struct_limit_K": W.IRVE3_FTPS_STRUCT_LIMIT_K,
        },
        "surface_energy_balance": {
            # q_conv = q_cond + q_rad + residual, evaluated on every element.
            # The residual is the solver's own closure error: TPS_Surface_Balance
            # stops bisection when f(T) stops changing, so a small residual here
            # is evidence the returned T_s really is the root of THAT equation.
            "sigma_Wm2K4": stefan_boltzmann_sigma(),
            "sigma_source": "recovered from Ada Radiative_Eq_Temp_C identity",
            "sigma_codata_Wm2K4": SIGMA_CODATA_WM2K4,
            "emissivity": W.IRVE3_FTPS_EMISSIVITY,
            "residual_Wm2_abs_max": max(
                abs(r["balance_residual_Wm2"]) for r in rows),
            "residual_Wm2_abs_mean": statistics.fmean(
                abs(r["balance_residual_Wm2"]) for r in rows),
            #  All three ratios below are normalised by the element's TOTAL
            #  throughput (q_cond + q_rad), not by q_conv alone. Under the
            #  coupled model q_conv is only part of what the surface sees, so
            #  dividing by it makes the radiative share exceed 100 % for any
            #  element that is shedding heat to its neighbours -- a
            #  presentation artefact, not a physical result. Because the
            #  balance closes, q_cond + q_rad == q_conv + q_lateral, so this
            #  is exactly "of the heat leaving the surface, how much went out
            #  by radiation". With both lateral terms zero it reduces
            #  identically to the old q_rad/q_conv.
            #  Relative closure is taken over elements carrying at least
            #  1 W/m^2 of throughput. Below that the denominator is so small
            #  that an absolute residual of 0.06 W/m^2 -- 1.6e-7 of the peak
            #  -- reports as a ratio near 1, which would read as a solver
            #  defect when it is arithmetic on a cold element. The floor is
            #  stated here so the filter is visible, not hidden.
            "residual_throughput_floor_Wm2": RESIDUAL_REL_FLOOR_WM2,
            "residual_rel_max": max(
                (abs(r["balance_residual_Wm2"])
                 / (r["q_cond_Wm2"] + r["q_rad_Wm2"])
                 for r in rows
                 if (r["q_cond_Wm2"] + r["q_rad_Wm2"]) > RESIDUAL_REL_FLOOR_WM2),
                default=0.0),
            #  Same throughput floor as the relative residual, so the mean
            #  is not dragged around by elements carrying a few W/m^2. Each
            #  statistic also records the population it was taken over --
            #  an unlabelled mean is not evidence.
            "radiative_population_floor_Wm2": RESIDUAL_REL_FLOOR_WM2,
            "radiative_elements_used": sum(
                1 for r in rows
                if (r["q_cond_Wm2"] + r["q_rad_Wm2"]) > RESIDUAL_REL_FLOOR_WM2),
            "mean_radiative_fraction": _safe_mean(
                [r["q_rad_Wm2"] / (r["q_cond_Wm2"] + r["q_rad_Wm2"])
                 for r in rows
                 if (r["q_cond_Wm2"] + r["q_rad_Wm2"])
                 > RESIDUAL_REL_FLOOR_WM2]),
            "max_radiative_fraction": max(
                (r["q_rad_Wm2"] / (r["q_cond_Wm2"] + r["q_rad_Wm2"])
                 for r in rows
                 if (r["q_cond_Wm2"] + r["q_rad_Wm2"])
                 > RESIDUAL_REL_FLOOR_WM2),
                default=0.0),
            #  Net in-plane exchange, so the report states the lateral term
            #  rather than leaving it to be inferred.
            "mean_lateral_Wm2": statistics.fmean(
                r["q_lateral_Wm2"] for r in rows),
            "min_lateral_Wm2": min(r["q_lateral_Wm2"] for r in rows),
            "max_lateral_Wm2": max(r["q_lateral_Wm2"] for r in rows),
            "elements_losing_to_neighbours": sum(
                1 for r in rows if r["q_lateral_Wm2"] < 0.0),
            "elements_gaining_from_neighbours": sum(
                1 for r in rows if r["q_lateral_Wm2"] > 0.0),
        },
        "caveats": [
            # Parenthesised so each caveat reads as ONE list item rather than
            # as several adjacent strings (ruff ISC004).
            ("T_back is pinned to T_init by the solver's steady-state "
             "Dirichlet cold-face condition, so its structure-limit flag "
             "restates the boundary condition rather than predicting a "
             "transient back-face temperature. The informative outer-ply "
             "number is T_surface."),
            ("The zero-flux elements are real: their raw SPARTA per-element "
             "flux is negative DSMC noise, which axiom A1 floors at zero."),
        ],
    }


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Per-element IRVE-3 F-TPS conduction over the step-2200 "
                    "SPARTA snapshot.")
    parser.add_argument("--vtu", default=None,
                        help="snapshot VTU (must be the step-2200 file); "
                             "defaults to results/<tree>/paraview/surf_2200.vtu "
                             "so the file always matches --tree")
    parser.add_argument("--step", type=int, default=REQUIRED_STEP,
                        help="snapshot step; only 2200 is accepted")
    parser.add_argument("--tree", default=None, choices=sorted(PER_PLY_TREES),
                        help="name the results tree this snapshot came from; "
                             "its role and verdict are recorded in the "
                             "summary JSON so the provenance cannot be lost")
    parser.add_argument("--altitude-km", type=float,
                        default=REF_STEP2200_ALT_KM,
                        help="flight altitude for Q_SG [km] "
                             "(reference run step-2200 condition, read from "
                             "00_reference/validation_timeseries.csv)")
    parser.add_argument("--velocity-ms", type=float,
                        default=REF_STEP2200_VEL_MS,
                        help="flight velocity for Q_SG [m/s] "
                             "(reference run step-2200 condition; the Ada "
                             "Snapshot_Vel_Ms constant 3378.0 is a DIFFERENT "
                             "run's value and is deliberately NOT used)")
    parser.add_argument("--nose-radius-m", type=float, default=0.55,
                        help="nose bluntness radius for Q_SG [m] "
                             "(IRVE-3 Geometry_Parameters default)")
    parser.add_argument("--t-init-k", type=float, default=300.0,
                        help="pinned cold-face temperature T_init [K] "
                             "(the solver's Dirichlet boundary condition)")
    parser.add_argument("--t-inf-k", type=float, default=300.0,
                        help="radiative ambient T_inf [K]")
    parser.add_argument("--out-dir", default=None,
                        help="directory for the CSV/JSON outputs")
    parser.add_argument("--json", default=None,
                        help="write the summary JSON to this path")
    parser.add_argument("--no-lateral", action="store_true",
                        help="skip the lateral (in-plane) coupling and run "
                             "the legacy pure 1-D through-thickness solve")
    parser.add_argument("--no-profiles", action="store_true",
                        help="skip the per-element profile CSV")
    parser.add_argument("--limit", type=int, default=0,
                        help="solve only the first N elements (0 = all); "
                             "for smoke runs only, and reported as such")
    args = parser.parse_args(argv)

    # Resolve --vtu AFTER --tree so the default follows the claimed tree
    # (see guard_tree_provenance). With neither given, fall back to the
    # reference snapshot, which is the tree this driver was written for.
    if args.vtu is None:
        if args.tree is not None:
            args.vtu = os.path.join(
                _HERE, "..", "results", args.tree, "paraview",
                f"surf_{args.step}.vtu")
        else:
            args.vtu = DEFAULT_VTU

    snapshot = os.path.normpath(args.vtu)

    print("=" * 78)
    print("Per-element IRVE-3 F-TPS conduction -- SPARTA step-2200 snapshot")
    print("=" * 78)

    # Provenance must agree before anything is solved or reported.
    guard_tree_provenance(snapshot, args.tree)
    print(f"[GUARD] tree provenance OK: --tree {args.tree} <- "
          f"{os.path.relpath(snapshot, os.path.join(_HERE, '..'))}")

    # A3: refuse anything but the step-2200 snapshot, BEFORE any solve.
    guard_step_identity(snapshot, args.step)
    print(f"[GUARD] step identity OK: {os.path.basename(snapshot)}")

    n_points, n_cells, ke_raw = parse_vtu_cell_array(snapshot, "HeatFlux_Wm2")
    shape = verify_snapshot_shape(n_points, n_cells)
    print(f"[PARSE] {n_cells} cells, {n_points} points "
          f"({shape['axial_segments']} axial segments x "
          f"N_Theta={shape['n_theta']}); raw flux "
          f"min={min(ke_raw):.1f} max={max(ke_raw):.1f} "
          f"mean={statistics.fmean(ke_raw):.1f} W/m^2")
    print(f"[CAPACITY] driver holds no fixed element array and each solve is a "
          f"single-element Ada call, so {n_cells} elements need no Ada-side "
          f"array. Max_Surf_Elements=2000 (postprocessing.ads) is on a "
          f"different path and is not exercised here.")

    # A1/A4: the SG magnitude comes from Ada; the snapshot's own peak reading
    # is the reference that maps onto it.
    sg = W.sutton_graves_heat_flux(args.altitude_km, args.velocity_ms,
                                   args.nose_radius_m)
    q_sg = float(sg["heat_flux_Wm2"])
    ke_ref = max(ke_raw)
    print(f"[ADA] Sutton-Graves magnitude from Ada FFI: q_SG = {q_sg:.1f} W/m^2 "
          f"({q_sg / 1.0e4:.3f} W/cm^2) at h={args.altitude_km} km, "
          f"V={args.velocity_ms} m/s, Rn={args.nose_radius_m} m; "
          f"rho={sg['density_kgm3']:.4e} kg/m^3")
    print(f"[ADA] Ke_Ref = {ke_ref:.1f} W/m^2 (snapshot peak reading maps to "
          f"q_SG; negative readings floor at q_i = 0 per axiom A1)")

    if args.limit:
        print(f"[WARN] --limit {args.limit}: solving a SUBSET. Results are a "
              f"smoke run, not the full-surface answer.")
        ke_raw = ke_raw[: args.limit]

    layup_depth = sum(W.IRVE3_FTPS_PLY_THICKNESS_M)
    print(f"[LAYUP] IRVE-3 F-TPS: plies t(m)="
          f"{list(W.IRVE3_FTPS_PLY_THICKNESS_M)} k="
          f"{list(W.IRVE3_FTPS_PLY_THERMAL_K)} -> total {layup_depth:.5f} m "
          f"({layup_depth / 0.0254:.4f} in), eps="
          f"{W.IRVE3_FTPS_EMISSIVITY}, structure limit "
          f"{W.IRVE3_FTPS_STRUCT_LIMIT_K:.2f} K "
          f"({W.IRVE3_FTPS_STRUCT_LIMIT_K - 273.15:.1f} degC)")
    print(f"[BC] T_init = {args.t_init_k} K (pinned cold face), "
          f"T_inf = {args.t_inf_k} K (radiative ambient)")

    # -- Lateral (in-plane) coupling -------------------------------------
    #  The mesh supplies the topology, the layup supplies the conductance;
    #  both are measured/derived here rather than assumed. --no-lateral runs
    #  the legacy pure 1-D solve so the two can be diffed directly.
    adjacency: list[list[tuple[int, float]]] | None = None
    sheet_wk = 0.0
    if args.no_lateral:
        print("[LATERAL] disabled by --no-lateral: pure 1-D through-thickness "
              "solve, every element thermally isolated")
    else:
        points, cells = parse_vtu_geometry(args.vtu)
        adjacency, mesh_stats = build_adjacency(points, cells)
        sheet = structural_sheet_conductance()
        sheet_wk = sheet["sheet_structural_W_K"]
        print(f"[MESH] {mesh_stats['cells']} cells, "
              f"{mesh_stats['edges']} edges, "
              f"{mesh_stats['neighbour_pairs']} neighbour pairs, "
              f"{mesh_stats['boundary_edges']} boundary edges (no partner), "
              f"{mesh_stats['isolated_cells']} isolated cells, "
              f"{mesh_stats['non_manifold_edges']} non-manifold")
        print(f"[MESH] structural plies only: "
              f"S = sum(k*t) = {sheet_wk:.6e} W/K across "
              f"{int(sheet['structural_ply_count'])} layer(s); the same sum "
              f"over ALL five plies would be "
              f"{sheet['sheet_total_W_K']:.6e} W/K "
              f"({(sheet['sheet_total_W_K'] - sheet_wk) / sheet_wk * 100.0:.1f} "
              f"% more), which the owner's structural-only decision excludes")
        if mesh_stats["isolated_cells"]:
            print(f"[MESH][WARN] {mesh_stats['isolated_cells']} cell(s) share "
                  f"no edge with any other cell; they stay 1-D by construction")

    rows = solve_all_elements(ke_raw, q_sg, ke_ref,
                              write_profiles=not args.no_profiles,
                              t_init=args.t_init_k, t_inf=args.t_inf_k,
                              adjacency=adjacency, sheet_wk=sheet_wk)
    summary = summarise(
        rows, q_sg, shape, snapshot,
        tree=args.tree,
        altitude_km=args.altitude_km,
        velocity_ms=args.velocity_ms,
    )

    out_dir = args.out_dir or os.path.join(_HERE, "..", "results", "tps_conduction")
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    element_csv = os.path.join(out_dir, f"tps_step{args.step}_elements.csv")
    write_element_csv(element_csv, rows)
    print(f"[OUT] {element_csv}")
    if not args.no_profiles:
        profile_csv = os.path.join(out_dir, f"tps_step{args.step}_profiles.csv")
        written = write_profile_csv(profile_csv, rows)
        print(f"[OUT] {profile_csv} ({written} rows = "
              f"{len(rows)} elements x {written // max(1, len(rows))} samples)")

    #  F123/F124: this table had no writer, so it drifted silently.  Emit it
    #  from the same layup the solve used, so it cannot disagree with the
    #  solver, and delete the orphan's authority for good.
    layers_csv = os.path.join(out_dir, f"tps_step{args.step}_layers.csv")
    layers_written = write_layers_csv(
        layers_csv, rows,
        W.IRVE3_FTPS_PLY_THICKNESS_M,
        W.IRVE3_FTPS_PLY_THERMAL_K,
        W.IRVE3_FTPS_PLY_NAMES)
    print(f"[OUT] {layers_csv} ({layers_written} rows = "
          f"{len(rows)} elements x {layers_written // max(1, len(rows))} plies, "
          f"written from the solved layup -- no longer an orphan)")

    json_path = args.json or os.path.join(out_dir, f"tps_step{args.step}_summary.json")
    os.makedirs(os.path.dirname(os.path.normpath(json_path)), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(f"[OUT] {json_path}")

    print("-" * 78)
    print(f"elements solved            : {summary['elements']}")
    print(f"peak q_SG                  : {summary['q_peak_Wm2']:.1f} W/m^2 "
          f"({summary['q_peak_Wcm2']:.3f} W/cm^2) vs 30 W/cm^2 1st-gen "
          f"rating "
          f"{NEXTEL_BF20_RATING_WCM2:.0f} W/cm^2 -> "
          f"{'WITHIN' if summary['peak_within_nextel_rating'] else 'OVER'}")
    print(f"peak element               : #{summary['peak_element']['element']} "
          f"T_s={summary['peak_element']['t_surface_K']:.1f} K "
          f"T_back={summary['peak_element']['t_back_K']:.1f} K")
    print(f"T_s  min/mean/max          : {summary['t_surface_K']['min']:.1f} / "
          f"{summary['t_surface_K']['mean']:.1f} / "
          f"{summary['t_surface_K']['max']:.1f} K")
    print(f"T_back min/mean/max        : {summary['t_back_K']['min']:.1f} / "
          f"{summary['t_back_K']['mean']:.1f} / "
          f"{summary['t_back_K']['max']:.1f} K")
    print(f"elements with q_i == 0     : {summary['elements_at_zero_flux']} "
          f"(of which {summary['elements_with_negative_raw_flux']} had negative "
          f"raw DSMC flux)")
    print(f"T_s over {W.IRVE3_FTPS_STRUCT_LIMIT_K:.2f} K limit  : "
          f"{summary['elements_t_surface_over_struct_limit']} / "
          f"{summary['elements']}")
    print(f"T_back over limit          : "
          f"{summary['elements_t_back_over_struct_limit']} / "
          f"{summary['elements']}  (pinned by the boundary condition -- see "
          f"caveats in the JSON)")
    bal = summary["surface_energy_balance"]
    print(f"surface balance closure    : max |q_conv+q_lateral-q_cond-q_rad| = "
          f"{bal['residual_Wm2_abs_max']:.3e} W/m^2 "
          f"(mean {bal['residual_Wm2_abs_mean']:.3e}); worst relative "
          f"{bal['residual_rel_max']:.3e}")
    print(f"re-radiation share of q    : mean "
          f"{bal['mean_radiative_fraction'] * 100.0:.2f}%, "
          f"max {bal['max_radiative_fraction'] * 100.0:.2f}% "
          f"(over {bal['radiative_elements_used']} elements carrying > "
          f"{bal['radiative_population_floor_Wm2']:g} W/m^2) "
          f"({100.0 - bal['mean_radiative_fraction'] * 100.0:.2f}% conducted "
          f"into the stack and laterally to neighbours)")
    print(f"lateral exchange           : mean "
          f"{bal['mean_lateral_Wm2']:+.3f} W/m^2, range "
          f"[{bal['min_lateral_Wm2']:+.3f}, {bal['max_lateral_Wm2']:+.3f}] "
          f"W/m^2; {bal['elements_gaining_from_neighbours']} elements gain "
          f"from a neighbour, {bal['elements_losing_to_neighbours']} shed "
          f"heat into theirs")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
