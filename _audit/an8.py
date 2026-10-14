from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)


def cls(c):
    r, g, b = c
    if r >= 248 and g >= 248 and b >= 248:
        return "."
    if abs(r - 55) <= 55 and abs(g - 71) <= 55 and abs(b - 79) <= 55 and max(r, g, b) < 165:
        return "S"
    if abs(r - 117) <= 25 and abs(g - 117) <= 25 and abs(b - 117) <= 25:
        return "g"
    if max(r, g, b) < 70:
        return "K"
    if r > 200 and g > 200 and b > 200:
        return "a"
    return "?"


print("== rule extent at text-free columns ==")
for x in (760, 770, 1410, 1420, 1055, 470, 800):
    col = [(y, tuple(int(v) for v in a[y, x])) for y in range(184, 197)]
    print(" x=", x, col)

print("\n== OUTPUT dump ==")
x0, x1 = 1428, 1608
print("      " + "".join(str((x // 10) % 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
for y in range(186, 222):
    print(f" y={y} " + "".join(cls(a[y, x]) for x in range(x0, x1 + 1)))
