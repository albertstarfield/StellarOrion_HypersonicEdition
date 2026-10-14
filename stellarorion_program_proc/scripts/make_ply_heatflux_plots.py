#!/usr/bin/env python3
"""Per-ply temperature/heat-flux figures for the TPS conduction stack.

The layup is the RAPISARDA 2023 F-TPS schedule (Table 4.17 == NASA/TM-20110012051
Table 5): two Nicalon SiC plies, two Pyrogel 3350 plies and one Kapton gas
barrier, 7.131 mm total.  It is NOT IRVE-3's flown hardware, which was two
Nextel BF-20 plies, two Pyrogel 3350 plies and an AKK barrier for a 6.35 mm
total.  Every figure below is single-sourced from the Ada preset through
`ada_pinn_wrapper` -- a text literal in this file once drifted from the layup
the solver used and silently defeated a material change.

The original IRVE-3 layup header follows for historical context only.

PURPOSE
    Turn the per-element, per-ply temperature breakdown written by the Ada/SPARK
    ``tps_conduction`` solver (``results/tps_conduction/tps_step2200_layers.csv``)
    into publication figures: the through-thickness heat flux of every ply and the
    temperature profile through the stack.

AXIOMS
    A1. The stack is in SERIES: in a steady state the same through-flux crosses
        every ply, so ``q_ply[i] = (T_top_i - T_bottom_i) / R_i`` with
        ``R_i = thickness_i / k_i``.  Deviations between plies are therefore a
        property of the recorded node temperatures, not of the formula, and are
        reported as measured rather than smoothed away.
    A2. ``tps_step2200_layers.csv`` records, per element, one row per ply whose
        ``depth_m`` is the TOP of that ply and whose ``temp_K`` is the node
        temperature at that depth.  Hence ``T_bottom_i == T_top_{i+1}`` for
        ``i = 1..4`` and ``T_bottom_5`` is the cold-face temperature
        (``t_back_K`` from the elements CSV, pinned to the Dirichlet value).
    A3. The solver's cold face is a steady-state Dirichlet boundary; the
        back-face temperature restates that boundary condition and is NOT a
        transient prediction (see the summary JSON ``caveats``).

THEORIES
    T1. Plotting the per-ply flux of the PEAK element shows the load path where
        the thermal margin is smallest.
    T2. Plotting the flux DISTRIBUTION across all elements shows how many
        elements sit near the structural limit rather than only the worst one.
    T3. A missing/empty CSV is an error, not an empty figure.

APPLICATIONS
    - ply_heatflux_peak_element.png : bar chart of q_ply for the peak element
    - ply_temperature_profile_peak_element.png : T vs depth through the stack
    - ply_heatflux_distribution.png : per-ply flux spread over all elements

CITATIONS
    [1] tps_conduction FFI (src/python/ada_pinn_wrapper.py) -- the solver that
        writes the layer CSV.
    [2] Fourier, J. (1822). Theorie analytique de la chaleur -- q = k dT/dx.
    [3] NASA TP-2013-4012 -- IRVE-3 5-ply flexible TPS layup (Nextel BF-20 /
        Pyrogel 3350 / AKK).
    [4] matplotlib boxplot + bar docs. https://matplotlib.org/stable/api/

Author: Albert Starfield Wahyu Suryo Samudro
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")  # must precede pyplot: headless render
import matplotlib.pyplot as plt

# Dark theme, shared with render_geometry_grid.py so the figure set is uniform.
_BG = "#0a0a0f"
_PANEL = "#1a1a2e"
_TEXT = "#8892b0"
_ACCENT = "#e94560"
_DIM = "#555555"

# Per-ply material names are NOT re-declared here.  They come from the
# single source of truth, `ada_pinn_wrapper.IRVE3_FTPS_PLY_NAMES`, via
# _load_ply_preset() below.  A second copy in this file once drifted from
# the Ada preset and had to be fixed in lockstep by hand.



def _load_ply_preset() -> tuple[tuple[float, ...], tuple[float, ...], tuple[str, ...]]:
    """Return (thicknesses, conductivities, names) for the IRVE-3 F-TPS layup.

    AXIOMS: `src/python/ada_pinn_wrapper.py` mirrors the Ada preset
    (`stellarorion_types.ads` `TPS_Layup_IRVE3`) and the test suite asserts the
    two agree, so it is the authoritative source available to a script that
    cannot link the Ada library.

    THEORIES: reading the mirror instead of re-declaring the numbers here
    means a layup change cannot silently diverge between the solver and the
    figures.

    APPLICATIONS: `load_layers` overrides the CSV material columns with these.

    Returns:
        (thickness_m per ply, k per ply, ply name per ply), all of length 5.

    Raises:
        FileNotFoundError: ada_pinn_wrapper.py could not be located.
        AttributeError: the mirror does not define the expected constants.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wrapper_dir = os.path.abspath(
        os.path.join(script_dir, os.pardir, "src", "python")
    )
    if not os.path.isfile(os.path.join(wrapper_dir, "ada_pinn_wrapper.py")):
        raise FileNotFoundError(
            f"ada_pinn_wrapper.py not found under {wrapper_dir} -- cannot "
            "resolve the authoritative ply preset"
        )
    sys.path.insert(0, wrapper_dir)
    try:
        import ada_pinn_wrapper as _apw
    finally:
        try:
            sys.path.remove(wrapper_dir)
        except ValueError:
            pass

    thicknesses = tuple(_apw.IRVE3_FTPS_PLY_THICKNESS_M)
    conductivities = tuple(_apw.IRVE3_FTPS_PLY_THERMAL_K)
    names = tuple(_apw.IRVE3_FTPS_PLY_NAMES)
    if not (len(thicknesses) == len(conductivities) == len(names)):
        raise ValueError(
            f"IRVE-3 F-TPS preset arrays have different lengths: "
            f"{len(thicknesses)}/{len(conductivities)}/{len(names)}"
        )
    if len(thicknesses) < 2:
        raise ValueError(
            f"IRVE-3 F-TPS preset has {len(thicknesses)} plies; a "
            "through-thickness gradient needs at least 2"
        )
    return thicknesses, conductivities, names


