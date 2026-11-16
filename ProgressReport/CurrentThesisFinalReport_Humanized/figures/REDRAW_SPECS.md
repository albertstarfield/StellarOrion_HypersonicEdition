# Redraw specifications for small-text diagram figures

Source: image-specialist report (session ses_ef161543dffeSRHTbaCubTzZqv, Oct 6 2026),
measured from the current PNGs (OCR + connected components + pixel dumps).
Purpose: content/layout reference for thesis-side redraw scripts
(figures/make_*.py pattern). Redraw targets: >=9pt declared fonts so printed
text is >=8pt at include width, dash-free text (no `--`, no em-dash), captions
and BeginAccSupp ActualText in the chapter .tex must keep matching the content.

Conversion: textwidth = 5.532 in = 398.3 pt, so
printed_pt = (px / image_width_px) * 398.3 for figures included at \textwidth.

Rebuild-relevant flag: all three originals print smallest text at ~2.3-3 pt
and even titles at ~4.9-6.4 pt => redraw needs roughly a 2.5-3x font increase
(or fewer/shorter strings) to clear the 8 pt floor.

---

## 1. methodology_derivation.png (2760x1987, aspect 1.389; ch3 L13, \textwidth)

Smallest-text ratio: 15 px / 2760 = 0.0054 (red labels) => ~2.8 pt font printed.
Dashes: none. Caption match: YES (nuance: the 3 red dashed arrows link boxes
WITHIN the Methods layer, caption says "between method layers").

### Text (verbatim)
- Title: `Methodology Derivation from First Principles`
- Left layer labels (gray bold italic caps, 2 lines): `LAYER 1 / AXIOMS`,
  `LAYER 2 / EQUATIONS`, `LAYER 3 / METHODS`, `LAYER 4 / IMPLEMENTATION`
- Row 1 blue boxes: `A1: Conservation (Mass, Momentum, Energy)` |
  `A2: Molecular Chaos (Stosszahlansatz)` | `A3: Continuum Hypothesis
  (valid for Kn<0.01)` | `A4: Equilibrium Distribution (MB statistics)`
- Row 2 orange boxes (white text): `Boltzmann Eq.  d f/dt + v.grad f = Q(f,f)` |
  `Navier-Stokes  rho(du/dt + u.grad u) = -grad p + div tau` |
  `Sutton-Graves  q = k sqrt(rho_inf/Rn) V_inf^3` | `Conservation Laws`
- Row 3 green boxes: `DSMC (Bird Algorithm) SPARTA` | `PINN (Physics-Informed
  Neural Network)` | `Metamodel of Physics (MoP) Surrogate` | `Genetic
  Algorithm Optimization`
- Row 4 purple boxes: `SPARTA Docker Container / 5-species air` | `DeepXDE
  PINN Library / Stage 1 + Stage 2` | `PyTorch MoP / 3-layer MLP / CCD
  sampling` | `StellarOrion Engine (Python) / main.py orchestrator`
- Red dashed-arrow labels (italic, above arrows in row 3): `data`, `refined`,
  `eval`
- Bottom legend: `Axioms (First Principles)` | `Governing Equations` |
  `Numerical Methods` | `Software Implementation`

### Layout
- 4 rows x 4 columns; flow top->bottom; red dashed arrows left->right in row 3.
- Box rects (px): row1 y233-420, x 307/887/1467/2047, w517 each, gaps 63.
  Row2 y636-843, widths 614/614/576/421 (NOT equal). Row3 y1021-1226,
  widths 582/592/592/469. Row4 y1520-1726, same x as row1.
  Rows 2/3 columns do NOT align with rows 1/4; arrows slant to connect
  source-center-bottom -> target-center-top.
- 12 solid arrows color #607D8B, shaft ~5 px, triangular head 16x21 px;
  tails start ~13 px inside source, heads end ~7-8 px inside target.
- 3 red dashed horizontal arrows #F44336 at y1122-1125, dash ~19 on / 3-4 off;
  labels above at y1061-1076 (`refined` spills over box edges, gap only 46 px).
- Legend frame (688,1928)-(2089,1971), patches 44x16 px at x698/1071/1410/1733.

### Styling
- White bg. Title #212121 bold, ink h43 (~6.4 pt). Layer labels #757575 bold
  italic caps, ink h16/line (~3.2 pt). Box fills blue #37A0F4, orange #FFA219,
  green #5EB761, purple #A63CB7 (no borders); legend patches #2196F3, #FF9800,
  #4CAF50, #9C27B0; legend text black ~2.9 pt. Box body white regular ink
  h16-20, pitch 23 (~3.0 pt). Red labels #F44336 italic ~2.8 pt.
  Title is 2.0x body size; smallest = 0.45 x title.

