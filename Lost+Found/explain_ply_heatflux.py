"""Explainer figure: why the per-ply heat flux is ONE number, and why ply 5 lies.

PURPOSE
    A teaching figure for the IRVE-3 5-ply TPS stack.  It shows, from the real
    ``results/tps_conduction/tps_step2200_layers.csv`` data at the peak element:
      1. the stack (ply, material, thickness, k, R = thickness/k);
      2. the recorded node temperatures vs depth, against the IDEAL series
         profile (T linear in R) implied by the two Dirichlet temperatures;
      3. the per-ply fluxes q_i = dT_i / R_i against the ONE series-consistent
         stack flux q = (T_surface - T_back) / R_total;
      4. the sensitivity dq/dT = 1/R, which is why the thinnest, lowest-R ply
         turns a few kelvin of inconsistency into thousands of W/m^2.

AXIOMS
    A1. Steady 1-D conduction through a series stack: d/dx(k dT/dx) = 0, so
        q = -k dT/dx is the SAME constant in every ply.
    A2. The 1-D steady problem is LINEAR, so superposition of separate solutions
        is valid -- but with two Dirichlet temperatures the solution is UNIQUE,
        so one solution carries exactly ONE through-flux.  Superposition can
        never produce several fluxes inside one steady state.
    A3. The recorded node temperatures are DATA, not a constructed series
        profile; any departure from T linear in R is an inconsistency of the
        recorded data and is reported as measured.

THEORIES
    T1. If the recorded profile is exactly series-consistent, every bar in
        panel 3 equals the dashed line.
    T2. The apparent per-ply flux error is amplified by 1/R, so the ply with the
        smallest R shows the largest apparent error for the same temperature
        error (here ply 5, R = 0.00015/0.12 = 0.00125 m^2 K/W).
    T3. q_i = dT_i / R_i is still the correct *definition* of that ply's
        through-flux; the point is that it is only equal across plies when the
        recorded temperatures form an exact series profile.

APPLICATIONS
    Produces ``Lost+Found/ply_heatflux_explainer.png`` (4 panels, dark theme).

CITATIONS
    [1] Fourier, J. (1822). Theorie analytique de la chaleur.
    [2] Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, ch. 3
        (series thermal resistance, one-dimensional steady conduction).
    [3] NASA TP-2013-4012 (IRVE-3), and the project's ``tps_conduction``
        Ada/SPARK model via ``ada_pinn_wrapper`` (single physics truth).

Author: Albert Starfield Wahyu Suryo Samudro
"""

from __future__ import annotations

import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)

_BG = "#0a0a0f"
_PANEL = "#1a1a2e"
_TEXT = "#8892b0"
_ACCENT = "#e94560"
_OK = "#4ecca3"
_DIM = "#555555"

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_SCRIPT_DIR)
_LAYERS_CSV = os.path.join(
    _PROJECT, "stellarorion_program_proc", "results", "tps_conduction",
    "tps_step2200_layers.csv",
)
_OUT_PNG = os.path.join(_SCRIPT_DIR, "ply_heatflux_explainer.png")


