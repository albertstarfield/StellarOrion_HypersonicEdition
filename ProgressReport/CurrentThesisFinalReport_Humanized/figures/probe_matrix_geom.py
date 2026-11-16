#!/usr/bin/env python3
"""Measure the coverage matrix artwork so its highlight and legend cannot drift.

WHY THIS EXISTS. The dashed red highlight and the legend key are the two
elements of figures/literature_review_map.png whose placement cannot be judged
from the generator source alone. A rendered-page audit of the first redraw
measured the outline straddling its row, with 1008 red pixels inside the row
above and 5 px of the bottom edge past the matrix, and measured a 0 px gap
between the matrix and the legend with the highlight stroke striking the legend
text. Those are pixel facts, so they are re-measured on the rendered PNG instead
of being assumed from the drawing code.

PARAMETERS. None. The PNG path is the module constant PNG_NAME and the
thresholds are the module constants.

RETURNS. 0 when every measurement clears its threshold, 1 when any measurement
fails, 2 when the artwork could not be measured at all.

EXCEPTIONS. RuntimeError when the PNG is missing, unreadable, or has no
measurable cells; the caller gets a non-zero return code rather than a trace.

CITATIONS.
- Pillow 12.3.0, image loading and array conversion,
  https://pillow.readthedocs.io/en/stable/
- NumPy 2.x, boolean column and row projections,
  https://numpy.org/doc/stable/

AXIOMS.
A1. The matrix body is drawn in exactly three flat fills plus a dash-free red
    highlight, so a colour match finds it without any layout assumption.
A2. The artwork is saved at 300 dpi, so one pixel is 1/300 in and a threshold
    expressed in inches converts by multiplying by 300.
A3. A measurement that cannot be taken is not a pass. Every guard below reports
    a number and compares it to a stated threshold.

THEORIES.
T1. The lowest band of cells is the This Work row, so the red outline must lie
    inside that band. An outline that reaches past it is either overlapping the
    previous row or leaving the matrix.
T2. Ink below the matrix that is not the matrix is legend ink, so the gap from
    the matrix bottom to the first legend pixel is the gutter.

APPLICATIONS.
A1. Run after every regeneration of the coverage matrix.
A2. Any figure where a dashed highlight and a key share a column of space.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

FIGDIR = Path(__file__).resolve().parent
PNG_NAME = "literature_review_map.png"
DPI = 300

# Flat fills of the matrix body, as RGB triples, and the tolerance of the match.
FULL_RGB = (26, 82, 118)
PART_RGB = (133, 193, 233)
NONE_RGB = (242, 244, 244)
HILITE_RGB = (231, 76, 60)
# The off white cell fill is only 13 units away from the white page on every
# channel, so its tolerance has to stay below that distance or the match swallows
# the entire background and the row split collapses. Measured here: a tolerance
# of 24 matched the page and reported 2 rows instead of 5.
FILL_TOL_FULL = 24
FILL_TOL_PART = 24
FILL_TOL_NONE = 6
HILITE_TOL = 70

# Span length clustering tolerance, in pixels, covering the antialiasing spread
# of a rasterised rectangle edge.
LENGTH_TOL_PX = 4

# Thresholds in pixels at DPI 300. INSET_TOL allows the stroke half width, since
# an inset outline is drawn with a 1.6 pt stroke centred on the inset edge.
INSET_TOL_PX = 6.0
MIN_GUTTER_PX = 30.0      # 0.10 in, 7.2 pt
MIN_TOP_OVERLAP_PX = 0.0


def near(img: np.ndarray, rgb: tuple[int, int, int], tol: int) -> np.ndarray:
    """Return a boolean mask of pixels within tol of rgb on all three channels.

    Parameters: img, an (h, w, 3) uint8 array; rgb, the target colour; tol, the
    per channel allowance.

    Returns: a boolean array of shape (h, w).

    Raises: nothing.
    """
    target = np.array(rgb, dtype=np.int16)
    delta = np.abs(img.astype(np.int16) - target)
    return np.all(delta <= tol, axis=2)


def bands(mask: np.ndarray, axis: int, minimum_fraction: float) -> list[tuple[int, int]]:
    """Return the inclusive index bands a mask occupies along one axis.

    A band is a maximal run of indices whose mask coverage reaches
    minimum_fraction of the busiest index, so the empty gutter between two cell
    rows is excluded and the gutter beside the label column is excluded.

    Parameters: mask, a boolean array; axis, the NumPy axis that is summed
    away, so 1 gives row bands and 0 gives column bands;
    minimum_fraction, the coverage fraction that counts as present.

    Returns: a list of (first, last) inclusive index pairs, empty if the mask
    is empty.

    Raises: nothing.
    """
    if not mask.any():
        return []
    counts = mask.sum(axis=axis)
    present = counts >= max(1, int(counts.max() * minimum_fraction))
    out: list[tuple[int, int]] = []
    start = None
    for idx, flag in enumerate(list(present) + [False]):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            out.append((start, idx - 1))
            start = None
    return out


def dominant(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return the largest group of equal length spans.

    The legend swatches are painted with the same three fills as the matrix
    cells, so a raw colour match finds them too. The matrix rows all share one
    height and its columns all share one width, so the largest group of equal
    length spans is the matrix and the swatches fall into a smaller group.
    Span lengths are clustered with a tolerance rather than bucketed, because a
    rasterised rectangle edge lands on a different pixel from one column to the
    next: the six measured column lengths were 138, 137, 138, 138, 137 and
    136 px, and the three legend swatches are 66 px. Bucketing that spread by
    four pixels still split the columns into two equal groups of three, which
    looks like a matrix with three columns.

    Parameters: spans, the bands found along one axis.

    Returns: the spans of the largest group, sorted by position.

    Raises: RuntimeError when spans is empty.
    """
    if not spans:
        raise RuntimeError("no spans to choose a dominant group from")
    clusters: list[list[tuple[int, int]]] = []
    means: list[float] = []
    for span in sorted(spans, key=lambda s: s[1] - s[0]):
        length = span[1] - span[0]
        if clusters and abs(length - means[-1]) <= LENGTH_TOL_PX:
            clusters[-1].append(span)
            means[-1] = sum(s[1] - s[0] for s in clusters[-1]) / len(clusters[-1])
        else:
            clusters.append([span])
            means.append(float(length))
    return sorted(max(clusters, key=len))


