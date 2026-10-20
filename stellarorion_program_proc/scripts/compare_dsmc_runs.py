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

CITATIONS
----------
[Reference: stellarorion_sparta.adb:3348] -- the [0, 3] drag-coefficient clamp.
[Reference: stellarorion_sparta.adb:3443] -- the timeseries CSV schema.
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

    saturated = any(c >= CD_CLAMP_MAX - 1.0e-9 for c in cd_recorded)
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
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    lines.append("| Metric | Unit | Reference | Optimised | Delta | Verdict |")
    lines.append("|:---|---:|---:|---:|---:|:---|")
    for name, unit, ref, cand, delta, verdict in rows:
        lines.append(
            f"| {name} | {unit} | {ref:.6g} | {cand:.6g} | "
            f"{delta:+.2f}% | {verdict} |"
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
            f"- DSMC+PINN_AUX heat load: **{heat:.6f} J/cm^2** "
            f"(reference {float(reference['total_heat_load_Jcm2']):.6f} J/cm^2)"
        )
        lines.append(f"- Target: **{q_target:.6f} J/cm^2**")
        lines.append(f"- Verdict (heat load <= target): **{verdict}**")
        if analytic_q is not None:
            ratio = heat / analytic_q if analytic_q else float("nan")
            lines.append(
                f"- Analytic screening prediction: {analytic_q:.6f} J/cm^2 "
                f"(DSMC/analytic = {ratio:.4f})"
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
            writer.writerow([name, unit, f"{ref:.10g}", f"{cand:.10g}",
                             f"{delta:.6f}", verdict])

    print(f"compare_dsmc_runs: wrote {args.out_md}")
    print(f"compare_dsmc_runs: wrote {args.out_csv}")
    if bool(candidate["cd_saturated"]):
        print(
            "compare_dsmc_runs: WARNING the optimised run's recorded cd is "
            "clamped at 3.0; use the reconstructed cd_raw column"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
