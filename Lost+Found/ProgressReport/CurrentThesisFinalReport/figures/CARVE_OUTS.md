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

## 5. Dead artwork inventory and removal (evidence from `audit_artifacts.py`)

`figures/audit_artifacts.py` was written to close the dead-artwork class in
one pass rather than figure by figure. It reads every `\includegraphics` in the
thesis sources, then reports images on disk that no include names and
generators whose output is not included. Before the cleanup it reported
29 unreferenced images and 1 dead generator. Every one of the 29 names was
checked with a whole-directory `grep -F` over the TeX sources, not only over
the include commands, so no AccSupp `ActualText` or comment reference was
missed: all 29 had zero hits.

Two external consumers were checked before removal and neither reads these
files:

- `stellarorion_program_proc/scripts/render_bo_figures.py` names
  `ccd_response_surface.png` only inside its own docstring, where it explains
  why it does not use that stale figure. The script does not read it.
- `Lost+Found/ProgressReport/Week 16 LaTeX/SOURCES.md` already recorded the
  same class of artwork as stale and excluded
  (`figures/ga_convergence.png`, `figures/ccd_response_surface.png`,
  `Spec1.png`). It is the predecessor decision for this tree and it holds a
  separate `figures` directory.

The 29 removed images are the `week10_*` series, the superseded
`*_smooth_M0_A0` variants that were replaced by the `_smooth` names still in
use, the design studies `Spec1.png`, `machnumberspecirve3.png`,
`heatratespecirve3.png`, `heatRate_HIAD2015_IRVE3.png`,
`accelerationgIRVE3.png`, `reentryaerodynamic.png`, `Scheduling.png`,
`upscaled_3d_mach_smooth_M0_A0.png`, the earlier result figures
`mop_accuracy.png`, `mop_architecture.png`, `pinn_convergence.png`,
`ccd_response_surface.png`, `convergence_residuals_master_smooth.png`, the
placeholder `placeholder.png`, two UI screenshots, and the field panels that
were never included (`thermal_map_smooth_M0_A0.png`,
`pressure_map_smooth_M0_A0.png`, `mach_map_smooth.png`,
`knudsen_map_smooth.png`, `velocity_vectors_smooth_M0_A0.png`,
`residence_time_map_smooth_M0_A0.png`,
`shock_stagnation_profile_smooth.png`).

The one dead generator, `make_convergence_residuals.py`, produced
`convergence_residuals_master_smooth.png`, which no include names. It was
removed with its output. Its historical finding is preserved where it matters:
the printed residual figure is now `fignew_convergence_residuals.png`, produced
by `make_fignew.py` from the verified optimization results, so the empty-plot
defect it documented cannot recur through the surviving path.

After the removal the tool reports 0 dead images and 0 dead generators, and the
eight modules it lists as drawing no figure are the shared helpers by design
(`print_fit.py`, `fig_metrics.py`, `measure_loop_gap.py`, the four probe
tools, and `strip_dashes.py`).

## 6. `fignew_pipeline.png` measured and kept (no carve-out needed)

This is a distinct figure from the chapter 3 `software_pipeline.png` artwork.
It is included in chapter 1 at `width=\textwidth` together with
`height=0.72\textheight` and `keepaspectratio`, so its printed size is limited
by the printed height, not the printed width. Measured by re-running
`make_pipeline_figure.py`: the saved image is 1586 by 2017 px, the fitted
printed height is 6.718 in, which equals `0.72` of the 9.33071 in page text
height, the achieved print scale is 0.999, and the smallest label prints at
8.39 pt. The generator already asserts the 8 pt floor against that
height-limited scale and raises `SystemExit` if it is not met, so the figure
needs no carve-out and no redraw. Its keep-aspectratio include is the reason it
keeps its own height-capped fit loop instead of calling
`print_fit.save_to_print_width`, which fits to width.

## 7. Double hyphens that must remain in source, and why

The goal forbids the two-character sequence formed by U+002D twice from
appearing in any source file. A small set of occurrences cannot be removed,
because the file's purpose is to detect that sequence, so removing it would
leave a checker that reports nothing while appearing to guard everything.

Measured occurrences that remain, by file and line:

- `check_structure.py`: seven regular expressions in `_ALLOWED_DASH`, which
  whitelist the contexts where a doubled hyphen is legitimate, plus the two
  membership tests at lines 166 and 171.
- `check_prose_batch.py`: the search pattern and the message it prints.
- `audit.py`: the count of the `Warning--Class` string emitted by one
  LaTeX build, the search for a run of three hyphens, and the label printed
  for that check.

These 16 occurrences are the whole remainder in the maintained battery.
Everything else in the thesis tree, including every generator under
`figures/`, now measures zero.

### 7.1 The tool that cleans this, and the bug it first contained

`strip_dashes.py` at the thesis root does the cleaning. Its default `prose`
mode rewrites only two kinds of text: comment tokens, and the string tokens
that Python's own parser reports as docstrings. Located by token type rather
than by pattern, it cannot reach an expression.

The first version located decorative text by line number, and it destroyed
seven working regular expressions in `check_structure.py`. The reason is
that a functional string and a decorative comment share a line, in the form
`re.compile(r"--[a-zA-Z]")   # CLI flag: --nose`, so rewriting the line
rewrote the pattern. The rewritten patterns no longer matched what they
were written to match, which would have made the checker report hundreds of
false positives about ordinary hyphens while still appearing to pass.

Two changes prevent a repeat. The rewrite operates on token spans, so a
comment's characters cannot reach the code beside it. And the tool
snapshots every string token that is not a docstring before the rewrite and
compares it afterwards, raising if any of them moved, so a blast radius that
was not measured cannot be written to disk.

`strip_dashes.py` also keeps the earlier whole-line `all` mode for the figure
generators, whose content has been read line by line and contains no search
pattern.

### 7.2 Proof that the cleanup changed no behaviour

The battery was re-run after cleaning its own source. Every number is
identical to the run before: `audit.py` 75 of 75 checks pass,
`check_backrefs.py` 207 of 207 pairs match, `check_structure.py` reports zero
brace imbalance, zero environment mismatch, zero residual em dashes, zero
banned scope terms and zero duplicate labels across 187 labels,
`scan_long_sentences.py` finds zero overlong sentences, and
`check_prose_batch.py` returns PASS with the appendix at 1311 words.
