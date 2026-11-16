#!/usr/bin/env python3
"""Add the two elaboration frames the register now owes: issue 3 and issue 4.

The deck's house pattern for a previous issue is a 2x2 card grid: a 24 pt title,
four cards of 6.07 x 2.40 in, each card holding a bold label paragraph and a body
paragraph at 16 pt Abadi MT Condensed Light in colour 062A31, a section chip, a
footer at 6.95 in and the sparkle/palette decoration.  Frames 42 and 43 use it
for issues 1 and 2; this script clones frame 43's shape tree twice, inserts the
copies at index 44 so all four issue frames sit together, and fills them with
the explanation that the register asked for.

Every number on the new frames is traceable:

  * the wall balance is `TPS_Surface_Balance` in
    stellarorion_program_proc/src/simulation_engine/stellarorion_physics.adb,
    lines 2601-2606, with the quartic term at 2613-2618;
  * the wall temperature 1348 K is `(q_rad / (eps * sigma)) ** 0.25` for
    q_rad = 140,399 W/m2 and eps = 0.75, i.e. the deck's own frame 20 and 21;
  * every GA value is the GA_Config record in
    stellarorion_program_proc/src/simulation_engine/stellarorion_optimization.ads,
    lines 210-218; the operators are at .adb 1460 (BLX-alpha), 1621 (Gaussian
    mutation) and 1373 (tournament).

The notes are written in the deck's own 8-part provenance format so the frames
stay readable by the generator that maintains the rest of the deck.
"""
import copy
import pathlib
import sys
import types
from typing import cast

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import make_pptx as M  # noqa: E402  (the generator, for its notes writer)
from easypptx import Slide as EasySlide  # noqa: E402
from pptx import Presentation  # noqa: E402

DECK = HERE / "ProgressReport.pptx"
BACKUP = HERE / "ProgressReport.pptx.bak_before_issue_slides"
TEMPLATE_INDEX = 43          # frame 43: PREVIOUS ISSUE 2, the same skeleton
INSERT_AT = 44               # new frames land right after frame 43

FRAMES = [
    {
        "id": "recall-previous-issue-3",
        "title": "PREVIOUS ISSUE 3: THE FOURTH POWER IS THE RADIATIVE SINK",
        "subtitle": "Issues: Issue 3",
        "cards": [
            ("What the frame actually solves:",
             "Not Fourier alone, but the wall balance (T - T_back)/R + eps*sigma*(T^4 - T_inf^4) - q_w + G*T - S = 0, with the in-plane term G*T - S from the lateral coupling."),
            ("Where the fourth power comes from:",
             "The surface sheds heat by re-radiating, q_rad = eps*sigma*T^4. Conduction carries the flux through the stack; radiation fixes the temperature at which that flux leaves, so T^4 is the boundary condition of the conduction problem, not a conduction law."),
            ("Why it forces an iteration:",
             "Fourier is linear in T and the sink is quartic, so no single linear solve closes the balance. With the neighbours fixed the slope is 1/R + 4*eps*sigma*T^3 + G, strictly positive, so the root is unique and a bisection reaches it."),
            ("At the design point:",
             "143,760 in = 140,399 re-radiated + 3,362 conducted W/m2, a ratio of 41.8 to 1. eps = 0.75 puts the wall at 1,348 K, where the sink moves 417 W/m2 per kelvin, 12.4 % of the conducted flux."),
        ],
        "footer": "Why the conduction frame carries a fourth power. The narration stays editable in PowerPoint.",
        "target": "the slide right after the elaboration of the second issue, before the two checks.",
        "note": "Why the conduction frame carries a power of four: the frame solves the wall energy balance, the quartic term is the Stefan-Boltzmann re-radiation that sets the surface temperature, and its nonlinearity is what forces the bisection.",
    },
    {
        "id": "recall-previous-issue-4",
        "title": "PREVIOUS ISSUE 4: WHAT EACH GENETIC PARAMETER DOES",
        "subtitle": "Issues: Issue 4",
        "cards": [
            ("Population 50, at most 200 generations:",
             "Fifty is ten times the five design variables and a quarter of the 200-individual cap. The campaign stopped on stagnation at generation 38, so it spent 50 x 38 = 1,900 evaluations, which is the budget the DSMC campaign had."),
            ("Tournament k = 3, two elites:",
             "The best of three random designs wins, so the best design is chosen with probability k/n = 3/50 = 6 % per draw, against 2 % at k = 1 and 100 % at k = 50: pressure enough to climb, mild enough to keep diversity. Two elites are copied untouched, so the best cost cannot regress."),
            ("Crossover 0.7, BLX-alpha 0.5:",
             "Seven pairs in ten are blended and three in ten copy the parents through. The blend samples the interval widened by alpha = 0.5 of the parental gap, so a child can step outside its parents without leaving the design box."),
            ("Mutation 0.1, sigma 0.1 of range:",
             "Each of the five genes mutates with probability 0.1, so half a gene per child on average, displaced by N(0, sigma) with sigma = 0.1 of that gene's range and clamped to its bounds. The run stops when the best cost has not improved by 1e-6 for 20 generations."),
        ],
        "footer": "Why each value and what it does; seed 42 keeps the campaign reproducible. The narration stays editable in PowerPoint.",
        "target": "the slide right after the elaboration of the third issue, before the two checks.",
        "note": "What every genetic parameter does and why it holds that value: population, generation cap, tournament pressure, elitism, crossover operator and rate, mutation rate and step, convergence rule, fixed seed.",
        "extra": "Values from GA_Config (stellarorion_optimization.ads:210-218); operators at stellarorion_optimization.adb:1373 (tournament), 1460 (BLX-alpha), 1621 (Gaussian mutation). The deck's earlier wording called the crossover uniform; it is BLX-alpha with alpha = 0.5.",
    },
]


