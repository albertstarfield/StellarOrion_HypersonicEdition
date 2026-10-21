#!/usr/bin/env python3
"""StellarOrion screening-model calibration fitter (orthogonal residual fit).

PURPOSE
-------
Fits the CALIBRATION DESIGN §2.6 orthogonal residual correction of the
StellarOrion *screening model* against the DSMC runs of the §2.7 local CCD,
and writes the §2.6.2 ``KEY = VALUE`` calibration file that the Ada
screening model (``StellarOrion_Optimization.Load_Calibration``) reads.

The script is deliberately STANDALONE (standard library only, no Ada FFI, no
NumPy): it must be runnable on a machine that has only the calibration runs
and the design document.  The Ada laws it reproduces are quoted, with their
source lines, below; the reproduction is checked numerically in ``--self-test``
against values that the repository already stores.

AXIOMS
------
A1: THE FIT IS AN ORTHOGONAL CONTRAST FIT, NOT A LEAST-SQUARES SOLVE.
    The basis is {1, x1, x2, x3, x1*x2, x1*x3, x2*x3} over the coded
    coordinates ``x_k = clamp((X(k) - centre_k)/half_k, -1, +1)``.  On the
    2^3 factorial the basis functions are mutually orthogonal with squared
    norm 8, so the coefficients are the plain contrasts
    ``b0 = mean(r)``, ``b_k = (1/8) * sum_i x_ik r_i`` and
    ``b_ij = (1/8) * sum_i x_ik x_jk r_i``.  No matrix is formed and no
    system is solved.  ``--self-test`` verifies the orthogonality NUMERICALLY
    and verifies that the closed form coincides with an explicit
    normal-equation solve on the canonical design.
A2: THE PHYSICAL COORDINATES COME FROM THE FLOWN GEOMETRY, NEVER FROM THE
    FILE NAME.  ``X(1) = geom_diameter_m / 2`` (the body/junction radius),
    ``X(2) = geom_toroid_radius_m``, ``X(3) = geom_angle_deg`` — the
    CALIBRATION DESIGN §2.1 mapping, inverted.  A run whose geometry cannot
    be read is a hard error naming the file and the missing column; it is
    never skipped silently.
A3: A MISSING COLUMN IS A NAMED, ACTIONABLE ERROR.  The old runs on disk
    predate CALIBRATION DESIGN §2.4 and therefore carry none of the new
    columns; the fitter must say WHICH file lacks WHICH column and why that
    matters, and must exit non-zero without writing a calibration file.
A4: THE ANCHOR IS ADMITTED ONLY WHEN IT IS INSIDE THE DESIGN BOX.  The
    reference run (X_ref = (1.5, 0.135, 60)) lies OUTSIDE the §2.7 box
    centred on the GA optimum, so it is an OUT-OF-BOX CHECK, not a fit
    point: including it would destroy the orthogonality the closed form
    relies on.  When an anchor lies inside the box it joins the fit as the
    10th point and the report says so explicitly.
A5: THE OUTPUT IS THE §2.6.2 FILE, VERBATIM IN ITS KEY NAMES.  The Ada
    loader reads ``key = value`` lines and skips ``#`` comments, so the file
    is ASCII, one key per line, in the §2.6.2 order.
A6: THE FLIGHT STATE OF THE ANALYTIC HEAT LAW IS EXPLICIT AND OVERRIDABLE.
    The default is the state the SPARTA package uses for its own
    Sutton-Graves column (rho = 6.9674e-4 kg/m^3, V = 2700 m/s), because
    the calibration compares against the DSMC runs.  The screening model's
    OWN heat term uses a different state (ISA at 51.8 km, V = 3378 m/s);
    the difference is a constant factor that the q-residual therefore
    absorbs.  ``--sg-density`` / ``--sg-velocity`` expose the choice
    explicitly instead of hiding it in the source.

THEOREMS
--------
T1: (orthogonality)  Over the eight corners of the 2^3 factorial the seven
    basis functions are pairwise orthogonal and each has squared norm 8.
    PROOF: the character table of the group Z2^3; the sum over all corners of
    a non-trivial character is 0 (pair the corners with the first coordinate
    flipped) and the sum of squares of a character is 8.
    APPLICATION: ``_gram_matrix`` evaluates this numerically and
    ``--self-test`` asserts it.
T2: (closed form == least squares on the canonical design)  For the design
    {8 corners} U {centre} the Gram matrix of the basis is
    diag(9, 8, 8, 8, 8, 8, 8, 8): the constant column has squared norm 9
    (nine points) and each contrast column has squared norm 8 (the centre
    contributes 0).  A diagonal Gram matrix makes the normal equations
    diagonal, hence the least-squares solution IS the contrast estimator:
    ``b0 = mean(r)`` over the nine points and ``b_k = (1/8) sum x_k r``.
    APPLICATION: ``--self-test`` compares the closed form with an explicit
    Gaussian elimination on the normal equations.
T3: (the correction is zero when the model is already right)  If the DSMC
    response equals the analytic response at every design point, every
    residual is 0, hence every coefficient is 0 and the calibrated model
    reproduces the analytic model exactly.
    APPLICATION: the ``--self-test`` synthetic fit.
T4: (the anchor cannot corrupt the fit)  An out-of-box anchor is excluded
    from the fit set, so the eight corners and the centre are the only
    contributors; the reported anchor residual is then an independent
    out-of-sample check of the fitted model.

APPLICATIONS
------------
1. ``scripts/calibrate_from_dsmc.py --run <ccd csv> ... --anchor <ref csv>``
   writes ``src/python/hiad_calibration.txt``.  The design-box centre and
   half-widths default to CALIBRATION DESIGN §2.7 and are overridable with
   ``--centre-x1..3`` / ``--half-x1..3``; the analytic heat law's flight
   state is overridable with ``--sg-density`` / ``--sg-velocity`` (axiom A6).
2. ``scripts/calibrate_from_dsmc.py --self-test`` runs the orthogonality
   check (T1), the closed-form-versus-normal-equations check (T2), the
   analytic-law reproduction checks, the zero-correction check (T3) and the
   calibration-file round-trip check.

CITATIONS
---------
[CALIBRATION_DESIGN.md §2.1]  the analytic-to-physical geometry mapping.
[CALIBRATION_DESIGN.md §2.4]  the new CSV columns.
[CALIBRATION_DESIGN.md §2.6]  the orthogonal residual correction mechanism.
[CALIBRATION_DESIGN.md §2.6.2] the KEY = VALUE calibration file format.
[CALIBRATION_DESIGN.md §2.7]  the local CCD design (centre, half-widths).
[Reference: stellarorion_optimization.adb:1909-1943]  Compute_Max_Radius.
[Reference: stellarorion_optimization.adb:2009-2039]  Estimate_Cd.
[Reference: stellarorion_optimization.ads:617-624]  Default_R_N_MOP (1.5),
    Default_R_Tor_MOP (0.135), Default_Half_Cone_MOP (60.0),
    Default_N_Tori_MOP (6) and Cd_Ref_MOP (1.47).
[Reference: stellarorion_optimization.adb:2306-2353]  Analytic_To_Physical
    (D = 2*X(1), nose = Nose_Radius_Ratio*X(1), torus = X(2), cone = X(3)).
[Reference: stellarorion_optimization.ads:782]  Nose_Radius_Ratio = 0.55/1.5.
[Reference: stellarorion_optimization.adb:87]  Tau_Sec = 13.582459 s.
[Reference: stellarorion_types.ads:61]  C_SG = 1.7415e-4 (Sutton-Graves).
[Reference: stellarorion_sparta.adb:1748-1754 and :3211-3216]  the SPARTA
    Sutton-Graves correlation, which uses ``Flight.Density_Kgm3`` and
    ``Flight.Velocity_Ms`` as the flight state and ``Geo.Nose_Radius_M`` as
    the nose radius.
[Reference: stellarorion_test_modes.adb:1297-1298]  that flight state:
    ``Flight.Velocity_Ms := 2700.0`` and
    ``Flight.Density_Kgm3 := 6.9674e-4`` (the values the SPARTA SG column
    is computed with; they are quoted verbatim in sparta.adb:3178-3180).
[Citation: Sutton & Graves (1972), NASA TR R-376] — stagnation-point heating.
[Citation: Anderson (2006), Hypersonic Gas Dynamics, Sec. 5.4] — blunt drag.
[Citation: Montgomery (2017), Design and Analysis of Experiments, 9th ed.] —
    the central composite design of CALIBRATION DESIGN §2.7.

Exit codes
----------
0  success (fit written, or self-test passed)
1  data / IO error (a named, actionable message on stderr; nothing written)
2  command-line usage error (argparse)
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
#  CALIBRATION DESIGN §2.7 — the local CCD design (default; overridable)
# ---------------------------------------------------------------------------
DEFAULT_CENTRE = (1.03967, 0.219741, 53.7247)
DEFAULT_HALF = (0.25, 0.06, 8.0)

# ---------------------------------------------------------------------------
#  The Ada screening-model laws reproduced here (see the CITATIONS block)
# ---------------------------------------------------------------------------
# [Reference: stellarorion_optimization.ads:617-624]
CD_REF_MOP = 1.47          # Cd_Ref_MOP
R_REF_MOP = 1.5            # Default_R_N_MOP  (the R_Ref of the Cd law)
N_TORI_MOP = 6             # Default_N_Tori_MOP
# [Reference: stellarorion_optimization.ads:782]
NOSE_RADIUS_RATIO = 0.55 / 1.5
# [Reference: stellarorion_types.ads:61]
C_SG = 1.7415e-4
# [Reference: stellarorion_test_modes.adb:1297-1298] — the flight state the
# SPARTA Sutton-Graves column uses (quoted in sparta.adb:3178-3180).
SG_DENSITY_KGM3 = 6.9674e-4
SG_VELOCITY_MS = 2700.0
# [Reference: stellarorion_optimization.adb:87]
TAU_SEC = 13.582459

# ---------------------------------------------------------------------------
#  CALIBRATION DESIGN §2.4 — the CSV columns the fitter consumes
# ---------------------------------------------------------------------------
COL_CD_RAW_PRESENTED = "cd_raw_presented_area"
COL_CD_RAW_BODY = "cd_raw_body_area"
COL_CD_UNCLAMPED = "cd_unclamped"
COL_DSMC_SURFACE_HEAT = "dsmc_surface_heat_load_jcm2"
COL_GEOM_DIAMETER = "geom_diameter_m"
COL_GEOM_NOSE = "geom_nose_radius_m"
COL_GEOM_TORUS = "geom_toroid_radius_m"
COL_GEOM_ANGLE = "geom_angle_deg"
COL_REF_AREA_PRESENTED = "ref_area_presented_m2"
COL_DRAG_SUM = "drag_sum_N"
COL_DYN_PRESS = "dyn_press_pa"
COL_HEAT_FLUX_SG = "heat_flux_sg_Wm2"

#: Columns a DSMC run MUST carry to be usable by the fitter.
REQUIRED_RUN_COLUMNS = (
    COL_CD_RAW_PRESENTED,
    COL_DSMC_SURFACE_HEAT,
    COL_GEOM_DIAMETER,
    COL_GEOM_TORUS,
    COL_GEOM_ANGLE,
)

#: Columns that are used for cross-checks only (absent is not an error).
OPTIONAL_RUN_COLUMNS = (
    COL_CD_RAW_BODY,
    COL_CD_UNCLAMPED,
    COL_GEOM_NOSE,
    COL_REF_AREA_PRESENTED,
    COL_DRAG_SUM,
    COL_DYN_PRESS,
    COL_HEAT_FLUX_SG,
)

# ---------------------------------------------------------------------------
#  CALIBRATION DESIGN §2.6.2 — the calibration file (key names are BINDING)
# ---------------------------------------------------------------------------
CALIBRATION_HEADER = (
    "# StellarOrion screening-model calibration (orthogonal residual correction).",
    "# Written by scripts/calibrate_from_dsmc.py; read by the Ada screening model.",
)

#: The 21 keys of the §2.6.2 file, in file order.  THE NAMES ARE BINDING.
CALIBRATION_KEYS = (
    "calibration_valid",
    "centre_x1", "centre_x2", "centre_x3",
    "half_x1", "half_x2", "half_x3",
    "cd_b0", "cd_b1", "cd_b2", "cd_b3", "cd_b12", "cd_b13", "cd_b23",
    "q_b0", "q_b1", "q_b2", "q_b3", "q_b12", "q_b13", "q_b23",
)

#: The seven basis coefficients, in the order the file lists them.
COEFFICIENT_SUFFIXES = ("b0", "b1", "b2", "b3", "b12", "b13", "b23")

#: The index pairs of the two-factor contrasts, in file order.
CONTRAST_PAIRS = ((0, 1), (0, 2), (1, 2))

#: Tolerance used to decide whether a coded coordinate sits on a corner.
CODED_TOLERANCE = 1.0e-9


class CalibrationError(RuntimeError):
    """Raised when the calibration cannot be performed (data, schema, I/O).

    Every message carries the file and the column/value at fault so the
    operator can act on it without reading the source (AXIOM A3).
    """


# ---------------------------------------------------------------------------
#  The reproduced Ada laws
# ---------------------------------------------------------------------------
def analytic_max_radius(r_n: float, r_tor: float, half_cone_deg: float) -> float:
    """Reproduce ``StellarOrion_Optimization.Compute_Max_Radius``.

    The body/junction radius, the torus minor radius and the half-cone
    angle are turned into the maximum radius of the toroidal vehicle:

        Gamma   = (90 - Half_Cone_Deg) * pi / 180
        R_Tang  = R_N * cos(Gamma)
        S_Last  = (2 * N_Tori - 1) * R_Tor
        R_Target= R_Tang + S_Last * cos(Gamma)
        R_Max   = R_Target + R_Tor

    Parameters:
        r_n: the body/junction radius X(1) [m].
        r_tor: the torus minor radius X(2) [m].
        half_cone_deg: the half-cone angle X(3) [deg].

    Returns:
        The maximum radius R_Max [m].

    Raises:
        ValueError: any argument is outside the documented envelope.

    [Reference: stellarorion_optimization.adb:1909-1943]
    [Reference: Rapisarda (2023), MSc Thesis, TU Delft, Sec. 3.7, App. C.1]
    """
    if r_n <= 0.0 or r_tor <= 0.0:
        raise ValueError(
            f"analytic_max_radius: r_n and r_tor must be positive, got "
            f"r_n={r_n!r}, r_tor={r_tor!r}"
        )
    if not 0.0 < half_cone_deg < 90.0:
        raise ValueError(
            f"analytic_max_radius: half_cone_deg must be in (0, 90) deg, got "
            f"{half_cone_deg!r}"
        )
    gamma = (90.0 - half_cone_deg) * math.pi / 180.0
    r_tang = r_n * math.cos(gamma)
    s_last = float(2 * N_TORI_MOP - 1) * r_tor
    r_target = r_tang + s_last * math.cos(gamma)
    return r_target + r_tor


def analytic_cd(r_n: float, r_tor: float, half_cone_deg: float) -> float:
    """Reproduce ``StellarOrion_Optimization.Estimate_Cd``.

        Cd       = Cd_Ref_MOP * (R_Max / R_Ref) ** 0.15 * Nose_Corr
        Nose_Corr= 1.0 + 0.05 * (R_Ref / R_N - 1.0)
        R_Ref    = Default_R_N_MOP = 1.5
        Cd_Ref   = Cd_Ref_MOP = 1.47

    Parameters:
        r_n: the body/junction radius X(1) [m].
        r_tor: the torus minor radius X(2) [m].
        half_cone_deg: the half-cone angle X(3) [deg].

    Returns:
        The drag coefficient Cd (dimensionless).

    Raises:
        ValueError: any argument is outside the documented envelope.

    [Reference: stellarorion_optimization.adb:2009-2039]
    [Citation: Anderson (2006), Hypersonic Gas Dynamics, Sec. 5.4]
    """
    r_max = analytic_max_radius(r_n, r_tor, half_cone_deg)
    nose_corr = 1.0 + 0.05 * (R_REF_MOP / r_n - 1.0)
    return CD_REF_MOP * (r_max / R_REF_MOP) ** 0.15 * nose_corr


def analytic_heat_load_jcm2(
    x1: float,
    density_kgm3: float = SG_DENSITY_KGM3,
    velocity_ms: float = SG_VELOCITY_MS,
) -> float:
    """Reproduce the current analytic Total Heat Load Q(x) [J/cm^2].

    The heat term is the Sutton-Graves stagnation flux taken at the
    PHYSICAL nose radius of the §2.1 mapping
    (``Nose_Radius_Ratio * X(1)``), integrated over the validated
    effective heating window ``Tau_Sec``:

        q_SG = C_SG * sqrt(rho_inf / R_nose) * V_inf ** 3     [W/m^2]
        Q(x) = q_SG * Tau_Sec / 1e4                           [J/cm^2]

    ``rho_inf`` and ``V_inf`` default to the flight state the SPARTA
    package uses for its own Sutton-Graves column
    (``Flight.Density_Kgm3`` and ``Flight.Velocity_Ms``), so the analytic
    term and the DSMC's own SG column speak about the same flight state.

    NOTE ON THE OTHER CONVENTION (documented, not hidden): the screening
    model's OWN heat term uses a DIFFERENT flight state -- the ISA density
    at the 51.8 km snapshot with V = 3378 m/s
    (stellarorion_optimization.adb:2217-2224) -- and that is the state the
    Ada cost function scores.  The two states differ by a constant factor,
    so a fit carried out with this default ALSO absorbs that constant into
    the q-residual.  The flight state is exposed on the command line
    (``--sg-density`` / ``--sg-velocity``) so Stage 2 can run either
    convention without editing the source.

    Parameters:
        x1: the analytic first coordinate (body/junction radius) [m].
        density_kgm3: the freestream density of the flight state [kg/m^3].
        velocity_ms: the flight-state velocity [m/s].

    Returns:
        The analytic Total Heat Load [J/cm^2].

    Raises:
        ValueError: x1 is not positive (the nose radius must be positive),
            or the flight state is not strictly positive.

    [Reference: stellarorion_sparta.adb:1748-1754 and :3211-3216]
    [Reference: stellarorion_test_modes.adb:1297-1298]  (rho, V)
    [Reference: stellarorion_types.ads:61]  (C_SG)
    [Reference: stellarorion_optimization.adb:87]  (Tau_Sec)
    [Reference: stellarorion_optimization.ads:782]  (Nose_Radius_Ratio)
    [Reference: stellarorion_optimization.adb:2217-2224]  (the screening
        model's own heat term and its flight state)
    [Citation: Sutton & Graves (1972), NASA TR R-376]
    """
    if x1 <= 0.0:
        raise ValueError(
            f"analytic_heat_load_jcm2: x1 must be positive, got {x1!r}"
        )
    if density_kgm3 <= 0.0 or velocity_ms <= 0.0:
        raise ValueError(
            f"analytic_heat_load_jcm2: the flight state must be strictly "
            f"positive, got density={density_kgm3!r}, velocity={velocity_ms!r}"
        )
    nose_radius = NOSE_RADIUS_RATIO * x1
    q_sg = C_SG * math.sqrt(density_kgm3 / nose_radius) * (velocity_ms ** 3)
    return q_sg * TAU_SEC / 1.0e4


# ---------------------------------------------------------------------------
#  Coded coordinates and the orthogonal basis
# ---------------------------------------------------------------------------
def coded_coordinate(value: float, centre: float, half: float) -> float:
    """Return the coded coordinate ``clamp((value - centre)/half, -1, +1)``.

    Parameters:
        value: the physical coordinate.
        centre: the centre of the design box.
        half: the half-width of the design box (must be positive).

    Returns:
        The coded coordinate in [-1, +1].

    Raises:
        ValueError: half is not positive.

    [Reference: CALIBRATION_DESIGN.md §2.6]
    """
    if half <= 0.0:
        raise ValueError(
            f"coded_coordinate: half-width must be positive, got {half!r}"
        )
    raw = (value - centre) / half
    if raw > 1.0:
        return 1.0
    if raw < -1.0:
        return -1.0
    return raw


def monomial_vector(x1: float, x2: float, x3: float) -> tuple[float, ...]:
    """Return the seven orthogonal basis values at a coded point.

    The order is the §2.6.2 file order: {1, x1, x2, x3, x1*x2, x1*x3, x2*x3}.

    Parameters:
        x1, x2, x3: the coded coordinates.

    Returns:
        The seven basis values, in the order the calibration file lists them.
    """
    return (1.0, x1, x2, x3, x1 * x2, x1 * x3, x2 * x3)


def fit_orthogonal_factorial(
    coded_points: list[tuple[float, float, float]],
    responses: list[float],
) -> tuple[float, ...]:
    """Fit the seven orthogonal coefficients of the 2^3 factorial design.

    THEOREM T2: on the canonical design (eight corners plus the centre) the
    closed-form contrasts ARE the least-squares solution, because the Gram
    matrix of the basis is diagonal.  No matrix is formed and no system is
    solved (AXIOM A1).

    Parameters:
        coded_points: the coded coordinates of the fit points.
        responses: the residual responses of the fit points (same length).

    Returns:
        The seven coefficients in the {b0, b1, b2, b3, b12, b13, b23} order.

    Raises:
        ValueError: the two sequences differ in length, are empty, or the
            design carries no factorial corner (the (1/8) divisor is the
            squared norm of the contrast columns and is only valid on a
            complete 2^3 factorial).

    [Reference: CALIBRATION_DESIGN.md §2.6]
    """
    if len(coded_points) != len(responses):
        raise ValueError(
            f"fit_orthogonal_factorial: {len(coded_points)} coded points but "
            f"{len(responses)} responses"
        )
    if not responses:
        raise ValueError("fit_orthogonal_factorial: no fit points")
    has_corner = any(
        all(abs(component) >= 1.0 - CODED_TOLERANCE for component in point)
        for point in coded_points
    )
    if not has_corner:
        raise ValueError(
            "fit_orthogonal_factorial: the design carries no factorial "
            "corner, so the (1/8) contrast divisor is not valid"
        )

    b0 = sum(responses) / len(responses)
    coefficients = [b0]
    for k in range(3):
        coefficients.append(
            sum(point[k] * value for point, value in zip(coded_points, responses))
            / 8.0
        )
    for first, second in CONTRAST_PAIRS:
        coefficients.append(
            sum(
                point[first] * point[second] * value
                for point, value in zip(coded_points, responses)
            )
            / 8.0
        )
    return tuple(coefficients)


def evaluate_model(
    coefficients: tuple[float, ...], x1: float, x2: float, x3: float
) -> float:
    """Evaluate the seven-term orthogonal model at a coded point.

    Parameters:
        coefficients: the fitted coefficients.
        x1, x2, x3: the coded coordinates.

    Returns:
        The model value.

    Raises:
        ValueError: the coefficient vector does not have seven entries.
    """
    if len(coefficients) != len(COEFFICIENT_SUFFIXES):
        raise ValueError(
            f"evaluate_model: expected {len(COEFFICIENT_SUFFIXES)} "
            f"coefficients, got {len(coefficients)}"
        )
    return sum(
        coefficient * monomial
        for coefficient, monomial in zip(
            coefficients, monomial_vector(x1, x2, x3)
        )
    )


def gram_matrix(
    coded_points: list[tuple[float, float, float]]
) -> list[list[float]]:
    """Return the Gram matrix of the seven basis functions over the points.

    Used as the numerical orthogonality diagnostic (THEOREM T1) and to tell
    the reader whether the closed form is the strict least-squares solution
    (diagonal Gram) or the orthogonal contrast estimator (non-diagonal Gram,
    which can only happen when an interior anchor was admitted).

    Parameters:
        coded_points: the coded coordinates of the fit points.

    Returns:
        The 7x7 symmetric Gram matrix.
    """
    basis = [monomial_vector(*point) for point in coded_points]
    size = len(COEFFICIENT_SUFFIXES)
    matrix = [[0.0] * size for _ in range(size)]
    for row in range(size):
        for column in range(size):
            matrix[row][column] = sum(
                vector[row] * vector[column] for vector in basis
            )
    return matrix


# ---------------------------------------------------------------------------
#  Reading a DSMC run
# ---------------------------------------------------------------------------
@dataclass
class RunPoint:
    """One DSMC run, reduced to what the calibration fit needs.

    Attributes:
        path: the CSV the run was read from.
        x_physical: the analytic triple (R_N, r_tor, cone) of the flown
            geometry, in the §2.1 coordinates.
        coded: the clamped coded coordinates of that triple.
        coded_raw: the UNCLAMPED coded coordinates (they show how far
            outside the design box the run lies).
        kind: "corner", "centre" or "off-design".
        cd_dsmc: the DSMC drag coefficient response (presented area).
        q_dsmc: the DSMC surface heat load response [J/cm^2].
        cd_analytic: the analytic drag coefficient at this geometry.
        q_analytic: the analytic heat load at this geometry [J/cm^2].
        nose_radius_flown: the flown nose radius, when the CSV records it.
        steps: the number of trajectory rows in the CSV.
        cd_cross_check: the largest deviation between the CSV's
            ``cd_raw_presented_area`` and the value recomputed from
            ``drag_sum_N / (dyn_press_pa * ref_area_presented_m2)``.
    """

    path: Path
    x_physical: tuple[float, float, float]
    coded: tuple[float, float, float]
    coded_raw: tuple[float, float, float]
    kind: str
    cd_dsmc: float
    q_dsmc: float
    cd_analytic: float
    q_analytic: float
    nose_radius_flown: float | None = None
    steps: int = 0
    cd_cross_check: float = float("nan")
    optional_columns_present: tuple[str, ...] = ()


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file and return its header and its rows.

    Parameters:
        path: the CSV to read.

    Returns:
        (header, rows) — the column names and the data rows.

    Raises:
        CalibrationError: the file is missing, is not a CSV, is empty, has
            no header, or has no data row.
    """
    if not path.is_file():
        raise CalibrationError(f"missing run CSV: {path}")
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CalibrationError(f"empty CSV (no header): {path}")
            header = list(reader.fieldnames)
            rows = list(reader)
    except csv.Error as exc:
        raise CalibrationError(f"malformed CSV {path}: {exc!r}") from exc
    except OSError as exc:
        raise CalibrationError(f"cannot read {path}: {exc!r}") from exc
    if not rows:
        raise CalibrationError(f"no data rows in {path}")
    return header, rows


def _require_columns(path: Path, header: list[str], needed: tuple[str, ...]) -> None:
    """Raise a named error when a required column is absent.

    AXIOM A3: the message names the file AND the column, and says what the
    column is for, so the operator never has to guess.

    Parameters:
        path: the CSV being read (for the message).
        header: the CSV header.
        needed: the columns the caller requires.

    Raises:
        CalibrationError: at least one required column is absent.
    """
    missing = [column for column in needed if column not in header]
    if missing:
        raise CalibrationError(
            f"{path}: missing required column(s) {missing}. "
            f"This run predates CALIBRATION DESIGN §2.4 (the new CSV "
            f"columns: cd_unclamped, cd_raw_body_area, "
            f"cd_raw_presented_area, dsmc_surface_heat_load_jcm2, geom_*, "
            f"ref_area_*); it must be re-flown with the updated Ada writer "
            f"before it can be calibrated. "
            f"Columns present: {header}"
        )


def _column_values(
    path: Path, rows: list[dict[str, str]], column: str
) -> list[float]:
    """Extract one column of a CSV as floats.

    Parameters:
        path: the CSV (for the error message).
        rows: the parsed rows.
        column: the column to extract.

    Returns:
        The column values as floats, in row order.

    Raises:
        CalibrationError: a value is missing, empty, non-numeric or
            non-finite.
    """
    values: list[float] = []
    # CSV line numbers: the header is line 1, so the first data row is line 2.
    for index, row in enumerate(rows, start=2):
        raw = row.get(column)
        if raw is None or raw.strip() == "":
            raise CalibrationError(
                f"{path}: line {index}: column {column!r} is empty"
            )
        try:
            value = float(raw)
        except ValueError as exc:
            raise CalibrationError(
                f"{path}: line {index}: column {column!r} is not a number: "
                f"{raw!r}"
            ) from exc
        if not math.isfinite(value):
            raise CalibrationError(
                f"{path}: line {index}: column {column!r} is not finite: {raw!r}"
            )
        values.append(value)
    return values


def _classify(coded: tuple[float, float, float]) -> str:
    """Classify a coded point as a factorial corner, the centre, or neither.

    Parameters:
        coded: the clamped coded coordinates.

    Returns:
        "corner", "centre" or "off-design".
    """
    if all(abs(component) >= 1.0 - CODED_TOLERANCE for component in coded):
        return "corner"
    if all(abs(component) <= CODED_TOLERANCE for component in coded):
        return "centre"
    return "off-design"


def read_run(
    path: Path,
    centre: tuple[float, float, float],
    half: tuple[float, float, float],
    drag_aggregate: str = "final",
    sg_density: float = SG_DENSITY_KGM3,
    sg_velocity: float = SG_VELOCITY_MS,
) -> RunPoint:
    """Read one DSMC run CSV and reduce it to a calibration fit point.

    The physical triple comes from the FLOWN geometry columns (§2.4):
    ``X(1) = geom_diameter_m / 2``, ``X(2) = geom_toroid_radius_m`` and
    ``X(3) = geom_angle_deg``.

    Parameters:
        path: the run CSV.
        centre: the design-box centre (X coordinates).
        half: the design-box half-widths (X coordinates).
        drag_aggregate: "final" (the last trajectory row) or "mean" (the
            mean over the trajectory) — how the drag response is reduced
            from the per-step CSV column to one number.
        sg_density: the freestream density of the flight state used by the
            analytic heat law [kg/m^3].
        sg_velocity: the flight-state velocity used by the analytic heat
            law [m/s].

    Returns:
        The reduced run.

    Raises:
        CalibrationError: a required column is missing, a value is not a
            finite number, or the geometry is outside the mapping envelope.

    [Reference: CALIBRATION_DESIGN.md §2.4]
    """
    header, rows = _read_csv(path)
    _require_columns(path, header, REQUIRED_RUN_COLUMNS)

    for index, half_width in enumerate(half):
        if half_width <= 0.0:
            raise CalibrationError(
                f"{path}: design-box half-width {index + 1} must be positive, "
                f"got {half_width!r}"
            )

    diameter = _column_values(path, rows, COL_GEOM_DIAMETER)[-1]
    toroid = _column_values(path, rows, COL_GEOM_TORUS)[-1]
    angle = _column_values(path, rows, COL_GEOM_ANGLE)[-1]
    if diameter <= 0.0:
        raise CalibrationError(
            f"{path}: {COL_GEOM_DIAMETER} must be positive, got {diameter!r}"
        )
    x_physical = (diameter / 2.0, toroid, angle)

    nose_radius_flown: float | None = None
    if COL_GEOM_NOSE in header:
        nose_radius_flown = _column_values(path, rows, COL_GEOM_NOSE)[-1]

    cd_column = _column_values(path, rows, COL_CD_RAW_PRESENTED)
    if drag_aggregate == "mean":
        cd_dsmc = sum(cd_column) / len(cd_column)
    else:
        cd_dsmc = cd_column[-1]
    q_dsmc = _column_values(path, rows, COL_DSMC_SURFACE_HEAT)[-1]

    coded_raw = tuple(
        (value - centre[index]) / half[index] for index, value in enumerate(x_physical)
    )
    coded = tuple(
        coded_coordinate(x_physical[index], centre[index], half[index])
        for index in range(3)
    )

    try:
        cd_analytic = analytic_cd(*x_physical)
        q_analytic = analytic_heat_load_jcm2(
            x_physical[0], sg_density, sg_velocity
        )
    except ValueError as exc:
        raise CalibrationError(
            f"{path}: the flown geometry {x_physical!r} is outside the "
            f"screening-model envelope: {exc}"
        ) from exc

    cross_check = float("nan")
    if all(
        column in header
        for column in (COL_DRAG_SUM, COL_DYN_PRESS, COL_REF_AREA_PRESENTED)
    ):
        drag_sum = _column_values(path, rows, COL_DRAG_SUM)[-1]
        dyn_press = _column_values(path, rows, COL_DYN_PRESS)[-1]
        ref_area = _column_values(path, rows, COL_REF_AREA_PRESENTED)[-1]
        if dyn_press > 0.0 and ref_area > 0.0:
            recomputed = drag_sum / (dyn_press * ref_area)
            cross_check = abs(recomputed - cd_dsmc)

    return RunPoint(
        path=path,
        x_physical=x_physical,
        coded=coded,
        coded_raw=coded_raw,
        kind=_classify(coded),
        cd_dsmc=cd_dsmc,
        q_dsmc=q_dsmc,
        cd_analytic=cd_analytic,
        q_analytic=q_analytic,
        nose_radius_flown=nose_radius_flown,
        steps=len(rows),
        cd_cross_check=cross_check,
        optional_columns_present=tuple(
            column for column in OPTIONAL_RUN_COLUMNS if column in header
        ),
    )


# ---------------------------------------------------------------------------
#  The calibration file
# ---------------------------------------------------------------------------
def calibration_values(
    centre: tuple[float, float, float],
    half: tuple[float, float, float],
    cd_coefficients: tuple[float, ...],
    q_coefficients: tuple[float, ...],
) -> dict[str, float]:
    """Build the key/value map of the §2.6.2 calibration file.

    Parameters:
        centre: the design-box centre.
        half: the design-box half-widths.
        cd_coefficients: the seven drag coefficients.
        q_coefficients: the seven heat coefficients.

    Returns:
        The 21 calibration values, keyed by the §2.6.2 key names.

    Raises:
        ValueError: a coefficient vector does not have seven entries.
    """
    if len(cd_coefficients) != 7 or len(q_coefficients) != 7:
        raise ValueError(
            "calibration_values: both coefficient vectors must have seven "
            f"entries, got {len(cd_coefficients)} and {len(q_coefficients)}"
        )
    values: dict[str, float] = {"calibration_valid": 1.0}
    for index in range(3):
        values[f"centre_x{index + 1}"] = centre[index]
    for index in range(3):
        values[f"half_x{index + 1}"] = half[index]
    for suffix, coefficient in zip(COEFFICIENT_SUFFIXES, cd_coefficients):
        values[f"cd_{suffix}"] = coefficient
    for suffix, coefficient in zip(COEFFICIENT_SUFFIXES, q_coefficients):
        values[f"q_{suffix}"] = coefficient
    return values


def format_calibration_file(
    values: dict[str, float], provenance: list[str]
) -> str:
    """Render the calibration file text (§2.6.2 format).

    Parameters:
        values: the key/value map (see :func:`calibration_values`).
        provenance: extra ``#`` comment lines appended after the keys.

    Returns:
        The file text: the §2.6.2 header, the keys in §2.6.2 order, then the
        provenance comments.

    Raises:
        ValueError: a key of the §2.6.2 file is missing from ``values``.
    """
    missing = [key for key in CALIBRATION_KEYS if key not in values]
    if missing:
        raise ValueError(f"format_calibration_file: missing keys {missing}")
    lines: list[str] = list(CALIBRATION_HEADER)
    for key in CALIBRATION_KEYS:
        if key == "calibration_valid":
            # The §2.6.2 file writes the flag as an integer ("= 1"); every
            # other key is a real number.
            lines.append(f"{key} = {int(values[key])}")
        else:
            lines.append(f"{key} = {float(values[key])!r}")
    lines.extend(provenance)
    return "\n".join(lines) + "\n"


def parse_calibration_file(path: Path) -> dict[str, float]:
    """Parse a calibration file back into a key/value map.

    This is the READER the Ada loader mirrors (Text_IO, one ``key = value``
    per line, ``#`` comments skipped) and it is used by the round-trip
    self-test.

    Parameters:
        path: the calibration file.

    Returns:
        The parsed values.

    Raises:
        CalibrationError: the file is missing, a line is malformed, or a
            required key is absent.
    """
    if not path.is_file():
        raise CalibrationError(f"missing calibration file: {path}")
    values: dict[str, float] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalibrationError(f"cannot read {path}: {exc!r}") from exc
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise CalibrationError(
                f"{path}: line {number}: not a 'key = value' line: {raw_line!r}"
            )
        key, _, raw_value = line.partition("=")
        key = key.strip()
        raw_value = raw_value.strip()
        try:
            values[key] = float(raw_value)
        except ValueError as exc:
            raise CalibrationError(
                f"{path}: line {number}: value of {key!r} is not a number: "
                f"{raw_value!r}"
            ) from exc
    missing = [key for key in CALIBRATION_KEYS if key not in values]
    if missing:
        raise CalibrationError(f"{path}: missing key(s) {missing}")
    return values


def write_calibration_file(
    path: Path,
    values: dict[str, float],
    provenance: list[str],
) -> None:
    """Write the calibration file, creating its directory when needed.

    Parameters:
        path: the destination file.
        values: the key/value map.
        provenance: extra ``#`` comment lines.

    Raises:
        CalibrationError: the file could not be written.
    """
    text = format_calibration_file(values, provenance)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="ascii")
    except (OSError, UnicodeEncodeError) as exc:
        raise CalibrationError(f"cannot write {path}: {exc!r}") from exc


