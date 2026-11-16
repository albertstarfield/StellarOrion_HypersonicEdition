# Page-Reduction Plan — CurrentThesisFinalReport

Handoff notes for the next agent instance.

**Objective:** reduce the page count of the thesis **without deleting
substantive technical content**. Content-level condensation (Lever C) is
listed separately and is flagged as needing author judgement.

Page numbers below are **printed** page numbers. Conversion is
`printed = PDF - 26`. The front matter is still 26 pp, so the offset has
not moved — but re-derive it after Lever B or D, which change front matter.

> **Status: Lever A is APPLIED and COMMITTED.** The thesis is now
> **191 pages**, down from 194. Lever A's *actual* yield was **3 pages**,
> not the 6–8 originally estimated here — §2 has been corrected with the
> measured numbers. Levers B–E remain open.

---

## 1. Current state

Total: **191 pages** = 26 front matter (roman) + 165 body (arabic).
(Was 194 / 168 before Lever A.)

| Part | Printed pp | Count | % of body |
| :--- | :--- | ---: | ---: |
| Ch1 Introduction | 1–12 | 12 | 7.3% |
| **Ch2 Literature Review** | **13–74** | **62** | **37.6%** |
| Ch3 Methodology | 75–115 | 41 | 24.8% |
| Ch4 Results and Discussion | 116–142 | 27 | 16.4% |
| Ch5 Conclusion | 143–146 | 4 | 2.4% |
| References | 147–155 | 9 | — |
| Appendix A | 156–159 | 4 | — |
| Appendix B | 160–161 | 2 | — |
| Appendix C | 162–163 | 2 | — |
| Appendix D | 164–165 | 2 | — |

Front matter map (PDF pages 1–26, **unchanged by Lever A**):

| PDF pp | Part | Count |
| :--- | :--- | ---: |
| 1 | Cover | 1 |
| 2 | Approval page | 1 |
| 3 | Abstract | 1 |
| 4–11 | Table of Contents | **8** |
| 12–19 | List of Figures (46 entries) | **8** |
| 20–22 | List of Tables (39 entries) | **3** |
| 23–24 | List of Symbols | 2 |
| 25–26 | List of Abbreviations | 2 |

**Headline: Ch2 is now 62 pp — 37.6% of the body, and it grew by 1 pp as
float repacking pushed content into it. The front matter's three generated
lists still occupy 19 of 26 pages.**

---

## 2. Levers, ranked by risk

### Lever A — Unpin the `[H]` floats · APPLIED · **measured 3 pp**

**This lever has been applied and committed.** The section is kept for the
record and to explain why the yield was 3 pp rather than the 6–8 first
estimated.

`[H]` forces a float to sit exactly where it was written, which prevents
LaTeX from packing floats onto shared pages and from moving a float past a
page it does not fit. The measurable consequence is vertical dead space.

Floats converted, `[H]` → `[!htbp]`:

```
chapter_03_methodology.tex          26 figure/table  + 1 algorithm
chapter_02_literature_review.tex    18
chapter_04_results.tex              17
appendix.tex                         9
chapter_01_introduction.tex          2
                                ------
TOTAL                               73   (72 figure/table + 1 algorithm)
```

**Measured result — before → after:**

| Metric | Before | After |
| :--- | ---: | ---: |
| Total pages | 194 | **191** |
| Body pages | 168 | 165 |
| Pages with >170 pt dead space | 17 | **8** |
| Total dead space | 5,679 pt (7.9 pp-equiv) | 3,700 pt (5.1 pp-equiv) |

All guardrails held: 0 LaTeX errors, 0 undefined references/citations, 0
rerun requests, 0 blank pages, 973 link annots with 0 nonzero borders,
accsupp still 51/51, overfull/underfull unchanged at 9/69.

