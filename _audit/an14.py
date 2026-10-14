from PIL import Image
import numpy as np
from scipy import ndimage

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
WHITE = np.all(a >= 250, axis=2)
NEARBLACK = ((a.max(axis=2) - a.min(axis=2)) < 25) & (a.mean(axis=2) < 110)
ORANGE = np.all(np.abs(a - np.array([232, 95, 20])) <= 30, axis=2)


def runs(mask, minlen=1):
    out = []
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


# 1 title
t = NEARBLACK[100:183, 250:1460]
ys, xs = np.nonzero(t)
ty0, ty1, tx0, tx1 = 100 + ys.min(), 100 + ys.max(), 250 + xs.min(), 250 + xs.max()
print("title ink y%d..%d x%d..%d ; rule top=186 -> gap=%d px" %
      (ty0, ty1, tx0, tx1, 186 - ty1 - 1))

# 2 feedback text (exclude vertical orange line x<600 and horizontal line y>=745)
f = ORANGE[600:746, 620:1105]
ys, xs = np.nonzero(f)
fy0, fy1, fx0, fx1 = 600 + ys.min(), 600 + ys.max(), 620 + xs.min(), 620 + xs.max()
# horizontal orange line rows
lrows = [y for y in range(740, 760) if ORANGE[y, 600:1200].sum() > 300]
print("feedback text bbox y%d..%d x%d..%d ; orange line rows=%s ; gap=%d px" %
      (fy0, fy1, fx0, fx1, lrows, (min(lrows) - fy1 - 1) if lrows else -1))

# 3 boxes: label fills
COLORS = {
    "lightblue": [229, 243, 253],
    "blue": [40, 113, 197],
    "orange": [232, 95, 20],
    "green": [63, 135, 66],
    "purple": [88, 39, 149],
}
print("\n== box border integrity (white runs >=3px inside border spans) ==")
for name, c in COLORS.items():
    m = np.all(np.abs(a - np.array(c)) <= 40, axis=2)
    lab, n = ndimage.label(m)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) < 500:
            continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        if y1 - y0 < 15 or x1 - x0 < 15:
            continue
        # scan candidate border rows: row at y0, y1 and rows in first/last 8 of bbox
        issues = []
        for y in list(range(y0, y0 + 6)) + list(range(y1 - 5, y1 + 1)):
            row = WHITE[y, x0:x1 + 1]
            for s, e in runs(row, 3):
                # ignore white regions outside actual shape: check fill present above/below
                inside = m[min(y + 2, a.shape[0] - 1), x0 + s] or m[max(y - 2, 0), x0 + s]
                if inside:
                    issues.append(("row", y, x0 + s, x0 + e))
        for x in list(range(x0, x0 + 6)) + list(range(x1 - 5, x1 + 1)):
            col = WHITE[y0:y1 + 1, x]
            for s, e in runs(col, 3):
                inside = m[y0 + s, min(x + 2, a.shape[1] - 1)] or m[y0 + s, max(x - 2, 0)]
                if inside:
                    issues.append(("col", x, y0 + s, y0 + e))
        print(" %-9s bbox y%d..%d x%d..%d  issues=%s" % (name, y0, y1, x0, x1, issues[:6]))

# 4 OpenFOAM top border
g = np.all(np.abs(a - np.array([63, 135, 66])) <= 40, axis=2)
lab, n = ndimage.label(g)
print("\ngreen components:")
for i in range(1, n + 1):
    ys, xs = np.nonzero(lab == i)
    if len(ys) < 500:
        continue
    print("  y%d..%d x%d..%d size=%d" % (ys.min(), ys.max(), xs.min(), xs.max(), len(ys)))

# 5 label glyph clusters (strict text only)
txt = ((np.abs(a - np.array([33, 33, 33])) <= 45).all(axis=2))
sub = txt[390:445, 955:1185]
ys, xs = np.nonzero(sub)
print("\nstrict label text bbox y%d..%d x%d..%d" % (390 + ys.min(), 390 + ys.max(),
                                                    955 + xs.min(), 955 + xs.max()))
rows = sorted(set(390 + int(v) for v in ys))
print(" rows:", rows[0], "..", rows[-1], "count", len(rows))