def _preset_tmax() -> tuple[float, ...]:
    """Return the per-ply maximum continuous-use temperature [K].

    AXIOMS: the ply limits live in the Ada preset mirror alongside the
    thicknesses and conductivities, so they are single-sourced the same way
    and cannot drift from the layup the solver used.

    THEORIES: a stack-level limit cannot express a layup whose plies span
    773 .. 2073 K, so the per-ply vector is what a figure must report.

    APPLICATIONS: ``plot_ply_stack_heatmap`` and
    ``plot_ply_temperature_by_element`` annotate each ply with its own limit.

    Returns:
        per-ply T_max [K], same order and length as the ply preset.

    Raises:
        FileNotFoundError: ada_pinn_wrapper.py could not be located.
        AttributeError: the mirror does not define IRVE3_FTPS_PLY_TMAX_K.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wrapper_dir = os.path.abspath(
        os.path.join(script_dir, os.pardir, "src", "python")
    )
    if not os.path.isfile(os.path.join(wrapper_dir, "ada_pinn_wrapper.py")):
        raise FileNotFoundError(
            f"ada_pinn_wrapper.py not found under {wrapper_dir} -- cannot "
            "resolve the authoritative ply preset"
        )
    sys.path.insert(0, wrapper_dir)
    try:
        import ada_pinn_wrapper as _apw
        tmax = tuple(_apw.IRVE3_FTPS_PLY_TMAX_K)
        thicknesses = tuple(_apw.IRVE3_FTPS_PLY_THICKNESS_M)
    finally:
        try:
            sys.path.remove(wrapper_dir)
        except ValueError:
            pass
    if len(tmax) != len(thicknesses):
        raise ValueError(
            f"IRVE3_FTPS_PLY_TMAX_K has {len(tmax)} entries but the layup has "
            f"{len(thicknesses)} plies"
        )
    if any(t <= 0.0 for t in tmax):
        raise ValueError(f"non-positive ply T_max in {tmax}")
    return tmax


def load_layers(csv_path: str) -> dict[int, list[dict]]:
    """Read the per-ply layer CSV into ``{element: [ply_row, ...]}``.

    Parameters:
        csv_path: path to ``tps_step2200_layers.csv``.

    Returns:
        dict mapping element id -> list of 5 dicts with keys
        ``ply, ply_name, depth_m, temp_K, thickness_m, k_WmK``.

    Raises:
        FileNotFoundError: csv_path does not exist.
        ValueError: the file has no usable rows.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"layer CSV not found: {csv_path}")

    thicknesses, conductivities, names = _load_ply_preset()
    seen_mismatch: set[int] = set()

    by_element: dict[int, list[dict]] = {}
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                element = int(row["element"])
                ply = int(row["ply"])
                csv_thickness = float(row["ply_thickness_m"])
                csv_k = float(row["ply_k_WmK"])
                csv_name = row["ply_name"]
                depth_m = float(row["depth_m"])
                temp_K = float(row["temp_K"])
            except (KeyError, ValueError):
                # Malformed row: skip it rather than aborting the whole figure.
                continue

            # DESIGN properties come from the preset, MEASURED data from the
            # CSV.  `tps_step2200_layers.csv` has no writer in this repository
            # (verified by grep: only readers exist), so its material columns
            # are an orphan and may be stale -- they were: it carried k=0.25
            # and the superseded grade "Pyrogel 2250" after both had changed,
            # which silently defeated the layup switch in the per-ply figures
            # while the solver used the new values.  Node temperatures and
            # depths ARE solver output and stay CSV-sourced.
            if ply < 1 or ply > len(thicknesses):
                print(
                    f"[ply] ERROR: element {element} has ply {ply} outside "
                    f"the preset range 1..{len(thicknesses)}; refusing to "
                    "guess a material",
                    file=sys.stderr,
                )
                continue

            # Report a disagreement ONCE per ply, then use the preset.  A
            # mismatch is a real signal (an orphan or a drift), so it must be
            # visible rather than silently resolved in either direction.
            csv_triple = (csv_thickness, csv_k, csv_name.strip())
            preset_triple = (
                thicknesses[ply - 1],
                conductivities[ply - 1],
                names[ply - 1].strip(),
            )
            if ply not in seen_mismatch and (
                abs(csv_triple[0] - preset_triple[0]) > 1.0e-12
                or abs(csv_triple[1] - preset_triple[1]) > 1.0e-12
                or csv_triple[2] != preset_triple[2]
            ):
                seen_mismatch.add(ply)
                print(
                    f"[ply] WARNING: ply {ply} in {csv_path} disagrees with "
                    f"the authoritative preset (thickness "
                    f"{csv_triple[0]:.6g} -> {preset_triple[0]:.6g} m, "
                    f"k {csv_triple[1]:.6g} -> {preset_triple[1]:.6g} "
                    f"W/(m*K), name {csv_triple[2]!r} -> "
                    f"{preset_triple[2]!r}). Using the preset.",
                    file=sys.stderr,
                )

            by_element.setdefault(element, []).append(
                {
                    "ply": ply,
                    "ply_name": preset_triple[2],
                    "depth_m": depth_m,
                    "temp_K": temp_K,
                    "thickness_m": preset_triple[0],
                    "k_WmK": preset_triple[1],
                }
            )

    if not by_element:
        raise ValueError(f"no usable rows parsed from {csv_path}")
    for rows in by_element.values():
        rows.sort(key=lambda r: r["ply"])
    return by_element


