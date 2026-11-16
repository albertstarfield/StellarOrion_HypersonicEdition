#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
"""Typeset the seven governing equations of the DSMC CFD subsection.

WHY: every slide of that subsection carries a companion slide with its
governing equation, and no such picture exists in the thesis. Each equation
is typeset with the mathtext of matplotlib into a picture of its own, taken
verbatim from chapter 3 of the thesis, with the label it carries there
printed under it. Under the equations sits a glossary of the symbols, packed
into lines measured against the real renderer, so the reader can see what
every variable of the formula means without leaving the slide.

The script writes only into the figures folder of the deck. It runs with the
interpreter of the thesis, because that is the interpreter that already holds
matplotlib and the project virtual environment must not be polluted.

Citations:
    Matplotlib 3.11.2, https://matplotlib.org/stable/api/mathtext_api.html
"""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parents[2]
#: A picture below this size in bytes was not written properly.
MIN_PICTURE_BYTES = 5000
#: The glossary never needs more lines than this on one picture.
#: WHY FIVE AND A TIGHTER STEP: the plate reserves a band under the glossary
#: for the assumption and the source label, so five lines are only allowed
#: because the step between them is smaller than it used to be.
MAX_GLOSSARY_LINES = 5
#: The smallest type the glossary is allowed to fall to.
MIN_GLOSSARY_PT = 8.5
FIGURES = PROJECT / "figures"
VENV_PYTHON = REPO / "Lost+Found/ProgressReport/CurrentThesisFinalReport/.venv-pdf/bin/python"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"

#: The assumption that makes each equation valid, drawn inside its picture.
#:
#: WHY INSIDE THE PICTURE: an assumption that lives only in a slide footer is
#: lost the moment the picture is lifted out of the deck, and the whole point of
#: the line is that the reader can see what the formula takes for granted.
ASSUMPTIONS: dict[str, str] = {
    "thesis_equation_shape.png": "a body of revolution, so every torus is a circular arc on a cone",
    "thesis_equation_setup.png": "a dilute gas with binary collisions and molecular chaos, closed by the VSS law",
    "thesis_equation_mesh.png": "each cell is finer than the local mean free path, so the continuum holds",
    "thesis_equation_convergence.png": "the samples are independent and each window is stationary",
    "thesis_equation_convection.png": "cold wall, Earth air, no ablation and no rarefaction correction",
    "thesis_equation_conduction.png": "one dimension along the stack, a lumped backface and constant ply properties",
    "thesis_equation_radiation.png": "a grey, diffuse, opaque surface facing space in steady balance",
    "thesis_equation_design_space.png": (
        "the nose radius follows from the five scalars and mass cancels"
        " in the ballistic ratio"
    ),
    "thesis_equation_cost_function.png": "four dimensionless objectives evaluated at one fixed exposure time",
    "thesis_equation_ga.png": "the cost is bounded and closed-form, so no solver call is needed",
    "thesis_equation_lateral.png": (
        "a lumped in-plane conductance applied after the one-dimensional solve"
    ),
    "thesis_equation_double_pass.png": (
        "the fidelity ratio is taken within one run, so only the thermal"
        " term carries the bias"
    ),
}

#: The field separator that passes a list through one command line argument.
SEP = chr(30)

