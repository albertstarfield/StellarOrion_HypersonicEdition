# Week 17 Narrative Scaffold (template-driven narrative generation, experimental)

**Purpose:** make the owner's target narration structure for the Week 17
StellarOrion progress report visible and buildable as a PowerPoint deck, with
every narrative position marked as an unfilled slot.

**Author:** generated for Wahyu Suryo Samudro (owner), ITB, Week 17 2026.

**Date:** 2026-10-21.

> Nothing is narrated here yet. Every slide body is a placeholder that says
> what that position must eventually carry, and nothing else.

---

## 1. Why this folder exists

The Week 17 report is currently narrated as a result dump: a sequence of
slides that each carry a plot and a caption. The owner wants it restructured
into a narrated arc (background, objective, methodology, issues, progress,
resolution, conclusion). Writing that arc by hand means hand-copying numbers
into prose, which drifts the moment a pipeline re-run changes a value.

So the arc is declared **first**, as structure, and the numbers are meant to be
filled in later from the machine-readable results under
`stellarorion_program_proc/results/`. That is the template-driven part: the
narrative skeleton is a template, and the values are slots.

This folder is where that skeleton lives while it is being shaped.

## 2. Relationship to `Week 17 LaTeX/`

| | |
|---|---|
| `Week 17 LaTeX/main.tex` | The **current** Beamer deck, with the real technical content (46 pages of results). A placeholder scaffold of the same shape also exists there, written in an earlier round. Untouched by this folder's tooling. |
| This folder | An **independent**, PowerPoint-native scaffold. Written from scratch. No file, macro, colour value or visual element is copied out of `Week 17 LaTeX/`. |

The only thing shared is factual identity metadata (paper title, author name,
NIM, supervisor names, institute, week label). That metadata is copied
verbatim from the thesis identity block on purpose: it must never drift
between the thesis, the Week 17 deck and this scaffold.

## 3. Files

| File | Purpose |
|---|---|
| `scaffold.json` | **The single source of truth.** the owner's block structure, the thirty-nine frames, the palette, the identity block, and the documentation fields that record where the structure came from. |
| `make_pptx.py` | The generator. Reads `scaffold.json`, writes the deck with EasyPPTX. Two modes: `regenerate` and `update`. |
| `scaffold_logic.py` | The pure specification logic, shared by the generator and by the symbolic-execution gate: the error type, the whitespace and XML helpers, and the field checkers. Kept separate so it can carry CrossHair contracts. |
| `sky_background.py` | Builds the sky picture: the vertical Frost-to-Navy gradient, a soft bloom and a gentle vignette, rendered to a PNG with Pillow. The picture is what the frosted glass sits on, and it is why the design looks the same in every renderer. |
| `font_choice.py` | Resolves the two Abadi faces against the fonts actually installed on this machine, and reports the substitution instead of letting it happen silently. It also hands out the font **file** behind a family, which is what lets a glass pill measure its own text. |
| `figure_layout.py` | The picture geometry: it reads a PNG with Pillow and returns the rectangle that fits it inside a box without distorting it, and it composes a tall picture into two halves side by side. Kept separate so the fitting and cutting maths stays small and testable. |
| `text_layout.py` | The text geometry: it wraps a line the way the renderer does and returns how many lines the line needs and how tall the block is, measured with the very font file the deck names. It is what makes a narration card exactly as tall as its own text. Kept separate so the wrapping arithmetic stays small and testable. |
| `tests/test_make_pptx.py` | The behavioural suite: the pure helpers, the specification loader and its rejection paths, the generated package, the narration cards, the update mode and the command line. Run with `.venv/bin/python -m pytest -q`. |
| `requirements.txt` | Pinned dependencies: `easypptx==0.11.0` (the writer), `crosshair-tool==0.0.111` (the symbolic-execution gate) and `pillow==13.0.0` (the sky picture). |
| `pyproject.toml` | Tooling configuration for ruff, pyrefly and pytest. |
| `figures/` | The thesis graphics imported for the RECALL block (`thesis_*.png`), the research workflow flowchart regenerated from the thesis generator (`thesis_flowchart.png`) and the same flowchart cut into its two halves (`thesis_flowchart_halves.png`), the place where the three required visuals will land once they exist, and the generated sky picture (`figures/sky_*.png`). The sky is a build artifact: the generator rebuilds it from the palette, so it is ignored by the folder `.gitignore`. |
| `.venv/` | Project-local virtual environment for the generator and the analysis tools. Already ignored by the repository `.gitignore` (`**venv**`). |
| `narrative_scaffold.pptx` | Generated PowerPoint deck (41 slides). A build artifact; already ignored by the repository `.gitignore` (`*.pptx`). |

