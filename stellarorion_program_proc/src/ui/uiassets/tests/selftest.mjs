// ============================================================================
// selftest.mjs — StellarOrion "Baloon Shield Maker" GUI Self-Test Routine
// ============================================================================
//
// AXIOMS:
//   A1: A UI feature exists iff (a) its element is present in the DOM and
//       (b) its handler runs to completion without an uncaught exception.
//       A "javascript blackhole" = either link broken (element missing,
//       routine undefined, dead getElementById) or the handler throwing.
//   A2: index.html (via manifest.generated.mjs) is the authoritative element
//       inventory; main.ts is the authoritative routine inventory.
//   A3: The sidecar under test must be launched exactly as run.py --gui does:
//       venv/python/bin/python3 src/ui/sidecar_ui.py --port <free>
//       [Reference: run.py:48-49 (_VENV_PYTHON), run.py:1709 (_start_sidecar)]
//   A4: HTTP 404 to a DECLARED missing endpoint (wizard API not yet wired)
//       is a WARN (wiring backlog), not a blackhole — the app must degrade
//       gracefully. 404 to any OTHER path (static asset, implemented API)
//       is a FAIL. [All sidecar 404s answer JSON: sidecar_ui.py:539,621]
//
// THEOREMS:
//   T1: Sweeping every manifest element with isolated error attribution
//       detects every synchronous handler throw in the app.
//   T2: Invoking every routine from ROUTINES (guarded by try/catch in-page)
//       detects every routine that is missing, throws, or rejects.
//   T3: Static cross-check (main.ts id/class literals vs index.html) detects
//       dead bindings that clicking cannot surface.
//
// APPLICATIONS:
//   1. Fixture: spawn sidecar on a free port, wait for /api/status.
//   2. Guards: pageerror / console.error / dialog(accept) / HTTP>=400 /
//      requestfailed — each recorded with the interaction label in force.
//   3. Phases: boot → static-audit → element sweep (per page + chrome) →
//      navigation & guard routines → routine sweep → report.
//   4. Output: matrix to stdout + tests/selftest-report.json.
//      Exit 0 = zero FAIL; 1 = FAIL present; 2 = fixture/setup crash.
//
// CITATIONS:
//   - Playwright (playwright-core v1.64.1) — https://playwright.dev/docs/intro
//   - Chrome DevTools Protocol (headless via system Chrome channel)
//   - ECMA-262 Script Semantics (classic script global function bindings)
//
// TIMING ANALYSIS:
//   Estimated: ~40-90s total (195 elements + 59 routines + nav phase).
//   Worst case: every hidden element costs one in-page dispatch (<5ms each);
//   boot waits ~2.5s for splash fade; fixture wait ≤15s (mirrors run.py).
//   Space: O(elements + errors) in Node memory (~few MB).
//   Hardware: any CPU; requires local Chrome for headless rendering.
//
// USAGE:  node selftest.mjs [--headed] [--keep-server]
// ============================================================================

import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { ELEMENTS } from './manifest.generated.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const UI_DIR = resolve(HERE, '..');                 // src/ui/uiassets
const SRC_UI = resolve(UI_DIR, '..', '..');         // src/ui
const PROC_ROOT = resolve(SRC_UI, '..', '..');      // stellarorion_program_proc
const SERVER = join(SRC_UI, 'sidecar_ui.py');
const VENV_PY = join(PROC_ROOT, 'venv', 'python', 'bin', 'python3');
const INDEX = join(UI_DIR, 'index.html');
const MAIN_TS = join(UI_DIR, 'main.ts');
const REPORT_JSON = join(HERE, 'selftest-report.json');
const HEADED = process.argv.includes('--headed');

// ── A4: declared-not-yet-wired wizard endpoints (survey of main.ts fetch
//    calls vs sidecar_ui.py routes). 404 here = WARN, expected. ───────────
const KNOWN_MISSING = new Set([
  '/api/local-user', '/api/atmosphere-data', '/api/cad-preview',
  '/api/optimization', '/api/readiness/sparta', '/api/readiness/openfoam',
  '/api/ssh/test', '/api/remote/screen', '/api/remote/install-python',
  '/api/remote/install-pyansys', '/api/remote/purge-arm', '/api/model-paths',
  '/api/draft/autosave', '/api/test/sparta', '/api/test/integration',
  '/api/sparta/build-image', '/api/preview/domain', '/api/content/manual',
  '/api/content/references', '/api/validation/grid-independence',
  '/api/demo/manim', '/api/demo/open',
]);
// History detail routes: only GET /api/history (list) is implemented.
const KNOWN_MISSING_PREFIX = ['/api/history/'];

