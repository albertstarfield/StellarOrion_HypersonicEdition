#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the detail slides the way the owner's screenshot shows them.

WHY: his screenshot has the picture on the left and the facts of the slide as
separate stacked glass cards on the right, one point per card, set large and
airy, with the provenance line under them. The deck drew one dense paragraph
column instead.

This script adds the figure layout "side_points" to the generator, points the
seven detail frames at it, and documents it. Every measurement is checked
before anything is written: if a single frame's points would not fit the
column at the smallest type size, the script stops and leaves every file as
it was.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

GENERATOR = PROJECT / "make_pptx.py"
SPEC = PROJECT / "scaffold.json"
README = PROJECT / "README.md"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
GENERATOR_BACKUP = BACKUP_DIR / "make_pptx_before_side_points.py"
SPEC_BACKUP = BACKUP_DIR / "scaffold_before_side_points.json"
README_BACKUP = BACKUP_DIR / "README_before_side_points.md"
EM_DASH = "\u2014"
#: The most points a detail slide may carry; his reference shows three.
MAX_POINTS = 4

FRAME_IDS = (
    "recall-methodology-optimization",
    "recall-methodology-setup",
    "recall-methodology-mesh",
    "recall-methodology-convergence",
    "recall-methodology-convection",
    "recall-methodology-conduction",
    "recall-methodology-radiation",
)

LAYOUT_CONSTANT = 'FIGURE_LAYOUT_FEATURE = "feature"'
LAYOUT_CONSTANT_NEW = """FIGURE_LAYOUT_FEATURE = "feature"
#: The layout of a graphic whose points stand beside it as separate cards.
#: WHY: a column of running prose beside a picture reads as fine print, so
#: the owner asked for the facts of the slide as stacked cards, one point
#: each, set large, with the provenance line under them.
FIGURE_LAYOUT_SIDE_POINTS = "side_points"
#: The width of the picture of a side-points frame, in inches.
SIDE_POINTS_PICTURE_WIDTH_IN = 7.70
#: The gutter between the picture and the column of cards, in inches.
SIDE_POINTS_GUTTER_IN = 0.20
#: The smallest column of cards, in inches; the picture gives way below it.
SIDE_POINTS_COLUMN_MIN_IN = 3.60
#: The gap between two stacked cards, in inches.
SIDE_POINTS_CARD_GAP_IN = 0.08
#: The padding inside a card of the column, in inches.
SIDE_POINTS_CARD_PADDING_IN = 0.16
#: The type size the column starts at, the floor it steps down to and the
#: step it takes: a card that does not fit is worse than a smaller point.
SIDE_POINTS_TEXT_START_PT = 13.0
SIDE_POINTS_TEXT_MIN_PT = 10.0
SIDE_POINTS_TEXT_STEP_PT = 0.5
#: The multiple of the point size that one line of a card occupies.
SIDE_POINTS_LINE_SPACING = 1.15
#: The type size of the caption that sits under the picture.
SIDE_POINTS_CAPTION_PT = 10.0
#: The share of the column a line of type is measured against. WHY: the
#: band cards use 0.78 because the preview draws their face wider, and a
#: column of cards beside a picture can be measured closer to the truth.
SIDE_POINTS_MEASURE_FACTOR = 0.90
"""

LOADER_SET_OLD = "    if layout not in {FIGURE_LAYOUT_SIDE, FIGURE_LAYOUT_FEATURE}:\n"
LOADER_SET_NEW = (
    "    if layout not in {FIGURE_LAYOUT_SIDE, FIGURE_LAYOUT_FEATURE, FIGURE_LAYOUT_SIDE_POINTS}:\n"
)
LOADER_MESSAGE_OLD = '            f"{FIGURE_LAYOUT_SIDE} and {FIGURE_LAYOUT_FEATURE}"\n'
LOADER_MESSAGE_NEW = (
    '            f"{FIGURE_LAYOUT_SIDE}, {FIGURE_LAYOUT_FEATURE} and '
    '{FIGURE_LAYOUT_SIDE_POINTS}"\n'
)

