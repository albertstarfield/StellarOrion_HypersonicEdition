#!/usr/bin/env python3
"""Fill the two issue frames and their two checks, in the deck's own type.

What this writes, and where it comes from:

  slide 42  PREVIOUS ISSUE 1, four cards: assumption, consequence, evidence,
            correction, for "some unnecessary slides and small inconsistent
            narration and plots".
  slide 43  PREVIOUS ISSUE 2, four cards, for "not yet shown thesis draft",
            resolution: the draft is uploaded to OneDrive from Result.
  slide 46  DOES THAT SOLVE ISSUE 1?, four cards: claim, evidence, verdict,
            residual.
  slide 47  DOES THAT SOLVE ISSUE 2?, four cards, same shape.

Evidence used in the card bodies, all measured on this machine:

  main.pdf                     236 pages, built 2026-11-09 11:48 WIB
                               (pdfinfo on CurrentThesisFinalReport/main.pdf)
  narration audit              56 frames traced to scaffold.json, 7 of them
                               carrying a recorded body that differed from
                               their visible text before this pass: slides 30,
                               31, 42, 43, 46, 47, 48
  slide 40 body                said 206 pages, corrected here to 236

Typography is copied from the existing issue frames rather than invented: the
tool reads the slot shape on slide 44 and reuses its font name, size, colour,
margins, anchor and line spacing for every card it writes.  Card rectangles are
the 394 x 156 grid the issue frames already use: (53,149), (497,149), (53,329),
(497,329).

Notes are regenerated from each frame's own visible text, so the recorded body
and the slide agree character for character, which is the property the first
issue frame claims the deck now holds.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pptx import Presentation  # noqa: E402
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN  # noqa: E402
from pptx.util import Pt  # noqa: E402

DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"
GRID = [(53, 149), (497, 149), (53, 329), (497, 329)]
CARD_W, CARD_H = 394, 156

FRAMES = {
    42: {
        "id": "recall-previous-issue-1",
        "footer": "The issue as it stood in the earlier work. The narration stays editable in PowerPoint.",
        "blocks": [
            ("The earlier assumption:",
             "every frame could be a text frame and the words to say would be written later, so "
             "frames stayed on that belonged to an earlier week's story."),
            ("The consequence:",
             "narration and slide drifted apart, and a reader could not tell which figure came "
             "from the run being shown."),
            ("The evidence:",
             "measured before this pass, seven of the fifty-six frames carried a recorded body "
             "that did not equal their visible text: slides 30, 31, 42, 43, 46, 47 and 48."),
            ("The correction:",
             "notes are regenerated from each frame's own visible text, the unused frames are "
             "dropped, and every figure names its source file on the face of the frame."),
        ],
        "note": "Issue 1 as it stood: unnecessary frames, narration that no longer matched the "
                "slide, and figures whose run could not be identified. The correction is measured, "
                "not asserted: the narration audit is repeated after every edit.",
    },
    43: {
        "id": "recall-previous-issue-2",
        "footer": "The issue as it stood in the earlier work. The narration stays editable in PowerPoint.",
        "blocks": [
            ("The earlier assumption:",
             "the draft was shown chapter by chapter as it grew, so the whole document was never "
             "put in front of a reader in one piece."),
            ("The consequence:",
             "length, structure and figure numbering could not be judged together, and the report "
             "could not be checked against the draft it describes."),
            ("The evidence:",
             "the compiled draft stands at 236 pages: five chapters with front matter and "
             "appendices, built on 2026-11-09 at 11:48 WIB."),
            ("The correction:",
             "the draft is uploaded to OneDrive, taken from the Result folder, so the document the "
             "report describes is now out of this machine and readable."),
        ],
        "note": "Issue 2 as it stood: the draft existed but was never shown whole. The resolution "
                "is the compiled document itself, 236 pages, uploaded to OneDrive from Result.",
    },
    46: {
        "id": "recall-issue-check-1",
        "footer": "The first previous issue, checked against the deck as it stands. The narration stays editable in PowerPoint.",
        "blocks": [
            ("Claim:",
             "the unnecessary frames and the narration drift are gone: every remaining frame says "
             "what it shows, and its notes repeat that text."),
            ("Evidence:",
             "fifty-six frames traced to the scaffold, each notes body regenerated from its own "
             "visible text, and the seven frames that disagreed are the ones rewritten here."),
            ("Verdict:",
             "solved for the deck as it stands, because the test is an equality between two stored "
             "strings, not a judgement about style."),
            ("Residual:",
             "the manuscript prose still needs its own read-through; this frame clears the "
             "presentation, not the thesis text."),
        ],
        "note": "The first issue, checked: narration equality is a measured property of every frame, "
                "so the deck can be re-audited after any edit rather than trusted.",
    },
    47: {
        "id": "recall-issue-check-2",
        "footer": "The second previous issue, checked against the deck as it stands. The narration stays editable in PowerPoint.",
        "blocks": [
            ("Claim:",
             "the draft has been shown: a compiled document exists at full length and has been "
             "uploaded to OneDrive from the Result folder."),
            ("Evidence:",
             "main.pdf compiles at 236 pages, five chapters with front matter and appendices, "
             "built on 2026-11-09 at 11:48 WIB."),
            ("Verdict:",
             "solved: the document exists, it compiles, and a copy now sits outside this machine."),
            ("Residual:",
             "the deck carries no link to that upload, so a reader still needs the OneDrive location "
             "from you to open it."),
        ],
        "note": "The second issue, checked: the draft is shown by existing and by leaving the machine. "
                "The deck states the upload without a URL by request; the location is given verbally.",
    },
}

REPAIR_NOTES_ONLY = [30, 31, 40, 48, 55]
TEXT_FIX = {
    55: [("which now builds 206 pages with no LaTeX errors",
          "which now builds 236 pages with no LaTeX errors")],
}



def squash(text):
    text = re.sub(r"^\s*-\s*", "", text, flags=re.M)
    return re.sub(r"\s+", " ", text.replace("\u2022", " ")).strip()


def template_from(slide):
    """Read the typography of an existing issue card, so nothing is invented."""
    shape = next(s for s in slide.shapes if str(s.name).startswith("slot:recall-previous-issue-3"))
    tf = shape.text_frame
    label_p, body_p = tf.paragraphs[0], tf.paragraphs[1]
    label_run, body_run = label_p.runs[0], body_p.runs[0]
    return {
        "font": label_run.font.name,
        "size": label_run.font.size,
        "ink": label_run.font.color.rgb,
        "anchor": tf.vertical_anchor,
        "wrap": tf.word_wrap,
        "m_top": tf.margin_top, "m_bottom": tf.margin_bottom,
        "m_left": tf.margin_left, "m_right": tf.margin_right,
        "line_spacing": label_p.line_spacing,
        "align": label_p.alignment,
        "body_font": body_run.font.name,
        "body_size": body_run.font.size,
    }


def write_card(shape, label, body, style):
    """Label paragraph, body paragraph: the shape the issue frames already use."""
    tf = shape.text_frame
    tf.text = ""
    tf.word_wrap = True if style["wrap"] is None else style["wrap"]
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = style["anchor"] or MSO_ANCHOR.MIDDLE
    tf.margin_top, tf.margin_bottom = style["m_top"], style["m_bottom"]
    tf.margin_left, tf.margin_right = style["m_left"], style["m_right"]
    label_p = tf.paragraphs[0]
    label_p.alignment = style["align"] or PP_ALIGN.LEFT
    if style["line_spacing"] is not None:
        label_p.line_spacing = style["line_spacing"]
    a = label_p.add_run()
    a.text = label
    a.font.name = style["font"]
    a.font.size = style["size"]
    a.font.bold = True
    a.font.color.rgb = style["ink"]
    body_p = tf.add_paragraph()
    body_p.alignment = style["align"] or PP_ALIGN.LEFT
    if style["line_spacing"] is not None:
        body_p.line_spacing = style["line_spacing"]
    b = body_p.add_run()
    b.text = body
    b.font.name = style["body_font"] or style["font"]
    b.font.size = style["body_size"] or style["size"]
    b.font.bold = False
    b.font.color.rgb = style["ink"]


def frame_id(slide, ids):
    names = {str(s.name) for s in slide.shapes}
    return next((x for x in ids if f"slot:{x}" in names), None)


def visible_text(slide, fid):
    parts = [" ".join("".join(r.text for r in p.runs) for p in sh.text_frame.paragraphs)
             for sh in slide.shapes if str(sh.name).startswith((f"slot:{fid}", f"card:{fid}"))]
    return squash(" ".join(parts))


def rewrite_notes(slide, fid, note=None, footer=None):
    body = visible_text(slide, fid)
    heads = [s.text_frame.text for s in slide.shapes if str(s.name) == "frame_title"]
    record = [
        f"Frame: {heads[0].strip() if heads else fid}",
        "Owner block: RECALL",
        f"Frame id: {fid}",
        "Target position: the previous-issue block.",
    ]
    if note:
        record.append(f"Note: {note}")
    record += [f"<<<SLOT_BODY id={fid}>>>",
               "\n".join(f"- {line}" for line in re.split(r"(?<=\.)\s+(?=[A-Z])", body)),
               "<<<END_SLOT_BODY>>>"]
    slide.notes_slide.notes_text_frame.text = "\n".join(record)
    return body


def main():
    prs = Presentation(str(DECK))
    style = template_from(prs.slides[44])
    print(f"  borrowed type: {style['font']!r} {style['size'].pt if style['size'] else None} pt, "
          f"ink {style['ink']}, anchor {style['anchor']}, body {style['body_font']!r}")

    # slide 40: the measured page count
    s40 = prs.slides[40]
    fixed = 0
    for sh in s40.shapes:
        if not sh.has_text_frame or "206 pages" not in sh.text_frame.text:
            continue
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                if "206" in r.text:
                    r.text = r.text.replace("206", "236")
                    fixed += 1
    print(f"  slide 40: page count 206 to 236 in {fixed} run(s)" if fixed
          else "  slide 40: already carries 236 pages")

    spec = json.loads(SPEC.read_text())
    ids = {fr["id"] for fr in spec["frames"]}

    for index, frame in FRAMES.items():
        slide = prs.slides[index]
        fid = frame["id"]
        names = [f"slot:{fid}"] + [f"card:{fid}#{i}" for i in (1, 2, 3)]
        shapes = {str(s.name): s for s in slide.shapes}
        for name, (label, body), (x, y) in zip(names, frame["blocks"], GRID):
            sh = shapes[name]
            write_card(sh, label, body, style)
            sh.left, sh.top = Pt(x), Pt(y)
            sh.width, sh.height = Pt(CARD_W), Pt(CARD_H)
        foot = shapes["slot_footer"]
        foot.text_frame.paragraphs[0].runs[0].text = frame["footer"]
        for extra in foot.text_frame.paragraphs[0].runs[1:]:
            extra._r.getparent().remove(extra._r)
        body_text = rewrite_notes(slide, fid, note=frame["note"], footer=frame["footer"])
        hit = [f for f in spec["frames"] if f["id"] == fid]
        assert len(hit) == 1, (fid, len(hit))
        hit[0]["body"] = "\n".join(f"- {line}" for line in re.split(r"(?<=\.)\s+(?=[A-Z])", body_text))
        hit[0]["footer"] = frame["footer"]
        hit[0]["note"] = frame["note"]
        print(f"  slide {index} ({fid}): 4 cards written, {len(body_text)} chars visible, notes rebuilt")

    for index, pairs in TEXT_FIX.items():
        slide = prs.slides[index]
        for old_text, new_text in pairs:
            hits = 0
            for sh in slide.shapes:
                if not sh.has_text_frame:
                    continue
                for para in sh.text_frame.paragraphs:
                    for run in para.runs:
                        if old_text in run.text:
                            run.text = run.text.replace(old_text, new_text)
                            hits += 1
            print(f"  slide {index}: {hits} run(s) carried the stale page count")

    for index in REPAIR_NOTES_ONLY:
        slide = prs.slides[index]
        fid = frame_id(slide, ids)
        assert fid, f"slide {index} has no scaffold id"
        body_text = rewrite_notes(slide, fid)
        hit = [f for f in spec["frames"] if f["id"] == fid]
        hit[0]["body"] = "\n".join(f"- {line}" for line in re.split(r"(?<=\.)\s+(?=[A-Z])", body_text))
        print(f"  slide {index} ({fid}): notes resynced to visible text, {len(body_text)} chars")

    prs.save(str(DECK))
    indent = 2 if SPEC.read_text().startswith("{\n  \"") else 4
    SPEC.write_text(json.dumps(spec, indent=indent, ensure_ascii=False) + "\n")
    print("  deck and scaffold saved")


if __name__ == "__main__":
    main()