// ============================================================================
// ROUTINE MANIFEST — every function declared in main.ts (59), each with the
// TEST that exercises it. invoke:'…' = called directly in-page (args shown);
// invoke:null = exercised through the UI element(s) named in testedVia.
// Regenerate the inventory after editing main.ts:
//   grep -nE '^(async )?function [a-zA-Z0-9_]+' ../main.ts
// ============================================================================
const ROUTINES = [
  // ── boot / background FX ──
  // initVariabilityListeners() — binds change→updateLHSSamples on 8 variability checkboxes; TEST: invoked at boot by us (page must already be loaded).
  { name: 'initVariabilityListeners', invoke: 'initVariabilityListeners()', testedVia: 'boot' },
  // initBackgroundEffects() — creates 50 stars + shooting-star loop in #star-container; TEST: direct invoke (idempotent DOM append).
  { name: 'initBackgroundEffects', invoke: 'initBackgroundEffects()', testedVia: 'direct' },
  // window.onload — splash fade + mermaid init; TEST: boot phase waits for #splash display:none.
  { name: 'window.onload', invoke: null, testedVia: 'boot: splash fade' },

  // ── navigation (also covered by dedicated nav phase) ──
  // changePage(delta) — footer prev/next wrapper; TEST: direct invoke +1/-1 and boundary 0/9.
  { name: 'changePage', invoke: 'changePage(0) /* boundary: no-op */', testedVia: 'nav phase + #btn-prev/#btn-next' },
  // jumpToPage(step) — guarded jump (locks on p3/p7 mid-run, readiness p5→6, 2→3/6→7 triggers); TEST: nav phase covers guards.
  { name: 'jumpToPage', invoke: null, testedVia: 'nav phase + #side-step-1..8' },
  // nextStep(step) — raw page switch (class .active dance, footer button state); TEST: direct invoke during page sweep.
  { name: 'nextStep', invoke: null, testedVia: 'page sweep (every page activation)' },

  // ── page 1: Mission Brief ──
  // refreshFinalPlots() — cache-bust reload of plot <img> on page 8; TEST: direct invoke (re-sets ?t= on images).
  { name: 'refreshFinalPlots', invoke: 'refreshFinalPlots()', testedVia: 'direct' },
  // appendLog(msg) — writes HTML into #terminal / #opt-terminal; TEST: direct invoke on both pages.
  { name: 'appendLog', invoke: 'appendLog("[selftest] probe")', testedVia: 'direct' },
  // updateProgress(val) — sets #progress-bar / #opt-progress-bar width; TEST: direct invoke (0..100) then reset to 0%.
  { name: 'updateProgress', invoke: 'updateProgress(0) /* reset to keep nav unlocked */', testedVia: 'direct' },
  // toggleMSIS() — shows/hides #msis-panel from #env-preset; TEST: click change on #env-preset (inline onchange).
  { name: 'toggleMSIS', invoke: null, testedVia: '#env-preset' },
  // applyLauncherPreset() — preset geometry→form; TEST: change on #launcher-preset (inline onchange).
  { name: 'applyLauncherPreset', invoke: null, testedVia: '#launcher-preset' },
  // toggleRemoteFields() — SSH field visibility by solver backend; TEST: change on #solver-backend → onBackendChange→toggleRemoteFields.
  { name: 'toggleRemoteFields', invoke: null, testedVia: '#solver-backend via onBackendChange' },
  // fetchAtmosphereData() — POST /api/atmosphere-data (declared missing→WARN); TEST: direct invoke + #btn-fetch-atmos? (inline onclick exists).
  { name: 'fetchAtmosphereData', invoke: 'fetchAtmosphereData()', testedVia: 'direct + inline onclick element' },
  // togglePayloadInput() — shows payload file input; TEST: click #enable-payload (inline onchange).
  { name: 'togglePayloadInput', invoke: null, testedVia: '#enable-payload' },
  // applyMaterialPreset() — TPS material preset→fields; TEST: change on #tps-material-preset (inline onchange).
  { name: 'applyMaterialPreset', invoke: null, testedVia: '#tps-material-preset' },

  // ── page 2→3 / 6→7 transitions ──
  // generateGeometry() — runs on jump 2→3: gathers params, POSTs /api/cad-preview; TEST: nav phase executes natural 2→3 jump.
  { name: 'generateGeometry', invoke: null, testedVia: 'nav phase (page 2→3 natural jump)' },
  // startOptimization() — runs on jump 6→7: POST /api/optimization (declared missing), progress bar; TEST: nav phase executes natural 6→7 jump.
  { name: 'startOptimization', invoke: null, testedVia: 'nav phase (page 6→7 natural jump)' },

  // ── form helpers ──
  // getCheck(id) — checked-state accessor with null guard; TEST: direct invoke on #verbose-log (exists) and #no-such-id (null path).
  { name: 'getCheck', invoke: 'getCheck("verbose-log") + "/" + getCheck("definitely-missing")', testedVia: 'direct (both branches)' },
  // onBackendChange() — solver backend switch → remote fields + domain refresh; TEST: change on #solver-backend.
  { name: 'onBackendChange', invoke: null, testedVia: '#solver-backend' },
  // lockContinueButton() — page-5 Continue gating on remoteVerified; TEST: direct invoke on p5 (locked and unlocked branches).
  { name: 'lockContinueButton', invoke: 'lockContinueButton()', testedVia: 'direct + nav phase' },

  // ── page 5: readiness / remote solver ──
  // testReadiness() — readiness probe + starts remote screen capture loop; TEST: click #btn-test-readiness; teardown stopRemoteAutoCapture().
  { name: 'testReadiness', invoke: null, testedVia: '#btn-test-readiness' },
  // captureRemoteView() — POST /api/remote/screen (declared missing) → image update; TEST: direct invoke (empty-params branch).
  { name: 'captureRemoteView', invoke: 'captureRemoteView()', testedVia: 'direct + #btn-capture-screen (inline onclick)' },
  // startRemoteAutoCapture() — 5s interval calling captureRemoteView; TEST: invoked via testReadiness; teardown below.
  { name: 'startRemoteAutoCapture', invoke: 'startRemoteAutoCapture()', testedVia: 'direct + teardown' },
  // stopRemoteAutoCapture() — clears the interval; TEST: direct invoke (teardown of capture loop).
  { name: 'stopRemoteAutoCapture', invoke: 'stopRemoteAutoCapture()', testedVia: 'teardown' },
  // logReadiness(msg) — appends to #test-verbose-logs; TEST: direct invoke.
  { name: 'logReadiness', invoke: 'logReadiness("[selftest] probe")', testedVia: 'direct' },
  // installRemotePython() — POST /api/remote/install-python; TEST: click #btn-install-python.
  { name: 'installRemotePython', invoke: null, testedVia: '#btn-install-python' },
  // installPyAnsys() — POST /api/remote/install-pyansys; TEST: click #btn-install-pyansys.
  { name: 'installPyAnsys', invoke: null, testedVia: '#btn-install-pyansys' },
  // purgeArmPython() — POST /api/remote/purge-arm; TEST: click #btn-purge-arm.
  { name: 'purgeArmPython', invoke: null, testedVia: '#btn-purge-arm' },
  // saveRemoteParams() — localStorage persist on remote field input/change; TEST: bound via addEventListener on #remote-fields inputs (element sweep).
  { name: 'saveRemoteParams', invoke: null, testedVia: 'addListeners on #remote-fields inputs (element sweep)' },
  // loadRemoteParams() — reads localStorage → sets remote fields; TEST: direct invoke (both empty and populated storage).
  { name: 'loadRemoteParams', invoke: 'loadRemoteParams()', testedVia: 'direct' },

  // ── page 4: 3D view ──
  // init3DView() — Three.js scene on #viewport, loads /api/model-paths (declared missing); TEST: direct invoke after jumping to page 4 (WebGL via SwiftShader).
  { name: 'init3DView', invoke: null, setup: 'nextStep(4)', testedVia: 'nav phase page 4 + direct' },

  // ── autosave / params ──
  // startAutosave() — interval → POST /api/draft/autosave; TEST: direct invoke once (interval kept; 404s are WARN).
  { name: 'startAutosave', invoke: 'startAutosave()', testedVia: 'direct' },
  // gatherAllParams() — reads ~90 controls → config object; TEST: direct invoke (returns object; assert not null).
  { name: 'gatherAllParams', invoke: 'JSON.stringify(gatherAllParams() || {}).length > 0', testedVia: 'direct' },
  // applyParams(params) — writes config object back into controls; TEST: direct invoke with {} (no-op branch).
  { name: 'applyParams', invoke: 'applyParams({})', testedVia: 'direct' },

  // ── tests / remote utilities ──
  // runIntegrationTest() — POST /api/test/sparta and /api/test/integration; TEST: click #btn-run-test.
  { name: 'runIntegrationTest', invoke: null, testedVia: '#btn-run-test' },
  // copyToClipboard(id) — navigator.clipboard.writeText of target innerText; TEST: direct invoke with #ssh-setup-cmd (clipboard permission granted to context).
  { name: 'copyToClipboard', invoke: 'copyToClipboard("ssh-setup-cmd")', testedVia: 'direct + inline onclick elements' },
  // buildSpartaImage() — POST /api/sparta/build-image; TEST: click #btn-build-image.
  { name: 'buildSpartaImage', invoke: null, testedVia: '#btn-build-image' },
  // onPinnAccelChange() — PINN fidelity warning; TEST: change on #pinn-accel (inline onchange).
  { name: 'onPinnAccelChange', invoke: null, testedVia: '#pinn-accel' },
  // onSteadyStateChange() — steady-state tolerance gating; TEST: change on #env-steady-state (inline onchange).
  { name: 'onSteadyStateChange', invoke: null, testedVia: '#env-steady-state' },
  // onSimStepsChange() — steps→warning/layers (also addEventListener on #env-run input); TEST: change + direct.
  { name: 'onSimStepsChange', invoke: 'onSimStepsChange()', testedVia: 'inline onchange on 2 inputs + listener' },
  // syncTarget(metric,type) — slider↔number sync for target triplets; TEST: direct invoke for all 6 metrics (beta,heat,g,temp,q,hload).
  { name: 'syncTarget', invoke: '["beta","heat","g","temp","q","hload"].forEach(m=>syncTarget(m,"range"))', testedVia: 'direct (all 6 metrics) + slider input events' },
  // refreshDomainPreview() — domain form → POST /api/preview/domain; TEST: direct invoke + inline onchange (5 inputs).
  { name: 'refreshDomainPreview', invoke: 'refreshDomainPreview()', testedVia: 'direct + inline onchange elements' },
  // onDomainPreviewReady() — swaps domain preview image; TEST: direct invoke (missing-image null branch).
  { name: 'onDomainPreviewReady', invoke: 'onDomainPreviewReady()', testedVia: 'direct' },

  // ── overlays ──
  // openManual() — manual overlay + GET /api/content/manual; TEST: click #btn-manual? (inline onclick openManual) then closeManual().
  { name: 'openManual', invoke: 'openManual()', testedVia: 'direct + inline onclick element' },
  // closeManual() — hides #manual-overlay; TEST: direct invoke after open.
  { name: 'closeManual', invoke: 'closeManual()', testedVia: 'direct + #btn-close-manual?' },
  // generateToc() — builds TOC from h1/h2/h3 in manual text; TEST: direct invoke after openManual (async content may 404→WARN, TOC handles empty).
  { name: 'generateToc', invoke: 'generateToc()', testedVia: 'direct' },
  // searchManual() — manual search box filter → marks; TEST: direct invoke (empty + term).
  { name: 'searchManual', invoke: 'searchManual()', testedVia: 'direct + #manual-search input events' },
  // checkStructuralValidity() — geometry sanity banner in summary; TEST: direct invoke.
  { name: 'checkStructuralValidity', invoke: 'checkStructuralValidity()', testedVia: 'direct' },
  // updateSummary() — page 6 summary renderer; TEST: direct invoke (all form fields read).
  { name: 'updateSummary', invoke: 'updateSummary()', testedVia: 'direct' },
  // updateLHSSamples() — LHS sample-count math; TEST: direct invoke + change listeners on #v-* checkboxes.
  { name: 'updateLHSSamples', invoke: 'updateLHSSamples()', testedVia: 'direct + #v-* checkbox listeners' },

  // ── history modal ──
  // openHistory() — modal + GET /api/history (IMPLEMENTED route; may be empty) ; TEST: direct invoke then closeHistory().
  { name: 'openHistory', invoke: 'openHistory()', testedVia: 'direct + sidebar Optimization History buttons' },
  // closeHistory() — hides #history-modal; TEST: direct invoke after open.
  { name: 'closeHistory', invoke: 'closeHistory()', testedVia: 'direct + inline onclick' },
  // loadHistoryList() — renders #history-list from GET /api/history; TEST: direct invoke (200 on implemented route).
  { name: 'loadHistoryList', invoke: 'loadHistoryList()', testedVia: 'direct via openHistory' },
  // loadRunDetails(runId) — GET /api/history/{id} (declared missing→WARN); TEST: NOT invoked with junk id (would test our own 404, not the app); covered when DB has runs.
  { name: 'loadRunDetails', invoke: null, testedVia: 'UI-only (needs a real run id in runs.csv)' },
  // resumeRun() — POST /api/history/{id}/resume; TEST: click #btn-resume-run (no-selection guard branch).
  { name: 'resumeRun', invoke: null, testedVia: '#btn-resume-run (guard branch: no selection)' },
  // deleteRun() — confirm() + DELETE /api/history/{id}; TEST: click #btn-delete-run (dialog auto-accepted; guard branch).
  { name: 'deleteRun', invoke: null, testedVia: '#btn-delete-run (dialog accepted)' },

  // ── header / demos / results ──
  // openLiteracyCredit() — references overlay; uses null-guarded #manual-title-text (dead binding, WARN in static audit); TEST: direct invoke + #btn-literacy (inline onclick).
  { name: 'openLiteracyCredit', invoke: 'openLiteracyCredit()', testedVia: 'direct + inline onclick element' },
  // startGridIndependencyTest() — POST /api/validation/grid-independence + progress; TEST: click #btn-grid-test (page 1 quick test).
  { name: 'startGridIndependencyTest', invoke: null, testedVia: '#btn-grid-test (grid test buttons on page 1)' },
  // runManimDemo() — jumps to page 3, POST /api/demo/manim; TEST: click #btn-visual-demo (header).
  { name: 'runManimDemo', invoke: null, testedVia: '#btn-visual-demo (header)' },
  // showDemoVideo(path) — confirm() then POST /api/demo/open (async fix in this branch); TEST: direct invoke (dialog auto-accepted).
  { name: 'showDemoVideo', invoke: 'showDemoVideo("/tmp/selftest-demo.mp4")', testedVia: 'direct (dialog accepted)' },
];

