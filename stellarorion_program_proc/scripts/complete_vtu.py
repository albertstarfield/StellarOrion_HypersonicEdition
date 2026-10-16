#!/usr/bin/env python3
# ===========================================================================
# SCRIPT: complete_vtu.py
# ===========================================================================
#
# AXIOMS:
#   A1  `HIAD_custom.surf` is the geometry the CFD actually flew.  Any
#       field attached to a `surf_*.vtu` is attached to THAT body.  This
#       script never invents geometry: it only re-writes the arrays of an
#       existing, readable VTU.
#   A2  A VTK UnstructuredGrid with cell data only renders as FLAT BLOCKS.
#       Smooth colouring requires `<PointData>`; without it ParaView
#       reports a mosaic, which readers correctly read as "weird
#       representation".
#   A3  The per-step scalars that describe the flow state (mach, altitude,
#       velocity, ...) are UNIFORM over the body at a given step, because
#       they are freestream/state quantities, not surface fields.  They
#       therefore carry one value replicated to every point and cell.
#   A4  A surface field f attached to a cell belongs to the cell's ring.
#       Every point lies on a shared edge of exactly two cells (or one,
#       on the boundary), so the node value is the MEAN of the incident
#       cell values.  For an axisymmetric ring-constant field this
#       reproduces the exact ring-to-node interpolation.
#   A5  `validation_timeseries.csv` is the authority for per-step state.
#       If its row for `step` is absent, the script FAILS LOUDLY rather
#       than writing zeros that would be indistinguishable from real
#       measurements.
#   A6  Every rewritten file must remain readable by the REAL VTK reader
#       (`audit_vtu.py`), not merely by this script's own parser.
#   A7  `<FieldData>` is collected by VTK only as a child of
#       `<UnstructuredGrid>`.  Nesting it inside `<Piece>` yields a file
#       that PARSES but reports zero field arrays -- measured, not assumed.
#   A8  The step number lives in the filename and both
#       `surf_<step>.vtu` and `surf_pinn_<step>.vtu` are legitimate export
#       families; one pattern must serve both so sorting, provenance and
#       reporting cannot disagree.
#   A9  This script never DESTROYS data it did not create: every cell array
#       it does not explicitly rewrite is preserved byte-for-byte, and a
#       name that already carries varying (spatial) values is never
#       overwritten by a uniform per-step scalar.
#
# THEORIES:
#   T1  cell->point averaging is area-agnostic: with A4 the node value is
#       (1/|C(p)|) * sum_{c in C(p)} f(c), which is linear, bounded by
#       the cell values (no overshoot), and symmetric under cell order.
#   T2  Adding arrays never changes Points/connectivity/offsets/types, so
#       the geometry and the cell->point index map are preserved exactly.
#   T3  Provenance in <FieldData> is the only place a reader can learn
#       which run produced the file; putting it there makes the file
#       self-describing even when it is copied out of the tree.
#
# APPLICATIONS:
#   parse VTU -> average cell arrays to nodes -> join timeseries row
#   -> emit PointData + enriched CellData + FieldData -> validate -> atomic
#      rename.
#
# CITATIONS:
#   [1] VTK File Format, UnstructuredGrid/PointData/CellData/FieldData
#       https://docs.vtk.org/en/latest/design/Documents/VTKFileFormats.html
#   [2] VTK "Cell Data to Point Data" filter, cell-to-node averaging
#       https://docs.vtk.org/en/latest/sources/Filtering/CellDataToPointData.html
#   [3] results/<tree>/validation_timeseries.csv — 22 per-step columns
#   [4] scripts/audit_vtu.py — independent real-VTK verification gate
#
# AUTHOR: Albert Starfield Wahyu Suryo Samudro
#
# EXIT: 0 all files completed & verified; 1 at least one failure;
#       2 usage error.  A partial failure is NEVER reported as success.
#
# ===========================================================================

