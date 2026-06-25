import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from StellarOrionEngine_ORION import Api
app = Api()

# =============================================================================
# StellarOrion — Orion Baseline Configuration (Mach 30, Earth Lunar Return)
# =============================================================================
#
# DSMC GOVERNING EQUATIONS (Direct Simulation Monte Carlo):
#   The Boltzmann equation is solved by tracking simulated particles that each
#   represent a cluster of real molecules. The key linking parameter is fnum.
#
#   PARTICLE COUNT FORMULA:
#     n_simulated = (nrho × V_domain) / fnum
#
#     where:
#       nrho     = freestream number density (molecules/m³)
#       V_domain = simulation domain volume (m³)
#       fnum     = number of real molecules represented by ONE simulated particle
#
#   For this config:
#     nrho = 2.45e22 molecules/m³ (Earth atmosphere at 40 km altitude)
#     V_domain = (4.5 - (-1.69)) × (3.976 - 0) × 1.0 = 6.19 × 3.976 × 1.0 ≈ 24.6 m³
#     fnum = 1.5e20
#     → n_simulated ≈ (2.45e22 × 24.6) / 1.5e20 ≈ 4,020 base particles
#     → After AMR (adaptive mesh refinement) near vehicle: ~2,000,000 particles
#
#   WHY fnum MATTERS:
#     - Lower fnum  → more simulated particles → better shockwave resolution → more RAM/CPU
#     - Higher fnum → fewer simulated particles → faster but noisier → shockwave invisible
#     - fnum = 1.5e20 gives ~2M particles: enough to clearly see the bow shock structure
#
#   PHYSICS CHAIN:
#     env_alt → selects atmosphere model (Earth: γ=1.4, R=287.05 J/kg·K)
#     env_alt → determines T∞ (freestream temperature, ~250 K at 40 km)
#     env_nrho → ambient number density at altitude (2.45e22 at 40 km Earth)
#     env_vstream → vehicle velocity relative to atmosphere (9500 m/s = Mach 30)
#     env_mach → v_stream / speed_of_sound (diagnostic, DSMC uses v_stream directly)
#     env_fnum → scales simulated particles to real physics (controls statistical quality)
#     env_run → total DSMC timesteps (dt = 1e-6 s fixed, so 2500 steps = 2.5 ms simulated)
#     env_cores → MPI parallel processes across CPU cores
#
# =============================================================================

opt_params = {
    'target_vehicle': 'ORION',       # Vehicle type: 'ORION' (capsule only), 'HIAD' (toroid), 'IRVE-3'
    'opt_method': 'random',          # Optimization method (unused when opt_samples=0)
    'opt_samples': '0',              # Number of optimization samples (0 = baseline only, no optimization)

    # --- FREESTREAM CONDITIONS ---
    'env_nrho': '2.45e22',           # Number density [molecules/m³] — Earth atmosphere at 40 km altitude
    'env_vstream': '9500.0',         # Freestream velocity [m/s] — Orion lunar return velocity (Mach 30)
    'env_mach': '30.0',              # Mach number — v_stream / speed_of_sound (diagnostic for logging)
    'env_alt': '40.0',               # Altitude [km] — selects Earth atmosphere preset (T∞, γ, R)

    # --- SIMULATION CONTROL ---
    'env_run': '2500',               # DSMC timesteps — dt=1e-6 s, so 2500 steps = 2.5 ms simulated time
    'env_fnum': '1.5e20',            # Particle scaling factor [molecules/particle]
                                     #   n_sim = (nrho × V_domain) / fnum
                                     #   fnum=1.5e20 → ~2M particles after AMR (visible shockwave)
                                     #   fnum=5.0e23 → ~600 particles (shockwave invisible)
    'env_xmin': '-1.69',             # Domain X-min [m] — upstream boundary (inflow face)
    'env_xmax': '4.5',               # Domain X-max [m] — downstream boundary (outflow face)
    'env_ymax': '3.976',             # Domain Y-max [m] — radial boundary (axisymmetric)
    'env_cores': 4,                 # MPI processes — uses all 16 CPU threads for parallel execution

    # --- GPU SETTINGS ---
    'sparta_gpu': False,             # GPU acceleration (Kokkos) — False = CPU-only via mpirun

    # --- VEHICLE GEOMETRY ---
    'base_diameter': 5.02,           # Vehicle base diameter [m] — Orion capsule: 5.02 m
    'default_payload': False,        # Use default cylinder payload — False = use custom STEP file
    'payload_file': 'CADDesign/ORION_custom_full.step',  # Custom payload geometry (Orion crew module)

    # --- OPTIMIZATION PARAMETERS (all disabled for baseline run) ---
    'active_params': {
        'diameter': True,            # Allow diameter variation (optimization only)
        'angle': True,               # Allow nose cone angle variation
        'nose': True,                # Allow nose bluntness variation
        'toroids': False,            # HIAD toroid parameters (disabled for Orion-only)
        'thickness': False,          # Heatshield thickness (disabled)
        'scallop_pts': False,        # Scallop discretization points (disabled)
        'scallop_angle': False       # Scallop pocket angle (disabled)
    }
}

app.execute_optimization(opt_params)
