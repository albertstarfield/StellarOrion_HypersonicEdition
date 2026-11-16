# Week 16 progress deck — what is live, what is stale

Read this before copying any PNG out of this folder. Several files here look like deck
assets and are not. One file that *is* a deck asset **was** stale — it shipped a corrected
value wrong for a week — and §"was stale, refreshed 2026-10-14" below records what happened
and how to check it has not happened again.

---

## The 12 figures actually used by the deck

These are the only PNGs `main.tex` references. Verified by extracting every
`\PlotFrame{...}{...}{<image>}` third argument and checking each name against disk:

```
heatflux_methodology      so_bo_3d                    so_dsmc_algorithm
kriging_denoise           so_bo_convergence           so_literature_map
so_ccd_screen             so_pinn_architecture        so_pipeline
so_scalloped_vs_smooth    so_sutton_graves            so_topology_before_after
```

Their provenance — which `_proc` or thesis script drew each one, and from which data —
is in **`SOURCES.md`**. That file is the authoritative map; this one is the warning label.

---

## Do not use the 12 scratch PNGs

```
crop_a.png  crop_b.png  crop_note_before.png  crop_note_after.png
insp_p7.png
rpt_p3.png  rpt_p4.png  rpt_p5.png  rpt_p6.png
rpt_p7.png  rpt_p8.png  rpt_p9.png
```

**Every one of them has zero references in `main.tex`.** They are 1.2 MB of render
scratch produced while a figure was being debugged, not deck content.

| Group | What it actually is |
| :-- | :-- |
| `rpt_p3`…`rpt_p9` | Screenshots of PDF pages 3–9, rendered 2026-10-08 while checking figure placement. They show a **9-page** deck. The deck is 14 pages now. |
| `insp_p7.png` | One screenshot of the then-current page 7, used to inspect the Sutton-Graves annotation. Its content predates the F83 regeneration. |
| `crop_a/b.png`, `crop_note_before/after.png` | Tight crops of the annotation box on that same figure, taken before and after one repositioning attempt. The repositioning was later superseded by regenerating the figure. |

They keep coming back. They were deleted, then restored by commit
`ee268e50` ("fix: restore 11 Week 16 LaTeX PNGs deleted by the previous commit" — note the
message says 11 and the commit contains 12). The decision was made on 2026-10-14 to leave
them in place rather than fight the sync that keeps returning them. **Leaving them is not
an endorsement.** Do not treat a recent mtime as evidence of use: these files were
rewritten on 2026-10-14 15:23 by the restore, but their *content* is from 2026-10-08.

**Rule: if you need a page screenshot, re-render it from the current `main.pdf`.** Do not
lift one of these.

---

## `figures/so_sutton_graves.png` (page 11) — was stale, refreshed 2026-10-14

This was the one that mattered: unlike the scratch files it **is referenced by the deck** —
it is the figure on page 11, *"4. REDEFINING YESTERDAY'S WRONG HEAT FLUX DEFINITION"*.

**What was wrong.** The deck copy was byte-identical to the pre-F83 artefact
(`029560f01d545f87f4002e1f6800988d`, 248565 B), annotating **16.14 W/cm²**.
`FAILURES_AND_FIXES.md` entry **F83** established that value came from the superseded Mars
correlation constant `C_SG = 1.83e-4`; the corrected Earth-air value `C_SG = 1.7415e-4`
(NASA TR R-376 Table 1, now at `stellarorion_types.ads:61`) gives **15.3575 W/cm²**, a
**5.1 % overstatement**. F83 was filed as fixed on 2026-10-07 by regenerating the figure.

**Why it came back.** Git history for the deck copy stopped at `a8404fb4` (2026-10-06), one
day before F83. The 2026-10-07 regeneration was never committed for this file, so the
working tree reverted to the older blob and page 11 shipped the exact number F83 exists to
correct. Note the slide *caption* was never affected: "reported peak overstated by 31.90 %
(F21)" describes the normalisation-constant condition mismatch at `R_N = 0.55 m`, a
different quantity. The stale part was the annotation **inside the artwork**.

**Fix applied 2026-10-14.** Copied the thesis source over the deck copy and rebuilt:

```
cd "Lost+Found/ProgressReport/Week 16 LaTeX"
cp ../CurrentThesisFinalReport/figures/sutton_graves_parametric.png figures/so_sutton_graves.png
for i in 1 2 3; do pdflatex -interaction=nonstopmode -file-line-error main.tex; done
```

