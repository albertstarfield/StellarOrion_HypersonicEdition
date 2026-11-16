#!/usr/bin/env python3
"""Shared print geometry helpers for every thesis figure generator.

PURPOSE
    Hold the one implementation of the print fit loop and the inside canvas
    assertion so that five generator scripts cannot drift apart. Four copies
    had already accumulated: make_fignew.py, make_lit_review_map.py,
    make_dsmc_flowchart.py and generate_sutton_graves_parametric.py, with two
    different convergence tests, two different reported scale conventions and
    two different inside canvas checks. Divergent copies of a numeric guard
    are worse than no guard, because a figure can pass one and fail the other.

PARAMETERS
    None at module level. Every function takes its own arguments and is
    documented individually.

RETURNS
    save_to_print_width returns (path, scale). assert_inside_canvas returns
    None. checked_dashes returns the list of offending strings, empty when
    the text is clean.

RAISES
    RuntimeError from save_to_print_width when the width cannot be matched,
    from assert_inside_canvas when an artist leaves the canvas, and from
    checked_dashes never; it is the callers decision to raise.

CITATIONS
    Matplotlib 3.11.2, figure saving, tight bounding box and renderer
    extents, PSF based license, https://matplotlib.org/stable/
    Pillow 12.3.0, PNG width measurement, MIT-CMU
    https://pypi.org/project/pillow/
    The thesis is typeset on A4 with 4 cm left and 3 cm right margins, so the
    text width in inches is 21.0/2.54 less (4.0+3.0)/2.54.

AXIOMS
    A1. A declared point size is not a printed point size. The printed size is
        the declared size times the print scale, where the print scale is the
        printed width over the saved width, so the scale must be measured and
        reported rather than assumed.
    A2. savefig with bbox_inches="tight" crops to the artist union, so the
        saved width is not the canvas width and is not knowable before saving.
    A3. A text artist wider than the canvas makes the tight crop grow, which
        makes the fit ratio grow, so the loop cannot converge. Any overhang
        must therefore be rejected before the first save.
    A4. get_window_extent returns pixels at the canvas dpi, so the divisor is
        that dpi and never the point size 72.

THEORIES
    T1. The crop ratio depends only on the internal proportions of the figure
        and is stable under resizing, so measuring it once and scaling the
        canvas by the reciprocal converges in a small number of attempts.
    T2. Under A4 a negative radian dash in a linestyle tuple is a drawing
        instruction rather than punctuation, so banning the literal two
        character sequence in source text does not ban dashed lines.

APPLICATIONS
    A1. Every redrawn or regenerated figure in figures/.
    A2. The build battery, so a figure can never ship with an unmeasured
        print scale.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.legend import Legend  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.text import Text  # noqa: E402
from PIL import Image  # noqa: E402

FIGDIR = Path(__file__).resolve().parent
assert FIGDIR.is_dir(), "print_fit.py must live in the figures directory"

# A4 width less the declared left and right margins, in inches.
TEXT_W_IN = 21.0 / 2.54 - (4.0 + 3.0) / 2.54

DPI = 300
FIT_TOL = 0.005
FIT_ATTEMPTS = 4

# Tolerance for the inside canvas assertion, in inches.
EDGE_TOL_IN = 0.01

# Banned dash characters are built from code points so that generator sources
# never contain a literal double hyphen, en dash or em dash.
DASH2 = chr(45) + chr(45)
DASHES = (DASH2, chr(0x2013), chr(0x2014))


def save_to_print_width(fig: plt.Figure, name: str, print_width_in: float,
                        dpi: int = DPI, label: str = "",
                        close: bool = True) -> tuple[Path, float]:
    """Save the figure so its printed width equals print_width_in.

    Parameters:
        fig: the fully drawn matplotlib Figure.
        name: destination file name inside the figures directory.
        print_width_in: the width on paper, in inches.
        dpi: raster density of the saved PNG.
        label: an optional prefix for the console line.
        close: close the figure when done. A caller that must measure the
            written file while the artist tree is still needed, such as the
            Sutton-Graves generator that verifies a temporary file before
            renaming it, passes False and closes it itself.

    Returns:
        A tuple of the written Path and the achieved print scale, which is
        print_width_in over the saved width in inches.

    Raises:
        RuntimeError when the width cannot be matched within FIT_ATTEMPTS
        attempts, or when the file is written with zero width.
    """
    out = FIGDIR / name
    target_px = print_width_in * dpi
    got_px = 0
    for attempt in range(1, FIT_ATTEMPTS + 1):
        fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white")
        with Image.open(out) as probe:
            got_px = probe.size[0]
        if got_px == 0:
            raise RuntimeError(f"{name} was written with zero width")
        if abs(got_px - target_px) / target_px <= FIT_TOL:
            break
        w, h = fig.get_size_inches()
        ratio = target_px / got_px
        fig.set_size_inches(w * ratio, h * ratio)
        print(f"  fit attempt {attempt}: {got_px}px, target {target_px:.0f}px")
    else:
        raise RuntimeError(
            f"{name}: could not fit to {print_width_in:.3f} in "
            f"(last {got_px / dpi:.3f} in). An artist is wider than the print "
            f"width, so the tight crop grows the image on every attempt. Run "
            f"assert_inside_canvas before saving to name the offending artist.")
    with Image.open(out) as probe:
        size = probe.size
    scale = print_width_in / (size[0] / dpi)
    prefix = f"[{label}] " if label else ""
    print(f"{prefix}wrote {name:40s} {size[0]}x{size[1]}px  "
          f"print {print_width_in:.3f} in  scale {scale:.3f}  "
          f"effective dpi {dpi / scale:.0f}")
    if close:
        plt.close(fig)
    return out, scale


def assert_inside_canvas(fig: plt.Figure, tol_in: float = EDGE_TOL_IN) -> None:
    """Fail when a drawn Text or Patch leaves the figure box.

    Parameters:
        fig: the fully drawn figure.
        tol_in: how far outside the box an extent may reach, in inches.

    Returns:
        None.

    Raises:
        RuntimeError naming every offending artist with its extent, so the
        layout can be corrected in one pass instead of one artist per run.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    w_in, h_in = fig.get_size_inches()
    # Dividing by fig.dpi, never by 72: extents are pixels at the canvas dpi
    # (AXIOM A4), and at the matplotlib default of 100 a figure that exactly
    # fills its canvas would appear to overhang by 39 percent.
    dpi = fig.dpi
    # axis("off") leaves spines, ticks and axis lines in the tree although
    # nothing of them is drawn, and unused minor tick labels are empty Text,
    # so both are excluded by type, by the visible flag and by empty content.
    skip_types = ("Spine", "Tick", "Axis")
    # A Legend is neither a Text nor a Patch, so an earlier version of this
    # function silently skipped it. Its box is a single artist with a single
    # window extent, so a three-column legend could grow 0.155 in past the
    # canvas while every individual Text and Patch stayed inside and the fit
    # loop chased a target it could never reach. The legend is now scanned
    # with everything else.
    checked_types = (Text, Patch, Legend)
    offenders = []
    for artist in fig.findobj():
        if type(artist).__name__ in skip_types:
            continue
        if not isinstance(artist, checked_types):
            continue
        if not artist.get_visible():
            continue
        if isinstance(artist, Text) and not artist.get_text():
            continue
        try:
            box = artist.get_window_extent(renderer=renderer)
        except Exception:
            continue
        x0, x1 = box.x0 / dpi, box.x1 / dpi
        y0, y1 = box.y0 / dpi, box.y1 / dpi
        over = []
        if x0 < -tol_in:
            over.append(f"left by {-x0:.3f} in")
        if x1 > w_in + tol_in:
            over.append(f"right by {x1 - w_in:.3f} in")
        if y0 < -tol_in:
            over.append(f"bottom by {-y0:.3f} in")
        if y1 > h_in + tol_in:
            over.append(f"top by {y1 - h_in:.3f} in")
        if over:
            if isinstance(artist, Legend):
                label = " | ".join(t.get_text() for t in artist.get_texts())
            else:
                label = getattr(artist, "get_text", lambda: "")()
            detail = ""
            if hasattr(artist, "get_xy"):
                detail = f" xy={tuple(round(v, 3) for v in artist.get_xy())}"
            offenders.append(
                f"{type(artist).__name__} {label!r}{detail} -> "
                f"{', '.join(over)} [extent x {x0:.3f} to {x1:.3f}, "
                f"y {y0:.3f} to {y1:.3f}]")
    if offenders:
        shown = offenders[:6]
        extra = "" if len(offenders) == len(shown) else (
            f"\n  ... and {len(offenders) - len(shown)} more")
        raise RuntimeError(
            f"{len(offenders)} artist(s) overhang the {w_in:.3f} x {h_in:.3f} in "
            f"canvas:\n  " + "\n  ".join(shown) + extra)


