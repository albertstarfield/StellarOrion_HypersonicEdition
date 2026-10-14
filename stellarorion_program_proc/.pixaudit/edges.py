"""Check 8: no ink within outermost 2px border."""
import numpy as np
from PIL import Image

a = np.asarray(Image.open('stellarorion_program_proc/bo_optimization_3d.png').convert('RGB')).astype(int)
m = (a < 250).any(axis=2)
h, w = m.shape
border = np.zeros_like(m)
border[0:2, :] = True; border[h-2:h, :] = True; border[:, 0:2] = True; border[:, w-2:w] = True
ys, xs = np.nonzero(m & border)
print('ink pixels in 2px border:', len(ys))
if len(ys):
    print('sample coords:', list(zip(xs[:20].tolist(), ys[:20].tolist())))
# also report min/max ink extents
ys2, xs2 = np.nonzero(m)
print('ink extent: x', xs2.min(), xs2.max(), ' y', ys2.min(), ys2.max())
# corner colors
for (x, y) in [(0,0),(1,1),(862,0),(0,595),(862,595)]:
    print('corner', x, y, a[y, x])
