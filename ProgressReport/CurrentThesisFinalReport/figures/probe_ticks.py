"""List every tick label of both sutton axes with its rendered size.

PURPOSE: the new layout guard in generate_sutton_graves_parametric.py
rejected the saved figure because the smallest printed text measured
5.95 pt, and the offending artist is a mathtext label of the form
10 to the power 0. The guard reports the string but not which axis owns
it, so this probe walks the two axes and prints the owner, the string,
the declared size and the measured position of every tick label.

PARAMETERS: none. The solver and the figure come from the generator
module itself, so the probe cannot drift from the real figure.

RETURNS: process exit status, 0 when the probe ran.

EXCEPTIONS: RuntimeError propagates if the Ada solver cannot be loaded,
which is the same failure the generator reports.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate_sutton_graves_parametric as gen  # noqa: E402


def main() -> int:
    """Print the tick labels of both axes and return 0.

    :returns: exit status, 0 on success.
    :raises RuntimeError: if the Ada solver is unavailable.
    """
    solver = gen._load_solver()
    baseline = solver["sg"](gen.H_RUN_KM, gen.V_RUN_MS)["heat_flux_Wcm2"]
    parts = gen.build_figure(solver, baseline)
    parts["fig"].canvas.draw()
    for name in ("ax1", "ax2"):
        ax = parts[name]
        print("=== %s scale x=%s y=%s" % (name, ax.get_xscale(), ax.get_yscale()))
        for axis, which in ((ax.xaxis, "major"), (ax.xaxis, "minor"),
                            (ax.yaxis, "major"), (ax.yaxis, "minor")):
            labels = [
                (label.get_visible(), label.get_text(), label.get_fontsize())
                for label in axis.get_ticklabels()
            ]
            print("  %s %s: %s" % (axis.axis_name, which, labels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())