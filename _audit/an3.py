from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
H, W, _ = a.shape
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


def show(y0, y1, x0, x1, minlen=3, tag=""):
    print(f"=== {tag} rows {y0}-{y1} cols {x0}-{x1} (run coords are absolute x) ===")
    for y in range(y0, y1 + 1):
        w = WHITE[y, x0:x1 + 1]
        rr = [(x0 + s, x0 + e) for s, e in runs(w, minlen)]
        nw = int(w.sum())
        # summarize: first/last non-white in the window
        nz = np.nonzero(~w)[0]
        span = f"{x0+nz[0]}..{x0+nz[-1]}" if len(nz) else "-"
        print(f" y={y:4d} white={nw:4d} firstlast_nonwhite={span} runs>={minlen}={rr}")


# CadQuery box full width
show(216, 238, 95, 350, 3, "N1 CadQuery top")
print()
# Determine fill bbox of CadQuery only
m = np.all(np.abs(a - np.array([229, 243, 253])) <= 6, axis=2)
sub = m[200:340, 80:360]
ys, xs = np.nonzero(sub)
print("CadQuery fill bbox y", ys.min() + 200, ys.max() + 200, "x", xs.min() + 80, xs.max() + 80)
# border color sample around top edge
for y in range(220, 234):
    row = a[y, 95:351]
    # count of gray border-ish
    print(y, "colors@x150,x200,x250,x300:", a[y, 150], a[y, 200], a[y, 250], a[y, 300])