---

## 2. governing_equations.png (2384x1578, aspect 1.511; ch3 L83, \textwidth)

Smallest-text ratio: 13 px / 2384 = 0.0055 (axiom chips) => ~2.9 pt printed.
Dashes: none textual (math minus signs in eqs 1 and 6; hyphens in
Navier-Stokes, Sutton-Graves, M-B). Caption match: YES with diffs:
(1) footer says "Table 3.1" while caption says tab:research_axioms;
(2) caption says "GA-based survivability optimization", figure says
`GA Optimization`; (3) figure quirks: duplicate "A3" axiom and A7 before A6.

### Text (verbatim)
- Title: `Governing Equations: Derivation Chain from Kinetic Theory to Optimization`
- Transition chips (2 lines, italic, over the 5 gaps): `Discretize (Bird, 1994)`
  | `Continuum Limit (Kn->0)` | `Regression Correlation` | `Neural
  Approximation` | `Global Search`
- Main boxes (2 lines, white bold): `Kinetic Theory` | `DSMC Method` |
  `Navier-Stokes Equations` | `Sutton-Graves Correlation` | `PINN Refinement`
  | `GA Optimization`
- Equation boxes (1 line each, under main boxes):
  1. `df/dt + v.grad f = integral (f f1 - f f1) g sigma dOmega dv1`
     (original renders WITHOUT visible primes; redraw with proper f' primes)
  2. `Delta x <= lambda/3,   Delta t <= 1/nu`
  3. `d rho/dt + div(rho u) = 0`
  4. `q_s = k sqrt(rho_inf/Rn) V_inf^3`
  5. `L = lambda_d L_data + lambda_pde L_PDE`
  6. `J* = min(beta - beta_target)^2 + lambda sum max(0, g_i)`
- Axiom chips (2 lines, purple): `A1: Conservation / A2: Molecular Chaos` |
  `A3: Mean Free Path / A4: M-B Distribution` | `A3: Continuum Assumption`
  (dup A3 in original) | `A5: Empirical Heating` | `A7: PINN Consistency`
  (A7 before A6 in original) | `A6: Convergence Guarantee`
- Footer: `Bottom: Axiom references (Table 3.1)    Top: Transition methodology`

### Layout
- Single horizontal chain: main boxes y460-943 (h483), x = 130/491/851/1212/
  1573/1934, w ~321, gaps 40. 5 solid #2C3E50 right-arrows in the gaps at
  y694-708 (shaft 5 px + triangle, tip ~6 px inside next box).
- Chips y306-358 centered on gaps; equation boxes centered y~1053
  (x/w: 112/357, 560/182, 919/185, 1292/161, 1606/254, 1886/416);
  axiom chips y1263-1312; footer y1459-1478. Annotation rows have NO
  connectors (free-floating).

### Styling
- White bg. Title #2C3E50 bold ink h34 (~5.9 pt). Main box fills
  #316383, #3D82AF, #4392C7, #2B9A84, #BE9F23, #9D4037, border #2C3E50 ~3 px,
  rounded. Box titles white bold ink h18-19 (~3.4-4.2 pt). Chips fill
  #FEFAEB border #F2EA9F, text #7F8C8D italic (~3.0 pt). Equation boxes white
  border #C0C6C9, text #2C3E50 ink h30 (~5.0 pt, math is largest non-title).
  Axiom chips fill #F7F1F9 border #DAC1E4 text #6C3483 ink h13-14 (~2.9 pt).
  Footer #7F8C8D italic (~3.4 pt). Smallest = 0.39 x title.

---

## 3. software_pipeline.png (3179x1585, aspect 2.006; ch3 L96, \textwidth)

Smallest-text ratio: 14 px / 3179 = 0.0044 ("VTK data") => ~2.3 pt printed
(SMALLEST of the three).
Dashes: **EM-DASH in title** `StellarOrion Engine — Software Pipeline
Architecture` (redraw with comma or colon per no-dash rule). No `--`.
Caption match: **NO** - diffs: (1) NO "Bayes Opt" element exists in the
figure (surrogate stage is `MoP Surrogate (PyTorch MLP)`; feedback arrow from
MoP -> engine labeled `GA optimization feedback loop`); (2) figure includes an
OpenFOAM laplacianFoam solver branch not in the caption; (3) input column has
3 inputs (geometry, flight conditions, DESIGN VARIABLES) but caption mentions
only two; (4) `refined` PINN->MoP label and ParaView output DO match.
Decision needed at redraw time: either update the caption/AccSupp to match the
figure (MoP + OpenFOAM + design variables) or drop those elements from the
redraw to match the caption - do not leave them mismatched.

### Text (verbatim)
- Title: `StellarOrion Engine — Software Pipeline Architecture` (fix dash)
- Column headers (gray caps): `INPUT` | `CORE ENGINE` | `SOLVERS` |
  `ML MODELS` | `OUTPUT`
- Input boxes: `CadQuery Geometry / STL export` | `Flight Conditions /
  V, T_inf, rho_inf` | `Design Variables / d, theta, n_tor, r_n`
- Engine: `StellarOrionEngine / Mach5Up.py / (main orchestrator)` (white bold)
- Solvers: `SPARTA / DSMC Solver / Docker container`; `OpenFOAM /
  laplacianFoam / (solid thermal)`
- ML: `PINN / DeepXDE / (FNN 5x128)`; `MoP Surrogate / PyTorch MLP /
  (3-layer, 8 output)`
- Output: `ParaView / VTK/ / STL / Rendering`
- Arrow labels (italic): `VTK/STL files` (inside SPARTA box top),
  `VTK data`, `surface data` (crossed by diagonal arrow), `refined`
  (orange #E65100, right of vertical PINN->MoP arrow),
  `GA optimization / feedback loop` (orange, 2 lines - overlaps OpenFOAM
  box text in the original; redraw must place it clear)
- Legend: `Input (Geometry, Conditions)` | `Core Engine (Orchestrator)` |
  `Physics Solvers (SPARTA, OpenFOAM)` | `ML Models (PINN, MoP)` |
  `Visualization (ParaView)`

### Layout
- 5 columns. Inputs x66-583, three at y251-454 / 499-702 / 747-950.
  Engine (689,383)-(1314,647). SPARTA (1474,345)-(2059,570),
  OpenFOAM (1474,612)-(2059,837). PINN (2161,345)-(2687,571),
  MoP (2161,612)-(2687,837). Output (2789,326)-(3119,647).
  Legend (683,1529)-(2503,1572).
- 10 solid arrows #37474F (shaft 5-6 px, head 15-19 px): 3 input->engine
  (inputs 2 and 3 CROSS in an X), engine->SPARTA, engine->OpenFOAM,
  engine->ParaView LONG line drawn OVER SPARTA and PINN boxes (redraw: route
  around/above instead), SPARTA->PINN, SPARTA->MoP diagonal, PINN->MoP
  vertical, MoP->engine feedback (head inside engine right edge).
- INPUT header ink overlaps input box 1's top border in the original (fix).

### Styling
- White bg. Title #212121 bold ink h38 (~4.9 pt). Headers #757575 bold caps
  (~3.1 pt). Input boxes fill #E5F3FD border #C0C1C2 text #212121 (~2.5 pt).
  Engine fill #2871C5 border #1665C0 white bold. Solvers fill #3F8742
  border #2F7D33 white. ML fill #E85F14 border #E65201 white. Output fill
  #582795 border #4B158C white. Arrow labels #37474F or #E65100 italic
  (~2.3-2.5 pt). Legend patches match box border colors (#E5F3FD, #1565C0,
  #2E7D32, #E65100, #4A148C). Smallest = 0.37 x title.

---

## 4. dsmc_algorithm_flowchart.png (1979x1580, aspect 1.253; ch2 L917, 0.9\textwidth)

Print width 0.9 x 5.53 in = 4.98 in. Smallest-text ratio: 10 px / 1979 =
0.0051 (subscript `steps` in the loop label) => 3.6 pt printed; box labels
9.4 pt nominal, title 14.5 pt nominal. To clear 8 pt the subscript must
grow about 2.2x; in the redraw, set every font >= 9 pt declared so the
smallest element clears 8 pt at 0.9\textwidth.
Dashes: none. Two single ASCII hyphens only (`Maxwell-Boltzmann`,
`Grid-Based`), both legitimate.
Caption match: **YES against the actual caption** (ch2 L919): "Flowchart
of Bird's No-Time-Counter (NTC) DSMC algorithm. The two-phase alternation
between particle movement (streamer phase) and collision pairing (collision
phase) is shown, with macroscopic property sampling accumulating at each
time step." Bird attribution, NTC, and the sampling step all match the
figure. NOTE: the describing session quoted a different caption
("problem definition to flow field visualization") that exists nowhere in
the repository (grep 0 hits); disregard it. AccSupp ActualText at ch2 L916
also matches (advection, collision, sampling). No caption or AccSupp edit
required; keep them identical on redraw.

### Text (verbatim)
- Title: `DSMC Algorithm (Bird, 1994)`
- Box 1: `Initialize Particles` / `(Maxwell-Boltzmann Distribution)`
- Box 2: `Move Particles Ballistically` / `(Free Flight for Δt)`
- Box 3: `Index Particles into Cells` / `(Grid-Based Spatial Sorting)`
- Box 4: `Sample Collisions within Cells` / `(NTC Method: Pair Selection)`
- Box 5: `Accumulate Macroscopic Properties` / `(ρ, T, u, p per Cell)`
- Box 6: `Check Convergence` / `(Steady State / Time Average)`
- Box 7: `Output Surface Data` / `(Heat Flux, Pressure, Shear)`
- Left of box 2: `Δt` (green mathtext)
- Right of loop, rotated 90° (reads bottom-to-top): `Repeat` / `N_steps`
- No legend, no footer, no Yes/No branch labels.

### Layout
- Landscape, single centered column. Title y20-57 centered.
- 7 identical boxes x502-1477 (w976, h136, pitch 203.5, gap 68),
  tops at y 153/357/561/764/968/1172/1375.
- 6 solid down-arrows x981-999 (60 px, 6 px shaft, 18x16 filled head),
  one per gap, order 1->2->3->4->5->6->7.
- Dashed red loop from right of box 6 (1606,1237) bulging left to
  x1485@y796 (8 px clear of box column) ending in up arrowhead at
  (1604,432) at right of box 2; free-floating, does not touch boxes.
  Dash 26 px / gap 4 px, stroke 6 px.
- Green `Δt` at (294,412), 176 px left of box 2. Rotated label at
  x1739-1790, y787-883, right of the loop.

### Styling
- White bg, black bold text, square corners, no title bar, no shadow,
  border ~5-6 px, fill = light tint of border hue. Tailwind palette:
  1 `#3B82F6`/`#DBEAFE` 2 `#22C55E`/`#DCFCE7` 3 `#F59E0B`/`#FEF3C7`
  4 `#EC4899`/`#FCE7F3` 5 `#6366F1`/`#E0E7FF` 6 `#A855F7`/`#F3E8FF`
  7 `#EF4444`/`#FEE2E2`.
- Box text: 2 centered lines, same size, line spacing ~30 px, block
  vertically centered. Down-arrows solid slate `#475569`. Loop dashed
  `#EF4444`. `Δt` green `#22C55E`; `Repeat` bold red.
- Font: DejaVu Sans Bold for roman text; mathtext italic for `Δt`,
  `ρ, T, u, p`, `N_steps`.

### Redraw requirements
- matplotlib thesis-side script (figures/make_dsmc_flowchart.py pattern),
  save at print width <= 0.9\textwidth, all fonts >= 9 pt declared
  (subscript `steps` is the binding constraint in the original: 6.5 pt).
- Dash-free (single ASCII hyphens in compound words are fine).
- No data invention: labels and structure are schematic, reuse verbatim.
- Keep caption and AccSupp text unchanged (they match).

---

## 5. literature_review_map.png (1979x1414, aspect 1.400; ch2 L43, 0.92\textwidth)

Text is legible in principle but the smallest cap height is 16 px of
1979 px width = ratio 0.0081, which prints at about 3.9 pt at the
current include width, so it fails the 8 pt floor and must be redrawn.
No dashes present.

Verbatim text to reuse:

- Title: `Literature Review: Coverage of Physical Phenomena and Methodology`
- Column headers (two lines each): `HIAD` / `Geometry`,
  `DSMC` / `Aerothermal`, `Sutton-Graves` / `Heating`, `PINN` / `Refinement`,
  `Survivability` / `Optimization`, `Multi-Solver` / `Pipeline`
- Row labels (two lines each, right aligned): `Rapisarda (2022)` /
  `ML for HIAD Heating`, `Rapisarda et al. (2024)` /
  `HIAD Parametric Study`, `Masciarelli & Cassis (2021)` / `LOFTID Design`,
  `Schwartzentruber (2018)` / `DSMC Hypersonic`,
  `This Work` / `StellarOrion Pipeline`
- Legend labels: `Fully covered`, `Partially covered`, `Not covered`

Layout: six columns by five rows, cells 189 x 150 px, 5 px dark
separators, cell edges `#2C3E50`. Cell fills: full `#1A5276` navy,
partial `#85C1E9` light blue, not covered `#F2F4F4` off-white. Marks:
full = solid white filled circle, partial = circle with navy left half
filled, not covered = no mark. A dashed red `#E74C3C` 6 px rectangle
outlines the `This Work` row. Reading order is top to bottom, left to
right, ending on the fully filled `This Work` row.

Coverage matrix (row by column, F = full, P = partial, empty = not
covered), transcribed from the artwork:

| row | HIAD Geo | DSMC | Sutton-G. | PINN | Surviv. | Multi-Solver |
|---|---|---|---|---|---|---|
| Rapisarda (2022) | F | P | P | F | F | P |
| Rapisarda et al. (2024) | F | P | F | empty | P | empty |
| Masciarelli & Cassis (2021) | F | empty | F | empty | empty | empty |
| Schwartzentruber (2018) | empty | F | empty | empty | empty | empty |
| This Work | F | F | F | F | F | F |

Redraw requirements:

- matplotlib thesis-side script (`figures/make_lit_review_map.py`
  pattern), save at print width 0.92 of the text width, all declared
  fonts >= 9 pt, title >= 13 pt.
- Keep the dashed red highlight around the `This Work` row (the caption
  and AccSupp both reference it).
- Caption and AccSupp need no edit: the caption already matches the
  artwork. Note that the AccSupp and caption describe the marks as
  circles with a half circle, which the artwork does use, while the
  legend swatches at the foot are rectangles; keep the circle marks so
  caption, AccSupp and artwork all agree.
- Dash-free text (single ASCII hyphens only).

## 6. pinn_architecture.png (2379x1376, aspect 1.729; ch2 L1065, 0.9\textwidth)

Smallest text is the mathtext subscripts at 14 px of 2379 px = ratio
0.0059, about 3.0 pt printed, so it fails the 8 pt floor. It also
contains a literal double hyphen `Navier--Stokes` in the artwork text,
which violates the no double hyphen rule, so the redraw must fix both.

Verbatim text to reuse, with the corrections the redraw must apply:

- Title: `Physics-Informed Neural Network (PINN) Architecture`
- Box 1: `PDE Residual` / `(Navier-Stokes)` (single hyphen, corrected)
- Box 2: math `$\mathcal{L}_{total} = \mathcal{L}_{PDE} + \mathcal{L}_{BC} + \mathcal{L}_{data}$`
- Box 3: `DSMC Data` / `Anchor Points`
- Red bold annotation: `Backpropagation` / `(AutoDiff)`
- Grey italic annotation box: `Stage 1: Pre-train on BC data` /
  `Stage 2: Fine-tune on PDE + DSMC data`
- Columns: `Input` / `$(x, r)$`, then `Hidden 1` ... `Hidden 4`, each
  with `128 neurons` below, then `Output` / `(u, v, T, p, rho)`

ARCHITECTURE CORRECTION (verified against
`stellarorion_program_proc/src/python/pinn_accelerator.py`): the code
builds `dde.nn.FNN([2] + [64] * 3 + [n_output], "tanh", "Glorot normal")`
with `n_output = 4` and the documented state vector `[rho, u, v, T]`
with pressure derived from the ideal gas law `p = rho * R_gas * T`.
The artwork claims four hidden layers of 128 neurons and five outputs,
which contradicts the code and the thesis tables. The redraw must show
**3 hidden layers of 64 neurons** and **4 outputs `$(rho, u, v, T)$`**.
(Do not confuse this with the separate `[1] + [128] * 4 + [1]` network
in `validation_pipeline.py`, which is a different, one input to one
output network and is not the network this figure depicts.)

Layout: three rounded boxes in one top row joined by thick orange
`#F59E0B` connectors without arrowheads, then six node columns (input,
three hidden, output) of filled ellipses, 5 rows each, with thin light
grey all-to-all links drawn behind the nodes, a red dashed vertical
arrow pointing up into the hidden column labelled `Backpropagation`,
and the grey stage box overlapping the third hidden column. Column
labels sit centered under each column.

Redraw requirements:

- matplotlib thesis-side script (`figures/make_pinn_architecture.py`
  pattern), save at print width 0.9 of the text width, all declared
  fonts >= 9 pt, math subscripts >= 9 pt so nothing prints below 8 pt.
- Draw nodes at the corrected count: input, `Hidden 1..3` each `64
  neurons`, output.
- Dash-free text: `Navier-Stokes` with a single hyphen.
- Caption and AccSupp were already corrected to
  `$(\rho, v_x, v_y, T)$` in this cycle and now match the redraw.

## Pending related items
- Caption/AccSupp content specs for these figures live in the chapter .tex
  (ch3 L13/L83/L96 captions quoted in session history).
