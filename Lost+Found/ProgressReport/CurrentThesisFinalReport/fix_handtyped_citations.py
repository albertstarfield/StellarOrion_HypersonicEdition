#!/usr/bin/env python3
"""Turn 31 hand-typed author-year citations into real \\cite commands, and
collapse three duplicate entries for one Anderson 2006 book.

DEFECT 1, THREE KEYS FOR ONE BOOK
============================================================================
ref.bib held the same book three times:

    AndersonHypersonic     Anderson, John D., Hypersonic and High-Temperature
    anderson2006hypersonic Gas Dynamics, 2nd ed., AIAA, 2006     cited 20x
    Anderson2006           (identical work)                      cited 0x

30 citations therefore split across three keys for one source. All are merged
into AndersonHypersonic, which is the key the text already uses most.

DEFECT 2, 31 AUTHOR-YEAR CITATIONS THAT BYPASS THE BIBLIOGRAPHY
============================================================================
Thirty-one places in the thesis write the citation out by hand instead of using
\\cite, for example

    The IRVE-3 flight measurement reports a peak heat flux of 14.36 W/cm2.
    Rapisarda (2023) reports the trajectory-integrated Sutton-Graves peak ...

    \\textbf{Lichodziejewski et al. (2012)} & Deformed Outer Mold Line (OML) ...

Consequences, all real:

  * The citation cannot be checked. Nothing links the text to the entry, so a
    wrong author or year in the entry is invisible.
  * A reader cannot trace the claim to the reference list.
  * The bibliography entries these refer to appear UNCITED. That is why
    cassell2022loftid, cassell2014heart, lichodziejewski2012oml and
    pmlr117-vinod19a all measured zero citations despite three of them being
    discussed in the literature-review table. Their BibTeX "and others"
    truncation warnings were therefore never attributable from the text.

Each conversion below is an EXACT string replacement, listed so the effect can
be read before it is applied. Nothing is inferred from a pattern match on free
text: an earlier heuristic sweep found 32 candidate sites, and one of them
(chapter 2 line 127, the string "(Anderson, 2006)") sits inside a LaTeX COMMENT
that documents why that attribution was withdrawn. It is deliberately not in
this table.

CITATION
  apacite, https://ctan.org/pkg/apacite
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

TH = Path(__file__).resolve().parent

# key every citation is retargeted to
ANDERSON_TARGET = "AndersonHypersonic"
ANDERSON_REMOVE = ["anderson2006hypersonic", "Anderson2006"]

# (old, new) exact strings. Order matters only in that the first match wins;
# none of these are prefixes of one another in a way that causes a misfire.
REPLACEMENTS: list[tuple[str, str]] = [
    #, narrative "Author (Year)" -> \\cite ===============================
    ("Rapisarda (2023)", r"\cite{rapisarda2023mdao}"),
    ("Bird (1994)", r"\cite{bird1994molecular}"),
    ("Raissi et al. (2019)", r"\cite{raissi2019pinn}"),
    #, narrative wrapped in \\textit =====================================
    (r"\textit{Lau et al. (2013)}", r"\cite{NASA2013TP4012}"),
    (r"\textit{Lichodziejewski et al. (2012)}", r"\cite{lichodziejewski2012oml}"),
    (r"\textit{Menter (1994)}", r"\cite{menter1994SST}"),
    #, parenthetical "(Author, Year)" inside table cells =================
    ("(Lau et al., 2013)", r"\cite{NASA2013TP4012}"),
    ("(Cassell et al., 2022)", r"\cite{cassell2022loftid}"),
    ("(Cassell et al., 2014)", r"\cite{cassell2014heart}"),
    #, a whole-cell citation, kept bold as the table already had it ======
    (r"\textbf{Lichodziejewski et al. (2012)}", r"\textbf{\cite{lichodziejewski2012oml}}"),
    (r"\textbf{Menter (1994)}", r"\textbf{\cite{menter1994SST}}"),
    #, two citations sharing one parenthesis ============================
    ("(Cybenko, 1989; Hornik et al., 1989)",
     r"\cite{cybenko1989approximation, hornik1989multilayer}"),
    #, the one caption, where the outer parentheses were the problem ====
    # "Bounds (Rapisarda 2023 Envelope)." -> "Bounds from \\cite{...}."
    # A \\cite already emits its own parentheses, so keeping the outer pair
    # would have printed "((Rapisarda, 2023) envelope)".
    ("Optimization Design Variables and Their Bounds (Rapisarda 2023 Envelope)",
     r"Optimization design variables and their bounds, from \cite{rapisarda2023mdao}"),
]


def drop_entry(text: str, key: str) -> tuple[str, bool]:
    """Remove one @-entry. Locates it by its own header line and verifies the
    span before cutting; see merge_duplicate_refs.py for why the earlier
    substring-search version damaged the file."""
    lines = text.split("\n")
    head = re.compile(r"^@[A-Za-z]+\s*\{\s*" + re.escape(key) + r"\s*,")
    for idx, line in enumerate(lines):
        if not head.match(line):
            continue
        depth = 0
        end = None
        for j in range(idx, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                end = j
                break
        if end is None:
            return text, False
        span = "\n".join(lines[idx:end + 1])
        if not span.lstrip().startswith("@") or f"{key}," not in span:
            return text, False
        if span.count("@") != 1:
            return text, False
        rest = end + 1
        while rest < len(lines) and lines[rest].strip() == "":
            rest += 1
        return "\n".join(lines[:idx] + lines[rest:]), True
    return text, False


def main() -> int:
    rc = 0
    files = [p for p in sorted(TH.glob("chapter_*.tex")) + sorted(TH.glob("appendix*.tex"))
             if "sync-conflict" not in p.name]

    #, 1. retarget the duplicate Anderson citations =====================
    print("Duplicate Anderson 2006 keys:")
    n = 0
    for src in files:
        t = src.read_text(encoding="utf-8")
        orig = t
        for old in ANDERSON_REMOVE:
            t = t.replace("{" + old + "}", "{" + ANDERSON_TARGET + "}")
            t = t.replace(old + ", ", ANDERSON_TARGET + ", ")
            t = t.replace(", " + old, ", " + ANDERSON_TARGET)
        if t != orig:
            src.write_text(t, encoding="utf-8")
            cnt = sum(orig.count(x) for x in ANDERSON_REMOVE)
            print(f"  ok  {src.name}: {cnt} citation(s) retargeted to {ANDERSON_TARGET}")
            n += cnt

    #, 2. convert hand-typed citations =================================
    print("\nHand-typed citations converted to \\cite:")
    total = 0
    for src in files:
        t = src.read_text(encoding="utf-8")
        orig = t
        applied: list[tuple[str, int]] = []
        for old, new in REPLACEMENTS:
            k = t.count(old)
            if k:
                t = t.replace(old, new)
                applied.append((old, k))
        if t != orig:
            src.write_text(t, encoding="utf-8")
            for old, k in applied:
                total += k
                print(f"  ok  {src.name}: {k}x  {old[:46]!r}")
    print(f"  total converted: {total}")

    #, 3. drop the two now-uncited duplicate entries ===================
    print("\nDuplicate entries removed from ref.bib:")
    bib = TH / "ref.bib"
    t = bib.read_text(encoding="utf-8")
    for key in ANDERSON_REMOVE:
        t, ok = drop_entry(t, key)
        print(f"  {'ok ' if ok else '!! '} @{key}")
        if not ok:
            rc = 1
    bib.write_text(t, encoding="utf-8")

    #, 4. every citation key must resolve ==============================
    bib_txt = bib.read_text(encoding="utf-8")
    missing = []
    for src in files:
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", src.read_text(encoding="utf-8")):
            for key in (k.strip() for k in m.group(1).split(",")):
                if key and f"{{{key}," not in bib_txt:
                    missing.append((src.name, key))
    if missing:
        print("\n  !! citation keys with no bib entry:")
        for name, key in missing:
            print(f"       {name}: {key}")
        rc = 1
    else:
        print("\n  ok  every citation key in every chapter resolves to an entry")

    #, 5. no hand-typed author-year citations left =====================
    surnames: dict[str, str] = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", bib_txt, re.S):
        a = re.search(r"author\s*=\s*\{(.+?)\}\s*,\s*\n", m.group(3), re.S)
        if not a:
            continue
        first = a.group(1).split(" and ")[0].strip()
        sur = first.split(",")[0].strip() if "," in first else first.split()[-1]
        y = re.search(r"year\s*=\s*\{?\s*(\d{4})", m.group(3))
        if sur:
            surnames.setdefault(sur.lower(), y.group(1) if y else "")
    pat = re.compile(r"([A-Z][A-Za-z\-']+)(?:\s+et\s+al\.)?\s*[,(]\s*\(?(\d{4})\)?")
    left = []
    for src in files:
        for i, line in enumerate(src.read_text(encoding="utf-8").split("\n"), 1):
            stripped = line.lstrip()
            if stripped.startswith("%"):
                continue
            body = re.sub(r"\\cite[a-z]*\{[^}]*\}", "", line)
            for m in pat.finditer(body):
                sur = m.group(1).lower()
                if sur in surnames and surnames[sur] == m.group(2):
                    left.append((src.name, i, m.group(0)))
    if left:
        print("\n  hand-typed author-year citations still present:")
        for name, i, txt in left:
            print(f"       {name}:{i}  {txt!r}")
    else:
        print("  ok  no hand-typed author-year citation remains outside LaTeX comments")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())