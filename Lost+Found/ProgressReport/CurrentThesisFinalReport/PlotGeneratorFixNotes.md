# Plot Generator Fix Notes

Source: full visual re-inspection of all 58 thesis figures (6 parallel image-inspection
passes, MiMo v2.6 native image reading). Findings verified per figure against the
rendered PNGs at native resolution; magnified crops used for small text.

Each section lists: **figure → producer program → defect → required fix.**
After these notes are reviewed, the Section A producer programs are to be fixed,
the affected figures regenerated, and re-verified visually.

Producer locations:
- `figures/*.py` — thesis-local figure scripts (run with the thesis `.venv-pdf` Python)
- `stellarorion_program_proc/scripts/*.py` — program-side render scripts

---

## A. Producer-script fixes (main plot producer programs)

### A1. `figures/make_governing_equations.py` → `governing_equations.png`
- **HIGH** — Axiom-chip text overflows the rounded boxes and adjacent labels collide:
  "Molecular Chaos" + "Continuum Assumption" touch; A5/A6/A7 spill outside their
  borders and run together ("HeatingConvergence", "GuaranteePINN" read as one string).
  *Fix:* widen the chips / reduce label font size / add horizontal padding so every
  chip's text fits inside its rounded rectangle with a minimum gap between chips.
- **MED** — Column header titles ("Refinement", "survivability", "optimization")
  fill their boxes edge-to-edge; glyphs touch/cross the box frame.
  *Fix:* shrink header font or widen the header boxes.

### A2. `figures/make_pinn_architecture.py` → `pinn_architecture.png`
- **MED** — Rotated "Backpropagation (AutoDiff)" label is drawn on top of the
  Stage-1/Stage-2 box and crosses its bottom border.
  *Fix:* move the rotated label fully outside the stage boxes (clear margin).
- **MED** — Neuron-count labels run together: "64 neurons64 neurons64 neurons".
  *Fix:* add separators/spaces or per-column padding between the three labels.
  *Disposition (a):* FIXED — BP_PT 10→9 + measured tuck (label top clears
  the loss box by 0.05 in, get_position/set_position); regenerated Oct 13,
  floor 8.05 pt pass; visual verify PASS (label fully below the box).
  *Disposition (b):* NOT A COLLISION — measured 0.132 in gaps (~4 spaces)
  between sub-labels; batch-3 "zero spacing" overstated; no code change.

### A3. `figures/make_software_pipeline.py` → `software_pipeline.png`
- **MED** — Start arrow's arrowhead lands on the "I" of the INPUT column header.
  *Fix:* shift the arrow start point (or the header) so the arrowhead terminates
  in clear space below/above the header.
- **LOW** — Top connector line is interrupted by the "OUTPUT" label; the elbow
  reads as broken (line ends ~4 px from the "T").
  *Fix:* route the connector around the label or move the label off the line.
  *Disposition:* FIXED both - Start arrow moved x 0.40 -> 0.30 (0.12 in
  clearance to the INPUT header ink); feed descent moved output_cx 6.04 ->
  6.39 (0.07 in clear of the OUTPUT text 5.76..6.32 and its mask, still
  landing on the top edge which reaches 6.48 per the slant note); regen
  floor 8.06 pt pass, fresh PNG Oct 13 00:36 (259353 B), visual verify
  PASS (both breaks gone, engine-side stub normal).

### A4. `figures/make_methodology_derivation.py` → `methodology_derivation.png`
- **MED** — First-column connector arrowheads strike through the layer labels
  "EQUATIONS" (L2), "METHODS" (L3), "IMPLEMENTATION" (L4).
  *Fix:* offset the connectors to enter the layer at a gap between label and box
  edge, or shorten the arrows so heads stop before the text.
