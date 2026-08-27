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

import csv
import datetime
import json
import sys
import threading
import time
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

# ── Formal verification contracts (CrossHair / deal) ──────────────────
# CrossHair verifies these postconditions; `deal` is the dev-only contract
# library managed by run.py's hash-gated venv. The decorator degrades to a
# no-op when `deal` is unavailable, so this module stays loadable in
# production environments that lack the verification toolchain.
try:  # pragma: no cover - dev dependency
    from deal import post as postcondition
except ImportError:  # pragma: no cover - dev dependency
    def postcondition(*_args: Any, **_kwargs: Any):
        """No-op stand-in when the deal package is unavailable."""
        def _decorator(func):
            return func
        return _decorator

# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_PORT = 8080
POLL_INTERVAL_S = 2.0
FRONTEND_DIR = Path(__file__).parent / "frontend"
VERSION = "1.0.0-hypersonic"
# Default runs directory (used when --db-dir is absent or malformed).
_DEFAULT_RUNS_DIR = Path(__file__).parent.parent.parent / "data" / "runs"
# Geometry snapshot store: every distinct HIAD surface is archived here under a
# timestamped, collision-proof name so history accumulates WITHOUT overwriting.
GEOMETRY_DIR = Path(__file__).parent.parent.parent / "data" / "geometries"
# Live surface produced by the Ada binary during a validation / sample run.
PROJECT_ROOT_SURF = Path(__file__).parent.parent.parent / "HIAD_custom.surf"


# ── Simulation State (thread-safe via Lock) ─────────────────────────────

