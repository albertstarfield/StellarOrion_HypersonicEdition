#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Compose slide 34's plate: reference volume fields plus the optimised surface map.

WHY: the deck showed four volume field maps of the VALIDATION REFERENCE body
only, and the owner expected slide 34 to carry the OPTIMISED topology's flow
field before the geometry comparison. The optimised runs archived no volume
dump (results/validation_optimized and results/validation_optimized_round2
hold surface VTUs only), so no volume slice of the optimised body can be
drawn without a new DSMC run, which the owner declined. What the run tree
DOES hold is the real surface mesh with its real surface heat flux:
results/validation_optimized_round2/paraview/surf_2200.vtu, 3696 points,
3648 quad cells, CELL array HeatFlux_Wm2. That surface field is drawn
here as a meridional profile (axisymmetric body, so the half-profile is the
whole surface) and composed into ONE plate beside the four reference maps,
so the single picture of the frame carries both bodies, honestly labelled:
volume slice for the reference, SURFACE map for the optimised body.

The drawing lives in DRIVER and runs under the interpreter of the thesis,
which is the interpreter that already holds matplotlib; the deck virtual
environment must not be polluted. This module therefore imports no plotting
library, which is also what keeps the ruff and pyrefly gates clean.

Citations:
    VTK XML UnstructuredGrid file format, https://docs.vtk.org/en/latest/design_documents/VTKFileFormats.html
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.scatter.html
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.imshow.html
    NumPy 2, https://numpy.org/doc/stable/reference/generated/numpy.fromstring.html
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
FIGURES = PROJECT / "figures"
THESIS_FIGURES = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"

#: The archived surface of the pass-2 (accepted gate winner) optimised body.
#: ASCII XML, so a plain ElementTree parse is enough, no binary decoding.
VTU_SOURCE = (
    REPO
    / "stellarorion_program_proc/results/validation_optimized_round2/paraview/surf_2200.vtu"
)

#: The four volume field maps of the validation reference body, reused
#: verbatim from the thesis, in the order (a) to (d) of the plate.
MAP_SOURCES: tuple[Path, ...] = (
    THESIS_FIGURES / "thermal_map_smooth.png",
    THESIS_FIGURES / "pressure_map_smooth.png",
    THESIS_FIGURES / "mach_map_smooth_M0_A0.png",
    THESIS_FIGURES / "velocity_vectors_smooth.png",
)

#: The plate this script writes. Slide 34 swaps to it in the scaffold.
OUT_PLATE = FIGURES / "thesis_flow_field_and_surface_map.png"

#: A plate below this size in bytes was not written properly.
MIN_PLATE_BYTES = 20000
#: Dots per inch of the raster: 7.70 in * 300 dpi = 2310 px wide, the width
#: of the picture box of a side_points frame at scale 1.0.
DPI = 300

