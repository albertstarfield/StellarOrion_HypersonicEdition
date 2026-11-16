"""Report the geometry of the gate figure so an overlap can be attributed.

WHY THIS EXISTS: the new all-pairs collision guard in fig_metrics reports a
pair of overlapping text boxes, but a pair without coordinates cannot be
judged. A title that merely passes close to a tick label and a title printed
on top of a tick label need different fixes, and only the coordinates tell
them apart.

PARAMETERS: none. The subject figure is produced by importing make_fignew and
rebuilding fig_gate() on the committed campaign data.

RETURNS: 0 after printing the report. 1 if the subject cannot be built.

EXCEPTIONS: RuntimeError when the module or the committed JSON cannot be
loaded, which means the figure cannot be measured at all.

CITATIONS:
    Matplotlib 3.11.2, Artist.get_window_extent and Axes.get_window_extent,
    https://matplotlib.org/stable/api/_as_gen/matplotlib.artist.Artist.html
    Pillow 12.3.0, https://pillow.readthedocs.io/en/stable/

AXIOMS:
    A1: get_window_extent returns PIXELS at the canvas dpi, so a printed point
        is width_px / fig.dpi, never width_px / 72.
    A2: the figure is built at the printed width, so canvas points are printed
        points, which is why no separate print scale is needed here.
    A3: an overlap is a property of the FINAL layout, so the figure must be
        laid out and drawn before any extent is read.

THEORIES:
    T1: every drawn text is located once and reported with its owning axes and
        role, because two panels can carry the same label.
    T2: a text box that reaches above the axes rectangle is either a title, a
        tick label whose data position lies above the window, or an artist
        placed with an axes fraction that resolves outside; the owner role
        distinguishes them.

APPLICATIONS:
    A1: attribute a collision guard failure to a named artist.
    A2: confirm a spacing fix without re-running the full generator.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

FIGDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(FIGDIR))


def load_subject():
    """Import make_fignew as a module.

    PARAMETERS: none.
    RETURNS: the imported module object.
    RAISES RuntimeError when the file is missing or will not import.
    """
    path = FIGDIR / "make_fignew.py"
    if not path.is_file():
        raise RuntimeError(f"missing {path}")
    spec = importlib.util.spec_from_file_location("make_fignew_probe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def report() -> int:
    """Build the gate figure and print every text box and axes rectangle.

    PARAMETERS: none.
    RETURNS: 0.
    RAISES RuntimeError when the figure cannot be built.
    """
    import fig_metrics as fm
    import matplotlib.pyplot as plt

    subject = load_subject()
    # Two temporary monkeypatches, each with a measured reason, and both
    # restored before anything is measured.
    #
    # 1. The guard is DISABLED. The probe exists to attribute a guard failure to
    #    a named artist, so it must survive the very failure it measures;
    #    leaving the guard in place aborts the run at the first save and
    #    reports nothing.
    subject._guard_layout = lambda *args, **kwargs: None
    #
    # 2. Figure closing is DISABLED. save() ends by closing the figure, and a
    #    closed figure returns empty extents, which is how the first version of
    #    this probe printed a canvas of 6.40 x 4.80 pt and zero visible texts
    #    for a figure that is 4.41 in wide with twenty labels on it. The patch is
    #    on the pyplot attribute itself, so it also catches the close inside
    #    print_fit, which imports the same module object.
    real_close = plt.close

    def quiet_close(*args, **kwargs):
        """Accept and ignore a close request while the probe holds the figure.

        PARAMETERS: whatever pyplot.close accepts.
        RETURNS: None.
        EXCEPTIONS: none; every argument is ignored.
        """
        return None

    plt.close = quiet_close
    try:
        plt.close("all")
        subject.fig_gate()
    finally:
        plt.close = real_close
    fig = plt.gcf()
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    scale = 1.0 / fig.dpi  # printed points per pixel, AXIOM A1

    width_pt, height_pt = fig.get_size_inches() * fig.dpi * scale
    print(f"canvas {width_pt:.2f} x {height_pt:.2f} pt  dpi {fig.dpi}")

    for index, ax in enumerate(fig.axes):
        box = ax.get_window_extent(renderer=rend)
        x0 = box.x0 * scale
        x1 = box.x1 * scale
        y0 = box.y0 * scale
        y1 = box.y1 * scale
        print(f"axes[{index}] x {x0:.2f} to {x1:.2f} pt  y {y0:.2f} to "
              f"{y1:.2f} pt")
        print(f"  ylim {ax.get_ylim()}  xlim {ax.get_xlim()}")

    # LIVENESS QUESTION, measured rather than assumed. A tick label whose data
    # position falls outside the final axis window is filtered out of the axis
    # tick list by matplotlib, but the Text object survives in the figure tree
    # with the position it had while the limits were still autoscaled. Such a
    # Text is never handed to the renderer, so it cannot appear on the page,
    # yet findobj still returns it and any box test then reports a collision
    # that the reader will never see. The three membership flags below
    # distinguish a live text from a stale one: a live tick label is in the
    # axis current tick list, and a text added by ax.text is in ax.texts.
    live_ticks = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                for label in (tick.label1, tick.label2):
                    if label is not None:
                        live_ticks.add(id(label))
    live_ax_texts = set()
    for ax in fig.axes:
        for text in ax.texts:
            live_ax_texts.add(id(text))

    clipped = fm.clipped_tick_ids(fig)
    rows = []
    for text in fig.findobj():
        if type(text).__name__ != "Text":
            continue
        content = text.get_text()
        if not content or id(text) in clipped:
            continue
        box = text.get_window_extent(renderer=rend)
        flags = ("T" if id(text) in live_ticks else "-") + \
                ("A" if id(text) in live_ax_texts else "-")
        rows.append((fm.owner_label(text, fig), flags, content,
                     box.x0 * scale, box.x1 * scale,
                     box.y0 * scale, box.y1 * scale))
    rows.sort(key=lambda r: -r[4])
    print(f"visible texts: {len(rows)}   flags TA = live, - = possibly stale")
    for owner, flags, content, x0, x1, y0, y1 in rows:
        shown = content.replace("\n", " / ")
        print(f"  {owner:22s} {flags} x[{x0:6.2f},{x1:6.2f}] y[{y0:6.2f},"
              f"{y1:6.2f}]  {shown}")

    for first, second, wide, high in fm.text_overlaps_pt(fig, scale):
        print(f"OVERLAP {first} against {second} at {wide:.2f} x {high:.2f} pt")
    plt.close("all")
    return 0


def main() -> int:
    """Entry point.

    PARAMETERS: none.
    RETURNS: 0 on success, 1 when the figure cannot be built.
    EXCEPTIONS: RuntimeError is reported, not raised, so the shell sees 1.
    """
    try:
        return report()
    except Exception as exc:  # noqa: BLE001 - a probe reports, it does not crash
        print(f"PROBE FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