| File | md5 | Bytes | Annotation |
| :-- | :-- | --: | :-- |
| `figures/so_sutton_graves.png` (deck, **now**) | `3912e7759176e40868fdc0c0caede41f` | 232192 | **15.36 W/cm²** |
| `../CurrentThesisFinalReport/figures/sutton_graves_parametric.png` | `3912e7759176e40868fdc0c0caede41f` | 232192 | **15.36 W/cm²** |
| *(previous deck copy)* | `029560f01d545f87f4002e1f6800988d` | 248565 | ~~16.14 W/cm²~~ |

**Verified, not assumed.** 3 pdflatex passes, `main.log` scored against all 11 patterns
(bare `!`, `^\./main\.tex:[0-9]+:`, `Missing $ inserted`, `Extra \}`, `Undefined control
sequence`, `Overfull`, `Underfull`, `LaTeX Warning`, `Package Warning`, `Rerun to get`,
`Fatal`) — all 0, verdict **CLEAN**; 14 pages; 0 `MISSING PLOT`. Page 11 rendered to PNG
and read back by eye: annotation reads 15.36, counter `11 / 14`, caption 2 lines, no
clipping or overlap.

**No layout change, measured rather than assumed.** Both figures are the *same canvas*,
1486×1288, identical aspect 1.1537 — so the earlier guess that this was a "restyle with a
larger canvas" was wrong. Pixel-diffing old vs. new page 11 at scale 3.0: identical
dimensions (1361×766), and rows bands outside the plot area are byte-for-byte equal in ink
count (title, rule, legend, caption, page counter all unchanged). Only **1.002 %** of page
pixels differ, all inside the plot box — as expected, since rescaling `C_SG` shifts the
curves, not the frame.

**If it regresses again:** that same `cp` + 3 passes is the remedy. Worth re-checking after
any autosave touching `figures/`, since the loss mechanism was an uncommitted regeneration,
not a deliberate revert.

---

## Other files in here that are not on any slide

Present but unreferenced, so they inflate the folder without being used. They are current,
unlike the scratch set — kept because they were copied for possible future use:

```
figures/so_bo_ccd_design.png       figures/so_gate_comparison.png
figures/placeholder_bo.png         figures/placeholder_kriging.png
figures/placeholder_heatflux.png   figures/placeholder_plots.png
figures/placeholder_problem.png    figures/placeholder_topology.png
figures/placeholder_validation.png
figures/gajah_putih.eps            figures/gajah_putih-eps-converted-to.pdf
```

The `gajah_*` pair **is** used — by `\ITBEmblem` on the title frame — so do not remove
those two. The `placeholder_*` files are the original skeleton placeholders, superseded by
the real figures above.

`so_gate_comparison.png` was regenerated by another thread on 2026-10-13 (130590 → 124561
bytes) without being wired to a slide. If a slide is ever added for it, re-check the source
rather than assuming it matches `_proc`.

---

## Rebuilding

Three passes, then judge from the log, never the exit status — pdflatex exits 1 with a clean
log routinely in this document:

```
for i in 1 2 3; do pdflatex -interaction=nonstopmode -file-line-error main.tex; done
```

The verdict must include the pattern `^\./main\.tex:[0-9]+:`. With `-file-line-error`, real
errors print as `./main.tex:NN: Missing $ inserted.` and do **not** start with `!`, so a
`^!`-only check misses them.

Expected: 14 pages, zero of any of `^!`, `^\./main\.tex:[0-9]+:`, `Missing $ inserted`,
`Extra \}`, `Undefined control sequence`, `Overfull`, `Underfull`, `LaTeX Warning`,
`Package Warning`, `Rerun to get`, `Fatal`.

`main.pdf` is tracked by **Git LFS**. Committing the PDF commits a 132-byte pointer, not the
file; verify the LFS oid against your on-disk `sha256` if you need to be sure the rebuild
landed.

---

## Deck shape

16 pages: title · OUTLINE · **PREVIOUS PROBLEM** (3 frames) · **CURRENT IMPLEMENTATION** (10 frames) · **CONTEXT** (moved to end).

PREVIOUS PROBLEM: `1. HEAT FLUX WAS NEVER DEFINED`, `2. COST FUNCTION INCOMPLETE (ATTEMPT-1)`,
`3. SAMPLING ORDERED WRONG (CCD FIRST)`.

CURRENT IMPLEMENTATION: `1. BAYESIAN OPTIMIZATION`, `1b. CCD SCREEN`, `2. KRIGING DENOISING`,
`3. VALIDATION RUN`, `3b. PINN`, `3c. HEAT FLUX: CONVECTION, CONDUCTION, RERADIATION`,
`4. REDEFINING YESTERDAY'S WRONG HEAT FLUX DEFINITION`, `4b. SCALLOPED VS SMOOTH`,
`5. OPTIMIZATION RESULT: TOPOLOGY BEFORE/AFTER`, `6. BAYESIAN PLOT OPTIMIZATION`.

