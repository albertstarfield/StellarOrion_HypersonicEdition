"""Decide whether an out-of-window tick label is drawn or merely present.

WHY THIS EXISTS: the collision guard reported a 250 tick label overlapping the
gate figure title, yet a rendered audit of the same PNG reported no such
label. Both cannot be true, so the question must be answered by measurement:
does matplotlib hand the label to the renderer, or does it filter the tick out
and leave a Text object behind? This probe asks matplotlib directly and also
greps the saved PNG for ink in the region the label would occupy.

PARAMETERS: none. The subject is built by importing make_fignew and calling
fig_gate() on the committed campaign data.

RETURNS: 0 after printing the evidence. 1 if the figure cannot be built.

EXCEPTIONS: RuntimeError when the module, the committed JSON or the saved PNG
is unavailable, because then the question cannot be answered at all.

CITATIONS:
    Matplotlib 3.11.2, Axis.get_majorticklocs and Axis.get_ticklabels,
    https://matplotlib.org/stable/api/_as_gen/matplotlib.axis.Axis.html
    Pillow 12.3.0, https://pillow.readthedocs.io/en/stable/
    NumPy 2.x, https://numpy.org/doc/stable/

AXIOMS:
    A1: an artist is drawn only if matplotlib includes it in the draw list, so
        the draw list, not the object tree, decides visibility.
    A2: get_window_extent reports where a text WOULD sit, so it cannot decide
        whether the text is inked.
    A3: the decisive test is ink in the saved PNG at the label's coordinates,
        because ink is the only evidence a reader receives.

THEORIES:
    T1: if a tick location lies outside the axis view interval then
        matplotlib's update filter excludes it, so its label is a leftover
        object and not a drawn artist.
    T2: a leftover object can still report a box, so a box test alone cannot
        distinguish a drawn label from a leftover one.

APPLICATIONS:
    A1: decide whether a collision report needs a spacing fix or a liveness fix.
    A2: validate any change to the collision guard's clipped-label handling.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image  # noqa: F401  kept for the documented raster path

FIGDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(FIGDIR))

DPI = 300


def load_subject():
    """Import make_fignew as a module.

    PARAMETERS: none.
    RETURNS: the imported module object.
    RAISES RuntimeError when the file is missing or will not import.
    """
    path = FIGDIR / "make_fignew.py"
    if not path.is_file():
        raise RuntimeError(f"missing {path}")
    spec = importlib.util.spec_from_file_location("make_fignew_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build(subject):
    """Build the gate figure with the guard and closing disabled.

    WHY: the probe must survive the failure it measures, and a closed figure
    returns empty extents.

    PARAMETERS: the imported subject module.
    RETURNS: the live figure.
    EXCEPTIONS: RuntimeError propagated from the subject.
    """
    import matplotlib.pyplot as plt

    subject._guard_layout = lambda *args, **kwargs: None
    real_close = plt.close
    plt.close = lambda *args, **kwargs: None
    try:
        plt.close("all")
        subject.fig_gate()
    finally:
        plt.close = real_close
    return plt.gcf()


def band_ink(fig, box, dpi: int = 100) -> int:
    """Count dark pixels of the drawn canvas inside one extent box.

    WHY THE CANVAS BUFFER AND NOT A SAVED FILE: a save with
    bbox_inches="tight" crops and shifts the raster, so a display-space box
    would no longer address the right pixels. The Agg canvas buffer is in
    display pixels already, which is the space get_window_extent reports, so the
    mapping is exact and needs no crop offset.

    AXIOM A4: the canvas y axis points up and the raster y axis points down, so
    a display box at y0 to y1 maps to raster rows height - y1 to height - y0.

    PARAMETERS:
        fig: the matplotlib Figure, which is redrawn inside the function.
        box: an extent box in display pixels, as returned by
            get_window_extent.
        dpi: canvas dpi, used only for the returned scale note.
    RETURNS: the number of pixels darker than 250 of 255 inside the box.
    EXCEPTIONS: RuntimeError if the canvas exposes no pixel buffer, which
        happens when a non-Agg backend is active.
    """
    import math

    fig.canvas.draw()
    try:
        rgba = np.asarray(fig.canvas.buffer_rgba(), dtype=np.int32)
    except AttributeError as exc:  # pragma: no cover - backend contract
        raise RuntimeError(
            "canvas exposes no pixel buffer; run under the Agg backend"
        ) from exc
    height = rgba.shape[0]
    width = rgba.shape[1]
    x0 = max(0, int(math.floor(box.x0)))
    x1 = min(width, int(math.ceil(box.x1)))
    y0 = max(0, int(math.floor(height - box.y1)))
    y1 = min(height, int(math.ceil(height - box.y0)))
    if x1 <= x0 or y1 <= y0:
        return 0
    patch = rgba[y0:y1, x0:x1]
    luma = (patch[..., 0] * 299 + patch[..., 1] * 587 + patch[..., 2] * 114) // 1000
    return int(np.count_nonzero(luma < 250))


def main() -> int:
    """Print the liveness evidence for every tick label of the gate axes.

    PARAMETERS: none.
    RETURNS: 0 on success, 1 on failure.
    EXCEPTIONS: RuntimeError is reported, not raised.
    """
    import matplotlib.pyplot as plt

    try:
        subject = load_subject()
        fig = build(subject)
        fig.canvas.draw()
        rend = fig.canvas.get_renderer()
        pt_per_px = 72.0 / fig.dpi

        for index, ax in enumerate(fig.axes):
            print(f"axes[{index}] ylim {ax.get_ylim()}")
            print(f"  get_majorticklocs {list(ax.yaxis.get_majorticklocs())}")
            print(f"  get_yticks        {list(ax.get_yticks())}")
            print(f"  locator()         {list(ax.yaxis.get_major_locator()())}")
            for minor in (False, True):
                labels = ax.yaxis.get_ticklabels(minor=minor)
                for label in labels:
                    content = label.get_text()
                    if not content:
                        continue
                    loc = label.get_position()[0]
                    box = label.get_window_extent(renderer=rend)
                    visible = label.get_visible()
                    print(f"  tick {content:>6s} pos={loc:8.3f} visible={visible} "
                          f"box x[{box.x0 * pt_per_px:6.2f},"
                          f"{box.x1 * pt_per_px:6.2f}] "
                          f"y[{box.y0 * pt_per_px:6.2f},"
                          f"{box.y1 * pt_per_px:6.2f}] pt")

        # Decisive DIFFERENTIAL test, AXIOM A3. Ink alone cannot separate the
        # 250 label from the title, because both occupy the same band. So the
        # band is measured twice: once with the title present and once with the
        # title emptied. If the 250 label were drawn, the second measurement
        # would still show ink in the band; if matplotlib filtered the tick out,
        # the band goes empty and the title was the only ink there.
        for ax in fig.axes:
            targets = [label for label in ax.yaxis.get_ticklabels(minor=False)
                       if label.get_text() == "250"]
            if not targets:
                continue
            box = targets[0].get_window_extent(renderer=rend)
            title = ax.title.get_text()
            for phase, emptied in (("title present", False),
                                   ("title emptied", True)):
                if emptied:
                    ax.set_title("")
                ink = band_ink(fig, box, DPI)
                print(f"  250 band, {phase}: {ink} dark pixels")
            ax.set_title(title)
        plt.close("all")
        return 0
    except Exception as exc:  # noqa: BLE001 - a probe reports, it does not crash
        print(f"PROBE FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