- *Disposition:* FIXED via white knockout stroke -- `path_effects=PE_LABEL`
  (`matplotlib.patheffects.withStroke`, linewidth 3.0, white) on both layer-label
  `ax.text` calls; geometric offsets were PROVEN impossible ("IMPLEMENTATION" at
  9 pt bold italic measures 1.3083 in, wider than both the inter-shaft free span
  1.29 in and the 1.26 in column, and shrinking the font fails the 8 pt floor:
  8.5 pt printed 7.61 FAIL).  Labels stay at BOX_AREA_LEFT / TEXT_PT 9.0 (floor
  8.06).  Regen passed, fresh PNG 310243 B Oct 13 01:11, visual PASS (arrows
  visibly interrupted at the glyphs = "line stops behind the text"; the
  strikethrough reading is gone).  Patch history: LABEL_X=0.785 / LABEL_PT=8.5
  attempt failed the floor and was reverted; then C17 knockout, with
  `from matplotlib import patheffects` added (importing matplotlib alone does
  not load the submodule) and a `PE_LABEL` constant carrying the WHY comment.

### A5. `figures/make_dsmc_flowchart.py` → `dsmc_algorithm_flowchart.png`
- **LOW** — No decision block: "Check Convergence" is drawn as a plain process
  rectangle, so the loop-back path has no yes/no branch and both exit and loop
  look unconditional.
  *Fix:* draw a diamond decision block with labelled "no" (loop) and "yes" (exit)
  branches.
  *Disposition:* FIXED - ISO 5807 diamond via DECISION_H = 0.90 slot for
  box 5 only (box 6 + Stop chain carry the delta in `box_top`, H 4.28 ->
  4.84; placement is width-driven `width=0.765\textwidth`, so H growth is
  scale-neutral); box-5 sub declares DECISION_SUB_FS = 8.1 (print_fit
  scale 1.000 -> prints 8.10 pt; loop subscript floor 8.36 pt); branch
  labels DECISION_NO (red, above the tail: diamond edge x 3.724 vs ink
  3.995..4.245 vs bezier 4.38) and DECISION_YES (beside the exit arrow:
  ink 0.7925..0.9175 vs box6 top 0.78 and diamond edge 0.931).
  Regen 176750 B Oct 13 05:43 (1265x1236 px), loop median gap 52 px >= 8,
  flush run 11 <= 80, visual PASS. NOTE: the sync watcher reverted both
  source and PNG once mid-task; recovered by re-applying and committing
  181a459c (source + PNG), after which status is clean.

### A6. `figures/make_hiad_sensitivity.py` → `hiad_design_sensitivity.png`
- **MED** — Panel (b) x-tick labels 10/11/12 merge into an unreadable "101112".
  *Fix:* increase tick spacing or rotate/stagger the tick labels.
- **LOW** — Source credit is light gray on white and tight to the bottom edge.
  *Fix:* darken the credit and add margin.

*Disposition (2026-10-13):* FIXED in `make_hiad_sensitivity.py`:
`ax2.tick_params(axis="x", labelrotation=45)` after `ax2.set_xticks(n_t)`
(keeps every tick value 1..12; double-digit labels get diagonal room) and
bottom band `tight_layout(rect=(0, 0.055, 1, 0.94))` + credit lifted to
`fig.text(0.99, 0.025, ..., color="0.20")`. Regen: RC=0, `scale 0.845, floor
8.0 pt` (FONT_TICK 10 -> 8.45 pt printed), PNG 174078 B, shasum256
216744d5af80c66d. Visual verification (vision service unavailable, see_image
failed x3 -> OCR-free pixel probe on the PNG): 12 distinct rotated tick
labels, 10/11/12 separated (clusters x 5.477-5.640 / 5.657-5.833 /
5.840-6.017 in, gaps 0.017 and 0.007 in = separated but tight at 11|12;
was fully merged pre-patch); credit darkest px 51 (=0.20 gray, was 0.35),
0.077 in right and 0.087 in bottom clearance, xlabels clear
(toroid count N_t at x 4.38-5.50, half-cone at x 1.12-2.72); no new overlaps.

### A7. `figures/make_hiad_sensitivity.py` → `hiad_parametric_cross_section.png`
- **HIGH** — The orange "Scalloped Skin" curve contains spurious self-intersecting
  triangular loops reaching r ≈ ±1500 mm (nowhere near the vehicle profile);
  the loops dominate the plot. Geometry/line-connection artifact.
  *Fix:* fix the point-connection ordering when plotting the scalloped profile
  (sort points along the curve / break the polyline at the seam instead of
  closing it across opposite sides).
