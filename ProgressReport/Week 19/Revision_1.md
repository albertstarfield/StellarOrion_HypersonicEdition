# Revision 1: the owner's annotations on the Week 18 narrative deck

Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.

This file records, without changing anything, what the owner wrote on the deck
he saved on 27 October 2026, and what each note asks for. It is a reading of
his own copy, not a plan that has been applied.

## 1. What was read

| Property | Value |
|---|---|
| File | `narrative_scaffold.pptx` |
| Size | 9,349,440 bytes |
| Saved | 27 October 2026, 11:52 |
| Package | 269 zip parts |
| Application | Microsoft Macintosh PowerPoint (from `docProps/app.xml`) |
| Slides | 49 |

The file on disk is the owner's saved copy. The last build written by
`make_pptx.py` was 8,877,340 bytes at 09:18 with 268 parts, so he opened that
build, typed into it and saved over it.

Reading was read only: the package was opened from disk and inspected, and no
byte of it was rewritten.

## 2. Where his comments actually live

There are **no PowerPoint comment objects in the file**. A scan of the package
for `comment`, `annotation`, `commentAuthor` and `authors` returns nothing, and
there is no `ppt/comments/*.xml` and no `ppt/commentAuthors.xml`. So nothing
was written through Review, New Comment.

Every note he wrote is in the **speaker notes pane** of the slide it belongs
to. That is the right place for this deck, because the deck is built to keep
the narration editable per frame.

His slide text is **untouched**:

- A strict comparison of every card on every frame against `scaffold.json`
  (whitespace normalised, cards sorted by index) gives 0 mismatches.
- No text boxes were added. Shapes named `TextBox`, `Rectangle` or `Comment`
  do not exist in the package.

Notes census across the 47 frames and 49 slides:

| State of the note | Count | Slides |
|---|---|---|
| The owner's typed note | 18 | listed in section 3 |
| The generator's old placeholder template | 27 | listed in section 4 |
| Empty | 4 | 1 (cover), 2 (outline), 19 (radiation), 32 (double pass) |

None of the 47 frames carries the scaffold `note` field text in its speaker
note. The deck therefore promises editable narration per frame while only 18
frames hold any words.

## 3. His eighteen notes, verbatim, with what each one asks for

### Slide 3, BACKGROUND OVERVIEW

> 1. Bigger font or easier to read 2. Problem is missing? (after Literature
> review analysis) [Rigid?] Pros and Cons (if we Geometry Increase it or
> Shrink it) Oh and is it for optimized geometry (Is it Packable and
> inflatable? (Scope Elaborate, we only focus on optimized geometry on this
> slide)) 3. Scope

Three asks in one note: the body type is too small to read on the slide, the
problem statement is missing after the literature review, and the scope has to
say plainly that this work treats the optimised geometry only, while still
stating the rigid against inflatable trade and whether the body is packable.

### Slide 4, OBJECTIVE AND RESEARCH SCOPE

> Definition Overlap. Rigid vs Inflatable (and also Dimension Difference we
> are not) [Rigid vs Inflatable figures] Objective 1st : Let's not use SPARTA
> DSMC and Genetic Algorithm on technical on methodology and chapter II and
> Chapter III Objective (Rephrase it) (Without per variable optimized) (and -
> performance analysis) (How's the featurework going on the optimized
> geometry)

The objective is defined twice, so the overlap has to go. He wants rigid
against inflatable and its dimension difference kept in view, a rigid and
inflatable figure pair, the objective rephrased so it does not lean on SPARTA,
DSMC or the genetic algorithm as technique, and the phrase "per variable
optimized" dropped. Performance analysis stays. The last question asks how the
framework actually proceeds on the optimised geometry.

### Slide 5, GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW

> 1. Simulate the geometry in Mach 5-6 (On Setup) not on the methodology Next
> Question: For else is it valid? Steps that is missing on the validation
> Theoretically Valid comparison methodology (Duplicate detected on
> Theoritically Valid , thus remove from here) Optimization Pipeline before
> Data Analysis Simulation Since this is a Overview Research workflow
> flowchart

