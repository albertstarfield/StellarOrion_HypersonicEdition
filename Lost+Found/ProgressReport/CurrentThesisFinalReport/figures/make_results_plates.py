"""Build the supporting-evidence plates for Chapter 4 from the results tree.

PURPOSE
    Chapter 4 described the flight-dynamics, surface-heat-flux, geometry and
    uncertainty evidence in prose while showing only single-snapshot figures.
    These plates put that evidence in front of the reader by REUSING the plots
    the program already wrote under
    ``stellarorion_program_proc/results/`` instead of recomputing anything.
    Where a plot genuinely does not exist in the tree, an explicit placeholder
    is produced rather than a silent omission.

AXIOMS
    A1. A plot file under ``results/`` is the program's own record of the run
        it names; reusing it verbatim cannot disagree with the thesis numbers.
    A2. The tree has no grid-independence figure and no surface-pressure
        distribution figure (verified by exhaustive listing); those two are
        therefore placeholders and are labelled as such, never simulated.
    A3. A missing source file raises, so a plate can never silently contain an
        empty cell where a result should be.
    A4. ``grid_mesh_map_smooth_00_reference_step_<n>.png`` uses an underscore
        before the step number; ``vtu_heatflux_vs_x_step<n>.png`` does not.

THEORIES
    T1. One plate per evidence type, with the reference and the optimised tree
        in separate columns, lets the reader compare across a row.
    T2. A caption line under each cell, carrying the exact source filename,
        makes the provenance auditable without reading the code.
    T3. A placeholder that states what is missing and which command would
        produce it is honest; an empty gap or a fabricated plot is not.

APPLICATIONS
    Writes ten PNGs into ``figures/`` for the new Chapter 4 section.

CITATIONS
    [1] stellarorion_program_proc/results/README.md - tree conventions.
    [2] stellarorion_program_proc/results/RUNS.md - run provenance.
    [3] Matplotlib Axes.imshow documentation, aspect='auto'.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import image as mpimg  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parent.parent.parent.parent
RES = REPO_ROOT / "stellarorion_program_proc" / "results"

def _wrap(txt: str, width: int = 110) -> str:
    """Wrap each paragraph of ``txt`` so that no line overruns the canvas.

    WHY: at 6.2 pt on a 6.0 in plate only about 127 characters fit on one
    line, so a long provenance sentence used to be clipped at the right edge.
    """
    return "\n".join(line for para in txt.split("\n")
                     for line in textwrap.wrap(para, width=width))

INK = "#222222"
GREY = "#555555"


def load(rel: str):
    """Return the RGB array of ``results/<rel>``.

    AXIOM A3: a missing source raises FileNotFoundError.
    """
    path = RES / rel
    if not path.is_file():
        raise FileNotFoundError(f"source plot missing: {path}")
    return mpimg.imread(path)


def plate(out_name: str, rows: list[list[tuple[str, str, str]]], *,
          figsize: tuple[float, float], suptitle: str, footer: str,
          col_titles: list[str] | None = None,
          row_titles: list[str] | None = None,
          top: float = 0.945, bottom: float = 0.115,
          wspace: float = 0.035, hspace: float = 0.16) -> None:
    """Render a grid of reused panels with provenance captions.

    Parameters:
        out_name: file name written into ``figures/``.
        rows: one list per row of ``(relative_path, cell_caption, panel_tag)``.
        figsize: figure size in inches.
        suptitle: figure title.
        footer: provenance and numbers, printed under the grid.
        col_titles: optional captions above each column.
        row_titles: optional captions left of each row.

    Raises:
        FileNotFoundError when any listed panel is absent (AXIOM A3).
    """
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(n_rows, n_cols, left=0.015, right=0.995, top=top,
                          bottom=bottom, wspace=wspace, hspace=hspace)

    for r, row in enumerate(rows):
        for c, (rel, caption, tag) in enumerate(row):
            ax = fig.add_subplot(gs[r, c])
            ax.imshow(load(rel), aspect="auto", interpolation="lanczos")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#BBBBBB")
                spine.set_linewidth(0.6)
            #  WHY the tag is drawn inside the panel corner: the cell caption
            #  alone does not tell the reader which tree a column belongs to
            #  when a row mixes both, and (a)/(b) tags are what the prose cites.
            if tag:
                ax.text(0.008, 0.985, tag, transform=ax.transAxes, ha="left",
                        va="top", fontsize=7.2, fontweight="bold", color=INK,
                        bbox=dict(facecolor="white", edgecolor="none", pad=1.2,
                                  alpha=0.9))
        if caption:
                ax.text(0.5, -0.055, caption, transform=ax.transAxes, ha="center",
                        va="top", fontsize=6.6, color=GREY)

    if col_titles:
        for c, title in enumerate(col_titles):
            x = 0.015 + (c + 0.5) * (0.980 / n_cols)
            fig.text(x, top + 0.026, title, ha="center", va="bottom",
                     fontsize=8.4, color=INK)
    if row_titles:
        for r, title in enumerate(row_titles):
            y = top - (r + 0.5) * ((top - bottom) / n_rows)
            fig.text(0.004, y, title, ha="center", va="center", rotation=90,
                     fontsize=6.8, color=INK)

    fig.text(0.5, 0.994, suptitle, ha="center", va="top", fontsize=9.4,
             color=INK)
    fig.text(0.015, 0.008, _wrap(footer), ha="left", va="bottom", fontsize=6.2,
             color="#333333", linespacing=1.4)
    fig.savefig(FIG_DIR / out_name, dpi=300, facecolor="white")
    plt.close(fig)
    print(f"wrote {out_name}")


def placeholder(out_name: str, title: str, lines: list[str], *,
                figsize: tuple[float, float] = (6.0, 2.6)) -> None:
    """Render an explicit missing-data placeholder.

    AXIOM A2: this is drawn ONLY for evidence the tree does not contain, and
    it says so in the figure itself.
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0.03, 0.06, 0.94, 0.80])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#F4F4F4")
    for spine in ax.spines.values():
        spine.set_color("#888888")
        spine.set_linewidth(1.0)
        spine.set_linestyle((0, (4, 3)))
    ax.text(0.5, 0.78, "FIGURE NOT AVAILABLE IN results/", ha="center",
            va="center", fontsize=10.0, fontweight="bold", color="#8A2B2B")
    ax.text(0.5, 0.60, title, ha="center", va="center", fontsize=8.6,
            color=INK)
    ax.text(0.5, 0.30, "\n".join(lines), ha="center", va="center",
            fontsize=7.2, color="#333333", linespacing=1.6)
    fig.savefig(FIG_DIR / out_name, dpi=300, facecolor="white")
    plt.close(fig)
    print(f"wrote {out_name}")


