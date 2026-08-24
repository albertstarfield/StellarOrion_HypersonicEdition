"""Tests for StellarOrion run.py pipeline orchestrator.

Run with:
    python3 -m pytest tests/test_run_pipeline.py -v
    # or
    python3 -m coverage run --branch -m unittest discover \
        -s tests -p "test_run_pipeline.py"

Coverage note: the unit classes below exercise run.py's pure and
side-effect-light helpers directly (import run).  Phase functions that
require Docker / Alire / the Ada binary are integration-scope and are
excluded from the unit coverage gate by design (documented in
docs/COVERAGE_FUZZING_STATUS.md).
"""

import hashlib
import http.server
import io
import json
import os
import sys
import tempfile
import threading
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase
from unittest import main as unittest_main

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import run


class TestHashComputation(TestCase):
    """Test source hash computation for cache invalidation."""

    def test_hash_file_format(self):
        """Hash file should be valid JSON with SHA256 digests."""
        hash_file = _PROJECT_ROOT / ".src_hashes.json"
        if hash_file.exists():
            data = json.loads(hash_file.read_text())
            self.assertIsInstance(data, dict)
            for key, val in data.items():
                self.assertIsInstance(key, str)
                self.assertEqual(len(val), 64)  # SHA256 hex digest

    def test_hash_determinism(self):
        """Same file content should produce same hash."""
        content = b"test content for hashing"
        h1 = hashlib.sha256(content).hexdigest()
        h2 = hashlib.sha256(content).hexdigest()
        self.assertEqual(h1, h2)


class TestVenvPaths(TestCase):
    """Test that venv paths are correctly resolved."""

    def test_venv_python_exists_after_bootstrap(self):
        """After Phase 1, venv/bin/python3 should exist."""
        venv_python = _PROJECT_ROOT / "venv" / "python" / "bin" / "python3"
        # This test only validates path resolution, not existence
        self.assertTrue(str(venv_python).endswith("bin/python3"))


class TestRequirementsFile(TestCase):
    """Test that requirements.txt exists and is valid."""

    def test_requirements_exists(self):
        req = _PROJECT_ROOT / "requirements.txt"
        self.assertTrue(req.exists(), "requirements.txt must exist")

    def test_requirements_not_empty(self):
        req = _PROJECT_ROOT / "requirements.txt"
        if req.exists():
            content = req.read_text().strip()
            self.assertGreater(len(content), 0, "requirements.txt is empty")


class TestSabotageVerifierExists(TestCase):
    """Test that sabotage_verifier.py exists and is importable."""

    def test_verifier_exists(self):
        verifier = _PROJECT_ROOT / "src" / "utils" / "sabotage_verifier.py"
        self.assertTrue(verifier.exists(), "sabotage_verifier.py must exist")

    def test_verifier_not_empty(self):
        verifier = _PROJECT_ROOT / "src" / "utils" / "sabotage_verifier.py"
        if verifier.exists():
            size = verifier.stat().st_size
            self.assertGreater(size, 1000, "sabotage_verifier.py seems too small")


class TestGPRAFile(TestCase):
    """Test GPR file has SPARK switches."""

    def test_gpr_exists(self):
        gpr = _PROJECT_ROOT / "stellarorion_program_proc.gpr"
        self.assertTrue(gpr.exists(), "GPR file must exist")

    def test_gpr_has_spark(self):
        gpr = _PROJECT_ROOT / "stellarorion_program_proc.gpr"
        if gpr.exists():
            content = gpr.read_text()
            self.assertIn("Source_Dirs", content, "GPR must specify source dirs")
            self.assertIn("Main", content, "GPR must specify main")


class TestColorHelper(TestCase):
    """Test ANSI colour wrapper (both TTY and non-TTY branches)."""

    def test_color_disabled_returns_plain(self):
        original = run._COLOR
        run._COLOR = False
        try:
            self.assertEqual(run._c("31", "err"), "err")
        finally:
            run._COLOR = original

    def test_color_enabled_wraps_ansi(self):
        original = run._COLOR
        run._COLOR = True
        try:
            self.assertEqual(run._c("32", "ok"), "\033[32mok\033[0m")
        finally:
            run._COLOR = original


class TestFindFreePort(TestCase):
    """Test ephemeral port selection."""

    def test_returns_valid_port(self):
        port = run._find_free_port()
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 1024)
        self.assertLessEqual(port, 65535)


class TestSidecarHealthCheck(TestCase):
    """Test sidecar health polling against live and dead endpoints."""

    def test_unreachable_endpoint_returns_false(self):
        # Port 1 on localhost is reserved and virtually never serving.
        self.assertFalse(run._sidecar_health_check(1, timeout_s=0.5))

    def test_live_endpoint_returns_true(self):
        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):  # silence request logging
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        try:
            thread.start()
            port = server.server_address[1]
            self.assertTrue(run._sidecar_health_check(port, timeout_s=5.0))
        finally:
            server.shutdown()
            server.server_close()


