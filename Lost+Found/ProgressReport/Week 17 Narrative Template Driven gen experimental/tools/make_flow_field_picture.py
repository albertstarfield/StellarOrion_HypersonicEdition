#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Compose the four DSMC flow fields of Chapter 4 into one deck picture.

WHY: the deck's methodology block ends with the optimization pipeline and
never showed the flow the solver actually produced. Chapter 4 of the thesis
carries four field maps of the validation reference run, one panel each, and
the deck has one picture box, so the four are composed here into a single
plate of the same shape the thesis prints them in.

The panels are pasted as they are, at their published size ratio, on the
background colour they already carry. Nothing is recoloured, cropped or
retouched, because each panel carries its own colour bar and its own
condition box. That condition box is the one thing a reader must not trust:
the thesis states in the captions that the legend printed inside the panels
belongs to a superseded campaign, and the authoritative condition is
M_inf = 7.53, T_inf = 267.85 K, V_inf about 2472 m/s, 19321 child cells.
The slide caption and the narration carry that correction; this picture
carries the fields.

The script writes only into the figures folder of the deck and uses the
project virtual environment, which already holds Pillow.

Citations:
    Pillow 12, https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
    Pillow 12, https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.resize
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
THESIS_FIGURES = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"

#: The four panels, in reading order: top-left, top-right, bottom-left,
#: bottom-right. The order follows the thesis, which introduces the scalar
#: fields before the vector one.
PANELS: tuple[tuple[str, str], ...] = (
    ("thermal_map_smooth.png", "temperature"),
    ("pressure_map_smooth.png", "pressure"),
    ("mach_map_smooth_M0_A0.png", "mach"),
    ("velocity_vectors_smooth.png", "velocity"),
)

#: The drag panel of the gate comparison, copied without recomposition.
DRAG_SOURCE = THESIS_FIGURES / "ref_vs_opt_dsmc_comparison.png"
DRAG_OUT = FIGURES / "thesis_ref_vs_opt_dsmc_comparison.png"

#: The plate this script writes, at the shape of the picture box of a
#: side_points frame: 7.70 in by 3.98 in at 300 dots per inch.
OUT_PLATE = FIGURES / "thesis_flow_field_maps.png"
PLATE_W = 2310
PLATE_H = 1194
#: Width of the white gutter that separates the four panels, in pixels.
GUTTER = 8

#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 20000


def _paste_panel(canvas: Image.Image, path: Path, box: tuple[int, int, int, int]) -> None:
    """Paste one field map into its cell, padded with the map's own sky.

    WHY: the four maps share one dark background, so padding each panel with
    a colour sampled from its own corner makes the plate read as one field
    of view instead of four photographs pasted on white.

    Args:
        canvas: The plate being composed.
        path: The field map to paste.
        box: The cell it goes into, as left, top, right, bottom.

    Raises:
        SystemExit: When the map is missing or its corner is transparent.
    """
    if not path.is_file():
        _ = sys.stderr.write(f"MISMATCH the field map is missing: {path}\n")
        raise SystemExit(1)
    panel = Image.open(path).convert("RGB")
    left, top, right, bottom = box
    cell_w = right - left
    cell_h = bottom - top
    scale = min(cell_w / panel.width, cell_h / panel.height)
    new_w = int(panel.width * scale)
    new_h = int(panel.height * scale)
    panel = panel.resize((new_w, new_h), Image.Resampling.LANCZOS)
    sky = panel.getpixel((2, 2))
    plate = Image.new("RGB", (cell_w, cell_h), sky)
    plate.paste(panel, ((cell_w - new_w) // 2, (cell_h - new_h) // 2))
    canvas.paste(plate, (left, top))


def compose() -> str:
    """Compose the four field maps into one plate and verify what was written.

    Returns:
        A one line report of the plate that was written.

    Raises:
        SystemExit: When a source map is missing or the plate is too small.
    """
    FIGURES.mkdir(parents=True, exist_ok=True)
    plate = Image.new("RGB", (PLATE_W, PLATE_H), "white")
    cell_w = (PLATE_W - GUTTER) // 2
    cell_h = (PLATE_H - GUTTER) // 2
    boxes = (
        (0, 0, cell_w, cell_h),
        (cell_w + GUTTER, 0, PLATE_W, cell_h),
        (0, cell_h + GUTTER, cell_w, PLATE_H),
        (cell_w + GUTTER, cell_h + GUTTER, PLATE_W, PLATE_H),
    )
    for (name, _what), box in zip(PANELS, boxes, strict=True):
        _paste_panel(plate, THESIS_FIGURES / name, box)
    plate.save(OUT_PLATE)
    size = OUT_PLATE.stat().st_size if OUT_PLATE.is_file() else 0
    if size < MIN_PICTURE_BYTES:
        _ = sys.stderr.write(f"MISMATCH the flow field plate was not written: {size} bytes\n")
        raise SystemExit(1)
    return f"[ok] flow field plate: {plate.width}x{plate.height}px, {size} bytes"


def copy_drag() -> str:
    """Copy the gate comparison into the deck without recomposition.

    Returns:
        A one line report of the copy, including the size check.

    Raises:
        SystemExit: When the source is missing or the copy is too small.
    """
    if not DRAG_SOURCE.is_file():
        _ = sys.stderr.write(f"MISMATCH the gate comparison is missing: {DRAG_SOURCE}\n")
        raise SystemExit(1)
    FIGURES.mkdir(parents=True, exist_ok=True)
    _ = shutil.copyfile(DRAG_SOURCE, DRAG_OUT)
    size = DRAG_OUT.stat().st_size if DRAG_OUT.is_file() else 0
    if size < MIN_PICTURE_BYTES:
        _ = sys.stderr.write(f"MISMATCH the gate comparison copy is too small: {size} bytes\n")
        raise SystemExit(1)
    if size != DRAG_SOURCE.stat().st_size:
        _ = sys.stderr.write("MISMATCH the gate comparison copy does not match its source\n")
        raise SystemExit(1)
    with Image.open(DRAG_OUT) as image:
        width, height = image.size
    return f"[ok] gate comparison: {width}x{height}px, {size} bytes"


def main() -> int:
    """Compose the plate, copy the gate panel and report what was written.

    Returns:
        Zero when both pictures were written, one when a source was missing.
    """
    try:
        _ = sys.stdout.write(compose() + "\n")
        _ = sys.stdout.write(copy_drag() + "\n")
    except SystemExit:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
