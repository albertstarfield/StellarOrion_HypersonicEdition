#!/usr/bin/env python3
"""Map thesis page spans per section from main.toc to locate cut candidates.

Reads main.toc (hyperref contentsline entries), converts body folios to PDF page
indices using the auto-detected body offset (measured from the rendered PDF), and
prints each section's page range and length so verbose areas are visible at a
glance. The final span ends at the real last page of main.pdf, never a stale
hardcoded count.

Exceptions: none expected; missing/unparsable entries are skipped with a note.
"""

import re
from pathlib import Path

import pypdfium2 as pdfium


def body_offset_1based() -> int:
    """Return the 1-based pdf page of body folio 1 (chapter 1 opener).

    Measured from the rendered PDF so list shortening or added front pages
    cannot silently invalidate the map.

    Parameters: none.
    Returns: int folio1_pdf_page - 1, added to arabic folios.
    Exceptions: RuntimeError when the opener heading cannot be located.
    """
    pdf = pdfium.PdfDocument("main.pdf")
    for i in range(11, len(pdf)):
        t = pdf[i].get_textpage().get_text_range()
        t = re.sub(r"[\uFFFC-\uFFFF\u200B\uFEFF]", "", t)
        if "CHAPTER 1" in t and ("INTRODUCTION" in t or "Introduction" in t):
            return i  # folio-1 offset equals the 0-based index of that page
    raise RuntimeError("body chapter-1 opener not found; front matter unexpected")


def main() -> None:
    """Parse main.toc and print section page spans (pdf pages)."""
    toc = Path("main.toc").read_text(encoding="utf-8")
    BODY_OFFSET = body_offset_1based()
    LAST_PAGE = len(pdfium.PdfDocument("main.pdf"))
    pat = re.compile(
        r"\\contentsline \{(section)\}\{\\numberline \{([^}]*)\}([^}]*)\}\{(\d+|[ivxlcdm]+)\}"
    )
    rows = []
    for kind, num, title, folio in pat.findall(toc):
        if folio.isdigit():
            rows.append((int(folio) + BODY_OFFSET, num, title.strip()))
    # Chapter-level spans too
    chap_pat = re.compile(
        r"\\contentsline \{chapter\}\{\\numberline \{([^}]*)\}([^}]*)\}\{(\d+|[ivxlcdm]+)\}"
    )
    chapters = []
    for num, title, folio in chap_pat.findall(toc):
        if folio.isdigit():
            chapters.append((int(folio) + BODY_OFFSET, num, title.strip()))
    print("CHAPTERS (pdf pages):")
    for i, (p, num, title) in enumerate(chapters):
        end = chapters[i + 1][0] - 1 if i + 1 < len(chapters) else LAST_PAGE
        print(f"  pdf {p:3d}-{end:3d} ({end - p + 1:3d}pp)  ch{num} {title[:55]}")
    print("SECTIONS (pdf pages):")
    for i, (p, num, title) in enumerate(rows):
        end = rows[i + 1][0] - 1 if i + 1 < len(rows) else LAST_PAGE
        span = end - p + 1
        print(f"  pdf {p:3d}-{end:3d} ({span:3d}pp)  {num:>6} {title[:52]}")


if __name__ == "__main__":
    main()