**Why 3 pp and not 6–8.** The dead space did not convert one-for-one into
saved pages — roughly 2.7 pp-equivalent of whitespace was genuinely
eliminated, but the rest was absorbed by reflow as floats re-settled. More
importantly, **the three worst remaining gaps are structural, not
float-driven.** They are chapter-end pages where `\chapter` forces a break:

| Page | Dead space | Why |
| :--- | ---: | :--- |
| p38 | 620 pt | end of Ch1 |
| p100 | 602 pt | end of Ch2 |
| p141 | 602 pt | end of Ch3 |

These are not recoverable by any float tuning. Lever A has therefore
extracted close to all the space that is actually available from float
placement, and **should not be revisited.**

One accepted side effect: three tables now share a page (Appendix A, PDF
p184 — A.3, A.4, A.5) with ~2–3 cm gaps between them, where previously each
occupied its own pinned slot. Verified by rendering: no clipping, no
overlap, all rows and captions present. The inter-table gaps are slightly
uneven, which is normal `[!htbp]` behaviour and a large net improvement on
the ~400 pt of dead space the pinned version left on that page.

### Lever B — Reduce TOC depth · LOW RISK · est. 5 pp

The Table of Contents runs 8 pages because it descends to third and fourth
level (`2.10.4 Molecular Interaction Model`, `3.3.4`, `5.2.2` …).

**Action:** set the depth in `preamble.tex`:

```latex
\setcounter{tocdepth}{2}   % chapters + sections only
```

Recovers roughly 5 pages. Note this is a **navigation-granularity** change,
not a content change — verify the institution's formatting requirement
before applying, since some require level-3 entries.

### Lever C — Condense Ch2 · MEDIUM RISK · est. 12–15 pp

Ch2 is 36% of the body. Ranked by length:

| § | Title | pp | Count |
| :--- | :--- | :--- | ---: |
| 2.5 | Impact of Surface Geometry on Flow Physics | 32–41 | 10 |
| 2.4 | Thermal Protection Systems (TPS) Technology | 25–31 | 7 |
| 2.8 | Thermodynamic Gas Models | 47–52 | 6 |
| 2.15 | Optimization Theory Fundamentals | 66–71 | 6 |
| 2.3 | Aerothermodynamics of Re-entry Vehicles | 20–24 | 5 |
| 2.2 | Fundamentals of Hypersonic Aerodynamics | 15–19 | 5 |
| 2.6 | Theoretical Framework of CFD | 42–45 | 4 |
| 2.9 / 2.13 / 2.14 / 2.10 | (four sections) | — | 3 each |
| 2.16 / 2.1 | Summary; Review of Related Research | — | 2 each |
| 2.7 / 2.11 / 2.12 | Turbulence; Knudsen; Continuum-vs-DSMC | — | 1 each |

Ch2 carries 25 `figure` + 4 `table` + 1 `longtable` = **30 floats over 61
pages**, with 23 figures at ≥0.8 `\textwidth`.

**Action:** this is the only lever that deletes text, so it needs an
editorial decision, not a mechanical one. Suggested order of attack:

1. Apply Lever A first and re-measure — a large share of Ch2's length is
   float dead space, not prose.
2. Target 2.5 and 2.15 (16 pp combined) for prose condensation. 2.5 is the
   chapter's own subject matter and is probably load-bearing; 2.15
   (Optimization Theory Fundamentals, 6 pp) is the most likely candidate
   for standard-textbook treatment with a citation instead of full
   derivation.
3. The three duplicated 1-page sections 2.7 / 2.11 / 2.12 (Turbulence
   Modeling, Knudsen Classification, Continuum-vs-DSMC) are adjacent and
   are prime merge candidates.

### Lever D — Compress the List of Figures · LOW–MED RISK · est. 2–3 pp

The LoF is 8 pages for 46 figures. Options, cheapest first: reduce LoF
entries to `\cftfigpage` without the full caption text; drop the List of
Figures and List of Tables entirely if the institution does not require
them; or reduce the figure count itself (see §4 — 3 figures currently have
false captions, so some of them are not earning their space).

