#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Give every slide of the DSMC CFD subsection its governing equation.

WHY: the owner asked for one more slide per DSMC CFD slide carrying the
equation that governs it. The seven equations are typeset into pictures of
their own, and each picture is placed directly after the slide it belongs to,
in the same subsection and the same picture left, cards right layout.

The script is a guarded one-shot driver: it verifies the seven pictures,
measures every title and every card, refuses to write when a measurement or
an anchor does not match, and backs up all three files first.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

SPEC = PROJECT / "scaffold.json"
TESTS = PROJECT / "tests" / "test_make_pptx.py"
README = PROJECT / "README.md"
FIGURES_README = PROJECT / "figures" / "README.md"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
SPEC_BACKUP = BACKUP_DIR / "scaffold_before_equations.json"
TESTS_BACKUP = BACKUP_DIR / "test_make_pptx_before_equations.py"
README_BACKUP = BACKUP_DIR / "README_before_equations.md"
FIGURES_BACKUP = BACKUP_DIR / "figures_README_before_equations.md"
EM_DASH = "\u2014"
#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 5000
TITLE_BUDGET_IN = 8.165
SUBSECTION = "Methodology: DSMC CFD"
FOOTER = "The equation that governs the step. The narration stays editable in PowerPoint."

#: (anchor frame id, equation frame id, title, picture, caption, source, cards)
PLACEMENTS: list[tuple[str, str, str, str, str, str, list[str]]] = [
    (
        "recall-methodology-shape",
        "recall-methodology-equation-shape",
        "GOVERNING EQUATION: THE SHAPE",
        "thesis_equation_shape.png",
        "The two equations that turn the design vector into the geometry of the vehicle.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "Nose radius follows the body radius: R_n is 0.3667 times X_1",
            "R_max adds the body radius and the torus stack along the cone",
            "The half-cone angle sets gamma: pi divided by two, minus X_3",
            "Five variables move the whole geometry inside one design box",
        ],
    ),
    (
        "recall-methodology-setup",
        "recall-methodology-equation-setup",
        "GOVERNING EQUATION: THE SOLVER",
        "thesis_equation_setup.png",
        "The equation the particle solver answers, and the cross-section it scatters with.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "The Boltzmann equation governs the distribution function of the gas",
            "Streaming and the force term balance the collision term",
            "DSMC answers it statistically instead of solving it directly",
            "The variable soft sphere cross-section sets how the particles scatter",
        ],
    ),
    (
        "recall-methodology-mesh",
        "recall-methodology-equation-mesh",
        "GOVERNING EQUATION: THE MESH",
        "thesis_equation_mesh.png",
        "The relation that decides how small a cell of the grid may be.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "Knudsen number is the mean free path divided by the length L",
            "The mean free path is one over square root two, pi, d squared and n",
            "The cell width must stay below the mean free path of the gas",
            "That is why the reference grid is finer than the local spacing",
        ],
    ),
    (
        "recall-methodology-convergence",
        "recall-methodology-equation-convergence",
        "GOVERNING EQUATION: THE CONVERGENCE",
        "thesis_equation_convergence.png",
        "The criterion that decides when a particle run is statistically converged.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "Statistical noise falls with the square root of the samples",
            "SPARTA averages surface force and energy every hundred steps",
            "Converged when drag and heat flux change by under two percent",
            "The baseline runs reach it after 500 to 1100 particle steps",
        ],
    ),
    (
        "recall-methodology-convection",
        "recall-methodology-equation-convection",
        "GOVERNING EQUATION: THE CONVECTION",
        "thesis_equation_convection.png",
        "The correlation that carries the convective load of every candidate.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "Sutton-Graves: the flux scales with the cube of the velocity",
            "It falls with the square root of the nose radius R_N",
            "The constant is 1.7415 times ten to the minus four for air",
            "At 3378 m/s and 1.5 m it gives 15.36 W per square centimetre",
        ],
    ),
    (
        "recall-methodology-conduction",
        "recall-methodology-equation-conduction",
        "GOVERNING EQUATION: THE CONDUCTION",
        "thesis_equation_conduction.png",
        "The balance that splits the arriving heat between the stack and the surface.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "The wall balance is conduction across the stack plus re-radiation",
            "R is the sum of the ply resistances, 0.3056 m^2 K per watt",
            "The backface model raises the temperature with its thermal lag",
            "The chain runs one dimension along the stack, element by element",
        ],
    ),
    (
        "recall-methodology-radiation",
        "recall-methodology-equation-radiation",
        "GOVERNING EQUATION: THE RADIATION",
        "thesis_equation_radiation.png",
        "The equilibrium that sets the temperature of the hot face of the vehicle.",
        "Source: typeset from chapter 3 of the thesis by tools/make_equation_pictures.py.",
        [
            "A grey body radiates q = eps sigma T to the fourth power",
            "The emissivity of the outer Nicalon SiC ply is 0.75",
            "Equilibrium divides the incoming flux by eps sigma and takes the root",
            "The surface temperature is therefore set by the radiation alone",
        ],
    ),
]

