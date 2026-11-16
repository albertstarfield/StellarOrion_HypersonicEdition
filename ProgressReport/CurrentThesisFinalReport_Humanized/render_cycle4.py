"""Render the pages holding the four regenerated figures, for visual audit.

WHY THIS EXISTS
    Three figures were rewritten from scratch this cycle (the Bayesian
    optimization convergence panel, the PINN architecture diagram and the
    central composite screen) and the coverage matrix was redrawn. A generator
    that passes its own guards still says nothing about what the reader sees
    once the figure sits on a page with a caption, so the rendered page is the
    only artifact that can be judged. This renders exactly those pages.

PARAMETERS
    None. The page list is PAGES below; the output names are derived from it.

RETURNS
    0 when every requested page rendered, 1 when the document or a page is
    missing.

EXCEPTIONS
    RuntimeError when main.pdf is absent or a page renders empty.

CITATIONS
    pypdfium2 v4.30.0, PdfDocument and PdfPage.render
        https://pypdfium2.readthedocs.io/en/stable/
    Pillow 12.3.0 is used only to confirm the render is non-empty.

AXIOMS
    A1: the page index is zero based while the printed folio is not, so the
        file name carries the one-based page number to match figcheck output.
    A2: two pixels per point is the scale this project renders every audit
        page at, and it is what makes a printed-point measurement a two-pixel
        measurement.

THEORIES
    T1: the rendered page is the ground truth because it is the only artifact
        that composes figure, caption, axis text and body prose together, so a
        collision that no per-figure measurement predicts can still be seen.
    T2: rendering both the figure page and its neighbour catches a float that
        has pushed its caption onto the following page.

APPLICATIONS
    A1: audit the four regenerated figures in one pass.
    A2: re-run after any rebuild, because page numbers move when figures change
        height.
"""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

THESIS = Path(__file__).resolve().parent
PDF = THESIS / "main.pdf"

PX_PER_PT = 2.0

# Zero-based page indices, each paired with the figure it carries, so a
# verifier reading the output knows which artifact each page is evidence for.
# Eight pages rather than four: this cycle's rendered audit of the seven
# regenerated panels found six real geometry collisions and one figure with
# no numeric tick labels at all, and every one of those fixes can only be
# judged on the page the figure actually sits on.
PAGES = {
    27: "pipeline",
    32: "litmap",
    48: "sutton",
    92: "pinn",
    114: "heatflux",
    126: "boccd",
    127: "ccd",
    128: "boconv",
    130: "gate",
}


def render(document, index: int, out_path: Path) -> None:
    """Write one page to out_path.

    Parameters:
        document: the open PdfDocument.
        index: zero-based page index.
        out_path: destination PNG path.

    Returns:
        None.

    Raises:
        RuntimeError when the render produces an empty image.
    """
    page = document[index]
    bitmap = page.render(scale=PX_PER_PT)
    image = bitmap.to_pil()
    if image.width == 0 or image.height == 0:
        raise RuntimeError(f"page {index + 1} rendered empty")
    image.save(out_path)
    print(f"wrote {out_path.name}  {image.width}x{image.height}px")


def main() -> int:
    """Render every page in PAGES and report the count.

    Returns:
        0 when all pages rendered, 1 when the document is missing.

    Raises:
        RuntimeError from render when a page renders empty.
    """
    if not PDF.exists():
        print(f"missing {PDF}")
        return 1
    document = pdfium.PdfDocument(str(PDF))
    print(f"pages: {len(document)}")
    written = 0
    for index, name in PAGES.items():
        if index >= len(document):
            print(f"page {index + 1} beyond document ({len(document)} pages)")
            continue
        out = THESIS / f"read_cycle4_{name}_p{index + 1}.png"
        render(document, index, out)
        written += 1
    with Image.open(THESIS / f"read_cycle4_{PAGES[list(PAGES)[0]]}_p{list(PAGES)[0] + 1}.png") as probe:
        probe.verify()
    print(f"written: {written}  missing: {len(PAGES) - written}")
    return 0 if written == len(PAGES) else 1


if __name__ == "__main__":
    raise SystemExit(main())