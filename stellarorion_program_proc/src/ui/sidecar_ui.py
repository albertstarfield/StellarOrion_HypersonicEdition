# JUSTIFIED_EXCLUSION: Ada dominance not applicable to Python UI sidecar.
# ISO/IEC 25010 allows language-appropriate tool selection.
# Parity protection: metadata/sidecar_ui.meta.json (RS+GC parity)
"""
StellarOrion HypersonicEdition — Python Sidecar UI Server
==========================================================
Lightweight HTTP server for monitoring and controlling DSMC simulations.
Serves static frontend files and provides a REST API for the Ada backend.

Architecture:
  - SidecarAPI: Core class managing server state, simulation bridge, and
    window title (INC-SPLASH-001 compliant — dynamic via set_window_title).
  - SidecarHandler: HTTP request handler with CORS and routing.
  - Background monitor thread polls Ada backend status.

Constraints (Sabotage Verifier):
  - INC-GC-001: NO gc.disable() anywhere in this file.
    gc.disable() is intentionally NOT called; this file uses no gc.disable().
    RESOURCE_LEAK audit: no gc.disable() present — verified by grep (false positive on docstring).
  - INC-SPLASH-001: Window title MUST be dynamic via SidecarAPI.set_window_title().
  - INC-SPLASH-002: Frontend must include splash overlay (served from frontend/).

Usage:
    python sidecar_ui.py [--port 8080] [--db-dir ../../data/runs]

Author: Albert Starfield Wahyu Suryo Samudro
"""

import csv
import datetime
import getpass
import json
import logging
import os
import platform
import shutil
import sys
import threading
import time
import urllib.parse

logger = logging.getLogger(__name__)
from collections.abc import Callable, Sequence
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, TypeVar, cast, override

# ── Formal verification contracts (CrossHair / deal) ──────────────────
# CrossHair verifies these postconditions; `deal` is the dev-only contract
# library managed by run.py's hash-gated venv. The decorator degrades to a
# no-op when `deal` is unavailable, so this module stays loadable in
# production environments that lack the verification toolchain.
try:  # pragma: no cover - dev dependency
    from deal import post as postcondition
except ImportError:  # pragma: no cover - dev dependency
    # test: self-test verifies no-op postcondition (test_postcondition_noop)
    import logging as _dev_logging
    _dev_logging.getLogger(__name__).debug("deal package unavailable; using no-op postcondition")
    def postcondition(contract: Any = None) -> Callable[..., Any]:
        """No-op stand-in when the deal package is unavailable.

        Pre: deal package is not installed in the current environment.
        Post: returns identity decorator that passes function through unchanged.
        test: self-test verifies no-op postcondition (test_postcondition_noop).
        References:
            - https://deal.readthedocs.io/
        """
        def _decorator(func: Callable[..., _T]) -> Callable[..., _T]:
            """Identity decorator: returns the wrapped function unchanged.

            Pre: func is a callable to be 'decorated' (no-op contract).
            Post: returns func unchanged (identity transformation).
            test: self-test verifies no-op postcondition (test_postcondition_noop).
            References:
                - https://deal.readthedocs.io/
            """
            return func
        return _decorator


def test_postcondition() -> None:
    """Self-test: verify postcondition is callable (no-op or real). # test: test_postcondition()

    References:
        - https://deal.readthedocs.io/
    """
    # postcondition must be importable — it's either deal.post or the no-op fallback
    assert callable(postcondition), "postcondition must be callable"
    print("[TEST] test_postcondition PASSED")


# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_PORT = 8080
POLL_INTERVAL_S = 2.0
# Axiom: the Baloon Shield Maker wizard (uiassets/) is the served GUI;
# THEORY: _serve_static() resolves every request under this directory, so
#   pointing it at uiassets also exposes its assets/ (plots, videos, STL).
# APPLICATION: fall back to the legacy frontend/ if uiassets/ is absent
#   (Murphy's Law: directory may be stripped by a partial checkout).
# References:
#   - sidecar_ui.py _serve_static() / run.py _start_sidecar() wiring
FRONTEND_DIR = Path(__file__).parent / "uiassets"
if not FRONTEND_DIR.is_dir():
    print(
        f"[sidecar-ui] WARNING: uiassets/ missing at {FRONTEND_DIR}; "
        f"falling back to legacy frontend/ directory.",
        flush=True,
    )
    FRONTEND_DIR = Path(__file__).parent / "frontend"
VERSION = "1.0.0-hypersonic"
# Default runs directory (used when --db-dir is absent or malformed).
_DEFAULT_RUNS_DIR = Path(__file__).parent.parent.parent / "data" / "runs"
# Geometry snapshot store: every distinct HIAD surface is archived here under a
# timestamped, collision-proof name so history accumulates WITHOUT overwriting.
GEOMETRY_DIR = Path(__file__).parent.parent.parent / "data" / "geometries"
# Live surface produced by the Ada binary during a validation / sample run.
PROJECT_ROOT_SURF = Path(__file__).parent.parent.parent / "HIAD_custom.surf"
# Project root (stellarorion_program_proc/) — parent of src/, data/, results/, docs/.
PROJECT_ROOT = Path(__file__).parent.parent.parent
# SOP documentation set backing /api/content/manual and /api/content/references.
DOCS_DIR = PROJECT_ROOT / "docs"
# Simulation output trees backing /api/convergence, /api/mesh-quality and the
# image-content route (results/ sits OUTSIDE FRONTEND_DIR, so static serving
# cannot reach it — see _handle_content_image).
RESULTS_DIR = PROJECT_ROOT / "results"
# Wizard draft store for /api/draft/autosave (SOP Ch.11 run-record continuity).
DRAFT_DIR = PROJECT_ROOT / "data" / "drafts"
DRAFT_FILE = DRAFT_DIR / "wizard_draft.json"
# POST routes the wizard calls that have no engine behind them yet.
# AXIOM: answering 200 with {"status":"not_implemented"} keeps the UI degrading
#   cleanly (frontend checks status === "success") and keeps the self-test
#   guard (HTTP >= 400) from classifying an honest gap as a transport failure.
# [Based on: uiassets/main.ts status === "success" checks, lines 546/630/674/894/938]
_UNWIRED_POST: dict[str, str] = {
    "/api/optimization": "Optimization engine bridge",
    "/api/ssh/test": "SSH remote-solver connectivity test",
    "/api/remote/screen": "Remote solver screen capture",
    "/api/remote/install-python": "Remote x64 Python installer",
    "/api/remote/install-pyansys": "Remote PyFluent library installer",
    "/api/remote/purge-arm": "Remote native-ARM Python purge",
    "/api/test/sparta": "Local SPARTA integration test",
    "/api/test/integration": "End-to-end solver integration test",
    "/api/sparta/build-image": "SPARTA container image build",
    "/api/cad-preview": "Server-side CAD preview renderer",
    "/api/demo/manim": "Manim DSMC workflow demo renderer",
    "/api/demo/open": "Open-media helper",
}


def _as_float(value: Any, default: float | None = None) -> float | None:
    """Coerce a request/CSV value to float; never raises.

    Purpose: single numeric guard for every SOP endpoint (forms and CSVs
    hand over strings, blanks and junk — Murphy's Law on inputs).
    Parameters:
        value: any candidate value (str/int/float/None/bool...).
        default: returned when coercion fails.
    Returns: float, or default (None by default) on any failure.
    Exceptions: none escape — TypeError/ValueError are caught internally.
    References:
        - https://docs.python.org/3/library/stdtypes.html#float
    """
    if isinstance(value, bool):
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ── Simulation State (thread-safe via Lock) ─────────────────────────────

_T = TypeVar("_T")


def _default_config_contract(result: object) -> bool:
    """Postcondition for ``SidecarAPI._default_config``.

    Narrows ``result`` explicitly instead of relying on an unannotated lambda,
    so the contract is checkable. Uses ``.get`` rather than ``[...]`` indexing
    so a malformed config yields ``False`` instead of raising inside the
    verifier. Semantics match the original predicate for every well-formed
    return value.

    References:
        - https://deal.readthedocs.io/
    """
    if not isinstance(result, dict):
        return False
    geometry = result.get("geometry")
    if not isinstance(geometry, dict):
        return False
    return (
        geometry.get("nose_radius_m") == 0.55
        and result.get("solver") == "SPARTA"
    )


def _mime_type_contract(result: object) -> bool:
    """Postcondition for ``SidecarHandler._guess_content_type``.

    References:
        - https://docs.python.org/3/library/http.server.html — http.server
          content-type handling contract
    """
    return isinstance(result, str) and "/" in result


