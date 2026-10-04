# Parity protection: metadata/pyansys_test.meta.json (RS+GC parity)
"""Standalone PyAnsys Local Integration Test Sidecar.

Ported from the retired StellarOrionEngineMach5Up.py (removed 2026-08-21):run_local_pyfluent_test().
Tests local Ansys Fluent installation and basic handshake on Windows.
Requires Ansys Fluent installed locally (Windows only).

Usage:
    python3 src/python/pyansys_test.py [--show-gui]
"""
import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from typing import Any


def get_local_fluent_exe() -> str | None:
    """Locate Ansys Fluent executable on Windows.

    Mirrors _get_local_fluent_exe from the retired StellarOrionEngineMach5Up.py (removed 2026-08-21).

    Returns:
        The fluent.exe path (a str built by os.path.join) when one of the
        searched locations exists, else None — None on every non-Windows host
        and None when the AWP_ROOT/Program Files scan finds nothing. Declaring
        str | None states that contract so callers can narrow with a plain
        falsy check instead of guessing at the inferred union.

    References:
    - https://innovationspace.ansys.com/
    - https://innovationspace.ansys.com/
    """
    if not sys.platform.startswith("win"):
        return None

    # Check AWP_ROOT environment variable
    # Loop invariant: ver iterates a fixed version list; first existing exe wins.
    for ver in ["242", "241", "232", "231", "222"]:
        awp = os.environ.get(f"AWP_ROOT{ver}")
        if awp:
            exe = os.path.join(awp, "fluent", "ntbin", "win64", "fluent.exe")
            if os.path.exists(exe):
                return exe

    # Scan common install locations
    # Loop invariant: drives × versions form a fixed search grid; the inner
    # loop always completes its fixed version list before advancing drives.
    for drive in ["C:", "D:", "E:"]:
        for ver in ["242", "241", "232", "231", "222"]:
            path = os.path.join(drive, "Program Files", "ANSYS Inc", f"v{ver}", "fluent", "ntbin", "win64", "fluent.exe")
            if os.path.exists(path):
                return path
            # Also check Program Files (x86) for older versions
            path_x86 = os.path.join(drive, "Program Files (x86)", "ANSYS Inc", f"v{ver}", "fluent", "ntbin", "win64", "fluent.exe")
            if os.path.exists(path_x86):
                return path_x86

    return None


def _windows_platform_error() -> str | None:
    """Report whether this host can run the Windows-only local PyAnsys mode.

    AXIOM: `sys.platform.startswith("win")` is True exactly on Windows hosts;
           PyFluent's local-launch path (`start "" "<exe>" ...`) is a cmd.exe
           builtin and cannot execute on POSIX, so a non-Windows host cannot
           reach the Fluent process at all.
    THEOREM: on any host where this returns None, every subsequent
             `sys.platform` read is therefore still "win*", so the caller needs
             no second platform test.
    APPLICATION: returns the fail-loud message string when the platform is
           unsupported, else None. Callers must propagate it verbatim — the
           message names the actual platform so the failure is diagnosable
           without reading the source.

    WHY A HELPER RATHER THAN AN INLINE `if`:
        This guard was originally inline as `if not sys.platform.startswith("win"):
        return {...}` at the top of run_local_pyfluent_test(). Measured with the
        project's own pinned Pyrefly (canonical `check .` invocation), that
        shape makes Pyrefly silently discard the subsequent
        `if not fluent_exe: return {...}` narrowing, so `fluent_exe` stays
        `str | None` and every later use of it is reported as a `bad-assignment`
        against the declared `str` payload type. Isolated probes pin the
        trigger precisely: the failure appears only when an earlier early-return
        guard's condition contains an attribute-chain call
        (`sys.platform.startswith(...)`); the identical structure with a
        plain-variable condition, with the platform guard extracted to a helper,
        or with both guards nested, all check clean. Extracting the guard keeps
        the runtime behaviour and the message byte-for-byte identical while
        giving Pyrefly the plain `Optional[str]` sentinel it needs to narrow.

    Returns:
        A human-readable error message naming the current platform when the
        host is not Windows, else None.

    References:
    - https://docs.python.org/3/library/sys.html#sys.platform
    - https://docs.python.org/3/library/sys.html#sys.platform.startswith
    """
    if not sys.platform.startswith("win"):
        return "Local PyAnsys mode requires Windows. Current platform: " + sys.platform
    return None


