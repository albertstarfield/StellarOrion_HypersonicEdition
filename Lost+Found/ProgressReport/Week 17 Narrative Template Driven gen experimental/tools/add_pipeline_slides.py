#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Add the four elaboration slides of the Optimization Pipeline subsection.

WHY: the owner split the methodology into subsections. The first one,
Methodology: DSMC CFD, is already elaborated; the second one, Methodology:
Optimization Pipeline, carries its flowchart and then four slides: the
design space and its Latin hypercube, the cost function, the genetic
algorithm, and the double pass with the DSMC gate. Every slide uses the
layout the owner approved earlier: picture left, its caption under it, four
short points as stacked cards on the right, provenance under the cards.

The script is a guarded driver: it copies and hash-verifies the four
pictures, measures every point column at the planned type size, counts every
anchor, refuses to write a file that carries an em dash, parses the result
and leaves every file untouched when a single check fails.
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
THESIS_FIGURES = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"
DECK_FIGURES = PROJECT / "figures"
SPEC = PROJECT / "scaffold.json"
TESTS = PROJECT / "tests" / "test_make_pptx.py"
README = PROJECT / "README.md"
FIGURES_README = DECK_FIGURES / "README.md"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
EM_DASH = "\u2014"

ANCHOR = "recall-methodology-optimization"
SUBSECTION = "Methodology: Optimization Pipeline"
LAYOUT = "side_points"

FLOWCHART_ROW = (
    "| 3. Methodology (the optimization flowchart) | `RECALL` | "
    "`METHODOLOGY: THE OPTIMIZATION FLOWCHART` |\n"
)

#: The four slides, in the order they must follow the flowchart.
SLIDES: list[dict[str, object]] = [
    {
        "id": "recall-methodology-pipeline-space",
        "title": "METHODOLOGY: THE DESIGN SPACE",
        "picture": "hiad_design_sensitivity",
        "caption": (
            "The five design variables of the HIAD and the way they set the geometry "
            "of the vehicle."
        ),
        "source": (
            "Source: hiad_design_sensitivity.png from CurrentThesisFinalReport/figures, the "
            "design variable sensitivity figure of Chapter III."
        ),
        "footer": "How the search space is defined. The narration stays editable in PowerPoint.",
        "target": "the slide after the optimization flowchart, opening the pipeline subsection.",
        "note": "The box the search runs in and the Latin hypercube that seeds it.",
        "body": [
            "Five design variables: body radius, torus radius, cone angle, toroid count, mass",
            "The box holds the 6-toroid Rapisarda baseline: 1.5 m, 0.135 m, 60 degrees",
            "A Latin hypercube of 50 individuals seeds one per stratum of every coordinate",
            "No random start, no factorial design and no surrogate-trained start",
        ],
    },
    {
        "id": "recall-methodology-pipeline-cost",
        "title": "METHODOLOGY: THE COST FUNCTION",
        "picture": "ga_convergence",
        "caption": (
            "The recorded convergence of the composite cost of the genetic algorithm over "
            "38 generations."
        ),
        "source": (
            "Source: ga_convergence.png from CurrentThesisFinalReport/figures, drawn by "
            "figures/make_ga_figures.py from the recorded campaign."
        ),
        "footer": "How a design is scored. The narration stays editable in PowerPoint.",
        "target": "the slide after the design space, carrying the cost of a design.",
        "note": "The objective that every candidate is scored against, and its recorded convergence.",
        "body": [
            "The cost is analytic: evaluating it needs no solver call",
            "Four dimensionless terms: heat load, stagnation flux, ballistic coefficient, drag",
            "All terms are non-negative, so the cost is at least zero by construction",
            "The weight on the drag term selects the regime of the heat-load and drag trade",
        ],
    },
    {
        "id": "recall-methodology-pipeline-ga",
        "title": "METHODOLOGY: THE GENETIC ALGORITHM",
        "picture": "ga_design_trajectory",
        "caption": (
            "The path of the generation-best design through the design box, coloured by "
            "generation."
        ),
        "source": (
            "Source: ga_design_trajectory.png from CurrentThesisFinalReport/figures, drawn by "
            "figures/make_ga_figures.py from the recorded campaign."
        ),
        "footer": "How the population evolves. The narration stays editable in PowerPoint.",
        "target": "the slide after the cost function, carrying the operators of the search.",
        "note": "The operators that breed the population and the path the recorded campaign took.",
        "body": [
            "Population of 50 designs evolved for at most 200 generations",
            "Tournament selection k = 3, uniform crossover 0.7, Gaussian mutation 0.1",
            "Elitism copies the best two unchanged, so the best cost never rises",
            "The campaign stopped on stagnation after 38 generations, 1900 evaluations",
        ],
    },
    {
        "id": "recall-methodology-pipeline-gate",
        "title": "METHODOLOGY: DOUBLE PASS AND THE GATE",
        "picture": "fignew_gate_comparison",
        "caption": (
            "The three heat loads the gate compares: flight, analytic prediction and the "
            "DSMC re-simulation."
        ),
        "source": (
            "Source: fignew_gate_comparison.png from CurrentThesisFinalReport/figures, the "
            "hybrid validation gate comparison."
        ),
        "footer": (
            "How the closed form is corrected against the solver. The narration stays "
            "editable in PowerPoint."
        ),
        "target": "the slide after the genetic algorithm, closing the pipeline subsection.",
        "note": "The two passes, the bounded correction factor and the gate that decides acceptance.",
        "body": [
            "Pass 1 searches in closed form; the pass-1 winner alone is re-simulated",
            "A correction factor from that run is clamped between 0.5 and 2.0",
            "Pass 2 re-runs the same algorithm with the heat-load term weighted by it",
            "The two validations are the only high-fidelity runs of the pipeline",
        ],
    },
]

