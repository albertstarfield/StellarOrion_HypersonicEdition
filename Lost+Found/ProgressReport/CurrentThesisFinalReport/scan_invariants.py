# -*- coding: utf-8 -*-
"""Scan main.pdf for global text invariants and verify this batch's fixes.

PURPOSE: Post-edit PDF text verification (invariants + per-batch phrase probes).
PARAMETERS: none (reads main.pdf in the current working directory).
RETURN: prints invariant counts and per-probe OK/MISS lines; exit 0 always.
EXCEPTIONS: pypdfium2 may raise on a corrupt/missing main.pdf (surfaced, not swallowed).
AXIOMS: goal forbids em-dash and gnatprove/SPARK in rendered text; batch edits
must appear verbatim (modulo pdfium line wrapping) in the PDF.
THEORIES: if all invariants are 0 and the positive probes print OK, the batch
renders correctly. The NIM.23624003 probe is NEGATIVE (old broken form must be
absent), so MISS is the expected result for it.
APPLICATIONS: run after every rebuild that touches probed text.
CITATIONS: pypdfium2 (BSD-3-Clause) - https://pypdfium2.readthedocs.io/
"""
import re

import pypdfium2 as pdfium

pdf = pdfium.PdfDocument('main.pdf')
text = ''.join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
# Drop format/invisible characters pdfium injects (isprintable() is False for
# them), keep line breaks for now, then collapse whitespace so phrase probes
# survive line wrapping in the rendered text stream.
text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
text = re.sub(r'\s+', ' ', text)
print('pages:', len(pdf))
low = text.lower()
print(
    'emdash:', text.count(chr(0x2014)),
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
    r'Knudsen number range 0\.01 < Kn',
    r'design analysis and optimization \(MDAO\) model',
    r'Under that condition',
    r'bands are not reached',
    r'deviate from the flight values',
    r'trajectory-integrated peak',
]
for pat in PROBES:
    print('OK  ' if re.search(pat, text) else 'MISS', pat)
pdf[0].render(scale=1.6).to_pil().save('fix_t_p1.png')
pdf[2].render(scale=1.6).to_pil().save('fix_t_p3.png')
print('rendered fix_t_p1.png / fix_t_p3.png')
