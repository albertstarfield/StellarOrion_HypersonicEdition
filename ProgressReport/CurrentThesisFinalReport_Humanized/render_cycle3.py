#!/usr/bin/env python3
"""Render the pages touched by the cycle 3 audit fixes, for a visual read.

PURPOSE
    Write one PNG per page so a vision auditor can read what the printed
    PDF actually shows after the following fixes: the math mode balance
    repair in the chapter 2 both paradigms paragraph, the table row
    padding on Table 3.8, and the unbreakable LHS citation in chapter 4.

PARAMETERS
    None. The page list below is fixed and records why each page matters.

RETURNS
    0 when every requested page was rendered and at least one page existed,
    1 when the document has fewer pages than the highest requested index.

RAISES
    RuntimeError if the PDF cannot be opened or a page renders to nothing.

CITATIONS
    pypdfium2 v4.30.0, PDFium rendering, Apache-2.0
    https://pypi.org/project/pypdfium2/
    Pillow 12.3.0, image writing, MIT-CMU
    https://pypi.org/project/pillow/

AXIOMS
    A1. A PDF page number here is the zero based index into the document,
        so the rendered file name carries page plus one to match the folio
        printed in the margin.
    A2. Rendering at 2.0 pixels per point reproduces the 12 pt body text at
        24 pixels, which is the size at which word spacing defects were
        previously measured.

THEORIES
    T1. Reading the rendered pixels, not the text layer, is the only way to
        confirm that inter-word spacing, rule clearance and page-break
        placement actually changed, because those properties do not survive
        text extraction.
    T2. Rendering the page before AND after the break for a paragraph that
        was split is necessary, since the defect appeared on the page that
        received the continuation line.

APPLICATIONS
    A1. Cycle 3 readability audit of the math mode repair, the table row
        padding, and the LHS citation.
    A2. Any future page whose prose an extraction tool has questioned.
"""
from pathlib import Path

import pypdfium2 as pdfium

THESIS = Path(__file__).resolve().parent
PDF = THESIS / "main.pdf"
PX_PER_PT = 2.0

# Zero based page indices, each with the fix it is meant to show.
PAGES = {
    64: "chapter 2 both paradigms paragraph, math mode repaired",
    65: "chapter 2 continuation line, must start a fresh sentence",
    90: "chapter 3 scope paragraph, output tuple wording",
    91: "Table 3.8 with the raised array stretch",
    124: "chapter 4 LHS sentence, noun and citation together",
    125: "page after the LHS sentence, must not open with a word tail",
}


def render(document, index, out_path):
    """Render one zero based page at PX_PER_PT and write it as a PNG.

    Parameters:
        document: an open pypdfium2 document.
        index: zero based page index.
        out_path: destination PNG path.

    Returns:
        The (width, height) pixel pair written.

    Raises:
        RuntimeError if the rendered bitmap is empty.
    """
    bitmap = document[index].render(scale=PX_PER_PT)
    image = bitmap.to_pil()
    if image.width == 0 or image.height == 0:
        raise RuntimeError(f"page {index + 1} rendered empty")
    image.save(out_path)
    return image.size


def main():
    """Render every page in PAGES and report the results.

    Returns:
        0 when all pages rendered, 1 when a requested index is past the end.

    Raises:
        RuntimeError if the PDF is missing or unreadable.
    """
    if not PDF.is_file():
        raise RuntimeError(f"missing {PDF}")
    document = pdfium.PdfDocument(str(PDF))
    written = []
    for index, why in PAGES.items():
        if index >= len(document):
            print(f"MISS page {index + 1}: document has {len(document)} pages")
            continue
        out = THESIS / f"read_cycle3_p{index + 1}.png"
        size = render(document, index, out)
        written.append(out.name)
        print(f"wrote {out.name} {size[0]}x{size[1]}px for {why}")
    print(f"pages: {len(document)} written: {len(written)} missing: "
          f"{len(PAGES) - len(written)}")
    return 0 if len(written) == len(PAGES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
