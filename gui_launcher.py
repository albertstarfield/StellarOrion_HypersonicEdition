import sys
import os
import subprocess
import shutil
import venv

# Pipe stdio and stderr to TestlogDev.log
class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

log_file = os.path.join(os.getcwd(), "TestlogDev.log")
sys.stdout = Logger(log_file)
sys.stderr = Logger(log_file)

print(f"\n--- Application Started: {os.path.abspath(__file__)} ---")

def setup_and_launch():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, ".venv_gui")
    
    # Check for manual reset flag
    if "--reset" in sys.argv:
        print("[!] Reset flag detected. Purging environment...")
        if os.path.exists(venv_dir):
            shutil.rmtree(venv_dir)

    # 1. Disk Space Check
    try:
        stat = os.statvfs(base_dir)
        free_bytes = stat.f_bavail * stat.f_frsize
        free_gb = free_bytes / (1024**3)
        if free_gb < 1.0:
            print(f"[!] WARNING: Extremely low disk space ({free_gb:.2f} GB free).")
            print("[*] Installation of CadQuery/Torch may fail. Please free up space.")
            print("[*] Suggestion: Delete 'tmp_sparta_build' or old 'CADDesign/venv' folders.")
    except: pass

    # 2. Determine Python & Pip executables (Robust across Windows/Unix styles)
    def detect_venv_paths():
        v_py = None
        v_pip = None
        pot_py = [
            os.path.join(venv_dir, "Scripts", "python.exe"),
            os.path.join(venv_dir, "bin", "python.exe"),
            os.path.join(venv_dir, "bin", "python"),
            os.path.join(venv_dir, "bin", "python3")
        ]
        pot_pip = [
            os.path.join(venv_dir, "Scripts", "pip.exe"),
            os.path.join(venv_dir, "bin", "pip.exe"),
            os.path.join(venv_dir, "bin", "pip"),
            os.path.join(venv_dir, "bin", "pip3")
        ]
        for p in pot_py:
            if os.path.exists(p):
                v_py = os.path.abspath(p)
                break
        for p in pot_pip:
            if os.path.exists(p):
                v_pip = os.path.abspath(p)
                break
        return v_py, v_pip

    venv_python, venv_pip = detect_venv_paths()

    # 2. Compatibility Check & Auto-Repair
    skip_check = "--skip-check-integrity" in sys.argv
    is_broken = False
    if venv_python and os.path.exists(venv_python) and not skip_check:
        try:
            # Check if cadquery is broken (common with 3.14/OCP)
            check_code = "import cadquery; print('CAD OK')"
            subprocess.check_output([venv_python, "-c", check_code], stderr=subprocess.STDOUT)
        except Exception as e:
            print(f"[!] Detected broken CAD environment: {e}")
            is_broken = True
    elif os.path.exists(venv_dir) and not venv_python:
        print("[!] Detected partial/broken virtual environment (No Python executable found).")
        is_broken = True

    if is_broken:
        print("[*] Attempting auto-repair (Purging venv)...")
        try:
            shutil.rmtree(venv_dir)
            venv_python = None
            venv_pip = None
        except Exception as e:
            print(f"[-] Auto-repair failed: {e}")
    elif skip_check:
        print("[*] Integrity check skipped by user flag.")

    # 3. Create VENV if it doesn't exist (or was purged)
    if not os.path.exists(venv_dir):
        target_python = sys.executable
        # Prefer 3.12/3.11 for CadQuery compatibility
        for cmd in ["python", "python3.12", "python3.11"]:
            try:
                ver_out = subprocess.check_output([cmd, "--version"], text=True)
                if "3.12" in ver_out or "3.11" in ver_out:
                    target_python = cmd
                    break
            except: continue
        
        print(f"[*] Creating self-healing GUI environment using {target_python}...")
        try:
            subprocess.check_call([target_python, "-m", "venv", venv_dir])
            # RE-DETECT paths after creation
            venv_python, venv_pip = detect_venv_paths()
        except Exception as e:
            print(f"[-] Fatal error creating venv: {e}")
            sys.exit(1)

    # 4. Check if we are already running in the venv
    if venv_python and sys.executable != os.path.abspath(venv_python):
        print("[*] Syncing dependencies with requirements.txt...")
        try:
            req_file = os.path.join(base_dir, "requirements.txt")
            if venv_pip:
                subprocess.check_call([venv_pip, "install", "-r", req_file])
                print("[+] Requirements synchronized.")
            else:
                print("[-] Warning: pip not found in venv. Skipping sync.")
        except Exception as e:
            print(f"[-] Warning: Dependency sync failed: {e}")

        print(f"[*] Restarting application inside fixed venv: {venv_python}")
        subprocess.call([venv_python, __file__])
        sys.exit(0)
    elif not venv_python:
        print("[-] Fatal: Virtual environment was created but Python executable is still missing.")
        sys.exit(1)

    # 5. Launch
    print("[*] Launching Baloon Shield Maker GUI...")
    try:
        from StellarOrionEngineMach5Up import Api
        import webview
        
        api = Api()
        web_index = os.path.join(base_dir, "web", "index.html")
        
        window = webview.create_window(
            "Baloon Shield Maker - StellarOrion Hypersonic Edition",
            web_index,
            js_api=api,
            width=1250,
            height=850,
            background_color="#0f172a"
        )
        api.set_window(window)
        webview.start(debug=False)
    except Exception as e:
        print(f"[-] Critical Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_and_launch()
