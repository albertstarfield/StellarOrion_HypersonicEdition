import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api

app = Api()

# =============================================================================
# StellarOrion — Run Both Baselines (IRVE-3 HIAD + Orion-HIAD)
# =============================================================================
# PARTICLE SCALING (applies to all configs):
#   n_sim = (nrho × V_domain) / fnum
#   fnum=1.5e20 → ~2M particles (minimum for visible shockwave)
#   Lower fnum = more particles = better statistics = more RAM/CPU
# =============================================================================

# 1. Run IRVE-3 Baseline
print("\n--- Running IRVE-3 Baseline ---")
irve3_params = {
    'target_vehicle': 'IRVE-3',
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_vstream': '10000.0',
    'env_mach': '32.0',
    'env_alt': '40.0',
    'env_run': '2500',          # Run full steady-state steps
    'env_fnum': '1.5e20',       # ~2M particles for visible shockwave
    'env_xmin': '-1.69',
    'env_xmax': '4.5',
    'env_ymax': '3.976',
    'env_cores': 10,
    'sparta_gpu': False,
    'base_diameter': 3.0,
    'default_payload': True,    # IRVE-3 has a default cylinder payload
    'payload_type': 'cylinder',
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': False, 'thickness': False, 'scallop_pts': False, 'scallop_angle': False}
}
try:
    pass
except Exception as e:
    print(f"IRVE-3 failed: {e}")

# 2. Run ORION-HIAD Baseline
print("\n--- Running ORION-HIAD Baseline ---")
orion_hiad_params = {
    'target_vehicle': 'HIAD',   # This creates the HIAD geometry
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_vstream': '10000.0',
    'env_mach': '32.0',
    'env_alt': '40.0',
    'env_run': '2500',          # Run full steady-state steps
    'env_fnum': '1.5e20',       # ~2M particles for visible shockwave
    'env_xmin': '-1.69',
    'env_xmax': '8.0',
    'env_ymax': '6.0',
    'env_cores': 10,
    'sparta_gpu': False,
    'base_diameter': 5.02,
    'default_payload': True,
    'payload_file': 'CADDesign/ORION_custom_full.step',
    'payload_type': 'orion',    # This tells it to use the Orion analytical geometry we just fixed
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': False, 'thickness': False, 'scallop_pts': False, 'scallop_angle': False}
}
try:
    app.execute_optimization(orion_hiad_params)
except Exception as e:
    print(f"ORION-HIAD failed: {e}")
