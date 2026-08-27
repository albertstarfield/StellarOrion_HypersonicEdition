import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api
app = Api()

# =============================================================================
# StellarOrion — HIAD + Orion Capsule Baseline (Mach 32, Earth)
# =============================================================================
# PARTICLE COUNT:
#   n_sim = (nrho × V_domain) / fnum
#   nrho = 2.45e22, V_domain = (6.0+1.69) × 4.5 × 1.0 ≈ 34.6 m³, fnum = 1.5e20
#   → n_sim ≈ (2.45e22 × 34.6) / 1.5e20 ≈ 5,600 base particles
#   → After AMR near vehicle: ~2,000,000 particles (visible shockwave + toroid wake)
#
# GOVERNING EQUATIONS:
#   DSMC solves the Boltzmann equation via particle collisions:
#     ∂f/∂t + v·∇f = Q_collisions
#   Each simulated particle = fnum real molecules. Collision frequency scales
#   with local number density n_local = n_sim × fnum / V_cell.
# =============================================================================

opt_params = {
    'target_vehicle': 'IRVE-3_ORION_PAYLOAD',  # Combined HIAD toroid + Orion capsule
    'opt_method': 'random',
    'opt_samples': '0',

    # --- FREESTREAM CONDITIONS (Earth at 40 km) ---
    'env_nrho': '2.45e22',           # Number density [molecules/m³]
    'env_vstream': '10000.0',        # Freestream velocity [m/s] — slightly above Mach 30
    'env_mach': '32.0',              # Mach number (diagnostic)
    'env_run': '2500',               # DSMC timesteps (dt=1e-6 s → 2.5 ms simulated)

    # --- PARTICLE SCALING ---
    'env_fnum': '1.5e20',            # Real molecules per simulated particle
                                     #   Lower = more particles = better statistics = more RAM
                                     #   fnum=1.5e20 → ~2M particles (shockwave visible)

    # --- DOMAIN BOUNDARIES ---
    'env_xmin': '-1.69',             # Upstream (inflow) — must be far enough to capture bow shock
    'env_xmax': '6.00',              # Downstream — expanded for Orion capsule trailing behind HIAD
    'env_ymax': '4.50',              # Radial — expanded for 7.5 m diameter HIAD + shock boundary

    # --- COMPUTE ---
    'env_cores': 10,                 # MPI processes (CPU cores)
    'sparta_gpu': False,             # CPU-only (no Kokkos GPU)

    # --- VEHICLE GEOMETRY ---
    'default_payload': True,         # Enable payload integration behind HIAD
    'payload_type': 'orion',         # Orion crew module shape
    'payload_radius': 2500.0,        # Payload radius [mm]
    'payload_height': 3300.0,        # Payload height [mm]

    # --- OPTIMIZATION PARAMETERS ---
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': True, 'thickness': True, 'scallop_pts': True, 'scallop_angle': True}
}

app.execute_optimization(opt_params)
