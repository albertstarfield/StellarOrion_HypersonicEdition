#!/usr/bin/env python3
"""Locate every PDF page containing the DSMC split sentence fragments.

AXIOMS: The PDF is the render ground truth; if a probe is not where the
caller expects, the search must report where (or whether) it exists at
all rather than guessing.

THEORIES: Flatten every page once, then report page indices for a set of
probe substrings taken verbatim from the expected split sentence and
from the surrounding source paragraph.

APPLICATIONS: Run from the thesis directory:
    .venv-pdf/bin/python find_dsmc_sentence.py

CITATIONS: pypdfium2 text extraction - https://pypdfium2.readthedocs.io/
"""
import re

import pypdfium2 as pdfium

PROBES = [
    "while the freestream stays continuum",
    "The SPARTA Boltzmann solver therefore remains correct",
    "layer that dominates the heat load",
    "slip-to-transition band",
    "when velocity and temperature slip corrections",
    "SPARTA Boltzmann solver",
    "freestream stays continuum",
]


def flat(text):
    """Collapse page text to a single-line probe-safe string.

    Parameters
    ----------
    text : str
        Raw pdfium page text.

    Returns
    -------
    str
        Whitespace-collapsed printable text.
    """
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", text)


def main():
    """Print, per probe, every 1-based PDF page where it occurs.

    Returns
    -------
    int
        Always 0.
    """
    pdf = pdfium.PdfDocument("main.pdf")
    pages = [flat(pdf[i].get_textpage().get_text_range()) for i in range(len(pdf))]
    for probe in PROBES:
        hits = [i + 1 for i, t in enumerate(pages) if probe in t]
        print(f"{hits if hits else 'NOT FOUND'}  <- {probe!r}")
    # Dump full text of any page that contains the second sentence.
    for i, t in enumerate(pages):
        if "SPARTA Boltzmann solver therefore remains" in t:
            pos = t.find("DSMC stays justified")
            start = pos if pos >= 0 else max(0, t.find("SPARTA Boltzmann") - 400)
            print(f"\n--- page {i + 1} context ---\n{t[start:start + 900]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