BRANCH_ANCHOR = """    inner_width = CONTENT_WIDTH_IN - 2.0 * FILLED_FIGURE_PADDING_IN
    if figure.layout == FIGURE_LAYOUT_FEATURE:
"""
BRANCH_NEW = """    inner_width = CONTENT_WIDTH_IN - 2.0 * FILLED_FIGURE_PADDING_IN
    if figure.layout == FIGURE_LAYOUT_SIDE_POINTS:
        _draw_side_points_panel(
            slide, frame, palette, area_left, area_top, area_height, inner_width,
        )
        return
    if figure.layout == FIGURE_LAYOUT_FEATURE:
"""

HELPER_ANCHOR = (
    "def _add_figure_panel(slide: Slide, frame: SlotFrame, "
    "palette: dict[str, str], panel_height_in: float) -> None:\n"
)
HELPER = '''def _side_points_plan(
    points: tuple[str, ...], family: str, column_width_in: float, available_in: float,
) -> tuple[float, tuple[float, ...]]:
    """Return the type size and the card heights that fit a column of points.

    WHY: the points of a detail slide are read one at a time beside the
    picture, so every point gets its own card and the whole stack has to fit
    the panel. The type starts large and steps down until it does, because a
    card that overflows is worse than a point set a little smaller.

    Args:
        points: The points of the frame, one card each.
        family: The face the cards are drawn in.
        column_width_in: The width of the column, in inches.
        available_in: The height the cards are allowed to take, in inches.

    Returns:
        The type size in points and the height of every card, in inches.

    Raises:
        ScaffoldError: When even the smallest type size does not fit.

    """
    text_width = column_width_in - 2.0 * SIDE_POINTS_CARD_PADDING_IN
    measured_width = text_width * SIDE_POINTS_MEASURE_FACTOR
    size = SIDE_POINTS_TEXT_START_PT
    while size >= SIDE_POINTS_TEXT_MIN_PT - 1e-9:
        lines = [wrap_line_count(point, family, size, measured_width) for point in points]
        heights = tuple(
            count * line_height_inches(family, size) * SIDE_POINTS_LINE_SPACING
            + 2.0 * SIDE_POINTS_CARD_PADDING_IN
            for count in lines
        )
        total = sum(heights) + SIDE_POINTS_CARD_GAP_IN * max(0, len(heights) - 1)
        if total <= available_in:
            return size, heights
        size -= SIDE_POINTS_TEXT_STEP_PT
    failure_reason = (
        f"a column of {len(points)} points needs more than the {available_in:.2f} inches "
        f"that are free at {SIDE_POINTS_TEXT_MIN_PT} pt"
    )
    raise ScaffoldError(failure_reason)


def _draw_side_points_panel(
    slide: Slide, frame: SlotFrame, palette: dict[str, str],
    area_left_in: float, area_top_in: float, area_height_in: float, inner_width_in: float,
) -> None:
    """Draw the picture, its caption, the stacked point cards and the source.

    WHY: the owner's reference slide puts the picture on the left and the
    facts of the slide on the right as separate cards, one point each, with
    the provenance line under them. The caption goes under the picture, where
    it belongs to the picture, so the column is left for the points.

    Args:
        slide: The slide the panel is drawn on.
        frame: The frame whose graphic and points are drawn.
        palette: The colour name to hexadecimal string map.
        area_left_in: The left edge of the content area of the panel.
        area_top_in: The top edge of the content area of the panel.
        area_height_in: The height of the content area of the panel.
        inner_width_in: The width of the content area of the panel.

    Raises:
        ScaffoldError: When the frame carries no graphic or no point, or when
            the points do not fit the column at the smallest type size.

    """
    figure = frame.figure
    if figure is None:
        failure_reason = f"frame '{frame.id}' has no graphic to draw"
        raise ScaffoldError(failure_reason)
    points = tuple(_narration_points(frame))
    if len(points) == 0:
        failure_reason = f"frame '{frame.id}' draws point cards but carries no point"
        raise ScaffoldError(failure_reason)

    picture_width = min(
        SIDE_POINTS_PICTURE_WIDTH_IN,
        inner_width_in - SIDE_POINTS_COLUMN_MIN_IN - SIDE_POINTS_GUTTER_IN,
    )
    column_left = area_left_in + picture_width + SIDE_POINTS_GUTTER_IN
    column_width = inner_width_in - picture_width - SIDE_POINTS_GUTTER_IN
    source_height = _source_box_height(figure.source, column_width)
    caption_lines = figure.caption.splitlines()
    if len(caption_lines) == 0:
        caption_lines = [figure.caption]
    caption_height = (
        len(caption_lines) * line_height_inches(BODY_FONT, SIDE_POINTS_CAPTION_PT)
        + FILLED_SOURCE_GAP_IN
    )
    picture_height = area_height_in - caption_height - FILLED_SOURCE_GAP_IN

    left, top, width, height = fit_picture_in_box(
        figure.path,
        (area_left_in, area_top_in, picture_width, picture_height),
        align="left",
    )
    picture = slide.pptx_slide.shapes.add_picture(
        str(figure.path),
        Emu(int(left * EMU_PER_INCH)),
        Emu(int(top * EMU_PER_INCH)),
        width=Emu(int(width * EMU_PER_INCH)),
        height=Emu(int(height * EMU_PER_INCH)),
    )
    picture.name = FIGURE_SHAPE_PREFIX + frame.id + "_image"

    caption = add_text_box(
        slide,
        area_left_in,
        area_top_in + picture_height + FILLED_SOURCE_GAP_IN,
        picture_width,
        caption_height,
        caption_lines,
        size=Pt(SIDE_POINTS_CAPTION_PT),
        color=css_colour(palette, SLOT_TEXT_COLOR),
        bold=False,
        italic=False,
    )
    caption.name = NAME_FIGURE_CAPTION

    source_top = area_top_in + area_height_in - source_height
    available = source_top - area_top_in - SIDE_POINTS_CARD_GAP_IN
    size_pt, heights = _side_points_plan(points, BODY_FONT, column_width, available)
    index = 0
    top_in = area_top_in
    for card_height in heights:
        card = slide.add_shape(
            "ROUNDED_RECTANGLE",
            x=in_(column_left),
            y=in_(top_in),
            width=in_(column_width),
            height=in_(card_height),
            fill_color=css_colour(palette, SLOT_BOX_COLOR),
        )
        card.name = f"{CARDS_ONLY_PANEL_PREFIX}{frame.id}#{index}"
        _set_corner_radius(card, GLASS_CORNER_RADIUS_IN)
        _glass_shape(
            card,
            fill=rgb(palette, SLOT_BOX_COLOR),
            fill_opacity=GLASS_FILL_OPACITY,
            edge=rgb(palette, FROST_EDGE_COLOR),
            edge_opacity=GLASS_EDGE_OPACITY,
            edge_width_pt=GLASS_EDGE_WIDTH_PT,
            shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
            shadow_opacity=GLASS_SHADOW_OPACITY,
        )
        text = add_text_box(
            slide,
            column_left + SIDE_POINTS_CARD_PADDING_IN,
            top_in,
            column_width - 2.0 * SIDE_POINTS_CARD_PADDING_IN,
            card_height,
            [""],
            size=Pt(size_pt),
            color=css_colour(palette, SLOT_TEXT_COLOR),
            bold=False,
            italic=False,
            align="left",
            vertical="middle",
            font_name=BODY_FONT,
        )
        text.name = (
            SLOT_SHAPE_PREFIX + frame.id
            if index == 0
            else f"{NARRATION_CARD_SHAPE_PREFIX}{frame.id}#{index}"
        )
        _write_milestone(
            text,
            points[index],
            size=Pt(size_pt),
            color=rgb(palette, SLOT_TEXT_COLOR),
            font_name=BODY_FONT,
        )
        index += 1
        top_in += card_height + SIDE_POINTS_CARD_GAP_IN

    source = add_text_box(
        slide,
        column_left,
        source_top,
        column_width,
        source_height,
        [figure.source],
        size=FILLED_SOURCE_SIZE,
        color=css_colour(palette, SLOT_TEXT_COLOR),
        bold=False,
        italic=False,
    )
    source.name = NAME_FIGURE_SOURCE


''' + HELPER_ANCHOR