- **MED** — "θc" annotation is struck through by the orange skin line.
  *Fix:* reposition the annotation into clear space.
- **LOW** — Dimension arrow passes through the T6/T7 markers; T7 exists only on
  the lower half (asymmetric) and its purple label has low contrast; x-axis runs
  to 2500 mm while the geometry ends at ~1500 mm (right ~35% empty).
  *Fix:* reroute the dimension arrow, mirror or drop T7, raise label contrast,
  trim `xlim`.

A7 *Disposition (2026-10-13):* FIXED. The shipped PNG had NO producer anywhere
(git -S / find / savefig sweeps all negative; it was an ad-hoc script that was
never committed; the two 'scallop' scripts found are text fixers). Wrote a new
producer `figures/make_hiad_parametric_cross_section.py` that reconstructs the
shipped drawing from measurements taken on the shipped PNG (1149x1180 px, axes
frame x 198.5-950.5 / y 102.5-1072.5 px; torus centres upper
(734,397)(873,474)(1010,549)(1148,623)(1288,698)(1422,767), lower mirrored;
centre-line fit r = 0.538 z + 3 mm through the origin; skin row
r = 0.538 z + 80 mm sampled z = 996..1534; nose arc r = 2.00 z^0.917) and
repairs every defect: (HIGH) the skin is rebuilt as ONE z-monotone polyline per
side (nose power arc -> quadratic-Bezier shoulder ease -> straight row -> aft
tip) with an in-script assert that raises if z ever fails to increase, so the
shipped shoulder zigzag (r = 652..939 mm over z = 740..940 mm) cannot return;
(MED) theta_c moved to the measured clear wedge at (z = 1160, r = 300) mm,
clear of skin, discs and cone lines (the shipped label band crossed the skin);
(LOW) the D arrow now spans exactly +/-1500 mm at z = 1750 mm, aft of every
marker (the shipped arrow spanned only +/-1220 mm at z = 1455 mm and cut the
T6/T7 region); T7 kept at the lower-stack end per the thesis alt-text with a
bright #F5F3FF label (was low-contrast purple); xlim trimmed 2500 -> 2050 mm
with the legend relocated to the measured clear upper-left zone. Also caught
and fixed an unlisted defect: the shipped D arrow spanned 2.44 m against its
own 3.0 m callout. Regen: RC=0, `scale 0.996, min text 8.97 pt`, 1485x833 px,
PNG 145845 B, shasum256 06be23f2cfccd7e0; visual PASS (native image read).
Fit-loop lesson: print_fit can only resize the canvas, never absolute label
point sizes, so the figure is born at the print width (4.83 in canvas +
0.1 in tight pad) with a figure-centred 10 pt title; assert_inside_canvas is
now part of the debug loop for any future dark-panel figure.

### A8. `figures/make_fignew.py` → `fignew_gate_comparison.png`
- **MED** — Value label "195.06" is pure black on the dark navy bar
  (≈2.2:1 contrast, hard to read). *Fix:* use white (or outlined) label on dark bars.
- **MED** — 324 px empty band (~20% of figure height) between x-tick labels and the
  legend, which dangles detached at the very bottom.
  *Fix:* tighten the axes/legend layout (remove the dead band, place legend under
  the axes).

### A9. `figures/make_fignew.py` → `fignew_trajectory.png`
- **LOW** — Two visually identical solid-blue legend keys ("1-DOF entry profile"
  vs "deceleration load"). *Fix:* distinguish line styles (e.g. dashed vs solid)
  or colours.
- **LOW** — Run-condition markers touch at ≈51 km (data-correct, crowded).
  *Fix:* marker offset/leader.

