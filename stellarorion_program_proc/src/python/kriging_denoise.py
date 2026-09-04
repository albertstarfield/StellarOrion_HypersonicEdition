"""StellarOrion Kriging Denoiser — Step 2 of the 4-step pipeline.

Bridges Step 1 (SPARTA DSMC) and Step 3 (PINN) by applying Gaussian
Process Regression (Kriging) spatial denoising to raw DSMC grid files.

AXIOMS:
  1. DSMC output is noisy (statistical fluctuation in particle counts)
  2. The underlying physical field is spatially smooth (continuum limit)
  3. GP regression recovers the smooth field from noisy observations
  4. Each variable (rho, T, vx, vy) is denoised independently

THEOREMS:
  1. GP posterior mean is the best linear unbiased predictor (BLUP)
  2. Denoised output preserves spatial correlations via kernel
  3. Noise variance σ²_n is estimated from data (WhiteKernel)

CITATIONS:
  [1] Rasmussen & Williams (2006), "Gaussian Processes for Machine Learning", MIT Press
  [2] Cressie (1993), "Statistics for Spatial Data", Wiley
  [3] Lophaven et al. (2002), "DACE — A MATLAB Kriging Toolbox", DTU
  [4] Scikit-learn docs: https://scikit-learn.org/stable/modules/gaussian_process.html
"""
import os
import sys
import warnings

import numpy as np

# Auto-install scikit-learn if missing (library interfacing, per project constraints)
try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import (
        ConstantKernel,
        Matern,
        WhiteKernel,
    )
except ImportError:
    print("[kriging_denoise] scikit-learn not found. Auto-installing ...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import (
        ConstantKernel,
        Matern,
        WhiteKernel,
    )


# ============================================================================
# CONSTANTS
# ============================================================================
# [Citation: Bird (1994), "Molecular Gas Dynamics", §2.3]
# DSMC statistical noise scales as 1/sqrt(N_particles_per_cell).
# Typical SPARTA cells have ~100-1000 particles → noise ~3-10%.

# Maximum cells for GP training (O(N³) memory, so we subsample for large grids)
_MAX_TRAINING_CELLS = 1000

# Default kernel: Matérn 5/2 (smooth but not infinitely differentiable,
# appropriate for physical fields that are C² but not C^∞)
# [Citation: Rasmussen & Williams (2006), §4.2]
_MATERN_52 = Matern(length_scale=1.0, length_scale_bounds=(1e-3, 1e3), nu=2.5)