#: (file name, lines of mathtext, source label of the thesis, glossary entries)
EQUATIONS: list[tuple[str, list[str], str, list[str]]] = [
    (
        "thesis_equation_shape.png",
        [
            r"$R_n = \kappa\, X_1, \qquad \kappa = 0.3667$",
            (
                r"$R_{max} = X_1\cos\gamma + (2N_t - 1)\,X_2\cos\gamma + X_2,"
                r" \qquad \gamma = \frac{\pi}{2} - X_3$"
            ),
        ],
        "chapter 3, Eq. nose_ratio and Eq. rmax",
        [
            "R_n = nose radius (m)",
            "X_1 = body radius (m)",
            "X_2 = torus radius (m)",
            "X_3 = half-cone angle (deg)",
            "gamma = pi/2 - X_3, the cone angle (rad)",
            "N_t = number of toroids",
            "R_max = outer radius of the stack (m)",
            "kappa = 0.3667, the nose ratio",
        ],
    ),
    (
        "thesis_equation_setup.png",
        [
            (
                r"$\frac{\partial f}{\partial t} + \mathbf{v}\cdot\nabla_{\mathbf{x}} f"
                r" + \frac{\mathbf{F}}{m}\cdot\nabla_{\mathbf{v}} f"
                r" = \left(\frac{\partial f}{\partial t}\right)_{coll}$"
            ),
            r"$\sigma = \pi d_{ref}^2 \left(\frac{g_{ref}}{g}\right)^{2(\omega - 0.5)}$",
        ],
        "chapter 3, the Boltzmann equation and the VSS cross-section",
        [
            "f = velocity distribution of the gas",
            "t = time (s)",
            "x = position (m)",
            "v = molecular velocity (m/s)",
            "F = force on a molecule (N)",
            "m = molecular mass (kg)",
            "sigma = collision cross-section (m2)",
            "omega = viscosity index of the VSS model",
        ],
    ),
    (
        "thesis_equation_mesh.png",
        [
            r"$Kn = \frac{\lambda}{L}$",
            r"$\lambda = \frac{1}{\sqrt{2}\,\pi d^2 n}$",
            r"$\Delta x < \lambda$",
        ],
        "chapter 3, the Knudsen number and the mean free path",
        [
            "Kn = Knudsen number",
            "lambda = mean free path (m)",
            "L = reference length of the vehicle (m)",
            "d = molecular diameter (m)",
            "n = number density of the gas (m^-3)",
            "Delta x = cell width of the Cartesian grid (m)",
        ],
    ),
    (
        "thesis_equation_convergence.png",
        [
            r"$\text{noise} \propto \frac{1}{\sqrt{N_{samples}}}$",
            r"$\frac{|\Delta C_d|}{|C_d|} < 0.02 \quad\text{over consecutive windows}$",
        ],
        "chapter 3, statistical convergence monitoring",
        [
            "N_samples = independent particle samples",
            "C_d = drag coefficient",
            "window = 100 particle steps, the default interval",
            "|Delta C_d| = change between consecutive windows",
            "criterion = under 2 percent",
            "reached after 500 to 1100 particle steps",
        ],
    ),
    (
        "thesis_equation_convection.png",
        [
            r"$\dot{q}_{stag} = C_{SG}\sqrt{\frac{\rho_\infty}{R_N}}\; V_\infty^3$",
            r"$C_{SG} = 1.7415 \times 10^{-4}$",
        ],
        "chapter 3, the Sutton-Graves correlation",
        [
            "q_stag = stagnation heat flux (W/m2)",
            "C_SG = Sutton-Graves constant for air",
            "rho_inf = freestream density (kg/m3)",
            "R_N = nose radius (m)",
            "V_inf = freestream velocity (m/s)",
        ],
    ),
    (
        "thesis_equation_conduction.png",
        [
            (
                r"$\dot{q}_{wall} = \frac{T_{surf} - T_{back}}{R}"
                r" + \epsilon\sigma\left(T_{surf}^4 - T_\infty^4\right)$"
            ),
            (
                r"$T_{back} = T_{init} + \frac{\dot{q}\,\Delta t\, \eta_{lag}}"
                r"{\rho_{TPS}\, C_{p,TPS}\, \delta_{TPS}}$"
            ),
        ],
        "chapter 3, the thermal balance and the backface model",
        [
            "q_wall = wall heat flux (W/m2)",
            "T_surf, T_back = surface and backface temperatures (K)",
            "T_inf, T_init = freestream and initial temperatures (K)",
            "R = thermal resistance of the stack (m2 K/W)",
            "epsilon = emissivity of the ply",
            "sigma = 5.67e-8, the Stefan-Boltzmann constant",
            "Delta t = time step (s), eta_lag = thermal lag factor",
            "rho, C_p, delta = density, heat capacity and thickness of the TPS",
        ],
    ),
    (
        "thesis_equation_radiation.png",
        [
            r"$\dot{q} = \epsilon\sigma T^4$",
            r"$T_{surface} = \left(\frac{\dot{q}_{stag}}{\epsilon\sigma}\right)^{1/4}$",
        ],
        "chapter 3, radiative equilibrium",
        [
            "q = radiated heat flux (W/m2)",
            "epsilon = emissivity of the hot face",
            "sigma = 5.67e-8, the Stefan-Boltzmann constant",
            "T = absolute surface temperature (K)",
            "q_stag = incoming stagnation heat flux (W/m2)",
        ],
    ),
    (
        "thesis_equation_design_space.png",
        [
            r"$\mathbf{x} = (X_1,\ X_2,\ X_3,\ N_t,\ m)$",
            r"$X_1 = D/2, \qquad X_2 = r_{tor}, \qquad X_3 = \theta_c$",
        ],
        "chapter 3, the design vector of the design space",
        [
            "x = design vector of the five variables",
            "X_1 = D/2 = body radius (m)",
            "X_2 = r_tor = torus radius (m)",
            "X_3 = theta_c = half-cone angle (deg)",
            "N_t = number of toroids",
            "m = vehicle mass (kg)",
            "kappa = 0.3667, the nose radius ratio",
        ],
    ),
    (
        "thesis_equation_cost_function.png",
        [
            (
                r"$J(\mathbf{x}) = W_{HL}\frac{Q}{Q_{target}}"
                r" + W_{q}\frac{\dot{q}_{SG}}{\dot{q}_{ref}}"
                r" + W_{\beta}\left(\frac{\beta}{\beta_{ref}} - 1\right)^{2}$"
            ),
            (
                r"$+ \ W_{Cd}\,\max\!\left(0,\ \frac{C_{d,goal} - C_d}"
                r"{C_{d,goal}}\right) + \Lambda_{pen}\,\Phi(\mathbf{x})$"
            ),
            r"$Q = \dot{q}_{SG}\,\tau, \qquad \tau = 13.582459\ \mathrm{s}$",
        ],
        "chapter 3, the composite cost and the heat load",
        [
            "J = composite cost the search minimises",
            "W_HL, W_q, W_beta, W_Cd = weights of the four terms",
            "Q = total heat load, Q_target its target",
            "q_stag = stagnation heat flux, q_ref its reference",
            "beta = ballistic coefficient, beta_ref its reference",
            "C_d = drag coefficient, C_d_goal the wanted value",
            "Lambda_pen = weight of the penalty Phi(x)",
            "tau = exposure time of the entry (s)",
        ],
    ),
    (
        "thesis_equation_ga.png",
        [
            r"$P = 50, \qquad G_{max} = 200, \qquad k_t = 3$",
            r"$p_c = 0.7, \qquad p_m = 0.1, \qquad \epsilon = 10^{-6}$",
        ],
        "chapter 3, the operators and the stopping rule of the genetic algorithm",
        [
            "P = designs in one generation",
            "G_max = maximum number of generations",
            "k_t = size of the tournament that picks a parent",
            "p_c = probability of crossover",
            "p_m = probability of mutation for each gene",
            "epsilon = stagnation tolerance on the best cost",
        ],
    ),
    (
        "thesis_equation_double_pass.png",
        [
            (
                r"$c = \mathrm{clamp}\!\left(\frac{q^{DSMC}_{flux}}"
                r"{q^{SG}_{flux}},\ 0.5,\ 2.0\right)$"
            ),
            (
                r"$J^{(2)}(\mathbf{x}) = J(\mathbf{x})"
                r" + (c - 1)\,\frac{Q(\mathbf{x})}{Q_{target}}$"
            ),
        ],
        "chapter 3, the correction factor and the corrected cost",
        [
            "c = fidelity ratio of solver over correlation",
            "q_DSMC = peak surface flux measured by the solver",
            "q_SG = Sutton-Graves prediction of the same run",
            "0.5 and 2.0 = the clamp limits of the factor",
            "J = cost of the first pass",
            "J(2) = corrected cost of the second pass",
            "Q/Q_target = normalised heat load term",
        ],
    ),
    (
        "thesis_equation_lateral.png",
        [
            r"$\dot{q}_{lat} = G_{lat}\left(T_{surf} - T_{surf}^{nb}\right)$",
        ],
        "chapter 3, Eq. lateral",
        [
            "q_lat = in-plane flux added to the element (W/m2)",
            "G_lat = lumped lateral conductance (W/m2 K)",
            "T_surf = surface temperature of the element (K)",
            "T_surf^nb = mean surface temperature of its neighbours (K)",
        ],
    ),
]

