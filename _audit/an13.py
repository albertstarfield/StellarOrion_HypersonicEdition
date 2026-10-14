from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
im = Image.open(P).convert("RGB")
a = np.asarray(im).astype(int)
W, H = im.size
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


def bbox(mask, y0, y1, x0, x1):
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    if len(ys) == 0:
        return None
    return (y0 + ys.min(), y0 + ys.max(), x0 + xs.min(), x0 + xs.max())


# --- label "surface data" ---
lab = bbox(NEARBLACK, 392, 445, 955, 1185)
print("surface-data label ink bbox y%d..%d x%d..%d" % lab)
print(" label ink rows:", sorted(set(int(v) for v in np.nonzero(NEARBLACK[392:445, 955:1185])[0] + 392)))

# label glyph columns (letters)
sub = NEARBLACK[lab[0]:lab[1] + 1, 955:1185]
rr = runs(sub.sum(axis=0) > 0, 1)
merged = []
for s, e in rr:
    if merged and s - merged[-1][1] <= 3:
        merged[-1][1] = e
    else:
        merged.append([s, e])
print(" label glyph clusters:", [(955 + s, 955 + e) for s, e in merged])

# white holes inside label glyphs? count white pixels strictly inside ink rows between clusters
print(" white px inside label bbox:", int(WHITE[lab[0]:lab[1] + 1, lab[2]:lab[3] + 1].sum()))

# --- OpenFOAM box top border ---
g = np.all(np.abs(a - np.array([63, 135, 66])) <= 45, axis=2)
print("\nOpenFOAM region green rows (x820..1050):")
for y in range(415, 450):
    rr = runs(g[y, 820:1055], 3)
    if rr:
        print("  y=%d" % y, [(820 + s, 820 + e) for s, e in runs(g[y, 820:1055], 1)])

# --- title bbox vs rule ---
title = bbox(NEARBLACK, 60, 180, 100, 1550)
print("\ntitle bbox y%d..%d x%d..%d" % title)
print("rule top row = 186 (AA 186, solid 187) -> title-rule gap = %d px" % (186 - title[1] - 1))

# --- feedback label vs orange line ---
fb = bbox(ORANGE, 620, 745, 500, 1100)
print("orange feedback TEXT bbox y%d..%d x%d..%d" % fb)
# orange line rows (horizontal segment)
print("orange rows 700..790 with wide runs:")
for y in range(700, 795):
    rr = runs(ORANGE[y, 450:1250], 30)
    if rr:
        print("  y=%d" % y, [(450 + s, 450 + e) for s, e in rr])

# --- legend rows ---
print("\nlegend near-black ink per row y760..910 (x300..1400):")
prev = None
for y in range(755, 915):
    n = int(NEARBLACK[y, 300:1400].sum())
    if n != prev:
        print("  y=%d count=%d" % (y, n))
        prev = n
# legend glyph clusters per band
for (y0, y1) in [(765, 800), (800, 845), (845, 890), (885, 915)]:
    sub = NEARBLACK[y0:y1, 300:1400]
    rr = runs(sub.sum(axis=0) > 0, 1)
    merged = []
    for s, e in rr:
        if merged and s - merged[-1][1] <= 6:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    ys, xs = np.nonzero(sub)
    if len(ys):
        print(" band y%d-%d ink y%d..%d clusters:" % (y0, y1, y0 + ys.min(), y0 + ys.max()),
              [(300 + s, 300 + e) for s, e in merged])

# --- canvas edge ink ---
edge = {}
edge['left x0..3'] = int(NEARBLACK[:, 0:4].sum())
edge['right x-4..'] = int(NEARBLACK[:, -4:].sum())
edge['top y0..3'] = int(NEARBLACK[0:4, :].sum())
edge['bottom y-4..'] = int(NEARBLACK[-4:, :].sum())
print("\nedge ink:", edge)
for name, sl in [("L", (slice(None), slice(0, 6))), ("R", (slice(None), slice(-6, None))),
                 ("T", (slice(0, 6), slice(None))), ("B", (slice(-6, None), slice(None)))]:
    ys, xs = np.nonzero(NEARBLACK[sl])
    if len(ys):
        print(" edge", name, "dark px:", len(ys))
