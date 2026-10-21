"""Draw the through-thickness thermal response of the FTPS layup.

PURPOSE
    The framework's composite F-TPS conduction solver is a per-element
    1-D layered model: every surface element carries its own through-
    thickness temperature profile and its own radiative/conductive
    balance.  The per-ply results are written by the solver to
    ``results/tps_conduction/<run>/tps_step*_profiles.csv`` and
    ``..._layers.csv``; this figure shows them, because the thermal
    chain (convection -> conduction -> re-radiation) is otherwise not
    visible anywhere in the thesis.

AXIOMS
    A1. Every number comes from the solver's own CSV output; nothing is
        recomputed here.
    A2. Depth is measured from the hot (outer) surface into the stack.
    A3. The two runs compared are the reference geometry and the
        optimised-geometry run, both at their final step.

THEORIES
    T1. A through-thickness profile is a monotone cooling curve because
        the stack is a series resistance: temperature falls with depth.
    T2. The balance columns of the element export are what closes the
        convection/conduction/re-radiation budget, so the figure reports
        them next to the profile.

CITATIONS
    [stellarorion_physics.ads Composite F-TPS conduction] -- the solver.
    [results/tps_conduction] -- the per-ply exports.
    [Matplotlib 3.11.2] -- https://matplotlib.org/stable/
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parent.parent.parent.parent
TPS_ROOT = REPO_ROOT / "stellarorion_program_proc/results/tps_conduction"
INK = "#222222"
CB = ["#004488", "#DDAA33", "#BB5566", "#228833"]


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV export into a list of dictionaries.

    Parameters
    ----------
    path : Path
        CSV file to read.

    Returns
    -------
    list of dict
        The parsed rows.

    Raises
    ------
    FileNotFoundError
        If the export is missing.
    """
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def profile_of(rows: list[dict[str, str]], element: str):
    """Return the (depth, temperature) profile of one element.

    Parameters
    ----------
    rows : list of dict
        Profile rows.
    element : str
        Element identifier.

    Returns
    -------
    tuple of list
        Depths in metres and temperatures in kelvin.
    """
    sel = [r for r in rows if r["element"] == element]
    sel.sort(key=lambda r: float(r["depth_m"]))
    return (
        [float(r["depth_m"]) for r in sel],
        [float(r["temp_K"]) for r in sel],
    )


def main() -> int:
    """Render the two-panel TPS figure.

    Returns
    -------
    int
        0 when the figure is written, 1 on any failure.
    """
    try:
        ref_dir = TPS_ROOT / "00_reference"
        profiles = read_rows(ref_dir / "tps_step2200_profiles.csv")
        layers = read_rows(ref_dir / "tps_step2200_layers.csv")
        elements = read_rows(ref_dir / "tps_step2200_elements.csv")
        opt_dir = TPS_ROOT / "03_opt_geometry"
        opt_layers = read_rows(opt_dir / "tps_step2200_layers.csv")

        element_ids = sorted({r["element"] for r in profiles}, key=int)
        picked = [element_ids[i] for i in
                  (0, len(element_ids) // 4, len(element_ids) // 2,
                   3 * len(element_ids) // 4, len(element_ids) - 1)]

        fig, (ax_profile, ax_layers) = plt.subplots(1, 2, figsize=(7.6, 3.2))
        for index, element in enumerate(picked):
            depth, temp = profile_of(profiles, element)
            ax_profile.plot(
                [d * 1000.0 for d in depth], temp,
                lw=1.5, color=CB[index % len(CB)],
                label=f"element {element}",
            )
        ax_profile.set_xlabel("depth into the layup [mm]")
        ax_profile.set_ylabel("temperature [K]")
        ax_profile.set_title(
            "a) through-thickness profile, reference run\n"
            "(five surface elements, final step)", fontsize=9.5)
        ax_profile.legend(fontsize=7.5, frameon=False)
        ax_profile.grid(True, color="#DDDDDD", lw=0.6)
        ax_profile.set_axisbelow(True)

        def layer_series(rows: list[dict[str, str]], run: str):
            sel = [r for r in rows if r["element"] == element_ids[0]]
            sel.sort(key=lambda r: int(r["ply"]))
            return (
                [float(r["depth_m"]) * 1000.0 for r in sel],
                [float(r["temp_K"]) for r in sel],
                [r["ply_name"] for r in sel],
            )

        depth_ref, temp_ref, names = layer_series(layers, "reference")
        depth_opt, temp_opt, _ = layer_series(opt_layers, "optimised")
        ax_layers.step(depth_ref, temp_ref, where="post", lw=1.6,
                       color=CB[0], label="reference geometry")
        ax_layers.step(depth_opt, temp_opt, where="post", lw=1.6,
                       color=CB[1], label="optimised geometry")
        ax_layers.set_xlabel("depth into the layup [mm]")
        ax_layers.set_ylabel("temperature [K]")
        ax_layers.set_title(
            "b) per-ply temperatures of the first element\n"
            f"({len(names)} plies, final step)", fontsize=9.5)
        ax_layers.legend(fontsize=8, frameon=False)
        ax_layers.grid(True, color="#DDDDDD", lw=0.6)
        ax_layers.set_axisbelow(True)

        first = elements[0]
        ax_layers.text(
            0.02, 0.04,
            "q_conv = {qc:.3g} W/m2, q_cond = {k:.3g} W/m2,\n"
            "q_rad = {r:.3g} W/m2, q_lateral = {l:.3g} W/m2".format(
                qc=float(first["q_conv_Wm2"]), k=float(first["q_cond_Wm2"]),
                r=float(first["q_rad_Wm2"]), l=float(first["q_lateral_Wm2"])),
            transform=ax_layers.transAxes, fontsize=7.5, color=INK,
            va="bottom")

        fig.tight_layout()
        out = FIG_DIR / "tps_ply_conduction.png"
        fig.savefig(out, dpi=300)
        plt.close(fig)
        print(f"wrote {out.name} ({len(element_ids)} elements, "
              f"{len(names)} plies)")
    except Exception as exc:  # noqa: BLE001 -- the generator reports loudly
        print(f"TPS figure failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
