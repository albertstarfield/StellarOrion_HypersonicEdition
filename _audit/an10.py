from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
SLATE = np.all(np.abs(a - np.array([55, 71, 79])) <= 45, axis=2)
WHITE = np.all(a >= 250, axis=2)
G = np.all(np.abs(a - np.array([117, 117, 117])) <= 25, axis=2)
DARK = np.all(a <= 60, axis=2)


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


def seg(y0, y1, x0, x1, mask, gap=2):
    m = mask[y0:y1 + 1, x0:x1 + 1]
    rr = runs(m.sum(axis=0) > 0, 1)
    merged = []
    for s, e in rr:
        if merged and s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    res = []
    for s, e in merged:
        sub = m[:, s:e + 1]
        ys, xs = np.nonzero(sub)
        res.append((x0 + s, x0 + e, y0 + int(ys.min()), y0 + int(ys.max()), int(sub.sum())))
    return res


print("ENGINE letters gap2:", seg(189, 220, 560, 735, G, 2))
print("OUTPUT letters gap2:", seg(189, 220, 1428, 1610, G, 2))

# slate inside each letter bbox
for name, x0, x1 in [("ENGINE", 560, 735), ("OUTPUT", 1428, 1610)]:
    print(f"-- {name}: slate inside letter bboxes --")
    for (s, e, t, b, cnt) in seg(189, 220, x0, x1, G, 2):
        sub = SLATE[189:221, s:e + 1]
        ys, xs = np.nonzero(sub)
        print(f"   x{s}-{e} ink={cnt} slate_px={sub.sum()} "
              f"slate_rows={(sorted(set(189 + int(v) for v in ys)) if sub.sum() else [])}")

print("\n== N4 corner dump: colors y386..400, x1028..1060 ==")
for y in range(386, 401):
    row = ""
    for x in range(1028, 1061):
        c = a[y, x]
        if c[0] >= 250 and c[1] >= 250 and c[2] >= 250:
            ch = "."
        elif abs(c[0] - 55) <= 45 and abs(c[1] - 71) <= 45 and abs(c[2] - 79) <= 45:
            ch = "S"
        elif abs(c[0] - 63) <= 40 and abs(c[1] - 135) <= 40 and abs(c[2] - 66) <= 40:
            ch = "G"
        elif int(c.mean()) < 90:
            ch = "K"
        elif int(c.mean()) < 245:
            ch = "a"
        else:
            ch = "."
        row += ch
    print(f" y={y} {row}")

print("\n== SPARTA full bbox (green + its stroke) ==")
sub = a[220:410, 760:1070]
gm = (np.abs(sub - np.array([63, 135, 66])) <= 45).all(axis=2)
ys, xs = np.nonzero(gm)
print(" green fill y", 220 + ys.min(), 220 + ys.max(), "x", 760 + xs.min(), 760 + xs.max())
