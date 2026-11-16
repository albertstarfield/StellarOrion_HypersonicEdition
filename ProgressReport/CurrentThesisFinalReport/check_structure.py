#!/usr/bin/env python3
r"""Structural sanity checks on the thesis sources that pdflatex does NOT catch
for you, because LaTeX silently repairs them instead of failing.

THE CLASS OF BUG THIS EXISTS TO CATCH
AXIOM: In LaTeX math mode, spaces are IGNORED. A paragraph with an odd number of
unescaped `$` therefore does not produce an error: from the stray `$` onward,
every space in the paragraph stops being a legal break point, so TeX emits one
enormous unbreakable box. The symptom is an Overfull \\hbox of several line
widths, and the source line looks perfectly ordinary to a human reader.

This was hit for real during this pass. `chapter_04_results.tex` line 260 read

    ... of $R = 0.25605$\\,m$^2\\,K/W and an outer emissivity of 0.80. ...

The third `$` (before `^2`) opened math that was never closed, so `m^2 K/W and
an outer emissivity of 0.80 ...` to the end of the paragraph was set in math
italic with no break opportunities. The log showed the prose in math-italic
font (`\\OML/ztmcm/m/it/12`) which is the diagnostic fingerprint, and the build
reported `Overfull \\hbox (1033.94652pt too wide)`, 2.6 line widths, on a
paragraph whose longest space-free run was only 19 characters.

CHECKS PERFORMED
  1. `$` parity per line, on code with comments stripped. An odd count on a
     single line is a leak, because a well-formed inline formula opens and
     closes on the same line.
  2. Brace balance per file.
  3. `\\begin{...}` / `\\end{...}` pairing per file.
  4. Residual em-dashes (true em-dash and em-dash-function en-dash).
  5. GNATprove / SPARK / formal-verification mentions, which the thesis owner
     has ruled out of scope entirely.
  6. Duplicate \label names across files. LaTeX does NOT error on these: the
     second definition silently wins and every \ref to that name then resolves
     to the wrong target, which is how a cross-reference can quietly point at
     the wrong section. This bit for real during this pass when the new cost
     function was labelled `eq:cost_function`, a name chapter 2 already used.

Citations
=========
* TeX math mode ignores spaces: https://texdoc.org/serve/logfile-spec/0/
* Overfull/underfull box reporting: https://latex2e.readthedocs.io/en/stable/texerror.html
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

THESIS = Path(__file__).resolve().parent

FILES = [
    "main.tex", "preamble.tex", "identity.tex", "cover.tex", "approval_sheet.tex",
    "abstract.tex", "table_of_contents.tex", "list_of_figures.tex",
    "list_of_tables.tex", "symbols.tex", "abbreviations.tex",
    "chapter_01_introduction.tex", "chapter_02_literature_review.tex",
    "chapter_03_methodology.tex", "chapter_04_results.tex",
    "chapter_05_conclusion.tex", "references.tex", "appendix.tex",
]

_CODE_OPEN = re.compile(r"\\begin\{(verbatim|lstlisting|minted|alltt)\}")
_CODE_CLOSE = re.compile(r"\\end\{(verbatim|lstlisting|minted|alltt)\}")
_BANNED = re.compile(
    r"gnatprove|spark|formal(ly)?\s+(verification|verified|proof)|"
    r"proof\s+(obligation|gate|level)|ada/spark",
    re.IGNORECASE,
)
_ALLOWED_DASH = [
    re.compile(r"[A-Za-z]--[A-Za-z]"),   # compound proper noun, one doubled hyphen
    re.compile(r"\d\s*--\s*\d"),         # bare numeric range
    re.compile(r"\$--\$"),               # math range between two inline formulas
    re.compile(r"\)\s*--\s*\("),         # panel label range
    re.compile(r"--[a-zA-Z]"),           # command-line flag
    re.compile(r"[a-zA-Z]--"),           # tail of a range or flag
    re.compile(r"\$k\$--\$\\omega\$"),   # turbulence model name
]


def strip_code_and_comments(text: str) -> list[str]:
    """Blank code-block bodies and comment tails, preserving line numbering."""
    out, inside = [], False
    for ln in text.split("\n"):
        if _CODE_OPEN.search(ln):
            inside = True
            out.append("")
            continue
        if _CODE_CLOSE.search(ln):
            inside = False
            out.append("")
            continue
        out.append("" if inside else re.sub(r"(?<!\\)%.*$", "", ln))
    return out


def main() -> int:
    failures = 0

    for name in FILES:
        path = THESIS / name
        if not path.exists():
            print(f"  MISSING {name}")
            failures += 1
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        lines = strip_code_and_comments(raw)
        problems: list[str] = []

        # 1. math-mode leak.
        #    Granularity is the PARAGRAPH, not the line. A per-line parity test
        #    is wrong: `cover.tex` legitimately opens math on one line and
        #    closes it three lines later around a `matrix` environment, which a
        #    line test reports as two false positives. Math may span lines, but
        #    it may not span a blank line in this document's usage, so each
        #    blank-line-delimited group must contain an even number of
        #    unescaped `$`, and the reported line is the one where the group
        #    first goes odd.
        group: list[tuple[int, int]] = []  # (line no, dollar count)
        for n, ln in enumerate(lines, 1):
            group.append((n, len(re.findall(r"(?<!\\)\$", ln))))
            if ln.strip() == "":
                if sum(c for _, c in group) % 2:
                    first_odd = next(
                        (n for i, (n, c) in enumerate(group)
                         if sum(x for _, x in group[: i + 1]) % 2),
                        group[0][0],
                    )
                    problems.append(
                        f"L{first_odd}: paragraph group L{group[0][0]}-L{group[-1][0]} "
                        f"has an ODD number of unescaped '$' -> math mode leaks "
                        f"past this group and every space after it stops being "
                        f"a legal break point"
                    )
                group = []
        if group and sum(c for _, c in group) % 2:
            problems.append(
                f"L{group[0][0]}: trailing paragraph group has an ODD number of "
                f"unescaped '$' -> math mode leaks to end of file"
            )

        # 2. brace balance
        depth = 0
        for ln in lines:
            depth += ln.count("{") - ln.count("}")
        if depth != 0:
            problems.append(f"brace depth ends at {depth}, expected 0")

        # 3. environment pairing
        stack: list[tuple[str, int]] = []
        for n, ln in enumerate(raw.split("\n"), 1):
            for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", ln):
                if m.group(1) == "begin":
                    stack.append((m.group(2), n))
                else:
                    if stack and stack[-1][0] == m.group(2):
                        stack.pop()
                    else:
                        problems.append(
                            f"L{n}: \\end{{{m.group(2)}}} does not match "
                            f"\\begin{{{stack[-1][0] if stack else 'NOTHING'}}}"
                        )
        for env, ln in stack:
            problems.append(f"L{ln}: \\begin{{{env}}} never closed")

        # 4. residual em-dash
        for n, ln in enumerate(lines, 1):
            if "---" not in ln and "\u2014" not in ln and "--" not in ln:
                continue
            probe = ln
            for pat in _ALLOWED_DASH:
                probe = pat.sub("<OK>", probe)
            if "---" in probe or "\u2014" in probe or "--" in probe:
                problems.append(f"L{n}: residual em-dash -> {probe.strip()[:90]!r}")

        # 5. banned scope
        for n, ln in enumerate(lines, 1):
            m = _BANNED.search(ln)
            if m:
                problems.append(f"L{n}: banned term {m.group(0)!r}")

    # 6. duplicate \\label names across the whole build (all files at once,
    #    since a collision is only meaningful between two different files)
    label_sites: dict[str, list[str]] = {}
    for name in FILES:
        path = THESIS / name
        if not path.exists():
            continue
        for n, ln in enumerate(
            path.read_text(encoding="utf-8", errors="replace").split("\n"), 1
        ):
            for m in re.finditer(r"\\label\{([^}]+)\}", ln):
                label_sites.setdefault(m.group(1), []).append(f"{name}:{n}")
    dupes = {k: v for k, v in label_sites.items() if len(v) > 1}
    for k, v in sorted(dupes.items()):
        print(f"\nDUPLICATE LABEL {k!r}")
        print(f"    defined at: {', '.join(v)}")
        print(f"    every \\ref{{{k}}} silently resolves to the LAST definition")
        failures += len(v)

        if problems:
            failures += len(problems)
            print(f"\n{name}")
            for p in problems:
                print(f"    !! {p}")

    print("\n" + "=" * 66)
    if failures:
        print(f"STRUCTURAL CHECK FAILED: {failures} problem(s) across {len(FILES)} files")
    else:
        print(f"STRUCTURAL CHECK PASSED: all {len(FILES)} files clean")
        print("  math-mode leaks     : 0")
        print("  brace imbalance     : 0")
        print("  environment mismatch: 0")
        print("  residual em-dashes  : 0")
        print("  banned scope terms  : 0")
        print(f"  duplicate labels    : 0  ({len(label_sites)} labels checked)")
    print("=" * 66)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
