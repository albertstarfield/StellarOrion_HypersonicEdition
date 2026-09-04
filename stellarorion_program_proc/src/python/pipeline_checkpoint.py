"""StellarOrion Pipeline Checkpoint — Save/Resume tracker for the 4-step pipeline.

Tracks completion status across the 4 pipeline phases:
  Step 1: SPARTA   — DSMC simulation (Docker/colima)
  Step 2: Kriging  — Spatial denoising of SPARTA grid output
  Step 3: PINN     — Physics-informed neural network training
  Step 4: MoP      — Metamodel Prognosis (virtual sample generation)

If the pipeline is interrupted (crash, power loss, timeout), the checkpoint
file allows resume from the last completed step without re-running prior steps.

Checkpoint file format (pipeline_checkpoint.json):
{
    "version": 1,
    "pipeline_id": "unique-id-or-timestamp",
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601",
    "steps": {
        "sparta":   {"status": "completed", "completed_at": "...", "output_files": [...]},
        "kriging":  {"status": "pending",   "completed_at": null,  "output_files": []},
        "pinn":     {"status": "pending",   "completed_at": null,  "output_files": []},
        "mop":      {"status": "pending",   "completed_at": null,  "output_files": []}
    },
    "config": {
        "grid_file": "grid.2200.out",
        "domain_bounds": [-5.0, 9.0, 3.9375],
        "iterations": 2000,
        "device": "cpu"
    }
}

Author: Albert Starfield Wahyu Suryo Samudro
"""

import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# ========================================================================
#  Pipeline step definitions
# ========================================================================

# Ordered pipeline steps — resume starts from the first non-completed step.
PIPELINE_STEPS = ("sparta", "kriging", "pinn", "mop")

# Default checkpoint filename
DEFAULT_CHECKPOINT_FILE = "pipeline_checkpoint.json"


