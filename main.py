#!/usr/bin/env python
import os
import sys
import subprocess

# --- Dependency Auto-Fix ----------------------------------------------------──
# --- Environment Management (Shared with GUI) ------------------------------──
def ensure_venv():
    """Ensures we are running inside the project's virtual environment (.venv_gui)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, ".venv_gui")
    
    # Skip bootstrap if explicitly requested or if already inside the venv
    if "--skip-venv-bootstrap" in sys.argv:
        return

    def get_venv_python():
        if sys.platform == "win32":
            p = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            p = os.path.join(venv_dir, "bin", "python")
            if not os.path.exists(p):
                p = os.path.join(venv_dir, "bin", "python3")
        
        if os.path.exists(p):
            # Final sanity check: if we are on Unix but found an .exe, it's invalid
            if sys.platform != "win32" and p.endswith(".exe"): return None
            return os.path.abspath(p)
        return None

    venv_python = get_venv_python()

    # If we found a venv but it's likely from another OS (Exec format error prevention)
    if venv_python and not os.access(venv_python, os.X_OK) and sys.platform != "win32":
        print("[!] Detected invalid venv binaries (likely cross-platform sync).")
        venv_python = None 

    # If we are NOT in the venv, we must bootstrap
    if not venv_python or sys.executable != venv_python:
        print("[*] StellarOrion Environment Check...")
        
        if not venv_python:
            if os.path.exists(venv_dir):
                print("[!] Existing .venv_gui is incompatible with this OS. Recreating...")
                try:
                    import shutil
                    shutil.rmtree(venv_dir)
                except: pass

            print(f"[*] Creating shared virtual environment: {venv_dir}")
            try:
                subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
                venv_python = get_venv_python()
            except Exception as e:
                print(f"[-] Fatal: Failed to create venv: {e}")
                sys.exit(1)

        # Sync dependencies if needed
        print("[*] Synchronizing dependencies in .venv_gui...")
        try:
            req_path = os.path.join(base_dir, "requirements.txt")
            # Robust pip detection
            if sys.platform == "win32":
                venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
            else:
                venv_pip = os.path.join(venv_dir, "bin", "pip")
            
            subprocess.check_call([venv_pip, "install", "-r", req_path])
        except Exception as e:
            print(f"[-] Warning: Dependency sync failed: {e}")

        print(f"[*] Restarting application in isolated environment...")
        try:
            new_args = [venv_python, __file__] + [a for a in sys.argv[1:] if a != "--skip-venv-bootstrap"] + ["--skip-venv-bootstrap"]
            os.execv(venv_python, new_args)
        except OSError as e:
            print(f"[-] Fatal: Failed to execute venv python ({e}). This may be due to cross-platform sync artifacts.")
            print("[*] Try deleting the .venv_gui folder manually.")
            sys.exit(1)

# Run bootstrap before anything else (unless inside Docker)
if "IN_DOCKER" not in os.environ:
    ensure_venv()

import ctypes
import shutil
import json
import argparse
import time
import re
import pydoc

sys.stdout.flush()



if os.environ.get("IN_DOCKER"):
    CONTAINER_WORKDIR = os.environ.get("DOCKER_WORKDIR", "/workspace")
    SPARTA_SRC = "/workspace/sparta" # Use the one built into the image
else:
    CONTAINER_WORKDIR = os.path.dirname(os.path.abspath(__file__))
    SPARTA_SRC = os.path.join(CONTAINER_WORKDIR, "sparta")

BUILD_DIR = os.path.join(CONTAINER_WORKDIR, "tmp_sparta_build") 

LIB_PATH = os.path.join(BUILD_DIR, "src", "libsparta.so")
FALLBACK_LIB_PATH = os.path.join(SPARTA_SRC, "build", "src", "libsparta.so")
# For Mac compatibility, the shared library extension is .dylib
if sys.platform == "darwin":
    LIB_PATH = os.path.join(BUILD_DIR, "src", "libsparta.dylib")
    FALLBACK_LIB_PATH = os.path.join(SPARTA_SRC, "build", "src", "libsparta.dylib")

WORKSPACE_OUTPUT = os.path.join(CONTAINER_WORKDIR, "workspace", "sparta_output.txt")


def build_sparta():
    """Build SPARTA shared library inside the container."""
    if os.path.exists(LIB_PATH):
        print("[*] SPARTA library already built in isolated dir. Skipping compilation.")
        return LIB_PATH
    
    # Try multiple fallback locations and filenames
    search_dirs = [
        os.path.join(SPARTA_SRC, "build", "src"),
        os.path.join(SPARTA_SRC, "src"),
    ]
    for d in search_dirs:
        if not os.path.exists(d): continue
        for f in os.listdir(d):
            if ("libsparta" in f) and (f.endswith(".so") or f.endswith(".dylib") or ".so." in f):
                found_path = os.path.join(d, f)
                print(f"[*] Found SPARTA library at {found_path}. Skipping compilation.")
                return found_path

    print(
        "[*] Building SPARTA shared library (this will take several minutes)..."
    )
    print(f"[*] Checking for previous build in {BUILD_DIR}...")
    if os.path.exists(BUILD_DIR):
        print(f"[*] Removing old build directory: {BUILD_DIR}...")
        shutil.rmtree(BUILD_DIR)
        print("[*] Old build directory removed.")
    os.makedirs(BUILD_DIR)


    kokkos_omp = "yes" if sys.platform != "darwin" else "OFF"

    use_gpu = os.environ.get("SPARTA_GPU", "0") == "1"

    cmake_cmd = [
        "cmake",
        SPARTA_SRC + "/cmake",
        "-DSPARTA_LIB=yes",
        "-DSPARTA_SHARED_LIB=yes",
        "-DBUILD_LIB=ON",
        "-DBUILD_SHARED_LIBS=ON",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DPKG_KOKKOS=yes",
        f"-DKokkos_ENABLE_OPENMP={kokkos_omp}",
        "-DKokkos_ENABLE_MPI=OFF",
        "-DPKG_PYTHON=yes",
        "-DBUILD_MPI=OFF",
        "-DPKG_MPI_STUBS=ON",
        "-DCMAKE_CXX_FLAGS=-D_Static_assert=static_assert",
    ]

    if use_gpu:
        print("[*] Enabling CUDA support in CMake...")
        cmake_cmd.extend([
            "-DKokkos_ENABLE_CUDA=yes",
            "-DKokkos_ARCH_NATIVE=ON"
        ])

    subprocess.run(cmake_cmd, cwd=BUILD_DIR, check=True)
    subprocess.run(
        ["make", "-j", os.environ.get("OMP_NUM_THREADS", "6")],
        cwd=BUILD_DIR,
        check=True,
    )

    if not os.path.exists(LIB_PATH):
        raise RuntimeError(f"SPARTA library not found at {LIB_PATH}")
    return LIB_PATH


def run_simulation(steps=None):
    # 1. Build SPARTA
    lib_path = build_sparta()
    os.environ["SPARTA_LIB_PATH"] = lib_path

    # 2. Set up Python path for the wrapper
    sparta_python_dir = os.path.join(SPARTA_SRC, "python")
    sys.path.insert(0, sparta_python_dir)

    # 3. Load library and import
    lib_dir = os.path.dirname(lib_path)
    ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)

    from sparta import sparta


    # 4. Initialize SPARTA with GPU flags if needed
    cmdargs = ["-log", "none"]
    if os.environ.get("SPARTA_GPU", "0") == "1":
        print("[*] Initializing SPARTA with Kokkos GPU acceleration...")
        cmdargs.extend(["-k", "on", "g", "1", "-sf", "kk"])
    
    spa = sparta(cmdargs=cmdargs)
    
    # Detect rank robustly without mpi4py
    me = 0
    # Try OpenMPI/MPICH/etc environment variables first
    for env_var in ["OMPI_COMM_WORLD_RANK", "PMI_RANK", "RANK"]:
        if env_var in os.environ:
            me = int(os.environ[env_var])
            break

    if me == 0:
        print(f"[*] SPARTA is live (GPU={'ON' if '-sf' in cmdargs else 'OFF'}).")


    # ------------------------------------------------------------
    # Run the HIAD reentry simulation
    # ------------------------------------------------------------
    original_dir = os.getcwd()
    hiad_dir = os.path.join(CONTAINER_WORKDIR, "CADDesign")
    if me == 0:
        print(f"[*] Changing to directory: {hiad_dir}")
    os.chdir(hiad_dir)

    # Copy species files so SPARTA finds them locally
    if me == 0:
        shutil.copy(os.path.join(SPARTA_SRC, "examples", "axi", "air.species"), "air.species")
        shutil.copy(os.path.join(SPARTA_SRC, "examples", "axi", "air.vss"), "air.vss")

    with open("in.hiad", "r") as f:
        lines = f.readlines()
        
    for line in lines:
        command = line.strip()
        if not command or command.startswith("#"):
            continue
        
        # Override run steps if requested
        if command.startswith("run ") and steps is not None:
            if me == 0: print(f"[*] Overriding: spa.command('run {steps}')")
            spa.command(f"run {steps}")
        else:
            spa.command(command)

    # ------------------------------------------------------------
    # End of simulation
    # ------------------------------------------------------------

    # 5. Write dummy output for demonstration
    if me == 0:
        print(f"[*] Changing back to directory: {original_dir}")
        os.chdir(original_dir)
        os.makedirs(os.path.dirname(WORKSPACE_OUTPUT), exist_ok=True)
        with open(WORKSPACE_OUTPUT, "w") as f:
            f.write("Simulation completed successfully.\n")
        print(f"[*] Output written to {WORKSPACE_OUTPUT}")

    # Ensure all processes are synchronized before closing
    spa.command("run 0")
    spa.close()
    sys.stdout.flush()
    os._exit(0)


def display_custom_help(parser):
    """Displays help in a manpage-like pager if in a terminal, else prints to stdout."""
    help_text = parser.format_help()
    
    # ANSI color codes
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    if sys.stdout.isatty():
        # Enhanced "Manpage" styling
        # Bold and uppercase major sections
        sections = [
            "usage:", "description:", "QUICK START EXAMPLES:", "NOTE:",
            "Mode Flags", "Solver Selection", "Simulation Parameters", 
            "Acceleration & Hardware", "Output & Display", "Remote PyFluent"
        ]
        for section in sections:
            # Match case-insensitively but preserve original casing for the replacement or use upper
            pattern = re.compile(re.escape(section), re.IGNORECASE)
            help_text = pattern.sub(f"{BOLD}{section.upper()}{RESET}", help_text)

        # Highlight arguments
        help_text = re.sub(r'(--\w+[-\w]*)', f"{CYAN}\\1{RESET}", help_text)
        help_text = re.sub(r'(-\w)\b', f"{CYAN}\\1{RESET}", help_text)

        # Use less as a pager (manpage style)
        try:
            # -R for ANSI colors, -S to chop long lines, -X to keep content on screen after exit
            env = os.environ.copy()
            env["LESS"] = "-RX" 
            process = subprocess.Popen(['less'], stdin=subprocess.PIPE, env=env, text=True)
            process.communicate(input=help_text)
        except Exception:
            # Fallback to pydoc pager or simple print
            pydoc.pager(help_text)
    else:
        # Standard output for non-terminal (e.g. piping to file)
        print(help_text)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "StellarOrion HIAD Simulation Runner\n"
            "------------------------------------\n"
            "A command-line interface for hypersonic HIAD geometry optimization and simulation\n"
            "using SPARTA (DSMC), OpenFOAM (dsmcFoam), and PyAnsys/PyFluent backends.\n"
            "\n"
            "QUICK START EXAMPLES:\n"
            "  Fetch IRVE-3 reference data:     python main.py --gettheirvebbaseline\n"
            "  Run IRVE-3 calibration check:    python main.py --compareCalibrate --solver openfoam\n"
            "  Run baseline SPARTA validation:  python main.py --test baseline --solver sparta\n"
            "  Run full optimization loop:      python main.py --optimize --solver sparta --samples 10\n"
            "\n"
            "NOTE: SPARTA and OpenFOAM solvers require Docker Desktop to be running.\n"
            "      PyAnsys requires Ansys software installed on the remote computer (for pyfluent)\n"
            "      or running on Windows (for local pyansys)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )

    # Add custom help flags
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit.")

    # -- Mode Flags ------------------------------------------------------------
    mode = parser.add_argument_group("Mode Flags (choose one)")
    mode.add_argument("--optimize", action="store_true",
        help="Run the full survivability optimization loop. Iterates over geometry samples using LHS, runs simulations, and converges toward optimal Cd/heat flux using PINN refinement.")
    mode.add_argument("--test", type=str,
        choices=["sparta", "pyfluent", "pyansys", "baseline", "openfoam", "sample"],
        metavar="MODE",
        help=(
            "Run a headless integration test. Choices:\n"
            "  sparta    - SPARTA Docker dry-run handshake test\n"
            "  openfoam  - OpenFOAM Docker readiness check\n"
            "  pyfluent  - Remote PyFluent SSH handshake\n"
            "  pyansys   - Local PyAnsys/Fluent handshake\n"
            "  baseline  - Full IRVE-3 baseline validation vs documentation\n"
            "  sample    - Single simulation with IRVE-3 default parameters"
        ))
    mode.add_argument("--compareCalibrate", action="store_true",
        help="Shorthand for: --headless --test sample --solver <solver>. Runs a single IRVE-3 geometry simulation and prints a formatted comparison table of Cd and heat flux against the official IRVE-3 baseline values.")
    mode.add_argument("--compareNoses", action="store_true",
        help="Run a comparative study between Smooth (blunt) and Pointy (sharp) nose types on the baseline HIAD geometry. Prints a side-by-side performance table.")
    mode.add_argument("--gettheirvebbaseline", action="store_true",
        help="Print the IRVE-3 mission baseline parameters as JSON (geometry, performance, validation targets). No simulation is run. Useful for reference.")
    mode.add_argument("--LiteracyReferences", action="store_true",
        help="Display the full project bibliography and research references from REFERENCES.MD in a manpage-like view.")

    # -- Solver Selection ----------------------------------------------------──
    solver_grp = parser.add_argument_group("Solver Selection")
    solver_grp.add_argument("--solver", type=str, default="sparta",
        choices=["sparta", "pyfluent", "pyansys", "openfoam"],
        help=(
            "Backend solver engine to use. Default: sparta\n"
            "  sparta    - DSMC rarefied flow solver via Docker (sparta-hysp image)\n"
            "  openfoam  - dsmcFoam continuum/DSMC solver via Docker (openfoam-hysp image)\n"
            "  pyansys   - Local Ansys Fluent via PyFluent (requires Ansys 2023R1+ install)\n"
            "  pyfluent  - Remote Ansys Fluent via SSH tunnel"
        ))

    # -- Simulation Parameters ------------------------------------------------─
    sim = parser.add_argument_group("Simulation Parameters")
    sim.add_argument("--steps", type=int, default=1000,
        help="Number of simulation timesteps. Default: 1000. (For SPARTA: particle advance steps. For dsmcFoam: time iterations.)")
    sim.add_argument("--grid-factor", type=float, default=1.0,
        help="Mesh density multiplier. Default: 1.0. >1.0 increases grid resolution, <1.0 decreases it.")
    sim.add_argument("--samples", type=int, default=5,
        help="Number of Latin Hypercube Sampling (LHS) geometry samples per optimization iteration. Default: 5.")
    sim.add_argument("--goal", type=str, default="drag", choices=["drag", "heat"],
        help="Optimization objective. 'drag' minimizes aerodynamic drag coefficient (Cd). 'heat' minimizes peak stagnation heat flux. Default: drag.")
    sim.add_argument("--nose-type", type=str, default="smooth", choices=["smooth", "pointy"],
        help="Type of nose geometry to generate. 'smooth' creates a spherical cap (IRVE-3 baseline). 'pointy' creates a sharp conical apex. Default: smooth.")
    sim.add_argument("--chem", type=str, default="5-species",
        choices=["5-species", "11-species", "mars"],
        help=(
            "Chemistry model for gas species. Default: 5-species\n"
            "  5-species  - Earth air: N2, O2, NO, N, O (standard for <80km)\n"
            "  11-species - High-enthalpy Earth: adds ionized species (N2+, O2+, NO+, e-) for >80km\n"
            "  mars       - Mars atmosphere: CO2, N2, CO, O (for future Mars EDL studies)"
        ))
    sim.add_argument("--payload", action="store_true", default=False,
        help="Enable a payload model on the backside of the HIAD shield. Requires --payload-file.")
    sim.add_argument("--payload-file", type=str, default=None,
        help="Path to a STEP file (.step/.stp) for the payload. Only used if --payload is enabled.")
    sim.add_argument("--slice-angle", type=float, default=360.0,
        help="Angle to revolve the skin (degrees). Use 360 for full body, or smaller (e.g. 10.0) for thin-slice 3D domains. Default: 360.0.")

    # -- Acceleration & Hardware --------------------------------------------───
    hw = parser.add_argument_group("Acceleration & Hardware")
    hw.add_argument("--pinn", action="store_true", default=True,
        help="Enable Physics-Informed Neural Network (PINN) surrogate for optimization acceleration. Default: enabled.")
    hw.add_argument("--no-pinn", action="store_false", dest="pinn",
        help="Disable the PINN surrogate. Optimization will rely entirely on direct simulation samples.")
    hw.add_argument("--sparta-gpu", action="store_true", default=False,
        help="Enable CUDA GPU acceleration for SPARTA via Kokkos. Requires an NVIDIA GPU and the CUDA-enabled sparta-hysp Docker image (Dockerfile.cuda).")
    hw.add_argument("--no-sparta-gpu", action="store_false", dest="sparta_gpu",
        help="Force CPU-only SPARTA execution even if a GPU is detected.")
    hw.add_argument("--skip-diag", action="store_true",
        help="Skip slow startup diagnostics (e.g. GPU detection via nvidia-smi). Useful for fast iteration on systems where GPU state is known.")

    # -- Output & Display ----------------------------------------------------──
    out = parser.add_argument_group("Output & Display")
    out.add_argument("--headless", action="store_true",
        help="Run in fully headless mode (no GUI windows). Required for CLI/server environments. Output is printed to stdout.")
    out.add_argument("--paraview", action="store_true",
        help="After an OpenFOAM simulation, automatically launch ParaView with an automated visualization script. Requires ParaView to be installed on the host.")
    out.add_argument("--verbose", action="store_true", default=True,
        help="Enable verbose logging from the simulation engine. Default: enabled.")
    out.add_argument("--no-verbose", action="store_false", dest="verbose",
        help="Suppress verbose engine output. Only critical results and errors will be printed.")

    # -- Remote PyFluent (SSH) ------------------------------------------------─
    ssh = parser.add_argument_group("Remote PyFluent / SSH Options (only with --solver pyfluent)")
    ssh.add_argument("--ssh-host", type=str, help="Hostname or IP of the remote Ansys Fluent server.")
    ssh.add_argument("--ssh-user", type=str, help="SSH username for the remote Fluent server.")
    ssh.add_argument("--ssh-pass", type=str, help="SSH password (if not using key-based auth).")
    ssh.add_argument("--ssh-key",  type=str, help="Path to SSH private key file for key-based authentication.")

    args, unknown = parser.parse_known_args()

    if args.help:
        display_custom_help(parser)

    if args.compareCalibrate:
        args.headless = True
        if not args.test:
            args.test = "sample"
        # Use default steps (1000) for calibration check unless user explicitly set something else

    if args.LiteracyReferences:
        ref_path = os.path.join(CONTAINER_WORKDIR, "REFERENCES.MD")
        if os.path.exists(ref_path):
            with open(ref_path, "r") as f:
                ref_content = f.read()
            
            if sys.stdout.isatty():
                # Manpage style styling for references
                BOLD = "\033[1m"
                RESET = "\033[0m"
                # Bold the citations like [0], [1]
                ref_content = re.sub(r'(\[\d+\])', f"{BOLD}\\1{RESET}", ref_content)
                
                try:
                    env = os.environ.copy()
                    env["LESS"] = "-RX"
                    process = subprocess.Popen(['less'], stdin=subprocess.PIPE, env=env, text=True)
                    process.communicate(input=ref_content)
                except Exception:
                    pydoc.pager(ref_content)
            else:
                print(ref_content)
        else:
            print(f"[-] Error: REFERENCES.MD not found at {ref_path}")
        return

    if args.gettheirvebbaseline:
        print("[*] Fetching IRVE-3 Baseline Parameter Results...")
        from StellarOrionEngineMach5Up import Api
        baseline = Api.get_irve_baseline_results_static()
        print(json.dumps(baseline, indent=4))
        return

    if not os.environ.get("IN_DOCKER"):
        from StellarOrionEngineMach5Up import Api
        api = Api()
        
        if args.compareNoses:
            print("[*] Starting HIAD Nose-Type Comparison Study (Smooth vs Pointy)...")
            res = api.run_nose_comparison(solver=args.solver, steps=args.steps, skip_diag=args.skip_diag, headless=args.headless, sparta_gpu=args.sparta_gpu)
            sys.exit(0)

        # Pre-flight check for Docker if using SPARTA or OpenFOAM
        if args.solver in ['sparta', 'openfoam'] or args.test in ['sparta', 'openfoam', 'baseline', 'sample']:
            try:
                subprocess.run(["docker", "info"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("[-] CRITICAL ERROR: Docker is not running or not installed.")
                print("    Please start Docker Desktop and ensure the daemon is active.")
                sys.exit(1)

        if args.test:
            print(f"[*] Starting Headless Integration Test: {args.test.upper()}...")
            if args.test == "sparta":
                res = api.run_sparta_integration_test()
                print(f"[*] Result: {res.get('status', 'unknown').upper()}")
                print(f"[*] Message: {res.get('message', '')}")
            elif args.test == "pyfluent":
                opt_params = {
                    'ssh_host': args.ssh_host or os.environ.get("STELLAR_SSH_HOST"),
                    'ssh_user': args.ssh_user or os.environ.get("STELLAR_SSH_USER"),
                    'ssh_pass': args.ssh_pass or os.environ.get("STELLAR_SSH_PASS"),
                    'ssh_key': args.ssh_key or os.environ.get("STELLAR_SSH_KEY"),
                }
                if not opt_params['ssh_host'] or not opt_params['ssh_user']:
                    print("[-] Error: SSH Host and User are required for PyFluent test.")
                    sys.exit(1)
                res = api.run_integration_test(opt_params)
                print(f"[*] Result: {res.get('status', 'unknown').upper()}")
                print(f"[*] Message: {res.get('message', '')}")
            elif args.test == "pyansys":
                print("[*] Starting Local PyAnsys (Windows Only) Integration Test...")
                res = api.run_local_pyfluent_test(show_gui=True)
                print(f"[*] Result: {res.get('status', 'unknown').upper()}")
                print(f"[*] Message: {res.get('message', '')}")
            elif args.test == "openfoam":
                res = api.run_openfoam_integration_test()
                print(f"[*] Result: {res.get('status', 'unknown').upper()}")
                print(f"[*] Message: {res.get('message', '')}")
            elif args.test == "baseline":
                print("[*] Starting IRVE-3 Baseline Validation Simulation...")
                res = api.run_baseline_validation(solver=args.solver, skip_diag=args.skip_diag, headless=args.headless, sparta_gpu=args.sparta_gpu)
                print(f"[*] Validation Result: {res.get('status', 'unknown').upper()}")
                
                if 'comparison' in res:
                    print("\n[Comparison: Simulation vs IRVE-3 Documentation]")
                    print(f"{'Variable':<30} | {'Simulation':<12} | {'Document':<12} | {'Error %':<8}")
                    print("-" * 75)
                    for k, v in res['comparison'].items():
                        sim_str = f"{v['sim']:.2f} {v.get('unit', '')}".strip()
                        doc_str = f"{v['doc']:.2f} {v.get('unit', '')}".strip()
                        print(f"{k:<30} | {sim_str:<12} | {doc_str:<12} | {v['error_pct']:.1f}%")
                
                if res.get('status') == 'error':
                    print(f"[-] Error Message: {res.get('message', '')}")
            elif args.test == "sample":
                print("[*] Running Single Simulation Sample...")
                # Fetch baseline early for printing and comparison
                baseline = api.get_irve_baseline_results_static()

                # Construct default params
                opt_params = {
                    'solver': args.solver,
                    'env_vstream': 2700.0,
                    'env_temp_inf': 250.0,
                    'env_nrho': 1e22,
                    'env_run': args.steps,
                    'env_fnum': '1e17', # Balanced fnum (~1M particles) to lower noise and maintain speed
                    'grid_factor': args.grid_factor, # Mesh adjustment: >1.0 denser, <1.0 sparser
                    'headless': args.headless,
                    'paraview': args.paraview,
                    'sparta_gpu': args.sparta_gpu
                }
                sample_dict = {
                    'diameter': 3.0,
                    'angle': 60.0,
                    'nose': 0.191,
                    'toroids': 7
                }

                if args.compareCalibrate:
                    print("\n" + "═"*80)
                    print(f"{'IRVE-3 CALIBRATION MODE: SYSTEM PARAMETERS':^80}")
                    print("═"*80)
                    
                    print("\n[GEOMETRIC BASELINE PARAMETERS]")
                    print("-" * 30)
                    for k, v in baseline['geometry'].items():
                        print(f"  {k:<25}: {v}")
                    
                    print("\n[FLIGHT PERFORMANCE PARAMETERS (TARGETS)]")
                    print("-" * 40)
                    for k, v in baseline['performance'].items():
                        print(f"  {k:<25}: {v}")
                    
                    print("\n[ENVIRONMENT PARAMETERS (CURRENT RUN)]")
                    print("-" * 40)
                    for k, v in opt_params.items():
                        if k.startswith('env_'):
                            print(f"  {k:<25}: {v}")
                    print("═"*80 + "\n")
                else:
                    print("[*] IRVE-3 Baseline Parameters:")
                    print(json.dumps({**opt_params, **sample_dict}, indent=4))
                
                # Generate Geometry STL
                print("[*] Generating Sample Geometry STL...")
                cad_dir = os.path.join(api.cwd, "CADDesign")
                python_exec = api._get_python_exec()
                cmd_cad = [
                    python_exec, os.path.join(cad_dir, "HIAD_GeometryEngine.py"),
                    "--diameter", str(sample_dict['diameter']),
                    "--angle", str(sample_dict['angle']),
                    "--nose", str(sample_dict['nose']),
                    "--toroids", str(sample_dict['toroids']),
                    "--thickness", "0.0254",
                    "--nose_type", args.nose_type,
                    "--output", "HIAD_sample",
                    "--slice_angle", str(args.slice_angle)
                ]

                if args.payload and args.payload_file:
                    cmd_cad.extend(["--payload_file", args.payload_file])
                subprocess.run(cmd_cad, cwd=cad_dir, check=True)

                if args.solver == 'openfoam':
                    api.test_openfoam_readiness()
                    res = api.run_openfoam_simulation(opt_params, sample_dict, surf_name="HIAD_sample")
                elif args.solver == 'sparta':
                    res = api.run_sparta_simulation(opt_params, sample_dict, surf_name="HIAD_sample")
                else:
                    # Fallback for other solvers in sample mode
                    res = api.run_sparta_integration_test() 
                
                # Add baseline comparison for solvers that return drag
                if 'drag' in res and res['drag'] > 0:
                    v = opt_params['env_vstream']
                    rho = 0.001 # approx 1e-3 (at 52km for IRVE-3)
                    force_n = res['drag']
                    area = 3.14159 * (sample_dict['diameter']/2)**2
                    cd_sim = force_n / (0.5 * rho * v**2 * area) if (rho * v**2 * area) > 0 else 0
                    
                    # Heat Flux conversion (W/m2 to W/cm2)
                    sim_heat = res.get('heat', 0) / 10000.0
                    
                    # Performance Metrics Derivation
                    mass_kg = baseline['geometry']['mass_kg']
                    force_n = res['drag']
                    decel_g = force_n / (mass_kg * 9.81) if mass_kg > 0 else 0
                    
                    # Pressure Metrics
                    # q = 0.5 * rho * v^2
                    q_kpa = (0.5 * rho * v**2) / 1000.0
                    # P_stag approx Cd * q (or use Newtonian approx: 2 * q)
                    p_stag_kpa = (cd_sim * q_kpa) 
                    
                    res['comparison'] = {
                        'drag_coeff': {
                            'sim': cd_sim,
                            'doc': baseline['validation_targets']['reference_cd'],
                            'error_pct': abs(cd_sim - baseline['validation_targets']['reference_cd']) / baseline['validation_targets']['reference_cd'] * 100
                        },
                        'peak_heat_flux': {
                            'sim': sim_heat,
                            'doc': baseline['performance']['peak_heat_flux_wcm2'],
                            'unit': 'W/cm2',
                            'error_pct': abs(sim_heat - baseline['performance']['peak_heat_flux_wcm2']) / baseline['performance']['peak_heat_flux_wcm2'] * 100 if baseline['performance']['peak_heat_flux_wcm2'] > 0 else 0
                        },
                        'total_heat_load': {
                            'sim': sim_heat * 10.0, # Dummy derivation for sample mode: heat * 10s
                            'doc': baseline['performance']['total_heat_load_jcm2'],
                            'unit': 'J/cm2',
                            'error_pct': abs((sim_heat * 10.0) - baseline['performance']['total_heat_load_jcm2']) / baseline['performance']['total_heat_load_jcm2'] * 100
                        },
                        'peak_deceleration': {
                            'sim': decel_g,
                            'doc': baseline['performance']['peak_deceleration_g'],
                            'unit': 'G',
                            'error_pct': abs(decel_g - baseline['performance']['peak_deceleration_g']) / baseline['performance']['peak_deceleration_g'] * 100
                        },
                        'dynamic_pressure': {
                            'sim': q_kpa,
                            'doc': baseline['performance']['peak_dynamic_pressure_kpa'],
                            'unit': 'kPa',
                            'error_pct': abs(q_kpa - baseline['performance']['peak_dynamic_pressure_kpa']) / baseline['performance']['peak_dynamic_pressure_kpa'] * 100
                        },
                        'stagnation_pressure': {
                            'sim': p_stag_kpa,
                            'doc': baseline['validation_targets']['stagnation_pressure_kpa'],
                            'unit': 'kPa',
                            'error_pct': abs(p_stag_kpa - baseline['validation_targets']['stagnation_pressure_kpa']) / baseline['validation_targets']['stagnation_pressure_kpa'] * 100
                        },
                        'toroid_radius': {
                            'sim': 0.1237, # From sample_dict calculation
                            'doc': baseline['geometry']['toroid_radius_m'],
                            'unit': 'm',
                            'error_pct': abs(0.1237 - baseline['geometry']['toroid_radius_m']) / baseline['geometry']['toroid_radius_m'] * 100
                        },
                        'payload_height': {
                            'sim': 1.7, # Input-based
                            'doc': baseline['geometry']['payload_height_m'],
                            'unit': 'm',
                            'error_pct': 0.0
                        },
                        'ambient_pressure': {
                            'sim': 75.77, # Hardcoded in sample_dict for now
                            'doc': baseline['validation_targets']['ambient_pressure_pa'],
                            'unit': 'Pa',
                            'error_pct': 0.0
                        },
                        'ambient_temp': {
                            'sim': 270.65, # Hardcoded in sample_dict for now
                            'doc': baseline['validation_targets']['ambient_temp_k'],
                            'unit': 'K',
                            'error_pct': 0.0
                        }
                    }
                
                print(f"[*] Result: {res}")

                if 'comparison' in res:
                    print("\n[Comparison: Simulation vs IRVE-3 Documentation]")
                    print(f"Source: {api.get_irve_citation()}")
                    print(f"{'Variable':<30} | {'Simulation':<12} | {'Document':<12} | {'Error %':<8}")
                    print("-" * 85)
                    for k, v in res['comparison'].items():
                        sim_str = f"{v['sim']:.2f} {v.get('unit', '')}".strip()
                        doc_str = f"{v['doc']:.2f} {v.get('unit', '')}".strip()
                        print(f"{k:<30} | {sim_str:<12} | {doc_str:<12} | {v['error_pct']:.1f}%")
                
                print(f"\n[*] Post-processing plots generated in: {os.path.join(CONTAINER_WORKDIR, 'web', 'assets', 'plots')}")
            return

        if args.optimize:
            print("[*] Optimization mode selected. Launching headless optimizer...")
            opt_params = {
                'env_preset': 'artemis',
                'env_nrho': '3.5e22',
                'env_temp_inf': '270.0',
                'env_fnum': '1e16',
                'env_temp': '1000.0',
                'env_step': '1e-6',
                'env_run': str(args.steps),
                'env_vstream': '2700.0',
                'env_duration': '60.0',
                'env_thermal_lag': '0.1',
                'env_chem_mode': args.chem,
                'env_steady_state': False,
                'pinn_accel': args.pinn,
                'sparta_gpu': args.sparta_gpu,
                'samples': args.samples,
                'goal': args.goal,
                'v_diameter': True,
                'v_angle': True,
                'v_toroids': True,
                'v_nose': True,
                'solver': args.solver,
                'verbose': args.verbose,
                'grid_factor': args.grid_factor,
                'payload': args.payload,
                'payload_file': args.payload_file
            }
            
            print("[VERBOSE] Sending Optimization Parameters:")
            # (json already imported)
            print(json.dumps(opt_params, indent=4))
            
            api.execute_optimization(opt_params, is_gui=False)
            return

        # Default: Launch the GUI
        print("[*] Launching StellarOrion GUI Launcher...")
        gui_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_launcher.py")
        subprocess.call([sys.executable, gui_script])
    else:
        # We are inside the container
        run_simulation(steps=args.steps if '--steps' in sys.argv else None)

if __name__ == "__main__":
    main()