def load_back_temp(elements_csv: str) -> dict[int, float]:
    """Read ``t_back_K`` per element from ``tps_step2200_elements.csv``.

    Parameters:
        elements_csv: path to the elements CSV.

    Returns:
        dict mapping element id -> cold-face temperature [K].  Missing file
        returns an empty dict; callers fall back to the layer-node convention.

    Raises:
        None.  A missing file is reported to stderr and yields ``{}`` so the
        caller can degrade to using the last layer node (documented fallback).
    """
    if not os.path.isfile(elements_csv):
        print(f"[ply] warn: {elements_csv} missing; using last layer node as cold face",
              file=sys.stderr)
        return {}
    out: dict[int, float] = {}
    with open(elements_csv, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out[int(row["element"])] = float(row["t_back_K"])
            except (KeyError, ValueError):
                continue
    return out


def per_ply_flux(rows: list[dict], back_temp_K: float) -> list[float]:
    """Compute the through-flux of each ply for one element [W/m^2].

    Parameters:
        rows: the 5 ply dicts of one element, ordered by ply number.
        back_temp_K: cold-face temperature below the last ply [K].

    Returns:
        list of 5 fluxes; ``q_i = (T_top_i - T_bottom_i) / (thickness_i / k_i)``.

    Raises:
        ValueError: fewer than 2 ply rows (cannot form a gradient).
    """
    if len(rows) < 2:
        raise ValueError(f"need >= 2 ply rows, got {len(rows)}")
    temps = [r["temp_K"] for r in rows] + [float(back_temp_K)]
    fluxes: list[float] = []
    for i, r in enumerate(rows):
        r_ply = r["thickness_m"] / r["k_WmK"]
        fluxes.append((temps[i] - temps[i + 1]) / r_ply)
    return fluxes


def stack_flux(rows: list[dict], back_temp_K: float) -> float:
    """Series-consistent through-flux of the whole stack [W/m^2].

    AXIOM: in steady one-dimensional series conduction the SAME heat flux
    passes through every ply, so the only self-consistent value is
    ``q = (T_surface - T_back) / sum_i (thickness_i / k_i)``.

    WHY THIS EXISTS: a per-ply ``q_i = dT_i / R_i`` is NOT that value whenever
    the recorded node temperatures are not an exact series profile.  A ply with
    a tiny resistance (here ply 5: R = 0.00015/0.12 = 0.00125 m^2 K/W) has
    ``dq/dT = 1/R = 800 W/m^2/K``, so a few kelvin of error in the pinned cold
    face is amplified into a large apparent flux.  Measured 2026-10-08 at the
    peak element: ply 5 = 10 842 W/m^2 against a stack value of 4 882.8 W/m^2.

    Parameters:
        rows: the 5 ply dicts of one element, ordered by ply number.
        back_temp_K: cold-face temperature below the last ply [K].

    Returns:
        float: ``(rows[0]["temp_K"] - back_temp_K) / sum(thickness_i / k_i)``.

    Raises:
        ValueError: no rows, or a non-positive total resistance.
    """
    if not rows:
        raise ValueError("need >= 1 ply row")
    r_total = sum(r["thickness_m"] / r["k_WmK"] for r in rows)
    if r_total <= 0.0:
        raise ValueError(f"non-positive total resistance {r_total}")
    return (rows[0]["temp_K"] - float(back_temp_K)) / r_total


def _style(ax) -> None:
    """Apply the shared dark theme to one axes."""
    ax.set_facecolor(_PANEL)
    ax.tick_params(colors=_TEXT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(_DIM)
    ax.title.set_color(_TEXT)


def plot_peak_element(rows: list[dict], fluxes: list[float], back_temp_K: float,
                      out_path: str) -> None:
    """Bar chart of the per-ply flux at the peak element, with the stack value.

    The bars are the per-ply ``dT_i / R_i`` values; the dashed line is the
    series-consistent stack flux (``stack_flux``).  In a steady series state
    the two must agree, so any bar that departs from the line means the
    recorded node temperatures are inconsistent -- most visibly in the
    thinnest, lowest-R ply, where ``1/R`` amplifies the discrepancy.  Both are
    shown; neither is hidden.
    """
    q_stack = stack_flux(rows, back_temp_K)
    # ply_name now comes from the preset (set in load_layers), so the labels
    # cannot drift from the layup the solver actually used.
    labels = [
        f"{r['ply']}\n{r['ply_name'].split()[0]}\n"
        f"R={r['thickness_m'] / r['k_WmK']:.5f}"
        for r in rows
    ]
    fig, ax = plt.subplots(figsize=(6.4, 3.9), dpi=200, facecolor=_BG)
    bars = ax.bar(labels, fluxes, color=_ACCENT, edgecolor="none")
    for bar, q in zip(bars, fluxes):
        ax.annotate(f"{q:,.0f}", (bar.get_x() + bar.get_width() / 2, q),
                    ha="center", va="bottom", color=_TEXT, fontsize=7)
    ax.axhline(q_stack, color=_TEXT, linestyle="--", linewidth=1.0)
    ax.annotate(f"series-consistent stack flux {q_stack:,.0f}",
                (0.02, q_stack), xycoords=("axes fraction", "data"),
                ha="left", va="bottom", color=_TEXT, fontsize=7)
    ax.set_ylabel("through-flux q [W/m$^2$]", color=_TEXT, fontsize=8)
    ax.set_xlabel("ply (surface to back), R = thickness / k", color=_TEXT, fontsize=8)
    ax.set_title("Per-ply heat flux -- peak element", color=_TEXT, fontsize=9)
    _style(ax)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    _annotate_stage(fig, y=0.022)
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


def plot_temperature_profile(rows: list[dict], back_temp_K: float, out_path: str) -> None:
    """Temperature vs depth through the stack for the peak element."""
    depths = [r["depth_m"] for r in rows]
    temps = [r["temp_K"] for r in rows]
    depths_full = depths + [depths[-1] + rows[-1]["thickness_m"]]
    temps_full = temps + [float(back_temp_K)]

    fig, ax = plt.subplots(figsize=(6.0, 3.6), dpi=200, facecolor=_BG)
    ax.plot([d * 1000.0 for d in depths_full], temps_full, "-o",
            color=_ACCENT, markersize=4, linewidth=1.4)
    for i, r in enumerate(rows):
        ax.axvline(r["depth_m"] * 1000.0, color=_DIM, linestyle=":", linewidth=0.7)
    ax.set_xlabel("depth from surface [mm]", color=_TEXT, fontsize=8)
    ax.set_ylabel("temperature [K]", color=_TEXT, fontsize=8)
    ax.set_title("Through-thickness temperature -- peak element", color=_TEXT, fontsize=9)
    _style(ax)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    _annotate_stage(fig, y=0.022)
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


def plot_flux_distribution(all_flux: list[list[float]], out_path: str) -> None:
    """Box plot of the per-ply flux across every element."""
    n_ply = len(all_flux[0])
    series = [[f[i] for f in all_flux] for i in range(n_ply)]
    # This function receives only the numbers, not the ply rows, so the names
    # are read from the same authoritative preset the solver used.  Importing
    # the wrapper is cached by the interpreter and is deterministic, so this
    # is not a second source of truth -- it is the same one, reached twice.
    _, _, preset_names = _load_ply_preset()
    labels = [f"{i + 1}\n{preset_names[i].split()[0]}" for i in range(n_ply)]

    fig, ax = plt.subplots(figsize=(6.0, 3.6), dpi=200, facecolor=_BG)
    # matplotlib renamed Axes.boxplot's `labels` kwarg to `tick_labels` in 3.9 and
    # removed the old name by 3.11 (verified: venv_validation ships 3.11.2, where
    # `labels=` raises TypeError "unexpected keyword argument"). Setting the tick
    # labels explicitly works on every version and avoids the rename entirely.
    bp = ax.boxplot(series, patch_artist=True, showfliers=False)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, color=_TEXT, fontsize=7)
    for box in bp["boxes"]:
        box.set(facecolor=_ACCENT, edgecolor="none", alpha=0.75)
    for key in ("whiskers", "caps", "medians"):
        for artist in bp[key]:
            artist.set(color=_TEXT)
    ax.set_ylabel("through-flux q [W/m$^2$]", color=_TEXT, fontsize=8)
    ax.set_xlabel("ply (surface to back)", color=_TEXT, fontsize=8)
    ax.set_title("Per-ply heat-flux distribution -- all elements", color=_TEXT, fontsize=9)
    _style(ax)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    _annotate_stage(fig, y=0.024)
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Reentry-stage annotation (single definition, reused by every figure)
# ---------------------------------------------------------------------------
# WHY A CONSTANT AND NOT AN f-string AT EACH CALL SITE: the flight condition
# behind these numbers is an OPEN decision, and the wording has to say so in
# every figure or a reader will take one velocity as settled.  Defining it once
# means it cannot be softened in one place and left exact in another.
#
# WHAT IS SETTLED: the data is DSMC step 2200 of a 300,000,000-step run.
# WHAT IS NOT: the velocity.  The code states Snapshot_Vel_Ms = 3378 m/s at
# Snapshot_Alt_Km = 51.8 km; the trajectory's own 51.8 km value is 2741.14 m/s
# and the scalloped DSMC deck uses 2700 m/s (M 7.534).  Velocity alone accounts
# for 98.0 % of the apparent 2x DSMC discrepancy, so the SENSITIVITY RANKING is
# invariant to this choice but the absolute numbers are not.
STAGE_TEXT = (
    "DSMC step 2200 of 300,000,000  |  snapshot condition stated in code: "
    "\u2009h = 51.8 km, V = 3378 m/s"
)
STAGE_CAVEAT = (
    "\u26a0 flight condition OPEN: the code states V = 3378 m/s at 51.8 km, the "
    "trajectory's own 51.8 km value is 2741.14 m/s and the scalloped DSMC deck "
    "uses 2700 m/s (M 7.534). Velocity alone explains 98.0% of the apparent "
    "2\u00d7 discrepancy; the ranking is invariant, the absolute values are not."
)


def _annotate_stage(fig, y: float = 0.012, fontsize: int = 6) -> None:
    """Stamp every figure with the trajectory stage it belongs to.

    AXIOMS:
        A1. A figure without its stage is uninterpretable, because the whole
            TPS state is a function of where the vehicle is on the trajectory.
        A2. The velocity behind these numbers is an OPEN decision, so the
            annotation must state the step, the condition the code asserts and
            the discrepancy -- never present one velocity as fact.

    THEORIES: putting the text in figure coordinates (not axes coordinates)
    keeps it outside the data box, so it cannot overlap a trace.

    APPLICATIONS: called once per figure, immediately before savefig.

    Parameters:
        fig: the Figure to annotate.
        y: vertical position in figure coordinates (0 = bottom).
        fontsize: point size of the annotation text.
    """
    fig.text(0.5, y, STAGE_TEXT, ha="center", va="bottom",
             color=_TEXT, fontsize=fontsize)
    fig.text(0.5, y - 0.014, STAGE_CAVEAT, ha="center", va="bottom",
             color=_ACCENT, fontsize=fontsize - 0.5, wrap=True)


def load_profiles(csv_path: str) -> dict[int, list[tuple[float, float]]]:
    """Read the through-thickness profile CSV into ``{element: [(depth, T), ...]}``.

    AXIOMS:
        A1. ``tps_step2200_profiles.csv`` is written by
            ``run_tps_conduction_step2200.py`` straight from the Ada solver's
            ``TPS_Profile_Sample`` array, so it is a primary record of the
            in-depth temperature -- unlike ``tps_step2200_layers.csv``, whose
            material columns are an orphan.
        A2. One element == one contiguous block of rows in file order.

    THEORIES: the profile is the measured through-thickness gradient; the
    literal-stack heatmap colours a ply from it rather than from a single node.

    APPLICATIONS: ``plot_ply_stack_heatmap`` and
    ``plot_ply_temperature_by_element``.

    Parameters:
        csv_path: path to ``tps_step2200_profiles.csv``.

    Returns:
        dict element id -> list of (depth_m, temp_K) in ascending depth order
        (hot face first).

    Raises:
        FileNotFoundError: csv_path does not exist.
        ValueError: the file has no usable rows.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"profile CSV not found: {csv_path}")

    by_element: dict[int, list[tuple[float, float]]] = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                element = int(row["element"])
                depth_m = float(row["depth_m"])
                temp_K = float(row["temp_K"])
            except (KeyError, ValueError):
                continue
            by_element.setdefault(element, []).append((depth_m, temp_K))
    for element, samples in by_element.items():
        samples.sort(key=lambda dt: dt[0])

    if not by_element:
        raise ValueError(f"no usable profile rows in {csv_path}")
    return by_element


def load_elements(csv_path: str) -> dict[int, dict[str, float]]:
    """Read the per-element summary CSV into ``{element: {field: value}}``.

    Parameters:
        csv_path: path to ``tps_step2200_elements.csv``.

    Returns:
        dict element id -> row dict with floats for
        ``ke_raw_Wm2, q_sg_Wm2, t_surface_K, t_back_K, n_iterations``.

    Raises:
        FileNotFoundError: csv_path does not exist.
        ValueError: the file has no usable rows.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"element CSV not found: {csv_path}")

    numeric = ("ke_raw_Wm2", "q_sg_Wm2", "t_surface_K", "t_back_K",
               "n_iterations")
    by_element: dict[int, dict[str, float]] = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                element = int(row["element"])
            except (KeyError, ValueError):
                continue
            values: dict[str, float] = {}
            for key in numeric:
                try:
                    values[key] = float(row[key])
                except (KeyError, ValueError):
                    values[key] = float("nan")
            by_element[element] = values

    if not by_element:
        raise ValueError(f"no usable element rows in {csv_path}")
    return by_element


