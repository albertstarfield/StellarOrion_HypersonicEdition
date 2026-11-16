#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Take the Bayesian step and the CCD screen out of the optimization flowchart.

WHY: the loop row of the flowchart still shows the method the thesis removed.
Issue 3 of the deck states it plainly: no central composite screen, no
surrogate, no acquisition step, and the Latin hypercube seeds the genetic
algorithm. A picture that says otherwise contradicts the slide two places
later, so the two boxes are corrected in a copy of the generator that lives
in this folder. The thesis file itself is never written.

The script is a guarded driver: it counts every anchor, refuses to write a
file that carries an em dash, runs the copy under the thesis interpreter,
checks the drawing guards of the generator and only then installs the picture.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
THESIS_FIGURES = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"
THESIS_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"
SOURCE_GENERATOR = THESIS_FIGURES / "make_pipeline_figure.py"
# WHY ARCHIVED: the picture this copy used to draw was replaced by
# tools/make_ga_flowchart_deck.py, so the copy is kept as evidence only.
LOCAL_GENERATOR = Path(__file__).resolve().parent / "backups" / "pipeline_figure_flowchart_APPLIED.py.bak"
LOCAL_OUTPUT = LOCAL_GENERATOR.parent / "fignew_pipeline.png"
TARGET = PROJECT / "figures" / "thesis_optimization_flowchart.png"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
TARGET_BACKUP = BACKUP_DIR / "thesis_optimization_flowchart_before_loop_fix.png"
EM_DASH = "\u2014"
MIN_PICTURE_BYTES = 5000

# WHY: the two boxes that name the removed method. The design space is seeded
# by a Latin hypercube only, and the search is the genetic algorithm.
LABEL_RULES: list[tuple[str, str, int]] = [
    ('    loop = ["Design space\\n(LHS or CCD)",\n            "Bayesian\\noptimization",\n',
     '    loop = ["Design space\\n(Latin hypercube)",\n            "Genetic\\nalgorithm",\n', 1),
    (
        '        # Symbol set: "Design space (LHS or CCD)" is the loop\'s data entry',
        '        # Symbol set: "Design space (Latin hypercube)" is the loop\'s data entry',
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


def build_local_copy() -> None:
    """Copy the thesis generator into this folder and correct the two boxes.

    Raises:
        SystemExit: When an anchor is missing, the copy would carry an em
            dash, or the thesis generator is absent.
    """
    if not SOURCE_GENERATOR.is_file():
        _ = sys.stdout.write(f"MISMATCH the thesis generator is missing: {SOURCE_GENERATOR}\n")
        raise SystemExit(1)
    text = SOURCE_GENERATOR.read_text(encoding="utf-8")
    for old, _new, expected in LABEL_RULES:
        found = text.count(old)
        if found != expected:
            _ = sys.stdout.write(
                f"MISMATCH expected {expected} occurrence(s) of the label anchor, found {found}\n",
            )
            raise SystemExit(1)
    for old, new, _expected in LABEL_RULES:
        text = text.replace(old, new, 1)
    # WHY: the thesis file carries one em dash in a comment. The house rule
    # forbids that character anywhere in this folder, so the copy drops it;
    # the line is a comment, so nothing that is drawn changes with it.
    dashes = text.count(EM_DASH)
    text = text.replace(EM_DASH, "-")
    if dashes != 1:
        _ = sys.stdout.write(f"MISMATCH expected one em dash in the source, found {dashes}\n")
        raise SystemExit(1)
    _ = LOCAL_GENERATOR.write_text(text, encoding="utf-8")
    _ = sys.stdout.write("the local copy carries the corrected loop boxes\n")


def render() -> None:
    """Draw the corrected flowchart with the thesis interpreter.

    Raises:
        SystemExit: When the interpreter, the drawing guards or the file
            size do not come out as expected.
    """
    if not THESIS_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the thesis interpreter is missing: {THESIS_PYTHON}\n")
        raise SystemExit(1)
    if LOCAL_OUTPUT.is_file():
        _ = LOCAL_OUTPUT.unlink()
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(THESIS_PYTHON), str(LOCAL_GENERATOR)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr if completed.stderr is not None else ""
        tail = stderr[-1200:]
        if len(tail) == 0:
            tail = completed.stdout[-1200:]
        _ = sys.stdout.write(f"MISMATCH the generator refused to draw:\n{tail}\n")
        raise SystemExit(1)
    if not LOCAL_OUTPUT.is_file() or LOCAL_OUTPUT.stat().st_size < MIN_PICTURE_BYTES:
        size = LOCAL_OUTPUT.stat().st_size if LOCAL_OUTPUT.is_file() else 0
        _ = sys.stdout.write(f"MISMATCH the drawing is only {size} bytes\n")
        raise SystemExit(1)
    _ = sys.stdout.write(f"drawn {LOCAL_OUTPUT.name}, {LOCAL_OUTPUT.stat().st_size} bytes\n")


def install() -> str:
    """Put the corrected drawing into the deck folder after backing up.

    Returns:
        The digest of the installed picture.

    Raises:
        SystemExit: When the copy does not match the drawing.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET.is_file():
        _ = TARGET_BACKUP.write_bytes(TARGET.read_bytes())
    _ = shutil.copy2(LOCAL_OUTPUT, TARGET)
    if digest(LOCAL_OUTPUT) != digest(TARGET):
        _ = sys.stdout.write("MISMATCH the installed picture does not match the drawing\n")
        raise SystemExit(1)
    return digest(TARGET)


def main() -> int:
    """Correct the loop boxes, redraw the flowchart and install it.

    Returns:
        Zero when the picture was installed, one when a guard refused.
    """
    try:
        build_local_copy()
        render()
        installed = install()
    except SystemExit:
        return 1
    _ = sys.stdout.write(
        "the flowchart now carries the Latin hypercube and the genetic algorithm\n"
        f"picture sha256 {installed[:16]}\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