FILLED_PLAN_ANCHOR = """    plan = _plan_narration_cards(frame, BODY_FONT, FILLED_BAND_COLUMNS)
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)
    _add_frame_header(slide, frame, palette)
    _add_figure_panel(slide, frame, palette, plan.figure_panel_height_in)
    _add_narration_column(slide, frame, palette, plan)
"""
FILLED_PLAN_NEW = """    # WHY: a frame whose points stand beside its picture has no band under
    # the panel, so the panel takes the whole content area and no narration
    # column is drawn below it.
    panel_height = FILLED_CARD_HEIGHT_IN
    plan: NarrationPlan | None = None
    if frame.figure.layout != FIGURE_LAYOUT_SIDE_POINTS:
        plan = _plan_narration_cards(frame, BODY_FONT, FILLED_BAND_COLUMNS)
        panel_height = plan.figure_panel_height_in
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)
    _add_frame_header(slide, frame, palette)
    _add_figure_panel(slide, frame, palette, panel_height)
    if plan is not None:
        _add_narration_column(slide, frame, palette, plan)
"""

REFRESH_ANCHOR = """    if frame.pill_list:
        for card in _collect_narration_shapes(slide, frame.id):
            element = card._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)
        _remove_pill_list_numbers(slide)
"""
REFRESH_NEW = """    if frame.figure is not None and frame.figure.layout == FIGURE_LAYOUT_SIDE_POINTS:
        # WHY: the points of this layout live inside the panel, so the old
        # cards, the old panels and the whole figure panel are removed before
        # the panel is drawn again with the current points.
        for card in _collect_narration_shapes(slide, frame.id):
            element = card._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)
        _remove_cards_only_panels(slide)
        _remove_figure_panel(slide, frame)
        _add_figure_panel(slide, frame, palette, FILLED_CARD_HEIGHT_IN)
        return
    if frame.pill_list:
        for card in _collect_narration_shapes(slide, frame.id):
            element = card._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)
        _remove_pill_list_numbers(slide)
"""

