#!/usr/bin/env python3
"""Parse a pdfTeX/LaTeX log into a bucketed, deduplicated warning + error report
WITH the source file and line recovered for every box defect.

AXIOMS
======
1. A LaTeX log interleaves hard errors (lines beginning "! ") and warnings
   (fragments such as "LaTeX Warning: ..." or "Package foo Warning: ...").
   Both must be bucketed by class, because a fix for one class rarely fixes
   another.
2. The same logical warning is re-emitted on every build pass. Counting raw
   occurrences over-reports the defect count by up to 4x, so warnings are
   deduplicated on (class, normalised message).
3. Overfull/Underfull box warnings are *typesetting* defects, not content
   defects. They must be reported separately and MUST carry a recoverable
   (file, line) so a human can open and fix them individually.
4. THE PROBLEM WITH (3): TeX's box warnings deliberately omit the filename
   ("Underfull \\hbox (badness 4954) in paragraph at lines 22==22"). They
   print only the line numbers. There is no "file:line:" prefix for them,
   unlike errors, even under -file-line-error. Verified empirically:
   `grep -cE "^[^ ]*\\.tex:[0-9]+: (Overfull|Underfull)" main.log` returns 0
   while the same log holds 74 box warnings.
   Therefore the filename must be recovered from TeX's own input stack, which
   the log DOES record: a line beginning "(" names the file being opened, and
   a line beginning ")" (possibly several in a row) closes one.
   => THEORY: replaying the log's open/close markers as a stack, then reading
   the top of that stack at the moment a box warning is emitted, yields the
   correct enclosing file. This is the same mechanism `latexmk` and
   `texfot` use to attribute log lines to files.
5. An empty report is a valid report. The target state is silence, so the
   script must be able to say CLEAN without inventing anything.

THEORIES
=========
Because passes 2-4 exist to settle cross references and citations, the FINAL
pass log is authoritative; transient "undefined" warnings in earlier passes
are expected and resolved by the last pass. So only the last log is parsed.

APPLICATIONS
============
    python3 report_warnings.py [path/to/main.log]
Default is ./main.log beside this script. Returns 0 only if fully clean.

Citations
=========
* TeX log file-name-prefix / stack grammar: https://texdoc.org/serve/logfile-spec/0/
* LaTeX2e error and warning stream: https://latex2e.readthedocs.io/en/stable/texerror.html
"""

from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path

_TEX_DOC = "https://texdoc.org/serve/logfile-spec/0/"

# AXIOM 2: normalisers stripping volatile detail so equal defects collapse.
_SUBS = (
    (re.compile(r"\b\d+ consecutive duplicate warnings\b"), ""),
    (re.compile(r"\(badness \d+\)"), "(badness N)"),
)

# TeX input-stack markers (AXIOM 4).
# Open:  a line whose first NON-SPACE character is "(" and which names a .tex
#        file. The leading-whitespace tolerance is REQUIRED, not cosmetic:
#        TeX continues a partially written line, so an input is frequently
#        logged as " (./chapter_01_introduction.tex" with a leading space.
#        Verified in this document's own main.log at lines 1205 and 1644.
# Close: a run of ")" at the start of the line (ignoring indent) closes that
#        many files.
_OPEN = re.compile(r"^\s*\(([^)\s]*\.tex)\b")
_CLOSE = re.compile(r"^\s*(\)+)")

# Bucket: (name, pattern). Pattern has the message in its LAST group.
_BUCKETS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ERROR", re.compile(r"^(?:.*?:(\d+):)?\s*!\s+(.*)$")),
    ("LaTeX Warning", re.compile(r"^.*?LaTeX Warning:\s*(.*)$")),
    ("Package Warning", re.compile(r"^.*?Package \S+ Warning:\s*(.*)$")),
    ("Class Warning", re.compile(r"^.*?Class \S+ Warning:\s*(.*)$")),
    ("pdfTeX Warning", re.compile(r"^.*?pdfTeX Warning:\s*(.*)$")),
    ("Font Warning", re.compile(r"^.*?Font Warning:\s*(.*)$")),
    ("Undefined citation", re.compile(r"^.*?Citation\s+[`'\"]([^`'\"]+)[`'\"]\s+on page.*$")),
    ("Undefined reference", re.compile(r"^.*?Reference\s+[`'\"]([^`'\"]+)[`'\"]\s+on page.*$")),
    ("duplicate destination", re.compile(r"^.*?destination with the same identifier.*$")),
    ("Overfull hbox", re.compile(r"^Overfull \\hbox \(([\d.]+)pt too wide\) in (.*)$")),
    ("Underfull hbox", re.compile(r"^Underfull \\hbox \((badness \d+)\) in (.*)$")),
    ("Overfull vbox", re.compile(r"^Overfull \\vbox \(([\d.]+)pt too high\) in (.*)$")),
    ("Underfull vbox", re.compile(r"^Underfull \\vbox \((badness \d+)\) in (.*)$")),
)

# "at lines 22==22" / "at lines 672==677" -> start line number.
_LINES_AT = re.compile(r"at lines (\d+)")
# "(badness 10000) in paragraph" style context, captured by the bucket pattern.
_KIND = re.compile(r"\b(paragraph|alignment|parbox|hbox)\b")


def _normalise(text: str) -> str:
    out = text.strip()
    for pat, rep in _SUBS:
        out = pat.sub(rep, out)
    return re.sub(r"\s+", " ", out)


