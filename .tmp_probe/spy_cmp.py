"""Pixel-verify optimization_comparison.png after tick/legend fixes.

AXIOMS: a text collision = two glyph sets sharing one 8-connected dark
component (the method the 2026-10-08 image audit used). Panel geometry is
unchanged by the fix, so the audit's measured zones still locate the same
labels.

THEORIES: (1) two properly spaced labels are >=2 separate components in
their former blob zone; (2) an opaque upper-left legend shows the full
'Flown (HIAD_custom.surf)' glyph run (>=16 glyph-like components); (3) a
regression back to a merged blob yields <2 components in a tick zone.

APPLICATION: prints per-zone component tables (x/y extents + area) for
human review and exits 1 on any regression, 2 if the PNG is unreadable.
No value is asserted from memory: every verdict comes from these pixels.
"""
import sys

from PIL import Image
import numpy as np

PNG = sys.argv[1] if len(sys.argv) > 1 else (
    "/Users/albertstarfield/Documents/NeoSchool14/for_someone/"
    "StellarOrion_HypersonicEdition/stellarorion_program_proc/"
    "optimization_comparison.png")


def load_dark(path):
    """Return (grayscale array, boolean dark mask) for a PNG.

    Parameters:
        path (str): filesystem path to the rendered figure.
    Returns:
        tuple: (numpy uint8 array, numpy bool mask of pixels with L < 128).
    Raises:
        SystemExit(2): if the file cannot be opened as an image.
    """
    try:
        im = Image.open(path).convert("L")
    except OSError as exc:  # noqa: BLE001 - surface exact cause, never silent
        print(f"ERROR: cannot open {path}: {exc}")
        raise SystemExit(2) from exc
    arr = np.asarray(im)
    return arr, arr < 128


def components(mask):
    """Label 8-connected components of a boolean mask (iterative BFS).

    Parameters:
        mask (numpy bool 2-D): dark-pixel mask.
    Returns:
        list: (x0, y0, x1, y1, area) per component with area >= 4 px.
    """
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        minx = maxx = x0
        miny = maxy = y0
        area = 0
        while stack:
            y, x = stack.pop()
            area += 1
            if x < minx:
                minx = x
            if x > maxx:
                maxx = x
            if y < miny:
                miny = y
            if y > maxy:
                maxy = y
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < h and 0 <= nx < w
                            and mask[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        if area >= 4:
            out.append((minx, miny, maxx, maxy, area))
    return out


def main():
    """Run all zone checks; return process exit code (0 pass, 1 fail)."""
    arr, dark = load_dark(PNG)
    print(f"image {arr.shape[1]}x{arr.shape[0]}  dark_px={int(dark.sum())}")

    edge = bool(dark[:3, :].any() or dark[-3:, :].any()
                or dark[:, :3].any() or dark[:, -3:].any())
    print("edge-clip ink:", "FAIL" if edge else "none")
    fail = edge

    # Zones measured by the 2026-10-08 audit (composition unchanged by fix).
    zones = {
        "L xtick": (170, 300, 320, 340),    # old merged blob x218-255 y313-331
        "R xtick": (630, 300, 790, 340),    # old merged blob x689-727
        "L ytick": (255, 275, 315, 330),    # old 0<->-2 merge x284-296
        "R ytick": (725, 275, 785, 330),    # old merge x755-767
        "L legend": (0, 180, 330, 285),     # old box x5-305 y236-274
    }
    for name, (zx0, zy0, zx1, zy1) in zones.items():
        sub = dark[zy0:zy1, zx0:zx1]
        comps = [c for c in components(sub)
                 if c[4] >= 6 and (c[2] - c[0]) <= 60 and (c[3] - c[1]) <= 30]
        print(f"\n{name} zone ({zx0},{zy0})-({zx1},{zy1}): {len(comps)} comps")
        for (x0, y0, x1, y1, area) in sorted(comps, key=lambda c: c[0]):
            print(f"   x{x0 + zx0}-{x1 + zx0} y{y0 + zy0}-{y1 + zy0} area{area}")
        if name.endswith("xtick") or name.endswith("ytick"):
            if len(comps) < 2:
                print(f"   REGRESSION: {name} still merged (<2 comps)")
                fail = True
        if name == "L legend":
            glyphs = [c for c in comps
                      if 4 <= (c[3] - c[1]) <= 22 and (c[2] - c[0]) <= 22]
            print(f"   glyph-like: {len(glyphs)}")
            if len(glyphs) < 16:
                print("   REGRESSION: legend text still occluded (<16 glyphs)")
                fail = True

    print("\nVERDICT:", "FAIL" if fail else "PASS")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
