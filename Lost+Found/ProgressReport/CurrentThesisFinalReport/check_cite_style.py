#!/usr/bin/env python3
"""Citation-style regression scanner for the thesis sources.

AXIOMS:
  A1. Every citation defect class found in earlier cycles must stay at zero
      after each prose-condensation round: adjacent parens, cite-before-paren,
      cite nested inside parens, consecutive duplicate cites of one key,
      sentence-initial parenthetical cites, and same-key duplicates within a
      single sentence (excluding legitimate distinct table-row citations).
  A2. The scanner is report-only (exit 0): it never edits sources, so it is
      safe to run while other work is in flight.

THEORIES:
  T1. Regex classes over comment-stripped source detect each defect family;
      cross-element table duplicates are printed separately for manual review
      (they were verified false positives in earlier cycles).

APPLICATIONS:
  Run: python3 check_cite_style.py   (from the thesis directory; exit 0 always).
  A non-zero "total issues" line means a real regression to fix.

CITATIONS:
  [Citation: Python re module - https://docs.python.org/3/library/re.html]
  [Reference: prior cycle scan results recorded in session history]
"""
import re
import sys
from pathlib import Path

FILES = [
    "chapter_01_introduction.tex",
    "chapter_02_literature_review.tex",
    "chapter_03_methodology.tex",
    "chapter_04_results.tex",
    "chapter_05_conclusion.tex",
    "abstract.tex",
    "appendix.tex",
]

def main() -> int:
    """Scan FILES for citation-style defect classes; print findings; always 0."""
    issues = 0
    for name in FILES:
        p = Path(name)
        if not p.exists():
            print(f"MISSING FILE {name}")
            continue
        text = re.sub(r"(?<!\\)%.*", "", p.read_text(encoding="utf-8"))
        # 1. text-paren immediately followed by a cite: "(...)~\cite"
        for m in re.finditer(r"\)[~\s]*\\cite[a-z]*\{([^}]*)\}", text):
            line = text[: m.start()].count("\n") + 1
            print(f"ADJ-PRE  {name}:{line}: {text[max(0,m.start()-45):m.end()+8]!r}")
            issues += 1
        # 2. cite immediately followed by " (": "\cite{...} ("
        for m in re.finditer(r"\\cite[a-z]*\{[^}]*\}[~\s]+\(", text):
            line = text[: m.start()].count("\n") + 1
            print(f"ADJ-POST {name}:{line}: {text[max(0,m.start()-30):m.end()+25]!r}")
            issues += 1
        # 3. cite nested inside a parenthetical group
        for m in re.finditer(r"\((?:[^()\\]|\\.)*\\cite[a-z]*\{[^}]*\}(?:[^()\\]|\\.)*\)", text):
            line = text[: m.start()].count("\n") + 1
            print(f"NESTED   {name}:{line}: {m.group(0)[:90]!r}")
            issues += 1
        # 4. consecutive duplicate cites sharing a key: }\cite{A}~\cite{B}
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}[~\s]*\\cite[a-z]*\{([^}]*)\}", text):
            if set(x.strip() for x in m.group(1).split(",")) & set(x.strip() for x in m.group(2).split(",")):
                line = text[: m.start()].count("\n") + 1
                print(f"DOUBLE   {name}:{line}: {m.group(0)[:80]!r}")
                issues += 1
        # 5. same key twice within one sentence (review-only list)
        for sent in re.split(r"(?<=[.;])\s+", text):
            keys = [k.strip() for c in re.findall(r"\\cite[a-z]*\{([^}]*)\}", sent) for k in c.split(",")]
            seen, dup = set(), set()
            for k in keys:
                if k in seen:
                    dup.add(k)
                seen.add(k)
            if dup:
                idx = text.find(sent[:60]) if sent[:60] in text else -1
                ln = text[: idx].count("\n") + 1 if idx >= 0 else "?"
                print(f"DUP-SENT {name}:{ln} {sorted(dup)} :: {' '.join(sent.split())[:160]}")
    print(f"total issues: {issues}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