def measure(png: Path) -> dict[str, object]:
    """Measure the highlight box, the last row and the legend gutter.

    Parameters: png, the artwork path.

    Returns: a dict with keys rows, cols, row_top, row_bottom, matrix_left,
    matrix_right, hilite, gutter_px and hilite_below_rows.

    Raises: RuntimeError when the file is missing, unreadable, or has no cells.
    """
    if not png.is_file():
        raise RuntimeError(f"missing artwork: {png}")
    try:
        img = np.asarray(Image.open(png).convert("RGB"))
    except Exception as exc:                      # noqa: BLE001 report and stop
        raise RuntimeError(f"cannot read {png}: {exc}") from exc

    cells = (near(img, FULL_RGB, FILL_TOL_FULL)
             | near(img, PART_RGB, FILL_TOL_PART)
             | near(img, NONE_RGB, FILL_TOL_NONE))
    if not cells.any():
        raise RuntimeError(f"no matrix cells found in {png}")
    red = near(img, HILITE_RGB, HILITE_TOL)

    rows = dominant(bands(cells, 1, 0.30))
    cols = dominant(bands(cells, 0, 0.30))
    if len(rows) != 5 or len(cols) != 6:
        raise RuntimeError(
            f"expected 5 rows and 6 columns, found {len(rows)} and {len(cols)}")

    row_top, row_bottom = rows[-1]
    matrix_left, matrix_right = cols[0][0], cols[-1][1]
    if not red.any():
        raise RuntimeError("no red highlight stroke found")

    rys, rxs = np.nonzero(red)
    hilite = (int(rxs.min()), int(rys.min()), int(rxs.max()), int(rys.max()))

    # The cell mask also matches the three legend swatches, which reuse the same
    # fills, so the last FILLED row must be sought inside the detected matrix
    # band only. Searching the whole image put the reference row in the legend,
    # which silently reported an empty band below the matrix and a gutter of -1.
    matrix = np.zeros_like(cells)
    matrix[rows[0][0]:rows[-1][1] + 1, matrix_left:matrix_right + 1] = True
    matrix &= cells
    # Ink is summed as int32 so the test cannot wrap on a uint8 accumulator.
    dark = img.astype(np.int32).sum(axis=2) < 200
    # The last FILLED row sits above the bottom gridline, whose own stroke
    # reaches a few pixels lower, and the gutter must be measured from that
    # stroke because it is the last ink the matrix itself draws. Searching
    # only the matrix column span keeps the legend swatch borders, which sit
    # to the LEFT of the matrix, out of the reference.
    fill_bottom = int(np.nonzero(matrix.any(axis=1))[0].max())
    ink_in_span = dark[:, matrix_left:matrix_right + 1]
    window = ink_in_span[fill_bottom:fill_bottom + 10, :].any(axis=1)
    matrix_bottom_px = (fill_bottom + int(np.nonzero(window)[0].max()) + 1
                       if window.any() else fill_bottom + 1)
    below = np.zeros_like(cells)
    below[matrix_bottom_px:, :] = True
    legend_ink = below & dark
    gutter = (int(np.nonzero(legend_ink.any(axis=1))[0].min())
              - matrix_bottom_px) if legend_ink.any() else -1

    return {
        "rows": len(rows), "cols": len(cols),
        "row_top": row_top, "row_bottom": row_bottom,
        "matrix_left": matrix_left, "matrix_right": matrix_right,
        "matrix_bottom": matrix_bottom_px,
        "hilite": hilite,
        "hilite_below_rows": int(rys.max()) - row_bottom,
        "hilite_into_row_above": row_top - int(rys.min()),
        "red_in_legend": int((red & below).sum()),
        "gutter_px": int(gutter),
    }


