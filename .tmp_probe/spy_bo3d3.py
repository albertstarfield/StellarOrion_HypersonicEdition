#!/usr/bin/env python3
"""Take-4 probe part 2: row-precise verification of audit-3 fixes.

AXIOMS: PNG bytes are ground truth; _PANEL (238,243,242) is background,
so 'content' = pixel with max(RGB) < 210 (slate/red/teal) or near-white
(>=250) ONLY where distinguishing star white from panel; rows are probed
at known glyph bands, never column-ANY over wide windows.
"""
import numpy as np
from PIL import Image

IM = Image.open("stellarorion_program_proc/bo_optimization_3d.png").convert("RGB")
a = np.asarray(IM).astype(int)
h, w, _ = a.shape
mx = a.max(axis=2)
content = mx < 210          # dark text / red / teal edge / dark spines
whitepx = mx >= 250         # pure white (star fill / canvas)


def runs_of(mask, x0=0, x1=None):
    """Contiguous True-ranges of a 1-D bool mask (offset by x0)."""
    x1 = x1 if x1 is not None else len(mask)
    out, s = [], None
    for i, v in enumerate(mask[x0:x1], start=x0):
        if v and s is None:
            s = i
        if not v and s is not None:
            out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, x1 - 1))
    return out


def gaps(runs):
    return [runs[i + 1][0] - runs[i][1] - 1 for i in range(len(runs) - 1)]


# --- 1. fig-legend entries at text rows: content runs + entry gaps ----
for y in (328, 331, 334):
    r = runs_of(content[y], 40, 880)
    print(f"legend y{y} content runs: {r}")
    print(f"  gaps: {gaps(r)}")
# star white start vs ')' dark end around x495-540 at handle rows
y = 328
band = slice(490, 545)
dark = np.where(content[y, band])[0] + 490
wht = np.where(whitepx[y, band] & (a[y, band, 1] >= 250) & (np.arange(490, 545) >= 0))[0] + 490
# star white = white pixels INSIDE legend interior (not bg): bg is 238 not white
print(f"E3/E4 zone y{y}: dark cols {dark.min() if len(dark) else '-'}..{dark.max() if len(dark) else '-'} (list {dark.tolist()})")
# detect star white run: pixels ==255 white in x500-535
wh2 = [x for x in range(500, 540) if tuple(a[y, x]) == (255, 255, 255)]
print(f"  pure-white cols x500-539: {wh2}")
# E4 text end vs E5 handle start (x675-700)
z4 = slice(675, 710)
d4 = np.where(content[y, z4])[0] + 675
print(f"E4/E5 zone y{y}: content cols {d4.tolist()}")

# --- 2. z-axis slot: per-row content+colorbar at 3 rows -----------------
for y, tag in ((105, "label-only row (above bar)"), (172, "tick '60' row"), (205, "tick '45' row")):
    row = a[y]
    cont = np.where(content[y, 300:470])[0] + 300
    # colorbar = saturated color: max-min > 40
    sat = np.where((row[:, :].max(axis=1) - row[:, :].min(axis=1)) > 40)[0]
    sat = sat[(sat >= 300) & (sat <= 470)]
    print(f"z-row y{172 if tag.startswith('tick') else y} {tag}: content cols {runs_of(content[y], 300, 470)} sat cols {runs_of(np.isin(np.arange(w), sat), 300, 470)}")

# --- 3. colorbar tick text rows (audit: y118-134 / 154-170 / 191-207) --
for y0, y1, tag in ((118, 134, "cb tick1"), (154, 170, "cb tick2"), (191, 207, "cb tick3")):
    sub = content[y0:y1 + 1, 360:460]
    r = runs_of(sub.any(axis=0), 360, 460)
    # glyph heights per run
    hs = []
    for x0, x1 in r:
        rr = np.where(content[y0:y1 + 1, x0:x1 + 1].any(axis=1))[0]
        hs.append((x0, x1, int(rr.max() - rr.min() + 1)))
    print(f"{tag} y{y0}-{y1}: runs(x0,x1,height) {hs}")

# --- 4. C ylabel vs cb label gap: content columns y95-215 x415-470 -----
r = runs_of(content[95:215, :].any(axis=0), 415, 470)
print(f"cb-label/C-ylabel band cols x415-469: {r} -> gaps {gaps(r)}")

# --- 5. B2 legend border vs spine: exact RGB sweep y430 x514-534 -------
print("B2 y430 RGB:", [(x, tuple(int(v) for v in a[430, x])) for x in range(514, 535)])

# --- 6. right-edge driver: second-rightmost content columns ------------
colink = np.where((mx < 250).any(axis=0))[0]   # any non-white incl panel bg
top = colink.max()
print(f"non-white rightmost col {top}; rows {np.where(mx[:, top] < 250)[0].min()}-{np.where(mx[:, top] < 250)[0].max()}")
# columns 780..top with non-white, excluding legend band rows 318-343
mask = mx < 250
mask2 = mask.copy()
mask2[315:347, :] = False
cols2 = np.where(mask2.any(axis=0))[0]
print(f"rightmost non-white OUTSIDE legend band: {cols2.max()}")
