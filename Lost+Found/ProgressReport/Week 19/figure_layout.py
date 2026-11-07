#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
# SPDX-License-Identifier: MIT
"""Fit a picture into a box without distorting it, and compose a tall figure.

WHY THIS EXISTS: a filled frame carries a graphic that was drawn for a page,
not for a slide. The graphic has to be placed inside a fixed glass panel of a
fixed size, and it must keep its own proportions, otherwise a plot of a heat
flux curve would be stretched into a different curve. The arithmetic of that
fit is kept in its own module so it can be reasoned about and tested on its
own, without dragging the slide builder in with it. The same module composes
a tall vertical figure into two halves side by side, because a portrait figure
on a landscape slide has to be read as two columns or it becomes unreadable.

THEORIES:
  1. A picture has one aspect ratio, and a box has one aspect ratio. A
     contain fit picks the largest rectangle with the picture's ratio that
     still lies inside the box.
  2. The fitted rectangle is then placed inside the box, horizontally by the
     caller and vertically centred, because a picture that is centred against
     one that is left aligned reads as a mistake.
  3. The fit is computed from the pixel dimensions of the file, so the result
     depends only on the file and the box, never on the renderer.
  4. A tall figure carries its type at a size that is measured against its
     own width, so a portrait figure shown at the width of a slide panel
     shrinks its type to a few points. Cutting it into two halves and laying
     them side by side doubles the width each half is shown at, and therefore
     doubles the size of its type.
  5. The cut is made at a blank row near the middle, because a cut through a
     box would cut the box in half and hide the stage that is cut.

APPLICATIONS: the filled recall frames of the Week 17 narrative deck place a
thesis figure inside the frosted glass panel of the slide, and the research
workflow flowchart of the thesis is shown as its two halves side by side.

CITATIONS:
  - Pillow 13.0.0 -- https://pillow.readthedocs.io/en/stable/reference/Image.html
  - ECMA-376 Part 1, DrawingML pictures --
    https://ecma-international.org/publications-and-standards/standards/ecma-376/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PIL import Image, ImageDraw

from scaffold_logic import ScaffoldError

if TYPE_CHECKING:
    from collections.abc import Sequence

#: The smallest picture dimension that counts as a real picture. A zero or a
#: negative dimension means the file was read wrong, and dividing by it would
#: raise a ZeroDivisionError instead of a clear message.
MINIMUM_PIXEL_DIMENSION = 1
#: The box of a picture fit is left, top, width and height.
BOX_PART_COUNT = 4

#: The number of inches in one foot, used only to keep the geometry in one
#: unit system.
INCHES_PER_FOOT = 12.0

#: The greyscale value below which a pixel counts as ink. The outlines of the
#: thesis flowchart are deep navy, so anything darker than this is a drawn
#: element, while the pale drop shadow of a box stays above it.
INK_GREY_THRESHOLD = 200
#: The fraction of the picture height that is searched for a blank row around
#: the requested split, so the cut can follow the artwork instead of cutting
#: through a box.
SPLIT_SEARCH_FRACTION = 0.08
#: The width of the gap between the two halves of a composed picture, in
#: pixels. It carries the divider rule that tells the reader the left half
#: continues in the right half.
GUTTER_WIDTH_PX = 80
#: The width of the divider rule in the gutter, in pixels.
DIVIDER_WIDTH_PX = 4
#: The colour of the divider rule.
DIVIDER_COLOUR = (176, 189, 200)
#: The colour the composed picture is filled with before the halves are
#: pasted onto it.
BACKGROUND_COLOUR = (255, 255, 255)
#: The ratio at which a tall picture is cut when no other ratio is asked for.
DEFAULT_SPLIT_RATIO = 0.5
#: The box the fit probe reports, in inches: the picture area of a figure
#: panel of the deck.
PROBE_BOX = (0.0, 0.0, 6.0633333, 3.66)


def picture_size_inches(path: Path) -> tuple[float, float]:
    """Return the size of a picture file in inches, from its pixel grid.

    WHY: a picture has no physical size of its own. The size of the panel it
    goes into is set in inches, and the only ratio that matters is the ratio
    between the width and the height of the file, which is a pure number and
    is the same whatever resolution the file was drawn at.

    Args:
        path: The picture file to read.

    Returns:
        The width and the height of the file in pixels.

    Raises:
        ScaffoldError: When the file cannot be opened or carries no pixels.
    """
    try:
        with Image.open(path) as image:
            width_px, height_px = image.size
    except OSError as exc:
        failure_reason = f"cannot read the picture {path}: {exc}"
        raise ScaffoldError(failure_reason) from exc
    if width_px < MINIMUM_PIXEL_DIMENSION or height_px < MINIMUM_PIXEL_DIMENSION:
        failure_reason = f"the picture {path} carries no usable pixels ({width_px} by {height_px})"
        raise ScaffoldError(failure_reason)
    return (float(width_px), float(height_px))


def fit_picture_in_box(
    path: Path, box: Sequence[float], align: str = "center",
) -> tuple[float, float, float, float]:
    """Fit a picture inside a box, keeping its proportions, and place it.

    WHY: the panel is a fixed size, but the pictures come from a thesis and
    have four different shapes. Stretching them to the panel would change what
    they show, so the picture is scaled until one of its sides touches the
    panel and the other stays inside.

    Args:
        path: The picture file to fit.
        box: The box as left, top, width and height in inches.
        align: Where the picture sits horizontally inside the box: "left",
            "center" or "right". A narrow picture that is centred in a wide
            area starts at a different x on every slide, so the left edge of
            the figures would not line up with the left edge of the cards
            underneath them.

    Returns:
        The fitted rectangle as left, top, width and height in inches.

    Raises:
        ScaffoldError: When the picture cannot be read, when the box is empty
            or when the alignment is not one of the three known names.
    """
    if len(box) != BOX_PART_COUNT:
        failure_reason = f"the picture box needs four numbers, found {len(box)}"
        raise ScaffoldError(failure_reason)
    left_in, top_in, width_in, height_in = box
    if width_in <= 0.0 or height_in <= 0.0:
        failure_reason = f"the picture box must have a positive size, found {width_in} by {height_in} inches"
        raise ScaffoldError(failure_reason)

    width_px, height_px = picture_size_inches(path)
    picture_aspect = width_px / height_px
    box_aspect = width_in / height_in
    if picture_aspect >= box_aspect:
        # WHY: the picture is wider than the box, so the width is the binding
        # side and the height follows from the picture's own ratio.
        fitted_width = width_in
        fitted_height = width_in / picture_aspect
    else:
        fitted_height = height_in
        fitted_width = height_in * picture_aspect
    if align == "left":
        offset_x = 0.0
    elif align == "right":
        offset_x = width_in - fitted_width
    elif align == "center":
        offset_x = (width_in - fitted_width) / 2.0
    else:
        failure_reason = f"the picture alignment must be left, center or right, found '{align}'"
        raise ScaffoldError(failure_reason)
    return (
        left_in + offset_x,
        top_in + (height_in - fitted_height) / 2.0,
        fitted_width,
        fitted_height,
    )


def _row_ink_counts(image: Image.Image) -> list[int]:
    """Count, for every row of a picture, how many pixels carry ink.

    WHY: the cut of a tall figure has to fall where the artwork is thinnest,
    so the amount of drawing in a row is what tells a gap between two stages
    from the stage itself. A box is a long horizontal rule and counts in the
    hundreds, while the gap between two boxes carries only the thin connector
    line and counts in the tens.

    Args:
        image: The picture to scan.

    Returns:
        The number of ink pixels of every row of the picture.
    """
    grey = image.convert("L")
    width_px, height_px = grey.size
    data = grey.tobytes()
    counts: list[int] = []
    for row in range(height_px):
        start = row * width_px
        chunk = data[start : start + width_px]
        counts.append(sum(1 for value in chunk if value < INK_GREY_THRESHOLD))
    return counts


def _distance_to_target(run: tuple[int, int], target: int) -> int:
    """Return how far the middle of a run of rows is from a target row.

    Args:
        run: The first and the row after the last row of the run.
        target: The row the run should be closest to.

    Returns:
        The distance in rows between the middle of the run and the target.
    """
    return abs((run[0] + run[1]) // 2 - target)


def _find_split_row(counts: Sequence[int], height_px: int, ratio: float) -> int:
    """Find the row at which a tall picture is cut into two halves.

    WHY: cutting the picture at an arbitrary row would cut a box in half and
    hide the stage that is cut, so the cut is made where the artwork is
    thinnest, close to the requested ratio.

    Args:
        counts: The number of ink pixels of every row of the picture.
        height_px: The height of the picture in pixels.
        ratio: Where the cut should fall, as a fraction of the height.

    Returns:
        The row at which the picture is cut.

    Raises:
        ScaffoldError: When the picture carries no gap near the ratio.
    """
    target = int(height_px * ratio)
    span = int(height_px * SPLIT_SEARCH_FRACTION)
    low = max(MINIMUM_PIXEL_DIMENSION, target - span)
    high = min(height_px - MINIMUM_PIXEL_DIMENSION, target + span)
    window = list(counts[low : high + 1])
    if len(window) == 0:
        failure_reason = (
            f"the picture has no row to cut near the split ratio {ratio:.3f}"
        )
        raise ScaffoldError(failure_reason)
    thinnest = min(window)
    runs: list[tuple[int, int]] = []
    run_start = -1
    for row in range(low, high + 1):
        if counts[row] <= thinnest:
            if run_start < 0:
                run_start = row
        elif run_start >= 0:
            runs.append((run_start, row))
            run_start = -1
    if run_start >= 0:
        runs.append((run_start, high + 1))
    if len(runs) == 0:
        failure_reason = (
            f"no gap was found near the split ratio {ratio:.3f}, "
            f"so the picture cannot be cut without cutting a drawn element"
        )
        raise ScaffoldError(failure_reason)
    distances = [_distance_to_target(run, target) for run in runs]
    best = runs[distances.index(min(distances))]
    return (best[0] + best[1]) // 2


def _trim_to_ink(image: Image.Image, counts: Sequence[int], first: int, last: int) -> Image.Image:
    """Cut the blank margin off the top and the bottom of a band of rows.

    WHY: the two halves of a tall figure are not the same height, so the
    shorter one would leave a band of empty paper under it and the composed
    picture would carry a margin that is not part of the drawing.

    Args:
        image: The picture the band belongs to.
        counts: The number of ink pixels of every row of the picture.
        first: The first row of the band.
        last: The row after the last row of the band.

    Returns:
        The band of rows, without its blank top and bottom margin.
    """
    top = first
    while top < last and counts[top] == 0:
        top += 1
    bottom = last
    while bottom > top and counts[bottom - 1] == 0:
        bottom -= 1
    return image.crop((0, top, image.width, bottom))


def compose_halves_side_by_side(
    source: Path, output: Path, ratio: float = DEFAULT_SPLIT_RATIO,
) -> tuple[int, int]:
    """Cut a tall picture in half and lay the two halves side by side.

    WHY: the research workflow flowchart of the thesis is 1760 by 3600 pixels
    and its labels are about eight points at the size the thesis prints them.
    Shown whole on a slide the labels fall to about two points and the
    figure cannot be read at all. Cut in half and laid side by side, each half
    is shown at twice the width and its labels stay legible, and the two
    halves are still one picture, so the slide builder stays unchanged.

    Args:
        source: The tall picture to cut.
        output: The composed picture to write.
        ratio: Where the cut falls, as a fraction of the height.

    Returns:
        The width and the height of the composed picture in pixels.

    Raises:
        ScaffoldError: When the source cannot be read or carries no gap near
            the requested ratio.
    """
    try:
        with Image.open(source) as image:
            picture = image.convert("RGB")
    except OSError as exc:
        failure_reason = f"cannot read the picture {source}: {exc}"
        raise ScaffoldError(failure_reason) from exc
    width_px, height_px = picture.size
    counts = _row_ink_counts(picture)
    split_row = _find_split_row(counts, height_px, ratio)
    upper = _trim_to_ink(picture, counts, 0, split_row)
    lower = _trim_to_ink(picture, counts, split_row, height_px)
    composed_height = max(upper.height, lower.height)
    composed = Image.new(
        "RGB", (width_px * 2 + GUTTER_WIDTH_PX, composed_height), BACKGROUND_COLOUR,
    )
    composed.paste(upper, (0, 0))
    composed.paste(lower, (width_px + GUTTER_WIDTH_PX, 0))
    divider_x = width_px + GUTTER_WIDTH_PX // 2
    drawer = ImageDraw.Draw(composed)
    drawer.line(
        [(divider_x, 0), (divider_x, composed_height)],
        fill=DIVIDER_COLOUR,
        width=DIVIDER_WIDTH_PX,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    composed.save(output)
    return (composed.width, composed.height)


def main(argv: Sequence[str] | None = None) -> int:
    """Print the fit of a picture, or compose the halves of a tall picture.

    WHY: the fit is pure arithmetic over a file, so it can be checked by hand
    before a slide is drawn, without building a deck. The composition is a
    build step of the thesis figure, so it has to be runnable on its own and
    repeatable from the command line.

    Args:
        argv: The command line arguments, without the program name.

    Returns:
        Zero when every picture was read.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    _ = parser.add_argument(
        "--compose",
        nargs=2,
        metavar=("SOURCE", "OUTPUT"),
        help="cut a tall picture in half and lay the halves side by side",
    )
    _ = parser.add_argument(
        "--ratio",
        type=float,
        default=DEFAULT_SPLIT_RATIO,
        help="where the cut falls, as a fraction of the height",
    )
    _ = parser.add_argument(
        "pictures",
        nargs="*",
        help="the pictures whose fit is printed",
    )
    arguments = parser.parse_args(argv)

    if arguments.compose is not None:
        compose = cast("list[str]", arguments.compose)
        source = Path(compose[0])
        output = Path(compose[1])
        width_px, height_px = compose_halves_side_by_side(source, output, arguments.ratio)
        _ = sys.stdout.write(f"composed {output.name}: {width_px} by {height_px} pixels\n")

    for argument in cast("list[str]", arguments.pictures):
        picture = Path(argument)
        fitted = fit_picture_in_box(picture, PROBE_BOX)
        _ = sys.stdout.write(
            f"{picture.name}: {fitted[2]:.4f} by {fitted[3]:.4f} inches "
            f"at {fitted[0]:.4f}, {fitted[1]:.4f}\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
