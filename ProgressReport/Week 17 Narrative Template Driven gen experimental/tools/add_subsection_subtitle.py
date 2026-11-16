#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Name the methodology subsection under the title of every slide of it.

WHY: the owner divides the methodology block into subsections for
elaboration. The first, "Methodology: DSMC CFD", is elaborated; the second,
"Methodology: Optimization Pipeline", is next. Nothing moves: each slide of
a subsection simply says which subsection it belongs to, in a line of its
own under the frame title inside the title band.

The script is a guarded replacement driver: it counts every anchor, refuses
to write when a count does not match, parses the result and leaves every file
untouched on any failure.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
GENERATOR = PROJECT / "make_pptx.py"
SPEC = PROJECT / "scaffold.json"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
GENERATOR_BACKUP = BACKUP_DIR / "make_pptx_before_subsection_label.py"
SPEC_BACKUP = BACKUP_DIR / "scaffold_before_subsection_label.json"
EM_DASH = "\u2014"

DSMC_SUBSECTION = "Methodology: DSMC CFD"
PIPELINE_SUBSECTION = "Methodology: Optimization Pipeline"
SUBSECTION_OF: dict[str, str] = {
    "recall-methodology-shape": DSMC_SUBSECTION,
    "recall-methodology-setup": DSMC_SUBSECTION,
    "recall-methodology-mesh": DSMC_SUBSECTION,
    "recall-methodology-convergence": DSMC_SUBSECTION,
    "recall-methodology-convection": DSMC_SUBSECTION,
    "recall-methodology-conduction": DSMC_SUBSECTION,
    "recall-methodology-radiation": DSMC_SUBSECTION,
    "recall-methodology-optimization": PIPELINE_SUBSECTION,
}

RULES: list[tuple[str, str, int]] = [
    # 1. the dataclass gains the field
    (
        ("        footer: The footer line of the slide, or an empty string when the\n"
        "            layout default is used.\n"),
        ("        footer: The footer line of the slide, or an empty string when the\n"
        "            layout default is used.\n"
        "        subsection: The methodology subsection this slide belongs to,\n"
        "            shown as a sub-title under the frame title.\n"),
        1,
    ),
    (
        '    cards_only: bool = False\n    footer: str = ""\n',
        '    cards_only: bool = False\n    footer: str = ""\n    subsection: str = ""\n',
        1,
    ),
    # 2. the loader reads it
    (
        ('        footer: object = entry.get("footer", "")\n'
        '        if not isinstance(footer, str):\n'
        '            failure_reason = f"frame \'{frame_id}\' needs a string footer"\n'
        "            raise ScaffoldError(failure_reason)\n"),
        ('        footer: object = entry.get("footer", "")\n'
        '        if not isinstance(footer, str):\n'
        '            failure_reason = f"frame \'{frame_id}\' needs a string footer"\n'
        "            raise ScaffoldError(failure_reason)\n"
        '        subsection: object = entry.get("subsection", "")\n'
        '        if not isinstance(subsection, str):\n'
        '            failure_reason = f"frame \'{frame_id}\' needs a string subsection"\n'
        "            raise ScaffoldError(failure_reason)\n"),
        1,
    ),
    (
        "                footer=footer.strip(),\n            ),",
        "                footer=footer.strip(),\n                subsection=subsection.strip(),\n            ),",
        1,
    ),
    # 3. the constants
    (
        "FRAME_TITLE_SIZE = Pt(24)\n",
        ("FRAME_TITLE_SIZE = Pt(24)\n"
        "#: The type size of the methodology sub-title drawn under the frame title.\n"
        "FRAME_SUBTITLE_SIZE = Pt(11)\n"
        "#: The height of the band the sub-title takes out of the title band.\n"
        "FRAME_SUBTITLE_BAND_IN = 0.24\n"),
        1,
    ),
    (
        'NAME_FRAME_TITLE = "frame_title"\n',
        'NAME_FRAME_TITLE = "frame_title"\nNAME_FRAME_SUBTITLE = "subtitle"\n',
        1,
    ),
    # 4. the header draws it, and the title gives up the band it needs
    (
        """    title = add_text_box(
        slide,
        MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        HEADER_CARD_TOP_IN,
        CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN - SECTION_CHIP_WIDTH_IN,
        HEADER_CARD_HEIGHT_IN,
        [frame.title],
        size=FRAME_TITLE_SIZE,
        font_name=TITLE_FONT,
        color=css_colour(palette, TITLE_TEXT_COLOR),
        bold=True,
        italic=False,
        vertical="middle",
    )
    title.name = NAME_FRAME_TITLE
""",
        """    # WHY: a slide that belongs to a methodology subsection says so under its
    # title, so the title box gives up the band the sub-title occupies and the
    # two are stacked inside the same plate instead of overlapping.
    title_height = HEADER_CARD_HEIGHT_IN
    if len(frame.subsection) != 0:
        title_height = HEADER_CARD_HEIGHT_IN - FRAME_SUBTITLE_BAND_IN
    title = add_text_box(
        slide,
        MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        HEADER_CARD_TOP_IN,
        CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN - SECTION_CHIP_WIDTH_IN,
        title_height,
        [frame.title],
        size=FRAME_TITLE_SIZE,
        font_name=TITLE_FONT,
        color=css_colour(palette, TITLE_TEXT_COLOR),
        bold=True,
        italic=False,
        vertical="middle",
    )
    title.name = NAME_FRAME_TITLE
    if len(frame.subsection) != 0:
        # WHY: the section chip ends above this band, so the sub-title can run
        # the full width of the plate and a long subsection name still fits.
        subtitle = add_text_box(
            slide,
            MARGIN_X_IN + GLASS_CARD_PADDING_IN,
            HEADER_CARD_TOP_IN + title_height,
            CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN,
            FRAME_SUBTITLE_BAND_IN,
            [frame.subsection],
            size=FRAME_SUBTITLE_SIZE,
            font_name=BODY_FONT,
            color=css_colour(palette, ACCENT_COLOR),
            bold=True,
            italic=False,
            vertical="middle",
        )
        subtitle.name = f"{NAME_FRAME_SUBTITLE}:{frame.id}"
""",
        1,
    ),
]


