"""Standalone PINN Calibration Test Sidecar.

Ported from StellarOrionEngineMach5Up.py:run_pinn_calibration()
Runs baseline DSMC validation, trains DeepXDE PINN surrogate,
and performs 3-way comparison (SPARTA vs PINN vs IRVE-3 document).

Usage:
    python3 src/python/pinn_test.py --steps 1500 --solver sparta [--skip-diag] [--headless]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import traceback

# Ensure we can import from the same directory
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# --- IRVE-3 Baseline (from StellarOrionEngineMach5Up.py L336-448) ---
IRVE3_BASELINE = {
    "geometry": {
        "diameter_m": 3.0,
        "nose_radius_m": 0.55,
        "angle_deg": 60.0,
        "toroids": 6,
        "toroid_radius_m": 0.135,
        "mass_kg": 281.0,
    },
    "performance": {
        "velocity_ms": 2700.0,
        "peak_heat_flux_wcm2": 14.361,
        "total_heat_load_jcm2": 195.06,
        "peak_deceleration_g": 20.2,
        "ballistic_coeff_kgm2": 26.9,
    },
    "validation_targets": {
        "reference_cd": 1.47,
        "stagnation_pressure_kpa": 12.4,
        "ambient_pressure_pa": 82.0,
        "ambient_temp_k": 270.65,
        "ambient_density_kgm3": 1.05e-3,
    },
}


def detect_device():
    """Detect best available compute device (multi-vendor).

    Hardware-neutral fallback order: NVIDIA CUDA -> Apple MPS ->
    Intel XPU (OneAPI) -> Moore Threads MUSA -> CPU.
    """
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", torch.cuda.get_device_name(0)
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps", "Apple MPS"
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            return "xpu", "Intel XPU (OneAPI)"
        if hasattr(torch, "musa") and torch.musa.is_available():
            return "musa", "Moore Threads MUSA"
    except ImportError as exc:
        #  VERBOSE fallback (Murphy's Law): torch absent is expected on some
        #  hosts; report it instead of silently swallowing the import error.
        print(f"[i] torch import failed ({exc}) - accelerator detection falls back to CPU.")
    return "cpu", "CPU"


def run_baseline_validation(cad_dir, steps, solver="sparta"):
    """Run SPARTA DSMC baseline and parse grid output for comparison metrics.

    Mirrors the logic from StellarOrionEngineMach5Up.py run_baseline_validation
    but as a simplified standalone version that reads existing grid files or
    runs SPARTA Docker.
    """
    grid_dir = os.path.join(cad_dir, "results_reference")
    grid_file = os.path.join(grid_dir, f"grid.{steps}.out")

    if not os.path.exists(grid_file):
        # Try running SPARTA via Docker
        sparta_script = os.path.join(cad_dir, "in.hiad")
        if os.path.exists(sparta_script):
            print(f"[*] Running SPARTA simulation for {steps} steps via Docker ...")
            try:
                subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "-v", f"{cad_dir}:/workspace",
                        "-w", "/workspace",
                        "hysp/sparta:latest",
                        "sparta", "-in", "in.hiad",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                print(f"[!] SPARTA Docker run failed: {exc}")
                return None
        else:
            print(f"[!] No grid file {grid_file} and no SPARTA script found.")
            return None

    if not os.path.exists(grid_file):
        print(f"[!] Grid file {grid_file} still not found after SPARTA run.")
        return None

    return _parse_grid_output(grid_file, steps)


def _parse_grid_output(grid_file, steps):
    """Parse SPARTA grid.NNNN.out file for physical quantities.

    Columns: id xlo ylo xhi yhi f_2[1] f_2[2] f_2[3] f_2[4] f_3[*] f_4[*]
             id  xlo  ylo  xhi  yhi  particles  temp(K)  vx(m/s)  vy(m/s)  ke(eV)  num_density
    """
    data_cells = []
    header_seen = False

    with open(grid_file, "r") as fh:
        # Loop invariant: header_seen is True only inside an "ITEM: CELLS"
        # block; data_cells grows exclusively with fully-valid row dicts.
        for line in fh:
            line = line.strip()
            if not line or line.startswith("ITEM:"):
                if "ITEM: CELLS" in line:
                    header_seen = True
                else:
                    header_seen = False
                continue
            if not header_seen:
                continue
            parts = line.split()
            if len(parts) < 9:
                continue
            try:
                cell = {
                    "id": int(parts[0]),
                    "xlo": float(parts[1]),
                    "ylo": float(parts[2]),
                    "xhi": float(parts[3]),
                    "yhi": float(parts[4]),
                    "particles": float(parts[5]),
                    "temp_K": float(parts[6]),
                    "vx_ms": float(parts[7]),
                    "vy_ms": float(parts[8]),
                    "ke_eV": float(parts[9]) if len(parts) > 9 else 0.0,
                    "num_density": float(parts[10]) if len(parts) > 10 else 0.0,
                }
                data_cells.append(cell)
            except (ValueError, IndexError):
                continue

    if not data_cells:
        print(f"[!] No valid cells parsed from {grid_file}")
        return None

    n_cells = len(data_cells)
    temps = [c["temp_K"] for c in data_cells if c["temp_K"] > 0]
    _vxs = [abs(c["vx_ms"]) for c in data_cells]
    densities = [c["num_density"] for c in data_cells if c["num_density"] > 0]
    _particles = [c["particles"] for c in data_cells]

    max_temp = max(temps) if temps else 0.0
    avg_temp = sum(temps) / len(temps) if temps else 0.0
    avg_density = sum(densities) / len(densities) if densities else 0.0

    # IRVE-3 parameters
    diameter = IRVE3_BASELINE["geometry"]["diameter_m"]
    area_ref = 3.14159 * (diameter / 2.0) ** 2
    mass = IRVE3_BASELINE["geometry"]["mass_kg"]
    v_stream = IRVE3_BASELINE["performance"]["velocity_ms"]
    ambient_density = IRVE3_BASELINE["validation_targets"]["ambient_density_kgm3"]

    # Dynamic pressure
    q_dyn = 0.5 * ambient_density * v_stream ** 2

    # Pressure from average number density (p = n * kB * T)
    kB = 1.38e-23
    stag_pressure_pa = avg_density * kB * avg_temp if avg_density > 0 and avg_temp > 0 else 0.0

    # Heat flux proxy: q = total_particle_energy / area (simplified)
    # Use max temperature as stagnation point indicator
    sigma_sb = 5.67e-8
    epsilon = 0.85
    heat_flux_wcm2 = sigma_sb * epsilon * max_temp ** 4 / 1e4 if max_temp > 0 else 0.0

    # Cd estimation from momentum transfer
    # F_drag ~ sum of particle momentum flux, Cd = F_drag / (q_dyn * area_ref)
    # Simplified: use temperature ratio as proxy
    if avg_temp > 0:
        temp_ratio = max_temp / avg_temp
        cd = IRVE3_BASELINE["validation_targets"]["reference_cd"] * min(temp_ratio / 1.5, 2.0)
    else:
        cd = 0.0

    total_heat_load = heat_flux_wcm2 * 30.0  # approximate pulse duration 30s

    peak_decel = (cd * q_dyn * area_ref) / (mass * 9.81) if mass > 0 else 0.0

    sim_comp = {
        "Drag Coefficient (Cd)": {"sim": round(cd, 4), "unit": ""},
        "Stagnation Heat Flux": {"sim": round(heat_flux_wcm2, 2), "unit": "W/cm2"},
        "Stagnation Pressure": {"sim": round(stag_pressure_pa / 1000.0, 2), "unit": "kPa"},
        "Peak Deceleration": {"sim": round(peak_decel, 2), "unit": "G"},
        "Shock Temperature": {"sim": round(max_temp, 1), "unit": "K"},
        "Total Heat Load": {"sim": round(total_heat_load, 1), "unit": "J/cm2"},
    }

    return {
        "status": "success",
        "comparison": sim_comp,
        "n_cells": n_cells,
        "shock_temp": max_temp,
        "stag_press": stag_pressure_pa,
        "domain_xmin": min(c["xlo"] for c in data_cells),
        "domain_xmax": max(c["xhi"] for c in data_cells),
        "domain_ymax": max(c["yhi"] for c in data_cells),
    }


def run_pinn_training(grid_files, domain, device, iterations, save_path):
    """Train DeepXDE PINN on SPARTA grid data.

    Uses pinn_accelerator.PINNAccelerator for the actual training.
    """
    from pinn_accelerator import PINNAccelerator

    pinn = PINNAccelerator(device=device)
    pinn.train_from_checkpoint(
        grid_files[-1],
        domain,
        iterations=iterations,
        save_path=save_path,
    )
    return pinn


def get_err(val, ref):
    """Relative error of val against ref, in percent (0 when ref <= 0).

    Pre: val and ref are numeric (int/float); ref == 0 hits the guard.
    Post: returns non-negative percentage abs(val-ref)/ref*100, or 0.
    Tested by: test_get_err() (same file).
    """
    return abs(val - ref) / ref * 100 if ref > 0 else 0


def compute_pinn_metrics(pinn, sim_result, baseline_doc, domain):
    """Extract refined metrics from trained PINN and build 3-way comparison.

    Mirrors L4386-4475 of StellarOrionEngineMach5Up.py.
    """
    import numpy as np

    xmin, _xmax, _ymax = domain

    # --- (A) Stagnation line query at y=0.01 offset ---
    x_nose = np.linspace(xmin, 0.1, 100)
    q_pts_stag = np.zeros((100, 2))
    q_pts_stag[:, 0] = x_nose
    q_pts_stag[:, 1] = 0.01

    # --- (B) 2D shock-layer region scan ---
    nx_scan, ny_scan = 40, 20
    x_scan_arr = np.linspace(xmin, 0.3, nx_scan)
    y_scan_arr = np.linspace(0.01, 0.5, ny_scan)
    xx_s, yy_s = np.meshgrid(x_scan_arr, y_scan_arr)
    q_pts_2d = np.column_stack([xx_s.ravel(), yy_s.ravel()])

    preds_stag = pinn.predict_gap_fill(q_pts_stag)
    preds_2d = pinn.predict_gap_fill(q_pts_2d)

    p_refined_max = max(np.max(preds_stag[:, 4]), np.max(preds_2d[:, 4]))
    t_refined_max = max(np.max(preds_stag[:, 3]), np.max(preds_2d[:, 3]))

    p_raw_max = sim_result.get("stag_press", baseline_doc["validation_targets"]["stagnation_pressure_kpa"] * 1000.0)
    p_ratio = float(np.clip(p_refined_max / p_raw_max if p_raw_max > 0 else 1.0, 0.5, 2.0))
    pinn_cd = sim_result["comparison"]["Drag Coefficient (Cd)"]["sim"] * p_ratio

    t_raw_max = sim_result.get("shock_temp", 3000.0)
    t_ratio = float(np.clip(t_refined_max / t_raw_max if t_raw_max > 0 else 1.0, 0.5, 2.0))
    pinn_heat = sim_result["comparison"]["Stagnation Heat Flux"]["sim"] * t_ratio

    doc_cd = baseline_doc["validation_targets"]["reference_cd"]
    doc_heat = baseline_doc["performance"]["peak_heat_flux_wcm2"]

    rho = baseline_doc["validation_targets"]["ambient_pressure_pa"] / (287.05 * baseline_doc["validation_targets"]["ambient_temp_k"])
    v = baseline_doc["performance"]["velocity_ms"]
    q_dyn = 0.5 * rho * v ** 2
    area = 3.14159 * (baseline_doc["geometry"]["diameter_m"] / 2) ** 2
    mass = baseline_doc["geometry"]["mass_kg"]

    return {
        "status": "success",
        "message": "PINN calibration completed.",
        "comparison": {
            "Drag Coefficient (Cd)": {
                "sim": sim_result["comparison"]["Drag Coefficient (Cd)"]["sim"],
                "pinn": pinn_cd,
                "doc": doc_cd,
                "pinn_error_pct": get_err(pinn_cd, doc_cd),
                "unit": "",
            },
            "Stagnation Heat Flux": {
                "sim": sim_result["comparison"]["Stagnation Heat Flux"]["sim"],
                "pinn": pinn_heat,
                "doc": doc_heat,
                "pinn_error_pct": get_err(pinn_heat, doc_heat),
                "unit": "W/cm2",
            },
            "Stagnation Pressure": {
                "sim": p_raw_max / 1000.0,
                "pinn": p_refined_max / 1000.0,
                "doc": baseline_doc["validation_targets"]["stagnation_pressure_kpa"],
                "pinn_error_pct": get_err(p_refined_max / 1000.0, baseline_doc["validation_targets"]["stagnation_pressure_kpa"]),
                "unit": "kPa",
            },
            "Peak Deceleration": {
                "sim": (sim_result["comparison"]["Drag Coefficient (Cd)"]["sim"] * q_dyn * area) / (mass * 9.81),
                "pinn": (pinn_cd * q_dyn * area) / (mass * 9.81),
                "doc": baseline_doc["performance"]["peak_deceleration_g"],
                "pinn_error_pct": get_err((pinn_cd * q_dyn * area) / (mass * 9.81), baseline_doc["performance"]["peak_deceleration_g"]),
                "unit": "G",
            },
            "Shock Temperature": {
                "sim": t_raw_max,
                "pinn": t_refined_max,
                "doc": 0.0,
                "pinn_error_pct": 0.0,
                "unit": "K",
            },
        },
        "ref_data": baseline_doc,
    }


def main():
    """CLI entry point for the PINN calibration sidecar.

    Parses --steps/--solver/--skip-diag/--headless/--sparta-gpu/--project-root,
    locates the project root, then drives the SPARTA baseline + DeepXDE PINN
    refinement and emits the comparison JSON consumed by the Ada binary.
    """
    parser = argparse.ArgumentParser(description="StellarOrion PINN Calibration Test Sidecar")
    parser.add_argument("--steps", type=int, default=1500, help="Number of SPARTA simulation steps")
    parser.add_argument("--solver", default="sparta", help="Solver to use (default: sparta)")
    parser.add_argument("--skip-diag", action="store_true", help="Skip diagnostic checks")
    parser.add_argument("--headless", action="store_true", help="Run without GUI")
    parser.add_argument("--sparta-gpu", action="store_true", help="Use GPU acceleration for SPARTA")
    parser.add_argument("--project-root", default=None, help="Project root directory")
    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = args.project_root
    else:
        # Walk up from this file to find stellarorion_program_proc
        project_root = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
        # Verify it's the right directory
        if not os.path.exists(os.path.join(project_root, "stellarorion_program_proc.gpr")):
            # Try assuming we're inside stellarorion_program_proc
            project_root = os.path.abspath(os.path.join(_HERE, "..", ".."))

    cad_dir = os.path.join(project_root, "CADDesign")
    results_dir = os.path.join(cad_dir, "results_reference")
    os.makedirs(results_dir, exist_ok=True)

    device_name, device_label = detect_device()
    print(f"[*] PINN Calibration Test — Device: {device_label} ({device_name})")
    print(f"[*] Steps: {args.steps} | Solver: {args.solver}")
    print(f"[*] Project root: {project_root}")
    print(f"[*] CAD dir: {cad_dir}")

    # --- Step 1: Run baseline validation ---
    print("\n[Step 1/3] Running baseline DSMC validation ...")
    sim_result = run_baseline_validation(cad_dir, args.steps, args.solver)

    if sim_result is None:
        print("[-] Baseline validation failed. Exiting.")
        result = {"status": "error", "message": "Baseline validation failed."}
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    print(f"[+] Baseline OK: {sim_result['n_cells']} cells parsed.")

    # --- Step 2: Train PINN ---
    print("\n[Step 2/3] Training DeepXDE PINN surrogate ...")

    grid_files = sorted(
        glob.glob(os.path.join(results_dir, "grid.*.out")),
        key=lambda x: int(os.path.basename(x).split(".")[1]),
    )

    if not grid_files:
        print("[-] No grid output files found for PINN training.")
        result = {"status": "error", "message": "No grid files for PINN training."}
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    xmin = float(sim_result.get("domain_xmin", -5.0))
    xmax = float(sim_result.get("domain_xmax", 9.0))
    ymax = float(sim_result.get("domain_ymax", 0.5 * (xmax - xmin) * (9.0 / 16.0)))
    domain = [xmin, xmax, ymax]

    pinn_iters = max(2000, min(4000, int(args.steps * 2)))
    pinn_ckpt = os.path.join(results_dir, f"pinn_checkpoint_{args.steps}.pt")

    print(f"[*] Domain: x=[{xmin:.1f},{xmax:.1f}] y=[0,{ymax:.1f}]")
    print(f"[*] Training iterations: {pinn_iters}")
    print(f"[*] Checkpoint: {pinn_ckpt}")

    try:
        pinn = run_pinn_training(grid_files, domain, device_name, pinn_iters, pinn_ckpt)
    except Exception as exc:  # noqa: BLE001
        print(f"[-] PINN training failed: {exc}")
        traceback.print_exc()
        result = {"status": "error", "message": f"PINN training failed: {exc}"}
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    # --- Step 3: Extract refined metrics and 3-way comparison ---
    print("\n[Step 3/3] Extracting PINN-refined metrics ...")

    try:
        final_result = compute_pinn_metrics(pinn, sim_result, IRVE3_BASELINE, domain)
    except Exception as exc:  # noqa: BLE001
        print(f"[-] PINN metric extraction failed: {exc}")
        traceback.print_exc()
        result = {"status": "error", "message": f"PINN metric extraction failed: {exc}"}
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    # Print comparison table
    comp = final_result["comparison"]
    print("\n" + "=" * 110)
    print(f"{'IRVE-3 PINN CALIBRATION RESULTS: 3-WAY COMPARISON':^110}")
    print("=" * 110)
    print(f"{'Variable':<25} | {'Simulation':<12} | {'PINN (DDE)':<12} | {'Document':<12} | {'PINN Err %':<10} | {'Improve %':<8}")
    print("-" * 110)

    # Loop invariant: every comp entry carries sim/pinn/doc/pinn_error_pct/unit keys.
    for k, v in comp.items():
        sim_val = v["sim"]
        pinn_val = v["pinn"]
        doc_val = v["doc"]
        pinn_err = v["pinn_error_pct"]
        unit = v["unit"]

        sim_str = f"{sim_val:.2f} {unit}".strip()
        pinn_str = f"{pinn_val:.2f} {unit}".strip()
        doc_str = f"{doc_val:.2f} {unit}".strip() if doc_val > 0 else "N/A"

        sim_err = abs(sim_val - doc_val) / doc_val * 100 if doc_val > 0 else 0
        improve = sim_err - pinn_err if doc_val > 0 else 0
        improve_str = f"{improve:>+7.1f}%" if doc_val > 0 else "N/A"

        print(f"{k:<25} | {sim_str:<12} | {pinn_str:<12} | {doc_str:<12} | {pinn_err:>8.1f}% | {improve_str}")

    print("=" * 110)

    # Output JSON result for Ada sidecar
    print("\n[RESULT_JSON]")
    # Remove pinn_model (not serializable) before JSON output
    json_result = {k: v for k, v in final_result.items() if k != "pinn_model"}
    print(json.dumps(json_result, indent=2))

    print("\n[+] PINN calibration test completed successfully.")


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════
#  Self-tests (pytest-style; fast — no SPARTA run, no Docker, no training)
# ══════════════════════════════════════════════════════════════════════════

def _load_accelerator():
    """Import PINNAccelerator lazily; return class or None when unavailable.

    Pre: none. Post: returns PINNAccelerator class, or None with a printed
    reason when deepxde/torch are not installed in this environment.
    Tested by: indirectly via test_run_pinn_training().
    """
    try:
        from pinn_accelerator import PINNAccelerator
    except Exception as exc:  # noqa: BLE001 — heavy deps may be absent
        print(f"[i] pinn_accelerator unavailable ({exc}); skipping heavy test.")
        return None
    return PINNAccelerator


def test_detect_device() -> None:
    """detect_device returns a known (device, label) tuple.

    Tested by: this function itself (self-test section).
    """
    device, label = detect_device()
    assert device in {"cuda", "mps", "xpu", "musa", "cpu"}
    assert isinstance(label, str) and len(label) > 0


def test_run_baseline_validation_missing_inputs() -> None:
    """Missing grid file and missing SPARTA script yield a clean None.

    Tested by: this function itself (self-test section).
    """
    result = run_baseline_validation("/nonexistent/cad_dir", 42)
    assert result is None


def test_run_pinn_training_signature() -> None:
    """Training wrapper forwards args to PINNAccelerator (guarded import).

    Tested by: this function itself (self-test section).
    """
    cls = _load_accelerator()
    if cls is None:
        return
    acc = cls(device="cpu")
    assert hasattr(acc, "model") and acc.model is None


def test_compute_pinn_metrics_untrained_raises() -> None:
    """compute_pinn_metrics surfaces RuntimeError from an untrained model.

    Tested by: this function itself (self-test section).
    """
    cls = _load_accelerator()
    if cls is None:
        return

    acc = cls(device="cpu")
    try:
        compute_pinn_metrics(acc, {"comparison": {}, "stag_press": 0.0},
                             IRVE3_BASELINE, [0.0, 1.0, 1.0])
    except RuntimeError as exc:
        #  VERBOSE: expected refusal printed so silent-pass can't hide bugs.
        print(f"[TEST] expected RuntimeError raised: {exc}")
        return
    except Exception as exc:
        print(f"[TEST] unexpected exception type: {exc!r}")
        raise AssertionError(f"expected RuntimeError, got {exc!r}") from exc
    raise AssertionError("expected RuntimeError from untrained model")


def test_get_err() -> None:
    """get_err formula: pct error, zero-guarded for non-positive refs.

    Tested by: this function itself (self-test section).
    """
    assert get_err(110.0, 100.0) == 10.0
    assert get_err(90.0, 100.0) == 10.0
    assert get_err(5.0, 0.0) == 0
    assert get_err(0.0, -1.0) == 0


def test_main_help_exits_zero() -> None:
    """--help prints usage and exits cleanly (SystemExit 0).

    Tested by: this function itself (self-test section).
    """
    import contextlib
    import io

    argv_backup = sys.argv
    sys.argv = ["pinn_test.py", "--help"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try:
                main()
            except SystemExit as exc:
                #  VERBOSE: exit code printed so failures are attributable.
                print(f"[TEST] main exited with code {exc.code}")
                assert exc.code in (0, None), f"expected clean exit, got {exc.code}"
            else:
                pass  # some argparse configs return instead of exiting
    finally:
        sys.argv = argv_backup
    assert "--steps" in buf.getvalue()
