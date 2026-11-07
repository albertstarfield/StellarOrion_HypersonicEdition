# Copyright (c) 2026 StellarOrion Week 17 narrative scaffold.
# SPDX-License-Identifier: MIT
"""Tests for the Week 17 narrative scaffold generator.

WHY THIS EXISTS
---------------
The generator writes a Microsoft PowerPoint file that a human will open, edit by
hand and hand back. A silent regression in it would either corrupt the deck or
quietly lose the owner's words, so every behaviour the tool promises is pinned
here: the specification is read strictly, the pure helpers keep their contracts,
the generated package is structurally sound, and the update mode never overwrites
something the owner wrote.

THEORIES
---------
1. The specification is the single source of truth, so a malformed specification
   must fail loudly at load time rather than produce a half-built deck.
2. A slot body that still equals the body recorded in the speaker notes is an
   untouched placeholder and may be refreshed. A body that differs was written
   by the owner and must survive the update.
3. A slide that matches no frame belongs to the owner and must be left alone.

APPLICATIONS
------------
    .venv/bin/python -m pytest

CITATIONS
---------
* pytest -- https://docs.pytest.org/
* python-pptx 1.0.2 -- https://python-pptx.readthedocs.io/
* EasyPPTX 0.11.0 -- https://Ameyanagi.github.io/EasyPPTX/
"""

from __future__ import annotations

import json
import operator
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import zipfile
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from PIL import Image
from pptx import Presentation as NativePresentation

import figure_layout
import make_pptx
import scaffold_logic
import sky_background

if TYPE_CHECKING:
    from pptx.presentation import Presentation as NativeDeck
    from pptx.shapes.autoshape import Shape
    from pptx.slide import Slide

EXPECTED_SECTION_COUNT = 5
EXPECTED_FRAME_COUNT = 23
EXPECTED_PREVIOUS_ISSUE_COUNT = 4
EXPECTED_ISSUE_CARD_COUNT = 4
EXPECTED_ISSUE_COLUMN_COUNT = 2
EXPECTED_ISSUE_ROW_COUNT = 2
EXPECTED_METHODOLOGY_FRAME_COUNT = 7
#: The fewest points a methodology slide must carry as cards under its picture.
EXPECTED_METHODOLOGY_MIN_POINTS = 3
EXPECTED_METHODOLOGY_CARD_COUNT = 4
EXPECTED_FILLED_FRAME_COUNT = 12
EXPECTED_SLIDE_WIDTH_EMU = 12192000
EXPECTED_LANDSCAPE_ASPECT = 1.5
EXPECTED_MILESTONE_COUNT = 5
TALL_PICTURE_WIDTH_PX = 400
TALL_PICTURE_HEIGHT_PX = 1200
EXPECTED_SLIDE_HEIGHT_EMU = 6858000
PROJECT = Path(__file__).resolve().parent.parent
SPEC = PROJECT / "scaffold.json"
VENV_PYTHON = PROJECT / ".venv" / "bin" / "python"


@pytest.fixture
def spec() -> make_pptx.Scaffold:
    """Return the real scaffold specification loaded from disk."""
    return make_pptx.load_spec(SPEC)


@pytest.fixture
def sky_path(spec: make_pptx.Scaffold) -> Path:
    """Return the sky picture that the slides of the deck sit on.

    Returns:
        The path of the sky picture inside the figures folder.
    """
    return sky_background.ensure_sky_image(spec.palette, PROJECT / "figures")


@pytest.fixture
def built(tmp_path: Path, sky_path: Path) -> Path:
    """Build a deck from the real specification into a temporary folder.

    Returns:
        The path of the generated deck inside the temporary folder.
    """
    output = tmp_path / "deck.pptx"
    _ = make_pptx.build_regenerate(
        make_pptx.load_spec(SPEC),
        output,
        with_sections=True,
        sky_path=sky_path,
    )
    return output


# ---------------------------------------------------------------------------
# The pure helpers carry the contracts that CrossHair proves symbolically.
# ---------------------------------------------------------------------------


def test_collapse_whitespace_joins_runs() -> None:
    """The helper collapses every whitespace run into a single space."""
    assert scaffold_logic.collapse_whitespace("  a \n b\tc  ") == "a b c"


