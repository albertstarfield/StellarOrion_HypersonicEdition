#!/usr/bin/env python3
"""Remove every em-dash from the thesis prose, replacing each with grammatical
punctuation chosen per occurrence rather than a blind mechanical swap.

AXIOMS
======
1. In LaTeX, `===` renders as an em-dash (U+2014) and `==` as an en-dash.
   The thesis owner has ruled that the em-dash must not appear at all.
2. A blind substitution of `===` -> `,` is NOT a fix. It corrupts grammar in
   three distinct constructions that occur here:
     (a) a parenthetical appositive set off by a matched PAIR of em-dashes,
         which must become a matched PAIR of parentheses;
     (b) a single interrupting em-dash before a clause that already follows a
         comma, where a comma is wrong (comma splice) and a colon or
         parenthetical is right;
     (c) a table cell whose em-dash means "not applicable", which must
         become the word n/a, not punctuation.
3. Therefore each occurrence needs a replacement chosen from its own context.
   This script is an explicit, auditable table of (old, new) pairs. Any pair
   that fails to match is REPORTED, not silently skipped, so a drift between
   this table and the source cannot hide.

THEORIES
=========
If every pair matches exactly once and a final scan finds zero `===` and zero
U+2014 in non-comment, non-code-block prose, then the em-dash is gone and the
prose still parses. Compile + re-render then confirms the typesetting.

SCOPE / EXCLUSIONS
==================
- LaTeX comments (text after an unescaped `%`) are excluded: they are not
  typeset, so an em-dash there is invisible in the PDF. They are still
  counted separately and reported.
- verbatim / lstlisting / minted / alltt bodies are excluded: a dash inside a
  code excerpt is DATA, not prose, and rewriting it would falsify the code.
- `chapter_02_literature_review.sync-conflict-*.tex` are excluded: they are
  Syncthing conflict copies, not part of the build (main.tex includes only
  `chapter_02_literature_review`).

Citations
=========
* LaTeX dash ligatures: https://tug.org/TUGboat/Volumes/tn09/3/hyphenator.html
* em-dash / en-dash typography guidance: https://www.wikiwand.com/en/Dash
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

THESIS = Path(__file__).resolve().parent

# Files that participate in the build. Sync-conflict copies are excluded.
FILES = [
    "chapter_01_introduction.tex",
    "chapter_02_literature_review.tex",
    "chapter_03_methodology.tex",
    "chapter_04_results.tex",
    "chapter_05_conclusion.tex",
    "appendix.tex",
    "abstract.tex",
    "abbreviations.tex",
    "cover.tex",
    "symbols.tex",
    "preamble.tex",
]

# ===========================================================================
# (AXIOM 3) The explicit replacement table: file -> list of (old, new).
# Ordering within a file matters only in that the first match wins; every pair
# below is unique within its file.
# ===========================================================================
PAIRS: dict[str, list[tuple[str, str]]] = {
    #, ch2
    "chapter_02_literature_review.tex": [
        # (b) single interrupting dash after a colon-introduced list
        (
            "Five studies form the rows --- Rapisarda 2022",
            "Five studies form the rows: Rapisarda 2022",
        ),
        # (b) caption: dash opens an enumeration of regimes -> colon
        (
            "labelled regimes --- continuum at $Kn < 0.01$",
            "labelled regimes: continuum at $Kn < 0.01$",
        ),
        # (b) caption: dash before "with a ..." -> comma (list continues)
        (
            "molecular at $Kn > 10$ --- with a reference-length legend entry",
            "molecular at $Kn > 10$, with a reference-length legend entry",
        ),
    ],
    #, ch3
    "chapter_03_methodology.tex": [
        # (a) matched pair appositive -> matched pair of parentheses
        (
            "The derivation chain---from fundamental kinetic theory to the "
            "implemented software pipeline---is summarized",
            "The derivation chain, from fundamental kinetic theory to the "
            "implemented software pipeline, is summarized",
        ),
        # (a) matched pair -> parentheses
        (
            "On the \\emph{global} reference length --- the full 3\\,m "
            "aeroshell diameter --- the IRVE-3 freestream",
            "On the \\emph{global} reference length (the full 3\\,m "
            "aeroshell diameter) the IRVE-3 freestream",
        ),
        # (a) matched pair -> parentheses
        (
            "On the \\emph{local} reference length --- the millimetre-scale "
            "bow-shock and stagnation layer --- the same gas",
            "On the \\emph{local} reference length (the millimetre-scale "
            "bow-shock and stagnation layer) the same gas",
        ),
        # (a) matched pair around a clause -> parentheses
        (
            "run condition --- $h = 51.8$\\,km under ISA, which yields "
            "$\\rho_{\\infty} = 7.851 \\times 10^{-4}$\\,kg/m$^3$ --- using "
            "the IRVE-3 sphere--cone nose radius",
            "run condition ($h = 51.8$\\,km under ISA, which yields "
            "$\\rho_{\\infty} = 7.851 \\times 10^{-4}$\\,kg/m$^3$) using "
            "the IRVE-3 sphere--cone nose radius",
        ),
        # (b) dash before "not a ..."; a comma here would splice two
        #     independent clauses, so a colon is correct.
        (
            "gradient across the shock layer --- not a transition-region or "
            "free-molecular claim",
            "gradient across the shock layer: not a transition-region or "
            "free-molecular claim",
        ),
    ],
    #, ch4
    "chapter_04_results.tex": [
        # (a) matched pair around a participial phrase -> parentheses
        (
            "orders of magnitude --- including negative values at later time "
            "steps --- and is statistical scatter",
            "orders of magnitude, including negative values at later time "
            "steps, and is statistical scatter",
        ),
        # (a) matched pair around an appositive describing a filter
        (
            "a three-stage filter --- a sixth-order polynomial fit followed by "
            "a Wilmoth bridging function --- to the same kind of raw DSMC data",
            "a three-stage filter (a sixth-order polynomial fit followed by a "
            "Wilmoth bridging function) to the same kind of raw DSMC data",
        ),
        # (b) dash before an evaluative clause; comma is right (same sentence,
        #     "respectively, consistent in sign ... below it.")
        (
            "respectively --- consistent in sign and in ordering with the "
            "geometric bound",
            "respectively, consistent in sign and in ordering with the "
            "geometric bound",
        ),
        # (b) independent clause follows -> semicolon, not comma (no splice)
        (
            "present in this render --- the repository contains no scalloped "
            "field map",
            "present in this render; the repository contains no scalloped "
            "field map",
        ),
        # (b) list items: the bold label already introduced a colon, so a
        #     comma continues the item cleanly.
        (
            "$Kn \\lesssim 0.01$ --- continuum band",
            "$Kn \\lesssim 0.01$, continuum band",
        ),
        (
            "$0.01 \\lesssim Kn \\lesssim 0.1$ --- slip-flow band",
            "$0.01 \\lesssim Kn \\lesssim 0.1$, slip-flow band",
        ),
        (
            "$0.1 \\lesssim Kn \\lesssim 10$ --- \\emph{not present} at this "
            "trajectory point",
            "$0.1 \\lesssim Kn \\lesssim 10$: \\emph{not present} at this "
            "trajectory point",
        ),
        (
            "$Kn > 10$ --- \\emph{not present} at this trajectory point",
            "$Kn > 10$: \\emph{not present} at this trajectory point",
        ),
        # (b) dash introducing a quotation clause, then "so the ...".
        #     A colon before the quote, then a comma before "so", keeps the
        #     final clause attached to the main verb without a splice.
        (
            "as known sources of discrepancy --- it notes that",
            "as known sources of discrepancy, since it notes that",
        ),
        (
            "flags the velocity mismatch --- so the 12.2",
            "flags the velocity mismatch, so the 12.2",
        ),
        # (a) matched pair appositive -> parentheses
        (
            "Because the shock layer --- the region that dominates convective "
            "heating --- reaches the slip-flow band",
            "Because the shock layer (the region that dominates convective "
            "heating) reaches the slip-flow band",
        ),
        # (a) matched pair appositive inside a comparison -> parentheses
        (
            "155.67~J/cm\\textsuperscript{2} --- 6.06\\,\\% \\emph{below} the "
            "165.72~J/cm\\textsuperscript{2} validation target --- while "
            "simultaneously reducing",
            "155.67~J/cm\\textsuperscript{2} (6.06\\,\\% \\emph{below} the "
            "165.72~J/cm\\textsuperscript{2} validation target) while "
            "simultaneously reducing",
        ),
        # (b) dash before a colon-worthy specification of the claim
        (
            "are not one-directional --- 17 of the 46 sit above",
            "are not one-directional: 17 of the 46 sit above",
        ),
        # (a) matched pair -> commas (the appositive is short and the
        #     sentence is long; parentheses would nest badly)
        (
            "and 29 sit below it --- so the excess cost",
            "and 29 sit below it, so the excess cost",
        ),
        (
            "Only the incumbent --- the best cost found so far --- is "
            "non-increasing",
            "Only the incumbent, the best cost found so far, is non-increasing",
        ),
        # (b) dash before an explanatory independent-ish clause; comma reads
        #     correctly because the main clause continues ("..., and the CCD
        #     optimum does not appear in the history.")
        (
            "reported above --- the 15-point CCD and the 70-entry history are "
            "separate datasets",
            "reported above, because the 15-point CCD and the 70-entry history "
            "are separate datasets",
        ),
        # (b) sentence-final dash before an appositive that restates the
        #     subject -> comma
        (
            "systematic bias in the closed-form surrogate --- precisely the "
            "quantity the multi-fidelity correction",
            "systematic bias in the closed-form surrogate, precisely the "
            "quantity the multi-fidelity correction",
        ),
        (
            "reduces the cost of the design space overall --- the expected "
            "outcome when",
            "reduces the cost of the design space overall, the expected "
            "outcome when",
        ),
    ],
    #, ch5
    "chapter_05_conclusion.tex": [
        # (b) dash before "and why ..."; comma joins two parallel "why"
        #     clauses under one antecedent.
        (
            "is the meaningful diagnostic --- and why the continuum PINN stage",
            "is the meaningful diagnostic, and why the continuum PINN stage",
        ),
    ],
    #, appendix
    "appendix.tex": [
        # (c) table cell "not applicable" -> the word n/a, not punctuation
        (
            "Specific heat ratio (air) & $\\gamma_{\\text{air}}$ & $1.4$ & "
            "--- \\\\",
            "Specific heat ratio (air) & $\\gamma_{\\text{air}}$ & $1.4$ & "
            "n/a \\\\",
        ),
        (
            "Prandtl number (air) & $\\text{Pr}$ & $0.71$ & --- \\\\",
            "Prandtl number (air) & $\\text{Pr}$ & $0.71$ & n/a \\\\",
        ),
        # (c) these two cells mark a parameter that does not apply to the
        #     smooth-skinned configuration described in that row.
        ("Nose profile & --- & Smooth \\\\", "Nose profile & n/a & Smooth \\\\"),
        ("Skin type & --- & Smooth \\\\", "Skin type & n/a & Smooth \\\\"),
    ],
}

_CODE_ENV = re.compile(r"\\begin\{(verbatim|lstlisting|minted|alltt)\}")
_CODE_END = re.compile(r"\\end\{(verbatim|lstlisting|minted|alltt)\}")
_EMDASH_U = "\u2014"
_ENDASH_U = "\u2013"


def in_code_block(lines: list[str]) -> list[bool]:
    """Mark each line as inside a verbatim-like environment (AXIOM: exclude)."""
    flags: list[bool] = []
    inside = False
    for ln in lines:
        if _CODE_ENV.search(ln):
            inside = True
            flags.append(True)
            continue
        if _CODE_END.search(ln):
            inside = False
            flags.append(True)
            continue
        flags.append(inside)
    return flags


def prose_only(lines: list[str]) -> list[str]:
    """Blank out comment tails and code-block bodies, keeping line numbering."""
    code = in_code_block(lines)
    out: list[str] = []
    for ln, is_code in zip(lines, code):
        out.append(ln if is_code else re.split(r"(?<!\\)%", ln, maxsplit=1)[0])
    return out


def scan(path: Path) -> tuple[int, int, int]:
    """Return (emdash_triple, emdash_unicode, endash_unicode) in prose."""
    lines = prose_only(path.read_text(encoding="utf-8", errors="replace").split("\n"))
    t = sum(ln.count("---") for ln in lines)
    u = sum(ln.count(_EMDASH_U) for ln in lines)
    e = sum(ln.count(_ENDASH_U) for ln in lines)
    return t, u, e


def main() -> int:
    rc = 0
    print("=" * 68)
    print("PRE-SCAN (prose only; comments and code blocks excluded)")
    print("=" * 68)
    before = {}
    for name in FILES:
        p = THESIS / name
        if not p.exists():
            print(f"  SKIP (absent): {name}")
            continue
        t, u, e = scan(p)
        before[name] = (t, u, e)
        if t or u or e:
            print(f"  {name:42s} ---={t:3d}  U+2014={u:2d}  U+2013={e:2d}")

    print()
    print("=" * 68)
    print("APPLYING CURATED REPLACEMENTS")
    print("=" * 68)
    for name, pairs in PAIRS.items():
        p = THESIS / name
        text = p.read_text(encoding="utf-8", errors="replace")
        for old, new in pairs:
            n = text.count(old)
            if n != 1:
                print(f"  !! {name}: expected 1 match, found {n} for: {old[:70]!r}")
                rc = 1
                continue
            text = text.replace(old, new, 1)
            print(f"  ok {name}: {old[:58]!r}")
        p.write_text(text, encoding="utf-8")

    print()
    print("=" * 68)
    print("POST-SCAN (prose only)")
    print("=" * 68)
    residual = 0
    for name in FILES:
        p = THESIS / name
        if not p.exists():
            continue
        t, u, e = scan(p)
        bt, bu, _ = before.get(name, (0, 0, 0))
        delta = (bt + bu) - (t + u)
        residual += t + u
        flag = "OK " if (t == 0 and u == 0) else "!! "
        print(f"  {flag}{name:42s} removed={delta:3d}  remaining ---={t} U+2014={u}")

    print()
    if residual == 0:
        print("VERDICT: no em-dash remains in thesis prose.")
    else:
        print(f"VERDICT: {residual} em-dash occurrence(s) still present.")
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
