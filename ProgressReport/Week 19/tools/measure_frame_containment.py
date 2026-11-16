#!/usr/bin/env python3
"""Measure whether a frame's text fits the boxes it was written into.

Reads the exported PDF (pdftotext -bbox-layout, one page per slide), takes the
slot and card rectangles from the .pptx, assigns every rendered line to the box
whose vertical band and horizontal span contain it, and reports for each box:

  lines      how many rendered lines landed in it
  complete   whether the joined text equals the text stored in the shape
  inside     whether every line sits within the box (no spill, no clipping)
  clearance  points between the lowest line and the box bottom

Hyphenated line breaks ("5-\\nspecies") are joined before comparison, because
the break is typography rather than content.

Usage:
  measure_frame_containment.py --pdf deck.pdf --page 3 --frame recall-latar-belakang
  measure_frame_containment.py --pdf deck.pdf --page 45 --frame recall-previous-issue-3
"""
import argparse
import html
import re

from pptx import Presentation
from pptx.util import Emu

BBOX_LINE = re.compile(
    r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)
BBOX_WORD = re.compile(r"<word[^>]*>(.*?)</word>", re.S)
BULLET = "\u2022"


def squash(text):
    text = text.replace(BULLET, " ")
    text = re.sub(r"-\s+", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def boxes(deck, index, frame_id):
    prs = Presentation(str(deck))
    slide = prs.slides[index]
    names = [f"slot:{frame_id}"] + [f"card:{frame_id}#{i}" for i in (1, 2, 3, 4, 5)]
    out = []
    for name in names:
        shape = next((s for s in slide.shapes if str(s.name) == name), None)
        if shape is None:
            continue
        text = " ".join("".join(r.text for r in p.runs) for p in shape.text_frame.paragraphs)
        out.append((name, Emu(shape.left).pt, Emu(shape.top).pt, Emu(shape.width).pt,
                    Emu(shape.height).pt, squash(text)))
    return out


def rendered_lines(bbox_html, page_number):
    doc = open(bbox_html, encoding="utf-8").read()
    pages = re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', doc, re.S)
    body = pages[page_number - 1][2]
    lines = []
    for m in BBOX_LINE.finditer(body):
        text = html.unescape(" ".join(BBOX_WORD.findall(m.group(5)))).strip()
        if text:
            lines.append((float(m.group(1)), float(m.group(2)), float(m.group(3)),
                          float(m.group(4)), text))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="exported PDF")
    ap.add_argument("--bbox", required=True, help="pdftotext -bbox-layout html")
    ap.add_argument("--deck", default="ProgressReport.pptx")
    ap.add_argument("--page", type=int, required=True, help="1-based PDF page")
    ap.add_argument("--frame", required=True, help="frame id")
    ap.add_argument("--index", type=int, help="0-based slide index (default page-1)")
    args = ap.parse_args()

    index = args.index if args.index is not None else args.page - 1
    lines = rendered_lines(args.bbox, args.page)
    problems = 0
    for name, x, y, w, h, expected in boxes(args.deck, index, args.frame):
        mine = [l for l in lines
                if l[0] >= x - 8 and l[2] <= x + w + 8 and y - 6 <= (l[1] + l[3]) / 2 <= y + h + 3]
        got = squash(" ".join(l[4] for l in mine))
        top = min((l[1] for l in mine), default=None)
        bottom = max((l[3] for l in mine), default=None)
        complete = got == expected
        inside = bottom is not None and top >= y - 1 and bottom <= y + h + 1
        problems += 0 if (complete and inside) else 1
        print(f"  {name}: {len(mine)} lines, complete {complete}, inside {inside}, "
              f"clearance {y + h - bottom:+.1f} pt")
        if not complete:
            print(f"    want: {expected[-90:]!r}")
            print(f"    got : {got[-90:]!r}")
    print(f"  verdict: {len(boxes(args.deck, index, args.frame)) - problems} of "
          f"{len(boxes(args.deck, index, args.frame))} boxes hold their text")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