# ---------------------------------------------------------------------------
#  The fit itself
# ---------------------------------------------------------------------------
@dataclass
class FitResult:
    """The outcome of the calibration fit.

    Attributes:
        cd_coefficients: the seven drag coefficients.
        q_coefficients: the seven heat coefficients.
        fit_points: the runs that entered the fit.
        skipped: the runs that were read but not fitted (with the reason).
        anchor: the anchor run (if any).
        anchor_included: whether the anchor entered the fit.
        cd_before: the drag residuals of the uncalibrated model.
        cd_after: the drag residuals of the calibrated model.
        q_before: the heat residuals of the uncalibrated model.
        q_after: the heat residuals of the calibrated model.
        gram_off_diagonal: the largest off-diagonal entry of the Gram matrix
            of the fit design (0.0 for the canonical diagonal design).
        centre: the design-box centre used.
        half: the design-box half-widths used.
    """

    cd_coefficients: tuple[float, ...]
    q_coefficients: tuple[float, ...]
    fit_points: list[RunPoint] = field(default_factory=list)
    skipped: list[tuple[RunPoint, str]] = field(default_factory=list)
    anchor: RunPoint | None = None
    anchor_included: bool = False
    cd_before: list[float] = field(default_factory=list)
    cd_after: list[float] = field(default_factory=list)
    q_before: list[float] = field(default_factory=list)
    q_after: list[float] = field(default_factory=list)
    gram_off_diagonal: float = 0.0
    centre: tuple[float, float, float] = DEFAULT_CENTRE
    half: tuple[float, float, float] = DEFAULT_HALF


