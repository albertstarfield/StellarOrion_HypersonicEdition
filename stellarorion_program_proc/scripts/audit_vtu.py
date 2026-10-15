#!/usr/bin/env python3
"""Audit every produced .vtu with the real VTK reader, and repair the
connectivity-gluing defect that made them unreadable.

WHY THIS EXISTS
    `stellarorion_sparta.adb` Write_VTU emitted each cell's four indices with
    a separator only *inside* the cell.  Between cells it wrote nothing on
    three of four iterations, so cell N's last index ran into cell N+1's first
    index ("... 49 1" + "1 49 ..." -> token "11").  VTK therefore saw a
    connectivity array shorter than 4*NumberOfCells and refused the file:

        ERR vtkXMLUnstructuredGridReader: Cannot read cell connectivity from
            Cells in piece 0 because the "connectivity" array is not long enough

    with GetErrorCode()=20008 and 0 points / 0 cells -- which is what ParaView
    showed as the "array thingy" when visibility was toggled.

AXIOMS
    A1  The ground truth for "is this file usable" is the VTK reader itself,
        never a hand-rolled parser.  `audit` reports what vtk actually returns.
    A2  A repair may only rewrite an array it can PROVE it recovered.  The
        connectivity is regenerated from Write_VTU's own index formula, then
        re-rendered in the *defective* layout and compared byte-for-byte with
        the file on disk.  Equal => the repair reproduces the author's intent
        exactly, not a plausible guess.  Unequal => refused, file untouched.
    A3  Files that already read cleanly are never modified.

THEORIES
    T1  N_Points = (N+1)*N_Theta and N_Cells = N*N_Theta, hence
        N_Theta = N_Points - N_Cells and N = N_Cells / N_Theta.  The two
        header integers determine the whole ring/theta topology.
    T2  Write_VTU's indices are N0=(k-1)*Nt+t, N1=k*Nt+t, N2=k*Nt+Tn,
        N3=(k-1)*Nt+Tn with Tn=(t+1) mod Nt -- a closed quad of revolution.

CITATIONS
    [Citation: VTK 9.7.1 vtkXMLUnstructuredGridReader — https://vtk.org/doc/]
    [Reference: VTK File Format Specification — https://docs.vtk.org/en/latest/file_formats.html]

USAGE
    python scripts/audit_vtu.py --root results            # report only
    python scripts/audit_vtu.py --root results --repair   # fix + verify
    python scripts/audit_vtu.py --root results --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

try:
    import vtk
except Exception as exc:  # pragma: no cover - environment guard
    print(f"[FATAL] vtk is not importable: {exc}", file=sys.stderr)
    raise SystemExit(2) from exc


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def _ascii_block(text: str, anchor: str) -> str:
    """Return the raw ascii payload of the DataArray whose tag contains `anchor`.

    Parameters
    ----------
    text : str
        Full XML document.
    anchor : str
        Substring identifying the DataArray opening tag, e.g. Name="connectivity".

    Returns
    -------
    str
        Everything between the tag's closing `>` and the next `</DataArray>`.

    Raises
    ------
    ValueError
        If the anchor or its closing tag is absent.
    """
    i = text.find(anchor)
    if i < 0:
        raise ValueError(f"anchor {anchor!r} not found")
    j = text.find(">", i)
    if j < 0:
        raise ValueError(f"anchor {anchor!r} has no closing >")
    k = text.find("</DataArray>", j)
    if k < 0:
        raise ValueError(f"anchor {anchor!r} has no </DataArray>")
    return text[j + 1:k]


def read_header(path: str) -> tuple[int, int]:
    """Return (NumberOfPoints, NumberOfCells) from the Piece header.

    Raises
    ------
    FileNotFoundError, ValueError
        Missing file or missing/malformed <Piece> header.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    m = re.search(r'<Piece\s+NumberOfPoints="(\d+)"\s+NumberOfCells="(\d+)"', text)
    if m is None:
        raise ValueError("no <Piece> header")
    return int(m.group(1)), int(m.group(2))


