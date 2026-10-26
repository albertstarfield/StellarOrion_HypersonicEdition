#!/usr/bin/env python3
"""Fly the multi-point DSMC trajectory campaign (review item #3) from one command.

WHY THIS EXISTS
  The single-point validation samples ONE flight condition (t = 97 s,
  alt 52.0692 km, V 3101.08 m/s), while the flight reconstruction integrates the
  whole entry; the resulting heat-load gap (-15.0 %) is the largest remaining
  quantitative discrepancy in the thesis. Closing it means flying several
  stations across the heating pulse and integrating the DSMC surface flux over
  the flight-time axis.

  The first attempt at that campaign was driven by an ad-hoc shell queue written
  into a temporary directory. It had no per-run record, judged success by the
  process exit code, and therefore reported a campaign as finished when in fact
  ONE station of five had produced data (the Docker/Colima daemon had died
  mid-run; stations 02..05 left 15-of-23 and 0-of-23 dumps, and every one of
  them exited 0). A campaign driver that cannot tell a dead solver from a
  completed one is not a driver. This script is the repo-owned replacement: it
  reproduces the campaign from the committed station plan, verifies the
  ARTEFACT of every station, records provenance, and refuses to report success
  when a station is missing.

AXIOMS
  A1.  The station set is the committed plan (scripts/plan_trajectory_stations.py
       -> results/00_reference/trajectory_stations.csv). This script never
       invents a station, an altitude or a Mach number.
  A2.  A station is COMPLETE when its own validation_timeseries.csv holds the
       row count the dump cadence demands (one row per 100 solver steps). The
       SOURCE OF TRUTH is the file the solver wrote, never the exit code and
       never this script's intent.
  A3.  A station that cannot be flown is recorded with status "failed" and NO
       metrics. No number is interpolated, substituted or carried over from a
       neighbouring station.
  A4.  The freestream of a station is the deck's own derivation from Flight
       (altitude -> ISA density/temperature, Mach -> velocity); passing --alt and
       --mach is what selects the station, and it also disables the IRVE-3
       baseline override in the validate path.

THEORIES
  T1.  If every station reports the same wall-clock flight time (time_s is
       constant inside one run) then integrating over the station index would
       be meaningless; the integration must therefore be performed on the
       FLIGHT-TIME axis of trajectory_profile.csv, by an external integrator
       (scripts/integrate_trajectory_load.py). This script only produces the
       station measurements that integrator consumes.
  T2.  A truncated solve still emits rows, so a row-count test alone is not
       sufficient when the solver dies after the last dump but before the final
       step; the exit status is checked as well, and a non-zero status marks the
       station failed even when the rows exist. Both tests are required.

APPLICATIONS
  python scripts/run_trajectory_campaign.py                 # fly every station
  python scripts/run_trajectory_campaign.py --resume        # adopt finished ones
  python scripts/run_trajectory_campaign.py --only 2 3      # repair a subset
  python scripts/run_trajectory_campaign.py --dry-run       # print the commands
  python scripts/run_trajectory_campaign.py --rebuild       # rebuild bin/main first

CITATIONS
  [Lau2013]   Lau & Munk, "IRVE-3 Flight Reconstruction", AIAA 2013-3951
              (flight peak heat load 195.06 J/cm^2, compared against in the
              integrator, not here).
  [SPARTA]    Plimpton & Gallis, SPARTA Users Manual -- dump/ave/surf cadence,
              https://sparta.github.io/doc/
  [RFC4180]   CSV format, https://www.rfc-editor.org/rfc/rfc4180
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"
PLAN = RESULTS_DIR / "00_reference" / "trajectory_stations.csv"
OUT_ROOT = RESULTS_DIR / "trajectory_stations"
BIN = PROJECT_ROOT / "bin" / "main"
INTEGRATOR = SCRIPT_DIR / "integrate_trajectory_load.py"

DEFAULT_STEPS = 2200
DUMP_CADENCE = 100          # the deck dumps surf/grid every 100 steps
DEFAULT_GEOMETRY = {
    "diameter": 3.0,
    "nose": 0.55,
    "tradius": 0.135,
    "angle": 60.0,
    "skin": "scalloped",
}


def _log(msg: str) -> None:
    """Print one campaign progress line.

    Parameters:
        msg: unprefixed message text.
    Returns:
        None.
    Exceptions:
        None -- print of a str does not raise.
    """
    print(f"[traj-campaign] {msg}", flush=True)


def read_plan(path: Path) -> list[dict[str, float]]:
    """Read the committed station plan, binding every column BY HEADER NAME.

    Parameters:
        path: the plan CSV written by scripts/plan_trajectory_stations.py.

    Returns:
        One dict per station with keys station, time_s, alt_km, vel_ms, mach,
        fnum, q_sg_wcm2, cum_load_pct -- all floats except station (int).

    Raises:
        FileNotFoundError: the plan does not exist.
        RuntimeError: the plan is empty or a required column is missing.

    AXIOMS:
        A1  The plan is generated from the shipped trajectory profile; it is the
            only authority for which conditions are flown.
        A2  Column order is an implementation detail of the generator, so every
            field is looked up by name (a positional read would silently bind
            mach to velocity the day the writer gains a column).
    """
    if not path.is_file():
        raise FileNotFoundError(f"station plan not found: {path}")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"station plan is empty: {path}")
    required = ("station", "time_s", "alt_km", "vel_ms", "mach", "fnum")
    missing = [key for key in required if key not in rows[0]]
    if missing:
        raise RuntimeError(f"station plan {path} lacks column(s): {', '.join(missing)}")
    plan: list[dict[str, float]] = []
    for row in rows:
        plan.append(
            {
                "station": int(float(row["station"])),
                "time_s": float(row["time_s"]),
                "alt_km": float(row["alt_km"]),
                "vel_ms": float(row["vel_ms"]),
                "mach": float(row["mach"]),
                "fnum": float(row["fnum"]),
                "q_sg_wcm2": float(row.get("q_sg_wcm2") or 0.0),
                "cum_load_pct": float(row.get("cum_load_pct") or 0.0),
            }
        )
    return plan


def expected_rows(steps: int) -> int:
    """Return the number of data rows a complete timeseries must hold.

    Parameters:
        steps: solver steps requested for the station.

    Returns:
        ``steps // DUMP_CADENCE`` -- one row per dump interval.

    AXIOMS:
        A1  The validate leg writes one timeseries row per dump, so the row
            count is fixed by the cadence and the step count, not by chance.
    """
    return max(1, steps // DUMP_CADENCE)


def station_dir(index: int) -> Path:
    """Return the results directory of one station.

    Parameters:
        index: 1-based station number from the plan.
    Returns:
        ``results/trajectory_stations/station_NN`` (zero-padded to two digits).
    """
    return OUT_ROOT / f"station_{index:02d}"


def timeseries_rows(path: Path) -> int:
    """Count the DATA rows (header excluded) of a station timeseries.

    Parameters:
        path: candidate validation_timeseries.csv.

    Returns:
        Number of data rows, or 0 when the file is absent or holds no data.

    Exceptions:
        OSError while reading is caught and reported as 0: an unreadable file is
        an incomplete station, never a passing one.
    """
    try:
        with path.open(newline="") as handle:
            rows = sum(1 for _ in csv.reader(handle))
        return max(0, rows - 1)
    except FileNotFoundError:
        #  WHY: an absent timeseries is the NORMAL case before a station flies;
        #  logging it on every probe would bury the real failures in noise.
        return 0
    except (OSError, csv.Error) as exc:
        _log(f"cannot read {path}: {exc}")
        return 0


def station_complete(index: int, steps: int) -> tuple[bool, int]:
    """Decide whether a station already holds a complete measurement.

    Parameters:
        index: 1-based station number.
        steps: solver steps the station must have run.

    Returns:
        ``(complete, rows)`` where ``rows`` is the data-row count found.

    AXIOMS:
        A1  Completeness is a property of the ARTEFACT, not of a log line.
    """
    rows = timeseries_rows(station_dir(index) / "validation_timeseries.csv")
    return rows >= expected_rows(steps), rows


def docker_ready() -> bool:
    """Report whether the Docker daemon answers.

    Parameters: none.
    Returns:
        True when ``docker ps`` exits 0.
    Exceptions:
        None -- a missing ``docker`` binary or a daemon failure is False, and the
        caller decides whether to wait or abort.
    """
    if shutil.which("docker") is None:
        _log("docker is not on PATH")
        return False
    try:
        res = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log(f"docker probe failed: {exc}")
        return False
    if res.returncode != 0:
        _log(f"docker probe exit {res.returncode}: {res.stderr.strip()[:200]}")
        return False
    return True


def build_command(station: dict[str, float], geometry: dict[str, object], steps: int,
                  out_dir: Path) -> list[str]:
    """Build the solver command line for one station.

    Parameters:
        station: one record from :func:`read_plan`.
        geometry: body parameters (diameter, nose, tradius, angle, skin).
        steps: solver steps.
        out_dir: the station's results directory.

    Returns:
        The argv list, with the executable as element 0.

    AXIOMS:
        A1  --alt and --mach are what select the station; passing them also
            disables the IRVE-3 baseline override in the validate path, so the
            freestream is the ISA state at that altitude.
        A2  --fnum comes from the plan so the particle count stays comparable
            across stations (rarefied high-altitude stations need fewer).
    """
    return [
        str(BIN), "--validate", "--headless",
        "--diameter", f"{geometry['diameter']}",
        "--nose", f"{geometry['nose']}",
        "--tradius", f"{geometry['tradius']}",
        "--angle", f"{geometry['angle']}",
        "--skin", str(geometry["skin"]),
        "--steps", str(steps),
        "--alt", f"{station['alt_km']:.6f}",
        "--mach", f"{station['mach']:.6f}",
        "--fnum", f"{station['fnum']:.6e}",
        "--results-dir", str(out_dir.relative_to(PROJECT_ROOT)),
    ]


def record(index: int, payload: dict[str, object]) -> None:
    """Write one station's provenance record.

    Parameters:
        index: 1-based station number.
        payload: the record to serialise as JSON.
    Returns:
        None.
    Exceptions:
        OSError is allowed to propagate: a campaign whose provenance cannot be
        written must fail loudly rather than continue unrecorded.
    """
    out = station_dir(index) / "case.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fly(index: int, station: dict[str, float], geometry: dict[str, object], steps: int,
        retries: int, timeout_s: float, dry_run: bool) -> dict[str, object]:
    """Fly one station and return its verdict record.

    Parameters:
        index: 1-based station number.
        station: plan record.
        geometry: body parameters.
        steps: solver steps.
        retries: extra attempts after a failed attempt (0 = single attempt).
        timeout_s: per-attempt wall-clock cap, seconds (0 disables).
        dry_run: print the command instead of executing it.

    Returns:
        The record written to ``case.json``: status is "ok" only when the
        artefact is complete AND the process exited 0.

    Raises:
        Nothing: a failed attempt is recorded, reported and retried; the caller
        aggregates the outcome. Exceptions from the subprocess layer are caught
        and converted into a failed attempt so one broken station cannot abort
        the campaign.

    AXIOMS:
        A1  Two independent tests decide success -- the declared exit status and
            the artefact row count. Either failing marks the station failed.
    THEOREMS:
        T1  A solver that dies between dumps still leaves rows on disk, so the
            row test alone would accept a truncated run; the status test alone
            would accept a solver that "succeeded" after writing nothing. Both
            are necessary and neither is sufficient alone.
    """
    out_dir = station_dir(index)
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = build_command(station, geometry, steps, out_dir)
    env = dict(os.environ)
    env.setdefault("MACOSX_DEPLOYMENT_TARGET", "26.0")
    env.setdefault("STELLARORION_PYTHON", str(PROJECT_ROOT / "venv_validation" / "bin" / "python3"))
    env["PATH"] = f"{Path.home() / '.local' / 'bin'}:{env.get('PATH', '')}"

    payload: dict[str, object] = {
        "station": index,
        "time_s": station["time_s"],
        "alt_km": station["alt_km"],
        "vel_ms": station["vel_ms"],
        "mach": station["mach"],
        "fnum": station["fnum"],
        "steps": steps,
        "expected_rows": expected_rows(steps),
        "command": " ".join(argv),
        "attempts": 0,
        "status": "failed",
        "exit_code": None,
        "rows": 0,
        "wall_time_s": 0.0,
    }

    if dry_run:
        _log(f"station {index:02d} (t={station['time_s']:.0f} s): {' '.join(argv)}")
        payload["status"] = "dry-run"
        return payload

    for attempt in range(1, max(1, retries) + 2):
        if not docker_ready():
            _log(f"station {index:02d}: docker daemon unreachable - not attempting")
            payload["attempts"] = attempt
            payload["status"] = "failed"
            payload["failure_reason"] = "docker daemon unreachable"
            record(index, payload)
            return payload
        _log(
            f"station {index:02d} attempt {attempt}: alt={station['alt_km']:.4f} km "
            f"mach={station['mach']:.3f} fnum={station['fnum']:.3e}"
        )
        started = time.time()
        try:
            res = subprocess.run(
                argv,
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=(timeout_s or None),
                check=False,
            )
            code, tail = res.returncode, (res.stdout or "")[-1500:]
        except subprocess.TimeoutExpired:
            code, tail = 124, f"timeout after {timeout_s:.0f} s"
            _log(f"station {index:02d}: {tail}")
        except OSError as exc:
            code, tail = 127, f"exec failed: {exc}"
            _log(f"station {index:02d}: {tail}")
        elapsed = time.time() - started
        rows = timeseries_rows(out_dir / "validation_timeseries.csv")
        ok = code == 0 and rows >= expected_rows(steps)
        payload.update(
            {
                "attempts": attempt,
                "exit_code": code,
                "rows": rows,
                "wall_time_s": round(elapsed, 3),
                "status": "ok" if ok else "failed",
            }
        )
        if ok:
            _log(f"station {index:02d}: OK  ({rows} rows, exit 0, {elapsed:.0f} s)")
            break
        payload["failure_reason"] = (
            f"exit {code}, {rows} of {expected_rows(steps)} rows"
        )
        _log(
            f"station {index:02d}: FAILED  exit {code}, {rows} of "
            f"{expected_rows(steps)} rows, {elapsed:.0f} s"
        )
        if tail.strip():
            _log(f"station {index:02d} log tail: {tail.strip().splitlines()[-1][:200]}")
        if attempt <= retries:
            _log(f"station {index:02d}: retrying")
    record(index, payload)
    return payload


def integrate() -> int:
    """Run the trajectory integrator over the stations that exist.

    Parameters: none.
    Returns:
        The integrator's exit status (2 means no station produced a timeseries).
    Exceptions:
        None -- a missing venv python falls back to the current interpreter, and
        an OSError is reported as status 127.
    """
    python = PROJECT_ROOT / "venv_validation" / "bin" / "python3"
    if not python.is_file():
        python = Path(sys.executable)
    try:
        res = subprocess.run(
            [str(python), str(INTEGRATOR)], cwd=str(PROJECT_ROOT), check=False
        )
        return res.returncode
    except OSError as exc:
        _log(f"cannot run the integrator: {exc}")
        return 127


def main(argv: list[str] | None = None) -> int:
    """Fly the trajectory campaign and record every station's verdict.

    Parameters:
        argv: command-line arguments; ``None`` means ``sys.argv[1:]``.

    Returns:
        0 when every requested station produced a complete measurement, 1 when
        at least one did not, 2 when the plan or the binary is missing.

    Raises:
        Nothing -- every failure path returns a status and prints its reason.

    AXIOMS:
        A1  --resume adopts an existing complete station instead of re-flying it,
            so a repaired campaign costs only the stations that are missing.
        A2  The campaign is reported complete only when every station in the
            plan is complete; "most of them" is a failure with a list.
    """
    parser = argparse.ArgumentParser(
        description="Fly the multi-point DSMC trajectory campaign (review item #3).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--plan", type=Path, default=PLAN, help="station plan CSV")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="solver steps per station")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="fly only these station numbers")
    parser.add_argument("--resume", action="store_true",
                        help="skip a station whose timeseries is already complete")
    parser.add_argument("--retries", type=int, default=1, help="extra attempts per station")
    parser.add_argument("--timeout", type=float, default=7200.0,
                        help="per-attempt wall-clock cap in seconds (0 = unlimited)")
    parser.add_argument("--dry-run", action="store_true", help="print commands only")
    parser.add_argument("--no-integrate", action="store_true",
                        help="do not run the integrator afterwards")
    parser.add_argument("--rebuild", action="store_true",
                        help="rebuild bin/main before flying (MACOSX_DEPLOYMENT_TARGET=26.0)")
    parser.add_argument("--diameter", type=float, default=DEFAULT_GEOMETRY["diameter"])
    parser.add_argument("--nose", type=float, default=DEFAULT_GEOMETRY["nose"])
    parser.add_argument("--tradius", type=float, default=DEFAULT_GEOMETRY["tradius"])
    parser.add_argument("--angle", type=float, default=DEFAULT_GEOMETRY["angle"])
    parser.add_argument("--skin", default=DEFAULT_GEOMETRY["skin"],
                        choices=("smooth", "scalloped"))
    args = parser.parse_args(argv)

    try:
        plan = read_plan(args.plan)
    except (FileNotFoundError, RuntimeError) as exc:
        _log(f"ERROR: {exc}")
        return 2

    if args.only:
        plan = [row for row in plan if row["station"] in set(args.only)]
        if not plan:
            _log(f"ERROR: --only {args.only} matched no station in {args.plan}")
            return 2

    if args.rebuild and not args.dry_run:
        env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET="26.0")
        env["PATH"] = f"{Path.home() / '.local' / 'bin'}:{env.get('PATH', '')}"
        gpr = PROJECT_ROOT / "stellarorion_program_proc.gpr"
        _log(f"rebuilding {BIN.name} ({gpr.name})")
        res = subprocess.run(
            ["gprbuild", "-f", "-P", str(gpr), "-j0"],
            cwd=str(PROJECT_ROOT), env=env, check=False,
        )
        if res.returncode != 0:
            _log(f"ERROR: gprbuild exited {res.returncode}")
            return 2

    if not args.dry_run and not BIN.is_file():
        _log(f"ERROR: solver binary missing: {BIN} (use --rebuild)")
        return 2

    geometry = {
        "diameter": args.diameter,
        "nose": args.nose,
        "tradius": args.tradius,
        "angle": args.angle,
        "skin": args.skin,
    }

    results: list[dict[str, object]] = []
    for station in plan:
        index = int(station["station"])
        if args.resume:
            complete, rows = station_complete(index, args.steps)
            if complete:
                _log(f"station {index:02d}: already complete ({rows} rows) - adopted")
                results.append({"station": index, "status": "ok", "rows": rows})
                continue
        results.append(
            fly(index, station, geometry, args.steps, args.retries, args.timeout, args.dry_run)
        )

    done = [row for row in results if row["status"] in ("ok", "dry-run")]
    missing = [row["station"] for row in results if row["status"] == "failed"]
    summary = {
        "plan": str(args.plan.relative_to(PROJECT_ROOT)),
        "stations_requested": [row["station"] for row in results],
        "stations_complete": [row["station"] for row in done],
        "stations_failed": missing,
        "steps": args.steps,
        "geometry": geometry,
        "complete": not missing,
        "records": results,
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "campaign.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _log(
        f"campaign: {len(done)}/{len(results)} stations complete"
        + (f" - FAILED: {missing}" if missing else "")
    )

    if not args.dry_run and not args.no_integrate:
        _log("integrating the measured stations over the flight-time axis")
        rc = integrate()
        if rc != 0:
            _log(f"integrator exited {rc} (2 = no station produced a timeseries)")

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
