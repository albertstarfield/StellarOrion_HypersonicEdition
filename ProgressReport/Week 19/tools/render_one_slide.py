#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Lift one slide of the deck into its own single-slide package.

WHY: the quick-look renderer only ever draws the FIRST slide of a package,
so a slide has to be cut into a package of its own before it can be rendered
and read back as an image. The old helper lived in a temp folder and was
wiped with it, so this one lives in the project folder next to the deck it
renders.

The package is a copy of the deck with the section list removed, every slide
relationship but one dropped, and the notes slide of the kept slide dropped
too: a package that still references a notes slide hangs the renderer.

The deck itself is only ever read, never written.

Usage:
    python tools/render_one_slide.py narrative_scaffold.pptx tools/render 13 15

Then, one file at a time (batching produces nothing):
    qlmanage -t -s 1600 -o <png-dir> <png-dir>/slide13.pptx
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

#: The block that lists the PowerPoint sections; it names slides by id.
SECTION_LIST = re.compile(rb"<p14:sectionLst>.*?</p14:sectionLst>", re.DOTALL)
#: One Relationship element of a .rels part.
SOLID_REF = re.compile(r"<Relationship\b[^>]*/>")
#: A Relationship that points at a slide of the presentation.
SLIDE_REF = re.compile(r'Id="(rId\d+)"[^>]*Target="slides/(slide\d+)\.xml"')
#: A Relationship of a slide that points at its notes slide.
NOTES_REF = re.compile(r'Target="\.\./notesSlides/([^"]+)"')


def build_one_slide(source: Path, target: Path, wanted: int) -> None:
    """Write a copy of `source` that holds only the slide `wanted`.

    WHY: the renderer draws the first slide of a package, so every slide but
    one has to leave the package, and the notes slide of the one that stays
    has to leave with them or the renderer hangs.

    Args:
        source: The deck to read.
        target: The single-slide package to write.
        wanted: The one-based number of the slide that must remain.

    Raises:
        ValueError: When the deck does not hold the requested slide.
    """
    _ = shutil.copyfile(source, target)
    with zipfile.ZipFile(target) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}

    keep = f"slide{wanted}"
    if f"ppt/slides/{keep}.xml" not in parts:
        missing = f"the deck holds no {keep}.xml"
        raise ValueError(missing)

    presentation = SECTION_LIST.sub(b"", parts["ppt/presentation.xml"])
    rels_text = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    for entry in SOLID_REF.findall(rels_text):
        match = SLIDE_REF.search(entry)
        if match is None or match.group(2) == keep:
            continue
        rel_id = match.group(1).encode("ascii")
        slide_id = re.compile(
            rb'<p:sldId\b[^>]*r:id="' + rel_id + rb'"[^>]*/>',
        )
        presentation = slide_id.sub(b"", presentation)
        rels_text = rels_text.replace(entry, "")

    # WHY: a package whose kept slide still points at a notes slide makes the
    # renderer hang for ever, and the notes are not what is being looked at.
    slide_rels_name = f"ppt/slides/_rels/{keep}.xml.rels"
    if slide_rels_name in parts:
        slide_rels = parts[slide_rels_name].decode("utf-8")
        for entry in SOLID_REF.findall(slide_rels):
            if "notesSlide" not in entry:
                continue
            note = NOTES_REF.search(entry)
            if note is None:
                continue
            slide_rels = slide_rels.replace(entry, "")
            _ = parts.pop(f"ppt/notesSlides/{note.group(1)}", None)
            _ = parts.pop(f"ppt/notesSlides/_rels/{note.group(1)}.rels", None)
        parts[slide_rels_name] = slide_rels.encode("utf-8")

    parts["ppt/presentation.xml"] = presentation
    parts["ppt/_rels/presentation.xml.rels"] = rels_text.encode("utf-8")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def main() -> int:
    """Cut the requested slides of a deck into single-slide packages.

    Returns:
        0 when every requested slide was cut, 1 when the deck does not hold
        one of the requested slide numbers.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("deck", type=Path, help="the deck to read")
    _ = parser.add_argument("outdir", type=Path, help="the folder to write")
    _ = parser.add_argument("slides", type=int, nargs="+", help="the slide numbers")
    args = parser.parse_args()
    deck: Path = args.deck
    outdir: Path = args.outdir
    numbers: list[int] = list(args.slides)
    _ = outdir.mkdir(parents=True, exist_ok=True)
    for number in numbers:
        target: Path = outdir / f"slide{number:02d}.pptx"
        try:
            build_one_slide(deck, target, number)
        except ValueError as error:
            _ = sys.stdout.write(f"FAILED {error}\n")
            return 1
        _ = sys.stdout.write(f"cut slide {number} into {target}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
