#!/usr/bin/env python3
"""Render the axial temperature trace through a scallop pocket of the HIAD body.

WHY THIS SCRIPT EXISTS
    The thesis figure ``scallop_pocket_temp_smooth_M0_A0.png`` is an axial trace
    through the centre of a single scallop pocket, and for a while no script in
    the repository could reproduce it: the only scallop renderer here
    (``generate_field_panels.render_scallop_pocket``) draws a different picture,
    a scatter of the surface coloured by radiative-equilibrium temperature, so
    the included panel was an orphan artifact whose numbers nobody could re-derive.
    This module rebuilds that panel from the run that the caption names, and it
    prints the peak so the caption's claim can be checked instead of trusted.

WHAT IT SAMPLES
    The probe is a radial band through the pocket skirt, not the centreline.
    A pocket sits on the toroid skirt; the reference body's skirt spans roughly
    r = 0.75 m to r = 1.83 m, so the band [0.80, 1.00] m passes through the
    pockets of the first toroid.  Cells in that band are ordered by axial
    position, and the temperature is the grid dump's own ``f_3`` quantity
    (``compute 3 thermal/grid all air temp``), i.e. the cell gas temperature -
    not a surface radiative-equilibrium value, which for this run peaks near
    2.3e3 K and therefore cannot explain a 3.6e3 K reading.

AXIOMS
    A1  ``grid.<step>.out`` carries ``id xlo ylo xhi yhi f_2[*] f_3[*] f_4[*]``
        and ``f_3`` is the cell gas temperature in kelvin; the header line is
        prefixed with ``ITEM: CELLS`` and that prefix MUST be stripped or every
        column index shifts by two and every row is discarded.
    A2  A scallop pocket is a toroidal valley, so a horizontal band at fixed
        radius intersects the pocket at every axial station of the skirt.
    A3  A cell with zero molecules carries T = 0.0; that is missing data, not a
        cold pocket, so those samples are gaps in the trace and never plotted
        as if they were measurements.
    A4  The deck names the ambient at the inlet; the trace is only legible
        against that reference, so it is drawn explicitly.

THEOREMS
    T1  Within one axial bin every cell of the band is at the same axial
        station, so the bin maximum is the pocket temperature at that station
        and the bin median is the bulk value behind it; reporting both keeps a
        single hot cell from being mistaken for the pocket.
    T2  The axial bins are contiguous, so the peak of the binned profile is the
        peak of the sampled trace, and its axial coordinate is the leading edge
        of the pocket shock.

CITATIONS
    [SPARTA] Plimpton & Gallis, SPARTA Users Manual - the ``dump`` and
        ``compute thermal/grid`` commands, and the header layout of a grid dump.
    [Capt]   Chapter 4 of this thesis, the caption of ``fig:scallop_pocket``,
        which states the run condition (M = 7.53, T_inf = 267.85 K, 19321
        cell grid) and the claimed peak of approximately 3.6e3 K.

APPLICATIONS
    Called by hand while verifying the figure, and by
    ``generate_field_panels.py`` when a scallop trace is wanted:

        venv_validation/bin/python3 scripts/make_scallop_pocket_trace.py \\
            --dump results/00_reference/grid.2200.out

    Writes ``scallop_pocket_temp_smooth_M0_A0.{png,csv}`` beside the dump's
    tree under ``plots/``, and prints the measured peak.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_DUMP = PROJECT_ROOT / "results" / "00_reference" / "grid.2200.out"
POCKET_INNER_M = 0.80
POCKET_OUTER_M = 1.00
AMBIENT_T_K = 267.85
SMOOTH_WINDOW = 3
FIGURE_STEM = "scallop_pocket_temp_smooth_M0_A0"


def read_grid_dump(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Read the cells of one SPARTA grid dump.

    Parameters:
        path: the ``grid.<step>.out`` file to read.

    Returns:
        ``(xlo, ylo, temperature, step)`` - the axial and radial lower cell
        corners and the cell gas temperature, plus the step number carried by
        the dump header.

    Raises:
        FileNotFoundError: the dump does not exist.
        RuntimeError: the header or the data block is missing, or the step
            cannot be read.

    AXIOMS:
        A1  The dump begins with ``ITEM: TIMESTEP`` and the step on the next
            line; that pair is the only authoritative statement of the step.
        A2  The cells header is ``ITEM: CELLS id xlo ylo xhi yhi f_2[*] f_3[*]
            f_4[*]``, so the first two tokens are a prefix and not columns.

    THEOREMS:
        T1  With the prefix stripped, the index of ``f_3[*]`` in the header is
            the index of the temperature in a data row, so no positional
            constant has to be hard-coded.
    """
    if not path.is_file():
        raise FileNotFoundError(f"grid dump not found: {path}")
    lines = path.read_text(encoding="ascii", errors="replace").splitlines()

    step = None
    for idx, line in enumerate(lines):
        if line.strip() == "ITEM: TIMESTEP" and idx + 1 < len(lines):
            value = lines[idx + 1].strip()
            if value.lstrip("-").isdigit():
                step = int(value)
            break
    if step is None:
        raise RuntimeError(f"no readable ITEM: TIMESTEP block in {path}")

    header_idx = None
    for idx, line in enumerate(lines):
        if line.startswith("ITEM: CELLS"):
            header_idx = idx
            break
    if header_idx is None:
        raise RuntimeError(f"no ITEM: CELLS header in {path}")

    #  AXIOM A2: the two leading tokens are the prefix, not column names.
    header = lines[header_idx].split()[2:]
    try:
        temp_col = header.index("f_3[*]")
    except ValueError as exc:
        raise RuntimeError(f"no f_3[*] column in {path}") from exc

    x_lo: list[float] = []
    r_lo: list[float] = []
    temp: list[float] = []
    for line in lines[header_idx + 1:]:
        parts = line.split()
        if len(parts) < len(header):
            continue
        x_lo.append(float(parts[1]))
        r_lo.append(float(parts[2]))
        temp.append(float(parts[temp_col]))
    if not temp:
        raise RuntimeError(f"no data rows under the cells header of {path}")
    return np.array(x_lo), np.array(r_lo), np.array(temp), step