def test_collapse_whitespace_keeps_empty_string_empty() -> None:
    """An empty string stays empty instead of becoming a single space."""
    assert len(scaffold_logic.collapse_whitespace("")) == 0


def test_escape_xml_escapes_the_four_dangerous_characters() -> None:
    """The XML helper escapes the ampersand, both angle brackets and the quote."""
    assert scaffold_logic.escape_xml('a&b<c>d"e') == "a&amp;b&lt;c&gt;d&quot;e"


def test_escape_xml_leaves_the_apostrophe_alone() -> None:
    """The apostrophe is not escaped because it is safe inside a quoted value."""
    assert scaffold_logic.escape_xml("it's") == "it's"


def test_is_hex_colour_accepts_six_digits_only() -> None:
    """The colour checker accepts exactly six hexadecimal digits."""
    assert scaffold_logic.is_hex_colour("DCE8E3")
    assert not scaffold_logic.is_hex_colour("DCE8E")
    assert not scaffold_logic.is_hex_colour("DCE8E33")
    assert not scaffold_logic.is_hex_colour("GGGGGG")


def test_require_text_returns_the_stripped_value() -> None:
    """A valid text field is returned without its surrounding whitespace."""
    assert scaffold_logic.require_text("  value  ", "a field") == "value"


def test_require_text_rejects_a_non_string() -> None:
    """A non-string field is rejected with a message that names the field."""
    with pytest.raises(scaffold_logic.ScaffoldError, match="to be a string"):
        _ = scaffold_logic.require_text(7, "a field")


def test_require_text_rejects_a_blank_string() -> None:
    """A blank string is rejected because every field here must carry content."""
    with pytest.raises(scaffold_logic.ScaffoldError, match="non-empty"):
        _ = scaffold_logic.require_text("   ", "a field")


def test_require_mapping_rejects_a_non_object() -> None:
    """A field that should be a JSON object is rejected when it is not one."""
    with pytest.raises(scaffold_logic.ScaffoldError, match="to be a JSON object"):
        _ = scaffold_logic.require_mapping([1, 2], "a block")


# ---------------------------------------------------------------------------
# The specification is read strictly.
# ---------------------------------------------------------------------------


def test_load_spec_reads_the_real_specification(spec: make_pptx.Scaffold) -> None:
    """The shipped specification yields the five owner blocks and eleven frames."""
    assert len(spec.sections) == EXPECTED_SECTION_COUNT
    assert len(spec.frames) == EXPECTED_FRAME_COUNT
    assert len(spec.frames_in("RECALL")) > 0


def test_specification_frame_ids_are_unique(spec: make_pptx.Scaffold) -> None:
    """Every frame carries its own identifier, because the identifier is the key."""
    identifiers = [frame.id for frame in spec.frames]
    assert len(set(identifiers)) == len(identifiers)


def test_specification_has_no_em_dash(spec: make_pptx.Scaffold) -> None:
    """The house rule forbids an em dash anywhere in the specification."""
    assert make_pptx.EM_DASH not in json.dumps(
        {"sections": spec.sections, "frames": [frame.body for frame in spec.frames]},
    )


def test_load_spec_rejects_a_frame_in_an_unknown_section(tmp_path: Path) -> None:
    """A frame that names a section the specification never declares is rejected."""
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document["frames"][0]["section"] = "NO SUCH BLOCK"
    broken = tmp_path / "broken.json"
    _ = broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(scaffold_logic.ScaffoldError, match="owner block"):
        _ = make_pptx.load_spec(broken)


def test_load_spec_rejects_a_duplicate_frame_id(tmp_path: Path) -> None:
    """Two frames that claim the same identifier are rejected."""
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document["frames"][1]["id"] = document["frames"][0]["id"]
    broken = tmp_path / "broken.json"
    _ = broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(scaffold_logic.ScaffoldError, match="repeats the frame id"):
        _ = make_pptx.load_spec(broken)


def test_load_spec_rejects_a_bad_colour(tmp_path: Path) -> None:
    """A palette entry that is not a hexadecimal colour is rejected."""
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document["palette"]["NarraInk"] = "NOTHEX"
    broken = tmp_path / "broken.json"
    # WHY: the graphic of a frame is resolved against the folder of the
    # specification, so a copy of the specification needs its pictures too.
    _ = shutil.copytree(SPEC.parent / "figures", tmp_path / "figures")
    _ = broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(scaffold_logic.ScaffoldError, match="hexadecimal"):
        _ = make_pptx.load_spec(broken)


