import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api
app = Api()

opt_params = {
    'target_vehicle': 'IRVE-3',
    'opt_method': 'random',
    'opt_samples': '0',
    'samples': 0,
    'resume': True,
    'env_mach': '17.6',
    'env_alt': '40.0',
    'env_run': '2500',
    'env_fnum': '2.5e20',
    'env_cores': 10,
    'sparta_gpu': False,
    'default_payload': False,
    'payload_file': 'CADDesign/HIAD_custom_full.step',
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': True, 'thickness': True, 'scallop_pts': True, 'scallop_angle': True}
}

app.execute_optimization(opt_params)
