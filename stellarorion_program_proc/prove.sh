#!/usr/bin/env bash
# prove.sh — StellarOrion HypersonicEdition Verification Script
# Runs GNATprove formal verification, gnatcov code coverage, and Python coverage.
# [Citation: Ada 2012 Reference Manual, ISO/IEC 8652:2012]
# [Citation: SPARK 2014 Reference Manual, ISO/IEC 8652:2014]
# [Citation: GNATprove User Guide, AdaCore 2024]
# [Citation: coverage.py v7.6, https://coverage.readthedocs.io/]
#
# Usage: bash prove.sh [--level N] [--coverage] [--python-coverage]
#   --level N            GNATprove proof level (1-4, default: 4)
#   --coverage           Run gnatcov for Ada code coverage
#   --python-coverage    Run coverage.py for Python sidecar
#   --all                Run all verification steps (prove + coverage + python)

set -euo pipefail

# AXIOMS: StellarOrion uses Ada 2012/SPARK 2014 for core logic.
#   Python is used ONLY for library interfacing (PyTorch, DeepXDE, Docker).
#   All logic MUST be in Ada. Python sidecar is orchestration only.
# THEORIES: GNATprove at level 4 provides strongest formal verification.
#   gnatcov provides statement/decision coverage metrics.
#   coverage.py provides Python branch/line coverage.
# APPLICATIONS: This script orchestrates all three verification layers.

LEVEL=4
RUN_COVERAGE=false
RUN_PYTHON_COVERAGE=false
RUN_ALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --level)
            LEVEL="$2"
            shift 2
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --python-coverage)
            RUN_PYTHON_COVERAGE=true
            shift
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if $RUN_ALL; then
    RUN_COVERAGE=true
    RUN_PYTHON_COVERAGE=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo " StellarOrion HypersonicEdition — Verification Suite"
echo " GNATprove Level $LEVEL | gnatcov | Python coverage.py"
echo " $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "========================================================================"
echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 1: GNATprove Formal Verification
# ─────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 1: GNATprove Formal Verification (Level $LEVEL)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Running: alr exec -- gnatprove -P stellarorion_program_proc.gpr --level=$LEVEL"
echo ""

GNATPROVE_OUT="obj/gnatprove/gnatprove.out"
GNATPROVE_RC=0
alr exec -- gnatprove -P stellarorion_program_proc.gpr --level="$LEVEL" || GNATPROVE_RC=$?

echo ""

# ─────────────────────────────────────────────────────────────────────
# F-proof(1): a zero exit code means the proof run COMPLETED, not that
# every obligation was discharged.  GNATprove exits 0 on a finished run
# with unproved checks still in the summary.  Previously the script keyed
# `PASSED` on the exit code alone, so it printed "GNATprove: PASSED" with
# 31 unproved obligations sitting directly above that line.  PASSED is now
# keyed on an unproved count of exactly zero, parsed from the summary the
# prover itself wrote.
# ─────────────────────────────────────────────────────────────────────
if [ ! -f "$GNATPROVE_OUT" ]; then
    echo "GNATprove: FAILED (Level $LEVEL) -- summary missing at $GNATPROVE_OUT"
    echo "gnatprove exited $GNATPROVE_RC; without a summary the result cannot be read."
    exit 1
fi

# Sum (total - proved) over every `not proved, N checks out of M proved`
# line.  awk always prints a number, so an all-proved run yields 0.
UNPROVED=$(grep -oE 'not proved, [0-9]+ checks out of [0-9]+ proved' "$GNATPROVE_OUT" 2>/dev/null \
    | awk '{s += $7 - $3} END {print s+0}' || true)
UNPROVED=${UNPROVED:-0}

if [ "$GNATPROVE_RC" -ne 0 ]; then
    echo "GNATprove: FAILED (Level $LEVEL) -- gnatprove exited $GNATPROVE_RC"
    echo "Check the output above for analysis errors."
    exit 1
fi

if [ "$UNPROVED" -gt 0 ]; then
    echo "GNATprove: NOT PROVED (Level $LEVEL) -- $UNPROVED obligation(s) unproved"
    echo "Summary: $GNATPROVE_OUT (see the 'Unproved' column)."
    exit 1
fi