"""Upgrade `surf_*.vtu` files to the complete array spec (PointData +
enriched CellData + FieldData provenance) using the run's own per-step
timeseries.  See the header block for axioms/theories/applications."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import re
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------
# Canonical array sets.  Names match the `irve*` point-array convention that
# already exists elsewhere in this repository (no new vocabulary invented).
# --------------------------------------------------------------------------

#: Flow/state scalars, uniform over the body, exposed as PointData so they
#: appear in ParaView's "Colour By" menu.
POINT_UNIFORM: tuple[tuple[str, str, str], ...] = (
    ("altitude_km", "alt_km", "float"),
    ("velocity_ms", "vel_ms", "float"),
    ("mach_number", "mach", "float"),
    ("dynamic_pressure_Pa", "dyn_press_pa", "float"),
    ("pressure_Pa", "ambient_pressure_pa", "float"),
    ("temperature_K", "ambient_temp_k", "float"),
    ("g_load", "g_load", "float"),
)

#: Cell-level per-step quantities added alongside the three spatial fields.
CELL_UNIFORM: tuple[tuple[str, str, str], ...] = (
    ("HeatLoad_Jcm2", "heat_load_jcm2", "float"),
    ("HeatFlux_Max_Wm2", "heatflux_max_Wm2", "float"),
    ("heat_flux_avg_Wm2", "heatflux_avg_Wm2", "float"),
    ("heat_flux_sg_Wm2", "heatflux_sg_Wm2", "float"),
    ("drag_sum_N", "drag_sum_N", "float"),
    ("lift_sum_N", "lift_sum_N", "float"),
    ("drag_coefficient", "cd", "float"),
    ("lift_coefficient", "cl", "float"),
)

#: Cell fields that are spatially varying and therefore get a node image.
CELL_TO_POINT: tuple[str, ...] = ("HeatFlux_Wm2", "Drag_N", "Lift_N")

#: Ideal-gas constant for dry air, J/(kg*K).  Source: SI brochure, not typed
#: from memory without a citation -- [NIST SP 811, R_specific dry air].
R_SPECIFIC_AIR = 287.058

_FLOAT_FMT = "%.9g"

#: Step-number extraction shared by both export families (`surf_1200.vtu`
#: and `surf_pinn_1200.vtu`) -- one pattern used for sorting, provenance
#: and reporting so the three can never disagree.
_STEP_RE = re.compile(r"surf_(?:pinn_)?(\d+)\.vtu$")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


class VtuError(RuntimeError):
    """Raised when a VTU cannot be parsed or violates an assumption above.

    The message always carries the path and the offending construct so the
    failure is reproducible from the log alone.
    """


def _read_array(lines: list[str], start: int, expected: int) -> tuple[list[float], int]:
    """Read one ASCII DataArray body.

    Parameters
    ----------
    lines : the full VTU as a list of lines
    start : index of the line holding the opening `<DataArray ...>` tag
    expected : exact number of numeric tokens required

    Returns
    -------
    (values, index_of_closing_line)

    Raises
    ------
    VtuError
        If the array is short, long, or contains a non-numeric token.
    """
    values: list[float] = []
    i = start + 1
    closed = False
    while i < len(lines):
        if "</DataArray>" in lines[i]:
            closed = True
            break
        for tok in lines[i].split():
            try:
                values.append(float(tok))
            except ValueError as exc:  # pragma: no cover - defensive
                raise VtuError(
                    f"non-numeric token {tok!r} at line {i + 1} of array body"
                ) from exc
        i += 1
    if not closed:
        raise VtuError(f"unterminated DataArray starting at line {start + 1}")
    if len(values) != expected:
        raise VtuError(
            f"DataArray at line {start + 1} holds {len(values)} values, "
            f"expected {expected}"
        )
    return values, i


def parse_vtu(text: str) -> dict:
    """Parse an ASCII UnstructuredGrid VTU into its numeric parts.

    Parameters
    ----------
    text : raw file contents

    Returns
    -------
    dict with keys ``n_points``, ``n_cells``, ``points`` (3*n floats),
    ``connectivity``, ``offsets``, ``types``, ``cell_arrays`` (ordered
    dict name -> list[float]).

    Raises
    ------
    VtuError
        On any structural deviation (missing block, wrong counts).
    """
    lines = text.splitlines()
    hdr = next((l for l in lines if "<Piece " in l), None)
    if hdr is None:
        raise VtuError("no <Piece> element: not an UnstructuredGrid")
    m_p = re.search(r'NumberOfPoints="(\d+)"', hdr)
    m_c = re.search(r'NumberOfCells="(\d+)"', hdr)
    if not m_p or not m_c:
        raise VtuError(f"<Piece> lacks NumberOfPoints/NumberOfCells: {hdr!r}")
    n_points, n_cells = int(m_p.group(1)), int(m_c.group(1))

    def find_block(tag: str) -> int:
        for idx, line in enumerate(lines):
            if tag in line:
                return idx
        raise VtuError(f"missing {tag} block")

    out: dict = {
        "n_points": n_points,
        "n_cells": n_cells,
        "cell_arrays": {},
    }

    i = find_block("<Points>")
    i += 1  # DataArray opening line
    if "<DataArray" not in lines[i]:
        raise VtuError("<Points> is not backed by a DataArray")
    pts, _ = _read_array(lines, i, n_points * 3)
    out["points"] = pts

    i = find_block("<Cells>")
    found: dict[str, list[float]] = {}
    j = i + 1
    while j < len(lines) and "</Cells>" not in lines[j]:
        if "<DataArray" in lines[j]:
            m = re.search(r'Name="([^"]+)"', lines[j])
            if m:
                arr, end = _read_array_lenient(lines, j)
                found[m.group(1)] = arr
                j = end
        j += 1
    for required in ("connectivity", "offsets", "types"):
        if required not in found:
            raise VtuError(f"<Cells> lacks {required!r}")
    out["connectivity"] = found["connectivity"]
    out["offsets"] = found["offsets"]
    out["types"] = found["types"]

    cd = find_block("<CellData>")
    j = cd + 1
    while j < len(lines) and "</CellData>" not in lines[j]:
        if "<DataArray" in lines[j]:
            m = re.search(r'Name="([^"]+)"', lines[j])
            if m:
                arr, end = _read_array_lenient(lines, j)
                out["cell_arrays"][m.group(1)] = arr
                j = end
        j += 1

    # Structural validation (T2): every cell must reference in-range points.
    conn = out["connectivity"]
    if len(conn) != n_cells * 4:
        raise VtuError(
            f"connectivity has {len(conn)} entries, expected {n_cells * 4} "
            "(this family is quad-only)"
        )
    for idx, p in enumerate(conn):
        if not 0 <= int(p) < n_points:
            raise VtuError(
                f"connectivity[{idx}] = {p} outside [0, {n_points}) -- "
                "file is defective, refusing to complete it"
            )
    for name, arr in out["cell_arrays"].items():
        if len(arr) != n_cells:
            raise VtuError(
                f"cell array {name!r} has {len(arr)} values, expected {n_cells}"
            )
    return out


def _read_array_lenient(lines: list[str], start: int) -> tuple[list[float], int]:
    """Read a DataArray whose expected length is not yet known.

    Parameters
    ----------
    lines, start : as for :func:`_read_array`

    Returns
    -------
    (values, index_of_closing_line)

    Raises
    ------
    VtuError if the array is unterminated or has a non-numeric token.
    """
    values: list[float] = []
    i = start + 1
    closed = False
    while i < len(lines):
        if "</DataArray>" in lines[i]:
            closed = True
            break
        for tok in lines[i].split():
            try:
                values.append(float(tok))
            except ValueError as exc:
                raise VtuError(
                    f"non-numeric token {tok!r} at line {i + 1}"
                ) from exc
        i += 1
    if not closed:
        raise VtuError(f"unterminated DataArray at line {start + 1}")
    return values, i


def _select_cell_arrays(celldata_inner: str, keep: tuple[str, ...]) -> str:
    """Extract only the named DataArray blocks from a `<CellData>` body.

    Parameters
    ----------
    celldata_inner : everything between `<CellData>` and `</CellData>`
    keep : DataArray names to retain, in ``keep`` order

    Returns
    -------
    the retained blocks, each terminated by a newline, in ``keep`` order.
    Byte-identical to the source for each retained array.

    Raises
    ------
    VtuError
        If a name in ``keep`` is not present -- that would silently drop a
        spatial field, which A2 forbids.
    """
    blocks: dict[str, str] = {}
    for m in re.finditer(
        r'( *)<DataArray\b[^>]*Name="([^"]+)"[^>]*>.*?</DataArray>\n',
        celldata_inner,
        flags=re.DOTALL,
    ):
        blocks[m.group(2)] = m.group(0)
    missing = [n for n in keep if n not in blocks]
    if missing:
        raise VtuError(
            f"source <CellData> lacks required spatial array(s) {missing}; "
            f"present={sorted(blocks)}"
        )
    return "".join(blocks[n] for n in keep)


# --------------------------------------------------------------------------
# Cell -> point averaging (A4 / T1)
# --------------------------------------------------------------------------


def cell_to_point(
    cell_values: list[float], connectivity: list[int], n_points: int
) -> list[float]:
    """Average each cell field onto its incident nodes.

    Parameters
    ----------
    cell_values : one value per cell, length == n_cells
    connectivity : flat quad connectivity, 4 entries per cell
    n_points : node count

    Returns
    -------
    list[float] of length ``n_points``.

    Raises
    ------
    VtuError
        If a node receives no incident cell (would require inventing a
        value, which A1 forbids).
    """
    acc = [0.0] * n_points
    cnt = [0] * n_points
    for c in range(len(cell_values)):
        v = float(cell_values[c])
        base = c * 4
        for k in range(4):
            p = int(connectivity[base + k])
            acc[p] += v
            cnt[p] += 1
    orphan = [i for i, n in enumerate(cnt) if n == 0]
    if orphan:
        raise VtuError(
            f"{len(orphan)} node(s) touch no cell (first: {orphan[:5]}) -- "
            "cannot average without inventing data"
        )
    return [acc[i] / cnt[i] for i in range(n_points)]


def _is_spatial(values: list[float]) -> bool:
    """True when a cell array actually varies across cells.

    Parameters
    ----------
    values : one value per cell

    Returns
    -------
    True if at least two cells disagree (i.e. it is a spatial field, not a
    per-step scalar).  A length-0 or length-1 array returns False: there is
    nothing to distinguish it from a constant.

    Why this matters
    ----------------
    Flattening a spatial field into a single scalar would destroy the very
    quantity a reader opened the file to look at, so this predicate gates
    whether the script may take ownership of a name (A9).
    """
    if len(values) < 2:
        return False
    first = values[0]
    return any(v != first for v in values[1:])


# --------------------------------------------------------------------------
# Timeseries join (A5)
# --------------------------------------------------------------------------


def load_timeseries(csv_path: Path) -> dict[int, dict[str, float]]:
    """Load `validation_timeseries.csv` keyed by integer step.

    Parameters
    ----------
    csv_path : path to the timeseries CSV

    Returns
    -------
    dict mapping step -> {column -> float}

    Raises
    ------
    VtuError
        If the file is missing, empty, or has no `step` column.
    """
    if not csv_path.is_file():
        raise VtuError(f"timeseries CSV not found: {csv_path}")
    rows: dict[int, dict[str, float]] = {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "step" not in reader.fieldnames:
            raise VtuError(
                f"{csv_path} has no 'step' column; columns={reader.fieldnames}"
            )
        for lineno, row in enumerate(reader, start=2):
            try:
                step = int(float(row["step"]))
            except (TypeError, ValueError) as exc:
                raise VtuError(
                    f"{csv_path}:{lineno} has a non-numeric step {row['step']!r}"
                ) from exc
            vals: dict[str, float] = {}
            for key, raw in row.items():
                if key is None or raw is None or raw == "":
                    continue
                try:
                    vals[key] = float(raw)
                except ValueError:
                    continue
            rows[step] = vals
    if not rows:
        raise VtuError(f"{csv_path} yielded no rows")
    return rows


def density_from_ideal_gas(pressure_pa: float, temp_k: float) -> float:
    """Dry-air density from pressure and temperature via the ideal-gas law.

    Parameters
    ----------
    pressure_pa : static pressure, Pa
    temp_k : absolute temperature, K

    Returns
    -------
    density in kg/m^3

    Raises
    ------
    ValueError
        If either input is non-physical (would silently publish a
        meaningless number).

    Citations
    ---------
    [NIST SP 811] rho = P / (R * T), R_specific(dry air) = 287.058 J/(kg K)
    """
    if not math.isfinite(pressure_pa) or not math.isfinite(temp_k):
        raise ValueError(f"non-finite P/T: {pressure_pa!r}, {temp_k!r}")
    if temp_k <= 0.0:
        raise ValueError(f"temperature must be > 0 K, got {temp_k!r}")
    if pressure_pa < 0.0:
        raise ValueError(f"pressure must be >= 0 Pa, got {pressure_pa!r}")
    return pressure_pa / (R_SPECIFIC_AIR * temp_k)


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------


def _fmt(values: list[float]) -> str:
    """Render a value list as ASCII rows of 6 numbers (readable + compact)."""
    parts = [_FLOAT_FMT % v for v in values]
    return "\n".join(" ".join(parts[i : i + 6]) for i in range(0, len(parts), 6))


def _point_array(name: str, values: list[float]) -> str:
    """Emit one `<DataArray>` inside `<PointData>`."""
    return (
        f'        <DataArray type="Float64" Name="{name}" format="ascii">\n'
        f"{_fmt(values)}\n"
        "        </DataArray>"
    )


def _cell_array(name: str, values: list[float]) -> str:
    """Emit one `<DataArray>` inside `<CellData>`."""
    return (
        f'        <DataArray type="Float64" Name="{name}" format="ascii">\n'
        f"{_fmt(values)}\n"
        "        </DataArray>"
    )


def _field_array(name: str, values: list[float]) -> str:
    """Emit one single-tuple `<DataArray>` inside `<FieldData>`."""
    return (
        f'        <DataArray type="Float64" Name="{name}" '
        'NumberOfTuples="1" format="ascii">\n'
        f"{_fmt(values)}\n"
        "        </DataArray>"
    )


def complete_file(
    vtu_path: Path,
    timeseries: dict[int, dict[str, float]],
    tree: str,
) -> dict:
    """Upgrade one VTU in place (atomically).

    Parameters
    ----------
    vtu_path : the `surf_N.vtu` to complete
    timeseries : as returned by :func:`load_timeseries`
    tree : run-folder name, recorded in FieldData provenance

    Returns
    -------
    dict report: ``step``, ``point_arrays_added``, ``cell_arrays_added``,
    ``fields_added``, ``bytes_before/after``.

    Raises
    ------
    VtuError
        On parse failure, missing timeseries row (A5), or any structural
        violation.  The original file is left untouched in that case.
    """
    raw = vtu_path.read_text(encoding="utf-8")
    m = _STEP_RE.search(vtu_path.name)
    if not m:
        raise VtuError(
            f"filename {vtu_path.name!r} does not encode a step "
            "(expected surf_<step>.vtu or surf_pinn_<step>.vtu)"
        )
    step = int(m.group(1))
    # `surf_pinn_*` is a SUMMARY export (its own `step` cell array carries
    # the sentinel 300000000), not a per-step dump.  It therefore has no
    # row in the timeseries.  We still add PointData and FieldData -- that
    # alone closes the "flat blocks, no provenance" gap -- but we never
    # fabricate per-step state for it (A5).
    is_summary = vtu_path.name.startswith("surf_pinn_")
    if is_summary:
        state: dict[str, float] | None = None
        print(
            f"[complete] note: {vtu_path.name} is a PINN summary export "
            f"(sentinel step {step}) -- completing geometry-derived arrays "
            f"only; no per-step state invented (A5).",
            file=sys.stderr,
        )
    elif step not in timeseries:
        raise VtuError(
            f"step {step} absent from timeseries (have "
            f"{sorted(timeseries)[:5]}...{sorted(timeseries)[-5:]}) -- "
            "refusing to fabricate state values (A5)"
        )
    else:
        state = timeseries[step]

    data = parse_vtu(raw)
    n_pts, n_cells = data["n_points"], data["n_cells"]

    # The ORIGINAL <CellData> payload is re-emitted byte-for-byte (T2);
    # only genuinely new arrays are rendered by this script, so no existing
    # number can be re-rounded by a float format.
    existing_cell = dict(data["cell_arrays"])
    point_arrays: dict[str, list[float]] = {}
    added_cell_arrays: dict[str, list[float]] = {}

    # --- spatial cell fields -> node images (A4/T1) --------------------
    for name in CELL_TO_POINT:
        if name in existing_cell:
            point_arrays[name] = cell_to_point(
                existing_cell[name], data["connectivity"], n_pts
            )

    # --- uniform flow scalars (A3); skipped for summary exports ---------
    rho: float | None = None
    if state is not None:
        for target, source, _kind in POINT_UNIFORM:
            if source not in state:
                raise VtuError(
                    f"timeseries row for step {step} lacks column {source!r}; "
                    f"available={sorted(state)}"
                )
            value = float(state[source])
            if not math.isfinite(value):
                raise VtuError(
                    f"timeseries column {source!r} for step {step} is "
                    f"non-finite ({value!r}) -- refusing to publish it"
                )
            point_arrays[target] = [value] * n_pts

        # ideal-gas density (derived, explicitly validated)
        rho = density_from_ideal_gas(
            state["ambient_pressure_pa"], state["ambient_temp_k"]
        )
        point_arrays["density_kgm3"] = [rho] * n_pts

    # --- cell-level per-step quantities; skipped for summary exports -----
    if state is not None:
        for target, source, _kind in CELL_UNIFORM:
            if source not in state:
                raise VtuError(
                    f"timeseries row for step {step} lacks column {source!r}; "
                    f"available={sorted(state)}"
                )
            value = float(state[source])
            if not math.isfinite(value):
                raise VtuError(
                    f"timeseries column {source!r} for step {step} is "
                    f"non-finite ({value!r})"
                )
            if target in existing_cell and _is_spatial(existing_cell[target]):
                # A spatially-varying field already lives under this name; a
                # uniform per-step scalar must never flatten it (A9).
                continue  # preserved verbatim below
            added_cell_arrays[target] = [value] * n_cells
        added_cell_arrays["step"] = [float(step)] * n_cells

    # Arrays that survive byte-for-byte from the source file.  Policy (A9):
    # everything we do NOT rewrite is preserved verbatim, so a source file
    # that already carries richer or differently-named data is never
    # degraded by this script.
    preserved_names = [n for n in existing_cell if n not in added_cell_arrays]

    # --- provenance (T3) -------------------------------------------------
    # Numeric arrays in <FieldData> carry the machine-readable state; the
    # human-readable identity (tree, surf digest, generator) goes in an XML
    # comment because VTK's ascii DataArray has no string type.  Both are
    # inside the file, so it stays self-describing wherever it is copied.
    surf_path, surf_md5_hex = _surf_identity(vtu_path, tree)
    fields: dict[str, float] = {
        "step": float(step),
        "n_points": float(n_pts),
        "n_cells": float(n_cells),
        "timeseries_rows": float(len(timeseries)),
    }
    if state is not None and rho is not None:
        fields.update(
            {
                "density_kgm3": rho,
                "ambient_pressure_Pa": float(state["ambient_pressure_pa"]),
                "ambient_temp_K": float(state["ambient_temp_k"]),
                "mach_number": float(state["mach"]),
                "altitude_km": float(state["alt_km"]),
                "velocity_ms": float(state["vel_ms"]),
                "heat_load_Jcm2": float(state["heat_load_jcm2"]),
            }
        )
    state_source = (
        f"results/{tree}/validation_timeseries.csv"
        if state is not None
        else "none (PINN summary export: step is a sentinel, no timeseries row)"
    )
    identity = (
        f"  <!-- StellarOrion surf field dataset\n"
        f"       run_tree      : {tree}\n"
        f"       step          : {step}\n"
        f"       geometry      : {surf_path}\n"
        f"       geometry_md5  : {surf_md5_hex}\n"
        f"       state_source  : {state_source}\n"
        f"       generator     : scripts/complete_vtu.py\n"
        f"       arrays        : {len(point_arrays)} PointData, "
        f"{len(preserved_names) + len(added_cell_arrays)} CellData, "
        f"{len(fields)} FieldData\n"
        f"  -->\n"
    )

    # --- rebuild the document -------------------------------------------
    piece_open_end = raw.index(">", raw.index("<Piece ")) + 1
    body_start = piece_open_end
    piece_close = raw.index("    </Piece>")
    inner = raw[body_start:piece_close]

    # Keep Points/Cells AND the original spatial CellData payload
    # byte-verbatim (T2).  Uniform per-step arrays are recomputed every run
    # from the timeseries, which makes this operation idempotent: re-running
    # never appends a duplicate of an array it added itself.
    pts_s = inner.index("      <Points>")
    cells_e = inner.index("      </Cells>") + len("      </Cells>\n")
    geometry = inner[pts_s:cells_e]
    cd_open = inner.index("      <CellData>") + len("      <CellData>\n")
    cd_close = inner.index("      </CellData>")
    original_cell_inner = _select_cell_arrays(
        inner[cd_open:cd_close], keep=tuple(preserved_names)
    )

    out_points = (
        "      <PointData>\n"
        + "\n".join(_point_array(k, point_arrays[k]) for k in sorted(point_arrays))
        + "\n      </PointData>\n"
    )
    new_cell_text = "".join(
        _cell_array(k, added_cell_arrays[k]) + "\n" for k in sorted(added_cell_arrays)
    )
    out_cells = (
        "      <CellData>\n" + original_cell_inner + new_cell_text
        + "      </CellData>\n"
    )
    out_fields = (
        "    <FieldData>\n"
        + "\n".join(_field_array(k, [fields[k]]) for k in sorted(fields))
        + "\n    </FieldData>\n"
    )

    # FieldData sits on the Piece in VTK 5+; place it first for readers
    # that only inspect the leading attribute data.
    new_inner = out_points + geometry + out_cells
    new_doc = raw[:body_start] + "\n" + new_inner + raw[piece_close:]
    # <FieldData> must be a child of <UnstructuredGrid>, NOT of <Piece>:
    # VTK's XML reader only collects field data at the dataset level, so a
    # copy nested inside the Piece is silently dropped (measured: reading a
    # Piece-nested version back yields 0 field arrays).
    grid_open = "  <UnstructuredGrid>\n"
    if grid_open not in new_doc:
        raise VtuError(
            "cannot locate '  <UnstructuredGrid>' to place FieldData -- "
            "unexpected document layout"
        )
    # Drop any identity comment and FieldData from a previous run
    # (idempotency) before writing the current ones, otherwise re-runs
    # accumulate duplicates.
    new_doc = re.sub(
        r"  <!-- StellarOrion surf field dataset.*?-->\n", "", new_doc, flags=re.DOTALL
    )
    new_doc = re.sub(r"    <FieldData>.*?</FieldData>\n", "", new_doc, flags=re.DOTALL)
    new_doc = new_doc.replace(grid_open, grid_open + out_fields, 1)
    new_doc = new_doc.replace("    <Piece ", identity + "    <Piece ", 1)

    # ---- verify by re-parsing BEFORE touching disk (A6 precursor) ------
    reparsed = parse_vtu(new_doc)
    if reparsed["n_points"] != n_pts or reparsed["n_cells"] != n_cells:
        raise VtuError("re-parse changed geometry counts; refusing to write")
    if reparsed["connectivity"] != data["connectivity"]:
        raise VtuError("re-parse changed connectivity; refusing to write")
    if reparsed["points"] != data["points"]:
        raise VtuError("re-parse changed point coordinates; refusing to write")
    for name in ("HeatFlux_Wm2", "Drag_N", "Lift_N"):
        if reparsed["cell_arrays"].get(name) != data["cell_arrays"].get(name):
            raise VtuError(f"existing cell array {name!r} was altered")

    # ---- atomic replace --------------------------------------------------
    fd, tmp = tempfile.mkstemp(
        dir=str(vtu_path.parent), prefix=".complete_", suffix=".vtu"
    )
    os.close(fd)
    try:
        Path(tmp).write_text(new_doc, encoding="utf-8")
        os.replace(tmp, vtu_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    return {
        "step": step,
        "point_arrays_added": sorted(point_arrays),
        "cell_arrays_added": sorted(added_cell_arrays),
        "fields_added": sorted(fields),
        "bytes_before": len(raw),
        "bytes_after": len(new_doc),
    }


def _surf_identity(vtu_path: Path, tree: str) -> tuple[str, str]:
    """Locate and fingerprint the `HIAD_custom.surf` that defines this body.

    Parameters
    ----------
    vtu_path : the VTU being completed
    tree : run-folder name

    Returns
    -------
    (display_path, md5_hex)

    The digest identifies WHICH vehicle the surface represents, so two
    runs' VTUs cannot be confused after being copied out of the tree.
    If the surf file is unreadable the digest is the literal string
    ``unavailable`` -- never a fake all-zero hash, which would read as a
    real answer.
    """
    root = _find_results_root(vtu_path)
    surf = root / tree / "HIAD_custom.surf"
    if not surf.is_file():
        print(
            f"[complete] WARN: {surf} missing -- geometry identity unavailable "
            "in provenance (reported, not faked)",
            file=sys.stderr,
        )
        return (str(surf), "unavailable")
    return (str(surf.relative_to(root)), hashlib.md5(surf.read_bytes()).hexdigest())


def _find_results_root(vtu_path: Path) -> Path:
    """Locate the `results/` directory containing `vtu_path`.

    Parameters
    ----------
    vtu_path : path inside a results tree

    Returns
    -------
    the `results` directory

    Raises
    ------
    VtuError if no ancestor named `results` exists.
    """
    for parent in vtu_path.resolve().parents:
        if parent.name == "results":
            return parent
    raise VtuError(f"no 'results' ancestor for {vtu_path}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Parameters
    ----------
    argv : optional argument vector (defaults to sys.argv[1:])

    Returns
    -------
    0 all files completed, 1 failures, 2 usage error
    """
    ap = argparse.ArgumentParser(
        description="Complete surf_*.vtu with PointData, per-step arrays "
        "and FieldData provenance."
    )
    ap.add_argument("--tree", required=True, help="run folder name, e.g. 00_reference")
    ap.add_argument(
        "--paraview-dir", default=None, help="defaults to results/<tree>/paraview"
    )
    ap.add_argument("--limit", type=int, default=0, help="only first N files (0=all)")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    script_dir = Path(__file__).resolve()
    results_root = script_dir.parents[1] / "results"
    tree = args.tree
    tree_dir = results_root / tree
    if not tree_dir.is_dir():
        print(f"[complete] ERROR: no such tree: {tree_dir}", file=sys.stderr)
        return 2
    pv = Path(args.paraview_dir) if args.paraview_dir else tree_dir / "paraview"
    if not pv.is_dir():
        print(f"[complete] ERROR: no such paraview dir: {pv}", file=sys.stderr)
        return 2

    ts_path = tree_dir / "validation_timeseries.csv"
    try:
        timeseries = load_timeseries(ts_path)
    except VtuError as exc:
        print(f"[complete] ERROR: {exc}", file=sys.stderr)
        return 1

    def _step_of(p: Path) -> int:
        m = _STEP_RE.search(p.name)
        return int(m.group(1)) if m else -1

    files = sorted((p for p in pv.glob("surf_*.vtu") if _STEP_RE.search(p.name)),
                   key=_step_of)
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"[complete] ERROR: no surf_*.vtu under {pv}", file=sys.stderr)
        return 1

    print(
        f"[complete] tree={tree} files={len(files)} "
        f"timeseries_rows={len(timeseries)} dry_run={args.dry_run}"
    )

    failures: list[str] = []
    for path in files:
        try:
            if args.dry_run:
                # parse + validate only
                parse_vtu(path.read_text(encoding="utf-8"))
                m = _STEP_RE.search(path.name)
                step = int(m.group(1))
                if step not in timeseries and not path.name.startswith(
                    "surf_pinn_"
                ):
                    raise VtuError(f"step {step} missing from timeseries")
                print(f"[complete] OK(dry) {path.name} step={step}")
                continue
            rep = complete_file(path, timeseries, tree)
            print(
                f"[complete] {path.name} step={rep['step']} "
                f"+{len(rep['point_arrays_added'])}pt "
                f"+{len(rep['cell_arrays_added'])}cell "
                f"{rep['bytes_before']}->{rep['bytes_after']}B"
            )
        except VtuError as exc:
            failures.append(f"{path.name}: {exc}")
            print(f"[complete] FAIL {path.name}: {exc}", file=sys.stderr)
        except OSError as exc:
            failures.append(f"{path.name}: {exc}")
            print(f"[complete] FAIL {path.name}: {exc}", file=sys.stderr)

    if failures:
        print(
            f"[complete] RESULT: {len(failures)}/{len(files)} FAILED",
            file=sys.stderr,
        )
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"[complete] RESULT: {len(files)}/{len(files)} completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
