#!/usr/bin/env python3
"""Fix stale hard-coded section cross-references and one wrong DoE sample count
in Chapter 3.

WHY THIS IS A DEFECT, NOT A STYLE NICKEL
AXIOM: A hard-coded section number is a frozen copy of a value LaTeX computes.
Chapter 3 already contains five such frozen copies, and four of them point at
sections with no relationship to the sentence citing them. Verified against the
rendered `main.toc` of this document:

  thesis text                          claims        section 3.4.3/3.5.1/3.4/3.3.5
  -----------------------------------  -----------  --------------------------------
  "two-stage PINN protocol (Sec 3.4)"  PINN is 3.7  3.4 = DSMC Simulation Framework
  "Face-Centered CCD (Sec 3.5.1)"      CCD is 3.8   3.5.1 = Surface Computes
  "GA operators (Sec 3.4.3)"           GA is 3.8    3.4.3 = SPARTA Solver Config
  "Pragmatic Choice (Sec 3.3.5)"       --            3.3.5 DOES NOT EXIST (3.3 has 4)
  "ballistic coefficient (Sec 3.2.4)"  beta is 3.5.2 3.2 has no subsections at all

THEORY: Replacing a frozen number with `\\ref` to a `\\label` makes the
reference self-maintaining, so renumbering can never silently invalidate it.
Four labels are therefore ADDED where the target had none.

SECOND DEFECT, FOUND WHILE DOING THE ABOVE
The same subsection claims the Face-Centered CCD was run with d = 4 design
variables (Diameter, Angle, Nose Radius, Toroid Radius), giving
N = 2^4 + 2(4) + 1 = 25 points. The executed screen recorded in
`stellarorion_program_proc/src/python/hiad_optimization_results.json` is
15 points over THREE factors:
    ccd_samples: 8 labels beginning "factorial", 6 beginning "axial", 1 "center"
    factor keys present in every row: R_N, r_tor, half_cone_deg  (no Diameter)
    8 + 6 + 1 = 15 = 2^3 + 2(3) + 1
Chapter 4 already reports 15 points, so Chapter 3 contradicted Chapter 4.
Both sites are corrected to d = 3 and N = 15.

Citations
---------
* Face-Centered CCD construction, N = 2^d + 2d + 1: Montgomery, Design and
  Analysis of Experiments, 9th ed., Wiley 2017, Ch. 5
  (doi:10.1002/9781119482086.refs).
"""

from __future__ import annotations

from pathlib import Path

CH3 = Path(__file__).resolve().parent / "chapter_03_methodology.tex"

# (old, new, expected_count)
EDITS: list[tuple[str, str, int]] = [
    # ---- add the four labels the corrected references need -----------------
    (
        "\\subsection{Ballistic Coefficient (\\texorpdfstring{$\\beta$}{beta})}",
        "\\subsection{Ballistic Coefficient (\\texorpdfstring{$\\beta$}{beta})}\n"
        "\\label{sec:ballistic_coefficient}",
        1,
    ),
    (
        "\\subsection{Two-Stage Training Protocol}",
        "\\subsection{Two-Stage Training Protocol}\n"
        "\\label{sec:pinn_two_stage}",
        1,
    ),
    (
        "\\subsection{Latin Hypercube Sampling (LHS)}",
        "\\subsection{Design of Experiments: LHS and CCD}\n"
        "\\label{sec:doe_sampling}",
        1,
    ),
    (
        "\\subsection{Genetic Algorithm Optimization}",
        "\\subsection{Genetic Algorithm Optimization}\n"
        "\\label{sec:ga_operators}",
        1,
    ),
    # ---- replace the five frozen numbers with live references --------------
    (
        "even at $Kn > 0.01$. & Sec.~3.3.5 (Pragmatic Choice) \\\\",
        "even at $Kn > 0.01$. & Sec.~\\ref{sec:pinn_pragmatic} \\\\",
        1,
    ),
    (
        "computed from the design parameters (see Sec.~3.2.4)",
        "computed from the design parameters "
        "(see Sec.~\\ref{sec:ballistic_coefficient})",
        1,
    ),
    (
        "operate on $J_{constrained}$ as described in Sec.~3.4.3",
        "operate on $J_{constrained}$ as described in "
        "Sec.~\\ref{sec:ga_operators}",
        1,
    ),
    (
        "$N = 25$ sample points generated via Face-Centered CCD (Sec.~3.5.1) "
        "across the design space.",
        "$N = 15$ sample points generated via Face-Centered CCD "
        "(Sec.~\\ref{sec:doe_sampling}) across the design space.",
        1,
    ),
    (
        "DSMC outputs are refined using the two-stage PINN protocol (Sec.~3.4).",
        "DSMC outputs are refined using the two-stage PINN protocol "
        "(Sec.~\\ref{sec:pinn_two_stage}).",
        1,
    ),
    # ---- correct the DoE sample count to the executed campaign ------------
    (
        "For a $d$-dimensional parameter space, the CCD constructs "
        "$N = 2^d + 2d + 1$ sample points: $2^d$ factorial (corner) points at "
        "$\\pm 1$ levels, $2d$ axial (star) points at $\\pm \\alpha$ along each "
        "axis, and $1$ center point replicated at the origin. For the $d = 4$ "
        "design variables (Diameter, Angle, Nose Radius, Toroid Radius), this "
        "yields $N = 16 + 8 + 1 = 25$ sample points, which is the minimum "
        "required for a second-order response surface model.",
        "For a $d$-dimensional parameter space, the CCD constructs "
        "$N = 2^d + 2d + 1$ sample points: $2^d$ factorial (corner) points at "
        "$\\pm 1$ levels, $2d$ axial (star) points at $\\pm \\alpha$ along each "
        "axis, and $1$ center point at the origin. The campaign executed in "
        "this work used $d = 3$ design variables (nose radius $R_N$, toroid "
        "radius $r_{tor}$, and half-cone angle $\\theta_c$), which yields "
        "$N = 8 + 6 + 1 = 15$ sample points, the minimum required for a "
        "second-order response surface model in three factors. The recorded "
        "screen comprises eight factorial corner points, six axial star "
        "points, and the single center point, and it is reported separately "
        "from the 70-entry Bayesian Optimization history of "
        "Sec.~\\ref{sec:bo_results}.",
        1,
    ),
]


def main() -> int:
    text = CH3.read_text(encoding="utf-8")
    rc = 0
    for old, new, want in EDITS:
        got = text.count(old)
        if got != want:
            print(f"  !! expected {want} match, found {got}: {old[:66]!r}")
            rc = 1
            continue
        text = text.replace(old, new, want)
        print(f"  ok  {old[:66]!r}")
    if rc == 0:
        CH3.write_text(text, encoding="utf-8")
        print("\nchapter_03_methodology.tex updated.")
    else:
        print("\nNOT WRITTEN (a replacement failed to match).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
