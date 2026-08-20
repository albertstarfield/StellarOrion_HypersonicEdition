/**
 * StellarOrion HypersonicEdition — Frontend Logic
 * =================================================
 * TypeScript source for the sidecar UI dashboard.
 * Compiles to main.js (vanilla JS, no bundler required).
 *
 * Features:
 *   - Real-time status polling (every 2 seconds)
 *   - Dashboard update functions
 *   - Splash screen initialization (INC-SPLASH-002)
 *   - Configuration form handling
 *
 * Author: Albert Starfield Wahyu Suryo Samudro
 */

const API_BASE = "";
const POLL_INTERVAL_MS = 2000;

// ── Types ──────────────────────────────────────────────────────────────

interface SimulationStatus {
  status: string;
  run_name: string;
  progress: number;
  results: Record<string, number>;
  metrics: Record<string, number>;
  window_title: string;
  version: string;
}

interface SimulationResults {
  results: Record<string, number>;
  metrics: Record<string, number>;
}

interface HistoryEntry {
  Name: string;
  Status: string;
  Progress: string;
  Mach: string;
  Altitude_Km: string;
  Diameter_M: string;
  Heat_Flux: string;
  Decel_G: string;
  Survivable: string;
}

interface HistoryResponse {
  runs: HistoryEntry[];
}

interface ConfigData {
  geometry: {
    diameter_m: number;
    angle_deg: number;
    nose_radius_m: number;
    toroid_count: number;
    toroid_radius_m: number;
    mass_kg: number;
  };
  flight: {
    mach: number;
    altitude_km: number;
    velocity_ms: number;
  };
  solver: string;
  chemistry: string;
  grid_factor: number;
}

// ── Splash Screen (INC-SPLASH-002) ─────────────────────────────────────

function initSplashScreen(): void {
  const overlay = document.getElementById("splash-overlay");
  const app = document.getElementById("app");
  if (!overlay || !app) return;

  // Wait for splash animation to complete, then fade out
  setTimeout(() => {
    overlay.classList.add("fade-out");
    app.classList.remove("hidden");

    // Remove overlay from DOM after transition
    overlay.addEventListener("transitionend", () => {
      overlay.remove();
    }, { once: true });
  }, 2800);
}

// ── API Helpers ────────────────────────────────────────────────────────

async function apiGet<T>(endpoint: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${endpoint}`);
  if (!resp.ok) {
    throw new Error(`API GET ${endpoint}: ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

async function apiPost<T>(endpoint: string, body?: Record<string, unknown>): Promise<T> {
  const resp = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(`API POST ${endpoint}: ${resp.status} ${JSON.stringify(err)}`);
  }
  return resp.json() as Promise<T>;
}

// ── DOM Helpers ────────────────────────────────────────────────────────