def _rms(values: list[float]) -> float:
    """Return the root-mean-square of a list of residuals.

    Parameters:
        values: the residuals.

    Returns:
        The RMS (0.0 for an empty list).
    """
    if not values:
        return 0.0
    return math.sqrt(sum(value * value for value in values) / len(values))


def _max_abs(values: list[float]) -> float:
    """Return the largest absolute value of a list of residuals.

    Parameters:
        values: the residuals.

    Returns:
        The largest |residual| (0.0 for an empty list).
    """
    if not values:
        return 0.0
    return max(abs(value) for value in values)


def _missing_corners(coded_points: list[tuple[float, float, float]]) -> list[str]:
    """Return the 2^3 factorial corners that are absent from a design.

    Only points that sit ON a corner count: the design centre (0, 0, 0) and
    any interior point must not be mistaken for the corner they are nearest
    to.

    Parameters:
        coded_points: the coded coordinates of the available points.

    Returns:
        The labels (e.g. "(-1,-1,+1)") of the missing corners.
    """
    present = {
        tuple(1 if component >= 0.0 else -1 for component in point)
        for point in coded_points
        if all(abs(component) >= 1.0 - CODED_TOLERANCE for component in point)
    }
    missing: list[str] = []
    for first in (-1, 1):
        for second in (-1, 1):
            for third in (-1, 1):
                if (first, second, third) not in present:
                    missing.append(
                        f"({first:+d},{second:+d},{third:+d})"
                    )
    return missing


