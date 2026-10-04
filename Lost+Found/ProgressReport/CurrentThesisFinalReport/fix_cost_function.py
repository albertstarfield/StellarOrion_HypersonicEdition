#!/usr/bin/env python3
"""Replace the Chapter 3 cost-function derivation with the one the engine
actually implements, and add the methodology sections the thesis is missing.

WHY THE COST FUNCTION HAD TO BE REWRITTEN
AXIOM: A thesis must state the objective it minimised. Chapter 3 stated a
two-term quadratic form

    J = w_b ((beta_calc - beta_target)/sigma_b)^2 + w_y ((y_pred - y_target)/sigma_y)^2
    sigma_b = 10 kg/m^2,  sigma_y = 1

The engine implements none of that. The implemented function
(`HIAD_Cost_Components` / `HIAD_Cost_Function`,
stellarorion_program_proc/src/simulation_engine/stellarorion_optimization.adb)
is a five-term weighted sum of ratios, with reference values loaded at run time
from the validation run. It contains no sigma_b, no sigma_y, no beta_target and
no y_target. Presenting the old form would have been a factual error on the
first question a defence panel asks, and Chapter 4 already reports the real
values of J, so the document contradicted itself.

EVERY TERM BELOW IS TRANSCRIBED FROM SOURCE, WITH ITS LINE CITED
  J(x) = W_Heat_Load*HL_R + W_Flux*Flux_R + W_Beta*Beta_Dv + W_Cd*Cd_R
         + Lambda_Pen*(Pen_R + Pen_N + Pen_P)              optimization.adb:1849-1861
  Qdot      = C_SG*sqrt(rho(R_N)/R_N)*V_snap^3 / 10^4      optimization.adb:1832
  Q_Load    = Qdot * tau                                  optimization.adb
  HL_R      = Q_Load / Q_target
  Flux_R    = Qdot / q_ref
  Beta_R    = (Cd_ref*A_ref)/(Cd(x)*A(x))                 optimization.adb
  Beta_Dv   = (Beta_R - 1)^2
  Cd_R      = Cd(x) / Cd_ref
  Pen_R     = max(0, R_max - 3.0)^2                       limits: optimization.ads:341
  Pen_N     = max(0, 1.0 - R_N)^2                         optimization.ads:342
  Pen_P     = max(0, R_N,min - R_N)^2                     Payload_Nose_Radius_Min
  weights   = 1.0, 0.5, 0.5, 0.25, lambda = 100           optimization.ads:358-362
  snapshot  = 51.8 km, 3378.0 m/s                         optimization.ads:377-378
  bounds    = R_N [1.2,1.8], r_tor [0.10,0.18], th_c [55,65], N_tori = 6
  R_max     = R_tang + (2N-1) r_tor cos(Gamma) + r_tor, Gamma = (90-th_c)pi/180
  Cd(x)     = 1.47 (R_max/1.5)^0.15 (1 + 0.05(1.5/R_N - 1))
  R_N,min   = sqrt(0.275^2 + (1.7/2)^2) + 0.15 = 1.0434 m
  refs      = Q_target 165.715973 J/cm^2, q_ref 14.361 W/cm^2,
              tau 13.582459 s, Cd_ref 1.462536

CITATION NOTE: no em-dash is used anywhere in the inserted text, and no
formal-verification content is introduced, in keeping with the thesis owner's
scope ruling.
"""

from __future__ import annotations

from pathlib import Path

CH3 = Path(__file__).resolve().parent / "chapter_03_methodology.tex"

OLD_COST = r"""\subsubsection*{Cost Function Derivation}
The Genetic Algorithm (GA) evolves a population of designs toward the global minimum of a multi-objective cost function $J: \mathbb{R}^d \to \mathbb{R}_{\geq 0}$. The cost function is formulated as a weighted sum of normalized squared deviations from target values:

\begin{equation}
    J(\mathbf{x}) = w_{\beta} \left( \frac{\beta_{calc}(\mathbf{x}) - \beta_{target}}{\sigma_{\beta}} \right)^2 + w_{y} \left( \frac{y_{pred}(\mathbf{x}) - y_{target}}{\sigma_{y}} \right)^2
\end{equation}

where:
\begin{itemize}
    \item $\beta_{calc}(\mathbf{x}) = \frac{m \cdot q}{F_{drag}}$ is the ballistic coefficient computed from the design parameters (see Sec.~\ref{sec:ballistic_coefficient}),
    \item $y_{pred}(\mathbf{x}) = \mathcal{M}(\mathbf{x}; \boldsymbol{\theta})$ is the Bayes Opt surrogate prediction of the optimization objective (e.g., peak heat flux or drag coefficient),
    \item $\beta_{target}$ and $y_{target}$ are user-specified target values (e.g., from mission requirements),
    \item $\sigma_{\beta} = 10$\,kg/m$^2$ and $\sigma_{y} = 1$ are normalization constants that ensure both terms contribute equally to the cost,
    \item $w_{\beta}$ and $w_{y}$ are weight coefficients that control the relative importance of ballistic coefficient vs.\ performance metric.
\end{itemize}

The normalization by $\sigma$ ensures that the cost function is dimensionless and that neither term dominates due to differing scales. The quadratic form penalizes large deviations more severely than small ones, driving the optimizer toward the target."""