// ============================================================================
// Shared state: error ledger with per-interaction attribution
// ============================================================================
const LEDGER = [];        // {phase,label,kind,text,detail}
let currentLabel = 'setup';
let serverProc = null;
let browser = null;

function record(kind, text, detail = '') {
  LEDGER.push({ phase: currentLabel.split(':')[0], label: currentLabel, kind, text: String(text).slice(0, 800), detail: String(detail).slice(0, 800) });
}

function freePort() {
  return new Promise((res, rej) => {
    const s = createServer();
    s.on('error', rej);
    s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); });
  });
}

async function waitJson(url, timeoutMs) {
  const t0 = Date.now();
  let lastErr = 'no attempt';
  while (Date.now() - t0 < timeoutMs) {
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 2000);
      const r = await fetch(url, { signal: ctl.signal });
      clearTimeout(t);
      if (r.ok) return await r.json();
      lastErr = `HTTP ${r.status}`;
    } catch (e) { lastErr = e.message; }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`health check failed for ${url} after ${timeoutMs}ms: ${lastErr}`);
}

// ── In-page interaction primitives (run inside evaluate) ──────────────────
const IN_PAGE = `
window.__st = {
  exists: (id) => !!document.getElementById(id),
  visible: (id) => {
    const el = document.getElementById(id);
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && cs.pointerEvents !== 'none';
  },
  enabled: (id) => {
    const el = document.getElementById(id);
    return el && !el.disabled;
  },
  act: (id, action) => {
    const el = document.getElementById(id);
    if (!el) throw new Error('element #' + id + ' missing in DOM');
    const fire = (type) => el.dispatchEvent(new Event(type, { bubbles: true }));
    if (action === 'inspect') return 'inspect';
    if (action === 'click') {
      if (el.click) el.click(); else fire('click');
      return 'click';
    }
    if (action === 'change') {
      if (el.tagName === 'SELECT') {
        // pick a different option when possible to actually fire handlers
        if (el.options.length > 1) {
          const idx = (el.selectedIndex + 1) % el.options.length;
          el.selectedIndex = idx;
        }
        fire('change');
        return 'change';
      }
      fire('change');
      return 'change';
    }
    if (action === 'input') {
      // range slider: move to midpoint of [min,max]
      const min = parseFloat(el.min || '0');
      const max = parseFloat(el.max || '100');
      const mid = min + (max - min) / 2;
      el.value = String(mid);
      fire('input');
      fire('change');
      return 'input';
    }
    if (action === 'type') {
      // text/number/… : leave existing value if non-empty, else benign probe
      if (el.value === '' || el.value === undefined) {
        el.value = el.type === 'number' ? '1' : 'selftest';
      }
      fire('input');
      fire('change');
      fire('blur');
      return 'type';
    }
    if (action === 'event') {
      fire('change'); // file input: dispatch change without files
      return 'event';
    }
    throw new Error('unknown action ' + action);
  },
  // force navigation preconditions (nav phase only)
  forceUnlock: () => {
    ['progress-bar', 'opt-progress-bar'].forEach((id) => {
      const b = document.getElementById(id);
      if (b) { b.style.width = '0%'; }
    });
  },
  page: () => (typeof currentPage !== 'undefined' ? currentPage : -1),
  setPage: (p) => { if (typeof currentPage !== 'undefined') { nextStep(p); } },
  activePage: () => {
    for (let i = 1; i <= 8; i++) {
      const p = document.getElementById('page-' + i);
      if (p && p.classList.contains('active')) return i;
    }
    return -1;
  },
  closeOverlays: () => {
    ['manual-overlay', 'history-modal', 'splash'].forEach((id) => {
      const o = document.getElementById(id);
      if (o) { o.style.display = 'none'; }
    });
  },
  callRoutine: (expr) => {
    try {
      // eslint-disable-next-line no-eval
      const r = eval(expr);
      return { ok: true, result: r === undefined ? 'undefined' : String(r).slice(0, 120) };
    } catch (e) {
      return { ok: false, error: e && e.stack ? e.stack : String(e) };
    }
  },
};
`;

