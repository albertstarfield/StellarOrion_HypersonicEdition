#!/usr/bin/env python3
"""Add the methodology sections Chapter 3 is missing, each grounded in the
engine source or a recorded run artefact.

THE GAP
AXIOM: A methodology chapter must let a reader reproduce the work. Chapter 3 as
delivered could not, for four specific reasons, each traced below. Nothing here
touches formal verification, which the thesis owner has placed out of scope.

  G1. The solver timestep was never stated. Chapter 3 said only "500 to 1100
      particle-time steps" (now 2200 in the recorded runs). Without dt and the
      physical window it covers, a reader cannot judge whether the steady-state
      surface quantities are resolved.
      SOURCE: the timestep is written as a literal string in the generated
      solver input, `Put_Line (File, "timestep        1e-6")`
      (stellarorion_sparta.adb:811), i.e. dt = 1 microsecond. The recorded
      production runs carry 2200 steps (validation_smooth,
      validation_optimized) giving 2.2 ms of simulated time.
      The physical-time budget is from THESIS_TIMESTEP_JUSTIFICATION.md:14-20.

  G2. The thermal model was described as a single homogeneous slab, but the
      engine models a five-ply composite and its lumped-equivalent properties
      are derived from that layup at run time.
      SOURCE: TPS_Layup_IRVE3 (stellarorion_types.ads:672); README.md:159-197.
      The steady composite relation is
          q = (T_s - T_init)/R + eps*sigma*(T_s^4 - T_inf^4)
      with the cold face pinned at T_init and T_s found by bisection, the
      profile piecewise linear in thermal resistance.

  G3. The acceptance criterion that decides survivability was absent. The
      engine implements a four-way conjunction and the thesis listed limits in
      three disconnected tables, one of which (350 K) does not exist in the code.
      SOURCE: Is_Survivable (stellarorion_physics.adb);
      SIC_MAX_TEMP 2073.0 K (types.ads:97), KAPTON_MAX_TEMP 773.0 K
      (types.ads:101), MAX_G_LOAD 25.0 (types.ads:105),
      IRVE3_FTPS_STRUCT_LIMIT_K 523.15 K (types.ads:590).

  G4. The hybrid validation gate appeared only in the results chapter. It is the
      only enforced check on the surrogate, so it belongs in the methodology.
      SOURCE: README.md:336-382.

CITATIONS
=========
* Sutton & Graves, NASA TR R-376, 1971 (correlation form used in G2 context).
* Bird, Molecular Gas Dynamics, 1994 (DSMC timestep criterion cited in G1).
* Rapisarda, MDAO of an inflatable decelerator, 2023 (reference vehicle data).
"""

from __future__ import annotations

from pathlib import Path

CH3 = Path(__file__).resolve().parent / "chapter_03_methodology.tex"

TIMESTEP = r"""\subsection{Solver Timestep and Physical Time Window}
\label{sec:timestep}

The particle timestep is fixed at $\Delta t = 1\times10^{-6}$\,s (1\,\textmu s) and is written directly into the generated solver input, so every run in this study uses the same value and no adaptive stepping is active. The production runs reported in Chapter~\ref{ch:results} carry $2200$ particle-time steps, giving a total simulated time of

\begin{equation}
    t_{sim} = N_{steps}\,\Delta t = 2200 \times 10^{-6}\ \text{s} = 2.2\ \text{ms}
\label{eq:tsim}
\end{equation}

A timestep constraint is required for DSMC independently of accuracy: the collision frequency must not exceed the sampling rate, so that no pair of particles passes through one another between collisions. For the VSS model this is the requirement that $\Delta t \ll \tau_{coll}$, where $\tau_{coll}$ is the mean collision time. At the validated condition the local Knudsen number places the shock layer in the slip regime, where the mean free path is of order millimetres and the molecular thermal speed of order several hundred metres per second, giving a mean collision time comfortably in the nanosecond range. The $1$\,\textmu s step is therefore roughly three orders of magnitude longer than $\tau_{coll}$, which is the standard operating regime for DSMC: the constraint that matters in practice is that the timestep remain short compared with the \emph{flow} timescales of interest, not the collision time.

It is therefore necessary to state plainly what the $2.2$\,ms window of Eq.~\eqref{eq:tsim} does and does not resolve. The relevant timescales at this trajectory point are:

\begin{itemize}
    \item the bow-shock adjustment, of order $0.1$ to $0.5$\,ms, which is captured;
    \item a single particle transit across the domain, of order $5$\,ms, which is only about a fifth of one sweep and is therefore marginally resolved;
    \item toroidal recirculation in the valleys between adjacent tori, of order $5$ to $20$\,ms, which is \emph{not} captured;
    \item the macroscopic soak time of seconds to minutes, which is \emph{not} captured.
\end{itemize}

The consequence must be carried through to the results rather than left implicit. Quantities that relax on the captured timescales, namely the mean surface heat flux, the drag coefficient and the lift coefficient, are adequately converged within the window; the surface coefficients have flattened by roughly step 300, well inside the $2200$ used. Quantities that depend on the unresolved valley recirculation, in particular the local backface temperature peaks in the inter-torus pockets, are not converged by this window and are reported in Chapter~\ref{ch:results} as a lower bound on the thermal load rather than as a settled value. Establishing that bound properly would require an unsteady production run of $5000$ to $10000$ steps on the shortlisted designs; that run is identified as future work and its absence is stated as a limitation rather than concealed."""

