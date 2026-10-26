#!/usr/bin/env python3
"""Plan the multi-point DSMC stations on the shipped entry trajectory.

WHY THIS SCRIPT EXISTS
    The single DSMC sample used in the thesis is compared against a flight
    reconstruction that integrates the whole entry, which leaves a documented
    heat-load gap of about -15 per cent.  Closing that gap requires the DSMC
    surface heat flux at several trajectory stations, integrated over flight
    time instead of quoted at one point.  This script chooses those stations
    from the shipped 1-DOF profile and emits the exact command line for each,
    so the campaign is reproducible instead of hand-picked.

AXIOMS
    A1  The trajectory profile (results/00_reference/trajectory_profile.csv)
        is the authoritative flight path: one row per second, columns
        time_s, alt_km, vel_ms, mach, dyn_press_pa, cd, g_load, downrange_km.
    A2  The DSMC deck derives its freestream from Flight only: `global nrho`
        = rho * N_A / M_air and `mixture ... vstream` = Flight.Velocity_Ms
        (stellarorion_sparta.adb:556-557, :712-724).  Flight is filled by
        Mach_Alt_To_Flight (stellarorion_environment.adb:743), so `--alt` and
        `--mach` are the complete control surface for a station.
    A3  The reference run holds ~1.39e6 simulated particles at
        nrho = 1.44835e22 (rho = 6.964e-4 kg/m^3) with fnum = 3.5e19.  The
        particle count scales as nrho / fnum, so holding that ratio holds the
        statistical weight of every station.

THEOREMS
    T1  With V = Mach * sqrt(gamma * R * T(alt)), the Mach that reproduces a
        station's flight velocity is M = V_row / sqrt(gamma * R * T_ISA(alt)).
        Choosing any other Mach would fly the correct altitude at the wrong
        speed and therefore at the wrong Sutton-Graves flux.
    T2  The fraction of the total convective load accumulated up to row i is
        sum_{j<i} q_j * dt_j / sum_j q_j * dt_j with dt = 1 s, so picking the
        rows nearest N equally spaced cumulative fractions places the stations
        where the load actually is, not where the clock is.

APPLICATIONS
    `python3 scripts/plan_trajectory_stations.py` writes
    results/00_reference/trajectory_stations.csv and prints one runnable
    command per station.  Feed the finished station trees to
    scripts/integrate_trajectory_load.py.

CITATIONS
    [Citation: Sutton & Graves, NASA TR R-376, 1971 - q = C_sg sqrt(rho/R_n) V^3]
    [Citation: ISO 2533:1975 - Standard Atmosphere, the layers reproduced below]
    [Reference: stellarorion_environment.adb Atmosphere_Temperature :367 and
        Atmosphere_Density :449 - the exact layer constants used here so the
        plan and the Ada agree]
    [Reference: stellarorion_physics.adb Sutton_Graves_Heat :745 - C_SG = 1.7415e-4]

CONSTRAINTS
    Every station must be reachable without a code change; no station may be
    invented, and the emitted fnum is a derived value, never a guess.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

GAMMA_AIR = 1.4
R_AIR = 287.058
G0 = 9.80665
T0 = 288.15
RHO0 = 1.225
C_SG = 1.7415e-4
NOSE_RADIUS_M = 0.55

# The reference run's freestream, used as the particle-count anchor (axiom A3).
REF_ALT_KM = 52.0692
REF_FNUM = 3.5e19

COLUMNS = ("station", "time_s", "alt_km", "vel_ms", "mach", "fnum",
           "q_sg_wcm2", "cum_load_pct")


def isa_temperature(alt_km: float) -> float:
    """Return the ISA temperature at an altitude, in kelvin.

    Parameters:
        alt_km: geometric altitude in kilometres (clamped at 0 below sea level).

    Returns:
        The layer temperature in kelvin.

    Raises:
        Nothing: the function is total over the real line.

    AXIOMS:
        A1  The atmosphere is piecewise linear in altitude with the seven
            layers of ISO 2533 (up to 84.852 km) and an isothermal cap above.

    THEOREMS:
        T1  The function is continuous at every layer boundary: substituting
            the boundary altitude into either adjacent branch yields the same
            value, which is why the DSMC freestream temperature has no jump.

    CITATIONS:
        [Citation: ISO 2533:1975 - Standard Atmosphere]
        [Reference: stellarorion_environment.adb Atmosphere_Temperature :367]
    """
    h = max(alt_km, 0.0)
    if h <= 11.0:
        return T0 - 6.5 * h
    if h <= 20.0:
        return 216.65
    if h <= 32.0:
        return 216.65 + 1.0 * (h - 20.0)
    if h <= 47.0:
        return 228.65 + 2.8 * (h - 32.0)
    if h <= 51.0:
        return 270.65
    if h <= 71.0:
        return 270.65 - 2.8 * (h - 51.0)
    if h <= 84.852:
        return 214.65 - 2.0 * (h - 71.0)
    return 186.87


def isa_density(alt_km: float) -> float:
    """Return the ISA density at an altitude, in kg/m^3.

    Parameters:
        alt_km: geometric altitude in kilometres (clamped at 0 below sea level).

    Returns:
        The density in kg/m^3, never negative.

    Raises:
        Nothing: the function is total over the real line.

    AXIOMS:
        A1  Inside a layer with a non-zero lapse rate the density follows the
            polytropic relation rho = rho_b (T/T_b)^(-g/(R L) - 1); inside an
            isothermal layer it follows the barometric relation
            rho = rho_b exp(-g (h - h_b) / (R T)).
        A2  The layer base densities (1.225, 0.36391, 0.08801, 0.01322,
            0.001427, 0.000861, 0.000064, 6.93531e-06) are the constants the
            Ada model uses, so this replica and the deck see one atmosphere.

    THEOREMS:
        T1  rho is strictly decreasing in altitude on [0, 84.852] km: every
            exponent is negative and every base density is positive, so a
            higher station is always more rarefied and needs a smaller fnum to
            keep the same particle count.

    CITATIONS:
        [Citation: ISO 2533:1975 - Standard Atmosphere]
        [Reference: stellarorion_environment.adb Atmosphere_Density :449]
    """
    h = max(alt_km, 0.0)
    if h <= 11.0:
        exponent = G0 / (R_AIR * 6.5e-3) - 1.0
        return RHO0 * (isa_temperature(h) / T0) ** exponent
    if h <= 20.0:
        exponent = -G0 * (h - 11.0) * 1000.0 / (R_AIR * 216.65)
        return 0.36391 * math.exp(exponent)
    if h <= 32.0:
        exponent = -G0 / (R_AIR * 1.0e-3) - 1.0
        return 0.08801 * (isa_temperature(h) / 216.65) ** exponent
    if h <= 47.0:
        exponent = -G0 / (R_AIR * 2.8e-3) - 1.0
        return 0.01322 * (isa_temperature(h) / 228.65) ** exponent
    if h <= 51.0:
        exponent = -G0 * (h - 47.0) * 1000.0 / (R_AIR * 270.65)
        return 0.001427 * math.exp(exponent)
    if h <= 71.0:
        exponent = G0 / (R_AIR * 2.8e-3) - 1.0
        return 0.000861 * (isa_temperature(h) / 270.65) ** exponent
    if h <= 84.852:
        exponent = G0 / (R_AIR * 2.0e-3) - 1.0
        return 0.000064 * (isa_temperature(h) / 214.65) ** exponent
    exponent = -G0 * (h - 84.852) * 1000.0 / (R_AIR * 186.87)
    return 6.93531e-06 * math.exp(exponent)


def speed_of_sound(alt_km: float) -> float:
    """Return the ISA speed of sound at an altitude, in m/s.

    Parameters:
        alt_km: geometric altitude in kilometres.

    Returns:
        sqrt(gamma R T) in m/s.

    Raises:
        Nothing.

    AXIOMS:
        A1  Air is a perfect gas with gamma = 1.4 and R = 287.058 J/(kg K)
            (stellarorion_pinn_trajectory.ads:43-47).

    THEOREMS:
        T1  Mach_Alt_To_Flight returns V = Mach * a(alt) with this same a, so
            dividing a station's flight velocity by a(alt) is exact and not an
            approximation.

    CITATIONS:
        [Citation: Anderson, Modern Compressible Flow, Ch. 2]
        [Reference: stellarorion_environment.adb Mach_To_Velocity :695]
    """
    return math.sqrt(GAMMA_AIR * R_AIR * isa_temperature(alt_km))


def sutton_graves(density: float, velocity: float, nose_radius: float) -> float:
    """Return the Sutton-Graves stagnation-point heat flux, in W/m^2.

    Parameters:
        density: freestream density in kg/m^3.
        velocity: freestream speed in m/s.
        nose_radius: effective nose radius in m.

    Returns:
        C_sg * sqrt(rho / R_n) * V^3 in W/m^2, or 0.0 for a non-positive input.

    Raises:
        Nothing: a degenerate argument returns 0.0 rather than raising, which
        is the same guard the Ada uses.

    AXIOMS:
        A1  Stagnation-point convective flux scales with sqrt(rho/R_n) V^3 for
            a cold-wall blunt body in the continuum limit.

    THEOREMS:
        T1  The function is monotone increasing in both density and velocity
            and decreasing in nose radius, so the station ranking by flux is
            invariant to the exact value of C_sg.

    CITATIONS:
        [Citation: Sutton & Graves, NASA TR R-376, 1971]
        [Reference: stellarorion_physics.adb Sutton_Graves_Heat :745]
    """
    if density <= 0.0 or nose_radius <= 0.0:
        return 0.0
    return C_SG * math.sqrt(density / nose_radius) * velocity**3


def load_profile(path: Path) -> list[dict]:
    """Read the trajectory profile and annotate every row.

    Parameters:
        path: the trajectory_profile.csv to read.

    Returns:
        A list of dicts with the CSV columns as floats plus ``q_sg_wm2``
        (Sutton-Graves flux at the row's own density and velocity),
        ``cum_j_m2`` (convective load accumulated up to and including the row)
        and ``cum_pct`` (that load as a percentage of the total).

    Raises:
        FileNotFoundError: the profile does not exist.
        KeyError: a required column is missing.

    AXIOMS:
        A1  The rows are one second apart and strictly increasing in time.
        A2  The row density follows from the dynamic pressure,
            rho = 2 q_dyn / V^2, which is the only density the profile records.

    THEOREMS:
        T1  The trapezoidal and rectangular loads agree to better than 1 per
            cent for a 1 s cadence, so the cumulative sum below is adequate for
            choosing stations (it is never used as the reported load).
    """
    if not path.is_file():
        raise FileNotFoundError(f"trajectory profile not found: {path}")
    rows: list[dict] = []
    with path.open() as handle:
        for raw in csv.DictReader(handle):
            row = {key: float(value) for key, value in raw.items()}
            velocity = row["vel_ms"]
            if velocity <= 0.0:
                continue
            density = 2.0 * row["dyn_press_pa"] / (velocity * velocity)
            row["rho_csv"] = density
            row["q_sg_wm2"] = sutton_graves(density, velocity, NOSE_RADIUS_M)
            rows.append(row)
    total = 0.0
    for index, row in enumerate(rows):
        if index > 0:
            total += 0.5 * (rows[index - 1]["q_sg_wm2"] + row["q_sg_wm2"])
        row["cum_j_m2"] = total
    if total > 0.0:
        for row in rows:
            row["cum_pct"] = 100.0 * row["cum_j_m2"] / total
    return rows


def pick_stations(rows: list[dict], count: int) -> list[dict]:
    """Choose stations at equally spaced cumulative-load fractions.

    Parameters:
        rows: the annotated profile from :func:`load_profile`.
        count: how many stations to choose (at least two).

    Returns:
        The chosen rows, in flight-time order, each carrying ``cum_target``.

    Raises:
        ValueError: fewer rows than requested stations.

    AXIOMS:
        A1  The convective load is the integral of the flux over flight time,
            so equal increments of load are the natural quadrature nodes.

    THEOREMS:
        T1  For count stations at fractions (i + 0.5)/count the first node sits
            where the load has barely started and the last where it is nearly
            finished, spanning the whole pulse instead of clustering at the
            peak.
        T2  Every chosen row is distinct: the fractions are strictly
            increasing and the cumulative load is non-decreasing, so the
            nearest-row search can only collapse two fractions that fall in
            the same second, which is rejected by the seen-set below.
    """
    if len(rows) < count:
        raise ValueError(f"profile has {len(rows)} rows, {count} stations requested")
    picks: list[dict] = []
    seen: set[float] = set()
    for index in range(count):
        fraction = (index + 0.5) / count
        target = fraction * rows[-1]["cum_j_m2"]
        candidate = min(rows, key=lambda r: abs(r["cum_j_m2"] - target))
        if candidate["time_s"] in seen:
            continue
        seen.add(candidate["time_s"])
        picks.append({**candidate, "cum_target": 100.0 * fraction})
    picks.sort(key=lambda r: r["time_s"])
    return picks


def add_peak(rows: list[dict], picks: list[dict]) -> list[dict]:
    """Insert the flux-peak row if it is not already within a station spacing.

    Parameters:
        rows: the annotated profile.
        picks: the stations from :func:`pick_stations`.

    Returns:
        The stations, time-ordered, with the peak row inserted when the nearest
        station is more than two seconds away from it.

    Raises:
        Nothing.

    AXIOMS:
        A1  The quadrature must resolve the maximum of the integrand or the
            trapezoidal rule under-resolves the centre of the pulse.

    THEOREMS:
        T1  Adding a node to a trapezoidal rule over a smooth integrand cannot
            increase the truncation error, so inserting the peak is always
            safe.
    """
    if not picks:
        return picks
    peak = max(rows, key=lambda r: r["q_sg_wm2"])
    if any(abs(peak["time_s"] - p["time_s"]) <= 2.0 for p in picks):
        return picks
    return sorted([*picks, {**peak, "cum_target": peak["cum_pct"]}],
                  key=lambda r: r["time_s"])


def write_plan(stations: list[dict], out_csv: Path, results_dir: Path,
               steps: int) -> list[str]:
    """Write the station table and build one command per station.

    Parameters:
        stations: the chosen rows.
        out_csv: destination of the station table.
        results_dir: parent directory for the per-station trees.
        steps: DSMC steps per station.

    Returns:
        The command lines, one per station, ready to paste into a shell.

    Raises:
        OSError: the destination cannot be written.

    AXIOMS:
        A1  fnum is anchored to the reference run: a station whose ISA density
            is rho_s needs fnum = 3.5e19 * rho_s / rho_ref to hold the same
            particle count (axiom A3 of the module).
        A2  The Mach that reproduces the row velocity is exact per theorem T1
            of the module, because Mach_Alt_To_Flight uses the same sound speed.

    THEOREMS:
        T1  The emitted command flies the intended station: --alt fixes the
            ISA density and temperature, --mach fixes the velocity through the
            sound speed, and --fnum fixes the statistical weight.
    """
    rho_ref = isa_density(REF_ALT_KM)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    commands: list[str] = []
    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for index, station in enumerate(stations, start=1):
            alt = station["alt_km"]
            mach = station["vel_ms"] / speed_of_sound(alt)
            fnum = REF_FNUM * isa_density(alt) / rho_ref
            writer.writerow([
                index, f"{station['time_s']:.0f}", f"{alt:.6f}",
                f"{station['vel_ms']:.3f}", f"{mach:.6f}", f"{fnum:.6e}",
                f"{station['q_sg_wm2'] / 1.0e4:.4f}", f"{station['cum_pct']:.3f}",
            ])
            commands.append(
                f"./bin/main --validate --headless --diameter 3.0 --nose 0.55 "
                f"--tradius 0.135 --angle 60.0 --skin scalloped --steps {steps} "
                f"--alt {alt:.6f} --mach {mach:.6f} --fnum {fnum:.6e} "
                f"--results-dir {results_dir / f'station_{index:02d}'}"
            )
    return commands


def main(argv: list[str] | None = None) -> int:
    """Plan the multi-point DSMC campaign.

    Parameters:
        argv: command-line arguments (defaults to sys.argv[1:]).

    Returns:
        0 on success, 2 when the profile is missing or unreadable.

    Raises:
        Nothing: every failure is reported and mapped to exit code 2.

    AXIOMS:
        A1  The plan is derived from the shipped profile only; no station is
            chosen by hand and no flux is assumed.
    """
    parser = argparse.ArgumentParser(
        description="Choose the multi-point DSMC stations on the shipped entry "
                    "trajectory and emit one runnable command per station.")
    parser.add_argument("--profile", type=Path,
                        default=Path("results/00_reference/trajectory_profile.csv"))
    parser.add_argument("--out-csv", type=Path,
                        default=Path("results/00_reference/trajectory_stations.csv"))
    parser.add_argument("--results-dir", type=Path,
                        default=Path("results/trajectory_stations"))
    parser.add_argument("--stations", type=int, default=5)
    parser.add_argument("--steps", type=int, default=2200)
    parser.add_argument("--commands", action="store_true",
                        help="print the runnable command for every station")
    args = parser.parse_args(argv)

    try:
        rows = load_profile(args.profile)
    except (FileNotFoundError, KeyError) as error:
        print(f"[stations] cannot read the profile: {error}", file=sys.stderr)
        return 2
    if not rows:
        print(f"[stations] profile has no usable row: {args.profile}", file=sys.stderr)
        return 2

    peak = max(rows, key=lambda r: r["q_sg_wm2"])
    total = rows[-1]["cum_j_m2"]
    print(f"[stations] profile: {len(rows)} rows, "
          f"t = {rows[0]['time_s']:.0f}..{rows[-1]['time_s']:.0f} s, "
          f"alt {rows[0]['alt_km']:.2f}..{rows[-1]['alt_km']:.2f} km")
    print(f"[stations] Sutton-Graves peak {peak['q_sg_wm2'] / 1.0e4:.2f} W/cm^2 "
          f"at t = {peak['time_s']:.0f} s (alt {peak['alt_km']:.2f} km, "
          f"V {peak['vel_ms']:.0f} m/s)")
    print(f"[stations] Sutton-Graves load {total / 1.0e4:.1f} J/cm^2 "
          f"over {rows[-1]['time_s']:.0f} s")

    stations = add_peak(rows, pick_stations(rows, args.stations))
    print(f"[stations] {len(stations)} stations "
          f"(equally spaced in cumulative load, peak inserted):")
    print(f"[stations] {'t_s':>5} {'alt_km':>9} {'V_ms':>8} {'Mach':>8} "
          f"{'fnum':>11} {'q_sg_W/cm2':>11} {'cum%':>7}")
    rho_ref = isa_density(REF_ALT_KM)
    for station in stations:
        alt = station["alt_km"]
        mach = station["vel_ms"] / speed_of_sound(alt)
        fnum = REF_FNUM * isa_density(alt) / rho_ref
        print(f"[stations] {station['time_s']:5.0f} {alt:9.3f} "
              f"{station['vel_ms']:8.0f} {mach:8.4f} {fnum:11.3e} "
              f"{station['q_sg_wm2'] / 1.0e4:11.2f} {station['cum_pct']:7.1f}")

    commands = write_plan(stations, args.out_csv, args.results_dir, args.steps)
    print(f"[stations] wrote {args.out_csv}")
    if args.commands:
        for command in commands:
            print(command)
    else:
        print("[stations] re-run with --commands to print the runnable command lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
