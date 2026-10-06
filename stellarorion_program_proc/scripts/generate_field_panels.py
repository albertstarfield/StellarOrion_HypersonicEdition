#!/usr/bin/env python3
"""Integrated PNG field-panel generator for the StellarOrion thesis figures.

AXIOMS
  A1  A figure is only reproducible if its source, its data source and its
      typography contract are all in this repository.
  A2  Text printed inside a figure must be legible at the size the thesis
      actually prints it, i.e. >= 8 pt once the panel is placed at
      0.75\\textwidth.
  A3  A panel whose input data does not exist must say so on the figure and
      on stderr; it must never render a plausible-looking substitute.

THEORIES
  T1  The eight chapter-4 field panels were previously shipped as PNGs with
      no generator in the tree (per-name search over src/ and scripts/ found
      only <img> loaders in src/ui/uiassets/index.html).  This module is
      that generator.
  T2  SPARTA grid dumps are the only per-cell 2-D field artefact.  Their
      column order follows the dump command in in.hiad, which declares
      `id xlo ylo xhi yhi f_2[*] f_3[*] f_4[*]` where fix 2 = ave/grid of
      `compute 2 ... n u v w`, fix 3 = ave/grid of `compute 3 thermal/grid
      ... temp`, fix 4 = ave/grid of `compute 4 ... nrho`.  Therefore a row
      has 11 tokens and parts[5]=n, [6]=u, [7]=v, [8]=w, [9]=T, [10]=nrho.
  T3  `fix ... ave/grid all 1 1 1` is an instantaneous average, so cells
      holding a handful of particles yield wildly noisy thermal values
      (measured: T up to 96184 K) and empty cells yield exactly 0.  Any
      colour norm, min/max or log scale MUST therefore be computed over
      masked cells only.
  T4  Typography: the figure is placed at 0.75\\textwidth = 4.1475 in when
      \\textwidth = 5.53 in.  Rendering the figure at that display width
      with explicit point sizes >= 8 pt makes the printed size equal to the
      authored size (scale 1.0), which satisfies A2 by construction.
  T5  The PINN was never trained (finding F24: dde.data.PDE rejects the
      NumPy array passed as a geometry), so PINNAccelerator.predict_full_state
      raises RuntimeError.  The PINN leg is therefore rendered from its real
      surface artefact surf_pinn_300000000.vtu and labelled as such.

APPLICATIONS
  generate_field_panels.py --list-steps
  generate_field_panels.py --tree validation --steps 0,500,1000,300000000
  generate_field_panels.py --tree all

CITATIONS
  [Citation: SPARTA user manual, s2.4 -- dump grid/surf command syntax]
  [Citation: results/validation/in.hiad:44-51 -- compute/fix declarations]
  [Citation: results/validation/in.hiad:58-59 -- dump declarations]
  [Reference: NASA SP-7468 (1976) -- U.S. Standard Atmosphere]
  [Based on: Bird (1994), Molecular Gas Dynamics, Sec. 1.5 -- mean free path]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys

import numpy as np

# --- physical constants (SI, CODATA / NASA SP-7468) -------------------------
K_B = 1.380649e-23          # Boltzmann [J/K]
GAMMA_AIR = 1.4             # ratio of specific heats for diatomic air
R_SPECIFIC_AIR = 8.314462618 / 0.0289647  # J/(kg K)
L_CHAR = 1.0                # reference length [m] for the Knudsen number
T_FLOOR = 50.0              # K -- below this a cell carries no particles
T_CEIL = 6000.0             # K -- above this the instantaneous average is noise
MIN_PARTICLES = 10          # -- cells with fewer are masked for colour panels

DISPLAY_WIDTH_IN = 4.1475   # 0.75 * 5.53 in, per A4 thesis \textwidth
FONT_PT = 9.0               # axis / colourbar text
TITLE_PT = 10.0             # panel titles
DPI = 300

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "results")
OUTDIR = os.path.join(REPO, "src", "ui", "uiassets", "assets", "plots")

GRID_RE = re.compile(r"^grid\.(\d+)\.out$")

#  Ada/SPARK FFI -- the single source of truth for every physics number used in
#  the field panels. sys.path is extended once, at import time, so the
#  radiative-equilibrium temperature below comes from Radiative_Eq_Temp_C and
#  NOT from a Python copy of sigma_SB.
sys.path.insert(0, os.path.join(REPO, "src", "python"))
from ada_pinn_wrapper import radiative_eq_temp  # path set just above


def _radiative_eq_temp_array(heat: np.ndarray, emissivity: float) -> np.ndarray:
    """Radiative-equilibrium temperature [K] for an array of heat fluxes.

    Single source of truth: Ada/SPARK StellarOrion_Physics.Radiative_Eq_Temp via
    ada_pinn_wrapper.radiative_eq_temp (Radiative_Eq_Temp_C). Python MUST NOT
    re-derive eps*sigma*T^4 -- a second copy of sigma silently diverges from the
    verified model (one truth, one value).

    Args:
        heat: per-point heat flux [W/m^2] (1-D).
        emissivity: surface emissivity in (0, 1].

    Returns:
        Surface temperature [K], same shape as ``heat``. Non-positive entries
        are left at 0.0 and filtered by the caller.

    Raises:
        RuntimeError -- propagated from radiative_eq_temp when the Ada handle is
            unavailable or Radiative_Eq_Temp_C fails; the failing flux is named
            by the wrapper.
    """
    t = np.zeros_like(heat, dtype=float)
    for idx in np.nonzero(heat > 0.0)[0]:
        t[idx] = radiative_eq_temp(float(heat[idx]), emissivity)
    return t


def log(msg: str) -> None:
    """Write a progress line to stdout (no flush surprises on long runs).

    Parameters
    ----------
    msg : str
        The message to print.

    Returns
    -------
    None

    Raises
    ------
    None -- printing failures propagate from the underlying stream.
    """
    print(msg, flush=True)


def warn(msg: str) -> None:
    """Write a diagnostic line to stderr.

    Parameters
    ----------
    msg : str
        The message to print.

    Returns
    -------
    None

    Raises
    ------
    None
    """
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------
def load_grid_dump(path: str) -> dict[str, np.ndarray] | None:
    """Parse one SPARTA grid.*.out dump into named per-cell arrays.

    Column order is taken from the dump command in in.hiad (T2):
    `id xlo ylo xhi yhi f_2[*] f_3[*] f_4[*]` with f_2 = (n,u,v,w),
    f_3 = (T), f_4 = (nrho), giving 11 whitespace tokens per data row.

    Parameters
    ----------
    path : str
        Absolute path to a grid dump file.

    Returns
    -------
    dict[str, np.ndarray] | None
        Keys: xlo, ylo, xhi, yhi, n, u, v, w, temp, nrho.  Returns None when
        the file contains no parseable CELLS block.

    Raises
    ------
    OSError -- if the file cannot be opened (handled by the caller).
    """
    rows: list[list[float]] = []
    in_cells = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("ITEM:"):
                    in_cells = "ITEM: CELLS" in line
                    continue
                if not in_cells:
                    continue
                parts = line.split()
                if len(parts) != 11:
                    # 11 tokens is the contract from in.hiad:59; anything else
                    # is a header line, a comment, or a malformed row.
                    continue
                try:
                    rows.append([float(x) for x in parts])
                except ValueError:
                    continue
    except OSError as exc:
        warn(f"[field] cannot read {path}: {exc}")
        return None
    if not rows:
        warn(f"[field] {path}: no 11-token CELLS rows found")
        return None
    a = np.asarray(rows, dtype=float)
    return {
        "xlo": a[:, 1], "ylo": a[:, 2], "xhi": a[:, 3], "yhi": a[:, 4],
        "n": a[:, 5], "u": a[:, 6], "v": a[:, 7], "w": a[:, 8],
        "temp": a[:, 9], "nrho": a[:, 10],
    }


def list_grid_steps(tree: str) -> list[int]:
    """Return the numeric steps available as grid dumps for one results tree.

    Parameters
    ----------
    tree : str
        Name of a directory under results/ (e.g. "validation").

    Returns
    -------
    list[int]
        Ascending step numbers.  Empty when the tree has no grid dumps.

    Raises
    ------
    None -- a missing directory yields [] rather than an exception.
    """
    d = os.path.join(RESULTS, tree)
    if not os.path.isdir(d):
        return []
    out: list[int] = []
    for name in os.listdir(d):
        m = GRID_RE.match(name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def list_trees() -> list[str]:
    """Return every results/ subdirectory that exists.

    Returns
    -------
    list[str]
        Sorted directory basenames under results/.

    Raises
    ------
    None
    """
    if not os.path.isdir(RESULTS):
        return []
    return sorted(
        e for e in os.listdir(RESULTS)
        if os.path.isdir(os.path.join(RESULTS, e))
    )


# ---------------------------------------------------------------------------
# derived quantities
# ---------------------------------------------------------------------------
def speed_of_sound(temp: np.ndarray) -> np.ndarray:
    """Ideal-gas speed of sound a = sqrt(gamma R T), safe against T <= 0.

    Parameters
    ----------
    temp : np.ndarray
        Temperature [K]; non-positive entries yield NaN rather than a crash.

    Returns
    -------
    np.ndarray
        Speed of sound [m/s] with NaN where T <= 0.

    Raises
    ------
    None -- arithmetic only; invalid input is reported as NaN.
    """
    t = np.asarray(temp, dtype=float)
    out = np.full(t.shape, np.nan, dtype=float)
    ok = t > 0.0
    out[ok] = np.sqrt(GAMMA_AIR * R_SPECIFIC_AIR * t[ok])
    return out


def mach_number(u: np.ndarray, v: np.ndarray, temp: np.ndarray) -> np.ndarray:
    """Mach number M = |V| / a for a 2-D cell.

    Parameters
    ----------
    u, v : np.ndarray
        Velocity components [m/s].
    temp : np.ndarray
        Temperature [K].

    Returns
    -------
    np.ndarray
        Mach number, NaN where a is undefined.

    Raises
    ------
    None
    """
    vel = np.hypot(u, v)
    a = speed_of_sound(temp)
    out = np.full(vel.shape, np.nan, dtype=float)
    ok = np.isfinite(a) & (a > 0.0)
    out[ok] = vel[ok] / a[ok]
    return out


def static_pressure(nrho: np.ndarray, temp: np.ndarray) -> np.ndarray:
    """Static pressure p = nrho * k_B * T (ideal gas, number density form).

    Parameters
    ----------
    nrho : np.ndarray
        Number density [m^-3].
    temp : np.ndarray
        Temperature [K].

    Returns
    -------
    np.ndarray
        Pressure [Pa]; zero wherever either factor is non-positive.

    Raises
    ------
    None
    """
    p = np.asarray(nrho, dtype=float) * K_B * np.asarray(temp, dtype=float)
    return np.where(p > 0.0, p, 0.0)


def knudsen_number(nrho: np.ndarray, temp: np.ndarray) -> np.ndarray:
    """Knudsen number Kn = lambda / L_CHAR with lambda ~ T / (sqrt(2) pi d^2 p).

    Substituting p = nrho k_B T makes lambda depend only on number density,
    which is why the panel can be built from nrho alone (T cancels).

    Parameters
    ----------
    nrho : np.ndarray
        Number density [m^-3].
    temp : np.ndarray
        Temperature [K]; retained for the interface and for sanity checks.

    Returns
    -------
    np.ndarray
        Dimensionless Knudsen number; NaN where nrho <= 0.

    Raises
    ------
    None
    """
    n = np.asarray(nrho, dtype=float)
    t = np.asarray(temp, dtype=float)
    d_air = 3.7e-10  # effective molecular diameter [m] -- Bird (1994) Tab. 1.3
    out = np.full(n.shape, np.nan, dtype=float)
    ok = (n > 0.0) & (t > 0.0)
    # lambda = k_B T / (sqrt(2) pi d^2 p), p = n k_B T  =>  lambda = 1/(sqrt(2) pi d^2 n)
    lam = np.zeros_like(n)
    lam[ok] = 1.0 / (math.sqrt(2.0) * math.pi * (d_air ** 2) * n[ok])
    out[ok] = lam[ok] / L_CHAR
    return out


def cell_mask(d: dict[str, np.ndarray], min_particles: int = MIN_PARTICLES
              ) -> np.ndarray:
    """Boolean mask of cells considered statistically meaningful.

    Parameters
    ----------
    d : dict[str, np.ndarray]
        Parsed grid dump.
    min_particles : int, optional
        Minimum DSMC particle count for a cell to be coloured.

    Returns
    -------
    np.ndarray
        True where the cell may contribute to a colour scale.

    Raises
    ------
    KeyError -- if "n" or "temp" is absent from d.
    """
    n = d["n"]
    t = d["temp"]
    return (n >= min_particles) & (t > T_FLOOR) & (t < T_CEIL)


# ---------------------------------------------------------------------------
# figure plumbing
# ---------------------------------------------------------------------------
def _pyplot():
    """Import matplotlib with a non-interactive backend.

    Returns
    -------
    module
        The pyplot module.

    Raises
    ------
    ImportError -- if matplotlib is absent from the active environment.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _apply_typography(fig) -> None:
    """Force every text artist on fig to at least FONT_PT / TITLE_PT points.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure whose artists are to be normalised.

    Returns
    -------
    None

    Raises
    ------
    None
    """
    for ax in fig.axes:
        for artist in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            artist.set_fontsize(FONT_PT)
        if ax.get_xlabel():
            ax.xaxis.label.set_fontsize(FONT_PT)
        if ax.get_ylabel():
            ax.yaxis.label.set_fontsize(FONT_PT)
        if ax.get_title():
            ax.title.set_fontsize(TITLE_PT)
        if ax.get_legend() is not None:
            for txt in ax.get_legend().get_texts():
                txt.set_fontsize(FONT_PT)
        if hasattr(ax, "get_images") and ax.get_images():
            cbar = ax.images[0].colorbar
            if cbar is not None:
                cbar.ax.tick_params(labelsize=FONT_PT)
                if cbar.ax.get_ylabel():
                    cbar.ax.yaxis.label.set_fontsize(FONT_PT)


