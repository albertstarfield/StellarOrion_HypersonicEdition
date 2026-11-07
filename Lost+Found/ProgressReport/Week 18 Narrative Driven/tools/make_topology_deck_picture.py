#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Draw the flown-topology comparison at the shape of a slide panel.

WHY: the thesis prints this comparison on a square plate, 6.0 by 6.1 in,
because a page has room to stack the meridional plot, the shoulder zoom and
the per-tree table one under another. The deck places its pictures in a box
7.70 in wide by about 4.0 in tall, so the square plate is height capped: it
lands about 3.9 in wide, the right half of the panel is empty, and the axis
text, the legend and the table inside it are too small to read. Scaling the
plate does not help, because the packing is the problem and not the size. So
this script draws the same three blocks again, for the box: the meridional
half-sections occupy the tall left column, the shoulder zoom takes the top of
the right column, and the table takes the bottom of the right column. Nothing
is recomputed and no number is typed in: every curve is read from the flown
surface of its run, exactly as the thesis plate reads it, and the table is the
same table of the same recorded values.

AXIOMS
    A1. The flown surface of a run is the polyline of that run's
        ``results/<tree>/HIAD_custom.surf``, the file the solver integrated.
        It is read, never reconstructed.
    A2. The gate heat load of a tree is the total recorded by that tree's
        validation time series. It is quoted, not recomputed.
    A3. A panel that cannot be read at the rendered size has no value, so the
        type is set in absolute points for this canvas and is not inherited
        from the page.

THEORIES
    T1. At equal axis scale the two 1.269 m trees differ only in the outer
        envelope, so the shoulder needs its own zoom to show the difference
        at all.
    T2. The box is 1.92 wide to tall, so a tall plot belongs on the left and
        two wide blocks belong stacked on the right; that packing leaves no
        empty panel.

APPLICATIONS
    Writes ``figures/thesis_topology_deck_plate.png`` for the deck only. The
    thesis plate and its generator are untouched.

CITATIONS
    [1] stellarorion_program_proc/scripts/plot_hiad_3d.py, read_surf, the
        reader the thesis plate also uses.
    [2] stellarorion_program_proc/results/<tree>/HIAD_custom.surf, the surface
        SPARTA integrated for each run.
    [3] CurrentThesisFinalReport/figures/make_topology_comparison.py, the
        thesis plate this one re-packs, same trees, same table, same values.
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
OUT = FIGURES / "thesis_topology_deck_plate.png"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"
DPI = 300
MIN_PICTURE_BYTES = 20000

DRIVER = r"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np

OUT = Path(sys.argv[1])
PROC = Path(sys.argv[2])
DPI = int(sys.argv[3])

sys.path.insert(0, str(PROC / "scripts"))
from plot_hiad_3d import read_surf

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

INK = "#222222"
GRID = "#E8E8E8"

# Same trees, same colours, same dash patterns, same recorded heat loads as
# the thesis plate, so a reader who has seen the thesis recognises this one.
TREES = (
    ("00_reference", "#004488", "-", "validation reference", "165.716", "target"),
    ("03_opt_geometry", "#DDAA33", "--", "optimised candidate", "165.716", "PASS*"),
    ("validation_optimized", "#228833", "-.", "gate pass 1 (failed)", "175.580", "FAIL"),
    ("validation_optimized_round2", "#BB5566", ":", "gate pass 2 (passed)", "117.526", "PASS"),
)