TOTAL_CHECKS=$(awk '/^Total /{print $2; exit}' "$GNATPROVE_OUT" 2>/dev/null || true)
TOTAL_CHECKS=${TOTAL_CHECKS:-?}
echo "GNATprove: PASSED (Level $LEVEL) -- $TOTAL_CHECKS checks, 0 unproved"

echo ""

# ─────────────────────────────────────────────────────────────────────
# Phase 2: gnatcov Ada Code Coverage (optional)
# ─────────────────────────────────────────────────────────────────────
# F-proof(2): these two MUST be initialised at TOP LEVEL.  They were only
# assigned inside `if $RUN_COVERAGE`, but line ~259 reads GNATCOV_FAILED
# unconditionally under `set -u`, so the default (no coverage requested)
# path died with "GNATCOV_FAILED: unbound variable" -- which read as
# "coverage failed" when coverage was never even asked for.  Same defect
# pattern PYTHON_COVERAGE_FAILED already had fixed; this closes the twin.
GNATCOV_STATUS="NOT RUN"
GNATCOV_FAILED=false

if $RUN_COVERAGE; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Phase 2: gnatcov Ada Code Coverage"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Building with coverage instrumentation..."
    echo ""

    # Build with coverage instrumentation
    # [Citation: GNAT User Guide — Code Coverage with gnatcov]
    if alr build --validation --report-level=stmt+decision; then
        echo ""
        echo "Ada build with coverage: PASSED"
    else
        echo ""
        echo "Ada build with coverage: FAILED"
        exit 1
    fi

    echo ""
    echo "Running gnatcov coverage analysis..."
    echo ""

    # F76: gnatcov outcome is a value, not a side effect.
    GNATCOV_STATUS="NOT RUN"
    GNATCOV_FAILED=false

    # Create coverage output directory
    mkdir -p obj/gcovr

    # Run gnatcov for statement and decision coverage
    # [Citation: GNATprove User Guide §8, Code Coverage Analysis]
    if gnatcov coverage -P stellarorion_program_proc.gpr \
        --level=stmt+decision \
        --output-dir=obj/gcovr \
        --buffer-size=16384 \
        src/simulation_engine/*.adb; then
        echo ""
        echo "gnatcov coverage: PASSED"
        echo "Report: obj/gcovr/"
        GNATCOV_STATUS="PASSED"
    else
        echo ""
        echo "gnatcov coverage: FAILED"
        GNATCOV_STATUS="FAILED"
        GNATCOV_FAILED=true
    fi

    echo ""
fi

# ─────────────────────────────────────────────────────────────────────
# Phase 3: Python Sidecar Coverage (optional)
# ─────────────────────────────────────────────────────────────────────
# F76: THE OUTCOME IS A VALUE, NOT A SIDE EFFECT.
# Before: nothing recorded whether the phase ran, passed or failed. The summary
# printed a report line purely because the flag was REQUESTED -- advertising
# obj/python_html/ that the fallback path never produced -- and the final
# "All verification steps completed successfully." was unconditional. So
# "Python coverage: FAILED" was immediately followed by success: the reported
# symptom. Now every failure mode sets PYTHON_COVERAGE_STATUS, the single gate
# PYTHON_COVERAGE_FAILED decides the exit, and the script exits non-zero.
PYTHON_COVERAGE_STATUS="NOT RUN"
PYTHON_COVERAGE_FAILED=false

if $RUN_PYTHON_COVERAGE; then
    echo "================================================================"
    echo "Phase 3: Python Sidecar Coverage (coverage.py)"
    echo "================================================================"
    echo ""

    PYTHON_SRC="$SCRIPT_DIR/src/python"
    # F76(1): WAS "$SCRIPT_DIR/tests/python" -- a directory that DOES NOT
    # EXIST. Both test modules live directly in tests/:
    #   tests/test_run_pipeline.py
    #   tests/test_validation_pipeline_regressions.py
    # With the old value discovery could never find a test, so
    # --python-coverage could never run the project's suite.
    PYTHON_TESTS="$SCRIPT_DIR/tests"

    # F76(2): WAS bare `python3` (the system interpreter, /opt/homebrew/bin),
    # which is neither this project's venv nor a guarantee that `coverage` is
    # installed -- and "pip install coverage --quiet 2>/dev/null || true" hid
    # that too. The project venv mandate says every Python dependency lives in
    # venv_validation/; this phase now uses exactly that interpreter.
    PYTHON_BIN="$SCRIPT_DIR/venv_validation/bin/python3"

    if [ ! -d "$PYTHON_SRC" ]; then
        echo "FATAL: Python source directory not found: $PYTHON_SRC" >&2
        PYTHON_COVERAGE_STATUS="FAILED (source directory missing)"
        PYTHON_COVERAGE_FAILED=true
    elif [ ! -d "$PYTHON_TESTS" ]; then
        echo "FATAL: Python test directory not found: $PYTHON_TESTS" >&2
        PYTHON_COVERAGE_STATUS="FAILED (test directory missing)"
        PYTHON_COVERAGE_FAILED=true
    elif [ ! -x "$PYTHON_BIN" ]; then
        echo "FATAL: project venv interpreter not found: $PYTHON_BIN" >&2
        PYTHON_COVERAGE_STATUS="FAILED (venv interpreter missing)"
        PYTHON_COVERAGE_FAILED=true
    else
        echo "Interpreter : $PYTHON_BIN"
        echo "Source      : $PYTHON_SRC"
        echo "Tests       : $PYTHON_TESTS"
        echo ""

        # F76(2) cont: THE TESTS ARE unittest-NATIVE, NOT pytest-NATIVE.
        # Both modules derive from unittest.TestCase, and this venv has NO
        # pytest ("python3 -m pytest" -> "No module named pytest"). The old
        # "-m pytest ... 2>/dev/null" therefore ALWAYS failed, and the
        # 2>/dev/null on the failing side of the if discarded exactly the
        # diagnostic that would have said so. unittest discover is the runner
        # these tests are written for; measured to run all 49 green here.
        # NOTE: the runner's output is deliberately NOT suppressed.
        # [Citation: coverage.py 7.x -- https://coverage.readthedocs.io/]
        # [Citation: Python 3.12 stdlib unittest -- test discovery protocol]
        echo "Running: coverage run --branch -m unittest discover -s tests ..."
        echo ""
        if "$PYTHON_BIN" -m coverage run \
                --source="$PYTHON_SRC" \
                --branch \
                --omit="*/tests/*,*/__pycache__/*" \
                -m unittest discover -s "$PYTHON_TESTS" -t "$SCRIPT_DIR"; then
            "$PYTHON_BIN" -m coverage report --show-missing || true
            "$PYTHON_BIN" -m coverage html -d obj/python_html || true
            echo ""
            echo "Python coverage: PASSED"
            echo "HTML report: obj/python_html/index.html"
            PYTHON_COVERAGE_STATUS="PASSED"
        else
            # F76(3) cont: the old fallback replaced a failed suite with an
            # import-only measurement ("-c import ... for every .py") --
            # measuring IMPORTS, not tests -- and then printed nothing at all.
            # Publishing a coverage figure for a suite that did not pass is
            # worse than publishing none, so nothing is published here.
            echo "" >&2
            echo "Python coverage: FAILED -- the unittest suite did not pass." >&2
            echo "  No coverage figure is published for a suite that did not" >&2
            echo "  pass. The previous behaviour replaced a failing run with" >&2
            echo "  an import-only measurement and then reported success." >&2
            PYTHON_COVERAGE_STATUS="FAILED (test suite did not pass)"
            PYTHON_COVERAGE_FAILED=true
        fi
    fi

    echo ""
fi

# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------
echo "================================================================"
echo "Verification Summary"
echo "================================================================"
echo "  GNATprove Level $LEVEL:  PASSED"
if $RUN_COVERAGE; then
    printf '  gnatcov coverage:       %s\n' "$GNATCOV_STATUS"
fi
# F76(3): the line now states the OUTCOME. Previously it printed whenever the
# flag was set, advertising a report that the fallback never produced.
printf '  Python coverage:        %s\n' "$PYTHON_COVERAGE_STATUS"
echo ""

# F76(3) cont: success is now a conclusion, not a constant.
if [ "$PYTHON_COVERAGE_FAILED" = "true" ] || [ "$GNATCOV_FAILED" = "true" ]; then
    echo "VERIFICATION FAILED -- the steps above did not all succeed."
    echo "================================================================"
    exit 1
fi
echo "All verification steps completed successfully."
echo "================================================================"
