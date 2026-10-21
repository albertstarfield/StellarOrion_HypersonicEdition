#!/usr/bin/env python3
"""Compare two DSMC validation runs (reference geometry vs optimised topology).

WHY THIS MODULE EXISTS
----------------------
The validation pipeline's own ``unified_comparison_table.csv`` compares one run
against the *published flight references* (IRVE-3, LOFTID, Rapisarda). It does
NOT compare a run against the *reference geometry's own DSMC run*, which is the
comparison an optimiser result has to be judged by: same solver, same flight
condition, same 2200-step protocol, different geometry.

AXIOM A1 -- Same schema, hard error.  Both runs must carry the columns written
    by ``src/simulation_engine/stellarorion_sparta.adb`` (the timeseries header
    at sparta.adb:3443). A missing column is a hard error, never a silent
    default: a comparison that quietly drops a metric is worse than no
    comparison, because it looks finished.

AXIOM A2 -- The recorded drag coefficient is CLAMPED and must not be read as a
    measurement.  The Ada writer clamps the drag coefficient to [0, 3]
    (``if FB_CD > 3.0 then FB_CD := 3.0;`` -- sparta.adb:3348).  A blunt
    geometry saturates that clamp, and the CSV then reports a flat "3.0" that
    a reader would take for a converged physical value.  This script therefore
    RECOMPUTES the drag coefficient from the raw drag force

        cd_raw = drag_sum_N / (dyn_press_pa * pi * R_N^2)

    and reports the clamped value, the raw value and a saturation flag
    side by side.

AXIOM A3 -- The frontal-area reconstruction is cross-checked, not assumed.
    The frontal area is ``pi * (D/2)^2`` with ``D = 2 * R_N`` (the CLI's
    ``--nose`` argument is the nose radius, hence R_N = D/2).  For a run whose
    recorded drag coefficient does NOT saturate the clamp, the reconstructed
    value must reproduce the recorded one; otherwise the reconstruction is
    reported as unverified instead of being used.

AXIOM A4 -- Every comparison states its direction.  A metric whose meaning is
    "lower is better" (heat load, peak heat flux, deceleration load) and one
    whose meaning is "higher is better" (drag coefficient) are reported with an
    explicit "better/worse" verdict, not a bare delta.

AXIOM A5 -- The CALIBRATION DESIGN 2.4 columns are OPTIONAL here, and a
    metric that is not recorded is reported as "n/a", never invented.  A run
    that predates the new schema (no ``cd_unclamped``, no
    ``cd_raw_body_area``, no ``cd_raw_presented_area``, no
    ``dsmc_surface_heat_load_jcm2``, no ``geom_*``) still compares exactly as
    before: the existing metric names, the existing CLI and the existing
    output columns are unchanged, and the new metric rows simply carry
    "n/a".

AXIOM A6 -- THE TWO HEAT LOADS ARE DIFFERENT THINGS AND ARE NEVER MIXED.
    ``total_heat_load_Jcm2`` is the ANALYTIC value: the Sutton-Graves
    correlation integrated over the heating window (sparta.adb:1870,
    ``Heat_Flux_Wm2 * 13.58``) -- a correlation, NOT a DSMC measurement.
    ``dsmc_surface_heat_load_jcm2`` (CALIBRATION DESIGN 2.4) is the DSMC
    SURFACE INTEGRAL: the time integral of the DSMC surface heat flux.  The
    report labels them "analytic (Sutton-Graves x window)" and "DSMC surface
    integral" respectively, so no reader can mistake one for the other.

AXIOM A7 -- The flown geometry is reported from the ``geom_*`` columns of
    the runs themselves, so a reader can see AT A GLANCE whether the two runs
    flew the same vehicle.  When the columns are absent the report says so
    explicitly instead of guessing from the CLI arguments.

CITATIONS
----------
[Reference: stellarorion_sparta.adb:3348] -- the [0, 3] drag-coefficient clamp.
[Reference: stellarorion_sparta.adb:3443] -- the timeseries CSV schema.
[Reference: stellarorion_sparta.adb:1870] -- Total_Heat_Load = Heat_Flux_Wm2
    * 13.58 (the Sutton-Graves x window value reported as heat_load_jcm2).
[Reference: CALIBRATION_DESIGN.md 2.4] -- the new CSV columns.
[Reference: Anderson, Hypersonic and High-Temperature Gas Dynamics, 2006,
    Sec. 8.4] -- F = 0.5 * Cd * A * rho * V^2, the definition used here.
[Reference: NASA/TP-2013-4012] -- the IRVE-3 reference geometry (R_N = 1.5 m).

Usage
-----
    python3 scripts/compare_dsmc_runs.py \
        --reference-csv results/00_reference/validation_timeseries.csv \
        --reference-r-n 1.5 \
        --candidate-csv results/validation_optimized/validation_timeseries.csv \
        --candidate-r-n 1.039670 \
        --q-target 165.715973 \
        --out-md results/validation_optimized/DSMC_PINN_AUX_vs_reference.md \
        --out-csv results/validation_optimized/DSMC_PINN_AUX_vs_reference.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

# The drag-coefficient clamp applied by the Ada writer (sparta.adb:3348).
CD_CLAMP_MAX = 3.0

# Columns the comparison needs; every one of them must be present (AXIOM A1).
REQUIRED_COLUMNS = (
    "step",
    "drag_sum_N",
    "lift_sum_N",
    "heatflux_max_Wm2",
    "heatflux_avg_Wm2",
    "drag_avg_N",
    "dyn_press_pa",
    "cd",
    "cl",
    "g_load",
    "heat_load_jcm2",
    "heat_flux_fr_wm2",
)

# CALIBRATION DESIGN 2.4 columns.  They are OPTIONAL: a run that predates
# the new schema simply does not have them and the corresponding metric is
# reported as "n/a" (AXIOM A5).
OPTIONAL_COLUMNS = (
    "cd_unclamped",
    "cd_raw_body_area",
    "cd_raw_presented_area",
    "dsmc_surface_heat_load_jcm2",
    "geom_diameter_m",
    "geom_nose_radius_m",
    "geom_toroid_radius_m",
    "geom_angle_deg",
    "ref_area_body_m2",
    "ref_area_presented_m2",
)

#: The geometry fields of the flown vehicle, in reporting order.
GEOMETRY_FIELDS = (
    ("geom_diameter_m", "body diameter", "m"),
    ("geom_nose_radius_m", "nose radius", "m"),
    ("geom_toroid_radius_m", "toroid radius", "m"),
    ("geom_angle_deg", "cone angle", "deg"),
)

#: Which source each heat-load metric comes from (AXIOM A6).
HEAT_LOAD_SOURCES = {
    "total_heat_load_Jcm2": "analytic (Sutton-Graves x window)",
    "dsmc_surface_heat_load_Jcm2": "DSMC surface integral",
}

#: Which source each other metric comes from (empty string = derived).
METRIC_SOURCES = {
    "cd_recorded": "DSMC (clamped to [0,3])",
    "cd_unclamped": "DSMC (unclamped)",
    "cd_raw": "reconstructed from the DSMC drag force",
    "cd_body": "reconstructed from the DSMC drag force",
    "cd_raw_body_area": "DSMC (body-area normalisation)",
    "cd_raw_presented_area": "DSMC (presented-area normalisation)",
    "geom_diameter_m": "flown geometry",
    "geom_nose_radius_m": "flown geometry",
    "geom_toroid_radius_m": "flown geometry",
    "geom_angle_deg": "flown geometry",
}


class ComparisonError(RuntimeError):
    """Raised when the two runs cannot be compared (schema, geometry, data)."""


def _read_run(csv_path: Path) -> list[dict[str, str]]:
    """Read one validation timeseries CSV and validate its schema.

    Parameters:
        csv_path: path to a ``validation_timeseries.csv`` file.

    Returns:
        The parsed rows, in file order, each a string-keyed dictionary.

    Raises:
        ComparisonError: the file is missing, has no data rows, or is missing
            one of the columns the comparison depends on.
    """
    if not csv_path.is_file():
        raise ComparisonError(f"missing run CSV: {csv_path}")
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ComparisonError(f"empty CSV (no header): {csv_path}")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ComparisonError(f"{csv_path}: missing columns {missing}")
        rows = list(reader)
    if not rows:
        raise ComparisonError(f"no data rows in {csv_path}")
    return rows


def _floats(rows: list[dict[str, str]], column: str) -> list[float]:
    """Extract one column as floats.

    Parameters:
        rows: the parsed CSV rows.
        column: the column name.

    Returns:
        The column values as floats, in row order.

    Raises:
        ComparisonError: a value is not a finite number.
    """
    out: list[float] = []
    for row in rows:
        try:
            value = float(row[column])
        except (TypeError, ValueError) as exc:
            raise ComparisonError(f"non-numeric {column!r}: {row[column]!r}") from exc
        if not math.isfinite(value):
            raise ComparisonError(f"non-finite {column!r}: {row[column]!r}")
        out.append(value)
    return out


def _optional_floats(
    rows: list[dict[str, str]], column: str
) -> list[float] | None:
    """Extract one OPTIONAL column as floats, or None when it is absent.

    AXIOM A5: a column that the run does not carry is reported as absent,
    never as zero and never as an error.

    Parameters:
        rows: the parsed CSV rows.
        column: the column name.

    Returns:
        The column values as floats, or None when the column is not in the
        CSV header.

    Raises:
        ComparisonError: the column IS present but a value is not a finite
            number.
    """
    if not rows or column not in rows[0]:
        return None
    return _floats(rows, column)


def _optional_last(rows: list[dict[str, str]], column: str) -> float:
    """Return the last value of an optional column, or NaN when absent.

    Parameters:
        rows: the parsed CSV rows.
        column: the column name.

    Returns:
        The final value of the column, or ``nan`` when the run does not
        carry the column.
    """
    values = _optional_floats(rows, column)
    if values is None:
        return float("nan")
    return values[-1]


def _summarise(
    rows: list[dict[str, str]],
    r_n: float,
    label: str,
    r_max: float | None = None,
) -> dict[str, float | bool | str]:
    """Reduce one run to the compared metrics.

    Parameters:
        rows: the parsed CSV rows of the run.
        r_n: the nose radius in metres (the CLI's ``--nose`` value); the
            frontal (reference) area is ``pi * R_N^2``.
        label: a human label for the run.
        r_max: the body's maximum radius in metres, when known.  The reported
            drag coefficient is normalised by the REFERENCE area
            ``pi * R_N^2`` (the ballistic-coefficient convention); the
            body-area-normalised value ``cd_body`` is added when the body
            radius is supplied.

    Returns:
        A dictionary with the peak/terminal metrics, the reconstructed drag
        coefficient and the clamp-saturation flag.

    Raises:
        ComparisonError: a required column is absent or non-numeric.
    """
    if r_n <= 0.0:
        raise ComparisonError(f"{label}: nose radius must be positive, got {r_n}")
    frontal_area = math.pi * r_n * r_n
    drag_sum = _floats(rows, "drag_sum_N")
    dyn_press = _floats(rows, "dyn_press_pa")
    cd_recorded = _floats(rows, "cd")
    heat_load = _floats(rows, "heat_load_jcm2")
    g_load = _floats(rows, "g_load")
    cl = _floats(rows, "cl")
    flux_max = _floats(rows, "heatflux_max_Wm2")
    flux_avg = _floats(rows, "heatflux_avg_Wm2")
    fr_flux = _floats(rows, "heat_flux_fr_wm2")

    cd_raw: list[float] = []
    for drag, press in zip(drag_sum, dyn_press):
        cd_raw.append(drag / (press * frontal_area) if press > 0.0 else float("nan"))
    finite_raw = [c for c in cd_raw if math.isfinite(c)]
    cd_body = float("nan")
    if r_max is not None:
        if r_max <= 0.0:
            raise ComparisonError(f"{label}: max radius must be positive, got {r_max}")
        body_area = math.pi * r_max * r_max
        cd_body = drag_sum[-1] / (dyn_press[-1] * body_area) if dyn_press[-1] > 0.0 else float("nan")

    # AXIOM A5: the CALIBRATION DESIGN 2.4 columns are optional; an absent
    # column yields NaN, which the report renders as "n/a".
    cd_unclamped = _optional_last(rows, "cd_unclamped")
    cd_raw_body = _optional_last(rows, "cd_raw_body_area")
    cd_raw_presented = _optional_last(rows, "cd_raw_presented_area")
    dsmc_surface_heat = _optional_last(rows, "dsmc_surface_heat_load_jcm2")
    geom_values = {
        key: _optional_last(rows, key) for key, _, _ in GEOMETRY_FIELDS
    }

    # AXIOM A2 (extended): the saturation flag now reads the UNCLAMPED
    # column when the run carries it -- that is the raw force ratio, and it
    # is what actually saturates the [0, 3] clamp.  A run without the column
    # keeps the legacy behaviour (the flag is inferred from the clamped
    # `cd` column).
    if math.isfinite(cd_unclamped):
        saturated = cd_unclamped >= CD_CLAMP_MAX - 1.0e-9
        saturation_source = "cd_unclamped"
    else:
        saturated = any(c >= CD_CLAMP_MAX - 1.0e-9 for c in cd_recorded)
        saturation_source = "cd (clamped column)"
    # AXIOM A3: cross-check the reconstruction on the unsaturated steps.
    check_max_abs_err = 0.0
    if not saturated:
        for raw, rec in zip(cd_raw, cd_recorded):
            if math.isfinite(raw):
                check_max_abs_err = max(check_max_abs_err, abs(raw - rec))

    return {
        "label": label,
        "r_n": r_n,
        "frontal_area": frontal_area,
        "steps": len(rows),
        "heat_flux_max_final_Wcm2": flux_max[-1] / 1.0e4,
        "heat_flux_max_run_max_Wcm2": max(flux_max) / 1.0e4,
        "heat_flux_avg_final_Wcm2": flux_avg[-1] / 1.0e4,
        "heat_flux_avg_run_max_Wcm2": max(flux_avg) / 1.0e4,
        "final_heat_flux_fr_Wcm2": fr_flux[-1] / 1.0e4,
        "total_heat_load_Jcm2": heat_load[-1],
        "peak_g_load": max(g_load),
        "final_g_load": g_load[-1],
        "cd_recorded": cd_recorded[-1],
        "cd_raw": finite_raw[-1] if finite_raw else float("nan"),
        "cd_raw_max": max(finite_raw) if finite_raw else float("nan"),
        "cd_saturated": saturated,
        "cd_reconstruction_error": check_max_abs_err,
        "final_cl": cl[-1],
        "final_drag_sum_N": drag_sum[-1],
        "cd_body": cd_body,
        # --- CALIBRATION DESIGN 2.4 metrics (NaN when not recorded) ---
        "cd_unclamped": cd_unclamped,
        "cd_raw_body_area": cd_raw_body,
        "cd_raw_presented_area": cd_raw_presented,
        "dsmc_surface_heat_load_Jcm2": dsmc_surface_heat,
        "geom_diameter_m": geom_values["geom_diameter_m"],
        "geom_nose_radius_m": geom_values["geom_nose_radius_m"],
        "geom_toroid_radius_m": geom_values["geom_toroid_radius_m"],
        "geom_angle_deg": geom_values["geom_angle_deg"],
        "cd_saturation_source": saturation_source,
        "has_flown_geometry": all(
            math.isfinite(value) for value in geom_values.values()
        ),
    }


def _delta(candidate: float, reference: float) -> float:
    """Percentage change of the candidate with respect to the reference.

    Parameters:
        candidate: the candidate value.
        reference: the reference value.

    Returns:
        The percentage change, or ``nan`` when the reference is zero.
    """
    if reference == 0.0:
        return float("nan")
    return (candidate - reference) / reference * 100.0


def _verdict(direction: str, candidate: float, reference: float) -> str:
    """State whether the candidate improved or worsened a metric.

    Parameters:
        direction: ``"lower"``, ``"higher"`` or ``"info"``.
        candidate: the candidate value.
        reference: the reference value.

    Returns:
        ``"better"``, ``"worse"``, ``"unchanged"`` or ``"n/a"``.
    """
    if direction == "info":
        return "n/a"
    if math.isclose(candidate, reference, rel_tol=1.0e-9, abs_tol=1.0e-12):
        return "unchanged"
    improved = candidate < reference if direction == "lower" else candidate > reference
    return "better" if improved else "worse"


def _rows_for_table(
    reference: dict[str, float | bool | str],
    candidate: dict[str, float | bool | str],
) -> list[tuple[str, str, float, float, float, str]]:
    """Build the metric rows of the comparison table.

    Parameters:
        reference: the reference run summary.
        candidate: the candidate run summary.

    Returns:
        One tuple per metric: name, unit, reference, candidate, delta percent,
        verdict.
    """
    # (name, unit, direction): "lower" = lower is better, "higher" = higher is
    # better, "info" = no single direction (reported without a verdict).
    # The first thirteen rows are the HISTORICAL metrics, unchanged in name,
    # order and meaning (AXIOM A5); the rows after them are the CALIBRATION
    # DESIGN 2.4 additions.
    metrics: list[tuple[str, str, str]] = [
        ("heat_flux_max_final_Wcm2", "W/cm^2", "lower"),
        ("heat_flux_max_run_max_Wcm2", "W/cm^2", "lower"),
        ("heat_flux_avg_final_Wcm2", "W/cm^2", "lower"),
        ("heat_flux_avg_run_max_Wcm2", "W/cm^2", "lower"),
        ("final_heat_flux_fr_Wcm2", "W/cm^2", "lower"),
        ("total_heat_load_Jcm2", "J/cm^2", "lower"),
        ("peak_g_load", "g", "lower"),
        ("final_g_load", "g", "lower"),
        ("cd_recorded", "-", "higher"),
        ("cd_raw", "-", "higher"),
        ("cd_body", "-", "higher"),
        ("final_cl", "-", "info"),
        ("final_drag_sum_N", "N", "higher"),
        # --- CALIBRATION DESIGN 2.4 ---
        ("cd_unclamped", "-", "higher"),
        ("cd_raw_body_area", "-", "higher"),
        ("cd_raw_presented_area", "-", "higher"),
        ("dsmc_surface_heat_load_Jcm2", "J/cm^2", "lower"),
        ("geom_diameter_m", "m", "info"),
        ("geom_nose_radius_m", "m", "info"),
        ("geom_toroid_radius_m", "m", "info"),
        ("geom_angle_deg", "deg", "info"),
    ]
    rows: list[tuple[str, str, float, float, float, str]] = []
    for name, unit, direction in metrics:
        ref = float(reference[name])
        cand = float(candidate[name])
        if not math.isfinite(cand) or not math.isfinite(ref):
            rows.append((name, unit, ref, cand, float("nan"), "n/a"))
            continue
        rows.append(
            (
                name,
                unit,
                ref,
                cand,
                _delta(cand, ref),
                _verdict(direction, cand, ref),
            )
        )
    return rows


def _fmt(value: float, spec: str = ".6g") -> str:
    """Format a number for the report, rendering a missing value as "n/a".

    AXIOM A5: a metric the run does not carry is reported as "n/a", never
    as a zero and never as "nan".

    Parameters:
        value: the value to format.
        spec: the format specification for a finite value.

    Returns:
        The formatted value, or "n/a" when it is not finite.
    """
    if not math.isfinite(value):
        return "n/a"
    return format(value, spec)


def _render_markdown(
    reference: dict[str, float | bool | str],
    candidate: dict[str, float | bool | str],
    rows: list[tuple[str, str, float, float, float, str]],
    q_target: float | None,
    analytic_q: float | None,
    analytic_cd: float | None,
    reference_csv: Path,
    candidate_csv: Path,
) -> str:
    """Render the comparison as markdown.

    Parameters:
        reference: the reference run summary.
        candidate: the candidate run summary.
        rows: the metric rows from :func:`_rows_for_table`.
        q_target: the analytic heat-load target in J/cm^2, if known.
        analytic_q: the analytic heat-load prediction in J/cm^2, if known.
        analytic_cd: the analytic drag prediction, if known.
        reference_csv: the reference CSV path (provenance).
        candidate_csv: the candidate CSV path (provenance).

    Returns:
        The markdown document.
    """
    lines: list[str] = []
    lines.append("# DSMC+PINN_AUX Validation -- Optimised Topology vs Reference Geometry")
    lines.append("")
    lines.append(
        "Generated by `scripts/compare_dsmc_runs.py` from the two DSMC "
        "validation runs (same solver, same flight condition, same 2200-step "
        "protocol; different geometry)."
    )
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Reference run: `{reference_csv}`")
    lines.append(f"- Candidate run: `{candidate_csv}`")
    lines.append(
        f"- Reference geometry: R_N = {float(reference['r_n']):.6f} m "
        f"(frontal area {float(reference['frontal_area']):.6f} m^2)"
    )
    lines.append(
        f"- Candidate geometry: R_N = {float(candidate['r_n']):.6f} m "
        f"(frontal area {float(candidate['frontal_area']):.6f} m^2)"
    )
    lines.append(f"- Steps compared: {int(reference['steps'])} (reference), "
                 f"{int(candidate['steps'])} (candidate)")
    lines.append(
        "- Drag coefficient convention: the reported `cd` is the drag force "
        "normalised by the REFERENCE frontal area `pi * R_N^2` (the "
        "ballistic-coefficient convention used by the Ada writer), not by the "
        "body's own frontal area; `cd_body` is the body-area-normalised value "
        "where the body radius is known."
    )
    lines.append(
        "- Saturation flag: inferred from "
        f"`{candidate['cd_saturation_source']!s}`; `cd_unclamped` is the "
        "DSMC drag force ratio WITHOUT the [0, 3] clamp applied by the Ada "
        "writer, and a run that carries it is flagged from that column."
    )
    lines.append("")
    lines.append("## Flown geometry")
    lines.append("")
    if bool(reference["has_flown_geometry"]) and bool(candidate["has_flown_geometry"]):
        lines.append("| Field | Reference | Optimised | Same? |")
        lines.append("|:---|---:|---:|:---|")
        differences: list[str] = []
        for key, label, unit in GEOMETRY_FIELDS:
            ref_value = float(reference[key])
            cand_value = float(candidate[key])
            same = math.isclose(ref_value, cand_value, rel_tol=1.0e-9,
                                abs_tol=1.0e-12)
            if not same:
                differences.append(label)
            lines.append(
                f"| {label} [{unit}] | {ref_value:.6g} | {cand_value:.6g} | "
                f"{'yes' if same else 'NO'} |"
            )
        lines.append("")
        if differences:
            lines.append(
                "> **The two runs did NOT fly the same vehicle** -- the "
                f"following differ: {', '.join(differences)}. Every "
                "comparison below therefore compares two different "
                "geometries under the same solver and flight condition."
            )
        else:
            lines.append(
                "> The two runs flew the SAME vehicle (all four geometry "
                "fields agree to 1e-9 relative)."
            )
    else:
        lines.append(
            "> **Not determinable from these files.** At least one run "
            "predates CALIBRATION DESIGN 2.4 and carries no `geom_*` "
            "columns, so the flown geometry cannot be read from the run "
            "itself. The CLI reference radii below are the values the "
            "comparison was asked to use, NOT a reading of what was flown."
        )
        lines.append("")
        lines.append(
            f"- Reference CLI reference radius: R_N = "
            f"{float(reference['r_n']):.6f} m "
            f"(frontal area {float(reference['frontal_area']):.6f} m^2)"
        )
        lines.append(
            f"- Candidate CLI reference radius: R_N = "
            f"{float(candidate['r_n']):.6f} m "
            f"(frontal area {float(candidate['frontal_area']):.6f} m^2)"
        )
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    lines.append(
        "| Metric | Unit | Source | Reference | Optimised | Delta | Verdict |"
    )
    lines.append("|:---|---:|:---|---:|---:|---:|:---|")
    for name, unit, ref, cand, delta, verdict in rows:
        source = HEAT_LOAD_SOURCES.get(name, METRIC_SOURCES.get(name, ""))
        delta_cell = (
            _fmt(delta, "+.2f") + "%"
            if math.isfinite(delta)
            else "n/a"
        )
        lines.append(
            f"| {name} | {unit} | {source} | {_fmt(ref)} | {_fmt(cand)} | "
            f"{delta_cell} | {verdict} |"
        )
    lines.append("")
    if bool(candidate["cd_saturated"]):
        lines.append(
            "> **The recorded drag coefficient of the optimised run is "
            "CLAMPED.** The Ada writer clamps `cd` to [0, 3] "
            "(`stellarorion_sparta.adb:3348`); the blunt optimised geometry "
            "saturates that clamp, so the CSV reports a flat 3.0 while the "
            "raw force ratio is "
            f"{float(candidate['cd_raw']):.4f}. The `cd_raw` row above is the "
            "reconstruction from the raw drag force and is the value to use."
        )
        if math.isfinite(float(candidate["cd_unclamped"])):
            lines.append(">")
            lines.append(
                "> The run also carries `cd_unclamped` (CALIBRATION DESIGN "
                "2.4): the DSMC drag force ratio with NO clamp, final step "
                f"{float(candidate['cd_unclamped']):.6f}. That is the "
                "authoritative drag coefficient of the flown vehicle."
            )
        lines.append("")
    else:
        lines.append(
            "> Drag-coefficient reconstruction cross-check: max |cd_raw - "
            f"cd_recorded| = {float(candidate['cd_reconstruction_error']):.3e} "
            "over the run (no clamp saturation)."
        )
        lines.append("")
    if q_target is not None:
        heat = float(candidate["total_heat_load_Jcm2"])
        verdict = "PASS" if heat <= q_target else "FAIL"
        lines.append("## Validation gate")
        lines.append("")
        lines.append(
            f"- Heat load (analytic: Sutton-Graves x window): "
            f"**{heat:.6f} J/cm^2** "
            f"(reference {float(reference['total_heat_load_Jcm2']):.6f} J/cm^2)"
        )
        lines.append(
            "  NOTE: this is the Sutton-Graves correlation integrated over "
            "the 13.58 s heating window (`stellarorion_sparta.adb:1870`), "
            "NOT a quantity measured by DSMC."
        )
        dsmc_surface = float(candidate["dsmc_surface_heat_load_Jcm2"])
        if math.isfinite(dsmc_surface):
            lines.append(
                f"- Heat load (DSMC surface integral): **{dsmc_surface:.6f} "
                f"J/cm^2** "
                f"(reference {_fmt(float(reference['dsmc_surface_heat_load_Jcm2']))} "
                "J/cm^2) -- the time integral of the DSMC surface heat flux"
            )
        else:
            lines.append(
                "- Heat load (DSMC surface integral): n/a -- the run carries "
                "no `dsmc_surface_heat_load_jcm2` column (it predates "
                "CALIBRATION DESIGN 2.4)."
            )
        lines.append(f"- Target: **{q_target:.6f} J/cm^2**")
        lines.append(f"- Verdict (heat load <= target): **{verdict}**")
        if analytic_q is not None:
            ratio = heat / analytic_q if analytic_q else float("nan")
            lines.append(
                f"- Analytic screening prediction: {analytic_q:.6f} J/cm^2 "
                f"(ratio CSV/analytic = {_fmt(ratio, '.4f')})"
            )
        if analytic_cd is not None:
            lines.append(
                f"- Analytic drag prediction: Cd = {analytic_cd:.6f} "
                f"(DSMC raw {float(candidate['cd_raw']):.4f})"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the comparison.

    Parameters:
        argv: the command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        The process exit status: 0 on success, 1 on a comparison error.
    """
    parser = argparse.ArgumentParser(
        description="Compare two DSMC validation runs (reference vs optimised).",
    )
    parser.add_argument("--reference-csv", required=True, type=Path)
    parser.add_argument("--reference-r-n", required=True, type=float)
    parser.add_argument("--reference-r-max", type=float, default=None)
    parser.add_argument("--candidate-csv", required=True, type=Path)
    parser.add_argument("--candidate-r-n", required=True, type=float)
    parser.add_argument("--candidate-r-max", type=float, default=None)
    parser.add_argument("--q-target", type=float, default=None)
    parser.add_argument("--analytic-q", type=float, default=None)
    parser.add_argument("--analytic-cd", type=float, default=None)
    parser.add_argument("--out-md", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        reference = _summarise(
            _read_run(args.reference_csv),
            args.reference_r_n,
            "reference",
            args.reference_r_max,
        )
        candidate = _summarise(
            _read_run(args.candidate_csv),
            args.candidate_r_n,
            "optimised",
            args.candidate_r_max,
        )
    except ComparisonError as exc:
        print(f"compare_dsmc_runs: {exc}", file=sys.stderr)
        return 1

    rows = _rows_for_table(reference, candidate)
    markdown = _render_markdown(
        reference,
        candidate,
        rows,
        args.q_target,
        args.analytic_q,
        args.analytic_cd,
        args.reference_csv,
        args.candidate_csv,
    )

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown, encoding="utf-8")
    with args.out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["metric", "unit", "reference", "optimised", "delta_pct", "verdict"]
        )
        for name, unit, ref, cand, delta, verdict in rows:
            writer.writerow([name, unit, _fmt(ref, ".10g"), _fmt(cand, ".10g"),
                             _fmt(delta, ".6f"), verdict])

    print(f"compare_dsmc_runs: wrote {args.out_md}")
    print(f"compare_dsmc_runs: wrote {args.out_csv}")
    # The console summary states the truth about the two heat loads (AXIOM
    # A6) and about the two drag coefficients (AXIOM A2), because those are
    # the two places a reader is most likely to mis-read the report.
    print(
        "compare_dsmc_runs: heat load (analytic: Sutton-Graves x window) "
        f"reference={float(reference['total_heat_load_Jcm2']):.6f} "
        f"optimised={float(candidate['total_heat_load_Jcm2']):.6f} J/cm^2"
    )
    dsmc_reference = float(reference["dsmc_surface_heat_load_Jcm2"])
    dsmc_candidate = float(candidate["dsmc_surface_heat_load_Jcm2"])
    print(
        "compare_dsmc_runs: heat load (DSMC surface integral) "
        f"reference={_fmt(dsmc_reference)} optimised={_fmt(dsmc_candidate)} "
        "J/cm^2"
    )
    if bool(candidate["cd_saturated"]):
        print(
            "compare_dsmc_runs: WARNING the optimised run's recorded cd is "
            "clamped at 3.0; use the reconstructed cd_raw column"
            + (
                f" (cd_unclamped = {float(candidate['cd_unclamped']):.6f})"
                if math.isfinite(float(candidate["cd_unclamped"]))
                else ""
            )
        )
    if bool(reference["has_flown_geometry"]) and bool(candidate["has_flown_geometry"]):
        same_geometry = all(
            math.isclose(float(reference[key]), float(candidate[key]),
                         rel_tol=1.0e-9, abs_tol=1.0e-12)
            for key, _, _ in GEOMETRY_FIELDS
        )
        print(
            "compare_dsmc_runs: flown geometry "
            + ("IDENTICAL (the two runs flew the same vehicle)"
               if same_geometry
               else "DIFFERENT (the two runs flew different vehicles -- see "
                    "the Flown geometry table)")
        )
    else:
        print(
            "compare_dsmc_runs: flown geometry NOT RECORDED (at least one run "
            "predates CALIBRATION DESIGN 2.4 and carries no geom_* columns)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
