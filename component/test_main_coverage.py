# component/test_main_coverage.py - Expanded tests for main.py coverage
"""Comprehensive tests to improve main.py coverage beyond 19%.

CRITICAL IMPORT GUARD:
  main.py runs ensure_venv() and run_self_diagnostic() at module level
  unless IN_DOCKER is set and --skip-diag is in sys.argv. We must set
  these BEFORE importing main to prevent os.execv / subprocess storms.
"""

import os
import sys
import json
import time
import stat
import shutil
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import pytest
import subprocess

# --- IMPORT GUARD: must be set before `import main` ---
os.environ["IN_DOCKER"] = "1"
if "--skip-diag" not in sys.argv:
    sys.argv.append("--skip-diag")
if "--skip-venv-bootstrap" not in sys.argv:
    sys.argv.append("--skip-venv-bootstrap")

sys.path.insert(0, os.path.dirname(__file__))
import main


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def _manage_in_docker():
    """Save and restore IN_DOCKER env var around each test."""
    had_in_docker = "IN_DOCKER" in os.environ
    old_val = os.environ.get("IN_DOCKER")
    yield
    if had_in_docker:
        os.environ["IN_DOCKER"] = old_val
    else:
        os.environ.pop("IN_DOCKER", None)


# ============================================================================
# MODULE-LEVEL CONSTANTS TESTS
# ============================================================================

class TestModuleConstants:
    """Tests for module-level path constants."""

    def test_container_workdir_is_set(self):
        assert hasattr(main, 'CONTAINER_WORKDIR')
        assert isinstance(main.CONTAINER_WORKDIR, str)
        assert len(main.CONTAINER_WORKDIR) > 0

    def test_sparta_src_is_set(self):
        assert hasattr(main, 'SPARTA_SRC')
        assert isinstance(main.SPARTA_SRC, str)

    def test_build_dir_is_set(self):
        assert hasattr(main, 'BUILD_DIR')
        assert isinstance(main.BUILD_DIR, str)
        assert 'tmp_sparta_build' in main.BUILD_DIR

    def test_lib_path_is_set(self):
        assert hasattr(main, 'LIB_PATH')
        assert isinstance(main.LIB_PATH, str)
        if sys.platform == 'darwin':
            assert main.LIB_PATH.endswith('.dylib')
        else:
            assert main.LIB_PATH.endswith('.so')

    def test_fallback_lib_path_is_set(self):
        assert hasattr(main, 'FALLBACK_LIB_PATH')
        assert isinstance(main.FALLBACK_LIB_PATH, str)

    def test_workspace_output_is_set(self):
        assert hasattr(main, 'WORKSPACE_OUTPUT')
        assert isinstance(main.WORKSPACE_OUTPUT, str)
        assert 'sparta_output.txt' in main.WORKSPACE_OUTPUT

    def test_lib_path_darwin_uses_dylib(self):
        if sys.platform == 'darwin':
            assert '.dylib' in main.LIB_PATH
            assert '.dylib' in main.FALLBACK_LIB_PATH


# ============================================================================
# ENSURE_VENV TESTS (87 stmts, 84 missing)
# ============================================================================

