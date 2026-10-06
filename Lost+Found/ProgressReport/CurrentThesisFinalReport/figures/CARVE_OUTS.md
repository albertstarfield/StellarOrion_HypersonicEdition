# Figure Carve-Outs

This file records figure-related audit decisions that cannot be closed by
regeneration, with the evidence behind each decision. It exists so the
rationale survives independently of commit messages.

Date: 2026-10-06. Scope: thesis directory of StellarOrion Hypersonic Edition.

## 1. Eight runtime field-panel figures (documented carve-out)

Figures: `thermal_map_smooth.png`, `pressure_map_smooth.png`,
`mach_map_smooth_M0_A0.png`, `knudsen_map_smooth_M0_A0.png`,
`velocity_vectors_smooth.png`, `grid_mesh_map_smooth.png`,
`scallop_pocket_temp_smooth_M0_A0.png`, `mesh_statistics_smooth.png`.
All are included at `0.75\textwidth` in chapter 4.

These PNGs have baked text measured at roughly 2 to 4 pt when printed.
The goal requires figure text large enough to read comfortably, taken as
8 pt or more. They cannot be regenerated from this repository, and they
cannot be scaled up to the threshold. Evidence:

1. No generator source exists anywhere in the repository. Searches of
   `stellarorion_program_proc` covered every language (Python, Ada,
   TypeScript, HTML, shell) for the literal file names, for the runtime
   log message `Generating Mesh Plot`, and for `assets/plots`. The only
   hits are runtime log files (`Lost+Found/orion_log.txt`,
   `Lost+Found/irve3_log.txt`) and UI loaders that display the images.
   The code that writes them is not in the repository.
2. No field data is committed. The only surface artifact is a geometry
   profile (`HIAD_custom.surf`, 77 points, no per-node field values).
   The results trees contain time-series CSVs only. Replotting the
   panels from committed data would require inventing the field values,
   which the goal forbids.
3. Scaling cannot fix the text. The baked text occupies about 0.0084 of
   the image width. At `\textwidth` (5.53 in) that prints near 3.4 pt,
   still far below 8 pt, and a wider print than `\textwidth` does not
   fit the page.

The captions and surrounding prose state the numeric content of these
panels in words, so the research content remains readable in the PDF.

## 2. Literal double hyphens in CLI flag tokens (carve-out from no-dash rule)

Eighteen rendered `\texttt{-{}-flag}` tokens are literal command-line
arguments of the documented `run.py` interface, for example
`--validate-only`. They are factual tokens, not typography, so they stay.
Everything else in sources and in the rendered PDF is free of em dashes
and double hyphens. Matplotlib figure text is dash free as well.

## 3. Pending (not carve-outs, tracked work)

- Six imported-artwork figures are under text-size measurement
  (`hiad_design_sensitivity`, `dsmc_algorithm_flowchart`,
  `sutherlandfx`, `Hiad_DesignSpec`, `Spec0`, `RecirculationExample`).
  Each will be kept, widened, redrawn, or carved out after measurement.
- Five diagrams with no generator (`methodology_derivation`,
  `governing_equations`, `software_pipeline`, `literature_review_map`,
  `pinn_architecture`) are queued for redraw as thesis-side scripts.
  These are schematics, so redrawing them invents no data.
