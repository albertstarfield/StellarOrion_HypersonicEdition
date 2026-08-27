import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngineMach5Up import Api
app = Api()

# =============================================================================
# StellarOrion — IRVE-3 HIAD-Only Baseline (Mach 17.6, Earth)
# =============================================================================
# PARTICLE COUNT:
#   n_sim = (nrho × V_domain) / fnum
#   nrho = 2.45e22, V_domain = (4.5+1.69) × 3.976 × 1.0 ≈ 24.6 m³, fnum = 1.5e20
#   → n_sim ≈ (2.45e22 × 24.6) / 1.5e20 ≈ 4,020 base particles
#   → After AMR: ~2,000,000 particles
#
# GOVERNING EQUATIONS:
#   DSMC collision rate: ν = n × σ × g (number density × cross-section × relative speed)
#   With fnum scaling: n_real = n_sim × fnum / V_cell
#   More particles (lower fnum) → better sampling of collision statistics → less noise
# =============================================================================

opt_params = {
    'target_vehicle': 'IRVE-3',      # IRVE-3 HIAD-only (no Orion payload)
    'opt_method': 'random',
    'opt_samples': '0',

    # --- FREESTREAM CONDITIONS ---
    'env_nrho': '2.45e22',           # Number density [molecules/m³] — Earth at 40 km
    'env_mach': '17.6',              # Mach number (IRVE-3 re-entry speed)
    'env_alt': '40.0',               # Altitude [km] — selects Earth atmosphere model
    'env_run': '200',                # DSMC timesteps (short test run)

    # --- PARTICLE SCALING ---
    'env_fnum': '1.5e20',            # ~2M particles for visible shockwave structure

    # --- COMPUTE ---
    'env_cores': 2,                  # MPI processes (reduced for quick test)

    # --- VEHICLE GEOMETRY ---
    'default_payload': True,         # IRVE-3 has default cylindrical payload
    'payload_type': 'cylinder',      # Simple cylinder payload shape
    'payload_radius': 500.0,         # Payload radius [mm]
    'payload_height': 2000.0,        # Payload height [mm]

    # --- OPTIMIZATION PARAMETERS ---
    'active_params': {'diameter': True, 'angle': True, 'nose': True, 'toroids': True, 'thickness': True, 'scallop_pts': True, 'scallop_angle': True}
}

# app.execute_optimization(opt_params)
