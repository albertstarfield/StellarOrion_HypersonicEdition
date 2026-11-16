#!/usr/bin/env python3
"""Restore the builder's provenance record for the Week 19 register frame.

WHY: the register was hand-edited with python-pptx, which overwrote the speaker
notes and so destroyed the ``<<<SLOT_BODY id=recall-previous-issues>>>`` record
the generator uses to tell an untouched slot from an owner-written one.  Without
it the frame is frozen: every future ``make_pptx.py --mode update`` sees
"no provenance record, so the visible text is kept" for ever.

This script does not invent the format.  It imports the generator itself and
calls the generator's own ``_write_notes``, so the notes come out byte-identical
to what a build writes, and it then reads the record back with the generator's
own ``_recorded_body`` to prove the round trip.

Run it with the tool's own interpreter: ``.venv/bin/python`` (easypptx lives there).
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import make_pptx as M  # noqa: E402
from easypptx import Slide as EasySlide  # noqa: E402
from pptx import Presentation  # noqa: E402

FRAME_ID = "recall-previous-issues"
DECK = HERE / "ProgressReport.pptx"

spec = M.load_spec(HERE / "scaffold.json")
frame = next(f for f in spec.frames if f.id == FRAME_ID)
body = frame.body
print(f"[spec]   body has {len(body.splitlines())} lines")
for line in body.splitlines():
    print(f"         - {line.lstrip('- ')[:96]}")

prs = Presentation(str(DECK))
slide = prs.slides[41]

before = M._recorded_body(EasySlide(slide), frame)
print(f"[before] recorded body readable by the tool: {before is not None}")

M._write_notes(EasySlide(slide), frame, body)
prs.save(str(DECK))

prs2 = Presentation(str(DECK))
slide2 = EasySlide(prs2.slides[41])
after = M._recorded_body(slide2, frame)
current = M._narration_text(M._collect_narration_shapes(slide2, frame.id))
same = M._normalise_body(current) == M._normalise_body(after or "")

print(f"[after]  recorded body readable: {after is not None}")
print(f"[after]  visible text == recorded text: {same}")
print(f"[after]  notes lines: {len(slide2.notes.splitlines())}")
print("--- notes ---")
for line in slide2.notes.splitlines():
    print("   ", line[:120])
