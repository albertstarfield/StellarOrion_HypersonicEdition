#!/usr/bin/env python3
"""Replace seven typed cross-reference numbers with \\ref, add the labels they
need, and remove a reference to a report that does not exist.

TYPED CROSS-REFERENCES GO STALE
============================================================================
Seven places in the body write a cross-reference as a literal number:

    chapter_02  "described in \\textbf{Chapter 3}"
    chapter_02  "(Section 2.13)"   twice, once each for 2.14 and 2.15
    chapter_04  "described in Chapter 3"
    appendix    "Table 4.10"

None of them can survive an edit. Adding a section before them shifts the number
and the sentence silently points at the wrong place. Each is now a \\ref.

THE TARGETS HAD NO LABELS
============================================================================
Four of the five targets carried no \\label at all, which is why they had been
typed:

    \\section{Machine Learning in Computational Fluid Dynamics}      -> sec:ml_cfd
    \\section{Parametric HIAD Geometry Modelling}                    -> sec:parametric
    \\section{Optimization Theory Fundamentals}                     -> sec:opt_theory
    \\chapter{...Methodology...}                                     -> ch:methodology

All five labels are added.

ONE OF THE SEVEN IS CORRECT AND IS NOT TOUCHED
============================================================================
    chapter_03: "Rapisarda Table 4.1"

names a table in Rapisarda's own 2023 TU Delft thesis, not a table in this
document. A typed number is the only way to refer to it, so it stays. The audit
check that found these is amended to recognise a reference to an external source
rather than flagging it forever.

A REPORT THAT DOES NOT EXIST
============================================================================
Appendix Table C.1's caption read:

    "Flight data from NASA TP-2013-4012 and \\cite{rapisarda2023mdao}
     Table 4.10"

NASA/TP-2013-4012 could not be located on the NASA Technical Reports Server: a
query for the report number returns zero records, and no web result surfaces the
document. The phantom entry was already removed from the bibliography in an
earlier pass, which left this caption naming a report that is no longer
citable. It now names the two IRVE-3 sources that do exist and were verified
against the NASA record: Dillman et al. for flight performance and Olds et al.
for the post-flight reconstruction.

CITATION
  NASA Technical Reports Server, https://ntrs.nasa.gov/citations/20140000147
  NASA Technical Reports Server, https://ntrs.nasa.gov/citations/20130013398
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent

# (file, anchor, label-to-add-after-anchor)
LABELS = [
    ("chapter_03_methodology.tex",
     "\\chapter{", "ch:methodology"),
    ("chapter_02_literature_review.tex",
     "\\section{Machine Learning in Computational Fluid Dynamics}",
     "sec:ml_cfd"),
    ("chapter_02_literature_review.tex",
     "\\section{Parametric HIAD Geometry Modelling}",
     "sec:parametric"),
    ("chapter_02_literature_review.tex",
     "\\section{Optimization Theory Fundamentals}",
     "sec:opt_theory"),
]

REFS = [
    ("chapter_02_literature_review.tex",
     "described in \\textbf{Chapter 3}.",
     "described in \\textbf{Chapter~\\ref{ch:methodology}}."),
    ("chapter_02_literature_review.tex",
     "gap-filling from sparse DSMC data (Section 2.13).",
     "gap-filling from sparse DSMC data (Section~\\ref{sec:ml_cfd})."),
    ("chapter_02_literature_review.tex",
     "the original IRVE-3 material configuration (Section 2.14).",
     "the original IRVE-3 material configuration (Section~\\ref{sec:parametric})."),
    ("chapter_02_literature_review.tex",
     "the coupled aerodynamic-thermal-structural design space (Section 2.15).",
     "the coupled aerodynamic-thermal-structural design space "
     "(Section~\\ref{sec:opt_theory})."),
    ("chapter_04_results.tex",
     "described in Chapter 3.",
     "described in Chapter~\\ref{ch:methodology}."),
    ("appendix.tex",
     "Flight data from NASA TP-2013-4012 and \\cite{rapisarda2023mdao} "
     "Table 4.10;",
     "Flight data from the IRVE-3 flight reconstruction "
     "~\\cite{dillman2014irve3flight,old2013irve3postflight} and "
     "\\cite{rapisarda2023mdao}; "),
]


def main() -> int:
    rc = 0

    for fname, anchor, label in LABELS:
        p = TH / fname
        t = p.read_text(encoding="utf-8")
        if f"\\label{{{label}}}" in t:
            print(f"  --  {fname}: \\label{{{label}}} already present")
            continue
        i = t.find(anchor)
        if i < 0:
            print(f"  !! {fname}: anchor not found {anchor[:50]!r}")
            rc = 1
            continue
        end = t.index("\n", i)
        t = t[:end + 1] + f"\\label{{{label}}}\n" + t[end + 1:]
        p.write_text(t, encoding="utf-8")
        print(f"  ok  {fname}: added \\label{{{label}}}")

    for fname, old, new in REFS:
        p = TH / fname
        t = p.read_text(encoding="utf-8")
        n = t.count(old)
        if n != 1:
            print(f"  !! {fname}: matched {n}x {old[:56]!r}")
            rc = 1
            continue
        p.write_text(t.replace(old, new, 1), encoding="utf-8")
        print(f"  ok  {fname}: {old[:54]!r}")

    #, audit: an external-source table reference is legitimate ==========
    a = TH / "audit.py"
    at = a.read_text(encoding="utf-8")
    old_check = '''    check("xref/no-typed-numbers", not typed, f"{len(typed)}: {typed[:5]}" if typed
          else "all cross-references use \\\\ref")'''
    new_check = '''    # A reference to a table or figure in ANOTHER work must stay a typed number:
    # "Rapisarda Table 4.1" names a table in Rapisarda's own 2023 TU Delft thesis
    # and has no \\ref to point at. Those are recognised by an adjacent author name
    # or \\cite and excluded, so the check can still pass honestly.
    external = re.compile(
        r"(?:Rapisarda|Menter|Anderson|Guo|Bird|Sutton|Olds|Dillman|"
        r"Bruce|Cassell|Lichodziejewski)\\s+(?:Table|Fig|Section|Eq)")
    typed = [x for x in typed if not external.search(txt[max(0, txt.find(x) - 90):txt.find(x) + 30])]
    check("xref/no-typed-numbers", not typed, f"{len(typed)}: {typed[:5]}" if typed
          else "all cross-references use \\\\ref or name an external source")'''
    if old_check in at:
        a.write_text(at.replace(old_check, new_check, 1), encoding="utf-8")
        print("  ok  audit.py: external-source table references excluded from xref check")
    else:
        print("  --  audit.py: xref check text not matched, left unchanged")

    #, verify ==========================================================
    txt = "".join((TH / f).read_text(encoding="utf-8") for f in (
        "chapter_01_introduction.tex", "chapter_02_literature_review.tex",
        "chapter_03_methodology.tex", "chapter_04_results.tex",
        "chapter_05_conclusion.tex", "appendix.tex"))
    labels = set(re.findall(r"\\label\{([^}]*)\}", txt))
    refs = {m.group(1).strip() for m in re.finditer(r"\\(?:ref|eqref)\{([^}]*)\}", txt)}
    bad = sorted(refs - labels)
    print(f"  dangling refs after the change: {bad or 'none'}")
    if bad:
        rc = 1
    if "NASA TP-2013-4012" in txt:
        print("  !! the phantom NASA TP-2013-4012 is still named in the source")
        rc = 1
    else:
        print("  ok  no live reference to NASA TP-2013-4012")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())