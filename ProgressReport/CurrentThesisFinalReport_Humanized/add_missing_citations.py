#!/usr/bin/env python3
"""Cite the external facts the thesis states without a source, and remove a
duplicated paragraph that narrates its own editing history.

ADDED SOURCE 1, U.S. Standard Atmosphere, 1976
============================================================================
The thesis evaluates its freestream state "under ISA" in at least four places:

    chapter_02: "the ISA freestream density rho_inf = 1.05e-3 kg/m3"
    chapter_02: "the ISA 52 km freestream density"
    chapter_03: "the SPARTA DSMC run condition (h = 51.8 km under ISA, which
                  yields rho_inf = 7.851e-4 kg/m3)"
    chapter_04: "the SPARTA DSMC run condition (h = 51.8 km, ISA
                  rho_inf = 7.851e-4 kg/m3)"

Not one of them carried a citation. The International Standard Atmosphere is the
definition of those densities, and stellarorion_program_proc/docs/CITATIONS.md,
the repository's own master reference list, names the source as:

    [US76] U.S. Standard Atmosphere, 1976, NOAA/NASA/USAF.
           Layer structure and lapse rates of the ISA model implemented in
           stellarorion_environment.adb

so the repository already records where the model comes from and the thesis
simply did not cite it. The entry is added and all four statements now cite it.

ADDED SOURCE 2, CODATA 2018
============================================================================
Appendix Table A.1 lists the physical constants and attributes them to the code:

    "Fundamental physical constants used in StellarOrion
     (from stellarorion_types.ads)."

Attributing a constant to the file that consumes it is not a source. The same
repository document records the true origin:

    [CODATA] CODATA 2018 recommended values (https://physics.nist.gov).
              Stefan-Boltzmann constant sigma = 5.670374419e-8 W/(m^2 K^4),
              Avogadro N_A = 6.02214076e23 mol^-1, molar mass of air
              M = 28.97e-3 kg/mol.

The table values are exactly those CODATA values, so the caption now cites
CODATA 2018 alongside naming the consuming source.

CITED EXISTING SOURCE, Bird (1994) for the mean free path
============================================================================
Chapter 2 evaluates Eq. for the mean free path with a hard-sphere molecular
diameter of 3.7e-10 m. That formula and that constant are Bird's, and
docs/CITATIONS.md names [Bird94] as the source for "Mean-free-path formula
lambda = 1/(sqrt(2) pi d^2 n)". Bird is already in the bibliography as
bird1994molecular and was not cited at this point.

DUPLICATED PARAGRAPH
============================================================================
chapter_03:437 and chapter_04:43 were two versions of the same paragraph, and
the Chapter 4 copy still said the values "were corrected during the course of
the work" and referred to "earlier revisions of this work". Chapter 3 had
already been rewritten to state provenance instead. Both now state the same
thing the same way, so the two copies no longer diverge.

CITATION
  NOAA/NASA/USAF, U.S. Standard Atmosphere, 1976, NASA/TM X-71469
  NIST, CODATA 2018 recommended values, https://physics.nist.gov
  Bird, G. A., Molecular Gas Dynamics, Oxford University Press, 1994
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent

NEW_ISA = """@techreport{usstandard1976,
  author      = {{U.S. National Aeronautics and Space Administration and
                  National Oceanic and Atmospheric Administration and U.S. Air
                  Force}},
  title       = {{U.S.} Standard Atmosphere, 1976},
  institution = {NASA Langley Research Center},
  address     = {Hampton, VA},
  year        = {1976},
  type        = {Technical Memorandum},
  number      = {NASA/TM X--71469},
  note        = {Layer structure and lapse rates of the ISA model implemented in
                  \\texttt{stellarorion\\_environment.adb}; the international
                  reference is ISO 2533:1975}
}
"""

NEW_CODATA = """@techreport{codata2018,
  author      = {{Committee on Data for Science and Technology}},
  title       = {{CODATA} Recommended Values 2018},
  institution = {National Institute of Standards and Technology},
  address     = {Gaithersburg, MD},
  year        = {2018},
  type        = {Technical Report},
  note        = {https://physics.nist.gov/cuu/Constants/; supplies the
                  Stefan-Boltzmann constant, the Avogadro constant and the
                  molar mass of air quoted in Appendix~A}
}
"""

# (file, old, new) exact replacements.
EDITS = [
    #, ISA statements =================================================
    ("chapter_02_literature_review.tex",
     "places the IRVE-3 freestream in the deep-continuum regime, not the "
     "transition regime.",
     "places the IRVE-3 freestream in the deep-continuum regime, not the "
     "transition regime~\\cite{bird1994molecular}."),
    ("chapter_02_literature_review.tex",
     "molecular diameter $d = 3.7\\times10^{-10}$~m and the ISA freestream density",
     "molecular diameter $d = 3.7\\times10^{-10}$~m~\\cite{bird1994molecular} and the "
     "ISA freestream density~\\cite{usstandard1976}"),
    ("chapter_02_literature_review.tex",
     "$L = 3.0$~m and the ISA 52~km freestream density gives",
     "$L = 3.0$~m and the ISA 52~km freestream density~\\cite{usstandard1976} gives"),
    ("chapter_03_methodology.tex",
     "($h = 51.8$\\,km under ISA, which yields $\\rho_{\\infty} = "
     "7.851 \\times 10^{-4}$\\,kg/m$^3$)",
     "($h = 51.8$\\,km under ISA~\\cite{usstandard1976}, which yields "
     "$\\rho_{\\infty} = 7.851 \\times 10^{-4}$\\,kg/m$^3$)"),
    # The anchor is the ISA density alone, not the whole parenthetical: the real
    # text continues ", $V_\\infty = 3{,}378$\\,m/s)" after the density.
    ("chapter_04_results.tex",
     "ISA $\\rho_{\\infty} = 7.851 \\times 10^{-4}$",
     "ISA~\\cite{usstandard1976} $\\rho_{\\infty} = 7.851 \\times 10^{-4}$"),
    #, CODATA ========================================================
    ("appendix.tex",
     "\\caption{Fundamental physical constants used in StellarOrion "
     "(from \\texttt{stellarorion\\_types.ads}).}",
     "\\caption{Fundamental physical constants used in StellarOrion, as "
     "consumed by \\texttt{stellarorion\\_types.ads} and taken from the 2018 "
     "recommended values~\\cite{codata2018}.}"),
    #, Chapter 4 duplicate of the Chapter 3 provenance paragraph =======
    ("chapter_04_results.tex",
     "The correlation constant and the nose radius used here were corrected "
     "during the course of the work. The value reported in earlier revisions of "
     "this work, $12.20$\\,W/cm$^2$, followed from the superseded pair "
     "$C_{SG} = 1.7415 \\times 10^{-4}$, $R_N = 0.55$\\,m evaluated at a "
     "hardcoded",
     "The correlation constant and the nose radius used here both differ from "
     "the engine defaults, so their provenance is stated. The engine default is "
     "$C_{SG} = 1.7415 \\times 10^{-4}$ and $R_N = 0.55$\\,m; the pair evaluated "
     "at a hardcoded"),
    ("chapter_04_results.tex",
     "rather than at the run condition. Because the correlation scales as "
     "$1/\\sqrt{R_N}$, the superseded $0.55$\\,m nose radius alone raised the "
     "computed flux by a factor of $\\sqrt{1.5/0.55} \\approx 1.65$. The "
     "corrected value is $+12.4\\%$ relative to the flight measurement and is "
     "reported in this work as the headline stagnation heat flux.",
     "rather than at the run condition, and yields $12.20$\\,W/cm$^2$. Because the "
     "correlation scales as $1/\\sqrt{R_N}$, the engine-default $0.55$\\,m nose "
     "radius alone raises the computed flux by a factor of "
     "$\\sqrt{1.5/0.55} \\approx 1.65$. At the run condition the value is "
     "$+12.4\\%$ relative to the flight measurement, and it is this work's "
     "headline stagnation heat flux."),
]


def main() -> int:
    rc = 0
    for fname, old, new in EDITS:
        p = TH / fname
        t = p.read_text(encoding="utf-8")
        n = t.count(old)
        if n != 1:
            print(f"  !! {fname}: anchor matched {n} times: {old[:60]!r}")
            rc = 1
            continue
        p.write_text(t.replace(old, new, 1), encoding="utf-8")
        print(f"  ok  {fname}: {old[:56]!r}")

    bib = TH / "ref.bib"
    t = bib.read_text(encoding="utf-8")
    added = []
    for key, block in (("usstandard1976", NEW_ISA), ("codata2018", NEW_CODATA)):
        if f"{{{key}," in t:
            print(f"  --  ref.bib: @{key} already present")
            continue
        t = t.rstrip("\n") + "\n\n" + block
        added.append(key)
    bib.write_text(t, encoding="utf-8")
    print(f"  ok  ref.bib: added {added}")

    #, verify every citation resolves ==================================
    txt = "".join((TH / f).read_text(encoding="utf-8")
                  for f in ("chapter_01_introduction.tex",
                            "chapter_02_literature_review.tex",
                            "chapter_03_methodology.tex",
                            "chapter_04_results.tex",
                            "chapter_05_conclusion.tex",
                            "appendix.tex"))
    cites = {k.strip() for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", txt)
             for k in m.group(1).split(",") if k.strip()}
    keys = {m.group(1) for m in re.finditer(r"^@[A-Za-z]+\s*\{\s*([^,]+?)\s*,",
                                            bib.read_text(encoding="utf-8"), re.M)}
    miss = sorted(cites - keys)
    print(f"  unresolved citations: {miss or 'none'}")
    if miss:
        rc = 1
    print(f"  entries not cited:   {sorted(keys - cites) or 'none'}")
    if keys - cites:
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())