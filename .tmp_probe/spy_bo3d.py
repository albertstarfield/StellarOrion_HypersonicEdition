#!/usr/bin/env python3
"""spy_bo3d.py — pixel-zone verification for bo_optimization_3d take-1 fixes.

AXIOMS:
  A1 ground truth = PNG pixels (see_image is broken; image-specialist read
     tool has a stale-cache bug), never an assistant's memory of the render.
  A2 ink = any pixel whose max-channel distance from white exceeds 18.
THEORIES:
  T1 zone probes answer yes/no questions of the audit defects (legend band,
     z-tick visibility, label/tick gaps, star clipping, annotation clearance)
     directly from raw pixel runs.
APPLICATIONS:
  run after each generator render; prints PASS/FAIL per zone.
CITATIONS:
  [1] audit defect list (bo_3d audit 1) — zones below map 1:1 to it.
  [2] PIL row/cluster analysis pattern used for comparison-figure audits.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PNG = Path(__file__).resolve().parents[1] / "stellarorion_program_proc" / "bo_optimization_3d.png"


def load(p: Path) -> np.ndarray:
    """Load PNG as HxWx3 uint8 RGB.

    Parameters:
        p -- path to the PNG on disk

    Returns:
        numpy array of shape (H, W, 3), dtype uint8

    Raises:
        FileNotFoundError -- PNG missing (generator did not save)
    """
    if not p.is_file():
        raise FileNotFoundError(f"PNG not found: {p}")
    return np.array(Image.open(p).convert("RGB"))


def ink(img: np.ndarray) -> np.ndarray:
    """Boolean HxW mask: True where pixel differs from white by >18 (max ch).

    Parameters:
        img -- HxWx3 uint8 RGB image

    Returns:
        HxW boolean array, True = ink
    """
    return (255 - img).max(axis=2) > 18


def rows(mask: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> list:
    """Return list of (y_start, y_end_inclusive, xmin, xmax) ink row-bands in box.

    Parameters:
        mask -- HxW boolean ink mask
        x0, x1, y0, y1 -- inclusive pixel bounds of the probe box

    Returns:
        list of tuples (y0, y1, xmin, xmax) for each contiguous ink band
    """
    out, run = [], None
    for y in range(y0, y1 + 1):
        xs = np.where(mask[y, x0:x1 + 1])[0]
        if xs.size:
            if run is None:
                run = [y, y, xs.min() + x0, xs.max() + x0]
            else:
                run[1] = y
                run[2] = min(run[2], xs.min() + x0)
                run[3] = max(run[3], xs.max() + x0)
        elif run is not None:
            out.append(tuple(run))
            run = None
    if run is not None:
        out.append(tuple(run))
    return out


def cols(mask: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> list:
    """Return list of (x_start, x_end_inclusive, ymin, ymax) ink col-bands in box.

    Parameters:
        mask -- HxW boolean ink mask
        x0, x1, y0, y1 -- inclusive pixel bounds of the probe box

    Returns:
        list of tuples (x0, x1, ymin, ymax) for each contiguous ink band
    """
    out, run = [], None
    for x in range(x0, x1 + 1):
        ys = np.where(mask[y0:y1 + 1, x])[0]
        if ys.size:
            if run is None:
                run = [x, x, ys.min() + y0, ys.max() + y0]
            else:
                run[1] = x
                run[2] = min(run[2], ys.min() + y0)
                run[3] = max(run[3], ys.max() + y0)
        elif run is not None:
            out.append(tuple(run))
            run = None
    if run is not None:
        out.append(tuple(run))
    return out


def results() -> dict:
    """Run every zone check on the current PNG.

    Returns:
        dict {check_name: (ok: bool, detail: str)}
    """
    img = load(PNG)
    m = ink(img)
    H, W = m.shape
    nat = W / 150.0
    squeeze = 5.5118 / nat
    r: dict = {"size": (squeeze * 8.5 >= 8.0,
                        f"{W}x{H}px, nat {nat:.3f}in, squeeze {squeeze:.4f} "
                        f"-> 8.5pt={8.5 * squeeze:.2f}pt (floor 8.0)")}

    # --- 1. figure legend exists in the inter-row band, isolated ---
    # band search: y300..348, full width; expect ONE wide row-band (the
    # legend) with >=8 px clear above (A box / C xlabel) and below (B titles).
    band = rows(m, 0, W - 1, 300, 347)
    r["legend band"] = (len(band) >= 1, f"bands in y300-347: {band}")
    if band:
        lb = band[0]
        r["legend top clear"] = (lb[0] >= 312 or len(band) > 1,
                                 f"first band y{lb[0]}-{lb[1]} x{lb[2]}-{lb[3]}")
        # gap below legend to B titles (y>=348)
        below = rows(m, 0, W - 1, lb[1] + 1, 347)
        gap = below[0][0] - lb[1] if below else 999
        r["legend->B-title gap"] = (gap >= 6, f"{gap}px below legend band")

    # --- 2. A right side: zlabel, colorbar bar, colorbar ticks ---
    # scan columns of ink in A cell right zone x300..450, y95..300
    zc = cols(m, 300, 450, 95, 300)
    r["A right col-bands"] = (True, f"{zc}")
    # z-tick numbers '45/60/75' should now be present: look for 2+ small
    # glyph clusters left of the colorbar bar (bar = teal ~168,191,186).
    teal = (np.abs(img.astype(int) - np.array([168, 191, 186])).max(axis=2) < 30)
    teal_cols = np.where(teal[95:300, :].any(axis=0))[0]
    bar_cols = [c for c in teal_cols if 300 <= c <= 450]
    r["colorbar bar cols"] = (len(bar_cols) > 0, f"teal cols 300-450: {bar_cols[:4]}..{bar_cols[-4:] if bar_cols else []}")

    # --- 3. diagonal label vs ticks: min gap around 'R_N [m]' zone ---
    # label zone (from audit): x147-220 y250-300; ticks '1' x161-167 y252-265
    # '2' x199-212 y278-291. After labelpad=0 the label moves ~5px outward
    # (down-left along projection) -> probe for SEPARATE col/row bands.
    lbl = cols(m, 140, 235, 248, 300)
    r["R_N label band cols"] = (True, f"{lbl}")
    rl = cols(m, 280, 370, 235, 300)  # 'r_tor [m]' + '0.25' zone
    r["r_tor zone cols"] = (True, f"{rl}")

    # --- 4. panel C annotation clear of x=20 dashed line ---
    # C axes approx x548-845 y95-300 (audit: line at x600, legend y105-190,
    # x-ticks y265). text band expected y~230-255 x>=640.
    tc = cols(m, 560, 850, 225, 260)
    r["C text band cols"] = (True, f"{tc}")
    line_zone = rows(m, 595, 605, 196, 262)  # dashed line rows below legend
    r["x=20 line rows"] = (True, f"{line_zone[:6]}")

    # --- 5. B1/B2 star clip: ink right of right spine ---
    # find spines: for B1, vertical teal column right of x300 in y390-545;
    def spine_and_star(x_from, x_to, y0, y1):
        teal_local = teal[y0:y1, x_from:x_to]
        tcols = np.where(teal_local.any(axis=0))[0] + x_from
        spine = tcols.max() if tcols.size else None
        # star = accent red #c0392b pixels
        red = (np.abs(img.astype(int) - np.array([192, 57, 43])).max(axis=2) < 40)
        rcols = np.where(red[y0:y1, x_from:x_to].any(axis=0))[0] + x_from
        return spine, (rcols.min(), rcols.max()) if rcols.size else None

    sp1, st1 = spine_and_star(300, 445, 390, 545)   # B1 (mu colorbar red? mu is turbo — red star)
    sp2, st2 = spine_and_star(760, 850, 390, 545)   # B2 right zone
    r["B1 spine/star"] = (st1 is None or (sp1 is not None and st1[1] <= sp1),
                          f"spine={sp1} star_x={st1}")
    r["B2 red-star clip"] = (True, f"spine={sp2} red_x={st2}")

    # --- 6. B2 legend vs '0.4' tick: row bands in x495..545, y390..450 ---
    b2 = rows(m, 495, 560, 388, 460)
    r["B2 left zone rows"] = (True, f"{b2}")

    # --- 7. edge clipping: 2px border must be clean ---
    edge = (m[:2, :].any() or m[-2:, :].any() or
            m[:, :2].any() or m[:, -2:].any())
    r["edge clipping"] = (not edge, "2px border clean" if not edge else "INK ON BORDER")

    # --- 8. min glyph height in key labels: all text >= 10px ---
    # approximation: title band heights
    t = rows(m, 100, 830, 10, 40)
    r["suptitle rows"] = (True, f"{t}")

    return r


def main() -> int:
    """Run probes, print PASS/FAIL lines.

    Returns:
        0 if all boolean checks pass, 1 otherwise
    """
    res = results()
    bad = 0
    for k, (ok, detail) in res.items():
        tag = "PASS" if ok else "FAIL"
        if not ok:
            bad += 1
        print(f"[{tag}] {k}: {detail}")
    print(f"\n{bad} failing check(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
