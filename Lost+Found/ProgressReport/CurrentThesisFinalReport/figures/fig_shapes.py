#!/usr/bin/env python3
"""Shared flowchart shape helpers for the thesis figure generators.

PURPOSE
    Provide the ISO 5807 input/output parallelogram (io_box) once, so
    make_methodology_figures.py and make_software_pipeline.py draw data
    symbols from identical geometry instead of maintaining two copies that
    can silently diverge.

PARAMETERS
    None at import time. Only geometry helpers are exported; each caller
    keeps its own rcParams (font choice) and colour constants.

RETURNS
    Module namespace. Import errors propagate if matplotlib is missing.

EXCEPTIONS
    ImportError if matplotlib is unavailable; ValueError never raised by
    io_box (degenerate widths render empty shapes, callers size boxes via
    their own verify step).

AXIOMS
    A1. Duplicate shape code across generator scripts diverges: the same
        helper edited in one script but not the other produces figures that
        disagree on symbol geometry. One module, one definition.
        (Rule: no copy-paste divergence.)
    A2. The axes in both caller scripts are in inches on both axes
        (figsize = canvas inches, axes spans the figure), so a slant offset
        given in inches is applied directly with no unit conversion.

THEORIES
    T1. Shifting the top edge right by a small constant (slant_in) is
        sufficient to make a quadrilateral read as the ISO 5807 data
        symbol, distinct from rectangular process boxes, without
        disturbing centred text placement beyond slant_in/2.

APPLICATIONS
    A1. make_methodology_figures.py draws the dump and metrics boxes of
        the result-extraction flow with io_box.
    A2. make_software_pipeline.py draws the three INPUT boxes and the
        OUTPUT box of the five-column pipeline with io_box.

CITATIONS
    ISO 5807, Information processing -- Documentation symbols and
    conventions -- Data processing flowcharts, https://www.iso.org/
    Matplotlib 3.9.4, Polygon,
    https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.Polygon.html
"""

from __future__ import annotations

from matplotlib.patches import Polygon  # noqa: E402  pure geometry, no backend


def io_box(ax: object, x0: float, y0: float, w: float, h: float,
           text: str, fill: str, edge: str, text_color: str = "#212121",
           fs: float = 9.5, linespacing: float = 1.3,
           slant_in: float = 0.05) -> None:
    """Draw a right-leaning input/output parallelogram with centered text.

    ISO 5807 data symbol: the top edge is shifted right by slant_in so the
    shape reads as input/output by outline alone, distinct from the
    rectangular process boxes. The axes here are in inches on both axes,
    so slant_in is used directly as a data offset (no unit conversion).

    :param ax: the axes to draw on.
    :param x0: bottom-left corner x in inches (before the slant).
    :param y0: bottom edge y in inches.
    :param w: horizontal width of the bottom edge in inches.
    :param h: height in inches.
    :param text: label string, may contain newlines.
    :param fill: face colour.
    :param edge: edge colour.
    :param text_color: text colour.
    :param fs: declared font size in points.
    :param linespacing: line spacing multiplier.
    :param slant_in: horizontal offset of the top edge in inches.
    :returns: None.
    """
    s = slant_in
    ax.add_patch(Polygon(
        [(x0, y0), (x0 + w, y0), (x0 + w + s, y0 + h), (x0 + s, y0 + h)],
        closed=True, linewidth=1.2, edgecolor=edge, facecolor=fill,
        zorder=2,
    ))
    ax.text(x0 + w / 2 + s / 2, y0 + h / 2, text, ha="center", va="center",
            fontsize=fs, color=text_color, zorder=3, linespacing=linespacing)
