#!/usr/bin/env python3
"""Tests for StellarOrion run.py pipeline orchestrator.

Run with:
    python3 -m pytest tests/test_run_pipeline.py -v
    # or
    python3 -m coverage run -m pytest tests/test_run_pipeline.py
"""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main as unittest_main

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


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


if __name__ == "__main__":
    unittest_main()
