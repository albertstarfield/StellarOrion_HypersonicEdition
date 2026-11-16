#!/usr/bin/env python3
"""Undo the collateral note rewrite: restore every pre-existing frame's notes.

`rewrite_frame_notes.py` treated any notes that did not contain a body marker as
a placeholder, which swept up eleven frames that already had hand-written notes
in a different shape.  This script puts those notes back verbatim from the
backup taken before the three frames were inserted, and leaves alone only the
frames whose visible text genuinely changed:

  recall-issue-3-theorem   new frame
  recall-issue-check-3     new frame
  recall-issue-check-4     new frame
  recall-issue-check-1     its body now counts 59 frames instead of 56
  recall-previous-issues   the register now covers four elaborated issues

Frames are matched by frame id (shape name), not by slide index, because three
slides were inserted between the backup and now.

Usage: python tools/restore_preexisting_notes.py
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
DECK = HERE / "ProgressReport.pptx"
BACKUP = pathlib.Path.home() / "Downloads" / "ProgressReport_before_checks_3_4.pptx"

KEEP = {
    "recall-issue-3-theorem",
    "recall-issue-check-3",
    "recall-issue-check-4",
    "recall-issue-check-1",
    "recall-previous-issues",
}

SLOT = re.compile(r"(?:slot|subtitle):(?P<id>[a-z0-9-]+)")


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


def frame_id(slide):
    for shape in slide.shapes:
        m = SLOT.match(str(shape.name))
        if m:
            return m.group("id")
    return None


def main() -> int:
    from pptx import Presentation

    old = Presentation(str(BACKUP))
    new = Presentation(str(DECK))
    old_notes = {}
    for slide in old.slides:
        fid = frame_id(slide)
        if fid:
            old_notes[fid] = notes_of(slide)

    restored, kept = 0, 0
    for slide in new.slides:
        fid = frame_id(slide)
        if fid is None:
            continue
        if fid in KEEP:
            kept += 1
            print(f"  kept regenerated: {fid}")
            continue
        if fid not in old_notes:
            print(f"  no backup for {fid}; left as is")
            continue
        before = notes_of(slide)
        if before == old_notes[fid]:
            continue
        set_notes(slide, old_notes[fid])
        restored += 1
        print(f"  restored {fid}: {len(old_notes[fid])} chars")

    new.save(str(DECK))
    print(f"  restored {restored} frames, kept {kept} regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