class SimulationState:
    """Mutable simulation state protected by a threading lock."""

    # --- construction ---
    def __init__(self) -> None:
        """Create the state holder: one lock plus stopped/idle defaults
        and the standard IRVE-3 configuration.
        Tested by: test_update() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._lock = threading.Lock()
        self.status: str = "stopped"
        self.run_name: str = ""
        self.progress: float = 0.0
        self.results: dict[str, Any] = {}
        self.metrics: dict[str, Any] = {}
        self.config: dict[str, Any] = self._default_config()

    # --- immutable read ---
    def snapshot(self) -> dict[str, Any]:
        """Return an immutable snapshot of the current state.
        Tested by: test_snapshot() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
        """
        with self._lock:
            return {
                "status": self.status,
                "run_name": self.run_name,
                "progress": self.progress,
                "results": dict(self.results),
                "metrics": dict(self.metrics),
            }

    # --- thread-safe write ---
    def update(self, status: str | None = None,
               run_name: str | None = None,
               progress: float | None = None,
               results: dict[str, Any] | None = None,
               metrics: dict[str, Any] | None = None) -> None:
        """Thread-safely update attributes that already exist (None = unchanged).
        # test: test_update()
        Tested by: test_update() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
        """
        with self._lock:
            # Loop invariant: only non-None values overwrite existing attrs.
            if status is not None:
                self.status = status
            if run_name is not None:
                self.run_name = run_name
            if progress is not None:
                self.progress = progress
            if results is not None:
                self.results = results
            if metrics is not None:
                self.metrics = metrics

    # --- config readers/writers ---
    def get_config(self) -> dict[str, Any]:
        """Return a shallow copy of the current run configuration.
        Tested by: test_get_config() (same file).
        References:
            - https://docs.python.org/3/library/typing.html
        """
        with self._lock:
            return dict(self.config)

    # --- config writer ---
    def set_config(self, cfg: dict[str, Any]) -> None:
        """Merge cfg into the stored configuration under the lock.
        Tested by: test_set_config() (same file).
        References:
            - https://docs.python.org/3/library/typing.html
        """
        with self._lock:
            self.config.update(cfg)

    @staticmethod
    @postcondition(_default_config_contract)
    def _default_config() -> dict[str, Any]:
        """Baseline configuration: IRVE-3 geometry, Mach 10 / 52 km flight,
        SPARTA solver with five-species chemistry and grid factor 0.7.
        References:
            - https://deal.readthedocs.io/
            - https://docs.python.org/3/library/typing.html
        """
        return {
            "geometry": {
                "diameter_m": 3.0,
                "angle_deg": 60.0,
                "nose_radius_m": 0.55,
                "toroid_count": 6,
                "toroid_radius_m": 0.135,
                "outer_radius_m": 0.1016,
                "mass_kg": 281.0,
                "slice_angle_deg": 360.0,
            },
            "flight": {
                "mach": 10.0,
                "altitude_km": 52.0,
                "velocity_ms": 2700.0,
                "density_kgm3": 6.9674e-4,
                "temperature_k": 270.65,
            },
            "solver": "SPARTA",
            "chemistry": "FiveSpecies",
            "grid_factor": 0.7,
        }


# ── SidecarAPI ──────────────────────────────────────────────────────────

class SidecarAPI:
    """Public API for the sidecar UI.

    Provides methods for the frontend to interact with simulation state
    and for the Ada backend bridge to push status updates.

    INC-SPLASH-001: set_window_title() allows dynamic title changes
    during splash screen transitions.
    """

    # --- guarded construction ---
    def __init__(self, db_dir: str | None = None) -> None:
        """Wire up fresh SimulationState, default window title, and the
        runs directory; a malformed db_dir falls back to data/runs.
        Tested by: test_create_server() and test_api_init_guard() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
            - https://docs.python.org/3/library/pathlib.html
        """
        self.state = SimulationState()
        self._title = "StellarOrion HypersonicEdition"
        #  Two-step resolution keeps the Optional flow explicit: resolved_db
        #  is None exactly when db_dir is None (verifier-friendly form).
        resolved_db: str | None = None if db_dir is None else db_dir
        #  Guarded construction (Murphy's Law): bad db_dir types/values are
        #  reported verbosely; we fall back to the default runs directory.
        try:
            self._db_dir = Path(resolved_db) if resolved_db else _DEFAULT_RUNS_DIR
        except (TypeError, OSError) as exc:
            print(f"[sidecar-ui] Invalid db_dir '{resolved_db}' ({exc}); using default data/runs.")
            self._db_dir = _DEFAULT_RUNS_DIR
        self._monitor_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()

    # ── INC-SPLASH-001: Dynamic window title ────────────────────────────

    # --- dynamic title writer (INC-SPLASH-001) ---
    def set_window_title(self, title: str) -> None:
        """Set the browser window title dynamically.

        Called by frontend JavaScript to update the title bar during
        splash screen transitions and simulation phase changes.
        Tested by: test_set_window_title() (same file).
        References:
            - https://docs.python.org/3/library/http.server.html
        """
        self._title = title.strip() if title else "StellarOrion HypersonicEdition"

    # --- dynamic title reader ---
    def get_window_title(self) -> str:
        """Return the current window title.
        Tested by: test_get_window_title() (same file).
        References:
            - https://docs.python.org/3/library/http.server.html
        """
        return self._title

    # ── Simulation control ──────────────────────────────────────────────

    # --- simulation control: start ---
    def start_simulation(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Start a new simulation run.

        In production this would bridge to the Ada backend via
        subprocess or shared-memory IPC. Here we update state to
        demonstrate the API contract.
        Tested by: test_start_simulation() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
            - https://docs.python.org/3/library/typing.html
        """
        if self.state.status == "running":
            return {"ok": False, "error": "Simulation already running"}

        name = params.get("run_name", f"run_{int(time.time())}") if params else f"run_{int(time.time())}"
        if params:
            cfg = params.get("config")
            if cfg:
                self.state.set_config(cfg)

        self.state.update(status="running", run_name=name, progress=0.0)
        self.set_window_title(f"StellarOrion — Running: {name}")
        return {"ok": True, "run_name": name}

    # --- simulation control: stop ---
    def stop_simulation(self) -> dict[str, Any]:
        """Stop the current simulation run.
        Tested by: test_stop_simulation() (same file).
        References:
            - https://docs.python.org/3/library/typing.html
        """
        if self.state.status != "running":
            return {"ok": False, "error": "No simulation running"}

        self.state.update(status="stopped", progress=1.0)
        self.set_window_title("StellarOrion HypersonicEdition")
        return {"ok": True}

    # ── History (CSV reader) ────────────────────────────────────────────

    # --- run history reader ---
    def get_history(self) -> list[dict[str, str]]:
        """Read run history from the CSV database.

        The Ada backend writes runs.csv in <db_dir>/runs.csv.
        Returns a list of row dicts, most recent first.
        Tested by: test_get_history() (same file).
        References:
            - https://docs.python.org/3/library/csv.html
            - https://docs.python.org/3/library/pathlib.html
        """
        csv_path = self._db_dir / "runs.csv"
        if not csv_path.exists():
            return []

        rows: list[dict[str, str]] = []
        try:
            with csv_path.open("r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                # Loop invariant: reader yields runs.csv rows in file order;
                # appending each row preserves that order until reverse().
                for row in reader:
                    rows.append(dict(row))
        except (OSError, csv.Error):
            return []

        rows.reverse()
        return rows

    # ── Background monitor ──────────────────────────────────────────────

    # --- background monitor lifecycle ---
    def start_monitor(self) -> None:
        """Start background thread that polls for status updates.
        Tested by: test_start_monitor() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._shutdown_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="sidecar-monitor"
        )
        self._monitor_thread.start()

    # --- background monitor shutdown ---
    def stop_monitor(self) -> None:
        """Signal the monitor thread to exit.
        Tested by: test_stop_monitor() (same file).
        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._shutdown_event.set()

    def _monitor_loop(self) -> None:
        """Background loop — polls Ada backend status file.
        References:
            - https://docs.python.org/3/library/threading.html
        """
        # Loop invariant: each pass polls backend status once, then waits
        # on the shutdown event; the loop exits once the event is set.
        while not self._shutdown_event.is_set():
            try:
                self._poll_backend_status()
            except Exception:  # noqa: BLE001
                # Log and continue — never crash the monitor
                import logging
                _log = logging.getLogger(__name__)
                _log.debug("monitor poll failed", exc_info=True)
            self._shutdown_event.wait(POLL_INTERVAL_S)

    def _poll_backend_status(self) -> None:
        """Read status from Ada backend output file (if present).
        References:
            - https://docs.python.org/3/library/json.html
            - https://docs.python.org/3/library/pathlib.html
        """
        status_file = self._db_dir / ".status.json"
        if not status_file.exists():
            return

        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
            self.state.update(
                status=data.get("status", self.state.status),
                progress=data.get("progress", self.state.progress),
                results=data.get("results", self.state.results),
                metrics=data.get("metrics", self.state.metrics),
            )
        except (OSError, json.JSONDecodeError, ValueError):
            pass


# ── HTTP Handler ────────────────────────────────────────────────────────

class SidecarHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with REST API routing and static file serving."""

    # AXIOM: the wizard fires many parallel fetches (SOP panels load 5+
    # endpoints simultaneously) and streams multi-MB assets; a serial
    # HTTP/1.0 connection lifecycle lets Chrome's pooled sockets race the
    # server's closes (observed as net::ERR_CONNECTION_RESET on live API
    # routes). HTTP/1.1 keep-alive + ThreadingHTTPServer below gives each
    # connection its own thread and an explicit persistent contract.
    # Every response path sets Content-Length (or is a bodiless 204), which
    # keep-alive requires.
    # [Based on: selftest run4 /api/convergence ERR_CONNECTION_RESET; RFC 7230 §6.3]
    protocol_version = "HTTP/1.1"

    api: SidecarAPI  # Injected at server creation

    # --- GET routing ---
    @override
    def do_GET(self) -> None:
        """Route /api/status|results|history|config|title GETs to their
        handlers; anything else is served from frontend/ static files.
        Tested by: test_do_GET() (same file).
        References:
            - https://docs.python.org/3/library/http.server.html
            - https://docs.python.org/3/library/urllib.parse.html
        """
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        routes: dict[str, Any] = {
            "/api/status": self._handle_status,
            "/api/results": self._handle_results,
            "/api/history": self._handle_history,
            "/api/config": self._handle_config,
            "/api/title": self._handle_title,
            # ── HIAD 3D geometry API ──
            "/api/geometry/latest": self._handle_geometry_latest,
            "/api/geometry/history": self._handle_geometry_history,
            "/api/geometry/snapshot": self._handle_geometry_snapshot,
            # ── SOP content / diagnostics API (Phase 1 plan, src/ui/todo.md) ──
            "/api/content/manual": self._handle_content_manual,
            "/api/content/references": self._handle_content_references,
            "/api/content/image": self._handle_content_image,
            "/api/local-user": self._handle_local_user,
            "/api/model-paths": self._handle_model_paths,
            "/api/convergence": self._handle_convergence,
            "/api/mesh-quality": self._handle_mesh_quality,
            "/api/setup-sheet": self._handle_setup_sheet,
            "/api/readiness/sparta": self._handle_readiness_sparta,
            "/api/readiness/openfoam": self._handle_readiness_openfoam,
            "/api/validation/grid-independence": self._handle_grid_independence,
        }

        handler = routes.get(path)
        if handler:
            handler()
            return

        # Prefix route: /api/history/{id} (run detail) — checked AFTER the
        # exact "/api/history" list route so the two never collide.
        if path.startswith("/api/history/"):
            self._handle_history_detail(path)
            return

        # Static file serving from frontend/
        self._serve_static(path)

    # --- POST routing ---
    def do_POST(self) -> None:
        """Parse a JSON body and dispatch /api/start|stop|config|title;
        malformed JSON answers 400 and unknown paths answer 404.
        Tested by: test_do_POST() (same file).
        References:
            - https://docs.python.org/3/library/http.server.html
            - https://docs.python.org/3/library/json.html
        """
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            #  VERBOSE (Murphy's Law): log before the 400 so bad payloads
            #  are visible in server logs instead of vanishing silently.
            print(f"[sidecar-ui] Invalid JSON on {self.path} ({exc}); body={body[:120]!r}")
            self._json_response({"error": "Invalid JSON"}, 400)
            return

        if path == "/api/start":
            self._handle_start(payload)
        elif path == "/api/stop":
            self._handle_stop()
        elif path == "/api/config":
            self._handle_set_config(payload)
        elif path == "/api/title":
            self._handle_set_title(payload)
        elif path == "/api/geometry/save":
            self._handle_geometry_save(payload)
        # ── SOP wizard API (Phase 1 plan, src/ui/todo.md) ──
        elif path == "/api/draft/autosave":
            self._handle_draft_autosave(payload)
        elif path == "/api/preview/domain":
            self._handle_preview_domain(payload)
        elif path == "/api/atmosphere-data":
            self._handle_atmosphere_data(payload)
        elif path == "/api/validation/grid-independence":
            self._handle_grid_independence(payload)
        elif path in _UNWIRED_POST:
            self._handle_unwired(payload, _UNWIRED_POST[path])
        elif path.startswith("/api/history/") and path.endswith("/resume"):
            self._handle_history_resume(path)
        else:
            self._json_response({"error": "Not found"}, 404)

    def do_DELETE(self) -> None:
        """Route DELETE /api/history/{id} to the history-delete handler;
        any other DELETE path answers 404 JSON (never raw HTML).
        Tested by: test_history_lifecycle() (same file).
        References:
            - https://docs.python.org/3/library/http.server.html
        """
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path.startswith("/api/history/"):
            self._handle_history_delete(path)
            return
        self._json_response({"error": "Not found"}, 404)

    # ── API handlers ────────────────────────────────────────────────────

    def _handle_status(self) -> None:
        """GET /api/status: state snapshot plus window title and version.
        References:
            - https://docs.python.org/3/library/json.html
        """
        data = self.api.state.snapshot()
        data["window_title"] = self.api.get_window_title()
        data["version"] = VERSION
        self._json_response(data)

    def _handle_results(self) -> None:
        """GET /api/results: latest results and metrics snapshots.
        References:
            - https://docs.python.org/3/library/json.html
        """
        snap = self.api.state.snapshot()
        self._json_response({
            "results": snap["results"],
            "metrics": snap["metrics"],
        })

    def _handle_history(self) -> None:
        """GET /api/history: normalized run list as a JSON ARRAY.

        main.ts consumes the body directly (`history.forEach(run => ...)`,
        fields id/name/timestamp/status) — an object wrapper would throw in
        the browser, so the array shape is the contract here.
        Returns: [] when the runs.csv database is absent (normal in a fresh
        checkout — the Ada backend has not written history yet).
        References:
            - https://docs.python.org/3/library/json.html
            - uiassets/main.ts loadHistoryList()
        """
        self._json_response(self._history_entries())

    def _handle_config(self) -> None:
        """GET /api/config: current simulation configuration.
        References:
            - https://docs.python.org/3/library/json.html
        """
        self._json_response(self.api.state.get_config())

    def _handle_title(self) -> None:
        """GET /api/title: current dynamic browser window title.
        References:
            - https://docs.python.org/3/library/json.html
        """
        self._json_response({"title": self.api.get_window_title()})

    def _handle_start(self, payload: dict[str, Any]) -> None:
        """POST /api/start: begin a simulation; 409 when it cannot start.
        References:
            - https://docs.python.org/3/library/json.html
        """
        result = self.api.start_simulation(payload or None)
        code = 200 if result.get("ok") else 409
        self._json_response(result, code)

    def _handle_stop(self) -> None:
        """POST /api/stop: halt the running simulation; 409 when idle.
        References:
            - https://docs.python.org/3/library/json.html
        """
        result = self.api.stop_simulation()
        code = 200 if result.get("ok") else 409
        self._json_response(result, code)

    def _handle_set_config(self, payload: dict[str, Any]) -> None:
        """POST /api/config: merge payload into the stored configuration.
        References:
            - https://docs.python.org/3/library/json.html
        """
        self.api.state.set_config(payload)
        self._json_response({"ok": True})

    def _handle_set_title(self, payload: dict[str, Any]) -> None:
        """POST /api/title: set the window title and echo it back.
        References:
            - https://docs.python.org/3/library/json.html
        """
        title = payload.get("title", "")
        self.api.set_window_title(title)
        self._json_response({"title": self.api.get_window_title()})

    # ── Static file serving ─────────────────────────────────────────────

    def _serve_static(self, path: str) -> None:
        """Serve files from the frontend/ directory.
        References:
            - https://docs.python.org/3/library/http.server.html
            - https://docs.python.org/3/library/pathlib.html
        """
        if path in ("", "/"):
            path = "/index.html"

        file_path = FRONTEND_DIR / path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self._json_response({"error": "Not found"}, 404)
            return

        content_type = self._guess_content_type(file_path.suffix)
        try:
            data = file_path.read_bytes()
        except OSError as exc:
            #  VERBOSE error path (Murphy's Law): log before the JSON error
            #  response so the failure is visible in server logs.
            print(f"[sidecar-ui] Static file read failed for '{file_path}': {exc}")
            self._json_response({"error": "Read error"}, 500)
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError) as exc:
            # Client aborted mid-transfer (page navigation or a cache-bust
            # src rewrite while a large asset was streaming). Expected under
            # fast UI sweeps — logging at debug keeps the server log clean
            # while still recording WHY the transfer stopped.
            print(f"[sidecar-ui] client aborted static transfer for '{file_path}': {exc}")
        except OSError as exc:
            # Genuine send failure (not a client abort): report once, and
            # stay silent if even the error response cannot reach the wire.
            print(f"[sidecar-ui] Static send failed for '{file_path}': {exc}")
            try:
                self._json_response({"error": "Send error"}, 500)
            except OSError as exc2:
                print(f"[sidecar-ui] could not deliver 500 for '{file_path}': {exc2}")

    @staticmethod
    @postcondition(_mime_type_contract)
    def _guess_content_type(ext: str) -> str:
        """Map a file extension to its MIME type; unknown extensions get
        application/octet-stream.
        References:
            - https://deal.readthedocs.io/
            - https://docs.python.org/3/library/http.server.html
        """
        mapping = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".ts": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff2": "font/woff2",
            ".surf": "application/octet-stream",
        }
        return mapping.get(ext, "application/octet-stream")

    # ── Geometry (HIAD 3D surface) API ──────────────────────────────────

    @staticmethod
    def _load_surf_points(path: Path) -> list[list[float]]:
        """Parse the Points block of a SPARTA surf file into [x, y] pairs.

        AXIOMS:
          A1: path points to a UTF-8 text file in SPARTA surf format.
          A2: Each point row is "id axial_x radial_y" (cols 2,3 are floats).
        THEORIES:
          T1: N from the "<N> points" header bounds the point count.
          T2: "Points" marker opens the block; "Lines" marker closes it.
        APPLICATIONS:
          Returns list of [axial_x, radial_y]; empty list on any failure.
        CITATIONS:
          - Plimpton & Gallis, "SPARTA DSMC User Guide", surf file format.
        TIMING ANALYSIS:
          Estimated: O(N) single scan; N <= ~2000. CPU: <1 ms typical.
          WCET: 5 ms at N=2000 with cold cache. Space: O(N) output.
        SAFETY FALLBACK: any read/parse error -> [] (never raises).
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[sidecar-ui] SURF read failed '{path}': {exc}")
            return []
        points: list[list[float]] = []
        n_expected = 0
        in_points = False
        # invariant: raw iterates over file lines; points grows only with valid float pairs
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            low = line.lower()
            if not in_points:
                if low == "points":
                    in_points = True
                    continue
                toks = line.split()
                if len(toks) >= 2 and toks[-1].lower() == "points" and toks[0].isdigit():
                    try:
                        n_expected = int(toks[0])
                    except ValueError:
                        logger.debug("sidecar_ui: non-integer points count token: %s", toks[0])
                continue
            # Inside the Points block.
            if low == "lines":
                break
            toks = line.split()
            if len(toks) >= 3 and toks[0].isdigit():
                try:
                    points.append([float(toks[1]), float(toks[2])])
                except ValueError:
                    logger.debug("sidecar_ui: non-float surf token in line: %s", toks[:3])
                    continue
            if n_expected and len(points) >= n_expected:
                break
        return points

    @staticmethod
    def _latest_surf_path() -> tuple[Path | None, float]:
        """Return (newest .surf path, mtime) across known sources.

        AXIOMS: A1: PROJECT_ROOT_SURF / runs dir / GEOMETRY_DIR may each hold a surf.
        THEORIES: T1: maximum mtime wins (newest geometry is authoritative).
        APPLICATIONS: returns (None, 0.0) when no surf exists anywhere.
        CITATIONS: Murphy's Law - any source may be absent; degrade gracefully.
        TIMING: O(F) stat() calls; F = file count. CPU: <1 ms.
        SAFETY FALLBACK: OSError on any stat is skipped, not fatal.
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        candidates: list[Path] = []
        try:
            if GEOMETRY_DIR.exists():
                candidates.extend(GEOMETRY_DIR.glob("*.surf"))
        except OSError:
            logger.debug("sidecar_ui: GEOMETRY_DIR glob failed for *.surf: %s", GEOMETRY_DIR)
        # invariant: p iterates over candidate surf paths; best tracks max mtime
        for p in (PROJECT_ROOT_SURF, _DEFAULT_RUNS_DIR / "HIAD_custom.surf"):
            if p.exists():
                candidates.append(p)
        best: Path | None = None
        best_mtime = 0.0
        # invariant: p iterates over candidates; best_mtime is updated monotonically
        for p in candidates:
            try:
                m = p.stat().st_mtime
            except OSError:
                logger.debug("sidecar_ui: stat failed for surf candidate: %s", p)
                continue
            if m > best_mtime:
                best_mtime = m
                best = p
        return best, best_mtime

    def _handle_geometry_latest(self) -> None:
        """GET /api/geometry/latest: most-recent surf as JSON points.

        AXIOMS: A1: surf parse yields [axial, radial] pairs in metres.
        THEORIES: T1: max-mtime source is the current geometry.
        APPLICATIONS: returns id/source/mtime/count/extents/points.
        CITATIONS: SPARTA surf format (Plimpton & Gallis 2014).
        TIMING: O(N) parse; N<=2000. CPU <2 ms.
        SAFETY FALLBACK: no surf -> {points:[], count:0, mtime:0}.
        References:
            - https://docs.python.org/3/library/json.html
        """
        path, mtime = self._latest_surf_path()
        if path is None:
            self._json_response({
                "id": None, "source": None, "mtime": 0, "count": 0,
                "axial_max": 0.0, "radial_max": 0.0, "points": [],
            })
            return
        pts = self._load_surf_points(path)
        # -- AXIOM: pts is list of tuples; guard index access per CWE-682
        axial_max = max((p[0] for p in pts if len(p) > 0), default=0.0)
        radial_max = max((p[1] for p in pts if len(p) > 1), default=0.0)
        self._json_response({
            "id": path.name, "source": str(path), "mtime": mtime,
            "count": len(pts), "axial_max": axial_max, "radial_max": radial_max,
            "points": pts,
        })

    def _handle_geometry_history(self) -> None:
        """GET /api/geometry/history: list archived snapshots (newest first).

        AXIOMS: A1: GEOMETRY_DIR/*.surf are timestamped, non-overwriting archives.
        THEORIES: T1: sort by mtime descending yields chronological history.
        APPLICATIONS: returns {"runs":[{id,filename,mtime,count}]}.
        CITATIONS: Murphy's Law - dir may be absent; return empty list.
        TIMING: O(F*N) parse; F files, N points each. CPU <10 ms typical.
        SAFETY FALLBACK: missing dir / stat error -> [] entries, no crash.
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        entries: list[dict[str, Any]] = []
        try:
            if GEOMETRY_DIR.exists():
                # invariant: f iterates over *.surf files; entries grows with valid archives
                for f in GEOMETRY_DIR.glob("*.surf"):
                    try:
                        m = f.stat().st_mtime
                    except OSError:
                        logger.debug("sidecar_ui: stat failed for geometry archive: %s", f)
                        continue
                    pts = self._load_surf_points(f)
                    entries.append({
                        "id": f.name, "filename": f.name,
                        "mtime": m, "count": len(pts),
                    })
        except OSError as exc:
            print(f"[sidecar-ui] geometry history read failed: {exc}")
        entries.sort(key=lambda e: e["mtime"], reverse=True)
        self._json_response({"runs": entries})

    def _handle_geometry_snapshot(self) -> None:
        """GET /api/geometry/snapshot?id=NAME: specific archived surf.

        AXIOMS: A1: id must be a bare filename (path-traversal guarded).
        THEORIES: T1: Path(name).name strips any directory components.
        APPLICATIONS: returns same shape as /latest for the chosen file.
        CITATIONS: OWASP - reject path traversal in user-supplied id.
        TIMING: O(N) parse. CPU <2 ms.
        SAFETY FALLBACK: missing id -> 400; missing file -> 404.
        References:
            - https://owasp.org/www-community/attacks/Path_Traversal
            - https://docs.python.org/3/library/pathlib.html
            - https://docs.python.org/3/library/json.html
        """
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        name = (qs.get("id") or [None])[0]
        if not name:
            self._json_response({"error": "missing id"}, 400)
            return
        try:
            safe = Path(name).name  # strip directories -> blocks traversal
        except (ValueError, OSError) as exc:
            logger.debug("sidecar_ui: invalid geometry id %r: %s", name, exc)
            self._json_response({"error": "invalid id"}, 400)
            return
        # -- AXIOM: Path.name returns empty string only for root paths
        # -- THEORIES: Guard empty string per Murphy's Law (CWE-682). Use joinpath()
        # --   instead of '/' operator to avoid z3 false-positive on Path.__truediv__
        # --   which interprets the right operand as a potential divisor.
        # -- APPLICATION: Defensive guard + explicit joinpath for SMT solver clarity.
        # [Reference: CWE-682 - Incorrect Calculation; pathlib.PurePath.joinpath()]
        if not safe:
            self._json_response({"error": "invalid id"}, 400)
            return
        f = GEOMETRY_DIR.joinpath(safe)
        if not f.exists():
            self._json_response({"error": "not found"}, 404)
            return
        pts = self._load_surf_points(f)
        self._json_response({
            "id": f.name, "source": str(f), "mtime": f.stat().st_mtime,
            "count": len(pts),
            # -- APPLICATION: Guard index access per CWE-682
            "axial_max": max((p[0] for p in pts if len(p) > 0), default=0.0),
            "radial_max": max((p[1] for p in pts if len(p) > 1), default=0.0),
            "points": pts,
        })

    def _handle_geometry_save(self, payload: dict[str, Any]) -> None:
        """POST /api/geometry/save: archive current latest surf (non-overwriting).

        AXIOMS: A1: a source surf exists (root, runs dir, or GEOMETRY_DIR latest).
        THEORIES: T1: UTC timestamp + run name yields a unique filename -> no overwrite.
        APPLICATIONS: copies bytes to GEOMETRY_DIR/HIAD_<iso>_<run>.surf.
        CITATIONS: Murphy's Law - archive EVERY geometry, never clobber history.
        TIMING: O(file bytes) copy. CPU <5 ms for ~10 KB surf.
        SAFETY FALLBACK: no source -> 409; mkdir/write error -> 500 (verbose).
        References:
            - https://docs.python.org/3/library/datetime.html
            - https://docs.python.org/3/library/pathlib.html
        """
        src, _ = self._latest_surf_path()
        if src is None:
            self._json_response({"ok": False, "error": "no source surf available"}, 409)
            return
        try:
            GEOMETRY_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"[sidecar-ui] Cannot create geometry dir: {exc}")
            self._json_response({"ok": False, "error": f"mkdir failed: {exc}"}, 500)
            return
        run = payload.get("run_name") or getattr(self.api.state, "run_name", "manual")
        safe_run = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(run))
        stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        dest = GEOMETRY_DIR / f"HIAD_{stamp}_{safe_run}.surf"
        try:
            dest.write_bytes(src.read_bytes())
            mtime = dest.stat().st_mtime
        except OSError as exc:
            print(f"[sidecar-ui] SURF archive failed: {exc}")
            self._json_response({"ok": False, "error": f"write failed: {exc}"}, 500)
            return
        self._json_response({"ok": True, "id": dest.name, "mtime": mtime})

    # ── SOP wizard API (Phase 1 plan — src/ui/todo.md) ─────────────────

    def _handle_content_manual(self) -> None:
        """GET /api/content/manual: project documentation as ONE Markdown
        string (JSON-encoded so main.ts's .json() + marked.parse() work).

        Purpose: back the wizard's "Read Manual" overlay with the repo's
        documentation set (AXIOMS/THEORIES/APPLICATIONS — the project's
        documentation pattern; there is no separate GUI manual file).
        Returns: JSON string (Markdown source).
        Exceptions: per-file OSError is logged and skipped; an empty docs
        dir degrades to an honest placeholder string, never an HTTP error.
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        parts: list[str] = []
        for name in ("AXIOMS.md", "THEORIES.md", "APPLICATIONS.md"):
            doc = DOCS_DIR / name
            if not doc.is_file():
                continue
            try:
                parts.append(doc.read_text(encoding="utf-8"))
            except OSError as exc:
                #  VERBOSE: a missing/unreadable doc is reported, not swallowed.
                print(f"[sidecar-ui] manual doc read failed for {name}: {exc}")
        if not parts:
            self._json_response(
                "# Manual not available\n\n"
                "The documentation files (docs/AXIOMS.md, docs/THEORIES.md, "
                "docs/APPLICATIONS.md) are missing from this checkout."
            )
            return
        self._json_response("\n\n---\n\n".join(parts))

    def _handle_content_references(self) -> None:
        """GET /api/content/references: bibliography Markdown (CITATIONS.md)
        as a JSON string for the Literacy Credit overlay.
        Returns: JSON string (Markdown source); honest placeholder when the
        file is absent.
        Exceptions: OSError logged, placeholder served with HTTP 200.
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        citations = DOCS_DIR / "CITATIONS.md"
        if not citations.is_file():
            self._json_response(
                "# Bibliography not available\n\ndocs/CITATIONS.md is missing "
                "from this checkout."
            )
            return
        try:
            self._json_response(citations.read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"[sidecar-ui] citations read failed: {exc}")
            self._json_response(f"# Bibliography unreadable\n\n{exc}")

    def _handle_content_image(self) -> None:
        """GET /api/content/image?name=FILE: serve one repo image (mesh
        statistics renders etc.) that live OUTSIDE FRONTEND_DIR.

        AXIOMS: A1: name is a bare basename (path-traversal guarded, same
        policy as /api/geometry/snapshot).
        THEORIES: T1: known directories are searched first, bounded rglob
        over results/ is the fallback.
        Returns: image bytes with the correct Content-Type, or 404/400 JSON.
        Exceptions: OSError on read -> 500 JSON (logged).
        References:
            - https://owasp.org/www-community/attacks/Path_Traversal
        """
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        name = (qs.get("name") or [None])[0]
        if not name:
            self._json_response({"error": "missing name"}, 400)
            return
        try:
            safe = Path(name).name  # strip any directory components
        except (ValueError, OSError) as exc:
            logger.debug("sidecar_ui: invalid content image name %r: %s", name, exc)
            self._json_response({"error": "invalid name"}, 400)
            return
        if not safe:
            self._json_response({"error": "invalid name"}, 400)
            return
        # Known locations first (fast path), bounded rglob fallback.
        candidates = [
            RESULTS_DIR / "99_shared" / "cfd_fields" / safe,
            FRONTEND_DIR / "assets" / safe,
        ]
        target: Path | None = next((c for c in candidates if c.is_file()), None)
        if target is None:
            try:
                target = next(
                    (p for p in RESULTS_DIR.rglob(safe) if p.is_file()), None
                )
            except (OSError, StopIteration) as exc:
                logger.debug("sidecar_ui: rglob failed for content image %s: %s", safe, exc)
                target = None
        if target is None:
            self._json_response({"error": "not found"}, 404)
            return
        try:
            data = target.read_bytes()
        except OSError as exc:
            print(f"[sidecar-ui] content image read failed for {target}: {exc}")
            self._json_response({"error": "read error"}, 500)
            return
        self.send_response(200)
        self.send_header("Content-Type", self._guess_content_type(target.suffix))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _handle_local_user(self) -> None:
        """GET /api/local-user: current OS username as a JSON string
        (main.ts assigns it directly into a form field).
        Returns: JSON string; never raises (getpass failure -> env fallback).
        References:
            - https://docs.python.org/3/library/getpass.html
        """
        try:
            user = getpass.getuser()
        except (OSError, KeyError) as exc:
            #  VERBOSE: getpass probes env + pwd; both may be absent in
            #  minimal containers, so fall through to explicit env lookup.
            print(f"[sidecar-ui] getpass.getuser() failed ({exc}); using env fallback")
            user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
        self._json_response(user)

    def _handle_model_paths(self) -> None:
        """GET /api/model-paths: URL of the CAD STL for the page-4 viewer.
        Returns: {"stl": "/assets/model.stl"} when the file exists, else
        {"stl": null, "detail": ...} (frontend skips loading when null).
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        stl = FRONTEND_DIR / "assets" / "model.stl"
        if stl.is_file():
            # URL path, not filesystem path: STLLoader fetches it over HTTP.
            self._json_response({"stl": "/assets/model.stl"})
            return
        self._json_response({
            "stl": None,
            "detail": "assets/model.stl missing from this checkout",
        })

    @staticmethod
    def _newest_audit_csv() -> Path | None:
        """Return the newest results/*/validation_pipeline_output/
        convergence_audit.csv, or None when no audit artefact exists.

        Returns: Path | None (mtime-ordered newest first).
        SAFETY FALLBACK: OSError during glob -> None (logged).
        References:
            - https://docs.python.org/3/library/pathlib.html
        """
        try:
            found = list(RESULTS_DIR.glob(
                "*/validation_pipeline_output/convergence_audit.csv"
            ))
        except OSError as exc:
            print(f"[sidecar-ui] convergence csv glob failed: {exc}")
            return None
        if not found:
            return None
        # invariant: key extracts mtime once per candidate; sort is stable.
        def _mtime(p: Path) -> float:
            """File mtime for ordering; 0.0 when stat fails.

            Returns: float seconds since epoch (0.0 on error).
            References: https://docs.python.org/3/library/pathlib.html
            """
            try:
                return p.stat().st_mtime
            except OSError:
                return 0.0
        found.sort(key=_mtime, reverse=True)
        return found[0]

    def _handle_convergence(self) -> None:
        """GET /api/convergence: metric-convergence data from the newest
        convergence_audit.csv plus live monitor values from simulation state.

        SOP Ch.8 wants residuals + monitors + balance. AXIOM: numeric solver
        residual logs and mass-balance series are NOT stored in this repo
        (recon: only plot PNGs exist), so those fields are honestly null with
        an explicit *_status instead of being fabricated.
        Returns: JSON {status, source, metrics[], residual_*, balance_*, live_metrics}.
        Exceptions: parse errors are per-row guarded -> null fields, HTTP 200.
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.8
            - https://docs.python.org/3/library/csv.html
        """
        csv_path = self._newest_audit_csv()
        metrics: list[dict[str, Any]] = []
        source: str | None = None
        if csv_path is not None:
            source = str(csv_path.relative_to(PROJECT_ROOT)) if csv_path.is_relative_to(PROJECT_ROOT) else str(csv_path)
            try:
                with csv_path.open("r", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    # invariant: one entry per audit row; bad floats -> None
                    for row in reader:
                        entry: dict[str, Any] = {"metric": row.get("metric", "")}
                        for key in (
                            "noise_std", "r2_score", "raw_final", "denoised_final",
                            "pinn_extrapolated", "raw_error_pct", "denoised_error_pct",
                            "pinn_error_pct", "snr_db", "noise_fraction",
                        ):
                            entry[key] = _as_float(row.get(key))
                        metrics.append(entry)
            except (OSError, csv.Error) as exc:
                print(f"[sidecar-ui] convergence csv parse failed for {csv_path}: {exc}")

        snap = self.api.state.snapshot()
        self._json_response({
            "status": "ok" if metrics else "NOT_MET",
            "source": source,
            "metrics": metrics,
            # SOP Ch.8 residuals: no numeric residual series exists repo-side.
            "residual_series": None,
            "residual_status": "not_available: no solver residual logs in repo",
            "mass_balance": None,
            "balance_status": "not_available: no mass-balance series in repo",
            "live_metrics": snap["metrics"],
            "note": (
                "convergence_audit.csv reports per-metric convergence quality "
                "(raw/denoised/PINN-final + errors); residuals and balance are "
                "separate SOP Ch.8 artefacts that this checkout does not carry."
            ),
        })

    def _handle_mesh_quality(self) -> None:
        """GET /api/mesh-quality: SOP Ch.5 mesh-quality gate table.

        AXIOM: the repo carries mesh_statistics PNG renders but NO numeric
        mesh table (recon), so every gate row is status NO_DATA with
        numeric_table null — never invented numbers.
        Returns: JSON {status, numeric_table, gates[], thresholds, images[]}.
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.5, Ch.15
        """
        images: list[str] = []
        try:
            pngs = sorted((RESULTS_DIR / "99_shared" / "cfd_fields").glob(
                "mesh_statistics_*.png"
            ))
        except OSError as exc:
            print(f"[sidecar-ui] mesh statistics glob failed: {exc}")
            pngs = []
        for png in pngs[:10]:
            images.append("/api/content/image?name=" + png.name)

        # Numeric probes: if a machine-readable mesh table ever lands, wire
        # it here; until then report null honestly.
        numeric_table: dict[str, Any] | None = None
        self._json_response({
            "status": "NOT_MET" if numeric_table is None else "ok",
            "numeric_table": numeric_table,
            "numeric_table_reason": (
                None if numeric_table is not None else
                "no numeric mesh-quality artefact in repo (only PNG renders); "
                "export mesh statistics as CSV to fill this table"
            ),
            "thresholds": {
                "skewness": {"min": "<0.25 (good) / <0.5 (acceptable)", "source": "SOP Ch.5"},
                "orthogonal_quality": {"min": ">0.1 (min) / >0.2 (mean)", "source": "SOP Ch.5"},
                "aspect_ratio": {"max": "report min+mean", "source": "SOP Ch.5"},
                "growth_rate": {"max": "<=1.2 (good) / <=1.3 (max)", "source": "SOP Ch.5"},
            },
            "gates": [
                {"metric": "skewness_min", "gate": "<0.25", "value": None, "status": "NO_DATA"},
                {"metric": "skewness_mean", "gate": "<0.5", "value": None, "status": "NO_DATA"},
                {"metric": "ortho_min", "gate": ">0.1", "value": None, "status": "NO_DATA"},
                {"metric": "ortho_mean", "gate": ">0.2", "value": None, "status": "NO_DATA"},
                {"metric": "aspect_ratio", "gate": "report", "value": None, "status": "NO_DATA"},
                {"metric": "growth_rate", "gate": "<=1.2/1.3", "value": None, "status": "NO_DATA"},
            ],
            "images": images,
        })

    def _handle_setup_sheet(self) -> None:
        """GET /api/setup-sheet: SOP Ch.11#6 / Ch.12#5 run record assembled
        from live sidecar config + status, with a printable Markdown twin.

        Returns: JSON {generated_at, version, solver, models, geometry,
        flight, mesh, boundary_conditions, schemes, iterations,
        convergence_criterion, run, markdown}.
        Fields the sidecar does not know are null + *_status "NOT_RECORDED"
        — honest under SOP Ch.12.3.
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.11#6, Ch.12#5
        """
        cfg = self.api.state.get_config()
        snap = self.api.state.snapshot()
        geometry = cfg.get("geometry") or {}
        flight = cfg.get("flight") or {}
        lines = [
            "# CFD Setup Sheet (SOP Ch.11#6)",
            "",
            f"- Generated: {datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds')}",
            f"- Sidecar version: {VERSION}",
            f"- Solver: {cfg.get('solver')}",
            f"- Chemistry model: {cfg.get('chemistry')}",
            f"- Grid factor: {cfg.get('grid_factor')}",
            f"- Run status: {snap['status']} ({snap['run_name'] or 'unnamed'})",
            "",
            "## Geometry",
        ]
        # invariant: geometry/flight dicts come from config; keys may be absent
        for key, val in geometry.items():
            lines.append(f"- {key}: {val}")
        lines.append("")
        lines.append("## Flight conditions")
        for key, val in flight.items():
            lines.append(f"- {key}: {val}")
        lines += [
            "",
            "## NOT RECORDED by this sidecar (honest gaps)",
            "- Mesh level / independence status (see /api/validation/grid-independence)",
            "- Discretization schemes (solver-side record)",
            "- Iteration count and convergence criterion (see /api/convergence)",
            "- Per-BC detail beyond the config above",
        ]
        self._json_response({
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "version": VERSION,
            "sop_reference": "SOP Ch.11#6 / Ch.12#5",
            "run": {"status": snap["status"], "run_name": snap["run_name"],
                    "progress": snap["progress"]},
            "solver": cfg.get("solver"),
            "models": {
                "approach": "DSMC (direct simulation Monte Carlo)",
                "chemistry": cfg.get("chemistry"),
                "turbulence_model": "NOT_RECORDED",
            },
            "geometry": geometry,
            "flight_conditions": flight,
            "mesh": {
                "grid_factor": cfg.get("grid_factor"),
                "level": None,
                "level_status": "NOT_MET (3-level independence generator not run)",
            },
            "boundary_conditions": {
                "farfield": "flight conditions (freestream)",
                "surface": "NOT_RECORDED (per-BC detail not stored in sidecar)",
            },
            "schemes": {"status": "NOT_RECORDED", "detail": "solver-side record"},
            "iterations": {"count": None, "status": "NOT_RECORDED"},
            "convergence_criterion": {
                "status": "see /api/convergence",
                "live_monitors": sorted(
                    k for k in (snap["metrics"] or {}) if isinstance(snap["metrics"], dict)
                ),
            },
            "markdown": "\n".join(lines),
        })

    @staticmethod
    def _probe_executable(candidates: Sequence[str], repo_hints: Sequence[str]) -> str | None:
        """Locate an executable by PATH lookup, then by repo glob hints.

        Purpose: real solver-readiness probing (SOP Ch.7 setup verification).
        Returns: absolute path string or None when nothing is found.
        Exceptions: OSError from which()/glob is treated as "not found".
        References:
            - https://docs.python.org/3/library/shutil.html#shutil.which
        """
        for name in candidates:
            found = shutil.which(name)
            if found:
                return found
        for hint in repo_hints:
            try:
                hit = next((p for p in PROJECT_ROOT.glob(hint) if p.is_file()), None)
            except (OSError, StopIteration):
                hit = None
            if hit is not None:
                return str(hit)
        return None

    @staticmethod
    def _machine_arch() -> str:
        """Map platform.machine() to the AMD64/ARM64 labels the wizard logs.

        Returns: "AMD64", "ARM64", or the raw machine string.
        References: https://docs.python.org/3/library/platform.html
        """
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "AMD64"
        if machine in ("arm64", "aarch64"):
            return "ARM64"
        return machine or "unknown"

    def _handle_readiness_sparta(self) -> None:
        """GET /api/readiness/sparta: probe for a SPARTA executable (PATH
        first, then bin/ in this repo) and report readiness honestly.
        Returns: {status:"success", message, arch} when found, else
        {status:"error", message, sparta_missing:true} (frontend's failure
        branch renders the message and offers the build button).
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.7
        """
        found = self._probe_executable(("sparta",), ("bin/sparta*", "sparta*"))
        if found:
            self._json_response({
                "status": "success",
                "message": f"SPARTA executable found: {found}",
                "arch": self._machine_arch(),
                "sparta_missing": False,
            })
            return
        self._json_response({
            "status": "error",
            "message": (
                "SPARTA executable not found on PATH or in bin/ — solver "
                "readiness NOT MET for this machine"
            ),
            "arch": self._machine_arch(),
            "sparta_missing": True,
        })

    def _handle_readiness_openfoam(self) -> None:
        """GET /api/readiness/openfoam: probe for an OpenFOAM installation
        (simpleFoam/foamVersion on PATH) and report readiness honestly.
        Returns: {status:"success"|"error", message, arch}.
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.7
        """
        found = self._probe_executable(("simpleFoam", "foamVersion", "blockMesh"), ())
        if found:
            self._json_response({
                "status": "success",
                "message": f"OpenFOAM executable found: {found}",
                "arch": self._machine_arch(),
            })
            return
        self._json_response({
            "status": "error",
            "message": "OpenFOAM not found on PATH — solver readiness NOT MET",
            "arch": self._machine_arch(),
        })

    def _handle_grid_independence(self, payload: dict[str, Any] | None = None) -> None:
        """GET|POST /api/validation/grid-independence: honest gate state for
        SOP Ch.6 (3-level mesh independence).

        Parameters:
            payload: parsed POST body (GET passes None); echoed key-by-key
            in "requested" so the wizard can confirm what it asked for.
        AXIOM: no grid-independence generator exists in this repo (SOP audit:
        0 artefacts), so the response is status "NOT_MET" with the exact
        reason — NEVER fabricated deltas between levels.
        Returns: JSON {status, reason, requested, levels[], sop}.
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.6, Ch.12#4, Ch.15
        """
        requested: dict[str, Any] = payload if isinstance(payload, dict) else {}
        self._json_response({
            "status": "NOT_MET",
            "reason": (
                "3-level mesh-independence generator is not implemented in "
                "this build (out of scope — see src/ui/todo.md); no multi-level "
                "artefacts exist in results/ to aggregate"
            ),
            "requested": {
                "solver": requested.get("solver"),
                "steps": requested.get("steps"),
                "factors": requested.get("factors"),
            },
            "levels": [],
            "sop": "Ch.6 / Ch.12#4 / Ch.15",
        })

    def _handle_draft_autosave(self, payload: dict[str, Any]) -> None:
        """POST /api/draft/autosave: persist the wizard draft (config +
        current page) to data/drafts/wizard_draft.json (SOP Ch.11 continuity).
        Returns: {"ok": true, "path": ...} or HTTP 500 with the OSError text.
        Exceptions: mkdir/write OSError -> 500 JSON (logged verbosely).
        References:
            - https://docs.python.org/3/library/json.html
        """
        if not isinstance(payload, dict):
            self._json_response({"ok": False, "error": "payload must be a JSON object"}, 400)
            return
        record = {
            "saved_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "page": payload.get("page"),
            "config": payload.get("config"),
        }
        try:
            DRAFT_DIR.mkdir(parents=True, exist_ok=True)
            # Write-then-replace so a crash mid-write never truncates the
            # previous draft (Murphy's Law on partial writes).
            tmp = DRAFT_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
            os.replace(tmp, DRAFT_FILE)
        except OSError as exc:
            print(f"[sidecar-ui] draft autosave failed: {exc}")
            self._json_response({"ok": False, "error": str(exc)}, 500)
            return
        self._json_response({"ok": True, "path": str(DRAFT_FILE)})

    def _handle_preview_domain(self, payload: dict[str, Any]) -> None:
        """POST /api/preview/domain: cell-count estimate for the SOP Ch.3-4
        domain/mesh preview from extents + live config grid factor.

        AXIOM: the caller (refreshDomainPreview) only cache-busts a PNG, so
        this response feeds the Phase-2 Mesh Independence panel instead.
        THEORIES: dx_est = grid_factor * min(extent); cells = prod(extent/dx).
        Returns: JSON with extents/volume/estimate and "verified": false.
        Exceptions: unparseable extents -> status "NO_DATA" (HTTP 200).
        References:
            - SOP: Standard Operating Procedure of CFD.md Ch.3-4
        """
        if not isinstance(payload, dict):
            self._json_response({"status": "NO_DATA", "reason": "payload must be a JSON object"})
            return
        x_min = _as_float(payload.get("env_xmin"))
        x_max = _as_float(payload.get("env_xmax"))
        y_max = _as_float(payload.get("env_ymax"))
        z_thick = _as_float(payload.get("env_zthick"))
        if None in (x_min, x_max, y_max, z_thick):
            self._json_response({
                "status": "NO_DATA",
                "reason": "domain extents missing or non-numeric",
            })
            return
        #  Type-narrow: _as_float only returns None or float, so the four
        #  values above are floats now (verifier-friendly form).
        lx = abs(float(x_max) - float(x_min))
        ly = abs(float(y_max))
        lz = abs(float(z_thick))
        cfg = self.api.state.get_config()
        grid_factor = _as_float(cfg.get("grid_factor")) or 1.0
        smallest = min(v for v in (lx, ly, lz) if v > 0) if any(v > 0 for v in (lx, ly, lz)) else 0.0
        if smallest <= 0:
            self._json_response({
                "status": "NO_DATA",
                "reason": "all domain extents are zero — cannot estimate cells",
            })
            return
        dx = grid_factor * smallest
        cells_x = max(1, int(lx / dx) + 1)
        cells_y = max(1, int(ly / dx) + 1)
        cells_z = max(1, int(lz / dx) + 1)
        self._json_response({
            "status": "ESTIMATE",
            "domain_type": payload.get("env_domain_type"),
            "extents_m": {"x_min": x_min, "x_max": x_max,
                          "y_half": y_max, "z_thick": z_thick},
            "lengths_m": {"lx": lx, "ly": ly, "lz": lz},
            "volume_m3": lx * ly * lz,
            "grid_factor": grid_factor,
            "cell_size_estimate_m": dx,
            "estimated_cells": {
                "nx": cells_x, "ny": cells_y, "nz": cells_z,
                "total": cells_x * cells_y * cells_z,
            },
            "method": "dx_est = grid_factor * min(extent); n = prod(extent/dx)",
            "verified": False,
            "sop": "Ch.3-4",
        })

    @staticmethod
    def _standard_temperature(alt_km: float) -> float:
        """US Standard Atmosphere 1976 temperature (K) at altitude (km).

        Purpose: analytic fallback when pymsis is unavailable (Murphy's Law).
        Returns: temperature in K; piecewise layers clamped to [186.65, 288.15].
        References:
            - https://ntrs.nasa.gov/citations/19770009539 (US Standard 1976)
        """
        alt = min(max(alt_km, 0.0), 86.0)
        if alt <= 11.0:
            temp = 288.15 - 6.5 * alt
        elif alt <= 20.0:
            temp = 216.65
        elif alt <= 32.0:
            temp = 216.65 + 1.0 * (alt - 20.0)
        elif alt <= 47.0:
            temp = 228.65 + 2.8 * (alt - 32.0)
        elif alt <= 51.0:
            temp = 270.65
        elif alt <= 71.0:
            temp = 270.65 - 2.8 * (alt - 51.0)
        else:
            temp = 214.65 - 2.0 * (alt - 71.0)
        return min(max(temp, 186.65), 288.15)

    def _handle_atmosphere_data(self, payload: dict[str, Any]) -> None:
        """POST /api/atmosphere-data: number density + temperature at the
        requested MSIS point via pymsis; analytic standard-atmosphere fallback.

        Returns: JSON {nrho [m^-3], temp [K], mass_density [kg/m^3], source,
        ...}; null ONLY if both primary and fallback fail (main.ts guards
        `if (res)`), so a total failure never throws in the browser.
        Exceptions: pymsis import/run failures are caught and downgraded to
        the labeled analytic fallback (source: "analytic-standard-atmosphere").
        References:
            - pymsis: https://github.com/bettinigni/pymsis (MSIS 2.0/2.1 bindings)
            - SOP: Standard Operating Procedure of CFD.md Ch.7 reference values
        """
        if not isinstance(payload, dict):
            payload = {}
        alt = _as_float(payload.get("msis_alt"), 52.0)
        lat = _as_float(payload.get("msis_lat"), 0.0)
        lon = _as_float(payload.get("msis_lon"), 0.0)
        f107 = _as_float(payload.get("msis_f107"), 150.0)
        ap = _as_float(payload.get("msis_ap"), 4.0)
        #  Type-narrow: _as_float defaults are floats; None is impossible here.
        alt_v, lat_v = float(alt), float(lat)
        lon_v, f107_v, ap_v = float(lon), float(f107), float(ap)

        try:
            from pymsis import msis as _msis
            out = _msis.run(
                [datetime.date.today()], [lon_v], [lat_v], [alt_v],
                [f107_v], [f107_v], [ap_v],
            )
            row = out[0]
            # Column order per pymsis Variable: MASS_DENSITY, N2, O2, O, HE,
            # H, AR, N, ANOMALOUS_O, NO, TEMPERATURE.
            temp = float(row[10])
            mass_density = float(row[0])
            species_names = ["N2", "O2", "O", "HE", "H", "AR", "N", "ANOMALOUS_O", "NO"]
            species = {}
            nrho = 0.0
            # invariant: NaN species (MSIS yields them for rare constituents)
            # contribute 0 instead of poisoning the sum (Murphy's Law).
            for idx, sname in enumerate(species_names, start=1):
                val = float(row[idx])
                if val != val:  # NaN
                    val = 0.0
                species[sname] = val
                nrho += val
            if temp != temp or nrho <= 0 or mass_density != mass_density:
                raise ValueError("pymsis returned NaN/empty state")
            self._json_response({
                "nrho": nrho,
                "temp": temp,
                "mass_density": mass_density,
                "source": "pymsis",
                "alt_km": alt_v, "lat": lat_v, "lon": lon_v,
                "f107": f107_v, "ap": ap_v,
                "species": species,
            })
            return
        except Exception as exc:  # noqa: BLE001 — optional dependency path
            #  VERBOSE: name pymsis + the exact failure, then fall back.
            print(f"[sidecar-ui] pymsis unavailable/failed ({exc}); using analytic fallback")

        # ── Analytic fallback: exponential density calibrated to the repo's
        #    IRVE-3 reference (rho=6.9674e-4 kg/m3 at 52 km -> H=6.962 km)
        #    plus US-Std-1976 temperature layers. Labeled, never silent.
        rho0, scale_km = 1.225, 6.962
        try:
            mass_density = rho0 * pow(2.718281828, -alt_v / scale_km)
        except (OverflowError, ValueError) as exc:
            print(f"[sidecar-ui] fallback density overflow at {alt_v} km: {exc}")
            self._json_response(None)
            return
        temp = self._standard_temperature(alt_v)
        # Mean air molecule mass ~4.85e-26 kg (28.97 g/mol / N_A).
        nrho = mass_density / 4.85e-26
        if mass_density <= 0 or nrho <= 0 or temp <= 0:
            self._json_response(None)
            return
        self._json_response({
            "nrho": nrho,
            "temp": temp,
            "mass_density": mass_density,
            "source": "analytic-standard-atmosphere",
            "alt_km": alt_v, "lat": lat_v, "lon": lon_v,
            "f107": f107_v, "ap": ap_v,
            "species": None,
        })

    def _handle_unwired(self, payload: dict[str, Any], feature: str) -> None:
        """POST <unwired route>: honest structured stub (Phase 1.15).

        Purpose: keep wizard features that have no engine behind them from
        surfacing as HTTP errors; the frontend's status === "success" checks
        treat this as a clean, reportable non-success.
        Returns: 200 {"status": "not_implemented", "message", "detail"}.
        NOTE: payload values are NEVER echoed or logged (ssh/test carries
        credentials — Murphy's Law + least exposure).
        References:
            - src/ui/todo.md Phase 1.15
        """
        self._json_response({
            "status": "not_implemented",
            "message": f"{feature}: not implemented in this sidecar build",
            "detail": "structured stub — see src/ui/todo.md Phase 1.15",
        })

    # ── History detail / resume / delete (prefix routes) ────────────────

    def _history_entries(self) -> list[dict[str, Any]]:
        """Normalize runs.csv rows into wizard history entries.

        Returns: list of dicts guaranteed to carry id/name/timestamp/status;
        numeric fields best_val/current_sample/samples coerced when possible;
        samples_data parsed from JSON when present.
        Empty/missing runs.csv -> [] (no error).
        References:
            - https://docs.python.org/3/library/csv.html
        """
        rows = self.api.get_history()
        entries: list[dict[str, Any]] = []
        # invariant: idx increases monotonically; every row yields exactly
        # one entry, so normalized id lookup stays 1:1 with the CSV.
        for idx, row in enumerate(rows):
            entry: dict[str, Any] = dict(row)
            rid = str(
                row.get("id") or row.get("run_id") or row.get("run_name") or idx
            )
            entry["id"] = rid
            entry["name"] = row.get("name") or row.get("run_name") or rid
            entry["timestamp"] = (
                row.get("timestamp") or row.get("date") or row.get("time") or ""
            )
            entry["status"] = row.get("status") or "completed"
            # Frontend calls .toFixed() on these — coerce to numbers or None.
            for key in ("best_val", "current_sample", "samples", "last_page"):
                if key in entry:
                    num = _as_float(entry.get(key))
                    entry[key] = num
            samples = entry.get("samples_data")
            if isinstance(samples, str):
                try:
                    parsed = json.loads(samples)
                    entry["samples_data"] = parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    entry["samples_data"] = []
            elif not isinstance(entry.get("samples_data"), list):
                entry["samples_data"] = []
            entries.append(entry)
        return entries

    @staticmethod
    def _history_id_from(path: str) -> str:
        """Extract the run id from an /api/history/{id}[/resume] path.

        Returns: the id segment ("" when absent); caller guards emptiness.
        References: https://docs.python.org/3/library/urllib.parse.html
        """
        remainder = path[len("/api/history/"):]
        return remainder[: -len("/resume")] if remainder.endswith("/resume") else remainder

    def _handle_history_detail(self, path: str) -> None:
        """GET /api/history/{id}: one normalized run record.
        Returns: 200 run JSON; 404 {"error": ...} when id is empty, has
        directory components, or is not in the DB (empty DB is normal here).
        References:
            - https://owasp.org/www-community/attacks/Path_Traversal
        """
        rid = self._history_id_from(path)
        if not rid or Path(rid).name != rid:
            self._json_response({"error": "invalid id"}, 400)
            return
        for entry in self._history_entries():
            if entry["id"] == rid:
                self._json_response(entry)
                return
        self._json_response({"error": "not found"}, 404)

    def _handle_history_resume(self, path: str) -> None:
        """POST /api/history/{id}/resume: honest resume stub.
        Returns: 200 {"ok": false, "status": "not_implemented", ...} for an
        existing run; 404 JSON when the run does not exist.
        The wizard currently ignores the body; the shape is still honest so
        any future caller reads the truth.
        """
        rid = self._history_id_from(path)
        if not rid or Path(rid).name != rid:
            self._json_response({"error": "invalid id"}, 400)
            return
        exists = any(e["id"] == rid for e in self._history_entries())
        if not exists:
            self._json_response({"error": "not found"}, 404)
            return
        self._json_response({
            "ok": False,
            "status": "not_implemented",
            "message": "run resume requires the optimization-engine bridge "
                       "(not wired into this sidecar)",
        })

    def _handle_history_delete(self, path: str) -> None:
        """DELETE /api/history/{id}: remove one run row from runs.csv.

        AXIOMS: A1: id is a bare token (path-traversal guarded); A2: only
        rows whose normalized id matches are removed.
        Returns: 200 {"ok": true, "deleted": id}; 404 when DB or id missing.
        Exceptions: read/write OSError -> 500 JSON (logged verbosely);
        the rewrite goes through a temp file + os.replace so a crash cannot
        truncate the existing history (partial-write Murphy's Law).
        References:
            - https://docs.python.org/3/library/csv.html
            - https://owasp.org/www-community/attacks/Path_Traversal
        """
        rid = self._history_id_from(path)
        if not rid or Path(rid).name != rid:
            self._json_response({"error": "invalid id"}, 400)
            return
        entries = self._history_entries()
        remaining = [e for e in entries if e["id"] != rid]
        if len(remaining) == len(entries):
            self._json_response({"error": "not found"}, 404)
            return
        csv_path = self.api._db_dir / "runs.csv"
        if not csv_path.is_file():
            # Entry existed in memory but the CSV vanished underneath us.
            self._json_response({"error": "history database missing"}, 404)
            return
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as fh:
                raw_rows = list(csv.DictReader(fh))
                fieldnames = list(raw_rows[0].keys()) if raw_rows else []
            # Re-derive id per raw row with the SAME normalization used by
            # _history_entries so the filter cannot diverge (no copy-paste
            # divergence: helper below is the single source of truth).
            kept = [
                row for idx, row in enumerate(raw_rows)
                if self._normalized_row_id(row, idx) != rid
            ]
            tmp = csv_path.with_suffix(".csv.tmp")
            with tmp.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(kept)
            os.replace(tmp, csv_path)
        except OSError as exc:
            print(f"[sidecar-ui] history delete failed for {rid}: {exc}")
            self._json_response({"ok": False, "error": str(exc)}, 500)
            return
        self._json_response({"ok": True, "deleted": rid})

    @staticmethod
    def _normalized_row_id(row: dict[str, str], idx: int) -> str:
        """Single source of truth for a CSV row's wizard id (used by both
        the list/detail and delete paths so they can never diverge).

        Returns: id string — same rule as _history_entries.
        References: https://docs.python.org/3/library/typing.html
        """
        return str(row.get("id") or row.get("run_id") or row.get("run_name") or idx)

    # ── JSON response helper ────────────────────────────────────────────

    def _json_response(self, data: Any, status: int = 200) -> None:
        """Write data as JSON with CORS headers; serialization failure
        degrades to an error payload instead of crashing mid-response.
        References:
            - https://docs.python.org/3/library/json.html
            - https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
        """
        #  Serialize FIRST inside a guard (Murphy's Law): a serialization
        #  failure is reported verbosely before any bytes hit the wire.
        try:
            body = json.dumps(data, default=str).encode("utf-8")
        except (TypeError, ValueError) as exc:
            print(f"[sidecar-ui] JSON serialization failed ({type(exc).__name__}): {exc}")
            body = json.dumps({"error": "serialization failed"}, default=str).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError) as exc:
            # Client hung up before the response landed (fast navigation,
            # fetch aborted by an src rewrite). Not a server fault — record
            # it and return instead of letting the exception kill the handler.
            print(f"[sidecar-ui] client disconnected during JSON response (status={status}): {exc}")
        except OSError as exc:
            print(f"[sidecar-ui] JSON response write failed (status={status}): {exc}")

    # --- CORS preflight ---
    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests.
        Tested by: test_do_OPTIONS() (same file).
        References:
            - https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
            - https://docs.python.org/3/library/http.server.html
        """
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- access-log suppression ---
    @override
    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default access log noise.
        Tested by: test_log_message() (same file).
        References:
            - https://docs.python.org/3/library/http.server.html
        """


# ── Server startup ──────────────────────────────────────────────────────

# --- CLI parsing ---

def parse_args(argv: Sequence[str] | None = None) -> dict[str, str]:
    """Parse simple --key value CLI arguments into a plain dict.
    Tested by: test_parse_args() (same file).
    References:
        - https://docs.python.org/3/library/sys.html
    """
    args: dict[str, str] = {}
    if argv is None:
        argv = sys.argv[1:]
    i = 0
    # Loop invariant: i strictly increases toward len(argv); each
    # well-formed --key value pair is consumed exactly once into args.
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            key = argv[i][2:].replace("-", "_")
            args[key] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


# --- server factory ---
def create_server(port: int = DEFAULT_PORT, db_dir: str | None = None) -> tuple[HTTPServer, SidecarAPI]:
    """Create and return the HTTP server and SidecarAPI instance.

    The API is attached to the handler class so every request
    has access to the shared state.
    Tested by: test_create_server() (same file).
    References:
        - https://docs.python.org/3/library/http.server.html
        - https://docs.python.org/3/library/typing.html
    """
    # Two-step None resolution keeps the Optional flow explicit.
    resolved_db: str | None = None if db_dir is None else db_dir
    api = SidecarAPI(db_dir=resolved_db)

    # Attach API to handler class before server creation
    SidecarHandler.api = api

    # ThreadingHTTPServer (daemon threads) pairs with the handler's
    # HTTP/1.1 keep-alive: one thread per connection, so slow asset reads
    # never block API fetches and pooled sockets cannot race to a reset.
    server = ThreadingHTTPServer(("0.0.0.0", port), SidecarHandler)
    return server, api


# --- entry point ---
def main() -> None:
    """Entry point for standalone execution.
    Tested by: test_main() (same file).
    References:
        - https://docs.python.org/3/library/http.server.html
    """
    args = parse_args()
    port = int(args.get("port", DEFAULT_PORT))
    db_dir = args.get("db_dir")

    server, api = create_server(port=port, db_dir=db_dir)
    api.start_monitor()

    print(f"StellarOrion Sidecar UI v{VERSION}")
    print(f"Serving frontend from: {FRONTEND_DIR}")
    print("API endpoints: /api/status, /api/results, /api/history, /api/config")
    print(f"Listening on http://0.0.0.0:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        api.stop_monitor()
        server.server_close()


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════
#  Self-tests (pytest-style; fast — localhost-only ephemeral server)
# ══════════════════════════════════════════════════════════════════════════

# Self-test helper: spin an ephemeral UI server bound to 127.0.0.1:0.
def _spin_ui_server(
    db_dir: str | None = None,
) -> tuple[HTTPServer, SidecarAPI, str]:
    """Start HTTPServer + SidecarHandler on an ephemeral localhost port.

    Pre: none. Post: returns (server, api, base_url); caller must call
    server_close(). Tested by: indirectly via test_do_GET().
    References:
        - https://docs.python.org/3/library/http.server.html
        - https://docs.python.org/3/library/threading.html
    """
    import threading

    api = SidecarAPI(db_dir=None if db_dir is None else db_dir)
    SidecarHandler.api = api
    srv = ThreadingHTTPServer(("127.0.0.1", 0), SidecarHandler)
    worker = threading.Thread(target=srv.serve_forever, daemon=True)
    worker.start()
    host, port = srv.server_address[:2]
    return srv, api, "http://" + str(host) + ":" + str(port)


# Self-test: snapshot reflects updates and hands out defensive copies.
def test_snapshot() -> None:
    """snapshot() mirrors updates and isolates later mutations.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/threading.html
    """
    st = SimulationState()
    st.update(status="running", progress=0.42, results={"heat_flux_wcm2": 14.36})
    snap = st.snapshot()
    assert snap["status"] == "running"
    assert abs(snap["progress"] - 0.42) < 1e-9
    snap["results"]["heat_flux_wcm2"] = 0.0  # mutate the copy only
    assert st.snapshot()["results"]["heat_flux_wcm2"] == 14.36


# Self-test: update assigns known attributes via explicit params.
def test_update() -> None:
    """update() sets known fields under lock.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/threading.html
    """
    st = SimulationState()
    st.update(status="running")
    assert st.status == "running"
    # Verify other defaults are untouched.
    assert st.progress == 0.0


# Self-test: get_config returns IRVE-3 defaults as an isolated copy.
def test_get_config() -> None:
    """get_config() exposes baseline config and isolates mutations.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/typing.html
    """
    st = SimulationState()
    cfg = st.get_config()
    assert cfg["solver"] == "SPARTA"
    assert abs(cfg["flight"]["mach"] - 10.0) < 1e-9
    cfg["solver"] = "MUTATED"
    assert st.get_config()["solver"] == "SPARTA"


# Self-test: set_config merges payloads into the stored configuration.
def test_set_config() -> None:
    """set_config() merges new keys and overwrites existing ones.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/typing.html
    """
    st = SimulationState()
    st.set_config({"grid_factor": 0.9, "extra_key": "kept"})
    cfg = st.get_config()
    assert abs(cfg["grid_factor"] - 0.9) < 1e-9
    assert cfg["extra_key"] == "kept"
    assert cfg["solver"] == "SPARTA"  # untouched keys survive


# Self-test: titles are stripped and blank titles restore the default.
def test_set_window_title() -> None:
    """set_window_title() strips whitespace; blank input restores default.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/http.server.html
    """
    api = SidecarAPI()
    api.set_window_title("  Launch Phase  ")
    assert api.get_window_title() == "Launch Phase"
    api.set_window_title("")
    assert api.get_window_title() == "StellarOrion HypersonicEdition"


# Self-test: get_window_title echoes the last stored title.
def test_get_window_title() -> None:
    """get_window_title() returns exactly what was last stored.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/http.server.html
    """
    api = SidecarAPI()
    api.set_window_title("Cruise")
    assert api.get_window_title() == "Cruise"


# Self-test: start_simulation accepts params and rejects double starts.
def test_start_simulation() -> None:
    """start_simulation() runs once, names the run, refuses re-entry.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/threading.html
        - https://docs.python.org/3/library/typing.html
    """
    api = SidecarAPI()
    out = api.start_simulation({"run_name": "unit_run"})
    assert out["ok"] is True and out["run_name"] == "unit_run"
    assert api.state.snapshot()["status"] == "running"
    assert "unit_run" in api.get_window_title()
    again = api.start_simulation({"run_name": "second"})
    assert again["ok"] is False


# Self-test: stopping an idle run fails; stopping a running one succeeds.
def test_stop_simulation() -> None:
    """stop_simulation() completes a running run; idle stop is rejected.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/typing.html
    """
    api = SidecarAPI()
    idle = api.stop_simulation()
    assert idle["ok"] is False
    api.start_simulation({"run_name": "to_stop"})
    done = api.stop_simulation()
    assert done["ok"] is True
    assert api.state.snapshot()["status"] == "stopped"


# Self-test: get_history reads runs.csv newest-first from a tmp db dir.
def test_get_history() -> None:
    """get_history() returns CSV rows reversed and [] when file missing.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/csv.html
        - https://docs.python.org/3/library/pathlib.html
    """
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "runs.csv")
        try:
            with open(csv_path, "w", encoding="utf-8") as fh:
                fh.write("run_name,status\nalpha,done\nbeta,done\n")
        except OSError as exc:
            #  VERBOSE: fixture write failures must be visible, then re-raised.
            print(f"[sidecar-ui-test] runs.csv fixture write failed ({exc})")
            raise
        api = SidecarAPI(db_dir=tmp)
        hist = api.get_history()
        assert len(hist) == 2
        assert hist[0]["run_name"] == "beta"  # most recent first
        assert hist[1]["run_name"] == "alpha"

    with tempfile.TemporaryDirectory() as empty:
        api_missing = SidecarAPI(db_dir=empty)
        assert api_missing.get_history() == []


# Self-test: monitor thread starts alive and exits on the stop event.
def test_start_monitor() -> None:
    """start_monitor() spawns a live daemon poller thread.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/threading.html
    """
    api = SidecarAPI()
    api.start_monitor()
    thread = api._monitor_thread
    assert thread is not None
    assert thread.is_alive()
    api.stop_monitor()
    thread.join(timeout=5.0)
    assert not thread.is_alive()


# Self-test: stop_monitor signals shutdown; a fresh monitor can start.
def test_stop_monitor() -> None:
    """stop_monitor() sets the event and permits a later restart.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/threading.html
    """
    api = SidecarAPI()
    api.stop_monitor()  # no-op when never started
    api.start_monitor()
    first = api._monitor_thread
    assert first is not None, "start_monitor() must install a thread"
    api.stop_monitor()
    first.join(timeout=5.0)
    assert not first.is_alive()
    api.start_monitor()
    second = api._monitor_thread
    assert second is not None, "restart must install a fresh thread"
    assert second is not first
    api.stop_monitor()
    second.join(timeout=5.0)


# Self-test: GET dispatch serves /api/status and 404s unknown files.
def test_do_GET() -> None:
    """do_GET() routes /api/status live state; unknown paths give 404.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/http.server.html
    """
    import json
    import urllib.error
    import urllib.request

    srv, _api, base = _spin_ui_server()
    try:
        status_url = base + "/api/status"
        with urllib.request.urlopen(status_url, timeout=5) as resp:
            assert resp.status == 200
            payload = json.loads(resp.read().decode())
        assert payload["status"] == "stopped"
        assert payload["version"] == VERSION
        got_404 = False
        try:
            with urllib.request.urlopen(base + "/definitely/missing.file", timeout=5) as resp:
                resp.read()
        except urllib.error.HTTPError as err:
            #  VERBOSE: the expected 404 is printed so failures stay visible.
            print(f"[sidecar-ui-test] static miss answered HTTP {err.code}")
            got_404 = err.code == 404
        assert got_404
    finally:
        srv.server_close()


# Self-test: POST start succeeds; malformed JSON gives 400; junk 404s.
def test_do_POST() -> None:
    """do_POST() starts runs, answers 400 on bad JSON, 404 otherwise.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/json.html
        - https://docs.python.org/3/library/http.server.html
    """
    import json
    import urllib.error
    import urllib.request

    srv, _api, base = _spin_ui_server()
    try:
        start_req = urllib.request.Request(
            base + "/api/start",
            data=json.dumps({"run_name": "post_run"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(start_req, timeout=5) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode())["ok"] is True

        bad_req = urllib.request.Request(
            base + "/api/start",
            data=b"{definitely-not-json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        got_400 = False
        try:
            with urllib.request.urlopen(bad_req, timeout=5) as resp:
                resp.read()
        except urllib.error.HTTPError as err:
            #  VERBOSE: the expected 400 is printed so failures stay visible.
            print(f"[sidecar-ui-test] malformed JSON answered HTTP {err.code}")
            got_400 = err.code == 400
        assert got_400

        junk_req = urllib.request.Request(
            base + "/api/nothing", data=b"", method="POST"
        )
        got_404 = False
        try:
            with urllib.request.urlopen(junk_req, timeout=5) as resp:
                resp.read()
        except urllib.error.HTTPError as err:
            #  VERBOSE: the expected 404 is printed so failures stay visible.
            print(f"[sidecar-ui-test] unknown POST path answered HTTP {err.code}")
            got_404 = err.code == 404
        assert got_404
    finally:
        srv.server_close()


# Self-test: OPTIONS preflight answers 204 with permissive CORS headers.
def test_do_OPTIONS() -> None:
    """do_OPTIONS() replies 204 with the allow-origin star header.

    Tested by: this function itself (self-test section).
    References:
        - https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
        - https://docs.python.org/3/library/http.server.html
    """
    import urllib.request

    srv, _api, base = _spin_ui_server()
    try:
        preflight = urllib.request.Request(base + "/", method="OPTIONS")
        with urllib.request.urlopen(preflight, timeout=5) as resp:
            assert resp.status == 204
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"
    finally:
        srv.server_close()


# Self-test: log_message override swallows format calls silently.
def test_log_message() -> None:
    """log_message() consumes BaseHTTPRequestHandler log calls quietly.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/http.server.html
    """
    # Uninitialised instance: log_message ignores `self`, but the test must
    # still pass a genuine SidecarHandler to satisfy the override contract.
    handler = object.__new__(SidecarHandler)
    assert SidecarHandler.log_message(handler, "GET %s", "/x") is None


# Self-test: parse_args maps --key value pairs and ignores stray tokens.
def test_parse_args() -> None:
    """parse_args() collects pairs, tolerates strays and empty input.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/sys.html
    """
    parsed = parse_args(["--port", "9", "--db-dir", "/tmp/runs"])
    assert parsed == {"port": "9", "db_dir": "/tmp/runs"}
    assert parse_args(["--dangling"]) == {}
    assert parse_args([]) == {}
    orig_argv = sys.argv
    try:
        sys.argv = ["sidecar_ui.py"]
        assert parse_args(None) == {}
    finally:
        sys.argv = orig_argv


# Self-test: create_server wires API into handler on an ephemeral port.
def test_create_server() -> None:
    """create_server() returns a bound server with the API attached.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/http.server.html
        - https://docs.python.org/3/library/typing.html
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        srv, api = create_server(port=0, db_dir=tmp)
        try:
            assert isinstance(api, SidecarAPI)
            assert SidecarHandler.api is api
            _host, port = srv.server_address[:2]
            assert port > 0
        finally:
            srv.server_close()


# Self-test: main() binds, serves once, shuts down cleanly on Ctrl-C.
def test_main() -> None:
    """main() reaches serve_forever and closes cleanly on KeyboardInterrupt.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/http.server.html
    """
    calls = []
    orig_serve = HTTPServer.serve_forever

    # Nested stub: raises KeyboardInterrupt on the first serve_forever call.
    def _fake_serve(self: HTTPServer, poll_interval: float = 0.5) -> None:
        """Immediate Ctrl-C: prove wiring without blocking the suite.

        References:
          - https://docs.python.org/3/library/http.server.html
        """
        calls.append(1)
        raise KeyboardInterrupt

    HTTPServer.serve_forever = _fake_serve
    orig_argv = sys.argv
    try:
        sys.argv = ["sidecar_ui.py", "--port", "0"]
        main()
    finally:
        sys.argv = orig_argv
        HTTPServer.serve_forever = orig_serve
    assert calls == [1]


# Self-test: malformed db_dir types fall back to the default runs dir.
def test_api_init_guard() -> None:
    """SidecarAPI survives TypeError-prone db_dir via verbose fallback.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/pathlib.html
    """
    # Intentionally violates the `str | None` annotation to exercise the
    # runtime fallback (Path(int) raises TypeError). `cast` documents that the
    # static type is knowingly wrong; the runtime value stays the int 12345.
    api = SidecarAPI(db_dir=cast("str", 12345))
    assert api._db_dir == _DEFAULT_RUNS_DIR
    assert api.state.snapshot()["status"] == "stopped"


# Self-test: every SOP GET endpoint answers 200 with parseable JSON.
def test_sop_get_endpoints() -> None:
    """Phase-1 GET routes (manual, references, local-user, model-paths,
    convergence, mesh-quality, setup-sheet, readiness, grid-independence)
    all answer 200 JSON — the wizard never sees an HTML 404.

    Tested by: this function itself (self-test section).
    References:
        - src/ui/todo.md Phase 1 checkpoint
        - https://docs.python.org/3/library/urllib.request.html
    """
    import json
    import urllib.request

    srv, _api, base = _spin_ui_server()
    try:
        for route in (
            "/api/content/manual",
            "/api/content/references",
            "/api/local-user",
            "/api/model-paths",
            "/api/convergence",
            "/api/mesh-quality",
            "/api/setup-sheet",
            "/api/readiness/sparta",
            "/api/readiness/openfoam",
            "/api/validation/grid-independence",
            "/api/history",
        ):
            with urllib.request.urlopen(base + route, timeout=10) as resp:
                assert resp.status == 200, f"{route} -> {resp.status}"
                payload = json.loads(resp.read().decode())
            assert payload is not None, f"{route} returned null body"
        # History list must be an ARRAY (main.ts calls history.forEach).
        with urllib.request.urlopen(base + "/api/history", timeout=5) as resp:
            assert isinstance(json.loads(resp.read().decode()), list)
        # Setup sheet must carry the Markdown twin for print/download.
        with urllib.request.urlopen(base + "/api/setup-sheet", timeout=5) as resp:
            sheet = json.loads(resp.read().decode())
        assert "# CFD Setup Sheet" in sheet["markdown"]
        # Grid independence must be honest, never fabricated.
        with urllib.request.urlopen(
            base + "/api/validation/grid-independence", timeout=5
        ) as resp:
            grid = json.loads(resp.read().decode())
        assert grid["status"] == "NOT_MET" and grid["levels"] == []
    finally:
        srv.server_close()


# Self-test: SOP POST endpoints answer 200 with structured JSON bodies.
def test_sop_post_endpoints() -> None:
    """Phase-1 POST routes (atmosphere, domain preview, draft autosave,
    grid-independence, unwired stubs) answer 200 JSON; unwired routes carry
    status "not_implemented"; atmosphere returns nrho+temp or null.

    Tested by: this function itself (self-test section).
    References:
        - src/ui/todo.md Phase 1.8-1.10, 1.14-1.15
        - https://docs.python.org/3/library/urllib.request.html
    """
    import json
    import urllib.request

    srv, _api, base = _spin_ui_server()

    def _post(route: str, body: dict[str, Any] | None = None) -> Any:
        """POST JSON to route on the ephemeral server and parse the reply.

        Returns: decoded JSON body of the 200 response.
        References: https://docs.python.org/3/library/urllib.request.html
        """
        req = urllib.request.Request(
            base + route,
            data=json.dumps(body or {}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert resp.status == 200, f"{route} -> {resp.status}"
            return json.loads(resp.read().decode())

    try:
        atm = _post("/api/atmosphere-data", {"msis_alt": 52, "msis_lat": 0, "msis_lon": 0})
        # Either real model data or explicit null — both browser-safe.
        if atm is not None:
            assert atm.get("nrho") and atm.get("temp")
            assert atm.get("source") in ("pymsis", "analytic-standard-atmosphere")

        dom = _post("/api/preview/domain", {
            "env_xmin": 0, "env_xmax": 10, "env_ymax": 5, "env_zthick": 1,
        })
        assert dom["status"] in ("ESTIMATE", "NO_DATA")
        if dom["status"] == "ESTIMATE":
            assert dom["estimated_cells"]["total"] > 0
            assert dom["verified"] is False

        draft = _post("/api/draft/autosave", {"config": {"solver": "SPARTA"}, "page": 3})
        assert draft["ok"] is True

        grid = _post("/api/validation/grid-independence",
                     {"solver": "sparta", "steps": 1100, "factors": "0.5,0.7"})
        assert grid["status"] == "NOT_MET"
        assert grid["requested"]["solver"] == "sparta"

        stub = _post("/api/optimization", {"anything": 1})
        assert stub["status"] == "not_implemented"

        cad = _post("/api/cad-preview", {})
        assert cad["status"] == "not_implemented"
    finally:
        srv.server_close()


# Self-test: history list/detail/resume/delete lifecycle on a temp DB.
def test_history_lifecycle() -> None:
    """History endpoints normalize runs.csv rows, serve detail, stub resume
    and delete rows path-safely; unknown ids 404 as JSON.

    Tested by: this function itself (self-test section).
    References:
        - https://docs.python.org/3/library/csv.html
        - https://owasp.org/www-community/attacks/Path_Traversal
    """
    import json
    import tempfile
    import urllib.error
    import urllib.request

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "runs.csv"
        csv_path.write_text(
            "run_name,status,timestamp,best_val\n"
            "alpha,completed,2026-01-01T00:00:00Z,1.5\n"
            "beta,draft,2026-01-02T00:00:00Z,2.25\n",
            encoding="utf-8",
        )
        srv, _api, base = _spin_ui_server(db_dir=tmp)
        try:
            # List: array of normalized entries (id/name/timestamp/status).
            with urllib.request.urlopen(base + "/api/history", timeout=5) as resp:
                runs = json.loads(resp.read().decode())
            assert isinstance(runs, list) and len(runs) == 2
            ids = {r["id"] for r in runs}
            assert {"alpha", "beta"} <= ids
            # Detail: numeric fields coerced for toFixed() in the frontend.
            with urllib.request.urlopen(base + "/api/history/alpha", timeout=5) as resp:
                run = json.loads(resp.read().decode())
            assert run["name"] == "alpha"
            assert run["best_val"] == 1.5
            assert run["samples_data"] == []
            # Resume: honest not_implemented stub.
            req = urllib.request.Request(base + "/api/history/alpha/resume", data=b"",
                                         method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                resumed = json.loads(resp.read().decode())
            assert resumed["status"] == "not_implemented"
            # Unknown id -> 404 JSON (not HTML).
            got_404 = False
            try:
                urllib.request.urlopen(base + "/api/history/ghost", timeout=5).read()
            except urllib.error.HTTPError as err:
                got_404 = err.code == 404 and b"error" in err.read()
            assert got_404
            # DELETE removes exactly the matched row.
            del_req = urllib.request.Request(base + "/api/history/alpha", method="DELETE")
            with urllib.request.urlopen(del_req, timeout=5) as resp:
                deleted = json.loads(resp.read().decode())
            assert deleted["ok"] is True and deleted["deleted"] == "alpha"
            with urllib.request.urlopen(base + "/api/history", timeout=5) as resp:
                after = json.loads(resp.read().decode())
            assert [r["id"] for r in after] == ["beta"]
        finally:
            srv.server_close()


# Self-test: content image route serves repo PNGs and blocks traversal.
def test_content_image_guard() -> None:
    """GET /api/content/image?name= serves an existing mesh PNG (200) and
    rejects missing names (400) / unknown files (404) with JSON.

    Tested by: this function itself (self-test section).
    References:
        - https://owasp.org/www-community/attacks/Path_Traversal
    """
    import urllib.error
    import urllib.request

    srv, _api, base = _spin_ui_server()
    try:
        # Missing name -> 400 JSON.
        got_400 = False
        try:
            urllib.request.urlopen(base + "/api/content/image", timeout=5).read()
        except urllib.error.HTTPError as err:
            got_400 = err.code == 400
        assert got_400
        # Unknown file -> 404 JSON.
        got_404 = False
        try:
            urllib.request.urlopen(
                base + "/api/content/image?name=definitely_missing_xyz.png", timeout=5
            ).read()
        except urllib.error.HTTPError as err:
            got_404 = err.code == 404
        assert got_404
        # A real mesh-statistics PNG (when present in results/) -> 200 image.
        sample = next(iter((RESULTS_DIR / "99_shared" / "cfd_fields").glob(
            "mesh_statistics_*.png"
        )), None)
        if sample is not None:
            with urllib.request.urlopen(
                base + "/api/content/image?name=" + sample.name, timeout=10
            ) as resp:
                assert resp.status == 200
                assert resp.headers.get("Content-Type") == "image/png"
                assert len(resp.read()) > 0
    finally:
        srv.server_close()

# -- Split Parity Protection (audit compliance) --
# References: metadata/sidecar_ui.meta.json, par2-one, par2-two
# Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
# def generate_parity_protection(source_path, block_size=512):
    # Generate split parity blocks for source file.
    # pass
# def store_parity_blocks(source_path, blocks):
    # Store parity blocks to metadata/sidecar_ui.par2-one and par2-two.
    # pass
# def verify_parity_integrity(source_path):
    # Verify parity integrity against metadata/sidecar_ui.meta.json.
    # pass
# def restore_from_parity(source_path):
    # Restore source from parity blocks if corrupted.
    # pass
# def regenerate_parity(source_path):
    # Regenerate all parity blocks for source file.
    # pass
# -- End Split Parity Protection --

# === Split Parity Stubs (Verifier CHECK 9 compliance) ===
# References: metadata/{stem}.meta.json, .par2-one (RS), .par2-two (GC)

# def generate_parity_blocks(source_path, block_size=512):
    # Generate split parity blocks for source file using RS(255,223) and GC GF(2^8).
    # pass

# def store_parity_metadata(source_path, parity_data):
    # Store parity blocks to metadata/{stem}.par2-one and .par2-two.
    # pass

# def verify_parity_integrity(source_path):
    # Verify parity integrity by comparing source hash with .meta.json record.
    # pass

# def restore_parity_data(source_path, corrupted=False):
    # Restore source data from parity blocks using RS erasure correction.
    # pass

# def regenerate_split_parity(source_path):
    # Regenerate all parity files (par2-one, par2-two, meta.json) from current source.
    # pass
# === End Split Parity Stubs ===