def perform_fit(
    runs: list[RunPoint],
    anchor: RunPoint | None,
    centre: tuple[float, float, float],
    half: tuple[float, float, float],
) -> FitResult:
    """Fit the orthogonal residual model to the DSMC responses.

    AXIOM A4: the anchor enters the fit ONLY when it lies inside the design
    box (every UNCLAMPED coded coordinate within [-1, +1]); otherwise it is
    an out-of-box check.

    Parameters:
        runs: the CCD runs (the eight corners and the centre).
        anchor: the reference anchor run, if any.
        centre: the design-box centre.
        half: the design-box half-widths.

    Returns:
        The fit result.

    Raises:
        CalibrationError: a factorial corner is missing from the design, or
            the fit is impossible (no points at all).
    """
    fit_points: list[RunPoint] = []
    skipped: list[tuple[RunPoint, str]] = []
    for run in runs:
        if run.kind in ("corner", "centre"):
            fit_points.append(run)
        else:
            skipped.append(
                (run, "not a factorial corner and not the design centre")
            )
    if not fit_points:
        raise CalibrationError(
            "no usable fit point: the supplied runs are neither the eight "
            "factorial corners nor the design centre"
        )
    missing = _missing_corners([run.coded for run in fit_points])
    if missing:
        raise CalibrationError(
            f"the 2^3 factorial is incomplete: the corner(s) {missing} are "
            f"missing from the supplied runs. The closed-form contrast fit "
            f"needs all eight corners (the (1/8) divisor is the squared "
            f"norm of the contrast columns)."
        )

    anchor_included = False
    if anchor is not None:
        inside = all(
            abs(component) <= 1.0 + CODED_TOLERANCE
            for component in anchor.coded_raw
        )
        if inside:
            fit_points.append(anchor)
            anchor_included = True
        else:
            skipped.append(
                (
                    anchor,
                    (
                        "outside the design box (unclamped coded coordinates "
                        f"{tuple(round(value, 6) for value in anchor.coded_raw)}) "
                        "-> out-of-box check, not a fit point"
                    ),
                )
            )

    coded = [run.coded for run in fit_points]
    cd_residuals = [run.cd_dsmc - run.cd_analytic for run in fit_points]
    q_residuals = [run.q_dsmc - run.q_analytic for run in fit_points]

    cd_coefficients = fit_orthogonal_factorial(coded, cd_residuals)
    q_coefficients = fit_orthogonal_factorial(coded, q_residuals)

    cd_after = [
        residual - evaluate_model(cd_coefficients, *point)
        for residual, point in zip(cd_residuals, coded)
    ]
    q_after = [
        residual - evaluate_model(q_coefficients, *point)
        for residual, point in zip(q_residuals, coded)
    ]

    gram = gram_matrix(coded)
    off_diagonal = max(
        (
            abs(gram[row][column])
            for row in range(7)
            for column in range(7)
            if row != column
        ),
        default=0.0,
    )

    return FitResult(
        cd_coefficients=cd_coefficients,
        q_coefficients=q_coefficients,
        fit_points=fit_points,
        skipped=skipped,
        anchor=anchor,
        anchor_included=anchor_included,
        cd_before=cd_residuals,
        cd_after=cd_after,
        q_before=q_residuals,
        q_after=q_after,
        gram_off_diagonal=off_diagonal,
        centre=centre,
        half=half,
    )