The LoT at 3 pp for 39 tables is proportionate; leave it.

### Lever E — List of Symbols + Abbreviations · MED RISK · 4 pp

PDF pp 23–26. Often optional in a thesis. Check institutional requirements
before removing. Do not remove without confirming — this is the kind of
front-matter change that fails a format check.

---

## 3. Expected outcome

| Lever | Est. saving | Risk |
| :--- | ---: | :--- |
| A — unpin floats | 6–8 pp | low |
| B — TOC depth | ~5 pp | low |
| D — LoF compression | 2–3 pp | low–med |
| C — condense Ch2 | 12–15 pp | med |
| E — drop symbol/abbrev lists | 4 pp | med |
| **Levers A+B+D only** | **~13–16 pp** | **low** |
| **All levers** | **~29–35 pp** | med |

**Recommended sequence:** A, then B, then re-measure and re-decide. The
low-risk levers alone take 194 → ~178–181 pp with no content removed. Only
then open Lever C, and only with the author.

---

## 4. Correctness defects found and NOT yet fixed

These are **accuracy** problems, not page-count problems. They were found
during the alt-text audit immediately before this plan was written, are
unfixed in `c51a379`, and must not be lost. Fixing them is independent of
the page reduction.

All three share one root cause: a borrowed textbook figure was captioned
and alt-texted as something it is not.

1. **`fig:shock_wave`** (`hypersonicMachandShockRelation.png`) — captioned
   *"Figure for Shock Wave Formation and Properties Relation (Anderson)"*.
   The artwork is a **"Lifting reentry from orbit" H–V reentry corridor
   diagram**: velocity 0–10 km/s vs altitude 0–110 km, high-lift and
   low-lift trim boundaries with a hatched corridor, ballistic-parameter
   contours labelled 8/12/16/20/24/28, the two annotated values
   50 kg/m² and 5000 kg/m², and the Shuttle Orbiter trajectory tracked
   along the high-lift edge. The caption is **false** — it describes a
   shock-formation diagram and the figure is a reentry-corridor diagram.

2. **`fig:sutherlands_law`** (`sutherlandfx.png`) — captioned *"Sutherland's
   Law effect on Laminar Boundary Layer Insulation"*. The artwork is a
   family of **compressible boundary-layer velocity profiles** in
   similarity coordinates: `u/u_e` (0→1) against `(y/x)√Re_x` (0→80), six
   solid curves labelled M∞ = 0, 4, 8, 12, 16, 20, separating progressively
   with Mach. Sutherland's law is a viscosity–temperature relation; this
   figure does not show it. The caption is **false**.

3. **`fig:surface_topology`** (`GolfBallImpactReImpact.png`) — captioned
   *"Impact of Surface Topology on Re Number"*, filename claims golf-ball
   re-impact. The artwork is a **flat-plate drag-coefficient chart**, both
   axes log: `C_D` (0.1–800) vs `Re` (10⁻¹–10⁶), with a solid smooth-surface
   curve, a dashed rough-surface branch diverging at the drag crisis
   (~Re 3×10⁵), and three leader-line callouts: *L/D → ∞*, *Drag 'crisis'
   (turbulent boundary layer appears)*, and *Effect of rough surface or
   turbulent freestream*. The rough/smooth distinction is genuinely
   depicted, so this caption is imprecise rather than wholly false — but
   the filename's golf-ball claim is unsupported.

Also outstanding: **9 figures still carry stub alt text** in the legacy
`"Figure for X."` form, 103–147 chars each, which convey almost nothing:

| Label | Image | Alt len |
| :--- | :--- | ---: |
| `fig:surface_topology` | `GolfBallImpactReImpact.png` | 142 |
| `fig:rigid_tps` | `ReinforcedNoseStaticTPS.png` | 140 |
| `fig:aerothermodynamics` | `aerodynamicHighShockBody.png` | 140 |
| `fig:bow_shock` | `bowshock_figure1.png` | 147 |
| `fig:grid_mesh` | `grid_mesh_map_smooth.png` | 106 |
| `fig:shock_wave` | `hypersonicMachandShockRelation.png` | 126 |
| `fig:knudsen_regime_map` | `knudsen_regime_map.png` | 140 |
| `fig:methodology_derivation` | `methodology_derivation.png` | 125 |
| `fig:sutherlands_law` | `sutherlandfx.png` | 103 |

