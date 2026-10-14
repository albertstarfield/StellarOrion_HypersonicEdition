#!/usr/bin/env python3
"""Take-4 probe for bo_optimization_3d.png: full-image ink profiling.

AXIOMS: the PNG bytes are ground truth (audit 3 proved `read` cache lies).
Purpose: verify audit-3 fixes (legend gaps, z-label slot, plain decade
ticks, B2 legend offset) and locate whatever sets the canvas right edge.
Prints measurements; orchestrator judges pass/fail.
"""
import numpy as np
from PIL import Image

IM = Image.open("stellarorion_program_proc/bo_optimization_3d.png").convert("RGB")
a = np.asarray(IM).astype(int)
h, w, _ = a.shape
print(f"canvas {w}x{h}")
white = (a.min(axis=2) >= 245)
ink = ~white

cols = np.where(ink.any(axis=0))[0]
rowsall = np.where(ink.any(axis=1))[0]
print(f"ink bbox x{cols.min()}-{cols.max()} y{rowsall.min()}-{rowsall.max()}")
right = cols.max()
for c in range(right - 30, right + 1, 6):
    rr = np.where(ink[:, c])[0]
    if len(rr):
        print(f"  col {c}: rows {rr.min()}-{rr.max()} n={len(rr)}")

# fig-legend band: frame extents + raw entry runs at text rows y326-335
band = ink[315:347, :]
bcols = np.where(band.any(axis=0))[0]
print(f"legend band ink x{bcols.min()}-{bcols.max()}")
seg = ink[326:336, :]
runs = []
start = None
for x in range(w):
    on = bool(seg[:, x].any())
    if on and start is None:
        start = x
    if not on and start is not None:
        runs.append((start, x - 1))
        start = None
if start is not None:
    runs.append((start, w - 1))
gaps = [runs[i + 1][0] - runs[i][1] - 1 for i in range(len(runs) - 1)]
print(f"raw runs y326-335: {runs}")
print(f"raw gaps: {gaps}")


def colprofile(x0, x1, y0, y1, label):
    """Print contiguous x-ranges holding any ink inside [x0,x1) x [y0,y1)."""
    rngs = []
    for x in range(x0, x1):
        if ink[y0:y1, x].any():
            if rngs and x == rngs[-1][1] + 1:
                rngs[-1] = (rngs[-1][0], x)
            else:
                rngs.append((x, x))
    print(f"{label}: ink col ranges {rngs}")


colprofile(325, 470, 95, 235, "z zone y95-235 (ticks/label/bar)")
colprofile(360, 480, 115, 210, "cb text+label zone y115-210")
colprofile(440, 535, 95, 215, "C ylabel+ytick zone y95-215")


def glyph_rows(x0, x1, y0, y1, label, thr=120):
    """Dark-ink row runs (glyph heights) inside a box."""
    sub = a[y0:y1, x0:x1]
    dark = sub.max(axis=2) < thr
    rws = np.where(dark.any(axis=1))[0]
    if len(rws) == 0:
        print(f"{label}: no dark ink")
        return
    out = []
    s = prev = None
    for r in rws:
        if s is None:
            s = r
        elif r - prev > 1:
            out.append((s + y0, prev + y0, prev - s + 1))
            s = r
        prev = r
    out.append((s + y0, prev + y0, prev - s + 1))
    print(f"{label}: dark row runs {out}")


glyph_rows(365, 445, 110, 215, "cb tick glyphs")
glyph_rows(470, 520, 95, 215, "C y-tick glyphs")
glyph_rows(448, 475, 95, 215, "C ylabel glyphs")

# B2 legend left border vs spine: probe rows y415, y430
for y in (415, 430):
    rr = np.where(ink[y, 505:560])[0] + 505
    print(f"B2 row y{y}: ink cols in 505-560 -> {rr.tolist()}")
