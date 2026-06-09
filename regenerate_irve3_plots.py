import os
from StellarOrionEngineMach5Up import Api
from source import visualizer
import sys

engine = Api()
# Reconstruct basic metadata used for IRVE-3 baseline
opt_params = {
    'target_vehicle': 'IRVE-3',
    'env_xmin': -5.0,
    'env_xmax': 9.0,
    'env_ymax': 5.0,
    'env_vstream': 2463.0, # roughly what we saw
    'env_temp_inf': 270.0,
    'env_nrho': 3.5e22,
    'payload': True, # FORCE payload overlay
    'mach': 10.0,
    'alt': 52.0
}
sample_dict = {
    'diameter': 3.36,
    'angle': 60.0,
    'toroids': 6,
    'toroid_radius': 0.135,
    'nose_radius': 0.55
}

viz_metadata = engine._get_viz_params(opt_params, sample_dict)
viz_metadata['payload'] = True # Ensure visualizer sees it

grid_file = "CADDesign/results_reference/grid.1100.out"
surf_file = "CADDesign/HIAD_custom.surf"
output_dir = "web/assets/plots"
prog_dir = "ProgressReport_Week5/figures/IRVE-3 HIAD Progress Report Figure"

print("Regenerating plots...")
visualizer.generate_plots(grid_file, output_dir, ref_params=viz_metadata, surf_file=surf_file)

import shutil
import glob
print("Copying to progress report...")
for file in glob.glob(os.path.join(output_dir, "*_smooth.png")):
    shutil.copy(file, prog_dir)
for file in glob.glob(os.path.join(output_dir, "*_smooth.jpg")):
    shutil.copy(file, prog_dir)

print("Done!")
