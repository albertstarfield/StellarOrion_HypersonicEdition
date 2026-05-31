import sys
from StellarOrionEngineMach5Up import Api

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
        'pinn_accel': True,
        'samples': 3,  # Adjusted for comparison
        'base_diameter': 3.0,
        'base_angle': 60.0,
        'base_toroids': 6,
        'base_nose': 0.550,
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
        # Run 1: Scalloped Mode (The "Real" Physics)
        print("\n[*] RUNNING MODE A: SCALLOPED (Wavy Skin)...")
        opt_params['flat_skin'] = False
        api.execute_optimization(opt_params, is_gui=False)
        
        # Run 2: Smooth Mode (The "Idealized" Baseline)
        print("\n[*] RUNNING MODE B: SMOOTH (Flat Skin)...")
        opt_params['flat_skin'] = True
        api.execute_optimization(opt_params, is_gui=False)
        
        print("\n[SUCCESS] Dual-mode optimization comparison completed.")
        print("[ANALYSIS] Compare results in the history DB to assess 'Scalloping Penalty' vs 'Drag Advantage'.")
    except Exception as e:
        print(f"\n[FAILURE] Optimization test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_headless_test()
