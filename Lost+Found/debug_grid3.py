import numpy as np
from source import visualizer

data = visualizer.parse_grid_dump("CADDesign/results_reference/grid.200.out")
valid_mask = np.all(np.isfinite(data[:, :10]), axis=1)
data = data[valid_mask]

nrho = data[:, 9]
print("Percentiles of nrho:")
print(f"0%: {np.percentile(nrho, 0):.2e}")
print(f"50%: {np.percentile(nrho, 50):.2e}")
print(f"90%: {np.percentile(nrho, 90):.2e}")
print(f"95%: {np.percentile(nrho, 95):.2e}")
print(f"99%: {np.percentile(nrho, 99):.2e}")
print(f"100%: {np.percentile(nrho, 100):.2e}")

