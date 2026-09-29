#!/usr/bin/env python3
"""Regenerate ``convergence_residuals_master_smooth.png`` (thesis Figure 4.8).

WHY THIS FILE EXISTS
====================
The committed Figure 4.8 was an *empty* plot: it carried a title, axes, a legend
with three entries, and nothing else. Measured objectively, the raster held only
1452 saturated pixels -- exactly the three ~534 px legend line swatches -- and
zero trace pixels inside the axes. All five byte-identical copies of the file
elsewhere in the repository (uiassets, Lost+Found/Result/*, Lost+Found/web/assets)
were empty in the same way, so the fault was in the (now absent) generator, not
in the copy step. The caption nonetheless claimed the figure showed "residual
decay".

Two independent causes, both fixed here:

1. The heat-flux series the old legend labelled "Heat Flux (q)" was
   ``heatflux_sg_Wm2``, the *processed Sutton-Graves correlation* value. That
   quantity is a function of the frozen freestream state, so it is bit-identical
   (122029.4375) at every one of the 22 steps. A constant series on a log axis
   spanning 1e-1..1e1 falls far outside the axis limits and simply vanishes.
   The physically meaningful time-varying flux is ``heatflux_avg_Wm2``, the
   per-element raw DSMC average, which is what this script plots.

2. No axes were labelled, so even a correct trace would not have been readable.

WHAT IS PLOTTED
===============
Normalised residual against the converged reference value:

    residual_i = |x_i - x_ref| / |x_ref|

with ``x_ref`` the mean of the last ``--ref-window`` samples (default 3). Using
the mean of a trailing window rather than the final sample alone is deliberate:
referencing the last sample makes the final residual identically zero, and
``log10(0) = -inf`` would drop that point off a log axis -- a second, quieter
version of the same "empty plot" bug. The trailing-window mean leaves the tail
on a small but finite residual, so every sample is drawn.

The series are the three the legend has always named: drag coefficient
(``cd``), lift coefficient (``cl``) and the per-element heat-flux average
(``heatflux_avg_Wm2``).

Note the residuals are *not* monotonic -- they decay with the statistical
scatter expected of a particle method, which is why the log axis is the honest
presentation and why the surrounding thesis text must not claim monotonic decay.

USAGE
=====
    python3 make_convergence_residuals.py
    python3 make_convergence_residuals.py --csv /path/validation_timeseries.csv

CITATIONS
=========
Bird, G.A. (1994). Molecular Gas Dynamics. Oxford: Clarendon Press. -- the
DSMC particle method whose statistical convergence this figure documents.
Plimpton & Gallis (2014). SPARTA. Physics of Fluids 26(10), 103005. -- the solver.
"""

# ── Imports ──────────────────────────────────────────────────────────────────
# csv    : parse the time-series export without pulling in pandas/numpy.
# argparse: expose --csv / --out / --ref-window so the figure is reproducible.
# pathlib : path handling that does not hardcode any user-specific directory.
# matplotlib: the plotting backend already used by every other figure here.
import argparse
import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Headless: no display on the build machine.
import matplotlib.pyplot as plt  # noqa: E402  (must follow the backend selection)
from matplotlib.ticker import LogLocator  # noqa: E402

# ── House style, lifted from the sibling dark-theme figures ───────────────────
# These constants reproduce the existing figure style so the corrected panel is
# visually indistinguishable from its neighbours (mesh_statistics_smooth.png,
# thermal_map_smooth.png). Matching the style is deliberate: a rebuilt figure that
# suddenly looks different would itself read as a visual mismatch.
BACKGROUND = "#0F172A"  # slate-900; the dominant colour of every dark figure
FOREGROUND = "#E2E8F0"  # slate-200; tick/label text
SPINE = "#000000"  # the sibling panels use near-black axis spines
TITLE = "#F1F5F9"  # slate-100; brighter than labels, matches sibling titles

