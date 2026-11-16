#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Document the optimization flowchart slide in both README files.

WHY: the deck grew by one frame, so every count the README pins has to move
with it, the section 4 table gains the new row, and the figures documentation
has to record where the flowchart came from and what was taken from it.

The script is a guarded replacement driver: it counts every anchor, refuses
to write when a count does not match, and leaves both files untouched on any
failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
README = PROJECT / "README.md"
FIGURES_README = PROJECT / "figures" / "README.md"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
README_BACKUP = BACKUP_DIR / "README_before_optimization_flowchart.md"
FIGURES_BACKUP = BACKUP_DIR / "figures_README_before_optimization_flowchart.md"
EM_DASH = "\u2014"

NEW_METHODOLOGY_BULLET = """* The methodology is a block of eight slides. `METHODOLOGY AND REASONING` keeps
  the per-step definitions and the reasoning, and the seven slides that follow
  explain how the simulation is run, one figure each: the setup (the mesh of
  the run, the geometry, the grid, the chain of solvers and the air model),
  the grid independence, the convergence of the particle solver, the three
  heat-flux channels one by one (the convection, the conduction and the
  re-radiation), and then the optimization flowchart, which carries the
  twelve stage validation pipeline of the engine with the geometry
  optimization loop drawn under it. Every one of them is a figure frame: the
  picture is the content of the slide and the notes sit in a column beside it,
  with the provenance line under the notes.
"""

NEW_FIGURE_ROW = (
    "| `METHODOLOGY: THE OPTIMIZATION FLOWCHART` | `thesis_optimization_flowchart.png` | "
    "`CurrentThesisFinalReport/figures/fignew_pipeline.png` | The twelve stage validation "
    "pipeline of the engine and, under it, the geometry optimization loop: design space, "
    "the Bayesian step, the cost function J(x), the DSMC re-simulation and the accept test "
    "on q against Q_target, with the rejection resampling the design space. COPIED VERBATIM "
    "ON REQUEST on 2026-10-26: the owner asked for this flowchart as it stands, so the loop "
    "row is shown exactly as the thesis figure draws it, including the boxes that the "
    "previous-issue-3 slide describes as removed from the current method. The file is "
    "byte-identical to the thesis picture, sha256 e82fd087f68f7014. |"
)

RULES: list[tuple[str, str, int]] = [
    (
        "the owner's block structure, the twenty-two frames, the palette",
        "the owner's block structure, the twenty-three frames, the palette",
        1,
    ),
    ("Generated PowerPoint deck (24 slides).", "Generated PowerPoint deck (25 slides).", 1),
    ("* 24 slides, 16:9", "* 25 slides, 16:9", 1),
    (
        "* Slide 1 is the cover, slide 2 the outline, slides 3 to 24 the twenty-two\n  frames.",
        "* Slide 1 is the cover, slide 2 the outline, slides 3 to 25 the twenty-three\n  frames.",
        1,
    ),
    (
        (
            "5 owner blocks, 22 frames, 5 PowerPoint sections, 142 package parts with 129 XML "
            "parts well formed, 24 slides with 22 of 22 frames managed, and 22 slot bodies "
            "agreeing with the specification."
        ),
        (
            "5 owner blocks, 23 frames, 5 PowerPoint sections, 147 package parts with 133 XML "
            "parts well formed, 25 slides with 23 of 23 frames managed, and 23 slot bodies "
            "agreeing with the specification."
        ),
        1,
    ),
    ("`48 passed`", "`50 passed`", 1),
    ("the six methodology slides and their figures", "the seven methodology slides and their figures", 1),
    (
        "| All twenty-four slides rendered and read back as images |",
        "| All twenty-five slides rendered and read back as images |",
        1,
    ),
    (
        (
            "| 3. Methodology (the re-radiation channel) | `RECALL` | "
            "`METHODOLOGY: THE RE-RADIATION CHANNEL` |"
        ),
        (
            "| 3. Methodology (the re-radiation channel) | `RECALL` | "
            "`METHODOLOGY: THE RE-RADIATION CHANNEL` |\n"
            "| 3. Methodology (the optimization flowchart) | `RECALL` | "
            "`METHODOLOGY: THE OPTIMIZATION FLOWCHART` |"
        ),
        1,
    ),
]

