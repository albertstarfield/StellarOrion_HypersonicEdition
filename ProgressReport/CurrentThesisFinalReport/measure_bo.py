#!/usr/bin/env python3
"""Measure natural size and printed text scale of the two BO figures.

AXIOMS: a figure's declared point size only equals its printed size when the
include width equals the PNG's natural width (scale 1.0); otherwise effective
pt = declared pt x (include_in / natural_in). THEORIES: both PNGs are saved at
dpi=160 with bbox_inches="tight", so natural inches = pixels / 160. The thesis
textwidth is 398.34 pt = 5.51181 in. APPLICATIONS: prints natural inches plus
the effective pt of every declared font size at include widths 0.75*textwidth
(current ch4 include) and textwidth (candidate fix), so the include choice that
keeps every label >= 8 pt can be made from data. CITES: matplotlib savefig
dpi/tight bbox semantics, https://matplotlib.org/stable/api/_as_gen/
matplotlib.pyplot.savefig.html
"""

from pathlib import Path

DPI = 160.0
TEXT_W_IN = 398.34 / 72.0  # 5.51181 in
FIGS = {
    "bo_ccd_design.png": {"title": 12.0, "legend": 12.0, "xytick": 12.0,
                          "axis": 12.0, "source": 10.0, "ztick_est": 10.0},
    "bo_convergence.png": {"title": 12.0, "legend": 12.0, "xytick": 12.0,
                           "axis": 12.0, "source": 10.0},
}


def main() -> int:
    figs_dir = Path(__file__).resolve().parent / "figures"
    for name, fonts in FIGS.items():
        from PIL import Image
        im = Image.open(figs_dir / name)
        w_px, h_px = im.size
        nat_in = w_px / DPI
        print(f"{name}: {w_px}x{h_px}px natural {nat_in:.3f}x{h_px/DPI:.3f}in")
        for inc_name, inc_in in (("0.75tw", 0.75 * TEXT_W_IN),
                                 ("textwidth", TEXT_W_IN)):
            scale = inc_in / nat_in
            effs = {k: v * scale for k, v in fonts.items()}
            worst = min(effs.values())
            flag = "OK" if worst >= 8.0 else "FAIL"
            print(f"    {inc_name} ({inc_in:.3f}in) scale={scale:.3f}: "
                  + " ".join(f"{k}={v:.1f}pt" for k, v in effs.items())
                  + f"  worst={worst:.2f}pt {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
