from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
STRICT = np.all(np.abs(a - np.array([55, 71, 79])) <= 25, axis=2)
DARK = a.mean(axis=2) < 110
WHITE = np.all(a >= 250, axis=2)


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


# label ink bbox in region
reg = DARK[380:450, 950:1200]
ys, xs = np.nonzero(reg)
print("dark(label region) bbox y", 380 + ys.min(), 380 + ys.max(), "x",
      950 + xs.min(), 950 + xs.max())
print("label ink rows:", sorted(set(380 + int(v) for v in ys))[:5], "...",
      sorted(set(380 + int(v) for v in ys))[-5:])

print("\nstrict slate runs x950-1200, y370-500 (len>=3):")
for y in range(370, 501):
    rr = runs(STRICT[y, 950:1201], 3)
    if rr:
        print("  y=%d" % y, [(950 + s, 950 + e) for s, e in rr])

print("\nASCII map x1040..1120, y370..500 (# strict slate, o dark text, * white/other nonwhite)")
print("      " + "".join(str((1040 + i) // 10 % 10) for i in range(80)))
for y in range(370, 501):
    row = ""
    for x in range(1040, 1120):
        if STRICT[y, x]:
            row += "#"
        elif DARK[y, x]:
            row += "o"
        elif WHITE[y, x]:
            row += "."
        else:
            row += "-"
    print("y=%3d %s" % (y, row))