Artwork notes already gathered for these, usable as alt-text source:

- `GolfBallImpactReImpact.png` — flat-plate `C_D` vs `Re`, both log. Solid
  curve falls from `C_D`≈70 at Re=10⁻¹ to a minimum ≈0.9 near Re≈10³, rises
  to ≈1.3 at Re≈10⁵, then drops at the crisis. Dashed rough/turbulent branch
  continues down to ≈0.3. Callouts as above. Fully legible.
- `ReinforcedNoseStaticTPS.png` — 3-panel **photo collage**, not a plot. (a)
  Shuttle Orbiter nose-cap close-up, dark RCC with panel seams, blue sky;
  (b) launch stack on the pad showing "United States" lettering, US flag and
  NASA insignia, orange external tank, a yellow step ladder and an orange
  hose in the foreground, a person clipped at the right edge; (c) removed
  RCC leading-edge panel, black sickle-shaped, brass attachment hardware,
  sky-blue backdrop.
- `aerodynamicHighShockBody.png` — schematic. M∞=36 inflow arrow, detached
  bow shock, hatched "High-temperature shock layer", a dashed fluid-element
  circle on the shock with `q_c` and `q_R` arrows, a diagonal element path,
  a second M∞=36 arrow, "T ≈ 11,000 K" at the wall, and a starburst
  radiation symbol between "Radiating fluid element" and "Partially ionized
  plasma". Fully legible.
- `bowshock_figure1.png` — cross-section schematic. Detached bow shock as a
  thin double arc, grey stippled shock layer, blunt-nosed cylindrical entry
  body with an elliptical open exit, a dashed boundary-layer edge inside
  the contour, and four leader callouts: "Strong bow shock wave",
  "High-temperature boundary layer", "Entry body", "High-temperature shock
  layer region", plus M∞ ≫ 1 with a rightward arrow. Fully legible.
- `hypersonicMachandShockRelation.png` — see defect 1 above. Fully legible.
- `knudsen_regime_map.png` — **genuine thesis figure, caption is correct.**
  Knudsen number (log, 10⁻⁴–10²) vs altitude (40–120 km, linear), with
  green continuum (<0.01), orange transitional/DSMC, pink free-molecular
  (>10) bands, a blue `HIAD (L = 3.0 m)` curve, and an orange dashed
  **IRVE-3 Entry (52 km)** reference line inside the transitional band.
  Legend upper-left. Needs alt text only, no caption change.
- `sutherlandfx.png` — see defect 2 above. Six curves, all legible.
- `grid_mesh_map_smooth.png` — "SPARTA Adaptive Mesh Grid", dark background,
  cyan wireframe. Axial (−4…8 m) vs Radial (−4…4 m). A biconic/wedge body
  spanning x≈0.2–2.0 m, magenta vertical reference line at x≈1.0 m,
  refinement clustered near the body, and symmetric T1–T7 wall-temperature
  markers on both upper and lower surfaces (orange/blue circles, cyan T7(S)
  rectangles at the shoulders). Mesh lines are dense far-field; individual
  far-field cells are hard to separate but refinement structure is clear.
