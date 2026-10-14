"""Final consolidated re-verification of both flowcharts.

Re-derives every number in the audit report from the rasters in one pass:
label extents (including fragments hidden under graphics), gaps to box
border/fill/text, gaps to arrow ink (anti-alias-inclusive colour tests),
pairwise label gaps, OCR on graphic-blanked crops, and glyph heights with
tittles separated. Prints a compact table used for the written report.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from probe_common import (
    EDGE_COLORS,
    FILL_COLORS,
    ORANGE,
    SLATE,
    color_mask,
    components,
    load,
    min_gap,
    ocr_multi,
    pts_of,
    text_mask,
)
from scipy import ndimage

FIGDIR = ("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/"
          "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/")
OUT = ("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/"
       "stellarorion_program_proc/.pixaudit")


def orangeish(a: np.ndarray) -> np.ndarray:
    """Orange feedback ink INCLUDING anti-aliased edges.

    Test: red excess over blue >= 40 with red >= 150. White, INK and slate
    all fail it; every orange blend (line core #E65100 and its AA ramp)
    passes.
    :param a: HxWx3 int array.
    :returns: HxW bool mask.
    """
    return ((a[..., 0] - a[..., 2]) >= 40) & (a[..., 0] >= 150)


def label_mask(a, tm, box, band=None):
    """IN text mask restricted to a window, keeping all fragments.

    :param a: image array (unused except for shape via tm).
    :param tm: text mask.
    :param box: (x0,y0,x1,y1) window.
    :param band: optional (y0,y1) to also restrict rows.
    :returns: HxW bool mask.
    """
    m = np.zeros(tm.shape, bool)
    x0, y0, x1, y1 = box
    if band:
        m[max(0, band[0]):band[1], max(0, x0):x1 + 1] = True
    else:
        m[max(0, y0):y1 + 1, max(0, x0):x1 + 1] = True
    return tm & m


def audit(path, transforms, labels, tag):
    """Audit one figure.

    :param path: PNG path.
    :param transforms: dict with X/Y callables and fit constants.
    :param labels: list of (name, xd, yd, window, band) tuples.
    :param tag: short prefix for saved crops.
    :returns: list of per-label dict results.
    """
    a = load(path)
    H, W = a.shape[:2]
    X, Y = transforms["X"], transforms["Y"]
    tm = text_mask(a)
    fill_raw = color_mask(a, FILL_COLORS, tol=6)
    fills = sorted(components(fill_raw, 20000), key=lambda c: c[4])
    fill = np.zeros((H, W), bool)
    for c in fills:
        fill[c[1]:c[3] + 1, c[0]:c[2] + 1] = True
    edge = color_mask(a, EDGE_COLORS, tol=6)
    border = edge & ndimage.binary_dilation(fill, iterations=6)
    white = (a >= 246).all(axis=2)
    box_text = np.zeros((H, W), bool)
    for c in fills:
        x0, y0, x1, y1 = c[:4]
        box_text[y0 + 8:y1 - 7, x0 + 8:x1 - 7] = white[y0 + 8:y1 - 7, x0 + 8:x1 - 7]
    box_text |= tm & ndimage.binary_erosion(fill, iterations=6)

    slate = color_mask(a, [SLATE], tol=4)
    org = orangeish(a) if tag == "solver" else np.zeros((H, W), bool)
    arrow_core = slate | (color_mask(a, [ORANGE], tol=4) if tag == "solver"
                          else np.zeros((H, W), bool))
    arrow_vis = slate | org            # AA-inclusive for collision numbers
    box_zone = np.zeros((H, W), bool)
    for c in fills:
        x0, y0, x1, y1 = c[:4]
        box_zone[max(0, y0 - 8):y1 + 9, max(0, x0 - 8):x1 + 9] = True
    arrow_vis = arrow_vis & ~box_zone & ~(np.zeros((H, W), bool)
                                          if tag != "solver"
                                          else _legend(H, W))

    results = []
    masks = {}
    for name, xd, yd, win, band in labels:
        masks[name] = label_mask(a, tm, win, band)
    for name, xd, yd, win, band in labels:
        m = masks[name]
        pts = pts_of(m)
        x0, y0 = int(pts[:, 0].min()), int(pts[:, 1].min())
        x1, y1 = int(pts[:, 0].max()), int(pts[:, 1].max())
        # label windows must not hide their own arrow ink: exclude them only
        # for OTHER labels' arrow measurement
        arrow_here = arrow_vis.copy()
        for on, om in masks.items():
            if on == name:
                continue
            o_pts = pts_of(om)
            arrow_here[max(0, o_pts[:, 1].min() - 10):o_pts[:, 1].max() + 11,
                       max(0, o_pts[:, 0].min() - 10):o_pts[:, 0].max() + 11] = False
        g5 = components(m, 5)
        bodies = [c for c in g5 if (c[3] - c[1] + 1) >= 10]
        tittles = [c for c in g5 if (c[3] - c[1] + 1) < 10]
        groups = int(ndimage.label(ndimage.binary_dilation(m, iterations=12))[1])
        # OCR on graphic-blanked crop
        pad = 8
        sy0, sx0 = max(0, y0 - pad), max(0, x0 - pad)
        stm = tm[sy0:y1 + pad + 1, sx0:x1 + pad + 1]
        cleaned = np.where(stm, 0, 255).astype(np.uint8)  # 2-D: 0=text, 255=bg
        cp = f"{OUT}/{tag}_{name.replace(' ', '_')}_clean.png"
        Image.fromarray(cleaned).save(cp)
        ocrs = ocr_multi(cp, psms=(7, 13, 6, 8))
        raw_crop = f"{OUT}/{tag}_{name.replace(' ', '_')}.png"
        Image.fromarray(a[sy0:y1 + pad + 1, sx0:x1 + pad + 1].astype(np.uint8)).save(raw_crop)
        r = {
            "name": name, "data": [xd, yd],
            "bbox": [x0, y0, x1, y1],
            "glyphs_area5": len(g5),
            "groups_dil12": groups,
            "gap_border": round(min_gap(pts, border), 1),
            "gap_fill": round(min_gap(pts, fill), 1),
            "gap_box_text": round(min_gap(pts, box_text), 1),
            "gap_arrow_visible": round(min_gap(pts, arrow_vis), 1),
            "gap_arrow_core": round(min_gap(pts, arrow_core), 1),
            "overlap_arrow_px": int((m & arrow_core).sum()),
            "gaps_other_labels": {k: round(min_gap(pts, v), 1)
                                  for k, v in masks.items() if k != name},
            "min_letter_body": min(c[3] - c[1] + 1 for c in bodies),
            "min_any_comp": min(c[3] - c[1] + 1 for c in g5),
            "tittles": [[t[0], t[1], t[2], t[3]] for t in tittles],
            "ocr": ocrs,
            "expected_cx": round(X(xd), 1),
            "observed_cx": round((x0 + x1) / 2, 1),
            "expected_baseline": round(Y(yd), 1),
            "ink_bottom": y1,
        }
        results.append(r)
    return results, masks


def _legend(H, W):
    """Legend band mask (y>=925) for solver_coupling.

    :param H: image height.
    :param W: image width.
    :returns: HxW bool mask.
    """
    m = np.zeros((H, W), bool)
    m[925:, :] = True
    return m


def main() -> int:
    """Print the final consolidated table for both figures.

    :returns: process exit code 0.
    """
    # ---- FIGURE 1 -------------------------------------------------------
    # Fit: x_px = 290.921*x + 30.079 ; y_px = 1049.59 - 291.818*y
    # (validated: feedback line y=2.8 -> 232.5 vs observed 231-234 centre
    #  232.5; verticals x=1.0/4.8 -> 320.5/1426.5 vs 321.0/1426.5;
    #  title y=3.35 -> 72.0 vs observed centre 72.0)
    t1 = {"X": lambda v: 290.921 * v + 30.079,
          "Y": lambda v: 1049.59 - 291.818 * v}
    # windows: label1 window widened to include 's' fragments at x315
    L1 = [
        ("surface heat flux", 1.55, 2.55, (310, 262, 655, 300), (262, 300)),
        ("backface temperature", 3.05, 2.55, (690, 262, 1145, 308), (262, 308)),
        ("grid dump", 1.55, 1.22, (375, 648, 586, 695), (648, 695)),
        ("refined field", 3.35, 1.22, (880, 648, 1130, 690), (648, 690)),
    ]
    r1, _m1 = audit(FIGDIR + "solver_coupling.png", t1, L1, "solver")
    print("=" * 78)
    print("FIGURE 1 solver_coupling.png  (1951x1078)")
    print("=" * 78)
    for r in r1:
        print(json.dumps(r, indent=2))

    # ---- FIGURE 2 -------------------------------------------------------
    # Fit: x_px = 290.645*x + 31.403 ; y_px = 902.29 - 291.154*y
    # (validated: slate arrow row y=1.55 -> 451.0 vs observed 449-453
    #  centre 451.0; title y=2.85 -> 72.5 vs observed 72.5; box fills
    #  353..550 vs predicted paths 349.1/552.9)
    t2 = {"X": lambda v: 290.645 * v + 31.403,
          "Y": lambda v: 902.29 - 291.154 * v}
    L2 = [
        ("raw data", 1.55, 1.95, (388, 290, 572, 330), (290, 348)),
        ("parsed", 3.05, 1.95, (844, 290, 991, 338), (290, 348)),
        ("integrated", 5.35, 0.95, (1478, 581, 1697, 630), (581, 639)),
    ]
    r2, _m2 = audit(FIGDIR + "result_extraction.png", t2, L2, "result")
    print("=" * 78)
    print("FIGURE 2 result_extraction.png  (1951x933)")
    print("=" * 78)
    for r in r2:
        print(json.dumps(r, indent=2))

    with open(f"{OUT}/final_verify.json", "w") as fh:
        json.dump({"fig1": r1, "fig2": r2}, fh, indent=2)
    print("written", f"{OUT}/final_verify.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
