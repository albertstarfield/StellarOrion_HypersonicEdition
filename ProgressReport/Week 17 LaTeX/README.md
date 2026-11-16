# Week 17 progress deck — what is live, what is stale

Read this before copying any PNG out of this folder. Several files here look like deck
assets and are not. One file that *is* a deck asset **was** stale — it shipped a corrected
value wrong for a week — and §"was stale, refreshed 2026-10-14" below records what happened
and how to check it has not happened again.

---

## The 19 figures actually used by the deck

These are the only PNGs `main.tex` references. Verified by extracting every
`\PlotFrame{...}{...}{<image>}` third argument plus every `\includegraphics`
target and checking each name against disk:

```
heatflux_methodology      hiad_geometry_grid        so_bo_3d
so_bo_convergence         so_ccd_screen             so_gate_comparison
so_grid_mesh_map          so_knudsen_map            so_literature_map
so_mach_map               so_mesh_statistics        so_performance_comparison
so_ply_heatflux_explainer so_ply_stack_temperature  so_sutton_graves
so_thermal_map            so_topology_4views        so_tps_backface
so_tps_ply_profile_peak
```

`so_ply_stack_temperature` is intentionally used **twice**: page 22
(VALIDATION, "TPS RESULT: PLY STACK TEMPERATURE") and page 31 (BACKUP,
"REDEMPTION 1c: PLY STACK AND TEMPERATURE"). Same artwork, two framings.

**The previous list of 12 in this file was wrong** — 6 of its 12 entries
(`kriging_denoise`, `so_dsmc_algorithm`, `so_pinn_architecture`, `so_pipeline`,
`so_scalloped_vs_smooth`, `so_topology_before_after`) were not referenced at all,
and it omitted the other 13 that are. Corrected 2026-10-19 by re-extracting the
references from `main.tex` rather than editing the old list.

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
| `rpt_p3`…`rpt_p9` | Screenshots of PDF pages 3–9, rendered 2026-10-08 while checking figure placement. They show a **9-page** deck. The deck is 39 pages now. |
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
it is the figure on page 30, *"REDEMPTION 1b: CONVECTION TERM (Sutton--Graves)"*, in
`BACKUP: DERIVATIONS`. (The frame it originally shipped on, *"4. REDEFINING YESTERDAY'S
WRONG HEAT FLUX DEFINITION"*, no longer exists; the deck was restructured after F83.)

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
cd "Lost+Found/ProgressReport/Week 17 LaTeX"
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
`Fatal`) — all 0, verdict **CLEAN**; 39 pages; 0 `MISSING PLOT`. Page 30 rendered to PNG
and read back by eye: annotation reads 15.36, caption 2 lines, no clipping or overlap.
(The `11 / 14` counter cited here at the time is obsolete — the deck is 39 pages.)

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

## `figures/heatflux_methodology.png` (page 8) — corrected 2026-10-19, R_total was stale

**What was wrong.** The deck shipped a three-way contradiction on the surface energy
balance. The artwork in `heatflux_methodology.png` (frame REDEMPTION 1f, page 8) read
`266509.3 = 261626.5 + 4882.8 W/m2, T_s 1550.23 K`, while the caption directly beneath it
read `266509.3 = 261530.8 + 4978.5 W/m2 ... (F84; outer-layer ε=0.75)`. Same left-hand
side, different split, ΔT_s = 24.5 K, both attributed to F84. The BACKUP frames REDEMPTION 1,
1d and 1d2 repeated the ε = 0.75 triple.

**Root cause, found in `_proc`.** Both triples used the **wrong thermal resistance**.
`FAILURES_AND_FIXES.md` F84 and the deck both used `R_tot = 0.25605 m²K/W`. But
`stellarorion_program_proc/src/python/ada_pinn_wrapper.py:1481` states the layup's
`R_total = 0.305583 m²·K/W`, and `stellarorion_types.ads:760` records why:

> `net stack R        0.257250 -> 0.305583 m^2*K/W, i.e. UP 18.8 %`

`0.25605` belongs to the **superseded 6.35 mm flown IRVE-3 stack** (Nextel BF-20 + 2.5 mm
Pyrogel). The deck's own REDEMPTION 1e table shows the **current 7.131 mm** Nicalon SiC +
3.047 mm Pyrogel + Kapton schedule, whose `Σ(t/k)` is exactly `0.305583` — the table was
right and the balance plugged in the old number. Reproduced by hand from the tuple at
`ada_pinn_wrapper.py:1495-1497`:

```
R = 2(0.000506/1.5) + 2(0.003047/0.02) + 0.000025/0.12
  = 0.000337 + 0.000337 + 0.152350 + 0.152350 + 0.000208 = 0.305583
```

**Emissivity.** `IRVE3_FTPS_EMISSIVITY = 0.80` (`ada_pinn_wrapper.py:1526`,
`stellarorion_types.ads:714`) is the stack-level hot-face value the Ada solver uses — this
part of F84 was correct and is unchanged. The outer Nicalon SiC ply's own `ε = 0.75`
(Rapisarda Table B.17) is a **material property listed in the ply table**, not the balance
input; the deck had been treating it as the latter.

**Corrected balance** (`q_conv = εσT_s⁴ + (T_s − T_back)/R_tot`, ε = 0.80,
R_tot = 0.305583, T_back = 300 K, solved by bisection to machine precision):

```
266509.3 = 262415.9 + 4093.4 W/m2      residual 0.0000 %      T_s = 1550.86 K
```