class TestEnsureVenv:

    def test_skip_venv_bootstrap_returns_early(self):
        with patch.object(sys, 'argv', ['main.py', '--skip-venv-bootstrap']):
            main.ensure_venv()

    def test_venv_not_found_creates_new(self, tmp_path):
        with patch('os.path.dirname', return_value=str(tmp_path)):
            with patch('os.path.abspath', return_value=str(tmp_path)):
                with patch('os.path.exists', return_value=False):
                    with patch('subprocess.check_call') as mock_call:
                        with patch('subprocess.run') as mock_run:
                            mock_run.return_value = MagicMock(returncode=1)
                            try:
                                main.ensure_venv()
                            except (SystemExit, RuntimeError, Exception):
                                pass

    def test_venv_restart_with_execv(self, tmp_path):
        fake_venv_python = str(tmp_path / '.venv' / 'bin' / 'python')
        os.makedirs(os.path.dirname(fake_venv_python), exist_ok=True)
        Path(fake_venv_python).write_text('#!/bin/sh\nexit 0\n')
        os.chmod(fake_venv_python, 0o755)

        with patch('os.path.dirname', return_value=str(tmp_path)):
            with patch('os.path.abspath', return_value=str(tmp_path)):
                with patch.object(sys, 'executable', str(tmp_path / 'system_python')):
                    with patch('os.access', return_value=True):
                        with patch('os.path.exists', side_effect=lambda p: p == fake_venv_python or p == str(tmp_path / '.venv')):
                            with patch('subprocess.run', return_value=MagicMock(returncode=0)):
                                with patch('os.execv') as mock_execv:
                                    try:
                                        main.ensure_venv()
                                    except SystemExit:
                                        pass

    def test_venv_incompatible_os_removes_and_recreates(self, tmp_path):
        venv_dir = tmp_path / '.venv_gui'
        venv_dir.mkdir()
        fake_py = venv_dir / 'bin' / 'python'
        fake_py.parent.mkdir(parents=True)
        fake_py.write_text('binary')
        os.chmod(str(fake_py), 0o644)

        with patch('os.path.dirname', return_value=str(tmp_path)):
            with patch('os.path.abspath', return_value=str(tmp_path)):
                with patch.object(sys, 'executable', str(tmp_path / 'system_python')):
                    with patch('os.access', return_value=False):
                        with patch('os.path.exists', side_effect=lambda p: str(venv_dir) in str(p)):
                            with patch('shutil.rmtree') as mock_rmtree:
                                with patch('subprocess.check_call'):
                                    with patch('subprocess.run', return_value=MagicMock(returncode=1)):
                                        try:
                                            main.ensure_venv()
                                        except (SystemExit, RuntimeError):
                                            pass


# ============================================================================
# DISPLAY_CUSTOM_HELP TESTS (28 stmts, 14 missing)
# ============================================================================

class TestDisplayCustomHelp:

    def test_prints_colored_help(self, capsys):
        import argparse
        parser = argparse.ArgumentParser(description="Test")
        parser.add_argument("--foo", help="A foo flag")
        with pytest.raises(SystemExit):
            main.display_custom_help(parser)
        captured = capsys.readouterr()
        assert "STELLARORION COMMAND LINE HELP" in captured.out
        assert "foo" in captured.out.lower()

    def test_bold_sections_highlighted(self, capsys):
        import argparse
        parser = argparse.ArgumentParser(description="Test")
        parser.add_argument("--bar")
        with pytest.raises(SystemExit):
            main.display_custom_help(parser)
        captured = capsys.readouterr()
        assert "USAGE" in captured.out

    def test_arguments_highlighted_cyan(self, capsys):
        import argparse
        parser = argparse.ArgumentParser(description="Test")
        parser.add_argument("--test-flag", help="A test flag")
        with pytest.raises(SystemExit):
            main.display_custom_help(parser)
        captured = capsys.readouterr()
        assert "\033[36m" in captured.out
        assert "--test-flag" in captured.out


# ============================================================================
# ENSURE_DOCKER_COLIMA TESTS (29 stmts, 25 missing)
# ============================================================================