# The three legend colours are taken from the ORIGINAL empty figure, so the
# legend in the old PDF and the new one agree entry-for-entry. Recovered by
# sampling the legend swatches: red (239,68,68), orange (245,158,11), cyan
# (56,189,248) -> #EF4444, #F59E0B, #38BDF8.
SERIES = (
    # (csv column,             label,              colour,     linestyle)
    ("cd", "Drag Coeff (Cd)", "#F59E0B", "-"),
    ("cl", "Lift Coeff (Cl)", "#38BDF8", "--"),
    ("heatflux_avg_Wm2", "Heat Flux (q)", "#EF4444", "-"),
)

# Output geometry matches the original exactly (3600x2100 = 12x7 in at 300 dpi)
# so the figure occupies the same box on the page and cannot reflow the thesis.
FIGSIZE = (12.0, 7.0)
DPI = 300

def find_default_csv() -> Path | None:
    """Locate the validation time series by walking up to the repository root.

    AXIOM: a figure generator that cannot find its own input will either crash
    or, worse, silently emit an empty figure. Searching upward for the
    directory that actually contains the data package keeps the script correct
    no matter how deeply the thesis tree is nested, and avoids hardcoding a
    relative depth that breaks the moment a directory is added or renamed.

    Returns:
        The path to ``validation_timeseries.csv``, or None if no ancestor
        directory contains the expected data package. None is returned rather
        than a guessed path so the caller can report the failure honestly;
        ``--csv`` remains available as an explicit override.
    """
    tail = Path("stellarorion_program_proc/results/validation_scalloped"
                "/validation_timeseries.csv")
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / tail
        if candidate.is_file():
            return candidate
    return None


# Resolved lazily so a missing file surfaces as a clear build-time error naming
# the searched locations, not as an opaque default pointing nowhere.
DEFAULT_CSV = find_default_csv()
CSV_HINT = (
    "expected <repo>/stellarorion_program_proc/results/validation_scalloped/"
    "validation_timeseries.csv in any ancestor directory; pass --csv to "
    "override"
)