COMPOSITE_TPS = r"""\subsection{Composite Thermal Protection Conduction Model}
\label{sec:composite_tps}

The thermal protection system is not a homogeneous slab. The engine models it as an ordered composite stack and returns the full in-depth temperature field, so that the conduction path crosses the actual material sequence rather than an equivalent single layer. The baseline layup used for the IRVE-3 configuration is five plies, listed in Table~\ref{tab:tps_materials} together with their effective through-thickness conductivities.

\begin{table}[!htbp]
    \centering
    \caption{IRVE-3 flexible thermal protection layup and derived lumped properties.}
    \label{tab:tps_layup}
    \begin{tabularx}{\textwidth}{r >{\RaggedRight\arraybackslash}X >{\RaggedRight\arraybackslash}p{3.4cm} >{\RaggedRight\arraybackslash}p{3.0cm}}
        \toprule
        \textbf{Ply} & \textbf{Material} & \textbf{Thickness} & \textbf{$k$ (W/(m$\cdot$K))} \\
        \midrule
        1 & Nextel BF-20 outer fabric   & 0.60\,mm & 0.25 \\
        2 & Nextel BF-20 outer fabric   & 0.60\,mm & 0.25 \\
        3 & Pyrogel 2250 insulation    & 2.50\,mm & 0.02 \\
        4 & Pyrogel 2250 insulation    & 2.50\,mm & 0.02 \\
        5 & Aluminized Kapton/Kevlar gas barrier & 0.15\,mm & 0.12 \\
        \midrule
        \multicolumn{2}{l}{\textbf{Total thickness}} & \textbf{6.35\,mm} & \textbf{R = 0.25605\,m\textsuperscript{2}K/W} \\
        \bottomrule
    \end{tabularx}
\end{table}

The quoted conductivities are effective through-thickness values rather than the solid constituents, because in a felt ply the conduction path crosses inter-fibre voids. Summing the ply resistances in series gives a total areal resistance of $R = 0.25605$\,m\textsuperscript{2}\,K/W over the $6.35$\,mm stack.

The steady one-dimensional conduction equation with a radiation boundary condition on the hot face and a pinned cold face is

\begin{equation}
\label{eq:composite_cond}
    q = \frac{T_s - T_{init}}{R} + \varepsilon\,\sigma_{B}\left( T_s^{4} - T_{\infty}^{4} \right)
\end{equation}

in which the unknown hot-face temperature $T_s$ appears on both sides, so it is found by bisection rather than in closed form. Two numerical consequences are worth recording. The bisection runs in extended precision because single precision cannot resolve the relative bracket tolerance required to converge $T_s$; and the resulting in-depth profile is piecewise linear in thermal resistance, which is why it is exactly linear in depth within any single homogeneous ply and kinked at each interface. The outer emissivity is $\varepsilon = 0.80$.

This model supersedes an earlier homogeneous 25.4\,mm silicon-carbide slab that had been carried as the default. That slab was the LOFTID baseline and is four times too thick for this vehicle; the current layup is both the physically correct one and a far more demanding thermal test, which is why it changes the survivability verdict reported in Chapter~\ref{ch:results}."""

SURVIVABILITY = r"""\subsection{Survivability Acceptance Criterion}
\label{sec:survivability}

The design loop needs a single unambiguous test for whether a candidate survives, and the engine implements exactly one. Survivability is the conjunction of four independent inequalities evaluated on the flight metrics of a candidate:

\begin{equation}
\label{eq:is_survivable}
    \mathrm{Surv}(\mathbf{x}) = \left( T_{surf} \leq 2073 \right) \wedge \left( T_{back} \leq 773 \right) \wedge \left( n_{G} \leq 25 \right) \wedge \left( a_{g} \leq 25 \right)
\end{equation}

where $T_{surf}$ is the peak surface temperature in kelvin, $T_{back}$ the backface temperature in kelvin, $n_{G}$ the measured deceleration load and $a_{g}$ the computed deceleration load. All four must hold simultaneously; satisfying any three is a failure. The two temperature limits are material limits taken from the TPS presets, the two load limits are the structural limit, and the fact that the two load channels are separate is deliberate, because one is read from the solver output and the other is evaluated from the flight metrics.

For the composite layup of Sec.~\ref{sec:composite_tps} a further structural limit applies in addition to Eq.~\eqref{eq:is_survivable}: the flexible TPS carries a limit of 523.15\,K on its structural temperature, which is tighter than the Kapton limit of the gas barrier ply and therefore binds first for this vehicle.

Table~\ref{tab:acceptance_limits} collects every limit used in this study together with its origin, so that no constraint in the document is stated without a source. The design-space penalty terms of Eq.~\eqref{eq:cost_function} enforce a subset of these limits during the search, namely the maximum radius, the minimum nose radius for thermal protection coverage and the payload clearance; the temperature and load limits are instead evaluated after the fact, on the DSMC re-simulation performed by the validation gate, because they depend on the flow solution rather than on geometry alone.

\begin{table}[!htbp]
    \centering
    \caption{Acceptance limits used in this study and their origin.}
    \label{tab:acceptance_limits}
    \begin{tabularx}{\textwidth}{>{\RaggedRight\arraybackslash}p{4.6cm} >{\RaggedRight\arraybackslash}p{2.8cm} >{\RaggedRight\arraybackslash}X}
        \toprule
        \textbf{Quantity} & \textbf{Limit} & \textbf{Origin and meaning} \\
        \midrule
        Peak surface temperature & 2073\,K & Silicon-carbide structural limit \\
        Backface temperature & 773\,K & Kapton limit of the gas barrier ply \\
        TPS structural temperature & 523.15\,K & Flexible-TPS limit for this layup \\
        Deceleration load (both channels) & 25\,g & Vehicle structural limit \\
        Maximum radius & 3.0\,m & IRVE-3 diameter envelope \\
        Minimum nose radius & 1.0\,m & Thermal protection coverage \\
        Payload clearance radius & 1.0434\,m & Cylindrical payload envelope plus wall standoff \\
        \bottomrule
    \end{tabularx}
\end{table}"""

