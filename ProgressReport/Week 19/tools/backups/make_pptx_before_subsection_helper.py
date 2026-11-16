#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Build and update the Week 17 narrative scaffold as a Microsoft PowerPoint deck.

WHY THIS EXISTS
---------------
The owner asked for a PowerPoint (.pptx) version of the Week 17 narration
placeholder scaffold. The scaffold itself is defined once, in ``scaffold.json``,
so that the deck can be regenerated after every narration edit, and so that a
hand-edited deck can be brought back in line without losing the owner's work.

THEORIES
--------
1. The specification is the single source of truth. Every slide the tool emits
   is derived from ``scaffold.json``; no slide content is hard-coded here.
2. Shape names are stable machine keys. The slot box on a placeholder slide is
   named ``slot:<frame id>``. Matching by name survives a retitle, a re-order
   and a re-save by PowerPoint, which a text match cannot promise.
3. Provenance decides ownership. The text that was on the slide when the tool
   last ran is recorded in the speaker notes between the ``<<<SLOT_BODY ...>>>``
   markers. If the visible text still equals that record, nobody has edited it
   and the tool may refresh it. If the visible text differs, the owner wrote it
   and the tool keeps it.
4. Failure must be loud. A missing key, a malformed package, an unparsable
   specification or an uncovered slide raises :class:`ScaffoldError` with the
   offending value in the message. Nothing is silently skipped and no empty
   text is ever emitted.
5. A failed run must not destroy the owner's deck. Output is written to a
   temporary file in the destination directory, verified there, and only then
   moved onto the target with :func:`os.replace`.

APPLICATIONS
------------
* ``python make_pptx.py`` regenerates ``narrative_scaffold.pptx`` from
  ``scaffold.json``.
* ``python make_pptx.py --mode update`` updates a deck the owner has edited in
  PowerPoint: untouched placeholders are refreshed, owner-written text and
  owner-added slides are kept, and frames that are missing are created and
  placed in their scaffold position.