def checked_dashes(*strings: str) -> list[str]:
    """Report every banned dash found in the given strings.

    Parameters:
        strings: the text values that will be drawn.

    Returns:
        The list of strings containing a double hyphen, en dash or em dash.
        An empty list means the text is clean.
    """
    return [s for s in strings if any(d in s for d in DASHES)]


def require_clean(*strings: str) -> None:
    """Raise when any given string contains a banned dash.

    Parameters:
        strings: the text values that will be drawn.

    Returns:
        None.

    Raises:
        RuntimeError naming each offending string and the dash it contains.
    """
    for s in checked_dashes(*strings):
        found = [f"U+{ord(d):04X}" for d in DASHES if d in s]
        raise RuntimeError(f"banned dash {found} in drawn text {s!r}")


if __name__ == "__main__":
    # Self check: the constants must agree with the thesis geometry and the
    # banned dash builder must not be the literal two character sequence.
    assert abs(TEXT_W_IN - 5.51181) < 1e-4, TEXT_W_IN
    assert DASH2 == chr(45) + chr(45) and DASH2 not in ("a" * 0 + "-"), "dash"
    assert checked_dashes("clean text") == []
    assert len(checked_dashes("a" + DASH2 + "b")) == 1
    assert checked_dashes("en" + chr(0x2013), "em" + chr(0x2014)) != []
    try:
        require_clean("x" + chr(0x2014))
    except RuntimeError:
        pass
    else:
        raise RuntimeError("require_clean failed to reject an em dash")
    print(f"TEXT_W_IN {TEXT_W_IN:.5f} in  print-fit tolerance {FIT_TOL:.3f}  "
          f"attempts {FIT_ATTEMPTS}  SELFCHECK PASS")
    sys.exit(0)
