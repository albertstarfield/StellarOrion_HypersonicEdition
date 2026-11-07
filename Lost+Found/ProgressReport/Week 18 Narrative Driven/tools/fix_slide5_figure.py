#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Refresh the parametric cross-section figure of slide 5 and its two lines.

WHY THIS EXISTS
---------------
The deck folder still held the measured reconstruction whose fitted skin line
self-intersected (the "sharp mushroom" outline). The thesis generator
``figures/make_hiad_parametric_cross_section.py`` states in its purpose block
that it replaces exactly that picture, and it wrote the replacement 36 minutes
after the deck copy was taken, so the deck was showing a stale figure. The
caption of the frame described the old picture (the shoulder torus T7 and the
scalloped skin), so the caption and the source line are rewritten with it.

CITATIONS
---------
ruff, the Python linter -- https://docs.astral.sh/ruff/
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path(
    "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/"
    "Lost+Found/ProgressReport/Week 17 Narrative Template Driven gen experimental",
)
REPO = PROJECT.parents[2]
THESIS_FIGURES = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"
SOURCE_PNG = THESIS_FIGURES / "hiad_parametric_cross_section.png"
DECK_PNG = PROJECT / "figures" / "thesis_hiad_parametric_cross_section.png"
SPEC = PROJECT / "scaffold.json"
TOOLS = PROJECT / "tools"
BACKUP_PNG = TOOLS / "thesis_hiad_parametric_cross_section_before_fix.png"
BACKUP_SPEC = TOOLS / "scaffold_before_slide5_caption.json"
EM_DASH = "\u2014"
FRAME_ID = "recall-tujuan-scope"

OLD_CAPTION = (
    "Parametric cross-section of the 3.0 m HIAD: the stacked toroidal bladders T1 to T6, "
    "the shoulder torus T7, the nose sphere and the scalloped skin on the Rapisarda MDAO "
    "baseline."
)
NEW_CAPTION = (
    "Meridional half-section of the HIAD bladder layout: the nose arc tangent to the cone "
    "generator and the six toroidal bladders T1 to T6, at R_N 0.55 m, r_tor 0.135 m and a "
    "half-cone angle of 60 degrees.\n"
    "Six tori reach R_max 1.90 m over a body length of 1.269 m, and the skin aft of the nose "
    "tangent is omitted so that the stack stays visible."
)
OLD_SOURCE = (
    "Source: CurrentThesisFinalReport/figures/hiad_parametric_cross_section.png, thesis "
    "Chapter II."
)
NEW_SOURCE = (
    "Source: hiad_parametric_cross_section.png from CurrentThesisFinalReport/figures, written "
    "by figures/make_hiad_parametric_cross_section.py."
)


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


def check() -> str:
    """Verify every condition before anything is written.

    WHY: the script touches the picture of a slide and the single source of
    truth of the whole deck, so every precondition is checked here and the
    caller writes only when this returns the empty string.

    Returns:
        An empty string when the run may proceed, otherwise the reason it may
        not.
    """
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    matches = [frame for frame in document["frames"] if frame["id"] == FRAME_ID]
    figure = matches[0].get("figure") if len(matches) == 1 else None
    conditions: list[tuple[bool, str]] = [
        (SOURCE_PNG.is_file(), f"the thesis figure is missing: {SOURCE_PNG}"),
        (DECK_PNG.is_file(), f"the deck figure is missing: {DECK_PNG}"),
        (digest(SOURCE_PNG) != digest(DECK_PNG), "the deck already holds the current thesis figure"),
        (EM_DASH not in NEW_CAPTION and EM_DASH not in NEW_SOURCE, "the new wording carries an em dash"),
        (len(matches) == 1, f"the specification holds {len(matches)} frames named {FRAME_ID}"),
        (isinstance(figure, dict), f"the frame {FRAME_ID} carries no figure block"),
        (
            isinstance(figure, dict) and figure.get("caption") == OLD_CAPTION,
            "the caption of the frame is not the expected one",
        ),
        (
            isinstance(figure, dict) and figure.get("source") == OLD_SOURCE,
            "the source line of the frame is not the expected one",
        ),
    ]
    for holds, problem in conditions:
        if not holds:
            return problem
    return ""


def install() -> tuple[str, str]:
    """Write the picture and the two lines, then read them back.

    Returns:
        A pair of digests, the picture before the change and the
        specification before the change.
    """
    before_png = digest(DECK_PNG)
    before_spec = digest(SPEC)
    _ = shutil.copyfile(DECK_PNG, BACKUP_PNG)
    _ = BACKUP_SPEC.write_bytes(SPEC.read_bytes())
    _ = shutil.copyfile(SOURCE_PNG, DECK_PNG)
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    figure: dict[str, object] = next(
        frame for frame in document["frames"] if frame["id"] == FRAME_ID
    )["figure"]
    figure["caption"] = NEW_CAPTION
    figure["source"] = NEW_SOURCE
    _ = SPEC.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    return before_png, before_spec


def verify() -> str:
    """Read both files back and confirm they hold what was written.

    Returns:
        An empty string when both files hold the new content, otherwise the
        reason they do not.
    """
    if digest(DECK_PNG) != digest(SOURCE_PNG):
        return "the installed picture does not match the thesis figure"
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    figure: dict[str, object] = next(
        frame for frame in document["frames"] if frame["id"] == FRAME_ID
    )["figure"]
    if figure["caption"] != NEW_CAPTION or figure["source"] != NEW_SOURCE:
        return "the specification does not hold the new wording"
    return ""


def main() -> int:
    """Replace the deck copy of the figure and rewrite its two lines.

    Returns:
        0 when the picture and the two lines are written and read back
        correctly, 1 on any mismatch (the files are then left as they were
        when the mismatch was found).
    """
    problem = check()
    if len(problem) != 0:
        _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1
    before_png, before_spec = install()
    problem = verify()
    if len(problem) != 0:
        _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1
    _ = sys.stdout.write(
        "slide 5 now carries the fixed parametric cross-section\n"
        f"  picture: {before_png[:16]} -> {digest(DECK_PNG)[:16]}\n"
        f"  spec:    {before_spec[:16]} -> {digest(SPEC)[:16]}\n"
        f"  backups: {BACKUP_PNG.name}, {BACKUP_SPEC.name}\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