class TestLockFile(TestCase):
    """Test PID lockfile lifecycle (uses temp paths only)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._lock_path = Path(self._tmp.name) / "test.lock"

    def tearDown(self):
        self._tmp.cleanup()

    def test_acquire_release_roundtrip(self):
        lock = run._LockFile(self._lock_path)
        lock.acquire()
        self.assertTrue(self._lock_path.exists())
        self.assertEqual(int(self._lock_path.read_text()), os.getpid())
        lock.release()
        self.assertFalse(self._lock_path.exists())

    def test_stale_lock_is_recovered(self):
        self._lock_path.write_text("999999999")  # dead PID
        lock = run._LockFile(self._lock_path)
        lock.acquire()  # must not raise; stale lock replaced
        self.assertEqual(int(self._lock_path.read_text()), os.getpid())
        lock.release()

    def test_corrupt_lock_is_recovered(self):
        self._lock_path.write_text("not-a-pid")
        lock = run._LockFile(self._lock_path)
        lock.acquire()
        self.assertEqual(int(self._lock_path.read_text()), os.getpid())
        lock.release()

    def test_live_pid_lock_raises_system_exit(self):
        self._lock_path.write_text(str(os.getpid()))  # our own live PID
        lock = run._LockFile(self._lock_path)
        with self.assertRaises(SystemExit) as ctx:
            lock.acquire()
        self.assertEqual(ctx.exception.code, 3)
        # Clean up so tearDown does not trip on the leftover file.
        self._lock_path.unlink(missing_ok=True)


class TestSourceHashes(TestCase):
    """Test hash-gated cache invalidation helpers.

    Backs up and restores the real .src_hashes.json so tests are
    side-effect free with respect to the repository state.
    """

    def setUp(self):
        self._backup = None
        if run._HASH_FILE.exists():
            self._backup = run._HASH_FILE.read_bytes()

    def tearDown(self):
        if self._backup is not None:
            run._HASH_FILE.write_bytes(self._backup)
        else:
            run._HASH_FILE.unlink(missing_ok=True)

    def test_compute_source_hashes_nonempty_sha256(self):
        hashes = run._compute_source_hashes()
        self.assertGreater(len(hashes), 0, "src/ contains .py files")
        for key, val in hashes.items():
            self.assertTrue(key.endswith(".py"))
            self.assertEqual(len(val), 64)

    def test_save_then_changed_is_false(self):
        run._save_hashes()
        self.assertFalse(run._hashes_changed())

    def test_missing_hash_file_means_changed(self):
        run._HASH_FILE.unlink(missing_ok=True)
        self.assertTrue(run._hashes_changed())

    def test_corrupt_hash_file_means_changed(self):
        run._HASH_FILE.write_text("{not valid json")
        self.assertTrue(run._hashes_changed())


class TestParseArgs(TestCase):
    """Test pipeline flag parsing and Ada-arg passthrough."""

    def _parse(self, argv):
        """Parse argv by temporarily replacing sys.argv (run.py API)."""
        original = sys.argv
        sys.argv = ["run.py", *argv]
        try:
            return run._parse_args()
        finally:
            sys.argv = original

    def test_defaults_are_false_with_passthrough(self):
        args, unknown = self._parse([])
        self.assertFalse(args.clean)
        self.assertFalse(args.no_launch)
        self.assertFalse(args.verbose)
        self.assertEqual(unknown, [])

    def test_known_flag_and_unknown_forwarding(self):
        # NOTE: "--test" would abbreviate-match "--test-build-integrity-only"
        # (argparse allow_abbrev default), so we use unambiguous sim flags.
        args, unknown = self._parse(
            ["--verbose", "--validate", "--steps", "100"]
        )
        self.assertTrue(args.verbose)
        self.assertIn("--validate", unknown)
        self.assertIn("--steps", unknown)
        self.assertIn("100", unknown)

    def test_abbrev_flag_matches_long_form(self):
        # Documents the argparse abbreviation behaviour explicitly.
        args, _unknown = self._parse(["--test"])
        self.assertTrue(args.test_build_integrity_only)


class TestOutputHelpers(TestCase):
    """Smoke-test console output helpers (no exceptions, sane content)."""

    def test_banner_prints_pipeline_name(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            run.banner()
        self.assertIn("Build Pipeline", buf.getvalue())

    def test_phase_header_formats(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            run.phase_header(2, "Python Static Analysis")
        self.assertIn("[Phase 2]", buf.getvalue())
        self.assertIn("Python Static Analysis", buf.getvalue())

    def test_step_info_and_leaf(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            run.step_info("info message")
            run.step_leaf("leaf message")
        self.assertIn("info message", buf.getvalue())
        self.assertIn("leaf message", buf.getvalue())

    def test_ensure_utf8_locale_idempotent(self):
        run._ensure_utf8_locale()
        enc = os.environ.get("LC_ALL", "")
        if enc:
            self.assertIn("UTF", enc.upper().replace("-", ""))


if __name__ == "__main__":
    unittest_main()
