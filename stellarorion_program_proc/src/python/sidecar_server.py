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

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self._json_response(_sim_state)
        elif self.path.startswith("/"):
            self._serve_static(self.path)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
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
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_static(self, path: str) -> None:
        # Try sidecar_ui first, then ui/
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

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # Silence request logging


def main() -> None:
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