*Disposition (2026-10-13):* BOTH FIXED in `make_fignew.py` (commit 0f18fbe8).
A8: added `label_ink_for()` (sRGB-linearised Rec.709 luminance, white ink below
0.25) so value labels follow bar luminance: "195.06" white on the navy IRVE-3
bar (was ~2.2:1 black), "155.67" black on gold, "77.93" white on rose. The
legend no longer dangles outside the canvas (old bbox (0.5, -0.30) made
bbox_inches="tight" grow the image and left a measured 324 px dead band):
tight_layout(rect=(0, 0.10, 1, 1)) reserves the band and the legend anchors at
(0.5, 0.005) inside the canvas. Gate PNG 1328x1200 px (was 1328x1572),
scale 0.996, RC=0. A9: the deceleration trace now draws the shared rcParams
dashed pattern (no literal double hyphen in source), so the legend keys are
distinct; the two run markers (data-correct 1 px crowding) carry callouts as
ax.text plus Line2D leaders placed in bands measured empty against each curve
((85, 1800)/(85, 4200) velocity, (85, 7)/(85, 13) g). LESSON: an Annotation
box contains its arrow, so annotate-with-arrow callouts that converge on one
marker pair always trip the shared text-overlap guard; plain text leaders keep
the guard measuring the label. Trajectory PNG 1566x1134 px, scale 1.003,
RC=0. Visual PASS on both (native read): labels readable, legend sits under
the tick labels with no dead band, callouts clear of curves and markers.

### A10. `figures/generate_sutton_graves_parametric.py` → `sutton_graves_parametric.png`
- **MED** — Opaque annotation box "IRVE-3 run condition 15.36 W/cm²" occludes the
  low-q segments of the nose-radius curve family (curves cut at the box edge;
  box interior 84% blank). *Fix:* move the box into genuinely empty space, shrink
  it, or make it semi-transparent.
- **LOW** — Panel (a) legend swatches for nose radii 0.1–3 m all render the same
  light blue — entries cannot be matched to curves. *Fix:* map each legend entry
  to its actual curve colour.
- **LOW** — Panel (b): "R_N = 1.5 m" box is grazed (<10 px) by the blue V=3 curve.
  *Fix:* nudge the box.

*Disposition (2026-10-13):* FIXED in `generate_sutton_graves_parametric.py`.
LOW (identical swatches): the nine non-baseline curves were all tab:blue at
alpha 0.55, so every legend swatch was the same light blue; the family is
now sampled from the ordered, monotone-luminance plasma map on [0.08, 0.88]
(`family_cmap`, `family_idx`), keeping neighbouring curves distinguishable
under deuteranopia and each well clear of the white canvas; legend swatches
inherit the curve colours automatically. MED (occluding callout): the
IRVE-3 callout moved from axes fraction (0.95, 0.075) to data (2.15, 1000),
left-top anchored, in the genuinely empty top-left triangle above the fan
(the lowest member, R_N = 3 m, had climbed through q ~ 30 to 55 W/cm2 across
the old x band and cut the box, leaving 84% of its interior blank); the
arrow is dropped because any leader to the ring marker at (3.378, 15.36)
would cross all nine curves, so the marker, the text and the caption carry
the identification. LOW (panel b graze): verified CLEAR in the shipped
render (the V = 3 km/s curve sits at q ~ 22 at x = 0.38 and only descends to
q ~ 8 near x = 3, while the box occupies q ~ 6 to 9 at x ~ 0.12 to 0.38), so
the prior ARROW_TARGET_Q repair already resolved it: no action. Regen:
RC=0, guard reports no label overlaps, no box leaves its axes, nothing
leaves the canvas, smallest printed text 8.41 pt (>= 8 pt floor); PNG
232192 B, shasum256 0ff94dc1aa16c220, visual PASS (9 distinct curves with
matching swatches, callout clear of the fan, panel (b) unchanged).

### A11. `figures/make_bo_ccd_design.py` → `bo_ccd_design.png`
- **MED** — Translucent legend frame overlaps the 3D plot: a data point sits
  inside the legend box and grid lines show through the legend.
  *Fix:* opaque legend (`framealpha=1`) placed outside the axes via
  `bbox_to_anchor`, or raise z-order of the legend above a solid face.
- **LOW** — Centre star and IRVE-3 baseline cross overlap each other.
  *Fix:* small marker offset.
- **LOW** — Only ≈14/15 design circles individually distinguishable (3D occlusion
  under the markers). *Fix:* minor camera angle or marker size adjustment.