GENERATOR_RULES: list[tuple[str, str, int]] = [
    (LAYOUT_CONSTANT, LAYOUT_CONSTANT_NEW, 1),
    (LOADER_SET_OLD, LOADER_SET_NEW, 1),
    (LOADER_MESSAGE_OLD, LOADER_MESSAGE_NEW, 1),
    (BRANCH_ANCHOR, BRANCH_NEW, 1),
    (HELPER_ANCHOR, HELPER, 1),
    (FILLED_PLAN_ANCHOR, FILLED_PLAN_NEW, 1),
    (REFRESH_ANCHOR, REFRESH_NEW, 1),
]

BULLET_MARKER = "* The methodology is a block of eight slides, opened by the overview and"
NEW_BULLET = """* The methodology is a block of eight slides, opened by the overview and
  then the reasoning: `GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW` carries the
  eleven stage workflow of the thesis and is shown first because it is the
  overview of everything that follows, `METHODOLOGY AND REASONING` keeps the
  per-step definitions, and `METHODOLOGY: THE OPTIMIZATION FLOWCHART` carries
  the twelve stage validation pipeline of the engine with the geometry
  optimization loop drawn under it. The six slides that follow explain how
  the simulation is run, and each of them is drawn the way the owner's
  reference slide asks for: the picture on the left with its caption under
  it, and the facts of the slide as separate stacked glass cards on the
  right, one point each, set at thirteen point and stepping down only as far
  as the column needs, with the provenance line under the cards. Every card
  is named after its frame, so the whole column is found and replaced as one
  thing when the tool updates a slide.
"""


