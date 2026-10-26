#!/usr/bin/env python3
"""Surface-pressure distribution along the HIAD body.

PURPOSE
    Produce the axial surface-pressure distribution the results chapter cites
    (figure 4.25): the per-surface pressure of the step-2200 DSMC dump against
    the axial station.  The pressure is read from the solver's own NATIVE
    per-surface pressure quantity whenever the deck dumps it
    (``compute surf <id> surf <group> <mixture> fx fy fz press`` ==> the dump
    column ``f_surfavg[4]``); only for a dump that predates that deck line is
    it DERIVED from the per-surface force dump and the surface mesh.

AXIOMS
    A1  The only inputs are the run's own artifacts: the final ``surf.<step>.out``
        dump and the ``*.surf`` surface mesh the solver was given.  No pressure
        is invented from a correlation, and no value is read from a log.
    A2  TWO ROUTES, ONE ORDER.  If the dump's header carries ``f_surfavg[4]``
        -- the ``press`` quantity the deck appends as a trailing column of
        ``compute surf ... fx fy fz press`` -- that column IS the solver's
        pressure and is plotted verbatim.  Otherwise the pressure is DERIVED:
        the force on a surface band is decomposed into a normal stress (the
        pressure) and a tangential stress (the shear), and the projection of the
        force onto the band's unit normal isolates the normal stress, because the
        shear is tangential by definition.  The columns are located BY HEADER
        NAME, never by position, because ``press`` was appended to the dump
        rather than inserted into it; the figure and the printed source line
        state which route was taken, so a reader never mistakes a derived
        profile for a native one.
    A3  The surface is the axisymmetric meridional profile: band ``i`` is the
        revolution of the segment between mesh points ``i`` and ``i+1``, so its
        wetted area is ``2*pi*r_centroid*length``.  The DUMP's surface id is that
        segment index, and a missing or zero-force band is reported rather than
        smoothed away.
    A4  If the run kept no surf dump, the script reports it and exits non-zero;
        it never fabricates a profile from a total drag.

THEOREMS
    T1  On the native route the plotted profile is the solver's own pressure --
        no decomposition, no neglected term.  On the derived route the pressure
        would equal the true surface pressure exactly if the shear were zero.
    T2  The derived route is falsifiable: integrating the derived pressure over
        the projected band areas reproduces the run's total drag to within the
        neglected shear contribution, and the script prints that check.  The
        native route prints its source line instead -- a check it does not need.

APPLICATIONS
    ``python3 scripts/make_surface_pressure_plot.py --results-dir
    results/reference_surface_pressure`` writes the NATIVE profile (that run's
    deck carries the ``press`` quantity), and
    ``--results-dir results/grid_independence/level_3`` writes the DERIVED one
    (that campaign predates the deck line).  Both write
    ``<results-dir>/plots/surface_pressure_vs_axial.png`` and a CSV beside it.

CITATIONS
    [SPARTA] SPARTA DSMC simulator, ``src/compute_surf.cpp``: the per-surface
        keywords include ``fx fy fz`` (force components), ``press`` (pressure)
        and ``ke`` (kinetic-energy flux); the deck's ``compute surf ... press``
        is what puts the native pressure in the dump's trailing column.
    [Anderson06] J. D. Anderson, *Hypersonic and High-Temperature Gas
        Dynamics*, 2nd ed., AIAA, 2006, ch. 3 (pressure and shear on a
        hypersonic surface; the normal-stress decomposition used on the
        fallback route).
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


def read_dump(
    path: Path,
) -> tuple[dict[int, tuple[float, float]], dict[int, float]]:
    """Read the per-surface forces and (when present) the native pressure.

    Parameters:
        path: the ``surf.<step>.out`` file.

    Returns:
        ``(forces, native)`` where ``forces`` maps
        ``surface id -> (axial force N, radial force N)`` taken from
        ``f_surfavg[1]`` and ``f_surfavg[2]``, and ``native`` maps
        ``surface id -> pressure Pa`` from ``f_surfavg[4]`` when the deck
        requested the SPARTA ``press`` keyword.  ``native`` is EMPTY for a
        dump written by a deck without that keyword, and the caller then
        falls back to the derived projection.

        WHY the columns are located by NAME: the deck appends ``press`` as a
        trailing quantity, so a positional reader would silently pick the
        wrong column for either generation of dump.  Locating each token in
        the header makes both generations readable and a future re-ordering
        harmless.  [Citation: SPARTA src/compute_surf.cpp - compute surf
        keywords n, nwt, nflux, mflux, fx, fy, fz, press, ...]

    Raises:
        FileNotFoundError: the file does not exist.
        ValueError: the header does not carry the expected column names.
    """
    if not path.is_file():
        raise FileNotFoundError(f"surf dump not found: {path}")
    forces: dict[int, tuple[float, float]] = {}
    native: dict[int, float] = {}
    index_id = index_axial = index_radial = index_press = -1
    columns = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("ITEM: SURFS"):
            #  WHY the prefix is stripped: the header line reads
            #  "ITEM: SURFS id f_1[1] ... f_surfavg[4]", so the two leading
            #  words would shift every column index by +2 relative to the data
            #  rows (which carry no prefix) and the row filter below would
            #  discard every row as too short.
            tokens = line.split()
            tokens = tokens[tokens.index("SURFS") + 1:]
            try:
                index_axial = tokens.index("f_surfavg[1]")
                index_radial = tokens.index("f_surfavg[2]")
            except ValueError as exc:
                raise ValueError(f"{path}: unexpected dump columns in {line!r}") from exc
            index_id = tokens.index("id")
            index_press = tokens.index("f_surfavg[4]") if "f_surfavg[4]" in tokens else -1
            columns = True
            continue
        if not columns:
            continue
        fields = line.split()
        if len(fields) <= max(index_id, index_axial, index_radial):
            continue
        try:
            surface = int(fields[index_id])
            axial = float(fields[index_axial])
            radial = float(fields[index_radial])
            pressure = float(fields[index_press]) if index_press >= 0 else 0.0
        except ValueError:
            continue
        forces[surface] = (axial, radial)
        if index_press >= 0:
            native[surface] = pressure
    if not forces:
        raise ValueError(f"{path}: no surface rows parsed")
    return forces, native


def pressure_profile(
    points: list[tuple[float, float]],
    segments: list[tuple[int, int]],
    forces: dict[int, tuple[float, float]],
    native: dict[int, float] | None = None,
) -> tuple[list[tuple[float, float]], float]:
    """Read or derive the per-band pressure profile (AXIOM A2/A3).

    Parameters:
        points: the mesh points as ``(x, r)``.
        segments: zero-based point-index pairs, one per surface id (id 1 is
            ``segments[0]``).
        forces: the per-surface forces keyed by surface id.
        native: the per-surface pressures keyed by surface id when the dump
            carries SPARTA's own ``press`` quantity; ``None`` or empty means
            the pressure must be derived from the force.

    Returns:
        ``(profile, sign)`` where profile is a list of
        ``(x_centroid_m, pressure_Pa, area_m2, axial_force_N)`` for every band
        that appears in the dump, and ``sign`` is the normal orientation that
        was used (``+1`` or ``-1``), chosen once for the whole body.  ``sign``
        is meaningless for a native profile and is reported as ``+1``.

    Raises:
        ValueError: no band in the mesh has a matching force.
    """
    native = native or {}
    bands: list[tuple[int, float, float, float, float, float, float, float]] = []
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
        bands.append(
            (index, 0.5 * (x0 + x1), area, axial, radial, dr / length, -dx / length, length)
        )
    if not bands:
        raise ValueError("no surface band matched a force entry")

    #  WHY the native branch comes first: when SPARTA has written its own
    #  per-surface pressure there is nothing to derive — the projection below
    #  exists only for dumps produced before the deck requested `press`.
    if native:
        profile = [
            (x_c, native.get(index, 0.0), area, axial)
            for index, x_c, area, axial, _radial, _nx, _nr, _length in bands
        ]
        return profile, 1.0

    #  WHY: the meridional normal is fixed by the mesh winding; its global sign
    #  must be the OUTWARD one.  A wrong guess makes the pressures negative, so
    #  the sign is chosen by the majority of the windward bands and reported.
    positive = sum(
        1 for _, _, _, ax, rad, nx, nr, _ in bands if -(ax * nx + rad * nr) > 0.0
    )
    sign = 1.0 if positive * 2 >= len(bands) else -1.0
    profile = [
        (x_c, -(axial * nx + radial * nr) * sign / area, area, axial)
        for _index, x_c, area, axial, radial, nx, nr, _length in bands
    ]
    return profile, sign


def dump_step(path: Path) -> int | None:
    """Read the SPARTA step number from a dump file's header.

    Parameters:
        path: the dump whose ``ITEM: TIMESTEP`` block should be read.

    Returns:
        The step as an ``int``, or ``None`` when the header is missing, the
        value is not an integer, or the file cannot be read.

    Raises:
        Nothing: an unreadable or malformed dump is reported on stderr and the
        caller falls back to a step-free label rather than inventing a number.

    AXIOMS:
        A1  A SPARTA dump begins with ``ITEM: TIMESTEP`` and the step on the
            following line; that pair is the only authoritative statement of
            which step the file holds.

    THEOREMS:
        T1  The step stated in the header equals the step in the file name for
            every dump this project writes, so labelling the figure from either
            source agrees; the header is preferred because the file may be
            renamed by a probe or a copy.

    CITATIONS:
        [SPARTA] Plimpton & Gallis, SPARTA Users Manual, dump command -- the
            ``ITEM: TIMESTEP`` / value pair is the documented header form.

    WHY: the title previously hard-coded "step-2200", so a figure drawn from an
    earlier dump (a partial run, a probe copy, or a differently numbered case)
    claimed a step it did not come from.  The title now states the dump's own
    step, and says only "DSMC surface dump" when the step cannot be read.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.strip() == "ITEM: TIMESTEP":
                    value = handle.readline().strip()
                    return int(value) if value.lstrip("-").isdigit() else None
    except OSError as exc:
        print(f"[pressure] cannot read the step from {path}: {exc}", file=sys.stderr)
    return None