- `methodology_derivation.png` — 4-layer derivation diagram. L1 AXIOMS
  (A1 Conservation, A2 Molecular Chaos/Stosszahlansatz, A3 Continuum
  Hypothesis Kn<0.01, A4 Equilibrium Distribution/MB) → L2 EQUATIONS
  (Boltzmann, Navier–Stokes, Sutton–Graves, Conservation Laws) → L3 METHODS
  (DSMC/SPARTA, PINN, MoP Surrogate, Genetic Algorithm) → L4 IMPLEMENTATION
  (SPARTA Docker 5-species air, DeepXDE Stage 1+2, PyTorch MoP 3-layer MLP,
  StellarOrion Engine main.py). Red dashed horizontal arrows labelled
  `data` → `refined` → `eval` across L3. Colour legend at the bottom. Minor
  legibility issue: the word **"refined"** is overlapped by its arrow shaft;
  `data` and `eval` are small and low-contrast.

---

## 5. Guardrails — do not regress the audited state

`c51a379` is verified clean. Re-verify all of this after **every** build,
and before committing:

```
pages                                : 176 (recorded 2026-10-21 after the GA conversion;
                                        was 179 after the PINN removal, 194 before it)
LaTeX errors (grep -c '^!' main.log)                     : must be 0
undefined refs/citations                                     : must be 0
real rerun requests                                          : must be 0
blank or near-blank pages                                    : must be 0
BeginAccSupp == EndAccSupp (comment-stripped)               : must be equal
  -> currently 51/51, 51 ActualText entries
/Link annots stroking a border (/Border != [0 0 0])         : must be 0
  -> currently 973 annots, all /Border [0 0 0], no /BS
red link ink (pixel sample of rendered pages)               : must be 0 px
  -> 643 annots carry dormant /C [1 0 0] metadata; this is
     harmless because /Border is zero, but confirm by pixel
conflict markers in tracked .tex                            : must be 0
git diff --check                                             : must be clean
"TABLE OF CONTENTS" / "REFERENCES" present, singular absent : must hold
```

PINN removal (2026-10-20). PINN is not part of the main pipeline required to
produce the optimised body, so every PINN reference was removed from the
thesis: the Chapter 3 PINN section, the Chapter 2 PINN subsection, the A7
axiom and Step 5 of the derivation chain, the Chapter 4 PINN claims and gate
leg wording, the Chapter 5 PINN validation subsection, the abstract and
keyword mentions, the abbreviation entry, and the PINN assets. The literature
coverage matrix, governing-equation chain, software-pipeline diagram and
methodology-derivation diagram were regenerated without the PINN column,
box, node or stage. Removal sites carry a `PINN-HIDDEN` comment. The page
count dropped from 194 to 179 and the printed-to-PDF offset is now +25.

Terminology (2026-10-21). The first-principles premises are called
"theory anchors", not "axioms", throughout the thesis. Section 3.1, its
subsection, Table 3.1, the derivation-chain steps, the methodology-derivation
diagram (LAYER 1 / THEORY ANCHORS, TA1 to TA4, legend) and the
governing-equation chips and footer (TA1 to TA6, "Theory-anchor references")
all use the new name. Labels are sec:theory_anchors and tab:theory_anchors.

Optimizer conversion (2026-10-21). The main pipeline is analytical: the
headline heat flux is the closed-form Sutton-Graves correlation, not a
solver-resolved field. The default optimiser is now a simple genetic
algorithm (population 50, up to 200 generations, tournament selection k=3,
uniform crossover 0.7, Gaussian mutation 0.1, two elites, stagnation stop at
20 generations / 1e-6), driven by the Ada/SPARK runner with a Ravenscar
worker pool. Every Bayesian-Optimization reference was removed from the
thesis: Chapters 1, 2 (Section 2.15 rewritten), 3 (Section 7 rewritten and
the standards section retitled), 4 (the optimization sections rewritten from
the newest artifact, src/python/hiad_optimization_results.json, recorded
2026-10-20), 5, the abstract, the abstrak and the abbreviations. The
software-pipeline, governing-equation and methodology-derivation diagrams
were regenerated with GA labels, and three new GA figures (ga_convergence,
ga_ccd_screen, ga_design_trajectory) replace the Bayes-Optimization panels.
The recorded campaign converged in 72 generations (3600 evaluations) with a
composite cost of 2.7375 against a baseline of 3.4338 (-20.28 %), a drag
coefficient of 1.6677 (+3.76 %) and a total heat load of 250.45 J/cm2
(+20.12 %): the objective's drag weight selects the drag regime, and the
thesis reports that trade-off explicitly. The printed-to-PDF offset is now
+24 and the page count is 176.