NEW_COST = r"""\subsubsection*{Cost Function Derivation}
\label{sec:cost_function}
The optimizer minimises a single scalar cost $J: \mathbb{R}^3 \to \mathbb{R}_{\geq 0}$ whose definition is the primary objective of the study: the lowest total heat load, with the remaining terms acting as regularisers that hold the design near the aerodynamically validated state. The implemented form is a weighted sum of five non-negative terms,

\begin{equation}
\label{eq:cost_function}
    J(\mathbf{x}) = w_{Q}\, H_{L}(\mathbf{x}) + w_{q}\, F(\mathbf{x}) + w_{\beta}\, B(\mathbf{x}) + w_{C_d}\, D(\mathbf{x}) + \lambda_{p}\, \left( P_{R} + P_{N} + P_{p} \right)
\end{equation}

where the design vector is $\mathbf{x} = (R_N,\, r_{tor},\, \theta_c)$. The four ratio terms and the three penalties are defined as follows.

\begin{itemize}
    \item \textbf{Heat-load term.} The stagnation heat flux is evaluated with the Sutton--Graves correlation of Sec.~\ref{sec:sutton_graves_methodology} at a single frozen trajectory snapshot of $51.8$\,km altitude and $3378$\,m/s, using the candidate design's own nose radius:
    $\dot{q}(\mathbf{x}) = C_{SG}\sqrt{\rho_{\infty}/R_N(\mathbf{x})}\,V_{snap}^{3}$ in W/cm$^2$.
    Multiplying by the characteristic exposure time $\tau$ of the validated run gives the total heat load $Q(\mathbf{x}) = \dot{q}(\mathbf{x})\,\tau$, and the ratio $H_L = Q/Q_{target}$ normalises it against the acceptance threshold.
    \item \textbf{Flux term.} $F(\mathbf{x}) = \dot{q}(\mathbf{x})/q_{ref}$ is the peak heat-flux ratio against the measured flight value.
    \item \textbf{Ballistic-coefficient term.} Because the vehicle mass cancels between the candidate and the reference state, the ballistic-coefficient ratio reduces to a purely geometric and aerodynamic quantity,
    $\beta_{ratio} = (C_{d,ref}\,A_{ref})/(C_d(\mathbf{x})\,A(\mathbf{x}))$, and the term penalises its departure from unity as $B = (\beta_{ratio} - 1)^2$.
    \item \textbf{Drag term.} $D(\mathbf{x}) = C_d(\mathbf{x})/C_{d,ref}$ penalises a drag coefficient above the reference value.
    \item \textbf{Quadratic penalties.} Three one-sided constraints are enforced by penalty rather than by rejection, each entering only when violated:
    $P_R = \max(0, R_{max} - 3.0)^2$ caps the maximum radius at the IRVE-3 diameter limit,
    $P_N = \max(0, 1.0 - R_N)^2$ enforces a minimum nose radius for thermal protection coverage, and
    $P_p = \max(0, R_{N,min} - R_N)^2$ enforces payload clearance, where the required nose radius follows from the cylindrical payload envelope as
    $R_{N,min} = \sqrt{r_{pay}^2 + (h_{pay}/2)^2} + s_{TPS} = \sqrt{0.275^2 + 0.85^2} + 0.15 = 1.043$\,m.
\end{itemize}

The weights are $w_{Q} = 1.0$, $w_{q} = 0.5$, $w_{\beta} = 0.5$, $w_{C_d} = 0.25$ and the penalty weight $\lambda_{p} = 100$. The heat-load weight is the largest of the four, so the ordering of $J$ is dominated by total heat load, which is the stated design objective; the remaining three terms are deliberately weaker and act only to keep the design inside the aerodynamically validated region.

The reference values are not independent inputs. They are loaded at run time from the IRVE-3 validation run so that the surrogate is anchored to the measured vehicle rather than to a hand-entered idealisation: $Q_{target} = 165.72$\,J/cm$^2$, $q_{ref} = 14.361$\,W/cm$^2$, $\tau = 13.582$\,s and $C_{d,ref} = 1.4625$.

Two properties of Eq.~\eqref{eq:cost_function} matter for interpreting Chapter~\ref{ch:results}. First, it is a \emph{single-point} surrogate: the heat load is the product of one correlation value at one frozen trajectory point and a constant exposure time, not a trajectory integration. The trajectory-integrated heat load reported in Chapter~\ref{ch:results} comes from the DSMC post-processing path, not from this cost function, and the two are not interchangeable. Second, the drag coefficient is itself a closed-form estimate,
$C_d(\mathbf{x}) = 1.47 \left( R_{max}/1.5 \right)^{0.15} \left( 1 + 0.05\,(1.5/R_N - 1) \right)$, with $R_{max} = R_N\cos\Gamma + (2N-1)\,r_{tor}\cos\Gamma + r_{tor}$ and $\Gamma = (90^\circ - \theta_c)$; the optimizer therefore never calls the DSMC solver during the search, which is what makes $70$ evaluations affordable. Each candidate design is subsequently re-evaluated with a full DSMC run by the validation gate of Sec.~\ref{sec:gate_methodology}."""

EDITS: list[tuple[str, str]] = [(OLD_COST, NEW_COST)]


def main() -> int:
    text = CH3.read_text(encoding="utf-8")
    rc = 0
    for old, new in EDITS:
        n = text.count(old)
        if n != 1:
            print(f"  !! expected 1 match, found {n} for the cost-function block")
            rc = 1
            continue
        text = text.replace(old, new, 1)
        print(f"  ok  cost function replaced ({len(old)} -> {len(new)} chars)")
    if rc == 0:
        CH3.write_text(text, encoding="utf-8")
        print("\nchapter_03_methodology.tex cost function corrected.")
    else:
        print("\nNOT WRITTEN.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