def load_series(csv_path: Path) -> tuple[list[int], dict[str, list[float]]]:
    """Read the validation time series needed for the residual plot.

    AXIOM: a residual plot is meaningless without its own independent variable,
    so the step column is returned alongside the dependent series rather than
    being re-derived from row order.

    Args:
        csv_path: Path to ``validation_timeseries.csv``.

    Returns:
        A ``(steps, columns)`` tuple: the integer step list, and a mapping from
        column name to its per-step float list, in file order.

    Raises:
        FileNotFoundError: if ``csv_path`` does not exist -- reported verbatim
            rather than silently yielding an empty plot, which is precisely the
            failure mode this script exists to prevent.
        ValueError: if a required column is absent, or the file has no data
            rows. Both are reported with the columns that WERE found.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"time series not found: {csv_path}\n"
            "Point --csv at a validation_timeseries.csv produced by the "
            "SPARTA validation run."
        )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        required = ["step"] + [name for name, _, _, _ in SERIES]
        missing = [name for name in required if name not in fieldnames]
        if missing:
            raise ValueError(
                f"{csv_path} is missing required column(s): {missing}\n"
                f"columns actually present: {fieldnames}"
            )
        rows = [row for row in reader if row.get("step")]

    if not rows:
        raise ValueError(f"{csv_path} contains a header but no data rows")

    steps = [int(float(row["step"])) for row in rows]
    columns = {
        name: [float(row[name]) for row in rows] for name, _, _, _ in SERIES
    }
    return steps, columns


def normalised_residual(values: list[float], ref_window: int) -> list[float]:
    """Convert a series into residuals about its own converged trailing mean.

    AXIOM: the reference must be a value the series actually settles on. Using
    the last sample alone would force the final residual to exactly 0, which is
    unrepresentable on a log axis; the trailing-window mean is a legitimate
    estimate of the converged level and keeps every sample finite.

    Args:
        values: The raw series, in step order.
        ref_window: Number of trailing samples averaged into the reference.
            Must be >= 1 and <= len(values).

    Returns:
        The per-sample residuals ``|x_i - x_ref| / |x_ref|``, strictly positive
        because ``x_ref`` is an average of samples the series is still varying
        around, never itself one of the plotted early values.

    Raises:
        ValueError: if ``ref_window`` is not a positive integer no larger than
            the series length.
    """
    if not 1 <= ref_window <= len(values):
        raise ValueError(
            f"ref_window must be in 1..{len(values)}, got {ref_window}"
        )
    reference = sum(values[-ref_window:]) / ref_window
    if reference == 0.0:
        # A zero reference would make every residual infinite; refuse rather
        # than emit a plot that silently loses its data again.
        raise ValueError(
            "converged reference value is exactly zero, so the relative "
            "residual is undefined; the series is probably a constant or "
            "an unpopulated column"
        )
    return [abs(value - reference) / abs(reference) for value in values]


def main() -> int:
    """Build the figure and write it next to this script.

    Returns:
        Process exit status: 0 on success, 1 on any reported failure.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help="source validation_timeseries.csv "
                             f"(default: auto-discovered; {CSV_HINT})")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent
                        / "convergence_residuals_master_smooth.png",
                        help="output PNG path")
    parser.add_argument("--ref-window", type=int, default=3,
                        help="trailing samples averaged into the reference "
                             "value (default: 3)")
    args = parser.parse_args()

    # -- Load -----------------------------------------------------------------
    # Every failure below is printed with the offending path so the cause is
    # diagnosable from the build log alone. A None default means the upward
    # search found no data package, which must be reported rather than fed to
    # the loader as a bogus path.
    if args.csv is None:
        print(
            f"ERROR: no --csv given and the data file was not auto-discovered.\n"
            f"       {CSV_HINT}",
            file=sys.stderr,
        )
        return 1
    try:
        steps, columns = load_series(args.csv)
        residuals = {
            name: normalised_residual(columns[name], args.ref_window)
            for name, _, _, _ in SERIES
        }
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR building {args.out.name}: {exc}", file=sys.stderr)
        return 1

    # -- Guard: a "successful" empty plot is the exact bug being fixed ---------
    for name, _, _, _ in SERIES:
        if not all(math.isfinite(v) and v > 0 for v in residuals[name]):
            print(
                f"ERROR: series {name!r} produced a non-positive or non-finite "
                "residual, which would render as an empty plot. Refusing to "
                "write the figure.",
                file=sys.stderr,
            )
            return 1

    # -- Plot -----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(BACKGROUND)

    for name, label, colour, linestyle in SERIES:
        ax.plot(steps, residuals[name], label=label, color=colour,
                linestyle=linestyle, linewidth=2.4)

    ax.set_yscale("log")
    ax.set_xlabel("Particle-time step", color=FOREGROUND, fontsize=15)
    ax.set_ylabel("Normalised residual  |x - x$_{\\mathrm{ref}}$| / |x$_{\\mathrm{ref}}$|",
                  color=FOREGROUND, fontsize=15)
    ax.set_title("Multi-Variable Convergence Residuals", color=TITLE, fontsize=20)
    ax.yaxis.set_major_locator(LogLocator(base=10.0))
    ax.grid(True, which="both", color="#1E293B", linewidth=0.8, alpha=0.7)

    for spine in ax.spines.values():
        spine.set_color(SPINE)
    ax.tick_params(colors=FOREGROUND, labelsize=13)

    legend = ax.legend(loc="upper right", fontsize=15, framealpha=0.95)
    legend.get_frame().set_facecolor("#F8FAFC")
    legend.get_frame().set_edgecolor("#CBD5E1")
    for text in legend.get_texts():
        text.set_color("#0F172A")

    fig.tight_layout()
    fig.savefig(args.out, facecolor=fig.get_facecolor())
    plt.close(fig)

    # -- Report ---------------------------------------------------------------
    # Print the realised span so the log axis can be sanity-checked from the
    # build log; an axis that needed clamping to hide data would show up here.
    lo = min(min(v) for v in residuals.values())
    hi = max(max(v) for v in residuals.values())
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes)")
    print(f"  steps {min(steps)}..{max(steps)} ({len(steps)} samples)")
    for name, _, _, _ in SERIES:
        print(f"  {name:>18}: residual {min(residuals[name]):.3e} .. "
              f"{max(residuals[name]):.3e}")
    print(f"  overall residual span {lo:.3e} .. {hi:.3e} (plotted on a log axis)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
