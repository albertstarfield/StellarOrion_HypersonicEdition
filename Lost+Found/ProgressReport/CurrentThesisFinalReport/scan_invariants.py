# -*- coding: utf-8 -*-
"""Scan main.pdf for global text invariants and verify this batch's fixes.

PURPOSE: Post-edit PDF text verification for the title/abstract/notation batch.
PARAMETERS: none (reads main.pdf in the current working directory).
RETURN: prints invariant counts and per-probe OK/MISS lines; exit 0 always.
EXCEPTIONS: pypdfium2 may raise on a corrupt/missing main.pdf (surfaced, not swallowed).
AXIOMS: goal forbids em-dash and gnatprove/SPARK in rendered text; this batch's
edits must appear verbatim (modulo pdfium line-break hyphenation) in the PDF.
THEORIES: if all invariants are 0 and all probes OK, the batch renders correctly.
APPLICATIONS: run after every rebuild that touches title/abstract/notation text.
CITATIONS: pypdfium2 (BSD-3-Clause) - https://pypdfium2.readthedocs.io/
"""
import re

import pypdfium2 as pdfium

pdf = pdfium.PdfDocument('main.pdf')
text = ''.join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
text = re.sub(r'[\uFFFC-\uFFFF\u200B\uFEFF]', '', text)
print('pages:', len(pdf))
low = text.lower()
print(
    'U+2014:', text.count('\u2014'),
    '| gnatprove:', low.count('gnatprove'),
    '| spark:', low.count('spark'),
    '| formal verification:', low.count('formal verification'),
    '| Retrieved from:', text.count('Retrieved from'),
    '| [?]:', text.count('[?]'),
)
PROBES = [
    r'NIM\. 23624003',
    r'NIM\.23624003',
    r'Gaussian Process \(GP\) with a Mat',
    r'Knudsen number 0\.01 < Kn',
    r'reference multidisciplinary design analysis and optimization \(MDAO\) model',
    r'Under that condition',
    r'bands are not reached',
    r'fall below the flight values',
    r'gives the best balance',
]
for pat in PROBES:
    print('OK  ' if re.search(pat, text) else 'MISS', pat)
pdf[0].render(scale=1.6).to_pil().save('fix_t_p1.png')
pdf[2].render(scale=1.6).to_pil().save('fix_t_p3.png')
print('rendered fix_t_p1.png / fix_t_p3.png')
