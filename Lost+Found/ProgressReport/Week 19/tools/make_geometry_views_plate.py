#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Compose the two bodies' four azimuth views at their true 1:1 aspect.

WHY: the thesis draws this comparison through a gridspec and stretches each
source picture into its cell with ``aspect="auto"``, so a wide four-view sheet
is squeezed into a cell that is nearly square. The bodies come out shaped like
vertical ellipses and narrow cones instead of bodies of revolution. Scaling or
cropping that plate cannot undo the squeeze, because the distortion is already
inside its pixels. So this script cuts the four panel squares out of each
source sheet at their measured bounds and lays them out again at the aspect the
panels actually have: one square per panel, four azimuths across, one body per
row. Nothing is redrawn and no render is repeated: every pixel of every body is
a crop of the picture the thesis already carries.

AXIOMS
    A1. A body of revolution seen along its axis is a circle, so its panel
        must be square in the composed plate. Any other aspect is a lie about
        the geometry.
    A2. The four panels of a source sheet are square blocks of the same size,
        so the plate can be rebuilt from measured rectangles alone and needs
        no resampling of the sheet as a whole.
    A3. Both bodies share one colour scale, so one note on the plate is
        enough and no second colour bar is needed.

THEORIES
    T1. Cutting at the panel bounds removes the per-panel ``az`` captions,
        which then have to be drawn once for the whole column instead of once
        per row; the plate is the same information with less repeated type.
    T2. At 300 dpi a 1.72 in panel is 516 px square, downsampled from 605 px,
        so the body keeps its edge and the anti-aliasing of the source.

APPLICATIONS
    Writes ``figures/thesis_geometry_views_plate.png`` for the deck only. The
    thesis plate and its generator are untouched.

CITATIONS
    [1] stellarorion_program_proc/results/99_shared/geometry/
        irve3_validation_3d_4views.png, 2548 by 1782 px.
    [2] stellarorion_program_proc/results/99_shared/geometry/
        optimized_topology_3d_4views.png, 2685 by 1782 px.
    [3] CurrentThesisFinalReport/figures/make_results_plates.py, the builder
        that squeezed these sheets with ``aspect="auto"``.
    [4] Pillow 12.0.0 - https://pillow.readthedocs.io/en/stable/

EXCEPTIONS
    Every failure writes a line beginning with MISMATCH to standard error and
    exits non-zero, so a missing source or font cannot pass as a plate.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
GEOMETRY = REPO / "stellarorion_program_proc/results/99_shared/geometry"
IRVE = GEOMETRY / "irve3_validation_3d_4views.png"
OPTIMISED = GEOMETRY / "optimized_topology_3d_4views.png"
OUT = PROJECT / "figures/thesis_geometry_views_plate.png"

DPI = 300
MIN_BYTES = 60000

# WHY these rectangles: measured on each sheet by counting the pixels brighter
# than the page black (10, 10, 15); each panel is the block whose background is
# the dark navy (26, 26, 46). All eight are 605 or 606 px square, which is the
# proof that the source views are square and only the page cell squeezed them.
PANELS = {
    "irve3": ((599, 212, 1205, 817), (1326, 212, 1932, 817),
              (599, 968, 1205, 1573), (1326, 968, 1932, 1573)),
    "optimised": ((668, 212, 1273, 817), (1394, 212, 2000, 817),
                  (668, 968, 1273, 1573), (1394, 968, 2000, 1573)),
}

AZIMUTHS = tuple(f"az = {angle}\u00b0" for angle in (0, 90, 180, 270))
ROW_LABELS = ("IRVE-3 validation baseline", "Optimised topology, round 1")

W_IN, H_IN = 7.70, 4.01
TOP_IN = 0.03
HEADER_IN = 0.22
GAP_X_IN = 0.14
GAP_Y_IN = 0.10
ROW_GAP_IN = 0.05
NOTE_IN = 0.18
NOTE_GAP_IN = 0.05
BOTTOM_IN = 0.03
LEFT_LABEL_IN = 0.21
LEFT_PAD_IN = 0.06
PANEL_IN = (H_IN - TOP_IN - HEADER_IN - GAP_Y_IN - ROW_GAP_IN - NOTE_GAP_IN
            - NOTE_IN - BOTTOM_IN) / 2.0

INK = (34, 34, 34)
GREY = (90, 90, 90)
FRAME = (187, 187, 187)
NOTE = ("Colour is axial position z along the body, 0.2 m at the nose to 1.2 m "
        "aft, on one scale shared by both bodies.")