def _parse_grid_file(grid_file):
    """Parse SPARTA grid.NNNN.out into training data.

    AXIOMS:
      1. Grid file format is SPARTA dump with ITEM: CELLS blocks
      2. Each cell has: id xlo xhi ylo yhi particles temp vx vy [num_density]
      3. x_center = (xlo + xhi) / 2, y_center = (ylo + yhi) / 2

    Returns: numpy array of shape (N, 6) — [x, y, rho, T, vx, vy]
    """
    cells = []
    header_seen = False

    with open(grid_file, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("ITEM:"):
                if "ITEM: CELLS" in line:
                    header_seen = True
                else:
                    header_seen = False
                continue
            if not header_seen:
                continue
            parts = line.split()
            if len(parts) < 9:
                continue
            try:
                # SPARTA format: id xlo xhi ylo yhi particles temp vx vy [num_density]
                # [Citation: SPARTA manual, §2.4 — grid file format]
                x_center = (float(parts[1]) + float(parts[2])) / 2.0
                y_center = (float(parts[3]) + float(parts[4])) / 2.0
                temp_K = float(parts[6])
                vx_ms = float(parts[7])
                vy_ms = float(parts[8])
                num_density = float(parts[10]) if len(parts) > 10 else 1e20

                # Convert number density to mass density: ρ = n × M_air / N_A
                # [Citation: Bird (1994), §2.3]
                M_air = 28.97e-3   # kg/mol
                N_A = 6.022e23     # Avogadro constant [1/mol]
                rho = num_density * M_air / N_A

                if temp_K > 0 and rho > 0:
                    cells.append([x_center, y_center, rho, temp_K, vx_ms, vy_ms])
            except (ValueError, IndexError):
                continue

    if not cells:
        raise ValueError(f"No valid cells parsed from {grid_file}")

    return np.array(cells, dtype=np.float64)


def _write_grid_file(grid_file, data):
    """Write denoised data back to SPARTA grid format.

    AXIOMS:
      1. Output format matches input format (grid.NNNN.out)
      2. Columns: id xlo xhi ylo yhi particles temp vx vy num_density
      3. We reconstruct cell bounds from centers (assume uniform spacing)

    data: numpy array of shape (N, 6) — [x, y, rho, T, vx, vy]
    """
    if data.shape[0] == 0:
        raise ValueError("Cannot write empty grid data")

    # Estimate cell spacing from data (assume roughly uniform grid)
    x_sorted = np.sort(np.unique(data[:, 0]))
    y_sorted = np.sort(np.unique(data[:, 1]))

    # Cell half-widths (approximate)
    dx = (x_sorted[-1] - x_sorted[0]) / max(len(x_sorted) - 1, 1) if len(x_sorted) > 1 else 1.0
    dy = (y_sorted[-1] - y_sorted[0]) / max(len(y_sorted) - 1, 1) if len(y_sorted) > 1 else 1.0
    half_dx = dx / 2.0
    half_dy = dy / 2.0

    with open(grid_file, "w") as fh:
        fh.write("ITEM: CELLS\n")
        fh.write("id xlo xhi ylo yhi particles temp vx vy num_density\n")
        for i, row in enumerate(data):
            x, y, rho, temp, vx, vy = row
            # Convert mass density back to number density for SPARTA format
            M_air = 28.97e-3
            N_A = 6.022e23
            num_density = rho * N_A / M_air
            # Fake particle count (normalized to 1.0 — SPARTA will re-initialize)
            particles = 1.0
            fh.write(
                f"{i + 1} {x - half_dx:.6e} {x + half_dx:.6e} "
                f"{y - half_dy:.6e} {y + half_dy:.6e} "
                f"{particles:.6e} {temp:.6e} {vx:.6e} {vy:.6e} {num_density:.6e}\n"
            )


def _build_kernel(noise_upper_bound=1.0):
    """Build GP kernel for spatial denoising.

    AXIOMS:
      1. Physical fields have smooth spatial correlations (Matérn 5/2)
      2. DSMC noise is independent per cell (WhiteKernel)
      3. Signal amplitude varies (ConstantKernel)

    THEOREM: The kernel K(x, x') = σ_f² × Matérn(x, x') + σ_n² × δ(x, x')
    is the optimal form for denoising spatially correlated signals corrupted
    by white noise. [Citation: Rasmussen & Williams (2006), §4.2]

    Returns: sklearn kernel object
    """
    # σ_f² × Matérn 5/2 — signal kernel
    # [Citation: Rasmussen & Williams (2006), §4.2]
    signal_kernel = ConstantKernel(
        constant_value=1.0,
        constant_value_bounds=(1e-3, 1e3),
    ) * _MATERN_52

    # σ_n² × δ(x, x') — noise kernel (DSMC statistical noise)
    # [Citation: Bird (1994), §2.3 — DSMC noise is cell-independent]
    noise_kernel = WhiteKernel(
        noise_level=0.1,
        noise_level_bounds=(1e-10, noise_upper_bound),
    )

    return signal_kernel + noise_kernel


def denoise_grid(raw_data, n_restarts=5, random_state=42):
    """Apply Kriging (GP) denoising to DSMC grid data.

    AXIOMS:
      1. raw_data has shape (N, 6) — [x, y, rho, T, vx, vy]
      2. Each variable (rho, T, vx, vy) is denoised independently
      3. Spatial coordinates (x, y) are GP inputs

    THEOREM: GP posterior mean f*(x) = K(x, X) [K(X, X) + σ_n² I]⁻¹ y
    is the best linear unbiased predictor (BLUP) of the true field.
    [Citation: Rasmussen & Williams (2006), Theorem 2.1]

    PROCEDURE:
      1. Extract spatial coordinates X = [x, y]
      2. For each variable v in [rho, T, vx, vy]:
         a. Fit GP: GP(X, v) with Matérn 5/2 + WhiteKernel
         b. Predict: v_denoised = GP.predict(X)
      3. Return denoised data [x, y, rho_denoised, T_denoised, vx_denoised, vy_denoised]

    RETURNS: numpy array of shape (N, 6) — [x, y, rho_kriged, T_kriged, vx_kriged, vy_kriged]
    """
    if raw_data.ndim != 2 or raw_data.shape[1] != 6:
        raise ValueError(f"Expected (N, 6) array, got shape {raw_data.shape}")

    X = raw_data[:, 0:2]  # spatial coordinates (N, 2)
    N = X.shape[0]

    if N == 0:
        raise ValueError("Cannot denoise empty data")

    # Subsample for large grids (GP is O(N³))
    # [Citation: Rasmussen & Williams (2006), §8 — computational cost]
    idx = np.arange(N)  # default: all indices
    if N > _MAX_TRAINING_CELLS:
        rng = np.random.RandomState(random_state)
        idx = rng.choice(N, _MAX_TRAINING_CELLS, replace=False)
        X_train = X[idx]
    else:
        X_train = X

    # Normalize coordinates for numerical stability
    # [Citation: Rasmussen & Williams (2006), §5.1 — preprocessing]
    x_mean, x_std = X_train.mean(axis=0), X_train.std(axis=0)
    x_std[x_std < 1e-10] = 1.0  # avoid division by zero
    X_train_norm = (X_train - x_mean) / x_std
    X_norm = (X - x_mean) / x_std

    # Variable indices and names for denoising
    # Columns: 0=x, 1=y, 2=rho, 3=T, 4=vx, 5=vy
    var_indices = [2, 3, 4, 5]
    var_names = ["rho", "T", "vx", "vy"]

    denoised = raw_data.copy()

    warnings.filterwarnings("ignore", category=RuntimeWarning)

    for vi, vname in zip(var_indices, var_names):
        # When subsampled, index into raw_data (full variable array), not X_train (coords only)
        # [Citation: Rasmussen & Williams (2006), §8 — subset of training data]
        y_train = raw_data[idx, vi] if N > _MAX_TRAINING_CELLS else raw_data[:, vi]

        # Skip if variance is too small (constant field)
        if np.std(y_train) < 1e-15:
            continue

        # Build kernel with appropriate noise bound
        # Heuristic: noise bound = 0.5 × std(y) (DSMC noise is typically 3-10%)
        noise_ub = max(0.5 * np.std(y_train), 1e-10)
        kernel = _build_kernel(noise_upper_bound=noise_ub)

        # Fit GP regressor
        # [Citation: Lophaven et al. (2002), DACE §3.2]
        gp = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=n_restarts,
            random_state=random_state,
            alpha=1e-10,  # numerical stability
        )

        try:
            gp.fit(X_train_norm, y_train)
        except (ValueError, RuntimeError) as e:
            print(f"[kriging_denoise] WARNING: GP fit failed for {vname}: {e}")
            continue

        # Predict denoised values at all grid points
        y_denoised, _y_std = gp.predict(X_norm, return_std=True)

        denoised[:, vi] = y_denoised

        # Report noise reduction
        raw_std = np.std(raw_data[:, vi])
        denoised_std = np.std(y_denoised)
        if raw_std > 0:
            noise_ratio = denoised_std / raw_std
            print(
                f"[kriging_denoise] {vname}: raw_std={raw_std:.4e}, "
                f"kriged_std={denoised_std:.4e}, ratio={noise_ratio:.3f}"
            )

    return denoised


