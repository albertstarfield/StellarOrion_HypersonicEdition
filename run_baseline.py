import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api
app = Api()

opt_params = {
    'target_vehicle': 'IRVE-3',
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_mach': '17.6',
    'env_alt': '40.0',
    'env_run': '200',
    'env_fnum': '1.0e23',
    'env_cores': 2,
    'sparta_gpu': False,
    'default_payload': True,
    'payload_type': 'cylinder',
    'payload_radius': 500.0,
    'payload_height': 2000.0,
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': True, 'thickness': True, 'scallop_pts': True, 'scallop_angle': True}
}

# app.execute_optimization(opt_params)
