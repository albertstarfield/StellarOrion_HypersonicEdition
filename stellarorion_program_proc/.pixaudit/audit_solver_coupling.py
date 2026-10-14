"""Evidence-based pixel audit of solver_coupling.png moved arrow labels.

AXIOMS
  A1. The raster is ground truth: every number printed below comes from a
      numpy/PIL probe of the committed PNG, never from an image viewer.
  A2. Geometry from make_methodology_figures.build_solver_coupling: H=3.5,
      PRINT_W_IN=6.50, axes=[0,0,1,1], xlim 0..6.5, ylim 0..3.5; the four
      moved labels are ha=centre, va=bottom, fontsize 9.5 italic at
      (1.55,2.55), (3.05,2.55), (1.55,1.22), (3.35,1.22).
  A3. Check (a) passes only when the glyphs form exactly ONE group at 12px
      dilation AND min gap to box border, box fill and box text >= 3px.
THEORIES
  T1. x_px=290.921*x+30.079 and y_px=1049.59-291.818*y are validated
      against four independent raster features (feedback line y=2.8 ->
      rows 231-234 -> predicted 232.5; feedback verticals x=1.0/4.8 ->
      320.5/1426.5 vs predicted 321.0/1426.5; title y=3.35 -> predicted
      72.0 vs observed centre 72.0; box paths 320.0/524.3/699.4/903.7 vs
      observed border bands 318-322/521-526/697-700/900-905).
  T2. Expected ink geometry is double-checked by re-rendering each label
      with matplotlib 3.11.2 at dpi=300 (one figure per label) and mapping
      render px -> PNG px with PNG = k*render + offset derived from T1;
      a real misplacement then shows up as a residual beyond ~3px.
  T3. Arrow ink = #37474F + #E65100 outside every box (fill dilated 6px,
      which also absorbs border pixels), outside the legend band, and
      outside every measured label window.
  T4. Mask hygiene: box fill keeps only components >=20000px (kills
      anti-alias specks); box border = edge colours within 6px of that
      fill (kills grey text AA matching #C0C1C2 and the free-standing
      orange feedback line); ML_EDGE (#E65201) is within tol of the
      ORANGE feedback line, so proximity-to-fill is what tells them apart.
APPLICATIONS
  A1. Prints PASS/FAIL evidence for checks (a)-(e) per moved label and
      writes solver_coupling_report.json plus label crops to .pixaudit/.
CITATIONS
  Matplotlib 3.11.2 - https://matplotlib.org/stable/
  scipy.ndimage - https://docs.scipy.org/doc/scipy/reference/
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
    ORANGE,
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
       "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/solver_coupling.png")
OUT = ("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/"
       "stellarorion_program_proc/.pixaudit")

# name, x_data, y_data, band, annotated arrow (mid-point data coords)
LABELS = [
    ("surface heat flux", 1.55, 2.55, "top", (1.95, 2.15),
     "SPARTA->OpenFOAM horizontal (top row)"),
    ("backface temperature", 3.05, 2.55, "top", (3.85, 2.15),
     "OpenFOAM->Survivability horizontal (top row)"),
    ("grid dump", 1.55, 1.22, "gap", (1.00, 1.50),
     "SPARTA->PINN vertical (inter-row)"),
    ("refined field", 3.35, 1.22, "gap", (2.90, 1.50),
     "OpenFOAM->Bayes vertical (inter-row)"),
]
BANDS = {"top": (240, 316), "gap": (640, 700)}
KX, OX = 290.921 / 300.0, 30.079       # render px -> PNG px (x)
KY, OY = 291.818 / 300.0, 1049.59 - 291.818 * 3.5   # render px -> PNG px (y)


def render_expected(xd: float, yd: float, text: str, color: str):
    """Re-render one label with matplotlib and return its PNG-space ink box.

    One figure per label so neighbouring labels can never contaminate the
    ink bbox. Anchor is the data point itself (ha=centre, va=bottom).
    :param xd: data x of the text anchor.
    :param yd: data y of the text anchor.
    :param text: label string.
    :param color: matplotlib colour string.
    :returns: (x0,y0,x1,y1) in PNG px of the expected ink, or None.
    """
    fig = plt.figure(figsize=(6.5, 3.5), dpi=300)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, 6.5)
    ax.set_ylim(0.0, 3.5)
    ax.axis("off")
    ax.text(xd, yd, text, ha="center", va="bottom", fontsize=9.5,
            fontstyle="italic", color=color)
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].astype(int)
    plt.close(fig)
    base = np.array([33, 33, 33]) if color != "#E65100" else np.array([230, 81, 0])
    m = (np.abs(buf - base).max(axis=2) <= 90) & (buf.sum(axis=2) < 730)
    ax_px, ay_px = 300.0 * xd, 300.0 * (3.5 - yd)
    win = np.zeros(m.shape, bool)
    win[max(0, int(ay_px) - 60):int(ay_px) + 40,
        max(0, int(ax_px) - 260):int(ax_px) + 260] = True
    ys, xs = np.nonzero(m & win)
    if len(xs) == 0:
        return None
    return (xs.min() * KX + OX, ys.min() * KY + OY,
            xs.max() * KX + OX, ys.max() * KY + OY)


def main() -> int:
    """Run every probe and print the audit.

    :returns: process exit code 0.
    """
    a = load(FIG)
    H, W = a.shape[:2]
    print(f"IMAGE {FIG}\n  size {W}x{H}")

    # ---- 1. transform validation ---------------------------------------
    orange = color_mask(a, [ORANGE], tol=4)
    slate = color_mask(a, [SLATE], tol=4)
    fb_runs = [r for r in grouped_runs(np.nonzero(orange[:, 900])[0])
               if r[1] - r[0] >= 3]
    vert_cols = grouped_runs(np.nonzero(orange[250:300, :].any(axis=0))[0])
    tm = text_mask(a)
    tcomps = [c for c in components(tm, 40) if c[1] < 150]
    tx0, ty0 = min(c[0] for c in tcomps), min(c[1] for c in tcomps)
    tx1, ty1 = max(c[2] for c in tcomps), max(c[3] for c in tcomps)
    print("T1 probes: feedback rows", fb_runs, "| verticals", vert_cols,
          "| title centre", ((tx0 + tx1) / 2, (ty0 + ty1) / 2),
          "| slate-in-textmask", int((tm & slate).sum()))

    fill_raw = color_mask(a, FILL_COLORS, tol=6)
    fill_comps = sorted(components(fill_raw, 20000), key=lambda c: (c[1], c[0]))
    fill = np.zeros((H, W), bool)
    for c in fill_comps:
        fill[c[1]:c[3] + 1, c[0]:c[2] + 1] = True
    edge_raw = color_mask(a, EDGE_COLORS, tol=6)
    border = edge_raw & ndimage.binary_dilation(fill, iterations=6)
    box_ink = fill | border
    box_bboxes = [(c[0], c[1], c[2], c[3]) for c in fill_comps]
    print("boxes:", box_bboxes)

    vcols = [(r[0] + r[1]) / 2 for r in vert_cols]
    s_x = (vcols[-1] - vcols[0]) / 3.8
    bx = vcols[0] - s_x
    fb_c = (fb_runs[0][0] + fb_runs[0][1]) / 2.0
    s_y = (fb_c - (ty0 + ty1) / 2.0) / 0.55
    cy = fb_c + 2.8 * s_y
    print(f"FIT x_px={s_x:.3f}x+{bx:.3f} y_px={cy:.2f}-{s_y:.3f}y")
    X = lambda xd: s_x * xd + bx
    Y = lambda yd: cy - s_y * yd

    white = (a >= 246).all(axis=2)
    box_text = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in box_bboxes:
        box_text[y0 + 8:y1 - 7, x0 + 8:x1 - 7] = white[y0 + 8:y1 - 7,
                                                        x0 + 8:x1 - 7]
    print("box text px:", int(box_text.sum()), " comps:",
          len(components(box_text, 20)))

    # ---- 2. label clusters ------------------------------------------------
    band_clusters = {}
    for bname, (yb0, yb1) in BANDS.items():
        win = np.zeros((H, W), bool)
        win[yb0:yb1, :] = True
        band_clusters[bname] = cluster_x(components(tm & win, 30), gap=26)
        print(f"BAND {bname}:", band_clusters[bname])

    assigned = {}
    for name, xd, yd, bname, _am, _sem in LABELS:
        cx = X(xd)
        assigned[name] = min(band_clusters[bname],
                             key=lambda c: abs((c[0] + c[2]) / 2 - cx))

    nd_win = np.zeros((H, W), bool)
    nd_win[165:235, 1300:] = True
    nd_all = cluster_x(components((color_mask(a, [ORANGE], tol=4) | tm)
                                   & nd_win, 30), gap=26)
    nd_cl = [c for c in nd_all if c[3] - c[1] >= 15]
    print("new design clusters:", nd_cl, "(raw:", nd_all, ")")
    nd_bbox = nd_cl[0][:4] if nd_cl else None

    # ---- 3. arrow mask ----------------------------------------------------
    box_zone = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in box_bboxes:
        box_zone[max(0, y0 - 8):y1 + 9, max(0, x0 - 8):x1 + 9] = True
    legend_zone = np.zeros((H, W), bool)
    legend_zone[925:, :] = True
    arrow = (slate | orange) & ~box_zone & ~legend_zone
    windows = [c[:4] for c in assigned.values()]
    if nd_bbox:
        windows.append(nd_bbox)
    for b in windows:
        arrow[max(0, b[1] - 10):b[3] + 11, max(0, b[0] - 10):b[2] + 11] = False
    arrow_comps = components(arrow, 40)
    print("ARROW comps:", [c for c in arrow_comps])

    # ---- 4. label masks ---------------------------------------------------
    masks = {}
    for name, _xd, _yd, bname, _am, _sem in LABELS:
        x0, y0, x1, y1, _n = assigned[name]
        win = np.zeros((H, W), bool)
        win[y0:y1 + 1, x0:x1 + 1] = True
        masks[name] = tm & win
    if nd_bbox:
        nd_w = np.zeros((H, W), bool)
        nd_w[nd_bbox[1]:nd_bbox[3] + 1, nd_bbox[0]:nd_bbox[2] + 1] = True
        masks["new design"] = (color_mask(a, [ORANGE], tol=4) | tm) & nd_w

    # ---- 5. measurements ---------------------------------------------------
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
        gcomps = components(m, 20)
        groups12 = int(ndimage.label(ndimage.binary_dilation(m, iterations=12))[1])
        xs = sorted([(c[0], c[2]) for c in gcomps])
        gaps = [xs[i + 1][0] - xs[i][1] - 1 for i in range(len(xs) - 1)]

        gap_border = min_gap(pts, border)
        gap_fill = min_gap(pts, fill)
        gap_boxtext = min_gap(pts, box_text)
        gap_arrow = min_gap(pts, arrow)

        # annotated arrow: nearest arrow comp to the expected mid-point
        exp_ax, exp_ay = X(arrow_d[0]), Y(arrow_d[1])
        intent = min(arrow_comps,
                     key=lambda c: abs((c[0] + c[2]) / 2 - exp_ax)
                     + abs((c[1] + c[3]) / 2 - exp_ay), default=None)
        gap_intent = min_gap(pts, _bbox(H, W, intent)) if intent else -1.0

        gaps_others = {}
        for other, om in masks.items():
            if other != name:
                gaps_others[other] = min_gap(pts, om)

        crop = save_crop(a, (x0, y0, x1, y1),
                         f"{OUT}/solver_{name.replace(' ', '_')}.png", pad=14)
        ocrs = ocr_multi(crop, psms=(7, 13, 6, 8))

        heights = sorted(c[3] - c[1] + 1 for c in gcomps)
        min_h = min(heights)
        exp_cx, exp_base = X(xd), Y(yd)
        obs_cx = (x0 + x1) / 2.0
        rend = render_expected(xd, yd, name, "#212121")
        r_pred = tuple(round(v, 1) for v in rend) if rend else None
        resid = tuple(round(o - r, 1) for o, r in zip((x0, y0, x1, y1), rend)) \
            if rend else None

        check_a = (groups12 == 1 and gap_border >= 3 and gap_fill >= 3
                   and gap_boxtext >= 3)
        check_c = all(v >= 3 for v in gaps_others.values())
        check_e = min_h >= 10
        verdicts[name] = (check_a, check_c, check_e)

        print(f"\nLABEL '{name}' data=({xd},{yd}) annotates: {sem}")
        print(f"  bbox px ({x0},{y0})-({x1},{y1}) w={x1-x0+1} h={y1-y0+1} "
              f"glyphs={len(gcomps)}")
        print(f"  (a) groups@dil12={groups12}; glyph gaps={gaps} "
              f"(max word gap {max(gaps) if gaps else 0}px)")
        print(f"  (a) min gap -> box BORDER={gap_border:.1f} FILL={gap_fill:.1f} "
              f"TEXT={gap_boxtext:.1f} px (need >=3); touches box ink: "
              f"{bool((m & box_ink).any())}")
        print(f"  (b) annotated arrow comp {intent[:4] if intent else None}; "
              f"gap label->that arrow = {gap_intent:.1f}px; gap label->any arrow "
              f"ink = {gap_arrow:.1f}px")
        if intent:
            acx, acy = (intent[0] + intent[2]) / 2, (intent[1] + intent[3]) / 2
            print(f"       arrow centre ({acx:.1f},{acy:.1f}) vs label centre "
                  f"({obs_cx:.1f},{(y0+y1)/2:.1f}): dx={obs_cx-acx:+.1f} "
                  f"dy={(y0+y1)/2-acy:+.1f} px")
        print(f"       band: label y {y0}..{y1}; feedback line rows {fb_runs[0]}; "
              f"row-A box ink top y=317; row-A bottom y=526; row-B top y=697")
        print("  (c) gaps to other labels: " +
              ", ".join(f"{k}={v:.1f}" for k, v in sorted(gaps_others.items())))
        print(f"  (d) OCR {json.dumps(ocrs)}")
        print(f"  (e) glyph heights={heights}; min={min_h}px; at 0.85 scale="
              f"{round(min_h*0.85,1)}px")
        print(f"  pos: matplotlib ground-truth render ink (PNG space) = {r_pred}; "
              f"observed residual (obs-pred) = {resid}")
        print(f"  pos: anchor expected x={exp_cx:.1f} baseline y={exp_base:.1f}; "
              f"observed centre x={obs_cx:.1f} ink bottom y={y1}")
        report["labels"][name] = {
            "data": [xd, yd], "annotates": sem,
            "bbox": [x0, y0, x1, y1], "glyphs": len(gcomps),
            "groups_dil12": groups12, "gap_border": gap_border,
            "gap_fill": gap_fill, "gap_box_text": gap_boxtext,
            "gap_arrow": gap_arrow, "gap_annotated_arrow": gap_intent,
            "arrow_bbox": list(intent[:4]) if intent else None,
            "gaps_other_labels": gaps_others, "ocr": ocrs,
            "glyph_heights": heights, "min_glyph_height": min_h,
            "render_pred_ink": r_pred, "residual_obs_minus_pred": resid,
            "check_a": bool(check_a), "check_c": bool(check_c),
            "check_e": bool(check_e),
        }

    if nd_bbox:
        print(f"\nCONTEXT 'new design' bbox {nd_bbox} (expected anchor "
              f"x={X(5.35):.1f} baseline y={Y(2.85):.1f})")
        crop = save_crop(a, nd_bbox, f"{OUT}/solver_new_design.png", pad=14)
        print("  OCR", json.dumps(ocr_multi(crop, psms=(7, 13, 6, 8))))
        nd_rend = render_expected(5.35, 2.85, "new design", "#E65100")
        print("  render pred", tuple(round(v, 1) for v in nd_rend),
              "residual", tuple(round(o - r, 1)
                                for o, r in zip(nd_bbox, nd_rend)))

    print("\nVERDICT (a / c / e):")
    for k, v in verdicts.items():
        print(f"  {k}: {'PASS' if v[0] else 'FAIL'}(a) "
              f"{'PASS' if v[1] else 'FAIL'}(c) {'PASS' if v[2] else 'FAIL'}(e)")
    with open(f"{OUT}/solver_coupling_report.json", "w") as fh:
        json.dump(report, fh, indent=2)
    print("JSON:", f"{OUT}/solver_coupling_report.json")
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
