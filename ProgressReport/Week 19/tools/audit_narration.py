#!/usr/bin/env python3
"""Compare every frame's recorded narration against what the slide actually shows.

The deck keeps a copy of each frame's body inside its speaker notes, fenced by
`<<<SLOT_BODY id=...>>>` / `<<<END id=...>>>`.  That copy exists so the notes can
be read on their own; it drifts the moment somebody edits the slide and forgets
the notes.  This script is the drift detector.

Two readings are printed per frame:

  exact   -- the note body equals the visible text character for character
             after collapsing whitespace;
  relaxed -- the two agree once everything except letters and digits is dropped,
             which tolerates punctuation and separator drift.

A frame is reported as a mismatch only when the relaxed reading fails too; the
exact count is printed separately so a punctuation-only drift still shows up.

Usage: python tools/audit_narration.py
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"

BODY = re.compile(r"<<<SLOT_BODY id=(?P<id>[^>]+)>>>\n?(?P<body>.*?)<<<END_SLOT_BODY>>>", re.DOTALL)
ALNUM = re.compile(r"[^0-9a-z]+")


def squash(text: str) -> str:
    return " ".join(text.split())


def alnum(text: str) -> str:
    return ALNUM.sub("", text.lower())


def notes_of(slide) -> str:
    """Return a slide's notes text, or an empty string when it has none."""
    frame = slide.notes_slide.notes_text_frame if slide.has_notes_slide else None
    return frame.text if frame is not None else ""


def visible_text(slide, fid: str) -> str:
    parts = []
    for shape in slide.shapes:
        name = str(shape.name)
        if name == f"slot:{fid}" or name.startswith(f"card:{fid}#"):
            if getattr(shape, "has_text_frame", False):
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs)
                    if line.strip():
                        parts.append(line.strip())
    return squash(" ".join(parts))


def main() -> int:
    from pptx import Presentation

    prs = Presentation(str(DECK))
    spec = json.loads(SPEC.read_text())
    ids = [f["id"] for f in spec["frames"]]

    traced, exact, relaxed, bad = 0, 0, 0, []
    for index, slide in enumerate(prs.slides):
        names = {str(s.name) for s in slide.shapes}
        fid = next((i for i in ids if f"slot:{i}" in names), None)
        if fid is None:
            continue
        traced += 1
        notes = notes_of(slide)
        match = BODY.search(notes)
        if not match:
            bad.append((index, fid, "no recorded body"))
            continue
        body, shown = match.group("body"), visible_text(slide, fid)
        flat = squash(re.sub(r"(?m)^[-•]\s*", "", body))
        if flat == shown:
            exact += 1
            relaxed += 1
        elif alnum(body) == alnum(shown):
            relaxed += 1
        else:
            missing = [w for w in shown.split() if w not in body][:6]
            bad.append((index, fid, f"drift, first words not in notes: {missing}"))

    print(f"  scaffold frames: {len(ids)} | traced in deck: {traced}")
    print(f"  exact matches:   {exact}/{traced}")
    print(f"  relaxed matches: {relaxed}/{traced}")
    for index, fid, why in bad:
        print(f"    slide {index}: {fid} <- {why}")
    return 0 if not bad and traced == len(ids) else 1


if __name__ == "__main__":
    sys.exit(main())
