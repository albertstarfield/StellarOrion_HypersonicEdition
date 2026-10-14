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
    The snapshot is the validated DSMC single-point case: h = 51.8 km,
    V = 3378 m/s, nose bluntness radius 0.55 m (the IRVE-3 Geometry_Parameters
    default, stellarorion_types.ads:284). The same pair appears as
    Snapshot_Alt_Km / Snapshot_Vel_Ms in stellarorion_optimization.ads:404-405
    and in VALIDATION_Sep_2_2026.md Sec 3.1; both are CLI-overridable here so a
    change to those Ada constants is a visible flag change, not a silent drift.

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
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC_PY = os.path.normpath(os.path.join(_HERE, "..", "src", "python"))
if _SRC_PY not in sys.path:
    sys.path.insert(0, _SRC_PY)

import ada_pinn_wrapper as W  # imported after the sys.path insert above

REQUIRED_STEP = 2200
DEFAULT_VTU = os.path.join(
    _HERE, "..", "results", "validation_optimized", "paraview",
    f"surf_{REQUIRED_STEP}.vtu")

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


def _flux_of(row: dict[str, Any]) -> float:
    """Sort key: the Sutton-Graves flux this element received [W/m^2]."""
    return float(row["q_sg_Wm2"])


def summarise(rows: list[dict[str, Any]], q_sg: float, shape: dict[str, int],
              snapshot: str) -> dict[str, Any]:
    """Aggregate statistics plus the two caveats a reader must not miss."""
    q_values = [r["q_sg_Wm2"] for r in rows]
    t_s = [r["t_surface_K"] for r in rows]
    t_b = [r["t_back_K"] for r in rows]
    peak = max(rows, key=_flux_of)
    zero_flux = sum(1 for v in q_values if v == 0.0)
    negative_raw = sum(1 for r in rows if r["ke_raw_Wm2"] < 0.0)
    return {
        "snapshot": os.path.basename(snapshot),
        "elements": len(rows),
        "snapshot_shape": shape,
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
    parser.add_argument("--altitude-km", type=float, default=51.8,
                        help="flight altitude for Q_SG [km] "
                             "(DSMC step-2200 condition)")
    parser.add_argument("--velocity-ms", type=float, default=3378.0,
                        help="flight velocity for Q_SG [m/s]")
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
    summary = summarise(rows, q_sg, shape, snapshot)

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