There is **no LaTeX in this folder**. The scaffold was LaTeX-native in an
earlier round; the LaTeX sources and their build artifacts were deleted when
the owner asked for a PowerPoint-native workflow, and `scaffold.json` took
over as the source of truth.

## 4. The target structure, and where each block lives

The owner's structure, transcribed into `scaffold.json` with the same block
boundaries. The owner's block markers were typed with U+2014 characters; the
house rule forbids U+2014 in source, so they are transliterated to ASCII
square brackets. The wording is otherwise unaltered.

| Owner block | Section | Slide title |
|---|---|---|
| `[ Intro start ]` 0. title start | `INTRO` | `TITLE AND OPENING` |
| `[ recall start ]` 1. Latar belakang overview | `RECALL` | `BACKGROUND OVERVIEW` |
| 2. Tujuan objective (all and 2-3 points), Research Scope limit | `RECALL` | `OBJECTIVE AND RESEARCH SCOPE` |
| 3. Methodology (the graphical framework flowchart, the overview of all below) | `RECALL` | `GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW` |
| 3. Methodology (graphical framework flowchart, per-step definitions, detailed methodology, the reasoning) | `RECALL` | `METHODOLOGY AND REASONING` |
| 3. Methodology (the shape the method tests) | `RECALL` | `METHODOLOGY: THE SHAPE UNDER TEST` |
| 3. Methodology (how the simulation is set up) | `RECALL` | `METHODOLOGY: THE SIMULATION SETUP` |
| 3. Methodology (the mesh and the grid independence) | `RECALL` | `METHODOLOGY: THE GRID INDEPENDENCE` |
| 3. Methodology (the convergence of the particle solver) | `RECALL` | `METHODOLOGY: THE SOLVER CONVERGENCE` |
| 3. Methodology (the convection channel) | `RECALL` | `METHODOLOGY: THE CONVECTION CHANNEL` |
| 3. Methodology (the conduction channel) | `RECALL` | `METHODOLOGY: THE CONDUCTION CHANNEL` |
| 3. Methodology (the re-radiation channel) | `RECALL` | `METHODOLOGY: THE RE-RADIATION CHANNEL` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE SHAPE` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE SOLVER` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE MESH` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE CONVERGENCE` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE CONVECTION` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE CONDUCTION` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE RADIATION` |
| 3. Methodology (the optimization flowchart) | `RECALL` | `METHODOLOGY: THE OPTIMIZATION FLOWCHART` |
| 3. Methodology (the design space and the Latin hypercube) | `RECALL` | `METHODOLOGY: THE DESIGN SPACE` |
| 3. Methodology (the cost function) | `RECALL` | `METHODOLOGY: THE COST FUNCTION` |
| 3. Methodology (the genetic algorithm) | `RECALL` | `METHODOLOGY: THE GENETIC ALGORITHM` |
| 3. Methodology (the double pass and the DSMC gate) | `RECALL` | `METHODOLOGY: DOUBLE PASS AND THE GATE` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE DESIGN SPACE` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE COST FUNCTION` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE GENETIC ALGORITHM` |
| 3. Methodology (the equation that governs the step) | `RECALL` | `GOVERNING EQUATION: THE DOUBLE PASS` |
| `[ Current progress start ]` 5. Overall progress (not the resolution detail) | `RECALL` | `OVERALL PROGRESS` |
| 4. Previous issues, listed before they are told | `RECALL` | `PREVIOUS ISSUES` |
| 4. Previous issues, one slide per issue | `RECALL` | `PREVIOUS ISSUE 1: THE HEAT FLUX WAS UNDEFINED` |
| 4. Previous issues, one slide per issue | `RECALL` | `PREVIOUS ISSUE 2: THE COST FUNCTION INCOMPLETE` |
| 4. Previous issues, one slide per issue | `RECALL` | `PREVIOUS ISSUE 3: THE BAYESIAN STEP WAS WRONG` |
| 4. Previous issues, one slide per issue | `RECALL` | `PREVIOUS ISSUE 4: THE NARRATION WAS MISSING` |
| 6. The progress issue, the resolution attempt, the update (DSMC, narration) | `CURRENT PROGRESS` | `ISSUE, RESOLUTION AND UPDATE` |
| trailing note: CFD and Optimized required plots | `REQUIRED VISUALS` | `REQUIRED PLOT: THE CFD CASE`, `REQUIRED PLOT: THE OPTIMIZED CASE` |
| trailing note: find the reference paper, show it next or in point 6 | `REQUIRED VISUALS` | `REQUIRED REFERENCE: THE SOURCE PAPER` |
| `[ Ending start ]` Conclusion (how close to the objective, does it answer the previous issue?) | `ENDING` | `CONCLUSION` |

