# Figures for the Week 17 narrative scaffold

**Purpose:** record which visuals the scaffold asks for, where the candidate
files live, and the rule that governs how a figure earns its place.

**Author:** generated for Wahyu Suryo Samudro (owner), ITB, Week 17 2026.

**Date:** 2026-10-21.

---

## 1. The three visual slots

The owner's structure ends with a note that asks for three visuals:

| Slot | Slide title | What it must show | Status |
|---|---|---|---|
| Plot A | `PLACEHOLDER PLOT A: CFD REQUIRED` | The CFD case. | Not chosen yet. |
| Plot B | `PLACEHOLDER PLOT B: OPTIMIZED REQUIRED` | The optimized case. | Not chosen yet. |
| Reference | `PLACEHOLDER REFERENCE: REFERENCE PAPER` | The reference paper that the point-6 narration cites. | Not chosen yet. |

These three slides are placeholders, not empty ones. Each carries the
instruction in its slot box so the requirement is visible while the deck is
being shaped, and the owner's note is reproduced verbatim in
`scaffold.json` under `owner_structure`.

## 2. Candidate sources already in the repository

Read-only reconnaissance of `stellarorion_program_proc/results/` found these
files that could serve the slots. Nothing has been copied into this folder.

| Slot | Candidate file |
|---|---|
| Plot A (CFD) | `stellarorion_program_proc/results/99_shared/cfd_fields/grid_mesh_map_smooth_03_opt_geometry_step_1000.png` |
| Plot B (Optimized) | `stellarorion_program_proc/results/99_shared/geometry/optimization_comparison.png`, `stellarorion_program_proc/results/99_shared/geometry/surf_profile_check.png` |

A caveat that must travel with any citation of the optimized run: the run
folder `03_opt_geometry` owns only one artefact (a video). There are no
thermal, Mach or Knudsen field maps for the optimized run, so any figure that
looks like a field comparison cannot be sourced from it. `results/README.md`
is the auto-generated guide that states which run owns which plot, and
`results/RUNS.md` is the run index; `00_reference` is the latest reference
and the default posture.

## 3. How a figure is inserted

There are two routes, and both are supported.

**Route 1, inside the tool.** The generator draws the slot box as a frosted
white glass pill with the slot body in it. A filled slot replaces that pill
with a picture, centred, scaled to keep its aspect ratio, the way
`slide.add_image(...)` in EasyPPTX does it. The picture file path is added to
the frame's entry in `scaffold.json`, so the figure is declared in the
specification rather than hidden in the code.

**Route 2, inside PowerPoint.** The owner opens `narrative_scaffold.pptx`,
deletes the slot box on the slide in question, and inserts the picture
directly. The tool must not undo that work: update mode only ever refreshes
the slot box text and the slide chrome, never removes or replaces shapes it
did not create.

## 4. The provenance rule

Every figure in the final deck carries a source. The convention already used
in the Week 17 Beamer deck is a caption that ends with
`Source: <path relative to the repository root>`, with underscores escaped
for LaTeX there and left plain in PowerPoint here.

A figure without a source path does not go into the deck. If the provenance
of a candidate image cannot be established from `results/README.md`,
`results/RUNS.md` or the file itself, the figure is not used.

## 5. Constraints that carry over from the Beamer deck

* **Aspect ratio.** The slides are 16:9 at `12192000 x 6858000` EMU. A figure
  that is wider than the content area will be scaled down, so a plot whose
  detail matters should be wide rather than tall.
* **Contrast.** The deck body colour is Navy on a near-white frosted glass pill
  that sits on a sky running from near white at the top to deep navy at the
  bottom, so a figure must be legible against the part of the sky it lands on.
  A plot with a pale background loses its edges against the glass; a plot with
  a dark background loses them against the lower sky. The floating frosted
  title band occupies the top of every placeholder slide and the picture area
  starts below it.
* **No decorative figures.** A figure that carries no number and no source is
  a slide filler. The Week 17 deck deliberately plots everything it states.

## 6. The sky picture also lives here

`figures/sky_<signature>.png` is the frosted-glass background of every slide.
It is a build artifact: `sky_background.py` rebuilds it from the four palette
colours in `scaffold.json`, and the signature in its name is a hash of those
colours and of the sky geometry, so the file is stable across runs and a
change of palette produces a new file rather than a stale one. The folder
`.gitignore` excludes it for that reason.

It is kept in this folder because it is a picture, and because a figure that
is inserted later must be able to sit on the same sky the generator expects.

## 7. The thesis graphics imported for the RECALL block

The RECALL block was filled from the thesis, and five of its slides
carry a graphic that was imported out of, or regenerated out of,
`Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/`. The copies live
in this folder with a `thesis_` prefix, so the origin stays visible and a file
of the same name can never be confused with one of the run outputs.

