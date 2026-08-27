#!/usr/bin/env python
"""
SPARTA simulation runner – executed inside Docker container.
Builds SPARTA if needed (Linux native), then runs simulation.
"""

import ctypes
import os
import subprocess
import sys

CONTAINER_WORKDIR = "/workspace"


def build_sparta():
    """Build SPARTA shared library inside the container."""
    sparta_src = os.path.join(CONTAINER_WORKDIR, "sparta")
    build_dir = os.path.join(sparta_src, "build")
    lib_path = os.path.join(build_dir, "src", "libsparta.so")

    # If library exists and CMakeCache.txt is from Linux, skip rebuild
    if os.path.exists(lib_path):
        cache_file = os.path.join(build_dir, "CMakeCache.txt")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                if "CMAKE_SYSTEM_NAME:STRING=Linux" in f.read():
                    print(
                        "[*] SPARTA library already built for Linux. Skipping compilation."
                    )
                    return lib_path

    # Otherwise, clean and rebuild
    print("[*] Building SPARTA shared library for Linux...")
    if os.path.exists(build_dir):
        import shutil

        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    use_gpu = os.environ.get("SPARTA_GPU", "0") == "1"
    
    cmake_cmd = [
        "cmake",
        "../cmake",
        "-DSPARTA_LIB=yes",
        "-DSPARTA_SHARED_LIB=yes",
        "-DBUILD_LIB=ON",
        "-DBUILD_SHARED_LIBS=ON",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DPKG_KOKKOS=yes",
        "-DKokkos_ENABLE_OPENMP=yes",
        "-DPKG_PYTHON=yes",
        "-DPKG_MPI=no",
        "-DCMAKE_CXX_FLAGS=-D_Static_assert=static_assert",
    ]
    
    if use_gpu:
        print("[*] Enabling CUDA support in CMake...")
        cmake_cmd.extend([
            "-DKokkos_ENABLE_CUDA=yes",
            "-DKokkos_ARCH_NATIVE=ON"
        ])

    subprocess.run(cmake_cmd, cwd=build_dir, check=True)
    subprocess.run(
        ["make", "-j", os.environ.get("OMP_NUM_THREADS", "6")],
        cwd=build_dir,
        check=True,
    )

    if not os.path.exists(lib_path):
        raise RuntimeError(f"SPARTA library not found at {lib_path}")
    return lib_path


def run_simulation():
    # Build library
    lib_path = build_sparta()
    os.environ["SPARTA_LIB_PATH"] = lib_path

    # Setup Python path for wrapper
    sparta_python_dir = os.path.join(CONTAINER_WORKDIR, "sparta", "python")
    sys.path.insert(0, sparta_python_dir)

    print(f"[*] Loading SPARTA from {lib_path}")
    ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)

    from sparta import sparta

    # Initialize
    spa = sparta(cmdargs=["-log", "none"])
    version = spa.extract_setting("sparta_version")
    print(f"[*] SPARTA version {version} ready.")

    # ------------------------------------------------------------
    # YOUR SIMULATION COMMANDS GO HERE
    # Example:
    # spa.command("read_data input.data")
    # spa.command("run 1000")
    # ------------------------------------------------------------

    # Write output to mounted workspace
    workspace_dir = os.path.join(CONTAINER_WORKDIR, "workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    output_file = os.path.join(workspace_dir, "sparta_output.txt")
    with open(output_file, "w") as f:
        f.write(f"SPARTA version: {version}\n")
        f.write("Simulation completed.\n")

    print(f"[*] Output written to {output_file}")
    spa.close()


if __name__ == "__main__":
    run_simulation()