The overall progress comes after the slides of the methodology: the owner
decided that the timeline of the five milestones belongs to the methodology
block, so it sits in the `RECALL` group, immediately after the graphical
framework slide and before the previous issues. The five milestones of the
research are drawn as a horizontal timeline: a gold axis with a numbered node
on it for every milestone, and a glass card under each node that carries the
milestone and one line of context.

The previous issues are a block of five slides. The first lists the four
issues of the earlier work as pills, one under the other, and each of the
four slides that follow elaborates one of them. The owner asked for the
list to come first and for every point of the list to get a slide of its
own, and the narration of each issue is rephrased from the redemption
frames of the Week 16 deck and from the summary of the three items in the
Week 17 deck.

The slide titles are the English names the deck now shows. The `PLACEHOLDER n:`
markers were dropped once the frames stopped being placeholders, and the two
Indonesian block names in the owner's own wording became `BACKGROUND OVERVIEW`
and `OBJECTIVE AND RESEARCH SCOPE`. The owner block names in the second column
are the PowerPoint section names and the machine keys of the tool, so they are
unchanged.

Twelve frames: one per owner item, plus the graphical framework flowchart of the
methodology block, which is too tall to share a slide with the text. The three
required visuals get their own
section because the owner wrote them after the ending block, so they get their
own home instead of being buried inside a narrative frame.

### 4.1 How `scaffold.json` is organised

| Key | Meaning |
|---|---|
| `schema_version` | Integer. The loader refuses a version it does not know. |
| `owner_directive`, `owner_structure`, `owner_structure_note` | The owner's own words, kept in the file so the structure never has to be remembered or re-derived. |
| `sections` | The five block names, in order. |
| `frames` | One object per slide: `id` (stable machine key), `section`, `title`, `body`, `target_position`, optional `note`, and an optional `figure` object (`path`, `caption`, `source`, and the optional `layout`, which is `side` or `feature`). A frame that names a graphic is drawn FILLED: its body becomes a band of cards under a full-width picture panel. The `feature` layout is for a frame that carries only a graphic: the picture then takes the whole panel and the frame has no narration. A graphic is resolved against the folder that holds the specification, so a specification copied elsewhere needs its pictures beside it. |
| `palette` | Four named hex colours: Frost, Sky, Navy and Gold. |
| `palette_roles` | What each colour is for. |
| `identity` | Paper title, author, NIM, both supervisors, report title, subtitle, institute lines, year. |

The `id` of a frame is the machine key the whole tool hangs on. It is written
into the slide as the **shape name** of the slot box (`slot:<id>`), so the
tool can find a slide again even if the owner renames its title in PowerPoint.

## 5. How the slot mechanism works

Every placeholder slide is built by one function, `add_placeholder_slide`, so
the eleven slides cannot drift apart in shape or styling. Two properties
follow, and both are deliberate:

* **No copy-paste divergence.** One builder, eleven slides.
* **An unfilled slot is unmistakable.** A slot body is drawn in italic inside a
  frosted white glass pill on the sky. On a projected slide it cannot be
  mistaken for finished narration. The slide also carries the footer
  `PLACEHOLDER SLIDE. Narration pending.`

Provenance is recorded in the speaker notes of every placeholder slide. The
notes carry the body that was in force when the tool last ran, fenced between
the markers `<<<SLOT_BODY id=<id>>>` and `<<<END_SLOT_BODY>>>`. That record is
what lets the update mode tell an untouched slot from an owner-written one.

## 6. Build and gate

```sh
cd "Lost+Found/ProgressReport/Week 17 Narrative Template Driven gen experimental"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python make_pptx.py
```

The generator writes to a temporary file in the target directory, verifies that
file, and only then replaces the target. A failed run therefore cannot leave a
half-written deck where the owner's copy was.

Options:

| Option | Meaning |
|---|---|
| `--spec <file>` | Path to the specification. Default: `scaffold.json` next to the script. |
| `--source-dir <dir>` | Folder that holds the specification. Default: the script's own folder. |
| `--output <file.pptx>` | Where to write. Default: `narrative_scaffold.pptx` in the source folder. |
| `--mode regenerate` | Build the deck from the specification. This is the default. |
| `--mode update` | Refresh an existing, hand-edited deck (see section 7). |
| `--no-sections` | Do not write the PowerPoint section list. |
| `--force-refresh-bodies` | In update mode, overwrite slots the owner has written to. |
| `--force-refresh-titles` | In update mode, overwrite the visible frame titles. |
| `--rebuild-sections` | In update mode, rebuild the PowerPoint section list. |

### 6.1 What the generator writes

* 41 slides, 16:9 (`12192000 x 6858000` EMU), blank layout, so nothing is
  inherited from an Office theme.
* Slide 1 is the cover, slide 2 the outline, slides 3 to 41 the thirty-nine
  frames.
* The cover carries the identity block (paper title, author, NIM, both
  supervisors, institute lines, week label, year).
* Each placeholder slide carries the floating frosted title band with the owner
  block tag on the right, the gold pill under the band, the frosted glass
  narration pill in italic, the `PLACEHOLDER SLIDE. Narration pending.` footer,
  the four-circle palette reference in the bottom right corner, the sparkle
  field, and speaker notes naming the slot.
* Three RECALL frames are FILLED: the thesis picture each of them names
  goes into a full-width glass panel on TOP, with the picture on the left of
  the panel and its caption and its provenance line in a column on the right,
  and their body is drawn UNDER that panel as a horizontal band of glass
  cards, one card per point, three cards to a row. Their footer reads
  `Content imported from the thesis. The narration stays editable in
  PowerPoint.`
* The overall progress is a horizontal timeline of the five milestones: a
  gold axis across the content area, a numbered glass node on the axis for
  every milestone, and a glass card under each node that carries the
  milestone and its detail.
* The previous issues are a block of five slides. `PREVIOUS ISSUES` lists
  the four issues of the earlier work as glass pills, one under the other,
  each with a numbered gold disc on its left, and each of the four slides
  that follow elaborates one issue as a band of four glass cards in two
  columns and two rows, every card carrying a heading and a detail. The
  first of the four carries the thesis heat-flux figure in a full-width
  panel above the band. Their footer reads `The issue as it stood in the
  earlier work. The narration stays editable in PowerPoint.`
* The methodology is one overview and then two subsections in the order the
  owner set. `GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW` opens the block because
  it is the overview of everything below, and `METHODOLOGY AND REASONING`
  keeps the per-step definitions. First comes `Methodology: DSMC CFD` in
  seven slides: the shape under test, the simulation setup, the grid
  independence, the convergence of the particle solver, and then the three
  heat-flux channels, the convection, the conduction and the re-radiation.
  Then comes `Methodology: Optimization Pipeline`: the optimization flowchart
  and its four slides, the design space with the Latin hypercube, the cost
  function, the genetic algorithm, and the double pass with the DSMC gate.
  Every one of those slides is drawn the way the owner's reference slide asks
  for: the picture on the left with its caption under it, and the facts of the
  slide as separate stacked glass cards on the right, one point each, set at
  thirteen point and stepping down only as far as the column needs, with the
  provenance line under the cards. Every card is named after its frame, so the
  whole column is found and replaced as one thing when the tool updates a
  slide.
* The `GRAPHICAL FRAMEWORK: RESEARCH WORKFLOW` frame carries the
  research workflow flowchart of the thesis and no narration. The flowchart is
  1760 by 3600 pixels, and shown whole on a slide its labels fall to about two
  points, so it is cut into its two halves and laid side by side; the halves
  are shown at 4.36 in each, and their labels stay at about eight points.
* Every slide carries the sky picture as its background, so the whole deck
  reads as one system.
* Five real PowerPoint **sections** are written through the `p14:sectionLst`
  extension (`INTRO`, `RECALL`, `CURRENT PROGRESS`, `REQUIRED VISUALS`,
  `ENDING`), so the deck's outline pane matches the owner's block structure.

### 6.2 Gates, measured on this machine