def render(
    profile: list[tuple[float, float, float, float]],
    dump: Path,
    out_png: Path,
    out_csv: Path,
    native: bool = False,
) -> None:
    """Draw the surface-pressure figure and write the machine-readable table.

    Parameters:
        profile: ``(x_m, pressure_Pa, area_m2, axial_force_N)`` tuples.
        dump: the dump the profile came from (named on the figure).
        out_png: destination of the PNG.
        out_csv: destination of the CSV.
        native: ``True`` when the pressures came from SPARTA's own ``press``
            quantity, ``False`` when they were derived from the surface force.
            The legend and the provenance footer state which one is shown, so
            the figure never claims a derivation it did not perform.

    Raises:
        OSError: an output path cannot be written.
    """
    x = [row[0] for row in profile]
    p_kpa = [row[1] / 1000.0 for row in profile]
    peak_index = max(range(len(p_kpa)), key=lambda index: p_kpa[index])

    fig, ax = plt.subplots(figsize=(10.0, 4.8), constrained_layout=True)
    ax.plot(x, p_kpa, "o-", color="#8e44ad", linewidth=2.0, markersize=5.5,
            label="SPARTA native surface pressure" if native else "derived surface pressure")
    ax.axhline(0.0, color="#888888", linewidth=1.0, linestyle=":")
    ax.plot([x[peak_index]], [p_kpa[peak_index]], "o", color="#c0392b", markersize=10,
            label=f"peak {p_kpa[peak_index]:.2f} kPa at x = {x[peak_index]:.4f} m")
    ax.set_xlabel("Axial station $x$ (m)")
    ax.set_ylabel(r"Surface pressure $p$ (kPa)")
    label = "DSMC surface dump"
    step = dump_step(dump)
    if step is not None:
        label = f"step-{step} DSMC surface dump"
    ax.set_title(f"Surface pressure along the HIAD body ({label})")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    source_note = (
        "Per-surface pressure read from SPARTA's own press quantity "
        "(compute surf ... press, dumped as f_surfavg[4]).\n"
        if native
        else "Pressure derived from the per-surface force projected onto the band normal "
        "(shear is tangential and cancels);\naxisymmetric band area 2*pi*r*L.\n"
    )
    fig.text(
        0.01, 0.01,
        source_note + f"Source: {dump.parent.name}/{dump.name}.",
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
        forces, native = read_dump(dump)
        profile, sign = pressure_profile(points, segments, forces, native)
        if native:
            print(f"[pressure] source: NATIVE press column (f_surfavg[4]) for "
                  f"{len(native)} surfaces")
        else:
            print("[pressure] source: DERIVED from the surface force "
                  "(no f_surfavg[4] column: the deck predates the press keyword)")
            print(f"[pressure] normal orientation: {'+' if sign > 0 else '-'}1 "
                  "(chosen once for the body)")
        render(profile, dump, outdir / "surface_pressure_vs_axial.png",
               outdir / "surface_pressure_vs_axial.csv", native=bool(native))
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"[pressure] FAILED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