#: The drawing program, run as a script by the interpreter of the thesis.
DRIVER = r'''
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

VTU = Path(sys.argv[1])
OUT = Path(sys.argv[2])
MIN_BYTES = int(sys.argv[3])
DPI = int(sys.argv[4])
MAPS = [Path(p) for p in sys.argv[5:9]]

# The plate is the picture box of a side_points frame: 7.70 in wide, about
# 3.98 in tall once the caption has been taken from the panel, aspect 1.93.
PLATE_W, PLATE_H = 7.70, 3.98

# Type sizes on the finished plate, in points.
PT_SUPER = 8.5
PT_PANEL = 7.5
PT_AXIS = 7.0


def parse_surface(path):
    """Return (points, cells, heat flux) of an ASCII VTK surface file.

    WHY: the optimised run archived its surface as an XML VTU with ascii
    DataArrays, so the parse is plain ElementTree plus float conversion and
    no VTK library is needed. Every count in the file is checked against the
    Piece header, because a silently truncated array would draw a wrong map.
    """
    root = ET.parse(path).getroot()
    piece = root.find(".//Piece")
    n_points = int(piece.get("NumberOfPoints"))
    n_cells = int(piece.get("NumberOfCells"))
    points_da = root.find(".//Points/DataArray")
    points = np.array(points_da.text.split(), dtype=float).reshape(-1, 3)
    conn_da = root.find(".//DataArray[@Name='connectivity']")
    flat = np.array(conn_da.text.split(), dtype=np.int64)
    off_da = root.find(".//DataArray[@Name='offsets']")
    offsets = np.array(off_da.text.split(), dtype=np.int64)
    hf_da = root.find(".//DataArray[@Name='HeatFlux_Wm2']")
    heat = np.array(hf_da.text.split(), dtype=float)
    if points.shape != (n_points, 3):
        raise SystemExit("MISMATCH points " + str(points.shape) + " header " + str(n_points))
    # The connectivity is ONE flat stream, not one cell per line: the offsets
    # array carries the end index of each cell, so the stride between
    # consecutive offsets is the number of points of a cell. This file is all
    # quads (stride 4), and a mixed-size mesh would be refused rather than
    # silently mis-sliced.
    if offsets.shape != (n_cells,):
        raise SystemExit("MISMATCH offsets " + str(offsets.shape) + " header " + str(n_cells))
    steps = np.diff(np.concatenate(([0], offsets)))
    if steps.size != n_cells or steps.min() != steps.max():
        raise SystemExit("MISMATCH mixed cell sizes in the offsets array")
    points_per_cell = int(steps[0])
    if flat.size != n_cells * points_per_cell:
        raise SystemExit("MISMATCH connectivity " + str(flat.size)
                         + " header " + str(n_cells * points_per_cell))
    cells = flat.reshape(n_cells, points_per_cell)
    if heat.shape != (n_cells,):
        raise SystemExit("MISMATCH heat flux " + str(heat.shape) + " header " + str(n_cells))
    if cells.min() < 0 or cells.max() >= n_points:
        raise SystemExit("MISMATCH connectivity out of range")
    return points, cells, heat


points, cells, heat = parse_surface(VTU)
# Meridional projection: the body is a surface of revolution about x, so the
# half-profile (axial station against radius) carries the whole surface and
# every cell maps to one spot coloured by its own heat flux.
xc = points[cells, 0].mean(axis=1)
rc = np.hypot(points[cells, 1], points[cells, 2]).mean(axis=1)
radius = np.hypot(points[:, 1], points[:, 2])

fig = plt.figure(figsize=(PLATE_W, PLATE_H))

# LEFT: the surface map of the optimised body, one coloured dot per cell,
# with the body interior shaded so the silhouette reads as a vehicle.
profile = fig.add_axes([0.055, 0.115, 0.275, 0.795])
order = np.argsort(points[:, 0])
profile.fill_between(
    points[order, 0], 0.0, radius[order], step="mid",
    color="#E8ECF2", zorder=0,
)
cloud = profile.scatter(xc, rc, c=heat, s=5, cmap="inferno", linewidths=0, zorder=2)
profile.set_xlim(-0.03, 0.84)
profile.set_ylim(-0.06, 1.26)
profile.set_aspect("equal", adjustable="box")
profile.set_xlabel("axial station x (m)", fontsize=PT_AXIS)
profile.set_ylabel("radius r (m)", fontsize=PT_AXIS)
profile.tick_params(labelsize=PT_AXIS)
profile.set_title(
    "pass-2 optimised body:\nsurface heat flux (W/m2)",
    fontsize=PT_SUPER, fontweight="bold", pad=4,
)
bar = fig.colorbar(cloud, ax=profile, fraction=0.085, pad=0.02)
bar.ax.tick_params(labelsize=PT_AXIS)

# RIGHT: the four reference volume maps, reused verbatim, each on its own
# axes. The box is sized to the map's own aspect (3600 x 2100) so aspect
# equal fills it exactly and nothing is stretched or letterboxed, and the
# placement is in FIGURE fractions: the earlier block-relative maths scaled
# the panel height by the block height twice, which pushed the (a) and (b)
# labels off the top edge and left the bottom quarter of the plate empty.
MAP_ASPECT = 3600.0 / 2100.0
fig.text(
    0.685, 0.985,
    "validation reference body: volume fields, meridional slice, step 2200",
    ha="center", va="top", fontsize=PT_SUPER, fontweight="bold",
)
map_w = 0.285
map_h = map_w * (PLATE_W / PLATE_H) / MAP_ASPECT
cols = (0.398, 0.708)
rows = (0.50, 0.06)
names = ["(a) surface temperature", "(b) surface pressure",
         "(c) Mach number", "(d) velocity vectors"]
for index, source in enumerate(MAPS):
    x0 = cols[index % 2]
    y0 = rows[index // 2]
    panel = fig.add_axes([x0, y0, map_w, map_h])
    image = plt.imread(source)
    panel.imshow(image, aspect="equal")
    panel.set_xticks([])
    panel.set_yticks([])
    for spine in panel.spines.values():
        spine.set_visible(False)
    panel.text(
        0.5, 1.02, names[index], ha="center", va="bottom",
        fontsize=PT_PANEL, fontweight="bold", transform=panel.transAxes,
    )

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=DPI, facecolor="white")
size = OUT.stat().st_size if OUT.is_file() else 0
if size < MIN_BYTES:
    sys.stderr.write("MISMATCH plate was not written: " + str(size) + " bytes\n")
    raise SystemExit(1)
from PIL import Image
with Image.open(OUT) as image:
    width, height = image.size
sys.stdout.write("[ok] flow field and surface map: " + str(width) + "x" + str(height)
                 + "px, " + str(size) + " bytes, heat flux "
                 + str(round(float(heat.min()), 1)) + " to "
                 + str(round(float(heat.max()), 1)) + " W/m2 over "
                 + str(len(heat)) + " cells\n")
'''


def render() -> int:
    """Run the drawing program under the interpreter of the thesis.

    Returns:
        The exit code of the drawing program.
    """
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(VENV_PYTHON),
            "-c",
            DRIVER,
            str(VTU_SOURCE),
            str(OUT_PLATE),
            str(MIN_PLATE_BYTES),
            str(DPI),
            *[str(path) for path in MAP_SOURCES],
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _ = sys.stdout.write(completed.stdout)
    if completed.returncode != 0:
        _ = sys.stderr.write(f"MISMATCH the plate failed:\n{completed.stderr[-2000:]}\n")
        return 1
    return 0


def main() -> int:
    """Compose the plate and report what was written.

    Returns:
        Zero when the plate was written, one when a source was missing.
    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the interpreter of the thesis is missing: {VENV_PYTHON}\n")
        return 1
    if not VTU_SOURCE.is_file():
        _ = sys.stdout.write(f"MISMATCH the optimised surface is missing: {VTU_SOURCE}\n")
        return 1
    for source in MAP_SOURCES:
        if not source.is_file():
            _ = sys.stdout.write(f"MISMATCH a field map is missing: {source}\n")
            return 1
    return render()


if __name__ == "__main__":
    raise SystemExit(main())