TEST_RULES: list[tuple[str, str, int]] = [
    ("EXPECTED_FRAME_COUNT = 24", "EXPECTED_FRAME_COUNT = 28", 1),
    ("EXPECTED_METHODOLOGY_FRAME_COUNT = 8", "EXPECTED_METHODOLOGY_FRAME_COUNT = 12", 1),
    ("EXPECTED_FILLED_FRAME_COUNT = 13", "EXPECTED_FILLED_FRAME_COUNT = 17", 1),
    (
        (
            '        "recall-methodology-optimization",\n'
            '        "recall-methodology-shape",\n'
            "    }"
        ),
        (
            '        "recall-methodology-optimization",\n'
            '        "recall-methodology-pipeline-space",\n'
            '        "recall-methodology-pipeline-cost",\n'
            '        "recall-methodology-pipeline-ga",\n'
            '        "recall-methodology-pipeline-gate",\n'
            '        "recall-methodology-shape",\n'
            "    }"
        ),
        1,
    ),
]

README_RULES: list[tuple[str, str, int]] = [
    (
        "the owner's block structure, the twenty-four frames, the palette",
        "the owner's block structure, the twenty-eight frames, the palette",
        1,
    ),
    ("Generated PowerPoint deck (26 slides).", "Generated PowerPoint deck (30 slides).", 1),
    ("* 26 slides, 16:9", "* 30 slides, 16:9", 1),
    ("slides 3 to 26 the twenty-four", "slides 3 to 30 the twenty-eight", 1),
    (
        "the eight methodology slides and their figures",
        "the twelve methodology slides and their figures",
        1,
    ),
]

NEW_ROWS = (
    "| 3. Methodology (the design space and the Latin hypercube) | `RECALL` | "
    "`METHODOLOGY: THE DESIGN SPACE` |\n"
    "| 3. Methodology (the cost function) | `RECALL` | "
    "`METHODOLOGY: THE COST FUNCTION` |\n"
    "| 3. Methodology (the genetic algorithm) | `RECALL` | "
    "`METHODOLOGY: THE GENETIC ALGORITHM` |\n"
    "| 3. Methodology (the double pass and the DSMC gate) | `RECALL` | "
    "`METHODOLOGY: DOUBLE PASS AND THE GATE` |\n"
)

FIGURES_ROW_MARKER = "tools/scaffold_before_slide5_caption.json`. |\n"
NEW_FIGURE_ROWS = (
    "| `METHODOLOGY: THE DESIGN SPACE` | `thesis_hiad_design_sensitivity.png` | "
    "`hiad_design_sensitivity.png` | The three design-variable relations: toroid count "
    "against diameter against the 3.0 m target, cone angle against nose radius, toroid "
    "count against torus radius. |\n"
    "| `METHODOLOGY: THE COST FUNCTION` | `thesis_ga_convergence.png` | "
    "`ga_convergence.png` | The generation-best composite cost of the recorded campaign "
    "over 38 generations and 1900 evaluations. |\n"
    "| `METHODOLOGY: THE GENETIC ALGORITHM` | `thesis_ga_design_trajectory.png` | "
    "`ga_design_trajectory.png` | The generation-best design path through the design box, "
    "with the baseline and optimum values of the three variables. |\n"
    "| `METHODOLOGY: DOUBLE PASS AND THE GATE` | `thesis_fignew_gate_comparison.png` | "
    "`fignew_gate_comparison.png` | The three heat loads the gate compares, against the "
    "acceptance threshold. Not included in the thesis text. |\n"
)