BODIES: dict[str, tuple[str, ...]] = {
    "recall-methodology-optimization": (
        "Twelve stage validation pipeline, with the geometry loop under it.",
        "Loop: design space, cost function, DSMC re-simulation, accept test.",
        "A rejection resamples the design space; an accepted geometry is kept.",
        "The stages run from flight parameters to the export of fields and plots.",
    ),
    "recall-methodology-setup": (
        "One uniform Cartesian grid: 139 by 139 cells at grid factor 0.7.",
        "The grid is finer than the local mean free path in the shock layer.",
        "Body of revolution with a toroidal stack; five design variables.",
        "Geometry and flight point feed SPARTA and the Ada/SPARK solver.",
    ),
    "recall-methodology-mesh": (
        "Three levels: 70, 100 and 139 grid points, 4,900 to 19,321 cells.",
        "Particles per level: 0.60, 0.85 and 1.19 million.",
        "Finest pair moves the peak flux by 8.30 percent, inside 10 percent.",
        "Skewness 0 and orthogonal quality 1 on the axis aligned grid.",
    ),
    "recall-methodology-convergence": (
        "Normalised residuals of drag, lift and heat flux against the step.",
        "They fall about three orders of magnitude over steps 100 to 2200.",
        "Particle retention 0.983 at step 400; stationarity near 0.005.",
        "The run closes on retention and indicator, not on a residual.",
    ),
    "recall-methodology-convection": (
        "q = C_SG sqrt(rho/R_N) V^3 with C_SG = 1.7415e-4 for Earth air.",
        "At 3378 m/s and a 1.5 m nose radius it gives 15.36 W/cm^2.",
        "The particle solver ranks geometries; it gives no absolute flux.",
        "At the candidate nose radius the screening flux is 25.36 W/cm^2.",
    ),
    "recall-methodology-conduction": (
        "Heat enters the hot face and conducts through the five-ply layup.",
        "Stack resistance 0.3056 m^2K/W over 3,648 surface elements.",
        "Back face stays at 300 K while the hot face reaches 1327.2 K.",
        "Lateral coupling carries 0.0083 W per square metre of the load.",
    ),
    "recall-methodology-radiation": (
        "The hot face radiates as a grey body, q = eps sigma T^4, eps 0.75.",
        "A convective load of 143,760 W/m^2 arrives at the surface.",
        "Reradiation takes 140,399 W/m^2, conduction only 3,362 W/m^2.",
        "So the surface temperature is set by the radiative balance.",
    ),
}


def check_frames() -> list[str]:
    """Return every reason the specification does not match what is expected.

    Returns:
        The problems found, empty when the specification is ready to patch.
    """
    document: dict[str, object] = json.loads(SPEC.read_text(encoding="utf-8"))
    raw_frames = document.get("frames")
    if not isinstance(raw_frames, list):
        return ["the specification holds no frame list"]
    frames: list[dict[str, object]] = [item for item in raw_frames if isinstance(item, dict)]
    problems: list[str] = []
    for frame_id in FRAME_IDS:
        frame = next((item for item in frames if str(item.get("id")) == frame_id), None)
        if frame is None:
            problems.append(f"the specification does not hold the frame '{frame_id}'")
            continue
        figure = frame.get("figure")
        if not isinstance(figure, dict):
            problems.append(f"the frame '{frame_id}' carries no figure")
            continue
        if figure.get("layout") == "side_points":
            problems.append(f"the frame '{frame_id}' already uses the new layout")
        if len(BODIES.get(frame_id, ())) > MAX_POINTS:
            problems.append(f"the new body of '{frame_id}' carries more than four points")
    return problems


