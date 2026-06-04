import sys
import os
import shutil

# Make output dirs
out_orion = os.path.join("ProgressReport", "Week 5", "figure", "baselineOrion")
out_hiad = os.path.join("ProgressReport", "Week 5", "figure", "baselineHIADOrion")
os.makedirs(out_orion, exist_ok=True)
os.makedirs(out_hiad, exist_ok=True)

# Run Orion
print("--- RUNNING ORION STANDALONE ---")
from StellarOrionEngine_ORION import Api as ApiOrion
app_orion = ApiOrion()
orion_params = {
    'target_vehicle': 'ORION',
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_vstream': '10000.0',
    'env_mach': '32.0',
    'env_alt': '40.0',
    'env_run': '700',
    'env_fnum': '2.5e20',
    'env_xmin': '-1.69',
    'env_xmax': '4.5',
    'env_ymax': '3.976',
    'env_cores': 10,
    'sparta_gpu': False,
    'base_diameter': 5.02,
    'default_payload': False,
    'payload_file': 'CADDesign/ORION_custom_full.step',
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': False, 'thickness': False, 'scallop_pts': False, 'scallop_angle': False}
}
try:
    app_orion.execute_optimization(orion_params)
    print("--- COPYING ORION RESULTS ---")
    results_dirs = [os.path.join("results", d) for d in os.listdir("results") if os.path.isdir(os.path.join("results", d))]
    latest_orion_dir = max(results_dirs, key=os.path.getmtime)
    for f in os.listdir(latest_orion_dir):
        if f.endswith('.png') or f.endswith('.jpg') or f.endswith('.mp4'):
            shutil.copy(os.path.join(latest_orion_dir, f), out_orion)
except Exception as e:
    print(f"Error running Orion standalone: {e}")

# Run HIAD-Orion
print("--- RUNNING HIAD-ORION ---")
from StellarOrionEngineMach5Up import Api as ApiHIAD
app_hiad = ApiHIAD()
hiad_params = {
    'target_vehicle': 'HIAD',
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_vstream': '10000.0',
    'env_mach': '32.0',
    'env_alt': '40.0',
    'env_run': '700',
    'env_fnum': '2.5e20',
    'env_xmin': '-1.69',
    'env_xmax': '8.0',
    'env_ymax': '6.0',
    'env_cores': 10,
    'sparta_gpu': False,
    'base_diameter': 5.02,
    'default_payload': True,
    'payload_file': 'CADDesign/ORION_custom_full.step',
    'payload_type': 'orion',
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': False, 'thickness': False, 'scallop_pts': False, 'scallop_angle': False}
}
try:
    app_hiad.execute_optimization(hiad_params)
    print("--- COPYING HIAD-ORION RESULTS ---")
    results_dirs = [os.path.join("results", d) for d in os.listdir("results") if os.path.isdir(os.path.join("results", d))]
    latest_hiad_dir = max(results_dirs, key=os.path.getmtime)
    for f in os.listdir(latest_hiad_dir):
        if f.endswith('.png') or f.endswith('.jpg') or f.endswith('.mp4'):
            shutil.copy(os.path.join(latest_hiad_dir, f), out_hiad)
except Exception as e:
    print(f"Error running HIAD-Orion: {e}")

print("--- ALL DONE ---")
