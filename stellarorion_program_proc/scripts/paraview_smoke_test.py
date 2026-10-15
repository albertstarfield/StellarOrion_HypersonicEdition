#!/usr/bin/env pvpython
"""ParaView smoke test: open every .vtu, exercise every array's visibility,
render, and screenshot. Run ONLY under pvpython.

    /Applications/ParaView-6.2.0.app/Contents/bin/pvpython \\
        scripts/paraview_smoke_test.py --root results --out .tmp/pv_test

WHAT IT PROVES
    The defect this guards against was a corrupt connectivity array: the grid
    never loaded, so every cell/point array appeared as a broken entry as soon
    as its visibility box was clicked.  Opening the file is therefore not
    enough -- this script drives the exact interaction the user reported:

      1. open the file and assert the pipeline produced points AND cells
      2. for EVERY point and cell array:
           a. make it the active scalar (what Colour By picks)
           b. switch the representation's visibility OFF then ON again
           c. Render
         an exception at any of those steps is a FAIL for that array
      3. save a PNG so a human/agent can confirm readability

AXIOMS
    A1  A file that opens but yields 0 points or 0 cells is a FAIL, not a
        pass -- an empty grid renders a blank image while claiming success.
    A2  Visibility is exercised per-array, not once for the representation:
        the reported bug was per-array.
    A3  Every failure is reported with the file and array that caused it;
        a partial run still writes the report rather than dying silently.

CITATIONS
    [Citation: ParaView 6.2.0 Python API — https://kitware.github.io/paraview-docs/]
    [Reference: VTK XMLUnstructuredGridReader — https://vtk.org/doc/]

EXIT CODES
    0 all tested files passed, 1 at least one failure, 2 usage/env error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

# A1: fail loudly rather than rendering a blank window and calling it a pass.
from paraview.simple import (
    ColorBy,
    Delete,
    GetActiveViewOrCreate,
    GetAnimationScene,
    GetColorTransferFunction,
    GetScalarBar,
    OpenDataFile,
    Render,
    ResetCamera,
    SaveScreenshot,
    Show,
)


def _array_names(dataset) -> tuple[list[str], list[str]]:
    """Return (point_array_names, cell_array_names) of a vtk dataset.

    Parameters
    ----------
    dataset : vtk.vtkDataSet
        Already-updated output of a reader.

    Returns
    -------
    (list[str], list[str])
        Names in stored order; empty lists when the attribute has no arrays.

    Raises
    ------
    AttributeError
        If `dataset` exposes no PointData/CellData -- a reader that returned
        None already failed at open time and is caught by the caller.
    """
    pd = dataset.GetPointData()
    cd = dataset.GetCellData()
    pnames = [pd.GetArrayName(i) for i in range(pd.GetNumberOfArrays())]
    cnames = [cd.GetArrayName(i) for i in range(cd.GetNumberOfArrays())]
    return pnames, cnames


def test_file(path: str, outdir: str, screenshot: bool = True) -> dict:
    """Open `path`, exercise every array's visibility, and screenshot it.

    Parameters
    ----------
    path : str
        Absolute or relative path to a .vtu.
    outdir : str
        Directory to receive the PNG (created if needed).
    screenshot : bool
        When False, skip SaveScreenshot (faster for bulk triage).

    Returns
    -------
    dict
        status ('pass'|'fail'), points, cells, arrays[], arrays_failed[],
        screenshot path or None, error text or None, elapsed seconds.

    Raises
    ------
    (none)
        Every exception is captured into the returned record (A3) so a batch
        keeps running after one bad file.
    """
    t0 = time.monotonic()
    rec: dict = {
        "path": path, "status": "fail", "points": 0, "cells": 0,
        "arrays": [], "arrays_failed": [], "screenshot": None,
        "error": None, "elapsed": 0.0,
    }
    reader = None
    try:
        reader = OpenDataFile(path)
        if reader is None:
            rec["error"] = "OpenDataFile returned None"
            return rec

        view = GetActiveViewOrCreate("RenderView")

        # A1: an empty grid is a failure, not a blank pass.
        rep = Show(reader, view)
        dataset = reader.GetClientSideObject().GetOutputDataObject(0)
        pts = dataset.GetNumberOfPoints()
        cells = dataset.GetNumberOfCells()
        rec["points"] = int(pts)
        rec["cells"] = int(cells)
        if pts == 0 or cells == 0:
            rec["error"] = (f"empty grid: {pts} points, {cells} cells "
                            f"(nothing to display)")
            return rec

        pnames, cnames = _array_names(dataset)
        rec["arrays"] = [{"name": n, "scope": "point"} for n in pnames]
        rec["arrays"] += [{"name": n, "scope": "cell"} for n in cnames]
        if not rec["arrays"]:
            rec["error"] = "grid has no point or cell arrays to colour by"
            return rec

        ResetCamera(view)
        Render(view)

        # A2: exercise EVERY array, individually.
        for spec in list(rec["arrays"]):
            name, scope = spec["name"], spec["scope"]
            try:
                source = reader.PointData if scope == "point" else reader.CellData
                array = source.GetArray(name)
                if array is None:
                    raise RuntimeError(f"{scope} array {name!r} not retrievable")
                # Colour By takes an association string + array name.
                # (Passing reader.CellData -- a FieldDataInformation proxy --
                # raises 'invalid association string'.)
                association = "POINTS" if scope == "point" else "CELLS"
                attr = (dataset.GetPointData() if scope == "point"
                        else dataset.GetCellData())
                attr.SetActiveScalars(name)
                ColorBy(rep, (association, name))
                tf = GetColorTransferFunction(name)
                bar = GetScalarBar(tf, view)
                if bar is not None:
                    bar.Title = f"{name} ({scope})"
                # the reported interaction: toggle visibility off then on
                rep.Visibility = 0
                Render(view)
                rep.Visibility = 1
                Render(view)
            except Exception as exc:  # noqa: BLE001 - per-array capture (A3)
                rec["arrays_failed"].append(
                    {"name": name, "scope": scope, "error": str(exc)})

        if rec["arrays_failed"]:
            rec["error"] = (f"{len(rec['arrays_failed'])} of "
                            f"{len(rec['arrays'])} arrays failed visibility")
            return rec

        if screenshot:
            os.makedirs(outdir, exist_ok=True)
            stem = os.path.splitext(os.path.basename(path))[0]
            png = os.path.join(outdir, f"{stem}.png")
            ResetCamera(view)
            Render(view)
            SaveScreenshot(png, view, ImageResolution=(1024, 768))
            if not os.path.isfile(png) or os.path.getsize(png) == 0:
                rec["error"] = "screenshot was not written"
                return rec
            rec["screenshot"] = png

        rec["status"] = "pass"
        return rec

    except Exception as exc:  # noqa: BLE001 - batch must not die (A3)
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["trace"] = traceback.format_exc(limit=4)
        return rec
    finally:
        # Release the reader before returning so a batch does not leak
        # render windows; the screenshot was already captured above.
        close_reader(reader)
        rec["elapsed"] = round(time.monotonic() - t0, 3)


def close_reader(reader) -> None:
    """Release a ParaView reader and its view if one was created.

    Parameters
    ----------
    reader : proxy or None
        The proxy returned by OpenDataFile.

    Returns
    -------
    None

    Raises
    ------
    (none)
        Cleanup is best-effort; a failure here must not mask a real result.
    """
    if reader is None:
        return
    try:
        Delete(reader)
        scene = GetAnimationScene()
        if scene is not None:
            scene.Stop()
    except Exception as exc:  # noqa: BLE001 - cleanup must not mask a result
        # NOT a bare `pass`: cleanup failure is still a fact the operator
        # should see. It must not change the verdict (A3), but swallowing it
        # outright would hide a leaked ParaView proxy across 1551 files.
        print(f"[PV] warn: reader cleanup failed: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Run the smoke test over every .vtu under --root.

    Parameters
    ----------
    argv : list[str] | None
        Defaults to sys.argv[1:].

    Returns
    -------
    int
        0 all pass, 1 any failure, 2 bad usage.

    Raises
    ------
    SystemExit
        Never; the status is returned so pvpython's own runner reports it.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="results")
    ap.add_argument("--out", default=".tmp/pv_test",
                    help="screenshot output directory")
    ap.add_argument("--report", default=None,
                    help="JSON report path (default: <out>/report.json)")
    ap.add_argument("--limit", type=int, default=0,
                    help="test only the first N files (0 = all)")
    ap.add_argument("--no-screenshots", action="store_true")
    ap.add_argument("--pattern", default=".vtu")
    args = ap.parse_args(argv)

    files: list[str] = []
    for dirpath, _dn, filenames in os.walk(args.root):
        for n in sorted(filenames):
            if n.endswith(args.pattern):
                files.append(os.path.join(dirpath, n))
    files.sort()
    if args.limit:
        files = files[:args.limit]
    if not files:
        print(f"[PV] no {args.pattern} files under {args.root}")
        return 2

    report_path = args.report or os.path.join(args.out, "report.json")
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)

    results = []
    n_pass = n_fail = 0
    for i, path in enumerate(files, 1):
        rec = test_file(path, args.out, screenshot=not args.no_screenshots)
        results.append(rec)
        if rec["status"] == "pass":
            n_pass += 1
        else:
            n_fail += 1
            print(f"[PV][FAIL] {path}: {rec['error']}")
        if i % 100 == 0 or i == len(files):
            print(f"[PV] {i}/{len(files)}  pass={n_pass} fail={n_fail}",
                  flush=True)

    summary = {
        "root": args.root,
        "total": len(files),
        "pass": n_pass,
        "fail": n_fail,
        "files": results,
    }
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"[PV] report -> {report_path}")
    print(f"[PV] PASS {n_pass} / FAIL {n_fail} of {len(files)}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