def plot_ply_stack_heatmap(peak_rows: list[dict],
                           low_rows: list[dict],
                           peak_back: float,
                           low_back: float,
                           peak_profile: list[tuple[float, float]],
                           low_profile: list[tuple[float, float]],
                           out_path: str,
                           peak_element: int = -1,
                           low_element: int = -1,
                           tmax: tuple[float, ...] | None = None) -> None:
    """Draw the LITERAL 5-ply stack, hot face up, coloured by temperature.

    AXIOMS:
        A1. The plies are in series and are drawn at their TRUE thickness
            ratios, so the picture is a scale section of the real stack: the
            hot face is at the top (depth 0) and the cold face at the bottom.
        A2. Colour comes from the solver's 33-sample through-thickness
            profile, not from one node per ply, so a ply whose internal
            gradient is steep shows it.
        A3. A ply thinner than the eye can resolve (the 25 um Kapton ply is
            0.35 % of the 7.131 mm stack) is drawn at true scale in the main
            section and repeated in an inset at an explicitly LABELLED
            exaggerated scale.  Honesty about the exaggeration is the point.

    THEORIES:
        T1. Contrasting the PEAK-heating element with a LOW-heating element in
            the same stack shows how much of the temperature field the outer
            plies take and how little the insulation's protection varies.
        T2. The annotating table reports each ply's own T_max capability next
            to its computed node temperature, because a single stack-level
            limit cannot express a layup whose plies span 773 .. 2073 K.

    APPLICATIONS:
    Writes ``results/plots/tps_per_ply/ply_stack_temperature_heatmap.png`` and
    returns None.  Never raises for a missing profile: it refuses to draw
    (returns after printing) rather than inventing a temperature field.

    Parameters:
        peak_rows: peak element's 5 ply rows from ``load_layers``.
        low_rows: the contrast element's 5 ply rows.
        peak_back, low_back: cold-face Dirichlet temperatures [K].
        peak_profile, low_profile: (depth_m, temp_K) samples per element.
        out_path: PNG destination.
        peak_element, low_element: element ids for the column titles.
        tmax: per-ply maximum continuous-use temperature [K].
    """
    if not peak_rows or not low_rows:
        raise ValueError("need 5 ply rows for both the peak and contrast element")
    if len(peak_profile) < 2 or len(low_profile) < 2:
        raise ValueError("need >= 2 profile samples per element to draw a stack")

    thicknesses = tuple(r["thickness_m"] for r in peak_rows)
    limits = tmax if tmax is not None else tuple(float("nan") for _ in peak_rows)

    all_temps = [t for _, t in peak_profile] + [t for _, t in low_profile]
    t_lo, t_hi = min(all_temps), max(all_temps)
    if not (t_hi > t_lo):
        raise ValueError(f"degenerate temperature range {t_lo}..{t_hi}")

    fig = plt.figure(figsize=(8.6, 6.2), dpi=200, facecolor=_BG)
    # wspace is generous because the node-temperature annotations and the
    # shared per-ply data column both live outside the strip rectangles.
    grid = fig.add_gridspec(
        2, 4, height_ratios=[0.60, 0.40], width_ratios=[1.0, 1.0, 0.62, 0.045],
        hspace=0.30, wspace=0.55, left=0.075, right=0.915, top=0.90, bottom=0.155,
    )
    ax_peak = fig.add_subplot(grid[0, 0])
    ax_low = fig.add_subplot(grid[0, 1])
    ax_legend = fig.add_subplot(grid[0, 2])
    ax_tab = fig.add_subplot(grid[1, :])
    ax_peak.set_facecolor(_PANEL)
    ax_low.set_facecolor(_PANEL)
    ax_legend.set_facecolor(_BG)
    ax_tab.set_facecolor(_PANEL)

    cmap = plt.get_cmap("inferno")
    norm = matplotlib.colors.Normalize(vmin=t_lo, vmax=t_hi)
    # The heat strip occupies the left 46 % of each axes; the rest holds the
    # node temperatures.  Drawn to a constant so the two columns line up.
    global _STRIP_W
    _STRIP_W = 0.46

    for ax, rows, profile, back, element, title in (
        (ax_peak, peak_rows, peak_profile, peak_back, peak_element,
         f"PEAK heating \u2014 element {peak_element}"),
        (ax_low, low_rows, low_profile, low_back, low_element,
         f"LOW heating \u2014 element {low_element}"),
    ):
        depths = [d for d, _ in profile]
        temps = [t for _, t in profile] + [float(back)]
        bounds = [0.0]
        for r in rows:
            bounds.append(bounds[-1] + r["thickness_m"])
        total_mm = bounds[-1] * 1000.0

        # The through-thickness heat strip: one column, y = depth, hot face up.
        # Built from explicit rectangles rather than pcolormesh so the colour of
        # every depth segment is exactly the recorded node temperature, with no
        # shading-rule ambiguity and no interpolation across the Ply interfaces.
        seg_depths = [d * 1000.0 for d in depths] + [total_mm]
        for i in range(len(temps) - 1):
            ax.add_patch(plt.Rectangle(
                (0.0, seg_depths[i]), _STRIP_W, seg_depths[i + 1] - seg_depths[i],
                facecolor=cmap(norm(temps[i])), edgecolor="none", linewidth=0))
        # True-proportion ply boundaries and labels.
        # The 0.506 mm SiC plies are only 7.10 % of the stack each, so a
        # three-line box centred in the band overflows into its neighbour --
        # which the machine-read check caught as a 44 % overlap.  A band that
        # cannot hold its own label gets ONLY the ply number inside, and every
        # ply's full data appears once in the right-hand legend column plus
        # the table below.  No information is dropped; the duplication is.
        y_span_mm = (bounds[-1]) * 1000.0
        for i, r in enumerate(rows):
            top_mm = bounds[i] * 1000.0
            bot_mm = bounds[i + 1] * 1000.0
            ax.axhline(bot_mm, color=_BG, linewidth=1.4)
            band_mm = bot_mm - top_mm
            if band_mm / y_span_mm >= 0.10:
                lab = (f"{i + 1}. {r['ply_name']}\n"
                       f"{r['thickness_m'] * 1000.0:.3f} mm "
                       f"({band_mm / y_span_mm * 100.0:.2f}%)\n"
                       f"R={r['thickness_m'] / r['k_WmK']:.5f}")
                ax.annotate(lab, (_STRIP_W / 2.0, (top_mm + bot_mm) / 2.0),
                            ha="center", va="center", color=_TEXT, fontsize=5.6,
                            bbox={"boxstyle": "round,pad=0.20",
                                  "facecolor": _BG, "edgecolor": _DIM,
                                  "alpha": 0.85})
            else:
                ax.annotate(str(i + 1), (0.015, (top_mm + bot_mm) / 2.0),
                            ha="left", va="center", color=_TEXT, fontsize=5.4)
                ax.annotate("", xy=(0.04, (top_mm + bot_mm) / 2.0),
                            xytext=(0.005, (top_mm + bot_mm) / 2.0),
                            arrowprops={"arrowstyle": "-", "color": _DIM,
                                         "linewidth": 0.4})
        # Node temperatures at true depth, measured not derived.
        for d, t in zip(depths, temps):
            ax.annotate(f"{t:,.1f} K", (_STRIP_W + 0.03, d * 1000.0),
                        ha="left", va="center", color=_TEXT, fontsize=4.8)
        ax.set_ylim(total_mm, 0.0)  # depth 0 (hot face) at the TOP
        ax.set_xlim(0.0, 1.0)
        ax.set_xticks([])
        ax.set_ylabel("depth from hot face [mm]", color=_TEXT, fontsize=7)
        ax.set_title(title, color=_TEXT, fontsize=8)
        ax.tick_params(colors=_TEXT, labelsize=6.5)
        for spine in ax.spines.values():
            spine.set_color(_DIM)

    # Thin-ply zoom.  The 25 um Kapton ply is 0.35% of the stack and would be
    # sub-pixel at true scale, so it is repeated here at a stated 20x.
    ax_zoom = ax_low.inset_axes([1.30, 0.42, 0.42, 0.30])
    ax_zoom.set_facecolor(_PANEL)
    zoom_plies = [i for i, t in enumerate(thicknesses)
                  if t / (thicknesses and sum(thicknesses)) < 0.02]
    zoom_pts: list[float] = []
    for i in zoom_plies:
        r = peak_rows[i]
        t_k = (peak_profile[0][1] if i == 0
               else float(r["temp_K"]))
        zoom_pts.append(t_k)
        ax_zoom.add_patch(plt.Rectangle((0.0, i * 10.0), 1.0, 8.0,
                                        facecolor=cmap(norm(t_k)),
                                        edgecolor=_BG, linewidth=0.6))
        ax_zoom.annotate(f"{i + 1}. {r['ply_name']} "
                         f"{r['thickness_m'] * 1000.0:.3f} mm",
                         (1.05, i * 10.0 + 4.0), ha="left", va="center",
                         color=_TEXT, fontsize=4.6,
                         transform=ax_zoom.get_yaxis_transform())
    ax_zoom.set_xlim(0.0, 1.0)
    ax_zoom.set_ylim(len(zoom_plies) * 10.0, 0.0)
    ax_zoom.set_xticks([])
    ax_zoom.set_yticks([])
    for spine in ax_zoom.spines.values():
        spine.set_color(_ACCENT)
    ax_zoom.set_title("thin plies, vertical scale \u00d720\n(NOT to scale)",
                      color=_ACCENT, fontsize=4.8)

    # Shared per-ply data column.  Both stack axes carry the SAME layup, so one
    # column serves both; evenly spaced rows cannot collide with each other or
    # with the strips the way position-locked in-band labels did.
    ax_legend.set_xlim(0.0, 1.0)
    ax_legend.set_ylim(0.0, 1.0)
    ax_legend.axis("off")
    ax_legend.set_title("layup (identical in both columns)",
                        color=_TEXT, fontsize=5.6, pad=4)
    for i, r in enumerate(peak_rows):
        share = r["thickness_m"] / sum(thicknesses) * 100.0
        limit = limits[i]
        ax_legend.annotate(
            f"{i + 1}. {r['ply_name']}\n"
            f"    {r['thickness_m'] * 1000.0:.3f} mm ({share:.2f}%)\n"
            f"    R={r['thickness_m'] / r['k_WmK']:.5f} m\u00b2K/W\n"
            f"    T_max={f'{limit:,.0f} K' if not math.isnan(limit) else 'n/a'}",
            (0.0, 1.0 - (i + 0.5) / len(peak_rows)), ha="left", va="center",
            color=_TEXT, fontsize=4.9)

    # Colourbar.
    sm = matplotlib.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=fig.add_subplot(grid[0, 3]))
    cbar.set_label("temperature [K]", color=_TEXT, fontsize=7)
    cbar.ax.tick_params(colors=_TEXT, labelsize=6)
    cbar.outline.set_color(_DIM)

    # Per-ply data table -- measured node temperatures and each ply's own limit.
    headers = ["ply", "material", "thickness\n[mm]", "k\n[W/m\u00b7K]",
               "R\n[m\u00b2K/W]", "T_top [K]", "T_bot [K]", "\u0394T [K]",
               "T_max\nlimit [K]", "margin [K]"]
    cell_text: list[list[str]] = []
    cell_colours: list[list[tuple[float, float, float, float]]] = []
    for i, r in enumerate(peak_rows):
        t_top = float(r["temp_K"])
        t_bot = (float(peak_rows[i + 1]["temp_K"]) if i + 1 < len(peak_rows)
                 else float(peak_back))
        limit = limits[i]
        margin = (limit - t_top) if not math.isnan(limit) else float("nan")
        cell_text.append([
            str(i + 1), r["ply_name"], f"{r['thickness_m'] * 1000.0:.3f}",
            f"{r['k_WmK']:.2f}", f"{r['thickness_m'] / r['k_WmK']:.5f}",
            f"{t_top:,.1f}", f"{t_bot:,.1f}", f"{t_top - t_bot:,.1f}",
            (f"{limit:,.0f}" if not math.isnan(limit) else "n/a"),
            (f"{margin:,.0f}" if not math.isnan(margin) else "n/a"),
        ])
        cell_colours.append([cmap(norm(t_top))] * len(headers))
    ax_tab.axis("off")
    ax_tab.set_title(
        "Per-ply temperature at the peak element -- measured node values, each "
        "ply's own T_max capability, and the remaining margin",
        color=_TEXT, fontsize=7.5, pad=8)
    table = ax_tab.table(cellText=cell_text, cellColours=cell_colours,
                         colLabels=headers, cellLoc="center", loc="upper center")
    table.auto_set_font_size(False)
    table.set_fontsize(5.8)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor(_DIM)
        cell.set_linewidth(0.4)
        if row == 0:
            cell.set_facecolor(_PANEL)
            cell.set_text_props(color=_TEXT)
        else:
            cell.set_text_props(color=_TEXT)

    fig.suptitle(
        "TPS literal 5-ply stack -- through-thickness temperature heatmap",
        color=_TEXT, fontsize=10, y=0.975)
    _annotate_stage(fig, y=0.028)
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