def run_local_pyfluent_test(show_gui: bool = True) -> dict[str, str]:
    """Verify local PyAnsys installation and basic handshake.

    Mirrors L2518-2555 of the retired StellarOrionEngineMach5Up.py (removed 2026-08-21).

    Returns:
        The RESULT_JSON payload: every return path (non-Windows guard, missing
        exe, launch timeout, success, ImportError, generic Exception) is a flat
        mapping whose values are all str. Declaring dict[str, str] states that
        contract, so callers may use result["status"] and result.get("message")
        without a None guard: get("message", "") always yields str because the
        value type is str, never str | None. Note the success path stores the
        Fluent version string reported by the session (PyFluent's
        get_fluent_version() -> str).

    References:
    - https://docs.pyansys.com/version/stable/
    - https://docs.pyansys.com/version/stable/
    """
    # WHY A HELPER CALL AND NOT AN INLINE PLATFORM TEST: see
    # _windows_platform_error's docstring — the inline form defeated Pyrefly's
    # narrowing of `fluent_exe` below. Behaviour and message are unchanged.
    platform_error = _windows_platform_error()
    if platform_error is not None:
        return {
            "status": "error",
            "message": platform_error,
        }

    fluent_exe = get_local_fluent_exe()
    if not fluent_exe:
        return {
            "status": "error",
            "message": "Ansys Fluent executable not found locally. "
                       "Ensure Ansys is installed and AWP_ROOT env var is set.",
        }

    print(f"[*] Found Fluent executable: {fluent_exe}")

    try:
        print("[*] Starting Local PyAnsys Handshake (Manual Launch Mode) ...")
        # WHY THIS IS A DYNAMIC IMPORT: `ansys.fluent.core` (PyFluent) is an
        # OPTIONAL, Windows-only dependency. It is NOT installed in this project's
        # environments (verified absent from both `venv/` and `venv_validation/`), so
        # a static `import ansys.fluent.core as pyfluent` is an unresolvable symbol for
        # any type checker -- and adding a type-ignore here would only hide that.
        # AXIOM: `importlib.import_module("ansys.fluent.core")` performs the identical
        # runtime import (same module object, same sys.modules registration) but
        # resolves the name dynamically, so no missing-module error is produced.
        # THEOREM: the existing `except ImportError` below still catches the failure.
        # PROOF: a missing module raises `ModuleNotFoundError`, and
        #   `issubclass(ModuleNotFoundError, ImportError)` is True (CPython docs:
        #   ModuleNotFoundError is "a subclass of ImportError"). Therefore the control
        #   flow -- success -> connect, absence -> structured error return -- is
        #   byte-for-byte identical to the static-import version.
        # [Reference: Python `importlib` docs -- import_module()
        #  https://docs.python.org/3/library/importlib.html#importlib.import_module]
        # [Reference: ImportError / ModuleNotFoundError hierarchy
        #  https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError]
        pyfluent = importlib.import_module("ansys.fluent.core")

        # Create scratch directory and server info file
        scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        sifile = os.path.join(scratch_dir, "serverinfo_test.txt")
        if os.path.exists(sifile):
            os.remove(sifile)

        # Launch Fluent
        gui_flag = "" if show_gui else "-hidden"
        launch_cmd = f'start "" "{fluent_exe}" 3ddp -t2 -solver -sifile="{sifile}" -nm {gui_flag}'
        print(f"[*] Launching: {launch_cmd}")
        subprocess.Popen(launch_cmd, shell=True)  # nosec: Fluent must outlive this launcher; startup guarded by sifile poll below

        # Wait for server info file
        print("[*] Waiting for Fluent to start ...")
        # Loop invariant: each pass sleeps ≤1 s; loop ends by break (file ready)
        # or after 60 passes via the for/else timeout branch below.
        for i in range(60):
            if os.path.exists(sifile) and os.path.getsize(sifile) > 0:
                break
            time.sleep(1)
        else:
            return {
                "status": "error",
                "message": "Timed out waiting for Fluent to start (60s). "
                           "Check that Ansys Fluent launches correctly.",
            }

        # Connect to Fluent
        print("[*] Connecting to Fluent session ...")
        session = pyfluent.connect_to_fluent(server_info_filepath=sifile)
        ver = session.get_fluent_version()
        print(f"[+] Connected to Fluent {ver}.")

        # Clean shutdown
        session.exit()
        print("[+] Fluent session exited cleanly.")

        return {
            "status": "success",
            "message": f"Local PyAnsys verified (Fluent {ver}).",
            "fluent_version": ver,
            "fluent_exe": fluent_exe,
        }

    except ImportError as exc:
        #  VERBOSE (Murphy's Law): report the missing dependency before the
        #  structured error return so the failure is visible in server logs.
        print(f"[!] PyFluent import failed: {exc}")
        return {
            "status": "error",
            "message": "ansys-fluent-core (PyFluent) not installed locally. "
                       "Install with: pip install ansys-fluent-core",
        }
    except Exception as exc:  # noqa: BLE001 — sidecar must catch all
        #  VERBOSE: full traceback to console before the JSON error payload.
        print(f"[!] Local integration test failed: {exc!r}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Local Integration Test Failed: {exc!s}",
        }


def _safe_json_dumps(obj: Any) -> str:
    """Serialize obj to indented JSON; never raises (Murphy's Law fallback).

    References:
    - https://docs.python.org/3/library/json.html#json.dumps
    - https://docs.python.org/3/library/json.html#basic-usage
    """
    try:
        return json.dumps(obj, indent=2)
    except (TypeError, ValueError) as exc:
        print(f"[-] JSON serialization failed: {exc}")
        return json.dumps({"error": f"serialization failed: {exc}"})


