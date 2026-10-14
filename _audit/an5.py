from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
WHITE = np.all(a >= 250, axis=2)
SLATE = np.all(np.abs(a - np.array([55, 71, 79])) <= 45, axis=2)
GRAY = np.all(np.abs(a - np.array([117, 117, 117])) <= 40, axis=2)
# gray text but exclude light gray borders (192/239) -> 117 +/-40 covers 77..157, fine


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


# ---- header band ----
band = slice(185, 232)
colink = GRAY[band].sum(axis=0)
clusters = runs(colink > 0, 1)
# merge clusters separated by <=6 px (letters within a word)
merged = []
for s, e in clusters:
    if merged and s - merged[-1][1] <= 8:
        merged[-1][1] = e
    else:
        merged.append([s, e])
print("HEADER gray-ink column clusters (merged gap<=8):")
words = []
for s, e in merged:
    if e - s < 12:
        continue
    sub = GRAY[185:232, s:e + 1]
    ys, xs = np.nonzero(sub)
    print(f"  x {s}..{e} (w={e-s+1})  ink rows {185+ys.min()}..{185+ys.max()}")
    words.append((s, e, 185 + ys.min(), 185 + ys.max()))

# rule extent
srow = SLATE[186:192].sum(axis=0)
inx = np.nonzero(srow > 0)[0]
print("rule slate cols:", inx.min(), inx.max(), "rule rows: ", end="")
rr = [y for y in range(180, 200) if SLATE[y, 600:1500].sum() > 400]
print(rr)

# ---- legs ----
for (x0, x1, name, ybot) in [(574, 590, "engine leg", 290), (1510, 1526, "output leg", 350)]:
    print(f"--- {name} cols {x0}..{x1} rows 184..{ybot} ---")
    for y in range(184, ybot + 1):
        seg = SLATE[y, x0:x1 + 1]
        wseg = WHITE[y, x0:x1 + 1]
        gseg = GRAY[y, x0:x1 + 1]
        print(
            f"  y={y} slate={int(seg.sum())} white={int(wseg.sum())} grayink={int(gseg.sum())}"
            f" slatecols={[x0+i for i,v in enumerate(seg) if v]}"
        )
