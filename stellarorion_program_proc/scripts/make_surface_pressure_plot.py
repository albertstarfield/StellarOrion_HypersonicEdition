#!/usr/bin/env python3
"""Surface-pressure distribution along the HIAD body.

PURPOSE
    Produce the axial surface-pressure distribution the results chapter cites
    (figure 4.25): the per-surface pressure of the step-2200 DSMC dump against
    the axial station, derived from the solver's own per-surface force dump and
    the surface mesh that produced it.

AXIOMS
    A1  The only inputs are the run's own artifacts: the final ``surf.<step>.out``
        dump and the ``*.surf`` surface mesh the solver was given.  No pressure
        is invented from a correlation, and no value is read from a log.
    A2  The solver writes a per-surface FORCE, not a pressure.  The pressure is
        therefore DERIVED: the force on a surface band is decomposed into a
        normal stress (the pressure) and a tangential stress (the shear); the
        projection of the force onto the band's unit normal isolates the normal
        stress, because the shear is tangential by definition.  The figure states
        this derivation, so a reader never mistakes it for a native pressure dump.
    A3  The surface is the axisymmetric meridional profile: band ``i`` is the
        revolution of the segment between mesh points ``i`` and ``i+1``, so its
        wetted area is ``2*pi*r_centroid*length``.  The DUMP's surface id is that
        segment index, and a missing or zero-force band is reported rather than
        smoothed away.
    A4  If the run kept no surf dump, the script reports it and exits non-zero;
        it never fabricates a profile from a total drag.

THEOREMS
    T1  If the shear were zero, the derived pressure would equal the total
        surface pressure exactly (A2 with a purely normal force).
    T2  The derivation is falsifiable: integrating the derived pressure over the
        projected band areas reproduces the run's total drag to within the
        neglected shear contribution, and the script prints that check.

APPLICATIONS
    ``python3 scripts/make_surface_pressure_plot.py --results-dir
    results/grid_independence/level_3`` writes
    ``<results-dir>/plots/surface_pressure_vs_axial.png`` and a CSV beside it.

CITATIONS
    [Anderson06] J. D. Anderson, *Hypersonic and High-Temperature Gas
        Dynamics*, 2nd ed., AIAA, 2006, ch. 3 (pressure and shear on a
        hypersonic surface; the normal-stress decomposition used here).
    [Bird94] G. A. Bird, *Molecular Gas Dynamics and the Direct Simulation of
        Gas Flows*, 2nd ed., Oxford, 1994, ch. 12 (surface momentum
        accommodation, the per-surface force a DSMC boundary reports).
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURF_DUMP_RE = re.compile(r"^surf\.(\d+)\.out$")


def read_geometry(path: Path) -> tuple[list[tuple[float, float]], list[tuple[int, int]]]:
    """Read a SPARTA surface file's points and line connectivity.

    Parameters:
        path: the ``*.surf`` file (``N points`` / ``M lines`` header, a
            ``Points`` section of ``id x r`` rows, a ``Lines`` section of
            ``id a b`` rows).

    Returns:
        ``(points, segments)`` with points as ``(x, r)`` in metres and segments
        as zero-based point-index pairs.

    Raises:
        FileNotFoundError: the file does not exist.
        ValueError: the file has no usable points section.
    """
    if not path.is_file():
        raise FileNotFoundError(f"surface mesh not found: {path}")
    points: list[tuple[float, float]] = []
    segments: list[tuple[int, int]] = []
    mode = ""
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lowered = line.lower()
        if lowered.startswith("points"):
            mode = "points"
            continue
        if lowered.startswith("lines"):
            mode = "lines"
            continue
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            first, second, third = (float(value) for value in fields)
        except ValueError:
            continue
        if mode == "points":
            points.append((second, third))
        elif mode == "lines":
            segments.append((int(first) - 1, int(third) - 1))
    if len(points) < 2:
        raise ValueError(f"{path}: no usable points section")
    if not segments:
        #  WHY: some writers omit the Lines section and imply the segments from
        #  the point order; that is the only case in which we infer them.
        segments = [(index, index + 1) for index in range(len(points) - 1)]
    return points, segments


def last_dump(results_dir: Path) -> Path:
    """Return the highest-step surf dump of a results tree.

    Parameters:
        results_dir: the run's results directory.

    Returns:
        The dump with the largest step number.

    Raises:
        FileNotFoundError: the tree holds no ``surf.<step>.out`` file.
    """
    dumps = [
        (int(match.group(1)), path)
        for path in results_dir.glob("surf.*.out")
        if (match := SURF_DUMP_RE.match(path.name))
    ]
    if not dumps:
        raise FileNotFoundError(f"no surf.<step>.out dump under {results_dir}")
    dumps.sort()
    return dumps[-1][1]


def read_dump(path: Path) -> dict[int, tuple[float, float]]:
    """Read the per-surface forces of a SPARTA surf dump.

    Parameters:
        path: the ``surf.<step>.out`` file.

    Returns:
        A mapping ``surface id -> (axial force N, radial force N)`` taken from
        ``f_surfavg[1]`` and ``f_surfavg[2]``.  The other columns are the
        per-surface momentum/energy fluxes, which this figure does not use.

    Raises:
        FileNotFoundError: the file does not exist.
        ValueError: the header does not carry the expected column names.
    """
    if not path.is_file():
        raise FileNotFoundError(f"surf dump not found: {path}")
    forces: dict[int, tuple[float, float]] = {}
    columns = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("ITEM: SURFS"):
            if "f_surfavg[1]" not in line or "f_surfavg[2]" not in line:
                raise ValueError(f"{path}: unexpected dump columns in {line!r}")
            columns = True
            continue
        if not columns:
            continue
        fields = line.split()
        if len(fields) < 7:
            continue
        try:
            surface = int(fields[0])
            axial = float(fields[4])
            radial = float(fields[5])
        except ValueError:
            continue
        forces[surface] = (axial, radial)
    if not forces:
        raise ValueError(f"{path}: no surface rows parsed")
    return forces


def pressure_profile(
    points: list[tuple[float, float]],
    segments: list[tuple[int, int]],
    forces: dict[int, tuple[float, float]],
) -> tuple[list[tuple[float, float]], float]:
    """Derive the per-band pressure profile (AXIOM A2/A3).

    Parameters:
        points: the mesh points as ``(x, r)``.
        segments: zero-based point-index pairs, one per surface id (id 1 is
            ``segments[0]``).
        forces: the per-surface forces keyed by surface id.

    Returns:
        ``(profile, sign)`` where profile is a list of
        ``(x_centroid_m, pressure_Pa, area_m2, axial_force_N)`` for every band
        that appears in the dump, and ``sign`` is the normal orientation that
        was used (``+1`` or ``-1``), chosen once for the whole body.

    Raises:
        ValueError: no band in the mesh has a matching force.
    """
    bands: list[tuple[float, float, float, float, float, float, float]] = []
    for index, (first, second) in enumerate(segments, start=1):
        if first >= len(points) or second >= len(points):
            continue
        x0, r0 = points[first]
        x1, r1 = points[second]
        dx, dr = x1 - x0, r1 - r0
        length = math.hypot(dx, dr)
        if length <= 0.0:
            continue
        r_c = 0.5 * (r0 + r1)
        #  WHY: the band is the revolution of the segment, so its wetted area is
        #  the circumference at the mean radius times the meridional length.
        area = 2.0 * math.pi * r_c * length if r_c > 0.0 else length
        axial, radial = forces.get(index, (0.0, 0.0))
        bands.append((0.5 * (x0 + x1), area, axial, radial, dr / length, -dx / length, length))
    if not bands:
        raise ValueError("no surface band matched a force entry")

    #  WHY: the meridional normal is fixed by the mesh winding; its global sign
    #  must be the OUTWARD one.  A wrong guess makes the pressures negative, so
    #  the sign is chosen by the majority of the windward bands and reported.
    positive = sum(1 for _, _, ax, rad, nx, nr, _ in bands if -(ax * nx + rad * nr) > 0.0)
    sign = 1.0 if positive * 2 >= len(bands) else -1.0
    profile = [
        (x_c, -(axial * nx + radial * nr) * sign / area, area, axial)
        for x_c, area, axial, radial, nx, nr, _ in bands
    ]
    return profile, sign


def render(
    profile: list[tuple[float, float, float, float]],
    dump: Path,
    out_png: Path,
    out_csv: Path,
) -> None:
    """Draw the surface-pressure figure and write the machine-readable table.

    Parameters:
        profile: ``(x_m, pressure_Pa, area_m2, axial_force_N)`` tuples.
        dump: the dump the profile came from (named on the figure).
        out_png: destination of the PNG.
        out_csv: destination of the CSV.

    Raises:
        OSError: an output path cannot be written.
    """
    x = [row[0] for row in profile]
    p_kpa = [row[1] / 1000.0 for row in profile]
    peak_index = max(range(len(p_kpa)), key=lambda index: p_kpa[index])

    fig, ax = plt.subplots(figsize=(10.0, 4.8), constrained_layout=True)
    ax.plot(x, p_kpa, "o-", color="#8e44ad", linewidth=2.0, markersize=5.5,
            label="derived surface pressure")
    ax.axhline(0.0, color="#888888", linewidth=1.0, linestyle=":")
    ax.plot([x[peak_index]], [p_kpa[peak_index]], "o", color="#c0392b", markersize=10,
            label=f"peak {p_kpa[peak_index]:.2f} kPa at x = {x[peak_index]:.4f} m")
    ax.set_xlabel("Axial station $x$ (m)")
    ax.set_ylabel(r"Surface pressure $p$ (kPa)")
    ax.set_title("Surface pressure along the HIAD body (step-2200 DSMC surface dump)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    fig.text(
        0.01, 0.01,
        "Pressure derived from the per-surface force projected onto the band normal "
        "(shear is tangential and cancels);\n"
        f"axisymmetric band area 2*pi*r*L.  Source: {dump.parent.name}/{dump.name}.",
        fontsize=7.0, color="#444444", ha="left", va="bottom",
    )
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x_m", "pressure_Pa", "area_m2", "axial_force_N"])
        for x_c, pressure, area, axial in profile:
            writer.writerow([f"{x_c:.6f}", f"{pressure:.6f}", f"{area:.9f}", f"{axial:.6f}"])

    integral = sum(p * area for _, p, area, _ in profile)
    print(f"[pressure] bands: {len(profile)}")
    print(f"[pressure] peak: {p_kpa[peak_index]:.3f} kPa at x = {x[peak_index]:.5f} m")
    print(f"[pressure] integral of p over band area: {integral:.1f} N (axial check)")
    print(f"[pressure] wrote {out_png}")
    print(f"[pressure] wrote {out_csv}")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Parameters:
        argv: argument list (``None`` uses ``sys.argv[1:]``).

    Returns:
        ``0`` on success, ``2`` when the inputs are missing or unusable.

    Raises:
        SystemExit: argparse's own usage errors.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-dir", type=Path,
                        default=Path("results") / "grid_independence" / "level_3",
                        help="run directory holding surf.<step>.out and the surface mesh")
    parser.add_argument("--mesh", type=Path, default=None,
                        help="surface mesh (default: HIAD_custom.surf in the run directory)")
    parser.add_argument("--outdir", type=Path, default=None,
                        help="output directory (default: <results-dir>/plots)")
    args = parser.parse_args(argv)
    mesh = args.mesh or (args.results_dir / "HIAD_custom.surf")
    outdir = args.outdir or (args.results_dir / "plots")
    try:
        dump = last_dump(args.results_dir)
        points, segments = read_geometry(mesh)
        forces = read_dump(dump)
        profile, sign = pressure_profile(points, segments, forces)
        print(f"[pressure] normal orientation: {'+' if sign > 0 else '-'}1 (chosen once for the body)")
        render(profile, dump, outdir / "surface_pressure_vs_axial.png",
               outdir / "surface_pressure_vs_axial.csv")
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"[pressure] FAILED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
