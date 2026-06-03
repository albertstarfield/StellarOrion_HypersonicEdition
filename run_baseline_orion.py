import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngine_ORION import Api
app = Api()

opt_params = {
    'target_vehicle': 'ORION',
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_vstream': '10000.0',
    'env_mach': '32.0', # Artemis I high-energy entry
    'env_alt': '40.0',
    'env_run': '2500',
    'env_fnum': '2.5e20',
    'env_xmin': '-1.69',
    'env_xmax': '2.00',
    'env_cores': 10,
    'sparta_gpu': False,
    'base_diameter': 5.02,
    'default_payload': False,
    'payload_file': 'CADDesign/ORION_custom_full.step',
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': False, 'thickness': False, 'scallop_pts': False, 'scallop_angle': False}
}

app.execute_optimization(opt_params)