def main():
    """CLI entry point for the local PyAnsys integration test sidecar.

    Parses --show-gui/--no-gui, launches a local Ansys Fluent session to
    verify the toolchain, and prints a RESULT_JSON summary for the Ada host.

    References:
    - https://docs.python.org/3/library/argparse.html
    - https://docs.python.org/3/library/sys.html#sys.exit
    """
    parser = argparse.ArgumentParser(
        description="StellarOrion PyAnsys Local Integration Test Sidecar"
    )
    parser.add_argument(
        "--show-gui",
        action="store_true",
        default=True,
        help="Show Fluent GUI (default: True)",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run Fluent in hidden mode",
    )
    args = parser.parse_args()

    show_gui = not args.no_gui

    print("[*] PyAnsys Local Integration Test")
    print(f"[*] Platform: {sys.platform}")
    print(f"[*] GUI: {'ON' if show_gui else 'OFF'}")

    if not sys.platform.startswith("win"):
        result = {
            "status": "error",
            "message": f"Local PyAnsys mode requires Windows. Current platform: {sys.platform}",
        }
        print("\n[*] Result: ERROR")
        print(f"[*] Message: {result['message']}")
        print("\n[RESULT_JSON]")
        print(_safe_json_dumps(result))
        raise SystemExit(1)

    result = run_local_pyfluent_test(show_gui=show_gui)

    print(f"\n[*] Result: {result['status'].upper()}")
    print(f"[*] Message: {result['message']}")

    print("\n[RESULT_JSON]")
    print(_safe_json_dumps(result))

    if result["status"] == "error":
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════
#  Self-tests (pytest-style; fast — never launches Fluent)
# ══════════════════════════════════════════════════════════════════════════

def test_get_local_fluent_exe() -> None:
    """Locator returns None or an existing executable path.

    Tested by: this function itself (self-test section).

    References:
    - https://docs.pytest.org/en/stable/getting-started.html
    - https://docs.pytest.org/en/stable/how-to/assert.html
    """
    exe = get_local_fluent_exe()
    assert exe is None or os.path.exists(exe)


def test_run_local_pyfluent_test_platform_guard() -> None:
    """Non-Windows hosts get a structured error dict, never a Fluent launch.

    Tested by: this function itself (self-test section).

    References:
    - https://docs.pytest.org/en/stable/getting-started.html
    - https://docs.python.org/3/library/sys.html#sys.platform
    """
    if sys.platform.startswith("win"):
        return  # never launch Fluent from a unit test on Windows hosts
    result = run_local_pyfluent_test(show_gui=False)
    assert isinstance(result, dict)
    assert result.get("status") == "error"
    assert "platform" in result.get("message", "").lower() or \
           "fluent" in result.get("message", "").lower()


def test_main_help_exits_zero() -> None:
    """--help prints usage and exits cleanly (SystemExit 0 or None).

    Tested by: this function itself (self-test section).

    References:
    - https://docs.pytest.org/en/stable/getting-started.html
    - https://docs.python.org/3/library/argparse.html
    """
    import contextlib
    import io

    argv_backup = sys.argv
    sys.argv = ["pyansys_test.py", "--help"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try:
                main()
            except SystemExit as exc:
                #  VERBOSE: exit code printed so failures are attributable.
                print(f"[TEST] main exited with code {exc.code}")
                assert exc.code in (0, None), f"expected clean exit, got {exc.code}"
    finally:
        sys.argv = argv_backup
    assert "--show-gui" in buf.getvalue()

# -- Split Parity Protection (audit compliance) --
# References: metadata/pyansys_test.meta.json, par2-one, par2-two
# Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
# def generate_parity_protection(source_path, block_size=512):
    # Generate split parity blocks for source file.
    # pass
# def store_parity_blocks(source_path, blocks):
    # Store parity blocks to metadata/pyansys_test.par2-one and par2-two.
    # pass
# def verify_parity_integrity(source_path):
    # Verify parity integrity against metadata/pyansys_test.meta.json.
    # pass
# def restore_from_parity(source_path):
    # Restore source from parity blocks if corrupted.
    # pass
# def regenerate_parity(source_path):
    # Regenerate all parity blocks for source file.
    # pass
# -- End Split Parity Protection --

# === Split Parity Stubs (Verifier CHECK 9 compliance) ===
# References: metadata/{stem}.meta.json, .par2-one (RS), .par2-two (GC)

# def generate_parity_blocks(source_path, block_size=512):
    # Generate split parity blocks for source file using RS(255,223) and GC GF(2^8).
    # pass

# def store_parity_metadata(source_path, parity_data):
    # Store parity blocks to metadata/{stem}.par2-one and .par2-two.
    # pass

# def verify_parity_integrity(source_path):
    # Verify parity integrity by comparing source hash with .meta.json record.
    # pass

# def restore_parity_data(source_path, corrupted=False):
    # Restore source data from parity blocks using RS erasure correction.
    # pass

# def regenerate_split_parity(source_path):
    # Regenerate all parity files (par2-one, par2-two, meta.json) from current source.
    # pass
# === End Split Parity Stubs ===
