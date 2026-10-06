#!/usr/bin/env python3
"""Render the pages carrying the readability-batch fixes to PNG for review.

AXIOMS:
  A1. Every source edit must be verified in the rendered PDF (goal rev 3).
  A2. pdfium text needs invisible-char stripping and whitespace collapse
      for reliable phrase probes (line breaks otherwise split matches).

THEORIES:
  T1. Probing the rebuilt main.pdf for each fix's distinctive phrase locates
      its page; rendering that page at scale 1.5 gives an inspectable PNG.

APPLICATIONS:
  Run: .venv-pdf/bin/python render_readfix.py   (from the thesis directory)
  Writes readfix_<key>_p<N>.png (temp, gitignored, NEVER committed);
  exits 1 if any probe is missing so silent misses cannot pass.

CITATIONS:
  [Citation: pypdfium2 - https://pypi.org/project/pypdfium2/]
"""
import re
import sys

import pypdfium2 as pdfium

PROBES = {
    "mdao": "optimization (MDAO) baseline",
    "window": "within the sampling window",
    "grid": "at lower cost than the ultra-fine",
    "ccd": "That 15-point CCD record is separate",
    "tourney": "In tournament selection of size",
    "dagger": "marks that entry",
    "doe": "Design of Experiments (DoE)",
    "sg": "(SG) correlation evaluated at",
}


def flat(text: str) -> str:
    """Flatten extracted page text for whitespace-tolerant probing.

    Parameters
    ==========
    text : str
        Raw pdfium page text.

    Returns
    =======
    str
        Invisible characters dropped, whitespace collapsed to single spaces.
    """
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", text)


def main() -> int:
    """Locate each probe's page, render it, report misses; 1 if any missing."""
    pdf = pdfium.PdfDocument("main.pdf")
    texts = [flat(pdf[i].get_textpage().get_text_range()) for i in range(len(pdf))]
    missing = []
    for key, phrase in PROBES.items():
        hit = next((i for i, t in enumerate(texts) if phrase in t), None)
        if hit is None:
            missing.append(key)
            print(f"MISS {key}: {phrase!r}")
            continue
        out = f"readfix_{key}_p{hit + 1}.png"
        pdf[hit].render(scale=1.5).to_pil().save(out)
        print(f"{key} pdf page {hit + 1} -> {out}")
    print("missing:", sorted(missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