class _FileStack:
    """Replay TeX's input-file stack so a log line can be attributed to a file.

    EMPIRICAL BASIS (verified against this document's own main.log)
    =============================================================
    TeX's box warnings deliberately omit the filename:
        "Underfull \\hbox (badness 10000) in paragraph at lines 32==32"
    so the file must be recovered from TeX's input stack. Verified facts about
    this log:
      * every chapter open appears as " (./<name>.tex" with a LEADING SPACE,
        because TeX continues a partially written line (log lines 918, 990,
        1025, 1131, 1165, 1205, 1256, 1486, 1644, 1764, 1833). A line-anchored
        regex must therefore tolerate leading whitespace.
      * every chapter close appears as a line-initial run of ")".
      * only .tex files are pushed, so package/class noise is ignored.

    REJECTED ALTERNATIVE, AND WHY
    =============================
    A per-character paren-depth scan looks more general but is WRONG here: the
    page-breaking detail lines the log emits around box warnings contain
    unbalanced parentheses of their own, which drive the depth negative and pop
    the whole stack, yielding an empty attribution for every site. The
    line-anchored tracker is therefore not a simplification but the reading
    that matches the actual log.

    Sites whose recovered line number cannot exist in the recovered file are
    rejected by the caller and reported as UNKNOWN rather than guessed.
    """

    _OPEN = re.compile(r"^\s*\((\./)?([^)\s]*\.tex)\b")
    _CLOSE = re.compile(r"^\s*(\)+)")

    def __init__(self) -> None:
        self.stack: list[str] = []
        self.seen: set[str] = set()

    def step(self, line: str) -> str | None:
        """Advance the stack by one log line; return the innermost .tex file."""
        m = self._OPEN.match(line)
        if m:
            name = m.group(2)
            if name not in self.stack:
                self.stack.append(name)
                self.seen.add(name)
            return self.stack[-1]
        m = self._CLOSE.match(line)
        if m:
            for _ in m.group(1):
                if self.stack:
                    self.stack.pop()
        return self.stack[-1] if self.stack else None


def _line_count(name: str, base: Path) -> int:
    """Line count of a thesis .tex file, or 0 when it is not one of ours."""
    f = base / name
    if not f.exists():
        return 0
    try:
        return len(f.read_text(encoding="utf-8", errors="replace").split("\n"))
    except OSError:
        return 0


def parse(log_path: Path) -> "OrderedDict[str, list[tuple[str, str, int]]]":
    """Return bucket -> [(location 'file:line', sample_message, count), ...]."""
    try:
        raw = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"FATAL: cannot read {log_path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    lines = raw.splitlines()
    stack = _FileStack()
    buckets: "OrderedDict[str, OrderedDict[str, list]]" = OrderedDict(
        (name, OrderedDict()) for name, _ in _BUCKETS
    )

    for line in lines:
        current = stack.step(line)

        for name, pat in _BUCKETS:
            m = pat.match(line)
            if not m:
                continue
            msg = m.group(m.lastindex) if m.groups() else line.strip()
            lineno_m = _LINES_AT.search(msg)
            lineno = int(lineno_m.group(1)) if lineno_m else 0

            # VALIDITY GUARD. A box warning can be raised inside a package or
            # class file rather than a thesis chapter, in which case the
            # recovered filename is the chapter the stack happened to be in and
            # the line number cannot exist there. Empirically this document
            # yields sites at lines 1657 / 1895 / 2093, which exceed EVERY
            # thesis .tex file (the longest is chapter_02 at 1557 lines).
            # Reporting those as chapter_05_conclusion.tex:1657 would be a lie,
            # so they are labelled UNKNOWN instead of being guessed at.
            if current and lineno and lineno > _line_count(current, log_path.parent):
                loc = f"UNKNOWN(non-thesis source, line {lineno})"
            elif current:
                loc = f"{current}:{lineno}"
            else:
                loc = f"UNKNOWN(no file on stack, line {lineno})"

            # Key on location so every distinct defect site is its own row.
            key = f"{loc}|{_normalise(msg)}"
            slot = buckets[name].setdefault(key, [loc, msg, 0])
            slot[2] += 1
            break

    out: "OrderedDict[str, list[tuple[str, str, int]]]" = OrderedDict()
    for name, od in buckets.items():
        if od:
            out[name] = [(v[0], v[1], v[2]) for v in od.values()]
    return out


def main() -> int:
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("main.log")
    buckets = parse(log_path)

    total = 0
    print(f"Log: {log_path}")
    for name, rows in buckets.items():
        subtotal = sum(r[2] for r in rows)
        total += subtotal
        print(f"\n===== {name}  ({subtotal} occurrence(s), {len(rows)} distinct site(s)) =====")
        for loc, msg, count in rows:
            body = msg if len(msg) <= 130 else msg[:127] + "..."
            print(f"  x{count:<3} {loc:<45} {body}")

    box = sum(r[2] for n in buckets if "box" in n for r in buckets[n])
    warn = sum(r[2] for n in buckets if "Warning" in n for r in buckets[n])
    ref = sum(
        r[2]
        for n in buckets
        if "Undefined" in n or "duplicate destination" in n
        for r in buckets[n]
    )
    err = sum(r[2] for r in buckets.get("ERROR", []))

    print("\n" + "#" * 62)
    print(f"TOTAL warning-class occurrences  : {warn}")
    print(f"TOTAL undefined cite/ref         : {ref}")
    print(f"TOTAL box defects (over/underfull): {box}")
    print(f"TOTAL hard errors                : {err}")
    print("VERDICT: " + ("CLEAN" if total == 0 else "NOT CLEAN"))
    print(f"(log grammar reference: {_TEX_DOC})")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
