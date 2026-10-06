"""Measure whether every drawn label fits vertically inside the box that holds it.

WHY THIS EXISTS
    A box-diagram generator can shrink its canvas height and pass every width
    guard it owns, because text width does not depend on canvas height. Boxes
    placed at fractions of the canvas therefore halve while the type inside
    them stays absolute, and the first symptom is a label crossing a border.
    That exact defect appeared twice in this project: once when the DSMC
    flowchart was resized for a 16:9 beamer frame, and once in the pipeline
    figure for the same reason. Both generators checked widths only. So this
    probe measures the VERTICAL clearance of each label against the box that
    contains it, and it is generic so a third occurrence cannot need a third
    bespoke checker.

PARAMETERS
    argv[1] (required): module file name inside this directory, for example
        make_pipeline_figure.py.
    argv[2] (optional): zero-argument callable to invoke, default "main".
        The callable is expected to build and save the figure; saving is
        harmless because matplotlib output is deterministic.

RETURNS
    0  every label clears its box above, below, left and right.
    1  at least one label touches or crosses a border.
    2  the probe itself failed (no figure captured, module missing, empty).

EXCEPTIONS
    RuntimeError: the module file is missing or the named callable is absent.
        The saved artifact of the subject is left untouched either way, since
        this probe only observes what the subject already draws.

CITATIONS
    Matplotlib 3.11.2, Artist.get_window_extent and Patch.get_window_extent,
    https://matplotlib.org/stable/api/_as_gen/matplotlib.artist.Artist.get_window_extent.html
    Matplotlib 3.11.2, pyplot.subplots,
    https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html

AXIOMS
    A1  A figure is fully constructed once every artist exists on it, so
        capturing the figure at the end of the build observes the final state
        rather than an intermediate one.
    A2  Text width is measured in display points and is independent of canvas
        height, therefore a width-only guard cannot detect a vertical overflow.
    A3  A rectangle is drawn as a centred stroke, so its ink reaches half a
        line width beyond its geometric edge on every side.
    A4  A label belongs to the box whose rectangle is the SMALLEST one that
        contains the label's centre; the axes patch is excluded because it
        contains every label and would otherwise win every comparison.

THEORIES
    T1  If a label's vertical extent lies inside the box inset by half a line
        width, then no pixel of that label can lie outside the box's ink.
    T2  Choosing the smallest containing rectangle makes each measurement
        local, so a crowded diagram reports one row at a time instead of one
        global worst case.

APPLICATIONS
    A1  After any resize of a box-diagram generator, in either direction.
    A2  Before committing a regenerated box diagram, so the defect is caught at
        the generator rather than on the printed page.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.text import Text  # noqa: E402

HERE = Path(__file__).resolve().parent
PT_PER_IN = 72.0
TOL_PT = 0.5
SKIP_TYPES = ("Rectangle",)


def load(module_name: str):
    """Import a sibling generator module by file name.

    Parameters: module_name, the file name inside this directory.
    Returns: the imported module object.
    Raises: RuntimeError when the file or the module is missing.
    """
    path = HERE / module_name
    if not path.is_file():
        raise RuntimeError(f"{path} does not exist")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{path} cannot be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def collect_figures(module_name: str, callable_name: str):
    """Build the subject and return every figure it created.

    Parameters: module_name, file name inside this directory; callable_name, a
        zero-argument attribute to invoke.
    Returns: the list of Figure objects created during the call.
    Raises: RuntimeError when the attribute is absent or no figure appeared.
    """
    module = load(module_name)
    entry = getattr(module, callable_name, None)
    if entry is None:
        raise RuntimeError(f"{module_name} has no attribute {callable_name}")
    made: list = []
    real_subplots = plt.subplots
    real_figure = plt.figure
    real_close = plt.close
    # AXIOM A5  A generator that closes its figure at the end of the build
    # leaves a FigureCanvasBase, which has no renderer, so every extent read
    # afterwards raises. Suppressing close keeps the canvas this probe needs.
    def spy_subplots(*args, **kwargs):
        result = real_subplots(*args, **kwargs)
        made.append(result[0])
        return result

    def spy_figure(*args, **kwargs):
        fig = real_figure(*args, **kwargs)
        made.append(fig)
        return fig

    plt.subplots = spy_subplots
    plt.figure = spy_figure
    plt.close = lambda *args, **kwargs: None
    try:
        entry()
    finally:
        plt.subplots = real_subplots
        plt.figure = real_figure
        plt.close = real_close
    if not made:
        raise RuntimeError(f"{module_name}.{callable_name} created no figure")
    return made


def rectangles(fig):
    """Return the candidate box rectangles of a figure.

    Parameters: fig, a matplotlib Figure.
    Returns: a list of (Patch, (x0, y0, x1, y1)) in display points.
    Raises: none.
    """
    fig.canvas.draw()
    out = []
    for patch in fig.findobj(match=Patch):
        if type(patch).__name__ in SKIP_TYPES and patch in fig.axes[:1]:
            continue
        try:
            box = patch.get_window_extent(renderer=fig.canvas.get_renderer())
        except (AttributeError, TypeError):
            continue
        if box.width <= 0 or box.height <= 0:
            continue
        out.append((patch, (box.x0, box.y0, box.x1, box.y1)))
    return out


def measure(fig):
    """Return one record per label that lies inside a box.

    Parameters: fig, a matplotlib Figure.
    Returns: a list of (text, below_pt, above_pt, left_pt, right_pt) sorted by
        the smallest clearance first. Labels outside every box are omitted.
    Raises: none.
    """
    renderer = fig.canvas.get_renderer()
    boxes = rectangles(fig)
    rows = []
    for text in fig.findobj(match=Text):
        if not text.get_visible() or not text.get_text():
            continue
        extent = text.get_window_extent(renderer=renderer)
        cx = 0.5 * (extent.x0 + extent.x1)
        cy = 0.5 * (extent.y0 + extent.y1)
        owners = [
            (b, r)
            for b, r in boxes
            if r[0] <= cx <= r[2] and r[1] <= cy <= r[3]
        ]
        if not owners:
            continue
        _, (x0, y0, x1, y1) = min(
            owners, key=lambda item: (item[1][2] - item[1][0]) * (item[1][3] - item[1][1])
        )
        half = 0.5 * _linewidth(boxes, (x0, y0, x1, y1))
        rows.append(
            (
                text.get_text(),
                (y0 + half) - extent.y0,
                extent.y1 - (y1 - half),
                (x0 + half) - extent.x0,
                (x1 - half) - extent.x1,
                (x0, y0, x1, y1),
                type(_owner_patch(boxes, (x0, y0, x1, y1))).__name__,
            )
        )
    rows.sort(key=lambda r: min(r[1:]))
    return rows


def _owner_patch(boxes, rect):
    """Return the patch whose rectangle equals rect, or None.

    Parameters: boxes, the rectangle list; rect, the rectangle to match.
    Returns: the Patch or None.
    Raises: none.
    """
    for patch, candidate in boxes:
        if candidate == rect:
            return patch
    return None


def _linewidth(boxes, rect):
    """Return the line width of the rectangle matching rect, in points.

    Parameters: boxes, the rectangle list; rect, the rectangle to match.
    Returns: the line width in points, 0.0 when nothing matches.
    Raises: none.
    """
    patch = _owner_patch(boxes, rect)
    return 0.0 if patch is None else float(patch.get_linewidth())


def main() -> int:
    """Run the probe and report every label clearance in printed points.

    Returns: 0 when every label clears its box, 1 on a collision, 2 on a
        probe failure.
    """
    if len(sys.argv) < 2:
        print("usage: probe_text_in_boxes.py <module.py> [callable]")
        return 2
    module_name = sys.argv[1]
    callable_name = sys.argv[2] if len(sys.argv) > 2 else "main"
    try:
        figures = collect_figures(module_name, callable_name)
    except RuntimeError as exc:
        print(f"PROBE FAIL: {exc}")
        return 2
    total_bad = 0
    for index, fig in enumerate(figures):
        rows = measure(fig)
        print(
            f"{module_name} figure[{index}] canvas "
            f"{fig.get_figwidth() * PT_PER_IN:.1f} x "
            f"{fig.get_figheight() * PT_PER_IN:.1f} pt, "
            f"{len(rows)} label(s) inside a box"
        )
        for text, below, above, left, right in rows[:14]:
            print(
                f"  {text[:44]!r:48} below {below:7.2f} above {above:7.2f} "
                f"left {left:7.2f} right {right:7.2f}"
            )
        bad = [r for r in rows if min(r[1:]) < TOL_PT]
        total_bad += len(bad)
        if bad:
            print(f"  FAILING {len(bad)} label(s):")
            for text, below, above, left, right in bad:
                print(
                    f"    {text[:44]!r:48} below {below:7.2f} above {above:7.2f} "
                    f"left {left:7.2f} right {right:7.2f}"
                )
    verdict = "PROBE FAIL" if total_bad else "PROBE PASS"
    print(f"{verdict}: {total_bad} label(s) touching or crossing a box border")
    return 1 if total_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
