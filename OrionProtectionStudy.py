import os
import sys
import subprocess
from StellarOrionEngineMach5Up import Api

def setup_orion_study():
    print("\n" + "="*80)
    print(f"{'STELLARORION: ORION PROTECTION STUDY INITIALIZATION':^80}")
    print("="*80)
    
    api = Api()
    
    # 1. Define Orion-scale Parameters
    # Reference: LOFTID (6m HIAD) protected a 1:1 scale test payload.
    # For a full Orion capsule (5m diameter), we scale the HIAD to 9m.
    orion_params = {
        'diameter': 9.0,        # meters
        'angle': 65.0,           # degrees (steeper for high-mass)
        'nose_radius': 0.5,      # meters
        'toroids': 12,           # Increased for structural rigidity
        'mass': 10500.0,         # kg (Orion CM mass approx 10.5t)
        'nose_type': 'smooth'
    }
    
    print(f"[*] Target Payload: Orion Crew Module (5m diameter)")
    print(f"[*] Protecting HIAD Scale: {orion_params['diameter']}m")
    
    # 2. Generate Geometry with Placeholder Payload
    # In the next step, we would use the actual Orion STEP file.
    # For now, we use a placeholder or the default payload logic.
    print("[*] Generating Initial Orion-HIAD Assembly...")
    
    cad_dir = os.path.join(api.cwd, "CADDesign")
    python_exec = api._get_python_exec()
    
    cmd_cad = [
        python_exec, os.path.join(cad_dir, "HIAD_GeometryEngine.py"),
        "--diameter", str(orion_params['diameter']),
        "--angle", str(orion_params['angle']),
        "--nose", str(orion_params['nose_radius']),
        "--toroids", str(orion_params['toroids']),
        "--output", "Orion_HIAD_ScaleStudy",
        "--imageDebug"
    ]
    
    try:
        subprocess.run(cmd_cad, cwd=cad_dir, check=True)
        print(f"[SUCCESS] Orion scale assembly generated: Orion_HIAD_ScaleStudy.step")
    except Exception as e:
        print(f"[FAILURE] Geometry generation failed: {e}")
        return

    # 3. Define Sampling Strategy for Global Optimization
    print("\n[OPTIMIZATION STRATEGY: GLOBAL SAMPLING]")
    print("-" * 40)
    print("  Mode: Multi-Objective LHS (Latin Hypercube Sampling)")
    print("  Samples: 48 (Proposed)")
    print("  Objectives: Minimize Peak Heat Flux & Maximize Drag Coefficient")
    print("  Constraints: Protect Orion Wake (T_backshell < 500K)")
    
    print("\n[*] Ready for Phase 4 Execution.")
    print("="*80 + "\n")

if __name__ == "__main__":
    setup_orion_study()
