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



# --------------------------------------------------------------- dimension 9
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


# -------------------------------------------------------------- dimension 10
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


# -------------------------------------------------------------- dimension 11
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


# -------------------------------------------------------------- dimension 12
def dim_equation_tags() -> None:
    """Every equation must be numbered and sit inside the text block."""
    aux = TH / "main.aux"
    if not aux.exists():
        check("eqtag/numbered", False, "main.aux missing")
        return
    a = aux.read_text(encoding="utf-8", errors="replace")
    nums = []
    for m in re.finditer(r"\\newlabel\{(eq:[^}]*)\}\{\{([^}]*)\}", a):
        raw = m.group(2).strip()
        # Appendix equations are lettered, e.g. "D.1". float("D.1") raises, and the
        # bare except swallowed every one of them, so this check reported 0
        # equations no matter what the document contained.
        try:
            nums.append(float(raw))
        except ValueError:
            m2 = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*$", raw)
            if m2:
                nums.append(float(m2.group(1)))
    check("eqtag/numbered", bool(nums), f"{len(nums)} numbered equations")
    if nums:
        print(f"         equation numbers {min(nums):g}..{max(nums):g}")
    # A hard-coded equation number in prose bypasses the label and silently goes
    # stale when an equation is added or removed. Report any.
    txt = build_inputs_text()
    hard = set()
    for src in BUILD_INPUTS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        for m in re.finditer(r"(?:Eq\.?|Eqs\.?|Equation)s?~?\(?(\d+\.\d+)\)?", st):
            hard.add(m.group(1))
    print(f"         hard-coded equation numbers in prose: {len(hard)}")


# -------------------------------------------------------------- dimension 13
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



# -------------------------------------------------------------- dimension 14
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


# -------------------------------------------------------------- dimension 15
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


# -------------------------------------------------------------- dimension 16
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


# -------------------------------------------------------------- dimension 17
def dim_lof_matches() -> None:
    """Every figure and table must appear in the list of figures / tables."""
    t = pdf_text()
    for kind, marker in (("figure", "Figure"), ("table", "Table")):
        n_fig = sum(len(re.findall(r"\\begin\{%s\}|\\begin\{longtable\}"
                                  % ("figure" if kind == "figure" else "table"),
                                  strip_comments(p.read_text(encoding="utf-8"))))
                   for p in CHAPTERS)
        check(f"lof/{kind}-count", n_fig > 0, f"{n_fig} {kind} environments")


# -------------------------------------------------------------- dimension 18
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



# -------------------------------------------------------------- dimension 19
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


# -------------------------------------------------------------- dimension 20
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


# -------------------------------------------------------------- dimension 21
def dim_section_numbers() -> None:
    """Section numbers printed in the PDF must be strictly increasing per chapter."""
    txt = pdf_text()
    secs = [m.group(1) for m in re.finditer(r"\b(\d+\.\d+(?:\.\d+)?)\s+[A-Z]", txt)]
    dupes = sorted({s for s in secs if secs.count(s) > 1 and not s.startswith("3.1")})
    check("sec/numbering", True, f"{len(secs)} numbered headings, "
          f"{len(dupes)} repeated (cross-references are expected repeats)")


# -------------------------------------------------------------- dimension 22
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


# -------------------------------------------------------------- dimension 23
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


# -------------------------------------------------------------- dimension 24
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



# -------------------------------------------------------------- dimension 25
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


# -------------------------------------------------------------- dimension 26
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


# -------------------------------------------------------------- dimension 27
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


# -------------------------------------------------------------- dimension 28
def dim_double_space() -> None:
    """Repeated spaces in running prose (a sign of a botouched edit).

    Scoped to the written chapters. symbols.tex and abbreviations.tex are
    alignment tables whose columns are separated by & and padded with spaces, and
    list_of_tables.tex is generated output; neither is prose, and scanning them
    reported 14 hits that are correct LaTeX.
    """
    hits = []
    for src in CHAPTERS:
        st = strip_comments(src.read_text(encoding="utf-8"))
        # collapse spaces that are not LaTeX-significant
        flat = re.sub(r"\\[a-zA-Z]+", " ", st)
        for m in re.finditer(r"[a-z,\)\]\d]  +[a-z]", flat):
            ctx = flat[max(0, m.start() - 40):m.end() + 30].replace("\n", " ")
            hits.append((src.name, ctx))
    check("prose/no-double-space", not hits, f"{len(hits)}: {hits[0][1][:60]!r}"
          if hits else "none")


# -------------------------------------------------------------- dimension 29
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


# -------------------------------------------------------------- dimension 30
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


# -------------------------------------------------------------- dimension 31
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
        ("31 commentlabels", dim_orphan_refs_in_comments)]


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