| Slide | Imported file | Thesis origin | What it shows |
|---|---|---|---|
| `BACKGROUND OVERVIEW` | `thesis_HIADsDeployed.png` | Chapter I (also Chapter II) | The deployed inflatable HIAD, the inflated toroidal stack that replaces a rigid TPS on the vehicle. |
| `OBJECTIVE AND RESEARCH SCOPE` | `thesis_hiad_design_spec.png` | Chapter III, the vehicle specification drawing `Hiad_DesignSpec.png` | The HIAD as an overview: the inflatable aeroshell against the rigid body it replaces, labelled 15 m inflatable and 4.57 m rigid. MOVED HERE ON 2026-10-26: the meridional half-section that used to sit on this slide went to the methodology slide below, because it answers which shape is being tested. |
| `METHODOLOGY: THE SHAPE UNDER TEST` | `thesis_hiad_parametric_cross_section.png` | Chapter II | The meridional half-section of the HIAD bladder layout: the nose arc tangent to the cone generator, the six tori T1 to T6, R_N 0.55 m, r_tor 0.135 m, half-cone 60 degrees, R_max 1.90 m, L_body 1.269 m. REFRESHED ON 2026-10-26: the deck copy was the earlier measured reconstruction whose fitted skin line self-intersected, so it was replaced by the figure `figures/make_hiad_parametric_cross_section.py` writes; the backups of both the old picture and the old caption are `tools/thesis_hiad_parametric_cross_section_before_fix.png` and `tools/scaffold_before_slide5_caption.json`. |
| `METHODOLOGY: THE DESIGN SPACE` | `thesis_hiad_design_sensitivity.png` | `hiad_design_sensitivity.png` | The three design-variable relations: toroid count against diameter against the 3.0 m target, cone angle against nose radius, toroid count against torus radius. |
| `METHODOLOGY: THE COST FUNCTION` | `thesis_ga_convergence.png` | `ga_convergence.png` | The generation-best composite cost of the recorded campaign over 38 generations and 1900 evaluations. |
| `METHODOLOGY: THE GENETIC ALGORITHM` | `thesis_ga_design_trajectory.png` | `ga_design_trajectory.png` | The generation-best design path through the design box, with the baseline and optimum values of the three variables. |
| `METHODOLOGY: DOUBLE PASS AND THE GATE` | `thesis_fignew_gate_comparison.png` |
| `GOVERNING EQUATION: THE SHAPE` | `thesis_equation_shape.png` | Typeset in this folder | The two equations that turn the design vector into the geometry of the vehicle. |
| `GOVERNING EQUATION: THE SOLVER` | `thesis_equation_setup.png` | Typeset in this folder | The equation the particle solver answers, and the cross-section it scatters with. |
| `GOVERNING EQUATION: THE MESH` | `thesis_equation_mesh.png` | Typeset in this folder | The relation that decides how small a cell of the grid may be. |
| `GOVERNING EQUATION: THE CONVERGENCE` | `thesis_equation_convergence.png` | Typeset in this folder | The criterion that decides when a particle run is statistically converged. |
| `GOVERNING EQUATION: THE CONVECTION` | `thesis_equation_convection.png` | Typeset in this folder | The correlation that carries the convective load of every candidate. |
| `GOVERNING EQUATION: THE CONDUCTION` | `thesis_equation_conduction.png` | Typeset in this folder | The balance that splits the arriving heat between the stack and the surface. |
| `GOVERNING EQUATION: THE RADIATION` | `thesis_equation_radiation.png` | Typeset in this folder | The equilibrium that sets the temperature of the hot face of the vehicle. | `fignew_gate_comparison.png` | The three heat loads the gate compares, against the acceptance threshold. Not included in the thesis text. |
| `METHODOLOGY AND REASONING` | `thesis_software_pipeline.png` | Chapter III, Figure 3.3 | The StellarOrion engine pipeline: geometry and flight conditions feed the Ada core engine, the SPARTA DSMC solver and the Ada/SPARK one-dimensional thermal solver, and the genetic algorithm writes the next geometry back. The thesis redrew this figure so that its labels print at eight points or more, and the redrawing added the Ada/SPARK thermal solver box, so the caption in the deck follows the new artwork. |
| `GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW` | `thesis_flowchart_halves.png` | Chapter III, Figure 3.4 | The eleven-stage research workflow of the thesis with its two decision loops. The file is the thesis flowchart regenerated by `figures/make_flowchart.py` and then cut into its two halves, because the flowchart is 1760 by 3600 pixels and would be unreadable whole. |
| `PREVIOUS ISSUE 1: THE HEAT FLUX WAS UNDEFINED` | `thesis_fignew_scalloped_vs_smooth_heatflux.png` | Thesis figure archive | The heat flux of the smooth and the scalloped body over the particle-time step, as the per-element mean and as the peak cell: the two candidate channels of the heat-flux definition, which do not rank the two bodies the same way. |

