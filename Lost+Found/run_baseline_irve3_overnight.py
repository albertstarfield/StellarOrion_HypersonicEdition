import sys
import os
import shutil
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api

# Make output dirs
out_irve3 = os.path.join("ProgressReport", "Week 5", "figures", "IRVE-3-HIAD")
out_irve3_baseline = os.path.join("ProgressReport", "Week 5", "figures", "IRVE-3-HIAD-BASELINE")
os.makedirs(out_irve3, exist_ok=True)
os.makedirs(out_irve3_baseline, exist_ok=True)

# Run IRVE-3 HIAD-Only Baseline
print("--- RUNNING IRVE-3 HIAD-ONLY BASELINE (OVERNIGHT) ---")
app = Api()
opt_params = {
    'target_vehicle': 'IRVE-3',      # IRVE-3 HIAD-only (no Orion payload)
    'opt_method': 'random',
    'opt_samples': '0',

    # --- FREESTREAM CONDITIONS ---
    'env_nrho': '2.45e22',           # Number density [molecules/m³] — Earth at 40 km
    'env_mach': '17.6',              # Mach number (IRVE-3 re-entry speed)
    'env_alt': '40.0',               # Altitude [km] — selects Earth atmosphere model
    'env_run': '1500',               # DSMC timesteps (overnight run)

    # --- PARTICLE SCALING ---
    'env_fnum': '1.5e20',            # ~2M particles for visible shockwave structure

    # --- COMPUTE ---
    'env_cores': 10,                 # MPI processes for overnight run

    # --- VEHICLE GEOMETRY ---
    'default_payload': True,         # IRVE-3 has default cylindrical payload
    'payload_type': 'cylinder',      # Simple cylinder payload shape
    'payload_radius': 500.0,         # Payload radius [mm]
    'payload_height': 2000.0,        # Payload height [mm]

    # --- OPTIMIZATION PARAMETERS ---
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': True, 'thickness': True, 'scallop_pts': True, 'scallop_angle': True}
}

try:
    app.execute_optimization(opt_params)
    print("--- COPYING IRVE-3 RESULTS ---")
    results_dirs = [os.path.join("results", d) for d in os.listdir("results") if os.path.isdir(os.path.join("results", d))]
    if results_dirs:
        latest_dir = max(results_dirs, key=os.path.getmtime)
        print(f"Latest results dir: {latest_dir}")
        for f in os.listdir(latest_dir):
            if f.endswith('.png') or f.endswith('.jpg') or f.endswith('.mp4'):
                src_path = os.path.join(latest_dir, f)
                shutil.copy(src_path, out_irve3)
                shutil.copy(src_path, out_irve3_baseline)
        print("--- COPY COMPLETE ---")
    else:
        print("No results directory found.")
except Exception as e:
    print(f"Error running IRVE-3 baseline: {e}")

print("--- ALL DONE ---")
