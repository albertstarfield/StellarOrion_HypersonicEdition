"""Measure whether every flowchart box label stays inside its own box.

PURPOSE
    A box label that touches or crosses its border is unreadable, and no
    existing guard in this project tests that pairing: print_fit checks the
    canvas, fig_metrics checks text against other text, and neither compares
    a label with the rectangle that is supposed to contain it. This probe
    rebuilds the DSMC flowchart and measures that containment directly, so
    the decision to shorten a box or to enlarge it is made from a number.

PARAMETERS
    None. The subject is the sibling module make_dsmc_flowchart, imported
    from this file's own directory.

RETURNS
    0 when every box label clears its border by at least MIN_CLEAR_PT,
    1 when any box fails, 2 when the figure could not be built.

EXCEPTIONS
    RuntimeError: if the subject module fails to import, or if the rebuilt
        figure reports no axes, which would make an empty measurement look
        like a pass.

CITATIONS
    Matplotlib 3.11.2, Figure.savefig and Axes.add_patch.
    https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.html

AXIOMS
    A1  The figure is built at exactly its printed width, so a measurement
        taken in canvas inches is already a measurement in printed inches.
    A2  A text extent includes the full ascent and descent of the line, not
        only the inked glyphs, so a label reported as clearing a border by a
        small positive amount still has ink inside the border.
    A3  A border stroke is drawn centred on its rectangle, so the interior
        edge of the stroke lies half a linewidth inside the rectangle and a
        label is safe only when its extent stays inside THAT edge.
    A4  The axes patch is itself a Rectangle, so a rectangle is one of the
        flowchart boxes only when its width equals the box width; without
        that test the patch matches every label and the report claims one
        box too many, with clearances above two hundred points.

THEORIES
    T1  A pair (rectangle, label) collides exactly when their display boxes
        intersect, so listing every pair is a complete containment report.
    T2  Extents are pixels at the canvas resolution, so dividing by the
        canvas dpi converts them to inches without a second conversion.

APPLICATIONS
    A1  Re-run after any change to BOX_H, GAP, BOX_FS or the label offsets,
        because each of those moves the label relative to the border.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.text import Text  # noqa: E402

import fig_metrics as fm  # noqa: E402  shared text metrics, one implementation
import make_dsmc_flowchart as subject  # noqa: E402  the figure under test

# Smallest acceptable gap between a label extent and the inside edge of its
# border, in printed points. Chosen from the same measurement that produced
# the earlier MIN_SEP_GAP_PX floor of eight pixels at 300 dpi, which is
# 1.92 printed points; rounding up leaves a visible white channel.
MIN_CLEAR_PT = 2.0

# Matplotlib draws a rectangle border centred on the path, so the interior
# edge sits half the linewidth inside the rectangle. BOX_LW is read from the
# subject rather than typed here so the two cannot drift apart.
BORDER_INSET_PT = 0.5 * subject.BOX_LW


def measure() -> list[tuple[int, float, float, float]]:
    """Rebuild the figure and measure every label against its own box.

    Returns
        One tuple per box as (index, clear_below_pt, clear_above_pt,
        clear_left_pt), where each clearance is the gap in printed points
        between the label extent and the inside edge of that border. A
        negative value means the label crosses the border.

    Exceptions
        RuntimeError: if the rebuilt figure has no axes.
    """
    captured: dict[str, object] = {}
    original = subject.pf.save_to_print_width

    def capture(fig, name, print_width_in, **kwargs):
        """Keep the figure instead of writing and closing it."""
        captured["fig"] = fig
        captured["name"] = name
        return None, 1.0

    subject.pf.save_to_print_width = capture
    try:
        subject.draw()
    finally:
        subject.pf.save_to_print_width = original
        fig = captured.get("fig")
        if fig is not None and hasattr(fig, "axes") and fig.axes:
            rows = report(fig)
            plt.close(fig)
            return rows
    raise RuntimeError("the rebuilt figure reported no axes")


def report(fig) -> list[tuple[int, float, float, float]]:
    """Return one clearance row per flowchart box, tightest box first."""
    rend = fig.canvas.get_renderer()
    inch_per_px = 72.0 / fig.dpi
    rects = [
        p for p in fig.findobj()
        if isinstance(p, Rectangle) and p.get_edgecolor()[3] > 0
        and abs(p.get_width() - subject.BOX_W) < 1e-6
    ]
    texts = [t for t in fig.findobj() if isinstance(t, Text) and t.get_text()]
    rows: list[tuple[int, float, float, float]] = []
    for idx, rect in enumerate(sorted(rects, key=lambda r: -r.get_y())):
        frame = rect.get_window_extent(renderer=rend)
        # The interior edge of a centred border stroke, AXIOM A3.
        inset = BORDER_INSET_PT / 72.0 / inch_per_px
        inside = (frame.x0 + inset, frame.y0 + inset,
                  frame.x1 - inset, frame.y1 - inset)
        worst = None
        for text in texts:
            box = text.get_window_extent(renderer=rend)
            if box.x1 < inside[0] or box.x0 > inside[2]:
                continue
            if box.y1 < inside[1] or box.y0 > inside[3]:
                continue
            below = (box.y0 - inside[1]) * inch_per_px
            above = (inside[3] - box.y1) * inch_per_px
            left = (box.x0 - inside[0]) * inch_per_px
            rows_row = (min(below, above, left), idx, below, above, left)
            worst = rows_row if worst is None or rows_row[0] < worst[0] else worst
        if worst is not None:
            rows.append((worst[1], worst[2], worst[3], worst[4]))
    return rows


def main() -> int:
    """Print every clearance and return the verdict."""
    try:
        rows = measure()
    except RuntimeError as exc:
        print(f"PROBE ERROR: {exc}")
        return 2
    if not rows:
        print("PROBE ERROR: no box rectangle carried a label")
        return 2
    print(f"canvas {subject.W:.4f} x {subject.H:.4f} in  box height "
          f"{subject.BOX_H:.4f} in  label {subject.BOX_FS:.1f} pt  "
          f"floor {MIN_CLEAR_PT:.1f} pt")
    failures = 0
    for idx, below, above, left in sorted(rows, key=lambda r: min(r[1:])):
        ok = min(below, above, left) >= MIN_CLEAR_PT
        failures += 0 if ok else 1
        print(f"  box {idx}: below {below:+.2f} pt  above {above:+.2f} pt  "
              f"left {left:+.2f} pt  {'PASS' if ok else 'FAIL'}")
    print(f"boxes measured {len(rows)}  failing {failures}")
    print("PROBE PASS" if failures == 0 else "VERDICT: a box label crosses its border")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
