---
session: ses_fc1c
updated: 2026-08-26T13:38:47.399Z
---

# Session Summary

## Goal
Produce an exhaustive OLD-vs-NEW GUI comparison report (Sections A–F: old feature inventory, new feature inventory, capability parity table, broken-assets table, backend/API parity gaps, prioritized remediation) for `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition`, as a research-only deliverable with file:line evidence.

## Constraints & Preferences
- RESEARCH-ONLY: read/grep/glob/bash-for-reading allowed; NO file modifications.
- Fixed return format Sections A–F; be exhaustive with paths + line numbers.
- Pre-established context must not be re-derived (old GUI = gui_launcher.py/pywebview + web/; new GUI = stellarorion_program_proc/run.py --gui → src/ui/sidecar_ui.py stdlib http.server; KNOWN GAP #1 = frontend requests main.js but only main.ts exists).
- Report is the final deliverable for the goal.

## Progress
### Done
- [x] Resolved tree layout confusion: NO project-root `src/`; new GUI lives under `stellarorion_program_proc/src/` (ui/frontend, ui/sidecar_ui.py, python/sidecar_server.py, sidecar_ui/, simulation_engine/*.adb).
- [x] Line counts captured: web/index.html=1481, web/script.js=1697, web/style.css=1135, StellarOrionEngineMach5Up.py=5543, gui_launcher.py=176, stellarorion_program_proc/src/ui/sidecar_ui.py=957.
- [x] Read web/index.html FULLY: splash (#splash "STELLAR ORION", 1500ms fade script.js:7-13), aurora bg + 50-star field (script.js:40-53), 8-step sidebar wizard (side-step-N, jumpToPage), CDNs katex@0.16.11+auto-render/mermaid/marked (index.html:11-15), Google Fonts Inter/Outfit/Fira Code (line 10), variability checkboxes v-diameter/v-angle/v-toroids/v-nose/v-thick/v-scallop-pts/v-scallop-ang/v-mass with ±delta inputs (script.js:26-37; e.g. delta-toroids default 3 at index.html:754), three.js STL viewer (model.stl via get_model_paths), domain_preview.png cache-bust ?t= (script.js:1025-1026), remote_view.png remote capture, btn-run-test flow branching sparta→run_sparta_integration_test else ssh/solver params {env_cores:2, solver_bl_layers:5, viscous_model:"laminar"}→run_integration_test (script.js:851-891), logReadiness() console, history-details-panel with hist-run-name/meta/status + param-grid (index.html:1434+).
- [x] Enumerated backend surface: `class Api` at StellarOrionEngineMach5Up.py:150; HistoryManager class L23-128 (db_path="optimization_history.db"; create_run:67, add_sample:88, get_all_runs:98, get_run:105, delete_run:120, upsert_draft:127). Api methods anchored: __init__:158, _journal_intention:179, calculate_shield_mass:197(static), calculate_shield_mass_analytical:256, get_irve_baseline_results_static:336/:450, get_irve_citation:455, get_manual_content:463, get_references_content:492, get_optimization_history:503, get_run_details:506, delete_run:509, autosave_draft:513, resume_run_from_history:518, has_nvidia_gpu:530, detect_nvidia_gpu:541, _get_python_exec:548, _get_git_hash:568, _compute_surf_y_max:576, _compute_surf_centroid:620, _get_viz_params:710, set_window:762, get_local_user:765, log_to_gui:768, log_to_readiness:786, request_domain_preview:795, generate_cad_preview:805, get_model_paths:857, parse_sparta_results:870, calculate_flight_metrics:983, get_msis_atmosphere:1192, get_atmosphere_data:1227, get_environment_from_mach_alt:1250, get_chemistry_data:1289, generate_surf_react_script:1316, _safe_copy:1335, generate_sparta_script:1341, run_remote_pyfluent:1549, run_nose_comparison:4491, build_sparta_image:4573, run_sparta_integration_test:4599, run_openfoam_simulation:4648, run_hybrid_thermal_solver:4878, generate_openfoam_solid_case:5031, generate_openfoam_case:5158, _write_of_dict:5409, parse_openfoam_results:5424, _is_gpu_available:5460, run_manim_demo:5468, open_demo_video:5533.
- [x] Asset IO mapped in engine: sqlite optimization_history.db; journal append (L189); domain_preview.png written at runtime to web/assets/plots/ (L799, L843); HIAD_custom.stl→copied to web/assets/model.stl (L861-867); air.surf_react write (L2107); in.hiad write (L2115); config write (L1650); .stl/.step search (L1615); results JSON read (L1679). Engine JS-injected plot refresh list (~L3413-3424): thermal_map, pressure_map, convergence_{aero,thermal,mission}_smooth, upscaled_3d_{temp,velocity,mach}, stagnation_graph, knudsen_map, species_{N,O,N2,O2,NO}_map.
- [x] Read new frontend partially: splash-overlay INC-SPLASH-002 with inline SVG logo (index.html:15-33); main.ts types SimulationStatus{status,run_name,progress,results,metrics,window_title,version}, HistoryEntry{Name,Status,Progress,Mach,Altitude_Km,Diameter_M,Heat_Flux,Decel_G,Survivable}, ConfigData{geometry{diameter_m,angle_deg,nose_radius_m,toroid_count,toroid_radius_m,mass_kg}, flight{mach,altitude_km,velocity_ms}, solver, chemistry, grid_factor}; API_BASE="" L16, POLL_INTERVAL_MS=2000 L17, fetch GET helper L93 / POST helper L101.
- [x] Mapped sidecar_ui.py REST surface: FRONTEND_DIR=L38; GET routes L321-325 (/api/status→_handle_status:370, /api/results→:377, /api/history→:385, /api/config→:390, /api/title→:394); POST L357-363 (/api/start→_handle_start:398 returns 409, /api/stop→:404 returns 409 idle, /api/config→:410, /api/title→:415); CORS do_OPTIONS:489; static serve from FRONTEND_DIR L428-437.
- [x] Read secondary UI: stellarorion_program_proc/src/sidecar_ui/js/main.js (polls /api/status every POLL_MS=1000, renders cards step/progress+bar/drag N/heat-flux W/m²/beta kg/m²/decel-g g/surface-temp K, status-badge classes) + index.html (header, 7 metric cards, script js/main.js L51).
- [x] OLD-GUI asset audit COMPLETE via disk checks. MISSING: web/assets/plots/{domain_preview.png, simulation_anim.mp4, convergence_aero_smooth.png, convergence_thermal_smooth.png, convergence_mission_smooth.png, stagnation_graph.png, species_N2_map.png, species_O2_map.png, species_NO_map.png, species_N_map.png, species_O_map.png}. EXISTS: web/assets/{model.stl, remote_view.png}, web/assets/plots/{thermal_map.png, pressure_map.png, upscaled_3d_temp.png, upscaled_3d_velocity.png, upscaled_3d_mach.png, knudsen_map.png, residence_time_map.png, scallop_pocket_temp.png}.
- [x] NEW-frontend asset refs: index.html references only style.css (L7) + main.js (L263, MISSING); main.ts uses fetch only, splash is inline SVG. sidecar_ui refs css/style.css + js/main.js — BOTH exist. Confirmed component/renderEngine/presentation.js EXISTS (content unread).

### In Progress
- [ ] Full enumeration of NEW frontend (stellarorion_program_proc/src/ui/frontend/index.html sections beyond splash, main.ts functions: poll loop, dashboard render, config form, start/stop, history render, title) — only first ~70 lines of each read.
- [ ] Task 6: Ada dashboard-surface grep in stellarorion_program_proc/src/simulation_engine/*.adb (status_writer / reports / Put_Line / validation / compareCalibrate / grid-independence / history DB queries) vs REST coverage — NOT STARTED.
- [ ] Task 7 remainder: compare src/python/sidecar_server.py routes vs sidecar_ui.py (sidecar_server.py unread).
- [ ] Task 8: skim component/renderEngine/presentation.js for shared asset paths (existence confirmed only).
- [ ] Finish Section A enumeration of web/index.html wizard steps 2–8 names/settings/CAD panels/buttons with line refs.
- [ ] Assemble final A–F report.

### Blocked
- (none)

## Key Decisions
- **Path interpretation**: Context paths like "src/ui/..." resolved relative to `stellarorion_program_proc/` after `find` proved no project-root `src/` exists.
- **domain_preview.png classified as runtime-generated**: Engine writes it via request_domain_preview (L795) / generate_cad_preview (L805, L799/L843), so absence on disk is expected, not a hard break — will note nuance in Section D.
- **Grep/awk over full reads for 5543-line engine**: Efficient extraction of Api surface and asset IO without reading entire file.
- **Research-only honored**: Zero modifications made despite gaps discovered.

## Next Steps
1. Verify `stellarorion_program_proc/src/ui/frontend/style.css` exists on disk; `wc -l` both frontend files; finish FULL read of index.html (enumerate every section/control/ID after line ~40) and main.ts (all functions: poll loop, render/update functions, config form handler, start/stop button wiring, history rendering, setTitle usage).
2. Grep `stellarorion_program_proc/src/simulation_engine/*.adb|*.ads` for status_writer, reports, Put_Line, validation, compareCalibrate, grid-independence, history/db query routines; list Ada capabilities NOT surfaced by the 9 REST endpoints.
3. Read `stellarorion_program_proc/src/python/sidecar_server.py`; diff its routes/handlers vs sidecar_ui.py (note which UI it serves and any extra endpoints).
4. Skim `component/renderEngine/presentation.js` imports/string literals for asset paths shared with either GUI.
5. Targeted re-reads of web/index.html ranges to name wizard steps 2–8 and enumerate settings panels/CAD integration/buttons/links for Section A completeness.
6. Build Section C parity table (MISSING/PARTIAL/PRESENT per old capability), Section D broken-assets table (11 missing old paths + main.js + any new-frontend misses), Section E backend parity (old Api methods vs GET /api/status|results|history|config|title + POST /api/start|stop|config|title vs Ada outputs).
7. Compose and deliver final report Sections A–F with file:line refs.

## Critical Context
- KNOWN GAP #1 CONFIRMED: `stellarorion_program_proc/src/ui/frontend/index.html:263` loads `<script src="main.js">`; only main.ts exists; no transpile step found anywhere → new primary GUI currently cannot execute its logic.
- Old-GUI missing assets (verified non-existent on disk): listed above under Done; note domain_preview.png is dynamically produced by engine (not shipped).
- Engine JS-injection plot list (~StellarOrionEngineMach5Up.py:3413-3424) drives image refresh cycles for thermal/pressure/convergence/3D-upscale/species maps — several targets missing (convergence_*_smooth, stagnation_graph, species_*).
- New REST API = only 9 routes; old pywebview Api ≈ 45 public methods (SPARTA/OpenFOAM/pyfluent/manim/GPU-detect/atmosphere-MSIS/chemistry/history-CRUD/draft-autosave/CAD-preview/remote-capture) → large expected parity gap for Section E.
- main.ts HistoryEntry schema keys (Name, Status, Progress, Mach, Altitude_Km, Diameter_M, Heat_Flux, Decel_G, Survivable) suggest DB column mapping for /api/history.
- Secondary monitor (src/sidecar_ui/) is a minimal 7-card status viewer polling /api/status @1s — far thinner than primary frontend.
- Full directory dumps saved at `/Users/albertstarfield/.local/share/opencode/tool-output/` (tool_03e3f36fe001BM4JcoUtDsR7M1, tool_03e3f60830012WNu1EsJm4z5sy, tool_03e3f8867001IDzIf9cvKlD6f1) if re-listing needed.
- web/assets/plots contains many *_smooth_M0_A0.png / sync-conflict variants — potential substitutes for missing canonical plot names worth noting in Section D/F.

## File Operations
### Read
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/sidecar_ui/index.html`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/sidecar_ui/js/main.js`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/ui/frontend/index.html`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/ui/frontend/main.ts`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/web/index.html`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/web/script.js`
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/StellarOrionEngineMach5Up.py` (targeted greps/awk: class Api L150, def listings, asset-IO lines)
- `/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/ui/sidecar_ui.py` (route/handler extraction via grep)

### Modified
- (none)
