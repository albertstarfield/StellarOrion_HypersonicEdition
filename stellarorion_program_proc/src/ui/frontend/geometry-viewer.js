/*
 * geometry-viewer.js — Live 3D HIAD geometry viewer (classic script, self-contained)
 * =================================================================================
 * Renders the SPARTA surf profile served by the sidecar UI as a rotating
 * surface-of-revolution on a <canvas>. Polls /api/geometry/latest every 2 s,
 * lists archived snapshots in a <select>, and supports "Save Snapshot" (POST).
 *
 * AXIOMS:
 *   A1: The surf profile is axisymmetric: each [axial_x, radial_y] pair defines
 *       a circle of radius radial_y at axial station axial_x.
 *   A2: The sidecar server is reachable at the same origin as this document.
 *   A3: main.js (compiled from main.ts) may be ABSENT — this script must run
 *       standalone, so it defines its own fetch helpers (no cross-file deps).
 * THEORIES:
 *   T1: A surface of revolution is the union of circles swept about the axial
 *       axis; a wireframe of meridians + latitudinal rings conveys the shape.
 *   T2: Weak-perspective projection + depth shading yields readable 3D without
 *       a WebGL dependency (offline-robust per Murphy's Law).
 * CITATIONS:
 *   - Plimpton & Gallis, "SPARTA DSMC User Guide", surf file format.
 *   - Murphy's Law: any network/file/parse failure degrades to a safe state.
 * SAFETY FALLBACK: empty points -> "no geometry" message; fetch errors ->
 *   console.error (verbose) + status text; never throws to the page.
 */