The Mach 5 to 6 simulation belongs on the setup stage, not scattered through
the methodology. He questions what else the workflow is valid for, says the
validation steps are missing, says the "theoretically valid comparison
methodology" box is duplicated and must go, and says the optimization pipeline
has to sit before data analysis and simulation in an overview flowchart.

### Slide 6, METHODOLOGY AND REASONING

> Re:Design Figure Is not focused here Stage Missing on the flowchart. Just use
> it manual. Duplkicates on Slide 5 Stage 5 and Stage 4 (swap)

The figure on this slide is not the point of the slide. A stage is missing from
the flowchart. The flowchart duplicates slide 5 and he would rather keep one
manual version. Stage 5 and stage 4 have to be swapped.

### Slide 7, METHODOLOGY: THE SHAPE UNDER TEST

> This is for No man sky stuff For Procedural Generation Display parameter math
> in the Shape against the How it will shaped (merge 7 and 8) No need seperation

The parameter mathematics reads like procedural generation rather than
engineering, so the parameters should be shown against the shape they produce.
He wants slide 7 merged with slide 8, its governing equation, with no
separation between them.

### Slide 8, GOVERNING EQUATION: THE SHAPE

> Kappa. It's missing citation source

The `kappa = 0.3667` constant needs its source cited.

### Slide 9, METHODOLOGY: THE SIMULATION SETUP

> Grid factor 0.7 but where's the cells total

The grid factor of 0.7 is stated but the resulting cell count is not.

### Slide 10, GOVERNING EQUATION: THE SOLVER

> Boltzmann How to explain it. Without Lattice but using No Time NTC No Time
> Counter. Overview? What can we get from here? how can we derive it Also df/dt
> (is Unsteady) (but why) Explain it.

The Boltzmann equation needs an explanation that does not lean on a lattice,
stated as the No Time Counter collision method. He wants the overview, what the
equation buys us, how it is derived, and why the `df/dt` term is unsteady.

### Slide 11, METHODOLOGY: THE GRID INDEPENDENCE

> QoL ?

An open question about quality of life on this slide, meaning the presentation
of the grid independence material should be easier to take in.

### Slide 13, METHODOLOGY: THE SOLVER CONVERGENCE

> Convergence might still happen

A caution that convergence may still occur, so the slide should not overstate
non convergence.

### Slide 16, GOVERNING EQUATION: THE CONVECTION

> Is this EMPIRICAL or analytical where is that Constant coming from also H is
> convective coefficient

He wants the Sutton-Graves correlation labelled as empirical rather than
analytical, with the origin of the constant, and he reads `H` as the
convective coefficient.

### Slide 18, GOVERNING EQUATION: THE CONDUCTION

> Conduction and Radiation ? T^4??

A question about why the conduction balance on this plate carries the
radiation term with `T` to the fourth power.

### Slide 22, METHODOLOGY: TPS MATERIAL PRESETS

> Slide 22 to 19 This is fragmented

The material table is fragmented by distance: it sits at slide 22 and he wants
it around slide 19, next to the validation material.

### Slide 29, GOVERNING EQUATION: THE COST FUNCTION

> Where'sthe objective Total Heat Load Objective

He asks where the total heat load objective is in the cost function, that is,
which term is the heat load term.

### Slide 31, GOVERNING EQUATION: THE GENETIC ALGORITHM

> Tournament Selection kt (3) Give definition (parameter and can be more
> optimized space in here)

The tournament size `k_t = 3` needs a definition, and he suggests the
parameter could take a wider range in the search space.

### Slide 34, METHODOLOGY: THE FLOWN TOPOLOGIES

> Topology comparison and Performance Analysis

The slide should compare topology and performance together, not topology
alone.

### Slide 35, METHODOLOGY: DRAG AND THE GATE

> Topology Is missing