SERIF_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/Library/Fonts/Times New Roman.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
)


def load_font(size_px: int) -> ImageFont.FreeTypeFont:
    """Return a serif face at the requested pixel size.

    Args:
        size_px: The type size in pixels for this canvas.

    Returns:
        The first serif face found on this machine.

    Raises:
        SystemExit: When no serif face exists, because falling back to a
            bitmap default would change the plate's appearance silently.
    """
    for candidate in SERIF_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size_px)
    _ = sys.stderr.write("MISMATCH no serif face was found for the plate\n")
    raise SystemExit(1)


def rotate_label(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """Render a row label rotated a quarter turn for the left margin.

    Args:
        text: The row label to draw.
        font: The face the label is set in.

    Returns:
        An RGBA image holding the rotated label, tightly cropped.
    """
    probe = Image.new("RGBA", (10, 10), (255, 255, 255, 0))
    box = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
    strip_width = int(box[2] - box[0]) + 8
    strip_height = int(box[3] - box[1]) + 8
    strip = Image.new("RGBA", (strip_width, strip_height), (255, 255, 255, 0))
    ImageDraw.Draw(strip).text((4 - box[0], 4 - box[1]), text,
                               font=font, fill=(*INK, 255))
    return strip.rotate(90, expand=True)


def main() -> int:
    """Build the plate from the two measured four-view sheets.

    Returns:
        Zero on success, one when a source is missing or the plate is short.
    """
    for source in (IRVE, OPTIMISED):
        if not source.is_file():
            _ = sys.stderr.write(f"MISMATCH source sheet missing: {source}\n")
            return 1

    canvas_w = round(W_IN * DPI)
    canvas_h = round(H_IN * DPI)
    panel_px = round(PANEL_IN * DPI)
    gap_px = round(GAP_X_IN * DPI)
    left_px = round((LEFT_LABEL_IN + LEFT_PAD_IN) * DPI)
    top_px = round((TOP_IN + HEADER_IN) * DPI)
    row_step = panel_px + round(GAP_Y_IN * DPI) + round(ROW_GAP_IN * DPI)

    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    column_font = load_font(round(0.105 * DPI))
    row_font = load_font(round(0.095 * DPI))
    note_font = load_font(round(0.078 * DPI))

    for index, azimuth in enumerate(AZIMUTHS):
        left = left_px + index * (panel_px + gap_px)
        box = draw.textbbox((0, 0), azimuth, font=column_font)
        middle = left + panel_px / 2.0 - (box[2] - box[0]) / 2.0
        draw.text((middle - box[0], top_px - round(HEADER_IN * DPI)),
                  azimuth, font=column_font, fill=INK)

    for row, (key, source, label) in enumerate(
        (("irve3", IRVE, ROW_LABELS[0]), ("optimised", OPTIMISED, ROW_LABELS[1])),
    ):
        top = top_px + row * row_step
        with Image.open(source) as opened:
            sheet = opened.convert("RGB")
            for index, panel in enumerate(PANELS[key]):
                square = sheet.crop(panel).resize(
                    (panel_px, panel_px), Image.Resampling.LANCZOS,
                )
                left = left_px + index * (panel_px + gap_px)
                canvas.paste(square, (left, top))
                draw.rectangle(
                    (left, top, left + panel_px - 1, top + panel_px - 1),
                    outline=FRAME, width=2,
                )
        plate = rotate_label(label, row_font)
        canvas.paste(
            plate,
            (round(0.05 * DPI),
             top + panel_px // 2 - plate.height // 2),
            plate,
        )

    # WHY the note sits below the last row: written over the panels it was grey
    # type on a dark panel, which is unreadable at slide size.
    note_top = canvas_h - round(BOTTOM_IN * DPI) - round(NOTE_IN * DPI)
    draw.text((left_px, note_top), NOTE, font=note_font, fill=GREY)

    canvas.save(OUT, format="PNG", optimize=True)
    size = OUT.stat().st_size
    if size < MIN_BYTES:
        _ = sys.stderr.write(
            f"MISMATCH the geometry plate is short: {size} bytes\n",
        )
        return 1
    _ = sys.stdout.write(
        f"[ok] geometry views plate: {canvas_w}x{canvas_h}px, {size} bytes, "
        f"8 square panels of {panel_px}px\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
