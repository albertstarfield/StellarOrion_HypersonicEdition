#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
# SPDX-License-Identifier: MIT
"""Draw the sky picture that every slide of the deck sits on.

WHY THIS EXISTS
---------------
The deck's background is a vertical gradient that runs from a pale mint
white at the top, through a bright turquoise, into a saturated teal at the
bottom. That gradient is
written into the slide XML as an ``a:gradFill``, and Microsoft PowerPoint
renders it correctly. The macOS Quick Look generator does not: it flattens any
gradient to the unweighted mean of its stops, so on the machine that builds
the deck the sky could neither be previewed nor checked. The sky is therefore
drawn once, as a picture, and every slide carries it as its first shape. Every
renderer then shows exactly the same sky, and the frosted glass panels have
something to sit on.

THEORIES
--------
1. A background that cannot be rendered cannot be verified, so the background
   is carried as a picture rather than as gradient markup.
2. The picture is named after a hash of the colours and the drawing constants
   it was built from. A change to either produces a new file, and an unchanged
   palette reuses the file that is already there, so the build is
   reproducible and never serves a stale sky.
3. The glass panels only read as glass when something is behind them, so the
   sky has to be the first shape on every slide.

APPLICATIONS
------------
:func:`ensure_sky_image` is called once per build, before any slide is drawn.

CITATIONS
---------
* Pillow 13.0.0 -- https://pillow.readthedocs.io/en/stable/
* ECMA-376 Part 1, DrawingML pictures -- https://ecma-international.org/publications-and-standards/standards/ecma-376/
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from scaffold_logic import HEX_COLOUR_LENGTH, ScaffoldError

#: The width of the sky picture in pixels.
SKY_IMAGE_WIDTH_PX = 2560
#: The height of the sky picture in pixels.
SKY_IMAGE_HEIGHT_PX = 1440
#: The palette slot of the colour the sky starts at, at the top of the slide.
GRADIENT_TOP_NAME = "Light"
#: The palette slot of the colour in the middle of the sky.
GRADIENT_MIDDLE_NAME = "Mid"
#: The palette slot of the colour the sky ends at, at the bottom of the slide.
GRADIENT_BOTTOM_NAME = "Ink"
#: Where the middle colour of the sky sits, counted from the top of the slide.
GRADIENT_MIDDLE_POSITION = 0.44
#: The horizontal centre of the bloom, as a fraction of the width.
SKY_BLOOM_CENTRE_X = 0.5
#: The vertical centre of the bloom, as a fraction of the height.
SKY_BLOOM_CENTRE_Y = 0.02
#: The horizontal radius of the bloom, as a fraction of the width.
SKY_BLOOM_RADIUS_X = 0.95
#: The vertical radius of the bloom, as a fraction of the height.
SKY_BLOOM_RADIUS_Y = 0.62
#: How strongly the bloom lightens the sky, from 0.0 to 1.0.
SKY_BLOOM_STRENGTH = 0.34
#: The radius of the blurred edge of the bloom, as a fraction of the width.
SKY_BLOOM_BLUR = 0.10
#: The horizontal radius of the vignette, as a fraction of the width.
SKY_VIGNETTE_RADIUS_X = 0.92
#: The vertical radius of the vignette, as a fraction of the height.
SKY_VIGNETTE_RADIUS_Y = 0.92
#: How strongly the vignette darkens the corners, from 0.0 to 1.0.
SKY_VIGNETTE_STRENGTH = 0.30
#: The radius of the blurred edge of the vignette, as a fraction of the width.
SKY_VIGNETTE_BLUR = 0.16
#: The number of hexadecimal digits of the signature in the file name.
SKY_SIGNATURE_LENGTH = 8
#: The largest value one colour channel may hold.
CHANNEL_MAXIMUM = 255
#: The number of channels a colour is made of.
CHANNEL_COUNT = 3


def _gradient_stops(palette: dict[str, str]) -> list[tuple[float, tuple[int, int, int]]]:
    """Read the three gradient stops of the sky out of the palette.

    Args:
        palette: The palette that resolves every colour name.

    Returns:
        The stops, each a position from 0.0 to 1.0 and a colour.

    Raises:
        ScaffoldError: When the palette has no colour for one of the stops.
    """
    for name in (GRADIENT_TOP_NAME, GRADIENT_MIDDLE_NAME, GRADIENT_BOTTOM_NAME):
        if name not in palette:
            failure_reason = f"the palette needs a '{name}' colour to draw the sky"
            raise ScaffoldError(failure_reason)
    return [
        (0.0, hex_to_rgb(palette[GRADIENT_TOP_NAME])),
        (GRADIENT_MIDDLE_POSITION, hex_to_rgb(palette[GRADIENT_MIDDLE_NAME])),
        (1.0, hex_to_rgb(palette[GRADIENT_BOTTOM_NAME])),
    ]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Turn a six digit hexadecimal colour into its three channels.

    Args:
        value: The colour as six hexadecimal digits, with no leading hash.

    Returns:
        The red, green and blue channels, each from 0 to 255.

    Raises:
        ScaffoldError: When the text is not six hexadecimal digits.
    """
    text = value.strip().lstrip("#")
    if len(text) != HEX_COLOUR_LENGTH:
        failure_reason = f"'{value}' is not six hexadecimal digits, so it is not a colour"
        raise ScaffoldError(failure_reason)
    try:
        channels = tuple(int(text[index : index + 2], 16) for index in range(0, 6, 2))
    except ValueError as exc:
        failure_reason = f"'{value}' is not six hexadecimal digits, so it is not a colour"
        raise ScaffoldError(failure_reason) from exc
    red, green, blue = channels
    return (red, green, blue)