def test_load_spec_rejects_a_missing_file(tmp_path: Path) -> None:
    """A specification that does not exist is reported, not silently accepted."""
    with pytest.raises(scaffold_logic.ScaffoldError, match="not found"):
        _ = make_pptx.load_spec(tmp_path / "absent.json")


# ---------------------------------------------------------------------------
# The generated package is structurally sound.
# ---------------------------------------------------------------------------


def test_build_writes_the_expected_number_of_slides(built: Path, spec: make_pptx.Scaffold) -> None:
    """The deck holds the cover, the outline and one slide per frame."""
    deck = NativePresentation(str(built))
    assert len(deck.slides) == 2 + len(spec.frames)


def test_build_uses_the_wide_screen_size(built: Path) -> None:
    """The deck is 16:9, because a projected slide must be 16:9."""
    deck = NativePresentation(str(built))
    assert deck.slide_width == EXPECTED_SLIDE_WIDTH_EMU
    assert deck.slide_height == EXPECTED_SLIDE_HEIGHT_EMU


def test_every_frame_slide_carries_its_machine_key(built: Path, spec: make_pptx.Scaffold) -> None:
    """A frame is anchored by its slot box, or by its panel when it has no narration."""
    deck = NativePresentation(str(built))
    names = {shape.name for slide in deck.slides for shape in slide.shapes}
    for frame in spec.frames:
        if len(frame.body) == 0 and frame.figure is not None:
            assert f"figure:{frame.id}" in names
        else:
            assert f"slot:{frame.id}" in names


def test_the_section_list_carries_one_brace_wrapped_identifier(built: Path) -> None:
    """The PowerPoint section identifiers are single brace-wrapped GUIDs."""
    with zipfile.ZipFile(built) as archive:
        text = archive.read("ppt/presentation.xml").decode("utf-8")
    assert "{{" not in text
    assert "}}" not in text


def test_verify_package_accepts_the_generated_deck(built: Path) -> None:
    """The generator's own package check passes on what it just wrote."""
    assert len(make_pptx.verify_package(built)) > 0


def test_verify_presentation_accepts_the_generated_deck(
    built: Path,
    spec: make_pptx.Scaffold,
) -> None:
    """The generator's own content check passes on what it just wrote."""
    assert len(make_pptx.verify_presentation(built, spec, strict=True)) > 0


# ---------------------------------------------------------------------------
# Update mode: the owner's words survive.
# ---------------------------------------------------------------------------


def _slot_text(deck_path: Path, frame_id: str) -> str:
    """Return the visible text of the slot box with the given identifier."""
    deck = NativePresentation(str(deck_path))
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.name == f"slot:{frame_id}":
                return cast("Shape", shape).text_frame.text
    return ""


def _write_owner_text(deck_path: Path, frame_id: str, text: str) -> None:
    """Overwrite the slot box of one frame, the way an owner would in PowerPoint."""
    deck = NativePresentation(str(deck_path))
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.name == f"slot:{frame_id}":
                frame = cast("Shape", shape).text_frame
                frame.clear()
                frame.paragraphs[0].add_run().text = text
    deck.save(str(deck_path))


def test_update_keeps_the_owner_text(
    built: Path,
    spec: make_pptx.Scaffold,
    tmp_path: Path,
    sky_path: Path,
) -> None:
    """A slot the owner filled in by hand keeps its words when the tool runs again."""
    _ = shutil.copy(built, tmp_path / "owned.pptx")
    _write_owner_text(tmp_path / "owned.pptx", "recall-latar-belakang", "OWNER WORDS")
    _ = make_pptx.build_update(
        spec,
        tmp_path / "owned.pptx",
        force_bodies=False,
        force_titles=False,
        rebuild_sections=False,
        sky_path=sky_path,
    )
    assert _slot_text(tmp_path / "owned.pptx", "recall-latar-belakang") == "OWNER WORDS"


def test_update_refreshes_an_untouched_slot(
    built: Path,
    spec: make_pptx.Scaffold,
    tmp_path: Path,
    sky_path: Path,
) -> None:
    """A slot nobody touched is refreshed from the specification."""
    _ = shutil.copy(built, tmp_path / "owned.pptx")
    _ = make_pptx.build_update(
        spec,
        tmp_path / "owned.pptx",
        force_bodies=False,
        force_titles=False,
        rebuild_sections=False,
        sky_path=sky_path,
    )
    expected = next(frame for frame in spec.frames if frame.id == "ending-conclusion").body
    assert _slot_text(tmp_path / "owned.pptx", "ending-conclusion") == expected


