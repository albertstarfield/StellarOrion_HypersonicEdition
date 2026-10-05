#!/usr/bin/env python3
"""Backref (.brf) validator: every apacite back-citation must point at a page
whose rendered text actually contains that reference's author-year cite.

AXIOMS:
  A1 main.bbl holds 44 apacite bibitems; main.brf holds one \\backcite per
     rendered citation occurrence, tagged with its printed folio label.
  A2 A backref is valid iff its target page's rendered text contains the
     citation's surname and year (layout-stable, robust to line breaks).
  A3 apacite short-author fields are raw LaTeX (\\BBA, \\BOthers{.}, ~, braces)
     and must be normalized before matching rendered text.

THEOREMS:
  T1 (label map) folio n -> pdf page n+30; roman folio i..xxxiv -> page index+2.
  T2 (normalization) strip_tex()+flat() reduce any bibitem short-author to the
     substring form that pdftext extraction yields on the citation page.

APPLICATIONS:
  check_backrefs.py parses bbl+brf, resolves every (key,label) pair, and
  FAILS (exit 1) when: a label is out of range, a key is unknown to the bbl,
  a bbl key has zero backrefs, or (surname, year) does not match the page.

OUTPUT/ERROR CONTRACT:
  prints a PASS/FAIL summary; exit 0 only when all checks pass.

[Citation: apacite 2.35 (backref module) - https://mirrors.ctan.org/macros/latex/contrib/apacite/]
"""
import re
import sys
import unicodedata
from pathlib import Path

import pypdfium2 as pdfium

# --- T1: folio -> pdf page map for the current front-matter offset ------------
BODY_OFFSET = 30          # fallback only; replaced at runtime by detect_body_offset()
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
         "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13,
         "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19,
         "xx": 20, "xxi": 21, "xxii": 22, "xxiii": 23, "xxiv": 24, "xxv": 25,
         "xxvi": 26, "xxvii": 27, "xxviii": 28, "xxix": 29, "xxx": 30,
         "xxxi": 31, "xxxii": 32, "xxxiii": 33, "xxxiv": 34}


def detect_body_offset(pdf):
    """Locate the 0-based pdf index of body folio 1 (chapter 1 opener) (T1).

    Front-matter edits (list shortening, added pages) shift this offset, so it
    is measured from the rendered document instead of hardcoded.

    Parameters: pdf - loaded pypdfium2 document.
    Returns: int index of the first page at/after index 11 headed 'CHAPTER 1'.
    Exceptions: RuntimeError when the heading cannot be located.
    """
    for i in range(11, len(pdf)):
        t = pdf[i].get_textpage().get_text_range()
        t = re.sub(r"[\uFFFC-\uFFFF\u200B\uFEFF]", "", t)
        if "CHAPTER 1" in t and "INTRODUCTION" in t:
            return i
    raise RuntimeError("body chapter-1 opener not found; front matter unexpected")


def label_to_pdf(label):
    """Map a printed folio label to a 0-based pdf page index (T1).

    Parameters: label (str) - arabic ('89') or roman ('xiv') folio.
    Returns: int page index, or -1 when the label is unresolvable.
    Exceptions: none; malformed labels return -1.
    """
    label = label.strip().lower()
    if label.isdigit():
        return int(label) + BODY_OFFSET - 1
    if label in ROMAN:
        return ROMAN[label] + 1 - 1
    return -1


def strip_tex(s):
    """Reduce an apacite short-author LaTeX string to plain text (A3).

    Parameters: s (str) - raw bbl short-author field.
    Returns: str with \\BOthers{.} -> 'et al.', \\BBA -> '&', no markup.
    Exceptions: none.
    """
    s = s.replace("~", " ")
    s = re.sub(r"\\BOthers\s*\{\s*\.?\s*\}", "et al.", s)
    s = s.replace(r"\BBA", "&")
    s = re.sub(r"\\protect\s*", "", s)
    s = re.sub(r"\\'", "", s)            # Mat\'ern -> Matern
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("\\", " ")
    return s.replace("{", "").replace("}", "")


def flat(s):
    """Normalize text for substring matching: accents stripped, commas/space
    collapsed, lowercased (T2).

    Parameters: s (str) - any text.
    Returns: str comparable against rendered pdf text.
    Exceptions: none.
    """
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s,]+", " ", s).strip().lower()


def surname(short):
    """First meaningful token of the normalized short-author (A2).

    Parameters: short (str) - raw short-author from bbl.
    Returns: str surname, or '' when no usable token exists.
    Exceptions: none.
    """
    for tok in strip_tex(short).split():
        t = tok.strip(",.;:")
        if len(t) > 1 and t.lower() not in ("et", "al", "others", "and"):
            return t
    return ""


def main():
    """Run all backref checks. Returns process exit code (0 = pass)."""
    bbl = Path("main.bbl").read_text(encoding="utf-8")
    brf = Path("main.brf").read_text(encoding="utf-8")
    bbl = re.sub(r"%\s*\n\s*", "", bbl)

    # bbl: key, short-author, year
    refs = {}
    for m in re.finditer(r"\\bibitem\s*\[([^\]]*)\]\s*\{(.*?)\}", bbl, re.S):
        body, key = m.group(1), m.group(2).strip()
        ca = re.search(r"\\citeauthoryear\s*\{(.*?)\}\s*\{(.*?)\}\s*"
                       r"\{\s*\{\\protect\s*\\APACyear\s*\{(\d{4})\}\s*\}\s*\}",
                       body, re.S)
        if not ca:
            print(f"FAIL bbl entry unparsable: {key}")
            return 1
        refs[key] = (ca.group(1), ca.group(2), ca.group(3))

    # brf: (key, label) unique pairs
    pairs = set(re.findall(r"\\backcite\s*\{(.*?)\}\{\{(.*?)\}\{", brf))
    keys = {k for k, _ in pairs}
    failures = []
    for k in sorted(keys - set(refs)):
        failures.append(f"unknown key in brf: {k}")
    for k in sorted(set(refs) - keys):
        failures.append(f"bbl key with zero backrefs: {k}")

    # page text cache
    global BODY_OFFSET
    pdf = pdfium.PdfDocument("main.pdf")
    npages = len(pdf)
    BODY_OFFSET = detect_body_offset(pdf)
    cache = {}

    def page_text(idx):
        if idx not in cache:
            raw = pdf[idx].get_textpage().get_text_range()
            cache[idx] = flat(re.sub(r"[\uFFFC-\uFFFF\u200B\uFEFF]", "", raw))
        return cache[idx]

    n_ok = 0
    for key, label in sorted(pairs):
        idx = label_to_pdf(label)
        if idx < 0 or idx >= npages:
            failures.append(f"bad page label {label!r} for {key}")
            continue
        short, _au, year = refs[key]
        sn, txt = flat(surname(short)), page_text(idx)
        if sn and sn in txt and year in txt:
            n_ok += 1
        else:
            failures.append(f"content miss: {key} @ {label} "
                            f"(need {sn!r}/{year})")

    print(f"bbl entries: {len(refs)}  brf keys: {len(keys)}  "
          f"unique pairs: {len(pairs)}  matched: {n_ok}")
    for f in failures:
        print("FAIL " + f)
    print("VERDICT:", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
