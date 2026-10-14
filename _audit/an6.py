from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)

WHITE = np.all(a >= 250, axis=2)
# exact header gray (117,117,117)
G = np.all(np.abs(a - np.array([117, 117, 117])) <= 20, axis=2)
# slate rule/line
S = np.all(np.abs(a - np.array([55, 71, 79])) <= 35, axis=2)

print("== rule rows (count in x600..1500 of slate, of gray) ==")
for y in range(182, 198):
    print(f" y={y} slate={int(S[y,600:1500].sum()):4d} gray={int(G[y,600:1500].sum()):4d} white={int(WHITE[y,600:1500].sum()):4d}")

print("\n== exact header ink bboxes (G mask) per cluster ==")
band = slice(184, 240)
colink = G[band].sum(axis=0)


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


cl = runs(colink > 0, 1)
merged = []
for s, e in cl:
    if merged and s - merged[-1][1] <= 10:
        merged[-1][1] = e
    else:
        merged.append([s, e])
for s, e in merged:
    if e - s < 15:
        continue
    sub = G[184:240, s:e + 1]
    ys, xs = np.nonzero(sub)
    print(f"  x {s}..{e} ink rows {184+ys.min()}..{184+ys.max()} n={len(ys)}")

print("\n== per-row exact gray ink in header band across whole width ==")
for y in range(186, 226):
    print(f" y={y} gray_total={int(G[y].sum()):4d}")

def dump(y0, y1, x0, x1, tag):
    print(f"\n== DUMP {tag} rows {y0}..{y1} cols {x0}..{x1} ==")
    def cls(c):
        r, g, b = c
        if r >= 250 and g >= 250 and b >= 250:
            return "."
        if abs(r - 55) <= 60 and abs(g - 71) <= 60 and abs(b - 79) <= 60 and max(r, g, b) < 170:
            return "S"  # slate
        if abs(r - 117) <= 45 and abs(g - 117) <= 45 and abs(b - 117) <= 45 and r < 200:
            return "g"  # gray text
        if r > 200 and g > 200 and b > 200:
            return "a"  # light gray AA
        return "?"
    print("      " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for y in range(y0, y1 + 1):
        row = "".join(cls(a[y, x]) for x in range(x0, x1 + 1))
        print(f" y={y} {row}")


dump(186, 240, 560, 600, "engine leg / ENGINE-E region")
dump(186, 232, 1505, 1530, "output leg / OUTPUT region")
