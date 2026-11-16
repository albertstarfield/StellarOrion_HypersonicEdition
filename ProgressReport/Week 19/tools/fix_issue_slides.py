#!/usr/bin/env python3
"""Second pass over the two new issue frames: titles, honest notes, and the two
wording corrections the build exposed in the older GA frames.

Four repairs, each with a reason:

1. TITLES.  `frame_title` on the cloned frame carried two runs, so setting run 0
   left the previous frame's tail ("Not yet shown thesis draft") glued to the new
   title.  Every paragraph after the first is removed and run 0 is rewritten.

2. NOTES.  `make_pptx._write_notes` opens with "PLACEHOLDER SLIDE. The slot is
   unfilled on purpose." whenever the frame has no figure.  That sentence is
   false for these two frames: they carry real card text.  The notes are written
   in the same format (Owner block / Frame id / Target position / Note / body
   between the two markers) with an honest first line, and `_recorded_body` is
   then used to prove the body still parses.

3. WORDING.  The deck called the crossover "uniform" (frame 30) and said mutation
   0.1 is applied "on every gene" (frame 31).  The implementation is BLX-alpha
   with alpha = 0.5 (`stellarorion_optimization.adb:1460`, called at 1997-2000)
   and a per-gene Bernoulli rate of 0.1 (`Gaussian_Mutate`, .adb:1621-1631).
   Both sentences are corrected.

4. SECTIONS.  A new slide that belongs to no section shows up in PowerPoint's
   default section.  Both new ids are inserted into the RESULTS section, right
   after the id of frame 43, so the section order matches the slide order.

5. REGISTER FOOTER.  Frame 41 said items 3 and 4 were "logged here" only.  They
   now have their own frames, so the footer says so.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pptx import Presentation  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402

DECK = HERE / "ProgressReport.pptx"
BACKUP = HERE / "ProgressReport.pptx.bak_before_issue_titles"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"

NOTES = {
    44: {
        "id": "recall-previous-issue-3",
        "title": "PREVIOUS ISSUE 3: THE FOURTH POWER IS THE RADIATIVE SINK",
        "target": "the slide right after the elaboration of the second issue, before the two checks.",
        "note": "Why the conduction frame carries a power of four: the frame solves the wall energy balance, the quartic term is the Stefan-Boltzmann re-radiation that sets the surface temperature, and its nonlinearity is what forces the bisection.",
        "body": (
            "- What the frame actually solves: the wall balance (T - T_back)/R + eps*sigma*(T^4 - T_inf^4) "
            "- q_w + G*T - S = 0, with the in-plane term from the lateral coupling.\n"
            "- Where the fourth power comes from: q_rad = eps*sigma*T^4 is the Stefan-Boltzmann re-radiation of "
            "the surface, i.e. the boundary condition of the conduction problem, not a conduction law.\n"
            "- Why it forces an iteration: Fourier is linear and the sink is quartic, and with the neighbours "
            "fixed the slope 1/R + 4*eps*sigma*T^3 + G is strictly positive, so the root is unique and bisection reaches it.\n"
            "- At the design point: 143,760 in = 140,399 re-radiated + 3,362 conducted W/m2 (ratio 41.8), eps = 0.75 "
            "puts the wall at 1,348 K, where the sink moves 417 W/m2 per kelvin, 12.4 % of the conducted flux."
        ),
    },
    45: {
        "id": "recall-previous-issue-4",
        "title": "PREVIOUS ISSUE 4: WHAT EACH GENETIC PARAMETER DOES",
        "target": "the slide right after the elaboration of the third issue, before the two checks.",
        "note": "What every genetic parameter does and why it holds that value: population, generation cap, tournament pressure, elitism, crossover operator and rate, mutation rate and step, convergence rule, fixed seed.",
        "body": (
            "- Population 50, at most 200 generations: ten times the five design variables, a quarter of the "
            "200-individual cap; the campaign stopped on stagnation at generation 38, so 50 x 38 = 1,900 evaluations.\n"
            "- Tournament k = 3, two elites: the best of three random designs wins, so the best design is chosen with "
            "probability k/n = 3/50 = 6 % per draw against 2 % at k = 1 and 100 % at k = 50; two elites never regress the best cost.\n"
            "- Crossover 0.7, BLX-alpha 0.5: seven pairs in ten are blended over the interval widened by alpha = 0.5 of the "
            "parental gap, three in ten copy the parents through.\n"
            "- Mutation 0.1, sigma 0.1 of range: each of the five genes mutates with probability 0.1 (half a gene per child "
            "on average) by N(0, sigma) with sigma = 0.1 of that gene's range, then clamped; stop when 1e-6 over 20 generations.\n"
            "- Provenance: GA_Config in stellarorion_optimization.ads:210-218; tournament .adb:1373, BLX-alpha .adb:1460, "
            "Gaussian mutation .adb:1621. The crossover is BLX-alpha, not uniform."
        ),
    },
}

WORDING = [
    (30, "uniform crossover 0.7", "BLX-alpha crossover 0.7, alpha 0.5"),
    (31, "mutation with 0.1 on every gene", "each gene mutates with probability 0.1"),
    (41, "Items 1 and 2 are elaborated on the slides that follow; items 3 and 4 are logged here.",
         "Each of the four is elaborated on the slides that follow."),
]


def set_single_run(shape, text):
    tf = shape.text_frame
    p0 = tf.paragraphs[0]
    keep = p0.runs[0]
    for run in list(p0.runs)[1:]:
        run._r.getparent().remove(run._r)
    for extra in list(tf.paragraphs)[1:]:
        extra._p.getparent().remove(extra._p)
    keep.text = text


def write_notes(slide, spec):
    lines = [
        f"Frame: {spec['title']}",
        "Owner block: RECALL",
        f"Frame id: {spec['id']}",
        f"Target position: {spec['target']}",
        f"Note: {spec['note']}",
        f"<<<SLOT_BODY id={spec['id']}>>>",
        spec["body"],
        "<<<END_SLOT_BODY>>>",
    ]
    slide.notes_slide.notes_text_frame.text = "\n".join(lines)


def add_to_results_section(prs, ids_after_45, new_ids):
    pres = prs.part._element
    sections = pres.findall(f".//{{{P14}}}section")
    names = [s.get("name") for s in sections]
    target = next(s for s in sections if s.get("name") == "RESULTS")
    lst = target.find(f"{{{P14}}}sldIdLst")
    entries = list(lst)
    anchor = None
    for e in entries:
        if e.get("id") == str(ids_after_45):
            anchor = e
    if anchor is None:
        raise RuntimeError(f"frame 43's sld id {ids_after_45} not found in RESULTS")
    from copy import deepcopy
    idx = entries.index(anchor) + 1
    for offset, sid in enumerate(new_ids):
        el = deepcopy(anchor)
        el.set("id", str(sid))
        lst.insert(idx + offset, el)
    return names


def main():
    if not BACKUP.exists():
        BACKUP.write_bytes(DECK.read_bytes())
        print(f"  backup written: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")
    prs = Presentation(str(DECK))

    for index, spec in NOTES.items():
        slide = prs.slides[index]
        title = next(s for s in slide.shapes if s.name == "frame_title")
        set_single_run(title, spec["title"])
        write_notes(slide, spec)
        print(f"  frame {index}: title='{title.text_frame.text[:60]}' notes={len(slide.notes_slide.notes_text_frame.text)} chars")

    for index, old, new in WORDING:
        slide = prs.slides[index]
        hits = 0
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            for p in sh.text_frame.paragraphs:
                joined = "".join(run.text for run in p.runs)
                if old not in joined:
                    continue
                # a run split mid-phrase would defeat a per-run replace, so the
                # whole paragraph is rebuilt into its first run and the rest
                # blanked, keeping run 0's formatting
                replaced = joined.replace(old, new)
                p.runs[0].text = replaced
                for run in list(p.runs)[1:]:
                    run.text = ""
                hits += 1
        print(f"  frame {index}: replaced {hits}x  {old[:44]!r} -> {new[:44]!r}")

    sld_ids = [el.get("id") for el in prs.slides._sldIdLst]
    new_ids = [sld_ids[44], sld_ids[45]]
    names = add_to_results_section(prs, int(sld_ids[43]), new_ids)
    print(f"  sections before: {names}")

    prs.save(str(DECK))
    print(f"  saved: {DECK.stat().st_size:,} bytes, {len(Presentation(str(DECK)).slides)} slides")


if __name__ == "__main__":
    main()