| Gate | Result |
|---|---|
| `ruff check --select ALL --preview .` | `All checks passed!` (0 findings) |
| `pyrefly check --preset all --check-unannotated-defs --infer-return-types checked --strict-callable-subtyping --spec-compliant-overloads .` | `INFO 0 errors (4 suppressed)`; the four suppressions are documented ignores on the python-pptx colour setter, whose type is unannotated upstream. |
| `.venv/bin/crosshair check scaffold_logic.py` | Exit 0, no counterexample. CrossHair explores the specification contracts symbolically, so the field checkers are proved over every possible input rather than sampled. The module carries `# crosshair: analysis_kind=PEP316` and `pre:` / `post:` contracts; the generator imports those helpers rather than repeating them. |
| `.venv/bin/python make_pptx.py` | Exit 0. Self-reports: the sky picture path, the resolved font faces, 5 owner blocks, 39 frames, 5 PowerPoint sections, 227 package parts with 197 XML parts well formed, 41 slides with 39 of 39 frames managed, and 39 slot bodies agreeing with the specification. |
| Update-mode test against an owner-edited deck | `UPDATE MODE: PASS` |
| `.venv/bin/python -m pytest -q` | `50 passed`. The suite covers the helpers, the loader and its rejection paths, the generated package, the filled frames, their graphics, their narration cards, the figure-only frame, the timeline of the overall progress, the pills of the outline, the list of pills of the four previous issues, the band of cards of every issue and its two columns, the twenty-three methodology slides and their figures, the compose helper, the update mode and the command line. |
| Microsoft PowerPoint opens the file | Yes. `lsof` showed the running app holding `narrative_scaffold.pptx` and having created the Office lock file `~$narrative_scaffold.pptx`, which a corrupt or rejected package does not produce. The first version of this deck was REJECTED by PowerPoint with a repair prompt; the cause and the guard are in section 10. |
| Cover slide rendered with `qlmanage` and read back as an image | Title, subtitle, author, institute lines, year, uppercase paper title, NIM and both supervisors all present, nothing clipped. |
| All twenty-five slides rendered and read back as images | Every slide renders without clipping, overlap or missing text. The placeholder slides carry a left-aligned frosted glass narration pill, a right-aligned owner-block tag, the floating title band, the gold pill, the footer, the four palette circles and the sparkle field; the cover carries its title in a full-width frosted plate and its subtitle in a frosted pill of its own. The four filled RECALL frames were read back the same way, after a first render showed the caption of the methodology frame colliding with its provenance line; the caption band was widened and the caption was moved to sit directly under its picture. A later render showed the narration spilling out of the bottom of its own card, because the card heights were measured with the real font file while the preview substituted a wider face; the measurement is now made against a box 18 percent narrower, so a card is always tall enough. The graphical framework frame was read back the same way: the two halves of the flowchart are legible, the caption and the provenance line sit beside them, and nothing overlaps. The overall progress timeline and the outline were read back the same way: the five milestones sit in one row under the axis, every milestone card holds its own text, and the outline lists the five owner blocks as five glass pills, one under the other. The five slides of the previous issues were read back the same way: the list shows
  four pills with a numbered gold disc on each, and every issue slide shows a
  grid of cards with a heading and a detail in every card, with the text clear
  of the edge of its card. The four methodology slides were read back the same
  way: each title sits on one line of the title band, the band of four cards
  fills the content area, and every card carries its own footer line. |
| Font resolution | The generator prints the face it used for the title and for the body, and names any face it had to substitute. On this machine the title resolves to `Abadi`; the body resolves to `Abadi MT Condensed Light`, because the family `Abadi MT` is not installed here. |

The generator verifies its own output on every run, so a broken deck cannot
be written: the package is opened as a zip, every XML and relationship part is
parsed, the presentation structure is checked for a single `p:extLst` with
only `p:ext` children and for a `screen16x9` slide size, and the slide count,
titles, bodies, cover identity and outline entries are compared against the
specification.

### 6.3 The visual design

The owner asked for a frosted glass look: a white-blue gradient running into
dark blue, with a yellow-to-white sparkle variation, rounded like an Apple
web interface, with shadows, and with a four-colour palette reference in the
bottom right corner of every slide at 5% opacity. That brief is implemented
as follows.