CITATIONS
---------
* EasyPPTX 0.11.0 -- https://Ameyanagi.github.io/EasyPPTX/ (the writer)
* python-pptx 1.0.2 -- https://python-pptx.readthedocs.io/ (reached through EasyPPTX)
* ECMA-376 Part 1, Office Open XML File Formats -- https://ecma-international.org/publications-and-standards/standards/ecma-376/
* Microsoft PowerPoint 16.114 (the consumer of the generated file)
* p14 section extension schema -- http://schemas.microsoft.com/office/powerpoint/2010/main
"""

from __future__ import annotations

import argparse
import json
import operator
import random
import sys
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

    from easypptx import Slide
    from lxml.etree import _Element
    from pptx.dml.color import RGBColor
    from pptx.shapes.autoshape import Shape
    from pptx.text.text import _Paragraph, _Run
    from pptx.util import Length

from easypptx import Presentation, in_
from lxml import etree
from PIL import ImageFont
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Pt

from figure_layout import fit_picture_in_box, picture_size_inches
from font_choice import font_file_for, font_is_installed, resolve_font
from scaffold_logic import (
    ScaffoldError,
    collapse_whitespace,
    escape_xml,
    is_hex_colour,
    require_mapping,
    require_text,
)
from sky_background import ensure_sky_image, relative_luminance, sky_colour_at
from text_layout import line_height_inches, wrap_line_count

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Width of a 16:9 slide in English Metric Units (1 inch == 914400 EMU).
SLIDE_WIDTH_EMU = 12192000
#: Height of a 16:9 slide in English Metric Units.
SLIDE_HEIGHT_EMU = 6858000

#: Horizontal margin of every text element, in inches.
MARGIN_X_IN = 0.55
#: Width of the slide in inches (16:9).
SLIDE_WIDTH_IN = 13.3333333
#: Height of the slide in inches (16:9).
SLIDE_HEIGHT_IN = 7.5
#: Width of the content column, in inches.
CONTENT_WIDTH_IN = SLIDE_WIDTH_IN - 2.0 * MARGIN_X_IN
#: Height of the coloured band that carries the frame title, in inches.
TITLE_BAND_HEIGHT_IN = 0.95
#: Height of the accent rule drawn under the title band, in inches (one point).
ACCENT_RULE_HEIGHT_IN = 1.0 / 72.0
#: Top edge of the narration card, in inches.
SLOT_BOX_TOP_IN = 1.95
#: Height of the narration card, in inches.
SLOT_BOX_HEIGHT_IN = 3.35
#: Inner padding of a glass card, in inches.
SLOT_BOX_PADDING_IN = 0.34
#: Top edge of the right-aligned section tag, in inches.
SECTION_TAG_TOP_IN = 1.12
#: Top edge of the footer line, in inches.
FOOTER_TOP_IN = 6.95

#: Type size of a frame title.
# WHY 24 POINTS: measured against the real Abadi Bold font file, the longest
# title in the deck ("PLACEHOLDER 3: METHODOLOGY AND REASONING", 40
# characters) is 8.47 in wide at 26 pt and 7.82 in at 24 pt. The title box
# is 9.55 in wide, so 24 pt leaves 22 percent of slack. That slack is what
# keeps the title on ONE line when a renderer substitutes a wider face for
# Abadi, which the macOS preview does because it cannot see the Office cloud
# font cache where Abadi lives.
FRAME_TITLE_SIZE = Pt(24)
#: The type size of the methodology sub-title drawn under the frame title.
FRAME_SUBTITLE_SIZE = Pt(11)
#: The height of the band the sub-title takes out of the title band.
FRAME_SUBTITLE_BAND_IN = 0.24
#: Type size of the text inside the slot box.
SLOT_TEXT_SIZE = Pt(20)
#: Type size of the right-aligned section tag.
SECTION_TAG_SIZE = Pt(12)
#: Type size of the footer line.
FOOTER_TEXT_SIZE = Pt(11)
#: The faces the owner asked for, most faithful first.
# WHY A RESOLVER AND NOT A LITERAL: a .pptx stores a font NAME, never the
# glyphs, so a name this machine cannot resolve is replaced silently by
# the renderer. The family "Abadi MT" is NOT installed here: Microsoft
# Office ships the two condensed Abadi MT faces, and the Office cloud font
# cache holds the family "Abadi" with its Regular, Bold, Italic and Bold
# Italic styles. The generator therefore resolves both faces against the
# fonts this machine really has and prints what it resolved, so a
# substitution is visible in the build log instead of being invisible on
# the slide.
TITLE_FONT_PREFERENCE = ("Abadi", "Abadi MT Condensed Extra Bold", "Abadi MT Condensed Light")
BODY_FONT_PREFERENCE = ("Abadi MT", "Abadi MT Condensed Light", "Abadi")
TITLE_FONT_FALLBACKS = ("Abadi", "Helvetica")
BODY_FONT_FALLBACKS = ("Abadi", "Helvetica")

#: The display face used for the four title blocks.
TITLE_FONT = resolve_font(TITLE_FONT_PREFERENCE, TITLE_FONT_FALLBACKS)
#: The text face used for every other run.
BODY_FONT = resolve_font(BODY_FONT_PREFERENCE, BODY_FONT_FALLBACKS)

#: Palette slot of the milky fill of every glass panel.
SLOT_BOX_COLOR = "Frost"
#: Palette slot of the narration text inside the glass panel.
SLOT_TEXT_COLOR = "Navy"
#: Palette slot of the frame title text.
TITLE_TEXT_COLOR = "Navy"
#: Palette slot of the title band fill.
TITLE_BAND_COLOR = "Frost"
#: Palette slot of the gold accent pill.
ACCENT_COLOR = "Gold"
#: Palette slot of ordinary body text.
BODY_TEXT_COLOR = "Navy"
#: Palette slot of the footer text, which sits in the night blue.
FOOTER_TEXT_COLOR = "Frost"
#: Palette slot of the subtitle and of the owner block badge.
SUBTITLE_TEXT_COLOR = "Navy"
#: Top of the frosted pill that holds the cover subtitle, in inches.
SUBTITLE_PILL_TOP_IN = 1.95
#: Height of the frosted pill that holds the cover subtitle, in inches.
SUBTITLE_PILL_HEIGHT_IN = 0.52
#: Horizontal padding inside the cover subtitle pill, in inches.
SUBTITLE_PILL_PADDING_IN = 0.26
#: The size of the cover subtitle, in points.
SUBTITLE_SIZE_PT = 24.0
#: Extra width of the cover subtitle pill, as a fraction of the measured
#: text width, so that a renderer which substitutes a wider face still
#: finds the text inside the pill. MEASURED: the face the macOS preview
#: substitutes is about 27 percent wider than Abadi MT Condensed Light,
#: so the headroom is set above that ratio.
SUBTITLE_WIDTH_HEADROOM = 1.40
#: Width used for the cover subtitle pill when the face cannot be measured.
SUBTITLE_FALLBACK_WIDTH_IN = 3.0
#: Pixels per point used when a line of text is measured.
MEASUREMENT_PIXELS_PER_POINT = 4
#: The number of points in one inch.
POINTS_PER_INCH = 72
#: Palette slot of the hairline border of a glass panel.
FROST_EDGE_COLOR = "Sky"
#: Palette slot of the night blue at the foot of the slide.
NAVY_DEEP_COLOR = "Navy"
#: Palette slot of the warm end of the sparkle variation.
SPARK_GOLD_COLOR = "Gold"
#: Palette slot of the cool white end of the sparkle variation.
SPARK_CREAM_COLOR = "Frost"
#: Palette slot of the sparkle used on the light part of the sky.
SPARK_DARK_COLOR = "Navy"
#: The brightness above which a sparkle is drawn in the dark colour.
SPARKLE_LIGHT_BACKGROUND_LUMINANCE = 0.55

#: Gradient stops of the sky, as palette slots with their position in the slide.
SKY_GRADIENT = (
    ("Frost", 0.00),
    ("Sky", 0.44),
    ("Navy", 1.00),
)
#: How opaque the milky fill of a glass card stays.
GLASS_FILL_OPACITY = 0.86
#: How opaque the fill of the floating title band stays.
GLASS_BAND_OPACITY = 0.62
#: How opaque the fill of the owner block badge stays.
GLASS_CHIP_OPACITY = 0.16
#: How opaque the hairline border of a glass card stays.
GLASS_EDGE_OPACITY = 0.35
#: The width of the hairline border of a glass card, in points.
GLASS_EDGE_WIDTH_PT = 1.0
#: How opaque the soft shadow under a floating element stays.
GLASS_SHADOW_OPACITY = 0.20
#: The blur radius of the soft shadow under a floating element, in points.
SHADOW_BLUR_PT = 18.0
#: How far the soft shadow is cast, in points.
SHADOW_DISTANCE_PT = 4.0
#: The direction the soft shadow is cast, in degrees clockwise from the horizontal.
SHADOW_DIRECTION_DEGREES = 90
#: The corner radius every glass card shares, in inches.
GLASS_CORNER_RADIUS_IN = 0.18
#: The inner padding of a glass card, in inches.
GLASS_CARD_PADDING_IN = 0.34
#: The top edge of the floating glass title band, in inches.
HEADER_CARD_TOP_IN = 0.34
#: The height of the floating glass title band, in inches.
HEADER_CARD_HEIGHT_IN = 0.92
#: The top edge of the gold accent pill, in inches.
GOLD_PILL_TOP_IN = 1.40
#: The width of the gold accent pill, in inches.
GOLD_PILL_WIDTH_IN = 1.10
#: The height of the gold accent pill, in inches.
GOLD_PILL_HEIGHT_IN = 0.055
#: The width of the owner block badge, in inches.
# WHY 2.00 INCHES: the badge sits at the right of the title band, and the
# title box is what is left of the band once the badge is taken out. A
# narrower badge gives the title more room to breathe on one line.
# "CURRENT PROGRESS", the longest badge label, needs about 1.25 in at 12 pt
# bold, so 2.00 in still holds it with a comfortable margin.
SECTION_CHIP_WIDTH_IN = 2.00
#: The height of the owner block badge, in inches.
SECTION_CHIP_HEIGHT_IN = 0.32
#: The top edge of the owner block badge, in inches.
SECTION_CHIP_TOP_IN = 0.64
#: The top edge of the frosted glass card on the cover slide, in inches.
COVER_TITLE_PLATE_TOP_IN = 0.66
COVER_TITLE_PLATE_HEIGHT_IN = 1.05
COVER_CARD_TOP_IN = 4.20
#: The height of the frosted glass card on the cover slide, in inches.
COVER_CARD_HEIGHT_IN = 2.15
#: The type size of the paper title on the cover slide.
#: WHY: the owner said the title was too small to read, so it is set larger
#: than the line above it and centred in the card.
COVER_JUDUL_SIZE = Pt(20)
#: The type size of the student number and supervisor line on the cover.
COVER_SUPERVISOR_SIZE = Pt(13)
#: The top edge of the first outline pill, in inches.
OUTLINE_PILL_TOP_IN = 1.95
#: The height of one outline pill, in inches.
OUTLINE_PILL_HEIGHT_IN = 0.70
#: The gap between two outline pills, in inches.
OUTLINE_PILL_GAP_IN = 0.22
#: The padding inside an outline pill, in inches.
OUTLINE_PILL_PADDING_IN = 0.42
#: The type size of the text of one outline pill.
OUTLINE_PILL_SIZE = Pt(22)
PILL_LIST_TOP_IN = 2.05
PILL_LIST_BOTTOM_IN = 6.60
PILL_LIST_GAP_IN = 0.34
PILL_LIST_PADDING_IN = 0.30
PILL_LIST_SIZE = Pt(19)
PILL_LIST_MIN_SIZE_PT = 12.0
PILL_LIST_SIZE_STEP_PT = 0.5
PILL_LIST_NUMBER_SIZE_IN = 0.46
PILL_LIST_NUMBER_GAP_IN = 0.30
PILL_LIST_NUMBER_SIZE_PT = Pt(14)
PILL_LIST_FOOTER_TEXT = (
    "Each of the four issues is elaborated on the slide that follows. "
    "The narration stays editable in PowerPoint."
)
CARDS_ONLY_COLUMNS = 2
CARDS_ONLY_CARD_PADDING_IN = 0.18
# WHY: the quick look renderer draws the body face wider than the font file
# measures it, and it wraps at the shape width while ignoring the right inset
# of the text frame. The band of cards is therefore measured against a
# narrower box than the text really has, so that the drawn line keeps a
# visible margin inside its card in the renderer and in PowerPoint.
CARDS_ONLY_MEASURE_WIDTH_FACTOR = 0.78
#: The room the text box of a card leaves on the right, in inches.
#: WHY: the renderer wraps at the right edge of the shape it draws in, so the
#: text box is narrower than the card and the text keeps a margin.
CARDS_ONLY_TEXT_GAP_IN = 0.24
#: The name prefix of the glass card of a band of cards.
CARDS_ONLY_PANEL_PREFIX = "card_panel:"
CARDS_ONLY_SIZE = Pt(16)
CARDS_ONLY_MIN_SIZE_PT = 11.0
CARDS_ONLY_SIZE_STEP_PT = 0.5
CARDS_ONLY_FOOTER_TEXT = "The narration stays editable in PowerPoint."
#: The base size of a sparkle, in inches.
SPARKLE_BASE_SIZE_IN = 0.085
#: How many placements are tried for every sparkle that is placed.
SPARKLE_ATTEMPT_FACTOR = 12
#: The seed of the sparkle field on the cover slide.
SPARKLE_SEED_COVER = 1701
#: The seed of the sparkle field on the outline slide.
SPARKLE_SEED_OUTLINE = 1702
#: The seed of the sparkle field on the placeholder slides.
SPARKLE_SEED_PLACEHOLDER = 1700
#: How opaque the glow around a sparkle stays.
SPARKLE_GLOW_OPACITY = 0.45
#: The blur radius of the glow around a sparkle, in points.
SPARKLE_GLOW_BLUR_PT = 7.0
#: The number of colour swatches in the palette reference.
PALETTE_SWATCH_COUNT = 4
#: The size of one colour swatch, in inches.
PALETTE_SWATCH_SIZE_IN = 0.115
#: The gap between two colour swatches, in inches.
PALETTE_SWATCH_GAP_IN = 0.030
#: How far the palette reference sits below the top of the footer band, in
#: inches. WHY: the circles are centred on the footer text line, and an
#: eleven point line is about 0.15 inches tall, so a circle of 0.115 inches
#: sits a twentieth of an inch below the top of the band.
PALETTE_SWATCH_FOOTER_OFFSET_IN = 0.02
#: The corner radius of one colour swatch, in inches.
# WHY NO RADIUS: the swatches are circles, so they carry no corner
# adjustment of their own.
#: How opaque the fill of a colour swatch stays.
PALETTE_SWATCH_OPACITY = 0.05
#: The width of the hairline of a colour swatch, in points.
PALETTE_SWATCH_EDGE_PT = 0.75
#: How opaque the hairline of a colour swatch stays.
PALETTE_SWATCH_EDGE_OPACITY = 0.35
#: The lowest opacity a fill may have.
MIN_OPACITY = 0.0
#: The highest opacity a fill may have.
MAX_OPACITY = 1.0
#: The scale of an opacity or of a gradient position, in hundred thousandths.
PERCENT_SCALE = 100000
#: The scale of an angle, in sixty thousandths of a degree.
ANGLE_UNITS_PER_DEGREE = 60000
#: The number of English Metric Units in one inch.
EMU_PER_INCH = 914400
#: The number of English Metric Units in one point.
EMU_PER_POINT = 12700
#: The mask of one colour channel.
CHANNEL_MASK = 0xFF
#: The largest corner adjustment a rounded rectangle accepts.
MAX_CORNER_ADJUSTMENT = 0.5

#: The URI of the p14 extension that carries the PowerPoint section list.
SECTION_EXTENSION_URI = "{521415D9-36F7-43E2-AB2F-B90AF26B5E84}"
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

#: Prefix of the machine key carried by the name of every slot box.
SLOT_SHAPE_PREFIX = "slot:"
#: Marker that opens the provenance record inside the speaker notes.
SLOT_BODY_MARKER_START = "<<<SLOT_BODY id={id}>>>"
#: Marker that closes the provenance record inside the speaker notes.
SLOT_BODY_MARKER_END = "<<<END_SLOT_BODY>>>"
#: Phrase used by the first generation of this tool to record the body.
LEGACY_BODY_PREFIX = "It must eventually carry: "
#: Phrase used by the first generation of this tool to close the body record.
LEGACY_BODY_SUFFIX = "Owner block:"

#: Name of the title band rectangle.
NAME_TITLE_BAND = "title_band"
#: Name of the accent rule.
NAME_ACCENT_RULE = "accent_rule"
#: Name of the frame title text box.
NAME_FRAME_TITLE = "frame_title"
NAME_FRAME_SUBTITLE = "subtitle"
#: Name of the right-aligned section tag.
NAME_SECTION_TAG = "section_tag"
#: Name of the footer line.
NAME_SLOT_FOOTER = "slot_footer"
#: Name of the cover title text box.
NAME_COVER_TITLE = "cover_title"
NAME_COVER_TITLE_PLATE = "cover_title_plate"
#: Name of the cover subtitle text box.
NAME_COVER_SUBTITLE = "cover_subtitle"
#: Name of the frosted pill that holds the cover subtitle.
NAME_COVER_SUBTITLE_PILL = "cover_subtitle_pill"
#: Name of the cover author block.
NAME_COVER_AUTHOR = "cover_author_block"
#: Name of the cover paper title.
NAME_COVER_JUDUL = "cover_judul"
#: Name of the cover supervisor line.
NAME_COVER_SUPERVISORS = "cover_supervisor_line"
#: Name of the outline title.
NAME_OUTLINE_TITLE = "outline_title"
#: Name prefix of the outline pills and their labels.
NAME_OUTLINE_PILL = "outline_pill_"
#: Name of the frosted glass card on the cover slide.
NAME_COVER_CARD = "cover_card"
#: Name of the pill badge that names the owner block.
NAME_SECTION_CHIP = "section_chip"
#: Name of the gold accent pill.
NAME_GOLD_PILL = "gold_pill"
#: The shape name of the sky picture that sits behind every slide.
NAME_SKY_BACKGROUND = "sky_background"

#: Text printed under every placeholder slide.
FOOTER_TEXT = "PLACEHOLDER SLIDE. Narration pending."

#: The layout of a frame that carries a graphic. A filled frame is a
#: figure panel at the top of the content area and a horizontal band of
#: narration cards under it.
# WHY: the owner asked for the narration cards to run horizontally, so
#: the figure takes the full width of the content area and the cards sit
#: in a band under it, three to a row.
FILLED_CARD_TOP_IN = 1.95
FILLED_CARD_HEIGHT_IN = 4.90
FILLED_FIGURE_PADDING_IN = 0.22
#: The height of the caption box of the figure panel.
#: WHY: the caption sits in a column beside the picture, so the box has
#: to hold the longest caption of the deck without touching the
#: provenance line under it.
FILLED_CAPTION_HEIGHT_IN = 0.92
FILLED_SOURCE_HEIGHT_IN = 0.30
#: The gap between the caption column and its provenance line, in inches.
FILLED_SOURCE_GAP_IN = 0.06
FILLED_CAPTION_SIZE = Pt(11)
FILLED_SOURCE_SIZE = Pt(9)
FILLED_NARRATION_SIZE = Pt(14)
FILLED_NARRATION_LINE_SPACING = 1.15
FILLED_BULLET_INDENT_IN = 0.20
#: Padding inside a narration card, in inches.
FILLED_CARD_PADDING_IN = 0.12
#: The gap between two narration cards, in inches.
FILLED_CARD_GAP_IN = 0.10
#: The fraction of the real text width that the card layout is measured
#: against.
# WHY: the card heights are measured with the font file the deck names, but a
#: renderer that cannot see that file substitutes a face that is about a
#: fifth wider, so the same text then needs another line. Measuring against a
#: narrower box makes every card tall enough for the substituted face too,
#: which is what stops the text from spilling out of its own card.
FILLED_MEASURE_WIDTH_FACTOR = 0.82
#: The smallest type size a narration card may be drawn at, in points.
FILLED_NARRATION_MIN_SIZE_PT = 10.0
#: The step the narration type size drops by when the cards do not fit.
FILLED_NARRATION_SIZE_STEP_PT = 0.5
#: The name prefix of the narration cards after the first one.
NARRATION_CARD_SHAPE_PREFIX = "card:"
#: How many narration cards sit in one row of the horizontal band.
FILLED_BAND_COLUMNS = 3
#: The tallest band of narration cards the content area leaves room for.
FILLED_BAND_MAX_IN = 2.55
#: The gap between the figure panel and the band of narration cards.
FILLED_FIGURE_GAP_IN = 0.16
#: The width of the area of the figure panel that carries the picture.
FILLED_FIGURE_AREA_WIDTH_IN = 5.90
#: The gap between the picture and the caption column of the figure panel.
FILLED_FIGURE_COLUMN_GAP_IN = 0.35
#: The width of the notes column of a frame whose figure owns the content
#: area. WHY: the column must be wide enough for the notes of the frame to
#: fit above the provenance line, so the picture of a wide figure gives up
#: the room it needs.
FEATURE_NOTES_COLUMN_IN = 3.20
#: The width of the column of the figure panel that carries the caption.
FILLED_CAPTION_COLUMN_WIDTH_IN = (
    CONTENT_WIDTH_IN
    - 2.0 * FILLED_FIGURE_PADDING_IN
    - FILLED_FIGURE_AREA_WIDTH_IN
    - FILLED_FIGURE_COLUMN_GAP_IN
)
BULLET_GLYPH = "\u2022"
FILLED_FOOTER_TEXT = "Content imported from the thesis. The narration stays editable in PowerPoint."

#: The number of milestones a horizontal timeline carries. The owner asked
#: for five points on the overall progress block.
TIMELINE_COLUMNS = 5
#: The gap between two milestone cards of a timeline.
TIMELINE_CARD_GAP_IN = 0.16
#: The padding inside a milestone card.
TIMELINE_CARD_PADDING_IN = 0.16
#: The diameter of the node that marks a milestone on the axis.
TIMELINE_NODE_SIZE_IN = 0.46
#: The top of the axis the milestone nodes sit on.
TIMELINE_AXIS_TOP_IN = 2.15
#: The height of the axis rule.
TIMELINE_AXIS_HEIGHT_IN = 0.035
#: The top of the milestone cards, below the axis.
TIMELINE_CARD_TOP_IN = 2.85
#: The type size a milestone card starts at.
TIMELINE_SIZE = Pt(15)
#: The smallest type size a milestone card may be drawn at.
TIMELINE_MIN_SIZE_PT = 10.0
#: The step the milestone type size drops by when the cards do not fit.
TIMELINE_SIZE_STEP_PT = 0.5
#: The height of a milestone card, in inches. The cards reach the bottom of
#: the content area, so the row of glass reads as one band of panels.
TIMELINE_CARD_HEIGHT_IN = 3.60
#: The line spacing of the milestone text.
TIMELINE_LINE_SPACING = 1.15
#: The type size of the number inside a milestone node.
TIMELINE_NODE_SIZE_PT = Pt(13)
#: The footer of a timeline slide.
TIMELINE_FOOTER_TEXT = (
    "Progress summary from the thesis and the Week 17 report. "
    "The milestones stay editable in PowerPoint."
)
#: The name of the axis rule of a timeline.
NAME_TIMELINE_AXIS = "timeline_axis"
#: The name prefix of a milestone node.
NAME_TIMELINE_NODE = "timeline_node_"
NAME_PILL_LIST_NUMBER = "pill_list_number_"
#: The character that separates the label of a milestone from its detail.
MILESTONE_SEPARATOR = ":"
FIGURE_SHAPE_PREFIX = "figure:"
#: The layout of a graphic that shares its panel with a column of
#: narration under it.
FIGURE_LAYOUT_SIDE = "side"
#: The layout of a graphic that takes the whole panel, for a frame
#: that carries no narration and whose graphic is the content of the
#: slide.
FIGURE_LAYOUT_FEATURE = "feature"
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

#: The narrowest column that still carries a caption of a full width
#: graphic. The picture takes the rest of the panel, because the
#: picture is what the frame is about.
FIGURE_CAPTION_MIN_WIDTH_IN = 2.40
NAME_FIGURE_CAPTION = "figure_caption"
NAME_FIGURE_SOURCE = "figure_source"
FIGURE_MARKER_START = "<<<FIGURE id={id}>>>"
FIGURE_MARKER_END = "<<<END_FIGURE>>>"

#: File name of the scaffold specification inside the source directory.
SPEC_FILENAME = "scaffold.json"
#: File name of the generated deck inside the source directory.
DEFAULT_OUTPUT_NAME = "narrative_scaffold.pptx"
#: The only schema version this tool understands.
SPEC_SCHEMA_VERSION = 1

#: The file mode the written deck gets.
# WHY: a temporary file is created with mode 0600, so a deck written
# through the atomic save would land on disk readable only by its
# owner, while every other file in this folder is 0644. The mode is
# set explicitly so the deliverable looks and behaves like the rest.
OUTPUT_FILE_MODE = 0o644
#: Identity fields that must be present and non-empty.
REQUIRED_IDENTITY_FIELDS = (
    "judul",
    "penulis",
    "nim",
    "pembimbing_satu",
    "pembimbing_dua",
    "title",
    "subtitle",
    "author",
    "institute",
    "date",
)
#: The house rule forbids the U+2014 em dash in generated sources.
EM_DASH = "\u2014"
# ---------------------------------------------------------------------------
# The specification model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameFigure:
    """The graphic bound to a filled frame.

    Attributes:
        path: The absolute path of the picture file.
        caption: The line that explains the picture.
        source: The provenance line, naming the file the picture came from.
        layout: How the graphic shares the panel: "side" leaves a
            column for the narration under the graphic, "feature" gives
            the whole panel to the graphic.

    """

    path: Path
    caption: str
    source: str
    layout: str = FIGURE_LAYOUT_SIDE


@dataclass(frozen=True)
class TimelinePlan:
    """The measured layout of a horizontal timeline of milestones.

    Attributes:
        points: The milestone texts, in order.
        size_pt: The type size the milestone cards are drawn at.
        card_width_in: The width of one milestone card in inches.
        text_width_in: The width of the text inside one card in inches.
        card_height_in: The height of every milestone card in inches.

    """

    points: tuple[str, ...]
    size_pt: float
    card_width_in: float
    text_width_in: float
    card_height_in: float


@dataclass(frozen=True)
class PillListPlan:
    """The measured layout of a vertical list of pills.

    Attributes:
        points: The pill labels, in order.
        size_pt: The type size the labels are drawn at.
        label_width_in: The width of the label inside one pill in inches.
        pill_height_in: The height of every pill in inches.
        band_top_in: The top of the first pill in inches.

    """

    points: tuple[str, ...]
    size_pt: float
    label_width_in: float
    pill_height_in: float
    band_top_in: float


@dataclass(frozen=True)
class CardsOnlyPlan:
    """The measured layout of a band of cards that fills the content area.

    Attributes:
        points: The texts of the cards, in order.
        size_pt: The type size the cards are drawn at.
        columns: How many cards sit in one row.
        card_width_in: The width of one card in inches.
        text_width_in: The width of the text inside one card in inches.
        row_heights: The height of every row of cards in inches.
        band_top_in: The top of the band in inches.
        band_height_in: The height of the band in inches.
        figure_panel_height_in: The height of the figure panel in inches, or
            zero when the frame carries no graphic.

    """

    points: tuple[str, ...]
    size_pt: float
    columns: int
    card_width_in: float
    text_width_in: float
    row_heights: tuple[float, ...]
    band_top_in: float
    band_height_in: float
    figure_panel_height_in: float


@dataclass(frozen=True)
class SlotFrame:
    """One placeholder slide of the scaffold.

    Attributes:
        id: Stable machine key. It is the suffix of the slot shape name, so
            matching a slide to a frame survives a retitle.
        section: Owner block the frame belongs to.
        title: The frame title, shown in the title band.
        body: The text of the unfilled slot.
        target_position: Where the frame belongs in the finished deck.
        note: Free-form note kept for the owner.
        figure: The graphic bound to the frame, or ``None`` for a frame
            that is still an empty slot.
        timeline: Whether the frame is drawn as a horizontal timeline of
            milestones instead of a slot or a filled frame.
        pill_list: Whether the frame is drawn as a vertical list of pills,
            one pill for every point of the body.
        cards_only: Whether the frame is drawn as a band of cards that fills
            the content area, with no figure panel.
        footer: The footer line of the slide, or an empty string when the
            layout default is used.
        subsection: The methodology subsection this slide belongs to,
            shown as a sub-title under the frame title.

    """

    id: str
    section: str
    title: str
    body: str
    target_position: str = ""
    note: str = ""
    figure: FrameFigure | None = None
    timeline: bool = False
    pill_list: bool = False
    cards_only: bool = False
    footer: str = ""
    subsection: str = ""


@dataclass(frozen=True)
class DeckIdentity:
    """The factual identity block shown on the cover slide.

    Attributes:
        judul: The paper title.
        penulis: The name of the author.
        nim: The student number.
        pembimbing_satu: The first supervisor.
        pembimbing_dua: The second supervisor.
        title: The report title.
        subtitle: The report subtitle.
        author: The author line on the cover.
        institute: The institute lines, one per list item.
        date: The year shown on the cover.

    """

    judul: str
    penulis: str
    nim: str
    pembimbing_satu: str
    pembimbing_dua: str
    title: str
    subtitle: str
    author: str
    institute: tuple[str, ...]
    date: str


@dataclass(frozen=True)
class Scaffold:
    """The whole specification: owner blocks, frames, palette and identity.

    Attributes:
        sections: The owner block names, in deck order.
        frames: The placeholder frames, in deck order.
        palette: Colour name to six digit hexadecimal string.
        identity: The cover identity block.
        meta: Every remaining key of the specification, kept verbatim.

    """

    sections: tuple[str, ...]
    frames: tuple[SlotFrame, ...]
    palette: dict[str, str]
    identity: DeckIdentity
    meta: dict[str, object]

    def frames_in(self, section: str) -> list[SlotFrame]:
        """Return the frames that belong to one owner block, in deck order.

        Args:
            section: The owner block name to look up.

        Returns:
            The frames whose ``section`` equals the argument.

        Raises:
            Nothing. The frames of a block are looked up, never validated here.
        """
        return [frame for frame in self.frames if frame.section == section]


# ---------------------------------------------------------------------------
# Loading and validating the specification
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NarrationPlan:
    """The measured layout of the horizontal narration band.

    WHY: the cards of a filled frame run in rows under the figure panel,
    so the height of a row is the height of its tallest card, and the band
    has to fit the content area that the figure panel leaves over. The
    plan is measured before anything is drawn, so a card is always as tall
    as the text it carries.

    Attributes:
        points: The narration points, one per card.
        size_pt: The type size the cards are drawn in.
        card_width_in: The width of one card in inches.
        text_width_in: The width the text of one card has.
        row_heights: The height of every row of cards in inches.
        band_height_in: The height of the whole band in inches.
        figure_panel_height_in: The height the figure panel is left with.

    """

    points: tuple[str, ...]
    size_pt: float
    card_width_in: float
    text_width_in: float
    row_heights: tuple[float, ...]
    band_height_in: float
    figure_panel_height_in: float


def _parse_frame_figure(
    entry: dict[str, object],
    base: Path,
    frame_id: str,
) -> FrameFigure | None:
    """Read and validate the optional graphic of one frame.

    WHY: a graphic is content, so a frame that names a picture that is not
    there must stop the build instead of producing a slide with a hole in
    it. The picture path is resolved against the folder of the
    specification, so a specification can be moved with its figures.

    Args:
        entry: The frame entry of the specification.
        base: The folder that holds the specification.
        frame_id: The frame identifier, used in the error messages.

    Returns:
        The bound graphic, or ``None`` when the frame carries no graphic.

    Raises:
        ScaffoldError: When the graphic block is malformed, when one of its
            fields is missing, or when the picture file does not exist.
    """
    raw = entry.get("figure")
    if raw is None:
        return None
    block = require_mapping(raw, f"frames['{frame_id}'].figure")
    relative = require_text(block.get("path"), f"frames['{frame_id}'].figure.path")
    caption = require_text(block.get("caption"), f"frames['{frame_id}'].figure.caption")
    source = require_text(block.get("source"), f"frames['{frame_id}'].figure.source")
    layout = require_text(
        block.get("layout", FIGURE_LAYOUT_SIDE),
        f"frames['{frame_id}'].figure.layout",
    )
    if layout not in {FIGURE_LAYOUT_SIDE, FIGURE_LAYOUT_FEATURE, FIGURE_LAYOUT_SIDE_POINTS}:
        failure_reason = (
            f"frame '{frame_id}' names the figure layout '{layout}', which is not one of "
            f"{FIGURE_LAYOUT_SIDE}, {FIGURE_LAYOUT_FEATURE} and {FIGURE_LAYOUT_SIDE_POINTS}"
        )
        raise ScaffoldError(failure_reason)
    picture = base / relative
    if not picture.exists():
        failure_reason = (f"frame '{frame_id}' points at the picture {relative}, which does not exist")
        raise ScaffoldError(failure_reason)
    return FrameFigure(path=picture, caption=caption, source=source, layout=layout)


def load_spec(path: Path) -> Scaffold:
    """Load and validate the scaffold specification.

    Args:
        path: The path of the ``scaffold.json`` file to read.

    Returns:
        A validated :class:`Scaffold`.

    Raises:
        ScaffoldError: When the file is missing, unreadable, not valid JSON, of
        an unknown schema version, or missing any required member.
    """
    if not path.exists():
        failure_reason = (f"scaffold specification not found: {path}")
        raise ScaffoldError(failure_reason)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        failure_reason = (f"cannot read the scaffold specification {path}: {exc}")
        raise ScaffoldError(failure_reason) from exc

    if EM_DASH in raw:
        failure_reason = (
            f"the scaffold specification {path} contains a U+2014 em dash; "
            "the house rule forbids it in generated sources"
        )
        raise ScaffoldError(failure_reason)

    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        failure_reason = (f"the scaffold specification {path} is not valid JSON: {exc}")
        raise ScaffoldError(failure_reason) from exc

    document: dict[str, object] = require_mapping(data, "the top level of the specification")
    version = document.get("schema_version")
    if version != SPEC_SCHEMA_VERSION:
        failure_reason = (
            f"unsupported scaffold schema_version {version!r} in {path}; "
            f"this tool understands {SPEC_SCHEMA_VERSION}"
        )
        raise ScaffoldError(failure_reason)

    raw_sections = document.get("sections")
    if not isinstance(raw_sections, list) or len(raw_sections) == 0:
        failure_reason = (f"the specification {path} needs a non-empty 'sections' list")
        raise ScaffoldError(failure_reason)
    sections: list[str] = []
    for index, item in enumerate(cast("list[object]", raw_sections)):
        name = require_text(item, f"sections[{index}]")
        if name in sections:
            failure_reason = (f"the specification {path} repeats the owner block '{name}'")
            raise ScaffoldError(failure_reason)
        sections.append(name)

    raw_frames = document.get("frames")
    if not isinstance(raw_frames, list) or len(raw_frames) == 0:
        failure_reason = (f"the specification {path} needs a non-empty 'frames' list")
        raise ScaffoldError(failure_reason)
    frames: list[SlotFrame] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(cast("list[object]", raw_frames)):
        entry = require_mapping(item, f"frames[{index}]")
        frame_id = require_text(entry.get("id"), f"frames[{index}].id")
        if frame_id in seen_ids:
            failure_reason = (f"the specification {path} repeats the frame id '{frame_id}'")
            raise ScaffoldError(failure_reason)
        seen_ids.add(frame_id)
        section = require_text(entry.get("section"), f"frames[{index}].section")
        if section not in sections:
            failure_reason = (f"frame '{frame_id}' names the owner block '{section}', which is not one of {sections}")
            raise ScaffoldError(failure_reason)
        title = require_text(entry.get("title"), f"frames[{index}].title")
        body: object = entry.get("body", "")
        if not isinstance(body, str):
            failure_reason = (f"frame '{frame_id}' needs a string body, found {type(body).__name__}")
            raise ScaffoldError(failure_reason)
        target_position: object = entry.get("target_position", "")
        if not isinstance(target_position, str):
            failure_reason = (f"frame '{frame_id}' needs a string target_position")
            raise ScaffoldError(failure_reason)
        note: object = entry.get("note", "")
        if not isinstance(note, str):
            failure_reason = (f"frame '{frame_id}' needs a string note")
            raise ScaffoldError(failure_reason)
        timeline: object = entry.get("timeline", False)
        if not isinstance(timeline, bool):
            failure_reason = f"frame '{frame_id}' needs a boolean timeline flag"
            raise ScaffoldError(failure_reason)
        pill_list: object = entry.get("pill_list", False)
        if not isinstance(pill_list, bool):
            failure_reason = f"frame '{frame_id}' needs a boolean pill_list flag"
            raise ScaffoldError(failure_reason)
        cards_only: object = entry.get("cards_only", False)
        if not isinstance(cards_only, bool):
            failure_reason = f"frame '{frame_id}' needs a boolean cards_only flag"
            raise ScaffoldError(failure_reason)
        footer: object = entry.get("footer", "")
        if not isinstance(footer, str):
            failure_reason = f"frame '{frame_id}' needs a string footer"
            raise ScaffoldError(failure_reason)
        subsection: object = entry.get("subsection", "")
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

    raw_palette = require_mapping(document.get("palette"), "a 'palette' object")
    palette: dict[str, str] = {}
    for name, value in raw_palette.items():
        text: str = require_text(value, f"palette['{name}']")
        if not is_hex_colour(text):
            failure_reason = (f"palette['{name}'] must be six hexadecimal digits, found '{text}'")
            raise ScaffoldError(failure_reason)
        palette[name] = text.upper()
    for required in (
        SLOT_BOX_COLOR,
        SLOT_TEXT_COLOR,
        TITLE_TEXT_COLOR,
        TITLE_BAND_COLOR,
        ACCENT_COLOR,
        BODY_TEXT_COLOR,
    ):
        if required not in palette:
            failure_reason = (f"the palette is missing the required colour '{required}'")
            raise ScaffoldError(failure_reason)

    raw_identity = require_mapping(document.get("identity"), "an 'identity' object")
    for field_name in REQUIRED_IDENTITY_FIELDS:
        if field_name == "institute":
            continue  # the institute is a list of lines and is checked below.
        _ = require_text(raw_identity.get(field_name), f"identity.{field_name}")
    institute_raw: object = raw_identity["institute"]
    if isinstance(institute_raw, str):
        institute = tuple(line.strip() for line in institute_raw.splitlines() if len(line.strip()) != 0)
    elif isinstance(institute_raw, list):
        institute = tuple(require_text(line, "identity.institute[]") for line in cast("list[object]", institute_raw))
    else:
        failure_reason = (
            "identity.institute must be a string or a list of strings, "
            f"found {type(institute_raw).__name__}"
        )
        raise ScaffoldError(failure_reason)
    if len(institute) == 0:
        failure_reason = ("identity.institute must hold at least one line")
        raise ScaffoldError(failure_reason)

    identity = DeckIdentity(
        judul=str(raw_identity["judul"]).strip(),
        penulis=str(raw_identity["penulis"]).strip(),
        nim=str(raw_identity["nim"]).strip(),
        pembimbing_satu=str(raw_identity["pembimbing_satu"]).strip(),
        pembimbing_dua=str(raw_identity["pembimbing_dua"]).strip(),
        title=str(raw_identity["title"]).strip(),
        subtitle=str(raw_identity["subtitle"]).strip(),
        author=str(raw_identity["author"]).strip(),
        institute=institute,
        date=str(raw_identity["date"]).strip(),
    )

    meta: dict[str, object] = {
        key: value
        for key, value in document.items()
        if key not in {"schema_version", "sections", "frames", "palette", "identity"}
    }
    return Scaffold(
        sections=tuple(sections),
        frames=tuple(frames),
        palette=palette,
        identity=identity,
        meta=meta,
    )


# ---------------------------------------------------------------------------
# Small text helpers
# ---------------------------------------------------------------------------
def _new_guid() -> str:
    """Return a fresh identifier in the brace-wrapped form OOXML expects.

    Returns:
        A string such as ``{6E2C1A0B-...}``.
    """
    return "{" + str(uuid.uuid4()).upper() + "}"


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def rgb(palette: dict[str, str], name: str) -> RGBColor:
    """Return a palette colour as a python-pptx RGBColor.

    Args:
        palette: Mapping of palette names to six digit hex strings.
        name: The palette entry to look up.

    Returns:
        The colour as an RGBColor.

    Raises:
        Nothing directly; the helper that does the check reports the failure.
    """
    return RGBColor.from_string(_palette_hex(palette, name))


def css_colour(palette: dict[str, str], name: str) -> str:
    """Return a palette colour as the CSS literal EasyPPTX expects.

    WHY: EasyPPTX resolves a colour from a "#RRGGBB" string, a colour triple or
    a library colour name. A bare hex string is dropped without an error, so the
    "#" prefix is part of the contract and is added in this one place.

    Args:
        palette: Mapping of palette names to six digit hex strings.
        name: The palette entry to look up.

    Returns:
        The colour as a CSS string such as '#21302F', which EasyPPTX accepts.

    Raises:
        Nothing directly; the helper that does the check reports the failure.
    """
    return "#" + _palette_hex(palette, name)


def _palette_hex(palette: dict[str, str], name: str) -> str:
    """Return the six digit hex string of a palette entry.

    Args:
        palette: Mapping of palette names to six digit hex strings.
        name: The palette entry to look up.

    Returns:
        The six digit hex value of that palette entry.

    Raises:
        ScaffoldError: When the palette holds no entry under that name.
    """
    try:
        value = palette[name]
    except KeyError as error:
        known = ", ".join(sorted(palette))
        failure_reason = (f"the palette has no colour named {name!r}; the known colours are: {known}")
        raise ScaffoldError(failure_reason) from error
    return value.upper()


def font_report() -> list[str]:
    """Report the faces the deck uses and flag any substitution.

    Returns:
        One line naming the title face and the text face, plus one line
        for every face whose first preference is not installed on this
        machine.
    """
    lines = [f"fonts: title '{TITLE_FONT}', body '{BODY_FONT}'"]
    for label, preference, resolved in (
        ("title", TITLE_FONT_PREFERENCE, TITLE_FONT),
        ("body", BODY_FONT_PREFERENCE, BODY_FONT),
    ):
        if not font_is_installed(preference[0]):
            lines.append(
                f"fonts: the {label} face '{preference[0]}' is not installed on this machine, "
                f"so '{resolved}' is used instead",
            )
    return lines


def style_run(
    run: _Run,
    *,
    size: Length,
    color: RGBColor,
    bold: bool,
    italic: bool,
    font_name: str | None = None,
) -> None:
    """Apply the house typography to a single text run.

    Args:
        run: The text run to style.
        size: The point size to apply.
        color: The colour to apply.
        bold: Whether the run is bold.
        italic: Whether the run is italic.
        font_name: The face to apply. None keeps the face the run already
            carries and falls back to the text face only when it has none.
    """
    if font_name is not None:
        run.font.name = font_name
    elif run.font.name is None:
        run.font.name = BODY_FONT
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def add_text_box(
    slide: Slide,
    left_in: float,
    top_in: float,
    width_in: float,
    height_in: float,
    lines: Sequence[str],
    *,
    size: Length,
    color: str,
    bold: bool,
    italic: bool,
    align: str = "left",
    vertical: str = "top",
    line_spacing: float | None = None,
    font_name: str = BODY_FONT,
    word_wrap: bool = True,
) -> Shape:
    """Add a text box to a slide through EasyPPTX and return the shape.

    WHY THE INCH CONVERSION: EasyPPTX reads a plain number as a percentage, so
    every coordinate is wrapped in in_() to keep the geometry identical to the
    inch based layout the deck was designed with. The text frame margins are
    zeroed afterwards because EasyPPTX keeps the python-pptx defaults, which
    would push the text away from the frame title band.

    Args:
        slide: The slide that receives the text box.
        left_in: Distance from the left edge of the slide, in inches.
        top_in: Distance from the top edge of the slide, in inches.
        width_in: Width of the text box, in inches.
        height_in: Height of the text box, in inches.
        lines: The lines of text, one paragraph each, in order.
        size: The point size to apply.
        color: The colour to apply.
        bold: Whether the text is bold.
        italic: Whether the text is italic.
        align: The horizontal alignment: 'left', 'center' or 'right'.
        vertical: The vertical alignment: 'top', 'middle' or 'bottom'.
        line_spacing: The line spacing multiplier, or None to keep the default.
        font_name: The face to apply. The display face marks the titles and
            the text face carries everything else.
        word_wrap: Whether the text may break onto a second line. A line of
            text that must stay on one line sets this to False, so a
            renderer that substitutes a wider face widens the line instead
            of breaking it and spilling out of the glass behind it.

    Returns:
        The text box shape, so the caller can rename it.
    """
    shape = slide.add_text(
        "\n".join(lines),
        x=in_(left_in),
        y=in_(top_in),
        width=in_(width_in),
        height=in_(height_in),
        font_size=round(size.pt),
        font_bold=bold,
        font_italic=italic,
        font_name=font_name,
        align=align,
        vertical=vertical,
        color=color,
        fit="none",
    )
    frame = shape.text_frame
    frame.word_wrap = word_wrap
    frame.margin_left = Emu(0)
    frame.margin_right = Emu(0)
    frame.margin_top = Emu(0)
    frame.margin_bottom = Emu(0)
    if line_spacing is not None:
        for paragraph in frame.paragraphs:
            paragraph.line_spacing = line_spacing
    return shape


def _flat_shape(shape: Shape, color: RGBColor) -> None:
    """Give a shape a flat fill with no outline and no shadow.

    WHY: the deck is a flat design, and the PowerPoint theme would otherwise
    draw a border and a shadow around every autoshape.

    Args:
        shape: The shape to flatten.
        color: The fill colour to apply.
    """
    shape.fill.solid()
    shape.fill.fore_color.rgb = color  # pyrefly: ignore[bad-assignment]
    shape.line.fill.background()
    shape.shadow.inherit = False


def new_presentation() -> Presentation:
    """Create an empty 16:9 presentation with EasyPPTX.

    WHY THE EXTRA STEPS: EasyPPTX builds a 13.33 inch wide deck, while the
    16:9 slide size in the file format is 13.3333 inches. The width is forced
    to the exact figure so the deck matches the layout it was designed with,
    and the slide size type is stamped as screen16x9 so PowerPoint opens the
    file in widescreen mode instead of guessing.

    Returns:
        The new deck.

    Raises:
        ScaffoldError: When the package does not expose a slide size element.
    """
    presentation = Presentation(aspect_ratio="16:9")
    native = presentation.pptx_presentation
    native.slide_width = Emu(SLIDE_WIDTH_EMU)
    native.slide_height = Emu(SLIDE_HEIGHT_EMU)
    # WHY: python-pptx publishes no accessor for the slide size element, and
    # the tool has to stamp its type attribute so PowerPoint opens the deck
    # as 16:9 and not as 4:3.
    element: _Element | None = native.part._element.find(qn("p:sldSz"))  # ruff: ignore[private-member-access]
    if element is None:
        failure_reason = ("the presentation part carries no p:sldSz element, so the slide size cannot be fixed")
        raise ScaffoldError(failure_reason)
    element.set("type", "screen16x9")
    return presentation


def add_blank_slide(presentation: Presentation) -> Slide:
    """Add an empty slide that carries no placeholder shapes.

    WHY: a slide built from a layout that carries placeholders would show
    empty boxes in the deck.

    Args:
        presentation: The deck that receives the new slide.

    Returns:
        The new slide.
    """
    return presentation.add_slide()


# ---------------------------------------------------------------------------
# The frosted-glass skin
# ---------------------------------------------------------------------------


def _set_fill_alpha(shape: Shape, opacity: float) -> None:
    """Make the solid fill of a shape translucent.

    Args:
        shape: The shape whose solid fill is adjusted.
        opacity: How opaque the fill stays, from 0.0 to 1.0.

    """
    value = max(MIN_OPACITY, min(MAX_OPACITY, opacity))
    solid: _Element | None = shape._element.spPr.find(qn("a:solidFill"))  # ruff: ignore[private-member-access]
    if solid is None:
        return
    colour: _Element | None = solid.find(qn("a:srgbClr"))
    if colour is None:
        return
    for existing in colour.findall(qn("a:alpha")):
        colour.remove(existing)
    colour.append(parse_xml(f'<a:alpha {nsdecls("a")} val="{round(value * PERCENT_SCALE)}"/>'))


def _set_line_alpha(shape: Shape, opacity: float) -> None:
    """Make the outline of a shape translucent.

    Args:
        shape: The shape whose outline is adjusted.
        opacity: How opaque the outline stays, from 0.0 to 1.0.

    """
    value = max(MIN_OPACITY, min(MAX_OPACITY, opacity))
    line: _Element | None = shape._element.spPr.find(qn("a:ln"))  # ruff: ignore[private-member-access]
    if line is None:
        return
    solid = line.find(qn("a:solidFill"))
    if solid is None:
        return
    colour: _Element | None = solid.find(qn("a:srgbClr"))
    if colour is None:
        return
    for existing in colour.findall(qn("a:alpha")):
        colour.remove(existing)
    colour.append(parse_xml(f'<a:alpha {nsdecls("a")} val="{round(value * PERCENT_SCALE)}"/>'))


def _add_soft_shadow(
    shape: Shape,
    *,
    colour: RGBColor,
    opacity: float,
    blur_pt: float | None = None,
    distance_pt: float | None = None,
    direction_degrees: int | None = None,
) -> None:
    """Give a shape the soft shadow that makes it float, or the glow that makes it sparkle.

    Args:
        shape: The shape that receives the shadow.
        colour: The colour of the shadow.
        opacity: How opaque the shadow stays, from 0.0 to 1.0.
        blur_pt: The blur radius of the shadow, in points.
        distance_pt: How far the shadow is cast, in points. Zero gives a glow.
        direction_degrees: The direction the shadow is cast, clockwise from the horizontal.

    Raises:
        ScaffoldError: When the shape carries no effect list to hold the shadow.
    """
    value = max(MIN_OPACITY, min(MAX_OPACITY, opacity))
    blur = SHADOW_BLUR_PT if blur_pt is None else blur_pt
    distance = SHADOW_DISTANCE_PT if distance_pt is None else distance_pt
    direction = SHADOW_DIRECTION_DEGREES if direction_degrees is None else direction_degrees
    shape.shadow.inherit = False
    effect: _Element | None = shape._element.spPr.find(qn("a:effectLst"))  # ruff: ignore[private-member-access]
    if effect is None:
        failure_reason = "the shape carries no effect list to hold the shadow"
        raise ScaffoldError(failure_reason)
    for existing in effect.findall(qn("a:outerShdw")):
        effect.remove(existing)
    effect.append(
        parse_xml(
            f'<a:outerShdw {nsdecls("a")} blurRad="{int(blur * EMU_PER_POINT)}" '
            f'dist="{int(distance * EMU_PER_POINT)}" '
            f'dir="{direction * ANGLE_UNITS_PER_DEGREE}" rotWithShape="0">'
            f'<a:srgbClr val="{colour}"><a:alpha val="{round(value * PERCENT_SCALE)}"/></a:srgbClr>'
            f"</a:outerShdw>",
        ),
    )


def _set_corner_radius(shape: Shape, radius_in: float) -> None:
    """Round a shape with a radius that is the same on every card.

    The rounded-rectangle adjustment is a fraction of the shorter side, so the
    radius has to be divided by that side to give one constant radius across
    cards of very different sizes.

    Args:
        shape: The rounded rectangle whose radius is set.
        radius_in: The radius of the corner, in inches.

    Raises:
        ScaffoldError: When the shape has no size to round.
    """
    shorter = min(shape.width, shape.height)
    if shorter <= 0:
        failure_reason = "the shape has no size to round"
        raise ScaffoldError(failure_reason)
    adjustment = radius_in / (shorter / EMU_PER_INCH)
    shape.adjustments[0] = min(adjustment, MAX_CORNER_ADJUSTMENT)


def _glass_shape(
    shape: Shape,
    *,
    fill: RGBColor,
    fill_opacity: float,
    edge: RGBColor | None,
    edge_opacity: float,
    edge_width_pt: float,
    shadow_colour: RGBColor,
    shadow_opacity: float,
) -> None:
    """Give a shape the frosted-glass treatment.

    Args:
        shape: The shape that becomes a glass panel.
        fill: The colour of the milky fill.
        fill_opacity: How opaque the fill stays, from 0.0 to 1.0.
        edge: The colour of the thin border, or None for a borderless panel.
        edge_opacity: How opaque the border stays, from 0.0 to 1.0.
        edge_width_pt: The width of the border, in points.
        shadow_colour: The colour of the soft shadow under the panel.
        shadow_opacity: How opaque the shadow stays, from 0.0 to 1.0.

    """
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill  # pyrefly: ignore[bad-assignment]
    _set_fill_alpha(shape, fill_opacity)
    if edge is None:
        shape.line.fill.background()
    else:
        shape.line.fill.solid()
        shape.line.fill.fore_color.rgb = edge  # pyrefly: ignore[bad-assignment]
        shape.line.width = Pt(edge_width_pt)
        _set_line_alpha(shape, edge_opacity)
    _add_soft_shadow(shape, colour=shadow_colour, opacity=shadow_opacity)


def _set_sky_background(slide: Slide, sky_path: Path) -> None:
    """Lay the sky picture behind a slide.

    The picture is placed as the first shape of the slide, so the frosted
    glass panels and the sparkles sit on top of it.

    Args:
        slide: The slide whose background is painted.
        sky_path: The sky picture to lay down.
    """
    native = slide.pptx_slide
    picture = native.shapes.add_picture(
        str(sky_path),
        Emu(0),
        Emu(0),
        width=Emu(SLIDE_WIDTH_EMU),
        height=Emu(SLIDE_HEIGHT_EMU),
    )
    picture.name = NAME_SKY_BACKGROUND
    # WHY: the picture has to sit behind every panel, so its element is moved
    # to the front of the shape tree. The first two children of that tree are
    # the group properties, so index two is the first shape.
    tree = native.shapes._spTree  # ruff: ignore[private-member-access]
    element = picture._element  # ruff: ignore[private-member-access]
    tree.remove(element)
    tree.insert(2, element)


def _lerp_hex(first: str, second: str, ratio: float) -> str:
    """Blend two hexadecimal colours.

    Args:
        first: The colour at a ratio of 0.0.
        second: The colour at a ratio of 1.0.
        ratio: How far along the blend the result sits, from 0.0 to 1.0.

    Returns:
        The blended colour as six hexadecimal digits.
    """
    start = int(first, 16)
    end = int(second, 16)
    channels = []
    for shift in (16, 8, 0):
        first_channel = (start >> shift) & CHANNEL_MASK
        second_channel = (end >> shift) & CHANNEL_MASK
        channels.append(round(first_channel + (second_channel - first_channel) * ratio))
    return "".join(f"{channel:02X}" for channel in channels)


def _overlaps(
    left: float,
    top: float,
    size: float,
    avoid: Sequence[tuple[float, float, float, float]],
) -> bool:
    """Say whether a square would land on top of a protected rectangle.

    Args:
        left: The left edge of the square, in inches.
        top: The top edge of the square, in inches.
        size: The width and the height of the square, in inches.
        avoid: The rectangles to keep clear, as left, top, width and height.

    Returns:
        True when the square touches one of the rectangles.
    """
    for rect_left, rect_top, rect_width, rect_height in avoid:
        horizontal = left < rect_left + rect_width and left + size > rect_left
        vertical = top < rect_top + rect_height and top + size > rect_top
        if horizontal and vertical:
            return True
    return False


def _add_sparkles(
    slide: Slide,
    palette: dict[str, str],
    *,
    seed: int,
    zones: Sequence[tuple[float, float, float, float]],
    avoid: Sequence[tuple[float, float, float, float]] = (),
    maximum: int = 14,
) -> int:
    """Scatter the glowing sparkle field over a slide.

    The field is drawn from a fixed seed, so the same slide always receives the
    same sparkles and a regenerated deck is identical to the previous one.

    Args:
        slide: The slide that receives the sparkles.
        palette: The palette that resolves every colour name.
        seed: The seed of the placement, fixed per slide so the deck is reproducible.
        zones: The rectangles the sparkles are placed in, as left, top, width and height.
        avoid: The rectangles the sparkles must not touch.
        maximum: The largest number of sparkles that may be placed.

    Returns:
        The number of sparkles that were placed.

    Raises:
        ScaffoldError: When no zone was given to place the sparkles in.
    """
    if len(zones) == 0:
        failure_reason = "a sparkle field needs at least one zone to be placed in"
        raise ScaffoldError(failure_reason)
    # WHY: the field is a decorative layout, not a secret. A fixed seed keeps a
    # regenerated deck identical, which is what the reproducibility of this
    # generator depends on.
    generator = random.Random(seed)  # ruff: ignore[suspicious-non-cryptographic-random-usage]
    gold = _palette_hex(palette, SPARK_GOLD_COLOR)
    cream = _palette_hex(palette, SPARK_CREAM_COLOR)
    placed = 0
    attempts = 0
    while placed < maximum and attempts < maximum * SPARKLE_ATTEMPT_FACTOR:
        attempts += 1
        zone = zones[generator.randrange(len(zones))]
        size = SPARKLE_BASE_SIZE_IN * generator.uniform(0.45, 1.85)
        left = zone[0] + generator.uniform(0.0, max(zone[2] - size, 0.0))
        top = zone[1] + generator.uniform(0.0, max(zone[3] - size, 0.0))
        if _overlaps(left, top, size, avoid):
            continue
        # WHY: a white sparkle vanishes on the light top of the sky and a
        # gold one vanishes on the dark bottom, so the colour of a sparkle
        # follows the brightness of the sky behind it. The yellow to white
        # variation the owner asked for is the one on the dark part.
        background = sky_colour_at(palette, (top + size / 2.0) / SLIDE_HEIGHT_IN)
        if relative_luminance(background) > SPARKLE_LIGHT_BACKGROUND_LUMINANCE:
            colour = _palette_hex(palette, SPARK_DARK_COLOR)
        else:
            colour = _lerp_hex(gold, cream, generator.random())
        shape = slide.add_shape(
            "STAR_4_POINT",
            x=in_(left),
            y=in_(top),
            width=in_(size),
            height=in_(size),
            fill_color=f"#{colour}",
        )
        shape.name = f"sparkle_{placed:02d}"
        shape.line.fill.background()
        _set_fill_alpha(shape, generator.uniform(0.45, 1.0))
        shape.rotation = float(generator.randrange(0, 180, 15))
        _add_soft_shadow(
            shape,
            colour=RGBColor.from_string(colour),
            opacity=SPARKLE_GLOW_OPACITY,
            blur_pt=SPARKLE_GLOW_BLUR_PT,
            distance_pt=0.0,
            direction_degrees=0,
        )
        placed += 1
    return placed


def _add_pill(
    slide: Slide,
    *,
    left_in: float,
    top_in: float,
    width_in: float,
    height_in: float,
    fill: RGBColor,
    fill_opacity: float,
    shadow_colour: RGBColor,
    name: str,
) -> Shape:
    """Add a rounded pill, the shape the interface language uses for badges.

    Args:
        slide: The slide that receives the pill.
        left_in: The left edge of the pill, in inches.
        top_in: The top edge of the pill, in inches.
        width_in: The width of the pill, in inches.
        height_in: The height of the pill, in inches.
        fill: The colour of the pill.
        fill_opacity: How opaque the fill stays, from 0.0 to 1.0.
        shadow_colour: The colour of the soft shadow under the pill.
        name: The machine name of the shape.

    Returns:
        The pill that was drawn.
    """
    pill = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(left_in),
        y=in_(top_in),
        width=in_(width_in),
        height=in_(height_in),
        fill_color=f"#{fill}",
    )
    pill.name = name
    _set_corner_radius(pill, height_in / 2.0)
    _set_fill_alpha(pill, fill_opacity)
    pill.line.fill.background()
    _add_soft_shadow(pill, colour=shadow_colour, opacity=GLASS_SHADOW_OPACITY)
    return pill


def _palette_swatch_rect() -> tuple[float, float, float, float]:
    """Give the rectangle the tiny palette reference occupies.

    WHY THE FOOTER: the owner asked for the reference to sit in the footer at
    the content margin, so it reads as a mark of the slide rather than as an
    object floating in the corner. The right edge of the reference is the
    right content margin, and the circles are centred on the footer line.

    Returns:
        The rectangle as left, top, width and height, in inches.
    """
    width = PALETTE_SWATCH_COUNT * PALETTE_SWATCH_SIZE_IN
    width += (PALETTE_SWATCH_COUNT - 1) * PALETTE_SWATCH_GAP_IN
    right = SLIDE_WIDTH_IN - MARGIN_X_IN
    left = right - width
    top = FOOTER_TOP_IN + PALETTE_SWATCH_FOOTER_OFFSET_IN
    return (left, top, width, PALETTE_SWATCH_SIZE_IN)


def _add_palette_swatch(slide: Slide, palette: dict[str, str]) -> tuple[float, float, float, float]:
    """Draw the tiny four colour palette reference in the footer.

    The reference is a whisper: the fill of every swatch sits at five percent
    opacity, and only a hairline of the same colour keeps the four circles
    legible. It sits in the footer, at the right content margin, so it reads
    as a mark of the slide rather than as an object floating in the corner.

    Args:
        slide: The slide that receives the reference.
        palette: The palette that resolves every colour name.

    Returns:
        The rectangle the reference occupies, as left, top, width and height.
    """
    names = list(palette)[:PALETTE_SWATCH_COUNT]
    left, top, width, height = _palette_swatch_rect()
    for index, name in enumerate(names):
        swatch = slide.add_shape(
            "OVAL",
            x=in_(left + index * (PALETTE_SWATCH_SIZE_IN + PALETTE_SWATCH_GAP_IN)),
            y=in_(top),
            width=in_(PALETTE_SWATCH_SIZE_IN),
            height=in_(height),
            fill_color=css_colour(palette, name),
        )
        swatch.name = f"palette_swatch_{index}"
        _set_fill_alpha(swatch, PALETTE_SWATCH_OPACITY)
        swatch.line.fill.solid()
        swatch.line.fill.fore_color.rgb = rgb(palette, name)  # pyrefly: ignore[bad-assignment]
        swatch.line.width = Pt(PALETTE_SWATCH_EDGE_PT)
        _set_line_alpha(swatch, PALETTE_SWATCH_EDGE_OPACITY)
        # WHY: the reference is a mark of the slide, not an object resting on
        # it. The soft shadow that made it float in the corner is gone, and
        # the inherited theme shadow is switched off so nothing casts one.
        swatch.shadow.inherit = False
    return (left, top, width, height)


def measure_text_inches(text: str, family: str, size_pt: float) -> float:
    """Measure the width of a line of text in the face the deck names.

    WHY: a glass pill that hugs its text has to know how wide that text is.
    Measuring with the very font file the deck names is the only width that
    matches what the renderer will draw; counting characters and guessing
    an average is not.

    Args:
        text: The text to measure.
        family: The family name the text is drawn in.
        size_pt: The size of the text in points.

    Returns:
        The width of the text in inches. Zero when the face cannot be loaded,
        which the caller must treat as "this text cannot be measured".
    """
    path = font_file_for(family)
    if path is None:
        return 0.0
    pixels = round(size_pt * MEASUREMENT_PIXELS_PER_POINT)
    try:
        font = ImageFont.truetype(str(path), pixels)
    except OSError:
        return 0.0
    width_in_points = font.getlength(text) / MEASUREMENT_PIXELS_PER_POINT
    return width_in_points / POINTS_PER_INCH


def add_title_slide(
    presentation: Presentation,
    identity: DeckIdentity,
    palette: dict[str, str],
    sky_path: Path,
) -> Slide:
    """Draw the cover slide.

    The cover carries the sky gradient, the sparkle field and one frosted glass
    card that holds the paper title and the supervisors.

    Args:
        presentation: The presentation that receives the slide.
        identity: The identity block of the report.
        palette: The palette that resolves every colour name.
        sky_path: The sky picture the slide sits on.

    Returns:
        The slide that was drawn.
    """
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)

    _ = _add_pill(
        slide,
        left_in=MARGIN_X_IN,
        top_in=0.42,
        width_in=GOLD_PILL_WIDTH_IN,
        height_in=GOLD_PILL_HEIGHT_IN,
        fill=rgb(palette, ACCENT_COLOR),
        fill_opacity=1.0,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        name=NAME_GOLD_PILL,
    )

    title_plate = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(COVER_TITLE_PLATE_TOP_IN),
        width=in_(CONTENT_WIDTH_IN),
        height=in_(COVER_TITLE_PLATE_HEIGHT_IN),
        fill_color=css_colour(palette, SLOT_BOX_COLOR),
    )
    title_plate.name = NAME_COVER_TITLE_PLATE
    # WHY A FULL-WIDTH PLATE: the owner asked for the cover title to have
    # a holder like every other piece of glass in this deck, and chose the
    # full-width plate. It spans the whole content width, exactly like the
    # title band on a placeholder slide, so the cover speaks the same design
    # language and the 40 pt title has room to breathe. A rounded rectangle
    # can only round up to half of its shorter side, so half the height is
    # the largest radius that exists, and that shape is a full stadium.
    _set_corner_radius(title_plate, COVER_TITLE_PLATE_HEIGHT_IN / 2.0)
    _glass_shape(
        title_plate,
        fill=rgb(palette, SLOT_BOX_COLOR),
        fill_opacity=GLASS_BAND_OPACITY,
        edge=rgb(palette, FROST_EDGE_COLOR),
        edge_opacity=GLASS_EDGE_OPACITY,
        edge_width_pt=GLASS_EDGE_WIDTH_PT,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        shadow_opacity=GLASS_SHADOW_OPACITY,
    )

    title = add_text_box(
        slide,
        MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        COVER_TITLE_PLATE_TOP_IN,
        CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN,
        COVER_TITLE_PLATE_HEIGHT_IN,
        [identity.title],
        size=Pt(40),
        font_name=TITLE_FONT,
        color=css_colour(palette, TITLE_TEXT_COLOR),
        bold=True,
        italic=False,
        vertical="middle",
        word_wrap=False,
    )
    title.name = NAME_COVER_TITLE

    measured_subtitle = measure_text_inches(identity.subtitle, BODY_FONT, SUBTITLE_SIZE_PT)
    if measured_subtitle <= 0.0:
        measured_subtitle = SUBTITLE_FALLBACK_WIDTH_IN
    subtitle_pill_width = min(
        CONTENT_WIDTH_IN,
        measured_subtitle * SUBTITLE_WIDTH_HEADROOM + 2.0 * SUBTITLE_PILL_PADDING_IN,
    )

    subtitle_pill = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(SUBTITLE_PILL_TOP_IN),
        width=in_(subtitle_pill_width),
        height=in_(SUBTITLE_PILL_HEIGHT_IN),
        fill_color=css_colour(palette, SLOT_BOX_COLOR),
    )
    subtitle_pill.name = NAME_COVER_SUBTITLE_PILL
    # WHY A PILL: the owner asked for the subtitle to have a holder like the
    # other pieces of glass in this deck. A rounded rectangle can only round
    # its corners up to half of its shorter side, so half the height is the
    # largest radius that exists, and that shape is a full stadium, which is
    # what a pill is.
    _set_corner_radius(subtitle_pill, SUBTITLE_PILL_HEIGHT_IN / 2.0)
    _glass_shape(
        subtitle_pill,
        fill=rgb(palette, SLOT_BOX_COLOR),
        fill_opacity=GLASS_BAND_OPACITY,
        edge=rgb(palette, FROST_EDGE_COLOR),
        edge_opacity=GLASS_EDGE_OPACITY,
        edge_width_pt=GLASS_EDGE_WIDTH_PT,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        shadow_opacity=GLASS_SHADOW_OPACITY,
    )

    subtitle = add_text_box(
        slide,
        MARGIN_X_IN + SUBTITLE_PILL_PADDING_IN,
        SUBTITLE_PILL_TOP_IN,
        subtitle_pill_width - 2.0 * SUBTITLE_PILL_PADDING_IN,
        SUBTITLE_PILL_HEIGHT_IN,
        [identity.subtitle],
        size=Pt(SUBTITLE_SIZE_PT),
        color=css_colour(palette, SUBTITLE_TEXT_COLOR),
        bold=False,
        italic=False,
        align="center",
        vertical="middle",
        word_wrap=False,
    )
    subtitle.name = NAME_COVER_SUBTITLE

    author = add_text_box(
        slide,
        MARGIN_X_IN,
        2.66,
        CONTENT_WIDTH_IN,
        1.45,
        [identity.author, *identity.institute, identity.date],
        size=Pt(15),
        color=css_colour(palette, BODY_TEXT_COLOR),
        bold=False,
        italic=False,
        line_spacing=1.15,
    )
    author.name = NAME_COVER_AUTHOR

    card = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(COVER_CARD_TOP_IN),
        width=in_(CONTENT_WIDTH_IN),
        height=in_(COVER_CARD_HEIGHT_IN),
        fill_color=css_colour(palette, SLOT_BOX_COLOR),
    )
    card.name = NAME_COVER_CARD
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

    judul = add_text_box(
        slide,
        MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        COVER_CARD_TOP_IN + 0.26,
        CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN,
        0.95,
        [identity.judul.upper()],
        size=COVER_JUDUL_SIZE,
        font_name=TITLE_FONT,
        color=css_colour(palette, BODY_TEXT_COLOR),
        bold=True,
        italic=False,
        align="center",
        vertical="middle",
    )
    judul.name = NAME_COVER_JUDUL

    supervisors = add_text_box(
        slide,
        MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        COVER_CARD_TOP_IN + 1.28,
        CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN,
        0.70,
        [f"NIM {identity.nim}    Supervisor: {identity.pembimbing_satu}    Supervisor: {identity.pembimbing_dua}"],
        size=COVER_SUPERVISOR_SIZE,
        color=css_colour(palette, BODY_TEXT_COLOR),
        bold=False,
        italic=False,
        align="center",
        vertical="middle",
    )
    supervisors.name = NAME_COVER_SUPERVISORS

    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide,
        palette,
        seed=SPARKLE_SEED_COVER,
        zones=(
            (9.55, 1.88, 3.25, 2.55),
            (MARGIN_X_IN, 3.98, CONTENT_WIDTH_IN, 0.16),
            (MARGIN_X_IN, 6.50, CONTENT_WIDTH_IN, 0.70),
        ),
        avoid=(
            (
                MARGIN_X_IN,
                COVER_TITLE_PLATE_TOP_IN,
                CONTENT_WIDTH_IN,
                COVER_TITLE_PLATE_HEIGHT_IN,
            ),
            (MARGIN_X_IN, COVER_CARD_TOP_IN, CONTENT_WIDTH_IN, COVER_CARD_HEIGHT_IN),
            swatch,
        ),
        maximum=15,
    )
    return slide


def add_outline_slide(
    presentation: Presentation,
    scaffold: Scaffold,
    palette: dict[str, str],
    sky_path: Path,
) -> Slide:
    """Draw the outline slide.

    The outline sits on one frosted glass card that lists the owner blocks.

    Args:
        presentation: The presentation that receives the slide.
        scaffold: The scaffold that names the owner blocks.
        palette: The palette that resolves every colour name.
        sky_path: The sky picture the slide sits on.

    Returns:
        The slide that was drawn.
    """
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)

    _ = _add_pill(
        slide,
        left_in=MARGIN_X_IN,
        top_in=0.30,
        width_in=GOLD_PILL_WIDTH_IN,
        height_in=GOLD_PILL_HEIGHT_IN,
        fill=rgb(palette, ACCENT_COLOR),
        fill_opacity=1.0,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        name=NAME_GOLD_PILL,
    )

    title = add_text_box(
        slide,
        MARGIN_X_IN,
        0.55,
        CONTENT_WIDTH_IN,
        0.75,
        ["OUTLINE"],
        size=Pt(26),
        font_name=TITLE_FONT,
        color=css_colour(palette, TITLE_TEXT_COLOR),
        bold=True,
        italic=False,
        vertical="middle",
    )
    title.name = NAME_OUTLINE_TITLE

    for index, section in enumerate(scaffold.sections):
        pill_top = OUTLINE_PILL_TOP_IN + index * (OUTLINE_PILL_HEIGHT_IN + OUTLINE_PILL_GAP_IN)
        pill = slide.add_shape(
            "ROUNDED_RECTANGLE",
            x=in_(MARGIN_X_IN),
            y=in_(pill_top),
            width=in_(CONTENT_WIDTH_IN),
            height=in_(OUTLINE_PILL_HEIGHT_IN),
            fill_color=css_colour(palette, SLOT_BOX_COLOR),
        )
        pill.name = f"{NAME_OUTLINE_PILL}{index}"
        # WHY: the owner asked for every point of the outline to be a pill of
        # its own instead of one square card with a list inside it. A rounded
        # rectangle can only round to half of its shorter side, so half the
        # height is the largest radius that exists, and that shape is a full
        # stadium.
        _set_corner_radius(pill, OUTLINE_PILL_HEIGHT_IN / 2.0)
        _glass_shape(
            pill,
            fill=rgb(palette, SLOT_BOX_COLOR),
            fill_opacity=GLASS_FILL_OPACITY,
            edge=rgb(palette, FROST_EDGE_COLOR),
            edge_opacity=GLASS_EDGE_OPACITY,
            edge_width_pt=GLASS_EDGE_WIDTH_PT,
            shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
            shadow_opacity=GLASS_SHADOW_OPACITY,
        )
        label = add_text_box(
            slide,
            MARGIN_X_IN + OUTLINE_PILL_PADDING_IN,
            pill_top,
            CONTENT_WIDTH_IN - 2.0 * OUTLINE_PILL_PADDING_IN,
            OUTLINE_PILL_HEIGHT_IN,
            [section],
            size=OUTLINE_PILL_SIZE,
            font_name=TITLE_FONT,
            color=css_colour(palette, TITLE_TEXT_COLOR),
            bold=True,
            italic=False,
            align="center",
            vertical="middle",
        )
        label.name = f"{NAME_OUTLINE_PILL}{index}_label"

    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide,
        palette,
        seed=SPARKLE_SEED_OUTLINE,
        zones=((MARGIN_X_IN, 5.70, CONTENT_WIDTH_IN, 1.00),),
        avoid=(swatch,),
        maximum=9,
    )
    return slide


def _add_frame_header(slide: Slide, frame: SlotFrame, palette: dict[str, str]) -> None:
    """Draw the chrome that every frame slide shares.

    WHY: a filled frame and an empty slot are two different bodies of the
    same frame, and a title band that is drawn twice drifts. The chrome is
    therefore drawn once, here, and both bodies call it.

    Args:
        slide: The slide to draw on.
        frame: The frame whose title and owner block are shown.
        palette: The colour name to hexadecimal string map.

    """
    band = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(HEADER_CARD_TOP_IN),
        width=in_(CONTENT_WIDTH_IN),
        height=in_(HEADER_CARD_HEIGHT_IN),
        fill_color=css_colour(palette, TITLE_BAND_COLOR),
    )
    band.name = NAME_TITLE_BAND
    # WHY: the owner asked for the title plate to be rounded as much as the
    # narration body. A rounded rectangle can only round its corners up to
    # half of its shorter side, so half the height is the largest radius that
    # exists, and that shape is a full stadium, which is what a pill is.
    _set_corner_radius(band, HEADER_CARD_HEIGHT_IN / 2.0)
    _glass_shape(
        band,
        fill=rgb(palette, TITLE_BAND_COLOR),
        fill_opacity=GLASS_BAND_OPACITY,
        edge=None,
        edge_opacity=GLASS_EDGE_OPACITY,
        edge_width_pt=GLASS_EDGE_WIDTH_PT,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        shadow_opacity=GLASS_SHADOW_OPACITY,
    )

    _ = _add_pill(
        slide,
        left_in=MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        top_in=GOLD_PILL_TOP_IN,
        width_in=GOLD_PILL_WIDTH_IN,
        height_in=GOLD_PILL_HEIGHT_IN,
        fill=rgb(palette, ACCENT_COLOR),
        fill_opacity=1.0,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        name=NAME_GOLD_PILL,
    )

    # WHY: a slide that belongs to a methodology subsection says so under its
    # title, so the title box gives up the band the sub-title occupies and the
    # two are stacked inside the same plate instead of overlapping.
    title_height = HEADER_CARD_HEIGHT_IN
    if len(frame.subsection) != 0:
        title_height = HEADER_CARD_HEIGHT_IN - FRAME_SUBTITLE_BAND_IN
    title = add_text_box(
        slide,
        MARGIN_X_IN + GLASS_CARD_PADDING_IN,
        HEADER_CARD_TOP_IN,
        CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN - SECTION_CHIP_WIDTH_IN,
        title_height,
        [frame.title],
        size=FRAME_TITLE_SIZE,
        font_name=TITLE_FONT,
        color=css_colour(palette, TITLE_TEXT_COLOR),
        bold=True,
        italic=False,
        vertical="middle",
    )
    title.name = NAME_FRAME_TITLE
    if len(frame.subsection) != 0:
        # WHY: the section chip ends above this band, so the sub-title can run
        # the full width of the plate and a long subsection name still fits.
        subtitle = add_text_box(
            slide,
            MARGIN_X_IN + GLASS_CARD_PADDING_IN,
            HEADER_CARD_TOP_IN + title_height,
            CONTENT_WIDTH_IN - 2.0 * GLASS_CARD_PADDING_IN,
            FRAME_SUBTITLE_BAND_IN,
            [frame.subsection],
            size=FRAME_SUBTITLE_SIZE,
            font_name=BODY_FONT,
            color=css_colour(palette, ACCENT_COLOR),
            bold=True,
            italic=False,
            vertical="middle",
        )
        subtitle.name = f"{NAME_FRAME_SUBTITLE}:{frame.id}"

    chip = _add_pill(
        slide,
        left_in=MARGIN_X_IN + CONTENT_WIDTH_IN - GLASS_CARD_PADDING_IN - SECTION_CHIP_WIDTH_IN,
        top_in=SECTION_CHIP_TOP_IN,
        width_in=SECTION_CHIP_WIDTH_IN,
        height_in=SECTION_CHIP_HEIGHT_IN,
        fill=rgb(palette, FROST_EDGE_COLOR),
        fill_opacity=GLASS_CHIP_OPACITY,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        name=NAME_SECTION_CHIP,
    )
    chip_frame = chip.text_frame
    chip_frame.word_wrap = True
    chip_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    chip_frame.margin_left = Emu(int(0.08 * EMU_PER_INCH))
    chip_frame.margin_right = Emu(int(0.08 * EMU_PER_INCH))
    chip_frame.margin_top = Emu(0)
    chip_frame.margin_bottom = Emu(0)
    chip_paragraph = chip_frame.paragraphs[0]
    chip_paragraph.alignment = PP_ALIGN.CENTER
    chip_run = chip_paragraph.add_run()
    chip_run.text = frame.section.upper()
    style_run(
        chip_run,
        size=SECTION_TAG_SIZE,
        color=rgb(palette, SUBTITLE_TEXT_COLOR),
        bold=True,
        italic=False,
    )


def _footer_text(frame: SlotFrame) -> str:
    """Return the footer line of a frame.

    WHY: every frame may name its own footer, because the line of one block
    does not describe the slides of another block. The layout of the frame
    is the fallback, so a frame that names no footer still gets the line
    that belongs to its layout.

    Args:
        frame: The frame whose footer line is resolved.

    Returns:
        The footer line of the frame.
    """
    if len(frame.footer) != 0:
        return frame.footer
    if frame.pill_list:
        return PILL_LIST_FOOTER_TEXT
    if frame.cards_only:
        return CARDS_ONLY_FOOTER_TEXT
    if frame.timeline:
        return TIMELINE_FOOTER_TEXT
    if frame.figure is not None:
        return FILLED_FOOTER_TEXT
    return FOOTER_TEXT


def add_placeholder_slide(
    presentation: Presentation,
    frame: SlotFrame,
    palette: dict[str, str],
    sky_path: Path,
) -> Slide:
    """Draw one placeholder slide.

    The slide carries the sky gradient, a floating glass title band with a pill
    badge and a gold accent, one frosted glass card that holds the narration
    slot, and the sparkle field. The card is the machine key of the frame, so
    the update mode still finds it after the owner has edited the deck by hand.

    Args:
        presentation: The presentation that receives the slide.
        frame: The frame that names the owner block, the title and the body.
        palette: The palette that resolves every colour name.
        sky_path: The sky picture the slide sits on.

    Returns:
        The slide that was drawn.
    """
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)

    _add_frame_header(slide, frame, palette)
    card = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(SLOT_BOX_TOP_IN),
        width=in_(CONTENT_WIDTH_IN),
        height=in_(SLOT_BOX_HEIGHT_IN),
        fill_color=css_colour(palette, SLOT_BOX_COLOR),
    )
    card.name = SLOT_SHAPE_PREFIX + frame.id
    # WHY: the owner asked for the narration body to read as a pill. A
    # rounded rectangle can only round its corners up to half of its
    # shorter side, so half the height is the largest radius that exists,
    # and that shape is a full stadium, which is what a pill is.
    _set_corner_radius(card, SLOT_BOX_HEIGHT_IN / 2.0)
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

    text_frame = card.text_frame
    text_frame.word_wrap = True
    text_frame.vertical_anchor = MSO_ANCHOR.TOP
    padding = Emu(int(SLOT_BOX_PADDING_IN * EMU_PER_INCH))
    text_frame.margin_left = padding
    text_frame.margin_right = padding
    text_frame.margin_top = padding
    text_frame.margin_bottom = padding
    paragraph = text_frame.paragraphs[0]
    # WHY: an autoshape inherits the theme's centred paragraph alignment, so the
    # narration would be centred while every other text element is left aligned.
    paragraph.alignment = PP_ALIGN.LEFT
    run = paragraph.add_run()
    run.text = frame.body
    style_run(run, size=SLOT_TEXT_SIZE, color=rgb(palette, SLOT_TEXT_COLOR), bold=False, italic=False)

    footer = add_text_box(
        slide,
        MARGIN_X_IN,
        FOOTER_TOP_IN,
        CONTENT_WIDTH_IN,
        0.30,
        [_footer_text(frame)],
        size=FOOTER_TEXT_SIZE,
        color=css_colour(palette, FOOTER_TEXT_COLOR),
        bold=False,
        italic=False,
    )
    footer.name = NAME_SLOT_FOOTER

    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide,
        palette,
        seed=SPARKLE_SEED_PLACEHOLDER + sum(ord(character) for character in frame.id),
        zones=(
            (MARGIN_X_IN, 5.60, CONTENT_WIDTH_IN, 1.05),
            (MARGIN_X_IN, 1.42, CONTENT_WIDTH_IN, 0.42),
        ),
        avoid=(
            (MARGIN_X_IN, SLOT_BOX_TOP_IN - 0.10, CONTENT_WIDTH_IN, SLOT_BOX_HEIGHT_IN + 0.20),
            swatch,
        ),
        maximum=14,
    )
    return slide


def _narration_points(frame: SlotFrame) -> list[str]:
    """Return the points of a frame body, one entry per line.

    WHY: the specification writes a filled frame as one point per line, and
    every point becomes a card of its own, so the body has to be split
    into its points before anything is drawn.

    Args:
        frame: The frame whose body is split.

    Returns:
        The points of the body, with the bullet markers removed.

    """
    points: list[str] = []
    for line in frame.body.splitlines():
        text = _strip_bullet(line.strip())
        if len(text) != 0:
            points.append(text)
    return points


def _plan_narration_cards(frame: SlotFrame, family: str, columns: int) -> NarrationPlan:
    """Measure the horizontal narration band of a filled frame.

    WHY: the cards run in rows, so the height of a row is the height of
    its tallest card and the whole band has to fit the content area under
    the figure. The type size is stepped down until the band fits,
    because a card whose text does not fit is worse than a card whose type
    is a little smaller. The measurement is made against a box that is
    FILLED_MEASURE_WIDTH_FACTOR narrower than the real one, so a card is
    tall enough for a substituted face as well.

    Args:
        frame: The frame whose body is measured.
        family: The face the narration is drawn in.
        columns: How many cards sit in one row.

    Returns:
        The measured plan: the points, the type size, the card width, the
        height of every row, the height of the band and the height the
        figure panel is left with.

    Raises:
        ScaffoldError: When even the smallest type size does not fit.

    """
    points = tuple(_narration_points(frame))
    card_width = (CONTENT_WIDTH_IN - FILLED_CARD_GAP_IN * (columns - 1)) / columns
    text_width = card_width - 2.0 * FILLED_CARD_PADDING_IN - FILLED_BULLET_INDENT_IN
    measured_width = text_width * FILLED_MEASURE_WIDTH_FACTOR
    size = FILLED_NARRATION_SIZE.pt
    band_height = 0.0
    row_heights: tuple[float, ...] = ()
    while size >= FILLED_NARRATION_MIN_SIZE_PT - 1e-9:
        lines = [wrap_line_count(point, family, size, measured_width) for point in points]
        heights: list[float] = []
        for start in range(0, len(points), columns):
            row_lines = max(lines[start : start + columns])
            heights.append(
                row_lines * line_height_inches(family, size) * FILLED_NARRATION_LINE_SPACING
                + 2.0 * FILLED_CARD_PADDING_IN,
            )
        row_heights = tuple(heights)
        band_height = sum(row_heights) + FILLED_CARD_GAP_IN * max(0, len(row_heights) - 1)
        if band_height <= FILLED_BAND_MAX_IN:
            # WHY: a frame that carries no narration has no band at all, so
            # the figure panel takes the whole content area and no gap is
            # left between the panel and a band that is not there.
            gap = FILLED_FIGURE_GAP_IN if band_height > 0.0 else 0.0
            figure_height = FILLED_CARD_HEIGHT_IN - band_height - gap
            return NarrationPlan(
                points=points,
                size_pt=size,
                card_width_in=card_width,
                text_width_in=text_width,
                row_heights=row_heights,
                band_height_in=band_height,
                figure_panel_height_in=figure_height,
            )
        size -= FILLED_NARRATION_SIZE_STEP_PT
    failure_reason = (
        f"the narration of frame '{frame.id}' needs {band_height:.2f} inches at the smallest type "
        f"size of {FILLED_NARRATION_MIN_SIZE_PT} pt, but the band is only {FILLED_BAND_MAX_IN} "
        "inches tall"
    )
    raise ScaffoldError(failure_reason)


def _collect_narration_shapes(slide: Slide, frame_id: str) -> list[Shape]:
    """Return the narration shapes of a frame, in reading order.

    WHY: the narration of a filled frame is a stack of cards. The first
    card keeps the name that identifies the frame, and the other cards
    carry that name with an order number, so the whole stack can be found,
    read and replaced as one thing.

    Args:
        slide: The slide to look at.
        frame_id: The identifier of the frame.

    Returns:
        The shapes that carry the narration, the first card first.

    """
    cards: list[Shape] = []
    primary = _find_shape_by_name(slide, SLOT_SHAPE_PREFIX + frame_id)
    if primary is not None:
        cards.append(primary)
    prefix = NARRATION_CARD_SHAPE_PREFIX + frame_id + "#"
    extras: list[tuple[int, Shape]] = []
    for raw_shape in slide.shapes:
        shape: Shape = raw_shape
        name = shape.name
        if not name.startswith(prefix):
            continue
        try:
            order = int(name[len(prefix) :])
        except ValueError:
            continue
        extras.append((order, shape))
    extras.sort(key=operator.itemgetter(0))
    cards.extend(shape for _, shape in extras)
    return cards


def _narration_text(cards: Sequence[Shape]) -> str:
    """Return the visible text of a narration, one line per card.

    Args:
        cards: The narration shapes, in reading order.

    Returns:
        The text of every card, joined with a newline.

    """
    parts = [_shape_text(card) for card in cards]
    return "\n".join(part for part in parts if len(part) != 0)


def _remove_figure_panel(slide: Slide, frame: SlotFrame) -> None:
    """Remove the figure panel of a frame from its slide.

    WHY: the panel and its picture are drawn from the measured plan, so a
    body that changed leaves a panel of the wrong height behind, and the
    picture is a shape of its own that the panel does not carry.

    Args:
        slide: The slide the panel sits on.
        frame: The frame whose panel is removed.

    """
    prefix = FIGURE_SHAPE_PREFIX + frame.id
    names = {prefix, prefix + "_image", NAME_FIGURE_CAPTION, NAME_FIGURE_SOURCE}
    for raw_shape in list(slide.shapes):
        shape: Shape = raw_shape
        if shape.name in names:
            element = shape._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)


def _refresh_narration(slide: Slide, frame: SlotFrame, palette: dict[str, str], slot: Shape) -> None:
    """Redraw the narration of a frame from the specification.

    WHY: a filled frame carries a band of cards and a figure panel, and
    the band is measured from the body, so a body that changed needs the
    whole band and the panel to be drawn again. An unfinished frame has
    one wide slot, and only its words change.

    Args:
        slide: The slide the narration sits on.
        frame: The frame whose body is drawn.
        palette: The colour name to hexadecimal string map.
        slot: The slot shape of the frame.

    """
    if frame.figure is not None and frame.figure.layout == FIGURE_LAYOUT_SIDE_POINTS:
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
        plan = _plan_pill_list(frame, BODY_FONT)
        _add_pill_list(slide, frame, palette, plan)
        return
    if frame.cards_only:
        for card in _collect_narration_shapes(slide, frame.id):
            element = card._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)
        _remove_figure_panel(slide, frame)
        _remove_cards_only_panels(slide)
        plan = _plan_cards_only(frame, BODY_FONT, CARDS_ONLY_COLUMNS)
        _add_cards_only(slide, frame, palette, plan)
        return
    if frame.timeline:
        for card in _collect_narration_shapes(slide, frame.id):
            element = card._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)
        _remove_timeline_chrome(slide)
        plan = _plan_timeline(frame, BODY_FONT, TIMELINE_COLUMNS)
        _add_timeline_cards(slide, frame, palette, plan)
        return
    if frame.figure is None:
        _set_shape_text(
            slot,
            frame.body,
            size=SLOT_TEXT_SIZE,
            color=rgb(palette, SLOT_TEXT_COLOR),
            bold=False,
            italic=False,
        )
        return
    for card in _collect_narration_shapes(slide, frame.id):
        element = card._element  # ruff: ignore[private-member-access]
        element.getparent().remove(element)
    _remove_figure_panel(slide, frame)
    plan = _plan_narration_cards(frame, BODY_FONT, FILLED_BAND_COLUMNS)
    _add_figure_panel(slide, frame, palette, plan.figure_panel_height_in)
    _add_narration_column(slide, frame, palette, plan)


def _add_narration_column(
    slide: Slide, frame: SlotFrame, palette: dict[str, str], plan: NarrationPlan,
) -> None:
    """Draw the horizontal narration band of a filled frame.

    WHY: the owner asked for the cards to run horizontally, so the points
    sit in a band under the figure panel, FILLED_BAND_COLUMNS to a row,
    and every card of a row is as tall as the tallest of them, so a row
    reads as a row.

    Args:
        slide: The slide to draw on.
        frame: The frame whose body is drawn.
        palette: The colour name to hexadecimal string map.
        plan: The measured layout of the band.

    """
    band_top = FILLED_CARD_TOP_IN + plan.figure_panel_height_in + FILLED_FIGURE_GAP_IN
    for index, point in enumerate(plan.points):
        row = index // FILLED_BAND_COLUMNS
        column = index % FILLED_BAND_COLUMNS
        left = MARGIN_X_IN + column * (plan.card_width_in + FILLED_CARD_GAP_IN)
        top = band_top + sum(plan.row_heights[:row]) + FILLED_CARD_GAP_IN * row
        card = slide.add_shape(
            "ROUNDED_RECTANGLE",
            x=in_(left),
            y=in_(top),
            width=in_(plan.card_width_in),
            height=in_(plan.row_heights[row]),
            fill_color=css_colour(palette, SLOT_BOX_COLOR),
        )
        if index == 0:
            card.name = SLOT_SHAPE_PREFIX + frame.id
        else:
            card.name = f"{NARRATION_CARD_SHAPE_PREFIX}{frame.id}#{index}"
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
        text_frame = card.text_frame
        text_frame.word_wrap = True
        text_frame.vertical_anchor = MSO_ANCHOR.TOP
        padding = Emu(int(FILLED_CARD_PADDING_IN * EMU_PER_INCH))
        text_frame.margin_left = padding
        text_frame.margin_right = padding
        text_frame.margin_top = padding
        text_frame.margin_bottom = padding
        _write_bullets(
            card,
            point,
            size=Pt(plan.size_pt),
            color=rgb(palette, SLOT_TEXT_COLOR),
            bold=False,
            italic=False,
            font_name=BODY_FONT,
        )


def _picture_aspect(path: Path) -> float:
    """Return the width to height ratio of a picture file.

    WHY: a picture that fills a panel has to be as wide as its own
    proportions ask for, so the panel can give it the height it needs.

    Args:
        path: The picture file to measure.

    Returns:
        The width of the picture divided by its height.
    """
    width_px, height_px = picture_size_inches(path)
    return width_px / height_px


def _source_box_height(source: str, width_in: float) -> float:
    """Measure the height the provenance line needs in the notes column.

    WHY: the provenance line of a figure frame sits in the narrow column
    beside the picture, and a long provenance wraps into several lines. The
    box that holds it has to be as tall as the text, or the line runs out
    of the panel it belongs to. The text is measured against a box that is
    narrower than the real one, because a renderer that cannot see the face
    of the deck draws it wider, and the box must survive that too.

    Args:
        source: The provenance line.
        width_in: The width of the column the line is drawn in.

    Returns:
        The height of the box in inches.
    """
    lines = wrap_line_count(
        source,
        BODY_FONT,
        FILLED_SOURCE_SIZE.pt,
        width_in * CARDS_ONLY_MEASURE_WIDTH_FACTOR,
    )
    needed = lines * line_height_inches(BODY_FONT, FILLED_SOURCE_SIZE.pt) + FILLED_SOURCE_GAP_IN
    return max(FILLED_SOURCE_HEIGHT_IN, needed)


def _side_points_plan(
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
    top_in = area_top_in
    for index, card_height in enumerate(heights):
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


def _add_figure_panel(slide: Slide, frame: SlotFrame, palette: dict[str, str], panel_height_in: float) -> None:
    """Draw the figure panel of a filled frame.

    WHY: the narration band runs under the figure, so the figure panel is
    full width and the picture sits on its left while the caption and the
    provenance line sit in a column on its right. A caption under the
    picture would eat the height of the panel and shrink the picture,
    which is the one thing the panel cannot afford. A frame that carries
    only a graphic gives the whole panel to its picture, because that
    picture is the content of the frame.

    Args:
        slide: The slide to draw on.
        frame: The frame whose graphic is drawn.
        palette: The colour name to hexadecimal string map.
        panel_height_in: The height of the panel in inches.

    Raises:
        ScaffoldError: When the frame carries no graphic.

    """
    figure = frame.figure
    if figure is None:
        failure_reason = f"frame '{frame.id}' has no graphic to draw"
        raise ScaffoldError(failure_reason)
    panel = slide.add_shape(
        "ROUNDED_RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(FILLED_CARD_TOP_IN),
        width=in_(CONTENT_WIDTH_IN),
        height=in_(panel_height_in),
        fill_color=css_colour(palette, SLOT_BOX_COLOR),
    )
    panel.name = FIGURE_SHAPE_PREFIX + frame.id
    _set_corner_radius(panel, GLASS_CORNER_RADIUS_IN)
    _glass_shape(
        panel,
        fill=rgb(palette, SLOT_BOX_COLOR),
        fill_opacity=GLASS_FILL_OPACITY,
        edge=rgb(palette, FROST_EDGE_COLOR),
        edge_opacity=GLASS_EDGE_OPACITY,
        edge_width_pt=GLASS_EDGE_WIDTH_PT,
        shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
        shadow_opacity=GLASS_SHADOW_OPACITY,
    )
    area_left = MARGIN_X_IN + FILLED_FIGURE_PADDING_IN
    area_top = FILLED_CARD_TOP_IN + FILLED_FIGURE_PADDING_IN
    area_height = panel_height_in - 2.0 * FILLED_FIGURE_PADDING_IN
    inner_width = CONTENT_WIDTH_IN - 2.0 * FILLED_FIGURE_PADDING_IN
    if figure.layout == FIGURE_LAYOUT_SIDE_POINTS:
        _draw_side_points_panel(
            slide, frame, palette, area_left, area_top, area_height, inner_width,
        )
        return
    if figure.layout == FIGURE_LAYOUT_FEATURE:
        # WHY: a frame that carries no narration gives the whole panel to
        # its picture. The picture is as tall as the panel allows and as
        # wide as that height needs, and the caption keeps a column of its
        # own, so the picture is as large as the slide can show it.
        picture_width = min(
            area_height * _picture_aspect(figure.path),
            inner_width - FEATURE_NOTES_COLUMN_IN - FILLED_FIGURE_COLUMN_GAP_IN,
        )
        caption_width = inner_width - picture_width - FILLED_FIGURE_COLUMN_GAP_IN
    else:
        picture_width = FILLED_FIGURE_AREA_WIDTH_IN
        caption_width = FILLED_CAPTION_COLUMN_WIDTH_IN
    # WHY: every picture starts at the same x, so the left edge of the figure
    # lines up with the left edge of the card band underneath it. A centred
    # picture starts further to the right on every slide, because the four
    # thesis figures have four different shapes.
    left, top, width, height = fit_picture_in_box(
        figure.path,
        (area_left, area_top, picture_width, area_height),
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
    caption_left = area_left + width + FILLED_FIGURE_COLUMN_GAP_IN
    caption_height = FILLED_CAPTION_HEIGHT_IN
    source_height = FILLED_SOURCE_HEIGHT_IN
    source_top = area_top + FILLED_CAPTION_HEIGHT_IN
    caption_lines = figure.caption.splitlines()
    if len(caption_lines) == 0:
        caption_lines = [figure.caption]
    if figure.layout == FIGURE_LAYOUT_FEATURE:
        # WHY: a frame that gives the whole panel to its picture has room for
        # the notes beside it. The caption then takes the height of the picture
        # area and the provenance line sits under it, so the plot stays the
        # content of the frame and the words become a column of notes.
        source_height = _source_box_height(figure.source, caption_width)
        caption_height = area_height - source_height - FILLED_SOURCE_GAP_IN
        source_top = area_top + caption_height + FILLED_SOURCE_GAP_IN
    caption = add_text_box(
        slide,
        caption_left,
        area_top,
        caption_width,
        caption_height,
        caption_lines,
        size=FILLED_CAPTION_SIZE,
        color=css_colour(palette, SLOT_TEXT_COLOR),
        bold=False,
        italic=False,
    )
    caption.name = NAME_FIGURE_CAPTION
    source = add_text_box(
        slide,
        caption_left,
        source_top,
        caption_width,
        source_height,
        [figure.source],
        size=FILLED_SOURCE_SIZE,
        color=css_colour(palette, SLOT_TEXT_COLOR),
        bold=False,
        italic=False,
    )
    source.name = NAME_FIGURE_SOURCE


def add_filled_slide(presentation: Presentation, frame: SlotFrame, palette: dict[str, str], sky_path: Path) -> Slide:
    """Draw a filled frame: the figure on top, the narration band under it.

    WHY: the owner asked for the narration cards to run horizontally, so
    the figure takes the top of the content area at its full width and
    the cards run in a band under it.

    Args:
        presentation: The presentation the slide is added to.
        frame: The frame that is drawn.
        palette: The colour name to hexadecimal string map.
        sky_path: The picture that is the sky behind the slide.

    Returns:
        The slide that was drawn.

    Raises:
        ScaffoldError: When the frame carries no graphic.

    """
    if frame.figure is None:
        failure_reason = f"frame '{frame.id}' has no graphic to draw"
        raise ScaffoldError(failure_reason)
    # WHY: a frame whose points stand beside its picture has no band under
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
    footer = add_text_box(
        slide,
        MARGIN_X_IN,
        FOOTER_TOP_IN,
        CONTENT_WIDTH_IN,
        0.30,
        [_footer_text(frame)],
        size=FOOTER_TEXT_SIZE,
        color=css_colour(palette, FOOTER_TEXT_COLOR),
        bold=False,
        italic=False,
    )
    footer.name = NAME_SLOT_FOOTER
    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide,
        palette,
        seed=SPARKLE_SEED_PLACEHOLDER + sum(ord(character) for character in frame.id),
        zones=((MARGIN_X_IN, 1.42, CONTENT_WIDTH_IN, 0.42),),
        avoid=(
            (MARGIN_X_IN, FILLED_CARD_TOP_IN, CONTENT_WIDTH_IN, FILLED_CARD_HEIGHT_IN),
            swatch,
        ),
        maximum=6,
    )
    return slide


def _split_milestone(point: str) -> tuple[str, str]:
    """Split a milestone into its label and its detail.

    WHY: a milestone on a timeline is read as a label and a sentence, and the
    label is set in a heavier face on its own line, so the two have to be
    told apart. The label is the part before the first colon, so the
    specification can carry the two in one line.

    Args:
        point: The milestone text.

    Returns:
        The label and the detail of the milestone.
    """
    head, separator, tail = point.partition(MILESTONE_SEPARATOR)
    if len(separator) == 0:
        return (point, "")
    return (head + separator, tail.strip())


def _plan_timeline(frame: SlotFrame, family: str, columns: int) -> TimelinePlan:
    """Measure the milestone cards of a horizontal timeline.

    WHY: the milestones share one row, so every card has the same width and
    the same height, and that height is the height of the tallest milestone.
    The type size steps down until the tallest card fits its budget, because
    a card that is too short would clip its own text.

    Args:
        frame: The frame whose body holds the milestones.
        family: The face the text is measured with.
        columns: How many milestones sit in one row.

    Returns:
        The measured layout of the timeline.

    Raises:
        ScaffoldError: When even the smallest type size does not fit.
    """
    points = tuple(_narration_points(frame))
    card_width = (CONTENT_WIDTH_IN - TIMELINE_CARD_GAP_IN * (columns - 1)) / columns
    text_width = card_width - 2.0 * TIMELINE_CARD_PADDING_IN
    measured_width = text_width * FILLED_MEASURE_WIDTH_FACTOR
    size = TIMELINE_SIZE.pt
    # WHY: the height the tallest card needs is carried out of the loop, so
    # the failure message can name it when even the smallest type size is too
    # big.
    needed = 0.0
    while size >= TIMELINE_MIN_SIZE_PT - 1e-9:
        lines = 0
        for point in points:
            label, detail = _split_milestone(point)
            lines = max(
                lines,
                wrap_line_count(label, family, size, measured_width)
                + wrap_line_count(detail, family, size, measured_width),
            )
        needed = (
            lines * line_height_inches(family, size) * TIMELINE_LINE_SPACING
            + 2.0 * TIMELINE_CARD_PADDING_IN
        )
        if needed <= TIMELINE_CARD_HEIGHT_IN:
            return TimelinePlan(
                points=points,
                size_pt=size,
                card_width_in=card_width,
                text_width_in=text_width,
                card_height_in=TIMELINE_CARD_HEIGHT_IN,
            )
        size -= TIMELINE_SIZE_STEP_PT
    failure_reason = (
        f"the milestones of frame '{frame.id}' need {needed:.2f} inches at the "
        f"smallest type size of {TIMELINE_MIN_SIZE_PT} pt, but a milestone card is only "
        f"{TIMELINE_CARD_HEIGHT_IN} inches tall"
    )
    raise ScaffoldError(failure_reason)


def _write_milestone(
    shape: Shape,
    point: str,
    *,
    size: Length,
    color: RGBColor,
    font_name: str = BODY_FONT,
) -> None:
    """Draw one milestone as a label and a detail.

    WHY: a milestone is a phase of the project, and a phase is named before
    it is described. The label is therefore set in a heavier face on its own
    line, and the detail follows it.

    Args:
        shape: The shape that carries the milestone.
        point: The milestone text, the label before the first colon.
        size: The type size of the milestone.
        color: The type colour of the milestone.
        font_name: The face the milestone is drawn in.

    """
    text_frame = shape.text_frame
    text_frame.clear()
    label, detail = _split_milestone(point)
    label_paragraph = text_frame.paragraphs[0]
    label_paragraph.alignment = PP_ALIGN.LEFT
    label_paragraph.line_spacing = TIMELINE_LINE_SPACING
    label_run = label_paragraph.add_run()
    label_run.text = label
    style_run(label_run, size=size, color=color, bold=True, italic=False, font_name=font_name)
    if len(detail) != 0:
        detail_paragraph = text_frame.add_paragraph()
        detail_paragraph.alignment = PP_ALIGN.LEFT
        detail_paragraph.line_spacing = TIMELINE_LINE_SPACING
        detail_run = detail_paragraph.add_run()
        detail_run.text = detail
        style_run(detail_run, size=size, color=color, bold=False, italic=False, font_name=font_name)


def _add_timeline_cards(
    slide: Slide, frame: SlotFrame, palette: dict[str, str], plan: TimelinePlan,
) -> None:
    """Draw the axis, the nodes and the milestone cards of a timeline.

    WHY: a timeline is an axis with a node on it for every milestone, and the
    text of the milestone sits in a card under its node. The first card keeps
    the name that identifies the frame, and the other cards carry that name
    with an order number, so the whole row is found, read and replaced as one
    thing, exactly like the narration band of a filled frame.

    Args:
        slide: The slide to draw on.
        frame: The frame whose milestones are drawn.
        palette: The colour name to hexadecimal string map.
        plan: The measured layout of the timeline.

    """
    axis = slide.add_shape(
        "RECTANGLE",
        x=in_(MARGIN_X_IN),
        y=in_(TIMELINE_AXIS_TOP_IN),
        width=in_(CONTENT_WIDTH_IN),
        height=in_(TIMELINE_AXIS_HEIGHT_IN),
        fill_color=css_colour(palette, ACCENT_COLOR),
    )
    axis.name = NAME_TIMELINE_AXIS
    _flat_shape(axis, rgb(palette, ACCENT_COLOR))
    for index, point in enumerate(plan.points):
        centre = MARGIN_X_IN + index * (plan.card_width_in + TIMELINE_CARD_GAP_IN)
        centre += plan.card_width_in / 2.0
        node = slide.add_shape(
            "OVAL",
            x=in_(centre - TIMELINE_NODE_SIZE_IN / 2.0),
            y=in_(TIMELINE_AXIS_TOP_IN + TIMELINE_AXIS_HEIGHT_IN / 2.0 - TIMELINE_NODE_SIZE_IN / 2.0),
            width=in_(TIMELINE_NODE_SIZE_IN),
            height=in_(TIMELINE_NODE_SIZE_IN),
            fill_color=css_colour(palette, TITLE_BAND_COLOR),
        )
        node.name = f"{NAME_TIMELINE_NODE}{index}"
        _glass_shape(
            node,
            fill=rgb(palette, TITLE_BAND_COLOR),
            fill_opacity=GLASS_BAND_OPACITY,
            edge=rgb(palette, ACCENT_COLOR),
            edge_opacity=1.0,
            edge_width_pt=1.25,
            shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
            shadow_opacity=GLASS_SHADOW_OPACITY,
        )
        node_frame = node.text_frame
        node_frame.word_wrap = False
        node_frame.margin_left = Emu(0)
        node_frame.margin_right = Emu(0)
        node_frame.margin_top = Emu(0)
        node_frame.margin_bottom = Emu(0)
        node_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        node_paragraph = node_frame.paragraphs[0]
        node_paragraph.alignment = PP_ALIGN.CENTER
        node_run = node_paragraph.add_run()
        node_run.text = str(index + 1)
        style_run(
            node_run,
            size=TIMELINE_NODE_SIZE_PT,
            color=rgb(palette, TITLE_TEXT_COLOR),
            bold=True,
            italic=False,
            font_name=TITLE_FONT,
        )
        card = slide.add_shape(
            "ROUNDED_RECTANGLE",
            x=in_(centre - plan.card_width_in / 2.0),
            y=in_(TIMELINE_CARD_TOP_IN),
            width=in_(plan.card_width_in),
            height=in_(plan.card_height_in),
            fill_color=css_colour(palette, SLOT_BOX_COLOR),
        )
        card.name = (
            SLOT_SHAPE_PREFIX + frame.id
            if index == 0
            else f"{NARRATION_CARD_SHAPE_PREFIX}{frame.id}#{index}"
        )
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
        card_frame = card.text_frame
        card_frame.word_wrap = True
        card_frame.vertical_anchor = MSO_ANCHOR.TOP
        padding = Emu(int(TIMELINE_CARD_PADDING_IN * EMU_PER_INCH))
        card_frame.margin_left = padding
        card_frame.margin_right = padding
        card_frame.margin_top = padding
        card_frame.margin_bottom = padding
        _write_milestone(
            card,
            point,
            size=Pt(plan.size_pt),
            color=rgb(palette, SLOT_TEXT_COLOR),
            font_name=BODY_FONT,
        )


def add_timeline_slide(
    presentation: Presentation, frame: SlotFrame, palette: dict[str, str], sky_path: Path,
) -> Slide:
    """Draw a frame as a horizontal timeline of milestones.

    WHY: the owner asked for the overall progress of the research to be read
    as five phases on one row, so the phase that the work has reached is seen
    at a glance instead of being read out of a list.

    Args:
        presentation: The deck being built.
        frame: The frame to draw.
        palette: The colour name to hexadecimal string map.
        sky_path: The sky picture used as the background.

    Returns:
        The slide that was drawn.
    """
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)
    _add_frame_header(slide, frame, palette)
    plan = _plan_timeline(frame, BODY_FONT, TIMELINE_COLUMNS)
    _add_timeline_cards(slide, frame, palette, plan)
    footer = add_text_box(
        slide, MARGIN_X_IN, FOOTER_TOP_IN, CONTENT_WIDTH_IN, 0.30,
        [_footer_text(frame)], size=FOOTER_TEXT_SIZE,
        color=css_colour(palette, FOOTER_TEXT_COLOR), bold=False, italic=False,
    )
    footer.name = NAME_SLOT_FOOTER
    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide, palette,
        seed=SPARKLE_SEED_PLACEHOLDER + sum(ord(character) for character in frame.id),
        zones=((MARGIN_X_IN, 1.42, CONTENT_WIDTH_IN, 0.42),),
        avoid=((MARGIN_X_IN, FILLED_CARD_TOP_IN, CONTENT_WIDTH_IN, FILLED_CARD_HEIGHT_IN), swatch),
        maximum=6,
    )
    return slide


def _plan_pill_list(frame: SlotFrame, family: str) -> PillListPlan:
    """Measure a vertical list of pills.

    WHY: the pills share the content area equally, so the height of every
    pill is known before anything is drawn and the labels can be measured
    against it. The type size is stepped down until every label fits the
    height of its pill, because a label that overflows its pill is worse
    than a label that is one step smaller.

    Args:
        frame: The frame whose body is measured.
        family: The face the labels are drawn in.

    Returns:
        The measured plan: the labels, the type size, the width of the
        label inside a pill, the height of every pill and the top of the
        first pill.

    Raises:
        ScaffoldError: When the frame carries no point at all.

    """
    points = tuple(_narration_points(frame))
    if len(points) == 0:
        failure_reason = f"frame '{frame.id}' is drawn as a list of pills but carries no point"
        raise ScaffoldError(failure_reason)
    label_width = (
        CONTENT_WIDTH_IN
        - 2.0 * PILL_LIST_PADDING_IN
        - PILL_LIST_NUMBER_SIZE_IN
        - PILL_LIST_NUMBER_GAP_IN
    )
    measured_width = label_width * FILLED_MEASURE_WIDTH_FACTOR
    gaps = PILL_LIST_GAP_IN * max(0, len(points) - 1)
    pill_height = (PILL_LIST_BOTTOM_IN - PILL_LIST_TOP_IN - gaps) / len(points)
    size = PILL_LIST_SIZE.pt
    needed = 0.0
    while size >= PILL_LIST_MIN_SIZE_PT - 1e-9:
        lines = max(wrap_line_count(point, family, size, measured_width) for point in points)
        needed = (
            lines * line_height_inches(family, size) * TIMELINE_LINE_SPACING
            + 2.0 * PILL_LIST_PADDING_IN
        )
        if needed <= pill_height:
            return PillListPlan(
                points=points,
                size_pt=size,
                label_width_in=label_width,
                pill_height_in=pill_height,
                band_top_in=PILL_LIST_TOP_IN,
            )
        size -= PILL_LIST_SIZE_STEP_PT
    failure_reason = (
        f"the labels of frame '{frame.id}' need {needed:.2f} inches at the smallest type size "
        f"of {PILL_LIST_MIN_SIZE_PT} pt, but a pill is only {pill_height:.2f} inches tall"
    )
    raise ScaffoldError(failure_reason)


def _remove_pill_list_numbers(slide: Slide) -> None:
    """Remove the numbered discs of a list of pills.

    WHY: the discs are drawn separately from the pills, so a list that is
    drawn again would leave the old discs behind and the numbers would sit
    on top of each other.

    Args:
        slide: The slide the discs sit on.

    """
    for raw_shape in list(slide.shapes):
        shape: Shape = raw_shape
        if shape.name.startswith(NAME_PILL_LIST_NUMBER):
            element = shape._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)


def _remove_timeline_chrome(slide: Slide) -> None:
    """Remove the axis and the milestone discs of a timeline.

    WHY: the axis and the discs are drawn apart from the milestone cards, so
    a timeline that is drawn again without removing them would leave a second
    copy of each at the same coordinates and the slide would carry two axes
    and two discs per milestone.

    Args:
        slide: The slide the chrome sits on.

    """
    for raw_shape in list(slide.shapes):
        shape: Shape = raw_shape
        if shape.name == NAME_TIMELINE_AXIS or shape.name.startswith(NAME_TIMELINE_NODE):
            element = shape._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)


def _add_pill_list(
    slide: Slide, frame: SlotFrame, palette: dict[str, str], plan: PillListPlan,
) -> None:
    """Draw a vertical list of pills, one for every point of the body.

    WHY: the owner asked for the issues to be listed as pills, so the list is
    read before the issues are elaborated. The first pill carries the name
    that identifies the frame and the other pills carry that name with an
    order number, so the whole list is found, read and replaced as one
    thing, exactly like the narration band of a filled frame. The number of
    every issue sits in a disc on the left of its pill, which links the list
    to the slide that elaborates the same issue.

    Args:
        slide: The slide to draw on.
        frame: The frame whose points are drawn.
        palette: The colour name to hexadecimal string map.
        plan: The measured layout of the list.

    """
    for index, point in enumerate(plan.points):
        pill_top = plan.band_top_in + index * (plan.pill_height_in + PILL_LIST_GAP_IN)
        pill = slide.add_shape(
            "ROUNDED_RECTANGLE",
            x=in_(MARGIN_X_IN),
            y=in_(pill_top),
            width=in_(CONTENT_WIDTH_IN),
            height=in_(plan.pill_height_in),
            fill_color=css_colour(palette, SLOT_BOX_COLOR),
        )
        pill.name = (
            SLOT_SHAPE_PREFIX + frame.id
            if index == 0
            else f"{NARRATION_CARD_SHAPE_PREFIX}{frame.id}#{index}"
        )
        _set_corner_radius(pill, plan.pill_height_in / 2.0)
        _glass_shape(
            pill,
            fill=rgb(palette, SLOT_BOX_COLOR),
            fill_opacity=GLASS_FILL_OPACITY,
            edge=rgb(palette, FROST_EDGE_COLOR),
            edge_opacity=GLASS_EDGE_OPACITY,
            edge_width_pt=GLASS_EDGE_WIDTH_PT,
            shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
            shadow_opacity=GLASS_SHADOW_OPACITY,
        )
        pill_frame = pill.text_frame
        pill_frame.word_wrap = True
        pill_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        padding = Emu(int(PILL_LIST_PADDING_IN * EMU_PER_INCH))
        pill_frame.margin_left = Emu(
            int((PILL_LIST_PADDING_IN + PILL_LIST_NUMBER_SIZE_IN + PILL_LIST_NUMBER_GAP_IN)
                * EMU_PER_INCH),
        )
        pill_frame.margin_right = padding
        pill_frame.margin_top = padding
        pill_frame.margin_bottom = padding
        pill_paragraph = pill_frame.paragraphs[0]
        pill_paragraph.alignment = PP_ALIGN.CENTER
        pill_run = pill_paragraph.add_run()
        pill_run.text = point
        style_run(
            pill_run,
            size=Pt(plan.size_pt),
            color=rgb(palette, TITLE_TEXT_COLOR),
            bold=True,
            italic=False,
            font_name=TITLE_FONT,
        )
        number = slide.add_shape(
            "OVAL",
            x=in_(MARGIN_X_IN + PILL_LIST_PADDING_IN),
            y=in_(pill_top + (plan.pill_height_in - PILL_LIST_NUMBER_SIZE_IN) / 2.0),
            width=in_(PILL_LIST_NUMBER_SIZE_IN),
            height=in_(PILL_LIST_NUMBER_SIZE_IN),
            fill_color=css_colour(palette, TITLE_BAND_COLOR),
        )
        number.name = f"{NAME_PILL_LIST_NUMBER}{frame.id}_{index}"
        _glass_shape(
            number,
            fill=rgb(palette, TITLE_BAND_COLOR),
            fill_opacity=GLASS_BAND_OPACITY,
            edge=rgb(palette, ACCENT_COLOR),
            edge_opacity=1.0,
            edge_width_pt=1.25,
            shadow_colour=rgb(palette, NAVY_DEEP_COLOR),
            shadow_opacity=GLASS_SHADOW_OPACITY,
        )
        number_frame = number.text_frame
        number_frame.word_wrap = False
        number_frame.margin_left = Emu(0)
        number_frame.margin_right = Emu(0)
        number_frame.margin_top = Emu(0)
        number_frame.margin_bottom = Emu(0)
        number_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        number_paragraph = number_frame.paragraphs[0]
        number_paragraph.alignment = PP_ALIGN.CENTER
        number_run = number_paragraph.add_run()
        number_run.text = str(index + 1)
        style_run(
            number_run,
            size=PILL_LIST_NUMBER_SIZE_PT,
            color=rgb(palette, TITLE_TEXT_COLOR),
            bold=True,
            italic=False,
            font_name=TITLE_FONT,
        )


def add_pill_list_slide(
    presentation: Presentation, frame: SlotFrame, palette: dict[str, str], sky_path: Path,
) -> Slide:
    """Draw a frame as a vertical list of pills.

    WHY: the owner asked for the previous issues to be listed on one slide
    before each of them is elaborated, so the list is the frame that carries
    the names of the issues and nothing else.

    Args:
        presentation: The deck being built.
        frame: The frame to draw.
        palette: The colour name to hexadecimal string map.
        sky_path: The sky picture used as the background.

    Returns:
        The slide that was drawn.
    """
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)
    _add_frame_header(slide, frame, palette)
    plan = _plan_pill_list(frame, BODY_FONT)
    _add_pill_list(slide, frame, palette, plan)
    footer = add_text_box(
        slide, MARGIN_X_IN, FOOTER_TOP_IN, CONTENT_WIDTH_IN, 0.30,
        [_footer_text(frame)], size=FOOTER_TEXT_SIZE,
        color=css_colour(palette, FOOTER_TEXT_COLOR), bold=False, italic=False,
    )
    footer.name = NAME_SLOT_FOOTER
    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide, palette,
        seed=SPARKLE_SEED_PLACEHOLDER + sum(ord(character) for character in frame.id),
        zones=((MARGIN_X_IN, 1.42, CONTENT_WIDTH_IN, 0.42),),
        avoid=(
            (MARGIN_X_IN, PILL_LIST_TOP_IN, CONTENT_WIDTH_IN, PILL_LIST_BOTTOM_IN - PILL_LIST_TOP_IN),
            swatch,
        ),
        maximum=6,
    )
    return slide


def _card_rows(
    points: tuple[str, ...], family: str, size: float, measured_width: float, columns: int,
) -> tuple[tuple[float, ...], float]:
    """Measure the rows of a band of cards.

    WHY: the height of a row is the height of its tallest card, and the
    height of the band is the sum of the rows and the gaps between them.
    Every card carries a heading and a detail, so both are measured.

    Args:
        points: The texts of the cards, in order.
        family: The face the cards are drawn in.
        size: The type size the cards are drawn at.
        measured_width: The width the text is measured against in inches.
        columns: How many cards sit in one row.

    Returns:
        The height of every row in inches and the height of the band.

    """
    heights: list[float] = []
    for start in range(0, len(points), columns):
        row_points = points[start : start + columns]
        row_lines = 0
        for point in row_points:
            label, detail = _split_milestone(point)
            card_lines = wrap_line_count(label, family, size, measured_width)
            if len(detail) != 0:
                card_lines += wrap_line_count(detail, family, size, measured_width)
            # WHY: the row is as tall as its tallest card, so the lines of the
            # cards of a row are compared and not added up.
            row_lines = max(row_lines, card_lines)
        heights.append(
            row_lines * line_height_inches(family, size) * TIMELINE_LINE_SPACING
            + 2.0 * CARDS_ONLY_CARD_PADDING_IN,
        )
    band = sum(heights) + FILLED_CARD_GAP_IN * max(0, len(heights) - 1)
    return tuple(heights), band


def _plan_cards_only(frame: SlotFrame, family: str, columns: int) -> CardsOnlyPlan:
    """Measure a band of cards that fills the content area.

    WHY: a frame that elaborates an issue carries no graphic, so its cards
    take the whole content area and the text sits in the middle of a card
    that is taller than the text needs. A frame that does carry a graphic
    keeps the panel of the graphic above the cards, exactly like a filled
    frame, so the two never disagree about how much room the cards get.

    Args:
        frame: The frame whose body is measured.
        family: The face the cards are drawn in.
        columns: How many cards sit in one row.

    Returns:
        The measured plan: the texts, the type size, the number of columns,
        the width of a card, the width of the text inside a card, the height
        of every row, the top and the height of the band and the height of
        the figure panel.

    Raises:
        ScaffoldError: When the frame carries no point at all, or when even
            the smallest type size does not fit.

    """
    points = tuple(_narration_points(frame))
    if len(points) == 0:
        failure_reason = f"frame '{frame.id}' is drawn as a band of cards but carries no point"
        raise ScaffoldError(failure_reason)
    card_width = (CONTENT_WIDTH_IN - FILLED_CARD_GAP_IN * (columns - 1)) / columns
    text_width = (
        card_width - 2.0 * CARDS_ONLY_CARD_PADDING_IN - CARDS_ONLY_TEXT_GAP_IN
    )
    measured_width = text_width * CARDS_ONLY_MEASURE_WIDTH_FACTOR
    rows = (len(points) + columns - 1) // columns
    size = CARDS_ONLY_SIZE.pt
    band_height = 0.0
    while size >= CARDS_ONLY_MIN_SIZE_PT - 1e-9:
        row_heights, band_height = _card_rows(points, family, size, measured_width, columns)
        if frame.figure is not None:
            if band_height <= FILLED_BAND_MAX_IN:
                panel_height = FILLED_CARD_HEIGHT_IN - band_height - FILLED_FIGURE_GAP_IN
                if panel_height > 0.0:
                    return CardsOnlyPlan(
                        points=points,
                        size_pt=size,
                        columns=columns,
                        card_width_in=card_width,
                        text_width_in=text_width,
                        row_heights=row_heights,
                        band_top_in=FILLED_CARD_TOP_IN + panel_height + FILLED_FIGURE_GAP_IN,
                        band_height_in=band_height,
                        figure_panel_height_in=panel_height,
                    )
        else:
            gaps = FILLED_CARD_GAP_IN * max(0, rows - 1)
            available = FILLED_CARD_HEIGHT_IN - gaps
            if band_height <= available:
                row_height = available / rows
                return CardsOnlyPlan(
                    points=points,
                    size_pt=size,
                    columns=columns,
                    card_width_in=card_width,
                    text_width_in=text_width,
                    row_heights=tuple(row_height for _ in range(rows)),
                    band_top_in=FILLED_CARD_TOP_IN,
                    band_height_in=available + gaps,
                    figure_panel_height_in=0.0,
                )
        size -= CARDS_ONLY_SIZE_STEP_PT
    failure_reason = (
        f"the cards of frame '{frame.id}' need {band_height:.2f} inches at the smallest type size "
        f"of {CARDS_ONLY_MIN_SIZE_PT} pt, but the content area is only {FILLED_CARD_HEIGHT_IN} "
        "inches tall"
    )
    raise ScaffoldError(failure_reason)


def _remove_cards_only_panels(slide: Slide) -> None:
    """Remove the glass cards of a band of cards from their slide.

    WHY: the narration of a band lives in a text box inside the card, so a
    band that is drawn again leaves the old cards behind and the new cards
    would sit on top of them.

    Args:
        slide: The slide the cards sit on.

    """
    for raw_shape in list(slide.shapes):
        shape: Shape = raw_shape
        if shape.name.startswith(CARDS_ONLY_PANEL_PREFIX):
            element = shape._element  # ruff: ignore[private-member-access]
            element.getparent().remove(element)


def _add_cards_only(
    slide: Slide, frame: SlotFrame, palette: dict[str, str], plan: CardsOnlyPlan,
) -> None:
    """Draw the band of cards of a frame.

    WHY: the first card carries the name that identifies the frame and the
    other cards carry that name with an order number, so the whole band is
    found, read and replaced as one thing, exactly like the narration band
    of a filled frame.

    Args:
        slide: The slide to draw on.
        frame: The frame whose points are drawn.
        palette: The colour name to hexadecimal string map.
        plan: The measured layout of the band.

    """
    if plan.figure_panel_height_in > 0.0:
        _add_figure_panel(slide, frame, palette, plan.figure_panel_height_in)
    row_top = plan.band_top_in
    index = 0
    for row_height in plan.row_heights:
        for column in range(plan.columns):
            if index >= len(plan.points):
                break
            point = plan.points[index]
            left = MARGIN_X_IN + column * (plan.card_width_in + FILLED_CARD_GAP_IN)
            card = slide.add_shape(
                "ROUNDED_RECTANGLE",
                x=in_(left),
                y=in_(row_top),
                width=in_(plan.card_width_in),
                height=in_(row_height),
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
                left + CARDS_ONLY_CARD_PADDING_IN,
                row_top,
                plan.text_width_in,
                row_height,
                [""],
                size=Pt(plan.size_pt),
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
                point,
                size=Pt(plan.size_pt),
                color=rgb(palette, SLOT_TEXT_COLOR),
                font_name=BODY_FONT,
            )
            index += 1
        row_top += row_height + FILLED_CARD_GAP_IN


def add_cards_only_slide(
    presentation: Presentation, frame: SlotFrame, palette: dict[str, str], sky_path: Path,
) -> Slide:
    """Draw a frame as a band of cards that fills the content area.

    WHY: the owner asked for one slide per previous issue that explains what
    the issue was, and those slides carry a heading and a detail for every
    part of the issue.

    Args:
        presentation: The deck being built.
        frame: The frame to draw.
        palette: The colour name to hexadecimal string map.
        sky_path: The sky picture used as the background.

    Returns:
        The slide that was drawn.
    """
    slide = add_blank_slide(presentation)
    _set_sky_background(slide, sky_path)
    _add_frame_header(slide, frame, palette)
    plan = _plan_cards_only(frame, BODY_FONT, CARDS_ONLY_COLUMNS)
    _add_cards_only(slide, frame, palette, plan)
    footer = add_text_box(
        slide, MARGIN_X_IN, FOOTER_TOP_IN, CONTENT_WIDTH_IN, 0.30,
        [_footer_text(frame)], size=FOOTER_TEXT_SIZE,
        color=css_colour(palette, FOOTER_TEXT_COLOR), bold=False, italic=False,
    )
    footer.name = NAME_SLOT_FOOTER
    swatch = _add_palette_swatch(slide, palette)
    _ = _add_sparkles(
        slide, palette,
        seed=SPARKLE_SEED_PLACEHOLDER + sum(ord(character) for character in frame.id),
        zones=((MARGIN_X_IN, 1.42, CONTENT_WIDTH_IN, 0.42),),
        avoid=((MARGIN_X_IN, FILLED_CARD_TOP_IN, CONTENT_WIDTH_IN, FILLED_CARD_HEIGHT_IN), swatch),
        maximum=6,
    )
    return slide


def _build_frame_slide(
    presentation: Presentation,
    frame: SlotFrame,
    palette: dict[str, str],
    sky_path: Path,
) -> Slide:
    """Draw the slide of one frame, filled or empty.

    WHY: a frame that carries a graphic is drawn with the two column
    layout and a frame that does not is drawn as an empty slot. The choice
    lives in one place, so the two layouts can never disagree about which
    one a frame gets.

    Args:
        presentation: The deck being built.
        frame: The frame to draw.
        palette: The colour name to hexadecimal string map.
        sky_path: The sky picture used as the background.

    Returns:
        The slide that was drawn.
    """
    if frame.pill_list:
        return add_pill_list_slide(presentation, frame, palette, sky_path)
    if frame.cards_only:
        return add_cards_only_slide(presentation, frame, palette, sky_path)
    if frame.timeline:
        return add_timeline_slide(presentation, frame, palette, sky_path)
    if frame.figure is not None:
        return add_filled_slide(presentation, frame, palette, sky_path)
    return add_placeholder_slide(presentation, frame, palette, sky_path)


def _refresh_figures_in_place(
    presentation: Presentation,
    scaffold: Scaffold,
    palette: dict[str, str],
) -> int:
    """Give every frame that carries a graphic its panel on the existing slide.

    WHY: update mode never rebuilds a slide the owner may have edited, so a
    frame that gains a graphic after the deck was written would otherwise
    keep its empty slot. The panel is added to the slide that is already
    there; the narration is left alone, because the owner may have written
    into it.

    Args:
        presentation: The deck being updated.
        scaffold: The specification the deck must agree with.
        palette: The colour name to hexadecimal string map.

    Returns:
        The number of graphic panels that were added.
    """
    slides = list(presentation.slides)
    added = 0
    for frame in scaffold.frames:
        if frame.figure is None:
            continue
        host = None
        for slide in slides:
            if _find_shape_by_name(slide, SLOT_SHAPE_PREFIX + frame.id) is not None:
                host = slide
                break
            if _find_shape_by_name(slide, FIGURE_SHAPE_PREFIX + frame.id) is not None:
                host = slide
                break
        if host is None:
            continue
        if _find_shape_by_name(host, FIGURE_SHAPE_PREFIX + frame.id) is not None:
            continue
        plan = _plan_narration_cards(frame, BODY_FONT, FILLED_BAND_COLUMNS)
        _add_figure_panel(host, frame, palette, plan.figure_panel_height_in)
        added += 1
    return added


def _verify_frame_graphics(path: Path, scaffold: Scaffold) -> int:
    """Check that every frame with a graphic carries its panel and caption.

    WHY: a filled frame is only filled when the graphic is really on the
    slide, so the check is made on the written file and not on the
    specification.

    Args:
        path: The written deck.
        scaffold: The specification the deck must agree with.

    Returns:
        The number of graphic panels that were found.

    Raises:
        ScaffoldError: When a frame with a graphic has no panel, or when its
            caption is not on the slide.
    """
    presentation = Presentation.open(str(path))
    slides = list(presentation.slides)
    hosts: dict[str, Slide] = {}
    known_ids = frozenset(frame.id for frame in scaffold.frames)
    for slide in slides:
        for shape in slide.shapes:
            name = shape.name or ""
            frame_id = _frame_id_of_shape(name, known_ids)
            if frame_id is not None:
                hosts[frame_id] = slide
    placed = 0
    for frame in scaffold.frames:
        if frame.figure is None:
            continue
        host = hosts.get(frame.id)
        if host is None:
            failure_reason = (f"the deck is missing the frame '{frame.id}'")
            raise ScaffoldError(failure_reason)
        if _find_shape_by_name(host, FIGURE_SHAPE_PREFIX + frame.id) is None:
            failure_reason = (f"the deck is missing the graphic panel of frame '{frame.id}'")
            raise ScaffoldError(failure_reason)
        caption = _find_shape_by_name(host, NAME_FIGURE_CAPTION)
        if caption is None:
            failure_reason = (f"the deck is missing the graphic caption of frame '{frame.id}'")
            raise ScaffoldError(failure_reason)
        # WHY: the caption of a figure frame stands in several paragraphs, and
        # the text of a shape is read with its whitespace collapsed, so the two
        # are compared in the same normalised form.
        if collapse_whitespace(frame.figure.caption) not in _shape_text(caption):
            failure_reason = (
                f"the graphic caption of frame '{frame.id}' does not carry "
                "the caption of the specification"
            )
            raise ScaffoldError(failure_reason)
        placed += 1
    return placed


def apply_powerpoint_sections(presentation: Presentation, groups: Sequence[tuple[str, Sequence[int]]]) -> None:
    """Write the owner blocks as real PowerPoint sections.

    WHY: EasyPPTX has no section API, so the p14 extension is written into the
    presentation part directly. The escape hatch is the documented
    presentation.pptx_presentation attribute, which is the python-pptx object
    EasyPPTX itself drives.

    Args:
        presentation: The deck whose PowerPoint section list is written.
        groups: The owner block names, each with the slide indices it owns.

    Raises:
        ScaffoldError: When the deck has no slides, when a group owns no slide,
            or when a slide index points outside the deck.
    """
    native = presentation.pptx_presentation
    # WHY: the ordered list of slide identifiers is private in python-pptx,
    # and it is the only place that holds the order PowerPoint will show.
    entries = list(native.slides._sldIdLst)  # ruff: ignore[private-member-access]
    if len(entries) == 0:
        failure_reason = ("the deck carries no slides, so no section can be written")
        raise ScaffoldError(failure_reason)
    parts = []
    for name, indices in groups:
        if len(indices) == 0:
            failure_reason = (f"the section {name!r} was given no slides")
            raise ScaffoldError(failure_reason)
        items = []
        for index in indices:
            if index < 0 or index >= len(entries):
                failure_reason = (f"the section {name!r} refers to slide {index}, "
                    f"but the deck only has {len(entries)} slides")
                raise ScaffoldError(failure_reason)
            identifier: str | None = entries[index].get("id")
            relationship: str | None = entries[index].get(f"{{{R_NS}}}id")
            if identifier is None or relationship is None:
                failure_reason = (f"slide {index} of the section {name!r} carries no slide identifier")
                raise ScaffoldError(failure_reason)
            items.append(f'<p14:sldId id="{identifier}" r:id="{relationship}"/>')
        parts.append(
            f'<p14:section name="{escape_xml(name)}" id="{_new_guid()}">'
            f'<p14:sldIdLst>{"".join(items)}</p14:sldIdLst></p14:section>',
        )
    fragment: _Element = etree.fromstring(
        f'<p14:sectionLst xmlns:p14="{P14_NS}" xmlns:r="{R_NS}">{"".join(parts)}</p14:sectionLst>',
    )
    # WHY: the presentation element is private in python-pptx; the section
    # list has to be appended to it, and the extension schema has no other
    # entry point.
    element = native.part._element  # ruff: ignore[private-member-access]
    ext_list: _Element | None = element.find(qn("p:extLst"))
    if ext_list is None:
        ext_list = etree.SubElement(element, qn("p:extLst"))
    for extension in list(ext_list):
        if extension.get("uri") == SECTION_EXTENSION_URI:
            ext_list.remove(extension)
    extension: _Element = etree.SubElement(ext_list, qn("p:ext"))
    extension.set("uri", SECTION_EXTENSION_URI)
    extension.append(fragment)
    etree.cleanup_namespaces(
        element,
        top_nsmap={
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "r": R_NS,
            "p": P_NS,
            "p14": P14_NS,
            "mc": MC_NS,
        },
        keep_ns_prefixes=["a", "r", "p", "p14", "mc"],
    )
    element.set(f"{{{MC_NS}}}Ignorable", "p14")


def _recorded_body(slide: Slide, frame: SlotFrame) -> str | None:
    """Return the body that the tool recorded for a frame, or None.

    WHY: the recorded body is the provenance of the slot. When the visible text
    still equals the recorded body the owner has not touched the slot, so the
    tool may refresh it. When the two differ the owner has written their own
    narration, and that text must survive.

    Args:
        slide: The slide whose speaker notes are read.
        frame: The frame whose recorded body is looked up.

    Returns:
        The body recorded when the tool last wrote the slide, or None.

    WHY: the record is returned with its line structure intact. A filled
    body is written as one bullet per line, and the comparison that decides
    whether a slot is still the one this tool wrote has to see those lines
    one by one. Collapsing them here would leave the bullet markers of the
    later lines in the middle of one line, and every filled slot would
    look as if the owner had edited it.
    """
    try:
        notes = slide.notes if slide.notes is not None else ""
    except (AttributeError, KeyError, ValueError):
        notes = ""
    start = SLOT_BODY_MARKER_START.format(id=frame.id)
    if start in notes:
        remainder = notes.split(start, 1)[1]
        if SLOT_BODY_MARKER_END in remainder:
            return remainder.split(SLOT_BODY_MARKER_END, 1)[0]
    if LEGACY_BODY_PREFIX in notes:
        tail = notes.split(LEGACY_BODY_PREFIX, 1)[1]
        return tail.split(LEGACY_BODY_SUFFIX, 1)[0]
    return None


def _write_notes(slide: Slide, frame: SlotFrame, body: str) -> None:
    """Record the provenance of a frame in the speaker notes.

    WHY: the notes are the only place the tool can keep what it wrote, so
    the next run can tell an untouched slot from one the owner has edited.
    The body is recorded between two markers, and the graphic of a filled
    frame is recorded with markers of its own.

    Args:
        slide: The slide whose notes are written.
        frame: The frame the slide carries.
        body: The body the tool wrote into the slot.

    """
    lines = [
        (
            "PLACEHOLDER SLIDE. The slot is unfilled on purpose. "
            f"It must eventually carry: {body}"
        ),
        f"Owner block: {frame.section}",
        f"Frame id: {frame.id}",
        f"{SLOT_BODY_MARKER_START.format(id=frame.id)}",
        body,
        SLOT_BODY_MARKER_END,
    ]
    if frame.figure is not None:
        lines.extend(
            [
                f"{FIGURE_MARKER_START.format(id=frame.id)}",
                f"path: {frame.figure.path}",
                f"caption: {frame.figure.caption}",
                f"source: {frame.figure.source}",
                FIGURE_MARKER_END,
            ],
        )
    slide.notes = "\n".join(lines)


def _strip_bullet(line: str) -> str:
    """Remove the leading bullet marker of one narration line.

    Args:
        line: One line of a narration body.

    Returns:
        The line without its bullet marker.
    """
    stripped = line.strip()
    for marker in ("- ", "* ", "\u2022 "):
        if stripped.startswith(marker):
            return stripped.removeprefix(marker)
    return stripped


def _has_bullets(text: str) -> bool:
    """Report whether a text carries bullet markers on its lines.

    Args:
        text: The text to inspect.

    Returns:
        True when at least one line starts with a bullet marker.
    """
    return any(_strip_bullet(line) != line.strip() for line in text.splitlines())


def _normalise_body(text: str) -> str:
    """Normalise a narration body so that two spellings of it compare equal.

    WHY: the specification writes a filled body as bullet lines and the
    slide draws the same lines with a bullet glyph. The comparison that
    decides whether a slot is still the one this tool wrote, and the check
    that the deck agrees with the specification, must ignore that
    decoration.

    Args:
        text: A body, from the specification or from the slide.

    Returns:
        The body with the bullet markers removed and the whitespace
        collapsed.
    """
    joined = " ".join(_strip_bullet(line) for line in text.splitlines())
    return collapse_whitespace(joined.replace(BULLET_GLYPH, " "))


def _set_hanging_indent(paragraph: _Paragraph) -> None:
    """Hang the wrapped lines of a bulleted paragraph under its text.

    WHY: python-pptx exposes no public way to set the indent of a
    paragraph, but the DrawingML attributes marL and indent are the
    documented way to hang the second and later lines of a bulleted
    paragraph under the text of the first one. Without them a wrapped line
    runs back under the bullet glyph.

    Args:
        paragraph: The paragraph to indent.

    """
    indent = int(FILLED_BULLET_INDENT_IN * EMU_PER_INCH)
    properties = paragraph._p.get_or_add_pPr()  # ruff: ignore[private-member-access]
    properties.set("marL", str(indent))
    properties.set("indent", str(-indent))


def _write_bullets(
    shape: Shape,
    body: str,
    *,
    size: Length,
    color: RGBColor,
    bold: bool = False,
    italic: bool = False,
    font_name: str = BODY_FONT,
) -> None:
    """Draw a narration body as one bulleted paragraph per line.

    WHY: a filled body is written in the specification as one bullet per
    line, and a line that is drawn as one long paragraph is unreadable.
    The face is named explicitly because the height of every card is
    measured with that face, and a substituted face of a different width
    would overflow the card.

    Args:
        shape: The shape that carries the narration.
        body: The body text, one bullet per line.
        size: The type size of the narration.
        color: The type colour of the narration.
        bold: Whether the narration is bold.
        italic: Whether the narration is italic.
        font_name: The face the narration is drawn in.

    """
    text_frame = shape.text_frame
    text_frame.clear()
    lines = [line for line in body.splitlines() if len(line.strip()) != 0]
    for index, line in enumerate(lines):
        paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
        paragraph.alignment = PP_ALIGN.LEFT
        paragraph.line_spacing = FILLED_NARRATION_LINE_SPACING
        _set_hanging_indent(paragraph)
        run = paragraph.add_run()
        run.text = f"{BULLET_GLYPH} {_strip_bullet(line)}"
        style_run(run, size=size, color=color, bold=bold, italic=italic, font_name=font_name)


def _frame_id_of_shape(name: str, known_ids: frozenset[str]) -> str | None:
    """Return the frame a shape anchors, when the shape belongs to a frame.

    WHY: a frame that carries narration is anchored by its slot box, and a
    frame that carries only a graphic is anchored by its figure panel. The
    two kinds of frame are found the same way, so the ownership of a slide
    is resolved in one place instead of twice.

    Args:
        name: The name of the shape.
        known_ids: The identifiers of the frames of the specification.

    Returns:
        The frame identifier, or None when the shape anchors no frame.
    """
    for prefix in (SLOT_SHAPE_PREFIX, FIGURE_SHAPE_PREFIX):
        if not name.startswith(prefix):
            continue
        candidate = name[len(prefix) :]
        if candidate in known_ids:
            return candidate
    return None


def _find_shape_by_name(slide: Slide, name: str) -> Shape | None:
    """Return the shape called ``name`` on the slide, or None.

    Args:
        slide: The slide to inspect.
        name: The shape name to look for.

    Returns:
        The shape, or None when the slide does not carry it.
    """
    for raw_shape in slide.shapes:
        shape: Shape = raw_shape
        if shape.name == name:
            return shape
    return None


def _shape_text(shape: Shape | None) -> str:
    """Return the normalised text of a shape.

    Args:
        shape: The shape to read.

    Returns:
        The collapsed text, or an empty string when the shape has no text.
    """
    if shape is None or not shape.has_text_frame:
        return ""
    return collapse_whitespace(shape.text_frame.text)


def _find_title_shape(slide: Slide, title: str) -> Shape | None:
    """Return the frame title shape of the slide, or None.

    The shape named ``frame_title`` wins. When it is absent, any shape whose
    text equals the frame title is accepted, which lets a deck built by an
    earlier version of this tool be recognised.

    Args:
        slide: The slide to inspect.
        title: The frame title to look for.

    Returns:
        The shape, or None.
    """
    named = _find_shape_by_name(slide, NAME_FRAME_TITLE)
    if named is not None:
        return named
    wanted = collapse_whitespace(title)
    for raw_shape in slide.shapes:
        shape: Shape = raw_shape
        if shape.has_text_frame and _shape_text(shape) == wanted:
            return shape
    return None


def _find_slot_shape(slide: Slide, frame: SlotFrame, palette: dict[str, str]) -> tuple[Shape | None, str]:
    """Find the slot box of a frame on a slide.

    WHY THE FALLBACK: a deck written by an older version of this tool carries
    no machine name on the slot box, so the sand coloured box is adopted
    instead. A deck written by hand carries neither, and the frame is reported
    as missing so that update mode can create it.

    Args:
        slide: The slide that is searched.
        frame: The frame whose slot box is looked up.
        palette: Mapping of palette names to six digit hex strings.

    Returns:
        The slot shape and how it was found: 'named', 'adopted' or 'missing'.
    """
    named = _find_shape_by_name(slide, SLOT_SHAPE_PREFIX + frame.id)
    if named is not None:
        return named, "named"
    target = rgb(palette, SLOT_BOX_COLOR)
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        if _shape_fill_rgb(shape) == target:
            return shape, "adopted"
    return None, "missing"


def _shape_fill_rgb(shape: Shape | None) -> RGBColor | None:
    """Return the fill colour of a shape, or None when it has no solid fill.

    Args:
        shape: The shape whose fill colour is read.

    Returns:
        The fill colour, or None when the shape has no solid fill.
    """
    if shape is None:
        return None
    try:
        return shape.fill.fore_color.rgb
    except (AttributeError, TypeError, ValueError):
        return None


def _set_shape_text(
    shape: Shape,
    text: str,
    *,
    size: Length,
    color: RGBColor,
    bold: bool,
    italic: bool,
) -> None:
    """Replace the words of a shape and keep its styling.

    WHY: the shape keeps its own geometry and colour, and only the words
    change. A body that carries bullet markers is drawn as a bulleted list
    instead of one run, because a filled frame is written as one bullet per
    line.

    Args:
        shape: The shape whose text is replaced.
        text: The new text.
        size: The type size.
        color: The type colour.
        bold: Whether the text is bold.
        italic: Whether the text is italic.

    """
    if _has_bullets(text):
        _write_bullets(shape, text, size=size, color=color, bold=bold, italic=italic)
        return
    text_frame = shape.text_frame
    paragraphs = list(text_frame.paragraphs)
    for extra in paragraphs[1:]:
        extra._p.getparent().remove(extra._p)  # ruff: ignore[private-member-access]
    runs = list(paragraphs[0].runs)
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)  # ruff: ignore[private-member-access]
    if len(runs) == 0:
        run = paragraphs[0].add_run()
        runs = [run]
    runs[0].text = text
    style_run(runs[0], size=size, color=color, bold=bold, italic=italic)


def _slide_id_of(slide: Slide) -> int | None:
    """Return the numeric slide identifier of a slide.

    WHY: EasyPPTX wraps every slide, and only the wrapped python-pptx slide
    carries the identifier, so both shapes of slide are supported here.

    Args:
        slide: The slide, either an EasyPPTX slide or a native python-pptx slide.

    Returns:
        The slide identifier, or None when it cannot be read.
    """
    raw_identifier: object = getattr(slide, "slide_id", None)
    if raw_identifier is None:
        raw_identifier = slide.pptx_slide.slide_id
    if not isinstance(raw_identifier, int):
        return None
    return raw_identifier


def _slide_index_by_id(deck: Presentation | Sequence[Slide], slide_id: int | None) -> int | None:
    """Return the position of a slide inside a deck.

    Args:
        deck: The deck, or the plain list of its slides.
        slide_id: The slide identifier to look for.

    Returns:
        The position of that slide, or None when it is not in the deck.
    """
    # The caller may hand in either the presentation itself or a plain list of
    # slides, so both shapes are accepted here.
    slides: list[Slide] = list(deck.slides) if isinstance(deck, Presentation) else list(deck)
    for index, slide in enumerate(slides):
        if _slide_id_of(slide) == slide_id:
            return index
    return None


def _move_slide(presentation: Presentation, slide: Slide, index: int) -> None:
    """Move a slide to a new position in the deck.

    WHY: python-pptx has no public API to reorder slides, so the slide
    identifier element is moved inside the slide list of the presentation.

    Args:
        presentation: The deck whose slide order is changed.
        slide: The slide to move.
        index: The position the slide must end up at.

    Raises:
        ScaffoldError: When the slide is not registered in the deck.
    """
    native = presentation.pptx_presentation
    # WHY: the ordered list of slide identifiers is private in python-pptx,
    # and it is the only place that holds the order PowerPoint will show.
    slide_list = native.slides._sldIdLst  # ruff: ignore[private-member-access]
    wanted = str(_slide_id_of(slide))
    for candidate in list(slide_list):
        if candidate.get("id") == wanted:
            slide_list.remove(candidate)
            position = max(0, min(index, len(slide_list)))
            slide_list.insert(position, candidate)
            return
    failure_reason = (f"slide {wanted} is not registered in the deck, so it cannot be moved")
    raise ScaffoldError(failure_reason)


def _inspect_package_parts(archive: zipfile.ZipFile, path: Path) -> tuple[list[str], int, _Element]:
    """Read the members of the package and parse every XML part.

    Args:
        archive: The opened package.
        path: The package path, used in the error messages.

    Returns:
        The member names, the number of XML parts parsed, and the parsed
        presentation part.

    Raises:
        ScaffoldError: When the package is damaged, when a required part is
        missing, or when a part is not well formed XML.
    """
    broken = archive.testzip()
    if broken is not None:
        failure_reason = (f"the package {path} is damaged at member '{broken}'")
        raise ScaffoldError(failure_reason)
    names = archive.namelist()
    if "[Content_Types].xml" not in names:
        failure_reason = (
            f"the package {path} has no [Content_Types].xml, "
            "so it is not an Office Open XML file"
        )
        raise ScaffoldError(failure_reason)
    parsed = 0
    for name in names:
        if not name.endswith((".xml", ".rels")):
            continue
        try:
            etree.fromstring(archive.read(name))
        except etree.XMLSyntaxError as exc:
            failure_reason = (f"the package part '{name}' in {path} is not well formed XML: {exc}")
            raise ScaffoldError(failure_reason) from exc
        parsed += 1
    if "ppt/presentation.xml" not in names:
        failure_reason = (f"the package {path} has no ppt/presentation.xml")
        raise ScaffoldError(failure_reason)
    presentation_tree: _Element = etree.fromstring(archive.read("ppt/presentation.xml"))
    return names, parsed, presentation_tree


def verify_package(path: Path) -> list[str]:
    """Check that the written package is a well formed Office Open XML file.

    Args:
        path: The package to check.

    Returns:
        The report lines describing what was checked.

    Raises:
        ScaffoldError: When the archive is damaged, a part is missing, a part
        does not parse, or the presentation structure is wrong.
    """
    if not path.exists():
        failure_reason = (f"the generated package does not exist: {path}")
        raise ScaffoldError(failure_reason)
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        failure_reason = (f"the package {path} is not a readable zip archive: {exc}")
        raise ScaffoldError(failure_reason) from exc
    with archive:
        names, parsed, presentation_tree = _inspect_package_parts(archive, path)

    _check_presentation_structure(presentation_tree)
    return [
        f"package: {len(names)} parts, {parsed} XML parts well formed",
        "package: the presentation structure passes the section and slide-size checks",
    ]


def _check_presentation_structure(tree: _Element) -> None:
    """Check the structure of ``ppt/presentation.xml``.

    Args:
        tree: The parsed presentation part.

    Raises:
        ScaffoldError: When there is more than one extension list, when the
            extension list holds something other than extensions, when the
            slide size is not 16:9, when a section identifier is not one
            brace-wrapped GUID, or when the section list points at a slide
            that does not exist.
    """
    extension_lists = tree.findall(qn("p:extLst"))
    if len(extension_lists) > 1:
        failure_reason = (f"the presentation carries {len(extension_lists)} extension lists, expected at most one")
        raise ScaffoldError(failure_reason)
    slide_size = tree.find(qn("p:sldSz"))
    if slide_size is None:
        failure_reason = ("the presentation has no p:sldSz element")
        raise ScaffoldError(failure_reason)
    slide_type = slide_size.get("type")
    if slide_type not in {None, "screen16x9"}:
        failure_reason = (f"the presentation declares the slide size type '{slide_type}', expected screen16x9")
        raise ScaffoldError(failure_reason)

    if not extension_lists:
        return
    extension_list = extension_lists[0]
    for child in extension_list:
        if child.tag != qn("p:ext"):
            failure_reason = (f"the extension list holds '{child.tag}', expected only p:ext children; "
                "a nested extension list corrupts the package")
            raise ScaffoldError(failure_reason)

    slide_relationships = {
        node.get(qn("r:id")) for node in tree.findall(f"{qn('p:sldIdLst')}/{qn('p:sldId')}")
    }
    for extension in extension_list.findall(qn("p:ext")):
        if extension.get("uri") != SECTION_EXTENSION_URI:
            continue
        section_list = extension.find(f"{{{P14_NS}}}sectionLst")
        if section_list is None:
            failure_reason = ("the section extension holds no p14:sectionLst")
            raise ScaffoldError(failure_reason)
        for section in section_list.findall(f"{{{P14_NS}}}section"):
            name = section.get("name")
            if not name:
                failure_reason = ("the section list holds a section without a name")
                raise ScaffoldError(failure_reason)
            identifier = section.get("id")
            if identifier is None:
                failure_reason = ("the section list holds a section without an identifier")
                raise ScaffoldError(failure_reason)
            # WHY: PowerPoint rejects the whole package when a section identifier
            # is not one single brace-wrapped GUID. A doubled brace pair looks
            # like a GUID to the eye but is not parseable, and the symptom is the
            # unhelpful "PowerPoint found a problem with content" repair prompt,
            # so the package is checked here before the file is ever handed out.
            try:
                canonical = "{" + str(uuid.UUID(identifier)).upper() + "}"
            except ValueError:
                failure_reason = (
                    f"the section '{name}' carries the identifier '{identifier}', "
                    "which is not one brace-wrapped GUID"
                )
                raise ScaffoldError(failure_reason) from None
            if canonical != identifier:
                failure_reason = (
                    f"the section '{name}' carries the identifier '{identifier}', expected '{canonical}'"
                )
                raise ScaffoldError(failure_reason)
            for slide in section.iter(f"{{{P14_NS}}}sldId"):
                relationship_id = slide.get(f"{{{R_NS}}}id")
                if relationship_id not in slide_relationships:
                    failure_reason = (
                        f"the section '{name}' points at '{relationship_id}', "
                        "which is not a slide of this deck"
                    )
                    raise ScaffoldError(failure_reason)


def verify_presentation(path: Path, scaffold: Scaffold, *, strict: bool) -> list[str]:
    """Re-open the written deck and check it against the specification.

    Args:
        path: The deck to check.
        scaffold: The specification the deck must agree with.
        strict: When true the deck must be exactly the generated deck, with
            every title and body identical to the specification. When false
            the deck may carry owner slides and owner written text, and only
            the managed frames are checked.

    Returns:
        The report lines describing what was checked.

    Raises:
        ScaffoldError: When the deck does not agree with the specification.
    """
    presentation = Presentation.open(str(path))
    slides = list(presentation.slides)

    managed: dict[str, int] = {}
    known_ids = frozenset(frame.id for frame in scaffold.frames)
    for index, slide in enumerate(slides):
        for shape in slide.shapes:
            name = shape.name
            frame_id = _frame_id_of_shape(name, known_ids)
            if frame_id is None:
                continue
            if frame_id in managed and managed[frame_id] != index:
                failure_reason = (
                    f"the frame '{frame_id}' appears on slide {managed[frame_id] + 1} "
                    f"and again on slide {index + 1}"
                )
                raise ScaffoldError(failure_reason)
            managed[frame_id] = index

    if strict:
        expected = 2 + len(scaffold.frames)
        if len(slides) != expected:
            failure_reason = (f"the deck has {len(slides)} slides but the specification describes {expected}")
            raise ScaffoldError(failure_reason)
        missing = [frame.id for frame in scaffold.frames if frame.id not in managed]
        if len(missing) > 0:
            failure_reason = (f"the deck is missing the frame(s): {', '.join(missing)}")
            raise ScaffoldError(failure_reason)
    else:
        missing = [frame.id for frame in scaffold.frames if frame.id not in managed]
        if len(missing) == len(scaffold.frames):
            failure_reason = ("the deck carries no managed frame at all, so there is nothing to update")
            raise ScaffoldError(failure_reason)

    matched_bodies = 0
    for frame in scaffold.frames:
        if frame.id not in managed:
            continue
        slide = slides[managed[frame.id]]
        cards = _collect_narration_shapes(slide, frame.id)
        body = _narration_text(cards)
        if len(body) == 0 and len(frame.body) > 0:
            failure_reason = (f"the slot of frame '{frame.id}' on slide {managed[frame.id] + 1} is empty")
            raise ScaffoldError(failure_reason)
        title = _shape_text(_find_shape_by_name(slide, NAME_FRAME_TITLE))
        if strict:
            if title != collapse_whitespace(frame.title):
                failure_reason = (
                    f"the frame '{frame.id}' shows the title '{title}' "
                    f"but the specification says '{frame.title}'"
                )
                raise ScaffoldError(failure_reason)
            if _normalise_body(body) != _normalise_body(frame.body):
                failure_reason = (
                    f"the frame '{frame.id}' shows the body '{body}' "
                    f"but the specification says '{frame.body}'"
                )
                raise ScaffoldError(failure_reason)
        if _normalise_body(body) == _normalise_body(frame.body):
            matched_bodies += 1

    cover = _find_shape_by_name(slides[0], NAME_COVER_TITLE) if len(slides) > 0 else None
    cover_parts = [_shape_text(cover)]
    for cover_name in (
        NAME_COVER_TITLE,
        NAME_COVER_SUBTITLE,
        NAME_COVER_AUTHOR,
        NAME_COVER_JUDUL,
        NAME_COVER_SUPERVISORS,
    ):
        cover_parts.extend([_shape_text(_find_shape_by_name(slides[0], cover_name))])
    cover_text = " ".join(part for part in cover_parts if len(part) != 0)
    if strict:
        for needle in ("StellarOrion", scaffold.identity.author, scaffold.identity.nim):
            if needle not in cover_text:
                failure_reason = (f"the cover slide does not carry '{needle}'")
                raise ScaffoldError(failure_reason)

    outline_text = ""
    for slide in slides:
        parts: list[str] = []
        for raw_shape in slide.shapes:
            shape: Shape = raw_shape
            if not shape.name.startswith(NAME_OUTLINE_PILL):
                continue
            parts.append(_shape_text(shape))
        if len(parts) != 0:
            outline_text = " ".join(parts)
            break
    if strict:
        for section in scaffold.sections:
            if section not in outline_text:
                failure_reason = (f"the outline slide does not list the owner block '{section}'")
                raise ScaffoldError(failure_reason)

    if strict:
        _ = _verify_frame_graphics(path, scaffold)
    return [
        f"deck: {len(slides)} slides, {len(managed)} of {len(scaffold.frames)} frames managed by this tool",
        f"deck: {matched_bodies} slot bodies agree with the specification",
    ]


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------


def save_atomically(presentation: Presentation, output: Path, scaffold: Scaffold, *, strict: bool) -> list[str]:
    """Write the presentation, verify it, and only then move it onto the target.

    Args:
        presentation: The presentation to write.
        output: The file to write.
        scaffold: The specification the deck must agree with.
        strict: Whether the deck must be exactly the generated deck.

    Returns:
        The verification report lines.

    Raises:
        Nothing directly; the verification helpers report a failure and the original file is left untouched.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=str(output.parent),
        prefix=f".{output.stem}.",
        suffix=".tmp.pptx",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        presentation.save(str(temporary))
        # WHY: the temporary file was created with mode 0600, so the
        # mode is set before the file is moved onto the target. Without
        # this the deck would be the only unreadable file in the folder.
        temporary.chmod(OUTPUT_FILE_MODE)
        report = verify_package(temporary)
        report += verify_presentation(temporary, scaffold, strict=strict)
        _ = Path(temporary).replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return report


