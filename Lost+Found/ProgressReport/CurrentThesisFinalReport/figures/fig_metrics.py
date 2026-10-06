#!/usr/bin/env python3
"""Shared printed-layout measurement helpers for the thesis figure generators.

PURPOSE
=======
Every figure generator in this directory must prove, before it ships, that no
two printed labels collide, that no printed glyph falls below the 8 pt
legibility floor, and that nothing a reader must read is printed outside the
space the layout reserved for it. All of those need the same arithmetic, so it
lives here once instead of being copied into each script.

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
A4. Two printed labels are legible together if and only if their bounding boxes
    are disjoint, so a positive box overlap is the collision and not a proxy
    for it. Tick-gap tests cannot see this class at all: they compare a tick to
    its neighbour, while a legend title over an axis label, or a panel title
    over its own last word, involves two artists that no gap test pairs.
A5. An artist placed by an anchor is placed by that anchor, not by its extent,
    so a label can be anchored well inside a panel and still print outside it.
    The reserved space is the container rectangle, so the test is against the
    container and not against the anchor.

THEORIES
========
T1. Two adjacent labels collide on the page if and only if their printed
    bounding boxes overlap, so the gap between consecutive boxes, measured in
    printed points, decides the question exactly.
T2. An arrowhead is a filled patch of known size, so a curve is occluded only if
    a curve passes within one arrowhead of the arrow target. Measuring the
    point-to-polyline distance therefore settles occlusion without inspecting
    pixels.
T3. By A4, an all-pairs box test over the visible non-empty text of a figure is
    a complete collision test, and it costs one draw, so there is no reason for
    a generator to test only the pairs it happens to know about.
T4. By A5, containment must be tested per container. An annotation frame is
    contained in its own axes; a legend is contained in the dedicated cell the
    gridspec gave it. Both are the same arithmetic against a different rectangle.

APPLICATIONS
============
A1/A2 are used by every generator before its save() call. T1 is used to gate the
gate-figure category labels and the panel (b) radius ticks. T2 proves that the
panel (b) annotation arrow does not cover the V = 3 curve. T3 and T4 gate every
other generator and are the checks whose absence let a legend title overprint an
axis label and an annotation frame cross a spine on a rendered page.

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

import itertools
import math
from typing import Any, Sequence

from PIL import Image

try:  # pragma: no cover - import shape differs between matplotlib releases
    from matplotlib._mathtext import SHRINK_FACTOR
except ImportError:  # pragma: no cover
    SHRINK_FACTOR = 0.7

# Smallest spacing between log ticks, in decades, that the picker will accept.
# The first value tried, 0.15, was derived from the tick mark spacing rather
# than from the label spacing and was therefore far too strict: over the 0.47
# decade heat-flux windows it works out to about 50 printed points between two
# 10 pt labels, so it threw away ticks and left panel 1 with two labels and
# panel 2 with two. The binding constraint is the printed gap between the
# labels, so the floor is stated in decades only because that is the unit the
# picker works in, and it is set to 0.05, which is about 17 printed points on
# the shortest log panel in this project and about one and a half label heights.
MIN_DECADE_STEP = 0.05

# Never more ticks than this on one axis, whatever the requested target, so a
# short window cannot be filled edge to edge with numbers.
MAX_LOG_TICKS = 12


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


def same_row_gaps_pt(
    fig: Any, scale: float, min_gap_pt: float = 2.0
) -> list[tuple[str, str, float]]:
    """Return printed gaps between horizontally neighbouring labels on one row.

    WHY A SECOND GAP TEST AND NOT AN EXTENSION OF THE FIRST: x_tick_label_gaps_pt
    is exact because the labels it pairs share one axis and therefore one row.
    The defect it cannot see is two labels from DIFFERENT axes that end up in the
    same horizontal band, which is exactly what a multi-panel figure produces.
    Measured on the central composite screen, the panel 2 and panel 3 x labels
    were separated by a single white column and rendered as (m)Toroid, while
    every within-axis tick gap passed and no bounding box intersected, because
    the two labels were one column apart rather than touching. A box-overlap
    test cannot see a gap at all, so this test exists to place a floor under it.

    AXIOM A9: two labels are on the same row when their vertical extents
    overlap by at least half the height of the smaller one, so a label and the
    tick row beneath it are not paired.

    AXIOM A10: the gap is measured between the RIGHT edge of the left label and
    the LEFT edge of the right label, so a negative result means the boxes
    intersect and the caller should read it as an overlap, not as spacing.

    :param fig: the figure to scan; every visible non-empty Text is considered.
    :param scale: placement scale from effective_scale.
    :param min_gap_pt: only gaps below this many printed points are reported,
        because a wide gap is not a defect.
    :returns: list of (left owner + " | " + text, right owner + " | " + text,
        gap in printed pt), narrowest gap first.
    :rtype: list[tuple[str, str, float]]
    """
    import matplotlib

    rend = renderer_of(fig)
    per_pt = 72.0 / float(fig.dpi) * scale
    clipped = clipped_tick_ids(fig)
    boxes = []
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible() or id(artist) in clipped:
            continue
        content = artist.get_text()
        if not content.strip():
            continue
        ext = artist.get_window_extent(renderer=rend)
        boxes.append((ext.x0 * per_pt, ext.x1 * per_pt,
                      ext.y0 * per_pt, ext.y1 * per_pt,
                      owner_label(artist, fig) + " | "
                      + content.replace("\n", " / ")))
    out: list[tuple[str, str, float]] = []
    for left, right in itertools.combinations(boxes, 2):
        overlap = min(left[3], right[3]) - max(left[2], right[2])
        smaller = min(left[3] - left[2], right[3] - right[2])
        if overlap < 0.5 * smaller:
            continue  # not the same row, so spacing between them means nothing
        gap = right[0] - left[1]
        if left[0] > right[0]:
            gap = left[0] - right[1]
            left, right = right, left
        if gap < min_gap_pt:
            out.append((left[4], right[4], gap))
    out.sort(key=lambda item: item[2])
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


def owner_label(text: Any, fig: Any) -> str:
    """Return a short identifier for the artist that owns a Text.

    WHY THIS EXISTS: two panels of the same figure carry the same axis label
    and the same tick values, so a collision report that carries only the
    string cannot say WHICH artist met WHICH. A first version of
    ``text_overlaps_pt`` keyed its box table by string and silently overwrote
    one artist with another, so it reported another object's coordinates. The
    owner must therefore come from the artist's own membership in its axes,
    never from a text search.

    :param text: the Text artist to describe.
    :param fig: the figure it belongs to, used to number the axes.
    :returns: a label such as ``axes[1]:ylabel``, ``axes[2]:ytick``,
        ``axes[0]:title``, ``figure`` or ``detached``.
    :rtype: str
    """
    owner = text.axes
    if owner is None:
        # Matplotlib leaves .axes unset on some tick labels, so fall back to
        # an identity search over the tick lists. A text comparison would be
        # wrong here: two panels carry the same label text.
        for index, candidate in enumerate(fig.axes):
            for axis in (candidate.xaxis, candidate.yaxis):
                for minor in (False, True):
                    if any(text is tick for tick in axis.get_ticklabels(minor=minor)):
                        return "axes[%d]:%stick" % (index, "x" if axis is candidate.xaxis else "y")
            # Matplotlib leaves .axes unset on axis labels and titles too, so
            # those roles are matched by identity here as well.
            if text is candidate.xaxis.label:
                return "axes[%d]:xlabel" % index
            if text is candidate.yaxis.label:
                return "axes[%d]:ylabel" % index
            if text is candidate.title:
                return "axes[%d]:title" % index
            if text is candidate.xaxis.get_offset_text():
                return "axes[%d]:xoffset" % index
            if text is candidate.yaxis.get_offset_text():
                return "axes[%d]:yoffset" % index
        return "figure"
    try:
        name = "axes[%d]" % fig.axes.index(owner)
    except ValueError:
        return "detached"
    if text in owner.get_xticklabels(minor=True):
        return name + ":xminor"
    if text in owner.get_yticklabels(minor=True):
        return name + ":yminor"
    if text in owner.get_xticklabels():
        return name + ":xtick"
    if text in owner.get_yticklabels():
        return name + ":ytick"
    if text is owner.xaxis.label:
        return name + ":xlabel"
    if text is owner.yaxis.label:
        return name + ":ylabel"
    if text is owner.title:
        return name + ":title"
    if text is owner.xaxis.get_offset_text():
        return name + ":xoffset"
    if text is owner.yaxis.get_offset_text():
        return name + ":yoffset"
    return name


def clipped_tick_ids(fig: Any) -> set[int]:
    """Return the ids of tick labels that the axes clips away entirely.

    WHY THIS EXISTS: ``get_window_extent`` reports where a text WOULD sit and
    knows nothing about clipping, so a tick label whose tick matplotlib has
    filtered out still returns a box. On the gate figure the 250 label survived
    an explicit ``set_ylim`` that ended at 237.97, and a differential ink
    measurement with the title emptied and replaced proved the band held 0 dark
    pixels, so nothing was drawn there. On the Sutton-Graves panel (b) the same
    effect produced four phantom labels reading 0, 5, 10 and 15, evenly spaced
    across the canvas in the row that holds the real 0.1 to 3 tick labels, and
    the collision guard reported a 9.97 pt overlap between a phantom and a real
    label. A guard that counts clipped labels trains its reader to ignore it,
    so the fix belongs here and not in the caller.

    AXIOM A7: a tick label is drawn only when matplotlib keeps its tick, and
    matplotlib drops any tick whose data value lies outside the axis view
    interval, so a label left over from an earlier autoscaled window is inked
    nowhere and cannot collide with anything.

    AXIOM A8: a tick label does NOT carry its data value. Measured on the gate
    figure, label.get_position() returned (0.0, 0.0) for every one of its six y
    tick labels, including the 250 label whose real value is 250, because the
    position is assigned during the draw and is not stored on the artist. An
    earlier version of this function therefore compared 0.0 against the axis
    limits, flagged nothing, and silently never excluded anything on any axis
    that was not switched off. The data value cannot be read from the label, so
    the test is made geometric instead.

    :param fig: the figure whose axes are scanned.
    :returns: the set of ``id()`` values of tick labels outside their window.
    :rtype: set[int]
    """
    clipped: set[int] = set()
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    scale = 72.0 / fig.dpi
    for ax in fig.axes:
        if not ax.axison:
            # An axes switched off with axis("off") inks nothing, including its
            # tick labels, but those artists still report get_visible() True,
            # so every one of them is skipped here rather than in every caller.
            for axis in (ax.xaxis, ax.yaxis):
                for minor in (False, True):
                    for label in axis.get_ticklabels(minor=minor):
                        clipped.add(id(label))
            continue
        # The axes rectangle in printed points. A y tick label is drawn only if
        # its own box sits inside the vertical span of the axes, and an x tick
        # label only if its box sits inside the horizontal span, so each axis is
        # tested against the dimension it moves in.
        frame = ax.get_window_extent(renderer=rend)
        spans = {"y": (frame.y0 * scale, frame.y1 * scale),
                 "x": (frame.x0 * scale, frame.x1 * scale)}
        for key, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            low, high = spans[key]
            tol = 1e-6 * max(1.0, abs(high - low))
            for minor in (False, True):
                for label in axis.get_ticklabels(minor=minor):
                    if not label.get_visible() or not label.get_text():
                        continue
                    box = label.get_window_extent(renderer=rend)
                    centre = (box.y0 + box.y1) / 2 * scale if key == "y" \
                        else (box.x0 + box.x1) / 2 * scale
                    if centre < low - tol or centre > high + tol:
                        clipped.add(id(label))
    return clipped


def axes_without_tick_labels(fig: Any) -> list[tuple[int, str, str, list[float]]]:
    """Return every visible axis whose numeric ticks all fall outside its window.

    WHY THIS EXISTS: a rendered audit of the two-panel heat-flux figure found the
    second panel carrying tick marks and gridlines and NO numeric label, because
    its y window spans 150.8 to 446.4 and therefore contains no decade, so the
    default log locator offered 100 and 1000 and both lie outside. Every other
    guard passed that figure, because a missing label collides with nothing, sits
    at no size, and stays inside the canvas. Counting ``get_visible()`` labels
    also passes it, because the label artist reports visible True even when
    matplotlib filters its tick out of the draw, which an earlier draft of the
    probe did and which is how a false pass happens here.

    AXIOM A11: a tick label is drawn only when its locator value lies inside the
    axis window, so the number of reader-visible numeric labels on one axis
    equals the number of major locator values inside that window. Nothing else
    about the label, including its own visible flag, carries that information.

    :param fig: the drawn figure whose axes are scanned.
    :returns: one tuple per offending axis, ``(axes name such as "axes[1]:y",
        window text, major locator values)``. An axis with no locator value at
        all is returned too, because that is the same empty-axis defect. The
        name is qualified because a bare "y" cannot be acted on when a figure
        has more than one panel.
    :rtype: list[tuple[str, str, list[float]]]
    """
    offenders: list[tuple[str, str, list[float]]] = []
    fig.canvas.draw()
    for index, ax in enumerate(fig.axes):
        if not ax.axison:
            continue
        for key, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            low, high = sorted(axis.get_view_interval())
            locs = [float(v) for v in axis.get_majorticklocs()]
            inside = [v for v in locs if low <= v <= high]
            if inside:
                continue
            offenders.append((f"axes[{index}]:{key}",
                              f"window {low:.6g} to {high:.6g}", locs))
    return offenders


def _round_log_candidates(low: float, high: float) -> list[float]:
    """Return every round logarithmic value inside ``[low, high]``.

    WHY THE 1.x SERIES IS INCLUDED: the first version of this helper generated
    only one digit times a power of ten, which is the classical 1, 2, 5 decade
    mantissa family. Inside a window of 50.6 to 151.7 that family yields only
    60, 70, 80, 90 and 100, so the heat-flux panel 1 could show two ticks and
    the picker could not reach 110 through 150 at all, which is not a shortage
    of round numbers but a shortage of the KIND of round number this function
    was asked for. The 1.x mantissas are added per decade for that reason.

    :param low: the lower limit of the axis window.
    :param high: the upper limit of the axis window.
    :returns: ascending round values strictly inside the window, empty when the
        window spans no such value.
    :rtype: list[float]
    """
    found: list[float] = []
    first = int(math.floor(math.log10(low))) - 1
    last = int(math.ceil(math.log10(high))) + 1
    for exponent in range(first, last + 1):
        mantissas = [float("%de%d" % (tenths, exponent - 1))
                     for tenths in range(10, 20)]
        mantissas += [float("%de%d" % (digit, exponent)) for digit in range(2, 10)]
        for value in mantissas:
            if low * 1.0000001 < value < high * 0.9999999:
                found.append(value)
    return sorted(found)


def log_ticks_in_window(low: float, high: float, target: int = 4) -> list[float]:
    """Return round plain-digit log ticks that lie inside ``[low, high]``.

    WHY THIS EXISTS: on a log axis the printed distance between two ticks is
    proportional to the difference of their base-10 logarithms, so the ticks a
    reader finds evenly spaced are the ones evenly spaced in the EXPONENT. The
    first version solved that by placing ticks on exact powers of a fractional
    step, and it worked, and it printed 56.0138, 80.7665 and 116.457. Those are
    correct numbers and unreadable typography, so the candidate set is now the
    round numbers only: a single digit times a power of ten, which is what a
    reader can quote and compare.

    AXIOM A12: the tick set must lie strictly inside the window, because a tick
        exactly on a limit prints half its glyph against the spine, and the
        empty-axis test would then count a half-cut label as present.
    AXIOM A13: a printed axis label is a claim about a physical quantity, so its
        value is part of the content of the figure. 56.0138 asserts a precision
        the measurement does not have and is therefore a defect even though it
        lies inside the window.

    :param low: the lower limit of the axis window.
    :param high: the upper limit of the axis window.
    :param target: the desired count. The window is divided into that many equal
        bands in the exponent and one tick is taken per band; a tick closer than
        ``MIN_DECADE_STEP`` to its predecessor is dropped, because closer than
        that two numeric labels collide.
    :returns: ascending round tick values strictly inside the window, or an
        empty list when the window is degenerate.
    :rtype: list[float]
    :raises ValueError: when ``low`` or ``high`` is not positive, because a log
        axis cannot show a non-positive value.
    """
    if low <= 0.0 or high <= 0.0:
        raise ValueError(
            f"log ticks need positive limits, got {low!r} to {high!r}")
    if not high > low:
        return []
    lo_exp, hi_exp = math.log10(low), math.log10(high)
    candidates = _round_log_candidates(low, high)
    if not candidates:
        return []
    if len(candidates) <= target:
        return candidates
    # THE SUBSET SEARCH, AND WHY IT REPLACED THE PER-BAND GREEDY PICK. One tick
    # per equal band of the exponent is the obvious construction and it is the
    # wrong one here, because the candidate set is not uniform. Measured on the
    # heat-flux panel 2, whose window is 150.8 to 446.4 and whose round
    # candidates are 160, 170, 180, 190, 200, 300 and 400: four bands pick 170,
    # 200, 300, 400, whose exponent gaps are 0.071, 0.176 and 0.125, so the two
    # lowest labels nearly touch while the rest spread out. A reader judges an
    # axis by whether the ticks look evenly spaced, and they do not here. So the
    # picker now searches the round candidates for the subset of at most target
    # values whose exponent gaps deviate least from their own mean, and takes
    # the best subset over every count from three upward, because with two ticks
    # there is a single gap and therefore no deviation at all, which would make
    # every pair equally perfect and carry no information. On that window it
    # returns 200, 300, 400.
    exponents = [math.log10(v) for v in candidates]
    count = min(int(target), len(candidates), MAX_LOG_TICKS)
    best_set: list[float] = []
    best_score = float("inf")
    for size in range(3, count + 1):
        for combo in itertools.combinations(range(len(candidates)), size):
            gaps = [exponents[combo[i + 1]] - exponents[combo[i]]
                    for i in range(size - 1)]
            if min(gaps) < MIN_DECADE_STEP:
                continue
            mean = sum(gaps) / len(gaps)
            deviation = max(abs(g - mean) for g in gaps)
            # EVEN SPACING IS NOT ENOUGH ON ITS OWN. Judged on deviation alone
            # the search returned 1.6, 4 and 10 for a window of 1.5 to 2600, an
            # axis whose three perfectly even ticks stop at 10 while the data
            # runs past 2000, so the top two decades of the figure carry no
            # number at all. The span term charges half a decade for every
            # decade of window left unticked at each end, and it then returns
            # 2, 20, 200 and 2000 for that window.
            span_penalty = 0.5 * ((exponents[combo[0]] - lo_exp)
                                  + (hi_exp - exponents[combo[-1]]))
            score = deviation + span_penalty
            if score < best_score - 1e-12:
                best_score = score
                best_set = [candidates[i] for i in combo]
    if best_set:
        return best_set
    # The search found nothing, which means the window is too narrow for three
    # ticks that respect the spacing floor, so the sparse family is returned
    # whole rather than crowding the axis to fake a better count.
    return candidates


def text_overlaps_pt(
    fig: Any, scale: float, min_overlap_pt: float = 3.0
) -> list[tuple[str, str, float, float]]:
    """Return every pair of printed text labels whose bounding boxes overlap.

    AXIOM A4: two printed labels are legible together if and only if their
    bounding boxes are disjoint, so a positive overlap is the collision itself
    rather than a proxy for it. This is the guard the battery lacked, and its
    absence let a rendered page carry a legend title struck through an axis
    label, a panel title overprinted on its own last word, and two neighbouring
    axis labels separated by a single white column, all while every tick-gap
    and text-size check passed.

    AXIOM A6 (why the default tolerance is 3 pt): a matplotlib text extent
    includes the font's full ascent and descent, not the inked glyphs, so two
    labels on neighbouring rows report a few points of box overlap while their
    glyphs are plainly separated. At 13 pt Times the descent allowance is about
    3 pt, so ``min_overlap_pt`` defaults to 3.0 and sub-3 pt overlaps are
    reported as none. The exact spacing of labels that are meant to be adjacent
    is measured by x_tick_label_gaps_pt instead, which is exact because those
    labels share one row. This test is for the pairs no gap test pairs at all,
    namely a legend title against an axis label and an annotation against a
    tick label.

    :param fig: the figure to scan; every visible non-empty Text is tested.
    :param scale: placement scale from effective_scale.
    :param min_overlap_pt: ignore pairs whose overlap in either direction is
        below this many printed points.
    :returns: list of (owner_a + " | " + text_a, owner_b + " | " + text_b,
        overlap width pt, overlap height pt) sorted by the smaller overlap,
        largest first. Each side is prefixed by ``owner_label`` so two
        identically worded labels can still be told apart.
    :rtype: list[tuple[str, str, float, float]]
    """
    import matplotlib

    rend = renderer_of(fig)
    per_pt = 72.0 / float(fig.dpi) * scale
    clipped = clipped_tick_ids(fig)
    boxes = []
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible() or id(artist) in clipped:
            continue
        content = artist.get_text()
        if not content.strip():
            continue
        boxes.append(
            (
                artist.get_window_extent(renderer=rend),
                "%s | %s" % (owner_label(artist, fig), content),
            )
        )
    out: list[tuple[str, str, float, float]] = []
    for first in range(len(boxes)):
        for second in range(first + 1, len(boxes)):
            box_a, text_a = boxes[first]
            box_b, text_b = boxes[second]
            overlap_x = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            overlap_y = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if overlap_x <= 0.0 or overlap_y <= 0.0:
                continue
            width_pt = overlap_x * per_pt
            height_pt = overlap_y * per_pt
            if min(width_pt, height_pt) < min_overlap_pt:
                continue
            out.append((text_a, text_b, width_pt, height_pt))
    out.sort(key=lambda row: -min(row[2], row[3]))
    return out


def annotation_boxes_inside_axes_pt(
    ax: Any, fig: Any, scale: float, tol_pt: float = 0.0
) -> list[tuple[str, dict[str, float]]]:
    """Return every annotation on ``ax`` whose framed box leaves the axes.

    An annotation positioned in axes fraction is placed by its anchor, not by
    its width, so a long label anchored well inside the axes can still stick
    out of the left or right spine. On a rendered page that reads as a label
    printed across the neighbouring panel. Only artists that actually carry a
    frame patch are tested, because an unframed annotation has no box to leave.

    :param ax: the axes that owns the annotations.
    :param fig: the parent figure, needed for its dpi and renderer.
    :param scale: placement scale from effective_scale.
    :param tol_pt: how far outside the axes rectangle a box may reach, in
        printed points.
    :returns: list of (annotation text, {side: overflow in printed pt}) for
        every box that exceeds the tolerance.
    :rtype: list[tuple[str, dict[str, float]]]
    """
    rend = renderer_of(fig)
    per_pt = 72.0 / float(fig.dpi) * scale
    frame = ax.get_window_extent(renderer=rend)
    out: list[tuple[str, dict[str, float]]] = []
    for artist in ax.texts:
        if not artist.get_visible():
            continue
        patch = artist.get_bbox_patch()
        if patch is None:
            continue
        box = patch.get_window_extent(renderer=rend)
        over = {}
        for side, amount in (
            ("left", frame.x0 - box.x0),
            ("right", box.x1 - frame.x1),
            ("bottom", frame.y0 - box.y0),
            ("top", box.y1 - frame.y1),
        ):
            value = amount * per_pt
            if value > tol_pt:
                over[side] = value
        if over:
            out.append((artist.get_text(), over))
    return out


def legend_boxes_inside_axes_pt(
    ax: Any, fig: Any, scale: float, tol_pt: float = 0.0
) -> list[tuple[str, dict[str, float]]]:
    """Return every legend on ``ax`` whose printed box leaves the axes.

    This is the dedicated-cell case: a legend placed in its own axes with
    ``axis("off")`` must stay inside that cell, because the cell is the whole
    space the layout reserved for it. Measured on a rendered page, a legend
    wider than its cell printed over the axis label of the panel above.

    :param ax: the axes whose legends are measured.
    :param fig: the parent figure, needed for its dpi and renderer.
    :param scale: placement scale from effective_scale.
    :param tol_pt: how far outside the axes rectangle a legend may reach, in
        printed points.
    :returns: list of (legend label, {side: overflow in printed pt}).
    :rtype: list[tuple[str, dict[str, float]]]
    """
    import matplotlib

    rend = renderer_of(fig)
    per_pt = 72.0 / float(fig.dpi) * scale
    frame = ax.get_window_extent(renderer=rend)
    out: list[tuple[str, dict[str, float]]] = []
    for legend in ax.findobj(matplotlib.legend.Legend):
        if not legend.get_visible():
            continue
        box = legend.get_window_extent(renderer=rend)
        over = {}
        for side, amount in (
            ("left", frame.x0 - box.x0),
            ("right", box.x1 - frame.x1),
            ("bottom", frame.y0 - box.y0),
            ("top", box.y1 - frame.y1),
        ):
            value = amount * per_pt
            if value > tol_pt:
                over[side] = value
        if over:
            entries = " | ".join(t.get_text() for t in legend.get_texts())
            out.append((entries, over))
    return out