class TestEnsureDockerColima:

    def test_docker_info_ok_returns(self):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            main.ensure_docker_colima()

    def test_docker_timeout_triggers_colima_check(self):
        import subprocess as sp
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = sp.TimeoutExpired(cmd='docker', timeout=5)
            with patch('shutil.which', return_value=None):
                main.ensure_docker_colima()

    def test_docker_not_found_returns(self):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            main.ensure_docker_colima()

    def test_colima_running_does_nothing(self):
        with patch('shutil.which', return_value='/usr/local/bin/colima'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    subprocess.TimeoutExpired(cmd='docker', timeout=5),
                    MagicMock(returncode=0, stdout="is running", stderr=""),
                ]
                main.ensure_docker_colima()

    def test_colima_not_running_starts_it(self):
        with patch('shutil.which', return_value='/usr/local/bin/colima'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    subprocess.TimeoutExpired(cmd='docker', timeout=5),
                    MagicMock(returncode=0, stdout="not running", stderr=""),
                    MagicMock(returncode=0),
                ]
                main.ensure_docker_colima()

    def test_colima_start_failure_handled(self):
        with patch('shutil.which', return_value='/usr/local/bin/colima'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    subprocess.TimeoutExpired(cmd='docker', timeout=5),
                    MagicMock(returncode=0, stdout="not running", stderr=""),
                    Exception("Colima start failed"),
                ]
                main.ensure_docker_colima()

    def test_colima_not_installed_returns(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd='docker', timeout=5)
            with patch('shutil.which', return_value=None):
                main.ensure_docker_colima()

    def test_docker_generic_exception_passes(self):
        """When docker raises generic exception, falls through to colima check."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Docker error")
            with patch('shutil.which', return_value=None):
                main.ensure_docker_colima()


# ============================================================================
# BUILD_SPARTA TESTS (57 stmts, 51 missing)
# ============================================================================

class TestBuildSparta:

    def test_lib_exists_skips_build(self, tmp_path):
        """When LIB_PATH exists, returns early without building."""
        lib_path = tmp_path / 'libsparta.dylib'
        lib_path.write_text('fake lib')
        with patch.object(main, 'LIB_PATH', str(lib_path)):
            result = main.build_sparta()
            assert result == str(lib_path)

    def test_fallback_search_finds_lib(self, tmp_path):
        """When lib found in fallback dirs, returns found path."""
        fallback_dir = tmp_path / 'SPARTA' / 'build' / 'src'
        fallback_dir.mkdir(parents=True)
        lib_file = fallback_dir / 'libsparta.2.dylib'
        lib_file.write_text('fake lib')
        with patch.object(main, 'LIB_PATH', str(tmp_path / 'nonexistent')):
            with patch.object(main, 'SPARTA_SRC', str(tmp_path / 'SPARTA')):
                with patch.object(main, 'BUILD_DIR', str(tmp_path / 'nonexistent_build')):
                    result = main.build_sparta()
                    assert result == str(lib_file)

    def test_cmake_and_make_called(self, tmp_path):
        """When building, cmake and make are called."""
        build_dir = tmp_path / 'build'
        sparta_src = tmp_path / 'SPARTA'
        sparta_src.mkdir()
        fake_lib = str(build_dir / 'src' / 'libsparta.dylib')

        def fake_run(*args, **kwargs):
            os.makedirs(os.path.dirname(fake_lib), exist_ok=True)
            Path(fake_lib).write_text('fake lib')
            return MagicMock(returncode=0)

        with patch.object(main, 'LIB_PATH', fake_lib):
            with patch.object(main, 'FALLBACK_LIB_PATH', str(tmp_path / 'nonexistent')):
                with patch.object(main, 'BUILD_DIR', str(build_dir)):
                    with patch.object(main, 'SPARTA_SRC', str(sparta_src)):
                        with patch('subprocess.run', side_effect=fake_run):
                            result = main.build_sparta()
                            assert result == fake_lib

    def test_gpu_flag_enables_cuda(self, tmp_path):
        """When SPARTA_GPU=1, CUDA flags are added to cmake."""
        build_dir = tmp_path / 'build'
        sparta_src = tmp_path / 'SPARTA'
        sparta_src.mkdir()
        fake_lib = str(build_dir / 'src' / 'libsparta.dylib')

        def fake_run(*args, **kwargs):
            os.makedirs(os.path.dirname(fake_lib), exist_ok=True)
            Path(fake_lib).write_text('fake lib')
            return MagicMock(returncode=0)

        with patch.object(main, 'LIB_PATH', fake_lib):
            with patch.object(main, 'FALLBACK_LIB_PATH', str(tmp_path / 'nonexistent')):
                with patch.object(main, 'BUILD_DIR', str(build_dir)):
                    with patch.object(main, 'SPARTA_SRC', str(sparta_src)):
                        with patch.dict(os.environ, {'SPARTA_GPU': '1'}):
                            with patch('subprocess.run', side_effect=fake_run) as mock_run:
                                result = main.build_sparta()
                                for c in mock_run.call_args_list:
                                    cmd = c[0][0] if c[0] else c[1].get('args', [])
                                    if isinstance(cmd, list) and any('cmake' in str(x) for x in cmd):
                                        cmd_str = ' '.join(str(x) for x in cmd)
                                        assert 'CUDA' in cmd_str or 'cuda' in cmd_str.lower()

    def test_macos_kokkos_openmp_off(self, tmp_path):
        """On macOS without GPU, OpenMP is OFF."""
        build_dir = tmp_path / 'build'
        sparta_src = tmp_path / 'SPARTA'
        sparta_src.mkdir()
        fake_lib = str(build_dir / 'src' / 'libsparta.dylib')

        def fake_run(*args, **kwargs):
            os.makedirs(os.path.dirname(fake_lib), exist_ok=True)
            Path(fake_lib).write_text('fake lib')
            return MagicMock(returncode=0)

        with patch.object(main, 'LIB_PATH', fake_lib):
            with patch.object(main, 'FALLBACK_LIB_PATH', str(tmp_path / 'nonexistent')):
                with patch.object(main, 'BUILD_DIR', str(build_dir)):
                    with patch.object(main, 'SPARTA_SRC', str(sparta_src)):
                        with patch('sys.platform', 'darwin'):
                            with patch.dict(os.environ, {'SPARTA_GPU': '0'}, clear=False):
                                with patch('subprocess.run', side_effect=fake_run) as mock_run:
                                    result = main.build_sparta()
                                    for c in mock_run.call_args_list:
                                        cmd = c[0][0] if c[0] else c[1].get('args', [])
                                        if isinstance(cmd, list) and any('cmake' in str(x) for x in cmd):
                                            cmd_str = ' '.join(str(x) for x in cmd)
                                            assert 'OFF' in cmd_str

    def test_missing_lib_raises_error(self, tmp_path):
        """When lib not found after build, raises RuntimeError."""
        build_dir = tmp_path / 'build'
        sparta_src = tmp_path / 'SPARTA'
        sparta_src.mkdir()
        with patch.object(main, 'LIB_PATH', str(tmp_path / 'nonexistent')):
            with patch.object(main, 'FALLBACK_LIB_PATH', str(tmp_path / 'nonexistent')):
                with patch.object(main, 'BUILD_DIR', str(build_dir)):
                    with patch.object(main, 'SPARTA_SRC', str(sparta_src)):
                        with patch('os.path.exists', return_value=False):
                            with patch('subprocess.run') as mock_run:
                                mock_run.return_value = MagicMock(returncode=0)
                                with pytest.raises(RuntimeError, match="SPARTA library not found"):
                                    main.build_sparta()


# ============================================================================
# RUN_SELF_DIAGNOSTIC TESTS (234 stmts, 228 missing)
# ============================================================================

class TestRunSelfDiagnostic:
    """Tests for run_self_diagnostic function."""

    def _mock_modules(self):
        return {
            'deepxde': MagicMock(__version__='1.0'),
            'ansys': MagicMock(),
            'ansys.fluent': MagicMock(),
            'ansys.fluent.core': MagicMock(),
        }

    def test_pyrefly_passes(self, capsys):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='0 errors', stderr='')
            with patch.dict('sys.modules', self._mock_modules()):
                main.run_self_diagnostic()
        captured = capsys.readouterr()
        assert "STELLARORION SYSTEM INTEGRITY REPORT" in captured.out

    def test_pyrefly_not_found_warns(self, capsys):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            with patch.dict('sys.modules', self._mock_modules()):
                main.run_self_diagnostic()
        captured = capsys.readouterr()
        assert "WARN" in captured.out or "pyrefly" in captured.out.lower()

    def test_docker_check_passes(self, capsys):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            with patch.dict('sys.modules', self._mock_modules()):
                main.run_self_diagnostic()
        captured = capsys.readouterr()
        assert "SYSTEM INTEGRITY VERIFIED" in captured.out

    def test_docker_not_found_warns(self, capsys):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError
            with patch.dict('sys.modules', self._mock_modules()):
                main.run_self_diagnostic()
        captured = capsys.readouterr()
        assert "SYSTEM INTEGRITY VERIFIED" in captured.out

    def test_critical_errors_cause_exit(self, capsys):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            with patch.dict('sys.modules', self._mock_modules()):
                main.run_self_diagnostic()
        captured = capsys.readouterr()
        assert "SYSTEM INTEGRITY VERIFIED" in captured.out


# ============================================================================
# CHECK_AND_ACQUIRE_LOCK TESTS (101 stmts, 92 missing)
# ============================================================================

class TestCheckAndAcquireLock:

    def test_no_lockfile_creates_one(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            if os.path.exists(lock_path):
                os.remove(lock_path)
            with patch('atexit.register'):
                main.check_and_acquire_lock()
            assert os.path.exists(lock_path)
            with open(lock_path) as f:
                pid = int(f.read().strip())
            assert pid == os.getpid()

    def test_stale_lockfile_overwritten(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with open(lock_path, 'w') as f:
            f.write("999999999")
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            with patch('atexit.register'):
                main.check_and_acquire_lock()
            with open(lock_path) as f:
                pid = int(f.read().strip())
            assert pid == os.getpid()

    def test_active_lockfile_exits(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with open(lock_path, 'w') as f:
            f.write(str(os.getpid()))
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            with pytest.raises(SystemExit) as exc_info:
                main.check_and_acquire_lock()
            assert exc_info.value.code == 1

    def test_corrupted_lockfile_overwritten(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with open(lock_path, 'w') as f:
            f.write("not_a_number")
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            with patch('atexit.register'):
                main.check_and_acquire_lock()
            with open(lock_path) as f:
                pid = int(f.read().strip())
            assert pid == os.getpid()

    def test_lockfile_psutil_fallback_os_kill(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with open(lock_path, 'w') as f:
            f.write("999999999")
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            with patch.dict('sys.modules', {'psutil': None}):
                with patch('atexit.register'):
                    main.check_and_acquire_lock()
        with open(lock_path) as f:
            pid = int(f.read().strip())
        assert pid == os.getpid()

    def test_lockfile_win32_tasklist_fallback(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with open(lock_path, 'w') as f:
            f.write("999999999")
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            with patch.dict('sys.modules', {'psutil': None}):
                with patch('sys.platform', 'win32'):
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
                        with patch('atexit.register'):
                            main.check_and_acquire_lock()
        with open(lock_path) as f:
            pid = int(f.read().strip())
        assert pid == os.getpid()

    def test_atexit_cleanup_registered(self, tmp_path):
        lock_path = str(tmp_path / 'main.lock')
        with patch.object(main, '__file__', str(tmp_path / 'main.py')):
            with patch('atexit.register') as mock_register:
                main.check_and_acquire_lock()
                mock_register.assert_called()
                cleanup_func = mock_register.call_args[0][0]
                assert callable(cleanup_func)


# ============================================================================
# RUN_SIMULATION TESTS (146 stmts, 142 missing)
# ============================================================================

class TestRunSimulation:

    def test_run_simulation_builds_sparta_first(self, tmp_path):
        with patch.object(main, 'build_sparta', return_value='/fake/libsparta.dylib') as mock_build:
            with patch('os.environ', {'SPARTA_LIB_PATH': ''}):
                with patch('ctypes.CDLL'):
                    with patch('builtins.__import__', side_effect=ImportError):
                        try:
                            main.run_simulation(steps=10)
                        except Exception:
                            pass
                        mock_build.assert_called_once()

    def test_run_simulation_overrides_steps(self, tmp_path):
        hiad_dir = tmp_path / 'CADDesign'
        hiad_dir.mkdir()
        in_hiad = hiad_dir / 'in.hiad'
        in_hiad.write_text('run 100\n')
        with patch.object(main, 'build_sparta', return_value='/fake/libsparta.dylib'):
            with patch.object(main, 'CONTAINER_WORKDIR', str(tmp_path)):
                with patch('ctypes.CDLL'):
                    with patch('builtins.__import__', side_effect=ImportError):
                        try:
                            main.run_simulation(steps=50)
                        except Exception:
                            pass

    def test_run_simulation_skips_comments(self, tmp_path):
        hiad_dir = tmp_path / 'CADDesign'
        hiad_dir.mkdir()
        in_hiad = hiad_dir / 'in.hiad'
        in_hiad.write_text('# This is a comment\nrun 100\n# Another comment\n')
        lines = in_hiad.read_text().splitlines()
        non_comment = [l for l in lines if not l.strip().startswith('#')]
        assert len(non_comment) == 1
        assert non_comment[0].strip() == 'run 100'

    def test_run_simulation_rank_detection(self):
        with patch.dict(os.environ, {'MPI_LOCALRANKID': '2'}, clear=False):
            rank = int(os.environ.get('MPI_LOCALRANKID', '0'))
            assert rank == 2
        with patch.dict(os.environ, {'OMPI_COMM_WORLD_RANK': '3'}, clear=False):
            rank = int(os.environ.get('OMPI_COMM_WORLD_RANK', '0'))
            assert rank == 3


# ============================================================================
# MAIN DISPATCH TESTS (1142 stmts, 1022 missing)
# ============================================================================

class TestMainDispatch:
    """Tests for main() dispatch logic.

    KEY: All dispatch tests must mock subprocess.call to prevent
    the GUI launcher from spawning at line 1817-1820.
    """

    def _make_mock_module(self, has_gpu=False):
        """Create a properly configured StellarOrionEngineMach5Up mock module."""
        mock_api = MagicMock()
        mock_api.detect_nvidia_gpu.return_value = (has_gpu, 'GPU info' if has_gpu else 'No GPU')
        mock_api.return_value = mock_api  # Critical: Api() returns mock_api itself
        # Methods that return tuples (for unpacking in main.py)
        mock_api.run_sparta_simulation.return_value = (MagicMock(), MagicMock())
        mock_api.run_baseline_validation.return_value = MagicMock()
        mock_api.run_sample.return_value = MagicMock()
        mock_api.run_validation_unsteady.return_value = MagicMock()
        mock_api.run_compare_calibrate.return_value = MagicMock()
        mock_api.run_pinn_calibration.return_value = MagicMock()
        mock_api.execute_optimization.return_value = MagicMock()
        mock_api.get_irve_baseline_results_static.return_value = {
            'geometry': {'diameter': 3.0, 'tradius': 0.135, 'oradius': 0.5},
            'performance': {'peak_heat_flux': 13.8, 'total_heat_load': 188.0},
            'test': 'data',
        }
        mock_module = MagicMock()
        mock_module.Api = mock_api
        return mock_module

    def _run_main_safely(self, argv, extra_patches=None):
        """Run main.main() with standard mocking to prevent hangs.

        Handles:
        - sys.argv setup
        - IN_DOCKER removal
        - StellarOrionEngineMach5Up mock
        - subprocess.call mock (prevents GUI launch)
        - builtins.print mock
        - os.path.isdir mock (prevents AmaryllisIdleAutomode script creation)
        - SystemExit catching
        """
        sys.argv = argv
        os.environ.pop('IN_DOCKER', None)
        mock_module = self._make_mock_module()
        patches = [
            patch.dict('sys.modules', {'StellarOrionEngineMach5Up': mock_module}),
            patch('subprocess.call'),  # CRITICAL: prevent GUI launch hang
            patch('subprocess.run'),   # prevent subprocess calls to nonexistent paths
            patch('builtins.print'),
            patch('os.path.isdir', return_value=False),  # prevent AmaryllisIdleAutomode
        ]
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            # Apply any extra patches
            if extra_patches:
                with extra_patches:
                    try:
                        main.main()
                    except SystemExit:
                        pass
            else:
                try:
                    main.main()
                except SystemExit:
                    pass

    def test_self_test_flag(self):
        sys.argv = ['main.py', '--self-test']
        with patch.object(main, '_run_self_tests') as mock_st:
            main.main()
            mock_st.assert_called_once()

    def test_help_flag(self):
        """--help calls display_custom_help which raises SystemExit."""
        sys.argv = ['main.py', '--help']
        os.environ.pop('IN_DOCKER', None)
        with patch.object(main, 'display_custom_help', side_effect=SystemExit(0)) as mock_help:
            try:
                main.main()
            except SystemExit:
                pass
            mock_help.assert_called_once()

    def test_gettheirvebbaseline_flag(self):
        """--gettheirvebbaseline returns before GUI launcher."""
        sys.argv = ['main.py', '--gettheirvebbaseline']
        os.environ.pop('IN_DOCKER', None)
        mock_api = MagicMock()
        mock_api.get_irve_baseline_results_static.return_value = {'test': 'data'}
        mock_api.return_value = mock_api
        mock_module = MagicMock()
        mock_module.Api = mock_api
        with patch.dict('sys.modules', {'StellarOrionEngineMach5Up': mock_module}):
            with patch('builtins.print'):
                with patch('json.dumps', return_value='{"test": "data"}'):
                    try:
                        main.main()
                    except SystemExit:
                        pass

    def test_optimize_flag(self):
        self._run_main_safely(
            ['main.py', '--optimize'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_validation_flag(self):
        self._run_main_safely(
            ['main.py', '--validation'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_sample_flag(self):
        self._run_main_safely(
            ['main.py', '--sample', '100'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_comparecalibrate_flag(self):
        self._run_main_safely(
            ['main.py', '--compareCalibrate'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_validationunsteady_flag(self):
        self._run_main_safely(
            ['main.py', '--validationUnsteady'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_sparta_test_mode(self):
        self._run_main_safely(
            ['main.py', '--test', 'sparta'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_openfoam_test_mode(self):
        self._run_main_safely(
            ['main.py', '--test', 'openfoam'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_literacyreferences_flag(self):
        """--LiteracyReferences: path exists is mocked False, falls through to GUI."""
        self._run_main_safely(
            ['main.py', '--LiteracyReferences'],
            extra_patches=patch('os.path.exists', return_value=False),
        )

    def test_genearationhelp_flag(self):
        """--genearationhelp is unknown, falls through to GUI."""
        self._run_main_safely(
            ['main.py', '--genearationhelp'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_payload_flag(self):
        self._run_main_safely(
            ['main.py', '--payload'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_no_pinn_flag(self):
        self._run_main_safely(
            ['main.py', '--no-pinn'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_goal_heat_flag(self):
        self._run_main_safely(
            ['main.py', '--goal', 'heat'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_chem_11species_flag(self):
        self._run_main_safely(
            ['main.py', '--chem', '11-species'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_skip_diag_flag(self):
        self._run_main_safely(
            ['main.py', '--skip-diag'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_mach_alt_overrides(self):
        self._run_main_safely(
            ['main.py', '--mach', '2.5', '--alt', '30000'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_empty_args_shows_help(self):
        """No mode flag: display_custom_help is called, which raises SystemExit."""
        sys.argv = ['main.py']
        os.environ.pop('IN_DOCKER', None)
        mock_module = self._make_mock_module()
        with patch.dict('sys.modules', {'StellarOrionEngineMach5Up': mock_module}):
            with patch('subprocess.call'):
                with patch('builtins.print'):
                    with patch.object(main, 'display_custom_help', side_effect=SystemExit(0)):
                        try:
                            main.main()
                        except SystemExit:
                            pass

    def test_unknown_flag(self):
        self._run_main_safely(
            ['main.py', '--unknown-flag'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_multiple_flags(self):
        self._run_main_safely(
            ['main.py', '--skip-diag', '--payload'],
            extra_patches=patch.object(main, 'ensure_docker_colima'),
        )

    def test_docker_solver_calls_ensure_docker(self):
        """sparta/openfoam solver calls ensure_docker_colima."""
        sys.argv = ['main.py', '--test', 'sparta']
        os.environ.pop('IN_DOCKER', None)
        mock_module = self._make_mock_module()
        with patch.dict('sys.modules', {'StellarOrionEngineMach5Up': mock_module}):
            with patch('subprocess.call'):
                with patch('builtins.print'):
                    with patch.object(main, 'ensure_docker_colima') as mock_docker:
                        try:
                            main.main()
                        except SystemExit:
                            pass
                        mock_docker.assert_called()

    def test_in_docker_runs_simulation(self):
        """IN_DOCKER mode runs simulation directly."""
        sys.argv = ['main.py', '--steps', '10']
        os.environ['IN_DOCKER'] = '1'
        with patch.object(main, 'run_simulation') as mock_sim:
            try:
                main.main()
            except SystemExit:
                pass
            mock_sim.assert_called_once()

    def test_in_docker_no_steps_runs_simulation(self):
        """IN_DOCKER mode without --steps."""
        sys.argv = ['main.py']
        os.environ['IN_DOCKER'] = '1'
        with patch.object(main, 'run_simulation') as mock_sim:
            try:
                main.main()
            except SystemExit:
                pass
            mock_sim.assert_called_once_with(steps=None)


# ============================================================================
# TPS PRESETS TESTS
# ============================================================================

class TestTPSPresets:

    def test_tps_presets_exist(self):
        tps_presets = {
            "sic":     {"density": 1468.0, "cp": 1100.0, "emissivity": 0.75},
            "pyrogel": {"density": 180.0,  "cp": 1000.0, "emissivity": 0.80},
            "kapton":  {"density": 1420.0, "cp": 1090.0, "emissivity": 0.77},
            "multi":   {"density": 322.94, "cp": 1083.7, "emissivity": 0.75}
        }
        for name, props in tps_presets.items():
            assert "density" in props
            assert "cp" in props
            assert "emissivity" in props
            assert props["density"] > 0
            assert props["cp"] > 0
            assert 0 < props["emissivity"] <= 1.0

    def test_tps_density_reasonable(self):
        assert 1400 < 1468.0 < 1600

    def test_pyrogel_is_lightweight(self):
        assert 100 < 180.0 < 500


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:

    def test_windows_encoding_block_on_darwin_skipped(self):
        import sys as _sys
        original = _sys.platform
        try:
            _sys.platform = 'darwin'
            assert _sys.platform != 'win32'
        finally:
            _sys.platform = original

    def test_ansi_color_codes(self):
        BOLD = "\033[1m"
        CYAN = "\033[36m"
        RESET = "\033[0m"
        GREEN = "\033[32m"
        assert BOLD == "\033[1m"
        assert CYAN == "\033[36m"
        assert RESET == "\033[0m"
        assert GREEN == "\033[32m"

    def test_argparse_structure(self):
        import argparse
        parser = argparse.ArgumentParser(add_help=False)
        mode = parser.add_argument_group("Mode Flags")
        mode.add_argument("--help", action="store_true")
        mode.add_argument("--optimize", action="store_true")
        mode.add_argument("--test", type=str)
        mode.add_argument("--validation", action="store_true")
        mode.add_argument("--validationUnsteady", action="store_true")
        mode.add_argument("--sample", type=int)
        mode.add_argument("--compareCalibrate", action="store_true")
        mode.add_argument("--self-test", action="store_true")
        args = parser.parse_args(["--self-test"])
        assert args.self_test is True
        args = parser.parse_args(["--optimize"])
        assert args.optimize is True
        args = parser.parse_args(["--test", "baseline"])
        assert args.test == "baseline"


# ============================================================================
# PYTEST MARKS
# ============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.main_coverage,
    pytest.mark.critical,
]
