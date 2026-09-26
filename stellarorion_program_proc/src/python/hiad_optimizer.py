# Parity protection: metadata/hiad_optimizer.meta.json (RS+GC parity)
"""
HIAD Geometry Optimizer -- Thin FFI wrapper calling Ada/SPARK.

All computation (CCD sampling, cost function) is delegated to Ada/SPARK via FFI.
Bayesian Optimization (GP surrogate + Matern 5/2 + EI acquisition) runs in
Python using scikit-learn, calling Ada FFI for cost function evaluations.
MoP (Method of Projected Gradients) is available via Ada FFI for comparison.

AXIOMS:
  1. The HIAD geometry is fully parameterized by (R_N, r_tor, half_cone_deg).
  2. All physics and optimization logic lives in Ada/SPARK.
  3. Python provides only the CLI entry point, JSON output, and the
     post-run diagnostic render (scripts/render_geometry_grid.py).

CITATIONS:
  [1] stellarorion_ffi.ads — C-compatible FFI layer for optimization
  [2] stellarorion_optimization.ads — Core optimization algorithms
  [3] Ada 2012 Reference Manual, Interfaces.C package
  [4] scripts/render_geometry_grid.py — 87-panel geometry diagnostic
  [5] Kennedy, M.C. & O'Hagan, A. (2000) "Predicting the output from a
      complex computer code when fast approximations are available",
      Biometrika 87(1), 1-13 — multi-fidelity calibration / bounded
      multiplicative bias correction (basis of the --hybrid-validate
      correction loop, plan Part C)
  [6] Plimpton, S. & Gallis, P. (2014) "A.T. Sparta—a parallel
      unstructured DSMC code for comprehensive simulations of neutral
      and ionized gases", J. Comput. Phys. 268, 400-412 — SPARTA DSMC
      engine invoked by the gate's --validate leg
  [7] stellarorion_project.adb CLI — --validate / --validate-only /
      --results-dir / --nose / --tradius / --angle / --skin / --steps
  [8] run.py Phase 2b — validation_pipeline.py invocation template
      (--csv --target-step 300000000 --iterations 4000 --device auto
      --headless)
  [9] Validation Sep 1, 2026.md — reference command
      `bin/main --validate --skin scalloped --steps 2200`

Exit codes (see main()):
  0 success / gate PASS / --dry-run / --allow-fail
  1 infrastructure or child-process failure (never a fake verdict)
  3 hybrid gate verdict FAIL (q_hybrid > q_target) without --allow-fail

Author: Albert Starfield Wahyu Suryo Samudro
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

# --- Import FFI wrappers from ada_pinn_wrapper ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ada_pinn_wrapper import (
    estimate_cd,
    generate_ccd_samples,
    get_hiad_cross_section,
    hiad_cost_components,
    hiad_cost_function,
    run_bayesian_optimize,
    run_mop_optimize,
    set_validation_refs,
    sutton_graves_heat_flux,
)

# ======================================================================
#  Constants (matching Ada/SPARK defaults from stellarorion_optimization)
# ======================================================================

# [Citation: stellarorion_optimization.ads — Default_R_N, Default_R_Tor, etc.]
_DEFAULT_R_N = 1.5            # m -- nose sphere radius
_DEFAULT_R_TOR = 0.135        # m -- torus minor radius
_DEFAULT_HALF_CONE_DEG = 60.0  # degrees -- half-cone angle

# IRVE-3 flight conditions (Rapisarda 2023, Table 4.10)
_ALTITUDE_KM = 51.8           # km -- DSMC snapshot altitude
_VELOCITY_MS = 3378.0         # m/s -- velocity at snapshot

# Structural/thermal constraints (matching Ada constants)
_MAX_RADIUS_LIMIT = 3.0       # m -- IRVE-3 diameter limit
_NOSE_RADIUS_LIMIT = 1.0      # m -- minimum thermal protection


# ======================================================================
#  Dynamic validation base reference for J(x)
# ======================================================================


def _load_validation_refs() -> dict[str, float]:
    """Load the dynamic validation base reference used by J(x).

    Reads results/validation_scalloped/validation_pipeline_output/
    unified_comparison_data.json and extracts every reference the Ada
    cost function normalises against:

        q_target_jcm2 -- StellarOrion validated Total Heat Load [J/cm^2]
                         (the objective J(x) minimises against)
        flux_ref_wcm2 -- IRVE-3 flight peak heat flux [W/cm^2]
        tau_sec       -- effective heating duration [s], derived as
                         Q_flight / q_flight from the same flight pair
        cd_ref        -- StellarOrion validated drag coefficient
        flight_q_jcm2 -- IRVE-3 flight Total Heat Load (reporting only)

    AXIOMS:
      1. J(x) must normalise against the CURRENT validation state, not
         hard-coded constants -- re-running validation changes these
         values and the optimizer must follow automatically.
      2. Fail LOUD on any problem (missing file, schema drift, bad
         values): optimizing against a stale/absent reference would
         silently invalidate the objective (Murphy's Law).

    Returns:
        dict with keys q_target_jcm2, flux_ref_wcm2, tau_sec, cd_ref,
        flight_q_jcm2 (all positive floats).

    Raises:
        RuntimeError -- file missing, JSON invalid, key missing, or any
            extracted value not strictly positive / not finite.

    [Citation: results/validation_scalloped/validation_pipeline_output/
     unified_comparison_data.json -- comparison.stellarorion.raw_dsmc
     and comparison.irve3_flight blocks]
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.abspath(os.path.join(
        script_dir, os.pardir, os.pardir,
        "results", "validation_scalloped", "validation_pipeline_output",
        "unified_comparison_data.json",
    ))

    def _fail(reason: str) -> "RuntimeError":
        # Verbose, full-context error (no silent degradation).
        print(
            f"ERROR: cannot load dynamic validation reference for J(x)\n"
            f"  Cause:  {reason}\n"
            f"  File:   {json_path}\n"
            f"  Fix:    restore/re-run the validation pipeline so\n"
            f"          unified_comparison_data.json exists with the\n"
            f"          comparison.stellarorion / comparison.irve3_flight keys.",
            file=sys.stderr,
        )
        return RuntimeError(f"validation refs unavailable: {reason}")

    if not os.path.isfile(json_path):
        raise _fail("file not found")

    try:
        # nosec: S305 -- read-only parse of a repository data file
        with open(json_path, encoding="utf-8") as fh:  # nosec: S305
            data = json.load(fh)
        so = data["comparison"]["stellarorion"]["raw_dsmc"]
        irve3 = data["comparison"]["irve3_flight"]
        q_target = float(so["total_heat_load_Jcm2"])
        cd_ref = float(so["cd"])
        flux_ref = float(irve3["peak_heat_flux_Wcm2"])
        flight_q = float(irve3["total_heat_load_Jcm2"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise _fail(f"JSON parse/schema error: {exc!r}") from exc

    # tau derived from the self-consistent FLIGHT pair (Q/q), so the
    # heating time is itself a product of the validation run.
    if not (flux_ref > 0.0):
        raise _fail(f"flux_ref={flux_ref!r} is not > 0 (cannot derive tau)")
    tau_sec = flight_q / flux_ref

    refs = {
        "q_target_jcm2": q_target,
        "flux_ref_wcm2": flux_ref,
        "tau_sec": tau_sec,
        "cd_ref": cd_ref,
        "flight_q_jcm2": flight_q,
    }
    for key, val in refs.items():
        # Same finiteness gate as ada_pinn_wrapper.set_validation_refs
        # (rejects NaN/inf and <= 0).
        if not (0.0 < val < float("inf")):
            raise _fail(f"{key}={val!r} is not a positive finite number")
    return refs


# ======================================================================
#  Hybrid validation gate (DSMC + PINN)          -- plan Part B
#  Multi-fidelity correction loop                -- plan Part C
# ======================================================================
#
#  PURPOSE: after the analytic BO winner is produced (steps 0-7), the
#  gate re-simulates that EXACT geometry with the high-fidelity chain
#  (SPARTA DSMC -> validation_pipeline PINN), compares the fresh
#  Total Heat Load against the validated target, writes a pass/fail
#  verdict into hiad_optimization_results.json, derives a bounded
#  correction factor from the prediction error, and re-optimizes J(x)
#  with that correction (round 2).
#
#  AXIOMS:
#    A1: An analytic optimum is only trustworthy if the high-fidelity
#        chain reproduces it -- the gate is ENFORCED, not advisory.
#    A2: The reference data in results/validation_scalloped/ is the
#        source of every J(x) reference; the gate MUST write into a
#        separate results/validation_optimized*/ directory and NEVER
#        touch the reference (via bin/main --results-dir, plan Part A).
#    A3: Fail LOUD: any missing file, non-zero child exit, timeout, or
#        schema drift aborts with exit code 1 and a full report --
#        there is never a fabricated verdict (no silent failure).
#    A4: PASS  <=>  q_hybrid <= q_target  (the DSMC+PINN heat load of
#        the optimized geometry must not exceed the validated target).
#    A5: Correction factor c = clamp(q_hybrid / q_analytic, 0.5, 2.0):
#        a bounded multiplicative bias term, so one bad simulation
#        cannot collapse or explode the round-2 objective.
#
#  THEORIES:
#    T1: By A4 the verdict is a pure function of two positive floats
#        and the target; it is deterministic and unit-testable.
#    T2: By A5, J_round2(x) = J(x) + (c-1) * heat_load_ratio(x) prices
#        the heat-load term at the corrected fidelity while leaving
#        drag/ballistic/penalty terms untouched; at c=1 it is exactly
#        J(x) (proved by self-test).
#    T3: Kennedy & O'Hagan (2000) [Citation 5]: a constant-bias
#        multiplicative factor is the standard first-order
#        multi-fidelity discrepancy when one code consistently
#        over/under-predicts another.
#
#  APPLICATIONS:
#    _parse_args          -- CLI flags (--hybrid-validate, --dry-run,
#                            --allow-fail, --validate-round2, --force,
#                            --steps)
#    _gate_preconditions  -- checks binary/docker/venv/pipeline exist
#    _run_logged          -- runs one child leg, streams to a log file,
#                            enforces timeout, echoes the log tail
#    _gate_verdict        -- T1 as code (pure, self-tested)
#    _correction_factor   -- A5 as code (pure, self-tested)
#    _make_corrected_cost -- T2 as code (self-tested at c=1)
#    _hybrid_gate         -- orchestrator: dry-run | full | round2
#
#  TIMING ANALYSIS
#  ---------------------------------------------------------------------------
#  Timing anchor      : time.monotonic() (CLOCK_MONOTONIC-backed, ns-class)
#  Estimated runtime  : geometry QA < 5 s; DSMC leg 2-3 h at 2200 steps
#                       [Citation: run.py "SPARTA DSMC validation runs take
#                       2-3h at 2200 steps"]; PINN pipeline 5-30 min;
#                       round-2 BO ~ 1-2 min (70 Ada FFI evals)
#  WCET               : bounded by _GATE_DSMC_TIMEOUT_S (4 h) and
#                       _GATE_PIPE_TIMEOUT_S (90 min) subprocess timeouts
#  Space complexity   : O(1) auxiliary; child output goes to log files
#  Hardware assumed   : Docker daemon (SPARTA), CPython 3.10+, GPU optional
#  ---------------------------------------------------------------------------

# Gate tuning constants (see AXIOMS A4/A5 above).
_GATE_DSMC_TIMEOUT_S = 4 * 3600     # docs: 2-3 h at 2200 steps + margin
_GATE_PIPE_TIMEOUT_S = 90 * 60      # 4000 PINN iterations, CPU/GPU
_GATE_QA_TIMEOUT_S = 300            # geometry QA, seconds in practice
_GATE_STEPS_DEFAULT = 2200          # matches the reference validation run
_GATE_SKIN = "scalloped"            # skin of the reference validation data
_GATE_CORR_MIN = 0.5                # A5 lower clamp
_GATE_CORR_MAX = 2.0                # A5 upper clamp
_GATE_PIPE_TARGET_STEP = 300000000  # run.py Phase 2b template [Citation 8]
_GATE_PIPE_ITERATIONS = 4000        # run.py Phase 2b template [Citation 8]
_GATE_BO_KWARGS = {"n_initial": 20, "n_iter": 50, "xi": 0.01, "seed": 42}


def _ccd_cost(entry: "dict[str, str | float]") -> float:
    """Return the numeric cost of one CCD sample entry (min() key helper).

    AXIOMS: every CCD entry carries a numeric 'cost' (Ada FFI J(x));
    'label' is the only string field of the entry.
    THEORIES: a named, fully annotated function (instead of an inline
    lambda) lets the type checker bind min()'s key overload
    deterministically -- lambda parameter inference through overloaded
    builtins is unreliable, and an un-inferable parameter is reported
    as implicit-any-lambda.
    APPLICATIONS: used as the key of min() when picking the best CCD
    seed for Bayesian Optimization.

    Args:
        entry: one CCD result dict (label: str, every other field float).

    Returns:
        The entry's cost as float.

    Raises:
        ValueError: 'cost' missing or not convertible to float.
    """
    try:
        return float(entry["cost"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"CCD entry has no numeric 'cost': {entry!r}"
        ) from exc


def _parse_args(argv: "list[str] | None" = None) -> "argparse.Namespace":
    """Parse CLI arguments for the optimizer and the hybrid gate.

    AXIOMS: the default (no flags) run must behave EXACTLY as before the
    gate existed -- every new capability is opt-in.
    THEORIES: argparse validates combinations (--dry-run without
    --hybrid-validate, non-positive --steps) and exits code 2 on misuse,
    before any simulation work starts.
    APPLICATIONS: returns a Namespace; main() consumes it.

    Args:
        argv: argument list (defaults to sys.argv[1:]).

    Returns:
        argparse.Namespace with keys hybrid_validate, dry_run,
        allow_fail, validate_round2, force, steps (int > 0).

    Raises:
        SystemExit: argparse error (code 2) on invalid usage.
    """
    parser = argparse.ArgumentParser(
        prog="hiad_optimizer.py",
        description=(
            "HIAD Bayesian optimizer with optional enforced hybrid "
            "validation gate (DSMC + PINN re-simulation of the winner)."
        ),
    )
    parser.add_argument(
        "--hybrid-validate", action="store_true",
        help="after BO, re-simulate the winner with SPARTA DSMC + PINN, "
             "write a pass/fail verdict to the results JSON, apply the "
             "multi-fidelity correction, and re-optimize (round 2)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="with --hybrid-validate: check preconditions, run the "
             "geometry QA leg, print the planned DSMC/PINN commands, "
             "then stop (no 2-3h simulation, no verdict)",
    )
    parser.add_argument(
        "--allow-fail", action="store_true",
        help="exit 0 even if the gate verdict is FAIL (verdict is still "
             "written to the JSON; use for data-collection runs)",
    )
    parser.add_argument(
        "--validate-round2", action="store_true",
        help="also run the DSMC+PINN gate on the round-2 geometry "
             "(doubles simulation time; default off)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="delete a pre-existing non-empty results/validation_optimized* "
             "directory before the gate runs (destructive, explicit)",
    )
    parser.add_argument(
        "--steps", type=int, default=_GATE_STEPS_DEFAULT,
        help=f"SPARTA timestep count for the gate DSMC leg "
             f"(default: {_GATE_STEPS_DEFAULT})",
    )
    args = parser.parse_args(argv)
    # Input validation (THEORY T1 needs positive denominators downstream).
    if args.steps <= 0:
        parser.error(f"--steps must be a positive integer, got {args.steps}")
    if args.dry_run and not args.hybrid_validate:
        parser.error("--dry-run requires --hybrid-validate")
    return args


def _gate_repo_root() -> str:
    """Return the repository root (stellarorion_program_proc/).

    AXIOMS: every gate path (bin/main, results/, venv_validation/) is
    defined relative to the repo root, independent of the CWD the script
    was launched from. Derivation: src/python/hiad_optimizer.py ->
    ../.. == repo root.

    Returns:
        Absolute path string of the repository root.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))


def _gate_preconditions(root: "str") -> "tuple[bool, dict[str, str]]":
    """Verify every external dependency the gate will invoke.

    AXIOMS (A3): check BEFORE launching hours of work -- a missing
    binary/daemon/venv discovered late would waste the whole window.
    THEORIES: all-or-nothing: every check must pass; each failure prints
    its own full diagnostic (exact path/command + fix hint).

    Args:
        root: repository root directory.

    Returns:
        (ok, paths): ok is True only if every check passed; paths maps
        logical names to absolute paths (binary, venv_py, pipeline,
        out_dir, csv, pipe_out, unified_json, ref_csv).
    """
    paths = {
        "root": root,
        "binary": os.path.join(root, "bin", "main"),
        "venv_py": os.path.join(root, "venv_validation", "bin", "python3"),
        "pipeline": os.path.join(root, "src", "python", "validation_pipeline.py"),
        "out_dir_rel": os.path.join("results", "validation_optimized"),
        "out_dir": os.path.join(root, "results", "validation_optimized"),
        "ref_csv": os.path.join(
            root, "results", "validation_scalloped", "validation_timeseries.csv"),
    }
    paths["csv"] = os.path.join(paths["out_dir"], "validation_timeseries.csv")
    paths["pipe_out"] = os.path.join(paths["out_dir"], "validation_pipeline_output")
    paths["unified_json"] = os.path.join(
        paths["pipe_out"], "unified_comparison_data.json")
    ok = True

    def _missing(what: "str", where: "str", fix: "str") -> None:
        nonlocal ok
        ok = False
        print(
            f"ERROR: hybrid gate precondition failed\n"
            f"  Missing: {what}\n"
            f"  Path:    {where}\n"
            f"  Fix:     {fix}",
            file=sys.stderr,
        )

    # 1) compiled Ada binary with execute permission
    if not os.path.isfile(paths["binary"]):
        _missing("SPARTA-capable binary bin/main", paths["binary"],
                 "alr build   (from stellarorion_program_proc/)")
    elif not os.access(paths["binary"], os.X_OK):
        _missing("bin/main is not executable", paths["binary"],
                 "chmod +x bin/main or rebuild with alr build")
    # 2) validation pipeline script
    if not os.path.isfile(paths["pipeline"]):
        _missing("validation_pipeline.py", paths["pipeline"],
                 "restore the file from version control")
    # 3) hash-gated validation venv (Python 3.12, DeepXDE) [Citation 8]
    if not os.path.isfile(paths["venv_py"]):
        _missing("venv_validation Python", paths["venv_py"],
                 "python3 -m venv venv_validation && venv_validation/bin/"
                 "pip install scikit-learn torch deepxde")
    # 4) Docker daemon up (SPARTA runs containerized) -- run the actual
    #    command, do not just check PATH (daemon down == still broken).
    if shutil.which("docker") is None:
        _missing("docker executable on PATH", "(which docker -> empty)",
                 "install Docker / start Colima: colima start")
    else:
        try:
            probe = subprocess.run(
                ["docker", "ps"], capture_output=True, text=True,
                timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok = False
            print(
                f"ERROR: hybrid gate precondition failed\n"
                f"  Command: docker ps\n"
                f"  Cause:   could not run ({exc!r})\n"
                f"  Fix:     start the daemon: colima start / "
                f"open Docker Desktop",
                file=sys.stderr,
            )
        else:
            if probe.returncode != 0:
                ok = False
                print(
                    f"ERROR: hybrid gate precondition failed\n"
                    f"  Command: docker ps (exit {probe.returncode})\n"
                    f"  stdout:  {probe.stdout.strip() or '(empty)'}\n"
                    f"  stderr:  {probe.stderr.strip() or '(empty)'}\n"
                    f"  Fix:     start the daemon: colima start / "
                    f"open Docker Desktop",
                    file=sys.stderr,
                )
    # 5) reference validation CSV must exist (it feeds J(x) refs; the
    #    gate also asserts the gate never overwrites it -- A2).
    if not os.path.isfile(paths["ref_csv"]):
        _missing("reference validation CSV", paths["ref_csv"],
                 "restore results/validation_scalloped/ from version control")
    return ok, paths


def _echo_log_tail(log_path: "str", n: int = 30) -> None:
    """Print the last n lines of a child log file (verbose reporting).

    Args:
        log_path: absolute path of the log file.
        n: number of trailing lines to print.

    Never raises: a missing/unreadable log is reported, not swallowed.
    """
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"  (could not read log {log_path}: {exc!r})", file=sys.stderr)
        return
    tail = lines[-n:]
    if tail:
        print(f"  --- last {len(tail)} log line(s) of {log_path} ---")
        for line in tail:
            print(f"  | {line}", end="" if line.endswith("\n") else "\n")
        print("  --- end of log tail ---")


def _run_logged(
    cmd: "list[str]",
    log_path: "str",
    timeout_s: int,
    cwd: "str",
    label: "str",
) -> "tuple[int, float]":
    """Run one gate leg, streaming its output to a log file.

    AXIOMS (A3): every failure mode (launch error, non-zero exit, timeout)
    produces a distinct, fully reported return code; nothing is silently
    mapped to success. Child stdout+stderr go to log_path so multi-hour
    output cannot blow up memory or the terminal scrollback.

    THEORY: on timeout, subprocess.run kills the direct child; note that
    grandchildren (e.g. docker) may survive -- a warning is printed so
    the operator can run `docker ps`/`docker kill`.

    Args:
        cmd: argv list (first element is the executable).
        log_path: file to receive combined child output.
        timeout_s: wall-clock budget in seconds.
        cwd: working directory for the child (repo root).
        label: short tag used in all printed messages.

    Returns:
        (rc, seconds): rc == 0 success; 124 timeout; 125 launch failure;
        otherwise the child's own exit code. seconds = elapsed runtime.
    """
    print(f"  [{label}] $ {' '.join(cmd)}")
    print(f"  [{label}] log: {log_path} (timeout {timeout_s}s)")
    t0 = time.monotonic()
    try:
        with open(log_path, "w", encoding="utf-8") as logfh:
            # argv list, no shell -- cannot inject separators
            proc = subprocess.run(
                cmd, stdout=logfh, stderr=subprocess.STDOUT,
                timeout=timeout_s, cwd=cwd, check=False,
            )
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        print(
            f"ERROR: [{label}] timed out after {timeout_s}s\n"
            f"  Command: {' '.join(cmd)}\n"
            f"  Log:     {log_path}\n"
            f"  NOTE:    direct child was killed; check for surviving "
            f"grandchildren with `docker ps`.",
            file=sys.stderr,
        )
        rc = 124
    except OSError as exc:
        print(
            f"ERROR: [{label}] failed to launch\n"
            f"  Command: {' '.join(cmd)}\n"
            f"  Cause:   {exc!r}\n"
            f"  Log:     {log_path}",
            file=sys.stderr,
        )
        rc = 125
    seconds = time.monotonic() - t0
    print(f"  [{label}] exit={rc} after {seconds:.1f}s")
    # Verbose: always show context; on failure show more (A3).
    _echo_log_tail(log_path, n=40 if rc != 0 else 15)
    return rc, seconds


def _gate_geometry_qa(
    binary: "str", geo_flags: "list[str]", root: "str", label: "str",
) -> int:
    """Run `bin/main --validate-only` for one geometry (seconds, no SPARTA).

    AXIOMS: a geometry the Ada engine cannot accept must fail the gate
    BEFORE the multi-hour DSMC leg. Output is captured (small) and echoed
    in full -- no log file, so dry-run stays side-effect free.

    Args:
        binary: absolute path of bin/main.
        geo_flags: ['--nose', v, '--tradius', v, '--angle', v,
                    '--skin', name].
        root: repo root (child CWD).
        label: tag for printed messages.

    Returns:
        0 on pass, child rc (or 124/125) on failure.
    """
    cmd = [binary, "--validate-only", *geo_flags]
    print(f"  [{label}] $ {' '.join(cmd)}")
    try:
        # argv list, no shell -- cannot inject separators
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=_GATE_QA_TIMEOUT_S, cwd=root, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"ERROR: [{label}] geometry QA could not run\n"
            f"  Command: {' '.join(cmd)}\n"
            f"  Cause:   {exc!r}",
            file=sys.stderr,
        )
        return 125
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    print(f"  [{label}] exit={proc.returncode}")
    return proc.returncode


def _prep_out_dir(out_dir: "str", force: bool) -> bool:
    """Create a fresh, empty gate output directory.

    AXIOMS (A2/A3): a non-empty directory means a previous (possibly
    partial) gate run -- silently mixing runs would corrupt the verdict.
    Refuse unless --force, in which case the directory is deleted and
    recreated (explicitly requested, loudly printed).

    Args:
        out_dir: absolute path of the directory.
        force: allow deleting a non-empty directory.

    Returns:
        True when the directory exists and is empty afterwards.
    """
    if os.path.isdir(out_dir):
        entries = sorted(os.listdir(out_dir))
        if entries:
            if not force:
                print(
                    f"ERROR: hybrid gate output directory is not empty\n"
                    f"  Dir:   {out_dir}\n"
                    f"  Items: {len(entries)} (e.g. {entries[:3]})\n"
                    f"  Cause: a previous gate run left data behind; "
                    f"mixing runs would corrupt the verdict.\n"
                    f"  Fix:   re-run with --force to delete it, or "
                    f"remove it manually.",
                    file=sys.stderr,
                )
                return False
            print(f"  [--force] removing previous gate dir: {out_dir}")
            try:
                shutil.rmtree(out_dir)
            except OSError as exc:
                print(
                    f"ERROR: could not remove {out_dir}: {exc!r}",
                    file=sys.stderr,
                )
                return False
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        print(
            f"ERROR: could not create {out_dir}: {exc!r}", file=sys.stderr,
        )
        return False
    return True


def _gate_verdict(
    q_hybrid: "float", q_analytic: "float", q_target: "float",
) -> "dict[str, Any]":
    """Compute the gate verdict and prediction error (THEORY T1, AXIOM A4).

    AXIOMS:
      A4: PASS <=> q_hybrid <= q_target (boundary counts as PASS).
      A3: q_analytic must be strictly positive -- a non-positive
          denominator means the analytic pipeline is broken, so raise
          loudly instead of returning a garbage percentage.

    Args:
        q_hybrid: fresh DSMC+PINN Total Heat Load [J/cm^2].
        q_analytic: analytic (Sutton-Graves-based) Q(x) of the winner.
        q_target: validated heat-load target [J/cm^2].

    Returns:
        dict: passed (bool), q_hybrid_Jcm2, q_analytic_Jcm2,
        q_target_Jcm2, prediction_error_pct (100*(hybrid-analytic)/analytic).

    Raises:
        ValueError: any non-finite value or q_analytic <= 0.
    """
    for name, val in (("q_hybrid", q_hybrid),
                      ("q_analytic", q_analytic),
                      ("q_target", q_target)):
        if not isinstance(val, (int, float)) or not (
            0.0 < float(val) < float("inf")
        ):
            raise ValueError(
                f"gate verdict input invalid: {name}={val!r} must be a "
                f"positive finite number (got {val!r})"
            )
    err_pct = (q_hybrid - q_analytic) / q_analytic * 100.0
    return {
        "passed": bool(q_hybrid <= q_target),
        "q_hybrid_Jcm2": float(q_hybrid),
        "q_analytic_Jcm2": float(q_analytic),
        "q_target_Jcm2": float(q_target),
        "prediction_error_pct": err_pct,
    }


def _correction_factor(q_hybrid: "float", q_analytic: "float") -> float:
    """Bounded multiplicative correction c = clamp(q_h/q_a, 0.5, 2.0).

    AXIOM A5 / THEORY T3 (Kennedy & O'Hagan 2000, Biometrika 87(1)):
    the ratio of fidelities is the first-order discrepancy term; the
    clamps guarantee one pathological simulation cannot make round 2
    minimize nonsense (safety fallback, even though it 'seems ignorable').

    Args:
        q_hybrid: fresh high-fidelity heat load [J/cm^2].
        q_analytic: analytic prediction [J/cm^2].

    Returns:
        float in [0.5, 2.0].

    Raises:
        ValueError: non-positive or non-finite inputs.
    """
    for name, val in (("q_hybrid", q_hybrid), ("q_analytic", q_analytic)):
        if not isinstance(val, (int, float)) or not (
            0.0 < float(val) < float("inf")
        ):
            raise ValueError(
                f"correction factor input invalid: {name}={val!r} must be "
                f"a positive finite number"
            )
    raw = q_hybrid / q_analytic
    return min(max(raw, _GATE_CORR_MIN), _GATE_CORR_MAX)


def _make_corrected_cost(correction: "float"):
    """Build J_round2(x) = J(x) + (c-1) * heat_load_ratio(x) (THEORY T2).

    AXIOMS: only the heat-load term carries the DSMC-vs-analytic bias
    (drag and ballistic terms come from geometry integrals, not the
    thermal model); therefore only that term is corrected.

    Args:
        correction: bounded factor c from _correction_factor().

    Returns:
        Callable (r_n, r_tor, half_cone_deg) -> float suitable for
        run_bayesian_optimize(). At c == 1.0 the result equals
        hiad_cost_function exactly (asserted by the self-test).
    """
    if not (0.0 < float(correction) < float("inf")):
        raise ValueError(f"correction must be positive finite, got {correction!r}")

    def _cost(r_n: "float", r_tor: "float", half_cone_deg: "float") -> float:
        base = hiad_cost_function(r_n, r_tor, half_cone_deg)
        comp = hiad_cost_components(r_n, r_tor, half_cone_deg)
        return base + (correction - 1.0) * comp["heat_load_ratio"]

    return _cost


def _load_hybrid_q(unified_json_path: "str") -> "dict[str, Any]":
    """Read the FRESH gate comparison JSON (never the reference one).

    AXIOM A3: same fail-loud schema gate as _load_validation_refs, but
    pointed at the gate's own output directory; a stale/missing file
    would silently verdict the WRONG simulation.

    Args:
        unified_json_path: path to the gate's unified_comparison_data.json.

    Returns:
        dict with q_hybrid_Jcm2, cd_hybrid, source_json.

    Raises:
        RuntimeError: missing file, schema drift, or non-positive values.
    """

    def _fail(reason: "str") -> "RuntimeError":
        print(
            f"ERROR: cannot load gate comparison result\n"
            f"  Cause: {reason}\n"
            f"  File:  {unified_json_path}\n"
            f"  Fix:   inspect the pipeline log; the PINN leg must write "
            f"unified_comparison_data.json before a verdict exists.",
            file=sys.stderr,
        )
        return RuntimeError(f"gate comparison unavailable: {reason}")

    if not os.path.isfile(unified_json_path):
        raise _fail("file not found")
    try:
        # nosec: S305 -- read-only parse of a repository data file
        with open(unified_json_path, encoding="utf-8") as fh:  # nosec: S305
            data = json.load(fh)
        so = data["comparison"]["stellarorion"]["raw_dsmc"]
        q_hybrid = float(so["total_heat_load_Jcm2"])
        cd_hybrid = float(so["cd"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise _fail(f"JSON parse/schema error: {exc!r}") from exc
    for name, val in (("q_hybrid_Jcm2", q_hybrid), ("cd_hybrid", cd_hybrid)):
        if not (0.0 < val < float("inf")):
            raise _fail(f"{name}={val!r} is not a positive finite number")
    return {
        "q_hybrid_Jcm2": q_hybrid,
        "cd_hybrid": cd_hybrid,
        "source_json": unified_json_path,
    }


def _write_gate_block(
    output_path: "str",
    block: "dict[str, object]",
    extra: "dict[str, object] | None" = None,
) -> bool:
    """Merge the gate block (and optional extras) into the results JSON.

    AXIOM A3: read-modify-write of the file step 6 just produced; any I/O
    or parse error is reported in full and returns False (caller maps it
    to exit 1) -- the verdict must never be lost silently.

    Args:
        output_path: hiad_optimization_results.json path.
        block: value for the top-level "hybrid_validation" key.
        extra: optional additional top-level merges (e.g. optimized_round2).

    Returns:
        True on successful write.
    """
    try:
        with open(output_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"ERROR: cannot read results JSON to store the gate verdict\n"
            f"  File:  {output_path}\n"
            f"  Cause: {exc!r}",
            file=sys.stderr,
        )
        return False
    data["hybrid_validation"] = block
    if extra:
        data.update(extra)
    try:
        # nosec: S305 -- JSON serialization of computed optimization data
        with open(output_path, "w", encoding="utf-8") as fh:  # nosec: S305
            json.dump(data, fh, indent=2)
    except OSError as exc:
        print(
            f"ERROR: cannot write gate verdict to results JSON\n"
            f"  File:  {output_path}\n"
            f"  Cause: {exc!r}",
            file=sys.stderr,
        )
        return False
    return True


def _gate_dsmc_pipeline(
    paths: "dict[str, str]",
    geo_flags: "list[str]",
    steps: int,
    out_dir_rel: "str",
    out_dir: "str",
    tag: "str",
) -> "tuple[int, dict[str, object]]":
    """Full high-fidelity leg: QA -> SPARTA DSMC -> PINN pipeline.

    Shared by round 1 and (optionally) round 2 -- single implementation,
    no copy-paste divergence. Each stage runs only if the previous one
    succeeded (short-circuit on first failure).

    Args:
        paths: from _gate_preconditions().
        geo_flags: geometry CLI flags for bin/main.
        steps: SPARTA timestep count.
        out_dir_rel: results dir relative to root (for --results-dir).
        out_dir: absolute results dir (must already exist).
        tag: 'r1' or 'r2', used in logs/messages.

    Returns:
        (rc, info): rc == 0 only if every stage succeeded; info holds
        commands, log paths, durations, csv/unified_json paths.
    """
    info: dict[str, Any] = {"tag": tag, "commands": {}, "logs": {},
                            "seconds": {}}
    # Stage 1: geometry QA (fast; duplicated from dry-run path only in
    # the sense that both call this same helper -- no divergence).
    qa_rc = _gate_geometry_qa(paths["binary"], geo_flags, paths["root"],
                              f"{tag}-qa")
    info["commands"]["qa"] = [paths["binary"], "--validate-only", *geo_flags]
    if qa_rc != 0:
        return 1, info

    # Stage 2: SPARTA DSMC (hours). --results-dir keeps reference data
    # safe (Part A made the flag actually work).
    dsmc_cmd = [
        paths["binary"], "--validate", "--headless", *geo_flags,
        "--steps", str(steps), "--results-dir", out_dir_rel,
    ]
    dsmc_log = os.path.join(out_dir, f"gate_{tag}_dsmc.log")
    info["commands"]["dsmc"] = dsmc_cmd
    info["logs"]["dsmc"] = dsmc_log
    rc, secs = _run_logged(dsmc_cmd, dsmc_log, _GATE_DSMC_TIMEOUT_S,
                           paths["root"], f"{tag}-dsmc")
    info["seconds"]["dsmc"] = secs
    if rc != 0:
        return 1, info

    # Verify the CSV the DSMC leg must have produced (A3: no missing
    # artifacts, ever).
    csv = paths["csv"] if tag == "r1" else os.path.join(
        out_dir, "validation_timeseries.csv")
    if not os.path.isfile(csv) or os.path.getsize(csv) == 0:
        print(
            f"ERROR: [{tag}-dsmc] reported success but the validation CSV "
            f"is missing or empty\n"
            f"  Expected: {csv}\n"
            f"  Log:      {dsmc_log}\n"
            f"  Fix:      inspect the DSMC log; SPARTA must write "
            f"validation_timeseries.csv.",
            file=sys.stderr,
        )
        return 1, info
    info["csv"] = csv

    # Stage 3: PINN pipeline (minutes) -- command mirrors run.py
    # Phase 2b exactly [Citation 8], plus an explicit --output-dir so
    # results land in the gate directory (A2).
    pipe_out = os.path.join(out_dir, "validation_pipeline_output")
    pipe_cmd = [
        paths["venv_py"], paths["pipeline"],
        "--csv", csv,
        "--target-step", str(_GATE_PIPE_TARGET_STEP),
        "--iterations", str(_GATE_PIPE_ITERATIONS),
        "--device", "auto",
        "--headless",
        "--output-dir", pipe_out,
    ]
    pipe_log = os.path.join(out_dir, f"gate_{tag}_pipeline.log")
    info["commands"]["pinn_pipeline"] = pipe_cmd
    info["logs"]["pinn_pipeline"] = pipe_log
    rc, secs = _run_logged(pipe_cmd, pipe_log, _GATE_PIPE_TIMEOUT_S,
                           paths["root"], f"{tag}-pinn")
    info["seconds"]["pinn"] = secs
    if rc != 0:
        return 1, info

    unified_json = os.path.join(pipe_out, "unified_comparison_data.json")
    if not os.path.isfile(unified_json):
        print(
            f"ERROR: [{tag}-pinn] reported success but wrote no "
            f"unified_comparison_data.json\n"
            f"  Expected: {unified_json}\n"
            f"  Log:      {pipe_log}",
            file=sys.stderr,
        )
        return 1, info
    info["unified_json"] = unified_json
    info["pipe_out"] = pipe_out
    return 0, info


def _hybrid_gate(
    args: "argparse.Namespace",
    output: "dict[str, Any]",
    output_path: "str",
    refs: "dict[str, float]",
) -> int:
    """Orchestrate the hybrid validation gate + correction loop.

    Flow (full mode): preconditions -> prepare dir -> geometry QA ->
    DSMC -> PINN -> verdict -> correction -> round-2 BO ->
    (optional round-2 validation) -> persist everything -> return code.

    Dry-run mode: preconditions -> geometry QA -> print planned commands
    -> persist a 'dry_run' block -> return 0 (no verdict, ever).

    Args:
        args: parsed CLI arguments.
        output: the in-memory results dict (step 6), source of the
            optimized geometry and analytic Q(x).
        output_path: results JSON path (verdict destination).
        refs: dynamic validation references (q_target_jcm2 used by A4).

    Returns:
        0: dry-run OK, verdict PASS, or FAIL with --allow-fail;
        1: infrastructure/child failure (no verdict or verdict stored
           with an 'error' field);
        3: verdict FAIL.
    """
    print("\n[8/8] Hybrid validation gate (DSMC + PINN re-simulation)")
    print("=" * 72)
    geo = output["optimized"]
    geometry = {
        "R_N": geo["R_N"],
        "r_tor": geo["r_tor"],
        "half_cone_deg": geo["half_cone_deg"],
    }
    q_analytic = float(geo["total_heat_load_Jcm2"])
    q_target = float(refs["q_target_jcm2"])
    geo_flags = [
        "--nose", f"{geometry['R_N']:.6f}",
        "--tradius", f"{geometry['r_tor']:.6f}",
        "--angle", f"{geometry['half_cone_deg']:.6f}",
        "--skin", _GATE_SKIN,
    ]
    block: dict[str, Any] = {
        "mode": "dry_run" if args.dry_run else "full",
        "geometry": geometry,
        "skin": _GATE_SKIN,
        "steps": args.steps,
        "q_analytic_Jcm2": q_analytic,
        "q_target_Jcm2": q_target,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": None,
        "error": None,
    }
    print(f"  Geometry: R_N={geometry['R_N']:.4f} m  "
          f"r_tor={geometry['r_tor']:.4f} m  "
          f"cone={geometry['half_cone_deg']:.4f} deg  skin={_GATE_SKIN}")
    print(f"  Analytic Q(x) = {q_analytic:.4f} J/cm^2   "
          f"target = {q_target:.4f} J/cm^2   steps = {args.steps}")

    def _abort(rc: int, reason: str) -> int:
        """Persist the failed state and return the exit code (A3)."""
        block["error"] = reason
        block["exit_code"] = rc
        block["finished_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not _write_gate_block(output_path, block):
            return 1
        print(f"\n  GATE ABORTED (exit {rc}): {reason}", file=sys.stderr)
        return rc

    ok, paths = _gate_preconditions(_gate_repo_root())
    if not ok:
        return _abort(1, "precondition check failed (see errors above)")

    # ---------- DRY RUN: preconditions + geometry QA + command preview --
    if args.dry_run:
        print("\n  [dry-run] preconditions OK; running geometry QA only ...")
        qa_rc = _gate_geometry_qa(paths["binary"], geo_flags,
                                  paths["root"], "dry-qa")
        block["geometry_qa_rc"] = qa_rc
        out_dir_rel = paths["out_dir_rel"]
        dsmc_cmd = [
            paths["binary"], "--validate", "--headless", *geo_flags,
            "--steps", str(args.steps), "--results-dir", out_dir_rel,
        ]
        pipe_cmd = [
            paths["venv_py"], paths["pipeline"],
            "--csv", os.path.join(paths["out_dir"],
                                  "validation_timeseries.csv"),
            "--target-step", str(_GATE_PIPE_TARGET_STEP),
            "--iterations", str(_GATE_PIPE_ITERATIONS),
            "--device", "auto", "--headless",
            "--output-dir", os.path.join(paths["out_dir"],
                                         "validation_pipeline_output"),
        ]
        block["planned_commands"] = {
            "dsmc": dsmc_cmd, "pinn_pipeline": pipe_cmd,
        }
        print("\n  [dry-run] commands that a full gate would run:")
        print(f"    1) {' '.join(dsmc_cmd)}")
        print(f"    2) {' '.join(pipe_cmd)}")
        print("  [dry-run] no simulation launched, no verdict written.")
        return _finish_dry(block, output_path, qa_rc)

    # ---------- FULL RUN -------------------------------------------------
    if not _prep_out_dir(paths["out_dir"], args.force):
        return _abort(1, "could not prepare a fresh gate output directory")
    print("\n  Stage 1/3: high-fidelity chain (QA -> DSMC -> PINN) ...")
    rc, info = _gate_dsmc_pipeline(paths, geo_flags, args.steps,
                                   paths["out_dir_rel"], paths["out_dir"],
                                   "r1")
    block["legs_r1"] = info
    if rc != 0:
        return _abort(1, "high-fidelity chain failed (see log paths above)")

    # ---------- VERDICT --------------------------------------------------
    print("\n  Stage 2/3: computing verdict (A4: q_hybrid <= q_target) ...")
    try:
        hybrid = _load_hybrid_q(str(info["unified_json"]))
        verdict = _gate_verdict(
            float(hybrid["q_hybrid_Jcm2"]), q_analytic, q_target)
        correction = _correction_factor(
            float(hybrid["q_hybrid_Jcm2"]), q_analytic)
    except (RuntimeError, ValueError) as exc:
        return _abort(1, f"verdict computation failed: {exc}")
    verdict["cd_hybrid"] = hybrid["cd_hybrid"]
    verdict["source_json"] = hybrid["source_json"]
    block["verdict"] = verdict
    block["correction_factor"] = correction
    passed = bool(verdict["passed"])
    print(f"  q_hybrid   = {verdict['q_hybrid_Jcm2']:.4f} J/cm^2 (DSMC+PINN)")
    print(f"  q_analytic = {verdict['q_analytic_Jcm2']:.4f} J/cm^2")
    print(f"  q_target   = {verdict['q_target_Jcm2']:.4f} J/cm^2")
    print(f"  prediction error = {verdict['prediction_error_pct']:+.4f} %")
    print(f"  correction factor = {correction:.6f}  (clamped to "
          f"[{_GATE_CORR_MIN}, {_GATE_CORR_MAX}])")
    print(f"  VERDICT: {'PASS' if passed else 'FAIL'}")

    # ---------- ROUND 2 (multi-fidelity correction, plan Part C) ---------
    print("\n  Stage 3/3: round-2 Bayesian Optimization with corrected J ...")
    try:
        corrected_cost = _make_corrected_cost(correction)
        result2 = run_bayesian_optimize(corrected_cost, **_GATE_BO_KWARGS)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        return _abort(1, f"round-2 optimization failed: {exc}")
    x2 = result2["x_opt"]
    r2_cd = estimate_cd(*x2)
    r2_comp = hiad_cost_components(*x2)
    round2 = {
        "R_N": x2[0],
        "r_tor": x2[1],
        "half_cone_deg": x2[2],
        "Cd": r2_cd,
        "cost": result2["cost"],
        "cost_uncorrected": hiad_cost_function(*x2),
        "total_heat_load_Jcm2": r2_comp["heat_load_jcm2"],
        "cost_components": r2_comp,
        "correction_factor": correction,
        "n_evaluations": result2["n_evals"],
        "history": result2["history"],
    }
    block["optimized_round2"] = {
        k: v for k, v in round2.items() if k != "history"}
    print(f"  Round-2 x* : R_N={x2[0]:.4f}  r_tor={x2[1]:.4f}  "
          f"cone={x2[2]:.4f}")
    print(f"  Round-2 J (corrected)   = {result2['cost']:.6f}")
    print(f"  Round-2 Q(x)            = {r2_comp['heat_load_jcm2']:.4f} "
          f"J/cm^2")

    # ---------- OPTIONAL ROUND-2 GATE (--validate-round2) ----------------
    if args.validate_round2:
        print("\n  [optional] validating round-2 geometry (2nd DSMC run) ...")
        out2_rel = os.path.join("results", "validation_optimized_round2")
        out2_abs = os.path.join(paths["root"], out2_rel)
        if not _prep_out_dir(out2_abs, args.force):
            return _abort(1, "could not prepare round-2 output directory")
        geo2_flags = [
            "--nose", f"{x2[0]:.6f}",
            "--tradius", f"{x2[1]:.6f}",
            "--angle", f"{x2[2]:.6f}",
            "--skin", _GATE_SKIN,
        ]
        rc2, info2 = _gate_dsmc_pipeline(paths, geo2_flags, args.steps,
                                         out2_rel, out2_abs, "r2")
        block["legs_r2"] = info2
        if rc2 != 0:
            return _abort(1, "round-2 high-fidelity chain failed")
        try:
            hybrid2 = _load_hybrid_q(str(info2["unified_json"]))
            v2 = _gate_verdict(float(hybrid2["q_hybrid_Jcm2"]),
                               float(round2["total_heat_load_Jcm2"]),
                               q_target)
        except (RuntimeError, ValueError) as exc:
            return _abort(1, f"round-2 verdict computation failed: {exc}")
        v2["source_json"] = hybrid2["source_json"]
        block["verdict_round2"] = v2
        print(f"  ROUND-2 VERDICT: {'PASS' if v2['passed'] else 'FAIL'} "
              f"(q_hybrid={v2['q_hybrid_Jcm2']:.4f})")

    # ---------- PERSIST --------------------------------------------------
    block["exit_code"] = 0 if (passed or args.allow_fail) else 3
    block["allow_fail"] = bool(args.allow_fail)
    block["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not _write_gate_block(output_path, block,
                             extra={"optimized_round2": round2}):
        return 1
    print(f"\n  Gate verdict stored in: {output_path}")
    print("=" * 72)
    if passed:
        return 0
    if args.allow_fail:
        print("  Verdict FAIL but --allow-fail given -> exit 0.",
              file=sys.stderr)
        return 0
    print("  VERDICT FAIL -> exit 3 (use --allow-fail to soften).",
          file=sys.stderr)
    return 3


def _finish_dry(
    block: "dict[str, object]", output_path: "str", qa_rc: int,
) -> int:
    """Persist the dry-run block and return its exit code.

    Split out so the dry-run branch of _hybrid_gate stays readable; same
    fail-loud persistence contract as _abort().
    """
    block["exit_code"] = 0 if qa_rc == 0 else 1
    block["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not _write_gate_block(output_path, block):
        return 1
    print(f"  Dry-run block stored in: {output_path}")
    return 0 if qa_rc == 0 else 1


# ======================================================================
#  Main Entry Point (thin: calls Ada FFI for all computation)
# ======================================================================


def main(argv: "list[str] | None" = None) -> int:
    """Run the full HIAD geometry optimization pipeline (+ optional gate).

    All computation is delegated to Ada/SPARK via FFI.
    This function only handles CLI output, JSON serialization, the
    step-7 diagnostic render (subprocess -> render_geometry_grid.py),
    and -- when --hybrid-validate is given -- the step-8 DSMC+PINN
    validation gate with its multi-fidelity correction loop.

    Args:
        argv: CLI argument list (defaults to sys.argv[1:]).

    Returns:
        0 on success (JSON written AND grid rendered; gate PASS,
        gate --dry-run success, or FAIL suppressed by --allow-fail),
        1 on any infrastructure failure (never 0 on error -- verbose
        errors go to stderr),
        3 when the hybrid gate verdict is FAIL (see _hybrid_gate).
    """
    args = _parse_args(argv)
    print("=" * 72)
    print("  HIAD Geometry Optimizer (Bayesian Optimization)")
    print("  CCD Sampling + Multi-Objective Cost (J) + GP Surrogate + EI")
    if args.hybrid_validate:
        mode = "DRY-RUN" if args.dry_run else "FULL"
        print(f"  Hybrid validation gate: ENABLED ({mode}, "
              f"steps={args.steps}, skin={_GATE_SKIN})")
    print("=" * 72)

    # --- Step 0: DYNAMIC validation base reference for J(x) ---
    # AXIOMS: J(x) normalises every term against the CURRENT validation
    # state (unified_comparison_data.json) — loaded BEFORE the first
    # cost evaluation so every subsequent J uses the same basis.
    # APPLICATIONS: fail LOUD (RuntimeError propagates -> main returns 1)
    # rather than optimising against a stale/absent reference.
    # [Citation: hiad_optimizer._load_validation_refs]
    print("\n[0/7] Loading dynamic validation base reference for J(x) ...")
    try:
        refs = _load_validation_refs()
    except RuntimeError:
        # _load_validation_refs already printed the full verbose error.
        return 1
    set_validation_refs(
        refs["q_target_jcm2"], refs["flux_ref_wcm2"],
        refs["tau_sec"], refs["cd_ref"],
    )
    print(f"  Q_target (Total Heat Load) = {refs['q_target_jcm2']:.6f} J/cm^2"
          f"   (StellarOrion validated)")
    print(f"  q_ref (peak heat flux)     = {refs['flux_ref_wcm2']:.6f} W/cm^2"
          f"   (IRVE-3 flight)")
    print(f"  tau (heating duration)     = {refs['tau_sec']:.6f} s"
          f"   (= Q_flight / q_flight, dynamic)")
    print(f"  Cd_ref                     = {refs['cd_ref']:.6f}"
          f"   (StellarOrion validated)")
    print(f"  flight Q reference         = {refs['flight_q_jcm2']:.6f} J/cm^2"
          f"   (IRVE-3 flight, reporting)")

    # --- Step 1: Load default geometry from Ada/SPARK ---
    print("\n[1/7] Loading default HIAD geometry from Ada/SPARK ...")
    try:
        hiad_cs = get_hiad_cross_section()
        print(f"  Loaded {hiad_cs['n']} cross-section points from Ada/SPARK")
        print(f"  X range: [{min(hiad_cs['x']):.4f}, {max(hiad_cs['x']):.4f}] m")
        print(f"  Y range: [{min(hiad_cs['y']):.4f}, {max(hiad_cs['y']):.4f}] m")
    except OSError as exc:
        print(f"  WARNING: Ada FFI call failed ({exc}).", file=sys.stderr)

    # --- Step 2: Compute default parameters and cost via Ada FFI ---
    # AXIOMS: refs from step 0 are already loaded, so default_cost and
    # the component breakdown below share the dynamic validation basis.
    print("\n[2/7] Computing default parameters and cost (via Ada FFI) ...")
    default_cd = estimate_cd(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    default_cost = hiad_cost_function(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    default_comp = hiad_cost_components(
        _DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)

    # Compute SG heat flux at default geometry
    try:
        sg_result = sutton_graves_heat_flux(_ALTITUDE_KM, _VELOCITY_MS, _DEFAULT_R_N)
        default_sg_wm2 = sg_result["heat_flux_Wm2"]
        default_sg_wcm2 = sg_result["heat_flux_Wcm2"]
    except OSError:
        # Fallback: local SG computation not available via Ada
        default_sg_wm2 = 0.0
        default_sg_wcm2 = 0.0

    print(f"  Default R_N = {_DEFAULT_R_N:.4f} m")
    print(f"  Default r_tor = {_DEFAULT_R_TOR:.4f} m")
    print(f"  Default half_cone = {_DEFAULT_HALF_CONE_DEG:.2f} deg")
    print(f"  Default Cd = {default_cd:.6f}")
    print(f"  Default cost J = {default_cost:.6f}")
    print(f"  Default Total Heat Load Q(x) = "
          f"{default_comp['heat_load_jcm2']:.4f} J/cm^2 "
          f"(target {refs['q_target_jcm2']:.4f} J/cm^2)")
    print(f"  J terms: heat_load={default_comp['heat_load_ratio']:.4f} "
          f"flux={default_comp['flux_ratio']:.4f} "
          f"beta_dev={default_comp['beta_dev']:.6f} "
          f"cd={default_comp['cd_ratio']:.4f} "
          f"penalty={default_comp['penalty']:.4f}")
    print(f"  SG heat flux = {default_sg_wcm2:.4f} W/cm^2 "
          f"({default_sg_wm2:.2f} W/m^2)")

    # --- Step 3: Generate CCD sample points via Ada FFI ---
    print("\n[3/7] Generating CCD sample points (via Ada FFI) ...")
    ccd_samples = generate_ccd_samples()
    print(f"  Generated {len(ccd_samples)} CCD samples:")
    for i, s in enumerate(ccd_samples):
        print(f"    [{i:2d}] {s['label']:25s}  "
              f"R_N={s['R_N']:.4f}  r_tor={s['r_tor']:.4f}  "
              f"cone={s['half_cone_deg']:.2f}")

    # --- Step 4: Evaluate cost at all CCD points via Ada FFI ---
    print("\n[4/7] Evaluating cost at CCD sample points (via Ada FFI) ...")
    # Explicit annotation so pyrefly can infer the lambda parameter type
    # in the min(...) key below (dict[str, str | float]: label is a str,
    # every other entry is a float).
    ccd_results: list[dict[str, str | float]] = []
    for s in ccd_samples:
        c_i = hiad_cost_function(s["R_N"], s["r_tor"], s["half_cone_deg"])
        ccd_results.append({
            "label": s["label"],
            "R_N": s["R_N"],
            "r_tor": s["r_tor"],
            "half_cone_deg": s["half_cone_deg"],
            "cost": c_i,
        })
        print(f"    {s['label']:25s}  J={c_i:.6f}")

    # Find best CCD point as initial guess for BO
    # Named key function (_ccd_cost): pyrefly cannot infer inline lambda
    # parameters through min()'s overloads; the helper is fully typed.
    best_ccd = min(ccd_results, key=_ccd_cost)
    print(f"\n  Best CCD point: {best_ccd['label']} (J={best_ccd['cost']:.6f})")

    # --- Step 5: Bayesian Optimization via GP surrogate ---
    print("\n[5/7] Running Bayesian Optimization (GP surrogate + EI) ...")
    result = run_bayesian_optimize(
        hiad_cost_function, n_initial=20, n_iter=50, xi=0.01, seed=42,
    )
    opt_r_n, opt_r_tor, opt_cone = result["x_opt"]
    opt_cd = estimate_cd(opt_r_n, opt_r_tor, opt_cone)
    opt_comp = hiad_cost_components(opt_r_n, opt_r_tor, opt_cone)

    # Compute SG at optimized geometry
    try:
        sg_opt = sutton_graves_heat_flux(_ALTITUDE_KM, _VELOCITY_MS, opt_r_n)
        opt_sg_wm2 = sg_opt["heat_flux_Wm2"]
        opt_sg_wcm2 = sg_opt["heat_flux_Wcm2"]
    except OSError:
        opt_sg_wm2 = 0.0
        opt_sg_wcm2 = 0.0

    print(f"  Best cost: {result['cost']:.6f} (after {result['n_evals']} evaluations)")
    print(f"  Optimized R_N = {opt_r_n:.6f} m")
    print(f"  Optimized r_tor = {opt_r_tor:.6f} m")
    print(f"  Optimized half_cone = {opt_cone:.6f} deg")
    print(f"  Optimized Cd = {opt_cd:.6f}")
    print(f"  Optimized cost J = {result['cost']:.6f}")
    print(f"  Optimized Total Heat Load Q(x) = "
          f"{opt_comp['heat_load_jcm2']:.4f} J/cm^2 "
          f"(target {refs['q_target_jcm2']:.4f} J/cm^2)")
    print(f"  J terms: heat_load={opt_comp['heat_load_ratio']:.4f} "
          f"flux={opt_comp['flux_ratio']:.4f} "
          f"beta_dev={opt_comp['beta_dev']:.6f} "
          f"cd={opt_comp['cd_ratio']:.4f} "
          f"penalty={opt_comp['penalty']:.4f}")
    print(f"  SG heat flux = {opt_sg_wcm2:.4f} W/cm^2 ({opt_sg_wm2:.2f} W/m^2)")

    # Improvement percentage
    if default_cost > 0:
        improvement_pct = ((default_cost - result["cost"]) / default_cost) * 100.0
    else:
        improvement_pct = 0.0
    print(f"\n  Cost improvement: {improvement_pct:+.4f}%")
    if default_cd > 0:
        cd_improvement_pct = ((default_cd - opt_cd) / default_cd) * 100.0
    else:
        cd_improvement_pct = 0.0
    print(f"  Cd improvement: {cd_improvement_pct:+.4f}%")

    # --- Step 6: Save results to JSON ---
    print("\n[6/7] Saving results to JSON ...")
    # Heat-load improvement (the PRIMARY objective of J(x)) vs the
    # default geometry; both are absolute Q(x) in J/cm^2.
    if default_comp["heat_load_jcm2"] > 0.0:
        hl_pct = (
            (default_comp["heat_load_jcm2"] - opt_comp["heat_load_jcm2"])
            / default_comp["heat_load_jcm2"] * 100.0
        )
    else:
        hl_pct = 0.0
    output = {
        # DYNAMIC validation base reference actually used for this run
        # (read from unified_comparison_data.json — see _load_validation_refs)
        "validation_refs": refs,
        "default": {
            "R_N": _DEFAULT_R_N,
            "r_tor": _DEFAULT_R_TOR,
            "half_cone_deg": _DEFAULT_HALF_CONE_DEG,
            "Cd": default_cd,
            "cost": default_cost,
            "total_heat_load_Jcm2": default_comp["heat_load_jcm2"],
            "cost_components": default_comp,
            "sutton_graves_heat_flux_Wcm2": default_sg_wcm2,
            "sutton_graves_heat_flux_Wm2": default_sg_wm2,
        },
        "optimized": {
            "R_N": opt_r_n,
            "r_tor": opt_r_tor,
            "half_cone_deg": opt_cone,
            "Cd": opt_cd,
            "cost": result["cost"],
            "total_heat_load_Jcm2": opt_comp["heat_load_jcm2"],
            "cost_components": opt_comp,
            "sutton_graves_heat_flux_Wcm2": opt_sg_wcm2,
            "sutton_graves_heat_flux_Wm2": opt_sg_wm2,
            "n_evaluations": result["n_evals"],
        },
        "improvement": {
            "cost_pct": improvement_pct,
            "cd_pct": cd_improvement_pct,
            "total_heat_load_pct": hl_pct,
        },
        "ccd_samples": ccd_results,
        # AXIOMS: run_bayesian_optimize() contract returns "history" -- the full
        # evaluation log (20 Latin-Hypercube initial + 50 BO iterations = 70 pts).
        # THEORIES: persisting it lets render_bo_3d_plot.py rebuild the 3D scatter,
        # GP surrogate slices, and convergence curve without re-running the optimizer.
        # APPLICATIONS: direct key access (not .get) so a broken contract raises
        # loudly instead of silently writing an empty history (no silent failure).
        # [Citation: ada_pinn_wrapper.py run_bayesian_optimize — returns history]
        "history": result["history"],
        "config": {
            "source": "Bayesian Optimization (GP surrogate + EI acquisition)",
            "algorithm": "Bayesian Optimization",
            "surrogate": "Gaussian Process (Matern 5/2 kernel)",
            "acquisition": "Expected Improvement (xi=0.01)",
            "initial_sampling": "Latin Hypercube (n=20)",
            "bo_iterations": 50,
        },
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "hiad_optimization_results.json")
    # nosec: S305 -- JSON serialization of computed optimization data
    with open(output_path, "w") as fh:  # nosec: S305
        json.dump(output, fh, indent=2)
    print(f"  Results saved to: {output_path}")

    # --- Summary ---
    print("\n" + "=" * 72)
    print("  OPTIMIZATION SUMMARY")
    print("=" * 72)
    print(f"  Default  Cd = {default_cd:.6f}  J = {default_cost:.6f}")
    print(f"  Optimized Cd = {opt_cd:.6f}  J = {result['cost']:.6f}")
    print(f"  Improvement: {improvement_pct:+.4f}% (cost), {cd_improvement_pct:+.4f}% (Cd)")
    print(f"  Total Heat Load (PRIMARY OBJECTIVE): "
          f"{default_comp['heat_load_jcm2']:.4f} -> "
          f"{opt_comp['heat_load_jcm2']:.4f} J/cm^2 "
          f"({hl_pct:+.4f}%, target {refs['q_target_jcm2']:.4f})")
    print(f"  Validation refs (dynamic): Q_target={refs['q_target_jcm2']:.4f}, "
          f"q_ref={refs['flux_ref_wcm2']:.4f}, tau={refs['tau_sec']:.4f}s, "
          f"Cd_ref={refs['cd_ref']:.4f}")
    print(f"  Evaluations: {result['n_evals']} (20 initial LHD + 50 BO iterations)")
    print(f"  SG heat flux: {opt_sg_wcm2:.4f} W/cm^2")
    print("=" * 72)

    # --- Step 7: Render the 87-panel geometry grid (diagnostic figure) ---
    # AXIOMS: the grid is pure post-processing of the JSON just written --
    # it must never re-run the optimizer (render_geometry_grid A4).
    # THEORIES: a missing/broken renderer is a broken checkout, not a soft
    # skip -- fail loudly with full child stderr (no silent degradation).
    # APPLICATIONS: subprocess with timeout; echo child output; return 1 on
    # any non-zero child exit or launch failure.
    # [Citation: scripts/render_geometry_grid.py main() exit-code contract]
    print("\n[7/7] Rendering 87-panel HIAD geometry grid ...")
    # Path: src/python/hiad_optimizer.py -> ../../scripts/render_geometry_grid.py
    grid_script = os.path.abspath(os.path.join(
        script_dir, os.pardir, os.pardir, "scripts",
        "render_geometry_grid.py",
    ))
    if not os.path.isfile(grid_script):
        print(
            f"ERROR: grid renderer not found: {grid_script}\n"
            f"  Cause: scripts/render_geometry_grid.py missing from checkout.\n"
            f"  Fix:   restore the file from version control.",
            file=sys.stderr,
        )
        return 1
    try:
        proc = subprocess.run(
            [sys.executable, grid_script],
            capture_output=True, text=True, timeout=600, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"ERROR: failed to launch grid renderer: {exc!r}\n"
            f"  Script: {grid_script}",
            file=sys.stderr,
        )
        return 1
    # Echo child output so the operator sees every renderer message.
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        print(
            f"ERROR: render_geometry_grid.py exited with code "
            f"{proc.returncode}\n"
            f"  JSON results were still saved to: {output_path}",
            file=sys.stderr,
        )
        return 1
    print("  Geometry grid rendered successfully.")

    # --- Step 8 (opt-in): hybrid validation gate + correction loop ---
    # AXIOM A1: only runs with an explicit --hybrid-validate; the default
    # pipeline above is untouched. The gate consumes the freshly written
    # results JSON (output/output_path) and appends its verdict block.
    # [Citation: plan Part B/C -- _hybrid_gate()]
    if not args.hybrid_validate:
        print("\n  Hybrid validation gate: skipped "
              "(enable with --hybrid-validate)")
        return 0
    return _hybrid_gate(args, output, output_path, refs)


# ======================================================================
#  Self-Test
# ======================================================================

if __name__ == "__main__":
    print("=== HIAD Geometry Optimizer Self-Test (Ada/SPARK FFI) ===\n")

    # Test CCD generation via Ada FFI
    ccd = generate_ccd_samples()
    assert len(ccd) == 15, f"CCD should have 15 samples, got {len(ccd)}"
    factorial = [s for s in ccd if s["label"].startswith("factorial")]
    assert len(factorial) == 8, f"Should have 8 factorial points, got {len(factorial)}"
    center = [s for s in ccd if s["label"] == "center"]
    assert len(center) == 1, f"Should have 1 center point, got {len(center)}"
    axial = [s for s in ccd if s["label"].startswith("axial")]
    assert len(axial) == 6, f"Should have 6 axial points, got {len(axial)}"
    print(f"  CCD: {len(ccd)} samples (8 factorial + 1 center + 6 axial) -- OK")

    # Test default cost via Ada FFI (dynamic refs loaded first so the
    # self-test exercises the SAME path as a real optimization run)
    refs_t = _load_validation_refs()
    set_validation_refs(
        refs_t["q_target_jcm2"], refs_t["flux_ref_wcm2"],
        refs_t["tau_sec"], refs_t["cd_ref"],
    )
    print(f"  Validation refs: Q_target={refs_t['q_target_jcm2']:.6f} "
          f"q_ref={refs_t['flux_ref_wcm2']:.6f} tau={refs_t['tau_sec']:.6f} "
          f"Cd_ref={refs_t['cd_ref']:.6f} -- OK")
    c_def = hiad_cost_function(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    assert c_def > 0, f"default J(x) should be positive, got {c_def}"
    print(f"  Default cost J = {c_def:.6f} -- OK")

    # Component breakdown must agree exactly with the scalar cost and
    # predict a positive absolute Total Heat Load (single source of truth)
    comp_t = hiad_cost_components(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    assert abs(comp_t["total"] - c_def) < 1e-12, (
        f"components.total {comp_t['total']!r} != hiad_cost_function {c_def!r}")
    assert comp_t["heat_load_jcm2"] > 0.0, (
        f"predicted Q(x) must be positive, got {comp_t['heat_load_jcm2']!r}")
    assert comp_t["penalty"] == 0.0, (
        f"default geometry must be penalty-free, got {comp_t['penalty']!r}")
    print(f"  Components: Q(x)={comp_t['heat_load_jcm2']:.4f} J/cm^2 "
          f"heat_load={comp_t['heat_load_ratio']:.4f} "
          f"flux={comp_t['flux_ratio']:.4f} beta_dev={comp_t['beta_dev']:.6f} "
          f"cd={comp_t['cd_ratio']:.4f} penalty={comp_t['penalty']:.4f} -- OK")

    # Test estimate_cd via Ada FFI
    cd_val = estimate_cd(_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG)
    assert cd_val > 0, "Cd should be positive"
    print(f"  Default Cd = {cd_val:.6f} -- OK")

    # Test MoP optimization via Ada FFI (still available for comparison)
    result = run_mop_optimize((_DEFAULT_R_N, _DEFAULT_R_TOR, _DEFAULT_HALF_CONE_DEG),
                               max_iter=20)
    assert "x_opt" in result
    assert "cost" in result
    assert "converged" in result
    print(f"  MoP test: {result['n_iter']} iterations, J={result['cost']:.6f} -- OK")

    # Test Bayesian Optimization (small run for self-test)
    bo_result = run_bayesian_optimize(hiad_cost_function, n_initial=10, n_iter=5, seed=0)
    assert "x_opt" in bo_result
    assert "cost" in bo_result
    assert "n_evals" in bo_result
    print(f"  BO test: {bo_result['n_evals']} evals, J={bo_result['cost']:.6f} -- OK")

    # --- Hybrid gate self-tests (Parts B/C): pure logic, no Docker ---
    # Verdict boundaries (AXIOM A4: PASS <=> q_hybrid <= q_target)
    v_pass = _gate_verdict(150.0, 155.06, 165.716)
    assert v_pass["passed"] is True, f"150.0 must PASS, got {v_pass}"
    assert abs(v_pass["prediction_error_pct"]
               - (150.0 - 155.06) / 155.06 * 100.0) < 1e-9, v_pass
    v_edge = _gate_verdict(165.716, 155.06, 165.716)
    assert v_edge["passed"] is True, f"boundary (== target) must PASS, got {v_edge}"
    v_fail = _gate_verdict(170.0, 155.06, 165.716)
    assert v_fail["passed"] is False, f"170.0 must FAIL, got {v_fail}"
    # Error path (A3): non-positive denominator raises, never returns junk
    try:
        _gate_verdict(1.0, 0.0, 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("_gate_verdict(1.0, 0.0, 1.0) should raise ValueError")
    # Correction clamps (AXIOM A5)
    assert _correction_factor(0.4, 1.0) == _GATE_CORR_MIN, "low clamp"
    assert _correction_factor(2.5, 1.0) == _GATE_CORR_MAX, "high clamp"
    assert abs(_correction_factor(1.2, 1.0) - 1.2) < 1e-12, "identity in-range"
    # Corrected cost at c == 1.0 is exactly J(x) (THEORY T2)
    cost_c1 = _make_corrected_cost(1.0)
    assert abs(cost_c1(_DEFAULT_R_N, _DEFAULT_R_TOR,
                       _DEFAULT_HALF_CONE_DEG) - c_def) < 1e-12, (
        "corrected cost with c=1 must equal the base cost")
    # JSON round-trip of a gate verdict block (temp file, cleaned up)
    rt_path = None
    try:
        fd, rt_path = tempfile.mkstemp(prefix="gate_selftest_", suffix=".json")
        os.close(fd)
        with open(rt_path, "w", encoding="utf-8") as fh:
            json.dump({"hybrid_validation": v_pass}, fh)
        with open(rt_path, encoding="utf-8") as fh:
            rt = json.load(fh)
        assert rt["hybrid_validation"]["passed"] is True, rt
        assert abs(rt["hybrid_validation"]["prediction_error_pct"]
                   - v_pass["prediction_error_pct"]) < 1e-12, rt
    finally:
        if rt_path is not None and os.path.isfile(rt_path):
            os.unlink(rt_path)
    # CLI parsing: defaults keep the legacy pipeline untouched
    a_gate = _parse_args(["--hybrid-validate", "--dry-run", "--steps", "100"])
    assert a_gate.hybrid_validate and a_gate.dry_run and a_gate.steps == 100, (
        a_gate)
    a_plain = _parse_args([])
    assert not a_plain.hybrid_validate and not a_plain.dry_run
    assert not a_plain.allow_fail and not a_plain.validate_round2
    assert not a_plain.force and a_plain.steps == _GATE_STEPS_DEFAULT, a_plain
    print("  Gate self-tests: verdict PASS/edge/FAIL + error path, "
          "clamp bounds, c=1 identity, JSON round-trip, CLI defaults -- OK")

    print("\nAll self-tests passed.\n")

    # Fail fast on bad CLI usage BEFORE the (possibly hours-long) pipeline.
    # argparse exits with code 2 and a usage message on invalid flags.
    _parse_args()

    # Run full optimization
    sys.exit(main())
