#!/usr/bin/env python3
"""Shared printed-layout measurement helpers for the thesis figure generators.

PURPOSE
=======
Two generators (generate_sutton_graves_parametric.py and make_fignew.py) must
prove, before they ship, that no two printed labels collide and that no printed
glyph falls below the 8 pt legibility floor. Both need the same arithmetic, so
it lives here once instead of being copied into each script.

WHY A LIBRARY AND NOT A LOOK AT THE PNG
=======================================
Reading a rendered PNG cannot attribute a collision to a cause: the measured
pixel distance mixes three independent factors, namely the tight crop, the save
dpi, and the LaTeX placement scale. Asking matplotlib for the real text extents
keeps the typography in absolute points, and the single remaining unknown, the
placement scale, is then one multiplication that this module computes from the
saved file.

AXIOMS
======
A1. Text extents are only defined after a draw, so every function here requires
    a drawn canvas and says so in its contract.
A2. The printed size of a declared point size is `declared * scale`, where
    `scale = print_width_in / (saved_px / dpi)`. This is the same definition
    make_fignew.save() prints, so the two can never disagree.
A3. A mathtext sub or superscript prints at SHRINK_FACTOR times its parent, so
    a string carrying one cannot be judged by its parent size alone.

THEORIES
========
T1. Two adjacent labels collide on the page if and only if their printed
    bounding boxes overlap, so the gap between consecutive boxes, measured in
    printed points, decides the question exactly.
T2. An arrowhead is a filled patch of known size, so a curve is occluded only if
    a curve passes within one arrowhead of the arrow target. Measuring the
    point-to-polyline distance therefore settles occlusion without inspecting
    pixels.

APPLICATIONS
============
A1/A2 are used by both generators before their save() call. T1 is used to gate
the gate-figure category labels and the panel (b) radius ticks. T2 is used to
prove that the panel (b) annotation arrow does not cover the V = 3 curve.

CITATIONS
=========
[Citation: Matplotlib v3.11.2 - Artist.get_window_extent and
          FigureCanvasAgg.get_renderer - https://matplotlib.org/stable/api/]
[Citation: Pillow v12.3.0 - Image.open for the saved pixel width -
          https://pillow.readthedocs.io/en/stable/reference/Image.html]

PARAMETERS
==========
Every function takes only its measurement target and the scale factor; no
function mutates the figure it measures.

RETURNS
=======
Distances and sizes are returned in PRINTED POINTS (pt), never in pixels, so
that callers compare like with like.

EXCEPTIONS
==========
RuntimeError: if the canvas has not been drawn, or if a requested artist is
    absent, or if the saved PNG cannot be read. Callers must not fall back to a
    default, because a silent default here would hide exactly the defect these
    helpers exist to catch.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from PIL import Image

try:  # pragma: no cover - import shape differs between matplotlib releases
    from matplotlib._mathtext import SHRINK_FACTOR
except ImportError:  # pragma: no cover
    SHRINK_FACTOR = 0.7


def effective_scale(png_path: str, print_width_in: float, dpi: int) -> float:
    """Return the placement scale of a saved PNG: printed width / native width.

    :param png_path: path to the saved PNG.
    :param print_width_in: width in inches at which LaTeX includes the PNG.
    :param dpi: dpi used when the PNG was saved.
    :type png_path: str
    :type print_width_in: float
    :type dpi: int
    :returns: dimensionless multiplier applied to every declared point size.
    :rtype: float
    :raises RuntimeError: if the PNG is missing or unreadable, or if its width
        is not positive.
    """
    with Image.open(png_path) as img:
        px = img.size[0]
    if px <= 0:
        raise RuntimeError("%s reports width %d px" % (png_path, px))
    return print_width_in / (px / float(dpi))


def renderer_of(fig: Any) -> Any:
    """Return the renderer of a drawn canvas, or raise if it is not drawn.

    :param fig: the matplotlib Figure to query.
    :returns: a Renderer usable for get_window_extent.
    :raises RuntimeError: if no renderer is available yet.
    """
    canvas = getattr(fig, "canvas", None)
    if canvas is None:
        raise RuntimeError("figure has no canvas; nothing has been drawn")
    rend = getattr(canvas, "get_renderer", lambda: None)()
    if rend is None:
        raise RuntimeError("canvas has no renderer; call fig.canvas.draw() first")
    return rend


def x_tick_label_gaps_pt(
    ax: Any, fig: Any, scale: float
) -> list[tuple[str, str, float]]:
    """Return the printed gap between every pair of adjacent x tick labels.

    Labels that are hidden or carry no text are skipped, because an invisible
    label cannot collide with anything.

    :param ax: the axes whose x tick labels are measured.
    :param fig: the parent figure, needed for its dpi.
    :param scale: placement scale from effective_scale.
    :returns: list of (left label, right label, gap in printed pt), sorted left
        to right along the axis.
    :rtype: list[tuple[str, str, float]]
    :raises RuntimeError: if fewer than two visible labels are present, since a
        gap question cannot be answered without a pair.
    """
    rend = renderer_of(fig)
    dpi = float(fig.dpi)
    boxes = []
    for text in ax.get_xticklabels():
        if not text.get_visible():
            continue
        label = text.get_text()
        if not label.strip():
            continue
        ext = text.get_window_extent(renderer=rend)
        boxes.append((ext.x0, ext.x1, label))
    if len(boxes) < 2:
        raise RuntimeError(
            "need two visible x tick labels to measure a gap, found %d"
            % len(boxes)
        )
    boxes.sort()
    out: list[tuple[str, str, float]] = []
    for left, right in zip(boxes, boxes[1:]):
        gap_px = right[0] - left[1]
        out.append((left[2], right[2], gap_px * 72.0 / dpi * scale))
    return out


def smallest_text_pt(fig: Any, scale: float) -> tuple[float, str]:
    """Return the smallest printed text size in the figure and what produced it.

    A string that contains a mathtext sub or superscript is judged at
    SHRINK_FACTOR of its parent, because that is how matplotlib draws it.

    :param fig: the figure to scan.
    :param scale: placement scale from effective_scale.
    :returns: (printed size in pt, human readable description of the artist).
    :rtype: tuple[float, str]
    :raises RuntimeError: if the figure holds no text at all.
    """
    import matplotlib

    worst = None
    worst_why = ""
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible():
            continue
        content = artist.get_text()
        if not content.strip():
            continue
        declared = float(artist.get_fontsize()) * scale
        # A mathtext sub/superscript is the only construct that shrinks below
        # the declared size; detect it by the underscore or caret that
        # introduces it inside a dollar-delimited span.
        shrinks = False
        for chunk in content.split("$"):
            if len(chunk) > 1 and ("_" in chunk or "^" in chunk):
                shrinks = True
        printed = declared * (SHRINK_FACTOR if shrinks else 1.0)
        why = "%r fontsize %.1f%s" % (
            content[:40],
            artist.get_fontsize(),
            " with mathtext script" if shrinks else "",
        )
        if worst is None or printed < worst:
            worst = printed
            worst_why = why
    if worst is None:
        raise RuntimeError("figure contains no visible text to measure")
    return worst, worst_why


def _point_segment_distance(px: float, py: float,
                            ax0: float, ay0: float,
                            ax1: float, ay1: float) -> float:
    """Return the distance from a point to one line segment.

    :param px: point x.
    :param py: point y.
    :param ax0: segment start x.
    :param ay0: segment start y.
    :param ax1: segment end x.
    :param ay1: segment end y.
    :returns: the shortest distance in the same units as the inputs.
    :rtype: float
    """
    dx = ax1 - ax0
    dy = ay1 - ay0
    denom = dx * dx + dy * dy
    if denom <= 0.0:
        return math.hypot(px - ax0, py - ay0)
    t = ((px - ax0) * dx + (py - ay0) * dy) / denom
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax0 + t * dx), py - (ay0 + t * dy))


def min_distance_to_lines_pt(
    ax: Any, fig: Any, point_data: tuple[float, float], scale: float,
    skip: Sequence[Any] = (),
) -> tuple[float, str]:
    """Return the printed distance from a data point to the nearest drawn line.

    Exact for polylines: each consecutive pair of transformed vertices is
    treated as one segment and the true point-to-segment distance is taken.

    :param ax: the axes holding the lines and defining the data transform.
    :param fig: the parent figure, needed for its dpi.
    :param point_data: the (x, y) data coordinate to test.
    :param scale: placement scale from effective_scale.
    :param skip: line objects to ignore, typically the reference lines such as
        a dashed threshold that the arrow is meant to point at.
    :returns: (distance in printed pt, label of the nearest line).
    :rtype: tuple[float, str]
    :raises RuntimeError: if no eligible line is present.
    """
    rend = renderer_of(fig)
    dpi = float(fig.dpi)
    tpoint = ax.transData.transform(point_data)
    px = float(tpoint[0])
    py = float(tpoint[1])
    best = None
    best_label = ""
    for line in ax.lines:
        if line in skip:
            continue
        if not line.get_visible():
            continue
        verts = line.get_transform().transform(line.get_xydata())
        if len(verts) < 2:
            continue
        label = line.get_label() or "(unlabelled line)"
        for k in range(len(verts) - 1):
            dist = _point_segment_distance(
                px, py,
                float(verts[k][0]), float(verts[k][1]),
                float(verts[k + 1][0]), float(verts[k + 1][1]),
            )
            if best is None or dist < best:
                best = dist
                best_label = label
    if best is None:
        raise RuntimeError("no eligible line to measure a distance against")
    return best * 72.0 / dpi * scale, best_label
