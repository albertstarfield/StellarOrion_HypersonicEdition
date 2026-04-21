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

if os.environ.get("IN_DOCKER"):
    CONTAINER_WORKDIR = "/workspace"
else:
    CONTAINER_WORKDIR = os.path.dirname(os.path.abspath(__file__))

SPARTA_SRC = os.path.join(CONTAINER_WORKDIR, "sparta")
BUILD_DIR = os.path.join(CONTAINER_WORKDIR, "tmp_sparta_build")  # Isolated from host → no cross‑platform conflicts
LIB_PATH = os.path.join(BUILD_DIR, "src", "libsparta.so")
# For Mac compatibility, the shared library extension is .dylib
if sys.platform == "darwin":
    LIB_PATH = os.path.join(BUILD_DIR, "src", "libsparta.dylib")

WORKSPACE_OUTPUT = os.path.join(CONTAINER_WORKDIR, "workspace", "sparta_output.txt")


def build_sparta():
    """Build SPARTA shared library inside the container."""
    if os.path.exists(LIB_PATH):
        print("[*] SPARTA library already built. Skipping compilation.")
        return LIB_PATH

    print(
        "[*] Building SPARTA shared library (this will take several minutes)..."
    )
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    kokkos_omp = "yes" if sys.platform != "darwin" else "OFF"

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
    print(f"[*] Loading SPARTA from {lib_path}")
    ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)

    from sparta import sparta

    # 4. Initialize SPARTA
    spa = sparta(cmdargs=["-log", "none"])
    help(spa)
    print(f"[*] SPARTA is live.")

    # ------------------------------------------------------------
    # Run the HIAD reentry simulation
    # ------------------------------------------------------------
    original_dir = os.getcwd()
    hiad_dir = os.path.join(CONTAINER_WORKDIR, "CADDesign")
    print(f"[*] Changing to directory: {hiad_dir}")
    os.chdir(hiad_dir)

    # Copy species files so SPARTA finds them locally
    shutil.copy(os.path.join(SPARTA_SRC, "examples", "axi", "air.species"), "air.species")
    shutil.copy(os.path.join(SPARTA_SRC, "examples", "axi", "air.vss"), "air.vss")

    with open("in.hiad", "r") as f:
        full_command = ""
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Remove trailing comments
            line = line.split("#")[0].strip()
            if not line:
                continue

            if full_command:
                full_command += " " + line
            else:
                full_command = line

            if full_command.endswith("&"):
                full_command = full_command[:-1].strip()
                continue

            command = full_command
            full_command = ""

            if command:
                if steps and command.startswith("run "):
                    print(f"[*] Overriding: spa.command('run {steps}')")
                    spa.command(f"run {steps}")
                else:
                    print(f"[*] Executing: spa.command('{command}')")
                    spa.command(command)

    # ------------------------------------------------------------
    # End of simulation
    # ------------------------------------------------------------

    # 5. Write dummy output for demonstration
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
    parser.add_argument("--samples", type=int, default=5, help="Number of samples for optimization")
    parser.add_argument("--goal", type=str, default="drag", help="Optimization goal (drag or heat)")
    parser.add_argument("--steps", type=int, default=1000, help="Number of simulation steps")
    parser.add_argument("--pinn", action="store_true", default=True, help="Enable PINN acceleration (Default)")
    parser.add_argument("--no-pinn", action="store_false", dest="pinn", help="Disable PINN acceleration")
    args, unknown = parser.parse_known_args()

    if not os.environ.get("IN_DOCKER"):
        if args.optimize:
            print("[*] Optimization mode selected. Launching headless optimizer...")
            from StellarOrionEngineMach5Up import Api
            api = Api()
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
                'env_chem_mode': '5-species',
                'env_steady_state': False,
                'pinn_accel': args.pinn,
                'samples': args.samples,
                'goal': args.goal,
                'v_diameter': True,
                'v_angle': True,
                'v_toroids': True,
                'v_nose': True
            }
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