def load_peak_element(layers_csv: str) -> tuple[int, list[dict]]:
    """Return (element_id, ply rows ordered by ply) for the hottest element.

    Parameters:
        layers_csv: path to ``tps_step2200_layers.csv``.

    Returns:
        ``(element_id, rows)`` where ``rows`` is the 5 ply dicts of that
        element, ordered by ``ply``, each with keys ``ply``, ``ply_name``,
        ``depth_m``, ``temp_K``, ``thickness_m``, ``k_WmK``.

    Raises:
        SystemExit: the file is missing, empty, or unreadable -- a loud failure
            rather than a silently wrong figure.
    """
    if not os.path.isfile(layers_csv):
        sys.exit(f"[explain] missing {layers_csv}")
    by_element: dict[int, list[dict]] = {}
    try:
        with open(layers_csv, newline="") as fh:
            for raw in csv.DictReader(fh):
                el = int(raw["element"])
                by_element.setdefault(el, []).append(
                    {
                        "ply": int(raw["ply"]),
                        "ply_name": raw["ply_name"],
                        "depth_m": float(raw["depth_m"]),
                        "temp_K": float(raw["temp_K"]),
                        "thickness_m": float(raw["ply_thickness_m"]),
                        "k_WmK": float(raw["ply_k_WmK"]),
                    }
                )
    except (OSError, KeyError, ValueError) as exc:
        sys.exit(f"[explain] cannot parse {layers_csv}: {exc}")
    if not by_element:
        sys.exit(f"[explain] no rows in {layers_csv}")
    peak = max(by_element, key=lambda e: max(r["temp_K"] for r in by_element[e]))
    rows = sorted(by_element[peak], key=lambda r: r["ply"])
    return peak, rows


def stack_flux(rows: list[dict], back_temp_K: float) -> float:
    """Series-consistent through-flux ``(T_surface - T_back) / R_total``."""
    r_total = sum(r["thickness_m"] / r["k_WmK"] for r in rows)
    if r_total <= 0.0:
        sys.exit(f"[explain] non-positive total resistance {r_total}")
    return (rows[0]["temp_K"] - float(back_temp_K)) / r_total


