#!/usr/bin/env python3
r"""Render the PDF page of each regenerated figure for visual verification.

AXIOMS: (1) each of the 9 regenerated PNGs sits in exactly one figure
environment whose \caption text is unique enough to locate in the PDF text
layer; (2) pdf page = printed folio + body offset, where body offset is the
1-based index of the page containing both "CHAPTER 1" and "Introduction".
THEORIES: locate caption fragments by flattening pdfium text (strip invisible
chars, collapse whitespace), pick pages >= body index, render at scale 1.5.
APPLICATIONS: run `.venv-pdf/bin/python figcheck_render.py` (workdir =
thesis dir); writes figchk_<key>_p<N>.png, exits 1 if any probe misses.
ERRORS: RuntimeError on missing probe page. [Reference: goal rev 3+5
readability/figure-text verification]
"""
import re
import pathlib
import pypdfium2 as pdfium

TARGETS = {
    "pipeline": "fignew_pipeline.png",
    "heatflux": "fignew_scalloped_vs_smooth_heatflux.png",
    "traj": "fignew_trajectory.png",
    "convres": "fignew_convergence_residuals.png",
    "ccd": "fignew_ccd_screen.png",
    "gate": "fignew_gate_comparison.png",
    "sutton": "sutton_graves_parametric.png",
    "boccd": "bo_ccd_design.png",
    "boconv": "bo_convergence.png",
}


def flat(t: str) -> str:
    """Strip invisible chars and collapse whitespace so probes survive wrapping."""
    t = "".join(c for c in t if c.isprintable() or c in "\n\r\t")
    return re.sub(r"\s+", " ", t)


def caption_fragment(fname: str) -> str:
    """Return the first ~8 words of the \\caption following a figure's include."""
    for src in sorted(pathlib.Path(".").glob("chapter_*.tex")):
        text = src.read_text(encoding="utf-8")
        i = text.find(fname)
        if i < 0:
            continue
        m = re.search(r"\\caption(?:\[[^\]]*\])?\{", text[i:])
        if not m:
            continue
        start = i + m.end()
        # balanced-brace capture
        depth, j = 1, start
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        cap = text[start:j - 1]
        cap = re.sub(r"\\[a-zA-Z]+\s*", " ", cap)
        cap = re.sub(r"[{}$~]", " ", cap)
        words = [w for w in flat(cap).split() if w][:9]
        return " ".join(words)
    raise RuntimeError(f"no include found for {fname}")


def main() -> None:
    pdf = pdfium.PdfDocument("main.pdf")
    pages = [flat(pdf[i].get_textpage().get_text_range()) for i in range(len(pdf))]
    # body start = first page >= 11 with CHAPTER 1 + Introduction
    body = next(i for i in range(11, len(pages))
                if "CHAPTER 1" in pages[i] and "Introduction" in pages[i])
    missing = []
    for key, fname in TARGETS.items():
        frag = caption_fragment(fname)
        hit = next((i for i in range(body, len(pages)) if frag in pages[i]), None)
        if hit is None:
            # retry with first 5 words (caption line-break hyphenation)
            frag5 = " ".join(frag.split()[:5])
            hit = next((i for i in range(body, len(pages)) if frag5 in pages[i]), None)
        if hit is None:
            missing.append(key)
            print(f"{key}: MISS {frag!r}")
            continue
        pdf[hit].render(scale=1.5).to_pil().save(f"figchk_{key}_p{hit + 1}.png")
        print(f"{key}: pdf page {hit + 1}  [{frag[:60]}]")
    print("missing:", missing)
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
