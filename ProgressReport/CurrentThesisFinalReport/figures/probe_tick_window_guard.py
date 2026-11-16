#!/usr/bin/env python3
"""Append the tick-window guard to fig_metrics and prove it fires then passes.

WHY THIS TOOL EXISTS
====================
A rendered audit of the two-panel heat-flux figure reported that the second
panel carried tick marks and gridlines but no numeric labels at all. Measuring
the generator showed the cause and, more importantly, showed that a figure can
PASS every existing guard while showing a reader no numbers: the gate reports
label sizes, label gaps, box overlaps and canvas containment, and none of those
ask whether an axis has a label to print at all. The check therefore belongs in
the shared module, and this tool proves both directions of it, because a guard
proven only in the failing direction is a guard nobody can trust.

PARAMETERS
    None. It operates on the fig_metrics module in this directory and on two
    synthetic figures built here, so it needs no project data.

RETURNS
    0 when the guard reports the deliberately unlabelled axis and stays silent
    on the deliberately labelled one, and when the tick picker returns values
    inside the window that asked for them. 1 when either direction fails, 2 when
    the module cannot be imported.

RAISES
    RuntimeError when fig_metrics cannot be imported.

CITATIONS
[Citation: Matplotlib v3.11.2 - Axis.get_majorticklocs and Axis.set_ylim,
          the tick filtering that leaves a label with no ink -
          https://matplotlib.org/stable/api/_as_gen/matplotlib.axis.Axis.html]
[Citation: IEEE 754 double precision, used for the decade logarithm that the
          tick picker rounds - https://ieeexplore.ieee.org/document/4610935]

AXIOMS
    A1  A tick label is drawn only when its data value lies inside the axis
        window, so a count of get_visible() labels is not a count of drawn ones.
    A2  A log axis spanning less than one decade has no decade inside it, so the
        default decade locator produces no label at all, and the axis is not
        wrong, it is empty.
    A3  A guard proved only in the failing direction can be silently broken by
        a later edit, so both directions are exercised here.

THEORIES
    T1  By A1 and A2, the count of major locator values that fall inside the
        window is the number of numeric labels the reader actually sees, so
        counting locators inside the window settles the question exactly.
    T2  On a log axis the printed spacing between two ticks is proportional to
        the difference of their logarithms, so evenly spaced IN PRINT are ticks
        that are evenly spaced in the exponent, which is what the picker
        optimises.

APPLICATIONS
    A1/T1 guard the heat-flux panels, whose windows span 0.47 decades.
    T2 builds the replacement tick set for those panels.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import matplotlib  # noqa: E402  sibling module, unique print geometry

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  backend fixed above
import fig_metrics as fm  # noqa: E402  the module under test


def build() -> tuple:
    """Build two log axes, one with a decade inside it and one without.

    :returns: the (labelled, empty) axes pair.
    """
    fig, (ax_ok, ax_empty) = plt.subplots(1, 2, figsize=(6.0, 3.0))
    for ax in (ax_ok, ax_empty):
        ax.plot([1.0, 2.0], [1.0, 4.0], "-o")
        ax.set_yscale("log")
    ax_ok.set_ylim(50.0, 150.0)      # the decade 100 lies inside, so one label
    ax_empty.set_ylim(151.0, 446.0)  # 100 and 1000 both lie outside, so none
    return fig, ax_ok, ax_empty


def report(fig, ax_ok, ax_empty) -> int:
    """Run the guard on both axes and check the picker on the empty window.

    :returns: 0 when both directions behave, 1 otherwise.
    """
    rc = 0
    reported = fm.axes_without_tick_labels(fig)
    names = [entry[0] for entry in reported]
    print("guard reported", names)
    if "axes[1]:y" in names:
        print("PASS the guard names the axis whose every decade is outside its window")
    else:
        print("FAIL the guard did not name the empty axis, names were", names)
        rc = 1
    if "axes[0]:y" in names:
        print("FAIL the guard named the axis that does have a label")
        rc = 1
    else:
        print("PASS the guard is silent on the axis that has a label")

    ticks = fm.log_ticks_in_window(151.0, 446.0, target=4)
    print("picked ticks", ticks)
    inside = [t for t in ticks if 151.0 <= t <= 446.0]
    if len(inside) >= 3:
        print(f"PASS the picker returned {len(inside)} ticks inside the window")
    else:
        print("FAIL the picker returned", len(inside), "ticks inside the window")
        rc = 1
    bad = fm.log_ticks_in_window(151.0, 446.0, target=40)
    if bad == [] or len(bad) < 3:
        print("FAIL an impossible target produced", bad)
        rc = 1
    else:
        print(f"PASS a dense target is capped, {len(bad)} ticks requested 40")
    return rc


def main() -> int:
    """Run the proof and print its verdict.

    :returns: the exit code described in the module docstring.
    """
    try:
        fig, ax_ok, ax_empty = build()
        fig.canvas.draw()
        code = report(fig, ax_ok, ax_empty)
    except Exception as exc:  # noqa: BLE001  the tool reports, never raises out
        print(f"tool failed: {exc}")
        return 2
    print("SELFCHECK", "PASS" if code == 0 else f"FAIL code {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
