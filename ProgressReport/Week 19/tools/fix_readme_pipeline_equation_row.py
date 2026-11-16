#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Bring the generator self-report row of the README up to the 41 slide deck.

WHY: the README quotes the numbers the generator prints, and the deck grew
from 37 slides and 35 frames to 41 slides and 39 frames when the four
equation slides of the optimization pipeline were added. The row is rewritten
with the numbers of the last build so the documentation cannot contradict the
file it describes.

The script is a guarded replacement driver: it counts the anchor, refuses to
write when the count does not match, and leaves the file untouched otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
README = PROJECT / "README.md"
BACKUP = Path(__file__).resolve().parent / "backups" / "README_before_pipeline_equation_row.md"
EM_DASH = "\u2014"

OLD = (
    "5 owner blocks, 35 frames, 5 PowerPoint sections, 207 package parts with 181 XML parts "
    "well formed, 37 slides with 35 of 35 frames managed, and 35 slot bodies agreeing with "
    "the specification."
)
NEW = (
    "5 owner blocks, 39 frames, 5 PowerPoint sections, 227 package parts with 197 XML parts "
    "well formed, 41 slides with 39 of 39 frames managed, and 39 slot bodies agreeing with "
    "the specification."
)


def main() -> int:
    """Update the generator self-report row of the README.

    Returns:
        Zero when the row was rewritten, one when the anchor did not match.
    """
    text = README.read_text(encoding="utf-8")
    found = text.count(OLD)
    if found != 1:
        _ = sys.stdout.write(f"MISMATCH expected 1 occurrence of the old row, found {found}\n")
        return 1
    updated = text.replace(OLD, NEW, 1)
    if EM_DASH in updated:
        _ = sys.stdout.write("MISMATCH README.md would carry an em dash\n")
        return 1
    _ = BACKUP.write_bytes(README.read_bytes())
    _ = README.write_text(updated, encoding="utf-8")
    _ = sys.stdout.write("the generator self-report row now reports 41 slides and 39 frames\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
