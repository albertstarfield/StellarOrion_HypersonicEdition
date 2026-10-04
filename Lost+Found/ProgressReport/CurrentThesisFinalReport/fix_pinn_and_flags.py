#!/usr/bin/env python3
"""Correct the PINN architecture to the one the code builds, and stop CLI flags
from rendering as a single en-dash.

PART 1 - PINN ARCHITECTURE
AXIOM: The engine builds the network from
    dde.nn.FNN([2] + [64] * 3 + [n_output], "tanh", "Glorot normal")
with n_output = 4, declared with the comment
    # Output layer: 4 variables (rho, vx, vy, T)
(stellarorion_program_proc/src/python/pinn_accelerator.py:701 and :652-653)

The thesis stated THREE outputs, (rho, T, u), in two places:
  chapter_03_methodology.tex  tab:pinn_architecture "Output dimension 3 (rho,T,u)"
  chapter_02_literature_review.tex:1280 "3 output features (density, temperature,
                                     and axial velocity)"
The network actually predicts four fields: density, axial velocity, radial
velocity and temperature. This is a substantive modelling statement, because it
is what the PINN is conditioned against and what its loss is assembled from.

PART 1b - THE PARAMETER-COUNT EXPRESSION
The thesis wrote
    2*64 + 2*64^2 + 3*64 + 3  ~= 8,700
The stated total was right but the expression was not: it omits the bias vector
of the input layer (64) and of the two hidden layers (2*64), giving 8515 rather
than the intended count. Expanded correctly, with n_output = 4:
    (2*64 + 64) + 2*(64^2 + 64) + (4*64 + 4)
      =    192    +     8320      +     260     = 8772
Note this also changes the total: the correct figure for four outputs is 8772,
not 8700, which the three-output count happened to reproduce closely enough to
pass unchallenged.

PART 2 - CLI FLAGS RENDERING AS AN EN-DASH
AXIOM: In LaTeX, `--` is a ligature for U+2013 EN DASH in every font that has
the ligature, including the T1-encoded typewriter font that \texttt selects. So
`\texttt{--fnum}` does not print two hyphens; it prints one en-dash followed by
"fnum". Verified in the extracted text of the built PDF, which contains
    "ia \u2013fnum"      (from \texttt{--fnum})
    "ng\n\u2013self-test" (from \texttt{--self-test})
A command-line flag printed as an en-dash cannot be copied and pasted, so every
flag in the thesis is wrong as rendered. The fix is the standard LaTeX idiom
`-{}-`, which suppresses the ligature by inserting an empty group between the
two hyphens. The thesis already uses that idiom in chapter_04_results.tex for
`bin/main -{}-validate-only`, so applying it consistently also removes a real
inconsistency in how the same kind of token is written.

No em-dash is introduced: `-{}-` renders as two separate hyphens.
"""

from __future__ import annotations

import re
from pathlib import Path

THESIS = Path(__file__).resolve().parent

# (file, old, new) - each must match exactly once.
EDITS: list[tuple[str, str, str]] = [
    # ---- Part 1: ch3 architecture table --------------------------------
    (
        "chapter_03_methodology.tex",
        "        Output dimension & 3 $(\\rho, T, u)$ \\\\ \\hline\n"
        "        Total trainable parameters & $2 \\times 64 + 2 \\times 64^2 "
        "+ 3 \\times 64 + 3 \\approx 8{,}700$ \\\\ \\hline",
        "        Output dimension & 4 $(\\rho, v_x, v_y, T)$ \\\\ \\hline\n"
        "        Total trainable parameters & "
        "$(2 \\times 64 + 64) + 2\\,(64^{2} + 64) + (4 \\times 64 + 4) "
        "= 8{,}772$ \\\\ \\hline",
    ),
    # ---- Part 1: ch2 prose --------------------------------------------
    (
        "chapter_02_literature_review.tex",
        "3 hidden layers of 64 neurons each with $\\tanh$ activation, and 3 "
        "output features (density, temperature, and axial velocity)",
        "3 hidden layers of 64 neurons each with $\\tanh$ activation, and 4 "
        "output features (density, axial velocity, radial velocity, and "
        "temperature)",
    ),
]

# ---- Part 2: every \texttt{--flag} becomes \texttt{-{}-flag} ---------------
FLAG_FILES = [
    "chapter_01_introduction.tex",
    "chapter_02_literature_review.tex",
    "chapter_03_methodology.tex",
    "chapter_04_results.tex",
    "chapter_05_conclusion.tex",
    "appendix.tex",
]
# \texttt{--x}  or  \seqsplit{--x}   ->  -{}-
_FLAG_RE = re.compile(r"(\\texttt\{|\\seqsplit\{)(--)")

# A flag token is a leading double hyphen followed by a letter. Guard against
# touching a mathematical minus or an em-dash that is not a flag.
_FLAG_TOKEN = re.compile(r"^--[A-Za-z]")


def fix_flags(text: str) -> tuple[str, int]:
    """Rewrite leading `--flag` tokens inside \\texttt/\\seqsplit to `-{}-flag`."""
    out: list[str] = []
    i = 0
    count = 0
    for m in _FLAG_RE.finditer(text):
        rest = text[m.end():]
        # The leading "--" is ALREADY consumed by _FLAG_RE, so the token
        # pattern must NOT include it again. Matching "--" here was a real bug
        # that made this function silently report zero fixes while two matches
        # existed in the input.
        tok = re.match(r"[A-Za-z][A-Za-z0-9_.-]*", rest)
        if not tok:
            continue
        out.append(text[i:m.start()])
        out.append(m.group(1) + "-{}-" + tok.group(0))
        i = m.end() + len(tok.group(0))
        count += 1
    out.append(text[i:])
    return "".join(out), count


def main() -> int:
    rc = 0
    for name, old, new in EDITS:
        p = THESIS / name
        t = p.read_text(encoding="utf-8")
        n = t.count(old)
        if n != 1:
            print(f"  !! {name}: expected 1 match, found {n}: {old[:60]!r}")
            rc = 1
            continue
        p.write_text(t.replace(old, new, 1), encoding="utf-8")
        print(f"  ok  {name}: {old[:56]!r}")

    total = 0
    for name in FLAG_FILES:
        p = THESIS / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        new_t, n = fix_flags(t)
        if n:
            p.write_text(new_t, encoding="utf-8")
            total += n
            print(f"  ok  {name}: {n} CLI flag token(s) -> -{{}}-")
    print(f"\n{total} CLI flag token(s) fixed; {len(EDITS)} architecture edit(s).")
    if rc:
        print("SOME EDITS FAILED (see !! above).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
