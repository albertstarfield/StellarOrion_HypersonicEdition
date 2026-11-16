#!/usr/bin/env python3
"""Render the pages containing the two split long sentences to PNG.

AXIOMS: Goal revision 3 requires a readability read of rendered pages in
every audit cycle. The overlong-sentence fixes in chapter_01 and
chapter_02 must be seen on the rendered page before they are claimed
verified.

THEORIES: Extract flattened pdfium text (invisible chars dropped,
whitespace collapsed), locate each probe's page, and render that page at
scale 1.5 to lsfix_<key>_p<N>.png. A missing probe is reported and
exits 1 so silent misses cannot pass.

APPLICATIONS: Run from the thesis directory:
    .venv-pdf/bin/python render_lsfix.py

CITATIONS: pypdfium2 PDF rendering; probe strings are taken verbatim
from the post-fix source sentences.
"""
import re

import pypdfium2 as pdfium

PROBES = {
    "knudsen_item": "Knudsen Number Field Mapping: To analyze the spatial distribution",
    "dsmc_local": "DSMC stays justified",
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
        Invisible characters dropped and whitespace collapsed to single
        spaces so probes survive line wrapping.
    """
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", text)


def main() -> int:
    """Locate and render every probe page.

    Returns
    =======
    int
        0 when all probes found, 1 otherwise.
    """
    pdf = pdfium.PdfDocument("main.pdf")
    found = {}
    for i in range(len(pdf)):
        text = flat(pdf[i].get_textpage().get_text_range())
        for key, probe in PROBES.items():
            if key not in found and probe in text:
                found[key] = i
    missing = set(PROBES) - set(found)
    for key, idx in sorted(found.items()):
        out = f"lsfix_{key}_p{idx + 1}.png"
        pdf[idx].render(scale=1.5).to_pil().save(out)
        print(f"{key} pdf page {idx + 1} -> {out}")
    if missing:
        print(f"missing probes: {sorted(missing)}")
        return 1
    print("missing: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