(function () {
  "use strict";

  // ── Local fetch helpers (self-contained; do NOT rely on main.ts) ──────────

  /**
   * GET JSON from the sidecar API.
   * AXIOMS: A1 url is same-origin relative path. THEORIES: T1 non-2xx -> throw.
   * SAFETY: rejects on network error or bad JSON (caller handles).
   */
  async function apiGet(path) {
    const resp = await fetch(path, { method: "GET", cache: "no-store" });
    if (!resp.ok) {
      throw new Error(`GET ${path} -> HTTP ${resp.status}`);
    }
    return await resp.json();
  }

  /**
   * POST JSON to the sidecar API.
   * AXIOMS: A1 body is a plain object. SAFETY: rejects on non-2xx.
   */
  async function apiPost(path, body) {
    const resp = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    let data = null;
    try {
      data = await resp.json();
    } catch (e) {
      data = null;
    }
    if (!resp.ok) {
      const msg = (data && (data.error || data.detail)) || `HTTP ${resp.status}`;
      throw new Error(`POST ${path} -> ${msg}`);
    }
    return data;
  }

  // ── Module state ───────────────────────────────────────────────────────

  const STATE = {
    canvas: null,
    ctx: null,
    select: null,
    saveBtn: null,
    statusEl: null,
    model: null, // { model:[[{x,y,z}]], seg, n }
    mode: "latest", // "latest" | snapshot id
    yaw: 0.6,
    pitch: 0.5,
    dragging: false,
    lastX: 0,
    lastY: 0,
    rafId: 0,
    dpr: 1,
    unit: 1,
  };

  // ── Geometry build ─────────────────────────────────────────────────────

  /**
   * Build a normalized surface-of-revolution model from [axial, radial] points.
   * AXIOMS: A1 input is array of [x, y]; y >= 0 (radius). THEORIES: T1 sort by
   * x; center on mid-x; scale so half the span maps to ~1; sweep SEG circles.
   * SAFETY: <2 points -> null (caller shows "no geometry").
   */
  function buildModel(points) {
    if (!Array.isArray(points) || points.length < 2) return null;
    const pts = points
      .slice()
      .filter((p) => Array.isArray(p) && p.length >= 2 && isFinite(p[0]) && isFinite(p[1]))
      .sort((a, b) => a[0] - b[0]);
    if (pts.length < 2) return null;

    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => Math.abs(p[1]));
    const minX = Math.min.apply(null, xs);
    const maxX = Math.max.apply(null, xs);
    const maxR = Math.max.apply(null, ys.concat([1e-9]));
    const midX = (minX + maxX) / 2;
    const span = Math.max(maxX - minX, 2 * maxR, 1e-9);
    const s = 1 / (span / 2); // half-span -> 1
    const SEG = 32;

    const model = new Array(pts.length);
    for (let i = 0; i < pts.length; i++) {
      const X = (pts[i][0] - midX) * s;
      const Yr = pts[i][1] * s;
      const ring = new Array(SEG);
      for (let j = 0; j < SEG; j++) {
        const th = (j / SEG) * Math.PI * 2;
        ring[j] = { x: X, y: Yr * Math.cos(th), z: Yr * Math.sin(th) };
      }
      model[i] = ring;
    }
    return { model: model, seg: SEG, n: pts.length };
  }

  // ── Projection & drawing ──────────────────────────────────────────────

  /**
   * Project a model point to screen space with weak perspective.
   * AXIOMS: A1 yaw rotates about Y (vertical), pitch about X. THEORIES: T2
   * focal length 4 keeps perspective mild; closer (smaller z) -> brighter.
   * Returns { sx, sy, z } where z in [-1,1] is depth for shading.
   */
  function project(p) {
    // pitch about X axis
    const cy = Math.cos(STATE.pitch),
      sy = Math.sin(STATE.pitch);
    const y1 = p.y * cy - p.z * sy;
    const z1 = p.y * sy + p.z * cy;
    // yaw about Y axis
    const cyw = Math.cos(STATE.yaw),
      syw = Math.sin(STATE.yaw);
    const x2 = p.x * cyw + z1 * syw;
    const z2 = -p.x * syw + z1 * cyw;

    const focal = 4;
    const f = focal / (focal + z2); // mild perspective, z2 in ~[-1,1]
    const sx = STATE.canvas.clientWidth / 2 + x2 * STATE.unit * f;
    const sy = STATE.canvas.clientHeight / 2 - y1 * STATE.unit * f;
    return { sx: sx, sy: sy, z: z2 };
  }

  /** Map depth z in [-1,1] to an accent-cyan stroke with depth shading. */
  function shade(z) {
    const a = Math.max(0.22, Math.min(1, 0.6 - z * 0.35));
    return "rgba(0, 212, 255, " + a.toFixed(3) + ")";
  }

  /** Draw the wireframe for the current frame. */
  function drawModel() {
    const ctx = STATE.ctx;
    const m = STATE.model;
    if (!ctx || !m) return;
    const proj = new Array(m.n);
    for (let i = 0; i < m.n; i++) {
      const ring = new Array(m.seg);
      for (let j = 0; j < m.seg; j++) ring[j] = project(m.model[i][j]);
      proj[i] = ring;
    }

    ctx.lineWidth = 1;
    // Meridians (constant angle)
    for (let j = 0; j < m.seg; j++) {
      ctx.beginPath();
      for (let i = 0; i < m.n; i++) {
        const p = proj[i][j];
        if (i === 0) ctx.moveTo(p.sx, p.sy);
        else ctx.lineTo(p.sx, p.sy);
      }
      ctx.strokeStyle = shade(proj[0][j].z);
      ctx.stroke();
    }
    // Latitudinal rings (every ~24th station) for 3D readability
    const step = Math.max(1, Math.floor(m.n / 24));
    for (let i = 0; i < m.n; i += step) {
      ctx.beginPath();
      for (let j = 0; j <= m.seg; j++) {
        const p = proj[i][j % m.seg];
        if (j === 0) ctx.moveTo(p.sx, p.sy);
        else ctx.lineTo(p.sx, p.sy);
      }
      ctx.strokeStyle = shade(proj[i][0].z);
      ctx.stroke();
    }
  }

  /** Clear canvas and render. */
  function render() {
    const ctx = STATE.ctx;
    if (!ctx) return;
    const w = STATE.canvas.clientWidth;
    const h = STATE.canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);

    if (!STATE.model) {
      ctx.fillStyle = "#556677";
      ctx.font = "13px " + getComputedStyle(document.body).fontFamily;
      ctx.textAlign = "center";
      ctx.fillText("No HIAD geometry available", w / 2, h / 2);
      ctx.textAlign = "start";
      return;
    }
    drawModel();
  }

  /** Animation loop: auto-spin when not dragging. */
  function loop() {
    if (!STATE.dragging) STATE.yaw += 0.01;
    render();
    STATE.rafId = requestAnimationFrame(loop);
  }

  // ── Canvas sizing ──────────────────────────────────────────────────────

  function resizeCanvas() {
    if (!STATE.canvas) return;
    const dpr = window.devicePixelRatio || 1;
    STATE.dpr = dpr;
    const w = STATE.canvas.clientWidth;
    const h = STATE.canvas.clientHeight;
    STATE.canvas.width = Math.max(1, Math.floor(w * dpr));
    STATE.canvas.height = Math.max(1, Math.floor(h * dpr));
    STATE.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    STATE.unit = Math.min(w, h) * 0.4;
  }

  // ── Status helper ──────────────────────────────────────────────────────

  function showStatus(msg, isError) {
    if (STATE.statusEl) {
      STATE.statusEl.textContent = msg;
      STATE.statusEl.style.color = isError ? "#ef4444" : "#8899aa";
    }
    if (isError) console.error("[geometry-viewer] " + msg);
    else console.log("[geometry-viewer] " + msg);
  }

  // ── Data flow ──────────────────────────────────────────────────────────

  function setGeometry(data) {
    if (!data || !Array.isArray(data.points) || data.points.length < 2) {
      STATE.model = null;
      showStatus("No HIAD geometry available", false);
      return;
    }
    STATE.model = buildModel(data.points);
    const info =
      (data.id ? data.id + " · " : "") +
      data.points.length +
      " pts" +
      (data.axial_max ? " · ⌀≈" + (2 * data.radial_max).toExponential(2) + " m" : "");
    showStatus(info, false);
  }

  async function fetchLatest() {
    try {
      const data = await apiGet("/api/geometry/latest");
      if (STATE.mode === "latest") setGeometry(data);
    } catch (e) {
      showStatus("Live geometry poll failed: " + e.message, true);
    }
  }

  async function fetchSnapshot(id) {
    try {
      const data = await apiGet("/api/geometry/snapshot?id=" + encodeURIComponent(id));
      setGeometry(data);
      showStatus("Snapshot: " + (data.id || id), false);
    } catch (e) {
      showStatus("Snapshot load failed: " + e.message, true);
    }
  }

  async function fetchHistory() {
    try {
      const data = await apiGet("/api/geometry/history");
      const runs = (data && data.runs) || [];
      const sel = STATE.select;
      if (!sel) return;
      const current = sel.value;
      sel.innerHTML = "";
      const live = document.createElement("option");
      live.value = "__latest__";
      live.textContent = "● Latest (live)";
      sel.appendChild(live);
      runs.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.id;
        const t = new Date((r.mtime || 0) * 1000);
        opt.textContent = r.id + "  (" + (r.count || 0) + " pts" + (isFinite(t.getTime()) ? " · " + t.toISOString().slice(0, 19).replace("T", " ") : "") + ")";
        sel.appendChild(opt);
      });
      // Restore selection if still present, else fall back to latest
      const stillThere = Array.prototype.some.call(sel.options, (o) => o.value === current);
      sel.value = stillThere ? current : "__latest__";
    } catch (e) {
      showStatus("History load failed: " + e.message, true);
    }
  }

  async function saveSnapshot() {
    if (!STATE.saveBtn) return;
    STATE.saveBtn.disabled = true;
    try {
      const runNameEl = document.getElementById("sim-run-name");
      const runName = runNameEl ? runNameEl.textContent.trim() : "manual";
      const data = await apiPost("/api/geometry/save", { run_name: runName || "manual" });
      showStatus("Saved snapshot: " + (data.id || "ok"), false);
      await fetchHistory();
    } catch (e) {
      showStatus("Save failed: " + e.message, true);
    } finally {
      STATE.saveBtn.disabled = false;
    }
  }

  // ── Interaction ────────────────────────────────────────────────────────

  function bindEvents() {
    if (STATE.select) {
      STATE.select.addEventListener("change", () => {
        const v = STATE.select.value;
        if (v === "__latest__") {
          STATE.mode = "latest";
          fetchLatest();
        } else {
          STATE.mode = v;
          fetchSnapshot(v);
        }
      });
    }
    if (STATE.saveBtn) {
      STATE.saveBtn.addEventListener("click", saveSnapshot);
    }
    const c = STATE.canvas;
    if (c) {
      c.addEventListener("mousedown", (e) => {
        STATE.dragging = true;
        STATE.lastX = e.clientX;
        STATE.lastY = e.clientY;
      });
      window.addEventListener("mouseup", () => (STATE.dragging = false));
      window.addEventListener("mousemove", (e) => {
        if (!STATE.dragging) return;
        STATE.yaw += (e.clientX - STATE.lastX) * 0.01;
        STATE.pitch += (e.clientY - STATE.lastY) * 0.01;
        STATE.pitch = Math.max(-1.4, Math.min(1.4, STATE.pitch));
        STATE.lastX = e.clientX;
        STATE.lastY = e.clientY;
      });
    }
    window.addEventListener("resize", resizeCanvas);
  }

  // ── Init ───────────────────────────────────────────────────────────────

  function init() {
    STATE.canvas = document.getElementById("geo-canvas");
    STATE.select = document.getElementById("geo-history");
    STATE.saveBtn = document.getElementById("geo-save");
    STATE.statusEl = document.getElementById("geo-status");
    if (!STATE.canvas) {
      console.error("[geometry-viewer] #geo-canvas not found; viewer disabled.");
      return;
    }
    STATE.ctx = STATE.canvas.getContext("2d");
    if (!STATE.ctx) {
      showStatus("Canvas 2D context unavailable", true);
      return;
    }
    resizeCanvas();
    bindEvents();
    loop(); // start render loop
    fetchLatest();
    fetchHistory();
    setInterval(() => {
      if (STATE.mode === "latest") fetchLatest();
    }, 2000);
    console.log("[geometry-viewer] initialized.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
