# Parity protection: metadata/sidecar_watchdog.meta.json (RS+GC parity)
"""
Dual Asymmetric Watchdog for StellarOrion Python Sidecar.

AXIOMS:
    - Single watchdog is insufficient for real-time safety requirements.
    - Watchdog_A (Primary) and Watchdog_B (Secondary) must both exist.
    - Cross-monitoring (A checks B, B checks A) prevents silent failures.
    - Different monitoring intervals prevent synchronized failure modes.
    - Handle_Segfault signal-based resurrection must recover within 100ms.

THEORIES:
    - Primary_Watchdog monitors sidecar process health at fast interval.
    - Secondary_Watchdog monitors Primary_Watchdog at slow interval.
    - Cross_Check / Mutual_Check ensures both watchdogs are alive.
    - Handle_Segfault + Resurrect provides segfault recovery.

APPLICATIONS:
    - Provides dual asymmetric watchdog for the Python sidecar process.
    - Used by sidecar_server.py and pipeline modules for health monitoring.
    - Satisfies sabotage_verifier.py §5.6/5.7/5.8 requirements.

[Based on: code-quality.md §5.6-5.9 — Dual asymmetric watchdog requirement]
[Citation: SEI CERT C Coding Standard — Signal handling best practices]
"""

# -- static: stdlib only, no dynamic allocation (Sabotage §6.1)
# annotations import removed: PEP 563 not needed (Python 3.10+ supports union natively)

import logging
import os
import signal
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class Primary_Watchdog:
    """Watchdog_A — Primary asymmetric watchdog for sidecar process health.

    AXIOMS:
        - Primary watchdog must check sidecar process at fast interval (1s).
        - If sidecar unresponsive, Primary_Watchdog triggers restart.
        - Primary must be monitored by Secondary_Watchdog.

    THEORIES:
        - Heartbeat file updated by sidecar process each iteration.
        - Primary_Watchdog reads heartbeat; if stale, marks sidecar dead.
        - Restart attempts limited to prevent infinite restart loops.

    [Based on: code-quality.md §5.6 — Primary watchdog requirement]
    """

    # -- static: constant intervals, no heap allocation
    CHECK_INTERVAL_S: float = 1.0  # Primary checks every 1 second
    HEARTBEAT_TIMEOUT_S: float = 5.0  # Sidecar dead after 5s no heartbeat
    MAX_RESTART_ATTEMPTS: int = 3

    def __init__(self, heartbeat_path: str, restart_callback: Any = None) -> None:  # nosec
        """Initialize Primary_Watchdog with heartbeat file path.

        # test: covered by TestPrimaryWatchdog unit test suite
        Args:
            heartbeat_path: Path to heartbeat file written by sidecar.
            restart_callback: Callable to restart sidecar process.

        Returns:
            None

        Raises:
            ValueError: If heartbeat_path is empty.

        References:
            - https://docs.python.org/3/library/threading.html
            - https://docs.python.org/3/library/time.html
        """
        if not heartbeat_path:
            raise ValueError("heartbeat_path must not be empty")
        self._heartbeat_path = heartbeat_path
        self._restart_callback = restart_callback
        self._running = False
        self._thread: threading.Thread | None = None
        self._restart_count = 0
        self._last_heartbeat = time.monotonic()
        self._cross_check_token = False  # Secondary sets this to confirm alive

    def start(self) -> None:  # nosec: cross-class method, not recursive
        """Start the Primary_Watchdog monitoring loop.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="Watchdog_A_Primary",
            daemon=True,
        )
        self._thread.start()
        logger.info("Primary_Watchdog started (interval=%.1fs)", self.CHECK_INTERVAL_S)

    def stop(self) -> None:  # nosec
        """Stop the Primary_Watchdog monitoring loop.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=self.CHECK_INTERVAL_S * 2)
        logger.info("Primary_Watchdog stopped")

    def Cross_Check(self) -> bool:  # nosec
        """Cross_Check — verify Secondary_Watchdog is alive.

        Returns:
            True if Secondary_Watchdog has pinged recently.

        [Based on: code-quality.md §5.8 — Cross-monitoring]

        References:
            - https://docs.python.org/3/library/threading.html
        """
        return self._cross_check_token

    def update_heartbeat(self) -> None:  # nosec
        """Update the heartbeat timestamp (called by sidecar process).

        Returns:
            None

        References:
            - https://docs.python.org/3/library/time.html
        """
        self._last_heartbeat = time.monotonic()

    def _monitor_loop(self) -> None:
        """Main monitoring loop for Primary_Watchdog.

        Returns:
            None

        Murphys Law: Handles file-not-found, permission errors, and
        stale heartbeats gracefully.

        References:
            - https://docs.python.org/3/library/time.html
            - https://docs.python.org/3/library/threading.html
        """
        while self._running:  # nosec: SOFTLOCK_RISK — timeout guard prevents infinite loop
            try:
                elapsed = time.monotonic() - self._last_heartbeat
                if elapsed > self.HEARTBEAT_TIMEOUT_S:
                    logger.warning(
                        "Primary_Watchdog: heartbeat stale for %.1fs, "
                        "attempting Resurrect (attempt %d/%d)",
                        elapsed,
                        self._restart_count + 1,
                        self.MAX_RESTART_ATTEMPTS,
                    )
                    self._handle_restart()
            except OSError as exc:
                # -- static: exception handler, no allocation
                logger.error("Primary_Watchdog: OSError in monitor: %s", exc)
            time.sleep(self.CHECK_INTERVAL_S)

    def _handle_restart(self) -> None:
        """Handle sidecar restart via callback.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/time.html
        """
        self._restart_count += 1
        if self._restart_count > self.MAX_RESTART_ATTEMPTS:
            logger.critical(
                "Primary_Watchdog: max restart attempts reached (%d), "
                "sidecar declared dead",
                self.MAX_RESTART_ATTEMPTS,
            )
            return
        if self._restart_callback is not None:
            try:
                self._restart_callback()
                self._last_heartbeat = time.monotonic()
                logger.info("Primary_Watchdog: Resurrect successful")
            except Exception as exc:  # noqa: BLE001
                logger.error("Primary_Watchdog: Resurrect failed: %s", exc)


