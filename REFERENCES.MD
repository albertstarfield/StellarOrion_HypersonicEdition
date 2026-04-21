# Technical References & Theoretical Foundations

This document outlines the scientific theories, papers, and books that form the foundation of the StellarOrion Hypersonic Simulation Suite, as implemented in the `StellarOrionEngineMach5Up.py` and the broader simulation pipeline.

## 1. Rarefied Gas Dynamics & DSMC
The simulation core utilizes the **Direct Simulation Monte Carlo (DSMC)** method to model high-altitude, rarefied hypersonic flows where the continuum assumption (Navier-Stokes) breaks down.

*   **Primary Text**: G. A. Bird, *Molecular Gas Dynamics and the Direct Simulation of Gas Flows*, Clarendon Press, Oxford, 1994.
*   **Solver (SPARTA)**: S. J. Plimpton, S. G. Moore, A. Borner, A. K. Stagg, T. P. Koehler, J. R. Torczynski, and M. A. Gallis, "Direct simulation Monte Carlo on petaflop supercomputers and beyond," *Physics of Fluids*, 31, 086101, 2019. [DOI: 10.1063/1.5108534](https://doi.org/10.1063/1.5108534)
*   **Software**: SPARTA DSMC Simulator ([http://sparta.github.io](http://sparta.github.io))

## 2. Mathematical Models & Equations

### Aerodynamics & Flight Metrics
The following equations are implemented in `StellarOrionEngineMach5Up.py` to derive vehicle performance from DSMC results:

*   **Dynamic Pressure ($q$):**
    $$q = \frac{1}{2} \rho v_{\infty}^2$$
*   **Ballistic Coefficient ($\beta$):**
    $$\beta = \frac{m \cdot q}{F_{drag}}$$
*   **Instantaneous g-load ($n$):**
    $$n = \frac{F_{drag}}{m \cdot g_0}$$
*   **Heat Flux Proxy ($\dot{q}$):**
    $$\dot{q} = \frac{Q_{total}}{A_{ref}}, \quad A_{ref} = \pi \left(\frac{D}{2}\right)^2$$

**Variable Definitions:**
*   $q$: Dynamic pressure $[Pa]$
*   $\rho$: Local atmospheric density $[kg/m^3]$
*   $v_{\infty}$: Freestream velocity $[m/s]$
*   $\beta$: Ballistic coefficient $[kg/m^2]$
*   $m$: Vehicle mass $[kg]$
*   $F_{drag}$: Total aerodynamic drag force $[N]$
*   $g_0$: Earth gravity constant $[9.81 m/s^2]$
*   $n$: Instantaneous deceleration load $[g's]$
*   $\dot{q}$: Average surface heat flux $[W/m^2]$
*   $Q_{total}$: Total heat load transferred to the surface $[W]$
*   $A_{ref}$: Reference area (Projected frontal area) $[m^2]$
*   $D$: Aeroshell diameter $[m]$

### Thermal Protection System (TPS)
A 1D transient approximation is used to estimate backface heating for the flexible TPS:

*   **Radiative Equilibrium Surface Temperature ($T_s$):**
    $$T_s = \left( \frac{\dot{q}}{\sigma \epsilon} \right)^{1/4}$$
*   **Adiabatic Backface Temperature Rise ($\Delta T_{back}$):**
    $$\Delta T_{back} = \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{tps} \cdot C_{p,tps} \cdot \delta_{tps}}$$

**Variable Definitions:**
*   $T_s$: Radiative equilibrium surface temperature $[K]$
*   $\sigma$: Stefan-Boltzmann constant ($5.67 \times 10^{-8} W/m^2K^4$)
*   $\epsilon$: Surface emissivity (dimensionless, 0.0 - 1.0)
*   $\Delta T_{back}$: Net temperature rise at the back of the TPS $[K]$
*   $\Delta t$: Duration of peak heat pulse $[s]$
*   $\eta_{lag}$: Thermal lag factor (efficiency coefficient, default 0.15)
*   $\rho_{tps}$: Density of the flexible TPS material $[kg/m^3]$
*   $C_{p,tps}$: Specific heat capacity of the TPS $[J/kg \cdot K]$
*   $\delta_{tps}$: Thickness of the TPS stack $[m]$

### Survivability Optimization (SBO/GA)
The optimization loop uses a Metamodel Prognosis (MoP) trained via MSE loss:

*   **Objective Function (GA Cost):**
    $$J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{y} \left( \frac{y_{pred} - y_{target}}{1} \right)^2$$
*   **Metamodel Training Loss:**
    $$\mathcal{L} = \frac{1}{N} \sum_{i=1}^{N} (y_i - \hat{y}_i)^2$$

**Variable Definitions:**
*   $J$: Objective cost function for the Genetic Algorithm
*   $w_{\beta}, w_{y}$: Weight factors for the respective error terms
*   $\beta_{calc}$: Current ballistic coefficient derived from SPARTA
*   $\beta_{target}$: Desired ballistic coefficient goal
*   $y_{pred}$: Metamodel prediction for the specific design metric
*   $y_{target}$: Target value for the design metric
*   $\mathcal{L}$: Mean Squared Error (MSE) loss for NN training
*   $y_i$: Ground truth data from the SPARTA training set
*   $\hat{y}_i$: Neural network prediction for sample $i$
*   $N$: Total number of training samples (typically 50 for MoP initialization)

### Stochastic Sampling
*   **Stratified LHS Sampling:**
    $$x_i = x_{min} + (x_{max} - x_{min}) \cdot \frac{i + r}{N}$$
    *Where $i \in [0, N-1]$ is the sample index, $r \sim \mathcal{U}(0,1)$, and $N$ is the total number of samples.*

## 3. Hypersonic Aerothermodynamics
The calculations for heat flux, stagnation point proxies, and radiative equilibrium temperatures are based on established hypersonic theory.

*   **Reference Book**: J. D. Anderson, *Hypersonic and High-Temperature Gas Dynamics*, AIAA Education Series, 2nd Edition, 2006.
*   **Physics Implemented**: 
    *   Radiative equilibrium surface temperature ($\sigma \epsilon T^4$).
    *   Ballistic Coefficient ($\beta = m / (C_D A)$) for reentry trajectory analysis.

## 3. Atmospheric Modeling
The environment presets (Artemis/Earth) use the **NRLMSIS 2.1** empirical model for neutral atmosphere temperature and density.

*   **Primary Paper**: J. T. Emmert et al., "NRLMSIS 2.1: An empirical model of nitric oxide incorporated into MSIS," *Journal of Geophysical Research: Space Physics*, 127, e2022JA030896, 2022. [DOI: 10.1029/2022JA030896](https://doi.org/10.1029/2022JA030896)

## 4. Surrogate-Based Optimization (SBO)
The survivability optimization uses a metamodeling approach to reduce the computational cost of expensive DSMC simulations.

*   **Metamodel of Optimal Prognosis (MoP)**: T. Most and J. Will, "Meta-model of Optimal Prognosis—An automatic approach for variable reduction and optimal meta-model selection," *27th CADFEM Users’ Meeting*, Leipzig, Germany, 2009.
*   **Latin Hypercube Sampling (LHS)**: M. D. McKay, R. J. Beckman, and W. J. Conover, "A Comparison of Three Methods for Selecting Values of Input Variables in the Analysis of Output from a Computer Code," *Technometrics*, 21(2), 239-245, 1979.
*   **Machine Learning**: The metamodel is implemented via a multi-layer perceptron (PyTorch) using the MoP philosophy for steering Genetic Algorithms (GA).

## 5. HIAD Design & IRVE-3 Mission
The default geometry and simulation parameters are based on NASA's Hypersonic Inflatable Aerodynamic Decelerator (HIAD) project, specifically the IRVE-3 mission.

### IRVE-3 Default Parameters (Baseline)
| Parameter | Value | Reference |
| :--- | :--- | :--- |
| **Aeroshell Diameter** | 3.0 meters | NASA IRVE-3 Mission Specs |
| **Sphere-Cone Angle** | 60° (Half-Angle) | AIAA 2013-1386 |
| **Nose Radius** | 0.191 meters | NASA HIAD Geometry Baseline |
| **Toroid Count** | 7 Inflatable Rings | IRVE-3 Inflatable Structure |
| **Stowed Diameter** | 0.47 meters | Black Brant XI Payload Envelope |
| **Nominal Mass** | 281.0 kg | IRVE-3 Flight Hardware |

### Default Simulation Environment (Artemis/Lunar Return)
The default simulation settings in `main.py` and `StellarOrionEngineMach5Up.py` are calibrated for a high-energy lunar return reentry, reflecting conditions similar to NASA's Artemis mission profile rather than the suborbital IRVE-3 test.

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| **Entry Velocity** | 10,500 m/s | Lunar-to-Earth return speed |
| **Stream Density ($n_{\rho}$)** | $3.9 \times 10^{20} \text{ m}^{-3}$ | Approx. 80km altitude (Earth) |
| **Stream Temperature** | 200.0 K | Standard Mesosphere temperature |
| **Heat Pulse Duration** | 450.0 s | Typical high-energy peak heating duration |
| **Surface Emissivity** | 0.88 | Silicon Carbide (SiC) fabric TPS |

### IRVE-3 Flight Test Results (Validation Baseline)
Based on the post-flight reconstruction (NASA/TP-2013-4012), the following parameters represent the peak conditions achieved during the July 23, 2012 flight test:

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Entry Velocity** | Mach 10.0 | ~2,700 m/s at atmospheric interface |
| **Peak Heat Flux ($\dot{q}$)** | 14.4 W/cm$^2$ | Theoretical stagnation point peak |
| **Peak Deceleration** | 20.2 g | Total deceleration load |
| **Peak Dynamic Pressure ($q$)** | 0.9 psia | ~6.2 kPa |
| **Aeroshell Diameter** | 3.0 m | Full deployment state |
| **Nose Radius ($R_n$)** | 0.191 m | Stagnation curvature radius |
| **Cone Angle** | 60$^\circ$ | Forebody half-angle |

### Mission References
*   Cassell, G. J., et al., "Inflatable Re-entry Vehicle Experiment (IRVE-3) Flight Results," *AIAA 2013-1386*, 2013.
*   Lau, K., Cheatwood, N., et al., "Inflatable Re-entry Vehicle Experiment 3 (IRVE-3) Post-Flight Aerothermal Reconstruction," *NASA/TP-2013-4012*.
*   Dillman, R., "Inflatable Reentry Vehicle Experiment-3 (IRVE-3): Project Overview \& Instrumentation," *NASA LaRC*, 2015.

## 6. Physics-Informed Neural Networks (PINNs)
The pipeline integrates a PINN refinement stage via DeepXDE to "fill the gaps" in noisy DSMC data and perform inverse parameter estimation.

*   **Software (DeepXDE)**: Lu, L., Meng, X., Mao, Z., and Karniadakis, G. E., "DeepXDE: A deep learning library for solving differential equations," *SIAM Review*, 63(1), 208-228, 2021. [DOI: 10.1137/19M1274067](https://doi.org/10.1137/19M1274067)
*   **Methodology**: G. E. Karniadakis, I. G. Kevrekidis, L. Lu, C. H. Pang, and M. Perdikaris, "Physics-informed machine learning," *Nature Reviews Physics*, 3, 422–440, 2021.

---

## 7. Magister BibTeX Database (Source: Albert Thesis Template)
The following is a raw consolidation of all scientific references from the underlying thesis template.

```bibtex
%% Chapter 1

@article{huang2023,
  title   = {Simple and robust h-adaptive shock-capturing method for flux reconstruction framework},
  author  = {Huang, Lintao and Jiang, Zhenhua and Lou, Shuai and Zhang, Xin and Yan, Chao},
  journal = {Chinese Journal of Aeronautics},
  volume  = {36},
  number  = {7},
  pages   = {348--365},
  year    = {2023},
  doi     = {10.1016/j.cja.2023.04.010},
  issn    = {1000-9361}
}

@article{menter1994SST,
  title={Two-equation eddy-viscosity turbulence models for engineering applications},
  author={Menter, Florian R.},
  journal={AIAA Journal},
  volume={32},
  number={8},
  pages={1598--1605},
  year={1994},
  publisher={American Institute of Aeronautics and Astronautics},
  doi={10.2514/3.12149}
}
@book{white2006viscous,
  author    = {White, Frank M.},
  title     = {Viscous Fluid Flow},
  edition   = {3rd},
  publisher = {McGraw-Hill Education},
  address   = {New York},
  year      = {2006},
  isbn      = {978-0072402315}
}


@Article{aerospace9120800BluntBodyTheory,
author = {Hamza, Muhammad and Khan, Saima Bukhat and Maqsood, Adnan},
title = {Geometric Optimization of Blunt Bodies with Aerodisk and Opposing Jet for Wave Drag and Heat Reduction},
journal = {Aerospace},
volume = {9},
year = {2022},
number = {12},
url = {https://www.mdpi.com/2226-4310/9/12/800},
issn = {2226-4310},
abstract = {The use of passive, active, or hybrid flow control techniques is often investigated to reduce the acoustic signature, wave drag, and aerodynamic heating associated with the supersonic flow regime. This research explores passive and hybrid flow control techniques to achieve an optimal reduction in wave drag and aerodynamic heating on a blunt body using an aerodisk. While passive techniques use one or two aerospikes, hybrid techniques employ opposing jets and aerospikes. Numerical analysis is performed using Reynolds-Averaged Navier–Stokes (RANS) equations to analyze the bodies’ flow field. The statistical technique, Design of Experiments (DOE), is combined with Response Surface Method (RSM) to find the optimal configuration for four cases by generating design space. Two cases were considered for the optimization: single aerospike with and without opposing jet and double aerospike with and without opposing jet. Variables used for the design of the aerodisks were spike length and diameter, while the response variables were wave drag and normalized heat flux. The current study has established an optimum relationship between spike length and aerospike diameter located in front of the main blunt body for both single and double aerospikes. The study’s results suggest that a double aerodisk configuration is more beneficial for reducing drag and heat flux at supersonic speed than a single aerodisk. By incorporating an opposing jet at a pressure ratio of 0.8 from the frontal aerodisk to the spiked blunt body, it can reduce drag and heat flux by 86% and 95%, respectively. Finally, numerical verification is performed for statistically optimized designs.},
doi = {10.3390/aerospace9120800}
}



@Article{aerospace10080729SWBLISBLI,
AUTHOR = {Wang, Mengge and Wang, Ziyun and Zhang, Yue and Cheng, Daishu and Tan, Huijun and Wang, Kun and Gao, Simin},
TITLE = {Control of Cowl Shock/Boundary Layer Interaction in Supersonic Inlet Based on Dynamic Vortex Generator},
JOURNAL = {Aerospace},
VOLUME = {10},
YEAR = {2023},
NUMBER = {8},
ARTICLE-NUMBER = {729},
URL = {https://www.mdpi.com/2226-4310/10/8/729},
ISSN = {2226-4310},
ABSTRACT = {A shock wave/boundary layer interaction (SWBLI) is a common phenomenon in supersonic inlet flow, which can significantly degrade the aerodynamic performance of the inlet by inducing boundary layer separation. To address this issue, in this paper, we propose the use of a dynamic vortex generator to control the SWBLI in a typical supersonic inlet. The unsteady simulation method based on dynamic grid technology was employed to verify the effectiveness of the proposed method of control and investigate its mechanism. The results showed that, in a duct of finite width at the inlet, the SWBLI generated complex three-dimensional (3D) flow structures with remarkable swirling properties. At the same time, vortex pairs were generated close to the side wall as a result of its presence, and this led to the intensification of transverse flow and, in turn, the formation of a complex 3D structure of the flow of the separation bubble. The dynamic vortex generator induced oscillations of variable intensity in the vortex system in the supersonic boundary layer that enhanced the mixing between the boundary layer flow and the mainstream. Meanwhile, the unique effects of “extrusion” and “suction” in the oscillation process continued to charge the airflow, and the distribution of velocity in the boundary layer significantly improved. As the oscillation frequency of the vortex generator increased, its charging effect on low-velocity flow in the boundary layer increased, and its control effect on the flow field of the SWBLI became more pronounced. The proposed method of control reduced the length of the separation bubble by 31.76% and increased the total pressure recovery coefficient at the inlet by 6.4% compared to the values in the absence of control.},
DOI = {10.3390/aerospace10080729}
}

@presentation{dillman2015irve3,
  author       = {Dillman, Robert},
  title        = {Inflatable Reentry Vehicle Experiment-3 ({IRVE}-3): Project Overview \& Instrumentation},
  institution  = {NASA Langley Research Center (LaRC)},
  year         = {2015},
  month        = {August},
  day          = {18},
  note         = {Presentation on HIAD technology and flight instrumentation},
  address      = {Hampton, VA}
}



@article{RecirculationCaseWindDrivenCoastal,
author = {Petronio, Andrea and Roman, Federico and Nasello, C. and Armenio, Vincenzo},
year = {2013},
month = {12},
pages = {1095-1112},
title = {Large eddy simulation model for wind-driven sea circulation in coastal areas},
volume = {20},
journal = {Nonlinear Processes in Geophysics},
doi = {10.5194/npg-20-1095-2013}
}

@article{daub2022experimentsElasticLocalizedHeating,
  author  = {Daub, Dennis and Willems, Sebastian and G{\"u}lhan, Ali},
  title   = {Experiments on aerothermoelastic fluid--structure interaction in hypersonic flow},
  journal = {Journal of Sound and Vibration},
  year    = {2022},
  volume  = {531},
  pages   = {116714},
  doi     = {10.1016/j.jsv.2021.116714},
  publisher = {Elsevier}
}

@article{articlessk,
author = {Saleem, Bala and Mustafa, Andam and Kareem, Dalshad and Yuce, Mehmet and Szydłowski, Michał and Al-Ansari, Nadhir},
year = {2023},
month = {05},
pages = {49-69},
title = {Numerical Analysis of Turbulent Flow over a Backward-facing Step in an Open Channel},
volume = {70},
journal = {Archives of Hydro-Engineering and Environmental Mechanics},
doi = {10.2478/heem-2023-0004}
}

@techreport{TPS-stateofIndustryNASA,
  author      = {Stanley A. Bouslog},
  title       = {Thermal Protection Systems: State of the Industry},
  institution = {NASA Johnson Space Center},
  year        = {2023},
  number      = {NASA/TM-20230015883},
  month       = {November},
  type        = {Technical Presentation},
  note        = {Presented at SAMPE Space Applications Webinar}
}

@article{maman2022,
  title={A New Variant of Rusanov Scheme: $\beta$-Rusanov for Numerical Resolution of Shallow Water Flows},
  author={Maman, Yarodji Abdoul Kader and Rabé, Badé and Bisso, Saley},
  journal={International Journal of Applied Mathematics},
  volume={35},
  number={4},
  pages={585--600},
  year={2022},
  doi={10.12732/ijam.v35i4.7}
}
@book{AndersonHypersonic,
  title={Hypersonic and High-Temperature Gas Dynamics},
  author={Anderson, John D.},
  year={2006},
  publisher={AIAA},
  edition={2nd}
}


@article{jameson1981numerical,
  title={Numerical solution of the Euler equations by finite volume methods using artificial viscosity},
  author={Jameson, Antony and Schmidt, W. and Turkel, Eli},
  journal={AIAA Journal},
  volume={21},
  number={9},
  pages={1525--1532},
  year={1983},
  publisher={American Institute of Aeronautics and Astronautics},
  doi={10.2514/3.8102}
}

@book{versteeg2007cfd,
  title     = {An Introduction to Computational Fluid Dynamics: The Finite Volume Method},
  author    = {Versteeg, H. K. and Malalasekera, W.},
  year      = {2007},
  edition   = {2},
  publisher = {Pearson Education},
  address   = {Harlow, England},
  isbn      = {9780131274983}
}

@manual{fluent_muscl,
  title        = {ANSYS Fluent Theory Guide},
  author       = {{ANSYS Inc.}},
  year         = {2022},
  note         = {Section 5.2.5, "Third-Order MUSCL Scheme"},
  url          = {https://www.afs.enea.it/project/neptunius/docs/fluent/html/th/node366.htm}
}

@misc{starccm_muscl_forum,
  title        = {Accuracy of the MUSCL 3rd‑order differencing scheme},
  author       = {CFD‑Online Forum user},
  howpublished = {Online forum post on STAR‑CCM+},
  year         = {2020},
  note         = {Mentions availability of MUSCL 3rd‑order scheme in STAR‑CCM+},
  url          = {https://www.cfd-online.com/Forums/star-ccm/226908-accuracy-muscl-3rd-order-differencing-scheme.html}
}

@manual{comsol_cfdmodule,
  title        = {COMSOL Multiphysics CFD Module User Guide},
  author       = {{COMSOL AB}},
  year         = {2023},
  note         = {Describes second‑order upwind and TVD limiter options},
  url          = {https://www.comsol.com/support/knowledgebase}
}

@manual{openfoam_muscl,
  title        = {OpenFOAM User Guide: TVD and NVD Schemes},
  author       = {{OpenCFD Ltd.}},
  year         = {2024},
  note         = {Documentation of TVD/MUSCL divergence schemes in OpenFOAM},
  url          = {https://www.openfoam.com/documentation/guides/latest/doc/guide-schemes-divergence-nvd-tvd.html}
}

@article{shen2023,
  title     = {An efficient class of increasingly high-order ENO schemes with multi-resolution},
  author    = {Shen, Hua},
  journal   = {arXiv preprint arXiv:2311.15504},
  year      = {2023},
  note      = {ENO-MR maintains ENO properties without WENO weighting}
}

@inproceedings{wibisono2019WENO,
  title     = {The significance of temporal discretization in the high order numerical scheme for hyperbolic conservation law},
  author    = {Wibisono, Indra and Yanuar and Kosasih, E. A.},
  booktitle = {AIP Conference Proceedings},
  volume    = {2062},
  number    = {1},
  pages     = {020021},
  year      = {2019},
  publisher = {AIP Publishing},
  doi       = {10.1063/1.5086568},
  url       = {https://doi.org/10.1063/1.5086568}
}

% Chapter 2
@article{harten1987eno,
  title     = {Uniformly High Order Accurate Essentially Non-Oscillatory Schemes, III},
  author    = {Harten, Ami and Engquist, Bjorn and Osher, Stanley and Chakravarthy, Sukumar R.},
  journal   = {Journal of Computational Physics},
  volume    = {71},
  number    = {2},
  pages     = {231--303},
  year      = {1987},
  publisher = {Elsevier}
}

@article{liu1994weno,
  title={Weighted Essentially Non-Oscillatory Schemes},
  author={Liu, Xingwen and Osher, Stanley and Chan, Tony},
  journal={Journal of Computational Physics},
  volume={115},
  number={1},
  pages={200--212},
  year={1994},
  publisher={Elsevier}
}

@article{Gottlieb2001,
  author    = {Sigal Gottlieb and Chi-Wang Shu and Eitan Tadmor},
  title     = {Strong Stability-Preserving High-Order Time Discretization Methods},
  journal   = {SIAM Review},
  volume    = {43},
  number    = {1},
  pages     = {89--112},
  year      = {2001},
  doi       = {10.1137/S003614450036757X}
}

@book{Ketcheson2011,
  author    = {David I. Ketcheson and Sigal Gottlieb and Chi-Wang Shu},
  title     = {Strong Stability Preserving Runge-Kutta and Multistep Time Discretizations},
  publisher = {World Scientific},
  year      = {2011},
  isbn      = {978-981-4366-00-5}
}

@inproceedings{Shu1998,
  author    = {Chi-Wang Shu},
  title     = {Essentially Non-Oscillatory and Weighted Essentially Non-Oscillatory Schemes for Hyperbolic Conservation Laws},
  booktitle = {Advanced Numerical Approximation of Nonlinear Hyperbolic Equations},
  editor    = {A. Quarteroni},
  series    = {Lecture Notes in Mathematics},
  volume    = {1697},
  publisher = {Springer},
  pages     = {325--432},
  year      = {1998},
  doi       = {10.1007/BFb0096355}
}

@article{Shu2020,
  author    = {Chi-Wang Shu},
  title     = {Essentially Non-Oscillatory and Weighted Essentially Non-Oscillatory Schemes for Hyperbolic Conservation Laws},
  journal   = {Springer Series in Computational Mathematics},
  volume    = {17},
  pages     = {1--36},
  year      = {2020},
  publisher = {Springer},
  doi       = {10.1007/978-3-030-51072-9_1},
  note      = {Chapter in: Handbook of Numerical Analysis, Volume 17}
}

@article{Ketcheson2011TSRK,
  author    = {David I. Ketcheson and Sigal Gottlieb and Colin B. Macdonald},
  title     = {Strong Stability Preserving Two-Step Runge--Kutta Methods},
  journal   = {SIAM Journal on Numerical Analysis},
  volume    = {49},
  number    = {6},
  pages     = {2618--2639},
  year      = {2011},
  doi       = {10.1137/10080960X}
}

@article{Bresten2016,
  author    = {Christopher Bresten and Sigal Gottlieb and Zachary Grant and Daniel Higgs and David I. Ketcheson and Adrian N{\'e}meth},
  title     = {Explicit Strong Stability Preserving Multistep Runge–Kutta Methods},
  journal   = {Mathematics of Computation},
  volume    = {86},
  number    = {304},
  pages     = {747--769},
  year      = {2016},
  doi       = {10.1090/mcom/3115}
}

@article{lax1954,
  author    = {Peter D. Lax and Kurt O. Friedrichs},
  title     = {Weak Solutions of Nonlinear Hyperbolic Equations and Their Numerical Computation},
  journal   = {Communications on Pure and Applied Mathematics},
  volume    = {7},
  number    = {1},
  pages     = {159--193},
  year      = {1954},
  publisher = {Wiley},
  doi       = {10.1002/cpa.3160070112}
}

@article{rusanov1962,
  author    = {V. V. Rusanov},
  title     = {The Calculation of the Interaction of Non-Stationary Shock Waves with Obstacles},
  journal   = {USSR Computational Mathematics and Mathematical Physics},
  volume    = {1},
  number    = {2},
  pages     = {304--320},
  year      = {1962},
  publisher = {Pergamon},
  doi       = {10.1016/0041-5553(62)90062-9}
}


@article{zhang2011weno,
  author    = {Rui Zhang and Mengping Zhang and Chi-Wang Shu},
  title     = {On the Order of Accuracy and Numerical Performance of Two Classes of Finite Volume WENO Schemes},
  journal   = {Communications in Computational Physics},
  volume    = {9},
  number    = {3},
  pages     = {807--827},
  year      = {2011},
  doi       = {10.4208/cicp.291109.080410s}
}



% Chapter 3
@misc{sodshock,
  author       = {Benjamin Van Der Broeck},
  title        = {sodshock: Exact solution to the Sod shock tube problem},
  year         = {2015},
  howpublished = {\url{https://pypi.org/project/sodshock/}},
  note         = {Version 0.1.0, accessed 2025-07-01}
}
@article{sod1978survey,
  author  = {Gary A. Sod},
  title   = {A survey of several finite difference methods for systems of nonlinear hyperbolic conservation laws},
  journal = {Journal of Computational Physics},
  volume  = {27},
  number  = {1},
  pages   = {1--31},
  year    = {1978},
  publisher = {Elsevier},
  doi     = {10.1016/0021-9991(78)90023-2}
}
% Chapter 4

@article{zhu2020new,
  title={New developments of WENO schemes and their applications in computational fluid dynamics},
  author={Zhu, Jinjie and Qiu, Jianxian and Shu, Chi-Wang},
  journal={Journal of Computational Physics},
  volume={401},
  pages={109009},
  year={2020},
  publisher={Elsevier},
  doi={10.1016/j.jcp.2019.109009}
}


@techreport{lau2013irve,
  author      = {Lau, Kai and cheatwood, Neil and others},
  title       = {Inflatable Re-entry Vehicle Experiment 3 (IRVE-3) Post-Flight Aerothermal Reconstruction},
  institution = {NASA Langley Research Center},
  year        = {2013},
  type        = {Technical Report},
  note        = {AIP-2013-4012}
}

@article{cassell2022loftid,
  author  = {Cassell, Gregory J. and others},
  title   = {Low-Earth Orbit Flight Test of an Inflatable Decelerator (LOFTID) Mission Overview and Status},
  journal = {Journal of Spacecraft and Rockets},
  year    = {2022},
  volume  = {59},
  number  = {1},
  pages   = {12--25}
}

@inproceedings{lichodziejewski2012oml,
  author    = {Lichodziejewski, David and others},
  title     = {Impact of Deformed Outer Mold Line (OML) on the Aerothermodynamic Performance of HIADs},
  booktitle = {22nd AIAA Aerodynamic Decelerator Systems Technology Conference},
  year      = {2012},
  publisher = {AIAA}
}

@inproceedings{cassell2014heart,
  author    = {Cassell, Gregory J. and others},
  title     = {Aerothermodynamic Analysis of the High-Energy Atmospheric Reentry Test (HEART) Vehicle},
  booktitle = {52nd Aerospace Sciences Meeting},
  year      = {2014},
  publisher = {AIAA}
}

@article{DiNonnoLOFTID,
  author={DiNonno, John and Cheatwood, Neil},
  title={Low-Earth Orbit Flight Test of an Inflatable Decelerator (LOFTID) Mission Overview and Science Return},
  journal={AIAA SciTech Forum},
  year={2024},
  month={Jan},
  publisher={American Institute of Aeronautics and Astronautics},
  note={Paper submitted to AIAA SciTech 2024, Orlando}
}

@inproceedings{Guidotti2023EFESTO2,
  title={EFESTO-2: European Flexible Heat Shields Advanced TPS Design and Tests for Future In-Orbit Demonstration},
  author={Guidotti, Giuseppe and Princi, Alessandro and Gutierrez-Briceno, Jaime and Trovarelli, Federico and Governale, Giuseppe and Viola, Nicole and Dietlein, Ingrid and Callsen, Steen and Bergmann, Kevin and Zhai, Junnai and Gawehn, Thomas and Gardi, Roberto and Tiseo, Barbara and Prevereaud, Ysolde and Dauvois, Yann and Gambacciani, Giovanni and Dammacco, Giada},
  booktitle={Aerospace Europe Conference 2023 – 10th EUCASS – 9th CEAS},
  year={2023},
  doi={10.13009/EUCASS2023-765}
}

@article{Guo2011Polyimide,
  author = {Guo, Haiquan and Meador, M. A. and McCorkle, L. and Quade, D. J. and Guo, J. and Hamilton, B. and Cakmak, M. and Sprowl, G.},
  title = {Polyimide Aerogels Cross-Linked through Amine Functionalized Polyoligomeric Silsesquioxane},
  journal = {ACS Applied Materials \& Interfaces},
  year = {2011},
  volume = {3},
  number = {2},
  pages = {546--552},
  doi = {10.1021/am101123h}
}

@techreport{Hui2025TestPlanning,
  author = {Hui, Frank C. L. and Terrazas-Salinas, Imelda and Thermophysics Facilities Branch Staff},
  title = {Test Planning Guide for NASA Ames Research Center Arc Jet Complex, Ballistic Range Complex, and Electric Arc-driven Shock-Tube Facility},
  institution = {NASA Ames Research Center, Entry Systems and Technology Division, Thermophysics Facilities Branch},
  year = {2025},
  number = {A029-9701-XM3 Rev. K},
  address = {Moffett Field, CA 94035},
  month = {June},
  note = {This is Revision K of the document. An earlier Revision J was published in July 2022 by I. Terrazas-Salinas.}
}

@article{AlObaidi2021Parametric,
  author = {R. A. M. Al-Obaidi and A. J. M. Al-Obaidi and A. J. M. Al-Obaidi},
  title = {Parametric Study of a Transpiration-Cooled Leading Edge for a Hypersonic Vehicle},
  journal = {Journal of Aerospace Engineering},
  volume = {34},
  number = {1},
  pages = {04020100},
  year = {2021},
  publisher = {American Society of Civil Engineers},
  doi = {10.1061/(ASCE)AS.1943-5525.0001229}
}

@book{toro2009riemann,
  title={Riemann solvers and numerical methods for fluid dynamics: a practical introduction},
  author={Toro, Eleuterio F.},
  year={2009},
  publisher={Springer Science \& Business Media}
}

```