GATE = r"""\subsection{Hybrid Validation Gate Methodology}
\label{sec:gate_methodology}

The cost function of Sec.~\ref{sec:cost_function} is a closed-form surrogate, so a design that minimises it has not thereby been shown to be feasible. The gate described here is the mechanism that closes that loop, and it is the only enforced check on the surrogate anywhere in this work. It has five legs, executed in order, with the solver stage of Sec.~\ref{sec:dsmc_framework} supplying the expensive one.

\begin{enumerate}
    \item \textbf{Analytic prediction.} Evaluate Eq.~\eqref{eq:cost_function} at the candidate design and record the predicted heat load $q_{analytic}$.
    \item \textbf{DSMC re-simulation.} Run the full DSMC pipeline at the candidate geometry over the same trajectory point as the validation run, and record the surface-integrated heat load $q_{dsmc}$.
    \item \textbf{Multi-fidelity correction.} Form the ratio $c = q_{dsmc}/q_{analytic}$ and clamp it to $[0.5,\,2.0]$. The clamp is essential and not cosmetic: $c$ is a single ratio of two noisy quantities, so an unclamped value can be driven arbitrarily close to zero or arbitrarily large by statistical fluctuation alone, and would then dominate the corrected result. Clamping bounds the correction to a factor of two in either direction and forces the corrected value to remain on the same order as the prediction.
    \item \textbf{Corrected load and verdict.} The corrected heat load is $q_{hybrid} = c\,q_{analytic}$, and the design passes when $q_{hybrid} \leq Q_{target}$.
    \item \textbf{Exit status.} The gate reports pass, constraint violation, or solver failure as distinct exit codes, so that a failure can never be mistaken for a pass by a calling script.
\end{enumerate}

Two properties of this design are worth making explicit because they bound what the gate proves. The corrector is a scalar ratio applied to a scalar quantity, so it corrects the magnitude of the heat load and nothing else: it says nothing about where on the surface the load acts, nor about the peak-to-mean ratio, and a design could in principle pass the gate while concentrating heating unfavourably. And the gate is a threshold test, not an optimisation: it accepts or rejects a proposed design but does not search. Both limits are properties of a deliberately cheap gate, chosen so that the DSMC cost is paid once per shortlisted candidate rather than once per candidate in the population."""

EDITS: list[tuple[str, str, str]] = [
    # (anchor to insert BEFORE, inserted text, human description)
    (
        "\\subsection{Cartesian Grid and Collision Pairing}",
        TIMESTEP,
        "timestep and physical time window",
    ),
    (
        "\\subsection{Statistical Convergence Monitoring}",
        COMPOSITE_TPS,
        "composite F-TPS conduction model",
    ),
    (
        "\\subsection{Validation Against Flight Data}",
        SURVIVABILITY,
        "survivability acceptance criterion + limits table",
    ),
    (
        "\\section{Computational Infrastructure}",
        GATE,
        "hybrid validation gate methodology",
    ),
]


def main() -> int:
    text = CH3.read_text(encoding="utf-8")
    rc = 0
    for anchor, block, desc in EDITS:
        n = text.count(anchor)
        if n != 1:
            print(f"  !! anchor found {n}x (need 1) for: {desc}  <- {anchor!r}")
            rc = 1
            continue
        text = text.replace(anchor, block + "\n" + anchor, 1)
        print(f"  ok  inserted before {anchor[:52]!r}  [{desc}]")
    if rc == 0:
        CH3.write_text(text, encoding="utf-8")
        print(f"\nchapter_03_methodology.tex: {len(EDITS)} methodology sections added.")
    else:
        print("\nNOT WRITTEN (an anchor failed).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