def main() -> int:
    """Build all plates and return a process status."""
    ref = "00_reference/plots/"
    r2 = "validation_optimized_round2/plots/"

    plate(
        "flight_history_panel.png",
        [
            [(ref + "cd_vs_step.png", "cd_vs_step.png", "(a1)"),
             (r2 + "cd_vs_step.png", "cd_vs_step.png", "(a2)")],
            [(ref + "drag_sum_N_vs_step.png", "drag_sum_N_vs_step.png", "(b1)"),
             (r2 + "drag_sum_N_vs_step.png", "drag_sum_N_vs_step.png", "(b2)")],
            [(ref + "heat_load_jcm2_vs_step.png", "heat_load_jcm2_vs_step.png", "(c1)"),
             (r2 + "heat_load_jcm2_vs_step.png", "heat_load_jcm2_vs_step.png", "(c2)")],
            [(ref + "g_load_vs_step.png", "g_load_vs_step.png", "(d1)"),
             (r2 + "g_load_vs_step.png", "g_load_vs_step.png", "(d2)")],
        ],
        figsize=(6.0, 8.1),
        suptitle="Integrated flight history of the reference and of the optimised topology",
        col_titles=["validation reference (00_reference)",
                    "optimised topology (validation_optimized_round2)"],
        footer=("Reused verbatim from results/00_reference/plots/ (left) and "
                "results/validation_optimized_round2/plots/ (right); no simulation was re-run. "
                "Rows: (a) drag coefficient, (b) total drag force, (c) total heat load, "
                "(d) deceleration load."),
        bottom=0.100,
        top=0.900,
    )

    plate(
        "heatflux_vs_x_panel.png",
        [[
            (ref + "vtu_heatflux_vs_x_step100.png", "", "(a)"),
            (ref + "vtu_heatflux_vs_x_step1000.png", "", "(b)"),
            (ref + "vtu_heatflux_vs_x_step2200.png", "", "(c)"),
        ]],
        #  WHY no per-panel file captions: at three panels across a 6 in canvas
        #  the filenames collided with the footer and with each other, and the
        #  footer already names the source pattern and the three steps.
        figsize=(6.0, 3.55),
        suptitle="Surface heat flux along the meridian",
        footer=("Reused verbatim from results/00_reference/plots/vtu_heatflux_vs_x_step<n>.png: "
                "steps 100, 1000 and 2200. The shoulder carries the maximum and the aft face the "
                "minimum, which is why the TPS ply stack is graded rather than uniform. No curve is "
                "rescaled or edited."),
        bottom=0.255, hspace=0.05,
    )

    plate(
        "field_development_strip.png",
        [
            [
                ("99_shared/cfd_fields/grid_mesh_map_smooth_00_reference_step_0.png", "", ""),
                ("99_shared/cfd_fields/grid_mesh_map_smooth_00_reference_step_500.png", "", ""),
            ],
            [
                ("99_shared/cfd_fields/grid_mesh_map_smooth_00_reference_step_1500.png", "", ""),
                ("99_shared/cfd_fields/grid_mesh_map_smooth_00_reference_step_2200.png", "", ""),
            ],
        ],
        #  WHY a 2x2 grid instead of one row of four: at four panels across, each
        #  panel was 1.5 in wide, so its internal contours, axes and colour bar
        #  were unreadable in print, and the suptitle overlapped the panel tops.
        #  Two panels per row double the printed size of every field and let the
        #  suptitle clear the grid.
        figsize=(6.0, 3.60),
        suptitle="Sampling of the reference case: cells holding at least ten particles",
        footer=("Reused verbatim from results/99_shared/cfd_fields/grid_mesh_map_smooth_00_reference_step_<n>.png "
                "(149 archived steps), at steps 0, 500, 1500 and 2200 read left to right, top to bottom. "
                "The mesh and the two body outlines are identical in all four panels; what changes is "
                "the annotated count of cells holding at least ten DSMC particles (18879, 18036, "
                "16585, 16349), so the panels show the sampling filling the domain rather than a "
                "change of flow state."),
        top=0.880, bottom=0.150, hspace=0.10,
    )

    plate(
        "geometry_3d_plate.png",
        [[
            ("99_shared/geometry/irve3_validation_3d_4views.png", "", ""),
            ("99_shared/geometry/optimized_topology_3d_4views.png", "", ""),
        ]],
        figsize=(6.0, 3.55),
        suptitle="Three-dimensional geometry, four views",
        footer=("Reused verbatim from results/99_shared/geometry/. This is the only three-dimensional view of "
                "the bodies in the thesis; Figure 4.14 gives the\nmeridional section and the envelope difference, "
                "and this plate shows the same geometry in the round."),
        bottom=0.145, hspace=0.05,
    )

    plate(
        "survivability_panel.png",
        [[
            (ref + "survivability_assessment.png", "survivability_assessment.png", "(a)"),
            (ref + "T_surface_vs_step.png", "T_surface_vs_step.png", "(b)"),
        ]],
        figsize=(6.0, 2.55),
        suptitle="Thermal survivability assessment of the reference TPS",
        footer=("Reused verbatim from results/00_reference/plots/. (a) compares the computed surface temperature "
                "with the material limits; (b) is the surface\ntemperature history. Both exist only for the "
                "reference tree - the round-2 optimised tree has no T-history output, which is stated in "
                "Section 4.15 rather than implied."),
        bottom=0.175, hspace=0.05,
    )

    plate(
        "ccd_sensitivity_panel.png",
        [[
            ("99_shared/bo_figures/ga_ccd_design.png", "ga_ccd_design.png", "(a)"),
            ("99_shared/bo_figures/ga_ccd_sensitivity.png", "ga_ccd_sensitivity.png", "(b)"),
        ]],
        figsize=(6.0, 2.55),
        suptitle="Central-composite design and parameter sensitivity of the GA objective",
        footer=("Reused verbatim from results/99_shared/bo_figures/. (a) is the CCD sample layout in the three "
                "design variables; (b) is the sensitivity of the\ncomposite cost to each variable, which is why "
                "the torus radius moved 33 % while the half-cone angle moved 2.3 %."),
        bottom=0.175, hspace=0.05,
    )

    plate(
        "kriging_denoise_panel.png",
        [[
            ("99_shared/kriging/kriging_denoise_step100.png", "kriging_denoise_step100.png", "(a)"),
            ("99_shared/kriging/kriging_noise_reduction_step100.png", "kriging_noise_reduction_step100.png", "(b)"),
        ]],
        figsize=(6.0, 2.55),
        suptitle="DSMC stochastic noise and its kriging reduction",
        footer=("Reused verbatim from results/99_shared/kriging/ (step 100 shown; steps 0, 200 and 1000 are also "
                "archived). This is the evidence behind the\nclaim that the surface fields are noisy at the "
                "sampled state and that the optimisation used a smoothed surrogate."),
        bottom=0.175, hspace=0.05,
    )

    plate(
        "morphing_geometry_panel.png",
        [
            [("validation_optimized_round2/plots/geom_diameter_m_vs_step.png",
              "", "(a)"),
             ("validation_optimized_round2/plots/geom_nose_radius_m_vs_step.png",
              "", "(b)")],
            [("validation_optimized_round2/plots/geom_toroid_radius_m_vs_step.png",
              "", "(c)"),
             ("validation_optimized_round2/plots/geom_angle_deg_vs_step.png",
              "", "(d)")],
        ],
        figsize=(6.0, 4.2),
        suptitle="Shape morphing along the round-2 trajectory",
        footer=("Reused verbatim from results/validation_optimized_round2/plots/. The four design variables are "
                "logged at every step, so the geometric change reported in Section 4.14 is traceable step by "
                "step rather than quoted at two endpoints."),
        bottom=0.170, hspace=0.12,
    )

    placeholder(
        "placeholder_grid_independence.png",
        "Grid-independence of the integrated heat load Q against refinement level",
        ["results/grid_independence/level_1, level_2 and level_3 contain raw solver output only.",
         "No plot of Q (or C_d) against refinement level exists anywhere in the results tree,",
         "so the grid sensitivity claimed in Table 4.2 cannot be shown from an existing figure."],
        figsize=(6.0, 2.3),
    )

    placeholder(
        "placeholder_surface_pressure.png",
        "Surface pressure distribution along the body meridian",
        ["The results tree archives surface heat flux against x (vtu_heatflux_vs_x_step<n>.png)",
         "and the field maps, but no plot of surface pressure against x at any step.",
         "The pressure field is therefore described from Figure 4.2 only."],
        figsize=(6.0, 2.3),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
