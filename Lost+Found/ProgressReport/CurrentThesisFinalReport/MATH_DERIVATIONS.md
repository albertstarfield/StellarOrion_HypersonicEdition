## Derivation of the Governing Equations


This appendix collects the derivations of the fundamental and governing equations
quoted in Chapters~2--4. Each derivation is given from its physical first
principle; the numerical values used are those of the IRVE-3 baseline of
Table~\ref{tab:geometry} and Table~\ref{tab:flight}.

### Conservation of Mass (Continuity)
For a control volume $V$ with surface $S$, mass conservation requires
\[
\frac{\partial}{\partial t}\int_V \rho\,dV + \oint_S \rho\,\mathbf{u}\cdot d\mathbf{S}=0.
\]
Applying the divergence theorem and shrinking $V$ to a point gives the differential
form
\[
\frac{\partial\rho}{\partial t}+\nabla\cdot(\rho\mathbf u)=0.
\]

### Conservation of Momentum (Navier--Stokes)
Newton's second law for a fluid element: the rate of change of momentum equals
surface forces (pressure $p$ and viscous stress $\tau_{ij}$) plus body forces
$\mathbf S_M$. With the Newtonian constitutive relation
$\tau_{ij}=\mu(\partial u_i/\partial x_j+\partial u_j/\partial x_i)
-\frac{2}{3}\mu(\nabla\cdot\mathbf u)\delta_{ij}$ (Stokes hypothesis), the
compressible Navier--Stokes equation is
\[
\frac{\partial(\rho\mathbf u)}{\partial t}+\nabla\cdot(\rho\mathbf u\otimes\mathbf u)
=-\nabla p+\nabla\cdot\left[\mu\left(\nabla\mathbf u+(\nabla\mathbf u)^T
-\frac{2}{3}(\nabla\cdot\mathbf u)\mathbf I\right)\right]+\mathbf S_M.
\]

### Conservation of Energy
From the first law of thermodynamics for a fluid particle, with total energy
$E=i+\tfrac12|\mathbf u|^2$,
\[
\frac{\partial(\rho E)}{\partial t}+\nabla\cdot(\rho E\mathbf u)
=\nabla\cdot(k\nabla T)+\nabla\cdot(\tau_{ij}\cdot\mathbf u)+S_E,
\]
where $S_E$ collects chemical-reaction heat release and radiation. The viscous
dissipation term $\nabla\cdot(\tau_{ij}\cdot\mathbf u)$ is the dominant
aerodynamic-heating source in hypersonic boundary layers.

### The Boltzmann Transport Equation
Let $f(\mathbf r,\mathbf v,t)$ be the single-particle distribution function.
Under molecular chaos (Stosszahlansatz) the Liouville equation reduces to
\[
\frac{\partial f}{\partial t}+\mathbf v\cdot\nabla_{\mathbf r}f
+\frac{\mathbf F}{m}\cdot\nabla_{\mathbf v}f
=\left(\frac{\partial f}{\partial t}\right)_{\mathrm{coll}},
\]
with collision integral
\[
\left(\frac{\partial f}{\partial t}\right)_{\mathrm{coll}}
=\int\!\int (f'f'_1-ff_1)\,g\,\sigma(g,\Omega)\,d\Omega\,d\mathbf v_1.
\]
The equilibrium solution is the Maxwell--Boltzmann distribution
$f_{\mathrm{eq}}=n(m/2\pi k_BT)^{3/2}\exp(-m|\mathbf v-\mathbf u|^2/2k_BT)$.

### Chapman--Enskog: Boltzmann $\to$ Navier--Stokes
Expanding $f=f_{\mathrm{eq}}(1+\Phi^{(1)}+\cdots)$ in $Kn$:
\begin{itemize}
  \item zeroth order ($Kn^0$): Euler equations (inviscid);
  \item first order ($Kn^1$): Navier--Stokes with transport coefficients
  $\mu=\frac{5}{16}\frac{\sqrt{\pi mk_BT}}{\pi d^2\Omega_\mu^{(1,1)*}}$,
  $\kappa=\frac{25}{32}\frac{\sqrt{\pi mk_BT}}{\pi d^2\Omega_\kappa^{(1,1)*}}c_v$.
\end{itemize}
Thus the Navier--Stokes equations are the continuum limit ($Kn\ll1$) of the
Boltzmann equation; DSMC is required when $Kn>0.01$.

### DSMC: No-Time-Counter Collision Count
In a cell of volume $V_{\mathrm{cell}}$ containing $N_{\mathrm{cell}}$
particles, the number of collisions per time step $\Delta t$ is
\[
N_c=\frac{N_{\mathrm{cell}}(N_{\mathrm{cell}}-1)}{2}\,
\frac{\sigma g\,\Delta t}{V_{\mathrm{cell}}}.
\]
Particles are moved ballistically ($\mathbf r^{n+1}=\mathbf r^n+\mathbf v^n\Delta t$)
then collided pairwise using the VSS model; macroscopic quantities are accumulated
as time-averaged particle statistics.