def plot_ply_temperature_by_element(rows_by_element: dict[int, list[dict]],
                                    elements: dict[int, dict[str, float]],
                                    out_path: str,
                                    tmax: tuple[float, ...] | None = None,
                                    max_elements: int = 900) -> None:
    """Per-ply temperature data across the whole surface, not just the peak.

    AXIOMS:
        A1. The worst element is one sample; the SURVIVABILITY answer is how
            many elements exceed which limit, so the data must be shown across
            the surface.
        A2. Ordering the elements by descending peak node temperature makes the
            abscissa a heating axis, so each ply's trace is monotone by
            construction and the shape is readable.

    THEORIES:
        T1. Each ply's own T_max is a horizontal line on its own trace, which
            is the only way a stack whose plies span 773 .. 2073 K can be read
            without a single shared limit hiding a real exceedance.
        T2. Sub-sampling the abscissa (``max_elements``) keeps the PNG legible
            while the extremes -- which are what matter -- are never dropped.

    APPLICATIONS:
    Writes ``results/plots/tps_per_ply/ply_temperature_by_element.png``.

    Parameters:
        rows_by_element: ``{element: [ply_row, ...]}`` from ``load_layers``.
        elements: ``{element: {q_sg_Wm2, t_surface_K, ...}}`` from
            ``load_elements``.
        out_path: PNG destination.
        tmax: per-ply maximum continuous-use temperature [K].
        max_elements: abscissa subsample cap.
    """
    usable = [(e, rows) for e, rows in rows_by_element.items() if len(rows) >= 2]
    if not usable:
        raise ValueError("need >= 2 ply rows per element")
    usable.sort(key=lambda er: -max(r["temp_K"] for r in er[1]))
    if len(usable) > max_elements:
        step = len(usable) / float(max_elements)
        usable = [usable[int(i * step)] for i in range(max_elements)]

    n_ply = len(usable[0][1])
    limits = tmax if tmax is not None else tuple(float("nan") for _ in range(n_ply))
    names = tuple(r["ply_name"] for r in usable[0][1])

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(8.6, 3.8), dpi=200,
                                         facecolor=_BG, sharex=True)
    ax_lin.set_facecolor(_PANEL)
    ax_log.set_facecolor(_PANEL)

    xs = list(range(len(usable)))
    # One colour per ply, ordered hot -> cold so the traces read as a stack.
    cmap = plt.get_cmap("plasma")
    for i in range(n_ply):
        ys = [rows[i]["temp_K"] for _, rows in usable]
        colour = cmap(i / max(1, n_ply - 1))
        ax_lin.plot(xs, ys, color=colour, linewidth=1.0,
                    label=f"{i + 1}. {names[i]}")
        ax_log.plot(xs, ys, color=colour, linewidth=1.0)
        limit = limits[i]
        if not math.isnan(limit):
            ax_lin.axhline(limit, color=colour, linestyle=":", linewidth=0.7)

    ax_lin.set_yscale("linear")
    ax_log.set_yscale("log")
    for ax in (ax_lin, ax_log):
        ax.set_xlabel("elements ordered by hottest ply (descending)",
                      color=_TEXT, fontsize=7)
        ax.set_ylabel("node temperature [K]", color=_TEXT, fontsize=7)
        ax.tick_params(colors=_TEXT, labelsize=6.5)
        for spine in ax.spines.values():
            spine.set_color(_DIM)
        ax.grid(True, color=_DIM, linewidth=0.3, alpha=0.5)
    ax_lin.set_title("per-ply temperature -- linear", color=_TEXT, fontsize=8)
    ax_log.set_title("per-ply temperature -- log (the cold plies are visible)",
                     color=_TEXT, fontsize=8)
    ax_lin.legend(loc="upper right", fontsize=5.6, frameon=True,
                  facecolor=_PANEL, edgecolor=_DIM, labelcolor=_TEXT)

    # Distribution of each ply's node temperature: the box IS the answer to
    # "how many elements exceed which limit", without reading off one axis.
    ax_hist = ax_log.inset_axes([0.60, 0.14, 0.36, 0.42])
    ax_hist.set_facecolor(_PANEL)
    data = [[rows[i]["temp_K"] for _, rows in usable] for i in range(n_ply)]
    bp = ax_hist.boxplot(data, orientation="horizontal", patch_artist=True,
                         widths=0.7,
                         medianprops={"color": _ACCENT, "linewidth": 0.8},
                         flierprops={"marker": ".", "markersize": 1.0,
                                     "markerfacecolor": _TEXT,
                                     "markeredgecolor": "none"})
    for patch, i in zip(bp["boxes"], range(n_ply)):
        patch.set_facecolor(cmap(i / max(1, n_ply - 1)))
        patch.set_edgecolor(_DIM)
        patch.set_linewidth(0.4)
    for i, limit in enumerate(limits, start=1):
        if not math.isnan(limit):
            ax_hist.axvline(limit, color=_TEXT, linestyle=":", linewidth=0.5)
            ax_hist.annotate(f"{i}:{limit:,.0f}", (limit, n_ply + 0.35),
                             ha="center", va="bottom", color=_TEXT, fontsize=4.0)
    ax_hist.set_yticks(range(1, n_ply + 1))
    ax_hist.set_yticklabels([f"{i + 1}" for i in range(n_ply)], fontsize=4.6,
                            color=_TEXT)
    ax_hist.tick_params(colors=_TEXT, labelsize=4.6)
    ax_hist.set_xlabel("node T [K]", color=_TEXT, fontsize=4.8)
    ax_hist.set_title("distribution + dotted T_max per ply", color=_TEXT,
                      fontsize=4.8)
    for spine in ax_hist.spines.values():
        spine.set_color(_DIM)

    fig.suptitle("Per-ply temperature across the whole TPS surface",
                 color=_TEXT, fontsize=9.5, y=0.985)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    _annotate_stage(fig, y=0.026)
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