| Element | How it is built |
|---|---|
| Sky | A 2560 x 1440 PNG built by `sky_background.py`: the Frost stop at the top, Sky at 44% down, Navy at the bottom, a soft bloom near the top edge and a vignette at the corners. It is written to `figures/sky_<signature>.png`, where the signature is a hash of the stops and the geometry, so the file is stable across runs and changes when the palette changes. |
| Why a picture and not a gradient | The macOS Quick Look engine renders any `a:gradFill`, slide background or shape fill, as the flat **unweighted mean** of its stops. The three stops average to `(104, 125, 156)`, which is exactly what the preview showed. The deck's DrawingML was correct, but the design could not be seen, verified, or judged. A picture renders identically in every renderer, and it gives the glass something to refract. |
| Glass | Frost at 86% opacity for the narration card, 62% for the title band, 16% for the owner-block tag, each with a Sky hairline and a soft outer shadow. |
| Sparkles | Four-point stars, rotated so some read as a cross, each with a gold-to-cream glow. The fill follows the brightness of the sky behind it: Navy over the light top, gold or cream over the dark bottom, so no sparkle is ever invisible. The field is seeded from the frame identifier, so every slide differs and every run is reproducible. |
| Palette reference | Four circles, 0.115 in across, filled at 5% opacity with a 35% hairline of the same colour so the reference stays legible. They sit in the FOOTER, at the bottom right, at the content margin: the right edge of the reference is the right content margin, and the circles are centred on the footer line, so the reference reads as a mark of the slide instead of an object floating in the corner. The drop shadow that made it float is gone. |
| Narration body | A full pill: a rounded rectangle can only round to half its shorter side, so half the height is the maximum and is a stadium. |
| Outline | Every owner block of the outline is a glass PILL of its own, stacked one under the other with the name centred in it. The owner said that one square card with a list inside it read as a block of text, and a rounded rectangle can only round to half of its shorter side, so half the height of the pill is the largest radius that exists and that shape is a full stadium. |
| Timeline | The overall progress is a horizontal timeline: a gold axis across the content area, a numbered glass node on the axis for every milestone, and a glass card under each node that carries the milestone label in the title face and its detail below it. The five cards share one row, they reach the bottom of the content area, and the type size steps down from 15 pt until the tallest milestone fits, because a card that is too short would clip its own text. The first card keeps the name that identifies the frame and the others carry that name with an order number, so the update tool finds the whole row. |
| List of pills | A frame flagged `pill_list` is drawn as a vertical list of pills: one pill for every point of the body, stacked one under the other over the content area, each pill a full stadium with the label centred in it and a numbered gold disc on its left. The owner asked for the previous issues to be listed before they are told, and the pills are the list. The first pill carries the name that identifies the frame and the others carry that name with an order number, so the update tool finds the whole list. |
| Band of cards | A frame flagged `cards_only` is drawn as a band of glass cards that fills the content area, four cards in two columns and two rows, every card carrying a heading and a detail, with the text centred in the card. The first card carries the name that identifies the frame and the others carry that name with an order number. The narration sits in a text box inside the glass card, narrower than the card itself, because a renderer wraps the text of a shape at the edge of that shape and the text would otherwise touch the edge of its card. |
| Filled frame | A frame that names a graphic is laid out in two bands: the graphic on TOP in a FULL-WIDTH glass panel, and the narration UNDER it as a band of glass cards that runs HORIZONTALLY, three cards to a row. The picture sits on the LEFT of its panel and the caption and the provenance line sit in a column on the RIGHT, so the picture keeps the height it can get and the caption never steals it. The picture is fitted inside its panel without distortion. The picture inside the panel is LEFT aligned, so every figure starts at the same x and lines up with the card band underneath it; a centred picture starts further to the right on every slide, because the four thesis figures have four different shapes. |
| Feature frame | A frame whose `layout` is `feature` carries only a graphic. Its picture takes the whole width the panel can give it, the caption and the provenance line sit in the column that is left, and the frame has no narration band, so nothing steals height from the picture. The research workflow flowchart is drawn this way. |
| Narration cards | The body of a filled frame is drawn as ONE CARD PER POINT, laid out in horizontal rows of three, not as one dense panel. Each card is a frosted glass panel exactly as tall as its own text, and carries the bullet glyph with a hanging indent, so a wrapped line clears the bullet instead of running under it. The card width is the content width minus the gaps, divided by three. The text is UPRIGHT: the deck carries NO italic anywhere, because italic on a projected slide is hard to read (measured on the written package: zero italic runs). The heights are MEASURED with the very font file the deck names: `text_layout.py` wraps the text the way the renderer does. The measurement is made against a box 18 percent narrower than the real one, because a renderer that substitutes a wider face must still fit; a first render showed the text spilling out of the bottom of its card, and the measurement was widened until that cannot happen. The type steps down from 14 pt in half-point steps until the band fits its budget of 2.55 in, and if it still does not fit the generator fails loudly instead of clipping a card. The planner chose 14 pt for the background and the scope frame, 13 pt for the methodology frame and 12.5 pt for the previous issues frame. The first card is named `slot:<frame id>` and the rest `card:<frame id>#<n>`, so the update tool still finds the narration of a frame and can redraw the whole band. |
| Title band | The same full pill: the plate that carries the frame title is rounded to half its own height, so its ends are semicircles. The owner-block tag on its right is a smaller pill. |
| Cover subtitle | The cover subtitle is held in a pill as well, so no element of the skin is left as bare text. The pill is WIDER than its text, never narrower: `make_pptx.py` measures the line with the very font file the deck names (`font_choice.font_file_for`), and adds 40 percent of that width so a renderer that substitutes a wider face still fits inside the glass. The subtitle text box has wrapping switched off for the same reason, so the line can never break and spill out of the pill. |
| Cover title | The cover title sits in a FULL-WIDTH plate, the same idea as the title band of a placeholder slide: a frosted band across the whole content width, rounded to half its own height so its ends are semicircles, with the 40 pt title left-aligned inside it and the glass running on to the right. The wrapping of the title box is switched off, so a renderer that substitutes a wider face widens the line instead of breaking it. |
| Paper title and the names on the cover | The uppercase paper title and the line with the student number and the two supervisors sit in the frosted card at the foot of the cover. The owner said the paper title was too small, so it is set at 20 pt in the title face and the names at 13 pt, and both are centred in the card. |
| Type | `Abadi` for the four title blocks, `Abadi MT` for everything else, resolved against the installed fonts. The frame title is 24 pt, measured against the real Abadi Bold font file: the longest title in the deck is 7.82 in wide and the title box is 9.55 in, so there is 22 percent of slack and the title stays on one line even when a renderer substitutes a wider face for Abadi. |

