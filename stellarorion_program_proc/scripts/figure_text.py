"""Shared figure-text formatting helpers.

WHY THIS MODULE EXISTS
----------------------
Two figure renderers (``render_bo_3d_plot.py`` and ``render_geometry_grid.py``)
put the same headline quantity in their suptitle: the Cd improvement percentage
read from the shared optimisation results. Each had grown its own
``imp.get('cd_pct', float('nan'))`` default.  That default is a **silent
failure**: when the key is absent the title renders the literal string ``nan%``
and the figure still looks finished, so a missing input is indistinguishable
from a measured value.

AXIOM A1 -- A quantity that was not measured MUST NOT be rendered as if it were.
           The absence of a number is itself information, and it must be
           visible, not formatted into the output.

AXIOM A2 -- A skip is not a pass.  If the value cannot be read, the renderer
           says so on stderr AND prints "n/a" in the figure.  It never prints a
           number, and it never raises (a missing headline annotation must not
           destroy the rest of a figure that took minutes to render).

AXIOM A3 -- One implementation per meaning.  Both call sites share this
           function so the two figures cannot drift apart in how they report a
           missing value -- the same discipline already applied to the SPARTA
           surf reader (``plot_hiad_3d.read_surf``) and the Ada cross-check.

CITATIONS
----------
[Reference: FAILURES_AND_FIXES.md F70] -- recorded ``float('nan')`` defaults on
    the two suptitle sites as a latent fragility.
[Reference: FAILURES_AND_FIXES.md F40 / verify_profile_math AXIOM A3] -- the
    established rule in this project that a skipped check must never read as a
    pass.
[Citation: matplotlib suptitle semantics] -- ``Figure.suptitle`` renders the
    string it is given verbatim; ``nan`` produced by ``"{:.2f}".format(nan)``
    is indistinguishable from a measurement to every reader of the figure.
"""

from __future__ import annotations

import sys
from typing import Any

__all__ = ["improvement_pct"]

# AXIOM A3: the label used when the value is genuinely absent.  Deliberately
# not a number and not "nan" -- "n/a" is text, so it cannot be misread as a
# measurement even at a glance or after a lossy copy of the figure.
MISSING = "n/a"


def improvement_pct(data: dict[str, Any], key: str = "cd_pct") -> str:
    """Format an improvement percentage for a figure title, or report absence.

    Reads ``data["improvement"][key]`` and returns ``"<value:.2f>%"``.

    Parameters
    ----------
    data:
        The parsed optimisation-results mapping (see
        ``src/python/hiad_optimization_results.json``).  ``data["improvement"]``
        may be absent or may lack ``key``.
    key:
        Which entry of the ``improvement`` object to read.  Defaults to
        ``"cd_pct"``, the drag-coefficient improvement.

    Returns
    -------
    str
        ``"1.97%"`` when the value is present and finite; otherwise the string
        ``"n/a"``.  Never returns a bare ``"nan"`` or ``"nan%"``.

    Side effects
    ------------
    Writes one ``[WARNING]`` line to ``sys.stderr`` when the value is missing
    or non-finite, naming the key and the source object, so the log records that
    the figure caption is incomplete (AXIOM A2).

    Exceptions
    ----------
    None.  Every malformed input (absent object, absent key, ``None``, a
    non-numeric string, ``inf``/``nan`` values) degrades to ``"n/a"`` plus a
    warning; this function must never take down a figure that already rendered.
    """
    improvement = data.get("improvement") if hasattr(data, "get") else None
    if not isinstance(improvement, dict):
        print(
            f"[WARNING] figure caption: results object has no usable "
            f"'improvement' mapping ({type(improvement).__name__}); "
            f"reporting {key} as {MISSING}.",
            file=sys.stderr,
        )
        return MISSING

    raw = improvement.get(key)
    if raw is None:
        print(
            f"[WARNING] figure caption: 'improvement.{key}' is absent; "
            f"reporting {MISSING} rather than a number.",
            file=sys.stderr,
        )
        return MISSING

    try:
        value = float(raw)
    except (TypeError, ValueError):
        print(
            f"[WARNING] figure caption: 'improvement.{key}' = {raw!r} is not a "
            f"number; reporting {MISSING}.",
            file=sys.stderr,
        )
        return MISSING

    # A finite value is required: inf/nan would again render as text that looks
    # like a measurement.  math.isfinite is the honest test.
    import math

    if not math.isfinite(value):
        print(
            f"[WARNING] figure caption: 'improvement.{key}' = {value!r} is not "
            f"finite; reporting {MISSING}.",
            file=sys.stderr,
        )
        return MISSING

    return f"{value:.2f}%"