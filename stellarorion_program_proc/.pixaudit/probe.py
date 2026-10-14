"""Pixel audit helpers for bo_optimization_3d.png.
AXIOMS: read-tool cache may lie; every claim needs printed pixel evidence.
THEORIES: ink = non-white pixel; row/col projections locate boxes and text.
APPLICATIONS: python3 probe.py <func> args...
"""
import numpy as np
from PIL import Image

PNG = 'stellarorion_program_proc/bo_optimization_3d.png'

def load():
    im = Image.open(PNG).convert('RGB')
    return np.asarray(im).astype(int)

def ink(a, thr=250):
    """Boolean ink mask: any channel below thr."""
    return (a < thr).any(axis=2)

def rowproj(m, y0, y1, x0, x1):
    for y in range(y0, y1):
        print(y, int(m[y, x0:x1].sum()))

def colproj(m, y0, y1, x0, x1):
    for x in range(x0, x1):
        print(x, int(m[y0:y1, x].sum()))

if __name__ == '__main__':
    import sys
    a = load()
    m = ink(a)
    print('shape', a.shape)
    if sys.argv[1] == 'rows':
        rowproj(m, int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
    elif sys.argv[1] == 'cols':
        colproj(m, int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
    elif sys.argv[1] == 'px':
        x, y = int(sys.argv[2]), int(sys.argv[3])
        print('px', x, y, a[y, x])
    elif sys.argv[1] == 'crop':
        x0, y0, x1, y1 = map(int, sys.argv[2:6])
        out = sys.argv[6]
        Image.open(PNG).convert('RGB').crop((x0, y0, x1, y1)).save(out)
        print('saved', out, (x1-x0, y1-y0))
