#!/usr/bin/env python3
"""Identify which artist prevents a figure from fitting its printed width.

WHY THIS EXISTS
save() in make_fignew.py fits the printed width by resizing the canvas and
re-measuring the tight crop. That loop converges only while the crop width is
proportional to the canvas width. It stops converging the moment one artist is
wider than the canvas, because artist sizes are fixed in points while the
canvas is resized in inches: shrinking the canvas then shrinks the crop no
further, and the loop stalls. The trajectory figure stalled at 5.353 in against
a 5.236 in target. Guessing which artist did it produced three wrong answers,
so this probe MEASURES it: it intercepts save(), asks matplotlib for the tight
bounding box, and lists every artist whose window extent reaches further left
or further right than the canvas itself.

PARAMETERS
None. The figure to probe is chosen by the FIGURE_NAME constant below.
RETURNS
An exit code: 0 when an over-wide artist was found and named, 1 when every
artist fits inside the canvas (in which case the stall has another cause), and
2 on an unexpected failure.
EXCEPTIONS
RuntimeError if make_fignew cannot be imported or FIGURE_NAME is not callable.

CITATIONS
[Citation: Matplotlib 3.11.2 - https://matplotlib.org/stable/api/figure_api.html]
The Artist.get_window_extent and Figure.get_tightbbox contracts used here.
[Citation: Pillow 12.3.0 - https://pillow.readthedocs.io/en/stable/]
Not used directly; the probe only inspects the live canvas.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "figures"
assert FIGDIR.is_dir(), FIGDIR
sys.path.insert(0, str(FIGDIR))

# Which builder to probe. Every builder takes no arguments and returns None.
FIGURE_NAME = "fig_trajectory"

# An artist may sit this far outside the canvas before it counts as over-wide,
# in inches. One thousandth of an inch is well under a pixel at 300 dpi, so it
# only absorbs floating-point noise in the transform.
EDGE_TOL_IN = 0.001


def load_make_fignew():
    """Import make_fignew.py from its path and return the module.

    PARAMETERS: none.
    RETURNS: the imported module object.
    RAISES: RuntimeError if the file is missing or fails to import.
    """
    src = FIGDIR / "make_fignew.py"
    if not src.is_file():
        raise RuntimeError(f"missing {src}")
    spec = importlib.util.spec_from_file_location("make_fignew", src)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {src}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["make_fignew"] = mod
    spec.loader.exec_module(mod)
    return mod


def report(fig) -> None:
    """Print the tight crop size and every artist that overhangs the canvas.

    PARAMETERS: fig the matplotlib Figure to inspect.
    RETURNS: None. Raises RuntimeError if the canvas cannot be drawn.
    """
    fig.canvas.draw()
    w_in, h_in = fig.get_size_inches()
    renderer = fig.canvas.get_renderer()
    tight = fig.get_tightbbox(renderer)
    print(f"canvas      {w_in:.3f} x {h_in:.3f} in")
    print(f"tight crop  {tight.width:.3f} x {tight.height:.3f} in")
    print(f"crop wider than canvas by {tight.width - w_in:.3f} in")
    for i, ax in enumerate(fig.axes):
        bb = ax.get_position()
        print(f"  axes[{i}] x {bb.x0 * w_in:.3f} to {bb.x1 * w_in:.3f} in  "
              f"y {bb.y0 * h_in:.3f} to {bb.y1 * h_in:.3f} in")
    over = []
    fig_texts = []
    for artist in fig.findobj():
        try:
            ext = artist.get_window_extent(renderer)
        except Exception:  # noqa: BLE001 - an artist may refuse to measure
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        left = ext.x0 / fig.dpi
        right = ext.x1 / fig.dpi
        label = getattr(artist, "get_text", lambda: "")() or ""
        if artist.axes is None and isinstance(artist, matplotlib.text.Text):
            fig_texts.append((right, left, ext.width / fig.dpi, label))
        if left < -EDGE_TOL_IN or right > w_in + EDGE_TOL_IN:
            owner = "figure"
            if artist.axes is not None:
                try:
                    owner = f"axes[{fig.axes.index(artist.axes)}]"
                except ValueError:
                    owner = "axes?"
            over.append((type(artist).__name__, owner, label, left, right,
                         ext.width / fig.dpi))
    print(f"figure-owned text artists ({len(fig_texts)}), rightmost first:")
    for right, left, width, label in sorted(fig_texts, reverse=True)[:12]:
        print(f"    x {left:7.3f} to {right:7.3f} (width {width:.3f} in)  "
              f"size {label[:40]!r}")
    if not over:
        print("no artist reaches past the canvas")
        return
    print(f"{len(over)} artist(s) reach past the canvas:")
    for kind, owner, label, left, right, width in sorted(over, key=lambda r: -r[4]):
        print(f"  {owner:8s} {kind:14s} x {left:7.3f} to {right:7.3f} "
              f"(width {width:.3f} in)  {label}")


def main() -> int:
    """Probe the chosen builder and return an exit code.

    PARAMETERS: none.
    RETURNS: 0 when an over-wide artist was named, 1 when none was found,
        2 when the probe itself failed.
    RAISES: nothing; failures are reported through the exit code and printed
        traceback.
    """
    mod = load_make_fignew()
    builder = getattr(mod, FIGURE_NAME, None)
    if builder is None:
        raise RuntimeError(f"{FIGURE_NAME} is not a function in make_fignew.py")

    found = {"n": 0}

    def fake_save(fig, name, print_width_in):  # noqa: ANN001 - matplotlib callback
        found["n"] += 1
        print(f"intercepted save for {name} (print {print_width_in:.3f} in)")
        report(fig)
        raise SystemExit(0)

    mod.save = fake_save
    try:
        builder()
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001 - report, do not hide
        print(f"probe failed: {type(exc).__name__}: {exc}")
        return 2
    if not found["n"]:
        print(f"{FIGURE_NAME} never called save()")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
