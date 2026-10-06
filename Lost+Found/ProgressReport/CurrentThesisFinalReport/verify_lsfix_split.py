#!/usr/bin/env python3
"""Verify the two long-sentence splits in the rendered PDF pages.

AXIOMS: The rendered PDF page, not the .tex source, is ground truth for
readability claims. A split sentence that straddles a page break must be
read on BOTH pages before it can be called verified.

THEORIES: Extract flattened pdfium text for the probe pages plus the page
after each probe (the continuation page), print the exact rendered
sentences around each split, render the continuation page at scale 1.5,
and flag any "--" or em/en dash in the visible text.

APPLICATIONS: Run from the thesis directory:
    .venv-pdf/bin/python verify_lsfix_split.py
Exit 0 always; the report is the deliverable.

CITATIONS: pypdfium2 PDF text extraction and rendering - https://pypdfium2.readthedocs.io/
"""
import re

import pypdfium2 as pdfium

# Probe anchors (verbatim post-fix source text) -> pages of interest.
SPLITS = {
    "knudsen_item": {
        "anchor": "Knudsen Number Field Mapping: To analyze the spatial distribution",
        "expect": "bands that bound the shock-layer gradient. This characterizes the flow physics that governs aerothermal loads.",
    },
    "dsmc_local": {
        "anchor": "DSMC stays justified",
        "expect": "while the freestream stays continuum. The SPARTA Boltzmann solver therefore remains correct for the layer that dominates the heat load (Bird, 1994; Plimpton & Gallis, 2014).",
    },
}


def flat(text):
    """Collapse page text so probes survive line wrapping.

    Parameters
    ----------
    text : str
        Raw pdfium page text.

    Returns
    -------
    str
        Printable chars kept, whitespace collapsed to single spaces.
    """
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", text)


def dashes(text):
    """Return every dash-like token found in text.

    Parameters
    ----------
    text : str
        Flattened page text.

    Returns
    -------
    list of str
        Matched "--", em dash, or en dash tokens (may be empty).
    """
    return re.findall(r"--|[\u2013\u2014]", text)


def main():
    """Locate splits, print exact sentences, render continuation pages.

    Returns
    -------
    int
        Always 0; findings are printed for the caller to read.
    """
    pdf = pdfium.PdfDocument("main.pdf")
    pages = [flat(pdf[i].get_textpage().get_text_range()) for i in range(len(pdf))]
    for key, spec in SPLITS.items():
        idx = next((i for i, t in enumerate(pages) if spec["anchor"] in t), None)
        print(f"== {key}")
        if idx is None:
            print("   ANCHOR NOT FOUND")
            continue
        print(f"   anchor page (1-based pdf): {idx + 1}")
        # Show the anchor sentence region on this page and the continuation.
        for p in (idx, idx + 1):
            if p >= len(pages):
                continue
            text = pages[p]
            pos = text.find(spec["anchor"])
            # Print from anchor to end of page, or last 400 chars if the
            # anchor is absent (continuation page).
            snippet = text[pos:pos + 700] if pos >= 0 else text[-700:]
            print(f"   --- pdf page {p + 1} text ---")
            print("   " + snippet)
            d = dashes(text)
            print(f"   dashes on page {p + 1}: {d if d else 'none'}")
            out = f"lscont_{key}_p{p + 1}.png"
            pdf[p].render(scale=1.5).to_pil().save(out)
            print(f"   rendered -> {out}")
        # Verify the expected second sentence exists flattened across pages.
        window = " ".join(pages[idx:idx + 2])
        present = spec["expect"] in window
        print(f"   expected split text present across pages {idx + 1}-{idx + 2}: {present}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