def main() -> int:
    """Measure the artwork and report a PASS or FAIL verdict.

    Returns: 0 PASS, 1 FAIL, 2 measurement failure.

    Raises: nothing; measurement failures are caught and reported.
    """
    try:
        m = measure(FIGDIR / PNG_NAME)
    except RuntimeError as exc:
        print(f"MEASURE FAIL: {exc}")
        return 2

    print(f"matrix {m['rows']} rows x {m['cols']} columns, "
          f"x[{m['matrix_left']},{m['matrix_right']}] y[{m['row_top']},"
          f"{m['row_bottom']}]")
    print(f"highlight bbox x[{m['hilite'][0]},{m['hilite'][2]}] "
          f"y[{m['hilite'][1]},{m['hilite'][3]}]")
    checks = [
        ("highlight stays inside the This Work row",
         m["hilite_into_row_above"] <= INSET_TOL_PX),
        ("highlight does not run past the matrix bottom",
         m["hilite_below_rows"] <= INSET_TOL_PX),
        ("no highlight stroke in the legend band", m["red_in_legend"] == 0),
        (f"legend gutter at least {MIN_GUTTER_PX:.0f} px",
         int(m["gutter_px"]) >= MIN_GUTTER_PX),
    ]
    width = max(len(name) for name, _ in checks)
    failed = 0
    for name, ok in checks:
        failed += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"highlight into the row above {m['hilite_into_row_above']} px "
          f"(bound {INSET_TOL_PX:.0f}), past the matrix bottom "
          f"{m['hilite_below_rows']} px, red pixels in the legend "
          f"{m['red_in_legend']}, legend gutter {m['gutter_px']} px")
    if failed:
        print(f"VERDICT: FAIL ({failed} of {len(checks)} checks)")
        return 1
    print("VERDICT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())