# Standard Operating Procedure of CFD

<!--
================================================================================
SOP header — provenance and standing of this document
================================================================================

AXIOMS
------
A1. STATUS QUO, NOT PRESCRIPTION. This records how the Ansys Workbench CFD
    chain (geometry -> mesh -> Fluent -> results) is conventionally operated,
    as practice is typically performed. It is not a project mandate and does
    not yet describe this repository.
A2. TOOL ANCHOR. Stage names follow the Ansys Workbench "Fluid Flow (Fluent)"
    analysis system: Geometry -> Mesh -> Setup -> Solution -> Results.
A3. DETAIL LEVEL. Menu paths move between releases, so stage intent, inputs,
    gates and exit criteria are stated, and only release-stable interface
    names are given.
A4. THRESHOLDS ARE EMPIRICAL. The mesh-quality figures are commonly cited
    acceptance bands, not proved values for any specific physics set.

THEORIES
--------
T1. The schematic is a directed acyclic graph of cells; each cell's output is
    an artifact consumed downstream, so an upstream change invalidates
    everything below it. Hence the SOP is ordered, and recovery means
    "rerun from the first invalid cell".
T2. Verification (solving the equations right) and validation (modelling the
    right thing) are distinct gates and are therefore separate chapters.
T3. A result that cannot be presented honestly is not finished work: the
    evidence chain (Ch. 12) precedes the presentation (Ch. 13).

APPLICATIONS
------------
    Audience: an engineer or student operating Workbench for a conventional
    internal/external flow study who needs the usual operating order, its
    gates, and the form in which results are shown to other people.

