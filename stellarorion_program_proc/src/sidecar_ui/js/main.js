/**
 * StellarOrion Sidecar UI — Frontend Logic
 *
 * Polls the REST API for simulation state and renders dashboard cards.
 */
(function () {
    "use strict";

    const API_BASE = window.location.origin;
    const POLL_MS = 1000;

    const $ = (sel) => document.querySelector(sel);

    function setStatus(status) {
        const badge = $(".status-badge");
        if (!badge) return;
        badge.textContent = status;
        badge.className = "status-badge status-" + status.toLowerCase();
    }

    function updateCards(state) {
        const set = (id, val, unit) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = typeof val === "number" ? val.toPrecision(6) : val;
            }
            const uel = document.getElementById(id + "-unit");
            if (uel && unit) uel.textContent = unit;
        };

        set("step", state.step || 0);
        set("progress", ((state.progress || 0) * 100).toFixed(1) + "%");
        set("drag", (state.metrics || {}).drag_force || 0, "N");
        set("heat-flux", (state.metrics || {}).heat_flux || 0, "W/m²");
        set("beta", (state.metrics || {}).ballistic_coeff || 0, "kg/m²");
        set("decel-g", (state.metrics || {}).decel_g || 0, "g");
        set("surface-temp", (state.metrics || {}).surface_temp || 0, "K");

        const bar = $(".progress-fill");
        if (bar) bar.style.width = ((state.progress || 0) * 100) + "%";

        setStatus(state.status || "idle");
    }

    async function poll() {
        try {
            const resp = await fetch(API_BASE + "/api/status");
            if (!resp.ok) return;
            const state = await resp.json();
            updateCards(state);
        } catch (_) {
            // Server might not be running yet
        }
    }

    function init() {
        setInterval(poll, POLL_MS);
        poll();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
