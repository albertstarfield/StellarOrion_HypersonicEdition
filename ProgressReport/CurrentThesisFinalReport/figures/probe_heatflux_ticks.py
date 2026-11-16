#!/usr/bin/env python3
"""Measure the heat-flux panel y tick labels instead of trusting the drawing.

WHY THIS EXISTS
    A rendered audit of the two-panel heat-flux figure reported that the SECOND
    panel carried tick marks and gridlines but no numeric labels at all, with
    zero ink pixels between the rotated axis label and the tick marks. A figure
    can pass every size and gap guard and still show a reader no numbers, so the
    question is answered by measuring the locator, the limits and the ink.

PARAMETERS
    None. The subject module and both CSV inputs are fixed.

RETURNS
    0 when every panel drew at least one numeric y tick label, 1 when a panel
    drew none, 2 when the probe itself could not run.

RAISES
    RuntimeError when the subject module cannot be imported.

CITATIONS
    Matplotlib 3.11.2, Axis.get_majorticklocs and Axis.set_yscale
    https://matplotlib.org/stable/api/_as_gen/matplotlib.axis.Axis.html

AXIOMS
    A1  A tick mark and a gridline are drawn from the locator independently of
        the label, so their presence says nothing about the label.
    A2  A log axis whose window spans less than one decade needs explicit major
        ticks, because the default locator places them only on decades.
    A3  The generator's save() closes the figure, and a closed figure returns
        an empty artist tree, so the probe must keep it alive. An earlier draft
        of this probe reported PASS with no panel lines at all for exactly that
        reason, which is a false pass and the worst kind.

THEORIES
    T1  A panel with a label-free y axis has a locator result that is empty
        inside the window, so printing the locator beside the limits names the
        cause instead of guessing at it.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import matplotlib  # noqa: E402  sibling module, unique print geometry

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  backend fixed above
import make_fignew as mf  # noqa: E402  the subject generator


def probe() -> int:
    """Print both panels' y limits, locators and label boxes, then judge.

    The generator's own guard is disabled and plt.close is made a no-op for the
    duration, both restored in the finally clause, so the figure survives to be
    measured and the module is left exactly as it was found.

    Returns 0 when each panel has at least one visible numeric y label.
    """
    original_guard = mf._guard_layout
    original_close = plt.close
    mf._guard_layout = lambda *args, **kwargs: None
    plt.close = lambda *args, **kwargs: None
    try:
        mf.fig_scalloped_vs_smooth()
        fig = plt.gcf()
        fig.canvas.draw()
        return report(fig)
    finally:
        mf._guard_layout = original_guard
        plt.close = original_close


def report(fig) -> int:
    """Print the y limits, locators and labels of every axes in the figure.

    Parameters
        fig: the live matplotlib Figure whose axes are measured.
    Returns 0 when each axes has at least one visible numeric y label.
    """
    if not fig.axes:
        print("no axes were found, so this probe would be a false pass")
        return 1
    rc = 0
    for index, ax in enumerate(fig.axes, start=1):
        limits = ax.get_ylim()
        locs = list(ax.yaxis.get_majorticklocs())
        inside = [v for v in locs if limits[0] <= v <= limits[1]]
        labels = [(t.get_text(), t.get_visible(), t.get_position())
                  for t in ax.yaxis.get_ticklabels()]
        print(f"panel {index}: ylim ({limits[0]:.6g}, {limits[1]:.6g}) "
              f"decades {__import__('math').log10(limits[1] / limits[0]):.3f}")
        print(f"  major locators {['%.6g' % v for v in locs]}")
        print(f"  inside the window {['%.6g' % v for v in inside]}")
        print(f"  y tick labels {labels}")
        visible = [t for t in ax.yaxis.get_ticklabels()
                   if t.get_visible() and t.get_text()]
        print(f"  labels marked visible {len(visible)} {[t.get_text() for t in visible]}")
        # A label is DRAWN only when its locator value lies inside the window.
        # get_visible() reports the artist's own flag and knows nothing about the
        # window, so counting visible labels is a false pass, which is what an
        # earlier draft of this probe did and what the rendered audit caught.
        print(f"  labels actually inside the window {len(inside)}")
        if not inside:
            print("  VERDICT: panel draws NO numeric y tick label, because every "
                  "major locator value lies outside its own y window")
            rc = 1
    return rc


def main() -> int:
    """Run the probe and report its verdict.

    Returns the probe exit code, or 2 when the subject cannot be imported.
    """
    try:
        code = probe()
    except Exception as exc:  # noqa: BLE001  the probe reports, it never raises
        print(f"probe failed: {exc}")
        return 2
    print("PROBE", "PASS" if code == 0 else f"FAIL code {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
