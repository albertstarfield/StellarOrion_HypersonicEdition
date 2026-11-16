#!/usr/bin/env python3
"""Keep scaffold.json in step with the two new issue frames, and settle the notes.

The deck is generated from scaffold.json, so a frame that exists only in the
.pptx is a frame the next rebuild would lose.  Two entries are therefore added
right after `recall-previous-issue-2`, with the same shape as the two that are
already there (`cards_only`, `footer`, `subsection`), and the register entry's
note and target position are corrected: all four issues now have their own
frame.

The two GA frames also get the wording the implementation requires
(`BLX-alpha`, per-gene mutation), and the notes of frames 44 and 45 are rewritten
from the text that is actually on the slides, so the recorded provenance body and
the visible narration agree character for character.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pptx import Presentation  # noqa: E402

DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"
BACKUP = HERE / "scaffold.json.bak_before_issue_frames"

NEW_FRAMES = [
    {
        "id": "recall-previous-issue-3",
        "section": "RECALL",
        "title": "PREVIOUS ISSUE 3: THE FOURTH POWER IS THE RADIATIVE SINK",
        "target_position": "the slide right after the elaboration of the second issue, before the two checks.",
        "figure": None,
        "note": "Why the conduction frame carries a power of four. The frame solves the wall energy balance, "
                "the quartic term is the Stefan-Boltzmann re-radiation that sets the surface temperature, and "
                "its nonlinearity is what forces the bisection.",
        "cards_only": True,
        "footer": "Why the conduction frame carries a fourth power. The narration stays editable in PowerPoint.",
        "subsection": "Issues: Issue 3",
    },
    {
        "id": "recall-previous-issue-4",
        "section": "RECALL",
        "title": "PREVIOUS ISSUE 4: WHAT EACH GENETIC PARAMETER DOES",
        "target_position": "the slide right after the elaboration of the third issue, before the two checks.",
        "figure": None,
        "note": "What every genetic parameter does and why it holds that value: population, generation cap, "
                "tournament pressure, elitism, crossover operator and rate, mutation rate and step, "
                "convergence rule, fixed seed.",
        "cards_only": True,
        "footer": "Why each value and what it does; seed 42 keeps the campaign reproducible. "
                  "The narration stays editable in PowerPoint.",
        "subsection": "Issues: Issue 4",
    },
]

WORDING = [
    ("uniform crossover 0.7", "BLX-alpha crossover 0.7, alpha 0.5"),
    ("mutation with 0.1 on every gene", "each gene mutates with probability 0.1"),
]


def visible_cards(slide, frame_id):
    """Return [(label, body)] for the frame, in card order."""
    slots = [s for s in slide.shapes
             if str(s.name).startswith(f"slot:{frame_id}") or str(s.name).startswith(f"card:{frame_id}")]
    slots.sort(key=lambda s: (0 if str(s.name).startswith("slot:") else 1, str(s.name)))
    out = []
    for sh in slots:
        paras = sh.text_frame.paragraphs
        label = "".join(r.text for r in paras[0].runs).strip()
        body = " ".join("".join(r.text for r in p.runs).strip() for p in paras[1:]).strip()
        out.append((label, body))
    return out


def main():
    prs = Presentation(str(DECK))

    # 1. notes rewritten from the visible text
    for index, fr in ((44, NEW_FRAMES[0]), (45, NEW_FRAMES[1])):
        slide = prs.slides[index]
        cards = visible_cards(slide, fr["id"])
        assert len(cards) == 4, f"frame {index}: {len(cards)} cards"
        body = "\n".join(f"- {label} {text}" for label, text in cards)
        lines = [
            f"Frame: {fr['title']}",
            "Owner block: RECALL",
            f"Frame id: {fr['id']}",
            f"Target position: {fr['target_position']}",
            f"Note: {fr['note']}",
            f"<<<SLOT_BODY id={fr['id']}>>>",
            body,
            "<<<END_SLOT_BODY>>>",
        ]
        slide.notes_slide.notes_text_frame.text = "\n".join(lines)
        fr["body"] = body
        print(f"  frame {index}: notes rebuilt from {len(cards)} cards, {len(body)} chars")
    prs.save(str(DECK))

    # 2. scaffold entries
    if not BACKUP.exists():
        BACKUP.write_bytes(SPEC.read_bytes())
        print(f"  backup written: {BACKUP.name}")
    spec = json.loads(SPEC.read_text())
    frames = spec["frames"]
    ids = [f["id"] for f in frames]

    for fr in NEW_FRAMES:
        if fr["id"] in ids:
            print(f"  {fr['id']} already in the scaffold, not duplicating")
            continue
        anchor = ids.index("recall-previous-issue-2")
        entry = {k: fr[k] for k in
                 ("id", "section", "title", "body", "target_position", "figure", "note",
                  "cards_only", "footer", "subsection")}
        frames.insert(anchor + 1 + NEW_FRAMES.index(fr), entry)
        ids.insert(anchor + 1 + NEW_FRAMES.index(fr), fr["id"])
        print(f"  scaffold: inserted {fr['id']} at index {anchor + 1 + NEW_FRAMES.index(fr)}")

    for fr in frames:
        if fr["id"] == "recall-previous-issues":
            fr["note"] = ("The four issues as they stand. Each of the four is elaborated on the slides "
                          "that follow.")
            fr["target_position"] = ("the list of the four previous issues, right before the four slides "
                                     "that elaborate them.")
            print("  scaffold: register note and target position updated")
        body = fr.get("body") or ""
        for old, new in WORDING:
            if old in body:
                fr["body"] = body.replace(old, new)
                body = fr["body"]
                print(f"  scaffold: {fr['id']} wording fixed ({old[:34]!r})")

    indent = 2 if SPEC.read_text().startswith("{\n  \"") else 4
    SPEC.write_text(json.dumps(spec, indent=indent, ensure_ascii=False) + "\n")
    print(f"  scaffold saved: {len(frames)} frames, {SPEC.stat().st_size:,} bytes, indent={indent}")


if __name__ == "__main__":
    main()