DRIVER = r"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

out_dir = Path(sys.argv[1])
lines = sys.argv[2].split(chr(30))
label = sys.argv[3]
entries = sys.argv[4].split(chr(30)) if sys.argv[4] else []
max_lines = int(sys.argv[5])
min_size = float(sys.argv[6])
assumption = sys.argv[7]

plt.rcParams["mathtext.fontset"] = "dejavusans"
figure, axis = plt.subplots(figsize=(7.7, 4.0), dpi=200)
axis.axis("off")
axis.set_xlim(0.0, 1.0)
axis.set_ylim(0.0, 1.0)
# WHY: the equations keep the upper band, the glossary of the symbols sits
# under them and the source label closes the picture, so no block can land
# on top of another whatever the count of equations is.
count = len(lines)
if count <= 2:
    start, step = 0.88, 0.24
else:
    start, step = 0.90, 0.19
equation_artists = []
for index, line in enumerate(lines):
    artist = axis.text(
        0.5,
        start - index * step,
        line,
        ha="center",
        va="center",
        fontsize=19,
        color="#0A132C",
    )
    equation_artists.append(artist)

# WHY: an equation that runs past the canvas is unreadable, so every line is
# measured against the real renderer and the type is stepped down while any
# one of them is wider than the band it sits in. A line that still does not
# fit at the smallest size stops the render instead of being cut off.
renderer = figure.canvas.get_renderer()
limit_px = int(0.94 * figure.get_size_inches()[0] * figure.dpi)
equation_size = 19.0
while True:
    widest = max(artist.get_window_extent(renderer=renderer).width for artist in equation_artists)
    if widest <= limit_px:
        break
    equation_size -= 1.0
    if equation_size < 14.0:
        raise SystemExit(
            "an equation still needs %.0f px at %g pt, only %.0f px fit"
            % (widest, equation_size, limit_px)
        )
    for artist in equation_artists:
        artist.set_fontsize(equation_size)

