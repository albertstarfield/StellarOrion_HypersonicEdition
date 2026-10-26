#!/usr/bin/env python3
"""Integrate the multi-point DSMC surface heat flux over the entry trajectory.

WHY THIS SCRIPT EXISTS
    The thesis compares one DSMC sample against a flight reconstruction that
    integrates the whole entry, which leaves a documented heat-load gap of
    about -15 per cent (chapter_03_methodology.tex).  The honest way to close
    that gap is to sample the DSMC surface heat flux at several trajectory
    stations and integrate it over flight time.  This script performs that
    integration and reports, in the same units and over the same time window,
    the Sutton-Graves flux of the shipped profile.  Nothing is extrapolated
    beyond the measured station window, and no endpoint is invented: the
    window is exactly [first station, last station].

AXIOMS
    A1  `results/00_reference/trajectory_stations.csv` (written by
        scripts/plan_trajectory_stations.py) lists the stations actually flown:
        time_s, alt_km, vel_ms, mach, fnum, q_sg_wcm2, cum_load_pct.
    A2  Each station tree holds the identical Ada-written timeseries
        (step, drag_sum_N, ..., heatflux_max_Wm2, heat_sum_Wm2,
        heatflux_avg_Wm2, heatflux_sg_Wm2, ..., heat_load_jcm2, ...).  The
        column of interest is located BY HEADER NAME, never by position.
    A3  `heatflux_avg_Wm2` is the area-averaged wall heat flux of the DSMC
        run: the quantity that integrates over time into a per-unit-area heat
        load, which is what the flight value 195.06 J/cm2 measures.
    A4  The deck's freestream density is ISA(alt) while the profile's own
        density is 2*q_dyn/V^2.  The two are reported side by side rather than
        silently reconciled.

THEOREMS
    T1  The trapezoid rule over the measured stations,
        Q = sum_i 0.5*(q_i + q_{i+1})*(t_{i+1} - t_i), is second-order accurate
        in the station spacing and requires no assumption about the shape of
        the heating pulse between samples.
    T2  Integrating the Sutton-Graves profile over the SAME window gives a
        like-for-like reference: the ratio Q_DSMC / Q_SG then measures the
        DSMC-vs-engineering-correlation fidelity at the sampled stations, not
        a difference in integration window.

APPLICATIONS
    Run after the station campaign finishes:

        python3 scripts/integrate_trajectory_load.py \\
            --plan results/00_reference/trajectory_stations.csv \\
            --stations-dir results/trajectory_stations \\
            --profile results/00_reference/trajectory_profile.csv \\
            --out-csv results/trajectory_stations/integrated_load.csv

CITATIONS
    [SG1971] Sutton & Graves, NASA TR R-376, 1971 (the q ~ sqrt(rho/R_n) V^3
        stagnation-point correlation implemented at
        stellarorion_physics.adb:745 with C_SG = 1.7415e-4,
        stellarorion_types.ads:62).
    [ISO2533] ISO 2533:1975 Standard Atmosphere (the ISA layers replicated in
        scripts/plan_trajectory_stations.py, mirroring
        stellarorion_environment.adb:367 and :449).
    [Lau2013] Lau, IRVE-3 flight reconstruction (the 14.36 W/cm2 and
        195.06 J/cm2 flight values compared against in Ch3).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

FLIGHT_LOAD_JCM2 = 195.06
EB = 1.0e4  #  W/m^2 per W/cm^2


def read_last_row(path: Path) -> dict[str, float]:
    """Return the final data row of a validation timeseries, keyed by column name.

    Parameters:
        path: the ``validation_timeseries.csv`` of one station tree.

    Returns:
        A mapping from column name to float value for the last data row.

    Raises:
        FileNotFoundError: the timeseries does not exist.
        RuntimeError: the file has no header or no data row.

    AXIOMS:
        A1  The header names are authoritative; positions may shift between
            binary versions, so every lookup is by name.
    """
    if not path.is_file():
        raise FileNotFoundError(f"station timeseries not found: {path}")
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        raise RuntimeError(f"station timeseries has no data row: {path}")
    header = rows[0]
    last = rows[-1]
    if len(last) != len(header):
        raise RuntimeError(
            f"column count mismatch in {path}: header {len(header)}, row {len(last)}"
        )
    return {name: float(value) for name, value in zip(header, last, strict=True)}


def read_plan(path: Path) -> list[dict]:
    """Read the station plan written by scripts/plan_trajectory_stations.py.

    Parameters:
        path: the station plan CSV.

    Returns:
        A list of dicts with ``station``, ``time_s``, ``alt_km``, ``vel_ms``,
        ``mach``, ``q_sg_wcm2`` and ``cum_load_pct``.

    Raises:
        FileNotFoundError: the plan does not exist.
    """
    if not path.is_file():
        raise FileNotFoundError(f"station plan not found: {path}")
    out: list[dict] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            out.append(
                {
                    "station": int(row["station"]),
                    "time_s": float(row["time_s"]),
                    "alt_km": float(row["alt_km"]),
                    "vel_ms": float(row["vel_ms"]),
                    "mach": float(row["mach"]),
                    "q_sg_wcm2": float(row["q_sg_wcm2"]),
                    "cum_load_pct": float(row["cum_load_pct"]),
                }
            )
    return out


def read_profile(path: Path) -> list[dict]:
    """Read the shipped 1-DOF trajectory profile.

    Parameters:
        path: ``trajectory_profile.csv``.

    Returns:
        A list of dicts with ``time_s``, ``alt_km``, ``vel_ms`` and
        ``dyn_press_pa``.

    Raises:
        FileNotFoundError: the profile does not exist.
    """
    if not path.is_file():
        raise FileNotFoundError(f"trajectory profile not found: {path}")
    out: list[dict] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            out.append(
                {
                    "time_s": float(row["time_s"]),
                    "alt_km": float(row["alt_km"]),
                    "vel_ms": float(row["vel_ms"]),
                    "dyn_press_pa": float(row["dyn_press_pa"]),
                }
            )
    return out


def trapezoid(times: list[float], values: list[float]) -> float:
    """Integrate a sampled series with the trapezoid rule.

    Parameters:
        times: sample times, strictly increasing.
        values: sample values, same length as ``times``.

    Returns:
        The integral in ``value * time`` units; 0.0 for fewer than two samples.

    Raises:
        ValueError: the two sequences differ in length.

    THEOREMS:
        T1  Each panel is exact for a linear segment, so the sum is exact for
            any piecewise-linear interpolation of the samples.
    """
    if len(times) != len(values):
        raise ValueError("times and values must have the same length")
    total = 0.0
    for i in range(len(times) - 1):
        dt = times[i + 1] - times[i]
        total += 0.5 * (values[i] + values[i + 1]) * dt
    return total


def main(argv: list[str] | None = None) -> int:
    """Integrate the station fluxes and write the comparison table.

    Parameters:
        argv: argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        0 on success, 2 when the plan or a station tree is missing.

    Raises:
        Nothing: every failure is reported on stderr and mapped to a return
        code, so a shell chain can react to it.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--plan", type=Path,
        default=Path("results/00_reference/trajectory_stations.csv"),
    )
    parser.add_argument(
        "--stations-dir", type=Path, default=Path("results/trajectory_stations"),
    )
    parser.add_argument(
        "--profile", type=Path,
        default=Path("results/00_reference/trajectory_profile.csv"),
    )
    parser.add_argument(
        "--out-csv", type=Path,
        default=Path("results/trajectory_stations/integrated_load.csv"),
    )
    args = parser.parse_args(argv)

    try:
        plan = read_plan(args.plan)
        profile = read_profile(args.profile)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[load] {exc}", file=sys.stderr)
        return 2

    missing: list[str] = []
    measured: list[dict] = []
    for station in plan:
        tree = args.stations_dir / f"station_{station['station']:02d}"
        try:
            row = read_last_row(tree / "validation_timeseries.csv")
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"[load] {exc}", file=sys.stderr)
            missing.append(tree.name)
            continue
        #  WHY: the profile density (2 q / V^2) and the ISA density the deck
        #  actually used are different assumptions; keeping both visible stops
        #  the comparison from hiding a modelling choice.
        alt = station["alt_km"]
        near = min(profile, key=lambda p: abs(p["time_s"] - station["time_s"]))
        vel = max(near["vel_ms"], 1.0)
        rho_profile = 2.0 * near["dyn_press_pa"] / (vel * vel)
        measured.append(
            {
                "station": station["station"],
                "time_s": station["time_s"],
                "alt_km": alt,
                "vel_ms": station["vel_ms"],
                "q_avg_wcm2": row["heatflux_avg_Wm2"] / EB,
                "q_max_wcm2": row["heatflux_max_Wm2"] / EB,
                "q_sg_wcm2": row["heatflux_sg_Wm2"] / EB,
                "rho_profile": rho_profile,
                "cd": row["cd"],
                "g_load": row["g_load"],
            }
        )

    if not measured:
        print("[load] no station tree produced a timeseries - nothing to integrate",
              file=sys.stderr)
        return 2

    times = [m["time_s"] for m in measured]
    q_avg = [m["q_avg_wcm2"] for m in measured]
    q_max = [m["q_max_wcm2"] for m in measured]
    q_sg = [m["q_sg_wcm2"] for m in measured]

    #  A3: q_avg is already W/cm^2, so W/cm^2 * s is J/cm^2 directly.
    load_avg = trapezoid(times, q_avg)
    load_max = trapezoid(times, q_max)
    load_sg = trapezoid(times, q_sg)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "station", "time_s", "alt_km", "vel_ms",
            "q_avg_Wcm2", "q_max_Wcm2", "q_sg_Wcm2",
            "ratio_avg_over_sg", "cd", "g_load",
        ])
        for m in measured:
            ratio = m["q_avg_wcm2"] / m["q_sg_wcm2"] if m["q_sg_wcm2"] else float("nan")
            writer.writerow([
                m["station"], f"{m['time_s']:.3f}", f"{m['alt_km']:.4f}",
                f"{m['vel_ms']:.3f}", f"{m['q_avg_wcm2']:.4f}",
                f"{m['q_max_wcm2']:.4f}", f"{m['q_sg_wcm2']:.4f}",
                f"{ratio:.4f}", f"{m['cd']:.6f}", f"{m['g_load']:.6f}",
            ])
        writer.writerow([])
        writer.writerow(["integrated_load_Jcm2", "t_start_s", "t_end_s",
                         "stations_used", "stations_missing"])
        writer.writerow([
            f"{load_avg:.4f}", f"{times[0]:.1f}", f"{times[-1]:.1f}",
            len(measured), len(missing),
        ])

    print(f"[load] stations measured: {len(measured)}/{len(plan)}"
          f"  (missing: {', '.join(missing) if missing else 'none'})")
    print(f"[load] window: t = {times[0]:.0f} .. {times[-1]:.0f} s")
    for m in measured:
        ratio = m["q_avg_wcm2"] / m["q_sg_wcm2"] if m["q_sg_wcm2"] else float("nan")
        print(f"[load]   station {m['station']}: t {m['time_s']:5.1f} s  "
              f"q_avg {m['q_avg_wcm2']:8.3f} W/cm^2  "
              f"q_sg {m['q_sg_wcm2']:8.3f}  ratio {ratio:5.3f}")
    print(f"[load] integrated DSMC load (area-averaged): {load_avg:.2f} J/cm^2")
    print(f"[load] integrated DSMC load (peak flux):     {load_max:.2f} J/cm^2")
    print(f"[load] integrated Sutton-Graves (same window): {load_sg:.2f} J/cm^2")
    if load_sg > 0.0:
        print(f"[load] DSMC / SG over the window: {load_avg / load_sg:.4f}")
    print(f"[load] flight value for comparison: {FLIGHT_LOAD_JCM2:.2f} J/cm^2")
    print(f"[load] wrote {args.out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
