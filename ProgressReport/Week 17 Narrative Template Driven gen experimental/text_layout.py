#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
# SPDX-License-Identifier: MIT
"""Measure wrapped text so a card can be sized to the text it carries.

WHY THIS EXISTS:
    The narration of a filled frame is drawn as one card per point, and
    every card has to be exactly as tall as the text inside it. A card
    that is too short clips its own words, and a card that is too tall
    leaves a hole. The height therefore has to be MEASURED, not guessed,
    and the measurement has to use the very font file the deck names,
    because a renderer that substitutes a wider face wraps the text
    earlier and produces a taller block.

THEORIES:
    1. A line of text occupies a known number of lines once the width of
       the box and the width of the face are known. Greedy word wrapping
       is what the renderer does, so greedy word wrapping is what the
       layout must do.
    2. The line advance of a paragraph is the line height of the face
       multiplied by the paragraph line spacing, exactly as the renderer
       computes it.
    3. A block of text is as tall as its lines plus the padding above
       and below it. Therefore the height of a card is a pure function of
       (text, face, size, width, spacing, padding) and can be computed
       before anything is drawn.

APPLICATIONS:
    The card layout of a filled narrative frame uses `block_height_inches`
    to size every card, and `wrap_line_count` to report how many lines a
    point occupies so that a card that would overflow its column is
    detected before the deck is written.

CITATIONS:
    Pillow 13.0.0, ImageFont.getlength and ImageFont.getmetrics
    https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
    ECMA-376 Part 1, DrawingML text layout
    https://ecma-international.org/publications-and-standards/standards/ecma-376/
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PIL import ImageFont

from font_choice import font_file_for
from scaffold_logic import ScaffoldError

if TYPE_CHECKING:
    from collections.abc import Sequence

#: Pixels per point used while measuring. A high resolution keeps the
#: rounding error of a measured width far below one thousandth of an
#: inch, which is the precision the layout needs.
MEASUREMENT_PIXELS_PER_POINT = 4

#: Points per inch.
POINTS_PER_INCH = 72

#: The fallback advance of a character, in fractions of the font size, used
#: when the named face cannot be loaded at all. It is the average advance
#: of a sans serif face and only ever makes the estimate conservative.
FALLBACK_ADVANCE_RATIO = 0.5

#: The fallback line height of a font, in fractions of the font size,
#: used when the named face cannot be loaded at all.
FALLBACK_LINE_HEIGHT_RATIO = 1.2

#: The number of parts a box needs.
BOX_PART_COUNT = 4
#: The smallest number of command line arguments the probe accepts.
MINIMUM_ARGUMENT_COUNT = 2
#: The face, the size and the width the probe measures with.
PROBE_FAMILY = "Abadi MT Condensed Light"
PROBE_SIZE_PT = 13.0
PROBE_WIDTH_IN = 4.8


def _font_at(family: str, size_pt: float) -> ImageFont.FreeTypeFont | None:
    """Load the font file behind a family at a given size.

    WHY: the measurement is only meaningful when it uses the same face
    the renderer will draw with. A face that is not installed cannot be
    measured, and the caller then falls back to a nominal estimate.

    Args:
        family: The font family name as the deck names it.
        size_pt: The size of the type in points.

    Returns:
        The loaded font, or None when the family is not installed.

    """
    path = font_file_for(family)
    if path is None:
        return None
    pixels = round(size_pt * MEASUREMENT_PIXELS_PER_POINT)
    try:
        return ImageFont.truetype(str(path), pixels)
    except OSError:
        return None


def text_width_inches(text: str, family: str, size_pt: float) -> float:
    """Measure the width of a single line of text.

    Args:
        text: The line to measure.
        family: The font family name as the deck names it.
        size_pt: The size of the type in points.

    Returns:
        The width of the line in inches.

    """
    font = _font_at(family, size_pt)
    if font is None:
        return len(text) * size_pt * FALLBACK_ADVANCE_RATIO / POINTS_PER_INCH
    return font.getlength(text) / MEASUREMENT_PIXELS_PER_POINT / POINTS_PER_INCH


def line_height_inches(family: str, size_pt: float) -> float:
    """Measure the line advance of a face at a given size.

    WHY: a paragraph is as tall as its lines, and the line advance is
    what the renderer uses, so the layout has to use the same number.

    Args:
        family: The font family name as the deck names it.
        size_pt: The size of the type in points.

    Returns:
        The height of one line in inches.

    """
    font = _font_at(family, size_pt)
    if font is None:
        return size_pt * FALLBACK_LINE_HEIGHT_RATIO / POINTS_PER_INCH
    ascent, descent = font.getmetrics()
    return (ascent + descent) / MEASUREMENT_PIXELS_PER_POINT / POINTS_PER_INCH


def wrap_line_count(text: str, family: str, size_pt: float, width_in: float) -> int:
    """Count the lines a text occupies in a box of a given width.

    WHY: the greedy word wrapping performed here is the wrapping the
    renderer performs, so the number of lines is the number of lines the
    card will really hold.

    Args:
        text: The text to wrap.
        family: The font family name as the deck names it.
        size_pt: The size of the type in points.
        width_in: The width of the box in inches.

    Returns:
        The number of lines the text occupies, at least one.

    Raises:
        ScaffoldError: When the box has no usable width.

    """
    if width_in <= 0.0:
        failure_reason = f"the text box must have a positive width, found {width_in} inches"
        raise ScaffoldError(failure_reason)
    words = text.split()
    if len(words) == 0:
        return 1
    lines = 1
    current = ""
    for word in words:
        candidate = word if len(current) == 0 else f"{current} {word}"
        if text_width_inches(candidate, family, size_pt) <= width_in:
            current = candidate
            continue
        if len(current) != 0:
            lines += 1
        current = word
    return lines


def block_height_inches(
    text: str,
    family: str,
    size_pt: float,
    width_in: float,
    *,
    line_spacing: float = 1.0,
    padding_in: float = 0.0,
) -> float:
    """Compute the height a block of text needs inside a card.

    Args:
        text: The text of the block.
        family: The font family name as the deck names it.
        size_pt: The size of the type in points.
        width_in: The width of the text area in inches.
        line_spacing: The paragraph line spacing multiplier.
        padding_in: The padding above and below the text in inches.

    Returns:
        The height of the block in inches.

    """
    lines = wrap_line_count(text, family, size_pt, width_in)
    advance = line_height_inches(family, size_pt) * line_spacing
    return lines * advance + 2.0 * padding_in


def main(argv: Sequence[str]) -> int:
    """Print the measured layout of every text given on the command line.

    Args:
        argv: The command line arguments, the texts to measure.

    Returns:
        The process exit code.

    """
    if len(argv) < MINIMUM_ARGUMENT_COUNT:
        _ = sys.stdout.write("usage: text_layout.py <text> [<text> ...]\n")
        return 1
    for argument in argv[1:]:
        lines = wrap_line_count(argument, PROBE_FAMILY, PROBE_SIZE_PT, PROBE_WIDTH_IN)
        _ = sys.stdout.write(f"{argument!r} -> {lines} lines\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