OLD_TEST_RULES: list[tuple[str, str, int]] = [
    ("EXPECTED_FRAME_COUNT = 28", "EXPECTED_FRAME_COUNT = 35", 1),
    ("EXPECTED_METHODOLOGY_FRAME_COUNT = 12", "EXPECTED_METHODOLOGY_FRAME_COUNT = 19", 1),
    ("EXPECTED_FILLED_FRAME_COUNT = 17", "EXPECTED_FILLED_FRAME_COUNT = 24", 1),
    (
        '        "recall-methodology-shape",\n    }',
        '        "recall-methodology-shape",\n'
        + "".join(f'        "{frame_id}",\n' for _anchor, frame_id, *_rest in PLACEMENTS)
        + "    }",
        1,
    ),
]

README_RULES: list[tuple[str, str, int]] = [
    ("the twenty-eight frames, the palette", "the thirty-five frames, the palette", 1),
    ("Generated PowerPoint deck (30 slides).", "Generated PowerPoint deck (37 slides).", 1),
    ("* 30 slides, 16:9", "* 37 slides, 16:9", 1),
    (
        "* Slide 1 is the cover, slide 2 the outline, slides 3 to 30 the twenty-eight\n  frames.",
        "* Slide 1 is the cover, slide 2 the outline, slides 3 to 37 the thirty-five\n  frames.",
        1,
    ),
    ("the twelve methodology slides and their figures", "the nineteen methodology slides and their figures", 1),
]

NEW_ROWS = "".join(
    "| 3. Methodology (the equation that governs the step) | `RECALL` | "
    f"`{title}` |\n"
    for _anchor, _frame_id, title, *_rest in PLACEMENTS
)
ROW_ANCHOR = (
    "| 3. Methodology (the re-radiation channel) | `RECALL` | "
    "`METHODOLOGY: THE RE-RADIATION CHANNEL` |"
)

FIGURES_ROW_ANCHOR = "| `METHODOLOGY: DOUBLE PASS AND THE GATE` | `thesis_fignew_gate_comparison.png` |"
NEW_FIGURE_ROWS = "".join(
    f"| `{title}` | `{picture}` | Typeset in this folder | {caption} |\n"
    for _anchor, _frame_id, title, picture, caption, _source, _cards in PLACEMENTS
)


def measure() -> list[str]:
    """Return every reason the new frames would not fit their slides.

    Returns:
        The problems found, empty when every title and card fits.
    """
    import make_pptx as maker  # ruff: ignore[import-outside-top-level]

    problems: list[str] = []
    for _anchor, frame_id, title, picture, _caption, _source, cards in PLACEMENTS:
        width = maker.measure_text_inches(title, maker.TITLE_FONT, maker.FRAME_TITLE_SIZE.pt)
        if width > TITLE_BUDGET_IN:
            problems.append(f"{frame_id}: the title {title!r} measures {width:.2f} in")
        path = PROJECT / "figures" / picture
        if not path.is_file() or path.stat().st_size < MIN_PICTURE_BYTES:
            problems.append(f"{frame_id}: the picture {picture} is missing or too small")
        plan = maker._side_points_plan(  # ruff: ignore[private-member-access]
            tuple(cards),
            maker.BODY_FONT,
            maker.SIDE_POINTS_COLUMN_MIN_IN,
            4.20,
        )
        if plan[0] != maker.SIDE_POINTS_TEXT_START_PT:
            problems.append(f"{frame_id}: the cards land at {plan[0]:.1f} pt")
    return problems


