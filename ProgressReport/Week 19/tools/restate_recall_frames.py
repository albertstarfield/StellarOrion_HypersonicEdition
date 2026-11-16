#!/usr/bin/env python3
"""Split the recall opening into a problem frame and an objective/scope frame.

The two opening frames overlapped: the background frame ended with a one-line
scope, and the objective frame ended with a limit that repeated it.  This tool
gives each frame one job.

  frame 2, BACKGROUND OVERVIEW          the actual problem, why it bites,
                                        the research gap, the trade
  frame 3, OBJECTIVE AND RESEARCH SCOPE the objective, the scope, what is out
                                        of scope, how the work is checked

Every sentence is a compression of a named section of Chapter I of
CurrentThesisFinalReport:

  fairing cap             chapter_01_introduction.tex:6    (Background)
  inflatable advantage    chapter_01_introduction.tex:9    (Background)
  deformation affects flow chapter_01_introduction.tex:32  (Problem Statement)
  rarefied regime         chapter_01_introduction.tex:34   (Problem Statement)
  four competing targets  chapter_01_introduction.tex:36   (Problem Statement)
  objective               chapter_01_introduction.tex:41   (Research Objective)
  validation, seed        chapter_01_introduction.tex:51   (Research Objective 4)
  no integrated framework chapter_01_introduction.tex:61   (Research Gap)
  manual sweeps           chapter_01_introduction.tex:63   (Research Gap)
  scope items             chapter_01_introduction.tex:88-100 (Scope and Limitations)
  PINN removed            chapter_01_introduction.tex:53   (pipeline note)
  grid independence       chapter_01_introduction.tex:96   (Scope, grid and pairing)
  fixed seed 42           stellarorion_optimization.ads:229 (GA_Config.Seed)

Layout: 2 x 2 blocks of 440 x 88 pt, 15 pt type, autofit off, top anchor, 6 pt
side margins; measured against the exported PDF so no block can spill.  The
notes are rewritten from the visible text, so the recorded body and the slide
agree character for character.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN  # noqa: E402
from pptx.util import Pt  # noqa: E402

DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"
BACKUP = HERE / "scaffold.json.bak_before_recall_merge"
FONT_PT = 15.0
INK = RGBColor.from_string("062A31")
POSITIONS = [(40, 316), (481, 316), (40, 406), (481, 406)]
CARD_W, CARD_H = 440, 92

FRAMES = [
    {
        "index": 2,
        "id": "recall-latar-belakang",
        "title": "BACKGROUND OVERVIEW",
        "subtitle": "Recall: the Problem and the Gap",
        "footer": "Four sentences, each compressed from Chapter I: Background, Problem Statement "
                  "and Research Gap.",
        "note": "The problem, why it bites, the gap and the trade, one block each. The scope is not "
                "on this frame: it moved to the frame that follows, so the two opening frames do "
                "not repeat each other.",
        "blocks": [
            ("THE ACTUAL PROBLEM",
             "a rigid shield cannot outgrow the fairing, so entry mass is capped, and above 50 km "
             "the continuum CFD that sized it stops being valid."),
            ("WHY IT BITES",
             "an inflatable packs small and inflates large, but its surface deforms under load, "
             "and that deformation changes the flow field and the heat transfer."),
            ("THE RESEARCH GAP",
             "no framework couples parametric geometry, DSMC in the transitional regime and GA "
             "optimisation; HIAD work stays on RANS/LES and manual sweeps."),
            ("THE TRADE",
             "area buys drag and thins the flux per unit area, yet peak heating, heat load, "
             "ballistic coefficient and mass move together, so the envelope is optimised, not chosen."),
        ],
    },
    {
        "index": 3,
        "id": "recall-tujuan-scope",
        "title": "OBJECTIVE AND RESEARCH SCOPE",
        "subtitle": "Recall: the Objective and the Scope",
        "footer": "Out of scope: packing and deployment mechanics, toroid structural sizing and the PINN path; the FTPS itself is flexible, only its shape is frozen.",
        "note": "The objective, the scope, what rigid means in that scope and how the work is "
                "checked. Rigid is a geometry assumption, not a material one: the fully inflated shape "
                "is frozen, so pressure-load deflection, fabric wrinkling, ablation and fluid-structure "
                "coupling are all outside the model (chapter 1, Scope and Limitations, item 1). The "
                "background frame carries the problem and the gap, so this frame starts from what the "
                "study sets out to do and where it stops.",
        "blocks": [
            ("THE OBJECTIVE",
             "build and validate one framework that predicts a HIAD aerothermal load and "
             "optimises its geometry for survivability, using SPARTA DSMC and a genetic algorithm."),
            ("THE SCOPE",
             "rigid, fully inflated 6-toroid HIAD; 5-species air with VSS collisions; "
             "0.01 < Kn < 1 at 50 to 60 km; 2D axisymmetric or 3D; GA on an analytic cost."),
            ("WHAT RIGID MEANS",
             "the fully inflated shape is frozen for the run: no pressure-load deflection, no "
             "fabric wrinkling, no ablation or recession, and no fluid-structure coupling."),
            ("HOW IT IS CHECKED",
             "Sutton-Graves and SPARTA surface quantities against IRVE-3 flight data, a four-level "
             "grid independence study, and a fixed seed 42 for re-runs."),
        ],
    },
]


def style(tf):
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_top = Pt(4)
    tf.margin_bottom = Pt(4)
    tf.margin_left = Pt(6)
    tf.margin_right = Pt(6)
    for p in tf.paragraphs:
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = 1.0
        for r in p.runs:
            r.font.size = Pt(FONT_PT)
            r.font.color.rgb = INK


def write_block(shape, label, body):
    tf = shape.text_frame
    tf.text = ""
    p = tf.paragraphs[0]
    bold_run = p.add_run()
    bold_run.text = f"\u2022 {label}: "
    bold_run.font.bold = True
    plain = p.add_run()
    plain.text = body
    plain.font.bold = False
    style(tf)


def set_single_run(shape, text):
    tf = shape.text_frame
    p = tf.paragraphs[0]
    assert p.runs, f"{shape.name} has no run to inherit formatting from"
    p.runs[0].text = text
    for extra in p.runs[1:]:
        extra._r.getparent().remove(extra._r)
    for extra_p in tf.paragraphs[1:]:
        extra_p._p.getparent().remove(extra_p._p)


def block_names(slide, frame_id):
    names = {str(s.name) for s in slide.shapes}
    ordered = [f"slot:{frame_id}"] + [f"card:{frame_id}#{i}" for i in (1, 2, 3)]
    missing = [n for n in ordered if n not in names]
    assert not missing, f"{frame_id}: missing shapes {missing}"
    return ordered


def frame_text(slide, frame_id):
    keys = (f"slot:{frame_id}", f"card:{frame_id}")
    parts = ["".join(r.text for p in sh.text_frame.paragraphs for r in p.runs)
             for sh in slide.shapes if str(sh.name).startswith(keys)]
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def main():
    prs = Presentation(str(DECK))
    spec = json.loads(SPEC.read_text())
    bodies = {}

    for fr in FRAMES:
        slide = prs.slides[fr["index"]]
        shapes = {str(s.name): s for s in slide.shapes}
        for name, (label, body), (x, y) in zip(block_names(slide, fr["id"]), fr["blocks"], POSITIONS):
            sh = shapes[name]
            write_block(sh, label, body)
            sh.left, sh.top = Pt(x), Pt(y)
            sh.width, sh.height = Pt(CARD_W), Pt(CARD_H)
        set_single_run(shapes[f"subtitle:{fr['id']}"], fr["subtitle"])
        set_single_run(shapes["slot_footer"], fr["footer"])

        body_lines = ["".join(r.text for p in sh.text_frame.paragraphs for r in p.runs).strip()
                      for sh in (shapes[n] for n in block_names(slide, fr["id"]))]
        note_body = "\n".join(f"- {line}" for line in body_lines)
        slide.notes_slide.notes_text_frame.text = "\n".join([
            f"Frame: {fr['title']}",
            "Owner block: RECALL",
            f"Frame id: {fr['id']}",
            "Target position: immediately after the outline." if fr["index"] == 2
            else "immediately after the background frame.",
            f"Note: {fr['note']}",
            f"<<<SLOT_BODY id={fr['id']}>>>",
            note_body,
            "<<<END_SLOT_BODY>>>",
        ])
        bodies[fr["id"]] = (note_body, fr)
        print(f"  frame {fr['index']} ({fr['id']}): 4 blocks, {len(note_body)} chars of notes, "
              f"subtitle {fr['subtitle']!r}")
        assert frame_text(slide, fr["id"]).count("\u2022") == 4

    prs.save(str(DECK))
    print("  deck saved")

    if not BACKUP.exists():
        BACKUP.write_bytes(SPEC.read_bytes())
        print(f"  scaffold backup: {BACKUP.name}")
    for fr_id, (note_body, fr) in bodies.items():
        hit = [f for f in spec["frames"] if f["id"] == fr_id]
        assert len(hit) == 1, (fr_id, len(hit))
        hit[0]["body"] = note_body
        hit[0]["footer"] = fr["footer"]
        hit[0]["subtitle"] = fr["subtitle"]
        hit[0]["note"] = fr["note"]
    indent = 2 if SPEC.read_text().startswith("{\n  \"") else 4
    SPEC.write_text(json.dumps(spec, indent=indent, ensure_ascii=False) + "\n")
    print(f"  scaffold: {len(bodies)} frames synced, {len(spec['frames'])} total")


if __name__ == "__main__":
    main()
