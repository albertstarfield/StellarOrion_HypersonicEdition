import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api
app = Api()

opt_params = {
    'target_vehicle': 'IRVE-3_ORION_PAYLOAD',
    'opt_method': 'random',
    'opt_samples': '0',
    'env_nrho': '2.45e22',
    'env_vstream': '10000.0',
    'env_mach': '32.0',
    'env_run': '2500',
    'env_fnum': '2.5e20',
    'env_xmin': '-1.69',
    'env_xmax': '6.00',  # Expanded to 6.0m because the Orion capsule trails completely behind the full face HIAD umbrella!
    'env_ymax': '4.50',  # Expanded to fit the 7.5m diameter (3.75m radius) + shock boundary
    'env_cores': 10,
    'sparta_gpu': False,
    'default_payload': True, # This enables the payload integration
    'payload_type': 'orion',
    'payload_radius': 2500.0,
    'payload_height': 3300.0,
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': True, 'thickness': True, 'scallop_pts': True, 'scallop_angle': True}
}

app.execute_optimization(opt_params)