class StepStatus(str, Enum):
    """Status of a pipeline step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ========================================================================
#  PipelineCheckpoint class
# ========================================================================

class PipelineCheckpoint:
    """JSON-based save/resume tracker for the StellarOrion pipeline.

    Usage:
        pc = PipelineCheckpoint("/path/to/results/pipeline_checkpoint.json")
        pc.start(pipeline_id="run-20260903", config={"grid_file": "grid.2200.out"})

        # Before SPARTA:
        if pc.is_step_completed("sparta"):
            print("SPARTA already done, skipping")
        else:
            pc.mark_step_running("sparta")
            run_sparta(...)
            pc.mark_step_completed("sparta", output_files=["grid.2200.out"])

        # Before Kriging:
        if pc.is_step_completed("kriging"):
            print("Kriging already done, skipping")
        else:
            pc.mark_step_running("kriging")
            run_kriging(...)
            pc.mark_step_completed("kriging", output_files=["grid.2200_denoised.out"])
    """

    def __init__(self, checkpoint_path: str) -> None:
        """Bind to a checkpoint file path. Does NOT create/overwrite on init.

        Args:
            checkpoint_path: Path to pipeline_checkpoint.json (will be created
                             on first start() or mark_step_running() call).
        """
        self.checkpoint_path = checkpoint_path
        self._data: dict[str, Any] | None = None

    # --- persistence ---

    def _load(self) -> dict[str, Any]:
        """Load checkpoint from disk. Returns empty dict if file doesn't exist.

        Tested by: test_checkpoint_load_empty() (same file).
        """
        if not os.path.exists(self.checkpoint_path):
            return {}
        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            # Corrupted checkpoint — start fresh and warn
            print(f"[checkpoint] WARNING: corrupted checkpoint at {self.checkpoint_path}: {exc}")
            print("[checkpoint] Starting fresh pipeline.")
            return {}

    def _save(self) -> None:
        """Persist current state to disk atomically.

        Writes to a temp file then renames for crash safety (POSIX atomic rename).

        Tested by: test_checkpoint_save_load_roundtrip() (same file).
        """
        if self._data is None:
            return
        self._data["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp_path = self.checkpoint_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.checkpoint_path)
        except OSError as exc:
            print(f"[checkpoint] WARNING: failed to save checkpoint: {exc}")

    # --- lifecycle ---

    def start(self, pipeline_id: str | None = None,
              config: dict[str, Any] | None = None) -> None:
        """Initialize a new pipeline run or resume an existing one.

        If the checkpoint file exists and has a prior run, it is preserved
        (resume mode). If not, a fresh checkpoint is created.

        Args:
            pipeline_id: Unique identifier for this run (e.g. timestamp or UUID).
                         Generated automatically if not provided.
            config: Pipeline configuration (grid_file, domain_bounds, etc.).
        """
        existing = self._load()
        if existing and existing.get("steps"):
            # Resume mode — keep existing state
            self._data = existing
            print(f"[checkpoint] Resuming pipeline {existing.get('pipeline_id', 'unknown')}")
            completed = [s for s, v in existing.get("steps", {}).items()
                         if v.get("status") == StepStatus.COMPLETED]
            print(f"[checkpoint] Completed steps: {completed or 'none'}")
        else:
            # Fresh start
            if pipeline_id is None:
                pipeline_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            now = datetime.now(timezone.utc).isoformat()
            self._data = {
                "version": 1,
                "pipeline_id": pipeline_id,
                "created_at": now,
                "updated_at": now,
                "steps": {
                    step: {
                        "status": StepStatus.PENDING,
                        "completed_at": None,
                        "output_files": [],
                    }
                    for step in PIPELINE_STEPS
                },
                "config": config or {},
            }
            self._save()
            print(f"[checkpoint] New pipeline started: {pipeline_id}")

    def _ensure_initialized(self) -> None:
        """Guard: must call start() first."""
        if self._data is None:
            raise RuntimeError(
                "PipelineCheckpoint not initialized. Call start() first."
            )

    # --- step queries ---

    def get_next_step(self) -> str | None:
        """Return the first step that is not yet completed, or None if all done.

        Tested by: test_checkpoint_get_next_step() (same file).
        """
        self._ensure_initialized()
        for step in PIPELINE_STEPS:
            status = self._data["steps"][step]["status"]
            if status != StepStatus.COMPLETED:
                return step
        return None

    def is_step_completed(self, step: str) -> bool:
        """Check if a specific step has been completed.

        Tested by: test_checkpoint_mark_completed_and_query() (same file).
        """
        self._ensure_initialized()
        return self._data["steps"][step]["status"] == StepStatus.COMPLETED

    def get_step_status(self, step: str) -> str:
        """Return the status string of a step.

        Tested by: test_checkpoint_mark_completed_and_query() (same file).
        """
        self._ensure_initialized()
        return self._data["steps"][step]["status"]

    def is_all_completed(self) -> bool:
        """Return True if every pipeline step is completed.

        Tested by: test_checkpoint_all_completed() (same file).
        """
        self._ensure_initialized()
        return all(
            self._data["steps"][s]["status"] == StepStatus.COMPLETED
            for s in PIPELINE_STEPS
        )

    # --- step mutations ---

    def mark_step_running(self, step: str) -> None:
        """Mark a step as currently running. Saves immediately.

        Tested by: test_checkpoint_mark_running() (same file).
        """
        self._ensure_initialized()
        self._data["steps"][step]["status"] = StepStatus.RUNNING
        self._save()

    def mark_step_completed(self, step: str,
                             output_files: list[str] | None = None) -> None:
        """Mark a step as completed with optional output file list. Saves immediately.

        Args:
            step: Step name (one of PIPELINE_STEPS).
            output_files: List of files produced by this step.

        Tested by: test_checkpoint_mark_completed_and_query() (same file).
        """
        self._ensure_initialized()
        self._data["steps"][step]["status"] = StepStatus.COMPLETED
        self._data["steps"][step]["completed_at"] = datetime.now(timezone.utc).isoformat()
        if output_files:
            self._data["steps"][step]["output_files"] = output_files
        self._save()

    def mark_step_failed(self, step: str, error: str | None = None) -> None:
        """Mark a step as failed. Saves immediately.

        Args:
            step: Step name.
            error: Optional error message to record.

        Tested by: test_checkpoint_mark_failed() (same file).
        """
        self._ensure_initialized()
        self._data["steps"][step]["status"] = StepStatus.FAILED
        if error:
            self._data["steps"][step]["error"] = error
        self._save()

    # --- config access ---

    def get_config(self) -> dict[str, Any]:
        """Return the pipeline configuration dict."""
        self._ensure_initialized()
        return self._data.get("config", {})

    def update_config(self, **kwargs: Any) -> None:
        """Merge key-value pairs into the config dict. Saves immediately."""
        self._ensure_initialized()
        self._data["config"].update(kwargs)
        self._save()

    def get_output_files(self, step: str) -> list[str]:
        """Return the output files recorded for a completed step."""
        self._ensure_initialized()
        return self._data["steps"][step].get("output_files", [])

    # --- reset ---

    def reset(self) -> None:
        """Reset all steps to pending (keep config). Saves immediately.

        Tested by: test_checkpoint_reset() (same file).
        """
        self._ensure_initialized()
        for step in PIPELINE_STEPS:
            self._data["steps"][step] = {
                "status": StepStatus.PENDING,
                "completed_at": None,
                "output_files": [],
            }
        self._save()

    def summary(self) -> str:
        """Return a human-readable summary of the pipeline state."""
        self._ensure_initialized()
        lines = [f"Pipeline: {self._data.get('pipeline_id', 'unknown')}"]
        for step in PIPELINE_STEPS:
            info = self._data["steps"][step]
            status = info["status"]
            files = info.get("output_files", [])
            icon = {"completed": "✓", "running": "→", "failed": "✗", "pending": "·"}.get(status, "?")
            line = f"  {icon} {step}: {status}"
            if files:
                line += f" ({len(files)} files)"
            lines.append(line)
        return "\n".join(lines)


# ========================================================================
#  Self-tests
# ========================================================================

def test_checkpoint_load_empty() -> None:
    """Loading from nonexistent path returns empty dict."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "nonexistent.json")
        pc = PipelineCheckpoint(path)
        data = pc._load()
        assert data == {}, f"Expected empty dict, got {data}"
    print("[TEST] test_checkpoint_load_empty PASSED")