def vtk_inspect(path: str) -> dict[str, Any]:
    """Load `path` with VTK and describe exactly what came back.

    Parameters
    ----------
    path : str
        Path to a .vtu file.

    Returns
    -------
    dict
        Keys: ok, error_code, points, cells, point_arrays, cell_arrays,
        field_arrays, error (message when ok is False).

    Notes
    -----
    VTK logs the connectivity failure to stderr; that is expected and is not
    swallowed here -- the returned error_code is the authoritative signal.
    """
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(path)
    reader.Update()
    grid = reader.GetOutput()
    code = reader.GetErrorCode()
    pts = grid.GetNumberOfPoints() if grid else 0
    cells = grid.GetNumberOfCells() if grid else 0
    # Distinguish two different non-ok states, because they mean different
    # things and lumping them hides a real defect behind a benign one:
    #   unreadable -> VTK itself rejected the file (error_code != 0)
    #   empty      -> VTK parsed it fine but it declares/contains nothing
    # A well-formed placeholder (NumberOfPoints="0") must NOT be reported as
    # corruption, and a corrupted file must NOT be reported as merely empty.
    unreadable = (code != 0)
    empty = (not unreadable and (pts == 0 or cells == 0))
    ok = (not unreadable and not empty)

    def _names(dsa: Any) -> list[str]:
        if dsa is None:
            return []
        return [dsa.GetArrayName(i) for i in range(dsa.GetNumberOfArrays())]

    if unreadable:
        verdict = "unreadable"
    elif empty:
        verdict = "empty"
    else:
        verdict = "ok"

    return {
        "ok": bool(ok),
        "unreadable": bool(unreadable),
        "empty": bool(empty),
        "verdict": verdict,
        "error_code": int(code),
        "points": int(pts),
        "cells": int(cells),
        "point_arrays": _names(grid.GetPointData()) if grid else [],
        "cell_arrays": _names(grid.GetCellData()) if grid else [],
        "field_arrays": _names(grid.GetFieldData()) if grid else [],
        "error": None if ok else f"vtk error code {code}",
    }


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------
def expected_connectivity(n_points: int, n_cells: int) -> tuple[list[int], int]:
    """Regenerate Write_VTU's quad connectivity from the two header integers.

    Parameters
    ----------
    n_points, n_cells : int
        From the <Piece> header.

    Returns
    -------
    (indices, n_theta)
        Flat list of 4*n_cells zero-based point indices, and the ring width.

    Raises
    ------
    ValueError
        If the header does not describe a complete ring/theta topology, i.e.
        N_Theta = n_points - n_cells is not positive or does not divide both
        counts.  Refusing here is the guard against "repairing" a file that
        was produced by some other writer.
    """
    n_theta = n_points - n_cells
    if n_theta <= 0 or n_points % n_theta or n_cells % n_theta:
        raise ValueError(
            f"header {n_points} pts / {n_cells} cells does not fit "
            f"(N+1)*Nt, N*Nt")
    n_rings = n_cells // n_theta
    out: list[int] = []
    for k in range(1, n_rings + 1):
        for t in range(n_theta):
            tn = (t + 1) % n_theta
            out.append((k - 1) * n_theta + t)   # N0
            out.append(k * n_theta + t)         # N1
            out.append(k * n_theta + tn)        # N2
            out.append((k - 1) * n_theta + tn)  # N3
    return out, n_theta


def render_defective(indices: list[int], n_cells: int) -> str:
    """Re-render `indices` exactly the way the broken Ada writer did.

    Four indices per cell separated by single spaces, NO separator between
    cells, and a newline after every fourth cell.

    Used as the proof step of A2: if this equals the bytes on disk, the
    regenerated connectivity is the original, not a reconstruction guess.
    """
    parts: list[str] = []
    for c in range(n_cells):
        base = c * 4
        parts.append(f"{indices[base]} {indices[base+1]} "
                     f"{indices[base+2]} {indices[base+3]}")
        if (c + 1) % 4 == 0:
            parts.append("\n")
    return "".join(parts)


