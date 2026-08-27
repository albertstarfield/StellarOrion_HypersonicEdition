import os
import StellarOrionEngineMach5Up
from source import visualizer

engine = StellarOrionEngineMach5Up.Api()
opt_params = {
    'target_vehicle': 'ORION',
    'env_xmin': -1.69,
    'env_xmax': 4.5,
    'env_ymax': 3.976,
}
sample_dict = {'diameter': 3.0}

viz_metadata = engine._get_viz_params(opt_params, sample_dict)
grid_file = "CADDesign/results_reference/grid.200.out"
surf_file = "CADDesign/ORION_custom.surf"
output_dir = "ProgressReport/Week 5/figures/ORION-HIAD-Baseline"
os.makedirs(output_dir, exist_ok=True)

visualizer.generate_plots(grid_file, output_dir, ref_params=viz_metadata, surf_file=surf_file)
print("Regenerated ORION plots!")
