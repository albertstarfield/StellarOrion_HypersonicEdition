from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)


def cls(c):
    r, g, b = c
    if r >= 248 and g >= 248 and b >= 248:
        return "."
    # slate-ish dark blue-gray
    if abs(r - 55) <= 55 and abs(g - 71) <= 55 and abs(b - 79) <= 55 and max(r, g, b) < 165:
        return "S"
    if abs(r - 117) <= 25 and abs(g - 117) <= 25 and abs(b - 117) <= 25:
        return "g"  # exact header gray
    if max(r, g, b) < 70:
        return "K"  # near-black text
    if r > 200 and g > 200 and b > 200:
        return "a"
    return "?"


def dump(y0, y1, x0, x1, tag, step=1):
    print(f"== {tag}: rows {y0}..{y1} cols {x0}..{x1} ==")
    print("      " + "".join(str((x // 10) % 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
    print("      " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for y in range(y0, y1 + 1, step):
        print(f" y={y} " + "".join(cls(a[y, x]) for x in range(x0, x1 + 1)))


dump(186, 222, 566, 732, "ENGINE word (E N G I N E)")
print()
dump(186, 222, 1431, 1606, "OUTPUT word")
print()
print("== RGB probe y188..196 at arm/leg columns ==")
for y in range(188, 197):
    print(" y", y, [(x, tuple(a[y, x])) for x in (570, 576, 578, 580, 582, 584, 586, 590, 592)])
