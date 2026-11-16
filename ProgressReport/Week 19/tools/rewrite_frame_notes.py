#!/usr/bin/env python3
"""Give the newly cloned frames the deck's own narration format.

Cloning a slide copies the speaker notes of the template, and the scaffold's
placeholder writer leaves the literal string "PLACEHOLDER SLIDE." at the top.
Both are wrong for a finished frame: the deck's convention is

    Frame: <title>
    Owner block: RECALL
    Frame id: <id>
    Target position: <where it sits>
    Note: <why the frame exists>
    <<<SLOT_BODY id=<id>>>
    - <sentence>
    - <sentence>
    <<<END_SLOT_BODY>>>

with the body regenerated from the slide's own visible text, so that the notes
can be read on their own and cannot drift from the frame.

Usage: python tools/rewrite_frame_notes.py [--dry-run]
"""
import json
import pathlib
import re
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent.parent
DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"

MARKER = re.compile(r"<<<SLOT_BODY id=(?P<id>[^>]+)>>>")
PLACEHOLDER = "PLACEHOLDER SLIDE"


def _tf(shape: Any) -> Any:
    """Return a shape's text frame without asking the type checker to guess."""
    return shape.text_frame


def squash(text: str) -> str:
    return " ".join(text.split())


def set_notes(slide, text: str) -> None:
    """Replace a slide's notes text, creating the notes slide if needed."""
    frame = slide.notes_slide.notes_text_frame
    if frame is None:
        raise RuntimeError("slide has no notes text frame")
    frame.text = text


def notes_of(slide) -> str:
    """Return a slide's notes text, or an empty string when it has none."""
    frame = slide.notes_slide.notes_text_frame if slide.has_notes_slide else None
    return frame.text if frame is not None else ""


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

    dry = "--dry-run" in sys.argv
    prs = Presentation(str(DECK))
    spec = json.loads(SPEC.read_text())
    by_id = {f["id"]: f for f in spec["frames"]}

    fixed = 0
    for index, slide in enumerate(prs.slides):
        names = {str(s.name) for s in slide.shapes}
        fid = next((i for i in by_id if f"slot:{i}" in names), None)
        if fid is None:
            continue
        notes = notes_of(slide)
        has_body = MARKER.search(notes) is not None
        if not notes.lstrip().startswith(PLACEHOLDER):
            continue
        frame = by_id[fid]
        title = next((_tf(s).text.strip() for s in slide.shapes
                      if str(s.name) == "frame_title"), fid)
        body = visible_text(slide, fid)
        record = [
            f"Frame: {title}",
            f"Owner block: {frame.get('section', 'RECALL')}",
            f"Frame id: {fid}",
            f"Target position: {frame.get('target_position', 'where it sits in the deck')}",
            f"Note: {frame.get('note', '')}",
            f"<<<SLOT_BODY id={fid}>>>",
            "\n".join(f"- {line}" for line in re.split(r"(?<=\.)\s+(?=[A-Z])", body)),
            "<<<END_SLOT_BODY>>>",
        ]
        if not dry:
            set_notes(slide, "\n".join(record))
        fixed += 1
        print(f"  slide {index}: {fid} -> {len(' '.join(record))} chars of notes, body {len(body)} chars")

    if not dry:
        prs.save(str(DECK))
    print(f"  {'would fix' if dry else 'fixed'}: {fixed} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
