"""Evidence-based pixel audit of result_extraction.png moved arrow labels.

AXIOMS
  A1. The raster is ground truth: every printed number is a numpy/PIL probe
      of the committed PNG.
  A2. Geometry from make_methodology_figures.build_result_extraction: H=3.0,
      PRINT_W_IN=6.50, axes=[0,0,1,1]; moved labels 'raw data' (1.55,1.95)
      and 'parsed' (3.05,1.95) are ha=centre va=bottom fontsize 9.5 italic;
      'integrated' (5.35,0.95) is unchanged.
  A3. Check (a) passes only when glyphs form ONE group at 12px dilation AND
      min gap to box border/fill/text >= 3px.
THEORIES
  T1. Affine fits validated against slate arrow rows (data y=1.55), slate
      vertical arrow (data x=4.8), the title (y=2.85) and box fill rows.
  T2. Label ink = INK #212121 cores (max-abs slack 30, excludes slate
      arrows which are 46 away per-channel); box fill = components >=20000px
      of the palette fills; border = edge colours within 6px of that fill;
      box text = white pixels inside fill bbox inset 8px (Parse box has INK
      text on light fill, others have white text).
  T3. 'integrated' is checked for collision against everything including the
      vertical arrow at data x=4.8 and the metrics box below it.
APPLICATIONS
  A1. Prints PASS/FAIL evidence for checks (a)-(e); writes
      result_extraction_report.json and crops to .pixaudit/.
CITATIONS
  Matplotlib 3.11.2 (generator) - https://matplotlib.org/stable/
  Tesseract 5.5.3 - https://github.com/tesseract-ocr/tesseract
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from probe_common import (
    EDGE_COLORS,
    FILL_COLORS,
    SLATE,
    cluster_x,
    color_mask,
    components,
    grouped_runs,
    load,
    min_gap,
    ocr_multi,
    pts_of,
    save_crop,
    text_mask,
)
from scipy import ndimage

FIG = ("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/"
       "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/result_extraction.png")
OUT = ("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/"
       "stellarorion_program_proc/.pixaudit")

# name, x, y, band, annotated arrow mid-point (data), semantics
LABELS = [
    ("raw data", 1.55, 1.95, "row", (1.95, 1.55),
     "dump->parse horizontal arrow"),
    ("parsed", 3.05, 1.95, "row", (3.85, 1.55),
     "parse->integrate horizontal arrow"),
    ("integrated", 5.35, 0.95, "side", (4.80, 1.05),
     "integrate->metrics vertical arrow"),
]


def main() -> int:
    """Run every probe and print the audit.

    :returns: process exit code 0.
    """
    a = load(FIG)
    H, W = a.shape[:2]
    print(f"IMAGE {FIG}\n  size {W}x{H}")

    slate = color_mask(a, [SLATE], tol=4)
    tm = text_mask(a)
    print("slate px:", int(slate.sum()), "| slate in text mask (want 0):",
          int((slate & tm).sum()))

    # slate arrow geometry
    slate_comps = components(slate, 40)
    print("slate arrow comps:", [c for c in slate_comps])
    # horizontal arrow rows: rows where slate spans >100px
    rows = [r for r in grouped_runs(np.nonzero(slate.sum(axis=1) > 100)[0])]
    print("slate wide rows (arrow y):", rows)
    cols = [c for c in grouped_runs(np.nonzero(slate.sum(axis=0) > 60)[0])]
    print("slate tall cols (arrow x):", cols)

    # title
    tcomps = [c for c in components(tm, 40) if c[1] < 200]
    tx0, ty0 = min(c[0] for c in tcomps), min(c[1] for c in tcomps)
    tx1, ty1 = max(c[2] for c in tcomps), max(c[3] for c in tcomps)
    print(f"title ink ({tx0},{ty0})-({tx1},{ty1}) centre "
          f"({(tx0+tx1)/2:.1f},{(ty0+ty1)/2:.1f}) [data x=3.25 y=2.85]")

    # box fills
    fill_raw = color_mask(a, FILL_COLORS, tol=6)
    fill_comps = sorted(components(fill_raw, 20000), key=lambda c: (c[1], c[0]))
    print("box fill bboxes:", [(c[0], c[1], c[2], c[3]) for c in fill_comps])

    # ---- fit transforms -------------------------------------------------
    # y: slate arrow row centre -> data 1.55 ; title centre -> 2.85
    arr_row = rows[0]
    arr_yc = (arr_row[0] + arr_row[1]) / 2.0
    ti_c = (ty0 + ty1) / 2.0
    s_y = (arr_yc - ti_c) / (2.85 - 1.55)
    cy = arr_yc + 1.55 * s_y
    # x: slate vertical col centre -> data 4.8 ; title centre -> 3.25
    vert_col = cols[-1]
    vx = (vert_col[0] + vert_col[1]) / 2.0
    s_x_title = (vx - (tx0 + tx1) / 2.0) / (4.8 - 3.25)
    bx_title = vx - s_x_title * 4.8
    # second x check: box fills at data x0 = 0.3 / 4.1 (fill inset ~3px)
    f0 = fill_comps[0]
    f_last = fill_comps[-1]
    print(f"PROBE arrow row {arr_row} centre {arr_yc} | vertical col {vert_col} "
          f"centre {vx}")
    print(f"FIT via title+arrow: s_x={s_x_title:.3f} bx={bx_title:.3f} "
          f"| s_y={s_y:.3f} cy={cy:.2f}")
    # refine x using box fills: x0 fill starts at 0.3+inset, last box at 4.1
    s_x_boxes = ((f_last[0] - f0[0]) / (4.1 - 0.3))
    print(f"FIT via box fills: s_x={s_x_boxes:.3f} (fill-left to fill-left)")
    s_x = s_x_title
    bx = bx_title

    def X(xd: float) -> float:
        """Data x -> pixel x."""
        return s_x * xd + bx

    def Y(yd: float) -> float:
        """Data y -> pixel y."""
        return cy - s_y * yd

    for v in (1.9, 1.55, 1.2, 0.9, 0.2, 2.85, 1.95, 0.95):
        print(f"  y={v} -> {Y(v):.1f}")
    for v in (0.3, 1.7, 2.2, 4.1, 4.8, 5.5, 1.55, 3.05, 5.35, 3.25):
        print(f"  x={v} -> {X(v):.1f}")

    # ---- masks -----------------------------------------------------------
    fill = np.zeros((H, W), bool)
    for c in fill_comps:
        fill[c[1]:c[3] + 1, c[0]:c[2] + 1] = True
    edge = color_mask(a, EDGE_COLORS, tol=6)
    border = edge & ndimage.binary_dilation(fill, iterations=6)
    box_ink = fill | border
    white = (a >= 246).all(axis=2)
    box_text = np.zeros((H, W), bool)
    for c in fill_comps:
        x0, y0, x1, y1 = c[:4]
        box_text[y0 + 8:y1 - 7, x0 + 8:x1 - 7] = white[y0 + 8:y1 - 7,
                                                        x0 + 8:x1 - 7]
    # INK box text (Parse box) counts too: INK pixels inside any fill
    box_text |= tm & ndimage.binary_erosion(fill, iterations=6)
    print("box text px:", int(box_text.sum()))
    print("  box fill runs at column x(1.0):",
          grouped_runs(np.nonzero(fill[:, int(X(1.0))])[0]),
          "[predict path rows 349.1/552.9 for y=1.9/1.2]")

    # ---- label clusters ---------------------------------------------------
    # Band MUST stop above the box-row ink (fill top 353 / 644) or the box's
    # own INK text ("Parse Surface Data") merges into the label cluster.
    bands = {"row": (int(Y(1.95)) - 45, int(Y(1.9)) - 1),
             "side": (int(Y(0.95)) - 45, int(Y(0.9)) - 1)}
    print("bands:", bands)
    band_clusters = {}
    for bname, (yb0, yb1) in bands.items():
        win = np.zeros((H, W), bool)
        win[max(0, yb0):yb1, :] = True
        band_clusters[bname] = cluster_x(components(tm & win, 20), gap=26)
        print(f"BAND {bname} y{yb0}..{yb1}:", band_clusters[bname])

    assigned = {}
    for name, xd, yd, bname, _am, _sem in LABELS:
        cx = X(xd)
        assigned[name] = min(band_clusters[bname],
                             key=lambda c: abs((c[0] + c[2]) / 2 - cx))

    # arrow mask: slate outside box zones, outside label windows
    box_zone = np.zeros((H, W), bool)
    for c in fill_comps:
        x0, y0, x1, y1 = c[:4]
        box_zone[max(0, y0 - 8):y1 + 9, max(0, x0 - 8):x1 + 9] = True
    arrow = slate & ~box_zone
    for b in assigned.values():
        arrow[max(0, b[1] - 10):b[3] + 11, max(0, b[0] - 10):b[2] + 11] = False
    arrow_comps = components(arrow, 40)
    print("ARROW comps:", [c for c in arrow_comps])

    masks = {}
    for name, _xd, _yd, bname, _am, _sem in LABELS:
        x0, y0, x1, y1, _n = assigned[name]
        win = np.zeros((H, W), bool)
        win[y0:y1 + 1, x0:x1 + 1] = True
        masks[name] = tm & win

    # ---- measurements -----------------------------------------------------
    report = {"figure": FIG, "size": [W, H],
              "fit": {"s_x": round(float(s_x), 3), "bx": round(float(bx), 3),
                      "s_y": round(float(s_y), 3), "cy": round(float(cy), 2)},
              "labels": {}}
    print("\n=== PER-LABEL ===")
    verdicts = {}
    for name, xd, yd, bname, arrow_d, sem in LABELS:
        m = masks[name]
        pts = pts_of(m)
        x0, y0 = int(pts[:, 0].min()), int(pts[:, 1].min())
        x1, y1 = int(pts[:, 0].max()), int(pts[:, 1].max())
        gcomps = components(m, 5)
        groups12 = int(ndimage.label(ndimage.binary_dilation(m, iterations=12))[1])
        xs = sorted([(c[0], c[2]) for c in gcomps])
        gaps = [xs[i + 1][0] - xs[i][1] - 1 for i in range(len(xs) - 1)]

        gap_border = min_gap(pts, border)
        gap_fill = min_gap(pts, fill)
        gap_boxtext = min_gap(pts, box_text)
        gap_arrow = min_gap(pts, arrow)

        exp_ax, exp_ay = X(arrow_d[0]), Y(arrow_d[1])
        intent = min(arrow_comps,
                     key=lambda c: abs((c[0] + c[2]) / 2 - exp_ax)
                     + abs((c[1] + c[3]) / 2 - exp_ay), default=None)
        gap_intent = min_gap(pts, _bbox(H, W, intent)) if intent else -1.0

        gaps_others = {k: min_gap(pts, v) for k, v in masks.items() if k != name}

        crop = save_crop(a, (x0, y0, x1, y1),
                         f"{OUT}/result_{name.replace(' ', '_')}.png", pad=14)
        ocrs = ocr_multi(crop, psms=(7, 13, 6, 8))
        heights = sorted(c[3] - c[1] + 1 for c in gcomps)
        # Tittles (detached i-dots) are ~5px by font design; report both the
        # all-component minimum and the minimum over letter-sized bodies.
        bodies = [c for c in gcomps if (c[3] - c[1] + 1) >= 10]
        tittles = [c for c in gcomps if (c[3] - c[1] + 1) < 10]
        min_h = min(heights)
        min_body = min(c[3] - c[1] + 1 for c in bodies) if bodies else None
        exp_cx, exp_base = X(xd), Y(yd)
        obs_cx = (x0 + x1) / 2.0

        # matplotlib ground-truth render of this label
        fig = plt.figure(figsize=(6.5, 3.0), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 6.5)
        ax.set_ylim(0, 3.0)
        ax.axis("off")
        ax.text(xd, yd, name, ha="center", va="bottom", fontsize=9.5,
                fontstyle="italic", color="#212121")
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].astype(int)
        plt.close(fig)
        rm = (np.abs(buf - np.array([33, 33, 33])).max(axis=2) <= 90) & \
            (buf.sum(axis=2) < 730)
        rwin = np.zeros(rm.shape, bool)
        rwin[max(0, int(300 * (3.0 - yd)) - 60):int(300 * (3.0 - yd)) + 40,
             max(0, int(300 * xd) - 260):int(300 * xd) + 260] = True
        rys, rxs = np.nonzero(rm & rwin)
        rend = (rxs.min() * s_x / 300 + bx, rys.min() * (s_y / 300) + (cy - 3.0 * s_y),
                rxs.max() * s_x / 300 + bx, rys.max() * (s_y / 300) + (cy - 3.0 * s_y)) \
            if len(rxs) else None

        check_a = (groups12 == 1 and gap_border >= 3 and gap_fill >= 3
                   and gap_boxtext >= 3)
        check_c = all(v >= 3 for v in gaps_others.values())
        check_e = min_h >= 10
        verdicts[name] = (check_a, check_c, check_e)

        print(f"\nLABEL '{name}' data=({xd},{yd}) annotates: {sem}")
        print(f"  bbox px ({x0},{y0})-({x1},{y1}) w={x1-x0+1} h={y1-y0+1} "
              f"glyphs={len(gcomps)}")
        print(f"  (a) groups@dil12={groups12}; glyph gaps={gaps}")
        print(f"  (a) gap border={gap_border:.1f} fill={gap_fill:.1f} "
              f"text={gap_boxtext:.1f} px (need>=3); touches box ink: "
              f"{bool((m & box_ink).any())}")
        print(f"  (b) annotated arrow {intent[:4] if intent else None}; "
              f"gap label->that arrow={gap_intent:.1f}px; ->any arrow={gap_arrow:.1f}px")
        if intent:
            acx, acy = (intent[0] + intent[2]) / 2, (intent[1] + intent[3]) / 2
            print(f"       arrow centre ({acx:.1f},{acy:.1f}) vs label centre "
                  f"({obs_cx:.1f},{(y0+y1)/2:.1f}): dx={obs_cx-acx:+.1f} "
                  f"dy={(y0+y1)/2-acy:+.1f}")
        print(f"       band: label y {y0}..{y1}; title ink y {ty0}..{ty1}; "
              f"box row top edge y={min(c[1] for c in fill_comps)}; "
              f"box row bottom y={max(c[3] for c in fill_comps)}")
        print("  (c) gaps: " + ", ".join(f"{k}={v:.1f}"
                                         for k, v in sorted(gaps_others.items())))
        print(f"  (d) OCR {json.dumps(ocrs)}")
        print(f"  (e) heights={heights}; min={min_h}px; min letter body={min_body}px; "
              f"tittles={[(t[0], t[1], t[2], t[3]) for t in tittles]}; "
              f"x0.85 body={round(min_body*0.85,1)}px tittle={round(min_h*0.85,1)}px")
        if rend:
            print("  pos: render pred", tuple(round(v, 1) for v in rend),
                  "residual", tuple(round(o - r, 1)
                                    for o, r in zip((x0, y0, x1, y1), rend)))
        print(f"  pos: expected centre x={exp_cx:.1f} (obs {obs_cx:.1f}, "
              f"delta {obs_cx-exp_cx:+.1f}px); expected baseline y={exp_base:.1f} "
              f"(ink bottom {y1})")
        report["labels"][name] = {
            "data": [xd, yd], "annotates": sem, "bbox": [x0, y0, x1, y1],
            "glyphs": len(gcomps), "groups_dil12": groups12,
            "gap_border": gap_border, "gap_fill": gap_fill,
            "gap_box_text": gap_boxtext, "gap_arrow": gap_arrow,
            "gap_annotated_arrow": gap_intent,
            "arrow_bbox": list(intent[:4]) if intent else None,
            "gaps_others": gaps_others, "ocr": ocrs, "heights": heights,
            "min_height": min_h, "min_letter_body": min_body,
            "tittle_boxes": [[t[0], t[1], t[2], t[3]] for t in tittles],
            "check_a": bool(check_a), "check_c": bool(check_c),
            "check_e": bool(check_e),
        }

    print("\nVERDICT (a / c / e):")
    for k, v in verdicts.items():
        print(f"  {k}: {'PASS' if v[0] else 'FAIL'}(a) "
              f"{'PASS' if v[1] else 'FAIL'}(c) {'PASS' if v[2] else 'FAIL'}(e)")
    with open(f"{OUT}/result_extraction_report.json", "w") as fh:
        json.dump(report, fh, indent=2)
    print("JSON:", f"{OUT}/result_extraction_report.json")
    return 0


def _bbox(H: int, W: int, comp) -> np.ndarray:
    """Boolean mask covering one component bbox.

    :param H: image height.
    :param W: image width.
    :param comp: (x0,y0,x1,y1,area) component tuple.
    :returns: HxW bool mask.
    """
    m = np.zeros((H, W), bool)
    m[comp[1]:comp[3] + 1, comp[0]:comp[2] + 1] = True
    return m


if __name__ == "__main__":
    raise SystemExit(main())