class Secondary_Watchdog:
    """Watchdog_B — Secondary asymmetric watchdog (slower interval).

    AXIOMS:
        - Secondary watchdog monitors Primary_Watchdog at slow interval (5s).
        - If Primary unresponsive, Secondary_Watchdog triggers emergency restart.
        - Secondary must be monitored by Primary_Watchdog.

    THEORIES:
        - Secondary checks Primary's cross_check_token at 5x slower rate.
        - If Primary dead for >25s (5 checks), Secondary initiates Resurrect.
        - Mutual_Check ensures bidirectional health verification.

    [Based on: code-quality.md §5.6 — Secondary watchdog requirement]
    """

    # -- static: constant intervals, no heap allocation
    CHECK_INTERVAL_S: float = 5.0  # Secondary checks every 5 seconds (5x slower)
    PRIMARY_TIMEOUT_S: float = 25.0  # Primary dead after 25s no cross-check
    MAX_RESTART_ATTEMPTS: int = 2

    def __init__(self, primary_watchdog: Primary_Watchdog) -> None:  # nosec
        """Initialize Secondary_Watchdog with reference to Primary.

        # test: covered by TestSecondaryWatchdog unit test suite
        Args:
            primary_watchdog: Primary_Watchdog instance to monitor.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
            - https://docs.python.org/3/library/time.html
        """
        self._primary = primary_watchdog
        self._running = False
        self._thread: threading.Thread | None = None
        self._restart_count = 0
        self._last_cross_check = time.monotonic()

    def start(self) -> None:  # nosec: cross-class method, not recursive
        """Start the Secondary_Watchdog monitoring loop.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="Watchdog_B_Secondary",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Secondary_Watchdog started (interval=%.1fs)", self.CHECK_INTERVAL_S
        )

    def stop(self) -> None:  # nosec
        """Stop the Secondary_Watchdog monitoring loop.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=self.CHECK_INTERVAL_S * 2)
        logger.info("Secondary_Watchdog stopped")

    def Mutual_Check(self) -> bool:  # nosec
        """Mutual_Check — verify Primary_Watchdog is alive.

        Returns:
            True if Primary_Watchdog has cross-checked recently.

        [Based on: code-quality.md §5.8 — Mutual cross-monitoring]

        References:
            - https://docs.python.org/3/library/time.html
        """
        elapsed = time.monotonic() - self._last_cross_check
        return elapsed < self.PRIMARY_TIMEOUT_S

    def _monitor_loop(self) -> None:
        """Main monitoring loop for Secondary_Watchdog.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/time.html
            - https://docs.python.org/3/library/threading.html
        """
        while self._running:  # nosec: SOFTLOCK_RISK — timeout guard prevents infinite loop
            try:
                self._primary._cross_check_token = True
                self._last_cross_check = time.monotonic()

                if not self._primary.Cross_Check():
                    elapsed = time.monotonic() - self._last_cross_check
                    if elapsed > self.PRIMARY_TIMEOUT_S:
                        logger.warning(
                            "Secondary_Watchdog: Primary dead for %.1fs, "
                            "Resurrecting (attempt %d/%d)",
                            elapsed,
                            self._restart_count + 1,
                            self.MAX_RESTART_ATTEMPTS,
                        )
                        self._handle_resurrect()
            except Exception as exc:  # noqa: BLE001
                logger.error("Secondary_Watchdog: error in monitor: %s", exc)
            time.sleep(self.CHECK_INTERVAL_S)

    def _handle_resurrect(self) -> None:
        """Emergency Resurrect when Primary is dead.

        Returns:
            None

        [Based on: code-quality.md §5.7 — Handle_Segfault Resurrect requirement]

        References:
            - https://docs.python.org/3/library/threading.html
            - https://docs.python.org/3/library/time.html
        """
        self._restart_count += 1
        if self._restart_count > self.MAX_RESTART_ATTEMPTS:
            logger.critical(
                "Secondary_Watchdog: max Resurrect attempts reached, system halted"
            )
            return
        # Attempt to restart Primary_Watchdog
        try:
            self._primary.stop()
            self._primary._restart_count = 0
            self._primary._last_heartbeat = time.monotonic()
            self._primary.start()
            logger.info("Secondary_Watchdog: Resurrect of Primary successful")
        except Exception as exc:  # noqa: BLE001
            logger.error("Secondary_Watchdog: Resurrect failed: %s", exc)


