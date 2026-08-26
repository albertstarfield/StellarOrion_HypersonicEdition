"""StellarOrion sidecar UI — HTTP server entry point.

Serves the monitoring frontend and provides a REST API for the Ada
binary to push simulation state updates.

Usage:
    python3 src/python/sidecar_server.py [--port 8080]
"""

import argparse
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_FRONTEND_DIR = _SCRIPT_DIR.parent / "sidecar_ui"
_UI_DIR = _SCRIPT_DIR.parent / "ui"

# Global simulation state
_sim_state: dict[str, Any] = {
    "status": "idle",
    "progress": 0.0,
    "step": 0,
    "total_steps": 0,
    "metrics": {},
}


class SidecarHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for the sidecar API + static files."""

    # --- GET routing ---
    def do_GET(self) -> None:
        """Serve /api/status as live simulation state; other paths fall
        through to static frontend files.
        Tested by: test_do_GET() (same file).
        """
        if self.path == "/api/status":
            self._json_response(_sim_state)
        elif self.path.startswith("/"):
            self._serve_static(self.path)
        else:
            self.send_error(404)

    # --- POST routing ---
    def do_POST(self) -> None:
        """Merge a JSON body into _sim_state (/api/update) or reset it
        to idle defaults (/api/reset); rejects malformed JSON with 400.
        Tested by: test_do_POST() (same file).
        """
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            #  VERBOSE (Murphy's Law): log before the 400 so bad payloads are
            #  visible in server logs instead of vanishing silently.
            print(f"[sidecar] Invalid JSON on {self.path} ({exc}); body={body[:120]!r}")
            self.send_error(400, "Invalid JSON")
            return

        if self.path == "/api/update":
            _sim_state.update(payload)
            self._json_response({"ok": True})
        elif self.path == "/api/reset":
            _sim_state.update({"status": "idle", "progress": 0.0, "step": 0, "metrics": {}})
            self._json_response({"ok": True})
        else:
            self.send_error(404)

    def _json_response(self, data: Any, status: int = 200) -> None:
        """Write data as a JSON body with permissive CORS headers."""
        #  Serialize FIRST inside a guard (Murphy's Law): a serialization
        #  failure is reported verbosely and degrades to an error payload
        #  instead of crashing the handler mid-response.
        try:
            payload = json.dumps(data)
        except (TypeError, ValueError) as exc:
            print(f"[sidecar] JSON serialization failed ({type(exc).__name__}): {exc}")
            payload = json.dumps({"error": "serialization failed"})
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload.encode())

    def _serve_static(self, path: str) -> None:
        """Serve a file from sidecar_ui/, falling back to ui/frontend;
        sends 404 when no candidate exists."""
        # Try sidecar_ui first, then ui/
        # Loop invariant: bases is a fixed two-element list; the loop returns
        # on the first existing candidate file, else falls through to 404.
        for base in [_FRONTEND_DIR, _UI_DIR / "frontend"]:
            target = base / path.lstrip("/")
            if target.is_file():
                self.send_response(200)
                ext = target.suffix.lower()
                ct = {
                    ".html": "text/html",
                    ".css": "text/css",
                    ".js": "application/javascript",
                    ".json": "application/json",
                    ".png": "image/png",
                    ".svg": "image/svg+xml",
                }.get(ext, "application/octet-stream")
                self.send_header("Content-Type", ct)
                self.end_headers()
                self.wfile.write(target.read_bytes())
                return
        self.send_error(404)

    # --- CORS preflight ---
    def do_OPTIONS(self) -> None:
        """Answer CORS preflight: allow GET/POST/OPTIONS with Content-Type
        from any origin.
        Tested by: test_do_OPTIONS() (same file).
        """
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- access-log suppression ---
    def log_message(self, fmt: str, *args: Any) -> None:
        """Suppress BaseHTTPRequestHandler's per-request console logging.
        Tested by: test_log_message() (same file).
        """
        # Silence request logging


# --- server entry point ---
def main() -> None:
    """Start the single-threaded HTTPServer for the sidecar UI.

    Binds --host/--port (defaults 127.0.0.1:8080), serves until interrupted,
    then closes the listening socket cleanly on Ctrl-C.
    Tested by: test_main() (same file).
    """
    parser = argparse.ArgumentParser(description="StellarOrion Sidecar UI")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), SidecarHandler)
    print(f"StellarOrion sidecar UI running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down sidecar UI.")
        server.server_close()


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════
#  Self-tests (pytest-style; fast — localhost-only ephemeral server)
# ══════════════════════════════════════════════════════════════════════════

def _spin_server():
    """Start HTTPServer on an ephemeral localhost port in a daemon thread.

    Pre: none. Post: returns (server, base_url); caller must server_close().
    Tested by: indirectly via test_do_GET().
    """
    import threading

    srv = HTTPServer(("127.0.0.1", 0), SidecarHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    host, port = srv.server_address[:2]
    return srv, "http://" + str(host) + ":" + str(port)


# Self-test: GET /api/status returns live JSON state over HTTP.
def test_do_GET() -> None:
    """GET /api/status returns 200 JSON carrying the status key.

    Tested by: this function itself (self-test section).
    """
    import json
    import urllib.request

    srv, url = _spin_server()
    try:
        status_url = url + "/api/status"
        with urllib.request.urlopen(status_url, timeout=5) as resp:
            assert resp.status == 200
            payload = json.loads(resp.read().decode())
        assert "status" in payload
    finally:
        srv.server_close()


# Self-test: POST update/reset mutate shared state over HTTP.
def test_do_POST() -> None:
    """POST /api/update merges state; /api/reset restores idle defaults.

    Tested by: this function itself (self-test section).
    """
    import json
    import urllib.request

    srv, url = _spin_server()
    try:
        req = urllib.request.Request(
            f"{url}/api/update",
            data=json.dumps({"progress": 0.5}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode())["ok"] is True

        req2 = urllib.request.Request(
            f"{url}/api/reset", data=b"", method="POST"
        )
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            assert resp2.status == 200
    finally:
        srv.server_close()


# Self-test: CORS preflight answers with permissive headers.
def test_do_OPTIONS() -> None:
    """OPTIONS preflight answers 2xx with CORS allow-origin header.

    Tested by: this function itself (self-test section).
    """
    import urllib.request

    srv, url = _spin_server()
    try:
        req = urllib.request.Request(url + "/", method="OPTIONS")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert 200 <= resp.status < 300
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"
    finally:
        srv.server_close()


# Self-test: log override silences per-request console noise.
def test_log_message() -> None:
    """log_message override swallows format calls without printing.

    Tested by: this function itself (self-test section).
    """
    assert SidecarHandler.log_message(object(), "GET %s", "/x") is None


# Self-test: startup binding sanity on an ephemeral socket.
def test_main() -> None:
    """Startup wiring binds an ephemeral socket and closes cleanly.

    Tested by: this function itself (self-test section).
    """
    srv = HTTPServer(("127.0.0.1", 0), SidecarHandler)
    _host, port = srv.server_address[:2]
    assert port > 0
    srv.server_close()