# ---------------------------------------------------------------------------
# The two modes
# ---------------------------------------------------------------------------


def build_regenerate(
    scaffold: Scaffold,
    output: Path,
    *,
    with_sections: bool,
    sky_path: Path,
) -> list[str]:
    """Build the deck from scratch out of the specification.

    Args:
        scaffold: The specification.
        output: The file to write.
        with_sections: Whether the PowerPoint section list is written.
        sky_path: The sky picture every slide sits on.

    Returns:
        The report lines.
    """
    presentation = new_presentation()
    _ = add_title_slide(presentation, scaffold.identity, scaffold.palette, sky_path)
    _ = add_outline_slide(presentation, scaffold, scaffold.palette, sky_path)
    for frame in scaffold.frames:
        slide = _build_frame_slide(presentation, frame, scaffold.palette, sky_path)
        _write_notes(slide, frame, frame.body)
    if with_sections:
        groups = [
            (section, [index for index, frame in enumerate(scaffold.frames) if frame.section == section])
            for section in scaffold.sections
        ]
        apply_powerpoint_sections(presentation, groups)
    report = [
        f"scaffold: {len(scaffold.sections)} owner blocks, {len(scaffold.frames)} placeholder frames",
        f"scaffold: {', '.join(scaffold.sections)}",
    ]
    if with_sections:
        report.append(f"sections written: {', '.join(scaffold.sections)}")
    else:
        report.append("sections: not written, because --no-sections was given")
    report += save_atomically(presentation, output, scaffold, strict=True)
    report.append(f"written: {output.resolve()}")
    return report


