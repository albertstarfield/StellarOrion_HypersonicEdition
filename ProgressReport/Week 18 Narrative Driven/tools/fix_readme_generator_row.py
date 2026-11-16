#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Bring the generator row of the README to the deck that was just built.

WHY: the deck grew to twenty-six slides when the shape slide was added, so
the row that quotes the generator's own self-report was left describing the
previous build. The row is rewritten with the numbers the generator printed
for this build.

The script is a guarded replacement driver: it counts the anchor, refuses to
write when it does not match, and leaves the file untouched on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
README = PROJECT / "README.md"
BACKUP = Path(__file__).resolve().parent / "backups" / "README_before_generator_row.md"
EM_DASH = "\u2014"

OLD = (
    "5 owner blocks, 23 frames, 5 PowerPoint sections, 147 package parts with 133 XML parts "
    "well formed, 25 slides with 23 of 23 frames managed, and 23 slot bodies agreeing with "
    "the specification."
)
NEW = (
    "5 owner blocks, 24 frames, 5 PowerPoint sections, 152 package parts with 137 XML parts "
    "well formed, 26 slides with 24 of 24 frames managed, and 24 slot bodies agreeing with "
    "the specification."
)


def main() -> int:
    """Update the generator row of the README.

    Returns:
        Zero when the row was rewritten, one when the guard refused.
    """
    text = README.read_text(encoding="utf-8")
    found = text.count(OLD)
    if found != 1:
        _ = sys.stdout.write(f"MISMATCH expected 1 occurrence, found {found}\n")
        return 1
    updated = text.replace(OLD, NEW, 1)
    if EM_DASH in updated:
        _ = sys.stdout.write("MISMATCH README.md would carry an em dash\n")
        return 1
    _ = BACKUP.parent.mkdir(parents=True, exist_ok=True)
    _ = BACKUP.write_bytes(README.read_bytes())
    _ = README.write_text(updated, encoding="utf-8")
    _ = sys.stdout.write("the generator row now quotes the twenty-six slide build\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
