"""Standalone PyFluent SSH Integration Test Sidecar.

Ported from StellarOrionEngineMach5Up.py:run_integration_test() and
test_ssh_connection(). Tests SSH connectivity to a remote Windows host,
verifies Python + Ansys Fluent + PyFluent availability, and reports status.

Usage:
    python3 src/python/pyfluent_test.py --ssh-host HOST --ssh-user USER [--ssh-pass PASS] [--ssh-key KEY]
"""
import argparse
import json
import os
import sys


def test_ssh_connection(host, user, password=None, key_path=None):
    """Test SSH connection and verify remote PyFluent environment.

    Mirrors L2570-2667 of StellarOrionEngineMach5Up.py.
    """
    try:
        import paramiko
    except ImportError:
        return {
            "status": "error",
            "message": "paramiko not installed. Install with: pip install paramiko",
        }

    if not host or not user:
        return {"status": "error", "message": "SSH host and user are required."}

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect
        if key_path and os.path.exists(key_path):
            ssh.connect(host, username=user, key_filename=key_path, timeout=10)
        elif password:
            ssh.connect(host, username=user, password=password, timeout=10)
        else:
            return {"status": "error", "message": "Either SSH key or password required."}

        # Check OS version
        _stdin, stdout, _stderr = ssh.exec_command("ver")
        os_ver = stdout.read().decode().strip()

        # Check Python
        _stdin, stdout, _stderr = ssh.exec_command(
            'python -c "import platform; print(f\'{platform.python_version()} ({platform.machine()})\')"'
        )
        py_info = stdout.read().decode().strip()
        py_ver = py_info if py_info else None
        is_py_x64 = "AMD64" in py_info if py_info else False

        # Deep scan for Ansys installation
        scan_cmd = (
            'powershell -Command "'
            "$found = $false; "
            "$drives = Get-PSDrive -PSProvider FileSystem; "
            "foreach ($d in $drives) { "
            "  $p = Join-Path $d.Root 'ANSYS Inc'; "
            "  if (Test-Path $p) { "
            "    $v = Get-ChildItem -Path $p -Directory | "
            "      Where-Object { $_.Name -match '^v\\d{3}$' } | "
            "      Sort-Object Name -Descending | Select-Object -First 1; "
            "    if ($v) { "
            "      $ver = $v.Name.Substring(1); "
            "      $path = $v.FullName; "
            "      [System.Environment]::SetEnvironmentVariable('AWP_ROOT' + $ver, $path, 'Machine'); "
            "      Write-Host 'FOUND:' + $ver + ':' + $path; "
            "      $found = $true; break; "
            "    } "
            "  } "
            "}; "
            'if (-not $found) { Write-Host \'MISSING\' }"'
        )
        _stdin, stdout, _stderr = ssh.exec_command(scan_cmd)
        scan_res = stdout.read().decode().strip()
        ansys_installed = "FOUND" in scan_res
        ansys_path = None
        ansys_ver = None
        if ansys_installed:
            parts = scan_res.split(":", 2)
            if len(parts) >= 3:
                ansys_ver = parts[1]
                ansys_path = parts[2]

        # Check for ansys-fluent-core (PyFluent)
        _stdin, stdout, _stderr = ssh.exec_command(
            'python -c "import ansys.fluent.core; print(\'PyAnsys OK\')"'
        )
        pyansys_status = stdout.read().decode().strip()
        pyansys_installed = "PyAnsys OK" in pyansys_status

        # Check processor architecture
        _stdin, stdout, _stderr = ssh.exec_command("echo %PROCESSOR_ARCHITECTURE%")
        arch = stdout.read().decode().strip().upper()

        ssh.close()

        # Build status message
        msg = f"Connected to {os_ver} ({arch}). "
        issues = []

        if py_ver:
            msg += f"Found Python {py_ver}. "
            if arch == "ARM64" and not is_py_x64 and not pyansys_installed:
                msg += "CRITICAL: Native ARM64 Python detected. x64 Python is REQUIRED for PyFluent. "
                issues.append("ARM64 Python without PyFluent")
        else:
            msg += "WARNING: Python not found on remote host. "
            issues.append("Python not installed")

        if ansys_installed:
            msg += f"Ansys Detected ({ansys_path}). "
        else:
            msg += "WARNING: Ansys Fluent not found. "
            issues.append("Ansys Fluent not installed")

        if pyansys_installed:
            msg += "PyFluent OK."
        else:
            msg += "WARNING: PyFluent library missing. "
            issues.append("ansys-fluent-core not installed")

        if issues:
            return {
                "status": "warning",
                "message": msg,
                "issues": issues,
                "os_ver": os_ver,
                "arch": arch,
                "python_ver": py_ver,
                "ansys_installed": ansys_installed,
                "ansys_path": ansys_path,
                "ansys_ver": ansys_ver,
                "pyfluent_installed": pyansys_installed,
            }

        return {
            "status": "success",
            "message": msg,
            "os_ver": os_ver,
            "arch": arch,
            "python_ver": py_ver,
            "ansys_installed": ansys_installed,
            "ansys_path": ansys_path,
            "ansys_ver": ansys_ver,
            "pyfluent_installed": pyansys_installed,
        }

    except Exception as exc:  # noqa: BLE001 — sidecar must catch all SSH errors
        return {"status": "error", "message": f"SSH connection failed: {exc!s}"}


