#!/usr/bin/env python3
"""Extract the structural skeleton of a thesis PDF (outline, TOC text, headings).

PURPOSE
    Read a thesis PDF and print (a) its PDF outline/bookmarks, (b) the raw text
    of its first pages so a printed table of contents can be read, and (c) every
    line that looks like a numbered section heading. Used to diff the reference
    "standard layout" thesis against the current thesis and find missing sections.

AXIOMS
    1. A thesis' section list is recoverable from either the embedded PDF outline
       or the printed table of contents; both are inspected and reported.
    2. Heading detection is heuristic: a line is treated as a heading when it
       matches a numbering pattern ("1.2", "Chapter 3", "3.1.2") OR is short
       (< 70 chars) and contains no terminal full stop.

PARAMETERS
    argv[1] : str - path of the PDF to inspect.

RETURNS
    None. Writes a report to stdout.

EXCEPTIONS
    FileNotFoundError - the PDF path does not exist.
    RuntimeError      - the PDF could not be opened by pypdfium2.

CITATIONS
    [pypdfium2 5.14.0 - https://pypi.org/project/pypdfium2/]
    [pdfplumber 0.11.10 - https://github.com/jsvine/pdfplumber]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _outline(path: Path) -> list[tuple[int, str]]:
    """Return the PDF bookmark outline as (level, title) pairs.

    PARAMETERS
        path : Path - the PDF file.

    RETURNS
        list of (level, title). Empty when the PDF has no outline.

    EXCEPTIONS
        RuntimeError - if pypdfium2 cannot open the document.
    """
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    out: list[tuple[int, str]] = []
    for i in range(len(pdf)):
        # pypdfium2 exposes bookmarks per page via get_toc(); we collect once.
        pass
    try:
        toc = pdf.get_toc()
    except Exception as exc:  # pragma: no cover - API variance across versions
        raise RuntimeError(f"pypdfium2 get_toc failed: {exc}") from exc
    for item in toc:
        # item is [level, title, page_index, ...]
        level = int(item[0])
        title = str(item[1]).strip()
        out.append((level, title))
    return out


def _text_pages(path: Path, first: int, last: int) -> list[tuple[int, str]]:
    """Return (page_number, text) for pages in [first, last] (1-based, inclusive).

    PARAMETERS
        path  : Path - the PDF file.
        first : int  - first 1-based page number.
        last  : int  - last 1-based page number (clamped to the document length).

    RETURNS
        list of (1-based page number, page text).

    EXCEPTIONS
        RuntimeError - if pdfminer.six cannot open the document.

    CITATIONS
        [pdfminer.six 20260107 - https://pdfminersix.readthedocs.io]
    """
    from pdfminer.high_level import extract_text

    pages: list[tuple[int, str]] = []
    try:
        for pno in range(first, last + 1):
            txt = extract_text(str(path), page_numbers=[pno - 1]) or ""
            pages.append((pno, txt))
    except Exception as exc:
        raise RuntimeError(f"pdfminer extract_text failed: {exc}") from exc
    return pages


_NUM = re.compile(r"^(?:\d+(?:\.\d+)*)\s+\S")
_CHAP = re.compile(r"^(?:Chapter|CHAPTER|Appendix|APPENDIX)\s+[0-9A-Z]")


def _heading_like(lines: list[str]) -> list[str]:
    """Filter a page's lines down to those that look like headings.

    PARAMETERS
        lines : list[str] - raw text lines.

    RETURNS
        list[str] of candidate heading lines (order preserved, de-duplicated).

    EXCEPTIONS
        None.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in lines:
        s = raw.strip()
        if not s or len(s) > 80:
            continue
        is_heading = bool(_NUM.match(s) or _CHAP.match(s))
        if not is_heading and len(s) <= 60 and s[-1] not in ".!,;:?":
            # short, no terminal punctuation -> possibly a bare heading
            is_heading = s[0].isupper() and s.lower() not in {"references", "bibliography"}
        if is_heading and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main() -> None:
    """Entry point: print outline, early-page text, and candidate headings.

    PARAMETERS
        None (reads sys.argv).

    RETURNS
        None.

    EXCEPTIONS
        SystemExit - when argv is wrong or the file is missing.
    """
    if len(sys.argv) < 2:
        print("usage: compare_structure.py <pdf>", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    print(f"### FILE: {path.name}")
    print(f"### SIZE: {path.stat().st_size} bytes")

    toc = _outline(path)
    print(f"\n### OUTLINE ({len(toc)} entries)")
    for level, title in toc:
        print(f"{'  ' * (level - 1)}{title}")

    print("\n### EARLY PAGES (1-8) RAW TEXT")
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    last = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    print(f"\n### PAGES {first}-{last} RAW TEXT")
    for pno, txt in _text_pages(path, first, last):
        print(f"\n----- page {pno} -----")
        print(txt)


if __name__ == "__main__":
    main()
