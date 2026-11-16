#!/usr/bin/env python3
"""Render the pages containing the 9 citation-adjacency reword fixes.

AXIOMS:
  A1. Every source edit must be verified in the rendered PDF (goal rev 3).
  A2. pdfium text needs invisible-char stripping and whitespace collapse for
      reliable phrase probes (line breaks otherwise split matches).

THEORIES:
  T1. Probing the rebuilt main.pdf for each new phrasing locates its page;
      rendering that page at scale 1.5 gives an inspectable PNG.

APPLICATIONS:
  Run: .venv-pdf/bin/python render_citefix.py  (from the thesis directory)
  Writes citefix_<key>_p<N>.png (temp, NEVER committed); exit 1 on miss.

CITATIONS:
  [Citation: pypdfium2 - https://pypi.org/project/pypdfium2/]
"""
import re
import sys
import pypdfium2 as pdfium

PROBES = {
    "golf": "as documented by (Anderson",
    "calor": "where Ma > 5 (Anderson",
    "suth": "Law of 1893 (Anderson",
    "pinn": "and initial conditions (Raissi",
    "summary": "in Sections 2.6-2.7 (Bird",
    "adapt": "adaptation in Section",
    "ccd": "(CCD) described in (Montgomery",
    "ei": "(EI) described by (Morris",
}

def flat(t: str) -> str:
    """Strip invisible chars and collapse whitespace for phrase matching."""
    t = "".join(c for c in t if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", t)

def main() -> int:
    """Locate each probe's page, render it, report misses; 0 if none missing."""
    pdf = pdfium.PdfDocument("main.pdf")
    texts = [flat(pdf[i].get_textpage().get_text_range()) for i in range(len(pdf))]
    missing = []
    for key, phrase in PROBES.items():
        hit = next((i for i, t in enumerate(texts) if phrase in t), None)
        if hit is None:
            missing.append(key)
            print(f"MISS {key}: {phrase!r}")
            continue
        pdf[hit].render(scale=1.5).to_pil().save(f"citefix_{key}_p{hit + 1}.png")
        print(f"{key} pdf page {hit + 1}")
    print("missing:", sorted(missing))
    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())