def pocket_profile(x_lo: np.ndarray, r_lo: np.ndarray, temp: np.ndarray,
                   inner: float, outer: float) -> list[dict]:
    """Bin the pocket band by axial station.

    Parameters:
        x_lo: axial lower cell corners (m).
        r_lo: radial lower cell corners (m).
        temp: cell gas temperature (K).
        inner: inner radius of the pocket band (m).
        outer: outer radius of the pocket band (m).

    Returns:
        One dict per axial station, sorted by ``x_m``, with ``x_m``, ``n``,
        ``t_max`` (pocket value) and ``t_med`` (bulk behind it).  A station with
        no molecule in the band reports ``n = 0`` and ``None`` temperatures, so
        the caller draws a gap rather than a fabricated zero.

    Raises:
        ValueError: the band is empty or inverted.

    AXIOMS:
        A1  A cell with zero molecules carries T = 0.0 and is missing data.
        A2  Cells sharing an axial lower corner belong to the same station.

    THEOREMS:
        T1  Taking the maximum within a station reports the pocket temperature;
            taking the median reports the bulk gas, so the pair separates the
            pocket from its surroundings without filtering either.
    """
    if outer <= inner:
        raise ValueError("pocket band is inverted")
    in_band = (r_lo >= inner) & (r_lo < outer)
    if not in_band.any():
        raise ValueError(f"no cells in the pocket band r = [{inner}, {outer}] m")

    stations: dict[float, list[float]] = {}
    for x, t in zip(x_lo[in_band], temp[in_band], strict=False):
        stations.setdefault(round(float(x), 6), []).append(float(t))

    rows: list[dict] = []
    for x in sorted(stations):
        values = [v for v in stations[x] if v > 0.0]
        if values:
            rows.append({"x_m": x, "n": len(values),
                         "t_max": max(values), "t_med": float(np.median(values))})
        else:
            rows.append({"x_m": x, "n": 0, "t_max": None, "t_med": None})
    return rows


def smooth(values: np.ndarray, window: int) -> np.ndarray:
    """Centred rolling mean that ignores gaps.

    Parameters:
        values: the profile, with NaN where a station has no data.
        window: how many stations to average, must be odd.

    Returns:
        The smoothed profile, NaN wherever every station in the window is NaN.

    Raises:
        ValueError: the window is not a positive odd number.

    AXIOMS:
        A1  The plot is a trace, not a field: adjacent stations differ only by
            sampling noise, so averaging neighbours removes noise, not signal.
        A2  A gap is not a zero; it must stay a gap after smoothing.

    THEOREMS:
        T1  A centred mean of an odd window keeps the abscissa of a symmetric
            feature unchanged, so smoothing cannot shift the reported peak.
    """
    if window < 1 or window % 2 == 0:
        raise ValueError("smoothing window must be a positive odd number")
    half = window // 2
    out = np.full_like(values, np.nan, dtype=float)
    for idx in range(len(values)):
        lo = max(0, idx - half)
        hi = min(len(values), idx + half + 1)
        chunk = values[lo:hi]
        chunk = chunk[~np.isnan(chunk)]
        if chunk.size:
            out[idx] = float(np.mean(chunk))
    return out