### A12. `figures/make_results_figs.py` → `LOFTID_mission_trajectory.png`
- **MED** — Annotation collisions: "CG Translation"/"ACS Hold" lines touch;
  bottom-right stack ("Max Heat Rate", "Max Dynamic Pressure", "CG Translations",
  "Loss of Signal") collides with itself and the red markers; "Max Dynamic Pressure"
  crosses the right frame (reaches x=840 vs frame x=818).
  *Fix:* reposition the annotation stack (offset y-positions, keep inside frame).
- **MED** — Phase-band labels ("Deployment", "Final Descent") are green-on-green
  (low contrast). *Fix:* darken/add stroke to label text.

### A13. `stellarorion_program_proc/scripts/generate_field_panels.py` → field-map family
- `mesh_statistics_smooth.png`:
  - **MED** — ~73% of the plot is blank: bars end at n≈472 while the axes run to
    1174; the tail claimed by the title (max n=399) is invisible (no bar pixels
    beyond n≈110). *Fix:* correct the axis limits / binning so the full histogram
    (up to max n=399) is actually drawn.
- `knudsen_map_smooth_M0_A0.png`, `mach_map_smooth_M0_A0.png`,
  `pressure_map_smooth.png`, `thermal_map_smooth.png`:
  - **MED** — Large white data void over ~45% of the axes (lower-right region
    below the shock curve): subtitle "9764 above n>=10" of 19321 cells means only
    high-count cells are rendered; roughly half the domain is unrendered white.
    *Fix:* render cells below the count threshold too (e.g. as a light neutral
    shade) so the domain reads as filled, or clip axes to the rendered region.
  - **LOW** — Salt-and-pepper speckle despite "smooth" in the name.
    *Fix:* apply the smoothing pass to all cells, not only above-threshold ones.
  - **LOW** — Grey subtitle may truncate at the right frame edge.
    *Fix:* shorten the subtitle or widen the right margin.
- `velocity_vectors_smooth.png`:
  - **MED** — Coloured vectors have NO colourbar/legend; magnitude is
    uninterpretable. *Fix:* add a colourbar for the vector magnitude.
  - **MED** — Left ~55% of the plot is densely overplotted black vectors merging
    into visual mush. *Fix:* stride/subsample the vector field (every k-th arrow)
    in the crowded region.
  - **LOW** — White void centre-right; subtitle truncate (same as above).

### A14. `stellarorion_program_proc/scripts/render_bo_3d_plot.py` → `bo_optimization_3d.png`
- **HIGH (content, wrong run)** — Panel C annotation reads "final best = 1.5599"
  = the October-9 re-run value; the thesis documents the official bdddb47 run
  (final best **1.6051**). The figure is generated from the wrong results file.
  *Fix:* point the script at the official run JSON
  (`git show bdddb47:stellarorion_program_proc/src/python/hiad_optimization_results.json`)
  and regenerate.
- **MED** — Panel A colourbar tick sets are interleaved/ambiguous: "1000"/"10"
  (cost) on one side, "45/60/75" with the rotated "φc [deg]" label on the other,
  placed between the two strips; it is unclear which strip each label belongs to.
  *Fix:* place each tick set on its own side of its strip (or use separate
  colourbar axes).
- **LOW** — Panel A 3D axis ticks and legend text are small (borderline at print
  size). *Fix:* increase tick/legend font size.

### A15. `stellarorion_program_proc/scripts/render_optimization_comparison.py` → `optimization_comparison.png`
- **HIGH (content, wrong run)** — Annotation shows "r_tor=0.103m" +
  "half_cone=40.5" = the re-run optimised design; the official bdddb47 design is
  **r_tor 0.0885 m, half-cone 40.15°, R_N 2.9714 m**. Wrong-run content.
  *Fix:* feed the official bdddb47 JSON (same command as A14) and regenerate.
- **MED** — Left panel x-axis label "X [m]" is struck through by the top border
  of the parameter annotation box. *Fix:* move the box off the axis label.
- **LOW** — "half_cone=40.5" runs flush to the box's right edge (possible
  truncation) and line 2 repeats "r_tor=0.103m". *Fix:* pad the box, dedupe.

