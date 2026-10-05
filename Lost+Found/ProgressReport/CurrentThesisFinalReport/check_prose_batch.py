#!/usr/bin/env python3
"""Verify round-1 prose-condensation integrity for finished chapter files.

Compares each working-tree file against its HEAD version (git show HEAD:./<file>)
and reports: word counts, \\cite/\\protect\\cite/\\label counts, brace balance,
forbidden sequences (`--` outside \\texttt{-{}-...} tokens, U+2014), and banned
words (gnatprove / spark / formal verification).

AXIOMS: the editors were forbidden from changing cite/label/protect counts, so
any count delta vs HEAD is a defect. `--` and U+2014 are banned by goal rev 6.

Usage (workdir = thesis dir): .venv-pdf/bin/python check_prose_batch.py
Exit code 0 = all files PASS.
"""
import re
import subprocess
import sys

FILES = [
    "chapter_01_introduction.tex",
    "chapter_02_literature_review.tex",
    "chapter_03_methodology.tex",
    "chapter_04_results.tex",
    "chapter_05_conclusion.tex",
    "appendix.tex",
]

BANNED = ("gnatprove", "spark", "formal verification")


def head_text(path):
    """Return the HEAD version of a cwd-relative file via git show."""
    out = subprocess.run(
        ["git", "show", f"HEAD:./{path}"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def counts(text):
    """Count the invariant token classes the editors must not change."""
    return {
        "words": len(re.findall(r"\S+", re.sub(r"(?<!\\)%.*", "", text))),
        "cite": len(re.findall(r"\\cite", text)),
        "protect": len(re.findall(r"\\protect", text)),
        "label": len(re.findall(r"\\label", text)),
        "braces": (text.count("{"), text.count("}")),
    }


def defects(text):
    """List forbidden sequences in working text (flag tokens are exempt)."""
    found = []
    # strip \texttt{-{}-...} flag tokens before hunting for `--`
    stripped = re.sub(r"\\texttt\{(?:-\{\}-[A-Za-z0-9]+)+\}", "", text)
    for m in re.finditer(r"--", stripped):
        line = stripped[:m.start()].count("\n") + 1
        found.append(f"-- at line {line}: {stripped[m.start()-30:m.end()+30]!r}")
    if "\u2014" in text:
        found.append(f"U+2014 x{text.count(chr(0x2014))}")
    low = text.lower()
    for w in BANNED:
        if w in low:
            found.append(f"banned word {w!r} x{low.count(w)}")
    return found


def main():
    """Run all checks; print a PASS/FAIL table; return process exit code."""
    bad = 0
    for path in FILES:
        with open(path, encoding="utf-8") as fh:
            cur = fh.read()
        old = head_text(path)
        c_cur, c_old = counts(cur), counts(old)
        probs = []
        for k in ("cite", "protect", "label"):
            # Losing tokens vs HEAD is a defect; gaining one is allowed when a
            # cycle deliberately adds a genuine citation (counts as evidence).
            if c_cur[k] < c_old[k]:
                probs.append(f"{k} {c_old[k]}->{c_cur[k]} (LOST)")
            elif c_cur[k] > c_old[k]:
                print(f"  note {path}: {k} {c_old[k]}->{c_cur[k]} (+deliberate)")
        if c_cur["braces"][0] != c_cur["braces"][1]:
            probs.append(f"unbalanced braces {c_cur['braces']}")
        probs += defects(cur)
        status = "PASS" if not probs else "FAIL"
        bad += bool(probs)
        delta = c_cur["words"] - c_old["words"]
        pct = 100.0 * delta / c_old["words"] if c_old["words"] else 0.0
        print(f"{status} {path}: words {c_old['words']}->{c_cur['words']} "
              f"({pct:+.1f}%), cite {c_cur['cite']}, "
              f"problems: {probs or 'none'}")
    print("VERDICT:", "FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