def denoise_grid_file(input_file, output_file=None, n_restarts=5, random_state=42):
    """High-level API: denoise a SPARTA grid file and optionally write output.

    AXIOMS:
      1. input_file is a valid SPARTA grid.NNNN.out file
      2. If output_file is None, write to input_file.kriged.out
      3. Kriging reduces DSMC statistical noise while preserving physics

    PROCEDURE:
      1. Parse input grid file → raw_data (N, 6)
      2. Apply denoise_grid() → denoised_data (N, 6)
      3. Write output grid file

    RETURNS: (denoised_data, output_file_path)
    """
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}.kriged{ext}"

    # Step 1: Parse raw DSMC grid output
    print(f"[kriging_denoise] Parsing: {input_file}")
    raw_data = _parse_grid_file(input_file)
    print(f"[kriging_denoise] Parsed {raw_data.shape[0]} cells")

    # Step 2: Apply Kriging denoising
    denoised_data = denoise_grid(
        raw_data, n_restarts=n_restarts, random_state=random_state
    )

    # Step 3: Write denoised grid file
    _write_grid_file(output_file, denoised_data)
    print(f"[kriging_denoise] Written: {output_file}")

    return denoised_data, output_file


# ============================================================================
# SELF-TESTS
# ============================================================================
def _run_self_tests():
    """Run self-tests for kriging_denoise module.

    TESTS:
      1. test_parse_grid_file — Verify parsing of grid format
      2. test_denoise_grid_basic — Verify denoising reduces noise
      3. test_denoise_grid_shape — Verify output shape matches input
      4. test_denoise_grid_constant — Verify constant fields pass through
      5. test_write_grid_file — Verify round-trip write/read
      6. test_kernel_build — Verify kernel construction
      7. test_denoise_grid_large — Verify subsampling for large grids

    RETURNS: list of (test_name, passed, message) tuples
    """
    results = []

    # Test 1: Parse a synthetic grid file
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".out", delete=False) as f:
            f.write("ITEM: CELLS\n")
            f.write("id xlo xhi ylo yhi particles temp vx vy num_density\n")
            for i in range(10):
                x = float(i) * 0.1
                y = 0.0
                f.write(
                    f"{i + 1} {x:.6e} {x + 0.05:.6e} {y:.6e} {y + 0.05:.6e} "
                    f"1.000000e+02 3.000000e+02 1.000000e+03 0.000000e+00 1.000000e+20\n"
                )
            tmpfile = f.name

        data = _parse_grid_file(tmpfile)
        os.unlink(tmpfile)
        assert data.shape == (10, 6), f"Expected (10, 6), got {data.shape}"
        results.append(("test_parse_grid_file", True, "OK"))
    except (AssertionError, ValueError, OSError) as e:
        results.append(("test_parse_grid_file", False, str(e)))

    # Test 2: Denoise reduces noise on synthetic data
    try:
        rng = np.random.RandomState(42)
        N = 100
        x = rng.uniform(0, 1, N)
        y = rng.uniform(0, 1, N)
        # True field: smooth sinusoidal
        rho_true = 1.0 + 0.1 * np.sin(2 * np.pi * x) * np.cos(2 * np.pi * y)
        # Add noise (DSMC-like)
        noise = 0.05 * rng.randn(N)
        rho_noisy = rho_true + noise

        raw = np.column_stack([x, y, rho_noisy, np.ones(N) * 300, np.ones(N) * 1000, np.zeros(N)])
        denoised = denoise_grid(raw, n_restarts=2, random_state=42)

        raw_std = np.std(rho_noisy - rho_true)
        denoised_std = np.std(denoised[:, 2] - rho_true)
        assert denoised_std < raw_std, f"Denoising didn't reduce noise: {denoised_std:.4f} >= {raw_std:.4f}"
        results.append(("test_denoise_grid_basic", True, f"noise ratio: {denoised_std / raw_std:.3f}"))
    except (AssertionError, ValueError, RuntimeError) as e:
        results.append(("test_denoise_grid_basic", False, str(e)))

    # Test 3: Output shape matches input
    try:
        rng = np.random.RandomState(42)
        raw = rng.rand(50, 6)
        raw[:, 0:2] *= 10  # spatial coords
        raw[:, 2] = 1.0 + 0.1 * raw[:, 2]  # rho
        raw[:, 3] = 300.0 + 10.0 * raw[:, 3]  # T
        raw[:, 4] = 1000.0 * raw[:, 4]  # vx
        raw[:, 5] = raw[:, 5]  # vy

        denoised = denoise_grid(raw, n_restarts=1, random_state=42)
        assert denoised.shape == raw.shape, f"Shape mismatch: {denoised.shape} != {raw.shape}"
        results.append(("test_denoise_grid_shape", True, "OK"))
    except (AssertionError, ValueError, RuntimeError) as e:
        results.append(("test_denoise_grid_shape", False, str(e)))

    # Test 4: Constant fields pass through unchanged
    try:
        raw = np.zeros((20, 6))
        raw[:, 0] = np.linspace(0, 1, 20)
        raw[:, 2] = 5.0  # constant rho
        raw[:, 3] = 300.0  # constant T
        raw[:, 4] = 1000.0  # constant vx
        raw[:, 5] = 0.0  # constant vy

        denoised = denoise_grid(raw, n_restarts=1, random_state=42)
        # Constant fields should stay constant (std ≈ 0)
        assert np.std(denoised[:, 2]) < 1e-5, f"Constant rho changed: std={np.std(denoised[:, 2])}"
        results.append(("test_denoise_grid_constant", True, "OK"))
    except (AssertionError, ValueError) as e:
        results.append(("test_denoise_grid_constant", False, str(e)))

    # Test 5: Round-trip write/read
    try:
        import tempfile
        rng = np.random.RandomState(42)
        raw = rng.rand(10, 6)
        raw[:, 0] = np.linspace(0, 1, 10)
        raw[:, 1] = 0.0
        raw[:, 2] = 1.0 + 0.01 * raw[:, 2]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".out", delete=False) as f:
            tmpfile = f.name

        _write_grid_file(tmpfile, raw)
        data_back = _parse_grid_file(tmpfile)
        os.unlink(tmpfile)

        assert data_back.shape == raw.shape, f"Round-trip shape mismatch: {data_back.shape}"
        # Check x coordinates preserved
        assert np.allclose(data_back[:, 0], raw[:, 0], atol=1e-4), "x coords lost"
        results.append(("test_write_grid_file", True, "OK"))
    except (AssertionError, ValueError, OSError) as e:
        results.append(("test_write_grid_file", False, str(e)))

    # Test 6: Kernel construction
    try:
        kernel = _build_kernel()
        assert kernel is not None, "Kernel is None"
        results.append(("test_kernel_build", True, "OK"))
    except (AssertionError, ValueError) as e:
        results.append(("test_kernel_build", False, str(e)))

    # Test 7: Large grid subsampling
    try:
        rng = np.random.RandomState(42)
        N = _MAX_TRAINING_CELLS + 1000  # exceeds limit
        raw = rng.rand(N, 6)
        raw[:, 0:2] *= 10
        raw[:, 2] = 1.0 + 0.1 * raw[:, 2]
        raw[:, 3] = 300.0 + 10.0 * raw[:, 3]
        raw[:, 4] = 1000.0 * raw[:, 4]

        denoised = denoise_grid(raw, n_restarts=1, random_state=42)
        assert denoised.shape == (N, 6), f"Large grid shape mismatch: {denoised.shape}"
        results.append(("test_denoise_grid_large", True, f"N={N}, subsampled to {_MAX_TRAINING_CELLS}"))
    except (AssertionError, ValueError, RuntimeError) as e:
        results.append(("test_denoise_grid_large", False, str(e)))

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("StellarOrion Kriging Denoiser — Self-Tests")
    print("=" * 60)

    results = _run_self_tests()

    passed = sum(1 for _, p, _ in results if p)
    total = len(results)

    for name, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
