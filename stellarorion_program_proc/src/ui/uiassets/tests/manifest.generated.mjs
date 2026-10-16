// ============================================================================
// manifest.generated.mjs — AUTO-GENERATED coverage manifest (index.html ids)  
// ============================================================================
// Every element of the Baloon Shield Maker GUI with the TEST that exercises it.
// Regenerate after editing index.html:  node gen_manifest.mjs
// Source: index.html (195 unique ids parsed)
// ============================================================================

export const ELEMENTS = [

  // ── group: (root) ──
  // #star-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "star-container", tag: "div", type: "", action: "inspect", group: "(root)" },
  // #splash <div> — TEST: exists in DOM (decorative/static node)
  { id: "splash", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: .sidebar ──
  // #side-step-1 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(1)
  { id: "side-step-1", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-2 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(2)
  { id: "side-step-2", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-3 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(3)
  { id: "side-step-3", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-4 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(4)
  { id: "side-step-4", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-5 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(5)
  { id: "side-step-5", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-6 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(6)
  { id: "side-step-6", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-7 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(7)
  { id: "side-step-7", tag: "div", type: "", action: "click", group: ".sidebar" },
  // #side-step-8 <div> — TEST: click → must not throw ; inline handler: click: jumpToPage(8)
  { id: "side-step-8", tag: "div", type: "", action: "click", group: ".sidebar" },

  // ── group: .header ──
  // #current-step-title <div> — TEST: exists in DOM (decorative/static node)
  { id: "current-step-title", tag: "div", type: "", action: "inspect", group: ".header" },
  // #step-indicator <div> — TEST: exists in DOM (decorative/static node)
  { id: "step-indicator", tag: "div", type: "", action: "inspect", group: ".header" },

  // ── group: (root) ──
  // #page-1 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-1", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-1 ──
  // #launcher-preset <select> — TEST: select new option → dispatch change → no throw ; inline handler: change: applyLauncherPreset()
  { id: "launcher-preset", tag: "select", type: "", action: "change", group: "page-1" },
  // #fairing-diameter <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "fairing-diameter", tag: "input", type: "number", action: "type", group: "page-1" },
  // #fairing-height <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "fairing-height", tag: "input", type: "number", action: "type", group: "page-1" },
  // #grid-test-steps <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "grid-test-steps", tag: "input", type: "number", action: "type", group: "page-1" },
  // #grid-test-factors <input type=text> — TEST: set value → dispatch input+change → no throw
  { id: "grid-test-factors", tag: "input", type: "text", action: "type", group: "page-1" },
  // #grid-test-headless <input type=checkbox> — TEST: click → must not throw
  { id: "grid-test-headless", tag: "input", type: "checkbox", action: "click", group: "page-1" },

  // ── group: (root) ──
  // #page-2 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-2", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-2 ──
  // #ref-diameter <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "ref-diameter", tag: "input", type: "number", action: "type", group: "page-2" },
  // #ref-angle <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "ref-angle", tag: "input", type: "number", action: "type", group: "page-2" },
  // #ref-toroids <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "ref-toroids", tag: "input", type: "number", action: "type", group: "page-2" },
  // #mass <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "mass", tag: "input", type: "number", action: "type", group: "page-2" },
  // #thickness <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "thickness", tag: "input", type: "number", action: "type", group: "page-2" },
  // #nose-radius <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "nose-radius", tag: "input", type: "number", action: "type", group: "page-2" },
  // #scallop-pts <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "scallop-pts", tag: "input", type: "number", action: "type", group: "page-2" },
  // #scallop-angle <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "scallop-angle", tag: "input", type: "number", action: "type", group: "page-2" },
  // #nose-type <select> — TEST: select new option → dispatch change → no throw
  { id: "nose-type", tag: "select", type: "", action: "change", group: "page-2" },
  // #flat-skin <input type=checkbox> — TEST: click → must not throw
  { id: "flat-skin", tag: "input", type: "checkbox", action: "click", group: "page-2" },
  // #tps-material-preset <select> — TEST: select new option → dispatch change → no throw ; inline handler: change: applyMaterialPreset()
  { id: "tps-material-preset", tag: "select", type: "", action: "change", group: "page-2" },
  // #tps-density <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "tps-density", tag: "input", type: "number", action: "type", group: "page-2" },
  // #tps-cp <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "tps-cp", tag: "input", type: "number", action: "type", group: "page-2" },
  // #tps-emissivity <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "tps-emissivity", tag: "input", type: "number", action: "type", group: "page-2" },
  // #tps-max-temp <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "tps-max-temp", tag: "input", type: "number", action: "type", group: "page-2" },
  // #enable-payload <input type=checkbox> — TEST: click → must not throw ; inline handler: change: togglePayloadInput()
  { id: "enable-payload", tag: "input", type: "checkbox", action: "click", group: "page-2" },
  // #payload-options-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "payload-options-container", tag: "div", type: "", action: "inspect", group: "page-2" },

  // ── group: payload-options-container ──
  // #default-payload <input type=checkbox> — TEST: click → must not throw ; inline handler: change: togglePayloadInput()
  { id: "default-payload", tag: "input", type: "checkbox", action: "click", group: "payload-options-container" },
  // #payload-path-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "payload-path-container", tag: "div", type: "", action: "inspect", group: "payload-options-container" },

  // ── group: payload-path-container ──
  // #payload-file <input type=text> — TEST: set value → dispatch input+change → no throw
  { id: "payload-file", tag: "input", type: "text", action: "type", group: "payload-path-container" },

  // ── group: (root) ──
  // #page-3 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-3", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-3 ──
  // #sim-status <p> — TEST: exists in DOM (decorative/static node)
  { id: "sim-status", tag: "p", type: "", action: "inspect", group: "page-3" },
  // #terminal <div> — TEST: exists in DOM (decorative/static node)
  { id: "terminal", tag: "div", type: "", action: "inspect", group: "page-3" },
  // #progress-bar <div> — TEST: exists in DOM (decorative/static node)
  { id: "progress-bar", tag: "div", type: "", action: "inspect", group: "page-3" },

  // ── group: (root) ──
  // #page-4 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-4", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-4 ──
  // #viewport <div> — TEST: exists in DOM (decorative/static node)
  { id: "viewport", tag: "div", type: "", action: "inspect", group: "page-4" },

  // ── group: (root) ──
  // #page-5 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-5", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-5 ──
  // #opt-mass <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "opt-mass", tag: "input", type: "number", action: "type", group: "page-5" },
  // #opt-d-min <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "opt-d-min", tag: "input", type: "number", action: "type", group: "page-5" },
  // #opt-d-max <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "opt-d-max", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-beta-range <input type=range> — TEST: set slider value → dispatch input+change → no throw ; inline handler: input: syncTarget('beta', 'range')
  { id: "target-beta-range", tag: "input", type: "range", action: "input", group: "page-5" },
  // #target-beta-val <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: input: syncTarget('beta', 'val')
  { id: "target-beta-val", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-beta-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "target-beta-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-heat-range <input type=range> — TEST: set slider value → dispatch input+change → no throw ; inline handler: input: syncTarget('heat', 'range')
  { id: "target-heat-range", tag: "input", type: "range", action: "input", group: "page-5" },
  // #target-heat-val <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: input: syncTarget('heat', 'val')
  { id: "target-heat-val", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-heat-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "target-heat-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-g-range <input type=range> — TEST: set slider value → dispatch input+change → no throw ; inline handler: input: syncTarget('g', 'range')
  { id: "target-g-range", tag: "input", type: "range", action: "input", group: "page-5" },
  // #target-g-val <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: input: syncTarget('g', 'val')
  { id: "target-g-val", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-g-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "target-g-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-temp-range <input type=range> — TEST: set slider value → dispatch input+change → no throw ; inline handler: input: syncTarget('temp', 'range')
  { id: "target-temp-range", tag: "input", type: "range", action: "input", group: "page-5" },
  // #target-temp-val <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: input: syncTarget('temp', 'val')
  { id: "target-temp-val", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-temp-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "target-temp-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-q-range <input type=range> — TEST: set slider value → dispatch input+change → no throw ; inline handler: input: syncTarget('q', 'range')
  { id: "target-q-range", tag: "input", type: "range", action: "input", group: "page-5" },
  // #target-q-val <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: input: syncTarget('q', 'val')
  { id: "target-q-val", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-q-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "target-q-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-hload-range <input type=range> — TEST: set slider value → dispatch input+change → no throw ; inline handler: input: syncTarget('hload', 'range')
  { id: "target-hload-range", tag: "input", type: "range", action: "input", group: "page-5" },
  // #target-hload-val <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: input: syncTarget('hload', 'val')
  { id: "target-hload-val", tag: "input", type: "number", action: "type", group: "page-5" },
  // #target-hload-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "target-hload-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-preset <select> — TEST: select new option → dispatch change → no throw ; inline handler: change: toggleMSIS()
  { id: "env-preset", tag: "select", type: "", action: "change", group: "page-5" },
  // #opt-samples <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "opt-samples", tag: "input", type: "number", action: "type", group: "page-5" },
  // #msis-panel <div> — TEST: exists in DOM (decorative/static node)
  { id: "msis-panel", tag: "div", type: "", action: "inspect", group: "page-5" },

  // ── group: msis-panel ──
  // #msis-alt <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "msis-alt", tag: "input", type: "number", action: "type", group: "msis-panel" },
  // #msis-lat <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "msis-lat", tag: "input", type: "number", action: "type", group: "msis-panel" },
  // #msis-lon <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "msis-lon", tag: "input", type: "number", action: "type", group: "msis-panel" },
  // #msis-f107 <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "msis-f107", tag: "input", type: "number", action: "type", group: "msis-panel" },
  // #msis-ap <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "msis-ap", tag: "input", type: "number", action: "type", group: "msis-panel" },

  // ── group: page-5 ──
  // #env-nrho <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-nrho", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-temp-inf <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-temp-inf", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-diameter <input type=checkbox> — TEST: click → must not throw
  { id: "v-diameter", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #v-angle <input type=checkbox> — TEST: click → must not throw
  { id: "v-angle", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-angle <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-angle", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-toroids <input type=checkbox> — TEST: click → must not throw
  { id: "v-toroids", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-toroids <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-toroids", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-nose <input type=checkbox> — TEST: click → must not throw
  { id: "v-nose", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-nose <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-nose", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-thick <input type=checkbox> — TEST: click → must not throw
  { id: "v-thick", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-thick <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-thick", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-scallop-pts <input type=checkbox> — TEST: click → must not throw
  { id: "v-scallop-pts", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-scallop-pts <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-scallop-pts", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-scallop-ang <input type=checkbox> — TEST: click → must not throw
  { id: "v-scallop-ang", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-scallop-ang <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-scallop-ang", tag: "input", type: "number", action: "type", group: "page-5" },
  // #v-mass <input type=checkbox> — TEST: click → must not throw
  { id: "v-mass", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #delta-mass <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "delta-mass", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-temp <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-temp", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-step <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-step", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-fnum <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-fnum", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-react <select> — TEST: select new option → dispatch change → no throw
  { id: "env-react", tag: "select", type: "", action: "change", group: "page-5" },
  // #env-run <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: change: onSimStepsChange()
  { id: "env-run", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-grid-factor <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-grid-factor", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-vstream <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-vstream", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-duration <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-duration", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-viscous-model <select> — TEST: select new option → dispatch change → no throw
  { id: "env-viscous-model", tag: "select", type: "", action: "change", group: "page-5" },
  // #viscous-warning <div> — TEST: exists in DOM (decorative/static node)
  { id: "viscous-warning", tag: "div", type: "", action: "inspect", group: "page-5" },
  // #env-chem-mode <select> — TEST: select new option → dispatch change → no throw
  { id: "env-chem-mode", tag: "select", type: "", action: "change", group: "page-5" },
  // #env-steady-state <input type=checkbox> — TEST: click → must not throw ; inline handler: change: onSteadyStateChange()
  { id: "env-steady-state", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #pinn-accel <input type=checkbox> — TEST: click → must not throw ; inline handler: change: onPinnAccelChange()
  { id: "pinn-accel", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #pinn-fidelity-warning <div> — TEST: exists in DOM (decorative/static node)
  { id: "pinn-fidelity-warning", tag: "div", type: "", action: "inspect", group: "page-5" },
  // #force-pinn <input type=checkbox> — TEST: click → must not throw ; inline handler: change: onSimStepsChange()
  { id: "force-pinn", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #env-steady-tol <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "env-steady-tol", tag: "input", type: "number", action: "type", group: "page-5" },
  // #solver-backend <select> — TEST: select new option → dispatch change → no throw ; inline handler: change: onBackendChange()
  { id: "solver-backend", tag: "select", type: "", action: "change", group: "page-5" },
  // #vehicle-type <select> — TEST: select new option → dispatch change → no throw
  { id: "vehicle-type", tag: "select", type: "", action: "change", group: "page-5" },
  // #sparta-gpu-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "sparta-gpu-container", tag: "div", type: "", action: "inspect", group: "page-5" },

  // ── group: sparta-gpu-container ──
  // #sparta-gpu <input type=checkbox> — TEST: click → must not throw
  { id: "sparta-gpu", tag: "input", type: "checkbox", action: "click", group: "sparta-gpu-container" },

  // ── group: page-5 ──
  // #verbose-log <input type=checkbox> — TEST: click → must not throw
  { id: "verbose-log", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #sim-cores <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "sim-cores", tag: "input", type: "number", action: "type", group: "page-5" },
  // #grid-test-steps <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "grid-test-steps", tag: "input", type: "number", action: "type", group: "page-5" },
  // #grid-test-factors <input type=text> — TEST: set value → dispatch input+change → no throw
  { id: "grid-test-factors", tag: "input", type: "text", action: "type", group: "page-5" },
  // #grid-test-headless <input type=checkbox> — TEST: click → must not throw
  { id: "grid-test-headless", tag: "input", type: "checkbox", action: "click", group: "page-5" },
  // #btn-test-readiness <button> — TEST: click → must not throw ; inline handler: click: testReadiness()
  { id: "btn-test-readiness", tag: "button", type: "", action: "click", group: "page-5" },
  // #btn-run-test <button> — TEST: click → must not throw ; inline handler: click: runIntegrationTest()
  { id: "btn-run-test", tag: "button", type: "", action: "click", group: "page-5" },
  // #test-readiness-status <div> — TEST: exists in DOM (decorative/static node)
  { id: "test-readiness-status", tag: "div", type: "", action: "inspect", group: "page-5" },
  // #python-install-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "python-install-container", tag: "div", type: "", action: "inspect", group: "page-5" },
  // #remote-view-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "remote-view-container", tag: "div", type: "", action: "inspect", group: "page-5" },

  // ── group: remote-view-container ──
  // #remote-screen-img <img> — TEST: exists in DOM (decorative/static node)
  { id: "remote-screen-img", tag: "img", type: "", action: "inspect", group: "remote-view-container" },
  // #remote-screen-placeholder <div> — TEST: exists in DOM (decorative/static node)
  { id: "remote-screen-placeholder", tag: "div", type: "", action: "inspect", group: "remote-view-container" },

  // ── group: page-5 ──
  // #test-verbose-logs-container <div> — TEST: exists in DOM (decorative/static node)
  { id: "test-verbose-logs-container", tag: "div", type: "", action: "inspect", group: "page-5" },

  // ── group: test-verbose-logs-container ──
  // #test-verbose-logs <div> — TEST: exists in DOM (decorative/static node)
  { id: "test-verbose-logs", tag: "div", type: "", action: "inspect", group: "test-verbose-logs-container" },

  // ── group: page-5 ──
  // #remote-fields <div> — TEST: exists in DOM (decorative/static node)
  { id: "remote-fields", tag: "div", type: "", action: "inspect", group: "page-5" },

  // ── group: remote-fields ──
  // #ssh-host <input type=text> — TEST: set value → dispatch input+change → no throw
  { id: "ssh-host", tag: "input", type: "text", action: "type", group: "remote-fields" },
  // #ssh-user <input type=text> — TEST: set value → dispatch input+change → no throw
  { id: "ssh-user", tag: "input", type: "text", action: "type", group: "remote-fields" },
  // #ssh-pass <input type=password> — TEST: set value → dispatch input+change → no throw
  { id: "ssh-pass", tag: "input", type: "password", action: "type", group: "remote-fields" },
  // #ssh-key <input type=text> — TEST: set value → dispatch input+change → no throw
  { id: "ssh-key", tag: "input", type: "text", action: "type", group: "remote-fields" },
  // #solver-dim <select> — TEST: select new option → dispatch change → no throw
  { id: "solver-dim", tag: "select", type: "", action: "change", group: "remote-fields" },
  // #solver-bl-layers <input type=number> — TEST: set value → dispatch input+change → no throw
  { id: "solver-bl-layers", tag: "input", type: "number", action: "type", group: "remote-fields" },
  // #solver-gpu <input type=checkbox> — TEST: click → must not throw
  { id: "solver-gpu", tag: "input", type: "checkbox", action: "click", group: "remote-fields" },
  // #ssh-setup-cmd <code> — TEST: exists in DOM (decorative/static node)
  { id: "ssh-setup-cmd", tag: "code", type: "", action: "inspect", group: "remote-fields" },

  // ── group: page-5 ──
  // #env-domain-type <select> — TEST: select new option → dispatch change → no throw ; inline handler: change: refreshDomainPreview()
  { id: "env-domain-type", tag: "select", type: "", action: "change", group: "page-5" },
  // #env-xmin <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: change: refreshDomainPreview()
  { id: "env-xmin", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-xmax <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: change: refreshDomainPreview()
  { id: "env-xmax", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-ymax <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: change: refreshDomainPreview()
  { id: "env-ymax", tag: "input", type: "number", action: "type", group: "page-5" },
  // #env-zthick <input type=number> — TEST: set value → dispatch input+change → no throw ; inline handler: change: refreshDomainPreview()
  { id: "env-zthick", tag: "input", type: "number", action: "type", group: "page-5" },
  // #domain-live-preview <img> — TEST: exists in DOM (decorative/static node)
  { id: "domain-live-preview", tag: "img", type: "", action: "inspect", group: "page-5" },

  // ── group: (root) ──
  // #page-6 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-6", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-6 ──
  // #summary-content <div> — TEST: exists in DOM (decorative/static node)
  { id: "summary-content", tag: "div", type: "", action: "inspect", group: "page-6" },
  // #domain-preview-img <img> — TEST: exists in DOM (decorative/static node)
  { id: "domain-preview-img", tag: "img", type: "", action: "inspect", group: "page-6" },

  // ── group: (root) ──
  // #page-7 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-7", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-7 ──
  // #opt-terminal <div> — TEST: exists in DOM (decorative/static node)
  { id: "opt-terminal", tag: "div", type: "", action: "inspect", group: "page-7" },
  // #opt-progress-bar <div> — TEST: exists in DOM (decorative/static node)
  { id: "opt-progress-bar", tag: "div", type: "", action: "inspect", group: "page-7" },

  // ── group: (root) ──
  // #page-8 <div> — TEST: exists in DOM (decorative/static node)
  { id: "page-8", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: page-8 ──
  // #res-ref <div> — TEST: exists in DOM (decorative/static node)
  { id: "res-ref", tag: "div", type: "", action: "inspect", group: "page-8" },
  // #res-opt <div> — TEST: exists in DOM (decorative/static node)
  { id: "res-opt", tag: "div", type: "", action: "inspect", group: "page-8" },
  // #vid-simulation <video> — TEST: exists in DOM (decorative/static node)
  { id: "vid-simulation", tag: "video", type: "", action: "inspect", group: "page-8" },
  // #img-conv-aero <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-conv-aero", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-conv-thermal <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-conv-thermal", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-conv-mission <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-conv-mission", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-thermal <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-thermal", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-pressure <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-pressure", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-3d-temp <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-3d-temp", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-3d-velocity <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-3d-velocity", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-3d-mach <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-3d-mach", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-stag <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-stag", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-knudsen <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-knudsen", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-residence <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-residence", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #img-scallop-temp <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-scallop-temp", tag: "img", type: "", action: "inspect", group: "page-8" },
  // #species-grid <div> — TEST: exists in DOM (decorative/static node)
  { id: "species-grid", tag: "div", type: "", action: "inspect", group: "page-8" },

  // ── group: species-grid ──
  // #img-species-N2 <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-species-N2", tag: "img", type: "", action: "inspect", group: "species-grid" },
  // #img-species-O2 <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-species-O2", tag: "img", type: "", action: "inspect", group: "species-grid" },
  // #img-species-NO <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-species-NO", tag: "img", type: "", action: "inspect", group: "species-grid" },
  // #img-species-N <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-species-N", tag: "img", type: "", action: "inspect", group: "species-grid" },
  // #img-species-O <img> — TEST: exists in DOM (decorative/static node)
  { id: "img-species-O", tag: "img", type: "", action: "inspect", group: "species-grid" },

  // ── group: (root) ──
  // #btn-prev <button> — TEST: click → must not throw ; inline handler: click: changePage(-1)
  { id: "btn-prev", tag: "button", type: "", action: "click", group: "(root)" },
  // #btn-next <button> — TEST: click → must not throw ; inline handler: click: changePage(1)
  { id: "btn-next", tag: "button", type: "", action: "click", group: "(root)" },
  // #manual-overlay <div> — TEST: exists in DOM (decorative/static node)
  { id: "manual-overlay", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: .manual-header ──
  // #manual-search <input type=text> — TEST: set value → dispatch input+change → no throw ; inline handler: input: searchManual()
  { id: "manual-search", tag: "input", type: "text", action: "type", group: ".manual-header" },
  // #search-count <span> — TEST: exists in DOM (decorative/static node)
  { id: "search-count", tag: "span", type: "", action: "inspect", group: ".manual-header" },

  // ── group: manual-overlay ──
  // #manual-body <div> — TEST: exists in DOM (decorative/static node)
  { id: "manual-body", tag: "div", type: "", action: "inspect", group: "manual-overlay" },

  // ── group: manual-body ──
  // #manual-sidebar <div> — TEST: exists in DOM (decorative/static node)
  { id: "manual-sidebar", tag: "div", type: "", action: "inspect", group: "manual-body" },

  // ── group: manual-sidebar ──
  // #manual-toc <div> — TEST: exists in DOM (decorative/static node)
  { id: "manual-toc", tag: "div", type: "", action: "inspect", group: "manual-sidebar" },

  // ── group: manual-body ──
  // #manual-loader <div> — TEST: exists in DOM (decorative/static node)
  { id: "manual-loader", tag: "div", type: "", action: "inspect", group: "manual-body" },
  // #manual-text <div> — TEST: exists in DOM (decorative/static node)
  { id: "manual-text", tag: "div", type: "", action: "inspect", group: "manual-body" },

  // ── group: (root) ──
  // #history-modal <div> — TEST: exists in DOM (decorative/static node)
  { id: "history-modal", tag: "div", type: "", action: "inspect", group: "(root)" },

  // ── group: history-modal ──
  // #history-list-panel <div> — TEST: exists in DOM (decorative/static node)
  { id: "history-list-panel", tag: "div", type: "", action: "inspect", group: "history-modal" },

  // ── group: history-list-panel ──
  // #history-list <div> — TEST: exists in DOM (decorative/static node)
  { id: "history-list", tag: "div", type: "", action: "inspect", group: "history-list-panel" },

  // ── group: history-modal ──
  // #history-details-panel <div> — TEST: exists in DOM (decorative/static node)
  { id: "history-details-panel", tag: "div", type: "", action: "inspect", group: "history-modal" },

  // ── group: history-details-panel ──
  // #history-details-empty <div> — TEST: exists in DOM (decorative/static node)
  { id: "history-details-empty", tag: "div", type: "", action: "inspect", group: "history-details-panel" },
  // #history-details-content <div> — TEST: exists in DOM (decorative/static node)
  { id: "history-details-content", tag: "div", type: "", action: "inspect", group: "history-details-panel" },

  // ── group: history-details-content ──
  // #hist-run-name <h3> — TEST: exists in DOM (decorative/static node)
  { id: "hist-run-name", tag: "h3", type: "", action: "inspect", group: "history-details-content" },
  // #hist-run-meta <div> — TEST: exists in DOM (decorative/static node)
  { id: "hist-run-meta", tag: "div", type: "", action: "inspect", group: "history-details-content" },
  // #hist-run-status <div> — TEST: exists in DOM (decorative/static node)
  { id: "hist-run-status", tag: "div", type: "", action: "inspect", group: "history-details-content" },
  // #hist-run-goal <strong> — TEST: exists in DOM (decorative/static node)
  { id: "hist-run-goal", tag: "strong", type: "", action: "inspect", group: "history-details-content" },
  // #hist-run-samples <strong> — TEST: exists in DOM (decorative/static node)
  { id: "hist-run-samples", tag: "strong", type: "", action: "inspect", group: "history-details-content" },
  // #hist-run-best <strong> — TEST: exists in DOM (decorative/static node)
  { id: "hist-run-best", tag: "strong", type: "", action: "inspect", group: "history-details-content" },
  // #hist-samples-list <div> — TEST: exists in DOM (decorative/static node)
  { id: "hist-samples-list", tag: "div", type: "", action: "inspect", group: "history-details-content" },
  // #btn-resume-run <button> — TEST: click → must not throw ; inline handler: click: resumeRun()
  { id: "btn-resume-run", tag: "button", type: "", action: "click", group: "history-details-content" },
  // #btn-delete-run <button> — TEST: click → must not throw ; inline handler: click: deleteRun()
  { id: "btn-delete-run", tag: "button", type: "", action: "click", group: "history-details-content" },
];