### A16. `stellarorion_program_proc/scripts/render_kriging_panel.py` → `kriging_denoise.png`
- **MED** — "KRIGED T" panel is nearly featureless black: the bow-shock structure
  clearly visible in "RAW T" is absent despite the caption promising "same limits
  as RAW"; "KRIGED vy" likewise featureless.
  *Fix:* verify the kriging output scaling/limits against the caption first — if
  the kriged field genuinely lost the structure, this indicates a real algorithm
  issue (investigate before "fixing" the plot; do not paper over it with autoscale).
- **LOW** — "KRIGED vx" shows blotchy orange mottling in the freestream not
  present in RAW. *Fix:* same investigation as above.

### A17. `figures/make_lit_review_map.py` → `literature_review_map.png`
- **LOW** — The "Partially covered" legend swatch is not used by any matrix cell.
  *Fix:* drop the unused legend entry.
- **LOW** — Rotated header "Sutton-Graves Heating" descends to nearly touch the
  grid's top border. *Fix:* shorten/raise the header text.
- (The 2×6 coverage-matrix format itself is BY DESIGN — see Section E.)

---

## B. Regenerate-from-official-run items

After the Section A content fixes (A14, A15) are applied, regenerate both figures
from the **official bdddb47 run** data so they agree with the thesis text
(chapter 4 documents: final J 1.6051, R_N 2.9714 m, r_tor 0.0885 m,
half-cone 40.15°):

1. Extract the official results JSON:
   `git show bdddb47:stellarorion_program_proc/src/python/hiad_optimization_results.json`
2. Run the fixed producers with that JSON as input.
3. Visual re-verify: `bo_optimization_3d.png` must show final best 1.6051;
   `optimization_comparison.png` must show r_tor=0.0885 / half_cone=40.15.

---

## C. Third-party / external-source figures — decision points (no local producer)

These figures have **no generator script in this repository** (verified by
repo-wide grep). Defects below cannot be fixed in code here; each needs an
author decision: replace with a corrected source image, re-export from the
original tool, rename the file, or accept as-is.

| Figure | Severity | Defect | Decision |
|---|---|---|---|
| `cp_temperature_nasa.png` | HIGH | NASA-polynomial C_p curve plunges below the y-floor at T≈1300 K and is clipped/absent 1300–6000 K; ~60% of the plot blank; trend contradicts physics (C_p of air rises above ~800 K) — wrong coefficients or an h(T)/T bug wherever it was produced | Recompute/re-export (find original generator: MATLAB/notebook) or replace |
| `knudsen_regime_map.png` | HIGH | HIAD Kn curve discontinuous: vertical branch at ≈44 km shoots off the top, disconnected segment restarts at 100 km (44–100 km data missing); curve also runs behind the upper-left legend box (MED) | Re-export with the full curve; move legend |
| `sutherlandfx.png` | HIGH | Content is compressible boundary-layer velocity profiles (M∞=0–20), NOT Sutherland's viscosity-vs-temperature law — wrong figure for the name | Rename file to match content, or replace with a real Sutherland-law plot (author decides) |
| `Spec0.png` | HIGH/MED | Left edge CLIPS text ("flexile TPS" cut, "…ble", "…cture"); right edge clips the "T7" tag; top-left "(a…)" partially cut; soft low-res raster (LOW) | Re-export from source with margins |
| `RecirculationExample.jpeg` | HIGH | Only 341×148 px — all annotations a few pixels tall (far below 8 pt at any print size); mushy JPEG (content itself correct) | Source a higher-resolution image |
| `hypersonicMachandShockRelation.png` | MED | Content is a lifting-reentry corridor (H–V map), NOT a θ–β–M Mach-shock chart — filename/content mismatch; leader lines/M tick labels crowd-cross (LOW) | Rename to match content, or replace with the actual Mach–shock relation chart |
| `GolfBallImpactReImpact.png` | MED | Content is the sphere drag-crisis curve (C_D vs Re), not a golf-ball impact figure; stray dashed-curve arrow near Re≈5e5 (LOW) | Rename to match content, or replace |
| `scalloped_wall_flow.png` | MED | Orange annotation block ("Valley: dp/dx > 0 …") collides with the red Bow Shock curve; red annotations on dark slate = poor contrast; columns crowd the curve (LOW) | Re-export with repositioned/contrasted annotations |
| `temperature_chemistry_regime.png` | MED | Leftmost blue callout "Caloric Perfect Gas" truncated at the left edge and overlapped by the green callout box | Re-export with callouts repositioned |
| `LOFTID_mission_trajectory.png` | MED | (If not produced by make_results_figs.py — see A12; confirm savefig target) annotation collisions + frame crossing + green-on-green | Fix in A12 if local; else external re-export |
| `aerospace-09-00800-g001-bluntbodyTheory.png` | LOW | Faint gray panel seams; stray black tick top-right corner | Cosmetic — accept or re-export |
| `IADsLayer.png` | LOW | Top label ascenders touch the frame border; 3 px slivers outside frame; source only 280×201 (soft >7 cm) | Accept or source larger |
| `ReinforcedNoseStaticTPS.png` | LOW | Collage panel heights mismatched → white empty block ~25–30% bottom-left | Accept or re-collage |
| `LocalizedHeatinginAmplify.png` | LOW | No colourbar/axes — amplitude sign undefined for the mode shapes; thin top strip | Accept (3D view) or add scale |
| `FigureTPSType0.png` | LOW | Annotation text ≈6.5 pt at 6 in (sub-8 pt at column width) | Re-export with larger text if feasible |
| `FigureTPSType2.png` | LOW | Leader arrows cross; bare callouts "A"/"LI" lack a key; text ≈7.5 pt marginal | Add key / reposition leaders |

