from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
m = a.mean(axis=2)

# E1 vs E2 aligned diff (search shift)
E1 = m[189:219, 564:592]
E2 = m[189:219, 701:729]
best = None
for dx in range(-4, 5):
    for dy in range(-3, 4):
        A = m[189 + dy:219 + dy, 564 + dx:592 + dx]
        B = m[189:219, 701:729]
        d = np.abs(A - B)
        s = d.mean()
        if best is None or s < best[0]:
            best = (s, dx, dy)
print("best E1->E2 shift dx,dy =", best[1:], "mean abs diff", round(best[0], 2))
dx, dy = best[1], best[2]
A = m[189 + dy:219 + dy, 564 + dx:592 + dx]
B = m[189:219, 701:729]
inkA = A < 160
inkB = B < 160
print("E1 ink px", int(inkA.sum()), "E2 ink px", int(inkB.sum()))
print("E2 ink but E1 white(>=250):", int(((B < 160) & (A >= 250)).sum()))
print("E2 ink but E1 slate(60..90):", int(((B < 160) & (A > 55) & (A < 95)).sum()))

# T1 vs T2
best = None
for dx in range(-5, 6):
    for dy in range(-3, 4):
        A = m[189 + dy:219 + dy, 1490 + dx:1519 + dx]
        B = m[189:219, 1573:1602]
        s = np.abs(A - B).mean()
        if best is None or s < best[0]:
            best = (s, dx, dy)
print("\nbest T1->T2 shift dx,dy =", best[1:], "mean abs diff", round(best[0], 2))
dx, dy = best[1], best[2]
A = m[189 + dy:219 + dy, 1490 + dx:1519 + dx]
B = m[189:219, 1573:1602]
print("T1 ink", int((A < 160).sum()), "T2 ink", int((B < 160).sum()))
print("T2 ink but T1 white:", int(((B < 160) & (A >= 250)).sum()))
print("T2 ink but T1 slate(55..95):", int(((B < 160) & (A > 55) & (A < 95)).sum()))

# exact RGB where output leg meets T1
print("\nT1 x1508..1522 RGB means, y189..197")
for y in range(189, 198):
    print(" y=%d " % y + " ".join("%3d" % int(m[y, x]) for x in range(1508, 1523)))
print("   rgb at (1516,192)=", a[192, 1516].tolist(), " (1516,193)=", a[193, 1516].tolist(),
      " (1514,192)=", a[192, 1514].tolist())
