#!/usr/bin/env python3
"""Per-ply heat-flux figures for the TPS conduction stack (5-ply IRVE-3 layup).

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
        Pyrogel 2250 / AKK).
    [4] matplotlib boxplot + bar docs. https://matplotlib.org/stable/api/

Author: Albert Starfield Wahyu Suryo Samudro
"""

from __future__ import annotations

import argparse
import csv
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

_PLY_NAMES = ("Nextel BF-20", "Pyrogel 2250", "AKK", "Pyrogel 2250", "Nextel BF-20")


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

    by_element: dict[int, list[dict]] = {}
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                element = int(row["element"])
                by_element.setdefault(element, []).append(
                    {
                        "ply": int(row["ply"]),
                        "ply_name": row["ply_name"],
                        "depth_m": float(row["depth_m"]),
                        "temp_K": float(row["temp_K"]),
                        "thickness_m": float(row["ply_thickness_m"]),
                        "k_WmK": float(row["ply_k_WmK"]),
                    }
                )
            except (KeyError, ValueError):
                # Malformed row: skip it rather than aborting the whole figure.
                continue

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
    labels = [
        f"{i + 1}\n{_PLY_NAMES[i].split()[0]}\nR={r['thickness_m'] / r['k_WmK']:.5f}"
        for i, r in enumerate(rows)
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
    fig.tight_layout()
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
    fig.tight_layout()
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


def plot_flux_distribution(all_flux: list[list[float]], out_path: str) -> None:
    """Box plot of the per-ply flux across every element."""
    n_ply = len(all_flux[0])
    series = [[f[i] for f in all_flux] for i in range(n_ply)]
    labels = [f"{i + 1}\n{_PLY_NAMES[i].split()[0]}" for i in range(n_ply)]

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
    fig.tight_layout()
    fig.savefig(out_path, facecolor=_BG)
    plt.close(fig)


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
    ap.add_argument("--outdir", default=os.path.join(project_root, "results", "plots", "tps_per_ply"))
    args = ap.parse_args()

    try:
        by_element = load_layers(args.layers_csv)
        back = load_back_temp(args.elements_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ply] ERROR: {exc}", file=sys.stderr)
        return 1

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

    os.makedirs(args.outdir, exist_ok=True)
    plot_peak_element(peak_rows, peak_flux, peak_back,
                      os.path.join(args.outdir, "ply_heatflux_peak_element.png"))
    plot_temperature_profile(peak_rows, peak_back, os.path.join(args.outdir, "ply_temperature_profile_peak_element.png"))
    plot_flux_distribution(all_flux, os.path.join(args.outdir, "ply_heatflux_distribution.png"))

    print(f"[ply] peak element {peak_element}: " + ", ".join(f"q{i + 1}={q:,.1f}" for i, q in enumerate(peak_flux)) + " W/m^2")
    print(f"[ply] elements processed: {len(all_flux)}")
    print(f"[ply] wrote 3 figures to {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
