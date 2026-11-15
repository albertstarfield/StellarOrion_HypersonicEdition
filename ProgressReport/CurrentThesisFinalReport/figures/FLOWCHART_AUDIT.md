# Flowchart audit and repair — 2026-11-15

Scope: the three flowcharts in `ProgressReport/CurrentThesisFinalReport/`.

| Figure | Generator | Included in |
|---|---|---|
| `figures/flowchart.png` | `figures/make_flowchart.py` | Chapter 1 (`fig:flowchart_ch1`) |
| `figures/fignew_pipeline.png` | `figures/make_pipeline_figure.py` | Chapter 3 (`fig:optimization_flowchart`) |
| `figures/dsmc_algorithm_flowchart.png` | `figures/make_dsmc_flowchart.py` | Chapter 2 (`fig:dsmc_flowchart`) |

## Defects found

1. **Duplicate branch label.** `make_flowchart.py` drew `"Yes: valid"` twice. The second
   block computed `y_exit2` from `ys[7]` (a process box, not a diamond) minus
   `DIAMOND_H/2`, landing the string in the gap between the GA box and the Data Analysis
   box. OCR of the committed PNG confirmed two occurrences.
2. **Factually wrong run condition.** The simulation box read `Simulate the Geometry in
   Mach 5-6`. The solver configuration is `SIM_MACH : constant Float := 10.29`
   (`stellarorion_program_proc/src/simulation_engine/stellarorion_postprocessing.ads:71`),
   51.8 km, V = 3378 m/s. "Mach 5-6" appears nowhere in the code or the chapters.
3. **Label grammar.** `Various of papers Study`.
4. **Stale docstring.** The module `LAYOUT` block and `CITATIONS` block still described the
   v1 artwork: two decision diamonds, an "Adjustment Needed" loop, no GA stage — the
   opposite of what `build()` draws.
5. **Self-inconsistent console output.** `main()` printed "9 stages, 1 decision diamond"
   while 11 nodes are drawn.
6. **Unverifiable citation in the docstring.** "Plimpton & Gallis (2014). SPARTA. Physics of
   Fluids 26(10), 103005" is not on SPARTA's own publication list
   (https://sparta.github.io/papers.html). Canonical: Plimpton, Moore, Borner, Stagg,
   Koehler, Torczynski & Gallis, *Physics of Fluids* 31, 086101 (2019); the report used in
   `ref.bib` is OSTI 1248702 (2015). Bird's 1994 title was also truncated.
7. **Repeated figure.** Chapter 3 reprinted the Chapter 1 artwork verbatim
   (`figures/flowchart.png` twice in the document, `fig:flowchart` defined in Ch.3),
   although `integrate_figures.py` records the decision to cross-reference instead. The
   reprint landed on a near-empty full page.
8. **Symbol-convention gap.** In the Chapter 3 pipeline, stages 9 ("Survivability check")
   and 10 ("Sanity checks") are pass/fail gates drawn as tinted rectangles with no branch
   edges, while the same figure uses ISO 5807 shapes for the entry/exit stages.

## Repairs applied

- Deleted the duplicate `"Yes: valid"` block.
- `Simulate the Geometry` label → `at Mach 10.29`.
- `Various of papers Study` → `Various Papers Survey`.
- `LAYOUT` and `CITATIONS` rewritten to the v2 behaviour; the withdrawn 2014 citation is
  recorded as withdrawn rather than silently dropped.
- `main()` now prints `11 nodes (2 terminators, 2 parallelograms, 6 processes, 1 diamond)`.
- Chapter 1 caption: "before the post-optimization data-analysis stage", plus a pointer to
  Figure 3.7 for the twelve-stage run, the DSMC-gated loop and the double pass.
- Chapter 3: the figure block was deleted and replaced with cross-references to
  `fig:flowchart_ch1` and `fig:optimization_flowchart`. `\label{fig:flowchart}` no longer
  exists; no dangling reference remains.
- Chapter 3 pipeline caption now states that stages 9 and 10 are gates drawn as tinted
  process boxes.
- `integrate_figures.py` and `make_pipeline_figure.py` docstrings corrected: the artwork
  was **not** removed from the repository, it is the Chapter 1 overview.
- `ref.bib`, `lau2013irve3` note: `W/cm^2` → `W/cm$^{2}$`. The bare caret caused
  `main.bbl:186: Missing $ inserted` and killed the build.

## Verification

- All three generators reproduce byte-identical output before the repair (sha256 match
  with the committed PNGs), and every internal fit guard passes.
- Post-repair `flowchart.png`: sha256 `a89a79b1016857e7fc109333749119623857f9f320ec1cebec4320f5ad9519ef`.
  OCR of the PNG and of PDF page 42 shows exactly one `Yes: valid`, `at Mach 10.29`, and
  `Various Papers Survey`.
- `latexmk -pdf main.tex` → rc = 0, `main.pdf` 235 pages, `main.log` contains **0**
  occurrences of `Warning`, `Overfull` or `Underfull`, 0 undefined references or
  citations, labels stable across passes.
- No duplicate `\label` among the live `.tex` files. The earlier duplicate list was an
  artifact of `.humanize_backup_20261108/` and `.pre_merge_backup_20261109_035445/`, which
  are not compiled.
- Lean axiom test `ProgressReport/Week 19/proofs/flowchart_audit.lean` → rc = 0
  (`before_not_coherent`, `after_coherent`, `repair_is_label_only`,
  `mach_label_now_matches_config`, `mach_label_was_wrong`).

## Open, not changed

- Converting pipeline stages 9 and 10 to diamonds. The figure is height-capped at
  `0.72\textheight` with fit guards on every label; reshaping two nodes would need the
  layout re-tuned and re-measured. The caption now documents the convention instead.
- Chapter 3 states a freestream of Mach 10.29 (matching `SIM_MACH`), while
  `chapter_04_gate.tex` quotes a reference state of 52.069 km / 3101 m/s / Mach 9.46.
  Two different trajectory points are in play; that is a chapter-level consistency
  question, not a flowchart one, and it is untouched here.
