#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Run the two methodology subsections in the order the owner set.

WHY: the owner wants Methodology: DSMC CFD first and Methodology:
Optimization Pipeline after it. The specification therefore moves the five
optimization frames behind the seven DSMC frames, the README table is
rebuilt in that same order, and the five rows that an earlier patch had
duplicated are removed while the table is being rebuilt.

The script is a guarded driver: it checks the old order and the old table
before it writes, refuses to write a file that carries an em dash, and
leaves every file untouched when a single check fails.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import cast

PROJECT = Path(__file__).resolve().parent.parent
SPEC = PROJECT / "scaffold.json"
README = PROJECT / "README.md"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
EM_DASH = "\u2014"

OPTIMIZATION_BLOCK = (
    "recall-methodology-optimization",
    "recall-methodology-pipeline-space",
    "recall-methodology-pipeline-cost",
    "recall-methodology-pipeline-ga",
    "recall-methodology-pipeline-gate",
)
DSMC_BLOCK = (
    "recall-methodology-shape",
    "recall-methodology-setup",
    "recall-methodology-mesh",
    "recall-methodology-convergence",
    "recall-methodology-convection",
    "recall-methodology-conduction",
    "recall-methodology-radiation",
)
OLD_ORDER = OPTIMIZATION_BLOCK + DSMC_BLOCK
NEW_ORDER = DSMC_BLOCK + OPTIMIZATION_BLOCK

REASONING_ROW = (
    "| 3. Methodology (graphical framework flowchart, per-step definitions, detailed "
    "methodology, the reasoning) | `RECALL` | `METHODOLOGY AND REASONING` |\n"
)
PROGRESS_ROW = "| `[ Current progress start ]` 5. Overall progress (not the resolution detail) |"

#: The table rows of the two subsections, in the order they must appear.
TABLE_ROWS = {
    "recall-methodology-shape": (
        "| 3. Methodology (the shape the method tests) | `RECALL` | "
        "`METHODOLOGY: THE SHAPE UNDER TEST` |\n"
    ),
    "recall-methodology-setup": (
        "| 3. Methodology (how the simulation is set up) | `RECALL` | "
        "`METHODOLOGY: THE SIMULATION SETUP` |\n"
    ),
    "recall-methodology-mesh": (
        "| 3. Methodology (the mesh and the grid independence) | `RECALL` | "
        "`METHODOLOGY: THE GRID INDEPENDENCE` |\n"
    ),
    "recall-methodology-convergence": (
        "| 3. Methodology (the convergence of the particle solver) | `RECALL` | "
        "`METHODOLOGY: THE SOLVER CONVERGENCE` |\n"
    ),
    "recall-methodology-convection": (
        "| 3. Methodology (the convection channel) | `RECALL` | "
        "`METHODOLOGY: THE CONVECTION CHANNEL` |\n"
    ),
    "recall-methodology-conduction": (
        "| 3. Methodology (the conduction channel) | `RECALL` | "
        "`METHODOLOGY: THE CONDUCTION CHANNEL` |\n"
    ),
    "recall-methodology-radiation": (
        "| 3. Methodology (the re-radiation channel) | `RECALL` | "
        "`METHODOLOGY: THE RE-RADIATION CHANNEL` |\n"
    ),
    "recall-methodology-optimization": (
        "| 3. Methodology (the optimization flowchart) | `RECALL` | "
        "`METHODOLOGY: THE OPTIMIZATION FLOWCHART` |\n"
    ),
    "recall-methodology-pipeline-space": (
        "| 3. Methodology (the design space and the Latin hypercube) | `RECALL` | "
        "`METHODOLOGY: THE DESIGN SPACE` |\n"
    ),
    "recall-methodology-pipeline-cost": (
        "| 3. Methodology (the cost function) | `RECALL` | "
        "`METHODOLOGY: THE COST FUNCTION` |\n"
    ),
    "recall-methodology-pipeline-ga": (
        "| 3. Methodology (the genetic algorithm) | `RECALL` | "
        "`METHODOLOGY: THE GENETIC ALGORITHM` |\n"
    ),
    "recall-methodology-pipeline-gate": (
        "| 3. Methodology (the double pass and the DSMC gate) | `RECALL` | "
        "`METHODOLOGY: DOUBLE PASS AND THE GATE` |\n"
    ),
}

NEW_BULLET = """* The methodology is one overview and then two subsections in the order the
  owner set. `GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW` opens the block because
  it is the overview of everything below, and `METHODOLOGY AND REASONING`
  keeps the per-step definitions. First comes `Methodology: DSMC CFD` in
  seven slides: the shape under test, the simulation setup, the grid
  independence, the convergence of the particle solver, and then the three
  heat-flux channels, the convection, the conduction and the re-radiation.
  Then comes `Methodology: Optimization Pipeline`: the optimization flowchart
  and its four slides, the design space with the Latin hypercube, the cost
  function, the genetic algorithm, and the double pass with the DSMC gate.
  Every one of those slides is drawn the way the owner's reference slide asks
  for: the picture on the left with its caption under it, and the facts of the
  slide as separate stacked glass cards on the right, one point each, set at
  thirteen point and stepping down only as far as the column needs, with the
  provenance line under the cards. Every card is named after its frame, so the
  whole column is found and replaced as one thing when the tool updates a
  slide.
"""