CONTEXT is intentionally seen as the LAST frame (positioning map is read after the evidence).

Constraints enforced by the preamble, not by convention: `\MaxTextLines{2}` raises
`\PackageError{Week16Deck}` if a caption exceeds two lines, and every number in a caption
must cite the file it came from. `\setbeamertemplate{background}{}` must stay empty —
painting the gajah on every frame collided with frametitles, a bug found only by reading a
rendered page back.

---

## Known open defect — page 4 attributes Bayesian numbers to MoP

**Status: RESOLVED 2026-10-14 (frame removed).** The MoP frame no longer ships in the
build; nothing in the deck attributes Bayesian numbers to MoP. The section `PREVIOUS PROBLEM`
now carries three framing slides (heat flux definition, cost function, sampling order), and
MoP is mentioned nowhere in the deck. The rejected solution (delete the frame and leave an
empty section) was superseded by user direction "that replaces the previous problem" — the
frame was deleted and the three framing slides took its place.

The record below is kept as history of the defect; the open-to-fix decision (how to handle
the empty section) no longer applies.

Page 4 *was* `WHAT MoP WAS SAMPLING: THE DSMC ALGORITHM`, caption reading:

> Two MoP runs at the fixed seed 42 returned different optima ($J$ 1.602195 vs 1.608508):
> the GP hyper-parameter fit varies, not the seed (F6).

That attribution is wrong. MoP is **Method of Projected Gradients**, an Ada/SPARK optimizer
reached through FFI, and `hiad_optimizer.py:8` describes it as "available via Ada FFI
**for comparison**". The current optimizer is Bayesian Optimization — the GP surrogate +
Matérn 5/2 + Expected Improvement path — which is what pages 5 and 14 show.

Three findings, all measured:

| # | Claim | Evidence |
| :-- | :-- | :-- |
| 1 | MoP cannot produce the quoted spread | `run_mop_optimize(x0, lr, tol, lambda_1, lambda_2, max_iter)` at `ada_pinn_wrapper.py:817` **has no seed parameter**, and no GP. It is projected gradient descent, deterministic given `x0` (`stellarorion_ffi.ads` → `Run_MoP_C`; Boyd & Vandenberghe 2004 §2.3). It has no Matérn length scale and never calls `lbfgs`. |
| 2 | The quoted numbers are Bayesian | The `seed=42` lives at `hiad_optimizer.py:1472`, inside `run_bayesian_optimize(hiad_cost_function, n_initial=20, n_iter=50, xi=0.01, seed=42)`. F6 itself attributes the spread to "the GP hyper-parameter fit (scikit-learn's `lbfgs` on the Matérn length scale)", at `FAILURES_AND_FIXES.md:212`. |
| 3 | No MoP failure justifies abandoning it | The `PREVIOUS PROBLEM` section comment asserts MoP was "too chaotic to use as a basis for further work". `FAILURES_AND_FIXES.md` contains exactly **one** MoP mention — **F98**, an FFI spec defect (missing `use Interfaces.C`, vacuous postcondition on `Run_MoP_C`), fixed 2026-10-13. **No chaos failure is recorded**, and F6 is itself labelled "not a failure; recorded for reproducibility". |

So the deck uses Bayesian Optimization's own benign run-to-run variation as the stated
reason for having replaced MoP. That is circular, and a judge who opens F6 will see it.

**The figure is not at fault.** `so_dsmc_algorithm.png` is the DSMC flowchart, and it
genuinely is what the cost function scores whichever optimizer drives it. Only the
attribution and the narrative are wrong.

**The constraint on any fix:** page 4 is the *only* frame under `PREVIOUS PROBLEM`.
Deleting it empties the section, and an empty `\section` still prints in the
auto-generated outline. So the frame cannot simply be deleted — either the section goes
with it, or something else has to move under it. That choice is what is on hold.

**Resolution (2026-10-14).** The constraint held, and was satisfied by repopulating rather
than deleting: three PREVIOUS PROBLEM frames (heat flux definition, cost function /
attempt-1, sampling order) were added where page 4 used to be, and `CONTEXT: WHERE THIS
WORK SITS` was moved to the last page, so `PREVIOUS PROBLEM` is no longer empty and the
MoP frame is gone. Build went back to 14 -> 16 pages, log still CLEAN on all 11 patterns,
0 `MISSING PLOT`. The figure (`so_dsmc_algorithm.png`) is still on disk and unreferenced,
so it now counts with the placeholder set under "Other files in here that are not on any
slide" above. Lead-in to this whole operation was the user's wording, not a spec change.