CITATIONS
---------
    [Citation: Ansys Help v242 — "Creating Fluent-Based Systems", cell
     sequence — https://ansyshelp.ansys.com/]
    [Citation: Ansys Help v251 — Orthogonal Quality metric —
     https://ansyshelp.ansys.com/public/views/secured/corp/v251/en/wb_msh/msh_orthogonal_quality.html]
    [Citation: Ansys SpaceClaim — geometry preparation —
     https://ansys.synopsys.com/products/3d-design/ansys-spaceclaim]
    [Reference: Ansys Fluent Meshing watertight/task-based workflow —
     https://simutechgroup.com/ansys-fluent-meshing-new-workflow-easier-and-faster-mesh-generation]

STATUS: status-quo reference for chapters 1-13. Sections 5.1, 6.1 and 12.5
        additionally record MEASURED instances for this repository
        (SPARTA/DSMC Cartesian grid + Ada/SPARK), emitted as files under
        stellarorion_program_proc/results/99_shared/sop/. Adaptation of the
        procedure itself beyond those measured records is still deferred
        until commissioned.
================================================================================
-->

This procedure describes the conventional operating sequence for a
computational fluid dynamics study in Ansys Workbench, from CAD through to
a reported result, and then the sequence for showing that result to other
people. Each chapter reads as a gate: what goes in, what is done, and what
must be true before moving on.

---

## Table of contents

1. [The Workbench project schematic](#chapter-1--the-workbench-project-schematic)
2. [Geometry preparation](#chapter-2--geometry-preparation)
3. [Mesh generation](#chapter-3--mesh-generation)
4. [Structured meshing](#chapter-4--structured-meshing)
5. [Mesh quality gates](#chapter-5--mesh-quality-gates)
6. [Mesh independence study](#chapter-6--mesh-independence-study)
7. [Fluent setup](#chapter-7--fluent-setup)
8. [Solution and convergence](#chapter-8--solution-and-convergence)
9. [Verification and validation](#chapter-9--verification-and-validation)
10. [Post-processing](#chapter-10--post-processing)
11. [Reporting and reproducibility](#chapter-11--reporting-and-reproducibility)
12. [Necessary solution and results procedure](#chapter-12--necessary-solution-and-results-procedure)
13. [Presenting solution and results to people](#chapter-13--presenting-solution-and-results-to-people)
14. [Common failure modes](#chapter-14--common-failure-modes)
15. [Gate checklist](#chapter-15--gate-checklist)

---

## Chapter 1 — The Workbench project schematic

Workbench is organised as a **project schematic**: a canvas of connected
cells. Adding the **Fluid Flow (Fluent)** analysis system drops one column
containing, in order:

| # | Cell | Purpose | Artifact produced |
|---|------|---------|-------------------|
| 1 | **Geometry** | Create or import the computational domain | geometry model |
| 2 | **Mesh** | Discretise the domain | mesh file (`.msh`) |
| 3 | **Setup** | Physics, materials, boundary conditions | case (`.cas`) |
| 4 | **Solution** | Iterate to convergence | solution data (`.dat`) |
| 5 | **Results** | Extract quantities and plots | contours, reports, exports |

Two structural facts drive the rest of this SOP:

- **Cells are ordered and dependent.** Editing Geometry invalidates Mesh,
  Setup, Solution and Results. Editing Setup invalidates Solution and
  Results. The recovery rule is therefore *rerun from the first invalidated
  cell*, not "fix the plot".
- **Data moves through shared links.** A cell can share its output with
  cells in other systems (for example a second Fluent system reusing one
  mesh), which is how parameter studies are arranged without rebuilding
  geometry.

**Typical operating order:** fill cells top-to-bottom, and move *up* only
when a gate fails for a reason that lives upstream.

---

## Chapter 2 — Geometry preparation

### 2.1 Which tool

- **SpaceClaim** is the current geometry editor: direct modelling aimed at
  simulation preparation rather than parametric feature history.
- **DesignModeler** is the legacy parametric alternative still present in
  older templates.

### 2.2 What "good" means here

The goal is not a pretty CAD file; it is a **watertight, solvable fluid
domain**:

1. **Import** the native or neutral CAD (STEP/IGES/native).
2. **Defeature** — remove chamfers, fillets, bolt holes and small embosses
   that are irrelevant to the flow but expensive to mesh. A common rule:
   remove anything smaller than the smallest flow feature you intend to
   resolve.
3. **Form the fluid volume, not the solid** — extract the enclosure, or
   boolean-subtract the body from a surrounding block for external flow.
4. **Add Bodies of Influence (BOI)** — invisible named volumes that exist
   only to carry local mesh sizing (a wake box, a boundary-layer box).
5. **Clean topology** — remove gaps, slivers and coincident faces; heal
   gaps; ensure faces meet.
6. **Decide sharing** — *Share Topology* (assembled/merged) makes coincident
   faces a single shared face so conformal cells meet across parts;
   separate contact sets produce non-conformal interfaces instead.
   Conformal is the usual default when the parts form one fluid domain.
7. **Name the boundaries** with meaningful named selections —
   `inlet`, `outlet`, `wall_nozzle`, `symmetry`, `farfield`. These become
   the boundary-condition identifiers in Fluent. This is the cheapest habit
   in the process, and forgetting it is the most common cause of rework.

### 2.3 Exit gate (geometry)

- Domain is closed/watertight; no stray edges or free faces.
- The **fluid** (not solid) volume is what will be meshed.
- Every physical boundary has a named selection.
- Estimated cell count is sensible for the intended study.

---

## Chapter 3 — Mesh generation

Three usual routes, chosen by problem shape rather than preference.

| Route | Typical use | Notes |
|-------|-------------|-------|
| **ANSYS Meshing** (the schematic's Mesh cell) | General 3D; tet-dominant with hex/wedge where possible | Integrated and shares geometry; suits most external flows |
| **Fluent Meshing** — task-based *watertight geometry* workflow | Large or production runs; one Fluent window for mesh and solve | Guided steps: describe geometry → import → select boundaries → surface mesh → boundary layers → describe geometry → volume mesh → update boundaries → write mesh |
| **ICEM CFD** | Structured hexa grids, multi-block | Explicit blocking; see Chapter 4 |

### 3.1 General sizing practice

- **Global sizing** sets the first, coarse level.
- **Local sizing** refines surfaces (leading edges, gaps, shear layers).
- **Bodies of influence** refine volumes (wakes, jets, mixing zones) without
  adding real surfaces.
- **Inflation / boundary-layer layers** are added at walls whenever a
  turbulence model with wall functions, or any resolved boundary layer, is
  intended. The first-cell height is driven by the target $y^+$, not by
  aesthetics — see Chapter 5.

### 3.2 The usual order of operations

1. Generate/import geometry; create named selections.
2. Surface mesh first; verify it captures geometry curvature.
3. Add inflation layers; verify first-cell height against target $y^+$.
4. Generate the volume mesh.
5. Run the quality metrics (Chapter 5) **before** leaving Mesh.
6. Only then transfer to Setup.

---

## Chapter 4 — Structured meshing

"Structured" here means **hexahedral cells arranged in a regular
(i,j,k)-ordered connectivity**, as opposed to tetrahedral or otherwise
unstructured fill. It is preferred because, for a given cell count, hex
cells usually give less numerical diffusion and better convergence — but
only when the mesh follows the flow and stays reasonably orthogonal.

### 4.1 The usual structured approaches

| Method | How it is applied in the Ansys ecosystem |
|--------|------------------------------------------|
| **Mapped / sweep** | ANSYS Meshing: a face mesh is *swept* through a volume to create prismatic hex rows; simplest structured path for extrudable shapes |
| **Multi-block (o-grid) blocking** | ICEM CFD: build an explicit block structure around the geometry, then `.o-grid` a block to resolve a body inside an annulus — the standard method for cylinders, ducts and external aerodynamic grids |
| **Inflation / hex-core** | Boundary-layer hex/wedge layers near walls with a tet or hex-core fill further out; a hybrid rather than pure structured mesh |
| **Structured Cartesian** | Uniform orthogonal cells; used by some DSMC/overset codes for shock-capturing simplicity |

### 4.2 What a structured blocking procedure normally looks like (ICEM CFD)

1. Import geometry; define parts/blocks for each named boundary.
2. **Blocking → Initialize** with a bounding box.
3. **Split** blocks to follow the dominant flow directions and geometry.
4. **Associate** block edges/vertices to geometry curves and points — the
   step that makes the grid fit the shape; association errors are the
   classic source of high skewness.
5. **O-grid** the block containing a body so cells wrap it circumferentially
   instead of clustering on a corner.
6. Align the boundary-layer direction; set edge parameters (bunching/number
   of points) for the near-wall rows.
7. **Pre-mesh** to preview; check quality; **Convert to unstructured mesh**
   and write an Ansys Fluent mesh.

### 4.3 The structured-mesh-specific checks

- **No fold-over**: mesh lines must not cross; the mesh check must report no
  negative volumes.
- **Block edges follow streamlines / body curvature**, not arbitrary lines.
- **Near-wall direction is normal to the wall** (this drives the inflation
  direction and hence $y^+$ accuracy).
- **Avoid abrupt size jumps**: consecutive growth rates stay moderate
  (commonly $\leq 1.2$–$1.3$).

---

## Chapter 5 — Mesh quality gates

These are the numbers typically inspected in the Mesh cell's quality display
before a mesh is allowed downstream.

| Metric | Definition (as given by Ansys) | Usual acceptance |
|--------|--------------------------------|------------------|
| **Skewness** | Deviation of a cell from its ideal shape; 0 = ideal, 1 = degenerate | `< 0.25` generally good; `< 0.5` acceptable; `> 0.7` threatens accuracy; `> 0.9` seriously problematic |
| **Orthogonal quality** | Minimum of the orthogonality and `1 − cell skewness`; 0 = poor, 1 = ideal | `> 0.1` minimum; `> 0.2` comfortable; `< 0.1` unacceptable |
| **Aspect ratio** | Longest to shortest edge | Near 1 in the bulk; higher tolerated only in thin boundary layers where stretching is intentional |
| **Growth rate** | Size ratio between adjacent cells | Typically $\leq 1.2$–$1.3$ |
| **First-cell height / $y^+$** | Derived from the boundary-layer target model | See below |

**$y^+$ is a design input, not an output.** The first-cell height is chosen
from the wall-unit requirement of the intended turbulence treatment —
low-$y^+$ near-wall resolution (order $y^+ \approx 1$) for integrated
boundary-layer resolution, or a wall-function band (order
$y^+ \approx 30$–$300$) otherwise. Choose the band first, then size
inflation from it; check the achieved $y^+$ from early iterations and revise
the mesh if it misses.

**If any gate fails:** do not compensate in the solver. Go back to local
sizing, association/blocking, or inflation, and re-check.

### 5.1 Where the gates discriminate, and where they do not

<!--
AXIOMS
------
A1. On an axis-aligned Cartesian grid the conventional shape metrics are
    degenerate by construction: every cell is rectangular, so skewness is 0
    and orthogonal quality is 1 regardless of what the solution does.
A2. A gate that cannot fail carries no information about the solution; it is a
    statement about the mesh topology.

THEORIES
--------
T1. The discriminating mesh records on such a grid are the cut-cell census at
    the body surface and the flow-volume closure residual, because those
    measure how the discretisation meets the geometry and whether the cellwise
    and global volumes agree.

APPLICATIONS
------------
    StellarOrion (SPARTA DSMC on a Cartesian grid) records skewness 0 and
    orthogonal quality 1 exactly, a growth rate of 1.00014123 against a 1.2
    limit, and a flow-volume closure of 1.33e-14 (00_reference) and 1.18e-14
    (03_opt_geometry) against a 1e-6 gate; the cut-cell census reads 18,746
    outside, 430 inside, 145 overlapping and 144 split, summing to the
    19,321-cell grid. Both evidence trees live in results/99_shared/sop/.

CITATIONS
---------
    [Reference: Ansys orthogonal-quality and skewness bands, Ch. 5 of this
     document - https://ansyshelp.ansys.com/]
-->

On an axis-aligned Cartesian grid the conventional shape metrics are
degenerate: every cell is rectangular, so skewness is exactly 0 and orthogonal
quality exactly 1 no matter what the solution does. Those rows stay in the
record — deleting them would let a later reader assume they had been tested —
but they are read as statements about the mesh topology, not as solution
evidence. The records that do discriminate on such a grid are the **cut-cell
census** at the body surface and the **flow-volume closure** residual, because
those measure how the discretisation meets the geometry and whether the
cellwise and global volumes agree.

---

## Chapter 6 — Mesh independence study

The status quo practice is a **mesh independence (grid convergence) study**:
repeat the same setup on at least three systematically refined meshes and
confirm the quantity of interest has stopped changing meaningfully.

Typical sequence:

1. Define three (or more) refinement levels — for example global scale
   factors `coarse / medium / fine` applied consistently.
2. Hold **all** other settings identical across levels.
3. Monitor the target observable (force coefficient, heat flux, mass flow)
   and the far-field solution, not just residuals.
4. Accept the mesh where the change between the last two levels is within
   the tolerance the study requires.
5. Where the change cannot be shown negligible, quote the observed
   convergence rate and an extrapolated/estimated uncertainty (the
   formalised form of this is the Grid Convergence Index).

Stopping at "the residuals are low on one mesh" is *not* a mesh independence
study.

### 6.1 Recorded study, and where its two gates disagree

<!--
AXIOMS
------
A1. A pairwise-change gate and an estimated-error gate answer different
    questions: whether the quantity of interest moved, and how far the finest
    mesh is estimated to sit from the converged value.
A2. The tolerance belongs to the study, not to the method; it must be recorded
    with its source and its date, or a later reader cannot tell which rule was
    in force.

THEORIES
--------
T1. With non-constant refinement ratios the extrapolated order inherits the
    asymmetry, so any extrapolated value and its index are estimates, not
    bounds.
T2. On a particle method the measured change mixes grid refinement with
    statistical sampling; the continuum value is reached only in the joint
    limit.

APPLICATIONS
------------
    A recorded three-level study of the SPARTA Cartesian grid refines 4,900,
    10,000 and 19,321 cells with every other setting held fixed and monitors
    the solver-resolved peak surface heat flux: 2.059e6, 1.946e6 and 1.797e6
    W/m2, giving successive changes of 5.488091% and 7.663952%.

CITATIONS
---------
    [Reference: convergence-index method as recorded by the project artifact
     results/99_shared/sop/grid_independence.json]
-->

A recorded three-level study of the SPARTA Cartesian grid refines 4,900, 10,000
and 19,321 cells with every other setting held fixed, and monitors the
solver-resolved peak surface heat flux: 2.059e6, 1.946e6 and 1.797e6 W/m2,
giving successive changes of 5.488091% and 7.663952%.

Two gates are applied to the same three levels, and they disagree:

- the **pairwise-change gate**, at the criterion adopted for the study (10%,
  widened from a 5% band on 2026-10-16), which 7.663952% passes;
- the **estimated-error gate**, written as the convergence index at 33.74%,
  which exceeds that same 10% tolerance.

The recorded artifact therefore reports the change as MET and the estimated
fine-mesh discretisation error as exceeding tolerance. Reporting only the
first gate would read as a clean pass; reporting only the second would read as
a failure. Both are carried, with the tolerance stated together with its
source and date, because step 4 of this chapter leaves the tolerance to the
study.

The convergence estimates are estimates and not bounds: the refinement ratios
differ across the levels (1.4285714 and 1.3900), so the observed order is
0.8427 and the safety-factor-scaled index inherits that asymmetry. The
particle census also rises with refinement (0.60, 0.85 and 1.19 million), so
the measured change mixes grid refinement with statistical sampling.

---

## Chapter 7 — Fluent setup

### 7.1 Solver selection

- **Pressure-based**: low-speed / incompressible and moderate-speed flows;
  default for most subsonic incompressible work.
- **Density-based**: compressible, high-speed flows with strong shocks, where
  a coupled density/energy solution is preferred.

This is the first physical decision, because it constrains the scheme and the
initialization that follow.

### 7.2 Models

Select in rough order of consequence:

1. **Dimensionality**: 2D planar / axisymmetric / 3D.
2. **Multiphase** (if applicable).
3. **Energy equation** on/off — required for heat transfer or compressible
   work.
4. **Turbulence model** — for example $k$-$\varepsilon$, $k$-$\omega$ SST,
   transition models, or laminar. The choice interacts directly with the
   $y^+$ band of Chapter 5.
5. **Species / reactions / radiation** as needed.

### 7.3 Materials, cell zones and boundary conditions

- Set fluid/solid **materials** and assign them to cell zones.
- Assign **cell zone** conditions (fluid vs solid, rotating reference frames,
  porous zones).
- Set **boundary conditions** on every named selection from Chapter 2 —
  velocity/pressure inlet, pressure outlet, mass-flow inlet, symmetry, wall
  (thermal condition), outflow. Verify *every* named selection has been
  reviewed, because Fluent will happily solve with a default condition you
  did not intend.

### 7.4 Interfaces

For non-conformal regions (sliding interfaces, two independently meshed
bodies, periodic pairs), define **mesh interfaces**; otherwise ensure shared
topology produced a conformal mesh and no interface is needed.

### 7.5 Exit gate (setup)

- Every boundary has an explicit, reviewed condition.
- The model list matches the problem statement; no default physics left
  unexamined (especially turbulence model and energy equation).
- Reference values set deliberately (they drive reported coefficients).

---

## Chapter 8 — Solution and convergence

### 8.1 Initialization

Choose **hybrid** or **standard** initialization. Good practice: initialize
from values close to the expected field (or run a cheap first pass) rather
than from a far-from-physical state that stalls.

### 8.2 Discretisation and controls

- **Spatial discretisation**: typically **second order** for final answers;
  first order may be used to start, but results reported from first-order
  schemes are not acceptable practice.
- **Courant number / relaxation**: start lower for stability, raise as the
  solution settles; pseudo-transient can be used to reach a steady answer
  faster when steady is the goal.
- Adjust under-relaxation factors only with a reason, and record the reason.

### 8.3 Monitors, not just residuals

Convergence in practice is judged by **three** things agreeing:

1. **Residuals** fall and flatten (typically several orders of magnitude),
2. **Monitored quantities** (lift/drag, mass imbalance at the outlet, heat
   transfer at a wall) reach a steady plateau, and
3. **Inlet–outlet balances** close (mass flow in ≈ mass flow out).

A residual plot alone is not convergence.

### 8.4 Exit gate (solution)

Monitors are flat over a run of iterations, residual targets met, balances
closed, and the solution has not drifted — with all three recorded (see
Chapter 11).

---

## Chapter 9 — Verification and validation

- **Verification** — *did we solve the equations right?*
  - mesh independence (Chapter 6),
  - discretisation/scheme sensitivity,
  - iteration convergence (Chapter 8),
  - residual balancing and, where used, sensitivity checks.
- **Validation** — *did we model the right thing?*
  - compare against an accepted reference: experiment, flight/test data, or
    a validated benchmark case,
  - state the comparison uncertainty explicitly,
  - identify the discrepancy rather than tuning it away.

Keeping these two separate is the standard expectation in any review: a
mesh-independent result can still be validated against nothing.

---

## Chapter 10 — Post-processing

Performed in **Results** (CFD-Post) or Fluent's post-processing surface:

| Output | Typical use |
|--------|-------------|
| **Contours** on surfaces/planes | Scalar fields: pressure, temperature, Mach, concentration |
| **Vectors** | Flow direction and recirculation zones |
| **Pathlines / streamlines** | Lagrangian view of the flow path |
| **Surface integrals / fluxes** | Mass, heat or species through a boundary |
| **Force / moment reports** | Coefficients $C_L$, $C_D$, $C_M$ against reference values |
| **XY plots** | Profiles along a line; iteration history |
| **Section planes / isosurfaces** | Internal structure of 3D fields |
| **Exports** | `.csv`/`.dat` extracts for external plotting |

Practical conventions:

- Plot on **cutting planes and walls** rather than the whole volume.
- Set **consistent colour ranges** across comparison cases; auto-ranged
  contours make two cases look different when they are not.
- Label each figure with the case, mesh and quantity — an unlabelled contour
  is unusable later.
- Always export the numeric data behind any reported figure.

---

## Chapter 11 — Reporting and reproducibility

An unrepeatable CFD result is not evidence. The usual practice:

1. **Save the project** (`.wbpj`) after each gate.
2. **Archive case and data files** (`.cas`, `.dat`) alongside the mesh
   (`.msh`) — these are the primary artifacts, not screenshots.
3. **Journaling**: Workbench/Fluent can record scripted journals so the
   setup can be replayed; use them for anything that will be repeated.
4. **Parameters**: expose key inputs as Workbench parameter sets so
   design-point studies are reproducible runs rather than manual edits.
5. **Batch / headless execution** for sweep studies, so runs are comparable
   and do not depend on interactive state.
6. **Record, for every run:** software release/version, mesh level, models,
   materials, boundary-condition values, schemes, monitors, iteration count
   and convergence criterion.

---

## Chapter 12 — Necessary solution and results procedure

This chapter states what must **exist and be checked** before a result may
be shown to anyone. It is the production side of the presentation in
Chapter 13: nothing appears in a slide that is not in this list.

### 12.1 The minimum evidence pack

| # | Deliverable | Why it is necessary | Typical form |
|---|-------------|---------------------|--------------|
| 1 | **Problem statement** | Fixes what the answer must satisfy: objectives, geometry, flow regime, expected ranges | Half a page, with a sketch |
| 2 | **Geometry record** | Proves the domain that was solved, not the CAD that was sent | Screenshot + named-boundary list |
| 3 | **Mesh quality record** | The single most challenged item in any review | Screenshot of metrics + minimum/mean table |
| 4 | **Mesh independence result** | Without it the numbers are mesh-dependent | 3-level plot of the key observable |
| 5 | **Setup sheet** | Makes the run reproducible and the assumptions visible | Solver, models, materials, BCs, reference values, schemes |
| 6 | **Convergence evidence** | Proves the iteration actually converged | Residuals + monitor plot + mass balance |
| 7 | **Result quantities** | The actual answer, as numbers | Table with uncertainty/tolerance |
| 8 | **Field visualisations** | Shows *why* the number is what it is | Contours, vectors, pathlines |
| 9 | **Validation comparison** | Puts the number against a reference | Plot vs experiment/flight/benchmark |
| 10 | **Limitations** | Establishes where the result may not be used | Bullet list |

### 12.2 Sequence of production

```
geometry record
    -> mesh record + quality table
        -> mesh independence plot
            -> setup sheet
                -> convergence evidence
                    -> result quantities
                        -> field visualisations
                            -> validation comparison
                                -> limitations
                                    -> assemble presentation
```

Each step consumes the one before it; presenting step 7 without steps 1–6
is the common cause of a review failing on method rather than on result.

### 12.3 Checks before anything is shown

- [ ] Every number has a defined **symbol, unit, and where it came from**
- [ ] Every figure has a **caption with case, mesh and quantity**
- [ ] Comparisons use **identical colour ranges and identical axes**
- [ ] Percent differences state **their baseline** (`vs what?`)
- [ ] Convergence evidence includes **monitors**, not residuals alone
- [ ] Mesh quality is quoted as **minimum and mean**, not "fine"
- [ ] Reference values (length, area, velocity, density) are **stated**
- [ ] Any figure repeated from another run carries that run's identifier
- [ ] Units are consistent end to end (SI unless declared otherwise)
- [ ] Uncertainty or tolerance accompanies any comparison claim

### 12.4 What is *not* sufficient

| Insufficient | Why |
|--------------|-----|
| A screenshot of a coloured contour with no axis, case or unit | Uninterpretable and unrepeatable |
| "Residuals dropped to 1e-4" without a monitor plot | Residuals alone do not establish convergence |
| "Good mesh quality" with no numbers | Not a measurement |
| One mesh, presented as accurate | No independence evidence |
| Comparing two cases with auto-ranged colour scales | Manufactures an apparent difference |
| A single number with no range, tolerance or uncertainty | Cannot be evaluated |

### 12.5 Where the evidence pack lives for this repository

<!--
AXIOMS
------
A1. An evidence pack that is narrated but not emitted as files cannot be
    re-checked by anyone else, so "recorded" means a file with a path.
A2. A compliance audit is itself a claim and needs its own denominator, its own
    coverage set and its own false positives reported.

THEORIES
--------
T1. Two scripts emit the pack: one writes the measured records, another audits
    figure sufficiency. They have different provenance, so a finding from one
    is not evidence about the other.

APPLICATIONS
------------
    For StellarOrion the pack is emitted into results/99_shared/sop/:
    a mesh-quality row set and a stationarity row set for each result tree
    (00_reference, 03_opt_geometry), the grid-independence artifact, and a
    figure-sufficiency checklist.

CITATIONS
---------
    [Reference: this document, Ch. 12 - https://example.invalid/sop-ch12]
-->

For StellarOrion the pack is emitted as files, not narrated in prose.
`scripts/generate_sop_artifacts.py` writes `results/99_shared/sop/`, holding a
mesh-quality row set and a stationarity row set for each result tree
(`00_reference` and `03_opt_geometry`) plus the grid-independence artifact.
The figure-sufficiency checklist in the same folder comes from a *different*
script, `scripts/audit_figure_sufficiency.py`, and audits clause 13.3 of this
document.

The checklist's own numbers must be quoted with its scope attached. It covers
389 figures and reports 352 as compliant, 37 as having no generator, 90.49% in
total, and a verdict of NOT_MET. Two of the 37 are false positives:
`bo_convergence.png` and `bo_ccd_design.png` are recorded as having no
generator, and `scripts/render_bo_figures.py` writes both. The audit also
covers only the results tree, so literature and author-drawn figures sit
outside its denominator by design. A compliance percentage quoted without its
coverage set is not a measurement.

---

## Chapter 13 — Presenting solution and results to people

A result is not finished until a second person can understand what was run,
what came out, and how much to trust it — in the time available.

### 13.1 Decide the audience first

| Audience | They need | They will ask first |
|----------|-----------|---------------------|
| **Technical peer / reviewer** | Method, mesh, convergence, validation | "How do you know it converged?" |
| **Design / project team** | The decision-relevant number and its margin | "So what do we do?" |
| **Management / non-specialist** | One sentence conclusion + confidence | "Is it good enough?" |
| **Academic / defence panel** | Derivation of the method, verification, validation, limitations | "What are your assumptions and their limits?" |

The same result legitimately gets a different *amount* of Ch. 12 material,
never a different result.

### 13.2 The standard presentation structure

1. **Question** — one slide: what was asked, and what the answer decides.
2. **Method in one diagram** — geometry → mesh → solver → result, as a
   pipeline, so the audience has a map.
3. **Mesh and verification** — quality metrics, mesh independence. Put this
   *before* results; it is what the reviewers are actually checking.
4. **Setup in one table** — solver, models, key boundary conditions,
   reference values. Readable, not exhaustive.
5. **Convergence** — residuals plus monitors; one sentence on how
   convergence was judged.
6. **The result** — the headline quantity, as a number with tolerance, and
   the comparison it depends on.
7. **Field evidence** — two or three labelled visualisations that explain
   the number physically.
8. **Validation** — result vs reference with the discrepancy stated.
9. **Limitations and next step** — always present; never omit.
10. **Backup appendix** — the full detail (extended plots, all tables, mesh
    statistics) so the main slides stay short.

### 13.3 How a result figure must be built

Every figure presented must be **self-sufficient**: a reader who sees only
the figure and its caption must not need the speaker.

Required on every result figure:

- **Title or caption** naming the case/condition
- **Axes with units**, and readable axis ranges
- **Legends** for multiple series
- **Colour scales shown with numeric limits** on any scalar contour
- **Consistent styling** across figures of the same type
- The **physical quantity**, explicitly (not just "pressure")
- For comparisons: a **stated baseline and % difference**

Optional but valuable: annotations for the feature being argued (shock
location, separation point, peak), and a reference line for the design
limit.

### 13.4 How to present the number itself

- Give **the value with its unit and uncertainty/tolerance** — e.g.
  "$C_D = 0.42 \pm 0.01$ (mesh-independent within 1.5 %)", never "$C_D$
  is about 0.4".
- State the **comparison basis** for any percentage.
- Give **one sentence of interpretation** after every number: what it means
  physically or for the decision.
- Separate **what was measured** (the CFD quantity) from **what was
  assumed** (the model), so the audience can discount appropriately.

### 13.5 Delivering it

- **Lead with the answer**, then the method — technical audiences want the
  conclusion first and the justification immediately after.
- Keep main slides **one message each**; move detail to backup.
- **Speak the units and the caveats aloud**; do not assume they are read.
- **Anticipate the three questions** that always come: *How do you know it
  converged? How do you know the mesh is adequate? Compared to what?* Each
  must be answerable from a slide already prepared.
- Rehearse the **timing**; method material routinely overruns and pushes
  results off the end.

### 13.6 Written report counterpart

The same content appears as sections in a written report:

| Report section | Corresponds to |
|----------------|----------------|
| Objective and problem statement | Slide 1 |
| Method / numerical approach | Slides 2–4 |
| Mesh generation and independence | Slide 3 |
| Boundary conditions and solver settings | Slide 4 |
| Convergence criteria and evidence | Slide 5 |
| Results (tables + figures) | Slides 6–7 |
| Validation and discussion | Slide 8 |
| Uncertainty, limitations, conclusions | Slide 9 |
| Appendix (full data, extended plots) | Slide 10 |

Every figure in a report must satisfy §13.3; every table must satisfy the
checklist in §12.3.

### 13.7 Delivery checklist

- [ ] Conclusion stated in the first minute / first content slide
- [ ] Method shown as a pipeline before any result appears
- [ ] Mesh quality **numbers** shown, not adjectives
- [ ] Mesh independence plot present
- [ ] Convergence shown with **monitors**, not residuals alone
- [ ] Reference values and units stated alongside every coefficient
- [ ] Comparisons use consistent colour ranges and declared baselines
- [ ] Limitations slide present
- [ ] Backup slides prepared for the predictable three questions
- [ ] Every figure self-sufficient per §13.3

---

## Chapter 14 — Common failure modes

| Symptom | Likely cause | Usual remedy |
|---------|--------------|--------------|
| Solution diverges / floating-point errors | Extreme mesh quality, bad BC combination, too-aggressive Courant | Check skewness and orthogonal quality first; lower Courant; initialize closer to physical values |
| Residuals stall at a high level | Under-constrained BCs, insufficient mesh, poor cell quality, or an unphysical model | Review BCs and models; inspect worst cells; refine locally |
| Solution oscillates and will not settle | Local refinement too coarse, or time-dependent physics treated as steady | Refine the region; consider a transient formulation |
| Backflow at a pressure outlet | Outlet too close to recirculation / large separation | Extend the outlet region; set backflow values deliberately; check outlet placement |
| Forces jump when the mesh changes | Mesh quality or insufficient boundary-layer resolution | Check inflation and $y^+$; ensure comparable cell counts for comparison |
| Two identical setups give different answers | Inconsistent schemes, reference values, or initialisation | Pin every setting explicitly; re-run from a clean project |
| High skewness in one corner | Geometry artefact, bad blocking association, abrupt sizing | Defeature the geometry; re-associate blocking; add local sizing |
| Result cannot be explained in review | Missing evidence from Chapter 12 | Assemble the evidence pack before presenting, not during |

---

## Chapter 15 — Gate checklist

A run is ready to **report** only when all of the following hold.

**Geometry**
- [ ] Fluid volume extracted; domain watertight
- [ ] All physical boundaries have named selections
- [ ] Sharing/contact strategy chosen deliberately

**Mesh**
- [ ] Surface mesh captures geometry features
- [ ] Boundary-layer first cell sized to the target $y^+$ band
- [ ] Skewness within the chosen band (typically `< 0.5`, ideally `< 0.25`)
- [ ] Orthogonal quality `> 0.1` (preferably `> 0.2`)
- [ ] Growth rate within limits
- [ ] Three-level mesh independence completed and recorded

**Setup**
- [ ] Pressure- or density-based solver justified
- [ ] Every model chosen deliberately and documented
- [ ] Every boundary condition reviewed explicitly
- [ ] Reference values set deliberately

**Solution**
- [ ] Second-order (or higher) spatial discretisation
- [ ] Residual targets met
- [ ] Monitors flat and recorded
- [ ] Inlet/outlet balance closed

**Validation**
- [ ] Verification and validation reported separately
- [ ] Results compared to a reference with stated uncertainty

**Presentation** (Chapter 13)
- [ ] Evidence pack complete per Chapter 12
- [ ] Every figure self-sufficient with units, case and quantity
- [ ] Comparisons declare their baseline
- [ ] Limitations stated
- [ ] Conclusion leads

**Archive**
- [ ] Case/data/mesh files archived with version and settings

---

## References

- Ansys Help — *Creating Fluent-Based Systems* (Fluid Flow (Fluent) analysis
  system cell sequence), Ansys 2024 R2 (v242). https://ansyshelp.ansys.com/
- Ansys Help — *Orthogonal Quality* mesh metric, Ansys 2025 R1 (v251).
  https://ansyshelp.ansys.com/public/views/secured/corp/v251/en/wb_msh/msh_orthogonal_quality.html
- Ansys SpaceClaim — geometry preparation product page.
  https://ansys.synopsys.com/products/3d-design/ansys-spaceclaim
- Ansys Fluent Meshing task-based (watertight geometry) workflow overview.
  https://simutechgroup.com/ansys-fluent-meshing-new-workflow-easier-and-faster-mesh-generation
- Mesh quality metrics in practice (skewness / orthogonal quality bands).
  https://cfd.ninja/ansys-meshing/ansys-meshing-fine-mesh

---

*Status: status-quo reference for the procedure chapters; sections 5.1, 6.1 and
12.5 record measured instances for this repository, emitted as files under
`stellarorion_program_proc/results/99_shared/sop/`.*
