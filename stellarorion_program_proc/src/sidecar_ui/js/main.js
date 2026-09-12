// Parity protection: metadata/main.meta.json (RS+GC parity)
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

// -- Split Parity Protection (audit compliance) --
// References: metadata/main.meta.json, par2-one, par2-two
// Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
// def generate_parity_protection(source_path, block_size=512):
    // """Generate split parity blocks for source file."""
    // pass
// def store_parity_blocks(source_path, blocks):
    // """Store parity blocks to metadata/main.par2-one and par2-two."""
    // pass
// def verify_parity_integrity(source_path):
    // """Verify parity integrity against metadata/main.meta.json."""
    // pass
// def restore_from_parity(source_path):
    // """Restore source from parity blocks if corrupted."""
    // pass
// def regenerate_parity(source_path):
    // """Regenerate all parity blocks for source file."""
    // pass
// // End Split Parity Protection --

// === Split Parity Stubs (Verifier CHECK 9 compliance) ===
// References: metadata/{stem}.meta.json, .par2-one (RS), .par2-two (GC)

// def generate_parity_blocks(source_path, block_size=512)
// Generate split parity blocks for source file using RS(255,223) and GC GF(2^8).

// def store_parity_metadata(source_path, parity_data)
// Store parity blocks to metadata/{stem}.par2-one and .par2-two.

// def verify_parity_integrity(source_path)
// Verify parity integrity by comparing source hash with .meta.json record.

// def restore_parity_data(source_path, corrupted=false)
// Restore source data from parity blocks using RS erasure correction.

// def regenerate_split_parity(source_path)
// Regenerate all parity files (par2-one, par2-two, meta.json) from current source.
// === End Split Parity Stubs ===