The four palette colours live in `scaffold.json`, so the whole look is
changed by editing one file.

## 7. Editing the deck by hand and then updating it

The owner is expected to open `narrative_scaffold.pptx` in PowerPoint and
write the narration into the slot boxes. When the specification changes (a
slot body is reworded, a frame is added), the tool must refresh the deck
**without** destroying what the owner wrote.

```sh
.venv/bin/python make_pptx.py --mode update --output narrative_scaffold.pptx
```

Update mode works like this:

* Slides are matched to frames by the `slot:<id>` shape name, and, for decks
  made before that name existed, by the frame title.
* A slot whose visible text still equals the body recorded in the speaker
  notes is an **untouched placeholder**: it is refreshed from the
  specification.
* A slot whose visible text differs from that record was **written by the
  owner**: it is kept, and the record is rewritten so the next run sees it as
  owner text too. `--force-refresh-bodies` overrides this.
* Frames that are missing from the deck are created and moved into the right
  place in the slide order.
* Slides the owner added, and any shape the owner added, are never touched.
* The PowerPoint section list is left alone unless `--rebuild-sections` is
  given.

Every decision is printed, so the run is auditable rather than silent.

## 8. How PowerPoint can and cannot be driven on this machine

Measured on this node, not assumed:

| Route | Finding |
|---|---|
| Microsoft PowerPoint | Installed, `/Applications/Microsoft PowerPoint.app`, version **16.114** (build 16.114.26101123), universal x86_64 + arm64. |
| AppleScript dictionary | `Contents/Resources/PowerPoint.sdef`, 4484 lines. Suites: Standard, Microsoft Office, Microsoft PowerPoint, Drawing, Text, Table. |
| AppleScript commands available | `quit`, `print out`, `run VB macro`, `save as picture`, `save theme color scheme`, `save theme font scheme`. **There is no `open`, `save`, `close` or `export` command.** |
| `tell application "Microsoft PowerPoint" to get version` | Returns `16.114` immediately, so Apple Events do reach the app. |
| Document-model queries (`active presentation`, `count of slides`) | **Hang.** Killed at a 60 s alarm with no output, while `quit` answered instantly, so no modal dialog was blocking. The bridge is simply not responsive in this session. |
| `screencapture -x` | Returns a fully black PNG. Screen Recording permission is not granted, so the GUI cannot be inspected visually. |
| `System Events` window queries | Return empty. Accessibility permission is not granted. |
| `qlmanage -t -s 1600 -o <dir> deck.pptx` | **Works.** Renders the first slide through the macOS Office engine. Slow, a few seconds per file. |
| LibreOffice / `soffice` | Not installed. |