def _section_groups_for_update(
    presentation: Presentation,
    scaffold: Scaffold,
    host_of_frame: dict[str, Slide],
) -> list[tuple[str, list[int]]]:
    """Work out which owner block each slide belongs to, for a section rebuild.

    A managed slide belongs to the block of its frame. An owner added slide
    belongs to the block of the managed slide that precedes it, so that a
    slide the owner dropped into the middle of a block stays inside it.

    Args:
        presentation: The presentation being updated.
        scaffold: The specification.
        host_of_frame: The frame identifier to slide object mapping.

    Returns:
        The section name and slide indices pairs, in deck order.
    """
    deck = list(presentation.slides)
    section_of_slide: dict[int | None, str] = {}
    current = scaffold.sections[0]
    for slide in deck:
        section_of_slide[_slide_id_of(slide)] = current
        for frame in scaffold.frames:
            host = host_of_frame.get(frame.id)
            if host is not None and _slide_id_of(host) == _slide_id_of(slide):
                current = frame.section
                break

    groups: list[tuple[str, list[int]]] = []
    for section in scaffold.sections:
        indices = [
            index
            for index, slide in enumerate(deck)
            if section_of_slide[_slide_id_of(slide)] == section
            and _find_shape_by_name(slide, NAME_COVER_TITLE) is None
            and _find_shape_by_name(slide, NAME_OUTLINE_TITLE) is None
        ]
        if len(indices) > 0:
            groups.append((section, indices))
    return groups


