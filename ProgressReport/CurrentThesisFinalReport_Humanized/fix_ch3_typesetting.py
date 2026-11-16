#!/usr/bin/env python3
r"""Fix the moderate typesetting defects the page audit found in Chapter 3.

Each defect below was located by rendering the built PDF to PNG and inspecting
the pages, and each fix is the minimal, content-preserving change that removes
the defect.

D1. ORPHANED EQUATION TAG (was page 114, Eq. 3.15)
    The worked Sutton-Graves substitution was a single very long display
    equation:
        q_stag = 1.7415e-4 x sqrt(7.851e-4/1.5) x (3378)^3
                 ~ 1.614e5 W/m^2 = 16.14 W/cm^2
    It reached the right text edge with zero slack, so the "(3.15)" tag was
    pushed onto a line of its own below the equation. Splitting the evaluation
    across the two lines it naturally occupies, using the `split` environment
    already used elsewhere in this chapter for the same purpose, restores the
    tag to the vertical centre of the block. No value changes.

D2. STRAY FRAME AROUND Eq. (3.14) (was page 113)
    The general Sutton-Graves relation is the only display equation in the
    chapter wrapped in \boxed. Nothing else in the document is framed, so it
    reads as an inconsistency rather than an emphasis. \boxed is removed. The
    equation and its number are unchanged.

D3. TABLE 3.9 FIRST COLUMN TOO NARROW (was page 122)
    The "Axiom" column was p{0.15\textwidth}. The entries are two-word phrases
    such as "A3: Sutherland viscosity" and "A7: Statistical stationarity", and
    at 0.15 of the measure the column broke them across three lines each:
        "A3: Suther-" / "land viscos-" / "ity"
    The second column carries long prose that is set ragged and so has slack,
    so 0.15 -> 0.21 and 0.55 -> 0.49 keeps the total width identical and is
    width-neutral for the whole table.

CITATION
--------
* Equation tag placement and the `split` environment:
  amsmath, https://ctan.org/pkg/amsmath
* Ragged-right p-columns and \RaggedRight: ragged2e,
  https://ctan.org/pkg/ragged2e
"""

from __future__ import annotations

from pathlib import Path

CH3 = Path(__file__).resolve().parent / "chapter_03_methodology.tex"

EDITS: list[tuple[str, str, str]] = [
    # ---- D2: remove the one-off frame around the general relation --------
    (
        r"    \boxed{\dot{q}_{stag} = C_{SG} \sqrt{\frac{\rho_{\infty}}{R_N}} \cdot V_{\infty}^3}",
        r"    \dot{q}_{stag} = C_{SG} \sqrt{\frac{\rho_{\infty}}{R_N}} \cdot V_{\infty}^3",
        "D2 unbox Eq. (3.14)",
    ),
    # ---- D1: split the worked substitution so the tag stays attached -----
    (
        r"    \dot{q}_{stag} = 1.83 \times 10^{-4} \sqrt{\frac{7.851 \times 10^{-4}}{1.5}} \times 3378^3 \approx 1.614 \times 10^{5} \ \text{W/m}^2 = 16.14 \ \text{W/cm}^2",
        r"""    \begin{split}
        \dot{q}_{stag}
          &= 1.83 \times 10^{-4} \sqrt{\frac{7.851 \times 10^{-4}}{1.5}} \times 3378^3 \\
          &\approx 1.614 \times 10^{5} \ \text{W/m}^2 \\
          &= 16.14 \ \text{W/cm}^2
    \end{split}""",
        "D1 split the SG substitution",
    ),
    # ---- D3: rebalance Table 3.9 columns, total width unchanged ---------
    (
        r"    \begin{tabular}{|>{\RaggedRight\arraybackslash}p{0.15\textwidth}|>{\RaggedRight\arraybackslash}p{0.55\textwidth}|>{\RaggedRight\arraybackslash}p{0.2\textwidth}|}",
        r"    \begin{tabular}{|>{\RaggedRight\arraybackslash}p{0.21\textwidth}|>{\RaggedRight\arraybackslash}p{0.49\textwidth}|>{\RaggedRight\arraybackslash}p{0.2\textwidth}|}",
        "D3 widen Table 3.9 column 1",
    ),
]


def main() -> int:
    text = CH3.read_text(encoding="utf-8")
    rc = 0
    for old, new, desc in EDITS:
        n = text.count(old)
        if n != 1:
            print(f"  !! {desc}: expected 1 match, found {n}")
            rc = 1
            continue
        text = text.replace(old, new, 1)
        print(f"  ok  {desc}")
    if rc == 0:
        CH3.write_text(text, encoding="utf-8")
        print("\nchapter_03_methodology.tex: 3 typesetting defects fixed.")
    else:
        print("\nNOT WRITTEN.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