# WHY: a glossary line that runs past the canvas is unreadable, so the
# entries are packed into lines measured against the real renderer and the
# type is stepped down while the pack still needs more lines than fit.
SEPARATOR = "   |   "
renderer = figure.canvas.get_renderer()
limit_px = int(0.94 * figure.get_size_inches()[0] * figure.dpi)
size = 10.5
while True:
    probe = axis.text(0.0, -1.0, "", fontsize=size)
    packed = [""]
    for entry in entries:
        candidate = entry if not packed[-1] else packed[-1] + SEPARATOR + entry
        probe.set_text(candidate)
        if probe.get_window_extent(renderer=renderer).width <= limit_px:
            packed[-1] = candidate
        else:
            packed.append(entry)
    probe.remove()
    if len(packed) <= max_lines or size <= min_size:
        break
    size -= 0.5
# WHY: dropping a symbol the reader needs would be a silent failure, so a
# glossary that still does not fit stops the render instead of being cut.
if len(packed) > max_lines:
    raise SystemExit(
        "the glossary needs %d lines at %g pt, only %d fit" % (len(packed), size, max_lines)
    )
top = 0.44 if count <= 2 else 0.40
# WHY: the glossary sits under the equations and above the reserved band of
# the assumption and the label, so the three blocks can never land on each
# other whatever the length of the glossary turns out to be.
# WHY THE STEP DEPENDS ON THE COUNT: a plate with three equations starts its
# glossary lower, so its lines are packed a little tighter to keep the last
# of them clear of the assumption band.
step = 0.055 if count <= 2 else 0.048
for index, line in enumerate(packed[:max_lines]):
    axis.text(
        0.035,
        top - index * step,
        line,
        ha="left",
        va="center",
        fontsize=size,
        color="#334155",
    )

