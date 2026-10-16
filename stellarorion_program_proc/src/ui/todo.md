# Sidecar TODO — CFD SOP ↔ GUI compliance plan

> Scope: make the sidecar GUI able to **supply every requirement of
> `Standard Operating Procedure of CFD.md` (688 lines) — at minimum, all the
> features that SOP checks.** Reference audits: `SOP_COMPLIANCE_AUDIT.md`
> (repo outputs), this plan (GUI coverage).
> Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` cut
> Approved by user: YES (user: "Alright do it and i'll go out for a while do it automatically")

---

## A. Gap matrix — SOP requirement vs GUI today

Legend: ✅ covered · 🟡 partial · ❌ gap

| # | SOP requirement | Chapter | GUI today | Status |
|---|---|---|---|---|
| 1 | Ordered workflow (Geometry→Mesh→Setup→Solution→Results) | 1 | Wizard pages 1–8 map to the flow | ✅ |
| 2 | Geometry record + 3D view + snapshot save | 2, 12#2 | Page 4 Three.js STL viewer + `/api/geometry/*` | ✅ |
| 3 | Domain/mesh preview, grid-factor control | 3–4 | `#env-grid-factor`, `#domain-live-preview` but `/api/preview/domain` endpoint MISSING | 🟡 |
| 4 | Mesh quality gates (skew/ortho/aspect/growth, min+mean) | 5, 12#3, 15 | Nothing in GUI; only `mesh_statistics_*.png` repo-side, no numeric table | ❌ |
| 5 | Mesh independence (3-level) | 6, 12#4, 15 | Controls exist (`#grid-test-steps/factors`); endpoint missing; NO generator exists repo-side (audit: 0 artefacts) | ❌ |
| 6 | Solver / models / materials / BC / reference values | 7 | Wizard page 5 (~90 inputs) + config panel | ✅ |
| 7 | Convergence: residuals + monitors + balance | 8, 12#6 | Metrics panel = monitors ✅; residual plot & mass-balance display absent (`convergence_audit.csv` + PNGs exist repo-side, unread by GUI) | 🟡 |
| 8 | Verification vs validation separate, uncertainty stated | 9, 12#7, 12.3 | IRVE-3 validation panel + `#target-*-tol` inputs exist but results never render as `value ± tol` | 🟡 |
| 9 | Post-processing outputs (contours, vectors, XY, reports) | 10 | Page 8 static plot gallery (329 PNGs) | ✅ |
| 10 | Numeric export (.csv) behind any figure | 10 | No download/export anywhere in GUI | ❌ |
| 11 | Setup sheet (solver, models, BCs, schemes, iterations, criterion) | 11#6, 12#5 | Page 6 summary partial; nothing printable/exportable; no generator repo-side | ❌ |
| 12 | Run record per run (version, mesh level, models, …) | 11#6 | Run History (runs.csv, DB empty) + `/api/config` round-trip | 🟡 |
| 13 | Evidence pack (10 items, checked) | 12 | No evidence-pack view | ❌ |
| 14 | Figure self-sufficiency / baselines / units | 12.3, 13.3 | Generator-side concern, not GUI | 🟡 |
| 15 | Limitations list | 12#10, 15 | Absent from GUI | ❌ |
| 16 | Gate checklist (geometry/mesh/setup/solution/validation/presentation/archive) | 15 | Absent from GUI | ❌ |
| 17 | Streamlines / isosurfaces | 10 | 0 artefacts repo-side — audit records as accepted DSMC limitation | ❌\* |

\* not to be built — to be **stated in the GUI Limitations block** instead.

**Blocking prerequisite:** wizard calls ~25 endpoints that do not exist in
`sidecar_ui.py` (grid-independence, preview/domain, content/manual,
history detail/resume/delete, model-paths, readiness, atmosphere, …).
Until wired, those features error instead of supplying anything.

---

## Phase 1 — Wire the backend (`src/ui/sidecar_ui.py`)

- [x] 1.1 `GET /api/content/manual` → serve `docs/*.md` (AXIOMS, THEORIES, APPLICATIONS…)
- [x] 1.2 `GET /api/content/references` → serve `docs/CITATIONS.md`
- [x] 1.3 `GET /api/history/{id}` — run detail (empty-DB safe JSON)
- [x] 1.4 `POST /api/history/{id}/resume` — resume record (empty-DB safe JSON)
- [x] 1.5 `DELETE /api/history/{id}` — delete record (path-guarded)
- [x] 1.6 `GET /api/model-paths` → locate `uiassets/assets/model.stl`
- [x] 1.7 `GET /api/local-user` → current user (getpass, no shell)
- [x] 1.8 `POST /api/draft/autosave` → persist wizard draft config to disk
- [x] 1.9 `POST /api/preview/domain` → real cell-count math from grid factor + extents
- [x] 1.10 `POST /api/atmosphere-data` → `pymsis` (already in `venv/python`)
- [x] 1.11 **`GET /api/convergence`** → parse `results/*/validation_pipeline_output/convergence_audit.csv` → residuals + monitors JSON
- [x] 1.12 **`GET /api/mesh-quality`** → best-available min/mean (parse `grid*.out`/logs; honest `"numeric_table": null` when not derivable)
- [x] 1.13 **`GET /api/setup-sheet`** → assemble SOP Ch.11#6 record: sidecar version, config, models, BCs, mesh level, schemes, iteration count, convergence criterion
- [x] 1.14 **`POST /api/validation/grid-independence`** → aggregate multi-level data if present, else `status:"NOT_MET"` with exact reason (NEVER fabricate results)
- [x] 1.15 Honest `{"status":"not_implemented","detail":…}` JSON for genuinely unwired routes (optimization, ssh/remote solver, readiness*, test, build-image, demo/manim|open, cad-preview) so the UI degrades cleanly and self-test classifies WARN not FAIL
- [x] 1.16 Server self-tests still pass: run `venv/python/bin/python3 sidecar_ui.py` bottom-of-file pytest-style suite

**Phase 1 checkpoint:** every wizard fetch resolves to a defined JSON shape
(200 real data or structured not_implemented); zero raw HTML 404s on `/api/*`.

**Phase 1 RESULT (2026-10-16): DONE** — 24/24 file self-tests pass (4 new:
`test_sop_get_endpoints`, `test_sop_post_endpoints`, `test_history_lifecycle`,
`test_content_image_guard`). Live-curl verified: 11 GET + 5 POST routes all 200;
`/api/history/{unknown}` and DELETE answer **404 JSON**. Deviations from plan:
readiness (`/api/readiness/sparta|openfoam`, *above) upgraded from stub to a
REAL executable probe (PATH + `bin/` globs; honest error + `sparta_missing`
flag when absent); `/api/history` GET now returns a JSON **array** (main.ts
calls `history.forEach`) instead of `{"runs": …}`; `GET /api/content/image
?name=` added to serve results/-side mesh PNGs (outside FRONTEND_DIR) for
Phase 2. pymsis answers nrho=1.70e22 m⁻³, T=264 K at 52 km; fallback path
labeled `analytic-standard-atmosphere`.

## Phase 2 — SOP feature panels (`src/ui/uiassets/`)

- [x] 2.1 **Gates & Evidence view**: Ch.15 gate checklist (7 groups) + Ch.12 evidence-pack 10-item table, each row live-statused (✅ / NOT MET + why) via Phase-1 endpoints
- [x] 2.2 **Mesh Quality panel**: min/mean table (skewness, ortho quality, aspect, growth) with SOP acceptance bands as thresholds (`<0.25/<0.5`, `>0.1/>0.2`, growth `≤1.2–1.3`); embed `mesh_statistics_*.png`; explicit NOT MET until numeric data exists
- [x] 2.3 **Mesh Independence panel**: reuse `#grid-test-steps/#grid-test-factors` controls + 3-level result plot + Δ-between-levels vs tolerance + honest gate state
- [x] 2.4 **Convergence panel**: residual curve + monitor plateau + mass-balance row from `/api/convergence`
- [x] 2.5 **Setup Sheet view** (Final Review page): render `/api/setup-sheet`, Print (`window.print`) + Download as Markdown/JSON
- [x] 2.6 **Uncertainty on results**: metrics + IRVE-3 table render `value ± tol` from existing `#target-*-tol`; comparisons state baseline + % difference (SOP 13.4)
- [x] 2.7 **Export buttons**: CSV/JSON download of metrics, config, setup sheet (client-side Blob)
- [x] 2.8 **Limitations block** (static): includes accepted limitation note for streamlines/isosurfaces (audit §3)
- [x] 2.9 New panel elements/routines added to `tests/manifest.generated.mjs` + `tests/ROUTINES` in `selftest.mjs` (regenerate manifest: `node gen_manifest.mjs`)

**Phase 2 RESULT (2026-10-16): DONE** — page 6 now carries Setup Sheet
(print/3 downloads), Gates & Evidence (Ch.15 + Ch.12 live tables), Mesh
Quality, Mesh Independence and the static Limitations block; page 8 carries
the Convergence Audit table, target ± tolerance Uncertainty table (with
IRVE-3 baselines + % diff, W/m²→W/cm² unit guard) and metrics CSV/JSON
exports. Panels load from `nextStep()` hooks + a `#btn-refresh-sop` button.
Manifest regenerated: **205 elements / 26 groups**; ROUTINES now covers all
**77 main.ts functions + window.onload (78 entries)**.
**Gallery fix (deviation):** `index.html` referenced 11 plot files that do
not exist anywhere in the repo → 4 remapped to real equivalents
(`convergence_residuals_master_smooth`, `grid_mesh_map_smooth` ×2 incl.
domain preview, `validation_anim_smooth_M0_A0.mp4`,
`shock_stagnation_profile_smooth`) and 7 replaced with honest
**PLOT NOT GENERATED** placeholders (2 convergence + 5 species maps) so no
404s remain. `copyToClipboard` fixed for non-standard `window.event`
(Firefox/programmatic invocation) — a real bug the sweep caught.

**Phase 2 checkpoint:** every SOP row in matrix §A shows ✅ (or 🟡 with the
reason recorded in Limitations) when the sidecar runs.

## Phase 3 — Self-test

- [x] 3.1 Extend `tests/selftest.mjs` KNOWN_MISSING list: remove now-implemented endpoints, add `not_implemented` routes as expected-WARN
- [x] 3.2 Run `node tests/selftest.mjs` → **zero FAIL** (missing repo data = WARN/NOT MET, never FAIL)
- [x] 3.3 Fix every FAIL found (report → user approval → fix → re-run)

**Phase 3 RESULT (2026-10-16): DONE** — `node selftest.mjs` → **exit 0,
283 PASS / 0 FAIL / 4 WARN** (all 4 WARNs are pre-existing null-guarded dead
bindings: `manual-title-text`, `.toc-item`, `.history-item`,
`.manual-search-box`). KNOWN_MISSING emptied (all 27 wizard routes wired;
re-add only with a wiring-backlog note). Run-1 failures fixed to reach zero:
(a) fixture paths (`VENV_PY`/`SERVER` resolved one directory off),
(b) `/favicon.ico` 404 at boot → `<link rel="icon" href="data:,">`,
(c) `copyToClipboard` crash on non-standard `window.event`,
(d) `refreshFinalPlots`/`onDomainPreviewReady` src rewrite aborting in-flight
fetches (`net::ERR_ABORTED`) → `el.complete` guard,
(e) sidecar static/JSON writes hardened against client disconnects
(BrokenPipe/ConnectionReset no longer cascade into 500-on-dead-socket).
All phases ran: static-audit, boot (zero faults), element sweep (205),
nav phase (lock/readiness/boundary guards OK), routine sweep (78).

**Phase 3 checkpoint:** self-test matrix exit code 0, report JSON archived.

## Phase 5 — SOP artefacts exist; wire them (gap re-audit)
Status: `[x]` done (verified and committed)

Verified (this session) that `results/99_shared/sop/`
carries machine-readable artefacts we previously assumed absent — so
those parts are NOT gaps. Convergence and mesh-quality now read them:

- [x] 5.1 `/api/convergence` ← pars es residuals (`step`, `n_particles`, `delta_particles`, `retention_frac`, `stationarity_indicator`, `residual_kind`) and mass balance.
  Verified: `/api/convergence` → 23 residual samples, `retention_final ≈ 0.8553`, `particles_lost_total = 200829`, kind `dsmc_stationarity_not_continuum`; PINN quality `metrics` (7).
- [x] 5.2 `/api/mesh-quality` ← parses numeric quality CSV (17 rows): status **MET** — skewness min 0 / mean 0, ortho min 1 / mean 1, growth 1.00014, volume closure rel err 1.18e-14; verdicts **MET / REPORT**.
  Verified against `results/99_shared/sop/{00_reference,03_opt_geometry}_mesh_quality.csv`.
- [x] 5.3 `/api/validation/grid-independence` ← reads `results/99_shared/sop/grid_independence.json` verbatim → **NOT_MET** with sourced reason "0 of 3 refinement levels present under results/grid_independence/level_*" (the honest SOP audit conclusion — flipping it means re-running `scripts/run_grid_independence.py` to emit all 3).
- [x] 5.4 GUI Limitations block rewritten (no stale "NO_DATA" / "not stored" claims): mesh numeric and residual stationarity now report real data; honesty notes clarify they are DSMC conservation-stationarity series, not CFD RMS residuals.
- [x] 5.5 Panels verified via `node selftest.mjs` (exit 0) and pixel read-back.

Genuinely still open (not implemented anywhere in the repo — confirmed by
`find`/`grep`/`tree` inspection this session):
- Streamlines / isosurface rendering - accepted DSMC limitation (SOP audit §3)
- 3-level grid-independence generator (run script present but only emits level_1/2)
- Figure self-sufficiency (labels/units/case, Ch.13.3) - generator-side
- optimization, ssh/remote solver, Manim demo, CAD preview routes
- toroid-radius input in the wizard (sidecar config holds 0.135 m)

- [x] 4.1 Launch sidecar (`venv/python/bin/python3 src/ui/sidecar_ui.py --port <free>`)
- [x] 4.2 Headless-Chrome screenshot of every new/changed page → PNG
- [x] 4.3 Read each PNG back; check layout, contrast, alignment, truncation, labels (units + case + quantity per SOP 13.3)
- [x] 4.4 Fix + re-snap until clean

**Phase 4 RESULT (2026-10-16): DONE.** 11 screenshots captured to
`tests/screenshots/` (gitignored; visual read-back done by the Image
Specialist subagent, three rounds, all pixel-measured; measurement
scripts in `/private/var/folders/.../T/opencode/` scratch space).

Corrections applied during re-snaps:
  - D1 (p6_setup_sheet): code-box now solid `#0f172a` (contrast 14.42:1 vs
    `#e5e7eb`) + dim hint line "Full record — scroll inside the box above."
  - D2 (gates/convergence tables): row separators `#9ca3af` (2.36-2.47:1),
    header rules `#6b7280` (4.47/4.63:1) — both were near-invisible light grey
  - D3 (mesh quality): thumbnails now wrap 3-per-row instead of clipping a 4th
    card at the container edge; open full-size via anchor in a new tab
  - D4 (limitations): bold lead-ins `#a16207` (4.92:1), zero `#ff…` yellow
  - Status glyphs are now **solid pills with white text** (MET #047857,
    NOT MET #b91c1c, PARTIAL/NO DATA #a16207; 4.92-6.47:1) on the light
    theme instead of bright outline text
  - Gates/Evidence gates now have uppercase `ITEM / STATUS / NOTE` headers
    with a bottom rule and both tables' Status/Note columns are pixel-aligned
    (x714 / x830) via fixed `table-layout: fixed` widths
  - Row-5 CSV path (`results/…/convergence_audit.csv`) now wraps inside the
    Note column (rightmost glyph at x1202, 9 px inside the table edge)
  - Table row borders, placeholder text (#b91c1c, was #f87171) and
    convergence NO-DATA banners (#a16207, was #fbbf24) all re-tuned for the
    light backdrop

Unresolved / accepted:
  - 4 WARNs in selftest are PRE-EXISTING null-guarded dead bindings
    (`manual-title-text`, `.toc-item`, `.history-item`, `.manual-search-box`),
    not defects in my code
  - WITHIN / OUTSIDE pill colors are not exercised (no in-criteria run data)
  - hard clip at footer (y737) is scrollable content, not an obstruction
  - run results pending `.status.json` inputs; Phase uses read-back only

Stability: `node selftest.mjs` → exit 0, **283 PASS / 0 FAIL / 4 WARN**, on
three consecutive runs after the socket-layer change
(`ThreadingHTTPServer` + `protocol_version = HTTP/1.1`), which eliminated
the intermittent `net::ERR_CONNECTION_RESET` on `/api/*`.<|end|>

**Phase 4 checkpoint:** screenshot evidence attached for each panel.

---

## Out of scope (flagged, not dropped)

- [-] 3-level grid-independence **generator** (repo-side physics work; SOP audit ranks it #1 repo gap — separate task)
- [-] Streamlines / isosurfaces rendering (accepted DSMC limitation → stated in Limitations block)
- [-] Plot label regeneration for Ch.13.3 figure self-sufficiency (generator-side concern)

## Execution order

Phase 1 → 2 → 3 → 4. Each phase ends with its checkpoint; stop and report
at each checkpoint, continue only with user approval.
