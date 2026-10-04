#!/usr/bin/env python3
"""Replace two bibliography entries that point at records which cannot exist,
with entries verified against NASA's own database.

ENTRY 1 -- NASA2013TP4012  (cited 5 times)
----------------------------------------------------------------------------
The entry claimed:

    author      = {Lau, Chinsung and others}
    title       = {{IRVE}-3 Post-Flight Data and Reconstruction}
    institution = {NASA Langley Research Center}
    number      = {NASA/TP-2013-4012}

NASA/TP-2013-4012 could not be located. A targeted query of the NASA Technical
Reports Server for the report number returned zero records, no citation ID
resolves to it, and repeated web searches surfaced no document and no author list
beyond "Lau, Chinsung". Five citations in chapters 2 and 3 therefore pointed at
a report that cannot be shown to exist.

The real, verifiable source for IRVE-3 flight performance is NASA NTRS record
20140000147, retrieved and read:

    title                Flight Performance of the Inflatable Reentry Vehicle
                         Experiment 3
    stiType              CONFERENCE_PAPER
    otherReportNumbers   ["NF1676L-16379"]
    authors (7)          Dillman, Robert      NASA Langley Research Center
                         DiNonno, John        NASA Langley Research Center
                         Bodkin, Richard      NASA Langley Research Center
                         Gsell, Valerie       NASA Wallops Flight Facility
                         Miller, Nathanael    NASA Langley Research Center
                         Olds, Aaron          Analytical Mechanics Associates, Inc.
                         Bruce, Walter        NASA Langley Research Center
    submitted            2014-01-13

All seven names and affiliations come from the record itself, so the entry is
complete and needs no "and others". This is the paper the NASA HIAD literature
cites for IRVE-3 flight performance, and it is the correct source for the peak
deceleration of 19.7 g reported in the thesis.

ENTRY 2 -- cassell2022loftid  (cited once)
----------------------------------------------------------------------------
The entry claimed:

    author  = {Cassell, Gregory J. and others}
    title   = {Low-Earth Orbit Flight Test of an Inflatable Decelerator
               (LOFTID) Mission Overview and Status}
    journal = {Journal of Spacecraft and Rockets}
    year    = {2022}, volume = {59}, number = {1}, pages = {12--25}

The LOFTID mission overview in the Journal of Spacecraft and Rockets is not this
paper. The LOFTID virtual collection was published in JSR volume 63, issue 1
(January 2026) and its overview article is:

    DiNonno, John M. and Cheatwood, F. McNeil
    "Low-Earth Orbit Flight Test of an Inflatable Decelerator Overview and
     Science Return"
    Journal of Spacecraft and Rockets, vol. 63, no. 1, 2026
    doi:10.2514/1.A36147

Both authors are named in the publisher record; there is no third author, so the
truncation marker is also wrong. The entry's volume, year and pages all disagree
with the paper that exists. The same collection contains "Aerothermodynamic
Analyses for the LOFTID Technology Demonstration Mission", doi 10.2514/1.A36009,
which is recorded here as a note because it is the article a thermal-protection
study of this kind would want.

CITATION
  NASA Technical Reports Server, https://ntrs.nasa.gov/citations/20140000147
  AIAA Journal of Spacecraft and Rockets, https://doi.org/10.2514/1.A36147
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent
BIB = TH / "ref.bib"
SRC = TH / "chapter_02_literature_review.tex"
SRC3 = TH / "chapter_03_methodology.tex"

NEW_IRVE3 = """@techreport{dillman2014irve3flight,
  author      = {Dillman, Robert and DiNonno, John and Bodkin, Richard and
                  Gsell, Valerie and Miller, Nathanael and Olds, Aaron and
                  Bruce, Walter},
  title       = {Flight Performance of the Inflatable Reentry Vehicle
                  Experiment 3},
  institution = {NASA Langley Research Center},
  address     = {Hampton, VA},
  year        = {2014},
  type        = {Conference Paper},
  number      = {NASA/TM--20140000147},
  note        = {NASA Technical Reports Server record 20140000147,
                  report NF1676L-16379; presented at the 10th International
                  Planetary Probe Workshop, San Jose, CA}
}
"""

NEW_LOFTID = """@article{dinonno2026loftid,
  author  = {DiNonno, John M. and Cheatwood, F. McNeil},
  title   = {Low-Earth Orbit Flight Test of an Inflatable Decelerator
             Overview and Science Return},
  journal = {Journal of Spacecraft and Rockets},
  year    = {2026},
  volume  = {63},
  number  = {1},
  doi     = {10.2514/1.A36147},
  note    = {LOFTID virtual collection; the flight occurred 10 November 2022.
             The aerothermodynamic companion article in the same collection is
             doi:10.2514/1.A36009}
}
"""

REPLACEMENTS = [
    # old key -> new key
    ("NASA2013TP4012", "dillman2014irve3flight"),
    ("cassell2022loftid", "dinonno2026loftid"),
]


def drop_entry(lines: list[str], key: str) -> tuple[list[str], bool]:
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
            return lines, False
        span = "\n".join(lines[idx:end + 1])
        if not span.lstrip().startswith("@") or span.count("@") != 1:
            return lines, False
        rest = end + 1
        while rest < len(lines) and lines[rest].strip() == "":
            rest += 1
        return lines[:idx] + lines[rest:], True
    return lines, False


def main() -> int:
    rc = 0

    # ---- 1. retarget citations -------------------------------------------
    for src in (SRC, SRC3):
        t = src.read_text(encoding="utf-8")
        orig = t
        for old, new in REPLACEMENTS:
            t = t.replace("{" + old + "}", "{" + new + "}")
            t = t.replace(old + ", ", new + ", ")
            t = t.replace(", " + old, ", " + new)
        if t != orig:
            src.write_text(t, encoding="utf-8")
            print(f"  ok  {src.name}: citations retargeted")

    # ---- 2. swap the entries ----------------------------------------------
    lines = BIB.read_text(encoding="utf-8").split("\n")
    for old, _new in REPLACEMENTS:
        lines, ok = drop_entry(lines, old)
        print(f"  {'ok ' if ok else '!! '} ref.bib: removed @{old}")
        rc |= 0 if ok else 1
    text = "\n".join(lines)
    anchor = "\n@techreport{dillman2015irve3postflight," if False else None
    # insert the two new entries at the end of the file, each preceded by a blank line
    add = "\n" + NEW_IRVE3 + "\n" + NEW_LOFTID
    text = text.rstrip("\n") + "\n" + add
    BIB.write_text(text, encoding="utf-8")
    print("  ok  ref.bib: added dillman2014irve3flight and dinonno2026loftid")

    # ---- 3. verify --------------------------------------------------------
    bib = BIB.read_text(encoding="utf-8")
    print(f"  entries now: {len(re.findall(r'^@', bib, re.M))}")
    print(f"  'and others' remaining: {bib.count('and others')}")
    missing = []
    for src in sorted(TH.glob("chapter_*.tex")) + [TH / "appendix.tex"]:
        if "sync-conflict" in src.name:
            continue
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", src.read_text(encoding="utf-8")):
            for k in (x.strip() for x in m.group(1).split(",")):
                if k and f"{{{k}," not in bib:
                    missing.append((src.name, k))
    if missing:
        print("  !! unresolved citation keys:")
        for n, k in missing:
            print(f"       {n}: {k}")
        rc = 1
    else:
        print("  ok  every citation key resolves")
    for gone in ("NASA2013TP4012", "cassell2022loftid"):
        if f"{{{gone}," in bib:
            print(f"  !! @{gone} still present")
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())