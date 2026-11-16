#!/usr/bin/env python3
"""Measure inter-word gaps on one page so word-space rivers cannot regress.

WHY THIS EXISTS. A readability audit of chapter 2 measured two lines whose
inter-word gaps ran 2.69x and 3.56x the median gap of their neighbours, the
classic river that pulls the eye down the page instead of across the line.
The paragraph was rewritten to close that defect, and this probe re-measures
the gaps so the fix is verified in the rendered PDF rather than assumed from
the source.

PARAMETERS. None. The target page is found by searching for a unique phrase
from the paragraph, so the probe follows the text when pagination shifts.

RETURNS. 0 when no line's median gap exceeds RIVER_RATIO times the page
median, 1 when a river is found, 2 when the page or phrase cannot be found.

EXCEPTIONS. RuntimeError when the PDF is missing or unreadable; the caller
gets a non-zero return code rather than a trace.

CITATIONS.
- pdfplumber 0.11.10, word extraction with coordinates,
  https://github.com/jsvine/pdfplumber

AXIOMS.
A1. Words on one justified line are separated by spaces whose width is set by
    the paragraph breaker, so a gap far wider than its neighbours is a river.
A2. The page median gap is the reference because it is the width the breaker
    actually used on that page, independent of the font size.

THEORIES.
T1. A line whose smallest gap exceeds RIVER_RATIO times the page median has
    at least one river, because even its tightest spacing is looser than the
    typical spacing elsewhere.

APPLICATIONS.
A1. Run after any edit that re-flows a paragraph measured for rivers.
A2. Any page where a readability audit reported a word-space river.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pdfplumber

PDF_NAME = "main.pdf"
# A phrase unique to the rewritten chapter-2 paragraph.
NEEDLE = "both paradigms"
# A gap wider than this multiple of the page median is a river.
RIVER_RATIO = 2.5
# Gaps wider than this are math operators or display-equation spacing, not
# word-space rivers, so they are excluded from the measurement.
MATH_GAP_PT = 30.0
# Lines with fewer words than this are headings, captions or display
# equations, not body prose, so they are excluded.
MIN_PROSE_WORDS = 6


def page_median_gap(words: list[dict]) -> float:
    """Return the median horizontal gap between consecutive words per line.

    Parameters: words, the pdfplumber word dicts for one page.

    Returns: the median of all same-line consecutive-word gaps.

    Raises: RuntimeError when fewer than two words share a line.
    """
    lines: dict[int, list[dict]] = {}
    for w in words:
        key = round(w["top"], 1)
        lines.setdefault(key, []).append(w)
    gaps: list[float] = []
    for line_words in lines.values():
        line_words.sort(key=lambda w: w["x0"])
        for a, b in zip(line_words, line_words[1:]):
            gaps.append(b["x0"] - a["x1"])
    if not gaps:
        raise RuntimeError("no same-line word pairs to measure")
    gaps.sort()
    return gaps[len(gaps) // 2]


def line_gaps(words: list[dict], top: float) -> list[float]:
    """Return the prose gaps on the line whose top matches.

    Gaps wider than MATH_GAP_PT are math operators or display-equation
    spacing, not word-space rivers, so they are dropped.

    Parameters: words, the page word dicts; top, the line top to match.

    Returns: the list of gaps on that line, empty if the line is not found.

    Raises: nothing.
    """
    line = [w for w in words if abs(w["top"] - top) < 2.0]
    line.sort(key=lambda w: w["x0"])
    return [b["x0"] - a["x1"] for a, b in zip(line, line[1:])
            if b["x0"] - a["x1"] <= MATH_GAP_PT]


def main() -> int:
    """Measure the paragraph page and report any word-space river.

    Returns: 0 no river, 1 river found, 2 measurement failure.

    Raises: nothing; failures are caught and reported.
    """
    pdf = Path(PDF_NAME)
    if not pdf.is_file():
        print(f"MEASURE FAIL: missing {pdf}")
        return 2
    try:
        with pdfplumber.open(str(pdf)) as doc:
            target = None
            for pageno, page in enumerate(doc.pages, start=1):
                text = page.extract_text() or ""
                if NEEDLE in text:
                    target = (pageno, page)
                    break
            if target is None:
                print(f"MEASURE FAIL: phrase {NEEDLE!r} not found")
                return 2
            pageno, page = target
            words = page.extract_words()
            median = page_median_gap(words)
            print(f"page {pageno}: {len(words)} words, median gap {median:.2f} pt")
            lines: dict[int, list[dict]] = {}
            for w in words:
                key = round(w["top"], 1)
                lines.setdefault(key, []).append(w)
            rivers = 0
            for top in sorted(lines):
                line = lines[top]
                if len(line) < MIN_PROSE_WORDS:
                    continue
                gaps = line_gaps(words, top)
                if not gaps:
                    continue
                small = min(gaps)
                if small > RIVER_RATIO * median:
                    rivers += 1
                    print(f"  RIVER line top={top:.1f} min gap {small:.2f} pt "
                          f"({small / median:.2f}x median)")
            if rivers:
                print(f"VERDICT: FAIL ({rivers} river line(s), "
                      f"ratio {RIVER_RATIO:.1f}x)")
                return 1
            print(f"VERDICT: PASS (no gap exceeds {RIVER_RATIO:.1f}x median)")
            return 0
    except Exception as exc:                              # noqa: BLE001 report
        print(f"MEASURE FAIL: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
