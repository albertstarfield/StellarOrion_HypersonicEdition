#!/usr/bin/env python3
"""Measure real inter-word gaps on a rendered thesis page, plus dump its text layer.

PURPOSE
    Decide, by pixel measurement rather than by OCR, whether the inter-word
    spaces on a given page are really present. An OCR transcription can lose
    spaces and can also hallucinate characters, so a claim of "destroyed word
    spacing" must be checked against the ink profile before any source file is
    edited. This script renders the page, slices it into text line bands,
    measures every white column run that lies between two ink clusters inside
    a band, and converts those runs to printed points. It also prints the page
    text layer so the glyph sequence can be compared with the measurement.

PARAMETERS
    None. Configuration is in the constants block below.

RETURNS
    Zero when the measurement runs to completion. The per-line gap statistics
    are printed to standard output.

EXCEPTIONS
    RuntimeError: raised when the page cannot be rendered, when the crop is
        empty of ink, or when the render produces an image with no width.

CITATIONS
    pypdfium2 v4.30.0, https://github.com/pypdfium2-team/pypdfium2
    Pillow v12.3.0, https://python-pillow.org/
    NumPy v2.x, https://numpy.org/doc/stable/

AXIOMS
    A1  A space in justified 12 pt body text renders as a run of fully white
        image columns at least 3 pt wide at 2 pixels per point.
    A2  An inter-word gap is a white run bounded on BOTH sides by ink in the
        same horizontal band. A white run bounded by a line break is not a
        word space and must be excluded by processing one band per line.
    A3  2.0 pixels per point holds for a page rendered at 144 dpi, so one
        pixel is half a point.

THEORIES
    T1  If the word spaces were truly destroyed, the measured inter-word gaps
        inside a line band would be zero or near zero. If the measured gaps
        cluster around 7 pixels, the spaces are intact and any transcription
        that lost them is a tool artifact.
    T2  A white run wider than about 30 pixels inside a band is a sentence
        space or a stretched justification gap, not a plain word space, so the
        distribution must be reported as a whole rather than as a single
        minimum.

APPLICATIONS
    A1  Audit of page 65 of the thesis PDF, the page carrying the paragraph
        that begins "This study employs both paradigms", to settle a reported
        text corruption claim.
    A2  Any future page whose prose is questioned by a text extraction tool.
"""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "main.pdf"

# Page to audit, one based, as printed in the PDF page counter.
PAGE_NUMBER = 65

# Scale in pixels per point. 144 dpi gives exactly 2.0.
PX_PER_PT = 2.0
# pypdfium2 scales a page so that one PDF point maps to `scale` pixels, which
# is 72 dpi at scale 1. So the render scale IS the pixels per point, and
# dividing by 72 here would shrink the page to a thumbnail.
# [Citation: pypdfium2 v4.30.0 - PdfPage.render(scale=...)]
RENDER_SCALE = PX_PER_PT

# Ink threshold on the maximum channel value. Below this a pixel is ink.
INK_MAX = 250

# Each line band is trimmed by this many pixels at each edge so the ascenders
# and descenders of the neighbouring line cannot enter the band.
BAND_TRIM_PX = 3

# Row gap, in rendered pixels, that separates one line of body text from the
# next. Measured on the audited page: consecutive line bands are separated by
# 14 to 16 empty rows, while a single line never has 7 fully empty rows inside
# it. The axis therefore picks line boundaries rather than splitting a line.
LINE_GAP_PX = 7

# Gap classes in printed points, used to classify each measured white run.
GAP_SPACE_MAX_PT = 12.0
GAP_SENTENCE_MIN_PT = 12.0


def render_page(path: Path, page_number: int) -> Image.Image:
    """Render one one-based page of a PDF to a PIL image.

    Parameters
        path: PDF file to render.
        page_number: one based page index inside the document.

    Returns
        The rendered page as an RGB image.

    Raises
        RuntimeError: when the document cannot be opened or the page index is
            out of range.
    """
    # [Citation: pypdfium2 v4.30.0 - PdfDocument.new and PdfPage.render]
    if not path.is_file():
        raise RuntimeError(f"missing PDF: {path}")
    document = pdfium.PdfDocument(str(path))
    try:
        if page_number < 1 or page_number > len(document):
            raise RuntimeError(f"page {page_number} outside 1..{len(document)}")
        page = document[page_number - 1]
        bitmap = page.render(scale=RENDER_SCALE)
        image = bitmap.to_pil().convert("RGB")
    finally:
        document.close()
    if image.width == 0:
        raise RuntimeError("rendered page has zero width")
    return image


