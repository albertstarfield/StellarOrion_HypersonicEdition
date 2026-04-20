import os
import sys
import json
from gui_backend import Api

def run_headless_test():
    print("[*] STARTING HEADLESS OPTIMIZATION TEST...")
    
    # Initialize API
    api = Api()
    
    # Define default parameters (similar to GUI defaults)
    opt_params = {
        'env_preset': 'artemis',
        'env_nrho': '3.9e20',
        'env_temp_inf': '200.0',
        'env_fnum': '1e16',
        'env_temp': '1000.0',
        'env_step': '1e-6',
        'env_run': '1000',
        'samples': 2,  # Small number for testing
        'base_diameter': 3.0,
        'base_angle': 60.0,
        'base_toroids': 7,
        'base_nose': 0.191,
        'd_min': 2.5,
        'd_max': 4.5,
        'goal': 'drag',
        'v_diameter': True,
        'v_angle': True,
        'v_toroids': True,
        'v_nose': True,
        'targets': {
            'beta': {'val': 150},
            'drag': {'val': 100}
        }
    }
    
    try:
        # Run the optimization
        api.execute_optimization(opt_params, is_gui=False)
        print("\n[SUCCESS] Headless optimization test completed successfully.")
    except Exception as e:
        print(f"\n[FAILURE] Optimization test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_headless_test()
