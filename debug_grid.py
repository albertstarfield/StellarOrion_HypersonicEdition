import numpy as np
from source import visualizer

data = visualizer.parse_grid_dump("CADDesign/results_reference/grid.200.out")
valid_mask = np.all(np.isfinite(data[:, :10]), axis=1)
data = data[valid_mask]

nrho = data[:, 9]
n_max = np.percentile(nrho, 95)
density_mask = nrho < (n_max * 0.01)

print(f"Data points: {len(data)}")
print(f"nrho min: {np.min(nrho):.2e}, max: {np.max(nrho):.2e}")
print(f"n_max (95th percentile): {n_max:.2e}")
print(f"Points masked out by density: {np.sum(density_mask)} / {len(nrho)}")