FILES: tuple[Path, ...] = (SPEC, TESTS, README, FIGURES_README)


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


def install_pictures() -> list[str]:
    """Copy the four pictures into the deck folder and verify every copy.

    Returns:
        The digest of each installed picture, in order.

    Raises:
        SystemExit: When a source is missing or a copy does not match.
    """
    digests: list[str] = []
    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for slide in SLIDES:
        name = str(slide["picture"])
        source = THESIS_FIGURES / f"{name}.png"
        target = DECK_FIGURES / f"thesis_{name}.png"
        if not source.is_file():
            _ = sys.stdout.write(f"MISMATCH the thesis figure is missing: {source}\n")
            raise SystemExit(1)
        if target.is_file():
            _ = (BACKUP_DIR / target.name).write_bytes(target.read_bytes())
        _ = shutil.copy2(source, target)
        if digest(source) != digest(target):
            _ = sys.stdout.write(f"MISMATCH the copy of {name}.png does not match\n")
            raise SystemExit(1)
        digests.append(digest(target))
    return digests


def check_measurements() -> list[str]:
    """Return every reason the four point columns would not fit.

    Returns:
        The problems found, empty when all four fit at the planned size.
    """
    import make_pptx as maker  # ruff: ignore[import-outside-top-level]

    inner_width = maker.CONTENT_WIDTH_IN - 2.0 * maker.FILLED_FIGURE_PADDING_IN
    picture_width = min(
        maker.SIDE_POINTS_PICTURE_WIDTH_IN,
        inner_width - maker.SIDE_POINTS_COLUMN_MIN_IN - maker.SIDE_POINTS_GUTTER_IN,
    )
    column_width = inner_width - picture_width - maker.SIDE_POINTS_GUTTER_IN
    area_height = maker.FILLED_CARD_HEIGHT_IN - 2.0 * maker.FILLED_FIGURE_PADDING_IN
    problems: list[str] = []
    for slide in SLIDES:
        source = str(slide["source"])
        source_height = maker._source_box_height(source, column_width)  # ruff: ignore[private-member-access]
        available = area_height - source_height - maker.SIDE_POINTS_CARD_GAP_IN
        points = [str(point) for point in cast("list[object]", slide["body"])]
        planned, _heights = maker._side_points_plan(  # ruff: ignore[private-member-access]
            tuple(points), maker.BODY_FONT, column_width, available,
        )
        if planned < maker.SIDE_POINTS_TEXT_START_PT:
            problems.append(
                f"{slide['id']} drops to {planned:.1f} pt in a {column_width:.2f} in column",
            )
    return problems


def check_anchors() -> list[str]:
    """Return every anchor of the tests and the READMEs that does not match.

    Returns:
        The problems found, empty when every anchor is present once.
    """
    problems: list[str] = []
    tests_text = TESTS.read_text(encoding="utf-8")
    readme_text = README.read_text(encoding="utf-8")
    figures_text = FIGURES_README.read_text(encoding="utf-8")
    for old, _new, expected in TEST_RULES:
        problems.extend(
            [f"tests: expected {expected} occurrence(s), found {tests_text.count(old)}"]
            if tests_text.count(old) != expected
            else [],
        )
    for old, _new, expected in README_RULES:
        problems.extend(
            [f"README: expected {expected} occurrence(s), found {readme_text.count(old)}"]
            if readme_text.count(old) != expected
            else [],
        )
    if readme_text.count(NEW_ROWS) != 0:
        problems.append("README: the four rows are already there")
    if readme_text.count(FLOWCHART_ROW) != 1:
        problems.append("README: the flowchart row was not found")
    if figures_text.count(FIGURES_ROW_MARKER) != 1:
        problems.append("figures/README: the shape row was not found")
    return problems


