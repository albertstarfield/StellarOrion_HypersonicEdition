#!/usr/bin/env python3
"""Render the still-unviewed structural pages of main.pdf for a readability read.

Renders the table-of-contents opener, the references opener, and the appendix
opener at scale 1.5 into sweep2_<name>_p<N>.png so the image-specialist can
audit layout and readability (goal revision 3) without touching chapter sources.

Usage: .venv-pdf/bin/python sweep2_render.py   (workdir = thesis dir)
Exit code 0 when all three pages render, 1 when a marker is missing.
"""
import re
import sys

import pypdfium2 as pdfium

MARKERS = {
    "toc": "TABLE OF CONTENTS",
    "refs": "REFERENCES",
    "appx": "APPENDIX",
}


def main() -> int:
    pdf = pdfium.PdfDocument("main.pdf")
    hits = {}
    for i in range(len(pdf)):
        text = re.sub(r"[\r\n]", " ", pdf[i].get_textpage().get_text_range())
        for key, marker in MARKERS.items():
            if key not in hits and marker in text and (
                key == "toc"
                or ("LIST OF" not in text and ". . ." not in text)
            ):
                hits[key] = i
    ok = True
    for key, idx in sorted(hits.items()):
        out = f"sweep2_{key}_p{idx + 1}.png"
        pdf[idx].render(scale=1.5).to_pil().save(out)
        print(f"{key} pdf page {idx + 1} -> {out}")
    for key in MARKERS:
        if key not in hits:
            print(f"MISS {key}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