**Also external (defect-free, listed for completeness):** `aerodynamicHighShockBody`,
`bowshock_figure1`, `swblishockinteract`, `HIADsDeployed`, `HIADsDeployed`-family
renders, `FigureTPSType1/3`, `aerospace` etc. — PASS.

---

## D. Cleanup / verification notes

- `velocity-contour-for-different-values-of-velocity-for-SST-K-o-model.jpg.png` —
  **VERIFIED NON-ISSUE**: file exists with the full leading "v" name, the
  ch2 include matches it, build is clean. (An earlier suspicion that the file
  was missing its leading "v" was a misread.)
- `gajah_putih-eps-converted-to.pdf` — could not be raster-inspected in this
  pass (PDF input); rasterize to PNG for review if it is to be kept.
- `kamenriderkabuto.eps` — orphan alternative, not included by any chapter.

---

## E. NOT defects (inspection-prompt false alarms — documented so they are not "fixed")

1. **`bo_convergence.png` — minimum at index 37, not 68.** The official run
   documented by the thesis (bdddb47) reaches its minimum at index 37 with
   final best 1.6051; the figure correctly shows that. The "index 68" expectation
   came from the superseded re-run. All-70 filled markers also match the chapter's
   accessible text ("Blue circles are the 70 evaluated costs"). **No change.**
2. **`literature_review_map.png` is a coverage matrix, not a citation graph.**
   The 2×6 matrix is the script's design (`make_lit_review_map.py`). **No change**
   (minor legend cleanup only — A17).
3. **`kriging_denoise.png` heatmap-vs-curves format** — heatmap format matches the
   script design; only the KRIGED T/vy content issue is real (A16).
4. **Pressure/thermal map filenames** — includes correctly use
   `pressure_map_smooth.png` / `thermal_map_smooth.png` (an inspection prompt
   added a wrong `_M0_A0` suffix; the includes are fine). **No change.**
5. **`scallop_pocket_temp_smooth_M0_A0.png`** — sparse strand-like point cloud
   accepted as rendering style; title/colorbar/structure verified. **PASS.**

---

## Pass list (no action)

aerodynamicHighShockBody, bowshock_figure1, swblishockinteract, HIADsDeployed,
FigureTPSType1, FigureTPSType3, domain_mesh, solver_coupling, result_extraction,
grid_mesh_map_smooth, Hiad_DesignSpec, results_performance_comparison,
results_tps_backface, fignew_ccd_screen, fignew_convergence_residuals,
fignew_pipeline, fignew_scalloped_vs_smooth_heatflux, scallop_pocket_temp —
18 figures verified with no actionable defects.

---

*Scope note: these are plotting/layout/data-consistency fixes only. No thesis
prose, numbers, or bibliography are affected by this notes file.*
