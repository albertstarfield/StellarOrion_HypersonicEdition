// Phase 4 screenshot harness (src/ui/todo.md 4.1-4.4): boots the sidecar
// exactly like selftest, drives the wizard to each changed page, and snaps
// viewport PNGs (top + scrolled) into tests/screenshots/ for read-back.
// References: playwright-core screenshot API, sidecar_ui.py fixture path set
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { resolve, join } from 'node:path';

const HERE = import.meta.dirname;                       // tests/
const UI_DIR = resolve(HERE, '..');                     // src/ui/uiassets
const SRC_UI = resolve(UI_DIR, '..');                   // src/ui
const SRC_DIR = resolve(UI_DIR, '..', '..');            // src
const PROC_ROOT = resolve(SRC_DIR, '..');               // stellarorion_program_proc
const SERVER = join(SRC_UI, 'sidecar_ui.py');
const VENV_PY = join(PROC_ROOT, 'venv', 'python', 'bin', 'python3');
const SHOTS = join(HERE, 'screenshots');
mkdirSync(SHOTS, { recursive: true });

const port = 18993;
console.log(`[shoot] sidecar on ${port} …`);
const proc = spawn(VENV_PY, [SERVER, '--port', String(port)], { cwd: PROC_ROOT, stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 1500));

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-unsafe-swiftshader'] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.log('[console.error]', m.text()); });

await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'domcontentloaded' });
// Splash must fade (INC-SPLASH-002) before capturing.
await page.waitForFunction(() => {
  const s = document.getElementById('splash');
  return !s || getComputedStyle(s).display === 'none';
}, { timeout: 8000 });
await page.evaluate(() => {
  window.__forceUnlock = () => {
    ['progress-bar', 'opt-progress-bar'].forEach((id) => {
      const b = document.getElementById(id);
      if (b) b.style.width = '0%';
    });
  };
});
await page.waitForTimeout(800);

// --- page 1 (boot state) ---
await page.screenshot({ path: join(SHOTS, 'p1_mission_brief.png') });

// --- page 5 (domain preview img remap) ---
await page.evaluate(() => { window.__forceUnlock(); nextStep(5); });
await page.waitForTimeout(600);
await page.screenshot({ path: join(SHOTS, 'p5_survivability_top.png') });

// --- page 6: SOP panels (setup sheet, gates, mesh quality, independence, limitations) ---
await page.evaluate(() => { window.__forceUnlock(); nextStep(6); });
await page.waitForFunction(() => {
  const b = document.getElementById('setup-sheet-body');
  return b && b.innerText.includes('Setup Sheet');
}, { timeout: 8000 });
await page.waitForTimeout(600);
await page.screenshot({ path: join(SHOTS, 'p6_review_top.png') });
// Scroll the setup sheet + its toolbar into view (below the domain preview).
await page.evaluate(() => {
  const el = document.getElementById('setup-sheet-body');
  if (el) el.scrollIntoView({ block: 'center' });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p6_setup_sheet.png') });
// Scroll the SOP sections into view for the read-back.
await page.evaluate(() => {
  const el = document.getElementById('gates-evidence-table');
  if (el) el.scrollIntoView({ block: 'start' });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p6_gates_evidence.png') });
await page.evaluate(() => {
  const el = document.getElementById('mesh-quality-table');
  if (el) el.scrollIntoView({ block: 'start' });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p6_mesh_quality.png') });
await page.evaluate(() => {
  const el = document.getElementById('limitations-list');
  if (el) el.scrollIntoView({ block: 'start' });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p6_limitations.png') });

// --- page 8: convergence + uncertainty + exports ---
await page.evaluate(() => { window.__forceUnlock(); nextStep(8); });
await page.waitForFunction(() => {
  const c = document.getElementById('convergence-table');
  return c && c.innerText.includes('Source');
}, { timeout: 8000 });
await page.waitForTimeout(600);
await page.screenshot({ path: join(SHOTS, 'p8_results_top.png') });
await page.evaluate(() => {
  const el = document.getElementById('convergence-table');
  if (el) el.scrollIntoView({ block: 'start' });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p8_convergence.png') });
await page.evaluate(() => {
  const el = document.getElementById('uncertainty-table');
  if (el) el.scrollIntoView({ block: 'start' });
});
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p8_uncertainty.png') });
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(300);
await page.screenshot({ path: join(SHOTS, 'p8_exports.png') });

await browser.close();
proc.kill();
console.log('[shoot] done →', SHOTS);
process.exit(0);
