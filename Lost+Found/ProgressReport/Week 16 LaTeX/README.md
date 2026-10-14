# Week 16 progress deck — what is live, what is stale

Read this before copying any PNG out of this folder. Several files here look like deck
assets and are not; one file that *is* a deck asset is stale and currently disagrees with
the thesis it was copied from.

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

## ⚠️ `figures/so_sutton_graves.png` is stale and on a shipped slide

This is the one that matters, because unlike the scratch files it is **referenced by the
deck** — it is the figure on page 11, *"4. REDEFINING YESTERDAY'S WRONG HEAT FLUX DEFINITION"*.

Measured, 2026-10-14:

| File | md5 | Bytes | Annotation reads |
| :-- | :-- | --: | :-- |
| `figures/so_sutton_graves.png` (deck, **stale**) | `029560f01d545f87f4002e1f6800988d` | 248565 | **16.14 W/cm²** |
| `../CurrentThesisFinalReport/figures/sutton_graves_parametric.png` (newest) | `3912e7759176e40868fdc0c0caede41f` | 232192 | **15.36 W/cm²** |

The deck copy is byte-identical to the **pre-F83** artefact. `FAILURES_AND_FIXES.md` entry
**F83** established that 16.14 W/cm² was computed with the superseded Mars correlation
constant `C_SG = 1.83e-4`; the corrected Earth-air value `C_SG = 1.7415e-4` (NASA TR R-376
Table 1, now at `stellarorion_types.ads:61`) gives **15.3575 W/cm²**, a **5.1 %
overstatement**. F83 was filed as fixed on 2026-10-07 by regenerating the figure.

**The fix did not survive into the deck.** Git history for the deck copy stops at
`a8404fb4` (2026-10-06), which predates F83. The 2026-10-07 regeneration was never
committed for this file, and the working tree reverted to the older blob.

Net effect: page 11 currently ships the number that entry F83 exists to correct. The slide
caption — "reported peak overstated by 31.90 % (F21)" — is about a *different* quantity
(the normalisation-constant condition mismatch at `R_N = 0.55 m`) and is unaffected; the
**annotation inside the artwork** is the stale part.

**Remedy:** copy the newer thesis figure over the deck copy and rebuild.

```
cd "Lost+Found/ProgressReport/Week 16 LaTeX"
cp ../CurrentThesisFinalReport/figures/sutton_graves_parametric.png figures/so_sutton_graves.png
for i in 1 2 3; do pdflatex -interaction=nonstopmode -file-line-error main.tex; done
```

Then check page 11 reads 15.36 W/cm². Note the newer figure is a restyle as well as a
number fix (viridis ramp, larger canvas), so the page will *look* different, not just
*differ* by one number.

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

14 pages: title · OUTLINE · **CONTEXT** · **PREVIOUS PROBLEM** · then twelve frames under
**CURRENT IMPLEMENTATION** — `1. BAYESIAN OPTIMIZATION`, `1b. CCD SCREEN`, `2. KRIGING
DENOISING`, `3. VALIDATION RUN`, `3b. PINN`, `3c. HEAT FLUX METHODOLOGY`, `4. REDEFINING…`,
`4b. SCALLOPED VS SMOOTH`, `5. TOPOLOGY BEFORE/AFTER`, `6. BAYESIAN PLOT`.

Constraints enforced by the preamble, not by convention: `\MaxTextLines{2}` raises
`\PackageError{Week16Deck}` if a caption exceeds two lines, and every number in a caption
must cite the file it came from. `\setbeamertemplate{background}{}` must stay empty —
painting the gajah on every frame collided with frametitles, a bug found only by reading a
rendered page back.
