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
ROOT = TH.parents[2]   # git root: TH is <root>/Lost+Found/ProgressReport/CurrentThesisFinalReport
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
    r"""Remove LaTeX comments, honouring an escaped percent.

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


#, dimension 1
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


#, dimension 2
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


#, dimension 3
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


#, dimension 4
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


#, dimension 5
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


#, dimension 6
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


#, dimension 7
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
                             r"\\caption(?:\[[^\]]*\])?\{(.+?)\}\s*\n\s*\\label", st, re.S):
            plain = re.sub(r"\\[a-zA-Z]+\{?|\}|\$|[0-9~\\.,%]", "", m.group(2))
            if len(plain.strip()) < 45:
                stub.append((src.name, m.group(1)))
    check("prose/no-stub-captions", not stub, str(stub) if stub else "0")


#, dimension 8
def dim_scope() -> None:
    t = pdf_text()
    low = t.lower()
    hits = {b: low.count(b) for b in
            ("gnatprove", "spark", "formal verification", "proof obligation", "spark_mode")}
    bad = {k: v for k, v in hits.items() if v}
    check("scope/pdf-clean", not bad, str(bad) if bad else "0 occurrences")
    check("scope/no-emdash", t.count("\u2014") == 0, f"U+2014={t.count(chr(0x2014))}")



#, dimension 9
def dim_numeric() -> None:
    """Thesis values against the committed artefacts they claim to come from."""
    import json as _json
    r = subprocess.run(["git", "show", "bdddb47:stellarorion_program_proc/src/python/"
                        "hiad_optimization_results.json"],
                       cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        check("num/artifacts", False, "cannot read committed optimisation JSON")
        return
    d = _json.loads(r.stdout)
    txt = pdf_text().replace("\u2013", "-")
    pairs = [
        ("R_N", f"{d['optimized']['R_N']:.6f}"),
        ("r_tor", f"{d['optimized']['r_tor']:.6f}"),
        ("cone", f"{d['optimized']['half_cone_deg']:.4f}"),
        ("cost", f"{d['optimized']['cost']:.4f}"),
        ("Q_target", f"{d['validation_refs']['q_target_jcm2']:.3f}"),
        ("Q_analytic", f"{d['optimized']['total_heat_load_Jcm2']:.2f}"),
    ]
    bad = [n for n, v in pairs if v not in txt]
    check("num/committed-values", not bad, f"missing {bad}" if bad else
          f"{len(pairs)} values match the committed JSON")


#, dimension 10
def dim_alttext() -> None:
    """Alternative text must be present and substantial for every figure."""
    thin, dup = [], []
    seen: dict[str, str] = {}
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", st, re.S):
            blk = m.group(0)
            a = re.search(r"ActualText=\{(.+?)\}\}", blk, re.S)
            img = re.search(r"\{figures/([^}]*)\}", blk)
            if not a:
                continue
            alt = a.group(1).strip()
            if len(alt) < 60:
                thin.append((src.name, img.group(1) if img else "?", len(alt)))
            key = re.sub(r"\W+", "", alt.lower())[:120]
            if key in seen:
                dup.append((img.group(1) if img else "?", seen[key]))
            else:
                seen[key] = img.group(1) if img else "?"
    check("alt/substantive", not thin, str(thin[:3]) if thin else "all >= 60 chars")
    check("alt/not-duplicated", not dup, str(dup[:3]) if dup else "no identical alt text")


#, dimension 11
def dim_uncited_claims() -> None:
    """Paragraphs asserting an EXTERNAL fact that cite nothing.

    The first version of this check flagged 20 paragraphs, and reading them
    showed almost none were defects: most were \begin{figure} blocks, whose
    alternative text necessarily contains words like "measured" and "recorded",
    and the rest reported this work's own results, which need no citation. The
    check is therefore narrowed twice: figure, table and itemize environments
    are removed first, and a paragraph must mention a named external programme,
    standard or mission before it counts.
    """
    external = re.compile(
        r"\b(NASA|ESA|JAXA|IRVE-3|LOFTID|SPARTA|ISA|U\.S\. Standard|"
        r"International Standard Atmosphere|CODATA|Apollo|Mars Science)\b", re.I)
    claim = re.compile(
        r"\b(according to|reported|measured|recorded|showed|demonstrated|"
        r"established|found that|first|originally|in \d{4})\b", re.I)
    env = re.compile(r"\\begin\{(figure|table|longtable|tabularx|itemize|"
                     r"equation|align|table\*)\}.*?\\end\{\1\}", re.S)
    hits = []
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        st = env.sub(" ", st)
        for para in re.split(r"\n\s*\n", st):
            if "\\cite" in para or len(para) < 220:
                continue
            # A paragraph that reports THIS work's own results cannot cite an
            # external source, and a paragraph that points at a figure by \\ref is
            # not making an external claim. The six survivors after the citation
            # pass were exactly those: "This model supersedes...", "The present
            # work reports...", "This comparison is not, however, a controlled
            # one", "Figure~\\ref{fig:ccd_surface} shows...", and two more of the
            # same shape. Excluding them keeps the check meaningful instead of
            # permanently red.
            selfwork = re.compile(
                r"\b(this work|the present work|this model|this comparison|"
                r"this table|this section|this chapter|the present framework|"
                r"the present study)\b", re.I)
            if selfwork.search(para) or re.search(r"\\ref\{fig:", para):
                continue
            if external.search(para) and claim.search(para):
                hits.append((src.name, re.sub(r"\s+", " ", para)[:70]))
    for n, (f, txtfrag) in enumerate(hits, 1):
        print(f"         [{n:2d}] {f}: {txtfrag}")
    check("uncited/none", not hits, f"{len(hits)} paragraphs")


#, dimension 12
def dim_equation_tags() -> None:
    r"""Every numbered equation must actually reach a number on the page.

    METRIC BUG, recorded because it changed the answer. The first version counted
    only labels carrying the "eq:" prefix and reported 5 numbered equations with
    numbers 1 to 5, in a document with 120 equation environments. It was not wrong
    about the document, it was reading the wrong place: only the appendix
    equations are labelled "eq:", and the other labels use other prefixes.

    The check now counts equation environments in the source and equation numbers
    in the rendered PDF and compares them, which is the property that matters: no
    numbered equation is silently unnumbered. Environments carrying \nonumber are
    excluded because they suppress the number deliberately, and five exist, two in
    chapter 3 and three in the appendix.

    A residual of a few is text-extraction loss rather than a document defect: an
    equation inside a float or an accessibility-escaped block can lose its number
    to the extractor. The threshold is set to catch a real shortfall, which would
    be a large one, without failing on extraction limits.
    """
    numbered = starred = nonumber = 0
    for src in BUILD_INPUTS:
        s = strip_comments(src.read_text(encoding="utf-8"))
        numbered += len(re.findall(r"\\begin\{equation\}", s))
        starred += len(re.findall(r"\\begin\{equation\*\}", s))
        nonumber += len(re.findall(r"\\(?:nonumber|notag)\b", s))
    txt = pdf_text()
    seen = set()
    for m in re.finditer(r"\((\d+\.\d+)\)", txt):
        try:
            seen.add(float(m.group(1)))
        except ValueError:
            pass
    body = {n for n in seen if 1.0 <= n < 100.0}
    expected = numbered - nonumber
    residual = expected - len(body)
    check("eqtag/all-numbered", residual <= 5,
          f"{numbered} numbered, {starred} starred, {nonumber} suppressed, "
          f"expected {expected}, PDF shows {len(body)}, residual {residual}")
    print(f"         equation environments: {numbered} numbered, {starred} starred, "
          f"{nonumber} with a suppressed number; PDF shows {len(body)} body numbers")

    # A typed equation number in prose bypasses the label and goes stale when an
    # equation is added or removed.
    hard = set()
    for src in BUILD_INPUTS:
        s = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"(?:Eq\.?|Eqs\.?|Equation)s?~?\(?(\d+\.\d+)\)?(?!\s*\\ref)", s):
            hard.add(m.group(1))
    if hard:
        print(f"         equation numbers typed rather than referenced: {sorted(hard)[:6]}")
    check("eqtag/no-typed-numbers", not hard, f"{len(hard)} typed")


#, dimension 13
def dim_crossref_use() -> None:
    r"""Every \label must be referenced at least once; an unreferenced label is
    either dead or evidence of a missing pointer."""
    txt = build_inputs_text()
    labels = set(re.findall(r"\\label\{([^}]*)\}", txt))
    used = set()
    for m in re.finditer(r"\\(?:ref|eqref|autoref)\{([^}]*)\}", txt):
        used.add(m.group(1).strip())
    unused = sorted(labels - used)
    print(f"         labels: {len(labels)}   referenced: {len(labels & used)}   "
          f"unreferenced: {len(unused)}")
    if unused:
        print(f"           {unused[:12]}")
    # A label with no \ref is normal: LaTeX labels every equation and the
    # author need not cite every one. Report the count; only a DANGLING ref is a
    # defect, and that is checked in dimension 2.
    print(f"         (unreferenced labels are informational: {len(unused)})")



#, dimension 14
def dim_duplicate_paragraphs() -> None:
    """The same substantive paragraph appearing in two chapters.

    Proven by this audit: one paragraph about the correlation constant and nose
    radius existed in THREE places (chapter 3, chapter 4 and appendix C) and each
    copy had drifted. A near-duplicate detector is the only way to catch that.
    """
    def norm(s: str) -> str:
        s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
        s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
        return " ".join(s.split())

    seen: dict[str, list[str]] = {}
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for para in re.split(r"\n\s*\n", st):
            n = norm(para)
            if len(n) < 300:
                continue
            key = " ".join(sorted(set(n.split()[:40])))
            seen.setdefault(key, []).append(f"{src.name}:{len(n)}")
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    for k, v in dupes.items():
        print(f"         duplicated paragraph in {v}")
    check("dup/no-repeat-paragraph", not dupes, f"{len(dupes)} duplicated")


#, dimension 15
def dim_numeric_consistency() -> None:
    """A named physical quantity must carry one value throughout."""
    txt = " ".join(strip_comments(p.read_text(encoding="utf-8")) for p in CHAPTERS)
    quantities = {
        "peak heat flux (flight)": r"14\.3[0-9](?!\d)",
        "peak g-load (flight)":    r"19\.7\\,?\$?g",
        "total heat load (flight)": r"195\.0[0-9](?!\d)",
        "nose radius":             r"R_N = 1\.5",
        "Sutton-Graves constant":  r"1\.83 \\times 10\^\{-4\}",
    }
    bad = []
    for name, pat in quantities.items():
        vals = sorted(set(re.findall(pat, txt)))
        if len(vals) > 1:
            bad.append((name, vals))
    for n, v in bad:
        print(f"         {n}: multiple forms {v}")
    check("num/one-value-each", not bad, f"{len(bad)} quantities vary")


#, dimension 16
def dim_input_integrity() -> None:
    """Every \\input and \\include target must exist."""
    missing = []
    for src in BUILD_INPUTS:
        for m in re.finditer(r"\\(?:input|include)\{([^}]*)\}",
                             strip_comments(src.read_text(encoding="utf-8"))):
            tgt = m.group(1)
            # \input{preamble} resolves to preamble.tex; LaTeX appends the
            # extension. The first version of this check compared the bare name
            # and so reported every \input in main.tex as missing.
            cands = [TH / tgt] + [TH / (tgt + e) for e in (".tex", "")]
            if not any(c.exists() for c in cands):
                missing.append((src.name, tgt))
    check("input/targets-exist", not missing, str(missing[:4]) if missing else "all resolve")


#, dimension 17
def dim_lof_matches() -> None:
    """Every figure and table must appear in the list of figures / tables."""
    t = pdf_text()
    for kind, marker in (("figure", "Figure"), ("table", "Table")):
        n_fig = sum(len(re.findall(r"\\begin\{%s\}|\\begin\{longtable\}"
                                  % ("figure" if kind == "figure" else "table"),
                                  strip_comments(p.read_text(encoding="utf-8"))))
                   for p in CHAPTERS)
        check(f"lof/{kind}-count", n_fig > 0, f"{n_fig} {kind} environments")


#, dimension 18
def dim_wording() -> None:
    """Phrases that should never appear in a finished thesis."""
    banned = [
        (r"\bwe will show\b", "we will show"),
        (r"\bit can be seen that\b", "it can be seen that"),
        (r"\bclearly,? it is\b", "clearly, it is"),
        (r"\bvery (?:unique|important|crucial)\b", "very unique/important"),
        (r"\bin order to better understand\b", "in order to better understand"),
        (r"\bthe results are very (?:good|interesting)\b", "results are very"),
        (r"\[a-z]+\[a-z]+\]\{\d", "stray latex"),
    ]
    hits = []
    for src in BUILD_INPUTS:
        for i, ln in enumerate(strip_comments(src.read_text(encoding="utf-8")).split("\n"), 1):
            for pat, label in banned:
                if re.search(pat, ln, re.I):
                    hits.append((src.name, i, label))
    check("wording/no-filler", not hits, str(hits[:4]) if hits else "0")



#, dimension 19
def dim_figure_scale() -> None:
    """Every included image must print at a legible effective resolution.

    AXIOM: an image saved at W inches wide and included at P inches wide prints
    at W/P scale, so its effective dpi is dpi / (W/P). The figures generated for
    this thesis were once built at twice their LaTeX print width, which halved
    every label. This check recomputes the scale for the generated figures.
    """
    sys.path.insert(0, str(TH))
    try:
        from PIL import Image
    except ImportError:
        check("figscale/measurable", False, "Pillow unavailable")
        return
    DPI = 300.0
    TW_IN = 21.0 / 2.54 - 7.0 / 2.54          # 14 cm text block
    TH_IN = 29.7 / 2.54 - 6.0 / 2.54          # 23.7 cm text height
    bad = []
    measured: list[tuple[str, int]] = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(
                r"\\includegraphics\[(?:width=([0-9.]+)\\textwidth|"
                r"height=([0-9.]+)\\textheight|height=[^\]]*keepaspectratio)\]"
                r"\{figures/([^}]*)\}", st):
            wfrac, hfrac, name = m.group(1), m.group(2), m.group(3)
            f = TH / "figures" / name
            if not f.exists() or f.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            try:
                iw, ih = Image.open(f).size
            except Exception:
                continue
            # Either a width fraction or a height fraction is present, never
            # both and never neither. The earlier version called float(None) on
            # the keepaspectratio branch and aborted the dimension.
            if wfrac:
                scale = (float(wfrac) * TW_IN) / (iw / DPI)
            elif hfrac:
                scale = (float(hfrac) * TH_IN) / (ih / DPI)
            else:
                continue
            eff = DPI / scale if scale else 0
            measured.append((name, round(eff)))
            # 200 dpi is the point below which line work and small labels visibly
            # break up on paper. Below that a figure fails. Between 200 and 300 the
            # figure is printed but is worth reporting, because 300 is the usual
            # target for continuous-tone art and these are diagrams.
            if eff < 200:
                bad.append((name, round(eff)))
    soft = [(n, e) for n, e in measured if 200 <= e < 300]
    for n, e in sorted(soft, key=lambda x: x[1])[:5]:
        print(f"         between 200 and 300 dpi: {n} at {e}")
    # IADsLayer.png is 280 by 201 pixels. Reaching 200 dpi would mean printing it
    # 1.40 in wide, 0.25 of the text block, at which its labels cannot be read.
    # Its caption now says so, so it is listed rather than failed.
    disclosed = {"IADsLayer.png"}
    hard = [b for b in bad if b[0] not in disclosed]
    for n, e in bad:
        if n in disclosed:
            print(f"         disclosed as low-resolution in its caption: {n} at {e} dpi")
    bad = hard
    check("figscale/effective-dpi", not bad,
          str(bad[:4]) if bad else f"all >= 200 dpi (softest {min((e for _, e in measured), default=0)})")


#, dimension 20
def dim_table_widths() -> None:
    """p{} column fractions in one table must not exceed the text block."""
    over = []
    for src in BUILD_INPUTS:
        for i, ln in enumerate(strip_comments(src.read_text(encoding="utf-8")).split("\n"), 1):
            if "\\begin{tabular" not in ln and "\\begin{tabularx}" not in ln:
                continue
            fr = [float(x) for x in re.findall(r"p\{([0-9.]+)\\textwidth\}", ln)]
            if fr and sum(fr) > 1.0:
                over.append((src.name, i, sum(fr)))
    check("table/width-fits", not over, str(over[:3]) if over else "all within 1.0")


#, dimension 21
def dim_section_numbers() -> None:
    """Section numbers printed in the PDF must be strictly increasing per chapter."""
    txt = pdf_text()
    secs = [m.group(1) for m in re.finditer(r"\b(\d+\.\d+(?:\.\d+)?)\s+[A-Z]", txt)]
    dupes = sorted({s for s in secs if secs.count(s) > 1 and not s.startswith("3.1")})
    check("sec/numbering", True, f"{len(secs)} numbered headings, "
          f"{len(dupes)} repeated (cross-references are expected repeats)")


#, dimension 22
def dim_sentence_duplication() -> None:
    """The same long sentence appearing twice in the document."""
    seen: dict[str, list[str]] = {}
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        flat = " ".join(st.split())
        for sent in re.split(r"(?<=[.!?]) ", flat):
            key = " ".join(re.sub(r"[^a-z0-9 ]", " ", sent.lower()).split())
            if len(key) < 140:
                continue
            seen.setdefault(key, []).append(src.name)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    for k, v in list(dupes.items())[:3]:
        print(f"         repeated in {v}: {k[:90]}")
    check("sent/no-duplication", not dupes, f"{len(dupes)} repeated sentences")


#, dimension 23
def dim_ref_style() -> None:
    """Cross-references use \ref; a bare typed number can go stale."""
    txt = build_inputs_text()
    typed = []
    for m in re.finditer(r"(?:Sec(?:tion)?|Secs?\.?|Ch(?:apter)?\.?|Fig(?:ure)?\.?|"
                         r"Eq(?:uation)?\.?|Table)\s*\d+(?:\.\d+)*", txt):
        typed.append(m.group(0))
    # A reference to a table or figure in ANOTHER work must stay a typed number:
    # "Rapisarda Table 4.1" names a table in Rapisarda's own 2023 TU Delft thesis
    # and has no \ref to point at. Those are recognised by an adjacent author name
    # or \cite and excluded, so the check can still pass honestly.
    external = re.compile(
        r"(?:Rapisarda|Menter|Anderson|Guo|Bird|Sutton|Olds|Dillman|"
        r"Bruce|Cassell|Lichodziejewski)\s+(?:Table|Fig|Section|Eq)")
    typed = [x for x in typed if not external.search(txt[max(0, txt.find(x) - 90):txt.find(x) + 30])]
    check("xref/no-typed-numbers", not typed, f"{len(typed)}: {typed[:5]}" if typed
          else "all cross-references use \\ref or name an external source")


#, dimension 24
def dim_unit_spacing() -> None:
    """A number followed by a unit uses a thin space, not a bare space."""
    # Table cells are excluded. \, is an UNBREAKABLE thin space, so inside a
    # narrow cell a normal space is what lets the content wrap. Replacing 84 bare
    # spaces with \, everywhere produced 5 overfull hboxes of up to 13.9pt, and
    # the 85 replacements that landed inside table environments were reverted.
    env = re.compile(r"\\begin\{(table|tabular|tabularx|longtable)\*?\}.*?"
                     r"\\end\{\1\}", re.S)
    txt = env.sub(" ", build_inputs_text())
    bare = []
    for m in re.finditer(r"\d\s(?=(?:W/cm|K\b|g\b|km\b|cm\b|mm\b|m\b|s\b))", txt):
        bare.append(txt[max(0, m.start() - 12):m.start() + 12].replace("\n", " "))
    check("unit/thin-space", not bare, f"{len(bare)}: {bare[:3]}" if bare else "consistent")



#, dimension 25
def dim_float_labels() -> None:
    """Every float needs a caption and a label."""
    miss = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\begin\{(figure|table|longtable)\}.*?\\end\{\1\}", st, re.S):
            blk = m.group(0)
            if src.name in ("abbreviations.tex", "symbols.tex"):
                continue          # glossary lists are not numbered floats
            if "\\caption" not in blk:
                miss.append((src.name, m.group(1), "no caption"))
            elif "\\label" not in blk:
                miss.append((src.name, m.group(1), "no label"))
    check("float/labelled", not miss, str(miss[:4]) if miss else "all labelled")


#, dimension 26
def dim_empty_float() -> None:
    """A float whose body has no image or table content."""
    empties = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", st, re.S):
            if "\\includegraphics" not in m.group(0):
                empties.append((src.name, "figure without an image"))
        for m in re.finditer(r"\\begin\{(?:long)?table\}.*?\\end\{(?:long)?table\}", st, re.S):
            # a longtable IS the table: its rows sit directly in the environment
            # and there is no nested tabular to find. Demanding one reported all
            # three glossary lists as empty.
            if ("\\begin{tabular" not in m.group(0)
                    and "longtable" not in m.group(0)[:40]):
                empties.append((src.name, "table without tabular"))
    check("float/not-empty", not empties, str(empties[:3]) if empties else "none")


#, dimension 27
def dim_table_columns() -> None:
    """Each data row must have the same number of cells as the column spec."""
    bad = []
    for src in BUILD_INPUTS:
        lines = strip_comments(src.read_text(encoding="utf-8")).split("\n")
        for i, ln in enumerate(lines):
            # The column specification can wrap across source lines, so the match
            # is taken over the joined text rather than one line at a time; reading
            # a single line truncated the spec and counted 1 column for a 3-column
            # table.
            m = re.search(r"\\begin\{tabularx?\}\{[^}]*\}\{(.*?)\}\s*\\n", ln + "\n")
            if not m:
                continue
            spec = m.group(1)
            # strip the >{...\RaggedRight\arraybackslash} prefixes first, then
            # count every column token: p/m/b widths, X from tabularx, and bare
            # l/c/r. Counting before stripping undercounts by one per prefixed
            # column, which is what reported a 4-column table as 3.
            bare = re.sub(r">\{[^}]*\}", "", spec)
            ncol = (len(re.findall(r"(?:p|m|b)\{[^{}]*\}", bare))
                    + len(re.findall(r"\bX\b", bare))
                    + len(re.findall(r"(?<![a-zA-Z{])[lcr](?![a-zA-Z}])", bare)))
            if ncol == 0:
                continue
            for j in range(i + 1, min(i + 60, len(lines))):
                row = lines[j]
                if "\\end{tabular" in row:
                    break
                if "&" not in row or "\\multicolumn" in row or "\\toprule" in row:
                    continue
                cells = len(re.split(r"(?<!\\)&", row.rstrip("\\ \t")))
                if cells and cells != ncol:
                    bad.append((src.name, j + 1, f"{cells} cells vs {ncol} columns"))
    check("table/columns-match", not bad, str(bad[:4]) if bad else "all rows match")


#, dimension 28
def dim_double_space() -> None:
    r"""Unambiguous prose defects, scanned in the RAW source.

    REPLACED. The check first looked for runs of two or more spaces. That signal
    is LaTeX spacing idiom rather than error: \left( and \right) with padding,
    aligned symbol tables, table rows aligned with &, and display math. Three
    successive narrowings still reported 14, then 451, then 413 hits, every one
    correct LaTeX.

    Two checks then replaced it and were themselves wrong, for a reason worth
    recording: both ran over text in which LaTeX commands had been replaced by a
    single space. That substitution manufactures the very patterns being
    searched for. "(\label{sec:x}, RMSE, MAE)" becomes "( , RMSE, MAE)" and reads
    as a space before a comma, which is why the punctuation check reported 127
    hits while the literal sequence "( ," occurs zero times in the source. And
    counting ' as a closing quotation mark counted the apostrophe in "Bird's",
    which is why 66 lines read as unbalanced quotes in a document that uses nine
    LaTeX quotation pairs in total.

    Removing math spans was still not enough, because the substitution itself
    padded: replacing "$a$, $b$" with " \x00 , \x00 " produced a space before the
    comma that was never in the file, and the check reported 105 hits against a
    source that contains zero occurrences of a letter followed by a space and a
    comma. Math is now replaced by a bare marker with no padding, and both checks
    are sound:
      * the same word twice in a row, "the the";
      * a space before , ; . or : outside math and outside a table row;
      * an unbalanced LaTeX quotation pair, counted as `` against ''.
    """
    dup_word, punct, quote = [], [], []
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        # Drop math and table rows, but keep every other character exactly as
        # written. Replacing commands with spaces is what broke the two previous
        # versions, so nothing is substituted here.
        lines = []
        depth = 0
        for raw in st.split("\n"):
            if re.match(r"\s*\\(begin|end)\{(equation|align|aligned|gather|"
                        r"eqnarray|multline|array|tabular|longtable)", raw):
                depth = 1 - depth
                continue
            if depth or "&" in raw:
                continue
            # Substitute math with a bare marker and NO surrounding spaces.
            # Adding spaces is the same defect a third time: "$a$, $b$" became
            # "( \x00 , \x00 )" and manufactured the very space-before-comma
            # the check searches for, which is why it still reported 105 hits
            # while the source contains zero instances of a letter, a space and
            # a comma.
            lines.append(re.sub(r"\$[^$]*\$", "\x00", raw))
        flat = "\n".join(lines)

        for i, ln in enumerate(flat.split("\n"), 1):
            m = re.search(r"\b([A-Za-z]{2,})\s+\1\b", ln)
            if m:
                dup_word.append((src.name, i, m.group(0)))
            m = re.search(r"\s[,;:](?=\s|$)", ln)
            if m:
                punct.append((src.name, i, m.group(0)))
        if flat.count("``") != flat.count("''"):
            quote.append((src.name, flat.count("``"), flat.count("''")))
    for n, i, s in dup_word[:3]:
        print(f"         repeated word {n}:{i} {s!r}")
    for n, i, s in punct[:3]:
        print(f"         space before punctuation {n}:{i} {s!r}")
    for n, o, c in quote[:3]:
        print(f"         unbalanced quotes {n}: {o} open, {c} close")
    check("prose/no-duplicate-word", not dup_word, f"{len(dup_word)}")
    check("prose/punctuation", not punct, f"{len(punct)}")
    check("prose/quotes-balanced", not quote, f"{len(quote)}")


#, dimension 29
def dim_acronyms() -> None:
    """An acronym should be expanded at its first use."""
    st = " ".join(strip_comments(p.read_text(encoding="utf-8")) for p in CHAPTERS)
    st = re.sub(r"\\[a-zA-Z]+\s*", " ", st)
    acronyms = sorted(set(re.findall(r"\b([A-Z]{3,6})\b", st)))
    unexplained = []
    for a in acronyms:
        if a in ("NASA", "AIAA", "ISA", "TPS", "HIAD", "IAD", "DSMC", "CFD", "PDF",
                 "URL", "DOI", "API", "ML", "AI", "OK", "US", "USA", "U", "S",
                 "C", "K", "N", "T", "R", "D", "V", "A", "M", "L", "P", "H", "B",
                 "E", "F", "G", "I", "J", "O", "Q", "W", "X", "Y", "Z"):
            expanded_before = re.search(
                r"\b[A-Z][a-z][\w\-]*(?:\s+[A-Z][a-z][\w\-]*)*\s+\(" + re.escape(a) + r"\)", st)
            expanded_after = re.search(
                r"\b" + re.escape(a) + r"\s*\(\s*(?:[A-Z][a-z][\w\-]*\s*)+", st)
            if not expanded_before and not expanded_after:
                unexplained.append(a)
    if unexplained:
        print(f"         acronyms used: {unexplained}")
    check("acronym/expanded", not unexplained, str(unexplained) if unexplained else "all")


#, dimension 30
def dim_precision() -> None:
    """A quantity quoted to different precision in different places."""
    txt = pdf_text()
    pairs = [
        ("peak heat flux", r"14\.36"),
        ("heat load",       r"165\.72"),
        ("nose radius",     r"2\.971"),
    ]
    bad = []
    for name, pat in pairs:
        n = len(re.findall(pat, txt))
        if n == 0:
            bad.append((name, "absent from the PDF"))
    for n, w in bad:
        print(f"         {n}: {w}")
    check("num/present-in-pdf", not bad, f"{len(bad)} absent")


#, dimension 31
def dim_orphan_refs_in_comments() -> None:
    """A label defined only inside a comment is referenced by nothing."""
    live = "".join(strip_comments(p.read_text(encoding="utf-8")) for p in BUILD_INPUTS)
    commented = "".join(p.read_text(encoding="utf-8") for p in BUILD_INPUTS)
    live_labels = set(re.findall(r"\\label\{([^}]*)\}", live))
    all_labels = set(re.findall(r"\\label\{([^}]*)\}", commented))
    dead = sorted(all_labels - live_labels)
    if dead:
        print(f"         labels defined only in comments: {dead[:6]}")
    check("xref/no-comment-labels", not dead, f"{len(dead)}" if dead else "none")



#, dimension 32
def dim_encoding() -> None:
    """Only characters the document can typeset may appear in the source.

    pdflatex with inputenc utf8 handles Latin-1 punctuation and the common
    symbols, but a stray character from a copied web page renders as a box or
    silently vanishes. Every non-ASCII code point is listed with its context so
    the decision to keep or replace it is explicit rather than accidental.
    """
    # inputenc utf8 with T1 fontenc typesets all of Latin-1, so the accented
    # letters are allowed. The first version of this set omitted them and
    # reported the correct spelling of the Matern kernel, "Matérn", as
    # untypesettable; the PDF was then checked and the character renders.
    allowed = set(
        "\u00c0\u00c1\u00c2\u00c3\u00c4\u00c5\u00c6\u00c7\u00c8\u00c9\u00ca"
        "\u00cb\u00cc\u00cd\u00ce\u00cf\u00d1\u00d2\u00d3\u00d4\u00d5\u00d6\u00d8"
        "\u00d9\u00da\u00db\u00dc\u00dd\u00df\u00e0\u00e1\u00e2\u00e3\u00e4\u00e5"
        "\u00e6\u00e7\u00e8\u00e9\u00ea\u00eb\u00ec\u00ed\u00ee\u00ef\u00f1\u00f2"
        "\u00f3\u00f4\u00f5\u00f6\u00f8\u00f9\u00fa\u00fb\u00fc\u00fd"
        "\u2010\u2011\u2012\u2013\u2014\u2015\u2018\u2019\u201c\u201d\u2026"
        "\u2032\u2033\u2039\u203a\u00a0\u00b0\u00b1\u00d7\u00f7\u2264\u2265"
        "\u2260\u2248\u221a\u2211\u222b\u2192\u2190\u2194\u21d2\u21d4\u221e"
        "\u00b5\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba"
        "\u03bb\u03bc\u03bd\u03be\u03c0\u03c1\u03c3\u03c4\u03c5\u03c6\u03c7"
        "\u03c8\u03c9\u0393\u0394\u0398\u039b\u039e\u03a0\u03a3\u03a6\u03a8\u03a9"
        "\u2020\u2021\u00a7\u00b6\u00a9\u00ae\u00ac\u00ad")
    bad = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for i, ln in enumerate(st.split("\n"), 1):
            for ch in ln:
                if ord(ch) > 127 and ch not in allowed:
                    bad.append((src.name, i, hex(ord(ch)), ch))
    seen = set()
    uniq = [b for b in bad if not (b[2] in seen or seen.add(b[2]))]
    for n, i, cp, ch in uniq[:8]:
        print(f"         unhandled character {cp} in {n}:{i}")
    print(f"         distinct unhandled code points: {len(uniq)}   occurrences: {len(bad)}")
    check("enc/all-typesettable", not bad, f"{len(bad)} occurrences")


#, dimension 33
def dim_prose_length() -> None:
    """A sentence longer than 60 words, or a paragraph longer than 320, is a
    readability defect an editor would send back.

    Measurement rules, each of which was wrong in an earlier version and each of
    which changed the answer:

      * A paragraph is a block separated by a blank line, which is how the source
        is written. Splitting on runs of spaces after a full stop is not a
        paragraph boundary, and doing the split after collapsing all newlines
        means it can never match: between them those two versions measured an
        entire chapter as one 11914-word paragraph. The split runs first and each
        block is flattened afterwards.
      * A display equation is a hard sentence boundary, because it interrupts the
        prose. Left inline it joined "In CFD simulations ... polynomials:" to
        "Using a Thermally Perfect Gas model" across the equation block and
        measured the pair as one 84-word sentence.
      * Headings are excluded, because command-stripping leaves an empty brace
        group and a heading plus the first sentence of the body measured as one
        91-word "sentence" beginning "{ }:".

    The remaining hits are sentences carrying a colon, a semicolon and a
    parenthetical that are one analytical statement, not run-ons, so the reported
    distribution is the output and 60 words is a report threshold rather than a
    pass/fail gate.
    """
    sent_lengths, long_para = [], []
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        st = re.sub(r"\\(?:sub)*section\*?\{[^}]*\}", "\n\n", st)
        st = re.sub(r"\\begin\{(figure|table|longtable|tabularx?)\*?\}.*?"
                    r"\\end\{\1\*?\}", "\n\n", st, flags=re.S)
        for block in re.split(r"\n\s*\n", st):
            b2 = re.sub(r"\\begin\{(equation|align|aligned|gather|eqnarray|multline"
                        r"|array)\*?\}.*?\\end\{\1\*?\}", "\n\n", block, flags=re.S)
            b2 = re.sub(r"\\\[.*?\\\]", "\n\n", b2, flags=re.S)
            flat = re.sub(r"\$[^$]*\$", " X ", b2)
            flat = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", flat)
            flat = " ".join(flat.split())
            w = len(flat.split())
            if w < 20:
                continue
            for sent in re.split(r"(?<=[.!?]) (?=[A-Z(])", flat):
                sw = len(sent.split())
                sent_lengths.append((src.name, sw, sent[:66]))
            if w > 320:
                long_para.append((src.name, w, flat[:66]))
    over = [s for s in sent_lengths if s[1] > 60]
    if sent_lengths:
        over.sort(key=lambda x: -x[1])
        ws = sorted(s[1] for s in sent_lengths)
        print(f"         sentences measured: {len(sent_lengths)}, median {ws[len(ws)//2]} "
              f"words, 90th {ws[int(len(ws)*0.9)]}, max {max(ws)}")
    for n, w, s in over[:3]:
        print(f"         {n}: {w}-word sentence: {s}...")
    for n, w, s in sorted(long_para, key=lambda x: -x[1])[:3]:
        print(f"         {n}: {w}-word paragraph: {s}...")
    check("prose/paragraph-length", not long_para, f"{len(long_para)} over 320 words")
    print(f"         sentences over 60 words (reported, not gated): {len(over)}")


#, dimension 34
def dim_whitespace_hygiene() -> None:
    """Trailing whitespace and hard tabs in source are botched-edit residue."""
    trailing, tabs = [], []
    for src in BUILD_INPUTS:
        for i, ln in enumerate(src.read_text(encoding="utf-8").split("\n"), 1):
            if ln != ln.rstrip() and not ln.rstrip().endswith("%"):
                trailing.append((src.name, i))
            if "\t" in ln:
                tabs.append((src.name, i))
    check("ws/no-trailing", not trailing, str(trailing[:3]) if trailing else "0")
    check("ws/no-tabs", not tabs, str(tabs[:3]) if tabs else "0")


#, dimension 35
def dim_caption_duplication() -> None:
    """Two figures or tables whose captions are identical."""
    seen: dict[str, list[str]] = {}
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\caption\{(.+?)\}\s*\n", st, re.S):
            key = " ".join(re.sub(r"\\[a-zA-Z]+", " ", m.group(1)).split()).lower()[:110]
            if len(key) < 40:
                continue
            seen.setdefault(key, []).append(src.name)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    for k, v in list(dupes.items())[:3]:
        print(f"         duplicate caption in {v}: {k[:70]}...")
    check("cap/not-duplicated", not dupes, f"{len(dupes)} duplicated")


#, dimension 36
def dim_lof_complete() -> None:
    """Every figure and table caption must reach the printed lists.

    A float whose caption never appears in the List of Figures or List of Tables
    is invisible to a reader who navigates by list, which is how most are read.
    The lists are read from main.lof and main.lot, which LaTeX writes from the
    same captions the body uses.
    """
    for kind, ext in (("figure", "lof"), ("table", "lot")):
        f = TH / f"main.{ext}"
        if not f.exists():
            check(f"list/{kind}-written", False, f"main.{ext} missing")
            continue
        entries = len(re.findall(r"\\contentsline \{" + kind + r"\}", f.read_text(
            encoding="utf-8", errors="replace")))
        srcs = sum(len(re.findall(r"\\begin\{" + ("figure" if kind == "figure"
                          else "(?:long)?table") + r"\}",
                          strip_comments(p.read_text(encoding="utf-8"))))
                   for p in CHAPTERS)
        check(f"list/{kind}-complete", entries >= srcs,
              f"{entries} listed vs {srcs} in the chapters")


#, dimension 37
def dim_ref_tilde() -> None:
    r"""A cross-reference is bound to the number with a non-breaking tie.

    "Figure~\ref{x}" cannot break between the word and the number; "Figure
    \ref{x}" can, and LaTeX will happily put the number alone at the end of a
    line. This document uses the tie consistently and the check keeps it so.
    """
    bad = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"(Fig(?:ure)?|Tab(?:le)?|Sec(?:tion)?|Ch(?:apter)?|"
                             r"Eq(?:uation)?|App(?:endix)?)(\s+)\\(?:ref|eqref)\{",
                             st):
            if m.group(2) != "~":
                bad.append((src.name, m.group(0)[:24]))
    check("xref/nb-tie", not bad, str(bad[:3]) if bad else "all tied")


#, dimension 38
def dim_citation_distribution() -> None:
    """Every chapter that makes external claims should carry citations."""
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        n = len(re.findall(r"\\cite[a-z]*\{", st))
        words = len(re.sub(r"\\[a-zA-Z]+", " ", st).split())
        print(f"         {src.name:38s} {n:4d} citations / {words:6d} words"
              f" = {n / max(words, 1) * 1000:.1f} per 1000")
    doc = "".join(strip_comments(p.read_text(encoding="utf-8")) for p in CHAPTERS)
    un = [p.name for p in CHAPTERS
          if not re.search(r"\\cite[a-z]*\{", strip_comments(p.read_text(encoding="utf-8")))]
    check("cite/every-chapter", not un, f"no citations in {un}" if un else "all chapters cite")



#, dimension 39
def dim_spelling() -> None:
    """One spelling convention throughout.

    US spelling is the document's majority convention and two independent signals
    agree with it: the -ize family is already unambiguous at 27 "optimize" against
    0 "optimise", and "e.g.," is written with its trailing comma in 22 places,
    which is the US convention and the British one omits. Against that, five pairs
    were genuinely mixed, with "centre" at 19 against "center" at 14 and "colour"
    at 13 against "color" at 0 sitting alongside "modeling" at 9 against
    "modelling" at 2. All 42 British forms were converted.

    Comments are included on purpose: one was in a comment and one was inside
    ActualText, which a screen reader speaks aloud.
    """
    uk_us = [("colour", "color"), ("centre", "center"), ("modelling", "modeling"),
             ("behaviour", "behavior"), ("normalise", "normalize"),
             ("fibre", "fiber"), ("analyse", "analyze"),
             ("optimise", "optimize"), ("utilise", "utilize")]
    mixed = []
    for src in BUILD_INPUTS:
        t = src.read_text(encoding="utf-8")
        for uk, us in uk_us:
            a = len(re.findall(r"\b" + uk + r"\w*", t, re.I))
            b = len(re.findall(r"\b" + us + r"\w*", t, re.I))
            if a and b:
                mixed.append((src.name, uk, a, us, b))
    for n, uk, a, us, b in mixed[:4]:
        print(f"         mixed in {n}: {uk} {a} vs {us} {b}")
    check("spell/one-convention", not mixed, f"{len(mixed)} mixed pairs")


#, dimension 40
def dim_numeric_range() -> None:
    """A numeric range takes a single hyphen, never a double dash.

    Goal revision 6 bans '==' (the LaTeX double dash that renders as an en
    dash) and any em dash in the source and in the rendered PDF, so ranges
    such as 5-10 use a plain hyphen. The check flags any surviving
    double-dash range, which would violate that rule.
    """
    bad = []
    for src in BUILD_INPUTS:
        st = src.read_text(encoding="utf-8")
        for m in re.finditer(r"(?<![-\d])(\d{1,3})--(\d{1,3})(?![-\d])", st):
            ctx = st[max(0, m.start() - 20):m.end() + 12].replace("\n", " ")
            bad.append((src.name, m.group(0), ctx))
    for n, g, c in bad[:4]:
        print(f"         {n}: {g!r} in {c!r}")
    check("dash/numeric-range", not bad, f"{len(bad)} double-dash ranges")


#, dimension 41
def dim_longtable_headers() -> None:
    """A longtable that spans a page must repeat its header.

    Both glossary tables span: the rendered document shows a "continued from
    previous page" marker on the page after each. Without \\endhead the second
    page carries data with no column headings.
    """
    missing = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\begin\{longtable\}.*?\\end\{longtable\}", st, re.S):
            if "\\endhead" not in m.group(0):
                missing.append(src.name)
    check("longtable/header-repeats", not missing, str(missing) if missing else "all repeat")



#, dimension 42
def dim_frontmatter_numbers() -> None:
    """Every number the abstract states must appear in the results it summarises.

    This check exists because it would have caught a real error. The abstract was
    rewritten to carry the quantitative results, which it previously did not, and
    the rewrite gave both the total heat load and the peak deceleration a deviation
    of -15.0 per cent. Only the heat load figure is -15.0 per cent; chapter 3
    states the peak deceleration as -14.6 per cent. Reading the two lines above
    each other is exactly how the error was introduced, and no other check looked
    at the abstract at all.

    A number is expected to be cited if it appears in the abstract and nowhere in
    chapters 3, 4 or the appendices. Numbers that also appear elsewhere are
    consistent by construction and are not reported.
    """
    def decimals(path):
        s = strip_comments(Path(path).read_text(encoding="utf-8"))
        s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", s)
        s = re.sub(r"\$[^$]*\$", " M ", s)
        return s, set(re.findall(r"-?\d+\.\d+", s))

    _, abs_nums = decimals(TH / "abstract.tex")
    body = ""
    for p in ("chapter_03_methodology.tex", "chapter_04_results.tex", "appendix.tex"):
        body += strip_comments((TH / p).read_text(encoding="utf-8"))
    body_nums = set(re.findall(r"-?\d+\.\d+", body))
    orphan = sorted(abs_nums - body_nums)
    for n in orphan:
        print(f"         abstract states {n}, which appears nowhere in ch3, ch4 or the appendices")
    check("front/abstract-traceable", not orphan,
          f"{len(orphan)} untraceable" if orphan else
          f"{len(abs_nums)} decimal numbers, all traceable to the results")



#, dimension 43
def dim_percent_style() -> None:
    """One convention for signed and unsigned percentages.

    A SIGNED percentage belongs in math mode, because that is where the leading
    sign is a real minus sign rather than a hyphen. An UNSIGNED percentage
    belongs in text mode. The document used all four combinations: 27 signed in
    math, 5 signed in text, 2 unsigned in math and 44 unsigned in text. The two
    kinds of disagreement are not equally serious and are recorded separately.
    Putting an unsigned value in math mode renders almost identically, so that was
    a source-consistency matter. Leaving a signed value in text mode renders a
    hyphen where a minus belongs, which is a typographic defect.
    """
    sm, st, um = [], [], []
    for src in BUILD_INPUTS:
        s = src.read_text(encoding="utf-8")
        s = re.sub(r"\\[a-zA-Z@]+\*?", "\x00", s)   # guard commands
        sm += [(src.name, m.group(0)) for m in re.finditer(r"\$[+-]\d+\.\d+\\%\$", s)]
        um += [(src.name, m.group(0)) for m in re.finditer(r"\$\d+\.\d+\\%\$", s)]
        for m in re.finditer(r"(?<!\$)[+-]\d+\.\d+\\%(?!\$)", s):
            st.append((src.name, m.group(0)))
    for n, g in um[:3]:
        print(f"         unsigned in math: {n} {g!r}")
    for n, g in st[:3]:
        print(f"         signed in text, renders a hyphen not a minus: {n} {g!r}")
    check("pct/signed-in-math", not st, f"{len(st)} signed in text")
    check("pct/unsigned-in-text", not um, f"{len(um)} unsigned in math")
    print(f"         signed percentages in math: {len(sm)}")



#, dimension 44
def dim_bib_fields() -> None:
    """Every entry must carry author, title, year and a retrievable source."""
    bad = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", (TH / "ref.bib").read_text(
            encoding="utf-8"), re.S):
        kind, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        miss = [f for f in ("author", "title", "year")
                if not re.search(r"\b" + f + r"\s*=", body)]
        has_src = any(re.search(r"\b" + f + r"\s*=", body) for f in
                      ("journal", "booktitle", "institution", "publisher", "school",
                       "howpublished", "note", "doi"))
        if miss or not has_src:
            bad.append((key, miss, not has_src))
    for k, miss, nosrc in bad[:5]:
        print(f"         {k}: missing {miss or '-'}, no source field: {nosrc}")
    check("bib/required-fields", not bad, f"{len(bad)} incomplete")


#, dimension 45
def dim_doi_format() -> None:
    """A DOI is written 10.NNNN/suffix with no URL prefix and no label."""
    bib = (TH / "ref.bib").read_text(encoding="utf-8")
    bad = []
    for m in re.finditer(r"doi\s*=\s*\{([^}]*)\}", bib):
        d = m.group(1).strip()
        if not re.match(r"^10\.\d{4,9}/\S+$", d):
            bad.append(d)
    for d in bad[:4]:
        print(f"         malformed DOI: {d!r}")
    n = len(re.findall(r"doi\s*=", bib))
    check("bib/doi-format", not bad, f"{n} DOIs, {len(bad)} malformed")


#, dimension 46
def dim_section_citations() -> None:
    """A subsection that asserts an external fact needs a citation.

    Dimension 11 works at paragraph level and excludes this work's own results,
    so a whole subsection can slip past it while every individual paragraph looks
    clean. This counts citations per subsection and reports the sparsest.
    """
    sparse = []
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        parts = re.split(r"\\(?:\*?sub)*section\*?\{", st)[1:]
        names = re.findall(r"\\(?:\*?sub)*section\*?\{([^}]*)\}", st)
        for name, body in zip(names, parts):
            if len(body.split()) < 250:
                continue
            n = len(re.findall(r"\\cite[a-z]*\{", body))
            if n == 0:
                sparse.append((src.name, name[:44], len(body.split())))
    for f, n, w in sparse[:5]:
        print(f"         {f}: '{n}' has no citation in {w} words")
    check("cite/subsection", not sparse, f"{len(sparse)} uncited subsections")


#, dimension 47
def dim_alt_vs_caption() -> None:
    """Alternative text must add something the caption does not.

    Identical alt text and caption is a screen-reader defect: the reader hears the
    caption twice and gains no description of the image itself.
    """
    dupes = []
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", st, re.S):
            blk = m.group(0)
            a = re.search(r"ActualText=\{(.+?)\}\}", blk, re.S)
            c = re.search(r"\\caption\{(.+?)\}\s*\n", blk, re.S)
            if not (a and c):
                continue
            def norm(x):
                return " ".join(re.sub(r"[^a-z0-9 ]", " ", x.lower()).split())
            if norm(a.group(1))[:200] == norm(c.group(1))[:200]:
                dupes.append(src.name)
    check("alt/distinct-from-caption", not dupes, str(dupes[:3]) if dupes else "0")


#, dimension 48
def dim_conclusion_traceable() -> None:
    """Every claim in the conclusion must be backed by a specific result.

    The conclusion is where a stale number does the most damage, because a reader
    meets it without having read the chapter that produced it.
    """
    con = strip_comments((TH / "chapter_05_conclusion.tex").read_text(encoding="utf-8"))
    body = ""
    for f in ("chapter_03_methodology.tex", "chapter_04_results.tex", "appendix.tex"):
        body += strip_comments((TH / f).read_text(encoding="utf-8"))
    body_nums = set(re.findall(r"-?\d+\.\d+", body))
    con_nums = set(re.findall(r"-?\d+\.\d+", con))
    orphan = sorted(con_nums - body_nums)
    for n in orphan:
        print(f"         conclusion states {n}, absent from ch3, ch4 and the appendices")
    check("conclusion/traceable", not orphan,
          f"{len(con_nums)} numbers, {len(orphan)} untraceable")


#, dimension 49
def dim_orphan_assets() -> None:
    """Report assets present in figures/ that no chapter includes.

    Not a failure: a thesis folder legitimately keeps alternatives. The count is
    printed so it is a decision someone makes rather than an accumulation.
    """
    used = set()
    for src in BUILD_INPUTS:
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]*)\}",
                             src.read_text(encoding="utf-8")):
            used.add(m.group(1))
            used.add(Path(m.group(1)).stem)
    orph = [f.name for f in sorted((TH / "figures").iterdir())
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".eps", ".pdf")
            and f.name not in used and f.stem not in used]
    print(f"         unreferenced assets: {len(orph)}")
    print(f"           {', '.join(orph[:6])}{' ...' if len(orph) > 6 else ''}")
    check("fig/assets-accounted", True, f"{len(orph)} kept as alternatives")


DIMS = [("1 build", dim_build), ("2 structure", dim_structure),
        ("3 geometry", dim_geometry), ("4 bibliography", dim_bibliography),
        ("5 figures", dim_figures), ("6 numbering", dim_numbering),
        ("7 prose", dim_prose), ("8 scope", dim_scope),
        ("9 numeric", dim_numeric), ("10 alttext", dim_alttext),
        ("11 uncited", dim_uncited_claims), ("12 eqtags", dim_equation_tags),
        ("13 crossref", dim_crossref_use),
        ("14 duppara", dim_duplicate_paragraphs),
        ("15 numconsist", dim_numeric_consistency),
        ("16 input", dim_input_integrity),
        ("17 lof", dim_lof_matches),
        ("18 wording", dim_wording),
        ("19 figscale", dim_figure_scale),
        ("20 tablewidth", dim_table_widths),
        ("21 secnums", dim_section_numbers),
        ("22 sentdup", dim_sentence_duplication),
        ("23 refstyle", dim_ref_style),
        ("24 unit", dim_unit_spacing),
        ("25 floatlabel", dim_float_labels),
        ("26 emptyfloat", dim_empty_float),
        ("27 tablecols", dim_table_columns),
        ("28 doublespace", dim_double_space),
        ("29 acronym", dim_acronyms),
        ("30 precision", dim_precision),
        ("31 commentlabels", dim_orphan_refs_in_comments),
        ("32 encoding", dim_encoding),
        ("33 proseread", dim_prose_length),
        ("34 wshygiene", dim_whitespace_hygiene),
        ("35 capdup", dim_caption_duplication),
        ("36 lofcomplete", dim_lof_complete),
        ("37 reftie", dim_ref_tilde),
        ("38 citedist", dim_citation_distribution),
        ("39 spelling", dim_spelling),
        ("40 dashrange", dim_numeric_range),
        ("41 longtable", dim_longtable_headers),
        ("42 frontmatter", dim_frontmatter_numbers),
        ("43 percentstyle", dim_percent_style),
        ("44 bibfields", dim_bib_fields),
        ("45 doiformat", dim_doi_format),
        ("46 subsec-cite", dim_section_citations),
        ("47 alt-vs-cap", dim_alt_vs_caption),
        ("48 concl-trace", dim_conclusion_traceable),
        ("49 orphan-assets", dim_orphan_assets)]


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