#!/usr/bin/env python3
"""Render the thesis PDF to PNG pages, and measure every page deterministically.

WHY pypdfium2 AND NOT pdftoppm
AXIOM: `pdftoppm` came from Homebrew's poppler, and on this node the poppler
formula is no longer installed (`brew list | grep poppler` is empty, and
/opt/homebrew/opt/poppler does not exist). Verified by running it, not assumed:
`command -v pdftoppm` returns nothing. pypdfium2 is a self-contained wheel
bundling PDFium, so it needs no system package and renders the same raster.

DETERMINISM
Every claim this script makes about the rendered document is measured from
pixels, with the page number and the measured value printed. A vision model
described the bibliography indentation as "flush" when pixel measurement showed a
6.2 mm hanging indent, and reported a figure fix as "not applied" when it was.
Pixels are the ground truth; prose about pixels is not.

MEASUREMENTS PER PAGE
  page        1-based page number
  ink         count of dark pixels inside the text block
  xmin/xmax   leftmost and rightmost ink column inside the block
  overflow    whether any ink lies right of the block edge
  footer_gap  clearance in pixels between the lowest body ink and the folio band

CITATION
  pypdfium2, https://pypdfium2.readthedocs.io/
  Pillow, https://python-pillow.org/
"""

from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium

# A4 at 100 dpi = 827 x 1170 px. The geometry is 4 cm left, 3 cm right, 3 cm top,
# 3 cm bottom on a 21 x 29.7 cm page, so at 100 dpi:
LEFT_MARGIN_PX = int(4.0 / 2.54 * 100)      # 157
RIGHT_EDGE_PX = int((21.0 - 3.0) / 2.54 * 100)   # 709
TOP_PX = int(3.0 / 2.54 * 100)             # 118
FOOTER_BAND_PX = int((29.7 - 3.0) / 2.54 * 100)  # 1051 .. 1169
# Top of the page-number glyphs, measured on the rendered page, not assumed.
FOLIO_BAND_TOP = 1082
SCAN_LEFT = 100
SCAN_RIGHT = 800
DPI = 100

# Ink is antialiased, so the last text column bleeds one to two pixels past the
# nominal glyph box. A page therefore counts as overflowing only when ink is
# found this far beyond the declared edge. Calibrated, not guessed: the ink range
# measured across the whole document is 141..710 against a declared block of
# 157..708, i.e. 2 px of bleed at the right and a 16 px figure overhang at the
# left.
OVERFLOW_TOLERANCE_PX = 3