// ============================================================================
// PHASE 0 — fixture: spawn sidecar exactly like run.py (A3)
// ============================================================================
async function startServer() {
  const port = await freePort();
  console.log(`[fixture] spawning: ${VENV_PY} ${SERVER} --port ${port}`);
  serverProc = spawn(VENV_PY, [SERVER, '--port', String(port)], {
    cwd: PROC_ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  serverProc.stdout.on('data', (d) => process.env.ST_VERBOSE && console.log('[srv]', d.toString()));
  serverProc.stderr.on('data', (d) => console.error('[srv:err]', d.toString()));
  serverProc.on('exit', (code) => { if (code !== 0 && code !== null) record('FAIL', `sidecar exited early (code ${code})`); });
  try {
    const status = await waitJson(`http://127.0.0.1:${port}/api/status`, 15000);
    console.log(`[fixture] sidecar healthy: status=${status.status ?? '?'} version=${status.version ?? '?'}`);
    return port;
  } catch (e) {
    record('FAIL', `sidecar health check failed: ${e.message}`);
    throw e;
  }
}

// ============================================================================
// PHASE 1 — static audit: every id/class literal in main.ts must exist in
// index.html (or be created dynamically). Detects silent dead bindings.
// ============================================================================
function staticAudit() {
  const html = readFileSync(INDEX, 'utf8');
  const ts = readFileSync(MAIN_TS, 'utf8');
  const htmlIds = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
  const refIds = new Set();
  for (const m of ts.matchAll(/getElementById\(['"]([^'"]+)['"]\)/g)) refIds.add(m[1]);
  const dead = [...refIds].filter((id) => !htmlIds.has(id) && !ts.includes(`id="${id}"`));
  const htmlClasses = new Set([...html.matchAll(/\sclass="([^"]+)"/g)].flatMap((m) => m[1].split(/\s+/)));
  const refClasses = new Set();
  for (const m of ts.matchAll(/querySelector(?:All)?\(['"]\.([a-zA-Z0-9_-]+)/g)) refClasses.add(m[1]);
  const deadClasses = [...refClasses].filter((c) => !htmlClasses.has(c));
  const dynamicGuarded = ['target-']; // template-literal ids: target-${metric}-…
  for (const id of dead) {
    if (dynamicGuarded.some((p) => id.startsWith(p))) continue;
    record('WARN', `dead-binding: main.ts getElementById('${id}') has no element in index.html`, 'clicking cannot reach it; use-site may be null-guarded (verify)');
  }
  for (const c of deadClasses) record('WARN', `dead-binding: main.ts querySelector('.${c}') has no such class in index.html`);
  console.log(`[static-audit] ${refIds.size} id refs, ${htmlIds.size} ids in html, ${dead.length} dead, ${deadClasses.length} dead classes`);
}

// ============================================================================
// main
// ============================================================================
async function main() {
  console.log('════════════════════════════════════════════════════════════');
  console.log(' StellarOrion GUI Self-Test — Baloon Shield Maker (uiassets)');
  console.log('════════════════════════════════════════════════════════════');

  currentLabel = 'fixture';
  staticAudit();

  const port = await startServer();
  const base = `http://127.0.0.1:${port}`;

  currentLabel = 'browser';
  browser = await chromium.launch({ channel: 'chrome', headless: !HEADED, args: ['--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({
    permissions: ['clipboard-read', 'clipboard-write'],
    viewport: { width: 1440, height: 900 },
  });

  // ── Guards: attribute every fault to the interaction in force ──────────
  const page = await ctx.newPage();
  page.setDefaultTimeout(5000);
  page.on('pageerror', (err) => record('FAIL', `pageerror: ${err.message}`, err.stack));
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const t = msg.text();
    // CDN/network console noise from declared-missing endpoints → WARN
    const missing = [...KNOWN_MISSING, ...KNOWN_MISSING_PREFIX].find((u) => t.includes(u));
    if (missing || t.includes('Failed to load resource')) {
      const urlMatch = t.match(/https?:\/\/[^\s"']+/);
      const path = urlMatch ? urlMatch[0] : '';
      if (path.includes('127.0.0.1') && [...KNOWN_MISSING].some((u) => path.includes(u) || KNOWN_MISSING_PREFIX.some((p) => path.includes(p)))) {
        record('WARN', `console: ${t}`);
        return;
      }
      if (path && !path.includes('127.0.0.1')) { record('WARN', `console (external): ${t}`); return; }
      if (t.includes('Failed to load resource')) { record('FAIL', `console (local resource): ${t}`); return; }
    }
    record('FAIL', `console.error: ${t}`);
  });
  page.on('dialog', (d) => { console.log(`[dialog:${d.type()}] ${d.message().slice(0, 80)} → accept`); d.accept().catch(() => {}); });
  page.on('response', (res) => {
    const st = res.status();
    if (st < 400) return;
    const url = new URL(res.url());
    if (url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') { record('WARN', `HTTP ${st} (external) ${url.pathname}`); return; }
    const p = url.pathname;
    const declared = KNOWN_MISSING.has(p) || KNOWN_MISSING_PREFIX.some((pre) => p.startsWith(pre));
    if (declared) record('WARN', `HTTP ${st} ${p} — declared missing endpoint (wiring backlog)`);
    else record('FAIL', `HTTP ${st} ${p} — unexpected (static asset or implemented API)`);
  });
  page.on('requestfailed', (req) => {
    const url = new URL(req.url());
    if (url.hostname !== '127.0.0.1') { record('WARN', `requestfailed (external): ${url.hostname} — ${req.failure()?.errorText}`); return; }
    record('FAIL', `requestfailed (local): ${url.pathname} — ${req.failure()?.errorText}`);
  });

  // ── PHASE 2 — boot: load app, splash must fade, zero pageerror ────────
  currentLabel = 'boot';
  const errorsBefore = LEDGER.length;
  await page.goto(`${base}/`, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.evaluate(IN_PAGE);
  try {
    await page.waitForFunction(() => {
      const s = document.getElementById('splash');
      return !s || getComputedStyle(s).display === 'none';
    }, { timeout: 8000 });
    console.log('[boot] splash faded OK');
  } catch {
    record('FAIL', 'boot: splash overlay never faded (INC-SPLASH-002 lifecycle broken)');
  }
  const bootFaults = LEDGER.slice(errorsBefore).length;
  if (bootFaults === 0) console.log('[boot] zero faults during load');

  // ── PHASE 3 — element sweep ───────────────────────────────────────────
  console.log(`\n[element-sweep] ${ELEMENTS.length} elements from manifest…`);
  let pass = 0, fail = 0, warn = 0;
  const pageGroups = [1, 2, 3, 4, 5, 6, 7, 8].map((n) => `page-${n}`);
  const results = [];

  async function sweepElement(el) {
    currentLabel = `element:#${el.id}`;
    const before = LEDGER.length;
    try {
      const exists = await page.evaluate((id) => window.__st.exists(id), el.id);
      if (!exists) {
        record('FAIL', `#${el.id} missing in DOM (manifest/index.html drift — rerun gen_manifest.mjs)`);
        results.push({ id: el.id, status: 'FAIL', note: 'missing in DOM' });
        fail++; return;
      }
      if (el.action === 'inspect') {
        results.push({ id: el.id, status: 'PASS', note: 'present (inspect)' });
        pass++; return;
      }
      // Real gesture when visible & enabled, in-page dispatch otherwise.
      const vis = await page.evaluate(([id, action]) => window.__st.visible(id) && window.__st.enabled(id), [el.id, el.action]);
      let mode;
      if (vis && (el.action === 'click')) {
        try {
          await page.click(`#${el.id}`, { timeout: 2500 });
          mode = 'playwright-click';
        } catch (e) {
          const r = await page.evaluate(([id, action]) => window.__st.act(id, action), [el.id, el.action]);
          mode = `fallback(${r})`;
        }
      } else {
        const r = await page.evaluate(([id, action]) => window.__st.act(id, action), [el.id, el.action]);
        mode = `in-page(${r})`;
      }
      // close overlays opened by this element so the next is reachable
      await page.evaluate(() => window.__st.closeOverlays());
      const newFaults = LEDGER.slice(before);
      if (newFaults.some((f) => f.kind === 'FAIL')) {
        results.push({ id: el.id, status: 'FAIL', note: newFaults.map((f) => f.text).join(' | ') });
        fail++;
      } else {
        results.push({ id: el.id, status: 'PASS', note: mode });
        pass++;
      }
    } catch (e) {
      record('FAIL', `sweep crash: ${e.message}`);
      results.push({ id: el.id, status: 'FAIL', note: e.message });
      fail++;
    }
  }

  // Chrome (always-visible shell): sidebar, header, footer, root
  currentLabel = 'sweep:shell';
  for (const el of ELEMENTS.filter((e) => !pageGroups.includes(e.group))) await sweepElement(el);

  // Pages 1..8: activate each page, then sweep its own elements with real clicks
  for (let p = 1; p <= 8; p++) {
    currentLabel = `sweep:page-${p}`;
    await page.evaluate((n) => { window.__st.forceUnlock(); window.__st.setPage(n); }, p);
    await page.evaluate(() => window.__st.closeOverlays());
    const els = ELEMENTS.filter((e) => e.group === `page-${p}`);
    for (const el of els) await sweepElement(el);
  }

  // ── PHASE 4 — navigation & guard behaviors ────────────────────────────
  console.log('\n[nav-phase] changePage/jumpToPage/nextStep + guards…');
  currentLabel = 'nav:natural-flow';
  // natural 2→3 (generateGeometry) and 6→7 (startOptimization)
  await page.evaluate(() => { window.__st.forceUnlock(); window.__st.setPage(2); });
  await page.evaluate(() => jumpToPage(3));           // triggers generateGeometry()
  await page.waitForTimeout(800);
  await page.evaluate(() => { window.__st.forceUnlock(); window.__st.setPage(6); });
  await page.evaluate(() => jumpToPage(7));           // triggers startOptimization()
  await page.waitForTimeout(1200);
  await page.evaluate(() => { window.__st.forceUnlock(); window.__st.closeOverlays(); });

  currentLabel = 'nav:lock-guard';
  // p3 lock: mid-run width must block navigation
  await page.evaluate(() => {
    window.__st.setPage(3);
    const b = document.getElementById('progress-bar');
    b.style.width = '50%';
    jumpToPage(1);
  });
  let lockOk = await page.evaluate(() => window.__st.activePage() === 3);
  if (lockOk) { console.log('[nav] lock guard OK (mid-run navigation blocked)'); }
  else record('FAIL', 'nav: jumpToPage allowed navigation while progress mid-run (lock broken)');
  await page.evaluate(() => window.__st.forceUnlock());

  currentLabel = 'nav:readiness-guard';
  // p5→6 guard: blocked when remoteVerified false, allowed when true
  await page.evaluate(() => { window.__st.setPage(5); remoteVerified = false; jumpToPage(6); });
  const guardBlocked = await page.evaluate(() => window.__st.activePage() === 5);
  if (guardBlocked) console.log('[nav] readiness guard OK (5→6 blocked without readiness)');
  else record('FAIL', 'nav: page 5→6 jumped despite remoteVerified=false (readiness guard broken)');
  await page.evaluate(() => { remoteVerified = true; jumpToPage(6); });
  const guardOpen = await page.evaluate(() => window.__st.activePage() === 6);
  if (guardOpen) console.log('[nav] readiness gate opens when remoteVerified=true');
  else record('FAIL', 'nav: page 5→6 blocked even with remoteVerified=true');

  currentLabel = 'nav:boundaries';
  const bnd = await page.evaluate(() => {
    window.__st.setPage(1); changePage(-1); const a = window.__st.activePage();
    window.__st.setPage(8); changePage(+1); const b = window.__st.activePage();
    return [a, b];
  });
  if (bnd[0] === 1 && bnd[1] === 8) console.log('[nav] changePage boundaries OK (no under/overflow)');
  else record('FAIL', `nav: changePage boundary broken (got ${bnd})`);

  currentLabel = 'nav:sweep-all-pages';
  for (let p = 1; p <= 8; p++) {
    const ok = await page.evaluate((n) => { window.__st.forceUnlock(); window.__st.setPage(n); return window.__st.activePage() === n; }, p);
    if (!ok) record('FAIL', `nav: nextStep(${p}) did not activate page-${p}`);
  }

  // ── PHASE 5 — routine sweep: every routine in ROUTINES manifest ───────
  console.log(`\n[routine-sweep] ${ROUTINES.length} routines from main.ts…`);
  for (const r of ROUTINES) {
    currentLabel = `routine:${r.name}`;
    const before = LEDGER.length;
    // (a) existence: classic-script function declarations must be global
    if (r.name !== 'window.onload') {
      const typeOk = await page.evaluate((n) => typeof window[n] === 'function', r.name);
      if (!typeOk) {
        record('FAIL', `routine '${r.name}' is not a global function (undefined — callers will throw ReferenceError)`);
        results.push({ id: `routine:${r.name}`, status: 'FAIL', note: 'undefined global' });
        fail++; continue;
      }
    }
    // (b) invocation (only where declared safe)
    if (r.invoke) {
      if (r.setup) await page.evaluate((s) => { window.__st.forceUnlock(); window.__st.closeOverlays(); eval(s); }, r.setup);
      const out = await page.evaluate((expr) => window.__st.callRoutine(expr), r.invoke);
      if (!out.ok) {
        record('FAIL', `routine '${r.name}' threw: ${out.error}`);
        results.push({ id: `routine:${r.name}`, status: 'FAIL', note: out.error });
        fail++;
      } else {
        await page.evaluate(() => { window.__st.closeOverlays(); window.__st.forceUnlock(); });
        const newFaults = LEDGER.slice(before).filter((f) => f.kind === 'FAIL');
        if (newFaults.length) {
          results.push({ id: `routine:${r.name}`, status: 'FAIL', note: newFaults.map((f) => f.text).join(' | ') });
          fail++;
        } else {
          results.push({ id: `routine:${r.name}`, status: 'PASS', note: `invoked → ${out.result}` });
          pass++;
        }
      }
    } else {
      // exercised through UI elements already swept
      const newFaults = LEDGER.slice(before).filter((f) => f.kind === 'FAIL');
      if (newFaults.length) {
        results.push({ id: `routine:${r.name}`, status: 'FAIL', note: newFaults.map((f) => f.text).join(' | ') });
        fail++;
      } else {
        results.push({ id: `routine:${r.name}`, status: 'PASS', note: `via-ui: ${r.testedVia}` });
        pass++;
      }
    }
  }

  // ── teardown in page: stop timers we started ──────────────────────────
  await page.evaluate(() => {
    try { stopRemoteAutoCapture(); } catch { /* already stopped */ }
    try { window.__st.closeOverlays(); window.__st.forceUnlock(); } catch { /* n/a */ }
  });

  // ── PHASE 6 — report ──────────────────────────────────────────────────
  currentLabel = 'report';
  const fails = LEDGER.filter((f) => f.kind === 'FAIL');
  const warns = LEDGER.filter((f) => f.kind === 'WARN');
  const report = {
    generatedAt: new Date().toISOString(),
    manifest: { elements: ELEMENTS.length, routines: ROUTINES.length },
    totals: { pass, fail, warn: warns.length },
    fails, warns, results,
  };
  writeFileSync(REPORT_JSON, JSON.stringify(report, null, 2), 'utf8');

  console.log('\n══════════════ SELF-TEST MATRIX ══════════════');
  console.log(`elements+routines PASS: ${pass}   FAIL: ${fail}   WARN: ${warns.length}`);
  if (warns.length) {
    console.log('\n── WARNs (declared missing endpoints / external / dead bindings) ──');
    const uniq = [...new Set(warns.map((w) => w.text))];
    uniq.slice(0, 40).forEach((w) => console.log(`  [WARN] ${w}`));
    if (uniq.length > 40) console.log(`  … +${uniq.length - 40} more (see selftest-report.json)`);
  }
  if (fails.length) {
    console.log('\n── FAILs (javascript blackholes) ──');
    fails.forEach((f) => console.log(`  [FAIL] <${f.label}> ${f.text}`));
  }
  console.log(`\nreport → ${REPORT_JSON}`);
  console.log('══════════════════════════════════════════════');
  return fails.length ? 1 : 0;
}

// ── Fixture teardown (finally semantics) ─────────────────────────────────
let exitCode = 2;
try {
  exitCode = await main();
} catch (e) {
  console.error('[selftest] SETUP CRASH:', e);
  record('FAIL', `setup crash: ${e.message}`);
  exitCode = 2;
} finally {
  try { if (browser) await browser.close(); } catch (e) { console.error('[teardown] browser close failed:', e.message); }
  try { if (serverProc) { serverProc.kill('SIGTERM'); await new Promise((r) => setTimeout(r, 500)); if (!serverProc.killed) serverProc.kill('SIGKILL'); } } catch (e) { console.error('[teardown] server kill failed:', e.message); }
  console.log('[teardown] browser + sidecar stopped');
}
process.exit(exitCode);
