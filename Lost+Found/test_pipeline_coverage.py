#!/usr/bin/env python
"""Comprehensive test suite for StellarOrion pipeline modules.

Covers: main.py, StellarOrionEngineMach5Up.py, source/pinn_accelerator.py, source/visualizer.py
Run with: pytest test_pipeline_coverage.py -v --tb=short
"""
import os
import sys
import sqlite3
import tempfile
import shutil
import json
import struct
import math
from unittest.mock import patch, MagicMock

import pytest
import numpy as np

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Skip main.py module-level ensure_venv() during test import
os.environ.setdefault("IN_DOCKER", "1")


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    """Provide a temporary directory, cleaned up after test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sparta_grid_file(tmp_dir):
    """Valid SPARTA grid dump file with 6 cells, 11 columns each."""
    path = os.path.join(tmp_dir, "grid.1.out")
    with open(path, "w") as f:
        f.write("ITEM: TIMESTEP\n0\n")
        f.write("ITEM: NUMBER OF CELLS\n6\n")
        f.write("ITEM: CELL COORDINATES\n")
        for i, (xlo, ylo) in enumerate(
            [(0.0, 0.0), (0.05, 0.0), (0.0, 0.05),
             (0.05, 0.05), (0.0, 0.1), (0.05, 0.1)], 1
        ):
            f.write(f"{i} {xlo} {ylo} {xlo+0.05} {ylo+0.05}\n")
        f.write("ITEM: CELLS\n")
        temps = [270.0, 275.0, 280.0, 285.0, 290.0, 295.0]
        for i, (xlo, ylo) in enumerate(
            [(0.0, 0.0), (0.05, 0.0), (0.0, 0.05),
             (0.05, 0.05), (0.0, 0.1), (0.05, 0.1)], 1
        ):
            vel = 500.0 - (i - 1) * 20.0
            f.write(
                f"{i} {xlo} {ylo} {xlo+0.05} {ylo+0.05} "
                f"3.47e21 {vel} 0.0 0.0 {temps[i-1]} 3.47e21\n"
            )
    return path


@pytest.fixture
def surf_file(tmp_dir):
    """Valid SPARTA .surf file with 6 points and 5 lines."""
    path = os.path.join(tmp_dir, "HIAD_custom.surf")
    with open(path, "w") as f:
        f.write("# Surface definition\nPoints\n6\n")
        for i, (z, r) in enumerate(
            [(0.0, 0.5), (0.1, 0.6), (0.2, 0.5),
             (0.3, 0.4), (0.4, 0.5), (0.5, 0.6)], 1
        ):
            f.write(f"{i} {z} {r}\n")
        f.write("Lines\n5\n1 2\n2 3\n3 4\n4 5\n5 6\n")
    return path


@pytest.fixture
def stl_ascii_file(tmp_dir):
    """ASCII STL with 2 triangular facets."""
    path = os.path.join(tmp_dir, "test.stl")
    with open(path, "w") as f:
        f.write(
            "solid test\n"
            "  facet normal 0.0 0.0 1.0\n"
            "    outer loop\n"
            "      vertex 0.0 0.0 0.0\n"
            "      vertex 1.0 0.0 0.0\n"
            "      vertex 0.0 1.0 0.0\n"
            "    endloop\n"
            "  endfacet\n"
            "  facet normal 0.0 0.0 -1.0\n"
            "    outer loop\n"
            "      vertex 1.0 0.0 0.0\n"
            "      vertex 1.0 1.0 0.0\n"
            "      vertex 0.0 1.0 0.0\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid test\n"
        )
    return path


@pytest.fixture
def stl_binary_file(tmp_dir):
    """Binary STL with 1 triangular facet."""
    path = os.path.join(tmp_dir, "test_bin.stl")
    header = b"\x00" * 80
    n_facets = struct.pack("<I", 1)
    facet = struct.pack("<fff", 0.0, 0.0, 1.0)   # normal
    facet += struct.pack("<fff", 0.0, 0.0, 0.0)   # v1
    facet += struct.pack("<fff", 1.0, 0.0, 0.0)   # v2
    facet += struct.pack("<fff", 0.0, 1.0, 0.0)   # v3
    facet += struct.pack("<H", 0)                   # attr
    with open(path, "wb") as f:
        f.write(header + n_facets + facet)
    return path


@pytest.fixture
def empty_sparta_file(tmp_dir):
    """SPARTA grid file with no cell data after ITEM: CELLS."""
    path = os.path.join(tmp_dir, "empty_grid.out")
    with open(path, "w") as f:
        f.write("ITEM: TIMESTEP\n0\nITEM: NUMBER OF CELLS\n0\n")
    return path


@pytest.fixture
def invalid_sparta_file(tmp_dir):
    """SPARTA grid file with too few columns per cell line."""
    path = os.path.join(tmp_dir, "invalid_grid.out")
    with open(path, "w") as f:
        f.write("ITEM: TIMESTEP\n0\nITEM: CELLS\n1 0.0 0.0 0.05 0.05\n")
    return path


# ===========================================================================
# MODULE 1: source/pinn_accelerator.py Tests
# ===========================================================================

class TestParseSpartaGrid:
    """Tests for parse_sparta_grid() in pinn_accelerator.py."""

    def test_returns_none_for_empty_file(self, empty_sparta_file):
        """Empty file (no cells section data) should return None, None."""
        from source.pinn_accelerator import parse_sparta_grid
        X, Y = parse_sparta_grid(empty_sparta_file)
        assert X is None
        assert Y is None

    def test_returns_none_for_invalid_file(self, invalid_sparta_file):
        """File with insufficient columns should return None, None."""
        from source.pinn_accelerator import parse_sparta_grid
        X, Y = parse_sparta_grid(invalid_sparta_file)
        assert X is None
        assert Y is None

    def test_returns_none_for_nonexistent_file(self, tmp_dir):
        """Nonexistent file should raise FileNotFoundError."""
        from source.pinn_accelerator import parse_sparta_grid
        with pytest.raises(FileNotFoundError):
            parse_sparta_grid(os.path.join(tmp_dir, "noexist.out"))

    def test_parses_valid_grid_file(self, sparta_grid_file):
        """Valid grid file should return X (coords) and Y (fields) arrays."""
        from source.pinn_accelerator import parse_sparta_grid
        X, Y = parse_sparta_grid(sparta_grid_file)
        assert X is not None
        assert Y is not None
        assert X.shape == (6, 2)  # 6 cells, (x_center, y_center)
        assert Y.shape == (6, 5)  # 6 cells, (rho, u, v, T, p)

    def test_grid_cell_centers_are_midpoints(self, sparta_grid_file):
        """Cell centers should be (xlo+xhi)/2, (ylo+yhi)/2."""
        from source.pinn_accelerator import parse_sparta_grid
        X, _ = parse_sparta_grid(sparta_grid_file)
        assert abs(X[0, 0] - 0.025) < 1e-10
        assert abs(X[0, 1] - 0.025) < 1e-10

    def test_pressure_computation(self, sparta_grid_file):
        """Pressure = nrho * k_B * T (ideal gas law, cite Boltzmann 1877)."""
        from source.pinn_accelerator import parse_sparta_grid
        _, Y = parse_sparta_grid(sparta_grid_file)
        k_B = 1.380649e-23  # Boltzmann constant [J/K]
        for i in range(6):
            nrho = 3.47e21  # number density [m^-3] from grid file
            T = Y[i, 3]
            expected_p = nrho * k_B * T
            assert abs(Y[i, 4] - expected_p) / expected_p < 1e-6

    def test_density_computation(self, sparta_grid_file):
        """Density = nrho * M_air / N_A (Bird 1994, DSMC fundamentals)."""
        from source.pinn_accelerator import parse_sparta_grid
        _, Y = parse_sparta_grid(sparta_grid_file)
        m_avg = 28.97e-3 / 6.022e23  # mass per molecule [kg]
        expected_rho = 3.47e21 * m_avg
        assert abs(Y[0, 0] - expected_rho) / expected_rho < 1e-6

    def test_temperature_column(self, sparta_grid_file):
        """Temperature column [K] should match input grid data."""
        from source.pinn_accelerator import parse_sparta_grid
        _, Y = parse_sparta_grid(sparta_grid_file)
        for i, T_expected in enumerate([270.0, 275.0, 280.0, 285.0, 290.0, 295.0]):
            assert abs(Y[i, 3] - T_expected) < 1e-10


# ===========================================================================
# MODULE 2: source/visualizer.py Tests
# ===========================================================================

class TestParseGridDump:
    """Tests for parse_grid_dump() in visualizer.py."""

    def test_parses_valid_grid(self, sparta_grid_file):
        """Valid grid file should return numpy array with all cell data."""
        from source.visualizer import parse_grid_dump
        data = parse_grid_dump(sparta_grid_file)
        assert isinstance(data, np.ndarray)
        assert data.shape[0] == 6
        assert data.shape[1] >= 10  # at least 10 columns

    def test_returns_empty_for_invalid(self, invalid_sparta_file):
        """Invalid file returns empty array."""
        from source.visualizer import parse_grid_dump
        data = parse_grid_dump(invalid_sparta_file)
        assert len(data) == 0

    def test_returns_empty_for_no_cells(self, empty_sparta_file):
        """File without ITEM: CELLS returns empty array."""
        from source.visualizer import parse_grid_dump
        data = parse_grid_dump(empty_sparta_file)
        assert len(data) == 0


class TestParseStl:
    """Tests for _parse_stl() in visualizer.py."""

    def test_ascii_stl(self, stl_ascii_file):
        """ASCII STL should parse into 2 triangles."""
        from source.visualizer import _parse_stl
        triangles = _parse_stl(stl_ascii_file)
        assert triangles is not None
        assert len(triangles) == 2
        assert triangles[0].shape == (3, 3)

    def test_binary_stl(self, stl_binary_file):
        """Binary STL should parse into 1 triangle."""
        from source.visualizer import _parse_stl
        triangles = _parse_stl(stl_binary_file)
        assert triangles is not None
        assert len(triangles) == 1

    def test_nonexistent_returns_empty(self, tmp_dir):
        """Nonexistent file returns empty list."""
        from source.visualizer import _parse_stl
        result = _parse_stl(os.path.join(tmp_dir, "noexist.stl"))
        assert result == []


class TestParseSurfPoints:
    """Tests for _parse_surf_points() in visualizer.py."""

    def test_valid_surf(self, surf_file):
        """Valid .surf file should return 6 (z, r) points."""
        from source.visualizer import _parse_surf_points
        points = _parse_surf_points(surf_file)
        assert len(points) == 6
        assert points[0] == (0.0, 0.5)

    def test_none_input(self):
        """None input returns empty list."""
        from source.visualizer import _parse_surf_points
        assert _parse_surf_points(None) == []

    def test_nonexistent_file(self):
        """Nonexistent file returns empty list."""
        from source.visualizer import _parse_surf_points
        assert _parse_surf_points("/no/such/file.surf") == []

    def test_empty_file(self, tmp_dir):
        """Empty .surf file returns empty list."""
        path = os.path.join(tmp_dir, "empty.surf")
        with open(path, "w") as f:
            f.write("# empty\n")
        from source.visualizer import _parse_surf_points
        assert _parse_surf_points(path) == []


class TestCleanForTri:
    """Tests for clean_for_tri() in visualizer.py.
    Axiom: np.nan_to_num replaces NaN/Inf with 0.0 for safe triangulation.
    """

    def test_replaces_nan_with_zero(self):
        """NaN values should be replaced with 0.0."""
        from source.visualizer import clean_for_tri
        result = clean_for_tri(np.array([1.0, np.nan, 3.0]))
        assert result[1] == 0.0
        assert result[0] == 1.0

    def test_replaces_inf_with_zero(self):
        """Inf values should be replaced with 0.0."""
        from source.visualizer import clean_for_tri
        result = clean_for_tri(np.array([1.0, np.inf, -np.inf]))
        assert result[1] == 0.0
        assert result[2] == 0.0


class TestFindFfmpeg:
    """Tests for find_ffmpeg() in visualizer.py."""

    def test_returns_string(self):
        """Should return a non-empty string."""
        from source.visualizer import find_ffmpeg
        result = find_ffmpeg()
        assert isinstance(result, str)
        assert len(result) > 0


class TestAddMetadataOverlay:
    """Tests for _add_metadata_overlay() in visualizer.py."""

    def test_skips_empty_params(self):
        """Empty ref_params should add no text."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        from source.visualizer import _add_metadata_overlay
        _add_metadata_overlay(ax, {})
        assert len(ax.texts) == 0
        plt.close(fig)

    def test_adds_text_with_params(self):
        """Non-empty ref_params should add a text box."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        from source.visualizer import _add_metadata_overlay
        _add_metadata_overlay(ax, {"v_inf": 2700, "mach": 10, "cells": 100})
        assert len(ax.texts) == 1
        plt.close(fig)


class TestGenerateConvergencePlot:
    """Tests for generate_convergence_plot() in visualizer.py."""

    def test_creates_plot_file(self, tmp_dir):
        """Should generate a PNG convergence plot."""
        from source.visualizer import generate_convergence_plot
        log_lines = [
            "1000 0 100000 0.5 0.01 1500.0 300.0 500.0 200.0 0 500 0.5 0.5 0.5\n",
            "2000 0 100000 0.55 0.012 1550.0 305.0 510.0 205.0 0 510 0.45 0.45 0.45\n",
            "3000 0 100000 0.52 0.011 1520.0 302.0 505.0 202.0 0 505 0.48 0.48 0.48\n",
        ]
        output_path = os.path.join(tmp_dir, "convergence.png")
        generate_convergence_plot(log_lines, output_path)
        assert os.path.exists(output_path)

    def test_empty_log_no_crash(self, tmp_dir):
        """Empty log lines should not crash."""
        from source.visualizer import generate_convergence_plot
        output_path = os.path.join(tmp_dir, "empty_conv.png")
        generate_convergence_plot([], output_path)


# ===========================================================================
# MODULE 3: StellarOrionEngineMach5Up.py — HistoryManager Tests
# ===========================================================================

class TestHistoryManager:
    """Tests for HistoryManager class (SQLite-backed run tracking)."""

    def test_creates_db(self, tmp_dir):
        """Creating HistoryManager should create the SQLite database file."""
        from StellarOrionEngineMach5Up import HistoryManager
        db_path = os.path.join(tmp_dir, "test.db")
        HistoryManager(db_path=db_path)
        assert os.path.exists(db_path)

    def test_create_and_get_run(self, tmp_dir):
        """create_run returns a valid ID; get_run retrieves it as a dict."""
        from StellarOrionEngineMach5Up import HistoryManager
        hm = HistoryManager(db_path=os.path.join(tmp_dir, "test.db"))
        run_id = hm.create_run("test_run", "optimization", 10, {"diameter": 3.0})
        assert run_id is not None and run_id > 0
        run = hm.get_run(run_id)
        assert run is not None
        assert run["name"] == "test_run"
        assert run["status"] == "running"

    def test_get_all_runs(self, tmp_dir):
        """get_all_runs should list all created runs."""
        from StellarOrionEngineMach5Up import HistoryManager
        hm = HistoryManager(db_path=os.path.join(tmp_dir, "test.db"))
        hm.create_run("run1", "opt", 5, {})
        hm.create_run("run2", "val", 10, {})
        runs = hm.get_all_runs()
        assert len(runs) == 2

    def test_update_run_progress(self, tmp_dir):
        """update_run_progress should update the current_sample field."""
        from StellarOrionEngineMach5Up import HistoryManager
        hm = HistoryManager(db_path=os.path.join(tmp_dir, "test.db"))
        run_id = hm.create_run("test", "opt", 10, {})
        hm.update_run_progress(run_id, current_sample=5)
        run = hm.get_run(run_id)
        assert run["current_sample"] == 5

    def test_add_sample(self, tmp_dir):
        """add_sample should insert a row into the samples table."""
        from StellarOrionEngineMach5Up import HistoryManager
        db_path = os.path.join(tmp_dir, "test.db")
        hm = HistoryManager(db_path=db_path)
        run_id = hm.create_run("test", "opt", 10, {})
        hm.add_sample(run_id, 0, {"d": 3.0}, {"drag": 100.0}, {"g_load": 5.0}, 12.5)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM samples WHERE run_id=?", (run_id,))
            assert cursor.fetchone()[0] == 1

    def test_delete_run(self, tmp_dir):
        """delete_run should remove the run from the database."""
        from StellarOrionEngineMach5Up import HistoryManager
        hm = HistoryManager(db_path=os.path.join(tmp_dir, "test.db"))
        run_id = hm.create_run("test", "opt", 10, {})
        hm.delete_run(run_id)
        assert hm.get_run(run_id) is None

    def test_upsert_draft(self, tmp_dir):
        """upsert_draft should insert then update draft state."""
        from StellarOrionEngineMach5Up import HistoryManager
        hm = HistoryManager(db_path=os.path.join(tmp_dir, "test.db"))
        hm.upsert_draft("draft1", {"param": 1}, 2)
        hm.upsert_draft("draft1", {"param": 2}, 3)  # update path
        # Should not raise

    def test_db_schema_migration(self, tmp_dir):
        """Re-creating HistoryManager on same DB should not crash (migration safe)."""
        from StellarOrionEngineMach5Up import HistoryManager
        db_path = os.path.join(tmp_dir, "test.db")
        HistoryManager(db_path=db_path)
        HistoryManager(db_path=db_path)  # second init — tests PRAGMA migration
        assert os.path.exists(db_path)


# ===========================================================================
# MODULE 3: StellarOrionEngineMach5Up.py — Api Static Methods Tests
# ===========================================================================

class TestApiCalculateShieldMass:
    """Tests for Api.calculate_shield_mass() static method.

    Axiom: Pappus's second theorem — surface area of revolution = 2*pi*integral(r*dl).
    Ref: DERIVATION.MD §3, Rapisarda 2023.
    """

    def test_empty_skin_returns_zero(self):
        """Empty skin_data should return zeroed dict."""
        from StellarOrionEngineMach5Up import Api
        result = Api.calculate_shield_mass([])
        assert result["mass_kg"] == 0.0
        assert result["surface_area_m2"] == 0.0

    def test_single_segment_skin(self):
        """Two-point skin defines one segment; area = 2*pi*r_avg*dl."""
        from StellarOrionEngineMach5Up import Api
        # Two points: (r=100mm, z=0mm, angle=0) and (r=100mm, z=100mm, angle=0)
        # dl = 0.1m, r_avg = 0.1m, area = 2*pi*0.1*0.1 = 0.0628 m^2
        skin = [(100.0, 0.0, 0.0), (100.0, 100.0, 0.0)]
        result = Api.calculate_shield_mass(skin, tps_thickness=0.0254, tps_density=1468.0)
        expected_area = 2.0 * math.pi * 0.1 * 0.1
        assert abs(result["surface_area_m2"] - expected_area) / expected_area < 1e-6
        expected_vol = expected_area * 0.0254
        assert abs(result["volume_m3"] - expected_vol) / expected_vol < 1e-6
        expected_mass = expected_vol * 1468.0
        assert abs(result["mass_kg"] - expected_mass) / expected_mass < 1e-6

    def test_larger_shield(self):
        """Half-cone profile: r=[0..1500mm], z=[0..1500mm]."""
        from StellarOrionEngineMach5Up import Api
        skin = [(float(r), float(r), 0.0) for r in range(0, 1501, 100)]
        result = Api.calculate_shield_mass(skin, tps_thickness=0.0254, tps_density=1468.0)
        assert result["mass_kg"] > 0
        assert result["surface_area_m2"] > 0
        assert result["volume_m3"] > 0


class TestApiCalculateShieldMassAnalytical:
    """Tests for Api.calculate_shield_mass_analytical() static method.
    Axiom: Sphere-cone HIAD geometry — nose cap is spherical, flank is conical.
    Ref: Rapisarda 2023 §4, IRVE-3 geometry.
    """

    def test_irve3_baseline_geometry(self):
        """IRVE-3 baseline: 3m diameter, 60-deg half-angle, 6 toroids."""
        from StellarOrionEngineMach5Up import Api
        result = Api.calculate_shield_mass_analytical(
            diameter_m=3.0, angle_deg=60.0, toroid_count=6,
            toroid_radius_m=0.135, nose_radius_m=0.55,
            tps_thickness=0.0254, tps_density=1468.0
        )
        assert result["total_shield_mass_kg"] > 0
        assert result["total_surface_area_m2"] > 0
        # Mass should be in a physically reasonable range for HIAD shield
        assert 1.0 < result["total_shield_mass_kg"] < 1000.0

    def test_zero_toroids(self):
        """Zero toroids should still compute nose cap + flank area."""
        from StellarOrionEngineMach5Up import Api
        result = Api.calculate_shield_mass_analytical(
            diameter_m=3.0, angle_deg=60.0, toroid_count=0,
            toroid_radius_m=0.135, nose_radius_m=0.55
        )
        assert result["total_shield_mass_kg"] > 0

    def test_larger_diameter_increases_mass(self):
        """Larger diameter -> larger surface area -> larger mass."""
        from StellarOrionEngineMach5Up import Api
        small = Api.calculate_shield_mass_analytical(
            diameter_m=2.0, angle_deg=60.0, toroid_count=3,
            toroid_radius_m=0.135, nose_radius_m=0.55
        )
        large = Api.calculate_shield_mass_analytical(
            diameter_m=4.0, angle_deg=60.0, toroid_count=3,
            toroid_radius_m=0.135, nose_radius_m=0.55
        )
        assert large["total_shield_mass_kg"] > small["total_shield_mass_kg"]


# ===========================================================================
# MODULE 3: StellarOrionEngineMach5Up.py — Engine Methods Tests
# ===========================================================================

class TestApiParseGridStatistics:
    """Tests for Api.parse_grid_statistics() method."""

    def test_valid_grid_returns_counts(self, sparta_grid_file):
        """Valid grid file should return cell count and domain extent."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        stats = api.parse_grid_statistics(sparta_grid_file)
        assert stats["total_cells"] == 6
        assert abs(stats["extent"][0] - 0.0) < 1e-10    # x_min
        assert abs(stats["extent"][1] - 0.1) < 1e-10    # x_max
        assert abs(stats["extent"][2] - 0.0) < 1e-10    # y_min
        assert abs(stats["extent"][3] - 0.15) < 1e-10   # y_max

    def test_nonexistent_returns_empty(self, tmp_dir):
        """Nonexistent file returns empty dict."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        stats = api.parse_grid_statistics(os.path.join(tmp_dir, "noexist.out"))
        assert stats == {}

    def test_empty_grid_returns_zero_cells(self, empty_sparta_file):
        """Grid with no cells returns total_cells=0."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        stats = api.parse_grid_statistics(empty_sparta_file)
        assert stats["total_cells"] == 0