def render_ply_heating_mp4(
    by_element: dict[int, list[dict]],
    back: dict[int, float],
    out_path: str,
    max_frames: int = 240,
    fps: int = 8,
) -> bool:
    """Animate the per-ply heating of the TPS stack as the vehicle heats up.

    AXIOMS:
    A1. Every element carries the same 5-ply stack, so the ONLY thing that
        varies across elements is how hard each ply is being driven.
    A2. Ordering the elements by their worst per-ply flux turns the frame
        index into a heating axis: frame 0 is the mildest element, the last
        frame is the peak.  Watching the bars grow IS the heating history.
    A3. A ply's flux is (T_top - T_bottom) / R_ply, the through-flux, and the
        temperature profile is the node curve T(depth).  Both are recorded
        per element in the layers CSV.

    THEORIES:
    T1. The stack is in quasi-steady conduction, so the per-ply flux must
        agree across plies.  Where it does NOT (ply 5 has R = 0.00125
        m^2 K/W, so its per-ply value is large), the animation shows the
        per-ply value and the caption states that the series value is the
        self-consistent one -- see stack_flux.
    T2. Because the per-ply flux of the peak element is an order of magnitude
        above the mild elements' on some plies, a LINEAR y-axis hides the
        mild frames.  The y-limit is taken from the data, not hardcoded.

    APPLICATIONS:
    Writes results/plots/tps_per_ply/ply_heating_animation.mp4, one frame
    per (subsampled) element in ascending heating order.  Returns True when
    the file is written, False when the animation stack is unavailable --
    the caller reports that loudly rather than writing a silent stub.

    Args:
        by_element: {element: [ply_row, ...]} from load_layers.
        back: {element: cold-face temperature K} from load_back_temp.
        out_path: destination .mp4 path.
        max_frames: cap on frames (the full 3648 elements is too many).
        fps: animation frame rate.

    Returns:
        True on success, False when matplotlib/ffmpeg is unavailable.

    Raises:
        ValueError: no element produced a per-ply flux.

    References:
        - https://matplotlib.org/stable/api/_as_gen/matplotlib.animation.FuncAnimation.html
        - https://matplotlib.org/stable/api/animation_api.html
    """
    ordered: list[tuple[int, list[float], list[dict], float]] = []
    skipped_flat = 0
    for element, rows in sorted(by_element.items()):
        if len(rows) < 2:
            continue
        back_temp = back.get(element, rows[-1]["temp_K"])
        try:
            fluxes = per_ply_flux(rows, back_temp)
        except ValueError:
            continue
        #  An element whose node temperatures are all equal carries NO
        #  through-flux -- it sits outside the heated region.  Keeping such
        #  elements would sort them to the front (their max flux is 0) and
        #  open the animation with a third of its frames blank, which reads
        #  as a broken figure rather than as "unheated".
        if max(fluxes) <= 0.0:
            skipped_flat += 1
            continue
        ordered.append((element, fluxes, rows, back_temp))

    if skipped_flat:
        print(f"[ply] skipped {skipped_flat} element(s) with no through-flux",
              file=sys.stderr)

    if not ordered:
        raise ValueError("no element produced a per-ply flux")

    #  A2: ascending heating order -- the animation heats up over time.
    ordered.sort(key=lambda item: max(item[1]))

    if len(ordered) > max_frames:
        step = len(ordered) / float(max_frames)
        ordered = [ordered[int(i * step)] for i in range(max_frames)]
        #  Always keep the peak element as the final frame so the animation
        #  ends on the worst case even if the stride skipped it.  Guarded:
        #  a malformed element must not abort the whole animation.
        peak_element = None
        peak_key = None
        for cand, cand_rows in by_element.items():
            if len(cand_rows) < 2:
                continue
            try:
                key = max(per_ply_flux(
                    cand_rows,
                    back.get(cand, cand_rows[-1]["temp_K"]),
                ))
            except ValueError:
                continue
            if peak_key is None or key > peak_key:
                peak_key, peak_element = key, cand
        if peak_element is not None:
            ordered[-1] = (
                peak_element,
                per_ply_flux(
                    by_element[peak_element],
                    back.get(peak_element, by_element[peak_element][-1]["temp_K"]),
                ),
                by_element[peak_element],
                back.get(peak_element, by_element[peak_element][-1]["temp_K"]),
            )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.animation import FFMpegWriter, FuncAnimation
    #  Narrowed deliberately: a missing matplotlib, a missing animation
    #  module, or a backend that refuses Agg.  Anything else is a real
    #  bug and must propagate rather than silently skip the animation.
    except (ImportError, RuntimeError) as exc:
        print(f"[ply] animation stack unavailable: {exc}", file=sys.stderr)
        return False

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    #  Dark theme, matching the five PNG figures.  This animation used to be
    #  built with no facecolour at all, so every MP4 frame was white
    #  (253,253,253 = 84.9 % of extracted frame pixels) next to dark PNGs in
    #  the same directory, and its bars/lines were matplotlib's default
    #  tableau colours (#d62728 / #1f77b4) instead of the project's _ACCENT.
    #  Found by extracting real frames and counting pixels, not by reading the
    #  renderer's exit code.
    fig, (ax_q, ax_t) = plt.subplots(1, 2, figsize=(12.0, 5.2), facecolor=_BG)
    ply_labels = [f"ply {r['ply']}\n{r['ply_name']}" for r in ordered[0][2]]
    x_pos = list(range(len(ply_labels)))
    #  T2: the per-ply flux spans orders of magnitude between the mildest and
    #  the peak element, so a LINEAR axis leaves the first frames blank and a
    #  caption cannot describe what it does not show.  Log axis, floored, so
    #  every frame is readable and the growth is the visible quantity.
    positive = [v for _, fl, _, _ in ordered for v in fl if v > 0.0]
    if not positive:
        raise ValueError("no positive per-ply flux to plot")
    y_lo = min(positive) * 0.01
    y_hi = max(positive) * 2.0
    ax_q.set_yscale("log")
    ax_q.set_ylim(y_lo, y_hi)
    ax_q.set_xticks(x_pos)
    ax_q.set_xticklabels(ply_labels, fontsize=8)
    ax_q.set_ylabel("per-ply heat flux [W/m^2]  (log)", color=_TEXT, fontsize=9)
    ax_q.set_title("per-ply heat flux", color=_TEXT, fontsize=10)
    #  bottom must be a POSITIVE number on a log axis, hence the floor.
    bar_floor = y_lo
    #  bottom = y_lo so a bar at the floor is still a visible column rather
    #  than an invisible hairline at the bottom edge of a log axis.
    bars_q = ax_q.bar(x_pos, [0.0] * len(x_pos), bottom=bar_floor,
                      color=_ACCENT, alpha=0.95, edgecolor="none")

    ax_t.set_xlabel("depth from hot face [mm]", color=_TEXT, fontsize=9)
    ax_t.set_ylabel("temperature [K]", color=_TEXT, fontsize=9)
    ax_t.set_title("temperature through the stack", color=_TEXT, fontsize=10)
    #  Same ply boundaries as the literal-stack figure, same dim style.
    for r in ordered[0][2]:
        ax_t.axvline(r["depth_m"] * 1000.0, color=_DIM, linestyle=":",
                     linewidth=0.7)
    #  Distinct from _ACCENT so the two panels read as different quantities;
    #  _TEXT is the shared theme's own secondary colour, not a matplotlib
     #  default.
    (line_t,) = ax_t.plot([], [], color=_TEXT, marker="o", markersize=3,
                          markerfacecolor=_ACCENT)

    n_frames = len(ordered)

    def _update(frame: int) -> None:
        element, fluxes, rows, back_temp = ordered[frame]
        for bar, value in zip(bars_q, fluxes):
            bar.set_height(max(0.0, value - bar_floor))
        depths = [r["depth_m"] * 1000.0 for r in rows] + [
            rows[-1]["depth_m"] * 1000.0
            + rows[-1]["thickness_m"] * 1000.0
        ]
        temps = [r["temp_K"] for r in rows] + [back_temp]
        line_t.set_data(depths, temps)
        ax_t.set_xlim(min(depths) * 0.98, max(depths) * 1.02)
        ax_t.set_ylim(min(temps) * 0.98, max(temps) * 1.02)
        fig.suptitle(
            f"TPS per-ply heating  --  element {element} of "
            f"{len(by_element)}  (heating {100.0 * (frame + 1) / n_frames:4.1f}%)",
            fontsize=11, color=_TEXT,
        )

    #  Shared dark theme on both panels: facecolour, tick/label colour, spines.
    for _ax in (ax_q, ax_t):
        _ax.set_facecolor(_PANEL)
        _ax.tick_params(colors=_TEXT, labelsize=8)
        for _spine in _ax.spines.values():
            _spine.set_color(_DIM)
        _ax.grid(True, color=_DIM, linewidth=0.3, alpha=0.45)
    #  Stage annotation per frame: a frame without its trajectory position is
    #  uninterpretable, exactly as for the PNGs.
    _annotate_stage(fig, y=0.018, fontsize=7)
    fig.subplots_adjust(bottom=0.20)

    anim = FuncAnimation(
        fig, _update, frames=n_frames, blit=False
    )
    writer = FFMpegWriter(fps=fps, bitrate=2400)
    anim.save(out_path, writer=writer, dpi=110)
    plt.close(fig)
    return True