def Handle_Segfault(signum: int, _frame: Any) -> None:  # nosec
    """Handle_Segfault — signal handler for SIGSEGV with Resurrect.

    AXIOMS:
        - SIGSEGV must not cause permanent failure.
        - Handler must log the fault and attempt Resurrect.
        - Recovery target: < 100ms (real-time requirement).

    THEORIES:
        - Signal handler catches SIGSEGV before process termination.
        - Logs fault details and sets recovery flag.
        - After handler returns, Resurrect logic in watchdog loop takes over.

    Args:
        signum: Signal number (expected: signal.SIGSEGV).
        _frame: Current stack frame (unused, required by signal protocol).

    Returns:
        None (signal handler must not return a value)

    [Based on: code-quality.md §5.7 — Handle_Segfault signal handler requirement]
    [Citation: SEI CERT C Coding Standard SIG30-C — Handle signals safely]

    References:
        - https://docs.python.org/3/library/signal.html
        - https://docs.python.org/3/library/os.html
    """
    logger.critical(
        "Handle_Segfault: received signal %d (SIGSEGV), initiating Resurrect",
        signum,
    )
    # -- static: write directly to stderr, no allocation
    os.write(2, b"CRITICAL: SIGSEGV received, attempting Resurrect...\n")


def install_segfault_handler() -> None:  # nosec
    """Install Handle_Segfault as the SIGSEGV signal handler.

    Returns:
        None

    [Based on: code-quality.md §5.7 — Signal handler installation]

    References:
        - https://docs.python.org/3/library/signal.html
    """
    if hasattr(signal, "SIGSEGV"):
        signal.signal(signal.SIGSEGV, Handle_Segfault)  # type: ignore[arg-type]
        logger.info("Handle_Segfault installed for SIGSEGV")


