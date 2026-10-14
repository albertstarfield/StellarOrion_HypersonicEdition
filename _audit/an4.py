from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
WHITE = np.all(a >= 250, axis=2)
NEARWHITE = np.all(a >= 245, axis=2)
SLATE = np.all(np.abs(a - np.array([55, 71, 79])) <= 30, axis=2)


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


def show(y0, y1, x0, x1, minlen=3, tag=""):
    print(f"=== {tag} rows {y0}-{y1} cols {x0}-{x1} ===")
    for y in range(y0, y1 + 1):
        w = WHITE[y, x0:x1 + 1]
        rr = [(x0 + s, x0 + e) for s, e in runs(w, minlen)]
        nw = int(w.sum())
        nz = np.nonzero(~w)[0]
        span = f"{x0+nz[0]}..{x0+nz[-1]}" if len(nz) else "-"
        print(f" y={y:4d} white={nw:4d} nonwhite_span={span} wruns>={minlen}={rr}")


print("### row223 color samples")
for x in [90, 95, 100, 105, 110, 120, 129, 270, 300, 330, 340, 345, 350, 355, 360]:
    print("  x", x, a[223, x], "| y229:", a[229, x])
print()
print("### row 224 extent of non-white across wide window")
for y in [223, 224, 228, 229]:
    nz = np.nonzero(~WHITE[y, 0:500])[0]
    print(" y", y, "nonwhite x range", nz.min(), nz.max(), "count", len(nz))

# ---------- N2 SPARTA top ----------
show(228, 244, 790, 1070, 3, "N2 SPARTA top")
print()
# ---------- N3 PINN top ----------
show(234, 250, 1060, 1430, 3, "N3 PINN top")
print()
# ---------- N4 SPARTA bottom ----------
show(380, 398, 940, 1075, 3, "N4 SPARTA bottom/corner")
print()
# ---------- N5 rule ----------
print("=== N5 rule rows 183-192, cols 575-1522 : white columns per row ===")
for y in range(182, 194):
    w = WHITE[y, 575:1523]
    rr = [(575 + s, 575 + e) for s, e in runs(w, 1)]
    big = [(575 + s, 575 + e) for s, e in runs(w, 3)]
    sl = int(SLATE[y, 575:1523].sum())
    print(f" y={y} slate={sl:4d} white={int(w.sum()):4d} all_wruns={rr} runs>=3={big}")
