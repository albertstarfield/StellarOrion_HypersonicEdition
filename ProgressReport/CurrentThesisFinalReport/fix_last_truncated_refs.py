#!/usr/bin/env python3
"""Replace the last two bibliography entries whose author lists were truncated,
because the records they claimed do not match the works that exist.

ENTRY 1, cassell2014heart  (cited once, Table 2.1 row 4)
============================================================================
The entry claimed:

    author    = {Cassell, Gregory J. and others}
    title     = {Aerothermodynamic Analysis of the High-Energy Atmospheric
                 Reentry Test (HEART) Vehicle}
    booktitle = {52nd Aerospace Sciences Meeting}
    year      = {2014}, publisher = {AIAA}

The HEART aerothermodynamic analysis is a single-author NASA report. NASA NTRS
record 20120008176, retrieved and read:

    title             HEART Aerothermodynamic Analysis
    otherReportNumbers NASA/TM-2012-217568, L-20142, NF1676L-14649
    stiType           TECHNICAL_MEMORANDUM
    authors           Mazaheri, Alireza   NASA Langley Research Center
    submitted         2013-08-25

The work studies an 8.3 m HEART vehicle, generates twelve nose-shape
configurations, compares them at the peak-heating trajectory point, and
recommends a two-piece thermal protection system at the nose so that the
catalytic uncertainty at the nose-IAD juncture falls by at least 93 per cent.
That is precisely the finding Table 2.1 row 4 reports, so the citation was
pointing at the right study under the wrong author, venue and year.

ENTRY 2, lichodziejewski2012oml  (cited twice)
============================================================================
The entry claimed:

    author    = {Lichodziejewski, David and others}
    title     = {Impact of Deformed Outer Mold Line (OML) on the
                 Aerothermodynamic Performance of HIADs}
    booktitle = {22nd AIAA Aerodynamic Decelerator Systems Technology Conference}
    year      = {2012}

No such paper could be found. The deformation study the thesis actually
describes is:

    Guo, Jinghui; Lin, Guiping; Bu, Xueqin; Fu, Shiming; Chao, Yanmeng
    "Effect of static shape deformation on aerodynamics and aerothermodynamics
     of hypersonic inflatable aerodynamic decelerator"
    Acta Astronautica, vol. 136, pp. 421-433, July 2017
    doi:10.1016/j.actaastro.2017.03.019

It is a stacked-tori HIAD, it computes the deformed shape under maximum
aerodynamic pressure, and it reports maximum augmentations of 379 Pa, 2224 Pa
and 19.0 W/cm2, which is 9.8 per cent, 305.9 per cent and 101.6 per cent for
pressure, shear stress and heat flux. A 101.6 per cent heat-flux augmentation is
what Table 2.1 row 3 summarises as "surface irregularities between tori
significantly augment local heat flux", and the paper uses Menter's SST
turbulence model, the same closure the thesis adopts.

The nearest real Lichodziejewski 2012 paper is a different subject,
"Design and Testing of the Inflatable Aeroshell for the IRVE-3 Flight
Experiment", AIAA 2012-1515, which reports structural and packaging test work
rather than a deformation heat-flux study. Attributing the deformation result
to it would misattribute it, so the citation is retargeted to the paper that
actually contains the result.

CITATION
  NASA Technical Reports Server, https://ntrs.nasa.gov/citations/20120008176
  Acta Astronautica, https://doi.org/10.1016/j.actaastro.2017.03.019
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent
BIB = TH / "ref.bib"
CH2 = TH / "chapter_02_literature_review.tex"

NEW_HEART = """@techreport{mazaheri2012heart,
  author      = {Mazaheri, Alireza},
  title       = {{HEART} Aerothermodynamic Analysis},
  institution = {NASA Langley Research Center},
  address     = {Hampton, VA},
  year        = {2012},
  type        = {Technical Memorandum},
  number      = {NASA/TM--2012-217568},
  note        = {NASA Technical Reports Server record 20120008176,
                  report numbers NASA/TM-2012-217568, L-20142, NF1676L-14649}
}
"""

NEW_DEFORM = """@article{guo2017deformation,
  author  = {Guo, Jinghui and Lin, Guiping and Bu, Xueqin and Fu, Shiming and
             Chao, Yanmeng},
  title   = {Effect of Static Shape Deformation on Aerodynamics and
             Aerothermodynamics of Hypersonic Inflatable Aerodynamic
             Decelerator},
  journal = {Acta Astronautica},
  year    = {2017},
  volume  = {136},
  pages   = {421--433},
  doi     = {10.1016/j.actaastro.2017.03.019},
  note    = {Stacked-tori HIAD; reports maximum heat-flux augmentation of
             101.6 per cent under maximum aerodynamic pressure}
}
"""

RETARGET = {
    "cassell2014heart": "mazaheri2012heart",
    "lichodziejewski2012oml": "guo2017deformation",
}

# Row text that named the wrong study.
ROW_OLD_DEFORM = "Deformed Outer Mold Line (OML) Analysis."
ROW_NEW_DEFORM = ("Deformed Outer Mold Line (OML) / shape-deformation analysis of a "
                  "stacked-tori HIAD.")
ROW_OLD_HEART = "Optimized Nose-IAD Junction Geometry."
ROW_NEW_HEART = "Optimized nose-shape and two-piece TPS at the nose-IAD juncture."


def drop_entry(lines: list[str], key: str) -> tuple[list[str], bool]:
    head = re.compile(r"^@[A-Za-z]+\s*\{\s*" + re.escape(key) + r"\s*,")
    for idx, line in enumerate(lines):
        if not head.match(line):
            continue
        depth, end = 0, None
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

    #, citations =======================================================
    t = CH2.read_text(encoding="utf-8")
    for old, new in RETARGET.items():
        n = t.count(old)
        t = t.replace(old, new)
        print(f"  ok  chapter_02: {n} occurrence(s) of {old} -> {new}")
    for old, new in ((ROW_OLD_DEFORM, ROW_NEW_DEFORM), (ROW_OLD_HEART, ROW_NEW_HEART)):
        n = t.count(old)
        if n == 1:
            t = t.replace(old, new, 1)
            print(f"  ok  row text updated: {old[:44]!r}")
        else:
            print(f"  !! row text {old[:44]!r} matched {n} times")
            rc = 1
    CH2.write_text(t, encoding="utf-8")

    #, bibliography ====================================================
    lines = BIB.read_text(encoding="utf-8").split("\n")
    for old in RETARGET:
        lines, ok = drop_entry(lines, old)
        print(f"  {'ok ' if ok else '!! '} ref.bib: removed @{old}")
        rc |= 0 if ok else 1
    BIB.write_text("\n".join(lines).rstrip("\n") + "\n\n" + NEW_HEART + "\n" + NEW_DEFORM,
                   encoding="utf-8")
    print("  ok  ref.bib: added mazaheri2012heart and guo2017deformation")

    #, verify ==========================================================
    bib = BIB.read_text(encoding="utf-8")
    print(f"  entries: {len(re.findall(r'^@', bib, re.M))}   'and others': {bib.count('and others')}")
    if bib.count("and others"):
        rc = 1
    txt = "".join(p.read_text(encoding="utf-8") for p in TH.glob("chapter_*.tex"))
    txt += (TH / "appendix.tex").read_text(encoding="utf-8")
    cites = {k.strip() for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", txt)
             for k in m.group(1).split(",") if k.strip()}
    keys = {m.group(1) for m in re.finditer(r"^@[A-Za-z]+\s*\{\s*([^,]+?)\s*,", bib, re.M)}
    miss = sorted(cites - keys)
    print(f"  unresolved citations: {miss or 'none'}")
    if miss:
        rc = 1
    orphan = sorted(keys - cites)
    print(f"  entries not cited:   {orphan or 'none'}")
    if orphan:
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())