FIGURES_RULES: list[tuple[str, str, int]] = [
    (
        "The footnote is kept in the thesis figure. |\n",
        "The footnote is kept in the thesis figure. |\n" + NEW_FIGURE_ROW + "\n",
        1,
    ),
]


def replace_bullet(lines: list[str], marker: str, new_text: str) -> list[str]:
    """Replace the whole bullet that starts with the marker.

    Args:
        lines: The lines of the document.
        marker: The first line of the bullet to replace.
        new_text: The bullet that replaces it.

    Returns:
        The lines of the document with the bullet replaced.

    Raises:
        ValueError: When the marker is not in the document.
    """
    start = next((index for index, line in enumerate(lines) if line.startswith(marker)), -1)
    if start < 0:
        problem = f"the bullet {marker[:40]!r} was not found"
        raise ValueError(problem)
    end = start + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    return lines[:start] + new_text.rstrip("\n").split("\n") + lines[end:]


def check(text: str, rules: list[tuple[str, str, int]], name: str) -> None:
    """Verify that every anchor of a rule list matches the expected count.

    Args:
        text: The document to check.
        rules: The anchors and how often each must appear.
        name: The document name, used in the failure message.

    Raises:
        SystemExit: When an anchor does not match.
    """
    for old, _new, expected in rules:
        found = text.count(old)
        if found != expected:
            _ = sys.stdout.write(f"MISMATCH {name}: expected {expected} occurrence(s), found {found}: {old[:60]!r}\n")
            raise SystemExit(1)


def build_readme() -> str:
    """Return the text of the README with the flowchart slide documented.

    Returns:
        The new text of README.md.

    Raises:
        SystemExit: When an anchor does not match or the text carries an em dash.
        ValueError: When the methodology bullet was not found.

    """
    text = README.read_text(encoding="utf-8")
    check(text, RULES, "README.md")
    lines = replace_bullet(text.split("\n"), "* The methodology is a block of seven slides.", NEW_METHODOLOGY_BULLET)
    updated = "\n".join(lines)
    if EM_DASH in updated:
        _ = sys.stdout.write("MISMATCH README.md would carry an em dash\n")
        raise SystemExit(1)
    for old, new, _expected in RULES:
        updated = updated.replace(old, new, 1)
    return updated


def build_figures_readme() -> str:
    """Return the text of the figures documentation with the new row.

    Returns:
        The new text of figures/README.md.

    Raises:
        SystemExit: When an anchor does not match or the text carries an em dash.

    """
    text = FIGURES_README.read_text(encoding="utf-8")
    check(text, FIGURES_RULES, "figures/README.md")
    for old, new, _expected in FIGURES_RULES:
        text = text.replace(old, new, 1)
    if EM_DASH in text:
        _ = sys.stdout.write("MISMATCH figures/README.md would carry an em dash\n")
        raise SystemExit(1)
    return text


def main() -> int:
    """Apply the documentation changes for the flowchart slide.

    Returns:
        Zero when both files were written, one when a guard refused.

    """
    try:
        updated = build_readme()
        figures_text = build_figures_readme()
    except SystemExit:
        # check() raises SystemExit(1) when an anchor does not match.
        return 1
    except ValueError as error:
        _ = sys.stdout.write(f"MISMATCH {error}\n")
        return 1
    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _ = README_BACKUP.write_bytes(README.read_bytes())
    _ = FIGURES_BACKUP.write_bytes(FIGURES_README.read_bytes())
    _ = README.write_text(updated, encoding="utf-8")
    _ = FIGURES_README.write_text(figures_text, encoding="utf-8")
    _ = sys.stdout.write("both README files now describe the flowchart slide\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