def load(tree):
    path = PROC / "results" / tree / "HIAD_custom.surf"
    if not path.is_file():
        sys.stderr.write("MISMATCH flown surface missing: " + str(path) + "\n")
        raise SystemExit(1)
    pts = np.asarray(read_surf(str(path)), dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 3:
        sys.stderr.write("MISMATCH unexpected surface shape in " + str(path) + "\n")
        raise SystemExit(1)
    return pts


profiles = {tree: load(tree) for tree, *_rest in TREES}

figure = plt.figure(figsize=(7.70, 4.01), facecolor="white")

# Left column: the tall meridional plot. The axis limits below are the ones of
# the thesis plate, so the aspect of the body on the slide is the aspect the
# reader saw in the thesis.
ax_full = figure.add_axes([0.055, 0.115, 0.320, 0.790])
ax_zoom = figure.add_axes([0.470, 0.590, 0.500, 0.315])
ax_tab = figure.add_axes([0.455, 0.045, 0.525, 0.440])
ax_tab.axis("off")
ax_tab.set_xlim(0.0, 1.0)
ax_tab.set_ylim(0.0, 1.0)

for tree, colour, style, label, *_rest in TREES:
    pts = profiles[tree]
    ax_full.plot(pts[:, 0], pts[:, 1], color=colour, ls=style, lw=1.9, label=label)

ax_full.set_aspect("equal", adjustable="box")
ax_full.set_xlim(-0.03, 1.34)
ax_full.set_ylim(0.0, 1.97)
ax_full.set_xlabel("Axial position z (m)", fontsize=9.5, labelpad=1)
ax_full.set_ylabel("Radial position r (m)", fontsize=9.5, labelpad=1)
ax_full.tick_params(labelsize=9.0, pad=2)
ax_full.grid(True, color=GRID, lw=0.6)
ax_full.set_axisbelow(True)
for side in ("top", "right"):
    ax_full.spines[side].set_visible(False)
ax_full.set_title("Flown meridional half-sections", fontsize=11.0, color=INK, pad=6)
ax_full.legend(loc="upper left", fontsize=8.2, frameon=True, facecolor="white",
               edgecolor="#BBBBBB", framealpha=1.0, handlelength=2.2,
               borderpad=0.45, labelspacing=0.35)

ref = profiles["00_reference"]
opt = profiles["03_opt_geometry"]
ax_zoom.plot(ref[:, 0], ref[:, 1], color="#004488", lw=2.0, label="reference")
ax_zoom.plot(opt[:, 0], opt[:, 1], color="#DDAA33", ls="--", lw=1.8, label="optimised candidate")
r_max_ref = float(ref[:, 1].max())
r_max_opt = float(opt[:, 1].max())
ax_zoom.axhline(r_max_ref, color="#004488", lw=0.8, ls=(0, (2, 3)))
ax_zoom.axhline(r_max_opt, color="#DDAA33", lw=0.8, ls=(0, (2, 3)))
ax_zoom.annotate("", xy=(1.285, r_max_ref), xytext=(1.285, r_max_opt),
                 arrowprops=dict(arrowstyle="<->", lw=1.0, color=INK))
ax_zoom.text(1.268, 0.5 * (r_max_ref + r_max_opt),
             "{:.1f} mm".format((r_max_ref - r_max_opt) * 1000.0),
             fontsize=9.0, color=INK, va="center", ha="right",
             bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
ax_zoom.set_xlim(0.78, 1.32)
ax_zoom.set_ylim(1.70, 1.93)
ax_zoom.set_xlabel("Axial position z (m)", fontsize=9.5, labelpad=1)
ax_zoom.set_ylabel("Radial position r (m)", fontsize=9.5, labelpad=1)
ax_zoom.tick_params(labelsize=9.0, pad=2)
ax_zoom.grid(True, color=GRID, lw=0.6)
ax_zoom.set_axisbelow(True)
for side in ("top", "right"):
    ax_zoom.spines[side].set_visible(False)
ax_zoom.set_title("Shoulder envelope difference", fontsize=11.0, color=INK, pad=6)
ax_zoom.legend(loc="lower left", fontsize=8.4, frameon=True, facecolor="white",
               edgecolor="#BBBBBB", framealpha=1.0)

cols = (0.000, 0.405, 0.600, 0.755, 0.915)
header = ("flown tree", "L (m)", "r_max (m)", "Q (J/cm2)", "gate")
for x, text in zip(cols, header):
    ax_tab.text(x, 0.95, text, fontsize=8.2, fontweight="bold", color=INK,
                ha="left", va="center")
rows = [
    (tree, "{:.3f}".format(float(profiles[tree][:, 0].max())),
     "{:.3f}".format(float(profiles[tree][:, 1].max())), Q, gate)
    for tree, _c, _s, _l, Q, gate in TREES
]
for i, row in enumerate(rows):
    y = 0.775 - 0.185 * i
    for j, (x, text) in enumerate(zip(cols, row)):
        ax_tab.text(x, y, text, fontsize=8.5, color=INK, ha="left", va="center")
ax_tab.plot([0.0, 1.0], [0.875, 0.875], color="#999999", lw=0.7)
ax_tab.text(0.0, 0.030,
            "Q is the recorded gate heat load. PASS* marks a structural verdict,"
            " not a thermal one.",
            fontsize=7.6, color="#444444", ha="left", va="center")

figure.savefig(OUT, dpi=DPI, facecolor="white")
plt.close(figure)
print("[ok] topology deck plate written: " + str(OUT))
"""


def render() -> int:
    """Run the drawing driver in the interpreter that holds matplotlib.

    WHY: the deck virtual environment carries Pillow but not matplotlib, and
    the thesis interpreter already has it. Re-running there keeps the deck
    environment clean, which is the house pattern for every plate in this
    deck.

    Returns:
        The exit status of the driver, 0 on success.

    Raises:
        SystemExit: When the venv interpreter is absent.

    """
    if not VENV_PYTHON.is_file():
        _ = sys.stderr.write(f"MISMATCH the thesis interpreter is missing: {VENV_PYTHON}\n")
        raise SystemExit(1)
    proc_root = REPO / "stellarorion_program_proc"
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(VENV_PYTHON), "-c", DRIVER, str(OUT), str(proc_root), str(DPI)],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(completed.stderr[-2000:])
        _ = sys.stderr.write("MISMATCH the topology deck plate failed\n")
        return completed.returncode
    if not OUT.is_file():
        _ = sys.stderr.write("MISMATCH the topology deck plate was not written\n")
        return 1
    size = OUT.stat().st_size
    if size < MIN_PICTURE_BYTES:
        _ = sys.stderr.write(f"MISMATCH the topology deck plate is short: {size} bytes\n")
        return 1
    _ = sys.stdout.write(f"[ok] topology deck plate: 7.70x4.01 in, {size} bytes, 4 trees\n")
    return 0


def main() -> int:
    """Draw the plate and report its size.

    Returns:
        A process status, 0 when the plate is written and large enough.

    """
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