def _style(ax) -> None:
    """Apply the shared dark theme."""
    ax.set_facecolor(_PANEL)
    ax.tick_params(colors=_TEXT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(_DIM)
    ax.title.set_color(_TEXT)
    ax.xaxis.label.set_color(_TEXT)
    ax.yaxis.label.set_color(_TEXT)


def main() -> int:
    """Build the 4-panel explainer figure. Returns 0 on success."""
    back_temp_K = 300.0
    peak, rows = load_peak_element(_LAYERS_CSV)
    r_ply = [r["thickness_m"] / r["k_WmK"] for r in rows]
    r_total = sum(r_ply)
    temps = [r["temp_K"] for r in rows]
    depths_mm = [r["depth_m"] * 1000.0 for r in rows]
    depths_full_mm = depths_mm + [depths_mm[-1] + rows[-1]["thickness_m"] * 1000.0]
    temps_full = temps + [back_temp_K]
    q_ply = [(temps_full[i] - temps_full[i + 1]) / r_ply[i] for i in range(len(rows))]
    q_stack = stack_flux(rows, back_temp_K)

    labels = [f"{r['ply']}\n{r['ply_name'].split()[0]}" for r in rows]
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.6), dpi=150, facecolor=_BG)
    fig.suptitle(
        "IRVE-3 TPS: one through-flux, five bars -- why ply 5 lies "
        f"(peak element {peak})",
        color=_TEXT, fontsize=12,
    )

    # ---- Panel 1: the stack ------------------------------------------------
    #  One row per ply, label ABOVE its own bar.  The earlier design (one
    #  segmented row with the text inside each segment) CLIPPED the text on the
    #  thin plies -- measured 2026-10-08: ply 1 (0.60 mm) and ply 5 (0.15 mm)
    #  are far narrower than their 3-line labels, so the R values ran off the
    #  bar and were cut at the axes edge.
    ax = axes[0][0]
    cum = 0.0
    for i, r in enumerate(rows):
        thk_mm = r["thickness_m"] * 1000.0
        row_y = float(len(rows) - 1 - i)          # ply 1 on top
        ax.barh(row_y, thk_mm, left=cum, height=0.55,
                color=_ACCENT if i != 4 else _OK, edgecolor=_BG)
        ax.text(cum + thk_mm / 2.0, row_y + 0.38,
                f"{r['ply']} {r['ply_name'].split()[0]}\n"
                f"t={thk_mm:.2f} mm  k={r['k_WmK']:.2f}\n"
                f"R={r_ply[i]:.5f}",
                ha="center", va="bottom", color=_TEXT, fontsize=6.0)
        cum += thk_mm
    #  Wide margins so a label centred on a thin bar can never be clipped.
    ax.set_xlim(-cum * 0.45, cum * 1.45)
    ax.set_ylim(-0.8, float(len(rows)) + 0.25)
    ax.set_yticks([])
    ax.set_xlabel("depth from surface [mm]")
    ax.set_title("1. The stack (R = thickness / k)", fontsize=9)
    ax.annotate("surface 1550 K", xy=(0, -0.55), color=_TEXT, fontsize=7)
    ax.annotate(f"back face {back_temp_K:.0f} K (pinned BC)",
                xy=(cum, -0.55), color=_TEXT, fontsize=7, ha="right")
    _style(ax)

    # ---- Panel 2: recorded vs ideal profile --------------------------------
    ax = axes[0][1]
    ax.plot(depths_full_mm, temps_full, "-o", color=_ACCENT, markersize=4,
            linewidth=1.4, label="recorded nodes")
    # ideal series profile: T is linear in R, not in depth
    r_cum = [0.0]
    for rr in r_ply:
        r_cum.append(r_cum[-1] + rr)
    ideal_T = [temps[0] - q_stack * rc for rc in r_cum]
    ax.plot(depths_full_mm, ideal_T, "--", color=_OK, linewidth=1.2,
            label=f"ideal series profile (q={q_stack:,.0f})")
    for d in depths_mm:
        ax.axvline(d, color=_DIM, linestyle=":", linewidth=0.7)
    ax.set_xlabel("depth from surface [mm]")
    ax.set_ylabel("temperature [K]")
    ax.set_title("2. Recorded profile vs the one-flux ideal", fontsize=9)
    ax.legend(fontsize=7, facecolor=_PANEL, edgecolor=_DIM, labelcolor=_TEXT)
    _style(ax)

    # ---- Panel 3: per-ply bars vs the stack flux ---------------------------
    ax = axes[1][0]
    bars = ax.bar(labels, q_ply, color=_ACCENT, edgecolor="none")
    for bar, q in zip(bars, q_ply):
        ax.annotate(f"{q:,.0f}", (bar.get_x() + bar.get_width() / 2, q),
                    ha="center", va="bottom", color=_TEXT, fontsize=7)
    ax.axhline(q_stack, color=_OK, linestyle="--", linewidth=1.2)
    ax.annotate(f"series-consistent stack flux {q_stack:,.0f} W/m$^2$",
                xy=(0.02, 0.97), xycoords="axes fraction",
                color=_OK, fontsize=7, ha="left", va="top")
    ax.set_ylabel("q = dT / R  [W/m$^2$]")
    ax.set_xlabel("ply (surface to back)")
    ax.set_title("3. Five bars, one physical flux", fontsize=9)
    _style(ax)

    # ---- Panel 4: sensitivity dq/dT = 1/R ----------------------------------
    ax = axes[1][1]
    sens = [1.0 / rr for rr in r_ply]
    bars = ax.bar(labels, sens, color=_ACCENT, edgecolor="none")
    bars[-1].set_color(_OK)
    for bar, s in zip(bars, sens):
        ax.annotate(f"{s:,.0f}", (bar.get_x() + bar.get_width() / 2, s),
                    ha="center", va="bottom", color=_TEXT, fontsize=7)
    ax.set_ylabel("dq/dT = 1/R  [W/m$^2$/K]")
    ax.set_xlabel("ply (surface to back)")
    ax.set_title("4. Why the thin ply lies: error amplification", fontsize=9)
    _style(ax)

    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(_OUT_PNG, facecolor=_BG)
    plt.close(fig)
    print(f"[explain] peak element {peak}; R_total={r_total:.5f} m2K/W; "
          f"q_stack={q_stack:,.1f} W/m2")
    print("[explain] q_ply = " + ", ".join(f"{q:,.1f}" for q in q_ply))
    print(f"[explain] wrote {_OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
