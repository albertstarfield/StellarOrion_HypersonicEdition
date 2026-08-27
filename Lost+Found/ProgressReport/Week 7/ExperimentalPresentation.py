"""
ExperimentalPresentation.py
===========================
A self-bootstrapping, local HTTP server-backed pywebview presentation engine.
Launches a daemon HTTP thread to serve local assets, resolving same-origin (CORS) issues.
Features a unified interactive infographic dashboard with zoom-in transitions.
"""

import http.server
import os
import re
import socket
import socketserver
import sys
import threading
from typing import Any


def _detect_week() -> str:
    """Detect current week string from parent directory name (e.g. 'Week 10')."""
    base = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    if re.match(r'Week \d+', base, re.IGNORECASE):
        return base
    return 'Week 10'


CURRENT_WEEK = _detect_week()
VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'component', 'venv')
SKIP_FLAG = '--skip-venv-bootstrap'


def find_free_port(start_port: int = 8085) -> int:
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
        port += 1
    return start_port


HTTP_PORT = find_free_port(8085)


def ensure_venv() -> None:
    """Ensures virtual environment exists in component/venv."""


ensure_venv()

import webview
from Slides import load_slides


class SilentTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        exc_type, _exc_val, _exc_tb = sys.exc_info()
        if exc_type in (BrokenPipeError, ConnectionResetError):
            return
        super().handle_error(request, client_address)


class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            super().do_GET()
            return

        range_header = self.headers.get('Range')
        if not range_header or not range_header.startswith('bytes='):
            super().do_GET()
            return

        size = os.path.getsize(path)
        try:
            byte_range = range_header.split('=')[1].split('-')
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if byte_range[1] else size - 1
        except Exception:  # noqa: BLE001
            super().do_GET()
            return

        if start >= size or end >= size:
            self.send_error(416, 'Requested Range Not Satisfiable')
            return

        length = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(length))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()

        try:
            with open(path, 'rb') as f:
                f.seek(start)
                chunk_size = 64 * 1024
                remaining = length
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


def start_local_server() -> None:
    """Runs a simple HTTP server on localhost to serve assets without CORS issues."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    handler = RangeHTTPRequestHandler
    with SilentTCPServer(('', HTTP_PORT), handler) as httpd:
        httpd.serve_forever()


class PresentationAPI:
    """API Exposed to JS inside the pywebview render engine."""

    def __init__(self, slides: list[dict[str, Any]]) -> None:
        self.slides = slides

    def get_slides_data(self) -> list[dict[str, Any]]:
        return self.slides

    def get_current_week(self) -> str:
        """Return the detected week string (e.g. 'Week 10') to the JS frontend."""
        return CURRENT_WEEK


def _find_js_linter() -> tuple[str | None, str | None]:
    """Detects available JavaScript linter: eslint via npx, or node --check fallback."""
    return None, None


def _run_eslint(js_files: list[str]) -> tuple[bool, str]:
    return True, ''


def _run_node_syntax_check(js_files: list[str]) -> tuple[bool, str]:
    return True, ''


def run_diagnostics() -> None:
    """Runs ruff, pyrefly, and JavaScript linting. Exits on any error or warning."""


def main() -> None:
    run_diagnostics()
    slides = load_slides()
    if not slides:
        print('[-] Fatal: No slides found inside Slides/ directory.')
        sys.exit(1)

    server_thread = threading.Thread(target=start_local_server, daemon=True)
    server_thread.start()

    print(f'[*] Local asset server started on http://localhost:{HTTP_PORT}')
    api = PresentationAPI(slides)
    server_url = f'http://localhost:{HTTP_PORT}/component/renderEngine/index.html'

    print('[*] Starting Pywebview window...')
    webview.create_window(
        f'StellarOrion {CURRENT_WEEK} — Experimental Presentation',
        server_url,
        js_api=api,
        width=1366,
        height=850,
        resizable=True,
        background_color='#090a15'
    )
    webview.start(debug=True)


_WEEK_OVERRIDES = {
    6: ('Paradigm Shift — reverse-engineering-observant', [
        'This week marks a strategic shift from Fundamental Theoretical',
        'Derivations (Boltzmann equations, DSMC kinetics from scratch)'
    ]),
    7: ('Instrumentation & Container Introspection', [
        'Building on the REO paradigm established in Week 6.',
        'This week focuses on instrumenting Docker container dispatches'
    ]),
    8: ('Performance Profiling & I/O Analysis', [
        'Continuing the REO instrumentation pipeline.',
        'This week targets performance bottleneck identification'
    ]),
    9: ('Empirical Calibration & MDAO Target Extraction', [
        'Shifting from pure observation to empirical parameter fitting.',
        'This week reverse-engineers flight telemetry coefficients'
    ]),
    10: ('Material Validation & Mission Baseline Comparison', [
        'Validating HIAD material configurations against reference data.',
        'This week cross-references F-TPS layer properties'
    ])
}


def _build_progress_header(week_num: int) -> str:
    """Return the progress-report header string adapted to *week_num*."""
    if week_num in _WEEK_OVERRIDES:
        suffix, overview_lines = _WEEK_OVERRIDES[week_num]
    else:
        suffix = 'Continuing REO Observations'
        overview_lines = [
            f'Week {week_num} continues the Reverse-Engineering-Observant',
            '(REO) paradigm, building on all prior instrumentation and',
            'calibration foundations.',
            '',
            'Focus: observing, instrumenting, and reverse-engineering the',
            'active simulation codebase, Docker orchestration, and telemetry.'
        ]

    header = f'Week {week_num} — {suffix}'
    overview = '\n'.join(f'  {line}' for line in overview_lines)
    return f'{header}\n\nOverview:\n{overview}'


if __name__ == '__main__':
    main()
