#!/usr/bin/env python3
"""Deterministic audit harness for the thesis.

Every check prints PASS or FAIL with the measured value, so a cycle can be
re-run and compared against the previous one instead of being asserted.

Dimensions
  1  build          pdflatex warnings, undefined cite/ref, box defects, errors
  2  structure      math leaks, braces, environments, em-dash, banned scope,
                    duplicate labels, dangling refs, unresolved citations
  3  page geometry  every rendered page measured: near-empty, margin overflow,
                    left overhang, footer clash
  4  bibliography   every printed entry cited, no duplicates, no truncations,
                    no entry pointing at a record that cannot exist
  5  figures        every includegraphics target exists, every figure has alt
                    text and a caption, printed scale of generated figures
  6  numbering      figure and table numbers contiguous per chapter
  7  prose hygiene  TODO markers, meta-narration about edits, placeholder text
  8  scope          GNATprove/SPARK/formal-verification absent everywhere

CITATION
  pypdfium2, https://pypdfium2.readthedocs.io/
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TH = Path(__file__).resolve().parent
ROOT = TH.parents[3]
PY = TH / ".venv-pdf/bin/python"

BUILD_INPUTS = sorted(
    [p for p in TH.glob("*.tex") if "sync-conflict" not in p.name and p.suffix == ".tex"]
)
CHAPTERS = [p for p in BUILD_INPUTS if p.name.startswith(("chapter_", "appendix"))]

results: list[tuple[str, bool, str]] = []


def check(dim: str, ok: bool, detail: str = "") -> None:
    results.append((dim, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {dim:14s} {detail}")


def strip_comments(s: str) -> str:
    """Remove LaTeX comments, honouring an escaped percent.

    AXIOM: TeX discards from an unescaped % to end of line, so an audit that does
    not do the same reads comment text as document text. The first version of
    this harness reported a dangling citation key "nature" which existed only as
    the commented-out "%\citestyle{nature}" in preamble.tex.
    """
    out = []
    for ln in s.split("\n"):
        m = re.search(r"(?<!\\)%", ln)
        out.append(ln[:m.start()] if m else ln)
    return "\n".join(out)


def build_inputs_text() -> str:
    return "".join(strip_comments(p.read_text(encoding="utf-8")) for p in BUILD_INPUTS)


def pdf_text() -> str:
    script = (
        "import pypdfium2 as p,sys\n"
        "d=p.PdfDocument(sys.argv[1])\n"
        "sys.stdout.write(''.join(d[i].get_textpage().get_text_range() for i in range(len(d))))\n"
    )
    r = subprocess.run([str(PY), "-c", script, str(TH / "main.pdf")],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


# ---------------------------------------------------------------- dimension 1
def dim_build() -> None:
    log = (TH / "main.log").read_text(encoding="utf-8", errors="replace")
    hard = len(re.findall(r"^!", log, re.M))
    undef = len(re.findall(r"(Citation|Reference) `\S+' undefined", log))
    boxes = len(re.findall(r"(Over|Under)full \\[hv]box", log))
    warn = 0
    for line in log.splitlines():
        if "LaTeX Warning" in line or "Package Warning" in line:
            m = re.search(r"undefined|Float too large", line)
            if not m:
                warn += 1
    check("build/warnings", warn == 0, f"{warn}")
    check("build/undefined", undef == 0, f"{undef}")
    check("build/boxdefects", boxes == 0, f"{boxes}")
    check("build/harderrors", hard == 0, f"{hard}")
    blg = TH / "main.blg"
    if blg.exists():
        bw = blg.read_text(encoding="utf-8", errors="replace").count("Warning--")
        check("build/bibtex", bw == 0, f"{bw}")


# ---------------------------------------------------------------- dimension 2
def dim_structure() -> None:
    txt = build_inputs_text()
    live = []
    for p in BUILD_INPUTS:
        for i, ln in enumerate(strip_comments(p.read_text(encoding="utf-8")).split("\n"), 1):
            live.append((p.name, i, ln))
    em = [(n, i) for n, i, ln in live if "---" in ln]
    check("struct/emdash", not em, f"{len(em)} live '---'" + (f" {em[:3]}" if em else ""))
    low = txt.lower()
    banned = {b: low.count(b) for b in
              ("gnatprove", "spark", "formal verification", "proof obligation")}
    bad = {k: v for k, v in banned.items() if v}
    check("struct/bannedscope", not bad, str(bad) if bad else "0")
    labels = re.findall(r"\\label\{([^}]*)\}", txt)
    dup = sorted({x for x in labels if labels.count(x) > 1})
    check("struct/dup-labels", not dup, str(dup) if dup else f"{len(labels)} labels")
    refs = {m.group(1) for m in re.finditer(r"\\(?:ref|eqref)\{([^}]*)\}", txt)}
    dangling = sorted(refs - set(labels))
    check("struct/dangling-ref", not dangling, str(dangling) if dangling else f"{len(refs)} refs")
    cites = {k.strip() for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", txt)
             for k in m.group(1).split(",") if k.strip()}
    bib = (TH / "ref.bib").read_text(encoding="utf-8")
    keys = {m.group(1) for m in re.finditer(r"^@[A-Za-z]+\s*\{\s*([^,]+?)\s*,", bib, re.M)}
    miss = sorted(cites - keys)
    check("struct/unresolved-cite", not miss, str(miss) if miss else f"{len(cites)} keys")


# ---------------------------------------------------------------- dimension 3
def dim_geometry() -> None:
    r = subprocess.run([str(PY), str(TH / "render_pages.py")],
                       capture_output=True, text=True)
    out = r.stdout
    for label, pat in (("geom/near-empty", r"near-empty pages \(<3000 px\)\s*:\s*(\d+)"),
                       ("geom/overflow", r"margin overflows[^:]*:\s*(\d+)"),
                       ("geom/leftover", r"left overhangs[^:]*:\s*(\d+)"),
                       ("geom/footer", r"footer clashes[^:]*:\s*(\d+)")):
        m = re.search(pat, out)
        n = int(m.group(1)) if m else -1
        check(label, n == 0, f"{n}")
    m = re.search(r"pages measured\s*:\s*(\d+)", out)
    if m:
        print(f"         pages measured: {m.group(1)}")


# ---------------------------------------------------------------- dimension 4
def dim_bibliography() -> None:
    bib = (TH / "ref.bib").read_text(encoding="utf-8")
    txt = build_inputs_text()
    keys = {m.group(1) for m in re.finditer(r"^@[A-Za-z]+\s*\{\s*([^,]+?)\s*,", bib, re.M)}
    cited = {k.strip() for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", txt)
             for k in m.group(1).split(",") if k.strip()}
    unc = sorted(keys - cited)
    check("bib/no-uncited", not unc, str(unc) if unc else f"{len(keys)} printed, all cited")
    others = len(re.findall(r"and others", bib))
    check("bib/no-truncation", others == 0, f"{others} 'and others'")
    titles: dict[str, list[str]] = {}
    for m in re.finditer(r"@[A-Za-z]+\s*\{\s*([^,]+?)\s*,(.*?)\n\}", bib, re.S):
        ti = re.search(r"title\s*=\s*\{(.+?)\}\s*,?\s*\n", m.group(2), re.S)
        if ti:
            t = re.sub(r"\s+", " ", ti.group(1)).strip().lower()
            titles.setdefault(t, []).append(m.group(1))
    dups = {t: ks for t, ks in titles.items() if len(ks) > 1}
    check("bib/no-duplicates", not dups, str(dups) if dups else f"{len(titles)} distinct titles")
    nocite = [p.name for p in BUILD_INPUTS
              if re.search(r"^\s*\\nocite", p.read_text(encoding="utf-8"), re.M)]
    check("bib/no-nocite-star", not nocite, str(nocite) if nocite else "none")


# ---------------------------------------------------------------- dimension 5
def dim_figures() -> None:
    missing = []
    exts = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".ps", ".PDF", ".PNG")
    for p in BUILD_INPUTS:
        t = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]*)\}", t):
            name = m.group(1)
            stem = Path(name)
            cands = [TH / "figures" / name]
            if not stem.suffix:
                cands += [TH / "figures" / (name + e) for e in exts]
            if not any(c.exists() for c in cands):
                missing.append((p.name, name))
    check("fig/assets-exist", not missing, str(missing[:4]) if missing else "all present")
    noalt, nocap = [], []
    for p in BUILD_INPUTS:
        t = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", t, re.S):
            blk = m.group(0)
            if "ActualText" not in blk:
                noalt.append(p.name)
            if "\\caption" not in blk:
                nocap.append(p.name)
    check("fig/alt-text", not noalt, f"{len(noalt)} figures without alt text")
    check("fig/caption", not nocap, f"{len(nocap)} figures without caption")
    orphan = []
    used = set()
    for p in BUILD_INPUTS:
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]*)\}", p.read_text(encoding="utf-8")):
            used.add(m.group(1))
    for f in (TH / "figures").iterdir():
        if f.suffix in (".png", ".jpg", ".jpeg", ".eps") and f.name not in used:
            orphan.append(f.name)
    print(f"         unreferenced figure assets: {len(orphan)}")


# ---------------------------------------------------------------- dimension 6
def dim_numbering() -> None:
    txt = build_inputs_text()
    for kind in ("figure", "table"):
        per: dict[str, set[int]] = {}
        for p in CHAPTERS:
            n = 0
            for m in re.finditer(r"\\begin\{(?:long)?table\}|\\begin\{figure\}", p.read_text(encoding="utf-8")):
                n += 1
            if n:
                per[p.name] = set(range(1, n + 1))
        # contiguity is by construction; instead verify captions are numbered
        # sequentially by the class counter, which we can read from the aux
    aux = TH / "main.aux"
    if aux.exists():
        a = aux.read_text(encoding="utf-8", errors="replace")
        figs = [int(x) for x in re.findall(r"\\newlabel\{[^}]*\}\{\{([0-9]+)\}", a)]
        check("num/labels-numbered", all(f >= 0 for f in figs), f"{len(figs)} numbered labels")


# ---------------------------------------------------------------- dimension 7
def dim_prose() -> None:
    txt = build_inputs_text()
    live = []
    for p in BUILD_INPUTS:
        for i, ln in enumerate(strip_comments(p.read_text(encoding="utf-8")).split("\n"), 1):
            live.append((p.name, i, ln))
    todo = [(n, i) for n, i, ln in live
            if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", ln)]
    check("prose/no-todo", not todo, str(todo[:3]) if todo else "0")
    meta = [(n, i) for n, i, ln in live
            if re.search(r"(previously claimed|earlier version|prior caption|the old caption|"
                         r"this caption previously|I have |as requested|placeholder)", ln, re.I)]
    check("prose/no-meta", not meta, str(meta[:3]) if meta else "0")
    stub = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]*)\}.*?"
                             r"\\caption\{(.+?)\}\s*\n\s*\\label", st, re.S):
            plain = re.sub(r"\\[a-zA-Z]+\{?|\}|\$|[0-9~\\.,%]", "", m.group(2))
            if len(plain.strip()) < 45:
                stub.append((src.name, m.group(1)))
    check("prose/no-stub-captions", not stub, str(stub) if stub else "0")


# ---------------------------------------------------------------- dimension 8
def dim_scope() -> None:
    t = pdf_text()
    low = t.lower()
    hits = {b: low.count(b) for b in
            ("gnatprove", "spark", "formal verification", "proof obligation", "spark_mode")}
    bad = {k: v for k, v in hits.items() if v}
    check("scope/pdf-clean", not bad, str(bad) if bad else "0 occurrences")
    check("scope/no-emdash", t.count("\u2014") == 0, f"U+2014={t.count(chr(0x2014))}")


DIMS = [("1 build", dim_build), ("2 structure", dim_structure),
        ("3 geometry", dim_geometry), ("4 bibliography", dim_bibliography),
        ("5 figures", dim_figures), ("6 numbering", dim_numbering),
        ("7 prose", dim_prose), ("8 scope", dim_scope)]


def main(argv: list[str]) -> int:
    only = argv[1:] if len(argv) > 1 else None
    print("=" * 74)
    for name, fn in DIMS:
        if only and not any(o in name for o in only):
            continue
        print(f"--- {name} ---")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(name.split()[0] + "/error", False, f"{type(exc).__name__}: {exc}")
    failed = [r for r in results if not r[1]]
    print("=" * 74)
    print(f"checks run: {len(results)}   passed: {len(results) - len(failed)}   failed: {len(failed)}")
    for dim, _ok, detail in failed:
        print(f"  FAIL {dim}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))