def write_notes(slide, fr, body_lines):
    """Write the provenance block with the generator's own writer.

    The format is not reproduced by hand: `_write_notes` is called with a
    duck-typed frame (cast for the type checker only), so the notes come out
    byte-identical to a build and the deck's `_recorded_body` can read the body
    back.
    """
    frame = cast(
        "M.SlotFrame",
        types.SimpleNamespace(
            id=fr["id"],
            section="RECALL",
            title=fr["title"],
            figure=None,
            target_position=fr["target"],
            note=fr["note"],
            revision_note=fr.get("extra", ""),
        ),
    )
    body = "\n".join(body_lines)
    M._write_notes(EasySlide(slide), frame, body)
    return body


def clone_shapes(src_slide, dst_slide):
    tree = dst_slide.shapes._spTree
    for shape in list(dst_slide.shapes):
        tree.remove(shape._element)
    for shape in src_slide.shapes:
        tree.append(copy.deepcopy(shape._element))
    rebind_images(src_slide, dst_slide)


def rebind_images(src_slide, dst_slide):
    """Point the cloned pictures at the new slide's own image relationships.

    A deep-copied <p:pic> still carries the template slide's r:embed id.  That
    id does not exist in the new slide part's relationship table, so the copy
    opens as a broken picture (or a repair prompt in PowerPoint).  Each image is
    therefore re-related into the destination part and its blip re-pointed.
    """
    from pptx.oxml.ns import qn

    rebound = 0
    for shape in dst_slide.shapes:
        el = shape._element
        if el.tag != qn("p:pic"):
            continue
        blips = el.findall(".//" + qn("a:blip"))
        for blip in blips:
            old = blip.get(qn("r:embed"))
            if old is None:
                continue
            image_part = src_slide.part.related_part(old)
            new = dst_slide.part.relate_to(image_part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
            blip.set(qn("r:embed"), new)
            rebound += 1
    return rebound


def set_para_text(shape, label, body):
    tf = shape.text_frame
    ps = tf.paragraphs
    ps[0].runs[0].text = label
    body_run = ps[1].runs[0]
    body_run.text = body


def main():
    if BACKUP.exists():
        print(f"  backup already there, keeping it: {BACKUP.name}")
    else:
        BACKUP.write_bytes(DECK.read_bytes())
        print(f"  backup written: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")

    prs = Presentation(str(DECK))
    template = prs.slides[TEMPLATE_INDEX]

    for offset, fr in enumerate(FRAMES):
        slide = prs.slides.add_slide(template.slide_layout)
        clone_shapes(template, slide)

        # move the new slide from the end of the deck to its place in the block
        sldIdLst = prs.slides._sldIdLst
        new_id = list(sldIdLst)[-1]
        sldIdLst.remove(new_id)
        sldIdLst.insert(INSERT_AT + offset, new_id)

        renamed = 0
        for shape in slide.shapes:
            name = str(shape.name)
            if name.startswith("slot:recall-previous-issue-2"):
                shape._element.nvSpPr.cNvPr.set("name", f"slot:{fr['id']}")
                renamed += 1
            elif name.startswith("card:recall-previous-issue-2"):
                suffix = name.split("#")[-1]
                shape._element.nvSpPr.cNvPr.set("name", f"card:{fr['id']}#{suffix}")
                renamed += 1
            elif name.startswith("card_panel:recall-previous-issue-2"):
                shape._element.nvSpPr.cNvPr.set("name", f"card_panel:{fr['id']}")
                renamed += 1
            elif name.startswith("subtitle:recall-previous-issue-2"):
                shape._element.nvSpPr.cNvPr.set("name", f"subtitle:{fr['id']}")
                renamed += 1

        title = next(s for s in slide.shapes if s.name == "frame_title")
        title.text_frame.paragraphs[0].runs[0].text = fr["title"]
        sub = next(s for s in slide.shapes if s.name == f"subtitle:{fr['id']}")
        sub.text_frame.paragraphs[0].runs[0].text = fr["subtitle"]
        footer = next(s for s in slide.shapes if s.name == "slot_footer")
        footer.text_frame.paragraphs[0].runs[0].text = fr["footer"]

        cards = [s for s in slide.shapes if str(s.name).startswith(f"card:{fr['id']}#")]
        cards.sort(key=lambda s: str(s.name))
        lead = next(s for s in slide.shapes if s.name == f"slot:{fr['id']}")
        slots = [lead] + cards
        assert len(slots) == 4, f"expected four text slots, found {len(slots)}"
        for shape, (label, body) in zip(slots, fr["cards"]):
            set_para_text(shape, label, body)

        body_lines = [f"- {label} {body}" for label, body in fr["cards"]]
        body = write_notes(slide, fr, body_lines)
        written = slide.notes_slide.notes_text_frame.text
        print(f"  inserted at index {INSERT_AT + offset}: {fr['title'][:52]} | renamed {renamed} shapes | notes {len(written)} chars, body {len(body)}")

    prs.save(str(DECK))
    print(f"  saved {DECK.name}: {DECK.stat().st_size:,} bytes, {len(Presentation(str(DECK)).slides)} slides")


if __name__ == "__main__":
    main()
