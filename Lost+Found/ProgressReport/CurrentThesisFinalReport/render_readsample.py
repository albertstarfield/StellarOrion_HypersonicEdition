#!/usr/bin/env python3
"""Render a sample of the most text-dense PDF pages for the cycle readability read.

AXIOMS: goal rev 3 requires reading rendered PDF pages for readability problems
every audit cycle. Pages already covered by pending figure checks (28, 48, 107,
114, 121, 126, 127, 128, 130) must NOT be re-checked, so they are excluded from
the candidate set before ranking.

THEORIES: pdfium text extraction with invisible-character stripping and
whitespace collapse gives a reliable per-page character count. Ranking pages by
text length and sampling evenly across that ranking (first, quartiles, last)
yields a representative prose sample without overlapping pending work.

APPLICATIONS: run from the thesis directory with the project venv:
    .venv-pdf/bin/python render_readsample.py
Writes read_p<N>.png (temp, never commit) and prints each page's first 80
characters. Exit 1 if any render fails.

CITATIONS: [Citation: pypdfium2 PDF rendering - https://pypi.org/project/pypdfium2/]
"""
import re
import sys

import pypdfium2 as pdfium

FORBIDDEN = {28, 48, 107, 114, 121, 126, 127, 128, 130}
SAMPLE = 5


def flat(text):
    """Return text with non-printables dropped and whitespace collapsed.

    Parameters
    ----------
    text : str
        Raw pdfium page text.

    Returns
    -------
    str
        Printable-only text with runs of whitespace collapsed to one space.

    Exceptions
    ----------
    None; pure string transformation.
    """
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", text)


def main():
    """Rank non-forbidden pages by text length and render SAMPLE evenly spaced picks.

    Returns
    -------
    int
        0 when every selected page rendered, 1 otherwise.
    """
    pdf = pdfium.PdfDocument("main.pdf")
    scored = []
    for i in range(len(pdf)):
        page_no = i + 1
        if page_no in FORBIDDEN:
            continue
        text = flat(pdf[i].get_textpage().get_text_range())
        scored.append((len(text), page_no, text))
    scored.sort()
    dense = [s for s in scored if s[0] > 1500]
    if len(dense) < SAMPLE:
        dense = scored
    step = max(1, len(dense) // SAMPLE)
    picks = [dense[min(j * step, len(dense) - 1)] for j in range(SAMPLE)]
    failed = []
    for _, page_no, text in picks:
        out = f"read_p{page_no}.png"
        try:
            pdf[page_no - 1].render(scale=1.5).to_pil().save(out)
        except Exception as exc:
            print(f"FAIL p{page_no}: {exc}")
            failed.append(page_no)
            continue
        print(f"p{page_no} ({text[:80]}...) -> {out}")
    print("failed:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