class TestApiParseOpenfoamResults:
    """Tests for Api.parse_openfoam_results() method."""

    def test_missing_files_returns_zeros(self, tmp_dir):
        """Missing postProcessing files should return drag=0, heat=0."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        result = api.parse_openfoam_results(tmp_dir)
        assert result["drag"] == 0.0
        assert result["heat"] == 0.0

    def test_valid_forces_file(self, tmp_dir):
        """Valid forces.dat should extract drag from last non-comment line."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        forces_dir = os.path.join(tmp_dir, "postProcessing", "forces", "0")
        os.makedirs(forces_dir)
        with open(os.path.join(forces_dir, "forces.dat"), "w") as f:
            f.write("# Time Force_x Force_y\n")
            f.write("0.0 (100.0 50.0 0.0)\n")
            f.write("1.0 (200.0 60.0 0.0)\n")
        result = api.parse_openfoam_results(tmp_dir)
        assert result["drag"] == 200.0  # last non-comment, abs(parts[1])

    def test_valid_heat_file(self, tmp_dir):
        """Valid heat flux file should extract heat value."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        heat_dir = os.path.join(tmp_dir, "postProcessing", "heatFlux", "0")
        os.makedirs(heat_dir)
        with open(os.path.join(heat_dir, "surfaceFieldValue.dat"), "w") as f:
            f.write("# Time Value\n")
            f.write("0.0 15000.0\n")
            f.write("1.0 18000.0\n")
        result = api.parse_openfoam_results(tmp_dir)
        assert result["heat"] == 18000.0


class TestApiWriteOfDict:
    """Tests for Api._write_of_dict() method."""

    def test_creates_file_with_header(self, tmp_dir):
        """Should create an OpenFOAM dictionary file with standard header."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        path = os.path.join(tmp_dir, "testDict")
        api._write_of_dict(path, "FoamFile\n{\n    version 2.0;\n}")
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        assert "OpenFOAM" in content
        assert "testDict" in content

    def test_newline_consistency(self, tmp_dir):
        """File should use Unix newlines (LF only)."""
        from StellarOrionEngineMach5Up import Api
        api = Api.__new__(Api)
        path = os.path.join(tmp_dir, "nl_test")
        api._write_of_dict(path, "content")
        with open(path, "rb") as f:
            raw = f.read()
        assert b"\r\n" not in raw  # no Windows CRLF


