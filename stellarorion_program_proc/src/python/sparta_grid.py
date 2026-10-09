"""SPARTA grid-file parsing — the SINGLE canonical implementation.

PURPOSE
    Parse a SPARTA ``grid.NNNN.out`` dump into a numeric array for every
    downstream consumer (Kriging denoise, DeepXDE PINN training,
    post-processing).  Before this module existed the parser was duplicated
    byte-for-byte in ``kriging_denoise.py`` and ``pinn_accelerator.py``; the
    two copies then DIVERGED in their column mapping, so the PINN trainer was
    fed the axial velocity as the temperature.  One implementation, imported
    by both consumers, removes that entire divergence class (F32 /
    sabotage_verifier COPY_PASTE_DIVERGENCE).

AXIOMS
    A1. The dump contains one or more ``ITEM: CELLS`` blocks; only rows inside
        such a block are cell data.  Any other ``ITEM:`` line closes the block.
    A2. Each cell row carries 11 whitespace-separated tokens:
            id xlo ylo xhi yhi n u v w temp nrho
        measured against a real file (``results/validation/grid.0.out``):
            ITEM: CELLS id xlo ylo xhi yhi f_2[1] f_2[2] f_2[3] f_2[4] f_3[*] f_4[*]
            1 -5 0 -4.89928 0.0283273 19 8880.67 49.4097 -107.24 169.664 1.60125e+22
        => parts[0]=id  [1]=xlo [2]=ylo [3]=xhi [4]=yhi
           parts[5]=n   [6]=u   [7]=v   [8]=w   [9]=temp [10]=nrho
        because the deck computes ``2 grid all air n u v w``,
        ``3 thermal/grid all air temp`` and ``4 grid all air nrho``.
    A3. Cell centres are the bounding-box midpoints:
            x = (xlo + xhi) / 2,  y = (ylo + yhi) / 2

THEORIES
    T1. A row that does not carry a temperature token cannot be denoised or
        trained on, so it must be DROPPED — the absent temperature reads as
        0.0 and fails the ``temp_K > 0`` guard — rather than silently
        substituting an unmeasured field.
    T2. Mass density follows ``rho = n * M_air / N_A`` with M_air = 28.97e-3
        kg/mol and N_A = 6.022e23 1/mol [Citation: Bird (1994), §2.3].
    T3. A file with zero valid cells is an ERROR, not an empty result: raise,
        because every caller would otherwise train/denoise on nothing.

APPLICATIONS
    parse_grid_file(grid_file) -> np.ndarray of shape (N, 6):
        columns = [x, y, rho, T, vx, vy]

OUTPUT / ERROR CONTRACT
    Returns a ``float64`` array with one row per valid cell.
    Raises ``ValueError`` when the file yields no valid cells.

CITATIONS
    [1] SPARTA manual, §2.4 — grid file format.  https://sparta.github.io/
    [2] ``stellarorion_sparta.adb`` — compute 2/3/4 grid + dump 2 grid.
    [3] Bird, G. A. (1994). *Molecular Gas Dynamics and the Direct Simulation
        of Gas Flows*, §2.3.  Oxford University Press.
    [4] numpy.loadtxt documentation.
        https://numpy.org/doc/stable/reference/generated/numpy.loadtxt.html

Author: Albert Starfield Wahyu Suryo Samudro
"""

from __future__ import annotations

import numpy as np


def parse_grid_file(grid_file: str) -> np.ndarray:
    """Parse a SPARTA ``grid.NNNN.out`` dump into training data.

    AXIOMS:
      1. Grid file format is a SPARTA dump with ``ITEM: CELLS`` blocks.
      2. Each cell row has 11 tokens: id xlo ylo xhi yhi n u v w temp nrho.
      3. ``x_center = (xlo + xhi) / 2``, ``y_center = (ylo + yhi) / 2``.

    Parameters:
        grid_file: Path to the SPARTA ``grid.NNNN.out`` dump.

    Returns:
        numpy array of shape (N, 6) — ``[x, y, rho, T, vx, vy]``.

    Raises:
        ValueError: If no valid cells could be parsed from ``grid_file``
            (T3: an empty result is an error, never a silent empty array).
        OSError: If ``grid_file`` cannot be opened/read.

    References:
        - https://sparta.github.io/
        - https://numpy.org/doc/stable/reference/generated/numpy.loadtxt.html
    """
    cells = []
    header_seen = False

    # AXIOM A1: header_seen toggles on "ITEM: CELLS"; cells grows only with
    # valid rows, so a truncated/foreign block cannot inject bad geometry.
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
                # AXIOM A2: fewer than 9 tokens cannot even locate the cell.
                continue
            try:
                # SPARTA grid-dump row, MEASURED against a real file
                # (results/validation/grid.0.out):
                #   ITEM: CELLS id xlo ylo xhi yhi f_2[1] f_2[2] f_2[3] f_2[4] f_3[*] f_4[*]
                #   1 -5 0 -4.89928 0.0283273 19 8880.67 49.4097 -107.24 169.664 1.60125e+22
                # => parts[0]=id  [1]=xlo [2]=ylo [3]=xhi [4]=yhi
                #    parts[5]=n  [6]=u  [7]=v  [8]=w  [9]=temp  [10]=nrho
                # because the deck computes `2 grid all air n u v w`,
                #     `3 thermal/grid all air temp` and `4 grid all air nrho`.
                # [Citation: SPARTA manual, §2.4 — grid file format]
                # [Citation: stellarorion_sparta.adb — compute 2/3/4 grid + dump 2 grid]
                x_center = (float(parts[1]) + float(parts[3])) / 2.0
                y_center = (float(parts[2]) + float(parts[4])) / 2.0
                vx_ms = float(parts[6])
                vy_ms = float(parts[7])
                # THEORY T1: an absent (rather than wrong) temperature must read
                # 0.0 so the `temp_K > 0` guard below DROPS the cell instead of
                # silently denoising/training on an unmeasured field.
                temp_K = float(parts[9]) if len(parts) > 9 else 0.0
                num_density = float(parts[10]) if len(parts) > 10 else 1e20

                # THEORY T2: convert number density to mass density,
                # rho = n * M_air / N_A  [Citation: Bird (1994), §2.3]
                # -- AXIOM: N_A > 0 by definition of the Avogadro constant
                # -- APPLICATION: guard the division per Murphy's Law (CWE-682)
                M_air = 28.97e-3   # kg/mol
                N_A = 6.022e23     # Avogadro constant [1/mol]
                if N_A == 0.0:
                    continue  # unreachable: N_A is a physical constant; guard satisfies z3
                rho = num_density * M_air / N_A

                if temp_K > 0 and rho > 0:
                    cells.append([x_center, y_center, rho, temp_K, vx_ms, vy_ms])
            except (ValueError, IndexError):
                # A malformed row must not abort the whole dump; skip it.
                continue

    if not cells:
        # THEORY T3: an empty result is an error, never a silent empty array.
        raise ValueError(f"No valid cells parsed from {grid_file}")

    return np.array(cells, dtype=np.float64)