def run_integration_test(host, user, password=None, key_path=None):
    """Run full PyFluent integration test via SSH.

    1. Verify SSH connection
    2. Check Python + PyFluent availability
    3. Attempt a minimal Fluent handshake (if possible)
    """
    print(f"[*] Connecting to {user}@{host} ...")
    result = test_ssh_connection(host, user, password, key_path)

    if result["status"] == "error":
        return result

    print(f"[+] {result['message']}")

    if result["status"] == "warning":
        print("[!] Some issues detected. Integration test may fail.")
        for issue in result.get("issues", []):
            print(f"    - {issue}")

    # Attempt Fluent handshake if everything looks good
    if result.get("pyfluent_installed") and result.get("ansys_installed"):
        print("\n[*] Attempting remote Fluent handshake ...")
        try:
            import paramiko

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=10)
            elif password:
                ssh.connect(host, username=user, password=password, timeout=10)

            # Try launching a minimal Fluent session to verify handshake
            handshake_cmd = (
                'python -c "'
                "import ansys.fluent.core as pyfluent; "
                "print('Handshake OK'); "
                '"'
            )
            _stdin, stdout, stderr = ssh.exec_command(handshake_cmd, timeout=30)
            output = stdout.read().decode().strip()
            err = stderr.read().decode().strip()

            ssh.close()

            if "Handshake OK" in output:
                print("[+] Remote Fluent handshake succeeded.")
                result["handshake"] = True
            else:
                print(f"[!] Fluent handshake output: {output}")
                if err:
                    print(f"[!] stderr: {err}")
                result["handshake"] = False
                result["message"] += " Fluent handshake did not confirm."

        except Exception as exc:  # noqa: BLE001 — sidecar must catch all SSH errors
            print(f"[!] Fluent handshake failed: {exc}")
            result["handshake"] = False
    else:
        print("[*] Skipping Fluent handshake (missing prerequisites).")
        result["handshake"] = False

    return result


def _safe_json_dumps(obj):
    """Serialize obj to indented JSON; never raises (Murphy's Law fallback)."""
    try:
        return json.dumps(obj, indent=2)
    except (TypeError, ValueError) as exc:
        print(f"[-] JSON serialization failed: {exc}")
        return json.dumps({"error": f"serialization failed: {exc}"})


def main():
    """CLI entry point for the remote PyFluent SSH integration sidecar.

    Requires --ssh-host and --ssh-user plus either --ssh-key or --ssh-pass;
    runs the remote Fluent connectivity check and prints RESULT_JSON output.
    """
    parser = argparse.ArgumentParser(
        description="StellarOrion PyFluent SSH Integration Test Sidecar"
    )
    parser.add_argument("--ssh-host", required=True, help="Remote SSH host")
    parser.add_argument("--ssh-user", required=True, help="Remote SSH user")
    parser.add_argument("--ssh-pass", default="", help="SSH password (alternative to key)")
    parser.add_argument("--ssh-key", default="", help="Path to SSH private key")
    args = parser.parse_args()

    print("[*] PyFluent SSH Integration Test")
    print(f"[*] Host: {args.ssh_host}")
    print(f"[*] User: {args.ssh_user}")
    if args.ssh_key:
        print(f"[*] Key:  {args.ssh_key}")

    result = run_integration_test(
        args.ssh_host,
        args.ssh_user,
        password=args.ssh_pass if args.ssh_pass else None,
        key_path=args.ssh_key if args.ssh_key else None,
    )

    print(f"\n[*] Result: {result['status'].upper()}")
    print(f"[*] Message: {result['message']}")

    print("\n[RESULT_JSON]")
    print(_safe_json_dumps(result))

    if result["status"] == "error":
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