def build_spec() -> str:
    """Return the specification with the four frames inserted after the flowchart.

    Returns:
        The new text of the specification.

    Raises:
        SystemExit: When a frame already exists or the anchor is missing.
    """
    document = cast("dict[str, object]", json.loads(SPEC.read_text(encoding="utf-8")))
    frames = cast("list[dict[str, object]]", document.get("frames"))
    ids = [str(frame.get("id")) for frame in frames]
    for slide in SLIDES:
        if str(slide["id"]) in ids:
            _ = sys.stdout.write(f"MISMATCH the frame '{slide['id']}' already exists\n")
            raise SystemExit(1)
    if ANCHOR not in ids:
        _ = sys.stdout.write(f"MISMATCH the specification does not hold '{ANCHOR}'\n")
        raise SystemExit(1)
    insert_at = ids.index(ANCHOR) + 1
    for offset, slide in enumerate(SLIDES):
        points = [str(point) for point in cast("list[object]", slide["body"])]
        body = "\n".join(f"- {point}" for point in points)
        frames.insert(
            insert_at + offset,
            {
                "id": slide["id"],
                "section": "RECALL",
                "title": slide["title"],
                "subsection": SUBSECTION,
                "body": body,
                "target_position": slide["target"],
                "note": slide["note"],
                "figure": {
                    "path": f"figures/thesis_{slide['picture']}.png",
                    "caption": slide["caption"],
                    "source": slide["source"],
                    "layout": LAYOUT,
                },
                "footer": slide["footer"],
            },
        )
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def patch_tests() -> str:
    """Return the test file with the counts of the four new frames.

    Returns:
        The new text of the test file.
    """
    text = TESTS.read_text(encoding="utf-8")
    for old, new, _expected in TEST_RULES:
        text = text.replace(old, new, 1)
    _ = ast.parse(text)
    return text


def patch_readme() -> str:
    """Return README.md with the new counts and the four table rows.

    Returns:
        The new text of README.md.
    """
    text = README.read_text(encoding="utf-8")
    for old, new, _expected in README_RULES:
        text = text.replace(old, new, 1)
    return text.replace(FLOWCHART_ROW, FLOWCHART_ROW + NEW_ROWS, 1)


def patch_figures_readme() -> str:
    """Return figures/README.md with the four new picture rows.

    Returns:
        The new text of figures/README.md.
    """
    text = FIGURES_README.read_text(encoding="utf-8")
    return text.replace(FIGURES_ROW_MARKER, FIGURES_ROW_MARKER + NEW_FIGURE_ROWS, 1)


def refuse_em_dash(name: str, text: str) -> None:
    """Stop the run when a document would carry an em dash.

    Args:
        name: The document name for the message.
        text: The document text.

    Raises:
        SystemExit: When the text carries an em dash.
    """
    if EM_DASH in text:
        _ = sys.stdout.write(f"MISMATCH {name} would carry an em dash\n")
        raise SystemExit(1)


def apply_patches() -> tuple[dict[Path, str], list[str]]:
    """Check every guard, install the pictures and build the four documents.

    Returns:
        The new text of every document by path, and the digest of each
        installed picture.

    Raises:
        SystemExit: When a guard refuses.
    """
    problems = check_measurements() + check_anchors()
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        raise SystemExit(1)
    digests = install_pictures()
    built = {
        SPEC: build_spec(),
        TESTS: patch_tests(),
        README: patch_readme(),
        FIGURES_README: patch_figures_readme(),
    }
    for path, text in built.items():
        refuse_em_dash(path.name, text)
    return built, digests


def main() -> int:
    """Install the pictures, then patch the specification, the tests and the READMEs.

    Returns:
        Zero when every file was written, one when a guard refused.
    """
    digests: list[str] = []
    try:
        built, digests = apply_patches()
        _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        for path in FILES:
            _ = (BACKUP_DIR / f"{path.name}.before_pipeline_slides").write_bytes(path.read_bytes())
        for path, text in built.items():
            _ = path.write_text(text, encoding="utf-8")
    except SystemExit:
        return 1
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, json.JSONDecodeError) as error:
        _ = sys.stdout.write(f"MISMATCH {type(error).__name__}: {error}\n")
        return 1
    joined = ", ".join(str(slide["id"]) for slide in SLIDES)
    _ = sys.stdout.write(f"the four pipeline slides are in: {joined}\n")
    _ = sys.stdout.write(f"pictures sha256 {' '.join(d[:16] for d in digests)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
