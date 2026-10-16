# Sidecar TODO — CFD SOP ↔ GUI compliance plan

> Scope: make the sidecar GUI able to **supply every requirement of
> `Standard Operating Procedure of CFD.md` (688 lines) — at minimum, all the
> features that SOP checks.** Reference audits: `SOP_COMPLIANCE_AUDIT.md`
> (repo outputs), this plan (GUI coverage).
> Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` cut
> Approved by user: pending (plan awaiting approval before execution).

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

- [ ] 2.1 **Gates & Evidence view**: Ch.15 gate checklist (7 groups) + Ch.12 evidence-pack 10-item table, each row live-statused (✅ / NOT MET + why) via Phase-1 endpoints
- [ ] 2.2 **Mesh Quality panel**: min/mean table (skewness, ortho quality, aspect, growth) with SOP acceptance bands as thresholds (`<0.25/<0.5`, `>0.1/>0.2`, growth `≤1.2–1.3`); embed `mesh_statistics_*.png`; explicit NOT MET until numeric data exists
- [ ] 2.3 **Mesh Independence panel**: reuse `#grid-test-steps/#grid-test-factors` controls + 3-level result plot + Δ-between-levels vs tolerance + honest gate state
- [ ] 2.4 **Convergence panel**: residual curve + monitor plateau + mass-balance row from `/api/convergence`
- [ ] 2.5 **Setup Sheet view** (Final Review page): render `/api/setup-sheet`, Print (`window.print`) + Download as Markdown/JSON
- [ ] 2.6 **Uncertainty on results**: metrics + IRVE-3 table render `value ± tol` from existing `#target-*-tol`; comparisons state baseline + % difference (SOP 13.4)
- [ ] 2.7 **Export buttons**: CSV/JSON download of metrics, config, setup sheet (client-side Blob)
- [ ] 2.8 **Limitations block** (static): includes accepted limitation note for streamlines/isosurfaces (audit §3)
- [ ] 2.9 New panel elements/routines added to `tests/manifest.generated.mjs` + `tests/ROUTINES` in `selftest.mjs` (regenerate manifest: `node gen_manifest.mjs`)

**Phase 2 checkpoint:** every SOP row in matrix §A shows ✅ (or 🟡 with the
reason recorded in Limitations) when the sidecar runs.

## Phase 3 — Self-test

- [ ] 3.1 Extend `tests/selftest.mjs` KNOWN_MISSING list: remove now-implemented endpoints, add `not_implemented` routes as expected-WARN
- [ ] 3.2 Run `node tests/selftest.mjs` → **zero FAIL** (missing repo data = WARN/NOT MET, never FAIL)
- [ ] 3.3 Fix every FAIL found (report → user approval → fix → re-run)

**Phase 3 checkpoint:** self-test matrix exit code 0, report JSON archived.

## Phase 4 — Visual verification

- [ ] 4.1 Launch sidecar (`venv/python/bin/python3 src/ui/sidecar_ui.py --port <free>`)
- [ ] 4.2 Headless-Chrome screenshot of every new/changed page → PNG
- [ ] 4.3 Read each PNG back; check layout, contrast, alignment, truncation, labels (units + case + quantity per SOP 13.3)
- [ ] 4.4 Fix + re-snap until clean

**Phase 4 checkpoint:** screenshot evidence attached for each panel.

---

## Out of scope (flagged, not dropped)

- [-] 3-level grid-independence **generator** (repo-side physics work; SOP audit ranks it #1 repo gap — separate task)
- [-] Streamlines / isosurfaces rendering (accepted DSMC limitation → stated in Limitations block)
- [-] Plot label regeneration for Ch.13.3 figure self-sufficiency (generator-side concern)

## Execution order

Phase 1 → 2 → 3 → 4. Each phase ends with its checkpoint; stop and report
at each checkpoint, continue only with user approval.