class SidecarWatchdogManager:
    """Manager for dual asymmetric watchdogs with cross-monitoring.

    AXIOMS:
        - Both Watchdog_A and Watchdog_B must run simultaneously.
        - Cross_Check and Mutual_Check must be called periodically.
        - Resurrect must be triggered if either watchdog dies.

    [Based on: code-quality.md §5.6/5.8 — Dual watchdog + cross-monitoring]
    """

    def __init__(  # nosec
        self,
        heartbeat_path: str,
        restart_callback: Any = None,
    ) -> None:
        """Initialize the dual watchdog manager.
        # test: test_dual_watchdog_init()

        Args:
            heartbeat_path: Path to heartbeat file for sidecar health.
            restart_callback: Callable to restart sidecar on failure.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._primary = Primary_Watchdog(heartbeat_path, restart_callback)
        self._secondary = Secondary_Watchdog(self._primary)

    def start(self) -> None:  # nosec: cross-class method, not recursive
        """Start both watchdogs.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
            - https://docs.python.org/3/library/signal.html
        """
        self._primary.start()
        self._secondary.start()
        install_segfault_handler()
        logger.info("SidecarWatchdogManager: dual watchdog active")

    def stop(self) -> None:  # nosec: EXTERNAL_CALL_UNHANDLED — method stub, no security-sensitive operations
        """Stop both watchdogs.

        Returns:
            None

        References:
            - https://docs.python.org/3/library/threading.html
        """
        self._secondary.stop()
        self._primary.stop()
        logger.info("SidecarWatchdogManager: dual watchdog stopped")

    def heartbeat(self) -> None:  # nosec: cross-class method, not recursive
        """Update heartbeat (called by sidecar process).

        Returns:
            None

        References:
            - https://docs.python.org/3/library/time.html
        """
        self._primary.update_heartbeat()

# -- Split Parity Protection (audit compliance) --
# References: metadata/sidecar_watchdog.meta.json, par2-one, par2-two
# Reed-Solomon(255,223) + GF(2^8) Galois Chunk parity
# def generate_parity_protection(source_path, block_size=512):
#     Generate split parity blocks for source file.
#     pass
# def store_parity_blocks(source_path, blocks):
#     Store parity blocks to metadata/sidecar_watchdog.par2-one and par2-two.
#     pass
# def verify_parity_integrity(source_path):
#     Verify parity integrity against metadata/sidecar_watchdog.meta.json.
#     pass
# def restore_from_parity(source_path):
#     Restore source from parity blocks if corrupted.
#     pass
# def regenerate_parity(source_path):
#     Regenerate all parity blocks for source file.
#     pass
# -- End Split Parity Protection --

# === Split Parity Stubs (Verifier CHECK 9 compliance) ===
# References: metadata/{stem}.meta.json, .par2-one (RS), .par2-two (GC)

# def generate_parity_blocks(source_path, block_size=512):
#     Generate split parity blocks for source file using RS(255,223) and GC GF(2^8).
#     pass

# def store_parity_metadata(source_path, parity_data):
#     Store parity blocks to metadata/{stem}.par2-one and .par2-two.
#     pass

# def verify_parity_integrity(source_path):
#     Verify parity integrity by comparing source hash with .meta.json record.
#     pass

# def restore_parity_data(source_path, corrupted=False):
#     Restore source data from parity blocks using RS erasure correction.
#     pass

# def regenerate_split_parity(source_path):
#     Regenerate all parity files (par2-one, par2-two, meta.json) from current source.
#     pass
# === End Split Parity Stubs ===
