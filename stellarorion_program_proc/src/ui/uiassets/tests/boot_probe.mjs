// Boot-probe: load the wizard headless and print EVERY response >=400 and
// every requestfailed with its URL. Diagnostic helper for the selftest boot
// 404; not part of the suite itself.
// References: playwright-core request/response events
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { resolve, join } from 'node:path';

const UI_DIR = resolve(import.meta.dirname, '..');
const SRC_UI = resolve(UI_DIR, '..');
const PROC_ROOT = resolve(SRC_UI, '..', '..');
const SERVER = join(SRC_UI, 'sidecar_ui.py');
const VENV_PY = join(PROC_ROOT, 'venv', 'python', 'bin', 'python3');
const port = 18991;
const proc = spawn(VENV_PY, [SERVER, '--port', String(port)], { cwd: PROC_ROOT, stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 1500));

const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
page.on('response', (res) => console.log('RESP', res.status(), res.url()));
page.on('requestfailed', (req) => console.log('FAILED', req.url(), req.failure()?.errorText));
page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE.ERROR', m.text(), '| LOCATION:', JSON.stringify(m.location())); });
await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle', timeout: 20000 }).catch((e) => console.log('goto:', e.message));
await page.waitForTimeout(3000);
await browser.close();
proc.kill();
process.exit(0);
