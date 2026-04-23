#!/usr/bin/env python
"""
SPARTA simulation runner – executed inside the Docker container.
- Builds SPARTA from source in an isolated directory (/tmp/sparta_build)
- Runs the simulation and writes output to the shared workspace.
"""

import ctypes
import os
import shutil
import subprocess
import sys
import argparse

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
    me = 0
    try:
        me = spa.world_rank()
    except:
        pass

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

    spa.command("clear")
    spa.close()


def main():
    parser = argparse.ArgumentParser(description="StellarOrion Simulation Runner")
    parser.add_argument("--optimize", action="store_true", help="Run the full survivability optimization loop")
    parser.add_argument("--test", type=str, choices=["sparta", "pyfluent", "pyansys", "baseline"], help="Run integration test (headless)")
    parser.add_argument("--samples", type=int, default=5, help="Number of samples for optimization")
    parser.add_argument("--goal", type=str, default="drag", help="Optimization goal (drag or heat)")
    parser.add_argument("--steps", type=int, default=1000, help="Number of simulation steps")
    parser.add_argument("--pinn", action="store_true", default=True, help="Enable PINN acceleration (Default)")
    parser.add_argument("--no-pinn", action="store_false", dest="pinn", help="Disable PINN acceleration")
    parser.add_argument("--sparta-gpu", action="store_true", default=False, help="Enable SPARTA GPU acceleration")

    parser.add_argument("--no-sparta-gpu", action="store_false", dest="sparta_gpu", help="Disable SPARTA GPU acceleration")

    
    # SSH Credentials for headless PyFluent testing
    parser.add_argument("--ssh-host", type=str, help="Remote host for PyFluent")
    parser.add_argument("--ssh-user", type=str, help="Remote user for PyFluent")
    parser.add_argument("--ssh-pass", type=str, help="Remote password for PyFluent")
    parser.add_argument("--ssh-key", type=str, help="Remote SSH key path for PyFluent")
    parser.add_argument("--chem", type=str, default="5-species", choices=["5-species", "11-species", "mars"], help="Chemistry model (5-species, 11-species, or mars)")
    parser.add_argument("--gettheirvebbaseline", action="store_true", help="Get the IRVE baseline parameter results simulation sample")
    parser.add_argument("--solver", type=str, default="sparta", choices=["sparta", "pyfluent", "pyansys"], help="Backend solver (sparta, pyfluent, or local pyansys)")
    parser.add_argument("--skip-diag", action="store_true", help="Skip slow initial diagnostics (e.g. GPU detection)")
    parser.add_argument("--headless", action="store_true", help="Run simulation in headless mode (no GUI)")
    
    args, unknown = parser.parse_known_args()

    if args.gettheirvebbaseline:
        print("[*] Fetching IRVE-3 Baseline Parameter Results...")
        from StellarOrionEngineMach5Up import Api
        # Use static method if possible or just call it
        baseline = Api.get_irve_baseline_results_static()
        import json
        print(json.dumps(baseline, indent=4))
        return

    if not os.environ.get("IN_DOCKER"):
        from StellarOrionEngineMach5Up import Api
        api = Api()

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
            elif args.test == "baseline":
                print("[*] Starting IRVE-3 Baseline Validation Simulation...")
                res = api.run_baseline_validation(solver=args.solver, skip_diag=args.skip_diag, headless=args.headless, sparta_gpu=args.sparta_gpu)
                print(f"[*] Validation Result: {res.get('status', 'unknown').upper()}")
                if res.get('status') == 'error':
                    print(f"[-] Error Message: {res.get('message', '')}")

                if 'comparison' in res:
                    print("\n[Comparison: Simulation vs Documentation]")
                    for k, v in res['comparison'].items():
                        print(f"  - {k}: Sim={v['sim']:.2f}, Doc={v['doc']:.2f}, Error={v['error_pct']:.1f}%")
                
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
                'solver': args.solver
            }
            
            print("[VERBOSE] Sending Optimization Parameters:")
            import json
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