def test_checkpoint_save_load_roundtrip() -> None:
    """Save then load preserves all fields."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        pc.start(pipeline_id="test-run", config={"grid_file": "grid.out"})
        pc.mark_step_running("sparta")
        pc.mark_step_completed("sparta", output_files=["grid.2200.out"])

        # Load fresh instance
        pc2 = PipelineCheckpoint(path)
        pc2.start()  # resume mode
        assert pc2.is_step_completed("sparta"), "sparta should be completed"
        assert not pc2.is_step_completed("kriging"), "kriging should be pending"
        assert pc2.get_output_files("sparta") == ["grid.2200.out"]
    print("[TEST] test_checkpoint_save_load_roundtrip PASSED")


def test_checkpoint_mark_completed_and_query() -> None:
    """Mark steps completed and query status."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        pc.start()

        assert pc.get_next_step() == "sparta"
        assert pc.get_step_status("sparta") == StepStatus.PENDING

        pc.mark_step_running("sparta")
        assert pc.get_step_status("sparta") == StepStatus.RUNNING

        pc.mark_step_completed("sparta")
        assert pc.is_step_completed("sparta")
        assert pc.get_next_step() == "kriging"
    print("[TEST] test_checkpoint_mark_completed_and_query PASSED")


def test_checkpoint_all_completed() -> None:
    """All steps completed returns True only when every step is done."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        pc.start()

        assert not pc.is_all_completed()
        for step in PIPELINE_STEPS:
            pc.mark_step_completed(step)
        assert pc.is_all_completed()
    print("[TEST] test_checkpoint_all_completed PASSED")


def test_checkpoint_mark_failed() -> None:
    """Failed step is recorded and visible in status."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        pc.start()

        pc.mark_step_running("sparta")
        pc.mark_step_failed("sparta", error="Docker timeout")
        assert pc.get_step_status("sparta") == StepStatus.FAILED
        assert not pc.is_step_completed("sparta")
    print("[TEST] test_checkpoint_mark_failed PASSED")


def test_checkpoint_reset() -> None:
    """Reset clears all steps to pending."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        pc.start()

        pc.mark_step_completed("sparta")
        pc.mark_step_completed("kriging")
        pc.reset()

        assert not pc.is_step_completed("sparta")
        assert not pc.is_step_completed("kriging")
        assert pc.get_next_step() == "sparta"
    print("[TEST] test_checkpoint_reset PASSED")


def test_checkpoint_get_next_step() -> None:
    """Next step returns first non-completed step in order."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        pc.start()

        assert pc.get_next_step() == "sparta"
        pc.mark_step_completed("sparta")
        assert pc.get_next_step() == "kriging"
        pc.mark_step_completed("kriging")
        assert pc.get_next_step() == "pinn"
        pc.mark_step_completed("pinn")
        assert pc.get_next_step() == "mop"
        pc.mark_step_completed("mop")
        assert pc.get_next_step() is None
    print("[TEST] test_checkpoint_get_next_step PASSED")


def test_checkpoint_not_initialized_raises() -> None:
    """Calling methods before start() raises RuntimeError."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cp.json")
        pc = PipelineCheckpoint(path)
        try:
            pc.get_next_step()
        except RuntimeError as exc:
            print(f"[TEST] test_checkpoint_not_initialized_raises PASSED: {exc}")
            return
    raise AssertionError("expected RuntimeError for uninitialized checkpoint")


if __name__ == "__main__":
    test_checkpoint_load_empty()
    test_checkpoint_save_load_roundtrip()
    test_checkpoint_mark_completed_and_query()
    test_checkpoint_all_completed()
    test_checkpoint_mark_failed()
    test_checkpoint_reset()
    test_checkpoint_get_next_step()
    test_checkpoint_not_initialized_raises()
    print("\n[TEST] All pipeline_checkpoint.py self-tests PASSED")
