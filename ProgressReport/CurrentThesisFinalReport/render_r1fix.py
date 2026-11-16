#!/usr/bin/env python3
"""Render the round-1 fix pages (IAD/ISA expansion, gate cite) to PNGs.

Locates each probe sentence in main.pdf and saves a 1.5x render as
r1fix_<key>_p<N>.png for visual/readability verification.

Usage (workdir = thesis dir): .venv-pdf/bin/python render_r1fix.py
"""
import re

import pypdfium2 as pdfium

PROBES = {
    "iad": "Inflatable Aerodynamic Decelerator (IAD) the bow shock",
    "isa": "International Standard Atmosphere (ISA) freestream density",
    "gate": "Two tolerance statements apply",
}


def flat(text):
    """Normalise extracted text: strip invisible chars and line-break hyphens."""
    clean = re.sub(r"[\uFFFC-\uFFFF\u200B\uFEFF]", "", text)
    # pdfium emits \r (and \r\n) at wrapped lines; normalise to plain spaces.
    clean = clean.replace("\r", " ").replace("\n", " ")
    # Line-break hyphenation inserts "- " between syllables; remove it so
    # probes match across wrapped words (e.g. "Atmos-phere" -> "Atmosphere").
    clean = re.sub(r"(\w)-\s+(\w)", r"\1\2", clean)
    # \r replacements can double spaces; collapse runs of whitespace.
    return re.sub(r" {2,}", " ", clean)


def page_text(page):
    """Extract one page's text with invisible characters stripped."""
    raw = page.get_textpage().get_text_range()
    clean = re.sub(r"[\uFFFC-\uFFFF\u200B\uFEFF]", "", raw)
    return clean.replace("\n", " ")


def main():
    """Find each probe's page, render it, print page numbers."""
    pdf = pdfium.PdfDocument("main.pdf")
    found = {}
    for i in range(len(pdf)):
        text = flat(page_text(pdf[i]))
        for key, probe in PROBES.items():
            if key not in found and probe in text:
                found[key] = i + 1
    for key, page in sorted(found.items()):
        pdf[page - 1].render(scale=1.5).to_pil().save(f"r1fix_{key}_p{page}.png")
        print(key, "pdf page", page)
    missing = set(PROBES) - set(found)
    print("missing:", missing or "none")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
