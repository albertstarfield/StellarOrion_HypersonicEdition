#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Put the optimization flowchart into the deck as a methodology slide.

WHY: the owner asked for the optimization flowchart in the presentation. The
thesis figure fignew_pipeline.png carries the twelve stage validation
pipeline and, under it, the geometry optimization loop, so it is copied into
the folder of the deck and given a frame of its own directly after the
re-radiation slide. The picture is taken exactly as it is: nothing is
retouched.

The script is a guarded driver: it verifies the copy with a hash, counts
every anchor, measures the new title against the budget of the title band,
refuses to write a file that carries an em dash, parses the result and
leaves every file untouched when a check fails.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
SOURCE = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/fignew_pipeline.png"
TARGET = PROJECT / "figures" / "thesis_optimization_flowchart.png"
SPEC = PROJECT / "scaffold.json"
TESTS = PROJECT / "tests" / "test_make_pptx.py"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
SPEC_BACKUP = BACKUP_DIR / "scaffold_before_optimization_flowchart.json"
TESTS_BACKUP = BACKUP_DIR / "test_make_pptx_before_optimization_flowchart.py"
EM_DASH = "\u2014"
TITLE = "METHODOLOGY: THE OPTIMIZATION FLOWCHART"
TITLE_BUDGET_IN = 8.165
FRAME_ID = "recall-methodology-optimization"
ANCHOR_FRAME = "recall-methodology-radiation"

CAPTION = (
    "The validation pipeline the engine executes in its twelve stages, with the geometry\n"
    "optimization loop that feeds the next geometry back into the chain.\n"
    "The stages: flight parameters, geometry quality assurance, the generation of the HIAD\n"
    "surface, the solver input script, the solver container, the DSMC simulation, then the\n"
    "surface dumps, the flight metrics, the survivability check, the sanity checks, the\n"
    "comparison against the IRVE-3 flight data and the export of fields and plots.\n"
    "The loop: design space, the Bayesian step, the cost function J(x), the DSMC\n"
    "re-simulation and the accept test on q against Q_target, with a rejection resampling\n"
    "the design space, so every accepted geometry is re-measured before it is kept."
)
SOURCE_LINE = (
    "Source: fignew_pipeline.png from CurrentThesisFinalReport/figures, the validation "
    "pipeline and optimization loop figure."
)
FOOTER = "The pipeline and the optimization loop. The narration stays editable in PowerPoint."
TARGET_POSITION = (
    "the slide right after the re-radiation, carrying the pipeline and its optimization loop."
)
NOTE = (
    "The twelve stage validation pipeline of the engine and the geometry optimization loop "
    "that closes it, taken from the thesis figure without modification."
)

