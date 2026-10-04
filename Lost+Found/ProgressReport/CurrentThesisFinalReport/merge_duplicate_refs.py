#!/usr/bin/env python3
"""Merge the duplicated IRVE-3 references and remove two double-citations.

WHAT WAS WRONG, AND THE EVIDENCE FOR EACH MERGE
=============================================================================

MERGE A -- lau2013irve and lau2013irve3 collapse into old2013irve3postflight
----------------------------------------------------------------------------
The reference database held THREE entries for ONE paper:

    lau2013irve          "Inflatable Re-entry Vehicle Experiment 3 (IRVE-3)
                          Post-Flight Aerothermal Reconstruction"
                          author = "Lau, Kai and Cheatwood, Neil and others"
                          note   = "AIP-2013-4012"          CITED 0 TIMES

    lau2013irve3         same title, same authors, same note   CITED 4 TIMES

    old2013irve3postflight
                          "IRVE-3 Post-Flight Reconstruction"
                          10 authors beginning "Olds, Aaron"  CITED 6 TIMES

NASA's own record settles it. NTRS submission 20130013398
(https://ntrs.nasa.gov/api/citations/20130013398, retrieved and read) gives:

    title             IRVE-3 Post-Flight Reconstruction
    otherReportNumbers ["AIAA Paper 1514242"]
    stiType           CONFERENCE_PAPER
    authors           Olds, Aaron D.   Analytical Mechanics Associates, Inc.
                      Beck, Roger     Analytical Mechanics Associates, Inc.
                      Bose, David     Analytical Mechanics Associates, Inc.
                      White, Joseph    Analytical Mechanics Associates, Inc.
                      Edquist, Karl   NASA Langley Research Center
                      Hollis, Brian   NASA Langley Research Center
                      Lindell, Michael NASA Langley Research Center
                      Cheatwood, F.N. NASA Langley Research Center
                      Gsell, Valerie   Orbital Sciences Corp.
                      Bowden, Ernest   Orbital Sciences Corp.

The same ten names appear in the author block of the paper's own first page.
So the two lau* entries carry a first author who is not on the paper, and a
report number ("AIP-2013-4012") that matches nothing. All three keys are merged
into the entry that was already correct.

This also removes a genuine citation defect: Chapter 4 line 156 read
    \\cite{lau2013irve3, old2013irve3postflight}
which cited the SAME work twice inside one citation.

MERGE B -- Lau2013 collapses into NASA2013TP4012
----------------------------------------------------------------------------
Both entries describe NASA/TP-2013-4012 by Lau, Chinsung, 2013:

    Lau2013            @article, "journal = {NASA Technical Report}",
                       note = {NASA/TP-2013-4012}
    NASA2013TP4012     @techreport, number = {NASA/TP-2013-4012}

A NASA Technical Reports Server document is a @techreport, not an @article, and
a "journal" field of "NASA Technical Report" is not a venue. Chapter 2 line 1354
cited both keys in one \\cite for the same report. The @techreport form is kept
because it is the correct BibTeX type for a NASA TP.

WHAT THIS DOES NOT DO
=============================================================================
The remaining `and others` author lists are NOT invented. NASA/TP-2013-4012
could not be located on the NASA Technical Reports Server: a targeted search for
the report number returned zero records, and no web result surfaced the document
or an author list beyond "Lau, Chinsung". Leaving one truncated author list is
the honest outcome; writing plausible names would be a fabricated citation, which
is worse than a style warning.

CITATION
  NASA Technical Reports Server, https://ntrs.nasa.gov/
  BibTeX entry types, https://tug.org/texlive/Compendium/
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent
BIB = TH / "ref.bib"

# Keys removed entirely, and the key each is replaced by.
RETARGET = {
    "lau2013irve": "old2013irve3postflight",
    "lau2013irve3": "old2013irve3postflight",
    "Lau2013": "NASA2013TP4012",
}


def drop_entry(text: str, key: str) -> tuple[str, bool]:
    """Remove one complete @-entry, including the blank line after it.

    Two earlier implementations of this function damaged ref.bib, producing
    fragments such as "@techreport@article{cassell2022loftid,". Both failures
    came from locating the entry by searching for a SUBSTRING of the key and then
    walking BACKWARDS for an "@", which can land on a previous entry's type token.
    This version locates the entry by its own header line and walks FORWARD from
    there, and it verifies that the removed span actually contains the key and
    ends at a closing brace before writing anything.
    """
    lines = text.split("\n")
    head_re = re.compile(r"^@" + r"[A-Za-z]+" + r"\s*\{\s*" + re.escape(key) + r"\s*,")
    for idx, line in enumerate(lines):
        if not head_re.match(line):
            continue
        depth = 0
        end = None
        for j in range(idx, len(lines)):
            # A comment or a blank line cannot change brace depth for these files,
            # and no entry contains a line comment.
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                end = j
                break
        if end is None:
            return text, False
        span = "\n".join(lines[idx:end + 1])
        # Verify before cutting: the span must be the entry and nothing else.
        if not span.lstrip().startswith("@") or f"{key}," not in span:
            return text, False
        if "\n@" in "\n" + span and span.count("@") != 1:
            return text, False
        rest = end + 1
        while rest < len(lines) and lines[rest].strip() == "":
            rest += 1
        return "\n".join(lines[:idx] + lines[rest:]), True
    return text, False


def main() -> int:
    rc = 0

    # ---- 1. remove the double citation of one work inside one \cite ---------
    old = r"\cite{lau2013irve3, old2013irve3postflight}"
    new = r"\cite{old2013irve3postflight}"
    hits = 0
    for name in ("chapter_04_results.tex",):
        p = TH / name
        t = p.read_text(encoding="utf-8")
        if old in t:
            t = t.replace(old, new)
            p.write_text(t, encoding="utf-8")
            hits += 1
            print(f"  ok  {name}: collapsed the double citation of one work")
    if hits == 0:
        print("  !! expected double citation not found")
        rc = 1

    old2 = r"\cite{NASA2013TP4012, Lau2013}"
    new2 = r"\cite{NASA2013TP4012}"
    p = TH / "chapter_02_literature_review.tex"
    t = p.read_text(encoding="utf-8")
    if old2 in t:
        p.write_text(t.replace(old2, new2), encoding="utf-8")
        print("  ok  chapter_02_literature_review.tex: collapsed the double "
              "citation of NASA/TP-2013-4012")
    else:
        print("  !! expected double citation not found in chapter 2")
        rc = 1

    # ---- 2. retarget every remaining citation ------------------------------
    for src in sorted(TH.glob("chapter_*.tex")) + sorted(TH.glob("appendix*.tex")):
        if "sync-conflict" in src.name:
            continue
        t = src.read_text(encoding="utf-8")
        orig = t
        for old_key, target in RETARGET.items():
            t = t.replace("{" + old_key + "}", "{" + target + "}")
            t = t.replace(old_key + ", ", target + ", ")
            t = t.replace(", " + old_key, ", " + target)
        if t != orig:
            src.write_text(t, encoding="utf-8")
            print(f"  ok  {src.name}: retargeted citations")

    # ---- 3. delete the merged entries from the database --------------------
    t = BIB.read_text(encoding="utf-8")
    for key in RETARGET:
        t, ok = drop_entry(t, key)
        print(f"  {'ok ' if ok else '!! '} ref.bib: removed @{key}"
              + ("" if ok else "  (entry not found)"))
        if not ok:
            rc = 1
    BIB.write_text(t, encoding="utf-8")

    # ---- 4. prove no key is now missing from ref.bib -----------------------
    missing = []
    for src in sorted(TH.glob("chapter_*.tex")) + sorted(TH.glob("appendix*.tex")):
        if "sync-conflict" in src.name:
            continue
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}",
                                           src.read_text(encoding="utf-8")):
            for key in (k.strip() for k in m.group(1).split(",")):
                if key and f"{{{key}," not in t and f"{{{key}}}" not in t:
                    missing.append((src.name, key))
    if missing:
        print("  !! citation keys with no bib entry:")
        for name, key in missing:
            print(f"       {name}: {key}")
        rc = 1
    else:
        print("  ok  every citation key in every chapter resolves to an entry")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())