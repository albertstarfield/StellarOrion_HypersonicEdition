import os
import sys
import glob

sys.path.append('source')
from visualizer import generate_plots

plots_dir = 'CADDesign/results_reference'
cad_dir = 'CADDesign'
grid_files = sorted(glob.glob(os.path.join(plots_dir, 'grid.*.out')))

if grid_files:
    viz_metadata = {'target_vehicle': 'IRVE-3_ORION_PAYLOAD', 'env_xmin': -5.0, 'env_xmax': 9.0}
    surf_file = os.path.join(cad_dir, "HIAD_opt.surf")
    print(f"Using latest grid file: {grid_files[-1]}")
    generate_plots(grid_files[-1], plots_dir, suffix="", ref_params=viz_metadata, surf_file=surf_file)
    print("Plots regenerated successfully.")
else:
    print("No grid files found.")