def relative_luminance(colour: str) -> float:
    """Read how bright a colour is.

    Args:
        colour: The colour as six hexadecimal digits.

    Returns:
        The brightness, from 0.0 for black to 1.0 for white.
    """
    red, green, blue = hex_to_rgb(colour)
    return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / CHANNEL_MAXIMUM


def sky_colour_at(palette: dict[str, str], ratio: float) -> str:
    """Read the colour of the sky at one position down the slide.

    Args:
        palette: The palette that resolves every colour name.
        ratio: The position down the slide, from 0.0 at the top to 1.0 at the bottom.

    Returns:
        The colour as six hexadecimal digits.

    Raises:
        Nothing directly; the helper that reads the palette reports the failure.
    """
    red, green, blue = gradient_colour(_gradient_stops(palette), ratio)
    return f"{red:02X}{green:02X}{blue:02X}"


def gradient_colour(
    stops: list[tuple[float, tuple[int, int, int]]],
    ratio: float,
) -> tuple[int, int, int]:
    """Read the colour of a gradient at one position.

    Args:
        stops: The gradient stops, each a position from 0.0 to 1.0 and a colour.
        ratio: The position to read, from 0.0 to 1.0.

    Returns:
        The red, green and blue channels at that position.

    Raises:
        ScaffoldError: When the gradient carries no stop at all.
    """
    if len(stops) == 0:
        failure_reason = "a gradient needs at least one stop to be read"
        raise ScaffoldError(failure_reason)
    if ratio <= stops[0][0]:
        return stops[0][1]
    for index in range(1, len(stops)):
        position, colour = stops[index]
        if ratio > position:
            continue
        before_position, before_colour = stops[index - 1]
        span = position - before_position
        if span <= 0.0:
            return colour
        mix = (ratio - before_position) / span
        return (
            round(before_colour[0] + (colour[0] - before_colour[0]) * mix),
            round(before_colour[1] + (colour[1] - before_colour[1]) * mix),
            round(before_colour[2] + (colour[2] - before_colour[2]) * mix),
        )
    return stops[-1][1]


def _build_gradient(palette: dict[str, str]) -> Image.Image:
    """Paint the vertical gradient of the sky.

    Args:
        palette: The palette that resolves every colour name.

    Returns:
        The gradient as a picture.
    """
    stops = _gradient_stops(palette)
    column = Image.new("RGB", (1, SKY_IMAGE_HEIGHT_PX))
    pixels = [
        gradient_colour(stops, row / max(SKY_IMAGE_HEIGHT_PX - 1, 1)) for row in range(SKY_IMAGE_HEIGHT_PX)
    ]
    column.putdata(pixels)
    return column.resize((SKY_IMAGE_WIDTH_PX, SKY_IMAGE_HEIGHT_PX), Image.Resampling.BICUBIC)


