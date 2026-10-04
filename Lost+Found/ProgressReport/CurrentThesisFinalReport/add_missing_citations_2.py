#!/usr/bin/env python3
"""Add the citations the audit found missing, and remove a third copy of a
paragraph that narrates its own editing history.

WHAT THE AUDIT FOUND
----------------------------------------------------------------------------
Dimension 11 of audit.py flags paragraphs that assert a fact about a named
external programme, standard or mission and cite nothing. After figure, table and
itemize environments were removed, twelve paragraphs remained. Reading each one
separated six genuine omissions from six statements of this work's own results,
which need no citation. The six omissions and the sources now attached:

  chapter_01   "the first computational framework that couples automated
                parametric geometry generation (CadQuery), high-fidelity DSMC
                rarefied gas dynamics (SPARTA), Physics-Informed Neural Network
                refinement (DeepXDE)"
                -> names three external tools. SPARTA is plimpton2014sparta and
                   DeepXDE is lu2021deepxde; neither was cited here.

  chapter_03   "SPARTA tracks millions of simulated particles through three
                fundamental processes"
                -> describes the external solver.

  chapter_03   "loaded at run time from the IRVE-3 validation run ...
                q_ref = 14.361 W/cm2"
                -> 14.361 W/cm2 is the IRVE-3 flight peak heat flux, an external
                   measurement.

  chapter_04   "It is important to state precisely what the 16.14 W/cm2 figure
                represents ... the same class of quantity as Rapisarda's
                trajectory-integrated SG value of 15.26 W/cm2"
                -> 15.26 W/cm2 is Rapisarda's value.

  chapter_04   "the IRVE-3 flexible-TPS structural limit of 523.15 K" together
                with the five-ply layup
                -> the IRVE-3 TPS material set and its limits are external.

  appendix     "This single-point value is +12.4% relative to the 14.36 W/cm2
                flight measurement and +5.8% relative to Rapisarda's ...
                peak of 15.26 W/cm2"
                -> both comparison values are external.

  The six paragraphs NOT changed report this work's own results, which cannot
  be cited to anything external, or merely point at figures by \ref.

THIRD COPY OF THE SAME META-NARRATION
----------------------------------------------------------------------------
Chapter 3 and Chapter 4 both carried a paragraph explaining the correlation
constant and nose radius. Appendix C carried a third copy of it, still reading
"An earlier revision of this appendix reported 12.20 W/cm2 ...". Narrating an
appendix's own revision history inside the finished document is not appropriate,
and it is the third place the same paragraph appeared. The appendix copy is
rewritten to state provenance, matching the other two.

CITATION
  Plimpton & Gallis, SPARTA, Journal of Computational Physics, 2014
  Lu et al., DeepXDE, SIAM Review, 2021
  Olds et al., IRVE-3 Post-Flight Reconstruction, AIAA Paper 1514242
  Rapisarda, TU Delft MSc Thesis, 2023
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent

EDITS = [
    # ---- chapter 1: the three named external tools -----------------------
    ("chapter_01_introduction.tex",
     "high-fidelity DSMC rarefied gas dynamics (SPARTA), Physics-Informed Neural "
     "Network refinement (DeepXDE), and surrogate-assisted genetic algorithm "
     "optimization",
     "high-fidelity DSMC rarefied gas dynamics~\\cite{plimpton2014sparta}, "
     "Physics-Informed Neural Network refinement~\\cite{lu2021deepxde}, and "
     "surrogate-assisted genetic algorithm optimization"),
    # ---- chapter 3: SPARTA particle tracking -----------------------------
    ("chapter_03_methodology.tex",
     "SPARTA tracks millions of simulated particles through three fundamental "
     "processes:",
     "SPARTA~\\cite{plimpton2014sparta} tracks millions of simulated particles "
     "through three fundamental processes:"),
    # ---- chapter 3: the IRVE-3-derived reference values ------------------
    ("chapter_03_methodology.tex",
     "They are loaded at run time from the IRVE-3 validation run so that the "
     "surrogate is anchored to the measured vehicle",
     "They are loaded at run time from the IRVE-3 validation run "
     "~\\cite{old2013irve3postflight,dillman2014irve3flight} so that the surrogate "
     "is anchored to the measured vehicle"),
    # ---- chapter 4: the 16.14 figure and Rapisarda's 15.26 ---------------
    ("chapter_04_results.tex",
     "it is the same class of quantity as Rapisarda's trajectory-integrated SG "
     "value of 15.26~W/cm\\textsuperscript{2}",
     "it is the same class of quantity as Rapisarda's trajectory-integrated SG "
     "value of 15.26~W/cm\\textsuperscript{2}~\\cite{rapisarda2023mdao}"),
    # ---- chapter 4: the IRVE-3 TPS layup and its limits ------------------
    ("chapter_04_results.tex",
     "the IRVE-3 flexible-TPS structural limit of 523.15\\,K by 432.5\\,K",
     "the IRVE-3 flexible-TPS structural limit of 523.15\\,K by 432.5\\,K "
     "~\\cite{old2013irve3postflight}"),
    ("chapter_04_results.tex",
     "one 0.15\\,mm aluminized Kapton/Kevlar gas barrier, totalling 6.35\\,mm",
     "one 0.15\\,mm aluminized Kapton/Kevlar gas barrier~\\cite{guidotti2023efesto2materials}, "
     "totalling 6.35\\,mm"),
    # ---- appendix: the two comparison values -----------------------------
    ("appendix.tex",
     "relative to the $14.36$\\,W/cm$^2$ flight measurement and $+5.8\\%$ relative "
     "to Rapisarda's trajectory-integrated peak of $15.26$\\,W/cm$^2$;",
     "relative to the $14.36$\\,W/cm$^2$ flight "
     "measurement~\\cite{old2013irve3postflight} and $+5.8\\%$ relative to "
     "Rapisarda's trajectory-integrated peak of $15.26$\\,W/cm$^2$"
     "~\\cite{rapisarda2023mdao};"),
    # ---- appendix: third copy of the meta-narration ----------------------
    ("appendix.tex",
     "An earlier revision of this appendix reported $12.20$\\,W/cm$^2$ from the "
     "superseded coefficient $C_{SG} = 1.7415 \\times 10^{-4}$ and nose radius "
     "$R_N = 0.55$\\,m evaluated at a hardcoded $V_\\infty = 2700$\\,m/s; both "
     "constants have since been corrected to the values used here",
     "A value of $12.20$\\,W/cm$^2$ appears in the engine's own comments; it "
     "results from the engine default coefficient $C_{SG} = 1.7415 \\times "
     "10^{-4}$ and nose radius $R_N = 0.55$\\,m evaluated at a hardcoded "
     "$V_\\infty = 2700$\\,m/s rather than at the run condition, and is superseded "
     "by the values used here"),
]


def main() -> int:
    rc = 0
    for fname, old, new in EDITS:
        p = TH / fname
        t = p.read_text(encoding="utf-8")
        n = t.count(old)
        if n != 1:
            print(f"  !! {fname}: matched {n}x {old[:58]!r}")
            rc = 1
            continue
        p.write_text(t.replace(old, new, 1), encoding="utf-8")
        print(f"  ok  {fname}: {old[:56]!r}")

    txt = "".join((TH / f).read_text(encoding="utf-8") for f in (
        "chapter_01_introduction.tex", "chapter_02_literature_review.tex",
        "chapter_03_methodology.tex", "chapter_04_results.tex",
        "chapter_05_conclusion.tex", "appendix.tex"))
    cites = {k.strip() for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", txt)
             for k in m.group(1).split(",") if k.strip()}
    bib = (TH / "ref.bib").read_text(encoding="utf-8")
    keys = {m.group(1) for m in re.finditer(r"^@[A-Za-z]+\s*\{\s*([^,]+?)\s*,", bib, re.M)}
    print(f"  unresolved citations: {sorted(cites - keys) or 'none'}")
    print(f"  entries not cited:   {sorted(keys - cites) or 'none'}")
    if cites - keys or keys - cites:
        rc = 1
    # no remaining copy of the meta-narration
    live = []
    for f in ("chapter_03_methodology.tex", "chapter_04_results.tex", "appendix.tex"):
        for i, ln in enumerate((TH / f).read_text(encoding="utf-8").split("\n"), 1):
            if re.search(r"(?<!\\)%", ln):
                continue
            if re.search(r"earlier revision|corrected during the course", ln, re.I):
                live.append((f, i))
    print(f"  meta-narration remaining in live text: {live or 'none'}")
    if live:
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())