# ---------------------------------------------------------------------------
#  The report
# ---------------------------------------------------------------------------
def render_report(result: FitResult) -> str:
    """Render the human-readable calibration report.

    Parameters:
        result: the fit result.

    Returns:
        The report text.
    """
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("  StellarOrion screening-model calibration")
    lines.append("  (orthogonal residual correction, CALIBRATION DESIGN 2.6)")
    lines.append("=" * 72)
    lines.append(
        "Design box: centre = "
        f"({result.centre[0]:.6f}, {result.centre[1]:.6f}, "
        f"{result.centre[2]:.6f})   half = "
        f"({result.half[0]:.6f}, {result.half[1]:.6f}, {result.half[2]:.6f})"
    )
    lines.append("")
    lines.append(f"Fit points ({len(result.fit_points)}):")
    for run in result.fit_points:
        marker = "ANCHOR" if (result.anchor is run) else run.kind
        lines.append(
            f"  [{marker:>7s}] {run.path.name}  "
            f"X=({run.x_physical[0]:.6f}, {run.x_physical[1]:.6f}, "
            f"{run.x_physical[2]:.6f})  "
            f"x=({run.coded[0]:+.3f}, {run.coded[1]:+.3f}, {run.coded[2]:+.3f})"
        )
        lines.append(
            f"             cd: DSMC={run.cd_dsmc:.6f}  analytic="
            f"{run.cd_analytic:.6f}  |  "
            f"q: DSMC={run.q_dsmc:.6f}  analytic={run.q_analytic:.6f}  J/cm^2"
        )
    if result.skipped:
        lines.append("")
        lines.append("Excluded from the fit:")
        for run, reason in result.skipped:
            lines.append(f"  - {run.path.name}: {reason}")
    lines.append("")
    lines.append("CALIBRATION DESIGN 2.4 optional columns present in the runs:")
    for run in result.fit_points:
        lines.append(
            f"  {run.path.name}: "
            f"{list(run.optional_columns_present) if run.optional_columns_present else 'none'}"
        )
    lines.append("")
    lines.append("Fitted drag coefficients (cd_raw_presented_area residual):")
    for suffix, coefficient in zip(COEFFICIENT_SUFFIXES, result.cd_coefficients):
        lines.append(f"  cd_{suffix:<4s} = {coefficient:+.12e}")
    lines.append("")
    lines.append("Fitted heat coefficients (dsmc_surface_heat_load residual):")
    for suffix, coefficient in zip(COEFFICIENT_SUFFIXES, result.q_coefficients):
        lines.append(f"  q_{suffix:<4s} = {coefficient:+.12e}")
    lines.append("")
    lines.append("Residuals over the fit set:")
    lines.append(
        f"  drag: before  RMS={_rms(result.cd_before):.6e}  "
        f"max={_max_abs(result.cd_before):.6e}"
    )
    lines.append(
        f"         after   RMS={_rms(result.cd_after):.6e}  "
        f"max={_max_abs(result.cd_after):.6e}"
    )
    lines.append(
        f"  heat: before  RMS={_rms(result.q_before):.6e}  "
        f"max={_max_abs(result.q_before):.6e}   [J/cm^2]"
    )
    lines.append(
        f"         after   RMS={_rms(result.q_after):.6e}  "
        f"max={_max_abs(result.q_after):.6e}   [J/cm^2]"
    )
    lines.append(
        f"  Gram off-diagonal norm = {result.gram_off_diagonal:.3e} "
        f"({'diagonal: the closed form IS the least-squares solution' if result.gram_off_diagonal <= 1.0e-9 else 'NOT diagonal: the fit is the orthogonal contrast estimator'})"
    )
    anchor = result.anchor
    if anchor is not None:
        lines.append("")
        if result.anchor_included:
            lines.append(
                "Anchor: INSIDE the design box -> included in the fit as the "
                f"{len(result.fit_points)}th point."
            )
        else:
            lines.append(
                "Anchor: OUTSIDE the design box -> NOT included in the fit; "
                "the residual below is an out-of-box check."
            )
        cd_residual = anchor.cd_dsmc - anchor.cd_analytic
        q_residual = anchor.q_dsmc - anchor.q_analytic
        cd_model = evaluate_model(result.cd_coefficients, *anchor.coded)
        q_model = evaluate_model(result.q_coefficients, *anchor.coded)
        lines.append(
            f"  {anchor.path.name}: X=({anchor.x_physical[0]:.6f}, "
            f"{anchor.x_physical[1]:.6f}, {anchor.x_physical[2]:.6f})  "
            f"coded=({anchor.coded[0]:+.3f}, {anchor.coded[1]:+.3f}, "
            f"{anchor.coded[2]:+.3f})"
        )
        lines.append(
            f"  drag residual before = {cd_residual:+.6e}   "
            f"after = {cd_residual - cd_model:+.6e}"
        )
        lines.append(
            f"  heat residual before = {q_residual:+.6e}   "
            f"after = {q_residual - q_model:+.6e}   [J/cm^2]"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Self-test
# ---------------------------------------------------------------------------
def _normal_equations_solution(
    coded_points: list[tuple[float, float, float]], responses: list[float]
) -> tuple[float, ...]:
    """Solve the normal equations by explicit Gaussian elimination.

    Used ONLY by the self-test, to prove that the closed-form contrast fit
    coincides with the least-squares solution on the canonical design
    (THEOREM T2).  The production path never builds a matrix.

    Parameters:
        coded_points: the coded coordinates of the design points.
        responses: the responses of the design points.

    Returns:
        The seven least-squares coefficients.

    Raises:
        ValueError: the normal equations are singular.
    """
    size = len(COEFFICIENT_SUFFIXES)
    basis = [monomial_vector(*point) for point in coded_points]
    matrix = [
        [
            sum(vector[row] * vector[column] for vector in basis)
            for column in range(size)
        ]
        + [sum(vector[row] * value for vector, value in zip(basis, responses))]
        for row in range(size)
    ]
    for pivot in range(size):
        best = max(range(pivot, size), key=lambda row: abs(matrix[row][pivot]))
        if abs(matrix[best][pivot]) < 1.0e-12:
            raise ValueError("normal equations are singular")
        matrix[pivot], matrix[best] = matrix[best], matrix[pivot]
        divisor = matrix[pivot][pivot]
        for column in range(pivot, size + 1):
            matrix[pivot][column] /= divisor
        for row in range(size):
            if row == pivot:
                continue
            factor = matrix[row][pivot]
            if factor == 0.0:
                continue
            for column in range(pivot, size + 1):
                matrix[row][column] -= factor * matrix[pivot][column]
    return tuple(matrix[row][size] for row in range(size))


def _self_test() -> int:
    """Run the self-tests and print one [PASS]/[FAIL] line per check.

    Returns:
        0 when every check passed, 1 otherwise.
    """
    failures = 0

    def _check(name: str, condition: bool, detail: str) -> None:
        nonlocal failures
        if condition:
            print(f"[PASS] {name} — {detail}")
        else:
            failures += 1
            print(f"[FAIL] {name} — {detail}")

    print("=== calibrate_from_dsmc self-test ===")

    # --- T1: orthogonality of the seven basis functions over the 8 corners --
    corners = [
        (float(a), float(b), float(c))
        for a in (-1.0, 1.0)
        for b in (-1.0, 1.0)
        for c in (-1.0, 1.0)
    ]
    gram = gram_matrix(corners)
    off_diagonal = max(
        abs(gram[row][column])
        for row in range(7)
        for column in range(7)
        if row != column
    )
    diagonal_ok = all(
        abs(gram[index][index] - 8.0) < 1.0e-9 for index in range(1, 7)
    )
    _check(
        "orthogonality of the 2^3 factorial basis",
        off_diagonal < 1.0e-9 and diagonal_ok,
        f"max |off-diagonal| = {off_diagonal:.3e}, contrast norms = "
        f"{[round(gram[index][index], 6) for index in range(1, 7)]}",
    )

    # --- T2: the closed form IS the least-squares solution on the canonical
    #        design (eight corners + the centre).
    #  The synthetic response is GENERATED FROM THE MODEL, so the design
    #  carries no component outside the seven-dimensional model span.  That
    #  is the only situation in which a seven-term model reproduces nine
    #  responses exactly (the 2^3 corner space has eight dimensions and the
    #  model spans seven of them), and it is the situation the calibration
    #  relies on: the residual surface IS a seven-term model.
    known_coefficients = (
        3.0, -1.5, 0.25, 0.75, -0.5, 0.125, 0.0625,
    )
    design = corners + [(0.0, 0.0, 0.0)]
    responses = [
        evaluate_model(known_coefficients, *point) for point in design
    ]
    closed_form = fit_orthogonal_factorial(design, responses)
    solved = _normal_equations_solution(design, responses)
    deviation = max(abs(a - b) for a, b in zip(closed_form, solved))
    _check(
        "closed form == explicit normal-equation least squares",
        deviation < 1.0e-9,
        f"max |closed form - normal equations| = {deviation:.3e}",
    )

    # --- the closed form recovers the coefficients of a model-generated
    #        response exactly (no aliasing on the orthogonal design) -------
    recovery = max(
        abs(a - b) for a, b in zip(closed_form, known_coefficients)
    )
    _check(
        "the fit recovers the generating coefficients",
        recovery < 1.0e-9,
        f"max |fitted - generated| = {recovery:.3e}",
    )

    # --- the fitted model reproduces the design responses ------------------
    reproduced = max(
        abs(
            evaluate_model(closed_form, *point) - value
        )
        for point, value in zip(design, responses)
    )
    _check(
        "the fitted model reproduces the design responses",
        reproduced < 1.0e-9,
        f"max |model - response| = {reproduced:.3e}",
    )

    # --- T3: a model that is already right yields a zero correction --------
    zero_coefficients = fit_orthogonal_factorial(design, [0.0] * len(design))
    _check(
        "zero residual -> zero correction",
        all(abs(value) <= 1.0e-12 for value in zero_coefficients),
        f"max |coefficient| = {max(abs(v) for v in zero_coefficients):.3e}",
    )

    # --- the reproduced analytic Cd law matches the Ada anchor value --------
    # The reference value was produced by the Ada screening model (32-bit
    # Float arithmetic), hence the 1e-6 absolute tolerance.
    cd_anchor = analytic_cd(1.5, 0.135, 60.0)
    _check(
        "analytic Cd law reproduces the Ada reference anchor",
        abs(cd_anchor - 1.6072782278060913) < 1.0e-6,
        f"Cd(1.5, 0.135, 60) = {cd_anchor!r} "
        f"(Ada reference 1.6072782278060913)",
    )

    # --- the reproduced analytic heat law matches the documented flight state -
    # C_SG * sqrt(6.9674e-4 / 0.55) * 2700**3, computed in double precision.
    sg_flux = (
        C_SG * math.sqrt(SG_DENSITY_KGM3 / (NOSE_RADIUS_RATIO * 1.5))
        * (SG_VELOCITY_MS ** 3)
    )
    _check(
        "analytic Sutton-Graves flux matches the documented flight state",
        abs(sg_flux - 122002.5192600951) < 1.0e-4,
        f"q_SG(anchor) = {sg_flux!r} W/m^2",
    )

    # --- the clamp behaves as the design prescribes ------------------------
    clamp_ok = (
        coded_coordinate(3.0, 1.0, 1.0) == 1.0
        and coded_coordinate(-3.0, 1.0, 1.0) == -1.0
        and coded_coordinate(1.5, 1.0, 1.0) == 0.5
    )
    _check(
        "coded coordinate clamp",
        clamp_ok,
        "clamp((X-centre)/half, -1, +1) verified at +1, -1 and 0.5",
    )

    # --- the calibration file round-trips through the Ada-style reader -----
    values = calibration_values(
        DEFAULT_CENTRE,
        DEFAULT_HALF,
        closed_form,
        closed_form,
    )
    with tempfile.TemporaryDirectory(prefix="calibrate_selftest_") as folder:
        target = Path(folder) / "hiad_calibration.txt"
        try:
            write_calibration_file(target, values, ["# self-test"])
            parsed = parse_calibration_file(target)
        except CalibrationError as exc:  # pragma: no cover - defensive
            _check("calibration file round-trip", False, str(exc))
        else:
            same = all(
                abs(parsed[key] - values[key]) <= 1.0e-12 * max(
                    1.0, abs(values[key])
                )
                for key in CALIBRATION_KEYS
            )
            _check(
                "calibration file round-trip (KEY = VALUE)",
                same and len(parsed) == len(CALIBRATION_KEYS),
                f"{len(parsed)} keys written and read back identically",
            )

    if failures:
        print(f"=== self-test FAILED ({failures} failing check(s)) ===")
        return 1
    print("=== self-test PASSED ===")
    return 0


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def _default_output_path() -> Path:
    """Return the default calibration file path (§2.5/§2.6.2).

    Returns:
        ``<repo>/src/python/hiad_calibration.txt``, derived from this
        script's own location (never from the current working directory).
    """
    return Path(__file__).resolve().parent.parent / "src" / "python" / "hiad_calibration.txt"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line.

    Parameters:
        argv: the argument list (defaults to ``sys.argv[1:]``).

    Returns:
        The parsed namespace.

    Raises:
        SystemExit: argparse rejected the usage (exit code 2).
    """
    parser = argparse.ArgumentParser(
        prog="calibrate_from_dsmc.py",
        description=(
            "Fit the orthogonal residual correction of the StellarOrion "
            "screening model against the DSMC calibration runs and write the "
            "KEY = VALUE calibration file (CALIBRATION DESIGN 2.6.2)."
        ),
    )
    parser.add_argument(
        "--run", action="append", default=[], type=Path, metavar="CSV",
        help="a DSMC validation run CSV of the local CCD (repeatable; the "
             "eight factorial corners plus the centre point)",
    )
    parser.add_argument(
        "--anchor", type=Path, default=None, metavar="CSV",
        help="the reference anchor run (the IRVE-3 reference geometry). It "
             "joins the fit only when it lies inside the design box; "
             "otherwise it is reported as an out-of-box check",
    )
    parser.add_argument(
        "--centre-x1", type=float, default=DEFAULT_CENTRE[0],
        help=f"design-box centre, X(1) [m] (default {DEFAULT_CENTRE[0]})",
    )
    parser.add_argument(
        "--centre-x2", type=float, default=DEFAULT_CENTRE[1],
        help=f"design-box centre, X(2) [m] (default {DEFAULT_CENTRE[1]})",
    )
    parser.add_argument(
        "--centre-x3", type=float, default=DEFAULT_CENTRE[2],
        help=f"design-box centre, X(3) [deg] (default {DEFAULT_CENTRE[2]})",
    )
    parser.add_argument(
        "--half-x1", type=float, default=DEFAULT_HALF[0],
        help=f"design-box half-width, X(1) [m] (default {DEFAULT_HALF[0]})",
    )
    parser.add_argument(
        "--half-x2", type=float, default=DEFAULT_HALF[1],
        help=f"design-box half-width, X(2) [m] (default {DEFAULT_HALF[1]})",
    )
    parser.add_argument(
        "--half-x3", type=float, default=DEFAULT_HALF[2],
        help=f"design-box half-width, X(3) [deg] (default {DEFAULT_HALF[2]})",
    )
    parser.add_argument(
        "--out", type=Path, default=None, metavar="FILE",
        help="the calibration file to write (default: "
             "src/python/hiad_calibration.txt)",
    )
    parser.add_argument(
        "--sg-density", type=float, default=SG_DENSITY_KGM3, metavar="KG_M3",
        help="freestream density of the flight state used by the ANALYTIC "
             f"heat law [kg/m^3] (default {SG_DENSITY_KGM3}, the state the "
             "SPARTA package uses: stellarorion_test_modes.adb:1298)",
    )
    parser.add_argument(
        "--sg-velocity", type=float, default=SG_VELOCITY_MS, metavar="M_S",
        help="flight-state velocity used by the ANALYTIC heat law [m/s] "
             f"(default {SG_VELOCITY_MS}, the state the SPARTA package uses: "
             "stellarorion_test_modes.adb:1297)",
    )
    parser.add_argument(
        "--drag-aggregate", choices=("final", "mean"), default="final",
        help="how the per-step drag response is reduced to one number: "
             "'final' (the last trajectory row, default) or 'mean' (the "
             "mean over the trajectory)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="fit and report, but do not write the calibration file",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="run the orthogonality, closed-form, law-reproduction and "
             "file round-trip checks, print [PASS]/[FAIL] lines and exit",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return args
    if not args.run:
        parser.error(
            "at least one --run CSV is required (use --self-test to run the "
            "checks without any data)"
        )
    for index, half in enumerate((args.half_x1, args.half_x2, args.half_x3)):
        if half <= 0.0:
            parser.error(
                f"--half-x{index + 1} must be positive, got {half}"
            )
    if args.sg_density <= 0.0 or args.sg_velocity <= 0.0:
        parser.error(
            "--sg-density and --sg-velocity must be strictly positive, got "
            f"{args.sg_density!r} and {args.sg_velocity!r}"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the calibration fitter.

    Parameters:
        argv: the argument list (defaults to ``sys.argv[1:]``).

    Returns:
        0 on success (or a passing self-test), 1 on a data/IO error.
    """
    args = _parse_args(argv)

    if args.self_test:
        return _self_test()

    centre = (args.centre_x1, args.centre_x2, args.centre_x3)
    half = (args.half_x1, args.half_x2, args.half_x3)

    try:
        runs = [
            read_run(
                path, centre, half, args.drag_aggregate,
                args.sg_density, args.sg_velocity,
            )
            for path in args.run
        ]
        anchor = (
            read_run(
                args.anchor, centre, half, args.drag_aggregate,
                args.sg_density, args.sg_velocity,
            )
            if args.anchor is not None
            else None
        )
        result = perform_fit(runs, anchor, centre, half)
    except CalibrationError as exc:
        print(f"calibrate_from_dsmc: ERROR: {exc}", file=sys.stderr)
        return 1

    print(render_report(result))
    print(
        f"Analytic heat law flight state: rho = {args.sg_density!r} kg/m^3, "
        f"V = {args.sg_velocity!r} m/s (Sutton-Graves, tau = {TAU_SEC!r} s)"
    )

    if args.dry_run:
        print("\n[dry-run] no calibration file written.")
        return 0

    output = args.out if args.out is not None else _default_output_path()
    provenance = [
        (
            f"# Fitted by scripts/calibrate_from_dsmc.py on "
            f"{len(result.fit_points)} design point(s)."
        ),
        f"# Design box centre = ({centre[0]!r}, {centre[1]!r}, {centre[2]!r})",
        f"# Design box half   = ({half[0]!r}, {half[1]!r}, {half[2]!r})",
        "# cd_* are residuals of cd_raw_presented_area; q_* are residuals of",
        "# dsmc_surface_heat_load_jcm2 (J/cm^2).",
    ]
    if result.anchor is not None and not result.anchor_included:
        provenance.append(
            "# The reference anchor lies OUTSIDE the design box and was NOT "
            "fitted;"
        )
        provenance.append(
            "# it is reported as an out-of-box check in the fitter's report."
        )
    values = calibration_values(
        centre, half, result.cd_coefficients, result.q_coefficients
    )
    try:
        write_calibration_file(output, values, provenance)
    except CalibrationError as exc:
        print(f"calibrate_from_dsmc: ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nWrote calibration file: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