def check_measurements() -> list[str]:
    """Return every frame whose points would not fit the new column.

    The numbers of the new layout are repeated here because the script
    measures before it patches, so the generator does not carry them yet.

    Returns:
        The problems found, empty when every frame fits.
    """
    import make_pptx as maker  # ruff: ignore[import-outside-top-level]

    spec = maker.load_spec(SPEC)
    picture_width = 7.70
    gutter = 0.20
    column_min = 3.60
    gap = 0.08
    padding = 0.16
    spacing = 1.15
    inner_width = maker.CONTENT_WIDTH_IN - 2.0 * maker.FILLED_FIGURE_PADDING_IN
    if inner_width - picture_width - gutter < column_min:
        picture_width = inner_width - column_min - gutter
    column_width = inner_width - picture_width - gutter
    problems: list[str] = []
    for frame in spec.frames:
        if frame.id not in FRAME_IDS:
            continue
        figure = frame.figure
        if figure is None:
            problems.append(f"the frame {frame.id} carries no figure")
            continue
        # WHY: the new bodies are measured before they are written, so the
        # guard proves the layout fits what the deck is about to say.
        fallback = maker._narration_points(frame)  # ruff: ignore[private-member-access]
        points = BODIES.get(frame.id, tuple(fallback))
        area_height = maker.FILLED_CARD_HEIGHT_IN - 2.0 * maker.FILLED_FIGURE_PADDING_IN
        source_height = maker._source_box_height(  # ruff: ignore[private-member-access]
            figure.source, column_width,
        )
        available = area_height - source_height - gap
        text_width = column_width - 2.0 * padding
        measured_width = text_width * 0.90
        size = 13.0
        chosen: tuple[float, tuple[float, ...]] | None = None
        while size >= 10.0 - 1e-9:
            line_counts = [
                maker.wrap_line_count(point, maker.BODY_FONT, size, measured_width)
                for point in points
            ]
            heights = tuple(
                count * maker.line_height_inches(maker.BODY_FONT, size) * spacing + 2.0 * padding
                for count in line_counts
            )
            total = sum(heights) + gap * max(0, len(heights) - 1)
            if total <= available:
                chosen = (size, heights)
                break
            size -= 0.5
        if chosen is None:
            problems.append(
                f"the frame {frame.id} needs more room than {available:.2f} inches "
                f"at 10 pt with {len(points)} points",
            )
            continue
        size_pt, heights = chosen
        total = sum(heights) + gap * max(0, len(heights) - 1)
        _ = sys.stdout.write(
            f"  {frame.id}: {len(points)} cards at {size_pt} pt, column {column_width:.2f} in, "
            f"{total:.2f} in of {available:.2f} in free\n",
        )
    return problems


def main() -> int:
    """Add the side-points layout and point the seven detail frames at it.

    Returns:
        Zero when every file was written, one when a guard refused.

    """
    problems = check_frames()
    generator_text = GENERATOR.read_text(encoding="utf-8")
    for old, _new, expected in GENERATOR_RULES:
        found = generator_text.count(old)
        if found != expected:
            problems.append(
                f"make_pptx.py: expected {expected} occurrence(s), "
                f"found {found}: {old[:60]!r}",
            )
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1
    problems = check_measurements()
    if len(problems) != 0:
        for problem in problems:
            _ = sys.stdout.write(f"MISMATCH {problem}\n")
        return 1

    document = json.loads(SPEC.read_text(encoding="utf-8"))
    for frame in document["frames"]:
        if not isinstance(frame, dict) or str(frame.get("id")) not in FRAME_IDS:
            continue
        frame_id = str(frame.get("id"))
        figure_block = frame.get("figure")
        if isinstance(figure_block, dict):
            figure_block["layout"] = "side_points"
        frame["body"] = "- " + "\n- ".join(BODIES[frame_id])
    spec_text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"

    for old, new, _expected in GENERATOR_RULES:
        generator_text = generator_text.replace(old, new, 1)
    try:
        _ = ast.parse(generator_text)
    except SyntaxError as error:
        _ = sys.stdout.write(f"MISMATCH the generator would not parse: {error}\n")
        return 1

    readme_text = README.read_text(encoding="utf-8")
    lines = readme_text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith(BULLET_MARKER)), -1)
    if start < 0:
        _ = sys.stdout.write("MISMATCH README.md has no methodology bullet\n")
        return 1
    end = start + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    readme_text = "\n".join(lines[:start] + NEW_BULLET.rstrip("\n").split("\n") + lines[end:])

    for name, text in (
        ("the generator", generator_text),
        ("the specification", spec_text),
        ("README.md", readme_text),
    ):
        if EM_DASH in text:
            _ = sys.stdout.write(f"MISMATCH {name} would carry an em dash\n")
            return 1

    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _ = GENERATOR_BACKUP.write_bytes(GENERATOR.read_bytes())
    _ = SPEC_BACKUP.write_bytes(SPEC.read_bytes())
    _ = README_BACKUP.write_bytes(README.read_bytes())
    _ = GENERATOR.write_text(generator_text, encoding="utf-8")
    _ = SPEC.write_text(spec_text, encoding="utf-8")
    _ = README.write_text(readme_text, encoding="utf-8")
    _ = sys.stdout.write("the seven detail slides now draw their points beside the picture\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
