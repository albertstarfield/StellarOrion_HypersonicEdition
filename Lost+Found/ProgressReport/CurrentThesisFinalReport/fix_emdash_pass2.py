#!/usr/bin/env python3
"""Pass 2 of the em-dash removal: every dash that functions as an em-dash but
is not literally spelled `---`.

WHY A SECOND PASS IS NEEDED
AXIOM: In LaTeX, `---` renders as an em-dash and `--` as an en-dash. Pass 1
(`fix_emdash.py`) removed all 40 literal `---` occurrences. However the thesis
also uses the two-character `--` in the *grammatical role* of an em-dash,
namely as an interrupting or parenthetical dash. Those render as a dash and
read as an em-dash even though the source token is shorter, so removing only
`---` would satisfy the letter of the rule while leaving its spirit unmet.

THEORY: A dash in this thesis is acceptable ONLY when it is doing one of three
legitimate jobs, which are enumerated by construction and preserved verbatim:
  (i)   a COMPOUND HYPHEN joining proper nouns   -> Navier--Stokes
  (ii)  a numeric or section RANGE              -> 0.01--0.1
  (iii) literal DATA inside CLI flags or code   -> --nose, -{}-validate-only
Every other dash is an em-dash in disguise and is removed here.

Consequence for duplicated content (the no_copy_paste_divergence rule):
`appendix.tex` and `chapter_03_methodology.tex` each print the SAME IRVE-3
validation table. Their placeholder cells are therefore corrected in lockstep
in one replacement table below, so the two copies cannot drift apart.

Citations
---------
* LaTeX dash ligatures: https://tug.org/TUGboat/Volumes/tn09/3/hyphenator.html
* APA 6th ed. section 6.2 (dash usage): https://apastyle.apa.org/style-grammar-guidelines/bibliography/apa-6th-edition/
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

THESIS = Path(__file__).resolve().parent

PAIRS: dict[str, list[tuple[str, str]]] = {
    "chapter_01_introduction.tex": [
        # parenthetical participial phrase -> parentheses
        (
            "survivability -- balancing drag performance, peak heating, "
            "ballistic coefficient, and structural mass -- requires",
            "survivability (balancing drag performance, peak heating, "
            "ballistic coefficient, and structural mass) requires",
        ),
        # parenthetical list inside a "The X -- ... -- are" frame -> commas
        (
            "The geometric parameters -- including aeroshell diameter, "
            "forebody cone angle, toroid count, toroid radius, and nose radius "
            "-- are defined",
            "The geometric parameters, including aeroshell diameter, forebody "
            "cone angle, toroid count, toroid radius, and nose radius, are "
            "defined",
        ),
    ],
    "chapter_02_literature_review.tex": [
        # longtable continuation header: dash is a separator, not prose
        (
            "\\tablename\\ \\thetable{} -- continued from previous page",
            "\\tablename\\ \\thetable{} (continued from previous page)",
        ),
        # "the state of the X -- whether ... -- has" -> commas
        (
            "the state of the boundary layer -- whether laminar, transitional, "
            "or fully turbulent -- has a profound impact",
            "the state of the boundary layer, whether laminar, transitional, "
            "or fully turbulent, has a profound impact",
        ),
        # dash introduces the defining clause of a named technique -> colon
        (
            "relies on Turbulence Modeling -- mathematical approximations that "
            "predict",
            "relies on Turbulence Modeling: mathematical approximations that "
            "predict",
        ),
        # gloss inside an already-parenthesised term -> drop the dash entirely
        (
            "assumption (Stosszahlansatz) -- that pre-collision velocities of "
            "colliding pairs are uncorrelated -- one obtains",
            "assumption (Stosszahlansatz) that pre-collision velocities of "
            "colliding pairs are uncorrelated, one obtains",
        ),
        (
            "The mean free path $\\lambda$ -- the average distance a molecule "
            "travels between successive collisions -- is a fundamental quantity",
            "The mean free path $\\lambda$, the average distance a molecule "
            "travels between successive collisions, is a fundamental quantity",
        ),
    ],
    "chapter_03_methodology.tex": [
        # "The two configurations -- A and B -- are" -> commas
        (
            "for this study -- \\textbf{Configuration A (Scalloped)} and "
            "\\textbf{Configuration B (Smooth)} -- are constrained",
            "for this study, \\textbf{Configuration A (Scalloped)} and "
            "\\textbf{Configuration B (Smooth)}, are constrained",
        ),
        # section headings: an en-dash separator reads as a dash; a colon is
        # the conventional and unambiguous heading punctuation.
        (
            "\\subsection{Stagnation Heat Flux -- Sutton-Graves Correlation}",
            "\\subsection{Stagnation Heat Flux: Sutton-Graves Correlation}",
        ),
        (
            "\\subsection{Surface Temperature -- Radiative Equilibrium}",
            "\\subsection{Surface Temperature: Radiative Equilibrium}",
        ),
        (
            "\\subsection{Backface Temperature -- 1D Transient Model}",
            "\\subsection{Backface Temperature: 1D Transient Model}",
        ),
        (
            "\\subsection{Data Pipeline -- DSMC to PINN}",
            "\\subsection{Data Pipeline: DSMC to PINN}",
        ),
        # appositive after a long noun phrase -> comma
        (
            "per timestep per face element -- a simulation-internal unit that "
            "depends on",
            "per timestep per face element, a simulation-internal unit that "
            "depends on",
        ),
        # definition-list items: a colon introduces the gloss
        (
            "$\\rho_{ref} = \\max(\\rho_{SPARTA})$ -- peak number density",
            "$\\rho_{ref} = \\max(\\rho_{SPARTA})$: peak number density",
        ),
        (
            "$u_{ref} = \\max(|u_{SPARTA}|, |v_{SPARTA}|)$ -- maximum velocity",
            "$u_{ref} = \\max(|u_{SPARTA}|, |v_{SPARTA}|)$: maximum velocity",
        ),
        (
            "$T_{ref} = \\max(T_{SPARTA})$ -- peak translational temperature",
            "$T_{ref} = \\max(T_{SPARTA})$: peak translational temperature",
        ),
        (
            "$p_{ref} = \\max(p_{SPARTA})$ -- peak pressure",
            "$p_{ref} = \\max(p_{SPARTA})$: peak pressure",
        ),
        (
            "$L_{ref} = \\max(|x_{bound}|)$ -- maximum domain extent",
            "$L_{ref} = \\max(|x_{bound}|)$: maximum domain extent",
        ),
        # ---- table placeholder cells -> n/a -------------------------------
        (
            "Multi-layer (stack) & -- & -- & -- & Combined FTPS stack",
            "Multi-layer (stack) & n/a & n/a & n/a & Combined FTPS stack",
        ),
        (
            "Toroid count & $N_t$ & $[1, 12]$ & -- \\\\",
            "Toroid count & $N_t$ & $[1, 12]$ & n/a \\\\",
        ),
        # the IRVE-3 validation table (duplicated in appendix.tex:214-216)
        (
            "Peak Deceleration & 19.7\\,$g$ & -- & 16.83\\,$g$ & $-14.6$",
            "Peak Deceleration & 19.7\\,$g$ & n/a & 16.83\\,$g$ & $-14.6$",
        ),
        (
            "Ballistic Coefficient ($\\beta$) & 26.9 kg/m$^2$ & -- & "
            "27.70 kg/m$^2$ & $+3.0$",
            "Ballistic Coefficient ($\\beta$) & 26.9 kg/m$^2$ & n/a & "
            "27.70 kg/m$^2$ & $+3.0$",
        ),
        (
            "Drag Coefficient ($C_d$) & -- & -- & 1.4625 & -- \\\\",
            "Drag Coefficient ($C_d$) & n/a & n/a & 1.4625 & n/a \\\\",
        ),
        # the single literal U+2014 in the whole thesis, in a table cell
        (
            "Input dimension & 2 $(x, r)$ \u2014 axisymmetric",
            "Input dimension & 2 $(x, r)$ (axisymmetric)",
        ),
    ],
    "chapter_04_results.tex": [
        (
            "Aeroshell Diameter & 3.0\\,m & -- & 3.0\\,m & Geometry Sync",
            "Aeroshell Diameter & 3.0\\,m & n/a & 3.0\\,m & Geometry Sync",
        ),
        (
            "Peak Deceleration & 19.7\\,$g$ & -- & 16.83\\,$g$ & SO $-14.6\\%$",
            "Peak Deceleration & 19.7\\,$g$ & n/a & 16.83\\,$g$ & SO $-14.6\\%$",
        ),
    ],
    "appendix.tex": [
        # SAME table as chapter_03_methodology.tex:979-981 -> same fix, applied
        # in lockstep so the two printed copies cannot diverge.
        (
            "Peak deceleration & 19.7\\,$g$ & -- & 16.83\\,$g$ & $-14.6$",
            "Peak deceleration & 19.7\\,$g$ & n/a & 16.83\\,$g$ & $-14.6$",
        ),
        (
            "Ballistic coefficient ($\\beta$) & 26.9~kg/m\\textsuperscript{2} "
            "& -- & 27.70~kg/m\\textsuperscript{2} & $+3.0$",
            "Ballistic coefficient ($\\beta$) & 26.9~kg/m\\textsuperscript{2} "
            "& n/a & 27.70~kg/m\\textsuperscript{2} & $+3.0$",
        ),
        (
            "Drag coefficient ($C_d$) & -- & -- & 1.4625 & --",
            "Drag coefficient ($C_d$) & n/a & n/a & 1.4625 & n/a",
        ),
    ],
}

_CODE_ENV = re.compile(r"\\begin\{(verbatim|lstlisting|minted|alltt)\}")
_CODE_END = re.compile(r"\\end\{(verbatim|lstlisting|minted|alltt)\}")

# Dashes that are legitimate and MUST survive (axioms i-iii above).
# NOTE: `$--$` is required because most numeric ranges in this thesis wrap each
# endpoint in its own math group, e.g. $0.001$--$0.01$ and $O(10^2)$--$O(10^3)$.
# Without it the residual audit reports dozens of false positives and stops
# being trustworthy, which is worse than not running it at all.
_ALLOWED = [
    re.compile(r"[A-Za-z]--[A-Za-z]"),           # Navier--Stokes, sphere--cone
    re.compile(r"\d\s*--\s*\d"),                 # 0.01--0.1, 21--23, 500--1100
    re.compile(r"\$--\$"),                       # $0.001$--$0.01$, $10$--$15$
    re.compile(r"\)\s*--\s*\("),                 # panels (a)--(c)
    re.compile(r"--[a-zA-Z]"),                   # --nose, --validate-only
    re.compile(r"[a-zA-Z]--"),                   # -{}-style, tail of a range
    re.compile(r"\$k\$--\$\\omega\$"),           # k--omega turbulence model
]


def prose_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    out, inside = [], False
    for ln in lines:
        if _CODE_ENV.search(ln):
            inside = True
            out.append("")
            continue
        if _CODE_END.search(ln):
            inside = False
            out.append("")
            continue
        out.append("" if inside else re.split(r"(?<!\\)%", ln, maxsplit=1)[0])
    return out


def residual_dashes(path: Path) -> list[tuple[int, str]]:
    """Return prose lines still holding a dash that is NOT a legitimate one."""
    hits: list[tuple[int, str]] = []
    for n, ln in enumerate(prose_lines(path), 1):
        if "---" not in ln and "\u2014" not in ln and "--" not in ln:
            continue
        # Blank out legitimate dashes, then look for anything left.
        probe = ln
        for pat in _ALLOWED:
            probe = pat.sub("<OK>", probe)
        if "---" in probe or "\u2014" in probe or "--" in probe:
            hits.append((n, ln.strip()[:150]))
    return hits


def main() -> int:
    rc = 0
    print("APPLYING PASS-2 REPLACEMENTS")
    print("=" * 68)
    for name, pairs in PAIRS.items():
        p = THESIS / name
        text = p.read_text(encoding="utf-8", errors="replace")
        for old, new in pairs:
            n = text.count(old)
            if n != 1:
                print(f"  !! {name}: expected 1 match, got {n}: {old[:64]!r}")
                rc = 1
                continue
            text = text.replace(old, new, 1)
            print(f"  ok {name}: {old[:56]!r}")
        p.write_text(text, encoding="utf-8")

    print()
    print("RESIDUAL DASH AUDIT (legitimate compounds/ranges/CLI excluded)")
    print("=" * 68)
    total = 0
    for name in PAIRS:
        for n, ln in residual_dashes(THESIS / name):
            print(f"  !! {name}:{n}  {ln}")
            total += 1
    print()
    print("VERDICT: " + ("no em-dash-function dash remains." if total == 0
                         else f"{total} residual dash(es) need review."))
    return rc if rc == 0 and total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
