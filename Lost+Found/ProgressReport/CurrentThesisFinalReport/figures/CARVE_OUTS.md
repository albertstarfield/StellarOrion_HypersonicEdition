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

- Six imported-artwork figures: measured, decisions recorded in
  section 4 below (`Spec0` still needs a label-region look).
- Five diagrams with no generator (`methodology_derivation`,
  `governing_equations`, `software_pipeline`, `literature_review_map`,
  `pinn_architecture`) are queued for redraw as thesis-side scripts.
  These are schematics, so redrawing them invents no data. A sixth
  redraw candidate, `dsmc_algorithm_flowchart.png`, is covered in
  section 4.

## 4. Imported-artwork measurement results and decisions

Measured with effective-point size = (smallest text pixels / image
width pixels) printed width 72 / 0.70 cap ratio. Printed widths come
from each `\includegraphics` fraction of the 5.53 in text width.

| Figure | Effective pt | Needed width for 8 pt | Decision |
|---|---|---|---|
| `Hiad_DesignSpec.png` | 12.09 | 2.40 in | Kept as is |
| `Spec0.png` | 4.03 | 6.24 in | Pending label-region check |
| `dsmc_algorithm_flowchart.png` | 3.62 | 10.99 in | Redraw, spec queued |
| `sutherlandfx.png` | 3.52 | 6.33 in | Carve-out |
| `hiad_design_sensitivity.png` | 2.90 | 14.48 in | Carve-out |
| `RecirculationExample.jpeg` | 2.02 | 6.63 in | Carve-out |

Carve-out evidence:

- `hiad_design_sensitivity.png`: no generator, no sensitivity data
  anywhere in the repository (no sensitivity-named artifact outside a
  virtualenv, `run.py` has no sensitivity feature, the only matches are
  interactive HTML reports without plottable values). Rewidening cannot
  help: 14.48 in would be needed against a 5.53 in text width, and the
  panel titles and axis labels are black on a dark navy background,
  which is invisible in print regardless of size. Regenerating would
  require inventing the sensitivity values, which the goal forbids.
- `sutherlandfx.png`: a scanned equation image with no source or data
  in the repository; 6.33 in would be needed against 5.53 in, so
  widening cannot reach 8 pt either.
- `RecirculationExample.jpeg`: native resolution about 204 dpi with
  annotations unreadable even at ten times zoom, and no higher
  resolution original exists in the repository.
- `dsmc_algorithm_flowchart.png`: no generator anywhere in the
  repository; it is a schematic, so a thesis-side redraw script
  invents no data. Redraw spec tracked in `REDRAW_SPECS.md`.
- `Hiad_DesignSpec.png`: clears 8 pt with margin at its current
  include width, so no action.
- `Spec0.png`: the `T7` label renders about half the size of the
  `T1` to `T6` labels and some left-edge labels are clipped; a
  surgical image fix or redraw decision remains open.