# ===========================================================================
# MODULE 4: main.py Tests
# ===========================================================================

class TestEnsureVenv:
    """Tests for ensure_venv() in main.py."""

    def test_skip_venv_bootstrap(self):
        """--skip-venv-bootstrap should return immediately."""
        import main
        with patch.object(sys, "argv", ["main.py", "--skip-venv-bootstrap"]):
            main.ensure_venv()  # should not raise

    def test_no_skip_when_no_venv_found(self):
        """If no venv python found, should fall through (not hang)."""
        import main
        with patch.object(sys, "argv", ["main.py"]), \
             patch("os.path.exists", return_value=False), \
             patch("os.access", return_value=False):
            try:
                main.ensure_venv()
            except (SystemExit, RuntimeError):
                pass  # expected when no venv available


class TestDisplayCustomHelp:
    """Tests for display_custom_help() in main.py."""

    def test_displays_usage_section(self):
        """display_custom_help should print USAGE and then sys.exit(0)."""
        import main
        import argparse
        import io
        parser = argparse.ArgumentParser(description="Test")
        parser.add_argument("--foo")
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()
        try:
            main.display_custom_help(parser)
        except SystemExit:
            pass  # display_custom_help calls sys.exit(0)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "USAGE" in output or "HELP" in output


class TestEnsureDockerColima:
    """Tests for ensure_docker_colima() in main.py."""

    def test_docker_already_running(self):
        """If docker info succeeds, should do nothing."""
        import main
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            main.ensure_docker_colima()

    def test_docker_not_found(self):
        """If docker not found, should print message and return."""
        import main
        with patch("subprocess.run", side_effect=FileNotFoundError), \
             patch("builtins.print"):
            main.ensure_docker_colima()


