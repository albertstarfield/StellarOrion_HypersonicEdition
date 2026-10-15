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
def solve_all_elements(
    ke_raw: list[float],
    q_sg: float,
    ke_ref: float,
    write_profiles: bool,
    t_init: float,
    t_inf: float,
) -> list[dict[str, Any]]:
    """Call the Ada solver once per element and collect its outputs.

    The IRVE-3 layup arguments are left at their ``tps_conduction`` defaults,
    which ARE the IRVE-3 F-TPS schedule (axiom A2). They are not restated
    here, so there is exactly one copy of the ply table in the codebase.
    """
    if not (ke_ref > 0.0):
        raise SystemExit(
            f"[GUARD] Ke_Ref = {ke_ref} is not positive; it is the divisor "
            f"that maps the hottest snapshot reading onto Q_SG (axiom A4).")

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(ke_raw):
        result = W.tps_conduction(q_sg_scale=q_sg, ke_raw=raw, ke_ref=ke_ref,
                                  t_init=t_init, t_inf=t_inf)
        if not (0.0 <= result["q_sg"] <= q_sg * (1.0 + 1.0e-6)):
            raise SystemExit(
                f"[GUARD] element {index}: Ada returned q_SG="
                f"{result['q_sg']} outside [0, Q_SG={q_sg}]; the clamp in "
                f"axiom A1 was not honoured.")
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
              "t_back_exceeds_struct_limit"]
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
    parser.add_argument("--vtu", default=DEFAULT_VTU,
                        help="snapshot VTU (must be the step-2200 file)")
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
    parser.add_argument("--no-profiles", action="store_true",
                        help="skip the per-element profile CSV")
    parser.add_argument("--limit", type=int, default=0,
                        help="solve only the first N elements (0 = all); "
                             "for smoke runs only, and reported as such")
    args = parser.parse_args(argv)

    snapshot = os.path.normpath(args.vtu)

    print("=" * 78)
    print("Per-element IRVE-3 F-TPS conduction -- SPARTA step-2200 snapshot")
    print("=" * 78)

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

    rows = solve_all_elements(ke_raw, q_sg, ke_ref,
                              write_profiles=not args.no_profiles,
                              t_init=args.t_init_k, t_inf=args.t_inf_k)
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
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
