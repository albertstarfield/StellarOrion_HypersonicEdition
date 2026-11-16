#!/usr/bin/env python3
"""Two claims on the theorem and check-3 frames were stronger than the sources.

Card 2 of the theorem frame called the flight gas "free-molecular and optically
thin". The thesis says the opposite about rarefaction: at 52 km the mean free
path is about 1.0e-4 m over a 3.0 m body, Kn ~ 3.4e-5, and the rarefaction that
matters is local to a shock layer with a millimetric gradient scale. It never
mentions optical thickness at all, so "optically thin" is a modelling
assumption rather than a computed fact.

The cards now say what is true: the Rosseland term is a volumetric
conductivity that needs an optically thick medium, and dropping it here is an
assumption that nothing in the thesis measures. The check-3 residual says so
explicitly instead of asserting a rarefaction regime the thesis does not claim.

Deck cards, scaffold bodies and speaker notes are rewritten together.

Usage: python tools/patch_theorem_honesty.py
"""
import json
import pathlib
import re
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent.parent
DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"

EDITS: list[dict[str, Any]] = [
    {
        "frame": "recall-issue-3-theorem",
        "card": "card:recall-issue-3-theorem#2",
        "old": ("the flux diffuses as q_rad = -k_R grad T, with k_R = 16*sigma*T^3/(3*kappa_R). "
                "A conductivity that grows as T^3, whose potential is (4*sigma/(3*kappa_R))*T^4. "
                "The DSMC gas is free-molecular and optically thin, so the term vanishes here."),
        "new": ("the flux diffuses as q_rad = -k_R grad T, with k_R = 16*sigma*T^3/(3*kappa_R), a volumetric "
                "conductivity rather than a wall flux. It holds only in an optically thick medium; the shock "
                "layer here is not, so the term is dropped."),
    },
    {
        "frame": "recall-issue-check-3",
        "card": "card:recall-issue-check-3#3",
        "old": ("No participating-medium radiation and no ablation: a Rosseland term would be needed only for "
                "an optically thick gas, which the free-molecular DSMC flow is not."),
        "new": ("No participating-medium radiation and no ablation. Dropping the Rosseland term is an assumption, "
                "not a measurement: the thesis computes no optical depth, and only the term's own validity "
                "condition is checked."),
    },
]


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
    spec_path = SPEC
    spec = json.loads(spec_path.read_text())
    by_id = {f["id"]: f for f in spec["frames"]}

    frames_touched: set[str] = set()
    for edit in EDITS:
        slide = next(s for s in prs.slides
                     if any(str(sh.name) == f"slot:{edit['frame']}" for sh in s.shapes))
        card = next(sh for sh in slide.shapes if str(sh.name) == edit["card"])
        target = None
        for para in _tf(card).paragraphs:
            text = "".join(r.text for r in para.runs)
            if text.strip() == edit["old"]:
                target = para
                break
        if target is None:
            print(f"  {edit['card']}: old text not found; skipping")
            continue
        target.runs[0].text = edit["new"]
        for run in target.runs[1:]:
            run._r.getparent().remove(run._r)
        frames_touched.add(edit["frame"])
        print(f"  {edit['card']}: {len(edit['old'])} -> {len(edit['new'])} chars")

    for fid in frames_touched:
        slide = next(s for s in prs.slides if any(str(sh.name) == f"slot:{fid}" for sh in s.shapes))
        frame = by_id[fid]
        body = visible_text(slide, fid)
        bullets = "\n".join(f"- {line}" for line in re.split(r"(?<=\.)\s+(?=[A-Z])", body))
        frame["body"] = bullets
        title = _tf(next(sh for sh in slide.shapes if str(sh.name) == "frame_title")).text.strip()
        notes = "\n".join([
            f"Frame: {title}",
            f"Owner block: {frame['section']}",
            f"Frame id: {fid}",
            f"Target position: {frame['target_position']}",
            f"Note: {frame['note']}",
            f"<<<SLOT_BODY id={fid}>>>",
            bullets,
            "<<<END_SLOT_BODY>>>",
        ])
        notes_frame = slide.notes_slide.notes_text_frame
        if notes_frame is None:
            print(f"  {fid}: no notes frame")
            continue
        notes_frame.text = notes
        print(f"  {fid}: notes and scaffold rebuilt ({len(body)} chars of visible text)")

    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    prs.save(str(DECK))
    print(f"  saved deck and scaffold; frames touched: {sorted(frames_touched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