# WHY INSIDE THE PICTURE: the assumption is what the formula takes for
# granted, so it is drawn into the plate and travels with it. The usable width
# is measured from where the text starts, not from the edge of the canvas, and
# it is cut by a margin: a line that overruns the plate is a failure, and the
# first version of this block did exactly that on the conduction plate.
prefix = "Assumption: "
start_x = 0.035
renderer = figure.canvas.get_renderer()
axes_px = figure.get_size_inches()[0] * figure.dpi * 0.96
limit_px = axes_px * (1.0 - start_x) - 30
assume_size = 10.0
probe = axis.text(0.0, -1.0, "", fontsize=assume_size, weight="bold")


def _fits(value: str, size_pt: float) -> bool:
    probe.set_fontsize(size_pt)
    probe.set_text(value)
    return probe.get_window_extent(renderer=renderer).width <= limit_px


while assume_size > 8.5 and not _fits(prefix + assumption, assume_size):
    assume_size -= 0.5
assume_lines = [prefix + assumption]
if not _fits(prefix + assumption, assume_size):
    words = (prefix + assumption).split()
    half = len(words) // 2
    while half > 1:
        first = " ".join(words[:half])
        second = " ".join(words[half:])
        if _fits(first, assume_size) and _fits(second, assume_size):
            break
        half -= 1
    assume_lines = [" ".join(words[:half]), " ".join(words[half:])]
probe.remove()
assume_ys = [0.150] if len(assume_lines) == 1 else [0.178, 0.120]
for assume_y, assume_line in zip(assume_ys, assume_lines):
    axis.text(
        start_x,
        assume_y,
        assume_line,
        ha="left",
        va="center",
        fontsize=assume_size,
        color="#9C2B2B",
        weight="bold",
    )

axis.text(
    0.5,
    0.035,
    label,
    ha="center",
    va="center",
    fontsize=10.5,
    color="#475569",
    style="italic",
)
figure.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
figure.savefig(out_dir, facecolor="white")
"""


def render(
    name: str, maths: list[str], label: str, glossary: list[str], assumption: str,
) -> str:
    """Render one equation picture and verify what it wrote.

    Args:
        name: The file name of the picture inside the figures folder.
        maths: The lines of mathtext that form the equations.
        label: The provenance label of the thesis printed under the picture.
        glossary: The entries that say what every symbol of the equations means.
        assumption: The assumption the equation is valid under, drawn inside
            the picture under the glossary.

    Returns:
        A message describing what was written.

    Raises:
        SystemExit: When the render failed or the picture is too small.
    """
    target = FIGURES / name
    if target.is_file():
        backup = BACKUP_DIR / f"{name}.before"
        _ = backup.write_bytes(target.read_bytes())
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(VENV_PYTHON),
            "-c",
            DRIVER,
            str(target),
            SEP.join(maths),
            label,
            SEP.join(glossary),
            str(MAX_GLOSSARY_LINES),
            str(MIN_GLOSSARY_PT),
            assumption,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        _ = sys.stdout.write(f"MISMATCH {name} failed: {completed.stderr.strip()[-1200:]}\n")
        raise SystemExit(1)
    if not target.is_file() or target.stat().st_size < MIN_PICTURE_BYTES:
        _ = sys.stdout.write(f"MISMATCH {name} was not written\n")
        raise SystemExit(1)
    return f"typeset {name} ({target.stat().st_size} bytes)"


def main() -> int:
    """Render every equation picture and verify what was written.

    Returns:
        Zero when every picture was written, one when a render failed.

    """
    if not VENV_PYTHON.is_file():
        _ = sys.stdout.write(f"MISMATCH the interpreter of the thesis is missing: {VENV_PYTHON}\n")
        return 1
    _ = FIGURES.mkdir(parents=True, exist_ok=True)
    _ = BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        for name, maths, label, glossary in EQUATIONS:
            _ = sys.stdout.write(
                render(name, maths, label, glossary, ASSUMPTIONS[name]) + "\n",
            )
    except SystemExit as error:
        if error.code == 0:
            return 0
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