**Files changed.** `make_heatflux_methodology.py` (the bottom "Surface energy balance (F84)"
box — regenerates the artwork) and `main.tex` (frames 1f, 1e, 1, 1d, 1d2 and the LIMITATIONS
slide, which previously listed the 0.25605/0.305583 mismatch as an **open** defect and now
records it as reconciled). The figure was regenerated with the project `.venv`
(`matplotlib`) and read back by eye to confirm the box prints the new triple.

**If it regresses:** the numbers are not free-floating. Re-derive them from
`ada_pinn_wrapper.py:IRVE3_FTPS_PLY_THICKNESS_M` / `IRVE3_FTPS_PLY_THERMAL_K` /
`IRVE3_FTPS_EMISSIVITY` rather than copying them from a previous slide.

---

## Other files in here that are not on any slide

Present but unreferenced, so they inflate the folder without being used. They are current,
unlike the scratch set — kept because they were copied for possible future use:

```
figures/so_bo_ccd_design.png
figures/kriging_denoise.png        figures/so_dsmc_algorithm.png
figures/so_pinn_architecture.png   figures/so_pipeline.png
figures/so_scalloped_vs_smooth.png figures/so_topology_before_after.png
figures/placeholder_bo.png         figures/placeholder_kriging.png
figures/placeholder_heatflux.png   figures/placeholder_plots.png
figures/placeholder_problem.png    figures/placeholder_topology.png
figures/placeholder_validation.png
figures/gajah_putih.eps            figures/gajah_putih-eps-converted-to.pdf
```

The first six after `so_bo_ccd_design` (`kriging_denoise`, `so_dsmc_algorithm`,
`so_pinn_architecture`, `so_pipeline`, `so_scalloped_vs_smooth`,
`so_topology_before_after`) are the figures the *old, wrong* "12 figures" list in this file
claimed were in use. They are not referenced by `main.tex`. They are current artwork kept
for possible future use, not scratch — do not delete them, and do not cite them as shipped.

The `gajah_*` pair **is** used — by `\ITBEmblem` on the title frame — so do not remove
those two. The `placeholder_*` files are the original skeleton placeholders, superseded by
the real figures above.

**Correction 2026-10-19:** `so_gate_comparison.png` used to be listed here as unreferenced.
It **is** wired — page 24, `PLOT VALIDATION RESULT: HYBRID DSMC GATE`. It was regenerated by
another thread on 2026-10-13 (130590 → 124561 bytes) and then wired to a slide afterwards;
the "without being wired to a slide" note had gone stale. If it is ever regenerated again,
re-check the source rather than assuming it matches `_proc`.

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

Expected: 39 pages, zero of any of `^!`, `^\./main\.tex:[0-9]+:`, `Missing $ inserted`,
`Extra \}`, `Undefined control sequence`, `Overfull`, `Underfull`, `LaTeX Warning`,
`Package Warning`, `Rerun to get`, `Fatal`, `MISSING PLOT`, `PackageError`.

`main.pdf` is tracked by **Git LFS**. Committing the PDF commits a 132-byte pointer, not the
file; verify the LFS oid against your on-disk `sha256` if you need to be sure the rebuild
landed.

---

## Deck shape

39 pages. Measured from `main.tex` (19 `\begin{frame}` + 20 `\PlotFrame{`) and
cross-checked against the section start pages in `main.toc`:

| # | Section | Starts | Frames |
| :-- | :-- | --: | :-- |
| 1 | PROBLEM AND ANSWER | 2 | OUTLINE · PREVIOUS PROBLEM: SUMMARY OF THE THREE ITEMS |
| 2 | ANSWER: OPTIMIZATION RESULT | 4 | STATUS UPDATE · OPTIMIZATION RESULT: BASELINE VS. OPTIMUM · RESULT TABLE |
| 3 | METHOD AND SETUP | 7 | REDEMPTION 1d3 · 1f · 1e · 3a2 |
| 4 | VERIFICATION | 11 | DSMC MESH STATISTICS · GRID MESH MAP · REDEMPTION 3b (CCD) · 3c · 70-EVAL BAYESIAN CAMPAIGN · GEOMETRY GRID |
| 5 | RESULTS: FIELD EVIDENCE | 17 | THERMAL MAP · MACH MAP · KNUDSEN MAP · SKIN PERFORMANCE |
| 6 | VALIDATION | 21 | TPS BACKFACE CHECK · PLY STACK TEMPERATURE · PEAK PLY PROFILE · HYBRID DSMC GATE |
| 7 | BACKUP: DERIVATIONS | 26 | LIMITATIONS AND NEXT STEP is p25; then REDEMPTION 1, 1d, 1d2, 1a, 1b, 1c, 2, 2a, 2b, 3, 3a, 3a1, 3a3 |
| 8 | CONTEXT | 39 | WHERE THIS WORK SITS |

CONTEXT is intentionally the LAST frame (the positioning map is read after the evidence).
REDEMPTION labels are **not** monotonic with presentation order: 1d3/1f/1e/3a2 appear in
§3–4 while 1, 1d, 1d2, 1a–1c, 2/2a/2b, 3/3a/3a1/3a3 appear only in §7 BACKUP. The
forward references are deliberate — the main body shows the answer, BACKUP shows the work.

Constraints enforced by the preamble, not by convention: `\MaxTextLines{2}` raises
`\PackageError{Week17Deck}` if a caption exceeds two lines, and every number in a caption
must cite the file it came from. Note `\MaxTextLines` only checks the **declared** value —
it never measures the rendered line count, so it is self-attestation, not enforcement.
`\setbeamertemplate{background}{}` must stay empty — painting the gajah on every frame
collided with frametitles, a bug found only by reading a rendered page back.

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