function setText(id: string, value: string): void {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setHTML(id: string, value: string): void {
  const el = document.getElementById(id);
  if (el) el.innerHTML = value;
}

function setStyle(id: string, prop: string, value: string): void {
  const el = document.getElementById(id);
  if (el) (el.style as Record<string, unknown>)[prop] = value;
}

function setDisabled(id: string, disabled: boolean): void {
  const el = document.getElementById(id) as HTMLButtonElement | null;
  if (el) el.disabled = disabled;
}

// ── Status Badge ───────────────────────────────────────────────────────

function updateStatusBadge(status: string): void {
  const badge = document.getElementById("status-badge");
  if (!badge) return;

  badge.className = "badge";
  switch (status) {
    case "running":
      badge.classList.add("badge-running");
      badge.textContent = "RUNNING";
      break;
    case "error":
      badge.classList.add("badge-error");
      badge.textContent = "ERROR";
      break;
    default:
      badge.classList.add("badge-stopped");
      badge.textContent = "STOPPED";
      break;
  }
}

// ── Dashboard Updates ──────────────────────────────────────────────────

function updateStatusPanel(data: SimulationStatus): void {
  setText("sim-state", data.status.toUpperCase());
  setText("sim-run-name", data.run_name || "--");

  const pct = Math.round(data.progress * 100);
  setText("sim-progress-pct", `${pct}%`);
  setStyle("sim-progress-bar", "width", `${pct}%`);

  updateStatusBadge(data.status);

  // Button states
  const isRunning = data.status === "running";
  setDisabled("btn-start", isRunning);
  setDisabled("btn-stop", !isRunning);
}

function updateMetricsPanel(results: Record<string, number>, metrics: Record<string, number>): void {
  setText("m-heat-flux", formatNum(metrics.Stag_Heat_Flux_Wcm2 ?? results.Heat_Flux_Wm2));
  setText("m-drag", formatNum(results.Drag_Force));
  setText("m-gload", formatNum(metrics.Decel_G));
  setText("m-surf-temp", formatNum(metrics.Surface_Temp_K));
  setText("m-knudsen", formatNum(metrics.Knudsen_Number, 6));
  setText("m-ballistic", formatNum(metrics.Ballistic_Coeff));
}

function updateValidationPanel(metrics: Record<string, number>): void {
  // IRVE-3 validation: compare simulation metrics to flight data
  setText("v-peak-heat-sim", formatNum(metrics.Stag_Heat_Flux_Wcm2));
  setValidationStatus("v-peak-heat-status", metrics.Stag_Heat_Flux_Wcm2, 13.8, 0.15);

  setText("v-total-heat-sim", "--"); // Total heat load needs integration
  setText("v-total-heat-status", "--");

  setText("v-peak-g-sim", formatNum(metrics.Decel_G));
  setValidationStatus("v-peak-g-status", metrics.Decel_G, 19.7, 0.15);

  setText("v-stag-press-sim", "--"); // Stagnation pressure from results
  setText("v-stag-press-status", "--");
}

function setValidationStatus(
  elementId: string,
  simulated: number | undefined,
  flight: number,
  toleranceFraction: number
): void {
  const el = document.getElementById(elementId);
  if (!el || simulated === undefined || simulated === 0) {
    if (el) {
      el.textContent = "--";
      el.className = "val-status";
    }
    return;
  }

  const error = Math.abs(simulated - flight) / flight;
  if (error <= toleranceFraction) {
    el.textContent = "PASS";
    el.className = "val-status pass";
  } else {
    el.textContent = "FAIL";
    el.className = "val-status fail";
  }
}

function formatNum(value: number | undefined, decimals: number = 2): string {
  if (value === undefined || value === null || isNaN(value)) return "--";
  return value.toFixed(decimals);
}

// ── History Table ──────────────────────────────────────────────────────

function updateHistoryTable(runs: HistoryEntry[]): void {
  const tbody = document.getElementById("history-body");
  if (!tbody) return;

  if (!runs || runs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No runs recorded</td></tr>';
    return;
  }

  tbody.innerHTML = runs.map(run => `
    <tr>
      <td>${escapeHtml(run.Name || "--")}</td>
      <td>${escapeHtml(run.Status || "--")}</td>
      <td>${run.Progress ? `${Math.round(parseFloat(run.Progress) * 100)}%` : "--"}</td>
      <td>${run.Mach || "--"}</td>
      <td>${run.Altitude_Km || "--"}</td>
      <td>${run.Diameter_M || "--"}</td>
      <td>${run.Heat_Flux || "--"}</td>
      <td>${run.Decel_G || "--"}</td>
      <td>${run.Survivable === "True" ? "YES" : run.Survivable === "False" ? "NO" : "--"}</td>
    </tr>
  `).join("");
}

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Configuration Form ─────────────────────────────────────────────────

function loadConfigToForm(config: ConfigData): void {
  const geo = config.geometry;
  const flt = config.flight;

  setFormVal("cfg-diameter", geo.diameter_m);
  setFormVal("cfg-angle", geo.angle_deg);
  setFormVal("cfg-nose-radius", geo.nose_radius_m);
  setFormVal("cfg-toroid-count", geo.toroid_count);
  setFormVal("cfg-toroid-radius", geo.toroid_radius_m);
  setFormVal("cfg-mass", geo.mass_kg);
  setFormVal("cfg-mach", flt.mach);
  setFormVal("cfg-altitude", flt.altitude_km);
  setFormVal("cfg-velocity", flt.velocity_ms);

  const solverEl = document.getElementById("cfg-solver") as HTMLSelectElement | null;
  const chemEl = document.getElementById("cfg-chemistry") as HTMLSelectElement | null;
  if (solverEl) solverEl.value = config.solver;
  if (chemEl) chemEl.value = config.chemistry;
  setFormVal("cfg-grid-factor", config.grid_factor);
}

function setFormVal(id: string, value: number): void {
  const el = document.getElementById(id) as HTMLInputElement | null;
  if (el) el.value = String(value);
}

function gatherConfigFromForm(): ConfigData {
  return {
    geometry: {
      diameter_m: getFormVal("cfg-diameter"),
      angle_deg: getFormVal("cfg-angle"),
      nose_radius_m: getFormVal("cfg-nose-radius"),
      toroid_count: Math.round(getFormVal("cfg-toroid-count")),
      toroid_radius_m: getFormVal("cfg-toroid-radius"),
      mass_kg: getFormVal("cfg-mass"),
    },
    flight: {
      mach: getFormVal("cfg-mach"),
      altitude_km: getFormVal("cfg-altitude"),
      velocity_ms: getFormVal("cfg-velocity"),
    },
    solver: getSelectVal("cfg-solver"),
    chemistry: getSelectVal("cfg-chemistry"),
    grid_factor: getFormVal("cfg-grid-factor"),
  };
}

function getFormVal(id: string): number {
  const el = document.getElementById(id) as HTMLInputElement | null;
  return el ? parseFloat(el.value) || 0 : 0;
}

function getSelectVal(id: string): string {
  const el = document.getElementById(id) as HTMLSelectElement | null;
  return el ? el.value : "";
}

// ── Polling Loop ───────────────────────────────────────────────────────

let pollTimer: ReturnType<typeof setInterval> | null = null;
let lastStatus: string = "stopped";

async function pollStatus(): Promise<void> {
  try {
    const status = await apiGet<SimulationStatus>("/api/status");
    updateStatusPanel(status);
    updateMetricsPanel(status.results, status.metrics);

    if (status.status !== lastStatus) {
      // On status change, also refresh history
      lastStatus = status.status;
      await refreshHistory();
    }
  } catch (err) {
    console.error("Poll error:", err);
  }
}

async function refreshHistory(): Promise<void> {
  try {
    const data = await apiGet<HistoryResponse>("/api/history");
    updateHistoryTable(data.runs);
  } catch (err) {
    console.error("History fetch error:", err);
  }
}

function startPolling(): void {
  if (pollTimer) return;
  pollTimer = setInterval(pollStatus, POLL_INTERVAL_MS);
  pollStatus(); // Immediate first poll
}

function stopPolling(): void {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ── Event Handlers ─────────────────────────────────────────────────────

function setupEventHandlers(): void {
  // Start button
  const btnStart = document.getElementById("btn-start");
  if (btnStart) {
    btnStart.addEventListener("click", async () => {
      try {
        const config = gatherConfigFromForm();
        await apiPost("/api/start", { config });
        await pollStatus();
      } catch (err) {
        console.error("Start error:", err);
      }
    });
  }

  // Stop button
  const btnStop = document.getElementById("btn-stop");
  if (btnStop) {
    btnStop.addEventListener("click", async () => {
      try {
        await apiPost("/api/stop");
        await pollStatus();
      } catch (err) {
        console.error("Stop error:", err);
      }
    });
  }

  // Config form submit
  const form = document.getElementById("config-form") as HTMLFormElement | null;
  if (form) {
    form.addEventListener("submit", async (e: Event) => {
      e.preventDefault();
      try {
        const config = gatherConfigFromForm();
        await apiPost("/api/config", config);
      } catch (err) {
        console.error("Config save error:", err);
      }
    });
  }
}

// ── Initialization ─────────────────────────────────────────────────────

async function initApp(): Promise<void> {
  initSplashScreen();
  setupEventHandlers();

  // Load initial config into form
  try {
    const config = await apiGet<ConfigData>("/api/config");
    loadConfigToForm(config);
  } catch (err) {
    console.warn("Could not load config:", err);
  }

  // Load initial history
  await refreshHistory();

  // Start polling after splash screen settles
  setTimeout(startPolling, 3000);
}

// Boot
document.addEventListener("DOMContentLoaded", initApp);
