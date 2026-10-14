"""Check 1: figure-level legend band, entry gaps + OCR."""
import numpy as np
from PIL import Image

a = np.asarray(Image.open('stellarorion_program_proc/bo_optimization_3d.png').convert('RGB')).astype(int)
m = (a < 250).any(axis=2)

# locate the legend frame: search rows 300-345 for long horizontal runs
print('--- rows 300-345, ink count over x50-860 ---')
for y in range(300, 346):
    c = int(m[y, 50:861].sum())
    print(y, c)