def build_update(
    scaffold: Scaffold,
    output: Path,
    *,
    force_bodies: bool,
    force_titles: bool,
    rebuild_sections: bool,
    sky_path: Path,
) -> list[str]:
    """Bring an owner edited deck back in line with the specification.

    A slot whose text still equals the record left by the last run is an
    untouched placeholder and is refreshed. A slot the owner has written is
    kept. Frames that the deck does not carry yet are created and placed
    next to the frame that precedes them in the specification. Slides the owner
    has added are never touched.

    Args:
        scaffold: The specification.
        output: The deck to update, which is also the file that is rewritten.
        force_bodies: Whether owner written slot bodies are overwritten too.
        force_titles: Whether the visible frame titles are overwritten too.
        rebuild_sections: Whether the PowerPoint section list is rewritten.
        sky_path: The sky picture every slide sits on.

    Returns:
        The report lines.

    Raises:
        ScaffoldError: When the deck is missing or cannot be opened.
    """
    output = Path(output)
    if not output.exists():
        failure_reason = (f"cannot update '{output}': the deck does not exist")
        raise ScaffoldError(failure_reason)
    try:
        presentation = Presentation.open(str(output))
    except Exception as exc:  # pragma: no cover - python-pptx raises many types
        failure_reason = (f"cannot open the deck '{output}': {exc}")
        raise ScaffoldError(failure_reason) from exc

    slides = list(presentation.slides)
    known_ids = {frame.id for frame in scaffold.frames}
    host_of_frame: dict[str, Slide] = {}
    matched_slides: set[int] = set()

    for index, slide in enumerate(slides):
        for shape in slide.shapes:
            name = shape.name or ""
            frame_id = _frame_id_of_shape(name, frozenset(known_ids))
            if frame_id is not None and frame_id not in host_of_frame:
                host_of_frame[frame_id] = slide
                matched_slides.add(index)

    for frame in scaffold.frames:
        if frame.id in host_of_frame:
            continue
        for index, slide in enumerate(slides):
            if index in matched_slides:
                continue
            if _find_title_shape(slide, frame.title) is not None:
                host_of_frame[frame.id] = slide
                matched_slides.add(index)
                break

    report: list[str] = [
        f"update: {len(host_of_frame)} of {len(scaffold.frames)} frames found in the deck",
    ]

    for frame in scaffold.frames:
        slide = host_of_frame.get(frame.id)
        if slide is None:
            continue
        if len(frame.body) == 0:
            # WHY: a frame that carries only a graphic owns its glass panel
            # and has no slot box. The slot lookup is skipped for it,
            # because the fallback of that lookup would adopt the panel
            # itself and rename it away from the name that anchors the
            # frame.
            report.append(
                f"  {frame.id}: the frame carries no narration, so only its chrome was refreshed",
            )
        else:
            slot, method = _find_slot_shape(slide, frame, scaffold.palette)
            if slot is None:
                report.append(f"  {frame.id}: no slot box on the slide, so nothing was changed")
                continue
            if method == "adopted":
                slot.name = SLOT_SHAPE_PREFIX + frame.id
                report.append(f"  {frame.id}: adopted the sand slot box as '{SLOT_SHAPE_PREFIX}{frame.id}'")

            current = _narration_text(_collect_narration_shapes(slide, frame.id))
            recorded = _recorded_body(slide, frame)
            if force_bodies:
                _refresh_narration(slide, frame, scaffold.palette, slot)
                _write_notes(slide, frame, frame.body)
                report.append(f"  {frame.id}: slot body replaced because --force-refresh-bodies was given")
            elif recorded is None:
                report.append(f"  {frame.id}: the slide carries no provenance record, so the visible text is kept")
            elif _normalise_body(current) == _normalise_body(recorded):
                _refresh_narration(slide, frame, scaffold.palette, slot)
                _write_notes(slide, frame, frame.body)
                report.append(f"  {frame.id}: slot body refreshed from the specification")
            else:
                _write_notes(slide, frame, current)
                report.append(f"  {frame.id}: the slot was edited by the owner, so the text is kept")

        tag = _find_shape_by_name(slide, NAME_SECTION_TAG)
        if tag is not None:
            _set_shape_text(
                tag,
                frame.section.upper(),
                size=SECTION_TAG_SIZE,
                color=rgb(scaffold.palette, ACCENT_COLOR),
                bold=False,
                italic=False,
            )
        footer = _find_shape_by_name(slide, NAME_SLOT_FOOTER)
        if footer is not None:
            _set_shape_text(
                footer,
                _footer_text(frame),
                size=FOOTER_TEXT_SIZE,
                color=rgb(scaffold.palette, FOOTER_TEXT_COLOR),
                bold=False,
                italic=False,
            )
        if force_titles:
            title_shape = _find_shape_by_name(slide, NAME_FRAME_TITLE)
            if title_shape is not None:
                _set_shape_text(
                    title_shape,
                    frame.title,
                    size=FRAME_TITLE_SIZE,
                    color=rgb(scaffold.palette, TITLE_TEXT_COLOR),
                    bold=True,
                    italic=False,
                )
                report.append(f"  {frame.id}: frame title replaced because --force-refresh-titles was given")

    missing = [frame for frame in scaffold.frames if frame.id not in host_of_frame]
    for frame in missing:
        slide = _build_frame_slide(presentation, frame, scaffold.palette, sky_path)
        _write_notes(slide, frame, frame.body)
        host_of_frame[frame.id] = slide
        report.append(f"  {frame.id}: the frame was missing from the deck and has been created")

    if len(missing) > 0:
        order = {frame.id: index for index, frame in enumerate(scaffold.frames)}
        for frame in missing:
            deck = list(presentation.slides)
            anchor = None
            for previous in reversed([f for f in scaffold.frames if order[f.id] < order[frame.id]]):
                host = host_of_frame.get(previous.id)
                if host is None:
                    continue
                position = _slide_index_by_id(deck, _slide_id_of(host))
                if position is not None:
                    anchor = position + 1
                    break
            if anchor is None:
                for following in [f for f in scaffold.frames if order[f.id] > order[frame.id]]:
                    host = host_of_frame.get(following.id)
                    if host is None:
                        continue
                    position = _slide_index_by_id(deck, _slide_id_of(host))
                    if position is not None:
                        anchor = position
                        break
            if anchor is None:
                anchor = len(deck) - 1
            _move_slide(presentation, host_of_frame[frame.id], anchor)

    if rebuild_sections:
        apply_powerpoint_sections(presentation, _section_groups_for_update(presentation, scaffold, host_of_frame))
        report.append("sections: the PowerPoint section list was rebuilt")
    else:
        report.append("sections: left as they are, because --rebuild-sections was not given")

    _ = _refresh_figures_in_place(presentation, scaffold, scaffold.palette)
    report += save_atomically(presentation, output, scaffold, strict=False)
    report.append(f"written: {output.resolve()}")
    return report


