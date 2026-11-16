"""Render the specific pages touched by the current audit cycle.

WHY THIS SCRIPT EXISTS
======================
render_readfix.py locates pages by searching for a probe phrase. This cycle
already located every page of interest, so re-running phrase probes would
only risk matching a different sentence after a reflow. The page numbers are
therefore recorded explicitly here, together with the edit each page is
expected to show, so a reviewer can see what the render is for.

PAGES, zero based, with the edit under audit on each:
    59  Figure 4.xx caption region for the redrawn DSMC flowchart
    60  the redrawn DSMC flowchart itself
    63  the reworded "both paradigms" paragraph, first half
    64  its continuation, where the value and the equation reference sit
    89  the PINN "Scope of the implemented residual" paragraph
    90  Table 3.8, the target of that paragraph's cross reference
    123 the Latin Hypercube paragraph whose citation was split before

CITATIONS
=========
- pypdfium2, https://github.com/pypdfium2-team/pypdfium2
- Pillow 12.3.0, https://pillow.readthedocs.io/en/stable/
"""

from __future__ import annotations

import sys

import pypdfium2 as pdfium

PAGES = (59, 60, 63, 64, 89, 90, 123)
SCALE = 2.0


def main() -> int:
    """Render every page in PAGES to read_cycle2_pNN.png; 1 if any is missing.

    Returns
    =======
    int
        Zero when all pages rendered, one otherwise.
    """
    pdf = pdfium.PdfDocument("main.pdf")
    missing = []
    for index in PAGES:
        if index >= len(pdf):
            missing.append(index)
            print(f"MISS page {index + 1}: beyond the document")
            continue
        out = f"read_cycle2_p{index + 1}.png"
        pdf[index].render(scale=SCALE).to_pil().save(out)
        print(f"page {index + 1} -> {out}")
    print("missing:", missing)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())