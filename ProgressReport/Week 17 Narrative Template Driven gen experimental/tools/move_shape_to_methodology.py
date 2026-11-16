#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Give the scope slide an overview picture and the shape a methodology slide.

WHY: the owner does not want the meridional half-section on the objective and
scope slide, because that drawing is the methodology answer to "what shape
are we testing against". The scope slide therefore takes the thesis picture of
the HIAD as an overview, and the half-section moves to a new methodology slide
that sits immediately before the simulation setup.

The script is a guarded driver: it verifies the copy of the picture with a
hash, counts every anchor, measures the new point cards and the two captions
before writing, refuses to write a file that carries an em dash, parses the
test file and leaves every file untouched when a single check fails.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import cast

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

REPO = PROJECT.parents[2]
SOURCE_PICTURE = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/Hiad_DesignSpec.png"
TARGET_PICTURE = PROJECT / "figures" / "thesis_hiad_design_spec.png"
SPEC = PROJECT / "scaffold.json"
TESTS = PROJECT / "tests" / "test_make_pptx.py"
README = PROJECT / "README.md"
FIGURES_README = PROJECT / "figures" / "README.md"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
EM_DASH = "\u2014"

SCOPE_ID = "recall-tujuan-scope"
SHAPE_ID = "recall-methodology-shape"
ANCHOR_BEFORE = "recall-methodology-setup"
SHAPE_TITLE = "METHODOLOGY: THE SHAPE UNDER TEST"

SCOPE_SOURCE = (
    "Source: Hiad_DesignSpec.png from CurrentThesisFinalReport/figures, the vehicle "
    "specification drawing of Chapter III."
)
SCOPE_CAPTION = (
    "The HIAD as an overview: the inflatable aeroshell against the rigid body it replaces, "
    "as the thesis draws it."
)
SHAPE_CAPTION = (
    "Meridional half-section of the HIAD: the nose arc tangent to the cone generator and the "
    "six toroidal bladders T1 to T6."
)
SHAPE_SOURCE = (
    "Source: hiad_parametric_cross_section.png from CurrentThesisFinalReport/figures, written "
    "by figures/make_hiad_parametric_cross_section.py."
)
SHAPE_BODY = (
    "- Nose arc tangent to the cone generator: R_N 0.55 m at a half-cone angle of 60 degrees\n"
    "- Six toroidal bladders T1 to T6 of radius 0.135 m march up the cone\n"
    "- The stack reaches R_max 1.90 m over a body length of 1.269 m\n"
    "- The skin aft of the nose tangent is omitted so that the stack stays visible"
)
SHAPE_FOOTER = "The shape the method tests. The narration stays editable in PowerPoint."
SHAPE_TARGET = (
    "the slide right after the optimization flowchart and before the simulation setup, showing "
    "the shape the method tests."
)
SHAPE_NOTE = (
    "The shape under test: the parametric half-section with its nose arc, its six toroidal "
    "bladders and the parameter box of the baseline."
)

TEST_RULES: list[tuple[str, str, int]] = [
    ("EXPECTED_FRAME_COUNT = 23", "EXPECTED_FRAME_COUNT = 24", 1),
    ("EXPECTED_METHODOLOGY_FRAME_COUNT = 7", "EXPECTED_METHODOLOGY_FRAME_COUNT = 8", 1),
    ("EXPECTED_FILLED_FRAME_COUNT = 12", "EXPECTED_FILLED_FRAME_COUNT = 13", 1),
    (
        '        "recall-methodology-optimization",\n    }',
        f'        "recall-methodology-optimization",\n        "{SHAPE_ID}",\n    }}',
        1,
    ),
]

README_RULES: list[tuple[str, str, int]] = [
    (
        "the owner's block structure, the twenty-three frames",
        "the owner's block structure, the twenty-four frames",
        1,
    ),
    ("Generated PowerPoint deck (25 slides).", "Generated PowerPoint deck (26 slides).", 1),
    ("* 25 slides, 16:9", "* 26 slides, 16:9", 1),
    (
        "* Slide 1 is the cover, slide 2 the outline, slides 3 to 25 the twenty-three\n  frames.",
        "* Slide 1 is the cover, slide 2 the outline, slides 3 to 26 the twenty-four\n  frames.",
        1,
    ),
    (
        "the seven methodology slides and their figures",
        "the eight methodology slides and their figures",
        1,
    ),
    (
        (
            "| 3. Methodology (how the simulation is set up) | `RECALL` | "
            "`METHODOLOGY: THE SIMULATION SETUP` |"
        ),
        (
            "| 3. Methodology (the shape the method tests) | `RECALL` | "
            f"`{SHAPE_TITLE}` |\n"
            "| 3. Methodology (how the simulation is set up) | `RECALL` | "
            "`METHODOLOGY: THE SIMULATION SETUP` |"
        ),
        1,
    ),
]