def test_update_refuses_to_overwrite_the_owner_text_without_the_force_flag(
    built: Path,
    spec: make_pptx.Scaffold,
    tmp_path: Path,
    sky_path: Path,
) -> None:
    """Even with the force flag absent, an owner-written slot is left alone."""
    _ = shutil.copy(built, tmp_path / "owned.pptx")
    _write_owner_text(tmp_path / "owned.pptx", "recall-latar-belakang", "OWNER WORDS")
    _ = make_pptx.build_update(
        spec,
        tmp_path / "owned.pptx",
        force_bodies=False,
        force_titles=False,
        rebuild_sections=False,
        sky_path=sky_path,
    )
    assert "OWNER WORDS" in _slot_text(tmp_path / "owned.pptx", "recall-latar-belakang")


def test_update_reports_a_missing_deck(spec: make_pptx.Scaffold, tmp_path: Path, sky_path: Path) -> None:
    """Update mode refuses to run when there is no deck to update."""
    with pytest.raises(scaffold_logic.ScaffoldError, match="does not exist"):
        _ = make_pptx.build_update(
            spec,
            tmp_path / "absent.pptx",
            force_bodies=False,
            force_titles=False,
            rebuild_sections=False,
            sky_path=sky_path,
        )


# ---------------------------------------------------------------------------
# The command line is the contract the owner actually uses.
# ---------------------------------------------------------------------------


