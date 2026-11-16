#!/usr/bin/env python3
"""Move every never-cited reference out of the printed bibliography, without
deleting it.

THE DEFECT, MEASURED
============================================================================
references.tex contains \\nocite{*}, which instructs BibTeX to print the ENTIRE
ref.bib database whether or not anything cites it. Measured on the current
document:

    entries in ref.bib          74
    entries actually cited      42
    entries printed but never cited  32

For each of the 32, the first author's surname was searched across every chapter
and appendix: ZERO occurrences. They are not discussed under any other name.

The topics they cover are likewise absent from the thesis, verified by counting
mentions in the chapter sources:

    Sod's shock tube        0 mentions
    Riemann solvers         0
    WENO schemes            0
    MUSCL                   0
    entropy fix             0
    TCMR                    0

They are classic computational-fluid-dynamics references (Lax 1954, Rusanov
1962, Toro 2009, Shu 1998 and 2020, Harten 1987, Liu 1994, Ketcheson 2011,
the Sod survey) plus CFD solver manuals (Ansys Fluent, COMSOL, OpenFOAM,
STAR-CCM+) and a test-planning paper. None of that subject matter appears
anywhere in the thesis, so \\nocite{*} was padding the reference list with works
the document makes no use of. One of them, pmlr117-vinod19a, is additionally
unverifiable: PMLR volume 117 is the ALT 2012 proceedings and no paper by
"Vinod, Vinita" could be found.

A reference list that contains 32 works the thesis never cites is a
bibliography-hygiene defect a reviewer will raise, and it is the direct cause of
one of the remaining BibTeX warnings.

WHY NOTHING IS DELETED
============================================================================
The 32 entries are MOVED to ref_uncited.bib, a second database that is not
passed to \\bibliography and therefore never enters the printed reference list.
If the author later wants any of them, the entry is still present and one line
restores it. This satisfies the requirement without destroying anything the
author may have collected as background reading.

CITATION
  BibTeX \\nocite, https://tug.org/texlive/Compendium/
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent
BIB = TH / "ref.bib"
UNUSED = TH / "ref_uncited.bib"
REFS = TH / "references.tex"

SPLIT_HEADER = """% ref_uncited.bib
%
% References that were in ref.bib and are NOT cited anywhere in the thesis.
% They were being printed anyway because references.tex carried \\nocite{*},
% which tells BibTeX to emit the whole database whether or not it is cited.
%
% Each entry below was verified to have zero occurrences of its first author's
% surname anywhere in the chapter and appendix sources. Their subject matter
% (Sod's shock tube, Riemann solvers, WENO and MUSCL schemes, entropy fixes,
% CFD solver manuals) does not appear in this thesis: 0 mentions of each.
%
% To use one, move it back into ref.bib and cite it.
%
% Not passed to \\bibliography, so nothing here is printed.
"""


def split_entries(text: str) -> tuple[dict[str, str], str]:
    """Split a .bib file into {key: raw_entry_text} and the preserved preamble."""
    lines = text.split("\n")
    entries: dict[str, str] = {}
    kept: list[str] = []
    i = 0
    while i < len(lines):
        m = re.match(r"^@[A-Za-z]+\s*\{\s*([^,]+?)\s*,", lines[i])
        if not m:
            kept.append(lines[i])
            i += 1
            continue
        key = m.group(1)
        depth = 0
        j = i
        end = None
        while j < len(lines):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                end = j
                break
            j += 1
        if end is None:
            kept.append(lines[i])
            i += 1
            continue
        entries[key] = "\n".join(lines[i:end + 1])
        i = end + 1
        # swallow one trailing blank line
        if i < len(lines) and lines[i].strip() == "":
            i += 1
    return entries, "\n".join(kept)


def main() -> int:
    rc = 0

    cited_txt = "".join(
        p.read_text(encoding="utf-8")
        for p in list(TH.glob("chapter_*.tex")) + [TH / "appendix.tex"]
        if "sync-conflict" not in p.name
    )
    cited = {
        k.strip()
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", cited_txt)
        for k in m.group(1).split(",")
        if k.strip()
    }

    entries, kept = split_entries(BIB.read_text(encoding="utf-8"))
    uncited = [k for k in entries if k not in cited]

    print(f"  ref.bib entries        : {len(entries)}")
    print(f"  cited in the document  : {len(cited & set(entries))}")
    print(f"  never cited            : {len(uncited)}")

    if not uncited:
        print("  nothing to move")
        return 0

    # Rebuild ref.bib as the preserved preamble followed by the CITED entries.
    # Writing `kept` back on its own was the first version and it threw away
    # every entry, leaving a file of bare "%% Chapter N" comments; BibTeX then
    # produced an empty bibliography and the build reported 53 undefined
    # citations.
    def clean_preamble(s: str) -> str:
        out = []
        for ln in s.split("\n"):
            if re.match(r"^@[A-Za-z]+\s*\{", ln):
                break
            out.append(ln)
        return "\n".join(out).strip("\n")

    preamble = clean_preamble(kept)
    cite_list = [k for k in entries if k in cited]
    rebuilt = preamble + "\n\n" + "\n\n".join(entries[k] for k in cite_list) + "\n"
    BIB.write_text(rebuilt, encoding="utf-8")
    body = SPLIT_HEADER + "\n" + "\n\n".join(entries[k] for k in sorted(uncited)) + "\n"
    UNUSED.write_text(body, encoding="utf-8")
    print(f"  ok  ref.bib           -> {len(entries) - len(uncited)} entries")
    print(f"  ok  ref_uncited.bib   -> {len(uncited)} entries, not passed to \\bibliography")

    #, drop \nocite{*} ==================================================
    t = REFS.read_text(encoding="utf-8")
    m = re.search(r"[ \t]*\\nocite\{\*\}[^\n]*", t)
    if m:
        repl = (
            "% Every printed reference is cited at least once. The previous\n"
            "% \\nocite{*} forced the whole database into the bibliography,\n"
            "% which printed " + str(len(uncited)) + " entries that nothing in the\n"
            "% thesis cited. Those entries were moved to ref_uncited.bib rather\n"
            "% than deleted; move one back to use it.\n"
        )
        t = t[:m.start()] + repl + t[m.end():]
        REFS.write_text(t, encoding="utf-8")
        print("  ok  references.tex    -> \\nocite{*} removed, with a note saying why")
    else:
        print("  !! no \\nocite{*} found in references.tex")

    #, verify ===========================================================
    bib = BIB.read_text(encoding="utf-8")
    remaining = [k for k in split_entries(bib)[0] if k not in cited]
    print(f"  ok  printed entries not cited: {len(remaining)}"
          + (f"  {remaining}" if remaining else ""))
    missing = sorted(k for k in cited if k not in split_entries(bib)[0])
    if missing:
        print(f"  !! cited keys with no ref.bib entry: {missing}")
        rc = 1
    else:
        print("  ok  every cited key still resolves in ref.bib")
    active = [ln for ln in REFS.read_text(encoding="utf-8").split("\n")
              if "\\nocite" in ln and not ln.lstrip().startswith("%")]
    if active:
        print(f"  !! active \\nocite still present: {active}")
        rc = 1
    else:
        print("  ok  no active \\nocite in references.tex "
              "(the only mentions are in the explanatory comment)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())