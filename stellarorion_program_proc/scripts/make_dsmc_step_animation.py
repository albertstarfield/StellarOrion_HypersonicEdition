#!/usr/bin/env python3
"""Render the DSMC relaxation as a step-by-step animation (step 0 -> final).

WHY
    A DSMC case is a sequence of relaxation steps, not a single picture: the
    flow field starts from the freestream fill, a bow shock forms, and the
    surface statistics converge. The report shows that sequence only as a
    handful of static panels, so a reader cannot see the transient. This script
    turns the per-step grid dumps the solver already writes into one MP4, so
    the transient becomes visible without re-running anything.

AXIOMS
    A1  Every ``grid.<step>.out`` in a case tree is a complete, self-contained
        snapshot: its header names the step and its rows carry the cell state.
        A frame is therefore a pure function of one file -- no interpolation
        between files is needed and none is invented.
    A2  The colour scale must be identical on every frame, otherwise the
        animation could show a field that only looks stationary because the
        scale moves with it.
    A3  A cell with zero temperature holds no molecules. That is a GAP in the
        sampled region, not a 0 K measurement, so it is masked rather than
        painted at the bottom of the colour scale.
    A4  The body outline comes from the same ``.surf`` file SPARTA integrated,
        so the mask and the outline cannot disagree about where the wall is.
    A5  The cells are an adaptive unstructured list, not a rectangular array:
        the dump of the reference case holds 19 322 rows for 139 x 139 unique
        centres, i.e. one duplicated id. Each cell is therefore drawn as its
        own quadrilateral and no reshape is attempted.

THEOREMS
    T1  Sorting the dumps by the integer step in their filename (never by
        lexicographic order) is monotone in simulated time, because the step
        counter increases with every write. A lexicographic sort would place
        step 1000 before step 200.
    T2  With the colour limits fixed (A2) and the mask fixed (A3), two frames
        differ only in the data they display; any visible change in the video is
        therefore a change in the solution.

APPLICATIONS
    Called by ``run.py`` Phase 2c for every case tree that still holds its
    per-step grid dumps, and by hand as::

        venv_validation/bin/python3 scripts/make_dsmc_step_animation.py \
            --tree results/00_reference

    Outputs ``<tree>/plots/dsmc_steps.mp4`` plus the frames under
    ``<tree>/plots/dsmc_frames/`` (unless ``--no-frames`` is given).

CITATIONS
    [SPARTA] Plimpton & Gallis, SPARTA Users Manual -- the ``dump grid``
        command and the ``ITEM:``-delimited dump format.
    [FFmpeg] FFmpeg 9.0.2, libx264 -- https://ffmpeg.org/ffmpeg.html
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_TREE = Path("results") / "00_reference"
FRAME_DIR_NAME = "dsmc_frames"
MP4_NAME = "dsmc_steps.mp4"
DEFAULT_FPS = 4
HOLD_FRAMES = 8
#  WHY: ffmpeg is not on the default PATH of this host; the Homebrew keg-only
#  install is the one measured to exist.  Both candidates are tried before the
#  renderer gives up, and giving up is loud (see resolve_ffmpeg).
FFMPEG_CANDIDATES = ("ffmpeg", "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg")


def resolve_ffmpeg() -> str:
    """Locate the ffmpeg binary.

    Returns:
        The path of an ffmpeg executable that answered ``-version``.

    Raises:
        SystemExit: no candidate exists or runs. The renderer refuses to report
            success while writing no video.

    AXIOMS:
        A1  A missing encoder is an environment fault, not a reason to skip the
            artefact silently: the caller must see a non-zero exit code.

    THEOREMS:
        T1  Checking ``-version`` rather than mere existence rejects the
            half-installed binaries that exist on disk but cannot run.
    """
    for candidate in FFMPEG_CANDIDATES:
        path = candidate if Path(candidate).is_absolute() else shutil.which(candidate)
        if not path:
            continue
        try:
            probe = subprocess.run(
                [path, "-version"], capture_output=True, text=True, timeout=30, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"[anim] ffmpeg candidate {path} failed to run: {exc}", file=sys.stderr)
            continue
        if probe.returncode == 0:
            return path
        print(f"[anim] ffmpeg candidate {path} exited {probe.returncode}", file=sys.stderr)
    print(
        "[anim] FAILED: no working ffmpeg. Install it (brew install ffmpeg) or pass "
        "--ffmpeg <path>. Refusing to report success without a video.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def read_grid_dump(path: Path) -> dict:
    """Read one SPARTA grid dump into per-cell arrays.

    Parameters:
        path: the ``grid.<step>.out`` file.

    Returns:
        A dict with ``step`` (int) and the per-cell arrays ``xlo``, ``ylo``,
        ``xhi``, ``yhi`` (metres) and ``temp`` (gas temperature, kelvin).

    Raises:
        FileNotFoundError: the dump is missing.
        RuntimeError: the header carries no ``ITEM: TIMESTEP`` or ``ITEM: CELLS``
            block, lacks the ``f_3[*]`` column, or holds no data rows.

    AXIOMS:
        A1  The columns are located by HEADER NAME, never by position, because
            the dump line is prefixed with ``ITEM: CELLS`` and an off-by-two
            index silently drops every row.
        A2  A repeated cell id is a duplicated record, not a second cell: the
            reference dump carries 19 322 rows for 19 321 cells, with id 9096
            written twice and holding zero temperature both times.

    THEOREMS:
        T1  Stripping the ``ITEM: CELLS`` prefix restores the header/data column
            alignment, so ``f_3[*]`` indexes the same field in both.
        T2  Keeping the last record of a duplicated id preserves the cell set,
            because the duplicate carries identical geometry.
    """
    if not path.is_file():
        raise FileNotFoundError(f"grid dump not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    step = None
    header_index = None
    for index, line in enumerate(lines):
        if line.strip() == "ITEM: TIMESTEP" and index + 1 < len(lines):
            step = int(lines[index + 1].strip())
        if line.startswith("ITEM: CELLS"):
            header_index = index
            break
    if step is None:
        raise RuntimeError(f"{path}: no ITEM: TIMESTEP block")
    if header_index is None:
        raise RuntimeError(f"{path}: no ITEM: CELLS block")
    header = lines[header_index].split()[2:]
    try:
        temp_col = header.index("f_3[*]")
    except ValueError as exc:
        raise RuntimeError(f"{path}: header lacks f_3[*]: {header}") from exc

    records: dict[int, tuple[float, float, float, float, float]] = {}
    for line in lines[header_index + 1 :]:
        fields = line.split()
        if len(fields) <= temp_col:
            continue
        try:
            cell_id = int(fields[0])
            records[cell_id] = (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
                float(fields[4]),
                float(fields[temp_col]),
            )
        except ValueError:
            continue
    if not records:
        raise RuntimeError(f"{path}: no data rows")

    values = np.array(list(records.values()), dtype=float)
    return {
        "step": step,
        "xlo": values[:, 0],
        "ylo": values[:, 1],
        "xhi": values[:, 2],
        "yhi": values[:, 3],
        "temp": values[:, 4],
    }


def cell_polygons(dump: dict) -> tuple[list, np.ndarray]:
    """Turn the cell records into quadrilaterals plus their temperatures.

    Parameters:
        dump: the dict returned by :func:`read_grid_dump`.

    Returns:
        ``(verts, values)`` where ``verts`` is a list of 4-vertex polygons and
        ``values`` the matching temperatures, restricted to cells that actually
        hold molecules (axiom A3).

    Raises:
        Nothing: an all-empty dump simply yields empty lists, which the caller
            treats as a failed frame.

    AXIOMS:
        A1  Each row is one quadrilateral ``(xlo, ylo, xhi, yhi)``; that is the
            exact cell shape the solver integrated, so no interpolation is
            introduced by drawing it.
        A2  Cells with ``temp <= 0`` hold no molecules and are dropped, not
            painted (module axiom A3).

    THEOREMS:
        T1  Building one polygon per row makes the rendering independent of cell
            ordering, so the duplicate id and the adaptive sizing cannot corrupt
            the picture.
    """
    keep = dump["temp"] > 0.0
    if not keep.any():
        return [], np.array([])
    xlo = dump["xlo"][keep]
    ylo = dump["ylo"][keep]
    xhi = dump["xhi"][keep]
    yhi = dump["yhi"][keep]
    verts = np.stack(
        [
            np.column_stack((xlo, ylo)),
            np.column_stack((xhi, ylo)),
            np.column_stack((xhi, yhi)),
            np.column_stack((xlo, yhi)),
        ],
        axis=1,
    )
    return list(verts), dump["temp"][keep]


def read_surf(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read the body meridian from a SPARTA surface file.

    Parameters:
        path: the ``.surf`` file the case was integrated with.

    Returns:
        ``(z, r)`` -- the axial and radial coordinates of the surface points.

    Raises:
        FileNotFoundError: the surface file is missing.
        RuntimeError: the ``Points`` block cannot be located or is empty.

    AXIOMS:
        A1  Each point line is ``id Z_axial R_radial``; the block ends where the
            lines stop carrying three numeric fields.

    THEOREMS:
        T1  Taking the points in file order reproduces the meridian the solver
            integrated, so the outline drawn here is the actual wall.
    """
    if not path.is_file():
        raise FileNotFoundError(f"surface file not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "Points":
            start = index + 1
            break
    if start is None:
        raise RuntimeError(f"{path}: no Points block")
    z: list[float] = []
    r: list[float] = []
    for line in lines[start:]:
        fields = line.split()
        if len(fields) != 3:
            if z:
                break
            continue
        try:
            z.append(float(fields[1]))
            r.append(float(fields[2]))
        except ValueError:
            break
    if not z:
        raise RuntimeError(f"{path}: empty Points block")
    return np.asarray(z), np.asarray(r)


def read_step_times(tree: Path) -> dict[int, dict]:
    """Read the per-step diagnostics the solver already recorded.

    Parameters:
        tree: the case tree, expected to hold ``validation_timeseries.csv``.

    Returns:
        ``{step: {column: float}}``, empty when the file is absent or unreadable
        (an animation of the field alone is still honest).

    Raises:
        Nothing: a missing timeseries only loses the optional subtitle, and that
            is reported on stderr rather than hidden.

    AXIOMS:
        A1  The timeseries rows are keyed by DSMC step, the same axis as the
            dumps, so a frame can be annotated from this table alone.

    THEOREMS:
        T1  Binding by header name survives the trailing columns the run has
            gained over time, where positional indexing would read the wrong
            field.
    """
    path = tree / "validation_timeseries.csv"
    if not path.is_file():
        print(f"[anim] note: no {path.name} - frames carry the step only", file=sys.stderr)
        return {}
    table: dict[int, dict] = {}
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    table[int(float(row["step"]))] = {
                        key: float(value) for key, value in row.items() if key and value
                    }
                except (KeyError, TypeError, ValueError):
                    continue
    except OSError as exc:
        print(f"[anim] note: cannot read {path}: {exc} - frames carry the step only", file=sys.stderr)
        return {}
    return table


def dump_files(tree: Path) -> list[Path]:
    """List the per-step grid dumps of a tree in simulated-time order.

    Parameters:
        tree: the case tree.

    Returns:
        The ``grid.<step>.out`` paths sorted by their integer step.

    Raises:
        FileNotFoundError: the tree holds no per-step dumps.

    AXIOMS:
        A1  The step in the filename is the simulated-time index.

    THEOREMS:
        T1  Integer sorting is monotone in time; a lexicographic sort would put
            step 1000 before step 200.
    """
    found: list[tuple[int, Path]] = []
    for path in tree.glob("grid.*.out"):
        stem = path.name[len("grid.") : -len(".out")]
        if stem.isdigit():
            found.append((int(stem), path))
    if not found:
        raise FileNotFoundError(f"no grid.<step>.out dumps under {tree}")
    return [path for _, path in sorted(found)]


def render_frame(
    step: int,
    verts: list,
    values: np.ndarray,
    surf_z: np.ndarray,
    surf_r: np.ndarray,
    vmin: float,
    vmax: float,
    diag: dict | None,
    out_png: Path,
    xlim: tuple[float, float],
    rlim: tuple[float, float],
    scale: float,
) -> None:
    """Draw one frame: the temperature field with the body outline on top.

    Parameters:
        step: the DSMC step this frame shows (used in the title).
        verts, values: the cell quadrilaterals and their temperatures.
        surf_z, surf_r: the body meridian.
        vmin, vmax: the FIXED colour limits shared by every frame (module A2).
        diag: the timeseries row for this step, or None.
        out_png: destination PNG.
        xlim, rlim: the fixed view window, so the camera does not move.
        scale: radial exaggeration of the meridian so the body reads at this
            aspect ratio.

    Returns:
        None.

    Raises:
        Nothing explicit: the caller treats a missing PNG as a failed frame.

    AXIOMS:
        A1  ``PolyCollection`` paints one flat colour per cell, which is the
            data as stored -- no smoothing kernel is applied.
        A2  The body is a filled polygon closed along the axis, so the wall is
            opaque and cannot be mistaken for gas.

    THEOREMS:
        T1  With vmin/vmax fixed across calls the colour of a given temperature
            is identical on every frame, so motion in the video is motion in the
            solution.
    """
    #  WHY: constrained_layout cannot see the fig.text provenance footer, so it
    #  used to overrun the x-axis label and be clipped at the frame edge
    #  (measured on the first render).  Explicit margins reserve the strip.
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    fig.subplots_adjust(left=0.078, right=0.985, top=0.912, bottom=0.205)
    collection = PolyCollection(
        verts, array=values, cmap="inferno", edgecolors="none", linewidths=0.0
    )
    collection.set_clim(vmin, vmax)
    ax.add_collection(collection)
    ax.fill_between(surf_z, 0.0, surf_r * scale, color="#222222", zorder=3, linewidth=0)
    ax.plot(surf_z, surf_r * scale, color="#88ccff", linewidth=0.8, zorder=4)
    ax.set_xlim(*xlim)
    ax.set_ylim(*rlim)
    ax.set_xlabel("Axial position x (m)")
    ax.set_ylabel("Radial coordinate r (m)")
    title = f"DSMC relaxation: step {step}"
    if diag:
        pieces = []
        if "heatflux_avg_Wm2" in diag:
            pieces.append(f"q_avg = {diag['heatflux_avg_Wm2'] / 1.0e4:.2f} W/cm$^2$")
        if "drag_sum_N" in diag:
            pieces.append(f"drag = {diag['drag_sum_N'] / 1.0e3:.2f} kN")
        if "g_load" in diag:
            pieces.append(f"g = {diag['g_load']:.2f}")
        if pieces:
            title += "   (" + ", ".join(pieces) + ")"
    ax.set_title(title, fontsize=11)
    bar = fig.colorbar(collection, ax=ax, pad=0.015)
    bar.set_label("Gas temperature (K)")
    fig.text(
        0.008,
        0.028,
        "Source: per-step SPARTA grid dumps (compute 3 thermal/grid temp, dumped as f_3) and\n"
        "the HIAD_custom.surf meridian. Cells with zero temperature hold no molecules and are\n"
        "not drawn.",
        fontsize=6.0,
        color="#444444",
        va="bottom",
        linespacing=1.45,
    )
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def build_video(frames: list[Path], out_mp4: Path, ffmpeg: str, fps: int, hold: int) -> None:
    """Encode the frames into an H.264 MP4.

    Parameters:
        frames: the PNG frames in playback order, named ``0001.png`` upward.
        out_mp4: destination MP4.
        ffmpeg: an executable ffmpeg path.
        fps: frames per second.
        hold: extra copies of the final frame, so the last state is readable
            before the loop restarts.

    Returns:
        None.

    Raises:
        SystemExit: the encode fails or writes nothing. A renderer that reports
            success while writing no video is exactly the silent failure this
            project bans.

    AXIOMS:
        A1  The frames are numbered contiguously from 1, which the ``%04d``
            pattern requires.
        A2  ``-pix_fmt yuv420p`` is required for the file to play in a browser
            or on a presentation laptop; the default 4:4:4 profile does not.

    THEOREMS:
        T1  Repeating the last frame ``hold`` times adds ``hold / fps`` seconds of
            still time without changing any pixel of the data frames.
    """
    if hold > 0 and frames:
        source = frames[-1]
        #  WHY: the hold copies must continue the numbering from a FIXED base.
        #  Appending inside the loop made len(frames) grow, so the copies landed
        #  on 0024, 0026, 0028 ... and ffmpeg's %04d pattern stopped at the first
        #  gap -- the encode silently lost every hold frame (measured: 24 frames
        #  instead of 31).
        base = len(frames)
        for extra in range(1, hold + 1):
            target = source.parent / f"{base + extra:04d}.png"
            shutil.copyfile(source, target)
            frames = [*frames, target]
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(frames[0].parent / "%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "20",
        str(out_mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"[anim] ffmpeg failed ({result.returncode}): {result.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    if not out_mp4.is_file() or out_mp4.stat().st_size == 0:
        print(f"[anim] FAILED: ffmpeg reported success but {out_mp4} is missing or empty", file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    """Render the DSMC step animation for one case tree.

    Parameters:
        argv: command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 when the MP4 was written, 2 when the tree has no dumps, no usable
        surface file, or the encode failed.

    Raises:
        SystemExit: propagated from :func:`resolve_ffmpeg` / :func:`build_video`.

    AXIOMS:
        A1  The colour limits are computed once from all frames (99.5th
            percentile of the non-zero temperatures) so a single hot wake cell
            cannot flatten the whole sequence to one colour.
        A2  The view window is fixed from the dumps' own bounding box, so the
            camera never moves between frames.

    THEOREMS:
        T1  A single percentile pass over the pooled frames yields the same
            limits for every frame, satisfying module axiom A2.
    """
    parser = argparse.ArgumentParser(description="Render the DSMC relaxation as an MP4.")
    parser.add_argument("--tree", type=Path, default=DEFAULT_TREE, help="case tree holding grid.<step>.out")
    parser.add_argument("--outdir", type=Path, default=None, help="destination dir (default <tree>/plots)")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help="frames per second")
    parser.add_argument("--hold", type=int, default=HOLD_FRAMES, help="extra copies of the final frame")
    parser.add_argument("--vmax", type=float, default=0.0, help="override the colour maximum (kelvin)")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="radial exaggeration of the meridian (1.0 = true scale)")
    parser.add_argument("--xmax", type=float, default=3.0, help="right edge of the view window (m)")
    parser.add_argument("--ffmpeg", default=None, help="explicit ffmpeg path")
    parser.add_argument("--no-frames", action="store_true", help="delete the PNG frames after encoding")
    parser.add_argument("--max-frames", type=int, default=0, help="use at most this many dumps (0 = all)")
    args = parser.parse_args(argv)

    tree = args.tree if args.tree.is_absolute() else PROJECT_ROOT / args.tree
    if not tree.is_dir():
        print(f"[anim] FAILED: no such tree: {tree}", file=sys.stderr)
        return 2
    outdir = args.outdir or (tree / "plots")
    outdir.mkdir(parents=True, exist_ok=True)
    frame_dir = outdir / FRAME_DIR_NAME
    if frame_dir.exists():
        for stale in frame_dir.glob("*.png"):
            stale.unlink()
    frame_dir.mkdir(parents=True, exist_ok=True)

    try:
        dumps = dump_files(tree)
    except FileNotFoundError as exc:
        print(f"[anim] FAILED: {exc}", file=sys.stderr)
        return 2
    if args.max_frames > 0:
        dumps = dumps[: args.max_frames]

    try:
        surf_z, surf_r = read_surf(tree / "HIAD_custom.surf")
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[anim] FAILED: {exc}", file=sys.stderr)
        return 2

    diags = read_step_times(tree)

    #  WHY: two passes. The first pools the temperatures and the bounding box so
    #  every frame shares one scale and one camera (module axioms A2/A3); the
    #  second draws. A handful of dumps of ~19 000 cells is small enough to read
    #  twice, and re-reading avoids holding every field in memory at once.
    pooled: list[np.ndarray] = []
    x_lo, x_hi, r_lo, r_hi = (np.inf, -np.inf, np.inf, -np.inf)
    rng = np.random.default_rng(0)
    for path in dumps:
        try:
            dump = read_grid_dump(path)
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"[anim] FAILED: {exc}", file=sys.stderr)
            return 2
        x_lo = min(x_lo, float(dump["xlo"].min()))
        x_hi = max(x_hi, float(dump["xhi"].max()))
        r_lo = min(r_lo, float(dump["ylo"].min()))
        r_hi = max(r_hi, float(dump["yhi"].max()))
        live = dump["temp"][dump["temp"] > 0.0]
        if live.size:
            take = min(live.size, 4000)
            pooled.append(live[rng.choice(live.size, size=take, replace=False)])
    if not pooled:
        print("[anim] FAILED: every dump is empty (no cell holds molecules)", file=sys.stderr)
        return 2
    stacked = np.concatenate(pooled)
    vmax = args.vmax if args.vmax > 0.0 else float(np.percentile(stacked, 99.5))
    vmin = 0.0
    if not np.isfinite(vmax) or vmax <= vmin:
        print("[anim] FAILED: degenerate colour range", file=sys.stderr)
        return 2
    r_view = max(r_hi, float(surf_r.max()) * args.scale) * 1.02
    xlim = (x_lo - 0.1, max(x_lo + 0.5, min(x_hi, args.xmax)))
    rlim = (0.0, r_view)

    frames: list[Path] = []
    for index, path in enumerate(dumps, start=1):
        dump = read_grid_dump(path)
        verts, values = cell_polygons(dump)
        out_png = frame_dir / f"{index:04d}.png"
        if verts:
            render_frame(
                dump["step"], verts, values, surf_z, surf_r, vmin, vmax,
                diags.get(dump["step"]), out_png, xlim, rlim, args.scale,
            )
        if not out_png.is_file():
            print(f"[anim] FAILED: frame {out_png} was not written", file=sys.stderr)
            return 2
        frames.append(out_png)

    ffmpeg = args.ffmpeg or resolve_ffmpeg()
    out_mp4 = outdir / MP4_NAME
    build_video(frames, out_mp4, ffmpeg, max(1, args.fps), max(0, args.hold))

    print(f"[anim] tree: {tree}")
    print(f"[anim] frames: {len(frames)} (steps {dumps[0].stem} .. {dumps[-1].stem})")
    print(f"[anim] colour range: 0 .. {vmax:.1f} K (99.5th percentile of all frames, fixed)")
    print(f"[anim] wrote {out_mp4} ({out_mp4.stat().st_size} B)")

    if args.no_frames:
        for frame in frame_dir.glob("*.png"):
            frame.unlink()
        frame_dir.rmdir()
        print(f"[anim] removed {frame_dir} (--no-frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