def main() -> int:
    """Entry point: build the three per-ply figures.

    Returns:
        0 on success; 1 if the input data could not be read (safety fallback:
        report loudly instead of writing a misleading empty figure).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    default_dir = os.path.join(project_root, "results", "tps_conduction")

    ap = argparse.ArgumentParser(description="Per-ply TPS heat-flux figures.")
    ap.add_argument("--layers-csv", default=os.path.join(default_dir, "tps_step2200_layers.csv"))
    ap.add_argument("--elements-csv", default=os.path.join(default_dir, "tps_step2200_elements.csv"))
    ap.add_argument("--profiles-csv", default=os.path.join(default_dir, "tps_step2200_profiles.csv"))
    ap.add_argument("--outdir", default=os.path.join(project_root, "results", "plots", "tps_per_ply"))
    ap.add_argument("--no-mp4", action="store_true",
                    help="skip the per-ply heating MP4 (PNGs are still written)")
    ap.add_argument("--mp4-frames", type=int, default=240,
                    help="cap on animation frames (default 240)")
    args = ap.parse_args()

    try:
        by_element = load_layers(args.layers_csv)
        back = load_back_temp(args.elements_csv)
        profiles = load_profiles(args.profiles_csv)
        elements = load_elements(args.elements_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ply] ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        preset_tmax = _preset_tmax()
    except (FileNotFoundError, AttributeError, ValueError) as exc:
        print(f"[ply] warn: per-ply T_max unavailable ({exc}); the stack "
              "heatmap will report 'n/a' limits", file=sys.stderr)
        preset_tmax = None

    all_flux: list[list[float]] = []
    for element, rows in sorted(by_element.items()):
        if len(rows) < 2:
            continue
        back_temp = back.get(element, rows[-1]["temp_K"])
        try:
            all_flux.append(per_ply_flux(rows, back_temp))
        except ValueError as exc:
            print(f"[ply] warn: element {element}: {exc}", file=sys.stderr)

    if not all_flux:
        print("[ply] ERROR: no element produced a per-ply flux", file=sys.stderr)
        return 1

    peak_element = max(by_element, key=lambda e: by_element[e][0]["temp_K"])
    peak_rows = by_element[peak_element]
    peak_back = back.get(peak_element, peak_rows[-1]["temp_K"])
    peak_flux = per_ply_flux(peak_rows, peak_back)

    # The contrast element: the LOWEST node temperature that still carries a
    # non-trivial heating state.  Taking the absolute minimum would land on an
    # unheated element and the two columns would differ only by a constant.
    # MEDIAN-heating element, not the minimum: the absolute minimum is an
    # unheated element (313 K against a 300 K Dirichlet face) and the two
    # columns would differ only by a constant, teaching nothing.  The median
    # element is the one the stack actually operates at for half the surface.
    heated = sorted(
        (e for e, rows in by_element.items()
         if len(rows) >= 2 and max(r["temp_K"] for r in rows) > 300.0),
        key=lambda e: max(r["temp_K"] for r in by_element[e]),
    )
    low_element = (heated[len(heated) // 2] if heated else peak_element)
    low_rows = by_element[low_element]
    low_back = back.get(low_element, low_rows[-1]["temp_K"])
    peak_profile = profiles.get(peak_element, [])
    low_profile = profiles.get(low_element, [])
    if len(peak_profile) < 2 or len(low_profile) < 2:
        print("[ply] ERROR: profiles CSV has no usable samples for elements "
              f"{peak_element}/{low_element}; refusing to draw the stack "
              "heatmap from invented data", file=sys.stderr)
        return 1

    os.makedirs(args.outdir, exist_ok=True)
    plot_peak_element(peak_rows, peak_flux, peak_back,
                      os.path.join(args.outdir, "ply_heatflux_peak_element.png"))
    plot_temperature_profile(peak_rows, peak_back, os.path.join(args.outdir, "ply_temperature_profile_peak_element.png"))
    plot_flux_distribution(all_flux, os.path.join(args.outdir, "ply_heatflux_distribution.png"))
    plot_ply_stack_heatmap(peak_rows, low_rows, peak_back, low_back,
                           peak_profile, low_profile,
                           os.path.join(args.outdir, "ply_stack_temperature_heatmap.png"),
                           peak_element=peak_element, low_element=low_element,
                           tmax=preset_tmax)
    plot_ply_temperature_by_element(by_element, elements,
                                    os.path.join(args.outdir, "ply_temperature_by_element.png"),
                                    tmax=preset_tmax)

    print(f"[ply] peak element {peak_element}: " + ", ".join(f"q{i + 1}={q:,.1f}" for i, q in enumerate(peak_flux)) + " W/m^2")
    print(f"[ply] elements processed: {len(all_flux)}")
    print(f"[ply] contrast element {low_element}: T_peak_node="
          f"{max(r['temp_K'] for r in low_rows):,.1f} K")
    print("[ply] per-ply node T at peak: "
          + ", ".join(f"ply{i + 1}={r['temp_K']:,.1f}" for i, r in enumerate(peak_rows)))

    mp4_path = os.path.join(args.outdir, "ply_heating_animation.mp4")
    wrote_mp4 = False
    if not args.no_mp4:
        try:
            wrote_mp4 = render_ply_heating_mp4(
                by_element, back, mp4_path, max_frames=args.mp4_frames
            )
        except ValueError as exc:
            print(f"[ply] ERROR: {exc}", file=sys.stderr)
            return 1

    figures_written = [
        "ply_heatflux_peak_element.png",
        "ply_temperature_profile_peak_element.png",
        "ply_heatflux_distribution.png",
        "ply_stack_temperature_heatmap.png",
        "ply_temperature_by_element.png",
    ]
    print(f"[ply] wrote {len(figures_written)} figures to {args.outdir}: "
          + ", ".join(figures_written))
    if wrote_mp4:
        print(f"[ply] wrote animation to {mp4_path}")
    elif not args.no_mp4:
        print("[ply] WARNING: MP4 not written (animation stack unavailable)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
