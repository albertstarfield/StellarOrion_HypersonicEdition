#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Clear the lint findings of the subsection sub-title change.

WHY: the loader of the specification grew one local too many when it learned
to read the subsection, so the validation moves into a helper of its own and
the function drops back under the local budget. The one-shot script that
carried the change is also brought to the house quote style, now that it has
already run.

The script is a guarded replacement driver: it counts every anchor, refuses
to write when a count does not match, parses the result and leaves the files
untouched on any failure.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
GENERATOR = PROJECT / "make_pptx.py"
PATCHER = Path(__file__).resolve().parent / "add_subsection_subtitle.py"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
GENERATOR_BACKUP = BACKUP_DIR / "make_pptx_before_subsection_helper.py"
EM_DASH = "\u2014"

LOADER_OLD = """        subsection: object = entry.get("subsection", "")
        if not isinstance(subsection, str):
            failure_reason = f"frame '{frame_id}' needs a string subsection"
            raise ScaffoldError(failure_reason)
        frames.append(
            SlotFrame(
                id=frame_id,
                section=section,
                title=title,
                body=body.strip(),
                target_position=target_position.strip(),
                note=note.strip(),
                figure=_parse_frame_figure(entry, path.parent, frame_id),
                timeline=timeline,
                pill_list=pill_list,
                cards_only=cards_only,
                footer=footer.strip(),
                subsection=subsection.strip(),
            ),
        )
"""

LOADER_NEW = """        frames.append(
            SlotFrame(
                id=frame_id,
                section=section,
                title=title,
                body=body.strip(),
                target_position=target_position.strip(),
                note=note.strip(),
                figure=_parse_frame_figure(entry, path.parent, frame_id),
                timeline=timeline,
                pill_list=pill_list,
                cards_only=cards_only,
                footer=footer.strip(),
                subsection=_require_subsection(entry, frame_id),
            ),
        )
"""

HELPER = '''def _require_subsection(entry: Mapping[str, object], frame_id: str) -> str:
    """Return the methodology subsection of a frame, empty when it has none.

    WHY: the subsection is an optional label, so a frame that carries none
    simply has no sub-title; the validation lives in this helper because the
    loader of the specification is already at its local budget.

    Args:
        entry: The frame entry of the specification.
        frame_id: The identifier of the frame, used in the failure message.

    Returns:
        The subsection name with its edges trimmed.

    Raises:
        ScaffoldError: When the entry carries a subsection that is not text.

    """
    value: object = entry.get("subsection", "")
    if not isinstance(value, str):
        failure_reason = f"frame '{frame_id}' needs a string subsection"
        raise ScaffoldError(failure_reason)
    return value.strip()


'''


def main() -> int:
    """Move the subsection validation into a helper.

    Returns:
        Zero when the generator was patched, one when a guard refused.

    """
    problems: list[str] = []
    generator_text = GENERATOR.read_text(encoding="utf-8")
    for old, expected in ((LOADER_OLD, 1), ("def load_spec(", 1)):
        found = generator_text.count(old)
        if found != expected:
            problems.append(f"make_pptx.py: expected {expected} occurrence(s), found {found}: {old[:60]!r}")
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1
    if generator_text.count(HELPER) != 0:
        _ = sys.stdout.write("MISMATCH the helper is already in the generator\n")
        return 1

    generator_text = generator_text.replace(LOADER_OLD, LOADER_NEW, 1)
    anchor = "def load_spec("
    generator_text = generator_text.replace(anchor, HELPER + anchor, 1)
    _ = ast.parse(generator_text)

    patcher_text = PATCHER.read_text(encoding="utf-8")
    if EM_DASH in generator_text or EM_DASH in patcher_text:
        _ = sys.stdout.write("MISMATCH a file would carry an em dash\n")
        return 1

    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _ = GENERATOR_BACKUP.write_bytes(GENERATOR.read_bytes())
    _ = GENERATOR.write_text(generator_text, encoding="utf-8")
    _ = sys.stdout.write("the subsection validation now lives in its own helper\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