def test_the_command_line_builds_a_deck(tmp_path: Path) -> None:
    """Running the tool as the owner runs it produces a verified deck."""
    output = tmp_path / "cli.pptx"
    # ruff: ignore[subprocess-without-shell-equals-true]
    result = subprocess.run(
        [str(VENV_PYTHON), str(PROJECT / "make_pptx.py"), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(PROJECT),
    )
    assert result.returncode == 0, result.stderr
    assert "written:" in result.stdout
    assert output.exists()


def test_the_command_line_reports_a_missing_specification(tmp_path: Path) -> None:
    """A wrong specification path is reported on the error channel, not swallowed."""
    # ruff: ignore[subprocess-without-shell-equals-true]
    result = subprocess.run(
        [
            str(VENV_PYTHON),
            str(PROJECT / "make_pptx.py"),
            "--spec",
            str(tmp_path / "absent.json"),
            "--output",
            str(tmp_path / "cli.pptx"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(PROJECT),
    )
    assert result.returncode == 1
    assert "FAILED" in result.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))


def _name_of(shape: object) -> str:
    """Return the name of a shape, or an empty string when it carries none."""
    raw = cast("Shape", shape).name
    return raw if raw is not None else ""


def test_the_recall_frames_carry_a_graphic(spec: make_pptx.Scaffold) -> None:
    """Every frame that carries a graphic names the picture it shows."""
    filled = [frame for frame in spec.frames if frame.figure is not None]
    assert len(filled) == EXPECTED_FILLED_FRAME_COUNT
    assert {frame.id for frame in filled} == {
        "recall-latar-belakang",
        "recall-tujuan-scope",
        "recall-methodology",
        "recall-flowchart",
        "recall-previous-issue-1",
        "recall-methodology-setup",
        "recall-methodology-mesh",
        "recall-methodology-convergence",
        "recall-methodology-convection",
        "recall-methodology-conduction",
        "recall-methodology-radiation",
        "recall-methodology-optimization",
    }


def test_every_graphic_is_there(spec: make_pptx.Scaffold) -> None:
    """The picture of every filled frame exists and names its source."""
    for frame in spec.frames:
        if frame.figure is None:
            continue
        assert frame.figure.path.exists()
        assert len(frame.figure.caption) > 0
        assert frame.figure.source.startswith("Source: ")


def test_the_deck_carries_the_graphics(built: Path, spec: make_pptx.Scaffold) -> None:
    """Every frame with a graphic has its panel and its caption on the slide."""
    deck = NativePresentation(str(built))
    slides = list(deck.slides)
    for frame in spec.frames:
        if frame.figure is None:
            continue
        host = None
        for slide in slides:
            for shape in slide.shapes:
                if shape.name in {f"slot:{frame.id}", f"figure:{frame.id}"}:
                    host = slide
        assert host is not None
        names = [shape.name for shape in host.shapes]
        assert f"figure:{frame.id}" in names
        assert f"figure:{frame.id}_image" in names
        assert "figure_caption" in names
        assert "figure_source" in names


def test_the_graphic_stays_inside_its_panel(built: Path) -> None:
    """The picture on a filled slide is inside the panel that carries it."""
    deck = NativePresentation(str(built))
    for slide in deck.slides:
        panels = [
            shape
            for shape in slide.shapes
            if (_name_of(shape)).startswith("figure:") and not (_name_of(shape)).endswith("_image")
        ]
        if len(panels) == 0:
            continue
        panel = cast("Shape", panels[0])
        pictures = [shape for shape in slide.shapes if (_name_of(shape)).endswith("_image")]
        assert len(pictures) == 1
        picture = cast("Shape", pictures[0])
        assert picture.left >= panel.left
        assert picture.top >= panel.top
        assert picture.left + picture.width <= panel.left + panel.width
        assert picture.top + picture.height <= panel.top + panel.height


def _cards_of(slide: Slide, frame_id: str) -> list[Shape]:
    """Return the narration cards of a frame, in reading order.

    Args:
        slide: The slide to look at.
        frame_id: The identifier of the frame.

    Returns:
        The card shapes, the first card first.

    """
    cards: list[Shape] = []
    extras: list[tuple[int, Shape]] = []
    for raw_shape in slide.shapes:
        shape = cast("Shape", raw_shape)
        name = _name_of(shape)
        if name == f"slot:{frame_id}":
            cards.append(shape)
        elif name.startswith(f"card:{frame_id}#"):
            extras.append((int(name.split("#")[-1]), shape))
    extras.sort(key=operator.itemgetter(0))
    cards.extend(shape for _, shape in extras)
    return cards


def test_the_narration_is_drawn_as_cards(built: Path, spec: make_pptx.Scaffold) -> None:
    """A filled frame carries one card per point, and every point is there."""
    deck = NativePresentation(str(built))
    for slide in deck.slides:
        for frame in spec.frames:
            if frame.figure is None:
                continue
            points = [
                line.strip().removeprefix("- ").removeprefix("* ").strip()
                for line in frame.body.splitlines()
                if len(line.strip()) != 0
            ]
            cards = _cards_of(slide, frame.id)
            if len(cards) == 0:
                continue
            assert len(cards) == len(points)
            joined = " ".join(card.text_frame.text for card in cards)
            for point in points:
                # WHY: a card of a band carries a heading and a detail on two
                # lines, so the two parts are looked for on their own.
                heading, _, detail = point.partition(":")
                assert heading.strip() in joined
                assert detail.strip() in joined


def test_the_cards_run_horizontally_inside_the_content_area(
    built: Path, spec: make_pptx.Scaffold,
) -> None:
    """The cards of a frame run in rows, do not overlap and stay in the content area."""
    deck = NativePresentation(str(built))
    scale = make_pptx.EMU_PER_INCH
    area_left = make_pptx.MARGIN_X_IN * scale
    area_right = (make_pptx.MARGIN_X_IN + make_pptx.CONTENT_WIDTH_IN) * scale
    area_top = make_pptx.FILLED_CARD_TOP_IN * scale
    area_bottom = (make_pptx.FILLED_CARD_TOP_IN + make_pptx.FILLED_CARD_HEIGHT_IN) * scale
    tolerance = scale / 100.0
    columns = make_pptx.FILLED_BAND_COLUMNS
    for slide in deck.slides:
        for frame in spec.frames:
            if frame.figure is None:
                continue
            cards = _cards_of(slide, frame.id)
            if len(cards) == 0:
                continue
            rectangles = []
            rows: dict[float, int] = {}
            for card in cards:
                assert card.left >= area_left - tolerance
                assert card.left + card.width <= area_right + tolerance
                assert card.top >= area_top - tolerance
                assert card.top + card.height <= area_bottom + tolerance
                rectangles.append((card.left, card.top, card.left + card.width, card.top + card.height))
                key = round(card.top / scale, 3)
                rows[key] = rows.get(key, 0) + 1
            for index, first in enumerate(rectangles):
                for second in rectangles[index + 1 :]:
                    overlap_x = min(first[2], second[2]) - max(first[0], second[0])
                    overlap_y = min(first[3], second[3]) - max(first[1], second[1])
                    assert overlap_x <= tolerance or overlap_y <= tolerance
            expected_rows = (len(cards) + columns - 1) // columns
            assert len(rows) == expected_rows
            for members in rows.values():
                assert members <= columns


def test_the_flowchart_frame_carries_only_a_graphic(spec: make_pptx.Scaffold) -> None:
    """The workflow frame is owned by its picture and carries no narration."""
    frame = next(frame for frame in spec.frames if frame.id == "recall-flowchart")
    assert len(frame.body) == 0
    assert frame.figure is not None
    assert frame.figure.layout == "feature"
    assert frame.figure.path.exists()


def test_the_flowchart_frame_has_no_narration_cards(built: Path) -> None:
    """The workflow frame carries its picture and no narration cards."""
    deck = NativePresentation(str(built))
    host = None
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.name == "figure:recall-flowchart":
                host = slide
    assert host is not None
    names = [shape.name for shape in host.shapes]
    assert "figure:recall-flowchart_image" in names
    assert "slot:recall-flowchart" not in names
    assert not any(name.startswith("card:recall-flowchart") for name in names)


def test_the_composed_flowchart_is_a_landscape_picture(spec: make_pptx.Scaffold) -> None:
    """The composed flowchart reads as two columns, so it is wider than it is tall."""
    frame = next(frame for frame in spec.frames if frame.id == "recall-flowchart")
    assert frame.figure is not None
    width_px, height_px = figure_layout.picture_size_inches(frame.figure.path)
    assert width_px / height_px > EXPECTED_LANDSCAPE_ASPECT


def test_the_compose_helper_cuts_a_tall_picture(tmp_path: Path) -> None:
    """The composition helper cuts a tall picture into two halves side by side."""
    source = tmp_path / "tall.png"
    picture = Image.new("RGB", (TALL_PICTURE_WIDTH_PX, TALL_PICTURE_HEIGHT_PX), "white")
    for offset in (200, 800):
        for row in range(offset, offset + 100):
            for column in range(50, 350):
                picture.putpixel((column, row), (0, 0, 128))
    picture.save(source)
    output = tmp_path / "wide.png"
    width_px, height_px = figure_layout.compose_halves_side_by_side(source, output)
    assert output.exists()
    assert width_px == TALL_PICTURE_WIDTH_PX * 2 + figure_layout.GUTTER_WIDTH_PX
    assert height_px <= TALL_PICTURE_HEIGHT_PX


def _timeline_slide(deck: NativeDeck) -> Slide:
    """Return the slide that carries the timeline of the overall progress.

    Args:
        deck: The native deck to look at.

    Returns:
        The slide that holds the milestone cards.

    Raises:
        AssertionError: When the deck carries no timeline at all.

    """
    for slide in deck.slides:
        for shape in slide.shapes:
            if _name_of(shape) == "slot:progress-overall":
                return slide
    failure_reason = "the deck carries no overall progress timeline"
    raise AssertionError(failure_reason)


def test_the_overall_progress_is_a_horizontal_timeline(
    built: Path,
    spec: make_pptx.Scaffold,
) -> None:
    """The overall progress frame carries five milestones on one row."""
    frame = next(item for item in spec.frames if item.id == "progress-overall")
    assert frame.timeline
    assert len(frame.body.splitlines()) == EXPECTED_MILESTONE_COUNT
    deck = NativePresentation(str(built))
    host = _timeline_slide(deck)
    names = [_name_of(shape) for shape in host.shapes]
    assert "timeline_axis" in names
    assert sum(1 for name in names if name.startswith("timeline_node_")) == EXPECTED_MILESTONE_COUNT
    assert len(_cards_of(host, "progress-overall")) == EXPECTED_MILESTONE_COUNT


def test_the_milestones_share_one_row(built: Path) -> None:
    """The milestone cards sit side by side and do not overlap."""
    deck = NativePresentation(str(built))
    cards = _cards_of(_timeline_slide(deck), "progress-overall")
    tops = {round(card.top) for card in cards}
    assert len(tops) == 1
    for first, second in pairwise(cards):
        assert first.left + first.width <= second.left


def test_update_does_not_duplicate_the_timeline_chrome(
    spec: make_pptx.Scaffold,
    tmp_path: Path,
    sky_path: Path,
) -> None:
    """Running the update leaves one axis and one disc per milestone.

    WHY: the axis and the discs are drawn apart from the milestone cards, so
    a refresh that draws them again without removing the old ones would leave
    two of each stacked at the same place on the slide.
    """
    output = tmp_path / "deck.pptx"
    _ = make_pptx.build_regenerate(spec, output, with_sections=True, sky_path=sky_path)
    for _attempt in range(2):
        _ = make_pptx.build_update(
            spec,
            output,
            force_bodies=False,
            force_titles=False,
            rebuild_sections=False,
            sky_path=sky_path,
        )
    deck = NativePresentation(str(output))
    host = _timeline_slide(deck)
    names = [_name_of(shape) for shape in host.shapes]
    assert names.count("timeline_axis") == 1
    assert sum(1 for name in names if name.startswith("timeline_node_")) == EXPECTED_MILESTONE_COUNT


def test_every_owner_block_of_the_outline_has_a_pill_of_its_own(
    built: Path,
    spec: make_pptx.Scaffold,
) -> None:
    """The outline lists the owner blocks, one glass pill each."""
    deck = NativePresentation(str(built))
    outline = None
    for slide in deck.slides:
        for shape in slide.shapes:
            if _name_of(shape) == "outline_title":
                outline = slide
    assert outline is not None
    labels = [
        cast("Shape", shape)
        for shape in outline.shapes
        if (_name_of(shape)).startswith("outline_pill_") and (_name_of(shape)).endswith("_label")
    ]
    assert len(labels) == EXPECTED_SECTION_COUNT
    joined = " ".join(shape.text_frame.text for shape in labels)
    for section in spec.sections:
        assert section in joined


def _slide_of(deck: NativeDeck, frame_id: str) -> Slide:
    """Return the slide that carries a frame, found by its machine key.

    Args:
        deck: The native deck to look at.
        frame_id: The identifier of the frame.

    Returns:
        The slide that holds the frame.

    Raises:
        AssertionError: When the deck carries no slide for the frame.

    """
    # WHY: a frame that gives its whole panel to a picture is named with the
    # figure prefix instead of the slot prefix, so both keys are looked up.
    keys = (f"slot:{frame_id}", f"figure:{frame_id}")
    for slide in deck.slides:
        for shape in slide.shapes:
            if _name_of(shape) in keys:
                return slide
    failure_reason = f"the deck carries no slide for '{frame_id}'"
    raise AssertionError(failure_reason)


def _points_of(frame: make_pptx.SlotFrame) -> list[str]:
    """Return the points of a frame body, one entry per line.

    Args:
        frame: The frame whose body is split.

    Returns:
        The points of the body, without the bullet markers.

    """
    return [
        line.strip().removeprefix("- ").removeprefix("* ").strip()
        for line in frame.body.splitlines()
        if len(line.strip()) != 0
    ]


def test_load_spec_rejects_a_non_boolean_pill_list_flag(tmp_path: Path) -> None:
    """The pill_list flag of a frame must be a boolean."""
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document["frames"][0]["pill_list"] = "yes"
    broken = tmp_path / "broken.json"
    _ = broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(scaffold_logic.ScaffoldError, match="pill_list"):
        _ = make_pptx.load_spec(broken)


def test_load_spec_rejects_a_non_boolean_cards_only_flag(tmp_path: Path) -> None:
    """The cards_only flag of a frame must be a boolean."""
    document = json.loads(SPEC.read_text(encoding="utf-8"))
    document["frames"][0]["cards_only"] = 3
    broken = tmp_path / "broken.json"
    _ = broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(scaffold_logic.ScaffoldError, match="cards_only"):
        _ = make_pptx.load_spec(broken)


def test_the_previous_issues_are_listed_as_pills(
    built: Path,
    spec: make_pptx.Scaffold,
) -> None:
    """The previous issues are listed as one glass pill per issue."""
    frame = next(item for item in spec.frames if item.id == "recall-previous-issues")
    assert frame.pill_list
    assert not frame.cards_only
    points = _points_of(frame)
    assert len(points) == EXPECTED_PREVIOUS_ISSUE_COUNT
    deck = NativePresentation(str(built))
    host = _slide_of(deck, "recall-previous-issues")
    pills = _cards_of(host, "recall-previous-issues")
    assert len(pills) == EXPECTED_PREVIOUS_ISSUE_COUNT
    joined = " ".join(pill.text_frame.text for pill in pills)
    for point in points:
        assert point in joined
    names = [_name_of(shape) for shape in host.shapes]
    discs = [name for name in names if name.startswith("pill_list_number_")]
    assert len(discs) == EXPECTED_PREVIOUS_ISSUE_COUNT


def test_the_pills_of_the_list_are_stacked_vertically(built: Path) -> None:
    """The pills stand on top of each other and none of them overlaps."""
    deck = NativePresentation(str(built))
    pills = _cards_of(_slide_of(deck, "recall-previous-issues"), "recall-previous-issues")
    tops = [pill.top for pill in pills]
    assert tops == sorted(tops)
    for first, second in pairwise(pills):
        assert first.top + first.height <= second.top


def test_every_previous_issue_has_a_slide_of_its_own(
    built: Path,
    spec: make_pptx.Scaffold,
) -> None:
    """Each issue of the list is elaborated on a slide of its own."""
    issue_frames = [
        frame for frame in spec.frames if frame.id.startswith("recall-previous-issue-")
    ]
    assert len(issue_frames) == EXPECTED_PREVIOUS_ISSUE_COUNT
    deck = NativePresentation(str(built))
    for frame in issue_frames:
        assert frame.cards_only
        assert not frame.pill_list
        points = _points_of(frame)
        host = _slide_of(deck, frame.id)
        cards = _cards_of(host, frame.id)
        assert len(cards) == len(points)
        joined = " ".join(card.text_frame.text for card in cards)
        for point in points:
            heading, _, detail = point.partition(":")
            assert heading.strip() in joined
            assert detail.strip() in joined


def test_the_methodology_is_elaborated_in_several_slides(
    spec: make_pptx.Scaffold, built: Path,
) -> None:
    """Every slide of the methodology detail block carries a figure of its own.

    WHY: a methodology slide that carries no picture states its physics
    without showing it, so every frame of the block must hold a graphic and
    must own a slide of its own.
    """
    frames = [frame for frame in spec.frames if frame.id.startswith("recall-methodology-")]
    assert len(frames) == EXPECTED_METHODOLOGY_FRAME_COUNT
    deck = NativePresentation(str(built))
    for frame in frames:
        assert frame.figure is not None
        points = _points_of(frame)
        assert len(points) >= EXPECTED_METHODOLOGY_MIN_POINTS
        slide = _slide_of(deck, frame.id)
        names = {shape.name for shape in slide.shapes}
        assert make_pptx.FIGURE_SHAPE_PREFIX + frame.id in names
        assert make_pptx.FIGURE_SHAPE_PREFIX + frame.id + "_image" in names
        assert len(_cards_of(slide, frame.id)) == len(points)


def test_the_text_of_a_card_stays_inside_its_glass_card(built: Path) -> None:
    """The narration of a card sits inside the glass card that carries it."""
    deck = NativePresentation(str(built))
    for frame_id in ("recall-previous-issue-2", "recall-previous-issue-3"):
        host = _slide_of(deck, frame_id)
        cards = _cards_of(host, frame_id)
        panels = [
            shape for shape in host.shapes if _name_of(shape).startswith("card_panel:")
        ]
        assert len(panels) == len(cards)
        for card, panel in zip(cards, panels, strict=True):
            assert card.left >= panel.left
            assert card.left + card.width <= panel.left + panel.width
            assert card.top >= panel.top
            assert card.top + card.height <= panel.top + panel.height


def test_the_cards_of_a_band_run_in_two_columns(built: Path) -> None:
    """The cards of a band run two to a row, so the band reads as a grid."""
    deck = NativePresentation(str(built))
    cards = _cards_of(_slide_of(deck, "recall-previous-issue-3"), "recall-previous-issue-3")
    assert len(cards) == EXPECTED_ISSUE_CARD_COUNT
    lefts = {card.left for card in cards}
    assert len(lefts) == EXPECTED_ISSUE_COLUMN_COUNT
    tops = {card.top for card in cards}
    assert len(tops) == EXPECTED_ISSUE_ROW_COUNT