def band_gaps(gray: np.ndarray, y0: int, y1: int) -> list[int]:
    """Return the widths of every white column run bounded by ink in a band.

    Parameters
        gray: two dimensional array of ink values, one row per pixel.
        y0: first row of the band, inclusive.
        y1: last row of the band, exclusive.

    Returns
        Widths in pixels of the interior white runs, in ascending column order.

    Raises
        RuntimeError: when the band lies outside the image.
    """
    rows, cols = gray.shape
    if y0 < 0 or y1 > rows or y1 <= y0:
        raise RuntimeError(f"band {y0}:{y1} outside 0:{rows}")
    strip = gray[y0:y1, :]
    column_ink = (strip < INK_MAX).any(axis=0)
    ink_columns = np.flatnonzero(column_ink)
    if ink_columns.size == 0:
        return []
    gaps: list[int] = []
    run_start: int | None = None
    for col in range(int(ink_columns[0]), int(ink_columns[-1]) + 1):
        if not column_ink[col]:
            if run_start is None:
                run_start = col
        elif run_start is not None:
            gaps.append(col - run_start)
            run_start = None
    return gaps


def classify(gaps: list[int]) -> dict[str, object]:
    """Summarise a gap list in printed points.

    Parameters
        gaps: white run widths in pixels.

    Returns
        Dictionary with the count, the minimum, the median and the maximum gap
        in points, plus the counts of spaces and sentence spaces.
    """
    points = [g / PX_PER_PT for g in gaps]
    if not points:
        return {"n": 0}
    spaces = [p for p in points if p <= GAP_SPACE_MAX_PT]
    sentences = [p for p in points if p >= GAP_SENTENCE_MIN_PT]
    return {
        "n": len(points),
        "min_pt": round(min(points), 2),
        "median_pt": round(statistics.median(points), 2),
        "max_pt": round(max(points), 2),
        "n_space": len(spaces),
        "n_sentence": len(sentences),
    }


def auto_bands(gray: "np.ndarray") -> list[tuple[int, int]]:
    """Locate the line bands of the body text block without hand-measured rows.

    A band is a maximal run of rows that carry at least one ink pixel, split
    wherever LINE_GAP_PX consecutive rows carry none. Hard-coded band extents
    go stale the moment a paragraph is re-worded, which is exactly when the
    spacing has to be re-measured, so the rows are found instead.

    Parameters
        gray: two-dimensional page luminance array in uint8.

    Returns
        The list of (first_row, last_row) inclusive bands, top of page first.

    Raises
        RuntimeError: when fewer than two bands are found, because a single
            band means the gap threshold is wrong for this page.
    """
    rows = (gray < INK_MAX).any(axis=1)
    bands: list[tuple[int, int]] = []
    start = None
    empty = 0
    for index, has_ink in enumerate(rows):
        if has_ink:
            if start is None:
                start = index
            empty = 0
        elif start is not None:
            empty += 1
            if empty >= LINE_GAP_PX:
                bands.append((start, index - empty))
                start = None
                empty = 0
    if start is not None:
        bands.append((start, len(rows) - 1))
    if len(bands) < 2:
        raise RuntimeError(
            f"found {len(bands)} band(s); LINE_GAP_PX={LINE_GAP_PX} does not "
            "separate the lines of this page")
    return bands


def text_layer(path: Path, page_number: int) -> str:
    """Return the text layer of one one-based page.

    Parameters
        path: PDF file to read.
        page_number: one based page index inside the document.

    Returns
        The page text with runs of whitespace collapsed to single spaces.

    Raises
        RuntimeError: when the page index is out of range.
    """
    document = pdfium.PdfDocument(str(path))
    try:
        page = document[page_number - 1]
        text = page.get_textpage().get_text_range()
    finally:
        document.close()
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    """Render the audited page, measure its line bands and print the text.

    Returns
        Zero when the audit completes.

    Raises
        RuntimeError: propagated from the helpers on any measurement failure.
    """
    page = int(sys.argv[1]) if len(sys.argv) > 1 else PAGE_NUMBER
    image = render_page(PDF_PATH, page)
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    print(f"page {page}: {image.width}x{image.height} px, {PX_PER_PT} px per pt")
    print(f"page {page} bands (y0, y1, gap statistics):")
    for y0, y1 in auto_bands(gray):
        gaps = band_gaps(gray, y0 + BAND_TRIM_PX, y1 - BAND_TRIM_PX)
        print(f"  band {y0:4d} to {y1:4d}: {classify(gaps)}")
    print()
    print(f"page {page} text layer:")
    print(text_layer(PDF_PATH, page))
    return 0


if __name__ == "__main__":
    sys.exit(main())