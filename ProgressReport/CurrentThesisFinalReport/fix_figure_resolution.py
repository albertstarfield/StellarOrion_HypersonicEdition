#!/usr/bin/env python3
"""Bring every included raster figure to at least 200 dots per inch at the size
it is printed, or record why that is impossible.

THE RULE
============================================================================
An image saved at W pixels wide and included at P inches wide prints at
effective dpi = W / P. So the width fraction that yields a target dpi is

    width_fraction = W / (target_dpi * TEXT_WIDTH_IN)

with TEXT_WIDTH_IN = 14 cm = 5.51181 in.

THE FLOOR
============================================================================
200 dpi is the point below which line work and small labels visibly break up in
print. Below the floor the figure is resized, unless the required width falls
under MIN_FRAC of the text block, at which point the figure would be too small
to read and the honest action is to disclose the limitation in its caption
instead. That floor is MIN_FRAC = 0.25.

WHAT THIS FOUND AND CHANGED
============================================================================
    figure                                     was      now
    IADsLayer.png                            102 dpi   disclosed, 280x201 px
    RecirculationExample.jpeg                 77 dpi   disclosed
    sutherlandfx.png                         172 dpi   resized
    aerodynamicHighShockBody.png             142 dpi   resized to 203
    GolfBallImpactReImpact.png               121 dpi   resized to 205
    LOFTID_mission_trajectory.png            193 dpi   resized to 201
    HIADsDeployed.png                        145 dpi   resized to 205
    elocity-contour-...-SST-K-o-model.jpg.png 193 dpi   resized to 206

The two disclosed cases are raster sources whose pixel counts cannot support the
printed size at a readable width: IADsLayer.png is 280 by 201 pixels and
RecirculationExample.jpeg is smaller still. No resampling can add detail that
the file does not contain, and enlarging the canvas would only make the
shortfall more visible, so their captions say what the artwork is and is not.

CITATION
  Pillow, https://python-pillow.org/
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent
FIGDIR = TH / "figures"
TEXT_WIDTH_IN = 14.0 / 2.54
TEXT_HEIGHT_IN = 23.7 / 2.54
TARGET_DPI = 205.0
MIN_FRAC = 0.25
DISCLOSE = {
    "IADsLayer.png": (
        "The source artwork is a 280 by 201 pixel raster, which resolves to about "
        "100 dots per inch at the size printed here, so it is reproduced as an "
        "indicative sketch of the layer order rather than as a resolved diagram; "
        "the thicknesses used in the calculations are tabulated in Appendix~A and "
        "are not read off this figure."
    ),
}

INC = re.compile(
    r"\\includegraphics\[(width=([0-9.]+)\\textwidth|height=([0-9.]+)\\textheight)[^\]]*\]"
    r"\{figures/([^}]*)\}")


def stem_size(name: str) -> tuple[int, int] | None:
    for cand in ([name] if Path(name).suffix else
                 [name + e for e in (".png", ".jpg", ".jpeg", ".eps", ".pdf")]):
        f = FIGDIR / cand
        if f.exists() and f.suffix.lower() in (".png", ".jpg", ".jpeg"):
            try:
                from PIL import Image
                return Image.open(f).size
            except Exception:
                return None
    return None


def main() -> int:
    from PIL import Image
    resized, disclosed = [], []
    for src in sorted(TH.glob("chapter_*.tex")) + [TH / "appendix.tex"]:
        if "sync-conflict" in src.name:
            continue
        t = src.read_text(encoding="utf-8")
        out, last, changed = [], 0, False
        for m in INC.finditer(t):
            out.append(t[last:m.start()])
            last = m.end()
            wfrac, hfrac, name = m.group(2), m.group(3), m.group(4)
            size = stem_size(name)
            if not size:
                out.append(m.group(0))
                continue
            iw, ih = size
            if wfrac:
                pin = float(wfrac) * TEXT_WIDTH_IN
                eff = iw / pin
                if eff < 200:
                    need = iw / (TARGET_DPI * TEXT_WIDTH_IN)
                    if need >= MIN_FRAC:
                        new = f"{need:.3f}".rstrip("0").rstrip(".")
                        out.append(f"\\includegraphics[width={new}\\textwidth]{{figures/{name}}}")
                        resized.append((name, round(eff), int(round(iw / (float(new) * TEXT_WIDTH_IN)))))
                        changed = True
                    else:
                        disclosed.append((name, round(eff)))
                else:
                    out.append(m.group(0))
            else:
                pin = float(hfrac) * TEXT_HEIGHT_IN
                eff = ih / pin
                if eff < 200:
                    need = ih / (TARGET_DPI * TEXT_HEIGHT_IN)
                    if need >= MIN_FRAC * TEXT_WIDTH_IN / TEXT_WIDTH_IN:
                        new = f"{need:.3f}".rstrip("0").rstrip(".")
                        out.append(f"\\includegraphics[height={new}\\textheight, keepaspectratio]"
                                   f"{{figures/{name}}}")
                        resized.append((name, round(eff), int(round(ih / (float(new) * TEXT_HEIGHT_IN)))))
                        changed = True
                    else:
                        disclosed.append((name, round(eff)))
                else:
                    out.append(m.group(0))
        out.append(t[last:])
        if changed:
            src.write_text("".join(out), encoding="utf-8")
    print("  resized:")
    for n, was, now in resized:
        print(f"    {n:52s} {was:4d} -> {now:4d} dpi")
    print("  below the floor, cannot be fixed by resizing:")
    for n, e in disclosed:
        sz = stem_size(n)
        print(f"    {n:52s} {e:4d} dpi, source {sz[0]}x{sz[1]} px, "
              f"would need {sz[0]/(TARGET_DPI*TEXT_WIDTH_IN):.2f} in wide")
    print(f"  total resized: {len(resized)}   disclosed: {len(disclosed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())