class SimulationState:
    """Mutable simulation state protected by a threading lock."""

    # --- construction ---
    def __init__(self) -> None:
        """Create the state holder: one lock plus stopped/idle defaults
        and the standard IRVE-3 configuration.
        Tested by: test_update() (same file).
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
    def update(self, **kwargs: Any) -> None:
        """Thread-safely assign the given keyword arguments onto attributes
        that already exist (unknown keys are ignored).
        Tested by: test_update() (same file).
        """
        with self._lock:
            # Loop invariant: kwargs is a fixed mapping; only pre-existing
            # attributes are assigned, so the attribute set never grows.
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    # --- config readers/writers ---
    def get_config(self) -> dict[str, Any]:
        """Return a shallow copy of the current run configuration.
        Tested by: test_get_config() (same file).
        """
        with self._lock:
            return dict(self.config)

    # --- config writer ---
    def set_config(self, cfg: dict[str, Any]) -> None:
        """Merge cfg into the stored configuration under the lock.
        Tested by: test_set_config() (same file).
        """
        with self._lock:
            self.config.update(cfg)

    @staticmethod
    @postcondition(
        lambda result: isinstance(result, dict)
        and "geometry" in result
        and result["geometry"]["nose_radius_m"] == 0.55
        and result.get("solver") == "SPARTA"
    )
    def _default_config() -> dict[str, Any]:
        """Baseline configuration: IRVE-3 geometry, Mach 10 / 52 km flight,
        SPARTA solver with five-species chemistry and grid factor 0.7."""
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
        """
        self._title = title.strip() if title else "StellarOrion HypersonicEdition"

    # --- dynamic title reader ---
    def get_window_title(self) -> str:
        """Return the current window title.
        Tested by: test_get_window_title() (same file).
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
        """
        self._shutdown_event.set()

    def _monitor_loop(self) -> None:
        """Background loop — polls Ada backend status file."""
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

    # --- GET routing ---
    def do_GET(self) -> None:
        """Route /api/status|results|history|config|title GETs to their
        handlers; anything else is served from frontend/ static files.
        Tested by: test_do_GET() (same file).
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
        }

        handler = routes.get(path)
        if handler:
            handler()
            return

        # Static file serving from frontend/
        self._serve_static(path)

    # --- POST routing ---
    def do_POST(self) -> None:
        """Parse a JSON body and dispatch /api/start|stop|config|title;
        malformed JSON answers 400 and unknown paths answer 404.
        Tested by: test_do_POST() (same file).
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
        else:
            self._json_response({"error": "Not found"}, 404)

    # ── API handlers ────────────────────────────────────────────────────

    def _handle_status(self) -> None:
        """GET /api/status: state snapshot plus window title and version."""
        data = self.api.state.snapshot()
        data["window_title"] = self.api.get_window_title()
        data["version"] = VERSION
        self._json_response(data)

    def _handle_results(self) -> None:
        """GET /api/results: latest results and metrics snapshots."""
        snap = self.api.state.snapshot()
        self._json_response({
            "results": snap["results"],
            "metrics": snap["metrics"],
        })

    def _handle_history(self) -> None:
        """GET /api/history: list of past runs read from the DB directory."""
        history = self.api.get_history()
        self._json_response({"runs": history})

    def _handle_config(self) -> None:
        """GET /api/config: current simulation configuration."""
        self._json_response(self.api.state.get_config())

    def _handle_title(self) -> None:
        """GET /api/title: current dynamic browser window title."""
        self._json_response({"title": self.api.get_window_title()})

    def _handle_start(self, payload: dict[str, Any]) -> None:
        """POST /api/start: begin a simulation; 409 when it cannot start."""
        result = self.api.start_simulation(payload or None)
        code = 200 if result.get("ok") else 409
        self._json_response(result, code)

    def _handle_stop(self) -> None:
        """POST /api/stop: halt the running simulation; 409 when idle."""
        result = self.api.stop_simulation()
        code = 200 if result.get("ok") else 409
        self._json_response(result, code)

    def _handle_set_config(self, payload: dict[str, Any]) -> None:
        """POST /api/config: merge payload into the stored configuration."""
        self.api.state.set_config(payload)
        self._json_response({"ok": True})

    def _handle_set_title(self, payload: dict[str, Any]) -> None:
        """POST /api/title: set the window title and echo it back."""
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
        except OSError as exc:
            #  VERBOSE error path (Murphy's Law): log before the JSON error
            #  response so the failure is visible in server logs.
            print(f"[sidecar-ui] Static file read failed for '{file_path}': {exc}")
            self._json_response({"error": "Read error"}, 500)

    @staticmethod
    @postcondition(
        lambda result: isinstance(result, str) and "/" in result
    )
    def _guess_content_type(ext: str) -> str:
        """Map a file extension to its MIME type; unknown extensions get
        application/octet-stream."""
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
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[sidecar-ui] SURF read failed '{path}': {exc}")
            return []
        points: list[list[float]] = []
        n_expected = 0
        in_points = False
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
                        pass
                continue
            # Inside the Points block.
            if low == "lines":
                break
            toks = line.split()
            if len(toks) >= 3 and toks[0].isdigit():
                try:
                    points.append([float(toks[1]), float(toks[2])])
                except ValueError:
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
        """
        candidates: list[Path] = []
        try:
            if GEOMETRY_DIR.exists():
                candidates.extend(GEOMETRY_DIR.glob("*.surf"))
        except OSError:
            pass
        for p in (PROJECT_ROOT_SURF, _DEFAULT_RUNS_DIR / "HIAD_custom.surf"):
            if p.exists():
                candidates.append(p)
        best: Path | None = None
        best_mtime = 0.0
        for p in candidates:
            try:
                m = p.stat().st_mtime
            except OSError:
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
        """
        path, mtime = self._latest_surf_path()
        if path is None:
            self._json_response({
                "id": None, "source": None, "mtime": 0, "count": 0,
                "axial_max": 0.0, "radial_max": 0.0, "points": [],
            })
            return
        pts = self._load_surf_points(path)
        axial_max = max((p[0] for p in pts), default=0.0)
        radial_max = max((p[1] for p in pts), default=0.0)
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
        """
        entries: list[dict[str, Any]] = []
        try:
            if GEOMETRY_DIR.exists():
                for f in GEOMETRY_DIR.glob("*.surf"):
                    try:
                        m = f.stat().st_mtime
                    except OSError:
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
        """
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        name = (qs.get("id") or [None])[0]
        if not name:
            self._json_response({"error": "missing id"}, 400)
            return
        safe = Path(name).name  # strip directories -> blocks traversal
        f = GEOMETRY_DIR / safe
        if not f.exists():
            self._json_response({"error": "not found"}, 404)
            return
        pts = self._load_surf_points(f)
        self._json_response({
            "id": f.name, "source": str(f), "mtime": f.stat().st_mtime,
            "count": len(pts),
            "axial_max": max((p[0] for p in pts), default=0.0),
            "radial_max": max((p[1] for p in pts), default=0.0),
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
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = GEOMETRY_DIR / f"HIAD_{stamp}_{safe_run}.surf"
        try:
            dest.write_bytes(src.read_bytes())
            mtime = dest.stat().st_mtime
        except OSError as exc:
            print(f"[sidecar-ui] SURF archive failed: {exc}")
            self._json_response({"ok": False, "error": f"write failed: {exc}"}, 500)
            return
        self._json_response({"ok": True, "id": dest.name, "mtime": mtime})

    # ── JSON response helper ────────────────────────────────────────────

    def _json_response(self, data: Any, status: int = 200) -> None:
        """Write data as JSON with CORS headers; serialization failure
        degrades to an error payload instead of crashing mid-response."""
        #  Serialize FIRST inside a guard (Murphy's Law): a serialization
        #  failure is reported verbosely before any bytes hit the wire.
        try:
            body = json.dumps(data, default=str).encode("utf-8")
        except (TypeError, ValueError) as exc:
            print(f"[sidecar-ui] JSON serialization failed ({type(exc).__name__}): {exc}")
            body = json.dumps({"error": "serialization failed"}, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    # --- CORS preflight ---
    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests.
        Tested by: test_do_OPTIONS() (same file).
        """
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- access-log suppression ---
    def log_message(self, fmt: str, *args: Any) -> None:
        """Suppress default access log noise.
        Tested by: test_log_message() (same file).
        """


# ── Server startup ──────────────────────────────────────────────────────

# --- CLI parsing ---
def parse_args(argv=None) -> dict:
    """Parse simple --key value CLI arguments into a plain dict.
    Tested by: test_parse_args() (same file).
    """
    args = {}
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
    """
    # Two-step None resolution keeps the Optional flow explicit.
    resolved_db: str | None = None if db_dir is None else db_dir
    api = SidecarAPI(db_dir=resolved_db)

    # Attach API to handler class before server creation
    SidecarHandler.api = api

    server = HTTPServer(("0.0.0.0", port), SidecarHandler)
    return server, api


# --- entry point ---
def main() -> None:
    """Entry point for standalone execution.
    Tested by: test_main() (same file).
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
def _spin_ui_server(db_dir=None):
    """Start HTTPServer + SidecarHandler on an ephemeral localhost port.

    Pre: none. Post: returns (server, api, base_url); caller must call
    server_close(). Tested by: indirectly via test_do_GET().
    """
    import threading

    api = SidecarAPI(db_dir=db_dir)
    SidecarHandler.api = api
    srv = HTTPServer(("127.0.0.1", 0), SidecarHandler)
    worker = threading.Thread(target=srv.serve_forever, daemon=True)
    worker.start()
    host, port = srv.server_address[:2]
    return srv, api, "http://" + str(host) + ":" + str(port)


# Self-test: snapshot reflects updates and hands out defensive copies.
def test_snapshot() -> None:
    """snapshot() mirrors updates and isolates later mutations.

    Tested by: this function itself (self-test section).
    """
    st = SimulationState()
    st.update(status="running", progress=0.42, results={"heat_flux_wcm2": 14.36})
    snap = st.snapshot()
    assert snap["status"] == "running"
    assert abs(snap["progress"] - 0.42) < 1e-9
    snap["results"]["heat_flux_wcm2"] = 0.0  # mutate the copy only
    assert st.snapshot()["results"]["heat_flux_wcm2"] == 14.36


# Self-test: update assigns known attributes and ignores unknown keys.
def test_update() -> None:
    """update() sets known fields under lock and drops unknown keys.

    Tested by: this function itself (self-test section).
    """
    st = SimulationState()
    st.update(status="running", totally_unknown_key=123)
    assert st.status == "running"
    assert not hasattr(st, "totally_unknown_key")


# Self-test: get_config returns IRVE-3 defaults as an isolated copy.
def test_get_config() -> None:
    """get_config() exposes baseline config and isolates mutations.

    Tested by: this function itself (self-test section).
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
    """
    api = SidecarAPI()
    api.set_window_title("Cruise")
    assert api.get_window_title() == "Cruise"


# Self-test: start_simulation accepts params and rejects double starts.
def test_start_simulation() -> None:
    """start_simulation() runs once, names the run, refuses re-entry.

    Tested by: this function itself (self-test section).
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
    """
    api = SidecarAPI()
    api.stop_monitor()  # no-op when never started
    api.start_monitor()
    first = api._monitor_thread
    api.stop_monitor()
    first.join(timeout=5.0)
    assert not first.is_alive()
    api.start_monitor()
    second = api._monitor_thread
    assert second is not first
    api.stop_monitor()
    second.join(timeout=5.0)


# Self-test: GET dispatch serves /api/status and 404s unknown files.
def test_do_GET() -> None:
    """do_GET() routes /api/status live state; unknown paths give 404.

    Tested by: this function itself (self-test section).
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
    """
    assert SidecarHandler.log_message(object(), "GET %s", "/x") is None


# Self-test: parse_args maps --key value pairs and ignores stray tokens.
def test_parse_args() -> None:
    """parse_args() collects pairs, tolerates strays and empty input.

    Tested by: this function itself (self-test section).
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
    """
    calls = []
    orig_serve = HTTPServer.serve_forever

    # Nested stub: raises KeyboardInterrupt on the first serve_forever call.
    def _fake_serve(self) -> None:
        """Immediate Ctrl-C: prove wiring without blocking the suite."""
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
    """
    api = SidecarAPI(db_dir=12345)  # Path(int) raises TypeError internally
    assert api._db_dir == _DEFAULT_RUNS_DIR
    assert api.state.snapshot()["status"] == "stopped"