FIGURES_RULES: list[tuple[str, str, int]] = [
    (
        (
            "| `OBJECTIVE AND RESEARCH SCOPE` | `thesis_hiad_parametric_cross_section.png` | "
            "Chapter II |"
        ),
        (
            "| `OBJECTIVE AND RESEARCH SCOPE` | `thesis_hiad_design_spec.png` | Chapter III, "
            "the vehicle specification drawing `Hiad_DesignSpec.png` | The HIAD as an overview: "
            "the inflatable aeroshell against the rigid body it replaces, labelled 15 m "
            "inflatable and 4.57 m rigid. MOVED HERE ON 2026-10-26: the meridional "
            "half-section that used to sit on this slide went to the methodology slide below, "
            "because it answers which shape is being tested. |\n"
            f"| `{SHAPE_TITLE}` | `thesis_hiad_parametric_cross_section.png` | Chapter II |"
        ),
        1,
    ),
]


def digest(path: Path) -> str:
    """Return the SHA-256 of a file.

    Args:
        path: The file to hash.

    Returns:
        The hexadecimal digest of the file.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_measurements() -> list[str]:
    """Return every geometry problem that would stop the script.

    Returns:
        The problems found, empty when everything fits.
    """
    import make_pptx as maker  # ruff: ignore[import-outside-top-level]

    problems: list[str] = []
    if not SOURCE_PICTURE.is_file():
        problems.append(f"the thesis picture is missing: {SOURCE_PICTURE}")
        return problems

    inner_width = maker.CONTENT_WIDTH_IN - 2.0 * maker.FILLED_FIGURE_PADDING_IN
    area_height = maker.FILLED_CARD_HEIGHT_IN - 2.0 * maker.FILLED_FIGURE_PADDING_IN
    picture_width = min(
        maker.SIDE_POINTS_PICTURE_WIDTH_IN,
        inner_width - maker.SIDE_POINTS_COLUMN_MIN_IN - maker.SIDE_POINTS_GUTTER_IN,
    )
    column_width = inner_width - picture_width - maker.SIDE_POINTS_GUTTER_IN
    source_height = maker._source_box_height(SHAPE_SOURCE, column_width)  # ruff: ignore[private-member-access]
    caption_lines = SHAPE_CAPTION.splitlines()
    caption_height = (
        len(caption_lines) * maker.line_height_inches(maker.BODY_FONT, maker.SIDE_POINTS_CAPTION_PT)
        + maker.FILLED_SOURCE_GAP_IN
    )
    available = area_height - caption_height - maker.FILLED_SOURCE_GAP_IN - source_height
    points = tuple(line.removeprefix("- ") for line in SHAPE_BODY.split("\n"))
    size, _heights = maker._side_points_plan(  # ruff: ignore[private-member-access]
        points, maker.BODY_FONT, column_width, available,
    )
    if size < maker.SIDE_POINTS_TEXT_START_PT:
        problems.append(f"the new point cards would drop to {size} pt in a {column_width:.2f} in column")

    scope_width = maker.FILLED_CAPTION_COLUMN_WIDTH_IN
    scope_lines = maker.wrap_line_count(SCOPE_CAPTION, maker.BODY_FONT, maker.FILLED_CAPTION_SIZE.pt, scope_width)
    scope_needed = scope_lines * maker.line_height_inches(maker.BODY_FONT, maker.FILLED_CAPTION_SIZE.pt)
    if scope_needed > maker.FILLED_CAPTION_HEIGHT_IN:
        problems.append(f"the scope caption needs {scope_needed:.2f} in of {maker.FILLED_CAPTION_HEIGHT_IN} in")
    source_lines = maker.wrap_line_count(SCOPE_SOURCE, maker.BODY_FONT, maker.FILLED_SOURCE_SIZE.pt, scope_width)
    source_needed = source_lines * maker.line_height_inches(maker.BODY_FONT, maker.FILLED_SOURCE_SIZE.pt)
    if source_needed > maker.FILLED_SOURCE_HEIGHT_IN:
        problems.append(f"the scope source needs {source_needed:.2f} in of {maker.FILLED_SOURCE_HEIGHT_IN} in")
    return problems


def check_anchors() -> list[str]:
    """Return every anchor of the test file and the two README files that is missing.

    Returns:
        The problems found, empty when every anchor matches its count.
    """
    problems: list[str] = []
    tests_text = TESTS.read_text(encoding="utf-8")
    for old, _new, expected in TEST_RULES:
        found = tests_text.count(old)
        if found != expected:
            problems.append(f"tests/test_make_pptx.py: expected {expected} found {found}: {old[:50]!r}")
    readme_text = README.read_text(encoding="utf-8")
    for old, _new, expected in README_RULES:
        found = readme_text.count(old)
        if found != expected:
            problems.append(f"README.md: expected {expected} found {found}: {old[:50]!r}")
    figures_text = FIGURES_README.read_text(encoding="utf-8")
    for old, _new, expected in FIGURES_RULES:
        found = figures_text.count(old)
        if found != expected:
            problems.append(f"figures/README.md: expected {expected} found {found}: {old[:50]!r}")
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    frames = cast("list[dict[str, object]]", document["frames"])
    ids = [str(frame.get("id")) for frame in frames]
    if SHAPE_ID in ids:
        problems.append(f"the frame '{SHAPE_ID}' is already in the specification")
    if ANCHOR_BEFORE not in ids or SCOPE_ID not in ids:
        problems.append("the specification is missing the scope frame or the setup frame")
    return problems


def build_spec() -> str:
    """Return the new specification text with the scope picture swapped and the shape frame added.

    Returns:
        The text to write into scaffold.json.
    """
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    frames = cast("list[dict[str, object]]", document["frames"])
    by_id = {str(frame["id"]): frame for frame in frames}
    scope = by_id[SCOPE_ID]
    figure = cast("dict[str, object]", scope["figure"])
    figure["path"] = f"figures/{TARGET_PICTURE.name}"
    figure["caption"] = SCOPE_CAPTION
    figure["source"] = SCOPE_SOURCE
    position = [str(frame["id"]) for frame in frames].index(ANCHOR_BEFORE)
    frames.insert(
        position,
        {
            "id": SHAPE_ID,
            "section": "RECALL",
            "title": SHAPE_TITLE,
            "body": SHAPE_BODY,
            "target_position": SHAPE_TARGET,
            "note": SHAPE_NOTE,
            "figure": {
                "path": "figures/thesis_hiad_parametric_cross_section.png",
                "caption": SHAPE_CAPTION,
                "source": SHAPE_SOURCE,
                "layout": "side_points",
            },
            "footer": SHAPE_FOOTER,
        },
    )
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    """Copy the overview picture, then patch the specification, the tests and both README files.

    Returns:
        Zero when every file was written, one when a guard refused.

    """
    problems = check_measurements()
    problems += check_anchors()
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1

    _ = shutil.copy2(SOURCE_PICTURE, TARGET_PICTURE)
    if digest(SOURCE_PICTURE) != digest(TARGET_PICTURE):
        _ = sys.stdout.write("MISMATCH the copy of the overview picture does not match the source\n")
        return 1

    spec_text = build_spec()
    tests_text = TESTS.read_text(encoding="utf-8")
    for old, new, _expected in TEST_RULES:
        tests_text = tests_text.replace(old, new, 1)
    readme_text = README.read_text(encoding="utf-8")
    for old, new, _expected in README_RULES:
        readme_text = readme_text.replace(old, new, 1)
    figures_text = FIGURES_README.read_text(encoding="utf-8")
    for old, new, _expected in FIGURES_RULES:
        figures_text = figures_text.replace(old, new, 1)

    for name, text in (
        ("the specification", spec_text),
        ("the test file", tests_text),
        ("README.md", readme_text),
        ("figures/README.md", figures_text),
    ):
        if EM_DASH in text:
            _ = sys.stdout.write(f"MISMATCH {name} would carry an em dash\n")
            return 1
    try:
        _ = ast.parse(tests_text)
    except SyntaxError as error:
        _ = sys.stdout.write(f"MISMATCH the test file would not parse: {error}\n")
        return 1

    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _ = SPEC_BACKUP_PATH.write_bytes(SPEC.read_bytes())
    _ = TESTS_BACKUP_PATH.write_bytes(TESTS.read_bytes())
    _ = README_BACKUP_PATH.write_bytes(README.read_bytes())
    _ = FIGURES_BACKUP_PATH.write_bytes(FIGURES_README.read_bytes())
    _ = SPEC.write_text(spec_text, encoding="utf-8")
    _ = TESTS.write_text(tests_text, encoding="utf-8")
    _ = README.write_text(readme_text, encoding="utf-8")
    _ = FIGURES_README.write_text(figures_text, encoding="utf-8")
    _ = sys.stdout.write(
        f"the scope slide now carries {TARGET_PICTURE.name} and {SHAPE_ID} carries the half-section\n"
        f"picture sha256 {digest(TARGET_PICTURE)[:16]}\n",
    )
    return 0


SPEC_BACKUP_PATH = BACKUP_DIR / "scaffold_before_shape_move.json"
TESTS_BACKUP_PATH = BACKUP_DIR / "test_make_pptx_before_shape_move.py"
README_BACKUP_PATH = BACKUP_DIR / "README_before_shape_move.md"
FIGURES_BACKUP_PATH = BACKUP_DIR / "figures_README_before_shape_move.md"

if __name__ == "__main__":
    raise SystemExit(main())
