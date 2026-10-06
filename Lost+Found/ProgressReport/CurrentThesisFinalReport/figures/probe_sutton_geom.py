#!/usr/bin/env python3
"""Measure the panel and text geometry of the Sutton-Graves figure before editing it.

PURPOSE
=======
A rendered-page audit found five collisions in figures/sutton_graves_parametric.png:
panel (a) minor tick labels printed on top of each other, the panel (a) legend
title struck through the x-axis label, the panel (a) title overprinted on its own
last word, the panel (b) annotation frame reaching 42 pt left of the panel (b)
left spine, and the annotation arrow stopping 2.4 pt short of the line it names.
Each fix needs a number before it can be chosen: how wide the panels actually
are, how wide the annotation text actually is, and where each artist's box
sits. This tool prints those numbers so the fix is a calculation and not a guess.

PARAMETERS
==========
None. The subject is imported as figures.generate_sutton_graves_parametric and
its build_figure() is called with the committed solver baseline.

RETURNS
=======
0 when every panel and text extent was measured, 1 when a measurement failed.

EXCEPTIONS
==========
RuntimeError: if the generator cannot be imported, if the Ada solver cannot be
constructed, or if the baseline constant cannot be read.

AXIOMS
======
A1. get_window_extent returns pixels at the canvas dpi, so every distance is
    converted with 72.0 / fig.dpi and never with a bare division by 72.
A2. The figure is built at exactly the printed width, so the printed scale is
    one to within the fit tolerance and printed points equal canvas points here.

THEORIES
========
T1. An annotation anchored in axes fraction is placed by its anchor, so the only
    way to know whether its frame fits is to compare the frame box with the
    axes box, which is what this tool reports.
T2. Two texts collide if and only if their boxes intersect, so listing every
    intersecting pair is a complete collision report for the figure.

APPLICATIONS
============
A1 chooses the annotation anchor and label width; A2 reports the panels and the
gridspec so the legend cell can be sized without trial and error.

CITATIONS
=========
[Citation: Matplotlib v3.11.2 - Artist.get_window_extent and Figure axes box -
          https://matplotlib.org/stable/api/axes_api.html]
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")

FIGDIR = os.path.dirname(os.path.abspath(__file__))
if FIGDIR not in sys.path:
    sys.path.insert(0, FIGDIR)

import fig_metrics as fm  # noqa: E402
import generate_sutton_graves_parametric as sg  # noqa: E402


def main() -> int:
    """Print panel boxes, text extents and every colliding text pair.

    :returns: 0 on success, 1 when the figure or a measurement is unavailable.
    :rtype: int
    """
    solver = sg._load_solver()
    parts = sg.build_figure(
        solver, solver["sg"](sg.H_RUN_KM, sg.V_RUN_MS)["heat_flux_Wcm2"])
    fig = parts["fig"]
    fig.canvas.draw()
    dpi = float(fig.dpi)
    per_pt = 72.0 / dpi

    print("canvas %.4f x %.4f in  dpi %.1f" % (*fig.get_size_inches(), dpi))
    for name in ("ax1", "ax2"):
        ax = parts[name]
        box = ax.get_window_extent(fig.canvas.get_renderer())
        print(
            "%s axes x %.2f to %.2f pt (%.3f in wide)  y %.2f to %.2f pt"
            % (
                name,
                box.x0 * per_pt,
                box.x1 * per_pt,
                (box.x1 - box.x0) * per_pt / 72.0,
                box.y0 * per_pt,
                box.y1 * per_pt,
            )
        )

    for label in ("ax1", "ax2"):
        ax = parts[label]
        for kind, artist in (
            ("title", ax.title),
            ("xlabel", ax.xaxis.label),
            ("ylabel", ax.yaxis.label),
        ):
            box = artist.get_window_extent(fig.canvas.get_renderer())
            print(
                "%s %-7s width %.2f pt  %r"
                % (label, kind, (box.x1 - box.x0) * per_pt, artist.get_text())
            )

    for ann in list(parts["ax1"].texts) + list(parts["ax2"].texts):
        box = ann.get_window_extent(fig.canvas.get_renderer())
        patch = ann.get_bbox_patch()
        print(
            "annotation width %.2f pt  xytext %s  %r%s"
            % (
                (box.x1 - box.x0) * per_pt,
                tuple(round(v, 3) for v in ann.get_position()),
                ann.get_text(),
                "" if patch is None else "  (framed)",
            )
        )

    overlaps = fm.text_overlaps_pt(fig, 1.0)
    print("colliding text pairs at or above 1.0 pt: %d" % len(overlaps))
    for text_a, text_b, width_pt, height_pt in overlaps:
        print("  %r  <->  %r  %.2f x %.2f pt" % (text_a, text_b, width_pt, height_pt))

    for name in ("ax1", "ax2"):
        ax = parts[name]
        leaks = fm.annotation_boxes_inside_axes_pt(ax, fig, 1.0)
        print("%s annotation frames outside the axes: %d" % (name, len(leaks)))
        for text, over in leaks:
            print("  %r -> %s" % (text, ", ".join(
                "%s by %.2f pt" % (side, value) for side, value in sorted(over.items())
            )))
    return 0


if __name__ == "__main__":
    sys.exit(main())