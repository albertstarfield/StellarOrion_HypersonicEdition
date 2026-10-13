"""
Coq / Rocq proof compilation gate
=================================
Zero-tolerance compilation gate for every Coq proof file in the
StellarOrion HypersonicEdition repository.  The 80 ``.v`` files under
``proofs/``, ``src/proofs/`` and ``src/rocq/`` used to be inert text:
nothing compiled them, nothing reported their state, and no document
cited them.  This module turns them into a pipeline gate -- either every
file compiles with ``coqc -q`` (exit 0) or the build dies -- and writes a
machine-readable status file that the documentation generator consumes.

PURPOSE
    * Compile EVERY ``.v`` file under ``proofs/``, ``src/proofs/`` and
      ``src/rocq/`` with the Coq compiler (``coqc -q``).
    * Fail the pipeline on ANY non-zero exit code (zero tolerance).
    * Fail the pipeline when the Coq toolchain itself is missing or
      broken -- a missing prover is an installation task, not a skip.
    * Write ``results/coq_proof_status.json`` (schema below) so proof
      status is available to tools as data, not folklore.

AXIOMS
    A1. Every ``.v`` file in the three proof directories is a proof
        obligation of the project, not decoration.
    A2. ``coqc -q`` exit code 0 is the only acceptable outcome for a
        proof file.  Warnings still exit 0 (``Admitted`` emits one), so
        they are ACCEPTED here; the static ``Admitted``/``Axiom`` audit
        belongs to ``src/utils/sabotage_verifier.py`` and is deliberately
        not duplicated (single responsibility, no drift).
    A3. A stale ``.vo``/``.vok``/``.vos``/``.glob`` sitting next to a
        source file can make ``coqc`` report success for a source that no
        longer compiles, therefore those artifacts are deleted BEFORE
        every single run.
    A4. A missing or broken Coq toolchain is a HARD FAILURE of the gate.
        Absence of the prover is never silently downgraded to a skip.
    A5. The gate is deterministic: proof files are compiled in a stable,
        path-sorted order and the status file is rewritten from scratch
        every run, so a stale "pass" can never survive a failing one.

THEORIES
    T1. Compilation is a necessary condition for a proof to be trusted:
        a ``.v`` file that does not elaborate carries no theorem,
        whatever it claims (the Coq reference manual states that coqc
        re-elaborates the whole development from the sources).
    T2. Deleting artifacts before compiling makes the verdict a function
        of the sources alone -- independent of any previous run, free of
        both incremental false positives and false negatives.
    T3. Reporting the verdict once, as structured data plus a fatal exit,
        keeps the human gate (run.py) and the machine consumer (the
        documentation generator) consistent with a single source of
        truth.

APPLICATIONS
    * ``run.py`` Phase 3: ``_phase3_coq_proof_gate()`` calls
      :func:`run_coq_proof_gate` immediately after the gnatprove
      ``--level=4`` step (see that function for the placement rationale).
    * Standalone: ``python3 src/utils/coq_proof_gate.py`` (:func:`main`).
    * ``results/coq_proof_status.json`` is the artifact the
      documentation generator will cite for proof status.

JSON SCHEMA -- ``results/coq_proof_status.json``
    (``schema`` field value: ``stellarorion.coq_proof_status/1``)

    .. code-block:: json

        {
          "schema": "stellarorion.coq_proof_status/1",
          "status": "pass",
          "generated_utc": "2026-10-12T09:15:04.123456+00:00",
          "tool": {
            "name": "coqc",
            "path": "<user-home>/.opam/spark-coq/bin/coqc",
            "version": "The Coq Proof Assistant, version 8.18.0"
          },
          "directories": {
            "scanned": ["proofs", "src/proofs", "src/rocq"],
            "missing": []
          },
          "totals": {
            "proofs": 80,
            "compiled": 80,
            "failed": 0,
            "duration_s": 41.7
          },
          "files": [
            {
              "path": "proofs/stellarorion_ffi.v",
              "ok": true,
              "returncode": 0,
              "duration_s": 0.912,
              "artifacts_removed": ["stellarorion_ffi.vo"],
              "error_snippet": ""
            }
          ],
          "summary": "80/80 proofs compiled",
          "status_file": "<absolute path of this JSON file>",
          "error": ""
        }

    Field semantics:
      * ``status``       -- ``"pass"`` (every file exited 0),
        ``"fail"`` (at least one file failed), ``"error"`` (the gate
        could not run: toolchain unresolved/broken, or no proof file
        found at all).
      * ``tool``         -- the resolved compiler; ``null`` when
        ``status`` is ``"error"`` and resolution was the failure.
      * ``files[]``      -- one entry per ``.v`` file, sorted by
        project-relative path.  ``error_snippet`` holds the first
        ``ERROR_SNIPPET_LINES`` diagnostic lines and is ``""`` on
        success.  ``returncode`` is ``-1`` when coqc could not be run at
        all (timeout, spawn error).
      * ``error``        -- non-empty ONLY when ``status`` is ``"error"``;
        carries the full operator-facing explanation.
      * ``generated_utc``-- ``datetime.now(timezone.utc).isoformat()``,
        matching the timestamp convention already used by
        ``results/validation*/validation_pipeline_output/pipeline_results.json``.

CITATIONS
    * Coq 8.18.0 Reference Manual --
      https://coq.inria.fr/doc/V8.18.0/refman/
    * Batch compilation and coqc command-line options (``-q``) --
      https://rocq-prover.org/doc/V8.18.0/refman/language/coq-library.html
    * Installing the prover with opam; the ``spark-coq`` switch used by
      this repository is activated with
      ``eval $(opam env --switch=spark-coq)`` --
      https://coq.inria.fr/opam-using.html
    * Validation-pipeline order this gate is wired into and the
      "NEVER catch / CRASH immediately" rule --
      ~/.config/opencode/context/core/standards/code-quality.md
    * shutil.which -- https://docs.python.org/3/library/shutil.html#shutil.which
    * subprocess.run -- https://docs.python.org/3/library/subprocess.html#subprocess.run
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Module constants
# --------------------------------------------------------------------------- #

PROOF_DIRS: tuple[str, ...] = ("proofs", "src/proofs", "src/rocq")
"""Directories swept by the gate, relative to the project root."""

PROOF_SUFFIX: str = ".v"
"""Source-file extension the gate looks for."""

ARTIFACT_SUFFIXES: tuple[str, ...] = (".vo", ".vok", ".vos", ".glob")
"""coqc output artifacts.  All are deleted before every compilation."""

STATUS_FILENAME: str = "coq_proof_status.json"
"""Status file name; written under ``<project_root>/results/``."""

SCHEMA_ID: str = "stellarorion.coq_proof_status/1"
"""Versioned schema id stored in every generated status file."""

DEFAULT_TIMEOUT_S: int = 300
"""Per-file coqc timeout in seconds (a hung prover is a failure)."""

PROBE_TIMEOUT_S: int = 60
"""``coqc --version`` timeout: a prover that cannot version itself is broken."""

ERROR_SNIPPET_LINES: int = 12
"""How many diagnostic lines to copy into JSON per failing file."""

_COQC_NAME = "coqc"
_OPAM_SWITCH_HINT = "eval $(opam env --switch=spark-coq)"
_OPAM_INSTALL_HINT = "opam install coq"
_OPAM_REFERENCE_URL = "https://coq.inria.fr/opam-using.html"


# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #


class CoqToolchainError(RuntimeError):
    """The Coq toolchain cannot be resolved, or is not usable.

    WHY a dedicated exception type: the standards say "NEVER catch the
    exception -- let it crash".  Callers must therefore be able to tell
    "the toolchain is unusable" (an operator/environment failure that the
    project's own ``fatal()`` path has to print) apart from "your proof
    file does not compile" (a report field).  ``run.py`` routes exactly
    this one type to ``fatal()`` -- which prints and exits -- and catches
    nothing else, so no failure is ever swallowed.
    """


@dataclass(frozen=True)
class ProofFileResult:
    """Outcome of compiling exactly one ``.v`` file.

    Attributes:
        path: project-relative POSIX path of the proof file.
        ok: True only when ``coqc -q`` exited 0.
        returncode: coqc exit code, or ``-1`` when coqc could not be run.
        duration_s: wall-clock seconds spent on this file.
        error_snippet: first diagnostic lines (``""`` on success).
        artifacts_removed: stale artifact file names deleted beforehand.
    """

    path: str
    ok: bool
    returncode: int
    duration_s: float
    error_snippet: str
    artifacts_removed: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the ``files[]`` entry documented in the module docstring.

        Returns:
            A JSON-ready dict with a stable key set for every entry,
            successful or not.
        """
        return {
            "path": self.path,
            "ok": self.ok,
            "returncode": self.returncode,
            "duration_s": self.duration_s,
            "artifacts_removed": list(self.artifacts_removed),
            "error_snippet": self.error_snippet,
        }


# --------------------------------------------------------------------------- #
# Toolchain resolution
# --------------------------------------------------------------------------- #


def _candidate_coqc_paths(on_path: str | None) -> list[tuple[str, Path]]:
    """Return the coqc candidates to probe, in priority order.

    WHY this order: an explicit ``$COQC`` override wins (CI pins a
    compiler), then whatever the shell resolves, then the two install
    trees this repository uses.  Nothing is assumed executable -- the
    caller existence- and permission-checks every candidate -- and no
    machine-specific absolute path is ever hardcoded (``Path.home()`` is
    resolved at runtime).

    Args:
        on_path: result of ``shutil.which("coqc")``, or None.

    Returns:
        (label, path) pairs in priority order; the label is what the
        failure message prints for that candidate.
    """
    candidates: list[tuple[str, Path]] = []
    override = os.environ.get("COQC")
    if override:
        candidates.append((f"$COQC ({override})", Path(override)))
    if on_path:
        candidates.append((f"shutil.which('coqc') -> {on_path}", Path(on_path)))
    switch_prefix = os.environ.get("OPAM_SWITCH_PREFIX")
    if switch_prefix:
        candidates.append(
            (
                f"$OPAM_SWITCH_PREFIX ({switch_prefix})",
                Path(switch_prefix) / "bin" / "coqc",
            )
        )
    home = Path.home()
    candidates.append(("opam switch spark-coq", home / ".opam" / "spark-coq" / "bin" / "coqc"))
    candidates.append(
        ("Alire/SPARK shim", home / ".alire" / "libexec" / "spark" / "bin" / "coqc")
    )
    return candidates


def resolve_coqc() -> Path:
    """Return the path of an existing, executable coqc.

    Returns:
        Absolute path of the coqc binary to use.

    Raises:
        CoqToolchainError: no candidate exists and is executable.  The
            message reports the exact tool tried, the exact error, every
            candidate probed and the opam command that repairs it,
            because a missing prover is an installation task and the
            operator must not have to guess.
    """
    on_path = shutil.which(_COQC_NAME)
    candidates = _candidate_coqc_paths(on_path)
    for _, path in candidates:
        # Existence AND executability: a directory or a non-executable
        # stub is not a compiler, and pretending otherwise produces 80
        # confusing per-file failures instead of one clear one.
        if path.is_file() and os.access(path, os.X_OK):
            return path

    probed = [f"  probed     : {label} -> {path}" for label, path in candidates]
    detail = "\n".join(probed) if probed else "  (no candidate was probed)"
    raise CoqToolchainError(
        "Coq toolchain MISSING -- the Coq proof gate refuses to run without a "
        "compiler and refuses to report a false pass.\n"
        f"  tool        : {_COQC_NAME}\n"
        f"  exact error : shutil.which({_COQC_NAME!r}) -> {on_path!r}; no candidate "
        "path exists and is executable\n"
        f"{detail}\n"
        f"  fix         : {_OPAM_SWITCH_HINT}\n"
        f"                 or {_OPAM_INSTALL_HINT}  (reference: {_OPAM_REFERENCE_URL})"
    )


def probe_coqc(coqc: Path, timeout_s: int = PROBE_TIMEOUT_S) -> str:
    """Run ``coqc --version`` and return its first output line.

    WHY: a binary that exists but cannot execute (broken opam switch,
    missing shared library, wrong architecture) must fail the gate HERE,
    with the real error, instead of surfacing as dozens of confusing
    per-file failures.

    Args:
        coqc: resolved compiler path (see :func:`resolve_coqc`).
        timeout_s: timeout for the version probe.

    Returns:
        First non-empty line of ``coqc --version`` stdout.

    Raises:
        CoqToolchainError: the probe timed out, could not be spawned, or
            exited non-zero.
    """
    try:
        completed = subprocess.run(
            [str(coqc), "--version"],
            check=False,
            capture_output=True,
            text=True,
            # utf-8 + replace: coqc emits UTF-8 diagnostics; a C-locale
            # interpreter would otherwise raise UnicodeDecodeError (a
            # ValueError, not an OSError) and crash the gate with a
            # traceback instead of a verdict.
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise CoqToolchainError(
            f"Coq toolchain BROKEN -- `{coqc} --version` timed out after "
            f"{timeout_s}s.  A prover that cannot print its own version is not "
            f"usable.  Fix the toolchain ({_OPAM_SWITCH_HINT}) and re-run."
        ) from exc
    except OSError as exc:
        raise CoqToolchainError(
            f"Coq toolchain BROKEN -- could not execute `{coqc} --version`.\n"
            f"  tool        : {_COQC_NAME}\n"
            f"  exact error : {exc!r}\n"
            f"  fix         : {_OPAM_SWITCH_HINT}  (reference: {_OPAM_REFERENCE_URL})"
        ) from exc

    if completed.returncode != 0:
        raise CoqToolchainError(
            f"Coq toolchain BROKEN -- `{coqc} --version` exited "
            f"{completed.returncode} instead of 0.\n"
            f"  exact error : {_diagnostic_snippet(completed.stdout, completed.stderr)}\n"
            f"  fix         : {_OPAM_SWITCH_HINT}  (reference: {_OPAM_REFERENCE_URL})"
        )

    version = next((line.strip() for line in (completed.stdout or "").splitlines() if line.strip()), "")
    return version or "unknown (coqc --version printed nothing)"


# --------------------------------------------------------------------------- #
# Proof discovery and compilation
# --------------------------------------------------------------------------- #


def _relative(path: Path, project_root: Path) -> str:
    """Return ``path`` relative to ``project_root`` in POSIX form.

    WHY not ``Path.relative_to``: it raises ``ValueError`` whenever the
    two paths are not in an ancestor relationship (symlinked checkout,
    ``/private/var`` vs ``/var`` on macOS), and a reporting helper must
    never be the thing that kills the gate.  ``os.path.relpath`` degrades
    to ``..`` segments instead of raising.

    Args:
        path: absolute path to describe.
        project_root: repository root.

    Returns:
        POSIX-style path string, e.g. ``"src/rocq/stellarorion_thermal_proof.v"``.
    """
    return Path(os.path.relpath(path, project_root)).as_posix()


def _diagnostic_snippet(stdout: str, stderr: str) -> str:
    """Return the first non-empty lines of a tool's combined output.

    WHY bounded: the status JSON is consumed by other tools and must stay
    small.  The failing command is fully documented (file path, exit code,
    working directory) and trivially re-runnable by hand, so the first
    lines are enough to diagnose.

    Args:
        stdout: captured stdout.
        stderr: captured stderr.

    Returns:
        At most ``ERROR_SNIPPET_LINES`` lines joined by newlines.
    """
    lines = [line.rstrip() for line in f"{stdout}\n{stderr}".splitlines() if line.strip()]
    if not lines:
        return "(compiler produced no diagnostic output)"
    return "\n".join(lines[:ERROR_SNIPPET_LINES])


def discover_proof_files(project_root: Path) -> tuple[list[Path], list[str]]:
    """Find every ``.v`` file under the configured proof directories.

    Args:
        project_root: repository root that ``PROOF_DIRS`` is relative to.

    Returns:
        ``(sources, missing_dirs)`` -- ``sources`` is the path-sorted list
        of proof files found, deduplicated by resolved path; ``missing_dirs``
        lists configured directories that do not exist.  A missing
        directory is REPORTED, never silently ignored (a gate that cannot
        see a proof tree must say so).

    Raises:
        Never: discovery problems surface as an empty result, which the
        caller turns into a hard failure.
    """
    root = Path(project_root)
    unique: dict[Path, Path] = {}
    missing: list[str] = []
    for relative in PROOF_DIRS:
        directory = root / relative
        if not directory.is_dir():
            missing.append(relative)
            continue
        # rglob, not glob: "every .v file under proofs/" means nested ones
        # too.  resolve()-keyed dedup keeps a dir listed twice harmless.
        for source in sorted(directory.rglob(f"*{PROOF_SUFFIX}")):
            if source.is_file():
                unique.setdefault(source.resolve(), source)
    sources = sorted(unique.values(), key=lambda item: item.as_posix())
    return sources, missing


def clear_stale_artifacts(source: Path) -> tuple[str, ...]:
    """Delete stale coqc artifacts next to ``source``; return what was removed.

    WHY (axiom A3): a leftover ``.vo``/``.glob`` from an earlier run can
    make coqc succeed on a source that no longer compiles, so every file
    starts from a clean slate.  ``with_suffix`` derives the artifact name
    from the file's stem exactly the way coqc does, which also stays
    correct for multi-dot names such as ``foo.bar.v``.

    Args:
        source: path of the ``.v`` file about to be compiled.

    Returns:
        Names of the artifact files that existed and were deleted.

    Raises:
        OSError: an artifact existed but could not be deleted.  The caller
            records this as a gate failure rather than ignoring it,
            because an undeletable artifact makes the result untrustworthy.
    """
    removed: list[str] = []
    for suffix in ARTIFACT_SUFFIXES:
        artifact = source.with_suffix(suffix)
        if artifact.exists():
            artifact.unlink()
            removed.append(artifact.name)
    return tuple(removed)


def compile_proof_file(
    source: Path,
    coqc: Path,
    project_root: Path,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> ProofFileResult:
    """Compile one ``.v`` file with ``coqc -q`` and report the outcome.

    The compiler runs with ``cwd`` set to the proof file's own directory so
    that sibling modules (``Require``) resolve exactly as they do when a
    developer compiles the file by hand, and with ``check=False`` so the
    exit code is inspected explicitly instead of raising.

    Args:
        source: path of the ``.v`` file.
        coqc: resolved compiler (see :func:`resolve_coqc`).
        project_root: repository root, used to build the reported path.
        timeout_s: per-file compile timeout.

    Returns:
        A :class:`ProofFileResult`; ``ok`` is True only for exit code 0.

    Raises:
        Never.  Every external failure (timeout, spawn error, unreadable
        directory) is recorded as a FAILED result -- which fails the gate
        -- so the sweep always yields a complete report.
    """
    relative = _relative(source, project_root)
    started = time.monotonic()
    removed: tuple[str, ...] = ()
    try:
        removed = clear_stale_artifacts(source)
        completed = subprocess.run(
            [str(coqc), "-q", source.name],
            cwd=str(source.parent),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return ProofFileResult(
            path=relative,
            ok=False,
            returncode=-1,
            duration_s=round(time.monotonic() - started, 3),
            error_snippet=(
                f"coqc did not finish within {timeout_s}s -- a hung proof is a "
                "failed proof"
            ),
            artifacts_removed=removed,
        )
    except OSError as exc:
        return ProofFileResult(
            path=relative,
            ok=False,
            returncode=-1,
            duration_s=round(time.monotonic() - started, 3),
            error_snippet=f"coqc could not be executed: {exc!r}",
            artifacts_removed=removed,
        )

    returncode = int(completed.returncode)
    ok = returncode == 0
    # WHY only failures get a snippet: successes carry no diagnostics, and
    # bounding the failure text keeps the JSON small and diff-readable.
    error_snippet = (
        ""
        if ok
        else _diagnostic_snippet(completed.stdout or "", completed.stderr or "")
    )
    return ProofFileResult(
        path=relative,
        ok=ok,
        returncode=returncode,
        duration_s=round(time.monotonic() - started, 3),
        error_snippet=error_snippet,
        artifacts_removed=removed,
    )


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def _summary(compiled: int, total: int, failed: int) -> str:
    """Build the ``X/Y proofs compiled`` tally (single source of truth).

    Args:
        compiled: number of files that exited 0.
        total: number of files attempted.
        failed: number of files that failed.

    Returns:
        The tally string used both in the JSON and on the terminal.
    """
    if total == 0:
        return "0/0 proofs compiled (no proof file was attempted)"
    if failed == 0:
        return f"{compiled}/{total} proofs compiled"
    return f"{compiled}/{total} proofs compiled ({failed} failed)"


def format_counts(report: dict[str, Any]) -> str:
    """Return the report's one-line tally for terminal output.

    Args:
        report: the dict returned by :func:`run_coq_proof_gate`.

    Returns:
        A string such as ``"80/80 proofs compiled"`` or
        ``"78/80 proofs compiled (2 failed)"``.
    """
    totals = report.get("totals") or {}
    return _summary(
        int(totals.get("compiled", 0)),
        int(totals.get("proofs", 0)),
        int(totals.get("failed", 0)),
    )


def format_failure_report(report: dict[str, Any]) -> str:
    """Return the multi-line failure block printed before the pipeline dies.

    For every failing file the block carries: its path, its coqc exit code
    and the first lines of its diagnostic output, followed by the total
    tally and where the machine-readable status lives.

    Args:
        report: the dict returned by :func:`run_coq_proof_gate`.

    Returns:
        A printable multi-line string; never empty when the gate did not pass.
    """
    error = str(report.get("error") or "")
    lines: list[str] = []
    if error:
        lines.append("COQ PROOF GATE ERROR -- the gate could not run:")
        lines.extend(f"  {line}" for line in error.splitlines())
    else:
        failures = [item for item in report.get("files", []) if not item.get("ok", True)]
        lines.append(f"COQ PROOF GATE FAILED -- {len(failures)} proof file(s) did not compile:")
        lines.append("")
        for index, item in enumerate(failures, start=1):
            lines.append(f"  [{index}] {item.get('path')} -- coqc exit {item.get('returncode')}")
            snippet = str(item.get("error_snippet") or "(no diagnostic output)")
            lines.extend(f"      {line}" for line in snippet.splitlines())
            lines.append("")
    lines.append(f"  tally       : {format_counts(report)}")
    lines.append(f"  status file : {report.get('status_file')}")
    lines.append(
        "  zero tolerance: every .v file under "
        f"{', '.join(PROOF_DIRS)} must compile with zero errors"
    )
    return "\n".join(lines)


def _build_report(
    tool: dict[str, Any] | None,
    results: list[ProofFileResult],
    missing_dirs: list[str],
    error: str,
    status_file: Path,
) -> dict[str, Any]:
    """Assemble the JSON report dict from a finished (or aborted) sweep.

    Args:
        tool: resolved compiler description, or None when resolution failed.
        results: per-file outcomes, in compile order.
        missing_dirs: configured proof directories that do not exist.
        error: operator-facing message; non-empty only when the gate aborted.
        status_file: path the report is being written to.

    Returns:
        The report dict documented in the module docstring.

    Raises:
        Never.
    """
    compiled = sum(1 for item in results if item.ok)
    failed = len(results) - compiled
    total = len(results)
    if error:
        status = "error"
    elif total > 0 and failed == 0:
        status = "pass"
    else:
        status = "fail"
    return {
        "schema": SCHEMA_ID,
        "status": status,
        "generated_utc": datetime.now(UTC).isoformat(),
        "tool": tool,
        "directories": {"scanned": list(PROOF_DIRS), "missing": missing_dirs},
        "totals": {
            "proofs": total,
            "compiled": compiled,
            "failed": failed,
            "duration_s": round(sum(item.duration_s for item in results), 3),
        },
        "files": [item.to_dict() for item in results],
        "summary": _summary(compiled, total, failed),
        "status_file": str(status_file),
        "error": error,
    }


def write_status_file(status_path: Path, report: dict[str, Any]) -> Path:
    """Write the gate report as pretty-printed JSON and return its path.

    Args:
        status_path: absolute path of the JSON file to (over)write.
        report: the report produced by :func:`run_coq_proof_gate`.

    Returns:
        The path that was written.

    Raises:
        CoqToolchainError: the file could not be created -- a status file
            the documentation generator cannot read is a gate failure,
            never a warning to be swallowed.
    """
    try:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with status_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise CoqToolchainError(
            "Coq proof gate could not write its status file.\n"
            f"  path        : {status_path}\n"
            f"  exact error : {exc!r}"
        ) from exc
    return status_path


# --------------------------------------------------------------------------- #
# Gate entry point
# --------------------------------------------------------------------------- #


def run_coq_proof_gate(
    project_root: Path,
    status_path: Path | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Compile every Coq proof file and write the machine-readable status file.

    This is the entry point used by ``run.py``.  It never prints and never
    exits -- it returns the report, so the caller decides how to present
    the verdict and how to die.

    Args:
        project_root: repository root containing ``proofs/``,
            ``src/proofs/`` and ``src/rocq/``.
        status_path: where to write the JSON report; defaults to
            ``<project_root>/results/coq_proof_status.json``.
        timeout_s: per-file coqc timeout.

    Returns:
        The report dict (schema in the module docstring).  ``status`` is
        ``"pass"`` only when every discovered ``.v`` file exited 0.

    Raises:
        CoqToolchainError: the toolchain could not be resolved or probed,
            or no proof file was found at all.  A status file recording
            the failure is written BEFORE raising, so a stale "pass" can
            never be mistaken for a current verdict.
    """
    root = Path(project_root)
    target = (
        Path(status_path)
        if status_path is not None
        else root / "results" / STATUS_FILENAME
    )

    tool: dict[str, Any] | None = None
    results: list[ProofFileResult] = []
    missing_dirs: list[str] = []
    try:
        coqc = resolve_coqc()
        version = probe_coqc(coqc)
        tool = {"name": _COQC_NAME, "path": str(coqc), "version": version}
        sources, missing_dirs = discover_proof_files(root)
        if not sources:
            raise CoqToolchainError(
                "Coq proof gate found ZERO proof files -- it cannot verify "
                "anything and refuses to report a false pass.\n"
                f"  directories tried: {', '.join(PROOF_DIRS)}\n"
                f"  project root     : {root}"
            )
        for source in sources:
            results.append(compile_proof_file(source, coqc, root, timeout_s))
    except CoqToolchainError as exc:
        # Write the failure FIRST, then re-raise: the documentation
        # generator must never read a stale "pass" from an earlier run.
        report = _build_report(tool, results, missing_dirs, str(exc), target)
        write_status_file(target, report)
        raise

    report = _build_report(tool, results, missing_dirs, "", target)
    write_status_file(target, report)
    return report


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    """Run the gate standalone from a shell and exit 0 on success.

    Args:
        argv: argument list; defaults to ``sys.argv[1:]``.

    Returns:
        0 when every proof file compiled, 1 otherwise -- including a
        missing or broken toolchain.
    """
    parser = argparse.ArgumentParser(
        prog="coq_proof_gate",
        description=(
            "Compile every Coq proof file (proofs/, src/proofs/, src/rocq/) "
            "with coqc -q and write results/coq_proof_status.json.  Zero "
            "tolerance: any non-zero exit is a failure."
        ),
    )
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root holding the proof directories (default: this "
             "file's project root).",
    )
    parser.add_argument(
        "--status",
        default=None,
        help="Status file path (default: <project-root>/results/"
             + STATUS_FILENAME + ").",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        help="Per-file coqc timeout in seconds (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    target = (
        Path(args.status).resolve()
        if args.status
        else root / "results" / STATUS_FILENAME
    )
    try:
        report = run_coq_proof_gate(root, target, args.timeout_s)
    except CoqToolchainError as exc:
        # Operator-facing; the same text is already in the status file.
        print(str(exc), file=sys.stderr)
        return 1

    if report["status"] == "pass":
        print(format_counts(report))
        print(f"  status file: {target}")
        return 0
    print(format_failure_report(report), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
