"""Name the widest drawn artists in a figure, ranked by printed width.

WHY THIS EXISTS
    print_fit.save_to_print_width resizes the CANVAS while text keeps its
    absolute point size, so when one text artist is wider than the target the
    loop chases its own tail and stalls just above the target width. The
    error message says only that an artist is too wide and does not name it,
    so this probe reports the ranking that identifies the culprit in one run.

    Measured on bo_convergence.png: the loop reported a steady 1728, 1699,
    1697, 1695 px against a 1654 px target, which is the signature of a
    fixed-width text artist rather than a layout that shrinks with the canvas.

PARAMETERS
    None. The figure to inspect is a module-level name, FIGURE_FACTORY, which
    must be a zero-argument callable returning a matplotlib Figure.

RETURNS
    0 when the ranking was printed, 1 when no artist could be measured.

EXCEPTIONS
    RuntimeError when the factory returns something that is not a Figure.

CITATIONS
    Matplotlib 3.11.2, get_window_extent and get_tightbbox
        https://matplotlib.org/stable/api/_as_gen/matplotlib.artist.Artist.html
    Pillow 12.3.0 is not used here; print_fit owns the image measurement.

AXIOMS
    A1: get_window_extent returns pixels at the canvas dpi, so a width in
        inches is the pixel span divided by fig.dpi and never by 72.
    A2: the tight crop is the union of the artist extents plus the save
        padding, so the widest single artist sets a lower bound on the crop
        width that no amount of canvas resizing can beat.
    A3: an Axes carries its own tick label children, so the figure must be
        drawn before extents are meaningful.

THEORIES
    T1: with text at absolute points, a resize scales only the axes and the
        tick positions, so the widest text artist keeps its width while the
        canvas shrinks; the ratio therefore approaches one from above and the
        loop cannot converge.
    T2: because the crop is a union, an artist wider than the target forces
        the crop wider than the target for every canvas size, which is exactly
        the divergence signature the error message describes.

APPLICATIONS
    A1: name the offending artist before changing a font size or a label.
    A2: rank by width so the widest offender is not mistaken for a secondary
        element that merely appears in the same failing report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  backend is fixed above
from matplotlib.patches import Patch  # noqa: E402  artist family under test
from matplotlib.text import Text  # noqa: E402  artist family under test

FIGDIR = Path(__file__).resolve().parent
if str(FIGDIR) not in sys.path:
    sys.path.insert(0, str(FIGDIR))

import make_bo_convergence as target  # noqa: E402  figure under inspection

TOP_N = 8


def measure(fig: plt.Figure) -> list[tuple[float, str]]:
    """Return (width_inches, description) for every drawn artist.

    Parameters:
        fig: the fully drawn figure to inspect.

    Returns:
        a list of pairs sorted widest first.

    Raises:
        none. Artists that refuse to report an extent are skipped.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    dpi = fig.dpi
    rows: list[tuple[float, str]] = []
    for artist in fig.findobj():
        if type(artist).__name__ in ("Spine", "Tick", "Axis"):
            continue
        if not isinstance(artist, (Text, Patch)):
            continue
        if not artist.get_visible():
            continue
        if isinstance(artist, Text) and not artist.get_text():
            continue
        try:
            box = artist.get_window_extent(renderer=renderer)
        except Exception:
            continue
        width_in = (box.x1 - box.x0) / dpi
        label = artist.get_text() if isinstance(artist, Text) else type(artist).__name__
        size = artist.get_fontsize() if isinstance(artist, Text) else 0.0
        rows.append((width_in, f"{width_in:6.3f} in  x[{box.x0 / dpi:.3f},"
                               f"{box.x1 / dpi:.3f}]  {size} pt  {label!r}"))
    rows.sort(key=lambda row: row[0], reverse=True)
    return rows


def main() -> int:
    """Measure the widest artists and report the ranking.

    Returns:
        0 when the ranking printed, 1 when nothing could be measured.

    Raises:
        RuntimeError when the factory does not return a Figure.
    """
    data = target.opt_data.load_verified()
    fig = target.build(data)
    if not isinstance(fig, plt.Figure):
        raise RuntimeError(f"build() returned {type(fig).__name__}, not a Figure")
    w_in, h_in = fig.get_size_inches()
    print(f"canvas {w_in:.3f} x {h_in:.3f} in  dpi {fig.dpi:.0f}")
    rows = measure(fig)
    if not rows:
        print("no artist could be measured")
        plt.close(fig)
        return 1
    print(f"artists measured: {len(rows)}")
    for _, line in rows[:TOP_N]:
        print(f"  {line}")
    print(f"tight crop {fig.get_tightbbox(renderer=fig.canvas.get_renderer()).width / fig.dpi:.3f} in")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())