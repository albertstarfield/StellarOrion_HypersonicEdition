#!/usr/bin/env python3
r"""Add short optional titles to long \caption{...} commands (dry-run by default).

Purpose: LaTeX prints the full caption into the List of Figures/Tables, which has
grown the LOF to ~12 pages. \caption[short]{full} keeps the full caption in the
body and prints only the short form in the list (standard practice).

Guards (a caption is SKIPPED unless all pass):
  - caption >= MIN_WORDS words and not already bracketed;
  - candidate short form is a prefix ending at a sentence boundary (.) or safe
    word cut <= MAX_WORDS;
  - prefix has balanced braces, even number of $, no \item, no unmatched \{ .

Usage:
  python3 caption_shorten.py          # dry-run: print plan
  python3 caption_shorten.py ==apply  # rewrite files in place
"""

import re
import sys
from pathlib import Path

MIN_WORDS = 30
MAX_WORDS = 18


def find_captions(text: str):
    """Yield (start, full_body, end) for each unbracketed \\caption{...}."""
    for m in re.finditer(r"\\caption\{", text):
        i = m.end()
        depth = 1
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        if depth:
            continue
        body = text[m.end() : i - 1]
        if body.startswith("["):
            continue
        yield m.start(), body, i


def candidate_prefixes(body: str):
    """Yield progressively shorter candidate short forms (strings)."""
    # sentence cuts: prefix up to a period followed by space, longest first
    for m in re.finditer(r"(?<=\S)\.\s", body):
        cand = body[: m.start()].strip()
        if len(cand.split()) >= 8:
            yield cand + "."
    # hard word cut
    words = body.split()
    if len(words) > MAX_WORDS:
        yield " ".join(words[:MAX_WORDS]) + "..."


def safe(cand: str) -> bool:
    """True when the LaTeX prefix is self-contained enough for a list entry."""
    if cand.count("{") != cand.count("}"):
        return False
    if cand.count("$") % 2 != 0:
        return False
    if "\\item" in cand or "\\begin" in cand or "\\end" in cand:
        return False
    if "\\ref" in cand or "\\cite" in cand or "\\label" in cand:
        return False
    if re.search(r"\\[a-zA-Z]+\s*$", cand):
        return False
    return True


STOPWORDS = {
    "a", "an", "the", "of", "in", "to", "at", "and", "or", "rather", "than",
    "is", "are", "was", "were", "with", "for", "on", "by", "as", "that",
    "this", "which", "from", "over", "into", "so", "it", "its", "not",
}


def refix_short(body: str):
    """Rebuild a short form that previously ended with an ellipsis (A5).

    Cut at the last clause boundary (, ; :) within the first 34 words, longest
    first; otherwise trim trailing stopwords from a 22-word cut. Never emits
    '...', so leader dots are not doubled in the list.

    Parameters: body (str) - the FULL caption text from the braced argument.
    Returns: str short form, or None when no safe candidate exists.
    Exceptions: none.
    """
    words = body.split()
    hi = min(len(words), 34)
    for i in range(hi, 7, -1):
        if words[i - 1] and words[i - 1][-1] in ",;:":
            cand = " ".join(words[:i])
            cand = re.sub(r"[,;:]$", ".", cand)
            if safe(cand):
                return cand
    cut = min(len(words), 22)
    while cut > 8 and words[cut - 1].strip(".,;:").lower() in STOPWORDS:
        cut -= 1
    cand = " ".join(words[:cut]).rstrip(" ,;:")
    if safe(cand):
        if not cand.endswith((".", "!", "?")):
            cand += "."
        return cand if safe(cand) else None
    return None


def refix_file(path, text, apply_mode: bool) -> int:
    """Replace ellipsis-terminated short forms in one file (A5).

    Parameters: path (Path) - file for messages; text (str) - source.
                apply_mode (bool) - write the result back when True.
    Returns: int number of short forms refixed.
    Exceptions: none; unsafe candidates are skipped with a printed note.
    """
    edits = []
    for m in re.finditer(r"\\caption\[([^\]]+)\]\{", text):
        if not m.group(1).endswith("..."):
            continue
        i = m.end()
        depth = 1
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[m.end() : i - 1]
        new = refix_short(body)
        if new is None:
            print(f"SKIP {path.name}: cannot refix {m.group(1)[:50]!r}")
            continue
        print(f"REFIX {path.name}: {m.group(1)[:55]!r} -> {new[:55]!r}")
        edits.append((m.start(1), m.end(1), new))
    for s, e, new in reversed(edits):
        text = text[:s] + new + text[e:]
    if apply_mode and edits:
        path.write_text(text, encoding="utf-8")
    return len(edits)


def main() -> None:
    """Dry-run or apply short caption forms across all thesis .tex files."""
    apply_mode = "--apply" in sys.argv
    if "--refix" in sys.argv:
        total = 0
        for p in sorted(Path(".").glob("*.tex")):
            total += refix_file(p, p.read_text(encoding="utf-8"), True)
        print(f"REFIX-APPLIED: {total} ellipsis shorts rebuilt")
        return
    planned = 0
    skipped = 0
    for path in sorted(Path(".").glob("*.tex")):
        text = path.read_text(encoding="utf-8")
        edits = []
        for start, body, end in find_captions(text):
            if len(body.split()) < MIN_WORDS:
                continue
            short = next((c for c in candidate_prefixes(body) if safe(c)), None)
            if short is None:
                skipped += 1
                print(f"SKIP {path.name}: {body[:60]!r} (no safe prefix)")
                continue
            edits.append((start, end, short, len(body.split())))
        for start, end, short, nwords in edits:
            planned += 1
            print(f"PLAN {path.name}: {nwords}w -> {short[:70]!r}")
        if apply_mode and edits:
            before = len(text)
            # apply back-to-front so earlier offsets stay valid
            for start, end, short, nwords in reversed(edits):
                assert text[start : start + 9] == "\\caption{", (path, start)
                text = text[: start + 8] + f"[{short}]" + text[start + 8 : end] + text[end:]
            expected = before + sum(len(s) + 2 for _, _, s, _ in edits)
            assert len(text) == expected, (
                f"{path}: length {len(text)} != expected {expected} (truncation guard)"
            )
            path.write_text(text, encoding="utf-8")
    mode = "APPLIED" if apply_mode else "DRY-RUN"
    print(f"{mode}: {planned} captions given short forms, {skipped} skipped")


if __name__ == "__main__":
    main()
