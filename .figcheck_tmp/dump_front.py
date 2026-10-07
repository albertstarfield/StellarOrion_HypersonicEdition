"""Dump the first N pages of a PDF as plain text, one page per block.

AXIOMS:
  1. Page numbering in the printed document is authoritative; PDF index is 0-based.
  2. pdfminer.six is the project's installed text extractor.
THEORIES:
  - extract_text(pdf, page_numbers=[...]) returns the concatenated page text.
APPLICATIONS:
  Usage: .venv-pdf/bin/python3 .figcheck_tmp/dump_front.py <pdf> <first1based> <last1based>
"""
from __future__ import annotations

import sys

from pdfminer.high_level import extract_text


def main() -> int:
    """Print each requested page's text under a page header."""
    if len(sys.argv) < 4:
        print("usage: dump_front.py <pdf> <first1based> <last1based>", file=sys.stderr)
        return 2
    pdf, first, last = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 320
    for p in range(first, last + 1):
        try:
            text = extract_text(pdf, page_numbers=[p - 1]) or ""
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"===== page {p}: EXTRACTION ERROR {exc!r}")
            continue
        body = " ".join(text.split())
        print(f"===== page {p}: {body[:limit]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