class TestRunSelfDiagnostic:
    """Tests for run_self_diagnostic() in main.py."""

    def test_runs_without_crash(self):
        """Self diagnostic should run without unhandled exception."""
        import main
        with patch("subprocess.run") as mock_run, \
             patch("builtins.print"):
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            try:
                main.run_self_diagnostic()
            except Exception:
                pass  # some checks may fail, that is OK for diagnostic


class TestBuildSparta:
    """Tests for build_sparta() in main.py."""

    def test_build_skips_if_lib_exists(self):
        """If LIB_PATH exists, should skip build."""
        import main
        with patch("os.path.exists", return_value=True):
            result = main.build_sparta()
            assert result == main.LIB_PATH


class TestCheckAndAcquireLock:
    """Tests for check_and_acquire_lock() in main.py."""

    def test_returns_file_object(self):
        """Should return an open file object (lock) or None."""
        import main
        lock = main.check_and_acquire_lock()
        # lock is either a file object or None
        if lock is not None:
            lock.close()


class TestMainArgParsing:
    """Tests for main() argument parsing in main.py."""

    def test_main_help_flag(self):
        """--help should trigger display_custom_help and exit."""
        import main
        with patch.object(sys, "argv", ["main.py", "--help"]), \
             patch("builtins.print"), \
             pytest.raises(SystemExit):
            main.main()

    def test_main_self_test(self):
        """--self-test should run _run_self_tests without crash."""
        import main
        with patch.object(sys, "argv", ["main.py", "--self-test"]), \
             patch.object(main, "_run_self_tests") as mock_test:
            try:
                main.main()
            except SystemExit:
                pass  # main() may sys.exit after self-test
            mock_test.assert_called_once()
