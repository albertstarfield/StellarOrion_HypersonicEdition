#!/usr/bin/env python3
"""Tighten the theorem frame's second card and keep its notes in step.

The card used to read "q_rad = -(16*sigma*T^3/(3*kappa_R))*grad T", which
PowerPoint broke immediately after the minus sign, leaving a line that ends in
a bare "-".  Restating the same law as a conductivity, q_rad = -k_R grad T with
k_R = 16*sigma*T^3/(3*kappa_R), gives the line breaker a space to work with and
says the thing the frame is about more directly.

The card text, the scaffold's matching bullet and the speaker notes are all
rewritten together, so the narration audit stays exact.

Usage: python tools/tighten_theorem_card.py
"""
import json
import pathlib
import re
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent.parent
DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"
FRAME_ID = "recall-issue-3-theorem"

OLD_BULLET = ("- When radiation does join the conduction term: ")
NEW_CARD = (
    "When radiation joins the conduction term:"
)
NEW_BODY = (
    "the flux diffuses as q_rad = -k_R grad T, with k_R = 16*sigma*T^3/(3*kappa_R). "
    "A conductivity that grows as T^3, whose potential is (4*sigma/(3*kappa_R))*T^4. "
    "The DSMC gas is free-molecular and optically thin, so the term vanishes here."
)


def _tf(shape: Any) -> Any:
    """Return a shape's text frame without asking the type checker to guess."""
    return shape.text_frame


def squash(text: str) -> str:
    return " ".join(text.split())


def visible_text(slide, fid: str) -> str:
    parts = []
    for shape in slide.shapes:
        name = str(shape.name)
        if (name == f"slot:{fid}" or name.startswith(f"card:{fid}#")) and getattr(shape, "has_text_frame", False):
            for para in shape.text_frame.paragraphs:
                line = "".join(run.text for run in para.runs).strip()
                if line:
                    parts.append(line)
    return squash(" ".join(parts))


def main() -> int:
    from pptx import Presentation

    prs = Presentation(str(DECK))
    slide = next(s for s in prs.slides
                 if any(str(sh.name) == f"slot:{FRAME_ID}" for sh in s.shapes))

    card = next(sh for sh in slide.shapes if str(sh.name) == f"card:{FRAME_ID}#2")
    paras = list(_tf(card).paragraphs)
    lead = "".join(r.text for r in paras[0].runs)
    paras[0].runs[0].text = NEW_CARD
    for r in paras[0].runs[1:]:
        r._r.getparent().remove(r._r)
    paras[1].runs[0].text = NEW_BODY
    for r in paras[1].runs[1:]:
        r._r.getparent().remove(r._r)
    print(f"  card lead : {lead!r} -> {NEW_CARD!r}")
    print(f"  card body : {NEW_BODY[:70]}...")

    spec = json.loads(SPEC.read_text())
    frame = next(f for f in spec["frames"] if f["id"] == FRAME_ID)
    bullets = frame["body"].split("\n")
    matches = [i for i, b in enumerate(bullets) if b.startswith(OLD_BULLET)]
    if len(matches) != 1:
        print(f"  scaffold bullet not found once ({len(matches)} hits); aborting")
        return 1
    bullets[matches[0]] = "- " + NEW_CARD + " " + NEW_BODY
    frame["body"] = "\n".join(bullets)
    SPEC.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    print(f"  scaffold bullet {matches[0]} rewritten")

    body = visible_text(slide, FRAME_ID)
    notes = "\n".join([
        f"Frame: {_tf(next(sh for sh in slide.shapes if str(sh.name) == 'frame_title')).text.strip()}",
        f"Owner block: {frame['section']}",
        f"Frame id: {FRAME_ID}",
        f"Target position: {frame['target_position']}",
        f"Note: {frame['note']}",
        f"<<<SLOT_BODY id={FRAME_ID}>>>",
        "\n".join(f"- {line}" for line in re.split(r"(?<=\.)\s+(?=[A-Z])", body)),
        "<<<END_SLOT_BODY>>>",
    ])
    frame_notes = slide.notes_slide.notes_text_frame
    if frame_notes is None:
        print("  slide has no notes frame; aborting")
        return 1
    frame_notes.text = notes
    print(f"  notes rebuilt from {len(body)} characters of visible text")

    prs.save(str(DECK))
    print("  saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