### Variable Soft Sphere (VSS) Cross-Section
\[
\sigma=\pi d_{\mathrm{ref}}^2\left(\frac{g_{\mathrm{ref}}}{g}\right)^{2(\omega-0.5)},
\]
where $\omega$ is the viscosity index ($\omega=0.5$ reduces to hard sphere;
$\omega>0.5$ gives a velocity-dependent cross-section reproducing the
temperature-dependent viscosity of real gases).

### Mean Free Path and Knudsen Number
\[
\lambda=\frac{1}{\sqrt2\,\pi d^2 n},\qquad Kn=\frac{\lambda}{L}.
\]
For the IRVE-3 body ($L=3.0$~m, $d=3.7\times10^{-10}$~m) at the archived run
density $n=1.448\times10^{22}$~m$^{-3}$, $\lambda\approx1.1\times10^{-4}$~m and
$Kn\approx4\times10^{-5}$ (near-continuum).

### Radiative Equilibrium Surface Temperature
Balancing incoming convective flux $\dot q$ against grey-body radiation:
\[
\dot q=\epsilon\sigma T_s^4 \;\Rightarrow\;
T_s=\left(\frac{\dot q}{\epsilon\sigma}\right)^{1/4},
\qquad \sigma=5.670374419\times10^{-8}\ \mathrm{W\,m^{-2}\,K^{-4}}.
\]

### One-Dimensional Backface Temperature
\[
T_{\mathrm{back}}=T_{\mathrm{init}}
+\frac{\dot q\,\Delta t\,\eta_{\mathrm{lag}}}
{\rho_{\mathrm{TPS}}\,C_{p,\mathrm{TPS}}\,\delta_{\mathrm{TPS}}},
\qquad \eta_{\mathrm{lag}}\approx0.15.
\]

### Ballistic Coefficient and g-Load
\[
\beta=\frac{m\,q}{F_{\mathrm{drag}}},\qquad
n=\frac{F_{\mathrm{drag}}}{m\,g_0},\qquad g_0=9.80665\ \mathrm{m\,s^{-2}}.
\]
For IRVE-3, $\beta=26.9$~kg/m$^2$ (flight) vs. $27.70$ (this work, +3.0\%).

### Cost Function of the Genetic Algorithm
The composite cost (Eq.~\eqref{eq:ga_cost}) is
\[
\begin{aligned}
J(\mathbf x)={}&W_{HL}\frac{Q}{Q_{\mathrm{target}}}
+W_q\frac{\dot q_{SG}}{\dot q_{\mathrm{ref}}}
+W_\beta\left(\frac{\beta}{\beta_{\mathrm{ref}}}-1\right)^2\\
&+W_{Cd}\max\!\left(0,\frac{C_{d,\mathrm{goal}}-C_d}{C_{d,\mathrm{goal}}}\right)
+\Lambda_{\mathrm{pen}}\Phi(\mathbf x),
\end{aligned}
\]
with $W_{HL}=1.0$, $W_q=0.5$, $W_\beta=0.5$, $W_{Cd}=30$,
$\Lambda_{\mathrm{pen}}=100$, $C_{d,\mathrm{goal}}=1.70$, and
$\Phi$ the envelope/payload penalty. All terms are dimensionless and
non-negative, so $J(\mathbf x)\ge0$; evaluation requires no solver call.

### Sutton--Graves Stagnation Heat Flux
\[
\dot q_s=C_{SG}\sqrt{\frac{\rho_\infty}{R_N}}\,V_\infty^3,\qquad
C_{SG}=1.7415\times10^{-4}.
\]
At $\rho_\infty=7.851\times10^{-4}$~kg/m$^3$, $R_N=1.5$~m,
$V_\infty=3378$~m/s: $\dot q_s\approx1.536\times10^5$~W/m$^2=15.36$~W/cm$^2$.

### Fay--Riddell Stagnation-Point Heat Transfer
\[
\dot q_s=0.763\,\mathrm{Pr}^{-0.6}\,(\rho_e\mu_e)^{0.4}\,(\rho_w\mu_w)^{0.1}\,
\sqrt{\left(\frac{du_e}{dx}\right)_s}\,(h_s-h_w).
\]

### Verified Fundamental Identities (LEAN / Rocq)
\[
\sqrt{\frac{1.5}{0.135}}=\frac{10}{3}\approx3.333,\qquad
\kappa=\frac{0.55}{1.5}=\frac{11}{30}\approx0.3667.
\]


### Sutton--Graves Heat Flux Derivation

The Sutton--Graves stagnation-point convective heat flux correlation is given by:

\dot{q} = C_{SG} \sqrt{\frac{\rho_\infty}{R_N}} \, V_\infty^3

where C_{SG} = 1.7415 × 10^{-4} W m^{-2} (kg m^{-3})^{-1/2} (m s^{-1})^{-3}.

Dimensional verification with SPARTA DSMC run conditions (rho_inf = 7.851e-4 kg/m^3, R_N = 1.5 m, V_inf = 3378 m/s):

\dot{q} = 1.7415e-4 × sqrt(7.851e-4 / 1.5) × (3378)^3 ≈ 1.536e5 W/m^2 = 15.36 W/cm^2

This single-point value is +6.9% relative to the 14.36 W/cm^2 flight measurement and +0.7% relative to Rapisarda's trajectory-integrated peak of 15.26 W/cm^2.
