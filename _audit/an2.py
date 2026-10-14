from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
im = Image.open(P).convert("RGB")
a = np.asarray(im).astype(int)
H, W, _ = a.shape

WHITE = np.all(a >= 250, axis=2)


def runs(mask, minlen=1):
    """Return list of (start, end_exclusive) runs of True in a 1-D bool array."""
    out = []
    i = 0
    n = len(mask)
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


def row_report(y0, y1, x0, x1, label, minrun=3):
    print(f"--- {label}: rows {y0}-{y1}, cols {x0}-{x1} ---")
    anyfail = False
    for y in range(y0, y1 + 1):
        w = WHITE[y, x0:x1 + 1]
        rr = runs(w, minrun)
        nwhite = int(w.sum())
        print(f"  y={y:4d} white={nwhite:4d} runs>={minrun}={rr}")
        if rr:
            anyfail = True
    return anyfail


# ---------- 1. CadQuery parallelogram top border ----------
row_report(214, 250, 120, 280, "N1 CadQuery top border region", 3)

# find exact CadQuery box extents
def box_extent(color, tol, region=None):
    m = np.all(np.abs(a - np.array(color)) <= tol, axis=2)
    if region:
        y0, y1, x0, x1 = region
        mm = np.zeros_like(m)
        mm[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
        m = mm
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return None
    return ys.min(), ys.max(), xs.min(), xs.max()


print("lightblue box bbox:", box_extent([229, 243, 253], 6, (200, 400, 100, 340)))
print("green SPARTA bbox:", box_extent([63, 135, 66], 8, (200, 420, 780, 1060)))
print("orange PINN bbox:", box_extent([232, 95, 20], 8, (200, 400, 1050, 1450)))
print("blue engine bbox:", box_extent([40, 113, 197], 8, (250, 650, 380, 780)))
print("purple ParaView bbox:", box_extent([88, 39, 149], 8, (300, 600, 1440, 1650)))
