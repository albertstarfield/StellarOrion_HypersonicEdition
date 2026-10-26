#!/usr/bin/env python3
"""Emit the multi-level mesh-independence case trees SOP Ch.6 / Ch.12#4 require.

AXIOMS
  A1.  Every level is a REAL SPARTA solve of the production deck with ONLY
       `create_grid` changed.  Nothing here synthesises a value that the
       solver did not print.
  A2.  The QoI is `c_heat` -- `compute heat reduce max f_1[3]`, the peak
       surface kinetic-energy flux -- because it is already declared by the
       production deck (results/<tree>/in.hiad:41).  Drag and lift are taken
       from the same thermo line as secondary quantities.
  A3.  The default tree is `00_reference`, the project's authoritative
       reference run (results/RUNS.md).  Its HIAD_custom.surf is the
       geometry every level revolve-threads.
  A4.  A level that fails to run writes status "failed" and NO qoi_value.
       The aggregator must never see a fabricated number standing in for a
       crashed level.

THEORIES
  T1.  Mesh independence is the statement that a QoI stops moving as the grid
       is refined.  With levels ordered by cell count, the deltas
       |Q_k - Q_{k-1}| / |Q_{k-1}| are the quantity to compare against the
       5% criterion; the FINEST pair is the one that decides the gate.
  T2.  `create_grid NX NY 1` on a fixed box makes NX*NY parent cells, so the
       cell count reported in case.json is read back from the solver log
       rather than computed -- the solver is the authority (IS, IS).
  T3.  SPARTA prints its solver table under a NAMED header built from the
       deck's own statements -- observed here as
       `Step CPU Np c_drag c_lift c_heat`.  The header, not the column
       position, is the contract: the set of trailing columns varies with
       which `compute ... reduce` lines the deck declares, so a parser that
       counts positions binds the wrong quantity to the wrong name.

APPLICATIONS
  -  `python scripts/run_grid_independence.py`  -> one level dir per entry of
     --levels plus results/grid_independence/level_<k>/case.json.  Three
     levels is the minimum the GCI needs; a fourth is how a non-monotone
     series is resolved (see make_grid_independence_plots.py, review item #2).
     Add a level without re-flying the others with
     `--levels 70 100 139 200 --only 4` (dirs are numbered by LIST ORDER, so
     the list must still start with the three existing sizes).
  -  `python scripts/generate_sop_artifacts.py --grid-independence` then
     aggregates them into the JSON the GUI reads.

References:
    - Standard Operating Procedure of CFD.md, Ch.6 (mesh independence),
      Ch.12#4, Ch.15
    - SPARTA compute reduce: https://lammps.sandia.gov/doc/compute_reduce.html
      (SPARTA follows the LAMMPS compute/fix conventions)
    - RFC 4180 (CSV), https://www.rfc-editor.org/rfc/rfc4180
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"
OUT_ROOT = RESULTS_DIR / "grid_independence"
DEFAULT_TREE = "00_reference"
DEFAULT_LEVELS = (70, 100, 139)   # coarse, medium, fine (production = 139)
DEFAULT_STEPS = 2200              # same as the production deck
SPARTA_BIN = PROJECT_ROOT.parent / "sparta" / "src" / "spa_mac_mpi"

# SPARTA writes the solver table under a NAMED header, e.g.
#   Step CPU Np c_drag c_lift c_heat
# Column count varies with which `compute ... reduce` statements the deck
# declares, so positions must NEVER be assumed -- a positional read here
# silently assigned c_drag to heat and c_heat to lift.  Parse the header and
# bind by name.
_STEP_HEADER = re.compile(r"^Step\s+CPU\s+Np\b.*$")
_ROW = re.compile(r"^\s*(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(.*)$")
_CREATED_CELLS = re.compile(r"^Created (\d+) child grid cells")


def _log(msg: str) -> None:
    """Print a progress line to stdout.

    Parameters:
        msg: text to emit, unprefixed.
    Returns: None.
    Exceptions: none (print does not raise for str output).
    """
    print(f"[grid-indep] {msg}", flush=True)


def _find_sparta() -> Path | None:
    """Locate a runnable SPARTA binary.

    Parameters: none.
    Returns:
        Path to the executable, or None when neither candidate exists.
    Exceptions: none; candidate paths are probed for existence and exec bit.
    References: https://github.com/sparta/sparta
    """
    candidates = [SPARTA_BIN, Path(shutil.which("spa") or "")]
    for cand in candidates:
        if cand and cand.is_file() and os.access(cand, os.X_OK):
            return cand
    return None


def build_deck(template: Path, level_dir: Path, n_grid: int, steps: int) -> Path | None:
    """Derive a level deck from the production `in.hiad`.

    Parameters:
        template: production deck (results/<tree>/in.hiad).
        level_dir: directory the deck and its dumps will live in.
        n_grid: cells per side for `create_grid n n 1`.
        steps: `run` length.
    Returns:
        Path to the written deck, or None when the template is missing.
    Exceptions:
        OSError propagates on write failure -- a deck that cannot be written
        must stop the level, not be skipped silently.
        ValueError when a dump/restart line carries no output path; that is
        a template the repointer does not understand and must not be passed
        through with its stale destination.
    Notes:
        * `create_grid` is rewritten (A1 -- the only physical change).
        * every dump path is repointed into level_dir, because the template
          still writes to the pre-migration `results/validation_scalloped/`.
        * `thermo_style custom` + `thermo 100` are INSERTED (T3) so the QoI
          is actually printed; the template has neither.
    References: Standard Operating Procedure of CFD.md, Ch.6
    """
    if not template.is_file():
        _log(f"template missing: {template}")
        return None
    lines = template.read_text(encoding="utf-8", errors="replace").splitlines()

    out: list[str] = []
    seen_grid = False
    seen_run = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("create_grid"):
            out.append(f"create_grid     {n_grid} {n_grid} 1")
            seen_grid = True
            continue
        if stripped.startswith(("dump ", "restart ")):
            # Repoint every output path into this level's directory.  The
            # template writes to the pre-migration results/validation_scalloped/
            # tree for BOTH dump and restart; leaving either would either fail
            # outright or deposit artefacts outside the case record.
            parts = line.split()
            # SPARTA's dump syntax is `dump ID group style every file fields`
            # -- there is no `out` keyword, so searching for that token found
            # nothing and the repoint silently no-op'ed (the level then died
            # with "Cannot open dump file").  The path is simply the first
            # token containing "/", which also covers `restart every file`.
            path_idx = next((i for i, tok in enumerate(parts) if "/" in tok), -1)
            if path_idx < 0:
                raise ValueError(f"no output path found in line: {line.strip()}")
            parts[path_idx] = str(level_dir / Path(parts[path_idx]).name)
            out.append(" ".join(parts))
            continue
        if stripped.startswith("run "):
            if not seen_run:
                # NOTE: SPARTA has NO `thermo`/`thermo_style` command
                # (src/input.cpp accepts log/print/restart/dump/fix only).
                # Named `compute ... reduce` values DO appear on the solver
                # table as trailing columns under a header naming them
                # (`Step CPU Np c_drag c_lift c_heat`), so the QoI comes from
                # that table -- bound by column NAME, never by position.
                out.append("# --- grid-independence note ---")
                out.append("# QoI read from the `Step CPU Np ...` table by")
                out.append("# column name; see run_grid_independence.parse_qoi.")
                out.append("# --- end note ---")
                seen_run = True
            out.append(f"run             {steps}")
            continue
        out.append(line)

    if not seen_grid or not seen_run:
        _log(f"{template.name}: create_grid/run line not found "
             f"(grid={seen_grid}, run={seen_run})")
        return None

    deck = level_dir / "in.hiad"
    deck.write_text("\n".join(out) + "\n", encoding="utf-8")
    return deck


def parse_qoi(log_path: Path) -> tuple[dict[str, float] | None, int]:
    """Read the final QoI row and the solver's own cell count from a run log.

    Parameters:
        log_path: SPARTA log written by the level run.
    Returns:
        (qoi, n_cells).  qoi holds heat/drag/lift/cpu_s/step from the LAST
        printed thermo row, or None when no such row exists (T3 violated or
        the run died).  n_cells is 0 when the solver never reported it.
    Exceptions:
        OSError caught -> (None, 0); a row with non-numeric fields is skipped,
        never defaulted to 0.0.
    References: Standard Operating Procedure of CFD.md, Ch.6
    """
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log(f"cannot read {log_path}: {exc}")
        return None, 0

    n_cells = 0
    qoi: dict[str, float] | None = None
    names: list[str] | None = None
    for line in text.splitlines():
        m = _CREATED_CELLS.match(line.strip())
        if m:
            n_cells = int(m.group(1))

        stripped = line.strip()
        if _STEP_HEADER.match(stripped):
            names = stripped.split()
            continue
        if names is None:
            continue

        m = _ROW.match(line)
        if not m:
            # A non-numeric line ends the numeric table; keep the last row.
            if qoi is not None and stripped and not stripped[0].isdigit():
                names = None
            continue
        try:
            values = [float(tok) for tok in stripped.split()]
        except ValueError:
            _log(f"non-numeric QoI row skipped: {stripped[:60]}")
            continue
        if len(values) != len(names):
            continue
        qoi = dict(zip(names, values, strict=True))

    if qoi is None:
        return None, n_cells
    if "c_heat" not in qoi:
        # Honest failure: the deck did not declare `compute heat reduce`, so
        # there is no QoI to report.  Returning the row without it would let
        # the caller publish a record that names a value it never measured.
        _log("log has a Step table but no c_heat column "
             "(deck missing `compute heat reduce`)")
        return None, n_cells
    return {
        "step": qoi.get("Step", 0.0),
        "cpu_s": qoi.get("CPU", 0.0),
        "n_particles": qoi.get("Np", 0.0),
        "heat": qoi["c_heat"],
        "drag": qoi.get("c_drag", 0.0),
        "lift": qoi.get("c_lift", 0.0),
    }, n_cells


def run_level(index: int, n_grid: int, template: Path, steps: int,
              sparta: Path) -> dict[str, object]:
    """Solve one refinement level and write its case.json (A4).

    Parameters:
        index: 1-based level number.
        n_grid: cells per side.
        template: production deck to derive from.
        steps: run length.
        sparta: SPARTA executable.
    Returns:
        The case record written to disk (also returned for the summary).
        On any failure the record carries status "failed" and NO qoi_value.
    Exceptions:
        subprocess failures are captured in the record; OSError during
        directory creation propagates (a level we cannot write is fatal).
    References: Standard Operating Procedure of CFD.md, Ch.6 / Ch.12#4
    """
    level_dir = OUT_ROOT / f"level_{index}"
    level_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    record: dict[str, object] = {
        "level": index,
        "n_grid": n_grid,
        "steps": steps,
        "run_record_id": (
            f"gi-l{index}-{n_grid}x{n_grid}-"f"{datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%S')}"
        ),
        "geometry": str(template),
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "status": "failed",
    }
    try:
        deck = build_deck(template, level_dir, n_grid, steps)
    except (OSError, ValueError) as exc:
        record["error"] = f"deck build failed: {exc}"
        _record(level_dir, record)
        return record
    if deck is None:
        record["error"] = "deck could not be derived from template"
        _record(level_dir, record)
        return record

    # Surface file must sit beside the deck: the template references
    # HIAD_custom.surf relatively.
    src_surf = template.parent / "HIAD_custom.surf"
    if src_surf.is_file():
        shutil.copy2(src_surf, level_dir / "HIAD_custom.surf")

    # The production deck references air.species/air.vss/air.react RELATIVE
    # to its own directory, but results/<tree>/ does not carry them -- they
    # live at the project root (and the vendored SPARTA examples).  Searching
    # a candidate list keeps the copy from silently no-op'ing, which would
    # surface only as an opaque SPARTA failure much later.
    _SEARCH_DIRS = (
        template.parent,
        PROJECT_ROOT,
        PROJECT_ROOT.parent / "sparta" / "examples" / "paraview",
    )
    for species in ("air.species", "air.vss", "air.react"):
        src = next((d / species for d in _SEARCH_DIRS if (d / species).is_file()), None)
        if src is None:
            record["error"] = f"missing input file: {species} (searched {', '.join(str(d) for d in _SEARCH_DIRS)})"
            _record(level_dir, record)
            return record
        shutil.copy2(src, level_dir / species)

    _log(f"level {index}: {n_grid}x{n_grid}, {steps} steps -> {level_dir.name}")
    try:
        proc = subprocess.run(
            # SPARTA rejects a bare deck name ("Invalid command-line
            # argument", sparta.cpp:176); it must be passed as -in <file>.
            [str(sparta), "-in", "in.hiad"],
            cwd=str(level_dir),
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
    except subprocess.TimeoutExpired:
        record["error"] = "timeout after 3600 s"
        _record(level_dir, record)
        return record
    except OSError as exc:
        record["error"] = f"spawn failed: {exc}"
        _record(level_dir, record)
        return record

    (level_dir / "stdout.log").write_text(
        (proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""),
        encoding="utf-8",
    )
    record["exit_code"] = proc.returncode

    log_path = level_dir / "log.sparta"
    if not log_path.is_file():
        cand = sorted(level_dir.glob("log.*"))
        log_path = cand[0] if cand else log_path

    qoi, n_cells = parse_qoi(log_path)
    record["n_cells"] = n_cells
    record["wall_time_s"] = round(time.time() - started, 3)
    if proc.returncode != 0:
        record["error"] = f"sparta exit {proc.returncode}"
    elif qoi is None:
        record["error"] = "no QoI row in log (thermo_style missing or run died)"
    else:
        record["status"] = "ok"
        record["qoi_name"] = "heat_peak_wm2"
        record["qoi_value"] = qoi["heat"]
        record["secondary"] = {"drag": qoi["drag"], "lift": qoi["lift"],
                               "n_particles": qoi["n_particles"],
                               "final_step": qoi["step"],
                               "cpu_s": qoi["cpu_s"]}
        _log(f"level {index}: cells={n_cells} heat={qoi['heat']:.6g} "
             f"status={record['status']}")
    _record(level_dir, record)
    return record


def _record(level_dir: Path, record: dict[str, object]) -> None:
    """Write case.json atomically for one level.

    Parameters:
        level_dir: directory receiving case.json.
        record: fully-populated level record.
    Returns: None.
    Exceptions:
        OSError propagates -- losing a record silently would leave the
        aggregator with fewer levels than were actually run (A4).
    References: https://docs.python.org/3/library/json.html
    """
    target = level_dir / "case.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, target)


def main(argv: list[str] | None = None) -> int:
    """Run the mesh-independence study over the requested levels.

    Parameters:
        argv: argument list; defaults to sys.argv[1:].
    Returns:
        0 when every level that was actually run reached status "ok", 1
        otherwise.
    Exceptions:
        Missing SPARTA binary or template is reported and returns 1 -- never
        a silent success with zero levels.

    AXIOMS:
        A1  The Grid Convergence Index is undefined for fewer than three
            levels (two grids give a difference, not an order), so fewer than
            three sizes is refused rather than run.
        A2  A fourth level is permitted and is the only sound way to settle a
            series whose successive differences grow -- no extrapolated value
            may be invented from a non-monotone three-level series.

    References: Standard Operating Procedure of CFD.md, Ch.6, Ch.15
    """
    parser = argparse.ArgumentParser(
        prog="run_grid_independence",
        description="Solve the production deck at three grid resolutions "
                    "and write level_*/case.json for SOP Ch.6.")
    parser.add_argument("--tree", default=DEFAULT_TREE)
    parser.add_argument("--levels", nargs="+", type=int,
                        default=list(DEFAULT_LEVELS),
                        help="cells per side, low->high (default: %(default)s)")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="run just these level numbers (smoke testing)")
    args = parser.parse_args(argv)

    sparta = _find_sparta()
    if sparta is None:
        print("[grid-indep] ERROR: no SPARTA binary found "
              f"(looked for {SPARTA_BIN} and `spa` on PATH)", file=sys.stderr)
        return 1
    template = RESULTS_DIR / args.tree / "in.hiad"
    if not template.is_file():
        print(f"[grid-indep] ERROR: template deck missing: {template}",
              file=sys.stderr)
        return 1
    if len(args.levels) < 3:
        #  WHY: two grids give a difference but no observed order, so the GCI
        #  would be undefined; refuse rather than emit a meaningless number.
        print("[grid-indep] ERROR: at least 3 level sizes are required",
              file=sys.stderr)
        return 1

    _log(f"sparta={sparta}")
    _log(f"template={template.relative_to(PROJECT_ROOT)}")
    _log(f"levels={args.levels} steps={args.steps}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for idx, n_grid in enumerate(args.levels, start=1):
        if args.only is not None and idx not in args.only:
            continue
        results.append(run_level(idx, n_grid, template, args.steps, sparta))

    ok = sum(1 for r in results if r.get("status") == "ok")
    _log(f"finished: {ok}/{len(results)} levels ok")
    _log("next: python scripts/generate_sop_artifacts.py --grid-independence")
    return 0 if ok == len(results) and ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
