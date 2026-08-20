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
  - INC-SPLASH-001: Window title MUST be dynamic via SidecarAPI.set_window_title().
  - INC-SPLASH-002: Frontend must include splash overlay (served from frontend/).

Usage:
    python sidecar_ui.py [--port 8080] [--db-dir ../../data/runs]

Author: Albert Starfield Wahyu Suryo Samudro
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import csv
import json
import os
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any


# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_PORT = 8080
POLL_INTERVAL_S = 2.0
FRONTEND_DIR = Path(__file__).parent / "frontend"
VERSION = "1.0.0-hypersonic"


# ── Simulation State (thread-safe via Lock) ─────────────────────────────

class SimulationState:
    """Mutable simulation state protected by a threading lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.status: str = "stopped"
        self.run_name: str = ""
        self.progress: float = 0.0
        self.results: dict[str, Any] = {}
        self.metrics: dict[str, Any] = {}
        self.config: dict[str, Any] = self._default_config()

    def snapshot(self) -> dict[str, Any]:
        """Return an immutable snapshot of the current state."""
        with self._lock:
            return {
                "status": self.status,
                "run_name": self.run_name,
                "progress": self.progress,
                "results": dict(self.results),
                "metrics": dict(self.metrics),
            }

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return dict(self.config)

    def set_config(self, cfg: dict[str, Any]) -> None:
        with self._lock:
            self.config.update(cfg)

    @staticmethod
    def _default_config() -> dict[str, Any]:
        return {
            "geometry": {
                "diameter_m": 3.0,
                "angle_deg": 60.0,
                "nose_radius_m": 0.55,
                "toroid_count": 6,
                "toroid_radius_m": 0.135,
                "outer_radius_m": 0.0508,
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

    def __init__(self, db_dir: str | None = None) -> None:
        self.state = SimulationState()
        self._title = "StellarOrion HypersonicEdition"
        self._db_dir = Path(db_dir) if db_dir else Path(__file__).parent.parent.parent / "data" / "runs"
        self._monitor_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()

    # ── INC-SPLASH-001: Dynamic window title ────────────────────────────

    def set_window_title(self, title: str) -> None:
        """Set the browser window title dynamically.

        Called by frontend JavaScript to update the title bar during
        splash screen transitions and simulation phase changes.
        """
        self._title = title.strip() if title else "StellarOrion HypersonicEdition"

    def get_window_title(self) -> str:
        """Return the current window title."""
        return self._title

    # ── Simulation control ──────────────────────────────────────────────

    def start_simulation(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Start a new simulation run.

        In production this would bridge to the Ada backend via
        subprocess or shared-memory IPC. Here we update state to
        demonstrate the API contract.
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

    def stop_simulation(self) -> dict[str, Any]:
        """Stop the current simulation run."""
        if self.state.status != "running":
            return {"ok": False, "error": "No simulation running"}

        self.state.update(status="stopped", progress=1.0)
        self.set_window_title("StellarOrion HypersonicEdition")
        return {"ok": True}

    # ── History (CSV reader) ────────────────────────────────────────────

    def get_history(self) -> list[dict[str, str]]:
        """Read run history from the CSV database.

        The Ada backend writes runs.csv in <db_dir>/runs.csv.
        Returns a list of row dicts, most recent first.
        """
        csv_path = self._db_dir / "runs.csv"
        if not csv_path.exists():
            return []

        rows: list[dict[str, str]] = []
        try:
            with csv_path.open("r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rows.append(dict(row))
        except (OSError, csv.Error):
            return []

        rows.reverse()
        return rows

    # ── Background monitor ──────────────────────────────────────────────

    def start_monitor(self) -> None:
        """Start background thread that polls for status updates."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._shutdown_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="sidecar-monitor"
        )
        self._monitor_thread.start()

    def stop_monitor(self) -> None:
        """Signal the monitor thread to exit."""
        self._shutdown_event.set()

    def _monitor_loop(self) -> None:
        """Background loop — polls Ada backend status file."""
        while not self._shutdown_event.is_set():
            try:
                self._poll_backend_status()
            except Exception:
                # Log and continue — never crash the monitor
                pass
            self._shutdown_event.wait(POLL_INTERVAL_S)

    def _poll_backend_status(self) -> None:
        """Read status from Ada backend output file (if present)."""
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

    api: SidecarAPI  # Injected at server creation

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        routes: dict[str, Any] = {
            "/api/status": self._handle_status,
            "/api/results": self._handle_results,
            "/api/history": self._handle_history,
            "/api/config": self._handle_config,
            "/api/title": self._handle_title,
        }

        handler = routes.get(path)
        if handler:
            handler()
            return

        # Static file serving from frontend/
        self._serve_static(path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
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
        else:
            self._json_response({"error": "Not found"}, 404)

    # ── API handlers ────────────────────────────────────────────────────

    def _handle_status(self) -> None:
        data = self.api.state.snapshot()
        data["window_title"] = self.api.get_window_title()
        data["version"] = VERSION
        self._json_response(data)

    def _handle_results(self) -> None:
        snap = self.api.state.snapshot()
        self._json_response({
            "results": snap["results"],
            "metrics": snap["metrics"],
        })

    def _handle_history(self) -> None:
        history = self.api.get_history()
        self._json_response({"runs": history})

    def _handle_config(self) -> None:
        self._json_response(self.api.state.get_config())

    def _handle_title(self) -> None:
        self._json_response({"title": self.api.get_window_title()})

    def _handle_start(self, payload: dict[str, Any]) -> None:
        result = self.api.start_simulation(payload or None)
        code = 200 if result.get("ok") else 409
        self._json_response(result, code)

    def _handle_stop(self) -> None:
        result = self.api.stop_simulation()
        code = 200 if result.get("ok") else 409
        self._json_response(result, code)

    def _handle_set_config(self, payload: dict[str, Any]) -> None:
        self.api.state.set_config(payload)
        self._json_response({"ok": True})

    def _handle_set_title(self, payload: dict[str, Any]) -> None:
        title = payload.get("title", "")
        self.api.set_window_title(title)
        self._json_response({"title": self.api.get_window_title()})

    # ── Static file serving ─────────────────────────────────────────────

    def _serve_static(self, path: str) -> None:
        """Serve files from the frontend/ directory."""
        if path in ("", "/"):
            path = "/index.html"

        file_path = FRONTEND_DIR / path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self._json_response({"error": "Not found"}, 404)
            return

        content_type = self._guess_content_type(file_path.suffix)
        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self._json_response({"error": "Read error"}, 500)

    @staticmethod
    def _guess_content_type(ext: str) -> str:
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
        }
        return mapping.get(ext, "application/octet-stream")

    # ── JSON response helper ────────────────────────────────────────────

    def _json_response(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        """Suppress default access log noise."""
        pass


# ── Server startup ──────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> dict[str, str]:
    """Parse simple --key value CLI arguments."""
    args: dict[str, str] = {}
    if argv is None:
        argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            key = argv[i][2:].replace("-", "_")
            args[key] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def create_server(
    port: int = DEFAULT_PORT,
    db_dir: str | None = None,
) -> tuple[HTTPServer, SidecarAPI]:
    """Create and return the HTTP server and SidecarAPI instance.

    The API is attached to the handler class so every request
    has access to the shared state.
    """
    api = SidecarAPI(db_dir=db_dir)

    # Attach API to handler class before server creation
    SidecarHandler.api = api

    server = HTTPServer(("0.0.0.0", port), SidecarHandler)
    return server, api


def main() -> None:
    """Entry point for standalone execution."""
    args = parse_args()
    port = int(args.get("port", DEFAULT_PORT))
    db_dir = args.get("db_dir")

    server, api = create_server(port=port, db_dir=db_dir)
    api.start_monitor()

    print(f"StellarOrion Sidecar UI v{VERSION}")
    print(f"Serving frontend from: {FRONTEND_DIR}")
    print(f"API endpoints: /api/status, /api/results, /api/history, /api/config")
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