def apply_spec() -> dict[Path, str]:
    """Return the new specification, the tests and both README files.

    Returns:
        The new text of every file the run writes.

    Raises:
        SystemExit: When an anchor is missing or a measurement fails.
    """
    problems = measure()
    tests_text = TESTS.read_text(encoding="utf-8")
    readme_text = README.read_text(encoding="utf-8")
    figures_text = FIGURES_README.read_text(encoding="utf-8")
    for old, _new, expected in OLD_TEST_RULES:
        found = tests_text.count(old)
        if found != expected:
            problems.append(f"tests: expected {expected} occurrence(s), found {found}: {old[:50]!r}")
    for old, _new, expected in README_RULES:
        found = readme_text.count(old)
        if found != expected:
            problems.append(f"README: expected {expected} occurrence(s), found {found}: {old[:50]!r}")
    if readme_text.count(ROW_ANCHOR) != 1:
        problems.append("README: the section 4 re-radiation row is not unique")
    if figures_text.count(FIGURES_ROW_ANCHOR) != 1:
        problems.append("figures/README: the gate row is not unique")
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        raise SystemExit(1)

    document = json.loads(SPEC.read_text(encoding="utf-8"))
    frames: list[dict[str, object]] = document["frames"]
    ids = [str(frame["id"]) for frame in frames]
    for anchor, frame_id, *_rest in PLACEMENTS:
        if anchor not in ids:
            _ = sys.stdout.write(f"MISMATCH the specification does not hold '{anchor}'\n")
            raise SystemExit(1)
        if frame_id in ids:
            _ = sys.stdout.write(f"MISMATCH the frame '{frame_id}' already exists\n")
            raise SystemExit(1)
    for anchor, frame_id, title, picture, caption, source, cards in reversed(PLACEMENTS):
        frames.insert(
            ids.index(anchor) + 1,
            {
                "id": frame_id,
                "section": "RECALL",
                "title": title,
                "body": "".join(f"- {card}\n" for card in cards).rstrip("\n"),
                "target_position": "the slide right after the step it governs, inside the "
                "same subsection.",
                "note": f"The governing equation of {anchor}: {caption}",
                "figure": {
                    "path": f"figures/{picture}",
                    "caption": caption,
                    "source": source,
                    "layout": "side_points",
                },
                "footer": FOOTER,
                "subsection": SUBSECTION,
            },
        )
    spec_text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"

    for old, new, _expected in OLD_TEST_RULES:
        tests_text = tests_text.replace(old, new, 1)
    _ = ast.parse(tests_text)

    lines = readme_text.split("\n")
    position = next(
        (index for index, line in enumerate(lines) if line == ROW_ANCHOR),
        -1,
    )
    if position < 0:
        _ = sys.stdout.write("MISMATCH the section 4 row was not found\n")
        raise SystemExit(1)
    lines = lines[: position + 1] + NEW_ROWS.rstrip("\n").split("\n") + lines[position + 1 :]
    readme_text = "\n".join(lines)
    for old, new, _expected in README_RULES:
        readme_text = readme_text.replace(old, new, 1)

    figures_text = figures_text.replace(
        FIGURES_ROW_ANCHOR,
        FIGURES_ROW_ANCHOR + "\n" + NEW_FIGURE_ROWS.rstrip("\n"),
        1,
    )
    for name, text in (
        ("the specification", spec_text),
        ("the tests", tests_text),
        ("README.md", readme_text),
        ("figures/README.md", figures_text),
    ):
        if EM_DASH in text:
            _ = sys.stdout.write(f"MISMATCH {name} would carry an em dash\n")
            raise SystemExit(1)
    return {
        SPEC: spec_text,
        TESTS: tests_text,
        README: readme_text,
        FIGURES_README: figures_text,
    }


def main() -> int:
    """Write the seven equation frames into the specification and the docs.

    Returns:
        Zero when every file was written, one when a guard refused.

    """
    try:
        updates = apply_spec()
    except SystemExit as error:
        if isinstance(error.code, int):
            return error.code
        return 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        _ = sys.stdout.write(f"MISMATCH {type(error).__name__}: {error}\n")
        return 1
    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = {
        SPEC: SPEC_BACKUP,
        TESTS: TESTS_BACKUP,
        README: README_BACKUP,
        FIGURES_README: FIGURES_BACKUP,
    }
    for path, text in updates.items():
        _ = backups[path].write_bytes(path.read_bytes())
        _ = path.write_text(text, encoding="utf-8")
    _ = sys.stdout.write("seven governing equation frames are in the specification\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