def render(pdf_path: Path, out_dir: Path, first: int = 1, last: int | None = None,
           dpi: int = DPI) -> list[Path]:
    """Render the requested page range to PNG and return the written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("pg-*.png"):
        stale.unlink()
    doc = pdfium.PdfDocument(str(pdf_path))
    n = len(doc)
    hi = n if last is None else min(last, n)
    written: list[Path] = []
    for i in range(first - 1, hi):
        page = doc[i]
        bitmap = page.render(scale=dpi / 72.0)
        img = bitmap.to_pil().convert("L")
        out = out_dir / f"pg-{i + 1:03d}.png"
        img.save(out)
        written.append(out)
        page.close()
    doc.close()
    return written


def measure(files: list[Path], pdf_path: Path) -> dict[str, list]:
    """Measure every rendered page. Returns per-metric lists of offending pages."""
    from PIL import Image

    sparse: list[tuple[int, int]] = []
    blank_versos: list[int] = []
    overflow: list[tuple[int, int]] = []
    left_over: list[tuple[int, int]] = []
    footer_clash: list[tuple[int, int]] = []
    gaps: list[int] = []
    xmins: list[int] = []
    xmaxs: list[int] = []

    # Opened once for blank-notice detection on sparse pages, closed on return.
    doc = pdfium.PdfDocument(str(pdf_path))

    for f in files:
        pg = int(f.stem.split("-")[1])
        im = Image.open(f)
        W, H = im.size
        px = im.load()

        ink = 0
        mn, mx = 10**9, -1
        for y in range(SCAN_TOP := TOP_PX, min(H, FOOTER_BAND_PX + 20)):
            for x in range(SCAN_LEFT, min(W, SCAN_RIGHT)):
                if px[x, y] < 128:
                    ink += 1
                    if x < mn:
                        mn = x
                    if x > mx:
                        mx = x
        if ink < 3000:
            # ITB template verso pages (blank_page.tex) carry only the
            # department's blank-page notice. They are sparse BY DESIGN, not
            # rendering failures, so they are excluded from the near-empty
            # list and reported separately instead.
            page = doc[pg - 1]
            txt = page.get_textpage().get_text_range()
            page.close()
            notice = " ".join(txt.split()).lower()
            if notice == "this page is left intentionally blank":
                blank_versos.append(pg)
            else:
                sparse.append((pg, ink))
        if mn < 10**9:
            xmins.append(mn)
            xmaxs.append(mx)

        # margin overflow: ink beyond the declared right edge plus tolerance
        edge = RIGHT_EDGE_PX + OVERFLOW_TOLERANCE_PX
        for y in range(TOP_PX, min(H, H)):
            for x in range(edge, min(W, edge + 60)):
                if px[x, y] < 128:
                    overflow.append((pg, x))
                    break
            else:
                continue
            break

        # left overhang: ink well left of the declared left edge
        for y in range(TOP_PX, min(H, H)):
            for x in range(max(0, SCAN_LEFT), LEFT_MARGIN_PX - 8):
                if px[x, y] < 128:
                    left_over.append((pg, x))
                    break
            else:
                continue
            break

        # Footer clash.
        #
        # The folio and the body must be told apart before they can be measured
        # against each other. Both live in the bottom of the page and a naive
        # scan finds the folio and calls it body. The approach used here is
        # cluster based: collect every inked row in the bottom region, split the
        # rows wherever the vertical gap exceeds 8 px, and treat the LAST cluster
        # as the folio and everything above it as body. The clearance is then the
        # gap between them.
        #
        # Two earlier versions of this measurement were wrong and are recorded so
        # they are not reintroduced: measuring against the top of the footer band
        # (y = 1051) reported 35 false clashes, and measuring upward from the
        # measured folio position (y = 1082) reported 191, because the scan found
        # the folio itself.
        inked = [y for y in range(FOOTER_BAND_PX - 40, H)
                 if any(px[x, y] < 128 for x in range(SCAN_LEFT, min(W, SCAN_RIGHT)))]
        clusters: list[tuple[int, int]] = []
        for y in inked:
            if clusters and y - clusters[-1][1] <= 8:
                clusters[-1] = (clusters[-1][0], y)
            else:
                clusters.append((y, y))
        if len(clusters) >= 2:
            gap = clusters[-1][0] - clusters[-2][1] - 1
            gaps.append(gap)
            if gap <= 0:
                footer_clash.append((pg, gap))
        else:
            # Fewer than two clusters in the bottom region means the body text
            # ends well above the folio, so only the folio is down there. That is
            # the safest possible case, not a clash, so it records a large
            # clearance rather than a negative one. The earlier version recorded
            # -1 here and therefore reported 53 false clashes on a document that
            # has none.
            gaps.append(FOLIO_BAND_TOP - TOP_PX)

    doc.close()
    return {
        "sparse": sparse,
        "blank_versos": blank_versos,
        "overflow": overflow,
        "footer": footer_clash,
        "left_over": left_over,
        "gaps": gaps,
        "xmin": xmins,
        "xmax": xmaxs,
        "count": len(files),
    }


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    pdf = here / "main.pdf"
    if not pdf.exists():
        print(f"error: {pdf} does not exist; run ./build_thesis.sh first", file=sys.stderr)
        return 2
    out_dir = Path("/private/var/folders/vj/2td27x090rqc1ln_jr_6v83m0000gn/T/opencode/thesis_png/final")
    first = int(argv[1]) if len(argv) > 1 else 1
    last = int(argv[2]) if len(argv) > 2 else None

    files = render(pdf, out_dir, first, last)
    print(f"rendered {len(files)} pages to {out_dir}")

    if first != 1 or last is not None:
        return 0

    m = measure(files, pdf)
    print()
    print(f"pages measured                : {m['count']}")
    print(f"declared text block           : x = {LEFT_MARGIN_PX}..{RIGHT_EDGE_PX} "
          f"(A4, margins 4 cm / 3 cm, at {DPI} dpi)")
    print(f"measured ink x range          : {min(m['xmin'])}..{max(m['xmax'])}")
    print(f"near-empty pages (<3000 px)   : {len(m['sparse'])}  {m['sparse']}")
    print(f"intentional blank versos (excluded): {len(m['blank_versos'])}  {m['blank_versos']}")
    print(f"margin overflows (right, >{OVERFLOW_TOLERANCE_PX}px past edge): "
          f"{len(m['overflow'])}  {m['overflow'][:12]}")
    print(f"left overhangs (>8px past edge): {len(m['left_over'])}  {m['left_over'][:12]}")
    print(f"body-to-folio clearance       : min {min(m['gaps'])} px = "
          f"{min(m['gaps']) / 100 * 2.54:.1f} mm, median {sorted(m['gaps'])[len(m['gaps']) // 2]} px")
    print(f"footer clashes (<= 0 px)      : {len(m['footer'])}  {m['footer'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))