def _add_bloom(image: Image.Image) -> Image.Image:
    """Lighten the top of the sky with a soft bloom.

    Args:
        image: The sky as it was drawn.

    Returns:
        The sky with the bloom applied.
    """
    mask = Image.new("L", image.size, 0)
    drawing = ImageDraw.Draw(mask)
    centre_x = int(image.width * SKY_BLOOM_CENTRE_X)
    centre_y = int(image.height * SKY_BLOOM_CENTRE_Y)
    radius_x = int(image.width * SKY_BLOOM_RADIUS_X)
    radius_y = int(image.height * SKY_BLOOM_RADIUS_Y)
    drawing.ellipse(
        (centre_x - radius_x, centre_y - radius_y, centre_x + radius_x, centre_y + radius_y),
        fill=round(CHANNEL_MAXIMUM * SKY_BLOOM_STRENGTH),
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=image.width * SKY_BLOOM_BLUR))
    white = Image.new("RGB", image.size, (CHANNEL_MAXIMUM, CHANNEL_MAXIMUM, CHANNEL_MAXIMUM))
    return Image.composite(white, image, mask)


def _add_vignette(image: Image.Image) -> Image.Image:
    """Darken the corners of the sky so the middle of the slide carries the eye.

    Args:
        image: The sky as it was drawn.

    Returns:
        The sky with the vignette applied.
    """
    outside = round(CHANNEL_MAXIMUM * SKY_VIGNETTE_STRENGTH)
    mask = Image.new("L", image.size, outside)
    drawing = ImageDraw.Draw(mask)
    centre_x = image.width // 2
    centre_y = image.height // 2
    radius_x = int(image.width * SKY_VIGNETTE_RADIUS_X)
    radius_y = int(image.height * SKY_VIGNETTE_RADIUS_Y)
    drawing.ellipse(
        (centre_x - radius_x, centre_y - radius_y, centre_x + radius_x, centre_y + radius_y),
        fill=CHANNEL_MAXIMUM,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=image.width * SKY_VIGNETTE_BLUR))
    dark = Image.new("RGB", image.size, (0, 0, 0))
    return Image.composite(image, dark, mask)


def _build_sky(palette: dict[str, str]) -> Image.Image:
    """Draw the whole sky.

    Args:
        palette: The palette that resolves every colour name.

    Returns:
        The sky as a picture.
    """
    sky = _build_gradient(palette)
    sky = _add_bloom(sky)
    return _add_vignette(sky)


def _sky_signature(palette: dict[str, str]) -> str:
    """Hash everything the sky is drawn from, so a change produces a new file.

    Args:
        palette: The palette that resolves every colour name.

    Returns:
        The first eight hexadecimal digits of the hash.
    """
    material = "|".join(
        [
            palette.get(GRADIENT_TOP_NAME, ""),
            palette.get(GRADIENT_MIDDLE_NAME, ""),
            palette.get(GRADIENT_BOTTOM_NAME, ""),
            str(GRADIENT_MIDDLE_POSITION),
            f"{SKY_IMAGE_WIDTH_PX}x{SKY_IMAGE_HEIGHT_PX}",
            str(SKY_BLOOM_STRENGTH),
            str(SKY_VIGNETTE_STRENGTH),
        ],
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:SKY_SIGNATURE_LENGTH]


def _is_usable(path: Path) -> bool:
    """Check whether a sky file is already there and is the right size.

    Args:
        path: The file to check.

    Returns:
        Whether the file can be reused.
    """
    if not path.exists():
        return False
    try:
        with Image.open(path) as picture:
            return picture.size == (SKY_IMAGE_WIDTH_PX, SKY_IMAGE_HEIGHT_PX)
    except OSError:
        return False


def ensure_sky_image(palette: dict[str, str], figures_dir: Path) -> Path:
    """Return the sky picture for a palette, drawing it when it is not there yet.

    Args:
        palette: The palette that resolves every colour name.
        figures_dir: The folder the picture is kept in.

    Returns:
        The path of the sky picture.

    Raises:
        ScaffoldError: When the palette has no colour for one of the gradient
            stops, or when the picture cannot be written.
    """
    _ = _gradient_stops(palette)
    signature = _sky_signature(palette)
    figures_dir.mkdir(parents=True, exist_ok=True)
    target = figures_dir / f"sky_{signature}.png"
    if _is_usable(target):
        return target
    try:
        picture = _build_sky(palette)
        picture.save(target, format="PNG", optimize=True)
    except OSError as exc:
        failure_reason = f"cannot write the sky picture to '{target}': {exc}"
        raise ScaffoldError(failure_reason) from exc
    return target