The fourth picture is in the thesis figure archive but is not placed in any
thesis chapter, so its provenance line says so rather than naming a chapter
it does not belong to. Every picture keeps the provenance of the file it came
from in the line under its caption, and the generator refuses to build a deck
whose picture is missing, so a slide can never silently lose its graphic.

A thesis figure is drawn for the text width of a printed page, so it carries
small type. The panel that holds it is therefore as large as the slide allows
(6.06 in wide by 3.54 in tall), which is why these graphics are legible on a
projected slide and not merely present. The heat-flux figure on the first
issue slide sits in a shorter panel, because the band of cards that tells the
issue takes the rest of the content area.

## 8. The CFD verification figures imported for the methodology block

The methodology block of the deck is a sequence of figure frames, so every
slide of it carries the picture of the physics it describes. The files were
copied out of `CurrentThesisFinalReport/figures/` and the thesis itself was
not touched. Two of them were changed in this folder, and both changes are
recorded here.

| Slide | File in this folder | Thesis origin | What it shows |
|---|---|---|---|
| `METHODOLOGY: THE SIMULATION SETUP` | `thesis_grid_mesh_map_smooth.png` | Chapter IV, Figure `fig:grid_mesh` | The uniform Cartesian grid of the reference run, cut by the vehicle body, with the instrumented surface elements T1 to T7(S). The runs build one grid with `create_grid 139 139 1` and never call `fix adapt_grid`, so nothing is refined at run time; the title printed inside the picture still reads "SPARTA Adaptive Mesh Grid" because it came from an older render of the figure. |
| `METHODOLOGY: THE GRID INDEPENDENCE` | `thesis_sop_grid_independence.png` | The SOP verification figure of the thesis | The three-level refinement of the peak surface flux and the gate on the finest pair against the 10 percent tolerance. REBUILT IN THIS FOLDER: the thesis figure is 2320 by 980 pixels and its annotation block was drawn on top of the x-axis label of the left panel, so the generator was copied to `.tmp/sop_figures/`, its canvas was made taller and the figure was written again with the annotation in a band of its own. The thesis copy is untouched. |
| `METHODOLOGY: THE SOLVER CONVERGENCE` | `thesis_convergence_residuals.png` | Chapter IV, Figure `fig:convergence` | The normalised residual of the drag coefficient, the lift coefficient and the per-element heat-flux average against the particle-time step. |
| `METHODOLOGY: THE CONVECTION CHANNEL` | `thesis_sutton_graves_parametric.png` | Chapter III | The Sutton-Graves correlation against the freestream velocity and against the nose radius, with the IRVE-3 design point called out. |
| `METHODOLOGY: THE CONDUCTION CHANNEL` | `thesis_tps_ply_conduction.png` | Chapter IV | The through-thickness temperature profile of five surface elements and the per-ply temperatures of the first element. |
| `METHODOLOGY: THE RE-RADIATION CHANNEL` | `thesis_tps_ply_stack_temperature.png` | Thesis figure archive | The through-thickness temperature heatmap of the 5-ply stack with the per-ply table of the measured temperatures and the margin of every ply. CROPPED IN THIS FOLDER: the footnote band of the thesis figure carries two overprinted lines that read as a smudge at slide size, so the bottom 84 pixels of 1240 were cut. The footnote is kept in the thesis figure. |
| `METHODOLOGY: THE OPTIMIZATION FLOWCHART` | `thesis_optimization_flowchart.png` | `CurrentThesisFinalReport/figures/fignew_pipeline.png` | The twelve stage validation pipeline of the engine and, under it, the geometry optimization loop: design space, the Bayesian step, the cost function J(x), the DSMC re-simulation and the accept test on q against Q_target, with the rejection resampling the design space. COPIED VERBATIM ON REQUEST on 2026-10-26: the owner asked for this flowchart as it stands, so the loop row is shown exactly as the thesis figure draws it, including the boxes that the previous-issue-3 slide describes as removed from the current method. The file is byte-identical to the thesis picture, sha256 e82fd087f68f7014. |

Two further files of the same family are in this folder and are not placed on
a slide: `thesis_sop_mesh_quality_record.png` (the mesh gates and the cut-cell
census; the caption of the thesis figure is truncated by its own canvas edge)
and `thesis_sop_dsmc_stationarity.png` (the particle census and the stationarity
indicator; its numbers are the ones the convergence slide quotes).