def _save(fig, name: str, step: int, outdir: str) -> str:
    """Apply the typography contract and write the PNG.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to render.
    name : str
        Base panel name, e.g. "thermal_map_smooth".
    step : int
        Step label appended to the file name.
    outdir : str
        Destination directory.

    Returns
    -------
    str
        Path of the file written.

    Raises
    ------
    OSError -- if the directory cannot be created or the file written.
    """
    _apply_typography(fig)
    fig.set_size_inches(DISPLAY_WIDTH_IN, DISPLAY_WIDTH_IN * 0.6, forward=True)
    os.makedirs(outdir, exist_ok=True)
    suffix = f"_pinn_{step}" if step >= 100_000_000 else f"_step_{step}"
    path = os.path.join(outdir, f"{name}{suffix}.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    return path


def _imshow_panel(ax, d, values, title, cbar_label, cmap="viridis",
                  log_scale=False, mask=None):
    """Draw one scalar field as a cell-centred image over the 2-D grid.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Target axes.
    d : dict[str, np.ndarray]
        Parsed grid dump (supplies the cell rectangles).
    values : np.ndarray
        Per-cell scalar to colour.
    title : str
        Panel title.
    cbar_label : str
        Colourbar label.
    cmap : str, optional
        Matplotlib colormap name.
    log_scale : bool, optional
        Use a log norm; ignored where the masked data has no positive span.
    mask : np.ndarray | None, optional
        Cells to include when computing the colour range.

    Returns
    -------
    None

    Raises
    ------
    ValueError -- if values and the grid arrays disagree in length.
    """
    from matplotlib.colors import LogNorm
    if values.shape != d["xlo"].shape:
        raise ValueError("values/grid length mismatch")

    use = mask if mask is not None else np.ones(values.shape, dtype=bool)
    finite = use & np.isfinite(values)
    # Colour limits come ONLY from masked cells (T3) -- never from the
    # empty-cell zeros or the instantaneous-average spikes.
    good = values[finite]
    if good.size == 0:
        ax.text(0.5, 0.5, "no valid cells\n(particle mask filtered all)",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=FONT_PT, color="crimson")
        ax.set_title(title, fontsize=TITLE_PT)
        return
    vmin, vmax = float(np.min(good)), float(np.max(good))
    norm = None
    if log_scale and vmin > 0.0:
        norm = LogNorm(vmin=vmin, vmax=max(vmax, vmin * 1.0001))

    # Draw each cell as its rectangle; 19321 cells is small enough for this.
    from matplotlib.collections import PolyCollection
    verts = np.stack([
        np.stack([d["xlo"], d["ylo"]], axis=1),
        np.stack([d["xhi"], d["ylo"]], axis=1),
        np.stack([d["xhi"], d["yhi"]], axis=1),
        np.stack([d["xlo"], d["yhi"]], axis=1),
    ], axis=1)
    colors = np.where(finite, values, np.nan)
    pc = PolyCollection(verts, array=colors, cmap=cmap, norm=norm,
                        edgecolors="none")
    pc.set_array(colors)
    ax.add_collection(pc)
    ax.autoscale_view()
    ax.set_xlim(d["xlo"].min(), d["xhi"].max())
    ax.set_ylim(d["ylo"].min(), d["yhi"].max())
    ax.set_aspect("equal")
    ax.set_xlabel("axial  x [m]", fontsize=FONT_PT)
    ax.set_ylabel("radial  y [m]", fontsize=FONT_PT)
    ax.set_title(title, fontsize=TITLE_PT, pad=20)
    cb = ax.figure.colorbar(pc, ax=ax, pad=0.02)
    cb.set_label(cbar_label, fontsize=FONT_PT)
    cb.ax.tick_params(labelsize=FONT_PT)


def _stats_note(ax, d: dict[str, np.ndarray], mask: np.ndarray,
                step: int) -> None:
    """Place per-cell statistics as a subtitle ABOVE the axes.

    Two earlier placements were wrong and are recorded so they are not
    repeated: (1) appending the counts to the title made it long enough to
    run under the colourbar and the two overlapped; (2) an in-axes text box
    was large enough to hide the bow-shock structure it described.  A
    subtitle sits in the page margin, so it occludes neither.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Target axes.
    d : dict[str, np.ndarray]
        Parsed grid dump (supplies cell counts).
    mask : np.ndarray
        Cells that passed the particle/temperature filter.
    step : int
        Step to report.

    Returns
    -------
    None

    Raises
    ------
    None
    """
    note = (f"step {step}  |  {d['xlo'].size} cells  |  "
            f"{int(mask.sum())} above n>={MIN_PARTICLES}")
    ax.text(0.5, 1.005, note, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=FONT_PT - 1.0, color="0.30")


def _nan_banner(ax, text: str) -> None:
    """Stamp an explicit 'data missing' message on an empty panel (A3).

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to annotate.
    text : str
        Message to show.

    Returns
    -------
    None

    Raises
    ------
    None
    """
    ax.text(0.5, 0.5, text, ha="center", va="center",
            transform=ax.transAxes, fontsize=FONT_PT, color="crimson",
            wrap=True)
    ax.set_xticks([])
    ax.set_yticks([])


# ---------------------------------------------------------------------------
# the eight panels
# ---------------------------------------------------------------------------
def render_grid_panels(step: int, d: dict[str, np.ndarray], outdir: str
                       ) -> list[str]:
    """Render the six grid-derived panels for one DSMC step.

    Parameters
    ----------
    step : int
        DSMC step represented by the dump.
    d : dict[str, np.ndarray]
        Parsed grid dump.
    outdir : str
        Destination directory.

    Returns
    -------
    list[str]
        Paths of the PNG files written.

    Raises
    ------
    OSError -- propagated from figure writing.
    ValueError -- if the dump lacks a required field.
    """
    plt = _pyplot()
    written: list[str] = []
    mask = cell_mask(d)
    press = static_pressure(d["nrho"], d["temp"])
    mach = mach_number(d["u"], d["v"], d["temp"])
    kn = knudsen_number(d["nrho"], d["temp"])
    # Titles stay short so they cannot reach under the colourbar; the
    # per-cell counts move inside the axes via _stats_note (A2/legibility).
    short = f"step {step}"

    # 1 -- thermal map -------------------------------------------------------
    fig, ax = plt.subplots()
    _imshow_panel(ax, d, d["temp"], f"Thermal map -- {short}",
                  "temperature [K]", cmap="inferno", mask=mask)
    _stats_note(ax, d, mask, step)
    written.append(_save(fig, "thermal_map_smooth", step, outdir))
    plt.close(fig)

    # 2 -- pressure map ------------------------------------------------------
    fig, ax = plt.subplots()
    _imshow_panel(ax, d, press, f"Pressure map -- {short}",
                  "static pressure [Pa]", cmap="magma", log_scale=True,
                  mask=mask)
    _stats_note(ax, d, mask, step)
    written.append(_save(fig, "pressure_map_smooth", step, outdir))
    plt.close(fig)

    # 3 -- Mach map ----------------------------------------------------------
    fig, ax = plt.subplots()
    _imshow_panel(ax, d, mach, f"Mach number -- {short}",
                  "Mach [-]", cmap="plasma", mask=mask)
    _stats_note(ax, d, mask, step)
    written.append(_save(fig, "mach_map_smooth_M0_A0", step, outdir))
    plt.close(fig)

    # 4 -- Knudsen map -------------------------------------------------------
    fig, ax = plt.subplots()
    _imshow_panel(ax, d, kn, f"Knudsen number -- {short}",
                  r"Kn = $\lambda/L$ [-]", cmap="cividis", log_scale=True,
                  mask=mask)
    _stats_note(ax, d, mask, step)
    written.append(_save(fig, "knudsen_map_smooth_M0_A0", step, outdir))
    plt.close(fig)

    # 5 -- velocity vectors --------------------------------------------------
    fig, ax = plt.subplots()
    if int(mask.sum()) >= 4:
        stride = max(1, math.ceil(mask.sum() / 700.0))
        sel = np.where(mask)[0][::stride]
        cx = (d["xlo"][sel] + d["xhi"][sel]) / 2.0
        cy = (d["ylo"][sel] + d["yhi"][sel]) / 2.0
        ax.quiver(cx, cy, d["u"][sel], d["v"][sel], d["temp"][sel],
                  cmap="inferno", scale=None, width=0.0035)
        ax.set_xlim(d["xlo"].min(), d["xhi"].max())
        ax.set_ylim(d["ylo"].min(), d["yhi"].max())
        ax.set_aspect("equal")
        ax.set_xlabel("axial  x [m]", fontsize=FONT_PT)
        ax.set_ylabel("radial  y [m]", fontsize=FONT_PT)
        ax.set_title(f"Velocity vectors -- {short}", fontsize=TITLE_PT, pad=20)
        _stats_note(ax, d, mask, step)
    else:
        _nan_banner(ax, "velocity vectors unavailable:\n"
                        f"only {int(mask.sum())} cells reach n>={MIN_PARTICLES}")
        ax.set_title(f"Velocity vectors -- {short}", fontsize=TITLE_PT, pad=20)
    written.append(_save(fig, "velocity_vectors_smooth", step, outdir))
    plt.close(fig)

    # 6 -- grid mesh ---------------------------------------------------------
    fig, ax = plt.subplots()
    verts = np.stack([
        np.stack([d["xlo"], d["ylo"]], axis=1),
        np.stack([d["xhi"], d["ylo"]], axis=1),
        np.stack([d["xhi"], d["yhi"]], axis=1),
        np.stack([d["xlo"], d["yhi"]], axis=1),
    ], axis=1)
    from matplotlib.collections import PolyCollection
    pc = PolyCollection(verts, facecolors="none", edgecolors="0.25",
                        linewidths=0.15)
    ax.add_collection(pc)
    ax.set_xlim(d["xlo"].min(), d["xhi"].max())
    ax.set_ylim(d["ylo"].min(), d["yhi"].max())
    ax.set_aspect("equal")
    ax.set_xlabel("axial  x [m]", fontsize=FONT_PT)
    ax.set_ylabel("radial  y [m]", fontsize=FONT_PT)
    ax.set_title(f"Computational mesh -- {short}", fontsize=TITLE_PT, pad=20)
    _stats_note(ax, d, mask, step)
    written.append(_save(fig, "grid_mesh_map_smooth", step, outdir))
    plt.close(fig)

    # 7 -- mesh statistics ---------------------------------------------------
    fig, ax = plt.subplots()
    positive = d["n"][d["n"] > 0]
    if positive.size:
        ax.hist(positive, bins=min(60, max(10, int(positive.max()))),
                color="steelblue", edgecolor="white", linewidth=0.3)
        ax.set_xlabel("DSMC particles per cell", fontsize=FONT_PT)
        ax.set_ylabel("cell count", fontsize=FONT_PT)
        ax.set_title(
            f"Mesh statistics -- {short};  "
            f"median n={float(np.median(d['n'])):.0f}, "
            f"max n={float(d['n'].max()):.0f}",
            fontsize=TITLE_PT)
    else:
        _nan_banner(ax, "mesh statistics unavailable: every cell is empty")
        ax.set_title(f"Mesh statistics -- {short}", fontsize=TITLE_PT)
    written.append(_save(fig, "mesh_statistics_smooth", step, outdir))
    plt.close(fig)

    return written


def render_scallop_pocket(step: int, tree: str, outdir: str) -> str | None:
    """Render the scalloped-pocket temperature panel from a surface VTU.

    Parameters
    ----------
    step : int
        Step label to stamp on the file name.
    tree : str
        results/ subtree holding paraview/surf_*.vtu files.
    outdir : str
        Destination directory.

    Returns
    -------
    str | None
        Path written, or None when no surface artefact exists (A3: the panel
        then reports the gap instead of inventing values).

    Raises
    ------
    OSError -- propagated from figure writing.
    """
    vtudir = os.path.join(RESULTS, tree, "paraview")
    if not os.path.isdir(vtudir):
        warn(f"[field] {tree}: no paraview/ directory -- "
             "scallop pocket panel cannot be rendered")
        return None
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    try:
        from make_vtu_visualization import _parse_vtu
    except Exception as exc:            # noqa: BLE001 -- optional dep; logged, panel reports the gap
        warn(f"[field] cannot import _parse_vtu: {exc}")
        return None

    # prefer this exact step, else the highest available surface dump
    want = os.path.join(vtudir, f"surf_{step}.vtu")
    if not os.path.isfile(want):
        cands = sorted(
            (f for f in os.listdir(vtudir) if re.match(r"^surf_\d+\.vtu$", f)),
            key=lambda f: int(re.search(r"\d+", f).group()),
        )
        if not cands:
            warn(f"[field] {tree}: no surf_*.vtu in {vtudir}")
            return None
        want = os.path.join(vtudir, cands[-1])
        warn(f"[field] {tree}: step {step} has no surface dump; "
             f"falling back to {os.path.basename(want)}")

    try:
        pts, heat = _parse_vtu(want)
    except Exception as exc:            # noqa: BLE001 -- corrupt VTU must not abort the batch; logged
        warn(f"[field] failed to parse {want}: {exc}")
        return None
    heat = np.asarray(heat, dtype=float)
    #  ONE TRUTH, ONE VALUE (2026-10-06): the surface temperature is the Ada/SPARK
    #  radiative-equilibrium value (Radiative_Eq_Temp_C); Python carries no copy
    #  of sigma and does not re-derive eps*sigma*T^4.
    t = _radiative_eq_temp_array(heat, 0.90)
    ok = np.isfinite(t) & (t > 0.0)
    if not ok.any():
        warn(f"[field] {want}: no positive heat flux -- panel reports the gap")
        return None

    plt = _pyplot()
    fig, ax = plt.subplots()
    sc = ax.scatter(pts[ok, 0], pts[ok, 1], c=t[ok], s=6, cmap="inferno",
                    edgecolors="none")
    ax.set_xlabel("axial  x [m]", fontsize=FONT_PT)
    ax.set_ylabel("radial  y [m]", fontsize=FONT_PT)
    ax.set_title(
        f"Scallop pocket temperature -- {os.path.basename(want)}  "
        f"(T_max={float(t[ok].max()):.0f} K)",
        fontsize=TITLE_PT)
    ax.set_aspect("equal")
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("radiative-equilibrium T [K]", fontsize=FONT_PT)
    cb.ax.tick_params(labelsize=FONT_PT)
    path = _save(fig, "scallop_pocket_temp_smooth_M0_A0", step, outdir)
    plt.close(fig)
    return path


def render_pinn_surface(outdir: str, tree: str = "validation_scalloped"
                        ) -> str | None:
    """Render the PINN leg (pseudo-step 300000000) from its real artefact.

    T5 applies: the network was never trained, so no field prediction is
    possible.  This renders the shipped surface heat-flux artefact and says
    so in the title rather than presenting a substitute as a prediction.

    Parameters
    ----------
    outdir : str
        Destination directory.
    tree : str, optional
        results/ subtree expected to hold surf_pinn_300000000.vtu.

    Returns
    -------
    str | None
        Path written, or None when the artefact is absent.

    Raises
    ------
    OSError -- propagated from figure writing.
    """
    target = os.path.join(RESULTS, tree, "paraview", "surf_pinn_300000000.vtu")
    if not os.path.isfile(target):
        warn(f"[field] PINN artefact missing: {target}")
        return None
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    try:
        from make_vtu_visualization import _parse_vtu
        pts, heat = _parse_vtu(target)
    except Exception as exc:            # noqa: BLE001 -- logged; PINN leg reported missing, not invented
        warn(f"[field] PINN artefact unreadable: {exc}")
        return None
    heat = np.asarray(heat, dtype=float)
    #  ONE TRUTH, ONE VALUE (2026-10-06): the surface temperature is the Ada/SPARK
    #  radiative-equilibrium value (Radiative_Eq_Temp_C); Python carries no copy
    #  of sigma and does not re-derive eps*sigma*T^4.
    t = _radiative_eq_temp_array(heat, 0.90)
    ok = np.isfinite(t) & (t > 0.0)
    if not ok.any():
        return None

    plt = _pyplot()
    fig, ax = plt.subplots()
    sc = ax.scatter(pts[ok, 0], pts[ok, 1], c=t[ok], s=6, cmap="inferno",
                    edgecolors="none")
    ax.set_xlabel("axial  x [m]", fontsize=FONT_PT)
    ax.set_ylabel("radial  y [m]", fontsize=FONT_PT)
    ax.set_title(
        "PINN surrogate surface -- pseudo-step 300000000\n"
        f"from {os.path.basename(target)} (surface heat flux; "
        "network untrained, no interior field)",
        fontsize=TITLE_PT)
    ax.set_aspect("equal")
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("radiative-equilibrium T [K]", fontsize=FONT_PT)
    cb.ax.tick_params(labelsize=FONT_PT)
    path = _save(fig, "scallop_pocket_temp_smooth_M0_A0", 300_000_000, outdir)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI driver: list or render every available field panel.

    Parameters
    ----------
    argv : list[str] | None, optional
        Argument vector; defaults to sys.argv[1:].

    Returns
    -------
    int
        0 when every requested panel was written, 1 when any panel is
        missing (A3: a gap is never reported as success), 2 on usage error.

    Raises
    ------
    None -- all internal failures are converted into the return code.
    """
    ap = argparse.ArgumentParser(
        description="Render the thesis field panels from SPARTA grid dumps, "
                    "surface VTUs and the PINN surface artefact.")
    ap.add_argument("--list-steps", action="store_true",
                    help="print available trees and step numbers, then exit")
    ap.add_argument("--tree", default="all",
                    help="results/ subtree to render (default: all)")
    ap.add_argument("--steps", default="all",
                    help="comma-separated steps, or 'all' (default)")
    ap.add_argument("--outdir", default=OUTDIR,
                    help=f"output directory (default: {OUTDIR})")
    ap.add_argument("--with-pinn", action="store_true", default=True,
                    help="also render the 300000000 pseudo-step (default)")
    ap.add_argument("--no-pinn", dest="with_pinn", action="store_false",
                    help="skip the PINN pseudo-step")
    args = ap.parse_args(argv)

    trees = list_trees() if args.tree == "all" else [args.tree]

    if args.list_steps:
        for t in trees:
            steps = list_grid_steps(t)
            print(f"{t}: grid steps = {steps if steps else 'NONE'}")
        print(f"display width = {DISPLAY_WIDTH_IN} in, font = {FONT_PT} pt "
              f"(title {TITLE_PT} pt), dpi = {DPI}")
        return 0

    if args.steps == "all":
        wanted: dict[str, list[int]] = {t: list_grid_steps(t) for t in trees}
    else:
        try:
            sel = [int(s) for s in args.steps.split(",") if s.strip()]
        except ValueError:
            ap.error("--steps must be integers or 'all'")
            return 2
        wanted = {t: sel for t in trees}

    written: list[str] = []
    failed: list[str] = []
    for tree in trees:
        steps = wanted[tree]
        if not steps:
            warn(f"[field] {tree}: NO grid dumps -- field panels unavailable. "
                 "The SPARTA deck must emit "
                 "`dump N grid all 100 <dir>/grid.*.out "
                 "id xlo ylo xhi yhi f_2[*] f_3[*] f_4[*]`.")
            failed.append(f"{tree}: no grid dumps")
            continue
        for step in steps:
            path = os.path.join(RESULTS, tree, f"grid.{step}.out")
            d = load_grid_dump(path)
            if d is None:
                failed.append(f"{path}: unparseable")
                continue
            try:
                written += render_grid_panels(step, d, args.outdir)
            except Exception as exc:    # noqa: BLE001 -- one bad dump must not stop other steps; logged
                warn(f"[field] grid panels failed for {path}: {exc!r}")
                failed.append(f"{path}: {exc!r}")
        p = render_scallop_pocket(steps[-1], tree, args.outdir)
        if p:
            written.append(p)
        else:
            failed.append(f"{tree}: scallop pocket panel")

    if args.with_pinn:
        p = render_pinn_surface(args.outdir)
        if p:
            written.append(p)
        else:
            failed.append("PINN pseudo-step 300000000")

    for path in written:
        log(f"[field] wrote {os.path.relpath(path, REPO)}")
    if failed:
        for item in failed:
            warn(f"[field] MISSING: {item}")
        warn(f"[field] {len(written)} written, {len(failed)} missing")
        return 1
    log(f"[field] {len(written)} panels written, none missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
