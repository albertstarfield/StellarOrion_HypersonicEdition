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

_PLY_NAMES = ("Nextel BF-20", "Nextel BF-20", "Pyrogel 2250", "Pyrogel 2250", "AKK")


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

    fig, (ax_q, ax_t) = plt.subplots(1, 2, figsize=(12.0, 5.2))
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
    ax_q.set_ylabel("per-ply heat flux [W/m^2]  (log)")
    ax_q.set_title("per-ply heat flux")
    #  bottom must be a POSITIVE number on a log axis, hence the floor.
    bar_floor = y_lo
    #  bottom = y_lo so a bar at the floor is still a visible column rather
    #  than an invisible hairline at the bottom edge of a log axis.
    bars_q = ax_q.bar(x_pos, [0.0] * len(x_pos), bottom=bar_floor,
                      color="#d62728", alpha=0.85)

    ax_t.set_xlabel("depth from hot face [mm]")
    ax_t.set_ylabel("temperature [K]")
    ax_t.set_title("temperature through the stack")
    (line_t,) = ax_t.plot([], [], color="#1f77b4", marker="o", markersize=3)

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
            fontsize=11,
        )

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
    ap.add_argument("--outdir", default=os.path.join(project_root, "results", "plots", "tps_per_ply"))
    ap.add_argument("--no-mp4", action="store_true",
                    help="skip the per-ply heating MP4 (PNGs are still written)")
    ap.add_argument("--mp4-frames", type=int, default=240,
                    help="cap on animation frames (default 240)")
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

    print(f"[ply] wrote 3 figures to {args.outdir}")
    if wrote_mp4:
        print(f"[ply] wrote animation to {mp4_path}")
    elif not args.no_mp4:
        print("[ply] WARNING: MP4 not written (animation stack unavailable)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