BULLET_MARKER = "* The methodology is a block of eight slides"


def reorder_spec() -> str:
    """Return the specification with the DSMC subsection before the optimization one.

    Returns:
        The new text of the specification.

    Raises:
        SystemExit: When the old order is not the expected one.
    """
    document = cast("dict[str, object]", json.loads(SPEC.read_text(encoding="utf-8")))
    frames = cast("list[dict[str, object]]", document.get("frames"))
    ids = [str(frame.get("id")) for frame in frames]
    for frame_id in OLD_ORDER:
        if frame_id not in ids:
            _ = sys.stdout.write(f"MISMATCH the specification does not hold '{frame_id}'\n")
            raise SystemExit(1)
    start = ids.index(OLD_ORDER[0])
    if tuple(ids[start : start + len(OLD_ORDER)]) != OLD_ORDER:
        _ = sys.stdout.write(f"MISMATCH the block is not in the old order: {ids[start:start + 12]}\n")
        raise SystemExit(1)
    by_id = {str(frame.get("id")): frame for frame in frames}
    reordered = [by_id[frame_id] for frame_id in NEW_ORDER]
    frames[start : start + len(OLD_ORDER)] = reordered
    check = [str(frame.get("id")) for frame in frames]
    if tuple(check[start : start + len(NEW_ORDER)]) != NEW_ORDER:
        _ = sys.stdout.write("MISMATCH the new order was not produced\n")
        raise SystemExit(1)
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def rebuild_table() -> str:
    """Return README.md with the methodology rows in the new order and without duplicates.

    Returns:
        The new text of README.md.

    Raises:
        SystemExit: When the anchors of the table were not found once.
    """
    text = README.read_text(encoding="utf-8")
    lines = text.split("\n")
    reasoning = next(
        (index for index, line in enumerate(lines) if line == REASONING_ROW.rstrip("\n")),
        -1,
    )
    progress = next(
        (index for index, line in enumerate(lines) if line.startswith(PROGRESS_ROW)),
        -1,
    )
    if reasoning < 0 or progress < 0 or progress <= reasoning:
        _ = sys.stdout.write("MISMATCH the table anchors were not found in order\n")
        raise SystemExit(1)
    new_rows = [TABLE_ROWS[frame_id].rstrip("\n") for frame_id in NEW_ORDER]
    rebuilt = lines[: reasoning + 1] + new_rows + lines[progress:]
    text = "\n".join(rebuilt)
    for frame_id in NEW_ORDER:
        if text.count(TABLE_ROWS[frame_id]) != 1:
            _ = sys.stdout.write(f"MISMATCH the row of '{frame_id}' is not unique\n")
            raise SystemExit(1)
    return text


def apply_reorder() -> None:
    """Build the new specification and README text, then write both files.

    Raises:
        SystemExit: When one of the guards refuses.
    """
    readme = README.read_text(encoding="utf-8")
    if readme.count(BULLET_MARKER) != 1:
        _ = sys.stdout.write("MISMATCH the methodology bullet was not found once\n")
        raise SystemExit(1)
    spec_text = reorder_spec()
    readme_text = rebuild_table()
    lines = readme_text.split("\n")
    start = next(
        (index for index, line in enumerate(lines) if line.startswith(BULLET_MARKER)),
        -1,
    )
    if start < 0:
        _ = sys.stdout.write("MISMATCH the methodology bullet disappeared\n")
        raise SystemExit(1)
    end = start + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    readme_text = "\n".join(lines[:start] + NEW_BULLET.rstrip("\n").split("\n") + lines[end:])
    for name, text in (("the specification", spec_text), ("README.md", readme_text)):
        if EM_DASH in text:
            _ = sys.stdout.write(f"MISMATCH {name} would carry an em dash\n")
            raise SystemExit(1)
    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _ = shutil.copyfile(SPEC, BACKUP_DIR / "scaffold_before_dsmc_first.json")
    _ = shutil.copyfile(README, BACKUP_DIR / "README_before_dsmc_first.md")
    _ = SPEC.write_text(spec_text, encoding="utf-8")
    _ = README.write_text(readme_text, encoding="utf-8")


def main() -> int:
    """Put the DSMC subsection first in the specification and in the README.

    Returns:
        Zero when both files were written, one when a guard refused.
    """
    try:
        apply_reorder()
    except SystemExit:
        return 1
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, json.JSONDecodeError) as error:
        _ = sys.stdout.write(f"MISMATCH {type(error).__name__}: {error}\n")
        return 1
    _ = sys.stdout.write("Methodology: DSMC CFD now runs before Methodology: Optimization Pipeline\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