def render(rows: list[dict], step: int, source: Path, outdir: Path) -> tuple[Path, Path]:
    """Draw the trace and write the table behind it.

    Parameters:
        rows: the binned profile from :func:`pocket_profile`.
        step: the dump step, stamped in the title.
        source: the dump the profile came from, named in the footer.
        outdir: destination directory.

    Returns:
        ``(png_path, csv_path)``.

    Raises:
        RuntimeError: no station carries a temperature.
        OSError: the figure cannot be written.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.array([row["x_m"] for row in rows], dtype=float)
    t_max = np.array([np.nan if row["t_max"] is None else row["t_max"] for row in rows],
                     dtype=float)
    t_med = np.array([np.nan if row["t_med"] is None else row["t_med"] for row in rows],
                     dtype=float)
    if np.all(np.isnan(t_max)):
        raise RuntimeError(f"{source}: no station carries a temperature")

    t_smooth = smooth(t_max, SMOOTH_WINDOW)
    peak_idx = int(np.nanargmax(t_max))
    peak_t = float(t_max[peak_idx])
    peak_x = float(x[peak_idx])

    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / f"{FIGURE_STEM}.png"
    table = outdir / f"{FIGURE_STEM}.csv"

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    #  WHY: the provenance footer is two lines of text below the axis, so the
    #  axes are given an explicit bottom margin; constrained_layout cannot see
    #  fig.text and the first render had the footer overrun the x label.
    fig.subplots_adjust(left=0.080, right=0.985, top=0.905, bottom=0.255)
    ax.plot(x, t_max, color="#b0b0b0", linewidth=0.8, marker=".", markersize=2.5,
            label="station maximum (pocket)")
    ax.plot(x, t_med, color="#2c7fb8", linewidth=0.9, alpha=0.85,
            label="station median (bulk behind the pocket)")
    ax.plot(x, t_smooth, color="#c0392b", linewidth=1.8,
            label=f"pocket trace (rolling mean, {SMOOTH_WINDOW} stations)")
    ax.axhline(AMBIENT_T_K, color="#1f77b4", linestyle="--", linewidth=1.0,
               alpha=0.8, label=f"freestream {AMBIENT_T_K:.0f} K")
    ax.axhline(3600.0, color="#7f7f7f", linestyle=":", linewidth=1.0,
               label="3.6e3 K (caption claim)")
    ax.plot([peak_x], [peak_t], marker="o", markersize=7, color="#111111",
            markerfacecolor="none")
    ax.annotate(f"peak {peak_t:.0f} K at x = {peak_x:.4f} m",
                xy=(peak_x, peak_t), xytext=(peak_x + 0.4, peak_t - 350.0),
                fontsize=8.5, color="#111111",
                arrowprops={"arrowstyle": "->", "color": "#555555", "lw": 0.9})
    ax.set_xlabel("Axial position (m)")
    ax.set_ylabel("Temperature (K)")
    ax.set_title(f"Scallop pocket axial trace (step-{step} DSMC grid dump)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_ylim(0.0, max(peak_t * 1.25, 4500.0))
    fig.text(0.012, 0.128,
             f"Source: {source.name}. Probe band r = [{POCKET_INNER_M:.2f}, "
             f"{POCKET_OUTER_M:.2f}] m (the pocket skirt). Quantity: cell gas "
             "temperature (compute 3 thermal/grid all air temp, dumped as f_3).",
             fontsize=6.6, color="#444444")
    fig.text(0.012, 0.086,
             "Gaps are axial stations with no molecule in the band, not zero kelvin; "
             "the dotted line marks the 3.6e3 K quoted in the caption.",
             fontsize=6.6, color="#444444")
    fig.savefig(png, dpi=200)
    plt.close(fig)

    with table.open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x_m", "n_cells", "t_max_K", "t_median_K", "t_smooth_K"])
        for idx, row in enumerate(rows):
            writer.writerow([
                f"{row['x_m']:.6f}", row["n"],
                "" if row["t_max"] is None else f"{row['t_max']:.2f}",
                "" if row["t_med"] is None else f"{row['t_med']:.2f}",
                "" if np.isnan(t_smooth[idx]) else f"{t_smooth[idx]:.2f}",
            ])

    print(f"[scallop] source: {source}")
    print(f"[scallop] probe band: r = [{POCKET_INNER_M}, {POCKET_OUTER_M}] m")
    print(f"[scallop] stations: {len(rows)} ({sum(1 for r in rows if r['n']) } carrying data)")
    print(f"[scallop] peak: {peak_t:.1f} K at x = {peak_x:.4f} m")
    print(f"[scallop] wrote {png}")
    print(f"[scallop] wrote {table}")
    return png, table


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Parameters:
        argv: command line arguments, defaults to ``sys.argv[1:]``.

    Returns:
        0 on success, 2 when the dump or the band cannot be used.

    Raises:
        Nothing: every failure is reported on stderr and mapped to exit code 2.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP,
                        help="grid dump to sample")
    parser.add_argument("--inner", type=float, default=POCKET_INNER_M,
                        help="inner radius of the pocket band (m)")
    parser.add_argument("--outer", type=float, default=POCKET_OUTER_M,
                        help="outer radius of the pocket band (m)")
    parser.add_argument("--outdir", type=Path, default=None,
                        help="destination directory (default: <tree>/plots)")
    args = parser.parse_args(argv)

    outdir = args.outdir if args.outdir is not None else args.dump.parent / "plots"
    try:
        x_lo, r_lo, temp, step = read_grid_dump(args.dump)
        rows = pocket_profile(x_lo, r_lo, temp, args.inner, args.outer)
        render(rows, step, args.dump, outdir)
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"[scallop] FAILED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
