from PIL import Image
import numpy as np

P = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
a = np.asarray(Image.open(P).convert("RGB")).astype(int)
SLATE = np.all(np.abs(a - np.array([55, 71, 79])) <= 45, axis=2)
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


def cls(c):
    r, g, b = c
    if r >= 250 and g >= 250 and b >= 250:
        return "."
    if abs(r - 55) <= 45 and abs(g - 71) <= 45 and abs(b - 79) <= 45:
        return "S"
    if g > r and g > b and g > 90:
        return "G"
    if g > r and g > b:
        return "g"
    if r > 150 and 60 < g < 150 and b < 80:
        return "O"
    if r < 90 and g < 90 and b > 100:
        return "P"
    if r > 200 and g > 200 and b > 200:
        return "a"
    if r < 90 and g < 90 and b < 90:
        return "K"
    return "?"


print("== probes ==")
for (y, x) in [(386, 1040), (386, 1050), (350, 1050), (300, 1050), (370, 1052),
               (345, 1052), (392, 1052), (380, 1052), (340, 1052), (330, 1052),
               (320, 1052), (310, 1052), (396, 1037), (400, 1034)]:
    print(f"  rgb({x},{y}) = {a[y,x].tolist()}")

print("\n== x1030..1070 y330..400 class map ==")
print("     " + "".join(str((1030 + i) % 10) for i in range(41)))
for y in range(330, 401):
    print(f" y={y} " + "".join(cls(a[y, x]) for x in range(1030, 1071)))

print("\n== slate runs per row, x950..1190, y335..470 ==")
for y in range(335, 471):
    rr = runs(SLATE[y, 950:1191], 2)
    if rr:
        print(" y=%d" % y, [(950 + s, 950 + e) for s, e in rr])
