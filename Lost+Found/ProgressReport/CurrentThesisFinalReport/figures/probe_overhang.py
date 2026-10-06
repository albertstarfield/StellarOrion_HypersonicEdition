"""Report which artists stick out past the figure canvas.

PURPOSE: the print fit loop in generate_sutton_graves_parametric.py cannot
converge at the native printed width. The tight crop measured 1119 px
against a 992 px target, which means the artist union is 127 px WIDER than
the canvas, so shrinking the canvas does not shrink the overhang. This
probe names the overhanging artists so the margins can be fixed instead of
the attempt count being raised.

PARAMETERS: none. The figure comes from the generator module, so the probe
measures the real layout.

RETURNS: process exit status, 0 when the probe ran.

EXCEPTIONS: RuntimeError propagates if the Ada solver cannot be loaded.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate_sutton_graves_parametric as gen  # noqa: E402

TOLERANCE_IN = 0.01


def main() -> int:
    """Print every artist that leaves the canvas and return 0.

    :returns: exit status, 0 on success.
    :raises RuntimeError: if the Ada solver is unavailable.
    """
    solver = gen._load_solver()
    baseline = solver["sg"](gen.H_RUN_KM, gen.V_RUN_MS)["heat_flux_Wcm2"]
    parts = gen.build_figure(solver, baseline)
    fig = parts["fig"]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width_in, height_in = fig.get_size_inches()
    transform = fig.dpi_scale_trans

    print("canvas %.4f x %.4f in" % (width_in, height_in))
    for artist in fig.findobj():
        if not getattr(artist, "get_visible", lambda: False)():
            continue
        box = artist.get_window_extent(renderer)
        left = transform.inverted().transform((box.x0, box.y0))[0]
        right = transform.inverted().transform((box.x1, box.y1))[0]
        top = transform.inverted().transform((box.x0, box.y1))[1]
        bottom = transform.inverted().transform((box.x1, box.y0))[1]
        over = []
        if left < -TOLERANCE_IN:
            over.append("left by %.3f in" % -left)
        if right > width_in + TOLERANCE_IN:
            over.append("right by %.3f in" % (right - width_in))
        if bottom < -TOLERANCE_IN:
            over.append("bottom by %.3f in" % -bottom)
        if top > height_in + TOLERANCE_IN:
            over.append("top by %.3f in" % (top - height_in))
        if over:
            print(
                "  OVERHANG %s: %s | text=%r"
                % (type(artist).__name__, ", ".join(over),
                   getattr(artist, "get_text", lambda: "")())
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())