The topology itself is missing from the drag slide.

### Slide 36, METHODOLOGY: TPS OF BOTH BODIES

> Methodology and Result Don't fuse it like that bruh

Methodology and result should not be fused on one slide.

## 4. The twenty seven slides whose notes are still the placeholder

Slides 12, 14, 15, 17, 20, 21, 23, 24, 25, 26, 27, 28, 30, 33, 37, 38, 39, 40,
41, 42, 43, 44, 45, 46, 47, 48, 49.

Every one carries the generator's template text, which begins `PLACEHOLDER
SLIDE. The slot is unfilled on purpose` and ends with the `<<<SLOT_BODY>>>`
machine block. So more than half the deck has no narration at all, which is
the gap the owner's own notes expose: the deck claims editable narration per
frame.

## 5. Three structural asks his notes imply, none of them applied

1. **Merge the shape slide with its equation** (slide 7 note). This removes one
   frame and one slide.
2. **Move the TPS material table to slide 19** (slide 22 note). This reorders
   frames without changing the count.
3. **Swap stage 5 and stage 4 in the workflow flowchart** (slide 6 note). This
   is a picture edit of `figures/thesis_flowchart_halves.png`, not a text edit.

## 6. Handling warning

The file on disk is his annotated copy. Running `make_pptx.py` writes
`narrative_scaffold.pptx` from `scaffold.json` and would destroy the eighteen
notes in it. Any rebuild has to come after his copy is set aside, and every
note has to be folded into `scaffold.json` first, either as the frame `note`
field or as the narration that replaces the placeholder.

## 7. What was applied in this pass

His annotated copy is preserved untouched at
`tools/backups/narrative_scaffold_owner_revision_1.pptx` (9,349,440 bytes).
The scaffold backup is `tools/backups/scaffold_before_revision_1.json`.

| Slide | Change |
|---|---|
| 3 | Four shorter bullets, so the type is larger, with the problem and the scope added |
| 4 | Duplicate objective removed and rephrased without naming SPARTA or the genetic algorithm; rigid against inflatable added |
| 6 | Stage 4 and stage 5 swapped, so validation and analysis precede the optimization |
| 8 | New bullet giving the origin of kappa: 0.55 m nose radius over 1.5 m body radius |
| 9 | Cell total added: 139 by 139 is 19,321 cells |
| 11 | Last bullet relabelled Quality, with skewness and orthogonal quality named |
| 13 | Last bullet now says convergence is judged on retention and stationarity, not a residual floor |
| 16 | Constant marked as fitted for air; origin bullet now says empirical and names the Fay-Riddell layer |
| 18 | New bullet explaining why radiation carries T to the fourth power |
| 19 | TPS material table moved to sit with the TPS channels, right after the conduction equation |
| 29 | New bullet naming the heat load term as the first and heaviest objective |
| 31 | New bullets defining the tournament and what k_t sets |
| 34 | Performance deltas added: surface load, area-averaged flux, peak flux |
| 35 | Topology of each run added, with the caveat that pass-2 is a 6.0 m body on the 3.0 m path |
| 36 | Retitled RESULTS: TPS OF BOTH BODIES, subtitle Results: TPS Response, first bullet marked Result |

Deck rebuilt: 49 slides, 47 of 47 frames managed, 47 slot bodies agree. Slides 3, 6, 18, 19, 34, 35 and 36 rendered and read back clean.

Still open from his notes, because each needs a new or edited picture rather than text:

1. Slide 5 and slide 6: the workflow flowchart needs the duplicate validation box removed and stage 4 and 5 swapped inside `figures/thesis_flowchart_halves.png`.
2. Slide 7: merging the shape slide with its governing equation needs one composed plate holding both, since a frame carries one figure.

## 8. What is not in this file

- No note of his was paraphrased into the deck.
- No slide text was changed.
- No frame was moved, merged or removed for this revision.
- Nothing is committed. The Week 18 folder is still untracked.