def main() -> int:
    """Add the subsection sub-title to the generator and to the spec.

    Returns:
        Zero when the generator and the specification were both patched,
        one when a guard refused.

    """
    problems: list[str] = []
    generator_text = GENERATOR.read_text(encoding="utf-8")
    for old, _new, expected in RULES:
        found = generator_text.count(old)
        if found != expected:
            problems.append(
                f"make_pptx.py: expected {expected} occurrence(s), found {found}: {old[:60]!r}",
            )
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    frames: list[dict[str, object]] = document["frames"]
    ids = {str(frame["id"]) for frame in frames}
    missing = [
        f"scaffold.json does not hold the frame '{frame_id}'"
        for frame_id in SUBSECTION_OF
        if frame_id not in ids
    ]
    problems.extend(missing)
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1

    for old, new, _expected in RULES:
        generator_text = generator_text.replace(old, new, 1)
    _ = ast.parse(generator_text)

    labelled = 0
    for frame in frames:
        frame_id = str(frame["id"])
        subsection = SUBSECTION_OF.get(frame_id)
        if subsection is None:
            continue
        if "subsection" in frame:
            _ = sys.stdout.write(f"MISMATCH the frame '{frame_id}' already carries a subsection\n")
            return 1
        frame["subsection"] = subsection
        labelled += 1
    spec_text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    for name, text in (("the generator", generator_text), ("the specification", spec_text)):
        if EM_DASH in text:
            _ = sys.stdout.write(f"MISMATCH {name} would carry an em dash\n")
            return 1

    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _ = GENERATOR_BACKUP.write_bytes(GENERATOR.read_bytes())
    _ = SPEC_BACKUP.write_bytes(SPEC.read_bytes())
    _ = GENERATOR.write_text(generator_text, encoding="utf-8")
    _ = SPEC.write_text(spec_text, encoding="utf-8")
    _ = sys.stdout.write(
        f"the sub-title of the subsection is drawn on {labelled} slides: "
        f"{DSMC_SUBSECTION} and {PIPELINE_SUBSECTION}\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
