"""Render selected pages of a PDF to PNG images.

Purpose:
    Produce page images of the ITB standard-layout example thesis so the
    visual layout of its front-matter sections can be inspected.

Parameters (argv):
    pdf_path   : input PDF path
    out_prefix : prefix for the written PNG files (``<prefix>_pNNN.png``)
    first      : first page, 1-based inclusive
    last       : optional last page, 1-based inclusive (defaults to first)

Returns:
    Prints the path of every PNG written.

Exceptions:
    SystemExit(2) on missing arguments, SystemExit(1) when the PDF is absent
    or pypdfium2 cannot be imported.
"""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 4:
        print("usage: render_ref.py <pdf> <out_prefix> <first> [last]")
        raise SystemExit(2)

    try:
        import pypdfium2 as pdfium
    except Exception as exc:  # pragma: no cover - environment guard
        print(f"pypdfium2 import failed: {exc}")
        raise SystemExit(1)

    pdf_path = Path(sys.argv[1])
    prefix = sys.argv[2]
    first = int(sys.argv[3])
    last = int(sys.argv[4]) if len(sys.argv) > 4 else first

    if not pdf_path.exists():
        print(f"missing pdf: {pdf_path}")
        raise SystemExit(1)

    doc = pdfium.PdfDocument(str(pdf_path))
    total = len(doc)
    try:
        for page_no in range(first, last + 1):
            if page_no < 1 or page_no > total:
                print(f"skip page {page_no} (pdf has {total} pages)")
                continue
            page = doc[page_no - 1]
            image = page.render(scale=2.0).to_pil()
            out_path = f"{prefix}_p{page_no:03d}.png"
            image.save(out_path)
            print(out_path)
    finally:
        doc.close()


if __name__ == "__main__":
    main()
