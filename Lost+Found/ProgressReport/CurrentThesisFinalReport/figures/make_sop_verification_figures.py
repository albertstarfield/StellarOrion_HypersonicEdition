"""Render the SOP verification-evidence figures for the results chapter.

The CFD Standard Operating Procedure (Chapters 5, 6, 8, 12 and 13) requires
three specific pieces of evidence before a result may be shown to anyone: a
mesh-quality record quoted as numbers, a mesh-independence study on
systematically refined meshes, and convergence evidence. This module draws
exactly those three figures from the artefacts the engine already emits.

AXIOMS
------
A1. The raw records are authoritative and are never recomputed here by
    preference. The three refinement levels come from the solver records at
    ``stellarorion_program_proc/results/grid_independence/level_*/case.json``
    and the mesh and stationarity records from
    ``stellarorion_program_proc/results/99_shared/sop/*.csv``.
A2. The mesh-independence tolerance is OWNER-SET, not derived. It is imported
    from the program itself (``TOLERANCE_PCT`` in
    ``scripts/generate_sop_artifacts.py``) so that the figure and the gate can
    never disagree. The constant was moved from 5 % to 10 % by owner decision
    on 2026-10-16; the on-disk aggregate JSON predates that decision and
    still records the 5 % verdict, which this figure deliberately reports
    both ways rather than picking one silently.
A3. The quantity of interest is the SPARTA peak surface kinetic-energy flux
    (``compute heat reduce max f_1[3]``), a per-cell sampling maximum, not a
    physically resolved heat flux. The refinement levels also carry different
    simulated particle counts, so the measured change mixes discretisation
    with sampling and the figure says so.
A4. On an axis-aligned Cartesian grid the classic skewness and orthogonal-
    quality gates are satisfied by construction. They are reported because the
    SOP asks for them, and the figure states that they carry no
    discriminating information here.

THEORIES
--------
T1. Mesh independence is the statement that the quantity of interest stops
    moving under refinement. With levels ordered by cell count, the relative
    change of the finest pair is the gate quantity (the program's own
    ``_convergence_analysis`` supplies the observed order, the Richardson
    extrapolation and the GCI estimate, which are quoted verbatim rather than
    re-derived, so two implementations cannot drift apart).
T2. A gate that is met is not a statement that the quantity is accurate: the
    estimated extrapolated error and the GCI are shown next to the tolerance
    so the reader can see that the numerical uncertainty is of the same order
    as the tolerance itself.
T3. For DSMC the convergence analogue is a sampling transient. Particle
    retention and the stationarity indicator are the honest quantities to
    show, and the 2 % window criterion that the methodology states for the
    drag coefficient and the stagnation heat flux is drawn for scale only,
    because it is not defined for a particle census.

APPLICATIONS
------------
Writes three PNGs beside this file:

- ``sop_grid_independence.png``   three-level study, deltas, tolerance band,
                                  convergence evidence
- ``sop_mesh_quality_record.png`` gate utilisation plus the cut-cell census
- ``sop_dsmc_stationarity.png``   particle retention and stationarity

Reads only; writes three PNGs. Exits non-zero with a diagnostic naming the
missing artefact, so a silently half-drawn figure is impossible.

CITATIONS
---------
    [Citation: Matplotlib v3.11.2 - https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html]
    [Based on: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subplots_demo.html]
    [Reference: Celik et al., J. Fluids Eng. 130 (2008) 078001, GCI method,
     as cited by scripts/generate_sop_artifacts.py]
    [Reference: SPARTA compute reduce, https://lammps.sandia.gov/doc/compute_reduce.html]
    [Reference: RFC 4180 CSV, https://www.rfc-editor.org/rfc/rfc4180]
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = Path(__file__).resolve().parent
PROC_NAME = "stellarorion_program_proc"
SOP_ARTIFACTS = None  # resolved in find_program_root()
GI_DIR = None
SOP_DIR = None
WCM2 = 1.0e4
TREES = ("00_reference", "03_opt_geometry")


class ArtifactError(RuntimeError):
    """Raised when a required measurement artefact is absent or malformed."""


def find_program_root() -> Path:
    """Locate the engine project by walking up from this file.

    The figure script lives inside the thesis directory tree, which is itself
    nested inside the repository, so the engine project is found by walking
    up until an ancestor containing a ``stellarorion_program_proc`` directory
    is reached. A counted parent index is deliberately not used: moving the
    thesis directory would silently repoint every path.

    Returns:
        Path of the engine project directory.

    Raises:
        ArtifactError: If no ancestor directory contains the project.
    """
    # pylint: disable=global-statement
    global SOP_ARTIFACTS, GI_DIR, SOP_DIR
    for base in (FIG_DIR, *FIG_DIR.parents):
        candidate = base / PROC_NAME
        if candidate.is_dir():
            SOP_ARTIFACTS = candidate / "scripts" / "generate_sop_artifacts.py"
            GI_DIR = candidate / "results" / "grid_independence"
            SOP_DIR = candidate / "results" / "99_shared" / "sop"
            return candidate
    raise ArtifactError(
        f"no {PROC_NAME} directory found at or above {FIG_DIR}; "
        "run this script from the thesis figures directory"
    )


def load_program() -> object:
    """Import the program's SOP artefact generator as a module.

    The module is imported for its constants and its convergence analysis
    only. Its ``main`` is guarded by ``__main__``, so importing runs no
    generator and writes nothing.

    Returns:
        The imported module object.

    Raises:
        ArtifactError: If the program source is missing or does not define
            the tolerance constants this figure is required to honour.
    """
    if not SOP_ARTIFACTS.is_file():
        raise ArtifactError(f"program artefact generator not found: {SOP_ARTIFACTS}")
    spec = importlib.util.spec_from_file_location("_sop_artifacts", SOP_ARTIFACTS)
    if spec is None or spec.loader is None:
        raise ArtifactError(f"cannot build an import spec for {SOP_ARTIFACTS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("TOLERANCE_PCT", "TOLERANCE_SOURCE", "_convergence_analysis"):
        if not hasattr(module, name):
            raise ArtifactError(f"{SOP_ARTIFACTS.name} defines no {name}")
    return module


def load_levels() -> list[dict[str, object]]:
    """Read the three refinement-level solver records in ascending cell order.

    Returns:
        The level records sorted by ``n_cells``.

    Raises:
        ArtifactError: If fewer than three level records exist, if a record
            lacks ``n_cells`` or ``qoi_value``, or if a level did not run.
    """
    records: list[dict[str, object]] = []
    if not GI_DIR.is_dir():
        raise ArtifactError(f"no grid-independence directory: {GI_DIR}")
    for case_json in sorted(GI_DIR.glob("level_*/case.json")):
        try:
            with case_json.open("r", encoding="utf-8") as handle:
                records.append(json.load(handle))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"unreadable level record {case_json}: {exc}") from exc
    if len(records) < 3:
        raise ArtifactError(
            f"{len(records)} of 3 refinement levels present under {GI_DIR}; "
            "run scripts/run_grid_independence.py first"
        )
    for record in records:
        if record.get("status") != "ok":
            raise ArtifactError(
                f"level {record.get('level', '?')} did not run "
                f"(status={record.get('status')!r}); refusing to plot it"
            )
        for key in ("n_cells", "qoi_value"):
            if key not in record:
                raise ArtifactError(f"level record {record.get('level')} lacks {key}")
    return sorted(records, key=lambda rec: float(rec["n_cells"]))


def load_rows(path: Path) -> list[dict[str, str]]:
    """Read one CSV of measurement records.

    Args:
        path: CSV file to read.

    Returns:
        The rows as dictionaries keyed by header name.

    Raises:
        ArtifactError: If the file is missing, unreadable or has no header.
    """
    if not path.is_file():
        raise ArtifactError(f"missing artefact: {path}")
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        raise ArtifactError(f"unreadable artefact {path}: {exc}") from exc
    if not rows:
        raise ArtifactError(f"empty artefact: {path}")
    return rows


def load_mesh_quality(tree: str) -> dict[str, dict[str, str]]:
    """Read the mesh-quality record for one result tree.

    Args:
        tree: Result-tree name, for example ``00_reference``.

    Returns:
        Mapping of metric name to its CSV row.

    Raises:
        ArtifactError: If the tree's record is missing or lacks a value.
    """
    rows = load_rows(SOP_DIR / f"{tree}_mesh_quality.csv")
    record = {row["metric"]: row for row in rows if row.get("metric")}
    if "skewness_min" not in record or "n_cells" not in record:
        raise ArtifactError(f"{tree} mesh-quality record lacks expected metrics")
    return record


def parse_gate(gate: str) -> tuple[str, float] | None:
    """Split a gate string into an operator and a numeric limit.

    Args:
        gate: Gate text such as ``<0.25``, ``>=0.1`` or ``report``.

    Returns:
        The operator and limit, or None when the gate is not numeric
        (a reported-but-ungated metric).
    """
    text = gate.strip()
    for op in ("<=", ">=", "<", ">"):
        if text.startswith(op):
            try:
                return op, float(text[len(op):])
            except ValueError:
                return None
    return None


def gate_utilisation(value: float, gate: str) -> float | None:
    """Express a metric as a fraction of the gate budget it is allowed.

    A utilisation of 1.0 sits exactly on the gate; below 1.0 passes. For a
    ``<=`` gate the value is divided by the limit; for a ``>=`` gate the
    limit is divided by the value, so both directions read the same way on
    one axis.

    Args:
        value: Measured metric value.
        gate: Gate text.

    Returns:
        The utilisation, or None when the gate has no numeric limit.
    """
    parsed = parse_gate(gate)
    if parsed is None:
        return None
    op, limit = parsed
    if limit == 0.0:
        return None
    if op in ("<", "<="):
        return abs(value) / abs(limit)
    return abs(limit) / abs(value) if value != 0.0 else None


def load_stationarity(tree: str) -> list[dict[str, float | str]]:
    """Read the DSMC stationarity series for one result tree.

    Args:
        tree: Result-tree name.

    Returns:
        Rows with float ``step``, ``retention_frac`` and
        ``stationarity_indicator`` plus the residual-kind label.

    Raises:
        ArtifactError: If the series is missing or lacks a needed column.
    """
    rows = load_rows(SOP_DIR / f"{tree}_residuals.csv")
    series: list[dict[str, float | str]] = []
    for row in rows:
        try:
            series.append(
                {
                    "step": float(row["step"]),
                    "retention_frac": float(row["retention_frac"]),
                    "stationarity_indicator": float(row["stationarity_indicator"]),
                    "kind": row.get("residual_kind", ""),
                }
            )
        except (KeyError, ValueError) as exc:
            raise ArtifactError(
                f"{tree} stationarity series lacks a usable column: {exc}"
            ) from exc
    return series


def fmt(value: float, digits: int = 3) -> str:
    """Format a measurement for a figure annotation.

    Args:
        value: Number to format.
        digits: Decimal places for the long form.

    Returns:
        A compact decimal string, scientific below 1e-4 or above 1e5.
    """
    if value != 0.0 and abs(value) < 1.0e-4:
        return f"{value:.3e}"
    return f"{value:,.{digits}f}"


def draw_grid_independence(
    levels: list[dict[str, object]], program: object, out_path: Path
) -> None:
    """Draw the three-level mesh-independence figure.

    Args:
        levels: Level records in ascending cell order.
        program: The imported program module supplying the tolerance and the
            convergence analysis.
        out_path: PNG to write.

    Raises:
        ArtifactError: If the program returns no convergence analysis.
    """
    cells = [float(rec["n_cells"]) for rec in levels]
    qoi = [float(rec["qoi_value"]) for rec in levels]
    convergence = program._convergence_analysis(list(levels))
    if not convergence:
        raise ArtifactError("program returned no convergence analysis")
    tolerance = float(program.TOLERANCE_PCT)
    deltas = [abs(qoi[i] - qoi[i - 1]) / abs(qoi[i - 1]) * 100.0 for i in range(1, 3)]
    finest_change = deltas[-1]
    verdict = "MET" if finest_change < tolerance else "NOT_MET"
    legacy = "MET" if finest_change < 5.0 else "NOT_MET"

    figure, (ax_qoi, ax_gate) = plt.subplots(
        1, 2, figsize=(11.6, 4.9), dpi=200, gridspec_kw={"width_ratios": [1.15, 1.0]}
    )

    medium = qoi[1]
    ax_qoi.axhspan(medium * (1.0 - tolerance / 100.0), medium * (1.0 + tolerance / 100.0),
                   color="#dbeafe", alpha=0.75, zorder=0,
                   label=f"$\\pm${tolerance:g}% band about the medium level")
    ax_qoi.plot(cells, qoi, "-o", color="#1d4ed8", lw=1.8, ms=7, zorder=3,
                label="peak surface kinetic-energy flux")
    for index, (x, y) in enumerate(zip(cells, qoi, strict=True)):
        last = index == len(cells) - 1
        ax_qoi.annotate(f"{fmt(y, 0)}", (x, y), textcoords="offset points",
                        # The final marker sits on the right spine of the log
                        # axis, so its label is anchored to the left of it.
                        xytext=(-7, -18) if last else (6, -14),
                        ha="right" if last else "left",
                        fontsize=8.5, color="#1d4ed8")
    ax_qoi.annotate(
        "",
        xy=(cells[2], qoi[2]), xytext=(cells[2], medium),
        arrowprops={"arrowstyle": "<->", "color": "#b91c1c", "lw": 1.4},
    )
    ax_qoi.annotate(
        f"finest pair {finest_change:.3f}%\n({fmt(qoi[2] - medium, 0)} W/m$^2$)",
        xy=(cells[2] * 0.86, (qoi[2] + medium) / 2.0), fontsize=8.5, color="#b91c1c",
        ha="right", va="center",
    )
    ax_qoi.set_xscale("log")
    ax_qoi.set_xlabel("Cartesian cell count [-] (log scale)")
    ax_qoi.set_ylabel("QoI: peak surface flux [W/m$^2$]")
    ax_qoi.set_title("Three-level refinement of the SPARTA QoI", fontsize=11, weight="bold")
    ax_qoi.grid(alpha=0.3, which="both")
    ax_qoi.legend(loc="lower left", fontsize=8.5, framealpha=0.95)
    ax_qoi.margins(x=0.16)

    labels = ["coarse $\\rightarrow$ medium", "medium $\\rightarrow$ fine"]
    bars = ax_gate.bar(labels, deltas, color=["#f59e0b", "#b91c1c"], width=0.55, zorder=3)
    for bar, delta in zip(bars, deltas, strict=True):
        ax_gate.annotate(f"{delta:.3f}%", (bar.get_x() + bar.get_width() / 2.0, delta),
                         textcoords="offset points", xytext=(0, 5),
                         ha="center", fontsize=9, weight="bold")
    ax_gate.axhline(tolerance, color="#166534", ls="--", lw=1.6, zorder=4)
    # x is in AXES FRACTION and y in data units, because the bar axis autoscales
    # tightly (observed xlim -0.353..1.352) and a data-space x of 1.42 lands
    # outside the axes and silently disappears.
    ax_gate.annotate(f"tolerance {tolerance:g}% (owner-set 2026-10-16)",
                     xy=(0.99, tolerance), xycoords=ax_gate.get_yaxis_transform(),
                     xytext=(0, 6), textcoords="offset points",
                     ha="right", color="#166534", fontsize=8.5)
    ax_gate.axhline(5.0, color="#64748b", ls=":", lw=1.3, zorder=4)
    # Short marker only: the full history of the tolerance lives in the text
    # block below, because a sentence here would collide with a filled bar.
    ax_gate.annotate("5%", xy=(0.99, 5.0), xycoords=ax_gate.get_yaxis_transform(),
                     xytext=(0, -11), textcoords="offset points",
                     ha="right", color="#475569", fontsize=8.5, weight="bold")
    ax_gate.set_ylim(0, max(*deltas, tolerance) * 1.45)
    ax_gate.set_ylabel("relative change of the QoI [%]")
    ax_gate.set_title(f"Gate on the finest pair: {verdict}", fontsize=11, weight="bold")
    ax_gate.grid(alpha=0.3, axis="y")

    order = convergence.get("observed_order_p")
    richardson = convergence.get("richardson_extrapolated_qoi")
    extrap_error = convergence.get("estimated_extrapolated_error_pct")
    gci = convergence.get("gci_fine_pct")
    particles = [float(levels[index]["secondary"]["n_particles"]) / 1.0e6
                 for index in range(3)]
    lines = [
        (f"tolerance {tolerance:g}% owner-set 2026-10-16; the recorded sweep applied "
         f"a 5% rule ({legacy})"),
        f"observed order p = {order:.4f}" if order is not None else "observed order undefined",
        f"Richardson value = {fmt(float(richardson), 0)} W/m$^2$" if richardson else "",
        f"estimated extrapolated error = {float(extrap_error):.2f}%" if extrap_error else "",
        f"GCI (fine, Fs=1.3) = {float(gci):.2f}%  [estimate]" if gci else "",
        "refinement ratios unequal (r21=1.4286, r32=1.3900):",
        "the change mixes discretisation with sampling",
        "(particles " + " / ".join(f"{value:.2f}" for value in particles) + " M)",
    ]
    figure.text(0.012, 0.015, "\n".join(line for line in lines if line), fontsize=8,
                va="bottom", ha="left", color="#111827")
    figure.subplots_adjust(left=0.065, right=0.985, top=0.90, bottom=0.30, wspace=0.24)
    figure.savefig(out_path, dpi=200)
    plt.close(figure)


def draw_mesh_quality(
    quality: dict[str, dict[str, dict[str, str]]], out_path: Path
) -> None:
    """Draw the mesh-quality gate record and the cut-cell census.

    Args:
        quality: Mapping of tree name to its metric rows.
        out_path: PNG to write.
    """
    figure, (ax_gate, ax_cells) = plt.subplots(1, 2, figsize=(11.6, 4.6), dpi=200)

    metrics = [
        ("skewness_min", "skewness, minimum"),
        ("skewness_mean", "skewness, mean"),
        ("ortho_min", "orthogonal quality, minimum"),
        ("ortho_mean", "orthogonal quality, mean"),
        ("growth_rate", "growth rate"),
        ("flow_volume_closure_rel_err", "flow-volume closure, relative error"),
    ]
    ypos = list(range(len(metrics)))[::-1]
    height = 0.34
    for index, tree in enumerate(TREES):
        record = quality[tree]
        offset = (1 - index) * height
        for slot, (metric, _label) in enumerate(metrics):
            row = record.get(metric)
            if row is None:
                continue
            value = float(row["value"])
            utilisation = gate_utilisation(value, row["gate"])
            y = ypos[slot] + offset
            if utilisation is None:
                continue
            # A metric that is exactly zero plots as a stub and is annotated,
            # so a zero is never drawn as an invented small number.
            ax_gate.barh(y, max(utilisation, 0.0), height=height * 0.92,
                         color=["#1d4ed8", "#0891b2"][index], zorder=3)
            text = "= 0 exactly" if value == 0.0 else f"{value:.6g}"
            ax_gate.annotate(text, (utilisation, y), xytext=(5, 0),
                             textcoords="offset points", va="center", fontsize=7.8)
    ax_gate.axvline(1.0, color="#b91c1c", ls="--", lw=1.5, zorder=4)
    ax_gate.annotate("gate limit", (1.0, len(metrics) - 0.42), xytext=(4, 0),
                     textcoords="offset points", color="#b91c1c", fontsize=8.5)
    ax_gate.set_yticks(ypos)
    ax_gate.set_yticklabels([label for _, label in metrics], fontsize=8.8)
    ax_gate.set_xlim(0.0, 1.55)
    ax_gate.set_xlabel("gate utilisation: value / limit for a $\\leq$ gate,\n"
                       "limit / value for a $\\geq$ gate  (1.0 = the gate)")
    ax_gate.set_title("Mesh gates, both result trees", fontsize=11, weight="bold")
    ax_gate.grid(alpha=0.3, axis="x")
    handles = [plt.Rectangle((0, 0), 1, 1, color=colour)
               for colour in ("#1d4ed8", "#0891b2")]
    ax_gate.legend(handles, list(TREES), loc="lower right", fontsize=8.5)

    outside, inside, overlapping = [], [], []
    for tree in TREES:
        record = quality[tree]
        outside.append(float(record["cells_outside_surf"]["value"]))
        inside.append(float(record["cells_inside_surf"]["value"]))
        overlapping.append(float(record["cells_overlapping_surf"]["value"]))
    split = [float(quality[tree]["surf_cells_split"]["value"]) for tree in TREES]
    ax_cells.barh(list(TREES), outside, color="#1d4ed8", label="cells outside the surface")
    ax_cells.barh(list(TREES), inside, left=outside, color="#0891b2",
                  label="cut cells inside")
    ax_cells.barh(list(TREES), overlapping,
                  left=[a + b for a, b in zip(outside, inside, strict=True)],
                  color="#f59e0b", label="cut cells overlapping")
    for slot, _ in enumerate(TREES):
        total = outside[slot] + inside[slot] + overlapping[slot]
        # Written inside the wide blue field, right-aligned at its end: placed
        # outside the bar the label ran past the axis spine and vanished.
        ax_cells.annotate(f"census sum {total:,.0f} cells, {split[slot]:,.0f} split",
                          (outside[slot] - 600.0, slot), ha="right", va="center",
                          color="white", fontsize=9)
    ax_cells.set_xlim(0.0, max(outside) * 1.06)
    ax_cells.set_xlabel("Cartesian cells [-]")
    ax_cells.set_title("Cut-cell census from the solver log", fontsize=11, weight="bold")
    ax_cells.grid(alpha=0.3, axis="x")
    ax_cells.legend(loc="lower right", fontsize=8.5)

    closures = [float(quality[tree]["flow_volume_closure_rel_err"]["value"])
                for tree in TREES]
    figure.text(0.012, 0.015,
                f"Flow-volume closure |cell-wise - global| / global = {closures[0]:.3e} "
                f"(00_reference) and {closures[1]:.3e} (03_opt_geometry) against a 1e-6 "
                f"gate. Skewness and orthogonal quality are exact by construction on an "
                f"axis-aligned Cartesian grid, so they carry no discriminating "
                f"information; the cut-cell census is the mesh record that does.",
                fontsize=8, va="bottom", ha="left", color="#111827")
    figure.subplots_adjust(left=0.215, right=0.985, top=0.90, bottom=0.26, wspace=0.42)
    figure.savefig(out_path, dpi=200)
    plt.close(figure)


def draw_stationarity(series: dict[str, list[dict[str, float | str]]],
                      out_path: Path) -> None:
    """Draw the DSMC sampling-stationarity record.

    Args:
        series: Mapping of tree name to its stationarity rows.
        out_path: PNG to write.
    """
    figure, (ax_ret, ax_ind) = plt.subplots(1, 2, figsize=(11.6, 4.4), dpi=200)
    colours = {"00_reference": "#1d4ed8", "03_opt_geometry": "#0891b2"}

    for tree, rows in series.items():
        steps = [float(row["step"]) for row in rows]
        retention = [float(row["retention_frac"]) for row in rows]
        indicator = [float(row["stationarity_indicator"]) for row in rows]
        ax_ret.plot(steps, retention, "-o", ms=4, lw=1.6, color=colours[tree], label=tree)
        ax_ind.plot(steps, indicator, "-o", ms=4, lw=1.6, color=colours[tree], label=tree)
        # The two runs finish at nearly the same value, so their end labels are
        # split above and below the curve instead of stacking on one another.
        vertical = 4 if tree == "00_reference" else -16
        ax_ret.annotate(f"{retention[-1]:.4f}", (steps[-1], retention[-1]),
                        xytext=(-46, vertical), textcoords="offset points", fontsize=8.5,
                        color=colours[tree])
        ax_ind.annotate(f"{indicator[-1] * 100.0:.2f}%", (steps[-1], indicator[-1]),
                        xytext=(-48, vertical), textcoords="offset points", fontsize=8.5,
                        color=colours[tree])

    ax_ret.axhline(1.0, color="#64748b", ls=":", lw=1.2)
    ax_ret.set_xlabel("particle-time step [-]")
    ax_ret.set_ylabel("particle retention fraction [-]")
    ax_ret.set_title("Particle census over the run", fontsize=11, weight="bold")
    ax_ret.grid(alpha=0.3)
    ax_ret.legend(loc="lower left", fontsize=8.5)

    ax_ind.axhline(0.02, color="#b91c1c", ls="--", lw=1.5)
    ax_ind.annotate("2% relative-change window criterion (methodology),\n"
                    "shown for scale: it is defined for the drag coefficient\n"
                    "and the stagnation heat flux, not for a particle census",
                    xy=(0.02, 0.0208), xycoords=ax_ind.get_yaxis_transform(),
                    ha="left", va="bottom", color="#b91c1c", fontsize=8)
    ax_ind.set_xlabel("particle-time step [-]")
    ax_ind.set_ylabel("stationarity indicator [-]")
    ax_ind.set_ylim(0.0, 0.03)
    ax_ind.set_title("Sampling stationarity, not a continuum residual",
                     fontsize=11, weight="bold")
    ax_ind.grid(alpha=0.3)

    figure.subplots_adjust(left=0.075, right=0.985, top=0.90, bottom=0.13, wspace=0.24)
    figure.savefig(out_path, dpi=200)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    """Render the three SOP verification-evidence figures.

    Args:
        argv: Argument list; defaults to ``sys.argv``. Only ``--outdir`` is
            accepted, to redirect the PNGs.

    Returns:
        0 when all three figures were written, 1 when an artefact is missing.

    Raises:
        SystemExit: Never raised directly; a missing artefact is reported and
            a non-zero status is returned.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=FIG_DIR,
                       help="directory for the PNG output")
    args = parser.parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)

    try:
        find_program_root()
        program = load_program()
        levels = load_levels()
        quality = {tree: load_mesh_quality(tree) for tree in TREES}
        series = {tree: load_stationarity(tree) for tree in TREES}
    except ArtifactError as exc:
        print(f"[sop-figures] ERROR: {exc}", file=sys.stderr)
        return 1

    jobs = (
        ("sop_grid_independence.png",
         lambda path: draw_grid_independence(levels, program, path)),
        ("sop_mesh_quality_record.png",
         lambda path: draw_mesh_quality(quality, path)),
        ("sop_dsmc_stationarity.png",
         lambda path: draw_stationarity(series, path)),
    )
    for name, job in jobs:
        path = args.outdir / name
        try:
            job(path)
        except (ArtifactError, KeyError, ValueError, OSError) as exc:
            print(f"[sop-figures] ERROR drawing {name}: {exc}", file=sys.stderr)
            return 1
        print(f"[sop-figures] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