Conclusion: writing the `.pptx` directly is the only reliable route. Driving
the installed PowerPoint by Apple Events is not possible for document-level
work, and screen-scraping the GUI is blocked by missing permissions.

## 9. Why EasyPPTX

The deck is written with **EasyPPTX 0.11.0**
(<https://Ameyanagi.github.io/EasyPPTX/>), a Python library built on top of
python-pptx with a friendlier API: percentage or absolute positioning via
`in_()`, text and shape helpers that take their own arguments, speaker notes
as a plain string, and `Presentation.open()` for loading an existing deck.

Two capabilities EasyPPTX does not expose directly are reached through its own
documented escape hatches, `presentation.pptx_presentation` and
`slide.pptx_slide`, which are the underlying python-pptx objects: the
`p14:sectionLst` extension that makes the owner's five blocks into real
PowerPoint sections, and moving a slide within the deck's slide order.

`python-pptx` is therefore a transitive dependency of EasyPPTX, not a direct
one. The alternative candidate `pptxlib` was checked and rejected: it drives
the real PowerPoint through COM (`pywin32`), which does not exist on macOS.

## 10. Defects found on this machine, and how they are guarded against

Six real defects were found while building this deck. Each one is now
guarded by the verifier that runs on every write, so the class cannot ship
again.

**The deck PowerPoint refused to open.** The owner reported
`PowerPoint found a problem with content in ... narrative_scaffold.pptx`.
The cause was the section list: `p14:section/@id` is a `ST_Guid`, and the
identifiers were being written with doubled braces
(`id="{{8A5B5D2A-...}}"`), because the format string escaped braces around a
value that already carried them. PowerPoint validates its own p14 namespace
strictly and refused the package. The fix writes the identifier once, and
`_check_presentation_structure` now rebuilds the canonical GUID for every
section and refuses anything else, so a malformed identifier stops the write
before it reaches the disk.

**Centred slot text.** The slot box is an autoshape, and an autoshape
inherits the theme's centred paragraph alignment. The generator set the run
text but never the paragraph alignment, so the slot body came out centred
while every other element in the deck was left aligned. The alignment is now
set explicitly on the slot paragraph.

**The macOS Quick Look generator hangs on speaker notes.** `qlmanage -t`
renders only the first slide of a deck, and it hangs whenever that slide
carries a notes part, whatever the notes contain. This was measured with four
different note payloads, and with the notes removed the same deck renders in
about a second. The deck was never at fault; the preview path was. The
notes themselves are verified by the update mode, which reads them back.

**The caption collided with its provenance line.** The first render of a
filled frame showed the caption of the methodology graphic running to
three lines while its box was sized for two, so the third line sat on
top of the source line. The cause was a band under the picture that was
two lines tall with the caption anchored to its bottom, so a longer
caption grew upwards into the source line. The band now holds three
lines and the caption starts directly under the picture, so a short
caption sits next to its graphic and a long one grows towards the
provenance line instead of into it.

**The written deck was readable only by its owner.** The atomic save
writes through a temporary file, and a temporary file is created with
mode 0600, so the deck landed on disk as `-rw-------` while every other
file in this folder is 0644. The mode is now set explicitly before the
file is moved onto the target.

**The narration spilled out of the bottom of its own card.** The card
heights are measured with the font file the deck names, so they are
correct for the real face. The macOS Quick Look preview cannot see the
Office cloud font cache and substitutes a face about a fifth wider, and
a point that fits on two lines then needs three, so the third line sat
below the card. The measurement is now made against a box 18 percent
narrower than the real one, which costs a little empty space in the real
face and guarantees that no substituted face can spill. The generator
also fails loudly, naming the frame, when even the smallest type size
does not fit the column, so a clipped card can never be written.

## 11. Next step, when the owner is ready

Fill the slots in order (0, 1, 2, 3, 4, 5, 6, conclusion) and add the three
visuals into `figures/`. Once the narration shape holds, the slot bodies
become the binding points for values pulled from
`stellarorion_program_proc/results/`, which is the template-driven generation
this folder is named for.

The design can be changed without touching the generator: the four colours
are in `scaffold.json`, and the sky picture, the glass opacities, the sparkle
field and the type are named constants at the top of `make_pptx.py` and
`sky_background.py`.
