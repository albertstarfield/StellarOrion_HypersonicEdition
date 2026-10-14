from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
SLATE = np.all(np.abs(a - np.array([55, 71, 79])) <= 45, axis=2)
WHITE = np.all(a >= 250, axis=2)
G = np.all(np.abs(a - np.array([117, 117, 117])) <= 25, axis=2)


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


print("== output leg: slate presence per row, x1500..1540 ==")
for y in range(186, 356, 1):
    s = SLATE[y, 1500:1541]
    rr = [(1500 + i, 1500 + j) for i, j in runs(s, 1)]
    if rr:
        print(f" y={y} slate runs {rr}")

print("\n== letter segmentation ==")


def segments(y0, y1, x0, x1, gap=4, mask=None):
    m = G[y0:y1 + 1, x0:x1 + 1] if mask is None else mask[y0:y1 + 1, x0:x1 + 1]
    col = m.sum(axis=0)
    rr = runs(col > 0, 1)
    merged = []
    for s, e in rr:
        if merged and s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = []
    for s, e in merged:
        sub = m[:, s:e + 1]
        ys, xs = np.nonzero(sub)
        out.append((x0 + s, x0 + e, y0 + ys.min(), y0 + ys.max(), int(sub.sum())))
    return out


print("ENGINE letters:", segments(189, 220, 560, 735, 4))
print("OUTPUT letters:", segments(189, 220, 1428, 1610, 4))
print("CORE letters:", segments(189, 220, 430, 560, 4))
print("INPUT letters:", segments(189, 222, 130, 270, 4))
print("SOLVERS letters:", segments(189, 222, 818, 1015, 4))
print("ML MODELS letters:", segments(189, 222, 1110, 1375, 4))
