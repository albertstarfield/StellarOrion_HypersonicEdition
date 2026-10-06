#!/usr/bin/env python3
"""Measure the rendered geometry of the DSMC repeat loop against the box column.

WHY THIS TOOL EXISTS
====================
matplotlib applies an ``arc3`` connection style in DISPLAY space, so the bow
of an annotated curve in data coordinates is not the bow that reaches the
renderer. Measured on the saved PNG, a drawn bow came out far deeper than the
data space curvature, and an arrow endpoint landed several pixels right of its
data position. An analytic assertion in data space therefore describes a curve
that is never drawn. This tool measures the SAVED PNG, which is the only
ground truth, and the generator that writes that PNG calls this same module,
so the two can never disagree about the same image.

WHAT THE DESIGN REQUIRES, AND HOW IT IS MEASURED
=================================================
A repeat loop must do two things at once: bow away from the box column so the
curve is visibly separate from the boxes, and touch the box column at exactly
two connectors, its dashed tail leaving the convergence box and its arrowhead
landing on the movement box. One distance cannot express both, because an
intended touch has a distance of zero. The measurements are therefore split
into the two properties the design actually has:

``sep_gap_px``
    The MEDIAN white run between the border core and the loop ink over the
    loop rows. The median is used rather than the widest run because the two
    rotated Repeat labels are also red ink and sit to the right of the
    curve, so the widest run is reported by the labels rather than by the
    geometry being checked. The labels occupy a small minority of rows, so
    the median is unaffected by them, and a bow that hugs the border drives
    the median down instead of up.

``touch_rows``
    The number of loop rows whose gap is at most one pixel, that is rows
    where the loop ink is flush with or merged into the border. Two
    connectors account for a small number of rows each; a merged bow
    accounts for a long run, which ``touch_run`` also reports.

AXIOMS
======
1. The rendered PNG is the ground truth for the drawn geometry.
2. The seven boxes carry six distinct border colours and one shared red with
   the loop, so the box edge is found from the six non-red borders and the
   loop from red only.
3. A fully saturated stroke core sits inside an antialiased edge, so a colour
   threshold locates the core of the border and understates its outer edge by
   about a pixel. The measurement is therefore taken from the core column and
   tolerates that one pixel, which is immaterial against an eight pixel floor.

THEORIES
========
1. If the loop bows clear of the boxes, then some row of the loop has a wide
   white run between border ink and loop ink, and the widest such run is a
   lower bound on the visible separation at the apex.
2. If the loop instead runs along the border, then most of its rows sit flush
   against the border, so the count of flush rows rises far past what two
   connectors can account for.

APPLICATIONS
============
1. Build time guard inside ``make_dsmc_flowchart.py`` after the figure is
   saved, so a bad bow fails generation instead of reaching the thesis.
2. Standalone audit of any rendered copy of the flowchart, including the
   superseded artwork, which it reports as a failure by design.

CITATIONS
=========
- Pillow 12.3.0, https://pillow.readthedocs.io/en/stable/
- NumPy 2.x, https://numpy.org/doc/stable/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Median white run required between the border and the loop ink, in rendered
# pixels. Eight pixels is about 1.9 pt at 300 dpi, which reads as a visible
# separation rather than a touch.
MIN_SEP_GAP_PX = 8

# Upper bound on flush rows. Each connector is one stroke wide: the dashed
# tail spans about six rows at 300 dpi and the arrowhead about ten, so two
# connectors account for fewer than forty rows. A merged bow spans a large
# fraction of the loop height, and measured 85 rows on the old artwork.
MAX_TOUCH_ROWS = 80

# A gap of this many pixels or fewer counts as flush rather than separated.
FLUSH_PX = 1

# Border colours of the seven boxes, excluding the red used by the loop.
BORDER_RGB = (
    (59, 130, 246),  # blue
    (34, 197, 94),  # green
    (245, 158, 11),  # amber
    (236, 72, 153),  # pink
    (99, 102, 241),  # indigo
    (168, 85, 247),  # purple
)
BORDER_TOL = 30
LOOP_RGB = (239, 68, 68)
LOOP_TOL = 70
MIN_COL_SEGMENT = 20


def near(rgb: np.ndarray, target: tuple[int, int, int], tol: int) -> np.ndarray:
    """Return a boolean mask of pixels within ``tol`` per channel of target.

    Parameters
    ==========
    rgb : np.ndarray
        Image array of shape (height, width, 3) and dtype uint8.
    target : tuple of int
        Reference colour, one value per channel.
    tol : int
        Per channel tolerance.

    Returns
    =======
    np.ndarray
        Boolean mask of shape (height, width).
    """
    delta = np.abs(rgb.astype(np.int16) - np.asarray(target, dtype=np.int16))
    return (delta <= tol).all(axis=2)


def _right_border_x(rgb: np.ndarray) -> int:
    """Return the column of the saturated core of the boxes' right border.

    Parameters
    ==========
    rgb : np.ndarray
        Image array of shape (height, width, 3).

    Returns
    =======
    int
        Median rightmost saturated column of the six non-red border colours.

    Raises
    ======
    SystemExit
        If fewer than five of the six border colours agree within three
        pixels, which means the image does not look like the flowchart.
    """
    found = []
    for colour in BORDER_RGB:
        mask = near(rgb, colour, BORDER_TOL)
        columns = np.nonzero(mask.sum(axis=0) >= MIN_COL_SEGMENT)[0]
        if columns.size:
            found.append(int(columns.max()))
    if len(found) < 5:
        raise SystemExit(
            f"only {len(found)} box borders found, expected at least 5 of 6"
        )
    agreed = sum(1 for x in found if abs(x - found[0]) <= 3)
    if agreed < 5:
        raise SystemExit(f"box border columns disagree: {sorted(found)}")
    return int(np.median(found))


def measure(path: Path) -> dict[str, int]:
    """Measure the loop geometry of a rendered flowchart.

    Parameters
    ==========
    path : Path
        Path of the PNG to measure.

    Returns
    =======
    dict
        Keys ``box_right_x``, ``loop_left_x``, ``bow_gap_px``,
        ``touch_rows``, ``touch_run`` and ``loop_rows``, all in pixels.

    Raises
    ======
    SystemExit
        If the image has no loop ink to the right of the box column.
    """
    rgb = np.asarray(Image.open(path).convert("RGB"))
    box_right_x = _right_border_x(rgb)
    red = near(rgb, LOOP_RGB, LOOP_TOL)

    # Loop ink is red that sits to the right of the box column. The seventh
    # box shares that red but lies entirely within the column, so masking it
    # out keeps the box outline from being read as loop geometry.
    loop = red.copy()
    loop[:, : box_right_x + 1] = False
    rows = np.nonzero(loop.any(axis=1))[0]
    if rows.size == 0:
        raise SystemExit(f"{path.name}: no loop ink right of the box column")

    loop_left_x = int(np.nonzero(loop.any(axis=0))[0].min())
    gaps = []
    for row in rows:
        first = int(np.nonzero(loop[row])[0].min())
        gaps.append(first - box_right_x - 1)

    flush = [gap <= FLUSH_PX for gap in gaps]
    touch_rows = int(sum(flush))
    touch_run = 0
    run = 0
    for is_flush in flush:
        run = run + 1 if is_flush else 0
        touch_run = max(touch_run, run)

    return {
        "box_right_x": box_right_x,
        "loop_left_x": loop_left_x,
        "sep_gap_px": int(np.median(gaps)),
        "max_gap_px": int(max(gaps)),
        "touch_rows": touch_rows,
        "touch_run": int(touch_run),
        "loop_rows": int(rows.size),
    }


def main(argv: list[str]) -> int:
    """Measure the image named by ``argv[1]`` and report pass or fail.

    Parameters
    ==========
    argv : list of str
        Command line arguments; ``argv[1]`` is the PNG path.

    Returns
    =======
    int
        Zero when the apex clearance and the flush bound both hold, one
        otherwise, and two when the arguments or the file are unusable.
    """
    if len(argv) != 2:
        print("usage: measure_loop_gap.py <flowchart.png>")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"{path}: file not found")
        return 2
    result = measure(path)
    ok = (
        result["sep_gap_px"] >= MIN_SEP_GAP_PX
        and result["touch_rows"] <= MAX_TOUCH_ROWS
    )
    print(
        f"{path.name}: box border core x={result['box_right_x']}, "
        f"loop left ink x={result['loop_left_x']}, "
        f"median gap {result['sep_gap_px']}px floor {MIN_SEP_GAP_PX}px "
        f"(widest {result['max_gap_px']}px), flush rows "
        f"{result['touch_rows']} longest run {result['touch_run']} bound "
        f"{MAX_TOUCH_ROWS}, {result['loop_rows']} loop rows "
        f"-> {'PASS' if ok else 'FAIL'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))