TEST_RULES: list[tuple[str, str, int]] = [
    ("EXPECTED_FRAME_COUNT = 22", "EXPECTED_FRAME_COUNT = 23", 1),
    ("EXPECTED_METHODOLOGY_FRAME_COUNT = 6", "EXPECTED_METHODOLOGY_FRAME_COUNT = 7", 1),
    ("EXPECTED_FILLED_FRAME_COUNT = 11", "EXPECTED_FILLED_FRAME_COUNT = 12", 1),
    (
        '        "recall-methodology-radiation",\n    }',
        '        "recall-methodology-radiation",\n        "recall-methodology-optimization",\n    }',
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
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            hasher.update(block)
    return hasher.hexdigest()


def install_picture() -> str:
    """Copy the flowchart into the deck folder and verify the copy.

    Returns:
        The digest of the installed picture.

    Raises:
        SystemExit: When the source is missing or the copy does not match.
    """
    if not SOURCE.is_file():
        _ = sys.stdout.write(f"MISMATCH the thesis figure is missing: {SOURCE}\n")
        raise SystemExit(1)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET.is_file():
        target_backup = BACKUP_DIR / "thesis_optimization_flowchart_before.png"
        _ = target_backup.write_bytes(TARGET.read_bytes())
    _ = shutil.copy2(SOURCE, TARGET)
    if digest(SOURCE) != digest(TARGET):
        _ = sys.stdout.write("MISMATCH the copy of the flowchart does not match the source\n")
        raise SystemExit(1)
    return digest(TARGET)


def measure_title() -> None:
    """Check that the new title fits on one line of the title band.

    Raises:
        SystemExit: When the title does not fit.
    """
    sys.path.insert(0, str(PROJECT))
    import make_pptx  # ruff: ignore[import-outside-top-level]

    width = make_pptx.measure_text_inches(TITLE, make_pptx.TITLE_FONT, make_pptx.FRAME_TITLE_SIZE.pt)
    if width > TITLE_BUDGET_IN:
        _ = sys.stdout.write(f"MISMATCH the title measures {width:.2f} in against {TITLE_BUDGET_IN} in\n")
        raise SystemExit(1)
    _ = sys.stdout.write(f"title {TITLE!r} measures {width:.2f} in of {TITLE_BUDGET_IN} in\n")


def patch_spec() -> None:
    """Insert the flowchart frame after the re-radiation frame.

    Raises:
        SystemExit: When an anchor is missing or a file would carry an em dash.
    """
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    frames: list[dict[str, object]] = document["frames"]
    ids = [str(frame["id"]) for frame in frames]
    if FRAME_ID in ids:
        _ = sys.stdout.write(f"MISMATCH the frame '{FRAME_ID}' is already in the specification\n")
        raise SystemExit(1)
    if ANCHOR_FRAME not in ids:
        _ = sys.stdout.write(f"MISMATCH the specification does not hold the frame '{ANCHOR_FRAME}'\n")
        raise SystemExit(1)
    position = ids.index(ANCHOR_FRAME) + 1
    frames.insert(
        position,
        {
            "id": FRAME_ID,
            "section": "RECALL",
            "title": TITLE,
            "body": "",
            "target_position": TARGET_POSITION,
            "note": NOTE,
            "figure": {
                "path": f"figures/{TARGET.name}",
                "caption": CAPTION,
                "source": SOURCE_LINE,
                "layout": "feature",
            },
            "footer": FOOTER,
        },
    )
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if EM_DASH in text:
        _ = sys.stdout.write("MISMATCH the specification would carry an em dash\n")
        raise SystemExit(1)
    _ = SPEC_BACKUP.write_text(SPEC.read_text(encoding="utf-8"), encoding="utf-8")
    _ = SPEC.write_text(text, encoding="utf-8")
    _ = sys.stdout.write(f"inserted the frame '{FRAME_ID}' at position {position + 1}\n")


def patch_tests() -> None:
    """Raise the counts the test suite pins for the new frame.

    Raises:
        SystemExit: When an anchor is missing or the result would not parse.
    """
    text = TESTS.read_text(encoding="utf-8")
    problems: list[str] = []
    for old, _new, expected in TEST_RULES:
        found = text.count(old)
        if found != expected:
            problems.append(f"expected {expected} occurrence(s), found {found}: {old[:60]!r}")
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        raise SystemExit(1)
    for old, new, _expected in TEST_RULES:
        text = text.replace(old, new, 1)
    if EM_DASH in text:
        _ = sys.stdout.write("MISMATCH the test file would carry an em dash\n")
        raise SystemExit(1)
    try:
        _ = ast.parse(text)
    except SyntaxError as error:
        _ = sys.stdout.write(f"MISMATCH the test file would not parse: {error}\n")
        raise SystemExit(1) from error
    if "recall-methodology-optimization" not in text:
        _ = sys.stdout.write("MISMATCH the new frame did not reach the test file\n")
        raise SystemExit(1)
    _ = TESTS_BACKUP.write_text(TESTS.read_text(encoding="utf-8"), encoding="utf-8")
    _ = TESTS.write_text(text, encoding="utf-8")
    _ = sys.stdout.write("the counts of the test suite now include the flowchart frame\n")


def main() -> int:
    """Install the picture, check the title, then patch the specification.

    Returns:
        Zero when every step succeeded, one when a guard refused.

    """
    try:
        installed = install_picture()
        measure_title()
        patch_spec()
        patch_tests()
    except SystemExit as error:
        if error.code == 0:
            return 0
        return 1
    _ = sys.stdout.write(
        "the optimization flowchart is in the deck folder and in the specification\n"
        f"picture sha256 {installed[:16]}\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