def render_fixed(indices: list[int], n_cells: int) -> str:
    """Render `indices` the way the CORRECTED writer emits them (P0.1)."""
    parts: list[str] = []
    for c in range(n_cells):
        base = c * 4
        parts.append(f"{indices[base]} {indices[base+1]} "
                     f"{indices[base+2]} {indices[base+3]}")
        parts.append("\n" if (c + 1) % 4 == 0 else " ")
    if parts and parts[-1] == " ":
        parts[-1] = "\n"
    return "".join(parts)


def repair_file(path: str, dry_run: bool = False) -> dict[str, Any]:
    """Rewrite a corrupt .vtu's connectivity array, guarded by proof (A2).

    Parameters
    ----------
    path : str
        Candidate .vtu.
    dry_run : bool
        When True, perform every check but write nothing.

    Returns
    -------
    dict
        status in {repaired, already-ok, refused, error}, plus a detail string
        explaining the decision.

    Raises
    ------
    (none)
        Every failure is captured and returned; a refused file is untouched.
    """
    try:
        n_points, n_cells = read_header(path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except (OSError, ValueError) as exc:
        return {"status": "error", "detail": f"read failed: {exc}"}

    # A well-formed placeholder declares zero points and zero cells and writes
    # its DataArrays as self-closing tags.  Nothing to repair -- report it as
    # `empty` so it is counted as a content gap rather than corruption.
    if n_points == 0 or n_cells == 0:
        return {
            "status": "empty",
            "detail": (f"valid but empty placeholder: "
                       f"NumberOfPoints={n_points} NumberOfCells={n_cells}; "
                       f"no geometry to display in ParaView"),
        }

    try:
        raw = _ascii_block(text, 'Name="connectivity"')
    except (OSError, ValueError) as exc:
        return {"status": "error", "detail": f"connectivity unreadable: {exc}"}

    # Already valid?  (A3)
    probe = vtk_inspect(path)
    if probe["ok"]:
        return {"status": "already-ok", "detail": probe["error"] or "reads cleanly"}

    try:
        indices, n_theta = expected_connectivity(n_points, n_cells)
    except ValueError as exc:
        return {"status": "refused", "detail": str(exc)}

    if len(indices) != 4 * n_cells:
        return {"status": "refused", "detail": "index count mismatch"}
    if max(indices) >= n_points:
        return {"status": "refused", "detail": "regenerated index out of range"}

    # PROOF (A2): reproducing the defective rendering byte-for-byte.
    # `raw` carries Put_Line's trailing newline immediately after the opening
    # tag, so both sides are whitespace-normalised before comparison; the
    # payload itself must still match exactly, character for character.
    proof = render_defective(indices, n_cells)
    if proof.strip() != raw.strip():
        return {
            "status": "refused",
            "detail": ("regenerated connectivity does not reproduce the bytes "
                       "on disk; refusing to overwrite (A2)"),
        }

    # Preserve the original leading/trailing whitespace so only the payload
    # region changes and the surrounding XML is left untouched.
    lead = raw[:len(raw) - len(raw.lstrip())]
    trail = raw[len(raw.rstrip()):]
    replacement = lead + render_fixed(indices, n_cells).strip() + trail
    new_text = text.replace(raw, replacement, 1)
    if new_text == text:
        return {"status": "refused", "detail": "replacement was a no-op"}

    if not dry_run:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        after = vtk_inspect(path)
        if not after["ok"]:
            return {
                "status": "error",
                "detail": (f"rewritten but VTK still refuses: "
                           f"code={after['error_code']} pts={after['points']} "
                           f"cells={after['cells']}"),
            }
        if after["cells"] != n_cells or after["points"] != n_points:
            return {
                "status": "error",
                "detail": (f"post-repair shape {after['points']}pts/"
                           f"{after['cells']}cells != header "
                           f"{n_points}/{n_cells}"),
            }

    return {
        "status": "repaired" if not dry_run else "would-repair",
        "detail": (f"n_theta={n_theta}, {4*n_cells} indices restored, "
                   f"proof matched byte-for-byte"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def find_vtu(root: str) -> list[str]:
    """Return every .vtu under `root`, sorted for deterministic reporting."""
    found: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".vtu"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    """Audit (and optionally repair) every .vtu under --root.

    Parameters
    ----------
    argv : list[str] | None
        Argument vector; defaults to sys.argv.

    Returns
    -------
    int
        0 when no file is unreadable, 1 when some remain broken, 2 on
        environment failure.

    Raises
    ------
    SystemExit
        Only for the missing-vtk environment guard.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="results", help="directory to scan")
    ap.add_argument("--repair", action="store_true", help="rewrite broken files")
    ap.add_argument("--dry-run", action="store_true",
                    help="check what --repair would do, write nothing")
    ap.add_argument("--json", help="write a machine-readable report here")
    args = ap.parse_args(argv)

    files = find_vtu(args.root)
    if not files:
        print(f"[AUDIT] no .vtu files under {args.root}")
        return 1

    report: dict[str, Any] = {"root": args.root, "total": len(files), "files": []}
    counts: dict[str, int] = {}
    # `unreadable` is the corruption metric; `empty` is a content gap and is
    # tallied separately so a benign placeholder cannot mask a real defect or
    # vice versa.
    broken_before = 0
    empty_before = 0

    for path in files:
        rec: dict[str, Any] = {"path": path}
        pre = vtk_inspect(path)
        rec["before"] = pre
        if pre["unreadable"]:
            broken_before += 1
        elif pre["empty"]:
            empty_before += 1

        if args.repair or args.dry_run:
            rec["repair"] = repair_file(path, dry_run=args.dry_run)
            status = rec["repair"]["status"]
            counts[status] = counts.get(status, 0) + 1
            if args.repair:
                rec["after"] = vtk_inspect(path)
        report["files"].append(rec)

    after = [f.get("after") or f["before"] for f in report["files"]]
    broken_after = sum(1 for s in after if s["unreadable"])
    empty_after = sum(1 for s in after if s["empty"])

    report["broken_before"] = broken_before
    report["broken_after"] = broken_after
    report["empty_before"] = empty_before
    report["empty_after"] = empty_after
    report["repair_counts"] = counts

    print(f"[AUDIT] scanned {len(files)} .vtu under {args.root}")
    print(f"[AUDIT] UNREADABLE (corrupt) before: {broken_before}")
    if args.repair:
        print(f"[AUDIT] UNREADABLE (corrupt) after : {broken_after}")
        for k, v in sorted(counts.items()):
            print(f"          {k:14s} {v}")
    elif args.dry_run:
        for k, v in sorted(counts.items()):
            print(f"          {k:14s} {v}")
    if empty_after:
        print(f"[AUDIT] EMPTY placeholders: {empty_after} "
              f"(valid VTK, zero geometry -- nothing to show in ParaView)")

    # Array inventory across the whole tree (P1.1).
    pa: set[str] = set()
    ca: set[str] = set()
    for f in report["files"]:
        src = f.get("after") or f["before"]
        pa.update(src.get("point_arrays") or [])
        ca.update(src.get("cell_arrays") or [])
    report["union_point_arrays"] = sorted(pa)
    report["union_cell_arrays"] = sorted(ca)
    print(f"[AUDIT] point arrays union: {sorted(pa)}")
    print(f"[AUDIT] cell  arrays union: {sorted(ca)}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"[AUDIT] wrote {args.json}")

    return 1 if broken_after else 0


if __name__ == "__main__":
    raise SystemExit(main())