# ---------------------------------------------------------------------------
# Command line entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Run the generator.

    Args:
        argv: The command line arguments, or None to read them from the shell.

    Returns:
        Zero on success, one when the run failed.
    """
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Build or update the Week 17 narrative scaffold as a PowerPoint deck.",
    )
    _ = parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help=f"path of the scaffold specification (default: <source-dir>/{SPEC_FILENAME})",
    )
    _ = parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="folder that holds the scaffold specification (default: the folder of this script)",
    )
    _ = parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"path of the deck to write (default: <source-dir>/{DEFAULT_OUTPUT_NAME})",
    )
    _ = parser.add_argument(
        "--mode",
        choices=("regenerate", "update"),
        default="regenerate",
        help="regenerate builds the deck from scratch; update refreshes an existing deck",
    )
    _ = parser.add_argument("--no-sections", action="store_true", help="do not write the PowerPoint section list")
    _ = parser.add_argument(
        "--force-refresh-bodies",
        action="store_true",
        help="in update mode, replace slot bodies even when the owner has written them",
    )
    _ = parser.add_argument(
        "--force-refresh-titles",
        action="store_true",
        help="in update mode, replace the visible frame titles",
    )
    _ = parser.add_argument(
        "--rebuild-sections",
        action="store_true",
        help="in update mode, rewrite the PowerPoint section list",
    )
    args = parser.parse_args(argv)

    source_dir = (args.source_dir or script_dir).resolve()
    spec_path = (args.spec or (source_dir / SPEC_FILENAME)).resolve()
    output = (args.output or (source_dir / DEFAULT_OUTPUT_NAME)).resolve()

    try:
        scaffold = load_spec(spec_path)
    except ScaffoldError as exc:
        _ = sys.stderr.write(f"FAILED: {exc}\n")
        return 1

    try:
        sky_path = ensure_sky_image(scaffold.palette, source_dir / "figures")
        if args.mode == "regenerate":
            report = build_regenerate(
                scaffold,
                output,
                with_sections=not args.no_sections,
                sky_path=sky_path,
            )
        else:
            report = build_update(
                scaffold,
                output,
                force_bodies=args.force_refresh_bodies,
                force_titles=args.force_refresh_titles,
                rebuild_sections=args.rebuild_sections,
                sky_path=sky_path,
            )
    except ScaffoldError as exc:
        _ = sys.stderr.write(f"FAILED: {exc}\n")
        return 1

    _ = sys.stdout.write(f"sky: {sky_path}\n")
    for line in font_report():
        _ = sys.stdout.write(f"{line}\n")
    for line in report:
        _ = sys.stdout.write(f"{line}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
