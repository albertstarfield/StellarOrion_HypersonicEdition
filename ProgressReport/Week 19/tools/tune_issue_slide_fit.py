#!/usr/bin/env python3
"""Make the four card bodies on each new issue frame sit inside their cards.

The cloned text boxes carried `normAutofit` (SHAPE_TO_FIT_TEXT), so PowerPoint
grew the box to fit the paragraph and the last line walked out of the card and
over the footer (measured on the export: 20.3 pt below the panel on frame 44).
Turning autofit off and giving the box the card's inner rectangle with a middle
anchor makes the text centre in the card instead, and a line spacing of 1.0 buys
roughly two more lines of room.

Two bodies are shortened at the same time, because at 16 pt over 6.07 in a card
holds about 7 lines and these were longer.  The text stays factual: nothing is
dropped except wording.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pptx import Presentation  # noqa: E402
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE  # noqa: E402
from pptx.util import Inches  # noqa: E402

DECK = HERE / "ProgressReport.pptx"
BACKUP = HERE / "ProgressReport.pptx.bak_before_fit_pass"

TRIMS = {
    44: [
        ("Fourier is linear, the sink is quartic, so no linear solve closes the balance. "
         "The slope 1/R + 4*eps*sigma*T^3 + G is strictly positive, so the root is unique "
         "and a bisection finds it.",
         "Fourier is linear, the sink quartic, so no linear solve closes the balance. The slope "
         "1/R + 4*eps*sigma*T^3 + G stays positive, so the root is unique and bisection finds it."),
    ],
    45: [
        ("The best of three random designs wins, so the best design is chosen with probability "
         "k/n = 3/50 = 6 % per draw, against 2 % at k = 1 and 100 % at k = 50: pressure enough "
         "to climb, mild enough to keep diversity. Two elites are copied untouched, so the best "
         "cost cannot regress.",
         "The best of three random designs wins, so the best design is chosen with probability "
         "k/n = 3/50 = 6 % per draw against 2 % at k = 1 and 100 % at k = 50: enough pressure to "
         "climb, mild enough to keep diversity. Two elites are copied untouched."),
        ("Fifty is ten times the five design variables and a quarter of the 200-individual cap. "
         "The campaign stopped on stagnation at generation 38, so it spent 50 x 38 = 1,900 "
         "evaluations, which is the budget the DSMC campaign had.",
         "Fifty is ten times the five design variables and a quarter of the 200-individual cap. "
         "The campaign stopped on stagnation at generation 38, so it spent 50 x 38 = 1,900 "
         "evaluations, the budget the DSMC campaign had."),
    ],
}

FRAME_IDS = {44: "recall-previous-issue-3", 45: "recall-previous-issue-4"}


def main():
    if not BACKUP.exists():
        BACKUP.write_bytes(DECK.read_bytes())
        print(f"  backup written: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")
    prs = Presentation(str(DECK))

    for index, replacements in TRIMS.items():
        slide = prs.slides[index]
        done = 0
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            for p in sh.text_frame.paragraphs:
                joined = "".join(r.text for r in p.runs)
                for old, new in replacements:
                    if old in joined:
                        p.runs[0].text = joined.replace(old, new)
                        for r in list(p.runs)[1:]:
                            r.text = ""
                        done += 1
                        joined = p.runs[0].text
        print(f"  frame {index}: {done} body paragraph(s) shortened")

    for index, fid in FRAME_IDS.items():
        slide = prs.slides[index]
        tuned = 0
        for sh in slide.shapes:
            name = str(sh.name)
            if not (name.startswith(f"slot:{fid}") or name.startswith(f"card:{fid}")):
                continue
            tf = sh.text_frame
            tf.auto_size = MSO_AUTO_SIZE.NONE
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            top_row = sh.top < Inches(4.0)
            sh.top = Inches(2.07) if top_row else Inches(4.57)
            sh.height = Inches(2.16)
            for p in tf.paragraphs:
                p.line_spacing = 1.0
            tuned += 1
        print(f"  frame {index}: autofit off, anchored, single spacing on {tuned} boxes")

    prs.save(str(DECK))
    print(f"  saved: {DECK.stat().st_size:,} bytes, {len(Presentation(str(DECK)).slides)} slides")


if __name__ == "__main__":
    main()
