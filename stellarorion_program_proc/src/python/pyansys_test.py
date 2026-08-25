"""Standalone PyAnsys Local Integration Test Sidecar.

Ported from StellarOrionEngineMach5Up.py:run_local_pyfluent_test().
Tests local Ansys Fluent installation and basic handshake on Windows.
Requires Ansys Fluent installed locally (Windows only).

Usage:
    python3 src/python/pyansys_test.py [--show-gui]
"""
import argparse
import json
import os
import subprocess
import sys
import time


def get_local_fluent_exe():
    """Locate Ansys Fluent executable on Windows.

    Mirrors _get_local_fluent_exe from StellarOrionEngineMach5Up.py.
    """
    if sys.platform != "win32":
        return None

    # Check AWP_ROOT environment variable
    for ver in ["242", "241", "232", "231", "222"]:
        awp = os.environ.get(f"AWP_ROOT{ver}")
        if awp:
            exe = os.path.join(awp, "fluent", "ntbin", "win64", "fluent.exe")
            if os.path.exists(exe):
                return exe

    # Scan common install locations
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


def run_local_pyfluent_test(show_gui=True):
    """Verify local PyAnsys installation and basic handshake.

    Mirrors L2518-2555 of StellarOrionEngineMach5Up.py.
    """
    if sys.platform != "win32":
        return {
            "status": "error",
            "message": "Local PyAnsys mode requires Windows. Current platform: " + sys.platform,
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
        import ansys.fluent.core as pyfluent

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

    except ImportError:
        return {
            "status": "error",
            "message": "ansys-fluent-core (PyFluent) not installed locally. "
                       "Install with: pip install ansys-fluent-core",
        }
    except Exception as exc:  # noqa: BLE001 — sidecar must catch all
        return {
            "status": "error",
            "message": f"Local Integration Test Failed: {exc!s}",
        }


def _safe_json_dumps(obj):
    """Serialize obj to indented JSON; never raises (Murphy's Law fallback)."""
    try:
        return json.dumps(obj, indent=2)
    except (TypeError, ValueError) as exc:
        print(f"[-] JSON serialization failed: {exc}")
        return json.dumps({"error": f"serialization failed: {exc}"})


def main():
    """CLI entry point for the local PyAnsys integration test sidecar.

    Parses --show-gui/--no-gui, launches a local Ansys Fluent session to
    verify the toolchain, and prints a RESULT_JSON summary for the Ada host.
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

    if sys.platform != "win32":
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
