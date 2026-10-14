from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
m = a.mean(axis=2)
rng = a.max(axis=2) - a.min(axis=2)
NEUTRAL = (rng <= 4) & (m >= 95) & (m <= 145)


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


def letters(y0, y1, x0, x1, gap=1):
    sub = NEUTRAL[y0:y1, x0:x1]
    rr = runs(sub.sum(axis=0) > 0, 1)
    merged = []
    for s, e in rr:
        if merged and s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = []
    for s, e in merged:
        piece = sub[:, s:e + 1]
        ys, xs = np.nonzero(piece)
        out.append(dict(x0=x0 + s, x1=x0 + e, y0=y0 + int(ys.min()),
                        y1=y0 + int(ys.max()), ink=int(piece.sum())))
    return out


eng = letters(189, 220, 560, 735)
out = letters(189, 220, 1425, 1606)
print("ENGINE letters:")
for L in eng:
    print("  ", L)
print("OUTPUT letters:")
for L in out:
    print("  ", L)


def mask_of(L):
    return NEUTRAL[L["y0"]:L["y1"] + 1, L["x0"]:L["x1"] + 1]


# compare first and last E of ENGINE
e1, e2 = eng[0], eng[-1]
m1, m2 = mask_of(e1), mask_of(e2)
if m1.shape == m2.shape:
    print("\nE1 vs E2 shape", m1.shape, "ink", e1["ink"], e2["ink"],
          "identical:", bool((m1 == m2).all()),
          "diff px:", int((m1 ^ m2).sum()))
else:
    print("\nE shapes differ", m1.shape, m2.shape, "ink", e1["ink"], e2["ink"])

# OUTPUT T's: letters with width<40 and centered stem -> pick by width
Ts = [L for L in out if (L["x1"] - L["x0"]) < 45]
print("\nOUTPUT narrow letters (candidates T):", [(L["x0"], L["x1"], L["ink"]) for L in Ts])
if len(Ts) >= 2:
    t1, t2 = Ts[0], Ts[-1]
    a1, a2 = mask_of(t1), mask_of(t2)
    if a1.shape == a2.shape:
        print("T1 vs T2 shape", a1.shape, "ink", t1["ink"], t2["ink"],
              "identical:", bool((a1 == a2).all()), "diff px:", int((a1 ^ a2).sum()))
    else:
        print("T shapes differ", a1.shape, a2.shape)

# slate pixels overlapping neutral glyph ink
SLATE = np.all(np.abs(a - np.array([55, 71, 79])) <= 20, axis=2)
for nm, L in [("E1", eng[0]), ("E2", eng[-1]), ("OUTPUT-l1", out[0])]:
    ys, xs = np.nonzero(SLATE[L["y0"]:L["y1"] + 1, L["x0"]:L["x1"] + 1])
    if len(ys):
        print(nm, "strict-slate px inside bbox rows:",
              sorted(set(L["y0"] + int(v) for v in ys)),
              "cols:", sorted(set(L["x0"] + int(v) for v in xs)))
    else:
        print(nm, "no strict slate inside bbox")

# does leg slate sit on white (counter) rows 192-194?
print("\nENGINE leg col x578-583 rows 188..240:")
for y in range(188, 241):
    seg = [(x, a[y, x].tolist()) for x in range(577, 585)]
    cls = "".join("S" if abs(int(a[y, x][0]) - 55) <= 25 and abs(int(a[y, x][2]) - 79) <= 25
                  else ("W" if a[y, x].min() >= 250 else "g") for x in range(577, 585))
    print("  y=%d %s" % (y, cls))