Also preserve:

- The `hidelinks` setting — it is why link borders are zero. Do not remove it.
- `cover.tex` uses `ActualText={}` on the ITB logo. This is **intentional**
  (decorative image) and is not a missing alt-text defect.
- `preamble.tex` defines `\includegraphicsWithAlt` but never calls it. It
  is dead code, deliberately left in place; the live alt text is written
  as hand-authored `\BeginAccSupp{...}` blocks. Do not "fix" this by
  converting 49 hand-written blocks to the macro mid-reduction.
- The printed→PDF offset (+26) shifts whenever front matter changes. Every
  page reference in these notes must be re-derived after Lever B or D.

---

## 6. Verification protocol per cycle

The workflow that has been working, and should be repeated for each lever:

1. Apply one lever. One at a time — do not batch A, B and D together, or a
   regression cannot be attributed.
2. Build **two** `pdflatex -interaction=nonstopmode -halt-on-error main.tex`
   passes. Two passes are needed for the TOC/LoF/LoT page numbers to settle.
3. Read `main.log` for errors, undefined references, rerun requests, and
   count overfull/underfull boxes.
4. Render the affected pages to PNG with `pdftoppm -r 130`, then **look at
   them**. Do not infer layout from the log alone — the `[H]` dead space on
   p184 and the missing dot leaders on the Table C.2 List-of-Tables row
   were both invisible to the log and only found by rendering.
5. Re-run the §5 guardrail checks.
6. Commit with the repo's existing style: `fix(thesis): <imperative summary>`,
   plus a body explaining what changed and what was verified.
7. Push. The branch `main` tracks `origin/main`; push after each verified
   cycle rather than accumulating a large unpushed backlog.

### Two-pass builds are not always enough

The Table of C.2 List-of-Tables row lost its dot leaders because the caption
fills the measure to the right margin, leaving `\dotfill` zero width. It is
**not** clipped and **not** overflowing, and it is the only affected row in
the document. It is recorded in the `c51a379` commit message as a known
cosmetic artifact and was deliberately left unfixed, because the fix
requires editing the author's caption wording. If a later lever changes that
caption or the LoT width, re-check this row.

---

## 7. Useful commands

```bash
cd Lost+Found/ProgressReport/CurrentThesisFinalReport

# build
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex

# render a page for visual inspection
pdftoppm -f 184 -l 184 -r 130 -png main.pdf /tmp/insp

# authoritative chapter/section start pages (do NOT parse the PDF for these)
grep -oE '\\contentsline \{chapter\}\{[^}]*\}\{[0-9]+\}' main.toc

# page count + log checks
pdfinfo main.pdf | grep Pages
grep -c '^!' main.log
grep -ciE 'undefined (reference|citation)|There were undefined' main.log

# float pinning census
grep -c '\[H\]' chapter_0*.tex appendix.tex

# accsupp balance (comment-stripped)
# strip '(?<!\\)%.*' then count BeginAccSupp / EndAccSupp
```

Authoritative page starts at `c51a379` (printed):

```
Ch1 p1    Ch2 p13   Ch3 p74   Ch4 p117   Ch5 p145
References p149     App A p158   App B p163   App C p165   App D p167
```

---

## 8. State at handoff

```
branch        : main, tracking origin/main
HEAD          : c51a379  "fix(thesis): pluralise the table-of-contents and
                         references headings"
local == remote, working tree clean, 0 untracked
main.pdf      : 194 pages, 10,207,356 bytes
```

This file is the only uncommitted change. It is documentation, not part of
the thesis build — `main.tex` does not `\input` it, so adding it cannot
affect the PDF.
